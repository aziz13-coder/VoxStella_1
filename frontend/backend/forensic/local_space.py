# -*- coding: utf-8 -*-
"""
Local-space (azimuth/altitude) computation helpers for forensic abduction mapping.

Computes topocentric azimuth/altitude for requested planets at a given
UTC timestamp and observer location (lat, lon).

Azimuth convention: 0° = North, 90° = East, 180° = South, 270° = West.
Altitude: degrees above the horizon (negative if below).
"""
from __future__ import annotations

import threading
from typing import Dict, Any, Iterable
from math import sin, cos, asin, atan2, radians, degrees

try:
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover - runtime safety
    swe = None  # type: ignore


_SWE_TOPO_LOCK = threading.RLock()


# Map simple names to Swiss Ephemeris IDs
PLANET_IDS = {
    'Sun': getattr(swe, 'SUN', 0) if swe else 0,
    'Moon': getattr(swe, 'MOON', 1) if swe else 1,
    'Mercury': getattr(swe, 'MERCURY', 2) if swe else 2,
    'Venus': getattr(swe, 'VENUS', 3) if swe else 3,
    'Mars': getattr(swe, 'MARS', 4) if swe else 4,
    'Jupiter': getattr(swe, 'JUPITER', 5) if swe else 5,
    'Saturn': getattr(swe, 'SATURN', 6) if swe else 6,
    # Moderns (when present)
    'Uranus': getattr(swe, 'URANUS', 7) if swe else 7,
    'Neptune': getattr(swe, 'NEPTUNE', 8) if swe else 8,
    'Pluto': getattr(swe, 'PLUTO', 9) if swe else 9,
}


def _jd_ut_from_iso(iso: str) -> float:
    """Compute UT Julian day from an ISO timestamp (assumed UTC or tz-aware).

    Accepts naive forms by assuming UTC.
    """
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    h = (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
        + (dt_utc.microsecond / 1e6) / 3600.0
    )
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, h)  # type: ignore


def _lst_hours(jd_ut: float, lon_deg: float) -> float:
    """Local sidereal time in hours for given JD(UT) and longitude (deg)."""
    gmst = swe.sidtime(jd_ut)  # hours at Greenwich
    lst = gmst + (lon_deg / 15.0)
    # Normalize to [0,24)
    while lst < 0:
        lst += 24.0
    while lst >= 24.0:
        lst -= 24.0
    return lst


def _az_alt_from_ra_dec(ra_hours: float, dec_deg: float, lat_deg: float, lst_hours: float) -> Dict[str, float]:
    """Convert RA/Dec to azimuth/altitude for a given latitude and local sidereal time.

    Returns azimuth_deg (0=N,90=E) and altitude_deg.
    Conventions follow standard spherical astronomy:
      HA = (LST − RA) in hours → degrees
      y = cos δ · sin HA
      x = cos φ · sin δ − sin φ · cos δ · cos HA
      az = atan2(y, x) normalized to 0..360° (0°=N, 90°=E)
    """
    # Hour angle in degrees
    ha_deg = (lst_hours - ra_hours) * 15.0
    # Normalize HA to [-180, 180]
    if ha_deg > 180.0:
        ha_deg -= 360.0
    if ha_deg < -180.0:
        ha_deg += 360.0

    ha = radians(ha_deg)
    dec = radians(dec_deg)
    lat = radians(lat_deg)

    # Altitude
    sin_alt = sin(lat) * sin(dec) + cos(lat) * cos(dec) * cos(ha)
    alt = asin(max(-1.0, min(1.0, sin_alt)))

    # Azimuth (0=N, increasing towards E) — use atan2(y, x)
    y = -cos(dec) * sin(ha)
    x = cos(lat) * sin(dec) - sin(lat) * cos(dec) * cos(ha)
    az = atan2(y, x)
    az_deg = (degrees(az) + 360.0) % 360.0
    return { 'azimuth_deg': az_deg, 'altitude_deg': degrees(alt) }


def compute_local_space(timestamp_iso: str, lat: float, lon: float, planets: Iterable[str]) -> Dict[str, Dict[str, float]]:
    """Compute azimuth/altitude for given planet names at place/time.

    Uses Swiss Ephemeris topocentric positions when available.
    """
    if swe is None:
        raise RuntimeError("pyswisseph not available")
    out: Dict[str, Dict[str, float]] = {}
    with _SWE_TOPO_LOCK:
        try:
            swe.set_topo(lon, lat, 0.0)
        except Exception:
            pass
        jd_ut = _jd_ut_from_iso(timestamp_iso)
        lst_h = _lst_hours(jd_ut, lon)
        # Swiss Ephemeris flags (canonical names with fallback)
        FLAGS = (
            getattr(swe, 'SEFLG_SWIEPH', getattr(swe, 'FLG_SWIEPH', 2))
            | getattr(swe, 'SEFLG_EQUATORIAL', getattr(swe, 'FLG_EQUATORIAL', 2048))
            | getattr(swe, 'SEFLG_TOPOCTR', getattr(swe, 'FLG_TOPOCTR', 32))
        )
        for name in planets:
            pid = PLANET_IDS.get(name)
            if pid is None:
                continue
            try:
                pos, _ = swe.calc_ut(jd_ut, pid, FLAGS)
                # For equatorial, Swiss Ephemeris returns RA & Dec in DEGREES.
                # Convert RA to sidereal hours for hour-angle math.
                ra_deg = float(pos[0])
                ra_hours = ra_deg / 15.0
                dec_deg = float(pos[1])
                out[name] = _az_alt_from_ra_dec(ra_hours, dec_deg, float(lat), lst_h)
            except Exception:
                continue
    return out


# Optional helpers for mapping/chart-angle interop
def chart_angle_from_asc_to_bearing(angle_from_asc_deg: float) -> float:
    """Convert a wheel angle measured CCW from ASC(East) to compass bearing (0°=N, 90°=E)."""
    try:
        a = float(angle_from_asc_deg)
    except Exception:
        a = 0.0
    return (90.0 + a) % 360.0


def back_azimuth(bearing_deg: float) -> float:
    """Return the opposite direction (only use when a rule explicitly calls for it)."""
    try:
        b = float(bearing_deg)
    except Exception:
        b = 0.0
    return (b + 180.0) % 360.0


def compute_local_space_diag(timestamp_iso: str, lat: float, lon: float, planets: Iterable[str]) -> Dict[str, Dict[str, float]]:
    """Return detailed intermediate values for local-space calculation per planet.

    Includes RA(deg), RA(hours), Dec, LST(hours), HA(deg), and the final azimuth/altitude.
    """
    if swe is None:
        raise RuntimeError("pyswisseph not available")
    out: Dict[str, Dict[str, float]] = {}
    with _SWE_TOPO_LOCK:
        try:
            swe.set_topo(lon, lat, 0.0)
        except Exception:
            pass
        jd_ut = _jd_ut_from_iso(timestamp_iso)
        lst_h = _lst_hours(jd_ut, lon)
        FLAGS = (
            getattr(swe, 'SEFLG_SWIEPH', getattr(swe, 'FLG_SWIEPH', 2))
            | getattr(swe, 'SEFLG_EQUATORIAL', getattr(swe, 'FLG_EQUATORIAL', 2048))
            | getattr(swe, 'SEFLG_TOPOCTR', getattr(swe, 'FLG_TOPOCTR', 32))
        )
        for name in planets:
            pid = PLANET_IDS.get(name)
            if pid is None:
                continue
            try:
                pos, _ = swe.calc_ut(jd_ut, pid, FLAGS)
                ra_deg = float(pos[0])
                ra_hours = ra_deg / 15.0
                dec_deg = float(pos[1])
                # Hour angle and alt/az
                ha_deg = (lst_h - ra_hours) * 15.0
                if ha_deg > 180.0: ha_deg -= 360.0
                if ha_deg < -180.0: ha_deg += 360.0
                altaz = _az_alt_from_ra_dec(ra_hours, dec_deg, float(lat), lst_h)
                out[name] = {
                    'ra_deg': ra_deg,
                    'ra_hours': ra_hours,
                    'dec_deg': dec_deg,
                    'lst_hours': lst_h,
                    'ha_deg': ha_deg,
                    'azimuth_deg': altaz['azimuth_deg'],
                    'altitude_deg': altaz['altitude_deg'],
                }
            except Exception:
                continue
    return out
