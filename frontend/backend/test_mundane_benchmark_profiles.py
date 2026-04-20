from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mundane_benchmark_profiles
from mundane_benchmark_profiles import calibrate_domain_score, get_domain_benchmark_profile


def test_public_health_profile_reports_multi_case_coverage():
    profile = get_domain_benchmark_profile("public_health")

    assert profile["domain_id"] == "public_health"
    assert profile["unique_case_count"] >= 4
    assert profile["distinct_source_count"] >= 2
    assert profile["coverage_tier"] in {"supported", "broad", "moderate"}


def test_alliance_stress_profile_is_supported_after_post_phase5_hardening():
    profile = get_domain_benchmark_profile("alliance_stress")

    assert profile["domain_id"] == "alliance_stress"
    assert profile["unique_case_count"] >= 4
    assert profile["distinct_source_count"] >= 2
    assert profile["coverage_tier"] in {"supported", "broad"}
    assert "single_case_benchmark" not in profile["gaps"]


def test_trade_and_commerce_profile_is_broad_after_post_phase5_hardening():
    profile = get_domain_benchmark_profile("trade_and_commerce")

    assert profile["domain_id"] == "trade_and_commerce"
    assert profile["unique_case_count"] >= 7
    assert profile["distinct_source_count"] >= 3
    assert profile["coverage_tier"] == "broad"


def test_epidemic_wave_pressure_profile_is_broad_after_post_phase5_hardening():
    profile = get_domain_benchmark_profile("epidemic_wave_pressure")

    assert profile["domain_id"] == "epidemic_wave_pressure"
    assert profile["unique_case_count"] >= 7
    assert profile["distinct_source_count"] >= 3
    assert profile["coverage_tier"] == "broad"


def test_regime_stability_profile_is_supported_after_post_phase5_hardening():
    profile = get_domain_benchmark_profile("regime_stability")

    assert profile["domain_id"] == "regime_stability"
    assert profile["unique_case_count"] >= 4
    assert profile["distinct_source_count"] >= 2
    assert profile["coverage_tier"] in {"supported", "broad"}
    assert "narrow_benchmark_shape" not in profile["gaps"]


def test_civil_unrest_profile_is_supported_after_non_british_hardening():
    profile = get_domain_benchmark_profile("civil_unrest")

    assert profile["domain_id"] == "civil_unrest"
    assert profile["unique_case_count"] >= 4
    assert profile["distinct_source_count"] >= 2
    assert profile["coverage_tier"] in {"supported", "broad"}


def test_unknown_domain_profile_falls_back_to_unseeded_defaults():
    calibration = calibrate_domain_score("unknown_domain", 80)

    assert calibration["profile"]["coverage_tier"] == "unseeded"
    assert calibration["adjusted_score"] == 64
    assert "no_benchmark_cases" in calibration["profile"]["gaps"]


def test_missing_benchmark_files_fall_back_to_defaults(monkeypatch, tmp_path):
    mundane_benchmark_profiles.load_domain_benchmark_profiles.cache_clear()
    monkeypatch.setattr(mundane_benchmark_profiles, "HISTORICAL_FILES", [tmp_path / "missing.jsonl"])

    try:
        profile = get_domain_benchmark_profile("war_conflict")
    finally:
        mundane_benchmark_profiles.load_domain_benchmark_profiles.cache_clear()

    assert profile["coverage_tier"] == "unseeded"
    assert "no_benchmark_cases" in profile["gaps"]
