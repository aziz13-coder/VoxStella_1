from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from forensic.house_system import (
    DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE,
    FORENSIC_HOUSE_SYSTEM_LABELS,
    FORENSIC_HOUSE_SYSTEM_SELECTION_VERSION,
    FORENSIC_HOUSE_SYSTEM_SELECTION_WEIGHTS,
    SUPPORTED_FORENSIC_HOUSE_SYSTEM_CODES,
    forensic_house_system_selection_score,
    normalize_forensic_house_system_code,
)
from forensic.tuning import assert_tuning_eligible
from forensic_statistical_benchmark_runner import (
    DEFAULT_DATASET_PATHS,
    REPO_ROOT,
    run_statistical_benchmark_suite,
)


def _resolve_dataset_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def assert_house_selection_datasets_eligible(paths: Sequence[str | Path]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for raw_path in paths:
        path = _resolve_dataset_path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"Forensic house-system dataset not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Forensic house-system dataset must contain a JSON object: {path}")
        role = assert_tuning_eligible(payload, path)
        rows.append({"path": str(path), "evaluation_role": role})
    return rows


def _selection_metrics(report: Dict[str, Any]) -> Dict[str, Optional[float]]:
    axis = report.get("primary_axis_metrics") or {}
    survival = report.get("secondary_survivability_metrics") or {}
    relationship = report.get("relationship_status_metrics") or {}
    return {
        "axis_labeled_balanced_accuracy": axis.get("labeled_balanced_accuracy"),
        "axis_micro_recall": axis.get("micro_recall"),
        "axis_explicit_contradiction_specificity": axis.get("explicit_contradiction_specificity"),
        "survivability_partial_credit_accuracy": survival.get("partial_credit_accuracy"),
        "relationship_macro_f1": relationship.get("macro_f1"),
    }


def run_house_system_selection(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    house_system_codes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    selected_paths = list(dataset_paths or DEFAULT_DATASET_PATHS)
    dataset_roles = assert_house_selection_datasets_eligible(selected_paths)
    codes = [
        normalize_forensic_house_system_code(code)
        for code in (house_system_codes or SUPPORTED_FORENSIC_HOUSE_SYSTEM_CODES)
    ]
    codes = [code for code in dict.fromkeys(codes) if code]
    if not codes:
        raise ValueError("At least one supported forensic house system is required")

    rows: List[Dict[str, Any]] = []
    for code in codes:
        report = run_statistical_benchmark_suite(
            selected_paths,
            house_system_code=code,
            use_secondary_factors=False,
            include_control_cases=False,
            bootstrap_iterations=1,
        )
        metrics = _selection_metrics(report)
        route_error_count = int(report.get("route_error_count") or 0)
        score = forensic_house_system_selection_score(metrics) if not route_error_count else None
        rows.append(
            {
                "house_system_code": code,
                "house_system_label": FORENSIC_HOUSE_SYSTEM_LABELS[code],
                "eligible": route_error_count == 0,
                "selection_score": round(score, 6) if score is not None else None,
                "case_count": int(report.get("case_count") or 0),
                "route_error_count": route_error_count,
                "metrics": metrics,
            }
        )

    code_order = {code: index for index, code in enumerate(SUPPORTED_FORENSIC_HOUSE_SYSTEM_CODES)}
    ranked = sorted(
        rows,
        key=lambda row: (
            not row["eligible"],
            -(row["selection_score"] if row["selection_score"] is not None else -1.0),
            -(row["metrics"].get("axis_labeled_balanced_accuracy") or 0.0),
            -(row["metrics"].get("survivability_partial_credit_accuracy") or 0.0),
            -(row["metrics"].get("relationship_macro_f1") or 0.0),
            code_order[row["house_system_code"]],
        ),
    )
    winner = ranked[0] if ranked and ranked[0]["eligible"] else None
    if winner is None:
        raise RuntimeError("No forensic house system completed the development replay without route errors")
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index

    return {
        "selection_id": FORENSIC_HOUSE_SYSTEM_SELECTION_VERSION,
        "evaluation_design": {
            "role": "development_model_selection",
            "uses_locked_holdout": False,
            "uses_secondary_factors": False,
            "metric_weights": dict(FORENSIC_HOUSE_SYSTEM_SELECTION_WEIGHTS),
            "tie_break": "composite_then_axis_then_survivability_then_relationship_then_declared_code_order",
            "limitations": [
                "The cases are curated retrospective development replays, not prospective validation.",
                "The selected house system is an engineering default for this symbolic engine, not a scientifically validated forensic method.",
                "Changing rules, fixtures, or labels requires rerunning selection and reserving untouched data for evaluation.",
            ],
        },
        "datasets": dataset_roles,
        "winner": dict(winner),
        "configured_default": DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE,
        "configured_default_matches_winner": winner["house_system_code"] == DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE,
        "rankings": ranked,
    }


def render_markdown_report(report: Dict[str, Any]) -> str:
    winner = report.get("winner") or {}
    lines = [
        "# Forensic House-System Development Selection",
        "",
        f"- Winner: `{winner.get('house_system_code')}` ({winner.get('house_system_label')})",
        f"- Composite score: `{winner.get('selection_score')}`",
        f"- Configured default: `{report.get('configured_default')}`",
        f"- Default matches winner: `{report.get('configured_default_matches_winner')}`",
        "- Scope: development model selection only; locked holdouts are rejected.",
        "",
        "| Rank | Code | System | Composite | Axis balanced | Survival partial | Relationship macro-F1 | Errors |",
        "|---:|:---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rankings") or []:
        metrics = row.get("metrics") or {}
        lines.append(
            f"| {row.get('rank')} | {row.get('house_system_code')} | {row.get('house_system_label')} | "
            f"{row.get('selection_score')} | {metrics.get('axis_labeled_balanced_accuracy')} | "
            f"{metrics.get('survivability_partial_credit_accuracy')} | {metrics.get('relationship_macro_f1')} | "
            f"{row.get('route_error_count')} |"
        )
    return "\n".join(lines).strip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Select the forensic house-system default on development data only.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--dataset", action="append", help="Development dataset path; may be repeated.")
    parser.add_argument("--house-system-code", action="append", help="House system to compare; may be repeated.")
    args = parser.parse_args(argv)
    report = run_house_system_selection(args.dataset, house_system_codes=args.house_system_code)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_markdown_report(report))
    return 0 if report.get("configured_default_matches_winner") else 2


if __name__ == "__main__":
    raise SystemExit(main())
