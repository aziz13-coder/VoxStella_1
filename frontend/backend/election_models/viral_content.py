from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from .common import (
    Score,
    BENEFICS, MALEFICS,
    ANGULAR_HOUSES, SUCCEDENT_HOUSES, CADENT_HOUSES,
    TRAD_RULER,
    FIXED_SIGNS, MUTABLE_SIGNS, CARDINAL_SIGNS,
    HI_EXALTATION, HI_TRIPLICITY, _hi_element,
    compute_morin_combustion,
    _collect_planets, _house_cusps, _house_from_lon, _sign_from_lon,
    _get_aspects_list, _ang_sep, _is_waxing,
)

SOFT_ASPECTS = {"Conjunction", "Trine", "Sextile"}
HARD_ASPECTS = {"Square", "Opposition", "Conjunction"}

IDEAL_ASC_SIGNS = {
    "Gemini": 3.0,
    "Libra": 2.6,
    "Aquarius": 2.3,
    "Leo": 2.1,
    "Sagittarius": 1.6,
    "Aries": 1.4,
}

ASC_CAUTION_SIGNS = {
    "Taurus": -2.2,
    "Scorpio": -2.0,
    "Capricorn": -1.6,
    "Cancer": -1.0,
}

MOON_AIR_SIGNS = {"Gemini", "Libra", "Aquarius"}
MOON_FIRE_SIGNS = {"Leo", "Sagittarius", "Aries"}


def _planet_house(planet: Optional[Dict[str, Any]], cusps: List[float]) -> Optional[int]:
    if not planet:
        return None
    try:
        if planet.get("house") is not None:
            return int(planet["house"])
    except Exception:
        pass
    try:
        lon = float(planet.get("longitude"))
    except Exception:
        return None
    return _house_from_lon(lon, cusps)


def _planets_in_house(names: Iterable[str], planets: Dict[str, Dict[str, Any]], cusps: List[float], target: int) -> List[str]:
    hits: List[str] = []
    for nm in names:
        house = _planet_house(planets.get(nm), cusps)
        if house == target:
            hits.append(nm)
    return hits


def _iter_aspects(aspects: Optional[List[Dict[str, Any]]], planet: str) -> Iterable[Tuple[str, str, str]]:
    if not aspects:
        return []
    rows: List[Tuple[str, str, str]] = []
    for row in aspects:
        try:
            p1 = str(row.get("planet1") or row.get("p1") or "")
            p2 = str(row.get("planet2") or row.get("p2") or "")
            if planet not in {p1, p2}:
                continue
            other = p2 if p1 == planet else p1
            asp = str(row.get("aspect") or "")
            phase = str(row.get("phase") or row.get("motion") or "").lower()
            rows.append((other, asp, phase))
        except Exception:
            continue
    return rows


def _combustion_status(planet: str, combust_map: Dict[str, str]) -> str:
    try:
        status = combust_map.get(planet)
        return str(status or "").lower()
    except Exception:
        return ""


def _clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def score_viral_content_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Score elections for launching viral/social media content."""

    score = 0.0
    tags: List[str] = []

    opts = options or {}
    if natal_hits is None:
        natal_hits = opts.get("natal_hits")

    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    aspects_list = _get_aspects_list(election_cd) or []

    asc_sign = _sign_from_lon(cusps[0]) if len(cusps) >= 1 else None
    mc_sign = _sign_from_lon(cusps[9]) if len(cusps) >= 10 else None

    combust_map: Dict[str, str] = {}
    try:
        cur_ts = opts.get("current_timestamp")
        if compute_morin_combustion is not None and cur_ts is not None:
            rows = compute_morin_combustion(election_cd if isinstance(election_cd, dict) else {}, cur_ts.isoformat())
            for r in rows or []:
                nm = str(r.get("planet") or "")
                st = str(r.get("status") or "").lower()
                if nm:
                    combust_map[nm] = st
    except Exception:
        combust_map = {}

    # Phase 4: Ascendant & 1st house (max 30)
    asc_tags: List[str] = []
    benefic_first = _planets_in_house(BENEFICS, planets, cusps, 1)
    if benefic_first:
        asc_tags.append(f"Benefic in 1st ({', '.join(benefic_first)})")

    asc_ruler_score = 0.0
    L1 = TRAD_RULER.get(asc_sign) if asc_sign else None
    if L1 and L1 in planets:
        pr = planets[L1]
        ruler_house = _planet_house(pr, cusps)
        if ruler_house in ANGULAR_HOUSES:
            asc_ruler_score += 8.0
            asc_tags.append(f"{L1} (ASC ruler) angular")
        elif ruler_house in SUCCEDENT_HOUSES:
            asc_ruler_score += 5.0
            asc_tags.append(f"{L1} (ASC ruler) succedent")
        elif ruler_house in CADENT_HOUSES:
            asc_ruler_score -= 4.0
            asc_tags.append(f"{L1} (ASC ruler) cadent")
        if bool(pr.get("retrograde")):
            asc_ruler_score -= 6.0
            asc_tags.append("ASC ruler retrograde – throttles visibility")
        else:
            asc_ruler_score += 4.0
            asc_tags.append("ASC ruler direct")
        status = _combustion_status(L1, combust_map)
        if status == "combust":
            asc_ruler_score -= 5.0
            asc_tags.append("ASC ruler combust")
        elif status == "under_beams":
            asc_ruler_score -= 2.0
            asc_tags.append("ASC ruler under beams")
        try:
            r_sign = str(pr.get("sign") or _sign_from_lon(float(pr.get("longitude"))))
            if TRAD_RULER.get(r_sign) == L1:
                asc_ruler_score += 4.0
                asc_tags.append("ASC ruler dignified")
            elif HI_EXALTATION.get(r_sign) == L1:
                asc_ruler_score += 3.0
                asc_tags.append("ASC ruler exalted")
            else:
                elem = _hi_element(r_sign)
                if elem in {"Air", "Fire"}:
                    asc_ruler_score += 1.5
                    asc_tags.append("ASC ruler in compatible element")
        except Exception:
            pass
        for other, asp, phase in _iter_aspects(aspects_list, L1):
            if other in BENEFICS and asp in SOFT_ASPECTS:
                bump = 2.5
                if "apply" in phase:
                    bump += 0.5
                asc_ruler_score += bump
                asc_tags.append(f"{L1} soft to {other}")
            if other in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                asc_ruler_score -= 4.0
                asc_tags.append(f"{L1} hard applying to {other}")
        asc_ruler_score = _clamp(asc_ruler_score, -10.0, 15.0)
    else:
        asc_tags.append("ASC ruler data unavailable")

    asc_sign_adj = 0.0
    if asc_sign in IDEAL_ASC_SIGNS:
        asc_sign_adj += IDEAL_ASC_SIGNS[asc_sign]
        asc_tags.append(f"{asc_sign} rising – social signal boost")
    elif asc_sign in ASC_CAUTION_SIGNS:
        asc_sign_adj += ASC_CAUTION_SIGNS[asc_sign]
        asc_tags.append(f"{asc_sign} rising – slower viral spread")
    elif asc_sign in MUTABLE_SIGNS:
        asc_sign_adj += 1.0
        asc_tags.append("Mutable Asc – responsive tone")

    benefic_bonus = 15.0 if benefic_first else 0.0
    asc_total = benefic_bonus + asc_ruler_score + asc_sign_adj
    asc_total = _clamp(asc_total, -10.0, 30.0)
    score += asc_total
    tags.extend(asc_tags)

    # Phase 1/2: 11th house (max 25)
    house11_tags: List[str] = []
    benefic_eleventh = _planets_in_house(BENEFICS, planets, cusps, 11)
    malefic_eleventh = _planets_in_house(MALEFICS, planets, cusps, 11)
    eleventh_score = 0.0
    if benefic_eleventh:
        eleventh_score += 12.0
        house11_tags.append(f"Benefic in 11th ({', '.join(benefic_eleventh)})")
    if malefic_eleventh:
        eleventh_score -= 6.0
        house11_tags.append(f"Malefic in 11th ({', '.join(malefic_eleventh)}) – audience friction")

    sign_11 = _sign_from_lon(cusps[10]) if len(cusps) >= 11 else None
    L11 = TRAD_RULER.get(sign_11) if sign_11 else None
    if L11 and L11 in planets:
        r11 = planets[L11]
        r11_house = _planet_house(r11, cusps)
        if r11_house in ANGULAR_HOUSES:
            eleventh_score += 7.0
            house11_tags.append("11th ruler angular")
        elif r11_house in SUCCEDENT_HOUSES:
            eleventh_score += 5.0
            house11_tags.append("11th ruler succedent")
        elif r11_house in CADENT_HOUSES:
            eleventh_score -= 4.0
            house11_tags.append("11th ruler cadent – weak follow-through")
        if bool(r11.get("retrograde")):
            eleventh_score -= 4.0
            house11_tags.append("11th ruler retrograde")
        status = _combustion_status(L11, combust_map)
        if status == "combust":
            eleventh_score -= 3.0
            house11_tags.append("11th ruler combust")
        elif status == "under_beams":
            eleventh_score -= 1.5
        try:
            r11_sign = str(r11.get("sign") or _sign_from_lon(float(r11.get("longitude"))))
            if TRAD_RULER.get(r11_sign) == L11:
                eleventh_score += 3.0
                house11_tags.append("11th ruler dignified")
            elif HI_EXALTATION.get(r11_sign) == L11:
                eleventh_score += 2.0
                house11_tags.append("11th ruler exalted")
        except Exception:
            pass
        for other, asp, phase in _iter_aspects(aspects_list, L11):
            if other in BENEFICS and asp in SOFT_ASPECTS:
                val = 2.5
                if "apply" in phase:
                    val += 0.5
                eleventh_score += val
                house11_tags.append(f"11th ruler soft to {other}")
            if other in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                eleventh_score -= 4.0
                house11_tags.append(f"11th ruler hard applying to {other}")
        if L1 and L1 in planets:
            try:
                r11_lon = float(r11.get("longitude"))
                asc_lon = float(cusps[0] % 360.0)
                sep = _ang_sep(r11_lon, asc_lon)
                if min(abs(sep - ang) for ang in (0.0, 60.0, 120.0)) <= 5.0:
                    eleventh_score += 3.0
                    house11_tags.append("11th ruler harmonizes with Asc")
            except Exception:
                pass
    eleventh_score = _clamp(eleventh_score, -15.0, 25.0)
    score += eleventh_score
    tags.extend(house11_tags)

    # Phase 3: Communication engines (3rd house & Mercury) – max 20
    communication_tags: List[str] = []
    mercury_score = 0.0
    mercury = planets.get("Mercury")
    if mercury:
        if bool(mercury.get("retrograde")):
            mercury_score -= 8.0
            communication_tags.append("Mercury retrograde – publishing lag")
        else:
            mercury_score += 5.0
            communication_tags.append("Mercury direct")
        try:
            m_sign = str(mercury.get("sign") or _sign_from_lon(float(mercury.get("longitude"))))
            if m_sign in {"Gemini", "Virgo"}:
                mercury_score += 4.0
                communication_tags.append("Mercury dignified")
            elif m_sign in {"Sagittarius", "Pisces"}:
                mercury_score -= 2.0
                communication_tags.append("Mercury in detriment/fall")
            elif m_sign in {"Libra", "Aquarius"}:
                mercury_score += 2.0
        except Exception:
            pass
        m_house = _planet_house(mercury, cusps)
        if m_house in {1, 3, 5, 10, 11}:
            mercury_score += 2.0
            communication_tags.append(f"Mercury in {m_house} house")
        elif m_house in {6, 8, 12}:
            mercury_score -= 2.5
            communication_tags.append("Mercury in hindered house")
        status = _combustion_status("Mercury", combust_map)
        if status == "combust":
            mercury_score -= 3.5
            communication_tags.append("Mercury combust")
        elif status == "under_beams":
            mercury_score -= 1.0
        for other, asp, phase in _iter_aspects(aspects_list, "Mercury"):
            if other in BENEFICS and asp in SOFT_ASPECTS:
                val = 2.5
                if "apply" in phase:
                    val += 0.5
                mercury_score += val
                communication_tags.append(f"Mercury soft to {other}")
            if other in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                mercury_score -= 4.0
                communication_tags.append(f"Mercury hard applying to {other}")
    else:
        communication_tags.append("Mercury data unavailable")

    third_support = 0.0
    sign_3 = _sign_from_lon(cusps[2]) if len(cusps) >= 3 else None
    L3 = TRAD_RULER.get(sign_3) if sign_3 else None
    if L3 and L3 in planets:
        r3 = planets[L3]
        r3_house = _planet_house(r3, cusps)
        if r3_house in ANGULAR_HOUSES:
            third_support += 4.0
            communication_tags.append("3rd ruler angular")
        elif r3_house in SUCCEDENT_HOUSES:
            third_support += 2.5
        elif r3_house in CADENT_HOUSES:
            third_support -= 2.0
        if bool(r3.get("retrograde")):
            third_support -= 2.5
        for other, asp, phase in _iter_aspects(aspects_list, L3):
            if other in BENEFICS and asp in SOFT_ASPECTS:
                val = 2.5
                if "apply" in phase:
                    val += 0.5
                third_support += val
                communication_tags.append(f"3rd ruler soft to {other}")
            if other in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                third_support -= 3.5
                communication_tags.append(f"3rd ruler hard applying to {other}")
    benefic_third = _planets_in_house(BENEFICS, planets, cusps, 3)
    if benefic_third:
        third_support += 2.0
        communication_tags.append(f"Benefic in 3rd ({', '.join(benefic_third)})")

    third_total = _clamp(mercury_score + third_support, -15.0, 20.0)
    score += third_total
    tags.extend(communication_tags)

    # Moon condition (max 15)
    moon_tags: List[str] = []
    moon_score = 0.0
    moon_apply = 0.0
    moon = planets.get("Moon")
    sun = planets.get("Sun")
    moon_speed = None
    moon_lon = None
    if moon:
        try:
            moon_lon = float(moon.get("longitude"))
        except Exception:
            moon_lon = None
        try:
            moon_speed = abs(float(moon.get("speed") or moon.get("daily_motion")))
        except Exception:
            moon_speed = None

        moon_house = _planet_house(moon, cusps)
        if moon_house in {1, 3, 5, 10, 11}:
            moon_score += 2.0
            moon_tags.append(f"Moon in {moon_house} house")
        elif moon_house in {6, 8, 12}:
            moon_score -= 2.5
            moon_tags.append("Moon in 6/8/12 – weak engagement")

        moon_sign = None
        try:
            moon_sign = str(moon.get("sign") or _sign_from_lon(moon_lon))
        except Exception:
            moon_sign = None
        if moon_sign in MOON_AIR_SIGNS:
            moon_score += 3.0
            moon_tags.append("Moon in air sign – social traction")
        elif moon_sign in MOON_FIRE_SIGNS:
            moon_score += 1.5
        elif moon_sign in {"Capricorn", "Scorpio"}:
            moon_score -= 1.5

        if moon_speed is not None:
            if moon_speed >= 12.5:
                moon_score += 2.0
                moon_tags.append("Moon swift")
            elif moon_speed < 11.0:
                moon_score -= 2.0
                moon_tags.append("Moon slow")

        if sun and sun.get("longitude") is not None and moon_lon is not None:
            if _is_waxing(moon_lon, float(sun.get("longitude"))):
                moon_score += 1.5
                moon_tags.append("Waxing Moon – growth momentum")
            else:
                moon_tags.append("Waning Moon")

        moon_next = election_cd.get("moon_next_aspect")
        if isinstance(moon_next, dict):
            try:
                pn = str(moon_next.get("planet") or "")
                asp = str(moon_next.get("aspect") or "")
                phase = str(moon_next.get("phase") or "").lower()
                if pn in BENEFICS and asp in SOFT_ASPECTS:
                    moon_apply += 8.0
                    note = f"Moon applying {asp} to {pn}"
                    if "apply" in phase:
                        note += " (applying)"
                    moon_tags.append(note)
                if pn in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                    moon_apply -= 6.0
                    moon_tags.append(f"Moon applying {asp} to {pn}")
            except Exception:
                pass

        voc = False
        try:
            cons = election_cd.get("considerations")
            if isinstance(cons, dict) and bool(cons.get("moon_void")):
                voc = True
            if bool(election_cd.get("moon_void") or election_cd.get("moon_voc") or election_cd.get("void_of_course")):
                voc = True
        except Exception:
            pass
        if voc:
            moon_apply -= 6.0
            moon_tags.append("Moon void-of-course – virality stalls")
    else:
        moon_tags.append("Moon data unavailable")

    moon_total = _clamp(moon_score + moon_apply, -12.0, 15.0)
    score += moon_total
    tags.extend(moon_tags)

    # Malefic management (max penalty 10)
    malefic_penalty = 0.0
    malefic_tags: List[str] = []
    for nm in ("Mars", "Saturn"):
        p = planets.get(nm)
        house = _planet_house(p, cusps)
        if house in ANGULAR_HOUSES:
            malefic_penalty += 5.0
            malefic_tags.append(f"{nm} on angle (house {house})")
        elif house == 11:
            malefic_penalty += 4.0
            malefic_tags.append(f"{nm} in 11th – social drag")
        for other, asp, phase in _iter_aspects(aspects_list, nm):
            if other in {"Mercury", "Moon"} or other == L1:
                if asp in HARD_ASPECTS and "apply" in phase:
                    malefic_penalty += 2.5
                    malefic_tags.append(f"{nm} hard applying to {other}")
    malefic_penalty = min(10.0, malefic_penalty)
    score -= malefic_penalty
    if malefic_tags:
        tags.extend(malefic_tags)

    # Creative spark (5th house minor bonus)
    fifth_bonus = 0.0
    benefic_fifth = _planets_in_house(BENEFICS, planets, cusps, 5)
    if benefic_fifth:
        fifth_bonus += 3.0
        tags.append(f"Benefic in 5th ({', '.join(benefic_fifth)}) – content appeal")
    sign_5 = _sign_from_lon(cusps[4]) if len(cusps) >= 5 else None
    L5 = TRAD_RULER.get(sign_5) if sign_5 else None
    if L5 and L5 in planets:
        r5 = planets[L5]
        r5_house = _planet_house(r5, cusps)
        if r5_house in {1, 5, 10, 11}:
            fifth_bonus += 1.5
            tags.append("5th ruler ties into spotlight houses")
        if bool(r5.get("retrograde")):
            fifth_bonus -= 1.5
            tags.append("5th ruler retrograde – creative hesitancy")

    score += fifth_bonus

    # Natal integration (optional)
    natal_cd = opts.get("natal_cd") if isinstance(opts.get("natal_cd"), dict) else None
    natal_cusps = opts.get("natal_cusps") if isinstance(opts.get("natal_cusps"), list) else None
    try:
        sr_windows = list(opts.get("sr_windows") or [])
    except Exception:
        sr_windows = []
    try:
        lr_list = list(opts.get("lr_list") or [])
    except Exception:
        lr_list = []
    integrated = bool(natal_cd or natal_cusps or natal_hits or sr_windows or lr_list)
    natal_tags: List[str] = []
    if integrated:
        natal_planets: Dict[str, Dict[str, Any]] = _collect_planets(natal_cd) if natal_cd else {}
        if natal_cusps and isinstance(natal_cusps, list) and len(natal_cusps) >= 11:
            try:
                natal_11_lon = float(natal_cusps[10] % 360.0)
                asc_lon = float(cusps[0] % 360.0)
                if _ang_sep(asc_lon, natal_11_lon) <= 5.0:
                    score += 4.0
                    natal_tags.append("Election Asc near natal 11th cusp (+4)")
            except Exception:
                pass
        natal_bonus = 0.0
        fav_hits = 0
        warn_hits = 0
        if natal_hits:
            social_tokens = ("c11", "h11", "11th", "c3", "h3", "3rd", "c5", "h5", "5th", "mercury", "venus", "mc")
            caution_tokens = ("c12", "h12", "c6", "h6", "c8", "h8", "asc")
            for hit in natal_hits[:25]:
                try:
                    tr = str(hit.get("transiting") or "")
                    tgt = str(hit.get("target_label") or hit.get("natal") or "").lower()
                    asp = str(hit.get("aspect") or "")
                    if tr in BENEFICS and asp in SOFT_ASPECTS:
                        if any(tok in tgt for tok in social_tokens):
                            fav_hits += 1
                    if tr in MALEFICS and asp in HARD_ASPECTS:
                        if any(tok in tgt for tok in caution_tokens) or "c11" in tgt or "c3" in tgt or "c5" in tgt:
                            warn_hits += 1
                except Exception:
                    continue
        if fav_hits:
            natal_bonus += min(10.0, fav_hits * 3.0)
            natal_tags.append(f"Transit hits boosting natal social houses (+{min(10.0, fav_hits * 3.0):.1f})")
        if warn_hits:
            natal_bonus -= min(8.0, warn_hits * 3.0)
            natal_tags.append(f"Malefic hits touching natal angles (-{min(8.0, warn_hits * 3.0):.1f})")
        try:
            if sr_windows and cur_ts is not None:
                if any(a <= cur_ts <= b for (a, b) in sr_windows):
                    natal_bonus += 2.0
                    natal_tags.append("Solar return window active (+2)")
            if lr_list and cur_ts is not None:
                nearest = min(abs((cur_ts - t).total_seconds()) for t in lr_list)
                if nearest <= 12 * 3600:
                    natal_bonus += 2.0
                    natal_tags.append("Near lunar return (+2)")
                elif nearest <= 48 * 3600:
                    natal_bonus += 1.0
                    natal_tags.append("Within 48h of lunar return (+1)")
        except Exception:
            pass
        # Natal promise sanity check – ensure 11th isn't severely afflicted
        try:
            natal_11_sign = _sign_from_lon(natal_cusps[10]) if natal_cusps and len(natal_cusps) >= 11 else None
            natal_L11 = TRAD_RULER.get(natal_11_sign) if natal_11_sign else None
            if natal_L11 and natal_L11 in natal_planets:
                nat_r11 = natal_planets[natal_L11]
                r11_house = int(nat_r11.get("house")) if nat_r11.get("house") is not None else None
                if r11_house in {6, 8, 12}:
                    natal_bonus -= 2.5
                    natal_tags.append("Natal 11th ruler cadent – temper expectations")
        except Exception:
            pass
        score += natal_bonus
        if not (natal_cd and natal_cusps):
            tags.append("Natal overlay active but natal chart data incomplete – add a saved snap")
            score -= 4.0

    if integrated and natal_tags:
        tags.extend(natal_tags)

    # Trendy MC frosting (small bonuses)
    if mc_sign in {"Leo", "Libra", "Aquarius"}:
        score += 1.0
        tags.append(f"MC in {mc_sign} – public appeal boost")

    final_score = _clamp(score, -100.0, 100.0)
    return Score(value=round(final_score, 2), tags=tags)


__all__ = ["score_viral_content_election"]
