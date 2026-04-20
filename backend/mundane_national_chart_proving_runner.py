from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from mundane_assets import get_polity_definitions
from mundane_models import ActiveClockContext, MundaneContextRequest
from mundane_service import resolve_context
from validate_mundane_benchmark_datasets import (
    NATIONAL_CHART_CANDIDATE_FILE,
    NATIONAL_CHART_PROVING_FILE,
    load_jsonl_cases,
    validate_historical_case,
    validate_national_chart_candidate_case,
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


def _normalize_id(value: Any) -> str:
    return _normalize_text(value).lower().replace(" ", "_")


def _time_prefix(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    if len(text) >= 5:
        return text[:5]
    return text


def _location_key(value: Any) -> str:
    text = _normalize_text(value).lower()
    if not text:
        return ""
    return text.split(",")[0].strip()


def _load_candidate_index() -> Dict[str, Dict[str, Any]]:
    candidate_index: Dict[str, Dict[str, Any]] = {}
    for payload in load_jsonl_cases(NATIONAL_CHART_CANDIDATE_FILE):
        validate_national_chart_candidate_case(payload, NATIONAL_CHART_CANDIDATE_FILE)
        candidate_id = _normalize_id(payload.get("candidate_id"))
        if candidate_id:
            candidate_index[candidate_id] = dict(payload)
    return candidate_index


def _index_polities() -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for polity in get_polity_definitions():
        polity_id = _normalize_id(polity.get("id"))
        if not polity_id:
            continue
        payload = dict(polity)
        indexed[polity_id] = payload
        aliases = polity.get("aliases") or []
        if isinstance(aliases, list):
            for alias in aliases:
                alias_id = _normalize_id(alias)
                if alias_id and alias_id not in indexed:
                    indexed[alias_id] = payload
    return indexed


def _resolve_runtime_chart_id(
    candidate_id: str,
    candidate_index: Mapping[str, Dict[str, Any]],
    indexed_polities: Mapping[str, Dict[str, Any]],
) -> Optional[str]:
    if candidate_id in indexed_polities:
        return candidate_id

    candidate = candidate_index.get(candidate_id)
    if not isinstance(candidate, dict):
        return None
    polity_id = _normalize_id(candidate.get("polity_id"))
    polity = indexed_polities.get(polity_id)
    if not isinstance(polity, dict):
        return None

    event = candidate.get("event") or {}
    candidate_date = _normalize_text(event.get("date"))
    candidate_time = _time_prefix(event.get("time"))
    candidate_location = _location_key(event.get("location"))

    charts = polity.get("national_charts") or []
    for chart in charts:
        chart_id = _normalize_id(chart.get("id"))
        if chart_id == candidate_id:
            return chart_id
        chart_datetime = _normalize_text(chart.get("datetime"))
        chart_date = chart_datetime[:10] if len(chart_datetime) >= 10 else ""
        chart_time = chart_datetime[11:16] if len(chart_datetime) >= 16 else ""
        chart_location = _location_key(chart.get("location"))
        if candidate_date and chart_date != candidate_date:
            continue
        if candidate_time and chart_time and chart_time != candidate_time:
            continue
        if candidate_location and chart_location and chart_location != candidate_location:
            continue
        if chart_id:
            return chart_id
    return None


def _case_requires_period_selection(case: Dict[str, Any]) -> bool:
    candidate_ids = [_normalize_id(item) for item in (case.get("candidate_ids") or []) if _normalize_id(item)]
    if len(candidate_ids) > 1:
        return True
    chart_basis = {_normalize_id(item) for item in (case.get("chart_basis") or []) if _normalize_id(item)}
    return bool(chart_basis & {"period_matched_context", "paired_founding_comparison"})


def load_national_chart_proving_cases(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cases: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()

    for payload in load_jsonl_cases(NATIONAL_CHART_PROVING_FILE):
        validate_historical_case(payload, NATIONAL_CHART_PROVING_FILE)
        if _normalize_id(payload.get("domain_id")) != "national_chart_proving":
            continue
        current_case_id = _normalize_text(payload.get("case_id"))
        if case_filter and current_case_id.lower() != case_filter:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            skipped.append({"case_id": current_case_id, "reason": "disabled"})
            continue
        cases.append(dict(payload))

    return cases, skipped


def _event_anchor_iso(case: Dict[str, Any]) -> str:
    event = case.get("event") or {}
    event_date = _normalize_text(event.get("date"))
    if not event_date:
        start_date = _normalize_text(event.get("start_date"))
        end_date = _normalize_text(event.get("end_date"))
        if start_date and end_date:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
            midpoint = start + timedelta(days=(end - start).days // 2)
            event_date = midpoint.isoformat()
        else:
            event_date = start_date
    if not event_date:
        raise ValueError(f"{case.get('case_id')} is missing an event date anchor")
    event_time = _normalize_text(event.get("time")) or "12:00:00"
    if len(event_time) == 5:
        event_time = f"{event_time}:00"
    return f"{event_date}T{event_time}"


def _infer_polity_id(
    case: Dict[str, Any],
    candidate_index: Mapping[str, Dict[str, Any]],
    indexed_polities: Mapping[str, Dict[str, Any]],
) -> str:
    preferred_candidate_id = _normalize_id(case.get("preferred_candidate_id"))
    if preferred_candidate_id:
        preferred_candidate = candidate_index.get(preferred_candidate_id)
        preferred_polity_id = _normalize_id((preferred_candidate or {}).get("polity_id"))
        if preferred_polity_id:
            return preferred_polity_id

    for candidate_id in case.get("candidate_ids") or []:
        normalized = _normalize_id(candidate_id)
        candidate = candidate_index.get(normalized)
        candidate_polity_id = _normalize_id((candidate or {}).get("polity_id"))
        if candidate_polity_id:
            return candidate_polity_id

    event = case.get("event") or {}
    event_polity = _normalize_id(event.get("polity"))
    if event_polity in indexed_polities:
        return event_polity
    raise ValueError(f"Unable to infer polity_id for proving case {case.get('case_id')}")


def execute_national_chart_proving_case(
    case: Dict[str, Any],
    *,
    active_clock: ActiveClockContext = DEFAULT_ACTIVE_CLOCK,
    candidate_index: Optional[Dict[str, Dict[str, Any]]] = None,
    indexed_polities: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    candidate_index = candidate_index or _load_candidate_index()
    indexed_polities = indexed_polities or _index_polities()
    polity_id = _infer_polity_id(case, candidate_index, indexed_polities)
    anchor_datetime = _event_anchor_iso(case)
    preferred_candidate_id = _normalize_id(case.get("preferred_candidate_id"))
    preferred_runtime_chart_id = _resolve_runtime_chart_id(preferred_candidate_id, candidate_index, indexed_polities)
    selection_mode = _case_requires_period_selection(case)

    request = MundaneContextRequest(
        chart_type="national_chart",
        polity_id=polity_id,
        location_context_type="national_chart",
        event_datetime=anchor_datetime,
        national_chart_id=None if selection_mode else preferred_runtime_chart_id,
    )
    context = resolve_context(request, active_clock=active_clock, bundle_resolver=None)
    return {
        "polity_id": polity_id,
        "anchor_datetime": anchor_datetime,
        "selection_mode": selection_mode,
        "preferred_runtime_chart_id": preferred_runtime_chart_id,
        "context": context.to_dict(),
    }


def evaluate_national_chart_proving_result(case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    context = (result.get("context") or {})
    reference_chart = (context.get("reference_chart") or {})
    selected_candidate_id = _normalize_id(reference_chart.get("id"))
    preferred_candidate_id = _normalize_id(case.get("preferred_candidate_id"))
    preferred_runtime_chart_id = _normalize_id(result.get("preferred_runtime_chart_id"))
    candidate_ids = [_normalize_id(item) for item in (case.get("candidate_ids") or []) if _normalize_id(item)]
    selection_basis = _normalize_id(reference_chart.get("selection_basis"))
    seed_quality = _normalize_id(case.get("seed_quality")) or "unspecified"
    selection_mode = bool(result.get("selection_mode"))

    warnings: List[str] = []
    passed = bool(preferred_runtime_chart_id) and selected_candidate_id == preferred_runtime_chart_id
    if selection_mode and selection_basis != "period_match":
        warnings.append("non_period_selection")
    if not selection_mode and selection_basis != "requested_chart_id":
        warnings.append("non_requested_selection")
    if seed_quality == "source_seeded":
        warnings.append("seeded_evidence")
    if not selection_basis:
        warnings.append("missing_selection_basis")
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
        "seed_quality": seed_quality,
        "polity_id": result.get("polity_id"),
        "anchor_datetime": result.get("anchor_datetime"),
        "selected_candidate_id": selected_candidate_id or None,
        "preferred_candidate_id": preferred_candidate_id or None,
        "preferred_runtime_chart_id": preferred_runtime_chart_id or None,
        "selection_basis": selection_basis or None,
        "candidate_ids": candidate_ids,
        "selection_mode": selection_mode,
        "warning_flags": warnings,
        "benchmark_refs": [
            _normalize_text(item.get("title"))
            for item in (case.get("source_assertions") or [])
            if isinstance(item, dict) and _normalize_text(item.get("title"))
        ],
    }


def run_national_chart_proving_benchmark_suite(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
    active_clock: ActiveClockContext = DEFAULT_ACTIVE_CLOCK,
) -> Dict[str, Any]:
    cases, skipped = load_national_chart_proving_cases(
        case_id=case_id,
        include_disabled=include_disabled,
    )
    candidate_index = _load_candidate_index()
    indexed_polities = _index_polities()

    results: List[Dict[str, Any]] = []
    pass_count = 0
    weak_pass_count = 0
    warning_counts: Dict[str, int] = {}
    seed_quality_counts: Dict[str, int] = {}

    for case in cases:
        execution = execute_national_chart_proving_case(
            case,
            active_clock=active_clock,
            candidate_index=candidate_index,
            indexed_polities=indexed_polities,
        )
        evaluation = evaluate_national_chart_proving_result(case, execution)
        if evaluation["passed"]:
            pass_count += 1
        if evaluation["diagnostic_status"] == "weak_pass":
            weak_pass_count += 1
        seed_quality = _normalize_id(evaluation.get("seed_quality"))
        seed_quality_counts[seed_quality] = int(seed_quality_counts.get(seed_quality) or 0) + 1
        for warning in evaluation.get("warning_flags") or []:
            warning_counts[warning] = int(warning_counts.get(warning) or 0) + 1
        results.append(evaluation)

    return {
        "dataset_path": str(Path(NATIONAL_CHART_PROVING_FILE).resolve()),
        "case_count": len(results),
        "pass_count": pass_count,
        "fail_count": len(results) - pass_count,
        "pass_rate": (pass_count / len(results)) if results else 0.0,
        "strong_pass_count": max(0, pass_count - weak_pass_count),
        "weak_pass_count": weak_pass_count,
        "warning_counts": dict(sorted(warning_counts.items())),
        "seed_quality_counts": dict(sorted(seed_quality_counts.items())),
        "skipped": skipped,
        "cases": results,
    }


def format_national_chart_proving_report(summary: Dict[str, Any]) -> str:
    lines = [
        "# Mundane National Chart Proving Benchmarks",
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
    seed_quality_counts = summary.get("seed_quality_counts") or {}
    if seed_quality_counts:
        lines.append(f"- seed quality counts: {json.dumps(seed_quality_counts, sort_keys=True)}")

    for item in summary.get("cases") or []:
        status = "PASS" if item.get("passed") else "FAIL"
        lines.extend(
            [
                "",
                f"## {status} {item.get('case_id')}",
                f"- label: {item.get('label')}",
                f"- diagnostic status: {item.get('diagnostic_status')}",
                f"- polity: {item.get('polity_id')}",
                f"- anchor datetime: {item.get('anchor_datetime')}",
                f"- selected candidate: {item.get('selected_candidate_id') or 'none'}",
                f"- preferred candidate: {item.get('preferred_candidate_id') or 'none'}",
                f"- selection basis: {item.get('selection_basis') or 'none'}",
                f"- seed quality: {item.get('seed_quality')}",
                f"- warnings: {', '.join(item.get('warning_flags') or []) or 'none'}",
                f"- refs: {', '.join(item.get('benchmark_refs') or []) or 'none'}",
            ]
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run national-chart proving benchmark cases.")
    parser.add_argument("--case-id", help="Only run a single proving case.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled proving rows.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    args = parser.parse_args(argv)

    summary = run_national_chart_proving_benchmark_suite(
        case_id=args.case_id,
        include_disabled=args.include_disabled,
    )
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_national_chart_proving_report(summary))
    return 0 if not summary.get("fail_count") else 1


if __name__ == "__main__":
    raise SystemExit(main())
