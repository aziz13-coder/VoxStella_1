from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from astrocartography_goal_models import get_goal_model, list_goal_models


ANGULAR_HOUSE_TO_ANGLE = {
    1: "ASC",
    4: "IC",
    7: "DSC",
    10: "MC",
}
ANGLE_TO_HOUSE = {angle: house for house, angle in ANGULAR_HOUSE_TO_ANGLE.items()}
RELOCATION_ANGULAR_ORB_DEG = 5.0
DEFAULT_DISTANCE_SENSITIVITY_PROFILES = {
    "conservative": 0.6,
    "standard": 1.0,
    "wide": 1.4,
}
DIMINISHING_RETURN_FACTORS = (1.0, 0.8, 0.65, 0.5)
DEFAULT_EVIDENCE_POLICY = {
    "min_independent_signals": 1,
    "weak_magnitude": 2.5,
    "strong_magnitude": 8.0,
    "block_caps": {
        "natal_lines": 12.0,
        "crossing_interactions": 6.0,
        "relocation": 8.0,
        "transit_overlay": 4.0,
    },
}

BENEFICS = {"Venus", "Jupiter", "Sun", "Moon"}
MALEFICS = {"Mars", "Saturn", "Neptune", "Pluto"}
HEURISTIC_BENEFICS = {"Jupiter", "Venus", "Sun", "Moon"}
HEURISTIC_MALEFICS = {"Mars", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"}
ACCIDENT_HEURISTIC_CORE = {"Mars", "Uranus", "Pluto"}
ACCIDENT_HEURISTIC_SECONDARY = {"Saturn", "Chiron"}
GAMBLING_SUPPORT_BODIES = {"Jupiter", "Venus", "Mercury", "Sun", "Moon"}
GAMBLING_CAUTION_BODIES = {"Saturn", "Mars", "Neptune", "Pluto", "Uranus"}
SUPPORTIVE_ASPECTS = {"conjunction", "sextile", "trine"}
HARD_ASPECTS = {"square", "opposition"}
DEFAULT_SCORE_POLARITY = "higher_is_better"
SUPPORTED_SCORE_POLARITIES = {DEFAULT_SCORE_POLARITY, "higher_is_worse"}

PLANET_STRENGTH_HOUSE_WEIGHTS = {
    1: 1.0,
    10: 1.0,
    11: 0.9,
    5: 0.85,
    2: 0.75,
    9: 0.6,
    7: 0.55,
    4: 0.45,
    3: 0.35,
    8: 0.28,
    6: 0.18,
    12: 0.12,
}


def goal_model_score_polarity(model: Dict[str, Any]) -> str:
    value = str((model or {}).get("score_polarity") or DEFAULT_SCORE_POLARITY).strip().lower()
    if value in {"higher_is_worse", "warning_high_is_worse", "risk_high_is_worse"}:
        return "higher_is_worse"
    if value in SUPPORTED_SCORE_POLARITIES:
        return value
    return DEFAULT_SCORE_POLARITY


def get_goal_score_polarity(goal_id: str) -> str:
    try:
        return goal_model_score_polarity(get_goal_model(goal_id))
    except Exception:
        return DEFAULT_SCORE_POLARITY


def _attach_goal_score_polarity(result: Dict[str, Any], score_polarity: str) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return result
    goal = result.get("goal")
    if isinstance(goal, dict):
        goal["score_polarity"] = score_polarity
    return result

SPECULATION_SUPPORT_WEIGHTS = {
    ("Jupiter", 5): 1.8,
    ("Jupiter", 11): 1.6,
    ("Jupiter", 2): 0.9,
    ("Jupiter", 8): 0.7,
    ("Venus", 5): 1.5,
    ("Venus", 11): 1.3,
    ("Venus", 2): 0.8,
    ("Venus", 8): 0.6,
    ("Mercury", 5): 1.1,
    ("Mercury", 11): 1.0,
    ("Mercury", 2): 0.6,
    ("Mercury", 8): 0.5,
    ("Sun", 5): 0.9,
    ("Sun", 11): 0.7,
    ("Sun", 2): 0.5,
    ("Sun", 8): 0.3,
    ("Moon", 5): 0.7,
    ("Moon", 11): 0.5,
    ("Moon", 2): 0.4,
    ("Moon", 8): 0.3,
}

SPECULATION_DRAG_WEIGHTS = {
    ("Saturn", 5): 1.7,
    ("Saturn", 11): 1.4,
    ("Saturn", 2): 1.3,
    ("Saturn", 8): 1.6,
    ("Neptune", 5): 1.6,
    ("Neptune", 11): 1.4,
    ("Neptune", 2): 1.5,
    ("Neptune", 8): 1.7,
    ("Mars", 5): 1.0,
    ("Mars", 11): 0.8,
    ("Mars", 2): 1.1,
    ("Mars", 8): 1.4,
    ("Pluto", 5): 1.0,
    ("Pluto", 11): 0.8,
    ("Pluto", 2): 1.0,
    ("Pluto", 8): 1.4,
    ("Uranus", 5): 0.8,
    ("Uranus", 11): 0.7,
    ("Uranus", 2): 0.8,
    ("Uranus", 8): 1.0,
}

PATTERN_PLANETS = {
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
    "Chiron",
}

PATTERN_EXACTNESS_MAX_ORBS = {
    "conjunction": 8.0,
    "sextile": 4.5,
    "square": 6.0,
    "trine": 6.0,
    "opposition": 8.0,
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

ASC_SUPPORT_ASPECTS = (
    ("conjunction", 0.0, 10.0),
    ("sextile", 60.0, 5.0),
    ("trine", 120.0, 8.0),
)

OBSTRUCTION_ASPECTS = (
    ("conjunction", 0.0, 8.0),
    ("square", 90.0, 6.0),
    ("opposition", 180.0, 8.0),
)


def _normalize_planet_map(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    planets = chart_data.get("planets") or {}
    if isinstance(planets, dict):
        return {str(name): dict(payload) for name, payload in planets.items() if isinstance(payload, dict)}
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(planets, list):
        for row in planets:
            if not isinstance(row, dict):
                continue
            name = str(row.get("planet") or row.get("name") or "").strip()
            if name:
                out[name] = dict(row)
    return out


def _normalize_planet_name(name: Any) -> str:
    return str(name or "").strip().replace("_", " ")


def _resolve_planet_name(name: Any, planets: Dict[str, Dict[str, Any]]) -> str:
    target = _normalize_planet_name(name)
    if not target:
        return ""
    if target in planets:
        return target
    lowered = target.lower()
    for candidate in planets:
        if candidate.lower().replace("_", " ") == lowered:
            return candidate
    return target


def _normalize_house_rulers(chart_data: Dict[str, Any], planets: Dict[str, Dict[str, Any]]) -> Dict[int, str]:
    raw = chart_data.get("house_rulers") or {}
    if not isinstance(raw, dict):
        return {}
    out: Dict[int, str] = {}
    for house, ruler in raw.items():
        try:
            house_num = int(house)
        except Exception:
            continue
        if house_num < 1 or house_num > 12:
            continue
        resolved = _resolve_planet_name(ruler, planets)
        if resolved:
            out[house_num] = resolved
    return out


def _get_chart_aspects(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("planetary_aspects_precise", "planetary_aspects", "aspects"):
        value = chart_data.get(key)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
    return []


def _normalize_aspect_name(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    if "trine" in text:
        return "trine"
    if "sext" in text:
        return "sextile"
    if "oppo" in text:
        return "opposition"
    if "square" in text or text == "sq":
        return "square"
    if "conj" in text:
        return "conjunction"
    return text


def _is_applying_aspect(row: Dict[str, Any]) -> bool:
    applying = row.get("applying")
    if isinstance(applying, bool):
        return applying
    phase = str(row.get("phase") or "").strip().lower()
    return phase == "applying"


def _planet_strength(planets: Dict[str, Dict[str, Any]], planet_angles: Dict[str, str], planet_name: str) -> float:
    planet_name = _resolve_planet_name(planet_name, planets)
    payload = planets.get(planet_name) or {}
    if not payload:
        return 0.0
    try:
        house = int(payload.get("house"))
    except Exception:
        house = None
    house_score = PLANET_STRENGTH_HOUSE_WEIGHTS.get(house or 0, 0.35)

    dignity_score = payload.get("dignity_score")
    dignity_norm = 0.5
    try:
        dignity_norm = _clamp01((float(dignity_score) + 8.0) / 16.0)
    except Exception:
        for key, low, high in (("essential_dignity", -5.0, 5.0), ("accidental_dignity", -8.0, 8.0)):
            try:
                dignity_norm = _clamp01((float(payload.get(key)) - low) / (high - low))
                break
            except Exception:
                continue

    angle_bonus = 0.0
    if planet_angles.get(planet_name) in {"ASC", "MC"}:
        angle_bonus = 0.08
    elif planet_angles.get(planet_name) in {"DSC", "IC"}:
        angle_bonus = 0.04

    solar_adjust = 0.0
    solar_condition = str(payload.get("solar_condition") or "").strip().lower()
    if "cazimi" in solar_condition:
        solar_adjust = 0.1
    elif "combust" in solar_condition:
        solar_adjust = -0.18
    elif "beam" in solar_condition:
        solar_adjust = -0.09

    retrograde_penalty = 0.2 if bool(payload.get("retrograde")) else 0.0
    return _clamp01((house_score * 0.55) + (dignity_norm * 0.35) + angle_bonus + solar_adjust - retrograde_penalty)


def _matching_aspects(aspects: Sequence[Dict[str, Any]], left: str, right: str, planets: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not left or not right:
        return []
    left = _resolve_planet_name(left, planets)
    right = _resolve_planet_name(right, planets)
    matches: List[Dict[str, Any]] = []
    for row in aspects or []:
        p1 = _resolve_planet_name(row.get("planet1") or row.get("from"), planets)
        p2 = _resolve_planet_name(row.get("planet2") or row.get("to"), planets)
        if {p1, p2} == {left, right}:
            matches.append(row)
    return matches


def _house_membership_bonus(planet_houses: Dict[str, int], planet_name: str, houses: set[int], amount: float) -> float:
    try:
        if int(planet_houses.get(planet_name) or 0) in houses:
            return amount
    except Exception:
        return 0.0
    return 0.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _planet_longitude(planets: Dict[str, Dict[str, Any]], planet_name: str) -> Optional[float]:
    resolved = _resolve_planet_name(planet_name, planets)
    if not resolved:
        return None
    payload = planets.get(resolved) or {}
    try:
        return float(payload.get("longitude")) % 360.0
    except Exception:
        return None


def _angular_separation(a: float, b: float) -> float:
    return abs(((float(a) - float(b) + 180.0) % 360.0) - 180.0)


def _finite_longitude(value: Any) -> Optional[float]:
    try:
        longitude = float(value)
    except Exception:
        return None
    if longitude != longitude or longitude in {float("inf"), float("-inf")}:
        return None
    return longitude % 360.0


def _chart_angle_longitudes(chart_data: Dict[str, Any], house_cusps: Sequence[float]) -> Dict[str, float]:
    asc = _finite_longitude(chart_data.get("ascendant_exact"))
    if asc is None:
        asc = _finite_longitude(chart_data.get("ascendant"))
    if asc is None and len(house_cusps) >= 1:
        asc = _finite_longitude(house_cusps[0])

    mc = _finite_longitude(chart_data.get("midheaven_exact"))
    if mc is None:
        mc = _finite_longitude(chart_data.get("midheaven"))
    if mc is None and len(house_cusps) >= 10:
        mc = _finite_longitude(house_cusps[9])

    angles: Dict[str, float] = {}
    if asc is not None:
        angles["ASC"] = asc
        angles["DSC"] = (asc + 180.0) % 360.0
    if mc is not None:
        angles["MC"] = mc
        angles["IC"] = (mc + 180.0) % 360.0
    return angles


def _planet_angle_proximity(
    planets: Dict[str, Dict[str, Any]],
    angle_longitudes: Dict[str, float],
    *,
    max_orb: float = RELOCATION_ANGULAR_ORB_DEG,
) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    planet_angles: Dict[str, str] = {}
    proximity: Dict[str, Dict[str, Any]] = {}
    for planet_name, payload in planets.items():
        longitude = _finite_longitude(payload.get("longitude"))
        if longitude is None or not angle_longitudes:
            continue
        candidates = sorted(
            (
                (_angular_separation(longitude, angle_longitude), angle)
                for angle, angle_longitude in angle_longitudes.items()
            ),
            key=lambda item: (float(item[0]), str(item[1])),
        )
        if not candidates:
            continue
        orb, angle = candidates[0]
        proximity[planet_name] = {
            "nearest_angle": angle,
            "orb_deg": round(float(orb), 4),
            "within_orb": bool(float(orb) <= float(max_orb)),
            "max_orb_deg": float(max_orb),
        }
        if float(orb) <= float(max_orb):
            planet_angles[planet_name] = angle
    return planet_angles, proximity


def _planet_condition_profiles(
    planets: Dict[str, Dict[str, Any]],
    aspects: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    profiles: Dict[str, Dict[str, Any]] = {}
    aspect_balance: Dict[str, float] = {name: 0.0 for name in planets}
    for row in aspects or []:
        left = _resolve_planet_name(row.get("planet1") or row.get("from"), planets)
        right = _resolve_planet_name(row.get("planet2") or row.get("to"), planets)
        if left not in planets or right not in planets:
            continue
        aspect_name = _normalize_aspect_name(row.get("aspect") or row.get("aspect_name"))
        if aspect_name in {"trine", "sextile"}:
            adjustment = 0.04
        elif aspect_name == "conjunction":
            adjustment = 0.0
        elif aspect_name in HARD_ASPECTS:
            adjustment = -0.05
        else:
            continue
        exactness = _aspect_exactness(row, aspect_name) if aspect_name in PATTERN_EXACTNESS_MAX_ORBS else 0.55
        aspect_balance[left] = aspect_balance.get(left, 0.0) + (adjustment * exactness)
        aspect_balance[right] = aspect_balance.get(right, 0.0) + (adjustment * exactness)

    for planet_name, payload in planets.items():
        quality = 0.0
        inputs: List[str] = []
        dignity = payload.get("dignity_score")
        try:
            dignity_value = max(-8.0, min(8.0, float(dignity)))
            quality += (dignity_value / 8.0) * 0.2
            inputs.append("dignity")
        except Exception:
            for key, scale in (("essential_dignity", 5.0), ("accidental_dignity", 8.0)):
                try:
                    dignity_value = max(-scale, min(scale, float(payload.get(key))))
                except Exception:
                    continue
                quality += (dignity_value / scale) * 0.14
                inputs.append(key)
                break

        solar_condition = str(payload.get("solar_condition") or "").strip().lower()
        if "cazimi" in solar_condition:
            quality += 0.12
            inputs.append("cazimi")
        elif "combust" in solar_condition:
            quality -= 0.18
            inputs.append("combust")
        elif "beam" in solar_condition:
            quality -= 0.08
            inputs.append("under_beams")

        if bool(payload.get("retrograde")):
            quality -= 0.08
            inputs.append("retrograde")

        aspect_adjustment = max(-0.15, min(0.15, aspect_balance.get(planet_name, 0.0)))
        if abs(aspect_adjustment) > 1e-9:
            quality += aspect_adjustment
            inputs.append("natal_aspects")

        quality = max(-0.35, min(0.35, quality))
        profiles[planet_name] = {
            "quality": round(quality, 4),
            "support_factor": round(1.0 + quality, 4),
            "caution_factor": round(1.0 - quality, 4),
            "inputs": inputs,
            "available": bool(inputs),
        }
    return profiles


def _condition_factor(
    condition_profiles: Dict[str, Dict[str, Any]],
    planets: Sequence[str],
    *,
    weight: float,
) -> Tuple[float, Dict[str, Any]]:
    available = [
        condition_profiles.get(str(planet)) or {}
        for planet in planets
        if (condition_profiles.get(str(planet)) or {}).get("available")
    ]
    if not available:
        return 1.0, {"available": False, "factor": 1.0, "planets": list(planets)}
    factor_key = "support_factor" if float(weight) >= 0.0 else "caution_factor"
    factor = sum(float(item.get(factor_key) or 1.0) for item in available) / float(len(available))
    return max(0.65, min(1.35, factor)), {
        "available": True,
        "factor": round(max(0.65, min(1.35, factor)), 4),
        "planets": list(planets),
        "basis": factor_key,
    }


def _best_longitude_aspect(
    lon_a: Optional[float],
    lon_b: Optional[float],
    aspect_defs: Sequence[Tuple[str, float, float]],
) -> Optional[Dict[str, Any]]:
    if lon_a is None or lon_b is None:
        return None
    separation = _angular_separation(float(lon_a), float(lon_b))
    best: Optional[Dict[str, Any]] = None
    for aspect_name, exact_angle, max_orb in aspect_defs:
        orb = abs(float(separation) - float(exact_angle))
        if orb > float(max_orb):
            continue
        exactness = _clamp01(1.0 - (orb / float(max_orb)))
        candidate = {
            "aspect": aspect_name,
            "orb": round(orb, 4),
            "exactness": exactness,
        }
        if best is None or float(candidate["exactness"]) > float(best.get("exactness") or 0.0):
            best = candidate
    return best


def _normalize_house_cusps(chart_data: Dict[str, Any]) -> List[float]:
    raw = chart_data.get("houses") or chart_data.get("house_cusps") or []
    if not isinstance(raw, list):
        return []
    out: List[float] = []
    for item in raw[:12]:
        try:
            out.append(float(item) % 360.0)
        except Exception:
            continue
    return out if len(out) >= 12 else []


def _longitude_in_arc(start: float, end: float, point: float) -> bool:
    start = float(start) % 360.0
    end = float(end) % 360.0
    point = float(point) % 360.0
    if start <= end:
        return start <= point < end
    return point >= start or point < end


def _derive_intercepted_signs(cusps: Sequence[float]) -> Dict[int, List[str]]:
    if len(cusps) < 12:
        return {}
    cusp_signs = {int(float(cusp) // 30.0) % 12 for cusp in cusps[:12]}
    intercepted: Dict[int, List[str]] = {}
    for house_idx in range(12):
        start = float(cusps[house_idx]) % 360.0
        end = float(cusps[(house_idx + 1) % 12]) % 360.0
        house_num = house_idx + 1
        hits: List[str] = []
        for sign_idx, sign_name in enumerate(SIGN_NAMES):
            if sign_idx in cusp_signs:
                continue
            sign_start = (sign_idx * 30.0) % 360.0
            sign_end_probe = ((sign_idx + 1) * 30.0 - 0.01) % 360.0
            sign_start_probe = (sign_start + 0.01) % 360.0
            if _longitude_in_arc(start, end, sign_start_probe) and _longitude_in_arc(start, end, sign_end_probe):
                hits.append(sign_name)
        if hits:
            intercepted[house_num] = hits
    return intercepted


def _house_for_longitude(lon: Optional[float], cusps: Sequence[float]) -> Optional[int]:
    if lon is None or len(cusps) < 12:
        return None
    point = float(lon) % 360.0
    for idx in range(12):
        if _longitude_in_arc(float(cusps[idx]), float(cusps[(idx + 1) % 12]), point):
            return idx + 1
    return None


def _south_node_longitude(planets: Dict[str, Dict[str, Any]]) -> Optional[float]:
    direct = _planet_longitude(planets, "South Node")
    if direct is not None:
        return direct
    north = _planet_longitude(planets, "North Node")
    if north is None:
        return None
    return (float(north) + 180.0) % 360.0


def _normalize_simple_score(raw_score: float, *, midpoint: float = 50.0, slope: float = 14.0) -> int:
    return int(round(max(0.0, min(100.0, float(midpoint) + (float(raw_score) * float(slope))))))


def _speculation_profile(planet_houses: Dict[str, int]) -> Tuple[float, float]:
    support_total = 0.0
    drag_total = 0.0
    core_supports: set[str] = set()
    benefic_supports: set[str] = set()

    for planet, house in planet_houses.items():
        support_total += SPECULATION_SUPPORT_WEIGHTS.get((planet, house), 0.0)
        drag_total += SPECULATION_DRAG_WEIGHTS.get((planet, house), 0.0)
        if house in {5, 11} and planet in {"Jupiter", "Venus", "Mercury", "Sun", "Moon"}:
            core_supports.add(planet)
        if house in {2, 5, 8, 11} and planet in {"Jupiter", "Venus"}:
            benefic_supports.add(planet)

    # The recovered gambling rule pack is much more asymmetric than the money/career
    # families: benefic speculative signatures help, but anti-speculation signatures
    # punish harder. Preserve that asymmetry explicitly instead of flattening to a count.
    if benefic_supports == {"Jupiter", "Venus"}:
        support_total += 0.8
    if len(core_supports & {"Jupiter", "Venus", "Mercury"}) >= 2:
        support_total += 0.5
    if "Jupiter" in core_supports and "Venus" in core_supports:
        support_total += 0.4
    if "Saturn" in planet_houses and planet_houses["Saturn"] in {5, 8}:
        drag_total += 0.4
    if "Neptune" in planet_houses and planet_houses["Neptune"] in {2, 5, 8, 11}:
        drag_total += 0.5

    return _clamp01(support_total / 4.6), _clamp01(drag_total / 4.0)


def _aspect_exactness(row: Dict[str, Any], aspect_name: str) -> float:
    try:
        orb_value = abs(float(row.get("orb")))
    except Exception:
        orb_value = None
    try:
        max_orb = float(row.get("allowed_orb") or row.get("max_orb") or PATTERN_EXACTNESS_MAX_ORBS.get(aspect_name) or 6.0)
    except Exception:
        max_orb = float(PATTERN_EXACTNESS_MAX_ORBS.get(aspect_name) or 6.0)
    max_orb = max(0.5, max_orb)
    if orb_value is None:
        if row.get("partile"):
            return 0.95
        if row.get("complete_platic"):
            return 0.8
        return 0.55
    if orb_value > max_orb:
        return 0.0
    return _clamp01(1.0 - (orb_value / max_orb))


def _best_pattern_aspect_rows(
    aspects: Sequence[Dict[str, Any]],
    planets: Dict[str, Dict[str, Any]],
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    rows: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in aspects or []:
        left = _resolve_planet_name(row.get("planet1") or row.get("from"), planets)
        right = _resolve_planet_name(row.get("planet2") or row.get("to"), planets)
        if not left or not right or left == right:
            continue
        if left not in PATTERN_PLANETS or right not in PATTERN_PLANETS:
            continue
        aspect_name = _normalize_aspect_name(row.get("aspect") or row.get("aspect_name"))
        if aspect_name not in PATTERN_EXACTNESS_MAX_ORBS:
            continue
        exactness = _aspect_exactness(row, aspect_name)
        if exactness <= 0.0:
            continue
        key = tuple(sorted((left, right)))
        candidate = {
            "planet1": left,
            "planet2": right,
            "aspect": aspect_name,
            "orb": row.get("orb"),
            "phase": row.get("phase"),
            "applying": row.get("applying"),
            "exactness": exactness,
        }
        current = rows.get(key)
        if current is None or float(candidate["exactness"]) > float(current.get("exactness") or 0.0):
            rows[key] = candidate
    return rows


def _pattern_strength_support(
    participants: Sequence[str],
    exactness: float,
    planets: Dict[str, Dict[str, Any]],
    planet_angles: Dict[str, str],
) -> float:
    if not participants:
        return 0.0
    avg_strength = sum(_planet_strength(planets, planet_angles, name) for name in participants) / max(1, len(participants))
    benefic_ratio = sum(1 for name in participants if name in GAMBLING_SUPPORT_BODIES) / float(len(participants))
    caution_ratio = sum(1 for name in participants if name in GAMBLING_CAUTION_BODIES) / float(len(participants))
    quality = _clamp01(0.42 + (0.22 * avg_strength) + (0.34 * benefic_ratio) - (0.18 * caution_ratio))
    return _clamp01(float(exactness) * quality)


def _pattern_strength_pressure(
    participants: Sequence[str],
    *,
    apex: Optional[str],
    exactness: float,
    planets: Dict[str, Dict[str, Any]],
    planet_angles: Dict[str, str],
) -> float:
    if not participants:
        return 0.0
    avg_strength = sum(_planet_strength(planets, planet_angles, name) for name in participants) / max(1, len(participants))
    caution_ratio = sum(1 for name in participants if name in GAMBLING_CAUTION_BODIES) / float(len(participants))
    benefic_ratio = sum(1 for name in participants if name in GAMBLING_SUPPORT_BODIES) / float(len(participants))
    apex_strength = _planet_strength(planets, planet_angles, apex or "")
    apex_caution = 1.0 if apex in GAMBLING_CAUTION_BODIES else 0.0
    quality = _clamp01(0.34 + (0.24 * avg_strength) + (0.28 * caution_ratio) + (0.18 * apex_caution) + (0.1 * apex_strength) - (0.12 * benefic_ratio))
    return _clamp01(float(exactness) * quality)


def _combine_pattern_strengths(values: Sequence[float]) -> float:
    combined = 0.0
    for value in sorted((_clamp01(item) for item in values if float(item) > 0.0), reverse=True):
        combined = 1.0 - ((1.0 - combined) * (1.0 - value))
    return _clamp01(combined)


def _compute_chart_pattern_geometry(
    planets: Dict[str, Dict[str, Any]],
    planet_angles: Dict[str, str],
    aspects: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    aspect_rows = _best_pattern_aspect_rows(aspects, planets)
    bodies = sorted(
        {
            name
            for row in aspect_rows.values()
            for name in (str(row.get("planet1") or ""), str(row.get("planet2") or ""))
            if name
        }
    )
    grand_trines: List[Dict[str, Any]] = []
    kites: List[Dict[str, Any]] = []
    t_squares: List[Dict[str, Any]] = []

    def _row(left: str, right: str) -> Optional[Dict[str, Any]]:
        return aspect_rows.get(tuple(sorted((left, right))))

    for trio in combinations(bodies, 3):
        rows = [_row(trio[0], trio[1]), _row(trio[0], trio[2]), _row(trio[1], trio[2])]
        if all(isinstance(row, dict) and str(row.get("aspect") or "") == "trine" for row in rows):
            exactness = sum(float(row.get("exactness") or 0.0) for row in rows if isinstance(row, dict)) / 3.0
            grand_trines.append(
                {
                    "planets": list(trio),
                    "exactness": round(exactness, 4),
                    "score": round(_pattern_strength_support(trio, exactness, planets, planet_angles), 4),
                }
            )

        for left, right in combinations(trio, 2):
            opposition = _row(left, right)
            if not opposition or str(opposition.get("aspect") or "") != "opposition":
                continue
            apex = next(item for item in trio if item not in {left, right})
            leg_one = _row(apex, left)
            leg_two = _row(apex, right)
            if not leg_one or not leg_two:
                continue
            if str(leg_one.get("aspect") or "") != "square" or str(leg_two.get("aspect") or "") != "square":
                continue
            exactness = (
                float(opposition.get("exactness") or 0.0)
                + float(leg_one.get("exactness") or 0.0)
                + float(leg_two.get("exactness") or 0.0)
            ) / 3.0
            t_squares.append(
                {
                    "apex": apex,
                    "opposition": [left, right],
                    "planets": list(trio),
                    "exactness": round(exactness, 4),
                    "score": round(_pattern_strength_pressure(trio, apex=apex, exactness=exactness, planets=planets, planet_angles=planet_angles), 4),
                }
            )
            break

    seen_kites: set[Tuple[str, ...]] = set()
    for trine in grand_trines:
        trio = tuple(str(item) for item in trine.get("planets") or [])
        if len(trio) != 3:
            continue
        base_exactness = [
            float((_row(trio[0], trio[1]) or {}).get("exactness") or 0.0),
            float((_row(trio[0], trio[2]) or {}).get("exactness") or 0.0),
            float((_row(trio[1], trio[2]) or {}).get("exactness") or 0.0),
        ]
        for focus in bodies:
            if focus in trio:
                continue
            for opposed in trio:
                opposition = _row(focus, opposed)
                if not opposition or str(opposition.get("aspect") or "") != "opposition":
                    continue
                sextile_targets = [item for item in trio if item != opposed]
                sextile_rows = [_row(focus, sextile_targets[0]), _row(focus, sextile_targets[1])]
                if not all(isinstance(row, dict) and str(row.get("aspect") or "") == "sextile" for row in sextile_rows):
                    continue
                key = tuple(sorted((*trio, focus)))
                if key in seen_kites:
                    continue
                seen_kites.add(key)
                exactness = (
                    sum(base_exactness)
                    + float(opposition.get("exactness") or 0.0)
                    + sum(float(row.get("exactness") or 0.0) for row in sextile_rows if isinstance(row, dict))
                ) / 6.0
                kites.append(
                    {
                        "focus": focus,
                        "opposed_vertex": opposed,
                        "planets": list(key),
                        "exactness": round(exactness, 4),
                        "score": round(_pattern_strength_support(key, exactness, planets, planet_angles), 4),
                    }
                )

    grand_trines.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    kites.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    t_squares.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)

    grand_trine_support = _combine_pattern_strengths(float(item.get("score") or 0.0) for item in grand_trines)
    kite_support = _combine_pattern_strengths(float(item.get("score") or 0.0) for item in kites)
    t_square_pressure = _combine_pattern_strengths(float(item.get("score") or 0.0) for item in t_squares)

    return {
        "items": {
            "grand_trines": grand_trines,
            "kites": kites,
            "t_squares": t_squares,
        },
        "metrics": {
            "grand_trine_support": grand_trine_support,
            "kite_support": kite_support,
            "t_square_pressure": t_square_pressure,
            "pattern_support": _combine_pattern_strengths([grand_trine_support, kite_support]),
            "pattern_pressure": t_square_pressure,
        },
    }


def _birth_time_confidence(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    explicit = chart_data.get("birth_time_confidence")
    try:
        confidence = _clamp01(float(explicit))
        return {
            "value": round(confidence, 4),
            "source": "explicit",
            "unknown_time": bool(confidence <= 0.25),
        }
    except Exception:
        pass

    unknown_time = bool(chart_data.get("unknown_time") or chart_data.get("birth_time_unknown"))
    if unknown_time:
        return {"value": 0.2, "source": "unknown_time", "unknown_time": True}

    uncertainty_minutes = chart_data.get("birth_time_uncertainty_minutes")
    try:
        minutes = max(0.0, float(uncertainty_minutes))
        confidence = max(0.2, 1.0 - min(1.0, minutes / 120.0) * 0.8)
        return {
            "value": round(confidence, 4),
            "source": "uncertainty_minutes",
            "uncertainty_minutes": round(minutes, 2),
            "unknown_time": bool(minutes >= 90.0),
        }
    except Exception:
        pass

    accuracy = str(chart_data.get("birth_time_accuracy") or chart_data.get("time_accuracy") or "").strip().lower()
    if accuracy:
        mapped = {
            "exact": 1.0,
            "recorded": 0.95,
            "verified": 0.95,
            "approximate": 0.65,
            "estimated": 0.55,
            "unknown": 0.2,
        }
        for token, confidence in mapped.items():
            if token in accuracy:
                return {
                    "value": confidence,
                    "source": "accuracy_label",
                    "label": accuracy,
                    "unknown_time": bool(confidence <= 0.25),
                }
    return {"value": 1.0, "source": "not_provided", "unknown_time": False}


def extract_relocation_features(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    normalized_chart = chart_data if isinstance(chart_data, dict) else {}
    planets = _normalize_planet_map(normalized_chart)
    house_rulers = _normalize_house_rulers(normalized_chart, planets)
    house_cusps = _normalize_house_cusps(normalized_chart)
    aspects = _get_chart_aspects(normalized_chart)
    planet_houses: Dict[str, int] = {}
    angular_house_occupancy: Dict[str, str] = {}
    house_occupancy: Dict[int, List[str]] = {house: [] for house in range(1, 13)}

    for name, payload in planets.items():
        try:
            house = int(payload.get("house"))
        except Exception:
            continue
        if house < 1 or house > 12:
            continue
        planet_houses[name] = house
        house_occupancy.setdefault(house, []).append(name)
        angle = ANGULAR_HOUSE_TO_ANGLE.get(house)
        if angle:
            angular_house_occupancy[name] = angle
    angle_longitudes = _chart_angle_longitudes(normalized_chart, house_cusps)
    planet_angles, planet_angle_proximity = _planet_angle_proximity(planets, angle_longitudes)
    planet_conditions = _planet_condition_profiles(planets, aspects)
    time_confidence = _birth_time_confidence(normalized_chart)
    intercepted_signs = _derive_intercepted_signs(house_cusps)
    asc_intercepted_signs = list(dict.fromkeys((intercepted_signs.get(1) or []) + (intercepted_signs.get(7) or [])))
    asc_interception = _clamp01(len(asc_intercepted_signs) / 2.0)
    pattern_geometry = _compute_chart_pattern_geometry(planets, planet_angles, aspects)

    def metric_ratio(matches: int, scale: int) -> float:
        if scale <= 0:
            return 0.0
        return max(0.0, min(1.0, matches / float(scale)))

    def placement_hits(allowed_planets: set[str], allowed_houses: set[int]) -> List[str]:
        return [
            f"relocation:{planet}:house:{house}"
            for planet, house in planet_houses.items()
            if planet in allowed_planets and house in allowed_houses
        ]

    metric_evidence: Dict[str, List[str]] = {
        "visibility": placement_hits({"Sun", "Jupiter", "Mercury", "Venus"}, {1, 10}),
        "partnership": placement_hits({"Venus", "Moon", "Jupiter"}, {5, 7}),
        "domesticity": placement_hits({"Moon", "Venus"}, {4, 5}),
        "mobility": placement_hits({"Mercury", "Jupiter", "Uranus"}, {3, 9}),
        "uncertainty": placement_hits({"Neptune", "Uranus"}, {1, 7, 9, 10, 12}),
        "stability_support": placement_hits({"Saturn", "Jupiter"}, {1, 4, 10}),
        "benefic_balance": placement_hits(BENEFICS, {1, 4, 5, 7, 10, 11}),
        "malefic_pressure": placement_hits(MALEFICS, {1, 6, 7, 8, 10, 12}),
        "community": placement_hits({"Venus", "Jupiter", "Mercury", "Moon", "Sun"}, {3, 11}),
        "beliefs": placement_hits({"Jupiter", "Neptune", "Sun", "Mercury", "Moon"}, {9, 12}),
        "chemistry": placement_hits({"Venus", "Mars", "Pluto", "Moon"}, {1, 5, 7, 8}),
        "career_status": placement_hits({"Sun", "Jupiter", "Saturn", "Mercury"}, {1, 10, 11}),
        "home_base": placement_hits({"Moon", "Venus", "Jupiter"}, {2, 4}),
        "personal_growth": placement_hits({"Sun", "Jupiter", "Uranus", "Pluto", "North Node"}, {1, 8, 9, 10, 11}),
        "communication": placement_hits({"Mercury", "Venus", "Moon", "Jupiter", "Sun", "Uranus"}, {3, 7, 9, 11}),
        "conflict_pressure": placement_hits({"Mars", "Saturn", "Pluto", "Uranus"}, {1, 7, 8, 12}),
        "body_presence": placement_hits({"Sun", "Venus", "Moon", "Mars", "Jupiter"}, {1, 2, 5, 10}),
        "travel_joy": placement_hits({"Venus", "Jupiter", "Sun", "Mercury", "Moon"}, {3, 5, 9, 11}),
        "restoration": placement_hits({"Moon", "Venus", "Jupiter", "Neptune", "Sun"}, {4, 9, 12}),
        "health_risk": placement_hits({"Mars", "Saturn", "Neptune", "Pluto", "Uranus"}, {1, 6, 8, 12}),
    }
    visibility_hits = len(metric_evidence["visibility"])
    partnership_hits = len(metric_evidence["partnership"])
    domesticity_hits = len(metric_evidence["domesticity"])
    mobility_hits = len(metric_evidence["mobility"])
    uncertainty_hits = len(metric_evidence["uncertainty"])
    stability_hits = len(metric_evidence["stability_support"])
    benefic_hits = len(metric_evidence["benefic_balance"])
    malefic_hits = len(metric_evidence["malefic_pressure"])
    community_hits = len(metric_evidence["community"])
    belief_hits = len(metric_evidence["beliefs"])
    chemistry_hits = len(metric_evidence["chemistry"])
    career_hits = len(metric_evidence["career_status"])
    home_hits = len(metric_evidence["home_base"])
    personal_growth_hits = len(metric_evidence["personal_growth"])
    communication_hits = len(metric_evidence["communication"])
    conflict_hits = len(metric_evidence["conflict_pressure"])
    body_presence_hits = len(metric_evidence["body_presence"])
    travel_joy_hits = len(metric_evidence["travel_joy"])
    restoration_hits = len(metric_evidence["restoration"])
    metric_evidence["stability"] = list(
        dict.fromkeys(metric_evidence["stability_support"] + metric_evidence["uncertainty"])
    )
    speculation_value, speculation_drag_value = _speculation_profile(planet_houses)
    metric_evidence["speculation"] = [
        f"relocation:{planet}:house:{house}"
        for planet, house in planet_houses.items()
        if SPECULATION_SUPPORT_WEIGHTS.get((planet, house), 0.0) > 0.0
    ]
    metric_evidence["speculation_drag"] = [
        f"relocation:{planet}:house:{house}"
        for planet, house in planet_houses.items()
        if SPECULATION_DRAG_WEIGHTS.get((planet, house), 0.0) > 0.0
    ]
    health_risk_hits = len(metric_evidence["health_risk"])
    gambling_signature = 0.0
    gambling_activation = 0.0
    for planet, house in planet_houses.items():
        if planet == "Jupiter" and house == 5:
            gambling_signature += 1.3
            gambling_activation += 0.4
        elif planet == "Jupiter" and house in {2, 8}:
            gambling_signature += 0.25 if house == 2 else 0.35
            gambling_activation += 0.05
        elif planet == "Venus" and house == 5:
            gambling_signature += 1.05
            gambling_activation += 0.35
        elif planet == "Venus" and house in {2, 8}:
            gambling_signature += 0.45 if house == 2 else 0.6
            gambling_activation += 0.05
        elif planet == "Mercury" and house == 5:
            gambling_signature += 0.75
            gambling_activation += 0.22
        elif planet == "Mercury" and house in {2, 8}:
            gambling_signature += 0.25 if house == 2 else 0.35
        elif planet == "Sun" and house in {5, 8}:
            gambling_signature += 0.5 if house == 5 else 0.35
            gambling_activation += 0.12
        elif planet == "Moon" and house in {5, 8}:
            gambling_signature += 0.85 if house == 5 else 0.25
            gambling_activation += 0.28 if house == 5 else 0.12
        elif planet in {"Jupiter", "Venus", "Mercury", "Moon"} and house == 11:
            gambling_signature += 0.12
    asc_ruler = house_rulers.get(1, "")
    gambling_ruler = house_rulers.get(5, "")
    ascendant_lon = None
    try:
        ascendant_lon = float((chart_data if isinstance(chart_data, dict) else {}).get("ascendant")) % 360.0
    except Exception:
        ascendant_lon = float(house_cusps[0]) % 360.0 if len(house_cusps) >= 1 else None
    asc_ruler_strength = _planet_strength(planets, planet_angles, asc_ruler)
    gambling_ruler_strength = _planet_strength(planets, planet_angles, gambling_ruler)
    asc_ruler_asc_hit = _best_longitude_aspect(_planet_longitude(planets, asc_ruler), ascendant_lon, ASC_SUPPORT_ASPECTS)
    gambling_ruler_asc_hit = _best_longitude_aspect(_planet_longitude(planets, gambling_ruler), ascendant_lon, ASC_SUPPORT_ASPECTS)
    moon_asc_hit = _best_longitude_aspect(_planet_longitude(planets, "Moon"), ascendant_lon, ASC_SUPPORT_ASPECTS)
    asc_ruler_asc_support = float((asc_ruler_asc_hit or {}).get("exactness") or 0.0)
    gambling_ruler_asc_support = float((gambling_ruler_asc_hit or {}).get("exactness") or 0.0)
    moon_asc_support = float((moon_asc_hit or {}).get("exactness") or 0.0)

    asc_gambling_harmony = 0.0
    asc_gambling_tension = 0.0
    if asc_ruler and gambling_ruler:
        if asc_ruler == gambling_ruler:
            asc_gambling_harmony = 0.85
        for row in _matching_aspects(aspects, asc_ruler, gambling_ruler, planets):
            aspect_name = _normalize_aspect_name(row.get("aspect") or row.get("aspect_name"))
            applying_factor = 1.0 if _is_applying_aspect(row) else 0.75
            if aspect_name == "trine":
                asc_gambling_harmony = max(asc_gambling_harmony, 1.0 * applying_factor)
            elif aspect_name == "sextile":
                asc_gambling_harmony = max(asc_gambling_harmony, 0.82 * applying_factor)
            elif aspect_name == "conjunction":
                asc_gambling_harmony = max(asc_gambling_harmony, 0.76 * applying_factor)
            elif aspect_name == "square":
                asc_gambling_tension = max(asc_gambling_tension, 1.0 * applying_factor)
            elif aspect_name == "opposition":
                asc_gambling_tension = max(asc_gambling_tension, 0.88 * applying_factor)

    asc_gambling_harmony = _clamp01(
        asc_gambling_harmony
        + _house_membership_bonus(planet_houses, asc_ruler, {5, 11}, 0.12)
        + _house_membership_bonus(planet_houses, gambling_ruler, {1, 10}, 0.12)
    )
    asc_gambling_tension = _clamp01(
        asc_gambling_tension
        + _house_membership_bonus(planet_houses, asc_ruler, {8, 12}, 0.12)
        + _house_membership_bonus(planet_houses, gambling_ruler, {8, 12}, 0.18)
    )

    moon_payload = planets.get("Moon") or {}
    try:
        moon_house = int(moon_payload.get("house"))
    except Exception:
        moon_house = None
    moon_void = bool(((chart_data if isinstance(chart_data, dict) else {}).get("considerations") or {}).get("moon_void"))
    moon_next_aspect = (chart_data if isinstance(chart_data, dict) else {}).get("moon_next_aspect")
    moon_gambling_support = 0.0
    moon_liability = 0.0
    if moon_house in {1, 2, 5, 11}:
        moon_gambling_support += {1: 0.24, 2: 0.18, 5: 0.3, 11: 0.22}.get(moon_house, 0.0)
    if moon_house in {8, 12}:
        moon_liability += 0.22
    if moon_void:
        moon_liability += 0.7
    if isinstance(moon_next_aspect, dict):
        next_planet = _resolve_planet_name(moon_next_aspect.get("planet"), planets)
        next_aspect_name = _normalize_aspect_name(moon_next_aspect.get("aspect"))
        next_applying_factor = 1.0 if _is_applying_aspect(moon_next_aspect) else 0.75
        if next_planet in {asc_ruler, gambling_ruler, "Jupiter", "Venus"} and next_aspect_name in SUPPORTIVE_ASPECTS:
            moon_gambling_support += (0.42 if next_planet in {asc_ruler, gambling_ruler} else 0.28) * next_applying_factor
        if next_planet in {asc_ruler, gambling_ruler} and next_aspect_name in HARD_ASPECTS:
            moon_liability += 0.38 * next_applying_factor
        if next_planet in {"Saturn", "Mars", "Neptune", "Pluto"} and next_aspect_name in HARD_ASPECTS:
            moon_liability += 0.44 * next_applying_factor

    for target in filter(None, {asc_ruler, gambling_ruler}):
        for row in _matching_aspects(aspects, "Moon", target, planets):
            aspect_name = _normalize_aspect_name(row.get("aspect") or row.get("aspect_name"))
            applying_factor = 1.0 if _is_applying_aspect(row) else 0.75
            if aspect_name in SUPPORTIVE_ASPECTS:
                moon_gambling_support += 0.18 * applying_factor
            elif aspect_name in HARD_ASPECTS:
                moon_liability += 0.22 * applying_factor

    retrograde_liability = 0.0
    for planet_name, penalty in (
        (asc_ruler, 0.36),
        (gambling_ruler, 0.44),
        (house_rulers.get(2, ""), 0.14),
        (house_rulers.get(8, ""), 0.1),
        (house_rulers.get(11, ""), 0.16),
    ):
        resolved = _resolve_planet_name(planet_name, planets)
        if resolved and bool((planets.get(resolved) or {}).get("retrograde")):
            retrograde_liability += penalty
        solar_condition = str((planets.get(resolved) or {}).get("solar_condition") or "").strip().lower()
        if resolved and "combust" in solar_condition:
            retrograde_liability += penalty * 0.5

    money_support = 0.0
    secondary_rulers = ((2, 0.34), (8, 0.16), (11, 0.38))
    for house, weight in secondary_rulers:
        money_support += _planet_strength(planets, planet_angles, house_rulers.get(house, "")) * weight
    money_support = _clamp01(
        money_support
        + (0.1 if "Jupiter" in house_occupancy.get(11, []) else 0.0)
        + (0.08 if "Venus" in house_occupancy.get(2, []) else 0.0)
    )
    south_node_lon = _south_node_longitude(planets)
    south_node_house = _house_for_longitude(south_node_lon, house_cusps)
    south_node_obstruction = 0.0
    if south_node_house in {1, 5, 8, 12}:
        south_node_obstruction += {1: 0.55, 5: 0.36, 8: 0.42, 12: 0.28}.get(int(south_node_house), 0.0)
    south_node_asc_hit = _best_longitude_aspect(south_node_lon, ascendant_lon, OBSTRUCTION_ASPECTS)
    if south_node_asc_hit:
        aspect_name = str(south_node_asc_hit.get("aspect") or "")
        aspect_weight = {"conjunction": 0.5, "square": 0.34, "opposition": 0.28}.get(aspect_name, 0.0)
        south_node_obstruction += aspect_weight * float(south_node_asc_hit.get("exactness") or 0.0)
    for target, weight in ((asc_ruler, 0.18), (gambling_ruler, 0.22), ("Moon", 0.16)):
        target_hit = _best_longitude_aspect(south_node_lon, _planet_longitude(planets, target), OBSTRUCTION_ASPECTS)
        if target_hit:
            south_node_obstruction += weight * float(target_hit.get("exactness") or 0.0)
    south_node_obstruction = _clamp01(south_node_obstruction)
    gambling_activation = _clamp01(
        gambling_activation
        + (0.4 * _clamp01(gambling_signature / 3.0))
        + (0.32 if gambling_ruler_strength >= 0.5 else 0.0)
        + (0.18 if asc_gambling_harmony >= 0.45 else 0.0)
        + (0.1 if moon_house == 5 else 0.0)
    )

    metrics = {
        "visibility": metric_ratio(visibility_hits, 3),
        "partnership": metric_ratio(partnership_hits, 3),
        "domesticity": metric_ratio(domesticity_hits, 2),
        "mobility": metric_ratio(mobility_hits, 3),
        "uncertainty": metric_ratio(uncertainty_hits, 2),
        "stability": metric_ratio(max(0, stability_hits - uncertainty_hits), 2),
        "benefic_balance": metric_ratio(benefic_hits, 4),
        "malefic_pressure": metric_ratio(malefic_hits, 4),
        "community": metric_ratio(community_hits, 4),
        "beliefs": metric_ratio(belief_hits, 3),
        "chemistry": metric_ratio(chemistry_hits, 3),
        "career_status": metric_ratio(career_hits, 3),
        "home_base": metric_ratio(home_hits, 3),
        "personal_growth": metric_ratio(personal_growth_hits, 4),
        "communication": metric_ratio(communication_hits, 4),
        "conflict_pressure": metric_ratio(conflict_hits, 4),
        "body_presence": metric_ratio(body_presence_hits, 4),
        "travel_joy": metric_ratio(travel_joy_hits, 4),
        "restoration": metric_ratio(restoration_hits, 3),
        "speculation": speculation_value,
        "speculation_drag": speculation_drag_value,
        "health_risk": metric_ratio(health_risk_hits, 4),
        "gambling_signature": _clamp01(gambling_signature / 3.0),
        "gambling_activation": gambling_activation,
        "asc_ruler_strength": asc_ruler_strength,
        "gambling_ruler_strength": gambling_ruler_strength,
        "asc_ruler_asc_support": asc_ruler_asc_support,
        "gambling_ruler_asc_support": gambling_ruler_asc_support,
        "moon_asc_support": moon_asc_support,
        "asc_gambling_harmony": asc_gambling_harmony,
        "asc_gambling_tension": asc_gambling_tension,
        "moon_gambling_support": _clamp01(moon_gambling_support),
        "moon_liability": _clamp01(moon_liability),
        "retrograde_liability": _clamp01(retrograde_liability),
        "money_support": money_support,
        "south_node_obstruction": south_node_obstruction,
        "asc_interception": asc_interception,
        "grand_trine_support": float((pattern_geometry.get("metrics") or {}).get("grand_trine_support") or 0.0),
        "kite_support": float((pattern_geometry.get("metrics") or {}).get("kite_support") or 0.0),
        "t_square_pressure": float((pattern_geometry.get("metrics") or {}).get("t_square_pressure") or 0.0),
        "pattern_support": float((pattern_geometry.get("metrics") or {}).get("pattern_support") or 0.0),
        "pattern_pressure": float((pattern_geometry.get("metrics") or {}).get("pattern_pressure") or 0.0),
    }

    return {
        "planet_houses": planet_houses,
        "planet_angles": planet_angles,
        "planet_angle_proximity": planet_angle_proximity,
        "angular_house_occupancy": angular_house_occupancy,
        "angle_longitudes": angle_longitudes,
        "house_occupancy": house_occupancy,
        "house_rulers": house_rulers,
        "planet_conditions": planet_conditions,
        "metric_evidence": metric_evidence,
        "confidence": {
            "birth_time": time_confidence,
        },
        "details": {
            "asc_ruler": asc_ruler,
            "gambling_ruler": gambling_ruler,
            "moon_void": moon_void,
            "ascendant": ascendant_lon,
            "asc_ruler_asc_hit": asc_ruler_asc_hit,
            "gambling_ruler_asc_hit": gambling_ruler_asc_hit,
            "moon_asc_hit": moon_asc_hit,
            "south_node_longitude": south_node_lon,
            "south_node_house": south_node_house,
            "south_node_asc_hit": south_node_asc_hit,
            "intercepted_signs": intercepted_signs,
            "asc_intercepted_signs": asc_intercepted_signs,
            "patterns": pattern_geometry.get("items") or {},
            "angular_house_occupancy": angular_house_occupancy,
            "planet_angle_proximity": planet_angle_proximity,
        },
        "metrics": metrics,
    }


def _score_distance(distance_km: float, max_km: float, falloff: str = "linear") -> float:
    distance_km = max(0.0, float(distance_km))
    max_km = max(1.0, float(max_km))
    if distance_km > max_km:
        return 0.0
    if falloff == "flat":
        return 1.0
    if falloff == "inverse":
        return 1.0 / (1.0 + (distance_km / max_km))
    return max(0.0, 1.0 - (distance_km / max_km))


def _distance_profile_multipliers(model: Dict[str, Any]) -> Dict[str, float]:
    policy = (model or {}).get("distance_policy") or {}
    configured = policy.get("profile_multipliers") or {}
    requested_profiles = [
        str(item).strip().lower()
        for item in (policy.get("sensitivity_profiles") or DEFAULT_DISTANCE_SENSITIVITY_PROFILES)
        if str(item).strip()
    ]
    profiles: Dict[str, float] = {}
    for profile in requested_profiles:
        fallback = DEFAULT_DISTANCE_SENSITIVITY_PROFILES.get(profile)
        if fallback is None:
            continue
        try:
            multiplier = float(configured.get(profile, fallback))
        except (TypeError, ValueError):
            multiplier = float(fallback)
        profiles[profile] = max(0.1, multiplier)
    for profile, fallback in DEFAULT_DISTANCE_SENSITIVITY_PROFILES.items():
        profiles.setdefault(profile, float(fallback))
    return profiles


def _heuristic_distance_weight(distance_km: Any, max_km: float = 500.0) -> float:
    try:
        value = max(0.0, float(distance_km))
    except Exception:
        return 0.0
    if value >= max_km:
        return 0.0
    return max(0.0, 1.0 - (value / max_km))


def _is_exact_crossing(row: Dict[str, Any]) -> bool:
    return str(row.get("kind") or "crossing").strip().lower() == "crossing"


def _heuristic_line_contributions(
    rows: Sequence[Dict[str, Any]],
    *,
    context: str,
    bodies: set[str],
    sign: float,
    multiplier: float = 1.0,
    rationale: str,
) -> List[Dict[str, Any]]:
    contributions: List[Dict[str, Any]] = []
    for row in rows or []:
        body = str(row.get("body") or row.get("planet") or "").strip()
        if body not in bodies:
            continue
        score = _heuristic_distance_weight(row.get("distance_km")) * float(multiplier) * float(sign)
        if abs(score) < 1e-9:
            continue
        contributions.append(
            {
                "kind": "line",
                "context": context,
                "score": round(score, 4),
                "matched": row,
                "label": row.get("label"),
                "distance_km": row.get("distance_km"),
                "rationale": rationale,
            }
        )
    return contributions


def _heuristic_crossing_contributions(
    crossings: Sequence[Dict[str, Any]],
    *,
    context: str,
    bodies: set[str],
    sign: float,
    multiplier: float = 1.0,
    min_body_matches: int = 1,
    rationale: str,
) -> List[Dict[str, Any]]:
    contributions: List[Dict[str, Any]] = []
    for row in crossings or []:
        if not _is_exact_crossing(row):
            continue
        planets = {str(item).strip() for item in (row.get("planets") or []) if str(item).strip()}
        body_matches = planets & bodies
        if not planets or len(body_matches) < int(min_body_matches):
            continue
        planet_factor = min(1.0, len(body_matches) / float(max(1, len(planets))))
        score = _heuristic_distance_weight(row.get("distance_km")) * planet_factor * float(multiplier) * float(sign)
        if abs(score) < 1e-9:
            continue
        contributions.append(
            {
                "kind": "crossing",
                "context": context,
                "score": round(score, 4),
                "matched": row,
                "label": row.get("label"),
                "distance_km": row.get("distance_km"),
                "rationale": rationale,
            }
        )
    return contributions


def _specific_crossing_contributions(
    crossings: Sequence[Dict[str, Any]],
    *,
    context: str,
    pairs: Sequence[Tuple[str, str]],
    multiplier: float = 1.0,
    rationale: str,
) -> List[Dict[str, Any]]:
    contributions: List[Dict[str, Any]] = []
    normalized_pairs = {frozenset((str(left), str(right))) for left, right in pairs}
    for row in crossings or []:
        if not _is_exact_crossing(row):
            continue
        planets = [str(item).strip() for item in (row.get("planets") or []) if str(item).strip()]
        if frozenset(planets) not in normalized_pairs:
            continue
        score = _heuristic_distance_weight(row.get("distance_km")) * float(multiplier)
        if abs(score) < 1e-9:
            continue
        contributions.append(
            {
                "kind": "crossing",
                "context": context,
                "score": round(score, 4),
                "matched": row,
                "label": row.get("label"),
                "distance_km": row.get("distance_km"),
                "rationale": rationale,
            }
        )
    return contributions


def _relocation_metric_value(relocation: Dict[str, Any], metric_name: str) -> float:
    metrics = relocation.get("metrics") or {}
    try:
        return float(metrics.get(metric_name) or 0.0)
    except Exception:
        return 0.0


def _evaluate_balance_heuristic(
    *,
    result_id: str,
    result_label: str,
    result_summary: str,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
    benefic_sign: float,
    malefic_sign: float,
    benefic_line_rationale: str,
    benefic_crossing_rationale: str,
    malefic_line_rationale: str,
    malefic_crossing_rationale: str,
    transit_benefic_line_rationale: str,
    transit_benefic_crossing_rationale: str,
    transit_malefic_line_rationale: str,
    transit_malefic_crossing_rationale: str,
) -> Dict[str, Any]:
    contributions: List[Dict[str, Any]] = []
    contributions.extend(
        _heuristic_line_contributions(
            natal_rows,
            context="natal",
            bodies=HEURISTIC_BENEFICS,
            sign=benefic_sign,
            rationale=benefic_line_rationale,
        )
    )
    contributions.extend(
        _heuristic_crossing_contributions(
            natal_crossings,
            context="natal",
            bodies=HEURISTIC_BENEFICS,
            sign=benefic_sign,
            rationale=benefic_crossing_rationale,
        )
    )
    contributions.extend(
        _heuristic_line_contributions(
            natal_rows,
            context="natal",
            bodies=HEURISTIC_MALEFICS,
            sign=malefic_sign,
            rationale=malefic_line_rationale,
        )
    )
    contributions.extend(
        _heuristic_crossing_contributions(
            natal_crossings,
            context="natal",
            bodies=HEURISTIC_MALEFICS,
            sign=malefic_sign,
            rationale=malefic_crossing_rationale,
        )
    )

    if transit_rows:
        contributions.extend(
            _heuristic_line_contributions(
                transit_rows,
                context="transit",
                bodies=HEURISTIC_BENEFICS,
                sign=benefic_sign,
                multiplier=transit_multiplier,
                rationale=transit_benefic_line_rationale,
            )
        )
        contributions.extend(
            _heuristic_line_contributions(
                transit_rows,
                context="transit",
                bodies=HEURISTIC_MALEFICS,
                sign=malefic_sign,
                multiplier=transit_multiplier,
                rationale=transit_malefic_line_rationale,
            )
        )
    if transit_crossings:
        contributions.extend(
            _heuristic_crossing_contributions(
                transit_crossings,
                context="transit",
                bodies=HEURISTIC_BENEFICS,
                sign=benefic_sign,
                multiplier=transit_multiplier,
                rationale=transit_benefic_crossing_rationale,
            )
        )
        contributions.extend(
            _heuristic_crossing_contributions(
                transit_crossings,
                context="transit",
                bodies=HEURISTIC_MALEFICS,
                sign=malefic_sign,
                multiplier=transit_multiplier,
                rationale=transit_malefic_crossing_rationale,
            )
        )

    raw_total = round(sum(float(item.get("score") or 0.0) for item in contributions), 4)
    score = _normalize_simple_score(raw_total, midpoint=40.0, slope=4.2)
    positives = sorted(
        [item for item in contributions if float(item.get("score") or 0.0) > 0.0],
        key=lambda item: float(item.get("score") or 0.0),
        reverse=True,
    )
    cautions = sorted(
        [item for item in contributions if float(item.get("score") or 0.0) < 0.0],
        key=lambda item: float(item.get("score") or 0.0),
    )
    breakdown = {
        "natal": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "natal"), 4),
        "transit": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "transit"), 4),
        "relocation": 0.0,
        "constraints": 0.0,
    }
    return {
        "goal": {
            "id": result_id,
            "label": result_label,
            "summary": result_summary,
        },
        "raw_score": raw_total,
        "score": score,
        "breakdown": breakdown,
        "top_supports": positives[:3],
        "top_cautions": cautions[:3],
        "contributions": contributions,
    }


def evaluate_benefic_minus_malefic_heuristic(
    *,
    result_id: str,
    result_label: str,
    result_summary: str,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    return _evaluate_balance_heuristic(
        result_id=result_id,
        result_label=result_label,
        result_summary=result_summary,
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        transit_rows=transit_rows,
        transit_crossings=transit_crossings,
        transit_multiplier=transit_multiplier,
        benefic_sign=1.0,
        malefic_sign=-1.0,
        benefic_line_rationale="Nearby benefic angular pressure improves the overall field in the simple balance heuristic.",
        benefic_crossing_rationale="Nearby benefic crossings improve the overall field in the simple balance heuristic.",
        malefic_line_rationale="Nearby malefic angular pressure lowers the balance score in the simple heuristic.",
        malefic_crossing_rationale="Nearby malefic crossings lower the balance score in the simple heuristic.",
        transit_benefic_line_rationale="Transit benefic angular pressure improves the overall field at reduced overlay weight.",
        transit_benefic_crossing_rationale="Transit benefic crossings improve the overall field at reduced overlay weight.",
        transit_malefic_line_rationale="Transit malefic angular pressure lowers the balance score at reduced overlay weight.",
        transit_malefic_crossing_rationale="Transit malefic crossings lower the balance score at reduced overlay weight.",
    )


def evaluate_malefic_minus_benefic_heuristic(
    *,
    result_id: str,
    result_label: str,
    result_summary: str,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    return _evaluate_balance_heuristic(
        result_id=result_id,
        result_label=result_label,
        result_summary=result_summary,
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        transit_rows=transit_rows,
        transit_crossings=transit_crossings,
        transit_multiplier=transit_multiplier,
        benefic_sign=-1.0,
        malefic_sign=1.0,
        benefic_line_rationale="Nearby benefic angular pressure lowers the risk score by adding protection and livability.",
        benefic_crossing_rationale="Nearby benefic crossings lower the risk score by softening the overall field.",
        malefic_line_rationale="Nearby malefic angular pressure raises the risk score in this generic warning heuristic.",
        malefic_crossing_rationale="Nearby malefic crossings raise the risk score in this generic warning heuristic.",
        transit_benefic_line_rationale="Transit benefic angular pressure lowers the risk score at reduced overlay weight.",
        transit_benefic_crossing_rationale="Transit benefic crossings lower the risk score at reduced overlay weight.",
        transit_malefic_line_rationale="Transit malefic angular pressure raises the risk score at reduced overlay weight.",
        transit_malefic_crossing_rationale="Transit malefic crossings raise the risk score at reduced overlay weight.",
    )


def evaluate_accident_pressure_heuristic(
    *,
    result_id: str,
    result_label: str,
    result_summary: str,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    relocation: Dict[str, Any],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    contributions: List[Dict[str, Any]] = []
    contributions.extend(
        _heuristic_line_contributions(
            natal_rows,
            context="natal",
            bodies=ACCIDENT_HEURISTIC_CORE,
            sign=1.0,
            multiplier=1.55,
            rationale="Mars, Uranus, and Pluto angular pressure raise acute accident and crash exposure.",
        )
    )
    contributions.extend(
        _heuristic_line_contributions(
            natal_rows,
            context="natal",
            bodies=ACCIDENT_HEURISTIC_SECONDARY,
            sign=1.0,
            multiplier=1.1,
            rationale="Saturn and Chiron add bodily strain, collision damage, and vulnerable recovery signatures.",
        )
    )
    contributions.extend(
        _heuristic_line_contributions(
            natal_rows,
            context="natal",
            bodies=HEURISTIC_BENEFICS,
            sign=-1.0,
            multiplier=0.9,
            rationale="Nearby benefic angular pressure lowers acute accident risk by softening the field.",
        )
    )
    contributions.extend(
        _heuristic_crossing_contributions(
            natal_crossings,
            context="natal",
            bodies=ACCIDENT_HEURISTIC_CORE | ACCIDENT_HEURISTIC_SECONDARY,
            sign=1.0,
            multiplier=1.2,
            min_body_matches=2,
            rationale="Dense malefic crossings raise acute accident pressure.",
        )
    )
    contributions.extend(
        _specific_crossing_contributions(
            natal_crossings,
            context="natal",
            pairs=(("Mars", "Uranus"), ("Mars", "Pluto"), ("Mars", "Saturn"), ("Uranus", "Pluto")),
            multiplier=1.45,
            rationale="Mars/Uranus, Mars/Pluto, Mars/Saturn, and Uranus/Pluto are the sharpest acute accident signatures in this heuristic.",
        )
    )

    if transit_rows:
        contributions.extend(
            _heuristic_line_contributions(
                transit_rows,
                context="transit",
                bodies=ACCIDENT_HEURISTIC_CORE,
                sign=1.0,
                multiplier=1.55 * transit_multiplier,
                rationale="Transit acute-malefic angular pressure raises short-term accident exposure at overlay weight.",
            )
        )
        contributions.extend(
            _heuristic_line_contributions(
                transit_rows,
                context="transit",
                bodies=ACCIDENT_HEURISTIC_SECONDARY,
                sign=1.0,
                multiplier=1.1 * transit_multiplier,
                rationale="Transit Saturn and Chiron add secondary accident strain at overlay weight.",
            )
        )
        contributions.extend(
            _heuristic_line_contributions(
                transit_rows,
                context="transit",
                bodies=HEURISTIC_BENEFICS,
                sign=-1.0,
                multiplier=0.9 * transit_multiplier,
                rationale="Transit benefic angular pressure lowers acute accident risk at overlay weight.",
            )
        )
    if transit_crossings:
        contributions.extend(
            _heuristic_crossing_contributions(
                transit_crossings,
                context="transit",
                bodies=ACCIDENT_HEURISTIC_CORE | ACCIDENT_HEURISTIC_SECONDARY,
                sign=1.0,
                multiplier=1.2 * transit_multiplier,
                min_body_matches=2,
                rationale="Transit malefic crossings raise acute accident pressure at overlay weight.",
            )
        )
        contributions.extend(
            _specific_crossing_contributions(
                transit_crossings,
                context="transit",
                pairs=(("Mars", "Uranus"), ("Mars", "Pluto"), ("Mars", "Saturn"), ("Uranus", "Pluto")),
                multiplier=1.45 * transit_multiplier,
                rationale="Transit accident-pattern crossings raise acute accident pressure at overlay weight.",
            )
        )

    relocation_metrics = [
        ("health_risk", 2.3, "High bodily-risk relocation signatures raise accident exposure."),
        ("malefic_pressure", 1.5, "General malefic relocation pressure raises acute accident exposure."),
        ("uncertainty", 1.2, "Instability and volatility make accident-prone places harsher."),
        ("conflict_pressure", 0.8, "Conflict-heavy environments raise collision and bodily-friction exposure."),
        ("benefic_balance", -1.3, "Strong benefic balance lowers accident pressure."),
        ("stability", -0.9, "Stable environments lower accident pressure."),
    ]
    for metric_name, weight, rationale in relocation_metrics:
        metric_value = _relocation_metric_value(relocation, metric_name)
        if metric_value <= 0.0:
            continue
        contributions.append(
            {
                "kind": "modifier",
                "context": "relocation",
                "score": round(weight * metric_value, 4),
                "metric": metric_name,
                "metric_value": round(metric_value, 4),
                "rationale": rationale,
            }
        )

    raw_total = round(sum(float(item.get("score") or 0.0) for item in contributions), 4)
    score = _normalize_simple_score(raw_total, midpoint=25.0, slope=5.0)
    positives = sorted(
        [item for item in contributions if float(item.get("score") or 0.0) > 0.0],
        key=lambda item: float(item.get("score") or 0.0),
        reverse=True,
    )
    cautions = sorted(
        [item for item in contributions if float(item.get("score") or 0.0) < 0.0],
        key=lambda item: float(item.get("score") or 0.0),
    )
    breakdown = {
        "natal": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "natal"), 4),
        "transit": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "transit"), 4),
        "relocation": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "relocation"), 4),
        "constraints": 0.0,
    }
    return {
        "goal": {
            "id": result_id,
            "label": result_label,
            "summary": result_summary,
        },
        "raw_score": raw_total,
        "score": score,
        "breakdown": breakdown,
        "top_supports": positives[:3],
        "top_cautions": cautions[:3],
        "contributions": contributions,
    }


def evaluate_gambling_natal_curated_heuristic(
    *,
    result_id: str,
    result_label: str,
    result_summary: str,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    relocation: Dict[str, Any],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
    include_natal: bool = True,
    include_transit: bool = True,
    include_relocation: bool = True,
    include_activation_floor: bool = True,
    activation_override: Optional[float] = None,
) -> Dict[str, Any]:
    contributions: List[Dict[str, Any]] = []
    activation = float(activation_override) if activation_override is not None else max(
        _relocation_metric_value(relocation, "gambling_activation"),
        _relocation_metric_value(relocation, "asc_gambling_harmony") * 0.9,
        _relocation_metric_value(relocation, "gambling_ruler_strength") * 0.85,
    )
    activation = _clamp01(activation)
    natal_support_multiplier = 0.18 + (0.82 * activation)
    if include_natal:
        contributions.extend(
            _heuristic_line_contributions(
                natal_rows,
                context="natal",
                bodies={"Jupiter", "Venus"},
                sign=1.0,
                multiplier=1.25 * natal_support_multiplier,
                rationale="Jupiter and Venus lines are the cleanest natal place signals for ease, luck, and favorable speculative flow.",
            )
        )
        contributions.extend(
            _heuristic_line_contributions(
                natal_rows,
                context="natal",
                bodies={"Mercury", "Sun", "Moon"},
                sign=1.0,
                multiplier=0.8 * natal_support_multiplier,
                rationale="Mercury, Sun, and Moon lines support judgment, confidence, and live momentum when the relocation chart already confirms gambling signatures.",
            )
        )
        contributions.extend(
            _heuristic_line_contributions(
                natal_rows,
                context="natal",
                bodies=GAMBLING_CAUTION_BODIES,
                sign=-1.0,
                multiplier=1.0,
                rationale="Harsh natal angular pressure from Saturn, Mars, Neptune, Pluto, and Uranus undermines speculation through blockage, volatility, or distorted judgment.",
            )
        )
        contributions.extend(
            _specific_crossing_contributions(
                natal_crossings,
                context="natal",
                pairs=(("Jupiter", "Venus"), ("Jupiter", "Mercury"), ("Venus", "Mercury"), ("Jupiter", "Sun")),
                multiplier=1.25 * natal_support_multiplier,
                rationale="Jupiter/Venus and allied benefic-mercurial crossings are the strongest natal place signatures for opportunity, judgment, and payout momentum.",
            )
        )
        contributions.extend(
            _specific_crossing_contributions(
                natal_crossings,
                context="natal",
                pairs=(("Venus", "Neptune"), ("Jupiter", "Neptune"), ("Mars", "Saturn"), ("Mars", "Pluto"), ("Saturn", "Neptune")),
                multiplier=-1.15,
                rationale="Neptunian glamour and heavy malefic crossings are the sharpest natal caution signatures for gambling places.",
            )
        )

    if include_transit and transit_rows:
        contributions.extend(
            _heuristic_line_contributions(
                transit_rows,
                context="transit",
                bodies={"Jupiter", "Venus"},
                sign=1.0,
                multiplier=1.25 * transit_multiplier,
                rationale="Transit benefic angular pressure can briefly amplify a good natal gambling place, but only at overlay weight.",
            )
        )
        contributions.extend(
            _heuristic_line_contributions(
                transit_rows,
                context="transit",
                bodies=GAMBLING_CAUTION_BODIES,
                sign=-1.0,
                multiplier=1.0 * transit_multiplier,
                rationale="Transit malefic angular pressure temporarily adds drag and overexposure at overlay weight.",
            )
        )
    if include_transit and transit_crossings:
        contributions.extend(
            _specific_crossing_contributions(
                transit_crossings,
                context="transit",
                pairs=(("Jupiter", "Venus"), ("Jupiter", "Mercury"), ("Venus", "Mercury"), ("Jupiter", "Sun")),
                multiplier=1.25 * transit_multiplier,
                rationale="Transit benefic crossings can briefly sharpen a natal gambling place at overlay weight.",
            )
        )
        contributions.extend(
            _specific_crossing_contributions(
                transit_crossings,
                context="transit",
                pairs=(("Venus", "Neptune"), ("Jupiter", "Neptune"), ("Mars", "Saturn"), ("Mars", "Pluto"), ("Saturn", "Neptune")),
                multiplier=-1.15 * transit_multiplier,
                rationale="Transit caution crossings briefly worsen natal gambling conditions at overlay weight.",
            )
        )

    relocation_metrics = [
        ("gambling_activation", 2.3, "The relocated chart needs direct gambling activation through the 5th house, Moon, or curated ruler links before benefic lines should be trusted."),
        ("gambling_signature", 1.55, "Direct 5th, 2nd, and 8th-house speculative signatures distinguish gambling places from generic social or money places."),
        ("asc_ruler_strength", 2.0, "A strong relocated Ascendant ruler makes the native able to act cleanly and capitalize on openings."),
        ("gambling_ruler_strength", 2.35, "A strong relocated 5th ruler is the core natal-curated gambling signature for speculative agency."),
        ("asc_ruler_asc_support", 0.9, "The legacy rule pack explicitly rewards the querent ruler in good aspect to the Ascendant."),
        ("gambling_ruler_asc_support", 0.95, "The legacy rule pack explicitly rewards the quesited ruler in good aspect to the Ascendant."),
        ("moon_asc_support", 1.1, "The legacy rule pack explicitly rewards Moon sextile, trine, or conjunction to the Ascendant."),
        ("asc_gambling_harmony", 2.65, "Harmony between the Ascendant ruler and 5th ruler is the closest natal-place analogue to the legacy querent-versus-quesited support rule."),
        ("moon_gambling_support", 1.75, "Moon support shows whether the relocated chart's flow helps the native convert opportunities into action."),
        ("grand_trine_support", 0.7, "Grand trines describe low-friction chart geometry that can let supportive gambling signatures move without repeated obstruction."),
        ("kite_support", 0.95, "A kite turns easy trine geometry into directed release, which can help a speculative chart convert opportunity into action."),
        ("speculation", 1.2, "Classic benefic speculative house placements still matter as a secondary support layer."),
        ("money_support", 0.95, "Support from the 2nd, 8th, and 11th houses helps bankroll circulation without defining the whole score."),
        ("benefic_balance", 0.55, "General benefic balance is helpful, but no longer substitutes for the curated gambling rulers."),
        ("south_node_obstruction", -1.45, "South Node contact acts as a traditional obstruction marker, especially when it catches the Ascendant, the rulers, or the Moon."),
        ("asc_interception", -2.6, "An intercepted Ascendant axis traps the native's agency inside the chart, matching the legacy 'ascendant is intercepted' caution."),
        ("t_square_pressure", -1.05, "T-square geometry adds strain, over-complication, and forced responses around gambling decisions."),
        ("speculation_drag", -1.7, "Heavy anti-speculation signatures in the relocated chart drag down gambling performance."),
        ("moon_liability", -2.25, "Void Moon and hostile Moon applications are major gambling cautions even in natal-place scoring."),
        ("retrograde_liability", -1.8, "Retrograde or combust key rulers weaken reliability and payoff conversion."),
        ("asc_gambling_tension", -2.3, "Hard tension between the Ascendant ruler and 5th ruler shows the native and the gamble working against each other."),
        ("malefic_pressure", -0.85, "General malefic relocation pressure remains a caution, but weaker than the curated ruler logic."),
        ("uncertainty", -0.55, "Diffuse or unstable places add noise and impulsivity to speculation."),
    ]
    if include_relocation:
        for metric_name, weight, rationale in relocation_metrics:
            metric_value = _relocation_metric_value(relocation, metric_name)
            if metric_value <= 0.0:
                continue
            contributions.append(
                {
                    "kind": "modifier",
                    "context": "relocation",
                    "score": round(weight * metric_value, 4),
                    "metric": metric_name,
                    "metric_value": round(metric_value, 4),
                    "rationale": rationale,
                }
            )
    if include_activation_floor and activation < 0.35:
        activation_gap = round((0.35 - activation) / 0.35, 4)
        contributions.append(
            {
                "kind": "modifier",
                "context": "relocation",
                "score": round(-1.15 * activation_gap, 4),
                "metric": "gambling_activation_floor",
                "metric_value": activation_gap,
                "rationale": "Without clear 5th-house, Moon, or curated ruler activation, benefic lines alone should not make a place look like a gambling specialist.",
            }
        )

    raw_total = round(sum(float(item.get("score") or 0.0) for item in contributions), 4)
    score = _normalize_simple_score(raw_total, midpoint=50.0, slope=14.0)
    positives = sorted(
        [item for item in contributions if float(item.get("score") or 0.0) > 0.0],
        key=lambda item: float(item.get("score") or 0.0),
        reverse=True,
    )
    cautions = sorted(
        [item for item in contributions if float(item.get("score") or 0.0) < 0.0],
        key=lambda item: float(item.get("score") or 0.0),
    )
    breakdown = {
        "natal": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "natal"), 4),
        "transit": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "transit"), 4),
        "relocation": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "relocation"), 4),
        "constraints": 0.0,
    }
    return {
        "goal": {
            "id": result_id,
            "label": result_label,
            "summary": result_summary,
        },
        "raw_score": raw_total,
        "score": score,
        "breakdown": breakdown,
        "top_supports": positives[:3],
        "top_cautions": cautions[:3],
        "contributions": contributions,
    }


def _normalize_goal_score(model: Dict[str, Any], raw_total: float) -> int:
    normalization = model.get("normalization") or {}
    min_score = float(normalization["min_score"]) if normalization.get("min_score") is not None else -10.0
    max_score = float(normalization["max_score"]) if normalization.get("max_score") is not None else 20.0
    if max_score <= min_score:
        return int(round(max(0.0, min(100.0, raw_total))))
    neutral_score = float(normalization["neutral_score"]) if normalization.get("neutral_score") is not None else 50.0
    neutral_score = max(0.0, min(100.0, neutral_score))
    if raw_total >= 0.0:
        denominator = max(1e-9, max_score)
        score = neutral_score + ((raw_total / denominator) * (100.0 - neutral_score))
    else:
        denominator = max(1e-9, abs(min_score))
        score = neutral_score + ((raw_total / denominator) * neutral_score)
    return int(round(max(0.0, min(100.0, score))))


def _score_line_component(
    component: Dict[str, Any],
    rows: Sequence[Dict[str, Any]],
    context: str,
    *,
    relocation: Optional[Dict[str, Any]] = None,
    multiplier: float = 1.0,
    distance_scale: float = 1.0,
    distance_profile: str = "standard",
) -> Optional[Dict[str, Any]]:
    planet = str(component.get("planet") or "")
    allowed_angles = {str(angle).upper() for angle in component.get("angles") or []}
    distance = component.get("distance") or {}
    primary_max_km = float(distance.get("primary_max_km") or 300.0)
    standard_max_km = float(distance.get("max_km") or 500.0)
    max_km = standard_max_km * max(0.1, float(distance_scale))
    falloff = str(distance.get("falloff") or "linear")
    candidates = [
        row for row in rows
        if str(row.get("body") or "") == planet and str(row.get("angle") or "").upper() in allowed_angles
    ]
    if not candidates:
        return None
    best = min(candidates, key=lambda row: float(row.get("distance_km") or 999999.0))
    best_distance_km = float(best.get("distance_km") or 0.0)
    factor = _score_distance(best_distance_km, max_km=max_km, falloff=falloff)
    if factor <= 0.0:
        return None
    weight = float(component.get("weight") or 0.0)
    condition_factor, condition_meta = _condition_factor(
        (relocation or {}).get("planet_conditions") or {},
        [planet],
        weight=weight,
    )
    birth_time_value = ((((relocation or {}).get("confidence") or {}).get("birth_time") or {}).get("value"))
    birth_time_factor = float(birth_time_value) if birth_time_value is not None else 1.0
    raw_score = weight * factor * float(multiplier) * condition_factor * birth_time_factor
    row_id = str(best.get("id") or f"{planet}:{str(best.get('angle') or '').upper()}")
    return {
        "kind": "line",
        "context": context,
        "component": component,
        "score": round(raw_score, 3),
        "matched": best,
        "label": best.get("label"),
        "distance_km": best.get("distance_km"),
        "distance_factor": round(factor, 6),
        "distance_policy": {
            "profile": str(distance_profile),
            "primary_max_km": round(primary_max_km, 3),
            "standard_max_km": round(standard_max_km, 3),
            "effective_max_km": round(max_km, 3),
            "status": _distance_policy_status(
                profile=str(distance_profile),
                distance_km=best_distance_km,
                primary_max_km=primary_max_km,
                standard_max_km=standard_max_km,
                effective_max_km=max_km,
                falloff=falloff,
                active=True,
            ),
        },
        "evidence_keys": [f"{context}:line:{row_id}"],
        "evidence_block": "transit_overlay" if context == "transit" else "natal_lines",
        "natal_condition": condition_meta,
        "birth_time_factor": round(birth_time_factor, 4),
        "rationale": component.get("rationale"),
    }


def _canonical_crossing_key(row: Dict[str, Any]) -> str:
    explicit = str(row.get("canonical_id") or row.get("crossing_id") or row.get("paran_id") or "").strip()
    if explicit:
        return explicit
    lines = [str(item).strip() for item in (row.get("lines") or []) if str(item).strip()]
    if not lines:
        row_id = str(row.get("id") or "").strip()
        if "|" in row_id:
            lines = [item.strip() for item in row_id.split("|") if item.strip()]
        elif row_id:
            return row_id
    if lines:
        return "|".join(sorted(lines))
    planets = sorted(str(item).strip() for item in (row.get("planets") or []) if str(item).strip())
    point = row.get("point")
    point_token = ""
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        try:
            point_token = f":{round(float(point[0]), 3)}:{round(float(point[1]), 3)}"
        except Exception:
            point_token = ""
    kind = str(row.get("kind") or "crossing").strip().lower()
    return f"{kind}:{'|'.join(planets)}{point_token}"


def _score_crossing_component(
    component: Dict[str, Any],
    crossings: Sequence[Dict[str, Any]],
    context: str,
    *,
    relocation: Optional[Dict[str, Any]] = None,
    multiplier: float = 1.0,
    distance_scale: float = 1.0,
    distance_profile: str = "standard",
) -> Optional[Dict[str, Any]]:
    target_pair = tuple(sorted(str(name) for name in component.get("pair") or []))
    if len(target_pair) != 2:
        return None
    distance = component.get("distance") or {}
    primary_max_km = float(distance.get("primary_max_km") or 300.0)
    standard_max_km = float(distance.get("max_km") or 500.0)
    max_km = standard_max_km * max(0.1, float(distance_scale))
    falloff = str(distance.get("falloff") or "linear")
    candidates_by_key: Dict[str, Dict[str, Any]] = {}
    for item in crossings:
        if not _is_exact_crossing(item):
            continue
        pair = tuple(sorted(str(name) for name in item.get("planets") or []))
        if pair == target_pair:
            canonical_key = _canonical_crossing_key(item)
            current = candidates_by_key.get(canonical_key)
            if current is None or float(item.get("distance_km") or 999999.0) < float(current.get("distance_km") or 999999.0):
                candidates_by_key[canonical_key] = item
    candidates = list(candidates_by_key.values())
    if not candidates:
        return None
    best = min(candidates, key=lambda row: float(row.get("distance_km") or 999999.0))
    best_distance_km = float(best.get("distance_km") or 0.0)
    factor = _score_distance(best_distance_km, max_km=max_km, falloff=falloff)
    if factor <= 0.0:
        return None
    weight = float(component.get("weight") or 0.0)
    condition_factor, condition_meta = _condition_factor(
        (relocation or {}).get("planet_conditions") or {},
        target_pair,
        weight=weight,
    )
    birth_time_value = ((((relocation or {}).get("confidence") or {}).get("birth_time") or {}).get("value"))
    birth_time_factor = float(birth_time_value) if birth_time_value is not None else 1.0
    interaction_scale_value = component.get("interaction_scale")
    interaction_scale = max(
        0.0,
        min(1.0, float(interaction_scale_value) if interaction_scale_value is not None else 0.5),
    )
    raw_score = (
        weight
        * factor
        * float(multiplier)
        * condition_factor
        * birth_time_factor
        * interaction_scale
    )
    canonical_key = _canonical_crossing_key(best)
    return {
        "kind": "crossing",
        "context": context,
        "component": component,
        "score": round(raw_score, 3),
        "matched": best,
        "label": best.get("label"),
        "distance_km": best.get("distance_km"),
        "distance_factor": round(factor, 6),
        "distance_policy": {
            "profile": str(distance_profile),
            "primary_max_km": round(primary_max_km, 3),
            "standard_max_km": round(standard_max_km, 3),
            "effective_max_km": round(max_km, 3),
            "status": _distance_policy_status(
                profile=str(distance_profile),
                distance_km=best_distance_km,
                primary_max_km=primary_max_km,
                standard_max_km=standard_max_km,
                effective_max_km=max_km,
                falloff=falloff,
                active=True,
            ),
        },
        "canonical_crossing_id": canonical_key,
        "evidence_keys": [f"{context}:crossing:{canonical_key}"],
        "evidence_block": "transit_overlay" if context == "transit" else "crossing_interactions",
        "interaction_residual": True,
        "interaction_scale": interaction_scale,
        "natal_condition": condition_meta,
        "birth_time_factor": round(birth_time_factor, 4),
        "rationale": component.get("rationale"),
    }


def _score_relocation_component(component: Dict[str, Any], relocation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    planets = [str(item) for item in component.get("planets") or []]
    houses = {int(item) for item in component.get("houses") or [] if isinstance(item, int)}
    angles = {str(item).upper() for item in component.get("angles") or []}
    planet_houses = relocation.get("planet_houses") or {}
    planet_angles = relocation.get("planet_angles") or {}
    metrics = relocation.get("metrics") or {}

    if component.get("kind") == "modifier":
        metric_name = str(component.get("metric") or "")
        try:
            factor = float(metrics.get(metric_name) or 0.0)
        except Exception:
            return None
        # Relocation metrics are normalized evidence magnitudes. Negative values
        # must never invert a caution weight into accidental support.
        if factor <= 0.0:
            return None
        weight = float(component.get("weight") or 0.0)
        evidence_role = str(component.get("evidence_role") or "local").strip().lower()
        evidence_keys = [
            str(item)
            for item in ((relocation.get("metric_evidence") or {}).get(metric_name) or [])
            if str(item)
        ]
        if not evidence_keys:
            evidence_keys = [f"metric:{metric_name}"]
        raw_score = 0.0 if evidence_role == "global_prior" else weight * factor
        return {
            "kind": "modifier",
            "context": "relocation",
            "component": component,
            "score": round(raw_score, 3),
            "metric": metric_name,
            "metric_value": round(factor, 3),
            "evidence_keys": evidence_keys,
            "evidence_block": "global_prior" if evidence_role == "global_prior" else "relocation",
            "evidence_role": evidence_role,
            "prior_weight": round(weight * factor, 3) if evidence_role == "global_prior" else None,
            "rationale": component.get("rationale"),
        }

    if not planets:
        return None

    hits: List[str] = []
    evidence_keys: List[str] = []
    for planet in planets:
        house = planet_houses.get(planet)
        angle = planet_angles.get(planet)
        matched = False
        if houses and house in houses:
            matched = True
            evidence_keys.append(f"relocation:{planet}:house:{house}")
        if angles and angle in angles:
            matched = True
            evidence_keys.append(f"relocation:{planet}:angle:{angle}")
        if matched:
            hits.append(planet)
    if not hits:
        return None
    factor = len(hits) / max(1, len(planets))
    weight = float(component.get("weight") or 0.0)
    condition_factor, condition_meta = _condition_factor(
        relocation.get("planet_conditions") or {},
        hits,
        weight=weight,
    )
    birth_time_value = (((relocation.get("confidence") or {}).get("birth_time") or {}).get("value"))
    birth_time_factor = float(birth_time_value) if birth_time_value is not None else 1.0
    raw_score = weight * factor * condition_factor * birth_time_factor
    return {
        "kind": "relocation",
        "context": "relocation",
        "component": component,
        "score": round(raw_score, 3),
        "matched_planets": hits,
        "evidence_keys": list(dict.fromkeys(evidence_keys)),
        "evidence_block": "relocation",
        "natal_condition": condition_meta,
        "birth_time_factor": round(birth_time_factor, 4),
        "rationale": component.get("rationale"),
    }


def _constraint_matches(operator: str, metric_value: float, threshold: float) -> bool:
    if operator == "gt":
        return metric_value > threshold
    if operator == "gte":
        return metric_value >= threshold
    if operator == "lt":
        return metric_value < threshold
    if operator == "lte":
        return metric_value <= threshold
    return False


def _score_constraint_component(component: Dict[str, Any], relocation: Dict[str, Any], current_total: float) -> Optional[Dict[str, Any]]:
    metrics = relocation.get("metrics") or {}
    metric_name = str(component.get("metric") or "")
    operator = str(component.get("operator") or "").strip().lower()
    threshold = float(component.get("threshold") or 0.0)
    metric_value = float(metrics.get(metric_name) or 0.0)
    if not metric_name or not operator:
        return None
    if not _constraint_matches(operator, metric_value, threshold):
        return None

    score = 0.0
    if component.get("add") is not None:
        score += float(component.get("add") or 0.0)

    cap_score = component.get("cap_score")
    if cap_score is not None and current_total > float(cap_score):
        score += float(cap_score) - float(current_total)

    multiplier = component.get("multiplier")
    if multiplier is not None:
        multiplier = float(multiplier)
        polarity = str(component.get("polarity") or "neutral").strip().lower()
        if polarity == "support":
            signed_base = max(0.0, float(current_total))
        elif polarity == "caution":
            signed_base = min(0.0, float(current_total))
        else:
            signed_base = float(current_total)
        score += signed_base * (multiplier - 1.0)

    if abs(score) < 1e-9:
        return None

    return {
        "kind": "constraint",
        "context": "constraints",
        "component": component,
        "score": round(score, 3),
        "metric": metric_name,
        "metric_value": round(metric_value, 3),
        "evidence_keys": [],
        "evidence_block": "constraints",
        "rationale": component.get("rationale"),
    }


def _model_scoring_scopes(model: Dict[str, Any]) -> List[Tuple[Dict[str, Any], str, float]]:
    composition = model.get("composition") or {}
    if str(composition.get("mode") or "standalone").strip().lower() != "specialist_residual":
        return [(model, "model", 1.0)]

    parent_id = str(composition.get("parent_id") or "").strip().lower()
    if not parent_id:
        raise ValueError(f"Specialist goal model {model.get('id')} is missing composition.parent_id")
    parent = get_goal_model(parent_id)
    parent_composition = parent.get("composition") or {}
    if str(parent_composition.get("mode") or "standalone").strip().lower() != "standalone":
        raise ValueError(f"Specialist goal model {model.get('id')} cannot inherit another specialist model")
    parent_weight = float(composition.get("parent_weight") if composition.get("parent_weight") is not None else 1.0)
    return [(parent, "parent", parent_weight), (model, "specialist_residual", 1.0)]


def _claim_atomic_evidence(
    contribution: Dict[str, Any],
    claimed: set[str],
) -> Optional[Dict[str, Any]]:
    evidence_role = str(contribution.get("evidence_role") or "local").strip().lower()
    if evidence_role == "global_prior":
        contribution["atomic_factor"] = 0.0
        contribution["deduplicated_evidence"] = []
        return contribution
    keys = list(dict.fromkeys(str(item) for item in (contribution.get("evidence_keys") or []) if str(item)))
    if not keys:
        component = contribution.get("component") or {}
        component_id = str(component.get("component_id") or "").strip()
        if component_id:
            keys = [f"component:{component_id}"]
        else:
            keys = [
                "component:"
                + ":".join(
                    [
                        str(contribution.get("context") or ""),
                        str(contribution.get("kind") or ""),
                        str(contribution.get("metric") or contribution.get("label") or ""),
                    ]
                )
            ]
    unique_keys = [key for key in keys if key not in claimed]
    if not unique_keys:
        return None
    atomic_factor = len(unique_keys) / float(len(keys))
    contribution["score"] = round(float(contribution.get("score") or 0.0) * atomic_factor, 4)
    contribution["atomic_factor"] = round(atomic_factor, 4)
    contribution["evidence_keys"] = unique_keys
    contribution["deduplicated_evidence"] = [key for key in keys if key not in unique_keys]
    claimed.update(unique_keys)
    if abs(float(contribution.get("score") or 0.0)) < 1e-9:
        return None
    return contribution


def _diminish_and_cap_contributions(
    contributions: List[Dict[str, Any]],
    evidence_policy: Dict[str, Any],
) -> None:
    block_caps = dict(DEFAULT_EVIDENCE_POLICY["block_caps"])
    block_caps.update(evidence_policy.get("block_caps") or {})
    block_names = {
        str(item.get("evidence_block") or "")
        for item in contributions
        if str(item.get("evidence_block") or "") not in {"", "constraints", "global_prior"}
    }
    for block in sorted(block_names):
        rows = [
            item
            for item in contributions
            if str(item.get("evidence_block") or "") == block
            and abs(float(item.get("score") or 0.0)) > 1e-9
        ]
        rows.sort(key=lambda item: abs(float(item.get("score") or 0.0)), reverse=True)
        for rank, item in enumerate(rows):
            factor = DIMINISHING_RETURN_FACTORS[min(rank, len(DIMINISHING_RETURN_FACTORS) - 1)]
            item["pre_diminishing_score"] = round(float(item.get("score") or 0.0), 4)
            item["diminishing_factor"] = factor
            item["score"] = round(float(item.get("score") or 0.0) * factor, 4)

        cap = float(block_caps.get(block) or 0.0)
        magnitude = sum(abs(float(item.get("score") or 0.0)) for item in rows)
        if cap <= 0.0 or magnitude <= cap:
            continue
        cap_factor = cap / magnitude
        for item in rows:
            item["block_cap_factor"] = round(cap_factor, 4)
            item["score"] = round(float(item.get("score") or 0.0) * cap_factor, 4)


def _cap_specialist_residual(contributions: List[Dict[str, Any]], model: Dict[str, Any]) -> None:
    composition = model.get("composition") or {}
    if str(composition.get("mode") or "").strip().lower() != "specialist_residual":
        return
    max_abs_residual = float(
        composition.get("max_abs_residual")
        if composition.get("max_abs_residual") is not None
        else 6.0
    )
    residual_rows = [
        item
        for item in contributions
        if item.get("model_scope") == "specialist_residual"
        and item.get("evidence_block") != "global_prior"
    ]
    residual_total = sum(float(item.get("score") or 0.0) for item in residual_rows)
    if max_abs_residual <= 0.0 or abs(residual_total) <= max_abs_residual:
        return
    cap_factor = max_abs_residual / abs(residual_total)
    for item in residual_rows:
        item["residual_cap_factor"] = round(cap_factor, 4)
        item["score"] = round(float(item.get("score") or 0.0) * cap_factor, 4)


def _evidence_policy_for(model: Dict[str, Any]) -> Dict[str, Any]:
    policy = dict(DEFAULT_EVIDENCE_POLICY)
    policy["block_caps"] = dict(DEFAULT_EVIDENCE_POLICY["block_caps"])
    configured = model.get("evidence_policy") or {}
    for key, value in configured.items():
        if key == "block_caps":
            policy["block_caps"].update(value or {})
        else:
            policy[key] = value
    return policy


def _evidence_summary(
    model: Dict[str, Any],
    contributions: Sequence[Dict[str, Any]],
    relocation: Dict[str, Any],
) -> Dict[str, Any]:
    policy = _evidence_policy_for(model)
    scored_rows = [
        item
        for item in contributions
        if item.get("evidence_block") not in {"constraints", "global_prior"}
        and abs(float(item.get("score") or 0.0)) > 1e-9
    ]
    unique_keys = {
        str(key)
        for item in scored_rows
        for key in (item.get("evidence_keys") or [])
        if str(key)
    }
    magnitude = sum(abs(float(item.get("score") or 0.0)) for item in scored_rows)
    positive = sum(max(0.0, float(item.get("score") or 0.0)) for item in scored_rows)
    negative = sum(abs(min(0.0, float(item.get("score") or 0.0))) for item in scored_rows)
    count = len(unique_keys)
    minimum = max(1, int(policy.get("min_independent_signals") or 1))
    if count == 0:
        strength = "insufficient"
        status = "no_activation"
    elif count < minimum:
        strength = "insufficient"
        status = "below_evidence_floor"
    elif magnitude < float(policy.get("weak_magnitude") or 2.5) or count == 1:
        strength = "weak"
        status = "sufficient"
    elif magnitude >= float(policy.get("strong_magnitude") or 8.0) and count >= 3:
        strength = "strong"
        status = "sufficient"
    else:
        strength = "moderate"
        status = "sufficient"

    if count == 0:
        direction = "no_activation"
    elif magnitude <= 1e-9 or abs(positive - negative) <= magnitude * 0.12:
        direction = "neutral"
    elif positive > 0.0 and negative > 0.0 and min(positive, negative) >= max(positive, negative) * 0.45:
        direction = "mixed"
    elif positive > negative:
        direction = "supportive"
    else:
        direction = "cautionary"

    birth_time = ((relocation.get("confidence") or {}).get("birth_time") or {})
    birth_time_confidence = float(birth_time.get("value")) if birth_time.get("value") is not None else 1.0
    status_name = str(model.get("status") or "").strip().lower()
    ranking_eligible = (
        status == "sufficient"
        and status_name == "active"
        and birth_time_confidence >= float(policy.get("min_birth_time_confidence") or 0.5)
    )
    ineligible_reasons: List[str] = []
    if status != "sufficient":
        ineligible_reasons.append(status)
    if status_name != "active":
        ineligible_reasons.append(f"model_status_{status_name or 'unknown'}")
    if birth_time_confidence < float(policy.get("min_birth_time_confidence") or 0.5):
        ineligible_reasons.append("birth_time_uncertainty")
    return {
        "status": status,
        "strength": strength,
        "direction": direction,
        "independent_signal_count": count,
        "minimum_independent_signals": minimum,
        "magnitude": round(magnitude, 4),
        "support_magnitude": round(positive, 4),
        "caution_magnitude": round(negative, 4),
        "ranking_eligible": ranking_eligible,
        "ranking_ineligible_reasons": ineligible_reasons,
    }


def _distance_contribution_key(item: Dict[str, Any]) -> str:
    component = item.get("component") or {}
    component_id = str(component.get("component_id") or "").strip()
    evidence_keys = "|".join(sorted(str(key) for key in (item.get("evidence_keys") or []) if str(key)))
    matched = item.get("matched") or {}
    matched_id = str(
        item.get("canonical_crossing_id")
        or matched.get("id")
        or item.get("label")
        or ""
    ).strip()
    identity = component_id or evidence_keys or matched_id
    return ":".join(
        [
            str(item.get("context") or ""),
            str(item.get("model_scope") or ""),
            str(item.get("source_model_id") or ""),
            str(item.get("kind") or ""),
            identity,
        ]
    )


def _distance_policy_status(
    *,
    profile: str,
    distance_km: float,
    primary_max_km: float,
    standard_max_km: float,
    effective_max_km: float,
    falloff: str,
    active: bool,
) -> str:
    if distance_km > effective_max_km:
        return "excluded_outside_profile"
    if _score_distance(distance_km, max_km=effective_max_km, falloff=falloff) <= 0.0:
        return "excluded_zero_at_boundary"
    if not active:
        return "excluded_by_profile_evidence_policy"
    if profile == "wide" and distance_km > standard_max_km:
        return "included_wide_sensitivity"
    if distance_km > primary_max_km:
        return "included_extended"
    if profile == "conservative":
        return "included_conservative"
    return "included_primary"


def _distance_sensitivity(
    model: Dict[str, Any],
    profile_results: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    multipliers = _distance_profile_multipliers(model)
    policy = model.get("distance_policy") or {}

    candidates: Dict[str, Dict[str, Any]] = {}
    contributions_by_profile: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for profile in multipliers:
        result = profile_results.get(profile) or {}
        indexed: Dict[str, Dict[str, Any]] = {}
        for item in result.get("contributions") or []:
            if item.get("kind") not in {"line", "crossing"} or item.get("distance_km") is None:
                continue
            key = _distance_contribution_key(item)
            indexed[key] = item
            candidates.setdefault(key, item)
        contributions_by_profile[profile] = indexed

    profiles: Dict[str, Dict[str, Any]] = {}
    for profile, multiplier in multipliers.items():
        result = profile_results.get(profile) or {}
        raw_score = float(result.get("raw_score") or 0.0)
        evidence = result.get("evidence") or {}
        observations: List[Dict[str, Any]] = []
        indexed = contributions_by_profile.get(profile) or {}
        for key, candidate in candidates.items():
            component = candidate.get("component") or {}
            distance_policy = component.get("distance") or {}
            distance_km = float(candidate.get("distance_km") or 0.0)
            primary_max_km = float(distance_policy.get("primary_max_km") or 300.0)
            standard_max_km = float(distance_policy.get("max_km") or 500.0)
            effective_max_km = standard_max_km * float(multiplier)
            falloff = str(distance_policy.get("falloff") or "linear")
            active_item = indexed.get(key)
            active = bool(active_item is not None and abs(float(active_item.get("score") or 0.0)) > 1e-9)
            matched = candidate.get("matched") or {}
            observations.append(
                {
                    "component_id": component.get("component_id"),
                    "kind": candidate.get("kind"),
                    "context": candidate.get("context"),
                    "label": candidate.get("label"),
                    "distance_km": round(distance_km, 3),
                    "display_zone": matched.get("zone"),
                    "primary_max_km": round(primary_max_km, 3),
                    "base_max_km": round(standard_max_km, 3),
                    "standard_max_km": round(standard_max_km, 3),
                    "effective_max_km": round(effective_max_km, 3),
                    "falloff": falloff,
                    "active": active,
                    "profile_score": round(float((active_item or {}).get("score") or 0.0), 4),
                    "policy_status": _distance_policy_status(
                        profile=profile,
                        distance_km=distance_km,
                        primary_max_km=primary_max_km,
                        standard_max_km=standard_max_km,
                        effective_max_km=effective_max_km,
                        falloff=falloff,
                        active=active,
                    ),
                }
            )
        observations.sort(
            key=lambda item: (
                float(item.get("distance_km") or 0.0),
                str(item.get("component_id") or ""),
            )
        )
        profiles[profile] = {
            "distance_multiplier": round(float(multiplier), 6),
            "raw_score": round(raw_score, 4),
            "score": _normalize_goal_score(model, raw_score),
            "interpretation_status": evidence.get("status"),
            "independent_signal_count": int(evidence.get("independent_signal_count") or 0),
            "distance_evidence": observations,
        }

    scores = [int((item or {}).get("score") or 0) for item in profiles.values()]
    spread = (max(scores) - min(scores)) if scores else 0
    standard_result = profile_results.get("standard") or {}
    return {
        "policy": {
            "primary_profile": str(policy.get("primary_profile") or "standard"),
            "primary_boundary_km": round(float(policy.get("primary_boundary_km") or 300.0), 3),
            "standard_cutoff_km": round(float(policy.get("standard_cutoff_km") or 500.0), 3),
            "profile_multipliers": {
                profile: round(float(multiplier), 6)
                for profile, multiplier in multipliers.items()
            },
            "note": policy.get("note"),
        },
        "profiles": profiles,
        "score_spread": spread,
        "sensitivity_stability": "high" if spread <= 6 else ("moderate" if spread <= 14 else "low"),
        "standard_raw_score": round(float(standard_result.get("raw_score") or 0.0), 4),
    }


def evaluate_goal_model(
    goal_id: str,
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    relocation: Dict[str, Any],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
    _distance_profile: str = "standard",
    _distance_scale: float = 1.0,
    _include_distance_sensitivity: bool = True,
) -> Dict[str, Any]:
    model = get_goal_model(goal_id)
    score_polarity = goal_model_score_polarity(model)
    transit_strategy = str(model.get("transit_strategy") or "overlay").strip().lower()
    effective_transit_rows = transit_rows
    effective_transit_crossings = transit_crossings
    effective_transit_multiplier = transit_multiplier
    if transit_strategy == "ignore":
        effective_transit_rows = None
        effective_transit_crossings = None
        effective_transit_multiplier = 0.0

    contributions: List[Dict[str, Any]] = []
    pending_constraints: List[Tuple[Dict[str, Any], str, str, float]] = []
    claimed_evidence: set[str] = set()
    for scoped_model, model_scope, scope_weight in _model_scoring_scopes(model):
        source_model_id = str(scoped_model.get("id") or "")
        for component in scoped_model.get("score_components") or []:
            kind = str(component.get("kind") or "")
            if kind == "constraint":
                pending_constraints.append((component, model_scope, source_model_id, scope_weight))
                continue

            scoped_contributions: List[Dict[str, Any]] = []
            if kind == "line":
                contribution = _score_line_component(
                    component,
                    natal_rows,
                    context="natal",
                    relocation=relocation,
                    multiplier=scope_weight,
                    distance_scale=_distance_scale,
                    distance_profile=_distance_profile,
                )
                if contribution:
                    scoped_contributions.append(contribution)
                if effective_transit_rows:
                    transit_contribution = _score_line_component(
                        component,
                        effective_transit_rows,
                        context="transit",
                        relocation=relocation,
                        multiplier=effective_transit_multiplier * scope_weight,
                        distance_scale=_distance_scale,
                        distance_profile=_distance_profile,
                    )
                    if transit_contribution:
                        scoped_contributions.append(transit_contribution)
            elif kind == "crossing":
                contribution = _score_crossing_component(
                    component,
                    natal_crossings,
                    context="natal",
                    relocation=relocation,
                    multiplier=scope_weight,
                    distance_scale=_distance_scale,
                    distance_profile=_distance_profile,
                )
                if contribution:
                    scoped_contributions.append(contribution)
                if effective_transit_crossings:
                    transit_contribution = _score_crossing_component(
                        component,
                        effective_transit_crossings,
                        context="transit",
                        relocation=relocation,
                        multiplier=effective_transit_multiplier * scope_weight,
                        distance_scale=_distance_scale,
                        distance_profile=_distance_profile,
                    )
                    if transit_contribution:
                        scoped_contributions.append(transit_contribution)
            elif kind in {"relocation", "modifier"}:
                contribution = _score_relocation_component(component, relocation)
                if contribution:
                    contribution["score"] = round(float(contribution.get("score") or 0.0) * scope_weight, 4)
                    scoped_contributions.append(contribution)

            for contribution in scoped_contributions:
                contribution["model_scope"] = model_scope
                contribution["source_model_id"] = source_model_id
                accepted = _claim_atomic_evidence(contribution, claimed_evidence)
                if accepted:
                    contributions.append(accepted)

    evidence_policy = _evidence_policy_for(model)
    _diminish_and_cap_contributions(contributions, evidence_policy)

    for component, model_scope, source_model_id, scope_weight in pending_constraints:
        scoped_total = sum(
            float(item.get("score") or 0.0)
            for item in contributions
            if item.get("model_scope") == model_scope
        )
        constraint = _score_constraint_component(
            component,
            relocation,
            current_total=scoped_total,
        )
        if not constraint:
            continue
        constraint["score"] = round(float(constraint.get("score") or 0.0) * scope_weight, 4)
        constraint["model_scope"] = model_scope
        constraint["source_model_id"] = source_model_id
        contributions.append(constraint)

    _cap_specialist_residual(contributions, model)

    raw_total = sum(float(item.get("score") or 0.0) for item in contributions)
    evidence = _evidence_summary(model, contributions, relocation)
    normalized_score = _normalize_goal_score(model, raw_total)
    score: Optional[int] = normalized_score if evidence["status"] == "sufficient" else None
    visible_contributions = [
        item
        for item in contributions
        if item.get("kind") != "constraint"
        and item.get("evidence_block") != "global_prior"
    ]
    positive_rows = sorted(
        [item for item in visible_contributions if float(item.get("score") or 0.0) > 0],
        key=lambda item: float(item.get("score") or 0.0),
        reverse=True,
    )
    negative_rows = sorted(
        [item for item in visible_contributions if float(item.get("score") or 0.0) < 0],
        key=lambda item: float(item.get("score") or 0.0),
    )
    if score_polarity == "higher_is_worse":
        positives = list(reversed(negative_rows))
        cautions = positive_rows
    else:
        positives = positive_rows
        cautions = negative_rows
    breakdown = {
        "natal": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "natal"), 3),
        "transit": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "transit"), 3),
        "relocation": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "relocation"), 3),
        "constraints": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("context") == "constraints"), 3),
        "parent": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("model_scope") == "parent"), 3),
        "specialist_residual": round(sum(float(item.get("score") or 0.0) for item in contributions if item.get("model_scope") == "specialist_residual"), 3),
    }
    current_profile_result = {
        "raw_score": raw_total,
        "evidence": evidence,
        "contributions": contributions,
    }
    if _include_distance_sensitivity:
        profile_results: Dict[str, Dict[str, Any]] = {
            str(_distance_profile): current_profile_result,
        }
        for profile, multiplier in _distance_profile_multipliers(model).items():
            if profile in profile_results:
                continue
            profile_evaluation = evaluate_goal_model(
                goal_id,
                natal_rows=natal_rows,
                natal_crossings=natal_crossings,
                relocation=relocation,
                transit_rows=transit_rows,
                transit_crossings=transit_crossings,
                transit_multiplier=transit_multiplier,
                _distance_profile=profile,
                _distance_scale=multiplier,
                _include_distance_sensitivity=False,
            )
            profile_contributions = profile_evaluation.get("contributions") or []
            profile_results[profile] = {
                "raw_score": sum(float(item.get("score") or 0.0) for item in profile_contributions),
                "evidence": profile_evaluation.get("evidence") or {},
                "contributions": profile_contributions,
            }
        distance_sensitivity = _distance_sensitivity(model, profile_results)
    else:
        distance_sensitivity = {
            "policy": {
                "primary_profile": str((model.get("distance_policy") or {}).get("primary_profile") or "standard"),
                "primary_boundary_km": round(
                    float((model.get("distance_policy") or {}).get("primary_boundary_km") or 300.0),
                    3,
                ),
                "standard_cutoff_km": round(
                    float((model.get("distance_policy") or {}).get("standard_cutoff_km") or 500.0),
                    3,
                ),
                "profile_multipliers": {
                    str(_distance_profile): round(float(_distance_scale), 6),
                },
                "note": (model.get("distance_policy") or {}).get("note"),
            },
            "profiles": {
                str(_distance_profile): {
                    "distance_multiplier": round(float(_distance_scale), 6),
                    "raw_score": round(raw_total, 4),
                    "score": _normalize_goal_score(model, raw_total),
                    "interpretation_status": evidence.get("status"),
                    "independent_signal_count": int(evidence.get("independent_signal_count") or 0),
                    "distance_evidence": [],
                }
            },
            "score_spread": 0,
            "sensitivity_stability": "high",
            "standard_raw_score": round(raw_total, 4) if _distance_profile == "standard" else None,
        }
    profile_scores = [
        int((item or {}).get("score") or 0)
        for item in (distance_sensitivity.get("profiles") or {}).values()
    ]
    birth_time = ((relocation.get("confidence") or {}).get("birth_time") or {})
    score_interval: Dict[str, Optional[int]]
    if score is None:
        score_interval = {"low": None, "high": None}
    else:
        low_profile = min(profile_scores) if profile_scores else score
        high_profile = max(profile_scores) if profile_scores else score
        score_interval = {
            "low": max(0, low_profile),
            "high": min(100, high_profile),
        }
    rank_stability = {
        "status": "not_applicable",
        "reason": "This is a single-location evaluation; rank stability is calculated by comparison and atlas workflows.",
        "sensitivity_proxy": distance_sensitivity.get("sensitivity_stability"),
    }
    return {
        "goal": {
            "id": model.get("id"),
            "label": model.get("label"),
            "summary": model.get("summary"),
            "status": model.get("status"),
            "scoring_engine": model.get("scoring_engine") or "declarative_components_v2",
            "composition": model.get("composition") or {"mode": "standalone"},
            "score_polarity": score_polarity,
        },
        "raw_score": round(raw_total, 3),
        "score": score,
        "score_available": score is not None,
        "score_interval": score_interval,
        "evidence_strength": evidence["strength"],
        "ranking_eligible": evidence["ranking_eligible"],
        "interpretation_status": evidence["status"],
        "evidence": evidence,
        "uncertainty": {
            "birth_time": birth_time,
            "birth_time_sampling": {
                "status": "not_sampled",
                "reason": "A single goal evaluation does not contain alternate-time chart calculations.",
            },
            "distance_sensitivity": distance_sensitivity,
            "score_interval": score_interval,
            "score_interval_method": "recomputed_distance_profiles_v1",
        },
        "rank_stability": rank_stability,
        "breakdown": breakdown,
        "top_supports": positives[:3],
        "top_cautions": cautions[:3],
        "global_priors": [
            item for item in contributions if item.get("evidence_block") == "global_prior"
        ],
        "contributions": contributions,
    }


def summarize_relocation_features(relocation: Dict[str, Any]) -> Dict[str, Any]:
    house_occupancy = relocation.get("house_occupancy") or {}
    angular_planets = [
        {"planet": planet, "angle": angle}
        for planet, angle in (relocation.get("planet_angles") or {}).items()
    ]
    prominent_houses = []
    for house in range(1, 13):
        planets = house_occupancy.get(house) or []
        if not planets:
            continue
        prominent_houses.append({"house": house, "planets": planets})
    prominent_houses.sort(key=lambda item: (-len(item.get("planets") or []), int(item.get("house") or 0)))
    metrics = relocation.get("metrics") or {}
    support_metrics = [
        (name, float(value))
        for name, value in metrics.items()
        if name not in {"uncertainty", "malefic_pressure", "conflict_pressure", "health_risk", "speculation_drag", "moon_liability", "retrograde_liability", "asc_gambling_tension"} and float(value) > 0.0
    ]
    support_metrics.sort(key=lambda item: item[1], reverse=True)
    caution_metrics = [
        (name, float(metrics.get(name) or 0.0))
        for name in ("uncertainty", "malefic_pressure", "conflict_pressure", "health_risk", "speculation_drag", "moon_liability", "retrograde_liability", "asc_gambling_tension")
        if float(metrics.get(name) or 0.0) > 0.0
    ]
    caution_metrics.sort(key=lambda item: item[1], reverse=True)

    if angular_planets:
        lead_labels = ", ".join(f"{item.get('planet')} {item.get('angle')}" for item in angular_planets[:2])
        headline = f"Relocation is led by {lead_labels}."
    elif support_metrics:
        headline = f"Relocation is strongest through {support_metrics[0][0].replace('_', ' ')} themes."
    else:
        headline = "Relocation does not yet show a dominant angular emphasis."

    support_notes = [
        f"{name.replace('_', ' ').title()} {round(value * 100)} / 100"
        for name, value in support_metrics[:3]
    ]
    caution_notes = [
        f"{name.replace('_', ' ').title()} {round(value * 100)} / 100"
        for name, value in caution_metrics[:2]
    ]
    return {
        "headline": headline,
        "angular_planets": angular_planets,
        "prominent_houses": prominent_houses[:4],
        "metrics": metrics,
        "support_notes": support_notes,
        "caution_notes": caution_notes,
    }


def list_goal_model_summaries() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for model in list_goal_models():
        status = str(model.get("status") or "").strip().lower()
        if status != "active":
            continue
        out.append(
            {
                "id": model.get("id"),
                "label": model.get("label"),
                "summary": model.get("summary"),
                "status": status or model.get("status"),
                "goal_family": model.get("goal_family"),
                "transit_strategy": model.get("transit_strategy") or "overlay",
                "score_polarity": goal_model_score_polarity(model),
            }
        )
    return out
