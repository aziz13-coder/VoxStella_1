from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


DEVELOPMENT_ROLES = {
    "development",
    "development_calibration",
}
FORBIDDEN_TUNING_TOKENS = ("holdout", "locked", "external_evaluation", "prospective", "retrospective")


def dataset_evaluation_role(payload: Dict[str, Any]) -> str:
    policy = payload.get("benchmark_policy") if isinstance(payload.get("benchmark_policy"), dict) else {}
    value = payload.get("evaluation_role") or policy.get("evaluation_role") or policy.get("status") or ""
    return str(value).strip().lower()


def assert_tuning_eligible(payload: Dict[str, Any], path: str | Path) -> str:
    """Return the declared role or reject undeclared/evaluation-only data."""
    role = dataset_evaluation_role(payload)
    if not role:
        raise ValueError(f"Dataset {Path(path).name} has no evaluation_role; tuning is denied by default")
    if any(token in role for token in FORBIDDEN_TUNING_TOKENS):
        raise ValueError(f"Dataset {Path(path).name} is evaluation-only ({role}); tuning is prohibited")
    if role not in DEVELOPMENT_ROLES:
        raise ValueError(f"Dataset {Path(path).name} has unsupported tuning role {role!r}")
    return role
