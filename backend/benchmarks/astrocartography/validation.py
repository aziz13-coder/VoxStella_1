from __future__ import annotations

import hashlib
import math
import random
from typing import Any, Dict, Iterable, List, Sequence, Tuple


SUPPORTED_OUTCOME_POLARITIES = {"positive", "negative"}
SUPPORTED_SCORE_POLARITIES = {"higher_is_better", "higher_is_worse"}
HAZARD_GOAL_IDS = {"accident_prone", "health_risk", "risk_pressure"}
DEFAULT_SPLIT_SEED = "vox-stella-astrocartography-v1"
DEFAULT_HOLDOUT_FRACTION = 0.25
MIN_BOOTSTRAP_GROUPS = 5


def normalize_outcome_polarity(value: Any) -> str:
    polarity = str(value or "").strip().lower()
    if polarity not in SUPPORTED_OUTCOME_POLARITIES:
        raise ValueError(
            f"outcome_polarity must be one of {sorted(SUPPORTED_OUTCOME_POLARITIES)}"
        )
    return polarity


def normalize_score_polarity(value: Any, *, goal_id: str = "") -> str:
    polarity = str(value or "").strip().lower()
    normalized_goal = str(goal_id or "").strip().lower()
    if normalized_goal in HAZARD_GOAL_IDS and polarity != "higher_is_worse":
        return "higher_is_worse"
    if polarity in SUPPORTED_SCORE_POLARITIES:
        return polarity
    return "higher_is_better"


def event_score_orientation(
    outcome_polarity: Any,
    score_polarity: Any,
    *,
    goal_id: str = "",
) -> int:
    """Return +1 when a higher score supports the observed event, otherwise -1."""

    outcome = normalize_outcome_polarity(outcome_polarity)
    score = normalize_score_polarity(score_polarity, goal_id=goal_id)
    if (outcome == "positive") == (score == "higher_is_better"):
        return 1
    return -1


def comparison_credit(
    event_score: float,
    control_score: float,
    *,
    orientation: int,
    tolerance: float = 1e-9,
) -> float:
    event_oriented = float(event_score) * float(orientation)
    control_oriented = float(control_score) * float(orientation)
    if math.isclose(event_oriented, control_oriented, rel_tol=tolerance, abs_tol=tolerance):
        return 0.5
    return 1.0 if event_oriented > control_oriented else 0.0


def positive_weight(value: Any, *, field: str, default: float = 1.0) -> float:
    if value is None or value == "":
        return float(default)
    try:
        weight = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a positive finite number") from exc
    if not math.isfinite(weight) or weight <= 0.0:
        raise ValueError(f"{field} must be a positive finite number")
    return weight


def case_weight(case: Dict[str, Any]) -> float:
    return positive_weight(case.get("case_weight"), field="case_weight")


def control_weight(control: Any) -> float:
    if not isinstance(control, dict):
        return 1.0
    for key in ("comparison_weight", "exposure_weight", "weight"):
        if control.get(key) is not None:
            return positive_weight(control.get(key), field=f"control.{key}")
    return 1.0


def person_group_id(case: Dict[str, Any]) -> str:
    for key in ("person_id", "person_name"):
        value = " ".join(str(case.get(key) or "").strip().lower().split())
        if value:
            return value
    birth = case.get("birth") if isinstance(case.get("birth"), dict) else {}
    birth_key = "|".join(
        str(birth.get(key) or "").strip().lower()
        for key in ("date", "time", "place")
    )
    if birth_key.strip("|"):
        return f"birth:{birth_key}"
    case_id = str(case.get("case_id") or "").strip().lower()
    if case_id:
        return f"case:{case_id}"
    raise ValueError("A person_id, person_name, birth identity, or case_id is required")


def assign_person_splits(
    cases: Sequence[Dict[str, Any]],
    *,
    holdout_fraction: float = DEFAULT_HOLDOUT_FRACTION,
    seed: str = DEFAULT_SPLIT_SEED,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    try:
        fraction = float(holdout_fraction)
    except (TypeError, ValueError) as exc:
        raise ValueError("holdout_fraction must be between 0 and 1") from exc
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("holdout_fraction must be between 0 and 1")

    groups = sorted({person_group_id(case) for case in cases})
    holdout_groups = set()
    for group in groups:
        digest = hashlib.sha256(f"{seed}\0{group}".encode("utf-8")).digest()
        uniform_value = int.from_bytes(digest[:8], "big") / float(2**64)
        if uniform_value < fraction:
            holdout_groups.add(group)

    assigned: List[Dict[str, Any]] = []
    for raw_case in cases:
        case = dict(raw_case)
        group_id = person_group_id(case)
        case["_person_group_id"] = group_id
        case["_validation_split"] = "holdout" if group_id in holdout_groups else "train"
        assigned.append(case)

    manifest = {
        "seed": str(seed),
        "holdout_fraction": fraction,
        "person_group_count": len(groups),
        "train_person_count": len(groups) - len(holdout_groups),
        "holdout_person_count": len(holdout_groups),
        "train_case_count": sum(1 for case in assigned if case["_validation_split"] == "train"),
        "holdout_case_count": sum(1 for case in assigned if case["_validation_split"] == "holdout"),
        "holdout_person_hashes": sorted(
            hashlib.sha256(group.encode("utf-8")).hexdigest()[:12]
            for group in holdout_groups
        ),
    }
    return assigned, manifest


def select_validation_split(
    cases: Sequence[Dict[str, Any]],
    *,
    split: str = "all",
    holdout_fraction: float = DEFAULT_HOLDOUT_FRACTION,
    seed: str = DEFAULT_SPLIT_SEED,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    requested = str(split or "all").strip().lower()
    if requested not in {"all", "train", "holdout"}:
        raise ValueError("split must be one of: all, train, holdout")
    assigned, manifest = assign_person_splits(
        cases,
        holdout_fraction=holdout_fraction,
        seed=seed,
    )
    selected: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for case in assigned:
        if requested == "all" or case["_validation_split"] == requested:
            selected.append(case)
        else:
            skipped.append(
                {
                    "dataset": str(case.get("_dataset_path") or ""),
                    "line_number": int(case.get("_line_number") or 0),
                    "case_id": str(case.get("case_id") or ""),
                    "reason": "validation_split",
                    "assigned_split": case["_validation_split"],
                    "requested_split": requested,
                }
            )
    manifest = {**manifest, "requested_split": requested, "selected_case_count": len(selected)}
    return selected, skipped, manifest


def weighted_mean(values: Iterable[Tuple[float, float]]) -> float | None:
    numerator = 0.0
    denominator = 0.0
    for value, weight in values:
        numeric_weight = positive_weight(weight, field="summary weight")
        numerator += float(value) * numeric_weight
        denominator += numeric_weight
    if denominator <= 0.0:
        return None
    return numerator / denominator


def clustered_bootstrap_ci(
    observations: Sequence[Dict[str, Any]],
    *,
    value_key: str,
    weight_key: str = "weight",
    group_key: str = "person_group_id",
    iterations: int = 2000,
    confidence: float = 0.95,
    seed: str = DEFAULT_SPLIT_SEED,
) -> Dict[str, Any] | None:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for observation in observations:
        if observation.get(value_key) is None:
            continue
        group = str(observation.get(group_key) or "").strip()
        if not group:
            continue
        grouped.setdefault(group, []).append(observation)
    group_ids = sorted(grouped)
    if len(group_ids) < MIN_BOOTSTRAP_GROUPS:
        return None

    iteration_count = max(200, int(iterations))
    confidence_value = float(confidence)
    if not 0.0 < confidence_value < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    rng_seed = int.from_bytes(
        hashlib.sha256(
            f"{seed}\0{value_key}\0{'|'.join(group_ids)}".encode("utf-8")
        ).digest()[:8],
        "big",
    )
    rng = random.Random(rng_seed)
    samples: List[float] = []
    for _ in range(iteration_count):
        selected_groups = [rng.choice(group_ids) for _ in group_ids]
        sampled_rows = [
            row
            for group in selected_groups
            for row in grouped[group]
        ]
        estimate = weighted_mean(
            (
                float(row[value_key]),
                float(row.get(weight_key) or 1.0),
            )
            for row in sampled_rows
        )
        if estimate is not None:
            samples.append(float(estimate))
    if not samples:
        return None
    samples.sort()
    alpha = 1.0 - confidence_value
    lower_index = max(0, min(len(samples) - 1, int((alpha / 2.0) * len(samples))))
    upper_index = max(
        0,
        min(len(samples) - 1, int(math.ceil((1.0 - (alpha / 2.0)) * len(samples))) - 1),
    )
    return {
        "lower": round(samples[lower_index], 4),
        "upper": round(samples[upper_index], 4),
        "confidence": confidence_value,
        "iterations": len(samples),
        "cluster_count": len(group_ids),
        "method": "person_cluster_bootstrap",
    }
