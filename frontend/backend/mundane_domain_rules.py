from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from mundane_benchmark_profiles import calibrate_domain_score
from mundane_models import ResolvedMundaneContext
from mundane_trigger_rules import index_trigger_profiles

_BENEFICS = {"Jupiter", "Venus"}
_MALEFICS = {"Mars", "Saturn"}
_ANGULAR_HOUSES = {1, 4, 7, 10}


def _normalize_id(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _chart_from_resolution(context: ResolvedMundaneContext, *, kind: Optional[str] = None) -> Optional[Dict[str, Any]]:
    resolution = context.chart_resolution if isinstance(context.chart_resolution, dict) else {}
    primary = resolution.get("primary_chart")
    if kind is None:
        return primary if isinstance(primary, dict) else None
    if isinstance(primary, dict) and _normalize_id(primary.get("kind")) == _normalize_id(kind):
        return primary
    for chart in resolution.get("supporting_charts") or []:
        if isinstance(chart, dict) and _normalize_id(chart.get("kind")) == _normalize_id(kind):
            return chart
    return None


def _planets(chart: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(chart, dict):
        return {}
    planets = chart.get("planets") or {}
    if not isinstance(planets, dict):
        return {}
    return {str(name): info for name, info in planets.items() if isinstance(info, dict)}


def _planet_house(chart: Optional[Dict[str, Any]], planet_name: str) -> Optional[int]:
    info = _planets(chart).get(planet_name)
    if not info:
        return None
    try:
        return int(info.get("house"))
    except Exception:
        return None


def _planet_longitude(chart: Optional[Dict[str, Any]], planet_name: str) -> Optional[float]:
    info = _planets(chart).get(planet_name)
    if not info:
        return None
    try:
        return float(info.get("longitude"))
    except Exception:
        return None


def _planet_retrograde(chart: Optional[Dict[str, Any]], planet_name: str) -> bool:
    info = _planets(chart).get(planet_name)
    return bool(info and info.get("retrograde"))


def _planet_angular(chart: Optional[Dict[str, Any]], planet_name: str) -> bool:
    house = _planet_house(chart, planet_name)
    return house in _ANGULAR_HOUSES if house is not None else False


def _normalize_angle(value: Any) -> float:
    return float(value or 0.0) % 360.0


def _angle_sep(a: float, b: float) -> float:
    return abs((((_normalize_angle(a) - _normalize_angle(b) + 180.0) % 360.0) - 180.0))


def _chart_angle_points(chart: Optional[Dict[str, Any]]) -> List[Tuple[str, float]]:
    if not isinstance(chart, dict):
        return []
    angles = chart.get("angles") or {}
    if not isinstance(angles, dict):
        return []
    points: List[Tuple[str, float]] = []
    try:
        asc = float(angles.get("ascendant"))
        points.append(("ascendant", _normalize_angle(asc)))
        points.append(("descendant", _normalize_angle(asc + 180.0)))
    except Exception:
        pass
    try:
        mc = float(angles.get("midheaven"))
        points.append(("midheaven", _normalize_angle(mc)))
        points.append(("imum_coeli", _normalize_angle(mc + 180.0)))
    except Exception:
        pass
    return points


def _planet_angle_detail(chart: Optional[Dict[str, Any]], planet_name: str) -> Optional[Dict[str, Any]]:
    longitude = _planet_longitude(chart, planet_name)
    if longitude is None:
        return None
    angle_points = _chart_angle_points(chart)
    if not angle_points:
        return None
    nearest_label, nearest_longitude = min(angle_points, key=lambda item: _angle_sep(longitude, item[1]))
    return {
        "planet": planet_name,
        "angle": nearest_label,
        "distance_deg": round(_angle_sep(longitude, nearest_longitude), 3),
        "house": _planet_house(chart, planet_name),
    }


def _proximity_bonus(distance_deg: Optional[float], *, max_bonus: int, within_deg: float = 15.0) -> int:
    if distance_deg is None:
        return 0
    try:
        distance = float(distance_deg)
    except Exception:
        return 0
    if distance < 0 or distance > within_deg:
        return 0
    scaled = max_bonus * (1.0 - (distance / within_deg))
    return max(0, int(round(scaled)))


def _planet_angular_weight(
    chart: Optional[Dict[str, Any]],
    planet_name: str,
    *,
    base_weight: int,
    max_proximity_bonus: int = 8,
) -> Tuple[int, Optional[Dict[str, Any]]]:
    detail = _planet_angle_detail(chart, planet_name)
    if not detail or detail.get("house") not in _ANGULAR_HOUSES:
        return 0, detail
    weight = int(base_weight) + _proximity_bonus(detail.get("distance_deg"), max_bonus=max_proximity_bonus)
    return weight, detail


def _ruler_signal_weight(summary: Optional[Dict[str, Any]], *, base_weight: int, max_proximity_bonus: int = 6) -> int:
    if not isinstance(summary, dict):
        return 0
    try:
        house_position = int(summary.get("house_position"))
    except Exception:
        return 0
    if house_position not in _ANGULAR_HOUSES:
        return 0
    return int(base_weight) + _proximity_bonus(summary.get("angle_distance_deg"), max_bonus=max_proximity_bonus)


def _planet_in_houses(chart: Optional[Dict[str, Any]], planet_name: str, houses: Iterable[int]) -> bool:
    house = _planet_house(chart, planet_name)
    allowed = {int(value) for value in houses}
    return house in allowed if house is not None else False


def _planet_in_house(chart: Optional[Dict[str, Any]], planet_name: str, house_number: int) -> bool:
    return _planet_in_houses(chart, planet_name, {house_number})


def _first_present(items: Iterable[Optional[str]]) -> Optional[str]:
    for item in items:
        if item:
            return str(item)
    return None


def _house_ruler(chart: Optional[Dict[str, Any]], house_number: int) -> Optional[str]:
    if not isinstance(chart, dict):
        return None
    house_rulers = chart.get("house_rulers") or {}
    if not isinstance(house_rulers, dict):
        return None
    value = house_rulers.get(str(house_number)) or house_rulers.get(house_number)
    return str(value) if value else None


def _house_ruler_position(chart: Optional[Dict[str, Any]], house_number: int) -> Optional[int]:
    ruler = _house_ruler(chart, house_number)
    if not ruler:
        return None
    return _planet_house(chart, ruler)


def _signals(context: ResolvedMundaneContext) -> Dict[str, Any]:
    resolution = context.chart_resolution if isinstance(context.chart_resolution, dict) else {}
    signals = resolution.get("signals") or {}
    return signals if isinstance(signals, dict) else {}


def _normalize_place(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _uses_capital_chart_context(context: ResolvedMundaneContext) -> bool:
    return _normalize_id((context.location_context or {}).get("id")) == "capital_chart"


def _reference_location(context: ResolvedMundaneContext) -> str:
    event_context = context.event_context if isinstance(context.event_context, dict) else {}
    return _normalize_place(event_context.get("reference_location") or event_context.get("event_location"))


def _capital_alignment(context: ResolvedMundaneContext) -> Dict[str, Any]:
    polity = context.polity if isinstance(context.polity, dict) else {}
    candidate = _reference_location(context)
    capital = _normalize_place(polity.get("capital") or polity.get("default_location"))
    if not candidate or not capital:
        return {"matches": False, "candidate": candidate, "capital": capital}
    return {
        "matches": candidate == capital,
        "candidate": candidate,
        "capital": capital,
    }


def _capital_chart_penalty_rule(
    context: ResolvedMundaneContext,
    *,
    weight: int,
    detail: str,
    source_tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    if not _uses_capital_chart_context(context):
        return None
    capital_alignment = _capital_alignment(context)
    if capital_alignment.get("matches"):
        return None
    candidate = capital_alignment.get("candidate") or "the resolved location"
    capital = capital_alignment.get("capital") or "the polity capital"
    return _rule(
        "off_capital_displacement",
        "Off-capital displacement",
        -abs(int(weight)),
        f"{detail} The resolved cell is {candidate}, not {capital}.",
        source_tags=source_tags or ["green_ingress"],
    )


def _activation_hits(context: ResolvedMundaneContext) -> List[Dict[str, Any]]:
    hits = _signals(context).get("activation_hits") or []
    return [item for item in hits if isinstance(item, dict)]


def _trigger_profiles(context: ResolvedMundaneContext, *trigger_ids: str) -> Dict[str, Dict[str, Any]]:
    return index_trigger_profiles(context, trigger_ids=trigger_ids)


def _cycle_trigger_context(profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(profile, dict):
        return {}
    metrics = profile.get("metrics") if isinstance(profile.get("metrics"), dict) else {}
    evidence = profile.get("evidence") if isinstance(profile.get("evidence"), list) else []
    cycle_context = evidence[0] if evidence and isinstance(evidence[0], dict) else {}
    return {
        "active": bool(profile.get("active")),
        "score": int(profile.get("score") or 0),
        "phase": metrics.get("cycle_phase") or cycle_context.get("cycle_phase"),
        "sign": metrics.get("conjunction_sign") or cycle_context.get("conjunction_sign"),
        "nearest_distance_years": metrics.get("nearest_distance_years") or cycle_context.get("nearest_distance_years"),
        "turning_window_level": metrics.get("turning_window_level") or cycle_context.get("turning_window_level"),
        "nearest_conjunction_datetime": cycle_context.get("nearest_conjunction_datetime"),
    }


def _assessment_level(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "elevated"
    return "quiet"


def _finalize(
    *,
    domain_id: str,
    axis: str,
    base_summary: str,
    matched_rules: List[Dict[str, Any]],
    cautions: Iterable[str],
    research_flags: Iterable[str],
) -> Dict[str, Any]:
    raw_score = max(0, min(100, sum(int(rule.get("weight") or 0) for rule in matched_rules)))
    calibration = calibrate_domain_score(domain_id, raw_score)
    score = int(calibration.get("adjusted_score") or 0)
    profile = calibration.get("profile") or {}
    caution_items = list(dict.fromkeys(str(item) for item in cautions if str(item).strip()))
    if profile.get("gaps"):
        caution_items.append(
            "Benchmark calibration gaps: " + ", ".join(str(item) for item in profile.get("gaps") or [])
        )
    if matched_rules:
        top_rules = sorted(matched_rules, key=lambda row: (-int(row.get("weight") or 0), str(row.get("label") or "")))
        top_labels = ", ".join(str(row.get("label") or "") for row in top_rules[:3] if row.get("label"))
        summary = f"{base_summary} Primary drivers: {top_labels}." if top_labels else base_summary
    else:
        summary = f"{base_summary} No strong matched rules were found in the current resolved chart set."
    return {
        "domain_id": domain_id,
        "axis": axis,
        "raw_score": raw_score,
        "score": score,
        "raw_level": _assessment_level(raw_score),
        "level": _assessment_level(score),
        "summary": summary,
        "matched_rules": matched_rules,
        "cautions": caution_items,
        "research_flags": list(dict.fromkeys(str(item) for item in research_flags if str(item).strip())),
        "calibration": {
            "coverage_tier": str(profile.get("coverage_tier") or "unseeded"),
            "unique_case_count": int(profile.get("unique_case_count") or 0),
            "dataset_row_count": int(profile.get("dataset_row_count") or 0),
            "distinct_source_count": int(profile.get("distinct_source_count") or 0),
            "distinct_sources": list(profile.get("distinct_sources") or []),
            "benchmark_types": dict(profile.get("benchmark_types") or {}),
            "seed_quality_counts": dict(profile.get("seed_quality_counts") or {}),
            "chart_basis_counts": dict(profile.get("chart_basis_counts") or {}),
            "confidence_factor": float(profile.get("confidence_factor") or 0.8),
            "score_cap": int(profile.get("score_cap") or 70),
            "gaps": list(profile.get("gaps") or []),
        },
    }


def _rule(rule_id: str, label: str, weight: int, detail: str, *, source_tags: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "id": rule_id,
        "label": label,
        "weight": int(weight),
        "detail": detail,
        "source_tags": list(source_tags or []),
    }


def _war_signal_state(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    signals = _signals(context)
    trigger_profiles = _trigger_profiles(context, "angularity", "retrograde_mars", "eclipse_degree_activation")
    aggressor_summary = signals.get("aggressor_house") if isinstance(signals.get("aggressor_house"), dict) else None
    defender_summary = signals.get("defender_house") if isinstance(signals.get("defender_house"), dict) else None
    mars_weight, mars_detail = _planet_angular_weight(chart, "Mars", base_weight=16, max_proximity_bonus=10)
    saturn_weight, saturn_detail = _planet_angular_weight(chart, "Saturn", base_weight=8, max_proximity_bonus=6)
    aggressor_weight = _ruler_signal_weight(aggressor_summary, base_weight=10, max_proximity_bonus=8)
    defender_weight = _ruler_signal_weight(defender_summary, base_weight=6, max_proximity_bonus=6)
    moon_detail = _planet_angle_detail(chart, "Moon")
    activation_hits = _activation_hits(context)
    activation_profile = trigger_profiles.get("eclipse_degree_activation") or {}
    retrograde_profile = trigger_profiles.get("retrograde_mars") or {}
    angularity_profile = trigger_profiles.get("angularity") or {}
    mars_retrograde = bool(retrograde_profile.get("active") or signals.get("mars_retrograde") or _planet_retrograde(chart, "Mars"))
    return {
        "chart": chart,
        "signals": signals,
        "aggressor_summary": aggressor_summary,
        "defender_summary": defender_summary,
        "mars_weight": mars_weight,
        "mars_detail": mars_detail,
        "saturn_weight": saturn_weight,
        "saturn_detail": saturn_detail,
        "aggressor_weight": aggressor_weight,
        "defender_weight": defender_weight,
        "moon_detail": moon_detail,
        "activation_hits": activation_hits,
        "activation_profile": activation_profile,
        "retrograde_profile": retrograde_profile,
        "angularity_profile": angularity_profile,
        "mars_retrograde": mars_retrograde,
    }


def _evaluate_war_outbreak(context: ResolvedMundaneContext) -> Dict[str, Any]:
    state = _war_signal_state(context)
    chart = state["chart"]
    chart_kind = _normalize_id((chart or {}).get("kind"))
    aggressor_summary = state["aggressor_summary"]
    defender_summary = state["defender_summary"]
    matched: List[Dict[str, Any]] = []
    cautions = []
    chart_mismatch = chart_kind != "war_event"

    if isinstance(chart, dict) and chart_kind == "war_event":
        matched.append(
            _rule(
                "war_outbreak_event_anchor",
                "War-event anchor",
                8,
                "The resolved primary chart is a war-event chart cast for first hostilities, which is the preferred basis for outbreak judgment.",
                source_tags=["watters_war_houses"],
            )
        )

    if state["mars_weight"]:
        detail = "Mars is angular"
        if state["mars_detail"] and state["mars_detail"].get("distance_deg") is not None:
            detail += f", nearest the {state['mars_detail'].get('angle')} within {state['mars_detail'].get('distance_deg')}deg"
        detail += ", matching an immediate martial outbreak signature."
        matched.append(
            _rule(
                "war_outbreak_mars_angular",
                "Mars angular",
                state["mars_weight"],
                detail,
                source_tags=["watters_war_houses", "green_public_affairs"],
            )
        )

    if state["aggressor_weight"] and aggressor_summary:
        matched.append(
            _rule(
                "war_outbreak_aggressor_ruler_angular",
                "Aggressor ruler angular",
                state["aggressor_weight"],
                f"The first-house ruler {aggressor_summary.get('ruler')} is angular, nearest the {aggressor_summary.get('closest_angle') or 'angle'} within {aggressor_summary.get('angle_distance_deg') or 'unknown'}deg, putting the initiating side immediately on stage.",
                source_tags=["watters_war_houses"],
            )
        )

    if state["moon_detail"] and state["moon_detail"].get("house") in {1, 7}:
        moon_weight = 6 + _proximity_bonus(state["moon_detail"].get("distance_deg"), max_bonus=4)
        matched.append(
            _rule(
                "war_outbreak_moon_axis",
                "Moon on conflict axis",
                moon_weight,
                f"The Moon is on the 1st/7th conflict axis, nearest the {state['moon_detail'].get('angle') or 'angle'} within {state['moon_detail'].get('distance_deg') or 'unknown'}deg, making the outbreak visible and immediate.",
                source_tags=["green_public_affairs", "watters_war_houses"],
            )
        )

    if state["aggressor_weight"] and state["defender_weight"]:
        matched.append(
            _rule(
                "war_outbreak_open_polarity",
                "Open conflict polarity",
                10,
                "Both aggressor and defender testimonies are active at the opening chart, matching overt first-hostilities polarity rather than latent tension.",
                source_tags=["watters_war_houses"],
            )
        )

    if state["activation_profile"].get("active"):
        matched.append(
            _rule(
                "war_outbreak_activation_support",
                "Activation support",
                max(8, int(state["activation_profile"].get("score") or 0)),
                f"{len(state['activation_hits'])} activation hit(s) reinforce the outbreak chart, but they remain secondary to the first-hostilities frame.",
                source_tags=["watters_eclipse_degree"],
            )
        )

    assessment = _finalize(
        domain_id="war_outbreak",
        axis="war_outbreak_pressure",
        base_summary="War outbreak is evaluated from first-hostilities anchoring, immediate martial onset, and direct aggressor-defender polarity.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )
    if not chart_mismatch:
        return assessment

    downgraded_raw_score = int(round(float(assessment.get("raw_score") or 0.0) * 0.45))
    downgraded_calibration = calibrate_domain_score("war_outbreak", downgraded_raw_score)
    downgraded_profile = downgraded_calibration.get("profile") or {}
    caution_items = list(dict.fromkeys([
        *(assessment.get("cautions") or []),
        "War outbreak is downgraded outside a war-event anchor; use campaign escalation or military reversal for non-event charts.",
    ]))
    research_flags = list(dict.fromkeys([*(assessment.get("research_flags") or []), "outbreak_chart_mismatch"]))
    assessment.update(
        raw_score=downgraded_raw_score,
        score=int(downgraded_calibration.get("adjusted_score") or 0),
        raw_level=_assessment_level(downgraded_raw_score),
        level=_assessment_level(int(downgraded_calibration.get("adjusted_score") or 0)),
        cautions=caution_items,
        research_flags=research_flags,
        calibration={
            "coverage_tier": str(downgraded_profile.get("coverage_tier") or "unseeded"),
            "unique_case_count": int(downgraded_profile.get("unique_case_count") or 0),
            "dataset_row_count": int(downgraded_profile.get("dataset_row_count") or 0),
            "distinct_source_count": int(downgraded_profile.get("distinct_source_count") or 0),
            "distinct_sources": list(downgraded_profile.get("distinct_sources") or []),
            "benchmark_types": dict(downgraded_profile.get("benchmark_types") or {}),
            "seed_quality_counts": dict(downgraded_profile.get("seed_quality_counts") or {}),
            "chart_basis_counts": dict(downgraded_profile.get("chart_basis_counts") or {}),
            "confidence_factor": float(downgraded_profile.get("confidence_factor") or 0.8),
            "score_cap": int(downgraded_profile.get("score_cap") or 70),
            "gaps": list(downgraded_profile.get("gaps") or []),
        },
    )
    return assessment


def _evaluate_campaign_escalation(context: ResolvedMundaneContext) -> Dict[str, Any]:
    state = _war_signal_state(context)
    chart = state["chart"]
    matched: List[Dict[str, Any]] = []
    cautions = []
    malefic_pressure = 0

    if state["mars_weight"]:
        malefic_pressure += state["mars_weight"]
    if state["saturn_weight"]:
        malefic_pressure += state["saturn_weight"]
        detail = "Saturn is angular and adds severity, blockade, or sustained burden to the campaign."
        if state["saturn_detail"] and state["saturn_detail"].get("distance_deg") is not None:
            detail = f"Saturn is angular, nearest the {state['saturn_detail'].get('angle')} within {state['saturn_detail'].get('distance_deg')}deg, adding attritional severity to the campaign."
        matched.append(
            _rule(
                "campaign_escalation_saturn_angular",
                "Saturn angular",
                state["saturn_weight"],
                detail,
                source_tags=["green_public_affairs", "watters_war_houses"],
            )
        )

    if state["aggressor_weight"] and state["defender_weight"]:
        matched.append(
            _rule(
                "campaign_escalation_active_polarity",
                "Escalating conflict polarity",
                10,
                "Both aggressor and defender testimonies remain active, matching a campaign that has broadened beyond a single strike or declaration.",
                source_tags=["watters_war_houses"],
            )
        )

    if state["defender_weight"] and state["defender_summary"]:
        matched.append(
            _rule(
                "campaign_escalation_defender_angular",
                "Defender ruler angular",
                state["defender_weight"] + 2,
                f"The seventh-house ruler {state['defender_summary'].get('ruler')} is angular, nearest the {state['defender_summary'].get('closest_angle') or 'angle'} within {state['defender_summary'].get('angle_distance_deg') or 'unknown'}deg, showing that the opposing side is fully engaged in an active campaign.",
                source_tags=["watters_war_houses"],
            )
        )

    if state["saturn_weight"] and state["mars_weight"]:
        matched.append(
            _rule(
                "campaign_escalation_joint_malefics",
                "Joint malefic pressure",
                12,
                "Mars and Saturn are both active, matching campaign intensification, blockade, attrition, or widening destructive force.",
                source_tags=["green_public_affairs", "annotated_raphael_war_doctrine"],
            )
        )

    if malefic_pressure and (state["aggressor_weight"] or state["defender_weight"]):
        matched.append(
            _rule(
                "campaign_escalation_axis_pressure",
                "Malefic pressure on active war axis",
                10,
                "Sustained malefic pressure is combining with an active war polarity, which fits escalation beyond a single opening action.",
                source_tags=["watters_war_houses", "green_public_affairs"],
            )
        )

    if _planet_in_house(chart, "Saturn", 6):
        matched.append(
            _rule(
                "campaign_escalation_saturn_sixth",
                "Saturn in the sixth",
                14,
                "Saturn in the sixth burdens armed forces, supplies, or service capacity, matching attritional campaign strain.",
                source_tags=["watters_war_houses", "annotated_raphael_war_doctrine"],
            )
        )

    if state["activation_profile"].get("active"):
        matched.append(
            _rule(
                "campaign_escalation_activation",
                "Eclipse-degree activation",
                max(18, int(state["activation_profile"].get("score") or 0)),
                f"{len(state['activation_hits'])} activation hit(s) were found against the eclipse chart, supporting campaign broadening or renewed intensification.",
                source_tags=["watters_eclipse_degree"],
            )
        )

    return _finalize(
        domain_id="campaign_escalation",
        axis="campaign_escalation_pressure",
        base_summary="Campaign escalation is evaluated from sustained malefic pressure, active war polarity, attritional signatures, and follow-on activation hits.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_military_reversal(context: ResolvedMundaneContext) -> Dict[str, Any]:
    state = _war_signal_state(context)
    chart = state["chart"]
    matched: List[Dict[str, Any]] = []
    cautions = ["Military reversal should be read as corroborated defeat pressure, not as a standalone victory guarantee for the other side."]

    if state["mars_retrograde"]:
        matched.append(
            _rule(
                "military_reversal_mars_retrograde",
                "Mars retrograde",
                20,
                "Retrograde Mars raises failed-aggression and reversal risk for the side that presses war under its condition.",
                source_tags=["watters_retrograde_mars"],
            )
        )

    if state["saturn_weight"]:
        detail = "Saturn is angular, increasing defeat, obstruction, or attrition pressure in the conflict."
        if state["saturn_detail"] and state["saturn_detail"].get("distance_deg") is not None:
            detail = f"Saturn is angular, nearest the {state['saturn_detail'].get('angle')} within {state['saturn_detail'].get('distance_deg')}deg, increasing defeat, obstruction, or attritional pressure in the conflict."
        matched.append(
            _rule(
                "military_reversal_saturn_angular",
                "Saturn angular",
                state["saturn_weight"] + 2,
                detail,
                source_tags=["green_public_affairs", "watters_war_houses"],
            )
        )

    if _planet_in_house(chart, "Saturn", 6):
        matched.append(
            _rule(
                "military_reversal_saturn_sixth",
                "Saturn in the sixth",
                14,
                "Saturn in the sixth burdens armies, supplies, and the service machine, matching attrition and eventual weakening of the war effort.",
                source_tags=["watters_war_houses", "annotated_raphael_war_doctrine"],
            )
        )

    if state["defender_weight"] and state["defender_summary"]:
        matched.append(
            _rule(
                "military_reversal_defender_angular",
                "Defender ruler angular",
                state["defender_weight"] + 4,
                f"The seventh-house ruler {state['defender_summary'].get('ruler')} is angular, nearest the {state['defender_summary'].get('closest_angle') or 'angle'} within {state['defender_summary'].get('angle_distance_deg') or 'unknown'}deg, showing resilient or recovering opposition.",
                source_tags=["watters_war_houses"],
            )
        )

    defender_balance = state["defender_weight"] + (6 if state["mars_retrograde"] else 0)
    if state["defender_weight"] and defender_balance >= max(1, state["aggressor_weight"]):
        matched.append(
            _rule(
                "military_reversal_defender_resilience",
                "Defender resilience",
                10,
                "Defender testimony is holding at least as strongly as the aggressor testimony once retrograde or setback pressure is taken into account, matching reversal risk against the side that opened or dominated early action.",
                source_tags=["watters_war_houses", "watters_retrograde_mars"],
            )
        )

    if state["mars_retrograde"] and state["aggressor_weight"]:
        matched.append(
            _rule(
                "military_reversal_aggressor_overreach",
                "Aggressor overreach under retrograde Mars",
                10,
                "The aggressor testimony is active under retrograde Mars, matching overreach, misjudgment, and eventual reversal rather than durable conquest.",
                source_tags=["watters_retrograde_mars"],
            )
        )

    if state["activation_profile"].get("active"):
        matched.append(
            _rule(
                "military_reversal_activation",
                "Eclipse-degree activation",
                max(14, int(state["activation_profile"].get("score") or 0)),
                f"{len(state['activation_hits'])} activation hit(s) were found against the eclipse chart, supporting a balance shift or defeat phase inside the war.",
                source_tags=["watters_eclipse_degree", "annotated_raphael_war_doctrine"],
            )
        )

    return _finalize(
        domain_id="military_reversal",
        axis="military_reversal_pressure",
        base_summary="Military reversal is evaluated from retrograde martial strain, attritional Saturn signatures, defender-strength testimony, and balance-shifting activations.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_war_conflict(context: ResolvedMundaneContext) -> Dict[str, Any]:
    outbreak = _evaluate_war_outbreak(context)
    escalation = _evaluate_campaign_escalation(context)
    reversal = _evaluate_military_reversal(context)
    matched: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for ruleset in (
        outbreak.get("matched_rules") or [],
        escalation.get("matched_rules") or [],
        reversal.get("matched_rules") or [],
    ):
        for source in ruleset:
            if not isinstance(source, dict):
                continue
            rule_id = str(source.get("id") or "")
            if rule_id in seen_ids:
                continue
            seen_ids.add(rule_id)
            matched.append(source)
    cautions = list(
        dict.fromkeys(
            [
                *(outbreak.get("cautions") or []),
                *(escalation.get("cautions") or []),
                *(reversal.get("cautions") or []),
            ]
        )
    )
    research_flags = list(dict.fromkeys([*context.research_flags, "compatibility_umbrella"]))

    return _finalize(
        domain_id="war_conflict",
        axis="war_pressure",
        base_summary="War conflict is evaluated as a compatibility umbrella merging outbreak, campaign-escalation, and military-reversal pressure.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=research_flags,
    )


def _evaluate_leadership_transition(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    trigger_profiles = _trigger_profiles(context, "retrograde_mars")
    matched: List[Dict[str, Any]] = []
    cautions = []
    capital_alignment = _capital_alignment(context)

    sun_weight, sun_detail = _planet_angular_weight(chart, "Sun", base_weight=10, max_proximity_bonus=8)
    if sun_weight:
        detail = "Solar authority is highly visible in the resolved chart, raising the public exposure of leadership outcomes."
        if sun_detail and sun_detail.get("distance_deg") is not None:
            detail = f"Solar authority is highly visible, with the Sun nearest the {sun_detail.get('angle')} within {sun_detail.get('distance_deg')}deg."
        matched.append(_rule("leadership_sun_angular", "Sun angular", sun_weight, detail, source_tags=["green_public_affairs"]))
    moon_weight, moon_detail = _planet_angular_weight(chart, "Moon", base_weight=6, max_proximity_bonus=5)
    if moon_weight:
        detail = "The Moon is angular, putting the public body and transition atmosphere visibly on stage."
        if moon_detail and moon_detail.get("distance_deg") is not None:
            detail = f"The Moon is angular, nearest the {moon_detail.get('angle')} within {moon_detail.get('distance_deg')}deg, increasing the public visibility of the transition atmosphere."
        matched.append(_rule("leadership_moon_angular", "Moon angular", moon_weight, detail, source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Sun", 10):
        matched.append(_rule("leadership_sun_tenth", "Sun in the tenth", 10, "The Sun occupies the tenth house, strengthening direct executive or royal visibility in the transition chart.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Moon", 10):
        matched.append(_rule("leadership_moon_tenth", "Moon in the tenth", 6, "The Moon in the tenth makes the leadership event visibly public and politically immediate.", source_tags=["green_public_affairs"]))
    tenth_ruler = _house_ruler(chart, 10)
    if tenth_ruler:
        ruler_weight, ruler_detail = _planet_angular_weight(chart, tenth_ruler, base_weight=12, max_proximity_bonus=8)
        if ruler_weight:
            matched.append(
                _rule(
                    "leadership_tenth_ruler_angular",
                    "Tenth-house ruler angular",
                    ruler_weight,
                    f"The tenth-house ruler {tenth_ruler} is angular, nearest the {(ruler_detail or {}).get('angle') or 'angle'} within {(ruler_detail or {}).get('distance_deg') or 'unknown'}deg, making the office-holder or transition fully visible.",
                    source_tags=["green_public_affairs"],
                )
            )
    for malefic in ("Mars", "Saturn"):
        weight, detail = _planet_angular_weight(chart, malefic, base_weight=8, max_proximity_bonus=6)
        if weight:
            text = f"{malefic} is angular, matching leadership strain and hard transition doctrine."
            if detail and detail.get("distance_deg") is not None:
                text = f"{malefic} is angular, nearest the {detail.get('angle')} within {detail.get('distance_deg')}deg, matching leadership strain and hard transition doctrine."
            matched.append(_rule(f"leadership_{_normalize_id(malefic)}_angular", f"{malefic} angular", weight, text, source_tags=["green_public_affairs"]))
    if tenth_ruler and _planet_retrograde(chart, tenth_ruler):
        matched.append(_rule("leadership_tenth_ruler_retrograde", "Tenth-house ruler retrograde", 16, f"The tenth-house ruler {tenth_ruler} is retrograde, weakening executive continuity and transition stability.", source_tags=["green_public_affairs", "watters_retrograde_mars"]))
    if (trigger_profiles.get("retrograde_mars") or {}).get("active"):
        matched.append(_rule("leadership_mars_retrograde", "Mars retrograde", 14, "Retrograde Mars inside a leadership chart is a warning for attritional, unstable, or reversive office change.", source_tags=["watters_retrograde_mars"]))
        cautions.append("Retrograde Mars is a transition warning; it does not by itself prove death, coup, or removal.")
    activation_hits = _activation_hits(context)
    if activation_hits:
        matched.append(_rule("leadership_activation_hits", "Activation hits present", 14, "The overlay chart shows activation hits that can sharpen leadership transition stress.", source_tags=["watters_eclipse_degree"]))
    jupiter_weight, jupiter_detail = _planet_angular_weight(chart, "Jupiter", base_weight=4, max_proximity_bonus=4)
    if jupiter_weight:
        text = "Angular Jupiter can moderate transition strain and preserve orderly succession."
        if jupiter_detail and jupiter_detail.get("distance_deg") is not None:
            text = f"Jupiter is angular, nearest the {jupiter_detail.get('angle')} within {jupiter_detail.get('distance_deg')}deg, moderating transition strain."
        matched.append(_rule("leadership_jupiter_angular_support", "Jupiter angular", -jupiter_weight, text, source_tags=["green_public_affairs"]))
    venus_weight, venus_detail = _planet_angular_weight(chart, "Venus", base_weight=3, max_proximity_bonus=3)
    if venus_weight:
        text = "Angular Venus can soften public rupture and preserve ceremonial or orderly transfer."
        if venus_detail and venus_detail.get("distance_deg") is not None:
            text = f"Venus is angular, nearest the {venus_detail.get('angle')} within {venus_detail.get('distance_deg')}deg, softening transition rupture."
        matched.append(_rule("leadership_venus_angular_support", "Venus angular", -venus_weight, text, source_tags=["green_public_affairs"]))
    if any(int(rule.get("weight") or 0) < 0 for rule in matched):
        cautions.append("Benefic support moderates transition stress but does not erase hard authority signals.")
    if _uses_capital_chart_context(context) and capital_alignment.get("matches"):
        matched.append(_rule("leadership_capital_chart_alignment", "Capital-chart alignment", 6, "The resolved location matches the polity capital, which strengthens public-office transition analysis.", source_tags=["green_ingress"]))
    else:
        penalty = _capital_chart_penalty_rule(
            context,
            weight=4,
            detail="Leadership-transition analysis is weaker away from the polity capital when a capital chart is the preferred frame.",
            source_tags=["green_ingress", "green_public_affairs"],
        )
        if penalty is not None:
            matched.append(penalty)

    return _finalize(
        domain_id="leadership_transition",
        axis="transition_pressure",
        base_summary="Leadership transition is evaluated from solar authority, luminaries, tenth-house office condition, and transition-specific activation stress.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_regime_stability(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    matched: List[Dict[str, Any]] = []
    cautions = []
    capital_alignment = _capital_alignment(context)

    sun_weight, sun_detail = _planet_angular_weight(chart, "Sun", base_weight=4, max_proximity_bonus=4)
    if sun_weight:
        detail = "Solar authority is visible enough to tie the chart directly to executive control."
        if sun_detail and sun_detail.get("distance_deg") is not None:
            detail = f"Solar authority is visible, with the Sun nearest the {sun_detail.get('angle')} within {sun_detail.get('distance_deg')}deg."
        matched.append(_rule("regime_sun_angular", "Sun angular", sun_weight, detail, source_tags=["green_public_affairs"]))
    for malefic in ("Mars", "Saturn"):
        weight, detail = _planet_angular_weight(chart, malefic, base_weight=10, max_proximity_bonus=8)
        if weight:
            text = f"{malefic} is angular, matching public disturbance and cabinet-strain doctrine."
            if detail and detail.get("distance_deg") is not None:
                text = f"{malefic} is angular, nearest the {detail.get('angle')} within {detail.get('distance_deg')}deg, matching public disturbance and cabinet-strain doctrine."
            matched.append(_rule(f"regime_{_normalize_id(malefic)}_angular_authority", f"{malefic} angular", weight, text, source_tags=["green_public_affairs"]))
    uranus_weight, uranus_detail = _planet_angular_weight(chart, "Uranus", base_weight=12, max_proximity_bonus=8)
    if uranus_weight:
        text = "Uranus is angular, increasing abrupt regime or constitutional instability."
        if uranus_detail and uranus_detail.get("distance_deg") is not None:
            text = f"Uranus is angular, nearest the {uranus_detail.get('angle')} within {uranus_detail.get('distance_deg')}deg, increasing abrupt regime or constitutional instability."
        matched.append(_rule("regime_uranus_angular", "Uranus angular", uranus_weight, text, source_tags=["green_public_affairs"]))
    tenth_ruler = _house_ruler(chart, 10)
    eleventh_ruler = _house_ruler(chart, 11)
    fourth_ruler = _house_ruler(chart, 4)
    if tenth_ruler and _planet_retrograde(chart, tenth_ruler):
        matched.append(_rule("regime_tenth_ruler_retrograde", "Tenth-house ruler retrograde", 16, f"The tenth-house ruler {tenth_ruler} is retrograde, weakening executive continuity.", source_tags=["green_public_affairs", "watters_retrograde_mars"]))
    if eleventh_ruler and _planet_retrograde(chart, eleventh_ruler):
        matched.append(_rule("regime_eleventh_ruler_retrograde", "Eleventh-house ruler retrograde", 14, f"The eleventh-house ruler {eleventh_ruler} is retrograde, weakening parliamentary or cabinet backing.", source_tags=["green_public_affairs"]))
    if fourth_ruler and _planet_retrograde(chart, fourth_ruler):
        matched.append(_rule("regime_fourth_ruler_retrograde", "Fourth-house ruler retrograde", 10, f"The fourth-house ruler {fourth_ruler} is retrograde, showing internal constitutional or domestic-base strain.", source_tags=["green_public_affairs"]))
    if _planet_in_houses(chart, "Saturn", {11}):
        matched.append(_rule("regime_saturn_eleventh_adverse_vote", "Saturn in the 11th", 12, "Saturn in the eleventh raises adverse-vote risk, ministerial resignation pressure, and sustained parliamentary obstruction.", source_tags=["green_public_affairs", "annotated_raphael_civil_unrest"]))
    if _planet_in_houses(chart, "Uranus", {11}):
        matched.append(_rule("regime_uranus_eleventh_complications", "Uranus in the 11th", 10, "Uranus in the eleventh points to extraordinary parliamentary complications, unruly debate, and sudden institutional disruption.", source_tags=["green_public_affairs", "annotated_raphael_civil_unrest"]))
    if _planet_in_houses(chart, "Neptune", {10}):
        matched.append(_rule("regime_neptune_tenth_collapse", "Neptune in the 10th", 12, "Neptune in the tenth can accompany scandal, confusion, failed measures, or a more general governmental downfall rather than orderly executive continuity.", source_tags=["green_public_affairs"]))
    if _planet_in_houses(chart, "Neptune", {11}):
        matched.append(_rule("regime_neptune_eleventh_disorder", "Neptune in the 11th", 8, "Neptune in the eleventh can confuse parliamentary procedure, aggravate underhand factional work, and weaken legislative coherence.", source_tags=["green_public_affairs", "annotated_raphael_civil_unrest"]))
    for malefic in ("Mars", "Saturn", "Uranus"):
        for house_number in (10, 11):
            if _planet_in_house(chart, malefic, house_number):
                matched.append(
                    _rule(
                        f"regime_{_normalize_id(malefic)}_house_{house_number}",
                        f"{malefic} in the {house_number}th",
                        10 if house_number == 10 else 8,
                        f"{malefic} occupies the {house_number}th house, directly pressuring executive or parliamentary continuity.",
                        source_tags=["green_public_affairs"],
                    )
                )
    activation_hits = _activation_hits(context)
    if activation_hits:
        matched.append(_rule("regime_activation_hits", "Activation hits present", 16, "The overlay chart shows activation hits that can sharpen institutional or parliamentary stress.", source_tags=["watters_eclipse_degree"]))
    jupiter_weight, jupiter_detail = _planet_angular_weight(chart, "Jupiter", base_weight=4, max_proximity_bonus=4)
    if jupiter_weight:
        text = "Angular Jupiter can moderate instability and preserve institutional control."
        if jupiter_detail and jupiter_detail.get("distance_deg") is not None:
            text = f"Jupiter is angular, nearest the {jupiter_detail.get('angle')} within {jupiter_detail.get('distance_deg')}deg, moderating instability."
        matched.append(_rule("regime_jupiter_angular_support", "Jupiter angular", -jupiter_weight, text, source_tags=["green_public_affairs"]))
    venus_weight, venus_detail = _planet_angular_weight(chart, "Venus", base_weight=3, max_proximity_bonus=3)
    if venus_weight:
        text = "Angular Venus can soften public rupture and preserve alliances inside governance structures."
        if venus_detail and venus_detail.get("distance_deg") is not None:
            text = f"Venus is angular, nearest the {venus_detail.get('angle')} within {venus_detail.get('distance_deg')}deg, softening public rupture."
        matched.append(_rule("regime_venus_angular_support", "Venus angular", -venus_weight, text, source_tags=["green_public_affairs"]))
    if any(int(rule.get("weight") or 0) < 0 for rule in matched):
        cautions.append("Benefic support does not cancel hard authority signals; it only moderates them.")
    if _uses_capital_chart_context(context) and capital_alignment.get("matches"):
        matched.append(_rule("regime_capital_chart_alignment", "Capital-chart alignment", 10, "The resolved location matches the polity capital under a capital-chart framework, which is the doctrinally preferred authority context.", source_tags=["green_ingress"]))
    else:
        penalty = _capital_chart_penalty_rule(
            context,
            weight=6,
            detail="Capital-chart regime analysis is weaker away from the polity capital.",
            source_tags=["green_ingress", "green_public_affairs"],
        )
        if penalty is not None:
            matched.append(penalty)

    return _finalize(
        domain_id="regime_stability",
        axis="regime_instability_pressure",
        base_summary="Regime stability is evaluated from executive and parliamentary condition, capital-chart authority context, and institutional disruption triggers.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_government_stability(context: ResolvedMundaneContext) -> Dict[str, Any]:
    leadership = _evaluate_leadership_transition(context)
    regime = _evaluate_regime_stability(context)
    matched: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for ruleset in (leadership.get("matched_rules") or [], regime.get("matched_rules") or []):
        for source in ruleset:
            if not isinstance(source, dict):
                continue
            rule_id = str(source.get("id") or "")
            if rule_id in seen_ids:
                continue
            seen_ids.add(rule_id)
            matched.append(source)

    cautions = list(dict.fromkeys([*(leadership.get("cautions") or []), *(regime.get("cautions") or [])]))
    research_flags = list(dict.fromkeys([*context.research_flags, "compatibility_umbrella"]))

    return _finalize(
        domain_id="government_stability",
        axis="government_instability_pressure",
        base_summary="Government stability is evaluated as a compatibility umbrella merging leadership-transition and regime-stability stress.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=research_flags,
    )


def _evaluate_diplomacy(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    trigger_profiles = _trigger_profiles(context, "retrograde_mars")
    matched: List[Dict[str, Any]] = []
    cautions = []
    capital_alignment = _capital_alignment(context)

    seventh_ruler = _house_ruler(chart, 7)
    ninth_ruler = _house_ruler(chart, 9)
    eleventh_ruler = _house_ruler(chart, 11)
    if seventh_ruler:
        house_position = _planet_house(chart, seventh_ruler)
        if house_position in _ANGULAR_HOUSES:
            detail = _planet_angle_detail(chart, seventh_ruler)
            weight = 8 + _proximity_bonus((detail or {}).get("distance_deg"), max_bonus=6)
            matched.append(_rule("seventh_ruler_angular", "Seventh-house ruler angular", weight, f"The seventh-house ruler {seventh_ruler} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, showing foreign-affairs matters fully on stage.", source_tags=["green_public_affairs"]))
        if _planet_retrograde(chart, seventh_ruler):
            matched.append(_rule("seventh_ruler_retrograde", "Seventh-house ruler retrograde", 18, f"The seventh-house ruler {seventh_ruler} is retrograde, increasing negotiation reversal risk.", source_tags=["watters_retrograde_mars"]))
    if ninth_ruler:
        ninth_house_position = _planet_house(chart, ninth_ruler)
        if ninth_house_position in _ANGULAR_HOUSES:
            detail = _planet_angle_detail(chart, ninth_ruler)
            weight = 6 + _proximity_bonus((detail or {}).get("distance_deg"), max_bonus=5)
            matched.append(_rule("ninth_ruler_angular", "Ninth-house ruler angular", weight, f"The ninth-house ruler {ninth_ruler} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, making treaties, foreign-law questions, or international assemblies more publicly active.", source_tags=["green_public_affairs"]))
        if _planet_retrograde(chart, ninth_ruler):
            matched.append(_rule("ninth_ruler_retrograde", "Ninth-house ruler retrograde", 12, f"The ninth-house ruler {ninth_ruler} is retrograde, weakening treaty durability and foreign-law coherence.", source_tags=["watters_retrograde_mars", "green_public_affairs"]))
    if eleventh_ruler and _planet_retrograde(chart, eleventh_ruler):
        matched.append(_rule("eleventh_ruler_retrograde", "Eleventh-house ruler retrograde", 10, f"The eleventh-house ruler {eleventh_ruler} is retrograde, straining allied support and legislative backing for foreign policy.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Mercury", 7):
        mercury_under_strain = _planet_retrograde(chart, "Mercury") or _planet_angular(chart, "Mars") or _planet_angular(chart, "Saturn")
        if mercury_under_strain:
            matched.append(_rule("mercury_seventh_breakdown", "Mercury in the seventh under strain", 14, "Mercury in the seventh is under visible strain, matching diplomatic blunders, treaty breakdown risk, or foreign-trade disputes rather than stable settlement.", source_tags=["annotated_raphael_diplomacy"]))
    mars_weight, mars_detail = _planet_angular_weight(chart, "Mars", base_weight=10, max_proximity_bonus=8)
    if mars_weight:
        matched.append(_rule("mars_angular_foreign", "Mars angular", mars_weight, f"Mars is angular, nearest the {(mars_detail or {}).get('angle') or 'angle'} within {(mars_detail or {}).get('distance_deg') or 'unknown'}deg, straining diplomacy and raising hostile foreign-affairs tone.", source_tags=["green_public_affairs", "watters_retrograde_mars"]))
    venus_weight, venus_detail = _planet_angular_weight(chart, "Venus", base_weight=8, max_proximity_bonus=6)
    if venus_weight:
        matched.append(_rule("venus_angular_support", "Venus angular", -venus_weight, f"Venus is angular, nearest the {(venus_detail or {}).get('angle') or 'angle'} within {(venus_detail or {}).get('distance_deg') or 'unknown'}deg, supporting peace, preservation, and treaty maintenance.", source_tags=["green_public_affairs"]))
    jupiter_weight, jupiter_detail = _planet_angular_weight(chart, "Jupiter", base_weight=6, max_proximity_bonus=5)
    if jupiter_weight:
        matched.append(_rule("jupiter_angular_support", "Jupiter angular", -jupiter_weight, f"Jupiter is angular, nearest the {(jupiter_detail or {}).get('angle') or 'angle'} within {(jupiter_detail or {}).get('distance_deg') or 'unknown'}deg, supporting honorable foreign relations and diplomatic coherence.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Venus", 9):
        matched.append(_rule("venus_in_ninth_support", "Venus in the ninth", -16, "Venus in the ninth supports peace, treaty settlement, and preservation of orderly foreign relations through ninth-house diplomacy and legal channels.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Jupiter", 9):
        matched.append(_rule("jupiter_in_ninth_support", "Jupiter in the ninth", -12, "Jupiter in the ninth supports honorable foreign service, lawful settlement, and international cooperation.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Mars", 9):
        matched.append(_rule("mars_in_ninth_strain", "Mars in the ninth", 12, "Mars in the ninth strains foreign-law and treaty channels, pushing diplomacy toward overt hostility.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Saturn", 9):
        matched.append(_rule("saturn_in_ninth_delay", "Saturn in the ninth", 10, "Saturn in the ninth can harden treaty channels, delay settlements, or burden foreign affairs with obstruction.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Venus", 11):
        matched.append(_rule("venus_in_eleventh_support", "Venus in the eleventh", -10, "Venus in the eleventh supports allies, parliamentary goodwill, and maintenance of friendly national backing.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Jupiter", 11):
        matched.append(_rule("jupiter_in_eleventh_support", "Jupiter in the eleventh", -8, "Jupiter in the eleventh supports friends of the nation, alliance confidence, and broader diplomatic backing.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Saturn", 11):
        matched.append(_rule("saturn_in_eleventh_strain", "Saturn in the eleventh", 12, "Saturn in the eleventh strains allied support networks and can show coldness or burden among friends of the nation.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Mars", 11):
        matched.append(_rule("mars_in_eleventh_strain", "Mars in the eleventh", 10, "Mars in the eleventh heats alliances, factions, or legislative support structures around foreign policy.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Moon", 11) and _planet_in_house(chart, "Saturn", 11):
        moon_longitude = _planet_longitude(chart, "Moon")
        saturn_longitude = _planet_longitude(chart, "Saturn")
        separation = _angle_sep(moon_longitude, saturn_longitude) if moon_longitude is not None and saturn_longitude is not None else None
        if separation is not None and separation <= 10.0:
            matched.append(_rule("moon_saturn_allied_stress", "Moon-Saturn allied stress", 20, f"Moon and Saturn are both in the eleventh house and separated by {round(separation, 2)}deg, matching benchmarked ally-collapse pressure through the friends-of-the-nation house.", source_tags=["green_public_affairs"]))
        else:
            matched.append(_rule("moon_saturn_eleventh", "Moon and Saturn in the eleventh", 14, "Moon and Saturn share the eleventh house, putting public alliance feeling and allied support under visible strain.", source_tags=["green_public_affairs"]))
    if (trigger_profiles.get("retrograde_mars") or {}).get("active"):
        matched.append(_rule("mars_retrograde_warning", "Mars retrograde", 16, "Retrograde Mars is a specific warning for failed agreements and reversals.", source_tags=["watters_retrograde_mars"]))
        cautions.append("Retrograde Mars should be treated as treaty-instability risk, not as a universal diplomatic failure rule.")
    if _uses_capital_chart_context(context) and capital_alignment.get("matches"):
        matched.append(_rule("capital_chart_alignment", "Capital-chart alignment", 10, "The resolved location matches the polity capital under a capital-chart framework, preserving the most authoritative diplomatic center for the polity.", source_tags=["green_ingress", "green_public_affairs"]))
    else:
        penalty = _capital_chart_penalty_rule(
            context,
            weight=6,
            detail="Diplomatic reading through a capital-chart frame is weaker away from the polity capital.",
            source_tags=["green_ingress", "green_public_affairs"],
        )
        if penalty is not None:
            matched.append(penalty)

    return _finalize(
        domain_id="diplomacy_foreign_affairs",
        axis="diplomatic_strain",
        base_summary="Diplomatic strain is evaluated from seventh-, ninth-, and eleventh-house condition, benefic treaty support, and martial reversal signals.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_alliance_stress(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    trigger_profiles = _trigger_profiles(context, "retrograde_mars")
    matched: List[Dict[str, Any]] = []
    cautions = [
        "Alliance-stress output remains research-gated and should be read as coalition or friendly-nation strain, not as a standalone war prediction."
    ]
    capital_alignment = _capital_alignment(context)

    seventh_ruler = _house_ruler(chart, 7)
    eighth_ruler = _house_ruler(chart, 8)
    ninth_ruler = _house_ruler(chart, 9)
    eleventh_ruler = _house_ruler(chart, 11)

    if eleventh_ruler:
        if _planet_angular(chart, eleventh_ruler):
            detail = _planet_angle_detail(chart, eleventh_ruler)
            weight = 8 + _proximity_bonus((detail or {}).get("distance_deg"), max_bonus=6)
            matched.append(
                _rule(
                    "eleventh_ruler_angular",
                    "Eleventh-house ruler angular",
                    weight,
                    f"The eleventh-house ruler {eleventh_ruler} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, putting allied support and friendly-nation questions on the public stage.",
                    source_tags=["green_public_affairs"],
                )
            )
        if _planet_retrograde(chart, eleventh_ruler):
            matched.append(
                _rule(
                    "eleventh_ruler_retrograde",
                    "Eleventh-house ruler retrograde",
                    14,
                    f"The eleventh-house ruler {eleventh_ruler} is retrograde, weakening allied support coherence or the reliability of friendly national backing.",
                    source_tags=["green_public_affairs", "watters_retrograde_mars"],
                )
            )
        eleventh_house_position = _planet_house(chart, eleventh_ruler)
        if eleventh_house_position in {6, 8, 12}:
            matched.append(
                _rule(
                    "eleventh_ruler_in_burden_house",
                    "Eleventh-house ruler in a burden house",
                    10,
                    f"The eleventh-house ruler {eleventh_ruler} falls in the {eleventh_house_position} house, showing allied support carried into strain, debt, or hidden weakness rather than easy cohesion.",
                    source_tags=["green_public_affairs"],
                )
            )
    if seventh_ruler and _planet_retrograde(chart, seventh_ruler):
        matched.append(
            _rule(
                "seventh_ruler_retrograde",
                "Seventh-house ruler retrograde",
                10,
                f"The seventh-house ruler {seventh_ruler} is retrograde, weakening treaty durability and making coalition commitments harder to hold together.",
                source_tags=["watters_retrograde_mars", "green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Saturn", 7):
        matched.append(
            _rule(
                "saturn_seventh_alliance_strain",
                "Saturn in the seventh",
                14,
                "Saturn in the seventh is very unfavorable for foreign affairs and prolonged alliance trouble, cooling treaty goodwill and making commitments burdensome or hard to preserve.",
                source_tags=["annotated_raphael_diplomacy", "green_public_affairs"],
            )
        )
    if seventh_ruler and _planet_in_houses(chart, seventh_ruler, {8}):
        matched.append(
            _rule(
                "seventh_ruler_in_eighth_alliance_resources",
                "Seventh-house ruler in the eighth",
                10,
                f"The seventh-house ruler {seventh_ruler} falls in the eighth house, tying treaties and allied dealings to debt, vulnerable shared resources, or losses through other powers.",
                source_tags=["watters_retrograde_mars", "green_public_affairs"],
            )
        )
    if ninth_ruler and _planet_retrograde(chart, ninth_ruler):
        matched.append(
            _rule(
                "ninth_ruler_retrograde_alliance",
                "Ninth-house ruler retrograde",
                8,
                f"The ninth-house ruler {ninth_ruler} is retrograde, weakening the wider foreign-relations channel that should support treaty or alliance coherence.",
                source_tags=["green_public_affairs", "annotated_raphael_diplomacy"],
            )
        )
    if ninth_ruler and _planet_in_houses(chart, ninth_ruler, {6, 8, 12}):
        house_position = _planet_house(chart, ninth_ruler)
        matched.append(
            _rule(
                "ninth_ruler_in_burden_house_alliance",
                "Ninth-house ruler in a burden house",
                8,
                f"The ninth-house ruler {ninth_ruler} falls in the {house_position} house, pushing foreign-relations management into strain, loss, or hidden weakness rather than easy cooperation.",
                source_tags=["green_public_affairs", "annotated_raphael_diplomacy"],
            )
        )
    if _planet_in_house(chart, "Mercury", 7):
        mercury_under_strain = _planet_retrograde(chart, "Mercury") or _planet_angular(chart, "Mars") or _planet_angular(chart, "Saturn")
        if mercury_under_strain:
            matched.append(
                _rule(
                    "mercury_seventh_alliance_breakdown",
                    "Mercury in the seventh under strain",
                    10,
                    "Mercury in the seventh is under visible strain, matching diplomatic blunders, broken understandings, and coalition-support confusion rather than stable alignment.",
                    source_tags=["annotated_raphael_diplomacy"],
                )
            )
    if _planet_in_house(chart, "Venus", 7):
        if _planet_retrograde(chart, "Venus"):
            matched.append(
                _rule(
                    "venus_seventh_retrograde_alliance",
                    "Venus in the seventh retrograde",
                    12,
                    "Venus in the seventh is retrograde, matching unstable alliances, treaty reversal, or the cooling of goodwill among powers that should be cooperating.",
                    source_tags=["watters_retrograde_mars", "annotated_raphael_diplomacy"],
                )
            )
        else:
            matched.append(
                _rule(
                    "venus_seventh_alliance_support",
                    "Venus in the seventh",
                    -8,
                    "Venus in the seventh supports peace-making, notable alliances, and treaty goodwill rather than coalition rupture.",
                    source_tags=["annotated_raphael_diplomacy", "green_public_affairs"],
                )
            )
    for planet_name, label, weight, detail, tags in (
        ("Saturn", "Saturn in the eleventh", 16, "Saturn in the eleventh strains allied support networks and can show coldness, burden, or failing help among friendly nations.", ["green_public_affairs"]),
        ("Mars", "Mars in the eleventh", 12, "Mars in the eleventh heats alliances and coalition structures, increasing rupture, quarrel, or hostile pressure among nominal supporters.", ["green_public_affairs"]),
        ("Uranus", "Uranus in the eleventh", 12, "Uranus in the eleventh points to sudden breaks, unreliable friends, or abrupt shifts in allied backing.", ["green_public_affairs"]),
        ("Neptune", "Neptune in the eleventh", 10, "Neptune in the eleventh clouds allied commitments and can show hidden or unreliable support among friends of the nation.", ["annotated_raphael_diplomacy", "green_public_affairs"]),
    ):
        if _planet_in_house(chart, planet_name, 11):
            matched.append(_rule(f"{_normalize_id(planet_name)}_in_eleventh", label, weight, detail, source_tags=tags))
    if eighth_ruler and _planet_in_houses(chart, eighth_ruler, {7, 11}):
        house_position = _planet_house(chart, eighth_ruler)
        matched.append(
            _rule(
                "eighth_ruler_in_alliance_house",
                "Eighth-house ruler in an alliance house",
                10,
                f"The eighth-house ruler {eighth_ruler} falls in the {house_position} house, bringing allied resources, debt exposure, or loss-through-others directly into treaty and coalition questions.",
                source_tags=["watters_retrograde_mars", "green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Moon", 11) and _planet_in_house(chart, "Saturn", 11):
        moon_longitude = _planet_longitude(chart, "Moon")
        saturn_longitude = _planet_longitude(chart, "Saturn")
        separation = _angle_sep(moon_longitude, saturn_longitude) if moon_longitude is not None and saturn_longitude is not None else None
        if separation is not None and separation <= 10.0:
            matched.append(
                _rule(
                    "moon_saturn_allied_stress",
                    "Moon-Saturn allied stress",
                    20,
                    f"Moon and Saturn are both in the eleventh house and separated by {round(separation, 2)}deg, matching benchmarked ally-collapse pressure through the friends-of-the-nation house.",
                    source_tags=["green_public_affairs"],
                )
            )
        else:
            matched.append(
                _rule(
                    "moon_saturn_eleventh",
                    "Moon and Saturn in the eleventh",
                    14,
                    "Moon and Saturn share the eleventh house, placing public alliance feeling and friendly-nation support under visible strain.",
                    source_tags=["green_public_affairs"],
                )
            )
    if _planet_in_house(chart, "Venus", 11):
        matched.append(
            _rule(
                "venus_in_eleventh_support",
                "Venus in the eleventh",
                -12,
                "Venus in the eleventh supports allies, goodwill among friendly nations, and preservation of coalition backing.",
                source_tags=["green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Jupiter", 11):
        matched.append(
            _rule(
                "jupiter_in_eleventh_support",
                "Jupiter in the eleventh",
                -10,
                "Jupiter in the eleventh supports alliance confidence, honorable friends of the nation, and broader cooperative backing.",
                source_tags=["green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Jupiter", 7):
        matched.append(
            _rule(
                "jupiter_in_seventh_support",
                "Jupiter in the seventh",
                -8,
                "Jupiter in the seventh supports honorable agreements, steadier foreign commitments, and broader confidence between powers.",
                source_tags=["annotated_raphael_diplomacy", "green_public_affairs"],
            )
        )
    if (trigger_profiles.get("retrograde_mars") or {}).get("active"):
        matched.append(
            _rule(
                "mars_retrograde_warning",
                "Mars retrograde",
                12,
                "Retrograde Mars is a specific warning for treaty reversal, broken commitments, and unstable alliance backing.",
                source_tags=["watters_retrograde_mars"],
            )
        )
        cautions.append("Retrograde Mars is a coalition-instability warning, not a standalone guarantee of alliance collapse.")
    if _uses_capital_chart_context(context) and capital_alignment.get("matches"):
        matched.append(
            _rule(
                "capital_chart_alignment",
                "Capital-chart alignment",
                8,
                "The resolved location matches the polity capital under a capital-chart framework, preserving the strongest center for allied-support judgment.",
                source_tags=["green_ingress", "green_public_affairs"],
            )
        )
    else:
        penalty = _capital_chart_penalty_rule(
            context,
            weight=6,
            detail="Alliance reading through a capital-chart frame is weaker away from the polity capital.",
            source_tags=["green_ingress", "green_public_affairs"],
        )
        if penalty is not None:
            matched.append(penalty)

    return _finalize(
        domain_id="alliance_stress",
        axis="allied_support_strain",
        base_summary="Alliance stress is evaluated from the eleventh house of friendly nations and support networks, then checked against treaty-channel weakness and retrograde reversal warnings.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_trade_and_commerce(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    trigger_profiles = _trigger_profiles(context, "eclipse_degree_activation", "mutation_and_conjunction_cycles")
    matched: List[Dict[str, Any]] = []
    cautions = [
        "Trade-and-commerce output remains research-gated and should be read as commercial-flow and policy strain, not as a complete macroeconomic model."
    ]
    capital_alignment = _capital_alignment(context)

    second_ruler = _house_ruler(chart, 2)
    seventh_ruler = _house_ruler(chart, 7)
    ninth_ruler = _house_ruler(chart, 9)
    eleventh_ruler = _house_ruler(chart, 11)

    if _planet_in_house(chart, "Mercury", 2):
        if _planet_retrograde(chart, "Mercury"):
            matched.append(
                _rule(
                    "mercury_second_trade_losses",
                    "Mercury in the second under strain",
                    12,
                    "Mercury in the second is under retrograde strain, matching losses through fraud, theft, sharp practice, or instability in trade and commerce revenues.",
                    source_tags=["annotated_raphael_finance"],
                )
            )
        else:
            matched.append(
                _rule(
                    "mercury_second_trade_activity",
                    "Mercury in the second",
                    -4,
                    "Mercury in the second supports gains in trade and commerce and keeps commercial affairs active rather than stagnant.",
                    source_tags=["annotated_raphael_finance"],
                )
            )
    if second_ruler and _planet_retrograde(chart, second_ruler):
        matched.append(
            _rule(
                "second_ruler_retrograde_trade",
                "Second-house ruler retrograde",
                12,
                f"The second-house ruler {second_ruler} is retrograde, weakening commercial continuity, market confidence, or the smooth flow of trade revenues.",
                source_tags=["green_public_affairs"],
            )
        )
    if second_ruler and _planet_in_houses(chart, second_ruler, {7}):
        matched.append(
            _rule(
                "second_ruler_in_seventh_trade",
                "Second-house ruler in the seventh",
                12,
                f"The second-house ruler {second_ruler} falls in the seventh house, tying national commerce directly to open foreign-country disputes, negotiations, or commercial bargaining.",
                source_tags=["green_public_affairs", "annotated_raphael_diplomacy"],
            )
        )
    if second_ruler and _planet_in_houses(chart, second_ruler, {9}):
        matched.append(
            _rule(
                "second_ruler_in_ninth_trade",
                "Second-house ruler in the ninth",
                10,
                f"The second-house ruler {second_ruler} falls in the ninth house, tying trade and commerce to foreign-law channels, shipping routes, or wider international commerce questions.",
                source_tags=["green_public_affairs"],
            )
        )
    if second_ruler and _planet_in_houses(chart, second_ruler, {11}):
        matched.append(
            _rule(
                "second_ruler_in_eleventh_trade",
                "Second-house ruler in the eleventh",
                12,
                f"The second-house ruler {second_ruler} falls in the eleventh house, tying commerce to Parliament, trade policy, and legislation touching commercial activity.",
                source_tags=["green_public_affairs", "annotated_raphael_finance"],
            )
        )
    if _planet_in_house(chart, "Mercury", 9):
        if _planet_retrograde(chart, "Mercury") or any(_planet_in_houses(chart, planet_name, {9}) for planet_name in ("Mars", "Saturn", "Neptune")):
            matched.append(
                _rule(
                    "mercury_ninth_trade_dispute",
                    "Mercury in the ninth under strain",
                    12,
                    "Mercury in the ninth is under visible strain, matching disputes over trade and commerce, legal-commercial wrangles, or agitated shipping and foreign-law channels.",
                    source_tags=["annotated_raphael_finance", "green_public_affairs"],
                )
            )
        else:
            matched.append(
                _rule(
                    "mercury_ninth_trade_support",
                    "Mercury in the ninth",
                    -6,
                    "Mercury in the ninth supports commercial activity, trade legislation, and wider shipping or foreign-law channels rather than obstructing them.",
                    source_tags=["annotated_raphael_finance"],
                )
            )
    if _planet_in_house(chart, "Mercury", 7):
        mercury_under_strain = _planet_retrograde(chart, "Mercury") or _planet_angular(chart, "Mars") or _planet_angular(chart, "Saturn")
        if mercury_under_strain:
            matched.append(
                _rule(
                    "mercury_seventh_trade_dispute",
                    "Mercury in the seventh under strain",
                    16,
                    "Mercury in the seventh is under visible strain, matching commercial and trade disputes with foreign countries, double-dealing, or coercive foreign bargaining rather than stable exchange.",
                    source_tags=["annotated_raphael_diplomacy"],
                )
            )
    if _planet_in_house(chart, "Venus", 7) and not _planet_retrograde(chart, "Venus"):
        matched.append(
            _rule(
                "venus_seventh_trade_relief",
                "Venus in the seventh",
                -6,
                "Venus in the seventh supports commercial agreements, smoother bargaining, and more cooperative foreign-trade relations.",
                source_tags=["annotated_raphael_diplomacy", "green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Jupiter", 7):
        matched.append(
            _rule(
                "jupiter_seventh_trade_relief",
                "Jupiter in the seventh",
                -6,
                "Jupiter in the seventh supports lawful exchange, stronger foreign commercial relationships, and greater room for successful agreements.",
                source_tags=["green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Saturn", 7):
        matched.append(
            _rule(
                "saturn_seventh_trade_depression",
                "Saturn in the seventh",
                12,
                "Saturn in the seventh is unfavorable for foreign dealings and can depress foreign trade, burdening exchange with prolonged difficulty rather than easy reciprocity.",
                source_tags=["annotated_raphael_diplomacy", "green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Mercury", 11):
        weight = 8 + (4 if _planet_retrograde(chart, "Mercury") else 0)
        detail = "Mercury in the eleventh ties Parliament directly to legislation touching trade and commerce."
        if _planet_retrograde(chart, "Mercury"):
            detail += " Retrograde Mercury intensifies arguments, delays, and commercial-policy disputes."
        matched.append(
            _rule(
                "mercury_eleventh_trade",
                "Mercury in the eleventh",
                weight,
                detail,
                source_tags=["annotated_raphael_finance"],
            )
        )
    if _planet_in_house(chart, "Jupiter", 11):
        matched.append(
            _rule(
                "jupiter_eleventh_trade",
                "Jupiter in the eleventh",
                -10,
                "Jupiter in the eleventh supports legislation that improves trade, commerce, and financial confidence rather than obstructing exchange.",
                source_tags=["annotated_raphael_finance"],
            )
        )
    if _planet_in_house(chart, "Saturn", 11):
        matched.append(
            _rule(
                "saturn_eleventh_trade",
                "Saturn in the eleventh",
                12,
                "Saturn in the eleventh points to adverse-vote risk, commercial restriction, and obstructive legislation affecting trade, securities, or the wider business climate.",
                source_tags=["annotated_raphael_finance", "green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Mars", 11):
        matched.append(
            _rule(
                "mars_eleventh_trade",
                "Mars in the eleventh",
                10,
                "Mars in the eleventh brings quarrels and parliamentary conflict into trade, shipping, tariff, or commercial-policy debates.",
                source_tags=["green_public_affairs", "annotated_raphael_finance"],
            )
        )
    if _planet_in_house(chart, "Mars", 9):
        matched.append(
            _rule(
                "mars_ninth_trade",
                "Mars in the ninth",
                12,
                "Mars in the ninth strains foreign-trade channels, shipping, and international commercial relations, pushing trade questions toward hostility or coercion.",
                source_tags=["green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Neptune", 9):
        matched.append(
            _rule(
                "neptune_ninth_trade_fraud",
                "Neptune in the ninth",
                10,
                "Neptune in the ninth points to fraud, scandal, or deceptive practice in trade and commerce rather than clean foreign exchange.",
                source_tags=["annotated_raphael_finance"],
            )
        )
    if _planet_in_house(chart, "Saturn", 9):
        matched.append(
            _rule(
                "saturn_ninth_trade",
                "Saturn in the ninth",
                10,
                "Saturn in the ninth burdens foreign-trade channels with obstruction, delay, and restrictive legal or shipping conditions.",
                source_tags=["green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Venus", 9):
        matched.append(
            _rule(
                "venus_ninth_trade_relief",
                "Venus in the ninth",
                -8,
                "Venus in the ninth eases treaty and foreign-law channels for commerce, supporting orderly trade relations rather than coercive dispute.",
                source_tags=["green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Jupiter", 9):
        matched.append(
            _rule(
                "jupiter_ninth_trade_relief",
                "Jupiter in the ninth",
                -6,
                "Jupiter in the ninth supports lawful foreign exchange, shipping confidence, and broader international commerce.",
                source_tags=["green_public_affairs"],
            )
        )
    if eleventh_ruler and _planet_retrograde(chart, eleventh_ruler):
        matched.append(
            _rule(
                "eleventh_ruler_retrograde_trade",
                "Eleventh-house ruler retrograde",
                8,
                f"The eleventh-house ruler {eleventh_ruler} is retrograde, showing legislative friction around trade, commerce, or government-backed commercial policy.",
                source_tags=["annotated_raphael_finance"],
            )
        )
    if seventh_ruler and _planet_retrograde(chart, seventh_ruler):
        matched.append(
            _rule(
                "seventh_ruler_retrograde_trade",
                "Seventh-house ruler retrograde",
                8,
                f"The seventh-house ruler {seventh_ruler} is retrograde, weakening foreign commercial agreements and making trade bargaining harder to stabilize.",
                source_tags=["annotated_raphael_diplomacy", "green_public_affairs"],
            )
        )
    if (
        any(_planet_in_houses(chart, planet_name, {11}) for planet_name in ("Mercury", "Mars", "Saturn"))
        and (second_ruler and _planet_in_houses(chart, second_ruler, {11}))
    ):
        matched.append(
            _rule(
                "commercial_legislation_blockage",
                "Commercial-legislation blockage",
                12,
                "Second-house commercial resources are tied directly into an afflicted eleventh-house legislative picture, matching blocked trade policy or parliamentary commercial obstruction.",
                source_tags=["annotated_raphael_finance", "green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Mercury", 7) and any(_planet_in_houses(chart, planet_name, {9, 11}) for planet_name in ("Mars", "Saturn")):
        matched.append(
            _rule(
                "foreign_trade_dispute_axis",
                "Foreign trade dispute axis",
                10,
                "Foreign-bargaining testimony and trade-policy obstruction are both active, matching blockades, coercive settlements, or open trade disputes rather than smooth exchange.",
                source_tags=["annotated_raphael_diplomacy", "annotated_raphael_finance"],
            )
        )
    if _uses_capital_chart_context(context) and capital_alignment.get("matches"):
        matched.append(
            _rule(
                "capital_chart_alignment_trade",
                "Capital-chart alignment",
                6,
                "The resolved location matches the polity capital under a capital-chart frame, preserving the most authoritative center for trade-policy and commercial-legislation judgment.",
                source_tags=["green_ingress", "green_public_affairs"],
            )
        )
    else:
        penalty = _capital_chart_penalty_rule(
            context,
            weight=4,
            detail="Trade-and-commerce reading through a capital-chart frame is weaker away from the polity capital.",
            source_tags=["green_ingress", "green_public_affairs"],
        )
        if penalty is not None:
            matched.append(penalty)
    activation_profile = trigger_profiles.get("eclipse_degree_activation") or {}
    if activation_profile.get("active"):
        matched.append(
            _rule(
                "trade_activation_hits",
                "Activation hits present",
                max(8, int(activation_profile.get("score") or 0)),
                "Activation hits can sharpen sudden commercial turns, blockades, or trade-policy shocks inside an already stressed commerce picture.",
                source_tags=["watters_eclipse_degree"],
            )
        )
    cycle_state = _cycle_trigger_context(trigger_profiles.get("mutation_and_conjunction_cycles"))
    if cycle_state.get("active"):
        cycle_weight = max(8, min(14, int(cycle_state.get("score") or 0)))
        matched.append(
            _rule(
                "mutation_cycle_trade_backdrop",
                "Mutation-cycle trade backdrop",
                cycle_weight,
                f"The Jupiter-Saturn cycle backdrop is active in {cycle_state.get('sign') or 'the current sign'} with {cycle_state.get('phase') or 'an active phase'}, placing commerce inside a broader policy and business-turning period rather than a single isolated dispute.",
                source_tags=["watters_mutations", "bonatti_revolutions"],
            )
        )
        cautions.append("Long-cycle trade testimony is backdrop context and should be read with direct commercial-house triggers, not as a standalone tariff or blockade timer.")

    return _finalize(
        domain_id="trade_and_commerce",
        axis="commercial_strain",
        base_summary="Trade and commerce are evaluated from second-house commercial resources, foreign-trade channels, and legislative blockage rather than only treasury balance.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_epidemic_wave_pressure(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    trigger_profiles = _trigger_profiles(context, "eclipse_degree_activation", "mutation_and_conjunction_cycles")
    matched: List[Dict[str, Any]] = []
    cautions = [
        "Epidemic-wave output remains research-gated and should be read as surge, recurrence, or subsiding pressure inside a broader public-health picture, not as deterministic outbreak prediction."
    ]
    capital_alignment = _capital_alignment(context)
    chart_type_id = _normalize_id((context.chart_type or {}).get("id"))
    chart_kind = _normalize_id((chart or {}).get("kind"))

    sixth_ruler = _house_ruler(chart, 6)
    eighth_ruler = _house_ruler(chart, 8)
    twelfth_ruler = _house_ruler(chart, 12)

    if sixth_ruler:
        if _planet_angular(chart, sixth_ruler):
            detail = _planet_angle_detail(chart, sixth_ruler)
            weight = 10 + _proximity_bonus((detail or {}).get("distance_deg"), max_bonus=8)
            matched.append(
                _rule(
                    "sixth_ruler_angular_wave",
                    "Sixth-house ruler angular",
                    weight,
                    f"The sixth-house ruler {sixth_ruler} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, bringing illness pressure into a visible wave or surge pattern.",
                    source_tags=["annotated_raphael_public_health", "green_public_affairs"],
                )
            )
        if _planet_retrograde(chart, sixth_ruler):
            matched.append(
                _rule(
                    "sixth_ruler_retrograde_wave",
                    "Sixth-house ruler retrograde",
                    12,
                    f"The sixth-house ruler {sixth_ruler} is retrograde, favoring recurrence, persistence, or return-wave behavior rather than one clean illness burst.",
                    source_tags=["annotated_raphael_public_health"],
                )
            )
        if _planet_in_houses(chart, sixth_ruler, {8, 12}):
            house_position = _planet_house(chart, sixth_ruler)
            matched.append(
                _rule(
                    "sixth_ruler_in_wave_house",
                    "Sixth-house ruler in a wave house",
                    10,
                    f"The sixth-house ruler {sixth_ruler} falls in the {house_position} house, tying epidemic burden directly to mortality or hospitalization pressure.",
                    source_tags=["annotated_raphael_public_health", "green_public_affairs"],
                )
            )
    if eighth_ruler and _planet_angular(chart, eighth_ruler):
        detail = _planet_angle_detail(chart, eighth_ruler)
        weight = 8 + _proximity_bonus((detail or {}).get("distance_deg"), max_bonus=6)
        matched.append(
            _rule(
                "eighth_ruler_angular_wave",
                "Eighth-house ruler angular",
                weight,
                f"The eighth-house ruler {eighth_ruler} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, sharpening mortality-wave visibility.",
                source_tags=["annotated_raphael_public_health", "green_public_affairs"],
            )
        )
    if twelfth_ruler and _planet_angular(chart, twelfth_ruler):
        detail = _planet_angle_detail(chart, twelfth_ruler)
        weight = 8 + _proximity_bonus((detail or {}).get("distance_deg"), max_bonus=6)
        matched.append(
            _rule(
                "twelfth_ruler_angular_wave",
                "Twelfth-house ruler angular",
                weight,
                f"The twelfth-house ruler {twelfth_ruler} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, making hospital or institutional burden part of the wave pattern.",
                source_tags=["annotated_raphael_public_health", "green_public_affairs"],
            )
        )
    if _planet_retrograde(chart, "Venus"):
        matched.append(
            _rule(
                "venus_retrograde_wave_onset",
                "Venus retrograde",
                14,
                "Retrograde Venus is active, which Watters ties to epidemic onset or renewed collective-health trouble rather than quiet subsidence.",
                source_tags=["watters_venus_retrograde_epidemics"],
            )
        )
    if _planet_in_house(chart, "Mars", 6):
        matched.append(
            _rule(
                "mars_in_sixth_wave",
                "Mars in the sixth",
                12,
                "Mars in the sixth intensifies fever, infection, and active epidemic pressure, supporting a sharper surge or aggravated wave rather than quiet background illness.",
                source_tags=["annotated_raphael_public_health"],
            )
        )
    if _planet_in_house(chart, "Saturn", 6):
        matched.append(
            _rule(
                "saturn_in_sixth_wave",
                "Saturn in the sixth",
                12,
                "Saturn in the sixth supports prolonged illness burden and makes a secondary wave or persistent drag more plausible.",
                source_tags=["annotated_raphael_public_health", "green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Saturn", 12):
        matched.append(
            _rule(
                "saturn_in_twelfth_wave",
                "Saturn in the twelfth",
                12,
                "Saturn in the twelfth burdens hospitals and institutions, supporting a drawn-out epidemic wave rather than a brief flare.",
                source_tags=["annotated_raphael_public_health", "green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Neptune", 12):
        matched.append(
            _rule(
                "neptune_in_twelfth_wave",
                "Neptune in the twelfth",
                10,
                "Neptune in the twelfth clouds hospitals and institutional management, supporting confused, saturating, or hard-to-contain wave pressure rather than clean recovery.",
                source_tags=["annotated_raphael_public_health"],
            )
        )
    elif _planet_angular(chart, "Neptune"):
        neptune_weight, neptune_detail = _planet_angular_weight(chart, "Neptune", base_weight=6, max_proximity_bonus=4)
        if neptune_weight:
            matched.append(
                _rule(
                    "neptune_angular_wave",
                    "Neptune angular",
                    neptune_weight,
                    f"Neptune is angular, nearest the {(neptune_detail or {}).get('angle') or 'angle'} within {(neptune_detail or {}).get('distance_deg') or 'unknown'}deg, making widespread confusion or diffuse institutional burden part of the wave picture.",
                    source_tags=["annotated_raphael_public_health"],
                )
            )
    if _planet_in_houses(chart, "Uranus", {1, 6, 12}):
        house_position = _planet_house(chart, "Uranus")
        matched.append(
            _rule(
                "uranus_wave_disruption",
                "Uranus in a health-disruption house",
                10,
                f"Uranus in the {house_position} house points to abrupt turns, mutation-style instability, or a sudden change in the epidemic picture.",
                source_tags=["annotated_raphael_public_health", "green_public_affairs"],
            )
        )
    saturn_relevant = _planet_in_houses(chart, "Saturn", {6, 8, 12}) or _planet_angular(chart, "Saturn")
    uranus_relevant = _planet_in_houses(chart, "Uranus", {1, 6, 12}) or _planet_angular(chart, "Uranus")
    if saturn_relevant and uranus_relevant:
        matched.append(
            _rule(
                "saturn_uranus_wave_axis",
                "Saturn-Uranus epidemic axis",
                18,
                "Saturn and Uranus are both active on the health-burden axis, matching recurrence, mutation, or a renewed wave rather than a settled public-health picture.",
                source_tags=["annotated_raphael_public_health", "green_public_affairs"],
            )
        )
    if chart_type_id == "lunation" or "lunation" in chart_kind:
        if _planet_in_house(chart, "Moon", 8) or sixth_ruler == "Moon" or _planet_in_house(chart, "Mercury", 8):
            matched.append(
                _rule(
                    "lunation_wave_trigger",
                    "Lunation wave trigger",
                    12,
                    "The resolved lunation is tied directly to illness or mortality houses, matching a short peak window or wave spike rather than a diffuse background trend.",
                    source_tags=["annotated_raphael_public_health"],
                )
            )
    if chart_type_id == "eclipse" or "eclipse" in chart_kind:
        matched.append(
            _rule(
                "eclipse_wave_window",
                "Eclipse wave window",
                8,
                "An eclipse framework is active, which can sharpen a wave peak or mark the start of subsiding pressure when the other health factors agree.",
                source_tags=["annotated_raphael_public_health", "watters_eclipse_degree"],
            )
        )
    activation_profile = trigger_profiles.get("eclipse_degree_activation") or {}
    if activation_profile.get("active"):
        matched.append(
            _rule(
                "wave_activation_hits",
                "Activation hits present",
                max(10, int(activation_profile.get("score") or 0)),
                "Activation hits sharpen the timing of a wave peak, recurrence, or a visible secondary-health spike already shown by the chart.",
                source_tags=["watters_eclipse_degree"],
            )
        )
    cycle_state = _cycle_trigger_context(trigger_profiles.get("mutation_and_conjunction_cycles"))
    if cycle_state.get("active"):
        cycle_weight = max(8, min(12, int(cycle_state.get("score") or 0)))
        matched.append(
            _rule(
                "mutation_cycle_epidemic_backdrop",
                "Mutation-cycle epidemic backdrop",
                cycle_weight,
                f"The Jupiter-Saturn cycle backdrop is active in {cycle_state.get('sign') or 'the current sign'} with {cycle_state.get('phase') or 'an active phase'}, reinforcing longer collective-health turning periods behind visible wave activity.",
                source_tags=["watters_mutations", "annotated_raphael_public_health"],
            )
        )
        cautions.append("Long-cycle epidemic testimony is backdrop context and should be read with direct illness, mortality, or institutional-wave signatures.")
    jupiter_weight, jupiter_detail = _planet_angular_weight(chart, "Jupiter", base_weight=4, max_proximity_bonus=4)
    if jupiter_weight:
        matched.append(
            _rule(
                "jupiter_wave_relief",
                "Jupiter angular",
                -jupiter_weight,
                f"Jupiter is angular, nearest the {(jupiter_detail or {}).get('angle') or 'angle'} within {(jupiter_detail or {}).get('distance_deg') or 'unknown'}deg, moderating wave severity and supporting organized relief.",
                source_tags=["green_public_affairs"],
            )
        )
    if _planet_in_house(chart, "Jupiter", 12):
        matched.append(
            _rule(
                "jupiter_twelfth_wave_relief",
                "Jupiter in the twelfth",
                -8,
                "Jupiter in the twelfth supports hospitals, institutions, and organized relief, reducing the chance that a wave remains maximally destructive.",
                source_tags=["green_public_affairs"],
            )
        )
    if _uses_capital_chart_context(context) and capital_alignment.get("matches"):
        matched.append(
            _rule(
                "capital_chart_alignment_wave",
                "Capital-chart alignment",
                6,
                "The resolved location matches the polity capital under a capital-chart frame, keeping wave-pressure judgment anchored to the governing center.",
                source_tags=["green_ingress", "annotated_raphael_public_health"],
            )
        )
    else:
        penalty = _capital_chart_penalty_rule(
            context,
            weight=6,
            detail="Epidemic-wave reading through a capital-chart frame is weaker away from the governing capital.",
            source_tags=["green_ingress", "annotated_raphael_public_health"],
        )
        if penalty is not None:
            matched.append(penalty)

    return _finalize(
        domain_id="epidemic_wave_pressure",
        axis="wave_recrudescence_and_peak_pressure",
        base_summary="Epidemic wave pressure is evaluated from recurring illness and mortality signatures, secondary-wave triggers, and eclipse or lunation timing overlays within the broader public-health frame.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_public_health(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    trigger_profiles = _trigger_profiles(context, "eclipse_degree_activation")
    matched: List[Dict[str, Any]] = []
    cautions = ["Public-health output remains research-gated and should be read as collective burden, not deterministic medical prediction."]
    capital_alignment = _capital_alignment(context)

    for malefic in _MALEFICS:
        if _planet_in_house(chart, malefic, 1):
            matched.append(_rule(f"{_normalize_id(malefic)}_first_house_burden", f"{malefic} in the first", 12, f"{malefic} in the first house puts visible strain on the condition and health of the populace rather than keeping the burden hidden.", source_tags=["annotated_raphael_public_health", "green_public_affairs"]))

    sixth_ruler = _house_ruler(chart, 6)
    eighth_ruler = _house_ruler(chart, 8)
    twelfth_ruler = _house_ruler(chart, 12)
    if sixth_ruler:
        house_position = _planet_house(chart, sixth_ruler)
        if house_position in _ANGULAR_HOUSES:
            detail = _planet_angle_detail(chart, sixth_ruler)
            weight = 10 + _proximity_bonus((detail or {}).get("distance_deg"), max_bonus=8)
            matched.append(_rule("sixth_ruler_angular", "Sixth-house ruler angular", weight, f"The sixth-house ruler {sixth_ruler} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, making health burdens more publicly visible.", source_tags=["annotated_raphael_public_health", "green_public_affairs"]))
        if _planet_retrograde(chart, sixth_ruler):
            matched.append(_rule("sixth_ruler_retrograde", "Sixth-house ruler retrograde", 10, f"The sixth-house ruler {sixth_ruler} is retrograde, adding strain and persistence to burden indications.", source_tags=["annotated_raphael_public_health"]))
    if eighth_ruler and _planet_angular(chart, eighth_ruler):
        detail = _planet_angle_detail(chart, eighth_ruler)
        weight = 8 + _proximity_bonus((detail or {}).get("distance_deg"), max_bonus=6)
        matched.append(_rule("eighth_ruler_angular", "Eighth-house ruler angular", weight, f"The eighth-house ruler {eighth_ruler} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, increasing mortality or crisis visibility.", source_tags=["annotated_raphael_public_health", "green_public_affairs"]))
    if twelfth_ruler:
        twelfth_house_position = _planet_house(chart, twelfth_ruler)
        if twelfth_house_position in _ANGULAR_HOUSES:
            detail = _planet_angle_detail(chart, twelfth_ruler)
            weight = 8 + _proximity_bonus((detail or {}).get("distance_deg"), max_bonus=6)
            matched.append(_rule("twelfth_ruler_angular", "Twelfth-house ruler angular", weight, f"The twelfth-house ruler {twelfth_ruler} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, making hospitalization and institutional burden part of the public-health picture.", source_tags=["annotated_raphael_public_health", "green_public_affairs"]))
    if _planet_in_house(chart, "Saturn", 12):
        matched.append(_rule("saturn_in_twelfth", "Saturn in the twelfth", 12, "Saturn in the twelfth increases institutional hardship, pressure on hospitals, and prolonged public-health burden behind the scenes.", source_tags=["annotated_raphael_public_health", "green_public_affairs"]))
    for malefic in _MALEFICS:
        weight, detail = _planet_angular_weight(chart, malefic, base_weight=8, max_proximity_bonus=6)
        if weight:
            matched.append(_rule(f"{_normalize_id(malefic)}_angular", f"{malefic} angular", weight, f"{malefic} is angular, nearest the {(detail or {}).get('angle') or 'angle'} within {(detail or {}).get('distance_deg') or 'unknown'}deg, increasing public burden and severity signals.", source_tags=["annotated_raphael_public_health", "watters_venus_retrograde_epidemics"]))
    activation_profile = trigger_profiles.get("eclipse_degree_activation") or {}
    if activation_profile.get("active"):
        matched.append(_rule("activation_hits", "Activation hits present", max(12, int(activation_profile.get("score") or 0)), "Overlay activations sharpen the timing of already-present burden signatures.", source_tags=["watters_eclipse_degree"]))
    jupiter_weight, jupiter_detail = _planet_angular_weight(chart, "Jupiter", base_weight=3, max_proximity_bonus=3)
    if jupiter_weight:
        matched.append(_rule("jupiter_relief", "Jupiter angular", -jupiter_weight, f"Jupiter is angular, nearest the {(jupiter_detail or {}).get('angle') or 'angle'} within {(jupiter_detail or {}).get('distance_deg') or 'unknown'}deg, moderating severity and preserving institutional relief capacity.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Jupiter", 12):
        matched.append(_rule("jupiter_in_twelfth_relief", "Jupiter in the twelfth", -8, "Jupiter in the twelfth supports hospitals, charitable institutions, and organized relief capacity during collective-health strain.", source_tags=["green_public_affairs"]))
    if _planet_in_house(chart, "Venus", 12):
        matched.append(_rule("venus_in_twelfth_relief", "Venus in the twelfth", -6, "Venus in the twelfth supports benevolence, donations, and institutional goodwill that can soften public-health burden.", source_tags=["green_public_affairs"]))
    if _uses_capital_chart_context(context) and capital_alignment.get("matches"):
        matched.append(_rule("capital_chart_alignment", "Capital-chart alignment", 8, "The resolved location matches the polity capital under a capital-chart framework, keeping the public-health read anchored to the doctrinal governing center.", source_tags=["green_ingress", "annotated_raphael_public_health"]))
    else:
        penalty = _capital_chart_penalty_rule(
            context,
            weight=8,
            detail="Public-health ingress reading is weaker away from the governing capital when the scan is using a capital-chart frame.",
            source_tags=["green_ingress", "annotated_raphael_public_health"],
        )
        if penalty is not None:
            matched.append(penalty)

    return _finalize(
        domain_id="public_health",
        axis="collective_health_burden",
        base_summary="Public-health burden is evaluated from first-, sixth-, eighth-, and twelfth-house condition, malefic angularity, and research-gated trigger overlays.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_civil_unrest(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    trigger_profiles = _trigger_profiles(context, "eclipse_degree_activation", "retrograde_mars", "mutation_and_conjunction_cycles")
    matched: List[Dict[str, Any]] = []
    cautions = []
    unrest_houses = {1, 4, 10, 11}

    mars_weight, mars_detail = _planet_angular_weight(chart, "Mars", base_weight=12, max_proximity_bonus=8)
    if mars_weight:
        matched.append(_rule("mars_angular_unrest", "Mars angular", mars_weight, f"Mars is angular, nearest the {(mars_detail or {}).get('angle') or 'angle'} within {(mars_detail or {}).get('distance_deg') or 'unknown'}deg, raising riots, turbulence, and open public disturbance.", source_tags=["green_public_affairs"]))
    saturn_weight, saturn_detail = _planet_angular_weight(chart, "Saturn", base_weight=8, max_proximity_bonus=6)
    if saturn_weight:
        matched.append(_rule("saturn_angular_unrest", "Saturn angular", saturn_weight, f"Saturn is angular, nearest the {(saturn_detail or {}).get('angle') or 'angle'} within {(saturn_detail or {}).get('distance_deg') or 'unknown'}deg, adding public hardship, repression, and disorder pressure.", source_tags=["green_public_affairs"]))
    if _planet_angular(chart, "Uranus"):
        matched.append(_rule("uranus_angular_unrest", "Uranus angular", 18, "Angular Uranus matches reform movements, mass agitation, and sudden unrest signatures.", source_tags=["watters_mutations"]))
    if _planet_in_houses(chart, "Mars", {1, 4}):
        house_number = _planet_house(chart, "Mars")
        matched.append(_rule("mars_people_house", "Mars in a people house", 14, f"Mars in the {house_number} house matches discontent, strikes, riots, and aggressive public excitement among the people or opposition side of the chart.", source_tags=["green_public_affairs", "annotated_raphael_civil_unrest"]))
    if _planet_in_houses(chart, "Uranus", {1, 4}):
        house_number = _planet_house(chart, "Uranus")
        matched.append(_rule("uranus_people_house", "Uranus in a people house", 16, f"Uranus in the {house_number} house points to insurrectionary, strike, or reform-agitation pressure among the people rather than routine parliamentary disagreement.", source_tags=["annotated_raphael_civil_unrest", "watters_mutations"]))
    if _planet_in_houses(chart, "Mars", {6}):
        matched.append(_rule("mars_in_sixth_labor_unrest", "Mars in the 6th", 10, "Mars in the sixth brings workers, unions, wages, and service bodies into overt conflict, matching militant labor unrest or strike escalation.", source_tags=["green_public_affairs", "annotated_raphael_civil_unrest"]))
    if _planet_in_houses(chart, "Uranus", {6}):
        matched.append(_rule("uranus_in_sixth_strikes", "Uranus in the 6th", 12, "Uranus in the sixth points to strikes, insubordination, labor agitation, and sudden disruption among the nation's workers and service classes.", source_tags=["green_public_affairs", "annotated_raphael_civil_unrest"]))
    if _planet_in_houses(chart, "Moon", {4}):
        disruption = _first_present(
            planet
            for planet in ("Mars", "Saturn", "Uranus", "Neptune")
            if _planet_in_houses(chart, planet, {4, 10, 11})
        )
        if disruption:
            matched.append(_rule("moon_fourth_discontent", "Moon in the fourth under pressure", 12, f"The Moon is in the fourth house of the people and opposition, while {disruption} is also pressuring the 4th/10th/11th public axis, matching mass discontent rather than quiet democratic support.", source_tags=["green_public_affairs", "annotated_raphael_civil_unrest"]))
        else:
            matched.append(_rule("moon_fourth_foreground", "Moon in the fourth", 6, "The Moon in the fourth brings the people, opposition, and democratic questions to the front of the national picture.", source_tags=["green_public_affairs"]))
    fourth_ruler = _house_ruler(chart, 4)
    if fourth_ruler and _planet_retrograde(chart, fourth_ruler):
        matched.append(_rule("fourth_ruler_retrograde", "Fourth-house ruler retrograde", 10, f"The fourth-house ruler {fourth_ruler} is retrograde, showing unstable opposition, repeated crowd grievances, or public questions that refuse to settle cleanly.", source_tags=["green_public_affairs"]))
    for planet_name, label, weight, detail, tags in (
        ("Mars", "Mars in the eleventh", 12, "Mars in the eleventh raises quarrels, party splits, and militant parliamentary agitation.", ["green_public_affairs", "annotated_raphael_civil_unrest"]),
        ("Saturn", "Saturn in the eleventh", 12, "Saturn in the eleventh raises dissensions, adverse-vote risk, ministerial difficulty, and party fracture.", ["green_public_affairs", "annotated_raphael_civil_unrest"]),
        ("Uranus", "Uranus in the eleventh", 12, "Uranus in the eleventh points to extraordinary parliamentary complications, unruly debates, and sudden legislative disruption.", ["green_public_affairs", "annotated_raphael_civil_unrest"]),
        ("Neptune", "Neptune in the eleventh", 10, "Neptune in the eleventh points to socialistic agitation, secret plotting, or underhand parliamentary unrest around legislation.", ["green_public_affairs", "annotated_raphael_civil_unrest"]),
    ):
        if _planet_in_houses(chart, planet_name, {11}):
            matched.append(_rule(f"{_normalize_id(planet_name)}_in_eleventh", label, weight, detail, source_tags=tags))
    eleventh_ruler = _house_ruler(chart, 11)
    if eleventh_ruler and _planet_retrograde(chart, eleventh_ruler):
        matched.append(_rule("eleventh_ruler_retrograde", "Eleventh-house ruler retrograde", 12, f"The eleventh-house ruler {eleventh_ruler} is retrograde, adding legislative strain and public-body instability.", source_tags=["green_public_affairs"]))
    for planet_name, label, weight, detail, tags in (
        ("Mars", "Mars in the tenth", 10, "Mars in the tenth brings open conflict to government and authority, making unrest more confrontational than merely oppositional.", ["green_public_affairs"]),
        ("Saturn", "Saturn in the tenth", 9, "Saturn in the tenth burdens the government and can turn public discontent into an authority crisis or rigid repression.", ["green_public_affairs"]),
        ("Uranus", "Uranus in the tenth", 12, "Uranus in the tenth disturbs rulers and government, helping convert social agitation into executive rupture or rash state reaction.", ["green_public_affairs"]),
        ("Neptune", "Neptune in the tenth", 10, "Neptune in the tenth matches socialistic agitation against government, scandal, and public confusion in authority matters.", ["green_public_affairs", "annotated_raphael_civil_unrest"]),
    ):
        if _planet_in_houses(chart, planet_name, {10}):
            matched.append(_rule(f"{_normalize_id(planet_name)}_in_tenth", label, weight, detail, source_tags=tags))
    public_axis_load = sum(
        1
        for planet_name in ("Mars", "Saturn", "Uranus", "Neptune", "Moon")
        if _planet_in_houses(chart, planet_name, unrest_houses)
    )
    if public_axis_load >= 3:
        matched.append(_rule("public_axis_overload", "Public-axis overload", 12, "Three or more major public significators fall in the 1st/4th/10th/11th houses, concentrating unrest in the people-government-parliament axis rather than leaving it diffuse.", source_tags=["green_public_affairs", "annotated_raphael_civil_unrest"]))
    if any(_planet_in_houses(chart, planet, {4}) for planet in ("Moon", "Mars", "Saturn", "Uranus", "Neptune")) and any(_planet_in_houses(chart, planet, {10}) for planet in ("Mars", "Saturn", "Uranus", "Neptune")):
        matched.append(_rule("people_vs_government_axis", "People-versus-government axis", 10, "The fourth house of the people/opposition and the tenth house of government are both under stress, matching direct confrontation between crowd pressure and state authority.", source_tags=["green_public_affairs"]))
    activation_profile = trigger_profiles.get("eclipse_degree_activation") or {}
    if activation_profile.get("active"):
        matched.append(_rule("unrest_activation_hits", "Activation hits present", max(12, int(activation_profile.get("score") or 0)), "Activation hits support sudden public disorder timing inside an already stressed chart.", source_tags=["watters_eclipse_degree"]))
    if (trigger_profiles.get("retrograde_mars") or {}).get("active"):
        matched.append(_rule("mars_retrograde_unrest", "Mars retrograde", 8, "Retrograde Mars adds volatile reversals and attritional disorder rather than clean escalation.", source_tags=["watters_retrograde_mars"]))
        cautions.append("Retrograde Mars can coincide with disorder, but it should not be treated as a standalone riot trigger.")
    cycle_state = _cycle_trigger_context(trigger_profiles.get("mutation_and_conjunction_cycles"))
    if cycle_state.get("active"):
        cycle_weight = max(8, min(14, int(cycle_state.get("score") or 0)))
        matched.append(
            _rule(
                "mutation_cycle_unrest_backdrop",
                "Mutation-cycle unrest backdrop",
                cycle_weight,
                f"The Jupiter-Saturn cycle backdrop is active in {cycle_state.get('sign') or 'the current sign'} with {cycle_state.get('phase') or 'an active phase'}, placing the chart inside a broader social-turning period rather than an isolated burst of disorder.",
                source_tags=["watters_mutations", "bonatti_revolutions"],
            )
        )
        cautions.append("Long-cycle unrest testimony is backdrop context and should be read with shorter triggers, not as a standalone riot timer.")
    venus_weight, venus_detail = _planet_angular_weight(chart, "Venus", base_weight=4, max_proximity_bonus=4)
    if venus_weight:
        matched.append(_rule("venus_angular_relief", "Venus angular", -venus_weight, f"Venus is angular, nearest the {(venus_detail or {}).get('angle') or 'angle'} within {(venus_detail or {}).get('distance_deg') or 'unknown'}deg, preserving civic peace and softening public rupture.", source_tags=["green_public_affairs"]))
    jupiter_weight, jupiter_detail = _planet_angular_weight(chart, "Jupiter", base_weight=3, max_proximity_bonus=3)
    if jupiter_weight:
        matched.append(_rule("jupiter_angular_relief", "Jupiter angular", -jupiter_weight, f"Jupiter is angular, nearest the {(jupiter_detail or {}).get('angle') or 'angle'} within {(jupiter_detail or {}).get('distance_deg') or 'unknown'}deg, reducing public disorder pressure through institutional stability.", source_tags=["green_public_affairs"]))

    return _finalize(
        domain_id="civil_unrest",
        axis="public_disorder_pressure",
        base_summary="Civil unrest is evaluated from the people-government-parliament axis, malefic disruption, and sudden-activation overlays rather than foreign-war logic.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def _evaluate_finance_economy(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    trigger_profiles = _trigger_profiles(context, "eclipse_degree_activation", "mutation_and_conjunction_cycles")
    matched: List[Dict[str, Any]] = []
    cautions = []

    second_ruler = _house_ruler(chart, 2)
    eighth_ruler = _house_ruler(chart, 8)
    tenth_ruler = _house_ruler(chart, 10)
    eleventh_ruler = _house_ruler(chart, 11)
    if second_ruler and _planet_retrograde(chart, second_ruler):
        matched.append(_rule("second_ruler_retrograde", "Second-house ruler retrograde", 16, f"The second-house ruler {second_ruler} is retrograde, weakening treasury continuity or economic confidence.", source_tags=["green_public_affairs", "watters_mutations"]))
    if second_ruler and _planet_in_houses(chart, second_ruler, {8}):
        matched.append(_rule("second_ruler_in_eighth", "Second-house ruler in the eighth", 18, f"The second-house ruler {second_ruler} falls in the eighth house, bringing debt, taxation, or foreign-financial strain directly onto the treasury.", source_tags=["green_public_affairs", "annotated_raphael_finance"]))
    if second_ruler and _planet_in_houses(chart, second_ruler, {12}):
        matched.append(_rule("second_ruler_in_twelfth", "Second-house ruler in the twelfth", 14, f"The second-house ruler {second_ruler} falls in the twelfth house, showing hidden loss, waste, or money tied up in institutions and leakages rather than productive circulation.", source_tags=["green_public_affairs"]))
    if second_ruler and _planet_in_houses(chart, second_ruler, {10}):
        matched.append(_rule("second_ruler_in_tenth", "Second-house ruler in the tenth", 8, f"The second-house ruler {second_ruler} is tied to the tenth house, making treasury and credit questions a direct government problem rather than a background economic mood.", source_tags=["green_public_affairs"]))
    if second_ruler and _planet_in_houses(chart, second_ruler, {11}):
        matched.append(_rule("second_ruler_in_eleventh", "Second-house ruler in the eleventh", 8, f"The second-house ruler {second_ruler} falls in the eleventh house, tying finance to Parliament, budget votes, and legislative wrangling over revenue or trade.", source_tags=["annotated_raphael_finance", "green_public_affairs"]))
    if eighth_ruler and _planet_in_houses(chart, eighth_ruler, {2}):
        matched.append(_rule("eighth_ruler_in_second", "Eighth-house ruler in the second", 14, f"The eighth-house ruler {eighth_ruler} falls in the second house, making debt, death duties, or foreign-financial obligations bite directly into the exchequer.", source_tags=["green_public_affairs", "annotated_raphael_finance"]))
    if eighth_ruler and _planet_in_houses(chart, eighth_ruler, {10}):
        matched.append(_rule("eighth_ruler_in_tenth", "Eighth-house ruler in the tenth", 10, f"The eighth-house ruler {eighth_ruler} is in the tenth house, making debt and fiscal burdens publicly governmental and reputational rather than merely technical.", source_tags=["green_public_affairs"]))
    if _planet_in_houses(chart, "Saturn", {2}):
        matched.append(_rule("saturn_in_second", "Saturn in the second", 18, "Saturn in the second points to poor revenue, financial stagnation, depreciation in securities, and prolonged contraction in money matters.", source_tags=["green_public_affairs", "watters_mutations", "annotated_raphael_finance"]))
    else:
        saturn_weight, saturn_detail = _planet_angular_weight(chart, "Saturn", base_weight=6, max_proximity_bonus=6)
        if saturn_weight:
            matched.append(_rule("saturn_angular_finance", "Saturn angular", saturn_weight, f"Saturn is angular, nearest the {(saturn_detail or {}).get('angle') or 'angle'} within {(saturn_detail or {}).get('distance_deg') or 'unknown'}deg, increasing public austerity or contraction pressure around the treasury.", source_tags=["green_public_affairs"]))
    if _planet_in_houses(chart, "Mars", {2}):
        matched.append(_rule("mars_in_second", "Mars in the second", 14, "Mars in the second points to expenditure shocks, stock-exchange losses, panics, bank failures, and disputes over financial questions.", source_tags=["green_public_affairs", "annotated_raphael_finance"]))
    if _planet_in_houses(chart, "Uranus", {2}):
        matched.append(_rule("uranus_in_second", "Uranus in the second", 14, "Uranus in the second points to financial crashes, sudden losses, and uneasiness in markets or national revenue.", source_tags=["green_public_affairs", "annotated_raphael_finance"]))
    if _planet_in_houses(chart, "Moon", {2}):
        matched.append(_rule("moon_in_second", "Moon in the second", 6, "The Moon in the second shows fluctuation in revenue, the money market, and public financial feeling rather than stable receipts.", source_tags=["green_public_affairs", "annotated_raphael_finance"]))
    if _planet_in_houses(chart, "Mercury", {11}):
        weight = 6 + (4 if _planet_retrograde(chart, "Mercury") else 0)
        detail = "Mercury in the eleventh ties Parliament directly to trade, commerce, and budget legislation."
        if _planet_retrograde(chart, "Mercury"):
            detail += " Retrograde Mercury intensifies arguments, recriminations, and legislative disputes over commercial or revenue questions."
        matched.append(_rule("mercury_in_eleventh_finance", "Mercury in the eleventh", weight, detail, source_tags=["annotated_raphael_finance"]))
    if _planet_in_houses(chart, "Jupiter", {11}):
        matched.append(_rule("jupiter_in_eleventh_finance", "Jupiter in the eleventh", -8, "Jupiter in the eleventh supports democratic legislation and improvement in trade, finance, and commerce through Parliament.", source_tags=["annotated_raphael_finance"]))
    if _planet_in_houses(chart, "Saturn", {11}):
        matched.append(_rule("saturn_in_eleventh_finance", "Saturn in the eleventh", 10, "Saturn in the eleventh points to adverse-vote risk, obstacles to government finance, and difficulty around securities or budget legislation.", source_tags=["annotated_raphael_finance", "green_public_affairs"]))
    if _planet_in_houses(chart, "Mars", {11}):
        matched.append(_rule("mars_in_eleventh_finance", "Mars in the eleventh", 8, "Mars in the eleventh brings quarrels and parliamentary conflict into military appropriations, trade, or finance debates.", source_tags=["green_public_affairs"]))
    if tenth_ruler and _planet_retrograde(chart, tenth_ruler):
        matched.append(_rule("tenth_ruler_retrograde_finance", "Tenth-house ruler retrograde", 10, f"The tenth-house ruler {tenth_ruler} is retrograde, weakening national credit or the government's ability to carry treasury policy smoothly.", source_tags=["green_public_affairs"]))
    if eleventh_ruler and _planet_retrograde(chart, eleventh_ruler):
        matched.append(_rule("eleventh_ruler_retrograde_finance", "Eleventh-house ruler retrograde", 8, f"The eleventh-house ruler {eleventh_ruler} is retrograde, showing legislative friction around budget, trade, or securities questions.", source_tags=["annotated_raphael_finance"]))
    if second_ruler and eighth_ruler and _planet_in_houses(chart, second_ruler, {8}) and _planet_in_houses(chart, eighth_ruler, {2}):
        matched.append(_rule("treasury_debt_loop", "Treasury-debt loop", 14, "The second and eighth houses feed one another directly, showing a loop of treasury strain, credit burden, and taxation pressure rather than a clean growth picture.", source_tags=["green_public_affairs", "annotated_raphael_finance"]))
    if any(_planet_in_houses(chart, planet_name, {2}) for planet_name in ("Saturn", "Mars", "Uranus")) and any(_planet_in_houses(chart, planet_name, {11}) for planet_name in ("Mercury", "Mars", "Saturn")):
        matched.append(_rule("treasury_and_budget_blockage", "Treasury strain with parliamentary blockage", 12, "Treasury stress in the second house is combining with eleventh-house parliamentary blockage, matching budget fights or finance-policy paralysis rather than private hardship alone.", source_tags=["green_public_affairs", "annotated_raphael_finance"]))
    activation_profile = trigger_profiles.get("eclipse_degree_activation") or {}
    if activation_profile.get("active"):
        matched.append(_rule("finance_activation_hits", "Activation hits present", max(10, int(activation_profile.get("score") or 0)), "Activation hits can sharpen sudden financial turns inside an already stressed treasury picture.", source_tags=["watters_eclipse_degree"]))
    cycle_state = _cycle_trigger_context(trigger_profiles.get("mutation_and_conjunction_cycles"))
    if cycle_state.get("active"):
        cycle_weight = max(10, min(16, int(cycle_state.get("score") or 0)))
        matched.append(
            _rule(
                "mutation_cycle_financial_backdrop",
                "Mutation-cycle financial backdrop",
                cycle_weight,
                f"The Jupiter-Saturn cycle backdrop is active in {cycle_state.get('sign') or 'the current sign'} with {cycle_state.get('phase') or 'an active phase'}, matching a wider economic and social turning period behind the immediate treasury picture.",
                source_tags=["watters_mutations", "bonatti_revolutions"],
            )
        )
        cautions.append("Long-cycle finance testimony is backdrop context and should be separated from immediate treasury and budget triggers.")
    if _planet_in_houses(chart, "Jupiter", {2}) or _planet_angular(chart, "Jupiter"):
        jupiter_bonus = 0
        if _planet_angular(chart, "Jupiter"):
            jupiter_bonus = _proximity_bonus(((_planet_angle_detail(chart, "Jupiter") or {}).get("distance_deg")), max_bonus=4)
        matched.append(_rule("jupiter_financial_relief", "Jupiter support", -(8 + jupiter_bonus), "Jupiter in treasury-significant positions can preserve credit, trade, or relief capacity.", source_tags=["green_public_affairs"]))
    if _planet_in_houses(chart, "Venus", {2}) or _planet_angular(chart, "Venus"):
        venus_bonus = 0
        if _planet_angular(chart, "Venus"):
            venus_bonus = _proximity_bonus(((_planet_angle_detail(chart, "Venus") or {}).get("distance_deg")), max_bonus=3)
        matched.append(_rule("venus_financial_relief", "Venus support", -(5 + venus_bonus), "Venus in treasury-significant positions supports commerce, banks, and resource circulation.", source_tags=["green_public_affairs"]))
    if any(int(rule.get("weight") or 0) < 0 for rule in matched):
        cautions.append("Benefic treasury support moderates strain but does not erase broader contraction signatures.")

    return _finalize(
        domain_id="finance_economy",
        axis="financial_stress",
        base_summary="Finance and economy are evaluated from treasury condition, credit and debt pressure, banking and trade strain, and parliamentary blockage rather than personal wealth symbolism.",
        matched_rules=matched,
        cautions=cautions,
        research_flags=context.research_flags,
    )


def evaluate_domain_context(context: ResolvedMundaneContext) -> Dict[str, Any]:
    domain_id = _normalize_id((context.domain or {}).get("id"))
    if not domain_id:
        return {
            "domain_id": None,
            "axis": "none",
            "score": 0,
            "level": "quiet",
            "summary": "No domain lens has been selected yet.",
            "matched_rules": [],
            "cautions": [],
            "research_flags": list(context.research_flags),
        }
    if domain_id == "war_conflict":
        return _evaluate_war_conflict(context)
    if domain_id == "war_outbreak":
        return _evaluate_war_outbreak(context)
    if domain_id == "campaign_escalation":
        return _evaluate_campaign_escalation(context)
    if domain_id == "military_reversal":
        return _evaluate_military_reversal(context)
    if domain_id == "government_stability":
        return _evaluate_government_stability(context)
    if domain_id == "leadership_transition":
        return _evaluate_leadership_transition(context)
    if domain_id == "regime_stability":
        return _evaluate_regime_stability(context)
    if domain_id == "alliance_stress":
        return _evaluate_alliance_stress(context)
    if domain_id == "trade_and_commerce":
        return _evaluate_trade_and_commerce(context)
    if domain_id == "diplomacy_foreign_affairs":
        return _evaluate_diplomacy(context)
    if domain_id == "epidemic_wave_pressure":
        return _evaluate_epidemic_wave_pressure(context)
    if domain_id == "public_health":
        return _evaluate_public_health(context)
    if domain_id == "civil_unrest":
        return _evaluate_civil_unrest(context)
    if domain_id == "finance_economy":
        return _evaluate_finance_economy(context)
    return {
        "domain_id": domain_id,
        "axis": "unsupported_domain",
        "raw_score": 0,
        "score": 0,
        "raw_level": "quiet",
        "level": "quiet",
        "summary": f"No domain evaluator is implemented for {domain_id}.",
        "matched_rules": [],
        "cautions": [],
        "research_flags": list(context.research_flags),
        "calibration": {
            "coverage_tier": "unseeded",
            "unique_case_count": 0,
            "dataset_row_count": 0,
            "distinct_source_count": 0,
            "distinct_sources": [],
            "benchmark_types": {},
            "seed_quality_counts": {},
            "chart_basis_counts": {},
            "confidence_factor": 0.8,
            "score_cap": 70,
            "gaps": ["no_benchmark_cases"],
        },
    }
