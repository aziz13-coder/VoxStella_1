from datetime import datetime, timezone
from pathlib import Path
from copy import deepcopy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import weather_service
from mundane_models import ActiveClockContext


def _clock_context() -> ActiveClockContext:
    return ActiveClockContext(
        timestamp=datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc).isoformat(),
        location="Miami, Florida, USA",
        timezone="America/New_York",
        mode="manual",
        house_system_code="P",
        latitude=25.7617,
        longitude=-80.1918,
    )


def _sample_resolution_payload():
    return {
        "status": "computed",
        "primary_chart": {
            "label": "Forecast Chart",
            "kind": "forecast_chart",
            "computed_datetime": "2026-04-12T12:00:00+00:00",
            "location": "Miami, Florida, USA",
            "timezone": "America/New_York",
            "planets": {
                "Mercury": {
                    "longitude": 12.0,
                    "sign": "Aries",
                    "house": 10,
                    "retrograde": False,
                    "closest_angle": "midheaven",
                    "angle_distance_deg": 1.2,
                },
                "Uranus": {
                    "longitude": 101.0,
                    "sign": "Cancer",
                    "house": 7,
                    "retrograde": False,
                    "closest_angle": "descendant",
                    "angle_distance_deg": 2.4,
                },
                "Moon": {
                    "longitude": 210.0,
                    "sign": "Scorpio",
                    "house": 1,
                    "retrograde": False,
                    "closest_angle": "ascendant",
                    "angle_distance_deg": 3.0,
                },
            },
        },
        "supporting_charts": [
            {
                "label": "Spring Ingress",
                "kind": "spring_ingress",
                "computed_datetime": "2026-03-20T09:00:00+00:00",
                "location": "Miami, Florida, USA",
                "timezone": "America/New_York",
                "planets": {
                    "Mercury": {
                        "longitude": 14.0,
                        "sign": "Aries",
                        "house": 10,
                        "retrograde": False,
                        "closest_angle": "midheaven",
                        "angle_distance_deg": 2.0,
                    }
                },
            },
            {
                "label": "Full Moon",
                "kind": "full_moon",
                "computed_datetime": "2026-04-10T01:00:00+00:00",
                "location": "Miami, Florida, USA",
                "timezone": "America/New_York",
                "planets": {
                    "Mercury": {
                        "longitude": 10.0,
                        "sign": "Aries",
                        "house": 10,
                        "retrograde": False,
                        "closest_angle": "midheaven",
                        "angle_distance_deg": 3.0,
                    },
                    "Uranus": {
                        "longitude": 100.0,
                        "sign": "Cancer",
                        "house": 7,
                        "retrograde": False,
                        "closest_angle": "descendant",
                        "angle_distance_deg": 4.0,
                    },
                },
            },
        ],
        "signals": {},
        "framework_items": [],
        "trigger_items": [],
        "locality_items": [],
        "research_flags": ["seed_runtime", "locality_proxy_only", "benchmark_backed"],
        "source_tags": ["riske", "watters"],
    }


def test_weather_runtime_catalog_lists_seed_families():
    payload = weather_service.get_runtime_catalog()

    family_ids = {row["id"] for row in payload["families"]}
    assert "flood_risk" in family_ids
    assert "hurricane_pressure" in family_ids
    assert "severe_convective_pressure" in family_ids
    assert "wind_event_pressure" in family_ids
    assert payload["runtime_status"] == "seed_runtime"
    assert payload["eclipse_decision"]["status"] == "deferred"
    assert payload["graduation_decision"]["decision"] == "no_new_runtime_families"


def test_weather_resolve_and_analyze_seed_runtime(monkeypatch):
    monkeypatch.setattr(weather_service, "resolve_weather_chart_resolution", lambda **_: _sample_resolution_payload())

    request_model = weather_service.build_weather_request({"family_id": "wind_event_pressure"})
    resolved = weather_service.resolve_weather_context(
        request_model,
        active_clock=_clock_context(),
        bundle_resolver=lambda *args, **kwargs: {},
    )
    analysis = weather_service.analyze_weather_context(resolved)
    payload = analysis.to_dict()

    assert resolved.family["id"] == "wind_event_pressure"
    assert resolved.event_context["location"] == "Miami, Florida, USA"
    assert payload["context"]["event_context"]["timezone"] == "America/New_York"
    assert payload["family_assessment"]["family_id"] == "wind_event_pressure"
    assert payload["family_assessment"]["score"] > 0
    assert payload["family_assessment"]["raw_score"] >= payload["family_assessment"]["score"]
    assert payload["framework_layer"]["label"] == "Seasonal Framework"
    assert payload["trigger_layer"]["label"] == "Lunar Trigger"
    assert payload["locality_layer"]["label"] == "Locality Proxy"
    assert payload["research"]["runtime_scope"] == "seed_weather_runtime"
    assert "seed_runtime" in payload["research"]["flags"]
    assert "eclipse_runtime_deferred" in payload["research"]["flags"]
    assert payload["family_assessment"]["signals"]["locality_strength"] >= 0


def test_weather_context_preserves_explicit_zero_coordinates(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        weather_service,
        "resolve_weather_chart_resolution",
        lambda **kwargs: captured.update(kwargs) or _sample_resolution_payload(),
    )

    request_model = weather_service.build_weather_request(
        {
            "family_id": "wind_event_pressure",
            "location": "Gulf of Guinea",
            "timezone": "UTC",
            "latitude": 0,
            "longitude": 0,
        }
    )
    resolved = weather_service.resolve_weather_context(
        request_model,
        active_clock=_clock_context(),
        bundle_resolver=lambda *args, **kwargs: {},
    )

    assert captured["latitude"] == 0.0
    assert captured["longitude"] == 0.0
    assert resolved.event_context["latitude"] == 0.0
    assert resolved.event_context["longitude"] == 0.0


def test_weather_wind_runtime_uses_retrograde_and_aspect_reinforcements(monkeypatch):
    payload = _sample_resolution_payload()
    payload["primary_chart"]["planets"]["Mercury"]["retrograde"] = True
    payload["primary_chart"]["planets"]["Mars"] = {
        "longitude": 72.0,
        "sign": "Gemini",
        "house": 7,
        "retrograde": False,
        "closest_angle": "descendant",
        "angle_distance_deg": 2.1,
    }
    monkeypatch.setattr(weather_service, "resolve_weather_chart_resolution", lambda **_: payload)

    request_model = weather_service.build_weather_request({"family_id": "wind_event_pressure"})
    resolved = weather_service.resolve_weather_context(
        request_model,
        active_clock=_clock_context(),
        bundle_resolver=lambda *args, **kwargs: {},
    )
    analysis = weather_service.analyze_weather_context(resolved).to_dict()
    labels = [item["label"] for item in analysis["family_assessment"]["matched_rules"]]

    assert "Mercury retrograde wind amplifier" in labels
    assert "Mercury-Mars wind/gust signature" in labels


def test_weather_wind_runtime_uses_mercury_bridge_timing(monkeypatch):
    payload = deepcopy(_sample_resolution_payload())
    payload["primary_chart"]["planets"]["Mercury"]["speed"] = 0.12
    payload["supporting_charts"][0]["planets"]["Mercury"]["retrograde"] = True
    payload["supporting_charts"][0]["planets"]["Mercury"]["speed"] = -0.18
    payload["supporting_charts"][1]["planets"]["Mercury"]["speed"] = 0.19
    monkeypatch.setattr(weather_service, "resolve_weather_chart_resolution", lambda **_: payload)

    request_model = weather_service.build_weather_request({"family_id": "wind_event_pressure"})
    resolved = weather_service.resolve_weather_context(
        request_model,
        active_clock=_clock_context(),
        bundle_resolver=lambda *args, **kwargs: {},
    )
    analysis = weather_service.analyze_weather_context(resolved).to_dict()
    labels = [item["label"] for item in analysis["family_assessment"]["matched_rules"]]
    signals = analysis["family_assessment"]["signals"]

    assert "Forecast Mercury bridge to seasonal ingress" in labels
    assert "Forecast Mercury bridge to lunar phase" in labels
    assert "Retrograde Mercury bridge amplifier" in labels
    assert "Stationing Mercury bridge amplifier" in labels
    assert signals["path_concentration"] >= 8


def test_weather_flood_runtime_uses_accumulation_and_tight_water_concentration(monkeypatch):
    payload = deepcopy(_sample_resolution_payload())
    payload["primary_chart"]["planets"] = {
        "Moon": {
            "longitude": 210.0,
            "sign": "Scorpio",
            "house": 3,
            "retrograde": False,
            "closest_angle": "imum_coeli",
            "angle_distance_deg": 2.8,
        },
        "Neptune": {
            "longitude": 332.0,
            "sign": "Pisces",
            "house": 4,
            "retrograde": True,
            "closest_angle": "imum_coeli",
            "angle_distance_deg": 5.1,
        },
    }
    payload["supporting_charts"] = [
        {
            "label": "Spring Ingress",
            "kind": "spring_ingress",
            "computed_datetime": "2026-03-20T09:00:00+00:00",
            "location": "Miami, Florida, USA",
            "timezone": "America/New_York",
            "planets": {
                "Moon": {
                    "longitude": 208.0,
                    "sign": "Scorpio",
                    "house": 10,
                    "retrograde": False,
                    "closest_angle": "midheaven",
                    "angle_distance_deg": 7.5,
                }
            },
        },
        {
            "label": "Full Moon",
            "kind": "full_moon",
            "computed_datetime": "2026-04-10T01:00:00+00:00",
            "location": "Miami, Florida, USA",
            "timezone": "America/New_York",
            "planets": {
                "Venus": {
                    "longitude": 15.0,
                    "sign": "Aries",
                    "house": 7,
                    "retrograde": False,
                    "closest_angle": "descendant",
                    "angle_distance_deg": 4.3,
                }
            },
        },
    ]
    monkeypatch.setattr(weather_service, "resolve_weather_chart_resolution", lambda **_: payload)

    request_model = weather_service.build_weather_request({"family_id": "flood_risk"})
    resolved = weather_service.resolve_weather_context(
        request_model,
        active_clock=_clock_context(),
        bundle_resolver=lambda *args, **kwargs: {},
    )
    analysis = weather_service.analyze_weather_context(resolved).to_dict()
    labels = [item["label"] for item in analysis["family_assessment"]["matched_rules"]]
    trigger_labels = [item["label"] for item in analysis["trigger_layer"]["items"]]
    framework_labels = [item["label"] for item in analysis["framework_layer"]["items"]]

    assert "Successive wet-trigger accumulation" in labels
    assert "Tight water-angle concentration" in labels
    assert "Venus angular moisture testimony" in trigger_labels
    assert "Venus angular moisture testimony" not in framework_labels


def test_weather_hurricane_runtime_uses_landfall_concentration_gate(monkeypatch):
    payload = deepcopy(_sample_resolution_payload())
    payload["primary_chart"]["planets"] = {
        "Mercury": {
            "longitude": 12.0,
            "sign": "Aries",
            "house": 10,
            "retrograde": False,
            "closest_angle": "midheaven",
            "angle_distance_deg": 1.2,
        },
        "Uranus": {
            "longitude": 100.0,
            "sign": "Cancer",
            "house": 7,
            "retrograde": False,
            "closest_angle": "descendant",
            "angle_distance_deg": 2.4,
        },
        "Neptune": {
            "longitude": 332.0,
            "sign": "Pisces",
            "house": 4,
            "retrograde": True,
            "closest_angle": "imum_coeli",
            "angle_distance_deg": 3.1,
        },
        "Moon": {
            "longitude": 211.0,
            "sign": "Scorpio",
            "house": 1,
            "retrograde": False,
            "closest_angle": "ascendant",
            "angle_distance_deg": 5.8,
        },
    }
    payload["supporting_charts"] = [
        {
            "label": "Autumn Ingress",
            "kind": "autumn_ingress",
            "computed_datetime": "2026-09-22T09:00:00+00:00",
            "location": "Miami, Florida, USA",
            "timezone": "America/New_York",
            "planets": {
                "Neptune": {
                    "longitude": 331.0,
                    "sign": "Pisces",
                    "house": 4,
                    "retrograde": True,
                    "closest_angle": "imum_coeli",
                    "angle_distance_deg": 4.9,
                }
            },
        },
        {
            "label": "Full Moon",
            "kind": "full_moon",
            "computed_datetime": "2026-10-10T01:00:00+00:00",
            "location": "Miami, Florida, USA",
            "timezone": "America/New_York",
            "planets": {
                "Mars": {
                    "longitude": 252.0,
                    "sign": "Sagittarius",
                    "house": 7,
                    "retrograde": False,
                    "closest_angle": "descendant",
                    "angle_distance_deg": 4.0,
                },
                "Uranus": {
                    "longitude": 100.0,
                    "sign": "Cancer",
                    "house": 7,
                    "retrograde": False,
                    "closest_angle": "descendant",
                    "angle_distance_deg": 4.0,
                },
            },
        },
    ]
    monkeypatch.setattr(weather_service, "resolve_weather_chart_resolution", lambda **_: payload)

    request_model = weather_service.build_weather_request({"family_id": "hurricane_pressure"})
    resolved = weather_service.resolve_weather_context(
        request_model,
        active_clock=_clock_context(),
        bundle_resolver=lambda *args, **kwargs: {},
    )
    analysis = weather_service.analyze_weather_context(resolved).to_dict()
    labels = [item["label"] for item in analysis["family_assessment"]["matched_rules"]]

    assert "Landfall concentration gate" in labels
    assert "Path cluster concentration" in labels


def test_weather_wind_runtime_uses_target_zone_intersections(monkeypatch):
    payload = deepcopy(_sample_resolution_payload())
    payload["primary_chart"]["target_zone_intersections"] = [
        {
            "pair_id": "Mercury:ascendant|Uranus:midheaven",
            "pair_label": "Mercury ASCENDANT x Uranus MIDHEAVEN",
            "horizon_planet": "Mercury",
            "horizon_angle": "ascendant",
            "horizon_distance_deg": 1.0,
            "meridian_planet": "Uranus",
            "meridian_angle": "midheaven",
            "meridian_distance_deg": 1.0,
            "combined_distance_deg": 2.0,
            "zone": "primary",
            "intersection_strength": 14.0,
        }
    ]
    payload["supporting_charts"][1]["target_zone_intersections"] = [
        {
            "pair_id": "Mercury:ascendant|Uranus:midheaven",
            "pair_label": "Mercury ASCENDANT x Uranus MIDHEAVEN",
            "horizon_planet": "Mercury",
            "horizon_angle": "ascendant",
            "horizon_distance_deg": 2.0,
            "meridian_planet": "Uranus",
            "meridian_angle": "midheaven",
            "meridian_distance_deg": 3.0,
            "combined_distance_deg": 5.0,
            "zone": "primary",
            "intersection_strength": 11.0,
        }
    ]
    monkeypatch.setattr(weather_service, "resolve_weather_chart_resolution", lambda **_: payload)

    request_model = weather_service.build_weather_request({"family_id": "wind_event_pressure"})
    resolved = weather_service.resolve_weather_context(
        request_model,
        active_clock=_clock_context(),
        bundle_resolver=lambda *args, **kwargs: {},
    )
    analysis = weather_service.analyze_weather_context(resolved).to_dict()
    labels = [item["label"] for item in analysis["family_assessment"]["matched_rules"]]
    signals = analysis["family_assessment"]["signals"]

    assert "Target-zone intersection: Mercury x Uranus" in labels
    assert "Repeated target-zone reinforcement" in labels
    assert signals["target_zone_intersection_count"] == 1
    assert signals["intersection_reinforcing_layer_count"] == 1
    assert signals["best_intersection_distance_deg"] == 2.0
    assert signals["path_concentration"] >= 8
