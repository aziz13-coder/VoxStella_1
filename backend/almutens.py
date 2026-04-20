# -*- coding: utf-8 -*-
"""
Traditional almuten helpers for Astro Clock.

This module computes essential-dignity almutens for zodiacal points using the
classical seven planets and the standard 5/4/3/2/1 weighting:

- domicile
- exaltation
- triplicity
- term
- face

The helpers are intentionally engine-agnostic so the dashboard can expose the
same data the future election workflow will need.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from house_influence import EXALTATION, SIGN_RULER, TRIPLICITY
from sect import compute_sect_info


TRADITIONAL_PLANETS: List[str] = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
]

SIGN_NAMES: List[str] = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGN_ELEMENTS: Dict[str, str] = {
    "Aries": "Fire",
    "Leo": "Fire",
    "Sagittarius": "Fire",
    "Taurus": "Earth",
    "Virgo": "Earth",
    "Capricorn": "Earth",
    "Gemini": "Air",
    "Libra": "Air",
    "Aquarius": "Air",
    "Cancer": "Water",
    "Scorpio": "Water",
    "Pisces": "Water",
}

TERMS: Dict[str, List[tuple[str, float]]] = {
    "Aries": [("Jupiter", 6), ("Venus", 6), ("Mercury", 8), ("Mars", 5), ("Saturn", 5)],
    "Taurus": [("Venus", 8), ("Mercury", 6), ("Jupiter", 8), ("Saturn", 5), ("Mars", 3)],
    "Gemini": [("Mercury", 7), ("Jupiter", 6), ("Venus", 7), ("Mars", 4), ("Saturn", 6)],
    "Cancer": [("Mars", 7), ("Venus", 6), ("Mercury", 6), ("Jupiter", 7), ("Saturn", 4)],
    "Leo": [("Saturn", 6), ("Mercury", 5), ("Venus", 7), ("Jupiter", 6), ("Mars", 6)],
    "Virgo": [("Mercury", 7), ("Venus", 10), ("Jupiter", 4), ("Mars", 7), ("Saturn", 2)],
    "Libra": [("Saturn", 6), ("Mercury", 7), ("Jupiter", 7), ("Venus", 8), ("Mars", 2)],
    "Scorpio": [("Mars", 7), ("Venus", 4), ("Mercury", 8), ("Jupiter", 5), ("Saturn", 6)],
    "Sagittarius": [("Jupiter", 12), ("Venus", 5), ("Mercury", 4), ("Saturn", 9)],
    "Capricorn": [("Mercury", 7), ("Jupiter", 6), ("Venus", 7), ("Saturn", 5), ("Mars", 5)],
    "Aquarius": [("Mercury", 7), ("Venus", 6), ("Jupiter", 7), ("Mars", 5), ("Saturn", 5)],
    "Pisces": [("Venus", 12), ("Jupiter", 4), ("Mercury", 3), ("Mars", 9), ("Saturn", 2)],
}

FACES: Dict[str, List[tuple[str, float, float]]] = {
    "Aries": [("Mars", 0.0, 10.0), ("Sun", 10.0, 20.0), ("Venus", 20.0, 30.0)],
    "Taurus": [("Mercury", 0.0, 10.0), ("Moon", 10.0, 20.0), ("Saturn", 20.0, 30.0)],
    "Gemini": [("Jupiter", 0.0, 10.0), ("Mars", 10.0, 20.0), ("Sun", 20.0, 30.0)],
    "Cancer": [("Venus", 0.0, 10.0), ("Mercury", 10.0, 20.0), ("Moon", 20.0, 30.0)],
    "Leo": [("Saturn", 0.0, 10.0), ("Jupiter", 10.0, 20.0), ("Mars", 20.0, 30.0)],
    "Virgo": [("Sun", 0.0, 10.0), ("Venus", 10.0, 20.0), ("Mercury", 20.0, 30.0)],
    "Libra": [("Moon", 0.0, 10.0), ("Saturn", 10.0, 20.0), ("Jupiter", 20.0, 30.0)],
    "Scorpio": [("Mars", 0.0, 10.0), ("Sun", 10.0, 20.0), ("Venus", 20.0, 30.0)],
    "Sagittarius": [("Mercury", 0.0, 10.0), ("Moon", 10.0, 20.0), ("Saturn", 20.0, 30.0)],
    "Capricorn": [("Jupiter", 0.0, 10.0), ("Mars", 10.0, 20.0), ("Sun", 20.0, 30.0)],
    "Aquarius": [("Venus", 0.0, 10.0), ("Mercury", 10.0, 20.0), ("Moon", 20.0, 30.0)],
    "Pisces": [("Saturn", 0.0, 10.0), ("Jupiter", 10.0, 20.0), ("Mars", 20.0, 30.0)],
}

POINT_LABELS: Dict[str, str] = {
    "ascendant": "Ascendant",
    "midheaven": "Midheaven",
}

POINT_IDS: Dict[str, int] = {
    "ascendant": 24,
    "midheaven": 33,
    "house_11": 34,
    "house_12": 35,
}


def _wrap360(value: float) -> float:
    return float(value) % 360.0


def _sign_name(longitude: float) -> str:
    return SIGN_NAMES[int(_wrap360(longitude) // 30.0) % 12]


def _degree_in_sign(longitude: float) -> float:
    return _wrap360(longitude) % 30.0


def _triplicity_ruler(sign: str, is_day_chart: Optional[bool]) -> Optional[str]:
    element = SIGN_ELEMENTS.get(sign)
    if not element:
        return None
    rulers = TRIPLICITY.get(element)
    if not isinstance(rulers, tuple) or len(rulers) < 2:
        return None
    if is_day_chart is False:
        return rulers[1]
    return rulers[0]


def _ordinal(value: int) -> str:
    if 10 <= (value % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _term_ruler(sign: str, degree_in_sign: float) -> Optional[str]:
    sequence = TERMS.get(sign) or []
    edge = 0.0
    for ruler, length in sequence:
        edge += float(length)
        if degree_in_sign < edge:
            return ruler
    return sequence[-1][0] if sequence else None


def _face_ruler(sign: str, degree_in_sign: float) -> Optional[str]:
    sequence = FACES.get(sign) or []
    for ruler, start, end in sequence:
        if float(start) <= degree_in_sign < float(end):
            return ruler
    return sequence[-1][0] if sequence else None


def _chart_is_day(chart_data: Dict[str, Any]) -> Optional[bool]:
    try:
        sect = compute_sect_info(chart_data or {})
    except Exception:
        sect = None
    if isinstance(sect, dict):
        value = str(sect.get("chart_sect") or "").lower().strip()
        if value == "diurnal":
            return True
        if value == "nocturnal":
            return False
    return None


def compute_almuten_for_longitude(longitude: float, is_day_chart: Optional[bool]) -> Dict[str, Any]:
    sign = _sign_name(longitude)
    degree_in_sign = _degree_in_sign(longitude)
    triplicity_ruler = _triplicity_ruler(sign, is_day_chart)
    exaltation_ruler = EXALTATION.get(sign)
    domicile_ruler = SIGN_RULER.get(sign)
    term_ruler = _term_ruler(sign, degree_in_sign)
    face_ruler = _face_ruler(sign, degree_in_sign)

    candidates: List[Dict[str, Any]] = []
    for planet in TRADITIONAL_PLANETS:
        breakdown: Dict[str, int] = {}
        dignities: List[str] = []
        score = 0
        if domicile_ruler == planet:
            breakdown["domicile"] = 5
            dignities.append("domicile")
            score += 5
        if exaltation_ruler == planet:
            breakdown["exaltation"] = 4
            dignities.append("exaltation")
            score += 4
        if triplicity_ruler == planet:
            breakdown["triplicity"] = 3
            dignities.append("triplicity")
            score += 3
        if term_ruler == planet:
            breakdown["term"] = 2
            dignities.append("term")
            score += 2
        if face_ruler == planet:
            breakdown["face"] = 1
            dignities.append("face")
            score += 1
        candidates.append(
            {
                "planet": planet,
                "score": score,
                "dignities": dignities,
                "breakdown": breakdown,
            }
        )

    candidates.sort(
        key=lambda item: (
            -int(item.get("score") or 0),
            -int(item.get("breakdown", {}).get("domicile", 0)),
            -int(item.get("breakdown", {}).get("exaltation", 0)),
            -int(item.get("breakdown", {}).get("triplicity", 0)),
            -int(item.get("breakdown", {}).get("term", 0)),
            -int(item.get("breakdown", {}).get("face", 0)),
            item.get("planet") or "",
        )
    )

    leader = candidates[0] if candidates else None
    leader_score = int(leader.get("score") or 0) if leader else 0
    ties = [row for row in candidates if int(row.get("score") or 0) == leader_score]
    tied_with = [row.get("planet") for row in ties[1:]]

    return {
        "longitude": _wrap360(longitude),
        "sign": sign,
        "degree_in_sign": degree_in_sign,
        "leader": leader.get("planet") if leader else None,
        "leaders": [row.get("planet") for row in ties if row.get("planet")],
        "leader_score": leader_score,
        "leader_dignities": list(leader.get("dignities") or []) if leader else [],
        "leader_breakdown": dict(leader.get("breakdown") or {}) if leader else {},
        "tied_with": [name for name in tied_with if isinstance(name, str)],
        "candidates": candidates,
    }


def compute_chart_almutens(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    chart_data = chart_data or {}
    houses = chart_data.get("houses") or chart_data.get("house_cusps") or []
    is_day_chart = _chart_is_day(chart_data)
    sect_label = "Day" if is_day_chart is True else "Night" if is_day_chart is False else None

    point_values: Dict[str, float] = {}
    ascendant = chart_data.get("ascendant")
    if ascendant is None and isinstance(houses, list) and houses:
        ascendant = houses[0]
    if ascendant is not None:
        point_values["ascendant"] = float(ascendant)

    midheaven = chart_data.get("midheaven")
    if midheaven is None and isinstance(houses, list) and len(houses) >= 10:
        midheaven = houses[9]
    if midheaven is not None:
        point_values["midheaven"] = float(midheaven)

    if isinstance(houses, list):
        for index, cusp in enumerate(houses[:12], start=1):
            try:
                point_values[f"house_{index}"] = float(cusp)
            except Exception:
                continue

    points: Dict[str, Dict[str, Any]] = {}
    for key, longitude in point_values.items():
        point = compute_almuten_for_longitude(longitude, is_day_chart)
        point["key"] = key
        point["label"] = POINT_LABELS.get(key) or f"{_ordinal(int(key.split('_')[1]))} House"
        point["point_id"] = POINT_IDS.get(key)
        points[key] = point

    display_order = [
        "ascendant",
        "midheaven",
        "house_2",
        "house_7",
        "house_11",
        "house_12",
    ]
    items = [points[key] for key in display_order if key in points]

    return {
        "sect": sect_label,
        "points": points,
        "display_order": display_order,
        "items": items,
    }


__all__ = [
    "compute_almuten_for_longitude",
    "compute_chart_almutens",
]
