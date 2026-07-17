from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import (
    ANGULAR_HOUSES,
    BENEFICS,
    CADENT_HOUSES,
    CARDINAL_SIGNS,
    FIXED_SIGNS,
    MALEFICS,
    SUCCEDENT_HOUSES,
    Score,
    TRAD_RULER,
    _ang_sep,
    _collect_planets,
    _get_aspects_list,
    _house_cusps,
    _house_from_lon,
    _is_waxing,
    _ordinal,
    _safe_float,
    _sign_from_lon,
)


VENUS_DOMICILES = {"Taurus", "Libra"}
MERCURY_DOMICILES = {"Gemini", "Virgo"}
SATURN_DOMICILES = {"Capricorn", "Aquarius"}
DIURNAL_SIGNS = {"Aries", "Gemini", "Leo", "Libra", "Sagittarius", "Aquarius"}
NOCTURNAL_SIGNS = {"Taurus", "Cancer", "Virgo", "Scorpio", "Capricorn", "Pisces"}
MARRIAGE_TARGET_TOKENS = ("7", "desc", "venus", "jupiter", "asc")

_MARRIAGE_CAUTION_FRAGMENTS = (
    "mobile asc",
    "retrograde",
    "slow",
    "afflicted",
    "hard aspect",
    "malefic",
    "bad house",
    "unfavored",
    "under beams",
    "combust",
    "natal promise weak",
    "natal promise mixed",
    "natal omitted",
    "moon applying to retrograde",
    "avoid moon application",
    "fixed star algol",
    "fixed star antares",
    "fixed star scheat",
)


def _planet_row(planets: Dict[str, Dict[str, Any]], name: Optional[str]) -> Dict[str, Any]:
    row = planets.get(name or "")
    return row if isinstance(row, dict) else {}


def _planet_lon(planets: Dict[str, Dict[str, Any]], name: Optional[str]) -> Optional[float]:
    row = _planet_row(planets, name)
    value = _safe_float(row.get("longitude"))
    return value % 360.0 if value is not None else None


def _planet_sign(planets: Dict[str, Dict[str, Any]], name: Optional[str]) -> Optional[str]:
    lon = _planet_lon(planets, name)
    return _sign_from_lon(lon) if lon is not None else None


def _planet_house(planets: Dict[str, Dict[str, Any]], name: Optional[str], cusps: List[float]) -> Optional[int]:
    row = _planet_row(planets, name)
    if row.get("house") is not None:
        try:
            return int(row.get("house"))
        except Exception:
            pass
    lon = _planet_lon(planets, name)
    if lon is None:
        return None
    return _house_from_lon(lon, cusps)


def _planet_speed_abs(planets: Dict[str, Dict[str, Any]], name: Optional[str]) -> Optional[float]:
    row = _planet_row(planets, name)
    speed = _safe_float(row.get("speed"))
    if speed is None:
        speed = _safe_float(row.get("daily_motion"))
    return abs(speed) if speed is not None else None


def _aspect_list(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    aspects = _get_aspects_list(chart_data)
    return aspects if isinstance(aspects, list) else []


def _aspect_pair(aspects: List[Dict[str, Any]], left: str, right: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for aspect in aspects:
        try:
            p1 = str(aspect.get("planet1") or aspect.get("p1") or "")
            p2 = str(aspect.get("planet2") or aspect.get("p2") or "")
        except Exception:
            continue
        if {p1, p2} == {left, right}:
            rows.append(aspect)
    return rows


def _aspect_name(aspect: Dict[str, Any]) -> str:
    return str(aspect.get("aspect") or "").strip()


def _aspect_phase(aspect: Dict[str, Any]) -> str:
    return str(aspect.get("phase") or "").strip().lower()


def _is_applying(aspect: Dict[str, Any]) -> bool:
    phase = _aspect_phase(aspect)
    return "apply" in phase or phase == "applying"


def _is_separating(aspect: Dict[str, Any]) -> bool:
    phase = _aspect_phase(aspect)
    return "sep" in phase or phase == "separating"


def _is_hard_aspect(name: str) -> bool:
    return name in {"Conjunction", "Square", "Opposition"}


def _is_soft_aspect(name: str) -> bool:
    return name in {"Conjunction", "Trine", "Sextile"}


def _natal_planet_map(natal_cd: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    natal_pl = (natal_cd or {}).get("planets") or {}
    if isinstance(natal_pl, dict):
        return {key: value for key, value in natal_pl.items() if isinstance(value, dict)}
    pl_map: Dict[str, Dict[str, Any]] = {}
    if isinstance(natal_pl, list):
        for row in natal_pl:
            if isinstance(row, dict) and row.get("planet"):
                pl_map[str(row["planet"])] = row
    return pl_map


def _natal_house_of(pl_map: Dict[str, Dict[str, Any]], natal_cusps: List[float], name: str) -> Optional[int]:
    row = pl_map.get(name)
    if not isinstance(row, dict):
        return None
    if row.get("house") is not None:
        try:
            return int(row.get("house"))
        except Exception:
            pass
    lon = _safe_float(row.get("longitude"))
    if lon is None:
        return None
    return _house_from_lon(lon, natal_cusps)


def _moon_is_bright_and_swift(planets: Dict[str, Dict[str, Any]]) -> bool:
    moon_lon = _planet_lon(planets, "Moon")
    sun_lon = _planet_lon(planets, "Sun")
    moon_speed = _planet_speed_abs(planets, "Moon")
    if moon_lon is None or sun_lon is None or moon_speed is None:
        return False
    return bool(_is_waxing(moon_lon, sun_lon)) and moon_speed >= 12.0


def _moon_has_little_light_or_is_slow(planets: Dict[str, Dict[str, Any]]) -> bool:
    moon_lon = _planet_lon(planets, "Moon")
    sun_lon = _planet_lon(planets, "Sun")
    moon_speed = _planet_speed_abs(planets, "Moon")
    waxing = _is_waxing(moon_lon, sun_lon) if moon_lon is not None and sun_lon is not None else None
    if moon_speed is not None and moon_speed < 11.0:
        return True
    return waxing is False


def _has_target_token(text: str, tokens: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in tokens)


def is_marriage_caution_tag(tag: Any) -> bool:
    try:
        text = str(tag or "").strip()
        if not text:
            return False
        lowered = text.lower()
        if any(fragment in lowered for fragment in _MARRIAGE_CAUTION_FRAGMENTS):
            return True
        if lowered.startswith("mars in ") or lowered.startswith("saturn in "):
            return True
        if lowered.startswith("moon afflicted by"):
            return True
        return False
    except Exception:
        return False


def split_marriage_tags(tags: List[str]) -> tuple[List[str], List[str]]:
    pros: List[str] = []
    cautions: List[str] = []
    for tag in list(tags or []):
        if is_marriage_caution_tag(tag):
            cautions.append(tag)
        else:
            pros.append(tag)
    return pros, cautions


def score_marriage_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Score marriage elections using Morin Book 26 core rules with documented fallbacks."""
    score = 0.0
    tags: List[str] = []

    opts = options or {}
    current_timestamp = opts.get("current_timestamp")
    natal_cd = opts.get("natal_cd") if isinstance(opts.get("natal_cd"), dict) else None
    sr_windows = list(opts.get("sr_windows") or [])
    lr_list = list(opts.get("lr_list") or [])
    hits = list(natal_hits or opts.get("natal_hits") or [])

    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    aspects = _aspect_list(election_cd)

    asc_sign = _sign_from_lon(float(cusps[0])) if len(cusps) >= 1 else None
    dsc_sign = _sign_from_lon(float(cusps[6])) if len(cusps) >= 7 else None
    asc_ruler = TRAD_RULER.get(asc_sign) if asc_sign else None
    seventh_ruler = TRAD_RULER.get(dsc_sign) if dsc_sign else None

    if not natal_cd:
        score -= 0.5
        tags.append("Natal omitted - natal-aware checks unavailable")

    if asc_sign in FIXED_SIGNS:
        score += 2.0
        tags.append(f"Fixed Asc ({asc_sign})")
    elif asc_sign in CARDINAL_SIGNS:
        score -= 1.5
        tags.append(f"Mobile Asc ({asc_sign}) for lasting matter")
    if dsc_sign == "Taurus":
        score += 2.0
        tags.append("Preferred fixed 7th (Taurus)")
    elif dsc_sign == "Leo":
        score += 1.0
        tags.append("Fixed 7th (Leo)")

    sun_house = _planet_house(planets, "Sun", cusps)
    is_day = isinstance(sun_house, int) and 7 <= sun_house <= 12
    moon_sign = _planet_sign(planets, "Moon")
    sun_sign = _planet_sign(planets, "Sun")
    if asc_sign:
        if is_day and asc_sign in DIURNAL_SIGNS:
            score += 0.4
            tags.append("Asc sign matches day sect")
        elif (not is_day) and asc_sign in NOCTURNAL_SIGNS:
            score += 0.4
            tags.append("Asc sign matches night sect")
    if is_day and sun_sign in DIURNAL_SIGNS:
        score += 0.3
        tags.append("Sun in diurnal sign by day")
    if (not is_day) and moon_sign in NOCTURNAL_SIGNS:
        score += 0.3
        tags.append("Moon in nocturnal sign by night")

    for label, planet_name in (("Asc ruler", asc_ruler), ("7th ruler", seventh_ruler)):
        if not planet_name:
            continue
        house = _planet_house(planets, planet_name, cusps)
        if house in ANGULAR_HOUSES:
            score += 1.5
            tags.append(f"{label} angular")
        elif house in SUCCEDENT_HOUSES:
            score += 0.5
            tags.append(f"{label} succedent")
        elif house in CADENT_HOUSES:
            score -= 1.0
            tags.append(f"{label} cadent")

        row = _planet_row(planets, planet_name)
        if bool(row.get("retrograde")):
            score -= 2.0
            tags.append(f"{label} retrograde")
        speed = _planet_speed_abs(planets, planet_name)
        if speed is not None and speed < 0.1:
            score -= 0.7
            tags.append(f"{label} slow")

        for malefic in ("Mars", "Saturn"):
            pair_rows = _aspect_pair(aspects, planet_name, malefic)
            for pair in pair_rows:
                aspect_name = _aspect_name(pair)
                if not _is_hard_aspect(aspect_name):
                    continue
                penalty = 1.0
                note = f"{label} afflicted by {malefic} ({aspect_name})"
                if _is_applying(pair):
                    penalty += 0.5
                    note = f"{label} applying to {malefic} ({aspect_name})"
                score -= penalty
                tags.append(note)
                break

    for benefic in BENEFICS:
        house = _planet_house(planets, benefic, cusps)
        if house in ANGULAR_HOUSES:
            gain = 1.0
            if house in {1, 7, 10}:
                gain += 0.5
            score += gain
            tags.append(f"{benefic} in {_ordinal(house)}")

    for malefic in MALEFICS:
        house = _planet_house(planets, malefic, cusps)
        if house in ANGULAR_HOUSES:
            loss = 1.5
            if house in {1, 10}:
                loss += 1.0
            elif house == 7:
                loss += 0.5
            score -= loss
            tags.append(f"{malefic} in {_ordinal(house)}")

    moon_house = _planet_house(planets, "Moon", cusps)
    if moon_house in (6, 8, 12):
        score -= 2.0
        tags.append("Moon in bad house (6/8/12)")

    for malefic in ("Mars", "Saturn"):
        for pair in _aspect_pair(aspects, "Moon", malefic):
            aspect_name = _aspect_name(pair)
            if not _is_hard_aspect(aspect_name):
                continue
            penalty = 2.0
            note = f"Moon afflicted by {malefic} ({aspect_name})"
            if _is_applying(pair):
                penalty += 0.5
                note = f"Moon applying hard to {malefic} ({aspect_name})"
            score -= penalty
            tags.append(note)
            break

    bright_swift = _moon_is_bright_and_swift(planets)
    weak_light = _moon_has_little_light_or_is_slow(planets)
    for target in ("Jupiter", "Saturn", "Mars", "Venus"):
        for pair in _aspect_pair(aspects, "Moon", target):
            if _aspect_name(pair) != "Conjunction":
                continue
            if target in {"Jupiter", "Saturn"}:
                if bright_swift:
                    score += 1.25
                    tags.append(f"Moon conjunct {target} while bright and swift")
                elif weak_light:
                    score -= 1.0
                    tags.append(f"Moon conjunct {target} with little light or slow")
            else:
                if bright_swift:
                    score -= 1.0
                    tags.append(f"Moon conjunct {target} while bright and swift")
                elif weak_light:
                    score += 0.5
                    tags.append(f"Moon conjunct {target} with little light or slow")
            break

    next_aspect = election_cd.get("moon_next_aspect")
    if isinstance(next_aspect, dict):
        next_planet = str(next_aspect.get("planet") or "")
        next_name = str(next_aspect.get("aspect") or "")
        next_row = _planet_row(planets, next_planet)
        if bool(next_row.get("retrograde")):
            score -= 1.8
            tags.append(f"Moon applying to retrograde {next_planet}")
        if moon_sign in VENUS_DOMICILES and next_planet == "Mars":
            score -= 1.5
            tags.append(f"Avoid Moon application: Mars from Venus sign ({moon_sign})")
        if moon_sign in MERCURY_DOMICILES and next_planet == "Jupiter":
            score -= 1.5
            tags.append(f"Avoid Moon application: Jupiter from Mercury sign ({moon_sign})")
        if moon_sign in SATURN_DOMICILES and next_planet == "Sun":
            score -= 1.5
            tags.append(f"Avoid Moon application: Sun from Saturn sign ({moon_sign})")
        if next_planet in BENEFICS and _is_soft_aspect(next_name):
            score += 0.8
            tags.append(f"Moon applying {next_name} to {next_planet}")
        if next_planet in MALEFICS and _is_hard_aspect(next_name):
            score -= 1.5
            tags.append(f"Moon applying {next_name} to {next_planet}")

        separated_from_mars = any(
            _aspect_name(pair) == "Conjunction" and _is_separating(pair)
            for pair in _aspect_pair(aspects, "Moon", "Mars")
        )
        opposite_sun = any(_aspect_name(pair) == "Opposition" for pair in _aspect_pair(aspects, "Moon", "Sun"))
        if (separated_from_mars or opposite_sun) and next_planet in MALEFICS and _is_hard_aspect(next_name):
            score -= 1.5
            tags.append("Moon separated from Mars or opposed Sun before malefic application")

    if opts.get("include_lunation_screen"):
        last_lunation = None
        for pair in _aspect_pair(aspects, "Moon", "Sun"):
            aspect_name = _aspect_name(pair)
            if aspect_name in {"Conjunction", "Opposition"} and _is_separating(pair):
                last_lunation = aspect_name
                break
        if last_lunation:
            sun_house = _planet_house(planets, "Sun", cusps)
            if sun_house in (1, 10, 11):
                score += 0.4
                tags.append("Preceding lunation in good house (proxy)")
            elif sun_house in (6, 8, 12):
                score -= 0.4
                tags.append("Preceding lunation in bad house (proxy)")

    if natal_cd:
        natal_cusps = natal_cd.get("house_cusps") or natal_cd.get("houses") or []
        natal_planets = _natal_planet_map(natal_cd)
        natal_asc_sign = _sign_from_lon(float(natal_cusps[0])) if len(natal_cusps) >= 1 else None
        natal_asc_ruler = TRAD_RULER.get(natal_asc_sign) if natal_asc_sign else None
        natal_dsc_sign = _sign_from_lon(float(natal_cusps[6])) if len(natal_cusps) >= 7 else None
        natal_seventh_ruler = TRAD_RULER.get(natal_dsc_sign) if natal_dsc_sign else None

        if asc_ruler and natal_asc_ruler and asc_ruler == natal_asc_ruler:
            score += 1.0
            tags.append("Election Asc ruler matches natal Asc ruler")

        moon_lon = _planet_lon(planets, "Moon")
        if moon_lon is not None and isinstance(natal_cusps, list) and len(natal_cusps) >= 12:
            natal_moon_house = _house_from_lon(moon_lon, natal_cusps)
            if natal_moon_house in (6, 8, 12):
                score -= 1.5
                tags.append("Moon falls in natal 6/8/12")

        if moon_lon is not None:
            for malefic in ("Mars", "Saturn"):
                natal_lon = _safe_float((natal_planets.get(malefic) or {}).get("longitude"))
                if natal_lon is None:
                    continue
                sep = _ang_sep(moon_lon, natal_lon)
                if sep <= 6.0 or abs(sep - 90.0) <= 6.0 or abs(sep - 180.0) <= 6.0:
                    score -= 1.5
                    tags.append(f"Moon hard to natal {malefic}")

            for target_name in ("Venus", "Jupiter", natal_seventh_ruler):
                if not target_name:
                    continue
                natal_lon = _safe_float((natal_planets.get(target_name) or {}).get("longitude"))
                if natal_lon is None:
                    continue
                sep = _ang_sep(moon_lon, natal_lon)
                if sep <= 6.0 or abs(sep - 60.0) <= 5.0 or abs(sep - 120.0) <= 6.0:
                    score += 0.8
                    tags.append(f"Moon soft to natal {target_name}")
                elif abs(sep - 90.0) <= 6.0 or abs(sep - 180.0) <= 6.0:
                    score -= 0.8
                    tags.append(f"Moon hard to natal {target_name}")

        if hits:
            favorable = 0.0
            warnings = 0.0
            for hit in hits[:15]:
                transiting = str(hit.get("transiting") or "")
                target = str(hit.get("target_label") or hit.get("natal") or "")
                aspect_name = str(hit.get("aspect") or "")
                if not _has_target_token(target, MARRIAGE_TARGET_TOKENS):
                    continue
                if transiting in BENEFICS and aspect_name in {"Conjunction", "Trine", "Sextile"}:
                    favorable += 0.6
                if transiting in MALEFICS and aspect_name in {"Conjunction", "Square", "Opposition"}:
                    warnings += 0.8
            if favorable:
                gain = min(2.4, favorable)
                score += gain
                tags.append(f"Directions/Transits favorable (+{gain:.1f})")
            if warnings:
                loss = min(3.2, warnings)
                score -= loss
                tags.append(f"Directions/Transits warn (-{loss:.1f})")

        try:
            if current_timestamp and sr_windows and any(start <= current_timestamp <= end for (start, end) in sr_windows):
                score += 0.8
                tags.append("Marriage SR window active")
            if current_timestamp and lr_list:
                nearest = min(abs((current_timestamp - lr).total_seconds()) for lr in lr_list)
                if nearest <= 12 * 3600:
                    score += 0.6
                    tags.append("Near lunar return (<=12h)")
                elif nearest <= 48 * 3600:
                    score += 0.2
                    tags.append("Near lunar return (<=48h)")
        except Exception:
            pass

        strong = 0
        weak = 0
        hinder = 0
        for planet_name in ("Venus", "Jupiter", natal_seventh_ruler):
            if not planet_name:
                continue
            house = _natal_house_of(natal_planets, natal_cusps, planet_name)
            if house in ANGULAR_HOUSES or house in SUCCEDENT_HOUSES:
                strong += 1
            row = natal_planets.get(planet_name) or {}
            if bool(row.get("retrograde")):
                weak += 1
        if len(natal_cusps) >= 7:
            natal_dsc_lon = float(natal_cusps[6]) % 360.0
            for malefic in ("Mars", "Saturn"):
                mal_lon = _safe_float((natal_planets.get(malefic) or {}).get("longitude"))
                if mal_lon is not None and _ang_sep(mal_lon, natal_dsc_lon) <= 4.0:
                    hinder += 1

        if strong == 0 and (weak >= 2 or hinder >= 1):
            score *= 0.5
            tags.append("Natal promise weak - capping score")
        elif strong >= 2 and weak == 0 and hinder == 0:
            tags.append("Natal promise supportive")
        else:
            score *= 0.85
            tags.append("Natal promise mixed")

    if opts.get("include_fixed_stars"):
        try:
            from fixed_stars import compute_fixed_star_hits

            hits_fs = compute_fixed_star_hits(
                election_cd if isinstance(election_cd, dict) else {},
                orb_deg=1.0,
                check_planets=["Moon"],
                include_cusps=True,
            )
            good = {"Regulus", "Spica", "Aldebaran", "Fomalhaut"}
            bad = {"Algol", "Antares", "Scheat"}
            for hit in hits_fs or []:
                star = str(hit.get("star") or "")
                target = str(hit.get("target_label") or hit.get("target") or "")
                if target not in {"Asc", "MC", "Moon"}:
                    continue
                if star in good:
                    score += 0.4
                    tags.append(f"Fixed star {star} on {target}")
                elif star in bad:
                    score -= 0.6
                    tags.append(f"Fixed star {star} on {target}")
        except Exception:
            pass

    pros, cautions = split_marriage_tags(tags)
    return Score(value=round(score, 2), tags=tags, pros=pros, cautions=cautions)


__all__ = ["score_marriage_election"]
