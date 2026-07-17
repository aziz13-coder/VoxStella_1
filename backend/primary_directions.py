# -*- coding: utf-8 -*-
"""
Regiomontanus Primary Directions — context windows for Morin-style transits.

This module computes direct and converse primary direction windows using
Regiomontanus oblique ascensions with full latitude handling. The output
is used by the transit engine to check concordance between radical
directions, revolutions, and transits.

Key features:
- Supports Asc/MC, the seven classical planets, and Part of Fortune as
  significators, with planets, their aspects, and antiscions as promittors.
- Applies diurnal/nocturnal semi-arc geometry (via oblique ascensions) to
  derive the arc in degrees and converts the arc to civil days using Morin’s
  “1° ≈ 1 year” key.
- Emits both direct and converse directions when the arc magnitude is less
  than ``MAX_ARC_DEGREES`` (default 120°), returning windows centred on the
  predicted completion timestamp for the requested calendar year.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import math

from swisseph_state import swisseph as swe

try:
    from context_layers import compute_solar_return_timestamp  # type: ignore
except Exception:  # pragma: no cover
    compute_solar_return_timestamp = None  # type: ignore

CLASSICAL = ("Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn")
BENEFICS = {"Jupiter", "Venus"}
MALEFICS = {"Mars", "Saturn"}
ASPECTS_DEFAULT = [0.0, 60.0, 90.0, 120.0, 180.0]
ASPECT_LABELS = {
    0.0: "conjunction",
    60.0: "sextile",
    90.0: "square",
    120.0: "trine",
    180.0: "opposition",
}
ASPECT_STRENGTH = {
    0.0: 100.0,
    60.0: 75.0,
    90.0: 85.0,
    120.0: 80.0,
    180.0: 90.0,
}
MAX_ARC_DEGREES = 120.0
MORIN_ARC_TO_DAYS = 1.014583


def _norm360(x: float) -> float:
    return float(x) % 360.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _obliquity_deg(jd: float) -> float:
    """Return mean obliquity (deg). If Swiss Ephemeris available, use it; else fallback constant."""
    try:
        if swe is None:
            return 23.4392911
        # Swiss Ephem: use mean obliquity from swe.calc_ut(jd, swe.ECL_NUT)
        # Python wrapper returns: [mean_obliquity, true_obliquity, ...], but not always consistent across builds.
        # Safer: use swe.calc_ut + swe.
        obl = swe.calc_ut(jd, swe.ECL_NUT)[0]
        return float(obl)
    except Exception:
        return 23.4392911


def _ecl_to_equ(lon_deg: float, lat_deg: float, eps_deg: float) -> Tuple[float, float]:
    """Convert ecliptic longitude/latitude to equatorial RA/Dec (degrees)."""
    lam = math.radians(float(lon_deg))
    bet = math.radians(float(lat_deg))
    eps = math.radians(float(eps_deg))
    sin_dec = math.sin(bet) * math.cos(eps) + math.cos(bet) * math.sin(eps) * math.sin(lam)
    dec = math.degrees(math.asin(_clamp(sin_dec, -1.0, 1.0)))
    y = math.sin(lam) * math.cos(eps) - math.tan(bet) * math.sin(eps)
    x = math.cos(lam)
    ra = math.degrees(math.atan2(y, x)) % 360.0
    return ra, dec


def _oblique_ascension(ra_deg: float, dec_deg: float, geo_lat_deg: float) -> Optional[Tuple[float, float]]:
    """Return (oblique ascension, semi-arc) for rising; None if circumpolar."""
    phi = math.radians(float(geo_lat_deg))
    dec = math.radians(float(dec_deg))
    try:
        cos_h = -math.tan(phi) * math.tan(dec)
    except Exception:
        return None
    if abs(cos_h) > 1.0:
        if abs(cos_h) > 1.02:
            return None
        cos_h = _clamp(cos_h, -1.0, 1.0)
    h = math.degrees(math.acos(cos_h))
    oa = (ra_deg - h) % 360.0
    return oa, h


def _jd_from_datetime(dt: datetime) -> float:
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0) if swe else 0.0


def _planet_ecl_lonlat(jd: float, name: str) -> Tuple[float, float]:
    pid = getattr(swe, name.upper(), None) if swe else None
    if pid is None or swe is None:
        return (0.0, 0.0)
    pos, _ = swe.calc_ut(jd, pid, swe.FLG_SWIEPH)
    # pos[0]=lon, pos[1]=lat
    return (float(pos[0]) % 360.0, float(pos[1]))


def _extract_latitude(natal_cd: Dict[str, Any]) -> float:
    """Best-effort extraction of geographic latitude (degrees)."""
    if not isinstance(natal_cd, dict):
        return 0.0
    preferred_keys = [
        ('location', 'latitude'),
        ('location', 'lat'),
        ('birth_location', 'latitude'),
        ('metadata', 'location', 'latitude'),
        ('observer', 'latitude'),
        ('geo', 'latitude'),
    ]
    for path in preferred_keys:
        data = natal_cd
        try:
            for key in path:
                if not isinstance(data, dict):
                    data = None
                    break
                data = data.get(key)
            if data is not None:
                return float(data)
        except Exception:
            continue
    try:
        if natal_cd.get('latitude') is not None:
            return float(natal_cd.get('latitude'))
    except Exception:
        pass
    return 0.0


def _extract_longitude(natal_cd: Dict[str, Any]) -> float:
    """Best-effort extraction of geographic longitude (degrees East)."""
    if not isinstance(natal_cd, dict):
        return 0.0
    preferred_keys = [
        ('location', 'longitude'),
        ('location', 'lon'),
        ('birth_location', 'longitude'),
        ('metadata', 'location', 'longitude'),
        ('observer', 'longitude'),
        ('geo', 'longitude'),
    ]
    for path in preferred_keys:
        data = natal_cd
        try:
            for key in path:
                if not isinstance(data, dict):
                    data = None
                    break
                data = data.get(key)
            if data is not None:
                return float(data)
        except Exception:
            continue
    try:
        if natal_cd.get('longitude') is not None:
            return float(natal_cd.get('longitude'))
    except Exception:
        pass
    return 0.0


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        v = value.replace('Z', '+00:00')
        dt = datetime.fromisoformat(v)
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _extract_natal_datetime(natal_cd: Dict[str, Any]) -> datetime:
    """Return natal datetime in UTC."""
    if not isinstance(natal_cd, dict):
        raise ValueError("Natal chart data missing")
    direct_keys = ['datetime', 'timestamp', 'birth_datetime', 'natal_datetime', 'original_datetime']
    for key in direct_keys:
        val = natal_cd.get(key)
        if isinstance(val, str):
            dt = _parse_iso_datetime(val)
            if dt:
                return dt
    metadata = natal_cd.get('metadata')
    if isinstance(metadata, dict):
        for key in ('birth_iso', 'original_birth_iso', 'datetime'):
            val = metadata.get(key)
            if isinstance(val, str):
                dt = _parse_iso_datetime(val)
                if dt:
                    return dt
    # Accept date + time combos
    date_val = natal_cd.get('date') or (metadata.get('date') if isinstance(metadata, dict) else None)
    time_val = natal_cd.get('time') or (metadata.get('time') if isinstance(metadata, dict) else None)
    if isinstance(date_val, str):
        try:
            iso = f"{date_val}T{time_val or '00:00:00'}"
            dt = _parse_iso_datetime(iso)
            if dt:
                return dt
        except Exception:
            pass
    raise ValueError("Unable to determine natal datetime from chart data")


def _extract_pof_longitude(natal_cd: Dict[str, Any]) -> Optional[float]:
    if not isinstance(natal_cd, dict):
        return None
    for key in ('arabic_parts', 'parts', 'lots'):
        data = natal_cd.get(key)
        if isinstance(data, dict):
            for name, val in data.items():
                try:
                    if 'fortune' in str(name).lower():
                        if isinstance(val, dict) and val.get('longitude') is not None:
                            return float(val.get('longitude')) % 360.0
                        return float(val) % 360.0
                except Exception:
                    continue
    return None


def _house_of(body: str, natal_cd: Dict[str, Any]) -> Optional[int]:
    planets = natal_cd.get('planets')
    if isinstance(planets, dict) and body in planets:
        row = planets[body]
        if isinstance(row, dict) and row.get('house') is not None:
            try:
                return int(row.get('house'))
            except Exception:
                return None
    if isinstance(planets, list):
        for row in planets:
            if isinstance(row, dict) and row.get('planet') == body and row.get('house') is not None:
                try:
                    return int(row.get('house'))
                except Exception:
                    return None
    return None


def _domain_of_house(house: Optional[int]) -> Optional[str]:
    mapping = {
        1: 'life',
        2: 'wealth',
        3: 'short_journeys',
        4: 'home',
        5: 'children',
        6: 'health',
        7: 'relationships',
        8: 'shared_resources',
        9: 'belief',
        10: 'honors',
        11: 'friends',
        12: 'secrets',
    }
    return mapping.get(int(house)) if isinstance(house, int) else None


NATURAL_DOMAINS = {
    'Sun': 'honors',
    'Moon': 'life',
    'Mercury': 'short_journeys',
    'Venus': 'relationships',
    'Mars': 'life',
    'Jupiter': 'honors',
    'Saturn': 'career',
    'Asc': 'life',
    'MC': 'honors',
    'Part of Fortune': 'wealth',
}

SIGNIFICATION_LABELS = {
    'life': 'life',
    'health': 'illness',
    'shared_resources': 'inheritance',
    'death': 'death',
    'honors': 'honors',
    'career': 'career',
    'wealth': 'wealth',
    'relationships': 'relationships',
    'marriage': 'relationships',
    'children': 'children',
    'short_journeys': 'travel',
    'long_journeys': 'travel',
    'belief': 'faith',
    'home': 'home',
    'friends': 'alliances',
    'secrets': 'hidden_matters',
}


def _collect_natal_positions(
    natal_cd: Dict[str, Any],
    natal_dt: datetime,
    include_modern: bool = False,
) -> Tuple[Dict[str, Dict[str, float]], float, float, float, Optional[float]]:
    jd = _jd_from_datetime(natal_dt)
    eps = _obliquity_deg(jd)
    geo_lat = _extract_latitude(natal_cd)
    geo_lon = _extract_longitude(natal_cd)
    positions: Dict[str, Dict[str, float]] = {}

    def add_position(name: str, lon: float, lat: float = 0.0) -> None:
        try:
            ra, dec = _ecl_to_equ(lon, lat, eps)
            oa_data = _oblique_ascension(ra, dec, geo_lat)
            if oa_data is None:
                return
            oa, semi_arc = oa_data
            positions[name] = {
                'lon': _norm360(lon),
                'lat': float(lat),
                'ra': ra,
                'dec': dec,
                'oa': oa,
                'semi_arc': semi_arc,
            }
        except Exception:
            return

    planet_names = list(CLASSICAL)
    if include_modern:
        planet_names.extend(['Uranus', 'Neptune', 'Pluto'])

    planets = (natal_cd or {}).get('planets') or {}
    if isinstance(planets, dict):
        for nm, row in planets.items():
            if nm not in planet_names or not isinstance(row, dict):
                continue
            lon = row.get('longitude')
            if lon is None:
                continue
            lat = float(row.get('latitude') or 0.0)
            add_position(nm, float(lon), lat)
    elif isinstance(planets, list):
        for row in planets:
            if not isinstance(row, dict):
                continue
            nm = str(row.get('planet'))
            if nm not in planet_names:
                continue
            lon = row.get('longitude')
            if lon is None:
                continue
            lat = float(row.get('latitude') or 0.0)
            add_position(nm, float(lon), lat)

    ascmc_vals: Optional[List[float]] = None
    ramc: Optional[float] = None
    if swe is not None:
        try:
            houses_data, ascmc = swe.houses(jd, geo_lat, geo_lon, b'R')
            ascmc_vals = list(ascmc)
            mc_lon = float(ascmc[1])
            ramc, _ = _ecl_to_equ(mc_lon, 0.0, eps)
        except Exception:
            ramc = None
            ascmc_vals = None

    try:
        houses = (natal_cd.get('houses') or natal_cd.get('house_cusps') or [])
        if isinstance(houses, list) and len(houses) >= 10:
            add_position('Asc', float(houses[0]) % 360.0, 0.0)
            add_position('MC', float(houses[9]) % 360.0, 0.0)
    except Exception:
        pass

    if ascmc_vals:
        try:
            if 'Asc' not in positions:
                add_position('Asc', float(ascmc_vals[0]) % 360.0, 0.0)
            if 'MC' not in positions:
                add_position('MC', float(ascmc_vals[1]) % 360.0, 0.0)
        except Exception:
            pass

    pof_lon = _extract_pof_longitude(natal_cd)
    if pof_lon is not None:
        add_position('Part of Fortune', pof_lon, 0.0)

    return positions, eps, geo_lat, geo_lon, ramc


def _direction_domain(name: str, natal_cd: Dict[str, Any]) -> Optional[str]:
    domain = _domain_of_house(_house_of(name, natal_cd))
    if domain:
        return domain
    return NATURAL_DOMAINS.get(name)


def _aspect_strength_value(aspect: float, promittor: str) -> float:
    base = ASPECT_STRENGTH.get(round(aspect % 360.0, 3), 70.0)
    if promittor in BENEFICS:
        base += 5.0
    elif promittor in MALEFICS:
        base -= 5.0
    return _clamp(base, 35.0, 100.0)


def _quality_label(strength: float) -> str:
    if strength >= 80.0:
        return 'benefic'
    if strength <= 55.0:
        return 'malefic'
    return 'mixed'


def _regio_zenith_distance(md_deg: float, lat_deg: float, decl_deg: float, upper: bool) -> float:
    """Approximate Regiomontanus zenith distance (deg)."""
    md = abs(float(md_deg))
    lat = float(lat_deg)
    decl = float(decl_deg)
    if abs(md - 90.0) < 1e-6:
        val = math.sin(math.radians(abs(lat))) * math.tan(math.radians(decl))
        val = max(-1.0, min(1.0, val))
        return 90.0 - math.degrees(math.atan(val))
    A = math.degrees(math.atan(math.cos(math.radians(lat)) * math.tan(math.radians(md))))
    B = math.degrees(math.atan(math.tan(math.radians(abs(lat))) * math.cos(math.radians(md))))
    if (decl < 0 and lat < 0) or (decl >= 0 and lat >= 0):
        C = B - abs(decl) if upper else B + abs(decl)
    else:
        C = B + abs(decl) if upper else B - abs(decl)
    F = math.degrees(
        math.atan(
            math.sin(math.radians(abs(lat))) *
            math.sin(math.radians(md)) *
            math.tan(math.radians(C))
        )
    )
    return A + F


def _regiomontanus_speculum(ra_deg: float, decl_deg: float, geo_lat_deg: float, ramc_deg: float) -> Optional[Dict[str, float]]:
    """Return minimal Regiomontanus speculum components (W, pole, md, hd)."""
    try:
        ra = float(ra_deg) % 360.0
        decl = float(decl_deg)
        lat = float(geo_lat_deg)
        ramc = float(ramc_deg) % 360.0
    except Exception:
        return None
    raic = (ramc + 180.0) % 360.0
    # Eastern or western of meridian
    if ramc > raic:
        eastern = not (raic < ra < ramc)
    else:
        eastern = not ((raic < ra < 360.0) or (0.0 <= ra < ramc))
    # Meridian distances
    med = abs(ramc - ra)
    if med > 180.0:
        med = 360.0 - med
    icd = abs(raic - ra)
    if icd > 180.0:
        icd = 360.0 - icd
    md = med
    table_md = med
    upper = True
    if icd < med:
        md = icd
        table_md = -icd
        upper = False
    # Adding declination latitude
    val = math.tan(math.radians(lat)) * math.tan(math.radians(decl))
    val = max(-1.0, min(1.0, val))
    adlat = math.degrees(math.asin(val))
    aoasc = (ramc + 90.0) % 360.0
    dodesc = (raic + 90.0) % 360.0
    aohd = ra - adlat
    hdasc = abs(aohd - aoasc)
    if hdasc > 180.0:
        hdasc = 360.0 - hdasc
    dohd = ra + adlat
    hddesc = abs(dohd - dodesc)
    if hddesc > 180.0:
        hddesc = 360.0 - hddesc
    hd = hdasc
    if hddesc < hdasc:
        hd = -hddesc
    dsa = 90.0 + adlat
    above = not (med > dsa)
    zd = _regio_zenith_distance(md, lat, decl, upper)
    tmpzd = zd
    if (above and hd < 0.0) or (not above and hd > 0.0):
        zd *= -1.0
    pole = 0.0
    try:
        pole_val = math.sin(math.radians(lat)) * math.sin(math.radians(tmpzd))
        pole = math.degrees(math.asin(max(-1.0, min(1.0, pole_val))))
    except Exception:
        pole = 0.0
    try:
        q_val = math.tan(math.radians(decl)) * math.tan(math.radians(pole))
        q_val = max(-1.0, min(1.0, q_val))
        Q = math.degrees(math.asin(q_val))
    except Exception:
        Q = 0.0
    if eastern:
        W = (ra - Q) % 360.0
    else:
        W = (ra + Q) % 360.0
    return {
        'W': W,
        'pole': pole,
        'md': table_md,
        'hd': hd,
        'above_horizon': above,
        'eastern': eastern,
    }


def _iter_promittor_targets(
    name: str,
    data: Dict[str, float],
    aspects: List[float],
    eps_deg: float,
    geo_lat: float,
    ramc: Optional[float],
) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    base_lon = data['lon']
    lat = data['lat']

    def build_entry(suffix: str, lon_val: float, aspect_val: float, antiscion: bool = False) -> Optional[Dict[str, Any]]:
        try:
            ra, dec = _ecl_to_equ(lon_val, lat, eps_deg)
            oa_data = _oblique_ascension(ra, dec, geo_lat)
            if oa_data is None:
                return None
            oa, semi_arc = oa_data
            return {
                'label': f"{name}{suffix}",
                'lon': _norm360(lon_val),
                'lat': lat,
                'ra': ra,
                'dec': dec,
                'oa': oa,
                'semi_arc': semi_arc,
                'w': (_regiomontanus_speculum(ra, dec, geo_lat, ramc) or {}).get('W') if ramc is not None else None,
                'aspect': aspect_val,
                'aspect_label': ASPECT_LABELS.get(aspect_val, 'conjunction'),
                'is_antiscion': antiscion,
            }
        except Exception:
            return None

    base_entry = None
    try:
        base_oa = data.get('oa')
        if base_oa is not None:
            base_entry = {
                'label': f"{name}",
                'lon': _norm360(base_lon),
                'lat': lat,
                'ra': data.get('ra'),
                'dec': data.get('dec'),
                'oa': float(base_oa),
                'semi_arc': data.get('semi_arc'),
                'w': data.get('w'),
                'aspect': 0.0,
                'aspect_label': ASPECT_LABELS.get(0.0, 'conjunction'),
                'is_antiscion': False,
            }
    except Exception:
        base_entry = None
    if base_entry is None:
        base_entry = build_entry('', base_lon, 0.0)
    if base_entry:
        entries.append(base_entry)
    for aspect in aspects:
        if aspect == 0.0:
            continue
        entry = build_entry(f" {ASPECT_LABELS.get(aspect, aspect)}", base_lon + aspect, aspect)
        if entry:
            entries.append(entry)
    ant = build_entry(' antiscion', 180.0 - base_lon, 0.0, antiscion=True)
    if ant:
        entries.append(ant)
    return entries


def _direction_signification(sig: str, prom: str, natal_cd: Dict[str, Any]) -> Dict[str, Any]:
    primary_domain = _direction_domain(prom, natal_cd)
    if primary_domain:
        label = SIGNIFICATION_LABELS.get(primary_domain, primary_domain)
        return {'domain': primary_domain, 'label': label, 'source': 'promittor'}
    fallback = _direction_domain(sig, natal_cd)
    label = SIGNIFICATION_LABELS.get(fallback, fallback or 'life')
    return {'domain': fallback or 'life', 'label': label, 'source': 'significator'}
def compute_primary_direction_windows(
    natal_dt: datetime,
    year: int,
    natal_cd: Dict[str, Any],
    *,
    aspects: Optional[List[float]] = None,
    window_days: int = 365,
    include_modern: bool = False,
) -> List[Dict[str, Any]]:
    """Compute Regiomontanus primary direction windows (direct + converse)."""
    if swe is None:
        return []
    if aspects is None:
        aspects = list(ASPECTS_DEFAULT)

    try:
        natal_dt_utc = natal_dt.astimezone(timezone.utc) if natal_dt.tzinfo else natal_dt.replace(tzinfo=timezone.utc)
    except Exception:
        natal_dt_utc = natal_dt.replace(tzinfo=timezone.utc)

    collected = _collect_natal_positions(natal_cd or {}, natal_dt_utc, include_modern=include_modern)
    if not isinstance(collected, tuple):
        return []
    if len(collected) >= 5:
        positions, eps_deg, geo_lat, geo_lon, ramc = collected[:5]
    elif len(collected) == 4:
        positions, eps_deg, geo_lat, geo_lon = collected
        ramc = None
    elif len(collected) == 3:
        positions, eps_deg, geo_lat = collected
        geo_lon = 0.0
        ramc = None
    else:
        return []
    if not positions:
        return []

    if ramc is not None:
        for info in positions.values():
            spec = _regiomontanus_speculum(info.get('ra', 0.0), info.get('dec', 0.0), geo_lat, ramc)
            if spec:
                info['w'] = spec.get('W')

    significators = {name: data for name, data in positions.items() if name in positions}
    windows: List[Dict[str, Any]] = []
    base_dt_cache: Dict[int, datetime] = {}

    def _base_timestamp(target_year: int) -> datetime:
        if target_year in base_dt_cache:
            return base_dt_cache[target_year]
        sr_dt = None
        try:
            if compute_solar_return_timestamp and 'Sun' in positions:
                sr_dt = compute_solar_return_timestamp(positions['Sun']['lon'], target_year)
        except Exception:
            sr_dt = None
        if sr_dt is None:
            sr_dt = datetime(target_year, 1, 1, tzinfo=timezone.utc)
        else:
            sr_dt = sr_dt.astimezone(timezone.utc) if sr_dt.tzinfo else sr_dt.replace(tzinfo=timezone.utc)
        base_dt_cache[target_year] = sr_dt
        return sr_dt

    for sig_name, sig_info in significators.items():
        w_sig = sig_info.get('w')
        oa_sig = sig_info.get('oa')
        if w_sig is None and oa_sig is None:
            continue
        for prom_name, prom_info in positions.items():
            if prom_name == sig_name:
                continue
            targets = _iter_promittor_targets(prom_name, prom_info, aspects, eps_deg, geo_lat, ramc)
            if not targets:
                continue
            direction_domain = _direction_domain(prom_name, natal_cd or {}) or _direction_domain(sig_name, natal_cd or {}) or 'life'
            for target in targets:
                w_prom = target.get('w')
                oa_prom = target.get('oa')
                if w_sig is not None and w_prom is not None:
                    arc_forward = (w_prom - w_sig) % 360.0
                    arc_backward = (w_sig - w_prom) % 360.0
                else:
                    if oa_sig is None or oa_prom is None:
                        continue
                    arc_forward = (oa_prom - oa_sig) % 360.0
                    arc_backward = (oa_sig - oa_prom) % 360.0
                arc_entries: List[Tuple[float, str]] = []
                if 0.0 < arc_forward <= MAX_ARC_DEGREES:
                    arc_entries.append((arc_forward, 'direct'))
                if 0.0 < arc_backward <= MAX_ARC_DEGREES:
                    arc_entries.append((-arc_backward, 'converse'))
                if not arc_entries:
                    continue

                strength = _aspect_strength_value(target.get('aspect', 0.0), prom_name)
                quality = _quality_label(strength)
                aspect_label = target.get('aspect_label', 'conjunction')

                for arc_signed, motion in arc_entries:
                    base_dt = _base_timestamp(int(year))
                    days = arc_signed * MORIN_ARC_TO_DAYS
                    ts = base_dt + timedelta(days=days)
                    if ts.year != int(year):
                        continue
                    window_start = ts - timedelta(days=window_days)
                    window_end = ts + timedelta(days=window_days)
                    signification = _direction_signification(sig_name, prom_name, natal_cd or {})
                    windows.append({
                        'start': window_start.isoformat(),
                        'end': window_end.isoformat(),
                        'timestamp': ts.isoformat(),
                        'label': f"{sig_name} → {prom_name} ({aspect_label}, {motion})",
                        'item': {
                            'significator': sig_name,
                            'promittor': prom_name,
                            'aspect': aspect_label,
                            'motion': motion,
                            'antiscion': target.get('is_antiscion', False),
                            'type': direction_domain,
                            'strength': round(strength, 2),
                            'quality': quality,
                            'arc_degrees': round(abs(arc_signed), 6),
                            'arc_days': round(days, 6),
                            'signification': signification,
                        },
                    })

    windows.sort(
        key=lambda w: (
            0 if str((w.get('item') or {}).get('motion')) == 'direct' else 1,
            0 if not bool((w.get('item') or {}).get('antiscion')) else 1,
            w.get('timestamp', ''),
        )
    )
    return windows


__all__ = [
    'compute_primary_direction_windows'
]
