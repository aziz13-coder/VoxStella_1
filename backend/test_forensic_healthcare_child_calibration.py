from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))

from forensic.survivability import compute_survivability


def _institutional_child_harm_features() -> dict:
    return {
        "case_context": {
            "case_type": "child",
            "child_case": True,
            "healthcare_context": True,
            "healthcare_child_context": True,
        },
        "houses": {
            "first_ruler": "Moon",
            "seventh_ruler": "Saturn",
            "first_ruler_in_8_or_12": True,
            "signs": {"1": "Cancer", "7": "Capricorn"},
        },
        "planets": {
            "Moon": {"house": 12, "dignity_score": 0},
            "Saturn": {"house": 6, "dignity_score": 0},
        },
        "moon": {"house": 12, "in_4_8_12": True, "hard_malefic_contact": True},
        "aspects": {},
        "solar": {"combustion": [], "under_beams": [], "cazimi": []},
    }


def _institutional_child_harm_findings() -> list[dict]:
    return [
        {
            "id": "violence_life_death_overlap",
            "title": "Life/death overlap points to violence or homicide",
            "category": "Violence",
            "weight": 4,
        },
        {
            "id": "violence_hidden_victim_with_angular_malefic",
            "title": "Hidden victim with angular violence markers",
            "category": "Violence",
            "weight": 3,
        },
        {
            "id": "abduction_worksite_or_assignment_seizure_signature",
            "title": "Abduction or worksite-seizure pattern is active",
            "category": "Abduction",
            "weight": 4,
        },
        {
            "id": "context_child_case_axis",
            "title": "Child victim or child-case context is active",
            "category": "Children",
            "weight": 3,
        },
        {
            "id": "sect_malefic_out_of_sect",
            "title": "Malefic contrary to sect (angular)",
            "category": "Stressors",
            "weight": 3,
        },
    ]


def test_healthcare_child_context_does_not_treat_worksite_abduction_as_release_favored():
    result = compute_survivability(
        _institutional_child_harm_features(),
        findings=_institutional_child_harm_findings(),
        categories={"Violence": 2, "Abduction": 1, "Children": 1, "Stressors": 1},
        case_type="child",
    )

    assert result["level"] == "Lower"
    assert result["outcome_band"] == "fatal_pressure_dominant"
    assert 5.0 <= result["breakdown"]["fatal_pressure"] < 8.0
    assert result["breakdown"]["danger"] == 0.0
    assert "healthcare/caregiver child context keeps abduction weighting" in " ".join(
        result["evidence"]["fatal_pressure"]
    )


def test_ordinary_abduction_context_keeps_release_recovery_branch():
    features = _institutional_child_harm_features()
    features["case_context"] = {
        "case_type": "child",
        "child_case": True,
        "healthcare_context": False,
        "caregiver_context": False,
        "institutional_care_context": False,
        "healthcare_child_context": False,
    }

    result = compute_survivability(
        features,
        findings=_institutional_child_harm_findings(),
        categories={"Violence": 2, "Abduction": 1, "Children": 1, "Stressors": 1},
        case_type="child",
    )

    assert result["level"] == "Moderate"
    assert result["outcome_band"] == "risk_loaded_survival"
    assert result["breakdown"]["fatal_pressure"] < 5.0
    assert "abduction context scales fatal pressure" in " ".join(result["evidence"]["fatal_pressure"])
