# -*- coding: utf-8 -*-
"""
Context Layers (Auto-Fill) for Morin Workflow

Provides helpers to suggest context windows and focus selections for the
Transits feature using:
 - Solar Return timestamp (cast for residence)
 - Secondary Progressions (stubbed; to be extended)
 - Primary Directions (integration hook)

Notes:
 - This module focuses on producing time windows and focus hints. It does not
   generate full return charts here; the main app already can generate charts.
 - Solar Return time is independent of location; residence location matters for
   house structure, which can be evaluated elsewhere.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timedelta, timezone
import math

from swisseph_state import swisseph as swe


def _norm360(x: float) -> float:
    return x % 360.0


def _delta_deg(a: float, b: float) -> float:
    """Minimal signed angular difference a-b in [-180, 180]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return d


def _sun_lon(dt: datetime) -> float:
    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)
    pos, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
    return float(pos[0]) % 360.0


def _jd_to_datetime_utc(jd: float) -> Optional[datetime]:
    if swe is None:
        return None
    try:
        y, m, d, ut = swe.revjul(float(jd), swe.GREG_CAL)
        base = datetime(int(y), int(m), int(d), tzinfo=timezone.utc)
        return base + timedelta(hours=float(ut))
    except Exception:
        return None


def _solar_crossing_fallback(target_lon: float, target_year: int) -> Optional[datetime]:
    if swe is None:
        return None

    start = datetime(target_year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(target_year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    times: List[datetime] = [start]
    raw0 = _sun_lon(start)
    unwrapped: List[float] = [raw0]
    prev_raw = raw0
    acc = 0.0
    t = start + timedelta(days=1)
    while t <= end:
        raw = _sun_lon(t)
        acc += _delta_deg(raw, prev_raw)
        unwrapped.append(raw0 + acc)
        times.append(t)
        prev_raw = raw
        t += timedelta(days=1)

    lo_u = min(unwrapped)
    hi_u = max(unwrapped)
    k_min = int(math.floor((lo_u - target_lon) / 360.0)) - 1
    k_max = int(math.ceil((hi_u - target_lon) / 360.0)) + 1

    bracket_lo: Optional[datetime] = None
    bracket_hi: Optional[datetime] = None
    target_u: Optional[float] = None

    for k in range(k_min, k_max + 1):
        cand = target_lon + 360.0 * k
        if cand < lo_u or cand > hi_u:
            continue
        for i in range(len(unwrapped) - 1):
            d0 = unwrapped[i] - cand
            d1 = unwrapped[i + 1] - cand
            if d0 == 0.0 or d0 * d1 <= 0.0:
                bracket_lo = times[i]
                bracket_hi = times[i + 1]
                target_u = cand
                break
        if bracket_lo is not None and bracket_hi is not None and target_u is not None:
            break

    if bracket_lo is None or bracket_hi is None or target_u is None:
        return None

    lo = bracket_lo
    hi = bracket_hi
    for _ in range(100):
        mid = lo + (hi - lo) / 2
        raw_lo_mid = _sun_lon(lo)
        raw_mid = _sun_lon(mid)
        lo_unwrap = raw_lo_mid + 360.0 * round((target_u - raw_lo_mid) / 360.0)
        mid_unwrap = raw_mid + 360.0 * round((target_u - raw_mid) / 360.0)
        d_lo = lo_unwrap - target_u
        d_mid = mid_unwrap - target_u
        if (hi - lo).total_seconds() <= 60 or abs(d_mid) < 0.008:
            return mid
        if d_lo * d_mid <= 0:
            hi = mid
        else:
            lo = mid
    return lo + (hi - lo) / 2


def _find_solar_crossing(target_lon: float, target_year: int) -> Optional[datetime]:
    target_lon = _norm360(float(target_lon))
    if swe is None:
        return None
    try:
        jd_start = swe.julday(target_year, 1, 1, 0.0)
        jd_hit = swe.solcross_ut(target_lon, jd_start, swe.FLG_SWIEPH)
        if isinstance(jd_hit, (list, tuple)):
            jd_hit = jd_hit[0]
        dt = _jd_to_datetime_utc(float(jd_hit))
        if dt is not None and dt.year == int(target_year):
            return dt
    except Exception:
        pass
    return _solar_crossing_fallback(target_lon, target_year)


def compute_solar_return_timestamp(natal_sun_lon: float, target_year: int) -> Optional[datetime]:
    """Find the UTC timestamp in target_year when the Sun returns to natal_sun_lon.

    Uses a bracket then binary search to ~0.01° precision.
    """
    return _find_solar_crossing(natal_sun_lon, target_year)


def _sun_return_for_longitude(target_lon: float, target_year: int) -> Optional[datetime]:
    """Find UTC timestamp when the Sun reaches target_lon (tropical, geocentric) in target_year.

    Uses a broad bracket around mid-year and refines to ≤ 1 minute UT.
    """
    return _find_solar_crossing(target_lon, target_year)


def suggest_focus_from_natal(natal_cd: Dict[str, Any]) -> Tuple[List[int], List[str]]:
    """Suggest focus houses and planets using natal house rulers and angles.

    Defaults: houses [1,10]; planets = rulers of 1 and 10 when identifiable.
    """
    houses = [1, 10]
    planets: List[str] = []
    try:
        hr = natal_cd.get('house_rulers') or {}
        if isinstance(hr, dict):
            for k in ('1', '10', 1, 10):
                v = hr.get(k)
                if isinstance(v, str):
                    planets.append(v)
                elif hasattr(v, 'value'):
                    planets.append(getattr(v, 'value'))
    except Exception:
        pass
    # uniq preserve order
    seen = set()
    planets = [p for p in planets if not (p in seen or seen.add(p))]
    return houses, planets


def compute_progressed_windows_stub() -> List[Dict[str, Any]]:
    """Placeholder for secondary progressions windows (to be implemented)."""
    return []


# ---------- Lunar Returns ----------

def _moon_lon(dt: datetime) -> float:
    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)
    pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)
    return float(pos[0]) % 360.0

def _moon_lon_lat(dt: datetime) -> Tuple[float, float]:
    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)
    pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)
    return float(pos[0]) % 360.0, float(pos[1])


def compute_nearest_lunar_return(
    natal_moon_lon: float,
    center: datetime,
    natal_moon_lat: Optional[float] = None,
) -> Optional[datetime]:
    """Find the UTC datetime nearest to 'center' when Moon returns to natal_moon_lon.

    Brackets around 'center' within +/- 72 hours using 6-hour steps to find a sign change
    in delta = normalize(λ☾(t) - natal_moon_lon), then refines by bisection to <= 60s.
    When natal_moon_lat is provided, performs a final refinement to keep lunar latitude
    within ±2° of the natal latitude (searching within ±12 hours of the longitude match).
    """
    if swe is None:
        return None
    # Normalize center to UTC timezone-aware
    try:
        if center.tzinfo is None:
            from datetime import timezone as _tz
        center = center.replace(tzinfo=_tz.utc)
    except Exception:
        pass
    from datetime import timedelta as _td
    def delta(t: datetime) -> float:
        lon, _ = _moon_lon_lat(t)
        return _delta_deg(lon, natal_moon_lon)
    # Build samples every 6h in +/-72h window
    window_h = 72
    step_h = 6
    samples = []
    for k in range(-window_h, window_h + step_h, step_h):
        t = center + _td(hours=k)
        try:
            samples.append((t, delta(t)))
        except Exception:
            continue
    # Find adjacent pair with sign change or near-zero
    a = b = None
    for i in range(len(samples) - 1):
        t0, d0 = samples[i]
        t1, d1 = samples[i+1]
        if abs(d0) < 0.05:
            a, b = t0, t0
            break
        if d0 * d1 <= 0:
            a, b = t0, t1
            break
    if a is None or b is None:
        return None
    # Refine by bisection to <= 60s or |delta| < ~0.01 deg
    for _ in range(60):
        mid = a + (b - a)/2
        dm = delta(mid)
        if (b - a).total_seconds() <= 60 or abs(dm) < 0.01:
            return mid
        da = delta(a)
        if da * dm <= 0:
            b = mid
        else:
            a = mid
    result = a + (b - a)/2

    if natal_moon_lat is None:
        return result

    nat_lat = float(natal_moon_lat)

    def score(candidate: datetime) -> Tuple[float, float]:
        lon, lat = _moon_lon_lat(candidate)
        lon_diff = abs(_delta_deg(lon, natal_moon_lon))
        lat_diff = abs(lat - nat_lat)
        return lat_diff, lon_diff

    best = result
    best_score = score(result)
    if best_score[0] <= 2.0:
        return best

    horizon_minutes = 12 * 60  # ±12h
    step_minutes = 5
    for minutes in range(0, horizon_minutes + step_minutes, step_minutes):
        offset = _td(minutes=minutes)
        for sign in (-1, 1):
            candidate = result + (offset if sign >= 0 else -offset)
            lat_diff, lon_diff = score(candidate)
            candidate_score = (lat_diff, lon_diff)
            if candidate_score < best_score:
                best = candidate
                best_score = candidate_score
            if lat_diff <= 2.0 and lon_diff <= 0.5:
                return candidate

    return best


def compute_lunar_return_timestamps(natal_moon_lon: float, year: int) -> List[datetime]:
    """Return list of UTC datetimes in the given year when Moon returns to natal_moon_lon.

    Simple approach: walk the year by ~2d steps to bracket crossings, then refine by bisection.
    """
    if swe is None:
        return []
    # Start of year UTC
    t0 = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(year+1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    out: List[datetime] = []
    step = timedelta(days=2)
    lo = t0
    dlo = _delta_deg(_moon_lon(lo), natal_moon_lon)
    while lo < t1:
        hi = lo + step
        if hi > t1:
            hi = t1
        dhi = _delta_deg(_moon_lon(hi), natal_moon_lon)
        # If sign changes or either near zero, we have a return in [lo, hi]
        if dlo == 0 or dhi == 0 or (dlo * dhi < 0):
            a, da = lo, dlo
            b, db = hi, dhi
            # bisection to ~minute precision
            for _ in range(40):
                mid = a + (b - a)/2
                dm = _delta_deg(_moon_lon(mid), natal_moon_lon)
                if abs(dm) < 0.01:
                    out.append(mid)
                    break
                if da * dm <= 0:
                    b, db = mid, dm
                else:
                    a, da = mid, dm
        lo = hi
        dlo = dhi
    return out


# ---------- Primary Directions (Solar Arc approximation) ----------

def compute_solar_arc_windows(natal_dt: datetime, year: int, natal_cd: Optional[Dict[str, Any]] = None,
                              aspects: Optional[List[float]] = None,
                              window_days: int = 90) -> List[Dict[str, Any]]:
    """Compute Solar Arc windows by directing natal bodies to natal angles/planets.

    SA at date T: SA(T) = λ☉(T) − λ☉(Birth). A directed longitude is λ_dir(X,T) = λ_nat(X) + SA(T).
    For a target natal longitude λ_nat(Y) and aspect A, the event occurs when:
      λ☉(T) = λ☉(Birth) + normalize(λ_nat(Y) + A − λ_nat(X)).

    We approximate windows as ±window_days around the exact timestamp.
    """
    if swe is None:
        return []
    if aspects is None:
        aspects = [0.0, 60.0, 90.0, 120.0, 180.0]

    # Collect natal longitudes
    nat_pl: Dict[str, float] = {}
    asc_lon = None; mc_lon = None
    try:
        raw = (natal_cd or {}).get('planets') or {}
        if isinstance(raw, dict):
            for nm, row in raw.items():
                if isinstance(row, dict) and row.get('longitude') is not None:
                    nat_pl[str(nm)] = float(row.get('longitude')) % 360.0
        elif isinstance(raw, list):
            for row in raw:
                if isinstance(row, dict) and row.get('planet') and row.get('longitude') is not None:
                    nat_pl[str(row['planet'])] = float(row.get('longitude')) % 360.0
        hc = (natal_cd or {}).get('houses') or (natal_cd or {}).get('house_cusps') or []
        if isinstance(hc, list) and len(hc) >= 10:
            asc_lon = float(hc[0]) % 360.0
            mc_lon = float(hc[9]) % 360.0
    except Exception:
        pass

    # Birth Sun longitude
    try:
        jd_birth = swe.julday(natal_dt.year, natal_dt.month, natal_dt.day,
                              natal_dt.hour + natal_dt.minute/60.0 + natal_dt.second/3600.0)
        pos, _ = swe.calc_ut(jd_birth, swe.SUN, swe.FLG_SWIEPH)
        sun_birth = float(pos[0]) % 360.0
    except Exception:
        return []

    def _targets() -> List[Tuple[str, float]]:
        out: List[Tuple[str,float]] = []
        # Angles first
        if asc_lon is not None: out.append(('Asc', asc_lon))
        if mc_lon is not None: out.append(('MC', mc_lon))
        # Natal classical planets
        for nm in ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn']:
            if nm in nat_pl:
                out.append((nm, nat_pl[nm]))
        return out

    wins: List[Dict[str, Any]] = []
    tgts = _targets()
    # For each directed X hitting target Y by aspect A, compute expected Sun longitude
    for X, lonX in list(nat_pl.items())[:]:
        for (Y, lonY) in tgts:
            for ang in aspects:
                desired = (lonY + ang - lonX) % 360.0
                target_lon = (sun_birth + desired) % 360.0
                ts = _sun_return_for_longitude(target_lon, year)
                if not isinstance(ts, datetime):
                    continue
                a = (ts - timedelta(days=window_days)).isoformat()
                b = (ts + timedelta(days=window_days)).isoformat()
                wins.append({'start': a, 'end': b, 'label': f'SA {X}->{Y} {int(ang)}°', 'timestamp': ts.isoformat()})
    # Deduplicate by timestamp (~12h)
    try:
        wins.sort(key=lambda w: w.get('timestamp',''))
        uniq: List[Dict[str, Any]] = []
        last_t = None
        for w in wins:
            t = w.get('timestamp')
            if not t:
                continue
            if last_t is None:
                uniq.append(w); last_t = t; continue
            try:
                from datetime import datetime as _dt
                t0 = _dt.fromisoformat(last_t.replace('Z','+00:00'))
                t1 = _dt.fromisoformat(str(t).replace('Z','+00:00'))
                if abs((t1 - t0).total_seconds()) >= 12*3600:
                    uniq.append(w); last_t = t
            except Exception:
                uniq.append(w); last_t = t
        wins = uniq
    except Exception:
        pass
    # Drop timestamp before returning to match PD window shape
    for w in wins:
        w.pop('timestamp', None)
    return wins


# ---------- Secondary Progressions (basic progressed Moon cue) ----------

def compute_progressed_moon_windows(natal_dt: datetime, year: int, targets: List[float]) -> List[Dict[str, Any]]:
    """Compute rough windows when progressed Moon is near aspects to target longitudes.

    Secondary progression: 1 day = 1 year. We evaluate progressed time at N days after
    natal for N = years since birth up to chosen year, then check 0/90/180 aspects to targets.
    """
    if swe is None:
        return []
    # progressed datetime at new_year: natal + (year - natal_year) days
    years = max(0, year - natal_dt.year)
    prog_dt = natal_dt + timedelta(days=years)
    # progressed Moon lon
    plon = _moon_lon(prog_dt)
    wins: List[Dict[str, Any]] = []
    aspect_angles = [0.0, 90.0, 180.0]
    tol = 1.0  # degrees
    def sep(a,b):
        d = abs((a-b+180.0)%360.0 - 180.0)
        return d
    for t in targets:
        for ang in aspect_angles:
            target = (t + ang) % 360.0
            if sep(plon, target) <= tol:
                a = (prog_dt - timedelta(days=7)).isoformat()
                b = (prog_dt + timedelta(days=7)).isoformat()
                wins.append({'start': a, 'end': b, 'label': 'Progressed Moon window'})
                break
    return wins


def compute_progressed_planet_windows(
    natal_dt: datetime,
    year: int,
    natal_cd: Dict[str, Any],
    include_modern: bool = False,
    aspects: Optional[List[float]] = None,
    tol_deg: float = 1.0,
    window_days: int = 7,
) -> List[Dict[str, Any]]:
    """Progressed planets (Sun..Saturn [+ modern]) to natal planets and angles (Asc/MC) by aspects.

    Secondary progression: progressed date = natal + years days. We evaluate at the exact progressed day
    for the target year and flag windows when any aspect (0/60/90/120/180) is within tol_deg to targets.
    """
    if swe is None:
        return []
    if aspects is None:
        aspects = [0.0, 60.0, 90.0, 120.0, 180.0]
    # progressed datetime for the given year (inner/progressed time)
    years = max(0, year - natal_dt.year)
    prog_dt = natal_dt + timedelta(days=years)
    # Targets: natal planets + angles
    targets_ll: List[Tuple[str, float]] = []
    try:
        raw = natal_cd.get('planets') or {}
        if isinstance(raw, dict):
            for nm, info in raw.items():
                if isinstance(info, dict) and info.get('longitude') is not None:
                    targets_ll.append((str(nm), float(info.get('longitude'))))
        elif isinstance(raw, list):
            for info in raw:
                if isinstance(info, dict) and info.get('planet') and info.get('longitude') is not None:
                    targets_ll.append((str(info.get('planet')), float(info.get('longitude'))))
        hc = natal_cd.get('houses') or natal_cd.get('house_cusps') or []
        if isinstance(hc, list) and len(hc) >= 10:
            targets_ll.append(('Asc', float(hc[0])))
            targets_ll.append(('MC', float(hc[9])))
    except Exception:
        pass
    # Progressed longitudes for planets
    names = ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn'] + (['Uranus','Neptune','Pluto'] if include_modern else [])
    jd = swe.julday(prog_dt.year, prog_dt.month, prog_dt.day, prog_dt.hour + prog_dt.minute/60.0 + prog_dt.second/3600.0)
    events: List[Dict[str, Any]] = []
    def sep(a,b):
        d = abs((a-b+180.0)%360.0 - 180.0)
        return d
    for nm in names:
        try:
            pid = getattr(swe, nm.upper(), None)
            if pid is None:
                continue
            pos, _ = swe.calc_ut(jd, pid, swe.FLG_SWIEPH)
            lon = float(pos[0]) % 360.0
            for (label, tgt) in targets_ll:
                for ang in aspects:
                    target = (tgt + ang) % 360.0
                    if sep(lon, target) <= tol_deg:
                        # Inner (progressed) window
                        s_in = (prog_dt - timedelta(days=window_days))
                        e_in = (prog_dt + timedelta(days=window_days))
                        # Outer-year mapping: change year to target year, keep month/day/time
                        def _outer(dt_in: datetime) -> Optional[str]:
                            try:
                                return dt_in.replace(year=year).isoformat()
                            except Exception:
                                return None
                        s_out = _outer(s_in)
                        e_out = _outer(e_in)
                        events.append({
                            'start': s_in.isoformat(),
                            'end': e_in.isoformat(),
                            'outer_start': s_out,
                            'outer_end': e_out,
                            'label': f'Prog {nm} {int(ang)}° {label}',
                            'planet': nm,
                            'aspect': ang,
                            'target': label,
                        })
                        break
        except Exception:
            continue
    return events


def compute_sr_enhanced_markers(natal_cd: Dict[str, Any], sr_cd: Dict[str, Any], orb_deg: float = 6.0) -> Dict[str, Any]:
    """Compute simple but richer SR↔Natal markers: SR planets to Natal angles/planets and SR Sun/Moon to Natal angles.

    Returns { aspects: [ {p1,p2,aspect,orb} ], angles: [tags] }
    """
    def _list_pl(cd):
        raw = cd.get('planets') or {}
        out = {}
        if isinstance(raw, dict):
            for k,v in raw.items():
                if isinstance(v, dict) and v.get('longitude') is not None:
                    out[str(k)] = float(v.get('longitude'))
        elif isinstance(raw, list):
            for v in raw:
                if isinstance(v, dict) and v.get('planet') and v.get('longitude') is not None:
                    out[str(v.get('planet'))] = float(v.get('longitude'))
        return out
    def _list_angles(cd):
        hc = cd.get('houses') or cd.get('house_cusps') or []
        if isinstance(hc, list) and len(hc) >= 10:
            return {'Asc': float(hc[0]), 'MC': float(hc[9])}
        return {}
    def _sep(a,b):
        d = abs((a-b+180.0)%360.0 - 180.0)
        return d
    aspects = []
    angles_tags = []
    np = _list_pl(natal_cd); sp = _list_pl(sr_cd)
    na = _list_angles(natal_cd)
    # SR planets to Natal angles
    for nm, slon in sp.items():
        for an, alon in na.items():
            d = _sep(slon, alon)
            for ang, lab in [(0,'Conjunction'),(60,'Sextile'),(90,'Square'),(120,'Trine'),(180,'Opposition')]:
                if abs(d-ang) <= orb_deg:
                    aspects.append({'p1': f'SR {nm}', 'p2': f'Natal {an}', 'aspect': lab, 'orb': round(abs(d-ang),2)})
                    break
    # SR planets to Natal planets
    for sn, slon in sp.items():
        for nn, nlon in np.items():
            if nn == sn: continue
            d = _sep(slon, nlon)
            for ang, lab in [(0,'Conjunction'),(60,'Sextile'),(90,'Square'),(120,'Trine'),(180,'Opposition')]:
                if abs(d-ang) <= orb_deg:
                    aspects.append({'p1': f'SR {sn}', 'p2': f'Natal {nn}', 'aspect': lab, 'orb': round(abs(d-ang),2)})
                    break
    # SR Sun/Moon to Natal angles quick tags
    for nm in ['Sun','Moon']:
        if nm in sp:
            for an, alon in na.items():
                d = _sep(sp[nm], alon)
                if d <= 2.0:
                    angles_tags.append(f'SR {nm} near Natal {an}')
                elif abs(d-90) <= 3.0:
                    angles_tags.append(f'SR {nm} square Natal {an}')
                elif abs(d-120) <= 3.0:
                    angles_tags.append(f'SR {nm} trine Natal {an}')
    return {'aspects': aspects, 'angle_tags': angles_tags}


# ---------- SR ↔ Natal Similarity ----------

def _sign_name(lon: float) -> str:
    names = [
        'Aries','Taurus','Gemini','Cancer','Leo','Virgo',
        'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'
    ]
    return names[int((_norm360(lon))//30)]


def _house_list(cd: Dict[str, Any]) -> List[float]:
    try:
        hc = cd.get('houses') or cd.get('house_cusps') or []
        if isinstance(hc, list) and len(hc) >= 12:
            return [float(x) for x in hc[:12]]
    except Exception:
        pass
    return [0.0]*12


def _planets_map(cd: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw = cd.get('planets') or {}
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, dict):
        for k,v in raw.items():
            if isinstance(v, dict):
                vv = dict(v); vv.setdefault('planet', k); out[str(k)] = vv
    elif isinstance(raw, list):
        for v in raw:
            if isinstance(v, dict) and v.get('planet'):
                out[str(v['planet'])] = v
    return out


def _angle_similarity(natal_cd: Dict[str, Any], sr_cd: Dict[str, Any]) -> Tuple[int, List[str]]:
    tags: List[str] = []
    score = 0
    n_h = _house_list(natal_cd)
    s_h = _house_list(sr_cd)
    try:
        n_asc = float(n_h[0]); s_asc = float(s_h[0])
        # Asc-Asc aspect
        d = abs(((s_asc - n_asc + 180.0) % 360.0) - 180.0)
        if d <= 8:
            tags.append('Asc Conj Asc'); score += 3
        elif abs(d-120.0) <= 8:
            tags.append('Asc Trine Asc'); score += 2
        elif abs(d-60.0) <= 6:
            tags.append('Asc Sextile Asc'); score += 1
        elif abs(d-90.0) <= 8:
            tags.append('Asc Square Asc'); score -= 2
        elif abs(d-180.0) <= 8:
            tags.append('Asc Opp Asc'); score -= 3
        # same sign on Asc
        if _sign_name(n_asc) == _sign_name(s_asc):
            tags.append('Asc same sign'); score += 1
    except Exception:
        pass
    # MC sign similarity
    try:
        n_mc = float(n_h[9]); s_mc = float(s_h[9])
        if _sign_name(n_mc) == _sign_name(s_mc):
            tags.append('MC same sign'); score += 1
    except Exception:
        pass
    return score, tags


def _planet_similarity(natal_cd: Dict[str, Any], sr_cd: Dict[str, Any], names: List[str]) -> Tuple[int, List[str]]:
    score = 0; tags: List[str] = []
    np = _planets_map(natal_cd); sp = _planets_map(sr_cd)
    n_h = _house_list(natal_cd); s_h = _house_list(sr_cd)
    def _house_of(lon: float, cusps: List[float]) -> Optional[int]:
        if not cusps or len(cusps) < 12: return None
        lon = _norm360(lon)
        for i in range(12):
            a = _norm360(cusps[i]); b = _norm360(cusps[(i+1)%12])
            if a <= b:
                if a <= lon < b: return i+1
            else:
                if lon >= a or lon < b: return i+1
        return None
    for nm in names:
        try:
            n = np.get(nm); s = sp.get(nm)
            if not (n and s):
                continue
            lon_n = float(n.get('longitude')); lon_s = float(s.get('longitude'))
            # same sign
            if _sign_name(lon_n) == _sign_name(lon_s):
                tags.append(f"{nm} same sign"); score += 1
            # same house number
            hn = int(n.get('house')) if n.get('house') is not None else _house_of(lon_n, n_h)
            hs = int(s.get('house')) if s.get('house') is not None else _house_of(lon_s, s_h)
            if hn and hs and hn == hs:
                tags.append(f"{nm} same house"); score += 1
            # return to natal place (≤ 2°) or aspect (≤ 6° to 60/90/120/180)
            d = abs(((lon_s - lon_n + 180.0) % 360.0) - 180.0)
            if d <= 2.0:
                tags.append(f"{nm} returns to place"); score += 2
            else:
                for ang, lab in [(60,'Sex'),(90,'Sq'),(120,'Tri'),(180,'Opp')]:
                    if abs(d-ang) <= 6.0:
                        tags.append(f"{nm} returns by {lab}"); score += (1 if ang in (60,120) else 0)
                        if ang in (90,180): score -= 1
                        break
        except Exception:
            continue
    return score, tags


def compute_sr_similarity(natal_cd: Dict[str, Any], sr_cd: Dict[str, Any]) -> Dict[str, Any]:
    # The Sun's exact return defines the solar revolution itself, so counting a
    # Sun-to-natal-place repeat here would inflate the score tautologically.
    names = ['Moon','Mercury','Venus','Mars','Jupiter','Saturn']
    s1, t1 = _angle_similarity(natal_cd, sr_cd)
    s2, t2 = _planet_similarity(natal_cd, sr_cd, names)
    score = s1 + s2
    level = 'Low'
    if score >= 8: level = 'High'
    elif score >= 4: level = 'Medium'
    return {'score': score, 'level': level, 'tags': (t1 + t2)}


# ---------- SR Ruler condition ----------

_TRAD_RULERS = {
    'Aries':'Mars','Taurus':'Venus','Gemini':'Mercury','Cancer':'Moon','Leo':'Sun','Virgo':'Mercury',
    'Libra':'Venus','Scorpio':'Mars','Sagittarius':'Jupiter','Capricorn':'Saturn','Aquarius':'Saturn','Pisces':'Jupiter'
}
_EXALT = {'Sun':'Aries','Moon':'Taurus','Jupiter':'Cancer','Mercury':'Virgo','Venus':'Pisces','Mars':'Capricorn','Saturn':'Libra'}


def compute_sr_ruler_condition(sr_cd: Dict[str, Any]) -> Dict[str, Any]:
    tags: List[str] = []
    houses = _house_list(sr_cd)
    asc_lon = float(houses[0]) if houses and len(houses)>=1 else 0.0
    asc_sign = _sign_name(asc_lon)
    ruler = _TRAD_RULERS.get(asc_sign)
    if not ruler:
        return {'ruler': None, 'tags': []}
    pl = _planets_map(sr_cd)
    sun = pl.get('Sun', {})
    r = pl.get(ruler, {})
    try:
        rl = float(r.get('longitude'))
        rh = int(r.get('house')) if r.get('house') is not None else None
    except Exception:
        rl, rh = 0.0, None
    # Angularity
    if rh in (1,4,7,10): tags.append('Ruler Angular')
    elif rh in (2,5,8,11): tags.append('Ruler Succedent')
    else: tags.append('Ruler Cadent')
    # Essential dignity
    if _sign_name(rl) == asc_sign or _EXALT.get(ruler) == _sign_name(rl):
        tags.append('Ruler Dignified')
    # Combust/under beams tags
    try:
        sl = float(sun.get('longitude'))
        d = abs(((rl - sl + 180.0) % 360.0) - 180.0)
        if d <= 0.33:
            tags.append('Ruler Cazimi')
        elif d <= 8.5:
            tags.append('Ruler Combust')
        elif d <= 18.0:
            tags.append('Ruler Under Beams')
    except Exception:
        pass
    # Benefic/Malefic hint
    if ruler in ('Jupiter','Venus'): tags.append('Ruler Benefic')
    if ruler in ('Saturn','Mars'): tags.append('Ruler Malefic')
    return {'ruler': ruler, 'tags': tags}


# ---------- LR selection by concordance ----------

def score_lr_concordance(natal_cd: Dict[str, Any], sr_cd: Dict[str, Any], lr_cd: Dict[str, Any], pd_windows: List[Dict[str, Any]]) -> Tuple[int,List[str]]:
    score = 0; tags: List[str] = []
    # Asc vs Natal Asc aspect
    try:
        n_asc = _house_list(natal_cd)[0]; lr_asc = _house_list(lr_cd)[0]
        d = abs(((lr_asc - n_asc + 180.0) % 360.0) - 180.0)
        if d <= 8: score += 2; tags.append('LR Asc~Natal Asc')
        elif abs(d-120) <= 8: score += 1; tags.append('LR Asc Tri Natal')
        elif abs(d-90) <= 8: score -= 1; tags.append('LR Asc Sq Natal')
        elif abs(d-180) <= 8: score -= 2; tags.append('LR Asc Opp Natal')
    except Exception:
        pass
    # Asc vs SR Asc sign match
    try:
        if _sign_name(_house_list(lr_cd)[0]) == _sign_name(_house_list(sr_cd)[0]):
            score += 1; tags.append('LR Asc same SR sign')
    except Exception:
        pass
    # Planet returns to natal place/aspect
    np = _planets_map(natal_cd); lp = _planets_map(lr_cd)
    # The Moon's exact return defines the lunar revolution itself, so exclude the
    # Moon from LR↔natal return scoring; otherwise every lunar return gets a free
    # "Moon LR~Natal place" support tag.
    for nm in ['Sun','Mercury','Venus','Mars','Jupiter','Saturn']:
        try:
            n = np.get(nm); l = lp.get(nm)
            if not (n and l): continue
            ln, ll = float(n.get('longitude')), float(l.get('longitude'))
            d = abs(((ll - ln + 180.0) % 360.0) - 180.0)
            if d <= 2: score += 2; tags.append(f'{nm} LR~Natal place')
            elif min(abs(d-60),abs(d-90),abs(d-120),abs(d-180)) <= 6:
                score += 1; tags.append(f'{nm} LR~Natal aspect')
        except Exception:
            continue
    # Boost if LR time falls inside any PD window
    try:
        lr_ts = lr_cd.get('timestamp')
        if isinstance(lr_ts, str):
            from datetime import datetime as _dt
            t = _dt.fromisoformat(lr_ts.replace('Z','+00:00'))
            for w in (pd_windows or []):
                try:
                    a = _dt.fromisoformat(str(w.get('start')).replace('Z','+00:00'))
                    b = _dt.fromisoformat(str(w.get('end')).replace('Z','+00:00'))
                    if a <= t <= b:
                        score += 2; tags.append('LR in PD window'); break
                except Exception:
                    continue
    except Exception:
        pass
    return score, tags
