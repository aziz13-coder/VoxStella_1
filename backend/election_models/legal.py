from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from .common import (
    Score,
    BENEFICS, MALEFICS,
    ANGULAR_HOUSES, SUCCEDENT_HOUSES, CADENT_HOUSES,
    TRAD_RULER,
    CARDINAL_SIGNS, FIXED_SIGNS,
    HI_EXALTATION, HI_TRIPLICITY, _hi_element,
    compute_morin_combustion,
    _collect_planets, _house_cusps, _house_from_lon, _sign_from_lon,
    _get_aspects_list, _ang_sep, _is_waxing,
)

SOFT_ASPECTS = {"Conjunction", "Trine", "Sextile"}
HARD_ASPECTS = {"Square", "Opposition", "Conjunction"}

IDEAL_ASC_SIGNS = CARDINAL_SIGNS


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
        if _planet_house(planets.get(nm), cusps) == target:
            hits.append(nm)
    return hits


def _iter_aspects(aspects: Optional[List[Dict[str, Any]]], center: str) -> Iterable[Tuple[str, str, str]]:
    if not aspects:
        return []
    rows: List[Tuple[str, str, str]] = []
    for row in aspects:
        try:
            p1 = str(row.get("planet1") or row.get("p1") or "")
            p2 = str(row.get("planet2") or row.get("p2") or "")
            if center not in {p1, p2}:
                continue
            other = p2 if p1 == center else p1
            asp = str(row.get("aspect") or "")
            phase_raw = row.get("phase") or row.get("motion")
            if phase_raw in (None, "") and row.get("applying") is not None:
                phase_raw = "applying" if bool(row.get("applying")) else "separating"
            phase = str(phase_raw or "").lower()
            rows.append((other, asp, phase))
        except Exception:
            continue
    return rows


def _combustion_status(planet: str, combust_map: Dict[str, str]) -> str:
    try:
        return str(combust_map.get(planet) or "").lower()
    except Exception:
        return ""


def _clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def score_legal_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Score elections for initiating or responding to legal action."""

    opts = options or {}
    action = str(opts.get("legal_action") or "filing").strip().lower()

    if natal_hits is None:
        natal_hits = opts.get("natal_hits")

    raw_natal_cd = opts.get("natal_cd")
    natal_cd = raw_natal_cd if isinstance(raw_natal_cd, dict) else None
    raw_natal_cusps = opts.get("natal_cusps")
    natal_cusps = raw_natal_cusps if isinstance(raw_natal_cusps, list) else None
    try:
        sr_windows = list(opts.get("sr_windows") or [])
    except Exception:
        sr_windows = []
    try:
        lr_list = list(opts.get("lr_list") or [])
    except Exception:
        lr_list = []
    integrated = bool(natal_cd or natal_cusps or natal_hits or sr_windows or lr_list)

    score = 0.0
    tags: List[str] = []

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

    # 1) Ascendant & 1st house (max ~30)
    asc_section = 0.0
    asc_tags: List[str] = []
    if asc_sign in IDEAL_ASC_SIGNS:
        asc_section += 5.0
        asc_tags.append(f"Cardinal Asc ({asc_sign}) – swift action")
    elif asc_sign in FIXED_SIGNS:
        asc_section -= 2.5
        asc_tags.append(f"Fixed Asc ({asc_sign}) – slower proceedings")
    benefic_first = _planets_in_house(BENEFICS, planets, cusps, 1)
    if benefic_first:
        asc_section += 4.0
        asc_tags.append(f"Benefic in 1st ({', '.join(benefic_first)})")
    malefic_first = _planets_in_house(MALEFICS, planets, cusps, 1)
    if malefic_first:
        asc_section -= 5.0
        asc_tags.append(f"Malefic in 1st ({', '.join(malefic_first)}) – exposes you")

    L1 = TRAD_RULER.get(asc_sign) if asc_sign else None
    asc_ruler_score = 0.0
    if L1 and L1 in planets:
        pr = planets[L1]
        h = _planet_house(pr, cusps)
        if h in ANGULAR_HOUSES:
            asc_ruler_score += 8.0
            asc_tags.append("ASC ruler angular")
        elif h in SUCCEDENT_HOUSES:
            asc_ruler_score += 4.0
            asc_tags.append("ASC ruler succedent")
        elif h in CADENT_HOUSES:
            asc_ruler_score -= 6.0
            asc_tags.append("ASC ruler cadent")
        if bool(pr.get("retrograde")):
            asc_ruler_score -= 8.0
            asc_tags.append("ASC ruler retrograde – weak standing")
        status = _combustion_status(L1, combust_map)
        if status == "combust":
            asc_ruler_score -= 6.0
            asc_tags.append("ASC ruler combust")
        elif status == "under_beams":
            asc_ruler_score -= 2.5
            asc_tags.append("ASC ruler under beams")
        try:
            r_sign = str(pr.get("sign") or _sign_from_lon(float(pr.get("longitude"))))
            if TRAD_RULER.get(r_sign) == L1:
                asc_ruler_score += 5.0
                asc_tags.append("ASC ruler dignified")
            elif HI_EXALTATION.get(r_sign) == L1:
                asc_ruler_score += 3.0
                asc_tags.append("ASC ruler exalted")
            elif HI_TRIPLICITY.get(r_sign):
                asc_ruler_score += 1.0
        except Exception:
            pass
        for other, asp, phase in _iter_aspects(aspects_list, L1):
            if other in BENEFICS and asp in SOFT_ASPECTS:
                bump = 3.0
                if "apply" in phase:
                    bump += 0.5
                asc_ruler_score += bump
                asc_tags.append(f"{L1} soft to {other}")
            if other in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                asc_ruler_score -= 4.0
                asc_tags.append(f"{L1} hard applying to {other}")
        asc_ruler_score = _clamp(asc_ruler_score, -8.0, 15.0)
    else:
        asc_tags.append("ASC ruler missing – uncertain footing")

    asc_section += asc_ruler_score
    asc_section = _clamp(asc_section, -30.0, 30.0)
    score += asc_section
    tags.extend(asc_tags)

    # 2) Moon condition (max ~20)
    moon_section = 0.0
    moon_tags: List[str] = []
    moon = planets.get("Moon")
    sun = planets.get("Sun")
    moon_lon = None
    if moon:
        moon_house = _planet_house(moon, cusps)
        if moon_house in {6, 8, 12}:
            moon_section -= 6.0
            moon_tags.append("Moon in 6/8/12 – avoid")
        elif moon_house in {1, 3, 10, 11}:
            moon_section += 3.0
            moon_tags.append(f"Moon in supportive house ({moon_house})")
        try:
            moon_lon = float(moon.get("longitude"))
        except Exception:
            moon_lon = None
        try:
            moon_sign = str(moon.get("sign") or _sign_from_lon(moon_lon))
        except Exception:
            moon_sign = None
        if moon_sign in CARDINAL_SIGNS:
            moon_section += 1.5
            moon_tags.append("Moon in cardinal sign")
        if moon_sign in FIXED_SIGNS:
            moon_section -= 1.0
        # Waxing check
        if sun and sun.get("longitude") is not None and moon_lon is not None:
            if _is_waxing(moon_lon, float(sun.get("longitude"))):
                moon_section += 2.0
                moon_tags.append("Moon waxing")
            else:
                moon_tags.append("Moon waning")
        # Speed
        try:
            speed = abs(float(moon.get("speed") or moon.get("daily_motion") or 0.0))
            if speed >= 12.5:
                moon_section += 1.5
                moon_tags.append("Moon swift")
            elif speed < 11.0:
                moon_section -= 2.0
                moon_tags.append("Moon slow")
        except Exception:
            pass
        # Void of course
        voc = False
        try:
            cons = election_cd.get("considerations")
            if isinstance(cons, dict) and bool(cons.get("moon_void")):
                voc = True
            if election_cd.get("moon_voc") or election_cd.get("moon_void") or election_cd.get("void_of_course"):
                voc = True
        except Exception:
            pass
        if voc:
            moon_section -= 8.0
            moon_tags.append("Moon void of course")

        # Aspect behaviour
        moon_next = election_cd.get("moon_next_aspect")
        if isinstance(moon_next, dict):
            pn = str(moon_next.get("planet") or "")
            asp = str(moon_next.get("aspect") or "")
            phase_raw = moon_next.get("phase")
            if phase_raw in (None, "") and moon_next.get("applying") is not None:
                phase_raw = "applying" if bool(moon_next.get("applying")) else "separating"
            phase = str(phase_raw or "").lower()
            if pn in BENEFICS and asp in SOFT_ASPECTS:
                moon_section += 4.0
                note = f"Moon applying {asp} to {pn}"
                if "apply" in phase:
                    note += " (applying)"
                moon_tags.append(note)
            if pn in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                moon_section -= 5.0
                moon_tags.append(f"Moon applying {asp} to {pn}")

        # Link to ASC ruler
        if L1 and moon_lon is not None and L1 in planets and planets[L1].get("longitude") is not None:
            sep = _ang_sep(moon_lon, float(planets[L1]["longitude"]))
            soft_orb = min(abs(sep - ang) for ang in (0.0, 60.0, 120.0))
            square_orb = abs(sep - 90.0)
            if soft_orb <= 6.0:
                moon_section += 3.0
                moon_tags.append("Moon connects to ASC ruler")
            elif square_orb <= 6.0:
                moon_section -= 1.0
                moon_tags.append("Moon square ASC ruler")
    else:
        moon_tags.append("Moon missing – incomplete data")

    moon_section = _clamp(moon_section, -10.0, 20.0)
    score += moon_section
    tags.extend(moon_tags)

    # 3) Mars / Saturn dynamics (max ~20 combined)
    mars_section = 0.0
    mars_tags: List[str] = []
    mars = planets.get("Mars")
    if mars:
        m_house = _planet_house(mars, cusps)
        if action in {"filing", "counter"}:
            if m_house in ANGULAR_HOUSES:
                mars_section += 6.0
                mars_tags.append("Mars angular – assertive advantage")
            elif m_house in SUCCEDENT_HOUSES:
                mars_section += 3.0
            elif m_house in CADENT_HOUSES:
                mars_section -= 4.0
            try:
                m_sign = str(mars.get("sign") or _sign_from_lon(float(mars.get("longitude"))))
                if m_sign in {"Aries", "Scorpio"}:
                    mars_section += 4.0
                    mars_tags.append("Mars in domicile")
                elif m_sign == "Capricorn":
                    mars_section += 5.0
                    mars_tags.append("Mars exalted")
                elif m_sign in {"Cancer", "Libra", "Taurus"}:
                    mars_section -= 3.0
                    mars_tags.append("Mars debilitated")
            except Exception:
                pass
            if bool(mars.get("retrograde")):
                mars_section -= 6.0
                mars_tags.append("Mars retrograde – weak offensive")
        else:
            # Defensive posture: prefer Mars contained
            if m_house in {7, 10}:
                mars_section -= 4.0
                mars_tags.append("Mars prominent – inflames conflict")
        status = _combustion_status("Mars", combust_map)
        if status == "combust":
            mars_section -= 4.0
            mars_tags.append("Mars combust")
        elif status == "under_beams":
            mars_section -= 1.5
        for other, asp, phase in _iter_aspects(aspects_list, "Mars"):
            if other == L1 and asp in SOFT_ASPECTS:
                val = 3.0
                if "apply" in phase:
                    val += 1.0
                mars_section += val
                mars_tags.append("Mars supporting ASC ruler")
            if other == "Moon" and asp in HARD_ASPECTS and "apply" in phase:
                mars_section -= 4.0
                mars_tags.append("Mars afflicts Moon")

    saturn_section = 0.0
    saturn_tags: List[str] = []
    saturn = planets.get("Saturn")
    if saturn:
        s_house = _planet_house(saturn, cusps)
        if action == "response":
            if s_house in ANGULAR_HOUSES:
                saturn_section += 4.0
                saturn_tags.append("Saturn angular – defensive spine")
            elif s_house in SUCCEDENT_HOUSES:
                saturn_section += 2.0
            elif s_house in CADENT_HOUSES:
                saturn_section -= 2.0
            if bool(saturn.get("retrograde")):
                saturn_section -= 3.0
                saturn_tags.append("Saturn retrograde – unstable defense")
            status = _combustion_status("Saturn", combust_map)
            if status == "combust":
                saturn_section -= 3.0
                saturn_tags.append("Saturn combust")
        else:
            if s_house == 1:
                saturn_section -= 4.0
                saturn_tags.append("Saturn in 1st – burdens action")
            if s_house == 7:
                saturn_section += 3.0
                saturn_tags.append("Saturn in 7th – hampers opponent")
        for other, asp, phase in _iter_aspects(aspects_list, "Saturn"):
            if other == L1 and asp in HARD_ASPECTS and "apply" in phase:
                saturn_section -= 4.0
                saturn_tags.append("Saturn afflicts ASC ruler")

    mars_saturn_total = _clamp(mars_section + saturn_section, -10.0, 20.0)
    score += mars_saturn_total
    tags.extend(mars_tags)
    tags.extend(saturn_tags)

    # 4) Seventh house (opponent) – encourage weakness
    seventh_diff = 0.0
    seventh_tags: List[str] = []
    sign_7 = _sign_from_lon(cusps[6]) if len(cusps) >= 7 else None
    L7 = TRAD_RULER.get(sign_7) if sign_7 else None
    if L7 and L7 in planets:
        r7 = planets[L7]
        r7_house = _planet_house(r7, cusps)
        if r7_house in CADENT_HOUSES:
            seventh_diff += 6.0
            seventh_tags.append("7th ruler cadent – opponent weakened")
        elif r7_house in ANGULAR_HOUSES:
            seventh_diff -= 6.0
            seventh_tags.append("7th ruler angular – opponent empowered")
        if bool(r7.get("retrograde")):
            seventh_diff += 4.0
            seventh_tags.append("7th ruler retrograde")
        status = _combustion_status(L7, combust_map)
        if status == "combust":
            seventh_diff += 3.0
            seventh_tags.append("7th ruler combust")
        elif status == "under_beams":
            seventh_diff += 1.5
        for other, asp, phase in _iter_aspects(aspects_list, L7):
            if other in BENEFICS and asp in SOFT_ASPECTS and "apply" in phase:
                seventh_diff -= 3.0
                seventh_tags.append("7th ruler receiving benefic support")
            if other in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                seventh_diff += 3.0
                seventh_tags.append("7th ruler afflicted by malefic")

    benefic_seventh = _planets_in_house(BENEFICS, planets, cusps, 7)
    if benefic_seventh:
        seventh_diff -= 5.0
        seventh_tags.append(f"Benefic in 7th ({', '.join(benefic_seventh)}) – opponent fortified")
    malefic_seventh = _planets_in_house(MALEFICS, planets, cusps, 7)
    for mal in malefic_seventh:
        if mal != L1:
            seventh_diff += 4.0
            seventh_tags.append(f"{mal} in 7th – pressures opponent")

    score += _clamp(seventh_diff, -10.0, 15.0)
    tags.extend(seventh_tags)

    # 5) 10th house (judge/court) & 4th (verdict)
    tenth_score = 0.0
    tenth_tags: List[str] = []
    benefic_tenth = _planets_in_house(BENEFICS, planets, cusps, 10)
    if benefic_tenth:
        tenth_score += 5.0
        tenth_tags.append(f"Benefic in 10th ({', '.join(benefic_tenth)}) – judicial favor")
    malefic_tenth = _planets_in_house(MALEFICS, planets, cusps, 10)
    if malefic_tenth:
        tenth_score -= 5.0
        tenth_tags.append(f"Malefic in 10th ({', '.join(malefic_tenth)})")
    sign_10 = _sign_from_lon(cusps[9]) if len(cusps) >= 10 else None
    L10 = TRAD_RULER.get(sign_10) if sign_10 else None
    if L10 and L10 in planets:
        r10 = planets[L10]
        r10_house = _planet_house(r10, cusps)
        if r10_house in ANGULAR_HOUSES:
            tenth_score += 4.0
            tenth_tags.append("10th ruler angular")
        elif r10_house in CADENT_HOUSES:
            tenth_score -= 4.0
        if bool(r10.get("retrograde")):
            tenth_score -= 2.5
            tenth_tags.append("10th ruler retrograde")
        status = _combustion_status(L10, combust_map)
        if status == "combust":
            tenth_score -= 3.0
            tenth_tags.append("10th ruler combust")
        elif status == "under_beams":
            tenth_score -= 1.0
        for other, asp, phase in _iter_aspects(aspects_list, L10):
            if other in BENEFICS and asp in SOFT_ASPECTS:
                tenth_score += 2.0
            if other in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                tenth_score -= 3.0

    score += _clamp(tenth_score, -8.0, 15.0)
    tags.extend(tenth_tags)

    fourth_score = 0.0
    fourth_tags: List[str] = []
    benefic_fourth = _planets_in_house(BENEFICS, planets, cusps, 4)
    if benefic_fourth:
        fourth_score += 3.0
        fourth_tags.append("Benefic in 4th – favorable verdict")
    malefic_fourth = _planets_in_house(MALEFICS, planets, cusps, 4)
    if malefic_fourth:
        fourth_score -= 3.0
        fourth_tags.append("Malefic in 4th – risky verdict")
    score += _clamp(fourth_score, -4.0, 6.0)
    tags.extend(fourth_tags)

    # 6) Mercury & Jupiter (documents & judges)
    mercury_score = 0.0
    mercury_tags: List[str] = []
    mercury = planets.get("Mercury")
    if mercury:
        if bool(mercury.get("retrograde")):
            mercury_score -= 6.0
            mercury_tags.append("Mercury retrograde – legal paperwork risk")
        status = _combustion_status("Mercury", combust_map)
        if status == "combust":
            mercury_score -= 4.0
            mercury_tags.append("Mercury combust")
        mh = _planet_house(mercury, cusps)
        if mh in {1, 3, 9, 10}:
            mercury_score += 2.0
        elif mh in {6, 8, 12}:
            mercury_score -= 2.0
        for other, asp, phase in _iter_aspects(aspects_list, "Mercury"):
            if other in BENEFICS and asp in SOFT_ASPECTS:
                mercury_score += 2.0
            if other in MALEFICS and asp in HARD_ASPECTS and "apply" in phase:
                mercury_score -= 2.5
    jupiter_score = 0.0
    jupiter_tags: List[str] = []
    jupiter = planets.get("Jupiter")
    if jupiter:
        j_house = _planet_house(jupiter, cusps)
        if j_house in {10, 1, 4}:
            jupiter_score += 4.0
            jupiter_tags.append("Jupiter in angular house – favors justice")
        if bool(jupiter.get("retrograde")):
            jupiter_score -= 2.0
            jupiter_tags.append("Jupiter retrograde")

    score += _clamp(mercury_score + jupiter_score, -10.0, 10.0)
    tags.extend(mercury_tags)
    tags.extend(jupiter_tags)

    # 7) Integrated natal analysis
    natal_tags: List[str] = []
    if integrated:
        natal_cusps_list: List[float] = []
        if isinstance(natal_cusps, list):
            try:
                natal_cusps_list = [float(x) for x in natal_cusps[:12]]
            except Exception:
                natal_cusps_list = list(natal_cusps[:12])
        natal_planets: Dict[str, Dict[str, Any]] = _collect_planets(natal_cd) if natal_cd else {}
        natal_strength = 0.0
        natal_risk = 0.0
        nat_sign_1 = _sign_from_lon(natal_cusps_list[0]) if len(natal_cusps_list) >= 1 else None
        nat_sign_7 = _sign_from_lon(natal_cusps_list[6]) if len(natal_cusps_list) >= 7 else None
        nat_sign_10 = _sign_from_lon(natal_cusps_list[9]) if len(natal_cusps_list) >= 10 else None
        nat_L1 = TRAD_RULER.get(nat_sign_1) if nat_sign_1 else None
        nat_L7 = TRAD_RULER.get(nat_sign_7) if nat_sign_7 else None
        nat_L10 = TRAD_RULER.get(nat_sign_10) if nat_sign_10 else None

        def _n_house(r: Optional[str]) -> Optional[int]:
            if not r or r not in natal_planets:
                return None
            try:
                if natal_planets[r].get("house") is not None:
                    return int(natal_planets[r]["house"])
            except Exception:
                pass
            try:
                lon = float(natal_planets[r].get("longitude"))
                return _house_from_lon(lon, natal_cusps_list)
            except Exception:
                return None

        if nat_L1:
            h = _n_house(nat_L1)
            if h in ANGULAR_HOUSES:
                natal_strength += 2.5
            elif h in CADENT_HOUSES:
                natal_risk += 2.5
        if nat_L7:
            h = _n_house(nat_L7)
            if h in ANGULAR_HOUSES:
                natal_risk += 3.0
            elif h in CADENT_HOUSES:
                natal_strength += 2.0
        if nat_L10:
            h = _n_house(nat_L10)
            if h in ANGULAR_HOUSES:
                natal_strength += 2.0

        nat_mars = natal_planets.get("Mars")
        if nat_mars and nat_mars.get("house") is not None:
            h = int(nat_mars.get("house"))
            if h in {10, 1}:
                natal_strength += 2.0
            if bool(nat_mars.get("retrograde")):
                natal_risk += 2.0
        nat_jupiter = natal_planets.get("Jupiter")
        if nat_jupiter and nat_jupiter.get("house") is not None:
            if int(nat_jupiter["house"]) in {10, 4}:
                natal_strength += 1.5

        if natal_strength < 1.0 and natal_risk >= 3.0:
            score -= 20.0
            natal_tags.append("Natal promise weak – action discouraged")
        else:
            score += min(10.0, natal_strength * 2.0)
            if natal_risk:
                score -= min(8.0, natal_risk * 1.5)

        fav_hits = 0
        warn_hits = 0
        if natal_hits:
            for hit in natal_hits[:25]:
                try:
                    tr = str(hit.get("transiting") or "")
                    tgt = str(hit.get("target_label") or hit.get("natal") or "").lower()
                    asp = str(hit.get("aspect") or "")
                    if tr in BENEFICS and asp in SOFT_ASPECTS and any(token in tgt for token in ("c1", "c10", "mc", "asc", "c7")):
                        fav_hits += 1
                    if tr in MALEFICS and asp in HARD_ASPECTS and any(token in tgt for token in ("c1", "c10", "c4", "asc", "mc", "c7")):
                        warn_hits += 1
                except Exception:
                    continue
        if fav_hits:
            gain = min(10.0, fav_hits * 2.5)
            score += gain
            natal_tags.append(f"Directions/Transits favorable (+{gain:.1f})")
        if warn_hits:
            loss = min(10.0, warn_hits * 2.5)
            score -= loss
            natal_tags.append(f"Directions warn (-{loss:.1f})")

        if sr_windows and cur_ts is not None:
            if any(a <= cur_ts <= b for (a, b) in sr_windows):
                score += 2.0
                natal_tags.append("Solar return window active (+2)")
        if lr_list and cur_ts is not None:
            try:
                nearest = min(abs((cur_ts - t).total_seconds()) for t in lr_list)
                if nearest <= 12 * 3600:
                    score += 1.5
                    natal_tags.append("Near lunar return (+1.5)")
                elif nearest <= 48 * 3600:
                    score += 0.5
                    natal_tags.append("Within 48h of lunar return (+0.5)")
            except Exception:
                pass

        if not (natal_cd and natal_cusps):
            score -= 5.0
            natal_tags.append("Natal overlay active but natal chart data incomplete – add a saved snap")

    if integrated and natal_tags:
        tags.extend(natal_tags)

    # 8) Misc penalties for severe malefic hits
    misc_penalty = 0.0
    for mal in ("Mars", "Saturn"):
        p = planets.get(mal)
        if not p:
            continue
        house = _planet_house(p, cusps)
        if house == 10 and mal == "Saturn":
            misc_penalty += 2.0
        if house == 4 and mal == "Mars":
            misc_penalty += 2.5
    score -= misc_penalty

    final_score = _clamp(score, 0.0, 100.0)
    return Score(value=round(final_score, 2), tags=tags)


__all__ = ["score_legal_election"]
