from datetime import datetime
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
import election_models.estate as estate
from election_models.common import Score


def test_estate_missing_precision_defaults_unknown_and_unsafe():
    assert estate._participant_precision_context({}) == {
        "precision_class": "unknown",
        "precision_safe": False,
        "precision_source": "missing_birth_time_quality",
    }


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
    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda _lat, _lon: None)


def _houses(start: float = 0.0):
    return [((start + i * 30.0) % 360.0) for i in range(12)]


def test_election_validate_requires_estate_participant(monkeypatch):
    _patch_validate_common(monkeypatch)
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/election/validate",
        query_string={
            "matter": "estate",
            "estate_direction": "buy",
            "start": "2026-04-18T08:00:00Z",
            "end": "2026-04-18T10:00:00Z",
            "location": "Jerusalem",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Estate election requires estate_participant_snap_id"


def test_election_validate_rejects_invalid_estate_direction(monkeypatch):
    _patch_validate_common(monkeypatch)
    client = app_module.app.test_client()

    response = client.get(
        "/api/astro-clock/election/validate",
        query_string={
            "matter": "estate",
            "estate_direction": "lease",
            "estate_participant_snap_id": "snap-estate",
            "start": "2026-04-18T08:00:00Z",
            "end": "2026-04-18T10:00:00Z",
            "location": "Jerusalem",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "estate_direction must be buy or sell"


def test_score_estate_election_adds_participant_line(monkeypatch):
    event_cd = {"houses": _houses(), "planets": {"Moon": {"longitude": 300.0}, "Sun": {"longitude": 90.0}}}
    participant = {
        "chart_data": {"houses": _houses(), "planets": {"Venus": {"longitude": 120.0}}},
        "label": "Buyer A",
        "precision_class": "certified",
        "precision_safe": True,
        "precision_source": "test_certified_fixture",
    }

    monkeypatch.setattr(
        estate,
        "_score_event_chart",
        lambda *_args, **_kwargs: Score(7.0, ["Event buy Moon phase support: waning (+3.0)"]),
    )
    monkeypatch.setattr(
        estate,
        "_score_participant_fit",
        lambda label, *_args, **_kwargs: (
            1.8,
            [f"{label}: event Fortuna conjunction participant Asc (+1.2)"],
        ),
    )

    result = estate.score_estate_election(
        event_cd,
        options={
            "estate_direction": "buy",
            "estate_participant": participant,
        },
    )

    assert result["value"] == 8.8
    assert "Event buy Moon phase support: waning (+3.0)" in result["tags"]
    assert any(tag.startswith("Buyer A:") for tag in result["tags"])
    assert [line["id"] for line in result["lines"]] == ["event", "participant:1"]
    assert result["lines"][0]["label"] == "Event line (buy)"
    assert result["lines"][1]["label"] == "Buyer A"
    assert result["lines"][1]["precision_class"] == "certified"
    assert result["lines"][1]["precision_safe"] is True


def test_estate_stream_payload_uses_estate_specific_extraction_fields(monkeypatch):
    _patch_validate_common(monkeypatch)

    monkeypatch.setattr(astro_clock_api, "_extend_chart_data_for_marriage_beta", lambda chart_data, _meta, include_moon_day: chart_data)
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_for",
        lambda dt_iso, *_args, **_kwargs: (
            {"houses": _houses(), "planets": {"Moon": {"longitude": 300.0}, "Sun": {"longitude": 90.0}}},
            {
                "timestamp": dt_iso.replace("Z", "+00:00"),
                "location": "Jerusalem",
                "timezone": "Asia/Jerusalem",
                "latitude": 31.778,
                "longitude": 35.235,
            },
        ),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_bundle_from_snap_id",
        lambda snap_id, *, house_system_code=None, missing_error="Snap not found": {
            "chart_data": {"houses": _houses(), "planets": {"Venus": {"longitude": 120.0}}},
            "meta": {"timestamp": "2026-04-18T08:00:00+00:00", "house_system_code": house_system_code},
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
        lambda: {"snap-estate": {"label": "Buyer A", "location": "Jerusalem"}},
    )

    def fake_estate(_chart_data, *, options=None, **_kwargs):
        ts = options.get("current_timestamp")
        hour = getattr(ts, "hour", 0)
        if hour == 8:
            event_score, participant_score = 5.0, 4.0
        elif hour == 9:
            event_score, participant_score = 1.0, 1.0
        else:
            event_score, participant_score = -2.0, 5.0
        return {
            "value": event_score + participant_score,
            "tags": [],
            "pros": [],
            "cautions": [],
            "lines": [
                {
                    "id": "event",
                    "kind": "event",
                    "label": "Event line (buy)",
                    "score": event_score,
                    "favorable": max(event_score, 0.0),
                    "tense": max(-event_score, 0.0),
                    "tags": [],
                },
                {
                    "id": "participant:1",
                    "kind": "participant",
                    "label": "Buyer A",
                    "score": participant_score,
                    "favorable": max(participant_score, 0.0),
                    "tense": max(-participant_score, 0.0),
                    "precision_class": "certified",
                    "precision_safe": True,
                    "tags": [],
                },
            ],
        }

    monkeypatch.setattr(election, "score_estate_election", fake_estate)

    client = app_module.app.test_client()
    response = client.get(
        "/api/astro-clock/election/suggest/stream",
        query_string=[
            ("matter", "estate"),
            ("estate_direction", "buy"),
            ("start", "2026-04-18T08:00:00Z"),
            ("end", "2026-04-18T10:00:00Z"),
            ("location", "Jerusalem"),
            ("timezone", "Asia/Jerusalem"),
            ("step_minutes", "60"),
            ("estate_participant_snap_id", "snap-estate"),
            ("estate_display_mode", "total"),
            ("estate_scope", "all"),
            ("estate_level_percent", "50"),
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
    assert done_payload["matter"] == "estate"
    assert done_payload["estate_direction"] == "buy"
    assert done_payload["participants"]["estate_participant_snap_id"] == "snap-estate"
    assert done_payload["participants"]["certified_assumption"] is True
    assert done_payload["participants"]["items"] == [{
        "snap_id": "snap-estate",
        "label": "Buyer A",
        "precision_class": "certified",
        "precision_safe": True,
        "precision_source": "saved_birth_time_quality:confirmed",
    }]
    assert done_payload["estate_extraction"]["selected_line_ids"] == ["event", "participant:1"]
    assert done_payload["estate_extraction"]["period_count"] == 1
    assert done_payload["estate_periods"][0]["id"].startswith("estate-period:")
    assert done_payload["top"][0]["estate_pass"] is True
    assert "business_beta_pass" not in done_payload["top"][0]
    assert done_payload["series"][1]["estate_pass"] is False
