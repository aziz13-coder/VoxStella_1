# -*- coding: utf-8 -*-
"""
Arabic Parts/Lots helper — engine-agnostic.

Computes selected Lots from serialized chart data (ASC, planets, house cusps).
Does not import or modify the horary engine.
"""

from typing import Any, Dict, List, Optional


def norm(x: float) -> float:
    return ((x % 360.0) + 360.0) % 360.0


def lot(asc: float, a: float, b: float, is_day: bool) -> float:
    return norm((asc + a - b) if is_day else (asc + b - a))


SIGNS = [
    (0, "Aries", "Mars"), (30, "Taurus", "Venus"), (60, "Gemini", "Mercury"), (90, "Cancer", "Moon"),
    (120, "Leo", "Sun"), (150, "Virgo", "Mercury"), (180, "Libra", "Venus"), (210, "Scorpio", "Mars"),
    (240, "Sagittarius", "Jupiter"), (270, "Capricorn", "Saturn"), (300, "Aquarius", "Saturn"), (330, "Pisces", "Jupiter"),
]


def sign_of(lon: float) -> Dict[str, Any]:
    d = norm(lon)
    idx = int(d // 30) % 12
    start, name, ruler = SIGNS[idx]
    return {"name": name, "ruler": ruler, "degree_in_sign": d - start}


def _in_arc(start: float, end: float, point: float) -> bool:
    start = norm(start)
    end = norm(end)
    point = norm(point)
    if start <= end:
        return start <= point < end
    else:
        return point >= start or point < end


def house_from_cusps(lon: float, cusps: List[float]) -> int:
    if not cusps or len(cusps) < 12:
        return 1
    for i in range(12):
        if _in_arc(cusps[i], cusps[(i + 1) % 12], lon):
            return i + 1
    return 1


def _planet_map(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    planets = chart_data.get("planets") or []
    if isinstance(planets, list):
        for p in planets:
            try:
                name = p.get("planet") or p.get("name")
                if not name:
                    continue
                out[name] = p
            except Exception:
                continue
    elif isinstance(planets, dict):
        for name, info in planets.items():
            out[name] = info
    return out


def _lon(p: Dict[str, Any], fallback: float = 0.0) -> float:
    try:
        return float(p.get("longitude", fallback))
    except Exception:
        return fallback


def _is_day_from_sun_house(chart_data: Dict[str, Any], cusps: List[float]) -> Optional[bool]:
    # Day if Sun in houses 7..12 (above horizon), else night.
    planets = _planet_map(chart_data)
    sun = planets.get("Sun")
    if sun is None:
        return None
    try:
        house = int(sun.get("house"))
        return True if 7 <= house <= 12 else False
    except Exception:
        # fallback using declination/altitude would require lat/lon/time; omit here
        return None


def compute_arabic_parts(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Compute Arabic parts and return a dict keyed by part name.

    Output fields per part: lon, sign, degree_in_sign, house, ruler
    """
    planets = _planet_map(chart_data)
    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
    if not isinstance(cusps, list) or len(cusps) < 12:
        cusps = []
    try:
        asc = float(chart_data.get("ascendant")) if chart_data.get("ascendant") is not None else None
    except Exception:
        asc = None
    if asc is None and isinstance(cusps, list) and len(cusps) >= 1:
        asc = float(cusps[0])
    if asc is None:
        return {}

    # Determine day/night from Sun house when available
    is_day = _is_day_from_sun_house(chart_data, cusps)
    if is_day is None:
        # default to True (day) if unknown
        is_day = True

    def P(name: str) -> Optional[float]:
        p = planets.get(name)
        return _lon(p) if p is not None else None

    def H(n: int) -> Optional[float]:
        if isinstance(cusps, list) and len(cusps) >= n:
            return float(cusps[n - 1])
        return None

    sun = P("Sun")
    moon = P("Moon")
    mercury = P("Mercury")
    mars = P("Mars")
    saturn = P("Saturn")
    uranus = P("Uranus")
    neptune = P("Neptune")

    def wrap(name: str, L: Optional[float]) -> Optional[Dict[str, Any]]:
        if L is None:
            return None
        info = sign_of(L)
        house = house_from_cusps(L, cusps) if cusps else None
        return {
            "name": name,
            "lon": L,
            "sign": info["name"],
            "degree_in_sign": info["degree_in_sign"],
            "house": house,
            "ruler": info["ruler"],
        }

    result: Dict[str, Dict[str, Any]] = {}
    if moon is not None and sun is not None:
        result["fortune"] = wrap("Fortune", lot(asc, moon, sun, is_day))
        result["spirit"] = wrap("Spirit", lot(asc, sun, moon, is_day))
    if mars is not None and saturn is not None:
        result["peril"] = wrap("Peril", lot(asc, mars, saturn, is_day))
    if saturn is not None and moon is not None:
        result["deathA"] = wrap("Death A", lot(asc, saturn, moon, is_day))
    h8 = H(8)
    if h8 is not None and moon is not None:
        result["deathB"] = wrap("Death B", lot(asc, h8, moon, is_day))
    if saturn is not None and mercury is not None:
        result["poison_v1"] = wrap("Poison V1", lot(asc, saturn, mercury, is_day))
    if mars is not None and neptune is not None:
        result["poison_v2"] = wrap("Poison V2", lot(asc, mars, neptune, is_day))
    if uranus is not None and mercury is not None:
        result["plane_v1"] = wrap("Plane V1", lot(asc, uranus, mercury, is_day))
    h9 = H(9)
    if uranus is not None and h9 is not None:
        result["plane_v2"] = wrap("Plane V2", lot(asc, uranus, h9, is_day))

    # Remove None entries
    return {k: v for k, v in result.items() if v is not None}

