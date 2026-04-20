from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from astrocartography_assets import get_angle_reference, get_body_reference, get_range_policy

try:
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover - runtime safety
    swe = None  # type: ignore


DEFAULT_BODIES = [
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
]

DEFAULT_ANGLES = ["MC", "IC", "ASC", "DSC"]

PLANET_IDS = {
    "Sun": getattr(swe, "SUN", 0) if swe else 0,
    "Moon": getattr(swe, "MOON", 1) if swe else 1,
    "Mercury": getattr(swe, "MERCURY", 2) if swe else 2,
    "Venus": getattr(swe, "VENUS", 3) if swe else 3,
    "Mars": getattr(swe, "MARS", 4) if swe else 4,
    "Jupiter": getattr(swe, "JUPITER", 5) if swe else 5,
    "Saturn": getattr(swe, "SATURN", 6) if swe else 6,
    "Uranus": getattr(swe, "URANUS", 7) if swe else 7,
    "Neptune": getattr(swe, "NEPTUNE", 8) if swe else 8,
    "Pluto": getattr(swe, "PLUTO", 9) if swe else 9,
    "North Node": getattr(swe, "MEAN_NODE", 10) if swe else 10,
}

PLANET_COLORS = {
    "Sun": "#f59e0b",
    "Moon": "#2563eb",
    "Mercury": "#10b981",
    "Venus": "#ec4899",
    "Mars": "#ef4444",
    "Jupiter": "#7c3aed",
    "Saturn": "#111827",
    "Uranus": "#14b8a6",
    "Neptune": "#0ea5e9",
    "Pluto": "#334155",
    "North Node": "#eab308",
}

PLANET_PRIORITY = {
    "Sun": 0,
    "Moon": 1,
    "Venus": 2,
    "Jupiter": 3,
    "Mercury": 4,
    "Mars": 5,
    "Saturn": 6,
    "Uranus": 7,
    "Neptune": 8,
    "Pluto": 9,
    "North Node": 10,
}

ANGLE_META = {
    "MC": {"label": "MC", "dashArray": None},
    "IC": {"label": "IC", "dashArray": "8 6"},
    "ASC": {"label": "ASC", "dashArray": None},
    "DSC": {"label": "DSC", "dashArray": "6 6"},
}

try:
    _RANGE_POLICY = get_range_policy()
except Exception:
    _RANGE_POLICY = {"primary_radius_km": 300.0, "extended_radius_km": 500.0}
PRIMARY_READING_RADIUS_KM = float(_RANGE_POLICY.get("primary_radius_km") or 300.0)
EXTENDED_READING_RADIUS_KM = float(_RANGE_POLICY.get("extended_radius_km") or 500.0)

try:
    BODY_INTERPRETATION = get_body_reference()
except Exception:
    BODY_INTERPRETATION = {}
try:
    ANGLE_INTERPRETATION = get_angle_reference()
except Exception:
    ANGLE_INTERPRETATION = {}

_LATITUDE_SAMPLES = [float(lat) for lat in range(-89, 90, 1)]
_PARAN_LATITUDE_SAMPLES = [float(lat) for lat in range(-84, 85, 2)]

_LOCAL_SPACE_SECTOR_META = {
    "N": "North-facing routes emphasize outward direction, visibility, and initiative.",
    "NE": "North-east corridors blend movement with curiosity and planning.",
    "E": "East-facing routes sharpen beginnings, contacts, and immediate activation.",
    "SE": "South-east corridors press ambition, effort, and practical drive.",
    "S": "South-facing routes deepen embodiment, weight, and grounded commitment.",
    "SW": "South-west corridors consolidate loyalty, recovery, and private bonds.",
    "W": "West-facing routes pull toward other people, dialogue, and response.",
    "NW": "North-west corridors lean toward reflection, redirection, and perspective.",
}


def _require_swe() -> None:
    if swe is None:
        raise RuntimeError("pyswisseph not available")


def _normalize_body_list(bodies: Optional[Iterable[str]]) -> List[str]:
    if not bodies:
        return list(DEFAULT_BODIES)
    out: List[str] = []
    for raw in bodies:
        name = str(raw or "").strip()
        if name in PLANET_IDS and name not in out:
            out.append(name)
    return out or list(DEFAULT_BODIES)


def _normalize_angle_list(angles: Optional[Iterable[str]]) -> List[str]:
    if not angles:
        return list(DEFAULT_ANGLES)
    out: List[str] = []
    for raw in angles:
        name = str(raw or "").strip().upper()
        if name in ANGLE_META and name not in out:
            out.append(name)
    return out or list(DEFAULT_ANGLES)


def _parse_iso_utc(timestamp_iso: str) -> datetime:
    dt = datetime.fromisoformat(str(timestamp_iso).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _jd_ut_from_iso(timestamp_iso: str) -> float:
    dt_utc = _parse_iso_utc(timestamp_iso)
    hour = (
        dt_utc.hour
        + (dt_utc.minute / 60.0)
        + (dt_utc.second / 3600.0)
        + (dt_utc.microsecond / 3600000000.0)
    )
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)  # type: ignore[arg-type]


def _wrap360(value: float) -> float:
    return float(value) % 360.0


def _wrap180(value: float) -> float:
    wrapped = _wrap360(value)
    if wrapped > 180.0:
        wrapped -= 360.0
    return wrapped


def _equatorial_positions(timestamp_iso: str, bodies: Sequence[str]) -> Tuple[float, List[Dict[str, float]]]:
    _require_swe()
    jd_ut = _jd_ut_from_iso(timestamp_iso)
    gst_deg = _wrap360(float(swe.sidtime(jd_ut)) * 15.0)  # type: ignore[arg-type]
    flags = (
        getattr(swe, "FLG_SWIEPH", getattr(swe, "SEFLG_SWIEPH", 2))
        | getattr(swe, "FLG_SPEED", getattr(swe, "SEFLG_SPEED", 256))
        | getattr(swe, "FLG_EQUATORIAL", getattr(swe, "SEFLG_EQUATORIAL", 2048))
    )
    positions: List[Dict[str, float]] = []
    for body in bodies:
        planet_id = PLANET_IDS.get(body)
        if planet_id is None:
            continue
        pos, _ = swe.calc_ut(jd_ut, planet_id, flags)  # type: ignore[arg-type]
        positions.append(
            {
                "body": body,
                "ra_deg": _wrap360(float(pos[0])),
                "dec_deg": float(pos[1]),
            }
        )
    return gst_deg, positions


def _split_segment_if_needed(
    segments: List[List[List[float]]],
    current: List[List[float]],
    next_point: List[float],
) -> List[List[float]]:
    if not current:
        current.append(next_point)
        return current
    prev_lon = float(current[-1][1])
    next_lon = float(next_point[1])
    if abs(prev_lon - next_lon) > 180.0:
        if len(current) >= 2:
            segments.append(current)
        return [next_point]
    current.append(next_point)
    return current


def _meridian_segments(longitude_deg: float) -> List[List[List[float]]]:
    return [[[-89.0, float(longitude_deg)], [89.0, float(longitude_deg)]]]


def _angular_curve_segments(ra_deg: float, dec_deg: float, gst_deg: float, angle: str) -> List[List[List[float]]]:
    dec_rad = math.radians(float(dec_deg))
    segments: List[List[List[float]]] = []
    current: List[List[float]] = []
    for latitude in _LATITUDE_SAMPLES:
        phi = math.radians(float(latitude))
        try:
            cos_h0 = -math.tan(phi) * math.tan(dec_rad)
        except Exception:
            cos_h0 = 2.0
        if cos_h0 < -1.0 or cos_h0 > 1.0:
            if len(current) >= 2:
                segments.append(current)
            current = []
            continue
        h0_deg = math.degrees(math.acos(max(-1.0, min(1.0, cos_h0))))
        lst_deg = ra_deg - h0_deg if angle == "ASC" else ra_deg + h0_deg
        longitude_deg = _wrap180(lst_deg - gst_deg)
        current = _split_segment_if_needed(segments, current, [float(latitude), longitude_deg])
    if len(current) >= 2:
        segments.append(current)
    return segments


def _line_segments_for_angle(ra_deg: float, dec_deg: float, gst_deg: float, angle: str) -> List[List[List[float]]]:
    angle_name = str(angle or "").upper()
    if angle_name == "MC":
        return _meridian_segments(_wrap180(ra_deg - gst_deg))
    if angle_name == "IC":
        return _meridian_segments(_wrap180(ra_deg + 180.0 - gst_deg))
    if angle_name in {"ASC", "DSC"}:
        return _angular_curve_segments(ra_deg, dec_deg, gst_deg, angle_name)
    return []


def build_astrocartography_lines(
    timestamp_iso: str,
    bodies: Optional[Iterable[str]] = None,
    angles: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    normalized_bodies = _normalize_body_list(bodies)
    normalized_angles = _normalize_angle_list(angles)
    gst_deg, positions = _equatorial_positions(timestamp_iso, normalized_bodies)
    lines: List[Dict[str, Any]] = []
    for item in positions:
        body = str(item["body"])
        color = PLANET_COLORS.get(body, "#64748b")
        for angle in normalized_angles:
            segments = _line_segments_for_angle(item["ra_deg"], item["dec_deg"], gst_deg, angle)
            if not segments:
                continue
            lines.append(
                {
                    "id": f"{body}:{angle}",
                    "body": body,
                    "angle": angle,
                    "label": f"{body} {ANGLE_META[angle]['label']}",
                    "color": color,
                    "dash_array": ANGLE_META[angle]["dashArray"],
                    "segments": segments,
                }
            )
    return {
        "timestamp": timestamp_iso,
        "gst_deg": round(gst_deg, 6),
        "bodies": normalized_bodies,
        "angles": normalized_angles,
        "lines": lines,
    }


def _bearing_label(bearing_deg: float) -> str:
    sectors = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    idx = int(round((float(bearing_deg) % 360.0) / 22.5)) % len(sectors)
    return sectors[idx]


def _octant_label(bearing_deg: float) -> str:
    sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int(round((float(bearing_deg) % 360.0) / 45.0)) % len(sectors)
    return sectors[idx]


def _destination_point(latitude_deg: float, longitude_deg: float, bearing_deg: float, distance_km: float) -> List[float]:
    earth_radius_km = 6371.0
    angular_distance = float(distance_km) / earth_radius_km
    lat1 = math.radians(float(latitude_deg))
    lon1 = math.radians(float(longitude_deg))
    bearing = math.radians(float(bearing_deg))

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )
    lon_deg = _wrap180(math.degrees(lon2))
    return [round(math.degrees(lat2), 6), round(lon_deg, 6)]


def _horizontal_position(ra_deg: float, dec_deg: float, gst_deg: float, latitude_deg: float, longitude_deg: float) -> Dict[str, float]:
    lst_deg = _wrap360(float(gst_deg) + float(longitude_deg))
    hour_angle_rad = math.radians(_wrap180(lst_deg - float(ra_deg)))
    lat_rad = math.radians(float(latitude_deg))
    dec_rad = math.radians(float(dec_deg))

    sin_alt = (
        math.sin(dec_rad) * math.sin(lat_rad)
        + math.cos(dec_rad) * math.cos(lat_rad) * math.cos(hour_angle_rad)
    )
    sin_alt = max(-1.0, min(1.0, sin_alt))
    altitude_rad = math.asin(sin_alt)
    azimuth_rad = math.atan2(
        math.sin(hour_angle_rad),
        (math.cos(hour_angle_rad) * math.sin(lat_rad)) - (math.tan(dec_rad) * math.cos(lat_rad)),
    )
    azimuth_deg = (math.degrees(azimuth_rad) + 180.0) % 360.0
    return {
        "azimuth_deg": round(azimuth_deg, 3),
        "altitude_deg": round(math.degrees(altitude_rad), 3),
        "local_sidereal_deg": round(lst_deg, 3),
    }


def build_local_space_rays(
    timestamp_iso: str,
    latitude: float,
    longitude: float,
    bodies: Optional[Iterable[str]] = None,
    max_distance_km: int = 3000,
    step_km: int = 300,
) -> Dict[str, Any]:
    normalized_bodies = _normalize_body_list(bodies)
    gst_deg, positions = _equatorial_positions(timestamp_iso, normalized_bodies)
    origin = [round(float(latitude), 6), round(float(longitude), 6)]
    rays: List[Dict[str, Any]] = []

    for item in positions:
        body = str(item.get("body") or "")
        horizontal = _horizontal_position(
            float(item.get("ra_deg") or 0.0),
            float(item.get("dec_deg") or 0.0),
            gst_deg,
            float(latitude),
            float(longitude),
        )
        azimuth_deg = float(horizontal.get("azimuth_deg") or 0.0)
        altitude_deg = float(horizontal.get("altitude_deg") or 0.0)
        points = [origin]
        for distance_km in range(int(step_km), int(max_distance_km) + int(step_km), int(step_km)):
            points.append(_destination_point(latitude, longitude, azimuth_deg, float(distance_km)))
        rays.append(
            {
                "id": f"{body}:local-space",
                "body": body,
                "label": f"{body} Local Space",
                "color": PLANET_COLORS.get(body, "#64748b"),
                "azimuth_deg": round(azimuth_deg, 2),
                "direction_label": _bearing_label(azimuth_deg),
                "altitude_deg": round(altitude_deg, 2),
                "above_horizon": altitude_deg >= 0.0,
                "segments": [points],
                "summary": (
                    f"{body} points toward {_bearing_label(azimuth_deg)} ({round(azimuth_deg, 1)}°) "
                    f"from this city."
                ),
            }
        )

    rays.sort(
        key=lambda item: (
            not bool(item.get("above_horizon")),
            -float(item.get("altitude_deg") or 0.0),
            PLANET_PRIORITY.get(str(item.get("body") or ""), 99),
        )
    )
    visible = [item for item in rays if item.get("above_horizon")]
    hidden = [item for item in rays if not item.get("above_horizon")]
    headline = (
        f"Local Space is led by {visible[0]['body']} toward {visible[0]['direction_label']}."
        if visible
        else "Local Space rays are mostly below the horizon for this target moment."
    )
    return {
        "timestamp": timestamp_iso,
        "origin": {
            "latitude": origin[0],
            "longitude": origin[1],
        },
        "reference_radius_km": int(max_distance_km),
        "step_km": int(step_km),
        "headline": headline,
        "visible_count": len(visible),
        "hidden_count": len(hidden),
        "rays": rays,
    }


def build_local_space_workspace(
    timestamp_iso: str,
    latitude: float,
    longitude: float,
    bodies: Optional[Iterable[str]] = None,
    max_distance_km: int = 3000,
    step_km: int = 300,
) -> Dict[str, Any]:
    payload = build_local_space_rays(
        timestamp_iso,
        latitude,
        longitude,
        bodies=bodies,
        max_distance_km=max_distance_km,
        step_km=step_km,
    )
    rays = [dict(item) for item in (payload.get("rays") or []) if isinstance(item, dict)]
    visible = []
    hidden = []
    sector_groups: Dict[str, Dict[str, Any]] = {}

    for ray in rays:
        azimuth_deg = float(ray.get("azimuth_deg") or 0.0)
        sector_label = _octant_label(azimuth_deg)
        body = str(ray.get("body") or "")
        body_meta = BODY_INTERPRETATION.get(body, {})
        ray["sector_label"] = sector_label
        ray["summary"] = str(ray.get("summary") or "").replace("В°", " deg").replace("°", " deg")
        ray["orientation_note"] = (
            f"{body} pushes {body_meta.get('core_themes', 'its core themes')} "
            f"toward the {sector_label} sector from this city."
        )
        if ray.get("above_horizon"):
            visible.append(ray)
            entry = sector_groups.setdefault(
                sector_label,
                {
                    "sector": sector_label,
                    "summary": _LOCAL_SPACE_SECTOR_META.get(sector_label, "This corridor colors how Local Space behaves here."),
                    "bodies": [],
                    "lead_body": None,
                    "top_altitude_deg": -999.0,
                    "count": 0,
                },
            )
            entry["bodies"].append(body)
            entry["count"] = int(entry.get("count") or 0) + 1
            altitude = float(ray.get("altitude_deg") or 0.0)
            if altitude > float(entry.get("top_altitude_deg") or -999.0):
                entry["top_altitude_deg"] = altitude
                entry["lead_body"] = body
        else:
            hidden.append(ray)

    dominant_sectors = sorted(
        sector_groups.values(),
        key=lambda item: (
            -int(item.get("count") or 0),
            -float(item.get("top_altitude_deg") or 0.0),
            str(item.get("sector") or ""),
        ),
    )
    range_rings_km = [ring for ring in (500, 1500, 3000) if ring <= int(max_distance_km)]
    if visible and dominant_sectors:
        headline = (
            f"Local Space is led by {visible[0]['body']} toward {visible[0]['direction_label']}. "
            f"The strongest sector is {dominant_sectors[0]['sector']}."
        )
    else:
        headline = "Local Space rays are mostly below the horizon for this target moment."

    return {
        **payload,
        "headline": headline,
        "range_rings_km": range_rings_km,
        "visible_count": len(visible),
        "hidden_count": len(hidden),
        "dominant_sectors": [
            {
                "sector": item.get("sector"),
                "summary": item.get("summary"),
                "count": item.get("count"),
                "lead_body": item.get("lead_body"),
                "bodies": item.get("bodies"),
            }
            for item in dominant_sectors[:4]
        ],
        "peak_rays": visible[:4],
        "shadow_rays": hidden[:3],
        "rays": rays,
    }


def _latlon_to_xy_km(lat_deg: float, lon_deg: float, ref_lat_deg: float) -> Tuple[float, float]:
    mean_lat_rad = math.radians(ref_lat_deg)
    x = float(lon_deg) * 111.320 * math.cos(mean_lat_rad)
    y = float(lat_deg) * 110.574
    return x, y


def _point_segment_distance_km(
    point_lat: float,
    point_lon: float,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> float:
    ref_lat = (float(point_lat) + float(start_lat) + float(end_lat)) / 3.0
    px, py = _latlon_to_xy_km(point_lat, point_lon, ref_lat)
    ax, ay = _latlon_to_xy_km(start_lat, start_lon, ref_lat)
    bx, by = _latlon_to_xy_km(end_lat, end_lon, ref_lat)
    dx = bx - ax
    dy = by - ay
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / ((dx * dx) + (dy * dy))
    t = max(0.0, min(1.0, t))
    cx = ax + (t * dx)
    cy = ay + (t * dy)
    return math.hypot(px - cx, py - cy)


def nearest_lines_for_point(
    lines: Sequence[Dict[str, Any]],
    latitude: float,
    longitude: float,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    for line in lines:
        best_distance = None
        for segment in line.get("segments") or []:
            if not isinstance(segment, list):
                continue
            if len(segment) == 1:
                pt = segment[0]
                try:
                    dist = _point_segment_distance_km(latitude, longitude, pt[0], pt[1], pt[0], pt[1])
                except Exception:
                    continue
                best_distance = dist if best_distance is None else min(best_distance, dist)
                continue
            for idx in range(len(segment) - 1):
                a = segment[idx]
                b = segment[idx + 1]
                try:
                    dist = _point_segment_distance_km(latitude, longitude, a[0], a[1], b[0], b[1])
                except Exception:
                    continue
                best_distance = dist if best_distance is None else min(best_distance, dist)
        if best_distance is None:
            continue
        ranked.append(
            {
                "id": line.get("id"),
                "body": line.get("body"),
                "angle": line.get("angle"),
                "label": line.get("label"),
                "color": line.get("color"),
                "distance_km": round(float(best_distance), 1),
            }
        )
    ranked.sort(key=lambda row: (float(row.get("distance_km") or 0.0), str(row.get("label") or "")))
    return ranked[: max(1, int(limit))]


def _distance_zone(
    distance_km: float,
    primary_radius_km: float = PRIMARY_READING_RADIUS_KM,
    extended_radius_km: float = EXTENDED_READING_RADIUS_KM,
) -> str:
    if distance_km <= primary_radius_km:
        return "primary"
    if distance_km <= extended_radius_km:
        return "extended"
    return "background"


def _line_proximity_score(
    distance_km: float,
    primary_radius_km: float = PRIMARY_READING_RADIUS_KM,
    extended_radius_km: float = EXTENDED_READING_RADIUS_KM,
) -> int:
    extended_radius_km = max(float(extended_radius_km), float(primary_radius_km) + 1.0)
    distance_km = max(0.0, float(distance_km))
    if distance_km <= primary_radius_km:
        closeness = 0.7 + (0.3 * (1.0 - (distance_km / max(primary_radius_km, 1.0))))
    elif distance_km <= extended_radius_km:
        closeness = 0.3 + (0.35 * ((extended_radius_km - distance_km) / (extended_radius_km - primary_radius_km)))
    else:
        overflow = min(1.0, (distance_km - extended_radius_km) / max(extended_radius_km, 1.0))
        closeness = max(0.05, 0.25 * (1.0 - overflow))
    return int(round(min(100.0, max(0.0, closeness * 100.0))))


def enrich_line_readings(
    rows: Sequence[Dict[str, Any]],
    primary_radius_km: float = PRIMARY_READING_RADIUS_KM,
    extended_radius_km: float = EXTENDED_READING_RADIUS_KM,
) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for row in rows:
        body = str(row.get("body") or "")
        angle = str(row.get("angle") or "").upper()
        distance_km = float(row.get("distance_km") or 0.0)
        zone = _distance_zone(distance_km, primary_radius_km=primary_radius_km, extended_radius_km=extended_radius_km)
        body_meta = BODY_INTERPRETATION.get(body, {})
        angle_meta = ANGLE_INTERPRETATION.get(angle, {})
        core_themes = body_meta.get("core_themes", "strong thematic emphasis")
        common_upside = body_meta.get("common_upside", "meaningful development")
        common_caution = body_meta.get("common_caution", "excess")
        domain = angle_meta.get("interprets_through", "this angle domain")
        shorthand = angle_meta.get("user_shorthand", "what changes here")
        summary = (
            f"{body} on the {angle} line emphasizes "
            f"{core_themes} through {domain}."
        )
        upside = f"This line often supports {common_upside}."
        caution = f"Watch for {common_caution}."
        enriched.append(
            {
                **row,
                "distance_km": round(distance_km, 1),
                "zone": zone,
                "signal_score": _line_proximity_score(
                    distance_km,
                    primary_radius_km=primary_radius_km,
                    extended_radius_km=extended_radius_km,
                ),
                "core_themes": core_themes,
                "upside": common_upside,
                "interprets_through": domain,
                "user_shorthand": shorthand,
                "summary": summary,
                "upside_note": upside,
                "caution": caution,
                "source_refs": [body_meta.get("source_ref"), angle_meta.get("source_ref")],
            }
        )
    return enriched


def build_location_reading(
    lines: Sequence[Dict[str, Any]],
    latitude: float,
    longitude: float,
    limit: int = 8,
    primary_radius_km: float = PRIMARY_READING_RADIUS_KM,
    extended_radius_km: float = EXTENDED_READING_RADIUS_KM,
) -> Dict[str, Any]:
    nearest = nearest_lines_for_point(lines, latitude, longitude, limit=limit)
    readings = enrich_line_readings(
        nearest,
        primary_radius_km=primary_radius_km,
        extended_radius_km=extended_radius_km,
    )
    zone_counts = {
        "primary": sum(1 for row in readings if row.get("zone") == "primary"),
        "extended": sum(1 for row in readings if row.get("zone") == "extended"),
        "background": sum(1 for row in readings if row.get("zone") == "background"),
    }
    lead_line = readings[0] if readings else None
    support_candidates = [row for row in readings[1:] if row.get("zone") != "background"]
    support_line = support_candidates[0] if support_candidates else (readings[1] if len(readings) > 1 else None)

    if not lead_line:
        headline = "No nearby astrocartography lines were found for this location in the current filter set."
        support_note = "Broaden the active bodies or inspect a different city to surface a stronger pattern."
    elif lead_line.get("zone") == "primary":
        headline = (
            f"{lead_line.get('label')} is the clearest nearby line. "
            f"Expect {lead_line.get('core_themes') or 'its themes'} to show up through "
            f"{lead_line.get('interprets_through') or 'this angle domain'}."
        )
        support_note = (
            f"Secondary support comes from {support_line.get('label')} and reinforces {support_line.get('upside') or 'that tone'}."
            if support_line
            else "This looks like a concentrated single-line emphasis rather than a clustered zone."
        )
    elif lead_line.get("zone") == "extended":
        headline = (
            f"{lead_line.get('label')} is the nearest active line here. "
            f"It points toward {lead_line.get('upside') or 'that topic'}, but more as a surrounding field than a direct hit."
        )
        support_note = (
            f"{support_line.get('label')} adds a second layer nearby."
            if support_line
            else "A closer city may sharpen the same theme more directly."
        )
    else:
        headline = (
            f"This location is comparatively quiet in the current scan. "
            f"{lead_line.get('label')} is the closest background line."
        )
        support_note = "Use this kind of location when you want distance from dominant line pressure."

    top_scores = [int(row.get("signal_score") or 0) for row in readings[:3]]
    signal_score = int(round(sum(top_scores) / max(1, len(top_scores)))) if top_scores else 0

    return {
        "signal_score": signal_score,
        "headline": headline,
        "support_note": support_note,
        "lead_line": lead_line,
        "support_line": support_line,
        "zone_counts": zone_counts,
        "nearest_lines": readings,
    }


def _segment_intersection(
    a1: Sequence[float],
    a2: Sequence[float],
    b1: Sequence[float],
    b2: Sequence[float],
) -> Optional[Tuple[float, float]]:
    x1, y1 = float(a1[1]), float(a1[0])
    x2, y2 = float(a2[1]), float(a2[0])
    x3, y3 = float(b1[1]), float(b1[0])
    x4, y4 = float(b2[1]), float(b2[0])
    denom = ((x1 - x2) * (y3 - y4)) - ((y1 - y2) * (x3 - x4))
    if abs(denom) < 1e-9:
        return None
    px = (((x1 * y2) - (y1 * x2)) * (x3 - x4) - (x1 - x2) * ((x3 * y4) - (y3 * x4))) / denom
    py = (((x1 * y2) - (y1 * x2)) * (y3 - y4) - (y1 - y2) * ((x3 * y4) - (y3 * x4))) / denom

    def _between(value: float, start: float, end: float) -> bool:
        return min(start, end) - 1e-9 <= value <= max(start, end) + 1e-9

    if _between(px, x1, x2) and _between(py, y1, y2) and _between(px, x3, x4) and _between(py, y3, y4):
        return (py, px)
    return None


def _point_distance_km(point_a: Sequence[float], point_b: Sequence[float]) -> float:
    return _point_segment_distance_km(float(point_a[0]), float(point_a[1]), float(point_b[0]), float(point_b[1]), float(point_b[0]), float(point_b[1]))


def _angular_separation_deg(a_deg: float, b_deg: float) -> float:
    diff = abs(_wrap180(float(a_deg) - float(b_deg)))
    return min(diff, 360.0 - diff)


def _circular_midpoint_deg(a_deg: float, b_deg: float) -> float:
    a_rad = math.radians(float(a_deg))
    b_rad = math.radians(float(b_deg))
    x = math.cos(a_rad) + math.cos(b_rad)
    y = math.sin(a_rad) + math.sin(b_rad)
    if abs(x) < 1e-9 and abs(y) < 1e-9:
        return _wrap360((float(a_deg) + float(b_deg)) / 2.0)
    return _wrap360(math.degrees(math.atan2(y, x)))


def _paran_event_lsts(ra_deg: float, dec_deg: float, latitude_deg: float) -> Dict[str, float]:
    events = {
        "MC": _wrap360(ra_deg),
        "IC": _wrap360(ra_deg + 180.0),
    }
    dec_rad = math.radians(float(dec_deg))
    phi = math.radians(float(latitude_deg))
    try:
        cos_h0 = -math.tan(phi) * math.tan(dec_rad)
    except Exception:
        cos_h0 = 2.0
    if -1.0 <= cos_h0 <= 1.0:
        h0_deg = math.degrees(math.acos(max(-1.0, min(1.0, cos_h0))))
        events["ASC"] = _wrap360(ra_deg - h0_deg)
        events["DSC"] = _wrap360(ra_deg + h0_deg)
    return events


def build_paran_candidates_for_point(
    timestamp_iso: str,
    latitude: float,
    longitude: float,
    bodies: Optional[Iterable[str]] = None,
    limit: int = 12,
    max_distance_km: float = 1200.0,
    orb_deg: float = 2.0,
) -> Dict[str, Any]:
    normalized_bodies = _normalize_body_list(bodies)
    gst_deg, positions = _equatorial_positions(timestamp_iso, normalized_bodies)
    horizon_angles = {"ASC", "DSC"}
    meridian_angles = {"MC", "IC"}
    candidates: List[Dict[str, Any]] = []

    for idx, item_a in enumerate(positions):
        events_a = _paran_event_lsts(float(item_a.get("ra_deg") or 0.0), float(item_a.get("dec_deg") or 0.0), float(latitude))
        body_a = str(item_a.get("body") or "")
        for item_b in positions[idx + 1:]:
            body_b = str(item_b.get("body") or "")
            if body_a == body_b:
                continue
            events_b = _paran_event_lsts(float(item_b.get("ra_deg") or 0.0), float(item_b.get("dec_deg") or 0.0), float(latitude))
            for angle_a, lst_a in events_a.items():
                for angle_b, lst_b in events_b.items():
                    if not (
                        (angle_a in horizon_angles and angle_b in meridian_angles)
                        or (angle_a in meridian_angles and angle_b in horizon_angles)
                    ):
                        continue
                    orb = _angular_separation_deg(lst_a, lst_b)
                    if orb > float(orb_deg):
                        continue
                    common_lst = _circular_midpoint_deg(lst_a, lst_b)
                    paran_lon = _wrap180(common_lst - gst_deg)
                    distance_km = _point_segment_distance_km(
                        float(latitude),
                        float(longitude),
                        float(latitude),
                        paran_lon,
                        float(latitude),
                        paran_lon,
                    )
                    if distance_km > float(max_distance_km):
                        continue
                    score_from_orb = max(0.0, 1.0 - (orb / max(float(orb_deg), 0.1)))
                    score_from_distance = max(0.0, 1.0 - (distance_km / max(float(max_distance_km), 1.0)))
                    signal_score = int(round(max(0.0, min(100.0, ((0.55 * score_from_orb) + (0.45 * score_from_distance)) * 100.0))))
                    zone = _distance_zone(distance_km, primary_radius_km=PRIMARY_READING_RADIUS_KM, extended_radius_km=max_distance_km)
                    candidates.append(
                        {
                            "id": f"{body_a}:{angle_a}|{body_b}:{angle_b}:paran",
                            "kind": "paran",
                            "label": f"{body_a} {angle_a} paran {body_b} {angle_b}",
                            "body_a": body_a,
                            "angle_a": angle_a,
                            "body_b": body_b,
                            "angle_b": angle_b,
                            "planets": [body_a, body_b],
                            "orb_deg": round(float(orb), 3),
                            "orb_minutes": round(float(orb) * 4.0, 2),
                            "distance_km": round(float(distance_km), 1),
                            "longitude_deg": round(float(paran_lon), 4),
                            "point": [round(float(latitude), 4), round(float(paran_lon), 4)],
                            "zone": zone,
                            "signal_score": signal_score,
                            "summary": (
                                f"{body_a} {angle_a} and {body_b} {angle_b} peak together at this latitude "
                                f"with an orb of {round(float(orb), 2)} deg."
                            ),
                        }
                    )

    candidates.sort(
        key=lambda item: (
            float(item.get("distance_km") or 999999.0),
            float(item.get("orb_deg") or 999999.0),
            str(item.get("label") or ""),
        )
    )
    lead = candidates[0] if candidates else None
    headline = (
        f"{lead.get('label')} is the clearest nearby paran."
        if lead
        else "No nearby parans were found for the current latitude and body set."
    )
    return {
        "headline": headline,
        "orb_deg": round(float(orb_deg), 2),
        "max_distance_km": round(float(max_distance_km), 1),
        "count": len(candidates),
        "lead_paran": lead,
        "items": candidates[: max(1, int(limit))],
    }


def build_global_paran_tracks(
    timestamp_iso: str,
    bodies: Optional[Iterable[str]] = None,
    *,
    orb_deg: float = 1.0,
    limit: int = 24,
    min_points: int = 6,
) -> Dict[str, Any]:
    normalized_bodies = _normalize_body_list(bodies)
    gst_deg, positions = _equatorial_positions(timestamp_iso, normalized_bodies)
    event_cache: Dict[Tuple[str, float], Dict[str, float]] = {}
    tracks: List[Dict[str, Any]] = []

    def _events_for(body_name: str, ra_deg: float, dec_deg: float, latitude_deg: float) -> Dict[str, float]:
        cache_key = (body_name, float(latitude_deg))
        cached = event_cache.get(cache_key)
        if cached is not None:
            return cached
        events = _paran_event_lsts(ra_deg, dec_deg, latitude_deg)
        event_cache[cache_key] = events
        return events

    for idx, item_a in enumerate(positions):
        body_a = str(item_a.get("body") or "")
        ra_a = float(item_a.get("ra_deg") or 0.0)
        dec_a = float(item_a.get("dec_deg") or 0.0)
        for item_b in positions[idx + 1:]:
            body_b = str(item_b.get("body") or "")
            ra_b = float(item_b.get("ra_deg") or 0.0)
            dec_b = float(item_b.get("dec_deg") or 0.0)
            pair_patterns = [
                (body_a, ra_a, dec_a, "ASC", body_b, ra_b, dec_b, "MC"),
                (body_a, ra_a, dec_a, "ASC", body_b, ra_b, dec_b, "IC"),
                (body_a, ra_a, dec_a, "DSC", body_b, ra_b, dec_b, "MC"),
                (body_a, ra_a, dec_a, "DSC", body_b, ra_b, dec_b, "IC"),
                (body_a, ra_a, dec_a, "MC", body_b, ra_b, dec_b, "ASC"),
                (body_a, ra_a, dec_a, "MC", body_b, ra_b, dec_b, "DSC"),
                (body_a, ra_a, dec_a, "IC", body_b, ra_b, dec_b, "ASC"),
                (body_a, ra_a, dec_a, "IC", body_b, ra_b, dec_b, "DSC"),
            ]
            for lhs_body, lhs_ra, lhs_dec, lhs_angle, rhs_body, rhs_ra, rhs_dec, rhs_angle in pair_patterns:
                segments: List[List[List[float]]] = []
                current: List[List[float]] = []
                min_orb_seen: Optional[float] = None
                total_points = 0
                exact_hits = 0
                for latitude_deg in _PARAN_LATITUDE_SAMPLES:
                    lhs_events = _events_for(lhs_body, lhs_ra, lhs_dec, latitude_deg)
                    rhs_events = _events_for(rhs_body, rhs_ra, rhs_dec, latitude_deg)
                    if lhs_angle not in lhs_events or rhs_angle not in rhs_events:
                        if len(current) >= 2:
                            segments.append(current)
                        current = []
                        continue
                    orb = _angular_separation_deg(lhs_events[lhs_angle], rhs_events[rhs_angle])
                    if orb > float(orb_deg):
                        if len(current) >= 2:
                            segments.append(current)
                        current = []
                        continue
                    common_lst = _circular_midpoint_deg(lhs_events[lhs_angle], rhs_events[rhs_angle])
                    longitude_deg = _wrap180(common_lst - gst_deg)
                    current = _split_segment_if_needed(segments, current, [float(latitude_deg), float(longitude_deg)])
                    total_points += 1
                    if orb <= max(0.2, float(orb_deg) * 0.35):
                        exact_hits += 1
                    if min_orb_seen is None or orb < min_orb_seen:
                        min_orb_seen = orb
                if len(current) >= 2:
                    segments.append(current)
                if not segments or total_points < int(min_points):
                    continue
                tracks.append(
                    {
                        "id": f"{lhs_body}:{lhs_angle}|{rhs_body}:{rhs_angle}:global-paran",
                        "kind": "global-paran",
                        "label": f"{lhs_body} {lhs_angle} paran {rhs_body} {rhs_angle}",
                        "body_a": lhs_body,
                        "angle_a": lhs_angle,
                        "body_b": rhs_body,
                        "angle_b": rhs_angle,
                        "color": "#7c3aed",
                        "dash_array": "3 8",
                        "segments": segments,
                        "sample_count": total_points,
                        "exact_hits": exact_hits,
                        "min_orb_deg": round(float(min_orb_seen or 0.0), 3),
                        "summary": (
                            f"{lhs_body} {lhs_angle} and {rhs_body} {rhs_angle} stay in paran "
                            f"alignment along this latitude corridor."
                        ),
                    }
                )

    tracks.sort(
        key=lambda item: (
            float(item.get("min_orb_deg") or 999999.0),
            -int(item.get("exact_hits") or 0),
            -int(item.get("sample_count") or 0),
            str(item.get("label") or ""),
        )
    )
    lead = tracks[0] if tracks else None
    headline = (
        f"{lead.get('label')} is the clearest global paran corridor in the active map."
        if lead
        else "No stable global paran corridors were found for the current body set."
    )
    return {
        "headline": headline,
        "orb_deg": round(float(orb_deg), 2),
        "latitude_step_deg": 2,
        "track_count": len(tracks),
        "lead_track": lead,
        "tracks": tracks[: max(1, int(limit))],
    }


def crossing_candidates_for_point(
    lines: Sequence[Dict[str, Any]],
    latitude: float,
    longitude: float,
    nearest_rows: Optional[Sequence[Dict[str, Any]]] = None,
    limit: int = 8,
    max_distance_km: float = EXTENDED_READING_RADIUS_KM,
) -> List[Dict[str, Any]]:
    line_lookup = {str(line.get("id") or ""): line for line in lines if isinstance(line, dict)}
    selected_rows = list(nearest_rows or nearest_lines_for_point(lines, latitude, longitude, limit=8))
    candidates: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()

    for idx, row_a in enumerate(selected_rows):
        line_a = line_lookup.get(str(row_a.get("id") or ""))
        if not line_a:
            continue
        for row_b in selected_rows[idx + 1:]:
            line_b = line_lookup.get(str(row_b.get("id") or ""))
            if not line_b:
                continue
            if str(row_a.get("body") or "") == str(row_b.get("body") or ""):
                continue
            pair_key = tuple(sorted([str(row_a.get("id") or ""), str(row_b.get("id") or "")]))
            if pair_key in seen:
                continue
            seen.add(pair_key)

            best_point = None
            best_distance = None
            for segment_a in line_a.get("segments") or []:
                if not isinstance(segment_a, list) or len(segment_a) < 2:
                    continue
                for segment_b in line_b.get("segments") or []:
                    if not isinstance(segment_b, list) or len(segment_b) < 2:
                        continue
                    for seg_a_idx in range(len(segment_a) - 1):
                        a1 = segment_a[seg_a_idx]
                        a2 = segment_a[seg_a_idx + 1]
                        for seg_b_idx in range(len(segment_b) - 1):
                            b1 = segment_b[seg_b_idx]
                            b2 = segment_b[seg_b_idx + 1]
                            point = _segment_intersection(a1, a2, b1, b2)
                            if point is None:
                                continue
                            distance = _point_segment_distance_km(latitude, longitude, point[0], point[1], point[0], point[1])
                            if best_distance is None or distance < best_distance:
                                best_distance = distance
                                best_point = point

            if best_distance is None:
                fallback_distance = (float(row_a.get("distance_km") or 0.0) + float(row_b.get("distance_km") or 0.0)) / 2.0
                if fallback_distance > max_distance_km:
                    continue
                best_distance = fallback_distance
                kind = "blend"
            else:
                if best_distance > max_distance_km:
                    continue
                kind = "crossing"

            zone = _distance_zone(best_distance, primary_radius_km=PRIMARY_READING_RADIUS_KM, extended_radius_km=max_distance_km)
            score = _line_proximity_score(best_distance, primary_radius_km=PRIMARY_READING_RADIUS_KM, extended_radius_km=max_distance_km)
            candidates.append(
                {
                    "id": f"{row_a.get('id')}|{row_b.get('id')}",
                    "label": f"{row_a.get('label')} x {row_b.get('label')}",
                    "kind": kind,
                    "planets": [row_a.get("body"), row_b.get("body")],
                    "lines": [row_a.get("id"), row_b.get("id")],
                    "distance_km": round(float(best_distance), 1),
                    "zone": zone,
                    "signal_score": score,
                    "point": [round(float(best_point[0]), 4), round(float(best_point[1]), 4)] if best_point else None,
                }
            )

    candidates.sort(key=lambda row: (float(row.get("distance_km") or 0.0), str(row.get("label") or "")))
    return candidates[: max(1, int(limit))]


def build_intersection_workspace(
    lines: Sequence[Dict[str, Any]],
    latitude: float,
    longitude: float,
    nearest_rows: Optional[Sequence[Dict[str, Any]]] = None,
    limit: int = 12,
    max_distance_km: float = 1200.0,
) -> Dict[str, Any]:
    candidates = crossing_candidates_for_point(
        lines,
        latitude,
        longitude,
        nearest_rows=nearest_rows,
        limit=max(limit * 2, 24),
        max_distance_km=max_distance_km,
    )
    exact_crossings = [item for item in candidates if str(item.get("kind") or "") == "crossing"]
    blends = [item for item in candidates if str(item.get("kind") or "") != "crossing"]
    lead = exact_crossings[0] if exact_crossings else (blends[0] if blends else None)

    if lead and str(lead.get("kind") or "") == "crossing":
        headline = (
            f"{lead.get('label')} is the clearest nearby intersection field. "
            f"It concentrates two line themes in the same region."
        )
    elif lead:
        headline = (
            f"{lead.get('label')} forms the closest blended convergence here. "
            f"The lines do not cross exactly nearby, but they still reinforce the same zone."
        )
    else:
        headline = "No strong nearby intersections were found for the current line set."

    geometry_points = [
        {
            "id": item.get("id"),
            "label": item.get("label"),
            "point": item.get("point"),
            "distance_km": item.get("distance_km"),
            "signal_score": item.get("signal_score"),
            "zone": item.get("zone"),
        }
        for item in exact_crossings
        if item.get("point")
    ][: max(1, int(limit))]

    return {
        "headline": headline,
        "lead_intersection": lead,
        "exact_count": len(exact_crossings),
        "blend_count": len(blends),
        "max_distance_km": round(float(max_distance_km), 1),
        "primary_crossings": exact_crossings[: max(1, int(limit))],
        "blend_candidates": blends[: max(1, int(limit // 2 or 1))],
        "geometry_points": geometry_points,
    }


def build_delineation_report(
    *,
    target_label: str,
    natal_reading: Dict[str, Any],
    natal_intersections: Dict[str, Any],
    natal_parans: Optional[Dict[str, Any]] = None,
    natal_local_space: Dict[str, Any],
    relocation_summary: Optional[Dict[str, Any]] = None,
    goal_evaluation: Optional[Dict[str, Any]] = None,
    transit_reading: Optional[Dict[str, Any]] = None,
    transit_intersections: Optional[Dict[str, Any]] = None,
    transit_parans: Optional[Dict[str, Any]] = None,
    transit_local_space: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cards: List[Dict[str, Any]] = []
    sections: List[Dict[str, Any]] = []

    natal_lead = natal_reading.get("lead_line") or {}
    if natal_lead:
        cards.append(
            {
                "id": "natal-lead",
                "title": "Natal Lead Line",
                "value": str(natal_lead.get("label") or "No lead line"),
                "detail": str(natal_reading.get("headline") or ""),
                "tone": "support" if natal_lead.get("zone") != "background" else "quiet",
            }
        )
    if transit_reading and transit_reading.get("lead_line"):
        cards.append(
            {
                "id": "transit-lead",
                "title": "Transit Activation",
                "value": str((transit_reading.get("lead_line") or {}).get("label") or ""),
                "detail": str(transit_reading.get("headline") or ""),
                "tone": "activation",
            }
        )
    if natal_intersections.get("lead_intersection"):
        lead_intersection = natal_intersections.get("lead_intersection") or {}
        cards.append(
            {
                "id": "intersections",
                "title": "Lead Intersection",
                "value": str(lead_intersection.get("label") or ""),
                "detail": f"{lead_intersection.get('distance_km')} km away",
                "tone": "support",
            }
        )
    if (natal_parans or {}).get("lead_paran"):
        lead_paran = (natal_parans or {}).get("lead_paran") or {}
        cards.append(
            {
                "id": "paran",
                "title": "Lead Paran",
                "value": str(lead_paran.get("label") or ""),
                "detail": f"{lead_paran.get('distance_km')} km away | orb {lead_paran.get('orb_deg')} deg",
                "tone": "activation",
            }
        )
    if goal_evaluation:
        cards.append(
            {
                "id": "goal-score",
                "title": "PathFinder Score",
                "value": str(goal_evaluation.get("score") or 0),
                "detail": str(((goal_evaluation.get("goal") or {}).get("label")) or ""),
                "tone": "goal",
            }
        )

    climate_items = []
    if natal_reading.get("headline"):
        climate_items.append(
            {
                "title": "Natal baseline",
                "body": natal_reading.get("headline"),
                "tone": "support",
            }
        )
    if natal_reading.get("support_note"):
        climate_items.append(
            {
                "title": "Support note",
                "body": natal_reading.get("support_note"),
                "tone": "neutral",
            }
        )
    if transit_reading and transit_reading.get("headline"):
        climate_items.append(
            {
                "title": "Transit overlay",
                "body": transit_reading.get("headline"),
                "tone": "activation",
            }
        )
    sections.append(
        {
            "id": "climate",
            "title": "Location Climate",
            "summary": f"How {target_label} reads before any goal-specific weighting.",
            "items": climate_items,
        }
    )

    intersection_items = [
        {
            "title": str(item.get("label") or ""),
            "body": f"{item.get('distance_km')} km away | {item.get('kind')}",
            "tone": "support" if str(item.get("kind") or "") == "crossing" else "neutral",
        }
        for item in (natal_intersections.get("primary_crossings") or [])[:4]
    ]
    if transit_intersections and transit_intersections.get("primary_crossings"):
        first = (transit_intersections.get("primary_crossings") or [])[0]
        if first:
            intersection_items.append(
                {
                    "title": "Transit convergence",
                    "body": f"{first.get('label')} | {first.get('distance_km')} km away",
                    "tone": "activation",
                }
            )
    sections.append(
        {
            "id": "intersections",
            "title": "Intersections",
            "summary": str(natal_intersections.get("headline") or ""),
            "items": intersection_items,
        }
    )

    paran_items = [
        {
            "title": str(item.get("label") or ""),
            "body": f"{item.get('distance_km')} km away | orb {item.get('orb_deg')} deg",
            "tone": "activation",
        }
        for item in ((natal_parans or {}).get("items") or [])[:4]
    ]
    if transit_parans and transit_parans.get("lead_paran"):
        lead_paran = transit_parans.get("lead_paran") or {}
        paran_items.append(
            {
                "title": "Transit paran",
                "body": f"{lead_paran.get('label')} | {lead_paran.get('distance_km')} km away",
                "tone": "activation",
            }
        )
    sections.append(
        {
            "id": "parans",
            "title": "Parans",
            "summary": str((natal_parans or {}).get("headline") or "No paran notes available."),
            "items": paran_items,
        }
    )

    local_space_items = [
        {
            "title": str(ray.get("label") or ""),
            "body": (
                f"{ray.get('direction_label')} | azimuth {ray.get('azimuth_deg')} deg | "
                f"altitude {ray.get('altitude_deg')} deg"
            ),
            "tone": "support" if ray.get("above_horizon") else "quiet",
        }
        for ray in (natal_local_space.get("rays") or [])
        if ray.get("above_horizon")
    ][:4]
    if transit_local_space and transit_local_space.get("rays"):
        transit_visible = [ray for ray in (transit_local_space.get("rays") or []) if ray.get("above_horizon")]
        if transit_visible:
            lead_ray = transit_visible[0]
            local_space_items.append(
                {
                    "title": "Transit directional emphasis",
                    "body": f"{lead_ray.get('label')} toward {lead_ray.get('direction_label')}",
                    "tone": "activation",
                }
            )
    sections.append(
        {
            "id": "local-space",
            "title": "Local Space",
            "summary": str(natal_local_space.get("headline") or ""),
            "items": local_space_items,
        }
    )

    relocation_items: List[Dict[str, Any]] = []
    metrics = (relocation_summary or {}).get("metrics") or {}
    angular_planets = (relocation_summary or {}).get("angular_planets") or []
    if angular_planets:
        relocation_items.append(
            {
                "title": "Angular planets",
                "body": ", ".join(
                    f"{item.get('planet')} {item.get('angle')}" for item in angular_planets[:6]
                ),
                "tone": "support",
            }
        )
    for metric_name in ("home_base", "community", "career_status", "beliefs", "chemistry"):
        value = float(metrics.get(metric_name) or 0.0)
        if value <= 0.0:
            continue
        relocation_items.append(
            {
                "title": metric_name.replace("_", " ").title(),
                "body": f"Relocation metric {round(value * 100.0)} / 100",
                "tone": "support" if value >= 0.5 else "neutral",
            }
        )
    if not relocation_items:
        relocation_items.append(
            {
                "title": "Relocation chart",
                "body": "The relocated chart does not yet show a strong angular or house emphasis.",
                "tone": "quiet",
            }
        )
    sections.append(
        {
            "id": "relocation",
            "title": "Relocation Layer",
            "summary": str((relocation_summary or {}).get("headline") or "How the relocated chart reshapes this city."),
            "items": relocation_items,
        }
    )

    goal_items: List[Dict[str, Any]] = []
    if goal_evaluation:
        for item in (goal_evaluation.get("top_supports") or [])[:3]:
            goal_items.append(
                {
                    "title": str(item.get("label") or item.get("metric") or "Support"),
                    "body": str(item.get("rationale") or ""),
                    "tone": "support",
                }
            )
        for item in (goal_evaluation.get("top_cautions") or [])[:2]:
            goal_items.append(
                {
                    "title": str(item.get("label") or item.get("metric") or "Caution"),
                    "body": str(item.get("rationale") or ""),
                    "tone": "caution",
                }
            )
    sections.append(
        {
            "id": "goal",
            "title": "PathFinder Fit",
            "summary": (
                f"Weighted for {((goal_evaluation or {}).get('goal') or {}).get('label')}."
                if goal_evaluation
                else "No PathFinder goal is active. This remains a general delineation."
            ),
            "items": goal_items,
        }
    )

    headline = (
        f"{target_label} is led by {natal_lead.get('label')}."
        if natal_lead
        else f"{target_label} is relatively quiet in the active line set."
    )
    if goal_evaluation and goal_evaluation.get("score") is not None:
        headline += f" Current PathFinder score: {goal_evaluation.get('score')}."

    return {
        "headline": headline,
        "cards": cards,
        "sections": sections,
    }
