from __future__ import annotations

import argparse
import copy
import json
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from datetime import datetime
from functools import lru_cache
from io import StringIO
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Sequence

import astro_clock_api
from mundane_models import ActiveClockContext
from mundane_scan_service import build_scan_request, run_scan
from validate_mundane_benchmark_datasets import (
    HISTORICAL_FILES,
    WAR_SCAN_HINDCAST_BENCHMARK_FILE,
    load_jsonl_cases,
    validate_historical_case,
    validate_war_scan_hindcast_case,
)


EPSILON = 1e-6

DEFAULT_ACTIVE_CLOCK = ActiveClockContext(
    timestamp="2026-04-13T08:00:00+00:00",
    location="Greenwich, UK",
    timezone="Europe/London",
    mode="manual",
    house_system_code="P",
    latitude=51.4769,
    longitude=-0.0005,
)
DISCOVERY_STRIPPED_REQUEST_FIELDS = {
    "reference_location",
    "reference_latitude",
    "reference_longitude",
    "event_location",
    "event_timezone",
}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _parse_datetime(value: Any) -> datetime:
    return datetime.fromisoformat(str(value or "").strip().replace("Z", "+00:00"))


def _window_contains(window: Dict[str, Any], dt_iso: str) -> bool:
    current = _parse_datetime(dt_iso)
    return _parse_datetime(window["start_datetime"]) <= current <= _parse_datetime(window["end_datetime"])


@lru_cache(maxsize=1)
def _historical_source_index() -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for raw_path in HISTORICAL_FILES:
        path = Path(raw_path).resolve()
        if not path.exists():
            continue
        for payload in load_jsonl_cases(path):
            validate_historical_case(payload, path)
            case_id = _normalize_text(payload.get("case_id"))
            if not case_id or case_id in index:
                continue
            index[case_id] = {
                "case_id": case_id,
                "label": payload.get("label"),
                "dataset": str(path),
                "domain_id": payload.get("domain_id"),
                "benchmark_type": payload.get("benchmark_type"),
                "event": payload.get("event") or {},
                "expected_domain_lead": payload.get("expected_domain_lead"),
                "expected_interpretations": list(payload.get("expected_interpretations") or []),
                "source_assertions": list(payload.get("source_assertions") or []),
            }
    return index


def _resolve_source_backing(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    index = _historical_source_index()
    backing: List[Dict[str, Any]] = []
    missing: List[str] = []
    unsourced: List[str] = []
    for raw_ref in case.get("benchmark_refs") or []:
        ref_id = _normalize_text(raw_ref)
        source_case = index.get(ref_id)
        if source_case is None:
            missing.append(ref_id)
            continue
        assertions = list(source_case.get("source_assertions") or [])
        if not assertions:
            unsourced.append(ref_id)
            continue
        backing.append(source_case)
    if missing:
        raise ValueError(f"{case.get('case_id')} has unresolved benchmark_refs: {', '.join(missing)}")
    if unsourced:
        raise ValueError(f"{case.get('case_id')} has benchmark_refs without source assertions: {', '.join(unsourced)}")
    if not backing:
        raise ValueError(f"{case.get('case_id')} must resolve at least one source-backed benchmark_ref")
    return backing


def _source_backing_summary(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for source_case in _resolve_source_backing(case):
        rows.append(
            {
                "case_id": source_case.get("case_id"),
                "label": source_case.get("label"),
                "dataset": source_case.get("dataset"),
                "domain_id": source_case.get("domain_id"),
                "benchmark_type": source_case.get("benchmark_type"),
                "event": source_case.get("event") or {},
                "expected_domain_lead": source_case.get("expected_domain_lead"),
                "expected_interpretations": list(source_case.get("expected_interpretations") or []),
                "source_assertions": [
                    {
                        "title": assertion.get("title"),
                        "normalized_file": assertion.get("normalized_file"),
                        "pages": assertion.get("pages"),
                        "claim": assertion.get("claim"),
                    }
                    for assertion in (source_case.get("source_assertions") or [])
                    if isinstance(assertion, dict)
                ],
            }
        )
    return rows


def _period_place_discovery_case(case: Dict[str, Any]) -> Dict[str, Any]:
    discovery_case = copy.deepcopy(case)
    request_payload = dict(discovery_case.get("request") or {})
    for field_name in DISCOVERY_STRIPPED_REQUEST_FIELDS:
        request_payload.pop(field_name, None)
    discovery_case["request"] = request_payload
    discovery_case["period_place_discovery"] = True
    return discovery_case


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


def load_war_scan_hindcast_cases(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> List[Dict[str, Any]]:
    path = Path(WAR_SCAN_HINDCAST_BENCHMARK_FILE).resolve()
    cases: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()
    for payload in load_jsonl_cases(path):
        validate_war_scan_hindcast_case(payload, path)
        if case_filter and _normalize_text(payload.get("case_id")).lower() != case_filter:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            continue
        case = dict(payload)
        _resolve_source_backing(case)
        case["_dataset_path"] = str(path)
        cases.append(case)
    return cases


def _run_case_scan(case: Dict[str, Any], *, quiet_engine: bool) -> Dict[str, Any]:
    request_model = build_scan_request(case["request"])
    sink = StringIO()
    context = redirect_stdout(sink) if quiet_engine else nullcontext()
    err_context = redirect_stderr(sink) if quiet_engine else nullcontext()
    with context, err_context:
        return run_scan(
            request_model,
            active_clock=DEFAULT_ACTIVE_CLOCK,
            bundle_resolver=astro_clock_api._mundane_bundle_resolver,
            include_series=True,
        )


def _points_in_window(series: List[Dict[str, Any]], window: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [point for point in series if _window_contains(window, str(point.get("datetime") or ""))]


def _summarize_window(series: List[Dict[str, Any]], window: Dict[str, Any], *, label: str) -> Dict[str, Any]:
    points = _points_in_window(series, window)
    if not points:
        raise ValueError(f"{label} produced no sampled points")
    scores = [float(point.get("scan_score") or 0.0) for point in points]
    peak_score = max(scores)
    peak_points = [point for point in points if abs(float(point.get("scan_score") or 0.0) - peak_score) <= EPSILON]
    peak_point = peak_points[len(peak_points) // 2]
    return {
        "sample_count": len(points),
        "mean_score": round(sum(scores) / len(scores), 4),
        "peak_score": round(peak_score, 4),
        "peak_datetime": peak_point.get("datetime"),
        "points": points,
    }


def _place_matches(place: Dict[str, Any], case: Dict[str, Any]) -> bool:
    label = _normalize_text(((place.get("location") or {}).get("label"))).lower()
    country_code = _normalize_text(((place.get("location") or {}).get("country_code"))).upper()
    place_tokens = [
        _normalize_text(token).lower()
        for token in (case.get("target_place_tokens_any") or [])
        if _normalize_text(token)
    ]
    country_codes = {
        _normalize_text(code).upper()
        for code in (case.get("target_country_codes_any") or [])
        if _normalize_text(code)
    }
    token_match = bool(place_tokens) and any(token in label for token in place_tokens)
    country_match = bool(country_codes) and country_code in country_codes
    if place_tokens:
        return token_match and (country_match if country_codes else True)
    return country_match


def _collect_failure_reasons(
    *,
    target_place_found: bool,
    target_place_rank: Optional[int],
    max_target_place_rank: int,
    target_percentile: Optional[float],
    min_target_percentile: float,
    peak_distance_hours: Optional[float],
    max_peak_distance_hours: float,
    target_beats_all_controls: Optional[bool],
) -> List[str]:
    reasons: List[str] = []
    if not target_place_found:
        reasons.append("target_place_not_returned")
        return reasons
    if target_place_rank is not None and target_place_rank > max_target_place_rank:
        reasons.append("target_place_rank_above_threshold")
    if target_percentile is not None and target_percentile < min_target_percentile:
        reasons.append("target_percentile_below_threshold")
    if peak_distance_hours is not None and peak_distance_hours > max_peak_distance_hours:
        reasons.append("peak_distance_too_large")
    if target_beats_all_controls is False:
        reasons.append("control_window_outperformed_target")
    return reasons


def _summarize_case(case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    places = list(((result.get("series") or {}).get("places") or []))
    target_place = None
    target_place_rank: Optional[int] = None
    for index, place in enumerate(places, start=1):
        if _place_matches(place, case):
            target_place = place
            target_place_rank = index
            break

    expectations = case.get("scoring_expectations") or {}
    max_target_place_rank = int(expectations.get("max_target_place_rank") or len(places) or 1)
    min_target_percentile = float(expectations.get("min_target_percentile") or 0.0)
    max_peak_distance_hours = float(expectations.get("max_peak_distance_hours") or 0.0)

    if target_place is None:
        failure_reasons = _collect_failure_reasons(
            target_place_found=False,
            target_place_rank=None,
            max_target_place_rank=max_target_place_rank,
            target_percentile=None,
            min_target_percentile=min_target_percentile,
            peak_distance_hours=None,
            max_peak_distance_hours=max_peak_distance_hours,
            target_beats_all_controls=None,
        )
        return {
            "case_id": case["case_id"],
            "label": case["label"],
            "domain_id": str((case.get("request") or {}).get("domain") or ""),
            "scan_mode": str((case.get("request") or {}).get("scan_mode") or ""),
            "target_place_found": False,
            "target_place_rank": None,
            "target_place_label": None,
            "target_percentile": None,
            "peak_distance_hours": None,
            "target_window_hit": False,
            "near_hit": False,
            "alignment_passed": False,
            "passed": False,
            "target_beats_all_controls": None,
            "failure_reasons": failure_reasons,
            "counts": result.get("counts") or {},
            "series_overview": ((result.get("series") or {}).get("series_overview") or {}),
            "benchmark_refs": list(case.get("benchmark_refs") or []),
            "source_backing": _source_backing_summary(case),
        }

    series = list(target_place.get("series") or [])
    target_window = case["target_window"]
    target_summary = _summarize_window(series, target_window, label=f"{case['case_id']} target window")
    control_summaries = [
        _summarize_window(series, window, label=f"{case['case_id']} control window {index}")
        for index, window in enumerate(case.get("control_windows") or [], start=1)
    ]

    all_scores = [float(point.get("scan_score") or 0.0) for point in series]
    target_peak_score = float(target_summary["peak_score"])
    target_rank = 1 + sum(1 for score in all_scores if score > (target_peak_score + EPSILON))
    target_percentile = round(
        sum(1 for score in all_scores if score <= (target_peak_score + EPSILON)) / max(len(all_scores), 1),
        4,
    )
    target_mean = float(target_summary["mean_score"])
    outside_points = [point for point in series if point not in target_summary["points"]]
    outside_scores = [float(point.get("scan_score") or 0.0) for point in outside_points]
    outside_mean = round(sum(outside_scores) / len(outside_scores), 4) if outside_scores else None
    target_mean_lift = round(target_mean / outside_mean, 4) if outside_mean and outside_mean > EPSILON else None
    max_control_peak = max((float(item["peak_score"]) for item in control_summaries), default=None)
    max_control_mean = max((float(item["mean_score"]) for item in control_summaries), default=None)
    target_beats_all_controls = (
        target_peak_score > (max_control_peak + EPSILON)
        if max_control_peak is not None
        else True
    )
    target_control_margin = round(target_peak_score - max_control_peak, 4) if max_control_peak is not None else None
    target_control_mean_margin = round(target_mean - max_control_mean, 4) if max_control_mean is not None else None

    peak_start = str(target_place.get("peak_window_start_datetime") or target_place.get("peak_datetime") or "")
    peak_end = str(target_place.get("peak_window_end_datetime") or target_place.get("peak_datetime") or "")
    peak_distance_hours = _window_distance_hours(
        peak_start,
        peak_end,
        str(target_window["start_datetime"]),
        str(target_window["end_datetime"]),
    )
    target_window_hit = peak_distance_hours <= EPSILON
    near_hit = (not target_window_hit) and peak_distance_hours <= max_peak_distance_hours
    target_share_of_peak = round(
        target_peak_score / max(float(target_place.get("peak_scan_score") or 0.0), EPSILON),
        4,
    )

    failure_reasons = _collect_failure_reasons(
        target_place_found=True,
        target_place_rank=target_place_rank,
        max_target_place_rank=max_target_place_rank,
        target_percentile=target_percentile,
        min_target_percentile=min_target_percentile,
        peak_distance_hours=peak_distance_hours,
        max_peak_distance_hours=max_peak_distance_hours,
        target_beats_all_controls=target_beats_all_controls,
    )
    alignment_passed = not failure_reasons

    return {
        "case_id": case["case_id"],
        "label": case["label"],
        "domain_id": str((case.get("request") or {}).get("domain") or ""),
        "scan_mode": str((case.get("request") or {}).get("scan_mode") or ""),
        "target_place_found": True,
        "target_place_rank": target_place_rank,
        "target_place_label": ((target_place.get("location") or {}).get("label")),
        "target_place_peak_score": round(float(target_place.get("peak_scan_score") or 0.0), 4),
        "target_place_peak_datetime": target_place.get("peak_datetime"),
        "target_window_peak_score": round(target_peak_score, 4),
        "target_window_peak_datetime": target_summary["peak_datetime"],
        "target_percentile": target_percentile,
        "target_window_hit": target_window_hit,
        "near_hit": near_hit,
        "peak_distance_hours": peak_distance_hours,
        "target_mean": target_mean,
        "outside_mean": outside_mean,
        "target_mean_lift": target_mean_lift,
        "target_share_of_peak": target_share_of_peak,
        "max_control_peak_score": max_control_peak,
        "max_control_mean_score": max_control_mean,
        "target_beats_all_controls": target_beats_all_controls,
        "target_control_margin": target_control_margin,
        "target_control_mean_margin": target_control_mean_margin,
        "alignment_passed": alignment_passed,
        "passed": alignment_passed,
        "failure_reasons": failure_reasons,
        "counts": result.get("counts") or {},
        "series_overview": ((result.get("series") or {}).get("series_overview") or {}),
        "benchmark_refs": list(case.get("benchmark_refs") or []),
        "source_backing": _source_backing_summary(case),
    }


def _critical_answer(report: Dict[str, Any]) -> str:
    place_recall_rate = float(report.get("place_recall_rate") or 0.0)
    alignment_pass_rate = float(report.get("alignment_pass_rate") or 0.0)
    target_window_hit_rate = float(report.get("target_window_hit_rate") or 0.0)
    if place_recall_rate < 0.75 or alignment_pass_rate < 0.5:
        return (
            "The current war-event scan shows weak hindcast localization. It can sometimes recover the theater after the fact, "
            "but the present runtime is not strong enough to claim reliable war-event scan prediction."
        )
    if target_window_hit_rate < 0.25 or alignment_pass_rate < 0.75:
        return (
            "The suite shows mixed hindcast signal. The runtime often recovers part of the war theater, "
            "but timing concentration and control-window discrimination remain inconsistent."
        )
    return (
        "The suite shows a usable hindcast localization signal for war-event scans, "
        "but this is still not enough to claim validated prospective war prediction."
    )


def run_war_scan_hindcast_suite(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
    quiet_engine: bool = True,
    period_place_discovery: bool = False,
) -> Dict[str, Any]:
    cases = load_war_scan_hindcast_cases(case_id=case_id, include_disabled=include_disabled)
    outcomes: List[Dict[str, Any]] = []
    domain_rollup: Dict[str, Dict[str, Any]] = {}

    for case in cases:
        scan_case = _period_place_discovery_case(case) if period_place_discovery else case
        result = _run_case_scan(scan_case, quiet_engine=quiet_engine)
        summary = _summarize_case(case, result)
        summary["period_place_discovery"] = bool(period_place_discovery)
        outcomes.append(summary)

        domain_id = summary["domain_id"] or "unknown"
        bucket = domain_rollup.setdefault(
            domain_id,
            {
                "case_count": 0,
                "place_recall_count": 0,
                "alignment_pass_count": 0,
                "target_window_hit_count": 0,
                "near_hit_count": 0,
                "place_ranks": [],
                "peak_distances": [],
                "failure_reasons": {},
            },
        )
        bucket["case_count"] += 1
        bucket["place_recall_count"] += 1 if summary["target_place_found"] else 0
        bucket["alignment_pass_count"] += 1 if summary["alignment_passed"] else 0
        bucket["target_window_hit_count"] += 1 if summary["target_window_hit"] else 0
        bucket["near_hit_count"] += 1 if summary["near_hit"] else 0
        if summary["target_place_rank"] is not None:
            bucket["place_ranks"].append(int(summary["target_place_rank"]))
        if summary["peak_distance_hours"] is not None:
            bucket["peak_distances"].append(float(summary["peak_distance_hours"]))
        for reason in summary["failure_reasons"]:
            bucket["failure_reasons"][reason] = int(bucket["failure_reasons"].get(reason) or 0) + 1

    case_count = len(outcomes)
    place_recall_count = sum(1 for item in outcomes if item["target_place_found"])
    alignment_pass_count = sum(1 for item in outcomes if item["alignment_passed"])
    target_window_hit_count = sum(1 for item in outcomes if item["target_window_hit"])
    near_hit_count = sum(1 for item in outcomes if item["near_hit"])
    source_backed_case_count = sum(1 for item in outcomes if item.get("source_backing"))
    source_assertion_count = sum(
        len(source.get("source_assertions") or [])
        for item in outcomes
        for source in (item.get("source_backing") or [])
    )
    median_target_place_rank = median([item["target_place_rank"] for item in outcomes if item["target_place_rank"] is not None]) if any(item["target_place_rank"] is not None for item in outcomes) else None
    median_peak_distance_hours = median([item["peak_distance_hours"] for item in outcomes if item["peak_distance_hours"] is not None]) if any(item["peak_distance_hours"] is not None for item in outcomes) else None

    family_summary = {
        domain_id: {
            "case_count": bucket["case_count"],
            "place_recall_count": bucket["place_recall_count"],
            "alignment_pass_count": bucket["alignment_pass_count"],
            "target_window_hit_count": bucket["target_window_hit_count"],
            "near_hit_count": bucket["near_hit_count"],
            "place_recall_rate": round(bucket["place_recall_count"] / bucket["case_count"], 4) if bucket["case_count"] else 0.0,
            "alignment_pass_rate": round(bucket["alignment_pass_count"] / bucket["case_count"], 4) if bucket["case_count"] else 0.0,
            "target_window_hit_rate": round(bucket["target_window_hit_count"] / bucket["case_count"], 4) if bucket["case_count"] else 0.0,
            "near_hit_rate": round(bucket["near_hit_count"] / bucket["case_count"], 4) if bucket["case_count"] else 0.0,
            "median_target_place_rank": round(median(bucket["place_ranks"]), 3) if bucket["place_ranks"] else None,
            "median_peak_distance_hours": round(median(bucket["peak_distances"]), 3) if bucket["peak_distances"] else None,
            "failure_reasons": dict(sorted(bucket["failure_reasons"].items())),
        }
        for domain_id, bucket in sorted(domain_rollup.items())
    }

    overall_failure_reasons: Dict[str, int] = {}
    for outcome in outcomes:
        for reason in outcome["failure_reasons"]:
            overall_failure_reasons[reason] = int(overall_failure_reasons.get(reason) or 0) + 1

    report = {
        "dataset_path": str(Path(WAR_SCAN_HINDCAST_BENCHMARK_FILE).resolve()),
        "period_place_discovery": bool(period_place_discovery),
        "case_count": case_count,
        "place_recall_count": place_recall_count,
        "alignment_pass_count": alignment_pass_count,
        "target_window_hit_count": target_window_hit_count,
        "near_hit_count": near_hit_count,
        "source_backed_case_count": source_backed_case_count,
        "source_assertion_count": source_assertion_count,
        "place_recall_rate": round(place_recall_count / case_count, 4) if case_count else 0.0,
        "alignment_pass_rate": round(alignment_pass_count / case_count, 4) if case_count else 0.0,
        "target_window_hit_rate": round(target_window_hit_count / case_count, 4) if case_count else 0.0,
        "near_hit_rate": round(near_hit_count / case_count, 4) if case_count else 0.0,
        "fail_count": case_count - alignment_pass_count,
        "median_target_place_rank": round(float(median_target_place_rank), 3) if median_target_place_rank is not None else None,
        "median_peak_distance_hours": round(float(median_peak_distance_hours), 3) if median_peak_distance_hours is not None else None,
        "failure_reasons": dict(sorted(overall_failure_reasons.items())),
        "family_summary": family_summary,
        "cases": outcomes,
    }
    report["critical_answer"] = _critical_answer(report)
    return report


def format_war_scan_hindcast_report(summary: Dict[str, Any]) -> str:
    lines = [
        "# Mundane War Scan Hindcasts",
        "",
        f"- dataset: `{summary.get('dataset_path')}`",
        f"- period-place discovery mode: {bool(summary.get('period_place_discovery'))}",
        f"- cases: {summary.get('case_count')}",
        f"- place recall: {summary.get('place_recall_count')} ({summary.get('place_recall_rate', 0.0):.2%})",
        f"- alignment passes: {summary.get('alignment_pass_count')} ({summary.get('alignment_pass_rate', 0.0):.2%})",
        f"- target-window hits: {summary.get('target_window_hit_count')} ({summary.get('target_window_hit_rate', 0.0):.2%})",
        f"- near hits: {summary.get('near_hit_count')} ({summary.get('near_hit_rate', 0.0):.2%})",
        f"- source-backed cases: {summary.get('source_backed_case_count')} ({summary.get('source_assertion_count')} source assertions)",
        f"- median target place rank: {summary.get('median_target_place_rank')}",
        f"- median peak distance (hours): {summary.get('median_peak_distance_hours')}",
        f"- critical answer: {summary.get('critical_answer')}",
    ]
    failure_reasons = summary.get("failure_reasons") or {}
    if failure_reasons:
        lines.append(f"- failure reasons: {json.dumps(failure_reasons, sort_keys=True)}")

    for item in summary.get("cases") or []:
        status = "PASS" if item.get("alignment_passed") else "FAIL"
        lines.extend(
            [
                "",
                f"## {status} {item.get('case_id')}",
                f"- label: {item.get('label')}",
                f"- domain: {item.get('domain_id')}",
                f"- target place: {item.get('target_place_label') or 'none'}",
                f"- target place rank: {item.get('target_place_rank')}",
                f"- target percentile: {item.get('target_percentile')}",
                f"- target-window hit: {item.get('target_window_hit')}",
                f"- near hit: {item.get('near_hit')}",
                f"- peak distance hours: {item.get('peak_distance_hours')}",
                f"- target beats controls: {item.get('target_beats_all_controls')}",
                f"- failure reasons: {', '.join(item.get('failure_reasons') or []) or 'none'}",
                f"- refs: {', '.join(item.get('benchmark_refs') or []) or 'none'}",
            ]
        )
        source_rows = item.get("source_backing") or []
        if source_rows:
            lines.append("- source backing:")
            for source in source_rows:
                event = source.get("event") or {}
                event_date = event.get("date") or event.get("start_date") or "unknown"
                if event.get("end_date") and event.get("end_date") != event_date:
                    event_date = f"{event_date} to {event.get('end_date')}"
                lines.append(
                    f"  - `{source.get('case_id')}` {event_date}, "
                    f"{event.get('location') or 'unknown location'}"
                )
                for assertion in (source.get("source_assertions") or [])[:2]:
                    lines.append(
                        "    - "
                        f"{assertion.get('title') or 'source'}"
                        f"{' pp. ' + str(assertion.get('pages')) if assertion.get('pages') else ''}: "
                        f"{assertion.get('claim') or ''}"
                    )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run mundane war scan hindcast benchmarks.")
    parser.add_argument("--case-id", help="Only run a single hindcast case.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled rows.")
    parser.add_argument(
        "--period-place-discovery",
        action="store_true",
        help="Strip known target-place anchors and test period/region input to returned places.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--show-engine-output", action="store_true", help="Show engine stdout/stderr during runs.")
    args = parser.parse_args(argv)

    summary = run_war_scan_hindcast_suite(
        case_id=args.case_id,
        include_disabled=args.include_disabled,
        quiet_engine=not args.show_engine_output,
        period_place_discovery=args.period_place_discovery,
    )
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_war_scan_hindcast_report(summary))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
