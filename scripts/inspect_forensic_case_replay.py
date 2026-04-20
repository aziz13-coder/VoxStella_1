import json
import sys
from pathlib import Path

from tests.forensic_case_replay_utils import (
    build_forensic_query_string,
    load_forensic_replay_cases,
    make_forensic_replay_app,
)


def main() -> int:
    case_id = sys.argv[1] if len(sys.argv) > 1 else ""
    extra_paths = sys.argv[2:]
    cases = {case["id"]: case for case in load_forensic_replay_cases()}
    if case_id not in cases:
        print(json.dumps({"error": "unknown_case", "known_ids": sorted(cases)}, indent=2))
        return 1

    app = make_forensic_replay_app()
    client = app.test_client()
    case = cases[case_id]
    query = build_forensic_query_string(case)
    response = client.get("/api/astro-clock/forensic", query_string=query)
    payload = response.get_json() if response.is_json else None

    features = (payload or {}).get("features") or {}
    houses = features.get("houses") or {}
    planets = features.get("planets") or {}
    moon = planets.get("Moon") or {}
    extra_feature_values = {}
    for path in extra_paths:
        cur = features
        for part in str(path).split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        extra_feature_values[path] = cur
    summary = {
        "categories": (payload or {}).get("categories") or {},
        "finding_ids": [
            finding.get("id")
            for finding in ((payload or {}).get("findings") or [])[:20]
            if finding.get("id")
        ],
        "top_finding_titles": [
            finding.get("title")
            for finding in ((payload or {}).get("findings") or [])[:12]
            if finding.get("title")
        ],
        "key_features": {
            "first_ruler": houses.get("first_ruler"),
            "first_ruler_house": houses.get("first_ruler_house"),
            "eighth_ruler": houses.get("eighth_ruler"),
            "seventh_ruler": houses.get("seventh_ruler"),
            "seventh_ruler_house": houses.get("seventh_ruler_house"),
            "seventh_ruler_in_12th": houses.get("seventh_ruler_in_12th"),
            "emphasis12_count": houses.get("emphasis12_count"),
            "malefics_in_6th": houses.get("malefics_in_6th"),
            "north_node_house": houses.get("north_node_house"),
            "neptune_angular": houses.get("neptune_angular"),
            "moon_house": moon.get("house"),
            "moon_sign": moon.get("sign"),
            "moon_void_of_course": (features.get("moon") or {}).get("void_of_course"),
            "moon_via_combusta": (features.get("moon") or {}).get("via_combusta"),
        },
        "extra_feature_values": extra_feature_values,
    }
    out = {
        "id": case_id,
        "query": query,
        "status_code": response.status_code,
        "summary": summary,
    }
    print(json.dumps(out, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
