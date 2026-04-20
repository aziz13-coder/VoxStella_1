from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from astrocartography_model_stress import run_stress_suite  # noqa: E402


def main() -> None:
    report = run_stress_suite()
    print(f"Scenarios: {report['scenario_count']}")
    print(f"Goals: {report['goal_count']}")
    print()
    print("Scenario winners")
    print("---------------")
    for scenario in report.get("scenarios") or []:
        ranking = scenario.get("ranking") or []
        top = ranking[:3]
        winners = ", ".join(
            f"{item.get('goal_id')} ({item.get('score')})"
            for item in top
        )
        print(f"{scenario.get('id')}: {winners}")
    print()
    print("Expectation failures")
    print("--------------------")
    failures = report.get("expectation_failures") or []
    if failures:
        for failure in failures:
            print(json.dumps(failure, ensure_ascii=False))
    else:
        print("none")
    print()
    print("High-overlap pairs (>= 0.92 cosine)")
    print("-----------------------------------")
    pairs = report.get("high_overlap_pairs") or []
    if pairs:
        for pair in pairs[:12]:
            print(f"{pair['left']} <-> {pair['right']}: {pair['similarity']}")
    else:
        print("none")


if __name__ == "__main__":
    main()
