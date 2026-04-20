from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_weather_benchmark_datasets import validate_weather_benchmark_datasets
from weather_benchmark_runner import DEFAULT_DATASET_PATHS, render_markdown_report, run_weather_benchmark_suite


def test_weather_benchmark_datasets_validate_seed_branch():
    report = validate_weather_benchmark_datasets()

    assert report["source_alignment_case_count"] >= 13
    assert report["historical_case_count"] >= 29
    assert report["dataset_row_count"] >= 42


def test_weather_benchmark_suite_loads_seed_cases_without_citation_failures():
    report = run_weather_benchmark_suite(DEFAULT_DATASET_PATHS)

    assert report["case_count"] >= 42
    assert report["unique_case_count"] >= 28
    assert report["source_alignment_case_count"] >= 13
    assert report["historical_case_count"] >= 29
    assert report["citation_failures"] == []
    assert report["family_counts"]["floods"] >= 2
    assert report["family_counts"]["hurricanes"] >= 2
    assert report["family_counts"]["thunderstorms_tornadoes"] >= 2
    assert report["family_counts"]["drought"] >= 2
    assert report["family_counts"]["snow_freezing_precipitation"] >= 2
    assert report["family_counts"]["temperature_extremes"] >= 2
    assert report["family_counts"]["wind"] >= 3
    assert report["family_counts"]["generalized_seasonal_temperature"] >= 2


def test_weather_benchmark_markdown_report_mentions_core_sections():
    report = run_weather_benchmark_suite(DEFAULT_DATASET_PATHS)
    markdown = render_markdown_report(report)

    assert "# Weather Benchmark Report" in markdown
    assert "## Coverage" in markdown
    assert "Unique case IDs" in markdown
    assert "`floods`" in markdown
    assert "`hurricanes`" in markdown
    assert "`thunderstorms_tornadoes`" in markdown
    assert "`drought`" in markdown
    assert "`snow_freezing_precipitation`" in markdown
    assert "`temperature_extremes`" in markdown
    assert "`wind`" in markdown
    assert "`generalized_seasonal_temperature`" in markdown
    assert "`weather_framework`" in markdown
