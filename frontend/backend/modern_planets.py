# -*- coding: utf-8 -*-
"""
Modern planets helper (Uranus, Neptune, Pluto) — engine-agnostic.

Computes modern planet positions (longitude, speed, retrograde) using
Swiss Ephemeris for a given UTC timestamp, and assigns houses based on
provided house cusps from serialized chart_data. No engine imports.
"""

from typing import Any, Dict, List
import datetime

try:
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None


SIGNS = [
    (0, "Aries"), (30, "Taurus"), (60, "Gemini"), (90, "Cancer"), (120, "Leo"), (150, "Virgo"),
    (180, "Libra"), (210, "Scorpio"), (240, "Sagittarius"), (270, "Capricorn"), (300, "Aquarius"), (330, "Pisces"),
]


def _sign_name(lon: float) -> str:
    d = float(lon) % 360.0
    idx = int(d // 30) % 12
    return SIGNS[idx][1]


def _in_arc(start: float, end: float, point: float) -> bool:
    """Return True if point lies on arc from start to end moving CCW, handling wrap."""
    start = start % 360.0
    end = end % 360.0
    point = point % 360.0
    if start <= end:
        return start <= point < end
    else:
        return point >= start or point < end


def _house_from_cusps(lon: float, cusps: List[float]) -> int:
    if not cusps or len(cusps) < 12:
        return 1
    for i in range(12):
        if _in_arc(cusps[i], cusps[(i + 1) % 12], lon):
            return i + 1
    return 1


def compute_modern_planets(chart_data: Dict[str, Any], timestamp_iso: str) -> List[Dict[str, Any]]:
    """Compute Uranus, Neptune, Pluto positions at the given timestamp.

    Returns a list of planet dicts compatible with chart_data['planets'] entries.
    """
    if swe is None:
        return []
    try:
        dt = datetime.datetime.fromisoformat(timestamp_iso.replace('Z', '+00:00')).astimezone(datetime.timezone.utc)
    except Exception:
        dt = datetime.datetime.now(datetime.timezone.utc)
    jd_ut = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0 + dt.second / 3600.0)

    modern_ids = [("Uranus", getattr(swe, "URANUS", 7)), ("Neptune", getattr(swe, "NEPTUNE", 8)), ("Pluto", getattr(swe, "PLUTO", 9))]
    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
    out: List[Dict[str, Any]] = []
    for name, pid in modern_ids:
        try:
            pos, _ = swe.calc_ut(jd_ut, pid, swe.FLG_SWIEPH | swe.FLG_SPEED)
            lon = float(pos[0] % 360.0)
            lat = float(pos[1])
            speed = float(pos[3])
            house = _house_from_cusps(lon, cusps) if isinstance(cusps, list) else 1
            out.append({
                "planet": name,
                "longitude": lon,
                "latitude": lat,
                "speed": speed,
                "retrograde": bool(speed < 0),
                "house": house,
                "sign": _sign_name(lon),
                "degree_in_sign": lon % 30.0,
                # dignity placeholders to avoid impacting traditional scoring
                "dignity_score": 0,
                "essential_dignity": 0,
                "accidental_dignity": 0,
                "dignities": [],
            })
        except Exception:
            continue
    return out
