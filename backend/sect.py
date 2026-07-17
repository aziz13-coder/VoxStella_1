# -*- coding: utf-8 -*-
"""
Sect (diurnal/nocturnal) helper — engine-agnostic.

Computes chart sect and per-planet sect comfort from serialized chart data.

Rules implemented:
- Day chart if the Sun's altitude is at/above the horizon, night if below.
  Sun house is only a fallback when altitude cannot be established.
- Diurnal planets: Sun, Jupiter, Saturn. Nocturnal: Moon, Venus, Mars.
- Mercury is "flex": day sect if morning star (west of Sun, oriental),
  night sect if evening star (east of Sun, occidental), based on ecliptic
  longitudes.
- Sign polarity follows the planet's assigned sect: diurnal prefers
  masculine signs (fire/air), nocturnal prefers feminine signs (earth/water).
- Hemisphere match follows planetary sect in chart context: planets of the
  chart sect prefer above the horizon, contrary-sect planets below.
- Hayz: sect match + sign polarity match + hemisphere match.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from swisseph_state import swisseph as swe


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


def _chart_coords(chart_data: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    lat = _get_num(chart_data.get("latitude"))
    lon = _get_num(chart_data.get("longitude"))
    if lat is not None and lon is not None:
        return lat, lon

    tz_info = chart_data.get("timezone_info")
    if isinstance(tz_info, dict):
        coords = tz_info.get("coordinates")
        if isinstance(coords, dict):
            lat = _get_num(coords.get("latitude"))
            lon = _get_num(coords.get("longitude"))
            if lat is not None and lon is not None:
                return lat, lon

    location = chart_data.get("location")
    if isinstance(location, (list, tuple)) and len(location) >= 2:
        lat = _get_num(location[0])
        lon = _get_num(location[1])
        if lat is not None and lon is not None:
            return lat, lon

    return None, None


def _parse_utc_datetime(chart_data: Dict[str, Any]) -> Optional[datetime]:
    tz_info = chart_data.get("timezone_info")
    candidates: List[Any] = []
    if isinstance(tz_info, dict):
        candidates.append(tz_info.get("utc_time"))
    candidates.extend([
        chart_data.get("utc_time"),
        chart_data.get("timestamp_utc"),
        chart_data.get("timestamp"),
        chart_data.get("date_time_utc"),
    ])

    for raw in candidates:
        if not raw:
            continue
        try:
            text = str(raw).strip()
            if text.endswith("Z"):
                text = f"{text[:-1]}+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def _direct_sun_altitude(chart_data: Dict[str, Any], sun: Dict[str, Any]) -> Optional[float]:
    for container in (chart_data, sun):
        if not isinstance(container, dict):
            continue
        for key in ("sun_altitude_deg", "sun_altitude", "solar_altitude_deg", "solar_altitude"):
            value = _get_num(container.get(key))
            if value is not None:
                return value

    horizontal = chart_data.get("sun_horizontal")
    if isinstance(horizontal, dict):
        for key in ("altitude_deg", "altitude"):
            value = _get_num(horizontal.get(key))
            if value is not None:
                return value

    positions = chart_data.get("horizontal_positions")
    if isinstance(positions, dict):
        sun_horizontal = positions.get("Sun") or positions.get("sun")
        if isinstance(sun_horizontal, dict):
            for key in ("altitude_deg", "altitude"):
                value = _get_num(sun_horizontal.get(key))
                if value is not None:
                    return value

    return None


def _computed_sun_altitude(chart_data: Dict[str, Any], sun: Dict[str, Any]) -> Optional[float]:
    lat, lon = _chart_coords(chart_data)
    dt_utc = _parse_utc_datetime(chart_data)
    sun_lon = _get_num(sun.get("longitude"))
    sun_lat = _get_num(sun.get("latitude"), 0.0)
    if lat is None or lon is None or dt_utc is None or sun_lon is None:
        return None

    try:
        hour = (
            dt_utc.hour
            + dt_utc.minute / 60.0
            + dt_utc.second / 3600.0
            + dt_utc.microsecond / 3600000000.0
        )
        jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)
        _azimuth, true_altitude, _apparent_altitude = swe.azalt(
            jd_ut,
            swe.ECL2HOR,
            [float(lon), float(lat), 0.0],
            0.0,
            0.0,
            [float(sun_lon), float(sun_lat or 0.0), 1.0],
        )
        return float(true_altitude)
    except Exception:
        return None


def _sun_altitude(chart_data: Dict[str, Any], planets: Dict[str, Dict[str, Any]]) -> Optional[float]:
    sun = planets.get("Sun")
    if not isinstance(sun, dict):
        return None
    direct = _direct_sun_altitude(chart_data, sun)
    if direct is not None:
        return direct
    return _computed_sun_altitude(chart_data, sun)


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


def _chart_sect_from_horizon(chart_data: Dict[str, Any], planets: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[float]]:
    altitude = _sun_altitude(chart_data, planets)
    if altitude is not None:
        return ("diurnal" if altitude >= 0.0 else "nocturnal"), altitude

    s_house = _sun_house(chart_data)
    if s_house is None:
        return None, None
    return ("diurnal" if 7 <= int(s_house) <= 12 else "nocturnal"), None


def _preferred_polarity(assigned_sect: Optional[str]) -> Optional[str]:
    if assigned_sect == "diurnal":
        return "masculine"
    if assigned_sect == "nocturnal":
        return "feminine"
    return None


def _preferred_hemisphere(assigned_sect: Optional[str], chart_sect: Optional[str]) -> Optional[str]:
    if assigned_sect not in ("diurnal", "nocturnal") or chart_sect not in ("diurnal", "nocturnal"):
        return None
    return "above" if assigned_sect == chart_sect else "below"


def compute_sect_info(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute chart sect summary and per-planet comfort (in-sect, hayz).

    Returns a dict with keys:
      - chart_sect: 'diurnal'|'nocturnal'|None
      - sect_light: 'Sun'|'Moon'|None
      - malefic_of_sect: 'Saturn'|'Mars'|None
      - benefic_of_sect: 'Jupiter'|'Venus'|None
      - sun_altitude_deg: float|None
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

    # Determine chart sect by Sun above/below the astronomical horizon.
    chart_sect, sun_altitude_deg = _chart_sect_from_horizon(chart_data, planets_map)

    sect_light = "Sun" if chart_sect == "diurnal" else "Moon" if chart_sect == "nocturnal" else None
    malefic_of_sect = "Saturn" if chart_sect == "diurnal" else "Mars" if chart_sect == "nocturnal" else None
    benefic_of_sect = "Jupiter" if chart_sect == "diurnal" else "Venus" if chart_sect == "nocturnal" else None

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
        in_sect = (
            (a_sect == chart_sect)
            if a_sect in ("diurnal", "nocturnal") and chart_sect in ("diurnal", "nocturnal")
            else None
        )

        pref_pol = _preferred_polarity(a_sect)
        pol_match = (pol == pref_pol) if pol in ("masculine", "feminine") and pref_pol else None

        pref_hem = _preferred_hemisphere(a_sect, chart_sect)
        hem_match = (hemisphere == pref_hem) if hemisphere in ("above", "below") and pref_hem else None

        hayz = bool(in_sect is True and pol_match is True and hem_match is True)

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
            "preferred_sign_polarity": pref_pol,
            "sign_polarity_match": pol_match,
            "house": h,
            "hemisphere": hemisphere,
            "preferred_hemisphere": pref_hem,
            "hemisphere_match": hem_match,
            "hayz": hayz,
        })

    return {
        "chart_sect": chart_sect,
        "sect_light": sect_light,
        "malefic_of_sect": malefic_of_sect,
        "benefic_of_sect": benefic_of_sect,
        "sun_altitude_deg": sun_altitude_deg,
        "mercury_phase": phase,
        "mercury_assigned_sect": mercury_assigned_sect,
        "planets": rows,
        "in_sect_planets": in_sect_names,
        "out_of_sect_planets": out_sect_names,
        "hayz_planets": hayz_names,
    }
