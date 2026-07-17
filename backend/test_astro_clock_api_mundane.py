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
import mundane_service
import mundane_scan_service


def _clock_payload():
    return {
        "timestamp": datetime(2025, 3, 20, 12, 0, tzinfo=timezone.utc).isoformat(),
        "location": "London, United Kingdom",
        "timezone": "Europe/London",
        "mode": "manual",
        "house_system_code": "P",
        "latitude": 51.5072,
        "longitude": -0.1276,
    }


def test_mundane_chart_types_returns_runtime_catalog():
    client = app_module.app.test_client()

    response = client.get("/api/astro-clock/mundane/chart-types")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert any(row["id"] == "national_chart" for row in payload["data"]["chart_types"])
    assert any(row["id"] == "public_health" for row in payload["data"]["domains"])
    assert any(row["id"] == "civil_unrest" for row in payload["data"]["domains"])
    assert any(row["id"] == "finance_economy" for row in payload["data"]["domains"])
    assert any(row["id"] == "leadership_transition" for row in payload["data"]["domains"])
    assert any(row["id"] == "regime_stability" for row in payload["data"]["domains"])
    assert any(row["id"] == "alliance_stress" for row in payload["data"]["domains"])
    assert any(row["id"] == "trade_and_commerce" for row in payload["data"]["domains"])
    assert any(row["id"] == "epidemic_wave_pressure" for row in payload["data"]["domains"])
    assert any(row["id"] == "war_outbreak" for row in payload["data"]["domains"])
    assert any(row["id"] == "campaign_escalation" for row in payload["data"]["domains"])
    assert any(row["id"] == "military_reversal" for row in payload["data"]["domains"])
    war_event = next(row for row in payload["data"]["chart_types"] if row["id"] == "war_event")
    aries_ingress = next(row for row in payload["data"]["chart_types"] if row["id"] == "aries_ingress")
    assert war_event["default_domain_id"] == "war_outbreak"
    assert "war_outbreak" in war_event["preferred_domain_ids"]
    assert "war_conflict" in war_event["supported_domain_ids"]
    assert "war_outbreak" in aries_ingress["discouraged_domain_ids"]
    assert payload["data"]["chart_type_domain_profiles"]["war_event"]["default_domain_id"] == "war_outbreak"
    assert any(row["id"] == "iran" for row in payload["data"]["polities"])
    assert any(row["id"] == "germany" for row in payload["data"]["polities"])
    assert any(row["id"] == "india" for row in payload["data"]["polities"])
    assert any(row["id"] == "israel" for row in payload["data"]["polities"])
    assert payload["data"]["runtime_scope"] == "computed_chart_context"


def test_mundane_context_resolve_returns_reference_chart(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        astro_clock_api,
        "_mundane_bundle_resolver",
        lambda dt_iso, location, timezone_name, house_system_code: {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "chart_data": {
                "planets": {},
                "house_rulers": {},
                "houses": [],
                "ascendant": 0.0,
                "midheaven": 90.0,
            },
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/context/resolve?chart_type=national_chart&polity_id=united_kingdom"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    context = payload["data"]["context"]
    assert context["polity"]["id"] == "united_kingdom"
    assert context["reference_chart"]["id"] == "uk_1801"
    assert context["domain"]["label"] == "Unselected Domain Lens"
    assert context["event_context"]["reference_location"] == "London, United Kingdom"


def test_mundane_context_resolve_accepts_custom_reference_chart(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        astro_clock_api,
        "_mundane_bundle_resolver",
        lambda dt_iso, location, timezone_name, house_system_code: {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "chart_data": {
                "planets": {},
                "house_rulers": {},
                "houses": [],
                "ascendant": 0.0,
                "midheaven": 90.0,
            },
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/context/resolve",
        query_string={
            "chart_type": "national_chart",
            "custom_polity_label": "Iran",
            "custom_chart_label": "Iran 1979",
            "custom_chart_datetime": "1979-04-01T00:00:00",
            "custom_chart_location": "Tehran, Iran",
            "custom_chart_timezone": "Asia/Tehran",
            "location_context_type": "national_chart",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    context = payload["data"]["context"]
    assert context["polity"]["label"] == "Iran"
    assert context["polity"]["id"].startswith("custom:")
    assert "user_supplied_polity" in context["research_flags"]
    assert context["reference_chart"]["label"] == "Iran 1979"
    assert context["reference_chart"]["status"] == "user_supplied"
    assert "user_supplied_chart" in context["reference_chart"]["research_flags"]


def test_mundane_context_resolve_auto_selects_period_matched_regime_chart(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        astro_clock_api,
        "_mundane_bundle_resolver",
        lambda dt_iso, location, timezone_name, house_system_code: {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "chart_data": {
                "planets": {},
                "house_rulers": {},
                "houses": [],
                "ascendant": 0.0,
                "midheaven": 90.0,
            },
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/context/resolve",
        query_string={
            "chart_type": "national_chart",
            "polity_id": "france",
            "event_datetime": "1951-06-01T12:00:00+00:00",
            "location_context_type": "national_chart",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    context = payload["data"]["context"]
    assert context["reference_chart"]["id"] == "france_fourth_republic_1946"
    assert context["reference_chart"]["selection_basis"] == "period_match"


def test_mundane_context_resolve_rejects_polity_without_period_match(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        astro_clock_api,
        "_mundane_bundle_resolver",
        lambda dt_iso, location, timezone_name, house_system_code: {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "chart_data": {
                "planets": {},
                "house_rulers": {},
                "houses": [],
                "ascendant": 0.0,
                "midheaven": 90.0,
            },
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/context/resolve",
        query_string={
            "chart_type": "national_chart",
            "polity_id": "germany",
            "event_datetime": "2025-06-01T12:00:00+00:00",
            "location_context_type": "national_chart",
        },
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "No national chart period matches" in payload["error"]


def test_mundane_context_resolve_accepts_burma_alias(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        astro_clock_api,
        "_mundane_bundle_resolver",
        lambda dt_iso, location, timezone_name, house_system_code: {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "chart_data": {
                "planets": {},
                "house_rulers": {},
                "houses": [],
                "ascendant": 0.0,
                "midheaven": 90.0,
            },
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/context/resolve",
        query_string={
            "chart_type": "national_chart",
            "polity_id": "burma",
            "event_datetime": "1948-06-01T12:00:00+06:30",
            "location_context_type": "national_chart",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    context = payload["data"]["context"]
    assert context["polity"]["id"] == "myanmar"
    assert context["reference_chart"]["id"] == "burma_1948"


def test_mundane_context_resolve_selects_india_republic_after_1950(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        astro_clock_api,
        "_mundane_bundle_resolver",
        lambda dt_iso, location, timezone_name, house_system_code: {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "chart_data": {
                "planets": {},
                "house_rulers": {},
                "houses": [],
                "ascendant": 0.0,
                "midheaven": 90.0,
            },
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/context/resolve",
        query_string={
            "chart_type": "national_chart",
            "polity_id": "india",
            "event_datetime": "1951-01-26T12:00:00+05:30",
            "location_context_type": "national_chart",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    context = payload["data"]["context"]
    assert context["reference_chart"]["id"] == "india_republic_1950"
    assert context["reference_chart"]["selection_basis"] == "period_match"


def test_mundane_context_resolve_prefers_israel_proclamation_for_1967(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        astro_clock_api,
        "_mundane_bundle_resolver",
        lambda dt_iso, location, timezone_name, house_system_code: {
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "timezone": timezone_name,
            },
            "chart_data": {
                "planets": {},
                "house_rulers": {},
                "houses": [],
                "ascendant": 0.0,
                "midheaven": 90.0,
            },
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/context/resolve",
        query_string={
            "chart_type": "national_chart",
            "polity_id": "israel",
            "event_datetime": "1967-06-05T12:00:00+02:00",
            "location_context_type": "national_chart",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    context = payload["data"]["context"]
    assert context["reference_chart"]["id"] == "israel_proclamation_1948"
    assert context["reference_chart"]["selection_basis"] == "period_match"


def test_mundane_analyze_returns_layers_and_sources(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        mundane_service,
        "resolve_chart_resolution",
        lambda **kwargs: {
            "status": "computed",
            "primary_chart": {
                "label": "Eclipse Chart",
                "kind": "solar_eclipse",
                "computed_datetime": "2025-03-29T10:00:00+00:00",
                "house_rulers": {"6": "Saturn", "8": "Mars"},
                "planets": {
                    "Saturn": {"house": 6, "retrograde": False, "longitude": 155.0},
                    "Mars": {"house": 8, "retrograde": False, "longitude": 245.0},
                    "Jupiter": {"house": 10, "retrograde": False, "longitude": 295.0},
                },
            },
            "framework_items": [{"chart_type": "eclipse", "computed_datetime": "2025-03-29T10:00:00+00:00"}],
            "trigger_items": [{"id": "solar_eclipse", "label": "Nearest Eclipse", "summary": "Computed", "status": "computed"}],
            "activation_items": [{"watchpoint": "eclipse_degree_activation", "label": "Eclipse-Degree Activation", "summary": "Hit", "status": "present"}],
            "signals": {"node_orb_deg": 1.2, "activation_hits": [{"planet": "Saturn", "target_point": "Sun", "orb_deg": 0.8}]},
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/analyze?chart_type=eclipse&polity_id=france&domain=public_health"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["framework_layer"]["id"] == "framework"
    assert payload["data"]["trigger_layer"]["items"]
    assert payload["data"]["activation_layer"]["items"]
    assert payload["data"]["trigger_profiles"]
    assert payload["data"]["research"]["status"] == "benchmark_expanded_research_gated"
    assert payload["data"]["runtime_scope"] == "computed_chart_context"
    assert payload["data"]["domain_assessment"]["domain_id"] == "public_health"
    assert payload["data"]["domain_assessment"]["matched_rules"]
    assert payload["data"]["domain_assessment"]["raw_score"] >= payload["data"]["domain_assessment"]["score"]
    assert payload["data"]["domain_assessment"]["calibration"]["coverage_tier"]
    assert payload["data"]["research"]["benchmark_profile"]["coverage_tier"]
    assert "eclipse_degree_activation" in payload["data"]["research"]["active_triggers"]
    assert any(item.get("computed_status") for item in payload["data"]["trigger_layer"]["items"])
    assert any(
        source["id"] == "annotated_raphael_public_health"
        for source in payload["data"]["doctrine"]["sources"]
    )


def test_mundane_analyze_preserves_custom_chart_research_flags(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        mundane_service,
        "resolve_chart_resolution",
        lambda **kwargs: {
            "status": "computed",
            "primary_chart": {
                "label": "War Event Chart",
                "kind": "war_event",
                "computed_datetime": "2026-02-28T03:00:00+03:30",
                "house_rulers": {"1": "Mars", "7": "Venus"},
                "planets": {
                    "Mars": {"house": 1, "retrograde": False, "longitude": 121.0},
                    "Venus": {"house": 7, "retrograde": False, "longitude": 301.0},
                    "Saturn": {"house": 10, "retrograde": False, "longitude": 15.0},
                },
            },
            "framework_items": [{"chart_type": "war_event", "computed_datetime": "2026-02-28T03:00:00+03:30"}],
            "trigger_items": [{"id": "war_event_anchor", "label": "War Event Anchor", "summary": "Computed", "status": "computed"}],
            "activation_items": [],
            "signals": {
                "aggressor_house": {"ruler": "Mars", "house_position": 1, "retrograde": False, "sign": "Leo"},
                "defender_house": {"ruler": "Venus", "house_position": 7, "retrograde": False, "sign": "Aquarius"},
                "mars_retrograde": False,
            },
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/analyze",
        query_string={
            "chart_type": "war_event",
            "domain": "war_conflict",
            "custom_polity_label": "Iran",
            "custom_chart_label": "Iran 1979",
            "custom_chart_datetime": "1979-04-01T00:00:00",
            "custom_chart_location": "Tehran, Iran",
            "custom_chart_timezone": "Asia/Tehran",
            "location_context_type": "event_chart",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert "user_supplied_chart" in payload["data"]["research"]["flags"]
    assert "not_registry_backed" in payload["data"]["research"]["flags"]
    assert "user_supplied_chart" in payload["data"]["domain_assessment"]["research_flags"]
    assert payload["data"]["context"]["reference_chart"]["status"] == "user_supplied"


def test_mundane_analyze_exposes_computed_cycle_trigger_profiles(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        mundane_service,
        "resolve_chart_resolution",
        lambda **kwargs: {
            "status": "computed",
            "primary_chart": {
                "label": "Aries Ingress",
                "kind": "aries_ingress",
                "computed_datetime": "2025-03-20T10:00:00+00:00",
                "house_rulers": {"2": "Mercury", "8": "Mars", "10": "Saturn", "11": "Jupiter"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mercury": {"house": 8, "retrograde": True, "longitude": 205.0},
                    "Mars": {"house": 2, "retrograde": False, "longitude": 35.0},
                    "Saturn": {"house": 10, "retrograde": True, "longitude": 94.0},
                    "Jupiter": {"house": 11, "retrograde": False, "longitude": 311.0},
                },
            },
            "cycle_context": {
                "type": "jupiter_saturn_cycle",
                "nearest_conjunction_datetime": "2020-12-21T18:00:00+00:00",
                "nearest_distance_years": 2.8,
                "cycle_phase": "opening_cycle",
                "turning_window_active": True,
                "turning_window_level": "strong",
                "conjunction_sign": "Aquarius",
            },
            "framework_items": [{"chart_type": "aries_ingress", "computed_datetime": "2025-03-20T10:00:00+00:00"}],
            "trigger_items": [{"id": "mutation_and_conjunction_cycles", "label": "Jupiter-Saturn Cycle", "summary": "Computed", "status": "computed"}],
            "activation_items": [],
            "signals": {},
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/analyze?chart_type=aries_ingress&polity_id=france&domain=finance_economy"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    cycle_profile = next(
        row for row in payload["data"]["trigger_profiles"] if row["id"] == "mutation_and_conjunction_cycles"
    )
    assert cycle_profile["status"] == "computed"
    assert cycle_profile["active"] is True
    assert cycle_profile["metrics"]["turning_window_active"] is True
    assert "mutation_and_conjunction_cycles" in payload["data"]["research"]["active_triggers"]


def test_mundane_analyze_rejects_unknown_domain(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)

    response = client.get(
        "/api/astro-clock/mundane/analyze?chart_type=eclipse&polity_id=france&domain=unknown_domain"
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "Unsupported domain" in payload["error"]


def test_mundane_analyze_rejects_discouraged_chart_domain_pairing(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)

    response = client.get(
        "/api/astro-clock/mundane/analyze?chart_type=aries_ingress&polity_id=united_states&domain=war_outbreak"
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "War Outbreak requires the War Event chart type" in payload["error"]


def test_mundane_scan_regions_returns_catalog():
    client = app_module.app.test_client()

    response = client.get("/api/astro-clock/mundane/scan/regions")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert any(row["id"] == "spatial_scan" for row in payload["data"]["scan_modes"])
    assert any(row["id"] == "middle_east" for row in payload["data"]["regions"])
    assert any(row["id"] == "war_event" for row in payload["data"]["chart_types"])
    war_event = next(row for row in payload["data"]["chart_types"] if row["id"] == "war_event")
    chart_type_ids = {
        str(row.get("id") or "").strip().lower()
        for row in (payload["data"].get("chart_types") or [])
    }
    assert any(row["id"] == "capital_chart" for row in payload["data"]["context_types"])
    assert any(row["id"] == "united_states" for row in payload["data"]["polities"])
    assert any(row["id"] == "long_range_async_scan" for row in payload["data"]["scan_modes"])
    assert payload["data"]["scan_mode_limits"]["long_range_async_scan"]["async_only"] is True
    assert payload["data"]["scan_chart_policy"]["national_chart"]["status"] == "analysis_only"
    assert "national_chart" not in chart_type_ids
    assert chart_type_ids == {"war_event", "eclipse", "lunation", "aries_ingress"}
    assert war_event["default_domain_id"] == "war_outbreak"
    assert "campaign_escalation" in war_event["preferred_domain_ids"]


def test_mundane_scan_run_rejects_long_range_sync_mode():
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/mundane/scan/run"
        "?chart_type=war_event&domain=war_conflict&region_id=middle_east"
        "&scan_mode=long_range_async_scan"
        "&start_datetime=2026-02-01T00:00:00%2B03:30"
        "&end_datetime=2026-03-01T00:00:00%2B03:30"
        "&time_step_hours=12"
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "async-only" in payload["error"]


def test_mundane_scan_run_rejects_discouraged_outbreak_pairing():
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/mundane/scan/run"
        "?chart_type=aries_ingress&domain=war_outbreak&polity_id=united_states&region_id=global"
        "&fixed_datetime=2026-02-28T03:00:00%2B03:30"
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "War Outbreak requires the War Event chart type" in payload["error"]


def test_mundane_scan_run_returns_ranked_results(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)

    monkeypatch.setattr(
        mundane_scan_service,
        "build_scan_request",
        lambda args: SimpleNamespace(to_dict=lambda: {"scan_mode": "spatial_scan", "region_id": "middle_east"}),
    )
    monkeypatch.setattr(
        mundane_scan_service,
        "run_scan",
        lambda request_model, *, active_clock, bundle_resolver, include_series=False: {
            "scan_mode": "spatial_scan",
            "region": {"id": "middle_east", "label": "Middle East"},
            "counts": {"candidate_locations": 2, "time_slices": 1, "evaluated_cells": 2, "kept_cells": 2, "returned": 1, "returned_places": 1, "failures": 0},
            "top_cells": [
                {
                    "rank": 1,
                    "location": {"label": "Tehran, Iran"},
                    "datetime": "2026-02-28T03:00:00+03:30",
                    "score": 18,
                    "level": "elevated",
                    "matched_rules": [],
                    "calibration": {"coverage_tier": "moderate"},
                    "research_flags": ["benchmark_backed"],
                }
            ],
            "top_places": [
                {
                    "rank": 1,
                    "location": {"label": "Tehran, Iran"},
                    "breakout_index": 18,
                    "peak_scan_score": 18,
                    "breakout_kind": "opening_break_candidate",
                }
            ],
            "results": [
                {
                    "rank": 1,
                    "location": {"label": "Tehran, Iran"},
                    "datetime": "2026-02-28T03:00:00+03:30",
                    "score": 18,
                    "level": "elevated",
                    "matched_rules": [],
                    "calibration": {"coverage_tier": "moderate"},
                    "research_flags": ["benchmark_backed"],
                }
            ],
            "primary_ranking_mode": "cells",
            "research_mode": True,
            "runtime_scope": "computed_chart_context",
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/scan/run?chart_type=war_event&domain=war_conflict&region_id=middle_east&fixed_datetime=2026-02-28T03:00:00%2B03:30"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["top_cells"][0]["location"]["label"] == "Tehran, Iran"
    assert payload["data"]["top_places"][0]["location"]["label"] == "Tehran, Iran"
    assert payload["data"]["results"][0]["location"]["label"] == "Tehran, Iran"
    assert payload["data"]["runtime_scope"] == "computed_chart_context"


def test_mundane_scan_run_can_include_series(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        mundane_scan_service,
        "build_scan_request",
        lambda args: SimpleNamespace(to_dict=lambda: {"scan_mode": "spatiotemporal_scan", "region_id": "middle_east"}),
    )
    monkeypatch.setattr(
        mundane_scan_service,
        "run_scan",
        lambda request_model, *, active_clock, bundle_resolver, include_series=False: {
            "scan_mode": "spatiotemporal_scan",
            "region": {"id": "middle_east", "label": "Middle East"},
            "counts": {"candidate_locations": 2, "time_slices": 3, "evaluated_cells": 6, "kept_cells": 6, "returned": 2, "returned_places": 1, "failures": 0},
            "top_cells": [{"rank": 1, "location": {"label": "Tehran, Iran"}, "score": 28, "level": "elevated"}],
            "top_places": [{"rank": 1, "location": {"label": "Tehran, Iran"}, "breakout_index": 31.5, "peak_scan_score": 31.5, "breakout_kind": "opening_break_candidate"}],
            "results": [{"rank": 1, "location": {"label": "Tehran, Iran"}, "score": 28, "level": "elevated"}],
            "series": {
                "timeline": ["2026-02-28T00:00:00+03:30", "2026-02-28T06:00:00+03:30"],
                "places": [{"location": {"label": "Tehran, Iran"}, "breakout_index": 31.5, "series": []}],
                "graph_places": [{"location": {"label": "Tehran, Iran"}, "breakout_index": 31.5, "series": []}],
                "breakout_candidates": [{"rank": 1, "location": {"label": "Tehran, Iran"}, "breakout_index": 31.5}],
                "series_overview": {"top_breakout_location": {"label": "Tehran, Iran"}},
            } if include_series else None,
            "primary_ranking_mode": "places",
            "default_output_view": "graph" if include_series else "cells",
            "runtime_scope": "computed_chart_context",
        },
    )

    response = client.get(
        "/api/astro-clock/mundane/scan/run?chart_type=war_event&domain=war_conflict&region_id=middle_east&start_datetime=2026-02-28T00:00:00%2B03:30&end_datetime=2026-02-28T12:00:00%2B03:30&time_step_hours=6&include_series=1"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["top_places"][0]["location"]["label"] == "Tehran, Iran"
    assert payload["data"]["series"]["series_overview"]["top_breakout_location"]["label"] == "Tehran, Iran"


def test_mundane_scan_start_and_result(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        mundane_scan_service,
        "build_scan_request",
        lambda args: SimpleNamespace(to_dict=lambda: {"scan_mode": "spatial_scan", "region_id": "middle_east"}),
    )
    monkeypatch.setattr(
        mundane_scan_service,
        "run_scan",
        lambda request_model, *, active_clock, bundle_resolver, progress_callback=None, include_series=False: (
            progress_callback and progress_callback({
                "stage": "evaluate_cells",
                "percent": 0.6,
                "message": "Scanning",
                "done": 1,
                "total": 2,
                "candidate_count": 2,
                "time_slices": 1,
                "kept_cells": 1,
                "failures": 0,
            }),
            {
                "scan_mode": "spatial_scan",
                "region": {"id": "middle_east", "label": "Middle East"},
                "counts": {"candidate_locations": 2, "time_slices": 1, "evaluated_cells": 2, "kept_cells": 1, "returned": 1, "failures": 0},
                "results": [{"rank": 1, "location": {"label": "Tehran, Iran"}, "score": 18, "level": "elevated"}],
                "series": {"places": [{"location": {"label": "Tehran, Iran"}, "series": []}]} if include_series else None,
                "research_mode": True,
                "runtime_scope": "computed_chart_context",
            }
        )[1],
    )

    def run_immediately(_job_name, callback):
        callback()
        return True

    monkeypatch.setattr(astro_clock_api, "_submit_background_job", run_immediately)

    response = client.post(
        "/api/astro-clock/mundane/scan/start",
        json={"chart_type": "war_event", "domain": "war_conflict", "region_id": "middle_east", "fixed_datetime": "2026-02-28T03:00:00+03:30"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    session_id = payload["data"]["session_id"]
    assert payload["data"]["progress"]["ready"] is True

    progress_response = client.get(f"/api/astro-clock/mundane/scan/progress?session_id={session_id}")
    progress_payload = progress_response.get_json()
    assert progress_response.status_code == 200
    assert progress_payload["data"]["ready"] is True
    assert progress_payload["data"]["candidate_count"] == 2

    result_response = client.get(f"/api/astro-clock/mundane/scan/result?session_id={session_id}")
    result_payload = result_response.get_json()
    assert result_response.status_code == 200
    assert result_payload["data"]["ready"] is True
    assert result_payload["data"]["result"]["results"][0]["location"]["label"] == "Tehran, Iran"


def test_mundane_scan_start_ignores_uncopyable_thread_in_progress_payload(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        mundane_scan_service,
        "build_scan_request",
        lambda args: SimpleNamespace(to_dict=lambda: {"scan_mode": "spatial_scan", "region_id": "middle_east"}),
    )
    monkeypatch.setattr(
        mundane_scan_service,
        "run_scan",
        lambda request_model, *, active_clock, bundle_resolver, progress_callback=None, include_series=False: {
            "scan_mode": "spatial_scan",
            "region": {"id": "middle_east", "label": "Middle East"},
            "counts": {"candidate_locations": 1, "time_slices": 1, "evaluated_cells": 1, "kept_cells": 1, "returned": 1, "failures": 0},
            "results": [{"rank": 1, "location": {"label": "Tehran, Iran"}, "score": 18, "level": "elevated"}],
            "research_mode": True,
            "runtime_scope": "computed_chart_context",
        },
    )

    monkeypatch.setattr(
        astro_clock_api,
        "_submit_background_job",
        lambda _job_name, _callback: True,
    )

    response = client.post(
        "/api/astro-clock/mundane/scan/start",
        json={"chart_type": "war_event", "domain": "war_conflict", "region_id": "middle_east", "fixed_datetime": "2026-02-28T03:00:00+03:30"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["progress"]["stage"] in {"queued", "pending"}


def test_mundane_scan_start_rejects_invalid_request_without_internal_error(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_mundane_active_clock_context", _clock_payload)

    response = client.post(
        "/api/astro-clock/mundane/scan/start",
        json={
            "chart_type": "war_event",
            "domain": "war_conflict",
            "region_id": "middle_east",
            "scan_mode": "spatiotemporal_scan",
            "start_datetime": "2023-01-01T01:00:00+00:00",
            "end_datetime": "2026-01-01T20:00:00+00:00",
            "time_step_hours": 6,
        },
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "spatiotemporal_scan is limited to 24 time slices" in payload["error"]
