from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import os
import sys

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


def test_create_snap_persists_frozen_chart_snapshot_for_synastry(monkeypatch):
    client = app_module.app.test_client()
    store = _FakeSnapStore()
    settings = SimpleNamespace(
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        custom_time=None,
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


def test_synastry_bundle_from_snap_id_uses_persisted_chart_snapshot_without_recompute(monkeypatch):
    snap = {
        "id": "snap-a",
        "label": "Frozen Snapshot",
        "effective_datetime": "2026-04-19T11:30:00+00:00",
        "location": "Jerusalem, Israel",
        "dashboard": {
            "timestamp": "2026-04-19T11:30:00+00:00",
            "location": "Jerusalem, Israel",
            "timezone": "Asia/Jerusalem",
            "planets": _sample_planets(50.0),
            "house_cusps": [180.0 + (i * 30.0) for i in range(12)],
            "ascendant": 180.0,
            "midheaven": 270.0,
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

    bundle, chart_meta = astro_clock_api._synastry_bundle_from_snap_id("snap-a", house_system_code="W")

    assert bundle["chart_data"]["planets"][0]["longitude"] == 10.0
    assert bundle["chart_data"]["house_cusps"] == [i * 30.0 for i in range(12)]
    assert bundle["chart_data"]["ascendant"] == 15.5
    assert bundle["chart_data"]["midheaven"] == 102.2
    assert bundle["meta"]["timezone"] == "Asia/Jerusalem"
    assert chart_meta["timezone"] == "Asia/Jerusalem"


def test_synastry_bundle_from_snap_id_uses_dashboard_snapshot_for_legacy_snaps_without_recompute(monkeypatch):
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
    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore([snap]))
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_bundle_for",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("legacy dashboard snapshots should not recast")),
    )

    bundle, chart_meta = astro_clock_api._synastry_bundle_from_snap_id("snap-b", house_system_code="W")

    assert bundle["chart_data"]["planets"][0]["longitude"] == 15.0
    assert bundle["chart_data"]["house_cusps"] == [5.0 + (i * 30.0) for i in range(12)]
    assert bundle["chart_data"]["ascendant"] == 5.0
    assert bundle["meta"]["timezone"] == "Europe/London"
    assert chart_meta["location"] == "London, UK"


def test_synastry_bundle_from_snap_id_recomputes_only_when_no_saved_snapshot_exists(monkeypatch):
    snap = {
        "id": "snap-c",
        "label": "Recompute Fallback",
        "effective_datetime": "2026-04-17T07:15:00+00:00",
        "location": "Paris, France",
        "dashboard": {
            "timezone": "Europe/Paris",
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
