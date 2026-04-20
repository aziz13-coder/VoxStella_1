from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from validate_weather_benchmark_datasets import PROSPECTIVE_FORECAST_FILE, load_jsonl_cases


def load_prospective_cases(*, case_id: Optional[str] = None, include_disabled: bool = False) -> List[Dict[str, Any]]:
    path = Path(PROSPECTIVE_FORECAST_FILE).resolve()
    cases: List[Dict[str, Any]] = []
    normalized_case_id = str(case_id or "").strip().lower()
    for payload in load_jsonl_cases(path):
        if normalized_case_id and str(payload.get("case_id") or "").strip().lower() != normalized_case_id:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            continue
        cases.append(dict(payload))
    return cases


def run_prospective_suite(*, case_id: Optional[str] = None, include_disabled: bool = False) -> Dict[str, Any]:
    cases = load_prospective_cases(case_id=case_id, include_disabled=include_disabled)
    return {
        "dataset_path": str(Path(PROSPECTIVE_FORECAST_FILE).resolve()),
        "case_count": len(cases),
        "status": "scaffold_only" if not cases else "defined_but_unexecuted",
        "critical_answer": (
            "Prospective weather benchmarking is scaffolded but not yet scored. "
            "No forward-run cases are defined in the active dataset."
            if not cases
            else "Prospective weather cases exist, but execution and scoring are not implemented in this scaffold."
        ),
        "cases": cases,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Report the weather prospective benchmark scaffold status.")
    parser.add_argument("--case-id", help="Filter to a single prospective case_id.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled scaffold cases.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown-like text.")
    args = parser.parse_args(argv)

    report = run_prospective_suite(case_id=args.case_id, include_disabled=args.include_disabled)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("# Weather Prospective Benchmark Scaffold")
        print("")
        print(f"- Cases: {report['case_count']}")
        print(f"- Status: {report['status']}")
        print("")
        print(report["critical_answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
