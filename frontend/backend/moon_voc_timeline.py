# -*- coding: utf-8 -*-
"""
Utility to build Moon VoC timeline info from compact chart data without
modifying the horary engine. Uses serialized fields produced by the engine
to estimate when VoC starts and its duration until sign exit.

Heuristics:
- If currently VoC, duration is time until sign exit.
- If not VoC and a next Moon aspect exists within the sign, we approximate
  the VoC window as the period after that perfection until sign exit.
  (If subsequent aspects exist, this is a lower bound; precision can be
   improved later by exposing an aspect schedule.)
"""

from typing import Any, Dict, Optional


def _safe_float(x) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def build_moon_voc_timeline(chart_data: Dict[str, Any],
                            in_voc: bool,
                            degree_in_sign: Optional[float],
                            moon_speed_deg_per_day: Optional[float],
                            next_aspect: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a dict with VoC timeline metrics.

    Keys:
      - in_voc: bool
      - sign_exit_eta_hours: float|None
      - next_aspect: { planet, aspect, eta_hours }|None
      - voc_starts_in_hours: float|None (when VoC will begin, if not VoC now)
      - voc_duration_hours: float|None (length of VoC window)
      - sign_progress_pct: float|None
    """
    deg_in_sign = _safe_float(degree_in_sign)
    speed = _safe_float(moon_speed_deg_per_day)
    sign_exit_hours = None
    if deg_in_sign is not None and speed and speed > 0:
        degrees_left = max(0.0, 30.0 - deg_in_sign)
        sign_exit_hours = (degrees_left / speed) * 24.0

    na_eta_hours = None
    na_aspect = None
    na_planet = None
    if isinstance(next_aspect, dict):
        days = _safe_float(next_aspect.get('perfection_eta_days'))
        if days is not None:
            na_eta_hours = days * 24.0
        na_aspect = next_aspect.get('aspect')
        na_planet = next_aspect.get('planet')

    # Estimate VoC start and duration
    voc_starts_in = None
    voc_duration = None
    inferred_voc_now = False
    if in_voc:
        # Already void: duration is time until sign exit
        voc_duration = sign_exit_hours
    else:
        if sign_exit_hours is not None and na_eta_hours is not None and na_eta_hours <= sign_exit_hours:
            # Approximate: VoC begins after the next perfection, until sign exit
            after_next = max(0.0, sign_exit_hours - na_eta_hours)
            voc_starts_in = na_eta_hours
            voc_duration = after_next
        elif sign_exit_hours is not None and (na_eta_hours is None or na_eta_hours > sign_exit_hours):
            # No next aspect within sign: infer immediate VoC window until sign exit.
            voc_starts_in = 0.0
            voc_duration = sign_exit_hours
            inferred_voc_now = True

    sign_progress_pct = None
    if deg_in_sign is not None:
        sign_progress_pct = max(0.0, min(100.0, (deg_in_sign / 30.0) * 100.0))

    payload = {
        'in_voc': bool(in_voc),
        'sign_exit_eta_hours': sign_exit_hours,
        'next_aspect': {
            'planet': na_planet,
            'aspect': na_aspect,
            'eta_hours': na_eta_hours,
        } if na_eta_hours is not None else None,
        'voc_starts_in_hours': voc_starts_in,
        'voc_duration_hours': voc_duration,
        'inferred_voc_now': inferred_voc_now,
        'sign_progress_pct': sign_progress_pct,
    }
    return payload
