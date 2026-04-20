from __future__ import annotations

import copy
from typing import Any


def whole_sign_cusps(asc_lon: float) -> list[float]:
    return [float((asc_lon + 30.0 * idx) % 360.0) for idx in range(12)]


def clone_chart(chart: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(chart)


def set_planet(chart: dict[str, Any], planet: str, **fields: Any) -> dict[str, Any]:
    chart.setdefault("planets", {}).setdefault(planet, {}).update(fields)
    return chart


def set_aspects(chart: dict[str, Any], aspects: list[dict[str, Any]], *, key: str = "planetary_aspects_precise") -> dict[str, Any]:
    chart[key] = list(aspects)
    return chart


def set_moon_next_aspect(
    chart: dict[str, Any],
    *,
    planet: str,
    aspect: str,
    phase: str = "applying",
) -> dict[str, Any]:
    chart["moon_next_aspect"] = {"planet": planet, "aspect": aspect, "phase": phase}
    return chart


def set_whole_sign_asc(chart: dict[str, Any], asc_lon: float) -> dict[str, Any]:
    chart["house_cusps"] = whole_sign_cusps(asc_lon)
    return chart


def base_surgery_chart() -> dict[str, Any]:
    return {
        "house_cusps": whole_sign_cusps(0.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 45.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 13.5},
            "Mercury": {"planet": "Mercury", "longitude": 285.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 120.0, "sign": "Leo", "house": 5, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 295.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 70.0, "sign": "Gemini", "house": 3, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Trine", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def base_journey_chart() -> dict[str, Any]:
    return {
        "house_cusps": [180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0],
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 10.0, "sign": "Aries", "house": 7, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 100.0, "sign": "Cancer", "house": 10, "retrograde": False, "speed": 13.5},
            "Mercury": {"planet": "Mercury", "longitude": 20.0, "sign": "Aries", "house": 7, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 195.0, "sign": "Libra", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 250.0, "sign": "Sagittarius", "house": 3, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 260.0, "sign": "Sagittarius", "house": 3, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 70.0, "sign": "Gemini", "house": 9, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def base_battle_chart() -> dict[str, Any]:
    return {
        "house_cusps": [180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0],
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 4, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 100.0, "sign": "Cancer", "house": 10, "retrograde": False, "speed": 13.2},
            "Venus": {"planet": "Venus", "longitude": 105.0, "sign": "Cancer", "house": 10, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 15.0, "sign": "Aries", "house": 7, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 220.0, "sign": "Scorpio", "house": 2, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 300.0, "sign": "Aquarius", "house": 5, "retrograde": False, "speed": 0.1},
            "Mercury": {"planet": "Mercury", "longitude": 290.0, "sign": "Capricorn", "house": 4, "retrograde": False, "speed": 1.2},
            "North Node": {"planet": "North Node", "longitude": 120.0, "sign": "Leo", "house": 11, "retrograde": False},
        },
        "planetary_aspects_precise": [],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Trine", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def base_contract_chart() -> dict[str, Any]:
    return {
        "house_cusps": [210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0],
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 285.0, "sign": "Capricorn", "house": 3, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 105.0, "sign": "Cancer", "house": 9, "retrograde": False, "speed": 13.2},
            "Mercury": {"planet": "Mercury", "longitude": 75.0, "sign": "Gemini", "house": 8, "retrograde": False, "speed": 1.1},
            "Venus": {"planet": "Venus", "longitude": 45.0, "sign": "Taurus", "house": 7, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 175.0, "sign": "Virgo", "house": 11, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 350.0, "sign": "Pisces", "house": 5, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 275.0, "sign": "Capricorn", "house": 3, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [
            {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Trine", "phase": "applying"},
        ],
        "moon_next_aspect": {"planet": "Venus", "aspect": "Sextile", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def base_business_chart() -> dict[str, Any]:
    return {
        "house_cusps": whole_sign_cusps(0.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 45.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 13.5},
            "Mercury": {"planet": "Mercury", "longitude": 165.0, "sign": "Virgo", "house": 6, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 120.0, "sign": "Leo", "house": 5, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 350.0, "sign": "Pisces", "house": 12, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 315.0, "sign": "Aquarius", "house": 11, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def base_marriage_chart() -> dict[str, Any]:
    return {
        "house_cusps": [210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0],
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 285.0, "sign": "Capricorn", "house": 3, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 45.0, "sign": "Taurus", "house": 7, "retrograde": False, "speed": 13.2},
            "Mercury": {"planet": "Mercury", "longitude": 285.0, "sign": "Capricorn", "house": 3, "retrograde": False, "speed": 1.1},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Aries", "house": 6, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 165.0, "sign": "Virgo", "house": 11, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 350.0, "sign": "Pisces", "house": 5, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 245.0, "sign": "Sagittarius", "house": 2, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [
            {"planet1": "Venus", "planet2": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        ],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def base_legal_chart() -> dict[str, Any]:
    return {
        "house_cusps": whole_sign_cusps(60.0),  # Gemini rising, Pisces MC
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 260.0, "sign": "Sagittarius", "house": 7, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 195.0, "sign": "Libra", "house": 5, "retrograde": False, "speed": 13.3},
            "Mercury": {"planet": "Mercury", "longitude": 165.0, "sign": "Virgo", "house": 4, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 80.0, "sign": "Gemini", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 345.0, "sign": "Pisces", "house": 10, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 350.0, "sign": "Pisces", "house": 10, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 325.0, "sign": "Aquarius", "house": 9, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [
            {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Opposition", "phase": "separating"},
            {"planet1": "Mercury", "planet2": "Venus", "aspect": "Square", "phase": "separating"},
        ],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Trine", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def base_beautification_chart() -> dict[str, Any]:
    return {
        "house_cusps": whole_sign_cusps(30.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 35.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 85.0, "sign": "Cancer", "house": 4, "retrograde": False, "speed": 13.2},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Taurus", "house": 1, "retrograde": False, "speed": 1.0},
            "Jupiter": {"planet": "Jupiter", "longitude": 195.0, "sign": "Libra", "house": 7, "retrograde": False, "speed": 0.2},
            "Mars": {"planet": "Mars", "longitude": 300.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 0.6},
            "Saturn": {"planet": "Saturn", "longitude": 260.0, "sign": "Sagittarius", "house": 9, "retrograde": False, "speed": 0.1},
            "Mercury": {"planet": "Mercury", "longitude": 40.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 1.3},
        },
        "planetary_aspects": [
            {"planet1": "Moon", "planet2": "Venus", "aspect": "Trine", "phase": "applying"},
            {"planet1": "Venus", "planet2": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        ],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def base_viral_chart() -> dict[str, Any]:
    return {
        "house_cusps": whole_sign_cusps(300.0),  # Aquarius rising, Sagittarius 11th
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 20.0, "sign": "Aries", "house": 3, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 195.0, "sign": "Libra", "house": 9, "retrograde": False, "speed": 13.2},
            "Mercury": {"planet": "Mercury", "longitude": 75.0, "sign": "Gemini", "house": 5, "retrograde": False, "speed": 1.3},
            "Venus": {"planet": "Venus", "longitude": 315.0, "sign": "Aquarius", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 110.0, "sign": "Cancer", "house": 6, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 250.0, "sign": "Sagittarius", "house": 11, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 340.0, "sign": "Pisces", "house": 2, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects": [
            {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Opposition", "phase": "separating"},
        ],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Trine", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }
