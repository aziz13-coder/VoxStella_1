from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import time

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
import weather_service
import weather_benchmark_profiles
import weather_scan_service


def _clock_payload():
    return {
        "timestamp": datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc).isoformat(),
        "location": "Miami, Florida, USA",
        "timezone": "America/New_York",
        "mode": "manual",
        "house_system_code": "P",
        "latitude": 25.7617,
        "longitude": -80.1918,
    }


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
                }
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


def test_weather_catalog_returns_seed_runtime_family_catalog():
    client = app_module.app.test_client()

    response = client.get("/api/astro-clock/weather/catalog")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    family_ids = {row["id"] for row in payload["data"]["families"]}
    assert "flood_risk" in family_ids
    assert "hurricane_pressure" in family_ids
    assert "severe_convective_pressure" in family_ids
    assert "wind_event_pressure" in family_ids
    assert payload["data"]["runtime_scope"] == "seed_weather_runtime"


def test_weather_catalog_gracefully_handles_missing_benchmark_datasets(monkeypatch, tmp_path):
    client = app_module.app.test_client()

    weather_benchmark_profiles.build_weather_family_profiles.cache_clear()
    monkeypatch.setattr(weather_benchmark_profiles, "DEFAULT_DATASET_PATHS", [tmp_path / "missing.jsonl"])

    try:
        response = client.get("/api/astro-clock/weather/catalog")
    finally:
        weather_benchmark_profiles.build_weather_family_profiles.cache_clear()

    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["benchmark_branch"]["family_profile_count"] == 0
    assert payload["data"]["runtime_scope"] == "seed_weather_runtime"


def test_weather_context_resolve_returns_seed_context(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_weather_active_clock_context", _clock_payload)
    monkeypatch.setattr(weather_service, "resolve_weather_chart_resolution", lambda **_: _sample_resolution_payload())

    response = client.get("/api/astro-clock/weather/context/resolve?family_id=wind_event_pressure")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    context = payload["data"]["context"]
    assert context["family"]["id"] == "wind_event_pressure"
    assert context["event_context"]["location"] == "Miami, Florida, USA"
    assert context["chart_resolution"]["primary_chart"]["kind"] == "forecast_chart"


def test_weather_analyze_returns_layered_seed_assessment(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_weather_active_clock_context", _clock_payload)
    monkeypatch.setattr(weather_service, "resolve_weather_chart_resolution", lambda **_: _sample_resolution_payload())

    response = client.get("/api/astro-clock/weather/analyze?family_id=wind_event_pressure")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert data["runtime_scope"] == "seed_weather_runtime"
    assert data["framework_layer"]["label"] == "Seasonal Framework"
    assert data["trigger_layer"]["label"] == "Lunar Trigger"
    assert data["locality_layer"]["label"] == "Locality Proxy"
    assert data["family_assessment"]["family_id"] == "wind_event_pressure"
    assert data["family_assessment"]["score"] > 0
    assert data["research"]["runtime_scope"] == "seed_weather_runtime"


def test_weather_analyze_rejects_missing_family_id():
    client = app_module.app.test_client()

    response = client.get("/api/astro-clock/weather/analyze")
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "family_id is required" in payload["error"]


def test_weather_scan_catalog_returns_scan_configuration():
    client = app_module.app.test_client()

    response = client.get("/api/astro-clock/weather/scan/catalog")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["runtime_scope"] == "seed_weather_scan"
    scope_ids = {row["id"] for row in payload["data"]["scan_scopes"]}
    assert "place_timeline" in scope_ids
    assert "region_timeline" in scope_ids


def test_weather_scan_run_returns_series_payload(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_weather_active_clock_context", _clock_payload)

    def fake_run(request_model, *, active_clock, bundle_resolver):
        return {
            "request": request_model.to_dict(),
            "counts": {"candidate_count": 1, "time_slices": 3, "evaluated": 3, "returned": 3},
            "scope": {"scan_scope": "place_timeline", "location": "Miami, Florida, USA"},
            "results": [
                {
                    "rank": 1,
                    "datetime": "2026-04-12T00:00:00+00:00",
                    "location": {"label": "Miami, Florida, USA", "timezone": "America/New_York"},
                    "score": 42,
                    "level": "active",
                    "scan_level": "dominant",
                    "matched_rules": [],
                    "signals": {},
                }
            ],
            "series": {
                "timeline": [
                    "2026-04-12T00:00:00+00:00",
                    "2026-04-12T06:00:00+00:00",
                    "2026-04-12T12:00:00+00:00",
                ],
                "places": [
                    {
                        "location": {"label": "Miami, Florida, USA"},
                        "peak_score": 42,
                        "peak_datetime": "2026-04-12T00:00:00+00:00",
                        "peak_selection": "single_peak",
                        "candidate_kind": "early_peak_candidate",
                        "series": [],
                    }
                ],
                "peak_candidates": [
                    {
                        "rank": 1,
                        "location": {"label": "Miami, Florida, USA"},
                        "peak_score": 42,
                        "peak_datetime": "2026-04-12T00:00:00+00:00",
                        "peak_selection": "single_peak",
                    }
                ],
                "series_overview": {
                    "timeline_points": 3,
                    "place_count": 1,
                    "top_peak_location": {"label": "Miami, Florida, USA"},
                    "top_peak_datetime": "2026-04-12T00:00:00+00:00",
                    "top_peak_score": 42,
                },
            },
            "calibration": {"coverage_tier": "seeded", "unique_case_count": 4},
            "runtime_scope": "seed_weather_scan",
        }

    monkeypatch.setattr("weather_scan_service.run_weather_scan", fake_run)

    response = client.get(
        "/api/astro-clock/weather/scan/run?family_id=wind_event_pressure&scan_scope=place_timeline&location=Miami,%20Florida,%20USA&start_datetime=2026-04-12T00:00:00%2B00:00&end_datetime=2026-04-12T12:00:00%2B00:00&time_step_hours=6"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["runtime_scope"] == "seed_weather_scan"
    assert payload["data"]["series"]["series_overview"]["timeline_points"] == 3


def test_weather_scan_start_ignores_uncopyable_thread_in_progress_payload(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_weather_active_clock_context", _clock_payload)
    monkeypatch.setattr(
        weather_scan_service,
        "run_weather_scan",
        lambda request_model, *, active_clock, bundle_resolver, progress_callback=None: {
            "request": request_model.to_dict(),
            "counts": {"candidate_count": 1, "time_slices": 3, "evaluated": 3, "returned": 1},
            "scope": {"scan_scope": "place_timeline", "location": "Miami, Florida, USA"},
            "results": [{"rank": 1, "datetime": "2026-04-12T00:00:00+00:00", "location": {"label": "Miami, Florida, USA"}, "score": 42, "level": "active"}],
            "series": {"timeline": ["2026-04-12T00:00:00+00:00"], "places": [], "peak_candidates": [], "series_overview": {"timeline_points": 1, "place_count": 0}},
            "calibration": {"coverage_tier": "seeded", "unique_case_count": 4},
            "runtime_scope": "seed_weather_scan",
        },
    )

    class UncopyableThread:
        def __init__(self, target, name=None, daemon=None):
            self._target = target

        def start(self):
            return None

        def __deepcopy__(self, memo):
            raise TypeError("thread objects are not deepcopy-safe")

    monkeypatch.setattr(astro_clock_api.threading, "Thread", UncopyableThread)

    response = client.post(
        "/api/astro-clock/weather/scan/start",
        json={
            "family_id": "wind_event_pressure",
            "scan_scope": "place_timeline",
            "location": "Miami, Florida, USA",
            "start_datetime": "2026-04-12T00:00:00+00:00",
            "end_datetime": "2026-04-12T12:00:00+00:00",
            "time_step_hours": 6,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["progress"]["stage"] in {"queued", "pending"}


def test_weather_scan_async_start_progress_and_result(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(astro_clock_api, "_weather_active_clock_context", _clock_payload)

    def fake_run(request_model, *, active_clock, bundle_resolver, progress_callback=None):
        if progress_callback:
            progress_callback({
                "ready": False,
                "failed": False,
                "percent": 0.5,
                "stage": "running",
                "message": "Weather scan running",
                "done": 3,
                "total": 6,
                "candidate_count": 2,
                "time_slices": 3,
                "evaluated": 3,
                "returned": 2,
            })
        return {
            "request": request_model.to_dict(),
            "counts": {"candidate_count": 2, "time_slices": 3, "evaluated": 6, "returned": 2},
            "scope": {"scan_scope": "region_timeline", "region": {"id": "global", "label": "Global"}, "resolution": "standard"},
            "results": [
                {
                    "rank": 1,
                    "datetime": "2026-04-12T06:00:00+00:00",
                    "location": {"label": "Miami, Florida, USA", "timezone": "America/New_York"},
                    "score": 42,
                    "level": "active",
                    "scan_level": "dominant",
                    "matched_rules": [],
                    "signals": {},
                }
            ],
            "series": {
                "timeline": [
                    "2026-04-12T00:00:00+00:00",
                    "2026-04-12T06:00:00+00:00",
                    "2026-04-12T12:00:00+00:00",
                ],
                "places": [
                    {
                        "location": {"label": "Miami, Florida, USA"},
                        "peak_score": 42,
                        "peak_datetime": "2026-04-12T06:00:00+00:00",
                        "peak_selection": "single_peak",
                        "candidate_kind": "early_peak_candidate",
                        "series": [],
                    }
                ],
                "peak_candidates": [
                    {
                        "rank": 1,
                        "location": {"label": "Miami, Florida, USA"},
                        "peak_score": 42,
                        "peak_datetime": "2026-04-12T06:00:00+00:00",
                        "peak_selection": "single_peak",
                    }
                ],
                "series_overview": {
                    "timeline_points": 3,
                    "place_count": 1,
                    "top_peak_location": {"label": "Miami, Florida, USA"},
                    "top_peak_datetime": "2026-04-12T06:00:00+00:00",
                    "top_peak_score": 42,
                },
            },
            "calibration": {"coverage_tier": "seeded", "unique_case_count": 4},
            "runtime_scope": "seed_weather_scan",
        }

    monkeypatch.setattr("weather_scan_service.run_weather_scan", fake_run)

    start_response = client.post(
        "/api/astro-clock/weather/scan/start",
        json={
            "family_id": "wind_event_pressure",
            "scan_scope": "region_timeline",
            "region_id": "global",
            "start_datetime": "2026-04-12T00:00:00+00:00",
            "end_datetime": "2026-04-12T12:00:00+00:00",
            "time_step_hours": 6,
        },
    )
    start_payload = start_response.get_json()

    assert start_response.status_code == 200
    assert start_payload["success"] is True
    session_id = start_payload["data"]["session_id"]
    assert session_id

    progress_response = client.get(f"/api/astro-clock/weather/scan/progress?session_id={session_id}")
    progress_payload = progress_response.get_json()

    assert progress_response.status_code == 200
    assert progress_payload["success"] is True

    result_payload = None
    for _ in range(30):
        result_response = client.get(f"/api/astro-clock/weather/scan/result?session_id={session_id}")
        result_payload = result_response.get_json()
        if result_payload["data"]["ready"] or result_payload["data"]["failed"]:
            break
        time.sleep(0.01)

    assert result_response.status_code == 200
    assert result_payload["success"] is True
    assert result_payload["data"]["ready"] is True
    assert result_payload["data"]["result"]["runtime_scope"] == "seed_weather_scan"
    assert result_payload["data"]["progress"]["evaluated"] == 6
