"""Versioned, deterministic calculation contracts for the licensed MCP bridge.

This module deliberately contains no Flask or license-storage logic.  The
Electron process owns the durable license and the Flask middleware validates a
short-lived, device-bound session before these functions are reached.
"""

from __future__ import annotations

from datetime import datetime, timezone as datetime_timezone
import math
import os
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MCP_SCHEMA_VERSION = "voxstella.astrology.v1"
DEFAULT_HOUSE_SYSTEM = "R"
HOUSE_SYSTEMS = {
    "R": "Regiomontanus",
    "P": "Placidus",
    "E": "Equal",
    "W": "Whole Sign",
    "O": "Porphyry",
    "C": "Campanus",
    "K": "Koch",
    "T": "Topocentric",
}
CLASSICAL_BODIES = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "North Node",
)
MODERN_BODIES = ("Uranus", "Neptune", "Pluto")
OPTIONAL_BODIES = (*MODERN_BODIES, "Chiron")
SUPPORTED_BODIES = (*CLASSICAL_BODIES, *OPTIONAL_BODIES)
CHART_SECTIONS = (
    "metadata",
    "angles",
    "planets",
    "houses",
    "aspects",
    "moon",
    "considerations",
)
DEFAULT_CHART_SECTIONS = CHART_SECTIONS
DEFAULT_POSITION_SECTIONS = ("metadata", "angles", "planets")
MAX_LOCATION_LENGTH = 200
MAX_LIST_LENGTH = 32
CHART_INPUT_FIELDS = frozenset({
    "datetime",
    "latitude",
    "longitude",
    "timezone",
    "location",
    "house_system_code",
    "bodies",
    "sections",
    "include_modern",
    "include_chiron",
})
PLANETARY_HOURS_INPUT_FIELDS = frozenset({
    "datetime",
    "latitude",
    "longitude",
    "timezone",
    "location",
})
SIGN_NAMES = (
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
ISO_DATETIME_WITH_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}")


class McpInputError(ValueError):
    """An invalid public MCP calculation request."""


def _ensure_known_fields(payload: Mapping[str, Any], allowed: frozenset[str]) -> None:
    unknown = sorted(str(key) for key in payload.keys() if key not in allowed)
    if unknown:
        raise McpInputError("unsupported request fields: " + ", ".join(unknown))


def _finite_number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool):
        raise McpInputError(f"{field} must be a number between {minimum} and {maximum}")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise McpInputError(f"{field} must be a number between {minimum} and {maximum}") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise McpInputError(f"{field} must be between {minimum} and {maximum}")
    return result


def _required_text(value: Any, field: str, *, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip():
        raise McpInputError(f"{field} is required")
    result = value.strip()
    if len(result) > maximum:
        raise McpInputError(f"{field} must be at most {maximum} characters")
    return result


def _optional_location(value: Any, latitude: float, longitude: float) -> str:
    if value is None:
        return f"{latitude:.6f}, {longitude:.6f}"
    return _required_text(value, "location", maximum=MAX_LOCATION_LENGTH)


def _timezone(value: Any) -> tuple[str, ZoneInfo]:
    timezone_name = _required_text(value, "timezone", maximum=100)
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise McpInputError("timezone must be a valid IANA timezone, for example Europe/London") from exc
    return timezone_name, zone


def _house_system(value: Any) -> str:
    raw = DEFAULT_HOUSE_SYSTEM if value in (None, "") else str(value).strip().upper()
    if raw not in HOUSE_SYSTEMS:
        raise McpInputError(
            "house_system_code must be one of " + ", ".join(sorted(HOUSE_SYSTEMS))
        )
    return raw


def _unique_enum_list(
    raw: Any,
    field: str,
    allowed: Sequence[str],
    default: Sequence[str],
) -> List[str]:
    if raw is None:
        return list(default)
    if not isinstance(raw, list):
        raise McpInputError(f"{field} must be an array")
    if not raw:
        raise McpInputError(f"{field} must not be empty")
    if len(raw) > MAX_LIST_LENGTH:
        raise McpInputError(f"{field} contains too many items")
    allowed_map = {item.casefold(): item for item in allowed}
    out: List[str] = []
    seen = set()
    for item in raw:
        if not isinstance(item, str):
            raise McpInputError(f"{field} entries must be strings")
        canonical = allowed_map.get(item.strip().casefold())
        if canonical is None:
            raise McpInputError(
                f"unsupported {field} entry {item!r}; supported values are {', '.join(allowed)}"
            )
        if canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return out


def _normalized_datetime(value: Any, timezone_name: str, zone: ZoneInfo) -> datetime:
    text = _required_text(value, "datetime", maximum=80)
    if ISO_DATETIME_WITH_TIME_RE.match(text) is None:
        raise McpInputError("datetime must be an ISO-8601 date and time")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise McpInputError("datetime must be an ISO-8601 date and time") from exc
    if parsed.tzinfo is None:
        # A supplied IANA zone makes local civil time explicit.  Round-tripping
        # catches nonexistent DST wall times instead of silently changing them.
        local = parsed.replace(tzinfo=zone, fold=0)
        alternate = parsed.replace(tzinfo=zone, fold=1)
        round_trip = local.astimezone(datetime_timezone.utc).astimezone(zone)
        alternate_round_trip = alternate.astimezone(datetime_timezone.utc).astimezone(zone)
        first_valid = round_trip.replace(tzinfo=None) == parsed
        alternate_valid = alternate_round_trip.replace(tzinfo=None) == parsed
        if not first_valid:
            raise McpInputError("datetime is a nonexistent local civil time in the supplied timezone")
        if alternate_valid and local.utcoffset() != alternate.utcoffset():
            raise McpInputError(
                "datetime is ambiguous in the supplied timezone; include an explicit UTC offset"
            )
        parsed = local
    return parsed.astimezone(zone)


def _round_number(value: Any, digits: int = 8) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, digits)


def _sign_position(longitude: Any) -> tuple[Optional[str], Optional[float]]:
    number = _round_number(longitude)
    if number is None:
        return None, None
    normalized = number % 360.0
    return SIGN_NAMES[int(normalized // 30) % 12], round(normalized % 30.0, 8)


def _compact_planets(chart_data: Mapping[str, Any], bodies: Iterable[str]) -> List[Dict[str, Any]]:
    raw = chart_data.get("planets") or {}
    if not isinstance(raw, Mapping):
        return []
    rows: List[Dict[str, Any]] = []
    for body in bodies:
        info = raw.get(body)
        if not isinstance(info, Mapping):
            continue
        longitude = _round_number(info.get("longitude"))
        calculated_sign, calculated_degree = _sign_position(longitude)
        row: Dict[str, Any] = {
            "body": body,
            "longitude": longitude,
            "latitude": _round_number(info.get("latitude")),
            "sign": info.get("sign") or calculated_sign,
            "degree_in_sign": _round_number(info.get("degree_in_sign")) or calculated_degree,
            "house": int(info["house"]) if isinstance(info.get("house"), (int, float)) else None,
            "speed": _round_number(info.get("speed")),
            "retrograde": bool(info.get("retrograde")),
        }
        for key in ("dignity_score", "essential_dignity", "accidental_dignity"):
            if info.get(key) is not None:
                row[key] = _round_number(info.get(key), 4)
        solar = info.get("solar_condition")
        if isinstance(solar, Mapping):
            row["solar_condition"] = {
                "condition": solar.get("condition"),
                "distance_from_sun": _round_number(solar.get("distance_from_sun"), 4),
                "exact_cazimi": bool(solar.get("exact_cazimi", False)),
                "traditional_exception": bool(solar.get("traditional_exception", False)),
            }
        provenance = info.get("calculation_provenance")
        if isinstance(provenance, Mapping):
            row["calculation_provenance"] = {
                key: provenance.get(key)
                for key in ("source", "ephemeris_engine", "accuracy", "degraded")
                if key in provenance
            }
        rows.append(row)
    return rows


def _compact_houses(chart_data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    cusps = chart_data.get("houses") or []
    rulers = chart_data.get("house_rulers") or {}
    if not isinstance(cusps, list):
        return []
    rows = []
    for index, cusp in enumerate(cusps[:12], start=1):
        longitude = _round_number(cusp)
        sign, degree = _sign_position(longitude)
        rows.append(
            {
                "house": index,
                "cusp_longitude": longitude,
                "sign": sign,
                "degree_in_sign": degree,
                "ruler": rulers.get(str(index)) if isinstance(rulers, Mapping) else None,
            }
        )
    return rows


def _compact_aspects(chart_data: Mapping[str, Any], bodies: set[str]) -> List[Dict[str, Any]]:
    raw = chart_data.get("aspects") or []
    if not isinstance(raw, list):
        return []
    rows = []
    for aspect in raw:
        if not isinstance(aspect, Mapping):
            continue
        first = str(aspect.get("planet1") or "")
        second = str(aspect.get("planet2") or "")
        if first not in bodies or second not in bodies:
            continue
        rows.append(
            {
                "body1": first,
                "body2": second,
                "aspect": aspect.get("aspect"),
                "orb": _round_number(aspect.get("orb"), 4),
                "phase": aspect.get("phase"),
                "applying": bool(aspect.get("applying")),
                "degrees_to_exact": _round_number(aspect.get("degrees_to_exact"), 4),
                "time_to_perfection_days": _round_number(aspect.get("time_to_perfection"), 4),
                "perfection_within_sign": bool(aspect.get("perfection_within_sign")),
                "exact_time": aspect.get("exact_time"),
            }
        )
    return rows


def _compact_moon(chart_data: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "last_aspect": chart_data.get("moon_last_aspect"),
        "next_aspect": chart_data.get("moon_next_aspect"),
    }


def _engine_chart(
    *,
    calculation_time: datetime,
    location: str,
    timezone_name: str,
    latitude: float,
    longitude: float,
    house_system_code: str,
    include_modern: bool,
    include_chiron: bool,
) -> Mapping[str, Any]:
    # Lazy import avoids making Flask's large Astro Clock module a dependency of
    # capability discovery and prevents a registration-time circular import.
    from astro_clock_api import _compute_chart_bundle_for

    return _compute_chart_bundle_for(
        calculation_time.isoformat(),
        location,
        timezone_name,
        house_system_code=house_system_code,
        latitude=latitude,
        longitude=longitude,
        include_modern=include_modern,
        include_chiron=include_chiron,
    )


def _validated_chart_request(
    payload: Mapping[str, Any],
    *,
    use_current_time: bool = False,
) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise McpInputError("request body must be a JSON object")
    _ensure_known_fields(payload, CHART_INPUT_FIELDS)
    latitude = _finite_number(payload.get("latitude"), "latitude", -90.0, 90.0)
    longitude = _finite_number(payload.get("longitude"), "longitude", -180.0, 180.0)
    timezone_name, zone = _timezone(payload.get("timezone"))
    location = _optional_location(payload.get("location"), latitude, longitude)
    house_system_code = _house_system(payload.get("house_system_code"))
    bodies = _unique_enum_list(payload.get("bodies"), "bodies", SUPPORTED_BODIES, CLASSICAL_BODIES)
    if bool(payload.get("include_modern")):
        bodies.extend(body for body in MODERN_BODIES if body not in bodies)
    if bool(payload.get("include_chiron")) and "Chiron" not in bodies:
        bodies.append("Chiron")
    default_sections = DEFAULT_POSITION_SECTIONS if use_current_time else DEFAULT_CHART_SECTIONS
    sections = _unique_enum_list(payload.get("sections"), "sections", CHART_SECTIONS, default_sections)
    calculation_time = (
        datetime.now(zone)
        if use_current_time
        else _normalized_datetime(payload.get("datetime"), timezone_name, zone)
    )
    include_modern = any(body in MODERN_BODIES for body in bodies)
    include_chiron = "Chiron" in bodies
    return {
        "calculation_time": calculation_time,
        "location": location,
        "timezone_name": timezone_name,
        "latitude": latitude,
        "longitude": longitude,
        "house_system_code": house_system_code,
        "bodies": bodies,
        "sections": sections,
        "include_modern": include_modern,
        "include_chiron": include_chiron,
        "use_current_time": use_current_time,
    }


def build_chart_bundle(
    payload: Mapping[str, Any],
    *,
    use_current_time: bool = False,
) -> tuple[Mapping[str, Any], Dict[str, Any]]:
    """Return the canonical engine bundle plus its validated public context.

    Feature adapters such as explicit-input synastry use this entry point so
    they share the exact MCP datetime, location, body, and house validation
    used by ``calculate_astrological_chart``.
    """

    context = _validated_chart_request(payload, use_current_time=use_current_time)
    bundle = _engine_chart(
        calculation_time=context["calculation_time"],
        location=context["location"],
        timezone_name=context["timezone_name"],
        latitude=context["latitude"],
        longitude=context["longitude"],
        house_system_code=context["house_system_code"],
        include_modern=context["include_modern"],
        include_chiron=context["include_chiron"],
    )
    return bundle, context


def calculate_chart(payload: Mapping[str, Any], *, use_current_time: bool = False) -> Dict[str, Any]:
    bundle, context = build_chart_bundle(payload, use_current_time=use_current_time)
    calculation_time = context["calculation_time"]
    location = context["location"]
    timezone_name = context["timezone_name"]
    latitude = context["latitude"]
    longitude = context["longitude"]
    house_system_code = context["house_system_code"]
    bodies = context["bodies"]
    sections = context["sections"]
    chart_data = bundle.get("chart_data") or {}
    meta = bundle.get("meta") or {}
    if not isinstance(chart_data, Mapping):
        raise RuntimeError("astrology engine returned an invalid chart payload")

    response: Dict[str, Any] = {
        "schema_version": MCP_SCHEMA_VERSION,
        "calculation": {
            "timestamp": meta.get("timestamp") or calculation_time.isoformat(),
            "location": meta.get("location") or location,
            "timezone": meta.get("timezone") or timezone_name,
            "latitude": _round_number(meta.get("latitude", latitude), 6),
            "longitude": _round_number(meta.get("longitude", longitude), 6),
            "house_system_code": chart_data.get("house_system_code") or house_system_code,
            "house_system": HOUSE_SYSTEMS.get(
                str(chart_data.get("house_system_code") or house_system_code).upper(),
                HOUSE_SYSTEMS[house_system_code],
            ),
            "time_basis": "current" if context["use_current_time"] else "requested",
        },
    }
    if "angles" in sections:
        ascendant = _round_number(chart_data.get("ascendant"))
        midheaven = _round_number(chart_data.get("midheaven"))
        response["angles"] = {
            "ascendant": ascendant,
            "midheaven": midheaven,
            "descendant": round((ascendant + 180.0) % 360.0, 8) if ascendant is not None else None,
            "imum_coeli": round((midheaven + 180.0) % 360.0, 8) if midheaven is not None else None,
        }
    if "planets" in sections:
        response["planets"] = _compact_planets(chart_data, bodies)
    if "houses" in sections:
        response["houses"] = _compact_houses(chart_data)
    if "aspects" in sections:
        response["aspects"] = _compact_aspects(chart_data, set(bodies))
    if "moon" in sections:
        response["moon"] = _compact_moon(chart_data)
    if "considerations" in sections:
        considerations = chart_data.get("considerations")
        response["considerations"] = dict(considerations) if isinstance(considerations, Mapping) else {}
    return response


def _serialize_planetary_hour(hour: Any) -> Dict[str, Any]:
    return {
        "hour_number": int(hour.hour_number),
        "ruling_planet": getattr(hour.ruling_planet, "value", str(hour.ruling_planet)),
        "start_time": hour.start_time.isoformat(),
        "end_time": hour.end_time.isoformat(),
        "duration_minutes": round(float(hour.duration_minutes), 4),
        "is_day_hour": bool(hour.is_day_hour),
    }


def calculate_planetary_hours(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise McpInputError("request body must be a JSON object")
    _ensure_known_fields(payload, PLANETARY_HOURS_INPUT_FIELDS)
    latitude = _finite_number(payload.get("latitude"), "latitude", -90.0, 90.0)
    longitude = _finite_number(payload.get("longitude"), "longitude", -180.0, 180.0)
    timezone_name, zone = _timezone(payload.get("timezone"))
    location = _optional_location(payload.get("location"), latitude, longitude)
    raw_datetime = payload.get("datetime")
    target_local = (
        _normalized_datetime(raw_datetime, timezone_name, zone)
        if raw_datetime not in (None, "")
        else datetime.now(zone)
    )

    from planetary_hours import PlanetaryHoursCalculator

    calculator = PlanetaryHoursCalculator(latitude=latitude, longitude=longitude)
    daily = calculator.calculate_daily_hours_for_local_date(target_local.date(), timezone_name)
    try:
        daily.current_hour = calculator.get_planetary_hour_for_local_datetime(target_local, timezone_name)
    except Exception:
        daily.current_hour = None
    return {
        "schema_version": MCP_SCHEMA_VERSION,
        "calculation": {
            "timestamp": target_local.isoformat(),
            "date": target_local.date().isoformat(),
            "location": location,
            "timezone": timezone_name,
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
        },
        "day_ruler": getattr(daily.day_ruler, "value", str(daily.day_ruler)),
        "sunrise": daily.sunrise.isoformat(),
        "sunset": daily.sunset.isoformat(),
        "hours": [_serialize_planetary_hour(hour) for hour in daily.hours],
        "current_hour": _serialize_planetary_hour(daily.current_hour) if daily.current_hour else None,
    }


def capabilities_payload() -> Dict[str, Any]:
    return {
        "schema_version": MCP_SCHEMA_VERSION,
        "feature_schema_version": "voxstella.features.v1",
        "app_version": os.getenv("VOX_STELLA_APP_VERSION", "development"),
        "transport": "stdio",
        "license_required": True,
        "tools": [
            "get_astrological_capabilities",
            "calculate_astrological_chart",
            "get_current_astrological_positions",
            "calculate_planetary_hours",
            "analyze_synastry",
            "calculate_trait_profile",
            "analyze_transits",
            "scan_transit_window",
            "analyze_astrocartography_location",
            "generate_astrocartography_map",
            "compare_astrocartography_locations",
            "search_astrocartography_atlas",
            "find_election_times",
            "calculate_bazi",
            "analyze_chinese_compatibility",
            "cast_iching_oracle",
            "analyze_forensic_event",
            "run_birth_time_certification",
        ],
        "feature_families": {
            "core": ["chart", "current_positions", "planetary_hours"],
            "synastry": ["explicit_chart_comparison"],
            "trait_profile": ["explicit_or_saved_chart"],
            "transits": ["exact", "bounded_window"],
            "astrocartography": ["location", "map", "compare", "atlas_search"],
            "election": ["bounded_candidate_scan"],
            "chinese_astrology": ["bazi", "compatibility", "iching"],
            "forensic": ["event_chart_analysis"],
            "certification": ["birth_time_rectification_assessment"],
        },
        "house_systems": [
            {"code": code, "name": name} for code, name in HOUSE_SYSTEMS.items()
        ],
        "default_house_system_code": DEFAULT_HOUSE_SYSTEM,
        "bodies": {
            "default": list(CLASSICAL_BODIES),
            "optional": list(OPTIONAL_BODIES),
        },
        "sections": list(CHART_SECTIONS),
        "required_location_parameters": ["latitude", "longitude", "timezone"],
        "timezone_format": "IANA timezone name",
        "datetime_format": "ISO-8601; naive values are interpreted in the supplied IANA timezone",
    }


__all__ = [
    "MCP_SCHEMA_VERSION",
    "McpInputError",
    "build_chart_bundle",
    "calculate_chart",
    "calculate_planetary_hours",
    "capabilities_payload",
]
