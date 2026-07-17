from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))

import forensic_roommate_benchmark_runner as runner


def test_worst_roommate_dataset_covers_released_episode_inventory():
    payload = runner.load_worst_roommate_benchmark_dataset()
    validation = runner.validate_worst_roommate_dataset(payload)

    assert validation["case_count"] == 9
    assert validation["season_counts"] == {1: 5, 2: 4}
    assert validation["runnable_case_count"] >= 4
    assert validation["holdout_case_count"] >= 4
    assert validation["missing_source_references"] == []
    assert validation["fact_source_gaps"] == []

    source_ids = {source["id"] for source in payload.get("sources") or []}
    for case in payload.get("cases") or []:
        assert case["episode"]["source_ids"]
        assert set(case["episode"]["source_ids"]).issubset(source_ids)
        assert case["case_inventory"]["birth_times"]["status"] == "not_used_not_collected"
        assert case["benchmark"]["replay_status"] in {
            "runnable",
            "holdout_missing_precise_event_time",
        }


def test_axis_comparison_uses_expected_and_contradictory_axes():
    case = {
        "benchmark": {
            "expected_primary_axes": ["violence_homicide", "deception_coverup"],
            "contradictory_axes": ["child_victim"],
        }
    }
    forensic_payload = {
        "categories": {"violence": 2},
        "findings": [
            {
                "title": "Known-person homicide pressure",
                "category": "violence",
                "rationale": "The testimony emphasizes murder, concealment, and hidden cover-up behavior.",
            }
        ],
    }

    assert runner.compare_case_to_forensic_output(case, forensic_payload) == {
        "status": "aligned",
        "matched_axes": ["violence_homicide", "deception_coverup"],
        "missed_axes": [],
        "contradicted_axes": [],
    }


def test_markdown_report_mentions_core_benchmark_sections(monkeypatch):
    def fake_route_payload(query):
        return {
            "status_code": 200,
            "payload": {
                "success": True,
                "categories": {"violence": 1},
                "findings": [
                    {
                        "title": "Homicide and concealment testimony",
                        "category": "violence",
                        "rationale": "Murder, hidden remains, and cover-up indicators are present.",
                    }
                ],
                "survivability": {
                    "level": "Lower",
                    "outcome_band": "fatal_pressure_dominant",
                    "score": 12,
                },
            },
        }

    monkeypatch.setattr(runner, "_call_forensic_route", fake_route_payload)
    report = runner.run_worst_roommate_benchmark_suite()
    markdown = runner.render_markdown_report(report)

    assert report["inventory"]["case_count"] == 9
    assert report["metrics"]["runnable_case_count"] >= 4
    assert "# Worst Roommate Ever Forensic Benchmark Report" in markdown
    assert "## Inventory" in markdown
    assert "## Baseline Metrics" in markdown
    assert "## Runnable Case Results" in markdown
    assert "## Holdouts" in markdown


def test_live_forensic_route_matches_frozen_worst_roommate_baselines():
    payload = runner.load_worst_roommate_benchmark_dataset()
    cases_by_id = {case["id"]: case for case in payload.get("cases") or []}
    report = runner.run_worst_roommate_benchmark_suite()

    assert report["route_errors"] == []
    assert report["metrics"]["runnable_case_count"] == 4

    for result in report["case_results"]:
        case = cases_by_id[result["case_id"]]
        benchmark = case["benchmark"]
        assert result["comparison"] == benchmark["current_comparison_baseline"]
        assert (
            result["survivability_comparison"]["status"]
            == benchmark["current_survivability_baseline"]["status"]
        )
        assert result["survivability"]["level"] == benchmark["current_survivability_baseline"]["level"]
        assert (
            result["survivability"]["outcome_band"]
            == benchmark["current_survivability_baseline"]["outcome_band"]
        )
