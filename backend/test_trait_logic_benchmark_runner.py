from __future__ import annotations

import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from trait_logic_benchmark_profiles import (
    get_trait_criminal_figure_baseline_cases,
    get_trait_house_determination_benchmark_cases,
    get_trait_logic_benchmark_cases,
    get_trait_public_figure_baseline_cases,
)
from trait_logic_benchmark_runner import (
    render_criminal_figure_biography_report,
    render_markdown_report,
    render_public_figure_biography_report,
    render_public_figure_baseline_report,
    run_trait_criminal_figure_biography_benchmark,
    run_trait_logic_benchmark_suite,
    run_trait_public_figure_biography_benchmark,
    run_trait_public_figure_baseline_benchmark,
)


def test_trait_logic_benchmark_cases_have_sources_and_targets():
    cases = get_trait_logic_benchmark_cases()
    assert len(cases) >= 6
    seen = set()
    for case in cases:
        case_id = case.get("case_id")
        assert case_id and case_id not in seen
        seen.add(case_id)
        birth = case.get("birth") or {}
        assert birth.get("datetime")
        assert birth.get("location")
        assert birth.get("latitude") is not None
        assert birth.get("longitude") is not None
        assert str(birth.get("source_url") or "").startswith("https://")
        assert case.get("biography_sources")
        for source_url in case.get("biography_sources") or []:
            assert str(source_url).startswith("https://")
        clusters = case.get("expected_clusters") or []
        assert clusters
        for cluster in clusters:
            assert cluster.get("cluster_id")
            assert cluster.get("trait_ids")
            assert float(cluster.get("min_score") or 0) > 0


def test_house_determination_benchmark_cases_are_source_backed():
    cases = get_trait_house_determination_benchmark_cases()
    assert len(cases) >= 5
    seen = set()
    for case in cases:
        case_id = case.get("case_id")
        assert case_id and case_id not in seen
        seen.add(case_id)
        assert case.get("case_type") == "house_determination"
        assert case.get("source_basis")
        metrics = case.get("metrics") or {}
        assert metrics.get("planet_area_scores")
        clusters = case.get("expected_clusters") or []
        assert clusters
        for cluster in clusters:
            assert cluster.get("required_evidence")
            assert float(cluster.get("min_score") or 0) > 0


def test_trait_logic_benchmark_suite_passes():
    report = run_trait_logic_benchmark_suite()
    assert report["passed"], render_markdown_report(report)
    assert report["case_count"] >= 6
    assert report["house_determination_case_count"] >= 5
    assert report["passed_cluster_count"] == report["cluster_count"]


def test_house_determination_benchmark_requires_area_evidence():
    report = run_trait_logic_benchmark_suite(["morin_h6_h10_service_profession"])
    assert report["passed"], render_markdown_report(report)
    cluster = report["cases"][0]["clusters"][0]
    assert cluster["required_evidence"] == ["Mercury area[health]", "Saturn area[health]"]
    assert cluster["evidence_pass"] is True
    assert cluster["score_rank_pass"] is True
    markdown = render_markdown_report(report)
    assert "Evidence: 2/2 Mercury area[health], Saturn area[health]" in markdown


def test_public_figure_baseline_cases_have_aa_a_sources_and_coordinates():
    cases = get_trait_public_figure_baseline_cases()
    assert len(cases) == 68
    seen = set()
    groups = {}
    for case in cases:
        case_id = case.get("case_id")
        assert case_id and case_id not in seen
        seen.add(case_id)
        groups[case.get("benchmark_group")] = groups.get(case.get("benchmark_group"), 0) + 1
        assert case.get("role_target")
        assert case.get("summary_context") == "public_figure_biography"
        birth = case.get("birth") or {}
        assert birth.get("datetime")
        assert birth.get("timezone") == "Etc/GMT+0"
        assert birth.get("house_system_code") == "R"
        assert birth.get("source_rating") in {"AA", "A"}
        assert str(birth.get("source_url") or "").startswith("https://arcadia-astrology.com/en/astrodb/")
        assert case.get("biography_sources")
        assert case.get("expected_clusters")
        assert -90.0 <= float(birth.get("latitude")) <= 90.0
        assert -180.0 <= float(birth.get("longitude")) <= 180.0
    assert groups == {"political_cabinet": 49, "famous_control": 19}


def test_public_figure_baseline_sample_route_passes():
    report = run_trait_public_figure_baseline_benchmark(
        ["emmanuel_macron", "barack_obama", "oprah_winfrey"]
    )
    assert report["passed"], render_public_figure_baseline_report(report)
    assert report["case_count"] == 3
    assert report["source_case_count"] == 68
    for case in report["cases"]:
        assert case["trait_count"] >= report["min_trait_count"]
        assert case["summary_trait_count"] >= report["min_summary_trait_count"]
        assert case["top_traits"]


def test_public_figure_biography_benchmark_sample_passes():
    report = run_trait_public_figure_biography_benchmark(["albert_einstein"])
    assert report["passed"], render_public_figure_biography_report(report)
    assert report["case_count"] == 1
    assert report["passed_cluster_count"] == report["cluster_count"] == 1
    cluster = report["cases"][0]["clusters"][0]
    assert cluster["best_top_trait"]["id"] == "invention_discovery"


def test_criminal_figure_baseline_cases_have_aa_a_sources_and_coordinates():
    cases = get_trait_criminal_figure_baseline_cases()
    assert len(cases) == 21
    seen = set()
    groups = {}
    for case in cases:
        case_id = case.get("case_id")
        assert case_id and case_id not in seen
        seen.add(case_id)
        groups[case.get("benchmark_group")] = groups.get(case.get("benchmark_group"), 0) + 1
        assert case.get("role_target")
        assert case.get("summary_context") == "criminal_biography"
        birth = case.get("birth") or {}
        assert birth.get("datetime")
        assert birth.get("timezone") == "Etc/GMT+0"
        assert birth.get("house_system_code") == "R"
        assert birth.get("source_rating") in {"AA", "A"}
        assert str(birth.get("source_url") or "").startswith("https://arcadia-astrology.com/en/astrodb/")
        assert case.get("biography_sources")
        assert case.get("expected_clusters")
        assert -90.0 <= float(birth.get("latitude")) <= 90.0
        assert -180.0 <= float(birth.get("longitude")) <= 180.0
    assert groups == {
        "assassination": 2,
        "cult_crime": 2,
        "fraud_murder": 1,
        "organized_crime": 6,
        "violent_offender": 10,
    }


def test_criminal_figure_biography_benchmark_sample_passes():
    report = run_trait_criminal_figure_biography_benchmark(
        ["ted_bundy", "john_wayne_gacy", "salvatore_riina"]
    )
    assert report["passed"], render_criminal_figure_biography_report(report)
    assert report["case_count"] == 3
    assert report["source_case_count"] == 21
    assert report["passed_cluster_count"] == report["cluster_count"] == 3
    best_traits = {
        case["case_id"]: case["clusters"][0]["best_top_trait"]["id"]
        for case in report["cases"]
    }
    assert best_traits["ted_bundy"] == "destructiveness"
    assert best_traits["john_wayne_gacy"] == "knavery_trickery_deceit"
    assert best_traits["salvatore_riina"] == "cunning"
