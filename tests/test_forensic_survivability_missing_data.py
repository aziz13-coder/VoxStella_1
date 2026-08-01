from backend.forensic.survivability import (
    _fatal_pressure_component,
    _house_group,
    _mechanism_flags,
    compute_survivability,
)


def test_missing_or_invalid_house_is_unknown_not_cadent() -> None:
    assert _house_group(None) == "unknown"
    assert _house_group(0) == "unknown"
    assert _house_group(13) == "unknown"


def test_missing_house_does_not_create_a_cadent_vitality_penalty() -> None:
    result = compute_survivability(
        {
            "houses": {"first_ruler": "Moon"},
            "planets": {"Moon": {"dignity_score": 0}},
        }
    )

    assert result["breakdown"]["vitality"] == 0
    assert all("cadent" not in item for item in result["evidence"]["vitality"])


def test_fatal_pressure_does_not_infer_mechanisms_from_titles() -> None:
    findings = [
        {
            "id": "unrelated_rule",
            "title": "Known-person homicide and catastrophic hidden transport harm",
            "category": "Violence",
        }
    ]

    score, evidence = _fatal_pressure_component({}, findings, {"Violence": 9, "Disaster": 4})
    flags = _mechanism_flags(findings, {"Violence": 9, "Disaster": 4})

    assert score == 0
    assert evidence == []
    assert not any(flags.values())


def test_correlated_fatal_rules_contribute_once_per_evidence_family() -> None:
    findings = [
        {"id": "violence_life_death_overlap", "category": "Violence"},
        {"id": "family_child_homicide_axis_cluster", "category": "Family"},
        {
            "id": "family_parricide_homicide_cluster",
            "category": "Family",
            "scoring_eligible": False,
        },
    ]

    score, evidence = _fatal_pressure_component({}, findings, {"Violence": 1, "Family": 2})

    assert score == 2.4
    assert len(evidence) == 1
    assert "family_child_homicide_axis_cluster" in evidence[0]


def test_transport_mechanism_does_not_imply_fatal_outcome() -> None:
    findings = [
        {
            "id": "vehicle_crash_or_transport_harm_pattern",
            "category": "Disaster",
            "scoring_eligible": True,
        }
    ]

    score, evidence = _fatal_pressure_component({}, findings, {"Disaster": 1})
    result = compute_survivability({}, findings, {"Disaster": 1})

    assert score == 0
    assert evidence == []
    assert result["classification_context"]["mechanism_flags"]["transport_harm"] is True
    assert result["classification_context"]["fatal_mechanism_context"] is False
