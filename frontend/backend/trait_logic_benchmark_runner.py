from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from flask import Flask

try:
    import backend.astro_clock_api as astro_clock_api
except Exception:
    import astro_clock_api  # type: ignore

try:
    from trait_logic_benchmark_profiles import (
        get_trait_criminal_figure_baseline_cases,
        get_trait_house_determination_benchmark_cases,
        get_trait_logic_benchmark_cases,
        get_trait_public_figure_baseline_cases,
    )
except Exception:
    from .trait_logic_benchmark_profiles import (
        get_trait_criminal_figure_baseline_cases,
        get_trait_house_determination_benchmark_cases,
        get_trait_logic_benchmark_cases,
        get_trait_public_figure_baseline_cases,
    )

try:
    from backend.traits.engine import TraitEngine
except Exception:
    from traits.engine import TraitEngine  # type: ignore


def _make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def _case_query_params(case: Dict[str, Any]) -> Dict[str, Any]:
    birth = case.get("birth") or {}
    params = {
        "mode": "manual",
        "datetime": birth.get("datetime"),
        "location": birth.get("location"),
        "timezone": birth.get("timezone") or "Etc/GMT+0",
        "latitude": birth.get("latitude"),
        "longitude": birth.get("longitude"),
        "house_system_code": birth.get("house_system_code") or "R",
    }
    summary_context = str(case.get("summary_context") or "").strip()
    if summary_context:
        params["summary_context"] = summary_context
    return params


def _rank_maps(profile: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
    trait_by_id: Dict[str, Dict[str, Any]] = {}
    for row in profile.get("traits") or []:
        trait_id = str(row.get("id") or "")
        if trait_id:
            trait_by_id.setdefault(trait_id, row)
    summary_rank: Dict[str, int] = {}
    for index, row in enumerate(profile.get("summary_traits") or [], start=1):
        trait_id = str(row.get("id") or "")
        if trait_id:
            summary_rank.setdefault(trait_id, index)
    return trait_by_id, summary_rank


def _evaluate_cluster(
    cluster: Dict[str, Any],
    trait_by_id: Dict[str, Dict[str, Any]],
    summary_rank: Dict[str, int],
) -> Dict[str, Any]:
    trait_ids = [str(item) for item in cluster.get("trait_ids") or [] if str(item)]
    min_score = float(cluster.get("min_score") or 0.0)
    max_summary_rank = int(cluster.get("max_summary_rank") or 0)
    candidates: List[Dict[str, Any]] = []
    for trait_id in trait_ids:
        trait = trait_by_id.get(trait_id)
        rank = summary_rank.get(trait_id)
        if trait is None:
            candidates.append({"id": trait_id, "present": False, "score": 0.0, "summary_rank": rank})
            continue
        try:
            score = float(trait.get("score") or 0.0)
        except Exception:
            score = 0.0
        evidence = [str(item) for item in (trait.get("evidence") or []) if str(item)]
        candidates.append(
            {
                "id": trait_id,
                "present": True,
                "score": round(score, 1),
                "summary_rank": rank,
                "band": trait.get("band"),
                "support_hits": trait.get("support_hits"),
                "support_total": trait.get("support_total"),
                "evidence": evidence,
            }
        )

    scored = [item for item in candidates if item.get("present")]
    best = max(
        scored,
        key=lambda item: (
            float(item.get("score") or 0.0),
            -int(item.get("summary_rank") or 999999),
        ),
        default=None,
    )
    best_score = float(best.get("score") or 0.0) if best else 0.0
    ranked = [
        item
        for item in scored
        if item.get("summary_rank") is not None
        and max_summary_rank > 0
        and int(item.get("summary_rank") or 999999) <= max_summary_rank
    ]
    score_rank_pass = bool(best_score >= min_score or ranked)
    required_evidence = [str(item) for item in (cluster.get("required_evidence") or []) if str(item)]
    evidence_text = "\n".join(
        line
        for candidate in candidates
        for line in (candidate.get("evidence") or [])
        if str(line)
    )
    evidence_hits = [token for token in required_evidence if token in evidence_text]
    evidence_pass = not required_evidence or len(evidence_hits) == len(required_evidence)
    passed = score_rank_pass and evidence_pass
    return {
        "cluster_id": cluster.get("cluster_id"),
        "label": cluster.get("label"),
        "passed": passed,
        "score_rank_pass": score_rank_pass,
        "min_score": min_score,
        "max_summary_rank": max_summary_rank or None,
        "best_trait": best,
        "candidate_traits": candidates,
        "required_evidence": required_evidence,
        "evidence_hits": evidence_hits,
        "evidence_pass": evidence_pass,
        "rationale": cluster.get("rationale"),
    }


def _evaluate_biographical_cluster(
    cluster: Dict[str, Any],
    trait_by_id: Dict[str, Dict[str, Any]],
    summary_rank: Dict[str, int],
) -> Dict[str, Any]:
    evaluated = _evaluate_cluster(cluster, trait_by_id, summary_rank)
    min_score = float(cluster.get("min_score") or 0.0)
    max_summary_rank = int(cluster.get("max_summary_rank") or 0)
    top_matches = []
    for candidate in evaluated.get("candidate_traits") or []:
        if not candidate.get("present"):
            continue
        rank = candidate.get("summary_rank")
        score = float(candidate.get("score") or 0.0)
        if rank is None or max_summary_rank <= 0:
            continue
        if int(rank) <= max_summary_rank and score >= min_score:
            top_matches.append(candidate)
    best_top = max(
        top_matches,
        key=lambda item: (
            float(item.get("score") or 0.0),
            -int(item.get("summary_rank") or 999999),
        ),
        default=None,
    )
    evaluated["passed"] = bool(best_top)
    evaluated["top_trait_pass"] = bool(best_top)
    evaluated["best_top_trait"] = best_top
    if not best_top:
        best_trait = evaluated.get("best_trait") or {}
        if not best_trait:
            failure_kind = "missing_expected_trait"
        else:
            best_score = float(best_trait.get("score") or 0.0)
            best_rank = best_trait.get("summary_rank")
            if best_score < min_score:
                failure_kind = "score_below_threshold"
            elif best_rank is None:
                failure_kind = "not_summary_represented"
            elif max_summary_rank > 0 and int(best_rank) > max_summary_rank:
                failure_kind = "summary_rank_too_low"
            else:
                failure_kind = "unknown_biography_failure"
        evaluated["failure_kind"] = failure_kind
    evaluated["pass_rule"] = (
        f"One expected trait must have score >= {min_score:g} "
        f"and summary rank <= {max_summary_rank}."
    )
    return evaluated


def _evaluate_direct_metrics_case(case: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], int, int]:
    elapsed_start = time.perf_counter()
    engine = TraitEngine()
    profile = engine.evaluate(dict(case.get("metrics") or {}), min_score=float(case.get("min_profile_score") or 0.0))
    elapsed_ms = int(round((time.perf_counter() - elapsed_start) * 1000))
    trait_by_id, summary_rank = _rank_maps(profile)
    clusters = [
        _evaluate_cluster(cluster, trait_by_id, summary_rank)
        for cluster in case.get("expected_clusters") or []
    ]
    failed = [
        {
            "case_id": case.get("case_id"),
            "cluster_id": cluster.get("cluster_id"),
            "label": cluster.get("label"),
        }
        for cluster in clusters
        if not cluster.get("passed")
    ]
    result = {
        "case_id": case.get("case_id"),
        "label": case.get("label"),
        "case_type": case.get("case_type") or "house_determination",
        "passed": all(cluster.get("passed") for cluster in clusters),
        "elapsed_ms": elapsed_ms,
        "source_basis": case.get("source_basis") or [],
        "summary": profile.get("summary") or {},
        "clusters": clusters,
    }
    return result, failed, len(clusters), sum(1 for cluster in clusters if cluster.get("passed"))


def run_trait_logic_benchmark_suite(
    case_ids: Optional[Iterable[str]] = None,
    *,
    app: Optional[Flask] = None,
) -> Dict[str, Any]:
    selected = set(str(case_id) for case_id in (case_ids or []) if str(case_id))
    public_cases_all = get_trait_logic_benchmark_cases()
    house_cases_all = get_trait_house_determination_benchmark_cases()
    cases = [
        case
        for case in public_cases_all
        if not selected or str(case.get("case_id")) in selected
    ]
    house_cases = [
        case
        for case in house_cases_all
        if not selected or str(case.get("case_id")) in selected
    ]
    if selected and len(cases) + len(house_cases) != len(selected):
        known = {str(case.get("case_id")) for case in public_cases_all + house_cases_all}
        missing = sorted(selected - known)
        raise ValueError(f"Unknown trait benchmark case ids: {', '.join(missing)}")

    client = (app or _make_app()).test_client() if cases else None
    started = time.perf_counter()
    case_results: List[Dict[str, Any]] = []
    cluster_total = 0
    cluster_passed = 0
    failed_clusters: List[Dict[str, Any]] = []
    previous_engine = getattr(astro_clock_api, "_engine", None)
    previous_traits_engine = getattr(astro_clock_api, "_traits_engine", None)

    try:
        for case in cases:
            params = _case_query_params(case)
            elapsed_start = time.perf_counter()
            response = client.get("/api/astro-clock/traits/profile", query_string=params)  # type: ignore[union-attr]
            elapsed_ms = int(round((time.perf_counter() - elapsed_start) * 1000))
            if response.status_code != 200:
                failure = {
                    "case_id": case.get("case_id"),
                    "label": case.get("label"),
                    "passed": False,
                    "elapsed_ms": elapsed_ms,
                    "error": response.get_data(as_text=True)[:500],
                    "clusters": [],
                }
                case_results.append(failure)
                failed_clusters.append({"case_id": case.get("case_id"), "cluster_id": "route_error"})
                continue

            payload = response.get_json(silent=True) or {}
            profile = payload.get("data") or {}
            trait_by_id, summary_rank = _rank_maps(profile)
            clusters = [
                _evaluate_cluster(cluster, trait_by_id, summary_rank)
                for cluster in case.get("expected_clusters") or []
            ]
            cluster_total += len(clusters)
            cluster_passed += sum(1 for cluster in clusters if cluster.get("passed"))
            for cluster in clusters:
                if not cluster.get("passed"):
                    failed_clusters.append(
                        {
                            "case_id": case.get("case_id"),
                            "cluster_id": cluster.get("cluster_id"),
                            "label": cluster.get("label"),
                        }
                    )
            case_results.append(
                {
                    "case_id": case.get("case_id"),
                    "label": case.get("label"),
                    "case_type": "public_figure_route",
                    "passed": all(cluster.get("passed") for cluster in clusters),
                    "elapsed_ms": elapsed_ms,
                    "birth_source": (case.get("birth") or {}).get("source_url"),
                    "birth_source_quality": (case.get("birth") or {}).get("source_quality"),
                    "biography_sources": case.get("biography_sources") or [],
                    "summary": profile.get("summary") or {},
                    "clusters": clusters,
                }
            )

        for case in house_cases:
            try:
                result, failed, total, passed = _evaluate_direct_metrics_case(case)
            except Exception as exc:
                result = {
                    "case_id": case.get("case_id"),
                    "label": case.get("label"),
                    "case_type": case.get("case_type") or "house_determination",
                    "passed": False,
                    "elapsed_ms": 0,
                    "error": str(exc)[:500],
                    "source_basis": case.get("source_basis") or [],
                    "clusters": [],
                }
                failed = [{"case_id": case.get("case_id"), "cluster_id": "direct_metrics_error"}]
                total = 0
                passed = 0
            cluster_total += total
            cluster_passed += passed
            failed_clusters.extend(failed)
            case_results.append(result)
    finally:
        if hasattr(astro_clock_api, "_engine"):
            astro_clock_api._engine = previous_engine
        if hasattr(astro_clock_api, "_traits_engine"):
            astro_clock_api._traits_engine = previous_traits_engine

    elapsed_ms = int(round((time.perf_counter() - started) * 1000))
    return {
        "suite": "trait_logic_benchmark_suite",
        "case_count": len(cases) + len(house_cases),
        "public_case_count": len(cases),
        "house_determination_case_count": len(house_cases),
        "cluster_count": cluster_total,
        "passed_cluster_count": cluster_passed,
        "failed_cluster_count": cluster_total - cluster_passed + sum(
            1 for item in failed_clusters if item.get("cluster_id") == "route_error"
        ),
        "passed": not failed_clusters,
        "elapsed_ms": elapsed_ms,
        "failed_clusters": failed_clusters,
        "cases": case_results,
    }


def _top_summary_traits(profile: Dict[str, Any], limit: int = 8) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in (profile.get("summary_traits") or [])[:limit]:
        trait_id = str(row.get("id") or "")
        if not trait_id:
            continue
        try:
            score = round(float(row.get("score") or 0.0), 1)
        except Exception:
            score = 0.0
        out.append(
            {
                "id": trait_id,
                "label": row.get("label") or trait_id.replace("_", " ").title(),
                "score": score,
                "band": row.get("band"),
            }
        )
    return out


def run_trait_public_figure_baseline_benchmark(
    case_ids: Optional[Iterable[str]] = None,
    *,
    app: Optional[Flask] = None,
    min_trait_count: int = 10,
    min_summary_trait_count: int = 3,
) -> Dict[str, Any]:
    selected = set(str(case_id) for case_id in (case_ids or []) if str(case_id))
    all_cases = get_trait_public_figure_baseline_cases()
    cases = [
        case
        for case in all_cases
        if not selected or str(case.get("case_id")) in selected
    ]
    if selected and len(cases) != len(selected):
        known = {str(case.get("case_id")) for case in all_cases}
        missing = sorted(selected - known)
        raise ValueError(f"Unknown public-figure benchmark case ids: {', '.join(missing)}")

    client = (app or _make_app()).test_client()
    started = time.perf_counter()
    case_results: List[Dict[str, Any]] = []
    failed_cases: List[Dict[str, Any]] = []
    previous_engine = getattr(astro_clock_api, "_engine", None)
    previous_traits_engine = getattr(astro_clock_api, "_traits_engine", None)

    try:
        for case in cases:
            params = _case_query_params(case)
            elapsed_start = time.perf_counter()
            response = client.get("/api/astro-clock/traits/profile", query_string=params)
            elapsed_ms = int(round((time.perf_counter() - elapsed_start) * 1000))
            birth = case.get("birth") or {}
            base_result: Dict[str, Any] = {
                "case_id": case.get("case_id"),
                "label": case.get("label"),
                "benchmark_group": case.get("benchmark_group"),
                "role_target": case.get("role_target"),
                "rating": birth.get("source_rating"),
                "birth_source": birth.get("source_url"),
                "birth_source_quality": birth.get("source_quality"),
                "source_local_time": birth.get("source_local_time"),
                "elapsed_ms": elapsed_ms,
            }
            if response.status_code != 200:
                result = {
                    **base_result,
                    "passed": False,
                    "error": response.get_data(as_text=True)[:500],
                    "trait_count": 0,
                    "summary_trait_count": 0,
                    "top_traits": [],
                }
                case_results.append(result)
                failed_cases.append(
                    {
                        "case_id": case.get("case_id"),
                        "label": case.get("label"),
                        "reason": "route_error",
                    }
                )
                continue

            payload = response.get_json(silent=True) or {}
            profile = payload.get("data") or {}
            traits = profile.get("traits") or []
            summary_traits = profile.get("summary_traits") or []
            trait_count = len(traits)
            summary_trait_count = len(summary_traits)
            passed = trait_count >= min_trait_count and summary_trait_count >= min_summary_trait_count
            result = {
                **base_result,
                "passed": passed,
                "trait_count": trait_count,
                "summary_trait_count": summary_trait_count,
                "summary": profile.get("summary") or {},
                "top_traits": _top_summary_traits(profile),
            }
            case_results.append(result)
            if not passed:
                failed_cases.append(
                    {
                        "case_id": case.get("case_id"),
                        "label": case.get("label"),
                        "reason": "insufficient_profile_output",
                        "trait_count": trait_count,
                        "summary_trait_count": summary_trait_count,
                    }
                )
    finally:
        if hasattr(astro_clock_api, "_engine"):
            astro_clock_api._engine = previous_engine
        if hasattr(astro_clock_api, "_traits_engine"):
            astro_clock_api._traits_engine = previous_traits_engine

    elapsed_ms = int(round((time.perf_counter() - started) * 1000))
    group_counts: Dict[str, int] = {}
    for case in case_results:
        group = str(case.get("benchmark_group") or "unknown")
        group_counts[group] = group_counts.get(group, 0) + 1
    return {
        "suite": "trait_public_figure_baseline_aa_a",
        "case_count": len(case_results),
        "source_case_count": len(all_cases),
        "group_counts": group_counts,
        "passed_case_count": sum(1 for case in case_results if case.get("passed")),
        "failed_case_count": len(failed_cases),
        "passed": not failed_cases,
        "min_trait_count": min_trait_count,
        "min_summary_trait_count": min_summary_trait_count,
        "elapsed_ms": elapsed_ms,
        "failed_cases": failed_cases,
        "cases": case_results,
    }


def run_trait_public_figure_biography_benchmark(
    case_ids: Optional[Iterable[str]] = None,
    *,
    app: Optional[Flask] = None,
) -> Dict[str, Any]:
    selected = set(str(case_id) for case_id in (case_ids or []) if str(case_id))
    all_cases = get_trait_public_figure_baseline_cases()
    cases = [
        case
        for case in all_cases
        if not selected or str(case.get("case_id")) in selected
    ]
    if selected and len(cases) != len(selected):
        known = {str(case.get("case_id")) for case in all_cases}
        missing = sorted(selected - known)
        raise ValueError(f"Unknown public-figure biography benchmark case ids: {', '.join(missing)}")

    missing_expectations = [
        str(case.get("case_id"))
        for case in cases
        if not case.get("expected_clusters") or not case.get("biography_sources")
    ]
    if missing_expectations:
        raise ValueError(
            "Missing biography expectations for public-figure cases: "
            + ", ".join(sorted(missing_expectations))
        )

    client = (app or _make_app()).test_client()
    started = time.perf_counter()
    case_results: List[Dict[str, Any]] = []
    failed_clusters: List[Dict[str, Any]] = []
    cluster_total = 0
    cluster_passed = 0
    previous_engine = getattr(astro_clock_api, "_engine", None)
    previous_traits_engine = getattr(astro_clock_api, "_traits_engine", None)

    try:
        for case in cases:
            params = _case_query_params(case)
            elapsed_start = time.perf_counter()
            response = client.get("/api/astro-clock/traits/profile", query_string=params)
            elapsed_ms = int(round((time.perf_counter() - elapsed_start) * 1000))
            birth = case.get("birth") or {}
            base_result: Dict[str, Any] = {
                "case_id": case.get("case_id"),
                "label": case.get("label"),
                "benchmark_group": case.get("benchmark_group"),
                "role_target": case.get("role_target"),
                "rating": birth.get("source_rating"),
                "birth_source": birth.get("source_url"),
                "birth_source_quality": birth.get("source_quality"),
                "biography_sources": case.get("biography_sources") or [],
                "source_local_time": birth.get("source_local_time"),
                "elapsed_ms": elapsed_ms,
            }
            if response.status_code != 200:
                result = {
                    **base_result,
                    "passed": False,
                    "error": response.get_data(as_text=True)[:500],
                    "top_traits": [],
                    "clusters": [],
                }
                case_results.append(result)
                failed_clusters.append(
                    {
                        "case_id": case.get("case_id"),
                        "cluster_id": "route_error",
                        "label": case.get("label"),
                    }
                )
                continue

            payload = response.get_json(silent=True) or {}
            profile = payload.get("data") or {}
            trait_by_id, summary_rank = _rank_maps(profile)
            clusters = [
                _evaluate_biographical_cluster(cluster, trait_by_id, summary_rank)
                for cluster in case.get("expected_clusters") or []
            ]
            cluster_total += len(clusters)
            cluster_passed += sum(1 for cluster in clusters if cluster.get("passed"))
            for cluster in clusters:
                if not cluster.get("passed"):
                    failed_clusters.append(
                        {
                            "case_id": case.get("case_id"),
                            "cluster_id": cluster.get("cluster_id"),
                            "label": cluster.get("label"),
                            "failure_kind": cluster.get("failure_kind"),
                            "pass_rule": cluster.get("pass_rule"),
                        }
                    )
            case_results.append(
                {
                    **base_result,
                    "passed": all(cluster.get("passed") for cluster in clusters),
                    "summary": profile.get("summary") or {},
                    "top_traits": _top_summary_traits(profile, limit=10),
                    "clusters": clusters,
                }
            )
    finally:
        if hasattr(astro_clock_api, "_engine"):
            astro_clock_api._engine = previous_engine
        if hasattr(astro_clock_api, "_traits_engine"):
            astro_clock_api._traits_engine = previous_traits_engine

    elapsed_ms = int(round((time.perf_counter() - started) * 1000))
    return {
        "suite": "trait_public_figure_biography_correctness_aa_a",
        "case_count": len(case_results),
        "source_case_count": len(all_cases),
        "cluster_count": cluster_total,
        "passed_cluster_count": cluster_passed,
        "failed_cluster_count": len(failed_clusters),
        "passed_case_count": sum(1 for case in case_results if case.get("passed")),
        "failed_case_count": sum(1 for case in case_results if not case.get("passed")),
        "passed": not failed_clusters,
        "elapsed_ms": elapsed_ms,
        "failed_clusters": failed_clusters,
        "failure_kind_counts": _failure_kind_counts(failed_clusters),
        "cases": case_results,
    }


def run_trait_criminal_figure_biography_benchmark(
    case_ids: Optional[Iterable[str]] = None,
    *,
    app: Optional[Flask] = None,
) -> Dict[str, Any]:
    selected = set(str(case_id) for case_id in (case_ids or []) if str(case_id))
    all_cases = get_trait_criminal_figure_baseline_cases()
    cases = [
        case
        for case in all_cases
        if not selected or str(case.get("case_id")) in selected
    ]
    if selected and len(cases) != len(selected):
        known = {str(case.get("case_id")) for case in all_cases}
        missing = sorted(selected - known)
        raise ValueError(f"Unknown criminal biography benchmark case ids: {', '.join(missing)}")

    missing_expectations = [
        str(case.get("case_id"))
        for case in cases
        if not case.get("expected_clusters") or not case.get("biography_sources")
    ]
    if missing_expectations:
        raise ValueError(
            "Missing biography expectations for criminal-figure cases: "
            + ", ".join(sorted(missing_expectations))
        )

    client = (app or _make_app()).test_client()
    started = time.perf_counter()
    case_results: List[Dict[str, Any]] = []
    failed_clusters: List[Dict[str, Any]] = []
    cluster_total = 0
    cluster_passed = 0
    previous_engine = getattr(astro_clock_api, "_engine", None)
    previous_traits_engine = getattr(astro_clock_api, "_traits_engine", None)

    try:
        for case in cases:
            params = _case_query_params(case)
            elapsed_start = time.perf_counter()
            response = client.get("/api/astro-clock/traits/profile", query_string=params)
            elapsed_ms = int(round((time.perf_counter() - elapsed_start) * 1000))
            birth = case.get("birth") or {}
            base_result: Dict[str, Any] = {
                "case_id": case.get("case_id"),
                "label": case.get("label"),
                "benchmark_group": case.get("benchmark_group"),
                "role_target": case.get("role_target"),
                "rating": birth.get("source_rating"),
                "birth_source": birth.get("source_url"),
                "birth_source_quality": birth.get("source_quality"),
                "biography_sources": case.get("biography_sources") or [],
                "source_local_time": birth.get("source_local_time"),
                "elapsed_ms": elapsed_ms,
            }
            if response.status_code != 200:
                result = {
                    **base_result,
                    "passed": False,
                    "error": response.get_data(as_text=True)[:500],
                    "top_traits": [],
                    "clusters": [],
                }
                case_results.append(result)
                failed_clusters.append(
                    {
                        "case_id": case.get("case_id"),
                        "cluster_id": "route_error",
                        "label": case.get("label"),
                    }
                )
                continue

            payload = response.get_json(silent=True) or {}
            profile = payload.get("data") or {}
            trait_by_id, summary_rank = _rank_maps(profile)
            clusters = [
                _evaluate_biographical_cluster(cluster, trait_by_id, summary_rank)
                for cluster in case.get("expected_clusters") or []
            ]
            cluster_total += len(clusters)
            cluster_passed += sum(1 for cluster in clusters if cluster.get("passed"))
            for cluster in clusters:
                if not cluster.get("passed"):
                    failed_clusters.append(
                        {
                            "case_id": case.get("case_id"),
                            "cluster_id": cluster.get("cluster_id"),
                            "label": cluster.get("label"),
                            "failure_kind": cluster.get("failure_kind"),
                            "pass_rule": cluster.get("pass_rule"),
                        }
                    )
            case_results.append(
                {
                    **base_result,
                    "passed": all(cluster.get("passed") for cluster in clusters),
                    "summary": profile.get("summary") or {},
                    "top_traits": _top_summary_traits(profile, limit=10),
                    "clusters": clusters,
                }
            )
    finally:
        if hasattr(astro_clock_api, "_engine"):
            astro_clock_api._engine = previous_engine
        if hasattr(astro_clock_api, "_traits_engine"):
            astro_clock_api._traits_engine = previous_traits_engine

    elapsed_ms = int(round((time.perf_counter() - started) * 1000))
    return {
        "suite": "trait_criminal_figure_biography_correctness_aa_a",
        "case_count": len(case_results),
        "source_case_count": len(all_cases),
        "cluster_count": cluster_total,
        "passed_cluster_count": cluster_passed,
        "failed_cluster_count": len(failed_clusters),
        "passed_case_count": sum(1 for case in case_results if case.get("passed")),
        "failed_case_count": sum(1 for case in case_results if not case.get("passed")),
        "passed": not failed_clusters,
        "elapsed_ms": elapsed_ms,
        "failed_clusters": failed_clusters,
        "failure_kind_counts": _failure_kind_counts(failed_clusters),
        "cases": case_results,
    }


def _failure_kind_counts(failed_clusters: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for failure in failed_clusters:
        kind = str(failure.get("failure_kind") or "unknown")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def render_markdown_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Trait Logic Benchmark Report")
    lines.append("")
    lines.append(f"- Suite: `{report.get('suite')}`")
    lines.append(f"- Cases: {int(report.get('case_count') or 0)}")
    lines.append(
        f"- Clusters passed: {int(report.get('passed_cluster_count') or 0)}/"
        f"{int(report.get('cluster_count') or 0)}"
    )
    lines.append(f"- Elapsed: {int(report.get('elapsed_ms') or 0)} ms")
    lines.append(f"- Result: {'PASS' if report.get('passed') else 'FAIL'}")
    lines.append("")
    for case in report.get("cases") or []:
        status = "PASS" if case.get("passed") else "FAIL"
        lines.append(f"## {status} {case.get('label') or case.get('case_id')}")
        lines.append("")
        if case.get("error"):
            lines.append(f"- Error: `{case.get('error')}`")
            lines.append("")
            continue
        summary = case.get("summary") or {}
        lines.append(f"- Dominant element: `{summary.get('dominant_element')}`")
        lines.append(f"- Dominant modality: `{summary.get('dominant_modality')}`")
        if case.get("case_type") == "house_determination":
            lines.append("- Source basis: " + "; ".join(case.get("source_basis") or []))
        else:
            lines.append(f"- Birth source: {case.get('birth_source')} ({case.get('birth_source_quality')})")
            lines.append("- Biography sources: " + ", ".join(case.get("biography_sources") or []))
        for cluster in case.get("clusters") or []:
            best = cluster.get("best_trait") or {}
            best_label = (
                f"`{best.get('id')}` score {best.get('score')} "
                f"rank {best.get('summary_rank') or 'n/a'}"
                if best
                else "no matching trait"
            )
            lines.append(
                f"- {'PASS' if cluster.get('passed') else 'FAIL'} `{cluster.get('cluster_id')}`: {best_label}"
            )
            if cluster.get("required_evidence"):
                lines.append(
                    "  Evidence: "
                    + f"{len(cluster.get('evidence_hits') or [])}/{len(cluster.get('required_evidence') or [])} "
                    + ", ".join(cluster.get("required_evidence") or [])
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_public_figure_baseline_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Trait Public Figure Baseline Report")
    lines.append("")
    lines.append(f"- Suite: `{report.get('suite')}`")
    lines.append(f"- Cases: {int(report.get('case_count') or 0)}")
    group_counts = report.get("group_counts") or {}
    if group_counts:
        lines.append(
            "- Groups: "
            + ", ".join(f"`{key}` {value}" for key, value in sorted(group_counts.items()))
        )
    lines.append(
        f"- Cases passed: {int(report.get('passed_case_count') or 0)}/"
        f"{int(report.get('case_count') or 0)}"
    )
    lines.append(f"- Minimum traits: {int(report.get('min_trait_count') or 0)}")
    lines.append(f"- Minimum summary traits: {int(report.get('min_summary_trait_count') or 0)}")
    lines.append(f"- Elapsed: {int(report.get('elapsed_ms') or 0)} ms")
    lines.append(f"- Result: {'PASS' if report.get('passed') else 'FAIL'}")
    lines.append("")
    failed_cases = report.get("failed_cases") or []
    if failed_cases:
        lines.append("## Failed Cases")
        lines.append("")
        for item in failed_cases:
            lines.append(
                f"- `{item.get('case_id')}` {item.get('label')}: {item.get('reason')}"
            )
        lines.append("")
    lines.append("## Case Results")
    lines.append("")
    for case in report.get("cases") or []:
        status = "PASS" if case.get("passed") else "FAIL"
        top_traits = ", ".join(
            f"`{trait.get('id')}` {trait.get('score')}"
            for trait in case.get("top_traits") or []
        )
        if not top_traits:
            top_traits = "no summary traits"
        lines.append(
            f"- {status} `{case.get('case_id')}` {case.get('label')} "
            f"({case.get('rating')}, {case.get('benchmark_group')}): {top_traits}"
        )
    return "\n".join(lines).rstrip() + "\n"


def render_public_figure_biography_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Trait Public Figure Biography Correctness Report")
    lines.append("")
    lines.append(f"- Suite: `{report.get('suite')}`")
    lines.append(f"- Cases: {int(report.get('case_count') or 0)}")
    lines.append(
        f"- Cases passed: {int(report.get('passed_case_count') or 0)}/"
        f"{int(report.get('case_count') or 0)}"
    )
    lines.append(
        f"- Clusters passed: {int(report.get('passed_cluster_count') or 0)}/"
        f"{int(report.get('cluster_count') or 0)}"
    )
    lines.append(f"- Elapsed: {int(report.get('elapsed_ms') or 0)} ms")
    lines.append(f"- Result: {'PASS' if report.get('passed') else 'FAIL'}")
    lines.append("")
    failed_clusters = report.get("failed_clusters") or []
    if failed_clusters:
        failure_kind_counts = report.get("failure_kind_counts") or {}
        if failure_kind_counts:
            lines.append("## Failure Types")
            lines.append("")
            for kind, count in sorted(failure_kind_counts.items()):
                lines.append(f"- `{kind}`: {count}")
            lines.append("")
        lines.append("## Failed Clusters")
        lines.append("")
        for item in failed_clusters:
            lines.append(
                f"- `{item.get('case_id')}` `{item.get('cluster_id')}`: "
                f"{item.get('label')} "
                f"[{item.get('failure_kind') or 'unknown'}] "
                f"({item.get('pass_rule') or 'route error'})"
            )
        lines.append("")
    lines.append("## Case Results")
    lines.append("")
    for case in report.get("cases") or []:
        status = "PASS" if case.get("passed") else "FAIL"
        lines.append(f"### {status} {case.get('label')} (`{case.get('case_id')}`)")
        lines.append("")
        if case.get("error"):
            lines.append(f"- Error: `{case.get('error')}`")
            lines.append("")
            continue
        lines.append(f"- Role target: {case.get('role_target')}")
        lines.append(f"- Birth source: {case.get('birth_source')} ({case.get('birth_source_quality')})")
        lines.append("- Biography sources: " + ", ".join(case.get("biography_sources") or []))
        top_traits = ", ".join(
            f"`{trait.get('id')}` {trait.get('score')}"
            for trait in case.get("top_traits") or []
        )
        lines.append(f"- Top traits: {top_traits or 'no summary traits'}")
        for cluster in case.get("clusters") or []:
            best_top = cluster.get("best_top_trait") or {}
            if best_top:
                best_text = (
                    f"`{best_top.get('id')}` score {best_top.get('score')} "
                    f"rank {best_top.get('summary_rank')}"
                )
            else:
                best = cluster.get("best_trait") or {}
                best_text = (
                    f"best available `{best.get('id')}` score {best.get('score')} "
                    f"rank {best.get('summary_rank') or 'n/a'}"
                    if best
                    else "no matching trait present"
                )
            lines.append(
                f"- {'PASS' if cluster.get('passed') else 'FAIL'} `{cluster.get('cluster_id')}`: "
                f"{best_text}; {cluster.get('pass_rule')}"
            )
            lines.append(f"  Rationale: {cluster.get('rationale')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_criminal_figure_biography_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Trait Criminal-Figure Biography Correctness Report")
    lines.append("")
    lines.append(f"- Suite: `{report.get('suite')}`")
    lines.append(f"- Cases: {int(report.get('case_count') or 0)}")
    lines.append(
        f"- Cases passed: {int(report.get('passed_case_count') or 0)}/"
        f"{int(report.get('case_count') or 0)}"
    )
    lines.append(
        f"- Clusters passed: {int(report.get('passed_cluster_count') or 0)}/"
        f"{int(report.get('cluster_count') or 0)}"
    )
    lines.append(f"- Elapsed: {int(report.get('elapsed_ms') or 0)} ms")
    lines.append(f"- Result: {'PASS' if report.get('passed') else 'FAIL'}")
    lines.append("")
    lines.append(
        "This benchmark checks whether chart-derived top traits align with documented criminal-case biographies. "
        "It is not a criminality detector and must not be used to infer guilt, risk, or diagnosis."
    )
    lines.append("")
    failed_clusters = report.get("failed_clusters") or []
    if failed_clusters:
        failure_kind_counts = report.get("failure_kind_counts") or {}
        if failure_kind_counts:
            lines.append("## Failure Types")
            lines.append("")
            for kind, count in sorted(failure_kind_counts.items()):
                lines.append(f"- `{kind}`: {count}")
            lines.append("")
        lines.append("## Failed Clusters")
        lines.append("")
        for item in failed_clusters:
            lines.append(
                f"- `{item.get('case_id')}` `{item.get('cluster_id')}`: "
                f"{item.get('label')} "
                f"[{item.get('failure_kind') or 'unknown'}] "
                f"({item.get('pass_rule') or 'route error'})"
            )
        lines.append("")
    lines.append("## Case Results")
    lines.append("")
    for case in report.get("cases") or []:
        status = "PASS" if case.get("passed") else "FAIL"
        lines.append(f"### {status} {case.get('label')} (`{case.get('case_id')}`)")
        lines.append("")
        if case.get("error"):
            lines.append(f"- Error: `{case.get('error')}`")
            lines.append("")
            continue
        lines.append(f"- Role target: {case.get('role_target')}")
        lines.append(f"- Birth source: {case.get('birth_source')} ({case.get('birth_source_quality')})")
        lines.append("- Biography sources: " + ", ".join(case.get("biography_sources") or []))
        top_traits = ", ".join(
            f"`{trait.get('id')}` {trait.get('score')}"
            for trait in case.get("top_traits") or []
        )
        lines.append(f"- Top traits: {top_traits or 'no summary traits'}")
        for cluster in case.get("clusters") or []:
            best_top = cluster.get("best_top_trait") or {}
            if best_top:
                best_text = (
                    f"`{best_top.get('id')}` score {best_top.get('score')} "
                    f"rank {best_top.get('summary_rank')}"
                )
            else:
                best = cluster.get("best_trait") or {}
                best_text = (
                    f"best available `{best.get('id')}` score {best.get('score')} "
                    f"rank {best.get('summary_rank') or 'n/a'}"
                    if best
                    else "no matching trait present"
                )
            lines.append(
                f"- {'PASS' if cluster.get('passed') else 'FAIL'} `{cluster.get('cluster_id')}`: "
                f"{best_text}; {cluster.get('pass_rule')}"
            )
            lines.append(f"  Rationale: {cluster.get('rationale')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run trait logic benchmarks.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--case-id", action="append", default=[], help="Run one case id. Repeat for multiple cases.")
    parser.add_argument(
        "--suite",
        choices=["logic", "public-figures", "public-figures-bio", "criminals-bio"],
        default="logic",
        help="Benchmark suite to run.",
    )
    parser.add_argument("--output", type=Path, help="Optional report output path.")
    args = parser.parse_args(argv)

    if args.suite == "public-figures":
        report = run_trait_public_figure_baseline_benchmark(args.case_id or None)
        rendered = (
            json.dumps(report, indent=2, sort_keys=True)
            if args.json
            else render_public_figure_baseline_report(report)
        )
    elif args.suite == "public-figures-bio":
        report = run_trait_public_figure_biography_benchmark(args.case_id or None)
        rendered = (
            json.dumps(report, indent=2, sort_keys=True)
            if args.json
            else render_public_figure_biography_report(report)
        )
    elif args.suite == "criminals-bio":
        report = run_trait_criminal_figure_biography_benchmark(args.case_id or None)
        rendered = (
            json.dumps(report, indent=2, sort_keys=True)
            if args.json
            else render_criminal_figure_biography_report(report)
        )
    else:
        report = run_trait_logic_benchmark_suite(args.case_id or None)
        rendered = (
            json.dumps(report, indent=2, sort_keys=True)
            if args.json
            else render_markdown_report(report)
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.json:
        print(rendered)
    else:
        print(rendered)
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
