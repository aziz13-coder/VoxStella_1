from __future__ import annotations

import calendar
import hashlib
import math
import random
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

TRADITIONAL_PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
DEFAULT_RESEARCH_PLANETS = TRADITIONAL_PLANETS + ["Uranus", "Neptune", "Pluto"]
SMALL_SAMPLE_TARGET_N = 20
LOW_COUNT_THRESHOLD = 5


COLUMN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "name": ("name", "label", "chart_name", "chart name", "person", "title"),
    "datetime": ("datetime", "date_time", "date time", "timestamp", "birth_datetime", "birth datetime"),
    "date": ("date", "birth_date", "birth date"),
    "time": ("time", "birth_time", "birth time"),
    "location": ("location", "place", "city", "birth_place", "birth place"),
    "timezone": ("timezone", "time_zone", "time zone", "tz"),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng"),
    "chart_type": ("chart_type", "chart type", "type"),
    "group": ("group", "cohort", "tag"),
    "notes": ("notes", "note", "description"),
}


EVALUATOR_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "positions",
        "label": "Positions",
        "description": "Planet and object sign placements.",
        "default_scopes": ["planet_signs"],
        "scopes": [
            {"id": "planet_signs", "label": "Planet signs", "description": "Each selected object by zodiac sign."},
            {"id": "elements", "label": "Elements", "description": "Each selected object by elemental triplicity."},
            {"id": "modalities", "label": "Modalities", "description": "Each selected object by modality."},
            {"id": "zodiac_range", "label": "Custom zodiac range", "description": "A chosen object within a selected sign degree range.", "custom": True},
        ],
    },
    {
        "id": "houses",
        "label": "Houses and Angles",
        "description": "House placements, cusp signs, and angle signs.",
        "default_scopes": ["planet_houses"],
        "scopes": [
            {"id": "planet_houses", "label": "Planet houses", "description": "Planet placements by house."},
            {"id": "angle_signs", "label": "Angle signs", "description": "Ascendant and Midheaven signs."},
            {"id": "cusp_signs", "label": "Cusp signs", "description": "House cusp signs."},
        ],
    },
    {
        "id": "aspects",
        "label": "Aspects",
        "description": "Planetary and angle contacts already calculated by the app.",
        "default_scopes": ["planetary_aspects"],
        "scopes": [
            {"id": "planetary_aspects", "label": "Planetary aspects", "description": "Planet-to-planet aspect contacts."},
            {"id": "angle_aspects", "label": "Angle aspects", "description": "Planet-to-angle aspect contacts."},
        ],
    },
    {
        "id": "rulership",
        "label": "Rulership",
        "description": "House ruler assignments and ruler placements.",
        "default_scopes": ["house_rulers"],
        "scopes": [
            {"id": "house_rulers", "label": "House rulers", "description": "Which planet rules each house."},
            {"id": "ruler_houses", "label": "Ruler houses", "description": "The house position of each house ruler."},
        ],
    },
    {
        "id": "receptions",
        "label": "Receptions",
        "description": "Mutual and mixed reception signals when available.",
        "default_scopes": ["reception_pairs"],
        "scopes": [
            {"id": "reception_pairs", "label": "Reception pairs", "description": "Available reception pair signals."},
        ],
    },
    {
        "id": "dispositors",
        "label": "Dispositors",
        "description": "Final and direct dispositor signals when available.",
        "default_scopes": ["final_dispositors"],
        "scopes": [
            {"id": "final_dispositors", "label": "Final dispositors", "description": "Available final dispositor signals."},
        ],
    },
    {
        "id": "dignities",
        "label": "Dignities",
        "description": "Dignified, challenged, and almuten-derived features.",
        "default_scopes": ["dignity_status"],
        "scopes": [
            {"id": "dignity_status", "label": "Dignity status", "description": "Dignified or challenged planet status."},
            {"id": "almutens", "label": "Almutens", "description": "Almuten leaders when available."},
        ],
    },
    {
        "id": "motion",
        "label": "Motion",
        "description": "Retrograde, direct, stationary, and speed class features.",
        "default_scopes": ["direction"],
        "scopes": [
            {"id": "direction", "label": "Direction", "description": "Direct or retrograde motion."},
            {"id": "stations", "label": "Stations", "description": "Near-station motion."},
        ],
    },
    {
        "id": "solar",
        "label": "Solar Conditions",
        "description": "Cazimi, combustion, and under-beams features.",
        "default_scopes": ["solar_conditions"],
        "scopes": [
            {"id": "solar_conditions", "label": "Solar conditions", "description": "Solar condition labels such as under beams."},
            {"id": "solar_phases", "label": "Solar phases", "description": "Detailed solar phase lists when available."},
        ],
    },
    {
        "id": "points",
        "label": "Symbolic Points",
        "description": "Filtered symbolic points and their activation features.",
        "default_scopes": ["active_points"],
        "scopes": [
            {"id": "point_signs", "label": "Point signs", "description": "Computed point zodiac signs."},
            {"id": "active_points", "label": "Active points", "description": "Points with active natal contacts."},
            {"id": "activation_contacts", "label": "Activation contacts", "description": "Object and aspect contact details for active points."},
        ],
    },
    {
        "id": "lots",
        "label": "Lots",
        "description": "Arabic lots and chart part placements.",
        "default_scopes": ["lot_signs"],
        "scopes": [
            {"id": "lot_signs", "label": "Lot signs", "description": "Lot placements by sign."},
            {"id": "lot_houses", "label": "Lot houses", "description": "Lot placements by house."},
        ],
    },
    {
        "id": "fixed_stars",
        "label": "Fixed Stars",
        "description": "Fixed-star conjunction hits calculated by the app.",
        "default_scopes": ["star_hits"],
        "scopes": [
            {"id": "star_hits", "label": "Star hits", "description": "Fixed-star contacts."},
        ],
    },
    {
        "id": "asteroids",
        "label": "Asteroids",
        "description": "Supported asteroid placements and motion.",
        "default_scopes": ["asteroid_signs"],
        "scopes": [
            {"id": "asteroid_signs", "label": "Asteroid signs", "description": "Asteroid placements by sign."},
            {"id": "asteroid_motion", "label": "Asteroid motion", "description": "Asteroid retrograde markers."},
        ],
    },
    {
        "id": "midpoints",
        "label": "Midpoints",
        "description": "Short-arc midpoint sign families.",
        "default_scopes": ["midpoint_signs"],
        "scopes": [
            {"id": "midpoint_signs", "label": "Midpoint signs", "description": "Pair midpoints by sign."},
        ],
    },
    {
        "id": "directional_3d",
        "label": "3D Coordinates",
        "description": "Directional coordinate features when available.",
        "default_scopes": ["horizon_state"],
        "scopes": [
            {"id": "horizon_state", "label": "Horizon state", "description": "Object above or below the local horizon."},
        ],
    },
]


def list_evaluator_catalog() -> List[Dict[str, Any]]:
    return [
        {
            **{key: value for key, value in row.items() if key not in {"scopes", "default_scopes"}},
            "default_scopes": list(row.get("default_scopes") or []),
            "scopes": [dict(scope) for scope in row.get("scopes") or []],
        }
        for row in EVALUATOR_CATALOG
    ]


def _catalog_ids() -> Set[str]:
    return {str(row["id"]) for row in EVALUATOR_CATALOG}


def _catalog_by_id() -> Dict[str, Dict[str, Any]]:
    return {str(row["id"]): row for row in EVALUATOR_CATALOG}


def normalize360(value: Any) -> float:
    return float(value) % 360.0


def signed_delta(a: float, b: float) -> float:
    return ((normalize360(a) - normalize360(b) + 540.0) % 360.0) - 180.0


def short_arc_midpoint(a: float, b: float) -> float:
    return normalize360(float(a) + (signed_delta(float(b), float(a)) / 2.0))


def sign_from_longitude(longitude: Any) -> str:
    return SIGN_NAMES[int(normalize360(longitude) // 30.0) % 12]


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return number


def _safe_int(value: Any) -> Optional[int]:
    number = _safe_float(value)
    if number is None:
        return None
    return int(number)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_header(value: Any) -> str:
    return re.sub(r"\s+", " ", _clean_text(value).lower().replace("_", " ").replace("-", " "))


def _pick_column(raw: Mapping[str, Any], key: str) -> Any:
    aliases = COLUMN_ALIASES.get(key, (key,))
    normalized = {_normalize_header(column): column for column in raw.keys()}
    for alias in aliases:
        actual = normalized.get(_normalize_header(alias))
        if actual is not None:
            return raw.get(actual)
    return None


def _feature_key_part(value: Any) -> str:
    text = _clean_text(value)
    text = text.replace(":", " ").replace("|", " ")
    return re.sub(r"\s+", "_", text).strip("_") or "unknown"


def _feature(
    features: Dict[str, Dict[str, Any]],
    family: str,
    subtype: str,
    parts: Sequence[Any],
    label: str,
    *,
    weight: float = 1.0,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    clean_parts = [_feature_key_part(part) for part in parts]
    key = ":".join([family, subtype, *clean_parts])
    if key not in features:
        features[key] = {
            "key": key,
            "family": family,
            "label": label,
            "weight": float(weight),
        }
        if meta:
            features[key]["meta"] = dict(meta)


def _coerce_datetime_text(value: Any) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.replace(tzinfo=None).isoformat(timespec="seconds")
    except Exception:
        pass
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt).isoformat(timespec="seconds")
        except Exception:
            continue
    return None


def _coerce_date_time(date_value: Any, time_value: Any) -> Optional[str]:
    date_text = _clean_text(date_value)
    if not date_text:
        return None
    time_text = _clean_text(time_value) or "00:00"
    candidates = [
        f"{date_text}T{time_text}",
        f"{date_text} {time_text}",
    ]
    for candidate in candidates:
        value = _coerce_datetime_text(candidate)
        if value:
            return value
    for date_fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        for time_fmt in ("%H:%M:%S", "%H:%M"):
            try:
                parsed_date = datetime.strptime(date_text, date_fmt).date()
                parsed_time = datetime.strptime(time_text, time_fmt).time()
                return datetime.combine(parsed_date, parsed_time).isoformat(timespec="seconds")
            except Exception:
                continue
    return None


def normalize_chart_row(row: Mapping[str, Any], index: int = 0) -> Dict[str, Any]:
    raw = dict(row or {})
    name = _clean_text(_pick_column(raw, "name") or f"Chart {index + 1}")
    dt_text = _coerce_datetime_text(_pick_column(raw, "datetime"))
    if not dt_text:
        dt_text = _coerce_date_time(_pick_column(raw, "date"), _pick_column(raw, "time"))
    location = _clean_text(_pick_column(raw, "location"))
    timezone_name = _clean_text(_pick_column(raw, "timezone"))
    lat = _safe_float(_pick_column(raw, "latitude"))
    lon = _safe_float(_pick_column(raw, "longitude"))
    chart_type = _clean_text(_pick_column(raw, "chart_type") or "natal").lower()
    if chart_type not in {"natal", "event"}:
        chart_type = "natal"

    errors: List[str] = []
    if not dt_text:
        errors.append("datetime_required")
    if not location and (lat is None or lon is None):
        errors.append("location_or_coordinates_required")
    if (lat is None) != (lon is None):
        errors.append("latitude_longitude_pair_required")

    return {
        "name": name,
        "datetime": dt_text,
        "location": location,
        "timezone": timezone_name,
        "latitude": lat,
        "longitude": lon,
        "chart_type": chart_type,
        "group": _clean_text(_pick_column(raw, "group")),
        "notes": _clean_text(_pick_column(raw, "notes")),
        "source_index": index,
        "valid": not errors,
        "errors": errors,
    }


def normalize_chart_rows(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [normalize_chart_row(row, index) for index, row in enumerate(rows or [])]


def generate_matched_control_rows(
    target_rows: Sequence[Mapping[str, Any]],
    *,
    per_chart: int = 20,
    seed: Any = "vox-stella-research",
    year_window: int = 3,
) -> List[Dict[str, Any]]:
    per_chart = max(1, min(int(per_chart or 1), 100))
    year_window = max(0, min(int(year_window or 0), 50))
    seed_text = _clean_text(seed) or "vox-stella-research"
    rng = random.Random(seed_text)
    controls: List[Dict[str, Any]] = []
    for index, row in enumerate(target_rows or []):
        normalized = normalize_chart_row(row, index) if not isinstance(row, dict) or "valid" not in row else dict(row)
        if not normalized.get("valid"):
            continue
        try:
            base = datetime.fromisoformat(str(normalized["datetime"]))
        except Exception:
            continue
        for control_index in range(per_chart):
            year = base.year + rng.randint(-year_window, year_window)
            month = rng.randint(1, 12)
            day = rng.randint(1, calendar.monthrange(year, month)[1])
            hour = rng.randint(0, 23)
            minute = rng.randint(0, 59)
            second = rng.randint(0, 59)
            dt = datetime(year, month, day, hour, minute, second)
            controls.append({
                "name": f"Comparison {index + 1}.{control_index + 1}",
                "datetime": dt.isoformat(timespec="seconds"),
                "location": normalized.get("location") or "",
                "timezone": normalized.get("timezone") or "",
                "latitude": normalized.get("latitude"),
                "longitude": normalized.get("longitude"),
                "chart_type": normalized.get("chart_type") or "natal",
                "group": "generated_comparison",
                "notes": f"Generated comparison for {normalized.get('name')}",
                "source_index": index,
                "valid": True,
                "errors": [],
            })
    return controls


def _planet_rows(chart_data: Mapping[str, Any]) -> List[Dict[str, Any]]:
    planets = chart_data.get("planets") if isinstance(chart_data, Mapping) else None
    rows: List[Dict[str, Any]] = []
    if isinstance(planets, Mapping):
        for name, info in planets.items():
            if isinstance(info, Mapping):
                row = dict(info)
                row.setdefault("planet", name)
                rows.append(row)
    elif isinstance(planets, list):
        for item in planets:
            if isinstance(item, Mapping):
                rows.append(dict(item))
    return rows


def _planet_lookup(chart_data: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("planet") or row.get("name") or ""): row for row in _planet_rows(chart_data) if row.get("planet") or row.get("name")}


def _house_cusps(chart_data: Mapping[str, Any]) -> List[float]:
    values = chart_data.get("house_cusps") or chart_data.get("houses") or []
    if not isinstance(values, list):
        return []
    out: List[float] = []
    for item in values[:12]:
        number = _safe_float(item)
        if number is not None:
            out.append(number)
    return out


def _selected_families(evaluator_families: Optional[Iterable[str]]) -> Set[str]:
    valid = _catalog_ids()
    if evaluator_families is None:
        return set(valid)
    selected = {str(item).strip() for item in evaluator_families if str(item or "").strip()}
    return selected & valid


def _scope_ids_for_family(family: str) -> Set[str]:
    row = _catalog_by_id().get(family) or {}
    return {str(scope.get("id")) for scope in row.get("scopes") or [] if not scope.get("custom")}


def _default_scopes_for_family(family: str) -> List[str]:
    row = _catalog_by_id().get(family) or {}
    return [str(item) for item in row.get("default_scopes") or []]


def _degree_label(value: Any) -> str:
    number = _safe_float(value)
    if number is None:
        return "0"
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _scope_dedupe_key(scope: Mapping[str, Any]) -> Tuple[Any, ...]:
    if scope.get("kind") == "zodiac_range":
        return (
            scope.get("family"),
            scope.get("kind"),
            scope.get("object"),
            scope.get("sign"),
            _degree_label(scope.get("start_degree")),
            _degree_label(scope.get("end_degree")),
        )
    return (scope.get("family"), scope.get("preset"))


def _sort_scope(scope: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    return (
        str(scope.get("family") or ""),
        str(scope.get("preset") or scope.get("kind") or ""),
        str(scope.get("object") or ""),
        str(scope.get("sign") or ""),
        _degree_label(scope.get("start_degree")),
    )


def normalize_feature_scopes(
    feature_scopes: Optional[Iterable[Any]] = None,
    *,
    evaluator_families: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    catalog = _catalog_by_id()
    normalized: List[Dict[str, Any]] = []

    def add_scope(scope: Dict[str, Any]) -> None:
        if not scope.get("family"):
            return
        key = _scope_dedupe_key(scope)
        if any(_scope_dedupe_key(existing) == key for existing in normalized):
            return
        normalized.append(scope)

    if feature_scopes is not None:
        for raw in feature_scopes or []:
            if isinstance(raw, str):
                family, _, preset = raw.partition(":")
                raw = {"family": family, "preset": preset}
            if not isinstance(raw, Mapping):
                continue
            family = _clean_text(raw.get("family"))
            if family not in catalog:
                continue
            preset = _clean_text(raw.get("preset") or raw.get("scope") or raw.get("id"))
            kind = _clean_text(raw.get("kind"))
            if family == "positions" and (kind == "zodiac_range" or preset == "zodiac_range"):
                obj = _clean_text(raw.get("object") or raw.get("planet") or raw.get("body"))
                sign = _clean_text(raw.get("sign"))
                start = _safe_float(raw.get("start_degree"))
                end = _safe_float(raw.get("end_degree"))
                if not obj or sign not in SIGN_NAMES or start is None or end is None:
                    continue
                add_scope({
                    "family": "positions",
                    "kind": "zodiac_range",
                    "object": obj,
                    "sign": sign,
                    "start_degree": max(0.0, min(30.0, start)),
                    "end_degree": max(0.0, min(30.0, end)),
                })
                continue
            if preset in _scope_ids_for_family(family):
                objects = raw.get("objects")
                add_scope({
                    "family": family,
                    "preset": preset,
                    "objects": objects if objects else "default",
                })
    else:
        families = _selected_families(evaluator_families)
        for family in families:
            for preset in _default_scopes_for_family(family):
                add_scope({"family": family, "preset": preset, "objects": "default"})

    return sorted(normalized, key=_sort_scope)


def _selected_scope_set(scopes: Sequence[Mapping[str, Any]]) -> Set[Tuple[str, str]]:
    return {
        (str(scope.get("family")), str(scope.get("preset")))
        for scope in scopes
        if scope.get("family") and scope.get("preset")
    }


def _custom_scopes(scopes: Sequence[Mapping[str, Any]], family: str, kind: str) -> List[Dict[str, Any]]:
    return [
        dict(scope)
        for scope in scopes
        if scope.get("family") == family and scope.get("kind") == kind
    ]


def _scope_enabled(scope_set: Set[Tuple[str, str]], family: str, preset: str) -> bool:
    return (family, preset) in scope_set


def _scope_meta(family: str, preset: str) -> Dict[str, Any]:
    return {"scope": {"family": family, "preset": preset}}


def _degree_in_sign(longitude: Any) -> Optional[float]:
    number = _safe_float(longitude)
    if number is None:
        return None
    return normalize360(number) % 30.0


def _degree_in_range(degree: float, start: float, end: float) -> bool:
    if start <= end:
        return start <= degree <= end
    return degree >= start or degree <= end


def _canonical_pair(a: Any, b: Any) -> Tuple[str, str]:
    left = _clean_text(a)
    right = _clean_text(b)
    order = {name: index for index, name in enumerate(DEFAULT_RESEARCH_PLANETS)}
    if order.get(left, 999) <= order.get(right, 999):
        return left, right
    return right, left


def _extract_reception_items(chart_data: Mapping[str, Any], enrichments: Mapping[str, Any]) -> List[Dict[str, Any]]:
    for source in (enrichments.get("receptions"), chart_data.get("receptions")):
        if isinstance(source, Mapping):
            items = source.get("items") or source.get("receptions") or []
            if isinstance(items, list):
                return [dict(item) for item in items if isinstance(item, Mapping)]
        if isinstance(source, list):
            return [dict(item) for item in source if isinstance(item, Mapping)]
    return []


def extract_research_features(
    chart_data: Mapping[str, Any],
    *,
    evaluator_families: Optional[Iterable[str]] = None,
    feature_scopes: Optional[Iterable[Any]] = None,
    enrichments: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    chart = chart_data if isinstance(chart_data, Mapping) else {}
    extra = enrichments if isinstance(enrichments, Mapping) else {}
    normalized_scopes = normalize_feature_scopes(feature_scopes, evaluator_families=evaluator_families)
    scope_set = _selected_scope_set(normalized_scopes)
    custom_position_ranges = _custom_scopes(normalized_scopes, "positions", "zodiac_range")
    features: Dict[str, Dict[str, Any]] = {}
    planets = _planet_rows(chart)
    lookup = _planet_lookup(chart)
    metrics = extra.get("metrics") if isinstance(extra.get("metrics"), Mapping) else {}

    if (
        _scope_enabled(scope_set, "positions", "planet_signs")
        or _scope_enabled(scope_set, "positions", "elements")
        or _scope_enabled(scope_set, "positions", "modalities")
        or custom_position_ranges
    ):
        for planet in planets:
            name = _clean_text(planet.get("planet") or planet.get("name"))
            lon = _safe_float(planet.get("longitude"))
            if not name or lon is None:
                continue
            sign = _clean_text(planet.get("sign")) or sign_from_longitude(lon)
            if _scope_enabled(scope_set, "positions", "planet_signs"):
                _feature(features, "positions", "planet_sign", [name, sign], f"{name} in {sign}", meta=_scope_meta("positions", "planet_signs"))
            if _scope_enabled(scope_set, "positions", "elements"):
                _feature(features, "positions", "planet_element", [name, _element(sign)], f"{name} in {_element(sign)} element", meta=_scope_meta("positions", "elements"))
            if _scope_enabled(scope_set, "positions", "modalities"):
                _feature(features, "positions", "planet_modality", [name, _modality(sign)], f"{name} in {_modality(sign)} modality", meta=_scope_meta("positions", "modalities"))
            degree = _degree_in_sign(lon)
            if degree is not None:
                for custom_scope in custom_position_ranges:
                    start = float(custom_scope["start_degree"])
                    end = float(custom_scope["end_degree"])
                    if name == custom_scope["object"] and sign == custom_scope["sign"] and _degree_in_range(degree, start, end):
                        start_label = _degree_label(start)
                        end_label = _degree_label(end)
                        _feature(
                            features,
                            "positions",
                            "zodiac_range",
                            [name, sign, start_label, end_label],
                            f"{name} in {sign} {start_label}-{end_label}",
                            meta={"scope": dict(custom_scope)},
                        )

    if (
        _scope_enabled(scope_set, "houses", "planet_houses")
        or _scope_enabled(scope_set, "houses", "angle_signs")
        or _scope_enabled(scope_set, "houses", "cusp_signs")
    ):
        cusps = _house_cusps(chart)
        if _scope_enabled(scope_set, "houses", "planet_houses"):
            for planet in planets:
                name = _clean_text(planet.get("planet") or planet.get("name"))
                house = _safe_int(planet.get("house"))
                if name and house and 1 <= house <= 12:
                    _feature(features, "houses", "planet_house", [name, house], f"{name} in House {house}", meta=_scope_meta("houses", "planet_houses"))
        if _scope_enabled(scope_set, "houses", "angle_signs"):
            angles = {
                "Ascendant": chart.get("ascendant"),
                "Midheaven": chart.get("midheaven"),
            }
            for angle, lon_raw in angles.items():
                lon = _safe_float(lon_raw)
                if lon is not None:
                    sign = sign_from_longitude(lon)
                    _feature(features, "houses", "angle_sign", [angle, sign], f"{angle} in {sign}", meta=_scope_meta("houses", "angle_signs"))
        if _scope_enabled(scope_set, "houses", "cusp_signs"):
            for index, lon in enumerate(cusps, start=1):
                sign = sign_from_longitude(lon)
                _feature(features, "houses", "cusp_sign", [index, sign], f"House {index} cusp in {sign}", meta=_scope_meta("houses", "cusp_signs"))

    if _scope_enabled(scope_set, "aspects", "planetary_aspects"):
        for aspect in metrics.get("planetary_aspects") or chart.get("aspects") or []:
            if not isinstance(aspect, Mapping):
                continue
            left = aspect.get("planet1") or aspect.get("a") or aspect.get("body1")
            right = aspect.get("planet2") or aspect.get("b") or aspect.get("body2")
            name = aspect.get("aspect") or aspect.get("type")
            if left and right and name:
                a, b = _canonical_pair(left, right)
                _feature(features, "aspects", "planetary", [a, name, b], f"{a} {name} {b}", meta=_scope_meta("aspects", "planetary_aspects"))
    if _scope_enabled(scope_set, "aspects", "angle_aspects"):
        for aspect in metrics.get("angle_aspects") or []:
            if not isinstance(aspect, Mapping):
                continue
            planet = aspect.get("planet")
            angle = aspect.get("angle")
            name = aspect.get("aspect")
            if planet and angle and name:
                _feature(features, "aspects", "angle", [planet, name, angle], f"{planet} {name} {angle}", meta=_scope_meta("aspects", "angle_aspects"))

    if _scope_enabled(scope_set, "rulership", "house_rulers") or _scope_enabled(scope_set, "rulership", "ruler_houses"):
        rulers = chart.get("house_rulers") or metrics.get("house_rulers") or {}
        planet_houses = metrics.get("planet_houses") or {}
        if isinstance(rulers, Mapping):
            for house, ruler in rulers.items():
                if not ruler:
                    continue
                if _scope_enabled(scope_set, "rulership", "house_rulers"):
                    _feature(features, "rulership", "house_ruler", [house, ruler], f"House {house} ruled by {ruler}", meta=_scope_meta("rulership", "house_rulers"))
                ruler_house = planet_houses.get(str(ruler)) or lookup.get(str(ruler), {}).get("house")
                if ruler_house and _scope_enabled(scope_set, "rulership", "ruler_houses"):
                    _feature(features, "rulership", "ruler_house", [house, ruler_house], f"Ruler of House {house} in House {ruler_house}", meta=_scope_meta("rulership", "ruler_houses"))

    if _scope_enabled(scope_set, "receptions", "reception_pairs"):
        for item in _extract_reception_items(chart, extra):
            kind = item.get("type") or item.get("reception_type") or "reception"
            left = item.get("planet_a") or item.get("from") or item.get("receiving")
            right = item.get("planet_b") or item.get("to") or item.get("received")
            if left and right:
                a, b = _canonical_pair(left, right)
                _feature(features, "receptions", kind, [a, b], f"{kind.replace('_', ' ').title()}: {a} and {b}", meta=_scope_meta("receptions", "reception_pairs"))

    if _scope_enabled(scope_set, "dispositors", "final_dispositors"):
        finals = extra.get("final_dispositor") or metrics.get("final_dispositor") or chart.get("final_dispositor") or {}
        if isinstance(finals, Mapping):
            for planet, dispositor in finals.items():
                if dispositor:
                    _feature(features, "dispositors", "final", [planet, dispositor], f"{planet} final dispositor {dispositor}", meta=_scope_meta("dispositors", "final_dispositors"))

    if _scope_enabled(scope_set, "dignities", "dignity_status") or _scope_enabled(scope_set, "dignities", "almutens"):
        for planet in planets:
            name = _clean_text(planet.get("planet") or planet.get("name"))
            score = _safe_float(planet.get("dignity_score"))
            essential = _safe_float(planet.get("essential_dignity"))
            if not name:
                continue
            dignity_value = score if score is not None else essential
            if dignity_value is None:
                continue
            if _scope_enabled(scope_set, "dignities", "dignity_status"):
                if dignity_value >= 4:
                    _feature(features, "dignities", "planet_dignified", [name], f"{name} dignified", meta=_scope_meta("dignities", "dignity_status"))
                elif dignity_value <= -3:
                    _feature(features, "dignities", "planet_challenged", [name], f"{name} challenged dignity", meta=_scope_meta("dignities", "dignity_status"))
        almutens = extra.get("almutens")
        if isinstance(almutens, Mapping) and _scope_enabled(scope_set, "dignities", "almutens"):
            for point in almutens.get("items") or []:
                if isinstance(point, Mapping) and point.get("label") and point.get("leader"):
                    _feature(features, "dignities", "almuten", [point.get("label"), point.get("leader")], f"{point.get('label')} almuten {point.get('leader')}", meta=_scope_meta("dignities", "almutens"))

    if _scope_enabled(scope_set, "motion", "direction") or _scope_enabled(scope_set, "motion", "stations"):
        for planet in planets:
            name = _clean_text(planet.get("planet") or planet.get("name"))
            if not name:
                continue
            speed = _safe_float(planet.get("speed"))
            retrograde = planet.get("retrograde")
            if retrograde is None and speed is not None:
                retrograde = speed < 0
            if _scope_enabled(scope_set, "motion", "direction"):
                _feature(features, "motion", "retrograde" if retrograde else "direct", [name], f"{name} {'retrograde' if retrograde else 'direct'}", meta=_scope_meta("motion", "direction"))
            if speed is not None and abs(speed) <= 0.03 and _scope_enabled(scope_set, "motion", "stations"):
                _feature(features, "motion", "stationary", [name], f"{name} near station", meta=_scope_meta("motion", "stations"))

    if _scope_enabled(scope_set, "solar", "solar_conditions") or _scope_enabled(scope_set, "solar", "solar_phases"):
        solar = metrics.get("solar") if isinstance(metrics.get("solar"), Mapping) else {}
        conditions = solar.get("conditions") if isinstance(solar.get("conditions"), Mapping) else {}
        if _scope_enabled(scope_set, "solar", "solar_conditions"):
            for planet, condition in conditions.items():
                _feature(features, "solar", "condition", [planet, condition], f"{planet} {condition}", meta=_scope_meta("solar", "solar_conditions"))
        solar_phase = metrics.get("solar_phase") if isinstance(metrics.get("solar_phase"), Mapping) else {}
        if _scope_enabled(scope_set, "solar", "solar_phases"):
            for phase_key, names in solar_phase.items():
                if isinstance(names, list):
                    for name in names:
                        _feature(features, "solar", "phase", [name, phase_key], f"{name} {str(phase_key).replace('_', ' ')}", meta=_scope_meta("solar", "solar_phases"))

    if (
        _scope_enabled(scope_set, "points", "point_signs")
        or _scope_enabled(scope_set, "points", "active_points")
        or _scope_enabled(scope_set, "points", "activation_contacts")
    ):
        points_payload = extra.get("points_payload") if isinstance(extra.get("points_payload"), Mapping) else {}
        for point in points_payload.get("points") or []:
            if not isinstance(point, Mapping) or point.get("available") is False:
                continue
            key = point.get("key") or point.get("name")
            name = point.get("name") or key
            lon = _safe_float(point.get("longitude"))
            if key and lon is not None and _scope_enabled(scope_set, "points", "point_signs"):
                _feature(features, "points", "sign", [key, sign_from_longitude(lon)], f"{name} in {sign_from_longitude(lon)}", meta=_scope_meta("points", "point_signs"))
            if point.get("hits") and _scope_enabled(scope_set, "points", "active_points"):
                _feature(features, "points", "active", [key], f"{name} active", meta=_scope_meta("points", "active_points"))
            if point.get("hits") and _scope_enabled(scope_set, "points", "activation_contacts"):
                for hit in point.get("hits") or []:
                    if isinstance(hit, Mapping):
                        obj = hit.get("object_name") or hit.get("object")
                        asp = hit.get("aspect")
                        if obj and asp:
                            _feature(features, "points", "activation", [key, obj, asp], f"{name} active by {obj} {asp}", meta=_scope_meta("points", "activation_contacts"))

    if _scope_enabled(scope_set, "lots", "lot_signs") or _scope_enabled(scope_set, "lots", "lot_houses"):
        lots = extra.get("arabic_parts") or chart.get("arabic_parts") or {}
        lot_rows = lots.values() if isinstance(lots, Mapping) else lots if isinstance(lots, list) else []
        for lot in lot_rows:
            if not isinstance(lot, Mapping):
                continue
            name = lot.get("name") or lot.get("key")
            lon = _safe_float(lot.get("lon") if lot.get("lon") is not None else lot.get("longitude"))
            sign = lot.get("sign") or (sign_from_longitude(lon) if lon is not None else None)
            house = lot.get("house")
            if name and sign and _scope_enabled(scope_set, "lots", "lot_signs"):
                _feature(features, "lots", "sign", [name, sign], f"{name} in {sign}", meta=_scope_meta("lots", "lot_signs"))
            if name and house and _scope_enabled(scope_set, "lots", "lot_houses"):
                _feature(features, "lots", "house", [name, house], f"{name} in House {house}", meta=_scope_meta("lots", "lot_houses"))

    if _scope_enabled(scope_set, "fixed_stars", "star_hits"):
        for hit in extra.get("fixed_star_hits") or chart.get("fixed_star_hits") or []:
            if not isinstance(hit, Mapping):
                continue
            star = hit.get("star") or hit.get("name")
            target = hit.get("planet") or hit.get("target")
            if star and target:
                _feature(features, "fixed_stars", "hit", [star, target], f"{star} with {target}", meta=_scope_meta("fixed_stars", "star_hits"))

    if _scope_enabled(scope_set, "asteroids", "asteroid_signs") or _scope_enabled(scope_set, "asteroids", "asteroid_motion"):
        asteroids = extra.get("asteroids") if isinstance(extra.get("asteroids"), Mapping) else {}
        for item in asteroids.get("items") or chart.get("asteroids") or []:
            if not isinstance(item, Mapping):
                continue
            name = item.get("name")
            lon = _safe_float(item.get("longitude"))
            sign = item.get("sign") or (sign_from_longitude(lon) if lon is not None else None)
            if name and sign and _scope_enabled(scope_set, "asteroids", "asteroid_signs"):
                _feature(features, "asteroids", "sign", [name, sign], f"{name} in {sign}", meta=_scope_meta("asteroids", "asteroid_signs"))
            if name and item.get("retrograde") and _scope_enabled(scope_set, "asteroids", "asteroid_motion"):
                _feature(features, "asteroids", "retrograde", [name], f"{name} retrograde", meta=_scope_meta("asteroids", "asteroid_motion"))

    if _scope_enabled(scope_set, "midpoints", "midpoint_signs"):
        midpoint_planets = [row for row in planets if _clean_text(row.get("planet")) in DEFAULT_RESEARCH_PLANETS and _safe_float(row.get("longitude")) is not None]
        for index, left in enumerate(midpoint_planets):
            for right in midpoint_planets[index + 1:]:
                left_name = _clean_text(left.get("planet"))
                right_name = _clean_text(right.get("planet"))
                lon = short_arc_midpoint(float(left["longitude"]), float(right["longitude"]))
                sign = sign_from_longitude(lon)
                _feature(features, "midpoints", "pair_sign", [left_name, right_name, sign], f"{left_name}-{right_name} midpoint in {sign}", meta=_scope_meta("midpoints", "midpoint_signs"))

    if _scope_enabled(scope_set, "directional_3d", "horizon_state"):
        directional = extra.get("directional_3d") or chart.get("directional_3d") or {}
        objects = directional.get("objects") if isinstance(directional, Mapping) else None
        if isinstance(objects, list):
            for item in objects:
                if not isinstance(item, Mapping):
                    continue
                name = item.get("name") or item.get("body")
                hor = item.get("horizontal") if isinstance(item.get("horizontal"), Mapping) else {}
                altitude = _safe_float(hor.get("latitude") or hor.get("altitude"))
                if name and altitude is not None:
                    zone = "above_horizon" if altitude >= 0 else "below_horizon"
                    _feature(features, "directional_3d", zone, [name], f"{name} {zone.replace('_', ' ')}", meta=_scope_meta("directional_3d", "horizon_state"))

    return features


def _normal_p_from_z(z_value: float) -> float:
    return max(0.0, min(1.0, math.erfc(abs(float(z_value)) / math.sqrt(2.0))))


def _benjamini_hochberg(rows: List[Dict[str, Any]]) -> None:
    ordered = sorted(
        [row for row in rows if row.get("p_value") is not None],
        key=lambda row: float(row["p_value"]),
    )
    m = len(ordered)
    running = 1.0
    for rank_from_end, row in enumerate(reversed(ordered), start=1):
        rank = m - rank_from_end + 1
        p_value = float(row["p_value"])
        running = min(running, p_value * m / max(rank, 1))
        row["q_value"] = round(running, 6)
    for row in rows:
        row.setdefault("q_value", None)


def analyze_feature_sets(
    target_feature_sets: Sequence[Iterable[str]],
    control_feature_sets: Sequence[Iterable[str]],
    feature_labels: Optional[Mapping[str, Mapping[str, Any]]] = None,
    *,
    min_occurrence: int = 1,
) -> Dict[str, Any]:
    target_sets = [set(row or []) for row in target_feature_sets]
    control_sets = [set(row or []) for row in control_feature_sets]
    labels = feature_labels if isinstance(feature_labels, Mapping) else {}
    target_n = len(target_sets)
    control_n = len(control_sets)
    all_keys = sorted(set().union(*target_sets, *control_sets) if (target_sets or control_sets) else set())
    rows: List[Dict[str, Any]] = []

    for key in all_keys:
        target_count = sum(1 for row in target_sets if key in row)
        control_count = sum(1 for row in control_sets if key in row)
        if max(target_count, control_count) < int(min_occurrence or 1):
            continue
        target_rate = target_count / target_n if target_n else 0.0
        control_rate = control_count / control_n if control_n else 0.0
        diff = target_rate - control_rate
        pooled = (target_count + control_count) / (target_n + control_n) if (target_n + control_n) else 0.0
        denom = math.sqrt(max(pooled * (1.0 - pooled) * ((1.0 / target_n) + (1.0 / control_n)), 0.0)) if target_n and control_n else 0.0
        z_score = diff / denom if denom > 0 else 0.0
        p_value = _normal_p_from_z(z_score) if target_n and control_n else None
        info = dict(labels.get(key) or {})
        warnings: List[str] = []
        if target_n < SMALL_SAMPLE_TARGET_N:
            warnings.append("small_target_sample")
        if min(target_count, control_count) < LOW_COUNT_THRESHOLD:
            warnings.append("low_feature_count")
        if control_count == 0 and target_count > 0:
            warnings.append("zero_control_occurrence")
        lift = None
        if control_rate > 0:
            lift = target_rate / control_rate
        elif target_rate > 0:
            lift = math.inf
        rows.append({
            "key": key,
            "label": info.get("label") or key,
            "family": info.get("family") or "unknown",
            "target_count": target_count,
            "target_total": target_n,
            "control_count": control_count,
            "control_total": control_n,
            "target_rate": round(target_rate, 6),
            "control_rate": round(control_rate, 6),
            "difference": round(diff, 6),
            "lift": None if lift is None else ("inf" if math.isinf(lift) else round(lift, 6)),
            "z_score": round(z_score, 6),
            "p_value": None if p_value is None else round(p_value, 6),
            "q_value": None,
            "effect_direction": "more_common" if diff >= 0 else "less_common",
            "warnings": warnings,
        })

    _benjamini_hochberg(rows)
    rows.sort(key=lambda row: (
        float(row["q_value"]) if row.get("q_value") is not None else 1.0,
        float(row["p_value"]) if row.get("p_value") is not None else 1.0,
        -abs(float(row.get("difference") or 0.0)),
        str(row.get("label") or ""),
    ))
    return {
        "target_count": target_n,
        "control_count": control_n,
        "feature_count": len(all_keys),
        "signal_count": len(rows),
        "signals": rows,
    }


def analyze_research_snapshots(
    target_snapshots: Sequence[Mapping[str, Any]],
    control_snapshots: Sequence[Mapping[str, Any]],
    *,
    evaluator_families: Optional[Iterable[str]] = None,
    feature_scopes: Optional[Iterable[Any]] = None,
    min_occurrence: int = 1,
) -> Dict[str, Any]:
    target_feature_sets: List[Set[str]] = []
    control_feature_sets: List[Set[str]] = []
    labels: Dict[str, Dict[str, Any]] = {}
    normalized_scopes = normalize_feature_scopes(feature_scopes, evaluator_families=evaluator_families)

    for collection, out in ((target_snapshots, target_feature_sets), (control_snapshots, control_feature_sets)):
        for snapshot in collection:
            features = extract_research_features(
                snapshot.get("chart_data") or snapshot,
                feature_scopes=normalized_scopes,
                enrichments=snapshot.get("enrichments") or {},
            )
            out.append(set(features))
            for key, value in features.items():
                labels.setdefault(key, value)

    payload = analyze_feature_sets(target_feature_sets, control_feature_sets, labels, min_occurrence=min_occurrence)
    payload["feature_scopes"] = normalized_scopes
    payload["feature_scope_count"] = len(normalized_scopes)
    payload["evaluator_families"] = sorted({str(scope.get("family")) for scope in normalized_scopes if scope.get("family")})
    return payload


def build_run_id(payload: Mapping[str, Any]) -> str:
    text = repr(sorted((str(k), repr(v)) for k, v in dict(payload or {}).items()))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _element(sign: str) -> str:
    sign_l = _clean_text(sign).lower()
    if sign_l in {"aries", "leo", "sagittarius"}:
        return "Fire"
    if sign_l in {"taurus", "virgo", "capricorn"}:
        return "Earth"
    if sign_l in {"gemini", "libra", "aquarius"}:
        return "Air"
    return "Water"


def _modality(sign: str) -> str:
    sign_l = _clean_text(sign).lower()
    if sign_l in {"aries", "cancer", "libra", "capricorn"}:
        return "Cardinal"
    if sign_l in {"taurus", "leo", "scorpio", "aquarius"}:
        return "Fixed"
    return "Mutable"
