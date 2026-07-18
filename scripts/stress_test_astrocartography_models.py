from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from astrocartography_model_stress import run_stress_suite  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run synthetic semantic stress fixtures for astrocartography goal models."
    )
    parser.add_argument(
        "--overlap-threshold",
        type=float,
        default=0.92,
        help=(
            "Fail when any active standalone public peer pair has cosine "
            "similarity at or above this threshold."
        ),
    )
    args = parser.parse_args(argv)
    report = run_stress_suite(overlap_threshold=args.overlap_threshold)
    print(f"Scenarios: {report['scenario_count']}")
    print(f"Catalog goals: {report['goal_count']}")
    print(f"Evaluated goals: {report['evaluated_goal_count']}")
    public_gate = report.get("public_gate") or {}
    print(
        "Default public gate: active standalone peers only "
        f"({public_gate.get('model_count') or 0} models)"
    )
    print()
    print("Public peer scenario winners")
    print("----------------------------")
    for scenario in report.get("scenarios") or []:
        ranking = scenario.get("ranking") or []
        top = ranking[:3]
        winners = ", ".join(
            f"{item.get('goal_id')} ({item.get('score')})"
            for item in top
        )
        print(f"{scenario.get('id')}: {winners}")
    print()
    print("Public semantic failures")
    print("------------------------")
    failures = report.get("expectation_failures") or []
    if failures:
        for failure in failures:
            print(json.dumps(failure, ensure_ascii=False))
    else:
        print("none")
    print()
    print(
        "Public standalone peer overlaps "
        f"(>= {report['overlap_threshold']:.3f} cosine)"
    )
    print("-----------------------------------------------")
    pairs = report.get("high_overlap_pairs") or []
    if pairs:
        for pair in pairs[:12]:
            print(f"{pair['left']} <-> {pair['right']}: {pair['similarity']}")
    else:
        print("none")
    print()
    print("Active specialist residual diagnostics")
    print("--------------------------------------")
    specialist_section = report.get("active_specialist_residuals") or {}
    specialist_checks = specialist_section.get("checks") or []
    if specialist_checks:
        for check in specialist_checks:
            state = "PASS" if check.get("check_passed") else "FAIL"
            print(
                f"{check.get('specialist_id')} <- {check.get('parent_id')}: "
                f"{state}; range={check.get('residual_range')}; "
                f"nonzero={check.get('nonzero_residual_count')}/"
                f"{check.get('scenario_count')}; "
                f"observed|max|={check.get('observed_max_abs_residual')} "
                f"<= configured {check.get('configured_max_abs_residual')}"
            )
    else:
        print("none")
    print("These diagnostics do not affect the default standalone public gate.")
    print()
    print("Non-public experimental research")
    print("--------------------------------")
    research = report.get("non_public_research") or {}
    research_ids = research.get("model_ids") or []
    print("Models: " + (", ".join(research_ids) if research_ids else "none"))
    for scenario in research.get("scenarios") or []:
        references = scenario.get("historical_probe_references") or []
        if not references:
            continue
        winners = ", ".join(
            f"{item.get('goal_id')} ({item.get('score')})"
            for item in (scenario.get("ranking") or [])[:3]
        )
        print(
            f"{scenario.get('id')} [historical probes: "
            f"{', '.join(references)}]: {winners}"
        )
    print("Research rankings are observations only; no semantic assertions are applied.")
    print()
    print("Explicit default-gate exclusions")
    print("--------------------------------")
    exclusions = report.get("model_exclusions") or []
    if exclusions:
        for exclusion in exclusions:
            print(
                f"{exclusion.get('goal_id')} "
                f"[status={exclusion.get('status')}, "
                f"composition={exclusion.get('composition_mode')}]: "
                f"{exclusion.get('gate_reason')}"
            )
    else:
        print("none")
    print()
    print("Intentional parent/specialist cosine exclusions")
    print("---------------------------------------------")
    for exclusion in (
        report.get("intentional_parent_specialist_pair_exclusions") or []
    ):
        print(
            f"{exclusion.get('parent_id')} <-> "
            f"{exclusion.get('specialist_id')}: "
            f"{exclusion.get('reason')}"
        )
    print()
    print(
        "Scope: synthetic semantic fixtures only. Experimental models are "
        "non-public research, and specialist promotion requires positive "
        "held-out lift."
    )
    print(
        "PUBLIC GATE: "
        + ("PASS" if report.get("gate_passed") else "FAIL")
    )
    return 0 if report.get("gate_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
