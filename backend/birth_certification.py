# -*- coding: utf-8 -*-
"""Birth-time certification and rectification scan helpers.

This module implements a source-compatible approximation of the rectification
workflow documented from the reference desktop tool:

* one natal candidate is scanned minute-by-minute over a <= 24 hour interval;
* every candidate is compared to dated life-event charts;
* event precision gates fast-moving dynamic points;
* weighted dynamic-to-natal aspects accumulate favorable and tense curves;
* curves are normalized to the same 0..100 style used by the reference export.

The implementation is intentionally data-driven. Exact proprietary tables for
all instruments, objects, and thematic groups are not embedded here; callers can
override the default weights once stronger parity data is available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from math import isfinite
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
from zoneinfo import ZoneInfo

from swisseph_state import (
    swisseph as swe,
    swisseph_ephemeris_path,
)


_PLANET_IDS: Tuple[Tuple[str, str], ...] = (
    ("Sun", "SUN"),
    ("Moon", "MOON"),
    ("Mercury", "MERCURY"),
    ("Venus", "VENUS"),
    ("Mars", "MARS"),
    ("Jupiter", "JUPITER"),
    ("Saturn", "SATURN"),
    ("Uranus", "URANUS"),
    ("Neptune", "NEPTUNE"),
    ("Pluto", "PLUTO"),
    ("North Node", "MEAN_NODE"),
    ("Chiron", "CHIRON"),
    ("Ceres", "CERES"),
    ("Pallas", "PALLAS"),
    ("Juno", "JUNO"),
    ("Vesta", "VESTA"),
    ("Lilith", "MEAN_APOG"),
)

_ASTEROID_NUMBER_POINTS: Tuple[Tuple[str, int], ...] = (
    ("Eros", 433),
    ("Psyche", 16),
    ("Proserpina", 26),
)

_CUSP_NAMES = (
    "Asc",
    "Cusp 2",
    "Cusp 3",
    "IC",
    "Cusp 5",
    "Cusp 6",
    "Dsc",
    "Cusp 8",
    "Cusp 9",
    "MC",
    "Cusp 11",
    "Cusp 12",
)

_FAST_FOR_COARSE_PRECISION = {"Moon", "Fortuna", "Cross", *_CUSP_NAMES}

_ASPECTS: Tuple[Tuple[str, float, float], ...] = (
    ("conjunction", 0.0, 0.99),
    ("semisquare", 45.0, -0.50),
    ("sextile", 60.0, 0.60),
    ("square", 90.0, -0.99),
    ("trine", 120.0, 0.95),
    ("sesquiquadrate", 135.0, -0.40),
    ("quincunx", 150.0, -0.20),
    ("opposition", 180.0, 0.90),
)

_INSTRUMENT_ALIASES = {
    "basic": "transit",
    "event": "transit",
    "transits": "transit",
    "transit": "transit",
    "direction": "direction_reverse",
    "direction_reverse": "direction_reverse",
    "solar_arc": "direction_reverse",
    "dr": "direction_reverse",
    "dr_arcsun": "direction_reverse",
    "profection": "profection_reverse",
    "profection_reverse": "profection_reverse",
    "dr_30": "profection_reverse",
    "primary": "primary_progression",
    "primary_progression": "primary_progression",
    "p1": "primary_progression",
    "secondary": "secondary_progression_local",
    "secondary_progression": "secondary_progression_local",
    "secondary_progression_local": "secondary_progression_local",
    "secondary_progression_natal": "secondary_progression_natal",
    "p2": "secondary_progression_local",
    "p2_local": "secondary_progression_local",
    "p2_natal": "secondary_progression_natal",
    "tertiary": "tertiary_progression",
    "tertiary_progression": "tertiary_progression",
    "p3": "tertiary_progression",
    "minor": "minor_progression",
    "minor_progression": "minor_progression",
    "pm": "minor_progression",
}

_DEFAULT_INSTRUMENTS = (
    {"id": "transit", "label": "T: Transits", "weight": 1.0, "planet_weight": 0.90, "angle_weight": 0.30, "galaxy_id": 1},
    {"id": "direction_reverse", "label": "Dr-ArcSun=YearTrop: Direction reverse", "weight": 1.0, "planet_weight": 0.80, "angle_weight": 0.80, "galaxy_id": 2},
    {"id": "profection_reverse", "label": "DR-30=YearTrop: Profection reverse", "weight": 1.0, "planet_weight": 0.50, "angle_weight": 0.50, "galaxy_id": 12},
    {"id": "primary_progression", "label": "P1-EQL-Nat-ArcSun=YearTrop: Primary progression", "weight": 1.0, "planet_weight": 0.0, "angle_weight": 0.99, "galaxy_id": 20},
    {"id": "secondary_progression_local", "label": "P2-Loc-TrueDay=YearTrop: Secondary progression", "weight": 1.0, "planet_weight": 0.99, "angle_weight": 0.70, "galaxy_id": 26},
    {"id": "secondary_progression_natal", "label": "P2-Nat-TrueDay=YearTrop: Secondary progression", "weight": 1.0, "planet_weight": 0.99, "angle_weight": 0.70, "galaxy_id": 89},
    {"id": "tertiary_progression", "label": "P3-MoonDay=MonthTrop: Tertiary progression", "weight": 1.0, "planet_weight": 0.90, "angle_weight": 0.60, "galaxy_id": 28},
    {"id": "minor_progression", "label": "PM-MonthTrop=YearTrop: Minor progression", "weight": 1.0, "planet_weight": 0.70, "angle_weight": 0.40, "galaxy_id": 29},
)

_INSTRUMENT_SCALES = {
    "direction_reverse": -1.0 / 365.2422,
    "profection_reverse": -30.0 / 365.2422,
    "primary_progression": 0.000008,
    "secondary_progression_local": 1.0 / 365.2422,
    "secondary_progression_natal": 1.0 / 365.2422,
    "tertiary_progression": 0.03784,
    "minor_progression": 0.074804,
}


@dataclass(frozen=True)
class RectificationEvent:
    label: str
    timestamp: datetime
    latitude: float
    longitude: float
    timezone_name: Optional[str] = None
    precision: int = 1
    theme: Optional[str] = None
    weight: float = 1.0
    source_note: Optional[str] = None


@dataclass
class RectificationSettings:
    birth_date: date
    birth_latitude: float
    birth_longitude: float
    birth_timezone: str = "UTC"
    birth_location: Optional[str] = None
    search_start_time: time = time(0, 0)
    search_end_time: time = time(23, 59)
    house_system: str = "T"
    orb_degrees: float = 1.0
    level_percent: int = 67
    include_series: bool = True
    max_rows: int = 1441
    source_time_status: str = "unknown"
    instruments: Sequence[Union[Mapping[str, Any], str]] = field(default_factory=lambda: list(_DEFAULT_INSTRUMENTS))
    object_weights: Mapping[str, float] = field(default_factory=dict)
    aspect_weights: Mapping[str, float] = field(default_factory=dict)


@dataclass
class _Point:
    name: str
    longitude: float
    kind: str
    speed: float = 0.0


@dataclass
class _RawRow:
    timestamp: datetime
    raw_plus: float = 0.0
    raw_minus: float = 0.0
    hit_count: int = 0
    event_hits: Dict[str, int] = field(default_factory=dict)


def _wrap360(value: float) -> float:
    return float(value) % 360.0


def _signed_delta(end_degrees: float, start_degrees: float) -> float:
    return ((_wrap360(end_degrees) - _wrap360(start_degrees) + 540.0) % 360.0) - 180.0


def _separation(a: float, b: float) -> float:
    return abs(_signed_delta(a, b))


def _coerce_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not isfinite(number):
        return default
    return number


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _zone(name: Optional[str]) -> timezone | ZoneInfo:
    if not name:
        return timezone.utc
    try:
        return ZoneInfo(str(name))
    except Exception:
        return timezone.utc


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not value:
        raise ValueError("birth_date is required")
    return date.fromisoformat(str(value)[:10])


def _parse_time(value: Any, default: time) -> time:
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if not value:
        return default
    text = str(value).strip()
    if len(text) == 5:
        text = f"{text}:00"
    return time.fromisoformat(text).replace(second=0, microsecond=0)


def _parse_datetime(value: Any, tz_name: Optional[str]) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif value:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    else:
        raise ValueError("event timestamp is required")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_zone(tz_name))
    return dt


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _event_precision_offset(precision: int) -> Optional[timedelta]:
    # Mirrors the reference precision cases:
    # 0 skip, 1 exact, 2 minutes, 3 hours, 4 days, 5 weeks, 6 months.
    if precision <= 0:
        return None
    if precision == 1:
        return timedelta(0)
    if precision == 2:
        return timedelta(minutes=15)
    if precision == 3:
        return timedelta(hours=3)
    if precision == 4:
        return timedelta(days=3)
    if precision == 5:
        return timedelta(days=21)
    if precision >= 6:
        return timedelta(days=90)
    return timedelta(0)


def _add_months(dt: datetime, months: int) -> datetime:
    month_index = (dt.month - 1) + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    month_lengths = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return dt.replace(year=year, month=month, day=min(dt.day, month_lengths[month - 1]))


def _shift_datetime_for_precision(dt: datetime, precision: int) -> Optional[datetime]:
    """Apply the same precision probe shift used by the reference workflow."""
    if precision <= 0:
        return None
    if precision == 6:
        return _add_months(dt, 3)
    offset = _event_precision_offset(precision)
    if offset is None:
        return None
    return dt + offset


def _julian_day(dt_utc: datetime) -> float:
    if swe is None:
        raise RuntimeError("Swiss Ephemeris is unavailable")
    dt = _to_utc(dt_utc)
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + dt.microsecond / 3_600_000_000.0
    return float(swe.julday(dt.year, dt.month, dt.day, hour, getattr(swe, "GREG_CAL", 1)))


def _build_points(
    dt_utc: datetime,
    latitude: float,
    longitude: float,
    house_system: str = "T",
) -> Dict[str, _Point]:
    if swe is None:
        raise RuntimeError("Swiss Ephemeris is unavailable")
    jd_ut = _julian_day(dt_utc)
    out: Dict[str, _Point] = {}
    flags = getattr(swe, "FLG_SWIEPH", 2) | getattr(swe, "FLG_SPEED", 256)

    def add_body(name: str, point_id: Any, kind: str = "planet") -> None:
        if point_id is None:
            return
        try:
            pos, _ret = swe.calc_ut(jd_ut, point_id, flags)
        except Exception:
            return
        speed = float(pos[3]) if len(pos) > 3 else 0.0
        out[name] = _Point(name=name, longitude=_wrap360(float(pos[0])), kind=kind, speed=speed)

    with swisseph_ephemeris_path("", swe_module=swe):
        for name, attr in _PLANET_IDS:
            add_body(name, getattr(swe, attr, None))
        asteroid_offset = getattr(swe, "AST_OFFSET", 10000)
        for name, number in _ASTEROID_NUMBER_POINTS:
            add_body(name, asteroid_offset + number, kind="asteroid")
        house_code = (house_system or "T").strip()[:1].encode("ascii", "ignore") or b"T"
        try:
            cusps, ascmc = swe.houses(jd_ut, float(latitude), float(longitude), house_code)
        except Exception:
            cusps, ascmc = swe.houses(jd_ut, float(latitude), float(longitude), b"P")
    asc = _wrap360(float(ascmc[0]))
    mc = _wrap360(float(ascmc[1]))
    normalized_cusps = [_wrap360(float(value)) for value in list(cusps)[:12]]
    if len(normalized_cusps) >= 12:
        for index, name in enumerate(_CUSP_NAMES):
            kind = "angle" if name in {"Asc", "IC", "Dsc", "MC"} else "cusp"
            out[name] = _Point(name=name, longitude=normalized_cusps[index], kind=kind)
    out["Asc"] = _Point(name="Asc", longitude=asc, kind="angle")
    out["MC"] = _Point(name="MC", longitude=mc, kind="angle")
    out["Dsc"] = _Point(name="Dsc", longitude=_wrap360(asc + 180.0), kind="angle")
    out["IC"] = _Point(name="IC", longitude=_wrap360(mc + 180.0), kind="angle")
    if len(ascmc) > 2:
        out["ARMC"] = _Point(name="ARMC", longitude=_wrap360(float(ascmc[2])), kind="aux_angle")
    if len(ascmc) > 3:
        out["Vertex"] = _Point(name="Vertex", longitude=_wrap360(float(ascmc[3])), kind="aux_angle")
    if len(ascmc) > 4:
        out["EqAsc"] = _Point(name="EqAsc", longitude=_wrap360(float(ascmc[4])), kind="aux_angle")
    if len(ascmc) > 5:
        out["CoAsc_Koh"] = _Point(name="CoAsc_Koh", longitude=_wrap360(float(ascmc[5])), kind="aux_angle")
    if len(ascmc) > 6:
        out["CoAsc_Munk"] = _Point(name="CoAsc_Munk", longitude=_wrap360(float(ascmc[6])), kind="aux_angle")
    if len(ascmc) > 7:
        out["PolarAsc_Munk"] = _Point(name="PolarAsc_Munk", longitude=_wrap360(float(ascmc[7])), kind="aux_angle")
    north = out.get("North Node")
    if north:
        out["South Node"] = _Point(name="South Node", longitude=_wrap360(north.longitude + 180.0), kind="node", speed=north.speed)
    sun = out.get("Sun")
    moon = out.get("Moon")
    if sun and moon:
        # Galaxy exposes Fortuna/Cross as chart objects. This keeps the paired lots
        # deterministic for rectification even when the exact proprietary variant
        # is not exported.
        fortune = _wrap360(asc + moon.longitude - sun.longitude)
        cross = _wrap360(asc + sun.longitude - moon.longitude)
        out["Fortuna"] = _Point(name="Fortuna", longitude=fortune, kind="lot")
        out["Cross"] = _Point(name="Cross", longitude=cross, kind="lot")
    return out


def _instrument_id(raw: Mapping[str, Any] | str) -> str:
    if isinstance(raw, str):
        key = raw
    else:
        key = str(raw.get("id") or raw.get("kind") or raw.get("name") or "transit")
    return _INSTRUMENT_ALIASES.get(key.strip().lower(), key.strip().lower())


def _instrument_weight(raw: Mapping[str, Any] | str) -> float:
    if isinstance(raw, str):
        return 1.0
    return _coerce_float(raw.get("weight"), 1.0) or 1.0


def _default_instrument(raw_id: str) -> Mapping[str, Any]:
    instrument_id = _INSTRUMENT_ALIASES.get(str(raw_id).strip().lower(), str(raw_id).strip().lower())
    for item in _DEFAULT_INSTRUMENTS:
        if item["id"] == instrument_id:
            return item
    return {}


def _is_angle_like(point: _Point) -> bool:
    return point.kind in {"angle", "cusp", "aux_angle"}


def _is_galaxy_dynamic_point(point: _Point) -> bool:
    return point.kind in {"planet", "node", "lot", "asteroid"}


def _is_galaxy_natal_target(point: _Point) -> bool:
    return point.kind in {"planet", "node", "lot", "asteroid", "angle", "cusp"}


def _instrument_axis_weight(raw: Mapping[str, Any] | str, point: _Point) -> float:
    instrument_id = _instrument_id(raw)
    defaults = _default_instrument(instrument_id)
    key = "angle_weight" if _is_angle_like(point) else "planet_weight"
    if isinstance(raw, Mapping) and raw.get(key) is not None:
        value = _coerce_float(raw.get(key), None)
    else:
        value = _coerce_float(defaults.get(key), None)
    if value is None:
        value = 1.0
    return value * _instrument_weight(raw)


def _progressed_datetime(birth_utc: datetime, event_utc: datetime) -> datetime:
    age_days = (_to_utc(event_utc) - _to_utc(birth_utc)).total_seconds() / 86400.0
    age_years = max(0.0, age_days / 365.2422)
    return _to_utc(birth_utc) + timedelta(days=age_years)


def _scaled_progressed_datetime(birth_utc: datetime, event_utc: datetime, scale_days_per_day: float) -> datetime:
    age_days = max(0.0, (_to_utc(event_utc) - _to_utc(birth_utc)).total_seconds() / 86400.0)
    return _to_utc(birth_utc) + timedelta(days=age_days * scale_days_per_day)


def _age_years(birth_utc: datetime, event_utc: datetime) -> float:
    age_days = max(0.0, (_to_utc(event_utc) - _to_utc(birth_utc)).total_seconds() / 86400.0)
    return age_days / 365.2422


def _shift_points(points: Mapping[str, _Point], arc_degrees: float) -> Dict[str, _Point]:
    return {
        name: _Point(name=name, longitude=_wrap360(point.longitude + arc_degrees), kind=point.kind, speed=point.speed)
        for name, point in points.items()
    }


def _solar_arc_points(
    birth_utc: datetime,
    event_utc: datetime,
    natal_points: Mapping[str, _Point],
    settings: RectificationSettings,
    direction: float,
) -> Dict[str, _Point]:
    progressed = _build_points(
        _progressed_datetime(birth_utc, event_utc),
        settings.birth_latitude,
        settings.birth_longitude,
        settings.house_system,
    )
    natal_sun = natal_points.get("Sun")
    prog_sun = progressed.get("Sun")
    arc = _signed_delta(prog_sun.longitude, natal_sun.longitude) * direction if natal_sun and prog_sun else 0.0
    return _shift_points(natal_points, arc)


def _dynamic_points_for_instrument(
    instrument_id: str,
    birth_utc: datetime,
    event_utc: datetime,
    event: RectificationEvent,
    natal_points: Mapping[str, _Point],
    settings: RectificationSettings,
) -> Dict[str, _Point]:
    if instrument_id == "secondary_progression_local":
        return _build_points(
            _progressed_datetime(birth_utc, event_utc),
            settings.birth_latitude,
            settings.birth_longitude,
            settings.house_system,
        )
    if instrument_id == "secondary_progression_natal":
        return _build_points(
            _progressed_datetime(birth_utc, event_utc),
            settings.birth_latitude,
            settings.birth_longitude,
            settings.house_system,
        )
    if instrument_id == "direction_reverse":
        return _solar_arc_points(birth_utc, event_utc, natal_points, settings, direction=-1.0)
    if instrument_id == "profection_reverse":
        return _shift_points(natal_points, -30.0 * _age_years(birth_utc, event_utc))
    if instrument_id == "primary_progression":
        return _shift_points(natal_points, _age_years(birth_utc, event_utc) * 0.0029)
    if instrument_id == "tertiary_progression":
        return _build_points(
            _scaled_progressed_datetime(birth_utc, event_utc, _INSTRUMENT_SCALES["tertiary_progression"]),
            settings.birth_latitude,
            settings.birth_longitude,
            settings.house_system,
        )
    if instrument_id == "minor_progression":
        return _build_points(
            _scaled_progressed_datetime(birth_utc, event_utc, _INSTRUMENT_SCALES["minor_progression"]),
            settings.birth_latitude,
            settings.birth_longitude,
            settings.house_system,
        )
    return _build_points(event_utc, event.latitude, event.longitude, settings.house_system)


def _allowed_dynamic_points(
    base_points: Mapping[str, _Point],
    shifted_points: Mapping[str, _Point],
    precision: int,
) -> Dict[str, bool]:
    offset = _event_precision_offset(precision)
    if offset is None:
        return {name: False for name in base_points}
    if offset.total_seconds() == 0:
        return {name: True for name in base_points}
    coarse_days = abs(offset.total_seconds()) / 86400.0
    allowed: Dict[str, bool] = {}
    for name, point in base_points.items():
        shifted = shifted_points.get(name)
        if shifted is None:
            allowed[name] = False
            continue
        if coarse_days > 0.999 and name in _FAST_FOR_COARSE_PRECISION:
            allowed[name] = False
            continue
        allowed[name] = _separation(point.longitude, shifted.longitude) <= 1.0
    return allowed


def _aspect_match(dynamic_lon: float, natal_lon: float, orb_degrees: float, aspect_overrides: Mapping[str, float]) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    for name, angle, default_coeff in _ASPECTS:
        orb = abs(_separation(dynamic_lon, natal_lon) - angle)
        if orb > orb_degrees:
            continue
        coeff = _coerce_float(aspect_overrides.get(name), default_coeff) or default_coeff
        score_factor = max(0.0, 1.0 - (orb / max(orb_degrees, 0.0001)))
        row = {"aspect": name, "angle": angle, "orb": orb, "coefficient": coeff, "factor": score_factor}
        if best is None or row["orb"] < best["orb"]:
            best = row
    return best


def _object_weight(name: str, kind: str, overrides: Mapping[str, float]) -> float:
    if name in overrides:
        return _coerce_float(overrides.get(name), 1.0) or 1.0
    if kind == "angle":
        return _coerce_float(overrides.get("angle"), 1.35) or 1.35
    if kind == "cusp":
        return _coerce_float(overrides.get("cusp"), 1.20) or 1.20
    if kind == "aux_angle":
        return _coerce_float(overrides.get("aux_angle"), 1.10) or 1.10
    if kind == "lot":
        return _coerce_float(overrides.get("lot"), 1.05) or 1.05
    if kind == "node":
        return _coerce_float(overrides.get("node"), 1.0) or 1.0
    if kind == "asteroid":
        return _coerce_float(overrides.get("asteroid"), 0.85) or 0.85
    return _coerce_float(overrides.get("planet"), 1.0) or 1.0


def normalize_rectification_rows(raw_rows: Sequence[_RawRow]) -> Tuple[List[Dict[str, Any]], float]:
    """Normalize raw plus/minus rows using the reference max/min-floor formula."""
    if not raw_rows:
        return [], 0.0
    max_abs = 0.0
    min_abs = 1e18
    for row in raw_rows:
        max_abs = max(max_abs, abs(row.raw_plus), abs(row.raw_minus))
        min_abs = min(min_abs, abs(row.raw_plus), abs(row.raw_minus))
    floor = min_abs * 0.9
    amplitude = max(0.0, max_abs - floor)
    normalized: List[Dict[str, Any]] = []
    for row in raw_rows:
        if amplitude > 1e-9 and row.raw_plus > 0:
            favorable = max(0.0, (abs(row.raw_plus) - floor) / amplitude)
        else:
            favorable = 0.0
        if amplitude > 1e-9 and row.raw_minus < 0:
            tense = max(0.0, (abs(row.raw_minus) - floor) / amplitude)
        else:
            tense = 0.0
        favorable_percent = round(favorable * 100.0, 2)
        tense_percent = round(tense * 100.0, 2)
        strength = max(favorable_percent, tense_percent)
        if favorable_percent > tense_percent:
            dominant_curve = "favorable"
        elif tense_percent > favorable_percent:
            dominant_curve = "tense"
        else:
            dominant_curve = "neutral"
        normalized.append(
            {
                "timestamp": row.timestamp.isoformat(),
                "favorable": favorable_percent,
                "tense": tense_percent,
                "strength": strength,
                "dominant_curve": dominant_curve,
                "raw_plus": round(row.raw_plus, 6),
                "raw_minus": round(row.raw_minus, 6),
                "hit_count": row.hit_count,
                "event_hits": dict(sorted(row.event_hits.items())),
            }
        )
    return normalized, amplitude


def extract_rectification_periods(rows: Sequence[Mapping[str, Any]], level_percent: int = 67) -> List[Dict[str, Any]]:
    """Extract contiguous minute periods where either curve reaches threshold."""
    periods: List[Dict[str, Any]] = []
    active: Optional[Dict[str, Any]] = None
    for row in rows:
        fav = _coerce_float(row.get("favorable"), 0.0) or 0.0
        tense = _coerce_float(row.get("tense"), 0.0) or 0.0
        strength = max(fav, tense)
        passes = fav >= level_percent or tense >= level_percent
        timestamp = str(row.get("timestamp"))
        if passes:
            if active is None:
                active = {
                    "start": timestamp,
                    "end": timestamp,
                    "peak_favorable": round(fav, 2),
                    "peak_tense": round(tense, 2),
                    "peak_strength": round(strength, 2),
                    "dominant_curve": "favorable" if fav >= tense else "tense",
                    "duration_minutes": 1,
                }
            else:
                active["end"] = timestamp
                active["peak_favorable"] = round(max(float(active["peak_favorable"]), fav), 2)
                active["peak_tense"] = round(max(float(active["peak_tense"]), tense), 2)
                active["peak_strength"] = round(max(float(active["peak_strength"]), strength), 2)
                active["duration_minutes"] = int(active.get("duration_minutes", 0)) + 1
                active["dominant_curve"] = "favorable" if float(active["peak_favorable"]) >= float(active["peak_tense"]) else "tense"
        elif active is not None:
            periods.append(active)
            active = None
    if active is not None:
        periods.append(active)
    return periods


def classify_certification(
    rows: Sequence[Mapping[str, Any]],
    events: Sequence[RectificationEvent],
    settings: RectificationSettings,
) -> Dict[str, Any]:
    source_status = (settings.source_time_status or "unknown").strip().lower()
    if source_status in {"aa", "record", "certificate", "family_exact", "certified"}:
        return {
            "status": "certified_source",
            "confidence": "high",
            "reason": "Birth time is marked as externally sourced; rectification is not required to certify it.",
        }
    ranked = sorted(rows, key=lambda r: max(_coerce_float(r.get("favorable"), 0.0) or 0.0, _coerce_float(r.get("tense"), 0.0) or 0.0), reverse=True)
    if not ranked:
        return {"status": "insufficient_data", "confidence": "none", "reason": "No scan rows were produced."}
    top_metric = _coerce_float(ranked[0].get("strength"), 0.0) or max(_coerce_float(ranked[0].get("favorable"), 0.0) or 0.0, _coerce_float(ranked[0].get("tense"), 0.0) or 0.0)
    second_metric = (
        (_coerce_float(ranked[1].get("strength"), 0.0) or max(_coerce_float(ranked[1].get("favorable"), 0.0) or 0.0, _coerce_float(ranked[1].get("tense"), 0.0) or 0.0))
        if len(ranked) > 1
        else 0.0
    )
    near_exact_events = sum(1 for event in events if event.precision in {1, 2, 3, 4})
    unique_themes = {event.theme or event.label for event in events}
    candidate = {
        "timestamp": ranked[0].get("timestamp"),
        "strength": round(top_metric, 2),
        "dominant_curve": ranked[0].get("dominant_curve"),
        "favorable": ranked[0].get("favorable"),
        "tense": ranked[0].get("tense"),
    }
    data_quality = {
        "event_count": len(events),
        "near_exact_event_count": near_exact_events,
        "independent_theme_count": len(unique_themes),
        "month_or_weaker_event_count": sum(1 for event in events if event.precision >= 6),
    }
    if top_metric >= 95.0 and (top_metric - second_metric) >= 2.0 and near_exact_events >= 3 and len(unique_themes) >= 3:
        return {
            "status": "rectified_candidate",
            "confidence": "medium",
            "reason": "A strong top minute exists across multiple relatively precise and independent events, but this is still rectification rather than external certification.",
            "candidate": candidate,
            "data_quality": data_quality,
        }
    return {
        "status": "unresolved_rectification",
        "confidence": "low",
        "reason": "The scan does not produce a sufficiently isolated, independently supported candidate.",
        "candidate": candidate,
        "data_quality": data_quality,
    }


def _parse_events(values: Iterable[Mapping[str, Any]]) -> List[RectificationEvent]:
    events: List[RectificationEvent] = []
    for idx, item in enumerate(values):
        label = str(item.get("label") or item.get("name") or f"Event {idx + 1}").strip()
        tz_name = item.get("timezone") or item.get("timezone_name")
        timestamp = _parse_datetime(item.get("timestamp") or item.get("datetime"), str(tz_name) if tz_name else None)
        lat = _coerce_float(item.get("latitude") if item.get("latitude") is not None else item.get("lat"))
        lon = _coerce_float(item.get("longitude") if item.get("longitude") is not None else item.get("lon"))
        if lat is None or lon is None:
            raise ValueError(f"{label}: latitude and longitude are required")
        events.append(
            RectificationEvent(
                label=label,
                timestamp=timestamp,
                latitude=lat,
                longitude=lon,
                timezone_name=str(tz_name) if tz_name else None,
                precision=max(0, _coerce_int(item.get("precision"), 1)),
                theme=str(item.get("theme")).strip() if item.get("theme") else None,
                weight=_coerce_float(item.get("weight"), 1.0) or 1.0,
                source_note=str(item.get("source_note")).strip() if item.get("source_note") else None,
            )
        )
    return events


def settings_from_payload(payload: Mapping[str, Any]) -> Tuple[RectificationSettings, List[RectificationEvent]]:
    birth = payload.get("birth") if isinstance(payload.get("birth"), Mapping) else payload
    search = payload.get("search") if isinstance(payload.get("search"), Mapping) else {}
    birth_date = _parse_date(birth.get("date") or birth.get("birth_date"))
    lat = _coerce_float(birth.get("latitude") if birth.get("latitude") is not None else birth.get("lat"))
    lon = _coerce_float(birth.get("longitude") if birth.get("longitude") is not None else birth.get("lon"))
    if lat is None or lon is None:
        raise ValueError("birth latitude and longitude are required")
    settings = RectificationSettings(
        birth_date=birth_date,
        birth_latitude=lat,
        birth_longitude=lon,
        birth_timezone=str(birth.get("timezone") or birth.get("timezone_name") or "UTC"),
        birth_location=str(birth.get("location")).strip() if birth.get("location") else None,
        search_start_time=_parse_time(search.get("start_time") or payload.get("search_start_time"), time(0, 0)),
        search_end_time=_parse_time(search.get("end_time") or payload.get("search_end_time"), time(23, 59)),
        house_system=str(payload.get("house_system_code") or payload.get("house_system") or birth.get("house_system") or "T")[:1],
        orb_degrees=max(0.1, _coerce_float(payload.get("orb_degrees"), 1.0) or 1.0),
        level_percent=max(1, min(100, _coerce_int(payload.get("level_percent"), 67))),
        include_series=str(payload.get("include_series", "true")).lower() not in {"0", "false", "no"},
        max_rows=max(1, _coerce_int(payload.get("max_rows"), 1441)),
        source_time_status=str(birth.get("source_time_status") or birth.get("time_status") or "unknown"),
        instruments=payload.get("instruments") if isinstance(payload.get("instruments"), Sequence) and not isinstance(payload.get("instruments"), (str, bytes)) else list(_DEFAULT_INSTRUMENTS),
        object_weights=payload.get("object_weights") if isinstance(payload.get("object_weights"), Mapping) else {},
        aspect_weights=payload.get("aspect_weights") if isinstance(payload.get("aspect_weights"), Mapping) else {},
    )
    events = _parse_events(payload.get("events") or [])
    if not events:
        raise ValueError("at least one rectification event is required")
    return settings, events


def rectify_birth_time(settings: RectificationSettings, events: Sequence[RectificationEvent]) -> Dict[str, Any]:
    if not events:
        raise ValueError("at least one rectification event is required")
    start_local = datetime.combine(settings.birth_date, settings.search_start_time, tzinfo=_zone(settings.birth_timezone))
    end_local = datetime.combine(settings.birth_date, settings.search_end_time, tzinfo=_zone(settings.birth_timezone))
    if end_local < start_local:
        raise ValueError("search end must be on or after search start")
    total_minutes = int(round((end_local - start_local).total_seconds() / 60.0)) + 1
    if total_minutes > settings.max_rows or total_minutes > 1441:
        raise ValueError("birth-time search range must be 24 hours or less")

    instruments = list(settings.instruments or _DEFAULT_INSTRUMENTS)
    raw_rows: List[_RawRow] = []
    for idx in range(total_minutes):
        candidate_local = start_local + timedelta(minutes=idx)
        candidate_utc = _to_utc(candidate_local)
        natal_points = _build_points(candidate_utc, settings.birth_latitude, settings.birth_longitude, settings.house_system)
        row = _RawRow(timestamp=candidate_local)
        for event in events:
            event_utc = _to_utc(event.timestamp)
            precision_offset = _event_precision_offset(event.precision)
            if precision_offset is None:
                continue
            for raw_instrument in instruments:
                instrument_id = _instrument_id(raw_instrument)
                dynamic_points = _dynamic_points_for_instrument(
                    instrument_id, candidate_utc, event_utc, event, natal_points, settings
                )
                shifted_event_utc = _shift_datetime_for_precision(event_utc, event.precision)
                if shifted_event_utc is None:
                    continue
                if shifted_event_utc == event_utc:
                    shifted_points = dynamic_points
                else:
                    shifted_points = _dynamic_points_for_instrument(
                        instrument_id,
                        candidate_utc,
                        shifted_event_utc,
                        event,
                        natal_points,
                        settings,
                    )
                allowed = _allowed_dynamic_points(dynamic_points, shifted_points, event.precision)
                for natal_name, natal in natal_points.items():
                    if not _is_galaxy_natal_target(natal):
                        continue
                    natal_weight = _object_weight(natal_name, natal.kind, settings.object_weights)
                    for dynamic_name, dynamic in dynamic_points.items():
                        if not _is_galaxy_dynamic_point(dynamic):
                            continue
                        if not allowed.get(dynamic_name, False):
                            continue
                        match = _aspect_match(
                            dynamic.longitude,
                            natal.longitude,
                            settings.orb_degrees,
                            settings.aspect_weights,
                        )
                        if not match:
                            continue
                        dynamic_weight = _object_weight(dynamic_name, dynamic.kind, settings.object_weights)
                        natal_axis_weight = _instrument_axis_weight(raw_instrument, natal)
                        dynamic_axis_weight = _instrument_axis_weight(raw_instrument, dynamic)
                        contribution = (
                            (natal_axis_weight * natal_weight + dynamic_axis_weight * dynamic_weight)
                            * event.weight
                            * abs(float(match["coefficient"]))
                            * float(match["factor"])
                        )
                        if contribution <= 0:
                            continue
                        row.hit_count += 1
                        row.event_hits[event.label] = row.event_hits.get(event.label, 0) + 1
                        if float(match["coefficient"]) < 0:
                            row.raw_minus -= contribution
                        else:
                            row.raw_plus += contribution
        raw_rows.append(row)

    rows, amplitude = normalize_rectification_rows(raw_rows)
    ranked = sorted(
        rows,
        key=lambda r: (
            max(_coerce_float(r.get("favorable"), 0.0) or 0.0, _coerce_float(r.get("tense"), 0.0) or 0.0),
            _coerce_float(r.get("hit_count"), 0.0) or 0.0,
        ),
        reverse=True,
    )
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    periods = extract_rectification_periods(rows, settings.level_percent)
    for rank, period in enumerate(sorted(periods, key=lambda item: float(item.get("peak_strength") or 0.0), reverse=True), start=1):
        period["rank"] = rank
    payload = {
        "model": "birth_time_certification_rectification",
        "algorithm": "minute_scan_event_instrument_aspect_weights_v1",
        "meta": {
            "birth_date": settings.birth_date.isoformat(),
            "birth_location": settings.birth_location,
            "birth_timezone": settings.birth_timezone,
            "birth_latitude": settings.birth_latitude,
            "birth_longitude": settings.birth_longitude,
            "house_system": settings.house_system,
            "orb_degrees": settings.orb_degrees,
            "level_percent": settings.level_percent,
            "row_count": len(rows),
            "normalization_amplitude": round(amplitude, 6),
            "parity_note": "Reference-compatible workflow; proprietary thematic/object/instrument tables are configurable and not fully embedded.",
        },
        "events": [
            {
                "label": event.label,
                "timestamp": event.timestamp.isoformat(),
                "latitude": event.latitude,
                "longitude": event.longitude,
                "timezone": event.timezone_name,
                "precision": event.precision,
                "theme": event.theme,
                "weight": event.weight,
                "source_note": event.source_note,
            }
            for event in events
        ],
        "instruments": [
            {
                "id": _instrument_id(item),
                "label": str(item.get("label") or item.get("name") or _instrument_id(item)) if isinstance(item, Mapping) else str(item),
                "weight": _instrument_weight(item),
                "planet_weight": _instrument_axis_weight(item, _Point("planet", 0.0, "planet")),
                "angle_weight": _instrument_axis_weight(item, _Point("angle", 0.0, "angle")),
            }
            for item in instruments
        ],
        "top_candidates": ranked[:20],
        "periods": periods,
        "certification": classify_certification(rows, events, settings),
    }
    if settings.include_series:
        payload["series"] = rows
    return payload


def rectify_birth_time_from_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    settings, events = settings_from_payload(payload)
    return rectify_birth_time(settings, events)


__all__ = [
    "RectificationEvent",
    "RectificationSettings",
    "classify_certification",
    "extract_rectification_periods",
    "normalize_rectification_rows",
    "rectify_birth_time",
    "rectify_birth_time_from_payload",
    "settings_from_payload",
]
