from __future__ import annotations

"""Compare the promoted Descendant-aspect policy with the pre-promotion baseline.

The canonical route supplies one feature/findings snapshot. The runner scores
that snapshot with both the frozen ``deduplicated_v2`` baseline and the current
production policy so a feature change cannot contaminate the comparison.
"""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
for import_path in (REPO_ROOT, REPO_ROOT / "backend"):
    value = str(import_path)
    if value not in sys.path:
        sys.path.insert(0, value)


from forensic.survivability import (  # noqa: E402
    DEFAULT_SURVIVABILITY_POLICY,
    compute_survivability,
)
from forensic_statistical_benchmark_runner import (  # noqa: E402
    DEFAULT_DATASET_PATHS,
    _call_forensic_route,
    _expected_survivability,
)


LOCKED_AVIATION_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_known_outcome_aviation_holdout_v1.json"
CONTAMINATED_RETROSPECTIVE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "forensic_holdout_30_cases_2026_05_20.json"
)
STRATIFIED_SURVIVABILITY_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "forensic_survivability_stratified_cases.json"
)
DEFAULT_COMPARISON_DATASETS = [
    *DEFAULT_DATASET_PATHS,
    LOCKED_AVIATION_PATH,
    CONTAMINATED_RETROSPECTIVE_PATH,
    STRATIFIED_SURVIVABILITY_PATH,
]
LEGACY_BASELINE_POLICY = replace(
    DEFAULT_SURVIVABILITY_POLICY,
    version="deduplicated_v2",
    descendant_aspects_enabled=False,
)
DESCENDANT_POLICY = DEFAULT_SURVIVABILITY_POLICY


def _case_id(case: Dict[str, Any], index: int) -> str:
    return str(case.get("id") or case.get("case_id") or f"case_{index}")


def _query(case: Dict[str, Any], *, use_secondary_factors: bool) -> Dict[str, str]:
    benchmark = case.get("benchmark") if isinstance(case.get("benchmark"), dict) else case
    query = dict(benchmark.get("query") or {})
    datetime_local = query.pop("datetime_local", None)
    if datetime_local is not None and "datetime" not in query:
        query["datetime"] = datetime_local
    query["secondary_factors"] = "1" if use_secondary_factors else "0"
    return {str(key): str(value) for key, value in query.items() if value is not None}


def _alignment(result: Dict[str, Any], expected: Dict[str, List[str]]) -> bool | None:
    levels = expected.get("levels") or []
    bands = expected.get("bands") or []
    if not levels or not bands:
        return None
    return result.get("level") in levels and result.get("outcome_band") in bands


def _change_status(baseline: bool | None, candidate: bool | None) -> str:
    if baseline is None or candidate is None:
        return "not_scored"
    if not baseline and candidate:
        return "improved"
    if baseline and not candidate:
        return "regressed"
    return "unchanged_aligned" if candidate else "unchanged_misaligned"


def _iter_cases(dataset_paths: Sequence[Path]) -> Iterable[tuple[Path, Dict[str, Any]]]:
    seen: set[str] = set()
    for dataset_path in dataset_paths:
        payload = json.loads(dataset_path.read_text(encoding="utf-8"))
        for index, case in enumerate(payload.get("cases") or []):
            case_id = _case_id(case, index)
            if case_id in seen:
                continue
            seen.add(case_id)
            yield dataset_path, case


def run_descendant_aspect_comparison(
    dataset_paths: Sequence[str | Path] | None = None,
    *,
    case_id: str | None = None,
    use_secondary_factors: bool = False,
) -> Dict[str, Any]:
    paths = [Path(path).resolve() for path in (dataset_paths or DEFAULT_COMPARISON_DATASETS)]
    rows: List[Dict[str, Any]] = []
    route_errors: List[Dict[str, Any]] = []

    for dataset_path, case in _iter_cases(paths):
        current_case_id = _case_id(case, len(rows))
        if case_id and current_case_id != case_id:
            continue
        query = _query(case, use_secondary_factors=use_secondary_factors)
        route_result = _call_forensic_route(query)
        payload = route_result.get("payload") or {}
        if route_result.get("status_code") != 200 or not payload.get("success"):
            route_errors.append(
                {
                    "case_id": current_case_id,
                    "status_code": route_result.get("status_code"),
                    "error": payload.get("error") or "route failed",
                }
            )
            continue

        benchmark = case.get("benchmark") if isinstance(case.get("benchmark"), dict) else case
        case_type = str((benchmark.get("query") or {}).get("case_type") or "general")
        scoring_findings = [
            finding
            for finding in (payload.get("findings") or [])
            if isinstance(finding, dict) and finding.get("scoring_eligible", True) is not False
        ]
        scoring_categories = payload.get("scoring_categories") or {}
        baseline = compute_survivability(
            payload.get("features") or {},
            findings=scoring_findings,
            categories=scoring_categories,
            case_type=case_type,
            policy=LEGACY_BASELINE_POLICY,
        )
        candidate = compute_survivability(
            payload.get("features") or {},
            findings=scoring_findings,
            categories=scoring_categories,
            case_type=case_type,
            policy=DESCENDANT_POLICY,
        )
        live_result = payload.get("survivability") or {}
        live_matches_candidate = all(
            live_result.get(key) == candidate.get(key)
            for key in ("level", "outcome_band", "score")
        )
        expected = _expected_survivability(case)
        baseline_aligned = _alignment(baseline, expected)
        candidate_aligned = _alignment(candidate, expected)
        impact = candidate.get("descendant_aspect_impact") or {}
        rows.append(
            {
                "case_id": current_case_id,
                "dataset": dataset_path.name,
                "expected": expected,
                "known_outcome": benchmark.get("known_outcome") or {},
                "baseline": {
                    "level": baseline.get("level"),
                    "band": baseline.get("outcome_band"),
                    "score": baseline.get("score"),
                    "aligned": baseline_aligned,
                },
                "candidate": {
                    "level": candidate.get("level"),
                    "band": candidate.get("outcome_band"),
                    "score": candidate.get("score"),
                    "aligned": candidate_aligned,
                },
                "change": _change_status(baseline_aligned, candidate_aligned),
                "live_route_matches_candidate": live_matches_candidate,
                "descendant_aspect_impact": impact,
            }
        )

    scored = [row for row in rows if row["baseline"]["aligned"] is not None]
    baseline_aligned_count = sum(row["baseline"]["aligned"] is True for row in scored)
    candidate_aligned_count = sum(row["candidate"]["aligned"] is True for row in scored)
    return {
        "experiment_id": "forensic_survivability_descendant_aspect_v1",
        "policy": {
            "baseline_version": LEGACY_BASELINE_POLICY.version,
            "version": DESCENDANT_POLICY.version,
            "live_default_changed": True,
            "scope": "hard Mars/Saturn/Uranus/Pluto contacts to the Descendant only",
            "phase_available": False,
        },
        "dataset_paths": [str(path) for path in paths],
        "secondary_factors_enabled": use_secondary_factors,
        "case_count": len(rows),
        "scored_case_count": len(scored),
        "route_errors": route_errors,
        "live_route_mismatch_count": sum(
            row["live_route_matches_candidate"] is not True for row in rows
        ),
        "baseline_aligned_count": baseline_aligned_count,
        "candidate_aligned_count": candidate_aligned_count,
        "baseline_accuracy": round(baseline_aligned_count / len(scored), 4) if scored else None,
        "candidate_accuracy": round(candidate_aligned_count / len(scored), 4) if scored else None,
        "change_counts": {
            status: sum(row["change"] == status for row in rows)
            for status in (
                "improved",
                "regressed",
                "unchanged_aligned",
                "unchanged_misaligned",
                "not_scored",
            )
        },
        "cases": rows,
        "limitations": [
            "Exploratory retrospective replay; not a blind or prospective validation.",
            "Mackenzie has no scored survivability target in its current fixture.",
            "Descendant applying or separating phase is unavailable in the static forensic feature payload.",
            "The locked aviation cases are reported as a regression stress check; this retrospective comparison is not external validation.",
            "The 30-case active-shooter set is contaminated retrospective development data and is reported only as a regression diagnostic.",
        ],
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Forensic Survivability Descendant-Aspect Comparison",
        "",
        f"- Policy: `{report['policy']['version']}` (promoted live default)",
        f"- Baseline: `{report['policy']['baseline_version']}`",
        f"- Cases: {report['case_count']} ({report['scored_case_count']} scored)",
        f"- Live-route mismatches: {report['live_route_mismatch_count']}",
        f"- Baseline exact alignment: {report['baseline_aligned_count']}/{report['scored_case_count']} ({report['baseline_accuracy']})",
        f"- Candidate exact alignment: {report['candidate_aligned_count']}/{report['scored_case_count']} ({report['candidate_accuracy']})",
        f"- Changes: `{report['change_counts']}`",
        "",
        "## Cases with Descendant contacts, applied pressure, or classification changes",
        "",
    ]
    for row in report["cases"]:
        impact = row.get("descendant_aspect_impact") or {}
        if not impact.get("contacts") and row.get("baseline") == row.get("candidate"):
            continue
        lines.append(
            f"- `{row['case_id']}`: "
            f"{row['baseline']['level']}/{row['baseline']['band']} ({row['baseline']['score']}) -> "
            f"{row['candidate']['level']}/{row['candidate']['band']} ({row['candidate']['score']}); "
            f"change={row['change']}; eligible={impact.get('harm_context_eligible')}; "
            f"descendant_fatal={impact.get('raw_fatal_pressure_delta', 0)}; "
            f"contacts={impact.get('contacts') or []}"
        )
    if report.get("route_errors"):
        lines.extend(["", "## Route errors", "", f"`{report['route_errors']}`"])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.get("limitations") or [])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", action="append", help="Fixture path; may be repeated.")
    parser.add_argument("--case-id")
    parser.add_argument("--secondary-factors", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_descendant_aspect_comparison(
        args.dataset,
        case_id=args.case_id,
        use_secondary_factors=args.secondary_factors,
    )
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_markdown(report))
    return 1 if report.get("route_errors") or report.get("live_route_mismatch_count") else 0


if __name__ == "__main__":
    raise SystemExit(main())
