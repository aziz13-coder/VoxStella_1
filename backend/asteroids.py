# -*- coding: utf-8 -*-
"""
Asteroid helpers for Astro Clock dashboard tiles.

This module currently exposes the four major asteroids plus Proserpina, which
the upcoming marriage beta workflow needs to inspect explicitly.
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None


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

ASTEROID_BODIES: List[Dict[str, Any]] = [
    {"name": "Ceres", "number": 1, "tier": "major"},
    {"name": "Pallas", "number": 2, "tier": "major"},
    {"name": "Juno", "number": 3, "tier": "major"},
    {"name": "Vesta", "number": 4, "tier": "major"},
    {"name": "Proserpina", "number": 26, "tier": "special", "galaxy_body_id": 17},
]

CARDINALS_16: List[str] = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]


def _wrap360(value: float) -> float:
    return float(value) % 360.0


def _sign_name(longitude: float) -> str:
    return SIGN_NAMES[int(_wrap360(longitude) // 30.0) % 12]


def _degree_in_sign(longitude: float) -> float:
    return _wrap360(longitude) % 30.0


def _in_arc(start: float, end: float, point: float) -> bool:
    start = _wrap360(start)
    end = _wrap360(end)
    point = _wrap360(point)
    if start <= end:
        return start <= point < end
    return point >= start or point < end


def _house_from_cusps(longitude: float, cusps: List[float]) -> Optional[int]:
    if not isinstance(cusps, list) or len(cusps) < 12:
        return None
    for index in range(12):
        if _in_arc(cusps[index], cusps[(index + 1) % 12], longitude):
            return index + 1
    return None


def _bearing_label(azimuth_deg: float) -> str:
    index = int(round((_wrap360(azimuth_deg) / 22.5))) % len(CARDINALS_16)
    return CARDINALS_16[index]


def _candidate_ephemeris_paths() -> List[str]:
    here = Path(__file__).resolve().parent
    packaged_root = getattr(sys, "_MEIPASS", None)
    raw = [
        str(here / "ephemeris" / "sweph"),
        str(here.parent / "backend" / "ephemeris" / "sweph"),
        str(Path(packaged_root).resolve() / "ephemeris" / "sweph") if packaged_root else None,
        os.environ.get("VOX_STELLA_SWISSEPH_PATH"),
        os.environ.get("SWISSEPH_PATH"),
        r"C:\Program Files (x86)\Galaxy\SwisEph",
    ]
    return [path for path in raw if isinstance(path, str) and path.strip()]


def _resolve_ephemeris_path() -> Optional[str]:
    for path in _candidate_ephemeris_paths():
        if os.path.isdir(path):
            return path
    return None


def compute_asteroid_positions(chart_data: Dict[str, Any], timestamp_iso: Optional[str]) -> Dict[str, Any]:
    if swe is None:
        return {
            "items": [],
            "status": "unavailable",
            "message": "Swiss Ephemeris is unavailable.",
        }

    try:
        dt_utc = datetime.datetime.fromisoformat(str(timestamp_iso or "").replace("Z", "+00:00")).astimezone(
            datetime.timezone.utc
        )
    except Exception:
        dt_utc = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    jd_ut = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + (dt_utc.minute / 60.0) + (dt_utc.second / 3600.0),
        getattr(swe, "GREG_CAL", 1),
    )

    ephe_path = _resolve_ephemeris_path()
    try:
        swe.set_ephe_path(ephe_path or "")
    except Exception:
        pass

    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
    ascendant = None
    if isinstance(cusps, list) and cusps:
        try:
            ascendant = float(cusps[0])
        except Exception:
            ascendant = None

    items: List[Dict[str, Any]] = []
    missing: List[Dict[str, str]] = []
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    for body in ASTEROID_BODIES:
        point_id = swe.AST_OFFSET + int(body["number"])
        try:
            position, _ = swe.calc_ut(jd_ut, point_id, flags)
            longitude = _wrap360(float(position[0]))
            latitude = float(position[1])
            speed = float(position[3])
            azimuth = (_wrap360(longitude - ascendant + 90.0) if ascendant is not None else None)
            items.append(
                {
                    "name": body["name"],
                    "number": body["number"],
                    "tier": body["tier"],
                    "galaxy_body_id": body.get("galaxy_body_id"),
                    "longitude": longitude,
                    "latitude": latitude,
                    "speed": speed,
                    "retrograde": bool(speed < 0),
                    "sign": _sign_name(longitude),
                    "degree_in_sign": _degree_in_sign(longitude),
                    "house": _house_from_cusps(longitude, cusps),
                    "azimuth_deg": round(azimuth, 2) if azimuth is not None else None,
                    "direction_label": _bearing_label(azimuth) if azimuth is not None else None,
                }
            )
        except Exception as exc:
            missing.append({"name": body["name"], "reason": str(exc)})

    if items and missing:
        status = "partial"
        message = "Some asteroid ephemeris files were unavailable."
    elif items:
        status = "ok"
        message = None
    else:
        status = "unavailable"
        message = "Asteroid ephemeris files are unavailable on this system."

    return {
        "items": items,
        "missing": missing,
        "status": status,
        "message": message,
        "ephemeris_available": bool(items),
    }


__all__ = ["compute_asteroid_positions", "ASTEROID_BODIES"]
