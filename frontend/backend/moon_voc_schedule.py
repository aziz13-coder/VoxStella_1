# -*- coding: utf-8 -*-
"""
Moon VoC schedule helper (standalone, engine-agnostic).

Uses serialized chart_data (planets with longitude/speed) to compute a
sequence of future Moon perfections (to classical planets) that occur before
sign exit, then derives a precise VoC start time and duration within the
current sign.
"""

from typing import Any, Dict, List, Optional, Tuple
import math

ASPECTS = [0.0, 60.0, 90.0, 120.0, 180.0]
CLASSICAL = {"Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}


def _norm180(x: float) -> float:
    return ((x + 180.0) % 360.0) - 180.0


def _time_to_next_perfection(m_lon: float, m_speed: float, p_lon: float, p_speed: float, aspect_deg: float) -> float:
    """Analytical time (days) to the next future perfection for the aspect geometry."""
    rel_sep = _norm180(m_lon - p_lon)  # (-180, 180]
    # targets for symmetric aspects
    if aspect_deg == 0.0:
        targets = [0.0]
    elif aspect_deg == 180.0:
        targets = [180.0, -180.0]
    else:
        targets = [aspect_deg, -aspect_deg]

    deltas = [_norm180(rel_sep - t) for t in targets]
    delta = min(deltas, key=lambda d: abs(d))
    v_rel = m_speed - p_speed
    if abs(v_rel) < 1e-9:
        return math.inf
    t = -delta / v_rel  # can be past
    if t > 0:
        return t
    # shift forward by multiples of period
    period = 360.0 / abs(v_rel)
    k = int(math.floor((-t) / period) + 1)
    return t + k * period


def _days_to_sign_exit(lon: float, speed: float) -> Optional[float]:
    # If speed ~ 0, unknown
    if abs(speed) < 1e-9:
        return None
    within = lon % 30.0
    if speed > 0:
        degrees_left = 30.0 - within
    else:
        degrees_left = within
    if degrees_left < 0:
        degrees_left += 30.0
    return degrees_left / abs(speed)


def _planet_map(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    planets = chart_data.get("planets") or []
    if isinstance(planets, list):
        for p in planets:
            try:
                name = p.get("planet") or p.get("name")
                if not name:
                    continue
                out[name] = {
                    "lon": float(p.get("longitude", 0.0)),
                    "speed": float(p.get("speed", 0.0)),
                }
            except Exception:
                continue
    elif isinstance(planets, dict):
        for name, info in planets.items():
            try:
                out[name] = {
                    "lon": float(info.get("longitude", 0.0)),
                    "speed": float(info.get("speed", 0.0)),
                }
            except Exception:
                continue
    return out


def compute_moon_schedule(chart_data: Dict[str, Any]) -> Tuple[List[Tuple[str, float, float]], Optional[float]]:
    """Return (events, moon_sign_exit_days) where events = list of (target_name, aspect_deg, t_days).

    Only includes future perfections that occur before Moon sign exit and before
    the target changes sign.
    """
    planets = _planet_map(chart_data)
    if "Moon" not in planets:
        return [], None
    m_lon = planets["Moon"]["lon"]
    m_speed = planets["Moon"]["speed"]
    moon_exit = _days_to_sign_exit(m_lon, m_speed)
    if moon_exit is None:
        return [], None
    events: List[Tuple[str, float, float]] = []
    for target, vals in planets.items():
        if target == "Moon" or target not in CLASSICAL:
            continue
        p_lon = vals["lon"]
        p_speed = vals["speed"]
        p_exit = _days_to_sign_exit(p_lon, p_speed)
        for A in ASPECTS:
            t = _time_to_next_perfection(m_lon, m_speed, p_lon, p_speed, A)
            if not math.isfinite(t) or t <= 0:
                continue
            # must be before Moon exits sign
            if moon_exit is not None and t > moon_exit:
                continue
            # and before target exits sign
            if p_exit is not None and t > p_exit:
                continue
            events.append((target, A, t))
    events.sort(key=lambda e: e[2])
    return events, moon_exit


def build_moon_voc_timeline_precise(chart_data: Dict[str, Any], in_voc: bool) -> Dict[str, Any]:
    events, moon_exit = compute_moon_schedule(chart_data)
    if moon_exit is None:
        return {
            'in_voc': bool(in_voc),
            'sign_exit_eta_hours': None,
            'next_aspect': None,
            'voc_starts_in_hours': None,
            'voc_duration_hours': None,
            'sign_progress_pct': None,
        }
    sign_exit_hours = moon_exit * 24.0
    # next event
    next_evt = events[0] if events else None
    next_aspect = None
    if next_evt:
        next_aspect = {
            'planet': next_evt[0],
            'aspect': int(next_evt[1]) if abs(next_evt[1] - int(next_evt[1])) < 1e-6 else next_evt[1],
            'eta_hours': next_evt[2] * 24.0,
        }
    # last event before exit defines start of VoC window
    last_evt = events[-1] if events else None
    # If there are no future perfections within the sign, Moon is VoC now by definition
    if not events:
        in_voc_out = True
        voc_starts = 0.0
        voc_dur = sign_exit_hours
    elif in_voc:
        in_voc_out = True
        voc_starts = 0.0
        voc_dur = sign_exit_hours
    else:
        in_voc_out = False
        voc_starts = last_evt[2] * 24.0
        voc_dur = max(0.0, sign_exit_hours - voc_starts)

    # progress in sign can still be derived externally; leave None here
    return {
        'in_voc': bool(in_voc_out),
        'sign_exit_eta_hours': sign_exit_hours,
        'next_aspect': next_aspect,
        'voc_starts_in_hours': voc_starts,
        'voc_duration_hours': voc_dur,
        'sign_progress_pct': None,
    }
