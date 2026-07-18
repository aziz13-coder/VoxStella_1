from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from benchmarks.astrocartography.baselines import compute_case_baselines
from benchmarks.astrocartography.validation import (
    DEFAULT_HOLDOUT_FRACTION,
    DEFAULT_SPLIT_SEED,
    case_weight,
    clustered_bootstrap_ci,
    comparison_credit,
    control_weight,
    event_score_orientation,
    normalize_outcome_polarity,
    normalize_score_polarity,
    person_group_id,
    select_validation_split,
    weighted_mean,
)


DEFAULT_BENCHMARK_DIR = Path(__file__).resolve().parent / "benchmarks" / "astrocartography"
DEFAULT_SPECULATION_DATASET = DEFAULT_BENCHMARK_DIR / "speculation_cases.jsonl"
DEFAULT_HEALTH_RISK_DATASET = DEFAULT_BENCHMARK_DIR / "health_risk_cases.jsonl"
SUPPORTED_MODES = {"natal_only", "event_transit_overlay"}
SUPPORTED_VALIDATION_SPLITS = {"all", "train", "holdout"}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _read_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        yield line_number, payload


def load_benchmark_cases(
    dataset_paths: Sequence[str | Path],
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cases: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()

    for raw_path in dataset_paths:
        path = Path(raw_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Benchmark dataset not found: {path}")
        for line_number, payload in _read_jsonl(path):
            current_case_id = _normalize_text(payload.get("case_id"))
            if case_filter and current_case_id.lower() != case_filter:
                continue
            if not include_disabled and not bool(payload.get("enabled")):
                skipped.append(
                    {
                        "dataset": str(path),
                        "line_number": line_number,
                        "case_id": current_case_id or f"line-{line_number}",
                        "reason": "disabled",
                    }
                )
                continue
            payload = dict(payload)
            payload["_dataset_path"] = str(path)
            payload["_line_number"] = line_number
            cases.append(payload)
    return cases, skipped


def _location_label(raw: Any) -> str:
    if isinstance(raw, str):
        return _normalize_text(raw)
    if isinstance(raw, dict):
        for key in ("label", "query", "name", "display_name", "place"):
            label = _normalize_text(raw.get(key))
            if label:
                return label
    return ""


def _resolve_city_payload(raw: Any, *, allow_live_geocode: bool = False) -> Dict[str, Any]:
    from astrocartography_city_catalog import search_city_catalog
    from horary_engine.services.geolocation import search_live_location_candidates

    if isinstance(raw, dict):
        label = _location_label(raw)
        lat = raw.get("latitude")
        lon = raw.get("longitude")
        if (lat is None) != (lon is None):
            raise ValueError(f"Explicit location coordinates require both latitude and longitude: {raw!r}")
        if label and lat is not None and lon is not None:
            latitude = float(lat)
            longitude = float(lon)
            if not math.isfinite(latitude) or not -90.0 <= latitude <= 90.0:
                raise ValueError(f"Invalid latitude for {label}: {lat!r}")
            if not math.isfinite(longitude) or not -180.0 <= longitude <= 180.0:
                raise ValueError(f"Invalid longitude for {label}: {lon!r}")
            return {
                "label": label,
                "query": label,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": _normalize_text(raw.get("timezone")),
                "country_code": _normalize_text(raw.get("country_code")).upper(),
                "country_name": _normalize_text(raw.get("country_name")),
                "admin1_code": _normalize_text(raw.get("admin1_code")),
                "population": int(raw.get("population") or 0),
                "feature_code": _normalize_text(raw.get("feature_code")) or "MANUAL",
                "resolution_source": "explicit_coordinates",
            }

    label = _location_label(raw)
    if not label:
        raise ValueError(f"Location label is required: {raw!r}")

    catalog_candidates = search_city_catalog(query=label, limit=6, resolution="ultra")
    if catalog_candidates:
        best = dict(catalog_candidates[0])
        best["resolution_source"] = "catalog"
        return best

    if allow_live_geocode:
        live_candidates = search_live_location_candidates(label, limit=6)
        if live_candidates:
            best = dict(live_candidates[0])
            best["resolution_source"] = "offline_catalog_candidate"
            return best

    raise ValueError(f"Could not resolve benchmark location: {label}")


def _control_blocks_for_case(case: Dict[str, Any]) -> Tuple[List[Any], Dict[str, Any]]:
    design = case.get("control_design")
    if design is not None and not isinstance(design, dict):
        raise ValueError("control_design must be an object when provided")
    design = dict(design or {})

    frozen_controls = case.get("frozen_controls")
    if frozen_controls is not None and not isinstance(frozen_controls, list):
        raise ValueError("frozen_controls must be a list when provided")
    if isinstance(frozen_controls, list) and frozen_controls:
        controls = list(frozen_controls)
        control_source = "frozen_controls"
        frozen = True
    else:
        raw_controls = case.get("controls") or []
        if not isinstance(raw_controls, list):
            raise ValueError("controls must be a list")
        controls = list(raw_controls)
        control_source = "controls"
        frozen = bool(design.get("frozen") or case.get("controls_frozen"))

    if not controls:
        raise ValueError("At least one control location is required")
    exposure_matched = bool(
        design.get("exposure_matched")
        or case.get("exposure_matched_controls")
    )
    selection = _normalize_text(
        design.get("selection")
        or case.get("control_selection")
    )
    same_person = bool(
        design.get("same_person")
        or "same_person" in selection.lower()
        or str(case.get("benchmark_type") or "").startswith("within_person")
    )
    return controls, {
        "source": control_source,
        "frozen": frozen,
        "exposure_matched": exposure_matched,
        "same_person": same_person,
        "selection": selection,
        "control_set_id": _normalize_text(
            design.get("control_set_id") or case.get("control_set_id")
        ),
        "control_set_version": _normalize_text(
            design.get("version") or case.get("control_set_version")
        ),
    }


def _validate_control_design(
    design: Dict[str, Any],
    *,
    require_frozen_controls: bool,
    require_exposure_matched_controls: bool,
) -> None:
    if require_frozen_controls and not bool(design.get("frozen")):
        raise ValueError("This run requires a frozen control set")
    if require_exposure_matched_controls and not bool(design.get("exposure_matched")):
        raise ValueError("This run requires exposure-matched controls")


def _require_block(case: Dict[str, Any], key: str) -> Dict[str, Any]:
    block = case.get(key)
    if not isinstance(block, dict):
        raise ValueError(f"Case {case.get('case_id')}: missing {key} block")
    return block


def _build_birth_datetime_iso(birth: Dict[str, Any]) -> str:
    birth_date = _normalize_text(birth.get("date"))
    birth_time = _normalize_text(birth.get("time"))
    if not birth_date or not birth_time:
        raise ValueError("Birth date and birth time are required")
    return f"{birth_date}T{birth_time}:00"


def _build_event_datetime_iso(event: Dict[str, Any]) -> str:
    event_date = _normalize_text(event.get("date"))
    event_time = _normalize_text(event.get("time")) or "12:00"
    if not event_date:
        raise ValueError("Event date is required")
    return f"{event_date}T{event_time}:00"


def _build_case_transit_context(
    case: Dict[str, Any],
    *,
    natal_meta: Dict[str, Any],
    event_city: Dict[str, Any],
) -> Tuple[str, Optional[str], Optional[str], Optional[float], Optional[float]]:
    event = _require_block(case, "event")
    transit_context = case.get("transit_context")
    if transit_context is not None and not isinstance(transit_context, dict):
        raise ValueError("transit_context must be an object when provided")
    transit_context = transit_context or {}
    location_strategy = _normalize_text(transit_context.get("location_strategy")).lower() or "natal"
    dt_iso = _build_event_datetime_iso(event)

    if location_strategy == "event":
        return (
            dt_iso,
            str(event_city.get("label") or event_city.get("query") or ""),
            _normalize_text(event_city.get("timezone")),
            float(event_city["latitude"]),
            float(event_city["longitude"]),
        )
    if location_strategy == "explicit":
        explicit_location = _normalize_text(transit_context.get("location") or transit_context.get("label"))
        if not explicit_location:
            raise ValueError("transit_context.location is required for explicit strategy")
        latitude = transit_context.get("latitude")
        longitude = transit_context.get("longitude")
        if (latitude is None) != (longitude is None):
            raise ValueError("transit_context explicit coordinates require both latitude and longitude")
        return (
            dt_iso,
            explicit_location,
            _normalize_text(transit_context.get("timezone")),
            float(latitude) if latitude is not None else None,
            float(longitude) if longitude is not None else None,
        )
    if location_strategy != "natal":
        raise ValueError(f"Unsupported transit_context.location_strategy: {location_strategy}")

    return (
        dt_iso,
        _normalize_text(transit_context.get("location")) or _normalize_text(natal_meta.get("location")),
        _normalize_text(transit_context.get("timezone")) or _normalize_text(natal_meta.get("timezone")),
        float(natal_meta["latitude"]) if natal_meta.get("latitude") is not None else None,
        float(natal_meta["longitude"]) if natal_meta.get("longitude") is not None else None,
    )


def _build_case_context(case: Dict[str, Any], *, mode: str, allow_live_geocode: bool = False) -> Dict[str, Any]:
    from astro_clock_api import _compute_chart_bundle_for
    from astrocartography_service import build_astrocartography_lines
    from astrocartography_goal_models import get_goal_model

    goal_id = _normalize_text(case.get("goal_id")).lower()
    if not goal_id:
        raise ValueError("goal_id is required")
    get_goal_model(goal_id)

    birth = _require_block(case, "birth")
    birth_place = _normalize_text(birth.get("place"))
    if not birth_place:
        raise ValueError("Birth place is required")
    birth_timezone = _normalize_text(birth.get("timezone")) or None
    birth_latitude = birth.get("latitude")
    birth_longitude = birth.get("longitude")
    if (birth_latitude is None) != (birth_longitude is None):
        raise ValueError("Birth coordinates require both latitude and longitude")
    natal_bundle = _compute_chart_bundle_for(
        _build_birth_datetime_iso(birth),
        birth_place,
        birth_timezone,
        latitude=float(birth_latitude) if birth_latitude is not None else None,
        longitude=float(birth_longitude) if birth_longitude is not None else None,
    )
    natal_meta = natal_bundle.get("meta") or {}
    natal_timestamp = _normalize_text(natal_meta.get("timestamp"))
    if not natal_timestamp:
        raise ValueError("Failed to compute natal timestamp")

    natal_lines_payload = build_astrocartography_lines(natal_timestamp)
    context: Dict[str, Any] = {
        "goal_id": goal_id,
        "natal_bundle": natal_bundle,
        "natal_meta": natal_meta,
        "natal_lines": natal_lines_payload.get("lines") or [],
        "transit_meta": None,
        "transit_lines": None,
    }
    if mode == "natal_only":
        return context

    event = _require_block(case, "event")
    event_city = _resolve_city_payload(event.get("location"), allow_live_geocode=allow_live_geocode)
    (
        dt_iso,
        transit_location,
        transit_timezone,
        transit_latitude,
        transit_longitude,
    ) = _build_case_transit_context(case, natal_meta=natal_meta, event_city=event_city)
    transit_bundle = _compute_chart_bundle_for(
        dt_iso,
        transit_location,
        transit_timezone or None,
        latitude=transit_latitude,
        longitude=transit_longitude,
    )
    transit_meta = transit_bundle.get("meta") or {}
    transit_timestamp = _normalize_text(transit_meta.get("timestamp"))
    if not transit_timestamp:
        raise ValueError("Failed to compute transit timestamp")
    transit_lines_payload = build_astrocartography_lines(transit_timestamp)
    context["transit_meta"] = transit_meta
    context["transit_lines"] = transit_lines_payload.get("lines") or []
    context["event_city_for_transit"] = event_city
    return context


def _score_city_for_case(
    city: Dict[str, Any],
    *,
    goal_id: str,
    natal_timestamp: str,
    natal_lines: Sequence[Dict[str, Any]],
    transit_lines: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    from astro_clock_api import _compute_chart_bundle_for
    from astrocartography_atlas_engine import _score_candidate
    from astrocartography_goal_engine import extract_relocation_features, get_goal_score_polarity

    latitude = float(city["latitude"])
    longitude = float(city["longitude"])
    relocation_bundle = _compute_chart_bundle_for(
        str(natal_timestamp),
        str(city.get("label") or city.get("query") or ""),
        str(city.get("timezone") or "") or None,
        latitude=latitude,
        longitude=longitude,
        include_modern=True,
        include_chiron=True,
    )
    relocation_features = extract_relocation_features(relocation_bundle.get("chart_data") or {})
    scored = _score_candidate(
        city,
        goal_id=goal_id,
        natal_lines=natal_lines,
        transit_lines=transit_lines,
        relocation_features=relocation_features,
    )
    baselines = compute_case_baselines(
        goal_id,
        natal_rows=((scored.get("natal") or {}).get("reading") or {}).get("nearest_lines") or [],
        natal_crossings=((scored.get("natal") or {}).get("crossings") or []),
        relocation=relocation_features,
        transit_rows=(((scored.get("transit") or {}).get("reading") or {}).get("nearest_lines") or []),
        transit_crossings=((scored.get("transit") or {}).get("crossings") or []),
    )
    models = {
        "product_model": {
            "id": goal_id,
            "label": "Product Model",
            "raw_score": float(((scored.get("location_score") or {}).get("raw_score")) or 0.0),
            "score": int(((scored.get("location_score") or {}).get("score")) or 0),
            "summary": str(((scored.get("location_score") or {}).get("headline")) or ""),
            "score_polarity": normalize_score_polarity(
                ((scored.get("location_score") or {}).get("goal") or {}).get("score_polarity")
                or get_goal_score_polarity(goal_id),
                goal_id=goal_id,
            ),
            "comparator_kind": "product_model",
            "independent_from_product_model": False,
        },
        **baselines,
    }
    return {
        "city": {
            "label": str(city.get("label") or city.get("query") or ""),
            "query": str(city.get("query") or city.get("label") or ""),
            "latitude": latitude,
            "longitude": longitude,
            "timezone": str(city.get("timezone") or ""),
            "country_code": str(city.get("country_code") or ""),
            "country_name": str(city.get("country_name") or ""),
            "resolution_source": str(city.get("resolution_source") or ""),
        },
        "product": scored,
        "models": models,
    }


def _comparator_rank_value(item: Dict[str, Any], comparator_id: str) -> float:
    payload = ((item.get("models") or {}).get(comparator_id) or {})
    if payload.get("raw_score") is not None:
        return float(payload.get("raw_score") or 0.0)
    return float(payload.get("score") or 0.0)


def rank_case_scores(
    scored_candidates: Sequence[Dict[str, Any]],
    *,
    outcome_polarity: str = "positive",
    goal_id: str = "",
    tie_tolerance: float = 1e-9,
) -> Dict[str, Dict[str, Any]]:
    normalized_outcome = normalize_outcome_polarity(outcome_polarity)
    comparator_ids = sorted(
        {
            comparator_id
            for item in scored_candidates
            for comparator_id in (item.get("models") or {}).keys()
        }
    )
    results: Dict[str, Dict[str, Any]] = {}

    for comparator_id in comparator_ids:
        eligible = [item for item in scored_candidates if comparator_id in (item.get("models") or {})]
        if not eligible:
            continue
        event_item = next((item for item in eligible if item.get("role") == "event"), None)
        if event_item is None:
            continue
        event_model = ((event_item.get("models") or {}).get(comparator_id) or {})
        score_polarity = normalize_score_polarity(
            event_model.get("score_polarity"),
            goal_id=goal_id if comparator_id == "product_model" else "",
        )
        orientation = event_score_orientation(
            normalized_outcome,
            score_polarity,
            goal_id=goal_id if comparator_id == "product_model" else "",
        )
        ranked = sorted(
            eligible,
            key=lambda item: (
                -(_comparator_rank_value(item, comparator_id) * orientation),
                str(((item.get("city") or {}).get("label")) or ""),
            ),
        )
        event_score = _comparator_rank_value(event_item, comparator_id)
        scores_against_event = [
            comparison_credit(
                event_score,
                _comparator_rank_value(item, comparator_id),
                orientation=orientation,
                tolerance=tie_tolerance,
            )
            for item in ranked
            if item is not event_item
        ]
        strictly_better_count = sum(1 for credit in scores_against_event if credit == 0.0)
        tied_peer_count = sum(1 for credit in scores_against_event if credit == 0.5)
        event_rank_min = strictly_better_count + 1
        event_rank_max = event_rank_min + tied_peer_count
        pairwise_total = 0
        pairwise_wins = 0
        pairwise_ties = 0
        pairwise_weight_total = 0.0
        pairwise_weighted_credit = 0.0
        control_scores: List[float] = []
        for item in ranked:
            if item.get("role") != "control":
                continue
            pairwise_total += 1
            control_score = _comparator_rank_value(item, comparator_id)
            control_scores.append(control_score)
            weight = control_weight(item)
            credit = comparison_credit(
                event_score,
                control_score,
                orientation=orientation,
                tolerance=tie_tolerance,
            )
            pairwise_weight_total += weight
            pairwise_weighted_credit += credit * weight
            if credit == 1.0:
                pairwise_wins += 1
            elif credit == 0.5:
                pairwise_ties += 1
        unweighted_credit = pairwise_wins + (0.5 * pairwise_ties)
        best_control_score = None
        if control_scores:
            best_control_score = (
                max(control_scores)
                if orientation > 0
                else min(control_scores)
            )
        weighted_rate = (
            pairwise_weighted_credit / pairwise_weight_total
            if pairwise_weight_total > 0.0
            else None
        )
        results[comparator_id] = {
            "id": comparator_id,
            "label": str(event_model.get("label") or comparator_id),
            "outcome_polarity": normalized_outcome,
            "score_polarity": score_polarity,
            "rank_direction": "descending" if orientation > 0 else "ascending",
            "event_rank": event_rank_min,
            "event_rank_min": event_rank_min,
            "event_rank_max": event_rank_max,
            "event_tie_count": tied_peer_count,
            "event_score": round(event_score, 4),
            "event_display_score": int(event_model.get("score") or 0),
            "best_control_score": best_control_score,
            "pairwise_wins": pairwise_wins,
            "pairwise_ties": pairwise_ties,
            "pairwise_total": pairwise_total,
            "pairwise_weight_total": round(pairwise_weight_total, 6),
            "pairwise_weighted_credit": round(pairwise_weighted_credit, 6),
            "pairwise_win_rate": round(weighted_rate, 4) if weighted_rate is not None else None,
            "unweighted_pairwise_win_rate": (
                round(unweighted_credit / pairwise_total, 4)
                if pairwise_total
                else None
            ),
            "auc": round(weighted_rate, 4) if weighted_rate is not None else None,
            "top_3_hit": bool(event_rank_min <= 3),
            "reciprocal_rank": round(1.0 / float(event_rank_min), 6),
            "ranking": [
                {
                    "role": item.get("role"),
                    "label": str((item.get("city") or {}).get("label") or ""),
                    "score": round(_comparator_rank_value(item, comparator_id), 4),
                    "oriented_score": round(
                        _comparator_rank_value(item, comparator_id) * orientation,
                        4,
                    ),
                    "display_score": int((((item.get("models") or {}).get(comparator_id) or {}).get("score")) or 0),
                    "comparison_weight": (
                        control_weight(item)
                        if item.get("role") == "control"
                        else None
                    ),
                }
                for item in ranked
            ],
        }
    return results


def _entry_pairwise_rate(entry: Dict[str, Any]) -> Optional[float]:
    if entry.get("pairwise_win_rate") is not None:
        return float(entry["pairwise_win_rate"])
    weighted_total = float(entry.get("pairwise_weight_total") or 0.0)
    if weighted_total > 0.0 and entry.get("pairwise_weighted_credit") is not None:
        return float(entry.get("pairwise_weighted_credit") or 0.0) / weighted_total
    pairwise_total = int(entry.get("pairwise_total") or 0)
    if pairwise_total <= 0:
        return None
    return (
        float(entry.get("pairwise_wins") or 0)
        + (0.5 * float(entry.get("pairwise_ties") or 0))
    ) / float(pairwise_total)


def _summarize_case_group(case_results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    comparator_ids = sorted(
        {
            comparator_id
            for case in case_results
            for comparator_id in (case.get("comparators") or {}).keys()
        }
    )
    comparators: Dict[str, Dict[str, Any]] = {}
    for comparator_id in comparator_ids:
        records = [
            (case, case["comparators"][comparator_id])
            for case in case_results
            if comparator_id in (case.get("comparators") or {})
        ]
        if not records:
            continue
        entries = [entry for _, entry in records]
        pairwise_total = sum(int(entry.get("pairwise_total") or 0) for entry in entries)
        micro_pairwise_weight_total = sum(
            float(entry.get("pairwise_weight_total") or entry.get("pairwise_total") or 0.0)
            for entry in entries
        )
        micro_pairwise_credit = sum(
            (
                float(entry.get("pairwise_weighted_credit"))
                if entry.get("pairwise_weighted_credit") is not None
                else float(entry.get("pairwise_wins") or 0)
                + (0.5 * float(entry.get("pairwise_ties") or 0))
            )
            for entry in entries
        )
        case_observations: List[Dict[str, Any]] = []
        for index, (case, entry) in enumerate(records):
            rate = _entry_pairwise_rate(entry)
            case_observations.append(
                {
                    "case_id": str(case.get("case_id") or f"case-{index}"),
                    "person_group_id": str(
                        case.get("person_id")
                        or case.get("_person_group_id")
                        or case.get("person_name")
                        or case.get("case_id")
                        or f"case-{index}"
                    ).strip().lower(),
                    "weight": case_weight(case),
                    "pairwise_rate": float(rate) if rate is not None else None,
                    "top_3_hit": 1.0 if entry.get("top_3_hit") else 0.0,
                    "reciprocal_rank": float(entry.get("reciprocal_rank") or 0.0),
                    "event_rank": float(entry.get("event_rank") or 0.0),
                }
            )
        rate_observations = [
            observation
            for observation in case_observations
            if observation["pairwise_rate"] is not None
        ]
        case_weighted_rate = weighted_mean(
            (observation["pairwise_rate"], observation["weight"])
            for observation in rate_observations
        )
        top_3_rate = weighted_mean(
            (observation["top_3_hit"], observation["weight"])
            for observation in case_observations
        )
        mean_reciprocal_rank = weighted_mean(
            (observation["reciprocal_rank"], observation["weight"])
            for observation in case_observations
        )
        mean_rank = weighted_mean(
            (observation["event_rank"], observation["weight"])
            for observation in case_observations
        )
        auc_ci = clustered_bootstrap_ci(
            rate_observations,
            value_key="pairwise_rate",
            seed=f"{DEFAULT_SPLIT_SEED}:{comparator_id}",
        )
        comparators[comparator_id] = {
            "label": str(entries[0].get("label") or comparator_id),
            "case_count": len(entries),
            "successful_pairwise_case_count": len(rate_observations),
            "case_weight_total": round(sum(item["weight"] for item in case_observations), 6),
            "pairwise_total": pairwise_total,
            "micro_pairwise_weight_total": round(micro_pairwise_weight_total, 6),
            "pairwise_win_rate": round(case_weighted_rate, 4) if case_weighted_rate is not None else None,
            "micro_pairwise_win_rate": (
                round(micro_pairwise_credit / micro_pairwise_weight_total, 4)
                if micro_pairwise_weight_total > 0.0
                else None
            ),
            "auc": round(case_weighted_rate, 4) if case_weighted_rate is not None else None,
            "auc_ci_95": auc_ci,
            "top_3_hit_rate": round(top_3_rate, 4) if top_3_rate is not None else None,
            "mean_reciprocal_rank": (
                round(mean_reciprocal_rank, 4)
                if mean_reciprocal_rank is not None
                else None
            ),
            "mean_event_rank": round(mean_rank, 4) if mean_rank is not None else None,
            "aggregation": "case_weighted",
        }

    for comparator_id, summary in comparators.items():
        if comparator_id == "product_model":
            continue
        matched: List[Tuple[float, float, float]] = []
        for case in case_results:
            case_comparators = case.get("comparators") or {}
            product_entry = case_comparators.get("product_model")
            comparator_entry = case_comparators.get(comparator_id)
            if not product_entry or not comparator_entry:
                continue
            product_rate = _entry_pairwise_rate(product_entry)
            comparator_rate = _entry_pairwise_rate(comparator_entry)
            if product_rate is None or comparator_rate is None:
                continue
            matched.append(
                (
                    float(product_rate),
                    float(comparator_rate),
                    case_weight(case),
                )
            )
        product_matched = weighted_mean((product, weight) for product, _, weight in matched)
        comparator_matched = weighted_mean((baseline, weight) for _, baseline, weight in matched)
        summary["matched_case_count_vs_product"] = len(matched)
        summary["matched_product_pairwise_win_rate"] = (
            round(product_matched, 4) if product_matched is not None else None
        )
        if product_matched is not None and comparator_matched is not None:
            summary["pairwise_lift_vs_product"] = round(
                product_matched - comparator_matched,
                4,
            )
    return comparators


def summarize_benchmark_results(
    case_results: Sequence[Dict[str, Any]],
    *,
    attempted_case_count: Optional[int] = None,
    failures: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    overall = _summarize_case_group(case_results)
    by_goal: Dict[str, Dict[str, Any]] = {}
    goal_ids = sorted({str(case.get("goal_id") or "") for case in case_results if str(case.get("goal_id") or "")})
    for goal_id in goal_ids:
        scoped = [case for case in case_results if str(case.get("goal_id") or "") == goal_id]
        by_goal[goal_id] = _summarize_case_group(scoped)
    attempted = (
        int(attempted_case_count)
        if attempted_case_count is not None
        else len(case_results) + len(failures or [])
    )
    failed = len(failures or [])
    successful = len(case_results)
    return {
        "overall": overall,
        "by_goal": by_goal,
        "accounting": {
            "attempted_case_count": attempted,
            "successful_case_count": successful,
            "failed_case_count": failed,
            "coverage_rate": round(successful / float(attempted), 4) if attempted else None,
            "model_metrics_exclude_failed_cases": True,
        },
    }


def _render_markdown_report(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Astrocartography Benchmark Summary")
    lines.append("")
    lines.append(f"- Mode: `{result.get('mode')}`")
    lines.append(f"- Dataset count: `{len(result.get('datasets') or [])}`")
    lines.append(f"- Enabled cases: `{len(result.get('case_results') or [])}`")
    lines.append(f"- Skipped rows: `{len(result.get('skipped') or [])}`")
    lines.append(f"- Failed cases: `{len(result.get('failures') or [])}`")
    accounting = (result.get("summary") or {}).get("accounting") or {}
    lines.append(
        f"- Successful coverage: `{accounting.get('coverage_rate') if accounting.get('coverage_rate') is not None else 'n/a'}`"
    )
    lines.append(f"- Validation split: `{((result.get('split') or {}).get('requested_split') or 'all')}`")
    lines.append("- Public specialist gate: `experimental until positive held-out lift`")
    lines.append("")

    overall = (result.get("summary") or {}).get("overall") or {}
    if overall:
        lines.append("## Overall")
        lines.append("")
        lines.append("| Comparator | Cases | Pairwise | Top-3 | MRR | Mean Rank |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for comparator_id, payload in overall.items():
            lines.append(
                f"| {payload.get('label') or comparator_id} | {payload.get('case_count') or 0} | "
                f"{payload.get('pairwise_win_rate') if payload.get('pairwise_win_rate') is not None else 'n/a'} | "
                f"{payload.get('top_3_hit_rate') if payload.get('top_3_hit_rate') is not None else 'n/a'} | "
                f"{payload.get('mean_reciprocal_rank') if payload.get('mean_reciprocal_rank') is not None else 'n/a'} | "
                f"{payload.get('mean_event_rank') if payload.get('mean_event_rank') is not None else 'n/a'} |"
            )
        lines.append("")

    by_goal = (result.get("summary") or {}).get("by_goal") or {}
    for goal_id, comparators in by_goal.items():
        lines.append(f"## Goal: `{goal_id}`")
        lines.append("")
        lines.append("| Comparator | Cases | Pairwise | Top-3 | MRR | Mean Rank |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for comparator_id, payload in comparators.items():
            lines.append(
                f"| {payload.get('label') or comparator_id} | {payload.get('case_count') or 0} | "
                f"{payload.get('pairwise_win_rate') if payload.get('pairwise_win_rate') is not None else 'n/a'} | "
                f"{payload.get('top_3_hit_rate') if payload.get('top_3_hit_rate') is not None else 'n/a'} | "
                f"{payload.get('mean_reciprocal_rank') if payload.get('mean_reciprocal_rank') is not None else 'n/a'} | "
                f"{payload.get('mean_event_rank') if payload.get('mean_event_rank') is not None else 'n/a'} |"
            )
        lines.append("")

    if result.get("failures"):
        lines.append("## Failed Cases")
        lines.append("")
        for failure in result["failures"]:
            lines.append(f"- `{failure.get('case_id')}`: {failure.get('error')}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def run_benchmark(
    dataset_paths: Sequence[str | Path],
    *,
    mode: str,
    case_id: Optional[str] = None,
    allow_live_geocode: bool = False,
    include_disabled: bool = False,
    split: str = "all",
    holdout_fraction: float = DEFAULT_HOLDOUT_FRACTION,
    split_seed: str = DEFAULT_SPLIT_SEED,
    require_frozen_controls: bool = False,
    require_exposure_matched_controls: bool = False,
) -> Dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode: {mode}")

    loaded_cases, skipped = load_benchmark_cases(
        dataset_paths,
        case_id=case_id,
        include_disabled=include_disabled,
    )
    cases, split_skipped, split_manifest = select_validation_split(
        loaded_cases,
        split=split,
        holdout_fraction=holdout_fraction,
        seed=split_seed,
    )
    skipped = [*skipped, *split_skipped]
    case_results: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    for case in cases:
        current_case_id = _normalize_text(case.get("case_id")) or f"line-{case.get('_line_number')}"
        try:
            context = _build_case_context(case, mode=mode, allow_live_geocode=allow_live_geocode)
            natal_timestamp = _normalize_text((context.get("natal_meta") or {}).get("timestamp"))
            if not natal_timestamp:
                raise ValueError("Missing natal timestamp")

            event_block = _require_block(case, "event")
            outcome_polarity = normalize_outcome_polarity(
                event_block.get("outcome_polarity")
            )
            control_blocks, control_design = _control_blocks_for_case(case)
            _validate_control_design(
                control_design,
                require_frozen_controls=require_frozen_controls,
                require_exposure_matched_controls=require_exposure_matched_controls,
            )

            scored_candidates: List[Dict[str, Any]] = []
            event_city = dict(context.get("event_city_for_transit") or {})
            if not event_city:
                event_city = _resolve_city_payload(event_block.get("location"), allow_live_geocode=allow_live_geocode)
            event_scored = _score_city_for_case(
                event_city,
                goal_id=str(context["goal_id"]),
                natal_timestamp=natal_timestamp,
                natal_lines=context["natal_lines"],
                transit_lines=context.get("transit_lines"),
            )
            event_scored["role"] = "event"
            scored_candidates.append(event_scored)

            for raw_control in control_blocks:
                resolved_control = _resolve_city_payload(raw_control, allow_live_geocode=allow_live_geocode)
                control_scored = _score_city_for_case(
                    resolved_control,
                    goal_id=str(context["goal_id"]),
                    natal_timestamp=natal_timestamp,
                    natal_lines=context["natal_lines"],
                    transit_lines=context.get("transit_lines"),
                )
                control_scored["role"] = "control"
                control_scored["reason"] = raw_control.get("reason") if isinstance(raw_control, dict) else ""
                control_scored["comparison_weight"] = control_weight(raw_control)
                if isinstance(raw_control, dict):
                    control_scored["exposure"] = raw_control.get("exposure")
                scored_candidates.append(control_scored)

            comparators = rank_case_scores(
                scored_candidates,
                outcome_polarity=outcome_polarity,
                goal_id=str(context["goal_id"]),
            )
            case_results.append(
                {
                    "case_id": current_case_id,
                    "goal_id": str(context["goal_id"]),
                    "dataset": str(case.get("_dataset_path") or ""),
                    "line_number": int(case.get("_line_number") or 0),
                    "person_name": _normalize_text(case.get("person_name")),
                    "person_id": _normalize_text(case.get("person_id")),
                    "_person_group_id": str(
                        case.get("_person_group_id") or person_group_id(case)
                    ),
                    "validation_split": str(case.get("_validation_split") or ""),
                    "case_weight": case_weight(case),
                    "outcome_polarity": outcome_polarity,
                    "control_design": control_design,
                    "mode": mode,
                    "comparators": comparators,
                    "candidates": scored_candidates,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "case_id": current_case_id,
                    "dataset": str(case.get("_dataset_path") or ""),
                    "line_number": int(case.get("_line_number") or 0),
                    "goal_id": _normalize_text(case.get("goal_id")).lower(),
                    "person_id": _normalize_text(case.get("person_id")),
                    "validation_split": str(case.get("_validation_split") or ""),
                    "error": str(exc),
                }
            )

    result = {
        "mode": mode,
        "datasets": [str(Path(path).resolve()) for path in dataset_paths],
        "skipped": skipped,
        "failures": failures,
        "case_results": case_results,
        "split": split_manifest,
        "validation_status": {
            "fixture_scope": "historical_outcome_benchmark",
            "public_specialist_gate": "experimental",
            "promotion_requirement": "positive held-out lift on person-grouped holdout data",
        },
        "summary": summarize_benchmark_results(
            case_results,
            attempted_case_count=len(cases),
            failures=failures,
        ),
    }
    result["markdown"] = _render_markdown_report(result)
    return result


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run astrocartography benchmark cases against the current PathFinder scoring logic.")
    parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        help="Path to a JSONL benchmark dataset. Can be provided multiple times.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(SUPPORTED_MODES),
        default="natal_only",
        help="Benchmark mode to run.",
    )
    parser.add_argument("--case-id", help="Run a single case_id only.")
    parser.add_argument("--allow-live-geocode", action="store_true", help="Use expanded bundled catalog lookup when a city is missing from the primary shipped catalog match.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled template rows.")
    parser.add_argument(
        "--split",
        choices=sorted(SUPPORTED_VALIDATION_SPLITS),
        default="all",
        help="Run all cases or a deterministic person-grouped train/holdout partition.",
    )
    parser.add_argument(
        "--holdout-fraction",
        type=float,
        default=DEFAULT_HOLDOUT_FRACTION,
        help="Fraction of person groups assigned to holdout.",
    )
    parser.add_argument(
        "--split-seed",
        default=DEFAULT_SPLIT_SEED,
        help="Stable seed used to assign whole people to train or holdout.",
    )
    parser.add_argument("--require-frozen-controls", action="store_true")
    parser.add_argument("--require-exposure-matched-controls", action="store_true")
    parser.add_argument("--output-json", help="Write the full benchmark result to a JSON file.")
    parser.add_argument("--output-md", help="Write the Markdown summary to a file.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    datasets = args.datasets or [str(DEFAULT_SPECULATION_DATASET)]
    result = run_benchmark(
        datasets,
        mode=args.mode,
        case_id=args.case_id,
        allow_live_geocode=bool(args.allow_live_geocode),
        include_disabled=bool(args.include_disabled),
        split=args.split,
        holdout_fraction=args.holdout_fraction,
        split_seed=args.split_seed,
        require_frozen_controls=bool(args.require_frozen_controls),
        require_exposure_matched_controls=bool(args.require_exposure_matched_controls),
    )

    if args.output_json:
        output_json_path = Path(args.output_json).resolve()
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    if args.output_md:
        output_md_path = Path(args.output_md).resolve()
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.write_text(result["markdown"], encoding="utf-8")

    print(result["markdown"])
    return 0 if not result.get("failures") else 1


if __name__ == "__main__":
    raise SystemExit(main())
