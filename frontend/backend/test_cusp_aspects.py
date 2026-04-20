from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import builtins
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
from cusp_aspects import compute_cusp_aspects


def _houses():
    return [i * 30.0 for i in range(12)]


def test_compute_cusp_aspects_uses_caller_future_chart_data_without_engine_import(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "astro_clock_engine":
            raise AssertionError("compute_cusp_aspects should not import astro_clock_engine")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    chart_data = {
        "houses": _houses(),
        "planets": [
            {"planet": "Mars", "longitude": 0.8, "speed": 1.0, "house": 1},
        ],
    }
    future_chart_data = {
        "houses": _houses(),
        "planets": [
            {"planet": "Mars", "longitude": 0.4, "speed": 1.0, "house": 1},
        ],
    }

    result = compute_cusp_aspects(
        chart_data,
        timestamp_iso="2026-04-14T12:00:00+00:00",
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        future_chart_data=future_chart_data,
    )

    hit = result["H1"][0]
    assert hit["planet"] == "Mars"
    assert hit["aspect"] == "Conjunction"
    assert hit["phase"] == "applying"
    assert hit["applying"] is True


def test_compute_cusp_aspects_uses_speed_fallback_when_future_chart_data_is_missing():
    applying_chart = {
        "houses": _houses(),
        "planets": [
            {"planet": "Mars", "longitude": 0.8, "speed": -1.0, "house": 1},
        ],
    }

    separating_chart = {
        "houses": _houses(),
        "planets": [
            {"planet": "Mars", "longitude": 0.8, "speed": 1.0, "house": 1},
        ],
    }

    applying_result = compute_cusp_aspects(
        applying_chart,
        timestamp_iso="2026-04-14T12:00:00+00:00",
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
    )
    separating_result = compute_cusp_aspects(
        separating_chart,
        timestamp_iso="2026-04-14T12:00:00+00:00",
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
    )

    applying_hit = applying_result["H1"][0]
    separating_hit = separating_result["H1"][0]

    assert applying_hit["phase"] == "applying"
    assert applying_hit["applying"] is True
    assert separating_hit["phase"] == "separating"
    assert separating_hit["applying"] is False


def test_dashboard_payload_supplies_future_chart_data_to_cusp_aspects(monkeypatch):
    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Jerusalem, Israel",
        custom_time=None,
        timezone="Asia/Jerusalem",
        house_system_code="R",
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "houses": _houses(),
                "house_rulers": {"1": "Mars"},
                "planets": [
                    {"planet": "Mars", "longitude": 0.8, "speed": 1.0, "sign": "Aries", "house": 1},
                    {"planet": "Moon", "longitude": 12.0, "speed": 13.0, "sign": "Aries", "house": 1},
                ],
                "aspects": [],
            }
        },
        moon_state=None,
        dispositor_chains={},
        current_aspects=[],
    )
    eng = SimpleNamespace(settings=settings)
    future_chart_data = {
        "houses": _houses(),
        "planets": [
            {"planet": "Mars", "longitude": 0.4, "speed": 1.0, "house": 1},
        ],
    }
    captured = {}

    monkeypatch.setattr(astro_clock_api, "_future_cusp_phase_chart_data", lambda *args, **kwargs: future_chart_data)
    monkeypatch.setattr(astro_clock_api, "compute_fixed_star_hits", lambda *args, **kwargs: [])
    monkeypatch.setattr(astro_clock_api, "compute_arabic_parts", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "_extract_receptions_payload", lambda *args, **kwargs: {"mutual": [], "top_unilateral": []})

    def capture_cusp_aspects(chart_data, **kwargs):
        captured["future_chart_data"] = kwargs.get("future_chart_data")
        return {}

    monkeypatch.setattr(astro_clock_api, "compute_cusp_aspects", capture_cusp_aspects)

    with app_module.app.test_request_context("/api/astro-clock/dashboard"):
        payload = astro_clock_api._build_dashboard_payload(eng, data)

    assert payload["cusp_aspects"] == {}
    assert captured["future_chart_data"] is future_chart_data
