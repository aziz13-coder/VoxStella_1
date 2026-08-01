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


DATASET_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_recent_documentaries_2025_2026_cases.json"
CASE_ID = "netflix_idaho_murders_college_nightmare_2026"
EXPECTED_HARD_NEGATIVES = {
    "accident_or_disaster",
    "water_disappearance_or_drowning",
    "domestic_partner_involvement",
    "family_involvement",
    "child_victim",
}


def _load_payload_and_case():
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    case = next(item for item in payload["cases"] if item["id"] == CASE_ID)
    return payload, case


def _run_anchor(case, time_local):
    query = runner.build_forensic_query(case)
    query["datetime"] = f"2022-11-13T{time_local}"
    query["secondary_factors"] = "0"
    route_result = runner._call_forensic_route(query)
    payload = route_result.get("payload") or {}
    assert route_result.get("status_code") == 200
    assert payload.get("success") is True
    survivability = payload.get("survivability") or {}
    relationship = payload.get("relationship_status") or {}
    return {
        "predicted_axes": runner.derive_predicted_axes(payload),
        "survivability_level": survivability.get("level"),
        "survivability_band": survivability.get("outcome_band"),
        "survivability_score": survivability.get("score"),
        "relationship": relationship.get("primary_label"),
    }


def test_idaho_benchmark_ground_truth_is_adjudicated_and_interval_aware():
    payload, case = _load_payload_and_case()
    sources = {source["id"]: source for source in payload["sources"]}

    assert case["known_facts"] == {
        "legal_status": "adjudicated_by_guilty_plea_and_sentencing",
        "offenses": ["one burglary count", "four first-degree murder counts"],
        "event_date_local": "2022-11-13",
        "event_time_window_local": "04:00-04:25",
        "scene": "occupied off-campus residence at 1122 King Road",
        "cause_and_manner": "four homicide deaths by stabbing",
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
        "moscow_police_king_road_outcome",
        "moscow_kohberger_sentencing_outcome",
    }
    assert all(sources[source_id]["kind"].startswith("official_") for source_id in case["event_source_ids"])
    assert case["event_anchor"]["anchor_kind"] == "official_incident_interval_midpoint"
    assert case["event_anchor"]["uncertainty_minutes"] == 12.5
    assert case["event_anchor"]["sensitivity_times_local"] == ["04:00:00", "04:12:30", "04:25:00"]
    assert "not asserted as any victim's exact time of death" in case["event_anchor"]["notes"]


def test_idaho_engine_output_matches_seven_predeclared_hard_fact_checks():
    _, case = _load_payload_and_case()
    report = runner.run_statistical_benchmark_suite(
        [DATASET_PATH],
        case_id=CASE_ID,
        include_control_cases=False,
        bootstrap_iterations=0,
    )

    assert report["route_error_count"] == 0
    assert report["case_count"] == 1
    result = report["case_results"][0]
    predicted_axes = set(result["predicted_axes"])

    hard_checks = {
        "homicide_detected": "violence_homicide" in predicted_axes,
        **{f"no_{axis}": axis not in predicted_axes for axis in EXPECTED_HARD_NEGATIVES},
        "fatal_outcome_direction": result["survivability"]["comparison"] == "aligned",
    }
    assert len(hard_checks) == 7
    assert all(hard_checks.values()), hard_checks
    assert result["status"] == "aligned"
    assert result["matched_axes"] == ["violence_homicide"]
    assert result["missed_axes"] == []
    assert result["contradicted_axes"] == []
    assert result["survivability"]["actual_level"] == "Lower"
    assert result["survivability"]["actual_band"] == "fatal_pressure_dominant"
    assert result["survivability"]["actual_score"] == -2.92
    assert result["relationship"]["predicted_primary"] == "stranger_public"
    assert case["relationship_target"]["confidence"] == "limited"

    # These are explicit current-baseline observations, not hidden successes.
    assert predicted_axes - {"violence_homicide"} == {"deception_coverup"}
    assert "deception_coverup" in case["comparison_policy"]["unscored_outputs"]
    assert "accomplice_or_witness" not in predicted_axes
    assert "accomplice_or_witness" in case["comparison_policy"]["unscored_outputs"]


def test_idaho_result_is_stable_across_the_official_homicide_interval():
    _, case = _load_payload_and_case()
    observations = [
        _run_anchor(case, time_local)
        for time_local in case["event_anchor"]["sensitivity_times_local"]
    ]

    assert observations == [
        {
            "predicted_axes": ["violence_homicide", "deception_coverup"],
            "survivability_level": "Lower",
            "survivability_band": "fatal_pressure_dominant",
            "survivability_score": -2.92,
            "relationship": "stranger_public",
        }
    ] * 3
