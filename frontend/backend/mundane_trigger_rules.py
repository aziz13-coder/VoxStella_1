from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from mundane_models import ResolvedMundaneContext

_ANGULAR_HOUSES = {1, 4, 7, 10}
_MALEFICS = {"Mars", "Saturn"}
_BENEFICS = {"Jupiter", "Venus"}


def _normalize_id(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _chart_from_resolution(context: ResolvedMundaneContext) -> Optional[Dict[str, Any]]:
    resolution = context.chart_resolution if isinstance(context.chart_resolution, dict) else {}
    primary = resolution.get("primary_chart")
    return primary if isinstance(primary, dict) else None


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


def _signals(context: ResolvedMundaneContext) -> Dict[str, Any]:
    resolution = context.chart_resolution if isinstance(context.chart_resolution, dict) else {}
    signals = resolution.get("signals") or {}
    return signals if isinstance(signals, dict) else {}


def _activation_hits(context: ResolvedMundaneContext) -> List[Dict[str, Any]]:
    hits = _signals(context).get("activation_hits") or []
    return [item for item in hits if isinstance(item, dict)]


def _strength_from_score(score: int) -> str:
    if score >= 24:
        return "strong"
    if score >= 12:
        return "active"
    if score > 0:
        return "watch"
    return "inactive"


def _profile(
    profile_id: str,
    label: str,
    *,
    status: str,
    active: bool,
    score: int,
    summary: str,
    source_tags: Iterable[str],
    research_flags: Iterable[str],
    evidence: Iterable[Dict[str, Any]],
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "id": profile_id,
        "label": label,
        "status": status,
        "active": bool(active),
        "strength": _strength_from_score(int(score)),
        "score": int(score),
        "summary": summary,
        "source_tags": [str(item) for item in source_tags if str(item).strip()],
        "research_flags": [str(item) for item in research_flags if str(item).strip()],
        "evidence": [item for item in evidence if isinstance(item, dict)],
        "metrics": dict(metrics or {}),
    }


def _angularity_profile(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    evidence: List[Dict[str, Any]] = []
    malefic_count = 0
    benefic_count = 0
    score = 0
    for planet_name in _planets(chart).keys():
        detail = _planet_angle_detail(chart, planet_name)
        if not detail or detail.get("house") not in _ANGULAR_HOUSES:
            continue
        distance = float(detail.get("distance_deg") or 0.0)
        base = 8 if planet_name in _MALEFICS else 6 if planet_name in _BENEFICS else 5
        bonus = max(0, int(round(6 * (1.0 - min(distance, 15.0) / 15.0))))
        planet_score = base + bonus
        score += planet_score
        if planet_name in _MALEFICS:
            malefic_count += 1
        if planet_name in _BENEFICS:
            benefic_count += 1
        evidence.append(
            {
                "planet": planet_name,
                "house": detail.get("house"),
                "angle": detail.get("angle"),
                "distance_deg": detail.get("distance_deg"),
                "role": "malefic" if planet_name in _MALEFICS else "benefic" if planet_name in _BENEFICS else "neutral",
                "score": planet_score,
            }
        )
    evidence.sort(key=lambda item: (-int(item.get("score") or 0), float(item.get("distance_deg") or 999.0), str(item.get("planet") or "")))
    summary = "No angular testimony was computed in the resolved chart."
    if evidence:
        lead = evidence[0]
        summary = (
            f"Angularity is active; {lead.get('planet')} is nearest the {lead.get('angle')} within "
            f"{lead.get('distance_deg')}deg, with {malefic_count} malefic and {benefic_count} benefic angular testimonies present."
        )
    return _profile(
        "angularity",
        "Angularity",
        status="computed" if evidence else "watch",
        active=bool(evidence),
        score=score,
        summary=summary,
        source_tags=["green_eclipses", "watters_eclipse_degree"],
        research_flags=[],
        evidence=evidence,
        metrics={
            "angular_count": len(evidence),
            "malefic_angular_count": malefic_count,
            "benefic_angular_count": benefic_count,
            "strongest_planet": (evidence[0] if evidence else {}).get("planet"),
            "strongest_distance_deg": (evidence[0] if evidence else {}).get("distance_deg"),
        },
    )


def _retrograde_mars_profile(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    signals = _signals(context)
    mars_retrograde = bool(signals.get("mars_retrograde") or _planet_retrograde(chart, "Mars"))
    mars_house = _planet_house(chart, "Mars")
    house_rulers = chart.get("house_rulers") if isinstance(chart, dict) else {}
    rules_houses = []
    if isinstance(house_rulers, dict):
        for house_key, ruler in house_rulers.items():
            if str(ruler) == "Mars":
                try:
                    rules_houses.append(int(house_key))
                except Exception:
                    continue
    evidence = []
    score = 0
    summary = "Mars is direct in the resolved chart, so the retrograde-Mars warning is inactive."
    if mars_retrograde:
        score = 20
        summary = "Mars is retrograde in the resolved chart, activating the reversal and unstable-aggression warning."
        evidence.append(
            {
                "planet": "Mars",
                "retrograde": True,
                "house": mars_house,
                "rules_houses": rules_houses,
            }
        )
    return _profile(
        "retrograde_mars",
        "Retrograde Mars",
        status="computed",
        active=mars_retrograde,
        score=score,
        summary=summary,
        source_tags=["watters_retrograde_mars"],
        research_flags=["source_concentrated"] if mars_retrograde else [],
        evidence=evidence,
        metrics={
            "mars_house": mars_house,
            "rules_houses": rules_houses,
            "retrograde": mars_retrograde,
        },
    )


def _eclipse_degree_activation_profile(context: ResolvedMundaneContext) -> Dict[str, Any]:
    hits = _activation_hits(context)
    strongest_orb = None
    if hits:
        strongest_orb = min(float(hit.get("orb_deg") or 999.0) for hit in hits)
    summary = "No eclipse-degree activation hits were present in the resolved chart."
    if hits:
        summary = f"{len(hits)} eclipse-degree activation hit(s) were found, with the strongest orb at {round(float(strongest_orb), 3)}deg."
    score = 8 * len(hits)
    if strongest_orb is not None and strongest_orb <= 1.5:
        score += 6
    return _profile(
        "eclipse_degree_activation",
        "Eclipse-Degree Activation",
        status="computed",
        active=bool(hits),
        score=score,
        summary=summary,
        source_tags=["watters_eclipse_degree"],
        research_flags=[],
        evidence=hits,
        metrics={
            "hit_count": len(hits),
            "strongest_orb_deg": None if strongest_orb is None else round(float(strongest_orb), 3),
            "activating_planets": sorted({str(hit.get("planet")) for hit in hits if hit.get("planet")}),
        },
    )


def _mutation_and_conjunction_cycles_profile(context: ResolvedMundaneContext) -> Dict[str, Any]:
    chart = _chart_from_resolution(context)
    resolution = context.chart_resolution if isinstance(context.chart_resolution, dict) else {}
    signals = _signals(context)
    cycle_context = resolution.get("cycle_context") if isinstance(resolution.get("cycle_context"), dict) else {}
    cycle_context = {**cycle_context, **({} if not isinstance(signals.get("cycle_context"), dict) else signals.get("cycle_context"))}
    chart_type_id = _normalize_id((context.chart_type or {}).get("id"))
    evidence = []
    score = 0
    active = False
    if cycle_context:
        evidence.append(cycle_context)
        nearest_distance_years = float(cycle_context.get("nearest_distance_years") or 99.0)
        turning_window_active = bool(cycle_context.get("turning_window_active"))
        turning_window_level = str(cycle_context.get("turning_window_level") or "background")
        if turning_window_level == "strong":
            score = 18
        elif turning_window_active:
            score = 12
        else:
            score = 6
        active = turning_window_active
        summary = (
            f"Jupiter-Saturn cycle context is computed for this chart; the nearest conjunction is "
            f"{cycle_context.get('nearest_conjunction_datetime')} in {cycle_context.get('conjunction_sign')}, "
            f"{nearest_distance_years:.3f} years from the anchor."
        )
        if turning_window_active:
            summary += " The chart falls inside the configured conjunction turning window."
        else:
            summary += " The chart sits outside the current turning window, so the cycle stays background-weighted."
        status = "computed"
    elif chart_type_id in {"national_chart", "aries_ingress", "lunation", "eclipse"} or _normalize_id((chart or {}).get("kind")) in {"national_chart", "aries_ingress", "new_moon", "full_moon", "solar_eclipse", "lunar_eclipse"}:
        summary = "This chart can host mutation or conjunction-cycle doctrine, but no explicit cycle marker was computed in the current runtime."
        status = "background_only"
    else:
        summary = "Mutation and conjunction cycles remain background doctrine for this request and were not explicitly computed."
        status = "background_only"
    return _profile(
        "mutation_and_conjunction_cycles",
        "Mutation / Conjunction Cycles",
        status=status,
        active=active,
        score=score,
        summary=summary,
        source_tags=["bonatti_revolutions", "watters_mutations"],
        research_flags=(["background_only"] if status == "background_only" else []) + (["long_cycle_backdrop"] if cycle_context else []),
        evidence=evidence,
        metrics={
            "has_cycle_context": bool(cycle_context),
            "chart_type_id": chart_type_id,
            "nearest_distance_years": cycle_context.get("nearest_distance_years") if cycle_context else None,
            "turning_window_active": bool(cycle_context.get("turning_window_active")) if cycle_context else False,
            "turning_window_level": cycle_context.get("turning_window_level") if cycle_context else None,
            "cycle_phase": cycle_context.get("cycle_phase") if cycle_context else None,
            "conjunction_sign": cycle_context.get("conjunction_sign") if cycle_context else None,
        },
    )


def compute_trigger_profiles(
    context: ResolvedMundaneContext,
    *,
    trigger_ids: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    requested = {_normalize_id(item) for item in (trigger_ids or []) if _normalize_id(item)}
    if not requested:
        requested = {
            "angularity",
            "retrograde_mars",
            "eclipse_degree_activation",
            "mutation_and_conjunction_cycles",
        }
    profiles = []
    factories = {
        "angularity": _angularity_profile,
        "retrograde_mars": _retrograde_mars_profile,
        "eclipse_degree_activation": _eclipse_degree_activation_profile,
        "mutation_and_conjunction_cycles": _mutation_and_conjunction_cycles_profile,
    }
    for trigger_id in requested:
        factory = factories.get(trigger_id)
        if factory is None:
            continue
        profiles.append(factory(context))
    profiles.sort(key=lambda row: str(row.get("id") or ""))
    return profiles


def index_trigger_profiles(
    context: ResolvedMundaneContext,
    *,
    trigger_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    return {_normalize_id(profile.get("id")): profile for profile in compute_trigger_profiles(context, trigger_ids=trigger_ids)}
