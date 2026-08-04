from __future__ import annotations

from pathlib import Path

from backend.forensic_survivability_descendant_aspect_comparison import (
    run_descendant_aspect_comparison,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
NETFLIX_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "forensic_netflix_true_crime_2025_2026_cases.json"
RECENT_DOCUMENTARIES_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "forensic_recent_documentaries_2025_2026_cases.json"
)


def _single_case(fixture: Path, case_id: str):
    report = run_descendant_aspect_comparison([fixture], case_id=case_id)
    assert report["route_errors"] == []
    assert report["live_route_mismatch_count"] == 0
    assert report["case_count"] == 1
    return report["cases"][0]


def test_mackenzie_comparison_records_descendant_pressure_without_claiming_validation() -> None:
    row = _single_case(NETFLIX_FIXTURE, "mackenzie_shirilla_the_crash")

    assert row["baseline"] == {
        "level": "Higher",
        "band": "nonfatal_tilt",
        "score": 3.35,
        "aligned": None,
    }
    assert row["candidate"] == {
        "level": "Lower",
        "band": "fatal_pressure_dominant",
        "score": 0.92,
        "aligned": None,
    }
    assert row["change"] == "not_scored"
    assert row["expected"] == {"levels": [], "bands": []}
    assert row["descendant_aspect_impact"]["contacts"] == [
        {
            "planet": "Pluto",
            "family": "outer_pressure",
            "aspect_to_descendant": "conjunction",
            "orb": 0.027,
            "raw_pressure": 2.43,
            "roles": [],
            "phase": "unavailable_static_angle_snapshot",
        }
    ]


def test_idaho_fixture_stays_correct_and_unchanged() -> None:
    row = _single_case(
        RECENT_DOCUMENTARIES_FIXTURE,
        "netflix_idaho_murders_college_nightmare_2026",
    )

    assert row["baseline"]["level"] == "Lower"
    assert row["baseline"]["band"] == "fatal_pressure_dominant"
    assert row["candidate"] == row["baseline"]
    assert row["change"] == "unchanged_aligned"
    assert row["descendant_aspect_impact"]["contacts"] == []


def test_replay_is_neutral_when_the_candidate_has_no_descendant_contact() -> None:
    row = _single_case(
        RECENT_DOCUMENTARIES_FIXTURE,
        "netflix_trainwreck_astroworld_tragedy_2025",
    )

    assert row["descendant_aspect_impact"]["contacts"] == []
    assert row["candidate"] == row["baseline"]
