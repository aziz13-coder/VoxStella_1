from __future__ import annotations

import json
import math
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


SIGNS = (
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

SIGN_TO_MODALITY = {
    "Aries": "Cardinal",
    "Cancer": "Cardinal",
    "Libra": "Cardinal",
    "Capricorn": "Cardinal",
    "Taurus": "Fixed",
    "Leo": "Fixed",
    "Scorpio": "Fixed",
    "Aquarius": "Fixed",
    "Gemini": "Mutable",
    "Virgo": "Mutable",
    "Sagittarius": "Mutable",
    "Pisces": "Mutable",
}

SIGN_TO_NATURAL_HOUSE = {
    "Aries": 1,
    "Taurus": 2,
    "Gemini": 3,
    "Cancer": 4,
    "Leo": 5,
    "Virgo": 6,
    "Libra": 7,
    "Scorpio": 8,
    "Sagittarius": 9,
    "Capricorn": 10,
    "Aquarius": 11,
    "Pisces": 12,
}

COMPATIBLE_ELEMENTS = {
    ("Fire", "Air"),
    ("Air", "Fire"),
    ("Earth", "Water"),
    ("Water", "Earth"),
}

SIGN_RULERS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

SIGN_EXALTATIONS = {
    "Aries": "Sun",
    "Taurus": "Moon",
    "Cancer": "Jupiter",
    "Virgo": "Mercury",
    "Libra": "Saturn",
    "Capricorn": "Mars",
    "Pisces": "Venus",
}

CORE_PLANETS = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
MODERN_PLANETS = ("Uranus", "Neptune", "Pluto")
HEALING_POINTS = ("Chiron",)
NODAL_POINTS = ("North Node", "South Node")
ANGLE_POINTS = ("Ascendant", "Descendant", "Midheaven", "IC")
PERSONAL_PLANETS = ("Sun", "Moon", "Mercury", "Venus", "Mars")

NODE_NAME_ALIASES = {
    "north node": "North Node",
    "true node": "North Node",
    "mean node": "North Node",
    "node": "North Node",
    "northnode": "North Node",
    "south node": "South Node",
    "southnode": "South Node",
}

HOUSE_OVERLAY_LABELS = {
    1: "identity and immediacy",
    2: "values and self-worth",
    3: "conversation and local life",
    4: "home and rootedness",
    5: "romance and pleasure",
    6: "duty and strain",
    7: "partnership and mirroring",
    8: "intensity and entanglement",
    9: "beliefs and horizons",
    10: "public direction",
    11: "friendship and allies",
    12: "distance and hidden pressure",
}

REPORT_CATEGORY_ORDER = (
    "resonance",
    "communication",
    "attraction",
    "compatibility",
    "attachment",
    "growth",
    "friction",
    "burden",
)

DEFAULT_OPTIONS = {
    "include_modern": True,
    "include_nodes": True,
    "include_chiron": False,
    "orb_profile": "balanced",
}

ASPECT_DEFS = (
    {"name": "Conjunction", "angle": 0.0, "enabled": True},
    {"name": "Opposition", "angle": 180.0, "enabled": True},
    {"name": "Trine", "angle": 120.0, "enabled": True},
    {"name": "Square", "angle": 90.0, "enabled": True},
    {"name": "Sextile", "angle": 60.0, "enabled": True},
    {"name": "Quincunx", "angle": 150.0, "enabled": True},
    {"name": "Semisextile", "angle": 30.0, "enabled": True},
    {"name": "Semisquare", "angle": 45.0, "enabled": False},
    {"name": "Sesquiquadrate", "angle": 135.0, "enabled": False},
)

ORB_PROFILES = {
    "tight": {
        "base": {
            "Conjunction": 3.0,
            "Opposition": 3.0,
            "Trine": 2.75,
            "Square": 2.75,
            "Sextile": 2.25,
            "Quincunx": 1.5,
            "Semisextile": 1.25,
            "Semisquare": 1.0,
            "Sesquiquadrate": 1.0,
        },
        "class_modifier": {
            "luminary": 1.0,
            "angle": 1.0,
            "personal": 0.25,
            "social": 0.0,
            "outer": -0.5,
            "node": -0.75,
            "chiron": -0.75,
            "other": 0.0,
        },
    },
    "balanced": {
        "base": {
            "Conjunction": 5.5,
            "Opposition": 5.5,
            "Trine": 5.0,
            "Square": 5.0,
            "Sextile": 4.0,
            "Quincunx": 2.75,
            "Semisextile": 2.0,
            "Semisquare": 1.5,
            "Sesquiquadrate": 1.5,
        },
        "class_modifier": {
            "luminary": 1.0,
            "angle": 1.0,
            "personal": 0.5,
            "social": 0.25,
            "outer": -0.5,
            "node": -0.75,
            "chiron": -0.75,
            "other": 0.0,
        },
    },
    "wide": {
        "base": {
            "Conjunction": 6.5,
            "Opposition": 6.5,
            "Trine": 6.0,
            "Square": 6.0,
            "Sextile": 5.0,
            "Quincunx": 3.25,
            "Semisextile": 2.25,
            "Semisquare": 1.75,
            "Sesquiquadrate": 1.75,
        },
        "class_modifier": {
            "luminary": 1.0,
            "angle": 1.0,
            "personal": 0.5,
            "social": 0.25,
            "outer": -0.25,
            "node": -0.5,
            "chiron": -0.5,
            "other": 0.0,
        },
    },
}


def _catalog_path() -> Path:
    override = os.getenv("VOX_STELLA_SYNASTRY_RULE_CATALOG")
    candidates: List[Path] = []
    if override:
        candidates.append(Path(override).expanduser())

    candidates.append(Path(__file__).resolve().with_name("synastry_rule_catalog.json"))

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass).resolve() / "synastry_rule_catalog.json")

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().with_name("synastry_rule_catalog.json"))

    seen: Set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            return path
    return candidates[0]


@lru_cache(maxsize=1)
def _load_catalog() -> Dict[str, Any]:
    path = _catalog_path()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Synastry rule catalog must be a JSON object")
    return data


def _source_basis() -> List[Dict[str, Any]]:
    return list(_load_catalog().get("sources") or [])


def _category_meta() -> Dict[str, Dict[str, Any]]:
    raw = _load_catalog().get("categories") or {}
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def _rule_families() -> List[Dict[str, Any]]:
    rules = _load_catalog().get("rule_families") or []
    return [rule for rule in rules if isinstance(rule, dict)]


def _overall_model() -> Dict[str, Any]:
    return dict(_load_catalog().get("overall_model") or {})


def _category_adjustments() -> Dict[str, Dict[str, Any]]:
    raw = _load_catalog().get("category_adjustments") or {}
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def _category_scale(category_id: str) -> float:
    meta = _category_meta().get(category_id) or {}
    try:
        return float(meta.get("scale") or 0.0)
    except Exception:
        return 0.0


def _category_polarity(category_id: str) -> str:
    meta = _category_meta().get(category_id) or {}
    return str(meta.get("polarity") or "positive").strip().lower() or "positive"


def _boolish(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_options(options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    raw = dict(DEFAULT_OPTIONS)
    if isinstance(options, dict):
        raw.update(options)
    orb_profile = str(raw.get("orb_profile") or DEFAULT_OPTIONS["orb_profile"]).strip().lower()
    if orb_profile not in ORB_PROFILES:
        orb_profile = DEFAULT_OPTIONS["orb_profile"]
    return {
        "include_modern": _boolish(raw.get("include_modern"), DEFAULT_OPTIONS["include_modern"]),
        "include_nodes": _boolish(raw.get("include_nodes"), DEFAULT_OPTIONS["include_nodes"]),
        "include_chiron": _boolish(raw.get("include_chiron"), DEFAULT_OPTIONS["include_chiron"]),
        "orb_profile": orb_profile,
    }


def _norm360(value: float) -> float:
    return float(value) % 360.0


def _signed_delta(value: float) -> float:
    return ((_norm360(value) + 180.0) % 360.0) - 180.0


def _angular_distance(a: float, b: float) -> float:
    diff = abs(_norm360(a) - _norm360(b))
    return diff if diff <= 180.0 else 360.0 - diff


def _sign_from_longitude(lon: float) -> str:
    idx = int(_norm360(lon) // 30.0) % 12
    return SIGNS[idx]


def _normalize_point_name(value: Any) -> str:
    name = str(value or "").strip()
    if not name:
        return ""
    lowered = name.lower()
    if lowered in NODE_NAME_ALIASES:
        return NODE_NAME_ALIASES[lowered]
    return name


def _point_class(name: str) -> str:
    if name in {"Sun", "Moon"}:
        return "luminary"
    if name in ANGLE_POINTS:
        return "angle"
    if name in PERSONAL_PLANETS:
        return "personal"
    if name in {"Jupiter", "Saturn"}:
        return "social"
    if name in MODERN_PLANETS:
        return "outer"
    if name in NODAL_POINTS:
        return "node"
    if name == "Chiron":
        return "chiron"
    return "other"


def _allowed_planet_names(options: Dict[str, Any]) -> Tuple[str, ...]:
    names: List[str] = list(CORE_PLANETS)
    if options.get("include_modern"):
        names.extend(MODERN_PLANETS)
    if options.get("include_nodes"):
        names.extend(NODAL_POINTS)
    if options.get("include_chiron"):
        names.extend(HEALING_POINTS)
    return tuple(dict.fromkeys(names))


def _signature_planet_names(options: Dict[str, Any]) -> Tuple[str, ...]:
    names: List[str] = list(CORE_PLANETS)
    if options.get("include_modern"):
        names.extend(MODERN_PLANETS)
    if options.get("include_chiron"):
        names.extend(HEALING_POINTS)
    return tuple(dict.fromkeys(names))


def _planet_rows(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    planets = chart_data.get("planets") or []
    rows: List[Dict[str, Any]] = []
    if isinstance(planets, list):
        rows = [row for row in planets if isinstance(row, dict)]
    elif isinstance(planets, dict):
        for name, payload in planets.items():
            if not isinstance(payload, dict):
                continue
            row = dict(payload)
            row.setdefault("planet", str(name))
            rows.append(row)
    return rows


def _house_cusps(chart_data: Dict[str, Any]) -> List[float]:
    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
    if not isinstance(cusps, list):
        return []
    out: List[float] = []
    for item in cusps[:12]:
        try:
            out.append(_norm360(float(item)))
        except Exception:
            continue
    return out


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


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _coerce_house(value: Any) -> Optional[int]:
    try:
        house = int(value)
    except Exception:
        return None
    if 1 <= house <= 12:
        return house
    return None


def _build_points(chart_data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    allowed_planets = set(_allowed_planet_names(options))
    cusps = _house_cusps(chart_data)
    out: Dict[str, Dict[str, Any]] = {}

    for row in _planet_rows(chart_data):
        name = _normalize_point_name(row.get("planet") or row.get("name"))
        if name not in allowed_planets:
            continue
        lon = _coerce_float(row.get("longitude"))
        if lon is None:
            continue
        sign = str(row.get("sign") or _sign_from_longitude(lon)).strip() or _sign_from_longitude(lon)
        house = _coerce_house(row.get("house"))
        if house is None and cusps:
            house = _house_of_longitude(lon, cusps)
        speed = _coerce_float(row.get("speed"))
        retrograde = row.get("retrograde")
        out[name] = {
            "name": name,
            "longitude": _norm360(lon),
            "sign": sign,
            "house": house,
            "speed": speed,
            "retrograde": bool(retrograde) if retrograde is not None else (speed is not None and speed < 0.0),
            "class": _point_class(name),
        }

    if options.get("include_nodes") and "North Node" in out and "South Node" not in out:
        north = out["North Node"]
        south_lon = _norm360(float(north["longitude"]) + 180.0)
        out["South Node"] = {
            "name": "South Node",
            "longitude": south_lon,
            "sign": _sign_from_longitude(south_lon),
            "house": _house_of_longitude(south_lon, cusps) if cusps else None,
            "speed": north.get("speed"),
            "retrograde": north.get("retrograde"),
            "class": "node",
        }

    asc = _coerce_float(chart_data.get("ascendant"))
    mc = _coerce_float(chart_data.get("midheaven"))
    if asc is not None:
        desc = _norm360(asc + 180.0)
        out["Ascendant"] = {
            "name": "Ascendant",
            "longitude": _norm360(asc),
            "sign": _sign_from_longitude(asc),
            "house": 1,
            "speed": None,
            "retrograde": False,
            "class": "angle",
        }
        out["Descendant"] = {
            "name": "Descendant",
            "longitude": desc,
            "sign": _sign_from_longitude(desc),
            "house": 7,
            "speed": None,
            "retrograde": False,
            "class": "angle",
        }
    if mc is not None:
        ic = _norm360(mc + 180.0)
        out["Midheaven"] = {
            "name": "Midheaven",
            "longitude": _norm360(mc),
            "sign": _sign_from_longitude(mc),
            "house": 10,
            "speed": None,
            "retrograde": False,
            "class": "angle",
        }
        out["IC"] = {
            "name": "IC",
            "longitude": ic,
            "sign": _sign_from_longitude(ic),
            "house": 4,
            "speed": None,
            "retrograde": False,
            "class": "angle",
        }
    return out


def _orb_limit(aspect_name: str, point_a: str, point_b: str, profile_name: str) -> float:
    profile = ORB_PROFILES.get(profile_name) or ORB_PROFILES[DEFAULT_OPTIONS["orb_profile"]]
    base_map = profile.get("base") or {}
    base = float(base_map.get(aspect_name) or 0.0)
    modifier_map = profile.get("class_modifier") or {}
    modifier_a = float(modifier_map.get(_point_class(point_a), 0.0))
    modifier_b = float(modifier_map.get(_point_class(point_b), 0.0))
    limit = base + ((modifier_a + modifier_b) / 2.0)
    return max(0.75, round(limit, 3))


def _enabled_aspects() -> List[Dict[str, Any]]:
    return [item for item in ASPECT_DEFS if item.get("enabled")]


def _aspect_phase(point_a: Dict[str, Any], point_b: Dict[str, Any], target_angle: float) -> str:
    speed_a = _coerce_float(point_a.get("speed"))
    speed_b = _coerce_float(point_b.get("speed"))
    if speed_a is None or speed_b is None:
        return "unknown"
    rel_speed = speed_a - speed_b
    if abs(rel_speed) <= 1e-4:
        return "stationary"
    signed_gap = _signed_delta(float(point_a["longitude"]) - float(point_b["longitude"]) - target_angle)
    return "applying" if (signed_gap * rel_speed) < 0 else "separating"


def _find_best_aspect(delta: float, point_a: Dict[str, Any], point_b: Dict[str, Any], options: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    for aspect_def in _enabled_aspects():
        name = str(aspect_def["name"])
        angle = float(aspect_def["angle"])
        max_orb = _orb_limit(name, str(point_a["name"]), str(point_b["name"]), str(options["orb_profile"]))
        orb = abs(delta - angle)
        if orb > max_orb:
            continue
        exactness = max(0.0, 1.0 - (orb / max_orb))
        phase = _aspect_phase(point_a, point_b, angle)
        strength = exactness * (1.06 if phase == "applying" else 1.0)
        candidate = {
            "aspect": name,
            "angle": angle,
            "orb": round(orb, 3),
            "max_orb": max_orb,
            "closeness": round(strength, 6),
            "phase": phase,
            "exactness": round(exactness, 6),
        }
        if best is None:
            best = candidate
            continue
        cand_norm = orb / max_orb if max_orb else 999.0
        best_norm = float(best["orb"]) / float(best["max_orb"]) if best.get("max_orb") else 999.0
        if cand_norm < best_norm or (cand_norm == best_norm and orb < float(best["orb"])):
            best = candidate
    return best


def _cross_aspects(
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    options: Dict[str, Any],
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for name_a, point_a in points_a.items():
        for name_b, point_b in points_b.items():
            delta = _angular_distance(float(point_a["longitude"]), float(point_b["longitude"]))
            aspect = _find_best_aspect(delta, point_a, point_b, options)
            if not aspect:
                continue
            hits.append(
                {
                    "point_a": name_a,
                    "point_b": name_b,
                    "sign_a": point_a["sign"],
                    "sign_b": point_b["sign"],
                    "longitude_a": round(float(point_a["longitude"]), 4),
                    "longitude_b": round(float(point_b["longitude"]), 4),
                    "house_a": point_a.get("house"),
                    "house_b": point_b.get("house"),
                    **aspect,
                }
            )
    hits.sort(key=lambda item: (item["orb"], item["point_a"], item["point_b"]))
    return hits


def _natal_aspects(points: Dict[str, Dict[str, Any]], options: Dict[str, Any]) -> List[Dict[str, Any]]:
    names = [name for name in _signature_planet_names(options) if name in points]
    hits: List[Dict[str, Any]] = []
    for idx, name_a in enumerate(names):
        for name_b in names[idx + 1:]:
            point_a = points[name_a]
            point_b = points[name_b]
            delta = _angular_distance(float(point_a["longitude"]), float(point_b["longitude"]))
            aspect = _find_best_aspect(delta, point_a, point_b, options)
            if not aspect:
                continue
            hits.append({"point_a": name_a, "point_b": name_b, **aspect})
    return hits


def _natal_unaspected_points(points: Dict[str, Dict[str, Any]], options: Dict[str, Any]) -> Set[str]:
    natal_hits = _natal_aspects(points, options)
    touched: Set[str] = set()
    for item in natal_hits:
        touched.add(str(item.get("point_a") or ""))
        touched.add(str(item.get("point_b") or ""))
    target_names = set(_signature_planet_names(options))
    return {name for name in target_names if name in points and name not in touched}


def _element_relation(sign_a: str, sign_b: str) -> str:
    el_a = SIGN_TO_ELEMENT.get(sign_a)
    el_b = SIGN_TO_ELEMENT.get(sign_b)
    if not el_a or not el_b:
        return "unknown"
    if el_a == el_b:
        return "same"
    if (el_a, el_b) in COMPATIBLE_ELEMENTS:
        return "compatible"
    return "tense"


def _signature(points: Dict[str, Dict[str, Any]], chart_data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    names = [name for name in _signature_planet_names(options) if name in points]
    element_counts = {key: 0 for key in ("Fire", "Earth", "Air", "Water")}
    modality_counts = {key: 0 for key in ("Cardinal", "Fixed", "Mutable")}
    occupied_houses: Set[int] = set()
    above_horizon = 0
    below_horizon = 0
    east = 0
    west = 0

    for name in names:
        point = points[name]
        sign = str(point.get("sign") or "")
        element = SIGN_TO_ELEMENT.get(sign)
        modality = SIGN_TO_MODALITY.get(sign)
        if element:
            element_counts[element] = element_counts.get(element, 0) + 1
        if modality:
            modality_counts[modality] = modality_counts.get(modality, 0) + 1
        house = _coerce_house(point.get("house"))
        if house is not None:
            occupied_houses.add(house)
            if 7 <= house <= 12:
                above_horizon += 1
            else:
                below_horizon += 1
            if house in {10, 11, 12, 1, 2, 3}:
                east += 1
            else:
                west += 1

    cusps = _house_cusps(chart_data)
    seventh_sign = _sign_from_longitude(cusps[6]) if len(cusps) >= 7 else None
    seventh_ruler = SIGN_RULERS.get(seventh_sign or "")
    seventh_house_planets = [
        name
        for name in names
        if int(points[name].get("house") or 0) == 7
    ]
    return {
        "element_counts": element_counts,
        "modality_counts": modality_counts,
        "lacking_elements": [key for key, count in element_counts.items() if count == 0],
        "lacking_modalities": [key for key, count in modality_counts.items() if count == 0],
        "occupied_houses": sorted(occupied_houses),
        "empty_houses": [house for house in range(1, 13) if house not in occupied_houses],
        "above_horizon": above_horizon,
        "below_horizon": below_horizon,
        "east": east,
        "west": west,
        "seventh_sign": seventh_sign,
        "seventh_ruler": seventh_ruler,
        "seventh_house_planets": seventh_house_planets,
        "asc_sign": str((points.get("Ascendant") or {}).get("sign") or ""),
    }


def _point_availability(
    chart_data_a: Dict[str, Any],
    chart_data_b: Dict[str, Any],
) -> Dict[str, Any]:
    raw_names_a = {
        _normalize_point_name(row.get("planet") or row.get("name"))
        for row in _planet_rows(chart_data_a)
    }
    raw_names_b = {
        _normalize_point_name(row.get("planet") or row.get("name"))
        for row in _planet_rows(chart_data_b)
    }
    raw_names_a.discard("")
    raw_names_b.discard("")
    modern_names = set(MODERN_PLANETS)
    chiron_names = set(HEALING_POINTS)
    node_names = set(NODAL_POINTS)
    available_union = raw_names_a | raw_names_b
    return {
        "chart_a_raw_points": sorted(raw_names_a),
        "chart_b_raw_points": sorted(raw_names_b),
        "modern_available": bool(available_union & modern_names),
        "chiron_available": bool(available_union & chiron_names),
        "nodes_available": bool(available_union & node_names),
    }


def _round_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _scaled_score(raw_value: float, scale: float) -> int:
    if scale <= 0:
        return 0
    return _round_score((raw_value / scale) * 100.0)


def _apply_headline_normalization(value: float, config: Dict[str, Any]) -> float:
    method = str((config or {}).get("method") or "").strip().lower()
    if not method or method in {"none", "identity"}:
        return float(value)
    if method == "sigmoid":
        center = float((config or {}).get("center") or 50.0)
        scale = float((config or {}).get("scale") or 15.0)
        if scale <= 0.0:
            return float(value)
        exponent = -((float(value) - center) / scale)
        exponent = max(-60.0, min(60.0, exponent))
        return 100.0 / (1.0 + math.exp(exponent))
    return float(value)


def _evidence_record(detail: str, delta: float, rule: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "detail": detail,
        "delta": round(float(delta), 2),
        "source": rule.get("source_key"),
        "source_anchor": rule.get("source_anchor"),
        "rule_family_id": rule.get("id"),
        "summary": rule.get("summary"),
    }


def _ensure_governance_shape(governance: Dict[str, Dict[str, Set[str]]], category_id: str) -> None:
    governance.setdefault(category_id, {})
    governance[category_id].setdefault("source_keys", set())
    governance[category_id].setdefault("rule_family_ids", set())


def _record_scores(
    scores: Dict[str, float],
    evidence: Dict[str, List[str]],
    evidence_items: Dict[str, List[Dict[str, Any]]],
    governance: Dict[str, Dict[str, Set[str]]],
    rule_hits: Set[str],
    source_hits: Set[str],
    rule: Dict[str, Any],
    detail: str,
    score_map: Dict[str, Any],
) -> Dict[str, float]:
    positive = 0.0
    negative = 0.0
    source_key = str(rule.get("source_key") or "").strip()
    rule_id = str(rule.get("id") or "").strip()
    for category_id, raw_value in (score_map or {}).items():
        if category_id not in _category_meta():
            continue
        try:
            delta = float(raw_value)
        except Exception:
            continue
        if delta == 0.0:
            continue
        scores[category_id] = float(scores.get(category_id, 0.0)) + delta
        bucket = evidence.setdefault(category_id, [])
        if detail not in bucket:
            bucket.append(detail)
        detailed_bucket = evidence_items.setdefault(category_id, [])
        candidate = _evidence_record(detail, delta, rule)
        if not any(
            str(item.get("detail") or "") == str(candidate.get("detail") or "")
            and str(item.get("rule_family_id") or "") == str(candidate.get("rule_family_id") or "")
            for item in detailed_bucket
        ):
            detailed_bucket.append(candidate)
        _ensure_governance_shape(governance, category_id)
        if source_key:
            governance[category_id]["source_keys"].add(source_key)
            source_hits.add(source_key)
        if rule_id:
            governance[category_id]["rule_family_ids"].add(rule_id)
            rule_hits.add(rule_id)
        if _category_polarity(category_id) == "negative":
            negative += max(0.0, delta)
        else:
            positive += max(0.0, delta)
    return {
        "positive": round(positive, 2),
        "negative": round(negative, 2),
        "total": round(positive + negative, 2),
    }


def _link_record(
    kind: str,
    label: str,
    impact: float,
    detail: str,
    rule: Dict[str, Any],
    impact_meta: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    payload = {
        "kind": kind,
        "label": label,
        "impact": round(float(impact), 2),
        "detail": detail,
        "source": rule.get("source_key"),
        "source_anchor": rule.get("source_anchor"),
        "rule_family_id": rule.get("id"),
        "summary": rule.get("summary"),
    }
    if isinstance(impact_meta, dict):
        payload["positive_impact"] = round(float(impact_meta.get("positive") or 0.0), 2)
        payload["negative_impact"] = round(float(impact_meta.get("negative") or 0.0), 2)
    return payload


def _pair_matches_rule(rule: Dict[str, Any], point_a: str, point_b: str) -> bool:
    pair = frozenset({point_a, point_b})
    kind = str(rule.get("kind") or "")
    if kind == "aspect_pair":
        return pair == frozenset(rule.get("points") or [])
    if kind == "aspect_pairs_any":
        for item in rule.get("pairs") or []:
            if pair == frozenset(item or []):
                return True
        return False
    if kind == "aspect_contains":
        required = set(rule.get("required_points") or [])
        other_points = set(rule.get("other_points") or [])
        names = {point_a, point_b}
        if not required.issubset(names):
            return False
        if not other_points:
            return True
        return bool((names - required) & other_points)
    return False


def _apply_aspect_rules(
    aspects: Sequence[Dict[str, Any]],
    scores: Dict[str, float],
    evidence: Dict[str, List[str]],
    evidence_items: Dict[str, List[Dict[str, Any]]],
    governance: Dict[str, Dict[str, Set[str]]],
    rule_hits: Set[str],
    source_hits: Set[str],
    supportive_links: List[Dict[str, Any]],
    challenging_links: List[Dict[str, Any]],
) -> None:
    rules = [rule for rule in _rule_families() if str(rule.get("kind") or "").startswith("aspect_")]
    for hit in aspects:
        point_a = str(hit.get("point_a") or "")
        point_b = str(hit.get("point_b") or "")
        aspect_name = str(hit.get("aspect") or "")
        closeness = float(hit.get("closeness") or 0.0)
        orb = float(hit.get("orb") or 0.0)
        phase = str(hit.get("phase") or "unknown")
        label = f"{point_a} {aspect_name} {point_b}"
        detail = f"{label} (orb {orb:.2f} deg, {phase})"
        for rule in rules:
            aspects_allowed = {str(item) for item in (rule.get("aspects") or [])}
            if aspect_name not in aspects_allowed:
                continue
            if not _pair_matches_rule(rule, point_a, point_b):
                continue
            base_scores = {
                str(key): float(value) * closeness
                for key, value in (rule.get("scores") or {}).items()
            }
            impact_pack = _record_scores(
                scores,
                evidence,
                evidence_items,
                governance,
                rule_hits,
                source_hits,
                rule,
                detail,
                base_scores,
            )
            bucket = str(rule.get("bucket") or "").lower()
            if bucket in {"supportive", "mixed"} and impact_pack["positive"] > 0.0:
                supportive_links.append(_link_record("aspect", label, impact_pack["positive"], detail, rule, impact_pack))
            if bucket in {"challenging", "mixed"} and impact_pack["negative"] > 0.0:
                challenging_links.append(_link_record("aspect", label, impact_pack["negative"], detail, rule, impact_pack))


def _apply_element_rules(
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    scores: Dict[str, float],
    evidence: Dict[str, List[str]],
    evidence_items: Dict[str, List[Dict[str, Any]]],
    governance: Dict[str, Dict[str, Set[str]]],
    rule_hits: Set[str],
    source_hits: Set[str],
) -> None:
    rules = [rule for rule in _rule_families() if str(rule.get("kind") or "") == "element_pair"]
    for rule in rules:
        points = list(rule.get("points") or [])
        if len(points) != 2:
            continue
        point_a = points_a.get(str(points[0]))
        point_b = points_b.get(str(points[1]))
        if not point_a or not point_b:
            continue
        relation = _element_relation(str(point_a["sign"]), str(point_b["sign"]))
        if relation == "same":
            score_map = rule.get("same_scores") or {}
        elif relation == "compatible":
            score_map = rule.get("compatible_scores") or {}
        elif relation == "tense":
            score_map = rule.get("tense_scores") or {}
        else:
            continue
        if not score_map:
            continue
        detail = f"{points[0]}/{points[1]} show {relation} elemental fit ({point_a['sign']} / {point_b['sign']})"
        _record_scores(scores, evidence, evidence_items, governance, rule_hits, source_hits, rule, detail, score_map)


def _cross_receptions(points_a: Dict[str, Dict[str, Any]], points_b: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    mutual: List[Dict[str, Any]] = []
    unilateral: List[Dict[str, Any]] = []
    for a_name in CORE_PLANETS:
        point_a = points_a.get(a_name)
        if not point_a:
            continue
        for b_name in CORE_PLANETS:
            point_b = points_b.get(b_name)
            if not point_b:
                continue
            if SIGN_RULERS.get(str(point_a["sign"])) == b_name:
                unilateral.append(
                    {
                        "receiving": b_name,
                        "received": a_name,
                        "type": "domicile",
                        "detail": f"{a_name} in {point_a['sign']}, ruled by {b_name}",
                    }
                )
            if SIGN_EXALTATIONS.get(str(point_a["sign"])) == b_name:
                unilateral.append(
                    {
                        "receiving": b_name,
                        "received": a_name,
                        "type": "exaltation",
                        "detail": f"{a_name} in {point_a['sign']}, exalted by {b_name}",
                    }
                )
            if SIGN_RULERS.get(str(point_a["sign"])) == b_name and SIGN_RULERS.get(str(point_b["sign"])) == a_name:
                mutual.append(
                    {
                        "planet_a": a_name,
                        "planet_b": b_name,
                        "type": "mutual_domicile",
                        "detail": f"{a_name} in {point_a['sign']} and {b_name} in {point_b['sign']}",
                    }
                )
            if SIGN_EXALTATIONS.get(str(point_a["sign"])) == b_name and SIGN_EXALTATIONS.get(str(point_b["sign"])) == a_name:
                mutual.append(
                    {
                        "planet_a": a_name,
                        "planet_b": b_name,
                        "type": "mutual_exaltation",
                        "detail": f"{a_name} in {point_a['sign']} and {b_name} in {point_b['sign']}",
                    }
                )
    seen = set()
    dedup_mutual: List[Dict[str, Any]] = []
    for item in mutual:
        key = tuple(sorted((item["planet_a"], item["planet_b"]))) + (item["type"],)
        if key in seen:
            continue
        seen.add(key)
        dedup_mutual.append(item)
    return {"mutual": dedup_mutual, "unilateral": unilateral[:16]}


def _apply_reception_rules(
    receptions: Dict[str, List[Dict[str, Any]]],
    scores: Dict[str, float],
    evidence: Dict[str, List[str]],
    evidence_items: Dict[str, List[Dict[str, Any]]],
    governance: Dict[str, Dict[str, Set[str]]],
    rule_hits: Set[str],
    source_hits: Set[str],
    supportive_links: List[Dict[str, Any]],
) -> None:
    rules = [rule for rule in _rule_families() if str(rule.get("kind") or "") == "reception"]
    for rule in rules:
        mode = str(rule.get("mode") or "").strip().lower()
        items = list(receptions.get(mode) or [])
        if not items:
            continue
        per_hit = {str(key): float(value) for key, value in (rule.get("per_hit_scores") or {}).items()}
        max_total = {str(key): float(value) for key, value in (rule.get("max_total_scores") or {}).items()}
        aggregate: Dict[str, float] = {}
        for item in items:
            for category_id, delta in per_hit.items():
                aggregate[category_id] = float(aggregate.get(category_id, 0.0)) + delta
        for category_id, cap in max_total.items():
            aggregate[category_id] = min(float(aggregate.get(category_id, 0.0)), cap)
        if not aggregate:
            continue
        detail = f"{mode.title()} reception contributes structural backing across the two charts."
        impact_pack = _record_scores(
            scores,
            evidence,
            evidence_items,
            governance,
            rule_hits,
            source_hits,
            rule,
            detail,
            aggregate,
        )
        if impact_pack["positive"] > 0.0:
            supportive_links.append(_link_record("reception", f"{mode.title()} reception", impact_pack["positive"], detail, rule, impact_pack))


def _house_overlays(
    points_a: Dict[str, Dict[str, Any]],
    chart_a_label: str,
    points_b: Dict[str, Dict[str, Any]],
    chart_b_label: str,
    cusps_a: Sequence[float],
    cusps_b: Sequence[float],
    options: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    allowed_names = _allowed_planet_names(options)
    a_in_b: List[Dict[str, Any]] = []
    b_in_a: List[Dict[str, Any]] = []
    for name in allowed_names:
        point_a = points_a.get(name)
        if point_a:
            house_in_b = _house_of_longitude(float(point_a["longitude"]), cusps_b)
            if house_in_b:
                a_in_b.append(
                    {
                        "from_chart": chart_a_label,
                        "to_chart": chart_b_label,
                        "point": name,
                        "house": house_in_b,
                        "label": HOUSE_OVERLAY_LABELS.get(house_in_b, "house emphasis"),
                    }
                )
        point_b = points_b.get(name)
        if point_b:
            house_in_a = _house_of_longitude(float(point_b["longitude"]), cusps_a)
            if house_in_a:
                b_in_a.append(
                    {
                        "from_chart": chart_b_label,
                        "to_chart": chart_a_label,
                        "point": name,
                        "house": house_in_a,
                        "label": HOUSE_OVERLAY_LABELS.get(house_in_a, "house emphasis"),
                    }
                )
    return {"a_in_b": a_in_b, "b_in_a": b_in_a}


def _apply_overlay_rules(
    overlays: Dict[str, List[Dict[str, Any]]],
    scores: Dict[str, float],
    evidence: Dict[str, List[str]],
    evidence_items: Dict[str, List[Dict[str, Any]]],
    governance: Dict[str, Dict[str, Set[str]]],
    rule_hits: Set[str],
    source_hits: Set[str],
    supportive_links: List[Dict[str, Any]],
    challenging_links: List[Dict[str, Any]],
) -> None:
    rules = [rule for rule in _rule_families() if str(rule.get("kind") or "") == "house_overlay"]
    for direction in ("a_in_b", "b_in_a"):
        for item in overlays.get(direction, []):
            house = int(item.get("house") or 0)
            point = str(item.get("point") or "")
            label = f"{point} in partner's House {house}"
            detail = f"{point} falls in the partner's House {house} ({item.get('label')})"
            for rule in rules:
                allowed_houses = {int(value) for value in (rule.get("houses") or [])}
                allowed_points = {str(value) for value in (rule.get("points") or [])}
                if house not in allowed_houses or point not in allowed_points:
                    continue
                impact_pack = _record_scores(
                    scores,
                    evidence,
                    evidence_items,
                    governance,
                    rule_hits,
                    source_hits,
                    rule,
                    detail,
                    rule.get("scores") or {},
                )
                bucket = str(rule.get("bucket") or "").lower()
                if bucket in {"supportive", "mixed"} and impact_pack["positive"] > 0.0:
                    supportive_links.append(_link_record("overlay", label, impact_pack["positive"], detail, rule, impact_pack))
                if bucket in {"challenging", "mixed"} and impact_pack["negative"] > 0.0:
                    challenging_links.append(_link_record("overlay", label, impact_pack["negative"], detail, rule, impact_pack))


def _apply_partnership_ruler_rules(
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    signature_a: Dict[str, Any],
    signature_b: Dict[str, Any],
    options: Dict[str, Any],
    scores: Dict[str, float],
    evidence: Dict[str, List[str]],
    evidence_items: Dict[str, List[Dict[str, Any]]],
    governance: Dict[str, Dict[str, Set[str]]],
    rule_hits: Set[str],
    source_hits: Set[str],
    supportive_links: List[Dict[str, Any]],
    challenging_links: List[Dict[str, Any]],
) -> None:
    ruler_a = str(signature_a.get("seventh_ruler") or "")
    ruler_b = str(signature_b.get("seventh_ruler") or "")
    point_a = points_a.get(ruler_a)
    point_b = points_b.get(ruler_b)
    if not point_a or not point_b:
        return
    delta = _angular_distance(float(point_a["longitude"]), float(point_b["longitude"]))
    hit = _find_best_aspect(delta, point_a, point_b, options)
    if not hit:
        return
    rules = [rule for rule in _rule_families() if str(rule.get("kind") or "") == "partnership_ruler_aspect"]
    label = f"7th-ruler {ruler_a} {hit['aspect']} {ruler_b}"
    detail = f"7th-ruler cross-aspect {ruler_a} {hit['aspect']} {ruler_b} (orb {float(hit['orb']):.2f} deg)"
    for rule in rules:
        aspects_allowed = {str(item) for item in (rule.get("aspects") or [])}
        if str(hit["aspect"]) not in aspects_allowed:
            continue
        score_map = {
            str(key): float(value) * float(hit.get("closeness") or 0.0)
            for key, value in (rule.get("scores") or {}).items()
        }
        impact_pack = _record_scores(
            scores,
            evidence,
            evidence_items,
            governance,
            rule_hits,
            source_hits,
            rule,
            detail,
            score_map,
        )
        bucket = str(rule.get("bucket") or "").lower()
        if bucket in {"supportive", "mixed"} and impact_pack["positive"] > 0.0:
            supportive_links.append(_link_record("ruler", label, impact_pack["positive"], detail, rule, impact_pack))
        if bucket in {"challenging", "mixed"} and impact_pack["negative"] > 0.0:
            challenging_links.append(_link_record("ruler", label, impact_pack["negative"], detail, rule, impact_pack))


def _apply_compensation_rules(
    chart_a_label: str,
    chart_b_label: str,
    points_a: Dict[str, Dict[str, Any]],
    points_b: Dict[str, Dict[str, Any]],
    aspects: Sequence[Dict[str, Any]],
    overlays: Dict[str, List[Dict[str, Any]]],
    signature_a: Dict[str, Any],
    signature_b: Dict[str, Any],
    natal_unaspected_a: Set[str],
    natal_unaspected_b: Set[str],
    scores: Dict[str, float],
    evidence: Dict[str, List[str]],
    evidence_items: Dict[str, List[Dict[str, Any]]],
    governance: Dict[str, Dict[str, Set[str]]],
    rule_hits: Set[str],
    source_hits: Set[str],
    supportive_links: List[Dict[str, Any]],
    challenging_links: List[Dict[str, Any]],
) -> None:
    rules = _rule_families()

    def apply_compensation_pair(
        target_signature: Dict[str, Any],
        source_signature: Dict[str, Any],
        source_label: str,
    ) -> None:
        for rule in rules:
            kind = str(rule.get("kind") or "")
            if kind == "element_lack_fill":
                strong_threshold = int(rule.get("strong_threshold") or 3)
                overload_threshold = int(rule.get("overload_threshold") or 5)
                for element in target_signature.get("lacking_elements") or []:
                    source_count = int((source_signature.get("element_counts") or {}).get(element) or 0)
                    if source_count <= 0:
                        continue
                    detail = f"{source_label} supplies the partner's missing {element} element with {source_count} placements."
                    score_map = rule.get("scores") or {}
                    if source_count >= strong_threshold:
                        score_map = rule.get("strong_scores") or score_map
                    impact_pack = _record_scores(
                        scores,
                        evidence,
                        evidence_items,
                        governance,
                        rule_hits,
                        source_hits,
                        rule,
                        detail,
                        score_map,
                    )
                    if impact_pack["positive"] > 0.0:
                        supportive_links.append(_link_record("compensation", f"{element} lack filled", impact_pack["positive"], detail, rule, impact_pack))
                    if source_count >= overload_threshold:
                        overload_map = rule.get("overload_scores") or {}
                        if overload_map:
                            overload_detail = f"{source_label}'s {element} emphasis may overcompensate the partner's missing {element} element."
                            overload_pack = _record_scores(
                                scores,
                                evidence,
                                evidence_items,
                                governance,
                                rule_hits,
                                source_hits,
                                rule,
                                overload_detail,
                                overload_map,
                            )
                            if overload_pack["negative"] > 0.0:
                                challenging_links.append(_link_record("compensation", f"{element} overcompensation", overload_pack["negative"], overload_detail, rule, overload_pack))

            elif kind == "modality_lack_fill":
                strong_threshold = int(rule.get("strong_threshold") or 3)
                for modality in target_signature.get("lacking_modalities") or []:
                    source_count = int((source_signature.get("modality_counts") or {}).get(modality) or 0)
                    if source_count < strong_threshold:
                        continue
                    detail = f"{source_label} reinforces the partner's missing {modality} mode through {source_count} placements."
                    impact_pack = _record_scores(
                        scores,
                        evidence,
                        evidence_items,
                        governance,
                        rule_hits,
                        source_hits,
                        rule,
                        detail,
                        rule.get("scores") or {},
                    )
                    if impact_pack["positive"] > 0.0:
                        supportive_links.append(_link_record("compensation", f"{modality} mode supplied", impact_pack["positive"], detail, rule, impact_pack))

            elif kind == "hemisphere_balance":
                axis = str(rule.get("axis") or "").lower()
                threshold = int(rule.get("threshold") or 7)
                matched = False
                if axis == "vertical":
                    matched = (
                        (int(target_signature.get("below_horizon") or 0) >= threshold and int(source_signature.get("above_horizon") or 0) >= threshold)
                        or (int(target_signature.get("above_horizon") or 0) >= threshold and int(source_signature.get("below_horizon") or 0) >= threshold)
                    )
                elif axis == "horizontal":
                    matched = (
                        (int(target_signature.get("east") or 0) >= threshold and int(source_signature.get("west") or 0) >= threshold)
                        or (int(target_signature.get("west") or 0) >= threshold and int(source_signature.get("east") or 0) >= threshold)
                    )
                if not matched:
                    continue
                detail = f"{source_label} balances the partner's {axis} hemisphere emphasis rather than mirroring it."
                impact_pack = _record_scores(
                    scores,
                    evidence,
                    evidence_items,
                    governance,
                    rule_hits,
                    source_hits,
                    rule,
                    detail,
                    rule.get("scores") or {},
                )
                if impact_pack["positive"] > 0.0:
                    supportive_links.append(_link_record("balance", f"{axis.title()} hemisphere balance", impact_pack["positive"], detail, rule, impact_pack))

    apply_compensation_pair(signature_a, signature_b, chart_b_label)
    apply_compensation_pair(signature_b, signature_a, chart_a_label)

    for rule in rules:
        kind = str(rule.get("kind") or "")

        if kind == "empty_house_fill":
            allowed_points = {str(item) for item in (rule.get("points") or [])}
            for direction, recipient_signature in (("a_in_b", signature_b), ("b_in_a", signature_a)):
                for item in overlays.get(direction) or []:
                    point = str(item.get("point") or "")
                    house = int(item.get("house") or 0)
                    if point not in allowed_points or house not in set(recipient_signature.get("empty_houses") or []):
                        continue
                    detail = f"{point} activates the partner's otherwise empty House {house}, giving that area a borrowed outlet."
                    impact_pack = _record_scores(
                        scores,
                        evidence,
                        evidence_items,
                        governance,
                        rule_hits,
                        source_hits,
                        rule,
                        detail,
                        rule.get("scores") or {},
                    )
                    bucket = str(rule.get("bucket") or "").lower()
                    if bucket in {"supportive", "mixed"} and impact_pack["positive"] > 0.0:
                        supportive_links.append(_link_record("compensation", f"{point} fills empty House {house}", impact_pack["positive"], detail, rule, impact_pack))
                    if bucket in {"challenging", "mixed"} and impact_pack["negative"] > 0.0:
                        challenging_links.append(_link_record("compensation", f"{point} fills empty House {house}", impact_pack["negative"], detail, rule, impact_pack))

        elif kind == "natal_activation":
            allowed_points = {str(item) for item in (rule.get("points") or [])}
            allowed_aspects = {str(item) for item in (rule.get("aspects") or [])}
            for hit in aspects:
                aspect_name = str(hit.get("aspect") or "")
                if aspect_name not in allowed_aspects:
                    continue
                point_a = str(hit.get("point_a") or "")
                point_b = str(hit.get("point_b") or "")
                if point_a in allowed_points and point_a in natal_unaspected_a:
                    detail = f"{point_b} {aspect_name.lower()} activates {chart_a_label}'s otherwise natal-unaspected {point_a}."
                elif point_b in allowed_points and point_b in natal_unaspected_b:
                    detail = f"{point_a} {aspect_name.lower()} activates {chart_b_label}'s otherwise natal-unaspected {point_b}."
                else:
                    continue
                closeness = float(hit.get("closeness") or 0.0)
                score_map = {
                    str(key): float(value) * closeness
                    for key, value in (rule.get("scores") or {}).items()
                }
                impact_pack = _record_scores(
                    scores,
                    evidence,
                    evidence_items,
                    governance,
                    rule_hits,
                    source_hits,
                    rule,
                    detail,
                    score_map,
                )
                bucket = str(rule.get("bucket") or "").lower()
                if bucket in {"supportive", "mixed"} and impact_pack["positive"] > 0.0:
                    supportive_links.append(_link_record("activation", "Natal lack activated", impact_pack["positive"], detail, rule, impact_pack))
                if bucket in {"challenging", "mixed"} and impact_pack["negative"] > 0.0:
                    challenging_links.append(_link_record("activation", "Natal lack activated", impact_pack["negative"], detail, rule, impact_pack))

        elif kind == "sign_house_affinity":
            for source_points, target_points, source_label, target_label in (
                (points_a, points_b, chart_a_label, chart_b_label),
                (points_b, points_a, chart_b_label, chart_a_label),
            ):
                target_asc_sign = str((target_points.get("Ascendant") or {}).get("sign") or "")
                for point_name in ("Sun", "Moon"):
                    source_point = source_points.get(point_name)
                    if not source_point:
                        continue
                    source_sign = str(source_point.get("sign") or "")
                    natural_house = int(SIGN_TO_NATURAL_HOUSE.get(source_sign) or 0)
                    if natural_house <= 0:
                        continue
                    if target_asc_sign == source_sign:
                        detail = f"{source_label}'s {point_name} in {source_sign} resonates with {target_label}'s Ascendant sign."
                    else:
                        match_name = next(
                            (
                                target_name
                                for target_name in ("Sun", "Moon")
                                if int((target_points.get(target_name) or {}).get("house") or 0) == natural_house
                            ),
                            "",
                        )
                        if not match_name:
                            continue
                        detail = f"{source_label}'s {point_name} in {source_sign} matches {target_label}'s natural House {natural_house} emphasis through {match_name}."
                    impact_pack = _record_scores(
                        scores,
                        evidence,
                        evidence_items,
                        governance,
                        rule_hits,
                        source_hits,
                        rule,
                        detail,
                        rule.get("scores") or {},
                    )
                    if impact_pack["positive"] > 0.0:
                        supportive_links.append(_link_record("affinity", "Sign-house affinity", impact_pack["positive"], detail, rule, impact_pack))

        elif kind == "directional_overlay_imbalance":
            houses = {int(value) for value in (rule.get("houses") or [])}
            threshold = int(rule.get("threshold") or 2)
            count_a = sum(1 for item in overlays.get("a_in_b") or [] if int(item.get("house") or 0) in houses)
            count_b = sum(1 for item in overlays.get("b_in_a") or [] if int(item.get("house") or 0) in houses)
            diff = abs(count_a - count_b)
            if diff < threshold:
                continue
            leading_label = chart_a_label if count_a > count_b else chart_b_label
            detail = f"{leading_label} activates the intimate houses more strongly than the reverse, which can make the bond feel uneven."
            impact_pack = _record_scores(
                scores,
                evidence,
                evidence_items,
                governance,
                rule_hits,
                source_hits,
                rule,
                detail,
                rule.get("scores") or {},
            )
            if impact_pack["negative"] > 0.0:
                challenging_links.append(_link_record("balance", "Directional overlay imbalance", impact_pack["negative"], detail, rule, impact_pack))


def _build_category_payload(
    scores: Dict[str, float],
    evidence: Dict[str, List[str]],
    evidence_items: Dict[str, List[Dict[str, Any]]],
    governance: Dict[str, Dict[str, Set[str]]],
) -> List[Dict[str, Any]]:
    categories = _category_meta()
    out: List[Dict[str, Any]] = []
    for key in REPORT_CATEGORY_ORDER:
        meta = categories.get(key) or {}
        raw = round(float(scores.get(key, 0.0)), 2)
        display = _scaled_score(raw, _category_scale(key))
        category_governance = governance.get(key) or {}
        detailed_evidence = sorted(
            list(evidence_items.get(key) or []),
            key=lambda item: (-abs(float(item.get("delta") or 0.0)), str(item.get("detail") or "")),
        )[:6]
        out.append(
            {
                "id": key,
                "name": meta.get("name") or key,
                "polarity": meta.get("polarity") or "positive",
                "score": display,
                "raw_score": raw,
                "max_score": _category_scale(key),
                "description": meta.get("description") or "",
                "evidence": (evidence.get(key) or [])[:8],
                "evidence_items": detailed_evidence,
                "source_keys": sorted(category_governance.get("source_keys") or []),
                "rule_family_ids": sorted(category_governance.get("rule_family_ids") or []),
            }
        )
    return out


def _average_scores(by_id: Dict[str, Dict[str, Any]], ids: Sequence[str]) -> float:
    values = [float((by_id.get(key) or {}).get("score") or 0.0) for key in ids]
    return round(sum(values) / len(values), 2) if values else 0.0


def _rule_ids_from_categories(
    evidence_items: Dict[str, List[Dict[str, Any]]],
    category_ids: Sequence[str],
) -> Set[str]:
    hits: Set[str] = set()
    for category_id in category_ids:
        for item in evidence_items.get(category_id) or []:
            rule_id = str(item.get("rule_family_id") or "").strip()
            if rule_id:
                hits.add(rule_id)
    return hits


def _rule_hit_count_from_categories(
    evidence_items: Dict[str, List[Dict[str, Any]]],
    category_ids: Sequence[str],
    target_rule_ids: Set[str],
) -> int:
    count = 0
    for category_id in category_ids:
        for item in evidence_items.get(category_id) or []:
            rule_id = str(item.get("rule_family_id") or "").strip()
            if rule_id and rule_id in target_rule_ids:
                count += 1
    return count


def _display_cap_to_raw(display_score: float, category_id: str) -> float:
    scale = _category_scale(category_id)
    if scale <= 0.0:
        return 0.0
    return round((float(display_score) / 100.0) * scale, 2)


def _apply_category_adjustments(
    scores: Dict[str, float],
    evidence: Dict[str, List[str]],
    evidence_items: Dict[str, List[Dict[str, Any]]],
    governance: Dict[str, Dict[str, Set[str]]],
    rule_hits: Set[str],
    source_hits: Set[str],
) -> None:
    adjustments = _category_adjustments()

    compatibility_adjustment = adjustments.get("compatibility_conflict_gate") or {}
    if compatibility_adjustment:
        compatibility_rule = dict(compatibility_adjustment)
        compatibility_rule.setdefault("id", "compatibility_conflict_gate")
        direct_ease_ids = {str(item) for item in (compatibility_adjustment.get("direct_ease_rule_family_ids") or [])}
        conflict_ids = {str(item) for item in (compatibility_adjustment.get("conflict_rule_family_ids") or [])}
        compatibility_hits = _rule_ids_from_categories(evidence_items, ("compatibility",))
        conflict_hits = _rule_ids_from_categories(evidence_items, ("friction", "burden")) & conflict_ids
        direct_ease_hits = compatibility_hits & direct_ease_ids
        current_raw = float(scores.get("compatibility") or 0.0)
        current_display = _scaled_score(current_raw, _category_scale("compatibility"))
        high_conflict_threshold = int(compatibility_adjustment.get("high_conflict_hit_threshold") or 4)
        medium_conflict_threshold = int(compatibility_adjustment.get("medium_conflict_hit_threshold") or 3)
        cap_display: Optional[float] = None
        if len(conflict_hits) >= high_conflict_threshold and len(direct_ease_hits) == 0:
            cap_display = float(compatibility_adjustment.get("max_display_score_without_direct_ease") or 52.0)
        elif len(conflict_hits) >= medium_conflict_threshold and len(direct_ease_hits) <= 1:
            cap_display = float(compatibility_adjustment.get("max_display_score_with_thin_direct_ease") or 68.0)
        if cap_display is not None and current_display > cap_display:
            capped_raw = _display_cap_to_raw(cap_display, "compatibility")
            delta = round(capped_raw - current_raw, 2)
            if delta < 0.0:
                detail = (
                    "Compatibility is capped because repeated hard themes outweigh direct ease markers "
                    f"({len(conflict_hits)} hard-theme families, {len(direct_ease_hits)} direct ease families)."
                )
                _record_scores(
                    scores,
                    evidence,
                    evidence_items,
                    governance,
                    rule_hits,
                    source_hits,
                    compatibility_rule,
                    detail,
                    {"compatibility": delta},
                )

    burden_adjustment = adjustments.get("burden_saturn_context_relief") or {}
    if burden_adjustment:
        burden_rule = dict(burden_adjustment)
        burden_rule.setdefault("id", "burden_saturn_context_relief")
        saturn_ids = {str(item) for item in (burden_adjustment.get("saturn_rule_family_ids") or [])}
        non_saturn_ids = {str(item) for item in (burden_adjustment.get("non_saturn_heaviness_rule_family_ids") or [])}
        direct_ease_ids = {str(item) for item in (burden_adjustment.get("direct_ease_rule_family_ids") or [])}
        burden_hits = _rule_ids_from_categories(evidence_items, ("burden",))
        saturn_hits = burden_hits & saturn_ids
        non_saturn_hits = burden_hits & non_saturn_ids
        direct_ease_hits = _rule_ids_from_categories(
            evidence_items,
            ("compatibility", "resonance", "communication", "attachment"),
        ) & direct_ease_ids
        current_raw = float(scores.get("burden") or 0.0)
        current_display = _scaled_score(current_raw, _category_scale("burden"))
        direct_ease_threshold = int(burden_adjustment.get("direct_ease_threshold") or 2)
        max_non_saturn = int(burden_adjustment.get("max_non_saturn_heaviness_hits") or 2)
        cap_display = float(burden_adjustment.get("max_display_score") or 52.0)
        if (
            len(saturn_hits) >= 2
            and len(direct_ease_hits) >= direct_ease_threshold
            and len(non_saturn_hits) <= max_non_saturn
            and current_display > cap_display
        ):
            capped_raw = _display_cap_to_raw(cap_display, "burden")
            delta = round(capped_raw - current_raw, 2)
            if delta < 0.0:
                detail = (
                    "Burden is moderated because Saturn-heavy seriousness is not fully corroborated by oppressive themes "
                    f"({len(saturn_hits)} Saturn-heavy families, {len(non_saturn_hits)} corroborating heaviness families)."
                )
                _record_scores(
                    scores,
                    evidence,
                    evidence_items,
                    governance,
                    rule_hits,
                    source_hits,
                    burden_rule,
                    detail,
                    {"burden": delta},
                )

    oppressive_adjustment = adjustments.get("burden_oppressive_cluster_floor") or {}
    if oppressive_adjustment:
        oppressive_rule = dict(oppressive_adjustment)
        oppressive_rule.setdefault("id", "burden_oppressive_cluster_floor")
        burden_hits = _rule_ids_from_categories(evidence_items, ("burden",))
        friction_burden_hits = _rule_ids_from_categories(evidence_items, ("friction", "burden"))
        saturn_hits = burden_hits & {str(item) for item in (oppressive_adjustment.get("hard_saturn_rule_family_ids") or [])}
        emotional_hits = friction_burden_hits & {str(item) for item in (oppressive_adjustment.get("emotional_strain_rule_family_ids") or [])}
        obstructive_hits = friction_burden_hits & {str(item) for item in (oppressive_adjustment.get("obstructive_rule_family_ids") or [])}
        current_raw = float(scores.get("burden") or 0.0)
        current_display = _scaled_score(current_raw, _category_scale("burden"))
        minimum_display = float(oppressive_adjustment.get("minimum_display_score") or 78.0)
        if (
            len(saturn_hits) >= int(oppressive_adjustment.get("hard_saturn_hit_threshold") or 2)
            and len(emotional_hits) >= int(oppressive_adjustment.get("emotional_strain_threshold") or 1)
            and len(obstructive_hits) >= int(oppressive_adjustment.get("obstructive_threshold") or 1)
            and current_display < minimum_display
        ):
            floored_raw = _display_cap_to_raw(minimum_display, "burden")
            delta = round(floored_raw - current_raw, 2)
            if delta > 0.0:
                detail = (
                    "Burden is elevated because hard Saturn is reinforced by emotional strain and obstructive conflict "
                    f"({len(saturn_hits)} hard-Saturn families, {len(emotional_hits)} emotional-strain families, "
                    f"{len(obstructive_hits)} obstructive families)."
                )
                _record_scores(
                    scores,
                    evidence,
                    evidence_items,
                    governance,
                    rule_hits,
                    source_hits,
                    oppressive_rule,
                    detail,
                    {"burden": delta},
                )

    attraction_supportive_adjustment = adjustments.get("attraction_supportive_polarity_floor") or {}
    if attraction_supportive_adjustment:
        attraction_rule = dict(attraction_supportive_adjustment)
        attraction_rule.setdefault("id", "attraction_supportive_polarity_floor")
        broad_hits = _rule_ids_from_categories(
            evidence_items,
            ("attraction", "attachment", "compatibility", "resonance", "friction"),
        )
        luminary_hits = broad_hits & {
            str(item) for item in (attraction_supportive_adjustment.get("luminary_rule_family_ids") or [])
        }
        venus_mars_hits = broad_hits & {
            str(item) for item in (attraction_supportive_adjustment.get("venus_mars_rule_family_ids") or [])
        }
        current_raw = float(scores.get("attraction") or 0.0)
        current_display = _scaled_score(current_raw, _category_scale("attraction"))
        minimum_display = float(attraction_supportive_adjustment.get("minimum_display_score") or 70.0)
        if luminary_hits and venus_mars_hits and current_display < minimum_display:
            floored_raw = _display_cap_to_raw(minimum_display, "attraction")
            delta = round(floored_raw - current_raw, 2)
            if delta > 0.0:
                detail = (
                    "Attraction is elevated because Sun/Moon polarity and Venus/Mars chemistry repeat the same "
                    f"message ({len(luminary_hits)} luminary families, {len(venus_mars_hits)} Venus-Mars families)."
                )
                _record_scores(
                    scores,
                    evidence,
                    evidence_items,
                    governance,
                    rule_hits,
                    source_hits,
                    attraction_rule,
                    detail,
                    {"attraction": delta},
                )

    attraction_stress_adjustment = adjustments.get("attraction_stress_cluster_floor") or {}
    if attraction_stress_adjustment:
        attraction_rule = dict(attraction_stress_adjustment)
        attraction_rule.setdefault("id", "attraction_stress_cluster_floor")
        broad_hits = _rule_ids_from_categories(
            evidence_items,
            ("attraction", "attachment", "compatibility", "resonance", "friction", "burden"),
        )
        luminary_hits = broad_hits & {
            str(item) for item in (attraction_stress_adjustment.get("luminary_rule_family_ids") or [])
        }
        chemistry_hits = broad_hits & {
            str(item) for item in (attraction_stress_adjustment.get("chemistry_rule_family_ids") or [])
        }
        current_raw = float(scores.get("attraction") or 0.0)
        current_display = _scaled_score(current_raw, _category_scale("attraction"))
        friction_display = _scaled_score(float(scores.get("friction") or 0.0), _category_scale("friction"))
        minimum_display = float(attraction_stress_adjustment.get("minimum_display_score") or 55.0)
        minimum_friction = float(attraction_stress_adjustment.get("minimum_friction_display_score") or 70.0)
        if luminary_hits and chemistry_hits and friction_display >= minimum_friction and current_display < minimum_display:
            floored_raw = _display_cap_to_raw(minimum_display, "attraction")
            delta = round(floored_raw - current_raw, 2)
            if delta > 0.0:
                detail = (
                    "Attraction is elevated because stressed Venus-Mars and luminary chemistry remain magnetic under "
                    f"high friction ({len(luminary_hits)} luminary-stress families, "
                    f"{len(chemistry_hits)} chemistry families, friction {friction_display})."
                )
                _record_scores(
                    scores,
                    evidence,
                    evidence_items,
                    governance,
                    rule_hits,
                    source_hits,
                    attraction_rule,
                    detail,
                    {"attraction": delta},
                )

    attachment_binding_adjustment = adjustments.get("attachment_enduring_binding_cluster_floor") or {}
    if attachment_binding_adjustment:
        attachment_rule = dict(attachment_binding_adjustment)
        attachment_rule.setdefault("id", "attachment_enduring_binding_cluster_floor")
        broad_hits = _rule_ids_from_categories(
            evidence_items,
            ("attachment", "compatibility", "growth", "burden", "resonance"),
        )
        reception_hits = broad_hits & {
            str(item) for item in (attachment_binding_adjustment.get("reception_rule_family_ids") or [])
        }
        saturn_rule_ids = {
            str(item) for item in (attachment_binding_adjustment.get("saturn_rule_family_ids") or [])
        }
        saturn_hits = broad_hits & saturn_rule_ids
        bond_confirmation_hits = broad_hits & {
            str(item) for item in (attachment_binding_adjustment.get("bond_confirmation_rule_family_ids") or [])
        }
        saturn_hit_count = _rule_hit_count_from_categories(
            evidence_items,
            ("attachment", "compatibility", "growth", "burden", "resonance"),
            saturn_rule_ids,
        )
        current_raw = float(scores.get("attachment") or 0.0)
        current_display = _scaled_score(current_raw, _category_scale("attachment"))
        minimum_display = float(attachment_binding_adjustment.get("minimum_display_score") or 70.0)
        if (
            reception_hits
            and saturn_hit_count >= int(attachment_binding_adjustment.get("saturn_hit_threshold") or 2)
            and len(bond_confirmation_hits) >= int(attachment_binding_adjustment.get("bond_confirmation_threshold") or 1)
            and current_display < minimum_display
        ):
            floored_raw = _display_cap_to_raw(minimum_display, "attachment")
            delta = round(floored_raw - current_raw, 2)
            if delta > 0.0:
                detail = (
                    "Attachment is elevated because mutual reception, repeated Saturn-binding testimony, and nodal or "
                    f"partnership confirmation recur together ({len(reception_hits)} reception families, "
                    f"{saturn_hit_count} Saturn-binding hits across {len(saturn_hits)} families, "
                    f"{len(bond_confirmation_hits)} confirmation families)."
                )
                _record_scores(
                    scores,
                    evidence,
                    evidence_items,
                    governance,
                    rule_hits,
                    source_hits,
                    attachment_rule,
                    detail,
                    {"attachment": delta},
                )


def _build_overall_score(
    category_payload: Sequence[Dict[str, Any]],
    receptions: Dict[str, List[Dict[str, Any]]],
    supportive_links: Sequence[Dict[str, Any]],
    challenging_links: Sequence[Dict[str, Any]],
) -> Tuple[int, List[str], List[Dict[str, Any]], Dict[str, Any]]:
    categories = _category_meta()
    model = _overall_model()
    by_id = {str(item.get("id")): item for item in category_payload}

    compatibility_ids = list(model.get("compatibility_dimensions") or ["resonance", "communication", "compatibility"])
    binding_ids = list(model.get("binding_dimensions") or ["attraction", "attachment"])
    growth_ids = list(model.get("growth_dimensions") or ["growth"])
    challenge_ids = list(model.get("challenge_dimensions") or ["friction", "burden"])
    weights = dict(model.get("weights") or {})

    compatibility_component = _average_scores(by_id, compatibility_ids)
    binding_component = _average_scores(by_id, binding_ids)
    growth_component = _average_scores(by_id, growth_ids)
    challenge_component = _average_scores(by_id, challenge_ids)

    positive_impact_total = round(sum(float(item.get("impact") or 0.0) for item in supportive_links), 2)
    negative_impact_total = round(sum(float(item.get("impact") or 0.0) for item in challenging_links), 2)
    if positive_impact_total > 0.0 or negative_impact_total > 0.0:
        support_balance_component = round((positive_impact_total / (positive_impact_total + negative_impact_total)) * 100.0, 2)
    else:
        support_balance_component = compatibility_component

    reception_bonus_cap = float(model.get("binding_bonus_cap") or 0.0)
    reception_bonus = min(reception_bonus_cap, 4.0 * len(receptions.get("mutual") or []))

    legacy_weighted_total = (
        compatibility_component * float(weights.get("compatibility", 0.30))
        + binding_component * float(weights.get("binding", 0.22))
        + growth_component * float(weights.get("growth", 0.12))
        + support_balance_component * float(weights.get("support_balance", 0.26))
        - challenge_component * float(weights.get("challenge", 0.18))
        + reception_bonus
    )
    headline_weights = {
        str(key): float(value)
        for key, value in dict(model.get("headline_category_weights") or {}).items()
    }
    headline_normalization = {
        str(key): value
        for key, value in dict(model.get("headline_normalization") or {}).items()
    }
    headline_weighted_total = 0.0
    if headline_weights:
        for category_id, weight in headline_weights.items():
            headline_weighted_total += float((by_id.get(category_id) or {}).get("score") or 0.0) * weight
    else:
        headline_weighted_total = legacy_weighted_total
    headline_normalized_total = _apply_headline_normalization(headline_weighted_total, headline_normalization)
    overall = _round_score(headline_normalized_total)

    strongest_support = next(iter(supportive_links), None)
    strongest_challenge = next(iter(challenging_links), None)
    strongest_compensation = next(
        (
            item
            for item in supportive_links
            if str(item.get("kind") or "") in {"compensation", "balance", "affinity", "ruler", "activation"}
        ),
        None,
    )

    summary_lines: List[str] = []
    overall_evidence_items: List[Dict[str, Any]] = []

    if strongest_support:
        support_label = strongest_support.get("label") or strongest_support.get("detail") or "supportive synastry contact"
        summary_lines.append(f"Strongest support: {support_label}.")
        overall_evidence_items.append(
            {
                "detail": strongest_support.get("detail") or support_label,
                "delta": round(float(strongest_support.get("impact") or 0.0), 2),
                "source": strongest_support.get("source"),
                "source_anchor": strongest_support.get("source_anchor"),
                "rule_family_id": strongest_support.get("rule_family_id"),
                "summary": strongest_support.get("summary"),
            }
        )
    if strongest_compensation and strongest_compensation is not strongest_support:
        comp_label = strongest_compensation.get("label") or strongest_compensation.get("detail") or "compensation factor"
        summary_lines.append(f"Main compensation factor: {comp_label}.")
        overall_evidence_items.append(
            {
                "detail": strongest_compensation.get("detail") or comp_label,
                "delta": round(float(strongest_compensation.get("impact") or 0.0), 2),
                "source": strongest_compensation.get("source"),
                "source_anchor": strongest_compensation.get("source_anchor"),
                "rule_family_id": strongest_compensation.get("rule_family_id"),
                "summary": strongest_compensation.get("summary"),
            }
        )
    if strongest_challenge:
        challenge_label = strongest_challenge.get("label") or strongest_challenge.get("detail") or "pressure contact"
        summary_lines.append(f"Main pressure: {challenge_label}.")
        overall_evidence_items.append(
            {
                "detail": strongest_challenge.get("detail") or challenge_label,
                "delta": round(float(strongest_challenge.get("impact") or 0.0), 2),
                "source": strongest_challenge.get("source"),
                "source_anchor": strongest_challenge.get("source_anchor"),
                "rule_family_id": strongest_challenge.get("rule_family_id"),
                "summary": strongest_challenge.get("summary"),
            }
        )

    if receptions.get("mutual"):
        summary_lines.append("Mutual reception adds a stabilizing undertone inside the bond.")

    if not summary_lines:
        strongest = sorted(
            ((key, float((by_id.get(key) or {}).get("score") or 0.0)) for key in REPORT_CATEGORY_ORDER),
            key=lambda item: item[1],
            reverse=True,
        )[:2]
        if strongest:
            strongest_labels = ", ".join(str((categories.get(key) or {}).get("name") or key) for key, _value in strongest)
            summary_lines.append(f"Strongest dimensions: {strongest_labels}.")
        else:
            summary_lines.append("The current comparison does not yet produce a strong governing pattern.")

    components = {
        "compatibility": compatibility_component,
        "binding": binding_component,
        "growth": growth_component,
        "support_balance": support_balance_component,
        "challenge": challenge_component,
        "category_scores": {
            category_id: float((by_id.get(category_id) or {}).get("score") or 0.0)
            for category_id in REPORT_CATEGORY_ORDER
        },
        "positive_impact_total": positive_impact_total,
        "negative_impact_total": negative_impact_total,
        "reception_bonus": round(reception_bonus, 2),
        "legacy_weighted_total": round(legacy_weighted_total, 2),
        "headline_weighted_total": round(headline_weighted_total, 2),
        "headline_normalized_total": round(headline_normalized_total, 2),
        "headline_model": str(model.get("headline_model") or "legacy_component_blend"),
        "headline_weights": headline_weights,
        "headline_normalization": headline_normalization,
        "weights": weights,
    }
    return overall, summary_lines, overall_evidence_items[:5], components


def build_synastry_report(
    bundle_a: Dict[str, Any],
    bundle_b: Dict[str, Any],
    chart_a: Dict[str, Any],
    chart_b: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_options = _normalize_options(options)
    chart_data_a = bundle_a.get("chart_data") or {}
    chart_data_b = bundle_b.get("chart_data") or {}
    points_a = _build_points(chart_data_a, normalized_options)
    points_b = _build_points(chart_data_b, normalized_options)
    aspects = _cross_aspects(points_a, points_b, normalized_options)

    scores: Dict[str, float] = {}
    evidence: Dict[str, List[str]] = {}
    evidence_items: Dict[str, List[Dict[str, Any]]] = {}
    governance: Dict[str, Dict[str, Set[str]]] = {}
    active_rule_families: Set[str] = set()
    active_sources: Set[str] = set()
    supportive_links: List[Dict[str, Any]] = []
    challenging_links: List[Dict[str, Any]] = []

    _apply_aspect_rules(
        aspects,
        scores,
        evidence,
        evidence_items,
        governance,
        active_rule_families,
        active_sources,
        supportive_links,
        challenging_links,
    )
    _apply_element_rules(
        points_a,
        points_b,
        scores,
        evidence,
        evidence_items,
        governance,
        active_rule_families,
        active_sources,
    )

    receptions = _cross_receptions(points_a, points_b)
    _apply_reception_rules(
        receptions,
        scores,
        evidence,
        evidence_items,
        governance,
        active_rule_families,
        active_sources,
        supportive_links,
    )

    overlays = _house_overlays(
        points_a,
        str(chart_a.get("label") or "Chart A"),
        points_b,
        str(chart_b.get("label") or "Chart B"),
        _house_cusps(chart_data_a),
        _house_cusps(chart_data_b),
        normalized_options,
    )
    _apply_overlay_rules(
        overlays,
        scores,
        evidence,
        evidence_items,
        governance,
        active_rule_families,
        active_sources,
        supportive_links,
        challenging_links,
    )

    signature_a = _signature(points_a, chart_data_a, normalized_options)
    signature_b = _signature(points_b, chart_data_b, normalized_options)
    natal_unaspected_a = _natal_unaspected_points(points_a, normalized_options)
    natal_unaspected_b = _natal_unaspected_points(points_b, normalized_options)
    point_availability = _point_availability(chart_data_a, chart_data_b)

    _apply_partnership_ruler_rules(
        points_a,
        points_b,
        signature_a,
        signature_b,
        normalized_options,
        scores,
        evidence,
        evidence_items,
        governance,
        active_rule_families,
        active_sources,
        supportive_links,
        challenging_links,
    )

    _apply_compensation_rules(
        str(chart_a.get("label") or "Chart A"),
        str(chart_b.get("label") or "Chart B"),
        points_a,
        points_b,
        aspects,
        overlays,
        signature_a,
        signature_b,
        natal_unaspected_a,
        natal_unaspected_b,
        scores,
        evidence,
        evidence_items,
        governance,
        active_rule_families,
        active_sources,
        supportive_links,
        challenging_links,
    )

    _apply_category_adjustments(
        scores,
        evidence,
        evidence_items,
        governance,
        active_rule_families,
        active_sources,
    )

    strongest_support = sorted(
        supportive_links,
        key=lambda item: (-float(item.get("impact") or 0.0), str(item.get("label") or "")),
    )[:10]
    strongest_challenge = sorted(
        challenging_links,
        key=lambda item: (-float(item.get("impact") or 0.0), str(item.get("label") or "")),
    )[:10]
    category_payload = _build_category_payload(scores, evidence, evidence_items, governance)
    overall_score, summary_lines, overall_evidence_items, overall_components = _build_overall_score(
        category_payload,
        receptions,
        strongest_support,
        strongest_challenge,
    )
    categories = _category_meta()

    overall_payload = {
        "id": "overall",
        "name": (categories.get("overall") or {}).get("name") or "Overall Compatibility",
        "polarity": (categories.get("overall") or {}).get("polarity") or "positive",
        "score": overall_score,
        "raw_score": overall_score,
        "max_score": _category_scale("overall") or 100.0,
        "description": (categories.get("overall") or {}).get("description") or "",
        "evidence": summary_lines,
        "evidence_items": overall_evidence_items,
        "source_keys": sorted(active_sources),
        "rule_family_ids": sorted(active_rule_families),
        "components": overall_components,
    }

    catalog = _load_catalog()
    return {
        "summary": {
            "overall_score": overall_score,
            "summary_lines": summary_lines,
            "supportive_link_count": len(supportive_links),
            "challenging_link_count": len(challenging_links),
            "mutual_reception_count": len(receptions.get("mutual") or []),
            "overall_components": overall_components,
        },
        "governance": {
            "catalog_version": catalog.get("version"),
            "active_rule_family_ids": sorted(active_rule_families),
            "active_source_keys": sorted(active_sources),
            "rule_family_count": len(_rule_families()),
            "orb_profile": normalized_options["orb_profile"],
            "active_points": sorted(points_a.keys()),
            "point_availability": point_availability,
        },
        "options": normalized_options,
        "chart_a": chart_a,
        "chart_b": chart_b,
        "categories": [overall_payload, *category_payload],
        "aspect_links": aspects[:120],
        "top_supportive_links": strongest_support,
        "top_challenging_links": strongest_challenge,
        "overlays": overlays,
        "receptions": receptions,
        "sources": _source_basis(),
    }
