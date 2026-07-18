from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from asteroids import _resolve_ephemeris_path as _resolve_astrocartography_ephemeris_path
from astrocartography_assets import get_angle_reference, get_body_reference, get_range_policy
from swisseph_state import swisseph as swe, swisseph_ephemeris_path, swisseph_lock


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
    "Chiron",
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
    "Chiron": getattr(swe, "CHIRON", 15) if swe else 15,
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
    "Chiron": "#8b5cf6",
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
    "Chiron": 11,
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

_EARTH_MEAN_RADIUS_KM = 6371.0088
_SPHERICAL_GEOMETRY_MODEL = "spherical-great-circle-half-arc-v1"
_DISPLAY_MAX_ARC_STEP_DEG = 12.0
_DISPLAY_MAX_CHORD_ERROR_KM = 2.0
_DISPLAY_MAX_RECURSION = 14
_DISPLAY_POLE_LATITUDE_DEG = 89.999
_GEOMETRY_TOLERANCE = 1e-10

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
    return out


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


def _clamp_unit(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _vector_dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(float(left[index]) * float(right[index]) for index in range(3))


def _vector_cross(left: Sequence[float], right: Sequence[float]) -> Tuple[float, float, float]:
    return (
        (float(left[1]) * float(right[2])) - (float(left[2]) * float(right[1])),
        (float(left[2]) * float(right[0])) - (float(left[0]) * float(right[2])),
        (float(left[0]) * float(right[1])) - (float(left[1]) * float(right[0])),
    )


def _vector_norm(vector: Sequence[float]) -> float:
    return math.sqrt(max(0.0, _vector_dot(vector, vector)))


def _normalize_vector(vector: Sequence[float]) -> Optional[Tuple[float, float, float]]:
    if not isinstance(vector, (list, tuple)) or len(vector) < 3:
        return None
    magnitude = _vector_norm(vector)
    if magnitude <= _GEOMETRY_TOLERANCE:
        return None
    return (
        float(vector[0]) / magnitude,
        float(vector[1]) / magnitude,
        float(vector[2]) / magnitude,
    )


def _latlon_to_unit(latitude_deg: float, longitude_deg: float) -> Tuple[float, float, float]:
    latitude = math.radians(float(latitude_deg))
    longitude = math.radians(float(longitude_deg))
    cos_latitude = math.cos(latitude)
    return (
        cos_latitude * math.cos(longitude),
        cos_latitude * math.sin(longitude),
        math.sin(latitude),
    )


def _unit_to_latlon(vector: Sequence[float]) -> Tuple[float, float]:
    unit = _normalize_vector(vector)
    if unit is None:
        raise ValueError("A zero vector has no geographic coordinate")
    latitude = math.degrees(math.asin(_clamp_unit(unit[2])))
    longitude = _wrap180(math.degrees(math.atan2(unit[1], unit[0])))
    return latitude, longitude


def _angular_distance_rad(left: Sequence[float], right: Sequence[float]) -> float:
    cross_norm = _vector_norm(_vector_cross(left, right))
    return math.atan2(cross_norm, _clamp_unit(_vector_dot(left, right)))


def _great_circle_distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    point_a = _latlon_to_unit(latitude_a, longitude_a)
    point_b = _latlon_to_unit(latitude_b, longitude_b)
    return _EARTH_MEAN_RADIUS_KM * _angular_distance_rad(point_a, point_b)


# Low-precision Chiron fallback when Swiss Ephemeris asteroid files are absent.
# Elements: NASA/JPL SBDB API, solution 171, epoch JD 2461200.5, J2000 equinox.
_CHIRON_JPL_ELEMENTS = {
    "epoch_jd": 2461200.5,
    "a_au": 13.68426760850124,
    "e": 0.3797656311453571,
    "i_deg": 6.930574468846328,
    "node_deg": 209.2961258613147,
    "peri_deg": 339.2878326589729,
    "mean_anomaly_deg": 216.7198966018106,
    "mean_motion_deg_per_day": 0.0194702593257484,
}


def _solve_kepler_ellipse(mean_anomaly_rad: float, eccentricity: float) -> float:
    eccentric_anomaly = float(mean_anomaly_rad)
    for _ in range(12):
        delta = (
            eccentric_anomaly
            - (float(eccentricity) * math.sin(eccentric_anomaly))
            - float(mean_anomaly_rad)
        ) / max(1e-12, 1.0 - (float(eccentricity) * math.cos(eccentric_anomaly)))
        eccentric_anomaly -= delta
        if abs(delta) < 1e-12:
            break
    return eccentric_anomaly


def _heliocentric_ecliptic_xyz_from_elements(jd_ut: float, elements: Dict[str, float]) -> Tuple[float, float, float]:
    eccentricity = float(elements["e"])
    semi_major_axis = float(elements["a_au"])
    mean_anomaly_deg = _wrap360(
        float(elements["mean_anomaly_deg"])
        + (float(elements["mean_motion_deg_per_day"]) * (float(jd_ut) - float(elements["epoch_jd"])))
    )
    eccentric_anomaly = _solve_kepler_ellipse(math.radians(mean_anomaly_deg), eccentricity)
    xv = semi_major_axis * (math.cos(eccentric_anomaly) - eccentricity)
    yv = semi_major_axis * math.sqrt(max(0.0, 1.0 - (eccentricity * eccentricity))) * math.sin(eccentric_anomaly)
    true_anomaly = math.atan2(yv, xv)
    radius = math.hypot(xv, yv)

    node = math.radians(float(elements["node_deg"]))
    peri = math.radians(float(elements["peri_deg"]))
    incl = math.radians(float(elements["i_deg"]))
    argument = true_anomaly + peri

    xh = radius * ((math.cos(node) * math.cos(argument)) - (math.sin(node) * math.sin(argument) * math.cos(incl)))
    yh = radius * ((math.sin(node) * math.cos(argument)) + (math.cos(node) * math.sin(argument) * math.cos(incl)))
    zh = radius * (math.sin(argument) * math.sin(incl))
    return xh, yh, zh


def _spherical_ecliptic_to_xyz(lon_deg: float, lat_deg: float, radius: float) -> Tuple[float, float, float]:
    lon = math.radians(float(lon_deg))
    lat = math.radians(float(lat_deg))
    r = float(radius)
    cos_lat = math.cos(lat)
    return (
        r * cos_lat * math.cos(lon),
        r * cos_lat * math.sin(lon),
        r * math.sin(lat),
    )


def _mean_obliquity_deg(jd_ut: float) -> float:
    centuries = (float(jd_ut) - 2451545.0) / 36525.0
    return 23.439291111 - (0.013004167 * centuries) - (0.000000164 * centuries * centuries) + (0.000000504 * centuries * centuries * centuries)


def _fallback_chiron_geocentric_ecliptic_xyz(jd_ut: float) -> Optional[Tuple[float, float, float]]:
    if swe is None:
        return None
    sun_flags = getattr(swe, "FLG_SWIEPH", getattr(swe, "SEFLG_SWIEPH", 2))
    try:
        sun_pos, _ = swe.calc_ut(jd_ut, getattr(swe, "SUN", 0), sun_flags)  # type: ignore[arg-type]
    except Exception:
        try:
            sun_pos, _ = swe.calc_ut(jd_ut, getattr(swe, "SUN", 0), getattr(swe, "FLG_MOSEPH", 4))  # type: ignore[arg-type]
        except Exception:
            return None

    chiron_x, chiron_y, chiron_z = _heliocentric_ecliptic_xyz_from_elements(jd_ut, _CHIRON_JPL_ELEMENTS)
    sun_x, sun_y, sun_z = _spherical_ecliptic_to_xyz(
        float(sun_pos[0]),
        float(sun_pos[1]) if len(sun_pos) > 1 else 0.0,
        float(sun_pos[2]) if len(sun_pos) > 2 else 1.0,
    )
    return chiron_x + sun_x, chiron_y + sun_y, chiron_z + sun_z


def fallback_chiron_ecliptic_position(jd_ut: float) -> Optional[Dict[str, float]]:
    """Return a low-precision geocentric Chiron ecliptic position.

    This is intentionally shared by line generation and relocated chart
    augmentation so PathFinder can score Chiron models even when the local
    Swiss Ephemeris asteroid files are not installed.
    """
    vector = _fallback_chiron_geocentric_ecliptic_xyz(jd_ut)
    if vector is None:
        return None
    geo_x, geo_y, geo_z = vector
    lon_deg = _wrap360(math.degrees(math.atan2(geo_y, geo_x)))
    lat_deg = math.degrees(math.atan2(geo_z, math.hypot(geo_x, geo_y)))
    speed = 0.0
    next_vector = _fallback_chiron_geocentric_ecliptic_xyz(float(jd_ut) + 1.0)
    if next_vector is not None:
        next_lon = _wrap360(math.degrees(math.atan2(next_vector[1], next_vector[0])))
        speed = _wrap180(next_lon - lon_deg)
    return {
        "longitude": lon_deg,
        "latitude": lat_deg,
        "speed": speed,
    }


def _fallback_chiron_equatorial_position(jd_ut: float) -> Optional[Tuple[float, float]]:
    vector = _fallback_chiron_geocentric_ecliptic_xyz(jd_ut)
    if vector is None:
        return None
    geo_x, geo_y, geo_z = vector
    obliquity = math.radians(_mean_obliquity_deg(jd_ut))
    eq_x = geo_x
    eq_y = (geo_y * math.cos(obliquity)) - (geo_z * math.sin(obliquity))
    eq_z = (geo_y * math.sin(obliquity)) + (geo_z * math.cos(obliquity))
    ra_deg = _wrap360(math.degrees(math.atan2(eq_y, eq_x)))
    dec_deg = math.degrees(math.atan2(eq_z, math.hypot(eq_x, eq_y)))
    return ra_deg, dec_deg


def _ephemeris_engine_from_flags(returned_flags: int) -> str:
    if swe is None:
        return "unavailable"
    if int(returned_flags) & int(getattr(swe, "FLG_JPLEPH", getattr(swe, "SEFLG_JPLEPH", 1))):
        return "jpl"
    if int(returned_flags) & int(getattr(swe, "FLG_SWIEPH", getattr(swe, "SEFLG_SWIEPH", 2))):
        return "swiss-ephemeris"
    if int(returned_flags) & int(getattr(swe, "FLG_MOSEPH", getattr(swe, "SEFLG_MOSEPH", 4))):
        return "moshier"
    return "unknown"


def _equatorial_positions(timestamp_iso: str, bodies: Sequence[str]) -> Tuple[float, List[Dict[str, Any]]]:
    _require_swe()
    jd_ut = _jd_ut_from_iso(timestamp_iso)
    flags = (
        getattr(swe, "FLG_SWIEPH", getattr(swe, "SEFLG_SWIEPH", 2))
        | getattr(swe, "FLG_EQUATORIAL", getattr(swe, "SEFLG_EQUATORIAL", 2048))
    )
    positions: List[Dict[str, Any]] = []
    ephemeris_path = _resolve_astrocartography_ephemeris_path() or ""
    with swisseph_ephemeris_path(ephemeris_path, swe_module=swe):
        with swisseph_lock():
            gst_deg = _wrap360(float(swe.sidtime(jd_ut)) * 15.0)  # type: ignore[arg-type]
            for body in bodies:
                planet_id = PLANET_IDS.get(body)
                if planet_id is None:
                    continue
                calculation: Dict[str, Any]
                try:
                    pos, returned_flags = swe.calc_ut(jd_ut, planet_id, flags)  # type: ignore[arg-type]
                    ra_deg = _wrap360(float(pos[0]))
                    dec_deg = float(pos[1])
                    engine = _ephemeris_engine_from_flags(int(returned_flags))
                    calculation = {
                        "position_source": engine,
                        "ephemeris_engine": engine,
                        "returned_flags": int(returned_flags),
                        "degraded": False,
                        "accuracy": "ephemeris",
                        "ranking_eligible": True,
                    }
                    if body == "Chiron" and ephemeris_path:
                        calculation["orbital_data_source"] = "swiss-ephemeris-asteroid-file"
                except Exception:
                    fallback_position = _fallback_chiron_equatorial_position(jd_ut) if body == "Chiron" else None
                    if fallback_position is None:
                        raise
                    ra_deg, dec_deg = fallback_position
                    calculation = {
                        "position_source": "jpl-elements-two-body-fallback",
                        "ephemeris_engine": "analytic-fallback",
                        "returned_flags": None,
                        "degraded": True,
                        "accuracy": "low",
                        "ranking_eligible": False,
                        "degraded_reason": "Bundled Swiss Ephemeris asteroid position was unavailable.",
                        "fallback_epoch_jd": _CHIRON_JPL_ELEMENTS["epoch_jd"],
                        "fallback_frame": "J2000 osculating elements; qualitative fallback only",
                    }
                positions.append(
                    {
                        "body": body,
                        "ra_deg": ra_deg,
                        "dec_deg": dec_deg,
                        "calculation": calculation,
                    }
                )
    return gst_deg, positions


def _build_line_geometry(
    ra_deg: float,
    dec_deg: float,
    gst_deg: float,
    angle: str,
) -> Optional[Dict[str, Any]]:
    """Build an exact spherical half-great-circle representation.

    ``midpoint`` identifies the requested half of the great circle: a point is
    on the closed half arc when it lies in the plane and its dot product with
    the midpoint is non-negative. ``axis`` joins the two arc endpoints and is
    oriented northward where the geometry permits.
    """

    angle_name = str(angle or "").upper()
    if angle_name not in ANGLE_META:
        return None

    substellar_longitude_deg = _wrap180(float(ra_deg) - float(gst_deg))
    substellar_longitude = math.radians(substellar_longitude_deg)
    declination = math.radians(float(dec_deg))
    body_vector = (
        math.cos(declination) * math.cos(substellar_longitude),
        math.cos(declination) * math.sin(substellar_longitude),
        math.sin(declination),
    )
    meridian_normal = (
        -math.sin(substellar_longitude),
        math.cos(substellar_longitude),
        0.0,
    )
    meridian_midpoint = (
        math.cos(substellar_longitude),
        math.sin(substellar_longitude),
        0.0,
    )

    if angle_name == "MC":
        normal = meridian_normal
        midpoint = meridian_midpoint
    elif angle_name == "IC":
        normal = meridian_normal
        midpoint = tuple(-value for value in meridian_midpoint)
    elif angle_name == "ASC":
        normal = body_vector
        rising_longitude = substellar_longitude - (math.pi / 2.0)
        midpoint = (math.cos(rising_longitude), math.sin(rising_longitude), 0.0)
    else:
        normal = body_vector
        setting_longitude = substellar_longitude + (math.pi / 2.0)
        midpoint = (math.cos(setting_longitude), math.sin(setting_longitude), 0.0)

    normal_unit = _normalize_vector(normal)
    midpoint_unit = _normalize_vector(midpoint)
    if normal_unit is None or midpoint_unit is None:
        return None
    axis = _normalize_vector(_vector_cross(normal_unit, midpoint_unit))
    if axis is None:
        return None
    if (
        axis[2] < -_GEOMETRY_TOLERANCE
        or (
            abs(axis[2]) <= _GEOMETRY_TOLERANCE
            and (axis[1] < -_GEOMETRY_TOLERANCE or (abs(axis[1]) <= _GEOMETRY_TOLERANCE and axis[0] < 0.0))
        )
    ):
        axis = tuple(-value for value in axis)

    south_endpoint = _unit_to_latlon(tuple(-value for value in axis))
    north_endpoint = _unit_to_latlon(axis)
    return {
        "model": _SPHERICAL_GEOMETRY_MODEL,
        "angle": angle_name,
        "normal": [float(value) for value in normal_unit],
        "midpoint": [float(value) for value in midpoint_unit],
        "axis": [float(value) for value in axis],
        "endpoints": [
            [float(south_endpoint[0]), float(south_endpoint[1])],
            [float(north_endpoint[0]), float(north_endpoint[1])],
        ],
        "ra_deg": float(ra_deg),
        "dec_deg": float(dec_deg),
        "gst_deg": float(gst_deg),
        "substellar_longitude_deg": float(substellar_longitude_deg),
    }


def _geometry_vectors(
    geometry: Dict[str, Any],
) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]]:
    if str(geometry.get("model") or "") != _SPHERICAL_GEOMETRY_MODEL:
        return None
    normal = _normalize_vector(geometry.get("normal") or [])
    midpoint = _normalize_vector(geometry.get("midpoint") or [])
    axis = _normalize_vector(geometry.get("axis") or [])
    if normal is None or midpoint is None or axis is None:
        return None
    return normal, midpoint, axis


def _arc_vector_at_parameter(geometry: Dict[str, Any], parameter_rad: float) -> Tuple[float, float, float]:
    vectors = _geometry_vectors(geometry)
    if vectors is None:
        raise ValueError("Invalid spherical line geometry")
    _, midpoint, axis = vectors
    return (
        (math.cos(parameter_rad) * midpoint[0]) + (math.sin(parameter_rad) * axis[0]),
        (math.cos(parameter_rad) * midpoint[1]) + (math.sin(parameter_rad) * axis[1]),
        (math.cos(parameter_rad) * midpoint[2]) + (math.sin(parameter_rad) * axis[2]),
    )


def _display_parameter_bounds(geometry: Dict[str, Any]) -> Tuple[float, float]:
    vectors = _geometry_vectors(geometry)
    if vectors is None:
        return -(math.pi / 2.0), math.pi / 2.0
    _, _, axis = vectors
    if abs(axis[2]) >= 1.0 - 1e-12:
        inset = math.radians(90.0 - _DISPLAY_POLE_LATITUDE_DEG)
        return -(math.pi / 2.0) + inset, (math.pi / 2.0) - inset
    return -(math.pi / 2.0), math.pi / 2.0


def _adaptive_arc_parameters(geometry: Dict[str, Any]) -> List[float]:
    start, end = _display_parameter_bounds(geometry)
    cache: Dict[float, Tuple[float, float]] = {}

    def _point(parameter: float) -> Tuple[float, float]:
        cached = cache.get(parameter)
        if cached is None:
            cached = _unit_to_latlon(_arc_vector_at_parameter(geometry, parameter))
            cache[parameter] = cached
        return cached

    parameters: List[float] = [start]

    def _subdivide(left: float, right: float, depth: int) -> None:
        midpoint_parameter = (left + right) / 2.0
        left_point = _point(left)
        right_point = _point(right)
        midpoint_point = _point(midpoint_parameter)
        right_longitude = _longitude_near_reference(right_point[1], left_point[1])
        linear_longitude = (left_point[1] + right_longitude) / 2.0
        midpoint_longitude = _longitude_near_reference(midpoint_point[1], linear_longitude)
        linear_latitude = (left_point[0] + right_point[0]) / 2.0
        chord_error_km = _great_circle_distance_km(
            midpoint_point[0],
            midpoint_longitude,
            linear_latitude,
            linear_longitude,
        )
        arc_step_deg = math.degrees(right - left)
        if depth < _DISPLAY_MAX_RECURSION and (
            arc_step_deg > _DISPLAY_MAX_ARC_STEP_DEG
            or chord_error_km > _DISPLAY_MAX_CHORD_ERROR_KM
        ):
            _subdivide(left, midpoint_parameter, depth + 1)
            _subdivide(midpoint_parameter, right, depth + 1)
            return
        parameters.append(right)

    _subdivide(start, end, 0)
    return parameters


def _seam_parameter(
    geometry: Dict[str, Any],
    left_parameter: float,
    right_parameter: float,
    boundary_longitude: float,
) -> float:
    left = float(left_parameter)
    right = float(right_parameter)

    def _offset(parameter: float) -> float:
        _, raw_longitude = _unit_to_latlon(_arc_vector_at_parameter(geometry, parameter))
        return _longitude_near_reference(raw_longitude, boundary_longitude) - boundary_longitude

    left_offset = _offset(left)
    right_offset = _offset(right)
    for _ in range(60):
        midpoint = (left + right) / 2.0
        midpoint_offset = _offset(midpoint)
        if abs(midpoint_offset) < 1e-12:
            return midpoint
        if (left_offset <= 0.0 <= midpoint_offset) or (left_offset >= 0.0 >= midpoint_offset):
            right = midpoint
            right_offset = midpoint_offset
        else:
            left = midpoint
            left_offset = midpoint_offset
    return (left + right) / 2.0


def _display_segments_for_geometry(geometry: Dict[str, Any]) -> List[List[List[float]]]:
    parameters = _adaptive_arc_parameters(geometry)
    continuous: List[Tuple[float, float, float]] = []
    prior_longitude: Optional[float] = None
    for parameter in parameters:
        latitude, longitude = _unit_to_latlon(_arc_vector_at_parameter(geometry, parameter))
        if prior_longitude is not None:
            longitude = _longitude_near_reference(longitude, prior_longitude)
        continuous.append((parameter, latitude, longitude))
        prior_longitude = longitude

    if not continuous:
        return []

    segments: List[List[List[float]]] = []
    current: List[List[float]] = [
        [round(float(continuous[0][1]), 6), round(float(_wrap180(continuous[0][2])), 6)]
    ]
    for index in range(1, len(continuous)):
        left_parameter, _, left_longitude = continuous[index - 1]
        right_parameter, right_latitude, right_longitude = continuous[index]
        low = min(left_longitude, right_longitude)
        high = max(left_longitude, right_longitude)
        boundaries = []
        first_index = int(math.floor((low - 180.0) / 360.0)) - 1
        last_index = int(math.ceil((high - 180.0) / 360.0)) + 1
        for boundary_index in range(first_index, last_index + 1):
            boundary = 180.0 + (360.0 * boundary_index)
            if low + 1e-10 < boundary < high - 1e-10:
                boundaries.append(boundary)
        if right_longitude < left_longitude:
            boundaries.reverse()

        for boundary in boundaries:
            crossing_parameter = _seam_parameter(
                geometry,
                left_parameter,
                right_parameter,
                boundary,
            )
            crossing_latitude, _ = _unit_to_latlon(
                _arc_vector_at_parameter(geometry, crossing_parameter)
            )
            old_seam = 180.0 if right_longitude > left_longitude else -180.0
            new_seam = -old_seam
            seam_point = [round(float(crossing_latitude), 6), old_seam]
            if not current or current[-1] != seam_point:
                current.append(seam_point)
            if len(current) >= 2:
                segments.append(current)
            current = [[round(float(crossing_latitude), 6), new_seam]]

        next_point = [
            round(float(right_latitude), 6),
            round(float(_wrap180(right_longitude)), 6),
        ]
        if not current or current[-1] != next_point:
            current.append(next_point)
    if len(current) >= 2:
        segments.append(current)
    return segments


def _line_segments_for_angle(
    ra_deg: float,
    dec_deg: float,
    gst_deg: float,
    angle: str,
) -> List[List[List[float]]]:
    geometry = _build_line_geometry(ra_deg, dec_deg, gst_deg, angle)
    if geometry is None:
        return []
    return _display_segments_for_geometry(geometry)


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
            geometry = _build_line_geometry(item["ra_deg"], item["dec_deg"], gst_deg, angle)
            if geometry is None:
                continue
            segments = _display_segments_for_geometry(geometry)
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
                    "geometry": geometry,
                    "calculation": dict(item.get("calculation") or {}),
                }
            )
    calculation_by_body = {
        str(item.get("body") or ""): dict(item.get("calculation") or {})
        for item in positions
        if item.get("body")
    }
    return {
        "timestamp": timestamp_iso,
        "gst_deg": round(gst_deg, 6),
        "bodies": normalized_bodies,
        "angles": normalized_angles,
        "lines": lines,
        "calculation": {
            "geometry_model": _SPHERICAL_GEOMETRY_MODEL,
            "coordinate_frame": "apparent geocentric equator and equinox of date",
            "geographic_model": "mean-radius sphere",
            "earth_radius_km": _EARTH_MEAN_RADIUS_KM,
            "degraded": any(bool(item.get("degraded")) for item in calculation_by_body.values()),
            "bodies": calculation_by_body,
        },
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
                "calculation": dict(item.get("calculation") or {}),
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


def _longitude_near_reference(longitude_deg: float, reference_deg: float) -> float:
    longitude = float(longitude_deg)
    reference = float(reference_deg)
    while longitude - reference > 180.0:
        longitude -= 360.0
    while longitude - reference < -180.0:
        longitude += 360.0
    return longitude


def _point_segment_distance_km(
    point_lat: float,
    point_lon: float,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> float:
    point = _latlon_to_unit(point_lat, point_lon)
    start = _latlon_to_unit(start_lat, start_lon)
    end = _latlon_to_unit(end_lat, end_lon)
    segment_length = _angular_distance_rad(start, end)
    if segment_length <= _GEOMETRY_TOLERANCE:
        return _EARTH_MEAN_RADIUS_KM * _angular_distance_rad(point, start)

    normal = _normalize_vector(_vector_cross(start, end))
    candidates: List[Tuple[float, float, float]] = [start, end]
    if normal is not None and segment_length < math.pi - 1e-9:
        projection = _normalize_vector(
            tuple(
                point[index] - (_vector_dot(point, normal) * normal[index])
                for index in range(3)
            )
        )
        if projection is not None:
            for candidate in (projection, tuple(-value for value in projection)):
                start_to_candidate = _angular_distance_rad(start, candidate)
                candidate_to_end = _angular_distance_rad(candidate, end)
                if abs((start_to_candidate + candidate_to_end) - segment_length) <= 1e-8:
                    candidates.append(candidate)

    return _EARTH_MEAN_RADIUS_KM * min(
        _angular_distance_rad(point, candidate)
        for candidate in candidates
    )


def _point_half_arc_distance_km(
    latitude: float,
    longitude: float,
    geometry: Dict[str, Any],
) -> Optional[float]:
    vectors = _geometry_vectors(geometry)
    if vectors is None:
        return None
    normal, midpoint, axis = vectors
    point = _latlon_to_unit(latitude, longitude)
    candidates: List[Tuple[float, float, float]] = [
        axis,
        tuple(-value for value in axis),
    ]
    projection = _normalize_vector(
        tuple(
            point[index] - (_vector_dot(point, normal) * normal[index])
            for index in range(3)
        )
    )
    if projection is not None and _vector_dot(projection, midpoint) >= -_GEOMETRY_TOLERANCE:
        candidates.append(projection)
    return _EARTH_MEAN_RADIUS_KM * min(
        _angular_distance_rad(point, candidate)
        for candidate in candidates
    )


def nearest_lines_for_point(
    lines: Sequence[Dict[str, Any]],
    latitude: float,
    longitude: float,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    for line in lines:
        best_distance = _point_half_arc_distance_km(
            latitude,
            longitude,
            line.get("geometry") or {},
        )
        if best_distance is None:
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
                "geometry_model": (line.get("geometry") or {}).get("model"),
                "calculation": dict(line.get("calculation") or {}),
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
    start_a = _latlon_to_unit(float(a1[0]), float(a1[1]))
    end_a = _latlon_to_unit(float(a2[0]), float(a2[1]))
    start_b = _latlon_to_unit(float(b1[0]), float(b1[1]))
    end_b = _latlon_to_unit(float(b2[0]), float(b2[1]))
    length_a = _angular_distance_rad(start_a, end_a)
    length_b = _angular_distance_rad(start_b, end_b)
    if length_a <= _GEOMETRY_TOLERANCE or length_b <= _GEOMETRY_TOLERANCE:
        return None
    normal_a = _normalize_vector(_vector_cross(start_a, end_a))
    normal_b = _normalize_vector(_vector_cross(start_b, end_b))
    if normal_a is None or normal_b is None:
        return None
    crossing = _normalize_vector(_vector_cross(normal_a, normal_b))
    if crossing is None:
        return None

    def _on_segment(
        candidate: Sequence[float],
        start: Sequence[float],
        end: Sequence[float],
        length: float,
    ) -> bool:
        return abs(
            _angular_distance_rad(start, candidate)
            + _angular_distance_rad(candidate, end)
            - length
        ) <= 1e-8

    candidates: List[Tuple[float, float]] = []
    for candidate in (crossing, tuple(-value for value in crossing)):
        if _on_segment(candidate, start_a, end_a, length_a) and _on_segment(
            candidate,
            start_b,
            end_b,
            length_b,
        ):
            candidates.append(_unit_to_latlon(candidate))
    if not candidates:
        return None
    candidates.sort(key=lambda point: (abs(point[0]), point[0], point[1]))
    return candidates[0]


def _point_distance_km(point_a: Sequence[float], point_b: Sequence[float]) -> float:
    return _great_circle_distance_km(
        float(point_a[0]),
        float(point_a[1]),
        float(point_b[0]),
        float(point_b[1]),
    )


def _angular_separation_deg(a_deg: float, b_deg: float) -> float:
    diff = abs(_wrap180(float(a_deg) - float(b_deg)))
    return min(diff, 360.0 - diff)


def _half_arc_intersections(
    geometry_a: Dict[str, Any],
    geometry_b: Dict[str, Any],
) -> List[Tuple[float, float]]:
    vectors_a = _geometry_vectors(geometry_a)
    vectors_b = _geometry_vectors(geometry_b)
    if vectors_a is None or vectors_b is None:
        return []
    normal_a, midpoint_a, _ = vectors_a
    normal_b, midpoint_b, _ = vectors_b
    crossing = _normalize_vector(_vector_cross(normal_a, normal_b))
    if crossing is None:
        return []

    points: List[Tuple[float, float]] = []
    for candidate in (crossing, tuple(-value for value in crossing)):
        if (
            _vector_dot(candidate, midpoint_a) >= -_GEOMETRY_TOLERANCE
            and _vector_dot(candidate, midpoint_b) >= -_GEOMETRY_TOLERANCE
        ):
            point = _unit_to_latlon(candidate)
            # Geographic longitude, and therefore MC/IC/ASC/DSC identity, is
            # undefined at the exact poles. Do not manufacture polar crossings.
            if abs(point[0]) >= 90.0 - 1e-9:
                continue
            if not any(
                _great_circle_distance_km(point[0], point[1], existing[0], existing[1]) < 1e-6
                for existing in points
            ):
                points.append(point)
    points.sort(key=lambda point: (point[0], point[1]))
    return points


def _canonical_angular_event_id(
    body_a: str,
    angle_a: str,
    body_b: str,
    angle_b: str,
) -> str:
    tokens = sorted(
        [
            f"{str(body_a)}:{str(angle_a).upper()}",
            f"{str(body_b)}:{str(angle_b).upper()}",
        ]
    )
    return f"angular-event:{tokens[0]}|{tokens[1]}"


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
    if -1.0 - 1e-10 <= cos_h0 <= 1.0 + 1e-10:
        h0_deg = math.degrees(math.acos(_clamp_unit(cos_h0)))
        events["ASC"] = _wrap360(ra_deg - h0_deg)
        events["DSC"] = _wrap360(ra_deg + h0_deg)
    return events


def _exact_paran_events(
    gst_deg: float,
    positions: Sequence[Dict[str, Any]],
    *,
    maximum_residual_deg: float,
) -> List[Dict[str, Any]]:
    ordered_positions = sorted(
        [item for item in positions if item.get("body")],
        key=lambda item: (
            PLANET_PRIORITY.get(str(item.get("body") or ""), 99),
            str(item.get("body") or ""),
        ),
    )
    exact_events: List[Dict[str, Any]] = []
    seen: set[Tuple[str, int, int]] = set()
    for index, item_a in enumerate(ordered_positions):
        body_a = str(item_a.get("body") or "")
        ra_a = float(item_a.get("ra_deg") or 0.0)
        dec_a = float(item_a.get("dec_deg") or 0.0)
        for item_b in ordered_positions[index + 1:]:
            body_b = str(item_b.get("body") or "")
            ra_b = float(item_b.get("ra_deg") or 0.0)
            dec_b = float(item_b.get("dec_deg") or 0.0)
            patterns = [
                ("ASC", "MC"),
                ("ASC", "IC"),
                ("DSC", "MC"),
                ("DSC", "IC"),
                ("MC", "ASC"),
                ("MC", "DSC"),
                ("IC", "ASC"),
                ("IC", "DSC"),
            ]
            for angle_a, angle_b in patterns:
                geometry_a = _build_line_geometry(ra_a, dec_a, gst_deg, angle_a)
                geometry_b = _build_line_geometry(ra_b, dec_b, gst_deg, angle_b)
                if geometry_a is None or geometry_b is None:
                    continue
                for point_latitude, point_longitude in _half_arc_intersections(geometry_a, geometry_b):
                    events_a = _paran_event_lsts(ra_a, dec_a, point_latitude)
                    events_b = _paran_event_lsts(ra_b, dec_b, point_latitude)
                    if angle_a not in events_a or angle_b not in events_b:
                        continue
                    actual_lst = _wrap360(float(gst_deg) + float(point_longitude))
                    pair_orb = _angular_separation_deg(events_a[angle_a], events_b[angle_b])
                    root_residual = max(
                        pair_orb,
                        _angular_separation_deg(actual_lst, events_a[angle_a]),
                        _angular_separation_deg(actual_lst, events_b[angle_b]),
                    )
                    if root_residual > max(float(maximum_residual_deg), 1e-7):
                        continue
                    canonical_event_id = _canonical_angular_event_id(
                        body_a,
                        angle_a,
                        body_b,
                        angle_b,
                    )
                    dedupe_key = (
                        canonical_event_id,
                        int(round(point_latitude * 1_000_000.0)),
                        int(round(point_longitude * 1_000_000.0)),
                    )
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    exact_events.append(
                        {
                            "canonical_event_id": canonical_event_id,
                            "body_a": body_a,
                            "angle_a": angle_a,
                            "body_b": body_b,
                            "angle_b": angle_b,
                            "latitude_deg": point_latitude,
                            "longitude_deg": point_longitude,
                            "orb_deg": pair_orb,
                            "root_residual_deg": root_residual,
                            "calculation": {
                                "body_a": dict(item_a.get("calculation") or {}),
                                "body_b": dict(item_b.get("calculation") or {}),
                            },
                        }
                    )
    exact_events.sort(
        key=lambda event: (
            float(event.get("root_residual_deg", 999999.0)),
            str(event.get("canonical_event_id") or ""),
            float(event.get("latitude_deg") or 0.0),
            float(event.get("longitude_deg") or 0.0),
        )
    )
    return exact_events


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
    candidates: List[Dict[str, Any]] = []
    exact_events = _exact_paran_events(
        gst_deg,
        positions,
        maximum_residual_deg=float(orb_deg),
    )
    for event in exact_events:
        point_latitude = float(event.get("latitude_deg") or 0.0)
        point_longitude = float(event.get("longitude_deg") or 0.0)
        distance_km = _great_circle_distance_km(
            float(latitude),
            float(longitude),
            point_latitude,
            point_longitude,
        )
        if distance_km > float(max_distance_km):
            continue
        pair_orb = float(event.get("orb_deg") or 0.0)
        root_residual = float(event.get("root_residual_deg") or 0.0)
        score_from_orb = max(0.0, 1.0 - (root_residual / max(float(orb_deg), 0.1)))
        score_from_distance = max(0.0, 1.0 - (distance_km / max(float(max_distance_km), 1.0)))
        signal_score = int(
            round(
                max(
                    0.0,
                    min(
                        100.0,
                        ((0.55 * score_from_orb) + (0.45 * score_from_distance)) * 100.0,
                    ),
                )
            )
        )
        zone = _distance_zone(
            distance_km,
            primary_radius_km=PRIMARY_READING_RADIUS_KM,
            extended_radius_km=max_distance_km,
        )
        canonical_event_id = str(event.get("canonical_event_id") or "")
        body_a = str(event.get("body_a") or "")
        angle_a = str(event.get("angle_a") or "")
        body_b = str(event.get("body_b") or "")
        angle_b = str(event.get("angle_b") or "")
        candidates.append(
            {
                "id": f"{canonical_event_id}:paran-point",
                "canonical_event_id": canonical_event_id,
                "kind": "paran",
                "event_kind": "paran-crossing-point",
                "label": f"{body_a} {angle_a} paran {body_b} {angle_b}",
                "body_a": body_a,
                "angle_a": angle_a,
                "body_b": body_b,
                "angle_b": angle_b,
                "planets": [body_a, body_b],
                "orb_deg": round(pair_orb, 6),
                "orb_minutes": round(pair_orb * 4.0, 4),
                "root_residual_deg": round(root_residual, 9),
                "distance_km": round(distance_km, 1),
                "latitude_deg": round(point_latitude, 6),
                "longitude_deg": round(point_longitude, 6),
                "point": [round(point_latitude, 6), round(point_longitude, 6)],
                "zone": zone,
                "signal_score": signal_score,
                "calculation": dict(event.get("calculation") or {}),
                "summary": (
                    f"{body_a} {angle_a} and {body_b} {angle_b} form an exact "
                    f"paran crossing near this coordinate."
                ),
            }
        )

    candidates.sort(
        key=lambda item: (
            float(item.get("distance_km", 999999.0)),
            float(item.get("root_residual_deg", 999999.0)),
            str(item.get("canonical_event_id") or ""),
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
        "orb_policy": "exact angular roots; orb_deg is the maximum accepted numerical residual",
        "max_distance_km": round(float(max_distance_km), 1),
        "calculation_mode": "analytic-spherical-root",
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
    tracks: List[Dict[str, Any]] = []
    exact_events = _exact_paran_events(
        gst_deg,
        positions,
        maximum_residual_deg=float(orb_deg),
    )
    for event in exact_events:
        canonical_event_id = str(event.get("canonical_event_id") or "")
        body_a = str(event.get("body_a") or "")
        angle_a = str(event.get("angle_a") or "")
        body_b = str(event.get("body_b") or "")
        angle_b = str(event.get("angle_b") or "")
        latitude_deg = float(event.get("latitude_deg") or 0.0)
        longitude_deg = float(event.get("longitude_deg") or 0.0)
        residual = float(event.get("root_residual_deg") or 0.0)
        tracks.append(
            {
                "id": f"{canonical_event_id}:paran-corridor",
                "canonical_event_id": canonical_event_id,
                "kind": "global-paran",
                "event_kind": "paran-latitude-corridor",
                "label": f"{body_a} {angle_a} paran {body_b} {angle_b}",
                "body_a": body_a,
                "angle_a": angle_a,
                "body_b": body_b,
                "angle_b": angle_b,
                "color": "#7c3aed",
                "dash_array": "3 8",
                "segments": [
                    [
                        [round(latitude_deg, 6), -180.0],
                        [round(latitude_deg, 6), 0.0],
                        [round(latitude_deg, 6), 180.0],
                    ]
                ],
                "root_point": [round(latitude_deg, 6), round(longitude_deg, 6)],
                "latitude_deg": round(latitude_deg, 6),
                "sample_count": 3,
                "exact_hits": 1,
                "min_orb_deg": round(float(event.get("orb_deg") or 0.0), 6),
                "root_residual_deg": round(residual, 9),
                "calculation": dict(event.get("calculation") or {}),
                "summary": (
                    f"{body_a} {angle_a} and {body_b} {angle_b} form an exact "
                    f"paran root on this latitude corridor."
                ),
            }
        )

    tracks.sort(
        key=lambda item: (
            float(item.get("root_residual_deg", 999999.0)),
            str(item.get("canonical_event_id") or ""),
            float(item.get("latitude_deg") or 0.0),
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
        "orb_policy": "exact angular roots; orb_deg is the maximum accepted numerical residual",
        "latitude_step_deg": 0,
        "calculation_mode": "analytic-spherical-root",
        "requested_min_points": int(min_points),
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
            analytic_geometry = (
                _geometry_vectors(line_a.get("geometry") or {}) is not None
                and _geometry_vectors(line_b.get("geometry") or {}) is not None
            )
            if analytic_geometry:
                for point in _half_arc_intersections(
                    line_a.get("geometry") or {},
                    line_b.get("geometry") or {},
                ):
                    distance = _great_circle_distance_km(
                        latitude,
                        longitude,
                        point[0],
                        point[1],
                    )
                    if best_distance is None or distance < best_distance:
                        best_distance = distance
                        best_point = point
            else:
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
                                distance = _great_circle_distance_km(
                                    latitude,
                                    longitude,
                                    point[0],
                                    point[1],
                                )
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

            body_a = str(row_a.get("body") or line_a.get("body") or "")
            angle_a = str(row_a.get("angle") or line_a.get("angle") or "")
            body_b = str(row_b.get("body") or line_b.get("body") or "")
            angle_b = str(row_b.get("angle") or line_b.get("angle") or "")
            canonical_event_id = _canonical_angular_event_id(
                body_a,
                angle_a,
                body_b,
                angle_b,
            )
            ordered_lines = sorted(
                [
                    (
                        str(row_a.get("id") or ""),
                        str(row_a.get("label") or ""),
                        body_a,
                    ),
                    (
                        str(row_b.get("id") or ""),
                        str(row_b.get("label") or ""),
                        body_b,
                    ),
                ],
                key=lambda item: item[0],
            )
            zone = _distance_zone(best_distance, primary_radius_km=PRIMARY_READING_RADIUS_KM, extended_radius_km=max_distance_km)
            score = _line_proximity_score(best_distance, primary_radius_km=PRIMARY_READING_RADIUS_KM, extended_radius_km=max_distance_km)
            candidates.append(
                {
                    "id": f"{canonical_event_id}:intersection",
                    "canonical_event_id": canonical_event_id,
                    "label": f"{ordered_lines[0][1]} x {ordered_lines[1][1]}",
                    "kind": kind,
                    "event_kind": (
                        "angular-line-crossing"
                        if kind == "crossing"
                        else "angular-line-proximity-blend"
                    ),
                    "planets": [ordered_lines[0][2], ordered_lines[1][2]],
                    "lines": [ordered_lines[0][0], ordered_lines[1][0]],
                    "distance_km": round(float(best_distance), 1),
                    "zone": zone,
                    "signal_score": score,
                    "point": [round(float(best_point[0]), 6), round(float(best_point[1]), 6)] if best_point else None,
                    "geometry_model": (
                        _SPHERICAL_GEOMETRY_MODEL
                        if analytic_geometry
                        else "spherical-polyline-segments"
                    ),
                    "calculation": {
                        "line_a": dict(line_a.get("calculation") or {}),
                        "line_b": dict(line_b.get("calculation") or {}),
                    },
                }
            )

    candidates.sort(
        key=lambda row: (
            float(row.get("distance_km") or 0.0),
            str(row.get("canonical_event_id") or ""),
        )
    )
    return candidates[: max(1, int(limit))]


def build_goal_scoring_context(
    lines: Sequence[Dict[str, Any]],
    latitude: float,
    longitude: float,
    *,
    primary_radius_km: float = PRIMARY_READING_RADIUS_KM,
    extended_radius_km: float = EXTENDED_READING_RADIUS_KM,
) -> Dict[str, Any]:
    """Build untruncated line and crossing rows for goal-model scoring."""
    scoring_rows = enrich_line_readings(
        nearest_lines_for_point(lines, latitude, longitude, limit=max(1, len(lines))),
        primary_radius_km=primary_radius_km,
        extended_radius_km=extended_radius_km,
    )
    crossing_limit = max(1, (len(scoring_rows) * max(0, len(scoring_rows) - 1)) // 2)
    crossings = crossing_candidates_for_point(
        lines,
        latitude,
        longitude,
        nearest_rows=scoring_rows,
        limit=crossing_limit,
        max_distance_km=extended_radius_km,
    )
    return {
        "nearest_lines": scoring_rows,
        "crossings": crossings,
    }


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
            "canonical_event_id": item.get("canonical_event_id"),
            "event_kind": item.get("event_kind"),
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
