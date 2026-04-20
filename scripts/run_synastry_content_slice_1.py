from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"

for path in (REPO_ROOT, TESTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from synastry_content_slice_utils import (
    load_synastry_content_slice,
    replay_synastry_content_case,
    summarize_synastry_content_case,
)


OUTPUT_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_content_slice_1_results.json"


def main():
    fixture = load_synastry_content_slice()
    results = []

    for case in fixture.get("cases") or []:
        if case.get("chart_data_a") and case.get("chart_data_b") and case.get("chart_meta_a") and case.get("chart_meta_b"):
            report = replay_synastry_content_case(case)
            results.append(summarize_synastry_content_case(case, report=report))
        else:
            results.append(summarize_synastry_content_case(case))

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "purpose": "Content-only synastry slice output for blog/demo cases. This artifact is explicitly outside the validation and calibration lanes.",
        "lane": fixture.get("lane") or "blog_content_only",
        "case_count": len(results),
        "results": results,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(json.dumps({"case_count": len(results), "lane": payload["lane"]}, indent=2))


if __name__ == "__main__":
    main()
