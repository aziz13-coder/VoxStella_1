from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from almutens import compute_chart_almutens

from .common import (
    ANGULAR_HOUSES,
    BENEFICS,
    MALEFICS,
    Score,
    _ang_sep,
    _collect_planets,
    _get_aspects_list,
    _house_cusps,
    _house_from_lon,
    _ordinal,
    _sign_from_lon,
)
from .marriage import (
    _aspect_name,
    _aspect_pair,
    _is_hard_aspect,
    _is_soft_aspect,
    _moon_has_little_light_or_is_slow,
    _moon_is_bright_and_swift,
    _planet_house,
    is_marriage_caution_tag,
)

_CROSS_SOFT_ASPECTS = (
    (0.0, 6.0, 1.0, "conjunction"),
    (60.0, 4.0, 0.75, "sextile"),
    (120.0, 5.0, 1.0, "trine"),
)
_CROSS_HARD_ASPECTS = (
    (90.0, 5.0, -0.75, "square"),
    (180.0, 6.0, -0.9, "opposition"),
)
def _planet_longitude(planets: Dict[str, Dict[str, Any]], name: Optional[str]) -> Optional[float]:
    if not name:
        return None
    row = planets.get(name)
    if not isinstance(row, dict):
        return None
    value = row.get("longitude")
    if value is None:
        return None
    try:
        return float(value) % 360.0
    except Exception:
        return None


def _almuten_point(points: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = points.get(key)
    return value if isinstance(value, dict) else {}


def _soft_support(longitude: Optional[float], target: Optional[float]) -> float:
    if longitude is None or target is None:
        return 0.0
    sep = _ang_sep(longitude, target)
    if sep <= 6.0:
        return 1.15
    if abs(sep - 60.0) <= 4.0:
        return 0.75
    if abs(sep - 120.0) <= 5.0:
        return 1.0
    return 0.0


def _hard_strain(longitude: Optional[float], target: Optional[float]) -> float:
    if longitude is None or target is None:
        return 0.0
    sep = _ang_sep(longitude, target)
    if sep <= 5.0:
        return -1.25
    if abs(sep - 90.0) <= 5.0:
        return -1.0
    if abs(sep - 180.0) <= 6.0:
        return -1.2
    return 0.0


def _beta_marriage_sign_preference(lon: Optional[float], *, factor: float = 1.0) -> tuple[float, str]:
    if lon is None:
        return 0.0, "unknown"
    sign = _sign_from_lon(float(lon))
    degree_in_sign = float(lon) % 30.0
    base = -3.0
    label = sign
    if sign == "Taurus":
        if degree_in_sign < 19.0:
            base = 3.0
            label = "early Taurus"
        else:
            base = -3.0
            label = "late Taurus"
    elif sign == "Gemini":
        if degree_in_sign < 15.0:
            base = 2.0
            label = "early Gemini"
        else:
            base = -2.0
            label = "late Gemini"
    elif sign == "Libra":
        base = 1.0
    elif sign == "Sagittarius":
        base = 1.0
    elif sign == "Capricorn":
        if degree_in_sign < 10.0:
            base = 2.0
            label = "early Capricorn"
        else:
            base = 1.0
    elif sign == "Pisces":
        base = 3.0
    return base * float(factor or 1.0), label


def _aspect_orb(aspect: Dict[str, Any]) -> float:
    try:
        return abs(float(aspect.get("orb")))
    except Exception:
        return 999.0


def _pick_aspect(
    aspects: List[Dict[str, Any]],
    left: str,
    right: str,
    *,
    predicate,
) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    for aspect in _aspect_pair(aspects, left, right):
        if not predicate(_aspect_name(aspect)):
            continue
        if best is None or _aspect_orb(aspect) < _aspect_orb(best):
            best = aspect
    return best


def _beta_is_caution_tag(tag: Any) -> bool:
    lowered = str(tag or "").strip().lower()
    if not lowered:
        return False
    if lowered.startswith("event ") and any(
        token in lowered for token in ("caution:", "strain", "low light", "sensitive house")
    ):
        return True
    if lowered.startswith("snap ") and "strain" in lowered:
        return True
    if "support" in lowered:
        return False
    if lowered.startswith("event asc marriage sign caution:") or lowered.startswith("event moon marriage sign caution:"):
        return True
    return is_marriage_caution_tag(tag)


def _split_beta_tags(tags: List[str]) -> tuple[List[str], List[str]]:
    pros: List[str] = []
    cautions: List[str] = []
    for tag in list(tags or []):
        if _beta_is_caution_tag(tag):
            cautions.append(tag)
        else:
            pros.append(tag)
    return pros, cautions


def _score_beta_moon_day(election_cd: Dict[str, Any]) -> tuple[float, Optional[str]]:
    moon_day = election_cd.get("moon_day")
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


def _score_beta_event_chart(
    election_cd: Dict[str, Any],
    *,
    event_almutens: Optional[Dict[str, Any]] = None,
) -> Score:
    score = 0.0
    tags: List[str] = []
    cusps = _house_cusps(election_cd)
    planets = _collect_planets(election_cd)
    aspects = _get_aspects_list(election_cd) or []
    event_points = (event_almutens or {}).get("points") or {}
    event_7th_almuten = _almuten_point(event_points, "house_7").get("leader")

    try:
        asc_lon = float(cusps[0]) % 360.0 if len(cusps) >= 1 else None
        asc_score, asc_label = _beta_marriage_sign_preference(asc_lon, factor=3.0)
        if asc_score > 0:
            score += asc_score
            tags.append(f"Event Asc marriage sign support: {asc_label} (+{asc_score:.1f})")
        elif asc_score < 0:
            score += asc_score
            tags.append(f"Event Asc marriage sign caution: {asc_label} ({asc_score:.1f})")
    except Exception:
        pass

    try:
        moon = planets.get("Moon") or {}
        moon_lon = float(moon.get("longitude")) if moon.get("longitude") is not None else None
        moon_score, moon_label = _beta_marriage_sign_preference(moon_lon, factor=1.0)
        if moon_score > 0:
            score += moon_score
            tags.append(f"Event Moon marriage sign support: {moon_label} (+{moon_score:.1f})")
        elif moon_score < 0:
            score += moon_score
            tags.append(f"Event Moon marriage sign caution: {moon_label} ({moon_score:.1f})")
    except Exception:
        pass

    try:
        jupiter = planets.get("Jupiter") or {}
        if bool(jupiter.get("retrograde")):
            score += 4.0
            tags.append("Event Jupiter retrograde support (+4.0)")
    except Exception:
        pass

    moon_day_score, moon_day_tag = _score_beta_moon_day(election_cd)
    if moon_day_tag:
        score += moon_day_score
        tags.append(moon_day_tag)

    if _moon_is_bright_and_swift(planets):
        score += 1.1
        tags.append("Event Moon bright and swift")
    elif _moon_has_little_light_or_is_slow(planets):
        score -= 1.1
        tags.append("Event Moon caution: low light or slow")

    moon_house = _planet_house(planets, "Moon", cusps)
    if moon_house in {1, 5, 7, 11}:
        score += 0.9
        tags.append(f"Event Moon in supportive house ({_ordinal(moon_house)})")
    elif moon_house in {6, 8, 12}:
        score -= 1.8
        tags.append(f"Event Moon in sensitive house ({_ordinal(moon_house)})")

    venus_house = _planet_house(planets, "Venus", cusps)
    if venus_house in {1, 5, 7, 10, 11}:
        score += 0.8
        tags.append(f"Event Venus in supportive house ({_ordinal(venus_house)})")
    elif venus_house in {6, 8, 12}:
        score -= 1.2
        tags.append(f"Event Venus in sensitive house ({_ordinal(venus_house)})")

    for benefic in BENEFICS:
        house = _planet_house(planets, benefic, cusps)
        if house in {1, 7, 10, 11}:
            score += 0.7
            tags.append(f"Event {benefic} in supportive {_ordinal(house)}")

    for malefic in MALEFICS:
        house = _planet_house(planets, malefic, cusps)
        if house in ANGULAR_HOUSES:
            penalty = 1.2
            if house in {1, 10}:
                penalty += 0.6
            score -= penalty
            tags.append(f"Event {malefic} strains {_ordinal(house)}")

    next_aspect = election_cd.get("moon_next_aspect")
    if isinstance(next_aspect, dict):
        next_planet = str(next_aspect.get("planet") or "")
        next_name = str(next_aspect.get("aspect") or "")
        soft_targets = {"Venus", "Jupiter"}
        if event_7th_almuten:
            soft_targets.add(str(event_7th_almuten))
        if next_planet in soft_targets and _is_soft_aspect(next_name):
            score += 0.9
            tags.append(f"Event Moon support: {next_name} to {next_planet}")
        if next_planet in {"Mars", "Saturn", "Uranus", "Neptune", "Pluto", "Proserpina"} and _is_hard_aspect(next_name):
            score -= 1.4
            tags.append(f"Event Moon strain: {next_name} to {next_planet}")

    target_specs = [("Moon", "Moon"), ("Venus", "Venus"), ("Jupiter", "Jupiter")]
    if event_7th_almuten:
        target_specs.append(("7th-house almuten", str(event_7th_almuten)))
    support_sources = [("Venus", "Venus"), ("Jupiter", "Jupiter")]
    strain_sources = [
        ("Mars", "Mars"),
        ("Saturn", "Saturn"),
        ("Uranus", "Uranus"),
        ("Neptune", "Neptune"),
        ("Pluto", "Pluto"),
        ("Proserpina", "Proserpina"),
    ]

    asc_lon = float(cusps[0]) % 360.0 if len(cusps) >= 1 else None
    for source_label, source_name in support_sources:
        source_lon = _planet_longitude(planets, source_name)
        if _soft_support(source_lon, asc_lon):
            score += 0.8
            tags.append(f"Event {source_label} supports Ascendant")
    for source_label, source_name in strain_sources:
        source_lon = _planet_longitude(planets, source_name)
        if _hard_strain(source_lon, asc_lon):
            score -= 1.0
            tags.append(f"Event {source_label} strains Ascendant")

    for target_label, target_name in target_specs:
        for source_label, source_name in support_sources:
            if source_name == target_name:
                continue
            support_aspect = _pick_aspect(aspects, source_name, target_name, predicate=_is_soft_aspect)
            if support_aspect is None:
                continue
            score += 0.75
            tags.append(f"Event {source_label} supports {target_label} ({_aspect_name(support_aspect)})")
            break
        for source_label, source_name in strain_sources:
            if source_name == target_name:
                continue
            strain_aspect = _pick_aspect(aspects, source_name, target_name, predicate=_is_hard_aspect)
            if strain_aspect is None:
                continue
            score -= 0.9
            tags.append(f"Event {source_label} strains {target_label} ({_aspect_name(strain_aspect)})")
            break

    pros, cautions = _split_beta_tags(tags)
    return Score(round(score, 2), tags, pros=pros, cautions=cautions)


def _cross_group_delta(
    source_longitude: Optional[float],
    target_longitude: Optional[float],
    *,
    weight: float,
) -> float:
    if source_longitude is None or target_longitude is None:
        return 0.0
    sep = _ang_sep(source_longitude, target_longitude)
    for exact, orb, factor, _name in _CROSS_SOFT_ASPECTS:
        if abs(sep - exact) <= orb:
            return weight * factor
    for exact, orb, factor, _name in _CROSS_HARD_ASPECTS:
        if abs(sep - exact) <= orb:
            return weight * factor
    return 0.0


def _participant_cross_score(
    participant_label: str,
    election_cd: Dict[str, Any],
    participant_cd: Dict[str, Any],
    *,
    event_almutens: Dict[str, Any],
) -> Tuple[float, List[str]]:
    score = 0.0
    tags: List[str] = []

    event_planets = _collect_planets(election_cd)
    participant_planets = _collect_planets(participant_cd)
    participant_cusps = _house_cusps(participant_cd)

    participant_almutens = compute_chart_almutens(participant_cd)
    event_points = event_almutens.get("points") or {}
    participant_points = participant_almutens.get("points") or {}

    event_asc_almuten = _almuten_point(event_points, "ascendant").get("leader")
    event_7th_almuten = _almuten_point(event_points, "house_7").get("leader")

    participant_asc = _almuten_point(participant_points, "ascendant")
    participant_mc = _almuten_point(participant_points, "midheaven")
    participant_2nd = _almuten_point(participant_points, "house_2")
    participant_7th = _almuten_point(participant_points, "house_7")

    participant_asc_almuten = participant_asc.get("leader")
    participant_2nd_almuten = participant_2nd.get("leader")
    participant_7th_almuten = participant_7th.get("leader")

    always_on_rules = (
        ("Jupiter", "Venus", 1.8),
        ("Venus", "Jupiter", 1.6),
        ("Jupiter", "Uranus", 1.35),
        ("Mercury", "Jupiter", 1.15),
        ("Jupiter", "Jupiter", 1.0),
        ("Neptune", "Jupiter", 0.95),
    )
    always_on_support = 0.0
    always_on_strain = 0.0
    support_hits = 0
    strain_hits = 0
    for event_name, participant_name, weight in always_on_rules:
        delta = _cross_group_delta(
            _planet_longitude(event_planets, event_name),
            _planet_longitude(participant_planets, participant_name),
            weight=weight,
        )
        if delta > 0:
            always_on_support += delta
            support_hits += 1
        elif delta < 0:
            always_on_strain += delta
            strain_hits += 1
    if support_hits:
        score += always_on_support
        tags.append(f"{participant_label}: always-on cross support {support_hits} hits (+{always_on_support:.1f})")
    if strain_hits:
        score += always_on_strain
        tags.append(f"{participant_label}: always-on cross strain {strain_hits} hits ({always_on_strain:.1f})")

    if event_7th_almuten and participant_7th_almuten and event_7th_almuten == participant_7th_almuten:
        score += 2.5
        tags.append(f"{participant_label}: event 7th almuten matches participant 7th almuten")
    elif event_7th_almuten and event_7th_almuten in {participant_asc_almuten, participant_2nd_almuten}:
        score += 1.25
        tags.append(f"{participant_label}: event 7th almuten agrees with participant 1st/2nd almutens")

    if event_asc_almuten and participant_7th_almuten and event_asc_almuten == participant_7th_almuten:
        score += 1.0
        tags.append(f"{participant_label}: event Asc almuten supports participant 7th almuten")

    participant_anchor_lons = {
        "Asc": participant_asc.get("longitude"),
        "MC": participant_mc.get("longitude"),
        "2nd": participant_2nd.get("longitude"),
        "7th": participant_7th.get("longitude"),
    }
    participant_sensitive_lons = {
        "1st almuten": _planet_longitude(participant_planets, participant_asc_almuten),
        "2nd almuten": _planet_longitude(participant_planets, participant_2nd_almuten),
        "7th almuten": _planet_longitude(participant_planets, participant_7th_almuten),
    }
    target_lons = [
        value for value in [*participant_anchor_lons.values(), *participant_sensitive_lons.values()]
        if value is not None
    ]

    precise_support = 0.0
    precise_strain = 0.0
    precise_support_hits = 0
    precise_strain_hits = 0

    event_jupiter_lon = _planet_longitude(event_planets, "Jupiter")
    if event_jupiter_lon is not None:
        house = _house_from_lon(event_jupiter_lon, participant_cusps)
        if house in {1, 7}:
            precise_support += 1.5
            precise_support_hits += 1
        elif house in {2, 10}:
            precise_support += 0.75
            precise_support_hits += 1
        elif house in {6, 8, 12}:
            precise_strain -= 0.75
            precise_strain_hits += 1
        for target in target_lons:
            soft_delta = _soft_support(event_jupiter_lon, target)
            if soft_delta:
                precise_support += soft_delta
                precise_support_hits += 1
                continue
            hard_delta = _hard_strain(event_jupiter_lon, target)
            if hard_delta:
                precise_strain += hard_delta * 0.6
                precise_strain_hits += 1

    event_7th_lon = _planet_longitude(event_planets, event_7th_almuten)
    event_7th_targets = [
        participant_anchor_lons.get("Asc"),
        participant_anchor_lons.get("7th"),
        participant_sensitive_lons.get("1st almuten"),
        participant_sensitive_lons.get("7th almuten"),
    ]
    for target in [value for value in event_7th_targets if value is not None]:
        soft_delta = _soft_support(event_7th_lon, target)
        if soft_delta:
            precise_support += soft_delta * 0.85
            precise_support_hits += 1
            continue
        hard_delta = _hard_strain(event_7th_lon, target)
        if hard_delta:
            precise_strain += hard_delta * 0.5
            precise_strain_hits += 1

    if precise_support_hits:
        score += precise_support
        tags.append(f"{participant_label}: house/cusp fit {precise_support_hits} hits (+{precise_support:.1f})")
    if precise_strain_hits:
        score += precise_strain
        tags.append(f"{participant_label}: house/cusp strain {precise_strain_hits} hits ({precise_strain:.1f})")

    return score, tags


def score_marriage_beta_election(
    election_cd: Dict[str, Any],
    *,
    natal_hits: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Score:
    opts = dict(options or {})
    participant_a_cd = opts.get("participant_a_cd") or {}
    participant_b_cd = opts.get("participant_b_cd") or {}
    event_almutens = compute_chart_almutens(election_cd)
    event_score = _score_beta_event_chart(election_cd, event_almutens=event_almutens)
    total = float(event_score.value or 0.0)
    tags = list(event_score.tags or [])

    if isinstance(participant_a_cd, dict) and participant_a_cd:
        participant_score, participant_tags = _participant_cross_score(
            "Snap A",
            election_cd,
            participant_a_cd,
            event_almutens=event_almutens,
        )
        total += participant_score
        tags.extend(participant_tags)

    if isinstance(participant_b_cd, dict) and participant_b_cd:
        participant_score, participant_tags = _participant_cross_score(
            "Snap B",
            election_cd,
            participant_b_cd,
            event_almutens=event_almutens,
        )
        total += participant_score
        tags.extend(participant_tags)
    pros, cautions = _split_beta_tags(tags)
    return Score(round(total, 2), tags, pros=pros, cautions=cautions)


__all__ = ["score_marriage_beta_election"]
