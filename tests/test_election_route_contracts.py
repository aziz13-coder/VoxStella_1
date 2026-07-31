from __future__ import annotations

import json
import sys
import types
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
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


def _extract_sse_payloads(raw_sse: str) -> list[dict]:
    payloads = []
    for chunk in raw_sse.split("\n\n"):
        chunk = chunk.strip()
        if chunk.startswith("data: "):
            payloads.append(json.loads(chunk[6:]))
    return payloads


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


def test_validate_and_stream_reject_unknown_matter_instead_of_falling_back():
    app = _make_app()
    client = app.test_client()
    query = _base_query(matter="not-a-real-election-model")

    validate_resp = client.get(f"/api/astro-clock/election/validate?{query}")
    stream_resp = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert validate_resp.status_code == 400
    assert stream_resp.status_code == 400
    assert "Unknown election matter" in validate_resp.get_json()["error"]
    assert validate_resp.get_json()["error"] == stream_resp.get_json()["error"]


def test_validate_and_stream_reject_invalid_limits_consistently(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    app = _make_app()
    client = app.test_client()

    for invalid_limit, expected_error in (
        ("not-an-integer", "Invalid limit"),
        ("0", "limit must be >= 1"),
        ("-5", "limit must be >= 1"),
    ):
        query = _base_query(limit=invalid_limit)
        validate_resp = client.get(f"/api/astro-clock/election/validate?{query}")
        stream_resp = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

        assert validate_resp.status_code == 400
        assert stream_resp.status_code == 400
        assert validate_resp.get_json()["error"] == expected_error
        assert stream_resp.get_json()["error"] == expected_error

    assert astro_clock_api._parse_transit_limit("9999", max_value=200) == (200, None)


def test_validate_and_stream_reject_invalid_line_extraction_options_consistently(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    app = _make_app()
    client = app.test_client()
    cases = (
        (
            _base_query(
                matter="business",
                business_algorithm="beta",
                participant_snap_id="participant-a",
                business_beta_display_mode="invalid",
            ),
            "business_beta_display_mode must be total or detail",
        ),
        (
            _base_query(
                matter="business",
                business_algorithm="beta",
                participant_snap_id="participant-a",
                business_beta_scope="invalid",
            ),
            "business_beta_scope must be all, current, or selected",
        ),
        (
            _base_query(
                matter="estate",
                estate_participant_snap_id="participant-a",
                estate_display_mode="invalid",
            ),
            "estate_display_mode must be total or detail",
        ),
        (
            _base_query(
                matter="estate",
                estate_participant_snap_id="participant-a",
                estate_scope="invalid",
            ),
            "estate_scope must be all, current, or selected",
        ),
    )

    for query, expected_error in cases:
        validate_resp = client.get(f"/api/astro-clock/election/validate?{query}")
        stream_resp = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

        assert validate_resp.status_code == 400
        assert stream_resp.status_code == 400
        assert validate_resp.get_json()["error"] == expected_error
        assert stream_resp.get_json()["error"] == expected_error


def test_reference_parity_validates_complete_thirty_day_minute_scan(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, **kwargs: {
            "chart_data": _business_chart(),
            "meta": {"timestamp": "1990-01-01T00:00:00Z"},
        },
    )
    app = _make_app()
    client = app.test_client()
    query = _base_query(
        matter="marriage",
        marriage_algorithm="beta",
        participant_a_snap_id="participant-a",
        participant_b_snap_id="participant-b",
        start="2026-03-01T00:00:00Z",
        end="2026-03-31T00:00:00Z",
        step_minutes="60",
        reference_parity="1",
    )

    response = client.get(f"/api/astro-clock/election/validate?{query}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["reference_parity"] is True
    assert payload["step_minutes"] == 1
    assert payload["total_steps"] == 43_201


def test_stream_reports_aggregated_step_failures(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())

    def _raise_chart_failure(*args, **kwargs):
        raise RuntimeError("synthetic chart failure")

    monkeypatch.setattr(astro_clock_api, "_compute_chart_for", _raise_chart_failure)
    app = _make_app()
    client = app.test_client()
    query = _base_query(end="2026-03-08T00:01:00Z", step_minutes="1", include_series="0")

    response = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert response.status_code == 200
    payload = _extract_done_payload(response.get_data(as_text=True))
    assert payload["top"] == []
    assert payload["stats"]["attempted"] == 2
    assert payload["stats"]["failed"] == 2
    assert payload["stats"]["failure_reasons"] == {"RuntimeError": 2}
    assert len(payload["stats"]["failure_samples"]) == 2
    assert payload["stats"]["failure_samples"][0]["message"] == "synthetic chart failure"


def test_stream_throttles_progress_events_for_dense_scans(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda dt_iso, location, tz_name, house_system_code=None: (
            _business_chart(),
            {"timestamp": dt_iso},
        ),
    )
    app = _make_app()
    query = _base_query(
        end="2026-03-08T10:00:00Z",
        step_minutes="1",
        include_series="0",
        limit="1",
    )

    response = app.test_client().get(
        f"/api/astro-clock/election/suggest/stream?{query}"
    )

    assert response.status_code == 200
    payloads = _extract_sse_payloads(response.get_data(as_text=True))
    progress = [item for item in payloads if item.get("type") == "progress"]
    assert 2 <= len(progress) <= 501
    assert progress[0]["progress"] == 0.0
    assert progress[-1]["progress"] == 1.0
    assert payloads[-1]["type"] == "done"


def test_mercury_direct_station_timeline_bisects_speed_sign_change(monkeypatch):
    class FakeSwissEphemeris:
        GREG_CAL = 1
        FLG_SWIEPH = 2
        FLG_SPEED = 256
        MERCURY = 2

        @staticmethod
        def julday(*args):
            return 1000.0

        @staticmethod
        def calc_ut(jd, planet_id, flags):
            assert planet_id == FakeSwissEphemeris.MERCURY
            return ([0.0, 0.0, 0.0, jd - 1110.0], flags)

    monkeypatch.setattr(astro_clock_api, "require_swisseph", lambda: FakeSwissEphemeris())
    monkeypatch.setattr(astro_clock_api, "_resolve_synastry_ephemeris_path", lambda: "test-ephemeris")
    monkeypatch.setattr(
        astro_clock_api,
        "swisseph_ephemeris_path",
        lambda *args, **kwargs: nullcontext(),
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    stations = astro_clock_api._mercury_direct_station_times(
        start,
        start + timedelta(days=1),
    )

    assert len(stations) == 1
    assert abs((stations[0] - (start - timedelta(days=10))).total_seconds()) < 1.0


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


def test_lunar_fertility_requires_natal_source(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))

    app = _make_app()
    client = app.test_client()
    query = _base_query(matter="lunar_fertility", consider_mode="phase_and_antiphase")

    validate_resp = client.get(f"/api/astro-clock/election/validate?{query}")
    stream_resp = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert validate_resp.status_code == 400
    assert stream_resp.status_code == 400
    assert "requires" in validate_resp.get_json()["error"].lower()
    assert validate_resp.get_json()["error"] == stream_resp.get_json()["error"]


def test_election_stream_returns_400_when_requested_natal_snap_is_unsafe(
    monkeypatch,
):
    monkeypatch.setattr(
        astro_clock_api,
        "_ensure_coords_for_location",
        lambda _location: (31.778, 35.235),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda _args: (_ for _ in ()).throw(
            ValueError("Confirm/correct the saved context first")
        ),
    )

    app = _make_app()
    client = app.test_client()
    queries = (
        _base_query(natal_snap_id="legacy-review-required"),
        _base_query(
            natal_datetime="2001-02-03T12:15:00Z",
            natal_location="Jerusalem",
        ),
    )
    for query in queries:
        response = client.get(
            f"/api/astro-clock/election/suggest/stream?{query}"
        )

        assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "Confirm/correct the saved context first",
    }


def test_election_stream_returns_400_when_requested_direct_natal_context_fails(
    monkeypatch,
):
    monkeypatch.setattr(
        astro_clock_api,
        "_ensure_coords_for_location",
        lambda _location: (31.778, 35.235),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda _args: (_ for _ in ()).throw(
            ValueError("Direct natal context could not be constructed")
        ),
    )

    app = _make_app()
    response = app.test_client().get(
        f"/api/astro-clock/election/suggest/stream?"
        f"{_base_query(
            natal_datetime='not-an-iso-datetime',
            natal_location='Jerusalem',
            natal_timezone='Asia/Jerusalem',
            latitude='31.778',
            longitude='35.235',
        )}"
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "Direct natal context could not be constructed",
    }


def test_election_stream_rejects_incomplete_explicit_direct_natal_context(
    monkeypatch,
):
    monkeypatch.setattr(
        astro_clock_api,
        "_ensure_coords_for_location",
        lambda _location: (31.778, 35.235),
    )

    app = _make_app()
    response = app.test_client().get(
        f"/api/astro-clock/election/suggest/stream?"
        f"{_base_query(natal_datetime='1990-01-01T00:00:00Z')}"
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "natal_datetime and natal_location required",
    }


def test_election_precision_requires_saved_birth_time_quality():
    unknown = astro_clock_api._election_precision_from_saved_bundle(
        {"chart_data": {}, "meta": {}}
    )
    certified = astro_clock_api._election_precision_from_saved_bundle({
        "birth_time": {
            "status": "certified",
            "ranking_eligible": True,
            "ranking_eligibility": "confirmed",
        },
    })

    assert unknown == {
        "precision_class": "unknown",
        "precision_safe": False,
        "precision_source": "saved_birth_time_quality:unclassified",
    }
    assert certified == {
        "precision_class": "certified",
        "precision_safe": True,
        "precision_source": "saved_birth_time_quality:confirmed",
    }


def test_lunar_fertility_stream_returns_period_payload(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda lat, lon: None)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, *, house_system_code=None, missing_error="Snap not found": {
            "chart_data": _business_chart(),
            "meta": {"timestamp": "1990-01-01T00:00:00Z", "house_system_code": house_system_code},
        },
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
                    "score": 98.0,
                    "tags": ["Lunar fertility window", "Phase"],
                    "phase_kind": "phase",
                    "sex_label": "female",
                }
            ],
            "series": [
                {
                    "timestamp": "2026-03-08T00:00:00+00:00",
                    "timestamp_local": "2026-03-08T00:00:00+00:00",
                    "score": 98.0,
                    "tags": ["Lunar fertility window", "Phase"],
                    "phase_kind": "phase",
                    "sex_label": "female",
                }
            ],
            "periods": [
                {
                    "id": "lfp-1",
                    "start": "2026-03-08T00:00:00+00:00",
                    "end": "2026-03-08T00:59:59+00:00",
                    "best_timestamp": "2026-03-08T00:00:00+00:00",
                    "best_score": 98.0,
                    "phase_kind": "phase",
                    "sex_label": "female",
                }
            ],
            "anchors": [{"timestamp": "2026-03-08T00:00:00+00:00", "phase_kind": "phase"}],
            "signature": {"target_elongation": 30.0},
            "stats": {"attempted": 1, "favorable_total": 1, "passing_total": 1, "period_count": 1},
        },
    )

    app = _make_app()
    client = app.test_client()
    query = _base_query(
        matter="lunar_fertility",
        natal_snap_id="snap-natal",
        consider_mode="phase_and_antiphase",
        level_percent="33",
        limit="1",
    )

    response = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert response.status_code == 200
    payload = _extract_done_payload(response.get_data(as_text=True))
    assert payload["matter"] == "lunar_fertility"
    assert payload["consider_mode"] == "phase_and_antiphase"
    assert payload["periods"][0]["id"] == "lfp-1"
    assert payload["top"][0]["score"] == 98.0
    assert payload["stats"]["series_retained"] == 1


def test_lunar_fertility_stream_applies_day_hour_filters(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda lat, lon: None)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, *, house_system_code=None, missing_error="Snap not found": {
            "chart_data": _business_chart(),
            "meta": {"timestamp": "1990-01-01T00:00:00Z", "house_system_code": house_system_code},
        },
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
                    "timestamp": "2026-03-08T08:00:00+00:00",
                    "timestamp_local": "2026-03-08T08:00:00+00:00",
                    "score": 99.0,
                    "passes_level": True,
                    "phase_kind": "phase",
                    "sex_label": "female",
                },
                {
                    "timestamp": "2026-03-08T10:00:00+00:00",
                    "timestamp_local": "2026-03-08T10:00:00+00:00",
                    "score": 88.0,
                    "passes_level": True,
                    "phase_kind": "phase",
                    "sex_label": "female",
                },
            ],
            "series": [
                {
                    "timestamp": "2026-03-08T08:00:00+00:00",
                    "timestamp_local": "2026-03-08T08:00:00+00:00",
                    "score": 99.0,
                    "passes_level": True,
                    "phase_kind": "phase",
                    "sex_label": "female",
                },
                {
                    "timestamp": "2026-03-08T10:00:00+00:00",
                    "timestamp_local": "2026-03-08T10:00:00+00:00",
                    "score": 88.0,
                    "passes_level": True,
                    "phase_kind": "phase",
                    "sex_label": "female",
                },
            ],
            "periods": [],
            "anchors": [],
            "signature": {},
            "stats": {"attempted": 2, "favorable_total": 2, "passing_total": 2, "period_count": 1},
        },
    )

    app = _make_app()
    client = app.test_client()
    query = _base_query(
        matter="lunar_fertility",
        start="2026-03-08T00:00:00Z",
        end="2026-03-08T12:00:00Z",
        natal_snap_id="snap-natal",
        consider_mode="phase_and_antiphase",
        level_percent="33",
        hour_start="09:00",
        hour_end="11:00",
        limit="5",
    )

    response = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert response.status_code == 200
    payload = _extract_done_payload(response.get_data(as_text=True))
    assert [row["timestamp"] for row in payload["top"]] == ["2026-03-08T10:00:00+00:00"]
    assert [row["timestamp"] for row in payload["series"]] == ["2026-03-08T10:00:00+00:00"]
    assert payload["periods"][0]["start"] == "2026-03-08T10:00:00+00:00"
    assert payload["stats"]["kept_total"] == 1
    assert payload["stats"]["unfiltered_favorable_total"] == 2


def test_lunar_fertility_stream_keeps_full_hourly_series_by_default(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_STREAM_MAX_WINDOW_HOURS", 1000.0)
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda location: (31.778, 35.235))
    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda lat, lon: None)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: object())
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, *, house_system_code=None, missing_error="Snap not found": {
            "chart_data": _business_chart(),
            "meta": {"timestamp": "1990-01-01T00:00:00Z", "house_system_code": house_system_code},
        },
    )
    monkeypatch.setattr(astro_clock_api, "_lunar_fertility_ephemeris_adapter", lambda: object())

    base_dt = datetime(2026, 3, 8, tzinfo=timezone.utc)
    rows = [
        {
            "timestamp": (base_dt + timedelta(hours=idx)).isoformat(),
            "timestamp_local": (base_dt + timedelta(hours=idx)).isoformat(),
            "score": 50.0 + (idx % 50),
            "passes_level": True,
            "phase_kind": "phase",
            "sex_label": "female",
        }
        for idx in range(800)
    ]
    monkeypatch.setattr(
        astro_clock_api,
        "scan_lunar_fertility_windows",
        lambda natal_cd, start_dt, end_dt, **kwargs: {
            "matter": "lunar_fertility",
            "consider_mode": kwargs.get("consider_mode"),
            "level_percent": kwargs.get("level_percent"),
            "top": rows[:5],
            "series": rows,
            "periods": [],
            "anchors": [],
            "signature": {},
            "stats": {"attempted": len(rows), "favorable_total": len(rows), "passing_total": len(rows), "period_count": 1},
        },
    )

    app = _make_app()
    client = app.test_client()
    query = _base_query(
        matter="lunar_fertility",
        start="2026-03-08T00:00:00Z",
        end="2026-04-10T00:00:00Z",
        natal_snap_id="snap-natal",
        consider_mode="phase_and_antiphase",
        level_percent="33",
        limit="5",
    )

    response = client.get(f"/api/astro-clock/election/suggest/stream?{query}")

    assert response.status_code == 200
    payload = _extract_done_payload(response.get_data(as_text=True))
    assert payload["stats"]["series_retained"] == 800
    assert payload["stats"]["series_dropped"] == 0
    assert len(payload["series"]) == 800


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
