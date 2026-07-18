# -*- coding: utf-8 -*-
"""
Primary Directions (Morin/Regiomontanus) — angles-focused implementation

Implements the arc-of-direction for significators on angles (Asc, MC)
and classical planets as promittors, using Regiomontanus logic:

 - MC: Arc = RA(planet) - RAMC
 - Asc: Arc = OA(planet, φ) - OA(Asc, φ) with OA(Asc) = RAMC + 90°

Declination and oblique ascension include ecliptic latitude of planets.
Time conversion uses Naibod measure: ~0.985647° (RA) per year.

This module provides a solid base to feed PD windows into the Transits
feature. It focuses on angles, which are the most practically used
significators. Aspects and full in-mundo aspect corrections can be added
in a follow-up iteration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, timedelta, timezone
import math
from morin_aspects import (
    ASPECT_SET,
    _sph_to_vec,
    _unit,
    _rotate,
    _build_plane_normal,
    _jd_from_iso,
    _apparent_inclination,
)


NAIBOD_DEG_PER_YEAR = 0.985647  # deg of RA per year
OBLIQUITY_DEG = 23.4392911
CLASSICAL = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]


def _rad(x: float) -> float:
    return math.radians(float(x))


def _deg(x: float) -> float:
    return math.degrees(float(x))


def _wrap360(x: float) -> float:
    return float(x) % 360.0


def _wrap24h_deg(x: float) -> float:
    # RA modulo 24h = 360°
    return _wrap360(x)


def _normalize_positive_arc(a: float) -> float:
    # force into [0, 360)
    return _wrap360(a)


def ecl_to_eq_ra_dec(lon_deg: float, lat_deg: float, eps_deg: float = OBLIQUITY_DEG) -> Tuple[float, float]:
    """Convert ecliptic lon/lat (deg) to equatorial RA (deg) and declination (deg)."""
    lam = _rad(lon_deg)
    beta = _rad(lat_deg)
    eps = _rad(eps_deg)
    sin_alpha = math.sin(lam) * math.cos(eps) - math.tan(beta) * math.sin(eps)
    cos_alpha = math.cos(lam)
    ra = math.atan2(sin_alpha, cos_alpha)  # radians
    ra_deg = _wrap360(_deg(ra))
    dec = math.asin(math.sin(beta) * math.cos(eps) + math.cos(beta) * math.sin(eps) * math.sin(lam))
    dec_deg = _deg(dec)
    return ra_deg, dec_deg


def ascensional_difference(dec_deg: float, pole_deg: float) -> float:
    """AD = arcsin(tan D * tan P) in degrees. Clamp domain to [-1,1]."""
    t = math.tan(_rad(dec_deg)) * math.tan(_rad(pole_deg))
    t = max(-1.0, min(1.0, t))
    return _deg(math.asin(t))


def oblique_ascension(ra_deg: float, dec_deg: float, latitude_deg: float) -> float:
    ad = ascensional_difference(dec_deg, latitude_deg)
    return _wrap24h_deg(ra_deg - ad)


def compute_pd_to_angles(natal_cd: Dict[str, Any], latitude_deg: float) -> List[Dict[str, Any]]:
    """Compute PD arcs for classical planets directed to the MC and Asc.

    Returns items: {significator: 'MC'|'Asc', promittor, arc_deg, age_years, type: 'direct'|'converse',
                    ra2, dec2, ra_mc, oa_asc}
    """
    # Extract cusps (C1 = Asc, C10 = MC) in ecliptic longitude
    cusps = []
    try:
        hc = natal_cd.get('houses') or natal_cd.get('house_cusps') or []
        if isinstance(hc, list):
            cusps = [float(x) for x in hc[:12]]
    except Exception:
        cusps = []
    if len(cusps) < 10:
        return []
    lon_asc = float(cusps[0])
    lon_mc = float(cusps[9])
    # RA of MC (ecliptic lat 0)
    ra_mc, dec_dummy = ecl_to_eq_ra_dec(lon_mc, 0.0)
    oa_asc = _wrap24h_deg(ra_mc + 90.0)  # OA of Asc at latitude

    # Collect natal planets long/lat
    raw_pl = natal_cd.get('planets') or {}
    planets: List[Dict[str, Any]] = []
    if isinstance(raw_pl, dict):
        for nm, info in raw_pl.items():
            if nm in CLASSICAL and isinstance(info, dict):
                try:
                    lon = float(info.get('longitude'))
                    lat = float(info.get('latitude', 0.0) or 0.0)
                    planets.append({'planet': nm, 'lon': lon, 'lat': lat})
                except Exception:
                    continue
    elif isinstance(raw_pl, list):
        for info in raw_pl:
            if isinstance(info, dict) and info.get('planet') in CLASSICAL:
                try:
                    lon = float(info.get('longitude'))
                    lat = float(info.get('latitude', 0.0) or 0.0)
                    planets.append({'planet': info.get('planet'), 'lon': lon, 'lat': lat})
                except Exception:
                    continue

    out: List[Dict[str, Any]] = []
    for row in planets:
        nm, lon, lat = row['planet'], row['lon'], row['lat']
        ra2, dec2 = ecl_to_eq_ra_dec(lon, lat)
        # MC directions
        arc_mc = _normalize_positive_arc(ra2 - ra_mc)
        # Asc directions
        oa2 = oblique_ascension(ra2, dec2, latitude_deg)
        arc_asc = _normalize_positive_arc(oa2 - oa_asc)
        # Ages (direct)
        age_mc = arc_mc / NAIBOD_DEG_PER_YEAR
        age_asc = arc_asc / NAIBOD_DEG_PER_YEAR
        # Converse arcs (360 - arc)
        c_arc_mc = _normalize_positive_arc(360.0 - arc_mc)
        c_arc_asc = _normalize_positive_arc(360.0 - arc_asc)
        c_age_mc = c_arc_mc / NAIBOD_DEG_PER_YEAR
        c_age_asc = c_arc_asc / NAIBOD_DEG_PER_YEAR

        out.append({'significator': 'MC', 'promittor': nm, 'aspect': 'Conjunction',
                    'arc_deg': round(arc_mc, 6), 'age_years': round(age_mc, 6), 'type': 'direct',
                    'ra_mc': ra_mc, 'ra2': ra2, 'dec2': dec2, 'oa_asc': oa_asc})
        out.append({'significator': 'Asc', 'promittor': nm, 'aspect': 'Conjunction',
                    'arc_deg': round(arc_asc, 6), 'age_years': round(age_asc, 6), 'type': 'direct',
                    'ra_mc': ra_mc, 'ra2': ra2, 'dec2': dec2, 'oa_asc': oa_asc})
        out.append({'significator': 'MC', 'promittor': nm, 'aspect': 'Conjunction',
                    'arc_deg': round(c_arc_mc, 6), 'age_years': round(c_age_mc, 6), 'type': 'converse',
                    'ra_mc': ra_mc, 'ra2': ra2, 'dec2': dec2, 'oa_asc': oa_asc})
        out.append({'significator': 'Asc', 'promittor': nm, 'aspect': 'Conjunction',
                    'arc_deg': round(c_arc_asc, 6), 'age_years': round(c_age_asc, 6), 'type': 'converse',
                    'ra_mc': ra_mc, 'ra2': ra2, 'dec2': dec2, 'oa_asc': oa_asc})

    return out


def compute_pd_windows(
    natal_cd: Dict[str, Any],
    natal_dt: datetime,
    latitude_deg: float,
    year: int,
    window_days: int = 90,
    include_modern: bool = False,
    include_angles: bool = True,
    include_planets: bool = True,
    include_aspects: bool = True,
    aspects: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Build PD windows (±window_days) for events whose age falls in the target year.
    Returns: [{ start, end, label, item }] where item is the PD row used.

    Uses compute_pd_full to include angles, planet→planet (Regiomontanus CP) and optional aspect points.
    """
    res = compute_pd_full(
        natal_cd, latitude_deg,
        include_modern=include_modern,
        include_angles=include_angles,
        include_planets=include_planets,
        include_aspects=include_aspects,
        aspects=aspects,
    )
    dirs = res.get('directions', []) or []
    out: List[Dict[str, Any]] = []
    for d in dirs:
        try:
            age = float(d.get('age_years') or 0.0)
            if age <= 0:
                continue
            event_dt = natal_dt + timedelta(days=age * 365.24219)
            if event_dt.year != year:
                continue
            s = (event_dt - timedelta(days=window_days)).isoformat()
            e = (event_dt + timedelta(days=window_days)).isoformat()
            sig = d.get('significator')
            pro = d.get('promittor')
            asp = d.get('aspect')
            typ = d.get('type')
            label = f"PD {typ} {pro}→{sig} ({asp})"
            out.append({'start': s, 'end': e, 'label': label, 'item': d})
        except Exception:
            continue
    return out


# ----------------- General planet→planet (approximate OA method) -----------------

def compute_pd_planet_to_planet(natal_cd: Dict[str, Any], latitude_deg: float, include_modern: bool = False) -> List[Dict[str, Any]]:
    """Approximate planet→planet (in mundo) directions via OA differences under φ.

    For each significator S in classical (and optional modern), each promittor P!=S, compute
    OA under latitude φ and take Arc = OA(P) - OA(S). Returns direct and converse.
    This is a first-order approximation; a more exact Regiomontanus CP pole
    can be added in a later refinement.
    """
    modern = ["Uranus","Neptune","Pluto"] if include_modern else []
    names = CLASSICAL + modern
    # Collect lon/lat
    raw_pl = natal_cd.get('planets') or {}
    idx: Dict[str, Tuple[float,float]] = {}
    if isinstance(raw_pl, dict):
        for nm, info in raw_pl.items():
            if nm in names and isinstance(info, dict):
                try:
                    idx[nm] = (float(info.get('longitude')), float(info.get('latitude', 0.0) or 0.0))
                except Exception:
                    continue
    elif isinstance(raw_pl, list):
        for info in raw_pl:
            if isinstance(info, dict) and info.get('planet') in names:
                try:
                    idx[info['planet']] = (float(info.get('longitude')), float(info.get('latitude', 0.0) or 0.0))
                except Exception:
                    continue
    items: List[Dict[str, Any]] = []
    for s in names:
        if s not in idx: continue
        lonS, latS = idx[s]
        raS, decS = ecl_to_eq_ra_dec(lonS, latS)
        oaS = oblique_ascension(raS, decS, latitude_deg)
        for p in names:
            if p == s or p not in idx: continue
            lonP, latP = idx[p]
            raP, decP = ecl_to_eq_ra_dec(lonP, latP)
            oaP = oblique_ascension(raP, decP, latitude_deg)
            arc = _normalize_positive_arc(oaP - oaS)
            carc = _normalize_positive_arc(360.0 - arc)
            items.append({'significator': s, 'promittor': p, 'aspect': 'Conjunction',
                          'arc_deg': round(arc, 6), 'age_years': round(arc/NAIBOD_DEG_PER_YEAR, 6), 'type': 'direct'})
            items.append({'significator': s, 'promittor': p, 'aspect': 'Conjunction',
                          'arc_deg': round(carc, 6), 'age_years': round(carc/NAIBOD_DEG_PER_YEAR, 6), 'type': 'converse'})
    return items


def _hour_angle_deg(ra_mc_deg: float, ra_deg: float) -> float:
    """Hour angle H = RAMC - RA (deg), normalized to [-180,180]."""
    d = (ra_mc_deg - ra_deg + 180.0) % 360.0 - 180.0
    return d


def _azimuth_deg(phi_deg: float, dec_deg: float, H_deg: float) -> float:
    """Return azimuth A (deg) using standard spherical astronomy formulas.

    tan A = sin H / (cos H sin φ - tan δ cos φ)
    """
    phi = _rad(phi_deg)
    dec = _rad(dec_deg)
    H = _rad(H_deg)
    num = math.sin(H)
    den = (math.cos(H) * math.sin(phi) - math.tan(dec) * math.cos(phi))
    A = math.atan2(num, den)
    return _deg(A)


def _pole_of_cp(phi_deg: float, dec_deg: float, H_deg: float) -> float:
    """Pole elevation P for Regiomontanus circle of position.

    Use relation: tan P = tan φ * cos A, where A is azimuth of significator.
    """
    A = _azimuth_deg(phi_deg, dec_deg, H_deg)
    t = math.tan(_rad(phi_deg)) * math.cos(_rad(A))
    return _deg(math.atan(t))


def compute_pd_planet_to_planet_regio(natal_cd: Dict[str, Any], latitude_deg: float, include_modern: bool = False) -> List[Dict[str, Any]]:
    """Planet→planet directions using Regiomontanus CP pole for each significator.

    For each significator S, compute CP pole P_S from azimuth using natal RAMC; then compute
    AD under P_S for S and for promittor P; OA_S^CP = RA_S - AD_S(P_S), OA_P^CP = RA_P - AD_P(P_S),
    Arc = OA_P^CP - OA_S^CP (direct and converse ages by Naibod).
    """
    modern = ["Uranus","Neptune","Pluto"] if include_modern else []
    names = CLASSICAL + modern
    # RAMC from MC cusp
    cusps = natal_cd.get('houses') or natal_cd.get('house_cusps') or []
    if not (isinstance(cusps, list) and len(cusps) >= 10):
        return []
    lon_mc = float(cusps[9])
    ra_mc, _ = ecl_to_eq_ra_dec(lon_mc, 0.0)
    # Collect lon/lat
    raw_pl = natal_cd.get('planets') or {}
    idx: Dict[str, Tuple[float,float]] = {}
    if isinstance(raw_pl, dict):
        for nm, info in raw_pl.items():
            if nm in names and isinstance(info, dict):
                try:
                    idx[nm] = (float(info.get('longitude')), float(info.get('latitude', 0.0) or 0.0))
                except Exception:
                    continue
    elif isinstance(raw_pl, list):
        for info in raw_pl:
            if isinstance(info, dict) and info.get('planet') in names:
                try:
                    idx[info['planet']] = (float(info.get('longitude')), float(info.get('latitude', 0.0) or 0.0))
                except Exception:
                    continue
    out: List[Dict[str, Any]] = []
    for s in names:
        if s not in idx: continue
        lonS, latS = idx[s]
        raS, decS = ecl_to_eq_ra_dec(lonS, latS)
        Hs = _hour_angle_deg(ra_mc, raS)
        P = _pole_of_cp(latitude_deg, decS, Hs)
        # AD for S under P
        adS = ascensional_difference(decS, P)
        oaS = _wrap24h_deg(raS - adS)
        for p in names:
            if p == s or p not in idx: continue
            lonP, latP = idx[p]
            raP, decP = ecl_to_eq_ra_dec(lonP, latP)
            adP = ascensional_difference(decP, P)
            oaP = _wrap24h_deg(raP - adP)
            arc = _normalize_positive_arc(oaP - oaS)
            carc = _normalize_positive_arc(360.0 - arc)
            out.append({'significator': s, 'promittor': p, 'aspect': 'Conjunction',
                        'arc_deg': round(arc, 6), 'age_years': round(arc/NAIBOD_DEG_PER_YEAR, 6), 'type': 'direct', 'pole_deg': round(P,6)})
            out.append({'significator': s, 'promittor': p, 'aspect': 'Conjunction',
                        'arc_deg': round(carc, 6), 'age_years': round(carc/NAIBOD_DEG_PER_YEAR, 6), 'type': 'converse', 'pole_deg': round(P,6)})
    return out


def _aspect_point_on_excentric(lon_deg: float, lat_deg: float, aspect_angle: float, planet_name: Optional[str] = None) -> Tuple[float,float]:
    """Return ecliptic lon/lat (deg) for the excentric aspect point of a planet.

    Uses the Morin excentric plane method: rotate the position by ±aspect along a great
    circle whose plane is oriented to match observed latitude trend. Here, we reuse a
    simplified version by building the plane from the position and assuming a small
    forward-step trend of latitude ~0 (static), which is acceptable for static natal.
    """
    # Build excentric plane inclination using Morin apparent inclination helper
    incl = max(abs(lat_deg), _apparent_inclination(planet_name or '', lat_deg)) if planet_name else max(0.0, abs(lat_deg))
    r0 = _unit(_sph_to_vec(lon_deg, lat_deg))
    # Use small forward lat trend equal to current lat (static natal), adequate for excentric geometry
    n = _build_plane_normal(r0, lat_deg, lat_deg, incl)
    r_aspect = _unit(_rotate(r0, n, aspect_angle))
    # convert to lon/lat
    # inverse of _sph_to_vec
    x,y,z = r_aspect
    lam = math.degrees(math.atan2(y, x)) % 360.0
    beta = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    return lam, beta


def compute_pd_aspects(natal_cd: Dict[str, Any], latitude_deg: float, include_modern: bool = False, aspects: Optional[List[float]] = None) -> List[Dict[str, Any]]:
    """Compute directions to promittor aspects (approximate in-mundo correction).

    For each planet P, compute excentric aspect point at given aspect angles (deg),
    convert to RA/Dec including the aspect latitude, then compute arcs to:
     - MC and Asc (as if aspect point is promittor), and
     - other planets (OA difference under φ approximation).
    """
    if aspects is None:
        aspects = [0.0, 60.0, 90.0, 120.0, 180.0]
    modern = ["Uranus","Neptune","Pluto"] if include_modern else []
    names = CLASSICAL + modern
    raw_pl = natal_cd.get('planets') or {}
    idx: Dict[str, Tuple[float,float]] = {}
    if isinstance(raw_pl, dict):
        for nm, info in raw_pl.items():
            if nm in names and isinstance(info, dict):
                try:
                    idx[nm] = (float(info.get('longitude')), float(info.get('latitude', 0.0) or 0.0))
                except Exception:
                    continue
    elif isinstance(raw_pl, list):
        for info in raw_pl:
            if isinstance(info, dict) and info.get('planet') in names:
                try:
                    idx[info['planet']] = (float(info.get('longitude')), float(info.get('latitude', 0.0) or 0.0))
                except Exception:
                    continue
    # Cusps for angles
    cusps = natal_cd.get('houses') or natal_cd.get('house_cusps') or []
    lon_mc = float(cusps[9]) if isinstance(cusps, list) and len(cusps) >= 10 else None
    ra_mc = None
    if lon_mc is not None:
        ra_mc, _ = ecl_to_eq_ra_dec(lon_mc, 0.0)
    oa_asc = None
    if ra_mc is not None:
        oa_asc = _wrap24h_deg(ra_mc + 90.0)

    out: List[Dict[str, Any]] = []
    for nm, (lon, lat) in idx.items():
        for ang in aspects:
            alon, alat = _aspect_point_on_excentric(lon, lat, ang, planet_name=nm)
            ra_as, dec_as = ecl_to_eq_ra_dec(alon, alat)
            # To angles
            if ra_mc is not None and oa_asc is not None:
                arc_mc = _normalize_positive_arc(ra_as - ra_mc)
                arc_asc = _normalize_positive_arc(oblique_ascension(ra_as, dec_as, latitude_deg) - oa_asc)
                out.append({'significator': 'MC', 'promittor': f'{nm} {int(ang)}°', 'aspect': 'Aspect', 'arc_deg': round(arc_mc,6), 'age_years': round(arc_mc/NAIBOD_DEG_PER_YEAR,6), 'type':'direct'})
                out.append({'significator': 'Asc', 'promittor': f'{nm} {int(ang)}°', 'aspect': 'Aspect', 'arc_deg': round(arc_asc,6), 'age_years': round(arc_asc/NAIBOD_DEG_PER_YEAR,6), 'type':'direct'})
                carc_mc = _normalize_positive_arc(360.0 - arc_mc)
                carc_asc = _normalize_positive_arc(360.0 - arc_asc)
                out.append({'significator': 'MC', 'promittor': f'{nm} {int(ang)}°', 'aspect': 'Aspect', 'arc_deg': round(carc_mc,6), 'age_years': round(carc_mc/NAIBOD_DEG_PER_YEAR,6), 'type':'converse'})
                out.append({'significator': 'Asc', 'promittor': f'{nm} {int(ang)}°', 'aspect': 'Aspect', 'arc_deg': round(carc_asc,6), 'age_years': round(carc_asc/NAIBOD_DEG_PER_YEAR,6), 'type':'converse'})
            # To other planets (OA under φ approx)
            for other, (ol, ot) in idx.items():
                if other == nm: continue
                raO, decO = ecl_to_eq_ra_dec(ol, ot)
                oaO = oblique_ascension(raO, decO, latitude_deg)
                oaA = oblique_ascension(ra_as, dec_as, latitude_deg)
                arc = _normalize_positive_arc(oaA - oaO)
                carc = _normalize_positive_arc(360.0 - arc)
                out.append({'significator': other, 'promittor': f'{nm} {int(ang)}°', 'aspect': 'Aspect', 'arc_deg': round(arc,6), 'age_years': round(arc/NAIBOD_DEG_PER_YEAR,6), 'type':'direct'})
                out.append({'significator': other, 'promittor': f'{nm} {int(ang)}°', 'aspect': 'Aspect', 'arc_deg': round(carc,6), 'age_years': round(carc/NAIBOD_DEG_PER_YEAR,6), 'type':'converse'})
    return out


# ----------------- Bounds/Terms (Egyptian) -----------------

_TERMS = {
    # sign -> [(lord, length_deg), ...] totalling 30
    'Aries': [('Jupiter',6),('Venus',6),('Mercury',8),('Mars',5),('Saturn',5)],
    'Taurus':[('Venus',8),('Mercury',6),('Jupiter',8),('Saturn',5),('Mars',3)],
    'Gemini':[('Mercury',6),('Jupiter',6),('Venus',5),('Mars',7),('Saturn',6)],
    'Cancer':[('Mars',7),('Venus',6),('Mercury',6),('Jupiter',7),('Saturn',4)],
    'Leo':   [('Jupiter',6),('Venus',5),('Saturn',7),('Mercury',6),('Mars',6)],
    'Virgo': [('Mercury',7),('Venus',10),('Jupiter',4),('Mars',7),('Saturn',2)],
    'Libra': [('Saturn',6),('Mercury',8),('Jupiter',7),('Venus',7),('Mars',2)],
    'Scorpio':[('Mars',7),('Venus',4),('Mercury',8),('Jupiter',5),('Saturn',6)],
    'Sagittarius':[('Jupiter',12),('Venus',5),('Mercury',4),('Saturn',5),('Mars',4)],
    'Capricorn':[('Mercury',7),('Jupiter',7),('Venus',8),('Saturn',4),('Mars',4)],
    'Aquarius':[('Mercury',7),('Venus',6),('Jupiter',7),('Mars',5),('Saturn',5)],
    'Pisces':[('Venus',12),('Jupiter',4),('Mercury',3),('Mars',9),('Saturn',2)],
}


def _sign_of(lon_deg: float) -> str:
    names = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
    return names[int(_wrap360(lon_deg)//30)]


def current_bound(sign: str, degree_in_sign: float) -> Dict[str, Any]:
    seq = _TERMS.get(sign)
    if not seq:
        return {'lord': None, 'start_deg': 0.0, 'end_deg': 30.0}
    acc = 0.0
    prev = 0.0
    for lord, length in seq:
        acc += float(length)
        if degree_in_sign < acc:
            return {'lord': lord, 'start_deg': prev, 'end_deg': acc}
        prev = acc
    return {'lord': seq[-1][0], 'start_deg': prev, 'end_deg': 30.0}


def compute_natal_bounds(natal_cd: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    raw = natal_cd.get('planets') or {}
    items = []
    if isinstance(raw, dict):
        for nm, info in raw.items():
            if nm in CLASSICAL and isinstance(info, dict):
                try:
                    lon = float(info.get('longitude'))
                    deg_in_sign = lon % 30.0
                    sign = _sign_of(lon)
                    out[nm] = {'sign': sign, 'degree_in_sign': deg_in_sign, 'bound': current_bound(sign, deg_in_sign)}
                except Exception:
                    continue
    elif isinstance(raw, list):
        for info in raw:
            if isinstance(info, dict) and info.get('planet') in CLASSICAL:
                try:
                    lon = float(info.get('longitude'))
                    deg_in_sign = lon % 30.0
                    sign = _sign_of(lon)
                    out[info['planet']] = {'sign': sign, 'degree_in_sign': deg_in_sign, 'bound': current_bound(sign, deg_in_sign)}
                except Exception:
                    continue
    return out


def compute_pd_full(natal_cd: Dict[str, Any], latitude_deg: float, include_modern: bool = False,
                    include_angles: bool = True, include_planets: bool = True,
                    include_aspects: bool = True, aspects: Optional[List[float]] = None) -> Dict[str, Any]:
    res: Dict[str, Any] = {'directions': []}
    dirs: List[Dict[str, Any]] = []
    if include_angles:
        dirs.extend(compute_pd_to_angles(natal_cd, latitude_deg))
    if include_planets:
        # Prefer Regiomontanus CP pole method for planet→planet
        dirs.extend(compute_pd_planet_to_planet_regio(natal_cd, latitude_deg, include_modern=include_modern))
    if include_aspects:
        dirs.extend(compute_pd_aspects(natal_cd, latitude_deg, include_modern=include_modern, aspects=aspects))
    # sort by age
    try:
        dirs.sort(key=lambda d: float(d.get('age_years') or 0.0))
    except Exception:
        pass
    res['directions'] = dirs
    res['bounds'] = compute_natal_bounds(natal_cd)
    # Optional: distributions timeline per significator (approximate zodiacal measure)
    try:
        res['distributions'] = compute_distribution_timelines(natal_cd)
    except Exception:
        res['distributions'] = {}
    return res


def compute_distribution_timelines(natal_cd: Dict[str, Any], years_max: int = 60) -> Dict[str, Any]:
    """Approximate distribution timeline (terms) for classical planets.

    We step zodiacal term boundaries forward and convert degrees to years via
    Naibod (1° RA ≈ 1.0146 years), suitable as a planning aid, not strict.
    """
    out: Dict[str, Any] = {}
    raw = natal_cd.get('planets') or {}
    items = []
    if isinstance(raw, dict):
        items = [{'planet': nm, **info} for nm, info in raw.items() if nm in CLASSICAL and isinstance(info, dict)]
    elif isinstance(raw, list):
        items = [info for info in raw if isinstance(info, dict) and info.get('planet') in CLASSICAL]
    years_per_deg = 1.0/NAIBOD_DEG_PER_YEAR  # ≈ 1.01468
    for info in items:
        nm = info.get('planet')
        try:
            lon = float(info.get('longitude'))
        except Exception:
            continue
        sign = _sign_of(lon)
        deg_in = lon % 30.0
        remaining = []
        # build sequence starting at current degree within current sign, then through following signs
        seq: List[Tuple[str,float]] = []
        # current sign boundaries
        terms = _TERMS.get(sign, [])
        acc = 0.0
        for lord, ln in terms:
            nxt = acc + float(ln)
            if deg_in < nxt:
                seq.append((f"Enter {lord} (within {sign})", nxt - deg_in))
        # next signs (wrap few signs, limited by years_max)
        signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
        idx = signs.index(sign)
        total_years = 0.0
        k = 1
        while total_years < years_max and k < 36:
            sname = signs[(idx + k) % 12]
            # terms in next sign
            for lord, ln in _TERMS.get(sname, []):
                seq.append((f"Enter {lord} ({sname})", float(ln)))
            k += 1
            total_years = sum(d for (_,d) in seq) * years_per_deg
        # convert to cumulative ages
        ages = []
        cumul_deg = 0.0
        for label, ddeg in seq:
            cumul_deg += ddeg
            ages.append({'label': label, 'age_years': round(cumul_deg * years_per_deg, 3)})
        out[nm] = ages
    return out
