from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from moon_day import compute_moon_day

from .common import (
    ANGULAR_HOUSES,
    Score,
    TRAD_RULER,
    _ang_sep,
    _collect_planets,
    _house_cusps,
    _house_from_lon,
    _ordinal,
    _safe_float,
    _sign_from_lon,
)


_BUSINESS_MOON_SIGN_SCORES = {
    "Cancer": 3.0,
    "Virgo": 2.0,
    "Pisces": 3.0,
    "Aries": -3.0,
    "Libra": -3.0,
    "Scorpio": -3.0,
    "Capricorn": -3.0,
    "Aquarius": -3.0,
    "Gemini": 0.0,
    "Leo": 0.0,
    "Sagittarius": 0.0,
}
_SLOW_SIGNS_NORTH = {"Cancer": 2.0, "Leo": 3.0, "Virgo": 3.0, "Libra": 1.0}
_SLOW_SIGNS_SOUTH = {"Capricorn": 2.0, "Aquarius": 3.0, "Pisces": 3.0, "Aries": 1.0}
_FAVORED_TIMING_RULERS = {"Sun", "Mercury", "Jupiter", "Saturn"}
_SOFT_ASPECTS: Sequence[Tuple[float, float, float, str]] = (
    (60.0, 4.5, 0.75, "sextile"),
    (120.0, 5.5, 0.95, "trine"),
)
_RESONANCE_ASPECTS: Sequence[Tuple[float, float, float, str]] = (
    (0.0, 6.0, 0.9, "conjunction"),
    (60.0, 4.5, 0.75, "sextile"),
    (120.0, 5.5, 0.95, "trine"),
)
_HARD_ASPECTS: Sequence[Tuple[float, float, float, str]] = (
    (90.0, 5.0, -0.75, "square"),
    (180.0, 6.0, -0.9, "opposition"),
)
_OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}
_NODE_ALIASES = ("North Node", "Node", "True Node", "Mean Node", "Rahu")
_LILITH_ALIASES = ("Lilith", "Black Moon Lilith", "True Lilith")
_TAG_WEIGHT_RE = re.compile(r"\(([+-]?\d+(?:\.\d+)?)\)\s*$|\s([+-]?\d+(?:\.\d+)?)\s*$")


def _first_planet(planets: Dict[str, Dict[str, Any]], *names: str) -> Optional[Dict[str, Any]]:
    for name in names:
        row = planets.get(name)
        if isinstance(row, dict):
            return row
    return None


def _planet_row(planets: Dict[str, Dict[str, Any]], name: Optional[str]) -> Dict[str, Any]:
    row = planets.get(name or "")
    return row if isinstance(row, dict) else {}


def _planet_lon(planets: Dict[str, Dict[str, Any]], name: Optional[str]) -> Optional[float]:
    row = _planet_row(planets, name)
    value = _safe_float(row.get("longitude"))
    return value % 360.0 if value is not None else None


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


def _planet_retrograde(planets: Dict[str, Dict[str, Any]], name: Optional[str]) -> bool:
    row = _planet_row(planets, name)
    if not row:
        return False
    if isinstance(row.get("retrograde"), bool):
        return bool(row.get("retrograde"))
    speed = _safe_float(row.get("speed"))
    if speed is None:
        speed = _safe_float(row.get("daily_motion"))
    return bool(speed is not None and speed < 0.0)


def _cusp_lon(cusps: List[float], index: int) -> Optional[float]:
    try:
        return float(cusps[index]) % 360.0
    except Exception:
        return None


def _ruler_for_cusp(cusps: List[float], index: int) -> Optional[str]:
    lon = _cusp_lon(cusps, index)
    return TRAD_RULER.get(_sign_from_lon(lon)) if lon is not None else None


def _moon_sign_preference(moon_lon: Optional[float]) -> tuple[float, Optional[str]]:
    if moon_lon is None:
        return 0.0, None
    sign = _sign_from_lon(moon_lon)
    degree_in_sign = float(moon_lon) % 30.0
    if sign == "Taurus":
        return (3.0 if degree_in_sign < 19.0 else 2.0), ("early Taurus" if degree_in_sign < 19.0 else "late Taurus")
    return _BUSINESS_MOON_SIGN_SCORES.get(sign, 0.0), sign


def _moon_phase_bonus(planets: Dict[str, Dict[str, Any]]) -> tuple[float, Optional[str]]:
    sun_lon = _planet_lon(planets, "Sun")
    moon_lon = _planet_lon(planets, "Moon")
    if sun_lon is None or moon_lon is None:
        return 0.0, None
    elongation = (moon_lon - sun_lon) % 360.0
    if 0.0 < elongation < 180.0:
        value = 2.0 if elongation <= 90.0 else 3.0
        label = f"Event Moon waxing bonus (+{value:.1f})"
        return value, label
    return 0.0, None


def _score_business_moon_day(election_cd: Dict[str, Any]) -> tuple[float, Optional[str]]:
    moon_day = election_cd.get("moon_day")
    if not isinstance(moon_day, dict):
        moon_day = compute_moon_day(election_cd)
    if not isinstance(moon_day, dict):
        return 0.0, None
    try:
        nid = int(moon_day.get("nid") or 0)
    except Exception:
        nid = 0
    tags = [str(tag).strip() for tag in list(moon_day.get("interval_tags") or []) if str(tag).strip()]
    first_half = nid <= 16
    if nid == 1:
        return -4.0, "Event Moon day caution: nid 1 (-4.0)"
    if any(tag in {"045", "180"} for tag in tags):
        return -1.0, "Event Moon day caution: 045/180 interval (-1.0)"
    if "060" in tags:
        value = 2.0 if first_half else 1.0
        return value, f"Event Moon day support: 060 interval (+{value:.1f})"
    if "090" in tags:
        value = -3.0 if first_half else -2.0
        return value, f"Event Moon day caution: 090 interval ({value:.1f})"
    if "120" in tags:
        value = 3.0 if first_half else 2.0
        return value, f"Event Moon day support: 120 interval (+{value:.1f})"
    if "135" in tags:
        value = -2.0 if first_half else -1.0
        return value, f"Event Moon day caution: 135 interval ({value:.1f})"
    return 0.0, None


def _slow_sign_bonus(lon: Optional[float], latitude: Optional[float], *, label: str) -> tuple[float, Optional[str]]:
    if lon is None or latitude is None:
        return 0.0, None
    if abs(float(latitude)) <= 30.0:
        return 0.0, None
    sign = _sign_from_lon(lon)
    table = _SLOW_SIGNS_NORTH if float(latitude) > 0.0 else _SLOW_SIGNS_SOUTH
    value = float(table.get(sign) or 0.0)
    if value <= 0.0:
        return 0.0, None
    return value, f"Event {label} slow-sign support: {sign} (+{value:.1f})"


def _business_target_names(planets: Dict[str, Dict[str, Any]], cusps: List[float]) -> List[str]:
    names: List[str] = []
    for cusp_index in (9, 0, 1):
        ruler = _ruler_for_cusp(cusps, cusp_index)
        if ruler:
            names.append(ruler)
    names.extend(["Mercury", "Saturn"])
    for name in planets:
        house = _planet_house(planets, name, cusps)
        if house == 10 and name not in {"South Node", "Ketu"}:
            names.append(name)
    out: List[str] = []
    seen = set()
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def _soft_aspect(longitude: Optional[float], target: Optional[float]) -> tuple[float, Optional[str]]:
    if longitude is None or target is None:
        return 0.0, None
    sep = _ang_sep(longitude, target)
    for angle, orb, value, label in _RESONANCE_ASPECTS:
        if abs(sep - angle) <= orb:
            return value, label
    return 0.0, None


def _support_aspect(longitude: Optional[float], target: Optional[float]) -> tuple[float, Optional[str]]:
    if longitude is None or target is None:
        return 0.0, None
    sep = _ang_sep(longitude, target)
    for angle, orb, value, label in _SOFT_ASPECTS:
        if abs(sep - angle) <= orb:
            return value, label
    return 0.0, None


def _hard_aspect(longitude: Optional[float], target: Optional[float]) -> tuple[float, Optional[str]]:
    if longitude is None or target is None:
        return 0.0, None
    sep = _ang_sep(longitude, target)
    for angle, orb, value, label in _HARD_ASPECTS:
        if abs(sep - angle) <= orb:
            return value, label
    return 0.0, None


def _fortune_payload(election_cd: Dict[str, Any]) -> tuple[Optional[float], Optional[int]]:
    lots = election_cd.get("arabic_parts") if isinstance(election_cd.get("arabic_parts"), dict) else None
    if not isinstance(lots, dict):
        try:
            from arabic_parts import compute_arabic_parts
        except Exception:
            return None, None
        lots = compute_arabic_parts(election_cd if isinstance(election_cd, dict) else {}) or {}
    pof = lots.get("fortune") or lots.get("Part of Fortune") or lots.get("Fortuna") or lots.get("Fortune")
    if not isinstance(pof, dict):
        return None, None
    lon = _safe_float(pof.get("longitude") if pof.get("longitude") is not None else pof.get("lon"))
    house = None
    if pof.get("house") is not None:
        try:
            house = int(pof.get("house"))
        except Exception:
            house = None
    if house is None and lon is not None:
        house = _house_from_lon(lon, _house_cusps(election_cd))
    return (lon % 360.0 if lon is not None else None), house


def _event_10th_population(planets: Dict[str, Dict[str, Any]], cusps: List[float]) -> int:
    count = 0
    for name in planets:
        if _planet_house(planets, name, cusps) == 10 and name not in {"South Node", "Ketu"}:
            count += 1
    return count


def _score_direct_motion(planets: Dict[str, Dict[str, Any]], cusps: List[float]) -> tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    for name in _business_target_names(planets, cusps):
        if not _planet_row(planets, name):
            continue
        if _planet_retrograde(planets, name):
            score -= 0.7
            tags.append(f"Event direct-motion caution: {name} retrograde (-0.7)")
        else:
            score += 0.7
            tags.append(f"Event direct-motion support: {name} direct (+0.7)")
    return score, tags


def _score_event_business_support(planets: Dict[str, Dict[str, Any]], cusps: List[float]) -> tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    asc_ruler = _ruler_for_cusp(cusps, 0)
    second_ruler = _ruler_for_cusp(cusps, 1)
    mc_ruler = _ruler_for_cusp(cusps, 9)
    left_points: List[Tuple[str, Optional[float]]] = [
        ("Asc ruler", _planet_lon(planets, asc_ruler)),
        ("Moon", _planet_lon(planets, "Moon")),
        ("Mercury", _planet_lon(planets, "Mercury")),
        ("Venus", _planet_lon(planets, "Venus")),
        ("MC", _cusp_lon(cusps, 9)),
    ]
    right_names = _business_target_names(planets, cusps)
    right_points = [(name, _planet_lon(planets, name)) for name in right_names]
    for left_label, left_lon in left_points:
        if left_lon is None:
            continue
        for right_label, right_lon in right_points:
            if right_lon is None or left_label == right_label:
                continue
            delta, aspect_label = _support_aspect(left_lon, right_lon)
            if delta:
                score += delta
                tags.append(f"Event business support: {left_label} {aspect_label} {right_label} (+{delta:.2f})")
    if second_ruler == "Mercury" or mc_ruler == "Mercury" or asc_ruler == "Mercury":
        score += 0.35
        tags.append("Event commerce ruler anchored by Mercury (+0.35)")
    return score, tags


def _score_moon_damage(planets: Dict[str, Dict[str, Any]]) -> tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    moon_lon = _planet_lon(planets, "Moon")
    if moon_lon is None:
        return score, tags
    damage_sets = [
        (("Mars",) + _NODE_ALIASES + _LILITH_ALIASES, 0.0, 6.0, -1.0, "conjunction"),
        (("Saturn", "Uranus", "Neptune") + _LILITH_ALIASES, 0.0, 6.0, -0.9, "conjunction"),
        (("Pluto",), 0.0, 6.0, -1.5, "conjunction"),
        (("Mars",) + _NODE_ALIASES + _LILITH_ALIASES, 90.0, 5.0, -0.9, "square"),
        (("Saturn", "Uranus", "Neptune", "Pluto"), 90.0, 5.0, -0.8, "square"),
        (("Mars",) + _NODE_ALIASES, 180.0, 6.0, -1.0, "opposition"),
        (("Saturn", "Uranus", "Neptune") + _LILITH_ALIASES, 180.0, 6.0, -0.95, "opposition"),
        (("Pluto",), 180.0, 6.0, -1.5, "opposition"),
    ]
    seen: set[tuple[str, str]] = set()
    for names, angle, orb, value, label in damage_sets:
        for name in names:
            row = _first_planet(planets, name)
            if not row:
                continue
            target_name = str(row.get("planet") or name)
            key = (target_name, label)
            if key in seen:
                continue
            target_lon = _safe_float(row.get("longitude"))
            if target_lon is None:
                continue
            if abs(_ang_sep(moon_lon, target_lon % 360.0) - angle) <= orb:
                score += value
                tags.append(f"Event Moon damage: {label} {target_name} ({value:.1f})")
                seen.add(key)
    return score, tags


def _score_house_topology(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    fortune_house: Optional[int],
) -> tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    for name in _OUTER_PLANETS:
        house = _planet_house(planets, name, cusps)
        if house in ANGULAR_HOUSES:
            score -= 1.0
            tags.append(f"Event house caution: {name} in {_ordinal(house)} ({-1.0:.1f})")
        elif house in {2, 3}:
            score -= 0.45
            tags.append(f"Event house caution: {name} in {_ordinal(house)} ({-0.45:.2f})")
    for name in ("Sun", "Venus", "Jupiter"):
        if _planet_house(planets, name, cusps) == 11:
            score += 0.9
            tags.append(f"Event house support: {name} in 11th (+0.9)")
    for name in ("Saturn", "Neptune"):
        if _planet_house(planets, name, cusps) == 10:
            score -= 1.1
            tags.append(f"Event house caution: {name} in 10th (-1.1)")
    if fortune_house == 10:
        score += 1.15
        tags.append("Event Fortuna in 10th (+1.15)")
    elif fortune_house in {8, 12}:
        score -= 1.1
        tags.append(f"Event Fortuna in {_ordinal(fortune_house)} (-1.1)")
    return score, tags


def _planetary_timing_bonus(options: Dict[str, Any]) -> tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    hour_ruler = str(options.get("hour_ruler") or "").strip()
    if hour_ruler in _FAVORED_TIMING_RULERS:
        score += 0.8
        tags.append(f"Event planetary hour support: {hour_ruler} (+0.8)")
    return score, tags


def _participant_business_targets(planets: Dict[str, Dict[str, Any]], cusps: List[float]) -> List[Tuple[str, Optional[float]]]:
    names = _business_target_names(planets, cusps)
    for name in ("Jupiter", "Saturn"):
        if name not in names:
            names.append(name)
    return [(name, _planet_lon(planets, name)) for name in names]


def _extract_tag_weight(tag: Any) -> Optional[float]:
    text = str(tag or "").strip()
    if not text:
        return None
    match = _TAG_WEIGHT_RE.search(text)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    try:
        return float(raw)
    except Exception:
        return None


def _line_channels(tags: Iterable[str], fallback_score: float = 0.0) -> Tuple[float, float]:
    favorable = 0.0
    tense = 0.0
    matched = False
    for tag in list(tags or []):
        weight = _extract_tag_weight(tag)
        if weight is None:
            continue
        matched = True
        if weight >= 0.0:
            favorable += weight
        else:
            tense += abs(weight)
    if not matched:
        if fallback_score >= 0.0:
            favorable = float(fallback_score or 0.0)
        else:
            tense = abs(float(fallback_score or 0.0))
    return round(favorable, 2), round(tense, 2)


def _participant_precision_context(participant: Dict[str, Any]) -> Dict[str, Any]:
    meta = participant.get("meta") if isinstance(participant.get("meta"), dict) else {}
    precision_class = str(
        participant.get("precision_class")
        or meta.get("precision_class")
        or "unknown"
    ).strip().lower() or "unknown"
    precision_safe_raw = participant.get("precision_safe")
    if precision_safe_raw is None:
        precision_safe_raw = meta.get("precision_safe")
    if precision_safe_raw is None:
        precision_safe = precision_class in {"certified", "timed", "known_time"}
    else:
        precision_safe = bool(precision_safe_raw)
    return {
        "precision_class": precision_class,
        "precision_safe": precision_safe,
        "precision_source": str(
            participant.get("precision_source")
            or meta.get("precision_source")
            or "missing_birth_time_quality"
        ).strip() or "missing_birth_time_quality",
    }


def _score_participant_cross_support(
    participant_label: str,
    participant_targets: Sequence[Tuple[str, Optional[float]]],
    event_targets: Sequence[Tuple[str, Optional[float]]],
) -> tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    for left_name, left_lon in participant_targets:
        if left_lon is None:
            continue
        for right_name, right_lon in event_targets:
            if right_lon is None:
                continue
            delta, label = _support_aspect(left_lon, right_lon)
            if delta:
                score += delta
                tags.append(f"{participant_label}: {left_name} {label} event {right_name} (+{delta:.2f})")
                continue
            delta, label = _hard_aspect(left_lon, right_lon)
            if delta:
                score += delta * 0.6
                tags.append(f"{participant_label}: {left_name} {label} event {right_name} ({delta * 0.6:.2f})")
    return score, tags


def _score_participant_fit(
    participant_label: str,
    election_cd: Dict[str, Any],
    participant_cd: Dict[str, Any],
    *,
    event_fortuna_lon: Optional[float],
    event_10th_count: int,
    precision_safe: bool,
) -> tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    event_cusps = _house_cusps(election_cd)
    participant_cusps = _house_cusps(participant_cd)
    event_planets = _collect_planets(election_cd)
    participant_planets = _collect_planets(participant_cd)

    event_targets = [
        ("Moon", _planet_lon(event_planets, "Moon")),
        ("Venus", _planet_lon(event_planets, "Venus")),
        ("Jupiter", _planet_lon(event_planets, "Jupiter")),
    ]
    participant_targets = _participant_business_targets(participant_planets, participant_cusps) if precision_safe else [
        (name, _planet_lon(participant_planets, name))
        for name in ("Mercury", "Jupiter", "Saturn")
    ]
    delta, cross_tags = _score_participant_cross_support(participant_label, participant_targets, event_targets)
    score += delta
    tags.extend(cross_tags)

    event_asc_lon = _cusp_lon(event_cusps, 0)
    participant_asc_lon = _cusp_lon(participant_cusps, 0)
    if precision_safe:
        delta, label = _soft_aspect(participant_asc_lon, event_asc_lon)
        if delta:
            boost = delta + 0.35
            score += boost
            tags.append(f"{participant_label}: Ascendant resonance with event Asc (+{boost:.2f})")
        else:
            delta, label = _hard_aspect(participant_asc_lon, event_asc_lon)
            if delta:
                score += delta * 0.5
                tags.append(f"{participant_label}: Ascendant strain against event Asc ({delta * 0.5:.2f})")

    participant_asc_ruler = _ruler_for_cusp(participant_cusps, 0)
    participant_asc_ruler_lon = _planet_lon(participant_planets, participant_asc_ruler)
    event_moon_lon = _planet_lon(event_planets, "Moon")
    if precision_safe:
        delta, label = _support_aspect(participant_asc_ruler_lon, event_moon_lon)
        if delta:
            score += delta + 0.25
            tags.append(f"{participant_label}: Asc ruler supports event Moon (+{delta + 0.25:.2f})")
        delta, label = _hard_aspect(participant_asc_ruler_lon, event_moon_lon)
        if delta:
            score += delta * 0.5
            tags.append(f"{participant_label}: Asc ruler strains event Moon ({delta * 0.5:.2f})")

    if precision_safe and event_fortuna_lon is not None and participant_asc_lon is not None:
        sep = _ang_sep(event_fortuna_lon, participant_asc_lon)
        if sep <= 3.0:
            score += 1.2
            tags.append(f"{participant_label}: event Fortuna contacts natal Asc (+1.2)")

    if event_10th_count > 0:
        boost = min(1.0, 0.25 * float(event_10th_count))
        score += boost
        tags.append(f"{participant_label}: event 10th populated ({event_10th_count}) (+{boost:.2f})")

    if precision_safe and participant_asc_ruler_lon is not None and event_cusps:
        house = _house_from_lon(participant_asc_ruler_lon, event_cusps)
        if house in {1, 4, 7, 10}:
            boost = 1.35 if house == 10 else 1.05
            score += boost
            tags.append(f"{participant_label}: Asc ruler falls in event {_ordinal(house)} (+{boost:.2f})")
        elif house in {2, 11}:
            score += 0.45
            tags.append(f"{participant_label}: Asc ruler falls in event {_ordinal(house)} (+0.45)")
        elif house in {6, 8, 12}:
            score -= 0.8
            tags.append(f"{participant_label}: Asc ruler falls in event {_ordinal(house)} (-0.8)")

    return score, tags


def _business_beta_is_caution_tag(tag: str) -> bool:
    text = str(tag or "").lower()
    return any(
        fragment in text
        for fragment in (
            "caution",
            "retrograde",
            "strain",
            "damage",
            "weak",
            "negative",
            "loss",
            "sensitive",
            "in 8th",
            "in 12th",
        )
    )


def _split_beta_tags(tags: Iterable[str]) -> tuple[List[str], List[str]]:
    pros: List[str] = []
    cautions: List[str] = []
    for tag in list(tags or []):
        if _business_beta_is_caution_tag(tag):
            cautions.append(tag)
        else:
            pros.append(tag)
    return pros, cautions


def _line_payload(
    *,
    line_id: str,
    kind: str,
    label: str,
    score: float,
    tags: Iterable[str],
    precision_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    line_tags = [str(tag) for tag in list(tags or []) if str(tag).strip()]
    pros, cautions = _split_beta_tags(line_tags)
    favorable, tense = _line_channels(line_tags, fallback_score=float(score or 0.0))
    payload: Dict[str, Any] = {
        "id": line_id,
        "kind": kind,
        "label": label,
        "score": round(float(score or 0.0), 2),
        "favorable": favorable,
        "tense": tense,
        "tags": line_tags,
    }
    if pros:
        payload["pros"] = pros
    if cautions:
        payload["cautions"] = cautions
    if isinstance(precision_context, dict) and precision_context:
        payload.update(
            {
                "precision_class": str(precision_context.get("precision_class") or "").strip() or "unknown",
                "precision_safe": bool(precision_context.get("precision_safe")),
                "precision_source": str(precision_context.get("precision_source") or "").strip() or "unknown",
            }
        )
    return payload


def _score_event_chart(election_cd: Dict[str, Any], options: Dict[str, Any]) -> Score:
    score = 0.0
    tags: List[str] = []
    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    meta = dict(options.get("event_meta") or {})

    moon_lon = _planet_lon(planets, "Moon")
    moon_score, moon_label = _moon_sign_preference(moon_lon)
    if moon_label and moon_score:
        score += moon_score
        tone = "support" if moon_score > 0 else "caution"
        tags.append(f"Event Moon sign {tone}: {moon_label} ({moon_score:+.1f})")

    phase_score, phase_tag = _moon_phase_bonus(planets)
    if phase_tag:
        score += phase_score
        tags.append(phase_tag)

    moon_day_score, moon_day_tag = _score_business_moon_day(election_cd)
    if moon_day_tag:
        score += moon_day_score
        tags.append(moon_day_tag)

    latitude = _safe_float(meta.get("latitude"))
    moon_slow_bonus, moon_slow_tag = _slow_sign_bonus(moon_lon, latitude, label="Moon")
    if moon_slow_tag:
        score += moon_slow_bonus
        tags.append(moon_slow_tag)
    asc_slow_bonus, asc_slow_tag = _slow_sign_bonus(_cusp_lon(cusps, 0), latitude, label="Asc")
    if asc_slow_tag:
        score += asc_slow_bonus
        tags.append(asc_slow_tag)

    delta, rows = _score_direct_motion(planets, cusps)
    score += delta
    tags.extend(rows)

    delta, rows = _planetary_timing_bonus(options)
    score += delta
    tags.extend(rows)

    delta, rows = _score_moon_damage(planets)
    score += delta
    tags.extend(rows)

    delta, rows = _score_event_business_support(planets, cusps)
    score += delta
    tags.extend(rows)

    fortuna_lon, fortuna_house = _fortune_payload(election_cd)
    delta, rows = _score_house_topology(planets, cusps, fortuna_house)
    score += delta
    tags.extend(rows)

    tenth_population = _event_10th_population(planets, cusps)
    if tenth_population:
        boost = min(1.2, 0.25 * float(tenth_population))
        score += boost
        tags.append(f"Event 10th-house population: {tenth_population} (+{boost:.2f})")

    return Score(value=round(score, 2), tags=tags)


def score_business_beta_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    opts = dict(options or {})
    event_score = _score_event_chart(election_cd, opts)
    total = float(event_score.value or 0.0)
    tags = list(event_score.tags or [])
    lines: List[Dict[str, Any]] = [
        _line_payload(
            line_id="event",
            kind="event",
            label="Event line",
            score=float(event_score.value or 0.0),
            tags=event_score.tags or [],
        )
    ]

    event_planets = _collect_planets(election_cd)
    event_cusps = _house_cusps(election_cd)
    event_fortuna_lon, _ = _fortune_payload(election_cd)
    event_10th_count = _event_10th_population(event_planets, event_cusps)

    participants = list(opts.get("business_participants") or [])
    for idx, participant in enumerate(participants):
        if not isinstance(participant, dict):
            continue
        participant_cd = participant.get("chart_data") or {}
        if not isinstance(participant_cd, dict) or not participant_cd:
            continue
        label = str(participant.get("label") or f"Participant {idx + 1}").strip() or f"Participant {idx + 1}"
        precision_context = _participant_precision_context(participant)
        delta, participant_tags = _score_participant_fit(
            label,
            election_cd,
            participant_cd,
            event_fortuna_lon=event_fortuna_lon,
            event_10th_count=event_10th_count,
            precision_safe=bool(precision_context.get("precision_safe")),
        )
        total += delta
        tags.extend(participant_tags)
        lines.append(
            _line_payload(
                line_id=f"participant:{idx + 1}",
                kind="participant",
                label=label,
                score=delta,
                tags=participant_tags,
                precision_context=precision_context,
            )
        )

    pros, cautions = _split_beta_tags(tags)
    return {
        "value": round(total, 2),
        "tags": tags,
        "pros": pros,
        "cautions": cautions,
        "lines": lines,
    }


__all__ = ["score_business_beta_election"]
