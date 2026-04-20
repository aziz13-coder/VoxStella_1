# -*- coding: utf-8 -*-
"""
Compute aspects between house cusps and planets (engine-agnostic).

Policy for cusp aspects:
- Tight fixed orb cap: 1.0 degrees for all aspects to cusps.
- No angle/luminary bonuses.
- Major aspects: Conjunction (0), Opposition (180), Square (90), Trine (120), Sextile (60).
- Applying/separating falls back to planet speed when no forward sample is provided.

This module consumes chart_data produced by the horary engine without importing
or mutating the engine. Callers may optionally supply a future chart projection
so phase classification can use sampled chart state instead of a speed-only
fallback.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _norm180(x: float) -> float:
    return ((float(x) + 180.0) % 360.0) - 180.0


def _absdiff_deg(a: float, b: float) -> float:
    d = abs((float(a) - float(b)) % 360.0)
    return min(d, 360.0 - d)


_ASPECTS = [
    (0.0, "Conjunction"),
    (180.0, "Opposition"),
    (90.0, "Square"),
    (120.0, "Trine"),
    (60.0, "Sextile"),
]

_HARD = {"Conjunction", "Opposition", "Square"}
_BASIC_RULES_CACHE: Optional[Dict[str, Any]] = None


def _dexter_to_cusp(planet_lon: float, cusp_lon: float) -> bool:
    """Return True if planet casts a dexter aspect to the cusp (earlier in zodiac)."""
    forward = ((float(cusp_lon) % 360.0) - (float(planet_lon) % 360.0)) % 360.0
    return forward <= 180.0


def _load_basic_rules() -> Dict[str, Any]:
    global _BASIC_RULES_CACHE
    if _BASIC_RULES_CACHE is not None:
        return _BASIC_RULES_CACHE
    paths = [
        os.path.join(os.path.dirname(__file__), "knowledge", "basic_analysis_rules.json"),
        os.path.join(os.path.dirname(__file__), "basic_analysis_rules.json"),
    ]
    data: Dict[str, Any] = {}
    for path in paths:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                break
        except Exception:
            continue
    _BASIC_RULES_CACHE = data
    return data


def _h_domain(house: Optional[int]) -> Optional[str]:
    try:
        if house is None:
            return None
        return str(_load_basic_rules().get("houses", {}).get(str(int(house)), {}).get("domain") or None)
    except Exception:
        return None


def _planet_list_from_chart(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    planets = chart_data.get("planets") or []
    out: List[Dict[str, Any]] = []
    if isinstance(planets, dict):
        for name, info in planets.items():
            if not isinstance(info, dict):
                continue
            item = dict(info)
            item.setdefault("planet", name)
            out.append(item)
    elif isinstance(planets, list):
        for item in planets:
            if isinstance(item, dict):
                out.append(item)
    return out


def _planet_items_from_chart(chart_data: Dict[str, Any], include_modern: bool) -> List[Dict[str, Any]]:
    planets = _planet_list_from_chart(chart_data)

    if include_modern:
        try:
            modern = chart_data.get("modern_planets")
            if not modern:
                try:
                    from modern_planets import compute_modern_planets  # type: ignore

                    tzinfo = chart_data.get("timezone_info") if isinstance(chart_data, dict) else {}
                    timestamp = None
                    if isinstance(tzinfo, dict):
                        timestamp = tzinfo.get("utc_time") or tzinfo.get("local_time")
                    modern = compute_modern_planets(chart_data, timestamp or "")
                except Exception:
                    modern = []
            if isinstance(modern, list):
                for item in modern:
                    if isinstance(item, dict):
                        planets.append(item)
        except Exception:
            pass

    out: List[Dict[str, Any]] = []
    for planet in planets:
        try:
            name = str(planet.get("planet") or "")
            if not name:
                continue
            longitude = float(planet.get("longitude", 0.0) or 0.0)
            speed = float(planet.get("speed", 0.0) or 0.0)
            try:
                house_raw = planet.get("house")
                house = int(house_raw) if house_raw is not None else None
            except Exception:
                house = None
            out.append(
                {
                    "planet": name,
                    "longitude": longitude,
                    "speed": speed,
                    "house": house,
                }
            )
        except Exception:
            continue
    return out


def _future_phase_state(
    chart_data: Optional[Dict[str, Any]],
    include_modern: bool,
) -> Optional[Dict[str, Any]]:
    if not isinstance(chart_data, dict):
        return None

    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
    if not isinstance(cusps, list):
        cusps = []

    future_cusps: List[Optional[float]] = []
    for item in cusps[:12]:
        try:
            future_cusps.append(float(item) if item is not None else None)
        except Exception:
            future_cusps.append(None)

    pitems = _planet_items_from_chart(chart_data, include_modern=include_modern)
    return {
        "cusps": future_cusps,
        "planets": {str(item.get("planet")): item for item in pitems},
    }


def compute_cusp_aspects(
    chart_data: Dict[str, Any],
    include_modern: bool = False,
    orb_deg: float = 1.0,
    *,
    timestamp_iso: Optional[str] = None,
    location: Optional[str] = None,
    timezone: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    dt_hours: float = 0.5,
    house_system_code: Optional[str] = None,
    future_chart_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Compute cusp-planet aspects with a fixed orb."""
    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
    if not isinstance(cusps, list) or len(cusps) < 12:
        cusps = [None] * 12

    try:
        logger.info(
            "[CUSP-ASPECTS] start: include_modern=%s, orb_deg=%.3f, cusps_present=%d",
            bool(include_modern),
            float(orb_deg),
            sum(1 for cusp in cusps[:12] if cusp is not None),
        )
    except Exception:
        pass

    pitems = _planet_items_from_chart(chart_data, include_modern=include_modern)

    try:
        logger.info(
            "[CUSP-ASPECTS] planets considered=%d [%s]",
            len(pitems),
            ", ".join(str(item.get("planet")) for item in pitems[:10]) + ("..." if len(pitems) > 10 else ""),
        )
    except Exception:
        pass

    sampled_future_cusps: Optional[List[Optional[float]]] = None
    sampled_future_planets: Optional[Dict[str, Dict[str, Any]]] = None
    future_state = _future_phase_state(future_chart_data, include_modern=include_modern)
    if future_state:
        sampled_cusps = future_state.get("cusps")
        if isinstance(sampled_cusps, list) and sampled_cusps:
            sampled_future_cusps = sampled_cusps
        sampled_planets = future_state.get("planets")
        if isinstance(sampled_planets, dict) and sampled_planets:
            sampled_future_planets = sampled_planets
    elif timestamp_iso:
        try:
            logger.info(
                "[CUSP-ASPECTS] no future chart supplied; using speed fallback for phase classification "
                "(location=%s, timezone=%s, house_system=%s, dt_hours=%.3f, latitude=%s, longitude=%s)",
                location,
                timezone,
                house_system_code or (chart_data.get("house_system_code") if isinstance(chart_data, dict) else None),
                float(dt_hours or 0.5),
                latitude,
                longitude,
            )
        except Exception:
            pass

    results: Dict[str, List[Dict[str, Any]]] = {}
    for cusp_index in range(12):
        key = f"H{cusp_index + 1}"
        try:
            cusp_raw = cusps[cusp_index]
            cusp_lon = float(cusp_raw) if cusp_raw is not None else None
        except Exception:
            cusp_lon = None
        if cusp_lon is None:
            results[key] = []
            continue

        hits: List[Dict[str, Any]] = []
        for item in pitems:
            planet_lon = float(item["longitude"])
            speed = float(item.get("speed", 0.0) or 0.0)
            origin_house = item.get("house") if isinstance(item, dict) else None
            for angle, aspect_name in _ASPECTS:
                separation = _absdiff_deg(planet_lon, cusp_lon)
                orb = abs(separation - angle)
                if orb > float(orb_deg) + 1e-6:
                    continue

                # Only compare against a sampled future chart when the caller
                # supplied a real forward snapshot. Otherwise fall back to the
                # planet-speed heuristic for applying/separating classification.
                use_sampled_future_state = (
                    sampled_future_cusps is not None
                    and sampled_future_planets is not None
                    and cusp_index < len(sampled_future_cusps)
                )

                if use_sampled_future_state:
                    try:
                        future_item = sampled_future_planets.get(str(item.get("planet")))
                        future_planet_lon = float((future_item or {}).get("longitude", planet_lon))
                        future_cusp_raw = sampled_future_cusps[cusp_index]
                        future_cusp_lon = float(future_cusp_raw) if future_cusp_raw is not None else cusp_lon
                        separation_now = abs(_norm180((planet_lon - cusp_lon) - angle))
                        separation_future = abs(_norm180((future_planet_lon - future_cusp_lon) - angle))
                        if separation_future < separation_now:
                            phase = "applying"
                        elif separation_future > separation_now:
                            phase = "separating"
                        else:
                            phase = "stationary"
                    except Exception:
                        diff = _norm180((planet_lon - cusp_lon) - angle)
                        if abs(speed) <= 1e-6:
                            phase = "stationary"
                        else:
                            phase = "applying" if (diff * speed) < 0 else "separating"
                else:
                    diff = _norm180((planet_lon - cusp_lon) - angle)
                    if abs(speed) <= 1e-6:
                        phase = "stationary"
                    else:
                        phase = "applying" if (diff * speed) < 0 else "separating"

                severity = "severe" if orb <= 0.25 else ("moderate" if orb <= 0.5 else "mild")
                category = "hard" if aspect_name in _HARD else "soft"
                band = "partile" if orb <= 0.5 else "tight"
                hit = {
                    "planet": item["planet"],
                    "aspect": aspect_name,
                    "angle": angle,
                    "orb": round(float(orb), 3),
                    "applying": phase == "applying",
                    "phase": phase,
                    "category": category,
                    "severity": severity,
                    "band": band,
                    "dexter": bool(_dexter_to_cusp(planet_lon, cusp_lon)),
                    "origin_house": origin_house,
                    "origin_domain": _h_domain(origin_house),
                    "cusp_longitude": cusp_lon,
                    "planet_longitude": planet_lon,
                }
                hits.append(hit)

        hits.sort(key=lambda hit: (hit["orb"], 0 if hit["category"] == "hard" else 1, hit["planet"]))
        results[key] = hits

    try:
        counts = {key: len(value or []) for key, value in results.items()}
        total = sum(counts.values())
        order = [f"H{n}" for n in range(1, 13)]
        summary = ", ".join(f"{key}:{counts.get(key, 0)}" for key in order)
        logger.info("[CUSP-ASPECTS] total_hits=%d; per-cusp: %s", int(total), summary)
    except Exception:
        pass

    return results
