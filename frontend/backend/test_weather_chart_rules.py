from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import weather_chart_rules
from weather_chart_rules import SearchCandidate


def _sample_bundle():
    return {
        "meta": {
            "location": "Miami, Florida, USA",
            "timezone": "America/New_York",
            "latitude": 25.7617,
            "longitude": -80.1918,
        },
        "chart_data": {
            "ascendant": 0.0,
            "midheaven": 90.0,
            "houses": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "planets": {
                "Mercury": {
                    "longitude": 2.0,
                    "sign": "Aries",
                    "house": 1,
                    "retrograde": False,
                    "speed": 1.1,
                },
                "Uranus": {
                    "longitude": 92.0,
                    "sign": "Cancer",
                    "house": 10,
                    "retrograde": False,
                    "speed": 0.3,
                },
            },
        },
    }


def test_target_zone_intersections_pair_horizon_and_meridian_lines():
    intersections = weather_chart_rules._target_zone_intersections(_sample_bundle())

    assert len(intersections) == 1
    assert intersections[0]["horizon_planet"] == "Mercury"
    assert intersections[0]["meridian_planet"] == "Uranus"
    assert intersections[0]["combined_distance_deg"] == 4.0
    assert intersections[0]["zone"] == "primary"
    assert intersections[0]["pair_label"] == "Mercury ASCENDANT x Uranus MIDHEAVEN"


def test_resolve_weather_chart_resolution_surfaces_target_zone_signals(monkeypatch):
    monkeypatch.setattr(
        weather_chart_rules,
        "_find_latest_cardinal_ingress",
        lambda anchor_dt, *, longitudes_at: SearchCandidate(
            event_type="spring_ingress",
            label="Spring Ingress",
            exact_dt=datetime(2026, 3, 20, 9, 0, tzinfo=timezone.utc),
            target_deg=0.0,
        ),
    )
    monkeypatch.setattr(
        weather_chart_rules,
        "_find_latest_lunar_phase",
        lambda anchor_dt, *, longitudes_at: SearchCandidate(
            event_type="full_moon",
            label="Full Moon",
            exact_dt=datetime(2026, 4, 10, 1, 0, tzinfo=timezone.utc),
            target_deg=180.0,
        ),
    )

    result = weather_chart_rules.resolve_weather_chart_resolution(
        forecast_datetime=datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc),
        location="Miami, Florida, USA",
        timezone_name="America/New_York",
        house_system_code="P",
        bundle_resolver=lambda *args, **kwargs: _sample_bundle(),
    )

    forecast_signal = result["signals"]["forecast_chart"]
    locality_items = {item["id"]: item for item in result["locality_items"]}

    assert forecast_signal["target_zone_intersections"]
    assert locality_items["forecast_chart_target_zones"]["target_zone_intersections"]
    assert result["primary_chart"]["target_zone_intersections"][0]["horizon_planet"] == "Mercury"
    assert result["primary_chart"]["target_zone_intersections"][0]["meridian_planet"] == "Uranus"


def test_resolve_weather_chart_resolution_treats_naive_forecast_as_local_time(monkeypatch):
    observed_anchors = []
    observed_bundle_datetimes = []

    def fake_ingress(anchor_dt, *, longitudes_at):
        observed_anchors.append(anchor_dt)
        return SearchCandidate(
            event_type="spring_ingress",
            label="Spring Ingress",
            exact_dt=datetime(2026, 3, 20, 9, 0, tzinfo=timezone.utc),
            target_deg=0.0,
        )

    def fake_lunar(anchor_dt, *, longitudes_at):
        observed_anchors.append(anchor_dt)
        return SearchCandidate(
            event_type="full_moon",
            label="Full Moon",
            exact_dt=datetime(2026, 4, 10, 1, 0, tzinfo=timezone.utc),
            target_deg=180.0,
        )

    monkeypatch.setattr(weather_chart_rules, "_find_latest_cardinal_ingress", fake_ingress)
    monkeypatch.setattr(weather_chart_rules, "_find_latest_lunar_phase", fake_lunar)

    def fake_bundle_resolver(forecast_datetime, *args, **kwargs):
        observed_bundle_datetimes.append(forecast_datetime)
        return _sample_bundle()

    weather_chart_rules.resolve_weather_chart_resolution(
        forecast_datetime="2026-04-12T12:00:00",
        location="Miami, Florida, USA",
        timezone_name="America/New_York",
        house_system_code="P",
        bundle_resolver=fake_bundle_resolver,
    )

    expected_anchor = datetime(2026, 4, 12, 16, 0, tzinfo=timezone.utc)
    assert observed_anchors == [expected_anchor, expected_anchor]
    assert observed_bundle_datetimes[-1] == "2026-04-12T16:00:00+00:00"
