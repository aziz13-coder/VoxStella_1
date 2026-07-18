# -*- coding: utf-8 -*-
"""
Asteroid helpers for Astro Clock dashboard tiles.

This module exposes the dashboard asteroid set by default. The Points engine
can opt into additional symbolic-point dependencies without changing the
Asteroids tile surface.
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from swisseph_state import swisseph_lock

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

POINT_DEPENDENCY_BODIES: List[Dict[str, Any]] = [
    {"name": "Eros", "number": 433, "tier": "point_dependency", "galaxy_body_id": 15, "source": "asteroid"},
    {"name": "Lilith", "tier": "point_dependency", "galaxy_body_id": 18, "source": "swisseph", "point_id": "MEAN_APOG"},
    {"name": "Selena", "number": 17, "tier": "point_dependency", "galaxy_body_id": 19, "source": "fictitious"},
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
    raw: List[Optional[str]] = [
        str(here / "ephemeris" / "sweph"),
        str(here.parent / "backend" / "ephemeris" / "sweph"),
    ]

    if packaged_root:
        pyinstaller_root = Path(packaged_root).resolve()
        raw.extend(
            [
                str(pyinstaller_root / "ephemeris" / "sweph"),
                str(pyinstaller_root.parent / "ephemeris" / "sweph"),
            ]
        )

    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).resolve().parent
        raw.extend(
            [
                str(executable_root / "ephemeris" / "sweph"),
                str(executable_root / "_internal" / "ephemeris" / "sweph"),
                str(executable_root.parent.parent / "ephemeris" / "sweph"),
            ]
        )

    backend_dir = os.environ.get("HORARY_BACKEND_DIR")
    if backend_dir:
        runtime_root = Path(backend_dir).resolve()
        raw.extend(
            [
                str(runtime_root / "ephemeris" / "sweph"),
                str(runtime_root / "_internal" / "ephemeris" / "sweph"),
                str(runtime_root.parent.parent / "ephemeris" / "sweph"),
            ]
        )

    raw.extend(
        [
            os.environ.get("VOX_STELLA_SWISSEPH_PATH"),
            os.environ.get("SWISSEPH_PATH"),
            r"C:\Program Files (x86)\Galaxy\SwisEph",
        ]
    )

    paths: List[str] = []
    seen = set()
    for path in raw:
        if not isinstance(path, str) or not path.strip():
            continue
        normalized = path.strip()
        key = os.path.normcase(os.path.normpath(normalized))
        if key in seen:
            continue
        seen.add(key)
        paths.append(normalized)
    return paths


def _resolve_ephemeris_path() -> Optional[str]:
    for path in _candidate_ephemeris_paths():
        if os.path.isdir(path):
            return path
    return None


def _existing_ephemeris_paths() -> List[Optional[str]]:
    paths = [path for path in _candidate_ephemeris_paths() if os.path.isdir(path)]
    return paths or [None]


def _body_point_id(body: Dict[str, Any]) -> int:
    source = str(body.get("source") or "asteroid").lower()
    if source == "swisseph":
        attr = str(body.get("point_id") or "").strip()
        point_id = getattr(swe, attr, None)
        if point_id is None:
            raise RuntimeError(f"Swiss Ephemeris point {attr or '<missing>'} is unavailable.")
        return int(point_id)
    if source == "fictitious":
        offset = getattr(swe, "FICT_OFFSET", None)
        if offset is None:
            raise RuntimeError("Swiss Ephemeris fictitious point support is unavailable.")
        return int(offset) + int(body["number"])
    return int(swe.AST_OFFSET) + int(body["number"])


def _compute_asteroid_items_for_current_path(
    jd_ut: float,
    flags: int,
    cusps: List[float],
    ascendant: Optional[float],
    bodies: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    items: List[Dict[str, Any]] = []
    missing: List[Dict[str, str]] = []

    for body in bodies:
        try:
            point_id = _body_point_id(body)
            position, _ = swe.calc_ut(jd_ut, point_id, flags)
            longitude = _wrap360(float(position[0]))
            latitude = float(position[1])
            speed = float(position[3])
            azimuth = (_wrap360(longitude - ascendant + 90.0) if ascendant is not None else None)
            items.append(
                {
                    "name": body["name"],
                    "number": body.get("number"),
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

    return items, missing


def compute_asteroid_positions(
    chart_data: Dict[str, Any],
    timestamp_iso: Optional[str],
    *,
    include_point_dependencies: bool = False,
) -> Dict[str, Any]:
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
        dt_utc = datetime.datetime.now(datetime.timezone.utc)

    jd_ut = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + (dt_utc.minute / 60.0) + (dt_utc.second / 3600.0),
        getattr(swe, "GREG_CAL", 1),
    )

    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
    ascendant = None
    if isinstance(cusps, list) and cusps:
        try:
            ascendant = float(cusps[0])
        except Exception:
            ascendant = None

    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    bodies = ASTEROID_BODIES + (POINT_DEPENDENCY_BODIES if include_point_dependencies else [])
    items: List[Dict[str, Any]] = []
    missing: List[Dict[str, str]] = []
    best_count = -1

    with swisseph_lock():
        for ephe_path in _existing_ephemeris_paths():
            try:
                swe.set_ephe_path(ephe_path or "")
                candidate_items, candidate_missing = _compute_asteroid_items_for_current_path(
                    jd_ut,
                    flags,
                    cusps,
                    ascendant,
                    bodies,
                )
            except Exception as exc:
                candidate_items = []
                candidate_missing = [{"name": body["name"], "reason": str(exc)} for body in bodies]
            finally:
                try:
                    swe.set_ephe_path("")
                except Exception:
                    pass
            if len(candidate_items) > best_count:
                items = candidate_items
                missing = candidate_missing
                best_count = len(candidate_items)
            if len(items) == len(bodies):
                break

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


__all__ = ["compute_asteroid_positions", "ASTEROID_BODIES", "POINT_DEPENDENCY_BODIES"]
