from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixed_stars import FIXED_STAR_CATALOG
from forensic.secondary_factors import compute_secondary_factor_analysis


def test_secondary_factors_require_relevant_special_degree_point():
    features = {
        "planets": {
            "Moon": {"longitude": 75.1, "sign": "Gemini", "degree_in_sign": 15.1, "house": 1},
        },
        "houses": {"first_ruler": "Moon", "seventh_ruler": "Saturn"},
        "angles": {},
        "case_context": {"case_type": "general"},
    }
    degree_special = {
        "special": {
            "Gemini_15": {
                "label": "Assassination degree (trad.)",
                "notes": "High-risk, targeted acts when tied to malefics or Moon.",
            }
        }
    }

    analysis = compute_secondary_factor_analysis(features, degree_special)

    assert analysis["findings"]
    assert analysis["survivability_delta"]["fatal_pressure"] > 0


def test_secondary_factors_use_juno_as_low_weight_partner_modifier_only_on_contact():
    features = {
        "planets": {
            "Venus": {"longitude": 181.0, "sign": "Libra", "degree_in_sign": 1.0, "house": 7},
            "Moon": {"longitude": 10.0, "sign": "Aries", "degree_in_sign": 10.0, "house": 1},
        },
        "asteroids": {
            "Juno": {"longitude": 180.4, "sign": "Libra", "degree_in_sign": 0.4, "house": 7},
        },
        "houses": {"first_ruler": "Moon", "seventh_ruler": "Venus"},
        "angles": {"Descendant": {"longitude": 180.0, "sign": "Libra", "degree_in_sign": 0.0}},
        "case_context": {"case_type": "general"},
    }

    analysis = compute_secondary_factor_analysis(features, {})

    assert analysis["relationship_score_delta"]["intimate_partner"] > 0
    assert analysis["survivability_delta"]["fatal_pressure"] == 0.0


def test_mcintosh_quindecile_adds_role_gated_fatal_pressure():
    features = {
        "planets": {
            "Moon": {"longitude": 10.0, "sign": "Aries", "degree_in_sign": 10.0, "house": 1},
            "Pluto": {"longitude": 175.0, "sign": "Virgo", "degree_in_sign": 25.0, "house": 7},
        },
        "houses": {"first_ruler": "Moon", "seventh_ruler": "Pluto"},
        "angles": {"Descendant": {"longitude": 180.0, "sign": "Libra", "degree_in_sign": 0.0}},
        "aspects": {},
        "case_context": {"case_type": "general"},
    }

    analysis = compute_secondary_factor_analysis(features, {})

    assert any("quindecile" in finding["id"] for finding in analysis["findings"])
    assert analysis["survivability_delta"]["fatal_pressure"] > 0.0
    assert "mcintosh_role_gated_patterns" in analysis["source_basis"]


def test_mcintosh_descendant_stellium_is_structured_secondary_pattern():
    features = {
        "planets": {
            "Moon": {"longitude": 181.0, "sign": "Libra", "degree_in_sign": 1.0, "house": 7},
            "Mars": {"longitude": 184.0, "sign": "Libra", "degree_in_sign": 4.0, "house": 7},
            "Pluto": {"longitude": 187.0, "sign": "Libra", "degree_in_sign": 7.0, "house": 7},
        },
        "houses": {"first_ruler": "Moon", "seventh_ruler": "Mars"},
        "angles": {"Descendant": {"longitude": 180.0, "sign": "Libra", "degree_in_sign": 0.0}},
        "aspects": {},
        "case_context": {"case_type": "general"},
    }

    analysis = compute_secondary_factor_analysis(features, {})

    assert any("descendant_stellium" in finding["id"] for finding in analysis["findings"])
    assert analysis["survivability_delta"]["fatal_pressure"] >= 0.3


def test_exact_dignity_degree_modifies_victim_and_perpetrator_roles():
    features = {
        "planets": {
            "Moon": {"longitude": 33.2, "sign": "Taurus", "degree_in_sign": 3.2, "house": 1},
            "Mars": {"longitude": 118.0, "sign": "Cancer", "degree_in_sign": 28.0, "house": 7},
        },
        "houses": {"first_ruler": "Moon", "seventh_ruler": "Mars"},
        "angles": {},
        "aspects": {},
        "case_context": {"case_type": "general"},
    }

    analysis = compute_secondary_factor_analysis(features, {})

    assert any("exact_dignity_degree" in finding["id"] for finding in analysis["findings"])
    assert analysis["survivability_delta"]["recovery_support"] > 0.0


def test_traditional_direction_payload_is_exposed_without_forcing_score():
    features = {
        "planets": {
            "Moon": {"longitude": 33.2, "sign": "Taurus", "degree_in_sign": 3.2, "house": 1},
        },
        "houses": {"first_ruler": "Moon", "seventh_ruler": "Mars"},
        "angles": {"Ascendant": {"longitude": 30.0, "sign": "Taurus", "degree_in_sign": 0.0}},
        "aspects": {},
        "case_context": {"case_type": "general"},
    }

    analysis = compute_secondary_factor_analysis(features, {})

    directions = analysis["traditional_directional_analysis"]
    assert directions["planet_directions"]["Moon"] == "northwest"
    assert directions["house_directions"]["1"] == "east"


def test_mcintosh_fixed_star_catalog_candidates_are_available():
    star_names = {item["name"] for item in FIXED_STAR_CATALOG}

    assert {"Hyades", "Praesaepe", "South Asellus", "Phecda", "Unukalhai", "Scheat"} <= star_names
