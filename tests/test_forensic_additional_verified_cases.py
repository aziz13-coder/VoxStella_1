import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
for import_path in (BACKEND_ROOT, REPO_ROOT):
    value = str(import_path)
    if value not in sys.path:
        sys.path.insert(0, value)

import forensic_statistical_benchmark_runner as runner


DATASET_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_fbi_active_shooter_extension_cases.json"
RECENT_DOCUMENTARY_DATASET_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_recent_documentaries_2025_2026_cases.json"
HOLDOUT_DATASET_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_holdout_30_cases_2026_05_20.json"


def test_additional_verified_cases_extend_statistical_corpus_to_33():
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    assert len(payload["cases"]) == 15
    assert any(source["id"] == "fbi_active_shooter_2000_2018" for source in payload["sources"])

    cases = runner.load_statistical_cases()
    extension_cases = [case for case in cases if case["dataset_name"] == DATASET_PATH.name]

    assert len(extension_cases) == 15
    assert len(cases) == 33
    assert all(case["query"].get("mode") == "manual" for case in extension_cases)
    assert all(case["expected_axes"] for case in extension_cases)
    assert all(case["expected_survivability"]["levels"] for case in extension_cases)


def test_recent_documentaries_are_independent_source_backed_development_cases():
    payload = json.loads(RECENT_DOCUMENTARY_DATASET_PATH.read_text(encoding="utf-8"))

    assert payload["evaluation_role"] == "development"
    assert payload["benchmark_policy"]["status"] == "development_house_system_selection_v1"
    assert len(payload["cases"]) == 4
    assert {case["id"] for case in payload["cases"]} == {
        "netflix_idaho_murders_college_nightmare_2026",
        "netflix_titan_oceangate_submersible_disaster_2025",
        "netflix_trainwreck_astroworld_tragedy_2025",
        "netflix_shipwrecked_costa_concordia_2026",
    }
    assert all(case["documentary_source_ids"] for case in payload["cases"])
    assert all(case["event_source_ids"] for case in payload["cases"])
    assert all(case["event_anchor"]["anchor_kind"] for case in payload["cases"])
    idaho = next(case for case in payload["cases"] if "idaho_murders" in case["id"])
    assert idaho["event_anchor"]["uncertainty_minutes"] == 12.5
    assert "Midpoint" in idaho["event_anchor"]["notes"]

    default_cases = runner.load_statistical_cases()
    recent_cases = [
        case for case in default_cases
        if case["dataset_name"] == RECENT_DOCUMENTARY_DATASET_PATH.name
    ]
    assert len(recent_cases) == 4


def test_forensic_retrospective_cases_are_separate_from_default_corpus_and_marked_contaminated():
    payload = json.loads(HOLDOUT_DATASET_PATH.read_text(encoding="utf-8"))

    assert payload["benchmark_policy"]["status"] == "contaminated_retrospective_evaluation"
    assert payload["benchmark_policy"]["evaluation_role"] == "development_retrospective_only"
    assert "HEALTHCARE_CHILD_CALIBRATION" in payload["benchmark_policy"]["contamination_note"]
    assert len(payload["cases"]) == 30
    assert {source["id"] for source in payload["sources"]} == {
        "fbi_active_shooter_2019",
        "fbi_active_shooter_2020",
        "fbi_active_shooter_2021",
        "fbi_active_shooter_2022",
        "fbi_active_shooter_2023",
    }

    default_cases = runner.load_statistical_cases()
    assert all(case["dataset_name"] != HOLDOUT_DATASET_PATH.name for case in default_cases)

    holdout_cases = runner.load_statistical_cases([HOLDOUT_DATASET_PATH])
    assert len(holdout_cases) == 30
    assert all(case["query"].get("mode") == "manual" for case in holdout_cases)
    assert all(case["expected_axes"] for case in holdout_cases)
    assert all(case["expected_survivability"]["levels"] for case in holdout_cases)
    assert all(case["expected_relationship_labels"] for case in holdout_cases)
