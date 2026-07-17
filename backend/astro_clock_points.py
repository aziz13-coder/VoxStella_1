from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SIGN_NAMES = [
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
]

CATALOG_FILENAME = "points_filtered_catalog.json"
FALLBACK_CATALOG_PATH = Path(r"C:\Program Files (x86)\Galaxy\docs\research\filtered_points\points_filtered_catalog.json")

OBJECT_ALIASES_BY_ID: Dict[int, Tuple[str, ...]] = {
    0: ("Sun",),
    1: ("Moon",),
    2: ("Mercury",),
    3: ("Venus",),
    4: ("Mars",),
    5: ("Jupiter",),
    6: ("Saturn",),
    7: ("Uranus",),
    8: ("Neptune",),
    9: ("Pluto",),
    10: ("Chiron",),
    11: ("Ceres",),
    12: ("Pallada", "Pallas"),
    13: ("Juno",),
    14: ("Vesta",),
    15: ("Eros",),
    16: ("Psyche",),
    17: ("Proserpina",),
    18: ("Lilith", "Black Moon Lilith"),
    19: ("Selena", "White Moon Selena"),
    20: ("Rahu", "North Node", "Node", "Ascending Node"),
    21: ("Ketu", "South Node", "Descending Node"),
}

OBJECT_NAMES_BY_ID = {object_id: aliases[0] for object_id, aliases in OBJECT_ALIASES_BY_ID.items()}
PLANET_OBJECTS = {name: object_id for object_id, aliases in OBJECT_ALIASES_BY_ID.items() for name in aliases}

NATAL_HIT_OBJECTS = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
    "Uranus": 7,
    "Neptune": 8,
    "Pluto": 9,
}

OBJECT_ORB_GROUP = {
    "Sun": 0,
    "Moon": 0,
    "Mercury": 1,
    "Venus": 1,
    "Mars": 2,
    "Jupiter": 3,
    "Saturn": 3,
    "Uranus": 4,
    "Neptune": 4,
    "Pluto": 4,
}

PINNED_PRIMARY_MANAGER_BY_SIGN = {
    0: (4, "Mars"),
    1: (3, "Venus"),
    2: (2, "Mercury"),
    3: (1, "Moon"),
    4: (0, "Sun"),
    5: (11, "Ceres"),
    6: (10, "Chiron"),
    7: (9, "Pluto"),
    8: (5, "Jupiter"),
    9: (6, "Saturn"),
    10: (7, "Uranus"),
    11: (8, "Neptune"),
}

GRADARH_ONLY_7_BY_REMAINDER = {
    0: (4, "Mars"),
    1: (0, "Sun"),
    2: (3, "Venus"),
    3: (2, "Mercury"),
    4: (1, "Moon"),
    5: (6, "Saturn"),
    6: (5, "Jupiter"),
}

ORB_OBJ = [
    [6.0, 5.5, 5.0, 4.5, 3.0, 2.0, 1.5],
    [5.5, 5.0, 4.5, 4.0, 2.5, 1.5, 1.0],
    [5.0, 4.5, 4.0, 3.5, 2.5, 1.5, 1.0],
    [4.5, 4.0, 3.5, 3.0, 2.0, 1.5, 1.0],
    [4.0, 3.5, 3.0, 2.5, 1.5, 1.0, 0.5],
    [3.5, 3.0, 2.5, 2.0, 1.0, 1.0, 0.5],
    [3.0, 2.5, 2.0, 1.5, 1.0, 1.0, 0.3],
    [2.5, 2.0, 1.5, 1.0, 0.8, 0.8, 0.6],
    [1.0, 1.0, 1.0, 1.0, 0.2, 0.2, 0.2],
    [0.5, 0.5, 0.5, 0.5, 0.1, 0.1, 0.1],
    [1.0, 0.7, 0.5, 0.4, 0.3, 0.2, 0.1],
]

SPECIAL_POINT_ORB_GROUP = 7

ENABLED_ASPECTS = [
    {"id": 0, "name": "Conjunction", "degrees": 0.0, "group": 0},
    {"id": 6, "name": "Sextile", "degrees": 60.0, "group": 3},
    {"id": 9, "name": "Square", "degrees": 90.0, "group": 2},
    {"id": 12, "name": "Trine", "degrees": 120.0, "group": 2},
    {"id": 18, "name": "Opposition", "degrees": 180.0, "group": 1},
]

PLANET_CHANNELS = {
    "Sun": "identity, will, vitality, visibility, authority",
    "Moon": "emotion, habit, body, family, needs, fluctuation",
    "Mercury": "thought, speech, skill, trade, writing, analysis",
    "Venus": "attraction, value, art, relationship, ease, aesthetics",
    "Mars": "action, drive, conflict, competition, force",
    "Jupiter": "expansion, status, teaching, law, wealth, opportunity",
    "Saturn": "structure, duty, constraint, authority, discipline",
    "Uranus": "disruption, independence, technology, sudden change",
    "Neptune": "imagination, idealism, spirituality, ambiguity",
    "Pluto": "intensity, power, crisis, transformation, hidden force",
}

ASPECT_TONES = {
    "Conjunction": ("direct fusion / amplification", "neutral"),
    "Sextile": ("opportunity / usable support", "easy"),
    "Square": ("friction / pressure / challenge", "hard"),
    "Trine": ("easy flow / natural support", "easy"),
    "Opposition": ("polarity / confrontation / externalization", "hard"),
}

TOKEN_RE = re.compile(r"(?:MS\d{2}|PM\d{2}|[PMTG]\d{3})")
SIGNED_TOKEN_RE = re.compile(r"([+-]?)(MS\d{2}|PM\d{2}|[PMTG]\d{3})")


def normalize360(value: float) -> float:
    return ((float(value) % 360.0) + 360.0) % 360.0


def normalize_aspect_distance(delta: float) -> float:
    distance = normalize360(delta)
    if distance > 180.0:
        distance = 360.0 - distance
    return distance


def short_arc_midpoint(left: float, right: float) -> float:
    delta = ((float(right) - float(left) + 540.0) % 360.0) - 180.0
    midpoint = normalize360(float(left) + delta / 2.0)
    return 0.0 if abs(midpoint - 360.0) < 1e-9 else midpoint


def compute_fortune_longitude(ascendant: float, sun: float, moon: float, is_day: bool) -> float:
    if is_day:
        return normalize360(float(ascendant) + float(moon) - float(sun))
    return normalize360(float(ascendant) + float(sun) - float(moon))


def compute_spirit_longitude(ascendant: float, sun: float, moon: float, is_day: bool) -> float:
    if is_day:
        return normalize360(float(ascendant) + float(sun) - float(moon))
    return normalize360(float(ascendant) + float(moon) - float(sun))


@lru_cache(maxsize=1)
def load_filtered_points_catalog() -> Dict[str, Any]:
    local_path = Path(__file__).resolve().with_name(CATALOG_FILENAME)
    paths = [local_path, FALLBACK_CATALOG_PATH]
    for path in paths:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        points = data.get("points")
        if not isinstance(points, list):
            raise ValueError(f"Invalid points catalog at {path}")
        return {"meta": dict(data.get("meta") or {}), "points": [dict(row) for row in points if isinstance(row, dict)]}
    raise FileNotFoundError(f"Missing {CATALOG_FILENAME}")


def _finite_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except Exception:
        return None
    return number if math.isfinite(number) else None


def _name_key(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _planet_rows(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw = chart_data.get("planets") if isinstance(chart_data, dict) else None
    rows: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, dict):
        iterator = []
        for name, payload in raw.items():
            if isinstance(payload, dict):
                row = dict(payload)
                row.setdefault("planet", name)
                iterator.append(row)
    elif isinstance(raw, list):
        iterator = [dict(row) for row in raw if isinstance(row, dict)]
    else:
        iterator = []

    for row in iterator:
        name = str(row.get("planet") or row.get("name") or "").strip()
        if not name:
            continue
        lon = _finite_float(row.get("longitude"))
        if lon is None:
            continue
        clean = dict(row)
        clean["planet"] = name
        clean["longitude"] = normalize360(lon)
        rows[_name_key(name)] = clean
        for object_id, aliases in OBJECT_ALIASES_BY_ID.items():
            if _name_key(name) in {_name_key(alias) for alias in aliases}:
                rows[_name_key(OBJECT_NAMES_BY_ID[object_id])] = clean
                for alias in aliases:
                    rows[_name_key(alias)] = clean
    return rows


def _lookup_object(planets: Dict[str, Dict[str, Any]], object_id: int) -> Tuple[Optional[Dict[str, Any]], str]:
    primary_name = OBJECT_NAMES_BY_ID.get(object_id, f"P{object_id:03d}")
    for alias in OBJECT_ALIASES_BY_ID.get(object_id, (primary_name,)):
        row = planets.get(_name_key(alias))
        if row:
            return row, primary_name
    if object_id == 21:
        for alias in OBJECT_ALIASES_BY_ID[20]:
            rahu = planets.get(_name_key(alias))
            if rahu and _finite_float(rahu.get("longitude")) is not None:
                row = dict(rahu)
                row["planet"] = primary_name
                row["longitude"] = normalize360(float(rahu["longitude"]) + 180.0)
                return row, primary_name
    if object_id == 20:
        for alias in OBJECT_ALIASES_BY_ID[21]:
            ketu = planets.get(_name_key(alias))
            if ketu and _finite_float(ketu.get("longitude")) is not None:
                row = dict(ketu)
                row["planet"] = primary_name
                row["longitude"] = normalize360(float(ketu["longitude"]) + 180.0)
                return row, primary_name
    return None, primary_name


def _houses(chart_data: Dict[str, Any]) -> List[Optional[float]]:
    raw = None
    for key in ("house_cusps_exact", "houses_exact", "house_cusps", "houses"):
        candidate = chart_data.get(key)
        if isinstance(candidate, (list, tuple)) and candidate:
            raw = candidate
            break
    if not isinstance(raw, (list, tuple)):
        return []
    out: List[Optional[float]] = []
    for item in raw[:12]:
        value = _finite_float(item)
        out.append(normalize360(value) if value is not None else None)
    return out


def _house_cusp(houses: List[Optional[float]], house_number: int, chart_data: Dict[str, Any]) -> Optional[float]:
    if house_number == 1:
        asc = _finite_float(chart_data.get("ascendant_exact"))
        if asc is None:
            asc = _finite_float(chart_data.get("ascendant"))
        if asc is not None:
            return normalize360(asc)
    if house_number == 10:
        mc = _finite_float(chart_data.get("midheaven_exact"))
        if mc is None:
            mc = _finite_float(chart_data.get("midheaven"))
        if mc is not None:
            return normalize360(mc)
    index = house_number - 1
    if 0 <= index < len(houses) and houses[index] is not None:
        return houses[index]
    if house_number == 7:
        asc = _finite_float(chart_data.get("ascendant_exact"))
        if asc is None:
            asc = _finite_float(chart_data.get("ascendant"))
        if asc is not None:
            return normalize360(asc + 180.0)
    if house_number == 4:
        mc = _finite_float(chart_data.get("midheaven_exact"))
        if mc is None:
            mc = _finite_float(chart_data.get("midheaven"))
        if mc is not None:
            return normalize360(mc + 180.0)
    return None


def _is_day_chart(planets: Dict[str, Dict[str, Any]], chart_data: Dict[str, Any]) -> Optional[bool]:
    sect = chart_data.get("sect") if isinstance(chart_data, dict) else None
    if isinstance(sect, dict):
        sect_value = str(sect.get("chart_sect") or sect.get("sect") or "").strip().lower()
        if sect_value.startswith("day") or sect_value.startswith("diurnal"):
            return True
        if sect_value.startswith("night") or sect_value.startswith("nocturnal"):
            return False
    sect_value = str(chart_data.get("chart_sect") or chart_data.get("sect") or "").strip().lower()
    if sect_value.startswith("day") or sect_value.startswith("diurnal"):
        return True
    if sect_value.startswith("night") or sect_value.startswith("nocturnal"):
        return False
    sun = planets.get(_name_key("Sun")) or {}
    try:
        sun_house = float(sun.get("house"))
        return 7.0 <= sun_house < 13.0
    except Exception:
        return None


def _sex_code(value: Any) -> int:
    text = str(value if value is not None else "").strip().lower()
    if text in {"1", "male", "m"}:
        return 1
    if text in {"2", "female", "f"}:
        return 2
    return 0


def _reason(code: str, message: Optional[str] = None, *, token: Optional[str] = None, detail: Optional[str] = None) -> Dict[str, str]:
    row: Dict[str, str] = {"code": code, "message": message or code.replace("_", " ")}
    if token:
        row["token"] = token
    if detail:
        row["detail"] = detail
    return row


def _dedupe_reasons(reasons: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: set[Tuple[str, str, str]] = set()
    out: List[Dict[str, str]] = []
    for reason in reasons:
        key = (str(reason.get("code") or ""), str(reason.get("token") or ""), str(reason.get("detail") or ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(reason)
    return out


def _token_label(token: str) -> str:
    if token.startswith("MS"):
        return f"Gradarh ruler of house {int(token[2:])}" if token[2:].isdigit() else token
    if token.startswith("PM"):
        return f"Cusp {int(token[2:])} manager midpoint" if token[2:].isdigit() else token
    if token.startswith("G"):
        return f"Fixed zodiac degree {int(token[1:])}" if token[1:].isdigit() else token
    if token.startswith("P"):
        try:
            idx = int(token[1:])
        except Exception:
            return token
        if idx in OBJECT_NAMES_BY_ID:
            return OBJECT_NAMES_BY_ID[idx]
        if 24 <= idx <= 35:
            house = idx - 23
            if house == 1:
                return "Ascendant"
            if house == 4:
                return "IC"
            if house == 7:
                return "Descendant"
            if house == 10:
                return "Midheaven"
            return f"Cusp {house}"
        return token
    if token.startswith("M"):
        return f"Manager of house {int(token[1:])}" if token[1:].isdigit() else token
    if token == "T001":
        return "Fortune"
    if token == "T003":
        return "Spirit"
    return token


def format_zodiac(longitude: float) -> Dict[str, Any]:
    lon = normalize360(longitude)
    sign_index = int(lon // 30.0) % 12
    in_sign = lon - sign_index * 30.0
    degree = int(math.floor(in_sign))
    minute = int(round((in_sign - degree) * 60.0))
    if minute >= 60:
        minute = 0
        degree += 1
    if degree >= 30:
        degree = 0
        sign_index = (sign_index + 1) % 12
    sign = SIGN_NAMES[sign_index]
    return {
        "sign": sign,
        "degree": degree,
        "minute": minute,
        "formatted": f"{degree} {sign} {minute:02d}",
    }


def _precision_meta(chart_data: Dict[str, Any], planets: Dict[str, Dict[str, Any]], is_day: Optional[bool]) -> Dict[str, bool]:
    houses = _houses(chart_data)
    has_houses = len([item for item in houses if item is not None]) >= 12
    has_asc = _house_cusp(houses, 1, chart_data) is not None
    has_mc = _house_cusp(houses, 10, chart_data) is not None
    has_lights = bool(_lookup_object(planets, 0)[0] and _lookup_object(planets, 1)[0])
    return {
        "has_exact_time": bool(has_houses and has_asc and has_mc),
        "has_houses": bool(has_houses),
        "has_manager_table": True,
        "has_lights": bool(has_lights),
        "has_day_night": is_day is not None,
    }


def _resolve_p_token(chart_data: Dict[str, Any], planets: Dict[str, Dict[str, Any]], token: str) -> Dict[str, Any]:
    try:
        idx = int(token[1:])
    except Exception:
        return {"available": False, "reason": _reason("invalid_token", "Invalid point token.", token=token)}
    if idx in OBJECT_NAMES_BY_ID:
        row, object_name = _lookup_object(planets, idx)
        lon = _finite_float((row or {}).get("longitude"))
        if lon is None:
            return {
                "available": False,
                "reason": _reason("missing_object", f"{object_name} is unavailable.", token=token, detail=object_name),
            }
        return {"available": True, "token": token, "object_id": idx, "object_name": object_name, "longitude": normalize360(lon)}
    if 24 <= idx <= 35:
        house_number = idx - 23
        cusp = _house_cusp(_houses(chart_data), house_number, chart_data)
        if cusp is None:
            return {
                "available": False,
                "reason": _reason("missing_house_cusp", f"House {house_number} cusp is unavailable.", token=token, detail=str(house_number)),
            }
        return {"available": True, "token": token, "house_number": house_number, "longitude": normalize360(cusp)}
    return {"available": False, "reason": _reason("unsupported_token", "Unsupported point token.", token=token)}


def resolve_manager_token(chart_data: Dict[str, Any], token: str) -> Dict[str, Any]:
    chart = chart_data if isinstance(chart_data, dict) else {}
    planets = _planet_rows(chart)
    try:
        house_number = int(str(token or "")[1:])
    except Exception:
        return {"available": False, "reason": "invalid_manager_token", "token": token}
    cusp = _house_cusp(_houses(chart), house_number, chart)
    if cusp is None:
        return {"available": False, "reason": "missing_house_cusp", "token": token}
    sign_id = int(normalize360(cusp) // 30.0) % 12
    object_id, manager_name = PINNED_PRIMARY_MANAGER_BY_SIGN.get(sign_id, (None, None))
    if manager_name is None or object_id is None:
        return {"available": False, "reason": "missing_manager_table", "token": token}
    row, object_name = _lookup_object(planets, int(object_id))
    longitude = _finite_float((row or {}).get("longitude"))
    if longitude is None:
        return {
            "available": False,
            "reason": "missing_manager_object",
            "token": token,
            "sign": SIGN_NAMES[sign_id],
            "object_name": manager_name,
        }
    return {
        "available": True,
        "token": token,
        "sign": SIGN_NAMES[sign_id],
        "object_name": object_name,
        "object_id": int(object_id),
        "longitude": normalize360(longitude),
    }


def resolve_gradarh_token(chart_data: Dict[str, Any], token: str) -> Dict[str, Any]:
    chart = chart_data if isinstance(chart_data, dict) else {}
    planets = _planet_rows(chart)
    try:
        house_number = int(str(token or "")[2:])
    except Exception:
        return {"available": False, "reason": "invalid_gradarh_token", "token": token}
    cusp = _house_cusp(_houses(chart), house_number, chart)
    if cusp is None:
        return {"available": False, "reason": "missing_house_cusp", "token": token}
    remainder = int(math.floor(normalize360(cusp))) % 7
    object_id, ruler_name = GRADARH_ONLY_7_BY_REMAINDER[remainder]
    row, object_name = _lookup_object(planets, object_id)
    longitude = _finite_float((row or {}).get("longitude"))
    if longitude is None:
        return {
            "available": False,
            "reason": "missing_gradarh_object",
            "token": token,
            "object_name": ruler_name,
        }
    return {
        "available": True,
        "token": token,
        "house_number": house_number,
        "object_name": object_name,
        "object_id": object_id,
        "longitude": normalize360(longitude),
    }


def _resolve_ms_token(chart_data: Dict[str, Any], token: str) -> Dict[str, Any]:
    resolved = resolve_gradarh_token(chart_data, token)
    if not resolved.get("available"):
        return {"available": False, "reason": _reason(str(resolved.get("reason") or "missing_gradarh"), "Gradarh ruler is unavailable.", token=token, detail=str(resolved.get("object_name") or ""))}
    return resolved


def _resolve_m_token(chart_data: Dict[str, Any], token: str) -> Dict[str, Any]:
    resolved = resolve_manager_token(chart_data, token)
    if not resolved.get("available"):
        return {"available": False, "reason": _reason(str(resolved.get("reason") or "missing_manager"), "House manager is unavailable.", token=token, detail=str(resolved.get("object_name") or ""))}
    return resolved


def _resolve_t_token(
    chart_data: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    token: str,
    is_day: Optional[bool],
) -> Dict[str, Any]:
    if token not in {"T001", "T003"}:
        return {"available": False, "reason": _reason("unsupported_token", "Unsupported helper token.", token=token)}
    asc = _resolve_p_token(chart_data, planets, "P024")
    sun = _resolve_p_token(chart_data, planets, "P000")
    moon = _resolve_p_token(chart_data, planets, "P001")
    missing = [item["reason"] for item in (asc, sun, moon) if not item.get("available")]
    if is_day is None:
        missing.append(_reason("day_night_unavailable", "Day/night state is unavailable.", token=token))
    if missing:
        return {"available": False, "reason": missing[0], "reasons": missing}
    if token == "T001":
        longitude = compute_fortune_longitude(float(asc["longitude"]), float(sun["longitude"]), float(moon["longitude"]), bool(is_day))
    else:
        longitude = compute_spirit_longitude(float(asc["longitude"]), float(sun["longitude"]), float(moon["longitude"]), bool(is_day))
    return {"available": True, "token": token, "longitude": longitude}


def _resolve_pm_token(chart_data: Dict[str, Any], planets: Dict[str, Dict[str, Any]], token: str) -> Dict[str, Any]:
    try:
        house_number = int(token[2:])
    except Exception:
        return {"available": False, "reason": _reason("invalid_pm_token", "Invalid midpoint helper token.", token=token)}
    cusp = _resolve_p_token(chart_data, planets, f"P{house_number + 23:03d}")
    manager = _resolve_m_token(chart_data, f"M{house_number:03d}")
    missing = []
    if not cusp.get("available"):
        missing.append(cusp["reason"])
    if not manager.get("available"):
        missing.append(manager["reason"])
    if missing:
        return {"available": False, "reason": missing[0], "reasons": missing}
    return {
        "available": True,
        "token": token,
        "longitude": short_arc_midpoint(float(cusp["longitude"]), float(manager["longitude"])),
    }


def _resolve_g_token(token: str) -> Dict[str, Any]:
    try:
        degree = float(int(token[1:]))
    except Exception:
        return {"available": False, "reason": _reason("invalid_fixed_degree_token", "Invalid fixed degree token.", token=token)}
    return {"available": True, "token": token, "longitude": normalize360(degree)}


def _resolve_token(
    token: str,
    chart_data: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    is_day: Optional[bool],
) -> Dict[str, Any]:
    if token.startswith("MS"):
        return _resolve_ms_token(chart_data, token)
    if token.startswith("PM"):
        return _resolve_pm_token(chart_data, planets, token)
    if token.startswith("P"):
        return _resolve_p_token(chart_data, planets, token)
    if token.startswith("M"):
        return _resolve_m_token(chart_data, token)
    if token.startswith("T"):
        return _resolve_t_token(chart_data, planets, token, is_day)
    if token.startswith("G"):
        return _resolve_g_token(token)
    return {"available": False, "reason": _reason("unsupported_token", "Unsupported point token.", token=token)}


def _extract_tokens(expr: str) -> List[str]:
    return TOKEN_RE.findall(expr or "")


def _formula_tokens(expr: str) -> Dict[str, str]:
    return {token: _token_label(token) for token in _extract_tokens(expr)}


def _eval_expression(
    expr: str,
    chart_data: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    is_day: Optional[bool],
) -> Tuple[Optional[float], List[Dict[str, str]]]:
    matches = list(SIGNED_TOKEN_RE.finditer(expr or ""))
    if not matches:
        return None, [_reason("formula_unavailable", "Formula tokens are unavailable.")]
    total = 0.0
    reasons: List[Dict[str, str]] = []
    for match in matches:
        sign = -1.0 if match.group(1) == "-" else 1.0
        token = match.group(2)
        resolved = _resolve_token(token, chart_data, planets, is_day)
        if not resolved.get("available"):
            reason_list = resolved.get("reasons") if isinstance(resolved.get("reasons"), list) else [resolved.get("reason")]
            reasons.extend([reason for reason in reason_list if isinstance(reason, dict)])
            continue
        total += sign * float(resolved["longitude"])
    if reasons:
        return None, _dedupe_reasons(reasons)
    return normalize360(total), []


def _allowed_orb(object_name: str, aspect_group: int) -> float:
    object_group = OBJECT_ORB_GROUP.get(object_name, 4)
    orb_a = ORB_OBJ[SPECIAL_POINT_ORB_GROUP][aspect_group]
    orb_b = ORB_OBJ[object_group][aspect_group]
    allowed = math.sqrt(max(0.0, orb_a * orb_b))
    return max(0.01, allowed)


def _hit_interpretation(point_name: str, object_name: str, aspect_name: str) -> Dict[str, str]:
    aspect_tone, tone_group = ASPECT_TONES.get(aspect_name, ("activation", "neutral"))
    channel = PLANET_CHANNELS.get(object_name, "")
    return {
        "planet_channel": channel,
        "aspect_tone": aspect_tone,
        "tone_group": tone_group,
        "summary": f"{point_name} has a symbolic activation through {object_name} by {aspect_name.lower()}.",
    }


def _point_hits(longitude: float, planets: Dict[str, Dict[str, Any]], point_name: str = "Point") -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for object_name, object_id in NATAL_HIT_OBJECTS.items():
        row, _ = _lookup_object(planets, object_id)
        object_longitude = _finite_float((row or {}).get("longitude"))
        if object_longitude is None:
            continue
        aspect_distance = normalize_aspect_distance(float(longitude) - object_longitude)
        for aspect in ENABLED_ASPECTS:
            fval = abs(aspect_distance - float(aspect["degrees"]))
            allowed = _allowed_orb(object_name, int(aspect["group"]))
            if fval <= allowed:
                strength = (allowed - fval) / allowed
                aspect_name = str(aspect["name"])
                hits.append({
                    "object": object_name,
                    "object_id": object_id,
                    "object_name": object_name,
                    "object_longitude": round(normalize360(object_longitude), 6),
                    "aspect": aspect_name,
                    "aspect_degrees": float(aspect["degrees"]),
                    "orb": round(fval, 6),
                    "fval": round(fval, 6),
                    "allowed_orb": round(allowed, 6),
                    "strength": round(strength, 6),
                    "interpretation": _hit_interpretation(point_name, object_name, aspect_name),
                })
    hits.sort(key=lambda item: (-float(item.get("strength") or 0.0), float(item.get("orb") or 999.0), str(item.get("object_name") or "")))
    return hits


def _row_used_formula(row: Dict[str, Any], is_day: Optional[bool]) -> Tuple[str, str]:
    formula_kind = str(row.get("formula_kind") or "").strip().lower()
    if formula_kind == "midpoint":
        return str(row.get("day_formula") or row.get("base_formula") or row.get("formula") or ""), "midpoint"
    day_formula = str(row.get("day_formula") or row.get("base_formula") or row.get("formula") or "")
    night_formula = str(row.get("night_formula") or day_formula)
    if is_day is True:
        return day_formula, "day"
    if is_day is False:
        return night_formula, "night"
    if day_formula == night_formula:
        return day_formula, "same"
    return day_formula, "unknown"


def _midpoint_longitude(
    row: Dict[str, Any],
    chart_data: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    is_day: Optional[bool],
) -> Tuple[Optional[float], List[Dict[str, str]]]:
    tokens = _extract_tokens(str(row.get("day_formula") or row.get("base_formula") or row.get("formula") or ""))
    if len(tokens) < 2:
        tokens = [str(row.get("cp1") or "").strip(), str(row.get("cp2") or "").strip()]
        tokens = [token for token in tokens if token]
    if len(tokens) < 2:
        return None, [_reason("formula_unavailable", "Midpoint formula tokens are unavailable.")]
    left = _resolve_token(tokens[0], chart_data, planets, is_day)
    right = _resolve_token(tokens[1], chart_data, planets, is_day)
    reasons = []
    for item in (left, right):
        if not item.get("available"):
            reason_list = item.get("reasons") if isinstance(item.get("reasons"), list) else [item.get("reason")]
            reasons.extend([reason for reason in reason_list if isinstance(reason, dict)])
    if reasons:
        return None, _dedupe_reasons(reasons)
    return short_arc_midpoint(float(left["longitude"]), float(right["longitude"])), []


def _point_row(
    catalog_row: Dict[str, Any],
    chart_data: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    is_day: Optional[bool],
    has_exact_time: bool,
    sex_code: int,
) -> Dict[str, Any]:
    unavailable: List[Dict[str, str]] = []
    row_sex = str(catalog_row.get("sex") or "undefined").strip().lower()
    requires_exact_time = bool(catalog_row.get("requires_exact_time"))
    if requires_exact_time and not has_exact_time:
        unavailable.append(_reason("exact_time_required", "Exact time, angles, and house cusps are required."))
    if row_sex in {"male", "m"} and sex_code != 1:
        unavailable.append(_reason("sex_code_required", "Male subject code is required for this row."))
    elif row_sex in {"female", "f"} and sex_code != 2:
        unavailable.append(_reason("sex_code_required", "Female subject code is required for this row."))

    formula, used = _row_used_formula(catalog_row, is_day)
    if str(catalog_row.get("formula_kind") or "").strip().lower() == "part_pdn" and used == "unknown":
        unavailable.append(_reason("day_night_unavailable", "Day/night state is unavailable."))

    longitude: Optional[float] = None
    formula_reasons: List[Dict[str, str]] = []
    if not unavailable:
        if str(catalog_row.get("formula_kind") or "").strip().lower() == "midpoint":
            longitude, formula_reasons = _midpoint_longitude(catalog_row, chart_data, planets, is_day)
        else:
            longitude, formula_reasons = _eval_expression(formula, chart_data, planets, is_day)
    unavailable.extend(formula_reasons)
    unavailable = _dedupe_reasons(unavailable)

    available = longitude is not None and not unavailable
    name = str(catalog_row.get("name") or "Point").strip() or "Point"
    hits = _point_hits(longitude, planets, name) if available and longitude is not None else []
    score = round(sum(float(hit.get("strength") or 0.0) for hit in hits), 6)

    return {
        "key": str(catalog_row.get("key") or catalog_row.get("source_row") or name),
        "source_row": str(catalog_row.get("source_row") or ""),
        "name": name,
        "status": str(catalog_row.get("keep_reason") or "filtered"),
        "requires_exact_time": requires_exact_time,
        "available": bool(available),
        "longitude": round(float(longitude), 6) if longitude is not None else None,
        "zodiac": format_zodiac(float(longitude)) if longitude is not None else None,
        "formula": {
            "day": str(catalog_row.get("day_formula") or ""),
            "night": str(catalog_row.get("night_formula") or catalog_row.get("day_formula") or ""),
            "used": used,
            "tokens": _formula_tokens(formula),
        },
        "score": score,
        "point_score": score,
        "hits": hits,
        "ui_severity": str(catalog_row.get("ui_severity") or "neutral"),
        "ui_color": str(catalog_row.get("ui_color") or "slate"),
        "category": str(catalog_row.get("category") or "general_symbolic"),
        "unavailable_reasons": unavailable,
    }


def _closest_orb(point: Dict[str, Any]) -> float:
    hits = point.get("hits") if isinstance(point, dict) else None
    if not isinstance(hits, list) or not hits:
        return 999.0
    return min(float(hit.get("orb") if hit.get("orb") is not None else 999.0) for hit in hits if isinstance(hit, dict))


def _top_hit_row(point: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "key": point.get("key"),
        "source_row": point.get("source_row"),
        "name": point.get("name"),
        "longitude": point.get("longitude"),
        "zodiac": point.get("zodiac"),
        "point_score": point.get("point_score"),
        "score": point.get("score"),
        "ui_severity": point.get("ui_severity"),
        "ui_color": point.get("ui_color"),
        "category": point.get("category"),
        "hits": point.get("hits") or [],
    }


def _timestamp_meta(timestamp_iso: Optional[str]) -> Dict[str, Optional[str]]:
    if not timestamp_iso:
        return {"datetime": None, "datetime_utc": None}
    text = str(timestamp_iso)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        utc_text = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        utc_text = text
    return {"datetime": text, "datetime_utc": utc_text}


def compute_symbolic_points_payload(
    chart_data: Dict[str, Any],
    timestamp_iso: Optional[str] = None,
    *,
    sex_code: Any = None,
    latitude: Any = None,
    longitude: Any = None,
    house_system: Optional[str] = None,
) -> Dict[str, Any]:
    chart = chart_data if isinstance(chart_data, dict) else {}
    planets = _planet_rows(chart)
    is_day = _is_day_chart(planets, chart)
    precision = _precision_meta(chart, planets, is_day)
    normalized_sex = _sex_code(sex_code)
    catalog = load_filtered_points_catalog()

    points = [
        _point_row(row, chart, planets, is_day, precision["has_exact_time"], normalized_sex)
        for row in catalog["points"]
    ]
    available_points = [row for row in points if row.get("available")]
    active_points = [row for row in available_points if isinstance(row.get("hits"), list) and len(row["hits"]) > 0]
    active_points.sort(
        key=lambda row: (
            -float(row.get("point_score") or 0.0),
            _closest_orb(row),
            str(row.get("name") or ""),
        )
    )
    top_hits = [_top_hit_row(row) for row in active_points[:10]]
    unavailable = [
        {
            "key": row.get("key"),
            "source_row": row.get("source_row"),
            "name": row.get("name"),
            "reasons": row.get("unavailable_reasons") or [],
        }
        for row in points
        if row.get("available") is False
    ]

    missing_hit_objects = [name for name, object_id in NATAL_HIT_OBJECTS.items() if _lookup_object(planets, object_id)[0] is None]
    meta = catalog.get("meta") or {}
    timestamp_meta = _timestamp_meta(timestamp_iso)
    return {
        "points_catalog_version": f"filtered-{int(meta.get('kept') or len(catalog['points']))}",
        "computed_count": len(available_points),
        "active_count": len(active_points),
        "unavailable_count": len(unavailable),
        "top_hits": top_hits,
        "unavailable": unavailable,
        "chart_meta": {
            "datetime": timestamp_meta["datetime"],
            "datetime_utc": timestamp_meta["datetime_utc"],
            "latitude": _finite_float(latitude if latitude is not None else chart.get("latitude")),
            "longitude": _finite_float(longitude if longitude is not None else chart.get("longitude")),
            "house_system": house_system or chart.get("house_system_code") or chart.get("house_system"),
            "is_day": is_day,
            "sex_code": normalized_sex,
            "precision": precision,
            "missing_hit_objects": missing_hit_objects,
        },
        "points": points,
    }
