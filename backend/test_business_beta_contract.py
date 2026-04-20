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
import election_models.business_beta as business_beta
from election_models.common import Score


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
    monkeypatch.setattr(astro_clock_api, "_validate_stream_scan_bounds", lambda _sdt, _edt, _step: (2, None))


def _houses(start: float = 0.0):
    return [((start + i * 30.0) % 360.0) for i in range(12)]


def test_election_validate_requires_at_least_one_business_participant_for_beta(monkeypatch):
    _patch_validate_common(monkeypatch)
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/election/validate",
        query_string={
            "matter": "business",
            "business_algorithm": "beta",
            "start": "2026-04-18T08:00:00Z",
            "end": "2026-04-18T10:00:00Z",
            "location": "Jerusalem",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Beta business requires at least one participant_snap_id"


def test_election_validate_rejects_duplicate_business_participants_for_beta(monkeypatch):
    _patch_validate_common(monkeypatch)
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/election/validate",
        query_string=[
            ("matter", "business"),
            ("business_algorithm", "beta"),
            ("start", "2026-04-18T08:00:00Z"),
            ("end", "2026-04-18T10:00:00Z"),
            ("location", "Jerusalem"),
            ("participant_snap_id", "snap-founder"),
            ("participant_snap_id", "snap-founder"),
        ],
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Beta business requires unique participant snaps"


def test_election_validate_accepts_unique_business_participants_for_beta(monkeypatch):
    _patch_validate_common(monkeypatch)

    def fake_bundle(snap_id, *, house_system_code=None, missing_error="Snap not found"):
        if snap_id not in {"snap-founder-a", "snap-founder-b"}:
            raise ValueError(missing_error)
        return {
            "chart_data": {"houses": _houses()},
            "meta": {"timestamp": "2026-04-18T08:00:00+00:00", "house_system_code": house_system_code},
        }

    monkeypatch.setattr(astro_clock_api, "_bundle_from_snap_id", fake_bundle)
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/election/validate",
        query_string=[
            ("matter", "business"),
            ("business_algorithm", "beta"),
            ("start", "2026-04-18T08:00:00Z"),
            ("end", "2026-04-18T10:00:00Z"),
            ("location", "Jerusalem"),
            ("participant_snap_id", "snap-founder-a"),
            ("participant_snap_id", "snap-founder-b"),
        ],
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_score_business_beta_election_adds_founder_layers(monkeypatch):
    event_cd = {"houses": _houses(), "planets": {"Moon": {"longitude": 90.0}}}
    participant_a = {"chart_data": {"houses": _houses(), "planets": {"Jupiter": {"longitude": 120.0}}}, "label": "Founder A"}
    participant_b = {"chart_data": {"houses": _houses(), "planets": {"Venus": {"longitude": 60.0}}}, "label": "Founder B"}

    monkeypatch.setattr(
        business_beta,
        "_score_event_chart",
        lambda *_args, **_kwargs: Score(9.0, ["Event Moon sign support: Cancer (+3.0)"]),
    )
    monkeypatch.setattr(
        business_beta,
        "_score_participant_fit",
        lambda label, *_args, **_kwargs: (
            1.5,
            [
                f"{label}: Asc ruler falls in event 10th (+1.35)",
                f"{label}: event Fortuna contacts natal Asc (+1.2)",
            ],
        ),
    )

    result = business_beta.score_business_beta_election(
        event_cd,
        options={
            "business_participants": [participant_a, participant_b],
            "business_mode": "growth",
        },
    )

    assert result["value"] > 9.0
    assert "Event Moon sign support: Cancer (+3.0)" in result["tags"]
    assert any(tag.startswith("Founder A:") for tag in result["tags"])
    assert any(tag.startswith("Founder B:") for tag in result["tags"])
    assert any(tag.startswith("Founder A:") for tag in (result.get("pros") or []))
    assert isinstance(result.get("cautions") or [], list)
    assert [line["label"] for line in result["lines"]] == ["Event line", "Founder A", "Founder B"]
    assert result["lines"][0]["kind"] == "event"
    assert result["lines"][1]["kind"] == "participant"
    assert result["lines"][0]["favorable"] == 3.0
    assert result["lines"][1]["precision_class"] == "certified"
    assert result["lines"][1]["precision_safe"] is True


def test_business_beta_cross_support_excludes_conjunctions():
    score, tags = business_beta._score_participant_cross_support(
        "Founder A",
        [("Mercury", 10.0)],
        [("Moon", 10.0)],
    )

    assert score == 0.0
    assert tags == []

    sextile_score, sextile_tags = business_beta._score_participant_cross_support(
        "Founder A",
        [("Mercury", 10.0)],
        [("Moon", 70.0)],
    )

    assert sextile_score > 0.0
    assert any("sextile" in tag for tag in sextile_tags)

    event_support_score, event_support_tags = business_beta._score_event_business_support(
        {
            "Moon": {"longitude": 0.0},
            "Mercury": {"longitude": 10.0},
            "Venus": {"longitude": 10.0},
        },
        _houses(),
    )

    assert event_support_score == 0.0
    assert event_support_tags == []


def test_business_beta_timing_bonus_uses_hour_ruler_only():
    day_only_score, day_only_tags = business_beta._planetary_timing_bonus(
        {"day_ruler": "Mercury", "hour_ruler": "Moon"}
    )
    hour_score, hour_tags = business_beta._planetary_timing_bonus(
        {"day_ruler": "Moon", "hour_ruler": "Mercury"}
    )

    assert day_only_score == 0.0
    assert day_only_tags == []
    assert hour_score == 0.8
    assert hour_tags == ["Event planetary hour support: Mercury (+0.8)"]


def test_business_beta_stream_payload_includes_algorithm_and_participants(monkeypatch):
    _patch_validate_common(monkeypatch)

    monkeypatch.setattr(astro_clock_api, "_extend_chart_data_for_marriage_beta", lambda chart_data, _meta, include_moon_day: chart_data)
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda *_args, **_kwargs: (
            {"houses": _houses(), "planets": {"Moon": {"longitude": 90.0}}},
            {"timestamp": "2026-04-18T08:00:00+00:00", "location": "Jerusalem", "timezone": "Asia/Jerusalem"},
        ),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, *, house_system_code=None, missing_error="Snap not found": {
            "chart_data": {"houses": _houses(), "planets": {"Jupiter": {"longitude": 120.0}}},
            "meta": {"timestamp": "2026-04-18T08:00:00+00:00", "house_system_code": house_system_code},
        },
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_snaps",
        lambda: {
            "snap-founder-a": {"label": "Founder A", "location": "Jerusalem"},
            "snap-founder-b": {"label": "Founder B", "location": "Jerusalem"},
        },
    )
    monkeypatch.setattr(
        election,
        "score_business_beta_election",
        lambda *_args, **_kwargs: {
            "value": 5.5,
            "tags": ["Event Moon sign support: Cancer (+3.0)"],
            "pros": ["Event Moon sign support: Cancer (+3.0)"],
            "cautions": [],
            "lines": [
                {
                    "id": "event",
                    "kind": "event",
                    "label": "Event line",
                    "score": 5.5,
                    "tags": ["Event Moon sign support: Cancer (+3.0)"],
                    "pros": ["Event Moon sign support: Cancer (+3.0)"],
                    "cautions": [],
                }
            ],
        },
    )

    client = app_module.app.test_client()
    response = client.get(
        "/api/astro-clock/election/suggest/stream",
        query_string=[
            ("matter", "business"),
            ("business_algorithm", "beta"),
            ("start", "2026-04-18T08:00:00Z"),
            ("end", "2026-04-18T09:00:00Z"),
            ("location", "Jerusalem"),
            ("timezone", "Asia/Jerusalem"),
            ("step_minutes", "60"),
            ("participant_snap_id", "snap-founder-a"),
            ("participant_snap_id", "snap-founder-b"),
        ],
    )

    assert response.status_code == 200
    done_lines = [
        line[len("data: "):]
        for line in response.data.decode("utf-8").splitlines()
        if line.startswith("data: ")
    ]
    done_payload = None
    for raw in done_lines:
        parsed = json.loads(raw)
        if parsed.get("type") == "done":
            done_payload = parsed["data"]
            break

    assert done_payload is not None
    assert done_payload["matter"] == "business"
    assert done_payload["business_algorithm"] == "beta"
    assert done_payload["participants"]["participant_snap_ids"] == ["snap-founder-a", "snap-founder-b"]
    assert done_payload["participants"]["certified_assumption"] is True
    assert done_payload["participants"]["items"] == [
        {"snap_id": "snap-founder-a", "label": "Founder A"},
        {"snap_id": "snap-founder-b", "label": "Founder B"},
    ]
    assert done_payload["business_beta_extraction"]["display_mode"] == "total"
    assert done_payload["business_beta_extraction"]["scope"] == "all"
    assert done_payload["top"][0]["lines"][0]["label"] == "Event line"
    assert done_payload["top"][0]["lines"][0]["kind"] == "event"


def test_business_beta_stream_extracts_periods_from_selected_lines(monkeypatch):
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
    monkeypatch.setattr(astro_clock_api, "_extend_chart_data_for_marriage_beta", lambda chart_data, _meta, include_moon_day: chart_data)
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda dt_iso, *_args, **_kwargs: (
            {"houses": _houses(), "planets": {"Moon": {"longitude": 90.0}}},
            {"timestamp": dt_iso.replace("Z", "+00:00"), "location": "Jerusalem", "timezone": "Asia/Jerusalem"},
        ),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, *, house_system_code=None, missing_error="Snap not found": {
            "chart_data": {"houses": _houses(), "planets": {"Jupiter": {"longitude": 120.0}}},
            "meta": {"timestamp": "2026-04-18T08:00:00+00:00", "house_system_code": house_system_code},
        },
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_snaps",
        lambda: {"snap-founder-a": {"label": "Founder A", "location": "Jerusalem"}},
    )

    def fake_business_beta(_chart_data, *, options=None, **_kwargs):
        ts = options.get("current_timestamp")
        hour = getattr(ts, "hour", 0)
        if hour == 8:
            event_score, founder_score = 6.0, 4.0
            event_favorable, founder_favorable = 6.0, 4.0
            event_tense, founder_tense = 0.0, 0.0
        elif hour == 9:
            event_score, founder_score = 1.0, 1.0
            event_favorable, founder_favorable = 4.0, 2.0
            event_tense, founder_tense = 3.0, 1.0
        else:
            event_score, founder_score = -2.0, 5.0
            event_favorable, founder_favorable = 1.0, 5.0
            event_tense, founder_tense = 3.0, 0.0
        return {
            "value": event_score + founder_score,
            "tags": [],
            "pros": [],
            "cautions": [],
            "lines": [
                {
                    "id": "event",
                    "kind": "event",
                    "label": "Event line",
                    "score": event_score,
                    "favorable": event_favorable,
                    "tense": event_tense,
                    "tags": [],
                },
                {
                    "id": "participant:1",
                    "kind": "participant",
                    "label": "Founder A",
                    "score": founder_score,
                    "favorable": founder_favorable,
                    "tense": founder_tense,
                    "precision_class": "certified",
                    "precision_safe": True,
                    "tags": [],
                },
            ],
        }

    monkeypatch.setattr(election, "score_business_beta_election", fake_business_beta)

    client = app_module.app.test_client()
    response = client.get(
        "/api/astro-clock/election/suggest/stream",
        query_string=[
            ("matter", "business"),
            ("business_algorithm", "beta"),
            ("start", "2026-04-18T08:00:00Z"),
            ("end", "2026-04-18T10:00:00Z"),
            ("location", "Jerusalem"),
            ("timezone", "Asia/Jerusalem"),
            ("step_minutes", "60"),
            ("participant_snap_id", "snap-founder-a"),
            ("business_beta_display_mode", "total"),
            ("business_beta_scope", "all"),
            ("business_beta_level_percent", "50"),
        ],
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
    assert done_payload["business_beta_extraction"]["selected_line_ids"] == ["event", "participant:1"]
    assert done_payload["business_beta_extraction"]["period_count"] == 1
    assert done_payload["business_beta_periods"][0]["start"] == "2026-04-18T08:00:00+00:00"
    assert done_payload["business_beta_periods"][0]["end"] == "2026-04-18T08:00:00+00:00"
    assert done_payload["top"][0]["timestamp"] == "2026-04-18T08:00:00+00:00"
    assert done_payload["top"][0]["aggregate_score"] == 10.0
    assert done_payload["top"][0]["business_beta_pass"] is True
    assert done_payload["series"][1]["business_beta_pass"] is False


def test_business_beta_stream_ignores_alpha_only_business_overlays(monkeypatch):
    _patch_validate_common(monkeypatch)

    captured_options = {}

    monkeypatch.setattr(astro_clock_api, "_extend_chart_data_for_marriage_beta", lambda chart_data, _meta, include_moon_day: chart_data)
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda *_args, **_kwargs: (
            {"houses": _houses(), "planets": {"Moon": {"longitude": 90.0}}},
            {"timestamp": "2026-04-18T08:00:00+00:00", "location": "Jerusalem", "timezone": "Asia/Jerusalem"},
        ),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, *, house_system_code=None, missing_error="Snap not found": {
            "chart_data": {"houses": _houses(), "planets": {"Jupiter": {"longitude": 120.0}}},
            "meta": {"timestamp": "2026-04-18T08:00:00+00:00", "house_system_code": house_system_code},
        },
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_snaps",
        lambda: {"snap-founder-a": {"label": "Founder A", "location": "Jerusalem"}},
    )

    def fake_business_beta(_chart_data, *, options=None, **_kwargs):
        captured_options.update(dict(options or {}))
        return {
            "value": 4.5,
            "tags": [],
            "pros": [],
            "cautions": [],
            "lines": [{"id": "event", "kind": "event", "label": "Event line", "score": 4.5, "tags": []}],
        }

    monkeypatch.setattr(election, "score_business_beta_election", fake_business_beta)

    client = app_module.app.test_client()
    response = client.get(
        "/api/astro-clock/election/suggest/stream",
        query_string=[
            ("matter", "business"),
            ("business_algorithm", "beta"),
            ("start", "2026-04-18T08:00:00Z"),
            ("end", "2026-04-18T09:00:00Z"),
            ("location", "Jerusalem"),
            ("timezone", "Asia/Jerusalem"),
            ("step_minutes", "60"),
            ("participant_snap_id", "snap-founder-a"),
            ("include_fixed_stars", "1"),
            ("include_lunation_screen", "1"),
            ("emphasize_commerce", "1"),
            ("business_mode", "growth"),
        ],
    )

    assert response.status_code == 200
    assert captured_options["business_algorithm"] == "beta"
    assert captured_options["include_traditional_timing"] is True
    assert "include_fixed_stars" not in captured_options
    assert "include_lunation_screen" not in captured_options
    assert "emphasize_commerce" not in captured_options
    assert "business_mode" not in captured_options
