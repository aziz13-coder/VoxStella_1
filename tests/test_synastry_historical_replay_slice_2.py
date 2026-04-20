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


FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_2.json"


def test_synastry_historical_replay_slice_2_has_expected_cases():
    fixture = load_synastry_historical_replay_cases(path=FIXTURE_PATH)
    ids = {case["id"] for case in fixture["cases"]}
    assert ids == {
        "frida_kahlo_diego_rivera",
        "sid_nancy",
        "elizabeth_taylor_richard_burton",
    }


def test_synastry_historical_replay_slice_2_tracks_timed_sources_and_snapshots():
    fixture = load_synastry_historical_replay_cases(path=FIXTURE_PATH)
    for case in fixture["cases"]:
        assert case["source_references"]
        assert case["chart_data_a"]["planets"]
        assert case["chart_data_b"]["planets"]
        assert case["chart_data_a"]["houses"]
        assert case["chart_data_b"]["houses"]
        assert case["chart_meta_a"]["birth_data_confidence"]
        assert case["chart_meta_b"]["birth_data_confidence"]


def test_synastry_historical_replay_slice_2_current_baseline():
    fixture = load_synastry_historical_replay_cases(path=FIXTURE_PATH)
    expected = {
        "frida_kahlo_diego_rivera": {
            "status": "partially_aligned",
            "matched": {"growth"},
            "missed_primary": {"burden"},
            "missed_secondary": {"attraction"},
        },
        "sid_nancy": {
            "status": "aligned",
            "matched": {"friction", "burden", "attraction"},
            "missed_primary": set(),
            "missed_secondary": set(),
        },
        "elizabeth_taylor_richard_burton": {
            "status": "aligned",
            "matched": {"friction", "attachment", "attraction"},
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
