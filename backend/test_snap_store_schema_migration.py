from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend.snaps_store import SnapStore, SnapStoreCorruptionError
from backend.snapshot_schema import canonical_time_context, canonicalize_snapshot_record


def _legacy_synthetic_snap(snap_id: str = "legacy-greece"):
    return {
        "id": snap_id,
        "label": "Synthetic legacy broad-place chart",
        "effective_datetime": "2001-02-03T14:15:00",
        "location": "greece",
        "timezone": "Europe/Athens",
        "timezone_label": "Europe/Athens (UTC+00:00)",
        "coords": [39.0, 22.0],
        "dashboard": {
            "timestamp": "2001-02-03T14:15:00",
            "location": "greece",
            "timezone": "Europe/Athens",
            "timezone_label": "Europe/Athens (UTC+00:00)",
            "planets": [
                {"planet": "Sun", "longitude": 314.0, "house": 4},
                {"planet": "Moon", "longitude": 75.0, "house": 12},
            ],
            "house_cusps": [
                172.32, 198.76, 228.27, 261.85, 295.72, 325.69,
                352.32, 18.76, 48.27, 81.85, 115.72, 145.69,
            ],
        },
    }


def test_migration_preserves_legacy_coords_and_converts_local_wall_time(tmp_path):
    path = tmp_path / "snaps_store.json"
    path.write_text(json.dumps({"snaps": [_legacy_synthetic_snap()]}), encoding="utf-8")

    store = SnapStore(str(path))
    snap = store.get("legacy-greece")

    assert snap["effective_datetime"] == "2001-02-03T12:15:00+00:00"
    assert snap["local_datetime"] == "2001-02-03T14:15:00+02:00"
    assert snap["timezone_label"] == "Europe/Athens (UTC+02:00)"
    assert (snap["latitude"], snap["longitude"]) == pytest.approx(
        (39.0, 22.0)
    )
    assert snap["coordinate_provenance"] == {
        "source": "snap.coords",
        "persisted_with_chart": True,
        "inferred_at_read_time": False,
        "legacy_shape": "snap.coords",
        "location_specificity": "generic_or_ambiguous",
        "review_required": True,
    }
    context = snap["calculation_context"]
    assert context["time_provenance"]["interpretation"] == (
        "legacy_local_wall_time_with_iana_zone"
    )
    assert context["review_required"] is True
    assert snap["migration"]["original_context"]["effective_datetime"] == (
        "2001-02-03T14:15:00"
    )


@pytest.mark.parametrize(
    "location",
    (
        "Pennsylvania",
        "Germany",
        "Iran",
        "Israel",
        "Idaho, United States",
        "West Virginia, USA",
        "California, United States",
        "Illinois, USA",
        "North Brabant, Netherlands",
        "Greater London, England, UK",
    ),
)
def test_country_and_admin_centroid_labels_require_review_for_new_saves(location):
    snap = {
        "schema_version": 2,
        "id": f"broad-{location}",
        "effective_datetime": "2001-02-03T12:15:00+00:00",
        "location": location,
        "timezone": "UTC",
        "latitude": 40.0,
        "longitude": -75.0,
        "coordinate_provenance": {
            "source": "geocoder",
            "persisted_with_chart": True,
            "inferred_during_calculation": True,
            "review_required": False,
            "location_specificity": "specific",
        },
        "dashboard": {},
    }

    canonical = canonicalize_snapshot_record(snap)

    assert canonical["coordinate_provenance"]["review_required"] is True
    assert (
        canonical["coordinate_provenance"]["location_specificity"]
        == "generic_or_ambiguous"
    )
    assert canonical["calculation_context"]["review_required"] is True


@pytest.mark.parametrize(
    "location",
    (
        "Athens, Greece",
        "Marseille, France",
        "Ottawa, Ontario",
        "Berkeley, California",
        "London",
    ),
)
def test_specific_city_labels_remain_eligible(location):
    snap = {
        "schema_version": 2,
        "id": f"city-{location}",
        "effective_datetime": "2001-02-03T12:15:00+00:00",
        "location": location,
        "timezone": "UTC",
        "latitude": 40.0,
        "longitude": -75.0,
        "coordinate_provenance": {
            "source": "selected_city",
            "persisted_with_chart": True,
            "review_required": False,
        },
        "dashboard": {},
    }

    canonical = canonicalize_snapshot_record(snap)

    assert canonical["coordinate_provenance"]["review_required"] is False
    assert canonical["coordinate_provenance"]["location_specificity"] == "specific"
    assert canonical["calculation_context"]["review_required"] is False


def test_migration_is_byte_stable_after_first_backup(tmp_path):
    path = tmp_path / "snaps_store.json"
    path.write_text(json.dumps({"snaps": [_legacy_synthetic_snap()]}), encoding="utf-8")

    store = SnapStore(str(path))
    first_bytes = path.read_bytes()
    first_backups = list(tmp_path.glob("snaps_store.json.backup-*"))
    first_mtime = path.stat().st_mtime_ns

    store.list()
    store.list()

    assert path.read_bytes() == first_bytes
    assert path.stat().st_mtime_ns == first_mtime
    assert list(tmp_path.glob("snaps_store.json.backup-*")) == first_backups
    assert len(first_backups) == 1


def test_duplicate_groups_are_reported_without_deleting_records(tmp_path):
    path = tmp_path / "snaps_store.json"
    snap_a = _legacy_synthetic_snap("snap-b")
    snap_b = _legacy_synthetic_snap("snap-a")
    path.write_text(json.dumps({"snaps": [snap_a, snap_b]}), encoding="utf-8")

    store = SnapStore(str(path))
    snaps = store.list()

    assert len(snaps) == 2
    assert {snap["duplicate_group"]["canonical_id"] for snap in snaps} == {"snap-a"}
    assert sum(bool(snap["duplicate_group"]["is_canonical"]) for snap in snaps) == 1
    report = store.migration_report()
    assert report["duplicates_removed"] == 0
    assert report["semantic_duplicate_groups"][0]["member_ids"] == ["snap-a", "snap-b"]


def test_idempotency_key_returns_existing_record(tmp_path):
    store = SnapStore(str(tmp_path / "snaps_store.json"))
    first = store.add(_legacy_synthetic_snap("snap-one"), idempotency_key="save-click-1")
    second_payload = _legacy_synthetic_snap("snap-two")
    second = store.add(second_payload, idempotency_key="save-click-1")

    assert second["id"] == first["id"] == "snap-one"
    assert len(store.list()) == 1


def test_add_replacement_preserves_and_marks_original(tmp_path):
    store = SnapStore(str(tmp_path / "snaps_store.json"), max_snaps=1)
    store.add(_legacy_synthetic_snap("legacy"))
    replacement = _legacy_synthetic_snap("corrected")
    replacement.update({
        "effective_datetime": "2001-02-03T12:15:00+00:00",
        "local_datetime": "2001-02-03T14:15:00+02:00",
        "location": "Athens, Greece",
        "timezone": "Europe/Athens",
        "latitude": 37.9838,
        "longitude": 23.7275,
        "coords": None,
    })

    stored = store.add_replacement("legacy", replacement)

    assert stored["id"] == "corrected"
    assert store.get("legacy")["superseded_by"] == "corrected"
    assert store.get("legacy")["supersession"]["records_removed"] == 0
    assert store.get("corrected")["supersedes"] == "legacy"
    assert len(store.list()) == 2


def test_changed_context_creates_replacement_revision_chain(tmp_path):
    store = SnapStore(str(tmp_path / "snaps_store.json"))
    store.add(_legacy_synthetic_snap("legacy"))
    first = _legacy_synthetic_snap("corrected-1")
    first.update({
        "effective_datetime": "2001-02-03T12:15:00+00:00",
        "location": "Athens, Greece",
        "timezone": "Europe/Athens",
        "latitude": 37.9838,
        "longitude": 23.7275,
        "coords": None,
    })
    stored_first = store.add_replacement("legacy", first)

    identical_retry = copy.deepcopy(first)
    identical_retry["id"] = "retry-with-new-id"
    stored_retry = store.add_replacement("legacy", identical_retry)

    assert stored_retry["id"] == stored_first["id"] == "corrected-1"
    assert store.get("retry-with-new-id") is None

    changed = copy.deepcopy(first)
    changed["id"] = "corrected-2"
    changed["latitude"] = 37.9755
    changed["longitude"] = 23.7348
    revised = store.add_replacement("legacy", changed)

    assert revised["id"] == "corrected-2"
    assert revised["supersedes"] == "corrected-1"
    assert revised["correction_source_id"] == "legacy"
    assert revised["correction_revision"] == 2
    assert store.get("corrected-1")["superseded_by"] == "corrected-2"
    assert store.get("legacy")["superseded_by"] == "corrected-2"
    assert {snap["id"] for snap in store.list()} == {
        "legacy",
        "corrected-1",
        "corrected-2",
    }

    assert store.delete("corrected-2") is True
    assert store.get("legacy")["superseded_by"] == "corrected-1"
    assert "superseded_by" not in store.get("corrected-1")
    assert store.get("corrected-2") is None
    live = {snap["id"]: snap for snap in store.list()}
    assert all(
        not snap.get("superseded_by")
        or snap["superseded_by"] in live
        for snap in live.values()
    )
    saved = json.loads(
        (tmp_path / "snaps_store.json").read_text(encoding="utf-8")
    )
    assert "corrected-2" in saved["tombstones"]


def test_deleting_replacement_backs_up_store_and_reopens_original_for_correction(
    tmp_path,
):
    path = tmp_path / "snaps_store.json"
    store = SnapStore(str(path))
    store.add(_legacy_synthetic_snap("legacy"))
    first_replacement = _legacy_synthetic_snap("corrected")
    first_replacement.update({
        "effective_datetime": "2001-02-03T12:15:00+00:00",
        "location": "Athens, Greece",
        "timezone": "Europe/Athens",
        "latitude": 37.9838,
        "longitude": 23.7275,
        "coords": None,
    })
    store.add_replacement("legacy", first_replacement)

    assert store.delete("corrected") is True

    original = store.get("legacy")
    assert "superseded_by" not in original
    assert original["supersession"]["status"] == "replacement_deleted_source_reopened"
    assert original["supersession_history"][-1]["replacement_id"] == "corrected"

    document = json.loads(path.read_text(encoding="utf-8"))
    tombstone = document["tombstones"]["corrected"]
    backup_path = Path(tombstone["backup_path"])
    assert tombstone["backup_contains_deleted_record"] is True
    assert backup_path.exists()
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    assert any(snap.get("id") == "corrected" for snap in backup["snaps"])

    second_replacement = copy.deepcopy(first_replacement)
    second_replacement["id"] = "corrected-again"
    stored = store.add_replacement("legacy", second_replacement)

    assert stored["id"] == "corrected-again"
    assert store.get("legacy")["superseded_by"] == "corrected-again"
    assert store.get("corrected") is None
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "corrected" in saved["tombstones"]


def test_legacy_import_does_not_apply_normal_retention_cap(tmp_path):
    current_path = tmp_path / "current" / "snaps_store.json"
    legacy_path = tmp_path / "legacy" / "snaps_store.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        json.dumps({"snaps": [_legacy_synthetic_snap("legacy")]}),
        encoding="utf-8",
    )
    store = SnapStore(str(current_path), max_snaps=1)
    current = _legacy_synthetic_snap("current")
    current["effective_datetime"] = "2000-01-01T00:00:00+00:00"
    current["dashboard"]["timestamp"] = "2000-01-01T00:00:00+00:00"
    store.add(current)

    report = store.import_legacy(str(legacy_path))

    assert report["last_imported_ids"] == ["legacy"]
    assert {snap["id"] for snap in store.list()} == {"legacy", "current"}


def test_legacy_import_marker_and_tombstone_prevent_resurrection(tmp_path):
    current_path = tmp_path / "backend" / "snaps_store.json"
    legacy_path = tmp_path / "snaps_store.json"
    legacy_path.write_text(
        json.dumps({"snaps": [_legacy_synthetic_snap("old-snap")]}),
        encoding="utf-8",
    )
    store = SnapStore(str(current_path))

    first_report = store.import_legacy(str(legacy_path))
    assert first_report["imported_ids"] == ["old-snap"]
    assert store.delete("old-snap") is True
    second_report = store.import_legacy(str(legacy_path))

    assert second_report == first_report
    assert store.get("old-snap") is None
    saved = json.loads(current_path.read_text(encoding="utf-8"))
    assert saved["tombstones"]["old-snap"]["reason"] == "user_deleted"

    legacy_path.write_text(
        json.dumps({"snaps": [_legacy_synthetic_snap("late-legacy-snap")]}),
        encoding="utf-8",
    )
    incremental_report = store.import_legacy(str(legacy_path))
    assert incremental_report["last_imported_ids"] == ["late-legacy-snap"]
    assert incremental_report["imported_ids"] == ["old-snap", "late-legacy-snap"]
    assert store.get("late-legacy-snap") is not None
    assert store.get("old-snap") is None
    assert store.import_legacy(str(legacy_path)) == incremental_report
    assert sum(
        snap["id"] == "late-legacy-snap" for snap in store.list()
    ) == 1


def test_corrupt_store_is_quarantined_and_never_overwritten(tmp_path):
    path = tmp_path / "snaps_store.json"
    corrupt_bytes = b'{"snaps": [broken'
    path.write_bytes(corrupt_bytes)

    with pytest.raises(SnapStoreCorruptionError) as exc_info:
        SnapStore(str(path))

    assert path.read_bytes() == corrupt_bytes
    quarantine = Path(exc_info.value.quarantine_path)
    assert quarantine.read_bytes() == corrupt_bytes


def test_unchanged_corrupt_store_reuses_one_quarantine_copy(tmp_path):
    path = tmp_path / "snaps_store.json"
    corrupt_bytes = b'{"snaps": [still-broken'
    path.write_bytes(corrupt_bytes)

    with pytest.raises(SnapStoreCorruptionError) as first:
        SnapStore(str(path))
    with pytest.raises(SnapStoreCorruptionError) as second:
        SnapStore(str(path))

    assert first.value.quarantine_path == second.value.quarantine_path
    quarantine_files = list(tmp_path.glob(
        "snaps_store.json.corrupt-quarantine.*.json"
    ))
    assert quarantine_files == [Path(first.value.quarantine_path)]
    assert quarantine_files[0].read_bytes() == corrupt_bytes
    assert path.read_bytes() == corrupt_bytes


def test_corrupt_quarantine_retention_is_bounded_and_keeps_current_copy(
    tmp_path,
):
    path = tmp_path / "snaps_store.json"
    quarantines = []

    for index in range(8):
        corrupt_bytes = f'{{"snaps": [broken-{index}'.encode()
        path.write_bytes(corrupt_bytes)
        with pytest.raises(SnapStoreCorruptionError) as exc_info:
            SnapStore(str(path))
        quarantines.append(Path(exc_info.value.quarantine_path))

    retained = list(tmp_path.glob(
        "snaps_store.json.corrupt-quarantine.*.json"
    ))
    assert len(retained) == 5
    assert quarantines[-1] in retained
    assert quarantines[-1].read_bytes() == b'{"snaps": [broken-7'
    assert path.read_bytes() == b'{"snaps": [broken-7'


def test_quarantine_retention_cap_includes_current_copy_even_if_source_mtime_is_old(
    tmp_path,
):
    path = tmp_path / "snaps_store.json"
    for index in range(5):
        sidecar = tmp_path / (
            f"snaps_store.json.corrupt-quarantine.preexisting-{index}.json"
        )
        sidecar.write_bytes(f"older-{index}".encode())
        mtime_ns = 2_000_000_000_000_000_000 + index
        sidecar.touch()
        os.utime(sidecar, ns=(mtime_ns, mtime_ns))

    current_bytes = b'{"snaps": [current-broken'
    path.write_bytes(current_bytes)
    old_mtime_ns = 1_000_000_000_000_000_000
    os.utime(path, ns=(old_mtime_ns, old_mtime_ns))

    with pytest.raises(SnapStoreCorruptionError) as exc_info:
        SnapStore(str(path))

    retained = list(tmp_path.glob(
        "snaps_store.json.corrupt-quarantine.*.json"
    ))
    assert len(retained) == 5
    assert Path(exc_info.value.quarantine_path) in retained
    assert Path(exc_info.value.quarantine_path).read_bytes() == current_bytes
    assert path.read_bytes() == current_bytes


def test_quarantine_pruning_never_follows_matching_name_symlink(tmp_path):
    path = tmp_path / "snaps_store.json"
    store = SnapStore(str(path))
    unrelated = tmp_path / "unrelated-user-data.txt"
    unrelated.write_text("must survive", encoding="utf-8")
    symlink = tmp_path / (
        "snaps_store.json.corrupt-quarantine.symlink.json"
    )
    try:
        symlink.symlink_to(unrelated)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    regular_sidecars = []
    for index in range(6):
        sidecar = tmp_path / (
            f"snaps_store.json.corrupt-quarantine.real-{index}.json"
        )
        sidecar.write_text(f"corrupt-{index}", encoding="utf-8")
        regular_sidecars.append(sidecar)

    store._prune_corrupt_quarantines_unlocked(
        keep_path=str(regular_sidecars[-1])
    )

    assert unrelated.read_text(encoding="utf-8") == "must survive"
    assert symlink.is_symlink()
    assert regular_sidecars[-1].exists()
    assert sum(sidecar.exists() for sidecar in regular_sidecars) == 5


def test_concurrent_backend_processes_do_not_lose_snap_writes(tmp_path):
    path = tmp_path / "snaps_store.json"
    script = (
        "import sys;"
        "from backend.snaps_store import SnapStore;"
        "store=SnapStore(sys.argv[1]);"
        "store.add({'id':sys.argv[2],"
        "'effective_datetime':'2026-01-01T00:00:00+00:00',"
        "'location':'Greenwich, UK','timezone':'UTC','latitude':51.4769,"
        "'longitude':-0.0005,'dashboard':{'planets':["
        "{'planet':'Sun','longitude':280.0,'house':1}]}})"
    )
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(path), f"snap-{index}"],
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        for index in range(4)
    ]
    for process in processes:
        assert process.wait(timeout=30) == 0

    store = SnapStore(str(path))
    assert {snap["id"] for snap in store.list()} == {
        "snap-0", "snap-1", "snap-2", "snap-3",
    }


def test_repeated_dst_wall_time_is_marked_ambiguous_with_both_candidates():
    context = canonical_time_context(
        "2024-11-03T01:30:00",
        "America/New_York",
        source_field="effective_datetime",
        legacy_local_wall_time=True,
    )

    assert context["ambiguous"] is True
    assert context["instant_utc"] is None
    assert context["wall_time_status"] == "ambiguous_fold"
    assert {
        row["instant_utc"] for row in context["wall_time_candidates"]
        if row["round_trip_matches"]
    } == {
        "2024-11-03T05:30:00+00:00",
        "2024-11-03T06:30:00+00:00",
    }


def test_nonexistent_dst_wall_time_is_marked_unresolved():
    context = canonical_time_context(
        "2024-03-10T02:30:00",
        "America/New_York",
        source_field="effective_datetime",
        legacy_local_wall_time=True,
    )

    assert context["ambiguous"] is True
    assert context["instant_utc"] is None
    assert context["wall_time_status"] == "nonexistent_gap"
    assert not any(
        row["round_trip_matches"] for row in context["wall_time_candidates"]
    )


def test_date_only_legacy_time_does_not_invent_midnight():
    context = canonical_time_context(
        "2002-04-05",
        "Asia/Tokyo",
        source_field="effective_datetime",
        legacy_local_wall_time=True,
    )

    assert context["ambiguous"] is True
    assert context["instant_utc"] is None
    assert context["local_datetime"] is None
    assert context["wall_time_status"] == "missing_time"
    assert context["interpretation"] == "date_only_missing_birth_time"


def test_store_does_not_publish_fold_candidate_as_effective_instant(tmp_path):
    snap = _legacy_synthetic_snap("dst-fold")
    snap.update({
        "effective_datetime": "2024-11-03T01:30:00",
        "location": "New York, NY",
        "timezone": "America/New_York",
        "timezone_label": "America/New_York (UTC+00:00)",
    })
    snap["dashboard"]["timestamp"] = "2024-11-03T01:30:00"
    snap["dashboard"]["timezone"] = "America/New_York"
    path = tmp_path / "snaps_store.json"
    path.write_text(json.dumps({"snaps": [snap]}), encoding="utf-8")

    migrated = SnapStore(str(path)).get("dst-fold")

    assert migrated["effective_datetime"] is None
    assert migrated["calculation_context"]["review_required"] is True
    assert migrated["calculation_context"]["time_provenance"]["ambiguous"] is True
