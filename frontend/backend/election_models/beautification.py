from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .common import (
    Score,
    BENEFICS,
    MALEFICS,
    ANGULAR_HOUSES,
    SUCCEDENT_HOUSES,
    CADENT_HOUSES,
    TRAD_RULER,
    _collect_planets,
    _house_cusps,
    _house_from_lon,
    _get_aspects_list,
    _sign_from_lon,
    _safe_float,
    _ang_sep,
    _is_waxing,
)

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

BEST_ASC_SIGNS = {"Libra", "Taurus", "Pisces"}
ASC_CAUTION_SIGNS = {"Scorpio", "Aries", "Capricorn"}

BODY_PART_SIGN_MAP: Dict[str, List[str]] = {
    "head": ["Aries"],
    "face": ["Aries", "Libra"],
    "brain": ["Aries"],
    "eyes": ["Aries"],
    "cheek": ["Libra"],
    "cheeks": ["Libra"],
    "lips": ["Taurus"],
    "mouth": ["Taurus"],
    "jaw": ["Taurus", "Capricorn"],
    "chin": ["Capricorn"],
    "skin": ["Libra", "Capricorn"],
    "neck": ["Taurus"],
    "throat": ["Taurus"],
    "breast": ["Cancer"],
    "breasts": ["Cancer"],
    "stomach": ["Cancer"],
    "heart": ["Leo"],
    "spine": ["Leo"],
    "upper back": ["Leo"],
    "arms": ["Gemini"],
    "hands": ["Gemini"],
    "lungs": ["Gemini"],
    "hips": ["Sagittarius"],
    "thighs": ["Sagittarius"],
    "liver": ["Sagittarius"],
    "knees": ["Capricorn"],
    "teeth": ["Capricorn"],
    "bones": ["Capricorn"],
    "feet": ["Pisces"],
    "ankles": ["Aquarius"],
    "circulation": ["Aquarius"],
    "reproductive": ["Scorpio"],
    "genitals": ["Scorpio"],
    "tattoo": ["Pisces", "Scorpio"],
}

PROCEDURE_PHASE_PREF = {
    "augmentation": "waxing",
    "filler": "waxing",
    "fillers": "waxing",
    "skin": "waxing",
    "laser": "waning",
    "botox": "waning",
    "reduction": "waning",
    "surgery": "waning",
    "surgical": "waning",
    "tattoo_removal": "waning",
    "removal": "waning",
}


def _opposite_sign(sign: Optional[str]) -> Optional[str]:
    if not sign:
        return None
    idx = SIGN_INDEX.get(sign)
    if idx is None:
        return None
    return SIGNS[(idx + 6) % 12]


def _normalize_sign(name: str) -> Optional[str]:
    if not name:
        return None
    text = name.strip().title()
    return text if text in SIGN_INDEX else None


def _collect_body_signs(options: Dict[str, Any]) -> Set[str]:
    signs: Set[str] = set()
    raw_signs: Iterable[Any] = ()
    if "body_sign" in options:
        raw_signs = [options["body_sign"]]
    elif "body_signs" in options:
        raw_signs = options["body_signs"]
    elif "target_sign" in options:
        raw_signs = [options["target_sign"]]
    elif "target_signs" in options:
        raw_signs = options["target_signs"]
    else:
        raw_signs = []
    for value in raw_signs:
        if isinstance(value, str):
            s = _normalize_sign(value)
            if s:
                signs.add(s)
    body_targets: List[str] = []
    for key in ("target", "targets", "body_part", "body_parts", "focus"):
        val = options.get(key)
        if isinstance(val, str):
            body_targets.extend([x.strip().lower() for x in val.split(",") if x.strip()])
        elif isinstance(val, (list, tuple, set)):
            for item in val:
                if isinstance(item, str):
                    body_targets.append(item.strip().lower())
    for target in body_targets:
        for keyword, mapped in BODY_PART_SIGN_MAP.items():
            if keyword in target:
                signs.update(mapped)
    return signs


def _moon_forbidden_signs(body_signs: Iterable[str]) -> Set[str]:
    forbidden: Set[str] = set()
    for s in body_signs:
        forbidden.add(s)
        opp = _opposite_sign(s)
        if opp:
            forbidden.add(opp)
    return forbidden


def _moon_is_voc(election_cd: Dict[str, Any]) -> bool:
    try:
        cons = election_cd.get("considerations")
        if isinstance(cons, dict) and cons.get("moon_void"):
            return True
    except Exception:
        pass
    for key in ("moon_void", "moon_voc", "void_of_course"):
        if election_cd.get(key):
            return True
    state = election_cd.get("moon_state")
    if isinstance(state, dict):
        return bool(state.get("void_of_course"))
    return False


def _eclipse_within(node_lons: List[float], lon: Optional[float], orb: float) -> bool:
    if lon is None:
        return False
    return any(_ang_sep(lon % 360.0, nl) <= orb for nl in node_lons)


def _extract_node_longitudes(planets: Dict[str, Dict[str, Any]]) -> List[float]:
    out: List[float] = []
    for label in ("North Node", "Node", "True Node"):
        node = planets.get(label)
        if node:
            lon = _safe_float(node.get("longitude"))
            if lon is not None:
                out.append(lon % 360.0)
                break
    for label in ("South Node", "Descending Node", "Ketu"):
        node = planets.get(label)
        if node:
            lon = _safe_float(node.get("longitude"))
            if lon is not None:
                out.append(lon % 360.0)
                break
    if len(out) == 1:
        out.append((out[0] + 180.0) % 360.0)
    return out


def _procedure_phase(options: Dict[str, Any]) -> Optional[str]:
    raw = ""
    for key in ("procedure_type", "procedure", "mode"):
        val = options.get(key)
        if isinstance(val, str):
            raw = val.strip().lower()
            break
    return PROCEDURE_PHASE_PREF.get(raw)


def _mercury_retrograde(planets: Dict[str, Dict[str, Any]]) -> bool:
    mercury = planets.get("Mercury")
    return bool(mercury and mercury.get("retrograde"))


def _mars_retrograde(planets: Dict[str, Dict[str, Any]]) -> bool:
    mars = planets.get("Mars")
    return bool(mars and mars.get("retrograde"))


def _benefics_in_angles(planets: Dict[str, Dict[str, Any]], cusps: List[float], tags: List[str]) -> float:
    bonus = 0.0
    for name in ("Venus", "Jupiter"):
        info = planets.get(name)
        if not info:
            continue
        lon = _safe_float(info.get("longitude"))
        house = int(info.get("house")) if info.get("house") is not None else _house_from_lon(lon, cusps) if lon is not None else None
        if house in ANGULAR_HOUSES:
            val = 3.5 if name == "Venus" else 2.5
            bonus += val
            tags.append(f"{name} angular (house {house})")
    return bonus


def _natal_bonus(
    election_cd: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    options: Dict[str, Any],
    natal_hits: Optional[List[Dict[str, Any]]],
    tags: List[str],
) -> float:
    natal_cd = options.get("natal_cd")
    if not isinstance(natal_cd, dict):
        return 0.0
    natal_planets = _collect_planets(natal_cd)
    natal_cusps = _house_cusps(natal_cd)
    if not natal_planets or not natal_cusps:
        return 0.0
    bonus = 0.0
    penalty = 0.0
    asc_ruler = None
    root_asc_sign = None
    try:
        root_asc_sign = _sign_from_lon(natal_cusps[0]) if len(natal_cusps) >= 1 else None
        if root_asc_sign:
            asc_ruler = natal_planets.get(TRAD_RULER.get(root_asc_sign, ""))
    except Exception:
        asc_ruler = None
    natal_venus = natal_planets.get("Venus")
    if natal_venus:
        venus_sign = natal_venus.get("sign") or _sign_from_lon(_safe_float(natal_venus.get("longitude")) or 0.0)
        if venus_sign in {"Taurus", "Libra", "Pisces"}:
            bonus += 4.0
            tags.append("Natal Venus dignified (+4)")
        if bool(natal_venus.get("retrograde")):
            penalty += 5.0
            tags.append("Natal Venus retrograde (-5)")
    if asc_ruler:
        if bool(asc_ruler.get("retrograde")):
            penalty += 4.0
            tags.append("Natal Asc ruler retrograde (-4)")
        ar_sign = asc_ruler.get("sign") or _sign_from_lon(_safe_float(asc_ruler.get("longitude")) or 0.0)
        if ar_sign in {"Taurus", "Libra"}:
            bonus += 3.0
            tags.append("Natal Asc ruler beauty-friendly (+3)")
    if natal_hits:
        positive_hits = 0
        negative_hits = 0
        for hit in natal_hits[:25]:
            tr = str(hit.get("transiting") or "")
            asp = str(hit.get("aspect") or "")
            tgt = str(hit.get("target_label") or hit.get("natal") or "")
            tgt_low = tgt.lower()
            if tr in BENEFICS and asp in {"Conjunction", "Trine", "Sextile"} and any(token in tgt_low for token in ("asc", "c1", "venus", "c10", "face")):
                positive_hits += 1
            if tr in MALEFICS and asp in {"Square", "Opposition", "Conjunction"} and any(token in tgt_low for token in ("asc", "venus", "c6", "c8", "c12")):
                negative_hits += 1
        if positive_hits:
            val = min(6.0, positive_hits * 2.0)
            bonus += val
            tags.append(f"Natal hits supportive (+{val:.1f})")
        if negative_hits:
            val = min(8.0, negative_hits * 2.5)
            penalty += val
            tags.append(f"Natal hits caution (-{val:.1f})")
    # Radical conformity: election Asc vs natal houses
    try:
        election_asc = cusps[0] if len(cusps) >= 1 else None
        if election_asc is not None:
            natal_house = _house_from_lon(election_asc, natal_cusps)
            if natal_house in (1, 5, 9, 10, 11):
                bonus += 2.5
                tags.append("Election Asc falls in natal fortunate house (+2.5)")
            elif natal_house in (6, 8, 12):
                penalty += 3.5
                tags.append("Election Asc in natal 6/8/12 (-3.5)")
    except Exception:
        pass
    result = bonus - penalty
    return result


def score_beautification_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Score beautification-focused elections, with optional natal integration."""
    opts = options or {}
    tags: List[str] = []
    total = 50.0  # baseline

    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    aspects_list = _get_aspects_list(election_cd) or []

    body_signs = _collect_body_signs(opts)
    forbidden_signs = _moon_forbidden_signs(body_signs)
    forbidden_signs.update({_normalize_sign(s) for s in opts.get("avoid_signs", []) if isinstance(s, str)})
    forbidden_signs.discard(None)

    procedure_phase = _procedure_phase(opts)

    moon = planets.get("Moon")
    sun = planets.get("Sun")
    moon_lon = _safe_float(moon.get("longitude")) if moon else None
    sun_lon = _safe_float(sun.get("longitude")) if sun else None
    moon_sign = moon.get("sign") if moon else None
    if not moon_sign and moon_lon is not None:
        moon_sign = _sign_from_lon(moon_lon)

    moon_forbidden = bool(moon_sign and moon_sign in forbidden_signs)
    if moon_forbidden:
        total -= 35.0
        tags.append(f"Moon in forbidden sign ({moon_sign})")
    elif moon_sign:
        tags.append(f"Moon in {moon_sign}")

    if procedure_phase and moon_lon is not None and sun_lon is not None:
        waxing = _is_waxing(moon_lon, sun_lon)
        if moon_forbidden:
            total -= 2.0
            tags.append("Moon phase muted by forbidden sign")
        elif procedure_phase == "waxing":
            if waxing:
                total += 6.0
                tags.append("Moon waxing supports growth")
            else:
                total -= 6.0
                tags.append("Moon waning vs growth goal")
        elif procedure_phase == "waning":
            if waxing is False:
                total += 6.0
                tags.append("Moon waning supports reduction")
            elif waxing is True:
                total -= 6.0
                tags.append("Moon waxing against reduction goal")

    if moon and _moon_is_voc(election_cd):
        total -= 18.0
        tags.append("Moon void-of-course (major)")

    if sun_lon is not None and moon_lon is not None:
        sep = _ang_sep(moon_lon, sun_lon)
        if sep <= 15.0:
            total -= 5.0
            tags.append("Moon under beams")

    moon_house = _house_from_lon(moon_lon, cusps) if moon_lon is not None else None
    if moon_house in ANGULAR_HOUSES:
        if moon_forbidden:
            total -= 6.0
            tags.append(f"Moon angular in forbidden sign (house {moon_house})")
        else:
            total += 4.0
            tags.append(f"Moon angular (house {moon_house})")
    elif moon_house in (6, 8, 12):
        total -= 6.0
        tags.append(f"Moon in {moon_house}th (health caution)")

    if moon:
        for aspect in aspects_list:
            try:
                p1 = str(aspect.get("planet1") or aspect.get("p1") or "")
                p2 = str(aspect.get("planet2") or aspect.get("p2") or "")
                asp = str(aspect.get("aspect") or "")
                phase = str(aspect.get("phase") or "").lower()
                if "Moon" not in {p1, p2}:
                    continue
                other = p2 if p1 == "Moon" else p1
                if other in BENEFICS and asp in {"Trine", "Sextile"}:
                    if moon_forbidden:
                        tags.append(f"Moon {asp.lower()} {other} (suppressed by forbidden sign)")
                    else:
                        total += 5.0
                        tags.append(f"Moon {asp.lower()} {other}")
                if other in MALEFICS and asp in {"Square", "Opposition"} and ("apply" in phase or phase == "applying"):
                    total -= 12.0
                    tags.append(f"Moon applying {asp.lower()} {other}")
            except Exception:
                continue

    venus = planets.get("Venus")
    venus_score = 0.0
    if venus:
        v_lon = _safe_float(venus.get("longitude"))
        v_sign = venus.get("sign") or (_sign_from_lon(v_lon) if v_lon is not None else None)
        v_house = int(venus.get("house")) if venus.get("house") is not None else _house_from_lon(v_lon, cusps) if v_lon is not None else None
        if v_sign in {"Taurus", "Libra", "Pisces"}:
            venus_score += 12.0
            tags.append("Venus dignified")
        if v_sign in {"Aries", "Scorpio"}:
            venus_score -= 8.0
            tags.append("Venus debilitated")
        if bool(venus.get("retrograde")):
            venus_score -= 20.0
            tags.append("Venus retrograde (avoid)")
        if v_house in ANGULAR_HOUSES:
            venus_score += 8.0
            tags.append(f"Venus angular (house {v_house})")
        for aspect in aspects_list:
            try:
                p1 = str(aspect.get("planet1") or aspect.get("p1") or "")
                p2 = str(aspect.get("planet2") or aspect.get("p2") or "")
                asp = str(aspect.get("aspect") or "")
                phase = str(aspect.get("phase") or "").lower()
                if "Venus" not in {p1, p2}:
                    continue
                other = p2 if p1 == "Venus" else p1
                if other in BENEFICS and asp in {"Trine", "Sextile"}:
                    venus_score += 6.0
                    tags.append(f"Venus {asp.lower()} {other}")
                if other in MALEFICS and asp in {"Square", "Opposition"} and ("apply" in phase or phase == "applying"):
                    venus_score -= 10.0
                    tags.append(f"Venus applying {asp.lower()} {other}")
            except Exception:
                continue
    total += venus_score

    # Malefic management
    for mal in ("Mars", "Saturn"):
        planet = planets.get(mal)
        if not planet:
            continue
        p_lon = _safe_float(planet.get("longitude"))
        p_sign = planet.get("sign") or (_sign_from_lon(p_lon) if p_lon is not None else None)
        p_house = int(planet.get("house")) if planet.get("house") is not None else _house_from_lon(p_lon, cusps) if p_lon is not None else None
        if p_sign and p_sign in forbidden_signs:
            total -= 8.0
            tags.append(f"{mal} in procedure sign ({p_sign})")
        if p_house in ANGULAR_HOUSES:
            total -= 5.0
            tags.append(f"{mal} angular (house {p_house})")
        if bool(planet.get("retrograde")):
            total -= 4.0
            tags.append(f"{mal} retrograde")

    if _mercury_retrograde(planets):
        total -= 6.0
        tags.append("Mercury retrograde")
    if _mars_retrograde(planets):
        total -= 10.0
        tags.append("Mars retrograde (surgery caution)")

    node_lons = _extract_node_longitudes(planets)
    if node_lons:
        if _eclipse_within(node_lons, sun_lon, 12.0):
            total -= 8.0
            tags.append("Within solar eclipse window")
        if _eclipse_within(node_lons, moon_lon, 12.0):
            total -= 8.0
            tags.append("Within lunar eclipse window")

    asc_sign = _sign_from_lon(cusps[0]) if len(cusps) >= 1 else None
    if asc_sign in BEST_ASC_SIGNS:
        total += 6.0
        tags.append(f"Ascendant in {asc_sign} (favorable)")
    elif asc_sign in ASC_CAUTION_SIGNS:
        total -= 6.0
        tags.append(f"Ascendant in {asc_sign} (caution)")

    total += _benefics_in_angles(planets, cusps, tags)

    # Natal overlay (optional)
    total += _natal_bonus(election_cd, planets, cusps, opts, natal_hits, tags)

    total = max(-100.0, min(100.0, total))
    return Score(value=round(total, 2), tags=tags)


__all__ = ["score_beautification_election"]
