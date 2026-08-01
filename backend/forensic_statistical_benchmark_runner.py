from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


def _resolve_reference_root() -> Path:
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "AGENTS.md").exists() and (parent / "backend").is_dir():
            return parent
    return current_path.parents[1]


REPO_ROOT = _resolve_reference_root()
BACKEND_ROOT = REPO_ROOT / "backend"
CURRENT_ROOT = Path(__file__).resolve().parent

for import_path in (CURRENT_ROOT, BACKEND_ROOT, REPO_ROOT):
    import_value = str(import_path)
    if import_value not in sys.path:
        sys.path.insert(0, import_value)


from forensic_roommate_benchmark_runner import _call_forensic_route as _roommate_call_forensic_route  # noqa: E402
from forensic.axis_assessment import AXIS_ORDER, assess_axes  # noqa: E402
from forensic.benchmark_policy import benchmark_exclusion_reason  # noqa: E402


DEFAULT_DATASET_PATHS = [
    REPO_ROOT / "tests" / "fixtures" / "forensic_worst_ex_ever_cases.json",
    REPO_ROOT / "tests" / "fixtures" / "forensic_netflix_true_crime_2025_2026_cases.json",
    REPO_ROOT / "tests" / "fixtures" / "forensic_recent_documentaries_2025_2026_cases.json",
    BACKEND_ROOT / "benchmarks" / "forensic" / "worst_roommate_ever_cases.json",
    REPO_ROOT / "tests" / "fixtures" / "forensic_fbi_active_shooter_extension_cases.json",
]

RELATIONSHIP_LABELS = [
    "intimate_partner",
    "family",
    "friend_acquaintance",
    "stranger_public",
]

RELATIONSHIP_AXIS_LABELS = {
    "domestic_partner_involvement": "intimate_partner",
    "family_involvement": "family",
    "friend_or_close_associate": "friend_acquaintance",
}


def _call_forensic_route(query: Dict[str, str]) -> Dict[str, Any]:
    return _roommate_call_forensic_route(query)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _round4(value: Any) -> Optional[float]:
    try:
        return round(float(value), 4)
    except Exception:
        return None


def _case_benchmark(case: Dict[str, Any]) -> Dict[str, Any]:
    benchmark = case.get("benchmark")
    return benchmark if isinstance(benchmark, dict) else case


def _case_id(case: Dict[str, Any], dataset_path: Path, index: int) -> str:
    return _normalize_text(case.get("id") or case.get("case_id")) or f"{dataset_path.stem}_{index}"


def _expected_axes(case: Dict[str, Any]) -> List[str]:
    benchmark = _case_benchmark(case)
    axes = benchmark.get("expected_primary_axes") or []
    return [str(axis) for axis in axes if str(axis).strip()]


def _contradictory_axes(case: Dict[str, Any]) -> List[str]:
    benchmark = _case_benchmark(case)
    axes = benchmark.get("contradictory_axes") or []
    return [str(axis) for axis in axes if str(axis).strip()]


def _expected_survivability(case: Dict[str, Any]) -> Dict[str, List[str]]:
    benchmark = _case_benchmark(case)
    expected = benchmark.get("expected_survivability")
    if isinstance(expected, dict):
        return {
            "levels": [str(item) for item in expected.get("levels") or [] if str(item).strip()],
            "bands": [str(item) for item in expected.get("bands") or [] if str(item).strip()],
        }
    return {
        "levels": [str(item) for item in case.get("expected_levels") or [] if str(item).strip()],
        "bands": [str(item) for item in case.get("expected_bands") or [] if str(item).strip()],
    }


def _normalize_relationship_label(value: Any) -> str:
    text = _normalize_text(value).lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "domestic_partner": "intimate_partner",
        "partner": "intimate_partner",
        "spouse": "intimate_partner",
        "intimate": "intimate_partner",
        "intimate_partner_involvement": "intimate_partner",
        "family_involvement": "family",
        "household": "family",
        "friend": "friend_acquaintance",
        "associate": "friend_acquaintance",
        "known_person": "friend_acquaintance",
        "friend_or_close_associate": "friend_acquaintance",
        "stranger": "stranger_public",
        "public": "stranger_public",
        "authority_public": "stranger_public",
        "stranger_or_public": "stranger_public",
    }
    return aliases.get(text, text if text in RELATIONSHIP_LABELS else "")


def _expected_relationship_labels(case: Dict[str, Any]) -> List[str]:
    benchmark = _case_benchmark(case)
    explicit = (
        benchmark.get("expected_relationship_labels")
        or benchmark.get("expected_relationship_status")
        or benchmark.get("relationship_status")
    )
    labels: List[str] = []
    if isinstance(explicit, dict):
        raw = explicit.get("labels") or explicit.get("expected_labels") or explicit.get("status")
    else:
        raw = explicit
    if isinstance(raw, str):
        labels.append(_normalize_relationship_label(raw))
    elif isinstance(raw, list):
        labels.extend(_normalize_relationship_label(item) for item in raw)

    if not labels:
        for axis in _expected_axes(case):
            label = RELATIONSHIP_AXIS_LABELS.get(axis)
            if label:
                labels.append(label)
    labels = [label for label in dict.fromkeys(labels) if label in RELATIONSHIP_LABELS]
    return labels


def _primary_relationship_label(labels: Sequence[str]) -> str:
    label_set = set(labels or [])
    for label in RELATIONSHIP_LABELS:
        if label in label_set:
            return label
    return ""


def build_forensic_query(case: Dict[str, Any]) -> Dict[str, str]:
    benchmark = _case_benchmark(case)
    query: Dict[str, Any] = {}
    if isinstance(benchmark.get("query"), dict):
        query = dict(benchmark.get("query") or {})
    elif isinstance(case.get("query"), dict):
        query = dict(case.get("query") or {})
    elif case.get("tested_anchors"):
        anchor = (case.get("tested_anchors") or [None])[0]
        if isinstance(anchor, dict) and isinstance(anchor.get("query"), dict):
            query = dict(anchor.get("query") or {})

    datetime_local = query.pop("datetime_local", None)
    if datetime_local and not query.get("datetime"):
        query["datetime"] = datetime_local
    if query and not query.get("mode"):
        query["mode"] = "manual"
    return {key: str(value) for key, value in query.items() if value is not None}


def _is_runnable_case(case: Dict[str, Any]) -> bool:
    benchmark = _case_benchmark(case)
    replay_status = _normalize_text(benchmark.get("replay_status")).lower()
    if replay_status and replay_status != "runnable":
        return False
    return bool(build_forensic_query(case))


def derive_predicted_axes(forensic_result: Dict[str, Any]) -> List[str]:
    explicit = forensic_result.get("axis_assessment") or {}
    explicit_axes = explicit.get("predicted_axes") if isinstance(explicit, dict) else None
    if isinstance(explicit_axes, list):
        values = {str(axis) for axis in explicit_axes}
        return [axis for axis in AXIS_ORDER if axis in values]
    return assess_axes(forensic_result.get("findings") or [])["predicted_axes"]


def _alignment_from_axes(
    expected_axes: Iterable[str],
    predicted_axes: Iterable[str],
    contradictory_axes: Iterable[str],
) -> Dict[str, Any]:
    expected = list(dict.fromkeys(str(axis) for axis in expected_axes if str(axis).strip()))
    predicted = set(str(axis) for axis in predicted_axes if str(axis).strip())
    contradicted = [axis for axis in contradictory_axes if axis in predicted]
    matched = [axis for axis in expected if axis in predicted]
    missed = [axis for axis in expected if axis not in predicted]

    if contradicted:
        status = "misaligned"
    elif not missed:
        status = "aligned"
    elif matched:
        status = "partially_aligned"
    else:
        status = "misaligned"

    return {
        "status": status,
        "matched_axes": matched,
        "missed_axes": missed,
        "contradicted_axes": contradicted,
    }


def compute_axis_metrics(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    expected_counter: Counter[str] = Counter()
    matched_counter: Counter[str] = Counter()
    negative_counter: Counter[str] = Counter()
    true_negative_counter: Counter[str] = Counter()
    contradiction_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()

    for row in rows:
        expected_axes = list(row.get("expected_axes") or [])
        if row.get("matched_axes") is not None:
            matched_axes = list(row.get("matched_axes") or [])
            contradicted_axes = list(row.get("contradicted_axes") or [])
            contradictory_axes = list(row.get("contradictory_axes") or [])
            missed_axes = [axis for axis in expected_axes if axis not in set(matched_axes)]
            if contradicted_axes:
                status = "misaligned"
            elif not missed_axes:
                status = "aligned"
            elif matched_axes:
                status = "partially_aligned"
            else:
                status = "misaligned"
        else:
            comparison = _alignment_from_axes(
                expected_axes,
                row.get("predicted_axes") or [],
                row.get("contradictory_axes") or [],
            )
            matched_axes = comparison["matched_axes"]
            contradicted_axes = comparison["contradicted_axes"]
            contradictory_axes = list(row.get("contradictory_axes") or [])
            status = comparison["status"]

        expected_counter.update(expected_axes)
        matched_counter.update(axis for axis in matched_axes if axis in set(expected_axes))
        negative_counter.update(contradictory_axes)
        true_negative_counter.update(axis for axis in contradictory_axes if axis not in set(contradicted_axes))
        contradiction_counter.update(contradicted_axes)
        status_counter[status] += 1

    expected_total = sum(expected_counter.values())
    matched_total = sum(matched_counter.values())
    per_axis: Dict[str, Dict[str, Any]] = {}
    recalls: List[float] = []
    for axis in sorted(expected_counter):
        expected_count = expected_counter[axis]
        matched_count = matched_counter.get(axis, 0)
        recall = matched_count / expected_count if expected_count else 0.0
        recalls.append(recall)
        per_axis[axis] = {
            "expected": expected_count,
            "matched": matched_count,
            "recall": _round4(recall),
        }

    micro_recall = matched_total / expected_total if expected_total else None
    macro_recall = statistics.mean(recalls) if recalls else None
    negative_total = sum(negative_counter.values())
    true_negative_total = sum(true_negative_counter.values())
    explicit_contradiction_specificity = true_negative_total / negative_total if negative_total else None
    if micro_recall is not None and explicit_contradiction_specificity is not None:
        labeled_balanced_accuracy = (micro_recall + explicit_contradiction_specificity) / 2.0
    else:
        labeled_balanced_accuracy = micro_recall
    runnable_count = len(rows)

    return {
        "runnable_case_count": runnable_count,
        "aligned_case_count": status_counter.get("aligned", 0),
        "partial_case_count": status_counter.get("partially_aligned", 0),
        "misaligned_case_count": status_counter.get("misaligned", 0),
        "case_alignment_rate": _round4(status_counter.get("aligned", 0) / runnable_count) if runnable_count else None,
        "expected_axis_count": expected_total,
        "matched_axis_count": matched_total,
        "micro_recall": _round4(micro_recall) if micro_recall is not None else None,
        "macro_recall": _round4(macro_recall) if macro_recall is not None else None,
        "negative_axis_count": negative_total,
        "true_negative_axis_count": true_negative_total,
        # These negatives are explicitly labeled contradictions only. Unlisted
        # axes are unknown, so this must not be described as full specificity.
        "explicit_contradiction_specificity": _round4(explicit_contradiction_specificity) if explicit_contradiction_specificity is not None else None,
        "labeled_balanced_accuracy": _round4(labeled_balanced_accuracy) if labeled_balanced_accuracy is not None else None,
        "negative_label_scope": "explicit_contradictory_axes_only",
        # Backward-compatible aliases retained for existing report consumers.
        "specificity": _round4(explicit_contradiction_specificity) if explicit_contradiction_specificity is not None else None,
        "balanced_accuracy": _round4(labeled_balanced_accuracy) if labeled_balanced_accuracy is not None else None,
        "primary_axis_score": _round4(labeled_balanced_accuracy) if labeled_balanced_accuracy is not None else None,
        "false_positive_contradiction_count": sum(contradiction_counter.values()),
        "false_positive_contradictions": dict(sorted(contradiction_counter.items())),
        "per_axis": per_axis,
        "comparison_status_counts": dict(sorted(status_counter.items())),
    }


def compute_survivability_metrics(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    status_counter: Counter[str] = Counter()
    scored = 0
    for row in rows:
        expected_levels = set(row.get("expected_levels") or [])
        expected_bands = set(row.get("expected_bands") or [])
        if not expected_levels and not expected_bands:
            continue
        scored += 1
        level_match = bool(expected_levels and row.get("actual_level") in expected_levels)
        band_match = bool(expected_bands and row.get("actual_band") in expected_bands)
        if level_match and band_match:
            status = "aligned"
        elif level_match or band_match:
            status = "partially_aligned"
        else:
            status = "misaligned"
        status_counter[status] += 1

    aligned = status_counter.get("aligned", 0)
    partial = status_counter.get("partially_aligned", 0)
    return {
        "scored_case_count": scored,
        "aligned_count": aligned,
        "partial_count": partial,
        "misaligned_count": status_counter.get("misaligned", 0),
        "accuracy": _round4(aligned / scored) if scored else None,
        "partial_credit_accuracy": _round4((aligned + partial * 0.5) / scored) if scored else None,
        "status_counts": dict(sorted(status_counter.items())),
    }


def survivability_alignment(row: Dict[str, Any]) -> str:
    expected_levels = set(row.get("expected_levels") or [])
    expected_bands = set(row.get("expected_bands") or [])
    if not expected_levels and not expected_bands:
        return "not_scored"
    level_match = bool(expected_levels and row.get("actual_level") in expected_levels)
    band_match = bool(expected_bands and row.get("actual_band") in expected_bands)
    if level_match and band_match:
        return "aligned"
    if level_match or band_match:
        return "partially_aligned"
    return "misaligned"


def derive_predicted_relationship_labels(forensic_result: Dict[str, Any]) -> List[str]:
    relationship_status = forensic_result.get("relationship_status") or {}
    raw_labels = relationship_status.get("labels") if isinstance(relationship_status, dict) else None
    labels: List[str] = []
    if isinstance(raw_labels, list):
        labels.extend(_normalize_relationship_label(item) for item in raw_labels)
    elif isinstance(raw_labels, str):
        labels.append(_normalize_relationship_label(raw_labels))
    primary = relationship_status.get("primary_label") if isinstance(relationship_status, dict) else None
    if primary:
        labels.append(_normalize_relationship_label(primary))
    labels = [label for label in dict.fromkeys(labels) if label in RELATIONSHIP_LABELS]
    if labels:
        return labels

    predicted_axes = derive_predicted_axes(forensic_result)
    for axis in predicted_axes:
        label = RELATIONSHIP_AXIS_LABELS.get(axis)
        if label:
            labels.append(label)
    labels = [label for label in dict.fromkeys(labels) if label in RELATIONSHIP_LABELS]
    return labels or ["stranger_public"]


def compute_relationship_status_metrics(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    counters = {
        label: {"true_positive": 0, "false_positive": 0, "false_negative": 0}
        for label in RELATIONSHIP_LABELS
    }
    exact = 0
    primary = 0

    scored_rows = [row for row in rows if row.get("expected_relationship_labels")]
    for row in scored_rows:
        expected = set(row.get("expected_relationship_labels") or [])
        predicted = set(row.get("predicted_relationship_labels") or ["stranger_public"])
        if expected == predicted:
            exact += 1
        if row.get("expected_primary_relationship") == row.get("predicted_primary_relationship"):
            primary += 1
        for label in RELATIONSHIP_LABELS:
            if label in expected and label in predicted:
                counters[label]["true_positive"] += 1
            elif label not in expected and label in predicted:
                counters[label]["false_positive"] += 1
            elif label in expected and label not in predicted:
                counters[label]["false_negative"] += 1

    total_tp = sum(item["true_positive"] for item in counters.values())
    total_fp = sum(item["false_positive"] for item in counters.values())
    total_fn = sum(item["false_negative"] for item in counters.values())

    def _precision(tp: int, fp: int) -> Optional[float]:
        return tp / (tp + fp) if (tp + fp) else None

    def _recall(tp: int, fn: int) -> Optional[float]:
        return tp / (tp + fn) if (tp + fn) else None

    def _f1(precision: Optional[float], recall: Optional[float]) -> Optional[float]:
        if precision is None or recall is None or (precision + recall) == 0:
            return None
        return 2 * precision * recall / (precision + recall)

    per_label: Dict[str, Dict[str, Any]] = {}
    f1_values: List[float] = []
    for label, counts in counters.items():
        precision = _precision(counts["true_positive"], counts["false_positive"])
        recall = _recall(counts["true_positive"], counts["false_negative"])
        f1 = _f1(precision, recall)
        if f1 is not None:
            f1_values.append(f1)
        per_label[label] = {
            **counts,
            "precision": _round4(precision) if precision is not None else None,
            "recall": _round4(recall) if recall is not None else None,
            "f1": _round4(f1) if f1 is not None else None,
        }

    micro_precision = _precision(total_tp, total_fp)
    micro_recall = _recall(total_tp, total_fn)
    micro_f1 = _f1(micro_precision, micro_recall)
    case_count = len(scored_rows)
    return {
        "case_count": case_count,
        "exact_match_count": exact,
        "primary_match_count": primary,
        "exact_match_rate": _round4(exact / case_count) if case_count else None,
        "primary_accuracy": _round4(primary / case_count) if case_count else None,
        "true_positive": total_tp,
        "false_positive": total_fp,
        "false_negative": total_fn,
        "micro_precision": _round4(micro_precision) if micro_precision is not None else None,
        "micro_recall": _round4(micro_recall) if micro_recall is not None else None,
        "micro_f1": _round4(micro_f1) if micro_f1 is not None else None,
        "macro_f1": _round4(statistics.mean(f1_values)) if f1_values else None,
        "per_label": per_label,
    }


def compute_light_mediation_calibration_metrics(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    signal_count = 0
    deltas: List[float] = []
    effect_counter: Counter[str] = Counter()
    visibility_counter: Counter[str] = Counter()
    level_flip_count = 0
    band_flip_count = 0

    for row in rows:
        impact = row.get("light_mediation_impact")
        if not isinstance(impact, dict):
            continue
        effect = str(impact.get("effect") or "none")
        delta = _round4(impact.get("score_delta")) or 0.0
        if effect == "none" and not delta:
            continue
        signal_count += 1
        deltas.append(abs(delta))
        effect_counter.update([effect])
        visibility_counter.update([str(impact.get("visibility") or "unknown")])
        if impact.get("level_changed"):
            level_flip_count += 1
        if impact.get("band_changed"):
            band_flip_count += 1

    return {
        "case_count_with_signal": signal_count,
        "raw_delta_case_count": sum(1 for value in deltas if value > 0.0),
        "delta_ge_0_25_count": sum(1 for value in deltas if value >= 0.25),
        "level_flip_count": level_flip_count,
        "band_flip_count": band_flip_count,
        "mean_abs_score_delta": round(statistics.mean(deltas), 4) if deltas else 0.0,
        "max_abs_score_delta": round(max(deltas), 4) if deltas else 0.0,
        "effect_counts": dict(sorted(effect_counter.items())),
        "visibility_counts": dict(sorted(visibility_counter.items())),
    }


def compute_null_significance(observed: Optional[float], controls: Sequence[float]) -> Dict[str, Any]:
    clean_controls = [float(value) for value in controls if value is not None]
    if observed is None or not clean_controls:
        return {
            "observed": _round4(observed),
            "control_count": len(clean_controls),
            "control_mean": None,
            "control_max": None,
            "empirical_p_value": None,
        }
    exceed_or_equal = sum(1 for value in clean_controls if value >= float(observed))
    p_value = (exceed_or_equal + 1) / (len(clean_controls) + 1)
    return {
        "observed": _round4(observed),
        "control_count": len(clean_controls),
        "control_mean": _round4(statistics.mean(clean_controls)),
        "control_median": _round4(statistics.median(clean_controls)),
        "control_max": _round4(max(clean_controls)),
        "empirical_p_value": _round4(p_value),
        "significant_at_0_05": bool(p_value < 0.05),
    }


def _case_recall(row: Dict[str, Any]) -> float:
    expected = set(row.get("expected_axes") or [])
    if not expected:
        return 0.0
    if row.get("predicted_axes") is not None:
        predicted = set(row.get("predicted_axes") or [])
        return len(expected & predicted) / len(expected)
    matched = set(row.get("matched_axes") or [])
    return len(expected & matched) / len(expected)


def bootstrap_case_recall_ci(
    rows: Sequence[Dict[str, Any]],
    *,
    iterations: int = 1000,
    seed: int = 17,
) -> Dict[str, Any]:
    if not rows:
        return {"mean": None, "ci95": [None, None], "iterations": 0}
    rng = random.Random(seed)
    recalls = [_case_recall(row) for row in rows]
    boot: List[float] = []
    for _ in range(max(1, iterations)):
        sample = [rng.choice(recalls) for _ in recalls]
        boot.append(statistics.mean(sample))
    boot.sort()
    lower_idx = int(0.025 * (len(boot) - 1))
    upper_idx = int(0.975 * (len(boot) - 1))
    return {
        "mean": _round4(statistics.mean(recalls)),
        "ci95": [_round4(boot[lower_idx]), _round4(boot[upper_idx])],
        "iterations": len(boot),
    }


def bootstrap_relationship_macro_f1_ci(
    rows: Sequence[Dict[str, Any]],
    *,
    iterations: int = 1000,
    seed: int = 29,
) -> Dict[str, Any]:
    scored_rows = [row for row in rows if row.get("expected_relationship_labels")]
    if not scored_rows:
        return {"mean": None, "ci95": [None, None], "iterations": 0}
    rng = random.Random(seed)
    boot: List[float] = []
    for _ in range(max(1, iterations)):
        sample = [rng.choice(scored_rows) for _ in scored_rows]
        value = compute_relationship_status_metrics(sample).get("macro_f1")
        if value is not None:
            boot.append(float(value))
    if not boot:
        return {"mean": None, "ci95": [None, None], "iterations": 0}
    boot.sort()
    lower_idx = int(0.025 * (len(boot) - 1))
    upper_idx = int(0.975 * (len(boot) - 1))
    return {
        "mean": _round4(compute_relationship_status_metrics(scored_rows).get("macro_f1")),
        "ci95": [_round4(boot[lower_idx]), _round4(boot[upper_idx])],
        "iterations": len(boot),
    }


def _permutation_control_metric(
    rows: Sequence[Dict[str, Any]],
    *,
    metric_key: str,
    max_controls: int = 100,
    seed: int = 1729,
) -> List[float]:
    if len(rows) < 2:
        return []
    controls: List[float] = []
    rng = random.Random(seed)
    control_count = max(0, int(max_controls))
    for _ in range(control_count):
        donor_order = list(range(len(rows)))
        rng.shuffle(donor_order)
        null_rows: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows):
            donor = rows[donor_order[idx]]
            null_rows.append(
                {
                    "expected_axes": list(row.get("expected_axes") or []),
                    "predicted_axes": list(donor.get("predicted_axes") or []),
                    "contradictory_axes": list(row.get("contradictory_axes") or []),
                }
            )
        value = compute_axis_metrics(null_rows).get(metric_key)
        if value is not None:
            controls.append(float(value))
    return controls


def _permutation_relationship_control_metric(
    rows: Sequence[Dict[str, Any]],
    *,
    metric_key: str,
    max_controls: int = 100,
    seed: int = 2718,
) -> List[float]:
    scored_rows = [row for row in rows if row.get("expected_relationship_labels")]
    if len(scored_rows) < 2:
        return []
    controls: List[float] = []
    rng = random.Random(seed)
    control_count = max(0, int(max_controls))
    for _ in range(control_count):
        donor_order = list(range(len(scored_rows)))
        rng.shuffle(donor_order)
        null_rows: List[Dict[str, Any]] = []
        for idx, row in enumerate(scored_rows):
            donor = scored_rows[donor_order[idx]]
            null_rows.append(
                {
                    "expected_relationship_labels": list(row.get("expected_relationship_labels") or []),
                    "predicted_relationship_labels": list(donor.get("predicted_relationship_labels") or []),
                    "expected_primary_relationship": row.get("expected_primary_relationship"),
                    "predicted_primary_relationship": donor.get("predicted_primary_relationship"),
                }
            )
        value = compute_relationship_status_metrics(null_rows).get(metric_key)
        if value is not None:
            controls.append(float(value))
    return controls


def load_statistical_cases(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    selected_paths = [Path(path) for path in (dataset_paths or DEFAULT_DATASET_PATHS)]
    normalized_case_id = _normalize_text(case_id).lower()
    cases: List[Dict[str, Any]] = []
    for dataset_path in selected_paths:
        path = dataset_path if dataset_path.is_absolute() else REPO_ROOT / dataset_path
        if not path.exists():
            raise FileNotFoundError(f"Forensic statistical benchmark dataset not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        for index, case in enumerate(payload.get("cases") or []):
            if not isinstance(case, dict):
                continue
            current_case_id = _case_id(case, path, index)
            if normalized_case_id and current_case_id.lower() != normalized_case_id:
                continue
            exclusion_reason = benchmark_exclusion_reason(case)
            if exclusion_reason:
                if normalized_case_id:
                    raise ValueError(f"Excluded forensic statistical benchmark case id: {case_id}. {exclusion_reason}")
                continue
            if not _expected_axes(case) or not _is_runnable_case(case):
                continue
            cases.append(
                {
                    "case_id": current_case_id,
                    "dataset_path": str(path),
                    "dataset_name": path.name,
                    "case": case,
                    "expected_axes": _expected_axes(case),
                    "contradictory_axes": _contradictory_axes(case),
                    "query": build_forensic_query(case),
                    "expected_survivability": _expected_survivability(case),
                    "expected_relationship_labels": _expected_relationship_labels(case),
                    "known_outcome": case.get("known_outcome") if isinstance(case.get("known_outcome"), dict) else {},
                    "family": case.get("family"),
                }
            )
    if normalized_case_id and not cases:
        raise ValueError(f"Unknown runnable forensic statistical benchmark case id: {case_id}")
    return cases


def run_statistical_benchmark_suite(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
    case_limit: Optional[int] = None,
    house_system_code: Optional[str] = None,
    use_secondary_factors: bool = False,
    include_control_cases: bool = True,
    control_iterations: int = 100,
    bootstrap_iterations: int = 1000,
    control_seed: int = 1729,
) -> Dict[str, Any]:
    cases = load_statistical_cases(dataset_paths, case_id=case_id)
    if case_limit is not None:
        cases = cases[: max(0, int(case_limit))]
    house_system_override = _normalize_text(house_system_code).upper() if house_system_code else None

    axis_rows: List[Dict[str, Any]] = []
    survival_rows: List[Dict[str, Any]] = []
    relationship_rows: List[Dict[str, Any]] = []
    case_results: List[Dict[str, Any]] = []
    route_errors: List[Dict[str, Any]] = []

    for item in cases:
        query = dict(item["query"])
        if house_system_override:
            query["house_system_code"] = house_system_override
        query["secondary_factors"] = "1" if use_secondary_factors else "0"
        route_result = _call_forensic_route(query)
        payload = route_result.get("payload") or {}
        if route_result.get("status_code") != 200 or not payload.get("success"):
            route_errors.append(
                {
                    "case_id": item["case_id"],
                    "status_code": route_result.get("status_code"),
                    "error": payload.get("error"),
                }
            )
            continue

        predicted_axes = derive_predicted_axes(payload)
        comparison = _alignment_from_axes(
            item["expected_axes"],
            predicted_axes,
            item["contradictory_axes"],
        )
        axis_row = {
            "case_id": item["case_id"],
            "dataset_name": item["dataset_name"],
            "expected_axes": item["expected_axes"],
            "predicted_axes": predicted_axes,
            "matched_axes": comparison["matched_axes"],
            "missed_axes": comparison["missed_axes"],
            "contradicted_axes": comparison["contradicted_axes"],
            "contradictory_axes": item["contradictory_axes"],
            "status": comparison["status"],
        }
        axis_rows.append(axis_row)

        survivability = payload.get("survivability") or {}
        expected_survival = item["expected_survivability"]
        survival_row = {
            "case_id": item["case_id"],
            "expected_levels": expected_survival.get("levels") or [],
            "expected_bands": expected_survival.get("bands") or [],
            "actual_level": survivability.get("level"),
            "actual_band": survivability.get("outcome_band"),
            "actual_score": survivability.get("score"),
            "light_mediation_impact": survivability.get("light_mediation_impact"),
        }
        survival_rows.append(survival_row)

        expected_relationship = list(item.get("expected_relationship_labels") or [])
        predicted_relationship = derive_predicted_relationship_labels(payload)
        relationship_row = {
            "case_id": item["case_id"],
            "dataset_name": item["dataset_name"],
            "expected_relationship_labels": expected_relationship,
            "predicted_relationship_labels": predicted_relationship,
            "expected_primary_relationship": _primary_relationship_label(expected_relationship),
            "predicted_primary_relationship": _primary_relationship_label(predicted_relationship),
            "relationship_status": payload.get("relationship_status") or {},
        }
        relationship_rows.append(relationship_row)

        case_results.append(
            {
                **axis_row,
                "relationship": {
                    "expected_labels": relationship_row["expected_relationship_labels"],
                    "predicted_labels": relationship_row["predicted_relationship_labels"],
                    "expected_primary": relationship_row["expected_primary_relationship"],
                    "predicted_primary": relationship_row["predicted_primary_relationship"],
                    "status": relationship_row["relationship_status"],
                },
                "survivability": {
                    "known_outcome": item.get("known_outcome") or {},
                    "expected_levels": survival_row["expected_levels"],
                    "expected_bands": survival_row["expected_bands"],
                    "actual_level": survival_row["actual_level"],
                    "actual_band": survival_row["actual_band"],
                    "actual_score": survival_row["actual_score"],
                    "light_mediation_impact": survival_row["light_mediation_impact"],
                    "comparison": survivability_alignment(survival_row),
                },
                "top_findings": [
                    {
                        "id": finding.get("id"),
                        "title": finding.get("title"),
                        "category": finding.get("category"),
                        "weight": finding.get("weight"),
                    }
                    for finding in (payload.get("findings") or [])[:8]
                    if isinstance(finding, dict)
                ],
            }
        )

    axis_metrics = compute_axis_metrics(axis_rows)
    survival_metrics = compute_survivability_metrics(survival_rows)
    relationship_metrics = compute_relationship_status_metrics(relationship_rows)
    light_mediation_calibration_metrics = compute_light_mediation_calibration_metrics(survival_rows)
    control_recalls = (
        _permutation_control_metric(axis_rows, metric_key="micro_recall", max_controls=control_iterations, seed=control_seed)
        if include_control_cases
        else []
    )
    control_balanced_scores = (
        _permutation_control_metric(axis_rows, metric_key="balanced_accuracy", max_controls=control_iterations, seed=control_seed)
        if include_control_cases
        else []
    )
    control_relationship_macro_f1 = (
        _permutation_relationship_control_metric(
            relationship_rows,
            metric_key="macro_f1",
            max_controls=control_iterations,
            seed=control_seed + 1,
        )
        if include_control_cases
        else []
    )

    report = {
        "benchmark_id": "forensic_statistical_axis_detection_v1",
        "evaluation_design": {
            "mode": "known_outcome_conditional_replay",
            "axis_prediction_basis": "explicit_rule_id_category_mapping_v1",
            "uses_free_text_for_axis_prediction": False,
            "null_control": "seeded_monte_carlo_label_permutation",
            "control_seed": int(control_seed),
            "limitations": [
                "Curated known cases are not a prospective blind validation sample.",
                "Chart inputs may include contextual labels such as case type and location.",
                "Metrics characterize this fixture set only and do not establish real-world forensic validity.",
            ],
        },
        "dataset_paths": sorted({item["dataset_path"] for item in cases}),
        "primary_target": "case_axis_detection",
        "secondary_target": "survivability_outcome_direction",
        "house_system_code": house_system_override,
        "secondary_factors_enabled": bool(use_secondary_factors),
        "case_count": len(cases),
        "route_error_count": len(route_errors),
        "route_errors": route_errors,
        "primary_axis_metrics": axis_metrics,
        "secondary_survivability_metrics": survival_metrics,
        "relationship_status_metrics": relationship_metrics,
        "light_mediation_calibration_metrics": light_mediation_calibration_metrics,
        "significance": {
            "axis_balanced_accuracy": compute_null_significance(
                axis_metrics.get("balanced_accuracy"),
                control_balanced_scores,
            ),
            "axis_micro_recall": compute_null_significance(
                axis_metrics.get("micro_recall"),
                control_recalls,
            ),
            "relationship_macro_f1": compute_null_significance(
                relationship_metrics.get("macro_f1"),
                control_relationship_macro_f1,
            ),
        },
        "confidence_intervals": {
            "axis_case_recall_bootstrap": bootstrap_case_recall_ci(
                axis_rows,
                iterations=bootstrap_iterations,
            ),
            "relationship_macro_f1_bootstrap": bootstrap_relationship_macro_f1_ci(
                relationship_rows,
                iterations=bootstrap_iterations,
            ),
        },
        "case_results": case_results,
    }
    return report


def render_markdown_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Forensic Statistical Benchmark Report")
    lines.append("")
    lines.append("- Primary target: case-axis detection")
    lines.append("- Secondary target: survivability/outcome direction")
    lines.append(f"- Benchmark ID: `{report.get('benchmark_id')}`")
    if report.get("house_system_code"):
        lines.append(f"- House system override: `{report.get('house_system_code')}`")
    if report.get("secondary_factors_enabled"):
        lines.append("- Asteroid/special-degree secondary factors: enabled")
    lines.append(f"- Runnable cases: {report.get('case_count')}")
    lines.append(f"- Route errors: {report.get('route_error_count')}")
    design = report.get("evaluation_design") or {}
    if design:
        lines.append(f"- Evaluation mode: {design.get('mode')}")
        lines.append(f"- Axis basis: {design.get('axis_prediction_basis')}")
    lines.append("")

    axis = report.get("primary_axis_metrics") or {}
    lines.append("## Primary Axis Metrics")
    lines.append("")
    lines.append(
        "- Micro recall: "
        f"{axis.get('matched_axis_count')}/{axis.get('expected_axis_count')} = {axis.get('micro_recall')}"
    )
    lines.append(
        f"- Explicit-contradiction specificity (not full specificity): "
        f"{axis.get('explicit_contradiction_specificity')}"
    )
    lines.append(f"- Balanced accuracy: {axis.get('balanced_accuracy')}")
    lines.append(f"- Macro recall: {axis.get('macro_recall')}")
    lines.append(f"- Case statuses: `{axis.get('comparison_status_counts')}`")
    lines.append(f"- False-positive contradictions: `{axis.get('false_positive_contradictions')}`")
    lines.append("")

    significance = ((report.get("significance") or {}).get("axis_balanced_accuracy") or {})
    lines.append("## Conditional Permutation Comparison")
    lines.append("")
    lines.append(f"- Observed primary axis score: {significance.get('observed')}")
    lines.append(f"- Null-control mean: {significance.get('control_mean')}")
    lines.append(f"- Null-control count: {significance.get('control_count')}")
    lines.append(f"- Fixture-level empirical p-value: {significance.get('empirical_p_value')}")
    lines.append("- This conditional replay comparison is not evidence of real-world forensic validity.")
    ci = ((report.get("confidence_intervals") or {}).get("axis_case_recall_bootstrap") or {})
    lines.append(f"- Bootstrap case-recall 95% CI: `{ci.get('ci95')}`")
    lines.append("")

    survival = report.get("secondary_survivability_metrics") or {}
    lines.append("## Secondary Survivability")
    lines.append("")
    lines.append(f"- Scored cases: {survival.get('scored_case_count')}")
    lines.append(f"- Accuracy: {survival.get('accuracy')}")
    lines.append(f"- Partial-credit accuracy: {survival.get('partial_credit_accuracy')}")
    lines.append(f"- Statuses: `{survival.get('status_counts')}`")
    lines.append("")

    relationship = report.get("relationship_status_metrics") or {}
    lines.append("## Relationship Status")
    lines.append("")
    lines.append(f"- Scored cases: {relationship.get('case_count')}")
    lines.append(f"- Primary-label accuracy: {relationship.get('primary_accuracy')}")
    lines.append(f"- Exact-label match rate: {relationship.get('exact_match_rate')}")
    lines.append(f"- Micro precision: {relationship.get('micro_precision')}")
    lines.append(f"- Micro recall: {relationship.get('micro_recall')}")
    lines.append(f"- Micro F1: {relationship.get('micro_f1')}")
    lines.append(f"- Macro F1: {relationship.get('macro_f1')}")
    rel_sig = ((report.get("significance") or {}).get("relationship_macro_f1") or {})
    lines.append(f"- Relationship macro-F1 empirical p-value: {rel_sig.get('empirical_p_value')}")
    rel_ci = ((report.get("confidence_intervals") or {}).get("relationship_macro_f1_bootstrap") or {})
    lines.append(f"- Relationship macro-F1 95% CI: `{rel_ci.get('ci95')}`")
    lines.append(f"- Per-label: `{relationship.get('per_label')}`")
    lines.append("")

    light_calibration = report.get("light_mediation_calibration_metrics") or {}
    lines.append("## Light Mediation Calibration")
    lines.append("")
    lines.append(f"- Cases with light-mediation signal: {light_calibration.get('case_count_with_signal')}")
    lines.append(f"- Raw score deltas: {light_calibration.get('raw_delta_case_count')}")
    lines.append(f"- Delta >= 0.25: {light_calibration.get('delta_ge_0_25_count')}")
    lines.append(f"- Level flips: {light_calibration.get('level_flip_count')}")
    lines.append(f"- Band flips: {light_calibration.get('band_flip_count')}")
    lines.append(f"- Mean absolute score delta: {light_calibration.get('mean_abs_score_delta')}")
    lines.append(f"- Max absolute score delta: {light_calibration.get('max_abs_score_delta')}")
    lines.append(f"- Effects: `{light_calibration.get('effect_counts')}`")
    lines.append(f"- Visibility: `{light_calibration.get('visibility_counts')}`")
    lines.append("")

    route_errors = report.get("route_errors") or []
    if route_errors:
        lines.append("## Route Errors")
        lines.append("")
        for error in route_errors:
            lines.append(
                f"- `{error.get('case_id')}`: status={error.get('status_code')} error={error.get('error')}"
            )
        lines.append("")

    lines.append("## Cases")
    lines.append("")
    for result in report.get("case_results") or []:
        survival_result = result.get("survivability") or {}
        relationship_result = result.get("relationship") or {}
        relationship_text = (
            f"relationship={relationship_result.get('predicted_primary')}/{relationship_result.get('expected_primary')}; "
            if relationship_result.get("expected_labels")
            else "relationship=not_scored; "
        )
        known_outcome = survival_result.get("known_outcome") or {}
        outcome_text = (
            f"known={known_outcome.get('class')} "
            f"({known_outcome.get('survivors')}/{known_outcome.get('occupants')} survived); "
            if known_outcome else ""
        )
        lines.append(
            f"- `{result.get('case_id')}` ({result.get('dataset_name')}): {result.get('status')}; "
            f"matched={result.get('matched_axes')}; missed={result.get('missed_axes')}; "
            f"contradicted={result.get('contradicted_axes')}; "
            f"{relationship_text}"
            f"{outcome_text}survivability={survival_result.get('actual_level')}/{survival_result.get('actual_band')} "
            f"[{survival_result.get('comparison')}]"
        )

    return "\n".join(lines).strip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the forensic statistical benchmark with case-axis detection as the primary target."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--case-id", help="Restrict execution to a single case id.")
    parser.add_argument("--case-limit", type=int, help="Run only the first N runnable cases.")
    parser.add_argument(
        "--dataset",
        action="append",
        help="Dataset path. May be repeated. Defaults to the curated forensic benchmark datasets.",
    )
    parser.add_argument(
        "--house-system-code",
        help="Override fixture house systems for sensitivity scans, e.g. R, P, W, E, C.",
    )
    parser.add_argument(
        "--secondary-factors",
        action="store_true",
        help="Enable asteroid/special-degree secondary forensic factors.",
    )
    parser.add_argument(
        "--no-controls",
        action="store_true",
        help="Skip permutation null-control significance.",
    )
    parser.add_argument(
        "--control-iterations",
        type=int,
        default=100,
        help="Number of seeded Monte Carlo label permutations to evaluate.",
    )
    parser.add_argument(
        "--bootstrap-iterations",
        type=int,
        default=1000,
        help="Bootstrap iterations for case-recall confidence interval.",
    )
    args = parser.parse_args(argv)

    report = run_statistical_benchmark_suite(
        args.dataset,
        case_id=args.case_id,
        case_limit=args.case_limit,
        house_system_code=args.house_system_code,
        use_secondary_factors=args.secondary_factors,
        include_control_cases=not args.no_controls,
        control_iterations=args.control_iterations,
        bootstrap_iterations=args.bootstrap_iterations,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown_report(report))
    return 1 if report.get("route_errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
