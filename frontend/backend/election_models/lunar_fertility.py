from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple
from zoneinfo import ZoneInfo

from swisseph_state import swisseph_lock

from .common import Score, _collect_planets, _safe_float, _sign_from_lon


LUNAR_CYCLE_DAYS = 27.321582794
HALF_LUNAR_CYCLE_DAYS = LUNAR_CYCLE_DAYS / 2.0
MOON_MAX_SPEED_DIVISOR = 18.505416991
ANCHOR_TOLERANCE_DEG = 1.0 / 3600.0
ANCHOR_MAX_ITERATIONS = 13
WINDOW_BEFORE_HOURS = 12.0
WINDOW_AFTER_HOURS = 24.0

MASCULINE_SIGNS = {"Aries", "Gemini", "Leo", "Libra", "Sagittarius", "Aquarius"}
FEMININE_SIGNS = {"Taurus", "Cancer", "Virgo", "Scorpio", "Capricorn", "Pisces"}
VALID_CONSIDER_MODES = {"phase", "phase_and_antiphase", "antiphase"}


class LunarEphemeris(Protocol):
    def longitude_at(self, dt_utc: datetime, body: str) -> float:
        ...


@dataclass(frozen=True)
class LunarFertilitySignature:
    sun_longitude: float
    moon_longitude: float
    target_elongation: float
    natal_branch: bool


@dataclass(frozen=True)
class LunarFertilityAnchor:
    timestamp: datetime
    phase_kind: str
    branch: bool
    elongation: float
    target_elongation: float


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_consider_mode(value: Optional[str]) -> str:
    raw = str(value or "phase_and_antiphase").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "both": "phase_and_antiphase",
        "main_and_antiphase": "phase_and_antiphase",
        "phase_antiphase": "phase_and_antiphase",
        "phase+antiphase": "phase_and_antiphase",
        "main_phase": "phase",
        "main": "phase",
    }
    mode = aliases.get(raw, raw)
    if mode not in VALID_CONSIDER_MODES:
        raise ValueError("consider_mode must be phase, phase_and_antiphase, or antiphase")
    return mode


def moon_branch_and_elongation(sun_longitude: float, moon_longitude: float) -> Tuple[bool, float]:
    """Return (Moon-ahead branch, short-arc Sun-Moon elongation)."""

    sun = float(sun_longitude) % 360.0
    moon = float(moon_longitude) % 360.0
    delta = (moon - sun) % 360.0
    if delta <= 180.0:
        return True, delta
    return False, 360.0 - delta


def _planet_longitude(chart_data: Dict[str, Any], name: str) -> Optional[float]:
    planets = _collect_planets(chart_data or {})
    row = planets.get(name)
    if not isinstance(row, dict):
        return None
    return _safe_float(row.get("longitude"))


def extract_natal_lunar_signature(natal_chart_data: Dict[str, Any]) -> LunarFertilitySignature:
    sun_lon = _planet_longitude(natal_chart_data, "Sun")
    moon_lon = _planet_longitude(natal_chart_data, "Moon")
    if sun_lon is None or moon_lon is None:
        raise ValueError("Lunar Fertility Windows requires natal Sun and Moon longitudes")
    branch, elongation = moon_branch_and_elongation(sun_lon, moon_lon)
    return LunarFertilitySignature(
        sun_longitude=float(sun_lon) % 360.0,
        moon_longitude=float(moon_lon) % 360.0,
        target_elongation=float(elongation),
        natal_branch=bool(branch),
    )


def _phase_kind_for_branch(branch: bool, natal_branch: bool) -> str:
    return "phase" if bool(branch) == bool(natal_branch) else "antiphase"


def _mode_accepts_phase_kind(phase_kind: str, consider_mode: str) -> bool:
    mode = normalize_consider_mode(consider_mode)
    if mode == "phase_and_antiphase":
        return True
    return phase_kind == mode


class SwissEphemerisAdapter:
    def __init__(self, *, ephemeris_path: Optional[str] = None, swe_module: Any = None):
        if swe_module is None:
            try:
                import swisseph as swe_module  # type: ignore
            except Exception as exc:  # pragma: no cover
                raise RuntimeError("Swiss Ephemeris is unavailable") from exc
        self.swe = swe_module
        try:
            with swisseph_lock():
                self.swe.set_ephe_path(ephemeris_path or "")
        except Exception:
            pass

    def longitude_at(self, dt_utc: datetime, body: str) -> float:
        dt = _normalize_utc(dt_utc)
        hour = dt.hour + (dt.minute / 60.0) + (dt.second / 3600.0) + (dt.microsecond / 3_600_000_000.0)
        jd_ut = self.swe.julday(dt.year, dt.month, dt.day, hour, getattr(self.swe, "GREG_CAL", 1))
        body_key = str(body or "").strip().lower()
        if body_key == "sun":
            point_id = getattr(self.swe, "SUN")
        elif body_key == "moon":
            point_id = getattr(self.swe, "MOON")
        else:
            raise ValueError(f"Unsupported lunar fertility body: {body}")
        speed_flag = getattr(self.swe, "FLG_SPEED", 0)
        with swisseph_lock():
            try:
                flags = getattr(self.swe, "FLG_SWIEPH", 2) | speed_flag
                pos, _ = self.swe.calc_ut(jd_ut, point_id, flags)
            except Exception:
                flags = getattr(self.swe, "FLG_MOSEPH", 4) | speed_flag
                pos, _ = self.swe.calc_ut(jd_ut, point_id, flags)
        return float(pos[0]) % 360.0


def solve_lunar_phase_anchor(
    seed_dt: datetime,
    target_elongation: float,
    ephemeris: LunarEphemeris,
    *,
    max_iterations: int = ANCHOR_MAX_ITERATIONS,
    tolerance_deg: float = ANCHOR_TOLERANCE_DEG,
) -> Tuple[datetime, bool, float]:
    dt = _normalize_utc(seed_dt)
    branch = True
    elongation = 0.0
    target = float(target_elongation)
    for _ in range(max(1, int(max_iterations))):
        sun_lon = ephemeris.longitude_at(dt, "Sun")
        moon_lon = ephemeris.longitude_at(dt, "Moon")
        branch, elongation = moon_branch_and_elongation(sun_lon, moon_lon)
        error = float(elongation) - target
        if abs(error) <= tolerance_deg:
            break
        correction_days = error / MOON_MAX_SPEED_DIVISOR
        if branch:
            dt = dt - timedelta(days=correction_days)
        else:
            dt = dt + timedelta(days=correction_days)
    return dt, branch, float(elongation)


def _window_bounds(anchor_dt: datetime) -> Tuple[datetime, datetime]:
    center = _normalize_utc(anchor_dt)
    return (
        center - timedelta(hours=WINDOW_BEFORE_HOURS),
        center + timedelta(hours=WINDOW_AFTER_HOURS),
    )


def _windows_overlap(anchor_dt: datetime, start_dt: datetime, end_dt: datetime) -> bool:
    left, right = _window_bounds(anchor_dt)
    return right >= start_dt and left <= end_dt


def generate_lunar_fertility_anchors(
    start_dt: datetime,
    end_dt: datetime,
    signature: LunarFertilitySignature,
    *,
    consider_mode: str = "phase_and_antiphase",
    ephemeris: LunarEphemeris,
) -> List[LunarFertilityAnchor]:
    start = _normalize_utc(start_dt)
    end = _normalize_utc(end_dt)
    if end <= start:
        raise ValueError("end_dt must be after start_dt")
    mode = normalize_consider_mode(consider_mode)
    cursor = start - timedelta(hours=WINDOW_AFTER_HOURS)
    search_end = end + timedelta(days=LUNAR_CYCLE_DAYS)
    anchors: List[LunarFertilityAnchor] = []
    seen: set[int] = set()

    while cursor <= search_end:
        anchor_dt, branch, elongation = solve_lunar_phase_anchor(
            cursor,
            signature.target_elongation,
            ephemeris,
        )
        phase_kind = _phase_kind_for_branch(branch, signature.natal_branch)
        key = int(anchor_dt.timestamp() // 600)
        if (
            key not in seen
            and _mode_accepts_phase_kind(phase_kind, mode)
            and _windows_overlap(anchor_dt, start, end)
        ):
            seen.add(key)
            anchors.append(
                LunarFertilityAnchor(
                    timestamp=anchor_dt,
                    phase_kind=phase_kind,
                    branch=branch,
                    elongation=round(elongation, 6),
                    target_elongation=round(signature.target_elongation, 6),
                )
            )
        cursor = cursor + timedelta(days=HALF_LUNAR_CYCLE_DAYS)

    return sorted(anchors, key=lambda item: item.timestamp)


def _strength_for(anchor_dt: datetime, point_dt: datetime) -> float:
    anchor = _normalize_utc(anchor_dt)
    point = _normalize_utc(point_dt)
    left, right = _window_bounds(anchor)
    if point < left or point > right:
        return 0.0
    if point <= anchor:
        span = max(1.0, (anchor - left).total_seconds())
        return max(0.0, min(100.0, ((point - left).total_seconds() / span) * 100.0))
    span = max(1.0, (right - anchor).total_seconds())
    return max(0.0, min(100.0, ((right - point).total_seconds() / span) * 100.0))


def _sex_label_for_sign(sign: str) -> str:
    if sign in MASCULINE_SIGNS:
        return "male"
    if sign in FEMININE_SIGNS:
        return "female"
    return "unknown"


def _safe_zone(timezone_name: Optional[str]) -> ZoneInfo:
    try:
        return ZoneInfo(str(timezone_name or "UTC"))
    except Exception:
        return ZoneInfo("UTC")


def project_lunar_fertility_series(
    start_dt: datetime,
    end_dt: datetime,
    anchors: Iterable[LunarFertilityAnchor],
    *,
    timezone_name: Optional[str] = "UTC",
    ephemeris: LunarEphemeris,
) -> List[Dict[str, Any]]:
    start = _normalize_utc(start_dt)
    end = _normalize_utc(end_dt)
    zone = _safe_zone(timezone_name)
    anchor_list = sorted(list(anchors or []), key=lambda item: item.timestamp)
    rows: List[Dict[str, Any]] = []
    t = start
    while t <= end:
        best: Optional[Tuple[float, LunarFertilityAnchor]] = None
        for anchor in anchor_list:
            strength = _strength_for(anchor.timestamp, t)
            if strength <= 0.0:
                continue
            if best is None or strength > best[0] or (
                math.isclose(strength, best[0], abs_tol=1e-9) and anchor.phase_kind == "phase"
            ):
                best = (strength, anchor)
        if best is not None:
            strength, anchor = best
            moon_lon = ephemeris.longitude_at(t, "Moon")
            moon_sign = _sign_from_lon(moon_lon)
            sex_label = _sex_label_for_sign(moon_sign)
            local_dt = t.astimezone(zone)
            score = round(strength, 2)
            tags = [
                "Lunar fertility window",
                "Phase" if anchor.phase_kind == "phase" else "Antiphase",
                f"Moon in {moon_sign}",
                "Moon in masculine sign" if sex_label == "male" else "Moon in feminine sign" if sex_label == "female" else "Moon sign polarity unknown",
            ]
            if strength >= 90.0:
                tags.append("Near anchor")
            rows.append(
                {
                    "timestamp": t.isoformat(),
                    "timestamp_local": local_dt.isoformat(),
                    "score": score,
                    "strength": score,
                    "phase_kind": anchor.phase_kind,
                    "sex_label": sex_label,
                    "moon_sign": moon_sign,
                    "moon_longitude": round(float(moon_lon) % 360.0, 6),
                    "anchor_timestamp": anchor.timestamp.isoformat(),
                    "anchor_offset_hours": round((t - anchor.timestamp).total_seconds() / 3600.0, 2),
                    "tags": tags,
                    "pros": tags[:3],
                    "cautions": [],
                }
            )
        t = t + timedelta(hours=1)
    return rows


def _parse_row_timestamp(row: Dict[str, Any]) -> Optional[datetime]:
    try:
        value = str(row.get("timestamp") or "")
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def group_lunar_fertility_periods(
    rows: Iterable[Dict[str, Any]],
    *,
    timezone_name: Optional[str] = "UTC",
) -> Dict[str, Any]:
    zone = _safe_zone(timezone_name)
    ordered = sorted(
        [dict(row) for row in rows or [] if _parse_row_timestamp(row) is not None],
        key=lambda row: _parse_row_timestamp(row) or datetime.min.replace(tzinfo=timezone.utc),
    )
    periods: List[Dict[str, Any]] = []
    rows_out: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = []

    def flush() -> None:
        if not current:
            return
        period_id = f"lfp-{len(periods) + 1}"
        first = current[0]
        last = current[-1]
        start_ts = _parse_row_timestamp(first)
        last_ts = _parse_row_timestamp(last)
        if start_ts is None or last_ts is None:
            return
        end_ts = last_ts + timedelta(hours=1, seconds=-1)
        peak = max(current, key=lambda row: float(row.get("score") or 0.0))
        for row in current:
            copy_row = dict(row)
            copy_row["period_id"] = period_id
            rows_out.append(copy_row)
        periods.append(
            {
                "id": period_id,
                "start": start_ts.isoformat(),
                "end": end_ts.isoformat(),
                "start_local": start_ts.astimezone(zone).isoformat(),
                "end_local": end_ts.astimezone(zone).isoformat(),
                "best_timestamp": peak.get("timestamp"),
                "best_timestamp_local": peak.get("timestamp_local"),
                "best_score": peak.get("score"),
                "phase_kind": first.get("phase_kind"),
                "sex_label": first.get("sex_label"),
                "moon_sign": peak.get("moon_sign"),
                "row_count": len(current),
            }
        )

    previous_ts: Optional[datetime] = None
    previous_phase = None
    previous_sex = None
    for row in ordered:
        ts = _parse_row_timestamp(row)
        if ts is None:
            continue
        phase_kind = row.get("phase_kind")
        sex_label = row.get("sex_label")
        contiguous = previous_ts is not None and abs((ts - (previous_ts + timedelta(hours=1))).total_seconds()) <= 1
        same_flags = phase_kind == previous_phase and sex_label == previous_sex
        if current and (not contiguous or not same_flags):
            flush()
            current = []
        current.append(row)
        previous_ts = ts
        previous_phase = phase_kind
        previous_sex = sex_label
    flush()
    return {"periods": periods, "rows": rows_out}


def scan_lunar_fertility_windows(
    natal_chart_data: Dict[str, Any],
    start_dt: datetime,
    end_dt: datetime,
    *,
    timezone_name: Optional[str] = "UTC",
    consider_mode: str = "phase_and_antiphase",
    level_percent: float = 33.0,
    ephemeris: Optional[LunarEphemeris] = None,
) -> Dict[str, Any]:
    if ephemeris is None:
        ephemeris = SwissEphemerisAdapter()
    start = _normalize_utc(start_dt)
    end = _normalize_utc(end_dt)
    if end <= start:
        raise ValueError("End must be after start")
    mode = normalize_consider_mode(consider_mode)
    try:
        level = float(level_percent)
    except Exception:
        level = 33.0
    level = max(0.0, min(100.0, level))
    signature = extract_natal_lunar_signature(natal_chart_data)
    anchors = generate_lunar_fertility_anchors(
        start,
        end,
        signature,
        consider_mode=mode,
        ephemeris=ephemeris,
    )
    all_rows = project_lunar_fertility_series(
        start,
        end,
        anchors,
        timezone_name=timezone_name,
        ephemeris=ephemeris,
    )
    passing_rows = [row for row in all_rows if float(row.get("score") or 0.0) >= level]
    grouped = group_lunar_fertility_periods(passing_rows, timezone_name=timezone_name)
    period_rows = grouped.get("rows") or []
    period_by_key = {
        (row.get("timestamp"), row.get("phase_kind"), row.get("sex_label")): row.get("period_id")
        for row in period_rows
    }
    series: List[Dict[str, Any]] = []
    for row in all_rows:
        copy_row = dict(row)
        copy_row["passes_level"] = float(copy_row.get("score") or 0.0) >= level
        period_id = period_by_key.get((copy_row.get("timestamp"), copy_row.get("phase_kind"), copy_row.get("sex_label")))
        if period_id:
            copy_row["period_id"] = period_id
        series.append(copy_row)
    top_source = passing_rows if passing_rows else all_rows
    top = sorted(top_source, key=lambda row: float(row.get("score") or 0.0), reverse=True)
    attempted = int(((end - start).total_seconds() // 3600) + 1)
    return {
        "matter": "lunar_fertility",
        "consider_mode": mode,
        "level_percent": level,
        "signature": {
            "sun_longitude": round(signature.sun_longitude, 6),
            "moon_longitude": round(signature.moon_longitude, 6),
            "target_elongation": round(signature.target_elongation, 6),
            "natal_phase_kind": "phase",
            "natal_branch": signature.natal_branch,
        },
        "anchors": [
            {
                "timestamp": anchor.timestamp.isoformat(),
                "phase_kind": anchor.phase_kind,
                "branch": anchor.branch,
                "elongation": anchor.elongation,
                "target_elongation": anchor.target_elongation,
            }
            for anchor in anchors
        ],
        "series": series,
        "periods": grouped.get("periods") or [],
        "top": top,
        "stats": {
            "attempted": attempted,
            "anchor_count": len(anchors),
            "favorable_total": len(all_rows),
            "passing_total": len(passing_rows),
            "period_count": len(grouped.get("periods") or []),
        },
    }


def score_lunar_fertility_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Compatibility adapter for the election facade.

    Lunar Fertility Windows is a range scanner. The real public entry point is
    scan_lunar_fertility_windows(...). This adapter prevents accidental route
    failures if a caller asks for a normal Score-shaped result.
    """

    return Score(
        value=0.0,
        tags=["Lunar Fertility Windows requires the range scanner"],
        pros=[],
        cautions=["Use scan_lunar_fertility_windows for hourly period output"],
    )


__all__ = [
    "ANCHOR_MAX_ITERATIONS",
    "ANCHOR_TOLERANCE_DEG",
    "HALF_LUNAR_CYCLE_DAYS",
    "LUNAR_CYCLE_DAYS",
    "MOON_MAX_SPEED_DIVISOR",
    "WINDOW_AFTER_HOURS",
    "WINDOW_BEFORE_HOURS",
    "LunarFertilityAnchor",
    "LunarFertilitySignature",
    "SwissEphemerisAdapter",
    "extract_natal_lunar_signature",
    "generate_lunar_fertility_anchors",
    "group_lunar_fertility_periods",
    "moon_branch_and_elongation",
    "normalize_consider_mode",
    "project_lunar_fertility_series",
    "scan_lunar_fertility_windows",
    "score_lunar_fertility_election",
    "solve_lunar_phase_anchor",
]
