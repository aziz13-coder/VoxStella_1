from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import weather_benchmark_profiles


def test_missing_benchmark_files_fall_back_to_seeded_defaults(monkeypatch, tmp_path):
    weather_benchmark_profiles.build_weather_family_profiles.cache_clear()
    monkeypatch.setattr(weather_benchmark_profiles, "DEFAULT_DATASET_PATHS", [tmp_path / "missing.jsonl"])

    try:
        profile = weather_benchmark_profiles.get_weather_family_profile("wind")
        branch_metrics = weather_benchmark_profiles.get_weather_branch_metrics()
    finally:
        weather_benchmark_profiles.build_weather_family_profiles.cache_clear()

    assert profile["benchmark_family_id"] == "wind"
    assert profile["coverage_tier"] == "seeded"
    assert "no_benchmark_rows" in profile["gaps"]
    assert branch_metrics["family_profile_count"] == 0
    assert branch_metrics["coverage_counts"] == {}


def test_family_profiles_include_doctrine_source_alignment_support():
    weather_benchmark_profiles.build_weather_family_profiles.cache_clear()
    try:
        profile = weather_benchmark_profiles.get_weather_family_profile("wind")
    finally:
        weather_benchmark_profiles.build_weather_family_profiles.cache_clear()

    assert profile["historical_source_count"] == 1
    assert profile["doctrine_source_count"] >= 2
    assert profile["doctrine_case_count"] >= 2
    assert profile["source_count"] > profile["historical_source_count"]
    assert "source_concentrated" not in profile["gaps"]
