# -*- coding: utf-8 -*-
"""
Planetary aspects with applying/separating phase (engine-agnostic).

Computes major aspects between planets using current longitudes and apparent
speeds to estimate phase via a small forward step. Optionally includes modern
planets (Uranus/Neptune/Pluto) using the existing modern_planets helper.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from modern_planets import compute_modern_planets


MAJOR_ASPECTS: List[Tuple[float, str, float]] = [
    (0.0,   "Conjunction", 8.0),
    (60.0,  "Sextile",     6.0),
    (90.0,  "Square",      8.0),
    (120.0, "Trine",       8.0),
    (180.0, "Opposition",  8.0),
]


def _norm360(x: float) -> float:
    return x % 360.0


def _norm180(x: float) -> float:
    return ((x + 180.0) % 360.0) - 180.0


def _orb_to_aspect(lon1: float, lon2: float, A: float) -> float:
    sep = abs(_norm180(lon1 - lon2))
    orb = abs(sep - A)
    if orb > 180.0:
        orb = 360.0 - orb
    return orb


def compute_planetary_aspects_precise(
    chart_data: Dict[str, Any],
    timestamp_iso: str,
    include_modern: bool = True,
    dt_hours: float = 0.5,
) -> List[Dict[str, Any]]:
    """Compute planetary aspects and classify applying/separating via forward step.

    Returns rows: { planet1, planet2, aspect, orb, max_orb, phase }.
    """
    # Collect planets with speeds
    planets: List[Dict[str, Any]] = []
    try:
        pl = chart_data.get("planets") or []
        if isinstance(pl, dict):
            for name, info in pl.items():
                if isinstance(info, dict):
                    x = dict(info)
                    x.setdefault("planet", name)
                    planets.append(x)
        elif isinstance(pl, list):
            planets = [p for p in pl if isinstance(p, dict)]
    except Exception:
        planets = []

    if include_modern:
        try:
            modern = compute_modern_planets(chart_data, timestamp_iso)
            # avoid duplicates
            present = {str(p.get("planet")) for p in planets}
            for m in modern:
                if str(m.get("planet")) not in present:
                    planets.append(m)
        except Exception:
            pass

    # Forward step in days
    dt_days = float(dt_hours) / 24.0

    out: List[Dict[str, Any]] = []
    n = len(planets)
    for i in range(n):
        a = planets[i]
        try:
            p1 = str(a.get("planet"))
            lon1 = float(a.get("longitude", 0.0))
            v1 = float(a.get("speed", 0.0) or 0.0)
        except Exception:
            continue
        for j in range(i + 1, n):
            b = planets[j]
            try:
                p2 = str(b.get("planet"))
                lon2 = float(b.get("longitude", 0.0))
                v2 = float(b.get("speed", 0.0) or 0.0)
            except Exception:
                continue
            for A, label, max_orb in MAJOR_ASPECTS:
                orb_now = _orb_to_aspect(lon1, lon2, A)
                if orb_now <= max_orb:
                    # Future step using apparent speeds
                    lon1f = _norm360(lon1 + v1 * dt_days)
                    lon2f = _norm360(lon2 + v2 * dt_days)
                    orb_future = _orb_to_aspect(lon1f, lon2f, A)
                    phase = None
                    try:
                        if orb_future < orb_now:
                            phase = "applying"
                        elif orb_future > orb_now:
                            phase = "separating"
                        else:
                            phase = "stationary"
                    except Exception:
                        phase = None
                    out.append({
                        "planet1": p1,
                        "planet2": p2,
                        "aspect": label,
                        "orb": round(float(orb_now), 3),
                        "max_orb": float(max_orb),
                        "phase": phase,
                    })

    out.sort(key=lambda r: abs(float(r.get("orb", 999.0))))
    return out
