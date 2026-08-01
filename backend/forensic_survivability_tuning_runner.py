from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

CURRENT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_ROOT.parent
for import_path in (CURRENT_ROOT, REPO_ROOT):
    value = str(import_path)
    if value not in sys.path:
        sys.path.insert(0, value)

from backend.forensic.survivability import (
    DEFAULT_SURVIVABILITY_POLICY,
    SurvivabilityPolicy,
    compute_survivability,
)
from backend.forensic.tuning import assert_tuning_eligible
from backend import forensic_statistical_benchmark_runner as benchmark


DEFAULT_DATASET = REPO_ROOT / "tests" / "fixtures" / "forensic_survivability_stratified_cases.json"


def candidate_policies() -> List[SurvivabilityPolicy]:
    default = DEFAULT_SURVIVABILITY_POLICY
    candidates = [default]
    for fatal_gate, violent_net, higher_net in product(
        (3.5, 4.5, 5.5),
        (-0.5, 0.5, 1.5),
        (2.0, 3.0, 4.0),
    ):
        if (
            fatal_gate == default.fatal_gate_pressure
            and violent_net == default.violent_gate_max_net
            and higher_net == default.higher_net
        ):
            continue
        candidate = replace(
            default,
            version=f"candidate_fg{fatal_gate:g}_vn{violent_net:g}_hn{higher_net:g}",
            fatal_gate_pressure=fatal_gate,
            violent_gate_max_net=violent_net,
            higher_net=higher_net,
        )
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _policy_distance(policy: SurvivabilityPolicy) -> float:
    default = DEFAULT_SURVIVABILITY_POLICY
    return round(
        abs(policy.fatal_gate_pressure - default.fatal_gate_pressure)
        + abs(policy.violent_gate_max_net - default.violent_gate_max_net)
        + abs(policy.higher_net - default.higher_net),
        6,
    )


def _score_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    values = list(rows)
    aligned = sum(1 for row in values if row["level_match"] and row["band_match"])
    partial = sum(1 for row in values if row["level_match"] != row["band_match"])
    count = len(values)
    return {
        "case_count": count,
        "aligned": aligned,
        "partial": partial,
        "accuracy": round(aligned / count, 4) if count else None,
        "partial_credit_accuracy": round((aligned + partial * 0.5) / count, 4) if count else None,
    }


def _evaluate_policy(cases: Sequence[Dict[str, Any]], policy: SurvivabilityPolicy) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for item in cases:
        payload = item["payload"]
        findings = [
            finding
            for finding in payload.get("findings") or []
            if isinstance(finding, dict) and finding.get("scoring_eligible", True) is not False
        ]
        result = compute_survivability(
            payload.get("features") or {},
            findings=findings,
            categories=payload.get("scoring_categories") or {},
            case_type=str((item.get("query") or {}).get("case_type") or "general"),
            policy=policy,
        )
        expected_levels = set(item.get("expected_levels") or [])
        expected_bands = set(item.get("expected_bands") or [])
        rows.append(
            {
                "case_id": item["case_id"],
                "family": item["family"],
                "actual_level": result.get("level"),
                "actual_band": result.get("outcome_band"),
                "level_match": result.get("level") in expected_levels,
                "band_match": result.get("outcome_band") in expected_bands,
            }
        )
    return {"policy": asdict(policy), "metrics": _score_rows(rows), "rows": rows}


def _select_policy(cases: Sequence[Dict[str, Any]], policies: Sequence[SurvivabilityPolicy]) -> SurvivabilityPolicy:
    ranked = []
    for policy in policies:
        metrics = _evaluate_policy(cases, policy)["metrics"]
        ranked.append(
            (
                float(metrics.get("accuracy") or 0.0),
                float(metrics.get("partial_credit_accuracy") or 0.0),
                -_policy_distance(policy),
                policy,
            )
        )
    return max(ranked, key=lambda row: row[:3])[3]


def _load_development_cases(dataset_path: Path) -> tuple[str, List[Dict[str, Any]]]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    role = assert_tuning_eligible(payload, dataset_path)
    prepared: List[Dict[str, Any]] = []
    for index, case in enumerate(payload.get("cases") or []):
        if not isinstance(case, dict):
            continue
        query = benchmark.build_forensic_query(case)
        expected_levels = list(case.get("expected_levels") or [])
        expected_bands = list(case.get("expected_bands") or [])
        if not query or not expected_levels or not expected_bands:
            continue
        query["secondary_factors"] = "0"
        route = benchmark._call_forensic_route(query)
        route_payload = route.get("payload") or {}
        if route.get("status_code") != 200 or not route_payload.get("success"):
            raise RuntimeError(f"Forensic route failed for {case.get('id') or index}: {route_payload.get('error')}")
        prepared.append(
            {
                "case_id": str(case.get("id") or f"case_{index}"),
                "family": str(case.get("family") or "ungrouped"),
                "query": query,
                "expected_levels": expected_levels,
                "expected_bands": expected_bands,
                "payload": route_payload,
            }
        )
    return role, prepared


def run_tuning(dataset: str | Path = DEFAULT_DATASET) -> Dict[str, Any]:
    dataset_path = Path(dataset)
    if not dataset_path.is_absolute():
        dataset_path = REPO_ROOT / dataset_path
    role, cases = _load_development_cases(dataset_path)
    policies = candidate_policies()
    baseline = _evaluate_policy(cases, DEFAULT_SURVIVABILITY_POLICY)
    selected = _select_policy(cases, policies)
    selected_result = _evaluate_policy(cases, selected)

    families = sorted({item["family"] for item in cases})
    outer_rows: List[Dict[str, Any]] = []
    for held_family in families:
        train = [item for item in cases if item["family"] != held_family]
        held = [item for item in cases if item["family"] == held_family]
        chosen = _select_policy(train, policies)
        test_result = _evaluate_policy(held, chosen)
        outer_rows.extend(test_result["rows"])

    nested_metrics = _score_rows(outer_rows)
    baseline_accuracy = float(baseline["metrics"].get("accuracy") or 0.0)
    selected_accuracy = float(selected_result["metrics"].get("accuracy") or 0.0)
    reasons: List[str] = []
    if len(cases) < 30:
        reasons.append("fewer_than_30_development_cases")
    if len(families) < 5:
        reasons.append("fewer_than_5_independent_case_families")
    if selected_accuracy < baseline_accuracy + 0.05:
        reasons.append("candidate_does_not_improve_development_accuracy_by_0.05")
    if float(nested_metrics.get("accuracy") or 0.0) < baseline_accuracy:
        reasons.append("leave_one_family_out_accuracy_below_baseline_full_set_accuracy")

    return {
        "dataset": str(dataset_path),
        "evaluation_role": role,
        "case_count": len(cases),
        "family_count": len(families),
        "candidate_count": len(policies),
        "baseline": baseline,
        "selected_candidate": selected_result,
        "leave_one_family_out": nested_metrics,
        "promotion": {
            "eligible": not reasons,
            "reasons": reasons,
            "policy_changed": selected != DEFAULT_SURVIVABILITY_POLICY,
            "note": "No policy is written by this runner; promotion requires a new untouched same-domain holdout.",
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Leakage-guarded survivability policy candidate search")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    args = parser.parse_args(argv)
    print(json.dumps(run_tuning(args.dataset), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
