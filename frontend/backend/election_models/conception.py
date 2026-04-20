from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from .common import (
    Score,
    FIXED_SIGNS,
    BENEFICS,
    MALEFICS,
    ANGULAR_HOUSES,
    SUCCEDENT_HOUSES,
    CADENT_HOUSES,
    TRAD_RULER,
    _hi_element,
    _sign_from_lon,
    _house_cusps,
    _collect_planets,
    _house_from_lon,
    _get_aspects_list,
    _ang_sep,
    _is_waxing,
)

FERTILE_SIGNS = {"Cancer", "Scorpio", "Pisces", "Taurus"}

MASC_SIGNS = {"Aries", "Gemini", "Leo", "Libra", "Sagittarius", "Aquarius"}
FEM_SIGNS = {"Taurus", "Cancer", "Virgo", "Scorpio", "Capricorn", "Pisces"}

MASC_PLANETS = {"Sun", "Jupiter", "Mars"}
FEM_PLANETS = {"Moon", "Venus", "Saturn"}

VENUS_DIGNITIES = {"Taurus", "Libra", "Pisces"}
JUPITER_DIGNITIES = {"Sagittarius", "Pisces", "Cancer"}
MARS_DIGNITIES = {"Aries", "Scorpio", "Capricorn"}
SATURN_DIGNITIES = {"Capricorn", "Aquarius", "Libra"}

SOFT_ASPECTS = {"Conjunction", "Trine", "Sextile"}
HARD_ASPECTS = {"Square", "Opposition", "Conjunction"}


def _planet_house(planet: Optional[Dict[str, Any]], cusps: List[float]) -> Optional[int]:
    if not planet:
        return None
    try:
        if planet.get("house") is not None:
            return int(planet.get("house"))
        lon = float(planet.get("longitude")) if planet.get("longitude") is not None else None
        if lon is not None:
            return _house_from_lon(lon, cusps)
    except Exception:
        return None
    return None


def _is_dignified(planet: str, sign: Optional[str]) -> bool:
    if not sign:
        return False
    sign = str(sign)
    if planet == "Venus":
        return sign in VENUS_DIGNITIES
    if planet == "Jupiter":
        return sign in JUPITER_DIGNITIES
    if planet == "Mars":
        return sign in MARS_DIGNITIES
    if planet == "Saturn":
        return sign in SATURN_DIGNITIES
    if planet == "Moon":
        return sign in {"Cancer", "Taurus"}
    if planet == "Sun":
        return sign == "Leo"
    return False


def _is_applying(phase: Optional[str]) -> bool:
    if not phase:
        return False
    phase = phase.lower()
    return "apply" in phase or phase == "applying"


def _iterate_aspects(aspects: Iterable[Dict[str, Any]], target: str) -> Iterable[Tuple[Dict[str, Any], str]]:
    for row in aspects or []:
        try:
            p1 = str(row.get("planet1") or row.get("p1") or "")
            p2 = str(row.get("planet2") or row.get("p2") or "")
            if not p1 or not p2:
                continue
            if target == p1:
                yield row, p2
            elif target == p2:
                yield row, p1
        except Exception:
            continue


def _element_of_sign(sign: Optional[str]) -> Optional[str]:
    if not sign:
        return None
    try:
        return _hi_element(sign)  # type: ignore
    except Exception:
        return None


def score_conception_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Score conception-focused election windows."""

    options = options or {}
    score = 0.0
    tags: List[str] = []
    critical_notes: List[str] = []

    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    aspects = _get_aspects_list(election_cd) or []

    asc_sign: Optional[str] = None
    fifth_sign: Optional[str] = None
    try:
        if len(cusps) >= 5:
            asc_sign = _sign_from_lon(cusps[0])
            fifth_sign = _sign_from_lon(cusps[4])
    except Exception:
        pass

    moon = planets.get("Moon")
    sun = planets.get("Sun")
    venus = planets.get("Venus")
    jupiter = planets.get("Jupiter")

    moon_sign = str(moon.get("sign")) if moon and moon.get("sign") else None
    moon_house = _planet_house(moon, cusps)
    moon_lon = float(moon.get("longitude")) if moon and moon.get("longitude") is not None else None
    sun_lon = float(sun.get("longitude")) if sun and sun.get("longitude") is not None else None

    gender_pref = (options or {}).get("gender") if options else None
    sex_focus: Optional[str] = None
    if isinstance(gender_pref, str):
        gp = gender_pref.strip().lower()
        if gp in {"male", "boy", "masculine"}:
            sex_focus = "male"
        elif gp in {"female", "girl", "feminine"}:
            sex_focus = "female"

    desired_signs = MASC_SIGNS if sex_focus == "male" else FEM_SIGNS if sex_focus == "female" else None
    opposite_signs = FEM_SIGNS if sex_focus == "male" else MASC_SIGNS if sex_focus == "female" else None
    desired_planets = MASC_PLANETS if sex_focus == "male" else FEM_PLANETS if sex_focus == "female" else None
    opposite_planets = FEM_PLANETS if sex_focus == "male" else MASC_PLANETS if sex_focus == "female" else None
    sex_bias = 0.0
    sex_counts = {"desired": 0, "opposed": 0, "neutral": 0}
    sex_details: List[str] = []

    def _sex_class(sign: Optional[str]) -> str:
        if not sign:
            return "neutral"
        if desired_signs and sign in desired_signs:
            return "desired"
        if opposite_signs and sign in opposite_signs:
            return "opposed"
        return "neutral"

    def _sex_register(label: str, sign: Optional[str], weight: float = 1.0) -> None:
        nonlocal sex_bias
        if not sex_focus:
            return
        status = _sex_class(sign)
        sex_details.append(f"{label}:{status}:{sign or '-'}")
        if status == "desired":
            sex_counts["desired"] += 1
            sex_bias += weight
        elif status == "opposed":
            sex_counts["opposed"] += 1
            sex_bias -= weight
        else:
            sex_counts["neutral"] += 1

    def _sex_register_planet(label: str, planet_name: str, weight: float = 1.0) -> None:
        nonlocal sex_bias
        if not sex_focus:
            return
        if desired_planets and planet_name in desired_planets:
            sex_details.append(f"{label}:desired:{planet_name}")
            sex_counts["desired"] += 1
            sex_bias += weight
        elif opposite_planets and planet_name in opposite_planets:
            sex_details.append(f"{label}:opposed:{planet_name}")
            sex_counts["opposed"] += 1
            sex_bias -= weight
        else:
            sex_details.append(f"{label}:neutral:{planet_name}")
            sex_counts["neutral"] += 1

    if sex_focus:
        _sex_register("Ascendant", asc_sign, 1.5)
        _sex_register("Fifth cusp", fifth_sign, 1.6)

    # --- 5th house strength ---
    fifth_planets: List[str] = []
    for nm, info in planets.items():
        h = _planet_house(info, cusps)
        if h == 5:
            fifth_planets.append(nm)
            if nm in BENEFICS:
                score += 3.0
                tags.append(f"{nm} in 5th (fertility boost)")
            elif nm in MALEFICS:
                sign = str(info.get("sign") or "")
                if _is_dignified(nm, sign):
                    score -= 1.0
                    tags.append(f"{nm} dignified in 5th (manageable)")
                else:
                    score -= 5.0
                    critical_notes.append(f"{nm} debilitated in 5th")

    fifth_ruler = TRAD_RULER.get(fifth_sign) if fifth_sign else None
    ruler_info = planets.get(fifth_ruler) if fifth_ruler else None
    if ruler_info:
        ruler_sign = str(ruler_info.get("sign") or _sign_from_lon(float(ruler_info.get("longitude") or 0.0)))
        if sex_focus:
            _sex_register("5th ruler", ruler_sign, 1.5)
        if _is_dignified(fifth_ruler, ruler_sign):
            score += 2.5
            tags.append("5th ruler dignified")
        ruler_house = _planet_house(ruler_info, cusps)
        if ruler_house in ANGULAR_HOUSES:
            score += 1.0
            tags.append("5th ruler angular")
        elif ruler_house in SUCCEDENT_HOUSES:
            score += 0.5
            tags.append("5th ruler succedent")
        elif ruler_house in CADENT_HOUSES:
            score -= 1.0
            tags.append("5th ruler cadent")

        for asp, other in _iterate_aspects(aspects, fifth_ruler):
            aspect = str(asp.get("aspect") or "")
            phase = str(asp.get("phase") or "").lower()
            if other in ("Ascendant", "Asc") and aspect in SOFT_ASPECTS and _is_applying(phase):
                score += 1.5
                tags.append("5th ruler applying soft to Ascendant")
            if other == "Moon" and aspect in SOFT_ASPECTS and _is_applying(phase):
                score += 1.8
                tags.append("5th ruler applying soft to Moon")
            if other in MALEFICS and aspect in HARD_ASPECTS and _is_applying(phase):
                score -= 2.2
                tags.append("5th ruler afflicted by malefic")
            if sex_focus and _is_applying(phase):
                if desired_planets and other in desired_planets and aspect in SOFT_ASPECTS:
                    _sex_register_planet(f"5th ruler applying {aspect}", other, 1.1)
                elif opposite_planets and other in opposite_planets and aspect in HARD_ASPECTS:
                    _sex_register_planet(f"5th ruler hard {aspect}", other, 1.1)

    # --- Moon requirements ---
    if moon_lon is not None and sun_lon is not None:
        waxing = _is_waxing(moon_lon, sun_lon)
        if waxing:
            score += 1.2
            tags.append("Moon waxing")
        else:
            score -= 4.0
            critical_notes.append("Moon waning")
    if moon_sign:
        if sex_focus:
            _sex_register("Moon", moon_sign, 2.0)
        if moon_sign in FERTILE_SIGNS:
            score += 2.5
            tags.append(f"Moon in fertile sign ({moon_sign})")
        else:
            score -= 1.5
            tags.append(f"Moon not in fertile sign ({moon_sign})")
    if moon_house in (6, 8, 12):
        score -= 4.5
        critical_notes.append(f"Moon in {moon_house}th house")

    moon_combust = False
    if moon_lon is not None and sun_lon is not None:
        sep = _ang_sep(moon_lon, sun_lon)
        if sep <= 8.0:
            moon_combust = True
            score -= 4.0
            critical_notes.append("Moon combust Sun")

    moon_soft = False
    for asp, other in _iterate_aspects(aspects, "Moon"):
        aspect = str(asp.get("aspect") or "")
        phase = str(asp.get("phase") or "").lower()
        if other in BENEFICS and aspect in ("Trine", "Sextile") and _is_applying(phase):
            moon_soft = True
            score += 2.8
            tags.append(f"Moon applying {aspect} to {other}")
            if sex_focus:
                _sex_register_planet(f"Moon applying {aspect}", other, 1.4)
        if other in MALEFICS and aspect in ("Square", "Opposition") and _is_applying(phase):
            score -= 3.5
            critical_notes.append(f"Moon applying {aspect} to {other}")
            if sex_focus:
                _sex_register_planet(f"Moon applying {aspect}", other, 1.6)
    if not moon_soft:
        tags.append("Moon lacks applying soft aspect to benefic")

    # --- Venus ---
    if venus:
        v_sign = str(venus.get("sign") or _sign_from_lon(float(venus.get("longitude") or 0.0)))
        if _is_dignified("Venus", v_sign):
            score += 2.0
            tags.append("Venus dignified")
        v_house = _planet_house(venus, cusps)
        if v_house in (1, 4, 5, 7, 10):
            score += 1.0
            tags.append("Venus well placed (angular/5th)")
        if bool(venus.get("retrograde")):
            score -= 3.0
            critical_notes.append("Venus retrograde")
        for asp, other in _iterate_aspects(aspects, "Venus"):
            aspect = str(asp.get("aspect") or "")
            phase = str(asp.get("phase") or "").lower()
            if other in ("Moon", "Jupiter") and aspect in SOFT_ASPECTS and _is_applying(phase):
                score += 1.0
                tags.append(f"Venus applying {aspect} to {other}")

    # --- Jupiter ---
    if jupiter:
        j_sign = str(jupiter.get("sign") or _sign_from_lon(float(jupiter.get("longitude") or 0.0)))
        if _is_dignified("Jupiter", j_sign):
            score += 1.8
            tags.append("Jupiter dignified")
        j_house = _planet_house(jupiter, cusps)
        if j_house == 5:
            score += 2.2
            tags.append("Jupiter in 5th")
        if bool(jupiter.get("retrograde")):
            score -= 2.5
            tags.append("Jupiter retrograde")
        for asp, other in _iterate_aspects(aspects, "Jupiter"):
            aspect = str(asp.get("aspect") or "")
            phase = str(asp.get("phase") or "").lower()
            if other in ("Moon", fifth_ruler) and aspect in SOFT_ASPECTS and _is_applying(phase):
                score += 1.2
                tags.append(f"Jupiter applying {aspect} to {other}")

    # --- Ascendant & malefic constraints ---
    if asc_sign:
        if asc_sign in FIXED_SIGNS:
            score += 1.0
            tags.append(f"Fixed Ascendant ({asc_sign})")
        if asc_sign in FERTILE_SIGNS:
            score += 1.0
            tags.append(f"Fertile Ascendant sign ({asc_sign})")

    asc_ruler = TRAD_RULER.get(asc_sign) if asc_sign else None
    asc_ruler_info = planets.get(asc_ruler) if asc_ruler else None
    if asc_ruler_info:
        asc_ruler_sign = str(asc_ruler_info.get("sign") or _sign_from_lon(float(asc_ruler_info.get("longitude") or 0.0)))
        if sex_focus:
            _sex_register("Asc ruler", asc_ruler_sign, 1.2)
        ar_house = _planet_house(asc_ruler_info, cusps)
        if ar_house in ANGULAR_HOUSES:
            score += 1.0
            tags.append("Asc ruler angular")
        elif ar_house in CADENT_HOUSES:
            score -= 1.0
            tags.append("Asc ruler cadent")
        if bool(asc_ruler_info.get("retrograde")):
            score -= 2.0
            tags.append("Asc ruler retrograde")
        for asp, other in _iterate_aspects(aspects, asc_ruler):
            aspect = str(asp.get("aspect") or "")
            phase = str(asp.get("phase") or "").lower()
            if other in MALEFICS and aspect in HARD_ASPECTS and _is_applying(phase):
                score -= 1.8
                tags.append("Asc ruler afflicted by malefic")
            if sex_focus and _is_applying(phase):
                if desired_planets and other in desired_planets and aspect in SOFT_ASPECTS:
                    _sex_register_planet(f"Asc ruler applying {aspect}", other, 0.9)
                elif opposite_planets and other in opposite_planets and aspect in HARD_ASPECTS:
                    _sex_register_planet(f"Asc ruler hard {aspect}", other, 0.9)

    for mal in MALEFICS:
        info = planets.get(mal)
        if not info:
            continue
        mh = _planet_house(info, cusps)
        if mh in (1, 5, 7):
            if _is_dignified(mal, str(info.get("sign") or "")):
                score -= 1.0
                tags.append(f"{mal} dignified but angular (monitor)")
            else:
                score -= 4.0
                critical_notes.append(f"{mal} in {mh}th house")

    if sun:
        for asp, other in _iterate_aspects(aspects, "Sun"):
            aspect = str(asp.get("aspect") or "")
            phase = str(asp.get("phase") or "").lower()
            if other in {"Moon", fifth_ruler} and aspect in ("Square", "Opposition") and _is_applying(phase):
                score -= 2.5
                tags.append("Sun hard aspect to fertility significator")

    if sex_focus:
        bias = max(-4.0, min(4.0, round(sex_bias, 2)))
        score += bias
        summary_focus = "boy" if sex_focus == "male" else "girl"
        summary_tag = (
            f"Sex focus ({summary_focus}): {sex_counts['desired']} supporting vs "
            f"{sex_counts['opposed']} opposing testimonies"
        )
        tags.insert(0, summary_tag)
        if sex_counts["desired"] >= sex_counts["opposed"]:
            tags.insert(1, f"Sex testimonies favor {summary_focus}")
        else:
            tags.insert(1, f"Sex testimonies oppose {summary_focus}")
        if sex_details:
            tags.append("SexAlignment|" + ";".join(sex_details))

    # --- Natal enrichment ---
    natal_cd = options.get("natal_cd")
    sr_windows = list(options.get("sr_windows") or [])
    lr_list = list(options.get("lr_list") or [])
    current_ts = options.get("current_timestamp")
    natal_cusps_opt = options.get("natal_cusps")

    if natal_cd:
        natal_planets = _collect_planets(natal_cd)
        natal_cusps = natal_cusps_opt
        if not (isinstance(natal_cusps, list) and len(natal_cusps) >= 12):
            natal_cusps = natal_cd.get("house_cusps") or natal_cd.get("houses")
        natal_cusps = list(natal_cusps) if isinstance(natal_cusps, list) else []

        natal_fifth_sign = None
        if natal_cusps and len(natal_cusps) >= 5:
            natal_fifth_sign = _sign_from_lon(float(natal_cusps[4]))
            tags.append(f"Natal 5th sign: {natal_fifth_sign}")
        natal_fifth_ruler = TRAD_RULER.get(natal_fifth_sign) if natal_fifth_sign else None
        natal_fifth_house_planets = []
        for nm, info in natal_planets.items():
            if _planet_house(info, natal_cusps) == 5:
                natal_fifth_house_planets.append(nm)
        if natal_fifth_house_planets:
            tags.append(f"Natal 5th occupants: {', '.join(natal_fifth_house_planets)}")
            if any(p in BENEFICS for p in natal_fifth_house_planets):
                score += 0.8
        if any(p in MALEFICS for p in natal_fifth_house_planets):
            score -= 1.2
            tags.append("Natal 5th holds malefic")

        natal_fertility_bonus = 0.0
        for p in ("Venus", "Moon", "Jupiter"):
            info = natal_planets.get(p)
            if not info:
                continue
            sign = str(info.get("sign") or _sign_from_lon(float(info.get("longitude") or 0.0)))
            if _is_dignified(p, sign):
                natal_fertility_bonus += 0.4
        if natal_fertility_bonus:
            score += natal_fertility_bonus
            tags.append("Natal fertility indicators strong")

        has_fertility_direction = False
        if natal_hits:
            for hit in natal_hits[:25]:
                label = str(hit.get("label") or hit.get("direction_label") or hit.get("target_label") or "")
                lower = label.lower()
                if "direction" in lower and ("5" in lower or "fifth" in lower):
                    has_fertility_direction = True
                    break
                tgt = str(hit.get("target_label") or hit.get("natal") or "").lower()
                if any(key in tgt for key in ("c5", "5th", "house 5")) and "dir" in lower:
                    has_fertility_direction = True
                    break
        if not has_fertility_direction:
            score *= 0.3
            tags.append("Natal directions weak — score reduced 70%")
        else:
            tags.append("Fertility direction active")

        benefic_to_natal_5th = False
        moon_afflicts_natal = False
        transit_ruler_hits_nat_ruler = False
        benefic_to_angles = False

        for hit in (natal_hits or [])[:40]:
            tr = str(hit.get("transiting") or "")
            tgt = str(hit.get("target_label") or hit.get("natal") or "")
            tgt_lower = tgt.lower()
            asp = str(hit.get("aspect") or "")
            if tr in BENEFICS and asp in SOFT_ASPECTS and any(key in tgt_lower for key in ("c5", "h5", "5th", "house 5", "fifth")):
                benefic_to_natal_5th = True
            if tr == "Moon" and asp in ("Square", "Opposition") and any(tgt_lower.endswith(x) or tgt_lower == x for x in ("moon", "venus")):
                moon_afflicts_natal = True
            if tr in BENEFICS and asp == "Conjunction" and any(key in tgt_lower for key in ("asc", "c1", "c5", "h5")):
                benefic_to_angles = True
            if fifth_ruler and natal_fifth_ruler and tr == fifth_ruler and natal_fifth_ruler.lower() in tgt_lower and asp in ("Trine", "Sextile", "Conjunction"):
                transit_ruler_hits_nat_ruler = True

        if benefic_to_natal_5th:
            score += 2.0
            tags.append("Transit benefic soft to natal 5th")
        else:
            tags.append("No transit benefic to natal 5th")
        if moon_afflicts_natal:
            score -= 2.8
            critical_notes.append("Transit Moon afflicts natal Moon/Venus")
        if transit_ruler_hits_nat_ruler:
            score += 1.5
            tags.append("Transit 5th ruler aspects natal 5th ruler")
        if benefic_to_angles:
            score += 0.8
            tags.append("Benefic conjunct natal angle/5th cusp")

        if natal_fifth_sign and moon_sign:
            nat_elem = _element_of_sign(natal_fifth_sign)
            moon_elem = _element_of_sign(moon_sign)
            if nat_elem and moon_elem and nat_elem == moon_elem:
                score += 0.7
                tags.append("Transit Moon shares element with natal 5th")

        natal_asc_sign = None
        if natal_cusps and len(natal_cusps) >= 1:
            natal_asc_sign = _sign_from_lon(float(natal_cusps[0]))
        if asc_sign and natal_asc_sign:
            asc_elem = _element_of_sign(asc_sign)
            nat_elem = _element_of_sign(natal_asc_sign)
            if asc_elem and nat_elem and asc_elem == nat_elem:
                score += 0.6
                tags.append("Ascendant harmonious with natal Ascendant")

        if sr_windows and current_ts is not None:
            if any(a <= current_ts <= b for (a, b) in sr_windows):
                score += 0.6
                tags.append("Within Solar Return fertility window")
            else:
                tags.append("Outside Solar Return fertility window")
        if lr_list and current_ts is not None:
            delta = min(abs((current_ts - lr).total_seconds()) for lr in lr_list)
            if delta <= 12 * 3600:
                score += 0.4
                tags.append("Near Lunar Return (≤12h)")

    else:
        tags.append("Transit-only mode (no natal)")

    # Apply critical penalties
    for note in critical_notes:
        tags.append(f"Critical: {note}")

    if critical_notes:
        score -= len(critical_notes) * 1.5

    return Score(value=round(score, 2), tags=tags)


__all__ = ["score_conception_election"]
