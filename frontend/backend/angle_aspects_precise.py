# -*- coding: utf-8 -*-
"""
Precise planet-to-angle aspects with applying/separating phase.

Computes aspects of planets to ASC/MC/DSC/IC within a tight orb (default 1.0°),
taking into account motion of BOTH the angles (cusps) and the planet by
sampling a short time step into the future.

This module uses AstroClockEngine directly to obtain the future snapshot and
remains separate from the horary engine core logic.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from astro_clock_engine import AstroClockEngine, AstroClockSettings, ClockMode


MAJOR_ASPECTS: List[Tuple[float, str]] = [
    (0.0, "Conjunction"),
    (60.0, "Sextile"),
    (90.0, "Square"),
    (120.0, "Trine"),
    (180.0, "Opposition"),
]


def _norm360(x: float) -> float:
    return x % 360.0


def _norm180(x: float) -> float:
    return ((x + 180.0) % 360.0) - 180.0


def _absdiff(a: float, b: float) -> float:
    return abs(_norm180(a - b))


def _orb_to_aspect(lon1: float, lon2: float, A: float) -> float:
    sep = _absdiff(lon1, lon2)
    orb = abs(sep - A)
    if orb > 180.0:
        orb = 360.0 - orb
    return orb


def _angles_from_chart(chart_data: Dict[str, Any]) -> Dict[str, float]:
    """Extract ASC/MC (and derive DSC/IC) from chart_data."""
    asc = None
    mc = None
    try:
        if chart_data.get("ascendant") is not None:
            asc = float(chart_data.get("ascendant"))
    except Exception:
        asc = None
    try:
        if chart_data.get("midheaven") is not None:
            mc = float(chart_data.get("midheaven"))
    except Exception:
        mc = None
    if asc is None or mc is None:
        cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
        if isinstance(cusps, list) and len(cusps) >= 10:
            try:
                asc = float(cusps[0])
            except Exception:
                asc = 0.0
            try:
                mc = float(cusps[9])
            except Exception:
                mc = 90.0
        else:
            asc = float(asc or 0.0)
            mc = float(mc or 90.0)
    dsc = _norm360(asc + 180.0)
    ic = _norm360(mc + 180.0)
    return {"ASC": asc, "DSC": dsc, "MC": mc, "IC": ic}


def compute_angle_aspects_precise(
    chart_data: Dict[str, Any],
    timestamp_iso: str,
    location: Optional[str],
    timezone: Optional[str],
    orb_deg: float = 1.0,
    dt_hours: float = 0.5,
    house_system_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compute planet-to-angle aspects with phase using a forward time sample.

    Returns rows: { planet, angle, aspect, orb, phase } for orb <= orb_deg.
    """
    # Current snapshot
    angles_now = _angles_from_chart(chart_data)
    planets_now: List[Dict[str, Any]] = []
    try:
        pl = chart_data.get("planets") or []
        if isinstance(pl, dict):
            for name, info in pl.items():
                if isinstance(info, dict):
                    x = dict(info)
                    x.setdefault("planet", name)
                    planets_now.append(x)
        elif isinstance(pl, list):
            planets_now = [p for p in pl if isinstance(p, dict)]
    except Exception:
        planets_now = []

    # Future snapshot via engine (both planets and angles move)
    try:
        dt0 = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    except Exception:
        # If parsing fails, just return current-only assessment (phase=None)
        dt0 = None

    angles_future: Dict[str, float] = angles_now
    planets_future: Dict[str, Dict[str, Any]] = {str(p.get("planet")): p for p in planets_now}
    if dt0 is not None:
        try:
            engine = AstroClockEngine()
            future_settings = AstroClockSettings(
                mode=ClockMode.MANUAL,
                location=location or None,
                custom_time=dt0 + timedelta(hours=dt_hours),
                timezone=timezone or None,
                house_system_code=(house_system_code or (chart_data.get('house_system_code') if isinstance(chart_data, dict) else None)),
            )
            future = engine.get_current_data(future_settings)
            ch2 = future.chart_result.get("chart_data", {})
            angles_future = _angles_from_chart(ch2)
            # normalize future planets
            pl2 = ch2.get("planets") or []
            planets_future = {}
            if isinstance(pl2, dict):
                for name, info in pl2.items():
                    if isinstance(info, dict):
                        x = dict(info)
                        x.setdefault("planet", name)
                        planets_future[name] = x
            elif isinstance(pl2, list):
                for p in pl2:
                    if isinstance(p, dict) and p.get("planet"):
                        planets_future[str(p.get("planet"))] = p
        except Exception:
            # keep future = now as fallback
            angles_future = angles_now
            planets_future = {str(p.get("planet")): p for p in planets_now}

    out: List[Dict[str, Any]] = []
    for p in planets_now:
        try:
            pname = str(p.get("planet"))
            plon_now = float(p.get("longitude", 0.0))
            p2 = planets_future.get(pname)
            plon_future = float(p2.get("longitude", plon_now)) if isinstance(p2, dict) else plon_now
        except Exception:
            continue
        for aname, alon_now in angles_now.items():
            alon_future = float(angles_future.get(aname, alon_now))
            for A, label in MAJOR_ASPECTS:
                orb_now = _orb_to_aspect(plon_now, alon_now, A)
                if orb_now <= orb_deg:
                    orb_future = _orb_to_aspect(plon_future, alon_future, A)
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
                        "planet": pname,
                        "angle": aname,
                        "aspect": label,
                        "orb": round(float(orb_now), 3),
                        "phase": phase,
                    })

    # Sort by orb ascending
    out.sort(key=lambda r: abs(float(r.get("orb", 999.0))))
    return out
