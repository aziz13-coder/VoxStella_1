from pathlib import Path
from types import SimpleNamespace
import os
import sys

import pytest

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mundane_scan_service
from mundane_models import ActiveClockContext


def _active_clock():
    return ActiveClockContext(
        timestamp="2026-04-11T08:00:00+00:00",
        location="Greenwich, UK",
        timezone="Europe/London",
        mode="realtime",
        house_system_code="P",
        latitude=51.4769,
        longitude=-0.0005,
    )


def test_build_scan_request_rejects_non_scan_chart_type():
    try:
        mundane_scan_service.build_scan_request(
            {
                "chart_type": "national_chart",
                "domain": "government_stability",
                "region_id": "global",
                "fixed_datetime": "2026-02-28T03:00:00+03:30",
            }
        )
    except ValueError as exc:
        assert "not scan-enabled" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported scan chart type")


def test_build_scan_request_rejects_discouraged_outbreak_pairing():
    with pytest.raises(ValueError) as exc:
        mundane_scan_service.build_scan_request(
            {
                "chart_type": "aries_ingress",
                "domain": "war_outbreak",
                "polity_id": "united_states",
                "region_id": "global",
                "fixed_datetime": "2026-02-28T03:00:00+03:30",
            }
        )

    assert "War Outbreak requires the War Event chart type" in str(exc.value)


def test_run_scan_returns_ranked_rows(monkeypatch):
    request_model = mundane_scan_service.build_scan_request(
        {
            "chart_type": "war_event",
            "domain": "war_conflict",
            "polity_id": "united_states",
            "national_chart_id": "us_1776_watters",
            "region_id": "middle_east",
            "scan_mode": "spatial_scan",
            "fixed_datetime": "2026-02-28T03:00:00+03:30",
            "candidate_limit": "2",
            "top_k": "2",
        }
    )

    monkeypatch.setattr(
        mundane_scan_service,
        "collect_region_candidates",
        lambda region_id, **kwargs: [
            {
                "label": "Tehran, Iran",
                "latitude": 35.6892,
                "longitude": 51.3890,
                "country_code": "IR",
                "country_name": "Iran",
                "timezone": "Asia/Tehran",
            },
            {
                "label": "Baghdad, Iraq",
                "latitude": 33.3152,
                "longitude": 44.3661,
                "country_code": "IQ",
                "country_name": "Iraq",
                "timezone": "Asia/Baghdad",
            },
        ],
    )

    def _fake_resolve_context(request, *, active_clock, bundle_resolver=None):
        return SimpleNamespace(
            chart_resolution={
                "signals": {
                    "scan_location": request.event_location,
                    "mars_retrograde": False,
                },
                "primary_chart": {
                    "label": "War Event Chart",
                    "location": request.event_location,
                },
            }
        )

    def _fake_analyze_context(resolved):
        location = resolved.chart_resolution["signals"]["scan_location"]
        score = 24 if "Baghdad" in location else 8
        return SimpleNamespace(
            domain_assessment={
                "score": score,
                "raw_score": score + 2,
                "level": "elevated" if score > 10 else "quiet",
                "raw_level": "elevated" if score > 10 else "quiet",
                "summary": f"Scan result for {location}",
                "matched_rules": [{"id": "rule", "label": "Rule", "weight": score}],
                "calibration": {"coverage_tier": "moderate", "unique_case_count": 2},
                "research_flags": ["benchmark_backed"],
            },
            context=resolved,
        )

    monkeypatch.setattr(mundane_scan_service.mundane_service, "resolve_context", _fake_resolve_context)
    monkeypatch.setattr(mundane_scan_service.mundane_service, "analyze_context", _fake_analyze_context)

    payload = mundane_scan_service.run_scan(
        request_model,
        active_clock=_active_clock(),
        bundle_resolver=object(),
    )

    assert payload["counts"]["candidate_locations"] == 2
    assert payload["counts"]["time_slices"] == 1
    assert payload["counts"]["returned"] == 2
    assert payload["counts"]["returned_places"] == 2
    assert payload["primary_ranking_mode"] == "cells"
    assert payload["top_cells"][0]["location"]["label"] == "Baghdad, Iraq"
    assert payload["top_places"][0]["location"]["label"] == "Baghdad, Iraq"
    assert payload["results"][0]["location"]["label"] == "Baghdad, Iraq"
    assert payload["results"][0]["score"] == 24
    assert payload["results"][0]["scan_level"] in {"dominant", "leading"}
    assert payload["results"][1]["scan_level"] in {"watch", "background", "active"}
    assert "scan_calibration" in payload
    assert payload["results"][1]["location"]["label"] == "Tehran, Iran"


def test_build_scan_request_requires_time_window_for_spatiotemporal():
    try:
        mundane_scan_service.build_scan_request(
            {
                "chart_type": "war_event",
                "domain": "war_conflict",
                "region_id": "middle_east",
                "scan_mode": "spatiotemporal_scan",
            }
        )
    except ValueError as exc:
        assert "requires start_datetime and end_datetime" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing time window")


def test_get_scan_runtime_catalog_exposes_new_region_presets():
    catalog = mundane_scan_service.get_scan_runtime_catalog()
    region_ids = {str(row.get("id")) for row in catalog.get("regions") or []}
    scan_mode_ids = {str(row.get("id")) for row in catalog.get("scan_modes") or []}
    assert "middle_east" in region_ids
    assert "levant" in region_ids
    assert "persian_gulf" in region_ids
    assert "long_range_async_scan" in scan_mode_ids
    assert catalog["scan_mode_limits"]["long_range_async_scan"]["max_time_slices"] > catalog["scan_mode_limits"]["spatiotemporal_scan"]["max_time_slices"]
    assert catalog["scan_chart_policy"]["national_chart"]["status"] == "analysis_only"


def test_build_scan_request_allows_long_range_async_mode():
    request_model = mundane_scan_service.build_scan_request(
        {
            "chart_type": "war_event",
            "domain": "war_conflict",
            "region_id": "middle_east",
            "scan_mode": "long_range_async_scan",
            "start_datetime": "2026-02-01T00:00:00+03:30",
            "end_datetime": "2026-03-01T00:00:00+03:30",
            "time_step_hours": "12",
        }
    )

    assert request_model.scan_mode == "long_range_async_scan"
    assert request_model.time_step_hours == 12
    assert request_model.candidate_limit == 6


def test_run_scan_uses_war_anchor_proximity_to_break_ties(monkeypatch):
    request_model = mundane_scan_service.build_scan_request(
        {
            "chart_type": "war_event",
            "domain": "war_conflict",
            "polity_id": "united_states",
            "national_chart_id": "us_1776_watters",
            "reference_location": "Tehran, Iran",
            "reference_latitude": "35.6892",
            "reference_longitude": "51.3890",
            "region_id": "persian_gulf",
            "scan_mode": "spatial_scan",
            "fixed_datetime": "2026-02-28T03:00:00+03:30",
            "candidate_limit": "2",
            "top_k": "2",
        }
    )

    monkeypatch.setattr(
        mundane_scan_service,
        "collect_region_candidates",
        lambda region_id, **kwargs: [
            {
                "label": "Tehran, Iran",
                "latitude": 35.6892,
                "longitude": 51.3890,
                "country_code": "IR",
                "country_name": "Iran",
                "timezone": "Asia/Tehran",
            },
            {
                "label": "Jeddah, Saudi Arabia",
                "latitude": 21.5433,
                "longitude": 39.1728,
                "country_code": "SA",
                "country_name": "Saudi Arabia",
                "timezone": "Asia/Riyadh",
            },
        ],
    )

    def _fake_resolve_context(request, *, active_clock, bundle_resolver=None):
        return SimpleNamespace(
            chart_resolution={
                "signals": {
                    "scan_location": request.event_location,
                    "mars_retrograde": False,
                },
                "primary_chart": {
                    "label": "War Event Chart",
                    "location": request.event_location,
                },
            }
        )

    def _fake_analyze_context(resolved):
        return SimpleNamespace(
            domain_assessment={
                "score": 9,
                "raw_score": 10,
                "level": "quiet",
                "raw_level": "quiet",
                "summary": "Tied absolute war score",
                "matched_rules": [{"id": "aggressor_ruler_angular", "label": "Aggressor ruler angular", "weight": 10}],
                "calibration": {"coverage_tier": "moderate", "unique_case_count": 2},
                "research_flags": ["benchmark_backed"],
            },
            context=resolved,
        )

    monkeypatch.setattr(mundane_scan_service.mundane_service, "resolve_context", _fake_resolve_context)
    monkeypatch.setattr(mundane_scan_service.mundane_service, "analyze_context", _fake_analyze_context)

    payload = mundane_scan_service.run_scan(
        request_model,
        active_clock=_active_clock(),
        bundle_resolver=object(),
    )

    assert payload["results"][0]["location"]["label"] == "Tehran, Iran"
    assert payload["results"][0]["scan_score"] > payload["results"][1]["scan_score"]
    assert payload["results"][0]["scan_bias"] > payload["results"][1]["scan_bias"]


def test_run_scan_can_return_series_payload(monkeypatch):
    request_model = mundane_scan_service.build_scan_request(
        {
            "chart_type": "war_event",
            "domain": "war_conflict",
            "polity_id": "united_states",
            "national_chart_id": "us_1776_watters",
            "region_id": "middle_east",
            "scan_mode": "spatiotemporal_scan",
            "start_datetime": "2026-02-28T00:00:00+03:30",
            "end_datetime": "2026-02-28T12:00:00+03:30",
            "time_step_hours": "6",
            "candidate_limit": "2",
            "top_k": "4",
        }
    )

    monkeypatch.setattr(
        mundane_scan_service,
        "collect_region_candidates",
        lambda region_id, **kwargs: [
            {
                "label": "Tehran, Iran",
                "latitude": 35.6892,
                "longitude": 51.3890,
                "country_code": "IR",
                "country_name": "Iran",
                "timezone": "Asia/Tehran",
            },
            {
                "label": "Baghdad, Iraq",
                "latitude": 33.3152,
                "longitude": 44.3661,
                "country_code": "IQ",
                "country_name": "Iraq",
                "timezone": "Asia/Baghdad",
            },
        ],
    )

    def _fake_resolve_context(request, *, active_clock, bundle_resolver=None):
        return SimpleNamespace(
            chart_resolution={
                "signals": {
                    "scan_location": request.event_location,
                    "scan_datetime": request.event_datetime,
                },
                "primary_chart": {
                    "label": "War Event Chart",
                    "location": request.event_location,
                },
            }
        )

    def _fake_analyze_context(resolved):
        location = resolved.chart_resolution["signals"]["scan_location"]
        dt = resolved.chart_resolution["signals"]["scan_datetime"]
        if "Tehran" in location and "06:00:00" in dt:
            score = 32
        elif "Tehran" in location:
            score = 18
        elif "06:00:00" in dt:
            score = 22
        else:
            score = 12
        return SimpleNamespace(
            domain_assessment={
                "score": score,
                "raw_score": score + 1,
                "level": "high" if score >= 30 else "elevated" if score >= 18 else "quiet",
                "raw_level": "high" if score >= 30 else "elevated" if score >= 18 else "quiet",
                "summary": f"Scan result for {location} at {dt}",
                "matched_rules": [{"id": "rule", "label": "Rule", "weight": score}],
                "calibration": {"coverage_tier": "moderate", "unique_case_count": 2},
                "research_flags": ["benchmark_backed"],
            },
            context=resolved,
        )

    monkeypatch.setattr(mundane_scan_service.mundane_service, "resolve_context", _fake_resolve_context)
    monkeypatch.setattr(mundane_scan_service.mundane_service, "analyze_context", _fake_analyze_context)

    payload = mundane_scan_service.run_scan(
        request_model,
        active_clock=_active_clock(),
        bundle_resolver=object(),
        include_series=True,
    )

    assert "series" in payload
    assert payload["default_output_view"] == "graph"
    assert payload["primary_ranking_mode"] == "places"
    assert payload["series"]["timeline"] == [
        "2026-02-28T00:00:00+03:30",
        "2026-02-28T06:00:00+03:30",
        "2026-02-28T12:00:00+03:30",
    ]
    assert payload["top_places"][0]["location"]["label"] == "Tehran, Iran"
    assert payload["series"]["breakout_candidates"][0]["location"]["label"] == "Tehran, Iran"
    assert payload["series"]["series_overview"]["top_peak_location"]["label"] == "Tehran, Iran"
    assert any(place["location"]["label"] == "Baghdad, Iraq" for place in payload["series"]["places"])
    assert len(payload["series"]["graph_places"]) <= payload["series"]["series_overview"]["graph_place_limit"]


@pytest.mark.parametrize(
    ("chart_type", "domain", "extra"),
    [
        ("war_event", "war_conflict", {}),
        ("eclipse", "government_stability", {"polity_id": "united_states"}),
        ("lunation", "government_stability", {"polity_id": "united_states"}),
        ("aries_ingress", "government_stability", {"polity_id": "united_states"}),
    ],
)
def test_run_scan_series_uses_representative_midpoint_for_flat_peak_plateaus(monkeypatch, chart_type, domain, extra):
    args = {
        "chart_type": chart_type,
        "domain": domain,
        "region_id": "middle_east",
        "scan_mode": "spatiotemporal_scan",
        "start_datetime": "2026-02-28T00:00:00+03:30",
        "end_datetime": "2026-02-28T12:00:00+03:30",
        "time_step_hours": "6",
        "candidate_limit": "1",
        "top_k": "4",
    }
    args.update(extra)
    request_model = mundane_scan_service.build_scan_request(args)

    monkeypatch.setattr(
        mundane_scan_service,
        "collect_region_candidates",
        lambda region_id, **kwargs: [
            {
                "label": "Tehran, Iran",
                "latitude": 35.6892,
                "longitude": 51.3890,
                "country_code": "IR",
                "country_name": "Iran",
                "timezone": "Asia/Tehran",
            }
        ],
    )

    def _fake_resolve_context(request, *, active_clock, bundle_resolver=None):
        return SimpleNamespace(
            chart_resolution={
                "signals": {
                    "scan_location": request.event_location,
                    "scan_datetime": request.event_datetime,
                },
                "primary_chart": {
                    "label": "Synthetic Scan Chart",
                    "location": request.event_location,
                },
            }
        )

    def _fake_analyze_context(resolved):
        location = resolved.chart_resolution["signals"]["scan_location"]
        dt = resolved.chart_resolution["signals"]["scan_datetime"]
        return SimpleNamespace(
            domain_assessment={
                "score": 24,
                "raw_score": 25,
                "level": "elevated",
                "raw_level": "elevated",
                "summary": f"Flat scan result for {location} at {dt}",
                "matched_rules": [{"id": "rule", "label": "Rule", "weight": 24}],
                "calibration": {"coverage_tier": "moderate", "unique_case_count": 2},
                "research_flags": ["benchmark_backed"],
            },
            context=resolved,
        )

    monkeypatch.setattr(mundane_scan_service.mundane_service, "resolve_context", _fake_resolve_context)
    monkeypatch.setattr(mundane_scan_service.mundane_service, "analyze_context", _fake_analyze_context)

    payload = mundane_scan_service.run_scan(
        request_model,
        active_clock=_active_clock(),
        bundle_resolver=object(),
        include_series=True,
    )

    place = payload["series"]["places"][0]
    assert place["peak_selection"] == "peak_plateau"
    assert place["peak_datetime"] == "2026-02-28T06:00:00+03:30"
    assert place["peak_window_start_datetime"] == "2026-02-28T00:00:00+03:30"
    assert place["peak_window_end_datetime"] == "2026-02-28T12:00:00+03:30"
    assert place["breakout_kind"] == "sustained_theater_candidate"
    assert payload["series"]["series_overview"]["top_peak_datetime"] == "2026-02-28T06:00:00+03:30"


def test_build_series_payload_marks_zero_series_as_no_peak():
    request_model = mundane_scan_service.build_scan_request(
        {
            "chart_type": "lunation",
            "domain": "government_stability",
            "polity_id": "united_states",
            "region_id": "middle_east",
            "scan_mode": "spatiotemporal_scan",
            "start_datetime": "2026-02-28T00:00:00+03:30",
            "end_datetime": "2026-02-28T12:00:00+03:30",
            "time_step_hours": "6",
            "candidate_limit": "1",
        }
    )

    payload = mundane_scan_service._build_series_payload(
        [
            {
                "datetime": "2026-02-28T00:00:00+03:30",
                "scan_score": 0.0,
                "score": 0.0,
                "raw_score": 0.0,
                "level": "quiet",
                "summary": None,
                "location": {"label": "Tehran, Iran"},
                "calibration": {"unique_case_count": 1},
            },
            {
                "datetime": "2026-02-28T06:00:00+03:30",
                "scan_score": 0.0,
                "score": 0.0,
                "raw_score": 0.0,
                "level": "quiet",
                "summary": None,
                "location": {"label": "Tehran, Iran"},
                "calibration": {"unique_case_count": 1},
            },
            {
                "datetime": "2026-02-28T12:00:00+03:30",
                "scan_score": 0.0,
                "score": 0.0,
                "raw_score": 0.0,
                "level": "quiet",
                "summary": None,
                "location": {"label": "Tehran, Iran"},
                "calibration": {"unique_case_count": 1},
            },
        ],
        timepoints=[
            "2026-02-28T00:00:00+03:30",
            "2026-02-28T06:00:00+03:30",
            "2026-02-28T12:00:00+03:30",
        ],
        request_model=request_model,
    )

    place = payload["places"][0]
    assert place["peak_selection"] == "no_peak"
    assert place["peak_datetime"] is None
    assert place["breakout_kind"] == "background"


def test_rank_scan_rows_diversifies_places_before_repeating_plateau_cells():
    rows = [
        {
            "location": {"label": "Baghdad, Iraq"},
            "datetime": "2026-02-28T00:00:00+03:30",
            "scan_score": 40.0,
            "score": 40.0,
            "raw_score": 42.0,
            "level": "critical",
            "calibration": {"unique_case_count": 3},
        },
        {
            "location": {"label": "Baghdad, Iraq"},
            "datetime": "2026-02-28T06:00:00+03:30",
            "scan_score": 39.0,
            "score": 39.0,
            "raw_score": 41.0,
            "level": "critical",
            "calibration": {"unique_case_count": 3},
        },
        {
            "location": {"label": "Tehran, Iran"},
            "datetime": "2026-02-28T00:00:00+03:30",
            "scan_score": 36.0,
            "score": 36.0,
            "raw_score": 38.0,
            "level": "high",
            "calibration": {"unique_case_count": 3},
        },
    ]

    ranked = mundane_scan_service._rank_scan_rows(rows, top_k=3)

    assert ranked[0]["location"]["label"] == "Baghdad, Iraq"
    assert ranked[1]["location"]["label"] == "Tehran, Iran"
    assert ranked[2]["location"]["label"] == "Baghdad, Iraq"
