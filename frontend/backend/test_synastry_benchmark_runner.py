from __future__ import annotations

from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "AGENTS.md").exists() and (candidate / "backend").is_dir():
            return candidate
    return Path(__file__).resolve().parents[1]


repo_root = _repo_root()
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(backend_dir))

import synastry_benchmark_runner as runner
from validate_synastry_benchmark_datasets import (
    load_logic_fixture,
    load_synastry_predictive_dataset,
    validate_synastry_benchmark_datasets,
)


PREDICTIVE_SAMPLE = backend_dir / "benchmarks" / "synastry" / "predictive_pairs_sample.json"
WORK_OUTCOME_SAMPLE = backend_dir / "benchmarks" / "synastry" / "predictive_work_outcome_sample.json"
REAL_PUBLIC = backend_dir / "benchmarks" / "synastry" / "real_public_pairs.json"
LOGIC_SAMPLE = repo_root / "tests" / "fixtures" / "synastry_benchmark_logic_fixture.json"


def test_synastry_predictive_sample_dataset_is_valid():
    dataset = load_synastry_predictive_dataset(PREDICTIVE_SAMPLE)

    assert len(dataset["people"]) == 4
    assert len(dataset["cases"]) == 3


def test_synastry_logic_fixture_is_valid():
    fixture = load_logic_fixture(LOGIC_SAMPLE)

    assert len(fixture["cases"]) == 1


def test_synastry_work_outcome_sample_dataset_is_valid():
    dataset = load_synastry_predictive_dataset(WORK_OUTCOME_SAMPLE)

    assert len(dataset["people"]) == 3
    assert len(dataset["cases"]) == 4
    assert all(case["mode"] == "work" for case in dataset["cases"])


def test_synastry_real_public_dataset_is_valid():
    dataset = load_synastry_predictive_dataset(REAL_PUBLIC)

    assert len(dataset["people"]) == 19
    assert len(dataset["cases"]) == 16
    assert sum(1 for case in dataset["cases"] if case["mode"] == "union") == 6
    assert sum(1 for case in dataset["cases"] if case["mode"] == "work") == 10
    case_ids = {case["case_id"] for case in dataset["cases"]}
    assert "work_musk_altman_real" in case_ids
    assert "work_buffett_munger_real" in case_ids


def test_synastry_benchmark_validation_counts_sample_inputs():
    report = validate_synastry_benchmark_datasets(
        predictive_dataset_paths=[PREDICTIVE_SAMPLE],
        logic_fixture_paths=[LOGIC_SAMPLE],
    )

    assert report["predictive_people_count"] == 4
    assert report["predictive_case_count"] == 3
    assert report["logic_case_count"] == 1
    assert report["predictive_people_by_kind"]["chart_data"] == 4
    assert report["predictive_mode_counts"] == {"overall": 1, "union": 1, "work": 1}


def test_run_predictive_benchmark_suite_scores_sample_cases():
    report = runner.run_predictive_benchmark_suite(
        [PREDICTIVE_SAMPLE],
        house_system_code="R",
    )

    assert report["case_count"] == 3
    assert report["skipped_case_count"] == 0
    assert report["models"]["memo_overall_score"]["case_count"] == 3
    assert report["models"]["memo_overall_score"]["top3_hit_rate"] == 1.0
    assert report["models"]["memo_legacy_score"]["case_count"] == 1
    assert report["models"]["memo_legacy_score"]["top1_hit_rate"] == 1.0
    assert "memo_legacy_score" in report["models_by_mode"]["overall"]
    assert report["models"]["life_themes_composite_total"]["top1_hit_rate"] == 1.0
    assert report["models"]["union_dynamics_composite_total"]["case_count"] == 1
    assert report["models"]["union_dynamics_composite_total"]["top1_hit_rate"] == 1.0
    assert report["models"]["work_alliance_composite_total"]["case_count"] == 1
    assert report["models"]["work_alliance_composite_total"]["top1_hit_rate"] == 1.0
    assert report["case_counts_by_mode"] == {"overall": 1, "union": 1, "work": 1}
    assert report["models_by_mode"]["union"]["union_dynamics_composite_total"]["case_count"] == 1
    assert report["models_by_mode"]["work"]["work_alliance_composite_total"]["case_count"] == 1
    assert report["models"]["random_expected"]["case_count"] == 3
    assert report["models"]["random_expected"]["top1_hit_rate"] == 0.3333
    assert report["models"]["random_expected"]["mrr"] == 0.6111


def test_run_logic_benchmark_suite_scores_sample_fixture():
    report = runner.run_logic_benchmark_suite([LOGIC_SAMPLE])

    assert report["case_count"] == 1
    assert report["models"]["memo_overall_score"]["case_count"] == 1
    assert report["models"]["life_themes_composite_total"]["case_count"] == 1
    assert report["models"]["union_dynamics_composite_total"]["case_count"] == 1
    assert report["models"]["work_alliance_composite_total"]["case_count"] == 1
    assert report["cases"][0]["models"]["memo_overall_score"]["forward_score"] != 0.0


def test_build_work_outcome_benchmark_suite_groups_pairs_and_labels():
    predictive = runner.run_predictive_benchmark_suite(
        [WORK_OUTCOME_SAMPLE],
        house_system_code="R",
    )
    report = runner.build_work_outcome_benchmark_suite(predictive)

    assert report["pair_case_count"] == 2
    assert report["durable_pair_count"] == 1
    assert report["breakdown_pair_count"] == 1
    assert len(report["pairs"]) == 2
    assert {
        row["outcome_label"] for row in report["pairs"]
    } == {"durable_success", "productive_then_breakdown"}
    assert report["models"]["memo_overall_score"]["case_count"] == 2
    assert report["models"]["work_alliance_aspect_total"]["durable_pair_count"] == 1
    assert report["models"]["work_alliance_aspect_total"]["breakdown_pair_count"] == 1
    assert report["models"]["work_alliance_aspect_total"]["pairwise_comparison_count"] == 1
    assert report["models"]["work_alliance_aspect_total"]["pairwise_win_rate"] is not None


def test_render_markdown_report_mentions_predictive_and_logic_sections():
    report = runner.run_synastry_benchmarks(
        predictive_dataset_paths=[PREDICTIVE_SAMPLE],
        logic_fixture_paths=[LOGIC_SAMPLE],
        house_system_code="R",
    )
    markdown = runner.render_markdown_report(report)

    assert "# Synastry Benchmark Report" in markdown
    assert "## Predictive Ranking" in markdown
    assert "### Overall" in markdown
    assert "### Union" in markdown
    assert "### Work" in markdown
    assert "## Logic Stability" in markdown
    assert "`memo_overall_score`" in markdown
    assert "`memo_legacy_score`" in markdown
    assert "`life_themes_composite_total`" in markdown
    assert "`overall_anchor_a_candidate_e`" in markdown


def test_render_markdown_report_mentions_work_outcome_section():
    report = runner.run_synastry_benchmarks(
        predictive_dataset_paths=[WORK_OUTCOME_SAMPLE],
        logic_fixture_paths=[LOGIC_SAMPLE],
        house_system_code="R",
    )
    markdown = runner.render_markdown_report(report)

    assert "## Work Outcome Separation" in markdown
    assert "Durable-success pairs" in markdown
    assert "Productive-then-breakdown pairs" in markdown
    assert "`work_alliance_aspect_total`" in markdown
    assert "## Work Outcome Pairs" in markdown
