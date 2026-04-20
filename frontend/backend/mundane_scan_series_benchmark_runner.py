from __future__ import annotations

import argparse
import io
import json
import logging
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import astro_clock_api
from mundane_models import ActiveClockContext
from mundane_scan_service import build_scan_request, run_scan
from validate_mundane_benchmark_datasets import (
    SCANNER_SERIES_BENCHMARK_FILE,
    load_jsonl_cases,
    validate_scanner_series_case,
)


DEFAULT_ACTIVE_CLOCK = ActiveClockContext(
    timestamp="2026-04-11T08:00:00+00:00",
    location="Greenwich, UK",
    timezone="Europe/London",
    mode="manual",
    house_system_code="P",
    latitude=51.4769,
    longitude=-0.0005,
)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _location_matches(location: Dict[str, Any], tokens: Sequence[str]) -> bool:
    label = _normalize_text((location or {}).get("label")).lower()
    normalized_tokens = [_normalize_text(token).lower() for token in (tokens or []) if _normalize_text(token)]
    return any(token in label for token in normalized_tokens)


def load_scanner_series_benchmark_cases(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cases: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()

    for payload in load_jsonl_cases(SCANNER_SERIES_BENCHMARK_FILE):
        validate_scanner_series_case(payload, SCANNER_SERIES_BENCHMARK_FILE)
        current_case_id = _normalize_text(payload.get("case_id"))
        if case_filter and current_case_id.lower() != case_filter:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            skipped.append({"case_id": current_case_id, "reason": "disabled"})
            continue
        cases.append(dict(payload))

    return cases, skipped


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(_json_safe(item) for item in value)
    return value


def execute_scanner_series_case(
    case: Dict[str, Any],
    *,
    active_clock: ActiveClockContext = DEFAULT_ACTIVE_CLOCK,
) -> Dict[str, Any]:
    request_payload = dict(case.get("request") or {})
    request_model = build_scan_request(request_payload)

    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        result = run_scan(
            request_model,
            active_clock=active_clock,
            bundle_resolver=astro_clock_api._mundane_bundle_resolver,
            include_series=True,
        )
    return result


def evaluate_scanner_series_case_result(case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    expectation = case.get("series_expectation") or {}
    series_payload = result.get("series") or {}
    timeline = list(series_payload.get("timeline") or [])
    places = list(series_payload.get("places") or [])
    breakout_candidates = list(series_payload.get("breakout_candidates") or [])
    overview = series_payload.get("series_overview") or {}

    warnings: List[str] = []
    passed = True

    if not timeline or not places:
        passed = False
        warnings.append("missing_series")

    expected_time_slices = expectation.get("expected_time_slices")
    if expected_time_slices is not None and len(timeline) != int(expected_time_slices):
        passed = False
        warnings.append("timeline_length_mismatch")

    if bool(expectation.get("require_series_alignment")) and timeline:
        for place in places:
            place_series = list(place.get("series") or [])
            if len(place_series) != len(timeline):
                passed = False
                warnings.append("series_alignment_failed")
                break
            if [str(point.get("datetime") or "") for point in place_series] != [str(tick) for tick in timeline]:
                passed = False
                warnings.append("series_alignment_failed")
                break

    expected_place_tokens = expectation.get("expected_place_tokens_any") or []
    expected_breakout_place_tokens = expectation.get("expected_breakout_place_tokens_any") or expected_place_tokens

    matched_place = next(
        (place for place in places if _location_matches(place.get("location") or {}, expected_place_tokens)),
        None,
    )
    if expected_place_tokens and matched_place is None:
        passed = False
        warnings.append("expected_place_missing_from_series")

    matched_breakout = next(
        (row for row in breakout_candidates if _location_matches(row.get("location") or {}, expected_breakout_place_tokens)),
        None,
    )
    if expected_breakout_place_tokens and matched_breakout is None:
        passed = False
        warnings.append("expected_place_missing_from_breakout_candidates")

    max_breakout_rank = expectation.get("max_breakout_rank")
    if matched_breakout is not None and max_breakout_rank is not None:
        breakout_rank = int(matched_breakout.get("rank") or 0)
        if breakout_rank > int(max_breakout_rank):
            passed = False
            warnings.append("expected_breakout_rank_exceeded")
        elif breakout_rank > 1:
            warnings.append("expected_breakout_not_top_rank")

    minimum_peak_scan_score = expectation.get("minimum_peak_scan_score")
    peak_scan_score = float((matched_place or {}).get("peak_scan_score") or 0.0)
    if minimum_peak_scan_score is not None:
        if peak_scan_score < float(minimum_peak_scan_score):
            passed = False
            warnings.append("low_peak_scan_score")

    minimum_breakout_index = expectation.get("minimum_breakout_index")
    breakout_index = float((matched_place or {}).get("breakout_index") or 0.0)
    if minimum_breakout_index is not None:
        if breakout_index < float(minimum_breakout_index):
            passed = False
            warnings.append("low_breakout_index")

    if bool(expectation.get("require_nonzero_series")) and matched_place is not None and peak_scan_score <= 0.0:
        passed = False
        warnings.append("expected_nonzero_series")

    expected_breakout_kinds = [_normalize_text(kind).lower() for kind in (expectation.get("expected_breakout_kind_any") or [])]
    matched_breakout_kind = _normalize_text((matched_place or {}).get("breakout_kind")).lower()
    if expected_breakout_kinds and matched_place is not None and matched_breakout_kind not in expected_breakout_kinds:
        warnings.append("unexpected_breakout_kind")

    diagnostic_status = "fail"
    if passed and not warnings:
        diagnostic_status = "strong_pass"
    elif passed:
        diagnostic_status = "weak_pass"

    return {
        "case_id": case.get("case_id"),
        "label": case.get("label"),
        "passed": passed,
        "diagnostic_status": diagnostic_status,
        "timeline_points": len(timeline),
        "place_count": len(places),
        "matched_place": ((matched_place or {}).get("location") or {}).get("label"),
        "matched_peak_scan_score": peak_scan_score,
        "matched_breakout_index": breakout_index,
        "matched_breakout_kind": (matched_place or {}).get("breakout_kind"),
        "matched_breakout_rank": int((matched_breakout or {}).get("rank") or 0) if matched_breakout else None,
        "warning_flags": warnings,
        "benchmark_refs": list(case.get("benchmark_refs") or []),
        "series_overview": overview,
    }


def run_scanner_series_benchmark_suite(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
    active_clock: ActiveClockContext = DEFAULT_ACTIVE_CLOCK,
) -> Dict[str, Any]:
    logging.getLogger("astro_clock_engine").setLevel(logging.ERROR)
    logging.getLogger("app").setLevel(logging.ERROR)

    cases, skipped = load_scanner_series_benchmark_cases(
        case_id=case_id,
        include_disabled=include_disabled,
    )

    case_results: List[Dict[str, Any]] = []
    pass_count = 0
    weak_pass_count = 0
    warning_counts: Dict[str, int] = {}
    for case in cases:
        scan_result = execute_scanner_series_case(case, active_clock=active_clock)
        evaluation = evaluate_scanner_series_case_result(case, scan_result)
        if evaluation["passed"]:
            pass_count += 1
        if evaluation["diagnostic_status"] == "weak_pass":
            weak_pass_count += 1
        for warning in evaluation.get("warning_flags") or []:
            warning_counts[warning] = int(warning_counts.get(warning) or 0) + 1
        evaluation["scan_result"] = scan_result
        case_results.append(evaluation)

    return {
        "dataset_path": str(Path(SCANNER_SERIES_BENCHMARK_FILE).resolve()),
        "case_count": len(case_results),
        "pass_count": pass_count,
        "fail_count": len(case_results) - pass_count,
        "pass_rate": (pass_count / len(case_results)) if case_results else 0.0,
        "weak_pass_count": weak_pass_count,
        "strong_pass_count": max(0, pass_count - weak_pass_count),
        "warning_counts": dict(sorted(warning_counts.items())),
        "skipped": skipped,
        "cases": case_results,
    }


def format_scanner_series_benchmark_report(summary: Dict[str, Any]) -> str:
    lines = [
        "# Mundane Scanner Series Benchmarks",
        "",
        f"- dataset: `{summary.get('dataset_path')}`",
        f"- cases: {summary.get('case_count')}",
        f"- passed: {summary.get('pass_count')}",
        f"- failed: {summary.get('fail_count')}",
        f"- pass rate: {summary.get('pass_rate', 0.0):.2%}",
        f"- strong passes: {summary.get('strong_pass_count')}",
        f"- weak passes: {summary.get('weak_pass_count')}",
    ]
    warning_counts = summary.get("warning_counts") or {}
    if warning_counts:
        lines.append(f"- warning counts: {json.dumps(warning_counts, sort_keys=True)}")
    for item in summary.get("cases") or []:
        status = "PASS" if item.get("passed") else "FAIL"
        lines.extend(
            [
                "",
                f"## {status} {item.get('case_id')}",
                f"- label: {item.get('label')}",
                f"- diagnostic status: {item.get('diagnostic_status')}",
                f"- matched place: {item.get('matched_place') or 'none'}",
                f"- breakout rank: {item.get('matched_breakout_rank')}",
                f"- peak scan score: {item.get('matched_peak_scan_score')}",
                f"- breakout index: {item.get('matched_breakout_index')}",
                f"- breakout kind: {item.get('matched_breakout_kind') or 'none'}",
                f"- timeline points: {item.get('timeline_points')}",
                f"- place count: {item.get('place_count')}",
                f"- warnings: {', '.join(item.get('warning_flags') or []) or 'none'}",
                f"- refs: {', '.join(item.get('benchmark_refs') or []) or 'none'}",
            ]
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run mundane scanner series benchmark cases.")
    parser.add_argument("--case-id", help="Only run a single scanner-series benchmark case.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled scanner-series benchmark rows.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of markdown.")
    args = parser.parse_args(argv)

    summary = run_scanner_series_benchmark_suite(
        case_id=args.case_id,
        include_disabled=args.include_disabled,
    )

    if args.json:
        print(json.dumps(_json_safe(summary), indent=2))
    else:
        print(format_scanner_series_benchmark_report(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
