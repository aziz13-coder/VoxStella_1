# -*- coding: utf-8 -*-
"""
Modern aspects helper — engine-agnostic.

Computes aspects involving modern planets (Uranus, Neptune, Pluto) using
only serialized planets entries (longitude, speed). Does not import or
modify the horary engine.
"""

from typing import Dict, List, Any
import math

ASPECTS = [
    (0.0, "Conjunction", 8.0),
    (60.0, "Sextile", 6.0),
    (90.0, "Square", 8.0),
    (120.0, "Trine", 8.0),
    (180.0, "Opposition", 8.0),
]

MODERN = {"Uranus", "Neptune", "Pluto"}


def _norm180(x: float) -> float:
    return ((x + 180.0) % 360.0) - 180.0


def _nearest_delta_to_aspect(sep: float, A: float) -> float:
    """Minimal signed delta from separation to the aspect geometry (±A)."""
    if A == 0.0:
        targets = [0.0]
    elif A == 180.0:
        targets = [180.0, -180.0]
    else:
        targets = [A, -A]
    deltas = [_norm180(sep - t) for t in targets]
    return min(deltas, key=lambda d: abs(d))


def _time_to_next_perfection(lon1: float, v1: float, lon2: float, v2: float, A: float) -> float:
    sep = _norm180(lon1 - lon2)
    delta = _nearest_delta_to_aspect(sep, A)
    v_rel = v1 - v2
    if abs(v_rel) < 1e-12:
        return math.inf
    t = -delta / v_rel
    if t > 0:
        return t
    period = 360.0 / abs(v_rel)
    k = int(math.floor((-t) / period) + 1)
    return t + k * period


def _orb_to_aspect(lon1: float, lon2: float, A: float) -> float:
    sep = abs(_norm180(lon1 - lon2))
    orb = abs(sep - A)
    if orb > 180.0:
        orb = 360.0 - orb
    return orb


def _is_applying(lon1: float, v1: float, lon2: float, v2: float, A: float) -> bool:
    # kinematic: orb shrinking in a short forward step
    now_orb = _orb_to_aspect(lon1, lon2, A)
    future_orb = _orb_to_aspect((lon1 + v1 * 0.05) % 360.0, (lon2 + v2 * 0.05) % 360.0, A)
    return future_orb < now_orb


def compute_modern_aspects(planets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute aspects that involve modern planets.

    Returns list of dicts with keys: planet1, planet2, aspect, orb, applying.
    """
    # Build source arrays
    items = []
    for p in planets:
        try:
            name = p.get("planet") or p.get("name")
            lon = float(p.get("longitude"))
            speed = float(p.get("speed", 0.0))
            items.append((name, lon, speed))
        except Exception:
            continue
    out: List[Dict[str, Any]] = []
    n = len(items)
    for i in range(n):
        p1, lon1, v1 = items[i]
        for j in range(i + 1, n):
            p2, lon2, v2 = items[j]
            # include only pairs with at least one modern
            if p1 not in MODERN and p2 not in MODERN:
                continue
            for A, label, max_orb in ASPECTS:
                orb = _orb_to_aspect(lon1, lon2, A)
                if orb <= max_orb:
                    applying = _is_applying(lon1, v1, lon2, v2, A)
                    out.append({
                        "planet1": p1,
                        "planet2": p2,
                        "aspect": label,
                        "orb": orb,
                        "applying": applying,
                    })
    return out

