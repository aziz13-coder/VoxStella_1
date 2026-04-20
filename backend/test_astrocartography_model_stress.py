from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from astrocartography_model_stress import run_stress_suite


def test_model_stress_suite_has_no_expectation_failures():
    report = run_stress_suite()
    assert report["scenario_count"] >= 10
    assert report["goal_count"] >= 19
    assert report["expectation_failures"] == []


def test_model_stress_suite_limits_extreme_goal_overlap():
    report = run_stress_suite()
    problematic = [
        pair for pair in (report.get("high_overlap_pairs") or [])
        if float(pair.get("similarity") or 0.0) >= 0.97
    ]
    assert problematic == []
