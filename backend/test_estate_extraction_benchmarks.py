from datetime import timedelta
from pathlib import Path
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import astro_clock_api


def _line(line_id, label, score, *, kind):
    score = float(score)
    return {
        "id": line_id,
        "kind": kind,
        "label": label,
        "score": score,
        "favorable": max(score, 0.0),
        "tense": max(-score, 0.0),
    }


def _row(hour, event_score, participant_score):
    timestamp = f"2026-04-18T{hour:02d}:00:00+00:00"
    return {
        "timestamp": timestamp,
        "timestamp_local": timestamp,
        "score": float(event_score + participant_score),
        "lines": [
            _line("event", "Event line (buy)", event_score, kind="event"),
            _line("participant:1", "Buyer A", participant_score, kind="participant"),
        ],
    }


def _controlled_rows():
    return [
        _row(8, 6.0, 4.0),
        _row(9, 3.0, 1.0),
        _row(10, -2.0, 5.0),
    ]


def _extract(**kwargs):
    return astro_clock_api._extract_estate_periods(
        _controlled_rows(),
        step_td=timedelta(hours=1),
        level_percent=50.0,
        **kwargs,
    )


def _line_stats_by_id(result):
    return {row["id"]: row for row in result["line_stats"]}


def test_total_all_estate_extraction_thresholds_and_periods():
    result = _extract(display_mode="total", scope="all")
    rows = result["rows"]
    stats = _line_stats_by_id(result)

    assert result["display_mode"] == "total"
    assert result["scope"] == "all"
    assert result["selected_line_ids"] == ["event", "participant:1"]
    assert stats["event"]["amplitude"] == 6.0
    assert stats["event"]["threshold"] == 3.0
    assert stats["participant:1"]["amplitude"] == 5.0
    assert stats["participant:1"]["threshold"] == 2.5

    assert [row["estate_pass"] for row in rows] == [True, False, False]
    assert [row["estate_selected_threshold"] for row in rows] == [5.5, 5.5, 5.5]
    assert [row["score"] for row in rows] == [10.0, 4.0, 3.0]
    assert "business_beta_pass" not in rows[0]

    assert result["passing_row_count"] == 1
    assert result["period_count"] == 1
    assert result["periods"] == [
        {
            "id": "estate-period:1",
            "start": "2026-04-18T08:00:00+00:00",
            "start_local": "2026-04-18T08:00:00+00:00",
            "end": "2026-04-18T08:00:00+00:00",
            "end_local": "2026-04-18T08:00:00+00:00",
            "best_timestamp": "2026-04-18T08:00:00+00:00",
            "best_timestamp_local": "2026-04-18T08:00:00+00:00",
            "best_score": 10.0,
            "row_count": 1,
            "selected_line_ids": ["event", "participant:1"],
        }
    ]


def test_detail_selected_estate_extraction_uses_only_selected_line():
    result = _extract(
        display_mode="detail",
        scope="selected",
        selected_line_ids=["participant:1"],
    )
    rows = result["rows"]

    assert result["display_mode"] == "detail"
    assert result["scope"] == "selected"
    assert result["selected_line_ids"] == ["participant:1"]
    assert [row["score"] for row in rows] == [4.0, 1.0, 5.0]
    assert [row["estate_pass"] for row in rows] == [True, False, True]
    assert [row["estate_selected_line_ids"] for row in rows] == [["participant:1"]] * 3
    assert rows[0]["estate_line_states"] == [
        {
            "id": "participant:1",
            "label": "Buyer A",
            "kind": "participant",
            "score": 4.0,
            "favorable": 4.0,
            "tense": 0.0,
            "threshold": 2.5,
            "metric": 4.0,
            "passed": True,
        }
    ]

    assert result["period_count"] == 2
    assert [period["id"] for period in result["periods"]] == ["estate-period:1", "estate-period:2"]
    assert result["periods"][1]["best_timestamp"] == "2026-04-18T10:00:00+00:00"
    assert result["periods"][1]["best_score"] == 5.0
    assert [row["timestamp"] for row in result["top_rows"]] == [
        "2026-04-18T10:00:00+00:00",
        "2026-04-18T08:00:00+00:00",
    ]


def test_total_current_estate_extraction_merges_adjacent_event_rows():
    result = _extract(
        display_mode="total",
        scope="current",
        current_line_id="event",
    )
    rows = result["rows"]

    assert result["selected_line_ids"] == ["event"]
    assert [row["score"] for row in rows] == [6.0, 3.0, -2.0]
    assert [row["estate_pass"] for row in rows] == [True, True, False]
    assert [row["estate_selected_threshold"] for row in rows] == [3.0, 3.0, 3.0]

    assert result["period_count"] == 1
    period = result["periods"][0]
    assert period["id"] == "estate-period:1"
    assert period["start"] == "2026-04-18T08:00:00+00:00"
    assert period["end"] == "2026-04-18T09:00:00+00:00"
    assert period["best_timestamp"] == "2026-04-18T08:00:00+00:00"
    assert period["best_score"] == 6.0
    assert period["row_count"] == 2
    assert period["selected_line_ids"] == ["event"]
