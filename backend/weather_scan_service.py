from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional
from zoneinfo import ZoneInfo

from astrocartography_city_catalog import get_atlas_resolution_settings, normalize_atlas_resolution
from horary_engine.services.geolocation import TimezoneManager, safe_geocode, search_live_location_candidates
from mundane_models import ActiveClockContext
from mundane_scan_grid import collect_region_candidates, get_scan_region_definitions, get_scan_catalog
from weather_benchmark_profiles import get_weather_family_profile
from weather_models import WeatherContextRequest
from weather_scan_models import WeatherScanRequest
from weather_service import analyze_weather_context, get_runtime_catalog, resolve_weather_context


SUPPORTED_WEATHER_SCAN_SCOPES = {"place_timeline", "region_timeline"}
DEFAULT_WEATHER_SCAN_TOP_K = 8
MAX_WEATHER_SCAN_TOP_K = 20
DEFAULT_WEATHER_SCAN_STEP_HOURS = 6
DEFAULT_WEATHER_SCAN_CANDIDATES = 6
MAX_WEATHER_SCAN_CANDIDATES = 20
MAX_WEATHER_SCAN_TIME_SLICES = 120
MAX_WEATHER_SCAN_EVALUATED_CELLS = 720
WEATHER_SERIES_PEAK_EPSILON = 1e-6

_timezone_manager = TimezoneManager()


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


def _coerce_positive_int(value: Any, *, field_name: str) -> int:
    try:
        parsed = int(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return parsed


def _coerce_optional_float(value: Any, *, field_name: str) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be a number") from exc


def _parse_datetime(value: Any, *, field_name: str, timezone_name: Optional[str] = None) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{field_name} is required")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError(f"{field_name} must be ISO-8601 compatible") from exc
    if parsed.tzinfo is None:
        tzinfo = timezone.utc
        if timezone_name:
            try:
                tzinfo = ZoneInfo(str(timezone_name))
            except Exception:
                tzinfo = timezone.utc
        parsed = parsed.replace(tzinfo=tzinfo)
    return parsed.astimezone(timezone.utc)


def _scan_timepoints(request_model: WeatherScanRequest) -> List[str]:
    timezone_name = request_model.timezone if request_model.scan_scope == "place_timeline" else None
    start = _parse_datetime(request_model.start_datetime, field_name="start_datetime", timezone_name=timezone_name)
    end = _parse_datetime(request_model.end_datetime, field_name="end_datetime", timezone_name=timezone_name)
    if end <= start:
        raise ValueError("end_datetime must be later than start_datetime")
    step_hours = int(request_model.time_step_hours or DEFAULT_WEATHER_SCAN_STEP_HOURS)
    points: List[str] = []
    current = start
    step = timedelta(hours=step_hours)
    while current <= end:
        points.append(current.isoformat())
        if len(points) > MAX_WEATHER_SCAN_TIME_SLICES:
            raise ValueError(f"Weather scan is limited to {MAX_WEATHER_SCAN_TIME_SLICES} time slices")
        current += step
    return points


def _resolve_place_candidate(
    location: str,
    timezone_name: Optional[str],
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Dict[str, Any]:
    if latitude is not None and longitude is not None:
        resolved_timezone = timezone_name
        if not resolved_timezone:
            try:
                resolved_timezone = _timezone_manager.get_timezone_for_location(latitude, longitude)
            except Exception:
                resolved_timezone = None
        return {
            "label": str(location or f"{latitude:.4f}, {longitude:.4f}").strip(),
            "name": str(location or f"{latitude:.4f}, {longitude:.4f}").strip(),
            "ascii_name": str(location or f"{latitude:.4f}, {longitude:.4f}").strip(),
            "latitude": round(float(latitude), 6),
            "longitude": round(float(longitude), 6),
            "country_name": "",
            "country_code": "",
            "timezone": resolved_timezone,
            "population": 0,
            "feature_code": "BENCHMARK",
        }

    live = search_live_location_candidates(location, limit=1)
    if live:
        candidate = dict(live[0])
        if not candidate.get("timezone"):
            try:
                candidate["timezone"] = _timezone_manager.get_timezone_for_location(
                    float(candidate.get("latitude") or 0.0),
                    float(candidate.get("longitude") or 0.0),
                )
            except Exception:
                candidate["timezone"] = None
        if timezone_name:
            candidate["timezone"] = timezone_name
        candidate["label"] = str(candidate.get("label") or candidate.get("name") or location).strip()
        return candidate

    latitude, longitude, address = safe_geocode(location)
    resolved_timezone = timezone_name
    if not resolved_timezone:
        try:
            resolved_timezone = _timezone_manager.get_timezone_for_location(latitude, longitude)
        except Exception:
            resolved_timezone = None
    address_text = str(address or location).strip()
    address_parts = [part.strip() for part in address_text.split(",") if part.strip()]
    country_name = address_parts[-1] if address_parts else ""
    return {
        "label": address_text or str(location).strip(),
        "name": address_parts[0] if address_parts else str(location).strip(),
        "ascii_name": address_parts[0] if address_parts else str(location).strip(),
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "country_name": country_name,
        "country_code": "",
        "timezone": resolved_timezone,
        "population": 0,
        "feature_code": "LIVE",
    }


def build_weather_scan_request(args: Mapping[str, Any]) -> WeatherScanRequest:
    family_id = _normalize_id(args.get("family_id") or args.get("weather_family") or args.get("family"))
    if not family_id:
        raise ValueError("family_id is required")
    family_catalog = {str(row.get("id") or "") for row in get_runtime_catalog().get("families") or []}
    if family_id not in family_catalog:
        raise ValueError(f"Unsupported weather family: {family_id}")

    scan_scope = _normalize_id(args.get("scan_scope") or "place_timeline")
    if scan_scope not in SUPPORTED_WEATHER_SCAN_SCOPES:
        raise ValueError(f"Unsupported scan_scope: {scan_scope}")

    top_k = DEFAULT_WEATHER_SCAN_TOP_K
    if args.get("top_k") not in (None, ""):
        top_k = min(MAX_WEATHER_SCAN_TOP_K, _coerce_positive_int(args.get("top_k"), field_name="top_k"))

    time_step_hours = DEFAULT_WEATHER_SCAN_STEP_HOURS
    if args.get("time_step_hours") not in (None, ""):
        time_step_hours = _coerce_positive_int(args.get("time_step_hours"), field_name="time_step_hours")

    resolution = normalize_atlas_resolution(args.get("resolution"))
    candidate_limit = None
    if args.get("candidate_limit") not in (None, ""):
        candidate_limit = min(MAX_WEATHER_SCAN_CANDIDATES, _coerce_positive_int(args.get("candidate_limit"), field_name="candidate_limit"))

    location = str(args.get("location") or "").strip() or None
    timezone_name = str(args.get("timezone") or "").strip() or None
    region_id = str(args.get("region_id") or "").strip() or None
    if scan_scope == "place_timeline":
        if not location:
            raise ValueError("location is required for place_timeline")
    else:
        if not region_id:
            raise ValueError("region_id is required for region_timeline")

    request_model = WeatherScanRequest(
        family_id=family_id,
        scan_scope=scan_scope,
        start_datetime=str(args.get("start_datetime") or "").strip(),
        end_datetime=str(args.get("end_datetime") or "").strip(),
        time_step_hours=time_step_hours,
        top_k=top_k,
        location=location,
        timezone=timezone_name,
        latitude=_coerce_optional_float(args.get("latitude"), field_name="latitude"),
        longitude=_coerce_optional_float(args.get("longitude"), field_name="longitude"),
        region_id=region_id,
        resolution=resolution,
        candidate_limit=candidate_limit,
        house_system_code=str(args.get("house_system_code") or "").strip() or None,
        source_preference=str(args.get("source_preference") or "").strip() or None,
    )

    timepoints = _scan_timepoints(request_model)
    resolution_settings = get_atlas_resolution_settings(resolution)
    candidate_bound = 1 if scan_scope == "place_timeline" else (
        candidate_limit if candidate_limit is not None else int(resolution_settings.get("relocation_limit") or DEFAULT_WEATHER_SCAN_CANDIDATES)
    )
    if len(timepoints) * candidate_bound > MAX_WEATHER_SCAN_EVALUATED_CELLS:
        raise ValueError(
            f"Requested weather scan exceeds the current bound of {MAX_WEATHER_SCAN_EVALUATED_CELLS} evaluated cells; reduce candidates, time slices, or resolution"
        )
    return request_model


def _candidate_pool(request_model: WeatherScanRequest) -> List[Dict[str, Any]]:
    if request_model.scan_scope == "place_timeline":
        return [
            _resolve_place_candidate(
                str(request_model.location or ""),
                request_model.timezone,
                latitude=request_model.latitude,
                longitude=request_model.longitude,
            )
        ]
    return collect_region_candidates(
        str(request_model.region_id or ""),
        resolution=request_model.resolution,
        limit=request_model.candidate_limit,
    )


def _relative_scan_level_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    top_score = max(float(row.get("score") or 0.0) for row in rows)
    top_count = sum(1 for row in rows if abs(float(row.get("score") or 0.0) - top_score) <= WEATHER_SERIES_PEAK_EPSILON)
    ranked_scores = sorted({float(row.get("score") or 0.0) for row in rows}, reverse=True)
    second_score = ranked_scores[1] if len(ranked_scores) > 1 else 0.0
    normalized_rows: List[Dict[str, Any]] = []
    for row in rows:
        score = float(row.get("score") or 0.0)
        ratio = (score / top_score) if top_score > 0 else 0.0
        if score <= 0:
            scan_level = "background"
        elif abs(score - top_score) <= WEATHER_SERIES_PEAK_EPSILON:
            scan_level = "dominant" if top_count == 1 and (top_score - second_score) > WEATHER_SERIES_PEAK_EPSILON else "co_leading"
        elif ratio >= 0.85:
            scan_level = "leading"
        elif ratio >= 0.6:
            scan_level = "active"
        elif ratio >= 0.35:
            scan_level = "watch"
        else:
            scan_level = "background"
        next_row = dict(row)
        next_row["scan_level"] = scan_level
        next_row["relative_score_ratio"] = round(ratio, 4)
        normalized_rows.append(next_row)
    return normalized_rows


def _sort_key(row: Mapping[str, Any]) -> tuple:
    return (
        -float(row.get("score") or 0.0),
        -float(row.get("event_focus") or 0.0),
        -float((((row.get("signals") or {}).get("locality_strength")) or 0.0)),
        str(row.get("datetime") or ""),
        str(((row.get("location") or {}).get("label") or "")),
    )


def _series_cell(row: Mapping[str, Any]) -> Dict[str, Any]:
    signals = dict(row.get("signals") or {})
    return {
        "datetime": row.get("datetime"),
        "score": round(float(row.get("score") or 0.0), 3),
        "raw_score": round(float(row.get("raw_score") or row.get("score") or 0.0), 3),
        "level": row.get("level"),
        "scan_level": row.get("scan_level"),
        "relative_score_ratio": row.get("relative_score_ratio"),
        "locality_strength": round(float(signals.get("locality_strength") or 0.0), 3),
        "path_concentration": round(float(signals.get("path_concentration") or 0.0), 3),
        "tight_hit_count": int(signals.get("tight_hit_count") or 0),
        "event_focus": round(float(row.get("event_focus") or 0.0), 3),
    }


def _empty_series_cell(datetime_value: str) -> Dict[str, Any]:
    return {
        "datetime": datetime_value,
        "score": 0.0,
        "raw_score": 0.0,
        "level": "quiet",
        "scan_level": "background",
        "relative_score_ratio": 0.0,
        "locality_strength": 0.0,
        "path_concentration": 0.0,
        "tight_hit_count": 0,
        "event_focus": 0.0,
    }


def _contiguous_index_groups(indices: List[int]) -> List[List[int]]:
    if not indices:
        return []
    groups: List[List[int]] = [[indices[0]]]
    for index in indices[1:]:
        if index == groups[-1][-1] + 1:
            groups[-1].append(index)
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
    scores = [float(point.get("score") or 0.0) for point in series]
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
    peak_indices = [index for index, score in enumerate(scores) if abs(score - peak_score) <= WEATHER_SERIES_PEAK_EPSILON]
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
    peak_window_start = series[selected_group[0]].get("datetime")
    peak_window_end = series[selected_group[-1]].get("datetime")
    return {
        "peak_index": representative_index,
        "peak_score": peak_score,
        "peak_point": representative_point,
        "peak_datetime": representative_point.get("datetime"),
        "peak_selection": selection,
        "peak_window_start_datetime": peak_window_start if selection != "recurring_equal_peaks" else series[peak_indices[0]].get("datetime"),
        "peak_window_end_datetime": peak_window_end if selection != "recurring_equal_peaks" else series[peak_indices[-1]].get("datetime"),
        "peak_group_count": len(groups),
        "peak_window_width_steps": (selected_group[-1] - selected_group[0] + 1) if selected_group else 0,
        "peak_occurrence_count": len(peak_indices),
    }


def _build_series_payload(rows: List[Dict[str, Any]], *, timepoints: List[str], top_k: int) -> Dict[str, Any]:
    graph_place_limit = min(max(int(top_k or DEFAULT_WEATHER_SCAN_TOP_K), 4), 10)
    if not rows:
        return {
            "timeline": list(timepoints),
            "places": [],
            "peak_candidates": [],
            "series_overview": {
                "timeline_points": len(timepoints),
                "place_count": 0,
                "graph_place_limit": graph_place_limit,
                "top_peak_location": None,
                "top_peak_datetime": None,
                "top_peak_score": 0.0,
            },
        }

    rows_with_levels = _relative_scan_level_rows([dict(row) for row in rows])
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
    for entry in place_map.values():
        cells = entry["cells"]
        series = [_series_cell(cells[timepoint]) if timepoint in cells else _empty_series_cell(timepoint) for timepoint in timepoints]
        peak_selection = _select_series_peak(series)
        peak_index = peak_selection["peak_index"]
        peak_score = float(peak_selection["peak_score"] or 0.0)
        baseline_score = float(series[0].get("score") or 0.0)
        rise = max(0.0, peak_score - baseline_score)
        score_values = [float(point.get("score") or 0.0) for point in series]
        mean_score = (sum(score_values) / len(score_values)) if score_values else 0.0
        peak_sharpness = round(max(0.0, peak_score - mean_score), 3)
        peak_cells = [point for point in series if abs(float(point.get("score") or 0.0) - peak_score) <= WEATHER_SERIES_PEAK_EPSILON]
        peak_locality_strength = max((float(point.get("locality_strength") or 0.0) for point in peak_cells), default=0.0)
        peak_path_concentration = max((float(point.get("path_concentration") or 0.0) for point in peak_cells), default=0.0)
        peak_window_width_steps = int(peak_selection.get("peak_window_width_steps") or 0)
        plateau_penalty = 0.0
        if peak_selection["peak_selection"] == "peak_plateau":
            plateau_penalty = min(6.0, max(0.0, peak_window_width_steps - 1) * 1.2)
        elif peak_selection["peak_selection"] == "recurring_equal_peaks":
            plateau_penalty = min(8.0, max(0.0, int(peak_selection.get("peak_occurrence_count") or 0) - 1) * 1.0)
        timing_factor = 1.0
        if peak_index is not None:
            timing_factor = 1.0 - (peak_index / last_index) * 0.3
        event_focus_index = round(
            max(
                0.0,
                peak_sharpness
                + (peak_locality_strength * 0.35)
                + (peak_path_concentration * 0.55)
                - plateau_penalty,
            ),
            3,
        )
        candidate_index = round(max(0.0, (peak_score * timing_factor) + (rise * 0.35) + event_focus_index), 3)
        if peak_score <= 0:
            candidate_kind = "background"
        elif peak_selection["peak_selection"] in {"peak_plateau", "recurring_equal_peaks"} and event_focus_index <= 8.0:
            candidate_kind = "sustained_window"
        elif peak_index is not None and peak_index <= max(1, len(timepoints) // 4) and event_focus_index >= 10.0:
            candidate_kind = "early_peak_candidate"
        elif peak_index is not None and peak_index >= max(1, int(len(timepoints) * 0.66)) and event_focus_index >= 10.0:
            candidate_kind = "late_window_candidate"
        else:
            candidate_kind = "mid_window_candidate"
        places.append(
            {
                "location": entry["location"],
                "peak_score": round(peak_score, 3),
                "peak_datetime": peak_selection["peak_datetime"],
                "peak_window_start_datetime": peak_selection["peak_window_start_datetime"],
                "peak_window_end_datetime": peak_selection["peak_window_end_datetime"],
                "peak_selection": peak_selection["peak_selection"],
                "peak_group_count": peak_selection.get("peak_group_count"),
                "peak_window_width_steps": peak_window_width_steps,
                "peak_occurrence_count": peak_selection.get("peak_occurrence_count"),
                "peak_sharpness": peak_sharpness,
                "peak_locality_strength": round(peak_locality_strength, 3),
                "peak_path_concentration": round(peak_path_concentration, 3),
                "event_focus_index": event_focus_index,
                "candidate_index": candidate_index,
                "candidate_kind": candidate_kind,
                "series": series,
            }
        )

    places.sort(
        key=lambda item: (
            -float(item.get("candidate_index") or 0.0),
            -float(item.get("peak_score") or 0.0),
            str(((item.get("location") or {}).get("label") or "")),
        )
    )
    places = places[:graph_place_limit]

    peak_candidates = [
        {
            "rank": index,
            "location": place.get("location"),
            "candidate_index": place.get("candidate_index"),
            "candidate_kind": place.get("candidate_kind"),
            "peak_datetime": place.get("peak_datetime"),
            "peak_window_start_datetime": place.get("peak_window_start_datetime"),
            "peak_window_end_datetime": place.get("peak_window_end_datetime"),
            "peak_selection": place.get("peak_selection"),
            "peak_score": place.get("peak_score"),
            "event_focus_index": place.get("event_focus_index"),
            "peak_locality_strength": place.get("peak_locality_strength"),
            "peak_path_concentration": place.get("peak_path_concentration"),
        }
        for index, place in enumerate(places[:5], start=1)
    ]

    top_peak = max(places, key=lambda item: float(item.get("peak_score") or 0.0), default=None)
    top_candidate = places[0] if places else None
    return {
        "timeline": list(timepoints),
        "places": places,
        "peak_candidates": peak_candidates,
        "series_overview": {
            "timeline_points": len(timepoints),
            "place_count": len(places),
            "graph_place_limit": graph_place_limit,
            "ranking_mode": "event_focus_weighted",
            "top_peak_location": (top_peak or {}).get("location"),
            "top_peak_datetime": (top_peak or {}).get("peak_datetime"),
            "top_peak_score": (top_peak or {}).get("peak_score"),
            "top_candidate_location": (top_candidate or {}).get("location"),
            "top_candidate_datetime": (top_candidate or {}).get("peak_datetime"),
            "top_candidate_index": (top_candidate or {}).get("candidate_index"),
        },
    }


def get_weather_scan_catalog() -> Dict[str, Any]:
    catalog = get_scan_catalog()
    weather_catalog = get_runtime_catalog()
    return {
        "scan_scopes": [
            {"id": "place_timeline", "label": "Specific Place", "summary": "Scan one place across a bounded time window."},
            {"id": "region_timeline", "label": "Region", "summary": "Scan a bounded atlas region across place and time."},
        ],
        "regions": get_scan_region_definitions(),
        "resolutions": catalog.get("resolutions") or [],
        "default_resolution": catalog.get("default_resolution"),
        "families": weather_catalog.get("families") or [],
        "default_time_step_hours": DEFAULT_WEATHER_SCAN_STEP_HOURS,
        "default_top_k": DEFAULT_WEATHER_SCAN_TOP_K,
        "default_candidate_limit": DEFAULT_WEATHER_SCAN_CANDIDATES,
        "max_top_k": MAX_WEATHER_SCAN_TOP_K,
        "max_candidates": MAX_WEATHER_SCAN_CANDIDATES,
        "max_time_slices": MAX_WEATHER_SCAN_TIME_SLICES,
        "max_evaluated_cells": MAX_WEATHER_SCAN_EVALUATED_CELLS,
        "runtime_scope": "seed_weather_scan",
    }


def _candidate_request(
    request_model: WeatherScanRequest,
    *,
    candidate: Dict[str, Any],
    forecast_datetime: str,
    active_clock: ActiveClockContext,
) -> WeatherContextRequest:
    label = str(candidate.get("label") or candidate.get("name") or request_model.location or "Unknown").strip()
    timezone_name = str(candidate.get("timezone") or request_model.timezone or active_clock.timezone or "").strip() or None
    return WeatherContextRequest(
        family_id=request_model.family_id,
        forecast_datetime=forecast_datetime,
        location=label,
        timezone=timezone_name,
        latitude=float(candidate.get("latitude") or 0.0),
        longitude=float(candidate.get("longitude") or 0.0),
        house_system_code=request_model.house_system_code or active_clock.house_system_code,
        source_preference=request_model.source_preference,
    )


def _evaluate_candidate_cell(
    request_model: WeatherScanRequest,
    *,
    candidate: Dict[str, Any],
    forecast_datetime: str,
    active_clock: ActiveClockContext,
    bundle_resolver,
) -> Dict[str, Any]:
    request_for_cell = _candidate_request(
        request_model,
        candidate=candidate,
        forecast_datetime=forecast_datetime,
        active_clock=active_clock,
    )
    resolved = resolve_weather_context(
        request_for_cell,
        active_clock=active_clock,
        bundle_resolver=bundle_resolver,
    )
    analysis = analyze_weather_context(resolved)
    assessment = analysis.family_assessment
    location_payload = {
        "label": str(candidate.get("label") or candidate.get("name") or request_for_cell.location or "Unknown").strip(),
        "country_name": str(candidate.get("country_name") or "").strip(),
        "country_code": str(candidate.get("country_code") or "").strip(),
        "timezone": str(request_for_cell.timezone or "").strip(),
        "latitude": request_for_cell.latitude,
        "longitude": request_for_cell.longitude,
    }
    return {
        "datetime": forecast_datetime,
        "location": location_payload,
        "score": round(float(assessment.get("score") or 0.0), 3),
        "raw_score": round(float(assessment.get("raw_score") or assessment.get("score") or 0.0), 3),
        "level": str(assessment.get("level") or "quiet"),
        "matched_rules": list(assessment.get("matched_rules") or []),
        "summary": str(assessment.get("summary") or "").strip(),
        "signals": dict(assessment.get("signals") or {}),
        "event_focus": round(
            max(
                0.0,
                float(((assessment.get("signals") or {}).get("locality_strength")) or 0.0)
                + float(((assessment.get("signals") or {}).get("path_concentration")) or 0.0),
            ),
            3,
        ),
    }


def run_weather_scan(
    request_model: WeatherScanRequest,
    *,
    active_clock: ActiveClockContext,
    bundle_resolver,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    timepoints = _scan_timepoints(request_model)
    candidates = _candidate_pool(request_model)
    if not candidates:
        raise ValueError("No scan candidates were resolved for the selected weather scope")
    total_cells = len(candidates) * len(timepoints)
    if total_cells > MAX_WEATHER_SCAN_EVALUATED_CELLS:
        raise ValueError(
            f"Resolved weather scan would evaluate {total_cells} cells, exceeding the bound of {MAX_WEATHER_SCAN_EVALUATED_CELLS}"
        )

    rows: List[Dict[str, Any]] = []
    _emit_progress(
        progress_callback,
        stage="running",
        percent=0.0,
        message="Weather scan running",
        done=0,
        total=total_cells,
        candidate_count=len(candidates),
        time_slices=len(timepoints),
        evaluated=0,
        returned=0,
    )
    completed = 0
    for candidate in candidates:
        for timepoint in timepoints:
            rows.append(
                _evaluate_candidate_cell(
                    request_model,
                    candidate=candidate,
                    forecast_datetime=timepoint,
                    active_clock=active_clock,
                    bundle_resolver=bundle_resolver,
                )
            )
            completed += 1
            _emit_progress(
                progress_callback,
                stage="running",
                percent=(completed / total_cells) if total_cells else 1.0,
                message="Weather scan running",
                done=completed,
                total=total_cells,
                candidate_count=len(candidates),
                time_slices=len(timepoints),
                evaluated=completed,
                returned=min(completed, int(request_model.top_k or DEFAULT_WEATHER_SCAN_TOP_K)),
            )

    rows = _relative_scan_level_rows(rows)
    ranked_rows = sorted(rows, key=_sort_key)[: int(request_model.top_k or DEFAULT_WEATHER_SCAN_TOP_K)]
    for rank, row in enumerate(ranked_rows, start=1):
        row["rank"] = rank

    calibration = get_weather_family_profile(request_model.family_id)
    result = {
        "request": request_model.to_dict(),
        "counts": {
            "candidate_count": len(candidates),
            "time_slices": len(timepoints),
            "evaluated": total_cells,
            "returned": len(ranked_rows),
        },
        "scope": {
            "scan_scope": request_model.scan_scope,
            "region_id": request_model.region_id,
            "location": request_model.location,
            "resolution": request_model.resolution,
        },
        "results": ranked_rows,
        "series": _build_series_payload(rows, timepoints=timepoints, top_k=int(request_model.top_k or DEFAULT_WEATHER_SCAN_TOP_K)),
        "calibration": calibration,
        "ranking_mode": "raw_cells_plus_place_series",
        "runtime_scope": "seed_weather_scan",
    }
    return result
