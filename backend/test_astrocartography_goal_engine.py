from pathlib import Path
import copy
import json
import runpy
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import astrocartography_goal_models as goal_models_module
from astrocartography_goal_engine import (
    _cap_specialist_residual,
    _score_constraint_component,
    _score_relocation_component,
    evaluate_accident_pressure_heuristic,
    evaluate_benefic_minus_malefic_heuristic,
    evaluate_malefic_minus_benefic_heuristic,
    evaluate_goal_model,
    extract_relocation_features,
    list_goal_model_summaries,
)
from astrocartography_goal_models import GoalModelValidationError, get_goal_model, validate_goal_model_payload


def test_goal_model_summaries_include_first_four_profiles():
    ids = {item["id"] for item in list_goal_model_summaries()}
    assert {"education", "love", "work", "money"}.issubset(ids)
    assert {"home", "partners", "beliefs", "friends", "career", "sex"}.issubset(ids)
    assert {"personal_growth", "body_presence", "communication", "conflict", "protective_places"}.issubset(ids)
    assert {"love_commitment", "money_stable_income", "career_public_profile", "home_retreat"}.issubset(ids)
    assert {"gambling_luck", "health_risk", "accident_prone", "travel_fun", "travel_relax", "risk_pressure"}.isdisjoint(ids)


def test_goal_model_schema_covers_runtime_extensions():
    schema_path = goal_models_module.GOAL_MODEL_PATH.with_name("place_goal_model.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    runtime_models = goal_models_module.load_goal_model_payload()["models"]

    assert goal_models_module.load_goal_model_payload()["schema_version"] == 2
    assert "evaluation_strategy" not in schema["properties"]
    assert all(model["scoring_engine"] == "declarative_components_v2" for model in runtime_models)
    assert all("evaluation_strategy" not in model for model in runtime_models)
    assert all(model.get("score_polarity") in {"higher_is_better", "higher_is_worse"} for model in runtime_models)
    assert all(model.get("composition") for model in runtime_models)
    assert all(component.get("component_id") and component.get("source_status") for model in runtime_models for component in model["score_components"])

    schema_top_level = set(schema["properties"])
    assert {"atlas_search_filters", "atlas_shortlist_strategy", "atlas_relocation_prepass_limit"} <= schema_top_level

    runtime_modifier_metrics = {
        str(component.get("metric"))
        for model in runtime_models
        for component in (model.get("score_components") or [])
        if isinstance(component, dict)
        and component.get("kind") == "modifier"
        and component.get("metric")
    }
    schema_modifier_metrics = set(schema["$defs"]["modifierWeight"]["properties"]["metric"]["enum"])
    assert runtime_modifier_metrics <= schema_modifier_metrics


def test_communication_and_education_keep_distinct_doctrinal_anchors():
    communication = get_goal_model("communication")
    education = get_goal_model("education")
    communication_components = communication["score_components"]
    education_components = education["score_components"]

    assert any(
        component.get("kind") == "line"
        and component.get("planet") == "Mercury"
        and component.get("angles") == ["DSC"]
        for component in communication_components
    )
    assert any(
        component.get("kind") == "relocation"
        and set(component.get("houses") or []) == {3, 7, 11}
        for component in communication_components
    )
    assert not any(
        component.get("kind") in {"line", "crossing"}
        and (
            component.get("planet") == "Jupiter"
            or set(component.get("pair") or []) == {"Mercury", "Jupiter"}
        )
        for component in communication_components
    )

    assert {
        component.get("planet")
        for component in education_components
        if component.get("kind") == "line" and component.get("angles") == ["MC"]
    } >= {"Mercury", "Jupiter"}
    assert any(
        component.get("kind") == "crossing"
        and set(component.get("pair") or []) == {"Mercury", "Jupiter"}
        for component in education_components
    )
    assert any(
        component.get("kind") == "relocation"
        and set(component.get("houses") or []) == {9}
        for component in education_components
    )
    assert communication.get("legacy_refs")
    assert education.get("legacy_refs")
    assert all(component.get("evidence_refs") for component in communication_components)
    assert all(component.get("evidence_refs") for component in education_components)
    assert all(
        component.get("source_status") == "experimental"
        for component in communication_components + education_components
        if component.get("kind") in {"crossing", "relocation"}
    )


def test_extract_relocation_features_separates_angular_houses_from_real_angle_proximity():
    chart_data = {
        "ascendant": 0.0,
        "midheaven": 90.0,
        "planets": {
            "Venus": {"house": 7, "longitude": 150.0},
            "Moon": {"house": 4, "longitude": 270.0},
            "Jupiter": {"house": 10, "longitude": 93.0},
            "Mercury": {"house": 3, "longitude": 45.0},
        }
    }

    features = extract_relocation_features(chart_data)

    assert features["planet_houses"]["Venus"] == 7
    assert features["angular_house_occupancy"]["Venus"] == "DSC"
    assert "Venus" not in features["planet_angles"]
    assert features["planet_angles"]["Moon"] == "IC"
    assert features["planet_angles"]["Jupiter"] == "MC"
    assert features["planet_angle_proximity"]["Venus"]["within_orb"] is False
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
    relocation_keys = [
        key
        for item in evaluation["contributions"]
        if item.get("context") == "relocation"
        for key in item.get("evidence_keys") or []
    ]
    assert len(relocation_keys) == len(set(relocation_keys))


def test_goal_model_does_not_score_blended_lines_as_exact_crossings():
    evaluation = evaluate_goal_model(
        "love",
        natal_rows=[],
        natal_crossings=[
            {
                "kind": "blend",
                "planets": ["Venus", "Moon"],
                "label": "Venus DSC x Moon IC",
                "distance_km": 20.0,
            }
        ],
        relocation=extract_relocation_features({"planets": {}}),
    )

    assert not any(item["kind"] == "crossing" for item in evaluation["contributions"])


def test_heuristic_models_do_not_score_blended_lines_as_exact_crossings():
    evaluation = evaluate_goal_model(
        "protective_places",
        natal_rows=[],
        natal_crossings=[
            {
                "kind": "blend",
                "planets": ["Jupiter", "Venus"],
                "label": "Jupiter ASC x Venus MC",
                "distance_km": 20.0,
            }
        ],
        relocation=extract_relocation_features({"planets": {}}),
    )

    assert not any(item["kind"] == "crossing" for item in evaluation["contributions"])


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


def test_specialists_are_declarative_and_unvalidated_models_are_experimental():
    accident_prone = get_goal_model("accident_prone")
    risk_pressure = get_goal_model("risk_pressure")
    protective_places = get_goal_model("protective_places")
    gambling = get_goal_model("gambling_luck")
    health_risk = get_goal_model("health_risk")
    body_presence = get_goal_model("body_presence")
    travel_fun = get_goal_model("travel_fun")
    travel_relax = get_goal_model("travel_relax")

    assert all(model["scoring_engine"] == "declarative_components_v2" for model in (accident_prone, risk_pressure, protective_places, gambling, health_risk, body_presence, travel_fun, travel_relax))
    assert all("evaluation_strategy" not in model for model in (accident_prone, risk_pressure, protective_places, gambling, health_risk, travel_fun, travel_relax))
    assert accident_prone["transit_strategy"] == "ignore"
    assert accident_prone["status"] == "experimental"
    assert gambling["status"] == "experimental"
    assert health_risk["status"] == "experimental"
    assert travel_fun["status"] == "experimental"
    assert travel_relax["status"] == "experimental"
    assert gambling["label"] == "Speculation Themes"
    assert "predict" in gambling["summary"].lower()
    assert any(item["kind"] == "hyp" and "PERSONALITY_THE BODY_APPEARANCE.HYP" in item["source_file"] for item in body_presence["legacy_refs"])
    assert protective_places["transit_strategy"] == "ignore"
    assert protective_places["status"] == "active"
    assert risk_pressure["transit_strategy"] == "ignore"
    assert risk_pressure["status"] == "deprecated"
    assert risk_pressure["score_polarity"] == "higher_is_worse"
    assert health_risk["score_polarity"] == "higher_is_worse"
    assert accident_prone["score_polarity"] == "higher_is_worse"
    assert all(component["source_status"] == "experimental" for component in gambling["score_components"])
    assert travel_fun["goal_family"] == "travel"
    assert travel_relax["goal_family"] == "travel"


def test_goal_model_regeneration_is_strict_v2_and_uses_independent_source():
    generator_path = Path(__file__).resolve().parents[1] / "scripts" / "build_astrocartography_goal_models.py"
    generator = runpy.run_path(str(generator_path))
    regenerated = {
        model["id"]: model
        for model in generator["build_payload"]()["models"]
    }

    payload = generator["build_payload"]()
    assert payload["schema_version"] == 2
    assert generator["SOURCE_PATH"].name == "place_goal_models.source.json"
    assert generator["SOURCE_PATH"] != generator["OUTPUT_PATH"]
    assert regenerated["travel_fun"]["status"] == "experimental"
    assert regenerated["travel_relax"]["status"] == "experimental"


def test_active_goal_summaries_expose_warning_score_polarity():
    summaries = {item["id"]: item for item in list_goal_model_summaries()}

    assert summaries["conflict"]["score_polarity"] == "higher_is_worse"
    assert "health_risk" not in summaries
    assert "accident_prone" not in summaries
    assert "gambling_luck" not in summaries


def test_accident_prone_goal_is_declarative_and_deduplicates_crossings():
    natal_rows = [
        {"body": "Mars", "angle": "ASC", "label": "Mars ASC", "distance_km": 20.0},
        {"body": "Uranus", "angle": "MC", "label": "Uranus MC", "distance_km": 55.0},
        {"body": "Jupiter", "angle": "IC", "label": "Jupiter IC", "distance_km": 70.0},
    ]
    natal_crossings = [
        {"id": "Mars:ASC|Uranus:MC", "lines": ["Mars:ASC", "Uranus:MC"], "planets": ["Mars", "Uranus"], "label": "Mars/Uranus", "distance_km": 60.0},
        {"id": "Uranus:MC|Mars:ASC", "lines": ["Uranus:MC", "Mars:ASC"], "planets": ["Uranus", "Mars"], "label": "duplicate", "distance_km": 65.0},
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
    crossing_rows = [
        item
        for item in product["contributions"]
        if item["kind"] == "crossing"
        and item.get("source_model_id") == "accident_prone"
    ]
    assert product["goal"]["scoring_engine"] == "declarative_components_v2"
    assert product["goal"]["composition"]["parent_id"] == "risk_pressure"
    assert len(crossing_rows) == 1
    assert crossing_rows[0]["interaction_residual"] is True
    assert product["breakdown"]["transit"] == 0.0


def test_goal_model_loader_refreshes_when_runtime_payload_changes(tmp_path, monkeypatch):
    original_payload = copy.deepcopy(goal_models_module.load_goal_model_payload())
    payload_path = tmp_path / "place_goal_models.runtime.json"
    schema_path = tmp_path / "place_goal_model.schema.json"
    payload_path.write_text(json.dumps(original_payload), encoding="utf-8")
    schema_path.write_text(
        goal_models_module.DEFAULT_GOAL_MODEL_SCHEMA_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.setattr(goal_models_module, "GOAL_MODEL_PATH", payload_path)
    goal_models_module._load_goal_model_payload_cached.cache_clear()

    first = goal_models_module.load_goal_model_payload()
    assert first["models"][0]["label"] == original_payload["models"][0]["label"]

    changed = copy.deepcopy(original_payload)
    changed["models"][0]["label"] = "Education Updated"
    payload_path.write_text(json.dumps(changed), encoding="utf-8")

    second = goal_models_module.load_goal_model_payload()
    assert second["models"][0]["label"] == "Education Updated"


def test_support_multiplier_never_makes_a_negative_total_more_negative():
    component = {
        "kind": "constraint",
        "metric": "stability",
        "operator": "gte",
        "threshold": 0.2,
        "multiplier": 1.2,
        "polarity": "support",
        "rationale": "support",
    }
    relocation = {"metrics": {"stability": 0.8}}

    assert _score_constraint_component(component, relocation, current_total=-4.0) is None
    positive = _score_constraint_component(component, relocation, current_total=4.0)
    assert positive is not None
    assert positive["score"] > 0


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


def test_speculation_model_is_parent_plus_local_residual():
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
    assert evaluation["goal"]["label"] == "Speculation Themes"
    assert evaluation["goal"]["composition"]["parent_id"] == "money"
    assert any(item.get("source_model_id") == "money" for item in evaluation["contributions"])
    assert any(item.get("source_model_id") == "gambling_luck" for item in evaluation["contributions"])
    assert not any(item.get("metric") in {"asc_ruler_strength", "gambling_ruler_strength", "moon_gambling_support"} for item in evaluation["contributions"])


def test_speculation_model_exposes_natal_patterns_only_as_non_ranking_priors():
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
    pattern_prior = next(item for item in evaluation["global_priors"] if item.get("metric") == "pattern_support")
    assert pattern_prior["score"] == 0
    assert pattern_prior["evidence_role"] == "global_prior"
    assert pattern_prior["prior_weight"] > 0


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


def test_city_invariant_asc_interception_does_not_change_speculation_ranking_score():
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
    assert clean_eval["raw_score"] == intercepted_eval["raw_score"]
    assert clean_eval["breakdown"]["relocation"] == intercepted_eval["breakdown"]["relocation"]
    assert not any(item.get("metric") == "asc_interception" for item in intercepted_eval["contributions"])


def test_city_invariant_ruler_and_node_metrics_do_not_change_speculation_ranking_score():
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
    assert supportive_eval["raw_score"] == obstructed_eval["raw_score"]
    assert not any(
        item.get("metric") in {
            "asc_ruler_asc_support",
            "gambling_ruler_asc_support",
            "moon_asc_support",
            "south_node_obstruction",
        }
        for item in supportive_eval["contributions"] + obstructed_eval["contributions"]
    )


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


def test_protective_places_is_a_distinct_declarative_livability_model():
    supportive_rows = [
        {"body": "Jupiter", "angle": "ASC", "label": "Jupiter ASC", "distance_km": 40.0},
        {"body": "Venus", "angle": "DSC", "label": "Venus DSC", "distance_km": 44.0},
        {"body": "Moon", "angle": "IC", "label": "Moon IC", "distance_km": 55.0},
    ]
    abrasive_rows = [
        {"body": "Mars", "angle": "IC", "label": "Mars IC", "distance_km": 70.0},
        {"body": "Saturn", "angle": "DSC", "label": "Saturn DSC", "distance_km": 120.0},
    ]
    transit_rows = [
        {"body": "Moon", "angle": "IC", "label": "Moon IC", "distance_km": 30.0},
        {"body": "Pluto", "angle": "ASC", "label": "Pluto ASC", "distance_km": 60.0},
    ]

    supportive = evaluate_goal_model(
        "protective_places",
        natal_rows=supportive_rows,
        natal_crossings=[],
        relocation=extract_relocation_features({"planets": {}}),
        transit_rows=transit_rows,
        transit_crossings=[],
    )
    abrasive = evaluate_goal_model(
        "protective_places",
        natal_rows=abrasive_rows,
        natal_crossings=[],
        relocation=extract_relocation_features({"planets": {}}),
    )

    assert supportive["goal"]["scoring_engine"] == "declarative_components_v2"
    assert supportive["score"] > abrasive["score"]
    assert supportive["breakdown"]["transit"] == 0.0


def test_risk_pressure_uses_higher_is_worse_polarity_and_evidence_floor():
    pressure_rows = [
        {"body": "Mars", "angle": "ASC", "label": "Mars ASC", "distance_km": 22.0},
        {"body": "Saturn", "angle": "DSC", "label": "Saturn DSC", "distance_km": 44.0},
        {"body": "Uranus", "angle": "DSC", "label": "Uranus DSC", "distance_km": 70.0},
    ]

    pressure = evaluate_goal_model(
        "risk_pressure",
        natal_rows=pressure_rows,
        natal_crossings=[],
        relocation=extract_relocation_features({"planets": {}}),
    )
    one_signal = evaluate_goal_model(
        "risk_pressure",
        natal_rows=pressure_rows[:1],
        natal_crossings=[],
        relocation=extract_relocation_features({"planets": {}}),
    )

    assert pressure["goal"]["score_polarity"] == "higher_is_worse"
    assert pressure["score"] is not None
    assert pressure["top_cautions"]
    assert pressure["top_cautions"][0]["score"] > 0
    assert one_signal["score"] is None
    assert one_signal["interpretation_status"] == "below_evidence_floor"


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
    evidence_keys = [
        key
        for item in evaluation["contributions"]
        for key in item.get("evidence_keys") or []
    ]
    assert len(evidence_keys) == len(set(evidence_keys))


def test_empty_evidence_returns_no_activation_instead_of_a_baseline_score():
    evaluation = evaluate_goal_model(
        "education",
        natal_rows=[],
        natal_crossings=[],
        relocation=extract_relocation_features({}),
    )

    assert evaluation["score"] is None
    assert evaluation["score_available"] is False
    assert evaluation["evidence_strength"] == "insufficient"
    assert evaluation["interpretation_status"] == "no_activation"
    assert evaluation["ranking_eligible"] is False
    assert evaluation["evidence"]["independent_signal_count"] == 0


def test_natal_condition_modulates_local_evidence_without_creating_evidence():
    good_relocation = extract_relocation_features(
        {"planets": {"Mercury": {"house": 9, "dignity_score": 6}}}
    )
    poor_relocation = extract_relocation_features(
        {"planets": {"Mercury": {"house": 9, "dignity_score": -6, "retrograde": True}}}
    )
    line = [{"id": "Mercury:MC", "body": "Mercury", "angle": "MC", "distance_km": 30.0}]

    good = evaluate_goal_model(
        "education",
        natal_rows=line,
        natal_crossings=[],
        relocation=good_relocation,
    )
    poor = evaluate_goal_model(
        "education",
        natal_rows=line,
        natal_crossings=[],
        relocation=poor_relocation,
    )

    assert good["raw_score"] > poor["raw_score"]
    assert any(item.get("natal_condition", {}).get("available") for item in good["contributions"])


def test_birth_time_uncertainty_reduces_rank_eligibility_and_widens_interval():
    rows = [
        {"id": "Mercury:ASC", "body": "Mercury", "angle": "ASC", "distance_km": 25.0},
        {"id": "Jupiter:MC", "body": "Jupiter", "angle": "MC", "distance_km": 50.0},
    ]
    exact = evaluate_goal_model(
        "education",
        natal_rows=rows,
        natal_crossings=[],
        relocation=extract_relocation_features({"birth_time_confidence": 1.0}),
    )
    uncertain = evaluate_goal_model(
        "education",
        natal_rows=rows,
        natal_crossings=[],
        relocation=extract_relocation_features({"unknown_time": True}),
    )

    assert exact["ranking_eligible"] is True
    assert uncertain["ranking_eligible"] is False
    assert "birth_time_uncertainty" in uncertain["evidence"]["ranking_ineligible_reasons"]
    exact_width = exact["score_interval"]["high"] - exact["score_interval"]["low"]
    uncertain_width = uncertain["score_interval"]["high"] - uncertain["score_interval"]["low"]
    assert uncertain_width > exact_width
    assert uncertain["rank_stability"]["status"] == "not_evaluated"


def test_negative_relocation_metric_cannot_invert_a_negative_weight_into_support():
    component = {
        "kind": "modifier",
        "metric": "uncertainty",
        "weight": -2.0,
        "rationale": "caution",
    }
    assert _score_relocation_component(component, {"metrics": {"uncertainty": -0.8}}) is None


def test_specialist_parent_is_inherited_once_and_residual_is_capped():
    evaluation = evaluate_goal_model(
        "money_stable_income",
        natal_rows=[
            {"id": "Jupiter:MC", "body": "Jupiter", "angle": "MC", "distance_km": 20.0},
            {"id": "Venus:ASC", "body": "Venus", "angle": "ASC", "distance_km": 30.0},
        ],
        natal_crossings=[],
        relocation=extract_relocation_features(
            {
                "planets": {
                    "Mercury": {"house": 6},
                    "Saturn": {"house": 10},
                    "Jupiter": {"house": 2},
                }
            }
        ),
    )

    assert evaluation["goal"]["composition"]["mode"] == "specialist_residual"
    assert evaluation["goal"]["composition"]["parent_id"] == "money"
    assert evaluation["breakdown"]["parent"] != 0
    assert abs(evaluation["breakdown"]["specialist_residual"]) <= 5.0
    assert {item.get("source_model_id") for item in evaluation["contributions"]} >= {"money", "money_stable_income"}


def test_specialist_residual_cap_includes_constraint_adjustments():
    model = copy.deepcopy(get_goal_model("health_risk"))
    model["composition"]["max_abs_residual"] = 4.0
    contributions = [
        {
            "model_scope": "specialist_residual",
            "evidence_block": "relocation",
            "score": 3.5,
        },
        {
            "model_scope": "specialist_residual",
            "evidence_block": "constraints",
            "score": 1.5,
        },
    ]

    _cap_specialist_residual(contributions, model)

    assert sum(item["score"] for item in contributions) == pytest.approx(4.0)
    assert all(item["residual_cap_factor"] == pytest.approx(0.8) for item in contributions)


def test_strict_v2_validator_rejects_duplicates_and_missing_component_sources():
    payload = copy.deepcopy(goal_models_module.load_goal_model_payload())
    payload["models"][1]["id"] = payload["models"][0]["id"]
    with pytest.raises(GoalModelValidationError, match="duplicate model id"):
        validate_goal_model_payload(payload)

    payload = copy.deepcopy(goal_models_module.load_goal_model_payload())
    payload["models"][0]["score_components"][0].pop("source_status")
    with pytest.raises(GoalModelValidationError, match="source_status"):
        validate_goal_model_payload(payload)


def test_strict_v2_validator_rejects_future_schema_version():
    payload = copy.deepcopy(goal_models_module.load_goal_model_payload())
    payload["schema_version"] = 999
    with pytest.raises(GoalModelValidationError, match="Unsupported"):
        validate_goal_model_payload(payload)


def test_extended_bodies_are_explicit_and_south_node_absence_is_gated():
    model = get_goal_model("personal_growth")
    assert model["body_scope"] == "extended"
    assert "North Node" in model["extended_body_policy"]["supported"]
    assert "South Node" in model["extended_body_policy"]["not_scored"]


def test_backend_and_frontend_runtime_assets_are_identical():
    backend_path = goal_models_module.GOAL_MODEL_PATH
    frontend_path = (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "backend"
        / "knowledge"
        / "astrocartography"
        / "place_goal_models.runtime.json"
    )
    assert backend_path.read_bytes() == frontend_path.read_bytes()
