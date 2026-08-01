from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


SUPPORTED_FORENSIC_HOUSE_SYSTEM_CODES = ("R", "P", "E", "W", "O", "C", "K", "T")
FORENSIC_HOUSE_SYSTEM_LABELS = {
    "R": "Regiomontanus",
    "P": "Placidus",
    "E": "Equal",
    "W": "Whole Sign",
    "O": "Porphyry",
    "C": "Campanus",
    "K": "Koch",
    "T": "Topocentric",
}

# Selected on the declared development corpus by
# backend/forensic_house_system_selection_runner.py. Locked holdouts and
# retrospective-evaluation fixtures are rejected by that runner.
DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE = "R"
FORENSIC_HOUSE_SYSTEM_SELECTION_VERSION = "development_composite_v1_2026_08_01"
FORENSIC_HOUSE_SYSTEM_SELECTION_WEIGHTS = {
    "axis_labeled_balanced_accuracy": 0.60,
    "survivability_partial_credit_accuracy": 0.30,
    "relationship_macro_f1": 0.10,
}
FORENSIC_HOUSE_SYSTEM_SELECTION_BASIS = {
    "selected_code": DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE,
    "selected_label": FORENSIC_HOUSE_SYSTEM_LABELS[DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE],
    "selection_version": FORENSIC_HOUSE_SYSTEM_SELECTION_VERSION,
    "development_case_count": 33,
    "selected_score": 0.72224,
    "runner": "backend/forensic_house_system_selection_runner.py",
    "evaluation_scope": "development_only_not_holdout_validation",
}


def normalize_forensic_house_system_code(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    code = str(value).strip().upper()
    if code not in SUPPORTED_FORENSIC_HOUSE_SYSTEM_CODES:
        supported = ", ".join(SUPPORTED_FORENSIC_HOUSE_SYSTEM_CODES)
        raise ValueError(f"Unsupported forensic house system {code!r}; supported codes are {supported}")
    return code


def forensic_house_system_selection_score(metrics: Mapping[str, Any]) -> float:
    values: Dict[str, float] = {}
    for key in FORENSIC_HOUSE_SYSTEM_SELECTION_WEIGHTS:
        raw = metrics.get(key)
        values[key] = float(raw) if raw is not None else 0.0
    return sum(
        FORENSIC_HOUSE_SYSTEM_SELECTION_WEIGHTS[key] * values[key]
        for key in FORENSIC_HOUSE_SYSTEM_SELECTION_WEIGHTS
    )
