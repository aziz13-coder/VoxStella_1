from __future__ import annotations

import argparse
import json
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

from astro_clock_api import _weather_bundle_resolver
from mundane_models import ActiveClockContext
from validate_weather_benchmark_datasets import (
    PREDICTIVE_CASE_ORIGINS,
    PREDICTIVE_HINDCAST_FILE,
    load_jsonl_cases,
    validate_predictive_hindcast_case,
)
from weather_scan_service import build_weather_scan_request, run_weather_scan


EPSILON = 1e-6


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _parse_datetime(value: Any) -> datetime:
    return datetime.fromisoformat(str(value or "").strip().replace("Z", "+00:00"))


def _normalize_case_origin(value: Any) -> str:
    normalized = str(value or "source_backed").strip().lower()
    return normalized if normalized in PREDICTIVE_CASE_ORIGINS else "source_backed"


def _window_contains(window: Dict[str, Any], dt_iso: str) -> bool:
    current = _parse_datetime(dt_iso)
    return _parse_datetime(window["start_datetime"]) <= current <= _parse_datetime(window["end_datetime"])


def _window_distance_hours(
    peak_start: str,
    peak_end: str,
    target_start: str,
    target_end: str,
) -> float:
    peak_start_dt = _parse_datetime(peak_start)
    peak_end_dt = _parse_datetime(peak_end)
    target_start_dt = _parse_datetime(target_start)
    target_end_dt = _parse_datetime(target_end)
    if peak_start_dt <= target_end_dt and peak_end_dt >= target_start_dt:
        return 0.0
    if peak_end_dt < target_start_dt:
        return round((target_start_dt - peak_end_dt).total_seconds() / 3600.0, 3)
    return round((peak_start_dt - target_end_dt).total_seconds() / 3600.0, 3)


def load_predictive_cases(
    *,
    case_id: Optional[str] = None,
    family_id: Optional[str] = None,
    case_origin: Optional[str] = None,
    include_disabled: bool = False,
) -> List[Dict[str, Any]]:
    path = Path(PREDICTIVE_HINDCAST_FILE).resolve()
    cases: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()
    family_filter = _normalize_text(family_id).lower()
    origin_filter = _normalize_case_origin(case_origin) if case_origin not in (None, "") else ""
    for payload in load_jsonl_cases(path):
        validate_predictive_hindcast_case(payload, path)
        if case_filter and _normalize_text(payload.get("case_id")).lower() != case_filter:
            continue
        if family_filter and _normalize_text(payload.get("runtime_family_id")).lower() != family_filter:
            continue
        if origin_filter and _normalize_case_origin(payload.get("case_origin")) != origin_filter:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            continue
        case = dict(payload)
        case["case_origin"] = _normalize_case_origin(case.get("case_origin"))
        case["_dataset_path"] = str(path)
        cases.append(case)
    return cases


def _build_active_clock(case: Dict[str, Any]) -> ActiveClockContext:
    return ActiveClockContext(
        timestamp=str(case["benchmark_window"]["start_datetime"]),
        location=str(case.get("location") or ""),
        timezone=str(case.get("timezone") or ""),
        mode="manual",
        house_system_code="P",
        latitude=float(case["latitude"]) if case.get("latitude") is not None else None,
        longitude=float(case["longitude"]) if case.get("longitude") is not None else None,
    )


def _run_case_scan(case: Dict[str, Any], *, quiet_engine: bool) -> Dict[str, Any]:
    request_model = build_weather_scan_request(
        {
            "family_id": case["runtime_family_id"],
            "scan_scope": case["scan_scope"],
            "location": case["location"],
            "timezone": case["timezone"],
            "latitude": case.get("latitude"),
            "longitude": case.get("longitude"),
            "start_datetime": case["benchmark_window"]["start_datetime"],
            "end_datetime": case["benchmark_window"]["end_datetime"],
            "time_step_hours": case["time_step_hours"],
            "top_k": 12,
        }
    )
    sink = StringIO()
    context = redirect_stdout(sink) if quiet_engine else nullcontext()
    err_context = redirect_stderr(sink) if quiet_engine else nullcontext()
    with context, err_context:
        return run_weather_scan(
            request_model,
            active_clock=_build_active_clock(case),
            bundle_resolver=_weather_bundle_resolver,
        )


def _points_in_window(series: List[Dict[str, Any]], window: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [point for point in series if _window_contains(window, str(point.get("datetime") or ""))]


def _summarize_window(series: List[Dict[str, Any]], window: Dict[str, Any], *, label: str) -> Dict[str, Any]:
    points = _points_in_window(series, window)
    if not points:
        raise ValueError(f"{label} produced no sampled points")
    scores = [float(point.get("score") or 0.0) for point in points]
    peak_score = max(scores)
    peak_points = [point for point in points if abs(float(point.get("score") or 0.0) - peak_score) <= EPSILON]
    peak_point = peak_points[len(peak_points) // 2]
    return {
        "sample_count": len(points),
        "mean_score": round(sum(scores) / len(scores), 4),
        "peak_score": round(peak_score, 4),
        "peak_datetime": peak_point.get("datetime"),
        "points": points,
    }


def _collect_failure_reasons(
    *,
    target_percentile: float,
    min_target_percentile: float,
    target_rank: int,
    max_target_rank: int,
    peak_distance_hours: float,
    max_peak_distance_hours: float,
    target_beats_all_controls: bool,
) -> List[str]:
    reasons: List[str] = []
    if target_percentile < min_target_percentile:
        reasons.append("target_percentile_below_threshold")
    if target_rank > max_target_rank:
        reasons.append("target_rank_above_threshold")
    if peak_distance_hours > max_peak_distance_hours:
        reasons.append("peak_distance_too_large")
    if not target_beats_all_controls:
        reasons.append("control_window_outperformed_target")
    return reasons


def _summarize_case(case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    places = (result.get("series") or {}).get("places") or []
    if not places:
        raise ValueError(f"{case['case_id']} returned no place series")
    place = places[0]
    series = place.get("series") or []
    if not series:
        raise ValueError(f"{case['case_id']} returned an empty place series")

    target_window = case["target_window"]
    target_summary = _summarize_window(series, target_window, label=f"{case['case_id']} target window")
    target_points = target_summary["points"]
    control_summaries = [
        _summarize_window(series, window, label=f"{case['case_id']} control window {index}")
        for index, window in enumerate(case.get("control_windows") or [], start=1)
    ]

    all_scores = [float(point.get("score") or 0.0) for point in series]
    target_scores = [float(point.get("score") or 0.0) for point in target_points]
    outside_scores = [float(point.get("score") or 0.0) for point in series if point not in target_points]

    target_peak_score = float(target_summary["peak_score"])
    overall_peak_score = float(place.get("peak_score") or 0.0)
    target_rank = 1 + sum(1 for score in all_scores if score > (target_peak_score + EPSILON))
    target_percentile = round(sum(1 for score in all_scores if score <= (target_peak_score + EPSILON)) / max(len(all_scores), 1), 4)
    target_mean = target_summary["mean_score"]
    outside_mean = round(sum(outside_scores) / len(outside_scores), 4) if outside_scores else None
    target_mean_lift = (
        round(target_mean / outside_mean, 4)
        if outside_mean is not None and outside_mean > EPSILON
        else None
    )
    max_control_peak = max((float(item["peak_score"]) for item in control_summaries), default=None)
    max_control_mean = max((float(item["mean_score"]) for item in control_summaries), default=None)
    target_beats_all_controls = (
        target_peak_score > (max_control_peak + EPSILON)
        if max_control_peak is not None
        else True
    )
    target_control_margin = (
        round(target_peak_score - max_control_peak, 4)
        if max_control_peak is not None
        else None
    )
    target_control_mean_margin = (
        round(target_mean - max_control_mean, 4)
        if max_control_mean is not None
        else None
    )

    peak_start = str(place.get("peak_window_start_datetime") or place.get("peak_datetime") or "")
    peak_end = str(place.get("peak_window_end_datetime") or place.get("peak_datetime") or "")
    peak_distance_hours = _window_distance_hours(
        peak_start,
        peak_end,
        str(target_window["start_datetime"]),
        str(target_window["end_datetime"]),
    )
    target_window_hit = peak_distance_hours <= EPSILON
    target_share_of_top = round((target_peak_score / overall_peak_score), 4) if overall_peak_score > EPSILON else 0.0

    expectations = case.get("scoring_expectations") or {}
    max_peak_distance_hours = float(expectations.get("max_peak_distance_hours") or 0.0)
    exact_hit = target_window_hit
    near_hit = (not exact_hit) and peak_distance_hours <= max_peak_distance_hours
    miss = not exact_hit and not near_hit
    alignment_passed = (
        target_percentile >= float(expectations.get("min_target_percentile") or 0.0)
        and target_rank <= int(expectations.get("max_target_rank") or len(series))
        and peak_distance_hours <= max_peak_distance_hours
        and target_beats_all_controls
    )
    exact_passed = alignment_passed and exact_hit
    near_passed = alignment_passed and near_hit
    failure_reasons = _collect_failure_reasons(
        target_percentile=target_percentile,
        min_target_percentile=float(expectations.get("min_target_percentile") or 0.0),
        target_rank=target_rank,
        max_target_rank=int(expectations.get("max_target_rank") or len(series)),
        peak_distance_hours=peak_distance_hours,
        max_peak_distance_hours=max_peak_distance_hours,
        target_beats_all_controls=target_beats_all_controls,
    )

    return {
        "case_id": case["case_id"],
        "label": case["label"],
        "case_origin": _normalize_case_origin(case.get("case_origin")),
        "runtime_family_id": case["runtime_family_id"],
        "benchmark_family_id": case["benchmark_family_id"],
        "source_case_id": case.get("source_case_id"),
        "location": case["location"],
        "timezone": case["timezone"],
        "sample_count": len(series),
        "target_sample_count": target_summary["sample_count"],
        "overall_peak_score": round(overall_peak_score, 4),
        "overall_peak_datetime": place.get("peak_datetime"),
        "overall_peak_selection": place.get("peak_selection"),
        "target_peak_score": round(target_peak_score, 4),
        "target_peak_datetime": target_summary["peak_datetime"],
        "target_rank": target_rank,
        "target_percentile": target_percentile,
        "target_mean": target_mean,
        "outside_mean": outside_mean,
        "target_mean_lift": target_mean_lift,
        "target_share_of_top": target_share_of_top,
        "control_window_count": len(control_summaries),
        "max_control_peak_score": max_control_peak,
        "max_control_mean_score": max_control_mean,
        "target_beats_all_controls": target_beats_all_controls,
        "target_control_margin": target_control_margin,
        "target_control_mean_margin": target_control_mean_margin,
        "peak_distance_hours": peak_distance_hours,
        "target_window_hit": target_window_hit,
        "exact_hit": exact_hit,
        "near_hit": near_hit,
        "miss": miss,
        "alignment_passed": alignment_passed,
        "exact_passed": exact_passed,
        "near_passed": near_passed,
        "passed": alignment_passed,
        "failure_reasons": failure_reasons,
        "expectations": expectations,
        "target_window": target_window,
        "control_windows": case.get("control_windows") or [],
    }


def _critical_answer(report: Dict[str, Any]) -> str:
    case_count = int(report.get("case_count") or 0)
    if case_count <= 0:
        return (
            "No predictive hindcast cases matched the requested filter. "
            "Add source-backed or novel-holdout cases before drawing any conclusion from this suite."
        )
    alignment_pass_rate = float(report.get("alignment_pass_rate") or 0.0)
    exact_pass_rate = float(report.get("exact_pass_rate") or 0.0)
    median_percentile = float(report.get("median_target_percentile") or 0.0)

    if exact_pass_rate < 0.25 or alignment_pass_rate < 0.5:
        return (
            "Current seed weather models do not show reliable event-timing prediction in this hindcast suite. "
            "Some cases may align after the fact, but the statistical signal is too weak to claim predictive reliability."
        )
    if exact_pass_rate < 0.5 or median_percentile < 0.8:
        return (
            "The suite shows weak-to-moderate hindcast alignment, not strong evidence of prospective prediction. "
            "The models can sometimes concentrate pressure near known events, but they are not yet reliable enough to claim predictive timing."
        )
    return (
        "The suite shows a usable hindcast signal, but this still does not prove prospective prediction. "
        "The models may highlight event windows after calibration, yet they remain research-gated and should not be presented as validated predictive systems."
    )


def _false_positive_policy() -> Dict[str, Any]:
    return {
        "same_place_temporal_controls": True,
        "nearby_place_spillover_allowed": True,
        "note": (
            "Predictive hindcasts penalize false positives only when non-event control windows at the same place "
            "outperform the target event window. Nearby-place spillover is not treated as a benchmark failure in "
            "the current place_timeline suite."
        ),
    }


def _new_rollup_bucket() -> Dict[str, Any]:
    return {
        "case_count": 0,
        "alignment_pass_count": 0,
        "exact_pass_count": 0,
        "near_pass_count": 0,
        "hit_count": 0,
        "control_win_count": 0,
        "target_percentiles": [],
        "failure_reasons": {},
    }


def _finalize_rollup_summary(rollup: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        key: {
            "case_count": bucket["case_count"],
            "alignment_pass_count": bucket["alignment_pass_count"],
            "exact_pass_count": bucket["exact_pass_count"],
            "near_pass_count": bucket["near_pass_count"],
            "hit_count": bucket["hit_count"],
            "control_win_rate": round(bucket["control_win_count"] / bucket["case_count"], 4) if bucket["case_count"] else 0.0,
            "alignment_pass_rate": round(bucket["alignment_pass_count"] / bucket["case_count"], 4) if bucket["case_count"] else 0.0,
            "exact_pass_rate": round(bucket["exact_pass_count"] / bucket["case_count"], 4) if bucket["case_count"] else 0.0,
            "near_pass_rate": round(bucket["near_pass_count"] / bucket["case_count"], 4) if bucket["case_count"] else 0.0,
            "target_window_hit_rate": round(bucket["hit_count"] / bucket["case_count"], 4) if bucket["case_count"] else 0.0,
            "median_target_percentile": round(median(bucket["target_percentiles"]), 4) if bucket["target_percentiles"] else 0.0,
            "failure_reasons": dict(sorted(bucket["failure_reasons"].items())),
        }
        for key, bucket in sorted(rollup.items())
    }


def run_predictive_hindcast_suite(
    *,
    case_id: Optional[str] = None,
    family_id: Optional[str] = None,
    case_origin: Optional[str] = None,
    include_disabled: bool = False,
    quiet_engine: bool = True,
) -> Dict[str, Any]:
    cases = load_predictive_cases(
        case_id=case_id,
        family_id=family_id,
        case_origin=case_origin,
        include_disabled=include_disabled,
    )
    outcomes: List[Dict[str, Any]] = []
    family_rollup: Dict[str, Dict[str, Any]] = {}
    origin_rollup: Dict[str, Dict[str, Any]] = {}

    for case in cases:
        result = _run_case_scan(case, quiet_engine=quiet_engine)
        summary = _summarize_case(case, result)
        outcomes.append(summary)
        bucket = family_rollup.setdefault(
            case["runtime_family_id"],
            _new_rollup_bucket(),
        )
        origin_bucket = origin_rollup.setdefault(
            summary["case_origin"],
            _new_rollup_bucket(),
        )
        for current_bucket in (bucket, origin_bucket):
            current_bucket["case_count"] += 1
            current_bucket["alignment_pass_count"] += 1 if summary["alignment_passed"] else 0
            current_bucket["exact_pass_count"] += 1 if summary["exact_passed"] else 0
            current_bucket["near_pass_count"] += 1 if summary["near_passed"] else 0
            current_bucket["hit_count"] += 1 if summary["target_window_hit"] else 0
            current_bucket["control_win_count"] += 1 if summary["target_beats_all_controls"] else 0
            current_bucket["target_percentiles"].append(summary["target_percentile"])
            for reason in summary["failure_reasons"]:
                current_bucket["failure_reasons"][reason] = int(current_bucket["failure_reasons"].get(reason) or 0) + 1

    case_count = len(outcomes)
    alignment_pass_count = sum(1 for item in outcomes if item["alignment_passed"])
    exact_pass_count = sum(1 for item in outcomes if item["exact_passed"])
    near_pass_count = sum(1 for item in outcomes if item["near_passed"])
    hit_count = sum(1 for item in outcomes if item["target_window_hit"])
    median_target_percentile = round(median([item["target_percentile"] for item in outcomes]), 4) if outcomes else 0.0
    median_peak_distance_hours = round(median([item["peak_distance_hours"] for item in outcomes]), 4) if outcomes else 0.0

    family_summary = _finalize_rollup_summary(family_rollup)
    origin_summary = _finalize_rollup_summary(origin_rollup)

    overall_failure_reasons: Dict[str, int] = {}
    for outcome in outcomes:
        for reason in outcome["failure_reasons"]:
            overall_failure_reasons[reason] = int(overall_failure_reasons.get(reason) or 0) + 1

    report = {
        "dataset_path": str(Path(PREDICTIVE_HINDCAST_FILE).resolve()),
        "case_count": case_count,
        "alignment_pass_count": alignment_pass_count,
        "alignment_fail_count": case_count - alignment_pass_count,
        "alignment_pass_rate": round(alignment_pass_count / case_count, 4) if case_count else 0.0,
        "pass_count": alignment_pass_count,
        "fail_count": case_count - alignment_pass_count,
        "pass_rate": round(alignment_pass_count / case_count, 4) if case_count else 0.0,
        "exact_pass_count": exact_pass_count,
        "exact_pass_rate": round(exact_pass_count / case_count, 4) if case_count else 0.0,
        "near_pass_count": near_pass_count,
        "near_pass_rate": round(near_pass_count / case_count, 4) if case_count else 0.0,
        "target_window_hit_rate": round(hit_count / case_count, 4) if case_count else 0.0,
        "target_window_pass_count": exact_pass_count,
        "target_window_pass_rate": round(exact_pass_count / case_count, 4) if case_count else 0.0,
        "median_target_percentile": median_target_percentile,
        "median_peak_distance_hours": median_peak_distance_hours,
        "overall_failure_reasons": dict(sorted(overall_failure_reasons.items())),
        "requested_case_origin": _normalize_case_origin(case_origin) if case_origin not in (None, "") else None,
        "false_positive_policy": _false_positive_policy(),
        "critical_answer": _critical_answer(
            {
                "case_count": case_count,
                "alignment_pass_rate": round(alignment_pass_count / case_count, 4) if case_count else 0.0,
                "exact_pass_rate": round(exact_pass_count / case_count, 4) if case_count else 0.0,
                "target_window_hit_rate": round(hit_count / case_count, 4) if case_count else 0.0,
                "median_target_percentile": median_target_percentile,
            }
        ),
        "family_summary": family_summary,
        "origin_summary": origin_summary,
        "cases": outcomes,
    }
    return report


def render_markdown_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Weather Predictive Hindcast Report")
    lines.append("")
    lines.append(f"- Cases: {int(report.get('case_count') or 0)}")
    lines.append(f"- Alignment passes: {int(report.get('alignment_pass_count') or 0)}")
    lines.append(f"- Alignment pass rate: {round(float(report.get('alignment_pass_rate') or 0.0) * 100, 1)}%")
    lines.append(f"- Exact passes: {int(report.get('exact_pass_count') or 0)}")
    lines.append(f"- Exact pass rate: {round(float(report.get('exact_pass_rate') or 0.0) * 100, 1)}%")
    lines.append(
        f"- Target-window passes: {int(report.get('target_window_pass_count') or 0)}"
    )
    lines.append(
        f"- Target-window pass rate: {round(float(report.get('target_window_pass_rate') or 0.0) * 100, 1)}%"
    )
    lines.append(f"- Near passes: {int(report.get('near_pass_count') or 0)}")
    lines.append(f"- Near pass rate: {round(float(report.get('near_pass_rate') or 0.0) * 100, 1)}%")
    lines.append(
        f"- Target-window hit rate: {round(float(report.get('target_window_hit_rate') or 0.0) * 100, 1)}%"
    )
    lines.append(f"- Median target percentile: {report.get('median_target_percentile')}")
    lines.append(f"- Median peak distance (hours): {report.get('median_peak_distance_hours')}")
    policy = report.get("false_positive_policy") or {}
    if policy:
        lines.append(
            f"- False-positive policy: same-place temporal controls only; nearby-place spillover {'allowed' if policy.get('nearby_place_spillover_allowed') else 'penalized'}"
        )
    lines.append("")
    lines.append("## Critical Answer")
    lines.append("")
    lines.append(report.get("critical_answer") or "No conclusion.")
    lines.append("")
    lines.append("## Family Summary")
    lines.append("")
    for family_id, bucket in (report.get("family_summary") or {}).items():
        lines.append(
            f"- `{family_id}`: {bucket['alignment_pass_count']}/{bucket['case_count']} alignment, "
            f"{bucket['exact_pass_count']} exact, "
            f"{bucket['near_pass_count']} near, "
            f"target beats controls {round(bucket['control_win_rate'] * 100, 1)}%, "
            f"median percentile {bucket['median_target_percentile']}"
        )
        if bucket.get("failure_reasons"):
            reasons = ", ".join(
                f"{reason}={count}" for reason, count in (bucket.get("failure_reasons") or {}).items()
            )
            lines.append(f"  - fail reasons: {reasons}")
    if report.get("origin_summary"):
        lines.append("")
        lines.append("## Origin Summary")
        lines.append("")
        for origin_id, bucket in (report.get("origin_summary") or {}).items():
            lines.append(
                f"- `{origin_id}`: {bucket['alignment_pass_count']}/{bucket['case_count']} alignment, "
                f"{bucket['exact_pass_count']} exact, "
                f"{bucket['near_pass_count']} near, "
                f"target beats controls {round(bucket['control_win_rate'] * 100, 1)}%, "
                f"median percentile {bucket['median_target_percentile']}"
            )
            if bucket.get("failure_reasons"):
                reasons = ", ".join(
                    f"{reason}={count}" for reason, count in (bucket.get("failure_reasons") or {}).items()
                )
                lines.append(f"  - fail reasons: {reasons}")
    if report.get("overall_failure_reasons"):
        lines.append("")
        lines.append("## Failure Reasons")
        lines.append("")
        for reason, count in (report.get("overall_failure_reasons") or {}).items():
            lines.append(f"- `{reason}`: {count}")
    lines.append("")
    lines.append("## Case Outcomes")
    lines.append("")
    for case in report.get("cases") or []:
        hit_label = "EXACT" if case["exact_hit"] else "NEAR" if case["near_hit"] else "MISS"
        lines.append(
            f"- `{case['case_id']}`: {'PASS' if case['alignment_passed'] else 'FAIL'} | "
            f"{hit_label} | "
            f"target percentile {case['target_percentile']} | "
            f"target rank {case['target_rank']} | "
            f"control margin {case['target_control_margin']} | "
            f"peak distance {case['peak_distance_hours']}h"
        )
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the weather predictive hindcast benchmark suite.")
    parser.add_argument("--case-id", help="Run a single predictive hindcast case by case_id.")
    parser.add_argument("--family-id", help="Run predictive hindcasts for a single runtime family id.")
    parser.add_argument("--case-origin", choices=sorted(PREDICTIVE_CASE_ORIGINS), help="Filter predictive hindcasts by case origin.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled cases.")
    parser.add_argument("--show-engine-logs", action="store_true", help="Do not suppress verbose engine logs during scan execution.")
    args = parser.parse_args(argv)

    report = run_predictive_hindcast_suite(
        case_id=args.case_id,
        family_id=args.family_id,
        case_origin=args.case_origin,
        include_disabled=args.include_disabled,
        quiet_engine=not args.show_engine_logs,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
