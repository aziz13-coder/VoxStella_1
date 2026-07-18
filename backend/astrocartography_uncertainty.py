from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence


DEFAULT_USER_ENTERED_UNCERTAINTY_MINUTES = 5.0
MAX_SAMPLED_UNCERTAINTY_MINUTES = 720.0
MAX_ATLAS_STABILITY_CANDIDATES = 64


def _optional_nonnegative_float(value: Any) -> Optional[float]:
    if value in (None, "", "null"):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < 0.0:
        return None
    return parsed


def build_birth_time_sampling_plan(
    birth_time_quality: Optional[Mapping[str, Any]],
    *,
    default_user_entered_minutes: float = DEFAULT_USER_ENTERED_UNCERTAINTY_MINUTES,
) -> Dict[str, Any]:
    """Return a bounded, deterministic symmetric sampling plan.

    Precise ranges use the two endpoints. Wider declared ranges add interior
    samples so a full-day uncertainty cannot hide intermediate house or angle
    changes. The reported time remains the center calculation.
    """

    quality = dict(birth_time_quality or {})
    status = str(quality.get("status") or "user_entered_time").strip().lower()
    eligibility = str(quality.get("ranking_eligibility") or "").strip().lower()
    confidence = str(quality.get("confidence") or "").strip().lower()
    declared = _optional_nonnegative_float(quality.get("effective_uncertainty_minutes"))
    if declared is None:
        declared = _optional_nonnegative_float(quality.get("uncertainty_minutes"))

    assumed = False
    requested = declared
    if requested is None and (
        status in {"user_entered_time", "user_entered", ""}
        or confidence == "user_entered"
        or eligibility == "provisional"
    ):
        requested = max(0.0, float(default_user_entered_minutes))
        assumed = True

    if requested is None:
        return {
            "status": "not_sampled",
            "method": "bounded_symmetric_time_grid_v1",
            "reason": "No numeric birth-time uncertainty range is available.",
            "declared_uncertainty_minutes": declared,
            "sampled_uncertainty_minutes": None,
            "assumed_uncertainty": False,
            "center_included": True,
            "samples": [],
        }

    sampled = min(float(requested), MAX_SAMPLED_UNCERTAINTY_MINUTES)
    range_capped = sampled + 1e-9 < float(requested)
    if sampled <= 1e-9:
        return {
            "status": "exact",
            "method": "bounded_symmetric_time_grid_v1",
            "declared_uncertainty_minutes": round(float(declared or 0.0), 3),
            "sampled_uncertainty_minutes": 0.0,
            "assumed_uncertainty": assumed,
            "range_capped": range_capped,
            "center_included": True,
            "samples": [],
        }

    if sampled <= 5.0:
        sample_count = 2
    elif sampled <= 30.0:
        sample_count = 4
    elif sampled <= 120.0:
        sample_count = 8
    else:
        sample_count = 12
    half_count = sample_count // 2
    negative_factors = [
        -1.0 + (index / half_count)
        for index in range(half_count)
    ]
    factors = negative_factors + [-value for value in reversed(negative_factors)]
    samples = []
    for index, factor in enumerate(factors, start=1):
        offset = round(sampled * factor, 6)
        samples.append(
            {
                "id": f"birth_time_sample_{index:02d}",
                "position": "earlier_sample" if offset < 0 else "later_sample",
                "offset_minutes": offset,
            }
        )
    return {
        "status": "ready",
        "method": "bounded_symmetric_time_grid_v1",
        "declared_uncertainty_minutes": (
            round(float(declared), 3) if declared is not None else None
        ),
        "sampled_uncertainty_minutes": round(sampled, 3),
        "assumed_uncertainty": assumed,
        "assumption": (
            f"User-entered times without a declared range are sampled at +/-{sampled:g} minutes."
            if assumed
            else None
        ),
        "range_capped": range_capped,
        "coverage_warning": (
            f"Declared uncertainty exceeds the bounded +/-{MAX_SAMPLED_UNCERTAINTY_MINUTES:g}-minute grid; "
            "reported envelopes cover the sampled range, not the full declaration."
            if range_capped
            else None
        ),
        "center_included": True,
        "sample_count": len(samples),
        "samples": samples,
    }


def shift_iso_timestamp(timestamp_iso: str, offset_minutes: float) -> str:
    """Shift an ISO instant while preserving its displayed UTC offset."""

    base = datetime.fromisoformat(str(timestamp_iso).replace("Z", "+00:00"))
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    shifted = base.astimezone(timezone.utc) + timedelta(minutes=float(offset_minutes))
    return shifted.astimezone(base.tzinfo).isoformat()


def attach_birth_time_sample_evaluations(
    base_evaluation: Mapping[str, Any],
    *,
    sampling_plan: Mapping[str, Any],
    sample_evaluations: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Attach observed score bounds from full endpoint recalculations."""

    result = deepcopy(dict(base_evaluation or {}))
    public_samples: List[Dict[str, Any]] = []
    observed_scores: List[int] = []
    observed_raw_scores: List[float] = []
    if result.get("score") is not None:
        observed_scores.append(int(result["score"]))
    if result.get("raw_score") is not None:
        observed_raw_scores.append(float(result["raw_score"]))

    for sample in sample_evaluations:
        evaluation = sample.get("evaluation") if isinstance(sample.get("evaluation"), Mapping) else {}
        score = evaluation.get("score")
        raw_score = evaluation.get("raw_score")
        if score is not None:
            observed_scores.append(int(score))
        if raw_score is not None:
            observed_raw_scores.append(float(raw_score))
        public = {
            "id": sample.get("id"),
            "position": sample.get("position"),
            "offset_minutes": sample.get("offset_minutes"),
            "timestamp": sample.get("timestamp"),
            "score": score,
            "raw_score": raw_score,
            "score_available": bool(evaluation.get("score_available", score is not None)),
            "evidence_strength": evaluation.get("evidence_strength"),
            "ranking_eligible": evaluation.get("ranking_eligible"),
        }
        for key in ("lead_line", "lead_line_distance_km", "relocation_available"):
            if key in sample:
                public[key] = sample.get(key)
        public_samples.append(public)

    time_interval = {
        "low": min(observed_scores) if observed_scores else None,
        "high": max(observed_scores) if observed_scores else None,
    }
    raw_interval = {
        "low": round(min(observed_raw_scores), 4) if observed_raw_scores else None,
        "high": round(max(observed_raw_scores), 4) if observed_raw_scores else None,
    }
    prior_interval = result.get("score_interval")
    prior_low = prior_interval.get("low") if isinstance(prior_interval, Mapping) else None
    prior_high = prior_interval.get("high") if isinstance(prior_interval, Mapping) else None
    combined_lows = [value for value in (prior_low, time_interval["low"]) if value is not None]
    combined_highs = [value for value in (prior_high, time_interval["high"]) if value is not None]
    combined_interval = {
        "low": min(combined_lows) if combined_lows else None,
        "high": max(combined_highs) if combined_highs else None,
    }

    sampling = {
        **dict(sampling_plan or {}),
        "status": (
            (
                "evaluated"
                if sampling_plan.get("coverage_complete", True)
                else "evaluated_partial"
            )
            if public_samples
            else str(sampling_plan.get("status") or "not_sampled")
        ),
        "recomputed_sample_count": len(public_samples),
        "total_chart_count": 1 + len(public_samples),
        "score_interval": time_interval,
        "raw_score_interval": raw_interval,
        "samples": public_samples,
    }
    uncertainty = dict(result.get("uncertainty") or {})
    uncertainty["birth_time_sampling"] = sampling
    uncertainty["score_interval"] = combined_interval
    uncertainty["score_interval_method"] = (
        "combined_recomputed_time_and_distance_scenarios_v1"
        if public_samples
        else str(
            uncertainty.get("score_interval_method")
            or "recomputed_distance_profiles_v1"
        )
    )
    result["uncertainty"] = uncertainty
    result["score_interval"] = combined_interval
    result["score_interval_method"] = uncertainty["score_interval_method"]
    return result


def summarize_line_uncertainty_corridors(
    base_lines_payload: Mapping[str, Any],
    *,
    sampling_plan: Mapping[str, Any],
    sample_line_payloads: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Summarize sampled movement as equatorial geographic corridors.

    Every angular curve crosses the equator at a deterministic longitude.
    Reporting the sampled west/east envelope there avoids pretending that a
    single global kilometre width represents a curved ASC/DSC line.
    """

    angle_offsets = {"MC": 0.0, "IC": 180.0, "ASC": -90.0, "DSC": 90.0}

    def _wrap180(value: float) -> float:
        wrapped = float(value) % 360.0
        return wrapped - 360.0 if wrapped > 180.0 else wrapped

    def _delta(value: float, center: float) -> float:
        return _wrap180(float(value) - float(center))

    sample_maps: List[Dict[str, Mapping[str, Any]]] = []
    sample_meta: List[Dict[str, Any]] = []
    for sample in sample_line_payloads:
        payload = sample.get("lines_payload") if isinstance(sample.get("lines_payload"), Mapping) else sample
        sample_maps.append({
            str(line.get("id") or ""): line
            for line in (payload.get("lines") or [])
            if isinstance(line, Mapping) and line.get("id")
        })
        sample_meta.append({
            "id": sample.get("id"),
            "offset_minutes": sample.get("offset_minutes"),
            "timestamp": sample.get("timestamp") or payload.get("timestamp"),
        })

    corridors: List[Dict[str, Any]] = []
    for line in base_lines_payload.get("lines") or []:
        if not isinstance(line, Mapping):
            continue
        line_id = str(line.get("id") or "")
        angle = str(line.get("angle") or "").upper()
        geometry = line.get("geometry") if isinstance(line.get("geometry"), Mapping) else {}
        substellar = _optional_nonnegative_float(geometry.get("substellar_longitude_deg"))
        if substellar is None:
            try:
                substellar = float(geometry.get("substellar_longitude_deg"))
            except (TypeError, ValueError):
                continue
        center = _wrap180(float(substellar) + angle_offsets.get(angle, 0.0))
        sampled_longitudes: List[float] = [center]
        endpoint_rows: List[Dict[str, Any]] = []
        for index, sample_map in enumerate(sample_maps):
            sampled_line = sample_map.get(line_id)
            sampled_geometry = (
                sampled_line.get("geometry")
                if isinstance(sampled_line, Mapping) and isinstance(sampled_line.get("geometry"), Mapping)
                else {}
            )
            try:
                sampled_substellar = float(sampled_geometry.get("substellar_longitude_deg"))
            except (TypeError, ValueError):
                continue
            longitude = _wrap180(sampled_substellar + angle_offsets.get(angle, 0.0))
            sampled_longitudes.append(longitude)
            endpoint_rows.append({
                **sample_meta[index],
                "equatorial_longitude": round(longitude, 6),
                "shift_from_center_deg": round(_delta(longitude, center), 6),
            })
        deltas = [_delta(value, center) for value in sampled_longitudes]
        west_delta = min(deltas)
        east_delta = max(deltas)
        corridors.append({
            "id": line_id,
            "body": line.get("body"),
            "angle": angle,
            "center_equatorial_longitude": round(center, 6),
            "west_equatorial_longitude": round(_wrap180(center + west_delta), 6),
            "east_equatorial_longitude": round(_wrap180(center + east_delta), 6),
            "west_shift_km_at_equator": round(abs(west_delta) * 111.195, 1),
            "east_shift_km_at_equator": round(abs(east_delta) * 111.195, 1),
            "sampled_width_km_at_equator": round((east_delta - west_delta) * 111.195, 1),
            "samples": endpoint_rows,
        })

    corridor_status = (
        (
            "evaluated"
            if sampling_plan.get("coverage_complete", True)
            else "evaluated_partial"
        )
        if sample_line_payloads
        else "not_sampled"
    )
    return {
        "status": corridor_status,
        "method": "equatorial_time_sample_envelope_v1",
        "sampling": dict(sampling_plan or {}),
        "sample_count": len(sample_line_payloads),
        "corridor_count": len(corridors),
        "corridors": corridors,
        "note": (
            "Widths are measured where each line crosses the equator; curved ASC/DSC "
            "corridors vary with latitude."
        ),
        "warnings": [
            warning
            for warning in (
                sampling_plan.get("coverage_warning"),
                sampling_plan.get("preparation_warning"),
            )
            if warning
        ],
    }


def _candidate_key(item: Mapping[str, Any], index: int) -> str:
    target = item.get("target") if isinstance(item.get("target"), Mapping) else {}
    candidate_id = target.get("candidate_id")
    if candidate_id not in (None, ""):
        return str(candidate_id)
    latitude = target.get("latitude")
    longitude = target.get("longitude")
    if latitude is not None and longitude is not None:
        try:
            return f"coordinate:{float(latitude):.6f}:{float(longitude):.6f}"
        except (TypeError, ValueError):
            pass
    return f"row:{index}:{target.get('label') or target.get('query') or ''}"


def _scenario_sort_key(
    *,
    raw_score: Any,
    score: Any,
    label: Any,
    candidate_key: str,
    score_polarity: str,
) -> tuple:
    raw_value = float(raw_score or 0.0)
    score_value = float(score or 0.0)
    if score_polarity == "higher_is_worse":
        return (raw_value, score_value, str(label or ""), str(candidate_key))
    return (-raw_value, -score_value, str(label or ""), str(candidate_key))


def apply_cross_location_rank_stability(
    rows: Sequence[MutableMapping[str, Any]],
    *,
    score_polarity: str = "higher_is_better",
    top_k: Optional[int] = None,
    scope_candidate_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute ranks across common distance and birth-time resample scenarios."""

    if not rows:
        return {
            "status": "not_applicable",
            "method": "cross_location_common_scenarios_v1",
            "candidate_count": 0,
            "scenario_count": 0,
        }

    keyed: Dict[str, MutableMapping[str, Any]] = {}
    meta: Dict[str, Dict[str, Any]] = {}
    for index, item in enumerate(rows):
        base_key = _candidate_key(item, index)
        key = base_key if base_key not in keyed else f"{base_key}#{index}"
        keyed[key] = item
        target = item.get("target") if isinstance(item.get("target"), Mapping) else {}
        meta[key] = {
            "label": target.get("label") or target.get("query") or key,
        }

    candidate_count = len(keyed)
    top_k_value = max(1, min(int(top_k or candidate_count), candidate_count))
    scenarios: Dict[str, Dict[str, Dict[str, Any]]] = {"reported_time": {}}
    scenario_types: Dict[str, str] = {"reported_time": "baseline"}
    for key, item in keyed.items():
        score_payload = item.get("location_score") if isinstance(item.get("location_score"), Mapping) else {}
        scenarios["reported_time"][key] = {
            "raw_score": score_payload.get("raw_score"),
            "score": score_payload.get("score"),
        }

        distance = (
            ((score_payload.get("uncertainty") or {}).get("distance_sensitivity") or {})
            if isinstance(score_payload.get("uncertainty"), Mapping)
            else {}
        )
        profiles = distance.get("profiles") if isinstance(distance.get("profiles"), Mapping) else {}
        for profile_name, profile in profiles.items():
            if not isinstance(profile, Mapping):
                continue
            scenario_id = f"distance:{profile_name}"
            scenarios.setdefault(scenario_id, {})[key] = {
                "raw_score": profile.get("raw_score"),
                "score": profile.get("score"),
            }
            scenario_types[scenario_id] = "distance_sensitivity"

        sampling = (
            ((score_payload.get("uncertainty") or {}).get("birth_time_sampling") or {})
            if isinstance(score_payload.get("uncertainty"), Mapping)
            else {}
        )
        for sample in sampling.get("samples") or []:
            if not isinstance(sample, Mapping) or not sample.get("id"):
                continue
            scenario_id = f"time:{sample.get('id')}"
            scenarios.setdefault(scenario_id, {})[key] = {
                "raw_score": sample.get("raw_score"),
                "score": sample.get("score"),
            }
            scenario_types[scenario_id] = "birth_time_resample"

    complete_scenarios = {
        scenario_id: values
        for scenario_id, values in scenarios.items()
        if len(values) == candidate_count
        and all(payload.get("score") is not None for payload in values.values())
    }
    deduplicated_scenarios: List[Dict[str, Any]] = []
    baseline_values = complete_scenarios.get("reported_time") or {}
    for scenario_id in list(complete_scenarios):
        if scenario_id == "reported_time" or not baseline_values:
            continue
        values = complete_scenarios[scenario_id]
        identical_to_baseline = all(
            abs(
                float((values.get(key) or {}).get("raw_score") or 0.0)
                - float((baseline_values.get(key) or {}).get("raw_score") or 0.0)
            ) <= 0.001
            and float((values.get(key) or {}).get("score") or 0.0)
            == float((baseline_values.get(key) or {}).get("score") or 0.0)
            for key in baseline_values
        )
        if identical_to_baseline:
            complete_scenarios.pop(scenario_id, None)
            deduplicated_scenarios.append(
                {
                    "id": scenario_id,
                    "duplicate_of": "reported_time",
                }
            )
    scenario_ranks: Dict[str, Dict[str, int]] = {}
    for scenario_id, values in complete_scenarios.items():
        ordered = sorted(
            values,
            key=lambda key: _scenario_sort_key(
                raw_score=values[key].get("raw_score"),
                score=values[key].get("score"),
                label=meta[key]["label"],
                candidate_key=key,
                score_polarity=score_polarity,
            ),
        )
        scenario_ranks[scenario_id] = {
            key: index
            for index, key in enumerate(ordered, start=1)
        }

    scenario_ids = list(scenario_ranks)
    for key, item in keyed.items():
        location_score = item.get("location_score")
        if not isinstance(location_score, MutableMapping):
            continue
        if candidate_count < 2:
            location_score["rank_stability"] = {
                "status": "not_applicable",
                "reason": "Rank stability needs at least two locations.",
                "method": "cross_location_common_scenarios_v1",
                "candidate_count": candidate_count,
                "scenario_count": len(scenario_ids),
            }
            continue

        ranks = [
            scenario_ranks[scenario_id][key]
            for scenario_id in scenario_ids
            if key in scenario_ranks[scenario_id]
        ]
        baseline_rank = scenario_ranks.get("reported_time", {}).get(key)
        rank_low = min(ranks) if ranks else baseline_rank
        rank_high = max(ranks) if ranks else baseline_rank
        spread = (
            int(rank_high) - int(rank_low)
            if rank_low is not None and rank_high is not None
            else None
        )
        retention = (
            sum(1 for rank in ranks if rank <= top_k_value) / len(ranks)
            if ranks
            else None
        )
        if spread is None:
            status = "insufficient_scenarios"
        elif spread == 0 and (retention is None or retention >= 0.999):
            status = "stable"
        elif spread <= 2 and (retention is None or retention >= 0.75):
            status = "moderate"
        else:
            status = "variable"
        location_score["rank_stability"] = {
            "status": status,
            "method": "cross_location_common_scenarios_v1",
            "baseline_rank": baseline_rank,
            "rank_interval": {"best": rank_low, "worst": rank_high},
            "rank_spread": spread,
            "top_k": top_k_value,
            "top_k_retention": round(retention, 3) if retention is not None else None,
            "candidate_count": candidate_count,
            "scope_candidate_count": int(scope_candidate_count or candidate_count),
            "bounded_scope": int(scope_candidate_count or candidate_count) > candidate_count,
            "scope_coverage": round(
                candidate_count / max(1, int(scope_candidate_count or candidate_count)),
                3,
            ),
            "scenario_count": len(scenario_ids),
            "birth_time_scenario_count": sum(
                1 for scenario_id in scenario_ids
                if scenario_types.get(scenario_id) == "birth_time_resample"
            ),
            "distance_scenario_count": sum(
                1 for scenario_id in scenario_ids
                if scenario_types.get(scenario_id) == "distance_sensitivity"
            ),
            "scenarios": [
                {
                    "id": scenario_id,
                    "kind": scenario_types.get(scenario_id),
                    "rank": scenario_ranks[scenario_id].get(key),
                }
                for scenario_id in scenario_ids
            ],
            "deduplicated_scenarios": deduplicated_scenarios,
            "detail": (
                f"Rank ranged from {rank_low} to {rank_high} across "
                f"{len(scenario_ids)} common recalculation scenarios."
                if rank_low is not None and rank_high is not None
                else "Comparable recalculation scenarios were unavailable."
            ),
        }

    return {
        "status": "evaluated" if candidate_count >= 2 and scenario_ids else "not_applicable",
        "method": "cross_location_common_scenarios_v1",
        "candidate_count": candidate_count,
        "scope_candidate_count": int(scope_candidate_count or candidate_count),
        "bounded_scope": int(scope_candidate_count or candidate_count) > candidate_count,
        "scope_coverage": round(
            candidate_count / max(1, int(scope_candidate_count or candidate_count)),
            3,
        ),
        "top_k": top_k_value,
        "scenario_count": len(scenario_ids),
        "scenarios": [
            {
                "id": scenario_id,
                "kind": scenario_types.get(scenario_id),
            }
            for scenario_id in scenario_ids
        ],
        "deduplicated_scenarios": deduplicated_scenarios,
    }


def bounded_stability_pool(
    rows: Sequence[MutableMapping[str, Any]],
    *,
    requested_limit: int,
    cap: int = MAX_ATLAS_STABILITY_CANDIDATES,
) -> List[MutableMapping[str, Any]]:
    count = min(len(rows), max(int(requested_limit) * 4, int(requested_limit) + 8), int(cap))
    return list(rows[:count])
