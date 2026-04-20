from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import astrocartography_goal_models as goal_models_module
from astrocartography_goal_engine import (
    evaluate_accident_pressure_heuristic,
    evaluate_benefic_minus_malefic_heuristic,
    evaluate_malefic_minus_benefic_heuristic,
    evaluate_goal_model,
    extract_relocation_features,
    list_goal_model_summaries,
)
from astrocartography_goal_models import get_goal_model


def test_goal_model_summaries_include_first_four_profiles():
    ids = {item["id"] for item in list_goal_model_summaries()}
    assert {"education", "love", "work", "money"}.issubset(ids)
    assert {"home", "partners", "beliefs", "friends", "career", "sex"}.issubset(ids)
    assert {"personal_growth", "body_presence", "communication", "conflict", "protective_places", "accident_prone"}.issubset(ids)
    assert {"love_commitment", "money_stable_income", "career_public_profile", "home_retreat"}.issubset(ids)
    assert {"gambling_luck", "health_risk", "travel_fun", "travel_relax"}.issubset(ids)
    assert "risk_pressure" not in ids


def test_extract_relocation_features_maps_houses_and_angles():
    chart_data = {
        "planets": {
            "Venus": {"house": 7},
            "Moon": {"house": 4},
            "Jupiter": {"house": 10},
            "Mercury": {"house": 3},
        }
    }

    features = extract_relocation_features(chart_data)

    assert features["planet_houses"]["Venus"] == 7
    assert features["planet_angles"]["Venus"] == "DSC"
    assert features["planet_angles"]["Moon"] == "IC"
    assert features["metrics"]["partnership"] > 0
    assert "community" in features["metrics"]
    assert "career_status" in features["metrics"]
    assert "personal_growth" in features["metrics"]
    assert "body_presence" in features["metrics"]
    assert "communication" in features["metrics"]
    assert "conflict_pressure" in features["metrics"]
    assert "travel_joy" in features["metrics"]
    assert "restoration" in features["metrics"]
    assert "speculation" in features["metrics"]
    assert "health_risk" in features["metrics"]


def test_extract_relocation_features_exposes_speculation_and_health_risk_metrics():
    features = extract_relocation_features(
        {
            "planets": {
                "Jupiter": {"house": 5},
                "Venus": {"house": 2},
                "Mercury": {"house": 11},
                "Mars": {"house": 6},
                "Saturn": {"house": 8},
                "Neptune": {"house": 12},
            }
        }
    )

    assert features["metrics"]["speculation"] > 0
    assert features["metrics"]["speculation_drag"] > 0
    assert features["metrics"]["health_risk"] > 0


def test_extract_relocation_features_treats_speculation_as_upside_plus_drag():
    benefic_features = extract_relocation_features(
        {
            "planets": {
                "Jupiter": {"house": 5},
                "Venus": {"house": 11},
                "Mercury": {"house": 5},
                "Sun": {"house": 11},
            }
        }
    )
    harsh_features = extract_relocation_features(
        {
            "planets": {
                "Saturn": {"house": 5},
                "Neptune": {"house": 8},
                "Mars": {"house": 2},
                "Uranus": {"house": 11},
            }
        }
    )

    assert benefic_features["metrics"]["speculation"] > harsh_features["metrics"]["speculation"]
    assert harsh_features["metrics"]["speculation_drag"] > benefic_features["metrics"]["speculation_drag"]


def test_extract_relocation_features_exposes_curated_gambling_metrics():
    features = extract_relocation_features(
        {
            "planets": {
                "Mars": {"house": 1, "dignity_score": 5, "retrograde": False, "solar_condition": "free"},
                "Venus": {"house": 10, "dignity_score": 4, "retrograde": False, "solar_condition": "free"},
                "Moon": {"house": 5},
                "Jupiter": {"house": 11, "dignity_score": 3},
                "Saturn": {"house": 8},
            },
            "house_rulers": {"1": "Mars", "2": "Venus", "5": "Venus", "8": "Saturn", "11": "Jupiter"},
            "considerations": {"moon_void": False},
            "moon_next_aspect": {"planet": "Venus", "aspect": "Trine", "applying": True},
            "aspects": [
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Trine", "applying": True},
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Sextile", "applying": True},
            ],
        }
    )

    assert features["details"]["asc_ruler"] == "Mars"
    assert features["details"]["gambling_ruler"] == "Venus"
    assert features["metrics"]["asc_ruler_strength"] > 0.5
    assert features["metrics"]["gambling_ruler_strength"] > 0.5
    assert features["metrics"]["asc_gambling_harmony"] > 0.5
    assert features["metrics"]["moon_gambling_support"] > 0.3
    assert features["metrics"]["retrograde_liability"] == 0.0
    assert "patterns" in features["details"]


def test_extract_relocation_features_detects_supportive_and_hard_geometry():
    supportive = extract_relocation_features(
        {
            "planets": {
                "Sun": {"house": 1, "dignity_score": 2},
                "Jupiter": {"house": 5, "dignity_score": 5},
                "Venus": {"house": 9, "dignity_score": 4},
                "Mercury": {"house": 11, "dignity_score": 3},
            },
            "aspects": [
                {"planet1": "Sun", "planet2": "Jupiter", "aspect": "Trine", "orb": 1.0, "applying": True},
                {"planet1": "Sun", "planet2": "Venus", "aspect": "Trine", "orb": 1.2, "applying": True},
                {"planet1": "Jupiter", "planet2": "Venus", "aspect": "Trine", "orb": 0.8, "applying": True},
                {"planet1": "Mercury", "planet2": "Sun", "aspect": "Opposition", "orb": 1.1, "applying": True},
                {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Sextile", "orb": 0.9, "applying": True},
                {"planet1": "Mercury", "planet2": "Venus", "aspect": "Sextile", "orb": 1.0, "applying": True},
            ],
        }
    )
    harsh = extract_relocation_features(
        {
            "planets": {
                "Moon": {"house": 12, "dignity_score": -3},
                "Mars": {"house": 6, "dignity_score": -2},
                "Saturn": {"house": 8, "dignity_score": -4},
            },
            "aspects": [
                {"planet1": "Moon", "planet2": "Mars", "aspect": "Square", "orb": 0.7, "applying": True},
                {"planet1": "Moon", "planet2": "Saturn", "aspect": "Square", "orb": 1.0, "applying": True},
                {"planet1": "Mars", "planet2": "Saturn", "aspect": "Opposition", "orb": 0.6, "applying": True},
            ],
        }
    )

    assert supportive["metrics"]["grand_trine_support"] > 0.2
    assert supportive["metrics"]["kite_support"] > 0.15
    assert supportive["metrics"]["pattern_support"] >= supportive["metrics"]["grand_trine_support"]
    assert len(supportive["details"]["patterns"]["grand_trines"]) == 1
    assert len(supportive["details"]["patterns"]["kites"]) == 1
    assert harsh["metrics"]["t_square_pressure"] > 0.2
    assert harsh["metrics"]["pattern_pressure"] == harsh["metrics"]["t_square_pressure"]
    assert len(harsh["details"]["patterns"]["t_squares"]) == 1


def test_extract_relocation_features_detects_asc_interception_from_house_cusps():
    features = extract_relocation_features(
        {
            "house_cusps": [10.0, 80.0, 110.0, 140.0, 170.0, 185.0, 190.0, 260.0, 290.0, 320.0, 350.0, 5.0],
        }
    )

    assert features["metrics"]["asc_interception"] == 1.0
    assert "Taurus" in features["details"]["asc_intercepted_signs"]
    assert "Scorpio" in features["details"]["asc_intercepted_signs"]
    assert features["details"]["intercepted_signs"][1] == ["Taurus"]
    assert features["details"]["intercepted_signs"][7] == ["Scorpio"]


def test_extract_relocation_features_detects_explicit_asc_support_and_south_node_obstruction():
    features = extract_relocation_features(
        {
            "ascendant": 0.0,
            "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "planets": {
                "Mars": {"house": 1, "longitude": 120.0, "dignity_score": 4},
                "Venus": {"house": 10, "longitude": 60.0, "dignity_score": 3},
                "Moon": {"house": 5, "longitude": 0.0},
                "North Node": {"house": 7, "longitude": 180.0},
            },
            "house_rulers": {"1": "Mars", "5": "Venus"},
        }
    )

    assert features["metrics"]["asc_ruler_asc_support"] > 0.9
    assert features["metrics"]["gambling_ruler_asc_support"] > 0.9
    assert features["metrics"]["moon_asc_support"] > 0.9
    assert features["metrics"]["south_node_obstruction"] > 0.6
    assert features["details"]["asc_ruler_asc_hit"]["aspect"] == "trine"
    assert features["details"]["gambling_ruler_asc_hit"]["aspect"] == "sextile"
    assert features["details"]["moon_asc_hit"]["aspect"] == "conjunction"
    assert features["details"]["south_node_house"] == 1


def test_extract_relocation_features_penalizes_void_and_retrograde_gambling_signatures():
    features = extract_relocation_features(
        {
            "planets": {
                "Mars": {"house": 12, "dignity_score": -4, "retrograde": True, "solar_condition": "combust"},
                "Venus": {"house": 8, "dignity_score": -2, "retrograde": True, "solar_condition": "under_beams"},
                "Moon": {"house": 12},
                "Saturn": {"house": 5},
            },
            "house_rulers": {"1": "Mars", "2": "Saturn", "5": "Venus", "8": "Saturn", "11": "Saturn"},
            "considerations": {"moon_void": True},
            "moon_next_aspect": {"planet": "Saturn", "aspect": "Square", "applying": True},
            "aspects": [
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Opposition", "applying": True},
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Square", "applying": True},
            ],
        }
    )

    assert features["details"]["moon_void"] is True
    assert features["metrics"]["asc_gambling_tension"] > 0.5
    assert features["metrics"]["moon_liability"] > 0.7
    assert features["metrics"]["retrograde_liability"] > 0.7


def test_evaluate_goal_model_scores_love_location_from_lines_crossings_and_relocation():
    natal_rows = [
        {
            "id": "Venus:DSC",
            "body": "Venus",
            "angle": "DSC",
            "label": "Venus DSC",
            "distance_km": 60.0,
            "zone": "primary",
        },
        {
            "id": "Moon:IC",
            "body": "Moon",
            "angle": "IC",
            "label": "Moon IC",
            "distance_km": 110.0,
            "zone": "primary",
        },
    ]
    natal_crossings = [
        {
            "id": "Venus:DSC|Moon:IC",
            "label": "Venus DSC x Moon IC",
            "planets": ["Venus", "Moon"],
            "distance_km": 80.0,
            "zone": "primary",
        }
    ]
    relocation = extract_relocation_features(
        {
            "planets": {
                "Venus": {"house": 7},
                "Moon": {"house": 4},
                "Jupiter": {"house": 5},
            }
        }
    )

    evaluation = evaluate_goal_model(
        "love",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        relocation=relocation,
    )

    assert evaluation["goal"]["id"] == "love"
    assert evaluation["score"] > 60
    assert evaluation["breakdown"]["natal"] > 0
    assert evaluation["breakdown"]["relocation"] > 0
    assert any(item["kind"] == "crossing" for item in evaluation["contributions"])
    assert any(item["kind"] == "modifier" for item in evaluation["contributions"])


def test_goal_model_loader_returns_expected_legacy_refs():
    model = get_goal_model("money")
    legacy_files = {item["source_file"] for item in model["legacy_refs"]}
    assert "GMU 01c.PLS" in legacy_files
    assert "MONEY.HYP" in legacy_files


def test_goal_model_loader_returns_second_wave_legacy_refs():
    model = get_goal_model("career")
    legacy_files = {item["source_file"] for item in model["legacy_refs"]}
    assert "CAREER.HYP" in legacy_files


def test_goal_model_loader_returns_advanced_legacy_refs():
    model = get_goal_model("communication")
    legacy_files = {item["source_file"] for item in model["legacy_refs"]}
    assert "CHATTER.HYP" in legacy_files
    assert "COMMUNICATION_BROTHER_SISTER.HYP" in legacy_files


def test_work_and_money_specialists_include_external_legacy_refs():
    work = get_goal_model("work")
    stable_income = get_goal_model("money_stable_income")

    assert "WORK__SERVICE _SICKNESS_.HYP" in {item["source_file"] for item in work["legacy_refs"]}
    assert "MONEY_GAINS_INVESTMENTS.HYP" in {item["source_file"] for item in stable_income["legacy_refs"]}


def test_beliefs_and_sex_models_include_constraints_and_expected_legacy_refs():
    beliefs = get_goal_model("beliefs")
    sex = get_goal_model("sex")

    assert "BELIEFS.HYP" in {item["source_file"] for item in beliefs["legacy_refs"]}
    assert "SEX.HYP" in {item["source_file"] for item in sex["legacy_refs"]}
    assert any(item["kind"] == "constraint" for item in beliefs["score_components"])
    assert any(item["kind"] == "constraint" for item in sex["score_components"])


def test_new_models_include_source_backing_refs():
    accident_prone = get_goal_model("accident_prone")
    risk_pressure = get_goal_model("risk_pressure")
    protective_places = get_goal_model("protective_places")
    gambling = get_goal_model("gambling_luck")
    health_risk = get_goal_model("health_risk")
    body_presence = get_goal_model("body_presence")
    travel_fun = get_goal_model("travel_fun")
    travel_relax = get_goal_model("travel_relax")

    assert any(item["kind"] == "doc" and "baselines.py" in item["source_file"] for item in accident_prone["legacy_refs"])
    assert accident_prone["evaluation_strategy"] == "accident_pressure"
    assert accident_prone["transit_strategy"] == "ignore"
    assert accident_prone["status"] == "active"
    assert any(item["kind"] == "doc" and "baselines.py" in item["source_file"] for item in risk_pressure["legacy_refs"])
    assert any(item["kind"] == "doc" and "baselines.py" in item["source_file"] for item in protective_places["legacy_refs"])
    assert any(item["kind"] == "doc" and "morin_engine_knowledge_map.md" in item["source_file"] for item in gambling["legacy_refs"])
    assert any(item["kind"] == "doc" and "06_extended_goal_domains.md" in item["source_file"] for item in gambling["legacy_refs"])
    assert any(item["kind"] == "hyp" and "Gambling_Elect_Personal.hyp" in item["source_file"] for item in gambling["legacy_refs"])
    assert any(item["kind"] == "hyp" and "WORK__SERVICE _SICKNESS_.HYP" in item["source_file"] for item in health_risk["legacy_refs"])
    assert any(item["kind"] == "doc" and "transits_morin.py" in item["source_file"] for item in health_risk["legacy_refs"])
    assert any(item["kind"] == "doc" and "06_extended_goal_domains.md" in item["source_file"] for item in health_risk["legacy_refs"])
    assert any(item["kind"] == "hyp" and "PERSONALITY_THE BODY_APPEARANCE.HYP" in item["source_file"] for item in body_presence["legacy_refs"])
    assert any(item["kind"] == "doc" and "morin_engine_knowledge_map.md" in item["source_file"] for item in body_presence["legacy_refs"])
    assert any(item["kind"] == "hyp" and "LOVE_CHILDREN_SPECULATION.HYP" in item["source_file"] for item in travel_fun["legacy_refs"])
    assert any(item["kind"] == "doc" and "morin_engine_knowledge_map.md" in item["source_file"] for item in travel_fun["legacy_refs"])
    assert any(item["kind"] == "hyp" and "HOME.HYP" in item["source_file"] for item in travel_relax["legacy_refs"])
    assert any(item["kind"] == "doc" and "morin_engine_knowledge_map.md" in item["source_file"] for item in travel_relax["legacy_refs"])
    assert gambling["evaluation_strategy"] == "gambling_natal_curated"
    assert gambling["transit_strategy"] == "ignore"
    assert protective_places["evaluation_strategy"] == "benefic_minus_malefic"
    assert protective_places["transit_strategy"] == "ignore"
    assert protective_places["status"] == "active"
    assert risk_pressure["evaluation_strategy"] == "malefic_minus_benefic"
    assert risk_pressure["transit_strategy"] == "ignore"
    assert risk_pressure["status"] == "deprecated"
    assert health_risk["status"] == "active"
    assert travel_fun["goal_family"] == "travel"
    assert travel_relax["goal_family"] == "travel"


def test_accident_prone_goal_uses_shared_accident_pressure_heuristic():
    natal_rows = [
        {"body": "Mars", "angle": "ASC", "label": "Mars ASC", "distance_km": 20.0},
        {"body": "Uranus", "angle": "MC", "label": "Uranus MC", "distance_km": 55.0},
        {"body": "Jupiter", "angle": "IC", "label": "Jupiter IC", "distance_km": 70.0},
    ]
    natal_crossings = [
        {"planets": ["Mars", "Uranus"], "label": "Mars/Uranus", "distance_km": 60.0},
    ]
    relocation = {
        "metrics": {
            "health_risk": 0.6,
            "malefic_pressure": 0.5,
            "uncertainty": 0.25,
            "conflict_pressure": 0.2,
            "benefic_balance": 0.1,
            "stability": 0.05,
        }
    }

    product = evaluate_goal_model(
        "accident_prone",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        relocation=relocation,
        transit_rows=[{"body": "Mars", "angle": "ASC", "label": "Transit Mars ASC", "distance_km": 5.0}],
        transit_crossings=[{"planets": ["Mars", "Uranus"], "label": "Transit Mars/Uranus", "distance_km": 5.0}],
    )
    heuristic = evaluate_accident_pressure_heuristic(
        result_id="accident_prone",
        result_label="Prone to Accidents",
        result_summary="test",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        relocation=relocation,
    )

    assert product["raw_score"] == heuristic["raw_score"]
    assert product["score"] == heuristic["score"]
    assert product["breakdown"]["transit"] == 0.0


def test_goal_model_loader_refreshes_when_runtime_payload_changes(tmp_path, monkeypatch):
    payload_path = tmp_path / "place_goal_models.runtime.json"
    payload_path.write_text(
        '{"models":[{"id":"education","label":"Education","version":"1.0.0","status":"active","summary":"One","score_components":[{"kind":"modifier","metric":"visibility","weight":1.0,"rationale":"x"}]}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(goal_models_module, "GOAL_MODEL_PATH", payload_path)
    goal_models_module._load_goal_model_payload_cached.cache_clear()

    first = goal_models_module.load_goal_model_payload()
    assert len(first["models"]) == 1
    assert first["models"][0]["id"] == "education"

    payload_path.write_text(
        '{"models":[{"id":"education","label":"Education","version":"1.0.0","status":"active","summary":"One","score_components":[{"kind":"modifier","metric":"visibility","weight":1.0,"rationale":"x"}]},{"id":"gambling_luck","label":"Gambling Luck","version":"1.0.0","status":"active","summary":"Two","score_components":[{"kind":"modifier","metric":"speculation","weight":1.0,"rationale":"y"}]}]}',
        encoding="utf-8",
    )

    second = goal_models_module.load_goal_model_payload()
    ids = {item["id"] for item in second["models"]}
    assert ids == {"education", "gambling_luck"}


def test_evaluate_goal_model_applies_constraint_adjustments():
    relocation = extract_relocation_features(
        {
            "planets": {
                "Venus": {"house": 7},
                "Moon": {"house": 4},
                "Jupiter": {"house": 5},
                "Uranus": {"house": 7},
                "Neptune": {"house": 10},
            }
        }
    )

    evaluation = evaluate_goal_model(
        "love_commitment",
        natal_rows=[
            {"body": "Venus", "angle": "DSC", "label": "Venus DSC", "distance_km": 40.0},
            {"body": "Moon", "angle": "IC", "label": "Moon IC", "distance_km": 60.0},
        ],
        natal_crossings=[
            {"planets": ["Venus", "Moon"], "label": "Venus DSC x Moon IC", "distance_km": 75.0},
        ],
        relocation=relocation,
    )

    assert any(item["kind"] == "constraint" for item in evaluation["contributions"])
    assert evaluation["breakdown"]["constraints"] < 0
    assert evaluation["score"] < 100


def test_beliefs_model_penalizes_high_uncertainty():
    relocation = extract_relocation_features(
        {
            "planets": {
                "Jupiter": {"house": 9},
                "Mercury": {"house": 3},
                "Sun": {"house": 9},
                "Neptune": {"house": 12},
                "Uranus": {"house": 9},
                "Moon": {"house": 12},
            }
        }
    )

    evaluation = evaluate_goal_model(
        "beliefs",
        natal_rows=[
            {"body": "Jupiter", "angle": "MC", "label": "Jupiter MC", "distance_km": 45.0},
            {"body": "Mercury", "angle": "ASC", "label": "Mercury ASC", "distance_km": 90.0},
        ],
        natal_crossings=[
            {"planets": ["Jupiter", "Mercury"], "label": "Jupiter MC x Mercury ASC", "distance_km": 75.0},
        ],
        relocation=relocation,
    )

    assert any(item["kind"] == "constraint" for item in evaluation["contributions"])
    assert evaluation["breakdown"]["constraints"] < 0


def test_sex_model_caps_high_pressure_results():
    relocation = extract_relocation_features(
        {
            "planets": {
                "Venus": {"house": 7},
                "Mars": {"house": 1},
                "Pluto": {"house": 8},
                "Moon": {"house": 5},
                "Saturn": {"house": 7},
                "Uranus": {"house": 8},
                "Neptune": {"house": 12},
            }
        }
    )

    evaluation = evaluate_goal_model(
        "sex",
        natal_rows=[
            {"body": "Venus", "angle": "DSC", "label": "Venus DSC", "distance_km": 30.0},
            {"body": "Mars", "angle": "ASC", "label": "Mars ASC", "distance_km": 35.0},
            {"body": "Pluto", "angle": "DSC", "label": "Pluto DSC", "distance_km": 80.0},
        ],
        natal_crossings=[
            {"planets": ["Venus", "Mars"], "label": "Venus DSC x Mars ASC", "distance_km": 40.0},
            {"planets": ["Mars", "Saturn"], "label": "Mars ASC x Saturn DSC", "distance_km": 100.0},
        ],
        relocation=relocation,
    )

    assert any(item["kind"] == "constraint" for item in evaluation["contributions"])
    assert evaluation["breakdown"]["constraints"] < 0


def test_gambling_luck_model_prefers_benefic_speculation_signatures():
    relocation = extract_relocation_features(
        {
            "planets": {
                "Mars": {"house": 1, "dignity_score": 5, "retrograde": False, "solar_condition": "free"},
                "Venus": {"house": 10, "dignity_score": 4, "retrograde": False, "solar_condition": "free"},
                "Moon": {"house": 5},
                "Jupiter": {"house": 11, "dignity_score": 4},
                "Mercury": {"house": 2, "dignity_score": 2},
                "Saturn": {"house": 6},
            },
            "house_rulers": {"1": "Mars", "2": "Mercury", "5": "Venus", "8": "Saturn", "11": "Jupiter"},
            "considerations": {"moon_void": False},
            "moon_next_aspect": {"planet": "Venus", "aspect": "Trine", "applying": True},
            "aspects": [
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Trine", "applying": True},
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Sextile", "applying": True},
            ],
        }
    )

    evaluation = evaluate_goal_model(
        "gambling_luck",
        natal_rows=[
            {"body": "Jupiter", "angle": "MC", "label": "Jupiter MC", "distance_km": 25.0},
            {"body": "Venus", "angle": "ASC", "label": "Venus ASC", "distance_km": 45.0},
            {"body": "Mercury", "angle": "MC", "label": "Mercury MC", "distance_km": 80.0},
        ],
        natal_crossings=[
            {"planets": ["Jupiter", "Venus"], "label": "Jupiter MC x Venus ASC", "distance_km": 55.0},
            {"planets": ["Mercury", "Jupiter"], "label": "Mercury MC x Jupiter MC", "distance_km": 95.0},
        ],
        relocation=relocation,
    )

    assert evaluation["goal"]["id"] == "gambling_luck"
    assert evaluation["score"] > 60
    assert evaluation["breakdown"]["relocation"] > 0
    assert any(item["kind"] == "modifier" and item.get("metric") == "asc_ruler_strength" for item in evaluation["contributions"])
    assert any(item["kind"] == "modifier" and item.get("metric") == "gambling_ruler_strength" for item in evaluation["contributions"])
    assert any(item["kind"] == "modifier" and item.get("metric") == "asc_gambling_harmony" for item in evaluation["contributions"])
    assert any(item["kind"] == "modifier" and item.get("metric") == "moon_gambling_support" for item in evaluation["contributions"])


def test_gambling_luck_model_scores_chart_pattern_geometry():
    relocation = extract_relocation_features(
        {
            "planets": {
                "Mars": {"house": 1, "dignity_score": 5, "retrograde": False, "solar_condition": "free"},
                "Venus": {"house": 10, "dignity_score": 4, "retrograde": False, "solar_condition": "free"},
                "Moon": {"house": 5, "dignity_score": 2},
                "Jupiter": {"house": 11, "dignity_score": 4},
                "Mercury": {"house": 7, "dignity_score": 3},
            },
            "house_rulers": {"1": "Mars", "2": "Venus", "5": "Venus", "8": "Saturn", "11": "Jupiter"},
            "considerations": {"moon_void": False},
            "moon_next_aspect": {"planet": "Venus", "aspect": "Trine", "applying": True},
            "aspects": [
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Trine", "orb": 0.9, "applying": True},
                {"planet1": "Mars", "planet2": "Jupiter", "aspect": "Trine", "orb": 1.2, "applying": True},
                {"planet1": "Venus", "planet2": "Jupiter", "aspect": "Trine", "orb": 1.0, "applying": True},
                {"planet1": "Mercury", "planet2": "Mars", "aspect": "Opposition", "orb": 1.1, "applying": True},
                {"planet1": "Mercury", "planet2": "Venus", "aspect": "Sextile", "orb": 0.8, "applying": True},
                {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Sextile", "orb": 0.9, "applying": True},
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Sextile", "applying": True},
            ],
        }
    )

    evaluation = evaluate_goal_model(
        "gambling_luck",
        natal_rows=[
            {"body": "Jupiter", "angle": "MC", "label": "Jupiter MC", "distance_km": 25.0},
            {"body": "Venus", "angle": "ASC", "label": "Venus ASC", "distance_km": 45.0},
        ],
        natal_crossings=[
            {"planets": ["Jupiter", "Venus"], "label": "Jupiter MC x Venus ASC", "distance_km": 55.0},
        ],
        relocation=relocation,
    )

    assert relocation["metrics"]["pattern_support"] > 0.2
    assert any(item["kind"] == "modifier" and item.get("metric") == "grand_trine_support" for item in evaluation["contributions"])
    assert any(item["kind"] == "modifier" and item.get("metric") == "kite_support" for item in evaluation["contributions"])


def test_gambling_luck_model_penalizes_void_moon_and_broken_ruler_links():
    favorable = extract_relocation_features(
        {
            "planets": {
                "Mars": {"house": 1, "dignity_score": 5, "retrograde": False, "solar_condition": "free"},
                "Venus": {"house": 10, "dignity_score": 4, "retrograde": False, "solar_condition": "free"},
                "Moon": {"house": 5},
                "Jupiter": {"house": 11},
            },
            "house_rulers": {"1": "Mars", "2": "Venus", "5": "Venus", "8": "Saturn", "11": "Jupiter"},
            "considerations": {"moon_void": False},
            "moon_next_aspect": {"planet": "Venus", "aspect": "Trine", "applying": True},
            "aspects": [
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Trine", "applying": True},
            ],
        }
    )
    broken = extract_relocation_features(
        {
            "planets": {
                "Mars": {"house": 12, "dignity_score": -4, "retrograde": True, "solar_condition": "combust"},
                "Venus": {"house": 8, "dignity_score": -2, "retrograde": True, "solar_condition": "under_beams"},
                "Moon": {"house": 12},
                "Saturn": {"house": 5},
                "Neptune": {"house": 2},
            },
            "house_rulers": {"1": "Mars", "2": "Neptune", "5": "Venus", "8": "Saturn", "11": "Saturn"},
            "considerations": {"moon_void": True},
            "moon_next_aspect": {"planet": "Saturn", "aspect": "Square", "applying": True},
            "aspects": [
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Opposition", "applying": True},
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Square", "applying": True},
            ],
        }
    )

    favorable_eval = evaluate_goal_model(
        "gambling_luck",
        natal_rows=[
            {"body": "Jupiter", "angle": "MC", "label": "Jupiter MC", "distance_km": 25.0},
            {"body": "Venus", "angle": "ASC", "label": "Venus ASC", "distance_km": 45.0},
        ],
        natal_crossings=[{"planets": ["Jupiter", "Venus"], "label": "Jupiter MC x Venus ASC", "distance_km": 55.0}],
        relocation=favorable,
    )
    broken_eval = evaluate_goal_model(
        "gambling_luck",
        natal_rows=[
            {"body": "Neptune", "angle": "ASC", "label": "Neptune ASC", "distance_km": 20.0},
            {"body": "Saturn", "angle": "MC", "label": "Saturn MC", "distance_km": 35.0},
        ],
        natal_crossings=[{"planets": ["Mars", "Saturn"], "label": "Mars ASC x Saturn MC", "distance_km": 40.0}],
        relocation=broken,
    )

    assert favorable_eval["score"] > broken_eval["score"]
    assert broken_eval["breakdown"]["relocation"] < favorable_eval["breakdown"]["relocation"]


def test_gambling_luck_model_penalizes_asc_interception():
    base_chart = {
        "planets": {
            "Mars": {"house": 1, "dignity_score": 5, "retrograde": False, "solar_condition": "free"},
            "Venus": {"house": 10, "dignity_score": 4, "retrograde": False, "solar_condition": "free"},
            "Moon": {"house": 5},
            "Jupiter": {"house": 11},
        },
        "house_rulers": {"1": "Mars", "2": "Venus", "5": "Venus", "8": "Saturn", "11": "Jupiter"},
        "considerations": {"moon_void": False},
        "moon_next_aspect": {"planet": "Venus", "aspect": "Trine", "applying": True},
        "aspects": [
            {"planet1": "Mars", "planet2": "Venus", "aspect": "Trine", "applying": True},
        ],
    }
    clean = extract_relocation_features(
        {
            **base_chart,
            "house_cusps": [10.0, 40.0, 70.0, 100.0, 130.0, 160.0, 190.0, 220.0, 250.0, 280.0, 310.0, 340.0],
        }
    )
    intercepted = extract_relocation_features(
        {
            **base_chart,
            "house_cusps": [10.0, 80.0, 110.0, 140.0, 170.0, 185.0, 190.0, 260.0, 290.0, 320.0, 350.0, 5.0],
        }
    )

    clean_eval = evaluate_goal_model(
        "gambling_luck",
        natal_rows=[
            {"body": "Jupiter", "angle": "MC", "label": "Jupiter MC", "distance_km": 25.0},
            {"body": "Venus", "angle": "ASC", "label": "Venus ASC", "distance_km": 45.0},
        ],
        natal_crossings=[{"planets": ["Jupiter", "Venus"], "label": "Jupiter MC x Venus ASC", "distance_km": 55.0}],
        relocation=clean,
    )
    intercepted_eval = evaluate_goal_model(
        "gambling_luck",
        natal_rows=[
            {"body": "Jupiter", "angle": "MC", "label": "Jupiter MC", "distance_km": 25.0},
            {"body": "Venus", "angle": "ASC", "label": "Venus ASC", "distance_km": 45.0},
        ],
        natal_crossings=[{"planets": ["Jupiter", "Venus"], "label": "Jupiter MC x Venus ASC", "distance_km": 55.0}],
        relocation=intercepted,
    )

    assert clean["metrics"]["asc_interception"] == 0.0
    assert intercepted["metrics"]["asc_interception"] == 1.0
    assert clean_eval["raw_score"] > intercepted_eval["raw_score"]
    assert clean_eval["breakdown"]["relocation"] > intercepted_eval["breakdown"]["relocation"]
    assert any(item["kind"] == "modifier" and item.get("metric") == "asc_interception" for item in intercepted_eval["contributions"])


def test_gambling_luck_model_uses_explicit_asc_rules_and_south_node_obstruction():
    supportive = extract_relocation_features(
        {
            "ascendant": 0.0,
            "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "planets": {
                "Mars": {"house": 1, "longitude": 120.0, "dignity_score": 5, "retrograde": False, "solar_condition": "free"},
                "Venus": {"house": 10, "longitude": 60.0, "dignity_score": 4, "retrograde": False, "solar_condition": "free"},
                "Moon": {"house": 5, "longitude": 0.0},
                "Jupiter": {"house": 11, "dignity_score": 4},
                "North Node": {"house": 11, "longitude": 330.0},
            },
            "house_rulers": {"1": "Mars", "2": "Venus", "5": "Venus", "8": "Saturn", "11": "Jupiter"},
            "considerations": {"moon_void": False},
            "moon_next_aspect": {"planet": "Venus", "aspect": "Trine", "applying": True},
            "aspects": [
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Trine", "applying": True},
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Sextile", "applying": True},
            ],
        }
    )
    obstructed = extract_relocation_features(
        {
            "ascendant": 0.0,
            "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "planets": {
                "Mars": {"house": 1, "longitude": 205.0, "dignity_score": 5, "retrograde": False, "solar_condition": "free"},
                "Venus": {"house": 10, "longitude": 150.0, "dignity_score": 4, "retrograde": False, "solar_condition": "free"},
                "Moon": {"house": 5, "longitude": 90.0},
                "Jupiter": {"house": 11, "dignity_score": 4},
                "North Node": {"house": 7, "longitude": 180.0},
            },
            "house_rulers": {"1": "Mars", "2": "Venus", "5": "Venus", "8": "Saturn", "11": "Jupiter"},
            "considerations": {"moon_void": False},
            "moon_next_aspect": {"planet": "Venus", "aspect": "Trine", "applying": True},
            "aspects": [
                {"planet1": "Mars", "planet2": "Venus", "aspect": "Trine", "applying": True},
                {"planet1": "Moon", "planet2": "Venus", "aspect": "Sextile", "applying": True},
            ],
        }
    )

    supportive_eval = evaluate_goal_model(
        "gambling_luck",
        natal_rows=[
            {"body": "Jupiter", "angle": "MC", "label": "Jupiter MC", "distance_km": 25.0},
            {"body": "Venus", "angle": "ASC", "label": "Venus ASC", "distance_km": 45.0},
        ],
        natal_crossings=[{"planets": ["Jupiter", "Venus"], "label": "Jupiter MC x Venus ASC", "distance_km": 55.0}],
        relocation=supportive,
    )
    obstructed_eval = evaluate_goal_model(
        "gambling_luck",
        natal_rows=[
            {"body": "Jupiter", "angle": "MC", "label": "Jupiter MC", "distance_km": 25.0},
            {"body": "Venus", "angle": "ASC", "label": "Venus ASC", "distance_km": 45.0},
        ],
        natal_crossings=[{"planets": ["Jupiter", "Venus"], "label": "Jupiter MC x Venus ASC", "distance_km": 55.0}],
        relocation=obstructed,
    )

    assert supportive["metrics"]["asc_ruler_asc_support"] > obstructed["metrics"]["asc_ruler_asc_support"]
    assert supportive["metrics"]["gambling_ruler_asc_support"] > obstructed["metrics"]["gambling_ruler_asc_support"]
    assert supportive["metrics"]["moon_asc_support"] > obstructed["metrics"]["moon_asc_support"]
    assert obstructed["metrics"]["south_node_obstruction"] > supportive["metrics"]["south_node_obstruction"]
    assert supportive_eval["raw_score"] > obstructed_eval["raw_score"]
    assert any(item["kind"] == "modifier" and item.get("metric") == "asc_ruler_asc_support" for item in supportive_eval["contributions"])
    assert any(item["kind"] == "modifier" and item.get("metric") == "gambling_ruler_asc_support" for item in supportive_eval["contributions"])
    assert any(item["kind"] == "modifier" and item.get("metric") == "moon_asc_support" for item in supportive_eval["contributions"])
    assert any(item["kind"] == "modifier" and item.get("metric") == "south_node_obstruction" for item in obstructed_eval["contributions"])


def test_health_risk_model_prefers_bodily_pressure_signatures():
    relocation = extract_relocation_features(
        {
            "planets": {
                "Mars": {"house": 1},
                "Saturn": {"house": 6},
                "Uranus": {"house": 8},
                "Neptune": {"house": 12},
                "Pluto": {"house": 6},
            }
        }
    )

    evaluation = evaluate_goal_model(
        "health_risk",
        natal_rows=[
            {"body": "Mars", "angle": "ASC", "label": "Mars ASC", "distance_km": 20.0},
            {"body": "Saturn", "angle": "ASC", "label": "Saturn ASC", "distance_km": 35.0},
            {"body": "Uranus", "angle": "ASC", "label": "Uranus ASC", "distance_km": 70.0},
        ],
        natal_crossings=[
            {"planets": ["Mars", "Saturn"], "label": "Mars ASC x Saturn ASC", "distance_km": 40.0},
            {"planets": ["Mars", "Uranus"], "label": "Mars ASC x Uranus ASC", "distance_km": 75.0},
        ],
        relocation=relocation,
    )

    assert evaluation["goal"]["id"] == "health_risk"
    assert evaluation["score"] > 65
    assert evaluation["breakdown"]["relocation"] > 0
    assert any(item["kind"] == "modifier" and item.get("metric") == "health_risk" for item in evaluation["contributions"])


def test_protective_places_model_prefers_generic_benefic_pressure():
    natal_rows = [
        {"body": "Jupiter", "angle": "ASC", "label": "Jupiter ASC", "distance_km": 40.0},
        {"body": "Venus", "angle": "MC", "label": "Venus MC", "distance_km": 44.0},
        {"body": "Mars", "angle": "ASC", "label": "Mars ASC", "distance_km": 70.0},
        {"body": "Saturn", "angle": "DSC", "label": "Saturn DSC", "distance_km": 120.0},
    ]
    natal_crossings = [
        {"planets": ["Jupiter", "Venus"], "label": "Jupiter ASC x Venus MC", "distance_km": 48.0},
        {"planets": ["Mars", "Saturn"], "label": "Mars ASC x Saturn DSC", "distance_km": 120.0},
    ]
    transit_rows = [
        {"body": "Moon", "angle": "IC", "label": "Moon IC", "distance_km": 30.0},
        {"body": "Pluto", "angle": "ASC", "label": "Pluto ASC", "distance_km": 60.0},
    ]

    evaluation = evaluate_goal_model(
        "protective_places",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        relocation=extract_relocation_features({"planets": {}}),
        transit_rows=transit_rows,
        transit_crossings=[],
    )
    expected = evaluate_benefic_minus_malefic_heuristic(
        result_id="protective_places",
        result_label="Protective Places",
        result_summary="Public natal-only model for easier, more protected, and more supportive places. Higher scores mean stronger protection and livability.",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
    )

    assert evaluation["goal"]["id"] == "protective_places"
    assert evaluation["raw_score"] == expected["raw_score"]
    assert evaluation["score"] == expected["score"]
    assert evaluation["breakdown"] == expected["breakdown"]
    assert evaluation["breakdown"]["transit"] == 0.0


def test_risk_pressure_model_prefers_generic_malefic_pressure():
    natal_rows = [
        {"body": "Jupiter", "angle": "ASC", "label": "Jupiter ASC", "distance_km": 40.0},
        {"body": "Mars", "angle": "ASC", "label": "Mars ASC", "distance_km": 22.0},
        {"body": "Saturn", "angle": "MC", "label": "Saturn MC", "distance_km": 44.0},
        {"body": "Uranus", "angle": "DSC", "label": "Uranus DSC", "distance_km": 70.0},
    ]
    natal_crossings = [
        {"planets": ["Mars", "Saturn"], "label": "Mars ASC x Saturn MC", "distance_km": 48.0},
        {"planets": ["Jupiter", "Venus"], "label": "Jupiter ASC x Venus IC", "distance_km": 120.0},
    ]
    transit_rows = [
        {"body": "Moon", "angle": "IC", "label": "Moon IC", "distance_km": 50.0},
        {"body": "Pluto", "angle": "ASC", "label": "Pluto ASC", "distance_km": 110.0},
    ]

    evaluation = evaluate_goal_model(
        "risk_pressure",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        relocation=extract_relocation_features({"planets": {}}),
        transit_rows=transit_rows,
        transit_crossings=[],
    )
    expected = evaluate_malefic_minus_benefic_heuristic(
        result_id="risk_pressure",
        result_label="High-Risk Places",
        result_summary="Research-only natal warning model for harsh, accident-prone, destabilizing, or caution-heavy places. Kept for benchmark comparison, not public use.",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
    )

    assert evaluation["goal"]["id"] == "risk_pressure"
    assert evaluation["raw_score"] == expected["raw_score"]
    assert evaluation["score"] == expected["score"]
    assert evaluation["breakdown"] == expected["breakdown"]
    assert evaluation["breakdown"]["transit"] == 0.0


def test_body_presence_model_prefers_visible_benefic_body_signatures():
    relocation = extract_relocation_features(
        {
            "planets": {
                "Venus": {"house": 1},
                "Sun": {"house": 10},
                "Moon": {"house": 5},
                "Jupiter": {"house": 2},
                "Mars": {"house": 1},
            }
        }
    )

    evaluation = evaluate_goal_model(
        "body_presence",
        natal_rows=[
            {"body": "Venus", "angle": "ASC", "label": "Venus ASC", "distance_km": 18.0},
            {"body": "Sun", "angle": "ASC", "label": "Sun ASC", "distance_km": 42.0},
            {"body": "Jupiter", "angle": "MC", "label": "Jupiter MC", "distance_km": 60.0},
        ],
        natal_crossings=[
            {"planets": ["Venus", "Sun"], "label": "Venus ASC x Sun ASC", "distance_km": 48.0},
        ],
        relocation=relocation,
    )

    assert evaluation["goal"]["id"] == "body_presence"
    assert evaluation["score"] > 60
    assert evaluation["breakdown"]["relocation"] > 0
    assert any(item["kind"] == "modifier" and item.get("metric") == "body_presence" for item in evaluation["contributions"])
