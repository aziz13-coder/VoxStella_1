import json
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
TESTS_DIR = REPO_ROOT / "tests"

for path in (BACKEND_DIR, TESTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from synastry_engine import build_synastry_report
from synastry_historical_validation_utils import (
    compare_case_to_synastry_output,
    load_synastry_historical_validation_corpus,
    runnable_cases,
)


OUTPUT_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_validation_results.json"


def _build_case_report(case):
    bundle_a = {"chart_data": case["chart_data_a"], "meta": {"label": case["partner_a"]}}
    bundle_b = {"chart_data": case["chart_data_b"], "meta": {"label": case["partner_b"]}}
    chart_a = case.get("chart_meta_a") or {"id": f"{case['id']}-a", "label": case["partner_a"], "location": case["partner_a"]}
    chart_b = case.get("chart_meta_b") or {"id": f"{case['id']}-b", "label": case["partner_b"], "location": case["partner_b"]}
    options = case.get("options") or None
    return build_synastry_report(bundle_a, bundle_b, chart_a, chart_b, options=options)


def main():
    corpus = load_synastry_historical_validation_corpus()
    cases = runnable_cases(corpus)

    results = []
    status_counts = Counter()
    for case in cases:
        report = _build_case_report(case)
        comparison = compare_case_to_synastry_output(case, report)
        results.append(
            {
                "case_id": case["id"],
                "title": case["title"],
                "status": comparison["status"],
                "comparison": comparison,
                "summary": report.get("summary") or {},
                "top_supportive_links": report.get("top_supportive_links") or [],
                "top_challenging_links": report.get("top_challenging_links") or [],
            }
        )
        status_counts[comparison["status"]] += 1

    payload = {
        "generated_at": "2026-04-03T12:45:00+03:00",
        "purpose": "Replay results for synastry historical validation corpus",
        "runnable_case_count": len(cases),
        "status_counts": dict(status_counts),
        "results": results,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(json.dumps({"runnable_case_count": len(cases), "status_counts": dict(status_counts)}, indent=2))


if __name__ == "__main__":
    main()
