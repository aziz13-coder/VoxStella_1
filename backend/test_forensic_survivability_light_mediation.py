from __future__ import annotations

import copy
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))

from forensic.survivability import compute_survivability


BASE_FEATURES = {
    "houses": {"first_ruler": "Moon", "seventh_ruler": "Mars", "signs": {"1": "Cancer", "7": "Capricorn"}},
    "planets": {
        "Moon": {"house": 1, "dignity_score": 0},
        "Jupiter": {"house": 10, "dignity_score": 2},
        "Mars": {"house": 8, "dignity_score": -1},
    },
    "moon": {"house": 1},
    "aspects": {},
    "solar": {"combustion": [], "under_beams": [], "cazimi": []},
}


def _features_with_light(light_mediation):
    features = copy.deepcopy(BASE_FEATURES)
    features["light_mediation"] = light_mediation
    return features


def test_favorable_light_mediation_adds_capped_recovery_support():
    result = compute_survivability(
        _features_with_light(
            {
                "translation": True,
                "translator": "Jupiter",
                "favorable": True,
                "confidence": 88,
                "participants": ["Jupiter", "Moon", "Sun"],
                "evidence": ["structured translation"],
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == 0.8
    assert result["breakdown"]["recovery_support"] == 0.8
    assert "favorable translation via Jupiter" in " ".join(result["evidence"]["light_mediation"])


def test_tight_soft_translation_by_dignified_benefic_gets_quality_boost():
    result = compute_survivability(
        _features_with_light(
            {
                "translation": True,
                "translator": "Jupiter",
                "favorable": True,
                "participants": ["Jupiter", "Moon", "Sun"],
                "from_leg": {
                    "aspect": "Trine",
                    "orb": 0.4,
                    "phase": "separating",
                    "partile": True,
                },
                "to_leg": {
                    "aspect": "Sextile",
                    "orb": 0.9,
                    "phase": "applying",
                    "complete_platic": True,
                },
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == 1.1
    assert result["breakdown"]["recovery_support"] == 1.1
    evidence = " ".join(result["evidence"]["light_mediation"])
    assert "aspect/orb quality" in evidence
    assert "mediator condition" in evidence


def test_loose_hard_translation_by_debilitated_benefic_loses_recovery_support():
    features = _features_with_light(
        {
            "translation": True,
            "translator": "Jupiter",
            "favorable": True,
            "participants": ["Jupiter", "Moon", "Sun"],
            "from_leg": {
                "aspect": "Square",
                "orb": 6.8,
                "phase": "separating",
            },
            "to_leg": {
                "aspect": "Opposition",
                "orb": 7.2,
                "phase": "applying",
            },
        }
    )
    features["planets"]["Jupiter"]["dignity_score"] = -3
    features["solar"]["under_beams"] = ["Jupiter"]

    result = compute_survivability(features, findings=[], categories={})

    assert result["breakdown"]["light_mediation"] == 0.0
    assert result["breakdown"]["recovery_support"] == 0.0
    evidence = " ".join(result["evidence"]["light_mediation"])
    assert "aspect/orb quality" in evidence
    assert "mediator condition" in evidence


def test_unfavorable_reception_and_hard_legs_increase_fatal_pressure():
    result = compute_survivability(
        _features_with_light(
            {
                "translation": True,
                "translator": "Venus",
                "favorable": False,
                "participants": ["Venus", "Moon", "Sun"],
                "challenge_reasons": ["weak reception"],
                "from_leg": {
                    "aspect": "Square",
                    "orb": 0.8,
                    "phase": "separating",
                },
                "to_leg": {
                    "aspect": "Opposition",
                    "orb": 1.1,
                    "phase": "applying",
                },
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == -1.2
    assert result["breakdown"]["fatal_pressure"] == 1.2
    assert "hostile translation via Venus" in " ".join(result["evidence"]["light_mediation"])


def test_victim_perpetrator_bridge_is_stronger_than_victim_only_mediation():
    result = compute_survivability(
        _features_with_light(
            {
                "translation": True,
                "translator": "Jupiter",
                "favorable": True,
                "participants": ["Moon", "Jupiter", "Mars"],
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == 1.05
    assert "victim-perpetrator bridge" in " ".join(result["evidence"]["light_mediation"])


def test_perpetrator_only_light_mediation_adds_fatal_pressure_not_recovery():
    result = compute_survivability(
        _features_with_light(
            {
                "translation": True,
                "translator": "Jupiter",
                "favorable": True,
                "participants": ["Jupiter", "Mars", "Sun"],
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == -0.35
    assert result["breakdown"]["fatal_pressure"] == 0.35
    assert result["breakdown"]["recovery_support"] == 0.0
    assert "perpetrator-only mediation" in " ".join(result["evidence"]["light_mediation"])


def test_prohibition_touching_victim_scores_as_denial_pressure():
    result = compute_survivability(
        _features_with_light(
            {
                "prohibition": True,
                "denial_type": "frustration",
                "prohibitor": "Saturn",
                "participants": ["Moon", "Mars", "Saturn"],
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == -0.9
    assert result["breakdown"]["fatal_pressure"] == 0.9
    assert "frustration" in " ".join(result["evidence"]["light_mediation"])


def test_malefic_light_mediation_adds_capped_fatal_pressure():
    result = compute_survivability(
        _features_with_light(
            {
                "collection": True,
                "collector": "Mars",
                "favorable": False,
                "confidence": 90,
                "participants": ["Mars", "Moon", "Saturn"],
                "challenge_reasons": ["hard aspect"],
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == -0.9
    assert result["breakdown"]["fatal_pressure"] == 0.9
    assert "hostile collection by Mars" in " ".join(result["evidence"]["light_mediation"])


def test_moon_collection_is_damped_but_still_scores_when_ungated():
    result = compute_survivability(
        _features_with_light(
            {
                "collection": True,
                "collector": "Moon",
                "mode": "BY_APPLICATION",
                "participants": ["Moon", "Mercury", "Jupiter"],
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == 0.25
    assert result["breakdown"]["recovery_support"] == 0.25
    assert "swift collector" in " ".join(result["evidence"]["light_mediation"])


def test_moon_collection_bridge_is_not_upgraded_as_valid_collection():
    result = compute_survivability(
        _features_with_light(
            {
                "collection": True,
                "collector": "Moon",
                "mode": "BY_APPLICATION",
                "participants": ["Moon", "Mars", "Jupiter"],
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == 0.25
    assert "swift collector" in " ".join(result["evidence"]["light_mediation"])
    assert "victim-perpetrator bridge" not in " ".join(result["evidence"]["light_mediation"])


def test_light_mediation_impact_exposes_raw_score_delta_when_outcome_does_not_flip():
    result = compute_survivability(
        _features_with_light(
            {
                "collection": True,
                "collector": "Moon",
                "mode": "BY_APPLICATION",
                "participants": ["Moon", "Mercury", "Jupiter"],
            }
        ),
        findings=[],
        categories={},
    )

    impact = result["light_mediation_impact"]
    assert impact["effect"] == "recovery_support"
    assert impact["score_delta"] == 0.25
    assert impact["score_without_light_mediation"] == round(result["score"] - 0.25, 2)
    assert impact["level_changed"] is False
    assert impact["band_changed"] is False
    assert impact["visibility"] == "raw_only"


def test_separating_collection_is_damped_but_still_scores_when_ungated():
    result = compute_survivability(
        _features_with_light(
            {
                "collection": True,
                "collector": "Jupiter",
                "mode": "BY_SEPARATION",
                "participants": ["Jupiter", "Moon", "Sun"],
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == 0.6
    assert result["breakdown"]["recovery_support"] == 0.6
    assert "separating collection" in " ".join(result["evidence"]["light_mediation"])


def test_light_mediation_without_victim_or_moon_contact_is_damped_but_not_zeroed():
    result = compute_survivability(
        _features_with_light(
            {
                "translation": True,
                "translator": "Jupiter",
                "favorable": True,
                "participants": ["Jupiter", "Venus", "Sun"],
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == 0.55
    assert result["breakdown"]["recovery_support"] == 0.55
    assert "indirect victim/Moon contact" in " ".join(result["evidence"]["light_mediation"])


def test_light_mediation_without_participant_detail_is_damped_but_not_zeroed():
    result = compute_survivability(
        _features_with_light(
            {
                "translation": True,
                "translator": "Jupiter",
                "favorable": True,
            }
        ),
        findings=[],
        categories={},
    )

    assert result["breakdown"]["light_mediation"] == 0.45
    assert result["breakdown"]["recovery_support"] == 0.45
    assert "limited participant detail" in " ".join(result["evidence"]["light_mediation"])


def test_child_case_adds_mercury_but_adult_sex_does_not_force_venus():
    features = copy.deepcopy(BASE_FEATURES)
    features["houses"]["first_ruler"] = "Saturn"
    features["planets"]["Saturn"] = {"house": 1, "dignity_score": 0}
    features["planets"]["Mercury"] = {"house": 3, "dignity_score": 0}
    features["planets"]["Venus"] = {"house": 5, "dignity_score": 0}

    child = compute_survivability(features, case_type="child")
    adult_female = compute_survivability(features, case_type="adult_female")

    assert child["victim_significators"] == ["Saturn", "Moon", "Mercury"]
    assert adult_female["victim_significators"] == ["Saturn", "Moon"]
    assert adult_female["is_statistical_probability"] is False
    assert adult_female["score_basis"] == "symbolic_rule_total_not_probability"
