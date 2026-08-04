from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
for import_path in (BACKEND_ROOT, REPO_ROOT):
    value = str(import_path)
    if value not in sys.path:
        sys.path.insert(0, value)


import forensic_statistical_benchmark_runner as statistical_runner  # noqa: E402


DATASET_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_recent_documentaries_2025_2026_cases.json"
CASE_ID = "netflix_idaho_murders_college_nightmare_2026"


def load_idaho_case(dataset_path: Path = DATASET_PATH) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    case = next((item for item in payload.get("cases") or [] if item.get("id") == CASE_ID), None)
    if not isinstance(case, dict):
        raise ValueError(f"Case {CASE_ID!r} was not found in {dataset_path}")
    return payload, case


def evaluate_fact_check(check: Dict[str, Any], case_result: Dict[str, Any]) -> Dict[str, Any]:
    assertion = check.get("engine_assertion") or {}
    kind = assertion.get("kind")
    predicted_axes = set(case_result.get("predicted_axes") or [])

    if kind == "axis_present":
        axis = str(assertion.get("axis") or "")
        passed = axis in predicted_axes
        expected = f"axis {axis!r} present"
        actual = "present" if passed else "absent"
    elif kind == "axis_absent":
        axis = str(assertion.get("axis") or "")
        passed = axis not in predicted_axes
        expected = f"axis {axis!r} absent"
        actual = "absent" if passed else "present"
    elif kind == "survivability_matches_expected":
        survivability = case_result.get("survivability") or {}
        alignment = str(survivability.get("comparison") or "not_scored")
        passed = alignment == "aligned"
        expected = (
            f"{survivability.get('expected_levels') or []} / "
            f"{survivability.get('expected_bands') or []}"
        )
        actual = (
            f"{survivability.get('actual_level')} / {survivability.get('actual_band')} "
            f"(score {survivability.get('actual_score')}, {alignment})"
        )
    else:
        raise ValueError(f"Unsupported fact-check assertion kind: {kind!r}")

    return {
        "id": check.get("id"),
        "fact": check.get("fact"),
        "source_ids": list(check.get("source_ids") or []),
        "assertion_kind": kind,
        "expected_engine_signal": expected,
        "engine_output": actual,
        "status": "pass" if passed else "fail",
    }


def _run_time_anchor(case: Dict[str, Any], time_local: str) -> Dict[str, Any]:
    query = statistical_runner.build_forensic_query(case)
    date_local = str((case.get("event_anchor") or {}).get("date_local") or "")
    query["datetime"] = f"{date_local}T{time_local}"
    query["secondary_factors"] = "0"
    route_result = statistical_runner._call_forensic_route(query)
    payload = route_result.get("payload") or {}
    if route_result.get("status_code") != 200 or not payload.get("success"):
        return {
            "time_local": time_local,
            "status": "route_error",
            "status_code": route_result.get("status_code"),
            "error": payload.get("error"),
        }

    survivability = payload.get("survivability") or {}
    relationship = payload.get("relationship_status") or {}
    return {
        "time_local": time_local,
        "status": "ok",
        "predicted_axes": statistical_runner.derive_predicted_axes(payload),
        "survivability": {
            "level": survivability.get("level"),
            "band": survivability.get("outcome_band"),
            "score": survivability.get("score"),
        },
        "relationship_primary": relationship.get("primary_label"),
    }


def _anchor_signature(observation: Dict[str, Any]) -> str:
    comparable = {
        "predicted_axes": observation.get("predicted_axes"),
        "survivability": observation.get("survivability"),
        "relationship_primary": observation.get("relationship_primary"),
    }
    return json.dumps(comparable, sort_keys=True)


def _anchor_classification_signature(observation: Dict[str, Any]) -> str:
    survivability = observation.get("survivability") or {}
    comparable = {
        "predicted_axes": observation.get("predicted_axes"),
        "survivability": {
            "level": survivability.get("level"),
            "band": survivability.get("band"),
        },
        "relationship_primary": observation.get("relationship_primary"),
    }
    return json.dumps(comparable, sort_keys=True)


def run_idaho_benchmark(dataset_path: Path = DATASET_PATH) -> Dict[str, Any]:
    dataset, case = load_idaho_case(dataset_path)
    statistical_report = statistical_runner.run_statistical_benchmark_suite(
        [dataset_path],
        case_id=CASE_ID,
        include_control_cases=False,
        bootstrap_iterations=0,
    )

    route_errors = list(statistical_report.get("route_errors") or [])
    case_results = list(statistical_report.get("case_results") or [])
    if route_errors or not case_results:
        return {
            "benchmark_id": "forensic_idaho_college_nightmare_fact_comparison_v1",
            "case_id": CASE_ID,
            "overall_status": "route_error",
            "route_errors": route_errors,
            "fact_comparisons": [],
        }

    case_result = case_results[0]
    fact_checks = list(case.get("fact_checks") or [])
    if not fact_checks:
        raise ValueError(f"Case {CASE_ID!r} has no declared fact_checks")
    fact_comparisons = [evaluate_fact_check(check, case_result) for check in fact_checks]

    event_anchor = case.get("event_anchor") or {}
    anchor_observations = [
        _run_time_anchor(case, time_local)
        for time_local in event_anchor.get("sensitivity_times_local") or []
    ]
    anchor_errors = [item for item in anchor_observations if item.get("status") != "ok"]
    anchor_classification_signatures = {
        _anchor_classification_signature(item)
        for item in anchor_observations
        if item.get("status") == "ok"
    }
    anchor_score_signatures = {
        _anchor_signature(item)
        for item in anchor_observations
        if item.get("status") == "ok"
    }
    time_window_stable = (
        bool(anchor_observations)
        and not anchor_errors
        and len(anchor_classification_signatures) == 1
    )
    score_window_stable = (
        bool(anchor_observations)
        and not anchor_errors
        and len(anchor_score_signatures) == 1
    )

    scored_axes = {
        str((check.get("engine_assertion") or {}).get("axis"))
        for check in fact_checks
        if (check.get("engine_assertion") or {}).get("kind") in {"axis_present", "axis_absent"}
    }
    predicted_axes = list(case_result.get("predicted_axes") or [])
    declared_unscored = set((case.get("comparison_policy") or {}).get("unscored_outputs") or [])
    unscored_engine_outputs = [
        axis for axis in predicted_axes if axis not in scored_axes and axis in declared_unscored
    ]
    unclassified_engine_outputs = [
        axis for axis in predicted_axes if axis not in scored_axes and axis not in declared_unscored
    ]

    source_ids = set(case.get("documentary_source_ids") or []) | set(case.get("event_source_ids") or [])
    for check in fact_checks:
        source_ids.update(check.get("source_ids") or [])
    source_register = [
        {
            "id": source.get("id"),
            "kind": source.get("kind"),
            "title": source.get("title"),
            "url": source.get("url"),
        }
        for source in dataset.get("sources") or []
        if source.get("id") in source_ids
    ]

    passed = sum(item.get("status") == "pass" for item in fact_comparisons)
    total = len(fact_comparisons)
    overall_status = "pass" if passed == total and time_window_stable and not unclassified_engine_outputs else "fail"
    relationship = case_result.get("relationship") or {}
    return {
        "benchmark_id": "forensic_idaho_college_nightmare_fact_comparison_v1",
        "case_id": CASE_ID,
        "title": case.get("title"),
        "evaluation_role": dataset.get("evaluation_role"),
        "overall_status": overall_status,
        "summary": {
            "hard_checks_passed": passed,
            "hard_checks_total": total,
            "time_window_stable": time_window_stable,
            "score_window_stable": score_window_stable,
            "route_error_count": len(route_errors) + len(anchor_errors),
        },
        "event_anchor": event_anchor,
        "known_facts": case.get("known_facts") or {},
        "known_outcome": case.get("known_outcome") or {},
        "fact_comparisons": fact_comparisons,
        "engine_result": case_result,
        "unscored_engine_outputs": unscored_engine_outputs,
        "unclassified_engine_outputs": unclassified_engine_outputs,
        "relationship_observation": {
            "documented_target": case.get("relationship_target") or {},
            "engine_primary": relationship.get("predicted_primary"),
            "status": "not_scored",
        },
        "time_sensitivity": {
            "stable": time_window_stable,
            "classification_stable": time_window_stable,
            "score_stable": score_window_stable,
            "observations": anchor_observations,
        },
        "source_register": source_register,
        "limitations": [
            "This is a retrospective, in-sample regression benchmark, not a blind or prospective test.",
            "The event time is the midpoint of an official incident interval, not an asserted exact time of death.",
            "Classification is stable across the interval; the raw symbolic score may vary as the Descendant moves.",
            (
                "A passed symbolic category check is not evidence that astrology can identify "
                "a crime, person, motive, or legal fact."
            ),
            "Unverified engine outputs are reported separately and do not receive factual credit.",
        ],
    }


def _markdown_cell(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True)
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown_report(report: Dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines: List[str] = [
        f"# {report.get('title') or 'Idaho benchmark'} — engine output versus facts",
        "",
        f"- Overall status: **{report.get('overall_status')}**",
        (
            f"- Hard factual checks: {summary.get('hard_checks_passed')}/"
            f"{summary.get('hard_checks_total')} passed"
        ),
        f"- Official-window classification stability: {summary.get('time_window_stable')}",
        f"- Official-window raw-score stability: {summary.get('score_window_stable')}",
        f"- Route errors: {summary.get('route_error_count')}",
        "",
        "## Fact comparison",
        "",
        "| Check | Source-backed fact | Expected engine signal | Actual engine output | Result |",
        "|---|---|---|---|---|",
    ]
    for item in report.get("fact_comparisons") or []:
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    item.get("id"),
                    item.get("fact"),
                    item.get("expected_engine_signal"),
                    item.get("engine_output"),
                    item.get("status"),
                )
            )
            + " |"
        )

    engine_result = report.get("engine_result") or {}
    survivability = engine_result.get("survivability") or {}
    relationship = report.get("relationship_observation") or {}
    lines.extend(
        [
            "",
            "## Engine observations",
            "",
            f"- Predicted axes: `{engine_result.get('predicted_axes') or []}`",
            (
                f"- Survivability: `{survivability.get('actual_level')} / "
                f"{survivability.get('actual_band')}` (score `{survivability.get('actual_score')}`)"
            ),
            (
                f"- Relationship: `{relationship.get('engine_primary')}` — observational only, "
                "not included in the hard score"
            ),
            f"- Declared unscored outputs: `{report.get('unscored_engine_outputs') or []}`",
            f"- Undeclared extra outputs: `{report.get('unclassified_engine_outputs') or []}`",
            "",
            "## Official time-window sensitivity",
            "",
            "| Local time | Axes | Survivability | Relationship |",
            "|---|---|---|---|",
        ]
    )
    for observation in (report.get("time_sensitivity") or {}).get("observations") or []:
        survival = observation.get("survivability") or {}
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    observation.get("time_local"),
                    observation.get("predicted_axes") or observation.get("error"),
                    f"{survival.get('level')} / {survival.get('band')} ({survival.get('score')})",
                    observation.get("relationship_primary"),
                )
            )
            + " |"
        )

    lines.extend(["", "## Sources", ""])
    for source in report.get("source_register") or []:
        lines.append(f"- [{source.get('title')}]({source.get('url')}) — `{source.get('kind')}`")

    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.get("limitations") or [])
    return "\n".join(lines).strip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare the Forensic engine with source-backed Idaho murders facts."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)

    report = run_idaho_benchmark()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown_report(report))
    return 0 if report.get("overall_status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
