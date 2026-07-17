from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any, Callable, Dict, List, Mapping, Optional

import mundane_service
from astrocartography_city_catalog import get_atlas_resolution_settings, normalize_atlas_resolution
from mundane_models import ActiveClockContext, MundaneContextRequest
from mundane_scan_grid import collect_region_candidates, describe_region, get_scan_catalog
from mundane_scan_models import MundaneScanRequest


SUPPORTED_SCAN_CHART_TYPES = {"war_event", "eclipse", "lunation", "aries_ingress"}
SUPPORTED_SCAN_MODES = {"spatial_scan", "spatiotemporal_scan", "long_range_async_scan"}
DEFAULT_SCAN_TOP_K = 8
MAX_SCAN_TOP_K = 20
MAX_SCAN_CANDIDATES = 32
DEFAULT_TIME_STEP_HOURS = 6
MAX_TIME_STEPS = 24
MAX_EVALUATED_CELLS = 160
LONG_RANGE_DEFAULT_TIME_STEP_HOURS = 12
LONG_RANGE_MAX_TIME_STEPS = 180
LONG_RANGE_MAX_EVALUATED_CELLS = 1200
LONG_RANGE_DEFAULT_CANDIDATE_LIMIT = 6
LONG_RANGE_MAX_CANDIDATES = 12
SERIES_PEAK_EPSILON = 1e-6

SCAN_MODE_LIMITS: Dict[str, Dict[str, Any]] = {
    "spatial_scan": {
        "max_time_slices": 1,
        "max_evaluated_cells": MAX_EVALUATED_CELLS,
        "default_time_step_hours": None,
        "default_candidate_limit": None,
        "max_candidates": MAX_SCAN_CANDIDATES,
        "async_only": False,
    },
    "spatiotemporal_scan": {
        "max_time_slices": MAX_TIME_STEPS,
        "max_evaluated_cells": MAX_EVALUATED_CELLS,
        "default_time_step_hours": DEFAULT_TIME_STEP_HOURS,
        "default_candidate_limit": None,
        "max_candidates": MAX_SCAN_CANDIDATES,
        "async_only": False,
    },
    "long_range_async_scan": {
        "max_time_slices": LONG_RANGE_MAX_TIME_STEPS,
        "max_evaluated_cells": LONG_RANGE_MAX_EVALUATED_CELLS,
        "default_time_step_hours": LONG_RANGE_DEFAULT_TIME_STEP_HOURS,
        "default_candidate_limit": LONG_RANGE_DEFAULT_CANDIDATE_LIMIT,
        "max_candidates": LONG_RANGE_MAX_CANDIDATES,
        "async_only": True,
    },
}


def _emit_progress(
    progress_callback: Optional[Callable[[Dict[str, Any]], None]],
    *,
    stage: str,
    percent: float,
    message: str,
    done: Optional[int] = None,
    total: Optional[int] = None,
    **extra: Any,
) -> None:
    if progress_callback is None:
        return
    payload: Dict[str, Any] = {
        "stage": str(stage or "working"),
        "percent": max(0.0, min(1.0, float(percent))),
        "message": str(message or "Working"),
    }
    if done is not None:
        payload["done"] = int(done)
    if total is not None:
        payload["total"] = int(total)
    if extra:
        payload.update(extra)
    progress_callback(payload)


def _normalize_id(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _scan_mode_config(scan_mode: str) -> Dict[str, Any]:
    normalized = _normalize_id(scan_mode)
    config = SCAN_MODE_LIMITS.get(normalized)
    if config is None:
        raise ValueError(f"Unsupported scan_mode: {scan_mode}")
    return config


def _coerce_positive_int(value: Any, *, field_name: str) -> int:
    try:
        parsed = int(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return parsed


def _coerce_nonnegative_float(value: Any, *, field_name: str) -> float:
    try:
        parsed = float(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return parsed


def _parse_datetime(value: str, *, field_name: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{field_name} is required")
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError(f"{field_name} must be ISO-8601 compatible") from exc


def _priority(level: Any) -> int:
    normalized = _normalize_id(level)
    return {
        "critical": 5,
        "high": 4,
        "elevated": 3,
        "watch": 2,
        "quiet": 1,
    }.get(normalized, 0)


def _scan_level_priority(level: Any) -> int:
    normalized = _normalize_id(level)
    return {
        "dominant": 6,
        "leading": 5,
        "co_leading": 4,
        "active": 3,
        "watch": 2,
        "background": 1,
    }.get(normalized, 0)


def _numeric_score(row: Mapping[str, Any], field_name: str) -> float:
    try:
        return float(row.get(field_name) or 0.0)
    except Exception:
        return 0.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    a = (sin(d_lat / 2.0) ** 2) + (cos(lat1_rad) * cos(lat2_rad) * (sin(d_lon / 2.0) ** 2))
    return 2.0 * earth_radius_km * asin(sqrt(max(0.0, min(1.0, a))))


def _scan_anchor(request_model: MundaneScanRequest) -> Optional[Dict[str, Any]]:
    base_request = request_model.context_request
    label = (
        str(base_request.reference_location or "").strip()
        or str(base_request.event_location or "").strip()
        or None
    )
    latitude = base_request.reference_latitude
    longitude = base_request.reference_longitude
    if latitude is None or longitude is None:
        return None
    try:
        return {
            "label": label or "Anchor",
            "latitude": float(latitude),
            "longitude": float(longitude),
        }
    except Exception:
        return None


def _war_scan_modifier(
    request_model: MundaneScanRequest,
    *,
    candidate: Dict[str, Any],
    anchor: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if _normalize_id(request_model.context_request.chart_type) != "war_event":
        return {"scan_bias": 0.0, "scan_bias_reason": None}
    if _normalize_id(request_model.context_request.domain) not in {"war_conflict", "war_outbreak", "campaign_escalation", "military_reversal"}:
        return {"scan_bias": 0.0, "scan_bias_reason": None}
    if not anchor:
        return {"scan_bias": 0.0, "scan_bias_reason": None}

    try:
        distance_km = _haversine_km(
            float(anchor["latitude"]),
            float(anchor["longitude"]),
            float(candidate.get("latitude") or 0.0),
            float(candidate.get("longitude") or 0.0),
        )
    except Exception:
        return {"scan_bias": 0.0, "scan_bias_reason": None}

    if distance_km <= 350.0:
        bias = 6.0
    elif distance_km <= 700.0:
        bias = 4.0
    elif distance_km <= 1200.0:
        bias = 2.0
    elif distance_km >= 2200.0:
        bias = -2.0
    else:
        bias = 0.0

    if bias == 0.0:
        reason = f"War-event scan anchor distance is {distance_km:.0f} km, which falls inside the neutral band."
    elif bias > 0:
        reason = f"War-event scan anchor is {distance_km:.0f} km away, so this cell stays close to the first-hostilities theater."
    else:
        reason = f"War-event scan anchor is {distance_km:.0f} km away, so this cell is displaced from the first-hostilities theater."
    return {
        "scan_bias": bias,
        "scan_bias_reason": reason,
        "scan_anchor_distance_km": round(distance_km, 1),
    }


def _scan_timepoints(request_model: MundaneScanRequest) -> List[str]:
    if request_model.scan_mode == "spatial_scan":
        return [str(request_model.fixed_datetime)]
    mode_config = _scan_mode_config(request_model.scan_mode)
    max_time_slices = int(mode_config.get("max_time_slices") or MAX_TIME_STEPS)
    start = _parse_datetime(str(request_model.start_datetime), field_name="start_datetime")
    end = _parse_datetime(str(request_model.end_datetime), field_name="end_datetime")
    if end <= start:
        raise ValueError("end_datetime must be later than start_datetime")
    step_hours = int(request_model.time_step_hours or DEFAULT_TIME_STEP_HOURS)
    points: List[str] = []
    current = start
    step = timedelta(hours=step_hours)
    while current <= end:
        points.append(current.isoformat())
        if len(points) > max_time_slices:
            raise ValueError(f"{request_model.scan_mode} is limited to {max_time_slices} time slices")
        current += step
    return points


def build_scan_request(args: Mapping[str, Any]) -> MundaneScanRequest:
    context_request = mundane_service.build_context_request(args, require_domain=True)
    chart_type = _normalize_id(context_request.chart_type)
    if chart_type not in SUPPORTED_SCAN_CHART_TYPES:
        raise ValueError(f"chart_type {context_request.chart_type} is not scan-enabled")
    mundane_service.enforce_chart_type_domain_pairing(
        context_request.chart_type,
        context_request.domain,
        execution_mode="scan",
    )

    scan_mode = _normalize_id(args.get("scan_mode") or "spatial_scan")
    if scan_mode not in SUPPORTED_SCAN_MODES:
        raise ValueError(f"Unsupported scan_mode: {scan_mode}")

    region_id = str(args.get("region_id") or "").strip()
    if not region_id:
        raise ValueError("region_id is required")
    describe_region(region_id)

    resolution = normalize_atlas_resolution(args.get("resolution"))
    top_k = DEFAULT_SCAN_TOP_K
    if args.get("top_k") not in (None, ""):
        top_k = min(MAX_SCAN_TOP_K, _coerce_positive_int(args.get("top_k"), field_name="top_k"))

    minimum_score = 0.0
    if args.get("minimum_score") not in (None, ""):
        minimum_score = _coerce_nonnegative_float(args.get("minimum_score"), field_name="minimum_score")

    mode_config = _scan_mode_config(scan_mode)

    candidate_limit: Optional[int] = None
    if args.get("candidate_limit") not in (None, ""):
        candidate_limit = min(
            int(mode_config.get("max_candidates") or MAX_SCAN_CANDIDATES),
            _coerce_positive_int(args.get("candidate_limit"), field_name="candidate_limit"),
        )
    elif mode_config.get("default_candidate_limit") is not None:
        candidate_limit = int(mode_config["default_candidate_limit"])

    fixed_datetime = str(args.get("fixed_datetime") or context_request.event_datetime or "").strip() or None
    start_datetime = str(args.get("start_datetime") or "").strip() or None
    end_datetime = str(args.get("end_datetime") or "").strip() or None
    time_step_hours = None
    if args.get("time_step_hours") not in (None, ""):
        time_step_hours = _coerce_positive_int(args.get("time_step_hours"), field_name="time_step_hours")

    if scan_mode == "spatial_scan":
        if not fixed_datetime:
            raise ValueError("spatial_scan requires fixed_datetime or event_datetime")
    else:
        if not start_datetime or not end_datetime:
            raise ValueError(f"{scan_mode} requires start_datetime and end_datetime")
        if time_step_hours is None:
            time_step_hours = int(mode_config.get("default_time_step_hours") or DEFAULT_TIME_STEP_HOURS)

    request_model = MundaneScanRequest(
        context_request=context_request,
        scan_mode=scan_mode,
        region_id=region_id,
        resolution=resolution,
        top_k=top_k,
        minimum_score=minimum_score,
        candidate_limit=candidate_limit,
        fixed_datetime=fixed_datetime,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        time_step_hours=time_step_hours,
    )
    timepoints = _scan_timepoints(request_model)
    resolution_settings = get_atlas_resolution_settings(resolution)
    candidate_bound = candidate_limit if candidate_limit is not None else int(resolution_settings.get("relocation_limit") or DEFAULT_SCAN_TOP_K)
    max_evaluated_cells = int(mode_config.get("max_evaluated_cells") or MAX_EVALUATED_CELLS)
    if len(timepoints) * candidate_bound > max_evaluated_cells:
        raise ValueError(
            f"Requested scan exceeds the current bound of {max_evaluated_cells} evaluated cells; reduce resolution, time slices, or candidate_limit"
        )
    return request_model


def get_scan_runtime_catalog() -> Dict[str, Any]:
    catalog = get_scan_catalog()
    catalog["supported_chart_types"] = sorted(SUPPORTED_SCAN_CHART_TYPES)
    catalog["supported_scan_modes"] = sorted(SUPPORTED_SCAN_MODES)
    catalog["max_top_k"] = MAX_SCAN_TOP_K
    catalog["max_candidates"] = MAX_SCAN_CANDIDATES
    catalog["max_time_slices"] = MAX_TIME_STEPS
    catalog["max_evaluated_cells"] = MAX_EVALUATED_CELLS
    catalog["scan_mode_limits"] = {mode_id: dict(config) for mode_id, config in SCAN_MODE_LIMITS.items()}
    chart_types = {
        _normalize_id(row.get("id")): dict(row)
        for row in mundane_service.get_runtime_catalog().get("chart_types") or []
        if _normalize_id(row.get("id"))
    }
    catalog["scan_chart_policy"] = {
        chart_type_id: {
            "status": "supported" if chart_type_id in SUPPORTED_SCAN_CHART_TYPES else "analysis_only",
            "reason": (
                "Scan-enabled with current chart-context semantics."
                if chart_type_id in SUPPORTED_SCAN_CHART_TYPES
                else (
                    "National-chart scan remains analysis-only because the current runtime fixes the reference chart and does not yet provide doctrinally clean spatial scan semantics."
                    if chart_type_id == "national_chart"
                    else "This chart type is not scan-enabled in the current runtime."
                )
            ),
            "label": str((chart_types.get(chart_type_id) or {}).get("label") or chart_type_id),
        }
        for chart_type_id in chart_types.keys()
    }
    return catalog


def _candidate_context_request(
    base_request: MundaneContextRequest,
    *,
    candidate: Dict[str, Any],
    event_datetime: str,
) -> MundaneContextRequest:
    city_label = str(candidate.get("label") or candidate.get("name") or "Unknown").strip()
    timezone_name = str(candidate.get("timezone") or base_request.event_timezone or "").strip() or None
    return replace(
        base_request,
        reference_location=city_label,
        reference_latitude=float(candidate.get("latitude") or 0.0),
        reference_longitude=float(candidate.get("longitude") or 0.0),
        event_datetime=event_datetime,
        event_location=city_label,
        event_timezone=timezone_name,
    )


def _scan_row(
    *,
    rank: int,
    candidate: Dict[str, Any],
    event_datetime: str,
    analysis: Any,
) -> Dict[str, Any]:
    assessment = analysis.domain_assessment or {}
    chart_resolution = (analysis.context.chart_resolution or {}) if analysis.context else {}
    return {
        "rank": rank,
        "location": {
            "label": str(candidate.get("label") or candidate.get("name") or "Unknown"),
            "latitude": float(candidate.get("latitude") or 0.0),
            "longitude": float(candidate.get("longitude") or 0.0),
            "country_code": candidate.get("country_code"),
            "country_name": candidate.get("country_name"),
            "timezone": candidate.get("timezone"),
        },
        "datetime": event_datetime,
        "score": float(assessment.get("score") or 0.0),
        "raw_score": float(assessment.get("raw_score") or 0.0),
        "level": assessment.get("level"),
        "raw_level": assessment.get("raw_level"),
        "scan_score": float(assessment.get("score") or 0.0),
        "scan_level": None,
        "scan_level_reason": None,
        "relative_score_ratio": None,
        "delta_from_top": None,
        "scan_bias": 0.0,
        "scan_bias_reason": None,
        "scan_anchor_distance_km": None,
        "summary": assessment.get("summary"),
        "matched_rules": assessment.get("matched_rules") or [],
        "primary_signals": chart_resolution.get("signals") or {},
        "calibration": assessment.get("calibration") or {},
        "research_flags": assessment.get("research_flags") or [],
        "primary_chart": (chart_resolution.get("primary_chart") or {}),
    }


def _apply_relative_scan_levels(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return rows
    top_score = max(_numeric_score(row, "scan_score") for row in rows)
    second_score = _numeric_score(rows[1], "scan_score") if len(rows) > 1 else 0.0
    min_score = min(_numeric_score(row, "scan_score") for row in rows)
    score_spread = max(0.0, top_score - min_score)
    top_gap = max(0.0, top_score - second_score)

    for index, row in enumerate(rows):
        score = _numeric_score(row, "scan_score")
        ratio = (score / top_score) if top_score > 0 else 0.0
        delta = max(0.0, top_score - score)
        scan_level = "background"
        reason = "No positive score separation was found in this scan cell."

        if top_score <= 0:
            scan_level = "background"
            reason = "All returned cells were effectively neutral after calibration."
        elif index == 0:
            if top_gap >= 8 or score_spread >= 12:
                scan_level = "dominant"
                reason = "This is the clearest hotspot in the returned scan, with a strong gap over the field."
            elif top_gap >= 4 or score_spread >= 6:
                scan_level = "leading"
                reason = "This cell leads the returned scan with visible but not overwhelming separation."
            else:
                scan_level = "co_leading" if len(rows) > 1 and second_score == top_score else "leading"
                reason = (
                    "This cell is at the front of the returned scan, but the field remains fairly compressed."
                    if scan_level == "leading"
                    else "This cell shares the top band with another returned candidate."
                )
        else:
            if ratio >= 0.9 or delta <= 1:
                scan_level = "co_leading"
                reason = "This cell remains very close to the scan leader."
            elif ratio >= 0.65 or delta <= 4:
                scan_level = "active"
                reason = "This cell is meaningfully active, but not at the top of the scan."
            elif score > 0:
                scan_level = "watch"
                reason = "This cell keeps some signal, but it sits behind the stronger candidates."
            else:
                scan_level = "background"
                reason = "This cell remains in the returned set but behaves like background pressure."

        row["scan_level"] = scan_level
        row["scan_level_reason"] = reason
        row["relative_score_ratio"] = round(ratio, 3)
        row["delta_from_top"] = round(delta, 3)
    return rows


def _scan_level_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        level = _normalize_id(row.get("scan_level"))
        if not level:
            continue
        counts[level] = int(counts.get(level) or 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-_scan_level_priority(item[0]), item[0])))


def _scan_sort_key(item: Mapping[str, Any]) -> Any:
    return (
        -float(item.get("scan_score") or 0.0),
        -float(item.get("score") or 0.0),
        -float(item.get("raw_score") or 0.0),
        -_priority(item.get("level")),
        -float(((item.get("calibration") or {}).get("unique_case_count") or 0.0)),
        str(((item.get("location") or {}).get("label") or "")),
        str(item.get("datetime") or ""),
    )


def _rank_scan_rows(rows: List[Dict[str, Any]], *, top_k: int) -> List[Dict[str, Any]]:
    diversified: List[Dict[str, Any]] = []
    remaining: List[Dict[str, Any]] = []
    seen_places: set[str] = set()
    for row in rows:
        place_key = _normalize_id(((row.get("location") or {}).get("label")))
        if place_key and place_key not in seen_places and len(diversified) < top_k:
            diversified.append(row)
            seen_places.add(place_key)
        else:
            remaining.append(row)

    selected_rows = diversified
    if len(selected_rows) < top_k:
        selected_rows.extend(remaining[: max(0, top_k - len(selected_rows))])

    ranked_rows: List[Dict[str, Any]] = []
    for index, row in enumerate(selected_rows[:top_k], start=1):
        updated = dict(row)
        updated["rank"] = index
        ranked_rows.append(updated)
    return _apply_relative_scan_levels(ranked_rows)


def _place_scan_sort_key(item: Mapping[str, Any]) -> Any:
    return (
        -float(item.get("breakout_index") or 0.0),
        -float(item.get("peak_scan_score") or 0.0),
        str(((item.get("location") or {}).get("label") or "")),
    )


def _place_diversity_group(item: Mapping[str, Any]) -> str:
    location = item.get("location") or {}
    country_code = str(location.get("country_code") or "").strip().upper()
    timezone_name = str(location.get("timezone") or "").strip()
    if country_code and timezone_name:
        return f"{country_code}:{timezone_name}"
    if timezone_name:
        return timezone_name
    try:
        longitude = float(location.get("longitude"))
    except Exception:
        longitude = None
    if country_code and longitude is not None:
        longitude_band = int((longitude + 180.0) // 15.0)
        return f"{country_code}:lonband:{longitude_band}"
    label = str(location.get("label") or "").strip()
    return label or "unknown"


def _order_places_for_discovery(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered_by_signal = sorted(places, key=_place_scan_sort_key)
    primary_theaters: List[Dict[str, Any]] = []
    same_theater_followups: List[Dict[str, Any]] = []
    seen_groups: set[str] = set()

    for place in ordered_by_signal:
        diversity_group = _place_diversity_group(place)
        updated = dict(place)
        updated["place_diversity_group"] = diversity_group
        if diversity_group not in seen_groups:
            updated["place_ranking_phase"] = "primary_theater"
            primary_theaters.append(updated)
            seen_groups.add(diversity_group)
        else:
            updated["place_ranking_phase"] = "same_theater_followup"
            same_theater_followups.append(updated)
    return primary_theaters + same_theater_followups


def _apply_relative_place_levels(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return rows
    breakout_values = sorted((float(row.get("breakout_index") or 0.0) for row in rows), reverse=True)
    top_breakout = breakout_values[0]
    second_breakout = breakout_values[1] if len(breakout_values) > 1 else 0.0
    min_breakout = breakout_values[-1]
    spread = max(0.0, top_breakout - min_breakout)
    gap = max(0.0, top_breakout - second_breakout)
    top_peak = max(float(row.get("peak_scan_score") or 0.0) for row in rows)

    for index, row in enumerate(rows):
        breakout = float(row.get("breakout_index") or 0.0)
        peak_score = float(row.get("peak_scan_score") or 0.0)
        ratio = (breakout / top_breakout) if top_breakout > 0 else 0.0
        peak_ratio = (peak_score / top_peak) if top_peak > 0 else 0.0
        delta = max(0.0, top_breakout - breakout)
        place_level = "background"
        reason = "No meaningful place-series separation was found in this scan."
        if top_breakout <= 0:
            place_level = "background"
            reason = "All returned places were effectively neutral after scan aggregation."
        elif index == 0:
            if gap >= 8 or spread >= 12:
                place_level = "dominant"
                reason = "This place leads the aggregated scan clearly after place-level deduping."
            elif gap >= 4 or spread >= 6:
                place_level = "leading"
                reason = "This place leads the aggregated scan with visible separation."
            else:
                place_level = "co_leading" if len(rows) > 1 and second_breakout == top_breakout else "leading"
                reason = (
                    "This place is at the front of the aggregated scan, but the field remains compressed."
                    if place_level == "leading"
                    else "This place shares the top breakout band with another returned place."
                )
        else:
            if ratio >= 0.9 or delta <= 1:
                place_level = "co_leading"
                reason = "This place stays very close to the top breakout band."
            elif ratio >= 0.65 or delta <= 4:
                place_level = "active"
                reason = "This place remains materially active after place-series aggregation."
            elif breakout > 0:
                place_level = "watch"
                reason = "This place retains some pressure, but it sits behind the stronger locations."

        row["place_scan_level"] = place_level
        row["place_scan_level_reason"] = reason
        row["relative_breakout_ratio"] = round(ratio, 3)
        row["relative_peak_ratio"] = round(peak_ratio, 3)
        row["delta_from_top_breakout"] = round(delta, 3)
    return rows


def _rank_top_places(places: List[Dict[str, Any]], *, top_k: int) -> List[Dict[str, Any]]:
    ranked_places: List[Dict[str, Any]] = []
    for index, place in enumerate(_order_places_for_discovery(places)[:top_k], start=1):
        ranked_places.append(
            {
                "rank": index,
                "location": place.get("location"),
                "breakout_index": round(float(place.get("breakout_index") or 0.0), 3),
                "breakout_kind": place.get("breakout_kind"),
                "breakout_datetime": place.get("breakout_datetime"),
                "peak_scan_score": round(float(place.get("peak_scan_score") or 0.0), 3),
                "peak_datetime": place.get("peak_datetime"),
                "peak_window_start_datetime": place.get("peak_window_start_datetime"),
                "peak_window_end_datetime": place.get("peak_window_end_datetime"),
                "peak_selection": place.get("peak_selection"),
                "peak_level": place.get("peak_level"),
                "first_active_datetime": place.get("first_active_datetime"),
                "place_diversity_group": place.get("place_diversity_group"),
                "place_ranking_phase": place.get("place_ranking_phase"),
            }
        )
    return _apply_relative_place_levels(ranked_places)


def _series_cell(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "datetime": row.get("datetime"),
        "scan_score": float(row.get("scan_score") or 0.0),
        "absolute_score": float(row.get("score") or 0.0),
        "scan_level": row.get("scan_level"),
        "absolute_level": row.get("level"),
        "summary": row.get("summary"),
    }


def _empty_series_cell(event_datetime: str) -> Dict[str, Any]:
    return {
        "datetime": event_datetime,
        "scan_score": 0.0,
        "absolute_score": 0.0,
        "scan_level": "background",
        "absolute_level": "quiet",
        "summary": None,
    }


def _contiguous_index_groups(indices: List[int]) -> List[List[int]]:
    if not indices:
        return []
    groups: List[List[int]] = [[indices[0]]]
    for index in indices[1:]:
        current = groups[-1]
        if index == current[-1] + 1:
            current.append(index)
        else:
            groups.append([index])
    return groups


def _select_series_peak(series: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not series:
        return {
            "peak_index": None,
            "peak_score": 0.0,
            "peak_point": None,
            "peak_datetime": None,
            "peak_selection": "no_peak",
            "peak_window_start_datetime": None,
            "peak_window_end_datetime": None,
        }

    scores = [float(point.get("scan_score") or 0.0) for point in series]
    peak_score = max(scores)
    if peak_score <= 0:
        return {
            "peak_index": None,
            "peak_score": 0.0,
            "peak_point": None,
            "peak_datetime": None,
            "peak_selection": "no_peak",
            "peak_window_start_datetime": None,
            "peak_window_end_datetime": None,
        }

    peak_indices = [index for index, score in enumerate(scores) if abs(score - peak_score) <= SERIES_PEAK_EPSILON]
    groups = _contiguous_index_groups(peak_indices)
    midpoint = (len(series) - 1) / 2.0
    selected_group = min(
        groups,
        key=lambda group: (
            -len(group),
            abs((((group[0] + group[-1]) / 2.0) - midpoint)),
            group[0],
        ),
    )
    representative_index = selected_group[len(selected_group) // 2]
    if len(peak_indices) == 1:
        selection = "single_peak"
    elif len(selected_group) > 1:
        selection = "peak_plateau"
    else:
        selection = "recurring_equal_peaks"
    representative_point = series[representative_index]
    return {
        "peak_index": representative_index,
        "peak_score": peak_score,
        "peak_point": representative_point,
        "peak_datetime": representative_point.get("datetime"),
        "peak_selection": selection,
        "peak_window_start_datetime": series[selected_group[0]].get("datetime"),
        "peak_window_end_datetime": series[selected_group[-1]].get("datetime"),
    }


def _build_series_payload(
    rows: List[Dict[str, Any]],
    *,
    timepoints: List[str],
    request_model: MundaneScanRequest,
) -> Dict[str, Any]:
    graph_place_limit = min(max(int(request_model.top_k or DEFAULT_SCAN_TOP_K), 6), 10)
    if not rows:
        return {
            "timeline": list(timepoints),
            "places": [],
            "graph_places": [],
            "breakout_candidates": [],
            "series_overview": {
                "timeline_points": len(timepoints),
                "place_count": 0,
                "graph_place_limit": graph_place_limit,
                "top_peak_location": None,
                "top_breakout_location": None,
            },
        }

    rows_with_levels = _apply_relative_scan_levels([dict(row) for row in rows])
    place_map: Dict[str, Dict[str, Any]] = {}
    for row in rows_with_levels:
        location = dict(row.get("location") or {})
        label = str(location.get("label") or "Unknown").strip() or "Unknown"
        entry = place_map.get(label)
        if entry is None:
            entry = {
                "location": location,
                "cells": {},
            }
            place_map[label] = entry
        entry["cells"][str(row.get("datetime") or "")] = row

    places: List[Dict[str, Any]] = []
    last_index = max(len(timepoints) - 1, 1)
    for label, entry in place_map.items():
        cells = entry["cells"]
        series = [_series_cell(cells[timepoint]) if timepoint in cells else _empty_series_cell(timepoint) for timepoint in timepoints]
        peak_selection = _select_series_peak(series)
        peak_index = peak_selection["peak_index"]
        peak_score = float(peak_selection["peak_score"] or 0.0)
        peak_point = peak_selection["peak_point"] or _empty_series_cell(timepoints[0] if timepoints else "")
        active_threshold = max(8.0, peak_score * 0.55) if peak_score > 0 else 0.0
        first_active_index = None
        for index, point in enumerate(series):
            if float(point.get("scan_score") or 0.0) >= active_threshold and float(point.get("scan_score") or 0.0) > 0:
                first_active_index = index
                break
        baseline_score = float(series[0].get("scan_score") or 0.0)
        breakout_rise = max(0.0, peak_score - baseline_score)
        timing_factor = 1.0
        if peak_index is not None:
            timing_factor = 1.0 - (peak_index / last_index) * 0.35
        breakout_index = round(max(0.0, (peak_score * timing_factor) + (breakout_rise * 0.45)), 3)
        if peak_score <= 0:
            breakout_kind = "background"
        elif peak_selection["peak_selection"] in {"peak_plateau", "recurring_equal_peaks"} and breakout_rise <= SERIES_PEAK_EPSILON:
            breakout_kind = "sustained_theater_candidate"
        elif first_active_index is not None and first_active_index <= max(1, len(timepoints) // 4):
            breakout_kind = "opening_break_candidate"
        elif peak_index is not None and peak_index >= max(1, int(len(timepoints) * 0.66)):
            breakout_kind = "late_campaign_pressure"
        else:
            breakout_kind = "sustained_theater_candidate"
        breakout_datetime = peak_selection["peak_datetime"]
        if breakout_kind == "opening_break_candidate" and first_active_index is not None:
            breakout_datetime = series[first_active_index].get("datetime")
        places.append(
            {
                "location": entry["location"],
                "peak_scan_score": round(peak_score, 3),
                "peak_datetime": peak_selection["peak_datetime"],
                "peak_window_start_datetime": peak_selection["peak_window_start_datetime"],
                "peak_window_end_datetime": peak_selection["peak_window_end_datetime"],
                "peak_selection": peak_selection["peak_selection"],
                "peak_level": peak_point.get("scan_level"),
                "first_active_datetime": series[first_active_index].get("datetime") if first_active_index is not None else None,
                "breakout_index": breakout_index,
                "breakout_kind": breakout_kind,
                "breakout_datetime": breakout_datetime,
                "series": series,
            }
        )

    places = _order_places_for_discovery(places)
    graph_places = places[:graph_place_limit]

    breakout_candidates = [
        {
            "rank": index,
            "location": place.get("location"),
            "breakout_index": place.get("breakout_index"),
            "breakout_kind": place.get("breakout_kind"),
            "first_active_datetime": place.get("first_active_datetime"),
            "breakout_datetime": place.get("breakout_datetime"),
            "peak_datetime": place.get("peak_datetime"),
            "peak_window_start_datetime": place.get("peak_window_start_datetime"),
            "peak_window_end_datetime": place.get("peak_window_end_datetime"),
            "peak_selection": place.get("peak_selection"),
            "peak_scan_score": place.get("peak_scan_score"),
            "peak_level": place.get("peak_level"),
            "place_diversity_group": place.get("place_diversity_group"),
            "place_ranking_phase": place.get("place_ranking_phase"),
        }
        for index, place in enumerate(graph_places[:5], start=1)
    ]

    top_peak = max(places, key=lambda item: float(item.get("peak_scan_score") or 0.0), default=None)
    top_breakout = places[0] if places else None
    return {
        "timeline": list(timepoints),
        "places": places,
        "graph_places": graph_places,
        "breakout_candidates": breakout_candidates,
        "series_overview": {
            "timeline_points": len(timepoints),
            "place_count": len(places),
            "graph_place_limit": graph_place_limit,
            "top_peak_location": (top_peak or {}).get("location"),
            "top_peak_datetime": (top_peak or {}).get("peak_datetime"),
            "top_peak_scan_score": (top_peak or {}).get("peak_scan_score"),
            "top_breakout_location": (top_breakout or {}).get("location"),
            "top_breakout_datetime": (top_breakout or {}).get("breakout_datetime"),
            "top_breakout_index": (top_breakout or {}).get("breakout_index"),
        },
    }


def _evaluate_scan_cells(
    request_model: MundaneScanRequest,
    *,
    active_clock: ActiveClockContext,
    bundle_resolver=None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    region = describe_region(request_model.region_id)
    anchor = _scan_anchor(request_model)
    _emit_progress(
        progress_callback,
        stage="prepare_scan",
        percent=0.02,
        message=f"Preparing {region.get('label') or 'selected region'} scan",
    )
    timepoints = _scan_timepoints(request_model)
    candidate_limit = request_model.candidate_limit
    candidates = collect_region_candidates(
        request_model.region_id,
        resolution=request_model.resolution,
        limit=candidate_limit,
    )
    if not candidates:
        raise ValueError("No atlas candidates were found for the selected region and resolution")

    mode_config = _scan_mode_config(request_model.scan_mode)
    max_evaluated_cells = int(mode_config.get("max_evaluated_cells") or MAX_EVALUATED_CELLS)
    if len(candidates) * len(timepoints) > max_evaluated_cells:
        raise ValueError(
            f"Resolved scan would evaluate {len(candidates) * len(timepoints)} cells, exceeding the bound of {max_evaluated_cells}"
        )

    total_cells = len(candidates) * len(timepoints)
    _emit_progress(
        progress_callback,
        stage="evaluate_cells",
        percent=0.08,
        message="Candidate pool ready",
        done=0,
        total=total_cells,
        candidate_count=len(candidates),
        time_slices=len(timepoints),
        region_id=region.get("id"),
        resolution=request_model.resolution,
    )

    rows: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    evaluated_cells = 0
    kept_cells = 0

    for event_datetime in timepoints:
        for candidate in candidates:
            evaluated_cells += 1
            cell_request = _candidate_context_request(
                request_model.context_request,
                candidate=candidate,
                event_datetime=event_datetime,
            )
            try:
                resolved = mundane_service.resolve_context(
                    cell_request,
                    active_clock=active_clock,
                    bundle_resolver=bundle_resolver,
                )
                analysis = mundane_service.analyze_context(resolved)
            except Exception as exc:
                failures.append(
                    {
                        "location": str(candidate.get("label") or candidate.get("name") or "Unknown"),
                        "datetime": event_datetime,
                        "error": str(exc),
                    }
                )
                _emit_progress(
                    progress_callback,
                    stage="evaluate_cells",
                    percent=0.08 + (0.84 * (evaluated_cells / max(total_cells, 1))),
                    message="Scanning region cells",
                    done=evaluated_cells,
                    total=total_cells,
                    kept_cells=kept_cells,
                    failures=len(failures),
                )
                continue

            row = _scan_row(
                rank=0,
                candidate=candidate,
                event_datetime=event_datetime,
                analysis=analysis,
            )
            modifier = _war_scan_modifier(
                request_model,
                candidate=candidate,
                anchor=anchor,
            )
            row["scan_bias"] = float(modifier.get("scan_bias") or 0.0)
            row["scan_bias_reason"] = modifier.get("scan_bias_reason")
            row["scan_anchor_distance_km"] = modifier.get("scan_anchor_distance_km")
            row["scan_score"] = round(max(0.0, float(row.get("score") or 0.0) + float(row.get("scan_bias") or 0.0)), 3)
            if float(row.get("score") or 0.0) < float(request_model.minimum_score):
                _emit_progress(
                    progress_callback,
                    stage="evaluate_cells",
                    percent=0.08 + (0.84 * (evaluated_cells / max(total_cells, 1))),
                    message="Scanning region cells",
                    done=evaluated_cells,
                    total=total_cells,
                    kept_cells=kept_cells,
                    failures=len(failures),
                )
                continue
            rows.append(row)
            kept_cells += 1
            _emit_progress(
                progress_callback,
                stage="evaluate_cells",
                percent=0.08 + (0.84 * (evaluated_cells / max(total_cells, 1))),
                message="Scanning region cells",
                done=evaluated_cells,
                total=total_cells,
                kept_cells=kept_cells,
                failures=len(failures),
            )

    rows.sort(key=_scan_sort_key)
    return {
        "region": region,
        "timepoints": timepoints,
        "candidates": candidates,
        "rows": rows,
        "failures": failures,
        "evaluated_cells": evaluated_cells,
        "kept_cells": kept_cells,
    }


def run_scan(
    request_model: MundaneScanRequest,
    *,
    active_clock: ActiveClockContext,
    bundle_resolver=None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    include_series: bool = False,
) -> Dict[str, Any]:
    scan_state = _evaluate_scan_cells(
        request_model,
        active_clock=active_clock,
        bundle_resolver=bundle_resolver,
        progress_callback=progress_callback,
    )
    region = scan_state["region"]
    timepoints = scan_state["timepoints"]
    candidates = scan_state["candidates"]
    rows = scan_state["rows"]
    failures = scan_state["failures"]
    evaluated_cells = int(scan_state["evaluated_cells"] or 0)
    kept_cells = int(scan_state["kept_cells"] or 0)
    total_cells = len(candidates) * len(timepoints)

    series_payload = _build_series_payload(
        rows,
        timepoints=timepoints,
        request_model=request_model,
    )
    top_places = _rank_top_places(series_payload.get("places") or [], top_k=request_model.top_k)
    ranked_rows = _rank_scan_rows(rows, top_k=request_model.top_k)
    primary_ranking_mode = "places" if len(timepoints) > 1 else "cells"

    result = {
        "scan_mode": request_model.scan_mode,
        "region": region,
        "resolution": get_atlas_resolution_settings(request_model.resolution),
        "request": request_model.to_dict(),
        "counts": {
            "candidate_locations": len(candidates),
            "time_slices": len(timepoints),
            "evaluated_cells": evaluated_cells,
            "kept_cells": kept_cells,
            "returned": len(ranked_rows),
            "returned_places": len(top_places),
            "failures": len(failures),
        },
        "scan_calibration": {
            "top_scan_score": float(ranked_rows[0].get("scan_score") or 0.0) if ranked_rows else 0.0,
            "top_absolute_score": float(ranked_rows[0].get("score") or 0.0) if ranked_rows else 0.0,
            "returned_score_spread": round(
                max((float(row.get("scan_score") or 0.0) for row in ranked_rows), default=0.0)
                - min((float(row.get("scan_score") or 0.0) for row in ranked_rows), default=0.0),
                3,
            ),
            "top_breakout_index": float(top_places[0].get("breakout_index") or 0.0) if top_places else 0.0,
            "scan_level_counts": _scan_level_counts(ranked_rows),
        },
        "primary_ranking_mode": primary_ranking_mode,
        "default_output_view": "graph" if include_series and primary_ranking_mode == "places" else "cells",
        "top_cells": ranked_rows,
        "top_places": top_places,
        "results": ranked_rows,
        "failures": failures[:10],
        "research_mode": True,
        "runtime_scope": "computed_chart_context",
    }
    if include_series:
        result["series"] = series_payload
    _emit_progress(
        progress_callback,
        stage="finalize_scan",
        percent=1.0,
        message="Mundane scan complete",
        done=evaluated_cells,
        total=total_cells,
        kept_cells=kept_cells,
        returned=len(ranked_rows),
        failures=len(failures),
    )
    return result
