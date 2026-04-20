from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CENSUS_PATH = FIXTURES_DIR / "horary_external_source_pass_metadata_census.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_source_pass_metadata_census_covers_all_completed_source_pass_cases():
    census_entries = _load_json(CENSUS_PATH)
    fixture_ids = set()

    for path in sorted(FIXTURES_DIR.glob("horary_*source_pass_slice*.json")):
        for case in _load_json(path):
            fixture_ids.add(case["id"])

    census_ids = {entry["id"] for entry in census_entries}

    assert census_ids == fixture_ids
    assert len(census_entries) == 55


def test_source_pass_metadata_census_track_counts_match_first_pass_policy():
    census_entries = _load_json(CENSUS_PATH)
    track_counts = Counter(entry["replay_track"] for entry in census_entries)

    assert track_counts["direct_replay"] == 0
    assert track_counts["image_reconstructable"] == 14
    assert track_counts["doctrine_only"] == 41


def test_source_pass_metadata_census_slice_span_is_complete():
    census_entries = _load_json(CENSUS_PATH)
    slice_numbers = {entry["slice_number"] for entry in census_entries}

    assert slice_numbers == {str(num) for num in range(2, 19)}
