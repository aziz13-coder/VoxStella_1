from __future__ import annotations

import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_ROOT.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "forensic_known_outcome_aviation_holdout_v1.json"

sys.path.insert(0, str(BACKEND_ROOT))

import forensic_statistical_benchmark_runner as runner


def test_known_outcome_holdout_is_balanced_sourced_and_not_a_default_tuning_set():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = payload["cases"]

    assert payload["evaluation_role"] == "locked_external_holdout_v1"
    assert FIXTURE.resolve() not in {Path(path).resolve() for path in runner.DEFAULT_DATASET_PATHS}
    assert len(cases) == 8
    assert len({case["id"] for case in cases}) == 8
    assert [case["known_outcome"]["class"] for case in cases].count("survival_dominant") == 4
    assert [case["known_outcome"]["class"] for case in cases].count("fatal_dominant") == 4
    assert all(len(case.get("sources") or []) >= 2 for case in cases)
    assert all(case.get("anchor_precision") in {"minute", "second"} for case in cases)
    assert all(case.get("expected_primary_axes") == ["accident_or_disaster"] for case in cases)


def test_known_outcome_holdout_replays_real_engine_and_records_each_comparison():
    report = runner.run_statistical_benchmark_suite(
        [FIXTURE],
        include_control_cases=False,
        bootstrap_iterations=50,
    )

    assert report["case_count"] == 8
    assert report["route_error_count"] == 0
    assert report["secondary_survivability_metrics"]["scored_case_count"] == 8
    assert sum(report["secondary_survivability_metrics"]["status_counts"].values()) == 8
    assert 0 <= report["primary_axis_metrics"]["matched_axis_count"] <= 8
    assert len(report["case_results"]) == 8
    for result in report["case_results"]:
        survival = result["survivability"]
        assert survival["known_outcome"]["class"] in {"survival_dominant", "fatal_dominant"}
        assert survival["actual_level"] in {"Lower", "Moderate", "Higher"}
        assert survival["comparison"] in {"aligned", "partially_aligned", "misaligned"}

    markdown = runner.render_markdown_report(report)
    assert "known=survival_dominant" in markdown
    assert "known=fatal_dominant" in markdown
    assert "relationship=not_scored" in markdown
