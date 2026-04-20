from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .common import (
    Score,
    _collect_planets,
    _house_cusps,
    _house_from_lon,
    _sign_from_lon,
    _get_aspects_list,
    _ang_sep,
    _is_waxing,
)


MOON_SIGN_POINTS: Dict[str, float] = {
    "Taurus": 10.0,
    "Capricorn": 10.0,
    "Cancer": 10.0,
    "Virgo": 7.0,
    "Libra": 7.0,
    "Scorpio": 7.0,
    "Pisces": 5.0,
    "Aquarius": 5.0,
    "Gemini": -4.0,
    "Leo": 2.0,
    "Sagittarius": 2.0,
    "Aries": -100.0,
}

MOON_SIGN_LABELS: Dict[str, str] = {
    "Taurus": "Tier 1 Moon (Taurus) – beauty & lasting results",
    "Capricorn": "Tier 1 Moon (Capricorn) – structured, professional finish",
    "Cancer": "Tier 1 Moon (Cancer) – nurturing & healthy regrowth",
    "Virgo": "Tier 2 Moon (Virgo) – precision and health",
    "Libra": "Tier 2 Moon (Libra) – beauty & balance",
    "Scorpio": "Tier 2 Moon (Scorpio) – transformative support",
    "Pisces": "Tier 3 Moon (Pisces) – gentle, soft outcome",
    "Aquarius": "Tier 3 Moon (Aquarius) – experimental flavor",
    "Gemini": "Bonatti exception: Moon in Gemini – avoid haircut timing",
    "Leo": "Caution Moon (Leo) – dramatic growth, manage volume",
    "Sagittarius": "Caution Moon (Sagittarius) – unpredictable regrowth",
    "Aries": "Golden rule: Moon in Aries – avoid head hair cuts",
}

ASC_SIGN_ADJUST: Dict[str, float] = {
    "Taurus": 1.5,
    "Capricorn": 1.3,
    "Cancer": 1.0,
    "Virgo": 0.8,
    "Libra": 0.8,
    "Scorpio": 0.8,
    "Pisces": 0.6,
    "Aquarius": 0.4,
    "Gemini": 0.4,
    "Leo": -0.6,
    "Sagittarius": -0.6,
    "Aries": -3.0,
}

SOFT_ASPECTS = {"Trine", "Sextile"}
HARD_ASPECTS = {"Square", "Opposition"}


def _normalize_goal(options: Optional[Dict[str, Any]]) -> str:
    goal = ''
    if options and isinstance(options, dict):
        goal = str(options.get('hair_goal') or '').strip().lower()
    if goal in {'growth', 'grow'}:
        return 'growth'
    if goal in {'lasting', 'maintain', 'stay'}:
        return 'lasting'
    return 'balanced'


def _safe_angle(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _detect_dark_moon(separation: Optional[float]) -> bool:
    try:
        if separation is None:
            return False
        return float(separation) <= 12.0
    except Exception:
        return False


def _aspect_match(separation: float, targets: Tuple[float, ...], orb: float = 4.0) -> Optional[float]:
    for t in targets:
        if abs(separation - t) <= orb:
            return t
    return None


def _weekday_bonus(dt, timezone: Optional[str]) -> Tuple[float, Optional[str]]:
    if dt is None:
        return 0.0, None
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        if isinstance(dt, datetime):
            loc_dt = dt
            if timezone:
                try:
                    tz = ZoneInfo(timezone)
                    if dt.tzinfo is None:
                        loc_dt = dt.replace(tzinfo=tz)
                    else:
                        loc_dt = dt.astimezone(tz)
                except Exception:
                    loc_dt = dt
            weekday = loc_dt.weekday()  # Monday=0
        else:
            return 0.0, None
    except Exception:
        return 0.0, None
    if weekday == 4:  # Friday
        return 2.0, "Venus day (Friday) bonus"
    if weekday in (0, 2):  # Monday, Wednesday
        return 1.0, "Supportive weekday (Moon/Mercury)"
    if weekday in (1, 5):  # Tuesday, Saturday
        return -1.0, "Challenging weekday (Mars/Saturn)"
    return 0.0, None


def score_haircut_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    """Score hair cutting elections with transit and optional natal context."""
    score = 0.0
    tags: List[str] = []

    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    moon = planets.get('Moon')
    sun = planets.get('Sun')

    moon_sign: Optional[str] = None
    moon_lon: Optional[float] = None
    moon_speed: Optional[float] = None
    asc_sign: Optional[str] = None

    if moon:
        moon_lon = _safe_angle(moon.get('longitude'))
        moon_speed = _safe_angle(moon.get('speed'))
        try:
            moon_sign = str(moon.get('sign') or _sign_from_lon(moon_lon))
        except Exception:
            moon_sign = None

    if cusps:
        asc_sign = _sign_from_lon(cusps[0])

    goal = _normalize_goal(options)

    # Golden rule and baseline score from Moon sign
    if moon_sign:
        base = MOON_SIGN_POINTS.get(moon_sign)
        if base is not None:
            score += base
            note = MOON_SIGN_LABELS.get(moon_sign)
            if note:
                tags.append(note)
        if moon_sign == "Aries":
            tags.append("Forbidden: Moon in Aries – wait two days")

    # Ascendant adjustments (head rulership awareness)
    if asc_sign:
        asc_adj = ASC_SIGN_ADJUST.get(asc_sign)
        if asc_adj:
            score += asc_adj
            if asc_adj > 0:
                tags.append(f"Ascendant in supportive sign ({asc_sign})")
            else:
                tags.append(f"Ascendant caution sign ({asc_sign})")

    # Moon phase handling (waxing/waning/dark)
    sun_lon = _safe_angle(sun.get('longitude')) if sun else None
    separation = _ang_sep(moon_lon, sun_lon) if (moon_lon is not None and sun_lon is not None) else None
    dark_moon = _detect_dark_moon(separation)
    if dark_moon:
        score -= 2.0
        tags.append("Dark Moon window – energy unstable")

    waxing = None
    if moon_lon is not None and sun_lon is not None:
        waxing = _is_waxing(moon_lon, sun_lon)

    if not dark_moon and waxing is not None:
        if goal == 'growth':
            waxing_bonus = 3.0
            waning_bonus = 0.5
        elif goal == 'lasting':
            waxing_bonus = 0.5
            waning_bonus = 3.0
        else:
            waxing_bonus = 2.0
            waning_bonus = 1.0
        if waxing is True:
            if waxing_bonus:
                score += waxing_bonus
                tags.append("Waxing Moon – growth supportive")
        else:
            if waning_bonus:
                score += waning_bonus
                tags.append("Waning Moon – style holds longer")

    # Day-of-week timing bonus
    current_ts = options.get('current_timestamp') if isinstance(options, dict) else None
    timezone_name: Optional[str] = None
    if isinstance(options, dict):
        tz_opt = options.get('timezone')
        if isinstance(tz_opt, str) and tz_opt.strip():
            timezone_name = tz_opt.strip()
    w_bonus, w_note = _weekday_bonus(current_ts, timezone_name)
    if w_bonus:
        score += w_bonus
        if w_note:
            tags.append(w_note)

    # Moon speed
    if moon_speed is not None:
        speed_abs = abs(moon_speed)
        if speed_abs > 13.0:
            score += 1.0
            tags.append("Moon swift (>13°/day)")
        elif speed_abs < 11.0:
            score -= 1.0
            tags.append("Moon slow (<11°/day)")

    # Void-of-course penalties
    voc = False
    try:
        if bool(election_cd.get('void_of_course')):
            voc = True
        if not voc and bool(election_cd.get('moon_void')):
            voc = True
        if not voc and bool(election_cd.get('moon_voc')):
            voc = True
        if not voc:
            cons = election_cd.get('considerations')
            if isinstance(cons, dict) and bool(cons.get('moon_void')):
                voc = True
        if not voc:
            moon_state = election_cd.get('moon_state')
            if isinstance(moon_state, dict) and bool(moon_state.get('void_of_course')):
                voc = True
    except Exception:
        voc = False
    if voc:
        score -= 2.0
        tags.append("Moon void-of-course – outcomes drift")

    # Moon aspects to benefics/malefics
    aspects_list = _get_aspects_list(election_cd) or []
    seen_pairs = set()
    for asp_row in aspects_list:
        try:
            p1 = str(asp_row.get('planet1') or asp_row.get('p1') or '')
            p2 = str(asp_row.get('planet2') or asp_row.get('p2') or '')
            aspect = str(asp_row.get('aspect') or asp_row.get('type') or '').title()
            if 'Moon' not in (p1, p2):
                continue
            other = p2 if p1 == 'Moon' else p1
            key = (other, aspect)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            phase = str(asp_row.get('phase') or '').lower()
            applying = 'apply' in phase
        except Exception:
            continue

        bonus = 0.0
        note: Optional[str] = None
        if other == 'Venus' and aspect in SOFT_ASPECTS:
            bonus = 3.0
            note = f"Moon {aspect.lower()} Venus – beauty boost"
        elif other == 'Jupiter' and aspect in SOFT_ASPECTS:
            bonus = 2.0
            note = f"Moon {aspect.lower()} Jupiter – fortunate timing"
        elif other == 'Saturn' and aspect in HARD_ASPECTS:
            bonus = -3.0
            note = f"Moon {aspect.lower()} Saturn – restrictive"
        elif other == 'Mars' and aspect in HARD_ASPECTS:
            bonus = -2.0
            note = f"Moon {aspect.lower()} Mars – irritation risk"
        elif other == 'Saturn' and aspect == 'Conjunction':
            bonus = -2.0
            note = "Moon conjunct Saturn – heavy result"

        if bonus:
            if applying and bonus > 0:
                bonus += 0.5
                note = (note or '') + " (applying)" if note else "Applying aspect bonus"
            score += bonus
            if note:
                tags.append(note)

    # Natal bonuses when data provided
    natal_cd = options.get('natal_cd') if isinstance(options, dict) else None
    natal_cusps = options.get('natal_cusps') if isinstance(options, dict) else None
    natal_planets: Dict[str, Dict[str, Any]] = {}
    natal_asc_sign: Optional[str] = None
    natal_asc_lon: Optional[float] = None

    if natal_cd and isinstance(natal_cd, dict):
        natal_planets = _collect_planets(natal_cd)
    if natal_cusps and isinstance(natal_cusps, list) and len(natal_cusps) >= 1:
        natal_asc_lon = _safe_angle(natal_cusps[0])
        natal_asc_sign = _sign_from_lon(natal_cusps[0])

    if natal_asc_sign and moon_sign and moon_sign == natal_asc_sign:
        score += 3.0
        tags.append("Transit Moon in natal Asc sign (+3)")
    if natal_asc_sign == 'Aries' and moon_sign == 'Aries':
        score -= 5.0
        tags.append("Natal Asc Aries + Moon Aries – extra sensitivity")

    if moon_lon is not None:
        if natal_asc_lon is not None:
            sep = _ang_sep(moon_lon, natal_asc_lon)
            aspect_hit = _aspect_match(sep, (60.0, 120.0))
            if aspect_hit:
                score += 2.0
                tags.append("Moon harmonizes with natal Asc (+2)")

        natal_moon = natal_planets.get('Moon')
        natal_venus = natal_planets.get('Venus')

        if natal_moon and natal_moon.get('longitude') is not None:
            nat_moon_lon = _safe_angle(natal_moon.get('longitude'))
            if nat_moon_lon is not None:
                sep = _ang_sep(moon_lon, nat_moon_lon)
                if _aspect_match(sep, (60.0, 120.0)) is not None:
                    score += 3.0
                    tags.append("Moon trine/sextile natal Moon (+3)")

        if natal_venus and natal_venus.get('longitude') is not None:
            nat_venus_lon = _safe_angle(natal_venus.get('longitude'))
            nat_venus_sign = None
            try:
                nat_venus_sign = str(natal_venus.get('sign') or _sign_from_lon(nat_venus_lon))
            except Exception:
                nat_venus_sign = None
            if nat_venus_lon is not None:
                sep = _ang_sep(moon_lon, nat_venus_lon)
                if _aspect_match(sep, (60.0, 120.0)) is not None:
                    score += 3.0
                    tags.append("Moon trine/sextile natal Venus (+3)")
            if nat_venus_sign in {'Taurus', 'Libra'} and moon_sign == 'Taurus':
                score += 2.0
                tags.append("Natal Venus in Venus sign + Moon Taurus (+2)")

        if natal_cusps and isinstance(natal_cusps, list) and len(natal_cusps) >= 12:
            natal_house = _house_from_lon(moon_lon, natal_cusps) if moon_lon is not None else None
            if isinstance(natal_house, int) and natal_house == 6:
                score += 2.0
                tags.append("Moon transiting natal 6th house (+2)")

    # Final qualitative rating
    if score >= 15:
        tags.append("Rating: EXCEPTIONAL ⭐⭐⭐⭐⭐")
    elif score >= 10:
        tags.append("Rating: EXCELLENT ⭐⭐⭐⭐")
    elif score >= 7:
        tags.append("Rating: GOOD ⭐⭐⭐")
    elif score >= 4:
        tags.append("Rating: ACCEPTABLE ⭐⭐")
    elif score >= 1:
        tags.append("Rating: MARGINAL ⭐")
    else:
        tags.append("Rating: POOR ❌")

    return Score(value=score, tags=tags)


__all__ = ['score_haircut_election']
