import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
for import_path in (BACKEND_ROOT, REPO_ROOT):
    value = str(import_path)
    if value not in sys.path:
        sys.path.insert(0, value)

import forensic_idaho_benchmark_runner as idaho_runner


DATASET_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_recent_documentaries_2025_2026_cases.json"
CASE_ID = "netflix_idaho_murders_college_nightmare_2026"
RELATIONSHIP_TARGET_MEANING = (
    "No intimate-partner, family, or friend relationship is established in the benchmark sources. "
    "This broad label does not assert motive, random selection, or the absence of every prior contact."
)


def _load_payload_and_case():
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    case = next(item for item in payload["cases"] if item["id"] == CASE_ID)
    return payload, case


@pytest.fixture(scope="module")
def benchmark_report():
    return idaho_runner.run_idaho_benchmark(DATASET_PATH)


def test_idaho_ground_truth_is_adjudicated_interval_aware_and_source_mapped():
    payload, case = _load_payload_and_case()
    sources = {source["id"]: source for source in payload["sources"]}

    assert case["known_facts"] == {
        "legal_status": "adjudicated_by_guilty_plea_and_sentencing",
        "offenses": ["one burglary count", "four first-degree murder counts"],
        "event_date_local": "2022-11-13",
        "event_time_window_local": "04:00-04:25",
        "scene": "occupied off-campus residence at 1122 King Road",
        "cause_and_manner": "four homicide deaths by stabbing",
        "victim_ages": [20, 20, 21, 21],
        "surviving_roommates": 2,
        "observation_context": "one surviving roommate reported seeing a masked person inside the house",
        "eyewitness_to_killings_established": False,
    }
    assert case["known_outcome"] == {
        "unit": "four direct homicide victims",
        "occupants": 4,
        "survivors": 0,
        "fatalities": 4,
        "class": "fatal_dominant",
    }
    assert set(case["event_source_ids"]) == {
        "idaho_court_homicide_window",
        "idaho_court_surviving_roommates_order",
        "idaho_court_plea_agreement",
        "idaho_court_case_summary",
        "moscow_police_homicide_facts",
        "moscow_police_victim_ages",
        "moscow_police_king_road_outcome",
        "moscow_kohberger_sentencing_outcome",
    }
    assert all(sources[source_id]["kind"].startswith("official_") for source_id in case["event_source_ids"])
    assert case["event_anchor"]["anchor_kind"] == "official_incident_interval_midpoint"
    assert case["event_anchor"]["uncertainty_minutes"] == 12.5
    assert case["event_anchor"]["sensitivity_times_local"] == ["04:00:00", "04:12:30", "04:25:00"]
    assert "not asserted as any victim's exact time of death" in case["event_anchor"]["notes"]

    assert len(case["fact_checks"]) == 6
    assert all(check["source_ids"] for check in case["fact_checks"])
    assert all(
        source_id in sources and sources[source_id]["kind"].startswith("official_")
        for check in case["fact_checks"]
        for source_id in check["source_ids"]
    )


def test_idaho_engine_output_matches_six_predeclared_hard_fact_checks(benchmark_report):
    assert benchmark_report["overall_status"] == "pass"
    assert benchmark_report["summary"] == {
        "hard_checks_passed": 6,
        "hard_checks_total": 6,
        "time_window_stable": True,
        "route_error_count": 0,
    }
    assert {item["id"]: item["status"] for item in benchmark_report["fact_comparisons"]} == {
        "homicide_event_family": "pass",
        "not_accident_or_disaster": "pass",
        "not_water_or_drowning": "pass",
        "not_abduction_or_missing_person": "pass",
        "no_child_victim": "pass",
        "fatal_outcome_direction": "pass",
    }

    engine_result = benchmark_report["engine_result"]
    assert engine_result["predicted_axes"] == ["violence_homicide", "deception_coverup"]
    assert engine_result["matched_axes"] == ["violence_homicide"]
    assert engine_result["missed_axes"] == []
    assert engine_result["contradicted_axes"] == []
    assert engine_result["survivability"]["actual_level"] == "Lower"
    assert engine_result["survivability"]["actual_band"] == "fatal_pressure_dominant"
    assert engine_result["survivability"]["actual_score"] == -2.92

    assert benchmark_report["unscored_engine_outputs"] == ["deception_coverup"]
    assert benchmark_report["unclassified_engine_outputs"] == []
    assert benchmark_report["relationship_observation"] == {
        "documented_target": {
            "confidence": "limited",
            "meaning": RELATIONSHIP_TARGET_MEANING,
        },
        "engine_primary": "stranger_public",
        "status": "not_scored",
    }
    assert engine_result["relationship"]["expected_labels"] == []


def test_idaho_result_is_stable_across_the_official_homicide_interval(benchmark_report):
    sensitivity = benchmark_report["time_sensitivity"]
    observations = sensitivity["observations"]

    assert sensitivity["stable"] is True
    assert [item["time_local"] for item in observations] == ["04:00:00", "04:12:30", "04:25:00"]
    for observation in observations:
        assert observation == {
            "time_local": observation["time_local"],
            "status": "ok",
            "predicted_axes": ["violence_homicide", "deception_coverup"],
            "survivability": {
                "level": "Lower",
                "band": "fatal_pressure_dominant",
                "score": -2.92,
            },
            "relationship_primary": "stranger_public",
        }


def test_idaho_markdown_report_exposes_unscored_outputs(benchmark_report):
    markdown = idaho_runner.render_markdown_report(benchmark_report)

    assert "Hard factual checks: 6/6 passed" in markdown
    assert "`['deception_coverup']`" in markdown
    assert "observational only, not included in the hard score" in markdown
    assert "retrospective, in-sample regression benchmark" in markdown
