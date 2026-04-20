from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mundane_models import ActiveClockContext, MundaneContextRequest, ResolvedMundaneContext
from mundane_trigger_rules import index_trigger_profiles
from validate_mundane_benchmark_datasets import (
    TRIGGER_PROFILE_BENCHMARK_FILE,
    load_jsonl_cases,
    validate_source_alignment_case,
    validate_trigger_profile_case,
    SOURCE_ALIGNMENT_FILE,
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


def _load_source_alignment_case_ids() -> set[str]:
    case_ids: set[str] = set()
    for payload in load_jsonl_cases(SOURCE_ALIGNMENT_FILE):
        validate_source_alignment_case(payload, SOURCE_ALIGNMENT_FILE)
        case_id = _normalize_text(payload.get("case_id"))
        if case_id:
            case_ids.add(case_id)
    return case_ids


def load_trigger_benchmark_cases(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    source_alignment_case_ids = _load_source_alignment_case_ids()
    cases: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()

    for payload in load_jsonl_cases(TRIGGER_PROFILE_BENCHMARK_FILE):
        validate_trigger_profile_case(payload, TRIGGER_PROFILE_BENCHMARK_FILE, source_alignment_case_ids)
        current_case_id = _normalize_text(payload.get("case_id"))
        if case_filter and current_case_id.lower() != case_filter:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            skipped.append({"case_id": current_case_id, "reason": "disabled"})
            continue
        cases.append(dict(payload))

    return cases, skipped


def _build_context(case: Dict[str, Any], *, active_clock: ActiveClockContext) -> ResolvedMundaneContext:
    context_payload = dict(case.get("context") or {})
    chart_type_id = _normalize_text(context_payload.get("chart_type")) or "war_event"
    domain_id = _normalize_text(context_payload.get("domain")) or "war_outbreak"
    location_context_id = _normalize_text(context_payload.get("location_context_type")) or "event_chart"
    polity_id = _normalize_text(context_payload.get("polity_id")) or "france"
    chart_resolution = dict(context_payload.get("chart_resolution") or {})

    request = MundaneContextRequest(
        chart_type=chart_type_id,
        domain=domain_id,
        polity_id=polity_id,
        location_context_type=location_context_id,
    )
    return ResolvedMundaneContext(
        request=request,
        active_clock=active_clock,
        chart_type={"id": chart_type_id, "label": chart_type_id},
        domain={"id": domain_id, "label": domain_id},
        location_context={"id": location_context_id, "label": location_context_id},
        polity={"id": polity_id, "label": polity_id.replace("_", " ").title(), "capital": active_clock.location, "default_location": active_clock.location},
        reference_chart=None,
        event_context={"location_context_type": location_context_id, "reference_location": active_clock.location},
        chart_resolution=chart_resolution,
        research_flags=["benchmark_backed"],
        source_tags=[],
    )


def evaluate_trigger_case_result(case: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    expectation = dict(case.get("expectation") or {})
    failed_checks: List[str] = []

    if "status" in expectation and _normalize_text(profile.get("status")) != _normalize_text(expectation.get("status")):
        failed_checks.append("status_mismatch")
    if "active" in expectation and bool(profile.get("active")) is not bool(expectation.get("active")):
        failed_checks.append("active_mismatch")
    if float(profile.get("score") or 0.0) < float(expectation.get("minimum_score") or 0.0):
        failed_checks.append("score_below_minimum")
    allowed_strengths = [_normalize_text(item).lower() for item in (expectation.get("allowed_strengths") or []) if _normalize_text(item)]
    if allowed_strengths and _normalize_text(profile.get("strength")).lower() not in allowed_strengths:
        failed_checks.append("strength_not_allowed")
    minimum_evidence_count = int(expectation.get("minimum_evidence_count") or 0)
    if len(profile.get("evidence") or []) < minimum_evidence_count:
        failed_checks.append("evidence_below_minimum")

    metrics = profile.get("metrics") if isinstance(profile.get("metrics"), dict) else {}
    for key, expected_value in (expectation.get("required_metric_values") or {}).items():
        if metrics.get(key) != expected_value:
            failed_checks.append(f"metric_mismatch:{key}")

    passed = not failed_checks
    diagnostic_status = "strong_pass" if passed else "fail"
    return {
        "case_id": case.get("case_id"),
        "label": case.get("label"),
        "trigger_id": case.get("trigger_id"),
        "passed": passed,
        "diagnostic_status": diagnostic_status,
        "status": profile.get("status"),
        "active": bool(profile.get("active")),
        "strength": profile.get("strength"),
        "score": int(profile.get("score") or 0),
        "evidence_count": len(profile.get("evidence") or []),
        "metrics": metrics,
        "failed_checks": failed_checks,
        "benchmark_refs": list(case.get("benchmark_refs") or []),
    }


def execute_trigger_case(
    case: Dict[str, Any],
    *,
    active_clock: ActiveClockContext = DEFAULT_ACTIVE_CLOCK,
) -> Dict[str, Any]:
    context = _build_context(case, active_clock=active_clock)
    trigger_id = _normalize_text(case.get("trigger_id"))
    return index_trigger_profiles(context, trigger_ids=[trigger_id]).get(trigger_id, {})


def run_trigger_benchmark_suite(
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
    active_clock: ActiveClockContext = DEFAULT_ACTIVE_CLOCK,
) -> Dict[str, Any]:
    cases, skipped = load_trigger_benchmark_cases(case_id=case_id, include_disabled=include_disabled)
    case_results: List[Dict[str, Any]] = []
    pass_count = 0
    for case in cases:
        profile = execute_trigger_case(case, active_clock=active_clock)
        evaluation = evaluate_trigger_case_result(case, profile)
        if evaluation["passed"]:
            pass_count += 1
        evaluation["profile"] = profile
        case_results.append(evaluation)

    return {
        "dataset_path": str(Path(TRIGGER_PROFILE_BENCHMARK_FILE).resolve()),
        "case_count": len(case_results),
        "pass_count": pass_count,
        "fail_count": len(case_results) - pass_count,
        "pass_rate": (pass_count / len(case_results)) if case_results else 0.0,
        "skipped": skipped,
        "cases": case_results,
    }


def format_trigger_benchmark_report(summary: Dict[str, Any]) -> str:
    lines = [
        "# Mundane Trigger Benchmarks",
        "",
        f"- dataset: `{summary.get('dataset_path')}`",
        f"- cases: {summary.get('case_count')}",
        f"- passed: {summary.get('pass_count')}",
        f"- failed: {summary.get('fail_count')}",
        f"- pass rate: {summary.get('pass_rate', 0.0):.2%}",
    ]
    for item in summary.get("cases") or []:
        status = "PASS" if item.get("passed") else "FAIL"
        lines.extend(
            [
                "",
                f"## {status} {item.get('case_id')}",
                f"- label: {item.get('label')}",
                f"- trigger: {item.get('trigger_id')}",
                f"- diagnostic status: {item.get('diagnostic_status')}",
                f"- status: {item.get('status')}",
                f"- active: {item.get('active')}",
                f"- strength: {item.get('strength')}",
                f"- score: {item.get('score')}",
                f"- evidence count: {item.get('evidence_count')}",
                f"- failed checks: {', '.join(item.get('failed_checks') or []) or 'none'}",
                f"- refs: {', '.join(item.get('benchmark_refs') or []) or 'none'}",
            ]
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run mundane trigger benchmark cases.")
    parser.add_argument("--case-id", help="Only run a single trigger benchmark case.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled trigger benchmark rows.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    args = parser.parse_args(argv)

    summary = run_trigger_benchmark_suite(case_id=args.case_id, include_disabled=args.include_disabled)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_trigger_benchmark_report(summary))
    return 0 if not summary.get("fail_count") else 1


if __name__ == "__main__":
    raise SystemExit(main())
