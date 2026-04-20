from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

try:
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover - runtime dependency may be unavailable in narrow test envs
    swe = None  # type: ignore


BundleResolver = Callable[..., Dict[str, Any]]
LongitudeResolver = Callable[[datetime], Dict[str, float]]

_KEY_PLANETS = ("Sun", "Moon", "Mars", "Jupiter", "Saturn", "North Node")
_ANGULAR_HOUSES = {1, 4, 7, 10}
_ECLIPSE_NODE_ORB_DEG = 12.0
_ECLIPSE_ACTIVATION_ORB_DEG = 2.0
_JUPITER_SATURN_SEARCH_YEARS = 25
_JUPITER_SATURN_STEP_DAYS = 30
_JUPITER_SATURN_ACTIVE_WINDOW_YEARS = 6.0
_JUPITER_SATURN_STRONG_WINDOW_YEARS = 3.0
_ZODIAC_SIGNS = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)
_CARDINAL_INGRESS_SPECS = {
    "aries": {"target_deg": 0.0, "start": (3, 18), "end": (3, 22), "label": "Aries Ingress", "role": "annual_framework"},
    "cancer": {"target_deg": 90.0, "start": (6, 19), "end": (6, 23), "label": "Cancer Ingress", "role": "quarterly_framework"},
    "libra": {"target_deg": 180.0, "start": (9, 20), "end": (9, 24), "label": "Libra Ingress", "role": "quarterly_framework"},
    "capricorn": {"target_deg": 270.0, "start": (12, 20), "end": (12, 24), "label": "Capricorn Ingress", "role": "quarterly_framework"},
}
_MOVABLE_SIGNS = {"Aries", "Cancer", "Libra", "Capricorn"}
_FIXED_SIGNS = {"Taurus", "Leo", "Scorpio", "Aquarius"}
_COMMON_SIGNS = {"Gemini", "Virgo", "Sagittarius", "Pisces"}
_INGRESS_DURATION_MONTHS = {"movable": 3, "fixed": 12, "common": 6}


@dataclass(slots=True)
class SearchCandidate:
    event_type: str
    exact_dt: datetime
    distance_seconds: float


def _normalize_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value or "").strip()
        if not raw:
            raise ValueError("datetime value is required")
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_angle(value: float) -> float:
    return float(value) % 360.0


def _signed_angle_diff(value: float, target: float) -> float:
    return ((_normalize_angle(value) - _normalize_angle(target) + 180.0) % 360.0) - 180.0


def _angle_sep(a: float, b: float) -> float:
    return abs(_signed_angle_diff(a, b))


def _angle_points(bundle: Dict[str, Any]) -> List[Tuple[str, float]]:
    chart_data = bundle.get("chart_data") or {}
    points: List[Tuple[str, float]] = []
    try:
        asc = float(chart_data.get("ascendant"))
        points.append(("ascendant", _normalize_angle(asc)))
        points.append(("descendant", _normalize_angle(asc + 180.0)))
    except Exception:
        pass
    try:
        mc = float(chart_data.get("midheaven"))
        points.append(("midheaven", _normalize_angle(mc)))
        points.append(("imum_coeli", _normalize_angle(mc + 180.0)))
    except Exception:
        pass
    return points


def _nearest_angle(longitude: float, bundle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    points = _angle_points(bundle)
    if not points:
        return None
    nearest_label, nearest_longitude = min(points, key=lambda item: _angle_sep(longitude, item[1]))
    return {
        "angle": nearest_label,
        "distance_deg": round(_angle_sep(longitude, nearest_longitude), 3),
    }


def _julian_day_utc(dt: datetime) -> float:
    dt_utc = _normalize_dt(dt)
    hours = dt_utc.hour + (dt_utc.minute / 60.0) + (dt_utc.second / 3600.0) + (dt_utc.microsecond / 3_600_000_000.0)
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hours)  # type: ignore[union-attr]


def _swe_longitudes(dt: datetime) -> Dict[str, float]:
    if swe is None:
        raise RuntimeError("swisseph is required for mundane chart search")
    jd_ut = _julian_day_utc(dt)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    sun_data, _ = swe.calc_ut(jd_ut, swe.SUN, flags)
    moon_data, _ = swe.calc_ut(jd_ut, swe.MOON, flags)
    try:
        node_data, _ = swe.calc_ut(jd_ut, swe.TRUE_NODE, flags)
    except Exception:
        node_data, _ = swe.calc_ut(jd_ut, swe.MEAN_NODE, flags)
    return {
        "Sun": _normalize_angle(sun_data[0]),
        "Moon": _normalize_angle(moon_data[0]),
        "North Node": _normalize_angle(node_data[0]),
    }


def _swe_jupiter_saturn_longitudes(dt: datetime) -> Dict[str, float]:
    if swe is None:
        raise RuntimeError("swisseph is required for mundane chart search")
    jd_ut = _julian_day_utc(dt)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    jupiter_data, _ = swe.calc_ut(jd_ut, swe.JUPITER, flags)
    saturn_data, _ = swe.calc_ut(jd_ut, swe.SATURN, flags)
    return {
        "Jupiter": _normalize_angle(jupiter_data[0]),
        "Saturn": _normalize_angle(saturn_data[0]),
    }


def _bundle_planets(bundle: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    chart_data = bundle.get("chart_data") or {}
    planets = chart_data.get("planets") or {}
    if isinstance(planets, dict):
        return {str(name): info for name, info in planets.items() if isinstance(info, dict)}
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(planets, list):
        for item in planets:
            if not isinstance(item, dict):
                continue
            name = str(item.get("planet") or item.get("name") or "").strip()
            if name:
                out[name] = item
    return out


def _bundle_houses(bundle: Dict[str, Any]) -> List[float]:
    chart_data = bundle.get("chart_data") or {}
    houses = chart_data.get("houses") or chart_data.get("house_cusps") or []
    if not isinstance(houses, list):
        return []
    out: List[float] = []
    for item in houses[:12]:
        try:
            out.append(float(item) % 360.0)
        except Exception:
            continue
    return out


def _bundle_snapshot(bundle: Dict[str, Any], *, label: str, chart_kind: str, computed_datetime: datetime) -> Dict[str, Any]:
    chart_data = bundle.get("chart_data") or {}
    meta = bundle.get("meta") or {}
    planets = _bundle_planets(bundle)
    key_planets: Dict[str, Any] = {}
    for name in _KEY_PLANETS:
        info = planets.get(name)
        if not info:
            continue
        key_planets[name] = {
            "longitude": float(info.get("longitude") or 0.0),
            "sign": info.get("sign"),
            "house": info.get("house"),
            "retrograde": bool(info.get("retrograde")),
            "speed": float(info.get("speed") or 0.0),
        }
    return {
        "label": label,
        "kind": chart_kind,
        "meta": meta,
        "computed_datetime": computed_datetime.isoformat(),
        "location": meta.get("location"),
        "timezone": meta.get("timezone"),
        "latitude": meta.get("latitude"),
        "longitude": meta.get("longitude"),
        "angles": {
            "ascendant": chart_data.get("ascendant"),
            "midheaven": chart_data.get("midheaven"),
        },
        "houses": _bundle_houses(bundle),
        "house_rulers": chart_data.get("house_rulers") or {},
        "planets": key_planets,
    }


def _angular_planets(bundle: Dict[str, Any], *, names: Iterable[str] = _KEY_PLANETS) -> List[Dict[str, Any]]:
    planets = _bundle_planets(bundle)
    hits: List[Dict[str, Any]] = []
    for name in names:
        info = planets.get(name)
        if not info:
            continue
        house = info.get("house")
        try:
            house_int = int(house)
        except Exception:
            continue
        if house_int in _ANGULAR_HOUSES:
            nearest_angle = _nearest_angle(float(info.get("longitude") or 0.0), bundle)
            hits.append(
                {
                    "planet": name,
                    "house": house_int,
                    "longitude": float(info.get("longitude") or 0.0),
                    "sign": info.get("sign"),
                    "closest_angle": (nearest_angle or {}).get("angle"),
                    "angle_distance_deg": (nearest_angle or {}).get("distance_deg"),
                }
            )
    return hits


def _house_ruler_summary(bundle: Dict[str, Any], house_number: int) -> Optional[Dict[str, Any]]:
    chart_data = bundle.get("chart_data") or {}
    rulers = chart_data.get("house_rulers") or {}
    if not isinstance(rulers, dict):
        return None
    ruler_name = rulers.get(str(house_number)) or rulers.get(house_number)
    if not ruler_name:
        return None
    planets = _bundle_planets(bundle)
    ruler_info = planets.get(str(ruler_name)) or {}
    longitude = ruler_info.get("longitude")
    nearest_angle = None
    if longitude is not None:
        try:
            nearest_angle = _nearest_angle(float(longitude), bundle)
        except Exception:
            nearest_angle = None
    return {
        "house": house_number,
        "ruler": str(ruler_name),
        "longitude": longitude,
        "sign": ruler_info.get("sign"),
        "house_position": ruler_info.get("house"),
        "retrograde": bool(ruler_info.get("retrograde")),
        "closest_angle": (nearest_angle or {}).get("angle"),
        "angle_distance_deg": (nearest_angle or {}).get("distance_deg"),
    }


def _eclipse_activation_hits(primary_bundle: Dict[str, Any], overlay_bundle: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not overlay_bundle:
        return []
    primary_planets = _bundle_planets(primary_bundle)
    overlay_planets = _bundle_planets(overlay_bundle)
    eclipse_points = []
    for point_name in ("Sun", "Moon"):
        info = primary_planets.get(point_name)
        if info and info.get("longitude") is not None:
            eclipse_points.append((point_name, float(info.get("longitude")) % 360.0))
    hits: List[Dict[str, Any]] = []
    for probe_name in ("Mars", "Jupiter", "Saturn"):
        probe = overlay_planets.get(probe_name)
        if not probe or probe.get("longitude") is None:
            continue
        probe_lon = float(probe.get("longitude")) % 360.0
        for point_name, point_lon in eclipse_points:
            orb = _angle_sep(probe_lon, point_lon)
            if orb <= _ECLIPSE_ACTIVATION_ORB_DEG:
                hits.append(
                    {
                        "planet": probe_name,
                        "target_point": point_name,
                        "orb_deg": round(orb, 3),
                        "longitude": round(probe_lon, 3),
                    }
                )
    return hits


def _zodiac_sign(longitude: float) -> str:
    index = int(_normalize_angle(longitude) // 30.0) % 12
    return _ZODIAC_SIGNS[index]


def _sign_modality(sign_name: str) -> str:
    if sign_name in _MOVABLE_SIGNS:
        return "movable"
    if sign_name in _FIXED_SIGNS:
        return "fixed"
    return "common"


def _cardinal_ingress_spec(ingress_id: str) -> Dict[str, Any]:
    normalized = str(ingress_id or "").strip().lower()
    spec = _CARDINAL_INGRESS_SPECS.get(normalized)
    if spec is None:
        raise ValueError(f"Unsupported ingress key: {ingress_id}")
    return spec


def _find_solar_ingress(
    year: int,
    *,
    target_deg: float,
    start_month: int,
    start_day: int,
    end_month: int,
    end_day: int,
    longitudes_at: LongitudeResolver,
) -> datetime:
    start = datetime(year, start_month, start_day, 0, 0, tzinfo=timezone.utc)
    end = datetime(year, end_month, end_day, 0, 0, tzinfo=timezone.utc)

    def sun_diff(dt: datetime) -> float:
        return _signed_angle_diff(longitudes_at(dt)["Sun"], target_deg)

    current = start
    prev_value = sun_diff(current)
    prev_dt = current
    step = timedelta(hours=6)
    while current < end:
        current = min(current + step, end)
        current_value = sun_diff(current)
        if prev_value == 0:
            return prev_dt
        if current_value == 0 or prev_value < 0 <= current_value or prev_value > 0 >= current_value:
            low = prev_dt
            high = current
            low_value = prev_value
            for _ in range(18):
                mid = low + ((high - low) / 2)
                mid_value = sun_diff(mid)
                if low_value == 0 or mid_value == 0:
                    return mid if mid_value == 0 else low
                if low_value < 0 <= mid_value or low_value > 0 >= mid_value:
                    high = mid
                else:
                    low = mid
                    low_value = mid_value
            return low + ((high - low) / 2)
        prev_dt = current
        prev_value = current_value
    raise ValueError(f"Unable to resolve solar ingress near {target_deg}deg for year {year}")


def _jupiter_saturn_raw_phase(longitudes: Dict[str, float]) -> float:
    return _normalize_angle(longitudes["Jupiter"] - longitudes["Saturn"])


def _find_jupiter_saturn_conjunctions(
    start: datetime,
    end: datetime,
    *,
    anchor_dt: datetime,
) -> List[SearchCandidate]:
    current = start
    prev_phase = _jupiter_saturn_raw_phase(_swe_jupiter_saturn_longitudes(current))
    prev_dt = current
    candidates: List[SearchCandidate] = []
    step = timedelta(days=_JUPITER_SATURN_STEP_DAYS)
    while current < end:
        current = min(current + step, end)
        current_phase = _unwrap_phase(prev_phase, _jupiter_saturn_raw_phase(_swe_jupiter_saturn_longitudes(current)))
        if abs(prev_phase) < 1e-9:
            candidates.append(
                SearchCandidate(
                    event_type="jupiter_saturn_conjunction",
                    exact_dt=prev_dt,
                    distance_seconds=abs((prev_dt - anchor_dt).total_seconds()),
                )
            )
        target_value = 360.0 * (int(prev_phase // 360.0) + 1)
        while target_value <= current_phase + 1e-9:
            if current_phase == prev_phase:
                exact_dt = current
            else:
                fraction = (target_value - prev_phase) / (current_phase - prev_phase)
                exact_dt = prev_dt + ((current - prev_dt) * fraction)
            candidates.append(
                SearchCandidate(
                    event_type="jupiter_saturn_conjunction",
                    exact_dt=exact_dt,
                    distance_seconds=abs((exact_dt - anchor_dt).total_seconds()),
                )
            )
            target_value += 360.0
        prev_dt = current
        prev_phase = current_phase
    return candidates


@lru_cache(maxsize=512)
def _cached_jupiter_saturn_cycle_context(anchor_dt_iso: str) -> Optional[Dict[str, Any]]:
    if swe is None:
        return None
    anchor_dt = _normalize_dt(anchor_dt_iso)
    search_start = anchor_dt - timedelta(days=365 * _JUPITER_SATURN_SEARCH_YEARS)
    search_end = anchor_dt + timedelta(days=365 * _JUPITER_SATURN_SEARCH_YEARS)
    candidates = _find_jupiter_saturn_conjunctions(search_start, search_end, anchor_dt=anchor_dt)
    if not candidates:
        return None
    previous = [candidate for candidate in candidates if candidate.exact_dt <= anchor_dt]
    upcoming = [candidate for candidate in candidates if candidate.exact_dt > anchor_dt]
    previous_candidate = max(previous, key=lambda row: row.exact_dt) if previous else None
    next_candidate = min(upcoming, key=lambda row: row.exact_dt) if upcoming else None
    if previous_candidate is None and next_candidate is None:
        return None

    nearest = min(
        [candidate for candidate in (previous_candidate, next_candidate) if candidate is not None],
        key=lambda row: abs((row.exact_dt - anchor_dt).total_seconds()),
    )
    nearest_years = abs((nearest.exact_dt - anchor_dt).total_seconds()) / (365.2425 * 86400.0)
    if previous_candidate is None:
        cycle_phase = "pre_conjunction"
    else:
        years_since_previous = (anchor_dt - previous_candidate.exact_dt).total_seconds() / (365.2425 * 86400.0)
        if years_since_previous <= _JUPITER_SATURN_STRONG_WINDOW_YEARS:
            cycle_phase = "opening_cycle"
        elif years_since_previous >= 12.0:
            cycle_phase = "late_cycle"
        else:
            cycle_phase = "mid_cycle"
    nearest_longitudes = _swe_jupiter_saturn_longitudes(nearest.exact_dt)
    conjunction_longitude = (nearest_longitudes["Jupiter"] + nearest_longitudes["Saturn"]) / 2.0
    turning_window_active = nearest_years <= _JUPITER_SATURN_ACTIVE_WINDOW_YEARS
    turning_window_level = "strong" if nearest_years <= _JUPITER_SATURN_STRONG_WINDOW_YEARS else "moderate" if turning_window_active else "background"
    return {
        "type": "jupiter_saturn_cycle",
        "anchor_datetime": anchor_dt.isoformat(),
        "previous_conjunction_datetime": previous_candidate.exact_dt.isoformat() if previous_candidate else None,
        "next_conjunction_datetime": next_candidate.exact_dt.isoformat() if next_candidate else None,
        "nearest_conjunction_datetime": nearest.exact_dt.isoformat(),
        "nearest_distance_years": round(nearest_years, 3),
        "years_since_previous": None if previous_candidate is None else round((anchor_dt - previous_candidate.exact_dt).total_seconds() / (365.2425 * 86400.0), 3),
        "years_until_next": None if next_candidate is None else round((next_candidate.exact_dt - anchor_dt).total_seconds() / (365.2425 * 86400.0), 3),
        "cycle_phase": cycle_phase,
        "turning_window_active": turning_window_active,
        "turning_window_level": turning_window_level,
        "turning_window_years": _JUPITER_SATURN_ACTIVE_WINDOW_YEARS,
        "conjunction_longitude": round(_normalize_angle(conjunction_longitude), 3),
        "conjunction_sign": _zodiac_sign(conjunction_longitude),
        "source_tags": ["watters_mutations", "bonatti_revolutions"],
    }


def _jupiter_saturn_cycle_context(anchor_dt: datetime) -> Optional[Dict[str, Any]]:
    return _cached_jupiter_saturn_cycle_context(_normalize_dt(anchor_dt).replace(microsecond=0).isoformat())


def _resolve_bundle(
    bundle_resolver: BundleResolver,
    dt_iso: str,
    location: Optional[str],
    timezone_name: Optional[str],
    house_system_code: Optional[str],
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Dict[str, Any]:
    if latitude is None or longitude is None:
        return bundle_resolver(dt_iso, location, timezone_name, house_system_code)
    try:
        return bundle_resolver(
            dt_iso,
            location,
            timezone_name,
            house_system_code,
            latitude=latitude,
            longitude=longitude,
        )
    except TypeError:
        return bundle_resolver(dt_iso, location, timezone_name, house_system_code)


def _phase_distance(longitudes: Dict[str, float], target: float) -> float:
    return _signed_angle_diff(longitudes["Moon"] - longitudes["Sun"], target)


def _raw_phase(longitudes: Dict[str, float]) -> float:
    return _normalize_angle(longitudes["Moon"] - longitudes["Sun"])


def _unwrap_phase(previous_phase: float, current_raw_phase: float) -> float:
    current_phase = current_raw_phase
    while current_phase - previous_phase <= -180.0:
        current_phase += 360.0
    while current_phase - previous_phase > 180.0:
        current_phase -= 360.0
    if current_phase < previous_phase:
        current_phase += 360.0
    return current_phase


def _find_event_candidates(
    start: datetime,
    end: datetime,
    *,
    step_hours: float,
    target_deg: float,
    event_type: str,
    longitudes_at: LongitudeResolver,
    anchor_dt: datetime,
) -> List[SearchCandidate]:
    current = start
    prev_phase = _raw_phase(longitudes_at(current))
    prev_dt = current
    candidates: List[SearchCandidate] = []
    step = timedelta(hours=step_hours)
    while current < end:
        current = min(current + step, end)
        current_phase = _unwrap_phase(prev_phase, _raw_phase(longitudes_at(current)))
        if abs(prev_phase - target_deg) < 1e-9:
            candidates.append(
                SearchCandidate(
                    event_type=event_type,
                    exact_dt=prev_dt,
                    distance_seconds=abs((prev_dt - anchor_dt).total_seconds()),
                )
            )
        k = int((prev_phase - target_deg) // 360.0)
        target_value = target_deg + 360.0 * (k + 1)
        while target_value <= current_phase + 1e-9:
            if current_phase == prev_phase:
                exact_dt = current
            else:
                fraction = (target_value - prev_phase) / (current_phase - prev_phase)
                exact_dt = prev_dt + ((current - prev_dt) * fraction)
            candidates.append(
                SearchCandidate(
                    event_type=event_type,
                    exact_dt=exact_dt,
                    distance_seconds=abs((exact_dt - anchor_dt).total_seconds()),
                )
            )
            target_value += 360.0
        prev_dt = current
        prev_phase = current_phase
    return candidates


def _binary_refine(
    start: datetime,
    end: datetime,
    *,
    target_deg: float,
    longitudes_at: LongitudeResolver,
    iterations: int = 18,
) -> datetime:
    low = start
    high = end
    low_value = _phase_distance(longitudes_at(low), target_deg)
    for _ in range(iterations):
        mid = low + ((high - low) / 2)
        mid_value = _phase_distance(longitudes_at(mid), target_deg)
        if low_value == 0 or mid_value == 0:
            return mid if mid_value == 0 else low
        if low_value < 0 <= mid_value or low_value > 0 >= mid_value:
            high = mid
        else:
            low = mid
            low_value = mid_value
    return low + ((high - low) / 2)


def _find_nearest_lunation(anchor_dt: datetime, *, longitudes_at: LongitudeResolver) -> SearchCandidate:
    start = anchor_dt - timedelta(days=20)
    end = anchor_dt + timedelta(days=20)
    candidates = _find_event_candidates(
        start,
        end,
        step_hours=12.0,
        target_deg=0.0,
        event_type="new_moon",
        longitudes_at=longitudes_at,
        anchor_dt=anchor_dt,
    )
    candidates.extend(
        _find_event_candidates(
            start,
            end,
            step_hours=12.0,
            target_deg=180.0,
            event_type="full_moon",
            longitudes_at=longitudes_at,
            anchor_dt=anchor_dt,
        )
    )
    if not candidates:
        raise ValueError("Unable to resolve a lunation near the requested date")
    return sorted(candidates, key=lambda row: (row.distance_seconds, row.exact_dt))[0]


def _find_nearest_eclipse(
    anchor_dt: datetime,
    *,
    longitudes_at: LongitudeResolver,
    bundle_resolver: BundleResolver,
    location: Optional[str],
    timezone_name: Optional[str],
    house_system_code: Optional[str],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Tuple[SearchCandidate, Dict[str, Any], float]:
    start = anchor_dt - timedelta(days=190)
    end = anchor_dt + timedelta(days=190)
    candidates = _find_event_candidates(
        start,
        end,
        step_hours=12.0,
        target_deg=0.0,
        event_type="solar_eclipse",
        longitudes_at=longitudes_at,
        anchor_dt=anchor_dt,
    )
    candidates.extend(
        _find_event_candidates(
            start,
            end,
            step_hours=12.0,
            target_deg=180.0,
            event_type="lunar_eclipse",
            longitudes_at=longitudes_at,
            anchor_dt=anchor_dt,
        )
    )
    if not candidates:
        raise ValueError("Unable to resolve an eclipse near the requested date")
    ranked = sorted(candidates, key=lambda row: (row.distance_seconds, row.exact_dt))
    for candidate in ranked:
        bundle = _resolve_bundle(
            bundle_resolver,
            candidate.exact_dt.isoformat(),
            location,
            timezone_name,
            house_system_code,
            latitude=latitude,
            longitude=longitude,
        )
        planets = _bundle_planets(bundle)
        sun = planets.get("Sun")
        moon = planets.get("Moon")
        node = planets.get("North Node")
        if not sun or not moon or not node:
            continue
        node_lon = float(node.get("longitude") or 0.0) % 360.0
        sun_orb = min(_angle_sep(float(sun.get("longitude") or 0.0), node_lon), _angle_sep(float(sun.get("longitude") or 0.0), (node_lon + 180.0) % 360.0))
        moon_orb = min(_angle_sep(float(moon.get("longitude") or 0.0), node_lon), _angle_sep(float(moon.get("longitude") or 0.0), (node_lon + 180.0) % 360.0))
        orb = min(sun_orb, moon_orb)
        if orb <= _ECLIPSE_NODE_ORB_DEG:
            return candidate, bundle, orb
    fallback = ranked[0]
    bundle = _resolve_bundle(
        bundle_resolver,
        fallback.exact_dt.isoformat(),
        location,
        timezone_name,
        house_system_code,
        latitude=latitude,
        longitude=longitude,
    )
    planets = _bundle_planets(bundle)
    node_lon = float(((planets.get("North Node") or {}).get("longitude") or 0.0)) % 360.0
    sun_lon = float(((planets.get("Sun") or {}).get("longitude") or 0.0)) % 360.0
    orb = min(_angle_sep(sun_lon, node_lon), _angle_sep(sun_lon, (node_lon + 180.0) % 360.0))
    return fallback, bundle, orb


def _find_aries_ingress(anchor_dt: datetime, *, longitudes_at: LongitudeResolver) -> datetime:
    return _find_solar_ingress(
        anchor_dt.year,
        target_deg=0.0,
        start_month=3,
        start_day=18,
        end_month=3,
        end_day=22,
        longitudes_at=longitudes_at,
    )


@lru_cache(maxsize=128)
def _cached_cardinal_ingress_datetime(ingress_id: str, year: int) -> str:
    if swe is None:
        raise RuntimeError("swisseph is required for mundane chart search")
    spec = _cardinal_ingress_spec(ingress_id)
    dt = _find_solar_ingress(
        year,
        target_deg=float(spec["target_deg"]),
        start_month=int(spec["start"][0]),
        start_day=int(spec["start"][1]),
        end_month=int(spec["end"][0]),
        end_day=int(spec["end"][1]),
        longitudes_at=_swe_longitudes,
    )
    return dt.isoformat()


def _cardinal_ingress_datetime(ingress_id: str, year: int) -> datetime:
    return _normalize_dt(_cached_cardinal_ingress_datetime(ingress_id, year))


def _find_latest_aries_ingress(anchor_dt: datetime) -> datetime:
    candidate = _cardinal_ingress_datetime("aries", anchor_dt.year)
    if candidate <= anchor_dt:
        return candidate
    return _cardinal_ingress_datetime("aries", anchor_dt.year - 1)


def _active_cardinal_ingress(anchor_dt: datetime) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    for year in (anchor_dt.year - 1, anchor_dt.year):
        for ingress_id in _CARDINAL_INGRESS_SPECS.keys():
            ingress_dt = _cardinal_ingress_datetime(ingress_id, year)
            if ingress_dt <= anchor_dt:
                spec = _cardinal_ingress_spec(ingress_id)
                candidates.append(
                    {
                        "ingress_id": ingress_id,
                        "label": str(spec["label"]),
                        "role": str(spec["role"]),
                        "computed_datetime": ingress_dt.isoformat(),
                    }
                )
    if not candidates:
        aries_dt = _find_latest_aries_ingress(anchor_dt)
        spec = _cardinal_ingress_spec("aries")
        return {
            "ingress_id": "aries",
            "label": str(spec["label"]),
            "role": str(spec["role"]),
            "computed_datetime": aries_dt.isoformat(),
        }
    return max(candidates, key=lambda row: row["computed_datetime"])


def _ingress_duration_metadata(bundle: Dict[str, Any]) -> Dict[str, Any]:
    chart_data = bundle.get("chart_data") or {}
    ascendant = chart_data.get("ascendant")
    if ascendant is None:
        return {
            "ascendant_sign": None,
            "framework_modality": "unknown",
            "framework_duration_months": None,
        }
    sign_name = _zodiac_sign(float(ascendant))
    modality = _sign_modality(sign_name)
    return {
        "ascendant_sign": sign_name,
        "framework_modality": modality,
        "framework_duration_months": _INGRESS_DURATION_MONTHS.get(modality),
    }


def _framework_ingress_item(ingress_id: str, computed_datetime: str, *, location: Optional[str], role: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    spec = _cardinal_ingress_spec(ingress_id)
    payload = {
        "chart_type": f"{ingress_id}_ingress" if ingress_id != "aries" else "aries_ingress",
        "ingress_id": ingress_id,
        "label": spec["label"],
        "role": role or spec["role"],
        "computed_datetime": computed_datetime,
        "location": location,
    }
    if extra:
        payload.update(extra)
    return payload


def _eclipse_locality_proxy(
    bundle: Dict[str, Any],
    *,
    eclipse_type: str,
    visibility_scope: Optional[str],
    location_context_type: Optional[str],
) -> Dict[str, Any]:
    observed_body = "Sun" if str(eclipse_type or "").strip().lower() == "solar_eclipse" else "Moon"
    planets = _bundle_planets(bundle)
    observed_info = planets.get(observed_body) or {}
    house_value = observed_info.get("house")
    try:
        house_number = int(house_value)
    except Exception:
        house_number = None
    if house_number is None:
        visibility_classification = "unknown_proxy"
        visibility_status = "approximate"
    elif house_number in {7, 8, 9, 10, 11, 12}:
        visibility_classification = "above_horizon_proxy"
        visibility_status = "locally_observable_proxy"
    else:
        visibility_classification = "below_horizon_proxy"
        visibility_status = "not_locally_observable_proxy"

    normalized_scope = str(visibility_scope or "").strip().lower() or "national"
    normalized_context = str(location_context_type or "").strip().lower()
    if normalized_context == "event_chart":
        territorial_relevance = "event_locality"
    elif normalized_context == "capital_chart" or normalized_scope == "capital":
        territorial_relevance = "capital_scope"
    elif normalized_context == "regional_chart" or normalized_scope == "regional":
        territorial_relevance = "regional_scope"
    elif normalized_scope == "global":
        territorial_relevance = "global_scope"
    else:
        territorial_relevance = "national_scope"

    if visibility_classification == "unknown_proxy" or territorial_relevance == "global_scope":
        locality_confidence = "low_proxy"
    else:
        locality_confidence = "moderate_proxy"

    summary = (
        f"{observed_body} is {visibility_classification.replace('_', ' ')} in the eclipse chart and the current territory frame is {territorial_relevance.replace('_', ' ')}."
    )

    return {
        "observed_body": observed_body,
        "observed_house": house_number,
        "visibility_scope": normalized_scope,
        "visibility_classification": visibility_classification,
        "visibility_status": visibility_status,
        "territorial_relevance": territorial_relevance,
        "locality_confidence": locality_confidence,
        "summary": summary,
    }


def resolve_chart_resolution(
    *,
    chart_type_id: str,
    anchor_datetime: Any,
    location: Optional[str],
    timezone_name: Optional[str],
    house_system_code: Optional[str],
    bundle_resolver: BundleResolver,
    reference_chart: Optional[Dict[str, Any]] = None,
    event_location: Optional[str] = None,
    event_timezone: Optional[str] = None,
    event_datetime: Optional[str] = None,
    location_latitude: Optional[float] = None,
    location_longitude: Optional[float] = None,
    visibility_scope: Optional[str] = None,
    location_context_type: Optional[str] = None,
) -> Dict[str, Any]:
    anchor_dt = _normalize_dt(anchor_datetime)
    longitudes_at = _swe_longitudes
    resolved_location = location or event_location
    resolved_timezone = timezone_name or event_timezone

    current_overlay_bundle = _resolve_bundle(
        bundle_resolver,
        anchor_dt.isoformat(),
        resolved_location,
        resolved_timezone,
        house_system_code,
        latitude=location_latitude,
        longitude=location_longitude,
    )

    if chart_type_id == "national_chart":
        if not isinstance(reference_chart, dict):
            raise ValueError("national_chart requires a reference chart")
        ref_dt = _normalize_dt(reference_chart.get("datetime"))
        cycle_context = _jupiter_saturn_cycle_context(anchor_dt)
        bundle = _resolve_bundle(
            bundle_resolver,
            ref_dt.isoformat(),
            reference_chart.get("location"),
            reference_chart.get("timezone"),
            house_system_code,
        )
        return {
            "status": "computed",
            "primary_chart": _bundle_snapshot(bundle, label="National Chart", chart_kind="national_chart", computed_datetime=ref_dt),
            "supporting_charts": [],
            "signals": {
                "chart_source_status": reference_chart.get("status"),
                "selected_chart_id": reference_chart.get("id"),
                "anchor_datetime": anchor_dt.isoformat(),
            },
            "cycle_context": cycle_context,
            "framework_items": [
                {
                    "chart_type": "national_chart",
                    "computed_datetime": ref_dt.isoformat(),
                    "location": reference_chart.get("location"),
                    "chart_id": reference_chart.get("id"),
                    "chart_status": reference_chart.get("status"),
                    "cycle_phase": (cycle_context or {}).get("cycle_phase"),
                    "nearest_conjunction_datetime": (cycle_context or {}).get("nearest_conjunction_datetime"),
                }
            ],
            "trigger_items": [],
            "activation_items": [
                {
                    "watchpoint": "current_overlay_available",
                    "label": "Current overlay chart available",
                    "summary": "The active AstroClock chart can be compared against the selected national chart for later trigger work.",
                    "status": "present",
                }
            ],
        }

    if chart_type_id == "war_event":
        event_dt = _normalize_dt(event_datetime or anchor_dt)
        war_location = event_location or resolved_location
        war_timezone = event_timezone or resolved_timezone
        if not war_location:
            raise ValueError("war_event requires event_location or a resolved location")
        bundle = _resolve_bundle(
            bundle_resolver,
            event_dt.isoformat(),
            war_location,
            war_timezone,
            house_system_code,
            latitude=location_latitude,
            longitude=location_longitude,
        )
        house_1 = _house_ruler_summary(bundle, 1)
        house_7 = _house_ruler_summary(bundle, 7)
        angular_hits = _angular_planets(bundle, names=("Mars", "Saturn", "Sun", "Moon"))
        mars = (_bundle_planets(bundle).get("Mars") or {})
        return {
            "status": "computed",
            "primary_chart": _bundle_snapshot(bundle, label="War Event Chart", chart_kind="war_event", computed_datetime=event_dt),
            "supporting_charts": [],
            "signals": {
                "aggressor_house": house_1,
                "defender_house": house_7,
                "mars_retrograde": bool(mars.get("retrograde")),
                "angular_hits": angular_hits,
            },
            "framework_items": [
                {
                    "chart_type": "war_event",
                    "computed_datetime": event_dt.isoformat(),
                    "location": war_location,
                    "aggressor_house": house_1,
                    "defender_house": house_7,
                }
            ],
            "trigger_items": angular_hits,
            "activation_items": [
                {
                    "watchpoint": "retrograde_mars",
                    "label": "Retrograde Mars",
                    "summary": "Mars is retrograde in the war event chart." if mars.get("retrograde") else "Mars is direct in the war event chart.",
                    "status": "present" if mars.get("retrograde") else "absent",
                }
            ],
        }

    if chart_type_id == "aries_ingress":
        ingress_dt = _find_latest_aries_ingress(anchor_dt)
        active_quarter = _active_cardinal_ingress(anchor_dt)
        cycle_context = _jupiter_saturn_cycle_context(ingress_dt)
        bundle = _resolve_bundle(
            bundle_resolver,
            ingress_dt.isoformat(),
            resolved_location,
            resolved_timezone,
            house_system_code,
            latitude=location_latitude,
            longitude=location_longitude,
        )
        angular_hits = _angular_planets(bundle)
        sun_lon = float(((_bundle_planets(bundle).get("Sun") or {}).get("longitude") or 0.0)) % 360.0
        duration_meta = _ingress_duration_metadata(bundle)
        framework_items = [
            _framework_ingress_item(
                "aries",
                ingress_dt.isoformat(),
                location=resolved_location,
                role="annual_framework",
                extra={
                    "sun_longitude": round(sun_lon, 6),
                    "cycle_phase": (cycle_context or {}).get("cycle_phase"),
                    "nearest_conjunction_datetime": (cycle_context or {}).get("nearest_conjunction_datetime"),
                    "ascendant_sign": duration_meta.get("ascendant_sign"),
                    "framework_modality": duration_meta.get("framework_modality"),
                    "framework_duration_months": duration_meta.get("framework_duration_months"),
                },
            )
        ]
        if str(active_quarter.get("ingress_id") or "") != "aries":
            framework_items.append(
                _framework_ingress_item(
                    str(active_quarter.get("ingress_id") or "aries"),
                    str(active_quarter.get("computed_datetime") or ingress_dt.isoformat()),
                    location=resolved_location,
                    role="active_quarterly_framework",
                )
            )
        return {
            "status": "computed",
            "primary_chart": _bundle_snapshot(bundle, label="Aries Ingress", chart_kind="aries_ingress", computed_datetime=ingress_dt),
            "supporting_charts": [],
            "signals": {
                "ingress_year": ingress_dt.year,
                "annual_ingress_datetime": ingress_dt.isoformat(),
                "active_quarterly_ingress": active_quarter,
                "sun_longitude": round(sun_lon, 6),
                "angular_hits": angular_hits,
                "framework_modality": duration_meta.get("framework_modality"),
                "framework_duration_months": duration_meta.get("framework_duration_months"),
                "ascendant_sign": duration_meta.get("ascendant_sign"),
            },
            "cycle_context": cycle_context,
            "framework_items": framework_items,
            "trigger_items": angular_hits
            + (
                [
                    {
                        "id": "mutation_and_conjunction_cycles",
                        "label": "Jupiter-Saturn Cycle",
                        "summary": (
                            f"Nearest Jupiter-Saturn conjunction is {(cycle_context or {}).get('nearest_conjunction_datetime')} "
                            f"in {(cycle_context or {}).get('conjunction_sign')}, with cycle phase {(cycle_context or {}).get('cycle_phase')}."
                        ),
                        "status": "computed" if cycle_context else "absent",
                        "watch_for": ["long_cycle_backdrop"],
                    }
                ]
                if cycle_context
                else []
            ),
            "activation_items": [],
        }

    if chart_type_id == "lunation":
        candidate = _find_nearest_lunation(anchor_dt, longitudes_at=longitudes_at)
        annual_ingress_dt = _find_latest_aries_ingress(candidate.exact_dt)
        active_quarter = _active_cardinal_ingress(candidate.exact_dt)
        cycle_context = _jupiter_saturn_cycle_context(candidate.exact_dt)
        bundle = _resolve_bundle(
            bundle_resolver,
            candidate.exact_dt.isoformat(),
            resolved_location,
            resolved_timezone,
            house_system_code,
            latitude=location_latitude,
            longitude=location_longitude,
        )
        planets = _bundle_planets(bundle)
        sun_lon = float(((planets.get("Sun") or {}).get("longitude") or 0.0)) % 360.0
        moon_lon = float(((planets.get("Moon") or {}).get("longitude") or 0.0)) % 360.0
        phase_sep = _angle_sep(moon_lon - sun_lon, 0.0 if candidate.event_type == "new_moon" else 180.0)
        framework_items = [
            _framework_ingress_item(
                "aries",
                annual_ingress_dt.isoformat(),
                location=resolved_location,
                role="annual_framework",
            )
        ]
        if str(active_quarter.get("ingress_id") or "") != "aries" or str(active_quarter.get("computed_datetime") or "") != annual_ingress_dt.isoformat():
            framework_items.append(
                _framework_ingress_item(
                    str(active_quarter.get("ingress_id") or "aries"),
                    str(active_quarter.get("computed_datetime") or annual_ingress_dt.isoformat()),
                    location=resolved_location,
                    role="active_quarterly_framework",
                )
            )
        return {
            "status": "computed",
            "primary_chart": _bundle_snapshot(bundle, label="Lunation Chart", chart_kind=candidate.event_type, computed_datetime=candidate.exact_dt),
            "supporting_charts": [],
            "signals": {
                "lunation_type": candidate.event_type,
                "annual_ingress_datetime": annual_ingress_dt.isoformat(),
                "active_quarterly_ingress": active_quarter,
                "phase_error_deg": round(phase_sep, 6),
                "sun_house": (planets.get("Sun") or {}).get("house"),
                "moon_house": (planets.get("Moon") or {}).get("house"),
            },
            "cycle_context": cycle_context,
            "framework_items": framework_items,
            "trigger_items": [
                {
                    "id": candidate.event_type,
                    "label": "Nearest Lunation",
                    "summary": f"Nearest {candidate.event_type.replace('_', ' ')} resolved to {candidate.exact_dt.isoformat()}",
                    "status": "computed",
                    "watch_for": [],
                },
                *(
                    [
                        {
                            "id": "mutation_and_conjunction_cycles",
                            "label": "Jupiter-Saturn Cycle",
                            "summary": (
                                f"Nearest Jupiter-Saturn conjunction is {(cycle_context or {}).get('nearest_conjunction_datetime')} "
                                f"in {(cycle_context or {}).get('conjunction_sign')}, with cycle phase {(cycle_context or {}).get('cycle_phase')}."
                            ),
                            "status": "computed" if cycle_context else "absent",
                            "watch_for": ["long_cycle_backdrop"],
                        }
                    ]
                    if cycle_context
                    else []
                ),
            ],
            "activation_items": [],
        }

    if chart_type_id == "eclipse":
        candidate, bundle, node_orb = _find_nearest_eclipse(
            anchor_dt,
            longitudes_at=longitudes_at,
            bundle_resolver=bundle_resolver,
            location=resolved_location,
            timezone_name=resolved_timezone,
            house_system_code=house_system_code,
            latitude=location_latitude,
            longitude=location_longitude,
        )
        annual_ingress_dt = _find_latest_aries_ingress(candidate.exact_dt)
        active_quarter = _active_cardinal_ingress(candidate.exact_dt)
        cycle_context = _jupiter_saturn_cycle_context(candidate.exact_dt)
        activation_hits = _eclipse_activation_hits(bundle, current_overlay_bundle)
        planets = _bundle_planets(bundle)
        node_lon = float(((planets.get("North Node") or {}).get("longitude") or 0.0)) % 360.0
        locality_proxy = _eclipse_locality_proxy(
            bundle,
            eclipse_type=candidate.event_type,
            visibility_scope=visibility_scope,
            location_context_type=location_context_type,
        )
        framework_items = [
            _framework_ingress_item(
                "aries",
                annual_ingress_dt.isoformat(),
                location=resolved_location,
                role="annual_framework",
            )
        ]
        if str(active_quarter.get("ingress_id") or "") != "aries" or str(active_quarter.get("computed_datetime") or "") != annual_ingress_dt.isoformat():
            framework_items.append(
                _framework_ingress_item(
                    str(active_quarter.get("ingress_id") or "aries"),
                    str(active_quarter.get("computed_datetime") or annual_ingress_dt.isoformat()),
                    location=resolved_location,
                    role="active_quarterly_framework",
                )
            )
        return {
            "status": "computed",
            "primary_chart": _bundle_snapshot(bundle, label="Eclipse Chart", chart_kind=candidate.event_type, computed_datetime=candidate.exact_dt),
            "supporting_charts": [
                _bundle_snapshot(current_overlay_bundle, label="Active Overlay Chart", chart_kind="current_overlay", computed_datetime=anchor_dt)
            ],
            "signals": {
                "eclipse_type": candidate.event_type,
                "node_orb_deg": round(node_orb, 6),
                "node_longitude": round(node_lon, 6),
                "activation_hits": activation_hits,
                "annual_ingress_datetime": annual_ingress_dt.isoformat(),
                "active_quarterly_ingress": active_quarter,
                "eclipse_locality": locality_proxy,
            },
            "cycle_context": cycle_context,
            "framework_items": framework_items,
            "trigger_items": [
                {
                    "id": candidate.event_type,
                    "label": "Nearest Eclipse",
                    "summary": f"Nearest {candidate.event_type.replace('_', ' ')} resolved to {candidate.exact_dt.isoformat()}",
                    "status": "computed",
                    "watch_for": [f"node_orb<={_ECLIPSE_NODE_ORB_DEG:g}deg"],
                },
                *(
                    [
                        {
                            "id": "mutation_and_conjunction_cycles",
                            "label": "Jupiter-Saturn Cycle",
                            "summary": (
                                f"Nearest Jupiter-Saturn conjunction is {(cycle_context or {}).get('nearest_conjunction_datetime')} "
                                f"in {(cycle_context or {}).get('conjunction_sign')}, with cycle phase {(cycle_context or {}).get('cycle_phase')}."
                            ),
                            "status": "computed" if cycle_context else "absent",
                            "watch_for": ["long_cycle_backdrop"],
                        }
                    ]
                    if cycle_context
                    else []
                ),
                {
                    "id": "eclipse_locality_proxy",
                    "label": "Eclipse Locality Proxy",
                    "summary": str(locality_proxy.get("summary") or ""),
                    "status": str(locality_proxy.get("visibility_status") or "approximate"),
                    "watch_for": [
                        str(locality_proxy.get("visibility_classification") or ""),
                        str(locality_proxy.get("territorial_relevance") or ""),
                    ],
                },
            ],
            "activation_items": [
                {
                    "watchpoint": "eclipse_degree_activation",
                    "label": "Eclipse-Degree Activation",
                    "summary": "Heavy-planet hits detected on the eclipse degree." if activation_hits else "No heavy-planet hits detected on the eclipse degree in the active overlay chart.",
                    "status": "present" if activation_hits else "absent",
                    "hits": activation_hits,
                },
                {
                    "watchpoint": "eclipse_locality_proxy",
                    "label": "Eclipse locality proxy",
                    "summary": str(locality_proxy.get("summary") or ""),
                    "status": str(locality_proxy.get("locality_confidence") or "low_proxy"),
                    "visibility_classification": locality_proxy.get("visibility_classification"),
                    "territorial_relevance": locality_proxy.get("territorial_relevance"),
                },
            ],
        }

    raise ValueError(f"Unsupported chart_type for chart resolution: {chart_type_id}")
