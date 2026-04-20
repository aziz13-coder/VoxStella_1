from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from astrocartography_source_alignment import (
    DEFAULT_DATASET_PATH,
    load_source_alignment_cases,
    run_source_alignment_suite,
)


def test_source_alignment_dataset_loads_seed_cases():
    cases, skipped = load_source_alignment_cases([DEFAULT_DATASET_PATH])
    case_ids = {str(case.get("case_id") or "") for case in cases}

    assert len(cases) >= 8
    assert skipped == []
    assert "lewis_sun_publicity" in case_ids


def test_source_alignment_suite_has_no_expectation_failures():
    report = run_source_alignment_suite([DEFAULT_DATASET_PATH])

    assert report["case_count"] >= 8
    assert report["goal_count"] >= 20
    assert report["expectation_failures"] == []
