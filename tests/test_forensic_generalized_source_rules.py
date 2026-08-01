from __future__ import annotations

from pathlib import Path

import pytest

from backend.forensic.axis_assessment import assess_axes
from backend.forensic.engine import evaluate, load_knowledge


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "backend" / "forensic" / "knowledge"


@pytest.fixture(scope="module")
def rules_by_id() -> dict[str, dict]:
    return {rule["id"]: rule for rule in load_knowledge(str(KNOWLEDGE_DIR))}


def _fires(rule: dict, features: dict) -> bool:
    return bool(evaluate(features, [rule]))


def test_generational_neptune_sign_does_not_create_water_label(rules_by_id: dict[str, dict]) -> None:
    rule = rules_by_id["water_disappearance_signatures"]
    features = {
        "houses": {
            "neptune_present": True,
            "neptune_in_4_8_12": False,
            "neptune_water_sign": True,
            "water_cusp_4_8_12": 0,
            "first_ruler_in_4_8_12": False,
        },
        "moon": {
            "water_sign": True,
            "in_4_8_12": False,
            "hard_malefic_contact": False,
        },
    }

    assert _fires(rule, features) is False
    features["houses"]["neptune_in_4_8_12"] = True
    assert _fires(rule, features) is True


@pytest.mark.parametrize(
    "counts,eleventh_ruler_house",
    [
        ({"5": 2, "10": 1}, 5),
        ({"5": 3, "10": 0}, 5),
        ({"5": 3, "10": 1}, 11),
    ],
)
def test_public_crowd_rule_needs_entertainment_group_and_public_channels(
    rules_by_id: dict[str, dict],
    counts: dict[str, int],
    eleventh_ruler_house: int,
) -> None:
    rule = rules_by_id["public_crowd_entertainment_axis"]
    features = {"houses": {"counts": counts, "eleventh_ruler_house": eleventh_ruler_house}}

    assert _fires(rule, features) is False


def test_public_crowd_rule_fires_when_all_three_channels_converge(rules_by_id: dict[str, dict]) -> None:
    rule = rules_by_id["public_crowd_entertainment_axis"]
    features = {"houses": {"counts": {"5": 3, "10": 1}, "eleventh_ruler_house": 5}}

    finding = evaluate(features, [rule])[0]
    axes = assess_axes([finding])["predicted_axes"]

    assert "authority_or_public_case" in axes
    assert "party_entertainment_context" in axes
    assert "friends_social_circle_context" in axes


def test_public_crowd_crisis_requires_concentrated_crowd_and_malefic_pressure(
    rules_by_id: dict[str, dict],
) -> None:
    rule = rules_by_id["public_crowd_crisis_axis"]
    features = {
        "houses": {
            "counts": {"5": 4, "10": 1},
            "eleventh_ruler_house": 5,
            "malefics_angular_count": 1,
        }
    }

    assert _fires(rule, features) is True
    features["houses"]["counts"]["5"] = 3
    assert _fires(rule, features) is False


def test_waterborne_disaster_requires_water_travel_and_crisis_channels(rules_by_id: dict[str, dict]) -> None:
    rule = rules_by_id["waterborne_accident_or_disaster_pattern"]
    features = {
        "houses": {
            "water_cusp_4_8_12": 2,
            "ninth_ruler_hard_afflicted": True,
            "first_ruler_house": 10,
            "counts": {"9": 1},
            "malefics_angular_count": 1,
        },
    }

    assert _fires(rule, features) is True
    features["houses"]["water_cusp_4_8_12"] = 1
    assert _fires(rule, features) is False


def test_transport_accident_requires_route_victim_moon_and_angular_pressure(
    rules_by_id: dict[str, dict],
) -> None:
    rule = rules_by_id["vehicle_crash_or_transport_harm_pattern"]
    features = {
        "houses": {
            "ninth_ruler_house": 6,
            "first_ruler_hard_afflicted": True,
            "malefics_angular_count": 1,
        },
        "moon": {"hard_malefic_contact": True},
    }

    assert _fires(rule, features) is True
    features["moon"]["hard_malefic_contact"] = False
    assert _fires(rule, features) is False

    features["moon"]["hard_malefic_contact"] = True
    features["houses"]["ninth_ruler_house"] = 5
    features["houses"]["third_ruler_house"] = 6
    assert _fires(rule, features) is False


def test_travel_disaster_uses_positive_corroboration_without_case_exclusions(
    rules_by_id: dict[str, dict],
) -> None:
    rule = rules_by_id["travel_accident_or_disaster_pattern"]
    features = {
        "houses": {
            "first_ruler_house": 9,
            "first_ruler_hard_afflicted": False,
            "third_ruler_hard_afflicted": False,
            "ninth_ruler_hard_afflicted": False,
            "malefics_angular_count": 1,
        },
        "moon": {"hard_malefic_contact": True},
    }

    assert _fires(rule, features) is True
    features["houses"]["malefics_angular_count"] = 0
    assert _fires(rule, features) is False


@pytest.mark.parametrize(
    "rule_id",
    [
        "family_domestic_moon_signature",
        "family_home_axis_under_pressure",
        "family_child_homicide_axis_cluster",
        "abduction_social_or_group_gathering_seizure_signature",
    ],
)
def test_contextual_patterns_cannot_activate_outcome_axes(
    rules_by_id: dict[str, dict],
    rule_id: str,
) -> None:
    rule = rules_by_id[rule_id]
    finding = {
        "id": rule_id,
        "category": rule["category"],
        "scoring_eligible": rule.get("scoring", True) is not False,
    }

    result = assess_axes([finding])

    assert rule["validation_status"] == "contextual_indicator_unvalidated"
    assert result["predicted_axes"] == []
    assert result["excluded_non_scoring_rule_ids"] == [rule_id]


@pytest.mark.parametrize(
    "rule_id",
    [
        "water_disappearance_signatures",
        "public_crowd_entertainment_axis",
        "public_crowd_crisis_axis",
        "vehicle_crash_or_transport_harm_pattern",
        "travel_accident_or_disaster_pattern",
        "waterborne_accident_or_disaster_pattern",
    ],
)
def test_new_or_revised_scoring_rules_expose_source_provenance(
    rules_by_id: dict[str, dict],
    rule_id: str,
) -> None:
    assert rules_by_id[rule_id]["source_refs"]
