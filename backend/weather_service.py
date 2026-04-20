from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional

from weather_assets import (
    get_weather_family_definitions,
    get_weather_layer_definitions,
    get_weather_reference_notes,
    get_weather_source_index,
)
from weather_benchmark_profiles import get_weather_branch_metrics, get_weather_family_profile
from weather_chart_rules import resolve_weather_chart_resolution
from weather_domain_rules import evaluate_weather_family_context
from weather_models import (
    ResolvedWeatherContext,
    WeatherAnalysis,
    WeatherContextRequest,
    WeatherLayer,
)
from mundane_models import ActiveClockContext


def _normalize_id(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _coerce_optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"Invalid numeric value: {value}") from exc


def _coerce_optional_text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _index_by_id(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        row_id = _normalize_id(row.get("id"))
        if row_id:
            indexed[row_id] = dict(row)
    return indexed


def _source_payload(tags: Iterable[str]) -> list[Dict[str, Any]]:
    source_index = get_weather_source_index()
    resolved: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = _normalize_id(tag)
        if not normalized or normalized in seen:
            continue
        source_info = source_index.get(normalized)
        if isinstance(source_info, dict):
            resolved.append({"id": normalized, **source_info})
            seen.add(normalized)
    return resolved


def _note_payload(note_ids: Iterable[str]) -> list[Dict[str, Any]]:
    note_index = (get_weather_reference_notes().get("note_index") or {})
    if not isinstance(note_index, dict):
        return []
    notes: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for note_id in note_ids:
        normalized = _normalize_id(note_id)
        if not normalized or normalized in seen:
            continue
        note = note_index.get(normalized)
        if isinstance(note, dict):
            notes.append({"id": normalized, **note})
            seen.add(normalized)
    return notes


def _build_layer(
    *,
    layer_id: str,
    label: str,
    summary: str,
    source_tags: Iterable[str],
    note_ids: Iterable[str],
    items: Iterable[Dict[str, Any]],
) -> WeatherLayer:
    return WeatherLayer(
        id=layer_id,
        label=label,
        summary=summary,
        source_tags=list(dict.fromkeys(str(tag) for tag in source_tags if str(tag).strip())),
        notes=_note_payload(note_ids),
        items=[dict(item) for item in items if isinstance(item, dict)],
    )


def build_weather_request(args: Mapping[str, Any]) -> WeatherContextRequest:
    family_id = _normalize_id(args.get("family_id") or args.get("weather_family") or args.get("family"))
    if not family_id:
        raise ValueError("family_id is required")
    return WeatherContextRequest(
        family_id=family_id,
        forecast_datetime=_coerce_optional_text(args.get("forecast_datetime") or args.get("event_datetime")),
        location=_coerce_optional_text(args.get("location") or args.get("forecast_location")),
        timezone=_coerce_optional_text(args.get("timezone") or args.get("forecast_timezone")),
        latitude=_coerce_optional_float(args.get("latitude")),
        longitude=_coerce_optional_float(args.get("longitude")),
        house_system_code=_coerce_optional_text(args.get("house_system_code")),
        source_preference=_normalize_id(args.get("source_preference")) or None,
    )


def get_runtime_catalog() -> Dict[str, Any]:
    return {
        "families": get_weather_family_definitions(),
        "layer_definitions": get_weather_layer_definitions(),
        "source_index": get_weather_source_index(),
        "benchmark_branch": get_weather_branch_metrics(),
        "eclipse_decision": {
            "status": "deferred",
            "decision": "not_active_in_runtime",
            "summary": "Weather eclipse timing remains deferred until locality and weak-family discrimination narrow further.",
        },
        "graduation_decision": {
            "status": "deferred",
            "decision": "no_new_runtime_families",
            "summary": "No benchmark-only weather family graduates into runtime until the current four families narrow further.",
        },
        "runtime_status": "seed_runtime",
    }


def resolve_weather_context(
    request_model: WeatherContextRequest,
    *,
    active_clock: ActiveClockContext,
    bundle_resolver,
) -> ResolvedWeatherContext:
    family_index = _index_by_id(get_weather_family_definitions())
    family = family_index.get(request_model.family_id)
    if family is None:
        raise ValueError(f"Unsupported weather family: {request_model.family_id}")

    forecast_datetime = request_model.forecast_datetime or active_clock.timestamp
    location = request_model.location or active_clock.location
    timezone_name = request_model.timezone or active_clock.timezone
    if not location:
        raise ValueError("location is required for weather analysis")
    house_system_code = request_model.house_system_code or active_clock.house_system_code

    chart_resolution = resolve_weather_chart_resolution(
        forecast_datetime=forecast_datetime,
        location=location,
        timezone_name=timezone_name,
        house_system_code=house_system_code,
        bundle_resolver=bundle_resolver,
        latitude=request_model.latitude or active_clock.latitude,
        longitude=request_model.longitude or active_clock.longitude,
    )

    research_flags = list(
        dict.fromkeys(
            [
                *list(family.get("research_flags") or []),
                *list(chart_resolution.get("research_flags") or []),
            ]
        )
    )
    source_tags = list(
        dict.fromkeys(
            [
                *list(family.get("source_tags") or []),
                *list(chart_resolution.get("source_tags") or []),
            ]
        )
    )

    return ResolvedWeatherContext(
        request=request_model,
        active_clock=active_clock,
        family=family,
        event_context={
            "forecast_datetime": forecast_datetime,
            "location": location,
            "timezone": timezone_name,
            "latitude": request_model.latitude or active_clock.latitude,
            "longitude": request_model.longitude or active_clock.longitude,
            "house_system_code": house_system_code,
        },
        chart_resolution=chart_resolution,
        research_flags=research_flags,
        source_tags=source_tags,
    )


def analyze_weather_context(resolved_context: ResolvedWeatherContext) -> WeatherAnalysis:
    evaluation = evaluate_weather_family_context(resolved_context)
    benchmark_family_id = str((resolved_context.family or {}).get("benchmark_family_id") or "")
    benchmark_profile = get_weather_family_profile(benchmark_family_id)
    combined_flags = list(
        dict.fromkeys(
            [
                *list(resolved_context.research_flags or []),
                *list(evaluation.get("research_flags") or []),
                *list(benchmark_profile.get("gaps") or []),
            ]
        )
    )
    doctrine_note_ids = list(evaluation.get("doctrine_note_ids") or [])
    source_tags = list(
        dict.fromkeys(
            [
                *list(resolved_context.source_tags or []),
                *list(evaluation.get("source_tags") or []),
            ]
        )
    )

    framework_layer = _build_layer(
        layer_id="framework_layer",
        label="Seasonal Framework",
        summary=str(evaluation.get("framework_summary") or ""),
        source_tags=source_tags,
        note_ids=["weather_framework", *doctrine_note_ids],
        items=evaluation.get("framework_notes") or [],
    )
    trigger_layer = _build_layer(
        layer_id="trigger_layer",
        label="Lunar Trigger",
        summary=str(evaluation.get("trigger_summary") or ""),
        source_tags=source_tags,
        note_ids=doctrine_note_ids,
        items=evaluation.get("trigger_notes") or [],
    )
    locality_layer = _build_layer(
        layer_id="locality_layer",
        label="Locality Proxy",
        summary=str(evaluation.get("locality_summary") or ""),
        source_tags=source_tags,
        note_ids=["weather_locality_proxy", *doctrine_note_ids],
        items=evaluation.get("locality_notes") or [],
    )

    family_assessment = dict(evaluation.get("assessment") or {})
    family_assessment["benchmark_family_id"] = benchmark_family_id

    doctrine = {
        "source_tags": source_tags,
        "sources": _source_payload(source_tags),
        "notes": _note_payload(doctrine_note_ids),
    }

    research = {
        "status": "seed_runtime",
        "runtime_scope": "seed_weather_runtime",
        "calibration": benchmark_profile,
        "flags": combined_flags,
        "limitations": [
            "The first runtime is benchmark-backed but still research-gated.",
            "Locality uses angular and horizon/meridian target-zone proxies until a fuller weather map runtime is implemented.",
            "Eclipse timing remains a bounded deferred decision and is not active scoring in the current weather runtime.",
            "The seed runtime separates family outputs and does not claim general meteorological completeness.",
        ],
        "active_branch_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return WeatherAnalysis(
        context=resolved_context,
        framework_layer=framework_layer,
        trigger_layer=trigger_layer,
        locality_layer=locality_layer,
        family_assessment=family_assessment,
        doctrine=doctrine,
        research=research,
    )
