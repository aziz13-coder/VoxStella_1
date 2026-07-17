from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from moon_day import compute_moon_day

try:
    from almutens import compute_chart_almutens
except Exception:  # pragma: no cover - optional in stripped test contexts
    compute_chart_almutens = None  # type: ignore

from .common import (
    ANGULAR_HOUSES,
    BENEFICS,
    MALEFICS,
    Score,
    TRAD_RULER,
    _ang_sep,
    _collect_planets,
    _house_cusps,
    _house_from_lon,
    _is_via_combusta,
    _ordinal,
    _safe_float,
    _sign_from_lon,
)


_RAPID_SIGNS_NORTH = {"Capricorn": 2.0, "Aquarius": 3.0, "Pisces": 3.0, "Aries": 1.0}
_RAPID_SIGNS_SOUTH = {"Cancer": 2.0, "Leo": 3.0, "Virgo": 3.0, "Libra": 1.0}
_SLOW_SIGNS_NORTH = {"Cancer": 2.0, "Leo": 3.0, "Virgo": 3.0, "Libra": 1.0}
_SLOW_SIGNS_SOUTH = {"Capricorn": 2.0, "Aquarius": 3.0, "Pisces": 3.0, "Aries": 1.0}
_FAVORED_HOUR_RULERS = {"Mercury", "Venus", "Jupiter"}
_OUTER_PRESSURE = {"Uranus", "Neptune", "Pluto"}
_NODE_ALIASES = ("North Node", "Node", "True Node", "Mean Node", "Rahu")
_LILITH_ALIASES = ("Lilith", "Black Moon Lilith", "True Lilith")
_SOFT_ASPECTS: Sequence[Tuple[float, float, float, str]] = (
    (60.0, 4.5, 0.7, "sextile"),
    (120.0, 5.5, 0.9, "trine"),
)
_RESONANCE_ASPECTS: Sequence[Tuple[float, float, float, str]] = (
    (0.0, 5.0, 1.0, "conjunction"),
    (60.0, 4.5, 0.75, "sextile"),
    (120.0, 5.5, 0.95, "trine"),
)
_HARD_ASPECTS: Sequence[Tuple[float, float, float, str]] = (
    (90.0, 5.0, -0.85, "square"),
    (180.0, 6.0, -0.9, "opposition"),
)
_MAJOR_ASPECTS: Sequence[Tuple[float, float, str]] = (
    (0.0, 5.0, "conjunction"),
    (60.0, 4.5, "sextile"),
    (90.0, 5.0, "square"),
    (120.0, 5.5, "trine"),
    (180.0, 6.0, "opposition"),
)
_TAG_WEIGHT_RE = re.compile(r"\(([+-]?\d+(?:\.\d+)?)\)\s*$|\s([+-]?\d+(?:\.\d+)?)\s*$")


def _first_planet(planets: Dict[str, Dict[str, Any]], *names: str) -> Optional[Dict[str, Any]]:
    for name in names:
        row = planets.get(name)
        if isinstance(row, dict):
            return row
    return None


def _planet_row(planets: Dict[str, Dict[str, Any]], name: Optional[str]) -> Dict[str, Any]:
    if not name:
        return {}
    row = planets.get(name)
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


def _unique_names(names: Iterable[Optional[str]]) -> List[str]:
    out: List[str] = []
    seen = set()
    for name in names:
        key = str(name or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _named_points(planets: Dict[str, Dict[str, Any]], names: Iterable[Optional[str]]) -> List[Tuple[str, Optional[float]]]:
    return [(name, _planet_lon(planets, name)) for name in _unique_names(names)]


def _occupants(planets: Dict[str, Dict[str, Any]], cusps: List[float], house: int) -> List[str]:
    out: List[str] = []
    for name in planets:
        if _planet_house(planets, name, cusps) == house:
            out.append(name)
    return out


def _aspect_delta(
    left_lon: Optional[float],
    right_lon: Optional[float],
    specs: Sequence[Tuple[float, float, float, str]],
) -> Tuple[float, Optional[str]]:
    if left_lon is None or right_lon is None:
        return 0.0, None
    sep = _ang_sep(left_lon, right_lon)
    for angle, orb, value, label in specs:
        if abs(sep - angle) <= orb:
            return value, label
    return 0.0, None


def _major_aspect_name(left_lon: Optional[float], right_lon: Optional[float]) -> Optional[str]:
    if left_lon is None or right_lon is None:
        return None
    sep = _ang_sep(left_lon, right_lon)
    for angle, orb, label in _MAJOR_ASPECTS:
        if abs(sep - angle) <= orb:
            return label
    return None


def _fortune_payload(election_cd: Dict[str, Any]) -> Tuple[Optional[float], Optional[int]]:
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


def _estate_is_caution_tag(tag: str) -> bool:
    text = str(tag or "").lower()
    return any(
        fragment in text
        for fragment in (
            "caution",
            "retrograde",
            "strain",
            "pressure",
            "friction",
            "via combusta",
            "malefic",
            "outer planet",
            "phase mismatch",
            "transfer risk",
            "counterparty tie",
        )
    )


def _split_estate_tags(tags: Iterable[str]) -> Tuple[List[str], List[str]]:
    pros: List[str] = []
    cautions: List[str] = []
    for tag in list(tags or []):
        if _estate_is_caution_tag(tag):
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
    pros, cautions = _split_estate_tags(line_tags)
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


def _moon_phase_bonus(planets: Dict[str, Dict[str, Any]], *, direction: str) -> Tuple[float, Optional[str]]:
    sun_lon = _planet_lon(planets, "Sun")
    moon_lon = _planet_lon(planets, "Moon")
    if sun_lon is None or moon_lon is None:
        return 0.0, None
    elongation = (moon_lon - sun_lon) % 360.0
    waxing = 0.0 < elongation < 180.0
    wants_waxing = direction == "sell"
    if waxing == wants_waxing:
        phase_distance = elongation if waxing else (360.0 - elongation)
        value = 2.0 if phase_distance <= 90.0 else 3.0
        phase_label = "waxing" if waxing else "waning"
        return value, f"Event {direction} Moon phase support: {phase_label} (+{value:.1f})"
    phase_label = "waxing" if waxing else "waning"
    return -1.0, f"Event {direction} Moon phase mismatch: {phase_label} (-1.0)"


def _latitude_sign_bonus(
    lon: Optional[float],
    latitude: Optional[float],
    *,
    direction: str,
    label: str,
) -> Tuple[float, Optional[str]]:
    if lon is None or latitude is None or abs(float(latitude)) <= 30.0:
        return 0.0, None
    sign = _sign_from_lon(lon)
    if direction == "buy":
        table = _RAPID_SIGNS_NORTH if float(latitude) > 0.0 else _RAPID_SIGNS_SOUTH
        tone = "rapid"
    else:
        table = _SLOW_SIGNS_NORTH if float(latitude) > 0.0 else _SLOW_SIGNS_SOUTH
        tone = "slow"
    value = float(table.get(sign) or 0.0)
    if value <= 0.0:
        return 0.0, None
    return value, f"Event {label} {tone}-sign estate support: {sign} (+{value:.1f})"


def _score_estate_moon_day(election_cd: Dict[str, Any]) -> Tuple[float, Optional[str]]:
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
        return -3.0, "Event Moon day caution: nid 1 (-3.0)"
    if any(tag in {"045", "180"} for tag in tags):
        return -1.0, "Event Moon day caution: 045/180 interval (-1.0)"
    if "060" in tags:
        value = 1.5 if first_half else 1.0
        return value, f"Event Moon day support: 060 interval (+{value:.1f})"
    if "090" in tags:
        value = -2.5 if first_half else -1.5
        return value, f"Event Moon day caution: 090 interval ({value:.1f})"
    if "120" in tags:
        value = 2.5 if first_half else 1.8
        return value, f"Event Moon day support: 120 interval (+{value:.1f})"
    if "135" in tags:
        value = -1.8 if first_half else -1.0
        return value, f"Event Moon day caution: 135 interval ({value:.1f})"
    return 0.0, None


def _score_direct_motion(planets: Dict[str, Dict[str, Any]], cusps: List[float]) -> Tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    for name in _unique_names(["Mercury", "Mars", "Venus", "Jupiter", _ruler_for_cusp(cusps, 1), _ruler_for_cusp(cusps, 6)]):
        if not _planet_row(planets, name):
            continue
        if _planet_retrograde(planets, name):
            score -= 0.9
            tags.append(f"Event direct-motion caution: {name} retrograde (-0.9)")
        else:
            score += 0.35
            tags.append(f"Event direct-motion support: {name} direct (+0.35)")
    return score, tags


def _score_mercury_mars(planets: Dict[str, Dict[str, Any]]) -> Tuple[float, List[str]]:
    mercury_lon = _planet_lon(planets, "Mercury")
    mars_lon = _planet_lon(planets, "Mars")
    if mercury_lon is None or mars_lon is None:
        return 0.0, []
    sep = _ang_sep(mercury_lon, mars_lon)
    if sep <= 5.0 or abs(sep - 90.0) <= 5.0:
        return -1.5, ["Event Mercury-Mars friction: conjunction/square (-1.5)"]
    if abs(sep - 60.0) <= 4.5 or abs(sep - 120.0) <= 5.5 or abs(sep - 180.0) <= 6.0:
        return -0.5, ["Event Mercury-Mars friction: major aspect (-0.5)"]
    return 0.0, []


def _score_counterparty_money_tie(planets: Dict[str, Dict[str, Any]], cusps: List[float]) -> Tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    second_ruler = _ruler_for_cusp(cusps, 1)
    seventh_ruler = _ruler_for_cusp(cusps, 6)
    aspect = _major_aspect_name(_planet_lon(planets, second_ruler), _planet_lon(planets, seventh_ruler))
    if aspect:
        score -= 0.9
        tags.append(f"Event counterparty tie caution: 2nd ruler {aspect} 7th ruler (-0.9)")
    for label, ruler in (("2nd ruler", second_ruler), ("7th ruler", seventh_ruler)):
        if ruler and _planet_retrograde(planets, ruler):
            score -= 0.8
            tags.append(f"Event {label} retrograde caution: {ruler} (-0.8)")
    return score, tags


def _score_house_topology(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    fortuna_lon: Optional[float],
    fortuna_house: Optional[int],
) -> Tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    ic_lon = _cusp_lon(cusps, 3)
    if ic_lon is not None:
        ic_sign = _sign_from_lon(ic_lon)
        if ic_sign in {"Taurus", "Leo", "Aquarius"}:
            score += 1.2
            tags.append(f"Event IC estate sign support: {ic_sign} (+1.2)")

    for name in ("Mercury",):
        if _planet_house(planets, name, cusps) == 4:
            score += 1.0
            tags.append(f"Event {name} in 4th property support (+1.0)")
    for name in ("Sun", "Venus", "Jupiter"):
        if _planet_house(planets, name, cusps) == 4:
            score += 1.3
            tags.append(f"Event {name} in 4th property support (+1.3)")
    for name in ("Mars", "Saturn", "Uranus", "Neptune", "Pluto"):
        house = _planet_house(planets, name, cusps)
        if house in {1, 4, 7}:
            score -= 1.1
            tags.append(f"Event angular property pressure: {name} in {_ordinal(house)} (-1.1)")

    if fortuna_lon is not None:
        fortuna_sign = _sign_from_lon(fortuna_lon)
        if fortuna_sign in {"Sagittarius", "Pisces"}:
            score += 1.0
            tags.append(f"Event Fortuna estate sign support: {fortuna_sign} (+1.0)")
        for name in ("Mercury", "Venus", "Jupiter"):
            delta, label = _aspect_delta(fortuna_lon, _planet_lon(planets, name), _SOFT_ASPECTS)
            if delta:
                boost = delta + 0.15
                score += boost
                tags.append(f"Event Fortuna {label} {name} support (+{boost:.2f})")
    if fortuna_house in {4, 2, 8}:
        score += 0.45
        tags.append(f"Event Fortuna in estate house {_ordinal(fortuna_house)} (+0.45)")
    return score, tags


def _score_property_support(planets: Dict[str, Dict[str, Any]], cusps: List[float]) -> Tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    property_targets = [("IC", _cusp_lon(cusps, 3)), ("4th ruler", _planet_lon(planets, _ruler_for_cusp(cusps, 3)))]
    for source in ("Venus", "Jupiter"):
        source_lon = _planet_lon(planets, source)
        for target_label, target_lon in property_targets:
            delta, label = _aspect_delta(source_lon, target_lon, _SOFT_ASPECTS)
            if delta:
                score += delta
                tags.append(f"Event property support: {source} {label} {target_label} (+{delta:.2f})")
    pressure_names = ("Mars", "Saturn", "Uranus", "Neptune", "Pluto")
    for source in pressure_names:
        source_lon = _planet_lon(planets, source)
        for target_label, target_lon in property_targets:
            hard_delta, hard_label = _aspect_delta(source_lon, target_lon, _HARD_ASPECTS)
            if hard_delta:
                score += hard_delta
                tags.append(f"Event property pressure: {source} {hard_label} {target_label} ({hard_delta:.2f})")
            elif source in {"Mars", "Saturn"} and source_lon is not None and target_lon is not None and _ang_sep(source_lon, target_lon) <= 5.0:
                score -= 1.0
                tags.append(f"Event property pressure: {source} conjunction {target_label} (-1.0)")
    return score, tags


def _money_or_transfer_targets(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    *,
    house: int,
    label: str,
) -> List[Tuple[str, Optional[float]]]:
    cusp_index = house - 1
    names = _unique_names([_ruler_for_cusp(cusps, cusp_index), *_occupants(planets, cusps, house)])
    points: List[Tuple[str, Optional[float]]] = [(f"{label} cusp", _cusp_lon(cusps, cusp_index))]
    points.extend(_named_points(planets, names))
    return points


def _score_money_set(planets: Dict[str, Dict[str, Any]], targets: Sequence[Tuple[str, Optional[float]]]) -> Tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    for target_label, target_lon in targets:
        if target_lon is None:
            continue
        for benefic, base in (("Venus", 0.8), ("Jupiter", 1.0)):
            delta, label = _aspect_delta(target_lon, _planet_lon(planets, benefic), _SOFT_ASPECTS)
            if delta:
                boost = base + (0.2 if benefic == "Jupiter" else 0.0)
                score += boost
                tags.append(f"Event money-set support: {target_label} {label} {benefic} (+{boost:.1f})")
        for name in ("Sun", "Moon", "Venus", "Jupiter"):
            delta, label = _aspect_delta(target_lon, _planet_lon(planets, name), _SOFT_ASPECTS)
            if delta:
                score += 0.55
                tags.append(f"Event money-set support: {target_label} {label} {name} (+0.55)")
            hard_delta, hard_label = _aspect_delta(target_lon, _planet_lon(planets, name), _HARD_ASPECTS)
            if hard_delta:
                score -= 0.65
                tags.append(f"Event money-set caution: {target_label} {hard_label} {name} (-0.65)")
    return score, tags


def _score_direction_branch(
    planets: Dict[str, Dict[str, Any]],
    cusps: List[float],
    *,
    direction: str,
) -> Tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    actor_points = [("Asc", _cusp_lon(cusps, 0)), ("Asc ruler", _planet_lon(planets, _ruler_for_cusp(cusps, 0)))]
    if direction == "buy":
        targets = _money_or_transfer_targets(planets, cusps, house=2, label="2nd")
        target_house = 2
        target_label = "money set"
    else:
        targets = _money_or_transfer_targets(planets, cusps, house=8, label="8th")
        target_house = 8
        target_label = "transfer set"

    for actor_label, actor_lon in actor_points:
        for target_name, target_lon in targets:
            delta, label = _aspect_delta(actor_lon, target_lon, _SOFT_ASPECTS)
            if delta:
                score += delta
                tags.append(f"Event {direction} support: {actor_label} {label} {target_name} (+{delta:.2f})")
            hard_delta, hard_label = _aspect_delta(actor_lon, target_lon, _HARD_ASPECTS)
            if hard_delta:
                score += hard_delta * 0.65
                tags.append(f"Event {direction} caution: {actor_label} {hard_label} {target_name} ({hard_delta * 0.65:.2f})")

    for name in BENEFICS:
        if _planet_house(planets, name, cusps) == target_house:
            score += 0.8
            tags.append(f"Event {direction} {target_label} support: {name} in {_ordinal(target_house)} (+0.8)")
    for name in MALEFICS:
        if _planet_house(planets, name, cusps) == target_house:
            score -= 0.8
            tags.append(f"Event {direction} {target_label} malefic caution: {name} in {_ordinal(target_house)} (-0.8)")
    return score, tags


def _score_planetary_timing(options: Dict[str, Any]) -> Tuple[float, List[str]]:
    hour_ruler = str(options.get("hour_ruler") or "").strip()
    if hour_ruler in _FAVORED_HOUR_RULERS:
        return 0.8, [f"Event planetary hour estate support: {hour_ruler} (+0.8)"]
    return 0.0, []


def _score_event_chart(election_cd: Dict[str, Any], options: Dict[str, Any]) -> Score:
    score = 0.0
    tags: List[str] = []
    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    meta = dict(options.get("event_meta") or {})
    direction = "sell" if str(options.get("estate_direction") or "").strip().lower() == "sell" else "buy"

    phase_score, phase_tag = _moon_phase_bonus(planets, direction=direction)
    if phase_tag:
        score += phase_score
        tags.append(phase_tag)

    moon_day_score, moon_day_tag = _score_estate_moon_day(election_cd)
    if moon_day_tag:
        score += moon_day_score
        tags.append(moon_day_tag)

    moon_lon = _planet_lon(planets, "Moon")
    if _is_via_combusta(moon_lon):
        score -= 2.0
        tags.append("Event Moon via combusta caution (-2.0)")

    latitude = _safe_float(meta.get("latitude"))
    for label, lon in (("Moon", moon_lon), ("Asc", _cusp_lon(cusps, 0))):
        delta, sign_tag = _latitude_sign_bonus(lon, latitude, direction=direction, label=label)
        if sign_tag:
            score += delta
            tags.append(sign_tag)

    for scorer in (
        lambda: _score_direct_motion(planets, cusps),
        lambda: _score_planetary_timing(options),
        lambda: _score_mercury_mars(planets),
        lambda: _score_counterparty_money_tie(planets, cusps),
    ):
        delta, rows = scorer()
        score += delta
        tags.extend(rows)

    fortuna_lon, fortuna_house = _fortune_payload(election_cd)
    for scorer in (
        lambda: _score_house_topology(planets, cusps, fortuna_lon, fortuna_house),
        lambda: _score_property_support(planets, cusps),
        lambda: _score_money_set(planets, _money_or_transfer_targets(planets, cusps, house=2, label="2nd")),
        lambda: _score_direction_branch(planets, cusps, direction=direction),
    ):
        delta, rows = scorer()
        score += delta
        tags.extend(rows)

    next_aspect = election_cd.get("moon_next_aspect")
    if isinstance(next_aspect, dict):
        next_planet = str(next_aspect.get("planet") or "")
        aspect = str(next_aspect.get("aspect") or "").strip().lower()
        if next_planet in BENEFICS and aspect in {"trine", "sextile", "conjunction"}:
            score += 0.7
            tags.append(f"Event Moon next aspect support: {aspect} {next_planet} (+0.7)")
        if next_planet in MALEFICS | _OUTER_PRESSURE and aspect in {"square", "opposition", "conjunction"}:
            score -= 0.9
            tags.append(f"Event Moon next aspect caution: {aspect} {next_planet} (-0.9)")

    return Score(value=round(score, 2), tags=tags)


def _participant_precision_context(participant: Dict[str, Any]) -> Dict[str, Any]:
    meta = participant.get("meta") if isinstance(participant.get("meta"), dict) else {}
    precision_class = str(
        participant.get("precision_class")
        or meta.get("precision_class")
        or "certified"
    ).strip().lower() or "certified"
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
            or "estate_certified_override"
        ).strip() or "estate_certified_override",
    }


def _almuten_leader(chart_data: Dict[str, Any], key: str) -> Optional[str]:
    if compute_chart_almutens is None:
        return None
    try:
        almutens = compute_chart_almutens(chart_data)
        point = ((almutens or {}).get("points") or {}).get(key)
        if isinstance(point, dict):
            return str(point.get("leader") or "").strip() or None
    except Exception:
        return None
    return None


def _participant_property_targets(participant_cd: Dict[str, Any]) -> List[Tuple[str, Optional[float]]]:
    planets = _collect_planets(participant_cd)
    cusps = _house_cusps(participant_cd)
    leader = _almuten_leader(participant_cd, "house_4") or _ruler_for_cusp(cusps, 3)
    names = _unique_names([leader, *_occupants(planets, cusps, 4), "Venus"])
    targets = [("participant IC", _cusp_lon(cusps, 3))]
    targets.extend((name, _planet_lon(planets, name)) for name in names)
    return targets


def _score_participant_fit(
    participant_label: str,
    election_cd: Dict[str, Any],
    participant_cd: Dict[str, Any],
    *,
    event_fortuna_lon: Optional[float],
    precision_safe: bool,
) -> Tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []
    event_cusps = _house_cusps(election_cd)
    participant_cusps = _house_cusps(participant_cd)
    event_planets = _collect_planets(election_cd)
    participant_planets = _collect_planets(participant_cd)
    property_targets = _participant_property_targets(participant_cd)

    event_moon_lon = _planet_lon(event_planets, "Moon")
    participant_asc_ruler = _ruler_for_cusp(participant_cusps, 0)
    participant_asc_ruler_lon = _planet_lon(participant_planets, participant_asc_ruler)
    if precision_safe:
        delta, label = _aspect_delta(participant_asc_ruler_lon, event_moon_lon, _RESONANCE_ASPECTS)
        if delta:
            score += delta + 0.25
            tags.append(f"{participant_label}: Asc ruler {label} event Moon (+{delta + 0.25:.2f})")
        hard_delta, hard_label = _aspect_delta(participant_asc_ruler_lon, event_moon_lon, _HARD_ASPECTS)
        if hard_delta:
            score += hard_delta * 0.55
            tags.append(f"{participant_label}: Asc ruler strains event Moon ({hard_delta * 0.55:.2f})")

    event_asc = _cusp_lon(event_cusps, 0)
    participant_asc = _cusp_lon(participant_cusps, 0)
    if precision_safe:
        delta, label = _aspect_delta(event_asc, participant_asc, _RESONANCE_ASPECTS)
        if delta:
            boost = delta + 0.35
            score += boost
            tags.append(f"{participant_label}: event Asc {label} participant Asc (+{boost:.2f})")
        hard_delta, hard_label = _aspect_delta(event_asc, participant_asc, _HARD_ASPECTS)
        if hard_delta:
            score += hard_delta * 0.55
            tags.append(f"{participant_label}: event Asc strain to participant Asc ({hard_delta * 0.55:.2f})")

    if precision_safe and event_fortuna_lon is not None and participant_asc is not None:
        delta, label = _aspect_delta(event_fortuna_lon, participant_asc, _RESONANCE_ASPECTS)
        if delta:
            boost = delta + 0.2
            score += boost
            tags.append(f"{participant_label}: event Fortuna {label} participant Asc (+{boost:.2f})")

    for benefic in ("Venus", "Jupiter"):
        benefic_lon = _planet_lon(event_planets, benefic)
        for target_label, target_lon in property_targets:
            delta, label = _aspect_delta(benefic_lon, target_lon, _SOFT_ASPECTS)
            if delta:
                score += delta
                tags.append(f"{participant_label}: event {benefic} {label} {target_label} (+{delta:.2f})")

    pressure_rows = [
        ("Mars", _planet_lon(event_planets, "Mars")),
        ("Saturn", _planet_lon(event_planets, "Saturn")),
        ("Uranus", _planet_lon(event_planets, "Uranus")),
        ("Neptune", _planet_lon(event_planets, "Neptune")),
        ("Pluto", _planet_lon(event_planets, "Pluto")),
    ]
    for alias in _NODE_ALIASES:
        row = _first_planet(event_planets, alias)
        if row:
            pressure_rows.append((str(row.get("planet") or alias), _safe_float(row.get("longitude"))))
            break
    for alias in _LILITH_ALIASES:
        row = _first_planet(event_planets, alias)
        if row:
            pressure_rows.append((str(row.get("planet") or alias), _safe_float(row.get("longitude"))))
            break
    for pressure_name, pressure_lon in pressure_rows:
        if pressure_lon is None:
            continue
        for target_label, target_lon in property_targets:
            hard_delta, hard_label = _aspect_delta(pressure_lon, target_lon, _HARD_ASPECTS)
            if hard_delta:
                score += hard_delta
                tags.append(f"{participant_label}: {pressure_name} pressure on {target_label} ({hard_delta:.2f})")
            elif target_lon is not None and _ang_sep(pressure_lon, target_lon) <= 5.0:
                score -= 0.8
                tags.append(f"{participant_label}: {pressure_name} conjunction pressure on {target_label} (-0.8)")

    event_fourth_count = len(_occupants(event_planets, event_cusps, 4))
    participant_fourth_count = len(_occupants(participant_planets, participant_cusps, 4))
    if event_fourth_count:
        boost = min(0.8, 0.2 * float(event_fourth_count))
        score += boost
        tags.append(f"{participant_label}: event 4th-house population ({event_fourth_count}) (+{boost:.2f})")
    if participant_fourth_count:
        boost = min(0.8, 0.2 * float(participant_fourth_count))
        score += boost
        tags.append(f"{participant_label}: participant 4th-house population ({participant_fourth_count}) (+{boost:.2f})")

    return score, tags


def score_estate_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    opts = dict(options or {})
    direction = "sell" if str(opts.get("estate_direction") or "").strip().lower() == "sell" else "buy"
    opts["estate_direction"] = direction

    event_score = _score_event_chart(election_cd, opts)
    total = float(event_score.value or 0.0)
    tags = list(event_score.tags or [])
    lines: List[Dict[str, Any]] = [
        _line_payload(
            line_id="event",
            kind="event",
            label=f"Event line ({direction})",
            score=float(event_score.value or 0.0),
            tags=event_score.tags or [],
        )
    ]

    participant = opts.get("estate_participant")
    if isinstance(participant, dict):
        participant_cd = participant.get("chart_data") or {}
        if isinstance(participant_cd, dict) and participant_cd:
            label = str(participant.get("label") or "Estate participant").strip() or "Estate participant"
            precision_context = _participant_precision_context(participant)
            event_fortuna_lon, _ = _fortune_payload(election_cd)
            delta, participant_tags = _score_participant_fit(
                label,
                election_cd,
                participant_cd,
                event_fortuna_lon=event_fortuna_lon,
                precision_safe=bool(precision_context.get("precision_safe")),
            )
            total += delta
            tags.extend(participant_tags)
            lines.append(
                _line_payload(
                    line_id="participant:1",
                    kind="participant",
                    label=label,
                    score=delta,
                    tags=participant_tags,
                    precision_context=precision_context,
                )
            )

    pros, cautions = _split_estate_tags(tags)
    return {
        "value": round(total, 2),
        "tags": tags,
        "pros": pros,
        "cautions": cautions,
        "lines": lines,
    }


__all__ = ["score_estate_election"]
