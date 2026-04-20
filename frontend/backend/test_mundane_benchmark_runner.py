from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mundane_benchmark_runner import DEFAULT_DATASET_PATHS, render_markdown_report, run_mundane_benchmark_suite


def test_mundane_benchmark_suite_loads_seed_cases_without_citation_failures():
    report = run_mundane_benchmark_suite(DEFAULT_DATASET_PATHS)

    assert report["case_count"] >= 45
    assert report["unique_case_count"] >= 35
    assert report["source_alignment_case_count"] >= 14
    assert report["historical_case_count"] >= 30
    assert report["national_chart_candidate_count"] >= 7
    assert report["citation_failures"] == []
    assert report["domain_counts"]["war_conflict"] >= 2
    assert report["domain_counts"]["diplomacy_foreign_affairs"] >= 2
    assert report["domain_counts"]["public_health"] >= 8
    assert report["domain_counts"]["national_chart_proving"] >= 4
    assert report["candidate_status_counts"]["contested_candidate"] >= 1


def test_mundane_benchmark_markdown_report_mentions_core_sections():
    report = run_mundane_benchmark_suite(DEFAULT_DATASET_PATHS)
    markdown = render_markdown_report(report)

    assert "# Mundane Benchmark Report" in markdown
    assert "## Coverage" in markdown
    assert "Unique case IDs" in markdown
    assert "National-chart candidate cases" in markdown
    assert "`war_conflict`" in markdown
    assert "`chart_framework`" in markdown
    assert "`diplomacy_foreign_affairs`" in markdown
    assert "`public_health`" in markdown
    assert "`public_health_trigger`" in markdown
    assert "`national_chart_proving`" in markdown
