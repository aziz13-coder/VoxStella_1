from __future__ import annotations

import math
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from astrocartography_city_catalog import (
    DEFAULT_ATLAS_RESOLUTION,
    city_catalog_candidate_matches_identity,
    city_catalog_candidate_matches_keyword,
    get_country_catalog_meta,
    get_city_catalog_country_codes_for_alias,
    get_atlas_resolution_settings,
    parse_city_catalog_identity_query,
    search_city_catalog,
)
from astrocartography_goal_engine import (
    evaluate_goal_model,
    extract_relocation_features,
    get_goal_score_polarity,
    summarize_relocation_features,
)
from astrocartography_goal_models import get_goal_model
from astrocartography_service import (
    DEFAULT_ANGLES,
    DEFAULT_BODIES,
    EXTENDED_READING_RADIUS_KM,
    PRIMARY_READING_RADIUS_KM,
    build_goal_scoring_context,
    build_location_reading,
    crossing_candidates_for_point,
)
from astrocartography_uncertainty import (
    MAX_ATLAS_STABILITY_CANDIDATES,
    apply_cross_location_rank_stability,
    attach_birth_time_sample_evaluations,
    bounded_stability_pool,
)
from horary_engine.services.geolocation import search_live_location_candidates


DEFAULT_ATLAS_LIMIT = 8
DEFAULT_RELOCATION_LIMIT = 18
MIN_ATLAS_RAW_SCORE = 0.25
DEFAULT_SHORTLIST_STRATEGY = "line_first"
RELOCATION_PREPASS_SHORTLIST_STRATEGY = "relocation_prepass"
MAX_RELOCATION_PREPASS_LIMIT = 480
GEOGRAPHIC_DIVERSITY_RADIUS_KM = 250.0
MAX_ATLAS_STABILITY_EVALUATIONS = 256
RELOCATION_AWARE_EVALUATION_STRATEGIES = {
    "accident_pressure",
    "gambling_natal_curated",
}

ASTROLOGY_RANKING_BASIS = {
    "scope": "astrological_interpretation_only",
    "description": (
        "Ranks the selected goal's astrological indicators only; it does not "
        "measure whether a destination is suitable in everyday life."
    ),
    "goal_required": True,
    "tie_breaker": "stable_label_then_candidate_id",
    "population_used_for_ranking": False,
    "display_order": "geographic_diversity_order_kept_separate_from_astrology_rank",
}

PRACTICAL_CONTEXT_POLICY = {
    "status": "not_assessed",
    "separate_from_astrology_ranking": True,
    "dimensions": ["personal_safety", "healthcare", "cost_of_living", "economy", "visa_and_immigration"],
    "guidance": (
        "Check current safety, healthcare, cost, employment, and visa sources "
        "separately before making a travel or relocation decision."
    ),
}

GOAL_SELECTION_POLICY = {
    "ranking_mode": "goal_specific",
    "goal_required": True,
    "neutral_overview": {
        "available": True,
        "ranked": False,
        "description": (
            "The map and single-location reading provide a neutral line overview. "
            "City ranking requires an explicit goal because there is no universal best place."
        ),
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


def _check_should_continue(should_continue: Optional[Callable[[], None]]) -> None:
    if should_continue is None:
        return
    should_continue()


def _empty_relocation_features() -> Dict[str, Any]:
    return {
        "planet_houses": {},
        "planet_angles": {},
        "house_occupancy": {},
        "metrics": {},
    }


def _normalize_target_text(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, dict):
        text = ""
        for key in ("query", "label", "name", "display_name", "address"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                text = candidate.strip()
                break
    else:
        text = ""

    if not text:
        return ""
    if text == "[object Object]":
        return ""
    if text.startswith("[object Object],"):
        return text.replace("[object Object],", "", 1).strip()
    return text


def _candidate_matches_identity_query(city: Dict[str, Any], query: Optional[str]) -> bool:
    if not str(query or "").strip():
        return True
    return city_catalog_candidate_matches_identity(city, query)


def _merge_atlas_candidates(
    catalog_candidates: Sequence[Dict[str, Any]],
    live_candidates: Sequence[Dict[str, Any]],
    *,
    continent_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    country_meta = get_country_catalog_meta()
    continent_norm = str(continent_code or "").strip().upper()
    merged: List[Dict[str, Any]] = []
    seen = set()

    def _dedupe_key(city: Dict[str, Any]) -> tuple:
        return (
            str(city.get("ascii_name") or city.get("name") or city.get("label") or "").strip().lower(),
            str(city.get("country_code") or "").strip().upper(),
            round(float(city.get("latitude") or 0.0), 3),
            round(float(city.get("longitude") or 0.0), 3),
        )

    for city in list(catalog_candidates) + list(live_candidates):
        item = dict(city)
        if item.get("candidate_id") in (None, ""):
            if item.get("geonameid") not in (None, ""):
                item["candidate_id"] = f"geonames:{item.get('geonameid')}"
            elif item.get("id") not in (None, ""):
                item["candidate_id"] = str(item.get("id"))
            else:
                item["candidate_id"] = (
                    f"coordinate:{round(float(item.get('latitude') or 0.0), 6)}:"
                    f"{round(float(item.get('longitude') or 0.0), 6)}"
                )
        if not item.get("coordinate_source"):
            item["coordinate_source"] = (
                str(item.get("live_source") or "live_geocoder")
                if item.get("live_source") or str(item.get("feature_code") or "").upper() == "LIVE"
                else "bundled_geonames_catalog"
            )
        country_code = str(item.get("country_code") or "").strip().upper()
        meta = country_meta.get(country_code, {})
        if not item.get("country_name") and meta.get("country_name"):
            item["country_name"] = meta.get("country_name")
        if not item.get("continent_code") and meta.get("continent_code"):
            item["continent_code"] = meta.get("continent_code")
            item["continent_name"] = meta.get("continent_name")
        if continent_norm and str(item.get("continent_code") or "").upper() != continent_norm:
            continue
        key = _dedupe_key(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def derive_goal_search_filters(
    goal_id: str,
    *,
    selected_bodies: Optional[Iterable[str]] = None,
    selected_angles: Optional[Iterable[str]] = None,
) -> Tuple[List[str], List[str]]:
    filter_meta = describe_goal_search_filters(
        goal_id,
        selected_bodies=selected_bodies,
        selected_angles=selected_angles,
    )
    return filter_meta["bodies"], filter_meta["angles"]


def describe_goal_search_filters(
    goal_id: str,
    *,
    selected_bodies: Optional[Iterable[str]] = None,
    selected_angles: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    model = get_goal_model(goal_id)
    supported_bodies = set(DEFAULT_BODIES)
    supported_angles = set(DEFAULT_ANGLES)
    atlas_filters = model.get("atlas_search_filters") if isinstance(model.get("atlas_search_filters"), dict) else {}

    goal_bodies: set[str] = {
        name
        for name in (
            str(body or "").strip()
            for body in (atlas_filters.get("bodies") or [])
        )
        if name in supported_bodies
    }
    goal_angles: set[str] = {
        name
        for name in (
            str(angle or "").strip().upper()
            for angle in (atlas_filters.get("angles") or [])
        )
        if name in supported_angles
    }

    bodies_from_components = not goal_bodies
    angles_from_components = not goal_angles

    for component in model.get("score_components") or []:
        kind = str(component.get("kind") or "")
        if kind == "line":
            planet = str(component.get("planet") or "").strip()
            if bodies_from_components and planet in supported_bodies:
                goal_bodies.add(planet)
            for angle in component.get("angles") or []:
                name = str(angle or "").strip().upper()
                if angles_from_components and name in supported_angles:
                    goal_angles.add(name)
        elif kind == "crossing":
            for planet in component.get("pair") or []:
                name = str(planet or "").strip()
                if bodies_from_components and name in supported_bodies:
                    goal_bodies.add(name)

    body_filter = [str(body).strip() for body in (selected_bodies or []) if str(body).strip()]
    angle_filter = [str(angle).strip().upper() for angle in (selected_angles or []) if str(angle).strip()]
    has_signature = bool(goal_bodies and goal_angles)

    if body_filter:
        goal_bodies = goal_bodies.intersection(body_filter)

    if angle_filter:
        goal_angles = goal_angles.intersection(angle_filter)

    return {
        "bodies": sorted(goal_bodies),
        "angles": sorted(goal_angles),
        "goal_has_signature": has_signature,
        "excluded_by_filters": bool(has_signature and (not goal_bodies or not goal_angles)),
    }


def _candidate_identity_payload(city: Dict[str, Any]) -> Dict[str, Any]:
    latitude = float(city.get("latitude") or 0.0)
    longitude = float(city.get("longitude") or 0.0)
    candidate_id = (
        str(city.get("candidate_id"))
        if city.get("candidate_id") not in (None, "")
        else (
            f"geonames:{city.get('geonameid')}"
            if city.get("geonameid") not in (None, "")
            else None
        )
    )
    return {
        "target": {
            "candidate_id": candidate_id,
            "label": _normalize_target_text(city.get("label")) or _normalize_target_text(city.get("query")),
            "query": _normalize_target_text(city.get("query")) or _normalize_target_text(city.get("label")),
            "latitude": latitude,
            "longitude": longitude,
            "coordinate_source": city.get("coordinate_source") or (
                "bundled_geonames_catalog"
                if city.get("geonameid") not in (None, "")
                else "candidate_coordinates"
            ),
        },
        "atlas_city": {
            "candidate_id": candidate_id,
            "geonameid": city.get("geonameid"),
            "country_code": city.get("country_code"),
            "country_name": city.get("country_name"),
            "admin1_code": city.get("admin1_code"),
            "population": int(city.get("population") or 0),
            "timezone": city.get("timezone"),
            "feature_code": city.get("feature_code"),
        },
    }


def _score_candidate(
    city: Dict[str, Any],
    *,
    goal_id: str,
    natal_lines: Sequence[Dict[str, Any]],
    transit_lines: Optional[Sequence[Dict[str, Any]]] = None,
    relocation_features: Optional[Dict[str, Any]] = None,
    relocation_status: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    identity = _candidate_identity_payload(city)
    latitude = float((identity.get("target") or {}).get("latitude") or 0.0)
    longitude = float((identity.get("target") or {}).get("longitude") or 0.0)

    natal_reading = build_location_reading(
        natal_lines,
        latitude,
        longitude,
        primary_radius_km=PRIMARY_READING_RADIUS_KM,
        extended_radius_km=EXTENDED_READING_RADIUS_KM,
    )
    natal_scoring = build_goal_scoring_context(
        natal_lines,
        latitude,
        longitude,
        primary_radius_km=PRIMARY_READING_RADIUS_KM,
        extended_radius_km=EXTENDED_READING_RADIUS_KM,
    )
    natal_crossings = crossing_candidates_for_point(
        natal_lines,
        latitude,
        longitude,
        nearest_rows=natal_reading.get("nearest_lines") or [],
        max_distance_km=EXTENDED_READING_RADIUS_KM,
    )

    transit_reading = None
    transit_scoring = None
    transit_crossings = None
    if transit_lines:
        transit_reading = build_location_reading(
            transit_lines,
            latitude,
            longitude,
            primary_radius_km=PRIMARY_READING_RADIUS_KM,
            extended_radius_km=EXTENDED_READING_RADIUS_KM,
        )
        transit_scoring = build_goal_scoring_context(
            transit_lines,
            latitude,
            longitude,
            primary_radius_km=PRIMARY_READING_RADIUS_KM,
            extended_radius_km=EXTENDED_READING_RADIUS_KM,
        )
        transit_crossings = crossing_candidates_for_point(
            transit_lines,
            latitude,
            longitude,
            nearest_rows=transit_reading.get("nearest_lines") or [],
            max_distance_km=EXTENDED_READING_RADIUS_KM,
        )

    goal_eval = evaluate_goal_model(
        goal_id,
        natal_rows=natal_scoring.get("nearest_lines") or [],
        natal_crossings=natal_scoring.get("crossings") or [],
        relocation=relocation_features or _empty_relocation_features(),
        transit_rows=(transit_scoring.get("nearest_lines") or []) if transit_scoring else None,
        transit_crossings=(transit_scoring.get("crossings") or []) if transit_scoring else None,
    )

    result: Dict[str, Any] = {
        **identity,
        "natal": {
            "reading": natal_reading,
            "crossings": natal_crossings,
        },
        "location_score": goal_eval,
    }
    if transit_reading:
        result["transit"] = {
            "reading": transit_reading,
            "crossings": transit_crossings,
        }
    if relocation_features is not None:
        result["relocation"] = {
            "available": True,
            "relocation_unavailable": False,
            "summary": summarize_relocation_features(relocation_features),
            "provenance": (relocation_status or {}).get("provenance") or {},
            "warnings": (relocation_status or {}).get("warnings") or [],
        }
    elif relocation_status:
        result["relocation"] = {
            "available": False,
            "relocation_unavailable": True,
            "summary": {},
            "error": relocation_status.get("error"),
            "provenance": relocation_status.get("provenance") or {},
            "warnings": relocation_status.get("warnings") or [],
        }
    return result


def _passes_signal_floor(
    item: Dict[str, Any],
    *,
    min_raw_score: float = MIN_ATLAS_RAW_SCORE,
    score_polarity: str = "higher_is_better",
) -> bool:
    score_payload = item.get("location_score") or {}
    if score_payload.get("ranking_eligible") is False:
        return False
    if score_polarity == "higher_is_worse":
        return bool(score_payload)
    raw_score = float(score_payload.get("raw_score") or 0.0)
    if raw_score >= float(min_raw_score):
        return True
    return any(float(entry.get("score") or 0.0) > 0.0 for entry in (score_payload.get("top_supports") or []))


def build_location_score_sort_key(
    location_score: Dict[str, Any],
    *,
    label: Any = "",
    population: Any = 0,
    score_polarity: str = "higher_is_better",
) -> tuple[float, float, str]:
    # Population may bound the candidate pool, but it is intentionally not a
    # ranking signal or tie-breaker in an astrology-only ordering.
    _ = population
    raw_score = float(location_score.get("raw_score") or 0.0)
    score = float(location_score.get("score") or 0.0)
    stable_label = str(label or "").casefold()
    if score_polarity == "higher_is_worse":
        return (
            raw_score,
            score,
            stable_label,
        )
    return (
        -raw_score,
        -score,
        stable_label,
    )


def _scored_candidate_sort_key(
    item: Dict[str, Any],
    *,
    score_polarity: str = "higher_is_better",
) -> tuple[float, float, float, str, str]:
    relocation = item.get("relocation") or {}
    relocation_unavailable = 1.0 if relocation.get("relocation_unavailable") else 0.0
    target = item.get("target") or {}
    return (
        relocation_unavailable,
        *build_location_score_sort_key(
        item.get("location_score") or {},
        label=(target.get("label") or target.get("query") or ""),
        score_polarity=score_polarity,
        ),
        str(target.get("candidate_id") or "").casefold(),
    )


def _target_coordinates(item: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    target = item.get("target") or {}
    try:
        latitude = float(target.get("latitude"))
        longitude = float(target.get("longitude"))
    except (TypeError, ValueError):
        return None
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        return None
    return latitude, longitude


def _great_circle_distance_km(
    left: Tuple[float, float],
    right: Tuple[float, float],
) -> float:
    left_lat, left_lon = map(math.radians, left)
    right_lat, right_lon = map(math.radians, right)
    delta_lat = right_lat - left_lat
    delta_lon = right_lon - left_lon
    haversine = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(left_lat) * math.cos(right_lat) * math.sin(delta_lon / 2.0) ** 2
    )
    return 6371.0088 * 2.0 * math.asin(math.sqrt(min(1.0, max(0.0, haversine))))


def _geographic_group_id(item: Dict[str, Any]) -> str:
    target = item.get("target") or {}
    candidate_id = str(target.get("candidate_id") or "").strip()
    if candidate_id:
        return f"area:{candidate_id}"
    coordinates = _target_coordinates(item)
    if coordinates is not None:
        return f"area:{coordinates[0]:.4f}:{coordinates[1]:.4f}"
    return f"area:{str(target.get('label') or target.get('query') or 'unknown').strip().lower()}"


def _with_geographic_group(
    item: Dict[str, Any],
    *,
    representative: Dict[str, Any],
    distance_km: float,
    selection_pass: str,
    astrology_rank: int,
    display_rank: int,
) -> Dict[str, Any]:
    result = dict(item)
    target = representative.get("target") or {}
    representative_label = str(target.get("label") or target.get("query") or "Regional result").strip()
    result["geographic_group"] = {
        "id": _geographic_group_id(representative),
        "label": f"{representative_label} area",
        "representative_candidate_id": target.get("candidate_id"),
        "representative_label": representative_label,
        "distance_to_representative_km": round(max(0.0, float(distance_km)), 1),
        "is_representative": item is representative,
        "selection_pass": selection_pass,
        "astrology_rank": int(astrology_rank),
        "display_rank": int(display_rank),
    }
    result["astrology_rank"] = int(astrology_rank)
    result["display_rank"] = int(display_rank)
    result["selection_order"] = int(display_rank)
    result["ranking_basis"] = dict(ASTROLOGY_RANKING_BASIS)
    result["practical_context"] = dict(PRACTICAL_CONTEXT_POLICY)
    result["suitability_assessed"] = False
    return result


def select_geographically_diverse_results(
    rows: Sequence[Dict[str, Any]],
    *,
    limit: int,
    radius_km: float = GEOGRAPHIC_DIVERSITY_RADIUS_KM,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Prefer distinct regions while preserving deterministic score order.

    A second pass fills any remaining slots, so narrow or local searches still
    return the requested number of candidates. Every returned row carries an
    explicit regional group and whether it was chosen in the diversity or fill
    pass.
    """

    requested_limit = max(0, int(limit))
    threshold_km = max(0.0, float(radius_km))
    selected: List[Tuple[Dict[str, Any], Dict[str, Any], float, str, int]] = []
    representatives: List[Dict[str, Any]] = []
    deferred: List[Tuple[Dict[str, Any], Dict[str, Any], float, int]] = []

    for astrology_rank, item in enumerate(rows, start=1):
        coordinates = _target_coordinates(item)
        nearest_representative = None
        nearest_distance = float("inf")
        if coordinates is not None:
            for representative in representatives:
                representative_coordinates = _target_coordinates(representative)
                if representative_coordinates is None:
                    continue
                distance = _great_circle_distance_km(coordinates, representative_coordinates)
                if distance < nearest_distance:
                    nearest_representative = representative
                    nearest_distance = distance

        is_distinct = (
            nearest_representative is None
            or nearest_distance >= threshold_km
        )
        if is_distinct and len(selected) < requested_limit:
            representatives.append(item)
            selected.append((item, item, 0.0, "distinct_region", astrology_rank))
        elif nearest_representative is not None:
            deferred.append((item, nearest_representative, nearest_distance, astrology_rank))

    same_region_fill_count = 0
    if len(selected) < requested_limit:
        for item, representative, distance, astrology_rank in deferred:
            selected.append((item, representative, distance, "same_region_fill", astrology_rank))
            same_region_fill_count += 1
            if len(selected) >= requested_limit:
                break

    final_results = []
    for display_rank, (
        item,
        representative,
        distance,
        selection_pass,
        astrology_rank,
    ) in enumerate(selected, start=1):
        final_results.append(
            _with_geographic_group(
                item,
                representative=representative,
                distance_km=distance,
                selection_pass=selection_pass,
                astrology_rank=astrology_rank,
                display_rank=display_rank,
            )
        )
    distinct_group_count = len(
        {
            str((item.get("geographic_group") or {}).get("id") or "")
            for item in final_results
        }
    )
    return final_results, {
        "enabled": True,
        "method": "deterministic_greedy_distance_then_fill",
        "radius_km": round(threshold_km, 1),
        "requested_result_count": requested_limit,
        "returned_result_count": len(final_results),
        "distinct_region_count": distinct_group_count,
        "same_region_fill_count": same_region_fill_count,
        "deferred_same_region_count": len(deferred),
        "ordering": {
            "astrology_rank": "global score order before geographic diversity",
            "display_rank": "geographically diversified presentation order",
        },
    }


def _build_scored_candidate_ranking(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranking: List[Dict[str, Any]] = []
    for index, item in enumerate(rows, start=1):
        target = item.get("target") or {}
        location_score = item.get("location_score") or {}
        atlas_city = item.get("atlas_city") or {}
        astrology_rank = int(item.get("astrology_rank") or index)
        display_rank = int(item.get("display_rank") or index)
        ranking.append(
            {
                "rank": astrology_rank,
                "astrology_rank": astrology_rank,
                "display_rank": display_rank,
                "selection_order": display_rank,
                "candidate_id": target.get("candidate_id"),
                "label": target.get("label"),
                "query": target.get("query"),
                "latitude": target.get("latitude"),
                "longitude": target.get("longitude"),
                "coordinate_source": target.get("coordinate_source"),
                "score": location_score.get("score"),
                "raw_score": location_score.get("raw_score"),
                "evidence_strength": location_score.get("evidence_strength"),
                "interpretation_status": location_score.get("interpretation_status"),
                "ranking_eligible": location_score.get("ranking_eligible", True),
                "uncertainty": location_score.get("uncertainty") or {},
                "rank_stability": location_score.get("rank_stability") or {},
                "population": atlas_city.get("population"),
                "country_name": atlas_city.get("country_name"),
                "lead_line": (((item.get("natal") or {}).get("reading") or {}).get("lead_line") or {}).get("label"),
                "top_supports": (location_score.get("top_supports") or [])[:2],
                "top_cautions": (location_score.get("top_cautions") or [])[:2],
                "relocation_available": not bool((item.get("relocation") or {}).get("relocation_unavailable")),
                "geographic_group": item.get("geographic_group") or {},
                "ranking_basis": item.get("ranking_basis") or dict(ASTROLOGY_RANKING_BASIS),
                "practical_context": item.get("practical_context") or dict(PRACTICAL_CONTEXT_POLICY),
                "suitability_assessed": False,
            }
        )
    return ranking


def resolve_goal_shortlist_plan(
    goal_id: str,
    *,
    relocation_limit: int,
    candidate_count: int,
) -> Dict[str, Any]:
    model = get_goal_model(goal_id)
    configured_strategy = str(model.get("atlas_shortlist_strategy") or "").strip().lower()
    strategy = configured_strategy or DEFAULT_SHORTLIST_STRATEGY
    evaluation_strategy = str(model.get("evaluation_strategy") or "").strip().lower()
    has_relocation_components = any(
        str(component.get("kind") or "").strip().lower() in {"relocation", "modifier", "constraint"}
        for component in (model.get("score_components") or [])
        if isinstance(component, dict)
    )
    if not configured_strategy and (
        has_relocation_components or evaluation_strategy in RELOCATION_AWARE_EVALUATION_STRATEGIES
    ):
        strategy = RELOCATION_PREPASS_SHORTLIST_STRATEGY
    if strategy not in {DEFAULT_SHORTLIST_STRATEGY, RELOCATION_PREPASS_SHORTLIST_STRATEGY}:
        strategy = DEFAULT_SHORTLIST_STRATEGY

    prepass_limit = max(1, int(relocation_limit))
    if strategy == RELOCATION_PREPASS_SHORTLIST_STRATEGY:
        # A line-only cutoff cannot bound relocation-dependent components.  The
        # API supplies a lightweight exact-house resolver, so every candidate
        # participates in this dependency-aware prepass.
        prepass_limit = int(candidate_count)

    return {
        "strategy": strategy,
        "prepass_limit": max(0, int(prepass_limit)),
    }


def _candidate_payload_from_scored_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **(item.get("atlas_city") or {}),
        **(item.get("target") or {}),
    }


def _uncertainty_candidate_key(item: Dict[str, Any]) -> str:
    target = item.get("target") or {}
    candidate_id = target.get("candidate_id")
    if candidate_id not in (None, ""):
        return str(candidate_id)
    try:
        return (
            f"coordinate:{float(target.get('latitude')):.6f}:"
            f"{float(target.get('longitude')):.6f}"
        )
    except (TypeError, ValueError):
        return str(target.get("label") or target.get("query") or "")


def build_bounded_stability_evaluation_pool(
    rows: Sequence[Dict[str, Any]],
    *,
    required_rows: Sequence[Dict[str, Any]],
    requested_limit: int,
    time_sample_count: int,
    max_evaluations: int = MAX_ATLAS_STABILITY_EVALUATIONS,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Bound full birth-time recalculations while retaining displayed results."""

    sample_count = max(0, int(time_sample_count))
    evaluation_cap = max(1, int(max_evaluations))
    requested_count = max(1, int(requested_limit))
    candidate_cap = int(MAX_ATLAS_STABILITY_CANDIDATES)
    if sample_count:
        candidate_cap = min(
            candidate_cap,
            max(requested_count, evaluation_cap // sample_count),
        )

    pool = list(
        bounded_stability_pool(
            rows,
            requested_limit=requested_count,
            cap=candidate_cap,
        )
    )
    rows_by_key = {
        _uncertainty_candidate_key(item): item
        for item in rows
    }
    row_order = {
        _uncertainty_candidate_key(item): index
        for index, item in enumerate(rows)
    }
    required_key_order = list(dict.fromkeys(
        _uncertainty_candidate_key(item)
        for item in required_rows
    ))
    required_keys = set(required_key_order)
    pool_keys = {
        _uncertainty_candidate_key(item)
        for item in pool
    }

    for required_key in required_key_order:
        if required_key in pool_keys:
            continue
        original = rows_by_key.get(required_key)
        if original is None:
            continue
        replace_index = next(
            (
                index
                for index in range(len(pool) - 1, -1, -1)
                if _uncertainty_candidate_key(pool[index]) not in required_keys
            ),
            None,
        )
        if replace_index is not None:
            pool_keys.discard(_uncertainty_candidate_key(pool[replace_index]))
            pool[replace_index] = original
        elif len(pool) < candidate_cap:
            pool.append(original)
        pool_keys.add(required_key)

    pool.sort(
        key=lambda item: row_order.get(
            _uncertainty_candidate_key(item),
            len(row_order),
        )
    )
    planned_evaluations = len(pool) * sample_count
    return pool, {
        "method": "bounded_candidate_by_time_sample_budget_v1",
        "candidate_cap": candidate_cap,
        "candidate_count": len(pool),
        "scope_candidate_count": len(rows),
        "time_sample_count": sample_count,
        "planned_full_recalculations": planned_evaluations,
        "max_full_recalculations": evaluation_cap,
        "within_evaluation_cap": planned_evaluations <= evaluation_cap,
        "bounded_scope": len(pool) < len(rows),
        "required_displayed_candidates_preserved": required_keys.issubset(pool_keys),
    }


def _ranking_eligible_relocation_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(chart_data, dict):
        return {}
    out = dict(chart_data)
    planets = chart_data.get("planets")
    if isinstance(planets, dict):
        out["planets"] = {
            name: payload
            for name, payload in planets.items()
            if not isinstance(payload, dict)
            or (payload.get("calculation_provenance") or {}).get("ranking_eligible", True)
        }
    elif isinstance(planets, list):
        out["planets"] = [
            payload
            for payload in planets
            if not isinstance(payload, dict)
            or (payload.get("calculation_provenance") or {}).get("ranking_eligible", True)
        ]
    return out


def _resolve_candidate_relocation(
    item: Dict[str, Any],
    resolver: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    try:
        bundle = resolver(item) or {}
    except Exception as exc:
        return None, {
            "available": False,
            "relocation_unavailable": True,
            "error": {
                "code": "relocation_calculation_failed",
                "message": str(exc) or "Relocation calculation failed for this candidate.",
            },
            "warnings": [
                "The candidate was retained with line-only evidence; no alternate house system was substituted."
            ],
        }
    if bundle.get("relocation_unavailable") or bundle.get("available") is False:
        return None, {
            "available": False,
            "relocation_unavailable": True,
            "error": bundle.get("error"),
            "provenance": bundle.get("provenance") or {},
            "warnings": bundle.get("warnings") or [],
        }
    chart_data = _ranking_eligible_relocation_chart(bundle.get("chart_data") or {})
    return extract_relocation_features(chart_data), {
        "available": True,
        "relocation_unavailable": False,
        "provenance": bundle.get("provenance") or {},
        "warnings": bundle.get("warnings") or [],
    }


def _score_candidate_with_relocation(
    city: Dict[str, Any],
    *,
    goal_id: str,
    natal_lines: Sequence[Dict[str, Any]],
    transit_lines: Optional[Sequence[Dict[str, Any]]],
    relocation_features: Optional[Dict[str, Any]],
    relocation_status: Optional[Dict[str, Any]],
    relocation_required: bool,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "goal_id": goal_id,
        "natal_lines": natal_lines,
        "transit_lines": transit_lines,
        "relocation_features": relocation_features,
    }
    if relocation_status and relocation_status.get("relocation_unavailable"):
        kwargs["relocation_status"] = relocation_status
    result = _score_candidate(city, **kwargs)
    if relocation_required and relocation_status and relocation_status.get("relocation_unavailable"):
        location_score = result.get("location_score")
        if isinstance(location_score, dict):
            location_score["ranking_eligible"] = False
            reasons = list(location_score.get("ineligible_reasons") or [])
            if "relocation_unavailable" not in reasons:
                reasons.append("relocation_unavailable")
            location_score["ineligible_reasons"] = reasons
    if relocation_status and relocation_status.get("available") and isinstance(result.get("relocation"), dict):
        result["relocation"]["provenance"] = relocation_status.get("provenance") or {}
        result["relocation"]["warnings"] = relocation_status.get("warnings") or []
    return result


def rank_candidate_pool_for_goal(
    *,
    goal_id: str,
    candidates: Sequence[Dict[str, Any]],
    natal_lines: Sequence[Dict[str, Any]],
    transit_lines: Optional[Sequence[Dict[str, Any]]] = None,
    limit: int = DEFAULT_ATLAS_LIMIT,
    relocation_limit: Optional[int] = None,
    limit_cap: Optional[int] = 20,
    relocation_limit_cap: Optional[int] = 30,
    relocation_bundle_resolver: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    should_continue: Optional[Callable[[], None]] = None,
    include_debug_ranking: bool = False,
    birth_time_sampling_plan: Optional[Dict[str, Any]] = None,
    birth_time_samples: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    limit = max(1, int(limit or DEFAULT_ATLAS_LIMIT))
    if limit_cap is not None:
        limit = min(limit, int(limit_cap))
    relocation_limit = max(limit, int(relocation_limit or DEFAULT_RELOCATION_LIMIT))
    if relocation_limit_cap is not None:
        relocation_limit = min(relocation_limit, int(relocation_limit_cap))
    initial_total = len(candidates)
    shortlist_plan = resolve_goal_shortlist_plan(
        goal_id,
        relocation_limit=relocation_limit,
        candidate_count=initial_total,
    )
    score_polarity = get_goal_score_polarity(goal_id)
    use_direct_relocation_prepass = bool(
        shortlist_plan["strategy"] == RELOCATION_PREPASS_SHORTLIST_STRATEGY
        and relocation_bundle_resolver is not None
        and shortlist_plan["prepass_limit"] >= initial_total
        and not include_debug_ranking
    )

    initial_results: List[Dict[str, Any]] = []
    if initial_total == 0:
        _emit_progress(
            progress_callback,
            stage="score_candidates",
            percent=0.65,
            message="No atlas candidates matched the current search",
            done=0,
            total=0,
            candidate_count=0,
        )
    elif use_direct_relocation_prepass:
        for city in candidates:
            initial_results.append(
                {
                    **_candidate_identity_payload(city),
                    "natal": {"reading": {}},
                    "location_score": {},
                }
            )
        _emit_progress(
            progress_callback,
            stage="prepare_candidates",
            percent=0.65,
            message="Candidate identities prepared for exact relocation-aware scoring",
            done=initial_total,
            total=initial_total,
            candidate_count=initial_total,
        )
    else:
        initial_step = max(1, initial_total // 24)
        for index, city in enumerate(candidates, start=1):
            _check_should_continue(should_continue)
            initial_results.append(
                _score_candidate(city, goal_id=goal_id, natal_lines=natal_lines, transit_lines=transit_lines)
            )
            if index == initial_total or index % initial_step == 0:
                progress = 0.16 + (0.49 * (index / initial_total))
                _emit_progress(
                    progress_callback,
                    stage="score_candidates",
                    percent=progress,
                    message="Scoring atlas candidates",
                    done=index,
                    total=initial_total,
                    candidate_count=initial_total,
                )
    if not use_direct_relocation_prepass:
        initial_results.sort(key=lambda item: _scored_candidate_sort_key(item, score_polarity=score_polarity))

    prepass_candidates = initial_results[: shortlist_plan["prepass_limit"]]
    relocation_prepass_results: List[Dict[str, Any]] = []
    final_results_source: List[Dict[str, Any]] = []

    if (
        shortlist_plan["strategy"] == RELOCATION_PREPASS_SHORTLIST_STRATEGY
        and relocation_bundle_resolver is not None
        and prepass_candidates
    ):
        _emit_progress(
            progress_callback,
            stage="relocation_prepass",
            percent=0.7,
            message="Running relocation-aware prepass before the final shortlist",
            done=0,
            total=len(prepass_candidates),
            prepass_count=len(prepass_candidates),
            candidate_count=initial_total,
        )
        prepass_total = len(prepass_candidates)
        prepass_step = max(1, prepass_total // 16)
        for index, item in enumerate(prepass_candidates, start=1):
            _check_should_continue(should_continue)
            city = _candidate_payload_from_scored_item(item)
            relocation_features, relocation_status = _resolve_candidate_relocation(
                item,
                relocation_bundle_resolver,
            )
            relocation_prepass_results.append(
                _score_candidate_with_relocation(
                    city,
                    goal_id=goal_id,
                    natal_lines=natal_lines,
                    transit_lines=transit_lines,
                    relocation_features=relocation_features,
                    relocation_status=relocation_status,
                    relocation_required=True,
                )
            )
            if index == prepass_total or index % prepass_step == 0:
                progress = 0.7 + (0.25 * (index / prepass_total))
                _emit_progress(
                    progress_callback,
                    stage="relocation_prepass",
                    percent=progress,
                    message="Scoring relocated charts for the expanded prepass",
                    done=index,
                    total=prepass_total,
                    prepass_count=prepass_total,
                )
        relocation_prepass_results.sort(key=lambda item: _scored_candidate_sort_key(item, score_polarity=score_polarity))
        shortlisted = relocation_prepass_results[:relocation_limit]
        final_results_source = relocation_prepass_results
    else:
        shortlisted = prepass_candidates[:relocation_limit]
        _emit_progress(
            progress_callback,
            stage="shortlist",
            percent=0.7,
            message="Shortlisting strongest cities for relocation scoring",
            done=len(shortlisted),
            total=len(initial_results),
            shortlisted_count=len(shortlisted),
            candidate_count=initial_total,
        )
        shortlist_total = len(shortlisted)
        shortlist_step = max(1, shortlist_total // 16) if shortlist_total else 1
        for index, item in enumerate(shortlisted, start=1):
            _check_should_continue(should_continue)
            city = _candidate_payload_from_scored_item(item)
            relocation_features = None
            relocation_status = None
            if relocation_bundle_resolver is not None:
                relocation_features, relocation_status = _resolve_candidate_relocation(
                    item,
                    relocation_bundle_resolver,
                )
            final_results_source.append(
                _score_candidate_with_relocation(
                    city,
                    goal_id=goal_id,
                    natal_lines=natal_lines,
                    transit_lines=transit_lines,
                    relocation_features=relocation_features,
                    relocation_status=relocation_status,
                    relocation_required=False,
                )
            )
            if shortlist_total and (index == shortlist_total or index % shortlist_step == 0):
                progress = 0.7 + (0.25 * (index / shortlist_total))
                _emit_progress(
                    progress_callback,
                    stage="relocation_scoring",
                    percent=progress,
                    message="Scoring relocated charts for shortlisted cities",
                    done=index,
                    total=shortlist_total,
                    shortlisted_count=shortlist_total,
                )
        final_results_source.sort(key=lambda item: _scored_candidate_sort_key(item, score_polarity=score_polarity))

    _check_should_continue(should_continue)
    viable_results = [
        item
        for item in final_results_source
        if _passes_signal_floor(item, score_polarity=score_polarity)
    ]

    provisional_results, _ = select_geographically_diverse_results(
        viable_results,
        limit=limit,
    )
    prepared_time_samples: List[Dict[str, Any]] = []
    for sample in birth_time_samples or []:
        if not isinstance(sample, dict):
            continue
        sample_id = str(sample.get("id") or "").strip()
        sample_lines = sample.get("natal_lines")
        if isinstance(sample_lines, dict):
            sample_lines = sample_lines.get("lines") or []
        if not sample_id or not isinstance(sample_lines, (list, tuple)):
            continue
        prepared_time_samples.append(
            {
                **sample,
                "id": sample_id,
                "natal_lines": sample_lines,
            }
        )

    stability_pool, stability_evaluation_policy = build_bounded_stability_evaluation_pool(
        viable_results,
        required_rows=provisional_results,
        requested_limit=limit,
        time_sample_count=len(prepared_time_samples),
    )

    sample_rows_by_candidate: Dict[str, List[Dict[str, Any]]] = {}
    evaluated_time_samples: List[Dict[str, Any]] = []
    planned_stability_evaluations = int(
        stability_evaluation_policy.get("planned_full_recalculations") or 0
    )
    completed_stability_evaluations = 0
    stability_progress_step = max(1, planned_stability_evaluations // 16)
    _emit_progress(
        progress_callback,
        stage="stability",
        percent=0.95,
        message=(
            "Recomputing bounded birth-time stability scenarios"
            if planned_stability_evaluations
            else "Evaluating cross-location rank stability"
        ),
        done=0,
        total=planned_stability_evaluations,
        stability_candidate_count=len(stability_pool),
        stability_sample_count=len(prepared_time_samples),
        max_full_recalculations=MAX_ATLAS_STABILITY_EVALUATIONS,
    )
    for sample in prepared_time_samples:
        sample_id = str(sample.get("id") or "")
        sample_lines = sample.get("natal_lines") or []
        sample_resolver = sample.get("relocation_bundle_resolver")
        _check_should_continue(should_continue)
        for base_item in stability_pool:
            _check_should_continue(should_continue)
            city = _candidate_payload_from_scored_item(base_item)
            relocation_features = None
            relocation_status = None
            if callable(sample_resolver):
                relocation_features, relocation_status = _resolve_candidate_relocation(
                    base_item,
                    sample_resolver,
                )
            sampled = _score_candidate_with_relocation(
                city,
                goal_id=goal_id,
                natal_lines=sample_lines,
                transit_lines=transit_lines,
                relocation_features=relocation_features,
                relocation_status=relocation_status,
                relocation_required=bool(
                    shortlist_plan["strategy"] == RELOCATION_PREPASS_SHORTLIST_STRATEGY
                    and callable(sample_resolver)
                ),
            )
            candidate_id = _uncertainty_candidate_key(base_item)
            sampled_reading = ((sampled.get("natal") or {}).get("reading") or {})
            lead_line = sampled_reading.get("lead_line") or {}
            sample_rows_by_candidate.setdefault(candidate_id, []).append(
                {
                    "id": sample_id,
                    "position": sample.get("position"),
                    "offset_minutes": sample.get("offset_minutes"),
                    "timestamp": sample.get("timestamp"),
                    "evaluation": sampled.get("location_score") or {},
                    "lead_line": lead_line.get("label"),
                    "lead_line_distance_km": lead_line.get("distance_km"),
                    "relocation_available": not bool(
                        (sampled.get("relocation") or {}).get("relocation_unavailable")
                    ),
                }
            )
            completed_stability_evaluations += 1
            if (
                completed_stability_evaluations == planned_stability_evaluations
                or completed_stability_evaluations % stability_progress_step == 0
            ):
                progress = 0.95 + (
                    0.025
                    * completed_stability_evaluations
                    / max(1, planned_stability_evaluations)
                )
                _emit_progress(
                    progress_callback,
                    stage="stability",
                    percent=progress,
                    message="Recomputing bounded birth-time stability scenarios",
                    done=completed_stability_evaluations,
                    total=planned_stability_evaluations,
                    stability_candidate_count=len(stability_pool),
                    stability_sample_count=len(prepared_time_samples),
                    max_full_recalculations=MAX_ATLAS_STABILITY_EVALUATIONS,
                )
        evaluated_time_samples.append(
            {
                "id": sample_id,
                "position": sample.get("position"),
                "offset_minutes": sample.get("offset_minutes"),
                "timestamp": sample.get("timestamp"),
            }
        )

    effective_sampling_plan = dict(birth_time_sampling_plan or {})
    if evaluated_time_samples:
        effective_sampling_plan["status"] = (
            "evaluated"
            if effective_sampling_plan.get("coverage_complete", True)
            else "evaluated_partial"
        )
        effective_sampling_plan["samples"] = evaluated_time_samples
    effective_sampling_plan["stability_evaluation"] = dict(
        stability_evaluation_policy
    )
    for item in stability_pool:
        location_score = item.get("location_score")
        if not isinstance(location_score, dict):
            continue
        candidate_id = _uncertainty_candidate_key(item)
        item["location_score"] = attach_birth_time_sample_evaluations(
            location_score,
            sampling_plan=effective_sampling_plan,
            sample_evaluations=sample_rows_by_candidate.get(candidate_id) or [],
        )

    stability_summary = apply_cross_location_rank_stability(
        stability_pool,
        score_polarity=score_polarity,
        top_k=limit,
        scope_candidate_count=len(viable_results),
    )
    stability_summary["evaluation_policy"] = dict(stability_evaluation_policy)
    _emit_progress(
        progress_callback,
        stage="stability",
        percent=0.976,
        message="Rank stability evaluation complete",
        done=completed_stability_evaluations,
        total=planned_stability_evaluations,
        stability_candidate_count=len(stability_pool),
        stability_sample_count=len(prepared_time_samples),
        max_full_recalculations=MAX_ATLAS_STABILITY_EVALUATIONS,
    )
    final_results, geographic_diversity = select_geographically_diverse_results(
        viable_results,
        limit=limit,
    )

    _check_should_continue(should_continue)
    _emit_progress(
        progress_callback,
        stage="finalizing",
        percent=0.98,
        message="Finalizing goal-specific astrology ranking",
        done=len(final_results),
        total=len(viable_results),
        viable_count=len(viable_results),
    )

    ranking = _build_scored_candidate_ranking(final_results)

    _emit_progress(
        progress_callback,
        stage="ready",
        percent=1.0,
        message="Atlas astrology search complete",
        done=len(final_results),
        total=len(final_results),
        viable_count=len(viable_results),
    )

    result: Dict[str, Any] = {
        "candidate_count": len(candidates),
        "shortlist_strategy": shortlist_plan["strategy"],
        "relocation_prepass_count": len(prepass_candidates),
        "shortlisted_count": len(shortlisted),
        "viable_count": len(viable_results),
        "relocation_unavailable_count": sum(
            1
            for item in final_results_source
            if (item.get("relocation") or {}).get("relocation_unavailable")
        ),
        "relocation_unavailable": [
            {
                "target": item.get("target") or {},
                "error": (item.get("relocation") or {}).get("error"),
                "warnings": (item.get("relocation") or {}).get("warnings") or [],
            }
            for item in final_results_source
            if (item.get("relocation") or {}).get("relocation_unavailable")
        ],
        "signal_floor_raw_score": MIN_ATLAS_RAW_SCORE,
        "score_polarity": score_polarity,
        "ranking_mode": "goal_specific_astrology",
        "ranking_basis": dict(ASTROLOGY_RANKING_BASIS),
        "practical_context": dict(PRACTICAL_CONTEXT_POLICY),
        "goal_selection": dict(GOAL_SELECTION_POLICY),
        "geographic_diversity": geographic_diversity,
        "birth_time_sampling": effective_sampling_plan,
        "rank_stability": stability_summary,
        "results": final_results,
        "ranking": ranking,
    }
    if include_debug_ranking:
        result["debug"] = {
            "initial_ranking": _build_scored_candidate_ranking(initial_results),
            "relocation_prepass_ranking": _build_scored_candidate_ranking(relocation_prepass_results),
            "final_scored_ranking": _build_scored_candidate_ranking(final_results_source),
            "prepass_labels": [str((item.get("target") or {}).get("label") or "") for item in prepass_candidates],
            "shortlisted_labels": [str((item.get("target") or {}).get("label") or "") for item in shortlisted],
        }
    return result


def rank_atlas_cities_for_goal(
    *,
    goal_id: str,
    natal_lines: Sequence[Dict[str, Any]],
    transit_lines: Optional[Sequence[Dict[str, Any]]] = None,
    query: Optional[str] = None,
    country_code: Optional[str] = None,
    continent_code: Optional[str] = None,
    resolution: Optional[str] = None,
    limit: int = DEFAULT_ATLAS_LIMIT,
    relocation_limit: Optional[int] = None,
    relocation_bundle_resolver: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    should_continue: Optional[Callable[[], None]] = None,
    birth_time_sampling_plan: Optional[Dict[str, Any]] = None,
    birth_time_samples: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    resolution_settings = get_atlas_resolution_settings(resolution)
    resolution_id = str(resolution_settings.get("id") or DEFAULT_ATLAS_RESOLUTION)
    augment_live_query = bool(resolution_settings.get("augment_live_query")) and bool(query)
    live_limit = max(1, min(int(resolution_settings.get("live_limit") or 6), 10))
    limit = max(1, min(int(limit or DEFAULT_ATLAS_LIMIT), 20))
    relocation_limit = max(
        limit,
        min(int(relocation_limit or resolution_settings.get("relocation_limit") or DEFAULT_RELOCATION_LIMIT), 30),
    )

    _check_should_continue(should_continue)
    _emit_progress(
        progress_callback,
        stage="collect_candidates",
        percent=0.02,
        message="Collecting atlas candidates",
    )

    country_keyword_codes = (
        get_city_catalog_country_codes_for_alias(query)
        if query
        else ()
    )
    parsed_identity_query = (
        parse_city_catalog_identity_query(query)
        if query and not country_keyword_codes
        else None
    )
    use_exact_identity = bool(
        parsed_identity_query
        and parsed_identity_query.get("city_prefix_exact")
    )
    catalog_candidate_limit = max(
        1,
        int(resolution_settings.get("candidate_limit") or 1),
    )
    catalog_candidates_with_sentinel = search_city_catalog(
        query=(
            parsed_identity_query.get("city_query")
            if use_exact_identity
            else query
        ),
        country_code=country_code,
        continent_code=continent_code,
        limit=catalog_candidate_limit + 1,
        resolution=resolution_id,
    )
    catalog_pool_truncated = (
        len(catalog_candidates_with_sentinel) > catalog_candidate_limit
    )
    catalog_candidates = catalog_candidates_with_sentinel[:catalog_candidate_limit]
    country_norm = str(country_code or "").strip().upper()

    def _matches_requested_identity(city: Dict[str, Any]) -> bool:
        city_country_code = str(city.get("country_code") or "").strip().upper()
        if country_keyword_codes and city_country_code not in country_keyword_codes:
            return False
        if (
            use_exact_identity
            and not city_catalog_candidate_matches_identity(
                city,
                parsed_identity_query,
            )
        ):
            return False
        if (
            query
            and not country_keyword_codes
            and not use_exact_identity
            and not city_catalog_candidate_matches_keyword(city, query)
        ):
            return False
        if country_norm and city_country_code != country_norm:
            return False
        return True

    catalog_candidates = [
        city
        for city in catalog_candidates
        if _matches_requested_identity(city)
    ]
    _check_should_continue(should_continue)
    _emit_progress(
        progress_callback,
        stage="collect_candidates",
        percent=0.08 if augment_live_query else 0.12,
        message="Catalog candidates collected",
        done=len(catalog_candidates),
        total=len(catalog_candidates),
        catalog_candidate_count=len(catalog_candidates),
    )
    _check_should_continue(should_continue)
    live_candidates = search_live_location_candidates(query or "", limit=live_limit) if augment_live_query else []
    live_candidates = [
        city
        for city in live_candidates
        if _matches_requested_identity(city)
    ]
    _check_should_continue(should_continue)
    candidates = _merge_atlas_candidates(
        catalog_candidates,
        live_candidates,
        continent_code=continent_code,
    )
    _emit_progress(
        progress_callback,
        stage="collect_candidates",
        percent=0.16,
        message="Candidate pool ready",
        done=len(candidates),
        total=len(candidates),
        catalog_candidate_count=len(catalog_candidates),
        live_candidate_count=len(live_candidates),
        candidate_count=len(candidates),
    )
    ranking_result = rank_candidate_pool_for_goal(
        goal_id=goal_id,
        candidates=candidates,
        natal_lines=natal_lines,
        transit_lines=transit_lines,
        limit=limit,
        relocation_limit=relocation_limit,
        relocation_bundle_resolver=relocation_bundle_resolver,
        progress_callback=progress_callback,
        should_continue=should_continue,
        birth_time_sampling_plan=birth_time_sampling_plan,
        birth_time_samples=birth_time_samples,
    )

    return {
        "query": {
            "text": query or "",
            "country_code": (country_code or "").upper(),
            "continent_code": (continent_code or "").upper(),
            "resolution": resolution_id,
        },
        "resolution": resolution_settings,
        "candidate_pool_policy": {
            "bounded": True,
            "candidate_limit": catalog_candidate_limit,
            "minimum_population": int(resolution_settings.get("min_population") or 0),
            "population_floor_applies_to": (
                resolution_settings.get("population_floor_applies_to")
                or "cities_other_than_capitals_and_first_level_admin_centers"
            ),
            "population_floor_exceptions": (
                resolution_settings.get("population_floor_exceptions")
                or ["PPLC", "PPLA"]
            ),
            "population_used_for_ranking": False,
            "ranking_tie_breaker": "stable_label_then_candidate_id",
            "mandatory_feature_codes": ["PPLC", "PPLA"],
            "mandatory_candidates_preserved": True,
            "lower_level_fill_order": "population_descending",
            "truncated": catalog_pool_truncated,
            "eligible_count_lower_bound": len(catalog_candidates_with_sentinel),
        },
        "catalog_candidate_count": len(catalog_candidates),
        "live_candidate_count": len(live_candidates),
        "used_live_augmentation": bool(live_candidates),
        **ranking_result,
    }
