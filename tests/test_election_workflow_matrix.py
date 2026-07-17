from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlencode

import pytest
from flask import Flask


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api


def _make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def _generic_chart() -> dict:
    return {
        "house_cusps": [float(i * 30.0) for i in range(12)],
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 45.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 13.4},
            "Mercury": {"planet": "Mercury", "longitude": 75.0, "sign": "Gemini", "house": 3, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 120.0, "sign": "Leo", "house": 5, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 350.0, "sign": "Pisces", "house": 12, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 300.0, "sign": "Aquarius", "house": 11, "retrograde": False, "speed": 0.1},
            "North Node": {"planet": "North Node", "longitude": 150.0, "sign": "Virgo", "house": 6, "retrograde": False},
        },
        "planetary_aspects_precise": [
            {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Square", "phase": "separating"},
            {"planet1": "Moon", "planet2": "Venus", "aspect": "Sextile", "phase": "applying"},
        ],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _extract_done_payload(raw_sse: str) -> dict:
    for chunk in raw_sse.split("\n\n"):
        chunk = chunk.strip()
        if not chunk.startswith("data: "):
            continue
        payload = json.loads(chunk[6:])
        if payload.get("type") == "done":
            return payload["data"]
    raise AssertionError("No done payload found in SSE response")


def _base_query(**overrides) -> str:
    params = {
        "start": "2026-03-08T00:00:00Z",
        "end": "2026-03-08T00:01:00Z",
        "location": "Jerusalem",
        "timezone": "UTC",
        "step_minutes": "60",
        "limit": "1",
    }
    params.update(overrides)
    return urlencode(params, doseq=True)


CASES = [
    ("marriage", {}),
    ("surgery", {"procedure": "cutting", "surgery_sign": "Aries"}),
    ("contract", {"prefer_fixed_asc": "1", "contract_mode": "new"}),
    ("business", {"business_mode": "growth", "include_traditional_timing": "1"}),
    ("estate", {"estate_direction": "buy", "estate_participant_snap_id": "snap-estate"}),
    ("journey", {"journey_type": "short"}),
    ("haircut", {"hair_goal": "growth"}),
    ("legal", {"legal_action": "filing"}),
    ("beautification", {"procedure_type": "fillers", "body_parts": "cheeks,lips"}),
    ("viral", {"include_traditional_timing": "1"}),
    ("battle", {"action_type": "attack"}),
    ("conception", {"gender": "male"}),
    ("lunar_fertility", {"natal_snap_id": "snap-estate", "consider_mode": "phase_and_antiphase", "level_percent": "33"}),
]


@pytest.mark.parametrize(("matter", "extra"), CASES)
def test_election_routes_support_each_registered_matter(monkeypatch, matter: str, extra: dict[str, str]):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda lat, lon: None)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda dt_iso, location, tz_name, house_system_code=None: (_generic_chart(), {"timestamp": dt_iso}),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, *, house_system_code=None, missing_error="Snap not found": {
            "chart_data": _generic_chart(),
            "meta": {"timestamp": "2026-03-08T00:00:00Z", "house_system_code": house_system_code},
        },
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_snaps",
        lambda: {"snap-estate": {"label": "Estate Participant", "location": "Jerusalem"}},
    )
    monkeypatch.setattr(astro_clock_api, "_lunar_fertility_ephemeris_adapter", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "scan_lunar_fertility_windows",
        lambda natal_cd, start_dt, end_dt, **kwargs: {
            "matter": "lunar_fertility",
            "consider_mode": kwargs.get("consider_mode"),
            "level_percent": kwargs.get("level_percent"),
            "top": [
                {
                    "timestamp": "2026-03-08T00:00:00+00:00",
                    "timestamp_local": "2026-03-08T00:00:00+00:00",
                    "score": 92.0,
                    "tags": ["Lunar fertility window", "Phase"],
                }
            ],
            "series": [
                {
                    "timestamp": "2026-03-08T00:00:00+00:00",
                    "timestamp_local": "2026-03-08T00:00:00+00:00",
                    "score": 92.0,
                    "tags": ["Lunar fertility window", "Phase"],
                }
            ],
            "periods": [],
            "anchors": [],
            "signature": {},
            "stats": {"attempted": 1, "favorable_total": 1, "passing_total": 1, "period_count": 0},
        },
    )

    app = _make_app()
    client = app.test_client()

    query = _base_query(matter=matter, **extra)
    validate_resp = client.get(f"/api/astro-clock/election/validate?{query}")
    stream_resp = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert validate_resp.status_code == 200
    assert stream_resp.status_code == 200

    payload = _extract_done_payload(stream_resp.get_data(as_text=True))
    assert payload["top"]
    top = payload["top"][0]
    assert isinstance(top["score"], (int, float))
    assert isinstance(top["tags"], list)
    assert payload["location"] == "Jerusalem"
    assert payload["timezone"] == "UTC"
