from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import weather_predictive_benchmark_runner as runner
from validate_weather_benchmark_datasets import validate_predictive_hindcast_case


def _case(case_id: str, family_id: str, *, case_origin: str = "source_backed") -> dict:
    payload = {
        "enabled": True,
        "case_id": case_id,
        "case_origin": case_origin,
        "runtime_family_id": family_id,
        "benchmark_family_id": family_id,
        "label": case_id,
        "scan_scope": "place_timeline",
        "location": "Test City",
        "timezone": "UTC",
        "benchmark_window": {
            "start_datetime": "2026-04-01T00:00:00",
            "end_datetime": "2026-04-02T00:00:00",
        },
        "target_window": {
            "start_datetime": "2026-04-01T12:00:00",
            "end_datetime": "2026-04-01T18:00:00",
        },
        "control_windows": [
            {
                "start_datetime": "2026-04-01T00:00:00",
                "end_datetime": "2026-04-01T06:00:00",
            },
            {
                "start_datetime": "2026-04-02T00:00:00",
                "end_datetime": "2026-04-02T00:00:00",
            },
        ],
        "time_step_hours": 6,
        "scoring_expectations": {
            "min_target_percentile": 0.75,
            "max_target_rank": 2,
            "max_peak_distance_hours": 24,
        },
        "source_assertions": [
            {
                "title": "Synthetic",
                "raw_file": "horary_knowledge/weather_earthquake_books_text/Predicting_Weather_Events_with_Astrology_-_Kris_Brandt_Riske.txt",
                "normalized_file": "horary_knowledge/mundane_knowledge_base/summaries/weather_seed_summary.md",
                "claim": "Synthetic benchmark.",
            }
        ],
    }
    if case_origin == "source_backed":
        payload["source_case_id"] = case_id
    return payload


def _scan_result(scores: list[float], peak_datetime: str) -> dict:
    timeline = [
        "2026-04-01T00:00:00",
        "2026-04-01T06:00:00",
        "2026-04-01T12:00:00",
        "2026-04-01T18:00:00",
        "2026-04-02T00:00:00",
    ]
    series = [
        {
            "datetime": dt,
            "score": score,
            "level": "active" if score >= 30 else "watch",
            "scan_level": "dominant" if score == max(scores) else "watch",
            "relative_score_ratio": round(score / max(scores), 4) if max(scores) else 0.0,
        }
        for dt, score in zip(timeline, scores)
    ]
    peak_score = max(scores)
    return {
        "series": {
            "places": [
                {
                    "location": {"label": "Test City"},
                    "peak_score": peak_score,
                    "peak_datetime": peak_datetime,
                    "peak_selection": "peak",
                    "peak_window_start_datetime": peak_datetime,
                    "peak_window_end_datetime": peak_datetime,
                    "series": series,
                }
            ]
        }
    }


def test_run_predictive_hindcast_suite_summarizes_pass_and_fail(monkeypatch):
    monkeypatch.setattr(
        runner,
        "load_predictive_cases",
        lambda **_: [
            _case("pass_case", "flood_risk"),
            _case("fail_case", "wind_event_pressure", case_origin="novel_holdout"),
        ],
    )

    def fake_run(case, *, quiet_engine):
        if case["case_id"] == "pass_case":
            return _scan_result([10, 20, 40, 38, 12], "2026-04-01T12:00:00")
        return _scan_result([45, 38, 14, 12, 11], "2026-04-01T00:00:00")

    monkeypatch.setattr(runner, "_run_case_scan", fake_run)

    report = runner.run_predictive_hindcast_suite()

    assert report["case_count"] == 2
    assert report["pass_count"] == 1
    assert report["fail_count"] == 1
    assert report["false_positive_policy"]["same_place_temporal_controls"] is True
    assert report["false_positive_policy"]["nearby_place_spillover_allowed"] is True
    assert report["exact_pass_count"] == 1
    assert report["target_window_pass_count"] == 1
    assert report["family_summary"]["flood_risk"]["alignment_pass_count"] == 1
    assert report["family_summary"]["wind_event_pressure"]["alignment_pass_count"] == 0
    assert report["origin_summary"]["source_backed"]["alignment_pass_count"] == 1
    assert report["origin_summary"]["novel_holdout"]["alignment_pass_count"] == 0
    assert report["family_summary"]["wind_event_pressure"]["failure_reasons"]["control_window_outperformed_target"] == 1
    assert report["cases"][0]["case_id"] == "pass_case"
    assert report["cases"][0]["passed"] is True
    assert report["cases"][0]["target_beats_all_controls"] is True
    assert report["cases"][0]["exact_passed"] is True
    assert report["cases"][1]["passed"] is False
    assert "control_window_outperformed_target" in report["cases"][1]["failure_reasons"]


def test_critical_answer_stays_cautious():
    verdict = runner._critical_answer(
        {
            "case_count": 10,
            "alignment_pass_rate": 0.8,
            "exact_pass_rate": 0.3,
            "target_window_hit_rate": 0.8,
            "median_target_percentile": 0.9,
        }
    )
    assert "weak-to-moderate hindcast alignment" in verdict


def test_critical_answer_handles_empty_filtered_suite():
    verdict = runner._critical_answer({"case_count": 0})

    assert "No predictive hindcast cases matched" in verdict


def test_render_markdown_report_states_false_positive_policy():
    report = {
        "case_count": 1,
        "alignment_pass_count": 1,
        "alignment_pass_rate": 1.0,
        "exact_pass_count": 1,
        "exact_pass_rate": 1.0,
        "target_window_pass_count": 1,
        "target_window_pass_rate": 1.0,
        "near_pass_count": 0,
        "near_pass_rate": 0.0,
        "target_window_hit_rate": 1.0,
        "median_target_percentile": 1.0,
        "median_peak_distance_hours": 0.0,
        "critical_answer": "ok",
        "family_summary": {},
        "origin_summary": {},
        "overall_failure_reasons": {},
        "false_positive_policy": runner._false_positive_policy(),
        "cases": [],
    }

    rendered = runner.render_markdown_report(report)

    assert "same-place temporal controls only" in rendered
    assert "nearby-place spillover allowed" in rendered


def test_alignment_pass_can_fail_when_controls_outperform_target():
    case = _case("control_fail", "wind_event_pressure")
    result = _scan_result([30, 45, 40, 38, 20], "2026-04-01T06:00:00")

    summary = runner._summarize_case(case, result)

    assert summary["target_beats_all_controls"] is False
    assert summary["alignment_passed"] is False
    assert "control_window_outperformed_target" in summary["failure_reasons"]


def test_load_predictive_cases_filters_family_id(monkeypatch):
    monkeypatch.setattr(
        runner,
        "load_jsonl_cases",
        lambda _path: [
            _case("flood_case", "flood_risk"),
            _case("wind_case", "wind_event_pressure", case_origin="novel_holdout"),
        ],
    )
    monkeypatch.setattr(runner, "validate_predictive_hindcast_case", lambda *_args, **_kwargs: None)

    cases = runner.load_predictive_cases(family_id="flood_risk")

    assert len(cases) == 1
    assert cases[0]["case_id"] == "flood_case"
    assert cases[0]["runtime_family_id"] == "flood_risk"


def test_load_predictive_cases_filters_case_origin(monkeypatch):
    monkeypatch.setattr(
        runner,
        "load_jsonl_cases",
        lambda _path: [
            _case("source_case", "flood_risk"),
            _case("novel_case", "flood_risk", case_origin="novel_holdout"),
        ],
    )
    monkeypatch.setattr(runner, "validate_predictive_hindcast_case", lambda *_args, **_kwargs: None)

    cases = runner.load_predictive_cases(case_origin="novel_holdout")

    assert len(cases) == 1
    assert cases[0]["case_id"] == "novel_case"
    assert cases[0]["case_origin"] == "novel_holdout"


def test_validate_predictive_case_allows_novel_holdout_without_source_case_id(tmp_path):
    case = _case("novel_case", "flood_risk", case_origin="novel_holdout")

    validate_predictive_hindcast_case(case, tmp_path / "predictive_hindcast_cases.jsonl")


def test_validate_predictive_case_requires_source_case_id_for_source_backed(tmp_path):
    case = _case("source_case", "flood_risk")
    case.pop("source_case_id", None)

    try:
        validate_predictive_hindcast_case(case, tmp_path / "predictive_hindcast_cases.jsonl")
    except ValueError as exc:
        assert "source_case_id is required" in str(exc)
    else:
        raise AssertionError("Expected source-backed predictive hindcast validation to fail without source_case_id")
