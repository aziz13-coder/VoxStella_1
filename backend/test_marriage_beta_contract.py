from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
import election
from election_models.common import Score
import election_models.marriage as marriage_model
import election_models.marriage_beta as marriage_beta
import moon_day


def _patch_validate_common(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda _location: (31.778, 35.235))
    monkeypatch.setattr(
        astro_clock_api,
        "_normalize_manual_datetime",
        lambda value, timezone_name=None, location=None: (
            datetime.fromisoformat(str(value).replace("Z", "+00:00")),
            timezone_name or "Asia/Jerusalem",
        ),
    )
    monkeypatch.setattr(astro_clock_api, "_validate_stream_scan_bounds", lambda _sdt, _edt, _step: (3, None))


def _houses(start: float = 0.0):
    return [((start + i * 30.0) % 360.0) for i in range(12)]


def test_election_validate_requires_two_participant_snaps_for_beta(monkeypatch):
    _patch_validate_common(monkeypatch)
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/election/validate",
        query_string={
            "matter": "marriage",
            "marriage_algorithm": "beta",
            "start": "2026-04-15T08:00:00Z",
            "end": "2026-04-15T10:00:00Z",
            "location": "Jerusalem",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Beta marriage requires participant_a_snap_id and participant_b_snap_id"


def test_election_validate_rejects_duplicate_participant_snaps_for_beta(monkeypatch):
    _patch_validate_common(monkeypatch)
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/election/validate",
        query_string={
            "matter": "marriage",
            "marriage_algorithm": "beta",
            "start": "2026-04-15T08:00:00Z",
            "end": "2026-04-15T10:00:00Z",
            "location": "Jerusalem",
            "participant_a_snap_id": "snap-a",
            "participant_b_snap_id": "snap-a",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Beta marriage requires two different participant snaps"


def test_election_validate_accepts_beta_with_two_participant_snaps(monkeypatch):
    _patch_validate_common(monkeypatch)

    def fake_bundle(snap_id, *, house_system_code=None, missing_error="Snap not found"):
        if snap_id not in {"snap-a", "snap-b"}:
            raise ValueError(missing_error)
        return {"chart_data": {"houses": _houses()}, "meta": {"house_system_code": house_system_code}}

    monkeypatch.setattr(astro_clock_api, "_bundle_from_snap_id", fake_bundle)
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/election/validate",
        query_string={
            "matter": "marriage",
            "marriage_algorithm": "beta",
            "start": "2026-04-15T08:00:00Z",
            "end": "2026-04-15T10:00:00Z",
            "location": "Jerusalem",
            "participant_a_snap_id": "snap-a",
            "participant_b_snap_id": "snap-b",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_election_validate_accepts_minute_precision_hour_filters(monkeypatch):
    _patch_validate_common(monkeypatch)
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/election/validate",
        query_string={
            "matter": "marriage",
            "start": "2026-04-15T08:00:00Z",
            "end": "2026-04-15T10:00:00Z",
            "location": "Jerusalem",
            "hour_start": "09:30",
            "hour_end": "17:30",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_compute_moon_day_tracks_interval_tags():
    payload = moon_day.compute_moon_day(
        {
            "planets": {
                "Sun": {"longitude": 0.0},
                "Moon": {"longitude": 60.0},
            }
        }
    )

    assert payload is not None
    assert payload["nid"] == 6
    assert payload["lunation_half"] == "first"
    assert "060" in payload["interval_tags"]
    assert payload["source"] == "lunation_angle_proxy"


def test_extend_chart_data_for_marriage_beta_is_beta_only_runtime_enrichment(monkeypatch):
    base_chart = {
        "planets": {
            "Sun": {"longitude": 0.0, "speed": 1.0},
            "Moon": {"longitude": 60.0, "speed": 13.0},
        },
        "houses": _houses(),
    }
    meta = {"timestamp": "2026-04-15T12:00:00+00:00"}

    monkeypatch.setattr(
        astro_clock_api,
        "compute_asteroid_positions",
        lambda *_args, **_kwargs: {
            "items": [
                {
                    "name": "Proserpina",
                    "longitude": 181.25,
                    "latitude": 1.2,
                    "house": 7,
                    "sign": "Libra",
                    "degree_in_sign": 1.25,
                    "retrograde": False,
                    "speed": 0.04,
                    "tier": "special",
                    "galaxy_body_id": 17,
                }
            ],
            "status": "ok",
        },
    )
    monkeypatch.setattr(
        astro_clock_api,
        "compute_planetary_aspects_precise",
        lambda chart_data, *_args, **_kwargs: [
            {
                "planet1": "Moon",
                "planet2": "Proserpina",
                "aspect": "Trine",
                "orb": 0.5,
                "phase": "applying",
            }
        ],
    )

    out = astro_clock_api._extend_chart_data_for_marriage_beta(
        base_chart,
        meta,
        include_moon_day=True,
    )

    assert "Proserpina" not in base_chart["planets"]
    assert "moon_day" not in base_chart
    assert out["planets"]["Proserpina"]["longitude"] == 181.25
    assert out["moon_day"]["nid"] == 6
    assert "060" in out["moon_day"]["interval_tags"]
    assert out["planetary_aspects_precise"][0]["planet2"] == "Proserpina"

    participant_out = astro_clock_api._extend_chart_data_for_marriage_beta(
        base_chart,
        meta,
        include_moon_day=False,
    )
    assert "moon_day" not in participant_out


def test_score_marriage_beta_election_adds_participant_layers(monkeypatch):
    event_cd = {
        "marker": "event",
        "houses": _houses(),
        "planets": {
            "Jupiter": {"longitude": 180.0},
            "Venus": {"longitude": 0.0},
            "Mercury": {"longitude": 184.0},
            "Neptune": {"longitude": 182.0},
            "Uranus": {"longitude": 178.0},
            "Mars": {"longitude": 250.0},
            "Saturn": {"longitude": 320.0},
        },
    }
    participant_a_cd = {
        "marker": "snap-a",
        "houses": _houses(),
        "planets": {
            "Venus": {"longitude": 0.0},
            "Mercury": {"longitude": 30.0},
            "Jupiter": {"longitude": 180.0},
            "Uranus": {"longitude": 180.0},
            "Neptune": {"longitude": 180.0},
            "Saturn": {"longitude": 90.0},
        },
    }
    participant_b_cd = {
        "marker": "snap-b",
        "houses": _houses(),
        "planets": {
            "Venus": {"longitude": 0.0},
            "Mercury": {"longitude": 30.0},
            "Jupiter": {"longitude": 180.0},
            "Uranus": {"longitude": 180.0},
            "Neptune": {"longitude": 180.0},
            "Saturn": {"longitude": 90.0},
        },
    }

    def fake_almutens(chart_data):
        marker = chart_data.get("marker")
        base = {
            "points": {
                "ascendant": {"leader": "Venus", "longitude": 0.0},
                "midheaven": {"leader": "Saturn", "longitude": 90.0},
                "house_2": {"leader": "Mercury", "longitude": 30.0},
                "house_7": {"leader": "Jupiter", "longitude": 180.0},
            }
        }
        if marker == "event":
            return base
        return base

    monkeypatch.setattr(
        marriage_beta,
        "_score_beta_event_chart",
        lambda *_args, **_kwargs: Score(10.0, ["Event base support"], pros=["Event base support"], cautions=[]),
    )
    monkeypatch.setattr(marriage_beta, "compute_chart_almutens", fake_almutens)
    result = marriage_beta.score_marriage_beta_election(
        event_cd,
        options={
            "current_timestamp": datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
            "participant_a_cd": participant_a_cd,
            "participant_b_cd": participant_b_cd,
        },
    )

    assert result.value > 10.0
    assert "Event base support" in result.tags
    assert "Event base support" in (result.pros or [])
    assert any(tag.startswith("Snap A:") for tag in result.tags)
    assert any(tag.startswith("Snap B:") for tag in result.tags)
    assert any(tag.startswith("Snap A:") for tag in (result.pros or []))
    assert isinstance(result.cautions or [], list)
    assert [line["id"] for line in (result.lines or [])] == [
        "event",
        "participant:1",
        "participant:2",
    ]
    assert all("favorable" in line and "tense" in line for line in (result.lines or []))


def test_score_marriage_beta_precision_gates_house_cusp_rules(monkeypatch):
    event_cd = {
        "marker": "event",
        "houses": _houses(),
        "planets": {
            "Jupiter": {"longitude": 180.0},
            "Venus": {"longitude": 15.0},
        },
    }
    participant_cd = {
        "marker": "snap-a",
        "houses": _houses(),
        "planets": {
            "Venus": {"longitude": 44.0},
            "Mercury": {"longitude": 30.0},
            "Jupiter": {"longitude": 180.0},
            "Uranus": {"longitude": 175.0},
            "Neptune": {"longitude": 190.0},
            "Saturn": {"longitude": 90.0},
        },
    }

    def fake_almutens(chart_data):
        marker = chart_data.get("marker")
        if marker == "event":
            return {
                "points": {
                    "ascendant": {"leader": "Venus", "longitude": 15.0},
                    "house_7": {"leader": "Jupiter", "longitude": 180.0},
                }
            }
        return {
            "points": {
                "ascendant": {"leader": "Venus", "longitude": 0.0},
                "midheaven": {"leader": "Saturn", "longitude": 90.0},
                "house_2": {"leader": "Mercury", "longitude": 30.0},
                "house_7": {"leader": "Jupiter", "longitude": 180.0},
            }
        }

    monkeypatch.setattr(
        marriage_beta,
        "_score_beta_event_chart",
        lambda *_args, **_kwargs: Score(5.0, ["Event base support"], pros=["Event base support"], cautions=[]),
    )
    monkeypatch.setattr(marriage_beta, "compute_chart_almutens", fake_almutens)

    unsafe = marriage_beta.score_marriage_beta_election(
        event_cd,
        options={
            "participant_a_cd": participant_cd,
            "participant_a_precision": {
                "precision_class": "unknown",
                "precision_safe": False,
                "precision_source": "test",
            },
        },
    )

    assert not any("house/cusp fit" in tag for tag in unsafe.tags)
    assert any("house/cusp rules withheld" in tag for tag in unsafe.tags)
    assert unsafe.lines[1]["precision_safe"] is False

    safe = marriage_beta.score_marriage_beta_election(
        event_cd,
        options={
            "participant_a_cd": participant_cd,
            "participant_a_precision": {
                "precision_class": "certified",
                "precision_safe": True,
                "precision_source": "test",
            },
        },
    )

    assert any("house/cusp fit" in tag for tag in safe.tags)
    assert any(tag.startswith("Snap A:") for tag in safe.tags)
    assert safe.lines[1]["precision_safe"] is True


def test_marriage_beta_stream_extracts_periods_and_precision_lines(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda _location: (31.778, 35.235))
    monkeypatch.setattr(
        astro_clock_api,
        "_normalize_manual_datetime",
        lambda value, timezone_name=None, location=None: (
            datetime.fromisoformat(str(value).replace("Z", "+00:00")),
            timezone_name or "Asia/Jerusalem",
        ),
    )
    monkeypatch.setattr(astro_clock_api, "_validate_stream_scan_bounds", lambda _sdt, _edt, _step: (3, None))
    monkeypatch.setattr(
        astro_clock_api,
        "_extend_chart_data_for_marriage_beta",
        lambda chart_data, _meta, include_moon_day: chart_data,
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda dt_iso, *_args, **_kwargs: (
            {"houses": _houses(), "planets": {"Moon": {"longitude": 90.0}}},
            {
                "timestamp": dt_iso.replace("Z", "+00:00"),
                "location": "Jerusalem",
                "timezone": "Asia/Jerusalem",
            },
        ),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, *, house_system_code=None, missing_error="Snap not found": {
            "chart_data": {
                "houses": _houses(),
                "planets": {"Jupiter": {"longitude": 120.0}},
            },
            "meta": {
                "timestamp": "1990-01-01T00:00:00+00:00",
                "house_system_code": house_system_code,
            },
            "birth_time": {
                "status": "certified",
                "ranking_eligible": True,
                "ranking_eligibility": "confirmed",
            },
        },
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_snaps",
        lambda: {
            "snap-a": {"label": "Partner A", "location": "Jerusalem"},
            "snap-b": {"label": "Partner B", "location": "Jerusalem"},
        },
    )

    def fake_marriage_beta(_chart_data, *, options=None, **_kwargs):
        hour = getattr((options or {}).get("current_timestamp"), "hour", 0)
        if hour == 8:
            values = ((6.0, 6.0, 0.0), (3.0, 3.0, 0.0), (2.0, 2.0, 0.0))
        elif hour == 9:
            values = ((1.0, 4.0, 3.0), (1.0, 2.0, 1.0), (1.0, 2.0, 1.0))
        else:
            values = ((-2.0, 1.0, 3.0), (3.0, 3.0, 0.0), (2.0, 2.0, 0.0))
        specs = (
            ("event", "event", "Event line"),
            ("participant:1", "participant", "Partner A"),
            ("participant:2", "participant", "Partner B"),
        )
        lines = [
            {
                "id": line_id,
                "kind": kind,
                "label": label,
                "score": score,
                "favorable": favorable,
                "tense": tense,
                "tags": [],
            }
            for (line_id, kind, label), (score, favorable, tense) in zip(specs, values)
        ]
        return {
            "value": sum(line["score"] for line in lines),
            "tags": [],
            "pros": [],
            "cautions": [],
            "lines": lines,
        }

    monkeypatch.setattr(election, "score_marriage_beta_election", fake_marriage_beta)

    response = app_module.app.test_client().get(
        "/api/astro-clock/election/suggest/stream",
        query_string={
            "matter": "marriage",
            "marriage_algorithm": "beta",
            "start": "2026-04-15T08:00:00Z",
            "end": "2026-04-15T10:00:00Z",
            "location": "Jerusalem",
            "timezone": "Asia/Jerusalem",
            "step_minutes": "60",
            "participant_a_snap_id": "snap-a",
            "participant_b_snap_id": "snap-b",
            "marriage_beta_display_mode": "total",
            "marriage_beta_scope": "all",
            "marriage_beta_level_percent": "50",
        },
    )

    assert response.status_code == 200
    done_payload = None
    for line in response.data.decode("utf-8").splitlines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[len("data: "):])
        if payload.get("type") == "done":
            done_payload = payload["data"]
            break

    assert done_payload is not None
    assert done_payload["marriage_beta_extraction"]["selected_line_ids"] == [
        "event",
        "participant:1",
        "participant:2",
    ]
    assert done_payload["marriage_beta_extraction"]["period_count"] == 1
    assert done_payload["marriage_beta_periods"][0]["start"] == "2026-04-15T08:00:00+00:00"
    assert done_payload["top"][0]["aggregate_score"] == 11.0
    assert done_payload["top"][0]["marriage_beta_pass"] is True
    assert done_payload["series"][1]["marriage_beta_pass"] is False
    assert all(item["precision_safe"] is True for item in done_payload["participants"]["items"])


def test_alpha_split_still_treats_plain_jupiter_retrograde_as_caution():
    pros, cautions = marriage_model.split_marriage_tags([
        "Jupiter retrograde",
        "Moon under beams",
    ])

    assert "Jupiter retrograde" in cautions
    assert "Moon under beams" in cautions


def test_beta_event_branch_rewards_jupiter_retrograde_without_alpha_runtime_tags(monkeypatch):
    event_cd = {
        "houses": _houses(),
        "planets": {
            "Jupiter": {"longitude": 180.0, "retrograde": True},
            "Moon": {"longitude": 330.0},
        },
    }

    monkeypatch.setattr(marriage_beta, "compute_chart_almutens", lambda *_args, **_kwargs: {"points": {}})

    result = marriage_beta.score_marriage_beta_election(event_cd, options={})

    assert "Event Jupiter retrograde support (+3.0)" in result.tags
    assert "Event Jupiter retrograde support (+3.0)" in (result.pros or [])
    assert not any("morin" in str(tag).lower() for tag in result.tags)
    assert not any("natal omitted" in str(tag).lower() for tag in result.tags)
    assert not any(str(tag).startswith("Fixed Asc") or str(tag).startswith("Mobile Asc") for tag in result.tags)


def test_beta_event_branch_scores_moon_day_interval_tags(monkeypatch):
    event_cd = {
        "houses": _houses(),
        "planets": {
            "Sun": {"longitude": 0.0},
            "Moon": {"longitude": 62.0, "speed": 13.1},
            "Jupiter": {"longitude": 180.0},
        },
        "moon_day": {
            "nid": 6,
            "interval_tags": ["060", "072"],
        },
    }

    monkeypatch.setattr(marriage_beta, "compute_chart_almutens", lambda *_args, **_kwargs: {"points": {}})

    result = marriage_beta.score_marriage_beta_election(event_cd, options={})

    assert "Event Moon day support: 060 interval (+2.0)" in result.tags
    assert "Event Moon day support: 060 interval (+2.0)" in (result.pros or [])


def test_beta_event_branch_is_not_built_from_alpha_runtime_tags(monkeypatch):
    event_cd = {
        "houses": _houses(90.0),
        "planets": {
            "Sun": {"longitude": 120.0, "house": 10},
            "Moon": {"longitude": 100.0, "house": 1, "speed": 13.1},
            "Venus": {"longitude": 92.0, "house": 1},
            "Jupiter": {"longitude": 178.0, "house": 4},
            "Mars": {"longitude": 5.0, "house": 10},
            "Saturn": {"longitude": 350.0, "house": 10},
        },
        "moon_next_aspect": {"planet": "Venus", "aspect": "Conjunction"},
        "aspects": [
            {"planet1": "Venus", "planet2": "Jupiter", "aspect": "Trine", "orb": 1.2},
            {"planet1": "Mars", "planet2": "Venus", "aspect": "Square", "orb": 2.4},
        ],
    }

    monkeypatch.setattr(
        marriage_beta,
        "compute_chart_almutens",
        lambda *_args, **_kwargs: {"points": {"house_7": {"leader": "Jupiter"}}},
    )

    result = marriage_beta.score_marriage_beta_election(event_cd, options={})

    assert any(str(tag).startswith("Event Asc marriage sign") for tag in result.tags)
    assert any(str(tag).startswith("Event Moon") for tag in result.tags)
    assert any("Event Mars strains" in str(tag) or "Event Saturn strains" in str(tag) for tag in result.tags)
    assert not any("morin" in str(tag).lower() for tag in result.tags)
    assert not any("natal omitted" in str(tag).lower() for tag in result.tags)
    assert not any(str(tag).startswith("Fixed Asc") or str(tag).startswith("Mobile Asc") for tag in result.tags)


def test_split_marriage_tags_marks_unfavored_sign_as_caution():
    pros, cautions = marriage_model.split_marriage_tags([
        "Fixed Asc (Leo)",
        "Unfavored 7th sign (Aquarius)",
        "Moon under beams",
    ])

    assert "Fixed Asc (Leo)" in pros
    assert "Unfavored 7th sign (Aquarius)" in cautions
    assert "Moon under beams" in cautions
