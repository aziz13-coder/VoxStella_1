from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import (
    Score,
    FIXED_SIGNS, CARDINAL_SIGNS, MUTABLE_SIGNS, BENEFICS, MALEFICS,
    ANGULAR_HOUSES, SUCCEDENT_HOUSES, CADENT_HOUSES,
    TRAD_RULER,
    HI_EXALTATION, HI_TRIPLICITY, _hi_element,
    compute_sect_info, compute_morin_combustion,
    _safe_float,
    _sign_from_lon, _house_cusps, _collect_planets, _house_from_lon, _get_aspects_list, _ang_sep, _is_via_combusta, _is_waxing,
)


JUPITER_DOMICILES = {"Sagittarius", "Pisces"}
JUPITER_EXALTATION = "Cancer"
JUPITER_DETRIMENTS = {"Gemini", "Virgo"}
JUPITER_FALL = "Capricorn"


def score_journey_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Score election for journeys (long/short), with or without natal.

    Options (optional):
      - journey_type: 'long' | 'short' (default: 'long')
      - sr_windows, lr_list, natal_cd, natal_cusps, natal_hits (same shape as other models)
      - include_fixed_stars: bool
    """
    score = 0.0
    tags: List[str] = []

    opts = options or {}
    journey_type = str(opts.get('journey_type') or 'long').strip().lower()
    travel_house = 9 if journey_type != 'short' else 3

    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    aspects_list = _get_aspects_list(election_cd) or []

    # Combustion map when timestamp available
    combust_map: Dict[str, str] = {}
    try:
        cur_ts = opts.get('current_timestamp')
        if compute_morin_combustion is not None and cur_ts is not None:
            rows = compute_morin_combustion(election_cd if isinstance(election_cd, dict) else {}, cur_ts.isoformat())
            for r in rows or []:
                nm = str(r.get('planet') or '')
                st = str(r.get('status') or '')
                if nm:
                    combust_map[nm] = st
    except Exception:
        combust_map = {}

    # Determine day/night (approx via Sun house)
    is_day = False
    try:
        sun = planets.get('Sun')
        sh: Optional[int] = None
        if sun:
            sun_lon = _safe_float(sun.get('longitude'))
            sh = int(sun.get('house')) if sun.get('house') is not None else _house_from_lon(sun_lon, cusps) if sun_lon is not None else None
        is_day = isinstance(sh, int) and 7 <= sh <= 12
    except Exception:
        is_day = False

    # Axes and rulers
    asc_sign = _sign_from_lon(cusps[0]) if len(cusps) >= 1 else None
    mc_sign = _sign_from_lon(cusps[9]) if len(cusps) >= 10 else None
    travel_sign = _sign_from_lon(cusps[travel_house - 1]) if len(cusps) >= travel_house else None
    L1 = TRAD_RULER.get(asc_sign) if asc_sign else None
    Ltravel = TRAD_RULER.get(travel_sign) if travel_sign else None

    # 1) ASC sign quality — cardinal best, mutable acceptable, fixed avoid
    try:
        if asc_sign in CARDINAL_SIGNS:
            score += 1.0; tags.append('Cardinal Asc (movement)')
        elif asc_sign in MUTABLE_SIGNS:
            score += 0.3; tags.append('Mutable Asc (adaptable)')
        elif asc_sign in FIXED_SIGNS:
            score -= 0.8; tags.append('Fixed Asc (delays)')
        # Day/Night sign harmony
        if asc_sign:
            diurnal = {"Aries","Gemini","Leo","Libra","Sagittarius","Aquarius"}
            nocturnal = {"Taurus","Cancer","Virgo","Scorpio","Capricorn","Pisces"}
            if (is_day and asc_sign in diurnal) or ((not is_day) and asc_sign in nocturnal):
                score += 0.2; tags.append('Asc sign matches chart sect')
    except Exception:
        pass

    # 2) L1 condition
    try:
        if L1 and L1 in planets:
            pr = planets[L1]
            lon = _safe_float(pr.get('longitude'))
            h = int(pr.get('house')) if pr.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if h in ANGULAR_HOUSES: score += 2.0; tags.append('ASC ruler angular')
            elif h in SUCCEDENT_HOUSES: score += 1.0; tags.append('ASC ruler succedent')
            elif h in CADENT_HOUSES: score -= 1.0; tags.append('ASC ruler cadent')
            if bool(pr.get('retrograde')): score -= 2.0; tags.append('ASC ruler retrograde')
            st = combust_map.get(L1)
            if st == 'combust': score -= 1.0; tags.append('ASC ruler combust')
            elif st == 'under_beams': score -= 0.5; tags.append('ASC ruler under beams')
    except Exception:
        pass

    # 2b) Mercury condition — avoid retrograde for logistics/communications
    try:
        me = planets.get('Mercury')
        if me:
            if bool(me.get('retrograde')):
                score -= 1.0; tags.append('Mercury retrograde (delays)')
    except Exception:
        pass

    # 3) Jupiter and Venus (benefics) placement priorities
    for nm in ('Jupiter','Venus'):
        try:
            p = planets.get(nm)
            if not p: continue
            lon = _safe_float(p.get('longitude'))
            h = int(p.get('house')) if p.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if nm == 'Jupiter':
                if h == 1: score += 2.0; tags.append('Jupiter in Asc (ideal)')
                elif h == 10: score += 1.5; tags.append('Jupiter in MC')
                elif h == travel_house: score += 1.2; tags.append('Jupiter in travel house')
                jsign = str(p.get('sign') or '')
                if not jsign and lon is not None:
                    jsign = _sign_from_lon(lon)
                if jsign in JUPITER_DOMICILES or jsign == JUPITER_EXALTATION: score += 1.0; tags.append('Jupiter dignified')
                if jsign in JUPITER_DETRIMENTS or jsign == JUPITER_FALL: score -= 0.6; tags.append('Jupiter debilitated')
                if bool(p.get('retrograde')): score -= 0.6; tags.append('Jupiter retrograde')
            else:  # Venus
                if h in (1,10): score += 0.6; tags.append(f'Venus in {h}th')
                elif h == 11: score += 0.4; tags.append('Venus in 11th')
        except Exception:
            continue

    # Bonatti adds the Part of Fortune and its ruler to short-journey elections.
    if journey_type == 'short':
        try:
            lots = election_cd.get('arabic_parts') if isinstance(election_cd.get('arabic_parts'), dict) else None
            if not isinstance(lots, dict):
                from arabic_parts import compute_arabic_parts

                lots = compute_arabic_parts(election_cd if isinstance(election_cd, dict) else {}) or {}
            pof = lots.get('fortune') or lots.get('Part of Fortune') or lots.get('Fortuna') or lots.get('Fortune')
            if isinstance(pof, dict):
                pof_lon = _safe_float(pof.get('longitude') if pof.get('longitude') is not None else pof.get('lon'))
                pof_house = int(pof.get('house')) if pof.get('house') is not None else _house_from_lon(pof_lon, cusps) if pof_lon is not None else None
                if pof_house == 3:
                    score += 1.5; tags.append('Part of Fortune in 3rd')
                elif pof_house in (1, 9, 10, 11):
                    score += 0.5; tags.append(f'Part of Fortune in {pof_house}th')
                elif pof_house in (6, 8, 12):
                    score -= 1.0; tags.append(f'Part of Fortune in {pof_house}th (avoid)')

                pof_ruler = str(pof.get('ruler') or '')
                if not pof_ruler and pof_lon is not None:
                    pof_ruler = str(TRAD_RULER.get(_sign_from_lon(pof_lon)) or '')
                if pof_ruler in planets:
                    pof_ruler_row = planets[pof_ruler]
                    r_lon = _safe_float(pof_ruler_row.get('longitude'))
                    r_house = int(pof_ruler_row.get('house')) if pof_ruler_row.get('house') is not None else _house_from_lon(r_lon, cusps) if r_lon is not None else None
                    if r_house in ANGULAR_HOUSES:
                        score += 1.0; tags.append('Fortune ruler angular')
                    elif r_house in SUCCEDENT_HOUSES:
                        score += 0.5; tags.append('Fortune ruler succedent')
                    elif r_house in CADENT_HOUSES:
                        score -= 0.5; tags.append('Fortune ruler cadent')
                    if bool(pof_ruler_row.get('retrograde')):
                        score -= 0.8; tags.append('Fortune ruler retrograde')
        except Exception:
            pass

    # 4) Moon placement and condition
    try:
        m = planets.get('Moon'); s = planets.get('Sun')
        if m:
            mlon = _safe_float(m.get('longitude'))
            mh = int(m.get('house')) if m.get('house') is not None else _house_from_lon(mlon, cusps) if mlon is not None else None
            if mh == travel_house:
                score += 2.0; tags.append('Moon in travel house')
            if mh in (6,8,12):
                score -= 2.0; tags.append('Moon in 6/8/12 (avoid)')
            # Moon sign — avoid fixed for travel
            try:
                m_sign = str(m.get('sign') or '')
                if not m_sign and mlon is not None:
                    m_sign = _sign_from_lon(mlon)
                if m_sign in FIXED_SIGNS:
                    score -= 0.5; tags.append('Moon in fixed sign (delays)')
            except Exception:
                pass
            # Combust/under beams & Via Combusta penalties (small)
            try:
                st_m = combust_map.get('Moon')
                if st_m == 'combust':
                    score -= 1.0; tags.append('Moon combust')
                elif st_m == 'under_beams':
                    score -= 0.5; tags.append('Moon under beams')
                elif s:
                    sun_lon = _safe_float(s.get('longitude'))
                    if mlon is not None and sun_lon is not None:
                        sep = abs((((mlon - sun_lon) + 180.0) % 360.0) - 180.0)
                        if sep <= 15.0:
                            score -= 0.5; tags.append('Moon under beams (≈15°)')
                if _is_via_combusta(mlon):
                    score -= 1.0; tags.append('Moon in Via Combusta')
            except Exception:
                pass
            # Waxing for new beginnings
            if s:
                sun_lon = _safe_float(s.get('longitude'))
                if mlon is not None and sun_lon is not None:
                    waxing = _is_waxing(mlon, sun_lon)
                    if waxing is True:
                        score += 0.5; tags.append('Moon waxing')
                    elif waxing is False:
                        tags.append('Moon waning')
            # Next applying aspect
            na = election_cd.get('moon_next_aspect')
            if isinstance(na, dict):
                pn = str(na.get('planet') or '')
                asp = str(na.get('aspect') or '')
                if pn in planets and bool(planets[pn].get('retrograde')):
                    score -= 1.0; tags.append('Moon applying to retrograde')
                if pn in BENEFICS and asp in ('Trine','Sextile','Conjunction'):
                    score += 1.5; tags.append(f"Moon applying {asp} to {pn}")
                if pn in MALEFICS and asp in ('Square','Opposition','Conjunction'):
                    score -= 2.0; tags.append(f"Moon applying {asp} to {pn}")
            # Avoid pattern: Moon opp Sun then applying malefic (approximate)
            try:
                has_moon_sun_opposition = any({str(a.get('planet1') or a.get('p1') or ''), str(a.get('planet2') or a.get('p2') or '')} == {'Moon','Sun'} and str(a.get('aspect') or '') == 'Opposition' for a in aspects_list)
                if has_moon_sun_opposition:
                    for a in aspects_list:
                        p1 = str(a.get('planet1') or a.get('p1') or '')
                        p2 = str(a.get('planet2') or a.get('p2') or '')
                        asp = str(a.get('aspect') or '')
                        ph = str(a.get('phase') or '').lower()
                        if 'apply' in ph or ph == 'applying':
                            if 'Moon' in {p1,p2} and ({p1,p2} & MALEFICS):
                                if asp in ('Conjunction','Square','Opposition'):
                                    score -= 2.0; tags.append('Moon opp Sun then applying malefic')
                                    break
            except Exception:
                pass
    except Exception:
        pass

    # 5) MC configuration: benefics on MC, soft aspects
    try:
        if len(cusps) >= 10:
            mc_lon = float(cusps[9] % 360.0)
            for nm in ('Jupiter','Venus'):
                p = planets.get(nm)
                if not p: continue
                lon = _safe_float(p.get('longitude'))
                if lon is None:
                    continue
                d = abs((((lon % 360.0 - mc_lon) + 180.0) % 360.0) - 180.0)
                if d <= 6.0 or abs(d-60.0) <= 6.0 or abs(d-120.0) <= 6.0:
                    score += 0.6; tags.append(f'{nm} soft to MC')
    except Exception:
        pass

    # 6) Malefics placement cautions
    for nm in ('Mars','Saturn'):
        try:
            p = planets.get(nm)
            if not p: continue
            lon = _safe_float(p.get('longitude'))
            h = int(p.get('house')) if p.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if h == 8: score -= 3.0; tags.append(f'{nm} in 8th (danger)')
            elif h in (1,12): score -= 2.0; tags.append(f'{nm} in {h}th (caution)')
            elif h == travel_house: score -= 1.5; tags.append(f'{nm} in travel house (obstacle)')
            elif h == 11: tags.append(f'{nm} in 11th (safer)')
        except Exception:
            continue

    # 6b) 8th-house ruler condition (safety)
    try:
        if len(cusps) >= 8:
            c8_sign = _sign_from_lon(cusps[7])
            r8 = TRAD_RULER.get(c8_sign)
            if r8 and r8 in planets:
                p8 = planets[r8]
                lon8 = _safe_float(p8.get('longitude'))
                h8 = int(p8.get('house')) if p8.get('house') is not None else _house_from_lon(lon8, cusps) if lon8 is not None else None
                if h8 in (8,12):
                    score -= 1.5; tags.append('8th ruler in 8th/12th (safety)')
                if bool(p8.get('retrograde')):
                    score -= 0.8; tags.append('8th ruler retrograde')
                # Affliction by malefics
                for a in aspects_list:
                    try:
                        p1 = str(a.get('planet1') or a.get('p1') or '')
                        p2 = str(a.get('planet2') or a.get('p2') or '')
                        asp = str(a.get('aspect') or '')
                        if r8 in {p1, p2} and (('Mars' in {p1,p2}) or ('Saturn' in {p1,p2})) and asp in ('Conjunction','Square','Opposition'):
                            score -= 1.2; tags.append('8th ruler afflicted by malefic')
                            break
                    except Exception:
                        continue
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
            if sl is not None and any(_ang_sep(sl % 360.0, nl) <= 1.0 for nl in node_lons):
                score -= 2.0; tags.append('Near eclipse: Sun near Node (≤1°)')
        if node_lons and moon:
            ml = _safe_float(moon.get('longitude'))
            if ml is not None and any(_ang_sep(ml % 360.0, nl) <= 1.0 for nl in node_lons):
                score -= 2.0; tags.append('Near eclipse: Moon near Node (≤1°)')
    except Exception:
        pass

    # 7) Optional fixed stars on key points
    try:
        if bool(opts.get('include_fixed_stars')):
            from fixed_stars import compute_fixed_star_hits
            hits_fs = compute_fixed_star_hits(election_cd if isinstance(election_cd, dict) else {}, orb_deg=1.0, check_planets=['Moon','Jupiter','Venus'], include_cusps=True)
            good = {'Regulus','Spica','Aldebaran','Arcturus','Fomalhaut'}
            bad = {'Algol','Antares','South Scale'}
            for h in hits_fs or []:
                star = str(h.get('star') or '')
                tgt = str(h.get('target_label') or h.get('target') or '')
                if tgt in ('Asc','MC','Moon','Jupiter','Venus'):
                    if star in good: score += 0.4; tags.append(f'Fixed star {star} on {tgt}')
                    if star in bad: score -= 0.6; tags.append(f'Fixed star {star} on {tgt}')
    except Exception:
        pass

    # 8) Natal journey potential gate (if natal provided)
    try:
        natal_cd = opts.get('natal_cd') if isinstance(opts, dict) else None
        if natal_cd and isinstance(natal_cd, dict):
            nat_cusps = natal_cd.get('house_cusps') or natal_cd.get('houses')
            nat_pl = natal_cd.get('planets') or {}
            plmap: Dict[str, Dict[str, Any]] = {}
            if isinstance(nat_pl, dict): plmap = {k:v for k,v in nat_pl.items() if isinstance(v, dict)}
            elif isinstance(nat_pl, list):
                for v in nat_pl:
                    if isinstance(v, dict) and v.get('planet'): plmap[str(v['planet'])] = v
            nat_travel_sign = _sign_from_lon(float(nat_cusps[travel_house - 1])) if isinstance(nat_cusps, list) and len(nat_cusps) >= travel_house else None
            Ltravel_nat = TRAD_RULER.get(nat_travel_sign) if nat_travel_sign else None

            def _house_nat(nm: str) -> Optional[int]:
                try:
                    p = plmap.get(nm)
                    if not p: return None
                    if p.get('house') is not None: return int(p.get('house'))
                    lon = _safe_float(p.get('longitude'))
                    if lon is not None and isinstance(nat_cusps, list) and len(nat_cusps) >= 12:
                        return _house_from_lon(lon, nat_cusps)
                    return None
                except Exception:
                    return None

            strong = 0; weak = 0; hinder = 0
            # Travel ruler condition
            if Ltravel_nat and Ltravel_nat in plmap:
                hh = _house_nat(Ltravel_nat)
                if isinstance(hh, int) and (hh in ANGULAR_HOUSES or hh in SUCCEDENT_HOUSES): strong += 1
                if bool(plmap[Ltravel_nat].get('retrograde')): weak += 1
            # Planets within natal travel house
            try:
                if isinstance(nat_cusps, list) and len(nat_cusps) >= 12:
                    for nm, p in plmap.items():
                        hh = _house_nat(nm)
                        if hh == travel_house:
                            if nm in BENEFICS: strong += 1
                            if nm in MALEFICS: weak += 1
            except Exception:
                pass
            # Links to ASC/MC
            try:
                if Ltravel_nat:
                    hL = _house_nat(Ltravel_nat)
                    if isinstance(hL, int) and hL in (1,10): strong += 1
            except Exception:
                pass
            # Malefic on natal 8th cusp tight
            try:
                if isinstance(nat_cusps, list) and len(nat_cusps) >= 8:
                    c8 = float(nat_cusps[7]) % 360.0
                    for mal in ('Mars','Saturn'):
                        p = plmap.get(mal)
                        if not p: continue
                        lon = _safe_float(p.get('longitude'))
                        if lon is None: continue
                        d = abs((((lon % 360.0 - c8)+180.0)%360.0)-180.0)
                        if d <= 3.0:
                            hinder += 1
            except Exception:
                pass
            mult = 1.0
            if strong == 0 and (weak >= 2 or hinder >= 1):
                mult = 0.4; tags.append('Natal journey promise weak — capping')
            elif strong >= 2 and weak == 0 and hinder == 0:
                mult = 1.0
            else:
                mult = 0.8
            score = score * mult
    except Exception:
        pass

    # 9) Timing feasibility: directions/transits proxy + SR/LR windows
    if natal_hits:
        try:
            fav = 0; unfav = 0
            for h in natal_hits[:20]:
                tr = str(h.get('transiting') or '')
                tgt = str(h.get('target_label') or h.get('natal') or '')
                asp = str(h.get('aspect') or '')
                towards_travel = (tgt.endswith('C9') or tgt.endswith('C3') or ' C9' in tgt or ' C3' in tgt)
                towards_angles = (tgt in ('Asc','MC','C1','C10'))
                towards_danger = (tgt.endswith('C8') or ' C8' in tgt or tgt.endswith('C12') or tgt.endswith('C6'))
                if tr in BENEFICS and asp in ('Conjunction','Trine','Sextile') and (towards_travel or towards_angles):
                    fav += 1
                if tr in MALEFICS and asp in ('Conjunction','Square','Opposition') and (towards_danger or towards_travel):
                    unfav += 1
            if fav: score += 0.5; tags.append('Directions/Transits favorable (journey)')
            if unfav: score -= 0.8; tags.append('Directions/Transits warnings (journey)')
        except Exception:
            pass

    try:
        sr_windows = list(opts.get('sr_windows') or [])
        lr_list = list(opts.get('lr_list') or [])
        cur_ts = opts.get('current_timestamp')
        if sr_windows and cur_ts is not None:
            in_sr = any(a <= cur_ts <= b for (a,b) in sr_windows)
            if in_sr: score += 0.4; tags.append('SR window (journey)')
        if lr_list and cur_ts is not None:
            dd = min(abs((cur_ts - t).total_seconds()) for t in lr_list)
            if dd <= 12*3600: score += 0.3; tags.append('Near LR (≤12h)')
            elif dd <= 48*3600: score += 0.1; tags.append('Near LR (≤48h)')
    except Exception:
        pass

    return Score(value=round(score, 2), tags=tags)


__all__ = ['score_journey_election']
