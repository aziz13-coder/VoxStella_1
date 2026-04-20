import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"

for path in (REPO_ROOT, TESTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from synastry_historical_replay_utils import (
    load_synastry_historical_replay_cases,
    replay_synastry_historical_case,
)


OUTPUT_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_1_results.json"


def main():
    fixture = load_synastry_historical_replay_cases()
    results = []
    status_counts = Counter()
    matched_counts = Counter()
    missed_primary_counts = Counter()
    missed_secondary_counts = Counter()

    for case in fixture.get("cases") or []:
        report, comparison = replay_synastry_historical_case(case)
        status_counts[comparison["status"]] += 1
        for key in comparison.get("matched_dimensions") or []:
            matched_counts[key] += 1
        for key in comparison.get("missed_primary_dimensions") or []:
            missed_primary_counts[key] += 1
        for key in comparison.get("missed_secondary_dimensions") or []:
            missed_secondary_counts[key] += 1

        categories = {
            item["id"]: item["score"]
            for item in (report.get("categories") or [])
            if item.get("id")
        }
        results.append(
            {
                "case_id": case["id"],
                "title": case["title"],
                "status": comparison["status"],
                "comparison": comparison,
                "category_scores": categories,
                "summary_lines": report.get("summary", {}).get("summary_lines") or [],
                "top_supportive_titles": [
                    item.get("title") or item.get("label")
                    for item in (report.get("top_supportive_links") or [])[:5]
                    if item.get("title") or item.get("label")
                ],
                "top_challenging_titles": [
                    item.get("title") or item.get("label")
                    for item in (report.get("top_challenging_links") or [])[:5]
                    if item.get("title") or item.get("label")
                ],
            }
        )

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "purpose": "Replay results for the first replay-ready synastry historical validation slice.",
        "case_count": len(results),
        "status_counts": dict(status_counts),
        "matched_dimension_counts": dict(matched_counts),
        "missed_primary_dimension_counts": dict(missed_primary_counts),
        "missed_secondary_dimension_counts": dict(missed_secondary_counts),
        "results": results,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(json.dumps({"case_count": len(results), "status_counts": dict(status_counts)}, indent=2))


if __name__ == "__main__":
    main()
