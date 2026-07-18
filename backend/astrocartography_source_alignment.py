from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from astrocartography_goal_engine import evaluate_goal_model, extract_relocation_features
from astrocartography_goal_models import list_goal_models


DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "benchmarks" / "astrocartography" / "source_alignment_cases.jsonl"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _read_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        yield line_number, payload


def _validate_case_contract(
    case: Dict[str, Any],
    *,
    path: Path,
    line_number: int,
) -> None:
    prefix = f"{path}:{line_number}"
    if case.get("fixture_policy") != "minimal_source_signal_v2":
        raise ValueError(
            f"{prefix}: source-alignment cases must use minimal_source_signal_v2"
        )
    source = case.get("source")
    if not isinstance(source, dict):
        raise ValueError(f"{prefix}: source must be an object")
    for field in ("claim_id", "classification", "claim", "refs", "normalized_file"):
        if source.get(field) in (None, "", []):
            raise ValueError(f"{prefix}: source.{field} is required")
    if source.get("classification") not in {"direct", "synthesis"}:
        raise ValueError(
            f"{prefix}: semantic fixtures require direct or synthesis provenance"
        )
    refs = source.get("refs")
    if not isinstance(refs, list):
        raise ValueError(f"{prefix}: source.refs must be a list")
    for ref in refs:
        if not isinstance(ref, dict):
            raise ValueError(f"{prefix}: source.refs entries must be objects")
        for field in ("source_id", "page", "page_id", "chunk_id"):
            if ref.get(field) in (None, ""):
                raise ValueError(f"{prefix}: source ref missing {field}")

    natal_rows = case.get("natal_rows") or []
    natal_crossings = case.get("natal_crossings") or []
    relocation_planets = case.get("relocation_planets") or {}
    if not isinstance(natal_rows, list) or len(natal_rows) > 1:
        raise ValueError(
            f"{prefix}: minimal fixtures may contain at most one natal line"
        )
    if natal_crossings:
        raise ValueError(
            f"{prefix}: minimal fixtures must not bake in crossing evidence"
        )
    if relocation_planets:
        raise ValueError(
            f"{prefix}: minimal fixtures must not bake in relocation evidence"
        )


def load_source_alignment_cases(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cases: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()

    for raw_path in dataset_paths or [DEFAULT_DATASET_PATH]:
        path = Path(raw_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Source-alignment dataset not found: {path}")
        for line_number, payload in _read_jsonl(path):
            current_case_id = _normalize_text(payload.get("case_id")) or f"line-{line_number}"
            if case_filter and current_case_id.lower() != case_filter:
                continue
            if not include_disabled and not bool(payload.get("enabled")):
                skipped.append(
                    {
                        "dataset": str(path),
                        "line_number": line_number,
                        "case_id": current_case_id,
                        "reason": "disabled",
                    }
                )
                continue
            case = dict(payload)
            case["_dataset_path"] = str(path)
            case["_line_number"] = line_number
            _validate_case_contract(case, path=path, line_number=line_number)
            cases.append(case)
    return cases, skipped


def _line(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = _normalize_text(payload.get("body") or payload.get("planet"))
    angle = _normalize_text(payload.get("angle")).upper()
    if not body or not angle:
        raise ValueError(f"Invalid natal row payload: {payload!r}")
    distance_km = float(payload.get("distance_km") or 0.0)
    return {
        "id": f"{body}:{angle}:{distance_km}",
        "body": body,
        "angle": angle,
        "label": f"{body} {angle}",
        "distance_km": distance_km,
        "zone": "primary" if distance_km <= 300 else "extended",
    }


def _crossing(payload: Dict[str, Any]) -> Dict[str, Any]:
    planets = payload.get("planets") or payload.get("pair") or []
    if not isinstance(planets, list) or len(planets) < 2:
        raise ValueError(f"Invalid crossing payload: {payload!r}")
    normalized_planets = [_normalize_text(item) for item in planets if _normalize_text(item)]
    if len(normalized_planets) < 2:
        raise ValueError(f"Invalid crossing payload: {payload!r}")
    distance_km = float(payload.get("distance_km") or 0.0)
    return {
        "id": f"{'|'.join(sorted(normalized_planets))}:{distance_km}",
        "planets": normalized_planets,
        "label": " x ".join(normalized_planets),
        "distance_km": distance_km,
        "zone": "primary" if distance_km <= 300 else "extended",
    }


def _relocation_features(payload: Dict[str, Any]) -> Dict[str, Any]:
    planets = payload.get("planets") if isinstance(payload, dict) else None
    if planets is None:
        planets = payload
    if not isinstance(planets, dict):
        raise ValueError(f"Invalid relocation payload: {payload!r}")
    normalized = {
        _normalize_text(name): {"house": int(house)}
        for name, house in planets.items()
        if _normalize_text(name)
    }
    return extract_relocation_features({"planets": normalized})


def _active_goal_models() -> List[Dict[str, Any]]:
    models = []
    for model in list_goal_models():
        if str(model.get("status") or "").strip().lower() != "active":
            continue
        models.append(model)
    models.sort(key=lambda item: str(item.get("id") or ""))
    return models


def _rank_case(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    natal_rows = [_line(item) for item in (case.get("natal_rows") or [])]
    natal_crossings = [_crossing(item) for item in (case.get("natal_crossings") or [])]
    relocation = _relocation_features(case.get("relocation_planets") or {})
    ranked: List[Dict[str, Any]] = []

    for model in _active_goal_models():
        goal_id = str(model.get("id") or "").strip().lower()
        evaluation = evaluate_goal_model(
            goal_id,
            natal_rows=natal_rows,
            natal_crossings=natal_crossings,
            relocation=relocation,
        )
        ranked.append(
            {
                "goal_id": goal_id,
                "label": model.get("label"),
                "score": int(evaluation.get("score") or 0),
                "raw_score": float(evaluation.get("raw_score") or 0.0),
                "breakdown": evaluation.get("breakdown") or {},
                "top_supports": evaluation.get("top_supports") or [],
                "top_cautions": evaluation.get("top_cautions") or [],
            }
        )

    ranked.sort(key=lambda item: (-int(item.get("score") or 0), -float(item.get("raw_score") or 0.0), str(item.get("goal_id") or "")))
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def _evaluate_expectations(
    case: Dict[str, Any],
    ranking: Sequence[Dict[str, Any]],
    *,
    default_top_k: int = 5,
) -> List[Dict[str, Any]]:
    failures: List[Dict[str, Any]] = []
    case_id = _normalize_text(case.get("case_id")) or "unknown"
    if not ranking:
        return [
            {
                "case_id": case_id,
                "expectation": "non_empty_ranking",
                "detail": "No goal scores were produced for this case.",
            }
        ]

    rank_by_goal = {str(item.get("goal_id") or ""): item for item in ranking}
    top_k = int(case.get("top_k") or default_top_k)
    top_ids = [str(item.get("goal_id") or "") for item in ranking[:top_k]]

    expected_lead = _normalize_text(case.get("expected_lead")).lower()
    if expected_lead:
        actual_lead = str(ranking[0].get("goal_id") or "").lower()
        if actual_lead != expected_lead:
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "expected_lead",
                    "detail": f"Expected {expected_lead} to lead but observed {actual_lead}.",
                }
            )
        else:
            lead_raw = float(ranking[0].get("raw_score") or 0.0)
            runner_raw = max(
                (
                    float(item.get("raw_score") or 0.0)
                    for item in ranking[1:]
                ),
                default=float("-inf"),
            )
            required_gap = float(case.get("minimum_lead_raw_gap") or 0.0)
            observed_gap = lead_raw - runner_raw
            if observed_gap <= 0.0 or observed_gap + 1e-12 < required_gap:
                failures.append(
                    {
                        "case_id": case_id,
                        "expectation": "strict_expected_lead",
                        "detail": (
                            f"Expected {expected_lead} to lead without a raw-score "
                            f"tie and by at least {required_gap:g}; observed gap "
                            f"{observed_gap:g}."
                        ),
                    }
                )

    for goal_id in case.get("expected_in_top") or []:
        expected_goal = _normalize_text(goal_id).lower()
        if expected_goal and expected_goal not in top_ids:
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "expected_in_top",
                    "detail": f"Expected {expected_goal} in top {top_k}, observed {top_ids}.",
                }
            )

    for goal_id in case.get("disallowed_in_top") or []:
        disallowed_goal = _normalize_text(goal_id).lower()
        if disallowed_goal and disallowed_goal in top_ids:
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "disallowed_in_top",
                    "detail": f"Did not expect {disallowed_goal} in top {top_k}, observed {top_ids}.",
                }
            )

    for relation in case.get("expected_above") or []:
        if not isinstance(relation, dict):
            raise ValueError(f"Case {case_id}: expected_above entries must be objects")
        higher = _normalize_text(relation.get("higher")).lower()
        lower = _normalize_text(relation.get("lower")).lower()
        if not higher or not lower:
            raise ValueError(f"Case {case_id}: expected_above entries require higher and lower")
        higher_rank = rank_by_goal.get(higher)
        lower_rank = rank_by_goal.get(lower)
        if higher_rank is None or lower_rank is None:
            missing = higher if higher_rank is None else lower
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "expected_above",
                    "detail": f"Ranking is missing goal {missing}.",
                }
            )
            continue
        higher_raw = float(higher_rank.get("raw_score") or 0.0)
        lower_raw = float(lower_rank.get("raw_score") or 0.0)
        required_gap = float(relation.get("min_raw_gap") or 0.0)
        observed_gap = higher_raw - lower_raw
        if (
            int(higher_rank.get("rank") or 0) >= int(lower_rank.get("rank") or 0)
            or observed_gap <= 0.0
            or observed_gap + 1e-12 < required_gap
        ):
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "expected_above",
                    "detail": (
                        f"Expected {higher} strictly above {lower} with raw-score "
                        f"gap at least {required_gap:g}; observed ranks "
                        f"{higher_rank.get('rank')} and {lower_rank.get('rank')} "
                        f"and raw gap {observed_gap:g}."
                    ),
                }
            )

    for expectation in case.get("expected_rank_at_most") or []:
        if not isinstance(expectation, dict):
            raise ValueError(
                f"Case {case_id}: expected_rank_at_most entries must be objects"
            )
        goal_id = _normalize_text(expectation.get("goal_id")).lower()
        maximum_rank = int(expectation.get("rank") or 0)
        ranked_goal = rank_by_goal.get(goal_id)
        if (
            not goal_id
            or maximum_rank < 1
            or ranked_goal is None
            or int(ranked_goal.get("rank") or 0) > maximum_rank
        ):
            observed_rank = ranked_goal.get("rank") if ranked_goal else "missing"
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "expected_rank_at_most",
                    "detail": (
                        f"Expected {goal_id or '<missing>'} at rank "
                        f"{maximum_rank} or better; observed {observed_rank}."
                    ),
                }
            )

    for expectation in case.get("expected_raw_bounds") or []:
        if not isinstance(expectation, dict):
            raise ValueError(
                f"Case {case_id}: expected_raw_bounds entries must be objects"
            )
        goal_id = _normalize_text(expectation.get("goal_id")).lower()
        ranked_goal = rank_by_goal.get(goal_id)
        if ranked_goal is None:
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "expected_raw_bounds",
                    "detail": f"Ranking is missing goal {goal_id}.",
                }
            )
            continue
        raw_score = float(ranked_goal.get("raw_score") or 0.0)
        minimum = expectation.get("min")
        maximum = expectation.get("max")
        if minimum is not None and raw_score < float(minimum):
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "expected_raw_bounds",
                    "detail": (
                        f"Expected {goal_id} raw score >= {float(minimum):g}; "
                        f"observed {raw_score:g}."
                    ),
                }
            )
        if maximum is not None and raw_score > float(maximum):
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "expected_raw_bounds",
                    "detail": (
                        f"Expected {goal_id} raw score <= {float(maximum):g}; "
                        f"observed {raw_score:g}."
                    ),
                }
            )

    if case.get("expected_all_raw_zero"):
        nonzero = [
            (str(item.get("goal_id") or ""), float(item.get("raw_score") or 0.0))
            for item in ranking
            if abs(float(item.get("raw_score") or 0.0)) > 1e-12
        ]
        if nonzero:
            failures.append(
                {
                    "case_id": case_id,
                    "expectation": "expected_all_raw_zero",
                    "detail": f"Expected a neutral ranking; non-zero goals: {nonzero}.",
                }
            )

    return failures


def run_source_alignment_suite(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
    default_top_k: int = 5,
) -> Dict[str, Any]:
    cases, skipped = load_source_alignment_cases(dataset_paths, case_id=case_id, include_disabled=include_disabled)
    active_models = _active_goal_models()
    report_cases: List[Dict[str, Any]] = []
    expectation_failures: List[Dict[str, Any]] = []

    for case in cases:
        ranking = _rank_case(case)
        failures = _evaluate_expectations(case, ranking, default_top_k=default_top_k)
        expectation_failures.extend(failures)
        report_cases.append(
            {
                "case_id": case.get("case_id"),
                "label": case.get("label"),
                "dataset": case.get("_dataset_path"),
                "line_number": case.get("_line_number"),
                "source": case.get("source") or {},
                "expected_lead": case.get("expected_lead"),
                "expected_in_top": case.get("expected_in_top") or [],
                "disallowed_in_top": case.get("disallowed_in_top") or [],
                "expected_above": case.get("expected_above") or [],
                "expected_rank_at_most": case.get("expected_rank_at_most") or [],
                "expected_raw_bounds": case.get("expected_raw_bounds") or [],
                "expected_all_raw_zero": bool(case.get("expected_all_raw_zero")),
                "top_k": int(case.get("top_k") or default_top_k),
                "top_results": ranking[: int(case.get("top_k") or default_top_k)],
                "failures": failures,
                "fixture_type": "synthetic_semantic_claim",
                "semantic_only": True,
            }
        )

    return {
        "dataset_paths": [str(Path(path).resolve()) for path in (dataset_paths or [DEFAULT_DATASET_PATH])],
        "case_count": len(report_cases),
        "goal_count": len(active_models),
        "cases": report_cases,
        "expectation_failures": expectation_failures,
        "semantic_gate_passed": not expectation_failures,
        "skipped": skipped,
        "validation_scope": {
            "fixture_type": "synthetic_semantic_claims",
            "semantic_only": True,
            "outcome_validation": False,
            "public_specialist_gate": "experimental",
            "promotion_requirement": "positive held-out lift on person-grouped historical outcomes",
        },
    }


def render_markdown_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Astrocartography Source Alignment")
    lines.append("")
    lines.append(f"- Cases: {int(report.get('case_count') or 0)}")
    lines.append(f"- Active goals: {int(report.get('goal_count') or 0)}")
    lines.append(f"- Expectation failures: {len(report.get('expectation_failures') or [])}")
    lines.append("- Scope: synthetic semantic fixtures only; this is not outcome validation.")
    lines.append("- Public specialist gate: experimental until positive held-out lift.")
    lines.append("")
    for dataset_path in report.get("dataset_paths") or []:
        lines.append(f"- Dataset: `{dataset_path}`")

    skipped = report.get("skipped") or []
    if skipped:
        lines.append("")
        lines.append("## Skipped")
        lines.append("")
        for item in skipped:
            lines.append(f"- {item.get('case_id')}: {item.get('reason')}")

    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for case in report.get("cases") or []:
        case_id = case.get("case_id")
        label = case.get("label") or case_id
        expected = _normalize_text(case.get("expected_lead")) or "n/a"
        top_results = case.get("top_results") or []
        observed = ", ".join(f"{item.get('goal_id')} ({item.get('score')})" for item in top_results[:3]) or "none"
        lines.append(f"### {label}")
        lines.append("")
        lines.append(f"- Case ID: `{case_id}`")
        lines.append(f"- Expected lead: `{expected}`")
        lines.append(f"- Observed top results: {observed}")
        source = case.get("source") or {}
        claim = _normalize_text(source.get("claim"))
        if claim:
            lines.append(f"- Source claim: {claim}")
        raw_file = _normalize_text(source.get("raw_file"))
        if raw_file:
            lines.append(f"- Raw source: `{raw_file}`")
        normalized_file = _normalize_text(source.get("normalized_file"))
        if normalized_file:
            lines.append(f"- Normalized source: `{normalized_file}`")
        pages = source.get("pages") or []
        if pages:
            lines.append(f"- Pages: {pages}")
        failures = case.get("failures") or []
        if failures:
            lines.append("- Status: FAIL")
            for failure in failures:
                lines.append(f"  - {failure.get('expectation')}: {failure.get('detail')}")
        else:
            lines.append("- Status: PASS")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate astrocartography goal models against curated source-backed claim cases.")
    parser.add_argument("--dataset", action="append", default=[], help="Path to a source-alignment JSONL dataset. Repeat for multiple datasets.")
    parser.add_argument("--case-id", help="Run only one case_id from the dataset.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled cases.")
    parser.add_argument("--top-k", type=int, default=5, help="Default top-k window for in-top expectations.")
    parser.add_argument("--output-json", help="Optional path to write the full report as JSON.")
    parser.add_argument("--output-md", help="Optional path to write the markdown summary.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    dataset_paths = args.dataset or [DEFAULT_DATASET_PATH]
    report = run_source_alignment_suite(
        dataset_paths,
        case_id=args.case_id,
        include_disabled=args.include_disabled,
        default_top_k=args.top_k,
    )
    markdown = render_markdown_report(report)
    print(markdown, end="")

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(markdown, encoding="utf-8")

    return 1 if report.get("expectation_failures") else 0


if __name__ == "__main__":
    raise SystemExit(main())
