from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import (
    Score,
    FIXED_SIGNS, CARDINAL_SIGNS, BENEFICS, MALEFICS,
    ANGULAR_HOUSES, SUCCEDENT_HOUSES, CADENT_HOUSES,
    TRAD_RULER,
    HI_EXALTATION, HI_TRIPLICITY, _hi_element,
    compute_sect_info, compute_morin_combustion,
    _safe_float,
    _sign_from_lon, _house_cusps, _collect_planets, _house_from_lon, _get_aspects_list, _ang_sep, _is_waxing,
)

# Business-specific dignities and helpers
JUPITER_DOMICILES = {"Sagittarius", "Pisces"}
JUPITER_EXALTATION = "Cancer"
JUPITER_DETRIMENTS = {"Gemini", "Virgo"}
JUPITER_FALL = "Capricorn"


def score_business_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Score election for starting a business (isolated model)."""
    score = 0.0
    tags: List[str] = []

    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)

    # Context
    asc_sign: Optional[str] = None
    mc_sign: Optional[str] = None
    try:
        if len(cusps) >= 10:
            asc_sign = _sign_from_lon(cusps[0])
            mc_sign = _sign_from_lon(cusps[9])
    except Exception:
        pass

    natal_cd = None
    sr_windows = list((options or {}).get('sr_windows') or [])
    lr_list = list((options or {}).get('lr_list') or [])
    cur_ts = (options or {}).get('current_timestamp')
    natal_cusps_opt = (options or {}).get('natal_cusps')
    natal_asc_sign = (options or {}).get('natal_asc_sign')
    natal_asc_well = bool((options or {}).get('natal_asc_well')) if options else False
    try:
        natal_cd = (options or {}).get('natal_cd') if options else None
    except Exception:
        natal_cd = None

    # Combustion/under-beams status when timestamp available
    combust_map: Dict[str, str] = {}
    try:
        if compute_morin_combustion is not None and cur_ts is not None:
            rows = compute_morin_combustion(election_cd if isinstance(election_cd, dict) else {}, cur_ts.isoformat())
            for r in rows or []:
                nm = str(r.get('planet') or '')
                st = str(r.get('status') or '')
                if nm:
                    combust_map[nm] = st
    except Exception:
        combust_map = {}

    # 1) Ascendant quality
    if asc_sign in FIXED_SIGNS:
        score += 1.0; tags.append(f'Fixed Asc ({asc_sign})')
    elif asc_sign in CARDINAL_SIGNS:
        score += 0.5; tags.append('Cardinal Asc (initiative)')

    # MC sign preferences (small)
    try:
        if mc_sign:
            if mc_sign in ("Capricorn", "Taurus"):
                score += 0.3; tags.append(f'MC sign preference ({mc_sign})')
            elif mc_sign in ("Leo", "Libra"):
                score += 0.2; tags.append(f'MC sign preference ({mc_sign})')
    except Exception:
        pass

    # Mercury — commerce/contracts engine
    try:
        me = planets.get('Mercury')
        aspects_list = _get_aspects_list(election_cd) or []
        if me:
            lon_me = _safe_float(me.get('longitude'))
            if bool(me.get('retrograde')):
                score -= 3.5; tags.append('Mercury retrograde (business risk)')
            m_sign = str(me.get('sign') or '')
            if not m_sign and lon_me is not None:
                m_sign = _sign_from_lon(lon_me)
            if m_sign in ("Gemini","Virgo"):
                score += 1.5; tags.append('Mercury dignified')
            elif m_sign in ("Sagittarius","Pisces"):
                score -= 1.5; tags.append('Mercury in detriment/fall')
            mh = int(me.get('house')) if me.get('house') is not None else _house_from_lon(lon_me, cusps) if lon_me is not None else None
            if mh in (1, 3, 9, 10, 11):
                score += 1.0; tags.append('Mercury well placed')
            st_me = combust_map.get('Mercury')
            if st_me == 'combust':
                score -= 1.2; tags.append('Mercury combust')
            elif st_me == 'under_beams':
                score -= 0.6; tags.append('Mercury under beams')
            # Aspects
            for a in aspects_list:
                try:
                    p1 = str(a.get('planet1') or a.get('p1') or '')
                    p2 = str(a.get('planet2') or a.get('p2') or '')
                    asp = str(a.get('aspect') or '')
                    ph = str(a.get('phase') or '').lower()
                    pair = {p1, p2}
                    if 'Mercury' in pair:
                        other = (pair - {'Mercury'}).pop()
                        if other in BENEFICS and asp in ('Conjunction','Trine','Sextile') and ('apply' in ph or ph == 'applying' or not ph):
                            score += 0.8; tags.append('Mercury soft to benefic')
                        if other in MALEFICS and asp in ('Conjunction','Square','Opposition') and ('apply' in ph or ph == 'applying'):
                            score -= 1.2; tags.append('Mercury hard to malefic')
                except Exception:
                    continue
    except Exception:
        pass

    # Asc degree nuance
    try:
        if len(cusps) >= 1:
            asc_lon = float(cusps[0] % 360.0)
            deg_in_sign = asc_lon % 30.0
            if 10.0 <= deg_in_sign <= 20.0:
                score += 0.2; tags.append('Asc middle decan (stable)')
            if deg_in_sign >= 29.0:
                score -= 0.5; tags.append('Asc anaretic (29°)')
            if deg_in_sign <= 1.0:
                score -= 0.2; tags.append('Asc very early (0–1°)')
    except Exception:
        pass

    # Asc ruler
    try:
        if asc_sign:
            r1 = TRAD_RULER.get(asc_sign)
            if r1 and r1 in planets:
                pr = planets[r1]
                lon = _safe_float(pr.get('longitude'))
                h = int(pr.get('house')) if pr.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
                if h in ANGULAR_HOUSES:
                    score += 2.0; tags.append('ASC ruler angular')
                elif h in SUCCEDENT_HOUSES:
                    score += 1.0; tags.append('ASC ruler succedent')
                elif h in CADENT_HOUSES:
                    score -= 1.0; tags.append('ASC ruler cadent')
                if bool(pr.get('retrograde')):
                    score -= 2.0; tags.append('ASC ruler retrograde')
                st = combust_map.get(r1)
                if st == 'combust':
                    score -= 1.5; tags.append('ASC ruler combust')
                elif st == 'under_beams':
                    score -= 0.6; tags.append('ASC ruler under beams')
                try:
                    r1_sign = str(pr.get('sign') or '')
                    if not r1_sign and lon is not None:
                        r1_sign = _sign_from_lon(lon)
                    if TRAD_RULER.get(r1_sign) == r1:
                        score += 1.0; tags.append('ASC ruler dignified')
                    elif HI_EXALTATION.get(r1_sign) == r1:
                        score += 1.0; tags.append('ASC ruler exalted')
                    else:
                        elem = _hi_element(r1_sign)
                        if elem in HI_TRIPLICITY:
                            is_day = False
                            if compute_sect_info is not None:
                                try:
                                    sec = compute_sect_info(election_cd)
                                    cs = str(sec.get('chart_sect') or '')
                                    is_day = (cs == 'diurnal')
                                except Exception:
                                    is_day = False
                            if elem == 'Fire' or elem == 'Air':
                                score += 0.6 if is_day else 0.3
                            elif elem == 'Earth':
                                score += 0.4
                            elif elem == 'Water':
                                score += 0.2
                except Exception:
                    pass
    except Exception:
        pass

    # Near-eclipse penalty (Sun/Moon within 1° of a Node)
    try:
        def _get_node_lons() -> List[float]:
            out: List[float] = []
            nn = planets.get('North Node') or planets.get('Node')
            if nn:
                lon_nn = _safe_float(nn.get('longitude'))
                if lon_nn is not None:
                    out.append(lon_nn % 360.0)
            sn = planets.get('South Node')
            if sn:
                lon_sn = _safe_float(sn.get('longitude'))
                if lon_sn is not None:
                    out.append(lon_sn % 360.0)
            if len(out) == 1:
                out.append((out[0] + 180.0) % 360.0)
            return out
        node_lons = _get_node_lons()
        sun = planets.get('Sun'); moon = planets.get('Moon')
        if node_lons and sun:
            sl = _safe_float(sun.get('longitude'))
            if sl is not None:
                sl = sl % 360.0
                if any(_ang_sep(sl, nl) <= 1.0 for nl in node_lons):
                    score -= 2.0; tags.append('Near eclipse: Sun near Node (≤1°)')
        if node_lons and moon:
            ml = _safe_float(moon.get('longitude'))
            if ml is not None:
                ml = ml % 360.0
                if any(_ang_sep(ml, nl) <= 1.0 for nl in node_lons):
                    score -= 2.0; tags.append('Near eclipse: Moon near Node (≤1°)')
    except Exception:
        pass

    # 2) 10th house business focus
    try:
        if mc_sign:
            L10 = TRAD_RULER.get(mc_sign)
            if L10 and L10 in planets:
                pr = planets[L10]
                lon = _safe_float(pr.get('longitude'))
                h = int(pr.get('house')) if pr.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
                if h in ANGULAR_HOUSES: score += 2.0; tags.append('MC ruler angular')
                elif h in SUCCEDENT_HOUSES: score += 1.0; tags.append('MC ruler succedent')
                elif h in CADENT_HOUSES: score -= 1.0; tags.append('MC ruler cadent')
                if bool(pr.get('retrograde')): score -= 1.5; tags.append('MC ruler retrograde')
    except Exception:
        pass

    # Benefics in angles (esp. 10th) and Sun authority in 10th
    for nm in ('Jupiter','Venus'):
        try:
            info = planets.get(nm)
            if not info: continue
            lon = _safe_float(info.get('longitude'))
            h = int(info.get('house')) if info.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if h == 10: score += 2.5; tags.append(f'{nm} in 10th')
            elif h in (1,7,4): score += 1.0; tags.append(f'{nm} in {h}th')
        except Exception:
            continue
    try:
        sun = planets.get('Sun')
        if sun:
            lon = _safe_float(sun.get('longitude'))
            h = int(sun.get('house')) if sun.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if h == 10:
                score += 1.0; tags.append('Sun in 10th (authority)')
    except Exception:
        pass

    # Jupiter condition and aspects to angles
    try:
        j = planets.get('Jupiter'); sun = planets.get('Sun')
        if j:
            j_lon = _safe_float(j.get('longitude'))
            jsign = str(j.get('sign') or '')
            if not jsign and j_lon is not None:
                jsign = _sign_from_lon(j_lon)
            jh = int(j.get('house')) if j.get('house') is not None else _house_from_lon(j_lon, cusps) if j_lon is not None else None
            if jh in ANGULAR_HOUSES: score += 1.0; tags.append('Jupiter angular')
            if jsign in JUPITER_DOMICILES or jsign == JUPITER_EXALTATION: score += 1.5; tags.append('Jupiter dignified')
            if jsign in JUPITER_DETRIMENTS or jsign == JUPITER_FALL: score -= 0.8; tags.append('Jupiter debilitated')
            if bool(j.get('retrograde')): score -= 0.8; tags.append('Jupiter retrograde')
            try:
                if len(cusps) >= 10 and j_lon is not None:
                    mc_lon = float(cusps[9] % 360.0); jl = j_lon % 360.0
                    d = abs((((jl - mc_lon) + 180.0) % 360.0) - 180.0)
                    if abs(d - 120.0) <= 6.0 or abs(d - 60.0) <= 6.0 or d <= 6.0:
                        score += 1.0; tags.append('Jupiter soft to MC')
                if len(cusps) >= 1 and j_lon is not None:
                    asc_lon = float(cusps[0] % 360.0); jl = j_lon % 360.0
                    d2 = abs((((jl - asc_lon) + 180.0) % 360.0) - 180.0)
                    if abs(d2 - 120.0) <= 6.0 or abs(d2 - 60.0) <= 6.0 or d2 <= 6.0:
                        score += 0.6; tags.append('Jupiter soft to Asc')
            except Exception:
                pass
    except Exception:
        pass

    # Venus soft to angles
    try:
        v = planets.get('Venus')
        if v and len(cusps) >= 10:
            vl = _safe_float(v.get('longitude'))
            if vl is not None:
                mc_lon = float(cusps[9] % 360.0)
                diff = abs((((vl % 360.0 - mc_lon) + 180.0) % 360.0) - 180.0)
                if diff <= 6.0 or abs(diff-60.0) <= 6.0 or abs(diff-120.0) <= 6.0:
                    score += 0.6; tags.append('Venus soft to MC')
        if v and len(cusps) >= 1:
            vl = _safe_float(v.get('longitude'))
            if vl is not None:
                asc_lon = float(cusps[0] % 360.0)
                diff2 = abs((((vl % 360.0 - asc_lon) + 180.0) % 360.0) - 180.0)
                if diff2 <= 6.0 or abs(diff2-60.0) <= 6.0 or abs(diff2-120.0) <= 6.0:
                    score += 0.6; tags.append('Venus soft to Asc')
    except Exception:
        pass

    # 2b) 2nd house resources
    try:
        if len(cusps) >= 2:
            c2_sign = _sign_from_lon(float(cusps[1]))
            L2 = TRAD_RULER.get(c2_sign)
            if L2 and L2 in planets:
                p2 = planets[L2]
                lon2 = _safe_float(p2.get('longitude'))
                h2 = int(p2.get('house')) if p2.get('house') is not None else _house_from_lon(lon2, cusps) if lon2 is not None else None
                if h2 in ANGULAR_HOUSES: score += 1.5; tags.append('2nd ruler angular')
                elif h2 in SUCCEDENT_HOUSES: score += 0.8; tags.append('2nd ruler succedent')
                elif h2 in CADENT_HOUSES: score -= 0.5; tags.append('2nd ruler cadent')
                if bool(p2.get('retrograde')): score -= 1.0; tags.append('2nd ruler retrograde')
                st2 = combust_map.get(L2)
                if st2 == 'combust': score -= 1.0; tags.append('2nd ruler combust')
                try:
                    if lon2 is not None and len(cusps) >= 10:
                        mc_lon = float(cusps[9] % 360.0)
                        dmc = _ang_sep(lon2 % 360.0, mc_lon)
                        if dmc <= 6.0 or abs(dmc-60.0) <= 6.0 or abs(dmc-120.0) <= 6.0:
                            score += 0.6; tags.append('2nd ruler soft to MC')
                    if lon2 is not None and mc_sign:
                        L10r = TRAD_RULER.get(mc_sign)
                        if L10r and L10r in planets:
                            l10lon = _safe_float(planets[L10r].get('longitude'))
                            if l10lon is not None:
                                dL = _ang_sep(lon2 % 360.0, l10lon % 360.0)
                                if dL <= 6.0 or abs(dL-60.0) <= 6.0 or abs(dL-120.0) <= 6.0:
                                    score += 0.6; tags.append('2nd ruler soft to L10')
                except Exception:
                    pass
            # Benefics in 2nd
            for nm in ('Jupiter','Venus'):
                try:
                    info = planets.get(nm)
                    if not info: continue
                    lon = _safe_float(info.get('longitude'))
                    h = int(info.get('house')) if info.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
                    if h == 2: score += 0.8; tags.append(f'{nm} in 2nd')
                except Exception:
                    continue
    except Exception:
        pass

    # 3) Moon condition for momentum
    try:
        m = planets.get('Moon'); s = planets.get('Sun')
        if m and s:
            ml = _safe_float(m.get('longitude'))
            sl = _safe_float(s.get('longitude'))
            if ml is not None and sl is not None:
                waxing = _is_waxing(ml, sl)
                if waxing is True:
                    score += 0.5; tags.append('Moon waxing')
                elif waxing is False:
                    tags.append('Moon waning')
            # House preference
            mh = int(m.get('house')) if m.get('house') is not None else _house_from_lon(ml, cusps) if ml is not None else None
            if isinstance(mh, int):
                if mh in (10,11): score += 1.0; tags.append('Moon in 10th/11th')
                elif mh == 2: score += 0.8; tags.append('Moon in 2nd')
                elif mh in (6,8,12): score -= 1.0; tags.append('Moon in 6/8/12')
            # Next applying aspect
            na = election_cd.get('moon_next_aspect')
            if isinstance(na, dict):
                pn = str(na.get('planet') or '')
                asp = str(na.get('aspect') or '')
                if pn in BENEFICS and asp in ('Trine','Sextile','Conjunction'):
                    score += 1.0; tags.append(f"Moon applying {asp} to {pn}")
                if pn in MALEFICS and asp in ('Square','Opposition','Conjunction'):
                    score -= 1.5; tags.append(f"Moon applying {asp} to {pn}")
    except Exception:
        pass

    # 4) Weekday timing (optional small)
    try:
        if (options or {}).get('include_traditional_timing') and cur_ts is not None:
            wd = int(cur_ts.isoweekday())  # 1..7
            if wd in (4,5,7,3):
                score += 0.2; tags.append('Traditional weekday boost')
        # Optional Planetary day/hour boost when supplied by caller
        day_ruler = ((options or {}).get('day_ruler') or '').strip()
        hour_ruler = ((options or {}).get('hour_ruler') or '').strip()
        favored = {'Jupiter','Venus','Mercury'}
        if day_ruler in favored:
            score += 0.2; tags.append(f'Planetary day: {day_ruler}')
        if hour_ruler in favored:
            score += 0.2; tags.append(f'Planetary hour: {hour_ruler}')
    except Exception:
        pass

    # 5) Business mode tweaks. These must vary with chart conditions; a
    # constant added to every timestamp cannot alter election ranking.
    try:
        mode = str((options or {}).get('business_mode') or '').strip().lower()
        if mode == 'conservative':
            risk_tokens = (
                'retrograde', 'combust', 'under beams', 'afflict', '6/8/12',
                'malefic', 'via combusta', 'eclipse',
            )
            risk_count = sum(
                1 for tag in tags
                if any(token in str(tag).lower() for token in risk_tokens)
            )
            if risk_count:
                adjustment = min(2.0, 0.35 * risk_count)
                score -= adjustment
                tags.append(f'Conservative risk adjustment (-{adjustment:.2f})')
        elif mode == 'growth':
            growth = 0.0
            jupiter = planets.get('Jupiter') or {}
            jupiter_house = (
                int(jupiter.get('house'))
                if jupiter.get('house') is not None
                else _house_from_lon(_safe_float(jupiter.get('longitude')), cusps)
                if _safe_float(jupiter.get('longitude')) is not None
                else None
            )
            if jupiter_house in (2, 10, 11):
                growth += 0.7
            if jupiter and not bool(jupiter.get('retrograde')):
                growth += 0.2
            moon = planets.get('Moon') or {}
            sun = planets.get('Sun') or {}
            moon_lon = _safe_float(moon.get('longitude'))
            sun_lon = _safe_float(sun.get('longitude'))
            if moon_lon is not None and sun_lon is not None and _is_waxing(moon_lon, sun_lon) is True:
                growth += 0.5
            if growth:
                score += growth
                tags.append(f'Growth conditions (+{growth:.2f})')
        if (options or {}).get('emphasize_commerce'):
            commerce = 0.0
            mercury = planets.get('Mercury') or {}
            mercury_house = (
                int(mercury.get('house'))
                if mercury.get('house') is not None
                else _house_from_lon(_safe_float(mercury.get('longitude')), cusps)
                if _safe_float(mercury.get('longitude')) is not None
                else None
            )
            if mercury:
                commerce += -0.8 if bool(mercury.get('retrograde')) else 0.25
            if mercury_house in (1, 2, 3, 10, 11):
                commerce += 0.45
            mercury_sign = str(mercury.get('sign') or '')
            if mercury_sign in {'Gemini', 'Virgo'}:
                commerce += 0.45
            if commerce:
                score += commerce
                tags.append(f'Commerce conditions ({commerce:+.2f})')
    except Exception:
        pass

    # Optional fixed stars
    try:
        if (options or {}).get('include_fixed_stars'):
            from fixed_stars import compute_fixed_star_hits
            hits_fs = compute_fixed_star_hits(election_cd if isinstance(election_cd, dict) else {}, orb_deg=1.0, check_planets=['Moon','Venus','Jupiter','Mercury','Sun'], include_cusps=True)
            good = {'Regulus','Spica','Aldebaran','Fomalhaut'}; bad = {'Algol','Antares','Scheat'}
            for h in hits_fs or []:
                star = str(h.get('star') or '')
                tgt = str(h.get('target_label') or h.get('target') or '')
                if tgt in ('Asc','MC','Moon','Venus','Jupiter','Sun'):
                    if star in good:
                        score += 0.4; tags.append(f'Fixed star {star} on {tgt}')
                    if star in bad:
                        score -= 0.6; tags.append(f'Fixed star {star} on {tgt}')
    except Exception:
        pass

    # Optional Part of Fortune
    try:
        lots = election_cd.get('arabic_parts') if isinstance(election_cd.get('arabic_parts'), dict) else None
        if not isinstance(lots, dict):
            from arabic_parts import compute_arabic_parts

            lots = compute_arabic_parts(election_cd if isinstance(election_cd, dict) else {}) or {}
        pof = lots.get('fortune') or lots.get('Part of Fortune') or lots.get('Fortuna') or lots.get('Fortune')
        if isinstance(pof, dict):
            lon = _safe_float(pof.get('longitude') if pof.get('longitude') is not None else pof.get('lon'))
            h = int(pof.get('house')) if pof.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if isinstance(h, int) and h in (1,2,10,11):
                score += 0.6; tags.append('Part of Fortune in 1/2/10/11')
            # Benefic aspects to Part of Fortune (soft) — Jupiter/Venus
            if lon is not None:
                for nm in ('Jupiter','Venus'):
                    p = planets.get(nm)
                    if not p: continue
                    pl = _safe_float(p.get('longitude'))
                    if pl is None:
                        continue
                    d = _ang_sep(lon % 360.0, pl % 360.0)
                    if d <= 6.0 or abs(d-60.0) <= 6.0 or abs(d-120.0) <= 6.0:
                        score += 0.4; tags.append(f'{nm} soft to Part of Fortune')
    except Exception:
        pass

    # 10) Natal enrichment
    if natal_hits:
        try:
            bonus = 0.0; pen = 0.0
            for h in natal_hits[:15]:
                tr = str(h.get('transiting') or '')
                tgt = str(h.get('target_label') or h.get('natal') or '')
                asp = str(h.get('aspect') or '')
                towards_business = ('MC' in tgt) or tgt.endswith('C10') or tgt.endswith('C2') or (' C10' in tgt) or (' C2' in tgt)
                towards_angles = (tgt in ('Asc','MC','C1','C10'))
                if tr in BENEFICS and asp in ('Conjunction','Trine','Sextile') and (towards_business or towards_angles):
                    bonus += 0.6
                if tr in MALEFICS and asp in ('Conjunction','Square','Opposition') and (towards_business or towards_angles):
                    pen += 0.8
            if bonus or pen:
                score += (bonus - pen); tags.append('Directions proxy (business)')
        except Exception:
            pass

    try:
        if sr_windows and cur_ts is not None:
            in_sr = any(a <= cur_ts <= b for (a,b) in sr_windows)
            if in_sr: score += 0.4; tags.append('SR window (business)')
        if lr_list and cur_ts is not None:
            dd = min(abs((cur_ts - t).total_seconds()) for t in lr_list)
            if dd <= 12*3600: score += 0.3; tags.append('Near LR (≤12h)')
            elif dd <= 48*3600: score += 0.1; tags.append('Near LR (≤48h)')
    except Exception:
        pass

    # Natal promise gate
    try:
        if natal_cd and isinstance(natal_cd, dict):
            natal_cusps = natal_cd.get('house_cusps') or natal_cd.get('houses')
            natal_pl = natal_cd.get('planets') or {}
            pl_map = {}
            if isinstance(natal_pl, dict):
                pl_map = {k:v for k,v in natal_pl.items() if isinstance(v, dict)}
            elif isinstance(natal_pl, list):
                for v in natal_pl:
                    if isinstance(v, dict) and v.get('planet'): pl_map[str(v['planet'])] = v
            def _house_of_nat(nm: str) -> Optional[int]:
                try:
                    p = pl_map.get(nm)
                    if not p: return None
                    lon = _safe_float(p.get('longitude'))
                    if p.get('house') is not None:
                        return int(p.get('house'))
                    if lon is not None and isinstance(natal_cusps, list) and len(natal_cusps) >= 12:
                        return _house_from_lon(lon, natal_cusps)
                    return None
                except Exception:
                    return None
            nat_mc_sign = None; nat_2_sign = None
            if isinstance(natal_cusps, list) and len(natal_cusps) >= 10:
                nat_mc_sign = _sign_from_lon(float(natal_cusps[9]))
                nat_2_sign = _sign_from_lon(float(natal_cusps[1]))
            strong = 0; weak = 0
            for nm in ('Jupiter','Venus'):
                hh = _house_of_nat(nm)
                if isinstance(hh, int) and (hh in ANGULAR_HOUSES or hh in SUCCEDENT_HOUSES):
                    strong += 1
                if pl_map.get(nm) and bool(pl_map[nm].get('retrograde')):
                    weak += 1
            for sign in (nat_mc_sign, nat_2_sign):
                if not sign: continue
                R = TRAD_RULER.get(sign)
                if R and R in pl_map:
                    hh = _house_of_nat(R)
                    if isinstance(hh, int) and (hh in ANGULAR_HOUSES or hh in SUCCEDENT_HOUSES):
                        strong += 1
                    if bool(pl_map[R].get('retrograde')):
                        weak += 1
            if mc_sign and nat_mc_sign and mc_sign == nat_mc_sign:
                score += 0.6; tags.append('Election MC sign == natal MC sign')
            mult = 1.0
            if strong == 0 and weak >= 2:
                mult = 0.4; tags.append('Natal business promise weak — capping score')
            elif strong >= 2 and weak == 0:
                mult = 1.0
            else:
                mult = 0.8
            score = score * mult
    except Exception:
        pass

    return Score(value=round(score, 2), tags=tags)

__all__ = ['score_business_election']
