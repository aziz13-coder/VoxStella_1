from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

try:
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None  # type: ignore


BundleResolver = Callable[..., Dict[str, Any]]
LongitudeResolver = Callable[[datetime], Dict[str, float]]

_TRACKED_PLANETS = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "North Node",
)
_ANGULAR_HOUSES = {1, 4, 7, 10}
_HORIZON_ANGLES = {"ascendant", "descendant"}
_MERIDIAN_ANGLES = {"midheaven", "imum_coeli"}
_SEASONAL_INGRESSES = (
    ("spring_ingress", "Spring Ingress", 0.0, (3, 18), (3, 22)),
    ("summer_ingress", "Summer Ingress", 90.0, (6, 19), (6, 23)),
    ("autumn_ingress", "Autumn Ingress", 180.0, (9, 21), (9, 25)),
    ("winter_ingress", "Winter Ingress", 270.0, (12, 20), (12, 24)),
)
_LUNAR_PHASE_TARGETS = (
    ("new_moon", "New Moon", 0.0),
    ("first_quarter", "First Quarter", 90.0),
    ("full_moon", "Full Moon", 180.0),
    ("last_quarter", "Last Quarter", 270.0),
)


@dataclass(slots=True)
class SearchCandidate:
    event_type: str
    label: str
    exact_dt: datetime
    target_deg: float


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


def _hours_since(anchor: datetime, prior: datetime) -> float:
    return round(max(0.0, (_normalize_dt(anchor) - _normalize_dt(prior)).total_seconds() / 3600.0), 3)


def _signed_angle_diff(value: float, target: float) -> float:
    return ((_normalize_angle(value) - _normalize_angle(target) + 180.0) % 360.0) - 180.0


def _angle_sep(a: float, b: float) -> float:
    return abs(_signed_angle_diff(a, b))


def _julian_day_utc(dt: datetime) -> float:
    dt_utc = _normalize_dt(dt)
    hours = dt_utc.hour + (dt_utc.minute / 60.0) + (dt_utc.second / 3600.0) + (dt_utc.microsecond / 3_600_000_000.0)
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hours)  # type: ignore[union-attr]


def _swe_longitudes(dt: datetime) -> Dict[str, float]:
    if swe is None:
        raise RuntimeError("swisseph is required for weather chart search")
    jd_ut = _julian_day_utc(dt)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    sun_data, _ = swe.calc_ut(jd_ut, swe.SUN, flags)
    moon_data, _ = swe.calc_ut(jd_ut, swe.MOON, flags)
    return {
        "Sun": _normalize_angle(sun_data[0]),
        "Moon": _normalize_angle(moon_data[0]),
    }


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


def _angle_axis(angle_name: str) -> Optional[str]:
    normalized = str(angle_name or "").strip().lower()
    if normalized in _HORIZON_ANGLES:
        return "horizon"
    if normalized in _MERIDIAN_ANGLES:
        return "meridian"
    return None


def _nearest_angle(longitude: float, bundle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    points = _angle_points(bundle)
    if not points:
        return None
    nearest_label, nearest_longitude = min(points, key=lambda item: _angle_sep(longitude, item[1]))
    return {
        "angle": nearest_label,
        "distance_deg": round(_angle_sep(longitude, nearest_longitude), 3),
    }


def _angular_hits(bundle: Dict[str, Any], names: Iterable[str] = _TRACKED_PLANETS) -> List[Dict[str, Any]]:
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
                    "sign": info.get("sign"),
                    "longitude": float(info.get("longitude") or 0.0),
                    "retrograde": bool(info.get("retrograde")),
                    "closest_angle": (nearest_angle or {}).get("angle"),
                    "angle_distance_deg": (nearest_angle or {}).get("distance_deg"),
                }
            )
    return hits


def _angular_lines(
    bundle: Dict[str, Any],
    names: Iterable[str] = _TRACKED_PLANETS,
    *,
    max_distance: float = 10.0,
) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []
    for hit in _angular_hits(bundle, names):
        angle_name = str(hit.get("closest_angle") or "").strip().lower()
        axis = _angle_axis(angle_name)
        try:
            distance = float(hit.get("angle_distance_deg"))
        except Exception:
            distance = None
        if axis is None or distance is None or distance > max_distance:
            continue
        lines.append(
            {
                "planet": hit.get("planet"),
                "angle": angle_name,
                "axis": axis,
                "distance_deg": round(distance, 3),
                "house": hit.get("house"),
                "sign": hit.get("sign"),
                "longitude": hit.get("longitude"),
                "retrograde": bool(hit.get("retrograde")),
            }
        )
    lines.sort(
        key=lambda row: (
            float(row.get("distance_deg") or 999.0),
            str(row.get("planet") or ""),
            str(row.get("angle") or ""),
        )
    )
    return lines


def _target_zone_intersections(
    bundle: Dict[str, Any],
    names: Iterable[str] = _TRACKED_PLANETS,
    *,
    max_line_distance: float = 10.0,
    max_combined_distance: float = 16.0,
) -> List[Dict[str, Any]]:
    lines = _angular_lines(bundle, names, max_distance=max_line_distance)
    horizon_hits = [row for row in lines if str(row.get("axis") or "") == "horizon"]
    meridian_hits = [row for row in lines if str(row.get("axis") or "") == "meridian"]
    intersections: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()
    for horizon_hit in horizon_hits:
        for meridian_hit in meridian_hits:
            if str(horizon_hit.get("planet") or "") == str(meridian_hit.get("planet") or ""):
                continue
            combined_distance = round(
                float(horizon_hit.get("distance_deg") or 0.0)
                + float(meridian_hit.get("distance_deg") or 0.0),
                3,
            )
            if combined_distance > max_combined_distance:
                continue
            pair_key = tuple(
                sorted(
                    (
                        f"{horizon_hit.get('planet')}:{horizon_hit.get('angle')}",
                        f"{meridian_hit.get('planet')}:{meridian_hit.get('angle')}",
                    )
                )
            )
            if pair_key in seen:
                continue
            seen.add(pair_key)
            intersections.append(
                {
                    "pair_id": "|".join(pair_key),
                    "pair_label": (
                        f"{horizon_hit.get('planet')} {str(horizon_hit.get('angle') or '').upper()} x "
                        f"{meridian_hit.get('planet')} {str(meridian_hit.get('angle') or '').upper()}"
                    ),
                    "horizon_planet": horizon_hit.get("planet"),
                    "horizon_angle": horizon_hit.get("angle"),
                    "horizon_distance_deg": horizon_hit.get("distance_deg"),
                    "meridian_planet": meridian_hit.get("planet"),
                    "meridian_angle": meridian_hit.get("angle"),
                    "meridian_distance_deg": meridian_hit.get("distance_deg"),
                    "combined_distance_deg": combined_distance,
                    "zone": "primary" if combined_distance <= 8.0 else "extended",
                    "intersection_strength": round(max(0.0, max_combined_distance - combined_distance), 3),
                }
            )
    intersections.sort(
        key=lambda row: (
            float(row.get("combined_distance_deg") or 999.0),
            -float(row.get("intersection_strength") or 0.0),
            str(row.get("pair_label") or ""),
        )
    )
    return intersections


def _chart_snapshot(bundle: Dict[str, Any], *, label: str, chart_kind: str, computed_datetime: datetime) -> Dict[str, Any]:
    chart_data = bundle.get("chart_data") or {}
    meta = bundle.get("meta") or {}
    planets = _bundle_planets(bundle)
    tracked: Dict[str, Any] = {}
    for name in _TRACKED_PLANETS:
        info = planets.get(name)
        if not info:
            continue
        longitude = float(info.get("longitude") or 0.0)
        nearest_angle = _nearest_angle(longitude, bundle)
        tracked[name] = {
            "longitude": longitude,
            "sign": info.get("sign"),
            "house": info.get("house"),
            "retrograde": bool(info.get("retrograde")),
            "speed": float(info.get("speed") or 0.0),
            "closest_angle": (nearest_angle or {}).get("angle"),
            "angle_distance_deg": (nearest_angle or {}).get("distance_deg"),
        }
    angular_lines = _angular_lines(bundle)
    target_zone_intersections = _target_zone_intersections(bundle)
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
        "planets": tracked,
        "angular_lines": angular_lines,
        "target_zone_intersections": target_zone_intersections,
    }


def _solar_diff(dt: datetime, target_deg: float, *, longitudes_at: LongitudeResolver) -> float:
    return _signed_angle_diff(longitudes_at(dt)["Sun"], target_deg)


def _phase_value(dt: datetime, *, longitudes_at: LongitudeResolver) -> float:
    longitudes = longitudes_at(dt)
    return _normalize_angle(longitudes["Moon"] - longitudes["Sun"])


def _phase_crossed(prev_phase: float, current_phase: float, target_deg: float) -> bool:
    prev_rel = (prev_phase - target_deg) % 360.0
    curr_rel = (current_phase - target_deg) % 360.0
    return curr_rel < prev_rel or curr_rel == 0.0


def _binary_refine(
    start: datetime,
    end: datetime,
    *,
    evaluator,
    target_deg: float,
    iterations: int = 18,
) -> datetime:
    low = start
    high = end
    low_value = evaluator(low, target_deg)
    for _ in range(iterations):
        mid = low + ((high - low) / 2)
        mid_value = evaluator(mid, target_deg)
        if low_value == 0 or mid_value == 0:
            return mid if mid_value == 0 else low
        if low_value < 0 <= mid_value or low_value > 0 >= mid_value:
            high = mid
        else:
            low = mid
            low_value = mid_value
    return low + ((high - low) / 2)


def _find_solar_ingress_for_year(
    year: int,
    *,
    ingress_id: str,
    label: str,
    target_deg: float,
    start_month_day: Tuple[int, int],
    end_month_day: Tuple[int, int],
    longitudes_at: LongitudeResolver,
) -> SearchCandidate:
    start = datetime(year, start_month_day[0], start_month_day[1], 0, 0, tzinfo=timezone.utc)
    end = datetime(year, end_month_day[0], end_month_day[1], 23, 59, tzinfo=timezone.utc)

    current = start
    prev_value = _solar_diff(current, target_deg, longitudes_at=longitudes_at)
    prev_dt = current
    step = timedelta(hours=6)
    while current < end:
        current = min(current + step, end)
        current_value = _solar_diff(current, target_deg, longitudes_at=longitudes_at)
        if prev_value == 0:
            exact_dt = prev_dt
            break
        if current_value == 0 or prev_value < 0 <= current_value or prev_value > 0 >= current_value:
            exact_dt = _binary_refine(
                prev_dt,
                current,
                evaluator=lambda dt, deg: _solar_diff(dt, deg, longitudes_at=longitudes_at),
                target_deg=target_deg,
            )
            break
        prev_dt = current
        prev_value = current_value
    else:
        raise ValueError(f"Unable to resolve {ingress_id} for year {year}")

    return SearchCandidate(
        event_type=ingress_id,
        label=label,
        exact_dt=exact_dt,
        target_deg=target_deg,
    )


def _find_latest_cardinal_ingress(anchor_dt: datetime, *, longitudes_at: LongitudeResolver) -> SearchCandidate:
    candidates: List[SearchCandidate] = []
    for year in (anchor_dt.year - 1, anchor_dt.year):
        for ingress_id, label, target_deg, start_md, end_md in _SEASONAL_INGRESSES:
            candidate = _find_solar_ingress_for_year(
                year,
                ingress_id=ingress_id,
                label=label,
                target_deg=target_deg,
                start_month_day=start_md,
                end_month_day=end_md,
                longitudes_at=longitudes_at,
            )
            if candidate.exact_dt <= anchor_dt:
                candidates.append(candidate)
    if not candidates:
        raise ValueError("Unable to resolve a seasonal ingress before the requested forecast time")
    return sorted(candidates, key=lambda row: row.exact_dt)[-1]


def _find_latest_lunar_phase(anchor_dt: datetime, *, longitudes_at: LongitudeResolver) -> SearchCandidate:
    start = anchor_dt - timedelta(days=40)
    end = anchor_dt
    step = timedelta(hours=6)
    candidates: List[SearchCandidate] = []

    for event_type, label, target_deg in _LUNAR_PHASE_TARGETS:
        current = start
        prev_phase = _phase_value(current, longitudes_at=longitudes_at)
        prev_dt = current
        while current < end:
            current = min(current + step, end)
            current_phase = _phase_value(current, longitudes_at=longitudes_at)
            if prev_phase == target_deg:
                exact_dt = prev_dt
                if exact_dt <= anchor_dt:
                    candidates.append(
                        SearchCandidate(
                            event_type=event_type,
                            label=label,
                            exact_dt=exact_dt,
                            target_deg=target_deg,
                        )
                    )
            if _phase_crossed(prev_phase, current_phase, target_deg):
                exact_dt = _binary_refine(
                    prev_dt,
                    current,
                    evaluator=lambda dt, deg: _signed_angle_diff(_phase_value(dt, longitudes_at=longitudes_at), deg),
                    target_deg=target_deg,
                )
                if exact_dt <= anchor_dt:
                    candidates.append(
                        SearchCandidate(
                            event_type=event_type,
                            label=label,
                            exact_dt=exact_dt,
                            target_deg=target_deg,
                        )
                    )
            prev_dt = current
            prev_phase = current_phase

    if not candidates:
        raise ValueError("Unable to resolve a lunar phase before the requested forecast time")
    return sorted(candidates, key=lambda row: row.exact_dt)[-1]


def resolve_weather_chart_resolution(
    *,
    forecast_datetime: Any,
    location: Optional[str],
    timezone_name: Optional[str],
    house_system_code: Optional[str],
    bundle_resolver: BundleResolver,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Dict[str, Any]:
    anchor_dt = _normalize_dt(forecast_datetime)
    longitudes_at = _swe_longitudes
    seasonal = _find_latest_cardinal_ingress(anchor_dt, longitudes_at=longitudes_at)
    lunar = _find_latest_lunar_phase(anchor_dt, longitudes_at=longitudes_at)
    seasonal_age_hours = _hours_since(anchor_dt, seasonal.exact_dt)
    lunar_age_hours = _hours_since(anchor_dt, lunar.exact_dt)

    seasonal_bundle = _resolve_bundle(
        bundle_resolver,
        seasonal.exact_dt.isoformat(),
        location,
        timezone_name,
        house_system_code,
        latitude=latitude,
        longitude=longitude,
    )
    lunar_bundle = _resolve_bundle(
        bundle_resolver,
        lunar.exact_dt.isoformat(),
        location,
        timezone_name,
        house_system_code,
        latitude=latitude,
        longitude=longitude,
    )
    forecast_bundle = _resolve_bundle(
        bundle_resolver,
        anchor_dt.isoformat(),
        location,
        timezone_name,
        house_system_code,
        latitude=latitude,
        longitude=longitude,
    )

    seasonal_snapshot = _chart_snapshot(
        seasonal_bundle,
        label=seasonal.label,
        chart_kind=seasonal.event_type,
        computed_datetime=seasonal.exact_dt,
    )
    lunar_snapshot = _chart_snapshot(
        lunar_bundle,
        label=lunar.label,
        chart_kind=lunar.event_type,
        computed_datetime=lunar.exact_dt,
    )
    forecast_snapshot = _chart_snapshot(
        forecast_bundle,
        label="Forecast Chart",
        chart_kind="forecast_chart",
        computed_datetime=anchor_dt,
    )

    return {
        "status": "computed",
        "primary_chart": forecast_snapshot,
        "supporting_charts": [seasonal_snapshot, lunar_snapshot],
        "signals": {
            "seasonal_ingress": {
                "id": seasonal.event_type,
                "label": seasonal.label,
                "computed_datetime": seasonal.exact_dt.isoformat(),
                "age_hours": seasonal_age_hours,
                "age_days": round(seasonal_age_hours / 24.0, 3),
                "angular_hits": _angular_hits(seasonal_bundle),
                "angular_lines": seasonal_snapshot.get("angular_lines") or [],
                "target_zone_intersections": seasonal_snapshot.get("target_zone_intersections") or [],
            },
            "lunar_phase": {
                "id": lunar.event_type,
                "label": lunar.label,
                "computed_datetime": lunar.exact_dt.isoformat(),
                "age_hours": lunar_age_hours,
                "angular_hits": _angular_hits(lunar_bundle),
                "angular_lines": lunar_snapshot.get("angular_lines") or [],
                "target_zone_intersections": lunar_snapshot.get("target_zone_intersections") or [],
            },
            "forecast_chart": {
                "computed_datetime": anchor_dt.isoformat(),
                "angular_hits": _angular_hits(forecast_bundle),
                "angular_lines": forecast_snapshot.get("angular_lines") or [],
                "target_zone_intersections": forecast_snapshot.get("target_zone_intersections") or [],
            },
            "eclipse_overlay": {
                "status": "deferred",
                "decision": "not_active_in_runtime",
                "reason": "Weather eclipse timing remains observational only until locality and family discrimination narrow further.",
            },
        },
        "framework_items": [
            {
                "id": seasonal.event_type,
                "label": seasonal.label,
                "computed_datetime": seasonal.exact_dt.isoformat(),
                "age_days": round(seasonal_age_hours / 24.0, 3),
                "location": seasonal_snapshot.get("location"),
                "summary": f"{seasonal.label} sets the broader seasonal weather backdrop for the requested forecast time.",
            }
        ],
        "trigger_items": [
            {
                "id": lunar.event_type,
                "label": lunar.label,
                "computed_datetime": lunar.exact_dt.isoformat(),
                "age_hours": lunar_age_hours,
                "location": lunar_snapshot.get("location"),
                "summary": f"{lunar.label} is the latest lunar trigger before the requested forecast time.",
            }
        ],
        "locality_items": [
            {
                "id": "forecast_chart_angles",
                "label": "Forecast Chart Angles",
                "summary": "The first runtime uses forecast-chart angular emphasis and meridian/horizon target-zone proxies until a fuller weather map layer is implemented.",
                "angular_hits": _angular_hits(forecast_bundle),
            },
            {
                "id": "forecast_chart_target_zones",
                "label": "Forecast Target Zones",
                "summary": "The runtime treats tight horizon and meridian angular crossings as target-zone proxies for weather focus, following the benchmarked line-intersection workflow without claiming a full map runtime.",
                "target_zone_intersections": forecast_snapshot.get("target_zone_intersections") or [],
            },
        ],
        "research_flags": ["seed_runtime", "locality_proxy_only", "benchmark_backed", "eclipse_runtime_deferred"],
        "source_tags": ["riske", "bonatti", "watters", "green_carter"],
    }

