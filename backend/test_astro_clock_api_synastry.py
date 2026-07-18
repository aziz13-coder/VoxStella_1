from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import os
import sys

import pytest

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api


def _sample_planets(offset: float = 0.0):
    return [
        {"planet": "Sun", "longitude": 10.0 + offset, "sign": "Aries", "house": 1},
        {"planet": "Moon", "longitude": 42.0 + offset, "sign": "Taurus", "house": 2},
        {"planet": "Venus", "longitude": 77.0 + offset, "sign": "Gemini", "house": 3},
    ]


class _FakeSnapStore:
    def __init__(self, snaps=None):
        self._snaps = {str(item.get("id")): item for item in (snaps or []) if isinstance(item, dict)}
        self.added = None

    def get(self, snap_id):
        return self._snaps.get(str(snap_id))

    def add(self, snap):
        self.added = snap
        self._snaps[str(snap.get("id"))] = snap

    def add_replacement(self, original_id, replacement):
        original = self._snaps[str(original_id)]
        original["superseded_by"] = replacement["id"]
        replacement["supersedes"] = original_id
        self._snaps[str(replacement["id"])] = replacement
        return replacement


def test_create_snap_persists_frozen_chart_snapshot_for_synastry(monkeypatch):
    client = app_module.app.test_client()
    store = _FakeSnapStore()
    settings = SimpleNamespace(
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        custom_time=None,
        paused_at=None,
        mode=astro_clock_api.ClockMode.REALTIME,
        house_system_code="R",
    )
    chart_data = {
        "ascendant": 15.5,
        "midheaven": 102.2,
        "houses": [i * 30.0 for i in range(12)],
        "planets": _sample_planets(),
    }
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 19, 11, 30, tzinfo=timezone.utc),
        settings=settings,
        chart_result={"chart_data": chart_data},
    )
    eng = SimpleNamespace(settings=settings, get_current_data=lambda: data)

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: eng)
    monkeypatch.setattr(
        astro_clock_api,
        "_build_dashboard_payload",
        lambda *_args, **_kwargs: {
            "timestamp": data.timestamp.isoformat(),
            "location": settings.location,
            "timezone": settings.timezone,
            "planets": _sample_planets(),
            "ascendant": 15.5,
            "midheaven": 102.2,
            "house_cusps": [i * 30.0 for i in range(12)],
        },
    )
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda _dash: {})
    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: store)

    response = client.post("/api/astro-clock/snap", json={"label": "Frozen Pair"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert store.added is not None
    assert store.added["label"] == "Frozen Pair"
    assert store.added["chart_snapshot"]["planets"][0]["planet"] == "Sun"
    assert store.added["chart_snapshot"]["house_cusps"] == [i * 30.0 for i in range(12)]
    assert store.added["chart_snapshot"]["ascendant"] == 15.5
    assert store.added["chart_snapshot"]["midheaven"] == 102.2


def test_create_snap_persists_birth_certification_metadata(monkeypatch):
    client = app_module.app.test_client()
    store = _FakeSnapStore()
    settings = SimpleNamespace(
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        custom_time=None,
        paused_at=None,
        mode=astro_clock_api.ClockMode.REALTIME,
        house_system_code="R",
        latitude=31.778,
        longitude=35.235,
    )
    chart_data = {
        "ascendant": 15.5,
        "midheaven": 102.2,
        "houses": [i * 30.0 for i in range(12)],
        "planets": _sample_planets(),
    }
    data = SimpleNamespace(
        timestamp=datetime(1990, 1, 1, 4, 32, tzinfo=timezone.utc),
        settings=settings,
        chart_result={"chart_data": chart_data},
    )
    eng = SimpleNamespace(settings=settings, get_current_data=lambda settings=None: data)

    certification = {
        "kind": "birth_time_certification",
        "status": "rectified_candidate",
        "confidence": "medium",
        "selected_candidate": {
            "timestamp": "1990-01-01T06:32:00+02:00",
            "strength": 91.2,
            "time_offset_minutes": 2,
        },
        "data_quality": {"event_count": 1},
    }

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: eng)
    monkeypatch.setattr(
        astro_clock_api,
        "_build_dashboard_payload",
        lambda *_args, **_kwargs: {
            "timestamp": data.timestamp.isoformat(),
            "location": settings.location,
            "timezone": settings.timezone,
            "planets": _sample_planets(),
            "ascendant": 15.5,
            "midheaven": 102.2,
            "house_cusps": [i * 30.0 for i in range(12)],
        },
    )
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda _dash: {})
    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: store)

    response = client.post(
        "/api/astro-clock/snap",
        json={
            "label": "Certification - Jan 01, 1990, 06:32 AM",
            "mode": "manual",
            "datetime": "1990-01-01T06:32:00+02:00",
            "location": "Jerusalem, Israel",
            "timezone": "Asia/Jerusalem",
            "latitude": 31.778,
            "longitude": 35.235,
            "house_system_code": "R",
            "certification": certification,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert store.added is not None
    assert store.added["certification"]["status"] == "rectified_candidate"
    assert store.added["dashboard"]["certification"]["selected_candidate"]["strength"] == 91.2
    assert store.added["summary"]["certification"] == {
        "kind": "birth_time_certification",
        "status": "rectified_candidate",
        "confidence": "medium",
        "strength": 91.2,
    }


def test_synastry_bundle_from_snap_id_uses_persisted_chart_snapshot_without_recompute(monkeypatch):
    snap = {
        "schema_version": 2,
        "id": "snap-a",
        "label": "Frozen Snapshot",
        "effective_datetime": "2026-04-19T11:30:00+00:00",
        "location": "Jerusalem, Israel",
        "timezone": "Asia/Jerusalem",
        "latitude": 31.778,
        "longitude": 35.235,
        "coordinate_provenance": {
            "source": "user_confirmed_context_override",
            "persisted_with_chart": True,
            "review_required": False,
        },
        "dashboard": {
            "timestamp": "2026-04-19T11:30:00+00:00",
            "location": "Jerusalem, Israel",
            "timezone": "Asia/Jerusalem",
        },
        "chart_snapshot": {
            "planets": _sample_planets(),
            "house_cusps": [i * 30.0 for i in range(12)],
            "ascendant": 15.5,
            "midheaven": 102.2,
        },
    }
    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore([snap]))
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_bundle_for",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("synastry should not recast saved snapshots")),
    )

    bundle, chart_meta = astro_clock_api._synastry_bundle_from_snap_id("snap-a")

    assert bundle["chart_data"]["planets"][0]["longitude"] == 10.0
    assert bundle["chart_data"]["house_cusps"] == [i * 30.0 for i in range(12)]
    assert bundle["chart_data"]["ascendant"] == 15.5
    assert bundle["chart_data"]["midheaven"] == 102.2
    assert bundle["meta"]["timezone"] == "Asia/Jerusalem"
    assert chart_meta["timezone"] == "Asia/Jerusalem"


def test_synastry_rejects_frozen_legacy_chart_without_saved_coordinates(monkeypatch):
    snap = {
        "id": "snap-b",
        "label": "Legacy Dashboard Snapshot",
        "effective_datetime": "2026-04-18T08:00:00+00:00",
        "location": "London, UK",
        "dashboard": {
            "timestamp": "2026-04-18T08:00:00+00:00",
            "location": "London, UK",
            "timezone": "Europe/London",
            "planets": _sample_planets(5.0),
            "house_cusps": [5.0 + (i * 30.0) for i in range(12)],
            "ascendant": 5.0,
            "midheaven": 95.0,
        },
    }
    geocode_calls = []

    def _fake_geocode(location, *_args, **_kwargs):
        geocode_calls.append(location)
        return 51.5074, -0.1278, "London, UK"

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore([snap]))
    monkeypatch.setattr(astro_clock_api, "safe_geocode", _fake_geocode)
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_bundle_for",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("legacy dashboard snapshots should not recast")),
    )

    with pytest.raises(ValueError, match="Confirm/correct the saved context first"):
        astro_clock_api._synastry_bundle_from_snap_id(
            "snap-b",
            house_system_code="W",
        )
    assert geocode_calls == []


def test_synastry_route_compares_saved_snapshot_coords_without_geocoding(monkeypatch):
    client = app_module.app.test_client()
    snaps = [
        {
            "id": "snap-a",
            "label": "Jerusalem Subject",
            "effective_datetime": "2026-04-18T08:00:00+00:00",
            "location": "Jerusalem, Israel",
            "latitude": 31.778,
            "longitude": 35.235,
            "dashboard": {
                "timestamp": "2026-04-18T08:00:00+00:00",
                "location": "Jerusalem, Israel",
                "timezone": "Asia/Jerusalem",
                "planets": _sample_planets(),
                "house_cusps": [i * 30.0 for i in range(12)],
                "ascendant": 15.5,
                "midheaven": 102.2,
            },
        },
        {
            "id": "snap-b",
            "label": "London Subject",
            "effective_datetime": "2026-04-18T08:00:00+00:00",
            "location": "London, UK",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "dashboard": {
                "timestamp": "2026-04-18T08:00:00+00:00",
                "location": "London, UK",
                "timezone": "Europe/London",
                "planets": _sample_planets(5.0),
                "house_cusps": [5.0 + (i * 30.0) for i in range(12)],
                "ascendant": 5.0,
                "midheaven": 95.0,
            },
        },
    ]
    captured = {}

    def _unexpected_geocode(*_args, **_kwargs):
        raise AssertionError("saved synastry snapshots should not geocode")

    def _fake_report(bundle_a, bundle_b, chart_a, chart_b, **_kwargs):
        captured["bundle_a_meta"] = bundle_a.get("meta") or {}
        captured["bundle_b_meta"] = bundle_b.get("meta") or {}
        captured["chart_a"] = chart_a
        captured["chart_b"] = chart_b
        return {
            "report_kind": "memo",
            "summary": {"headline": "Compared from saved charts"},
        }

    import synastry_multi_engine

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore(snaps))
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", _unexpected_geocode)
    monkeypatch.setattr(astro_clock_api, "_synastry_point_capability", lambda _meta: {"modern_supported": False, "chiron_supported": False})
    monkeypatch.setattr(astro_clock_api, "_extend_chart_data_for_synastry", lambda chart_data, _meta, **_kwargs: chart_data)
    monkeypatch.setattr(synastry_multi_engine, "build_synastry_engine_report", _fake_report)

    response = client.get(
        "/api/astro-clock/synastry",
        query_string={"snap_a_id": "snap-a", "snap_b_id": "snap-b", "engine_id": "memo"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["summary"]["headline"] == "Compared from saved charts"
    assert captured["chart_a"]["location"] == "Jerusalem, Israel"
    assert captured["chart_b"]["location"] == "London, UK"
    assert captured["bundle_a_meta"]["timezone"] == "Asia/Jerusalem"
    assert captured["bundle_b_meta"]["timezone"] == "Europe/London"


def test_synastry_bundle_from_snap_id_recomputes_only_when_no_saved_snapshot_exists(monkeypatch):
    snap = {
        "id": "snap-c",
        "label": "Recompute Fallback",
        "effective_datetime": "2026-04-17T07:15:00+00:00",
        "location": "Paris, France",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "dashboard": {
            "timezone": "Europe/Paris",
            "latitude": 48.8566,
            "longitude": 2.3522,
        },
    }
    captured = {}

    def _fake_compute(dt_iso, location, timezone_name, house_system_code=None, **_kwargs):
        captured["args"] = (dt_iso, location, timezone_name, house_system_code)
        return {
            "chart_result": {},
            "chart_data": {
                "planets": _sample_planets(2.0),
                "house_cusps": [2.0 + (i * 30.0) for i in range(12)],
                "ascendant": 2.0,
                "midheaven": 92.0,
            },
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "raw_chart": None,
        }

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore([snap]))
    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", _fake_compute)

    bundle, chart_meta = astro_clock_api._synastry_bundle_from_snap_id("snap-c", house_system_code="W")

    assert captured["args"] == (
        "2026-04-17T07:15:00+00:00",
        "Paris, France",
        "Europe/Paris",
        "W",
    )
    assert bundle["chart_data"]["ascendant"] == 2.0
    assert chart_meta["timezone"] == "Europe/Paris"


def test_synastry_recast_rejects_saved_context_without_confirmed_coordinates(
    monkeypatch,
):
    snap = {
        "id": "legacy-no-coordinates",
        "label": "Legacy no coordinates",
        "effective_datetime": "2026-04-17T07:15:00+00:00",
        "location": "Paris, France",
        "timezone": "Europe/Paris",
        "dashboard": {},
    }
    monkeypatch.setattr(
        astro_clock_api,
        "_snaps",
        lambda: _FakeSnapStore([snap]),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_bundle_for",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("uncertain saved context must be rejected before recasting")
        ),
    )

    with pytest.raises(ValueError, match="Confirm/correct the saved context first"):
        astro_clock_api._synastry_bundle_from_snap_id("legacy-no-coordinates")


def test_review_required_legacy_chart_is_rejected_by_synastry_api_path(monkeypatch):
    snap = {
        "id": "legacy-greece",
        "effective_datetime": "2001-02-03T14:15:00",
        "location": "greece",
        "timezone": "Europe/Athens",
        "timezone_label": "Europe/Athens (UTC+00:00)",
        "coords": [39.0, 22.0],
        "dashboard": {
            "timestamp": "2001-02-03T14:15:00",
            "timezone": "Europe/Athens",
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
    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore([snap]))
    monkeypatch.setattr(
        astro_clock_api,
        "_legacy_snap_coords_from_location",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("saved legacy coords must win before geocoding")
        ),
    )

    with pytest.raises(ValueError, match="Confirm/correct the saved context first"):
        astro_clock_api._synastry_bundle_from_snap_id("legacy-greece")


def test_modern_synastry_points_use_migrated_synthetic_utc_instant():
    chart = {
        "planets": [{"planet": "Sun", "longitude": 314.0, "house": 4}],
        "house_cusps": [
            172.32, 198.76, 228.27, 261.85, 295.72, 325.69,
            352.32, 18.76, 48.27, 81.85, 115.72, 145.69,
        ],
    }
    meta = {
        "timestamp": "2001-02-03T12:15:00+00:00",
        "calculation_context": {
            "instant_utc": "2001-02-03T12:15:00+00:00",
            "time_provenance": {"ambiguous": False},
        },
    }

    extended = astro_clock_api._extend_chart_data_for_synastry(
        chart,
        meta,
        include_modern=True,
        include_chiron=False,
    )
    uranus = next(
        row for row in extended["planets"]
        if row.get("planet") == "Uranus"
    )

    assert uranus["longitude"] == pytest.approx(320.4694435, abs=0.0005)


def test_ambiguous_naive_synastry_timestamp_blocks_point_augmentation():
    chart = {
        "planets": [{"planet": "Sun", "longitude": 10.0, "house": 1}],
        "house_cusps": [i * 30.0 for i in range(12)],
    }

    extended = astro_clock_api._extend_chart_data_for_synastry(
        chart,
        {"timestamp": "2024-11-03T01:30:00"},
        include_modern=True,
        include_chiron=True,
    )

    assert [row["planet"] for row in extended["planets"]] == ["Sun"]


def test_strict_manual_datetime_rejects_dst_fold_and_gap_with_candidates():
    with pytest.raises(astro_clock_api.LocalTimeResolutionError) as fold_exc:
        astro_clock_api._normalize_manual_datetime(
            "2024-11-03T01:30:00",
            timezone_name="America/New_York",
            location="New York, NY",
        )

    assert fold_exc.value.code == "ambiguous_local_time"
    assert {
        row["utc_offset"] for row in fold_exc.value.to_payload()["candidates"]
        if row["valid"]
    } == {"-04:00", "-05:00"}

    with pytest.raises(astro_clock_api.LocalTimeResolutionError) as gap_exc:
        astro_clock_api._normalize_manual_datetime(
            "2024-03-10T02:30:00",
            timezone_name="America/New_York",
            location="New York, NY",
        )

    assert gap_exc.value.code == "nonexistent_local_time"
    assert not any(
        row["valid"] for row in gap_exc.value.to_payload()["candidates"]
    )


def test_confirmed_local_datetime_accepts_both_fold_offsets_and_rejects_wrong_one():
    first = astro_clock_api._strict_confirmed_local_time_context(
        "2024-11-03T01:30:00-04:00",
        "America/New_York",
    )
    second = astro_clock_api._strict_confirmed_local_time_context(
        "2024-11-03T01:30:00-05:00",
        "America/New_York",
    )

    assert first["instant_utc"] == "2024-11-03T05:30:00+00:00"
    assert first["selected_fold"] == 0
    assert second["instant_utc"] == "2024-11-03T06:30:00+00:00"
    assert second["selected_fold"] == 1

    with pytest.raises(astro_clock_api.LocalTimeResolutionError) as wrong_exc:
        astro_clock_api._strict_confirmed_local_time_context(
            "2024-11-03T01:30:00-06:00",
            "America/New_York",
        )

    assert wrong_exc.value.code == "timezone_offset_mismatch"
    assert {
        row["utc_offset"] for row in wrong_exc.value.to_payload()["candidates"]
        if row["valid"]
    } == {"-04:00", "-05:00"}


def test_confirm_context_route_reports_bad_offset_date_only_and_accepts_explicit_utc(
    monkeypatch,
):
    client = app_module.app.test_client()
    legacy = {
        "id": "legacy-time-contract",
        "label": "Legacy time contract",
        "effective_datetime": "2000-01-01T12:00:00",
        "location": "Greece",
        "timezone": "Europe/Athens",
        "coords": [39.0, 22.0],
        "dashboard": {},
    }
    store = _FakeSnapStore([legacy])
    captured = {}

    def _fake_compute(dt_iso, location, timezone_name, **kwargs):
        captured.update({
            "dt_iso": dt_iso,
            "location": location,
            "timezone": timezone_name,
            **kwargs,
        })
        return {
            "chart_data": {
                "planets": [
                    {"planet": "Moon", "longitude": 10.0, "sign": "Aries", "house": 1},
                ],
                "houses": [i * 30.0 for i in range(12)],
            },
            "meta": {},
        }

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: store)
    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", _fake_compute)
    base = {
        "location": "Athens, Greece",
        "latitude": 37.9838,
        "longitude": 23.7275,
        "persist": False,
    }

    mismatch = client.post(
        "/api/astro-clock/snaps/legacy-time-contract/confirm-context",
        json={
            **base,
            "local_datetime": "2001-02-03T14:15:00+00:00",
            "timezone": "Europe/Athens",
        },
    )
    mismatch_payload = mismatch.get_json()
    assert mismatch.status_code == 400
    assert mismatch_payload["error_code"] == "timezone_offset_mismatch"
    assert mismatch_payload["time_resolution"]["candidates"][0]["utc_offset"] == "+02:00"

    date_only = client.post(
        "/api/astro-clock/snaps/legacy-time-contract/confirm-context",
        json={
            **base,
            "local_datetime": "2001-02-03",
            "timezone": "Europe/Athens",
        },
    )
    assert date_only.status_code == 400
    assert date_only.get_json()["error_code"] == "missing_local_time"

    utc_response = client.post(
        "/api/astro-clock/snaps/legacy-time-contract/confirm-context",
        json={
            **base,
            "local_datetime": "2000-01-01T12:00:00+00:00",
            "timezone": "UTC",
            "location": "Greenwich, UK",
            "latitude": 51.4769,
            "longitude": 0.0,
        },
    )

    assert utc_response.status_code == 200
    assert utc_response.get_json()["success"] is True
    assert captured["dt_iso"] == "2000-01-01T12:00:00+00:00"
    assert captured["timezone"] == "UTC"


@pytest.mark.parametrize(
    "location",
    [
        "Israel",
        "California, United States",
        "Greater London, England, UK",
    ],
)
def test_confirm_context_rejects_broad_location_even_with_coordinates(
    monkeypatch,
    location,
):
    client = app_module.app.test_client()
    legacy = {
        "id": "legacy-broad-location",
        "label": "Broad legacy location",
        "effective_datetime": "2000-01-01T12:00:00+00:00",
        "location": location,
        "timezone": "UTC",
        "coords": [31.76904, 35.21633],
        "dashboard": {},
    }
    store = _FakeSnapStore([legacy])
    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: store)
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_bundle_for",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("broad locations must be rejected before chart computation")
        ),
    )

    response = client.post(
        "/api/astro-clock/snaps/legacy-broad-location/confirm-context",
        json={
            "local_datetime": "2000-01-01T12:00:00+00:00",
            "timezone": "UTC",
            "location": location,
            "latitude": 31.76904,
            "longitude": 35.21633,
            "persist": True,
        },
    )

    assert response.status_code == 400
    assert "specific city or place" in response.get_json()["error"]
    assert "superseded_by" not in store.get("legacy-broad-location")


def test_confirm_context_route_previews_then_preserves_original_on_persist(monkeypatch):
    client = app_module.app.test_client()
    legacy = {
        "id": "legacy-athens",
        "label": "Synthetic legacy Greece chart",
        "effective_datetime": "2001-02-03T14:15:00",
        "location": "greece",
        "timezone": "Europe/Athens",
        "coords": [39.0, 22.0],
        "special_degrees": ["old-chart-degree"],
        "profile_hint": "masculine",
        "certification": {
            "kind": "birth_time_certification",
            "status": "certified",
            "confidence": "high",
        },
        "summary": {
            "hour_ruler": "Saturn",
            "moon_sign": "Cancer",
            "chart_sect": "Nocturnal",
            "sect_light": "Moon",
            "profile_hint": "masculine",
            "certification": {"status": "certified"},
        },
        "dashboard": {
            "timestamp": "2001-02-03T14:15:00",
            "timezone": "Europe/Athens",
            "planets": [{"planet": "Moon", "longitude": 75.0, "house": 12}],
            "house_cusps": [i * 30.0 for i in range(12)],
        },
    }
    store = _FakeSnapStore([legacy])
    captured = {}

    def _fake_compute(dt_iso, location, timezone_name, **kwargs):
        captured.update({
            "dt_iso": dt_iso,
            "location": location,
            "timezone": timezone_name,
            **kwargs,
        })
        return {
            "chart_data": {
                "planets": [
                    {"planet": "Moon", "longitude": 75.0, "house": 11},
                    {"planet": "Uranus", "longitude": 320.4694, "house": 4},
                ],
                "houses": [10.0 + i * 30.0 for i in range(12)],
                "ascendant": 10.0,
                "midheaven": 280.0,
                "house_rulers": {"1": "Mars"},
            },
            "meta": {},
        }

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: store)
    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", _fake_compute)
    monkeypatch.setattr(
        astro_clock_api,
        "compute_sect_info",
        lambda _chart: {"chart_sect": "Diurnal", "sect_light": "Sun"},
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_ph_instance",
        lambda *_args: SimpleNamespace(
            get_current_planetary_hour=lambda _dt: SimpleNamespace(
                ruling_planet=SimpleNamespace(value="Venus")
            )
        ),
    )
    body = {
        "local_datetime": "2001-02-03T14:15:00",
        "timezone": "Europe/Athens",
        "location": "Athens, Greece",
        "latitude": 37.9838,
        "longitude": 23.7275,
        "house_system_code": "R",
        "include_modern": True,
        "include_chiron": True,
    }

    preview_response = client.post(
        "/api/astro-clock/snaps/legacy-athens/confirm-context",
        json={**body, "persist": False},
    )
    preview = preview_response.get_json()["data"]

    assert preview_response.status_code == 200
    assert preview["persisted"] is False
    assert "superseded_by" not in store.get("legacy-athens")
    assert captured["dt_iso"] == "2001-02-03T12:15:00+00:00"
    assert captured["latitude"] == pytest.approx(37.9838)
    assert captured["longitude"] == pytest.approx(23.7275)
    assert preview["replacement"]["local_datetime"] == "2001-02-03T14:15:00+02:00"
    assert preview["replacement"]["special_degrees"] == ["old-chart-degree"]
    assert preview["replacement"]["summary"]["hour_ruler"] == "Venus"
    assert preview["replacement"]["summary"]["moon_sign"] == "Gemini"
    assert preview["replacement"]["summary"]["chart_sect"] == "Diurnal"
    assert preview["replacement"]["summary"]["sect_light"] == "Sun"
    assert preview["replacement"]["summary"]["profile_hint"] == "masculine"
    assert preview["replacement"]["profile_hint"] == "masculine"
    assert "certification" not in preview["replacement"]
    assert preview["replacement"]["recast_provenance"]["invalidated_fields"] == {
        "certification": "not carried because the certified birth context changed",
    }
    assert store.get("legacy-athens")["special_degrees"] == ["old-chart-degree"]
    assert store.get("legacy-athens")["certification"]["status"] == "certified"
    preview_moon = next(
        row for row in preview["replacement"]["chart_snapshot"]["planets"]
        if row["planet"] == "Moon"
    )
    assert preview_moon["house"] == 11

    persist_response = client.post(
        "/api/astro-clock/snaps/legacy-athens/confirm-context",
        json={**body, "persist": True},
    )
    persisted = persist_response.get_json()["data"]

    assert persist_response.status_code == 200
    assert persisted["persisted"] is True
    replacement_id = persisted["replacement"]["id"]
    assert store.get("legacy-athens")["superseded_by"] == replacement_id
    assert store.get(replacement_id)["supersedes"] == "legacy-athens"
