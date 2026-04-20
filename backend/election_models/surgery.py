from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import (
    Score,
    FIXED_SIGNS,
    BENEFICS, MALEFICS,
    TRAD_RULER,
    ANGULAR_HOUSES, SUCCEDENT_HOUSES, CADENT_HOUSES,
    compute_morin_combustion,
    _sign_from_lon, _house_cusps, _collect_planets, _house_from_lon, _get_aspects_list, _is_waxing, _ordinal, _is_via_combusta, _ang_sep,
)


# Body part rulerships by sign (Rule 26)
SURGERY_SIGN_ALIASES: Dict[str, Dict[str, Any]] = {
    "Aries": {
        "label": "Head, face, brain",
        "aliases": {"head", "face", "brain", "skull", "scalp", "cranial"},
    },
    "Taurus": {
        "label": "Neck, throat, thyroid",
        "aliases": {"neck", "throat", "thyroid"},
    },
    "Gemini": {
        "label": "Arms, shoulders, hands, lungs",
        "aliases": {"arm", "arms", "shoulder", "shoulders", "hand", "hands", "lung", "lungs"},
    },
    "Cancer": {
        "label": "Chest, breasts, stomach",
        "aliases": {"chest", "breast", "breasts", "stomach"},
    },
    "Leo": {
        "label": "Heart, upper back, spine",
        "aliases": {"heart", "spine", "upper back", "cardiac"},
    },
    "Virgo": {
        "label": "Intestines, digestive system",
        "aliases": {"intestine", "intestines", "digestive", "abdomen", "abdominal", "bowel"},
    },
    "Libra": {
        "label": "Kidneys, lower back, skin",
        "aliases": {"kidney", "kidneys", "lower back", "skin", "dermal"},
    },
    "Scorpio": {
        "label": "Reproductive organs, bladder, colon",
        "aliases": {"reproductive", "uterus", "ovary", "ovaries", "prostate", "bladder", "colon", "genital"},
    },
    "Sagittarius": {
        "label": "Thighs, hips, liver",
        "aliases": {"thigh", "thighs", "hip", "hips", "liver"},
    },
    "Capricorn": {
        "label": "Knees, bones, teeth, skin",
        "aliases": {"knee", "knees", "bone", "bones", "tooth", "teeth", "skeletal"},
    },
    "Aquarius": {
        "label": "Calves, ankles, circulatory system",
        "aliases": {"calf", "calves", "ankle", "ankles", "circulatory", "circulation"},
    },
    "Pisces": {
        "label": "Feet, lymphatic system",
        "aliases": {"foot", "feet", "lymph", "lymphatic"},
    },
}


def _normalize_sign_name(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        t = str(s).strip().title()
        # Normalize common variants
        if t in ("Ari", "Arie", "Aires"): return "Aries"
        if t in ("Tau",): return "Taurus"
        if t in ("Gem",): return "Gemini"
        if t in ("Can",): return "Cancer"
        if t in ("Vir",): return "Virgo"
        if t in ("Lib",): return "Libra"
        if t in ("Sco",): return "Scorpio"
        if t in ("Sag",): return "Sagittarius"
        if t in ("Cap",): return "Capricorn"
        if t in ("Aqu",): return "Aquarius"
        if t in ("Pis",): return "Pisces"
        # If full name already fine
        if t in SURGERY_SIGN_ALIASES:
            return t
        # If user passed a body alias accidentally here, leave for alias resolver
        return t
    except Exception:
        return None


def _resolve_target_sign_from_options(options: Optional[Dict[str, Any]]) -> Optional[str]:
    """Return target sign string from options.

    Accepts either 'target_sign' (e.g., 'Leo') or 'target' (e.g., 'heart', 'knee').
    """
    if not options:
        return None
    # 1) Direct sign
    ts = options.get('target_sign') or options.get('surgery_sign')
    tsn = _normalize_sign_name(ts)
    if tsn in SURGERY_SIGN_ALIASES:
        return tsn
    # 2) From alias
    tgt = (options.get('target') or options.get('surgery_target') or '').strip().lower()
    if tgt:
        for sign, meta in SURGERY_SIGN_ALIASES.items():
            try:
                aliases = set(str(x).lower() for x in (meta.get('aliases') or []))
                if tgt in aliases:
                    return sign
            except Exception:
                continue
    return None


def score_surgery_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Compute a Morin-inspired score for surgery/medical procedures.

    Options:
      - target_sign / surgery_sign: direct zodiac sign name to avoid for cutting
      - target / surgery_target: body-part alias (e.g., 'heart', 'knee')
      - procedure: 'cutting' (default), 'purging', 'diagnostic'
    """
    score = 0.0
    tags: List[str] = []
    never_reasons: List[str] = []

    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)

    def _opt_bool(name: str, default: bool) -> bool:
        val = (options or {}).get(name) if options else None
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        text = str(val).strip().lower()
        if text in {'1', 'true', 'yes', 'on'}:
            return True
        if text in {'0', 'false', 'no', 'off'}:
            return False
        return default

    strict_never_rules = _opt_bool('strict_surgery_never_rules', True)

    # Combustion/under-beams status map (if timestamp provided)
    combust_map: Dict[str, str] = {}
    try:
        cur_ts = (options or {}).get('current_timestamp') if options else None
        if compute_morin_combustion is not None and cur_ts is not None:
            rows = compute_morin_combustion(election_cd if isinstance(election_cd, dict) else {}, cur_ts.isoformat())
            for r in rows or []:
                nm = str(r.get('planet') or '')
                st = str(r.get('status') or '')
                if nm:
                    combust_map[nm] = st
    except Exception:
        combust_map = {}

    # Derive context
    asc_sign: Optional[str] = None
    try:
        if len(cusps) >= 1:
            asc_sign = _sign_from_lon(cusps[0])
    except Exception:
        asc_sign = None

    proc = None
    try:
        proc = str(options.get('procedure') if options else '').strip().lower() or 'cutting'
    except Exception:
        proc = 'cutting'
    target_sign = _resolve_target_sign_from_options(options)
    mercury = planets.get('Mercury')

    # Moon, Sun
    m = planets.get('Moon'); s = planets.get('Sun')
    moon_sign = None; moon_house = None
    if m:
        try:
            moon_sign = str(m.get('sign') or _sign_from_lon(float(m.get('longitude') or 0.0)))
        except Exception:
            moon_sign = None
        try:
            moon_house = int(m.get('house')) if m.get('house') is not None else _house_from_lon(float(m.get('longitude') or 0.0), cusps)
        except Exception:
            moon_house = None
    # Natal-house check for Moon (if natal cusps provided)
    try:
        natal_cusps_opt = (options or {}).get('natal_cusps') if options else None
        if m and natal_cusps_opt and isinstance(natal_cusps_opt, list) and len(natal_cusps_opt) >= 12 and m.get('longitude') is not None:
            mh_nat = _house_from_lon(float(m.get('longitude')), natal_cusps_opt)
            if isinstance(mh_nat, int) and mh_nat in (6,8,12):
                score -= 1.2; tags.append('Moon in natal 6/8/12')
    except Exception:
        pass

    # 1) ABSOLUTE PROHIBITION (Rule 26): avoid Moon in sign ruling the body part
    if target_sign and moon_sign and moon_sign == target_sign:
        score -= 8.0
        tags.append(f"Avoid: Moon in {moon_sign} (target body sign)")
        if strict_never_rules:
            never_reasons.append('Moon in target body-part sign')
    # Additional caution: avoid ASC in the sign ruling the body part
    try:
        if target_sign and asc_sign and asc_sign == target_sign:
            score -= 2.0; tags.append('ASC in target body sign (avoid)')
    except Exception:
        pass

    # Classic surgery cautions treat Mercury retrograde as a hard contraindication.
    try:
        if mercury and bool(mercury.get('retrograde')):
            score -= 3.0
            tags.append('Mercury retrograde')
            if strict_never_rules:
                never_reasons.append('Mercury retrograde')
    except Exception:
        pass

    # 2) Moon house prohibitions (Rule 11): 6th/8th/12th
    if isinstance(moon_house, int) and moon_house in (6, 8, 12):
        pen = 4.0 if moon_house in (6, 12) else 5.0
        score -= pen
        tags.append(f"Moon in {moon_house}th house")

    # Bonatti recommends the Moon in a fixed sign for surgery by iron.
    try:
        if proc == 'cutting' and moon_sign in FIXED_SIGNS:
            score += 1.5
            tags.append('Moon in fixed sign (surgery stability)')
    except Exception:
        pass

    # 3) Moon applying aspects and retrogrades (Rules 11,12,16,19)
    try:
        na = election_cd.get('moon_next_aspect')
        if isinstance(na, dict):
            pn = str(na.get('planet') or '')
            asp = str(na.get('aspect') or '')
            # Avoid Moon applying to retrograde
            if pn and pn in planets and bool(planets[pn].get('retrograde')):
                score -= 3.0; tags.append('Moon applying to retrograde planet')
            # Dangerous combinations (Rule 12)
            if moon_sign:
                if pn == 'Mars' and moon_sign in ('Taurus', 'Libra') and asp in ('Conjunction','Square','Opposition'):
                    score -= 3.0; tags.append('Moon→Mars from Venus signs')
                if pn == 'Jupiter' and moon_sign in ('Gemini', 'Virgo') and asp in ('Conjunction','Square','Opposition'):
                    score -= 2.0; tags.append('Moon→Jupiter from Mercury signs')
                if pn == 'Sun' and moon_sign in ('Capricorn', 'Aquarius') and asp in ('Conjunction','Square','Opposition'):
                    score -= 2.0; tags.append('Moon→Sun from Saturn signs')
            # Outcome indicator (Rule 20): next applying aspect proxy
            if pn in BENEFICS and asp in ('Trine','Sextile','Conjunction'):
                score += 2.0; tags.append(f"Moon applying {asp} to {pn}")
            if pn in MALEFICS and asp in ('Square','Opposition','Conjunction'):
                score -= 3.0; tags.append(f"Moon applying {asp} to {pn}")
    except Exception:
        pass

    # 3b) Moon opposite Sun (Full Moon) caution
    full_moon_flag = False
    moon_via_combusta = False
    try:
        # Combust/under-beams & Via Combusta penalties for Moon
        try:
            if m and s and m.get('longitude') is not None and s.get('longitude') is not None:
                st_m = combust_map.get('Moon')
                if st_m == 'combust':
                    score -= 2.0; tags.append('Moon combust')
                elif st_m == 'under_beams':
                    score -= 1.0; tags.append('Moon under beams')
                else:
                    sep = abs((((float(m.get('longitude')) - float(s.get('longitude'))) + 180.0) % 360.0) - 180.0)
                    if sep <= 15.0:
                        score -= 1.0; tags.append('Moon under beams (≈15°)')
            if m and _is_via_combusta(float(m.get('longitude') or 0.0)):
                moon_via_combusta = True
                score -= 1.5; tags.append('Moon in Via Combusta')
        except Exception:
            pass
        aspects_list = None
        for key in ('planetary_aspects_precise','planetary_aspects','aspects'):
            vlist = election_cd.get(key)
            if isinstance(vlist, list):
                aspects_list = vlist; break
        if aspects_list:
            for a in aspects_list:
                p1 = str(a.get('planet1') or a.get('p1') or '')
                p2 = str(a.get('planet2') or a.get('p2') or '')
                asp = str(a.get('aspect') or '')
                if {p1,p2} == {'Moon','Sun'} and asp == 'Opposition':
                    if proc in ('cutting','purging'):
                        score -= 2.0; tags.append('Full Moon (surgery caution)')
                    else:
                        score -= 1.0; tags.append('Full Moon (Moon–Sun opposition)')
                    full_moon_flag = True
                    break
    except Exception:
        pass
    if moon_via_combusta and strict_never_rules:
        never_reasons.append('Moon in Via Combusta')

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
        strict_deg = None
        try:
            # options may supply strict/eclipse degrees (default 12)
            if options and options.get('strict_eclipse_window'):
                strict_deg = float((options.get('eclipse_window_deg') or options.get('strict_eclipse_deg') or 12))
        except Exception:
            strict_deg = None
        if node_lons and s and s.get('longitude') is not None:
            sl = float(s.get('longitude')) % 360.0
            near = any(_ang_sep(sl, nl) <= 1.0 for nl in node_lons)
            if near:
                score -= 2.0; tags.append('Near eclipse: Sun near Node (≤1°)')
            else:
                # Approximate eclipse window (~±14 days) via Sun within 12° of Node
                if any(_ang_sep(sl, nl) <= 12.0 for nl in node_lons):
                    score -= 1.0; tags.append('Eclipse window: Sun within 12° of Node')
                    if strict_deg is not None and any(_ang_sep(sl, nl) <= strict_deg for nl in node_lons):
                        score -= 5.0; tags.append(f'Strict: eclipse window (Sun ≤{int(strict_deg)}°)')
        if node_lons and m and m.get('longitude') is not None:
            ml = float(m.get('longitude')) % 360.0
            near_m = any(_ang_sep(ml, nl) <= 1.0 for nl in node_lons)
            if near_m:
                score -= 2.0; tags.append('Near eclipse: Moon near Node (≤1°)')
            else:
                if any(_ang_sep(ml, nl) <= 12.0 for nl in node_lons):
                    score -= 1.0; tags.append('Eclipse window: Moon within 12° of Node')
                    if strict_deg is not None and any(_ang_sep(ml, nl) <= strict_deg for nl in node_lons):
                        score -= 5.0; tags.append(f'Strict: eclipse window (Moon ≤{int(strict_deg)}°)')
    except Exception:
        pass

    # 4) VOC Moon penalty when flagged (stronger for surgery)
    try:
        voc = False
        cons = election_cd.get('considerations') or {}
        if isinstance(cons, dict):
            voc = bool(cons.get('moon_void'))
        voc = voc or bool(election_cd.get('void_of_course') or election_cd.get('moon_void') or election_cd.get('moon_voc'))
        if not voc and isinstance(election_cd.get('moon_state'), dict):
            voc = bool(election_cd['moon_state'].get('void_of_course'))
        if voc:
            if proc in ('cutting','purging'):
                score -= 4.0; tags.append('Moon void-of-course (strong penalty)')
            else:
                score -= 1.0; tags.append('Moon void-of-course')
            if strict_never_rules:
                never_reasons.append('Moon void-of-course')
    except Exception:
        pass

    # 5) ASC and ASC ruler strength (Rules 3,5,7)
    try:
        if asc_sign:
            r1 = TRAD_RULER.get(asc_sign)
            if r1 and r1 in planets:
                pr = planets[r1]
                lon = float(pr.get('longitude')) if pr.get('longitude') is not None else None
                h = int(pr.get('house')) if pr.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
                if h in ANGULAR_HOUSES:
                    score += 2.0; tags.append('ASC ruler angular')
                elif h in SUCCEDENT_HOUSES:
                    score += 1.0; tags.append('ASC ruler succedent')
                elif h in CADENT_HOUSES:
                    score -= 1.0; tags.append('ASC ruler cadent')
                if bool(pr.get('retrograde')):
                    score -= 2.0; tags.append('ASC ruler retrograde')
                # Above horizon (houses 7–12) modest support
                try:
                    if isinstance(h, int) and 7 <= h <= 12:
                        score += 0.5; tags.append('ASC ruler above horizon')
                except Exception:
                    pass
    except Exception:
        pass

    # 6) 6th house condition (Rules 2,4) – light heuristic using sign ruler
    try:
        if len(cusps) >= 6:
            c6_sign = _sign_from_lon(cusps[5])
            r6 = TRAD_RULER.get(c6_sign)
            if r6 and r6 in planets:
                p6 = planets[r6]
                lon = float(p6.get('longitude')) if p6.get('longitude') is not None else None
                h6 = int(p6.get('house')) if p6.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
                if h6 in ANGULAR_HOUSES: score += 1.0; tags.append('6th ruler angular')
                if bool(p6.get('retrograde')): score -= 1.0; tags.append('6th ruler retrograde')
    except Exception:
        pass

    # 6b) 8th house (surgery/crisis) — ruler and malefics
    try:
        if len(cusps) >= 8:
            c8_sign = _sign_from_lon(cusps[7])
            r8 = TRAD_RULER.get(c8_sign)
            if r8 and r8 in planets:
                p8 = planets[r8]
                lon8 = float(p8.get('longitude')) if p8.get('longitude') is not None else None
                h8 = int(p8.get('house')) if p8.get('house') is not None else _house_from_lon(lon8, cusps) if lon8 is not None else None
                if h8 in (8, 12):
                    score -= 2.0; tags.append('8th ruler in 8th/12th')
                if bool(p8.get('retrograde')):
                    score -= 1.0; tags.append('8th ruler retrograde')
                # Affliction by malefics
                aspects_list = _get_aspects_list(election_cd) or []
                for a in aspects_list:
                    try:
                        p1 = str(a.get('planet1') or a.get('p1') or '')
                        p2 = str(a.get('planet2') or a.get('p2') or '')
                        asp = str(a.get('aspect') or '')
                        if r8 in {p1, p2} and (('Mars' in {p1,p2}) or ('Saturn' in {p1,p2})) and asp in ('Conjunction','Square','Opposition'):
                            score -= 1.5; tags.append('8th ruler afflicted by malefic')
                            break
                    except Exception:
                        continue
        # Malefics placed in 8th
        for mal in ('Mars','Saturn'):
            try:
                pm = planets.get(mal)
                if not pm: continue
                lonm = float(pm.get('longitude')) if pm.get('longitude') is not None else None
                hm = int(pm.get('house')) if pm.get('house') is not None else _house_from_lon(lonm, cusps) if lonm is not None else None
                if hm == 8:
                    score -= 2.0; tags.append(f'{mal} in 8th')
            except Exception:
                continue
    except Exception:
        pass

    # 7) Malefics out of angles (Rule 24); keep Mars in 1st strongly negative
    saturn_hard_house = False
    for nm in ('Mars','Saturn'):
        try:
            info = planets.get(nm)
            if not info: continue
            lon = float(info.get('longitude')) if info.get('longitude') is not None else None
            h = int(info.get('house')) if info.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if nm == 'Saturn' and h in (1, 7):
                saturn_hard_house = True
            if h in (1, 10):
                if nm == 'Mars' and h == 1:
                    score -= 3.0; tags.append('Mars in 1st (trauma to body)')
                else:
                    score -= 3.0; tags.append(f'{nm} angular')
            elif h == 6:
                score -= 2.0; tags.append(f'{nm} in 6th (illness risk)')
            elif h == 7:
                score -= 2.0; tags.append(f'{nm} in 7th')
            elif h == 4:
                score -= 1.0; tags.append(f'{nm} in 4th')
            elif h == 12:
                score -= 2.5; tags.append(f'{nm} in 12th (hospitalization)')
        except Exception:
            continue
    if saturn_hard_house and strict_never_rules:
        never_reasons.append('Saturn rising/in 7th')

    # 8) Benefics in angles (Rules 21–23)
    for nm in ('Jupiter','Venus'):
        try:
            info = planets.get(nm)
            if not info: continue
            lon = float(info.get('longitude')) if info.get('longitude') is not None else None
            h = int(info.get('house')) if info.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
            if h in (1,10):
                score += 2.0; tags.append(f'{nm} in {_ordinal(h)}')
            elif h == 11:
                score += 1.0; tags.append(f'{nm} in 11th')
        except Exception:
            continue

    # 9) Procedure-specific refinements
    # Purging procedures (Rule 27)
    if proc == 'purging':
        if moon_sign in ('Scorpio','Pisces'):
            score += 2.0; tags.append('Purging: Moon in Scorpio/Pisces')
        elif moon_sign in ('Cancer','Scorpio','Pisces'):
            score += 1.0; tags.append('Purging: Moon in water sign')
        # Avoid Moon conjunct Jupiter, Moon in Leo/earth signs weakens purgings
        try:
            aspects_list = None
            for key in ('planetary_aspects_precise','planetary_aspects','aspects'):
                vlist = election_cd.get(key)
                if isinstance(vlist, list):
                    aspects_list = vlist; break
            if aspects_list:
                for a in aspects_list:
                    p1 = str(a.get('planet1') or a.get('p1') or '')
                    p2 = str(a.get('planet2') or a.get('p2') or '')
                    asp = str(a.get('aspect') or '')
                    if {p1,p2} == {'Moon','Jupiter'} and asp == 'Conjunction':
                        score -= 1.0; tags.append('Purging weakened: Moon conj Jupiter')
                        break
        except Exception:
            pass
        if moon_sign in ('Leo','Taurus','Virgo','Capricorn'):
            score -= 1.0; tags.append('Purging weakened: Moon in Leo/Earth sign')
        # ASC ruler below horizon (houses 1–6) supports elimination
        try:
            if asc_sign:
                r1 = TRAD_RULER.get(asc_sign)
                if r1 and r1 in planets:
                    pr = planets[r1]
                    lon = float(pr.get('longitude')) if pr.get('longitude') is not None else None
                    h = int(pr.get('house')) if pr.get('house') is not None else _house_from_lon(lon, cusps) if lon is not None else None
                    if isinstance(h, int) and 1 <= h <= 6:
                        score += 1.0; tags.append('ASC ruler below horizon')
        except Exception:
            pass

    # Cutting/core surgery: Mars can be helpful if dignified and supportive
    if proc == 'cutting':
        try:
            mars = planets.get('Mars')
            if mars:
                ms = str(mars.get('sign') or _sign_from_lon(float(mars.get('longitude') or 0.0)))
                mh = int(mars.get('house')) if mars.get('house') is not None else _house_from_lon(float(mars.get('longitude') or 0.0), cusps)
                if ms in ("Aries","Scorpio","Capricorn") and mh in (3,6):
                    score += 2.5; tags.append('Mars dignified supporting surgery')
                # Mars retrograde and combust penalties
                if bool(mars.get('retrograde')):
                    score -= 1.5; tags.append('Mars retrograde')
                try:
                    if 'Mars' in combust_map and combust_map.get('Mars') == 'combust':
                        score -= 1.5; tags.append('Mars combust Sun')
                except Exception:
                    pass
                # Avoid hard Mars–Moon to reduce bleeding/inflammation risk
                aspects_list = _get_aspects_list(election_cd)
                if aspects_list:
                    for a in aspects_list:
                        p1 = str(a.get('planet1') or a.get('p1') or '')
                        p2 = str(a.get('planet2') or a.get('p2') or '')
                        asp = str(a.get('aspect') or '')
                        if {p1,p2} == {'Moon','Mars'} and asp in ('Square','Opposition','Conjunction'):
                            score -= 2.0; tags.append('Avoid: hard Moon–Mars')
                            break
        except Exception:
            pass

    # 10b) Physician/10th: L10 soft to L1, Jupiter soft to L10
    try:
        mc_sign = _sign_from_lon(cusps[9]) if len(cusps) >= 10 else None
        L1 = TRAD_RULER.get(asc_sign) if asc_sign else None
        L10 = TRAD_RULER.get(mc_sign) if mc_sign else None
        aspects_list = _get_aspects_list(election_cd) or []
        def _is_soft(a):
            asp = str(a.get('aspect') or '')
            ph_raw = a.get('phase') or a.get('motion')
            if ph_raw in (None, '') and a.get('applying') is not None:
                ph_raw = 'applying' if bool(a.get('applying')) else 'separating'
            ph = str(ph_raw or '').lower()
            return asp in ('Conjunction','Trine','Sextile') and (('apply' in ph) or ph == 'applying' or not ph)
        if L10 and L1:
            for a in aspects_list:
                p1 = str(a.get('planet1') or a.get('p1') or '')
                p2 = str(a.get('planet2') or a.get('p2') or '')
                if {p1,p2} == {L10, L1} and _is_soft(a):
                    score += 0.6; tags.append('Physician: L10 soft to L1')
                    break
        if L10 and 'Jupiter' in planets:
            for a in aspects_list:
                p1 = str(a.get('planet1') or a.get('p1') or '')
                p2 = str(a.get('planet2') or a.get('p2') or '')
                if {p1,p2} == {'Jupiter', L10} and _is_soft(a):
                    score += 0.5; tags.append('Jupiter soft to L10')
                    break
    except Exception:
        pass

    # 10) Traditional “contrary” rule: Moon conj Saturn/Jupiter better waxing; Mars/Venus contrary
    try:
        aspects_list = None
        for key in ('planetary_aspects_precise','planetary_aspects','aspects'):
            vlist = election_cd.get(key)
            if isinstance(vlist, list):
                aspects_list = vlist; break
        waxing = None
        if m and s and m.get('longitude') is not None and s.get('longitude') is not None:
            waxing = _is_waxing(float(m.get('longitude')), float(s.get('longitude')))
        if aspects_list:
            def _has_conj(target: str) -> bool:
                for a in aspects_list:
                    try:
                        p1 = str(a.get('planet1') or a.get('p1') or '')
                        p2 = str(a.get('planet2') or a.get('p2') or '')
                        asp = str(a.get('aspect') or '')
                        if {p1,p2} == {'Moon', target} and asp == 'Conjunction':
                            return True
                    except Exception:
                        continue
                return False
            if _has_conj('Jupiter') or _has_conj('Saturn'):
                if waxing is True:
                    score += 1.0; tags.append('Rule13: Moon conj Jupiter/Saturn while waxing (good)')
                elif waxing is False:
                    score -= 1.0; tags.append('Rule13: Moon conj Jupiter/Saturn while waning (contrary)')
            if _has_conj('Mars'):
                if waxing is True:
                    score -= 1.5; tags.append('Rule13: Moon conj Mars while waxing (inflammation risk)')
                elif waxing is False:
                    score += 0.5; tags.append('Rule13: Moon conj Mars while waning (mitigated)')
            if _has_conj('Venus'):
                if waxing is True:
                    score -= 1.0; tags.append('Rule13: Moon conj Venus while waxing (unfavorable)')
                elif waxing is False:
                    score += 0.3; tags.append('Rule13: Moon conj Venus while waning (mitigated)')
    except Exception:
        pass

    # 11) Natal enrichment (optional): simple transit-facing cues to Asc/6th
    if natal_hits:
        try:
            for h in natal_hits[:15]:
                tr = str(h.get('transiting') or '')
                tgt = str(h.get('target_label') or h.get('natal') or '')
                asp = str(h.get('aspect') or '')
                if tr in BENEFICS and asp in ('Conjunction','Trine','Sextile') and (tgt in ('Asc','C6') or ' 6th' in tgt or tgt.endswith('C6')):
                    score += 1.0; tags.append(f"Transit {tr}→{tgt} {asp}")
                if tr in MALEFICS and asp in ('Conjunction','Square','Opposition') and (tgt in ('Asc','C6') or ' 6th' in tgt or tgt.endswith('C6')):
                    score -= 1.5; tags.append(f"Transit {tr}→{tgt} {asp}")
        except Exception:
            pass

    # 12) Moon optimization and general environment (standalone best practices)
    try:
        # Waxing/Waning handling — surgery prefers waning
        if m and s and m.get('longitude') is not None and s.get('longitude') is not None:
            waxing = _is_waxing(float(m.get('longitude')), float(s.get('longitude')))
            if proc in ('cutting','purging'):
                if waxing is True:
                    score -= 0.5; tags.append('Waxing Moon (surgery): increased bleeding risk')
                elif waxing is False:
                    score += 0.5; tags.append('Waning Moon (surgery)')
            else:
                if waxing is True:
                    score += 0.5; tags.append('Moon waxing')
        # Moon house support: avoid boosting 1st for medical; penalize instead
        if isinstance(moon_house, int):
            if moon_house in (10,11):
                score += 0.5; tags.append(f'Moon in {moon_house}th')
            elif moon_house == 1 and proc in ('cutting','purging'):
                score -= 2.0; tags.append('Moon in 1st (medical caution)')
        # Moon speed (if available)
        try:
            spd = float(m.get('speed')) if m and m.get('speed') is not None else None
            if spd and spd > 13.0:
                score += 0.3; tags.append('Moon swift')
        except Exception:
            pass
        # Moon sign preference (lightweights; purging handled earlier)
        if proc != 'purging' and moon_sign:
            if moon_sign in ("Aries","Leo","Sagittarius"): score += 0.4; tags.append('Moon in fire sign')
            elif moon_sign in ("Gemini","Libra","Aquarius"): score += 0.2; tags.append('Moon in air sign')
            elif moon_sign in ("Taurus","Virgo","Capricorn"): score -= 0.1; tags.append('Moon in earth sign')
            elif moon_sign in ("Cancer","Scorpio","Pisces"): score -= 0.1; tags.append('Moon in water sign')
    except Exception:
        pass

    # 13) ASC sign quality by procedure (approximation without "major" flag)
    try:
        if asc_sign:
            if proc == 'diagnostic' and asc_sign in ("Gemini","Virgo","Sagittarius","Pisces"):
                score += 0.4; tags.append('Mutable ASC for diagnostic')
            elif proc == 'cutting' and asc_sign in ("Aries","Cancer","Libra","Capricorn"):
                score += 0.3; tags.append('Cardinal ASC for cutting')
    except Exception:
        pass

    # 14) Jupiter succedent support (2/11)
    try:
        j = planets.get('Jupiter')
        if j:
            lonj = float(j.get('longitude')) if j.get('longitude') is not None else None
            hj = int(j.get('house')) if j.get('house') is not None else _house_from_lon(lonj, cusps) if lonj is not None else None
            if hj == 2:
                score += 0.8; tags.append('Jupiter in 2nd (support)')
            elif hj == 11:
                tags.append('Jupiter in 11th (support)')
    except Exception:
        pass

    if strict_never_rules and never_reasons:
        dedup: List[str] = []
        seen = set()
        for reason in never_reasons:
            if reason not in seen:
                dedup.append(reason)
                seen.add(reason)
        score = min(score, -99.0)
        tags.append('Never timing contraindications: ' + '; '.join(dedup))

    return Score(value=round(score, 2), tags=tags)

__all__ = ['SURGERY_SIGN_ALIASES', 'score_surgery_election']
