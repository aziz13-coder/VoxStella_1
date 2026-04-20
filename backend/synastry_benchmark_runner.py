from __future__ import annotations

import argparse
import copy
import json
import os
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from synastry_multi_engine import build_synastry_engine_report
from validate_synastry_benchmark_datasets import (
    DEFAULT_LOGIC_FIXTURE_PATHS,
    DEFAULT_PREDICTIVE_DATASET_PATHS,
    load_logic_fixture,
    load_synastry_predictive_dataset,
    validate_synastry_benchmark_datasets,
)


DEFAULT_OPTIONS: Dict[str, Any] = {
    "include_modern": True,
    "include_nodes": True,
    "include_chiron": False,
    "orb_profile": "balanced",
}

MODEL_SPECS: Dict[str, Dict[str, Any]] = {
    "memo_overall_score": {
        "label": "Memo overall score",
        "engine_id": "memo",
        "score_path": ("summary", "overall_score"),
    },
    "memo_legacy_score": {
        "label": "Memo legacy score",
        "engine_id": "memo",
        "score_fn": "memo_legacy_score",
    },
    "life_themes_theme_total": {
        "label": "Life Themes theme total",
        "engine_id": "life_themes",
        "score_path": ("summary", "theme_total"),
    },
    "life_themes_aspect_total": {
        "label": "Life Themes aspect total",
        "engine_id": "life_themes",
        "score_path": ("summary", "aspect_total"),
    },
    "life_themes_composite_total": {
        "label": "Life Themes composite total",
        "engine_id": "life_themes",
        "score_path": ("summary", "composite_total"),
    },
    "union_dynamics_theme_total": {
        "label": "Union Dynamics theme total",
        "engine_id": "union_dynamics",
        "score_path": ("summary", "theme_total"),
    },
    "union_dynamics_aspect_total": {
        "label": "Union Dynamics aspect total",
        "engine_id": "union_dynamics",
        "score_path": ("summary", "aspect_total"),
    },
    "union_dynamics_composite_total": {
        "label": "Union Dynamics composite total",
        "engine_id": "union_dynamics",
        "score_path": ("summary", "composite_total"),
    },
    "work_alliance_theme_total": {
        "label": "Work Alliance theme total",
        "engine_id": "work_alliance",
        "score_path": ("summary", "theme_total"),
    },
    "work_alliance_aspect_total": {
        "label": "Work Alliance aspect total",
        "engine_id": "work_alliance",
        "score_path": ("summary", "aspect_total"),
    },
    "work_alliance_composite_total": {
        "label": "Work Alliance composite total",
        "engine_id": "work_alliance",
        "score_path": ("summary", "composite_total"),
    },
}

PREDICTIVE_MODELS_BY_MODE: Dict[str, Tuple[str, ...]] = {
    "overall": (
        "memo_overall_score",
        "memo_legacy_score",
        "life_themes_theme_total",
        "life_themes_aspect_total",
        "life_themes_composite_total",
    ),
    "union": (
        "memo_overall_score",
        "union_dynamics_theme_total",
        "union_dynamics_aspect_total",
        "union_dynamics_composite_total",
    ),
    "work": (
        "memo_overall_score",
        "work_alliance_theme_total",
        "work_alliance_aspect_total",
        "work_alliance_composite_total",
    ),
}

LOGIC_MODELS: Tuple[str, ...] = (
    "memo_overall_score",
    "life_themes_composite_total",
    "union_dynamics_composite_total",
    "work_alliance_composite_total",
)

WORK_OUTCOME_MODELS: Tuple[str, ...] = tuple(PREDICTIVE_MODELS_BY_MODE["work"])
WORK_OUTCOME_LABELS: Dict[str, str] = {
    "durable_success": "durable_success",
    "enduring_success": "durable_success",
    "productive_then_breakdown": "productive_then_breakdown",
    "split_litigated": "productive_then_breakdown",
    "split": "productive_then_breakdown",
    "breakdown": "productive_then_breakdown",
}


def _ensure_dev_env() -> None:
    os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
    os.environ.setdefault("VOX_STELLA_ENV", "development")


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_mode(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"overall", "life_themes", "themes"}:
        return "overall"
    if raw in {"union", "union_dynamics", "marital", "relationship"}:
        return "union"
    if raw in {"work", "work_alliance", "business"}:
        return "work"
    return "overall"


def _normalize_profile(value: Any) -> Optional[str]:
    raw = str(value or "").strip().lower()
    if raw in {"f", "female", "feminine", "woman"}:
        return "feminine"
    if raw in {"m", "male", "masculine", "man"}:
        return "masculine"
    if raw in {"blended", "mixed"}:
        return "blended"
    return None


def _merge_options(case_options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = dict(DEFAULT_OPTIONS)
    if isinstance(case_options, dict):
        merged.update(case_options)
    return merged


def _score_from_report(report: Dict[str, Any], model_id: str) -> float:
    spec = MODEL_SPECS[model_id]
    score_fn = str(spec.get("score_fn") or "").strip()
    if score_fn:
        if score_fn == "memo_legacy_score":
            return _score_memo_legacy_report(report)
        raise KeyError(f"Unsupported derived score function: {score_fn}")
    value: Any = report
    for key in spec["score_path"]:
        value = value.get(key) if isinstance(value, dict) else None
    return float(value or 0.0)


def _score_memo_legacy_report(report: Dict[str, Any]) -> float:
    components = dict((report.get("summary") or {}).get("overall_components") or {})
    legacy_value = components.get("legacy_weighted_total")
    if legacy_value is not None:
        return round(float(legacy_value or 0.0), 4)

    weights = dict(components.get("weights") or {})
    return round(
        (float(components.get("compatibility") or 0.0) * float(weights.get("compatibility", 0.30)))
        + (float(components.get("binding") or 0.0) * float(weights.get("binding", 0.22)))
        + (float(components.get("growth") or 0.0) * float(weights.get("growth", 0.12)))
        + (float(components.get("support_balance") or 0.0) * float(weights.get("support_balance", 0.26)))
        - (float(components.get("challenge") or 0.0) * float(weights.get("challenge", 0.18)))
        + float(components.get("reception_bonus") or 0.0),
        4,
    )


def _safe_median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(median(values))


def _safe_mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _normalize_work_outcome_label(value: Any) -> Optional[str]:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    return WORK_OUTCOME_LABELS.get(raw)


def _decode_compact_coord(token: Any) -> float:
    text = str(token or "").strip().upper()
    if len(text) < 2 or text[-1] not in {"N", "S", "E", "W"}:
        raise ValueError(f"Unsupported coordinate token: {token!r}")
    digits = "".join(ch for ch in text[:-1] if ch.isdigit())
    if len(digits) < 4:
        raise ValueError(f"Coordinate token has too few digits: {token!r}")
    degree_digits = len(digits) - 4
    degrees = int(digits[:degree_digits] or "0")
    minutes = int(digits[degree_digits : degree_digits + 2] or "0")
    seconds = int(digits[degree_digits + 2 :] or "0")
    value = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if text[-1] in {"S", "W"}:
        value *= -1.0
    return round(value, 8)


def _offset_suffix(token: Any) -> str:
    text = str(token or "").strip()
    if not text:
        return "+00:00"
    sign = "-" if text.startswith("-") else "+"
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) < 4:
        return "+00:00"
    hours = digits[:2]
    minutes = digits[2:4]
    seconds = digits[4:6] if len(digits) >= 6 else "00"
    if seconds != "00":
        return f"{sign}{hours}:{minutes}:{seconds}"
    return f"{sign}{hours}:{minutes}"


def _local_datetime_with_offset(value: Any, offset_token: Any) -> str:
    if isinstance(value, datetime):
        dt = value.replace(microsecond=0)
    else:
        dt = datetime.fromisoformat(str(value or "").strip())
        dt = dt.replace(microsecond=0)
    if dt.tzinfo is not None:
        return dt.isoformat()
    return f"{dt.isoformat()}{_offset_suffix(offset_token)}"


def _copy_cache_entry(entry: Tuple[Dict[str, Any], Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    bundle, chart_meta = entry
    return copy.deepcopy(bundle), copy.deepcopy(chart_meta)


def _build_chart_meta(person: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    chart_meta: Dict[str, Any] = {
        "id": str(person.get("person_id") or ""),
        "label": str(person.get("label") or person.get("person_id") or "Unknown"),
        "effective_datetime": str(meta.get("timestamp") or person.get("dt") or ""),
        "location": str(meta.get("location") or person.get("place") or person.get("location") or ""),
    }
    profile_hint = _normalize_profile(person.get("profile_hint") or person.get("sex"))
    if profile_hint:
        chart_meta["profile_hint"] = profile_hint
    return chart_meta


def _resolve_chart_data_person(person: Dict[str, Any], house_system_code: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    chart_data = copy.deepcopy(person.get("chart_data") or {})
    chart_data.setdefault("house_system_code", house_system_code)
    meta = {
        "timestamp": person.get("timestamp") or person.get("dt") or "2026-04-19T10:00:00+00:00",
        "location": person.get("place") or person.get("location") or person.get("label") or "",
        "timezone": person.get("timezone") or "UTC",
    }
    bundle = {"chart_data": chart_data, "meta": {"label": person.get("label") or person.get("person_id")}}
    return bundle, _build_chart_meta(person, meta)


def _resolve_raw_or_bank_person(
    person: Dict[str, Any],
    house_system_code: str,
    *,
    include_modern: bool,
    include_chiron: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    _ensure_dev_env()
    from astro_clock_api import _compute_chart_bundle_for, _extend_chart_data_for_synastry

    person_kind = str(person.get("kind") or "").strip().lower()
    if person_kind == "raw":
        dt_iso = _local_datetime_with_offset(person.get("dt"), person.get("delta_t"))
        location = str(person.get("place") or person.get("location") or person.get("label") or "").strip()
        latitude = _decode_compact_coord(person.get("lat"))
        longitude = _decode_compact_coord(person.get("lon"))
    else:
        from dbfread import DBF

        dbf_path = Path(str(person.get("dbf") or "")).expanduser()
        if not dbf_path.is_absolute():
            bank_root = Path(
                os.environ.get("VOX_STELLA_GALAXY_BANK_ROOT")
                or r"C:\Program Files (x86)\Galaxy\DataUser\Bank"
            )
            dbf_path = bank_root / dbf_path
        table = DBF(str(dbf_path), load=True, char_decode_errors="ignore")
        row_index = int(person.get("row"))
        if row_index < 0 or row_index >= len(table.records):
            raise IndexError(f"{dbf_path.name} row index out of range: {row_index}")
        row = table.records[row_index]
        dt_iso = _local_datetime_with_offset(row.get("DDT"), row.get("CDT"))
        location = _normalize_text(row.get("CPNAME") or person.get("label"))
        latitude = _decode_compact_coord(row.get("CLAT"))
        longitude = _decode_compact_coord(row.get("CLON"))

    bundle = _compute_chart_bundle_for(
        dt_iso,
        location,
        None,
        house_system_code=house_system_code,
        latitude=latitude,
        longitude=longitude,
    )
    chart_data = bundle.get("chart_data") or {}
    meta = bundle.get("meta") or {
        "timestamp": dt_iso,
        "location": location,
        "timezone": "UTC",
    }
    chart_data = _extend_chart_data_for_synastry(
        chart_data,
        meta,
        include_modern=include_modern,
        include_chiron=include_chiron,
    )
    resolved_bundle = {
        "chart_data": chart_data,
        "meta": {"label": person.get("label") or person.get("person_id")},
    }
    return resolved_bundle, _build_chart_meta(person, meta)


def _resolve_person_entry(
    person: Dict[str, Any],
    *,
    house_system_code: str,
    include_modern: bool,
    include_chiron: bool,
    cache: Dict[Tuple[str, str, bool, bool], Tuple[Dict[str, Any], Dict[str, Any]]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    cache_key = (
        str(person.get("person_id") or ""),
        house_system_code,
        bool(include_modern),
        bool(include_chiron),
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return _copy_cache_entry(cached)

    kind = str(person.get("kind") or "").strip().lower()
    if kind == "chart_data":
        resolved = _resolve_chart_data_person(person, house_system_code)
    else:
        resolved = _resolve_raw_or_bank_person(
            person,
            house_system_code,
            include_modern=include_modern,
            include_chiron=include_chiron,
        )
    cache[cache_key] = _copy_cache_entry(resolved)
    return _copy_cache_entry(resolved)


def _load_predictive_registry(
    dataset_paths: Sequence[str | Path],
    *,
    case_id: Optional[str],
    include_disabled: bool,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    people_by_id: Dict[str, Dict[str, Any]] = {}
    cases: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()

    for raw_path in dataset_paths:
        path = Path(raw_path).resolve()
        dataset = load_synastry_predictive_dataset(path)
        for person in dataset.get("people") or []:
            person_id = str(person.get("person_id") or "").strip()
            if person_id in people_by_id:
                raise ValueError(f"Duplicate person_id across predictive datasets: {person_id}")
            people_by_id[person_id] = dict(person)
        for case in dataset.get("cases") or []:
            current_case_id = _normalize_text(case.get("case_id")).lower()
            if case_filter and current_case_id != case_filter:
                continue
            if not include_disabled and case.get("enabled") is False:
                continue
            case_copy = dict(case)
            case_copy["_dataset_path"] = str(path)
            cases.append(case_copy)

    return people_by_id, cases


def _load_logic_cases(
    fixture_paths: Sequence[str | Path],
    *,
    case_id: Optional[str],
) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()
    for raw_path in fixture_paths:
        path = Path(raw_path).resolve()
        fixture = load_logic_fixture(path)
        for case in fixture.get("cases") or []:
            current_case_id = _normalize_text(case.get("id") or case.get("case_id")).lower()
            if case_filter and current_case_id != case_filter:
                continue
            case_copy = dict(case)
            case_copy["_fixture_path"] = str(path)
            cases.append(case_copy)
    return cases


def _sorted_candidate_rows(scores: Dict[str, float]) -> List[Tuple[str, float]]:
    return sorted(scores.items(), key=lambda item: (-float(item[1]), str(item[0])))


def _random_expected_case_metrics(candidate_count: int) -> Dict[str, float]:
    reciprocal = sum(1.0 / rank for rank in range(1, candidate_count + 1)) / max(candidate_count, 1)
    return {
        "top1": 1.0 / max(candidate_count, 1),
        "top3": min(3, candidate_count) / max(candidate_count, 1),
        "mrr": reciprocal,
        "mean_rank": (candidate_count + 1) / 2.0,
    }


def _summarize_predictive_model_rows(rows: Sequence[Dict[str, Any]], *, label: str) -> Dict[str, Any]:
    ranks = [int(row["rank"]) for row in rows]
    reverse_deltas = [
        float(row["reverse_delta"])
        for row in rows
        if row.get("reverse_delta") is not None
    ]
    return {
        "label": label,
        "case_count": len(rows),
        "top1_hit_rate": round(sum(1 for rank in ranks if rank == 1) / max(len(ranks), 1), 4),
        "top3_hit_rate": round(sum(1 for rank in ranks if rank <= 3) / max(len(ranks), 1), 4),
        "mrr": round(sum(1.0 / rank for rank in ranks) / max(len(ranks), 1), 4),
        "mean_rank": round(_safe_mean([float(rank) for rank in ranks]), 4),
        "mean_abs_reverse_delta": round(_safe_mean(reverse_deltas), 4) if reverse_deltas else None,
    }


def _work_pair_id(anchor_person_id: Any, true_partner_id: Any) -> str:
    left = str(anchor_person_id or "").strip()
    right = str(true_partner_id or "").strip()
    return "__".join(sorted((left, right)))


def _pairwise_score_metrics(
    durable_scores: Sequence[float],
    breakdown_scores: Sequence[float],
) -> Dict[str, Optional[float]]:
    if not durable_scores or not breakdown_scores:
        return {
            "pairwise_comparison_count": 0,
            "pairwise_win_rate": None,
            "pairwise_tie_rate": None,
            "pairwise_loss_rate": None,
        }

    win_count = 0
    tie_count = 0
    comparison_count = len(durable_scores) * len(breakdown_scores)
    for durable_score in durable_scores:
        for breakdown_score in breakdown_scores:
            if durable_score > breakdown_score:
                win_count += 1
            elif durable_score == breakdown_score:
                tie_count += 1
    loss_count = comparison_count - win_count - tie_count
    return {
        "pairwise_comparison_count": comparison_count,
        "pairwise_win_rate": round(win_count / comparison_count, 4),
        "pairwise_tie_rate": round(tie_count / comparison_count, 4),
        "pairwise_loss_rate": round(loss_count / comparison_count, 4),
    }


def _format_metric(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f}"


def build_work_outcome_benchmark_suite(predictive_report: Dict[str, Any]) -> Dict[str, Any]:
    grouped_pairs: Dict[str, Dict[str, Any]] = {}
    for case in predictive_report.get("cases") or []:
        if _normalize_mode(case.get("mode")) != "work":
            continue
        outcome_label = _normalize_work_outcome_label(case.get("outcome_label"))
        if not outcome_label:
            continue

        pair_id = _work_pair_id(case.get("anchor_person_id"), case.get("true_partner_id"))
        pair_row = grouped_pairs.setdefault(
            pair_id,
            {
                "pair_id": pair_id,
                "anchor_person_id": case.get("anchor_person_id"),
                "true_partner_id": case.get("true_partner_id"),
                "person_ids": sorted(
                    {
                        str(case.get("anchor_person_id") or "").strip(),
                        str(case.get("true_partner_id") or "").strip(),
                    }
                ),
                "relationship_type": case.get("relationship_type"),
                "outcome_label": outcome_label,
                "end_state_label": case.get("end_state_label"),
                "dataset_path": case.get("dataset_path"),
                "directional_case_ids": [],
                "model_results": {},
            },
        )
        pair_row["directional_case_ids"].append(str(case.get("case_id") or ""))
        if not pair_row.get("relationship_type") and case.get("relationship_type"):
            pair_row["relationship_type"] = case.get("relationship_type")
        if not pair_row.get("end_state_label") and case.get("end_state_label"):
            pair_row["end_state_label"] = case.get("end_state_label")

        for model_id in WORK_OUTCOME_MODELS:
            case_model_result = dict((case.get("model_results") or {}).get(model_id) or {})
            if not case_model_result:
                continue
            model_pair_row = pair_row["model_results"].setdefault(
                model_id,
                {
                    "directional_case_ids": [],
                    "directional_true_scores": [],
                    "fallback_reverse_score": None,
                },
            )
            model_pair_row["directional_case_ids"].append(str(case.get("case_id") or ""))
            model_pair_row["directional_true_scores"].append(float(case_model_result.get("true_score") or 0.0))
            if model_pair_row.get("fallback_reverse_score") is None and case_model_result.get("reverse_score") is not None:
                model_pair_row["fallback_reverse_score"] = float(case_model_result.get("reverse_score") or 0.0)

    pair_rows: List[Dict[str, Any]] = []
    rows_by_model: Dict[str, List[Dict[str, Any]]] = {model_id: [] for model_id in WORK_OUTCOME_MODELS}
    for pair_id in sorted(grouped_pairs):
        grouped_pair = grouped_pairs[pair_id]
        pair_row: Dict[str, Any] = {
            "pair_id": grouped_pair["pair_id"],
            "person_ids": list(grouped_pair["person_ids"]),
            "relationship_type": grouped_pair.get("relationship_type"),
            "outcome_label": grouped_pair.get("outcome_label"),
            "end_state_label": grouped_pair.get("end_state_label"),
            "directional_case_ids": sorted(set(grouped_pair.get("directional_case_ids") or [])),
            "model_results": {},
        }
        for model_id in WORK_OUTCOME_MODELS:
            grouped_model_row = dict((grouped_pair.get("model_results") or {}).get(model_id) or {})
            directional_scores = [float(score) for score in grouped_model_row.get("directional_true_scores") or []]
            used_reverse_fallback = False
            if len(directional_scores) < 2 and grouped_model_row.get("fallback_reverse_score") is not None:
                reverse_score = float(grouped_model_row.get("fallback_reverse_score") or 0.0)
                if not directional_scores or reverse_score != directional_scores[0]:
                    directional_scores.append(reverse_score)
                else:
                    directional_scores.append(reverse_score)
                used_reverse_fallback = True
            pair_score = _safe_mean(directional_scores)
            pair_model_result = {
                "pair_score": round(pair_score, 4),
                "directional_score_count": len(directional_scores),
                "used_reverse_fallback": used_reverse_fallback,
                "directional_true_scores": [round(score, 4) for score in directional_scores],
            }
            pair_row["model_results"][model_id] = pair_model_result
            rows_by_model[model_id].append(
                {
                    "pair_id": pair_row["pair_id"],
                    "outcome_label": pair_row["outcome_label"],
                    "pair_score": pair_score,
                }
            )
        pair_rows.append(pair_row)

    model_summaries: Dict[str, Dict[str, Any]] = {}
    for model_id, rows in rows_by_model.items():
        if not rows:
            continue
        durable_rows = [row for row in rows if row.get("outcome_label") == "durable_success"]
        breakdown_rows = [row for row in rows if row.get("outcome_label") == "productive_then_breakdown"]
        durable_scores = [float(row["pair_score"]) for row in durable_rows]
        breakdown_scores = [float(row["pair_score"]) for row in breakdown_rows]
        pairwise_metrics = _pairwise_score_metrics(durable_scores, breakdown_scores)
        model_summaries[model_id] = {
            "label": MODEL_SPECS[model_id]["label"],
            "case_count": len(rows),
            "durable_pair_count": len(durable_rows),
            "breakdown_pair_count": len(breakdown_rows),
            "mean_durable_pair_score": round(_safe_mean(durable_scores), 4) if durable_scores else None,
            "median_durable_pair_score": round(_safe_median(durable_scores), 4) if durable_scores else None,
            "mean_breakdown_pair_score": round(_safe_mean(breakdown_scores), 4) if breakdown_scores else None,
            "median_breakdown_pair_score": round(_safe_median(breakdown_scores), 4) if breakdown_scores else None,
            "durable_minus_breakdown_mean": (
                round(_safe_mean(durable_scores) - _safe_mean(breakdown_scores), 4)
                if durable_scores and breakdown_scores
                else None
            ),
            "chance_pairwise_win_rate": 0.5,
            **pairwise_metrics,
        }

    durable_pair_count = sum(1 for row in pair_rows if row.get("outcome_label") == "durable_success")
    breakdown_pair_count = sum(1 for row in pair_rows if row.get("outcome_label") == "productive_then_breakdown")
    return {
        "pair_case_count": len(pair_rows),
        "durable_pair_count": durable_pair_count,
        "breakdown_pair_count": breakdown_pair_count,
        "pairs": pair_rows,
        "models": model_summaries,
    }


def _report_for_pair(
    *,
    model_id: str,
    bundle_a: Dict[str, Any],
    bundle_b: Dict[str, Any],
    chart_a: Dict[str, Any],
    chart_b: Dict[str, Any],
    options: Dict[str, Any],
    profile_a: Optional[str],
    profile_b: Optional[str],
    cache: Dict[Tuple[str, str, str, str, str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    spec = MODEL_SPECS[model_id]
    engine_id = str(spec["engine_id"])
    profile_a_key = profile_a or ""
    profile_b_key = profile_b or ""
    cache_key = (
        str(chart_a.get("id") or chart_a.get("label") or ""),
        str(chart_b.get("id") or chart_b.get("label") or ""),
        engine_id,
        profile_a_key,
        profile_b_key,
        json.dumps(options, sort_keys=True),
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)
    report = build_synastry_engine_report(
        bundle_a,
        bundle_b,
        chart_a,
        chart_b,
        options=options,
        engine_id=engine_id,
        profile_a=profile_a,
        profile_b=profile_b,
    )
    cache[cache_key] = copy.deepcopy(report)
    return report


def _predictive_case_profiles(
    case: Dict[str, Any],
    people_by_id: Dict[str, Dict[str, Any]],
) -> Tuple[Optional[str], Optional[str]]:
    anchor_person = people_by_id.get(str(case.get("anchor_person_id") or "").strip()) or {}
    true_partner = people_by_id.get(str(case.get("true_partner_id") or "").strip()) or {}
    profile_a = _normalize_profile(case.get("profile_a")) or _normalize_profile(
        anchor_person.get("profile_hint") or anchor_person.get("sex")
    )
    profile_b = _normalize_profile(case.get("profile_b")) or _normalize_profile(
        true_partner.get("profile_hint") or true_partner.get("sex")
    )
    return profile_a, profile_b


def _case_chart_meta_from_fixture(case: Dict[str, Any], side: str) -> Dict[str, Any]:
    meta = dict(case.get(f"chart_meta_{side}") or {})
    label = str(meta.get("label") or case.get(f"partner_{side}") or f"Chart {side.upper()}")
    meta.setdefault("id", str(meta.get("id") or label))
    meta.setdefault("label", label)
    meta.setdefault("effective_datetime", str(meta.get("effective_datetime") or "2026-04-19T10:00:00+00:00"))
    meta.setdefault("location", str(meta.get("location") or label))
    profile_hint = _normalize_profile(meta.get("profile_hint") or meta.get("sex"))
    if profile_hint:
        meta["profile_hint"] = profile_hint
    return meta


def run_predictive_benchmark_suite(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
    house_system_code: str = "R",
) -> Dict[str, Any]:
    predictive_paths = list(dataset_paths or DEFAULT_PREDICTIVE_DATASET_PATHS)
    people_by_id, cases = _load_predictive_registry(
        predictive_paths,
        case_id=case_id,
        include_disabled=include_disabled,
    )
    chart_cache: Dict[Tuple[str, str, bool, bool], Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    report_cache: Dict[Tuple[str, str, str, str, str, str], Dict[str, Any]] = {}
    case_rows: List[Dict[str, Any]] = []
    skipped_cases: List[Dict[str, Any]] = []
    model_rows: Dict[str, List[Dict[str, Any]]] = {}
    model_rows_by_mode: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    for case in cases:
        mode = _normalize_mode(case.get("mode"))
        options = _merge_options(case.get("options"))
        include_modern = bool(options.get("include_modern"))
        include_chiron = bool(options.get("include_chiron"))
        anchor_id = str(case.get("anchor_person_id") or "").strip()
        anchor_person = people_by_id.get(anchor_id)
        if anchor_person is None:
            skipped_cases.append(
                {"case_id": case.get("case_id"), "reason": f"Anchor is missing from registry: {anchor_id}"}
            )
            continue

        try:
            anchor_bundle, anchor_chart = _resolve_person_entry(
                anchor_person,
                house_system_code=house_system_code,
                include_modern=include_modern,
                include_chiron=include_chiron,
                cache=chart_cache,
            )
        except Exception as exc:
            skipped_cases.append({"case_id": case.get("case_id"), "reason": str(exc)})
            continue

        profile_a, default_profile_b = _predictive_case_profiles(case, people_by_id)
        model_ids = PREDICTIVE_MODELS_BY_MODE.get(mode) or ()
        candidate_ids = [str(item or "").strip() for item in case.get("candidate_ids") or []]
        true_partner_id = str(case.get("true_partner_id") or "").strip()
        candidate_rows: Dict[str, Dict[str, Any]] = {}

        failed_resolution = None
        for candidate_id in candidate_ids:
            candidate_person = people_by_id.get(candidate_id)
            if candidate_person is None:
                failed_resolution = f"Candidate is missing from registry: {candidate_id}"
                break
            try:
                candidate_bundle, candidate_chart = _resolve_person_entry(
                    candidate_person,
                    house_system_code=house_system_code,
                    include_modern=include_modern,
                    include_chiron=include_chiron,
                    cache=chart_cache,
                )
            except Exception as exc:
                failed_resolution = str(exc)
                break
            candidate_rows[candidate_id] = {
                "bundle": candidate_bundle,
                "chart": candidate_chart,
                "profile_b": _normalize_profile(
                    case.get("profile_b") if candidate_id == true_partner_id else candidate_person.get("profile_hint") or candidate_person.get("sex")
                ) or default_profile_b,
            }

        if failed_resolution:
            skipped_cases.append({"case_id": case.get("case_id"), "reason": failed_resolution})
            continue

        case_summary: Dict[str, Any] = {
            "case_id": case.get("case_id"),
            "label": case.get("label") or case.get("relationship_type") or case.get("case_id"),
            "mode": mode,
            "relationship_type": case.get("relationship_type"),
            "outcome_label": _normalize_work_outcome_label(case.get("outcome_label")),
            "end_state_label": case.get("end_state_label"),
            "anchor_person_id": anchor_id,
            "true_partner_id": true_partner_id,
            "candidate_count": len(candidate_ids),
            "dataset_path": case.get("_dataset_path"),
            "model_results": {},
        }

        for model_id in model_ids:
            candidate_scores: Dict[str, float] = {}
            reverse_score = None
            for candidate_id in candidate_ids:
                candidate_row = candidate_rows[candidate_id]
                report = _report_for_pair(
                    model_id=model_id,
                    bundle_a=anchor_bundle,
                    bundle_b=candidate_row["bundle"],
                    chart_a=anchor_chart,
                    chart_b=candidate_row["chart"],
                    options=options,
                    profile_a=profile_a if "union_dynamics" in model_id else None,
                    profile_b=candidate_row["profile_b"] if "union_dynamics" in model_id else None,
                    cache=report_cache,
                )
                candidate_scores[candidate_id] = _score_from_report(report, model_id)
                if candidate_id == true_partner_id:
                    reverse_report = _report_for_pair(
                        model_id=model_id,
                        bundle_a=candidate_row["bundle"],
                        bundle_b=anchor_bundle,
                        chart_a=candidate_row["chart"],
                        chart_b=anchor_chart,
                        options=options,
                        profile_a=candidate_row["profile_b"] if "union_dynamics" in model_id else None,
                        profile_b=profile_a if "union_dynamics" in model_id else None,
                        cache=report_cache,
                    )
                    reverse_score = _score_from_report(reverse_report, model_id)

            ordered = _sorted_candidate_rows(candidate_scores)
            rank = next(
                index
                for index, (candidate_id, _score) in enumerate(ordered, start=1)
                if candidate_id == true_partner_id
            )
            top_candidate_id = ordered[0][0] if ordered else None
            true_score = float(candidate_scores.get(true_partner_id) or 0.0)
            case_result = {
                "case_id": case.get("case_id"),
                "mode": mode,
                "rank": rank,
                "candidate_count": len(candidate_ids),
                "true_partner_id": true_partner_id,
                "top_candidate_id": top_candidate_id,
                "true_score": true_score,
                "reverse_score": reverse_score,
                "reverse_delta": (
                    round(abs(true_score - float(reverse_score)), 4)
                    if reverse_score is not None
                    else None
                ),
                "ordered_candidates": [
                    {"candidate_id": candidate_id, "score": round(float(score), 4)}
                    for candidate_id, score in ordered
                ],
            }
            case_summary["model_results"][model_id] = case_result
            model_rows.setdefault(model_id, []).append(case_result)
            model_rows_by_mode.setdefault(mode, {}).setdefault(model_id, []).append(case_result)

        case_rows.append(case_summary)

    model_summaries: Dict[str, Dict[str, Any]] = {}
    for model_id, rows in model_rows.items():
        model_summaries[model_id] = _summarize_predictive_model_rows(
            rows,
            label=MODEL_SPECS[model_id]["label"],
        )

    model_summaries_by_mode: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for mode, rows_by_model in model_rows_by_mode.items():
        model_summaries_by_mode[mode] = {}
        for model_id, rows in rows_by_model.items():
            model_summaries_by_mode[mode][model_id] = _summarize_predictive_model_rows(
                rows,
                label=MODEL_SPECS[model_id]["label"],
            )

    random_rows = [row for row in case_rows if int(row.get("candidate_count") or 0) > 0]
    if random_rows:
        random_metrics = [_random_expected_case_metrics(int(row["candidate_count"])) for row in random_rows]
        model_summaries["random_expected"] = {
            "label": "Random expected baseline",
            "case_count": len(random_rows),
            "top1_hit_rate": round(_safe_mean([item["top1"] for item in random_metrics]), 4),
            "top3_hit_rate": round(_safe_mean([item["top3"] for item in random_metrics]), 4),
            "mrr": round(_safe_mean([item["mrr"] for item in random_metrics]), 4),
            "mean_rank": round(_safe_mean([item["mean_rank"] for item in random_metrics]), 4),
            "mean_abs_reverse_delta": None,
        }

    for mode in sorted({str(case.get("mode") or "") for case in case_rows}):
        mode_rows = [row for row in case_rows if str(row.get("mode") or "") == mode]
        if not mode_rows:
            continue
        random_metrics = [_random_expected_case_metrics(int(row["candidate_count"])) for row in mode_rows]
        model_summaries_by_mode.setdefault(mode, {})["random_expected"] = {
            "label": "Random expected baseline",
            "case_count": len(mode_rows),
            "top1_hit_rate": round(_safe_mean([item["top1"] for item in random_metrics]), 4),
            "top3_hit_rate": round(_safe_mean([item["top3"] for item in random_metrics]), 4),
            "mrr": round(_safe_mean([item["mrr"] for item in random_metrics]), 4),
            "mean_rank": round(_safe_mean([item["mean_rank"] for item in random_metrics]), 4),
            "mean_abs_reverse_delta": None,
        }

    case_counts_by_mode: Dict[str, int] = {}
    for case in case_rows:
        current_mode = str(case.get("mode") or "")
        case_counts_by_mode[current_mode] = case_counts_by_mode.get(current_mode, 0) + 1

    return {
        "dataset_paths": [str(Path(path).resolve()) for path in predictive_paths],
        "case_count": len(case_rows),
        "skipped_case_count": len(skipped_cases),
        "case_counts_by_mode": case_counts_by_mode,
        "cases": case_rows,
        "skipped_cases": skipped_cases,
        "models": model_summaries,
        "models_by_mode": model_summaries_by_mode,
    }


def run_logic_benchmark_suite(
    fixture_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    logic_paths = list(fixture_paths or DEFAULT_LOGIC_FIXTURE_PATHS)
    cases = _load_logic_cases(logic_paths, case_id=case_id)
    rows_by_model: Dict[str, List[Dict[str, Any]]] = {}
    case_rows: List[Dict[str, Any]] = []

    for case in cases:
        chart_data_a = copy.deepcopy(case.get("chart_data_a") or {})
        chart_data_b = copy.deepcopy(case.get("chart_data_b") or {})
        chart_meta_a = _case_chart_meta_from_fixture(case, "a")
        chart_meta_b = _case_chart_meta_from_fixture(case, "b")
        options = _merge_options(case.get("options"))

        bundle_a = {"chart_data": chart_data_a, "meta": {"label": chart_meta_a.get("label")}}
        bundle_b = {"chart_data": chart_data_b, "meta": {"label": chart_meta_b.get("label")}}

        profile_a = _normalize_profile(case.get("profile_a") or chart_meta_a.get("profile_hint") or chart_meta_a.get("sex"))
        profile_b = _normalize_profile(case.get("profile_b") or chart_meta_b.get("profile_hint") or chart_meta_b.get("sex"))

        result_row: Dict[str, Any] = {
            "case_id": case.get("id") or case.get("case_id"),
            "label": f"{chart_meta_a.get('label')} x {chart_meta_b.get('label')}",
            "models": {},
        }

        for model_id in LOGIC_MODELS:
            forward = build_synastry_engine_report(
                bundle_a,
                bundle_b,
                chart_meta_a,
                chart_meta_b,
                options=options,
                engine_id=MODEL_SPECS[model_id]["engine_id"],
                profile_a=profile_a if "union_dynamics" in model_id else None,
                profile_b=profile_b if "union_dynamics" in model_id else None,
            )
            reverse = build_synastry_engine_report(
                bundle_b,
                bundle_a,
                chart_meta_b,
                chart_meta_a,
                options=options,
                engine_id=MODEL_SPECS[model_id]["engine_id"],
                profile_a=profile_b if "union_dynamics" in model_id else None,
                profile_b=profile_a if "union_dynamics" in model_id else None,
            )
            forward_score = _score_from_report(forward, model_id)
            reverse_score = _score_from_report(reverse, model_id)
            details = {
                "case_id": result_row["case_id"],
                "forward_score": round(forward_score, 4),
                "reverse_score": round(reverse_score, 4),
                "abs_reverse_delta": round(abs(forward_score - reverse_score), 4),
            }
            if MODEL_SPECS[model_id]["engine_id"] != "memo":
                details["theme_total"] = round(float((forward.get("summary") or {}).get("theme_total") or 0.0), 4)
                details["aspect_total"] = round(float((forward.get("summary") or {}).get("aspect_total") or 0.0), 4)
                details["burden_total"] = round(float((forward.get("summary") or {}).get("burden_total") or 0.0), 4)
            result_row["models"][model_id] = details
            rows_by_model.setdefault(model_id, []).append(details)

        case_rows.append(result_row)

    model_summaries: Dict[str, Dict[str, Any]] = {}
    for model_id, rows in rows_by_model.items():
        forward_scores = [float(row["forward_score"]) for row in rows]
        reverse_deltas = [float(row["abs_reverse_delta"]) for row in rows]
        summary = {
            "label": MODEL_SPECS[model_id]["label"],
            "case_count": len(rows),
            "mean_forward_score": round(_safe_mean(forward_scores), 4),
            "median_forward_score": round(_safe_median(forward_scores), 4),
            "mean_abs_reverse_delta": round(_safe_mean(reverse_deltas), 4),
            "max_abs_reverse_delta": round(max(reverse_deltas), 4) if reverse_deltas else 0.0,
        }
        if MODEL_SPECS[model_id]["engine_id"] != "memo":
            summary["mean_theme_total"] = round(_safe_mean([float(row["theme_total"]) for row in rows]), 4)
            summary["mean_aspect_total"] = round(_safe_mean([float(row["aspect_total"]) for row in rows]), 4)
            summary["mean_burden_total"] = round(_safe_mean([float(row["burden_total"]) for row in rows]), 4)
        model_summaries[model_id] = summary

    return {
        "fixture_paths": [str(Path(path).resolve()) for path in logic_paths],
        "case_count": len(case_rows),
        "cases": case_rows,
        "models": model_summaries,
    }


def run_synastry_benchmarks(
    predictive_dataset_paths: Optional[Sequence[str | Path]] = None,
    logic_fixture_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
    house_system_code: str = "R",
) -> Dict[str, Any]:
    validation = validate_synastry_benchmark_datasets(
        predictive_dataset_paths=predictive_dataset_paths,
        logic_fixture_paths=logic_fixture_paths,
    )
    predictive = run_predictive_benchmark_suite(
        predictive_dataset_paths,
        case_id=case_id,
        include_disabled=include_disabled,
        house_system_code=house_system_code,
    )
    work_outcomes = build_work_outcome_benchmark_suite(predictive)
    logic = run_logic_benchmark_suite(logic_fixture_paths, case_id=case_id)
    return {
        "validation": validation,
        "predictive": predictive,
        "work_outcomes": work_outcomes,
        "logic": logic,
    }


def render_markdown_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    validation = report.get("validation") or {}
    predictive = report.get("predictive") or {}
    work_outcomes = report.get("work_outcomes") or {}
    logic = report.get("logic") or {}

    lines.append("# Synastry Benchmark Report")
    lines.append("")
    lines.append(f"- Predictive benchmark cases: {int(predictive.get('case_count') or 0)}")
    lines.append(f"- Work outcome pairs: {int(work_outcomes.get('pair_case_count') or 0)}")
    lines.append(f"- Logic benchmark cases: {int(logic.get('case_count') or 0)}")
    lines.append(f"- Predictive skipped cases: {int(predictive.get('skipped_case_count') or 0)}")
    lines.append("")
    lines.append("## Validation")
    lines.append("")
    lines.append(f"- Predictive people: {int(validation.get('predictive_people_count') or 0)}")
    lines.append(f"- Predictive cases: {int(validation.get('predictive_case_count') or 0)}")
    lines.append(f"- Logic fixture cases: {int(validation.get('logic_case_count') or 0)}")
    lines.append("")

    lines.append("## Predictive Ranking")
    lines.append("")
    case_counts_by_mode = predictive.get("case_counts_by_mode") or {}
    models_by_mode = predictive.get("models_by_mode") or {}
    mode_labels = {"overall": "Overall", "union": "Union", "work": "Work"}
    for mode in ("overall", "union", "work"):
        mode_summaries = models_by_mode.get(mode) or {}
        if not mode_summaries:
            continue
        lines.append(f"### {mode_labels.get(mode, mode.title())}")
        lines.append("")
        lines.append(f"- Cases: {int(case_counts_by_mode.get(mode) or 0)}")
        lines.append("")
        lines.append("| Model | Cases | Top-1 | Top-3 | MRR | Mean Rank |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        ordered_model_ids = list(PREDICTIVE_MODELS_BY_MODE.get(mode) or ())
        ordered_model_ids.append("random_expected")
        for model_id in ordered_model_ids:
            summary = mode_summaries.get(model_id)
            if not summary:
                continue
            lines.append(
                f"| `{model_id}` | {int(summary.get('case_count') or 0)} | "
                f"{float(summary.get('top1_hit_rate') or 0.0):.4f} | "
                f"{float(summary.get('top3_hit_rate') or 0.0):.4f} | "
                f"{float(summary.get('mrr') or 0.0):.4f} | "
                f"{float(summary.get('mean_rank') or 0.0):.4f} |"
            )
        lines.append("")

    if work_outcomes.get("models"):
        lines.append("## Work Outcome Separation")
        lines.append("")
        lines.append(f"- Pair cases: {int(work_outcomes.get('pair_case_count') or 0)}")
        lines.append(f"- Durable-success pairs: {int(work_outcomes.get('durable_pair_count') or 0)}")
        lines.append(f"- Productive-then-breakdown pairs: {int(work_outcomes.get('breakdown_pair_count') or 0)}")
        lines.append("- Chance pairwise win rate: `0.5000`")
        lines.append("")
        lines.append("| Model | Pairs | Durable | Breakdown | Mean Durable | Mean Breakdown | Mean Gap | Pairwise Win | Tie Rate |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for model_id in WORK_OUTCOME_MODELS:
            summary = (work_outcomes.get("models") or {}).get(model_id)
            if not summary:
                continue
            lines.append(
                f"| `{model_id}` | {int(summary.get('case_count') or 0)} | "
                f"{int(summary.get('durable_pair_count') or 0)} | "
                f"{int(summary.get('breakdown_pair_count') or 0)} | "
                f"{_format_metric(summary.get('mean_durable_pair_score'))} | "
                f"{_format_metric(summary.get('mean_breakdown_pair_score'))} | "
                f"{_format_metric(summary.get('durable_minus_breakdown_mean'))} | "
                f"{_format_metric(summary.get('pairwise_win_rate'))} | "
                f"{_format_metric(summary.get('pairwise_tie_rate'))} |"
            )
        lines.append("")

    lines.append("## Logic Stability")
    lines.append("")
    lines.append("| Model | Cases | Mean Forward | Median Forward | Mean Abs Reverse Delta | Max Abs Reverse Delta |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for model_id, summary in sorted((logic.get("models") or {}).items()):
        lines.append(
            f"| `{model_id}` | {int(summary.get('case_count') or 0)} | "
            f"{float(summary.get('mean_forward_score') or 0.0):.4f} | "
            f"{float(summary.get('median_forward_score') or 0.0):.4f} | "
            f"{float(summary.get('mean_abs_reverse_delta') or 0.0):.4f} | "
            f"{float(summary.get('max_abs_reverse_delta') or 0.0):.4f} |"
        )
    lines.append("")

    if predictive.get("cases"):
        lines.append("## Predictive Cases")
        lines.append("")
        for case in predictive.get("cases") or []:
            line = (
                f"- `{case.get('case_id')}` ({case.get('mode')}): true partner `{case.get('true_partner_id')}`, "
                f"{int(case.get('candidate_count') or 0)} candidates"
            )
            if case.get("outcome_label"):
                line += f", outcome `{case.get('outcome_label')}`"
            lines.append(line)

    if work_outcomes.get("pairs"):
        lines.append("")
        lines.append("## Work Outcome Pairs")
        lines.append("")
        for pair in work_outcomes.get("pairs") or []:
            person_ids = " / ".join(pair.get("person_ids") or [])
            lines.append(
                f"- `{pair.get('pair_id')}`: {person_ids} -> `{pair.get('outcome_label')}`"
            )

    if predictive.get("skipped_cases"):
        lines.append("")
        lines.append("## Skipped Cases")
        lines.append("")
        for case in predictive.get("skipped_cases") or []:
            lines.append(f"- `{case.get('case_id')}`: {case.get('reason')}")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synastry logic and predictive benchmarks.")
    parser.add_argument(
        "--predictive-dataset",
        action="append",
        dest="predictive_datasets",
        default=None,
        help="Path to a predictive pair dataset JSON file. Can be passed multiple times.",
    )
    parser.add_argument(
        "--logic-fixture",
        action="append",
        dest="logic_fixtures",
        default=None,
        help="Path to a logic benchmark fixture JSON file. Can be passed multiple times.",
    )
    parser.add_argument("--case-id", default=None, help="Run a single case id across both tracks when present.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled predictive cases.")
    parser.add_argument("--house-system-code", default="R", help="Pinned house system code for raw and bank chart casting.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    args = parser.parse_args()

    report = run_synastry_benchmarks(
        predictive_dataset_paths=args.predictive_datasets,
        logic_fixture_paths=args.logic_fixtures,
        case_id=args.case_id,
        include_disabled=bool(args.include_disabled),
        house_system_code=str(args.house_system_code or "R"),
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
