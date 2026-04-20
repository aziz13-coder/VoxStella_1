from pathlib import Path
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mundane_trigger_benchmark_runner


def test_evaluate_trigger_case_result_accepts_matching_profile():
    case = {
        "case_id": "trigger_case",
        "label": "Trigger case",
        "trigger_id": "retrograde_mars",
        "benchmark_refs": ["watters_retrograde_mars_aggressor_defeat"],
        "expectation": {
            "status": "computed",
            "active": True,
            "minimum_score": 20,
            "allowed_strengths": ["active", "strong"],
            "required_metric_values": {"retrograde": True, "mars_house": 1},
            "minimum_evidence_count": 1,
        },
    }
    profile = {
        "id": "retrograde_mars",
        "status": "computed",
        "active": True,
        "strength": "active",
        "score": 20,
        "evidence": [{"planet": "Mars"}],
        "metrics": {"retrograde": True, "mars_house": 1},
    }

    evaluation = mundane_trigger_benchmark_runner.evaluate_trigger_case_result(case, profile)

    assert evaluation["passed"] is True
    assert evaluation["diagnostic_status"] == "strong_pass"
    assert evaluation["failed_checks"] == []


def test_evaluate_trigger_case_result_reports_metric_mismatch():
    case = {
        "case_id": "trigger_case",
        "label": "Trigger case",
        "trigger_id": "mutation_and_conjunction_cycles",
        "benchmark_refs": ["watters_great_mutation_master_chart"],
        "expectation": {
            "status": "computed",
            "active": True,
            "minimum_score": 12,
            "required_metric_values": {"turning_window_active": True},
        },
    }
    profile = {
        "id": "mutation_and_conjunction_cycles",
        "status": "computed",
        "active": False,
        "strength": "watch",
        "score": 6,
        "evidence": [{}],
        "metrics": {"turning_window_active": False},
    }

    evaluation = mundane_trigger_benchmark_runner.evaluate_trigger_case_result(case, profile)

    assert evaluation["passed"] is False
    assert "active_mismatch" in evaluation["failed_checks"]
    assert "score_below_minimum" in evaluation["failed_checks"]
    assert "metric_mismatch:turning_window_active" in evaluation["failed_checks"]


def test_run_trigger_benchmark_suite_aggregates_results(monkeypatch):
    cases = [
        {
            "case_id": "case_a",
            "label": "Case A",
            "trigger_id": "angularity",
            "benchmark_refs": ["green_visible_angular_eclipse"],
            "expectation": {"status": "computed", "active": True, "minimum_score": 10},
        },
        {
            "case_id": "case_b",
            "label": "Case B",
            "trigger_id": "mutation_and_conjunction_cycles",
            "benchmark_refs": ["watters_great_mutation_master_chart"],
            "expectation": {"status": "computed", "active": True, "minimum_score": 10},
        },
    ]

    monkeypatch.setattr(
        mundane_trigger_benchmark_runner,
        "load_trigger_benchmark_cases",
        lambda **kwargs: (cases, []),
    )

    def _fake_execute(case, *, active_clock):
        if case["case_id"] == "case_a":
            return {"id": "angularity", "status": "computed", "active": True, "strength": "active", "score": 16, "evidence": [{"planet": "Mars"}], "metrics": {}}
        return {"id": "mutation_and_conjunction_cycles", "status": "background_only", "active": False, "strength": "inactive", "score": 0, "evidence": [], "metrics": {"turning_window_active": False}}

    monkeypatch.setattr(mundane_trigger_benchmark_runner, "execute_trigger_case", _fake_execute)

    summary = mundane_trigger_benchmark_runner.run_trigger_benchmark_suite()

    assert summary["case_count"] == 2
    assert summary["pass_count"] == 1
    assert summary["fail_count"] == 1
