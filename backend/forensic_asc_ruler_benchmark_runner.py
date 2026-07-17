#!/usr/bin/env python3
"""
Benchmark the forensic ASC-ruler house placement signal.

This runner treats the McIntosh ASC-ruler placement as a single explanatory
signal and validates whether its risk tone supports already curated placement,
setting, contact, motive, or disappearance-context axes. It deliberately keeps
any weighted context scoring behind explicit support, contradiction, and
null-control gates.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from forensic_statistical_benchmark_runner import (
    DEFAULT_DATASET_PATHS,
    REPO_ROOT,
    _call_forensic_route,
    compute_null_significance,
    load_statistical_cases,
)


DEFAULT_ASC_FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_asc_ruler_placement_cases.json"

DEFAULT_PROMOTION_THRESHOLDS = {
    "min_case_count": 12,
    "support_rate": 0.60,
    "contradiction_rate_max": 0.10,
    "support_p_value_max": 0.10,
}

ASC_RULER_TONE_AXES: Dict[str, Set[str]] = {
    "hidden": {"abduction_missing_person", "deception_coverup"},
    "fatal_pressure": {"violence_homicide"},
    "route": {"route_vehicle_transport"},
    "distance": {"route_vehicle_transport", "abduction_missing_person"},
    "material": {"trafficking_or_possession_context"},
    "social": {"friend_or_close_associate", "accomplice_or_witness"},
    "associate": {"friend_or_close_associate"},
    "access": {"domestic_partner_involvement", "friend_or_close_associate", "abduction_missing_person"},
    "public": {"authority_or_public_case", "accomplice_or_witness"},
    "perpetrator_contact": {"domestic_partner_involvement", "friend_or_close_associate", "violence_homicide"},
    "mixed": set(),
}

ASC_RULER_HOUSE_DOCTRINE_AXES: Dict[int, str] = {
    1: "immediate_scene_or_vicinity_context",
    2: "trafficking_or_possession_context",
    3: "communication_vehicle_short_distance_context",
    4: "family_home_end_matter_context",
    5: "party_entertainment_context",
    6: "routine_disruption_stalker_context",
    7: "suspect_territory_context",
    8: "death_financial_entanglement_context",
    9: "far_distance_departure_context",
    10: "public_authority_witness_context",
    11: "friends_social_circle_context",
    12: "hidden_captive_kidnapped_context",
}


def _round4(value: Optional[float]) -> Optional[float]:
    return round(value, 4) if value is not None else None


def _normalize_axis_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    result: List[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result


def _normalize_thresholds(raw: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    thresholds = dict(DEFAULT_PROMOTION_THRESHOLDS)
    if isinstance(raw, dict):
        for key in thresholds:
            if key in raw:
                try:
                    thresholds[key] = float(raw[key])
                except Exception:
                    pass
    return thresholds


def _placement_tone(placement: Dict[str, Any]) -> str:
    return str(placement.get("risk_tone") or "unknown").strip() or "unknown"


def derive_asc_ruler_axes(placement: Dict[str, Any]) -> List[str]:
    tone = _placement_tone(placement)
    return sorted(ASC_RULER_TONE_AXES.get(tone, set()))


def derive_asc_ruler_source_doctrine_axes(placement: Dict[str, Any]) -> List[str]:
    try:
        house = int(placement.get("house"))
    except Exception:
        return []
    axis = ASC_RULER_HOUSE_DOCTRINE_AXES.get(house)
    return [axis] if axis else []


def _row_counts(row: Dict[str, Any]) -> Dict[str, Any]:
    expected = set(_normalize_axis_list(row.get("expected_axes")))
    contradictory = set(_normalize_axis_list(row.get("contradictory_axes")))
    derived = set(_normalize_axis_list(row.get("derived_axes")))
    supported = sorted(axis for axis in derived if axis in expected)
    contradicted = sorted(axis for axis in derived if axis in contradictory)
    if contradicted:
        status = "contradicted"
    elif supported:
        status = "supported"
    else:
        status = "unsupported"
    return {
        "supported_axes": supported,
        "contradicted_axes": contradicted,
        "status": status,
    }


def _promotion_recommended(
    metrics: Dict[str, Any],
    thresholds: Dict[str, float],
    significance: Optional[Dict[str, Any]] = None,
) -> bool:
    if (metrics.get("case_count") or 0) < int(thresholds["min_case_count"]):
        return False
    if (metrics.get("support_rate") or 0.0) < thresholds["support_rate"]:
        return False
    if (metrics.get("contradiction_rate") or 0.0) > thresholds["contradiction_rate_max"]:
        return False
    if significance and significance.get("empirical_p_value") is not None:
        return float(significance["empirical_p_value"]) <= thresholds["support_p_value_max"]
    return True


def compute_asc_ruler_metrics(
    rows: Sequence[Dict[str, Any]],
    *,
    promotion_thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    thresholds = _normalize_thresholds(promotion_thresholds)
    case_count = len(rows)
    status_counter: Counter[str] = Counter()
    tone_counter: Counter[str] = Counter()
    per_tone: Dict[str, Dict[str, int]] = defaultdict(lambda: {"case_count": 0, "supported": 0, "contradicted": 0})
    supported_axis_counter: Counter[str] = Counter()
    contradicted_axis_counter: Counter[str] = Counter()
    evaluated_rows: List[Dict[str, Any]] = []

    for row in rows:
        placement = row.get("asc_ruler_placement") if isinstance(row.get("asc_ruler_placement"), dict) else {}
        derived_axes = _normalize_axis_list(row.get("derived_axes")) or derive_asc_ruler_axes(placement)
        evaluated = {**row, "derived_axes": derived_axes}
        counts = _row_counts(evaluated)
        tone = _placement_tone(placement)
        status_counter[counts["status"]] += 1
        tone_counter[tone] += 1
        per_tone[tone]["case_count"] += 1
        if counts["supported_axes"]:
            per_tone[tone]["supported"] += 1
            supported_axis_counter.update(counts["supported_axes"])
        if counts["contradicted_axes"]:
            per_tone[tone]["contradicted"] += 1
            contradicted_axis_counter.update(counts["contradicted_axes"])
        evaluated_rows.append({**evaluated, **counts})

    supported = status_counter.get("supported", 0)
    contradicted = status_counter.get("contradicted", 0)
    unsupported = status_counter.get("unsupported", 0)
    per_tone_payload: Dict[str, Dict[str, Any]] = {}
    for tone, counts in sorted(per_tone.items()):
        tone_cases = counts["case_count"]
        per_tone_payload[tone] = {
            **counts,
            "support_rate": _round4(counts["supported"] / tone_cases) if tone_cases else None,
            "contradiction_rate": _round4(counts["contradicted"] / tone_cases) if tone_cases else None,
        }

    support_rate = supported / case_count if case_count else None
    contradiction_rate = contradicted / case_count if case_count else None
    score = (support_rate or 0.0) - (contradiction_rate or 0.0)
    metrics = {
        "case_count": case_count,
        "supported_case_count": supported,
        "unsupported_case_count": unsupported,
        "contradicted_case_count": contradicted,
        "support_rate": _round4(support_rate),
        "contradiction_rate": _round4(contradiction_rate),
        "context_support_score": _round4(score),
        "placement_signal_score": _round4(score),
        "status_counts": dict(sorted(status_counter.items())),
        "tone_counts": dict(sorted(tone_counter.items())),
        "supported_axes": dict(sorted(supported_axis_counter.items())),
        "contradicted_axes": dict(sorted(contradicted_axis_counter.items())),
        "per_tone": per_tone_payload,
        "promotion_thresholds": thresholds,
    }
    metrics["promotion_recommended"] = _promotion_recommended(metrics, thresholds)
    return metrics


def _load_asc_fixture(path: str | Path) -> Dict[str, Any]:
    fixture_path = Path(path)
    if not fixture_path.is_absolute():
        fixture_path = REPO_ROOT / fixture_path
    if not fixture_path.exists():
        raise FileNotFoundError(f"ASC-ruler benchmark fixture not found: {fixture_path}")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"ASC-ruler benchmark fixture must be a JSON object: {fixture_path}")
    return payload


def _selected_case_ids(fixture: Dict[str, Any], case_limit: Optional[int]) -> List[str]:
    selected: List[str] = []
    for item in fixture.get("cases") or []:
        if not isinstance(item, dict):
            continue
        case_id = str(item.get("case_id") or "").strip()
        if case_id and case_id not in selected:
            selected.append(case_id)
    if case_limit is not None:
        selected = selected[: max(0, int(case_limit))]
    return selected


def _fixture_case_map(fixture: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in fixture.get("cases") or []:
        if isinstance(item, dict) and item.get("case_id"):
            result[str(item["case_id"])] = item
    return result


def _source_doctrine_results(fixture: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for item in fixture.get("source_doctrine_cases") or []:
        if not isinstance(item, dict):
            continue
        case_id = str(item.get("case_id") or "").strip()
        placement = item.get("asc_ruler_placement") if isinstance(item.get("asc_ruler_placement"), dict) else {}
        if not case_id or not placement:
            continue
        row = {
            "case_id": case_id,
            "source_note": item.get("source_note") or "",
            "expected_axes": _normalize_axis_list(item.get("expected_context_axes")),
            "contradictory_axes": _normalize_axis_list(item.get("contradictory_context_axes")),
            "asc_ruler_placement": placement,
            "derived_axes": derive_asc_ruler_source_doctrine_axes(placement),
        }
        results.append({**row, **_row_counts(row)})
    return results


def _permutation_support_controls(rows: Sequence[Dict[str, Any]], *, max_controls: int) -> List[float]:
    if len(rows) <= 1:
        return []
    controls: List[float] = []
    shift_count = min(len(rows) - 1, max(0, int(max_controls)))
    for shift in range(1, shift_count + 1):
        shifted: List[Dict[str, Any]] = []
        for index, row in enumerate(rows):
            donor = rows[(index + shift) % len(rows)]
            shifted.append(
                {
                    "case_id": row.get("case_id"),
                    "expected_axes": row.get("expected_axes") or [],
                    "contradictory_axes": row.get("contradictory_axes") or [],
                    "asc_ruler_placement": donor.get("asc_ruler_placement") or {},
                    "derived_axes": donor.get("derived_axes") or [],
                }
            )
        value = compute_asc_ruler_metrics(shifted).get("support_rate")
        if value is not None:
            controls.append(float(value))
    return controls


def _promotion_decision(metrics: Dict[str, Any]) -> Dict[str, Any]:
    if metrics.get("promotion_recommended"):
        return {
            "decision": "promote_bounded_context_scoring_candidate",
            "reason": "Support rate, contradiction rate, and available null-control checks cleared the configured placement/reason context gates.",
        }
    return {
        "decision": "keep_descriptive_only",
        "reason": "ASC-ruler placement remains useful as a victim-placement/reason context signal, but benchmark gates did not clear enough evidence for adding a weighted context score.",
    }


def run_asc_ruler_benchmark_suite(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    asc_fixture_path: str | Path = DEFAULT_ASC_FIXTURE_PATH,
    case_limit: Optional[int] = None,
    house_system_code: Optional[str] = None,
    use_secondary_factors: bool = False,
    include_control_cases: bool = True,
    control_iterations: int = 100,
) -> Dict[str, Any]:
    fixture = _load_asc_fixture(asc_fixture_path)
    fixture_cases = _fixture_case_map(fixture)
    selected_ids = _selected_case_ids(fixture, case_limit)
    statistical_cases = {item["case_id"]: item for item in load_statistical_cases(dataset_paths or DEFAULT_DATASET_PATHS)}
    thresholds = _normalize_thresholds(fixture.get("promotion_thresholds"))
    house_system_override = str(house_system_code).strip().upper() if house_system_code else None

    case_results: List[Dict[str, Any]] = []
    route_errors: List[Dict[str, Any]] = []

    for case_id in selected_ids:
        item = statistical_cases.get(case_id)
        fixture_case = fixture_cases.get(case_id) or {}
        if not item:
            route_errors.append(
                {
                    "case_id": case_id,
                    "status_code": "fixture_missing",
                    "error": "Case id is not available in the statistical benchmark corpus.",
                }
            )
            continue

        query = dict(item["query"])
        if house_system_override:
            query["house_system_code"] = house_system_override
        query["secondary_factors"] = "1" if use_secondary_factors else "0"
        route_result = _call_forensic_route(query)
        payload = route_result.get("payload") or {}
        if route_result.get("status_code") != 200 or not payload.get("success"):
            route_errors.append(
                {
                    "case_id": case_id,
                    "status_code": route_result.get("status_code"),
                    "error": payload.get("error"),
                }
            )
            continue

        placement = payload.get("asc_ruler_placement") if isinstance(payload.get("asc_ruler_placement"), dict) else {}
        expected_axes = _normalize_axis_list(fixture_case.get("expected_context_axes")) or list(item["expected_axes"])
        contradictory_axes = _normalize_axis_list(fixture_case.get("contradictory_context_axes")) or list(item["contradictory_axes"])
        derived_axes = derive_asc_ruler_axes(placement)
        row = {
            "case_id": case_id,
            "dataset_name": item["dataset_name"],
            "title": item.get("case", {}).get("title") or item.get("case", {}).get("case_name") or "",
            "curation_note": fixture_case.get("curation_note") or "",
            "expected_axes": expected_axes,
            "contradictory_axes": contradictory_axes,
            "asc_ruler_placement": placement,
            "derived_axes": derived_axes,
        }
        case_results.append({**row, **_row_counts(row)})

    metrics = compute_asc_ruler_metrics(case_results, promotion_thresholds=thresholds)
    doctrine_results = _source_doctrine_results(fixture)
    doctrine_metrics = compute_asc_ruler_metrics(
        doctrine_results,
        promotion_thresholds={
            "min_case_count": 1,
            "support_rate": 1.0,
            "contradiction_rate_max": 0.0,
            "support_p_value_max": 1.0,
        },
    )
    doctrine_metrics["promotion_recommended"] = False
    doctrine_metrics["promotion_applicability"] = "not_applicable_source_doctrine_check"
    control_support_rates = (
        _permutation_support_controls(case_results, max_controls=control_iterations)
        if include_control_cases
        else []
    )
    significance = compute_null_significance(metrics.get("support_rate"), control_support_rates)
    if significance.get("empirical_p_value") is not None:
        metrics["promotion_recommended"] = _promotion_recommended(metrics, thresholds, significance)
    metrics["null_support_significance"] = significance
    metrics["scoring_recommendation"] = _promotion_decision(metrics)

    return {
        "benchmark_id": fixture.get("benchmark_id") or "forensic_asc_ruler_placement_v1",
        "primary_target": "asc_ruler_context_support",
        "dataset_paths": sorted({item["dataset_path"] for item in statistical_cases.values()}),
        "asc_fixture_path": str(Path(asc_fixture_path)),
        "house_system_code": house_system_override,
        "secondary_factors_enabled": bool(use_secondary_factors),
        "case_count": len(selected_ids),
        "evaluated_case_count": len(case_results),
        "source_doctrine_case_count": len(doctrine_results),
        "route_error_count": len(route_errors),
        "route_errors": route_errors,
        "metrics": metrics,
        "source_doctrine_metrics": doctrine_metrics,
        "case_results": case_results,
        "source_doctrine_results": doctrine_results,
    }


def render_markdown_report(report: Dict[str, Any]) -> str:
    metrics = report.get("metrics") or {}
    significance = metrics.get("null_support_significance") or {}
    decision = metrics.get("scoring_recommendation") or {}
    lines: List[str] = []
    lines.append("# ASC-Ruler Placement Benchmark Report")
    lines.append("")
    lines.append(f"- Benchmark ID: `{report.get('benchmark_id')}`")
    lines.append("- Primary target: ASC-ruler placement/reason context support")
    lines.append(f"- Curated cases: {report.get('case_count')}")
    lines.append(f"- Evaluated cases: {report.get('evaluated_case_count')}")
    lines.append(f"- Source doctrine checks: {report.get('source_doctrine_case_count')}")
    lines.append(f"- Route errors: {report.get('route_error_count')}")
    lines.append(f"- Support rate: {metrics.get('supported_case_count')}/{metrics.get('case_count')} = {metrics.get('support_rate')}")
    lines.append(f"- Contradiction rate: {metrics.get('contradicted_case_count')}/{metrics.get('case_count')} = {metrics.get('contradiction_rate')}")
    lines.append(f"- Context-support score: {metrics.get('context_support_score')}")
    lines.append(f"- Null support mean: {significance.get('control_mean')}")
    lines.append(f"- Null support empirical p-value: {significance.get('empirical_p_value')}")
    lines.append(f"- Promotion recommendation: {'yes' if metrics.get('promotion_recommended') else 'no'}")
    lines.append(f"- Scoring decision: `{decision.get('decision')}`")
    lines.append(f"- Reason: {decision.get('reason')}")
    lines.append("")
    lines.append("## Tone Metrics")
    lines.append("")
    lines.append(f"- Tone counts: `{metrics.get('tone_counts')}`")
    lines.append(f"- Supported axes: `{metrics.get('supported_axes')}`")
    lines.append(f"- Contradicted axes: `{metrics.get('contradicted_axes')}`")
    lines.append("")
    route_errors = report.get("route_errors") or []
    if route_errors:
        lines.append("## Route Errors")
        lines.append("")
        for error in route_errors:
            lines.append(f"- `{error.get('case_id')}`: status={error.get('status_code')} error={error.get('error')}")
        lines.append("")
    doctrine_results = report.get("source_doctrine_results") or []
    if doctrine_results:
        doctrine_metrics = report.get("source_doctrine_metrics") or {}
        lines.append("## Source Doctrine Checks")
        lines.append("")
        lines.append(
            f"- Support rate: {doctrine_metrics.get('supported_case_count')}/"
            f"{doctrine_metrics.get('case_count')} = {doctrine_metrics.get('support_rate')}"
        )
        for result in doctrine_results:
            placement = result.get("asc_ruler_placement") or {}
            lines.append(
                f"- `{result.get('case_id')}`: {result.get('status')}; "
                f"H{placement.get('house')} {placement.get('risk_tone')}; "
                f"derived={result.get('derived_axes')}; "
                f"supported={result.get('supported_axes')}"
            )
        lines.append("")
    lines.append("## Cases")
    lines.append("")
    for result in report.get("case_results") or []:
        placement = result.get("asc_ruler_placement") or {}
        lines.append(
            f"- `{result.get('case_id')}`: {result.get('status')}; "
            f"H{placement.get('house')} {placement.get('risk_tone')}; "
            f"derived={result.get('derived_axes')}; "
            f"supported={result.get('supported_axes')}; "
            f"contradicted={result.get('contradicted_axes')}"
        )
    return "\n".join(lines).strip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ASC-ruler placement forensic benchmark.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--asc-fixture", default=str(DEFAULT_ASC_FIXTURE_PATH), help="ASC-ruler benchmark fixture path.")
    parser.add_argument("--case-limit", type=int, help="Run only the first N curated cases.")
    parser.add_argument("--dataset", action="append", help="Statistical dataset path. May be repeated.")
    parser.add_argument("--house-system-code", help="Override fixture house systems for sensitivity scans.")
    parser.add_argument("--secondary-factors", action="store_true", help="Enable asteroid/special-degree secondary factors.")
    parser.add_argument("--no-controls", action="store_true", help="Skip permutation null controls.")
    parser.add_argument("--control-iterations", type=int, default=100, help="Maximum permutation null-control rotations.")
    args = parser.parse_args(argv)

    report = run_asc_ruler_benchmark_suite(
        args.dataset,
        asc_fixture_path=args.asc_fixture,
        case_limit=args.case_limit,
        house_system_code=args.house_system_code,
        use_secondary_factors=args.secondary_factors,
        include_control_cases=not args.no_controls,
        control_iterations=args.control_iterations,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown_report(report))
    return 1 if report.get("route_error_count") else 0


if __name__ == "__main__":
    raise SystemExit(main())
