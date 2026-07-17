# -*- coding: utf-8 -*-
"""
Morin-style aspect computation with latitude correction (Full Morin).

Implements the seven-aspect set (0°, 30°, 60°, 90°, 120°, 150°, 180°)
using an apparent-orbit great-circle model per planet. For each planet:

- Build the great circle with inclination equal to the planet's maximum
  attainable latitude in the current hemisphere (constant inclination map
  per classical planet; Moon uses its variable ~5.145°).
- Determine the great-circle plane orientation (normal vector) that passes
  through the current geocentric position and matches the observed latitude
  trend (increasing/decreasing) over a short forward step.
- Measure aspect arcs along this great circle by rotating the planet's unit
  vector around the plane normal by the aspect angle (±A) to obtain the
  corrected "aspect ray" directions.
- Convert these corrected directions back to ecliptic coords and select the
  branch (dexter/sinister) that minimizes the 3D angular separation to the
  other planet's direction.

Activation and flags per Morin:
- Orbs of virtue: fixed per planet from visibility thresholds (deg).
- Active when separation to corrected ray ≤ combined orbs (sum of orbs).
- Partile when separation ≤ sum of semi-diameters (deg).
- Complete platic when separation ≤ min(orbA, orbB).
- Phase (applying/separating/stationary) via shrink/grow of separation over
  a small forward step.

Notes:
- This module targets classical planets (Sun–Saturn). It does not alter the
  existing horary engine logic and is opt-in via API query.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Tuple
import math

from swisseph_state import swisseph as swe


ASPECT_SET: List[Tuple[float, str]] = [
    (0.0, "Conjunction"),
    (30.0, "Semi-sextile"),
    (60.0, "Sextile"),
    (90.0, "Square"),
    (120.0, "Trine"),
    (150.0, "Quincunx"),
    (180.0, "Opposition"),
]

CLASSICAL: List[str] = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

# Morin orbs of virtue (deg) based on visibility thresholds
ORB_OF_VIRTUE: Dict[str, float] = {
    "Sun": 18.0,
    "Moon": 12.0,
    "Venus": 13.0,
    "Jupiter": 8.0,
    "Saturn": 7.0,
    "Mars": 6.5,
    "Mercury": 8.0,
}

# Semi-diameter (deg) approximate fallbacks for partile checks
SEMI_DIAMETER_DEG: Dict[str, float] = {
    "Sun": 0.2667,
    "Moon": 0.2725,
    "Mercury": 0.0040,
    "Venus": 0.0060,
    "Mars": 0.0035,
    "Jupiter": 0.0200,
    "Saturn": 0.0090,
}

# Apparent orbit inclination per planet (deg). Moon uses ~5.145°.
APPARENT_INCL_DEG: Dict[str, float] = {
    "Sun": 0.0,
    "Moon": 5.145,
    "Mercury": 7.0,
    "Venus": 3.3947,
    "Mars": 1.8506,
    "Jupiter": 1.304,
    "Saturn": 2.485,
}


def _norm360(x: float) -> float:
    return x % 360.0


def _rad(x: float) -> float:
    return math.radians(float(x))


def _deg(x: float) -> float:
    return math.degrees(float(x))


def _sph_to_vec(lon_deg: float, lat_deg: float) -> Tuple[float, float, float]:
    lon = _rad(lon_deg)
    lat = _rad(lat_deg)
    cl = math.cos(lat)
    return (cl * math.cos(lon), cl * math.sin(lon), math.sin(lat))


def _vec_to_sph(v: Tuple[float, float, float]) -> Tuple[float, float]:
    x, y, z = v
    lon = math.degrees(math.atan2(y, x)) % 360.0
    lat = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    return lon, lat


def _dot(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _cross(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


def _norm(v: Tuple[float, float, float]) -> float:
    return math.sqrt(_dot(v, v))


def _unit(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    n = _norm(v)
    if n == 0:
        return (0.0, 0.0, 0.0)
    return (v[0]/n, v[1]/n, v[2]/n)


def _rotate(v: Tuple[float, float, float], axis: Tuple[float, float, float], deg_angle: float) -> Tuple[float, float, float]:
    """Rotate vector v around unit axis by deg_angle using Rodrigues' formula."""
    a = _unit(axis)
    theta = _rad(deg_angle)
    c, s = math.cos(theta), math.sin(theta)
    axv = _cross(a, v)
    adp = _dot(a, v)
    # Rodrigues: v' = v*c + (a x v)*s + a*(a·v)*(1-c)
    return (
        v[0]*c + axv[0]*s + a[0]*adp*(1-c),
        v[1]*c + axv[1]*s + a[1]*adp*(1-c),
        v[2]*c + axv[2]*s + a[2]*adp*(1-c),
    )


def _planet_id(name: str) -> int:
    return getattr(swe, name.upper(), None)


def _cache_jd(jd_ut: float) -> float:
    return round(float(jd_ut), 9)


@lru_cache(maxsize=4096)
def _lon_lat_cached(jd_ut: float, name: str) -> Tuple[float, float]:
    pid = _planet_id(name)
    if pid is None:
        return 0.0, 0.0
    # Ecliptic coordinates (geocentric true position)
    pos, _ = swe.calc_ut(jd_ut, pid, swe.FLG_SWIEPH)
    # pos = [lon, lat, dist, lon_speed, lat_speed, dist_speed]
    return float(pos[0]) % 360.0, float(pos[1])


def _lon_lat_at(jd_ut: float, name: str) -> Tuple[float, float]:
    return _lon_lat_cached(_cache_jd(jd_ut), str(name))


@lru_cache(maxsize=4096)
def _equatorial_declination_at(jd_ut: float, name: str) -> float:
    pid = _planet_id(name)
    if pid is None:
        return 0.0
    pos, _ = swe.calc_ut(jd_ut, pid, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
    return float(pos[1])


def _semi_diameter_deg(name: str, jd_ut: float) -> float:
    return _semi_diameter_cached(str(name), _cache_jd(jd_ut))


@lru_cache(maxsize=4096)
def _semi_diameter_cached(name: str, jd_ut: float) -> float:
    # Try ephemeris apparent diameter when available (convert arcsec → deg)
    try:
        pid = _planet_id(name)
        if pid is not None:
            # swe.pheno_ut returns [phase angle, phase frac, elongation, apparent diameter, mag]
            vals = swe.pheno_ut(jd_ut, pid, 0)
            if isinstance(vals, (list, tuple)) and len(vals) >= 4:
                diam_arcsec = float(vals[3])
                if diam_arcsec > 0:
                    return (diam_arcsec / 2.0) / 3600.0
    except Exception:
        pass
    return float(SEMI_DIAMETER_DEG.get(name, 0.005))


def _apparent_inclination(name: str, current_lat_deg: float) -> float:
    """Return inclination i (deg) for great-circle model, ensuring i ≥ |β|."""
    base = float(APPARENT_INCL_DEG.get(name, 0.0))
    lat_abs = abs(float(current_lat_deg))
    return max(base, lat_abs)


def _build_plane_normal(r0: Tuple[float, float, float], lat_now: float, lat_future: float, incl_deg: float) -> Tuple[float, float, float]:
    """Compute great-circle plane normal n for given position and inclination.

    Constraints: n·r0 = 0 (plane passes through r0) and the angle between n and
    z_hat equals incl (i). Among the two solutions, choose the one whose tangent
    direction (n × r0) matches the observed latitude trend.
    """
    z_hat = (0.0, 0.0, 1.0)
    # Basis for plane ⟂ r0
    e1 = _cross(z_hat, r0)
    if _norm(e1) < 1e-9:
        e1 = _cross((1.0, 0.0, 0.0), r0)
    e1 = _unit(e1)
    e2 = _unit(_cross(r0, e1))
    s1, s2 = _dot(e1, z_hat), _dot(e2, z_hat)
    s_norm = math.sqrt(s1*s1 + s2*s2)  # = |cos(lat_now)|
    cosi = math.cos(_rad(incl_deg))
    # Guard for numerical feasibility
    if s_norm < 1e-9:
        s_norm = 1e-9
    # If cosi exceeds available projection length, clamp a little inside
    if abs(cosi) > s_norm:
        cosi = math.copysign(s_norm * 0.999999, cosi)
    # Foot along projection
    a0 = (cosi * s1) / (s_norm * s_norm)
    b0 = (cosi * s2) / (s_norm * s_norm)
    # Perpendicular direction in (a,b)
    px, py = -s2, s1
    denom = s_norm
    tmag_sq = 1.0 - (cosi / s_norm) ** 2
    tmag = math.sqrt(max(0.0, tmag_sq)) / max(1e-12, denom)
    # Two unit solutions in (a,b)
    a1, b1 = a0 + tmag * px, b0 + tmag * py
    a2, b2 = a0 - tmag * px, b0 - tmag * py
    n1 = _unit((e1[0]*a1 + e2[0]*b1, e1[1]*a1 + e2[1]*b1, e1[2]*a1 + e2[2]*b1))
    n2 = _unit((e1[0]*a2 + e2[0]*b2, e1[1]*a2 + e2[1]*b2, e1[2]*a2 + e2[2]*b2))
    # Trend selection: choose n so that (n × r0) raises/lowers z as observed
    lat_trend_up = (lat_future - lat_now) >= 0.0
    t1 = _cross(n1, r0)
    t2 = _cross(n2, r0)
    if (_dot(t1, z_hat) >= 0.0) == lat_trend_up:
        return n1
    else:
        return n2


def _angular_sep_deg(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    v = max(-1.0, min(1.0, _dot(_unit(a), _unit(b))))
    return _deg(math.acos(v))


def _dexter_sinister(lon1: float, lon2: float) -> str:
    d = (_norm360(lon2 - lon1) + 360.0) % 360.0
    return 'sinister' if 0.0 < d < 180.0 else 'dexter'


def _jd_from_iso(timestamp_iso: str) -> float:
    try:
        import datetime as _dt
        dt = _dt.datetime.fromisoformat(timestamp_iso.replace('Z', '+00:00')).astimezone(_dt.timezone.utc)
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0 + dt.second / 3600.0)
    except Exception:
        # Fallback to 'now' in UT if parsing fails
        import datetime as _dt
        dt = _dt.datetime.now(_dt.timezone.utc)
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0 + dt.second / 3600.0)


def _is_retrograde(jd_ut: float, name: str) -> bool:
    return _retrograde_cached(str(name), _cache_jd(jd_ut))


@lru_cache(maxsize=4096)
def _retrograde_cached(name: str, jd_ut: float) -> bool:
    """Approximate retrograde by checking forward motion sign over a small dt."""
    try:
        lon0, _ = _lon_lat_at(jd_ut, name)
        lon1, _ = _lon_lat_at(jd_ut + 1.0/24.0, name)  # +1h
        d = ((lon1 - lon0 + 540.0) % 360.0) - 180.0
        return d < 0.0
    except Exception:
        return False


def _aspect_angle_from_name(label: str) -> float:
    k = (label or '').strip().lower()
    if 'conj' in k: return 0.0
    if 'semi' in k: return 30.0
    if 'sex' in k: return 60.0
    if 'square' in k: return 90.0
    if 'trine' in k: return 120.0
    if 'quin' in k: return 150.0
    if 'opp' in k: return 180.0
    return 0.0


def _simulate_application_type(nameA: str, nameB: str, angle: float, jd0: float, max_days: float = 60.0) -> str:
    """Simulate forward to classify application type: complete | incomplete | mutual.

    - complete: reach partile threshold (sum of semi-diameters) before retrograde change.
    - incomplete: retrograde state changes before partile or horizon exceeded.
    - mutual: both retrograde at start and applying (orb shrinking).
    Uses ecliptic-only separation for efficiency.
    """
    # Initial retrograde states
    rA0 = _is_retrograde(jd0, nameA)
    rB0 = _is_retrograde(jd0, nameB)
    # partile threshold
    sd_sum = _semi_diameter_deg(nameA, jd0) + _semi_diameter_deg(nameB, jd0)
    # Helper: current orb to target aspect (ecliptic only)
    def orb_to(jd: float) -> float:
        lonA, _ = _lon_lat_at(jd, nameA)
        lonB, _ = _lon_lat_at(jd, nameB)
        sep = abs(((lonA - lonB + 180.0) % 360.0) - 180.0)
        o = abs(sep - angle)
        return o if o <= 180.0 else 360.0 - o
    # initial check for applying
    o0 = orb_to(jd0)
    o1 = orb_to(jd0 + 0.5)  # +12h
    applying = o1 < o0
    if rA0 and rB0 and applying:
        # label mutual if both retrograde initially and approaching
        tag = 'mutual'
    else:
        tag = 'complete'  # default optimistic
    # scan forward
    step = 0.5  # days
    t = 0.0
    last_orb = o0
    while t <= max_days:
        jd = jd0 + t
        o = orb_to(jd)
        if o <= sd_sum + 1e-6:
            return tag if tag == 'mutual' else 'complete'
        # detect retrograde change for either
        if _is_retrograde(jd, nameA) != rA0 or _is_retrograde(jd, nameB) != rB0:
            return 'incomplete'
        # break if orbs are diverging for long
        if t > 2.0 and o > last_orb + 0.25:
            # not converging meaningfully
            pass
        last_orb = o
        t += step
    return 'incomplete'


def compute_morin_aspects(chart_data: Dict[str, Any], timestamp_iso: str, dt_hours: float = 0.5) -> List[Dict[str, Any]]:
    """Compute Morin-mode aspects for classical planets.

    Returns rows: { planet1, planet2, aspect, orb, max_orb, partile, complete_platic,
                     direction, phase } sorted by orb ascending.
    """
    if swe is None:
        return []
    try:
        jd0 = _jd_from_iso(timestamp_iso)
    except Exception:
        return []
    dt_days = float(dt_hours) / 24.0

    # Gather current positions (lon, lat) and future positions for trend
    now_ll: Dict[str, Tuple[float, float]] = {}
    fut_ll: Dict[str, Tuple[float, float]] = {}
    fut2_ll: Dict[str, Tuple[float, float]] = {}
    sd_map: Dict[str, float] = {}
    for name in CLASSICAL:
        now_ll[name] = _lon_lat_at(jd0, name)
        fut_ll[name] = _lon_lat_at(jd0 + dt_days, name)
        fut2_ll[name] = _lon_lat_at(jd0 + 2*dt_days, name)
        sd_map[name] = _semi_diameter_deg(name, jd0)

    out: List[Dict[str, Any]] = []
    N = len(CLASSICAL)
    for i in range(N):
        A = CLASSICAL[i]
        lonA, latA = now_ll[A]
        lonAf, latAf = fut_ll[A]
        rA = _unit(_sph_to_vec(lonA, latA))
        # Build great-circle plane normal for A
        inclA = _apparent_inclination(A, latA)
        nA = _build_plane_normal(rA, latA, latAf, inclA)

        for j in range(i + 1, N):
            B = CLASSICAL[j]
            lonB, latB = now_ll[B]
            rB = _unit(_sph_to_vec(lonB, latB))

            for ang, label in ASPECT_SET:
                # Two branches along great circle
                r_pos = _unit(_rotate(rA, nA, +ang))
                r_neg = _unit(_rotate(rA, nA, -ang))
                sep_pos = _angular_sep_deg(r_pos, rB)
                sep_neg = _angular_sep_deg(r_neg, rB)
                if sep_pos <= sep_neg:
                    sep = sep_pos
                    branch = +1
                else:
                    sep = sep_neg
                    branch = -1

                # Gate by combined moieties (Morin half-orbs)
                orbA = float(ORB_OF_VIRTUE.get(A, 0.0))
                orbB = float(ORB_OF_VIRTUE.get(B, 0.0))
                moietyA = orbA / 2.0
                moietyB = orbB / 2.0
                combined = moietyA + moietyB
                if sep > combined:
                    continue

                # Partile and platic checks
                sd_sum = sd_map.get(A, 0.0) + sd_map.get(B, 0.0)
                partile = sep <= sd_sum
                complete_platic = (sep <= min(moietyA, moietyB))

                # Phase via forward step (recompute A/B positions & A's plane at +dt)
                lonA2, latA2 = fut_ll[A]
                rA2 = _unit(_sph_to_vec(lonA2, latA2))
                lonB2, latB2 = fut_ll[B]
                rB2 = _unit(_sph_to_vec(lonB2, latB2))
                nA2 = _build_plane_normal(rA2, latA2, fut2_ll[A][1], inclA)
                r_branch_future = _unit(_rotate(rA2, nA2, +ang if branch > 0 else -ang))
                sep_future = _angular_sep_deg(r_branch_future, rB2)
                if sep_future < sep - 1e-6:
                    phase = 'applying'
                elif sep_future > sep + 1e-6:
                    phase = 'separating'
                else:
                    phase = 'stationary'

                out.append({
                    'planet1': A,
                    'planet2': B,
                    'aspect': label,
                    'orb': round(float(sep), 4),
                    'max_orb': round(float(combined), 4),
                    'partile': bool(partile),
                    'complete_platic': bool(complete_platic),
                    'direction': _dexter_sinister(lonA, lonB),
                    'phase': phase,
                })

    out.sort(key=lambda r: (abs(float(r.get('orb', 999.0))), 0 if r.get('partile') else 1, 0 if r.get('complete_platic') else 1))
    return out


def compute_morin_antiscia(timestamp_iso: str, orb_deg: float = 1.0) -> List[Dict[str, Any]]:
    """Compute Morin-style antiscia hits: planets near ecliptic longitudes that share
    the same declination as another planet (β=0, δ(λ) = arcsin(sin ε sin λ)).

    Returns rows: { planet1, planet2, aspect: 'Antiscia', orb, max_orb } sorted by orb.
    """
    if swe is None:
        return []
    jd = _cache_jd(_jd_from_iso(timestamp_iso))
    # Obliquity of the ecliptic (mean) in degrees
    eps_deg = 23.4392911
    seps = math.sin(_rad(eps_deg))
    # Get current ecliptic positions and declinations
    lon_lat: Dict[str, Tuple[float, float]] = {}
    decl: Dict[str, float] = {}
    for name in CLASSICAL:
        lon, lat = _lon_lat_at(jd, name)
        lon_lat[name] = (lon, lat)
        try:
            decl[name] = _equatorial_declination_at(jd, name)
        except Exception:
            decl[name] = 0.0

    out: List[Dict[str, Any]] = []
    seen: set = set()
    for i, A in enumerate(CLASSICAL):
        dA = decl.get(A, 0.0)
        s = None
        try:
            s = math.sin(_rad(dA)) / seps
        except Exception:
            s = None
        if s is None or s < -1.0 or s > 1.0:
            continue
        # Two antiscia longitudes on the ecliptic (β=0)
        lam0 = _deg(math.asin(max(-1.0, min(1.0, s))))
        lam1 = (180.0 - lam0) % 360.0
        lam0 = _norm360(lam0)
        P0 = _unit(_sph_to_vec(lam0, 0.0))
        P1 = _unit(_sph_to_vec(lam1, 0.0))
        for j, B in enumerate(CLASSICAL):
            if j == i:
                continue
            lonB, latB = lon_lat[B]
            rB = _unit(_sph_to_vec(lonB, latB))
            sep0 = _angular_sep_deg(P0, rB)
            sep1 = _angular_sep_deg(P1, rB)
            sep = min(sep0, sep1)
            if sep <= float(orb_deg) + 1e-9:
                # Deduplicate unordered pairs by sorted planet names
                key = tuple(sorted((A, B))) + (round(sep, 4),)
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    'planet1': A,
                    'planet2': B,
                    'aspect': 'Antiscia',
                    'orb': round(float(sep), 4),
                    'max_orb': float(orb_deg),
                })
    out.sort(key=lambda r: abs(float(r.get('orb', 999.0))))
    return out


def compute_morin_contra_antiscia(timestamp_iso: str, orb_deg: float = 1.0) -> List[Dict[str, Any]]:
    """Compute Morin-style contra-antiscia hits: planets near ecliptic longitudes
    that have the opposite declination of another planet (equal magnitude, opposite sign).

    For ecliptic longitudes (β=0), declination δ(λ) = arcsin(sin ε sin λ). Points with
    opposite declination satisfy sin λ' = - sin λ, which occurs at λ' = -λ and λ' = 180° + λ.

    Returns rows: { planet1, planet2, aspect: 'Contra-antiscia', orb, max_orb } sorted by orb.
    """
    if swe is None:
        return []
    jd = _cache_jd(_jd_from_iso(timestamp_iso))
    eps_deg = 23.4392911
    seps = math.sin(_rad(eps_deg))

    # Current positions and declinations
    lon_lat: Dict[str, Tuple[float, float]] = {}
    decl: Dict[str, float] = {}
    for name in CLASSICAL:
        lon, lat = _lon_lat_at(jd, name)
        lon_lat[name] = (lon, lat)
        try:
            decl[name] = _equatorial_declination_at(jd, name)
        except Exception:
            decl[name] = 0.0

    out: List[Dict[str, Any]] = []
    seen: set = set()
    for i, A in enumerate(CLASSICAL):
        dA = decl.get(A, 0.0)
        try:
            s = math.sin(_rad(dA)) / seps
        except Exception:
            s = None
        if s is None or s < -1.0 or s > 1.0:
            continue
        # Antiscia base longitudes for +|δ| (as in compute_morin_antiscia)
        lam0 = _deg(math.asin(max(-1.0, min(1.0, s)))) % 360.0
        lam1 = (180.0 - lam0) % 360.0
        # Contra-antiscia longitudes (opposite declination): -lam0, 180+lam0
        cl0 = (-lam0) % 360.0
        cl1 = (180.0 + lam0) % 360.0
        P0 = _unit(_sph_to_vec(cl0, 0.0))
        P1 = _unit(_sph_to_vec(cl1, 0.0))
        for j, B in enumerate(CLASSICAL):
            if j == i:
                continue
            lonB, latB = lon_lat[B]
            rB = _unit(_sph_to_vec(lonB, latB))
            sep0 = _angular_sep_deg(P0, rB)
            sep1 = _angular_sep_deg(P1, rB)
            sep = min(sep0, sep1)
            if sep <= float(orb_deg) + 1e-9:
                key = tuple(sorted((A, B))) + (round(sep, 4),)
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    'planet1': A,
                    'planet2': B,
                    'aspect': 'Contra-antiscia',
                    'orb': round(float(sep), 4),
                    'max_orb': float(orb_deg),
                })
    out.sort(key=lambda r: abs(float(r.get('orb', 999.0))))
    return out


def compute_morin_combustion(chart_data: Dict[str, Any], timestamp_iso: str) -> List[Dict[str, Any]]:
    """Compute Morin-style combustion status for classical planets.

    Status: 'cazimi' | 'combust' | 'under_beams' | 'free'
    Using Sun orb = 18°, planet orbs from ORB_OF_VIRTUE, and Sun radius ~0.2667° for cazimi.
    """
    if swe is None:
        return []
    try:
        jd0 = _jd_from_iso(timestamp_iso)
    except Exception:
        return []
    # Gather sun lon
    lonS, latS = _lon_lat_at(jd0, 'Sun')

    # Collect classical planet lon
    planets = []
    try:
        pl = chart_data.get('planets') or []
        if isinstance(pl, dict):
            for name, info in pl.items():
                if name in CLASSICAL and name != 'Sun' and isinstance(info, dict):
                    planets.append(name)
        elif isinstance(pl, list):
            for p in pl:
                nm = p.get('planet')
                if nm in CLASSICAL and nm != 'Sun':
                    planets.append(nm)
    except Exception:
        planets = [n for n in CLASSICAL if n != 'Sun']

    out: List[Dict[str, Any]] = []
    sun_orb = 18.0
    sun_radius = 0.2667  # deg (~16')
    for name in planets:
        try:
            lonP, latP = _lon_lat_at(jd0, name)
            # Small-circle separation along ecliptic only (consistent with Morin orb scheme)
            d = abs(((lonP - lonS + 180.0) % 360.0) - 180.0)
            # symmetric around 180, use smaller
            if d > 180.0:
                d = 360.0 - d
            p_orb = float(ORB_OF_VIRTUE.get(name, 0.0))
            combustion_limit = max(0.0, sun_orb - p_orb)
            status = 'free'
            exact_cazimi = False
            if d <= sun_radius:
                status = 'cazimi'
                exact_cazimi = True
            elif d <= combustion_limit:
                status = 'combust'
            elif d <= sun_orb:
                status = 'under_beams'
            out.append({
                'planet': name,
                'distance_deg': round(float(d), 3),
                'status': status,
                'combustion_limit_deg': round(float(combustion_limit), 3),
                'under_beams_limit_deg': sun_orb,
                'exact_cazimi': exact_cazimi,
            })
        except Exception:
            continue
    return out


def compute_morin_patterns(chart_data: Dict[str, Any], timestamp_iso: str, morin_aspects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute simplified Morin-style complex patterns using Morin aspects.

    Patterns:
      - translation: middle planet separating from A and applying to C, A and C not in active aspect
      - besiegement: for each X, nearest active before and after bracketing longitudes
      - doryphory: planets attending Sun/Moon within combined orb (active Morin aspect), add orientation and angular flag
    """
    # Normalize chart planet longitudes and houses
    try:
        pl = chart_data.get('planets') or []
    except Exception:
        pl = []
    planet_lon: Dict[str, float] = {}
    planet_house: Dict[str, int] = {}
    if isinstance(pl, dict):
        for nm, info in pl.items():
            if isinstance(info, dict):
                try:
                    planet_lon[str(nm)] = float(info.get('longitude', 0.0))
                except Exception:
                    planet_lon[str(nm)] = 0.0
                try:
                    planet_house[str(nm)] = int(info.get('house', 0))
                except Exception:
                    planet_house[str(nm)] = 0
    elif isinstance(pl, list):
        for info in pl:
            if isinstance(info, dict) and info.get('planet'):
                nm = str(info.get('planet'))
                try:
                    planet_lon[nm] = float(info.get('longitude', 0.0))
                except Exception:
                    planet_lon[nm] = 0.0
                try:
                    planet_house[nm] = int(info.get('house', 0))
                except Exception:
                    planet_house[nm] = 0

    # Build quick access from morin_aspects
    by_pair: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in morin_aspects or []:
        a = str(row.get('planet1'))
        b = str(row.get('planet2'))
        if not a or not b:
            continue
        key = tuple(sorted((a, b)))
        by_pair[key] = row

    # Translation: middle M separates from A and applies to C; A and C not directly in active
    trans = []
    # Pre-index applying/separating directions relative to middle
    applies_from = {}  # M -> set(C)
    separates_from = {}  # M -> set(A)
    for row in morin_aspects or []:
        p1 = str(row.get('planet1'))
        p2 = str(row.get('planet2'))
        ph = str(row.get('phase') or '').lower()
        # Store symmetric for ease
        if ph == 'applying':
            applies_from.setdefault(p1, set()).add(p2)
            applies_from.setdefault(p2, set()).add(p1)
        elif ph == 'separating':
            separates_from.setdefault(p1, set()).add(p2)
            separates_from.setdefault(p2, set()).add(p1)
    for M, sep_set in separates_from.items():
        app_set = applies_from.get(M) or set()
        if not app_set or not sep_set:
            continue
        for A in sep_set:
            for C in app_set:
                if A == C:
                    continue
                key = tuple(sorted((A, C)))
                if key in by_pair:
                    # A and C already directly connected (active Morin aspect) – skip
                    continue
                # Comprehensive: require strong legs (complete platic or partile) on both legs
                leg1 = by_pair.get(tuple(sorted((M, A))))
                leg2 = by_pair.get(tuple(sorted((M, C))))
                if not leg1 or not leg2:
                    continue
                strong1 = leg1.get('partile') or leg1.get('complete_platic')
                strong2 = leg2.get('partile') or leg2.get('complete_platic')
                if not (strong1 and strong2):
                    continue
                # application type via forward simulation on the applying leg (M→C)
                ang_to = _aspect_angle_from_name(leg2.get('aspect'))
                app_type = _simulate_application_type(M, C, ang_to, _jd_from_iso(timestamp_iso)) if ang_to is not None else None
                trans.append({
                    'middle': M,
                    'from': A,
                    'to': C,
                    'from_leg': {
                        'aspect': leg1.get('aspect'),
                        'orb': leg1.get('orb'),
                        'phase': leg1.get('phase'),
                        'partile': leg1.get('partile'),
                        'complete_platic': leg1.get('complete_platic'),
                    },
                    'to_leg': {
                        'aspect': leg2.get('aspect'),
                        'orb': leg2.get('orb'),
                        'phase': leg2.get('phase'),
                        'partile': leg2.get('partile'),
                        'complete_platic': leg2.get('complete_platic'),
                        'application_type': app_type,
                    },
                })

    # Besiegement: for each X, nearest before and after planets with active Morin aspects
    def _delta(a, b):
        return ((planet_lon.get(b, 0.0) - planet_lon.get(a, 0.0) + 360.0) % 360.0)
    besieged = []
    # build adjacency list
    neighbors: Dict[str, List[str]] = {}
    for row in morin_aspects or []:
        a = str(row.get('planet1'))
        b = str(row.get('planet2'))
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)
    # Comprehensive besiegement (by malefics via aspect 'rays')
    malefics = {'Mars', 'Saturn'}
    for X, arr in neighbors.items():
        # malefics that aspect X
        mal_list = [Y for Y in arr if Y in malefics]
        if len(mal_list) < 2:
            continue
        # choose before and after among malefics by zodiac order
        before = None; after = None
        min_before = 1e9; min_after = 1e9
        for Y in mal_list:
            d = _delta(X, Y)
            if d == 0:
                continue
            if 0 < d < min_after:
                min_after = d; after = Y
            if 0 < (360.0 - d) < min_before:
                min_before = (360.0 - d); before = Y
        if before and after:
            leg_before = by_pair.get(tuple(sorted((X, before))))
            leg_after = by_pair.get(tuple(sorted((X, after))))
            if not leg_before or not leg_after:
                continue
            besieged.append({
                'besieged': X,
                'before': before,
                'after': after,
                'before_leg': {
                    'aspect': leg_before.get('aspect'),
                    'orb': leg_before.get('orb'),
                    'phase': leg_before.get('phase'),
                    'partile': leg_before.get('partile'),
                    'complete_platic': leg_before.get('complete_platic'),
                },
                'after_leg': {
                    'aspect': leg_after.get('aspect'),
                    'orb': leg_after.get('orb'),
                    'phase': leg_after.get('phase'),
                    'partile': leg_after.get('partile'),
                    'complete_platic': leg_after.get('complete_platic'),
                },
            })

    # Doryphory: attendance to luminaries within Morin aspects
    dory = []
    # Rough sect/sex compatibility
    diurnal_set = {'Sun', 'Jupiter', 'Saturn'}
    nocturnal_set = {'Moon', 'Venus', 'Mars'}
    masculine = {'Sun', 'Jupiter', 'Saturn', 'Mars'}
    feminine = {'Moon', 'Venus'}
    # Chart sect by Sun house above/below horizon (Sun in H7-H12 → day)
    chart_day = planet_house.get('Sun', 0) in (7,8,9,10,11,12)
    for lum in ('Sun', 'Moon'):
        attendants = []
        L = lum
        for row in morin_aspects or []:
            a = str(row.get('planet1'))
            b = str(row.get('planet2'))
            if L not in (a, b):
                continue
            P = b if a == L else a
            # orientation (approx): relative longitudes
            try:
                dlon = ((planet_lon.get(P, 0.0) - planet_lon.get(L, 0.0) + 360.0) % 360.0)
            except Exception:
                dlon = 0.0
            orient = 'oriental' if L == 'Sun' and dlon > 180.0 else ('occidental' if L == 'Moon' and dlon <= 180.0 else 'neutral')
            angular = (planet_house.get(P, 0) in (1,4,7,10))
            # sect and sex
            if chart_day:
                sect_ok = (P in diurnal_set)
            else:
                sect_ok = (P in nocturnal_set)
            if P in masculine:
                sex_label = 'masculine'
            elif P in feminine:
                sex_label = 'feminine'
            else:
                sex_label = 'neutral'
            attendants.append({
                'planet': P,
                'orientation': orient,
                'angular': bool(angular),
                'aspect': row.get('aspect'),
                'orb': row.get('orb'),
                'phase': row.get('phase'),
                'partile': row.get('partile'),
                'complete_platic': row.get('complete_platic'),
                'sect_ok': bool(sect_ok),
                'sex': sex_label,
            })
        if attendants:
            dory.append({ 'luminary': L, 'attendants': attendants })

    # ---- Additional patterns per Morin ----
    jd0 = _jd_from_iso(timestamp_iso)
    # Daily motion map and speed ranks
    daily_motion: Dict[str, float] = {}
    for nm in planet_lon.keys():
        try:
            lon0, _ = _lon_lat_at(jd0, nm)
            lon1, _ = _lon_lat_at(jd0 + 1.0, nm)
            dm = ((lon1 - lon0 + 540.0) % 360.0) - 180.0
            daily_motion[nm] = abs(dm)
        except Exception:
            daily_motion[nm] = 0.0
    # Helper: connected within combined orbs using morin_aspects set
    def connected(a: str, b: str) -> bool:
        return tuple(sorted((a, b))) in by_pair

    # Mediation (corrected prohibition): slower middle between two swifter extremes, connected to both
    mediation = []
    # Sort by longitude to consider triplets
    order = sorted(planet_lon.keys(), key=lambda k: planet_lon.get(k, 0.0))
    norder = len(order)
    for i in range(norder - 2):
        A = order[i]
        B = order[i+1]
        C = order[i+2]
        if not (connected(A, B) and connected(B, C)):
            continue
        if daily_motion.get(B, 0.0) < daily_motion.get(A, 0.0) and daily_motion.get(B, 0.0) < daily_motion.get(C, 0.0):
            # Slower middle mediates/extenuates rather than prohibiting
            mediation.append({ 'extreme_1': A, 'middle': B, 'extreme_2': C })

    # Preemptive transfer (cutting off correction): swift extreme reaches other before middle does
    preemptive = []
    def _days_to_partile_pair(X: str, Y: str) -> float:
        # choose active aspect angle between X and Y if exists
        row = by_pair.get(tuple(sorted((X, Y))))
        if not row:
            return float('inf')
        A = _aspect_angle_from_name(row.get('aspect'))
        if A is None:
            return float('inf')
        # simulate forward coarsely using ecliptic sep
        # reuse simulate to detect t; here return first day threshold
        sd_sum = _semi_diameter_deg(X, jd0) + _semi_diameter_deg(Y, jd0)
        t = 0.0
        step = 0.5
        last = 1e9
        while t <= 60.0:
            lonX, _ = _lon_lat_at(jd0 + t, X)
            lonY, _ = _lon_lat_at(jd0 + t, Y)
            sep = abs(((lonX - lonY + 180.0) % 360.0) - 180.0)
            orb = abs(sep - A)
            if orb > 180.0: orb = 360.0 - orb
            if orb <= sd_sum + 1e-6:
                return t
            if orb > last + 0.25 and t > 2.0:
                return float('inf')
            last = orb
            t += step
        return float('inf')
    for i in range(norder - 2):
        E1 = order[i]
        M = order[i+1]
        E2 = order[i+2]
        if not (connected(E1, M) and connected(M, E2)):
            continue
        # extreme must be swifter than middle
        if daily_motion.get(E1, 0.0) <= daily_motion.get(M, 0.0):
            continue
        t_e1_e2 = _days_to_partile_pair(E1, E2)
        t_m_e2 = _days_to_partile_pair(M, E2)
        if t_e1_e2 < float('inf') and t_m_e2 < float('inf') and t_e1_e2 < t_m_e2:
            preemptive.append({ 'swift_extreme': E1, 'middle': M, 'receiving_extreme': E2, 'days_e1_to_e2': t_e1_e2, 'days_m_to_e2': t_m_e2 })

    # Frustration: A applies to B; C contrary motion overtakes B first
    frustration = []
    # Build applying relationships
    rel = {}
    for row in morin_aspects or []:
        a = str(row.get('planet1')); b = str(row.get('planet2'))
        ph = str(row.get('phase') or '').lower()
        if ph == 'applying':
            rel.setdefault(a, set()).add(b)
            rel.setdefault(b, set()).add(a)
    for A, Bs in rel.items():
        for B in list(Bs):
            # A applying to B
            rowAB = by_pair.get(tuple(sorted((A, B))))
            if not rowAB or str(rowAB.get('phase')).lower() != 'applying':
                continue
            # require A faster than B
            if daily_motion.get(A, 0.0) <= daily_motion.get(B, 0.0):
                continue
            # A reaches B?
            tAB = _days_to_partile_pair(A, B)
            if not (tAB < float('inf')):
                continue
            for C in planet_lon.keys():
                if C in (A, B):
                    continue
                # contrary motion: retrograde state differs over +1h
                if _is_retrograde(jd0, A) == _is_retrograde(jd0, C):
                    continue
                # Will C reach B sooner?
                tCB = _days_to_partile_pair(C, B)
                if tCB < tAB:
                    frustration.append({ 'frustrated': A, 'target': B, 'frustrating': C, 'days_C_before_A': tAB - tCB })

    # Collection: collector applies to (or separates from) 2+ simultaneously, extremes not connected
    collection = []
    for Col in planet_lon.keys():
        connects = []
        for other in planet_lon.keys():
            if other == Col:
                continue
            rowCO = by_pair.get(tuple(sorted((Col, other))))
            if not rowCO:
                continue
            ds = float(rowCO.get('orb') or 999.0)
            ph = str(rowCO.get('phase') or '').lower()
            connects.append({ 'planet': other, 'phase': ph, 'aspect': rowCO.get('aspect'), 'orb': ds })
        if len(connects) < 2:
            continue
        applying = [c for c in connects if c['phase'] == 'applying']
        separating = [c for c in connects if c['phase'] == 'separating']
        # BY_APPLICATION
        if len(applying) >= 2:
            for i in range(len(applying)):
                for j in range(i+1, len(applying)):
                    P1 = applying[i]['planet']; P2 = applying[j]['planet']
                    if connected(P1, P2):
                        continue
                    if daily_motion.get(Col, 0.0) > max(daily_motion.get(P1, 0.0), daily_motion.get(P2, 0.0)):
                        collection.append({ 'collector': Col, 'collected': [P1, P2], 'mode': 'BY_APPLICATION' })
        # BY_SEPARATION
        if len(separating) >= 2:
            for i in range(len(separating)):
                for j in range(i+1, len(separating)):
                    P1 = separating[i]['planet']; P2 = separating[j]['planet']
                    if connected(P1, P2):
                        continue
                    collection.append({ 'collector': Col, 'collected': [P1, P2], 'mode': 'BY_SEPARATION' })

    return {
        'translation': trans,
        'besiegement': besieged,
        'doryphory': dory,
        'mediation': mediation,
        'preemptive_transfer': preemptive,
        'frustration': frustration,
        'collection': collection,
    }
