# -*- coding: utf-8 -*-
"""
Declination aspects (parallel / antiparallel) — engine-agnostic helper.

Computes declination-based aspects for a set of planets at a given UTC
timestamp using Swiss Ephemeris. No dependency on horary engine internals.
"""

from typing import List, Dict, Any
import math
import datetime

try:
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None

CLASSICAL = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
MODERN = ["Uranus", "Neptune", "Pluto"]


def _swe_id(name: str) -> int:
    return getattr(swe, name.upper(), None)


def _decl_at(jd_ut: float, pid: int) -> float:
    # returns declination in degrees using ecliptic->equatorial conversion
    # swe.calc_ut returns ecliptic coords; declination requires equatorial calc
    # Use flag for equatorial coordinates
    pos, _ = swe.calc_ut(jd_ut, pid, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
    # pos: [RA, Decl, Distance, RA speed, Decl speed]
    return float(pos[1])


def _names_to_ids(names: List[str]) -> List[tuple]:
    out = []
    for n in names:
        pid = _swe_id(n)
        if pid is not None:
            out.append((n, pid))
    return out


def compute_declination_aspects(timestamp_iso: str, planet_names: List[str], orb_deg: float = 1.0,
                                apply_only: bool = True) -> List[Dict[str, Any]]:
    """Compute parallel / antiparallel aspects for given planets.

    Returns list of dicts: { planet1, planet2, type: 'parallel'|'antiparallel', orb, applying, max_orb }
    """
    if swe is None:
        return []
    try:
        dt = datetime.datetime.fromisoformat(timestamp_iso.replace('Z', '+00:00')).astimezone(datetime.timezone.utc)
    except Exception:
        dt = datetime.datetime.now(datetime.timezone.utc)
    jd_ut = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0 + dt.second / 3600.0)

    ids = _names_to_ids(planet_names)
    if not ids:
        return []

    # compute decl for now and +dt for applying check
    dt_days = 0.05
    decl_now = {}
    decl_future = {}
    for name, pid in ids:
        try:
            decl_now[name] = _decl_at(jd_ut, pid)
            decl_future[name] = _decl_at(jd_ut + dt_days, pid)
        except Exception:
            continue

    out: List[Dict[str, Any]] = []
    n = len(ids)
    for i in range(n):
        n1, _ = ids[i]
        if n1 not in decl_now:
            continue
        for j in range(i + 1, n):
            n2, _ = ids[j]
            if n2 not in decl_now:
                continue
            d1 = decl_now[n1]
            d2 = decl_now[n2]
            # parallel: same sign declinations, orb = |d1 - d2|
            # antiparallel: opposite sign declinations, orb = | |d1| - |d2| |
            aspects = []
            if d1 * d2 >= 0:
                orb = abs(d1 - d2)
                if orb <= orb_deg:
                    aspects.append(('parallel', orb))
            else:
                orb = abs(abs(d1) - abs(d2))
                if orb <= orb_deg:
                    aspects.append(('antiparallel', orb))

            if not aspects:
                continue

            # applying check: is separation shrinking in declination space
            d1f = decl_future.get(n1, d1)
            d2f = decl_future.get(n2, d2)
            for typ, orb in aspects:
                if typ == 'parallel':
                    now_sep = abs(d1 - d2)
                    fut_sep = abs(d1f - d2f)
                else:  # antiparallel
                    now_sep = abs(abs(d1) - abs(d2))
                    fut_sep = abs(abs(d1f) - abs(d2f))
                applying = fut_sep < now_sep
                if apply_only and not applying:
                    continue
                out.append({
                    'planet1': n1,
                    'planet2': n2,
                    'aspect': typ,
                    'orb': float(orb),
                    'applying': bool(applying),
                    'max_orb': float(orb_deg),
                })
    # sort by smallest orb
    out.sort(key=lambda a: a['orb'])
    return out
