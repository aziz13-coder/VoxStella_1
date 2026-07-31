from __future__ import annotations

from math import isfinite
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .common import (
    Score,
    BENEFICS,
    MALEFICS,
    ANGULAR_HOUSES,
    SUCCEDENT_HOUSES,
    CADENT_HOUSES,
    TRAD_RULER,
    HI_EXALTATION,
    HI_TRIPLICITY,
    _hi_element,
    compute_morin_combustion,
    _collect_planets,
    _house_cusps,
    _house_from_lon,
    _sign_from_lon,
    _get_aspects_list,
    _ang_sep,
    _safe_float,
    _is_via_combusta,
    _is_waxing,
)

ALGOL_DEG = 56.1
SOFT_ASPECTS = {"Trine", "Sextile", "Conjunction"}
HARD_ASPECTS = {"Square", "Opposition", "Conjunction"}
ACTION_TYPES = {"battle", "attack", "defense", "siege", "retreat"}

WEIGHTS = {
    "asc_strength": 100.0,
    "mars_strength": 150.0,
    "mc_strength": 100.0,
    "moon_condition": 80.0,
    "jupiter_benefit": 60.0,
    "seventh_weakness": 70.0,
    "eighth_safety": 90.0,
    "angle_fortification": 50.0,
    "traditional_timing": 30.0,
    "fixed_stars": 40.0,
    "natal_synastry": 120.0,
}

FIXED_STARS = {
    "Regulus": {"lon": 150.0, "nature": "benefic", "orb": 2.0, "power": 20.0},
    "Spica": {"lon": 204.0, "nature": "benefic", "orb": 2.0, "power": 15.0},
    "Algol": {"lon": ALGOL_DEG, "nature": "malefic", "orb": 3.0, "power": -50.0},
    "Antares": {"lon": 249.7, "nature": "martial", "orb": 2.0, "power": 12.0},
    "Aldebaran": {"lon": 69.7, "nature": "martial", "orb": 2.0, "power": 10.0},
}

NODE_ALIASES = {"North Node", "South Node", "True Node", "Mean Node", "Node", "Rahu", "Ketu"}

SIGNS = [
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
SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}

FALL_SIGNS = {
    "Sun": "Libra",
    "Moon": "Scorpio",
    "Mercury": "Pisces",
    "Venus": "Virgo",
    "Mars": "Cancer",
    "Jupiter": "Capricorn",
    "Saturn": "Aries",
}


def _clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _circular_diff(a: float, b: float) -> float:
    try:
        return abs((((float(a) - float(b)) + 180.0) % 360.0) - 180.0)
    except Exception:
        return 999.0


def _opposite_sign(sign: str) -> Optional[str]:
    idx = SIGN_INDEX.get(sign)
    if idx is None:
        return None
    return SIGNS[(idx + 6) % 12]


def _detriment_signs() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for sign, ruler in TRAD_RULER.items():
        opp = _opposite_sign(sign)
        if not opp:
            continue
        out.setdefault(ruler, []).append(opp)
    return out


DETRIMENT_SIGNS = _detriment_signs()


def _planet_house(planet: Optional[Dict[str, Any]], cusps: List[float]) -> Optional[int]:
    if not planet:
        return None
    if planet.get("house") is not None:
        try:
            return int(planet["house"])
        except Exception:
            pass
    lon = _safe_float(planet.get("longitude"))
    if lon is None:
        return None
    try:
        return _house_from_lon(lon, cusps)
    except Exception:
        return None


def _planet_sign(planet: Optional[Dict[str, Any]]) -> Optional[str]:
    if not planet:
        return None
    if planet.get("sign"):
        return str(planet["sign"])
    lon = _safe_float(planet.get("longitude"))
    if lon is None:
        return None
    try:
        return _sign_from_lon(lon)
    except Exception:
        return None


def _dignity_rank(planet_name: str, sign: Optional[str]) -> int:
    if not sign:
        return 0
    if TRAD_RULER.get(sign) == planet_name:
        return 3
    if HI_EXALTATION.get(sign) == planet_name:
        return 2
    detriments = DETRIMENT_SIGNS.get(planet_name, [])
    if sign in detriments:
        return -3
    if FALL_SIGNS.get(planet_name) == sign:
        return -2
    return 0


def _aspect_hits(
    aspects: List[Dict[str, Any]],
    center: str,
    targets: Iterable[str],
    kinds: Iterable[str],
    applying_only: bool = False,
) -> List[Tuple[str, str]]:
    hits: List[Tuple[str, str]] = []
    targets_set = {t for t in targets}
    kinds_set = {k for k in kinds}
    for row in aspects:
        try:
            p1 = str(row.get("planet1") or row.get("p1") or "")
            p2 = str(row.get("planet2") or row.get("p2") or "")
            if center not in {p1, p2}:
                continue
            other = p2 if p1 == center else p1
            if other not in targets_set:
                continue
            asp = str(row.get("aspect") or "")
            if asp not in kinds_set:
                continue
            if applying_only:
                ph = str(row.get("phase") or row.get("motion") or "").lower()
                if "apply" not in ph and ph != "applying":
                    continue
            hits.append((other, asp))
        except Exception:
            continue
    return hits


def _moon_is_void(election_cd: Dict[str, Any]) -> bool:
    try:
        cons = election_cd.get("considerations")
        if isinstance(cons, dict) and cons.get("moon_void"):
            return True
    except Exception:
        pass
    for key in ("moon_void", "moon_voc", "void_of_course"):
        try:
            if election_cd.get(key):
                return True
        except Exception:
            continue
    state = election_cd.get("moon_state")
    if isinstance(state, dict):
        try:
            if state.get("void_of_course"):
                return True
        except Exception:
            pass
    return False


def _sun_lon(planets: Dict[str, Dict[str, Any]]) -> Optional[float]:
    sun = planets.get("Sun")
    if not sun:
        return None
    lon = _safe_float(sun.get("longitude"))
    if lon is None:
        return None
    try:
        return lon % 360.0
    except Exception:
        return None


def _is_oriental(planet_lon: Optional[float], sun_lon: Optional[float]) -> bool:
    if planet_lon is None or sun_lon is None:
        return False
    diff = (planet_lon - sun_lon) % 360.0
    return 0.0 < diff < 180.0


def _fixed_star_score(point_lon: Optional[float], star_meta: Dict[str, Any]) -> Optional[float]:
    if point_lon is None:
        return None
    try:
        diff = _circular_diff(point_lon % 360.0, float(star_meta["lon"]))
        if diff <= float(star_meta["orb"]):
            return float(star_meta["power"])
    except Exception:
        return None
    return None


def _prohibition_checks(
    election_cd: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    aspects: List[Dict[str, Any]],
    action_type: str,
    include_fixed_stars: bool,
) -> List[str]:
    reasons: List[str] = []
    moon = planets.get("Moon")
    mars = planets.get("Mars")
    asc_sign = _sign_from_lon(cusps[0]) if len(cusps) >= 1 else None
    asc_ruler_name = TRAD_RULER.get(asc_sign) if asc_sign else None
    asc_ruler = planets.get(asc_ruler_name) if asc_ruler_name else None
    seventh_sign = _sign_from_lon(cusps[6]) if len(cusps) >= 7 else None
    seventh_ruler_name = TRAD_RULER.get(seventh_sign) if seventh_sign else None
    seventh_ruler = planets.get(seventh_ruler_name) if seventh_ruler_name else None
    sun_lon = _sun_lon(planets)

    if moon:
        moon_lon = _safe_float(moon.get("longitude"))
        if _moon_is_void(election_cd):
            reasons.append("Moon void-of-course")
        if moon_lon is not None and _circular_diff(moon_lon, ALGOL_DEG) <= 3.0:
            reasons.append("Moon on Algol (≤3°)")
        if _is_via_combusta(moon_lon):
            reasons.append("Moon in Via Combusta")
        moon_sign = _planet_sign(moon)
        if moon_sign in {"Scorpio", "Capricorn"}:
            hard_hits = _aspect_hits(aspects, "Moon", MALEFICS, HARD_ASPECTS, applying_only=True)
            if hard_hits:
                reasons.append("Moon debilitated and applying to malefic")
    if mars:
        if bool(mars.get("retrograde")) and action_type != "defense":
            reasons.append("Mars retrograde (non-defensive action)")
        mars_lon = _safe_float(mars.get("longitude"))
        if sun_lon is not None and mars_lon is not None:
            sep = _circular_diff(mars_lon, sun_lon)
            if sep <= 8.0:
                reasons.append("Mars combust (≤8°)")
            elif sep <= 15.0:
                reasons.append("Mars under beams (≤15°)")
        mars_sign = _planet_sign(mars)
        if mars_sign in {"Cancer", "Libra"}:
            hard_hits = _aspect_hits(aspects, "Mars", MALEFICS, HARD_ASPECTS, applying_only=True)
            if hard_hits:
                reasons.append("Mars in detriment/fall and afflicted")
    if include_fixed_stars:
        asc_lon = cusps[0] % 360.0 if len(cusps) >= 1 else None
        if asc_lon is not None and _circular_diff(asc_lon, ALGOL_DEG) <= 3.0:
            reasons.append("Ascendant on Algol (≤3°)")
    if asc_ruler:
        asc_ruler_house = _planet_house(asc_ruler, cusps)
        if asc_ruler_house in CADENT_HOUSES:
            hard_hits = _aspect_hits(aspects, asc_ruler_name or "", MALEFICS, HARD_ASPECTS, applying_only=True)
            if hard_hits:
                reasons.append("Ascendant ruler cadent and afflicted")
        if asc_ruler_name and seventh_ruler_name:
            hard = _aspect_hits(aspects, asc_ruler_name, {seventh_ruler_name}, HARD_ASPECTS, applying_only=True)
            if hard and _dignity_rank(asc_ruler_name, _planet_sign(asc_ruler)) < _dignity_rank(
                seventh_ruler_name, _planet_sign(seventh_ruler)
            ):
                suffix = " from the 8th house" if asc_ruler_house == 8 else ""
                reasons.append(f"Ascendant ruler applying to stronger 7th ruler{suffix}")
    try:
        nodes: List[float] = []
        nn = planets.get("North Node") or planets.get("Node")
        if nn:
            lon_nn = _safe_float(nn.get("longitude"))
            if lon_nn is not None:
                nodes.append(lon_nn % 360.0)
        sn = planets.get("South Node")
        if sn:
            lon_sn = _safe_float(sn.get("longitude"))
            if lon_sn is not None:
                nodes.append(lon_sn % 360.0)
        if len(nodes) == 1:
            nodes.append((nodes[0] + 180.0) % 360.0)
        if nodes and sun_lon is not None:
            if any(_circular_diff(sun_lon, nl) <= 12.0 for nl in nodes):
                reasons.append("Solar eclipse window (≤12° from node)")
        if nodes and moon:
            moon_lon_mod = _safe_float(moon.get("longitude"))
            if moon_lon_mod is not None and any(_circular_diff(moon_lon_mod % 360.0, nl) <= 12.0 for nl in nodes):
                reasons.append("Lunar eclipse window (≤12° from node)")
    except Exception:
        pass
    if reasons:
        return [f"Prohibition: {r}" for r in reasons]
    return []


def _score_asc_strength(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    aspects: List[Dict[str, Any]],
    action_type: str,
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["asc_strength"]
    tags: List[str] = []
    if len(cusps) < 1:
        return 0.0, tags
    asc_sign = _sign_from_lon(cusps[0])
    value = 0.0
    if asc_sign in {"Aries", "Leo", "Capricorn", "Scorpio"}:
        value += 25.0
        tags.append(f"Asc in {asc_sign} favours initiative")
    elif asc_sign in {"Cancer", "Libra", "Pisces"}:
        value -= 15.0
        tags.append(f"Asc in {asc_sign} softens posture")
    ruler_name = TRAD_RULER.get(asc_sign)
    ruler = planets.get(ruler_name) if ruler_name else None
    if ruler:
        ruler_sign = _planet_sign(ruler)
        rank = _dignity_rank(ruler_name or "", ruler_sign)
        value += rank * 5.0
        if rank > 0:
            tags.append(f"Asc ruler dignified in {ruler_sign}")
        elif rank < 0:
            tags.append(f"Asc ruler debilitated in {ruler_sign}")
        ruler_house = _planet_house(ruler, cusps)
        if ruler_house in {1, 10}:
            value += 20.0
            tags.append(f"Asc ruler angular (house {ruler_house})")
        elif ruler_house == 11:
            value += 10.0
            tags.append("Asc ruler in 11th (supports allies)")
        elif ruler_house in {7}:
            value -= 10.0
            tags.append("Asc ruler in 7th (gives leverage away)")
        elif ruler_house == 8:
            value -= 50.0
            tags.append("Asc ruler in 8th (danger)")
        elif ruler_house in {12}:
            value -= 20.0
            tags.append("Asc ruler in 12th (hidden risks)")
        elif ruler_house in {6}:
            value -= 15.0
            tags.append("Asc ruler in 6th (attrition)")
        soft_hits = _aspect_hits(aspects, ruler_name or "", BENEFICS, SOFT_ASPECTS)
        if soft_hits:
            value += 15.0
            tags.append(f"Asc ruler supported by {soft_hits[0][0]}")
        hard_hits = _aspect_hits(aspects, ruler_name or "", MALEFICS, HARD_ASPECTS, applying_only=True)
        if hard_hits:
            value -= 20.0
            tags.append(f"Asc ruler pressured by {hard_hits[0][0]}")
        if bool(ruler.get("retrograde")):
            value -= 15.0
            tags.append("Asc ruler retrograde")
        else:
            tags.append("Asc ruler direct")
        speed = ruler.get("speed")
        if speed is not None:
            try:
                spd = float(speed)
                if spd > 1.2:
                    value += 10.0
                    tags.append("Asc ruler swift")
            except Exception:
                pass
    if action_type in {"siege", "defense"} and asc_sign in {"Capricorn", "Taurus"}:
        value += 10.0
        tags.append("Fixed earth Asc supports endurance")
    return _clamp(value, -weight, weight), tags


def _score_mars_strength(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    aspects: List[Dict[str, Any]],
    action_type: str,
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["mars_strength"]
    tags: List[str] = []
    mars = planets.get("Mars")
    if not mars:
        return 0.0, tags
    value = 0.0
    mars_sign = _planet_sign(mars)
    if mars_sign in {"Aries", "Scorpio"}:
        value += 40.0
        tags.append("Mars in domicile")
    elif mars_sign == "Capricorn":
        value += 35.0
        tags.append("Mars exalted")
    elif mars_sign in {"Leo", "Sagittarius"}:
        value += 20.0
        tags.append("Mars in fiery triplicity")
    elif mars_sign in {"Taurus", "Libra"}:
        value -= 40.0
        tags.append("Mars in detriment")
    elif mars_sign == "Cancer":
        value -= 35.0
        tags.append("Mars in fall")
    mars_house = _planet_house(mars, cusps)
    if mars_house == 10:
        value += 30.0
        tags.append("Mars angular in 10th")
    elif mars_house == 1:
        value += 25.0
        tags.append("Mars on Ascendant")
    elif mars_house == 11:
        value += 15.0
        tags.append("Mars in 11th (rallying allies)")
    elif mars_house == 7:
        value -= 10.0
        tags.append("Mars in 7th strengthens opponent")
    elif mars_house == 8:
        value -= 40.0
        tags.append("Mars in 8th risks losses")
    elif mars_house == 12:
        value -= 25.0
        tags.append("Mars in 12th (hidden dangers)")
    if not bool(mars.get("retrograde")):
        value += 15.0
        tags.append("Mars direct")
    speed = mars.get("speed")
    if speed is not None:
        try:
            spd = float(speed)
            if spd > 0.6:
                value += 10.0
                tags.append("Mars swift")
        except Exception:
            pass
    jupiter_hits = _aspect_hits(aspects, "Mars", {"Jupiter"}, {"Trine", "Sextile"})
    if jupiter_hits:
        value += 25.0
        tags.append("Mars in harmony with Jupiter")
    sun_hits = _aspect_hits(aspects, "Mars", {"Sun"}, {"Trine"})
    if sun_hits:
        value += 20.0
        tags.append("Mars trine Sun")
    saturn_hits = _aspect_hits(aspects, "Mars", {"Saturn"}, {"Square", "Opposition"})
    if saturn_hits:
        value -= 25.0
        tags.append("Mars afflicted by Saturn")
    sun_lon = _sun_lon(planets)
    mars_lon_raw = _safe_float(mars.get("longitude"))
    mars_lon = mars_lon_raw % 360.0 if mars_lon_raw is not None else None
    if sun_lon is not None and mars_lon is not None:
        sep = _circular_diff(mars_lon, sun_lon)
        if sep <= 8.0:
            value -= 30.0
            tags.append("Mars combust")
        elif sep <= 15.0:
            value -= 15.0
            tags.append("Mars under beams")
    if action_type in {"attack", "battle", "siege"}:
        if _is_oriental(mars_lon, sun_lon):
            value += 10.0
            tags.append("Mars oriental supports offensive")
    elif action_type in {"defense", "retreat"}:
        if not _is_oriental(mars_lon, sun_lon):
            value += 10.0
            tags.append("Mars occidental supports defense")
    return _clamp(value, -weight, weight), tags


def _score_mc_strength(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    aspects: List[Dict[str, Any]],
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["mc_strength"]
    tags: List[str] = []
    if len(cusps) < 10:
        return 0.0, tags
    mc_sign = _sign_from_lon(cusps[9])
    value = 0.0
    if mc_sign in {"Leo", "Aries", "Capricorn"}:
        value += 20.0
        tags.append(f"MC in {mc_sign} empowers visibility")
    mc_ruler_name = TRAD_RULER.get(mc_sign)
    mc_ruler = planets.get(mc_ruler_name) if mc_ruler_name else None
    if mc_ruler:
        mc_rank = _dignity_rank(mc_ruler_name or "", _planet_sign(mc_ruler))
        value += mc_rank * 4.0
        if mc_rank > 0:
            tags.append(f"MC ruler dignified")
        elif mc_rank < 0:
            tags.append(f"MC ruler weakened")
        mc_house = _planet_house(mc_ruler, cusps)
        if mc_house in ANGULAR_HOUSES:
            value += 20.0
            tags.append("MC ruler angular")
        elif mc_house in {6, 8, 12}:
            value -= 15.0
            tags.append("MC ruler in cadent/malefic house")
        asc_soft = _aspect_hits(aspects, mc_ruler_name or "", {"Asc"}, {"Trine", "Sextile"})
        if asc_soft:
            value += 15.0
            tags.append("MC ruler supports Ascendant")
    planets_in_10th = [
        nm for nm, info in planets.items() if _planet_house(info, cusps) == 10 and nm not in {"South Node", "North Node"}
    ]
    for nm in planets_in_10th:
        pname = nm
        pinfo = planets[nm]
        rank = _dignity_rank(pname, _planet_sign(pinfo))
        if pname == "Jupiter":
            value += 20.0
            tags.append("Jupiter in 10th (glory)")
        elif pname == "Sun":
            value += 18.0
            tags.append("Sun in 10th (leadership)")
        elif pname == "Mars":
            if rank > 0:
                value += 15.0
                tags.append("Mars in 10th and dignified")
        elif pname in {"Saturn", "South Node"} and rank < 2:
            value -= 20.0
            tags.append(f"{pname} in 10th depresses outcome")
    return _clamp(value, -weight, weight), tags


def _score_moon_condition(
    election_cd: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    action_type: str,
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["moon_condition"]
    tags: List[str] = []
    moon = planets.get("Moon")
    sun = planets.get("Sun")
    if not moon:
        return 0.0, tags
    value = 0.0
    moon_lon_raw = _safe_float(moon.get("longitude"))
    moon_lon = moon_lon_raw % 360.0 if moon_lon_raw is not None else None
    sun_lon_raw = _safe_float(sun.get("longitude")) if sun else None
    sun_lon = sun_lon_raw % 360.0 if sun_lon_raw is not None else None
    if moon_lon is not None and sun_lon is not None:
        sep = _circular_diff(moon_lon, sun_lon)
        phase_pct = (sep / 180.0) * 100.0
        waxing = _is_waxing(moon_lon, sun_lon)
        if action_type in {"attack", "battle", "siege"}:
            value += (phase_pct / 100.0) * 20.0
            if waxing:
                tags.append("Moon waxing favours offence")
        else:
            value += ((100.0 - phase_pct) / 100.0) * 15.0
            if not waxing:
                tags.append("Moon waning supports consolidation")
    moon_sign = _planet_sign(moon)
    sign_scores = {
        "Aries": 20.0,
        "Leo": 18.0,
        "Sagittarius": 15.0,
        "Capricorn": 15.0,
        "Scorpio": 12.0,
        "Aquarius": 8.0,
        "Gemini": 5.0,
        "Taurus": -5.0,
        "Virgo": -8.0,
        "Libra": -10.0,
        "Cancer": -12.0,
        "Pisces": -15.0,
    }
    value += sign_scores.get(moon_sign, 0.0)
    if moon_sign:
        tags.append(f"Moon in {moon_sign}")
    moon_house = _planet_house(moon, cusps)
    house_scores = {1: 15.0, 10: 18.0, 11: 12.0, 9: 8.0, 6: -20.0, 8: -30.0, 12: -25.0}
    if moon_house in house_scores:
        value += house_scores[moon_house]
        if moon_house in {6, 8, 12}:
            tags.append(f"Moon in {moon_house}th (weakens morale)")
        else:
            tags.append(f"Moon in {moon_house}th (supports momentum)")
    next_aspect = election_cd.get("moon_next_aspect")
    if isinstance(next_aspect, dict):
        pn = str(next_aspect.get("planet") or "")
        asp = str(next_aspect.get("aspect") or "")
        ph = str(next_aspect.get("phase") or "").lower()
        if pn in {"Jupiter", "Venus"} and asp in {"Trine", "Sextile", "Conjunction"}:
            value += 20.0
            tags.append(f"Moon applying {asp} to {pn}")
        elif pn in {"Saturn", "Mars"} and asp in {"Square", "Opposition", "Conjunction"} and ("apply" in ph or ph == "applying"):
            value -= 25.0
            tags.append(f"Moon applying {asp} to {pn}")
        elif pn == "Sun" and asp == "Trine":
            value += 15.0
            tags.append("Moon applying trine to Sun")
    speed = moon.get("speed")
    if speed is not None:
        try:
            spd = abs(float(speed))
            if spd > 13.0:
                value += 8.0
                tags.append("Moon swift")
        except Exception:
            pass
    return _clamp(value, -weight, weight), tags


def _score_jupiter_benefit(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    aspects: List[Dict[str, Any]],
    asc_ruler_name: Optional[str],
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["jupiter_benefit"]
    tags: List[str] = []
    jupiter = planets.get("Jupiter")
    if not jupiter:
        return 0.0, tags
    value = 0.0
    j_house = _planet_house(jupiter, cusps)
    if j_house in {1, 10, 11}:
        value += 20.0
        tags.append(f"Jupiter in {j_house}th house")
    elif j_house in {6, 8, 12}:
        value -= 10.0
        tags.append("Jupiter in cadent/malefic house")
    rank = _dignity_rank("Jupiter", _planet_sign(jupiter))
    value += rank * 4.0
    if rank > 0:
        tags.append("Jupiter dignified")
    elif rank < 0:
        tags.append("Jupiter debilitated")
    if asc_ruler_name:
        soft = _aspect_hits(aspects, "Jupiter", {asc_ruler_name}, {"Trine", "Sextile"})
        if soft:
            value += 15.0
            tags.append("Jupiter supporting Asc ruler")
    mj = _aspect_hits(aspects, "Jupiter", {"Mars"}, {"Trine", "Sextile"})
    if mj:
        value += 15.0
        tags.append("Jupiter supporting Mars")
    if bool(jupiter.get("retrograde")):
        value -= 10.0
        tags.append("Jupiter retrograde")
    return _clamp(value, -weight, weight), tags


def _score_seventh_weakness(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    aspects: List[Dict[str, Any]],
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["seventh_weakness"]
    tags: List[str] = []
    if len(cusps) < 7:
        return 0.0, tags
    seventh_sign = _sign_from_lon(cusps[6])
    ruler_name = TRAD_RULER.get(seventh_sign)
    ruler = planets.get(ruler_name) if ruler_name else None
    value = 0.0
    if ruler:
        rank = _dignity_rank(ruler_name or "", _planet_sign(ruler))
        value += (5 - rank) * 5.0
        if rank <= 0:
            tags.append("7th ruler not dignified (favourable)")
        else:
            tags.append("7th ruler fortified (caution)")
        house = _planet_house(ruler, cusps)
        if house in CADENT_HOUSES:
            value += 20.0
            tags.append("7th ruler cadent")
        elif house in {1, 10}:
            value -= 15.0
            tags.append("7th ruler angular")
        if bool(ruler.get("retrograde")):
            value += 15.0
            tags.append("7th ruler retrograde")
        hard_hits = _aspect_hits(aspects, ruler_name or "", MALEFICS, HARD_ASPECTS, applying_only=True)
        if hard_hits:
            value += 15.0
            tags.append("7th ruler afflicted by malefic")
    planets_in_7th = [
        nm
        for nm, info in planets.items()
        if _planet_house(info, cusps) == 7 and nm in {"Mars", "Saturn", "South Node"}
    ]
    if planets_in_7th:
        value += 10.0 * len(planets_in_7th)
        tags.append("Malefic influence in 7th weakens enemy")
    return _clamp(value, -weight, weight), tags


def _score_eighth_safety(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    aspects: List[Dict[str, Any]],
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["eighth_safety"]
    tags: List[str] = []
    if len(cusps) < 8:
        return 0.0, tags
    eighth_planets = [
        nm
        for nm, info in planets.items()
        if _planet_house(info, cusps) == 8 and nm not in {"North Node", "South Node"}
    ]
    value = 0.0
    if eighth_planets:
        value -= len(eighth_planets) * 20.0
        tags.append("Planets occupying 8th house")
    eighth_sign = _sign_from_lon(cusps[7])
    r8_name = TRAD_RULER.get(eighth_sign)
    r8 = planets.get(r8_name) if r8_name else None
    if r8:
        house = _planet_house(r8, cusps)
        if house in CADENT_HOUSES:
            value += 15.0
            tags.append("8th ruler cadent (safer)")
        elif house in {1, 10}:
            value -= 20.0
            tags.append("8th ruler angular (exposure)")
        if not _aspect_hits(aspects, r8_name or "", {"Asc", TRAD_RULER.get(_sign_from_lon(cusps[0])) or ""}, SOFT_ASPECTS):
            value += 20.0
            tags.append("8th ruler not linking to Asc")
        malefic_aspect = _aspect_hits(aspects, r8_name or "", MALEFICS, HARD_ASPECTS, applying_only=True)
        if not malefic_aspect:
            value += 15.0
            tags.append("8th cusp free of malefic pressure")
    return _clamp(value, -weight, weight), tags


def _score_angle_fortification(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["angle_fortification"]
    tags: List[str] = []
    value = 0.0
    for house in ANGULAR_HOUSES:
        for nm, info in planets.items():
            if nm in {"South Node", "North Node"}:
                continue
            if _planet_house(info, cusps) != house:
                continue
            if nm in {"Jupiter", "Venus"}:
                value += 8.0
                tags.append(f"{nm} in {house}th angle")
            elif nm == "Sun":
                value += 6.0
                tags.append("Sun angular")
            elif nm == "Mars":
                rank = _dignity_rank("Mars", _planet_sign(info))
                if rank > 0 and house in {1, 10}:
                    value += 6.0
                    tags.append("Mars fortified on angle")
            elif nm == "Saturn" and house in {1, 10} and _dignity_rank("Saturn", _planet_sign(info)) < 2:
                value -= 10.0
                tags.append("Saturn weak on vital angle")
    return _clamp(value, -weight, weight), tags


def _score_traditional_timing(
    options: Optional[Dict[str, Any]],
    action_type: str,
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["traditional_timing"]
    if not options or not options.get("include_traditional_timing"):
        return 0.0, []
    tags: List[str] = []
    value = 0.0
    action = action_type or "battle"

    def _norm(ruler: Any) -> str:
        return str(ruler or "").strip().title()

    day_ruler = _norm(options.get("day_ruler"))
    hour_ruler = _norm(options.get("hour_ruler"))

    def _ruler_bonus(ruler: str) -> float:
        if not ruler:
            return 0.0
        if action in {"attack", "battle", "siege"}:
            if ruler == "Mars":
                return 10.0
            if ruler == "Sun":
                return 6.0
            if ruler == "Jupiter":
                return 5.0
            if ruler == "Saturn" and action == "siege":
                return 4.0
            if ruler in {"Venus", "Moon"}:
                return -6.0
            if ruler == "Mercury":
                return -3.0
        else:  # defense / retreat
            if ruler == "Saturn":
                return 8.0
            if ruler == "Jupiter":
                return 5.0
            if ruler == "Mars":
                return 4.0
            if ruler == "Mercury" and action == "retreat":
                return 4.0
            if ruler == "Sun":
                return 2.0
            if ruler in {"Venus", "Moon"}:
                return -4.0
        return 0.0

    day_bonus = _ruler_bonus(day_ruler)
    if day_bonus:
        value += day_bonus
        if day_bonus > 0:
            tags.append(f"Planetary day ruler {day_ruler} supports timing")
        else:
            tags.append(f"Planetary day ruler {day_ruler} weakens timing")
    hour_bonus = _ruler_bonus(hour_ruler)
    if hour_bonus:
        value += hour_bonus
        if hour_bonus > 0:
            tags.append(f"Planetary hour ruler {hour_ruler} supports timing")
        else:
            tags.append(f"Planetary hour ruler {hour_ruler} weakens timing")
    if day_bonus > 0 and hour_bonus > 0 and day_ruler and hour_ruler and day_ruler == hour_ruler:
        value += 2.0
        tags.append("Aligned day/hour ruler reinforces strategy")

    return _clamp(value, -weight, weight), tags


def _score_fixed_stars_component(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    include_fixed_stars: bool,
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["fixed_stars"]
    if not include_fixed_stars:
        return 0.0, []
    tags: List[str] = []
    value = 0.0
    critical_points: List[Tuple[str, Optional[float], bool]] = []
    if len(cusps) >= 1:
        critical_points.append(("Asc", cusps[0] % 360.0, True))
    if len(cusps) >= 10:
        critical_points.append(("MC", cusps[9] % 360.0, False))
    for name in ("Mars", "Sun", "Moon", "Jupiter"):
        info = planets.get(name)
        if info:
            lon = _safe_float(info.get("longitude"))
            if lon is not None:
                critical_points.append((name, lon % 360.0, name == "Moon"))
    for label, lon, is_primary in critical_points:
        for star, meta in FIXED_STARS.items():
            score = _fixed_star_score(lon, meta)
            if score is None:
                continue
            if meta["nature"] == "malefic" and is_primary:
                return -weight, [f"Fixed star {star} on {label} (malefic)"]
            bonus = score * (1.5 if is_primary else 1.0)
            value += bonus
            tags.append(f"{star} activating {label}")
    return _clamp(value, -weight, weight), tags


def _score_natal_synastry(
    election_cd: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    options: Optional[Dict[str, Any]],
) -> Tuple[float, List[str]]:
    weight = WEIGHTS["natal_synastry"]
    if not options or not isinstance(options.get("natal_cd"), dict):
        return 0.0, []
    natal_cd = options.get("natal_cd", {})
    natal_planets = _collect_planets(natal_cd)
    natal_cusps = _house_cusps(natal_cd)
    if not natal_planets or not natal_cusps:
        return 0.0, []
    tags: List[str] = []
    value = 0.0
    asc_ruler_name = TRAD_RULER.get(_sign_from_lon(cusps[0])) if len(cusps) >= 1 else None
    asc_ruler = planets.get(asc_ruler_name) if asc_ruler_name else None
    election_mars = planets.get("Mars")
    election_moon = planets.get("Moon")
    election_mc_lon = cusps[9] % 360.0 if len(cusps) >= 10 else None
    election_asc_lon = cusps[0] % 360.0 if len(cusps) >= 1 else None
    natal_mars = natal_planets.get("Mars")
    natal_mc_lon = natal_cusps[9] % 360.0 if len(natal_cusps) >= 10 else None
    natal_asc_lon = natal_cusps[0] % 360.0 if len(natal_cusps) >= 1 else None

    def _aspect_type(a: Optional[float], b: Optional[float], orb: float = 4.0) -> Optional[str]:
        if a is None or b is None:
            return None
        diff = _circular_diff(a, b)
        for angle, name in ((0.0, "Conjunction"), (60.0, "Sextile"), (90.0, "Square"), (120.0, "Trine"), (180.0, "Opposition")):
            if abs(diff - angle) <= orb:
                return name
        return None

    # Asc ruler to natal planets
    if asc_ruler:
        asc_lon_raw = _safe_float(asc_ruler.get("longitude"))
        if asc_lon_raw is not None:
            asc_lon = asc_lon_raw % 360.0
            for np_name in ("Mars", "Jupiter", "Sun", "Saturn"):
                nplanet = natal_planets.get(np_name)
                if not nplanet:
                    continue
                nlon = _safe_float(nplanet.get("longitude"))
                if nlon is None:
                    continue
                asp = _aspect_type(asc_lon, nlon % 360.0)
                if asp in {"Trine", "Sextile"}:
                    mult = 15.0 if np_name in {"Mars", "Jupiter"} else 10.0
                    value += mult
                    tags.append(f"Asc ruler {asp.lower()} natal {np_name}")
                elif asp in {"Square", "Opposition"}:
                    value -= 10.0
                    tags.append(f"Asc ruler {asp.lower()} natal {np_name}")
    # Mars synastry
    if election_mars and natal_mars:
        em_lon = _safe_float(election_mars.get("longitude"))
        nm_lon = _safe_float(natal_mars.get("longitude"))
        if em_lon is not None and nm_lon is not None:
            asp = _aspect_type(em_lon % 360.0, nm_lon % 360.0)
            if asp == "Trine":
                value += 40.0
                tags.append("Mars trine natal Mars")
            elif asp == "Sextile":
                value += 25.0
                tags.append("Mars sextile natal Mars")
            elif asp in {"Square", "Opposition"}:
                value -= 30.0
                tags.append("Mars hard to natal Mars")
    # Moon to natal significators
    if election_moon:
        moon_lon_raw = _safe_float(election_moon.get("longitude"))
        if moon_lon_raw is not None:
            moon_lon = moon_lon_raw % 360.0
            targets = (
                "Mars",
                asc_ruler_name or "",
                TRAD_RULER.get(_sign_from_lon(natal_cusps[9]) if len(natal_cusps) >= 10 else "") or "",
            )
            for np_name in targets:
                if not np_name:
                    continue
                nplanet = natal_planets.get(np_name)
                if not nplanet:
                    continue
                nlon = _safe_float(nplanet.get("longitude"))
                if nlon is None:
                    continue
                asp = _aspect_type(moon_lon, nlon % 360.0)
                if asp in {"Trine", "Sextile"}:
                    value += 20.0
                    tags.append(f"Moon {asp.lower()} natal {np_name}")
                elif asp in {"Square", "Opposition"}:
                    value -= 15.0
                    tags.append(f"Moon {asp.lower()} natal {np_name}")
            natal_moon_house = _house_from_lon(moon_lon, natal_cusps)
            if natal_moon_house in {6, 8, 12}:
                value -= 30.0
                tags.append("Election Moon in natal 6/8/12")
    # Election planets in natal houses
    for pname in ("Mars", "Jupiter", "Sun"):
        pinfo = planets.get(pname)
        if not pinfo:
            continue
        plon = _safe_float(pinfo.get("longitude"))
        if plon is None:
            continue
        natal_house = _house_from_lon(plon % 360.0, natal_cusps)
        if pname == "Mars":
            if natal_house in {1, 10, 11}:
                value += 20.0
                tags.append("Election Mars energises natal angular house")
            elif natal_house in {6, 8, 12}:
                value -= 25.0
                tags.append("Election Mars in natal cadent/malefic house")
        elif pname == "Jupiter" and natal_house in {1, 10, 11}:
            value += 15.0
            tags.append("Election Jupiter boosts natal angles")
    # Asc alignment
    if election_asc_lon is not None and natal_asc_lon is not None:
        if _circular_diff(election_asc_lon, natal_asc_lon) <= 3.0:
            value += 25.0
            tags.append("Election Asc near natal Asc")
    # MC alignment
    if election_mc_lon is not None and natal_mc_lon is not None:
        asp = _aspect_type(election_mc_lon, natal_mc_lon)
        if asp in {"Trine", "Sextile"}:
            value += 15.0
            tags.append("Election MC harmonises natal MC")
    # Solar/Lunar return proximity
    current_timestamp = options.get("current_timestamp")
    sr_windows = options.get("sr_windows") or []
    if current_timestamp and sr_windows:
        for (start, end) in sr_windows:
            try:
                if start <= current_timestamp <= end:
                    value += 12.0
                    tags.append("Within solar return window")
                    break
            except Exception:
                continue
    lr_list = options.get("lr_list") or []
    if current_timestamp and lr_list:
        try:
            deltas = [
                abs((current_timestamp - lr).total_seconds())
                for lr in lr_list
                if hasattr(lr, "total_seconds")
            ]
            if deltas:
                near = min(deltas)
                if near <= 12 * 3600:
                    value += 10.0
                    tags.append("Near lunar return (<12h)")
                elif near <= 48 * 3600:
                    value += 5.0
                    tags.append("Within 48h of lunar return")
        except Exception:
            pass
    hits = options.get("natal_hits")
    if isinstance(hits, list):
        positive = 0.0
        caution = 0.0
        for hit in hits[:15]:
            try:
                trans = str(hit.get("transiting") or "")
                aspect = str(hit.get("aspect") or "")
                target = str(hit.get("target_label") or hit.get("natal") or "").lower()
                if trans in {"Jupiter", "Sun", "Mars"} and aspect in {"Conjunction", "Trine", "Sextile"} and any(
                    tok in target for tok in ("c1", "c10", "mc", "asc", "mars")
                ):
                    positive += 6.0
                if trans in {"Saturn", "Mars"} and aspect in {"Square", "Opposition"} and any(
                    tok in target for tok in ("c1", "c10", "c4", "c7", "asc", "mc")
                ):
                    caution += 6.0
            except Exception:
                continue
        if positive:
            value += positive
            tags.append("Natal directions favourable")
        if caution:
            value -= caution
            tags.append("Natal directions warn of friction")
    # Natal suitability baseline
    natal_asc_ruler_name = TRAD_RULER.get(_sign_from_lon(natal_cusps[0]) if len(natal_cusps) >= 1 else "")
    natal_asc_ruler = natal_planets.get(natal_asc_ruler_name)
    if natal_asc_ruler and natal_asc_ruler.get("house") is not None:
        h = int(natal_asc_ruler["house"])
        if h in {6, 8, 12}:
            value -= 25.0
            tags.append("Natal Asc ruler cadent")
    natal_mars_sign = _planet_sign(natal_mars)
    if natal_mars_sign in {"Aries", "Scorpio", "Capricorn"}:
        value += 15.0
        tags.append("Natal Mars strong")
    elif natal_mars_sign in {"Cancer", "Taurus", "Libra"}:
        value -= 15.0
        tags.append("Natal Mars weak")

    return _clamp(value, -weight, weight), tags


def score_battle_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    planets = _collect_planets(election_cd)
    cusps = _house_cusps(election_cd)
    aspects = _get_aspects_list(election_cd) or []
    opts = options or {}
    if natal_hits is not None:
        opts = dict(opts)
        opts.setdefault("natal_hits", natal_hits)
    action_raw = str(opts.get("action_type") or opts.get("battle_action") or "battle").strip().lower()
    action_type = action_raw if action_raw in ACTION_TYPES else "battle"
    include_fixed_stars = bool(opts.get("include_fixed_stars"))

    prohibitions = _prohibition_checks(election_cd, planets, cusps, aspects, action_type, include_fixed_stars)
    if prohibitions:
        return Score(value=-9999.0, tags=prohibitions)

    tags: List[str] = []
    total = 0.0

    asc_score, asc_tags = _score_asc_strength(planets, cusps, aspects, action_type)
    total += asc_score
    tags.extend(asc_tags)

    mars_score, mars_tags = _score_mars_strength(planets, cusps, aspects, action_type)
    total += mars_score
    tags.extend(mars_tags)

    mc_score, mc_tags = _score_mc_strength(planets, cusps, aspects)
    total += mc_score
    tags.extend(mc_tags)

    moon_score, moon_tags = _score_moon_condition(election_cd, planets, cusps, action_type)
    total += moon_score
    tags.extend(moon_tags)

    asc_ruler_name = TRAD_RULER.get(_sign_from_lon(cusps[0])) if len(cusps) >= 1 else None
    jup_score, jup_tags = _score_jupiter_benefit(planets, cusps, aspects, asc_ruler_name)
    total += jup_score
    tags.extend(jup_tags)

    seventh_score, seventh_tags = _score_seventh_weakness(planets, cusps, aspects)
    total += seventh_score
    tags.extend(seventh_tags)

    eighth_score, eighth_tags = _score_eighth_safety(planets, cusps, aspects)
    total += eighth_score
    tags.extend(eighth_tags)

    angle_score, angle_tags = _score_angle_fortification(planets, cusps)
    total += angle_score
    tags.extend(angle_tags)

    timing_score, timing_tags = _score_traditional_timing(opts, action_type)
    total += timing_score
    tags.extend(timing_tags)

    star_score, star_tags = _score_fixed_stars_component(planets, cusps, include_fixed_stars)
    total += star_score
    tags.extend(star_tags)

    natal_score, natal_tags = _score_natal_synastry(election_cd, planets, cusps, opts)
    total += natal_score
    tags.extend(natal_tags)

    return Score(value=round(total, 2), tags=tags)


__all__ = ["score_battle_election"]
