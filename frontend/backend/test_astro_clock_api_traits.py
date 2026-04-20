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
import house_influence


def test_traits_profile_does_not_depend_on_dashboard_builder(monkeypatch):
    client = app_module.app.test_client()

    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Paris, France",
        custom_time=None,
        timezone="Europe/Paris",
        house_system_code="R",
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "ascendant": 15.5,
                "midheaven": 102.2,
                "houses": [i * 30.0 for i in range(12)],
                "house_rulers": {"1": "Venus", "10": "Saturn"},
                "planets": [
                    {"planet": "Sun", "longitude": 10.0, "sign": "Aries", "house": 1},
                    {"planet": "Moon", "longitude": 52.0, "sign": "Taurus", "house": 2},
                    {"planet": "Venus", "longitude": 25.0, "sign": "Aries", "house": 1},
                ],
                "aspects": [
                    {"planet1": "Sun", "planet2": "Moon", "aspect": "Sextile", "orb": 1.2},
                    {"planet1": "Sun", "planet2": "Venus", "aspect": "Conjunction", "orb": 0.6},
                ],
                "solar_conditions_summary": {
                    "free_planets": [{"planet": "Moon"}],
                    "combusted_planets": [{"planet": "Venus", "distance_from_sun": 5.1}],
                },
            },
            "reception_details": {
                "mutual_receptions": [
                    {"planet1": "Venus", "planet2": "Moon", "type": "mutual_reception", "strength": 4}
                ]
            },
        },
        moon_state=None,
        dispositor_chains={},
        current_aspects=[],
    )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: SimpleNamespace(settings=settings))
    monkeypatch.setattr(astro_clock_api, "_data_for_request_clock_context", lambda eng: (data, settings))
    monkeypatch.setattr(
        astro_clock_api,
        "_build_dashboard_payload",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("dashboard path should not be used")),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "compute_metrics",
        lambda cd, timestamp_iso=None, special_degrees=None: {
            "sign_emphasis": {"Aries": 2.0, "Taurus": 1.0},
            "element_balance": {"Fire": 2.0, "Earth": 1.0, "Air": 0.0, "Water": 0.0},
            "modality_balance": {"Cardinal": 2.0, "Fixed": 1.0, "Mutable": 0.0},
            "planet_status": {"Sun": {"strong": True}, "Moon": {"strong": False}},
            "planetary_aspects": [],
            "house_rulers": {"1": "Venus", "10": "Saturn"},
        },
    )
    monkeypatch.setattr(
        house_influence,
        "compute_house_influences",
        lambda cd, metrics: {"houses": [], "planet_strengths": {"Sun": 1.0}},
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_traits_engine_instance",
        lambda: SimpleNamespace(
            evaluate=lambda metrics: {
                "summary": "Fast trait summary",
                "top_traits": [{"id": "sun_aries", "name": "Sun in Aries", "score": 42.0}],
                "summary_traits": [],
                "top_traits_by_polarity": {},
                "traits": [],
                "guidance": [],
                "trait_enrichment_meta": {"version": 1},
            }
        ),
    )

    response = client.get("/api/astro-clock/traits/profile")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data_payload = payload["data"]
    assert data_payload["summary"] == "Fast trait summary"
    assert data_payload["top_traits"][0]["id"] == "sun_aries"
    assert data_payload["chart_snapshot"]["timestamp"] == "2026-04-14T12:00:00+00:00"
    assert data_payload["chart_snapshot"]["location"] == "Paris, France"
    assert data_payload["chart_snapshot"]["house_cusps"]
    assert data_payload["receptions"]["mutual"][0]["p1"] == "Venus"


def test_traits_profile_perf_logging_is_opt_in_and_non_disruptive(monkeypatch):
    client = app_module.app.test_client()

    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Paris, France",
        custom_time=None,
        timezone="Europe/Paris",
        house_system_code="R",
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "ascendant": 15.5,
                "midheaven": 102.2,
                "houses": [i * 30.0 for i in range(12)],
                "house_rulers": {"1": "Venus", "10": "Saturn"},
                "planets": [
                    {"planet": "Sun", "longitude": 10.0, "sign": "Aries", "house": 1},
                    {"planet": "Moon", "longitude": 52.0, "sign": "Taurus", "house": 2},
                    {"planet": "Venus", "longitude": 25.0, "sign": "Aries", "house": 1},
                ],
                "aspects": [
                    {"planet1": "Sun", "planet2": "Moon", "aspect": "Sextile", "orb": 1.2},
                    {"planet1": "Sun", "planet2": "Venus", "aspect": "Conjunction", "orb": 0.6},
                ],
            },
            "reception_details": {
                "mutual_receptions": [
                    {"planet1": "Venus", "planet2": "Moon", "type": "mutual_reception", "strength": 4}
                ]
            },
        },
        moon_state=None,
        dispositor_chains={},
        current_aspects=[],
    )

    captured_logs = []

    def capture_info(message, *args, **kwargs):
        rendered = message % args if args else str(message)
        captured_logs.append(rendered)

    monkeypatch.setenv("VOX_STELLA_ASTRO_PERF", "1")
    monkeypatch.setattr(astro_clock_api.logger, "info", capture_info)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: SimpleNamespace(settings=settings))
    monkeypatch.setattr(astro_clock_api, "_data_for_request_clock_context", lambda eng: (data, settings))
    monkeypatch.setattr(
        astro_clock_api,
        "compute_metrics",
        lambda cd, timestamp_iso=None, special_degrees=None: {
            "sign_emphasis": {"Aries": 2.0, "Taurus": 1.0},
            "element_balance": {"Fire": 2.0, "Earth": 1.0, "Air": 0.0, "Water": 0.0},
            "modality_balance": {"Cardinal": 2.0, "Fixed": 1.0, "Mutable": 0.0},
        },
    )
    monkeypatch.setattr(
        house_influence,
        "compute_house_influences",
        lambda cd, metrics: {"houses": [], "planet_strengths": {"Sun": 1.0}},
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_traits_engine_instance",
        lambda: SimpleNamespace(
            evaluate=lambda metrics: {
                "summary": "Fast trait summary",
                "top_traits": [{"id": "sun_aries", "name": "Sun in Aries", "score": 42.0}],
                "summary_traits": [],
                "top_traits_by_polarity": {},
                "traits": [],
                "guidance": [],
                "trait_enrichment_meta": {"version": 1},
            }
        ),
    )

    response = client.get("/api/astro-clock/traits/profile")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["summary"] == "Fast trait summary"
    assert any("[astro-perf]" in entry and "span=route.traits_profile" in entry for entry in captured_logs)
