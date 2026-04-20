from __future__ import annotations

import json
import sys
import types
from datetime import datetime
from pathlib import Path

from flask import Flask

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api
from election import (
    score_battle_election,
    score_journey_election,
    score_legal_election,
    score_marriage_election,
    score_surgery_election,
)
from tests.election_stress_utils import (
    base_battle_chart,
    base_journey_chart,
    base_legal_chart,
    base_marriage_chart,
    base_surgery_chart,
    clone_chart,
)


def _make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def _base_query(**overrides) -> str:
    params = {
        "matter": "business",
        "start": "2026-03-08T00:00:00Z",
        "end": "2026-03-08T02:00:00Z",
        "location": "Jerusalem",
        "timezone": "UTC",
        "step_minutes": "60",
    }
    params.update(overrides)
    return "&".join(f"{key}={value}" for key, value in params.items())


def _extract_done_payload(raw_sse: str) -> dict:
    for chunk in raw_sse.split("\n\n"):
        chunk = chunk.strip()
        if not chunk.startswith("data: "):
            continue
        payload = json.loads(chunk[6:])
        if payload.get("type") == "done":
            return payload["data"]
    raise AssertionError("No done payload found in SSE response")


def _business_chart() -> dict:
    return {
        "house_cusps": [i * 30.0 for i in range(12)],
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 45.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 13.5},
            "Mercury": {"planet": "Mercury", "longitude": 285.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 120.0, "sign": "Leo", "house": 5, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 295.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 200.0, "sign": "Libra", "house": 7, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _normalize_direct_score(score_obj) -> tuple[float, list[str]]:
    if score_obj is None:
        return 0.0, []
    if isinstance(score_obj, (int, float)):
        return float(score_obj), []
    if isinstance(score_obj, dict):
        value = score_obj.get("value")
        if value is None:
            value = score_obj.get("score") or 0.0
        return float(value), list(score_obj.get("tags") or [])
    value = getattr(score_obj, "value", None)
    if value is None:
        value = getattr(score_obj, "score", 0.0)
    return float(value or 0.0), list(getattr(score_obj, "tags", []) or [])


def _assert_stream_parity(monkeypatch, *, chart: dict, matter: str, scorer, score_options: dict, query_overrides: dict) -> None:
    stream_timestamp = datetime.fromisoformat("2026-03-08T00:00:00+00:00")
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda lat, lon: None)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda dt_iso, location, tz_name, house_system_code=None: (clone_chart(chart), {"timestamp": dt_iso}),
    )

    app = _make_app()
    client = app.test_client()
    query = _base_query(
        matter=matter,
        end="2026-03-08T00:01:00Z",
        limit="1",
        include_series="0",
        **query_overrides,
    )

    response = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert response.status_code == 200
    payload = _extract_done_payload(response.get_data(as_text=True))
    assert payload["top"]

    route_top = payload["top"][0]
    effective_options = {
        "current_timestamp": stream_timestamp,
        "timezone": "UTC",
        **score_options,
    }
    expected_score, expected_tags = _normalize_direct_score(
        scorer(clone_chart(chart), options=effective_options)
    )

    assert route_top["score"] == expected_score
    assert route_top["tags"] == expected_tags
    assert route_top["timestamp"] == "2026-03-08T00:00:00+00:00"


def test_validate_and_stream_reject_zero_step_minutes_consistently(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))

    app = _make_app()
    client = app.test_client()
    query = _base_query(step_minutes="0")

    validate_resp = client.get(f"/api/astro-clock/election/validate?{query}")
    stream_resp = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert validate_resp.status_code == 400
    assert stream_resp.status_code == 400
    assert validate_resp.get_json()["error"] == "step_minutes must be >= 1"
    assert stream_resp.get_json()["error"] == "step_minutes must be >= 1"


def test_validate_and_stream_reject_oversized_windows_consistently(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))

    app = _make_app()
    client = app.test_client()
    query = _base_query(
        start="2026-03-01T00:00:00Z",
        end="2026-04-15T00:00:00Z",
    )

    validate_resp = client.get(f"/api/astro-clock/election/validate?{query}")
    stream_resp = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert validate_resp.status_code == 400
    assert stream_resp.status_code == 400
    assert "Requested range exceeds max window" in validate_resp.get_json()["error"]
    assert validate_resp.get_json()["error"] == stream_resp.get_json()["error"]


def test_stream_business_route_applies_natal_transit_hits(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda lat, lon: None)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda dt_iso, location, tz_name, house_system_code=None: (_business_chart(), {"timestamp": dt_iso}),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda args: (_business_chart(), {"timestamp": "1990-01-01T00:00:00Z", "location": "Jerusalem", "timezone": "UTC"}),
    )

    transits_mod = types.ModuleType("transits_morin")
    transits_mod.compute_morin_transits_to_natal = lambda *args, **kwargs: [
        {"transiting": "Jupiter", "aspect": "Trine", "target_label": "MC"}
    ]
    monkeypatch.setitem(sys.modules, "transits_morin", transits_mod)

    context_mod = types.ModuleType("context_layers")
    context_mod.compute_solar_return_timestamp = lambda natal_sun, year: None
    context_mod.compute_lunar_return_timestamps = lambda natal_moon, year: []
    monkeypatch.setitem(sys.modules, "context_layers", context_mod)

    app = _make_app()
    client = app.test_client()

    baseline_query = _base_query(
        end="2026-03-08T00:01:00Z",
        limit="1",
    )
    baseline_response = client.get(f"/api/astro-clock/election/suggest/stream?{baseline_query}")
    assert baseline_response.status_code == 200
    baseline_payload = _extract_done_payload(baseline_response.get_data(as_text=True))

    query = _base_query(
        end="2026-03-08T00:01:00Z",
        include_sr_lr="1",
        natal_snap_id="snap-1",
        limit="1",
    )

    response = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert response.status_code == 200
    payload = _extract_done_payload(response.get_data(as_text=True))
    assert baseline_payload["top"]
    assert payload["top"]
    baseline_top = baseline_payload["top"][0]
    top = payload["top"][0]
    assert top["score"] > baseline_top["score"]
    assert any("Directions proxy (business)" in tag for tag in top["tags"])
    assert not any("Directions proxy (business)" in tag for tag in baseline_top["tags"])


def test_stream_business_route_accepts_manual_natal_context(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda lat, lon: None)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda dt_iso, location, tz_name, house_system_code=None: (_business_chart(), {"timestamp": dt_iso}),
    )

    seen_args = {}

    def _fake_natal_from_query(args):
        seen_args["natal_datetime"] = args.get("natal_datetime")
        seen_args["natal_location"] = args.get("natal_location")
        seen_args["natal_timezone"] = args.get("natal_timezone")
        return _business_chart(), {"timestamp": "1990-01-01T00:00:00Z", "location": "Jerusalem", "timezone": "UTC"}

    monkeypatch.setattr(astro_clock_api, "_natal_from_query", _fake_natal_from_query)

    transits_mod = types.ModuleType("transits_morin")
    transits_mod.compute_morin_transits_to_natal = lambda *args, **kwargs: [
        {"transiting": "Jupiter", "aspect": "Trine", "target_label": "MC"}
    ]
    monkeypatch.setitem(sys.modules, "transits_morin", transits_mod)

    context_mod = types.ModuleType("context_layers")
    context_mod.compute_solar_return_timestamp = lambda natal_sun, year: None
    context_mod.compute_lunar_return_timestamps = lambda natal_moon, year: []
    monkeypatch.setitem(sys.modules, "context_layers", context_mod)

    app = _make_app()
    client = app.test_client()

    baseline_query = _base_query(
        end="2026-03-08T00:01:00Z",
        limit="1",
    )
    baseline_response = client.get(f"/api/astro-clock/election/suggest/stream?{baseline_query}")
    assert baseline_response.status_code == 200
    baseline_payload = _extract_done_payload(baseline_response.get_data(as_text=True))

    query = _base_query(
        end="2026-03-08T00:01:00Z",
        include_sr_lr="1",
        natal_datetime="1990-01-01T00:00:00Z",
        natal_location="Jerusalem",
        natal_timezone="UTC",
        limit="1",
    )

    response = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert response.status_code == 200
    payload = _extract_done_payload(response.get_data(as_text=True))
    assert baseline_payload["top"]
    assert payload["top"]
    baseline_top = baseline_payload["top"][0]
    top = payload["top"][0]
    assert seen_args == {
        "natal_datetime": "1990-01-01T00:00:00Z",
        "natal_location": "Jerusalem",
        "natal_timezone": "UTC",
    }
    assert top["score"] > baseline_top["score"]
    assert any("Directions proxy (business)" in tag for tag in top["tags"])


def test_stream_marriage_route_succeeds_without_natal_context(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda lat, lon: None)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda dt_iso, location, tz_name, house_system_code=None: (_business_chart(), {"timestamp": dt_iso}),
    )

    app = _make_app()
    client = app.test_client()
    query = _base_query(
        matter="marriage",
        end="2026-03-08T00:01:00Z",
        limit="1",
    )

    response = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert response.status_code == 200
    payload = _extract_done_payload(response.get_data(as_text=True))
    assert payload["top"]
    assert isinstance(payload["top"][0]["score"], (int, float))


def test_stream_surgery_route_matches_direct_scorer(monkeypatch):
    _assert_stream_parity(
        monkeypatch,
        chart=base_surgery_chart(),
        matter="surgery",
        scorer=score_surgery_election,
        score_options={"procedure": "cutting", "surgery_sign": "Leo"},
        query_overrides={"procedure": "cutting", "surgery_sign": "Leo"},
    )


def test_stream_journey_route_matches_direct_scorer(monkeypatch):
    _assert_stream_parity(
        monkeypatch,
        chart=base_journey_chart(),
        matter="journey",
        scorer=score_journey_election,
        score_options={},
        query_overrides={},
    )


def test_stream_battle_route_matches_direct_scorer(monkeypatch):
    _assert_stream_parity(
        monkeypatch,
        chart=base_battle_chart(),
        matter="battle",
        scorer=score_battle_election,
        score_options={"action_type": "attack"},
        query_overrides={"action_type": "attack"},
    )


def test_stream_marriage_route_matches_direct_scorer(monkeypatch):
    _assert_stream_parity(
        monkeypatch,
        chart=base_marriage_chart(),
        matter="marriage",
        scorer=score_marriage_election,
        score_options={},
        query_overrides={},
    )


def test_stream_legal_route_matches_direct_scorer(monkeypatch):
    _assert_stream_parity(
        monkeypatch,
        chart=base_legal_chart(),
        matter="legal",
        scorer=score_legal_election,
        score_options={"legal_action": "filing"},
        query_overrides={"legal_action": "filing"},
    )
