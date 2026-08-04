from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))

from forensic.relationship_status import compute_relationship_status


def _features():
    return {
        "houses": {
            "first_ruler": "Moon",
            "first_ruler_house": 1,
            "seventh_ruler": "Saturn",
            "seventh_ruler_house": 7,
            "first_and_seventh_rulers_aspected": True,
            "first_and_seventh_rulers_same_house": False,
            "seventh_and_eleventh_same_ruler": False,
        },
        "planets": {
            "Moon": {"house": 1, "dignity_score": 0},
            "Saturn": {"house": 7, "dignity_score": 0},
            "Mercury": {"house": 3, "dignity_score": 2},
        },
        "aspects": {
            "Moon_to_Saturn": {"type": "trine", "applying": True, "orb": 1.0},
        },
    }


def _aspect_features(aspect):
    features = _features()
    features["houses"] = {
        **features["houses"],
        "first_ruler_house": 2,
        "seventh_ruler_house": 9,
        "first_and_seventh_rulers_aspected": True,
    }
    features["aspects"] = {"Moon_to_Saturn": aspect}
    return features


def test_soft_applying_direct_aspect_and_reception_boost_known_person_status():
    status = compute_relationship_status(
        _aspect_features({"type": "trine", "applying": True, "orb": 1.0}),
        findings=[
            {
                "id": "friend_or_associate_axis_active",
                "title": "Friend or close associate axis is active",
                "category": "Associates",
            },
        ],
        categories={"Associates": 1},
        receptions={
            "mutual": [{"p1": "Moon", "p2": "Saturn", "strength": 5}],
            "top_unilateral": [],
        },
        light_mediation={},
    )

    assert "friend_acquaintance" in status["labels"]
    assert status["direct_aspect_component"]["aspect"] == "trine"
    assert status["direct_aspect_component"]["applying"] is True
    assert status["direct_aspect_component"]["score_delta"] > 1.0
    assert status["reception_component"]["score_delta"] > 0.0
    assert "mutual reception between victim/perpetrator rulers" in status["evidence"]["reception"]
    assert status["confidence_basis"] == "symbolic_rule_strength_not_empirical_probability"
    assert status["is_statistical_probability"] is False


def _mackenzie_bridge_features():
    features = _features()
    features["houses"] = {
        **features["houses"],
        "first_ruler": "Moon",
        "first_ruler_house": 2,
        "seventh_ruler": "Saturn",
        "seventh_ruler_house": 8,
        "seventh_ruler_in_8_or_12": True,
    }
    features["moon"] = {
        "sign": "Virgo",
        "house": 2,
        "dispositor": "Mercury",
        "dispositor_house": 2,
        "dispositor_to_seventh_ruler_type": "opposition",
        "dispositor_to_seventh_ruler_hard": True,
        "dispositor_to_seventh_ruler_orb": 0.266,
    }
    features["aspects"] = {
        "Mercury_to_Saturn": {
            "type": "opposition",
            "applying": False,
            "orb": 0.266,
        }
    }
    return features


def _mackenzie_bridge_findings(include_transport=True):
    findings = [
        {
            "id": "known_person_route_harm_moon_dispositor_bridge",
            "title": "Moon dispositor links route harm to a known-person or close associate axis",
            "category": "Associates",
            "scoring_eligible": True,
        }
    ]
    if include_transport:
        findings.append(
            {
                "id": "vehicle_crash_or_transport_harm_pattern",
                "title": "Vehicle crash or transport harm pattern is active",
                "category": "Disaster",
                "scoring_eligible": True,
            }
        )
    return findings


def test_complete_moon_dispositor_route_bridge_opens_low_confidence_known_person_label():
    status = compute_relationship_status(
        _mackenzie_bridge_features(),
        findings=_mackenzie_bridge_findings(),
        categories={"Associates": 1, "Disaster": 1},
        receptions={},
        light_mediation={},
    )

    component = status["moon_dispositor_relationship_component"]
    assert status["primary_label"] == "friend_acquaintance"
    assert status["labels"] == ["friend_acquaintance"]
    assert status["scores"]["friend_acquaintance"] == 1.75
    assert status["confidence"] == "Low"
    assert component["eligible"] is True
    assert component["label_gate_met"] is True
    assert component["policy_version"] == "moon_dispositor_route_harm_v1"
    assert component["aspect"] == "opposition"
    assert component["orb"] == 0.266
    assert component["counterfactual"] == {
        "labels_without_component": ["stranger_public"],
        "primary_label_without_component": "stranger_public",
        "friend_score_without_component": 0.0,
        "classification_changed": True,
    }


def test_moon_dispositor_bridge_requires_independent_transport_harm():
    status = compute_relationship_status(
        _mackenzie_bridge_features(),
        findings=_mackenzie_bridge_findings(include_transport=False),
        categories={"Associates": 1},
        receptions={},
        light_mediation={},
    )

    component = status["moon_dispositor_relationship_component"]
    assert status["primary_label"] == "stranger_public"
    assert status["scores"]["friend_acquaintance"] == 0.0
    assert component["eligible"] is False
    assert component["prerequisites"]["independent_transport_harm"] is False


def test_hard_separating_wide_aspect_stays_below_label_without_other_support():
    status = compute_relationship_status(
        _aspect_features({"type": "square", "applying": False, "orb": 7.5}),
        findings=[],
        categories={},
        receptions={},
        light_mediation={},
    )

    assert status["labels"] == ["stranger_public"]
    assert status["direct_aspect_component"]["aspect"] == "square"
    assert status["direct_aspect_component"]["score_delta"] < 0.75
    assert "wide hard separating direct aspect" in status["evidence"]["direct_aspect"]


def test_reception_strength_must_involve_victim_and_perpetrator_rulers():
    status = compute_relationship_status(
        _aspect_features({"type": "sextile", "applying": True, "orb": 1.0}),
        findings=[],
        categories={},
        receptions={
            "mutual": [{"p1": "Venus", "p2": "Jupiter", "strength": 8}],
            "top_unilateral": [{"receiving": "Venus", "received": "Jupiter", "strength": 8}],
        },
        light_mediation={},
    )

    assert status["reception_component"]["score_delta"] == 0.0
    assert status["labels"] == ["stranger_public"]


def test_generic_light_mediation_does_not_create_relationship_status():
    status = compute_relationship_status(
        _aspect_features({}),
        findings=[],
        categories={},
        light_mediation={"translation": True, "translator": "Mercury"},
    )

    assert status["primary_label"] == "stranger_public"
    assert status["labels"] == ["stranger_public"]
    assert status["light_mediation_component"]["score_delta"] == 0.0
    assert status["light_mediation_component"]["role"] == "third_party_only"


def test_victim_perpetrator_translation_supports_known_relationship_bridge():
    status = compute_relationship_status(
        _features(),
        findings=[],
        categories={},
        light_mediation={
            "translation": True,
            "translator": "Mercury",
            "participants": ["Moon", "Mercury", "Saturn"],
            "legs": [
                {"aspect": "trine", "orb": 1.0, "phase": "separating"},
                {"aspect": "sextile", "orb": 0.8, "phase": "applying"},
            ],
            "favorable": True,
        },
    )

    assert "friend_acquaintance" in status["labels"]
    assert status["scores"]["friend_acquaintance"] >= 2.0
    assert status["light_mediation_component"]["role"] == "victim_perpetrator_bridge"
    assert status["light_mediation_component"]["score_delta"] > 0.0


def test_light_prohibition_blocks_closeness_instead_of_inflating_it():
    status = compute_relationship_status(
        _features(),
        findings=[
            {"id": "friend_or_associate_axis_active", "title": "Friend or close associate axis is active", "category": "Associates"},
        ],
        categories={"Associates": 1},
        light_mediation={
            "prohibition": True,
            "denial_type": "frustration",
            "prohibitor": "Mars",
            "participants": ["Moon", "Mars", "Saturn"],
        },
    )

    assert status["scores"]["friend_acquaintance"] < 2.5
    assert status["light_mediation_component"]["score_delta"] < 0.0
    assert "Light prohibition blocks victim/perpetrator perfection" in status["evidence"]["light_mediation"]


def test_single_generic_domestic_finding_does_not_label_intimate_partner():
    status = compute_relationship_status(
        _aspect_features({}),
        findings=[
            {
                "id": "domestic_partner_axis_contact",
                "title": "Partner axis is active in a domestic matter",
                "category": "Domestic",
            },
        ],
        categories={"Domestic": 1},
        receptions={},
        light_mediation={},
    )

    assert status["primary_label"] == "stranger_public"
    assert status["scores"]["intimate_partner"] < 2.0


def test_partner_linked_finding_needs_structural_corrob_to_label_intimate_partner():
    status = compute_relationship_status(
        _aspect_features({"type": "trine", "applying": False, "orb": 2.0}),
        findings=[
            {
                "id": "domestic_partner_known_spouse_homicide",
                "title": "Partner-linked homicide pattern is active",
                "category": "Domestic",
            },
        ],
        categories={"Domestic": 1},
        receptions={},
        light_mediation={},
    )

    assert status["primary_label"] == "stranger_public"
    assert status["scores"]["intimate_partner"] < 2.0


def test_specific_partner_harm_finding_can_label_intimate_partner():
    status = compute_relationship_status(
        _aspect_features({}),
        findings=[
            {
                "id": "domestic_partner_proxy_or_contract_harm",
                "title": "Domestic-by-proxy or partner-linked contract harm pattern is active",
                "category": "Domestic",
            },
        ],
        categories={"Domestic": 1},
        receptions={},
        light_mediation={},
    )

    assert status["primary_label"] == "intimate_partner"
    assert status["scores"]["intimate_partner"] >= 2.0


def test_near_home_partner_finding_needs_custody_family_corrob():
    near_home = {
        "id": "domestic_partner_near_home_axis",
        "title": "Partner involvement tied to the home axis",
        "category": "Domestic",
    }

    uncorroborated = compute_relationship_status(
        _aspect_features({}),
        findings=[near_home],
        categories={"Domestic": 1},
        receptions={},
        light_mediation={},
    )
    corroborated = compute_relationship_status(
        _aspect_features({}),
        findings=[
            near_home,
            {
                "id": "family_custody_child_violence_axis",
                "title": "Family custody and child-present violence pattern is active",
                "category": "Family",
            },
        ],
        categories={"Domestic": 1, "Family": 1},
        receptions={},
        light_mediation={},
    )

    assert uncorroborated["primary_label"] == "stranger_public"
    assert corroborated["primary_label"] == "intimate_partner"


def test_first_seventh_exchange_with_applying_hard_contact_labels_intimate_partner():
    status = compute_relationship_status(
        _features(),
        findings=[],
        categories={},
        receptions={},
        light_mediation={},
    )

    assert "intimate_partner" in status["labels"]
    assert status["scores"]["intimate_partner"] >= 2.0


def test_light_bridge_requires_more_than_weak_friend_contact():
    status = compute_relationship_status(
        _aspect_features({"type": "sextile", "applying": True, "orb": 3.5}),
        findings=[],
        categories={},
        receptions={},
        light_mediation={
            "collection": True,
            "collector": "Sun",
            "participants": ["Moon", "Sun", "Saturn"],
            "legs": [
                {"aspect": "sextile", "orb": 3.5, "phase": "separating"},
                {"aspect": "sextile", "orb": 3.5, "phase": "applying"},
            ],
        },
    )

    assert status["scores"]["friend_acquaintance"] < 3.0
    assert status["labels"] == ["stranger_public"]
