from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))
sys.path.append(str(REPO_ROOT / "tests"))

from tests.synastry_historical_replay_utils import (
    load_synastry_historical_replay_cases,
    replay_synastry_historical_case,
)


def test_synastry_historical_replay_slice_1_has_expected_cases():
    fixture = load_synastry_historical_replay_cases()
    ids = {case["id"] for case in fixture["cases"]}
    assert ids == {
        "paul_newman_joanne_woodward",
        "charles_diana",
    }


def test_synastry_historical_replay_slice_1_tracks_timed_sources_and_snapshots():
    fixture = load_synastry_historical_replay_cases()
    for case in fixture["cases"]:
        assert case["birth_data_confidence"] in {"AA", "A"}
        assert case["source_references"]
        assert case["chart_data_a"]["planets"]
        assert case["chart_data_b"]["planets"]
        assert case["chart_data_a"]["houses"]
        assert case["chart_data_b"]["houses"]
        assert case["chart_meta_a"]["birth_data_confidence"] in {"AA", "A"}
        assert case["chart_meta_b"]["birth_data_confidence"] in {"AA", "A"}


def test_synastry_historical_replay_slice_1_current_baseline():
    fixture = load_synastry_historical_replay_cases()
    expected = {
        "paul_newman_joanne_woodward": {
            "status": "aligned",
            "matched": {"attachment", "compatibility", "burden"},
            "missed_primary": set(),
            "missed_secondary": set(),
        },
        "charles_diana": {
            "status": "aligned",
            "matched": {"burden", "compatibility", "friction"},
            "missed_primary": set(),
            "missed_secondary": set(),
        },
    }

    for case in fixture["cases"]:
        report, comparison = replay_synastry_historical_case(case)
        baseline = expected[case["id"]]

        assert comparison["status"] == baseline["status"], case["id"]
        assert set(comparison["matched_dimensions"]) == baseline["matched"], case["id"]
        assert set(comparison["missed_primary_dimensions"]) == baseline["missed_primary"], case["id"]
        assert set(comparison["missed_secondary_dimensions"]) == baseline["missed_secondary"], case["id"]
        assert report["summary"]["summary_lines"], case["id"]
        assert report["top_supportive_links"], case["id"]
        assert report["top_challenging_links"], case["id"]


def test_synastry_historical_replay_slice_1_adjustment_rules_fire_on_the_expected_cases():
    fixture = load_synastry_historical_replay_cases()
    expected_adjustments = {
        "paul_newman_joanne_woodward": {"burden": "burden_saturn_context_relief"},
        "charles_diana": {
            "compatibility": "compatibility_conflict_gate",
            "burden": "burden_oppressive_cluster_floor",
        },
    }

    for case in fixture["cases"]:
        report, _comparison = replay_synastry_historical_case(case)
        category_map = {item["id"]: item for item in report["categories"]}
        for category_id, rule_id in expected_adjustments[case["id"]].items():
            evidence_ids = {
                item.get("rule_family_id")
                for item in (category_map[category_id].get("evidence_items") or [])
                if item.get("rule_family_id")
            }
            assert rule_id in evidence_ids, (case["id"], category_id, evidence_ids)
