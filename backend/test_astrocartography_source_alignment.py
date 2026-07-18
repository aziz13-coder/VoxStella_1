from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from astrocartography_source_alignment import (
    DEFAULT_DATASET_PATH,
    _evaluate_expectations,
    load_source_alignment_cases,
    run_source_alignment_suite,
)


def test_source_alignment_dataset_loads_seed_cases():
    cases, skipped = load_source_alignment_cases([DEFAULT_DATASET_PATH])
    case_ids = {str(case.get("case_id") or "") for case in cases}

    assert len(cases) >= 8
    assert skipped == []
    assert "lewis_sun_mc_publicity" in case_ids
    assert all(case["fixture_policy"] == "minimal_source_signal_v2" for case in cases)
    assert all(len(case.get("natal_rows") or []) <= 1 for case in cases)
    assert all(not case.get("natal_crossings") for case in cases)
    assert all(not case.get("relocation_planets") for case in cases)


def test_source_alignment_suite_has_no_semantic_failures():
    report = run_source_alignment_suite([DEFAULT_DATASET_PATH])

    assert report["case_count"] >= 8
    assert report["goal_count"] >= 19
    assert report["expectation_failures"] == []
    assert report["semantic_gate_passed"] is True
    assert report["validation_scope"]["semantic_only"] is True
    assert report["validation_scope"]["outcome_validation"] is False
    assert report["validation_scope"]["public_specialist_gate"] == "experimental"
    assert all(case["fixture_type"] == "synthetic_semantic_claim" for case in report["cases"])


def test_strict_expectations_reject_raw_score_ties():
    ranking = [
        {"goal_id": "love", "rank": 1, "score": 62, "raw_score": 6.0},
        {
            "goal_id": "love_commitment",
            "rank": 2,
            "score": 61,
            "raw_score": 6.0,
        },
    ]
    failures = _evaluate_expectations(
        {
            "case_id": "tie",
            "expected_lead": "love",
            "minimum_lead_raw_gap": 0.01,
            "expected_above": [
                {
                    "higher": "love",
                    "lower": "love_commitment",
                    "min_raw_gap": 0.01,
                }
            ],
        },
        ranking,
    )

    assert {failure["expectation"] for failure in failures} == {
        "strict_expected_lead",
        "expected_above",
    }
