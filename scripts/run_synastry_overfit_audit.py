from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
TESTS_DIR = REPO_ROOT / "tests"

for path in (REPO_ROOT, BACKEND_DIR, TESTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from synastry_overfit_audit_support import (  # noqa: E402
    ATTACHMENT_FLOOR_RULE_ID,
    ATTRACTION_STRESS_FLOOR_RULE_ID,
    ATTRACTION_SUPPORTIVE_FLOOR_RULE_ID,
    BURDEN_FLOOR_RULE_ID,
    COMPATIBILITY_GATE_RULE_ID,
    build_high_friction_without_hard_saturn_report,
    build_magnetic_stress_cluster_report,
    build_oppressive_cluster_report,
    build_serious_but_workable_saturn_report,
    build_supportive_polarity_chemistry_report,
    report_rule_ids_by_category,
    seeded_adjustment_audit,
)
from synastry_stress_support import category_map, report_has_rule  # noqa: E402
from tests.synastry_historical_replay_utils import (  # noqa: E402
    load_synastry_historical_replay_cases,
    replay_synastry_historical_case,
)


OUTPUT_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_overfit_audit_results.json"
SLICE_1_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_1.json"
SLICE_2_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_2.json"
SLICE_3_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_3.json"


def _report_summary(report):
    categories = category_map(report)
    return {
        "attraction_score": float((categories.get("attraction") or {}).get("score") or 0.0),
        "burden_score": float((categories.get("burden") or {}).get("score") or 0.0),
        "compatibility_score": float((categories.get("compatibility") or {}).get("score") or 0.0),
        "friction_score": float((categories.get("friction") or {}).get("score") or 0.0),
        "attachment_score": float((categories.get("attachment") or {}).get("score") or 0.0),
        "attraction_rule_ids": report_rule_ids_by_category(report, "attraction"),
        "attachment_rule_ids": report_rule_ids_by_category(report, "attachment"),
        "burden_rule_ids": report_rule_ids_by_category(report, "burden"),
        "compatibility_rule_ids": report_rule_ids_by_category(report, "compatibility"),
        "has_attachment_floor": report_has_rule(report, ATTACHMENT_FLOOR_RULE_ID),
        "has_attraction_supportive_floor": report_has_rule(report, ATTRACTION_SUPPORTIVE_FLOOR_RULE_ID),
        "has_attraction_stress_floor": report_has_rule(report, ATTRACTION_STRESS_FLOOR_RULE_ID),
        "has_burden_floor": report_has_rule(report, BURDEN_FLOOR_RULE_ID),
        "has_compatibility_gate": report_has_rule(report, COMPATIBILITY_GATE_RULE_ID),
    }


def main():
    historical_cases = []
    historical_status_counts = {}
    for fixture_path in (SLICE_1_PATH, SLICE_2_PATH, SLICE_3_PATH):
        fixture = load_synastry_historical_replay_cases(path=fixture_path)
        slice_results = []
        for case in (fixture.get("cases") or []):
            report, comparison = replay_synastry_historical_case(case)
            slice_results.append(
                {
                    "case_id": case["id"],
                    "status": comparison["status"],
                    **_report_summary(report),
                }
            )
        status_counts = {}
        for item in slice_results:
            status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
        historical_status_counts[fixture_path.name] = status_counts
        historical_cases.append(
            {
                "fixture": str(fixture_path),
                "case_count": len(slice_results),
                "status_counts": status_counts,
                "cases": slice_results,
            }
        )

    archetypes = {
        "oppressive_cluster": _report_summary(build_oppressive_cluster_report()),
        "serious_but_workable_saturn": _report_summary(build_serious_but_workable_saturn_report()),
        "high_friction_without_hard_saturn_cluster": _report_summary(build_high_friction_without_hard_saturn_report()),
        "supportive_polarity_chemistry": _report_summary(build_supportive_polarity_chemistry_report()),
        "magnetic_stress_cluster": _report_summary(build_magnetic_stress_cluster_report()),
    }

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "purpose": "Audit whether recent synastry category adjustments behave like general doctrine rather than only fitting the first two historical replay couples.",
        "historical_replay_slices": historical_cases,
        "historical_status_counts": historical_status_counts,
        "seeded_corpus_audit": seeded_adjustment_audit(seed_count=24),
        "synthetic_archetypes": archetypes,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(
        json.dumps(
            {
                "historical_status_counts": historical_status_counts,
                "burden_floor_seed_count": payload["seeded_corpus_audit"]["burden_floor_count"],
                "compatibility_gate_seed_count": payload["seeded_corpus_audit"]["compatibility_gate_count"],
                "attraction_supportive_floor_seed_count": payload["seeded_corpus_audit"]["attraction_supportive_floor_count"],
                "attraction_stress_floor_seed_count": payload["seeded_corpus_audit"]["attraction_stress_floor_count"],
                "attachment_floor_seed_count": payload["seeded_corpus_audit"]["attachment_floor_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
