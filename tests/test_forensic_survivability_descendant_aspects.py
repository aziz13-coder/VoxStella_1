from __future__ import annotations

from dataclasses import replace

from backend.forensic.survivability import (
    DEFAULT_SURVIVABILITY_POLICY,
    _descendant_aspect_pressure_component,
    compute_survivability,
)


EXPERIMENT_POLICY = replace(
    DEFAULT_SURVIVABILITY_POLICY,
    version="descendant_aspect_experiment_v1",
    descendant_aspects_enabled=True,
)
LEGACY_POLICY = replace(
    DEFAULT_SURVIVABILITY_POLICY,
    version="deduplicated_v2",
    descendant_aspects_enabled=False,
)


def _features(*, descendant: float = 180.0, planets=None):
    return {
        "angles": {
            "Ascendant": {"longitude": (descendant + 180.0) % 360.0},
            "Descendant": {"longitude": descendant},
            "IC": {"longitude": 70.0},
            "Midheaven": {"longitude": 250.0},
        },
        "planets": planets or {},
        "houses": {},
        "house_rulers": {},
        "aspects": {},
        "moon": {},
        "solar": {},
    }


def _transport_finding():
    return {
        "id": "vehicle_crash_or_transport_harm_pattern",
        "category": "Disaster",
        "scoring_eligible": True,
    }


def test_default_policy_scores_descendant_contacts_after_promotion() -> None:
    features = _features(planets={"Pluto": {"longitude": 180.0}})

    result = compute_survivability(
        features,
        findings=[_transport_finding()],
        categories={"Disaster": 1},
    )

    assert result["classification_policy"]["version"] == "deduplicated_v3_descendant_aspects"
    assert result["breakdown"]["descendant_aspect_fatal_pressure"] == 2.43
    assert result["descendant_aspect_impact"]["enabled"] is True
    assert result["classification_context"]["descendant_aspect_transport_context"] is True
    assert result["level"] == "Lower"


def test_legacy_policy_can_reproduce_the_pre_promotion_result() -> None:
    features = _features(planets={"Pluto": {"longitude": 180.0}})

    result = compute_survivability(
        features,
        findings=[_transport_finding()],
        categories={"Disaster": 1},
        policy=LEGACY_POLICY,
    )

    assert result["breakdown"]["descendant_aspect_fatal_pressure"] == 0.0
    assert result["descendant_aspect_impact"]["enabled"] is False
    assert result["classification_context"]["descendant_aspect_transport_context"] is False
    assert result["level"] == "Moderate"


def test_descendant_pressure_is_not_applied_without_independent_harm_context() -> None:
    features = _features(planets={"Mars": {"longitude": 90.0}})

    result = compute_survivability(features, findings=[], categories={})

    impact = result["descendant_aspect_impact"]
    assert impact["contacts"][0]["aspect_to_descendant"] == "square"
    assert impact["candidate_raw_fatal_pressure"] == 2.43
    assert impact["harm_context_eligible"] is False
    assert impact["eligibility_reason"] == "no_independent_harm_context"
    assert impact["raw_fatal_pressure_delta"] == 0.0
    assert result["breakdown"]["descendant_aspect_fatal_pressure"] == 0.0


def test_descendant_conjunction_is_scored_once() -> None:
    features = _features(planets={"Pluto": {"longitude": 180.027}})

    danger, fatal, evidence, contacts = _descendant_aspect_pressure_component(
        features,
        EXPERIMENT_POLICY,
    )

    assert danger == 0.0
    assert fatal == 2.43
    assert len(contacts) == 1
    assert contacts[0]["aspect_to_descendant"] == "conjunction"
    assert contacts[0]["orb"] == 0.027
    assert "conjunction Descendant" in evidence[0]


def test_opt_in_descendant_pressure_can_activate_compound_transport_gate() -> None:
    features = _features(planets={"Pluto": {"longitude": 180.027}})

    result = compute_survivability(
        features,
        findings=[_transport_finding()],
        categories={"Disaster": 1},
        policy=EXPERIMENT_POLICY,
    )

    assert result["level"] == "Lower"
    assert result["outcome_band"] == "fatal_pressure_dominant"
    assert result["breakdown"]["descendant_aspect_fatal_pressure"] == 2.43
    assert result["descendant_aspect_impact"]["transport_fatal_gate_activated"] is True
    assert result["descendant_aspect_impact"]["level_without_descendant_aspects"] == "Moderate"


def test_traditional_and_outer_families_each_contribute_only_their_strongest_contact() -> None:
    features = _features(
        planets={
            "Mars": {"longitude": 1.0},
            "Saturn": {"longitude": 0.2},
            "Pluto": {"longitude": 179.9},
            "Uranus": {"longitude": 91.0},
        }
    )

    _, fatal, _, contacts = _descendant_aspect_pressure_component(features, EXPERIMENT_POLICY)

    assert [row["planet"] for row in contacts] == ["Saturn", "Pluto"]
    assert fatal == 4.5  # capped after one traditional and one outer contact


def test_mc_ic_contact_is_not_mistaken_for_victim_axis_pressure() -> None:
    features = _features(planets={"Pluto": {"longitude": 70.0}})

    danger, fatal, evidence, contacts = _descendant_aspect_pressure_component(
        features,
        EXPERIMENT_POLICY,
    )

    assert danger == 0.0
    assert fatal == 0.0
    assert evidence == []
    assert contacts == []


def test_benefic_descendant_contact_is_not_promoted_by_pressure_component() -> None:
    features = _features(planets={"Jupiter": {"longitude": 0.1}})

    danger, fatal, evidence, contacts = _descendant_aspect_pressure_component(
        features,
        EXPERIMENT_POLICY,
    )

    assert danger == 0.0
    assert fatal == 0.0
    assert evidence == []
    assert contacts == []


def test_missing_descendant_data_remains_neutral_and_explainable() -> None:
    features = {"planets": {"Saturn": {"longitude": 0.0}}}

    danger, fatal, evidence, contacts = _descendant_aspect_pressure_component(
        features,
        EXPERIMENT_POLICY,
    )

    assert danger == 0.0
    assert fatal == 0.0
    assert "Descendant longitude missing" in evidence[0]
    assert contacts == []
