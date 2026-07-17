from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.election_models.lunar_fertility import (
    LUNAR_CYCLE_DAYS,
    MOON_MAX_SPEED_DIVISOR,
    LunarFertilityAnchor,
    extract_natal_lunar_signature,
    generate_lunar_fertility_anchors,
    group_lunar_fertility_periods,
    moon_branch_and_elongation,
    normalize_consider_mode,
    project_lunar_fertility_series,
    scan_lunar_fertility_windows,
)


class LinearMoonEphemeris:
    def __init__(self, epoch: datetime):
        self.epoch = epoch.astimezone(timezone.utc)

    def longitude_at(self, dt_utc: datetime, body: str) -> float:
        if body == "Sun":
            return 0.0
        dt = dt_utc.astimezone(timezone.utc)
        days = (dt - self.epoch).total_seconds() / 86400.0
        return (days * (360.0 / LUNAR_CYCLE_DAYS)) % 360.0


class SignEphemeris:
    def longitude_at(self, dt_utc: datetime, body: str) -> float:
        if body == "Sun":
            return 0.0
        return 15.0 if dt_utc.hour < 18 else 45.0


def test_lunar_signature_uses_short_arc_branch_not_opposition():
    assert moon_branch_and_elongation(10.0, 40.0) == (True, 30.0)
    assert moon_branch_and_elongation(10.0, 340.0) == (False, 30.0)

    signature = extract_natal_lunar_signature(
        {
            "planets": {
                "Sun": {"longitude": 10.0},
                "Moon": {"longitude": 340.0},
            }
        }
    )

    assert signature.target_elongation == 30.0
    assert signature.natal_branch is False


def test_consider_mode_validation_and_aliases():
    assert normalize_consider_mode("phase") == "phase"
    assert normalize_consider_mode("both") == "phase_and_antiphase"
    assert normalize_consider_mode("antiphase") == "antiphase"
    with pytest.raises(ValueError):
        normalize_consider_mode("full_moon")


def test_projection_scores_window_strength_and_moon_sign_polarity():
    anchor = LunarFertilityAnchor(
        timestamp=datetime(2026, 3, 8, 12, tzinfo=timezone.utc),
        phase_kind="phase",
        branch=True,
        elongation=30.0,
        target_elongation=30.0,
    )

    rows = project_lunar_fertility_series(
        datetime(2026, 3, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 8, 20, tzinfo=timezone.utc),
        [anchor],
        timezone_name="UTC",
        ephemeris=SignEphemeris(),
    )

    by_hour = {datetime.fromisoformat(row["timestamp"]).hour: row for row in rows}
    assert 0 not in by_hour
    assert by_hour[12]["score"] == 100.0
    assert by_hour[12]["sex_label"] == "male"
    assert by_hour[18]["sex_label"] == "female"
    assert by_hour[18]["score"] == 75.0


def test_period_grouping_splits_by_phase_and_sex():
    rows = [
        {"timestamp": "2026-03-08T10:00:00+00:00", "timestamp_local": "2026-03-08T10:00:00+00:00", "score": 50, "phase_kind": "phase", "sex_label": "male"},
        {"timestamp": "2026-03-08T11:00:00+00:00", "timestamp_local": "2026-03-08T11:00:00+00:00", "score": 80, "phase_kind": "phase", "sex_label": "male"},
        {"timestamp": "2026-03-08T12:00:00+00:00", "timestamp_local": "2026-03-08T12:00:00+00:00", "score": 70, "phase_kind": "antiphase", "sex_label": "male"},
    ]

    grouped = group_lunar_fertility_periods(rows, timezone_name="UTC")

    assert len(grouped["periods"]) == 2
    assert grouped["periods"][0]["best_timestamp"] == "2026-03-08T11:00:00+00:00"
    assert grouped["periods"][0]["row_count"] == 2
    assert grouped["periods"][1]["phase_kind"] == "antiphase"


def test_scan_generates_phase_rows_and_periods_with_fake_ephemeris():
    epoch = datetime(2026, 3, 8, 0, tzinfo=timezone.utc)
    natal = {
        "planets": {
            "Sun": {"longitude": 0.0},
            "Moon": {"longitude": 30.0},
        }
    }

    result = scan_lunar_fertility_windows(
        natal,
        epoch,
        epoch + timedelta(days=4),
        timezone_name="UTC",
        consider_mode="phase",
        level_percent=33,
        ephemeris=LinearMoonEphemeris(epoch),
    )

    assert result["matter"] == "lunar_fertility"
    assert result["anchors"]
    assert all(anchor["phase_kind"] == "phase" for anchor in result["anchors"])
    assert result["series"]
    assert result["top"][0]["score"] >= 90.0
    assert result["periods"]
    assert result["stats"]["passing_total"] > 0


def test_generate_anchors_can_select_antiphase_only():
    epoch = datetime(2026, 3, 8, 0, tzinfo=timezone.utc)
    signature = extract_natal_lunar_signature(
        {
            "planets": {
                "Sun": {"longitude": 0.0},
                "Moon": {"longitude": 30.0},
            }
        }
    )

    anchors = generate_lunar_fertility_anchors(
        epoch,
        epoch + timedelta(days=30),
        signature,
        consider_mode="antiphase",
        ephemeris=LinearMoonEphemeris(epoch),
    )

    assert anchors
    assert all(anchor.phase_kind == "antiphase" for anchor in anchors)
