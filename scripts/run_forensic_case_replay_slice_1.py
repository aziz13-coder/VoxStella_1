import json
from pathlib import Path

from tests.forensic_case_corpus_utils import compare_case_to_forensic_output
from tests.forensic_case_replay_utils import (
    build_forensic_query_string,
    load_forensic_replay_cases,
    make_forensic_replay_app,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_case_replay_slice_1_results.json"


def main():
    app = make_forensic_replay_app()
    client = app.test_client()

    results = []
    for case in load_forensic_replay_cases():
        query = build_forensic_query_string(case)
        response = client.get("/api/astro-clock/forensic", query_string=query)
        entry = {
            "id": case["id"],
            "status_code": response.status_code,
        }
        if response.status_code == 200:
            payload = response.get_json() or {}
            entry["success"] = bool(payload.get("success"))
            entry["comparison"] = compare_case_to_forensic_output(case, payload)
            entry["categories"] = payload.get("categories") or {}
            entry["top_finding_titles"] = [
                finding.get("title")
                for finding in (payload.get("findings") or [])[:5]
                if finding.get("title")
            ]
        else:
            try:
                entry["error_payload"] = response.get_json()
            except Exception:
                entry["error_payload"] = None
        results.append(entry)

    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"Wrote replay results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
