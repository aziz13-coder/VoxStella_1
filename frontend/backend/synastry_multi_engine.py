from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from house_influence import SIGN_RULER
from synastry_engine import (
    _angular_distance,
    _build_points,
    _cross_aspects,
    _find_best_aspect,
    _house_cusps,
    _natal_unaspected_points,
    _normalize_options,
    _normalize_point_name,
    _point_availability,
    _source_basis,
    build_synastry_report,
)


ENGINE_DEFS: Dict[str, Dict[str, Any]] = {
    "memo": {
        "id": "memo",
        "label": "Memo",
        "report_kind": "memo",
        "description": "Narrative memo built from the current synastry scoring catalog.",
    },
    "life_themes": {
        "id": "life_themes",
        "label": "Life Themes",
        "report_kind": "structured",
        "description": "Full-house compatibility engine organized as self-to-theme comparisons.",
    },
    "union_dynamics": {
        "id": "union_dynamics",
        "label": "Union Dynamics",
        "report_kind": "structured",
        "description": "Partnership and domestic compatibility engine organized around bond and home dynamics.",
    },
    "work_alliance": {
        "id": "work_alliance",
        "label": "Work Alliance",
        "report_kind": "structured",
        "description": "Collaboration-focused compatibility engine built from the business house cluster.",
    },
}

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

SIGN_TO_ELEMENT = {
    "Aries": "Fire",
    "Leo": "Fire",
    "Sagittarius": "Fire",
    "Taurus": "Earth",
    "Virgo": "Earth",
    "Capricorn": "Earth",
    "Gemini": "Air",
    "Libra": "Air",
    "Aquarius": "Air",
    "Cancer": "Water",
    "Scorpio": "Water",
    "Pisces": "Water",
}

ELEMENT_ORDER = ("Fire", "Earth", "Air", "Water")
ELEMENT_META = {
    "Fire": {"id": "fire", "label": "Fire", "glyph": "🜂"},
    "Earth": {"id": "earth", "label": "Earth", "glyph": "🜃"},
    "Air": {"id": "air", "label": "Air", "glyph": "🜁"},
    "Water": {"id": "water", "label": "Water", "glyph": "🜄"},
}
ELEMENT_COMPATIBILITY = {
    ("Fire", "Fire"),
    ("Earth", "Earth"),
    ("Air", "Air"),
    ("Water", "Water"),
    ("Fire", "Air"),
    ("Air", "Fire"),
    ("Earth", "Water"),
    ("Water", "Earth"),
}
HOUSE_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
POINT_GLYPHS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
    "Uranus": "♅",
    "Neptune": "♆",
    "Pluto": "♇",
    "Chiron": "⚷",
    "Lilith": "⚸",
    "North Node": "☊",
    "South Node": "☋",
    "Rahu": "☊",
    "Ketu": "☋",
    "Fortuna": "⊗",
    "Ascendant": "Asc",
    "Descendant": "Dsc",
    "Midheaven": "MC",
    "IC": "IC",
}
ASPECT_GLYPHS = {
    "Conjunction": "☌",
    "Semisextile": "⚺",
    "Semisquare": "∠",
    "SemiSquare": "∠",
    "Sextile": "⚹",
    "Square": "□",
    "Sesquiquadrate": "⚼",
    "Trine": "△",
    "Quincunx": "⚻",
    "Opposition": "☍",
}
FALLBACK_RESONANCE_GLYPHS = {
    3: "≍",
    1: "☍",
    -3: "✕",
}

OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}
PRESSURE_PLANETS = {"Saturn", "Neptune", "Lilith"}
CORE_AND_MODERN = (
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
)

HOUSE_THEME_META: Dict[int, Dict[str, str]] = {
    1: {"id": "alaspT01", "label": "Identity & Presence"},
    2: {"id": "alaspT02", "label": "Resources & Security"},
    3: {"id": "alaspT03", "label": "Exchange & Communication"},
    4: {"id": "alaspT04", "label": "Home & Roots"},
    5: {"id": "alaspT05", "label": "Romance & Expression"},
    6: {"id": "alaspT06", "label": "Service & Friction"},
    7: {"id": "alaspT07", "label": "Partnership"},
    8: {"id": "alaspT08", "label": "Entanglement & Risk"},
    9: {"id": "alaspT09", "label": "Meaning & Belief"},
    10: {"id": "alaspT10", "label": "Status & Direction"},
    11: {"id": "alaspT11", "label": "Networks & Allies"},
    12: {"id": "alaspT12", "label": "Private Undercurrent"},
}

OVERALL_DIRECT_PAIRS: Dict[int, Tuple[Tuple[str, str], ...]] = {
    1: (("Sun", "Sun"), ("Sun", "Mars"), ("Mars", "Sun")),
    2: (("Sun", "Sun"), ("Sun", "Venus"), ("Venus", "Sun")),
    3: (("Sun", "Sun"), ("Sun", "Mercury"), ("Mercury", "Sun")),
    4: (("Sun", "Sun"), ("Sun", "Moon"), ("Moon", "Sun")),
    5: (("Sun", "Sun"),),
    6: (("Sun", "Sun"), ("Sun", "Mercury"), ("Mercury", "Sun")),
    7: (("Sun", "Sun"), ("Sun", "Venus"), ("Venus", "Sun")),
    8: (("Sun", "Sun"), ("Sun", "Mars"), ("Mars", "Sun")),
    9: (("Sun", "Sun"), ("Sun", "Jupiter"), ("Jupiter", "Sun")),
    10: (("Sun", "Sun"), ("Sun", "Saturn"), ("Saturn", "Sun")),
    11: (("Sun", "Sun"), ("Sun", "Saturn"), ("Saturn", "Sun")),
    12: (("Sun", "Sun"), ("Sun", "Jupiter"), ("Jupiter", "Sun")),
}

WORK_HOUSES = (1, 2, 6, 7, 10)
WORK_WARNING_HOUSES = (2, 6, 10)
WORK_BURDEN_SEEDS = {
    "Snap A": ("Sun", "Saturn", "Sun"),
    "Snap B": ("Sun", "Sun", "Saturn"),
}
WORK_HARD_LOCAL_ASPECTS = {"Conjunction", "Square", "Opposition"}
PROFILE_TO_SEX = {
    "feminine": "female",
    "masculine": "male",
}
PROFILE_BUCKETS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "feminine": {
        "a": ("Sun", "Moon", "Venus", "Ascendant"),
        "b": ("Moon", "Venus", "Descendant"),
    },
    "masculine": {
        "a": ("Sun", "Mars", "Ascendant"),
        "b": ("Sun", "Mars", "Descendant"),
    },
    "blended": {
        "a": ("Sun", "Moon", "Venus", "Mars", "Ascendant"),
        "b": ("Sun", "Moon", "Venus", "Mars", "Descendant"),
    },
}
UNION_157_VECTORS: Dict[str, Tuple[str, ...]] = {
    "female": ("Venus", "Mars", "Mars", "Venus", "Mars", "Sun", "Sun"),
    "male": ("Mars", "Venus", "Mars", "Venus", "Sun", "Venus", "Sun"),
}
UNION_14_VECTORS: Dict[str, Tuple[str, ...]] = {
    "female": ("Moon", "Moon", "Saturn", "Saturn", "Sun", "Sun", "Sun"),
    "male": ("Moon", "Saturn", "Moon", "Saturn", "Moon", "Saturn", "Sun"),
}
LILITH_ALIASES = {
    "lilith": "Lilith",
    "true lilith": "Lilith",
    "black moon lilith": "Lilith",
    "mean lilith": "Lilith",
    "osc lilith": "Lilith",
}


def list_synastry_engines() -> List[Dict[str, Any]]:
    return [dict(ENGINE_DEFS[key]) for key in ("memo", "life_themes", "union_dynamics", "work_alliance")]


def _engine_meta(engine_id: str) -> Dict[str, Any]:
    return dict(ENGINE_DEFS.get(engine_id) or ENGINE_DEFS["memo"])


def _normalize_engine_id(engine_id: Optional[str]) -> str:
    raw = str(engine_id or "memo").strip().lower()
    return raw if raw in ENGINE_DEFS else "memo"


def _normalize_profile(value: Optional[str]) -> str:
    raw = str(value or "blended").strip().lower()
    return raw if raw in PROFILE_BUCKETS else "blended"


def _profile_hint_from_chart(chart_meta: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(chart_meta, dict):
        return None
    raw = str(chart_meta.get("profile_hint") or "").strip().lower()
    if raw in PROFILE_BUCKETS:
        return raw
    return None


def _normalize_engine_point_name(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered in LILITH_ALIASES:
        return LILITH_ALIASES[lowered]
    return _normalize_point_name(raw)


def _norm360(value: float) -> float:
    return float(value) % 360.0


def _sign_index(sign: str) -> Optional[int]:
    try:
        return SIGN_NAMES.index(str(sign or ""))
    except ValueError:
        return None


def _point_glyph(name: str) -> str:
    return str(POINT_GLYPHS.get(str(name or "").strip()) or "")


def _aspect_glyph(name: str) -> str:
    return str(ASPECT_GLYPHS.get(str(name or "").strip()) or "•")


def _element_of_point(point: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(point, dict):
        return None
    sign_name = str(point.get("sign") or "").strip()
    return SIGN_TO_ELEMENT.get(sign_name)


def _bucket_counts_by_element(names: Sequence[str], points: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    counts = {element: 0 for element in ELEMENT_ORDER}
    for name in dict.fromkeys(str(item) for item in names if str(item or "").strip()):
        point = points.get(name)
        element = _element_of_point(point)
        if element in counts:
            counts[element] += 1
    return counts


def _bucket_counts_by_house(names: Sequence[str], points: Dict[str, Dict[str, Any]]) -> Dict[int, int]:
    counts = {house: 0 for house in range(1, 13)}
    for name in dict.fromkeys(str(item) for item in names if str(item or "").strip()):
        point = points.get(name)
        house = int(point.get("house") or 0) if isinstance(point, dict) else 0
        if 1 <= house <= 12:
            counts[house] += 1
    return counts


def _element_compliance_counts(
    names: Sequence[str],
    points: Dict[str, Dict[str, Any]],
    other_names: Sequence[str],
    other_points: Dict[str, Dict[str, Any]],
) -> Dict[str, int]:
    counts = {element: 0 for element in ELEMENT_ORDER}
    other_elements = [
        element
        for element in (_element_of_point(other_points.get(name)) for name in dict.fromkeys(str(item) for item in other_names))
        if element
    ]
    if not other_elements:
        return counts
    for name in dict.fromkeys(str(item) for item in names if str(item or "").strip()):
        point = points.get(name)
        element = _element_of_point(point)
        if not element:
            continue
        if any((element, other_element) in ELEMENT_COMPATIBILITY for other_element in other_elements):
            counts[element] += 1
    return counts


def _row_logic_type(mode: Any) -> str:
    raw = str(mode or "").strip().lower()
    if raw == "explicit_aspect":
        return "explicit_aspect"
    if raw == "same_object_fallback":
        return "same_object_fallback"
    return "burdening_warning"


def _point_display_label(name: str, point: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    clean_name = str(name or "").strip()
    if not clean_name:
        return "", ""
    if clean_name.lower().startswith("h") and "cusp" in clean_name.lower():
        return clean_name, "House cusp warning"
    glyph = _point_glyph(clean_name)
    label = f"{glyph} {clean_name}".strip() if glyph else clean_name
    meta_parts: List[str] = []
    if isinstance(point, dict):
        house = int(point.get("house") or 0)
        sign = str(point.get("sign") or "").strip()
        if 1 <= house <= 12:
            meta_parts.append(f"H{house}")
        if sign:
            meta_parts.append(sign)
    return label, " · ".join(meta_parts)


def _warning_mid_display(anchor_name: str, detail: str) -> str:
    clean_anchor = str(anchor_name or "").strip()
    glyph = _point_glyph(clean_anchor)
    if not glyph and clean_anchor.lower().startswith("h") and "cusp" in clean_anchor.lower():
        glyph = "⌂"
    if "30th degree" in str(detail or ""):
        return f"{glyph or '⚠'}-30°"
    return f"{glyph or '⚠'}⚠"


def _compat_aspect_name(payload: Dict[str, Any]) -> str:
    return _normalize_local_aspect_name(payload.get("aspect_name") or payload.get("aspect"))


def _mid_display_for_row(
    row: Dict[str, Any],
    left_point: Optional[Dict[str, Any]],
    right_point: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    logic_type = _row_logic_type(row.get("mode"))
    left_name = str(row.get("left") or "").strip()
    right_name = str(row.get("right") or "").strip()
    if logic_type == "explicit_aspect":
        left_glyph = _point_glyph(left_name) or left_name
        right_glyph = _point_glyph(right_name) or right_name
        aspect_name = _compat_aspect_name(row)
        aspect_glyph = _aspect_glyph(aspect_name)
        return f"{left_glyph}{aspect_glyph}{right_glyph}", f"{left_name} {aspect_name} {right_name}".strip()
    if logic_type == "same_object_fallback":
        glyph = _point_glyph(left_name or right_name) or (left_name or right_name or "•")
        relation_glyph = FALLBACK_RESONANCE_GLYPHS.get(int(row.get("score") or 0), "≈")
        return f"{glyph}{relation_glyph}{glyph}", str(row.get("label") or "Sign resonance")
    anchor_name = left_name or right_name
    return _warning_mid_display(anchor_name, str(row.get("detail") or "")), str(row.get("detail") or row.get("label") or "Warning")


def _serialize_structured_row(
    row: Dict[str, Any],
    *,
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    left_name = str(row.get("left") or "").strip()
    right_name = str(row.get("right") or "").strip()
    left_point = points_a.get(left_name) or points_b.get(left_name)
    right_point = points_b.get(right_name) or points_a.get(right_name)
    left_label, left_meta = _point_display_label(left_name, left_point)
    right_label, right_meta = _point_display_label(right_name, right_point)
    mid_raw, mid_semantic = _mid_display_for_row(row, left_point, right_point)
    return {
        "label": row.get("label"),
        "detail": row.get("detail"),
        "score": int(row.get("score") or 0),
        "aspect_name": _compat_aspect_name(row) if _row_logic_type(row.get("mode")) == "explicit_aspect" else row.get("aspect_name"),
        "orb": row.get("orb"),
        "mode": row.get("mode"),
        "logic_type": _row_logic_type(row.get("mode")),
        "left": left_name,
        "right": right_name,
        "left_label": left_label,
        "right_label": right_label,
        "left_meta": left_meta,
        "right_meta": right_meta,
        "mid_raw": mid_raw,
        "mid_semantic": mid_semantic,
        "layer": row.get("layer"),
    }


def _same_object_fallback_score(point_a: Dict[str, Any], point_b: Dict[str, Any]) -> int:
    idx_a = _sign_index(str(point_a.get("sign") or ""))
    idx_b = _sign_index(str(point_b.get("sign") or ""))
    if idx_a is None or idx_b is None:
        return 0
    diff = abs(idx_a - idx_b) % 12
    diff = min(diff, 12 - diff)
    if diff == 0:
        return 3
    if diff == 6:
        return 1
    if diff in {1, 5}:
        return -3
    return 0


def _longitude_in_arc(start: float, end: float, point: float) -> bool:
    start = _norm360(start)
    end = _norm360(end)
    point = _norm360(point)
    if start <= end:
        return start <= point < end
    return point >= start or point < end


def _house_of_longitude(lon: float, cusps: Sequence[float]) -> Optional[int]:
    if len(cusps) < 12:
        return None
    for idx in range(12):
        if _longitude_in_arc(cusps[idx], cusps[(idx + 1) % 12], lon):
            return idx + 1
    return None


def _aspect_base_value(aspect_name: str, left_name: str, right_name: str) -> int:
    pair = {left_name, right_name}
    if aspect_name == "Conjunction":
        if "Saturn" in pair:
            return -7
        if pair & OUTER_PLANETS:
            return -9
        return 9
    if aspect_name == "Trine":
        return 8
    if aspect_name == "Sextile":
        return 4
    if aspect_name == "Opposition":
        if "Saturn" in pair:
            return -4
        if pair & OUTER_PLANETS:
            return -6
        return 6
    if aspect_name == "Square":
        return -8
    if aspect_name in {"Semisquare", "Sesquiquadrate"}:
        return -2
    if aspect_name in {"Semisextile", "Quincunx"}:
        return -1
    return -1


def _object_weight(name: str, aspect_name: str) -> int:
    if name in {"Sun", "Moon"}:
        return 9
    if name in {"Mercury", "Venus", "Mars"}:
        return 7
    if name in {"Jupiter", "Saturn"}:
        return 8
    if name in OUTER_PLANETS:
        if aspect_name == "Conjunction":
            return 6
        if aspect_name in {"Square", "Trine"}:
            return 5
        if aspect_name == "Sextile":
            return 3
        if aspect_name == "Opposition":
            return 4
        if aspect_name in {"Semisquare", "Sesquiquadrate"}:
            return 2
        return 1
    return 1


def _explicit_aspect_score(aspect: Dict[str, Any]) -> int:
    aspect_name = _compat_aspect_name(aspect)
    point_a = str(aspect.get("point_a") or "")
    point_b = str(aspect.get("point_b") or "")
    base = _aspect_base_value(aspect_name, point_a, point_b)
    sign = 1 if base >= 0 else -1
    magnitude = abs(base)
    weight_a = _object_weight(point_a, aspect_name)
    weight_b = _object_weight(point_b, aspect_name)
    scaled = math.sqrt((weight_a * magnitude / 9.0) * (weight_b * magnitude / 9.0))
    return int(scaled * sign)


def _aspect_lookup(aspects: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for aspect in aspects:
        key = (str(aspect.get("point_a") or ""), str(aspect.get("point_b") or ""))
        if not key[0] or not key[1]:
            continue
        current = lookup.get(key)
        if current is None or float(aspect.get("orb") or 99.0) < float(current.get("orb") or 99.0):
            lookup[key] = aspect
    return lookup


def _value_to_int(value: float) -> int:
    return int(round(float(value or 0.0)))


def _normalize_local_aspect_name(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    if "conj" in text:
        return "Conjunction"
    if "oppo" in text:
        return "Opposition"
    if "trine" in text:
        return "Trine"
    if "semi sext" in text or text == "semisextile":
        return "Semisextile"
    if "semi square" in text or text == "semisquare":
        return "Semisquare"
    if "sesqui" in text:
        return "Sesquiquadrate"
    if "square" in text:
        return "Square"
    if "sext" in text:
        return "Sextile"
    if "quinc" in text:
        return "Quincunx"
    return str(value or "").strip()


def _chart_aspect_rows(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("planetary_aspects_precise", "planetary_aspects", "aspects"):
        value = chart_data.get(key)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
    return []


def _chart_planet_rows(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    planets = chart_data.get("planets") or []
    if isinstance(planets, list):
        return [dict(item) for item in planets if isinstance(item, dict)]
    if isinstance(planets, dict):
        rows: List[Dict[str, Any]] = []
        for name, payload in planets.items():
            if not isinstance(payload, dict):
                continue
            row = dict(payload)
            row.setdefault("planet", str(name))
            rows.append(row)
        return rows
    return []


def _all_local_aspects(points: Dict[str, Dict[str, Any]], options: Dict[str, Any]) -> List[Dict[str, Any]]:
    names = list(points.keys())
    hits: List[Dict[str, Any]] = []
    for idx, name_a in enumerate(names):
        for name_b in names[idx + 1:]:
            point_a = points.get(name_a)
            point_b = points.get(name_b)
            if not point_a or not point_b:
                continue
            delta = _angular_distance(float(point_a["longitude"]), float(point_b["longitude"]))
            aspect = _find_best_aspect(delta, point_a, point_b, options)
            if not aspect:
                continue
            hits.append({"point_a": name_a, "point_b": name_b, "aspect_name": aspect.get("aspect")})
    return hits


def _local_aspect_index(
    chart_data: Dict[str, Any],
    points: Dict[str, Dict[str, Any]],
    options: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    index: Dict[str, List[Dict[str, Any]]] = {}
    raw_rows = _chart_aspect_rows(chart_data)
    if raw_rows:
        for row in raw_rows:
            point_a = _normalize_engine_point_name(
                row.get("planet1") or row.get("point_a") or row.get("left") or row.get("source")
            )
            point_b = _normalize_engine_point_name(
                row.get("planet2") or row.get("point_b") or row.get("right") or row.get("target")
            )
            aspect_name = _normalize_local_aspect_name(row.get("aspect") or row.get("aspect_name") or row.get("sasp"))
            if not point_a or not point_b or not aspect_name:
                continue
            payload = {"point_a": point_a, "point_b": point_b, "aspect_name": aspect_name}
            index.setdefault(point_a, []).append(payload)
            index.setdefault(point_b, []).append(payload)
        return index

    for hit in _all_local_aspects(points, options):
        point_a = str(hit.get("point_a") or "")
        point_b = str(hit.get("point_b") or "")
        aspect_name = str(hit.get("aspect_name") or hit.get("aspect") or "")
        if not point_a or not point_b or not aspect_name:
            continue
        payload = {"point_a": point_a, "point_b": point_b, "aspect_name": aspect_name}
        index.setdefault(point_a, []).append(payload)
        index.setdefault(point_b, []).append(payload)
    return index


def _cusp_zodiac_id(chart_data: Dict[str, Any], house: int) -> Optional[int]:
    cusps = _house_cusps(chart_data)
    if len(cusps) < int(house):
        return None
    return int(float(cusps[int(house) - 1]) % 360.0 // 30.0) % 12


def _build_engine_points(chart_data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    points = _build_points(chart_data or {}, options)
    cusps = _house_cusps(chart_data)
    for row in _chart_planet_rows(chart_data):
        name = _normalize_engine_point_name(row.get("planet") or row.get("name"))
        if name != "Lilith" or name in points:
            continue
        lon = row.get("longitude")
        try:
            longitude = _norm360(float(lon))
        except Exception:
            continue
        house = row.get("house")
        try:
            house_num = int(house) if house is not None else None
        except Exception:
            house_num = None
        if (house_num is None or not (1 <= house_num <= 12)) and cusps:
            house_num = _house_of_longitude(longitude, cusps)
        points[name] = {
            "name": name,
            "longitude": longitude,
            "sign": str(row.get("sign") or SIGN_NAMES[int(longitude // 30.0) % 12]),
            "house": house_num,
            "speed": row.get("speed"),
            "retrograde": bool(row.get("retrograde")),
            "class": "other",
            "degree_in_sign": row.get("degree_in_sign"),
        }
    return points


def _is_cosmogram(chart_data: Dict[str, Any]) -> bool:
    for key in ("cosmogram", "is_cosmogram"):
        if chart_data.get(key) is True:
            return True
    return False


def _house_group(points: Dict[str, Dict[str, Any]], chart_data: Dict[str, Any], house: int) -> List[str]:
    if _is_cosmogram(chart_data):
        return []
    cusps = _house_cusps(chart_data)
    idx = int(house) - 1
    if idx < 0 or len(cusps) < 12:
        return []
    start_sign = int(float(cusps[idx]) % 360.0 // 30.0) % 12
    end_sign = int(float(cusps[(idx + 1) % 12]) % 360.0 // 30.0) % 12
    if start_sign == end_sign:
        ruler = _normalize_engine_point_name(SIGN_RULER.get(SIGN_NAMES[start_sign]))
        return [ruler] if ruler and ruler in points else []

    limit = end_sign if end_sign >= start_sign else end_sign + 12
    names: List[str] = []
    for sign_idx in range(start_sign, limit + 1):
        sign_name = SIGN_NAMES[sign_idx % 12]
        ruler = _normalize_engine_point_name(SIGN_RULER.get(sign_name))
        if ruler and ruler in points and ruler not in names:
            names.append(ruler)
    return names


def _match_pair_row(
    *,
    section_id: str,
    layer: str,
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    aspect_lookup: Dict[Tuple[str, str], Dict[str, Any]],
    left_name: str,
    right_name: str,
    detail: str,
) -> Optional[Dict[str, Any]]:
    point_a = points_a.get(left_name)
    point_b = points_b.get(right_name)
    if not point_a or not point_b:
        return None
    aspect = aspect_lookup.get((left_name, right_name))
    if aspect is not None:
        aspect_name = _compat_aspect_name(aspect)
        score = _explicit_aspect_score(aspect)
        return {
            "section_id": section_id,
            "layer": layer,
            "left": left_name,
            "right": right_name,
            "label": f"{left_name} {aspect_name} {right_name}",
            "detail": detail,
            "score": score,
            "orb": round(float(aspect.get("orb") or 0.0), 2),
            "aspect_name": aspect_name,
            "mode": "explicit_aspect",
        }
    if left_name == right_name:
        score = _same_object_fallback_score(point_a, point_b)
        if score:
            return {
                "section_id": section_id,
                "layer": layer,
                "left": left_name,
                "right": right_name,
                "label": f"{left_name} sign resonance",
                "detail": detail,
                "score": score,
                "orb": None,
                "aspect_name": None,
                "mode": "same_object_fallback",
            }
    return None


def _top_notes(rows: Sequence[Dict[str, Any]], limit: int = 2) -> List[str]:
    ordered = sorted(rows, key=lambda item: (-abs(int(item.get("score") or 0)), str(item.get("label") or "")))
    notes: List[str] = []
    for row in ordered[:limit]:
        detail = str(row.get("detail") or row.get("label") or "").strip()
        if detail:
            notes.append(detail)
    return notes


def _section_item(
    *,
    item_id: str,
    label: str,
    score: int,
    summary: str,
    rows: Sequence[Dict[str, Any]],
    extra: Optional[Dict[str, Any]] = None,
    points_a: Optional[Dict[str, Dict[str, Any]]] = None,
    points_b: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    positive_count = sum(1 for row in rows if int(row.get("score") or 0) > 0)
    negative_count = sum(1 for row in rows if int(row.get("score") or 0) < 0)
    item = {
        "id": item_id,
        "label": label,
        "score": score,
        "summary": summary,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "row_count": len(list(rows)),
        "notes": _top_notes(rows),
    }
    if points_a is not None and points_b is not None:
        item["rows"] = _structured_event_rows(rows, points_a=points_a, points_b=points_b, limit=None)
    if extra:
        item.update(extra)
    return item


def _structured_event_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    limit: Optional[int] = 36,
) -> List[Dict[str, Any]]:
    ordered = sorted(rows, key=lambda item: (-abs(int(item.get("score") or 0)), float(item.get("orb") or 99.0)))
    if limit is not None:
        ordered = ordered[: int(limit)]
    return [_serialize_structured_row(row, points_a=points_a, points_b=points_b) for row in ordered]


def _shared_contact_rows(aspects: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for aspect in aspects:
        aspect_name = _compat_aspect_name(aspect)
        score = _explicit_aspect_score(aspect)
        rows.append(
            {
                "label": f"{aspect.get('point_a')} {aspect_name} {aspect.get('point_b')}",
                "detail": f"orb {round(float(aspect.get('orb') or 0.0), 2)}",
                "score": score,
                "aspect_name": aspect_name,
                "orb": round(float(aspect.get("orb") or 0.0), 2),
                "mode": "explicit_aspect",
                "left": aspect.get("point_a"),
                "right": aspect.get("point_b"),
                "layer": "shared",
            }
        )
    return rows


def _summarize_structure(
    *,
    items: Sequence[Dict[str, Any]],
    burden_rows: Sequence[Dict[str, Any]],
    contact_rows: Sequence[Dict[str, Any]],
    engine_label: str,
    items_include_burden: bool = False,
) -> Dict[str, Any]:
    burden_total = sum(int(row.get("score") or 0) for row in burden_rows)
    theme_total = sum(int(item.get("score") or 0) for item in items)
    if not items_include_burden:
        theme_total += burden_total
    aspect_total = sum(int(row.get("score") or 0) for row in contact_rows)
    composite_total = theme_total + aspect_total
    ordered = sorted(items, key=lambda item: int(item.get("score") or 0), reverse=True)
    strongest = ordered[0] if ordered else None
    weakest = ordered[-1] if ordered else None
    summary_lines: List[str] = []
    if strongest:
        summary_lines.append(f"Strongest area: {strongest.get('label')} ({int(strongest.get('score') or 0):+d}).")
    if weakest and weakest is not strongest:
        summary_lines.append(f"Most difficult area: {weakest.get('label')} ({int(weakest.get('score') or 0):+d}).")
    if burden_rows:
        summary_lines.append(f"Pressure rows: {len(burden_rows)} warnings are active.")
    if contact_rows:
        summary_lines.append(f"Shared contact grid: {len(contact_rows)} scored cross-aspects.")
    return {
        "engine_title": engine_label,
        "theme_total": theme_total,
        "aspect_total": aspect_total,
        "burden_total": burden_total,
        "composite_total": composite_total,
        "positive_item_count": sum(1 for item in items if int(item.get("score") or 0) > 0),
        "negative_item_count": sum(1 for item in items if int(item.get("score") or 0) < 0),
        "summary_lines": summary_lines,
    }


def _bounded_sigmoid_score(value: float, *, center: float, scale: float) -> int:
    safe_scale = abs(float(scale or 1.0)) or 1.0
    exponent = -((float(value) - float(center)) / safe_scale)
    return int(round(max(0.0, min(100.0, 100.0 / (1.0 + math.exp(exponent))))))


def _work_alliance_durability_check(summary: Dict[str, Any]) -> Dict[str, Any]:
    theme_total = int(summary.get("theme_total") or 0)
    aspect_total = int(summary.get("aspect_total") or 0)
    burden_total = int(summary.get("burden_total") or 0)
    composite_total = int(summary.get("composite_total") or 0)
    weighted_raw = (0.65 * float(theme_total)) + (0.35 * float(aspect_total))
    score = _bounded_sigmoid_score(weighted_raw, center=12.0, scale=18.0)

    if score >= 82 and burden_total >= -15:
        signal = "durable_success_lean"
        label = "durable signal"
        title = "Durable collaboration signal"
        body = (
            "The business-house foundation stays net-positive and the pressure layer is not "
            "overwhelming, so the pair reads as more able to hold useful cooperation over time."
        )
    elif score >= 66:
        signal = "productive_but_exposed"
        label = "productive, but exposed"
        title = "Productive with visible stress"
        body = (
            "The pair can still build or execute together, but the pressure layer is active "
            "enough that durability looks earned rather than effortless."
        )
    elif score >= 45:
        signal = "mixed_durability"
        label = "mixed durability"
        title = "Capable, but not naturally stable"
        body = (
            "The collaboration can function, but the business structure does not read as "
            "self-stabilizing. It may work in phases more easily than it holds cleanly."
        )
    else:
        signal = "breakdown_prone"
        label = "breakdown-prone"
        title = "Breakdown-prone pattern"
        body = (
            "Pressure and business-theme drag are overtaking the cooperative layer, so the "
            "pair reads as more vulnerable to fracture than to durable alignment."
        )

    notes: List[str] = []
    if theme_total >= 20:
        notes.append("The business-house foundation is clearly net-positive.")
    elif theme_total >= 0:
        notes.append("The business-house foundation is positive, but not emphatic.")
    else:
        notes.append("The business-house foundation is net-negative.")

    if aspect_total > 0:
        notes.append("Shared contact rows are still adding collaborative traction.")
    else:
        notes.append("The contact layer is not doing enough corrective work.")

    if burden_total <= -18:
        notes.append("Pressure rows are materially subtracting from long-run stability.")
    elif burden_total < 0:
        notes.append("Pressure is present, but not dominant.")
    else:
        notes.append("Pressure rows are not dominating the current business picture.")

    return {
        "id": "work_durability_v1",
        "label": label,
        "signal": signal,
        "score": score,
        "weighted_raw": round(weighted_raw, 2),
        "theme_total": theme_total,
        "aspect_total": aspect_total,
        "burden_total": burden_total,
        "composite_total": composite_total,
        "title": title,
        "body": body,
        "notes": notes,
    }


def _area_bucket_payload(
    *,
    bucket_id: str,
    label: str,
    glyph: str,
    primary_value: int,
    secondary_value: int,
) -> Dict[str, Any]:
    return {
        "id": bucket_id,
        "label": label,
        "glyph": glyph,
        "primary_value": int(primary_value),
        "secondary_value": int(secondary_value),
    }


def _areas_payload(
    *,
    chart_label_a: str,
    chart_label_b: str,
    direct_pool_a: Sequence[str],
    role_pool_a: Sequence[str],
    direct_pool_b: Sequence[str],
    role_pool_b: Sequence[str],
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    direct_element_a = _bucket_counts_by_element(direct_pool_a, points_a)
    role_element_a = _bucket_counts_by_element(role_pool_a, points_a)
    direct_element_b = _bucket_counts_by_element(direct_pool_b, points_b)
    role_element_b = _bucket_counts_by_element(role_pool_b, points_b)
    thematic_pool_a = list(dict.fromkeys([*direct_pool_a, *role_pool_a]))
    thematic_pool_b = list(dict.fromkeys([*direct_pool_b, *role_pool_b]))
    compliance_a = _element_compliance_counts(thematic_pool_a, points_a, thematic_pool_b, points_b)
    compliance_b = _element_compliance_counts(thematic_pool_b, points_b, thematic_pool_a, points_a)
    house_counts_a = _bucket_counts_by_house(thematic_pool_a, points_a)
    house_counts_b = _bucket_counts_by_house(thematic_pool_b, points_b)
    stripes = [
        {
            "id": "subject_a_elements",
            "label": f"{chart_label_a} thematic elements",
            "description": "Direct-object pool against role-group pool for the left-side chart.",
            "bucket_kind": "element",
            "primary_label": "Direct",
            "secondary_label": "Role",
            "buckets": [
                _area_bucket_payload(
                    bucket_id=ELEMENT_META[element]["id"],
                    label=ELEMENT_META[element]["label"],
                    glyph=ELEMENT_META[element]["glyph"],
                    primary_value=direct_element_a[element],
                    secondary_value=role_element_a[element],
                )
                for element in ELEMENT_ORDER
            ],
        },
        {
            "id": "subject_b_elements",
            "label": f"{chart_label_b} thematic elements",
            "description": "Direct-object pool against role-group pool for the right-side chart.",
            "bucket_kind": "element",
            "primary_label": "Direct",
            "secondary_label": "Role",
            "buckets": [
                _area_bucket_payload(
                    bucket_id=ELEMENT_META[element]["id"],
                    label=ELEMENT_META[element]["label"],
                    glyph=ELEMENT_META[element]["glyph"],
                    primary_value=direct_element_b[element],
                    secondary_value=role_element_b[element],
                )
                for element in ELEMENT_ORDER
            ],
        },
        {
            "id": "element_compliance",
            "label": "Element compliance",
            "description": "How often each chart's selected thematic pool finds a compatible elemental counterweight in the other chart.",
            "bucket_kind": "element",
            "primary_label": chart_label_a,
            "secondary_label": chart_label_b,
            "buckets": [
                _area_bucket_payload(
                    bucket_id=f"{ELEMENT_META[element]['id']}_fit",
                    label=ELEMENT_META[element]["label"],
                    glyph=ELEMENT_META[element]["glyph"],
                    primary_value=compliance_a[element],
                    secondary_value=compliance_b[element],
                )
                for element in ELEMENT_ORDER
            ],
        },
        {
            "id": "house_importance",
            "label": "House importance",
            "description": "Thematic pool distribution by natal house across both sides.",
            "bucket_kind": "house",
            "primary_label": chart_label_a,
            "secondary_label": chart_label_b,
            "buckets": [
                _area_bucket_payload(
                    bucket_id=f"house_{house}",
                    label=HOUSE_ROMAN[house - 1],
                    glyph=HOUSE_ROMAN[house - 1],
                    primary_value=house_counts_a[house],
                    secondary_value=house_counts_b[house],
                )
                for house in range(1, 13)
            ],
        },
    ]
    for stripe in stripes:
        max_value = 0
        for bucket in stripe["buckets"]:
            max_value = max(max_value, int(bucket["primary_value"]), int(bucket["secondary_value"]))
        stripe["max_value"] = int(max_value)
    return {
        "label": "Areas Diagram",
        "description": "Four stripe graphs based on the structured engine's selected thematic pools.",
        "stripes": stripes,
    }


def _pool_names_from_rows(rows: Sequence[Dict[str, Any]], side: str) -> List[str]:
    key = "left" if str(side) == "left" else "right"
    ordered: List[str] = []
    for row in rows:
        name = str(row.get(key) or "").strip()
        if name:
            ordered.append(name)
    return list(dict.fromkeys(ordered))


def _pool_names_from_items(items: Sequence[Dict[str, Any]], side: str, *, layers: Sequence[str]) -> List[str]:
    allowed = {str(layer) for layer in layers}
    ordered: List[str] = []
    for item in items:
        for row in item.get("rows") or []:
            if str(row.get("layer") or "") not in allowed:
                continue
            name = str(row.get("left") if side == "left" else row.get("right") or "").strip()
            if name:
                ordered.append(name)
    return list(dict.fromkeys(ordered))


def _exact_degree_warning(point: Dict[str, Any]) -> bool:
    raw = point.get("degree_in_sign")
    try:
        degree = float(raw)
    except Exception:
        degree = float(point.get("longitude") or 0.0) % 30.0
    return math.isclose(degree, 30.0, abs_tol=1e-6)


def _warning_row(
    side_label: str,
    point_name: str,
    detail: str,
    layer: str = "burden",
    *,
    anchor_side: str,
) -> Dict[str, Any]:
    if str(anchor_side) == "left":
        left_name = point_name
        right_name = ""
    else:
        left_name = ""
        right_name = point_name
    return {
        "label": f"{side_label}: {point_name}",
        "detail": detail,
        "score": -3,
        "aspect_name": None,
        "orb": None,
        "mode": "burden_warning",
        "left": left_name,
        "right": right_name,
        "side_label": side_label,
        "layer": layer,
    }


def _dedupe_warning_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("label") or ""), str(row.get("detail") or ""), str(row.get("layer") or ""))
        deduped.setdefault(key, row)
    return list(deduped.values())


def _house_occupants(points: Dict[str, Dict[str, Any]], house: int) -> List[str]:
    names: List[str] = []
    for name, point in points.items():
        if int(point.get("house") or 0) == int(house):
            names.append(name)
    return names


def _pool_burden_rows(
    *,
    chart_data_a: Dict[str, Any],
    chart_data_b: Dict[str, Any],
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    natal_unaspected_a: Set[str],
    natal_unaspected_b: Set[str],
    pool_a: Sequence[str],
    pool_b: Sequence[str],
    target_houses: Sequence[int],
    layer: str,
    options: Dict[str, Any],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    target_house_set = {int(value) for value in target_houses}
    for side_label, chart_data, points, natal_unaspected, pool_names in (
        ("Snap A", chart_data_a, points_a, natal_unaspected_a, pool_a),
        ("Snap B", chart_data_b, points_b, natal_unaspected_b, pool_b),
    ):
        anchor_side = "left" if side_label == "Snap A" else "right"
        local_aspects = _local_aspect_index(chart_data, points, options)
        for house in target_house_set:
            if _cusp_zodiac_id(chart_data, house) == 9:
                rows.append(
                    _warning_row(
                        side_label,
                        f"H{house} cusp",
                        f"Warning house {house} cusp is in zodiac id 9.",
                        layer,
                        anchor_side=anchor_side,
                    )
                )
        for name in dict.fromkeys(str(item) for item in pool_names):
            point = points.get(name)
            if not point:
                continue
            point_house = int(point.get("house") or 0)
            local_hits = local_aspects.get(name) or []
            isolated = name in natal_unaspected or not local_hits
            if name in PRESSURE_PLANETS and point_house in target_house_set:
                rows.append(_warning_row(side_label, name, f"{name} occupies warning house {point_house}.", layer, anchor_side=anchor_side))
            if _exact_degree_warning(point):
                rows.append(_warning_row(side_label, name, f"{name} is at the exact 30th degree in-sign.", layer, anchor_side=anchor_side))
            if isolated:
                rows.append(_warning_row(side_label, name, f"{name} has no local aspects inside the active burden pool.", layer, anchor_side=anchor_side))
                for hit in local_hits:
                    point_a = str(hit.get("point_a") or "")
                    point_b = str(hit.get("point_b") or "")
                    other_name = point_b if point_a == name else point_a
                    aspect_name = str(hit.get("aspect_name") or "")
                    if other_name not in {"Uranus", "Pluto"} or aspect_name not in WORK_HARD_LOCAL_ASPECTS:
                        continue
                    rows.append(
                        _warning_row(
                            side_label,
                            name,
                            f"{name} has a hard local {aspect_name.lower()} to {other_name} while otherwise isolated.",
                            layer,
                            anchor_side=anchor_side,
                        )
                    )
    return _dedupe_warning_rows(rows)


def _overall_burden_pool(chart_data: Dict[str, Any], points: Dict[str, Dict[str, Any]], *, anchor_house: int, anchor_angle: str) -> List[str]:
    names: List[str] = [name for name in CORE_AND_MODERN if name in points]
    if anchor_angle in points:
        names.append(anchor_angle)
    names.extend(_house_group(points, chart_data, anchor_house))
    names.extend(_house_occupants(points, anchor_house))
    for house in range(1, 13):
        names.extend(_house_group(points, chart_data, house))
    return list(dict.fromkeys(name for name in names if name in points))


def _overall_burden_rows(
    *,
    chart_data_a: Dict[str, Any],
    chart_data_b: Dict[str, Any],
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    natal_unaspected_a: Set[str],
    natal_unaspected_b: Set[str],
    options: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return _pool_burden_rows(
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        natal_unaspected_a=natal_unaspected_a,
        natal_unaspected_b=natal_unaspected_b,
        pool_a=_overall_burden_pool(chart_data_a, points_a, anchor_house=1, anchor_angle="Ascendant"),
        pool_b=_overall_burden_pool(chart_data_b, points_b, anchor_house=7, anchor_angle="Descendant"),
        target_houses=tuple(range(1, 13)),
        layer="burden",
        options=options,
    )


def _work_alliance_burden_rows(
    *,
    chart_data_a: Dict[str, Any],
    chart_data_b: Dict[str, Any],
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    natal_unaspected_a: Set[str],
    natal_unaspected_b: Set[str],
    options: Dict[str, Any],
) -> List[Dict[str, Any]]:
    def _pool(side_label: str, chart_data: Dict[str, Any], points: Dict[str, Dict[str, Any]]) -> List[str]:
        names: List[str] = [name for name in WORK_BURDEN_SEEDS[side_label] if name in points]
        for house in WORK_HOUSES:
            names.extend(_house_group(points, chart_data, int(house)))
        return list(dict.fromkeys(name for name in names if name in points))

    return _pool_burden_rows(
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        natal_unaspected_a=natal_unaspected_a,
        natal_unaspected_b=natal_unaspected_b,
        pool_a=_pool("Snap A", chart_data_a, points_a),
        pool_b=_pool("Snap B", chart_data_b, points_b),
        target_houses=WORK_WARNING_HOUSES,
        layer="burden",
        options=options,
    )


def _build_life_theme_items(
    *,
    chart_data_a: Dict[str, Any],
    chart_data_b: Dict[str, Any],
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    aspect_lookup: Dict[Tuple[str, str], Dict[str, Any]],
    houses: Sequence[int],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    role_enabled = not (_is_cosmogram(chart_data_a) or _is_cosmogram(chart_data_b))
    for house in houses:
        meta = HOUSE_THEME_META[int(house)]
        direct_rows: List[Dict[str, Any]] = []
        role_rows: List[Dict[str, Any]] = []
        for left_name, right_name in OVERALL_DIRECT_PAIRS[int(house)]:
            row = _match_pair_row(
                section_id=meta["id"],
                layer="direct",
                points_a=points_a,
                points_b=points_b,
                aspect_lookup=aspect_lookup,
                left_name=left_name,
                right_name=right_name,
                detail=f"Direct psychology pair for house {house}.",
            )
            if row is not None:
                direct_rows.append(row)

        if role_enabled:
            left_house_group = _house_group(points_a, chart_data_a, int(house))
            right_house_group = _house_group(points_b, chart_data_b, int(house))
            self_a_group = _house_group(points_a, chart_data_a, 1)
            self_b_group = _house_group(points_b, chart_data_b, 1)
            role_pairs = [(self_b_group, left_house_group, "H1(chart1) <-> Hn(chart0)")]
            if int(house) != 1:
                role_pairs.append((right_house_group, self_a_group, "Hn(chart1) <-> H1(chart0)"))

            seen_role_keys: Set[Tuple[str, str, str]] = set()
            for chart1_group, chart0_group, detail in role_pairs:
                for chart1_name in chart1_group:
                    for chart0_name in chart0_group:
                        row = _match_pair_row(
                            section_id=meta["id"],
                            layer="role",
                            points_a=points_a,
                            points_b=points_b,
                            aspect_lookup=aspect_lookup,
                            left_name=chart0_name,
                            right_name=chart1_name,
                            detail=f"{detail} for house {house}.",
                        )
                        if row is None:
                            continue
                        dedupe_key = (chart0_name, chart1_name, detail)
                        if dedupe_key in seen_role_keys:
                            continue
                        seen_role_keys.add(dedupe_key)
                        role_rows.append(row)

        all_rows = [*direct_rows, *role_rows]
        score = sum(int(row.get("score") or 0) for row in all_rows)
        summary = f"Self-to-theme exchange for house {house}."
        items.append(
            _section_item(
                item_id=meta["id"],
                label=meta["label"],
                score=score,
                summary=summary,
                rows=all_rows,
                points_a=points_a,
                points_b=points_b,
                extra={
                    "house": int(house),
                    "direct_score": sum(int(row.get("score") or 0) for row in direct_rows),
                    "role_score": sum(int(row.get("score") or 0) for row in role_rows),
                },
            )
        )
    return items


def _union_pair_slots(profile_a: str, profile_b: str, family: str) -> List[Tuple[str, str]]:
    vector_map = UNION_157_VECTORS if str(family) == "157" else UNION_14_VECTORS
    sex_a = PROFILE_TO_SEX.get(profile_a)
    sex_b = PROFILE_TO_SEX.get(profile_b)
    if not sex_a or not sex_b:
        return []
    return list(zip(vector_map[sex_a], vector_map[sex_b]))


def _union_direct_pool_names(profile: str, family: str) -> List[str]:
    vector_map = UNION_157_VECTORS if str(family) == "157" else UNION_14_VECTORS
    sex = PROFILE_TO_SEX.get(profile)
    if sex:
        return list(dict.fromkeys(vector_map[sex]))
    if str(family) == "157":
        return ["Sun", "Moon", "Venus", "Mars", "Ascendant", "Descendant"]
    return ["Moon", "Saturn", "Sun"]


def _build_union_exact_rows(
    *,
    section_id: str,
    label: str,
    slot_pairs: Sequence[Tuple[str, str]],
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    aspect_lookup: Dict[Tuple[str, str], Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    for idx, (left_name, right_name) in enumerate(slot_pairs, start=1):
        row = _match_pair_row(
            section_id=section_id,
            layer="psychology",
            points_a=points_a,
            points_b=points_b,
            aspect_lookup=aspect_lookup,
            left_name=left_name,
            right_name=right_name,
            detail=f"{label} psychology slot {idx}.",
        )
        if row is not None:
            rows.append(row)
    score = sum(int(row.get("score") or 0) for row in rows)
    return (
        _section_item(
            item_id=section_id,
            label=label,
            score=score,
            summary=f"{label} psychology layer.",
            rows=rows,
            points_a=points_a,
            points_b=points_b,
            extra={"slot_count": len(slot_pairs), "logic_mode": "exact_slots"},
        ),
        rows,
    )


def _build_union_bucket_rows(
    *,
    section_id: str,
    label: str,
    left_bucket: Sequence[str],
    right_bucket: Sequence[str],
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    aspect_lookup: Dict[Tuple[str, str], Dict[str, Any]],
    limit: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    for left_name in left_bucket:
        for right_name in right_bucket:
            row = _match_pair_row(
                section_id=section_id,
                layer="psychology",
                points_a=points_a,
                points_b=points_b,
                aspect_lookup=aspect_lookup,
                left_name=left_name,
                right_name=right_name,
                detail=f"{label} psychology bucket match.",
            )
            if row is None:
                continue
            key = (left_name, right_name)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    rows = sorted(rows, key=lambda item: (-abs(int(item.get("score") or 0)), float(item.get("orb") or 99.0)))[:limit]
    score = sum(int(row.get("score") or 0) for row in rows)
    return (
        _section_item(
            item_id=section_id,
            label=label,
            score=score,
            summary=f"{label} psychology layer.",
            rows=rows,
            points_a=points_a,
            points_b=points_b,
            extra={"logic_mode": "blended_fallback"},
        ),
        rows,
    )


def _build_union_role_rows(
    *,
    section_id: str,
    label: str,
    chart_data_a: Dict[str, Any],
    chart_data_b: Dict[str, Any],
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    aspect_lookup: Dict[Tuple[str, str], Dict[str, Any]],
    comparisons: Sequence[Tuple[int, int, str]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if _is_cosmogram(chart_data_a) or _is_cosmogram(chart_data_b):
        return _section_item(
            item_id=section_id,
            label=label,
            score=0,
            summary=f"{label} role layer.",
            rows=[],
            points_a=points_a,
            points_b=points_b,
        ), []
    rows: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str, str]] = set()
    for house_b, house_a, detail in comparisons:
        left_group = _house_group(points_b, chart_data_b, int(house_b))
        right_group = _house_group(points_a, chart_data_a, int(house_a))
        for left_name in left_group:
            for right_name in right_group:
                row = _match_pair_row(
                    section_id=section_id,
                    layer="role",
                    points_a=points_a,
                    points_b=points_b,
                    aspect_lookup=aspect_lookup,
                    left_name=right_name,
                    right_name=left_name,
                    detail=detail,
                )
                if row is None:
                    continue
                dedupe_key = (right_name, left_name, detail)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                rows.append(row)
    score = sum(int(row.get("score") or 0) for row in rows)
    return _section_item(
        item_id=section_id,
        label=label,
        score=score,
        summary=f"{label} role layer.",
        rows=rows,
        points_a=points_a,
        points_b=points_b,
    ), rows


def _build_structured_report(
    *,
    engine_id: str,
    engine_label: str,
    chart_data_a: Dict[str, Any],
    chart_data_b: Dict[str, Any],
    chart_a: Dict[str, Any],
    chart_b: Dict[str, Any],
    options: Dict[str, Any],
    sections: Sequence[Dict[str, Any]],
    items: Sequence[Dict[str, Any]],
    burden_rows: Sequence[Dict[str, Any]],
    contact_rows: Sequence[Dict[str, Any]],
    profile_a: Optional[str] = None,
    profile_b: Optional[str] = None,
    known_gaps: Optional[Sequence[str]] = None,
    items_include_burden: bool = False,
    areas: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary = _summarize_structure(
        items=items,
        burden_rows=burden_rows,
        contact_rows=contact_rows,
        engine_label=engine_label,
        items_include_burden=items_include_burden,
    )
    governance = {
        "ordered_pair": True,
        "strict_source_parity": False,
        "point_availability": _point_availability(chart_data_a, chart_data_b),
        "orb_profile": options.get("orb_profile"),
        "known_gaps": list(known_gaps or []),
    }
    if profile_a is not None or profile_b is not None:
        governance["profile_mode"] = {
            "profile_a": profile_a or "blended",
            "profile_b": profile_b or "blended",
        }
    return {
        "report_kind": "structured",
        "engine_id": engine_id,
        "engine_label": engine_label,
        "available_engines": list_synastry_engines(),
        "summary": summary,
        "governance": governance,
        "options": options,
        "chart_a": chart_a,
        "chart_b": chart_b,
        "areas": dict(areas or {}),
        "sections": list(sections),
        "sources": _source_basis(),
    }


def _build_life_themes_report(
    *,
    bundle_a: Dict[str, Any],
    bundle_b: Dict[str, Any],
    chart_a: Dict[str, Any],
    chart_b: Dict[str, Any],
    options: Dict[str, Any],
    houses: Sequence[int],
    engine_id: str,
    engine_label: str,
    known_gaps: Sequence[str],
) -> Dict[str, Any]:
    chart_data_a = bundle_a.get("chart_data") or {}
    chart_data_b = bundle_b.get("chart_data") or {}
    points_a = _build_engine_points(chart_data_a, options)
    points_b = _build_engine_points(chart_data_b, options)
    aspects = _cross_aspects(points_a, points_b, options)
    aspect_lookup = _aspect_lookup(aspects)
    natal_unaspected_a = _natal_unaspected_points(points_a, options)
    natal_unaspected_b = _natal_unaspected_points(points_b, options)
    theme_items = _build_life_theme_items(
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        aspect_lookup=aspect_lookup,
        houses=houses,
    )
    burden_rows = _overall_burden_rows(
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        natal_unaspected_a=natal_unaspected_a,
        natal_unaspected_b=natal_unaspected_b,
        options=options,
    )
    contact_rows = _shared_contact_rows(aspects)
    direct_pool_a = _pool_names_from_items(theme_items, "left", layers=("direct",))
    role_pool_a = _pool_names_from_items(theme_items, "left", layers=("role",))
    direct_pool_b = _pool_names_from_items(theme_items, "right", layers=("direct",))
    role_pool_b = _pool_names_from_items(theme_items, "right", layers=("role",))
    sections = [
        {
            "id": "themes",
            "label": "Themes",
            "kind": "group_breakdown",
            "items": theme_items,
        },
        {
            "id": "pressure",
            "label": "Pressure",
            "kind": "event_rows",
            "items": _structured_event_rows(burden_rows, points_a=points_a, points_b=points_b, limit=24),
        },
        {
            "id": "contact_grid",
            "label": "Contact Grid",
            "kind": "event_rows",
            "items": _structured_event_rows(contact_rows, points_a=points_a, points_b=points_b, limit=32),
        },
    ]
    return _build_structured_report(
        engine_id=engine_id,
        engine_label=engine_label,
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        chart_a=chart_a,
        chart_b=chart_b,
        options=options,
        sections=sections,
        items=theme_items,
        burden_rows=burden_rows,
        contact_rows=contact_rows,
        known_gaps=known_gaps,
        areas=_areas_payload(
            chart_label_a=str(chart_a.get("label") or "Chart A"),
            chart_label_b=str(chart_b.get("label") or "Chart B"),
            direct_pool_a=direct_pool_a,
            role_pool_a=role_pool_a,
            direct_pool_b=direct_pool_b,
            role_pool_b=role_pool_b,
            points_a=points_a,
            points_b=points_b,
        ),
    )


def _build_work_alliance_report(
    *,
    bundle_a: Dict[str, Any],
    bundle_b: Dict[str, Any],
    chart_a: Dict[str, Any],
    chart_b: Dict[str, Any],
    options: Dict[str, Any],
) -> Dict[str, Any]:
    chart_data_a = bundle_a.get("chart_data") or {}
    chart_data_b = bundle_b.get("chart_data") or {}
    points_a = _build_engine_points(chart_data_a, options)
    points_b = _build_engine_points(chart_data_b, options)
    aspects = _cross_aspects(points_a, points_b, options)
    aspect_lookup = _aspect_lookup(aspects)
    natal_unaspected_a = _natal_unaspected_points(points_a, options)
    natal_unaspected_b = _natal_unaspected_points(points_b, options)
    theme_items = _build_life_theme_items(
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        aspect_lookup=aspect_lookup,
        houses=WORK_HOUSES,
    )
    burden_rows = _work_alliance_burden_rows(
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        natal_unaspected_a=natal_unaspected_a,
        natal_unaspected_b=natal_unaspected_b,
        options=options,
    )
    contact_rows = _shared_contact_rows(aspects)
    direct_pool_a = _pool_names_from_items(theme_items, "left", layers=("direct",))
    role_pool_a = _pool_names_from_items(theme_items, "left", layers=("role",))
    direct_pool_b = _pool_names_from_items(theme_items, "right", layers=("direct",))
    role_pool_b = _pool_names_from_items(theme_items, "right", layers=("role",))
    sections = [
        {
            "id": "themes",
            "label": "Themes",
            "kind": "group_breakdown",
            "items": theme_items,
        },
        {
            "id": "pressure",
            "label": "Pressure",
            "kind": "event_rows",
            "items": _structured_event_rows(burden_rows, points_a=points_a, points_b=points_b, limit=24),
        },
        {
            "id": "contact_grid",
            "label": "Contact Grid",
            "kind": "event_rows",
            "items": _structured_event_rows(contact_rows, points_a=points_a, points_b=points_b, limit=32),
        },
    ]
    report = _build_structured_report(
        engine_id="work_alliance",
        engine_label=_engine_meta("work_alliance")["label"],
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        chart_a=chart_a,
        chart_b=chart_b,
        options=options,
        sections=sections,
        items=theme_items,
        burden_rows=burden_rows,
        contact_rows=contact_rows,
        known_gaps=[
            "When saved chart data lacks natal aspect rows, the business burdening layer falls back to computed aspect availability for isolation warnings.",
            "Work Alliance parity is pinned to the decoded Basic tool fixture state; broader reversal and multi-instrument benchmark coverage is still pending.",
        ],
        areas=_areas_payload(
            chart_label_a=str(chart_a.get("label") or "Chart A"),
            chart_label_b=str(chart_b.get("label") or "Chart B"),
            direct_pool_a=direct_pool_a,
            role_pool_a=role_pool_a,
            direct_pool_b=direct_pool_b,
            role_pool_b=role_pool_b,
            points_a=points_a,
            points_b=points_b,
        ),
    )
    report["summary"]["durability_check"] = _work_alliance_durability_check(report.get("summary") or {})
    report["summary"]["summary_lines"] = [
        f"Durability check: {report['summary']['durability_check'].get('title')} ({int(report['summary']['durability_check'].get('score') or 0)}/100).",
        *list(report["summary"].get("summary_lines") or []),
    ]
    report["governance"]["outcome_model"] = "work_durability_v1"
    return report


def _union_burden_rows(
    *,
    family: str,
    chart_data_a: Dict[str, Any],
    chart_data_b: Dict[str, Any],
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    natal_unaspected_a: Set[str],
    natal_unaspected_b: Set[str],
    profile_a: str,
    profile_b: str,
    options: Dict[str, Any],
    layer: str,
) -> List[Dict[str, Any]]:
    if str(family) == "157":
        houses = (1, 5, 7)
    else:
        houses = (1, 4)

    def _pool(chart_data: Dict[str, Any], points: Dict[str, Dict[str, Any]], profile: str) -> List[str]:
        names: List[str] = _union_direct_pool_names(profile, family)
        for house in houses:
            names.extend(_house_group(points, chart_data, house))
        return list(dict.fromkeys(name for name in names if name in points))

    return _pool_burden_rows(
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        natal_unaspected_a=natal_unaspected_a,
        natal_unaspected_b=natal_unaspected_b,
        pool_a=_pool(chart_data_a, points_a, profile_a),
        pool_b=_pool(chart_data_b, points_b, profile_b),
        target_houses=(5,),
        layer=layer,
        options=options,
    )


def _build_union_dynamics_report(
    *,
    bundle_a: Dict[str, Any],
    bundle_b: Dict[str, Any],
    chart_a: Dict[str, Any],
    chart_b: Dict[str, Any],
    options: Dict[str, Any],
    profile_a: str,
    profile_b: str,
) -> Dict[str, Any]:
    chart_data_a = bundle_a.get("chart_data") or {}
    chart_data_b = bundle_b.get("chart_data") or {}
    points_a = _build_engine_points(chart_data_a, options)
    points_b = _build_engine_points(chart_data_b, options)
    aspects = _cross_aspects(points_a, points_b, options)
    aspect_lookup = _aspect_lookup(aspects)
    natal_unaspected_a = _natal_unaspected_points(points_a, options)
    natal_unaspected_b = _natal_unaspected_points(points_b, options)
    buckets_a = PROFILE_BUCKETS.get(profile_a) or PROFILE_BUCKETS["blended"]
    buckets_b = PROFILE_BUCKETS.get(profile_b) or PROFILE_BUCKETS["blended"]
    exact_bond_slots = _union_pair_slots(profile_a, profile_b, "157")
    exact_home_slots = _union_pair_slots(profile_a, profile_b, "14")

    if exact_bond_slots:
        bond_p_item, bond_p_rows = _build_union_exact_rows(
            section_id="alasp157P",
            label="Bond / Psychology",
            slot_pairs=exact_bond_slots,
            points_a=points_a,
            points_b=points_b,
            aspect_lookup=aspect_lookup,
        )
    else:
        bond_p_item, bond_p_rows = _build_union_bucket_rows(
            section_id="alasp157P",
            label="Bond / Psychology",
            left_bucket=buckets_a["a"] + buckets_a["b"],
            right_bucket=buckets_b["a"] + buckets_b["b"],
            points_a=points_a,
            points_b=points_b,
            aspect_lookup=aspect_lookup,
            limit=7,
        )
    bond_r_item, bond_r_rows = _build_union_role_rows(
        section_id="alasp157R",
        label="Bond / Role",
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        aspect_lookup=aspect_lookup,
        comparisons=(
            (1, 7, "H1(chart1) <-> H7(chart0)"),
            (7, 1, "H7(chart1) <-> H1(chart0)"),
            (1, 1, "H1(chart1) <-> H1(chart0)"),
            (1, 5, "H1(chart1) <-> H5(chart0)"),
            (5, 1, "H5(chart1) <-> H1(chart0)"),
            (5, 5, "H5(chart1) <-> H5(chart0)"),
        ),
    )
    bond_b_rows = _union_burden_rows(
        family="157",
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        natal_unaspected_a=natal_unaspected_a,
        natal_unaspected_b=natal_unaspected_b,
        profile_a=profile_a,
        profile_b=profile_b,
        options=options,
        layer="bond_burden",
    )
    bond_b_item = _section_item(
        item_id="alasp157B",
        label="Bond / Burdening",
        score=sum(int(row.get("score") or 0) for row in bond_b_rows),
        summary="Bond pressure warnings.",
        rows=bond_b_rows,
        points_a=points_a,
        points_b=points_b,
    )

    if exact_home_slots:
        home_p_item, home_p_rows = _build_union_exact_rows(
            section_id="alasp14P",
            label="Home / Psychology",
            slot_pairs=exact_home_slots,
            points_a=points_a,
            points_b=points_b,
            aspect_lookup=aspect_lookup,
        )
    else:
        home_p_item, home_p_rows = _build_union_bucket_rows(
            section_id="alasp14P",
            label="Home / Psychology",
            left_bucket=buckets_a["a"],
            right_bucket=buckets_b["a"],
            points_a=points_a,
            points_b=points_b,
            aspect_lookup=aspect_lookup,
            limit=6,
        )
    home_r_item, home_r_rows = _build_union_role_rows(
        section_id="alasp14R",
        label="Home / Role",
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        aspect_lookup=aspect_lookup,
        comparisons=(
            (1, 4, "H1(chart1) <-> H4(chart0)"),
            (4, 1, "H4(chart1) <-> H1(chart0)"),
            (4, 4, "H4(chart1) <-> H4(chart0)"),
        ),
    )
    home_b_rows = _union_burden_rows(
        family="14",
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        points_a=points_a,
        points_b=points_b,
        natal_unaspected_a=natal_unaspected_a,
        natal_unaspected_b=natal_unaspected_b,
        profile_a=profile_a,
        profile_b=profile_b,
        options=options,
        layer="home_burden",
    )
    home_b_item = _section_item(
        item_id="alasp14B",
        label="Home / Burdening",
        score=sum(int(row.get("score") or 0) for row in home_b_rows),
        summary="Home pressure warnings.",
        rows=home_b_rows,
        points_a=points_a,
        points_b=points_b,
    )

    items = [bond_p_item, bond_r_item, bond_b_item, home_p_item, home_r_item, home_b_item]
    burden_rows = [*bond_b_rows, *home_b_rows]
    contact_rows = _shared_contact_rows(aspects)
    direct_pool_a = _pool_names_from_items((bond_p_item, home_p_item), "left", layers=("psychology",))
    role_pool_a = _pool_names_from_items((bond_r_item, home_r_item), "left", layers=("role",))
    direct_pool_b = _pool_names_from_items((bond_p_item, home_p_item), "right", layers=("psychology",))
    role_pool_b = _pool_names_from_items((bond_r_item, home_r_item), "right", layers=("role",))
    sections = [
        {
            "id": "bond",
            "label": "Bond",
            "kind": "group_breakdown",
            "items": [bond_p_item, bond_r_item, bond_b_item],
        },
        {
            "id": "home",
            "label": "Home",
            "kind": "group_breakdown",
            "items": [home_p_item, home_r_item, home_b_item],
        },
        {
            "id": "contact_grid",
            "label": "Contact Grid",
            "kind": "event_rows",
            "items": _structured_event_rows(contact_rows, points_a=points_a, points_b=points_b, limit=32),
        },
    ]
    return _build_structured_report(
        engine_id="union_dynamics",
        engine_label=_engine_meta("union_dynamics")["label"],
        chart_data_a=chart_data_a,
        chart_data_b=chart_data_b,
        chart_a=chart_a,
        chart_b=chart_b,
        options=options,
        sections=sections,
        items=items,
        burden_rows=burden_rows,
        contact_rows=contact_rows,
        profile_a=profile_a,
        profile_b=profile_b,
        known_gaps=[
            "Saved snaps do not yet persist source-side sex/profile metadata in a universal way, so the engine falls back to blended bucket scans when no explicit or hinted profile is available.",
            "Union Dynamics parity is pinned to the decoded Basic tool fixture state; broader reversal and multi-instrument benchmark coverage is still pending.",
        ],
        items_include_burden=True,
        areas=_areas_payload(
            chart_label_a=str(chart_a.get("label") or "Chart A"),
            chart_label_b=str(chart_b.get("label") or "Chart B"),
            direct_pool_a=direct_pool_a,
            role_pool_a=role_pool_a,
            direct_pool_b=direct_pool_b,
            role_pool_b=role_pool_b,
            points_a=points_a,
            points_b=points_b,
        ),
    )


def build_synastry_engine_report(
    bundle_a: Dict[str, Any],
    bundle_b: Dict[str, Any],
    chart_a: Dict[str, Any],
    chart_b: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
    *,
    engine_id: Optional[str] = None,
    profile_a: Optional[str] = None,
    profile_b: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_engine_id = _normalize_engine_id(engine_id)
    normalized_options = _normalize_options(options)
    normalized_profile_a = _normalize_profile(profile_a or _profile_hint_from_chart(chart_a))
    normalized_profile_b = _normalize_profile(profile_b or _profile_hint_from_chart(chart_b))

    if normalized_engine_id == "memo":
        report = build_synastry_report(bundle_a, bundle_b, chart_a, chart_b, options=normalized_options)
        report["report_kind"] = "memo"
        report["engine_id"] = "memo"
        report["engine_label"] = _engine_meta("memo")["label"]
        report["available_engines"] = list_synastry_engines()
        return report

    if normalized_engine_id == "life_themes":
        return _build_life_themes_report(
            bundle_a=bundle_a,
            bundle_b=bundle_b,
            chart_a=chart_a,
            chart_b=chart_b,
            options=normalized_options,
            houses=tuple(HOUSE_THEME_META.keys()),
            engine_id="life_themes",
            engine_label=_engine_meta("life_themes")["label"],
            known_gaps=[
                "Life Themes parity is pinned to the decoded Basic tool fixture state; broader reversal and multi-instrument benchmark coverage is still pending.",
            ],
        )

    if normalized_engine_id == "work_alliance":
        return _build_work_alliance_report(
            bundle_a=bundle_a,
            bundle_b=bundle_b,
            chart_a=chart_a,
            chart_b=chart_b,
            options=normalized_options,
        )

    return _build_union_dynamics_report(
        bundle_a=bundle_a,
        bundle_b=bundle_b,
        chart_a=chart_a,
        chart_b=chart_b,
        options=normalized_options,
        profile_a=normalized_profile_a,
        profile_b=normalized_profile_b,
    )


__all__ = ["build_synastry_engine_report", "list_synastry_engines"]
