from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import (
    Score,
    FIXED_SIGNS, BENEFICS, MALEFICS,
    ANGULAR_HOUSES, SUCCEDENT_HOUSES, CADENT_HOUSES,
    TRAD_RULER,
    compute_morin_combustion,
    _sign_from_lon, _house_cusps, _collect_planets, _get_aspects_list, _house_from_lon, _ang_sep,
)


def score_contract_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Compute a score for contract/partnership agreement signing.

    Principles (universal, without natal):
      - Mercury direct and not combust/under beams
      - Moon not in 6/8/12, waxing preferred; avoid VOC; applying to benefics
      - Fortify 7th house/Descendant (benefics in 7th; dignified, angular L7)
      - Prefer fixed axes (esp. Taurus/Leo); avoid Scorpio on Desc; penalize Aries/Aquarius on Desc
      - Keep malefics off the angles (especially Mars on Asc/Desc)
      - Benefics angular (1/7/10)

    With natal (optional):
      - Apply a natal promise gate similar to marriage model
      - Small boosts for sensible overlays (e.g., election ASC not in natal 6/8/12)
    """
    score = 0.0
    tags: List[str] = []

    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    aspects_list = _get_aspects_list(election_cd)

    # Options
    opts = options or {}
    pref_raw = opts.get('prefer_fixed_asc')
    if isinstance(pref_raw, str):
        prefer_fixed_asc = pref_raw.strip().lower() in {'1', 'true', 'yes'}
    elif pref_raw is None:
        prefer_fixed_asc = False
    else:
        prefer_fixed_asc = bool(pref_raw)
    saturn_binding_ok = bool(opts.get('saturn_binding_ok', True))
    min_mercury_direct_days = int(opts.get('min_mercury_direct_days', 0) or 0)
    contract_mode = str(opts.get('contract_mode') or '').strip().lower()  # '', 'new', 'renew', 'amend', 'finalize'

    # Combustion map (uses timestamp when provided)
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

    # Signs on Asc/Desc
    asc_sign: Optional[str] = None
    dsc_sign: Optional[str] = None
    try:
        if len(cusps) >= 7:
            asc_sign = _sign_from_lon(cusps[0])
            dsc_sign = _sign_from_lon(cusps[6])
    except Exception:
        pass

    # Prefer fixed signs for stability
    if prefer_fixed_asc and asc_sign in FIXED_SIGNS:
        score += 2.0; tags.append(f"Fixed Asc ({asc_sign})")
    if dsc_sign in FIXED_SIGNS:
        if dsc_sign == 'Scorpio':
            # Scorpio on Descendant is traditionally problematic for agreements
            score -= 3.0; tags.append('Unfavored 7th sign (Scorpio)')
        else:
            score += 2.0; tags.append(f"Fixed 7th ({dsc_sign})")
    if dsc_sign == 'Aries':
        score -= 2.0; tags.append('Unfavored 7th sign (Aries)')
    if dsc_sign == 'Aquarius':
        score -= 2.0; tags.append('Unfavored 7th sign (Aquarius)')

    # Mercury — the contract itself
    try:
        me = planets.get('Mercury')
        if me:
            if bool(me.get('retrograde')):
                # Apply deal-breaker logic by context
                if contract_mode in ('renew','resign','amend','revise','finalize'):
                    # Allow during Rx with caution; small negative to reflect extra diligence needed
                    score -= 0.5; tags.append('Mercury retrograde (exception: renewing/amending/finalizing)')
                else:
                    # Default/new contracts: near deal-breaker
                    score -= 5.0; tags.append('Deal-breaker: Mercury retrograde (new contracts)')
            else:
                tags.append('Mercury direct')
                # Optional post-station buffer is not computed here; caller can filter by time
                if min_mercury_direct_days:
                    # Use speed as a coarse proxy for proximity to station; penalize very slow motion
                    try:
                        spd = float(me.get('speed')) if me.get('speed') is not None else None
                    except Exception:
                        spd = None
                    if spd is not None and spd < 0.2:
                        score -= 0.8; tags.append('Mercury near station (speed low)')
                    else:
                        tags.append(f"Mercury direct ≥{min_mercury_direct_days}d (proxy)")
            m_sign = str(me.get('sign') or _sign_from_lon(float(me.get('longitude') or 0.0)))
            if m_sign in ("Gemini","Virgo"):
                score += 2.0; tags.append('Mercury dignified')
            elif m_sign in ("Sagittarius","Pisces"):
                score -= 2.0; tags.append('Mercury in detriment/fall')
            mh = int(me.get('house')) if me.get('house') is not None else _house_from_lon(float(me.get('longitude') or 0.0), cusps)
            if mh in (1,3,7,9,10):
                score += 1.0; tags.append('Mercury well placed')
            st = combust_map.get('Mercury')
            if st == 'combust':
                score -= 2.0; tags.append('Mercury combust')
            elif st == 'under_beams':
                score -= 1.0; tags.append('Mercury under beams')
            # Mercury’s aspects to benefics/malefics (coarse from aspects list)
            if aspects_list:
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
                                score += 1.0; tags.append('Mercury soft to benefic')
                            if other in MALEFICS and asp in ('Conjunction','Square','Opposition') and ('apply' in ph or ph == 'applying'):
                                score -= 1.5; tags.append('Mercury hard to malefic')
                    except Exception:
                        continue
    except Exception:
        pass

    # Moon conditions (avoid 6/8/12, VOC, and hard applying to malefics)
    try:
        m = planets.get('Moon'); s = planets.get('Sun')
        if m:
            mh = int(m.get('house')) if m.get('house') is not None else _house_from_lon(float(m.get('longitude') or 0.0), cusps)
            if mh in (6,8,12):
                score -= 2.0; tags.append('Moon in bad house (6/8/12)')
            na = election_cd.get('moon_next_aspect')
            if isinstance(na, dict):
                pn = str(na.get('planet') or '')
                asp = str(na.get('aspect') or '')
                ph = str(na.get('phase') or '').lower()
                if pn == 'Mercury' and asp in ('Trine','Sextile','Conjunction') and ('apply' in ph or ph == 'applying' or not ph):
                    score += 1.0; tags.append('Moon applying soft to Mercury')
                if pn in BENEFICS and asp in ('Trine','Sextile','Conjunction'):
                    score += 1.5; tags.append(f"Moon applying {asp} to {pn}")
                if pn in MALEFICS and asp in ('Square','Opposition','Conjunction'):
                    score -= 2.0; tags.append(f"Moon applying {asp} to {pn}")
            # VOC Moon flag
            try:
                voc = False
                if isinstance(election_cd.get('considerations'), dict):
                    voc = bool(election_cd['considerations'].get('moon_void'))
                voc = voc or bool(election_cd.get('void_of_course')) or bool(election_cd.get('moon_voc')) or bool(election_cd.get('moon_void'))
                if not voc and isinstance(election_cd.get('moon_state'), dict):
                    voc = bool(election_cd['moon_state'].get('void_of_course'))
                if voc:
                    score -= 3.0; tags.append('Moon VOC')
            except Exception:
                pass
            # Waxing preferred
            if s and s.get('longitude') is not None and m.get('longitude') is not None:
                sep = abs((((float(m.get('longitude')) - float(s.get('longitude'))) + 180.0) % 360.0) - 180.0)
                waxing = True if sep < 180.0 else False
                if waxing:
                    score += 0.5; tags.append('Moon waxing')
    except Exception:
        pass

    # 7th ruler placement and angular benefics/malefics
    try:
        r7 = TRAD_RULER.get(dsc_sign) if dsc_sign else None
        if r7 and r7 in planets:
            pr = planets[r7]
            lon = float(pr.get('longitude')) if pr.get('longitude') is not None else None
            h = int(pr.get('house')) if pr.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if h in ANGULAR_HOUSES: score += 2.0; tags.append('7th ruler angular')
            elif h in SUCCEDENT_HOUSES: score += 1.0; tags.append('7th ruler succedent')
            elif h in CADENT_HOUSES: score -= 1.0; tags.append('7th ruler cadent')
            if bool(pr.get('retrograde')): score -= 2.0; tags.append('7th ruler retrograde')
        # Benefics/malefics on angles
        for nm in ("Jupiter", "Venus", "Mars", "Saturn"):
            info = planets.get(nm)
            if not info: continue
            lon = float(info.get('longitude')) if info.get('longitude') is not None else None
            h = int(info.get('house')) if info.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if nm in BENEFICS:
                if h in (1,7,10): score += 1.0; tags.append(f'{nm} in {h}th')
            else:
                if h in (1,7): score -= 2.0; tags.append(f'{nm} in {h}th')
    except Exception:
        pass

    # Near-eclipse penalty (Sun/Moon within 1° of a Node)
    try:
        def _get_node_lons() -> List[float]:
            out: List[float] = []
            nn = planets.get('North Node') or planets.get('Node')
            if nn and nn.get('longitude') is not None:
                out.append(float(nn.get('longitude')) % 360.0)
            sn = planets.get('South Node')
            if sn and sn.get('longitude') is not None:
                out.append(float(sn.get('longitude')) % 360.0)
            elif out:
                out.append((out[0] + 180.0) % 360.0)
            return out
        node_lons = _get_node_lons()
        sun = planets.get('Sun'); moon = planets.get('Moon')
        if node_lons and sun and sun.get('longitude') is not None:
            sl = float(sun.get('longitude')) % 360.0
            if any(_ang_sep(sl, nl) <= 1.0 for nl in node_lons):
                score -= 2.0; tags.append('Near eclipse: Sun near Node (≤1°)')
        if node_lons and moon and moon.get('longitude') is not None:
            ml = float(moon.get('longitude')) % 360.0
            if any(_ang_sep(ml, nl) <= 1.0 for nl in node_lons):
                score -= 2.0; tags.append('Near eclipse: Moon near Node (≤1°)')
    except Exception:
        pass

    # Saturn binding exception (when explicitly allowed)
    try:
        if saturn_binding_ok and isinstance(dsc_sign, str) and TRAD_RULER.get(dsc_sign) == 'Saturn':
            # Saturn dignified/exalted softens binding nature for long-term agreements
            s = planets.get('Saturn')
            if s and s.get('sign'):
                s_sign = str(s.get('sign'))
                exalted = (s_sign == 'Libra')
                dign = (TRAD_RULER.get(s_sign) == 'Saturn') or exalted
                if dign:
                    score += 0.8; tags.append('Saturn dignified for binding stability')
    except Exception:
        pass

    # Natal context enrichment (gate and simple overlays)
    try:
        natal_cd = opts.get('natal_cd') if isinstance(opts, dict) else None
        if natal_cd and isinstance(natal_cd, dict):
            natal_cusps = natal_cd.get('house_cusps') or natal_cd.get('houses')
            natal_pl = natal_cd.get('planets') or {}
            pl_map: Dict[str, Dict[str, Any]] = {}
            if isinstance(natal_pl, dict):
                for k, v in natal_pl.items():
                    if isinstance(v, dict): pl_map[k] = v
            elif isinstance(natal_pl, list):
                for v in natal_pl:
                    if isinstance(v, dict) and v.get('planet'): pl_map[str(v['planet'])] = v
            strong = 0; weak = 0; hinder = 0
            # Benefics condition in natal
            for nm in ('Venus','Jupiter'):
                p = pl_map.get(nm)
                if not p: continue
                try:
                    hh = int(p.get('house')) if p.get('house') is not None else None
                except Exception:
                    hh = None
                if hh is None and p.get('longitude') is not None and isinstance(natal_cusps, list) and len(natal_cusps) >= 12:
                    hh = _house_from_lon(float(p.get('longitude')), natal_cusps)
                if isinstance(hh, int) and (hh in ANGULAR_HOUSES or hh in SUCCEDENT_HOUSES):
                    strong += 1
                if bool(p.get('retrograde')):
                    weak += 1
            # Natal L7
            try:
                if isinstance(natal_cusps, list) and len(natal_cusps) >= 7:
                    natal_dsc_sign = _sign_from_lon(float(natal_cusps[6]))
                    L7n = TRAD_RULER.get(natal_dsc_sign)
                    if L7n and L7n in pl_map:
                        pr = pl_map[L7n]
                        try:
                            hh7 = int(pr.get('house')) if pr.get('house') is not None else None
                        except Exception:
                            hh7 = None
                        if hh7 is None and pr.get('longitude') is not None and isinstance(natal_cusps, list) and len(natal_cusps) >= 12:
                            hh7 = _house_from_lon(float(pr.get('longitude')), natal_cusps)
                        if isinstance(hh7, int) and (hh7 in ANGULAR_HOUSES or hh7 in SUCCEDENT_HOUSES):
                            strong += 1
                        if bool(pr.get('retrograde')):
                            weak += 1
            except Exception:
                pass
            # Malefic tightly on natal 7th cusp
            try:
                if isinstance(natal_cusps, list) and len(natal_cusps) >= 7:
                    dsc_lon = float(natal_cusps[6]) % 360.0
                    for mal in ('Saturn','Mars'):
                        p = pl_map.get(mal)
                        if not p or p.get('longitude') is None: continue
                        lon = float(p.get('longitude')) % 360.0
                        d = abs((((lon - dsc_lon)+180.0)%360.0)-180.0)
                        if d <= 3.0:
                            hinder += 1
            except Exception:
                pass
            # Gate multiplier
            mult = 1.0
            if strong == 0 and (weak >= 2 or hinder >= 1):
                mult = 0.4; tags.append('Natal promise weak — capping score')
            elif strong >= 2 and weak == 0 and hinder == 0:
                mult = 1.0
            else:
                mult = 0.8
            score = score * mult
            # Avoid election Asc on natal 6/8/12
            try:
                if isinstance(natal_cusps, list) and len(natal_cusps) >= 12 and len(cusps) >= 1:
                    asc_lon = float(cusps[0] % 360.0)
                    hh_nat = _house_from_lon(asc_lon, natal_cusps)
                    if isinstance(hh_nat, int) and hh_nat in (6,8,12):
                        score -= 0.8; tags.append('Election ASC on natal 6/8/12')
            except Exception:
                pass
            # Align to natal Asc sign when declared well-disposed
            try:
                natal_asc_sign = opts.get('natal_asc_sign')
                natal_asc_well = opts.get('natal_asc_well')
                if asc_sign and natal_asc_sign and natal_asc_well and asc_sign == str(natal_asc_sign):
                    score += 0.6; tags.append('ASC matches natal (well-disposed)')
            except Exception:
                pass
    except Exception:
        pass

    return Score(value=round(score, 2), tags=tags)

__all__ = ['score_contract_election']
