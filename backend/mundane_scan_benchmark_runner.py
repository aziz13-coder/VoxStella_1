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
    SCANNER_BENCHMARK_FILE,
    load_jsonl_cases,
    validate_scanner_case,
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


def _row_scan_score(row: Dict[str, Any]) -> float:
    try:
        if row.get("scan_score") is not None:
            return float(row.get("scan_score") or 0.0)
        return float(row.get("score") or 0.0)
    except Exception:
        return 0.0


def load_scanner_benchmark_cases(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cases: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()

    for payload in load_jsonl_cases(SCANNER_BENCHMARK_FILE):
        validate_scanner_case(payload, SCANNER_BENCHMARK_FILE)
        current_case_id = _normalize_text(payload.get("case_id"))
        if case_filter and current_case_id.lower() != case_filter:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            skipped.append({"case_id": current_case_id, "reason": "disabled"})
            continue
        cases.append(dict(payload))

    return cases, skipped


def _location_matches(row: Dict[str, Any], expectation: Dict[str, Any]) -> bool:
    label = _normalize_text(((row.get("location") or {}).get("label"))).lower()
    country_code = _normalize_text(((row.get("location") or {}).get("country_code"))).upper()
    location_tokens = [
        _normalize_text(token).lower()
        for token in (expectation.get("location_tokens_any") or [])
        if _normalize_text(token)
    ]
    country_codes = {
        _normalize_text(code).upper()
        for code in (expectation.get("country_codes_any") or [])
        if _normalize_text(code)
    }
    token_match = bool(location_tokens) and any(token in label for token in location_tokens)
    country_match = bool(country_codes) and country_code in country_codes
    return token_match or country_match


def evaluate_scanner_case_result(case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    expectation = case.get("expectation") or {}
    rows = list(result.get("results") or [])
    minimum_results = int(expectation.get("minimum_results") or 1)
    max_rank = expectation.get("max_rank")
    max_rank_value = int(max_rank) if max_rank is not None else None

    matches: List[Dict[str, Any]] = []
    for row in rows:
        if not _location_matches(row, expectation):
            continue
        rank_value = int(row.get("rank") or 0)
        if max_rank_value is not None and rank_value > max_rank_value:
            continue
        matches.append(row)

    passed = len(rows) >= minimum_results and bool(matches)
    top_match = matches[0] if matches else None
    scores = [_row_scan_score(row) for row in rows]
    levels = [_normalize_text(row.get("level")).lower() for row in rows if _normalize_text(row.get("level"))]
    scan_levels = [
        _normalize_text(row.get("scan_level")).lower()
        for row in rows
        if _normalize_text(row.get("scan_level"))
    ]
    score_spread = (max(scores) - min(scores)) if scores else 0.0
    distinct_score_count = len({score for score in scores})
    top_score = scores[0] if scores else 0.0
    top_score_tie_count = sum(1 for score in scores if score == top_score)
    matched_score = _row_scan_score(top_match) if top_match else None
    warnings: List[str] = []
    if rows and all(score == 0.0 for score in scores):
        warnings.append("all_zero_scores")
    if rows and score_spread <= 0.0:
        warnings.append("no_score_separation")
    elif rows and distinct_score_count <= 2:
        warnings.append("low_score_variety")
    if scan_levels:
        if len(set(scan_levels)) <= 1 and rows:
            warnings.append("uniform_scan_levels")
    elif len(set(levels)) <= 1 and rows:
        warnings.append("uniform_levels")
    if top_match is not None and int(top_match.get("rank") or 0) > 1:
        warnings.append("expected_location_not_top_rank")
    if top_match is not None and max_rank_value is not None and int(top_match.get("rank") or 0) == max_rank_value:
        warnings.append("expected_location_at_rank_limit")
    if rows and top_score_tie_count > 1:
        warnings.append("top_score_tied")
    if bool(expectation.get("require_nonzero_top_score")) and top_score <= 0.0:
        warnings.append("expected_nonzero_top_score")
        passed = False
    if bool(expectation.get("require_scan_separation")):
        if any(
            warning in warnings
            for warning in ("all_zero_scores", "no_score_separation", "uniform_scan_levels", "uniform_levels")
        ):
            warnings.append("scan_separation_requirement_failed")
            passed = False
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
        "minimum_results": minimum_results,
        "returned": len(rows),
        "expected_max_rank": max_rank_value,
        "matched_rank": int(top_match.get("rank")) if top_match else None,
        "matched_location": ((top_match.get("location") or {}).get("label")) if top_match else None,
        "matched_score": matched_score,
        "top_score": top_score,
        "score_spread": score_spread,
        "distinct_score_count": distinct_score_count,
        "top_score_tie_count": top_score_tie_count,
        "warning_flags": warnings,
        "scan_levels": scan_levels,
        "top_locations": [((row.get("location") or {}).get("label")) for row in rows],
        "benchmark_refs": list(case.get("benchmark_refs") or []),
        "counts": result.get("counts") or {},
        "scan_calibration": result.get("scan_calibration") or {},
    }


def execute_scanner_case(
    case: Dict[str, Any],
    *,
    active_clock: ActiveClockContext = DEFAULT_ACTIVE_CLOCK,
) -> Dict[str, Any]:
    request_payload = dict(case.get("request") or {})
    request_model = build_scan_request(request_payload)

    # The underlying chart engine is noisy in dev; suppress stdout/stderr for benchmark runs.
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        result = run_scan(
            request_model,
            active_clock=active_clock,
            bundle_resolver=astro_clock_api._mundane_bundle_resolver,
        )
    return result


def run_scanner_benchmark_suite(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
    active_clock: ActiveClockContext = DEFAULT_ACTIVE_CLOCK,
) -> Dict[str, Any]:
    logging.getLogger("astro_clock_engine").setLevel(logging.ERROR)
    logging.getLogger("app").setLevel(logging.ERROR)

    cases, skipped = load_scanner_benchmark_cases(
        case_id=case_id,
        include_disabled=include_disabled,
    )

    case_results: List[Dict[str, Any]] = []
    pass_count = 0
    weak_pass_count = 0
    warning_counts: Dict[str, int] = {}
    for case in cases:
        scan_result = execute_scanner_case(case, active_clock=active_clock)
        evaluation = evaluate_scanner_case_result(case, scan_result)
        if evaluation["passed"]:
            pass_count += 1
        if evaluation["diagnostic_status"] == "weak_pass":
            weak_pass_count += 1
        for warning in evaluation.get("warning_flags") or []:
            warning_counts[warning] = int(warning_counts.get(warning) or 0) + 1
        evaluation["scan_result"] = scan_result
        case_results.append(evaluation)

    return {
        "dataset_path": str(Path(SCANNER_BENCHMARK_FILE).resolve()),
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


def format_scanner_benchmark_report(summary: Dict[str, Any]) -> str:
    lines = [
        "# Mundane Scanner Benchmarks",
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
                f"- matched rank: {item.get('matched_rank')}",
                f"- matched location: {item.get('matched_location') or 'none'}",
                f"- matched score: {item.get('matched_score')}",
                f"- top score: {item.get('top_score')}",
                f"- score spread: {item.get('score_spread')}",
                f"- distinct scores: {item.get('distinct_score_count')}",
                f"- returned rows: {item.get('returned')}",
                f"- scan levels: {', '.join(item.get('scan_levels') or []) or 'none'}",
                f"- warnings: {', '.join(item.get('warning_flags') or []) or 'none'}",
                f"- top locations: {', '.join(item.get('top_locations') or []) or 'none'}",
                f"- refs: {', '.join(item.get('benchmark_refs') or []) or 'none'}",
            ]
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run mundane scanner benchmark cases.")
    parser.add_argument("--case-id", help="Only run a single scanner benchmark case.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled scanner benchmark rows.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of markdown.")
    args = parser.parse_args(argv)

    summary = run_scanner_benchmark_suite(
        case_id=args.case_id,
        include_disabled=args.include_disabled,
    )

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_scanner_benchmark_report(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
