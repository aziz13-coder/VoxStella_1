from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.forensic.survivability import DEFAULT_SURVIVABILITY_POLICY, SurvivabilityPolicy
from backend.forensic.tuning import assert_tuning_eligible, dataset_evaluation_role
from backend.forensic_survivability_tuning_runner import candidate_policies


REPO_ROOT = Path(__file__).resolve().parents[1]


def _payload(name: str):
    return json.loads((REPO_ROOT / "tests" / "fixtures" / name).read_text(encoding="utf-8"))


def test_tuning_guard_accepts_declared_development_fixture() -> None:
    payload = _payload("forensic_survivability_stratified_cases.json")
    assert dataset_evaluation_role(payload) == "development_calibration"
    assert assert_tuning_eligible(payload, "development.json") == "development_calibration"


@pytest.mark.parametrize(
    "fixture",
    [
        "forensic_known_outcome_aviation_holdout_v1.json",
        "forensic_holdout_30_cases_2026_05_20.json",
    ],
)
def test_tuning_guard_rejects_locked_or_retrospective_evaluation_data(fixture: str) -> None:
    payload = _payload(fixture)
    with pytest.raises(ValueError):
        assert_tuning_eligible(payload, fixture)


def test_candidate_grid_is_deterministic_and_contains_current_policy() -> None:
    policies = candidate_policies()
    assert policies[0] == DEFAULT_SURVIVABILITY_POLICY
    assert len(policies) == len(set(policies)) == 27
    assert all(isinstance(policy, SurvivabilityPolicy) for policy in policies)
