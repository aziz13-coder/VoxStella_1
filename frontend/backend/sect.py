# -*- coding: utf-8 -*-
"""
Sect (diurnal/nocturnal) helper — engine-agnostic.

Computes chart sect and per-planet sect comfort based only on serialized
chart_data (planets with sign/house/longitude and house cusps).

Rules implemented:
- Day chart if Sun is above horizon (houses 7–12), night otherwise.
- Diurnal planets: Sun, Jupiter, Saturn. Nocturnal: Moon, Venus, Mars.
- Mercury is "flex": day sect if morning star (west of Sun, oriental),
  night sect if evening star (east of Sun, occidental), based on ecliptic
  longitudes.
- Sign polarity: day prefers masculine signs (fire/air), night prefers
  feminine (earth/water).
- Hemisphere match: day prefers above horizon; night prefers below.
- Hayz: sect match + sign polarity match + hemisphere match.
"""

from typing import Any, Dict, List, Optional


MASC_SIGNS = {"Aries", "Gemini", "Leo", "Libra", "Sagittarius", "Aquarius"}
FEM_SIGNS = {"Taurus", "Cancer", "Virgo", "Scorpio", "Capricorn", "Pisces"}


def _norm360(x: float) -> float:
    x = x % 360.0
    return x if x >= 0 else x + 360.0


def _norm180(x: float) -> float:
    return ((x + 180.0) % 360.0) - 180.0


def _sign_from_lon(lon: Optional[float]) -> Optional[str]:
    if lon is None:
        return None
    L = _norm360(float(lon))
    idx = int(L // 30) % 12
    return [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ][idx]


def _house_from_cusps(lon: float, cusps: List[float]) -> Optional[int]:
    if not isinstance(cusps, list) or len(cusps) < 12:
        return None
    def in_arc(start: float, end: float, point: float) -> bool:
        start = _norm360(start); end = _norm360(end); point = _norm360(point)
        if start <= end:
            return start <= point < end
        else:
            return point >= start or point < end
    for i in range(12):
        s = float(cusps[i]); e = float(cusps[(i + 1) % 12])
        if in_arc(s, e, lon):
            return i + 1
    return None


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


def _get_num(x, default=None):
    try:
        return float(x)
    except Exception:
        return default


def _sun_house(chart_data: Dict[str, Any]) -> Optional[int]:
    planets = _planet_map(chart_data)
    sun = planets.get("Sun")
    if isinstance(sun, dict):
        try:
            h = int(sun.get("house"))
            if 1 <= h <= 12:
                return h
        except Exception:
            pass
        # fallback: compute house from cusps + lon
        lon = _get_num(sun.get("longitude"))
        cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
        if lon is not None and isinstance(cusps, list) and len(cusps) >= 12:
            return _house_from_cusps(lon, cusps)
    return None


def _planet_house(name: str, planets: Dict[str, Dict[str, Any]], cusps: List[float]) -> Optional[int]:
    p = planets.get(name)
    if not isinstance(p, dict):
        return None
    try:
        h = int(p.get("house"))
        if 1 <= h <= 12:
            return h
    except Exception:
        pass
    lon = _get_num(p.get("longitude"))
    if lon is not None and isinstance(cusps, list) and len(cusps) >= 12:
        return _house_from_cusps(lon, cusps)
    return None


def _planet_sign(name: str, planets: Dict[str, Dict[str, Any]]) -> Optional[str]:
    p = planets.get(name)
    if not isinstance(p, dict):
        return None
    sign = p.get("sign")
    if isinstance(sign, str) and sign:
        return sign
    lon = _get_num(p.get("longitude"))
    return _sign_from_lon(lon)


def _polarity(sign: Optional[str]) -> Optional[str]:
    if not sign:
        return None
    if sign in MASC_SIGNS:
        return "masculine"
    if sign in FEM_SIGNS:
        return "feminine"
    return None


def _mercury_phase(planets: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Return 'morning' if Mercury west of Sun (oriental), 'evening' if east (occidental)."""
    sun = planets.get("Sun")
    merc = planets.get("Mercury")
    if not isinstance(sun, dict) or not isinstance(merc, dict):
        return None
    s_lon = _get_num(sun.get("longitude"))
    m_lon = _get_num(merc.get("longitude"))
    if s_lon is None or m_lon is None:
        return None
    delta = _norm180(m_lon - s_lon)
    # m_lon west of Sun -> morning star (rises before Sun)
    return "morning" if delta < 0 else "evening"


def compute_sect_info(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute chart sect summary and per-planet comfort (in-sect, hayz).

    Returns a dict with keys:
      - chart_sect: 'diurnal'|'nocturnal'
      - sect_light: 'Sun'|'Moon'
      - malefic_of_sect: 'Saturn'|'Mars'
      - benefic_of_sect: 'Jupiter'|'Venus'
      - mercury_phase: 'morning'|'evening'|None
      - mercury_assigned_sect: 'diurnal'|'nocturnal'|None
      - planets: [ { planet, inherent_sect, assigned_sect, in_sect,
                     sign, sign_polarity, sign_polarity_match,
                     house, hemisphere, hemisphere_match, hayz } ]
      - in_sect_planets: [names]
      - out_of_sect_planets: [names]
      - hayz_planets: [names]
    """
    planets_map = _planet_map(chart_data)
    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []

    # Determine chart sect by Sun above/below horizon
    s_house = _sun_house(chart_data)
    if s_house is None:
        # Default to day if unknown
        chart_sect = "diurnal"
    else:
        chart_sect = "diurnal" if 7 <= int(s_house) <= 12 else "nocturnal"

    sect_light = "Sun" if chart_sect == "diurnal" else "Moon"
    malefic_of_sect = "Saturn" if chart_sect == "diurnal" else "Mars"
    benefic_of_sect = "Jupiter" if chart_sect == "diurnal" else "Venus"

    # Mercury assignment by phase
    phase = _mercury_phase(planets_map)
    mercury_assigned_sect = None
    if phase == "morning":
        mercury_assigned_sect = "diurnal"
    elif phase == "evening":
        mercury_assigned_sect = "nocturnal"

    diurnal_set = {"Sun", "Jupiter", "Saturn"}
    nocturnal_set = {"Moon", "Venus", "Mars"}

    def inherent_sect(name: str) -> Optional[str]:
        if name in diurnal_set:
            return "diurnal"
        if name in nocturnal_set:
            return "nocturnal"
        if name == "Mercury":
            return "flex"
        return None

    def assigned_sect(name: str) -> Optional[str]:
        if name == "Mercury":
            return mercury_assigned_sect
        return inherent_sect(name)

    # Per-planet comfort
    rows = []
    in_sect_names: List[str] = []
    out_sect_names: List[str] = []
    hayz_names: List[str] = []

    for name, pdata in planets_map.items():
        if name not in {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}:
            continue
        sign = _planet_sign(name, planets_map)
        pol = _polarity(sign)
        lon = _get_num(pdata.get("longitude"))
        h = None
        try:
            h = int(pdata.get("house")) if pdata.get("house") is not None else None
        except Exception:
            h = None
        if h is None and lon is not None:
            h = _house_from_cusps(lon, cusps) if isinstance(cusps, list) else None
        hemisphere = None
        if isinstance(h, int) and 1 <= h <= 12:
            hemisphere = "above" if 7 <= h <= 12 else "below"

        a_sect = assigned_sect(name)
        in_sect = (a_sect == chart_sect) if a_sect in ("diurnal", "nocturnal") else None

        # Preferred polarity and hemisphere by chart sect
        pref_pol = "masculine" if chart_sect == "diurnal" else "feminine"
        pol_match = (pol == pref_pol) if pol in ("masculine", "feminine") else None

        pref_hem = "above" if chart_sect == "diurnal" else "below"
        hem_match = (hemisphere == pref_hem) if hemisphere in ("above", "below") else None

        hayz = bool(in_sect and pol_match and hem_match)

        if in_sect is True:
            in_sect_names.append(name)
        elif in_sect is False:
            out_sect_names.append(name)
        if hayz:
            hayz_names.append(name)

        rows.append({
            "planet": name,
            "inherent_sect": inherent_sect(name),
            "assigned_sect": a_sect,
            "in_sect": in_sect,
            "sign": sign,
            "sign_polarity": pol,
            "sign_polarity_match": pol_match,
            "house": h,
            "hemisphere": hemisphere,
            "hemisphere_match": hem_match,
            "hayz": hayz,
        })

    return {
        "chart_sect": chart_sect,
        "sect_light": sect_light,
        "malefic_of_sect": malefic_of_sect,
        "benefic_of_sect": benefic_of_sect,
        "mercury_phase": phase,
        "mercury_assigned_sect": mercury_assigned_sect,
        "planets": rows,
        "in_sect_planets": in_sect_names,
        "out_of_sect_planets": out_sect_names,
        "hayz_planets": hayz_names,
    }

