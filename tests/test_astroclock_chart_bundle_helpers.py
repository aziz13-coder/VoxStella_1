from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.datastructures import MultiDict


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api


class _SentinelChart:
    pass


_USER_ENTERED_BIRTH_TIME_QUALITY = {
    "kind": "birth_time_quality",
    "status": "user_entered_time",
    "confidence": "user_entered",
    "source_time_status": None,
    "uncertainty_minutes": None,
    "effective_uncertainty_minutes": None,
    "search_window_minutes": None,
    "ranking_eligible": True,
    "ranking_eligibility": "provisional",
    "warnings": [
        "The birth time has not been externally certified; city ranks are provisional.",
    ],
}


def test_compute_chart_bundle_for_retains_raw_chart(monkeypatch):
    sentinel = _SentinelChart()

    class _StubEngine:
        def __init__(self):
            self.settings = types.SimpleNamespace(
                location="Jerusalem, Israel",
                timezone="UTC",
                latitude=31.778,
                longitude=35.235,
                house_system_code="R",
            )

        def get_current_data(self, settings=None):
            return types.SimpleNamespace(
                timestamp=datetime(2026, 3, 8, 0, 0, tzinfo=timezone.utc),
                chart_result={
                    "chart_data": {
                        "planets": {"Moon": {"longitude": 45.0, "sign": "Taurus", "house": 2}},
                        "house_rulers": {"1": "Moon"},
                        "aspects": [],
                    },
                    "_raw_chart": sentinel,
                },
            )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(
        astro_clock_api,
        "_resolve_timezone_for_context",
        lambda tz_name, _location, **_kwargs: tz_name or "UTC",
    )

    bundle = astro_clock_api._compute_chart_bundle_for(
        "2026-03-08T00:00:00Z",
        "Jerusalem, Israel",
        "UTC",
        house_system_code="R",
    )
    chart_data, meta = astro_clock_api._compute_chart_for(
        "2026-03-08T00:00:00Z",
        "Jerusalem, Israel",
        "UTC",
        house_system_code="R",
    )

    assert bundle["raw_chart"] is sentinel
    assert bundle["chart_data"]["house_rulers"] == {"1": "Moon"}
    assert bundle["meta"]["timezone"] == "UTC"
    assert chart_data == bundle["chart_data"]
    assert meta == bundle["meta"]
    assert "_raw_chart" not in chart_data


def test_natal_bundle_from_query_uses_manual_inputs(monkeypatch):
    sentinel = _SentinelChart()
    calls = {}

    def _fake_compute_bundle(dt_iso, location, tz_name, house_system_code=None, latitude=None, longitude=None):
        calls.update(
            {
                "dt_iso": dt_iso,
                "location": location,
                "timezone": tz_name,
                "house_system_code": house_system_code,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
        return {
            "chart_result": {"chart_data": {"house_rulers": {"10": "Mars"}}},
            "chart_data": {"house_rulers": {"10": "Mars"}},
            "meta": {"timestamp": "1990-01-01T00:00:00+00:00", "location": location, "timezone": tz_name},
            "raw_chart": sentinel,
        }

    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", _fake_compute_bundle)

    args = MultiDict(
        {
            "natal_datetime": "1990-01-01T00:00:00Z",
            "natal_location": "Jerusalem",
            "natal_timezone": "UTC",
            "house_system_code": "R",
        }
    )

    bundle = astro_clock_api._natal_bundle_from_query(args)
    chart_data, meta = astro_clock_api._natal_from_query(args)

    assert calls == {
        "dt_iso": "1990-01-01T00:00:00Z",
        "location": "Jerusalem",
        "timezone": "UTC",
        "house_system_code": "R",
        "latitude": None,
        "longitude": None,
    }
    assert bundle["raw_chart"] is sentinel
    assert chart_data == {"house_rulers": {"10": "Mars"}}
    assert meta == {
        "timestamp": "1990-01-01T00:00:00+00:00",
        "location": "Jerusalem",
        "timezone": "UTC",
        "coordinate_source": "geocoder",
        "birth_time": _USER_ENTERED_BIRTH_TIME_QUALITY,
    }


def test_natal_bundle_from_query_uses_snap_context(monkeypatch):
    sentinel = _SentinelChart()
    calls = {}

    def _fake_compute_bundle(dt_iso, location, tz_name, house_system_code=None, latitude=None, longitude=None):
        calls.update(
            {
                "dt_iso": dt_iso,
                "location": location,
                "timezone": tz_name,
                "house_system_code": house_system_code,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
        return {
            "chart_result": {"chart_data": {"house_rulers": {"1": "Moon"}}},
            "chart_data": {"house_rulers": {"1": "Moon"}},
            "meta": {"timestamp": dt_iso, "location": location, "timezone": tz_name},
            "raw_chart": sentinel,
        }

    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", _fake_compute_bundle)
    monkeypatch.setattr(
        astro_clock_api,
        "_snaps",
        lambda: {
                "snap-1": {
                    "effective_datetime": "2001-05-15T14:20:00Z",
                    "location": "Washington, District of Columbia",
                    "timezone": "America/New_York",
                    "latitude": 38.9072,
                    "longitude": -77.0369,
                }
            },
        )

    args = MultiDict({"natal_snap_id": "snap-1", "house_system_code": "R"})

    bundle = astro_clock_api._natal_bundle_from_query(args)
    chart_data, meta = astro_clock_api._natal_from_query(args)

    assert calls == {
        "dt_iso": "2001-05-15T14:20:00+00:00",
        "location": "Washington, District of Columbia",
        "timezone": "America/New_York",
        "house_system_code": "R",
        "latitude": 38.9072,
        "longitude": -77.0369,
    }
    assert bundle["raw_chart"] is sentinel
    assert chart_data == {"house_rulers": {"1": "Moon"}}
    assert meta == {
        "timestamp": "2001-05-15T14:20:00+00:00",
        "location": "Washington, District of Columbia",
        "timezone": "America/New_York",
        "coordinate_source": "saved_snap",
        "coordinate_provenance": {
            "source": "snap.latitude_longitude",
            "persisted_with_chart": True,
            "inferred_at_read_time": False,
            "legacy_shape": "snap.latitude_longitude",
            "location_specificity": "specific",
            "review_required": False,
        },
        "birth_time": _USER_ENTERED_BIRTH_TIME_QUALITY,
    }
