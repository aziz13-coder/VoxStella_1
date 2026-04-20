from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from weather_models import ResolvedWeatherContext


_RELEVANT_LOCALITY_PLANETS = {
    "flood_risk": ("Moon", "Venus", "Neptune", "Saturn", "Mars"),
    "hurricane_pressure": ("Mercury", "Moon", "Mars", "Uranus", "Neptune"),
    "severe_convective_pressure": ("Mercury", "Mars", "Uranus"),
    "wind_event_pressure": ("Mercury", "Uranus", "Saturn"),
}


def _normalize_id(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _chart_index(chart_resolution: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    primary = chart_resolution.get("primary_chart")
    if isinstance(primary, dict):
        index[_normalize_id(primary.get("kind")) or "forecast_chart"] = primary
    for chart in chart_resolution.get("supporting_charts") or []:
        if not isinstance(chart, dict):
            continue
        chart_kind = _normalize_id(chart.get("kind"))
        if chart_kind:
            index[chart_kind] = chart
    return index


def _planets(chart: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    planets = chart.get("planets") or {}
    if isinstance(planets, dict):
        return {str(name): info for name, info in planets.items() if isinstance(info, dict)}
    return {}


def _planet(chart: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    return _planets(chart).get(name)


def _longitude(chart: Dict[str, Any], name: str) -> Optional[float]:
    info = _planet(chart, name)
    if not info:
        return None
    try:
        return float(info.get("longitude"))
    except Exception:
        return None


def _house(chart: Dict[str, Any], name: str) -> Optional[int]:
    info = _planet(chart, name)
    if not info:
        return None
    try:
        return int(info.get("house"))
    except Exception:
        return None


def _angle_distance(chart: Dict[str, Any], name: str) -> Optional[float]:
    info = _planet(chart, name)
    if not info:
        return None
    try:
        return float(info.get("angle_distance_deg"))
    except Exception:
        return None


def _is_angular(chart: Dict[str, Any], name: str, *, max_distance: float = 10.0) -> bool:
    house = _house(chart, name)
    if house in {1, 4, 7, 10}:
        return True
    distance = _angle_distance(chart, name)
    return distance is not None and distance <= max_distance


def _angle_name(chart: Dict[str, Any], name: str) -> Optional[str]:
    info = _planet(chart, name)
    return str((info or {}).get("closest_angle") or "").strip() or None


def _signed_angle_diff(a: float, b: float) -> float:
    return (((float(a) - float(b)) + 180.0) % 360.0) - 180.0


def _major_aspect(chart: Dict[str, Any], left: str, right: str, *, orb: float = 6.0) -> Optional[Dict[str, Any]]:
    left_lon = _longitude(chart, left)
    right_lon = _longitude(chart, right)
    if left_lon is None or right_lon is None:
        return None
    separation = abs(_signed_angle_diff(left_lon, right_lon))
    aspects = {
        "conjunction": 0.0,
        "sextile": 60.0,
        "square": 90.0,
        "trine": 120.0,
        "opposition": 180.0,
    }
    closest_name = None
    closest_delta = None
    for name, target in aspects.items():
        delta = abs(separation - target)
        if closest_delta is None or delta < closest_delta:
            closest_name = name
            closest_delta = delta
    if closest_name is None or closest_delta is None or closest_delta > orb:
        return None
    return {
        "aspect": closest_name,
        "orb_deg": round(closest_delta, 3),
        "separation_deg": round(separation, 3),
    }


def _cross_chart_major_aspect(
    left_chart: Dict[str, Any],
    left: str,
    right_chart: Dict[str, Any],
    right: str,
    *,
    orb: float = 6.0,
) -> Optional[Dict[str, Any]]:
    left_lon = _longitude(left_chart, left)
    right_lon = _longitude(right_chart, right)
    if left_lon is None or right_lon is None:
        return None
    separation = abs(_signed_angle_diff(left_lon, right_lon))
    aspects = {
        "conjunction": 0.0,
        "sextile": 60.0,
        "square": 90.0,
        "trine": 120.0,
        "opposition": 180.0,
    }
    closest_name = None
    closest_delta = None
    for name, target in aspects.items():
        delta = abs(separation - target)
        if closest_delta is None or delta < closest_delta:
            closest_name = name
            closest_delta = delta
    if closest_name is None or closest_delta is None or closest_delta > orb:
        return None
    return {
        "aspect": closest_name,
        "orb_deg": round(closest_delta, 3),
        "separation_deg": round(separation, 3),
    }


def _planet_speed(chart: Dict[str, Any], name: str) -> Optional[float]:
    info = _planet(chart, name)
    if not info:
        return None
    try:
        return float(info.get("speed"))
    except Exception:
        return None


def _is_stationing(chart: Dict[str, Any], name: str, *, max_speed: float = 0.25) -> bool:
    speed = _planet_speed(chart, name)
    return speed is not None and abs(speed) <= max_speed


def _rule(
    *,
    layer: str,
    chart_kind: str,
    rule_id: str,
    label: str,
    summary: str,
    score: int,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "id": rule_id,
        "layer": layer,
        "chart_kind": chart_kind,
        "label": label,
        "summary": summary,
        "score": score,
    }
    if extra:
        payload.update(extra)
    return payload


def _level_from_score(score: int) -> str:
    if score >= 36:
        return "active"
    if score >= 24:
        return "elevated"
    if score >= 12:
        return "watch"
    return "quiet"


def _notes_summary(notes: List[Dict[str, Any]], fallback: str) -> str:
    if not notes:
        return fallback
    ranked = sorted(notes, key=lambda row: (-int(row.get("score") or 0), row.get("label") or ""))
    parts = [str(row.get("label") or "").strip() for row in ranked[:3] if str(row.get("label") or "").strip()]
    return ", ".join(parts) if parts else fallback


def _layer_locality_hits(
    chart_kind: str,
    chart: Dict[str, Any],
    relevant: Iterable[str],
    *,
    max_distance: float,
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for name in relevant:
        if not _is_angular(chart, name, max_distance=max_distance):
            continue
        distance = _angle_distance(chart, name)
        hits.append(
            {
                "planet": name,
                "chart_kind": chart_kind,
                "angle_distance_deg": distance,
                "closest_angle": _angle_name(chart, name),
                "tight": distance is not None and distance <= 6.5,
            }
        )
    return hits


def _chart_target_zone_intersections(
    chart_kind: str,
    chart: Dict[str, Any],
    relevant: Iterable[str],
) -> List[Dict[str, Any]]:
    relevant_set = {str(name) for name in relevant if str(name).strip()}
    intersections = chart.get("target_zone_intersections") or []
    rows: List[Dict[str, Any]] = []
    for item in intersections:
        if not isinstance(item, dict):
            continue
        horizon_planet = str(item.get("horizon_planet") or "").strip()
        meridian_planet = str(item.get("meridian_planet") or "").strip()
        if horizon_planet not in relevant_set or meridian_planet not in relevant_set:
            continue
        try:
            combined_distance = float(item.get("combined_distance_deg"))
        except Exception:
            combined_distance = None
        rows.append(
            {
                "chart_kind": chart_kind,
                "horizon_planet": horizon_planet,
                "horizon_angle": str(item.get("horizon_angle") or "").strip(),
                "meridian_planet": meridian_planet,
                "meridian_angle": str(item.get("meridian_angle") or "").strip(),
                "pair_label": str(item.get("pair_label") or "").strip(),
                "combined_distance_deg": combined_distance,
                "zone": str(item.get("zone") or "").strip() or "extended",
                "intersection_strength": float(item.get("intersection_strength") or 0.0),
            }
        )
    rows.sort(
        key=lambda row: (
            float(row.get("combined_distance_deg") or 999.0),
            -float(row.get("intersection_strength") or 0.0),
            str(row.get("pair_label") or ""),
        )
    )
    return rows


def _build_locality_notes(
    family_id: str,
    forecast_chart: Dict[str, Any],
    *,
    supporting_charts: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    relevant = _RELEVANT_LOCALITY_PLANETS.get(family_id) or ()
    supporting_charts = supporting_charts or {}
    supporting_hits_by_layer = {
        chart_kind: _layer_locality_hits(chart_kind, chart, relevant, max_distance=9.5)
        for chart_kind, chart in supporting_charts.items()
        if isinstance(chart, dict) and chart
    }
    supporting_intersections_by_layer = {
        chart_kind: _chart_target_zone_intersections(chart_kind, chart, relevant)
        for chart_kind, chart in supporting_charts.items()
        if isinstance(chart, dict) and chart
    }
    forecast_hits = _layer_locality_hits("forecast_chart", forecast_chart, relevant, max_distance=10.0)
    forecast_intersections = _chart_target_zone_intersections("forecast_chart", forecast_chart, relevant)
    hits: List[Dict[str, Any]] = []
    for hit in forecast_hits:
        distance = hit.get("angle_distance_deg")
        hits.append(
            _rule(
                layer="locality_layer",
                chart_kind="forecast_chart",
                rule_id=f"locality_{_normalize_id(hit.get('planet'))}",
                label=f"{hit.get('planet')} angular target-zone proxy",
                summary=(
                    f"{hit.get('planet')} is near the {hit.get('closest_angle') or 'nearest angle'} "
                    f"of the forecast chart, which the seed runtime treats as a locality emphasis proxy."
                ),
                score=max(4, 12 - int(round(distance or 0.0))),
                extra={
                    "planet": hit.get("planet"),
                    "angle_distance_deg": distance,
                    "closest_angle": hit.get("closest_angle"),
                },
            )
        )
    for intersection in forecast_intersections[:2]:
        combined_distance = intersection.get("combined_distance_deg")
        score = max(6, 14 - int(round(combined_distance or 0.0)))
        hits.append(
            _rule(
                layer="locality_layer",
                chart_kind="forecast_chart",
                rule_id=(
                    f"target_zone_{_normalize_id(intersection.get('horizon_planet'))}_"
                    f"{_normalize_id(intersection.get('meridian_planet'))}"
                ),
                label=(
                    f"Target-zone intersection: {intersection.get('horizon_planet')} x "
                    f"{intersection.get('meridian_planet')}"
                ),
                summary=(
                    f"{intersection.get('horizon_planet')} on the "
                    f"{str(intersection.get('horizon_angle') or '').replace('_', ' ')} and "
                    f"{intersection.get('meridian_planet')} on the "
                    f"{str(intersection.get('meridian_angle') or '').replace('_', ' ')} form a "
                    "tight horizon/meridian target-zone proxy at the forecast location."
                ),
                score=score,
                extra={
                    "pair_label": intersection.get("pair_label"),
                    "combined_distance_deg": combined_distance,
                    "zone": intersection.get("zone"),
                },
            )
        )
    reinforcing_layers = [chart_kind for chart_kind, layer_hits in supporting_hits_by_layer.items() if layer_hits]
    intersection_layers = [
        chart_kind for chart_kind, rows in supporting_intersections_by_layer.items() if rows
    ]
    unique_planets = {
        str(hit.get("planet") or "").strip()
        for hit in [*forecast_hits, *[item for layer in supporting_hits_by_layer.values() for item in layer]]
        if str(hit.get("planet") or "").strip()
    }
    tight_hit_count = sum(1 for hit in forecast_hits if bool(hit.get("tight")))
    locality_strength = 0
    if forecast_hits:
        locality_strength = min(
            24,
            (len(forecast_hits) * 4)
            + (tight_hit_count * 3)
            + (max(0, len(reinforcing_layers)) * 3)
            + max(0, len(unique_planets) - 1),
        )
    best_intersection_distance = min(
        (
            float(item.get("combined_distance_deg"))
            for item in [*forecast_intersections, *[row for rows in supporting_intersections_by_layer.values() for row in rows]]
            if item.get("combined_distance_deg") is not None
        ),
        default=None,
    )
    target_zone_intersection_count = len(forecast_intersections)
    path_concentration = 0
    if forecast_intersections:
        path_concentration = min(
            12,
            (len(forecast_intersections) * 3)
            + (len(intersection_layers) * 2)
            + max(0, 10 - int(round(best_intersection_distance or 10.0))),
        )
    metrics = {
        "forecast_angular_hits": len(forecast_hits),
        "tight_hit_count": tight_hit_count,
        "reinforcing_layer_count": len(reinforcing_layers),
        "reinforcing_layers": reinforcing_layers,
        "unique_relevant_planets": len(unique_planets),
        "locality_strength": locality_strength,
        "path_concentration": path_concentration,
        "target_zone_intersection_count": target_zone_intersection_count,
        "intersection_reinforcing_layer_count": len(intersection_layers),
        "best_intersection_distance_deg": round(best_intersection_distance, 3) if best_intersection_distance is not None else None,
    }
    if forecast_hits and reinforcing_layers:
        hits.append(
            _rule(
                layer="locality_layer",
                chart_kind="forecast_chart",
                rule_id="locality_reinforcement",
                label="Repeated locality reinforcement",
                summary="Relevant locality testimony repeats across supporting weather layers and the forecast chart, which the runtime treats as a stronger target-zone concentration than a single angular hit.",
                score=6,
                extra={
                    "reinforcing_layers": reinforcing_layers,
                    "unique_relevant_planets": len(unique_planets),
                },
            )
        )
    if forecast_intersections and intersection_layers:
        hits.append(
            _rule(
                layer="locality_layer",
                chart_kind="forecast_chart",
                rule_id="target_zone_reinforcement",
                label="Repeated target-zone reinforcement",
                summary="Relevant horizon and meridian target-zone intersections repeat across supporting weather layers, which the runtime treats as a narrower focus band than a single angular concentration alone.",
                score=6,
                extra={
                    "reinforcing_layers": intersection_layers,
                    "target_zone_intersection_count": target_zone_intersection_count,
                },
            )
        )
    if not hits:
        fallback_summary = (
            "No strong angular or target-zone locality proxy is present in the forecast chart; the seed runtime falls back to the requested location without a sharper target-zone emphasis."
        )
        if reinforcing_layers or intersection_layers:
            fallback_summary = (
                "Supporting weather layers carry relevant locality testimony, but the forecast chart does not concentrate it tightly enough to sharpen the requested location."
            )
        return fallback_summary, [], metrics
    top = sorted(hits, key=lambda row: (-int(row.get("score") or 0), row.get("planet") or ""))[0]
    if str(top.get("rule_id") or "").startswith("target_zone_"):
        summary = (
            f"{top.get('pair_label') or top.get('label')} is the strongest forecast-chart "
            "target-zone proxy."
        )
    else:
        summary = (
            f"{top.get('planet')} is the strongest forecast-chart locality proxy, closest to the "
            f"{top.get('closest_angle') or 'nearest angle'}."
        )
    if reinforcing_layers or intersection_layers:
        repeated_layers = [*reinforcing_layers, *[layer for layer in intersection_layers if layer not in reinforcing_layers]]
        summary = (
            f"{summary} Relevant locality testimony also repeats in {', '.join(layer.replace('_', ' ') for layer in repeated_layers)}."
        )
    return summary, hits, metrics


def _weighted_rule_total(matched_rules: Iterable[Dict[str, Any]]) -> Tuple[int, int, int]:
    grouped: Dict[str, List[int]] = {}
    raw_total = 0
    total_count = 0
    for rule in matched_rules:
        label = str(rule.get("label") or rule.get("id") or "").strip()
        score = int(rule.get("score") or 0)
        raw_total += score
        total_count += 1
        grouped.setdefault(label, []).append(score)
    weights = (1.0, 0.6, 0.35, 0.2)
    weighted_total = 0.0
    for scores in grouped.values():
        ranked_scores = sorted(scores, key=lambda value: abs(value), reverse=True)
        for index, score in enumerate(ranked_scores):
            weight = weights[index] if index < len(weights) else weights[-1]
            weighted_total += score * weight
    duplicate_count = max(0, total_count - len(grouped))
    return int(round(weighted_total)), raw_total, duplicate_count


def _timing_metrics(context: ResolvedWeatherContext) -> Dict[str, Any]:
    signals = (context.chart_resolution or {}).get("signals") or {}
    lunar_signal = signals.get("lunar_phase") or {}
    seasonal_signal = signals.get("seasonal_ingress") or {}
    eclipse_signal = signals.get("eclipse_overlay") or {}
    try:
        lunar_age_hours = float(lunar_signal.get("age_hours"))
    except Exception:
        lunar_age_hours = None
    try:
        seasonal_age_days = float(seasonal_signal.get("age_days"))
    except Exception:
        seasonal_age_days = None
    return {
        "lunar_phase_id": _normalize_id(lunar_signal.get("id")),
        "lunar_age_hours": lunar_age_hours,
        "seasonal_ingress_id": _normalize_id(seasonal_signal.get("id")),
        "seasonal_age_days": seasonal_age_days,
        "eclipse_overlay_status": str(eclipse_signal.get("status") or "").strip() or "deferred",
    }


def _orb_scaled_score(
    aspect: Dict[str, Any],
    *,
    max_score: int,
    min_score: int,
    orb_penalty_per_degree: float = 1.5,
) -> int:
    try:
        orb_deg = float(aspect.get("orb_deg") or 0.0)
    except Exception:
        orb_deg = 0.0
    score = max_score - int(round(orb_deg * orb_penalty_per_degree))
    return max(min_score, score)


def _wind_angular_score(chart: Dict[str, Any], planet: str, *, max_score: int, min_score: int) -> Optional[int]:
    if not _is_angular(chart, planet):
        return None
    distance = _angle_distance(chart, planet)
    if distance is None:
        return max_score
    if distance <= 8.0:
        return max_score
    if distance <= 16.0:
        return max(max_score - 2, min_score)
    if distance <= 24.0:
        return max(max_score - 4, min_score)
    return min_score


def _is_tight_angular(chart: Dict[str, Any], name: str, *, max_distance: float = 8.0) -> bool:
    distance = _angle_distance(chart, name)
    if distance is not None:
        return distance <= max_distance
    house = _house(chart, name)
    return house in {1, 4, 7, 10}


def _tight_angular_hits(chart: Dict[str, Any], planets: Iterable[str], *, max_distance: float = 8.0) -> List[str]:
    return [name for name in planets if _is_tight_angular(chart, name, max_distance=max_distance)]


def _family_common_payload(
    *,
    family_id: str,
    family_label: str,
    framework_notes: List[Dict[str, Any]],
    trigger_notes: List[Dict[str, Any]],
    locality_notes: List[Dict[str, Any]],
    locality_metrics: Optional[Dict[str, Any]] = None,
    timing_metrics: Optional[Dict[str, Any]] = None,
    doctrine_note_ids: Iterable[str],
    source_tags: Iterable[str],
    research_flags: Iterable[str],
) -> Dict[str, Any]:
    matched_rules = sorted(
        [*framework_notes, *trigger_notes, *locality_notes],
        key=lambda row: (-int(row.get("score") or 0), row.get("label") or ""),
    )
    weighted_score, raw_score, duplicate_rule_count = _weighted_rule_total(matched_rules)
    locality_metrics = dict(locality_metrics or {})
    timing_metrics = dict(timing_metrics or {})
    return {
        "family_id": family_id,
        "family_label": family_label,
        "framework_notes": framework_notes,
        "trigger_notes": trigger_notes,
        "locality_notes": locality_notes,
        "framework_summary": _notes_summary(
            framework_notes,
            "Seasonal framework signals are light and mostly background for this family.",
        ),
        "trigger_summary": _notes_summary(
            trigger_notes,
            "Short-term trigger signals are limited in the resolved weather charts.",
        ),
        "locality_summary": _notes_summary(
            locality_notes,
            "No strong locality proxy is present beyond the requested location.",
        ),
        "assessment": {
            "family_id": family_id,
            "family_label": family_label,
            "score": weighted_score,
            "raw_score": raw_score,
            "level": _level_from_score(weighted_score),
            "summary": (
                f"{family_label} is assessed from the seasonal ingress, the latest lunar phase, "
                f"and forecast-chart locality proxies. Top signals: "
                f"{_notes_summary(matched_rules, 'no strong signals')}"
            ),
            "matched_rules": matched_rules,
            "signals": {
                "framework_count": len(framework_notes),
                "trigger_count": len(trigger_notes),
                "locality_count": len(locality_notes),
                "duplicate_rule_count": duplicate_rule_count,
                "distinct_rule_count": max(0, len(matched_rules) - duplicate_rule_count),
                "locality_strength": int(locality_metrics.get("locality_strength") or 0),
                "path_concentration": int(locality_metrics.get("path_concentration") or 0),
                "tight_hit_count": int(locality_metrics.get("tight_hit_count") or 0),
                "reinforcing_layer_count": int(locality_metrics.get("reinforcing_layer_count") or 0),
                "target_zone_intersection_count": int(locality_metrics.get("target_zone_intersection_count") or 0),
                "intersection_reinforcing_layer_count": int(locality_metrics.get("intersection_reinforcing_layer_count") or 0),
                "best_intersection_distance_deg": locality_metrics.get("best_intersection_distance_deg"),
                "unique_relevant_planets": int(locality_metrics.get("unique_relevant_planets") or 0),
                "lunar_age_hours": timing_metrics.get("lunar_age_hours"),
                "seasonal_age_days": timing_metrics.get("seasonal_age_days"),
                "eclipse_overlay_status": timing_metrics.get("eclipse_overlay_status") or "deferred",
            },
        },
        "doctrine_note_ids": list(dict.fromkeys(str(note_id) for note_id in doctrine_note_ids if str(note_id).strip())),
        "source_tags": list(dict.fromkeys(str(tag) for tag in source_tags if str(tag).strip())),
        "research_flags": list(dict.fromkeys(str(flag) for flag in research_flags if str(flag).strip())),
    }


def _evaluate_flood_risk(context: ResolvedWeatherContext, charts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    seasonal = charts.get("spring_ingress") or charts.get("summer_ingress") or charts.get("autumn_ingress") or charts.get("winter_ingress") or {}
    lunar = charts.get("new_moon") or charts.get("full_moon") or charts.get("first_quarter") or charts.get("last_quarter") or {}
    forecast = charts.get("forecast_chart") or {}
    timing = _timing_metrics(context)

    framework_notes: List[Dict[str, Any]] = []
    trigger_notes: List[Dict[str, Any]] = []

    for chart_kind, chart in (("seasonal_ingress", seasonal), ("lunar_phase", lunar), ("forecast_chart", forecast)):
        for name in ("Moon", "Venus", "Neptune"):
            if _is_angular(chart, name):
                framework_notes.append(
                    _rule(
                        layer="framework_layer" if chart_kind == "seasonal_ingress" else "trigger_layer",
                        chart_kind=chart_kind,
                        rule_id=f"{chart_kind}_{_normalize_id(name)}_moisture",
                        label=f"{name} angular moisture testimony",
                        summary=f"{name} is angular in the {chart_kind.replace('_', ' ')}, supporting excess-water and heavy-precipitation logic.",
                        score=8 if chart_kind == "seasonal_ingress" else 10,
                        extra={"planet": name},
                    )
                )

    for chart_kind, chart in (("seasonal_ingress", seasonal), ("lunar_phase", lunar), ("forecast_chart", forecast)):
        aspect = _major_aspect(chart, "Saturn", "Neptune", orb=6.5)
        if aspect:
            note = _rule(
                layer="framework_layer" if chart_kind == "seasonal_ingress" else "trigger_layer",
                chart_kind=chart_kind,
                rule_id=f"{chart_kind}_saturn_neptune",
                label="Saturn-Neptune flood testimony",
                summary=f"Saturn and Neptune form a {aspect['aspect']} in the {chart_kind.replace('_', ' ')}, matching the seeded heavy-rain and flood doctrine.",
                score=12 if chart_kind == "seasonal_ingress" else 14,
                extra=aspect,
            )
            if chart_kind == "seasonal_ingress":
                framework_notes.append(note)
            else:
                trigger_notes.append(note)

    if _is_angular(forecast, "Mars") and (
        _is_angular(forecast, "Moon") or _is_angular(forecast, "Venus") or _is_angular(forecast, "Neptune")
    ):
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="forecast_chart",
                rule_id="forecast_flash_flood_kicker",
                label="Flash-flood acceleration",
                summary="Mars is angular alongside water-bearing testimony in the forecast chart, which the seed runtime treats as a flash-flood accelerator rather than only a wet pattern.",
                score=8,
            )
        )

    wet_chart_hits = {
        "seasonal_ingress": [name for name in ("Moon", "Venus", "Neptune") if _is_angular(seasonal, name)],
        "lunar_phase": [name for name in ("Moon", "Venus", "Neptune") if _is_angular(lunar, name)],
        "forecast_chart": [name for name in ("Moon", "Venus", "Neptune") if _is_angular(forecast, name)],
    }
    active_wet_charts = [chart_kind for chart_kind, hits in wet_chart_hits.items() if hits]
    total_wet_hits = sum(len(hits) for hits in wet_chart_hits.values())
    if len(active_wet_charts) >= 2 and total_wet_hits >= 3:
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="forecast_chart",
                rule_id="successive_wet_trigger_accumulation",
                label="Successive wet-trigger accumulation",
                summary="Wet testimony repeats across the seasonal, lunar, and forecast layers, which the runtime treats as an accumulation pattern instead of a single isolated rain hit.",
                score=8,
                extra={
                    "active_wet_charts": active_wet_charts,
                    "total_wet_hits": total_wet_hits,
                },
            )
        )

    tight_forecast_water_hits = _tight_angular_hits(forecast, ("Moon", "Venus", "Neptune"), max_distance=6.5)
    if tight_forecast_water_hits and (wet_chart_hits["lunar_phase"] or wet_chart_hits["seasonal_ingress"]):
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="forecast_chart",
                rule_id="tight_water_angle_concentration",
                label="Tight water-angle concentration",
                summary="A water-bearing planet is tightly concentrated on a forecast-chart angle while earlier wet testimony is already active, sharpening the flood window inside a broader wet run.",
                score=8,
                extra={"tight_water_planets": tight_forecast_water_hits},
            )
        )

    if _is_angular(seasonal, "Saturn") and not framework_notes:
        framework_notes.append(
            _rule(
                layer="framework_layer",
                chart_kind="seasonal_ingress",
                rule_id="seasonal_saturn_blocks_rain",
                label="Saturn rain-prohibition backdrop",
                summary="Saturn dominates the seasonal ingress without offsetting moisture testimony, tempering flood pressure and preserving Bonatti's rain-prohibition logic.",
                score=-6,
            )
        )

    locality_summary, locality_notes, locality_metrics = _build_locality_notes(
        "flood_risk",
        forecast,
        supporting_charts={"seasonal_ingress": seasonal, "lunar_phase": lunar},
    )
    if len(active_wet_charts) >= 2 and tight_forecast_water_hits:
        locality_metrics["path_concentration"] = 6 + min(4, len(tight_forecast_water_hits))
        locality_notes.insert(
            0,
            _rule(
                layer="locality_layer",
                chart_kind="forecast_chart",
                rule_id="flood_locality_cluster",
                label="Waterfield locality cluster",
                summary="Flood-relevant planets are tightly concentrated on forecast-chart angles while earlier wet testimony is already active, which the runtime treats as a narrower flood target zone.",
                score=6,
                extra={"tight_water_planets": tight_forecast_water_hits},
            ),
        )
        locality_summary = "Forecast angles carry a tighter waterfield cluster than a broad wet background alone."
    payload = _family_common_payload(
        family_id="flood_risk",
        family_label="Flood Risk",
        framework_notes=framework_notes,
        trigger_notes=trigger_notes,
        locality_notes=locality_notes,
        locality_metrics=locality_metrics,
        timing_metrics=timing,
        doctrine_note_ids=("weather_framework", "weather_locality_proxy", "flood_risk"),
        source_tags=("riske", "bonatti", "watters", "green_carter"),
        research_flags=("seed_runtime", "locality_proxy_only", "eclipse_runtime_deferred"),
    )
    payload["locality_summary"] = locality_summary
    return payload


def _evaluate_hurricane_pressure(context: ResolvedWeatherContext, charts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    seasonal = charts.get("summer_ingress") or charts.get("autumn_ingress") or charts.get("spring_ingress") or charts.get("winter_ingress") or {}
    lunar = charts.get("new_moon") or charts.get("full_moon") or charts.get("first_quarter") or charts.get("last_quarter") or {}
    forecast = charts.get("forecast_chart") or {}
    timing = _timing_metrics(context)

    framework_notes: List[Dict[str, Any]] = []
    trigger_notes: List[Dict[str, Any]] = []

    seasonal_kind = _normalize_id(seasonal.get("kind"))
    if seasonal_kind in {"summer_ingress", "autumn_ingress"}:
        framework_notes.append(
            _rule(
                layer="framework_layer",
                chart_kind=seasonal_kind,
                rule_id="seasonal_tropical_window",
                label="Seasonal tropical storm window",
                summary="The resolved seasonal ingress is a summer or autumn ingress, which the seed runtime treats as the natural tropical-storm framework window.",
                score=6,
            )
        )

    forecast_storm_stack = False
    for chart_kind, chart in (("lunar_phase", lunar), ("forecast_chart", forecast)):
        for left, right, label, score in (
            ("Mercury", "Uranus", "Mercury-Uranus storm signature", 14),
            ("Mars", "Uranus", "Mars-Uranus storm signature", 12),
        ):
            aspect = _major_aspect(chart, left, right, orb=6.5)
            if aspect:
                if chart_kind == "forecast_chart":
                    forecast_storm_stack = True
                trigger_notes.append(
                    _rule(
                        layer="trigger_layer",
                        chart_kind=chart_kind,
                        rule_id=f"{chart_kind}_{_normalize_id(left)}_{_normalize_id(right)}",
                        label=label,
                        summary=f"{left} and {right} form a {aspect['aspect']} in the {chart_kind.replace('_', ' ')}, supporting hurricane and tropical-storm volatility.",
                        score=score,
                        extra=aspect,
                    )
                )

    for chart_kind, chart in (("seasonal_ingress", seasonal), ("lunar_phase", lunar), ("forecast_chart", forecast)):
        for name, label, score in (
            ("Neptune", "Neptune angular moisture field", 9),
            ("Moon", "Moon angular tidal/moisture field", 7),
            ("Mercury", "Mercury angular wind-track signal", 7),
        ):
            if _is_angular(chart, name):
                note = _rule(
                    layer="framework_layer" if chart_kind == "seasonal_ingress" else "trigger_layer",
                    chart_kind=chart_kind,
                    rule_id=f"{chart_kind}_{_normalize_id(name)}_hurricane",
                    label=label,
                    summary=f"{name} is angular in the {chart_kind.replace('_', ' ')}, reinforcing wind-and-moisture testimony for hurricane pressure.",
                    score=score,
                    extra={"planet": name},
                )
                if chart_kind == "seasonal_ingress":
                    framework_notes.append(note)
                else:
                    trigger_notes.append(note)

    tight_track_hits = _tight_angular_hits(forecast, ("Mercury", "Moon", "Neptune", "Mars", "Uranus"), max_distance=6.5)
    if forecast_storm_stack and "Mercury" in tight_track_hits and ({"Moon", "Neptune"} & set(tight_track_hits)):
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="forecast_chart",
                rule_id="forecast_landfall_concentration",
                label="Landfall concentration gate",
                summary="The forecast chart combines a live storm trigger with tight Mercury plus moisture concentration on the angles, which the runtime treats as a sharper landfall-style focus rather than only broad tropical pressure.",
                score=10,
                extra={"tight_track_planets": tight_track_hits},
            )
        )
    if forecast_storm_stack and len(tight_track_hits) >= 3:
        locality_notes_seed = [
            _rule(
                layer="locality_layer",
                chart_kind="forecast_chart",
                rule_id="forecast_path_cluster",
                label="Path cluster concentration",
                summary="Three or more hurricane-significant planets are tightly concentrated on forecast-chart angles, reinforcing the location as a stronger path-focus candidate.",
                score=6,
                extra={"tight_track_planets": tight_track_hits},
            )
        ]
    else:
        locality_notes_seed = []

    locality_summary, locality_notes, locality_metrics = _build_locality_notes(
        "hurricane_pressure",
        forecast,
        supporting_charts={"seasonal_ingress": seasonal, "lunar_phase": lunar},
    )
    locality_notes = [*locality_notes_seed, *locality_notes]
    if locality_notes_seed:
        locality_summary = "Forecast angles carry a tighter storm-path cluster than a broad tropical background alone."
        locality_metrics["path_concentration"] = 8 + min(4, max(0, len(tight_track_hits) - 2))
    payload = _family_common_payload(
        family_id="hurricane_pressure",
        family_label="Hurricane Pressure",
        framework_notes=framework_notes,
        trigger_notes=trigger_notes,
        locality_notes=locality_notes,
        locality_metrics=locality_metrics,
        timing_metrics=timing,
        doctrine_note_ids=("weather_framework", "weather_locality_proxy", "hurricane_pressure"),
        source_tags=("riske", "watters", "green_carter"),
        research_flags=("seed_runtime", "locality_proxy_only", "eclipse_runtime_deferred"),
    )
    payload["locality_summary"] = locality_summary
    return payload


def _evaluate_severe_convective_pressure(context: ResolvedWeatherContext, charts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    seasonal = charts.get("spring_ingress") or charts.get("summer_ingress") or charts.get("autumn_ingress") or charts.get("winter_ingress") or {}
    lunar = charts.get("new_moon") or charts.get("full_moon") or charts.get("first_quarter") or charts.get("last_quarter") or {}
    forecast = charts.get("forecast_chart") or {}
    timing = _timing_metrics(context)

    framework_notes: List[Dict[str, Any]] = []
    trigger_notes: List[Dict[str, Any]] = []

    for chart_kind, chart in (("seasonal_ingress", seasonal), ("lunar_phase", lunar), ("forecast_chart", forecast)):
        for left, right, label in (
            ("Mercury", "Uranus", "Mercury-Uranus convective signature"),
            ("Mars", "Uranus", "Mars-Uranus convective signature"),
        ):
            aspect = _major_aspect(chart, left, right, orb=6.0)
            if aspect:
                note = _rule(
                    layer="framework_layer" if chart_kind == "seasonal_ingress" else "trigger_layer",
                    chart_kind=chart_kind,
                    rule_id=f"{chart_kind}_{_normalize_id(left)}_{_normalize_id(right)}_convective",
                    label=label,
                    summary=f"{left} and {right} form a {aspect['aspect']} in the {chart_kind.replace('_', ' ')}, supporting severe-convective pressure.",
                    score=12 if chart_kind == "seasonal_ingress" else 15,
                    extra=aspect,
                )
                if chart_kind == "seasonal_ingress":
                    framework_notes.append(note)
                else:
                    trigger_notes.append(note)

    for chart_kind, chart in (("lunar_phase", lunar), ("forecast_chart", forecast)):
        for name, score in (("Mercury", 8), ("Mars", 8), ("Uranus", 10)):
            if _is_angular(chart, name):
                trigger_notes.append(
                    _rule(
                        layer="trigger_layer",
                        chart_kind=chart_kind,
                        rule_id=f"{chart_kind}_{_normalize_id(name)}_convective_angular",
                        label=f"{name} angular convective testimony",
                        summary=f"{name} is angular in the {chart_kind.replace('_', ' ')}, reinforcing abrupt severe-weather pressure.",
                        score=score,
                        extra={"planet": name},
                    )
                )

    lunar_kind = _normalize_id(lunar.get("kind"))
    if lunar_kind in {"first_quarter", "last_quarter"}:
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind=lunar_kind,
                rule_id=f"{lunar_kind}_dynamic_phase",
                label="Dynamic quarter-phase trigger",
                summary="The latest lunar trigger is a quarter phase, which the seed runtime treats as a more volatile short-term trigger for severe convection than a quiet background phase.",
                score=6,
            )
        )

    forecast_aspect_labels = {note.get("label") for note in trigger_notes if note.get("chart_kind") == "forecast_chart"}
    if {"Mercury-Uranus convective signature", "Mars-Uranus convective signature"} & forecast_aspect_labels and _is_angular(forecast, "Uranus") and (_is_angular(forecast, "Mercury") or _is_angular(forecast, "Mars")):
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="forecast_chart",
                rule_id="forecast_stacked_convective_structure",
                label="Stacked convective trigger structure",
                summary="Forecast-chart convective aspects stack with angular convective planets, which the runtime treats as a sharper severe-weather window than a broad seasonal risk band.",
                score=8,
            )
        )
    lunar_age_hours = timing.get("lunar_age_hours")
    if lunar_kind in {"first_quarter", "last_quarter"} and isinstance(lunar_age_hours, float):
        if lunar_age_hours <= 96.0:
            trigger_notes.append(
                _rule(
                    layer="trigger_layer",
                    chart_kind=lunar_kind,
                    rule_id=f"{lunar_kind}_fresh_convective_window",
                    label="Fresh convective trigger window",
                    summary="The quarter-phase trigger is still fresh in the short-term window, which the runtime treats as more event-focused than a later residual convective band.",
                    score=5,
                    extra={"lunar_age_hours": lunar_age_hours},
                )
            )
        elif lunar_age_hours >= 120.0:
            trigger_notes.append(
                _rule(
                    layer="trigger_layer",
                    chart_kind=lunar_kind,
                    rule_id=f"{lunar_kind}_aging_convective_trigger",
                    label="Aging convective trigger window",
                    summary="The quarter-phase trigger is aging out of its sharper short-term window, so the runtime discounts late broad convection slightly.",
                    score=-4,
                    extra={"lunar_age_hours": lunar_age_hours},
                )
            )

    locality_summary, locality_notes, locality_metrics = _build_locality_notes(
        "severe_convective_pressure",
        forecast,
        supporting_charts={"seasonal_ingress": seasonal, "lunar_phase": lunar},
    )
    if _is_angular(forecast, "Uranus") and len(_tight_angular_hits(forecast, ("Mercury", "Mars", "Uranus"), max_distance=7.0)) >= 2:
        locality_metrics["path_concentration"] = 6
    payload = _family_common_payload(
        family_id="severe_convective_pressure",
        family_label="Severe Convective Pressure",
        framework_notes=framework_notes,
        trigger_notes=trigger_notes,
        locality_notes=locality_notes,
        locality_metrics=locality_metrics,
        timing_metrics=timing,
        doctrine_note_ids=("weather_framework", "weather_locality_proxy", "severe_convective_pressure"),
        source_tags=("riske", "watters"),
        research_flags=("seed_runtime", "locality_proxy_only", "eclipse_runtime_deferred"),
    )
    payload["locality_summary"] = locality_summary
    return payload


def _evaluate_wind_event_pressure(context: ResolvedWeatherContext, charts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    seasonal = charts.get("spring_ingress") or charts.get("summer_ingress") or charts.get("autumn_ingress") or charts.get("winter_ingress") or {}
    lunar = charts.get("new_moon") or charts.get("full_moon") or charts.get("first_quarter") or charts.get("last_quarter") or {}
    forecast = charts.get("forecast_chart") or {}
    timing = _timing_metrics(context)

    framework_notes: List[Dict[str, Any]] = []
    trigger_notes: List[Dict[str, Any]] = []

    for chart_kind, chart in (("seasonal_ingress", seasonal), ("lunar_phase", lunar), ("forecast_chart", forecast)):
        mercury_score = _wind_angular_score(
            chart,
            "Mercury",
            max_score=10 if chart_kind == "forecast_chart" else 8,
            min_score=4 if chart_kind == "forecast_chart" else 3,
        )
        if mercury_score is not None:
            note = _rule(
                layer="framework_layer" if chart_kind == "seasonal_ingress" else "trigger_layer",
                chart_kind=chart_kind,
                rule_id=f"{chart_kind}_mercury_wind",
                label="Mercury angular wind testimony",
                summary=f"Mercury is angular in the {chart_kind.replace('_', ' ')}, preserving the seed wind/front doctrine.",
                score=mercury_score,
                extra={"planet": "Mercury", "angle_distance_deg": _angle_distance(chart, "Mercury")},
            )
            if chart_kind == "seasonal_ingress":
                framework_notes.append(note)
            else:
                trigger_notes.append(note)

    for chart_kind, chart in (("lunar_phase", lunar), ("forecast_chart", forecast)):
        aspect = _major_aspect(chart, "Mercury", "Uranus", orb=6.0)
        if aspect:
            trigger_notes.append(
                _rule(
                    layer="trigger_layer",
                    chart_kind=chart_kind,
                    rule_id=f"{chart_kind}_mercury_uranus_wind",
                    label="Mercury-Uranus wind/front signature",
                    summary=f"Mercury and Uranus form a {aspect['aspect']} in the {chart_kind.replace('_', ' ')}, supporting abrupt wind and frontal pressure.",
                    score=10,
                    extra=aspect,
                )
            )
        for left, right, label, max_score, min_score in (
            ("Mercury", "Mars", "Mercury-Mars wind/gust signature", 8, 3),
            ("Mercury", "Saturn", "Mercury-Saturn frontal compression", 6, 2),
        ):
            aspect = _major_aspect(chart, left, right, orb=6.0)
            if not aspect:
                continue
            trigger_notes.append(
                _rule(
                    layer="trigger_layer",
                    chart_kind=chart_kind,
                    rule_id=f"{chart_kind}_{_normalize_id(left)}_{_normalize_id(right)}_wind",
                    label=label,
                    summary=f"{left} and {right} form a {aspect['aspect']} in the {chart_kind.replace('_', ' ')}, reinforcing wind-front pressure in the seed runtime.",
                    score=_orb_scaled_score(aspect, max_score=max_score, min_score=min_score),
                    extra=aspect,
                )
            )

        mercury = _planet(chart, "Mercury") or {}
        mercury_active = any(
            note.get("chart_kind") == chart_kind and note.get("planet") == "Mercury"
            for note in trigger_notes
        ) or (
            chart_kind == "lunar_phase"
            and any(note.get("chart_kind") == chart_kind and note.get("planet") == "Mercury" for note in framework_notes)
        )
        if mercury_active and bool(mercury.get("retrograde")):
            trigger_notes.append(
                _rule(
                    layer="trigger_layer",
                    chart_kind=chart_kind,
                    rule_id=f"{chart_kind}_mercury_retrograde_wind",
                    label="Mercury retrograde wind amplifier",
                    summary=f"Mercury is retrograde while already active in the {chart_kind.replace('_', ' ')}, matching the source warning that retrograde Mercury sharpens storm-front and wind-event behavior.",
                    score=4,
                    extra={"planet": "Mercury", "retrograde": True},
                )
            )

    mercury_bridge_active = False
    for supporting_kind, supporting_chart in (("seasonal_ingress", seasonal), ("lunar_phase", lunar)):
        if not supporting_chart:
            continue
        bridge_aspect = _cross_chart_major_aspect(forecast, "Mercury", supporting_chart, "Mercury", orb=4.5)
        if not bridge_aspect or str(bridge_aspect.get("aspect") or "") not in {"conjunction", "square", "opposition"}:
            continue
        mercury_bridge_active = True
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="forecast_chart",
                rule_id=f"forecast_mercury_bridge_{supporting_kind}",
                label=f"Forecast Mercury bridge to {supporting_kind.replace('_', ' ')}",
                summary=f"Forecast Mercury forms a {bridge_aspect['aspect']} to Mercury in the {supporting_kind.replace('_', ' ')}, which the source method treats as a sharper event-day timing bridge than a broad weekly wind background.",
                score=_orb_scaled_score(
                    bridge_aspect,
                    max_score=12 if supporting_kind == "seasonal_ingress" else 10,
                    min_score=6 if supporting_kind == "seasonal_ingress" else 5,
                ),
                extra=bridge_aspect,
            )
        )
        if bool((_planet(supporting_chart, "Mercury") or {}).get("retrograde")):
            trigger_notes.append(
                _rule(
                    layer="trigger_layer",
                    chart_kind="forecast_chart",
                    rule_id=f"forecast_mercury_bridge_{supporting_kind}_retrograde",
                    label="Retrograde Mercury bridge amplifier",
                    summary="The support chart Mercury is retrograde while the forecast Mercury bridge perfects, which the source doctrine treats as a more negative and event-specific wind trigger than a background weekly signature.",
                    score=4,
                    extra={"supporting_chart_kind": supporting_kind, "retrograde": True},
                )
            )
        if _is_stationing(forecast, "Mercury") or _is_stationing(supporting_chart, "Mercury"):
            trigger_notes.append(
                _rule(
                    layer="trigger_layer",
                    chart_kind="forecast_chart",
                    rule_id=f"forecast_mercury_bridge_{supporting_kind}_stationing",
                    label="Stationing Mercury bridge amplifier",
                    summary="A Mercury bridge is active while Mercury is stationing in one of the linked layers, which the source doctrine treats as a sharper event-level wind trigger.",
                    score=4,
                    extra={"supporting_chart_kind": supporting_kind, "stationing": True},
                )
            )

    if _is_angular(forecast, "Uranus"):
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="forecast_chart",
                rule_id="forecast_uranus_wind_shock",
                label="Uranus angular wind shock",
                summary="Uranus is angular in the forecast chart, strengthening abrupt wind-event pressure.",
                score=8,
                extra={"planet": "Uranus"},
            )
        )

    wind_structure_groups = {
        "mercury_angular": any(note.get("label") == "Mercury angular wind testimony" for note in [*framework_notes, *trigger_notes]),
        "mercury_uranus": any(note.get("label") == "Mercury-Uranus wind/front signature" for note in trigger_notes),
        "mercury_mars": any(note.get("label") == "Mercury-Mars wind/gust signature" for note in trigger_notes),
        "mercury_saturn": any(note.get("label") == "Mercury-Saturn frontal compression" for note in trigger_notes),
        "uranus_angular": any(note.get("label") == "Uranus angular wind shock" for note in trigger_notes),
        "mercury_bridge": any(str(note.get("label") or "").startswith("Forecast Mercury bridge to ") for note in trigger_notes),
    }
    active_group_count = sum(1 for value in wind_structure_groups.values() if value)
    if active_group_count >= 3 and wind_structure_groups["mercury_angular"] and wind_structure_groups["uranus_angular"]:
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="forecast_chart",
                rule_id="forecast_stacked_wind_structure",
                label="Stacked frontal structure",
                summary="Mercury wind testimony, frontal aspects, and Uranian shock stack together, which the runtime treats as a sharper wind-event structure than a broad breezy background.",
                score=6,
            )
        )
    elif active_group_count <= 1 and wind_structure_groups["mercury_angular"]:
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="forecast_chart",
                rule_id="forecast_broad_wind_background",
                label="Broad wind background without reinforced front structure",
                summary="The chart shows broad Mercury wind testimony without enough reinforcement from sharper front signatures, so the runtime discounts event-level wind concentration slightly.",
                score=-6,
            )
        )
    lunar_age_hours = timing.get("lunar_age_hours")
    if (
        not mercury_bridge_active
        and isinstance(lunar_age_hours, float)
        and lunar_age_hours >= 144.0
        and (wind_structure_groups["mercury_uranus"] or wind_structure_groups["mercury_saturn"])
    ):
        trigger_notes.append(
            _rule(
                layer="trigger_layer",
                chart_kind="lunar_phase",
                rule_id="aging_wind_background_band",
                label="Aging weekly wind background",
                summary="The weekly wind background is already aging and no sharper Mercury bridge has formed yet, so the runtime discounts early-band wind pressure slightly.",
                score=-6,
                extra={"lunar_age_hours": lunar_age_hours},
            )
        )

    locality_summary, locality_notes, locality_metrics = _build_locality_notes(
        "wind_event_pressure",
        forecast,
        supporting_charts={"seasonal_ingress": seasonal, "lunar_phase": lunar},
    )
    if wind_structure_groups["mercury_angular"] and active_group_count >= 3 and locality_metrics.get("tight_hit_count", 0) >= 1:
        locality_metrics["path_concentration"] = 5 + min(3, int(locality_metrics.get("tight_hit_count") or 0))
    if mercury_bridge_active and locality_metrics.get("path_concentration", 0) > 0:
        locality_metrics["path_concentration"] = max(int(locality_metrics.get("path_concentration") or 0), 8)
    payload = _family_common_payload(
        family_id="wind_event_pressure",
        family_label="Wind Event Pressure",
        framework_notes=framework_notes,
        trigger_notes=trigger_notes,
        locality_notes=locality_notes,
        locality_metrics=locality_metrics,
        timing_metrics=timing,
        doctrine_note_ids=("weather_framework", "weather_locality_proxy", "wind_event_pressure"),
        source_tags=("riske", "bonatti", "watters"),
        research_flags=("seed_runtime", "locality_proxy_only", "eclipse_runtime_deferred"),
    )
    payload["locality_summary"] = locality_summary
    return payload


def evaluate_weather_family_context(context: ResolvedWeatherContext) -> Dict[str, Any]:
    family_id = _normalize_id((context.family or {}).get("id"))
    charts = _chart_index(context.chart_resolution or {})

    if family_id == "flood_risk":
        return _evaluate_flood_risk(context, charts)
    if family_id == "hurricane_pressure":
        return _evaluate_hurricane_pressure(context, charts)
    if family_id == "severe_convective_pressure":
        return _evaluate_severe_convective_pressure(context, charts)
    if family_id == "wind_event_pressure":
        return _evaluate_wind_event_pressure(context, charts)

    raise ValueError(f"Unsupported weather family: {family_id}")

