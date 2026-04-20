from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from typing import Any, Dict, Iterable, List

from validate_mundane_benchmark_datasets import HISTORICAL_FILES, load_jsonl_cases


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split()).lower().replace(" ", "_")


def _default_profile(domain_id: str) -> Dict[str, Any]:
    return {
        "domain_id": domain_id,
        "unique_case_count": 0,
        "dataset_row_count": 0,
        "distinct_source_count": 0,
        "distinct_sources": [],
        "dataset_names": [],
        "benchmark_types": {},
        "seed_quality_counts": {},
        "chart_basis_counts": {},
        "coverage_tier": "unseeded",
        "confidence_factor": 0.8,
        "score_cap": 70,
        "explicit_case_ratio": 0.0,
        "gaps": ["no_benchmark_cases"],
    }


def _coverage_tier(unique_case_count: int, distinct_source_count: int) -> str:
    if unique_case_count >= 7 and distinct_source_count >= 3:
        return "broad"
    if unique_case_count >= 4 and distinct_source_count >= 2:
        return "supported"
    if unique_case_count >= 2:
        return "moderate"
    if unique_case_count >= 1:
        return "seeded"
    return "unseeded"


def _confidence_factor(coverage_tier: str, *, explicit_case_ratio: float, benchmark_type_count: int) -> float:
    factor = {
        "broad": 1.0,
        "supported": 0.97,
        "moderate": 0.92,
        "seeded": 0.88,
        "unseeded": 0.8,
    }.get(coverage_tier, 0.8)
    if explicit_case_ratio < 0.5:
        factor -= 0.03
    if benchmark_type_count >= 2:
        factor += 0.01
    return max(0.75, min(1.0, factor))


def _score_cap(coverage_tier: str) -> int:
    return {
        "broad": 100,
        "supported": 95,
        "moderate": 90,
        "seeded": 85,
        "unseeded": 70,
    }.get(coverage_tier, 70)


@lru_cache(maxsize=1)
def load_domain_benchmark_profiles() -> Dict[str, Dict[str, Any]]:
    rows_by_domain: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    unique_cases_by_domain: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)

    for path in HISTORICAL_FILES:
        if not path.exists():
            continue
        for case in load_jsonl_cases(path):
            if not bool(case.get("enabled")):
                continue
            domain_id = _normalize_text(case.get("domain_id"))
            case_id = _normalize_text(case.get("case_id"))
            if not domain_id or not case_id:
                continue
            rows_by_domain[domain_id].append({"dataset_name": path.name, **case})
            unique_cases_by_domain[domain_id].setdefault(case_id, {"dataset_name": path.name, **case})

    profiles: Dict[str, Dict[str, Any]] = {}
    for domain_id, rows in rows_by_domain.items():
        unique_cases = list(unique_cases_by_domain[domain_id].values())
        source_titles = {
            str(assertion.get("title") or "").strip()
            for case in unique_cases
            for assertion in (case.get("source_assertions") or [])
            if isinstance(assertion, dict) and str(assertion.get("title") or "").strip()
        }
        benchmark_type_counts: Counter[str] = Counter()
        seed_quality_counts: Counter[str] = Counter()
        chart_basis_counts: Counter[str] = Counter()
        explicit_case_count = 0

        for case in unique_cases:
            benchmark_type = _normalize_text(case.get("benchmark_type"))
            if benchmark_type:
                benchmark_type_counts[benchmark_type] += 1
            seed_quality = _normalize_text(case.get("seed_quality") or "unspecified")
            if seed_quality:
                seed_quality_counts[seed_quality] += 1
            if seed_quality == "source_explicit":
                explicit_case_count += 1
            for basis in case.get("chart_basis") or []:
                normalized_basis = _normalize_text(basis)
                if normalized_basis:
                    chart_basis_counts[normalized_basis] += 1

        unique_case_count = len(unique_cases)
        distinct_source_count = len(source_titles)
        coverage_tier = _coverage_tier(unique_case_count, distinct_source_count)
        explicit_case_ratio = explicit_case_count / unique_case_count if unique_case_count else 0.0
        confidence_factor = _confidence_factor(
            coverage_tier,
            explicit_case_ratio=explicit_case_ratio,
            benchmark_type_count=len(benchmark_type_counts),
        )
        score_cap = _score_cap(coverage_tier)
        gaps: List[str] = []
        if unique_case_count <= 1:
            gaps.append("single_case_benchmark")
        if distinct_source_count <= 1:
            gaps.append("source_concentrated")
        if len(benchmark_type_counts) <= 1:
            gaps.append("narrow_benchmark_shape")

        profiles[domain_id] = {
            "domain_id": domain_id,
            "unique_case_count": unique_case_count,
            "dataset_row_count": len(rows),
            "distinct_source_count": distinct_source_count,
            "distinct_sources": sorted(source_titles),
            "dataset_names": sorted({str(row.get("dataset_name") or "") for row in rows if str(row.get("dataset_name") or "")}),
            "benchmark_types": dict(sorted(benchmark_type_counts.items())),
            "seed_quality_counts": dict(sorted(seed_quality_counts.items())),
            "chart_basis_counts": dict(sorted(chart_basis_counts.items())),
            "coverage_tier": coverage_tier,
            "confidence_factor": confidence_factor,
            "score_cap": score_cap,
            "explicit_case_ratio": round(explicit_case_ratio, 3),
            "gaps": gaps,
        }

    return profiles


def get_domain_benchmark_profile(domain_id: str) -> Dict[str, Any]:
    normalized_domain_id = _normalize_text(domain_id)
    if not normalized_domain_id:
        return _default_profile(normalized_domain_id)
    profile = load_domain_benchmark_profiles().get(normalized_domain_id)
    if profile is None:
        return _default_profile(normalized_domain_id)
    return dict(profile)


def calibrate_domain_score(domain_id: str, raw_score: int) -> Dict[str, Any]:
    profile = get_domain_benchmark_profile(domain_id)
    adjusted_score = int(round(max(0, raw_score) * float(profile.get("confidence_factor") or 0.8)))
    adjusted_score = min(int(profile.get("score_cap") or 70), adjusted_score)
    return {
        "profile": profile,
        "raw_score": int(raw_score),
        "adjusted_score": adjusted_score,
    }
