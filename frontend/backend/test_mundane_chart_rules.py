from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mundane_chart_rules import _find_aries_ingress, _find_latest_aries_ingress, _find_nearest_lunation, resolve_chart_resolution


def test_find_aries_ingress_refines_crossing():
    exact = datetime(2025, 3, 20, 9, 0, tzinfo=timezone.utc)

    def longitudes_at(dt):
        delta_days = (dt - exact).total_seconds() / 86400.0
        return {
            "Sun": (delta_days * 1.0) % 360.0,
            "Moon": 0.0,
            "North Node": 15.0,
        }

    resolved = _find_aries_ingress(datetime(2025, 3, 20, 12, 0, tzinfo=timezone.utc), longitudes_at=longitudes_at)

    assert abs((resolved - exact).total_seconds()) < 3600


def test_find_latest_aries_ingress_uses_previous_ingress_before_march(monkeypatch):
    current_year_ingress = datetime(2026, 3, 20, 9, 0, tzinfo=timezone.utc)
    previous_year_ingress = datetime(2025, 3, 20, 9, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(
        "mundane_chart_rules._cardinal_ingress_datetime",
        lambda ingress_id, year: current_year_ingress if year == 2026 else previous_year_ingress,
    )

    resolved = _find_latest_aries_ingress(datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc))

    assert resolved == previous_year_ingress


def test_find_nearest_lunation_selects_nearest_new_moon():
    anchor = datetime(2025, 3, 20, 12, 0, tzinfo=timezone.utc)
    new_moon = anchor + timedelta(days=1)
    full_moon = new_moon + timedelta(days=14)

    def longitudes_at(dt):
        phase = ((dt - new_moon).total_seconds() / 86400.0) * (180.0 / 14.0)
        return {
            "Sun": 0.0,
            "Moon": phase % 360.0,
            "North Node": 15.0,
        }

    candidate = _find_nearest_lunation(anchor, longitudes_at=longitudes_at)

    assert candidate.event_type == "new_moon"
    assert abs((candidate.exact_dt - new_moon).total_seconds()) < 3600


def test_resolve_chart_resolution_war_event_uses_event_chart_and_house_logic():
    event_dt = datetime(2025, 4, 11, 12, 0, tzinfo=timezone.utc)
    captured = {}

    def bundle_resolver(dt_iso, location, timezone_name, house_system_code, **kwargs):
        captured["latitude"] = kwargs.get("latitude")
        captured["longitude"] = kwargs.get("longitude")
        return {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
                "latitude": kwargs.get("latitude"),
                "longitude": kwargs.get("longitude"),
            },
            "chart_data": {
                "planets": {
                    "Mars": {"longitude": 15.0, "sign": "Aries", "house": 1, "retrograde": True, "speed": -0.2},
                    "Saturn": {"longitude": 195.0, "sign": "Libra", "house": 7, "retrograde": False, "speed": 0.1},
                    "Sun": {"longitude": 22.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
                    "Moon": {"longitude": 210.0, "sign": "Scorpio", "house": 7, "retrograde": False, "speed": 13.0},
                },
                "house_rulers": {"1": "Mars", "7": "Venus"},
                "houses": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
                "ascendant": 0.0,
                "midheaven": 90.0,
            },
        }

    payload = resolve_chart_resolution(
        chart_type_id="war_event",
        anchor_datetime=event_dt,
        location="Paris, France",
        timezone_name="Europe/Paris",
        house_system_code="P",
        bundle_resolver=bundle_resolver,
        event_location="Paris, France",
        event_timezone="Europe/Paris",
        event_datetime=event_dt.isoformat(),
        location_latitude=48.8566,
        location_longitude=2.3522,
    )

    assert payload["primary_chart"]["kind"] == "war_event"
    assert payload["primary_chart"]["latitude"] == 48.8566
    assert payload["primary_chart"]["longitude"] == 2.3522
    assert payload["signals"]["aggressor_house"]["ruler"] == "Mars"
    assert payload["signals"]["mars_retrograde"] is True
    assert payload["activation_items"][0]["status"] == "present"
    assert captured["latitude"] == 48.8566
    assert captured["longitude"] == 2.3522


def test_resolve_chart_resolution_eclipse_and_lunation_attach_cycle_context(monkeypatch):
    anchor = datetime(2025, 4, 11, 12, 0, tzinfo=timezone.utc)

    def bundle_resolver(dt_iso, location, timezone_name, house_system_code, **kwargs):
        return {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "chart_data": {
                "planets": {
                    "Sun": {"longitude": 10.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
                    "Moon": {"longitude": 10.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 13.0},
                    "North Node": {"longitude": 12.0, "sign": "Aries", "house": 1, "retrograde": True, "speed": -0.05},
                },
                "house_rulers": {},
                "houses": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
                "ascendant": 0.0,
                "midheaven": 90.0,
            },
        }

    monkeypatch.setattr(
        "mundane_chart_rules._jupiter_saturn_cycle_context",
        lambda dt: {
            "type": "jupiter_saturn_cycle",
            "nearest_conjunction_datetime": "2020-12-21T18:00:00+00:00",
            "nearest_distance_years": 2.8,
            "cycle_phase": "opening_cycle",
            "turning_window_active": True,
            "turning_window_level": "strong",
            "conjunction_sign": "Aquarius",
        },
    )
    monkeypatch.setattr(
        "mundane_chart_rules._find_nearest_lunation",
        lambda anchor_dt, longitudes_at: type("Candidate", (), {"event_type": "new_moon", "exact_dt": anchor_dt})(),
    )
    monkeypatch.setattr(
        "mundane_chart_rules._find_latest_aries_ingress",
        lambda anchor_dt: datetime(2025, 3, 20, 10, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        "mundane_chart_rules._active_cardinal_ingress",
        lambda anchor_dt: {
            "ingress_id": "capricorn",
            "label": "Capricorn Ingress",
            "role": "quarterly_framework",
            "computed_datetime": "2025-12-21T10:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        "mundane_chart_rules._find_nearest_eclipse",
        lambda anchor_dt, **kwargs: (
            type("Candidate", (), {"event_type": "solar_eclipse", "exact_dt": anchor_dt})(),
            bundle_resolver(anchor_dt.isoformat(), "Paris, France", "Europe/Paris", "P"),
            1.0,
        ),
    )

    lunation_payload = resolve_chart_resolution(
        chart_type_id="lunation",
        anchor_datetime=anchor,
        location="Paris, France",
        timezone_name="Europe/Paris",
        house_system_code="P",
        bundle_resolver=bundle_resolver,
    )
    eclipse_payload = resolve_chart_resolution(
        chart_type_id="eclipse",
        anchor_datetime=anchor,
        location="Paris, France",
        timezone_name="Europe/Paris",
        house_system_code="P",
        bundle_resolver=bundle_resolver,
        location_context_type="capital_chart",
        visibility_scope="national",
    )

    assert lunation_payload["cycle_context"]["conjunction_sign"] == "Aquarius"
    assert any(item["id"] == "mutation_and_conjunction_cycles" for item in lunation_payload["trigger_items"])
    assert lunation_payload["signals"]["active_quarterly_ingress"]["ingress_id"] == "capricorn"
    assert len(lunation_payload["framework_items"]) == 2
    assert eclipse_payload["cycle_context"]["cycle_phase"] == "opening_cycle"
    assert any(item["id"] == "mutation_and_conjunction_cycles" for item in eclipse_payload["trigger_items"])
    assert any(item["id"] == "eclipse_locality_proxy" for item in eclipse_payload["trigger_items"])
    assert eclipse_payload["signals"]["eclipse_locality"]["visibility_classification"] == "below_horizon_proxy"
    assert eclipse_payload["signals"]["eclipse_locality"]["territorial_relevance"] == "capital_scope"


def test_resolve_chart_resolution_aries_ingress_carries_duration_and_active_quarter(monkeypatch):
    anchor = datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(
        "mundane_chart_rules._find_latest_aries_ingress",
        lambda anchor_dt: datetime(2025, 3, 20, 10, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        "mundane_chart_rules._active_cardinal_ingress",
        lambda anchor_dt: {
            "ingress_id": "capricorn",
            "label": "Capricorn Ingress",
            "role": "quarterly_framework",
            "computed_datetime": "2025-12-21T10:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        "mundane_chart_rules._jupiter_saturn_cycle_context",
        lambda dt: None,
    )

    def bundle_resolver(dt_iso, location, timezone_name, house_system_code, **kwargs):
        return {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "chart_data": {
                "planets": {
                    "Sun": {"longitude": 0.0, "sign": "Aries", "house": 10, "retrograde": False, "speed": 1.0},
                },
                "house_rulers": {},
                "houses": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
                "ascendant": 33.0,
                "midheaven": 90.0,
            },
        }

    payload = resolve_chart_resolution(
        chart_type_id="aries_ingress",
        anchor_datetime=anchor,
        location="Washington, DC, United States",
        timezone_name="America/New_York",
        house_system_code="P",
        bundle_resolver=bundle_resolver,
    )

    assert payload["signals"]["annual_ingress_datetime"] == "2025-03-20T10:00:00+00:00"
    assert payload["signals"]["active_quarterly_ingress"]["ingress_id"] == "capricorn"
    assert payload["signals"]["framework_modality"] == "fixed"
    assert payload["signals"]["framework_duration_months"] == 12
    assert len(payload["framework_items"]) == 2
