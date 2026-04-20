from datetime import datetime, timezone
from pathlib import Path
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
import context_layers
import primary_directions


def _clock_payload():
    return {
        "timestamp": datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc).isoformat(),
        "location": "Paris, France",
        "timezone": "Europe/Paris",
        "mode": "manual",
        "house_system_code": "R",
        "latitude": 48.8566,
        "longitude": 2.3522,
    }


def test_transits_context_auto_returns_context_maturity(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda args: (
            {
                "house_rulers": {"1": "Saturn", "10": "Jupiter"},
                "planets": {"Sun": {"longitude": 10.0}, "Moon": {"longitude": 20.0}},
            },
            {
                "timestamp": "1583-02-23T05:45:00+00:00",
                "location": "Villefranche, France",
                "timezone": "Europe/Paris",
            },
        ),
    )
    monkeypatch.setattr(
        context_layers,
        "compute_solar_arc_windows",
        lambda natal_dt, year, natal_cd: [
            {"start": "1613-05-01T00:00:00+00:00", "end": "1613-05-03T00:00:00+00:00", "label": "Solar Arc Window"}
        ],
    )
    monkeypatch.setattr(
        context_layers,
        "compute_progressed_planet_windows",
        lambda natal_dt, year, natal_cd: [
            {
                "start": "1613-05-08T00:00:00+00:00",
                "end": "1613-05-10T00:00:00+00:00",
                "outer_start": "1613-05-07T00:00:00+00:00",
                "outer_end": "1613-05-11T00:00:00+00:00",
                "label": "Progressed Window",
            }
        ],
    )
    monkeypatch.setattr(context_layers, "suggest_focus_from_natal", lambda natal_cd: ([1, 10], ["Saturn", "Jupiter"]))
    monkeypatch.setattr(
        primary_directions,
        "compute_primary_direction_windows",
        lambda natal_dt, year, natal_cd: [
            {"start": "1613-05-09T00:00:00+00:00", "end": "1613-05-10T00:00:00+00:00", "label": "PD Window"}
        ],
    )

    response = client.get(
        "/api/astro-clock/context/auto",
        query_string={
            "natal_datetime": "1583-02-23T05:45:00+00:00",
            "natal_location": "Villefranche, France",
            "natal_timezone": "Europe/Paris",
            "anchor_center": "1613-05-09T12:00:00+00:00",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert "context_maturity" in data
    maturity = data["context_maturity"]
    assert maturity["primary_directions"]["level"] == "partial"
    assert maturity["solar_arc"]["level"] == "partial"
    assert maturity["secondary_progressions"]["level"] == "partial"
    assert maturity["solar_return"]["level"] == "partial"
    assert maturity["lunar_return"]["level"] == "helper_only"
    assert maturity["focus_suggestions"]["level"] == "helper_only"


def test_prediction_sort_prioritizes_crisis_angle_testimony_over_benefic_honors():
    honors = {
        "event_type": "promotion",
        "life_area": "honors",
        "probability": 0.261,
        "score": 0.0,
        "label": "Sun Trine Jupiter",
        "factors": {
            "transit": "Sun Trine Jupiter",
            "determination_strength": 0.0,
            "significance": 0.0,
        },
    }
    crisis = {
        "event_type": "accident_major",
        "life_area": "danger",
        "probability": 1.0,
        "score": 30.0,
        "label": "Mars Quincunx Asc",
        "factors": {
            "transit": "Mars Quincunx Asc",
            "direction": "Danger direction @ 1615-07-07T12:00:00+00:00",
            "determination_strength": -0.9,
            "significance": -8.0,
        },
    }

    ranked = sorted([honors, crisis], key=astro_clock_api._prediction_sort_key)

    assert ranked[0]["event_type"] == "accident_major"
    assert astro_clock_api._prediction_domain_alignment(crisis) == 1.0
    assert astro_clock_api._prediction_crisis_focus(crisis) > 0.0


def test_select_dominant_occurrence_uses_midpoint_of_strongest_band():
    occurrences = [
        {"date": "1615-07-01T00:00:00+00:00", "support_score": 86.3, "score": 30.0},
        {"date": "1615-07-04T12:00:00+00:00", "support_score": 86.3, "score": 30.0},
        {"date": "1615-07-08T12:00:00+00:00", "support_score": 86.3, "score": 30.0},
        {"date": "1615-07-12T00:00:00+00:00", "support_score": 86.3, "score": 30.0},
        {"date": "1615-07-14T12:00:00+00:00", "support_score": 86.3, "score": 30.0},
    ]

    dominant = astro_clock_api._select_dominant_occurrence(occurrences)

    assert dominant == "1615-07-08T12:00:00+00:00"
