from pathlib import Path
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import mcp_chart_service as service  # noqa: E402


JERUSALEM_CHART = {
    "datetime": "2026-08-01T14:30:00+03:00",
    "location": "Jerusalem, Israel",
    "timezone": "Asia/Jerusalem",
    "latitude": 31.778,
    "longitude": 35.235,
    "house_system_code": "R",
}


def test_calculate_chart_matches_known_engine_fixture():
    result = service.calculate_chart(JERUSALEM_CHART)

    assert result["schema_version"] == "voxstella.astrology.v1"
    assert result["calculation"]["timestamp"] == "2026-08-01T14:30:00+03:00"
    assert result["calculation"]["house_system_code"] == "R"
    assert len(result["houses"]) == 12
    assert [row["body"] for row in result["planets"]] == list(service.CLASSICAL_BODIES)
    sun = next(row for row in result["planets"] if row["body"] == "Sun")
    moon = next(row for row in result["planets"] if row["body"] == "Moon")
    assert sun["longitude"] == pytest.approx(129.24727125, abs=1e-6)
    assert moon["longitude"] == pytest.approx(342.23569154, abs=1e-6)
    assert result["angles"]["ascendant"] == pytest.approx(237.3813, abs=1e-4)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("latitude", 91, "latitude must be between"),
        ("longitude", -181, "longitude must be between"),
        ("timezone", "Mars/Olympus", "valid IANA timezone"),
        ("house_system_code", "?", "house_system_code must be one of"),
        ("bodies", ["Vulcan"], "unsupported bodies entry"),
        ("sections", ["raw_internal_state"], "unsupported sections entry"),
    ],
)
def test_calculate_chart_rejects_invalid_public_parameters(field, value, message):
    payload = dict(JERUSALEM_CHART)
    payload[field] = value
    with pytest.raises(service.McpInputError, match=message):
        service.calculate_chart(payload)


def test_calculate_chart_rejects_unknown_fields():
    with pytest.raises(service.McpInputError, match="unsupported request fields: raw_engine"):
        service.calculate_chart({**JERUSALEM_CHART, "raw_engine": True})


def test_calculate_chart_requires_explicit_coordinates_and_timezone():
    for missing in ("latitude", "longitude", "timezone"):
        payload = dict(JERUSALEM_CHART)
        payload.pop(missing)
        with pytest.raises(service.McpInputError):
            service.calculate_chart(payload)


@pytest.mark.parametrize(
    ("timestamp", "message"),
    [
        ("2026-03-08T02:30:00", "nonexistent local civil time"),
        ("2026-11-01T01:30:00", "ambiguous"),
    ],
)
def test_calculate_chart_rejects_dst_wall_time_ambiguity(timestamp, message):
    payload = {
        **JERUSALEM_CHART,
        "datetime": timestamp,
        "timezone": "America/New_York",
        "location": "New York, NY",
        "latitude": 40.7128,
        "longitude": -74.006,
    }
    with pytest.raises(service.McpInputError, match=message):
        service.calculate_chart(payload)


def test_body_selection_enables_modern_calculation_and_filters_aspects(monkeypatch):
    captured = {}

    def fake_engine_chart(**kwargs):
        captured.update(kwargs)
        return {
            "meta": {
                "timestamp": kwargs["calculation_time"].isoformat(),
                "location": kwargs["location"],
                "timezone": kwargs["timezone_name"],
                "latitude": kwargs["latitude"],
                "longitude": kwargs["longitude"],
            },
            "chart_data": {
                "house_system_code": "R",
                "planets": {
                    "Sun": {"longitude": 10, "latitude": 0, "house": 1, "speed": 1},
                    "Uranus": {"longitude": 70, "latitude": 0, "house": 3, "speed": 0.1},
                },
                "aspects": [
                    {"planet1": "Sun", "planet2": "Uranus", "aspect": "Sextile", "orb": 0},
                    {"planet1": "Sun", "planet2": "Moon", "aspect": "Square", "orb": 1},
                ],
            },
        }

    monkeypatch.setattr(service, "_engine_chart", fake_engine_chart)
    payload = {
        **JERUSALEM_CHART,
        "bodies": ["Sun", "Uranus"],
        "sections": ["planets", "aspects"],
    }
    result = service.calculate_chart(payload)

    assert captured["include_modern"] is True
    assert [row["body"] for row in result["planets"]] == ["Sun", "Uranus"]
    assert len(result["aspects"]) == 1
    assert result["aspects"][0]["body2"] == "Uranus"


def test_planetary_hours_returns_complete_versioned_day():
    result = service.calculate_planetary_hours(
        {key: value for key, value in JERUSALEM_CHART.items() if key != "house_system_code"}
    )

    assert result["schema_version"] == "voxstella.astrology.v1"
    assert result["calculation"]["date"] == "2026-08-01"
    assert len(result["hours"]) == 24
    assert [row["hour_number"] for row in result["hours"]] == list(range(1, 25))


def test_planetary_hours_sunrise_matches_requested_local_date_east_of_utc():
    result = service.calculate_planetary_hours(
        {
            "datetime": "2026-08-01T12:00:00",
            "location": "Tokyo, Japan",
            "timezone": "Asia/Tokyo",
            "latitude": 35.6762,
            "longitude": 139.6503,
        }
    )
    zone = ZoneInfo("Asia/Tokyo")
    sunrise_local = datetime.fromisoformat(result["sunrise"]).astimezone(zone)
    sunset_local = datetime.fromisoformat(result["sunset"]).astimezone(zone)

    assert sunrise_local.date().isoformat() == result["calculation"]["date"]
    assert sunset_local.date().isoformat() == result["calculation"]["date"]


def test_capabilities_declares_license_and_required_location_contract():
    result = service.capabilities_payload()

    assert result["license_required"] is True
    assert result["default_house_system_code"] == "R"
    assert result["required_location_parameters"] == ["latitude", "longitude", "timezone"]
    assert "calculate_astrological_chart" in result["tools"]
