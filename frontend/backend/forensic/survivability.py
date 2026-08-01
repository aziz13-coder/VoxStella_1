from __future__ import annotations

"""
Backend survivability summary for forensic victim analysis.

This intentionally stays transparent and factor-based. The local doctrine used
elsewhere in the repository already treats survival/recovery judgments as a
balance of:
  - significator condition and dignity
  - Moon testimony
  - benefic support
  - malefic pressure
  - explicit death-edge testimony

That makes this a better fit than a frontend-only dignity heuristic.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Tuple


SIGN_RULERS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

BENEFICS = {"Venus", "Jupiter"}
MALEFICS = {"Mars", "Saturn"}
SUPPORT_ASPECT_WEIGHTS = {
    "conjunction": 2.0,
    "trine": 1.8,
    "sextile": 1.4,
}
DANGER_ASPECT_WEIGHTS = {
    "conjunction": 2.4,
    "opposition": 2.1,
    "square": 1.8,
}
SUPPORT_MAX_ORB = 6.0
DANGER_MAX_ORB = 7.0
LIGHT_MEDIATION_SOFT_ASPECTS = {"trine", "sextile"}
LIGHT_MEDIATION_HARD_ASPECTS = {"square", "opposition"}
LIGHT_MEDIATION_POSITIVE_CAP = 1.1
LIGHT_MEDIATION_NEGATIVE_CAP = -1.2


@dataclass(frozen=True)
class SurvivabilityPolicy:
    """Versioned classification thresholds, separate from feature scoring."""

    version: str = "deduplicated_v2"
    abduction_higher_net: float = 2.75
    abduction_max_fatal: float = 1.5
    abduction_max_danger: float = 2.0
    abduction_low_violence_multiplier: float = 0.45
    abduction_high_violence_multiplier: float = 0.6
    abduction_high_violence_min_count: int = 3
    rescue_min_recovery: float = 1.0
    rescue_min_support: float = 4.5
    rescue_max_fatal: float = 9.0
    fatal_gate_pressure: float = 4.5
    fatal_gate_max_net: float = 1.5
    mechanism_gate_pressure: float = 2.0
    mechanism_gate_max_net: float = 5.0
    weak_rescue_max_recovery: float = 1.0
    weak_rescue_max_support: float = 2.0
    violent_gate_danger: float = 3.0
    violent_gate_fatal: float = 1.5
    violent_gate_max_net: float = 0.5
    higher_net: float = 3.0
    higher_max_fatal: float = 3.0
    lower_net: float = -4.0
    nonfatal_band_net: float = 2.0


DEFAULT_SURVIVABILITY_POLICY = SurvivabilityPolicy()


def _normalize_case_type(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"child", "adult_female", "general"}:
        return raw
    return "general"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def _aspect_iter(aspects: Dict[str, Dict[str, Any]], planet: str) -> Iterable[Tuple[str, Dict[str, Any]]]:
    if not planet:
        return []
    seen = set()
    for key, rec in (aspects or {}).items():
        try:
            p1, p2 = key.split("_to_")
        except Exception:
            continue
        if p1 == planet:
            other = p2
        elif p2 == planet:
            other = p1
        else:
            continue
        aspect_type = str((rec or {}).get("type") or "").lower()
        orb = round(_to_float((rec or {}).get("orb"), 999.0), 3)
        applying = bool((rec or {}).get("applying") is True)
        sig = (other, aspect_type, orb, applying)
        if sig in seen:
            continue
        seen.add(sig)
        yield other, rec


def _house_group(house: Any) -> str:
    h = _to_int(house)
    if h is None or h < 1 or h > 12:
        return "unknown"
    if h in (1, 4, 7, 10):
        return "angular"
    if h in (2, 5, 8, 11):
        return "succedent"
    return "cadent"


def _orb_weight(orb: float, *, max_orb: float) -> float:
    if orb > max_orb:
        return 0.0
    if orb <= 0.5:
        return 1.35
    if orb <= 1.0:
        return 1.2
    if orb <= 2.0:
        return 1.05
    if orb <= 3.5:
        return 0.9
    if orb <= 5.0:
        return 0.7
    return 0.5


def _format_signed(value: float) -> str:
    rounded = round(value, 2)
    if rounded > 0:
        return f"+{rounded:g}"
    return f"{rounded:g}"


def _finding_ids(findings: List[Dict[str, Any]]) -> set[str]:
    return {
        str((finding or {}).get("id") or "").strip()
        for finding in findings or []
        if str((finding or {}).get("id") or "").strip()
        and (finding or {}).get("scoring_eligible", True) is not False
    }


_KNOWN_PERSON_VIOLENCE_IDS = {
    "violence_known_person_social_concealment_pattern",
    "violence_known_person_home_axis_pressure",
    "domestic_partner_known_spouse_homicide",
    "family_home_opponent_homicide_axis",
    "family_parental_axis_homicide",
    "family_parricide_homicide_cluster",
}
_TRANSPORT_HARM_IDS = {
    "vehicle_crash_or_transport_harm_pattern",
    "travel_accident_or_disaster_pattern",
    "waterborne_accident_or_disaster_pattern",
}
_CHILD_CONTEXT_IDS = {
    "child_house_under_stress",
    "child_family_overlap",
    "child_parental_harm_cluster",
    "context_child_case_axis",
    "family_custody_child_violence_axis",
    "family_child_homicide_axis_cluster",
}
_FAMILY_FATAL_IDS = {
    "family_home_opponent_homicide_axis",
    "family_parental_axis_homicide",
    "domestic_partner_known_spouse_homicide",
}

_FATAL_RULE_FAMILIES = {
    "direct lethal-harm testimony": {
        "violence_life_death_overlap": 2.2,
        "domestic_partner_known_spouse_homicide": 2.4,
        "family_child_homicide_axis_cluster": 2.4,
        "family_home_opponent_homicide_axis": 2.2,
        "family_parental_axis_homicide": 2.2,
        "family_parricide_homicide_cluster": 2.4,
        "violence_proxy_or_contract_attack_pattern": 2.0,
        "violence_known_person_social_concealment_pattern": 1.8,
        "violence_known_person_home_axis_pressure": 1.8,
        "violence_home_entry_service_pretext_pattern": 1.8,
        "violence_water_death_under_malefic_pressure": 1.8,
    },
    "concealed-harm testimony": {
        "violence_hidden_victim_with_angular_malefic": 1.5,
        "violence_malefic_in_8th_with_hidden_context": 1.5,
    },
    "accident/disaster mechanism": {
        "vehicle_crash_or_transport_harm_pattern": 2.0,
        "travel_accident_or_disaster_pattern": 1.8,
        "waterborne_accident_or_disaster_pattern": 1.8,
    },
    "water danger/recovery testimony": {
        "water_death_edge_disappearance_signature": 1.5,
        "water_disappearance_signatures": 0.8,
    },
}


def _mechanism_flags(
    findings: List[Dict[str, Any]],
    categories: Dict[str, int],
) -> Dict[str, bool]:
    del categories  # Rule IDs are the stable scoring interface.
    ids = _finding_ids(findings)
    violence_ids = {rule_id for rule_id in ids if rule_id.startswith("violence_")}
    abduction_ids = {rule_id for rule_id in ids if rule_id.startswith("abduction_") or rule_id.startswith("missing_person_")}

    return {
        "known_person_violence": bool(ids & _KNOWN_PERSON_VIOLENCE_IDS),
        "transport_harm": bool(ids & _TRANSPORT_HARM_IDS),
        "child_witness_violence": bool(violence_ids and ids & _CHILD_CONTEXT_IDS and not abduction_ids),
        "family_household_harm": bool(
            ids & _FAMILY_FATAL_IDS
            or (
                "family_household_relationship_cluster" in ids
                and bool(violence_ids or ids & {"malefics_in_6th", "venus_detriment_with_saturn"})
            )
        ),
    }


def _derive_victim_significators(features: Dict[str, Any], case_type: str) -> List[str]:
    houses = (features.get("houses") or {}) if isinstance(features, dict) else {}
    primary = houses.get("first_ruler") or SIGN_RULERS.get((houses.get("signs") or {}).get("1"))
    out: List[str] = []
    # Local forensic doctrine consistently treats the Moon as a co-significator
    # and explicitly adds Mercury for a missing or harmed child. It also warns
    # against inferring a person's sex from Venus/Mars, so adult_female does not
    # receive a sex-based natural co-ruler here.
    contextual = ["Mercury"] if _normalize_case_type(case_type) == "child" else []
    for item in [primary, "Moon", *contextual]:
        if item and item not in out:
            out.append(item)
    return out


def _derive_perpetrator_significators(features: Dict[str, Any]) -> List[str]:
    houses = (features.get("houses") or {}) if isinstance(features, dict) else {}
    primary = houses.get("seventh_ruler") or SIGN_RULERS.get((houses.get("signs") or {}).get("7"))
    out: List[str] = []
    if primary:
        out.append(str(primary))
    return out


def _normalize_house_rulers(raw: Dict[Any, Any]) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for key, value in (raw or {}).items():
        try:
            out[int(key)] = str(value)
        except Exception:
            continue
    return out


def _vitality_component(
    planets: Dict[str, Dict[str, Any]],
    solar: Dict[str, List[str]],
    victim_significators: List[str],
) -> Tuple[float, List[str]]:
    score = 0.0
    evidence: List[str] = []
    for planet in victim_significators:
        info = planets.get(planet) or {}
        if not info:
            continue
        dignity = _to_float(info.get("dignity_score"))
        dignity_pts = max(-2.5, min(2.5, dignity * 0.5))
        if dignity_pts:
            score += dignity_pts
            evidence.append(f"{planet} dignity {_format_signed(dignity_pts)}")

        group = _house_group(info.get("house"))
        if group == "angular":
            score += 1.0
            evidence.append(f"{planet} angular +1")
        elif group == "succedent":
            score += 0.5
            evidence.append(f"{planet} succedent +0.5")
        elif group == "cadent":
            score -= 0.75
            evidence.append(f"{planet} cadent -0.75")

        house = _to_int(info.get("house"))
        if house == 8:
            score -= 1.25
            evidence.append(f"{planet} in 8th -1.25")
        elif house == 12:
            score -= 1.5
            evidence.append(f"{planet} in 12th -1.5")

        if planet in set(solar.get("combustion") or []):
            score -= 1.5
            evidence.append(f"{planet} combust -1.5")
        elif planet in set(solar.get("under_beams") or []):
            score -= 0.75
            evidence.append(f"{planet} under beams -0.75")
        elif planet in set(solar.get("cazimi") or []):
            score += 1.5
            evidence.append(f"{planet} cazimi +1.5")
    return score, evidence


def _accidental_power_component(
    features: Dict[str, Any],
    planets: Dict[str, Dict[str, Any]],
    victim_significators: List[str],
) -> Tuple[float, List[str]]:
    """
    Source-backed accidental strength refinement.

    The local forensic corpus repeatedly treats angular rulers and planets in
    angular houses as the dominant testimonies in an event chart. The extra
    weight here is intentionally modest: it rewards an already-relevant victim
    significator when it is both an angular ruler and well-placed by house.
    """
    house_rulers = _normalize_house_rulers(features.get("house_rulers") or {})
    score = 0.0
    evidence: List[str] = []
    for planet in victim_significators:
        info = planets.get(planet) or {}
        if not info:
            continue
        ruled_angles = [house for house in (1, 4, 7, 10) if house_rulers.get(house) == planet]
        if not ruled_angles:
            continue
        group = _house_group(info.get("house"))
        if group == "angular":
            pts = 0.9 + max(0, len(ruled_angles) - 1) * 0.2
            score += pts
            evidence.append(f"{planet} angular ruler in angular house +{pts:g}")
        elif group == "succedent":
            pts = 0.3 + max(0, len(ruled_angles) - 1) * 0.1
            score += pts
            evidence.append(f"{planet} angular ruler with steady placement +{pts:g}")
    return score, evidence


def _benefic_support_component(
    features: Dict[str, Any],
    victim_significators: List[str],
) -> Tuple[float, List[str]]:
    aspects = features.get("aspects") or {}
    score = 0.0
    evidence: List[str] = []
    watched = list(dict.fromkeys(victim_significators + ["Moon"]))
    for planet in watched:
        for other, rec in _aspect_iter(aspects, planet):
            if other not in BENEFICS:
                continue
            aspect_type = str(rec.get("type") or "").lower()
            base = SUPPORT_ASPECT_WEIGHTS.get(aspect_type)
            if not base:
                continue
            orb = _to_float(rec.get("orb"), 999.0)
            orb_factor = _orb_weight(orb, max_orb=SUPPORT_MAX_ORB)
            if orb_factor <= 0:
                continue
            applying_bonus = 1.1 if rec.get("applying") is True else 1.0
            pts = round(base * orb_factor * applying_bonus, 2)
            score += pts
            evidence.append(f"{planet} {aspect_type} {other} {_format_signed(pts)}")
    return score, evidence


def _recovery_support_component(
    planets: Dict[str, Dict[str, Any]],
    features: Dict[str, Any],
    victim_significators: List[str],
) -> Tuple[float, List[str]]:
    """
    Source-backed rescue / recovery support.

    The local corpus treats fortunes as meaningful safety testimony when they
    support the victim ruler and Moon, especially when a benefic is itself
    strong by angular placement. This is not a general optimism factor; it is a
    narrow counterweight used when multiple benefic testimonies cluster around
    survival in an otherwise dangerous chart.
    """
    aspects = features.get("aspects") or {}
    score = 0.0
    evidence: List[str] = []

    primary = victim_significators[0] if victim_significators else None
    moon_supported = False
    primary_supported = False
    total_supports = 0

    watched = list(dict.fromkeys(victim_significators + ["Moon"]))
    for planet in watched:
        for other, rec in _aspect_iter(aspects, planet):
            if other not in BENEFICS:
                continue
            aspect_type = str(rec.get("type") or "").lower()
            if aspect_type not in SUPPORT_ASPECT_WEIGHTS:
                continue
            orb = _to_float(rec.get("orb"), 999.0)
            if _orb_weight(orb, max_orb=SUPPORT_MAX_ORB) <= 0:
                continue
            total_supports += 1
            if planet == "Moon":
                moon_supported = True
            if primary and planet == primary:
                primary_supported = True

    if primary_supported and moon_supported:
        score += 1.0
        evidence.append("victim ruler and Moon both receive fortune testimony +1")
    elif moon_supported or primary_supported:
        score += 0.4
        evidence.append("fortune testimony reaches a core life significator +0.4")

    angular_fortunes = []
    for benefic in BENEFICS:
        info = planets.get(benefic) or {}
        if _house_group(info.get("house")) == "angular":
            angular_fortunes.append(benefic)
    if angular_fortunes and total_supports:
        pts = 0.6 if len(angular_fortunes) == 1 else 0.9
        score += pts
        joined = "/".join(sorted(angular_fortunes))
        evidence.append(f"angular fortune support from {joined} +{pts:g}")

    return round(score, 2), evidence


def _light_mediation_participants(light_mediation: Dict[str, Any]) -> List[str]:
    participants: List[str] = []

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            text = value.strip()
            if text and text not in participants:
                participants.append(text)
            return
        if isinstance(value, dict):
            for key in (
                "planet",
                "name",
                "translator",
                "collector",
                "prohibitor",
                "frustrating",
                "frustrated",
                "swift_extreme",
                "receiving_extreme",
                "middle",
                "from",
                "to",
                "target",
            ):
                add(value.get(key))
            add(value.get("participants"))
            add(value.get("collected"))
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                add(item)

    for key in (
        "participants",
        "translator",
        "collector",
        "prohibitor",
        "frustrating",
        "frustrated",
        "swift_extreme",
        "receiving_extreme",
        "middle",
        "from",
        "to",
        "target",
        "collected",
    ):
        add(light_mediation.get(key))
    return participants


def _light_mediation_contact_points(light_mediation: Dict[str, Any]) -> List[str]:
    contacts: List[str] = []

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            text = value.strip()
            if text and text not in contacts:
                contacts.append(text)
            return
        if isinstance(value, dict):
            for key in (
                "planet",
                "name",
                "from",
                "to",
                "middle",
                "target",
                "prohibitor",
                "frustrating",
                "frustrated",
                "swift_extreme",
                "receiving_extreme",
            ):
                add(value.get(key))
            add(value.get("participants"))
            add(value.get("collected"))
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                add(item)

    for key in (
        "participants",
        "from",
        "to",
        "middle",
        "target",
        "prohibitor",
        "frustrating",
        "frustrated",
        "swift_extreme",
        "receiving_extreme",
        "collected",
    ):
        add(light_mediation.get(key))
    return contacts


def _light_mediation_role(
    participants: List[str],
    contact_points: List[str],
    victim_significators: List[str],
    perpetrator_significators: List[str],
) -> str:
    points = set(participants or []) | set(contact_points or [])
    victim_points = set(victim_significators + ["Moon"])
    perpetrator_points = set(perpetrator_significators)
    touches_victim = bool(victim_points.intersection(points))
    touches_perpetrator = bool(perpetrator_points.intersection(points))
    if touches_victim and touches_perpetrator:
        return "victim_perpetrator_bridge"
    if touches_victim:
        return "victim_only"
    if touches_perpetrator:
        return "perpetrator_only"
    return "third_party_only" if points else "unknown"


def _light_mediation_legs(light_mediation: Dict[str, Any]) -> List[Dict[str, Any]]:
    legs: List[Dict[str, Any]] = []
    seen = set()

    def add(value: Any) -> None:
        if isinstance(value, dict):
            if any(key in value for key in ("aspect", "orb", "phase", "partile", "complete_platic")):
                key = (
                    str(value.get("aspect") or "").strip().lower(),
                    str(value.get("orb") or ""),
                    str(value.get("phase") or "").strip().lower(),
                )
                if key not in seen:
                    seen.add(key)
                    legs.append(value)
                return
            for nested_key in ("from_leg", "to_leg", "legs"):
                add(value.get(nested_key))
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                add(item)

    add(light_mediation.get("legs"))
    add(light_mediation.get("from_leg"))
    add(light_mediation.get("to_leg"))
    return legs


def _normalize_aspect_name(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _light_mediation_leg_modifier(legs: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
    score = 0.0
    evidence: List[str] = []
    for leg in legs:
        aspect = _normalize_aspect_name(leg.get("aspect"))
        orb = abs(_to_float(leg.get("orb"), 999.0))
        orb_factor = _orb_weight(orb, max_orb=8.0)
        if aspect in LIGHT_MEDIATION_SOFT_ASPECTS:
            pts = 0.16 * orb_factor
            if leg.get("partile"):
                pts += 0.04
            elif leg.get("complete_platic"):
                pts += 0.02
            score += pts
            evidence.append(f"{aspect} orb {orb:g}")
        elif aspect in LIGHT_MEDIATION_HARD_ASPECTS:
            pts = -0.38 * max(0.75, orb_factor)
            if orb > 6.0:
                pts -= 0.08
            score += pts
            evidence.append(f"{aspect} orb {orb:g}")
        elif aspect == "conjunction":
            evidence.append(f"conjunction orb {orb:g}")
    return round(score, 2), evidence


def _solar_condition_contains(solar: Dict[str, List[str]], key: str, planet: str) -> bool:
    raw = (solar or {}).get(key) or []
    if isinstance(raw, set):
        return planet in raw
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item == planet:
                return True
            if isinstance(item, dict) and str(item.get("planet") or item.get("name") or "") == planet:
                return True
    return False


def _light_mediator_condition_modifier(
    features: Dict[str, Any],
    mediator: str,
) -> Tuple[float, List[str]]:
    planets = (features.get("planets") or {}) if isinstance(features, dict) else {}
    solar = (features.get("solar") or {}) if isinstance(features, dict) else {}
    info = planets.get(mediator) or {}
    score = 0.0
    evidence: List[str] = []

    if info:
        dignity = _to_float(info.get("dignity_score"))
        if dignity >= 2:
            score += 0.16
            evidence.append(f"{mediator} dignified")
        elif dignity > 0:
            score += 0.08
            evidence.append(f"{mediator} modest dignity")
        elif dignity <= -3:
            score -= 0.24
            evidence.append(f"{mediator} debilitated")
        elif dignity < 0:
            score -= 0.14
            evidence.append(f"{mediator} weak dignity")

    if _solar_condition_contains(solar, "combustion", mediator):
        score -= 0.25
        evidence.append(f"{mediator} combust")
    elif _solar_condition_contains(solar, "under_beams", mediator):
        score -= 0.12
        evidence.append(f"{mediator} under beams")
    elif _solar_condition_contains(solar, "cazimi", mediator):
        score += 0.2
        evidence.append(f"{mediator} cazimi")

    return round(score, 2), evidence


def _light_mediation_component(
    features: Dict[str, Any],
    victim_significators: List[str],
) -> Tuple[float, List[str]]:
    """
    Bounded source-backed translation/collection testimony.

    Forensic source notes treat translation as event-moving testimony and
    collection as an infusion into the collecting planet's placement. This is
    deliberately not an outcome override: it only nudges recovery support or
    fatal pressure when the mediation touches the victim ruler or Moon.
    """
    light_mediation = features.get("light_mediation") or {}
    if not isinstance(light_mediation, dict):
        return 0.0, []

    has_translation = bool(light_mediation.get("translation"))
    has_collection = bool(light_mediation.get("collection"))
    has_prohibition = bool(light_mediation.get("prohibition") or light_mediation.get("denial_type"))
    if not (has_translation or has_collection or has_prohibition):
        return 0.0, []

    kind = "prohibition" if has_prohibition else ("translation" if has_translation else "collection")
    mediator = str(
        light_mediation.get("translator")
        or light_mediation.get("collector")
        or light_mediation.get("prohibitor")
        or light_mediation.get("frustrating")
        or light_mediation.get("swift_extreme")
        or light_mediation.get("middle")
        or ""
    ).strip()
    if not mediator:
        mediator = "unspecified"

    participants = _light_mediation_participants(light_mediation)
    contact_points = _light_mediation_contact_points(light_mediation)
    perpetrator_significators = _derive_perpetrator_significators(features)
    role = _light_mediation_role(
        participants,
        contact_points,
        victim_significators,
        perpetrator_significators,
    )
    victim_points = set(victim_significators + ["Moon"])
    context_modifier = 0.0
    context_evidence: List[str] = []
    if not contact_points:
        preposition = "via" if kind == "translation" else "by"
        context_modifier -= 0.35
        context_evidence.append(f"{kind} {preposition} {mediator} limited participant detail")
    elif not victim_points.intersection(contact_points):
        preposition = "via" if kind == "translation" else "by"
        context_modifier -= 0.25
        context_evidence.append(f"{kind} {preposition} {mediator} indirect victim/Moon contact")

    challenge_reasons = []
    for key in ("challenge_reasons", "negative_reasons", "challenges"):
        raw = light_mediation.get(key)
        if isinstance(raw, list):
            challenge_reasons.extend(str(item) for item in raw if item)
        elif raw:
            challenge_reasons.append(str(raw))

    verdict = str(light_mediation.get("verdict") or "").strip().lower()
    unfavorable = (
        light_mediation.get("favorable") is False
        or verdict in {"unfavorable", "hostile", "negative"}
        or bool(challenge_reasons)
    )

    if has_prohibition:
        denial_type = str(light_mediation.get("denial_type") or "prohibition").strip().lower()
        if role == "victim_perpetrator_bridge":
            score = -0.9
        elif role == "victim_only":
            score = -0.7
        elif role == "perpetrator_only":
            score = -0.35
        else:
            score = -0.2
        evidence = (
            f"{denial_type} by {mediator} +{abs(score):g} fatal pressure"
            f" ({role.replace('_', '-')} denial)"
        )
        return round(score, 2), [evidence]

    if kind == "collection":
        mode = str(light_mediation.get("mode") or "").strip().upper()
        preposition = "by"
        if mode in {"BY_SEPARATION", "SEPARATING", "SEPARATION"}:
            context_modifier -= 0.2
            context_evidence.append(f"separating collection {preposition} {mediator}")
        # Match horary_engine.perfection_core: collection requires a slower collector.
        if mediator == "Moon":
            context_modifier -= 0.25
            context_evidence.append(f"swift collector {mediator}")

    if unfavorable or mediator in MALEFICS:
        score = -0.9
        tone = "hostile"
    elif mediator in BENEFICS:
        score = 0.8
        tone = "favorable"
    elif mediator == "Moon":
        score = 0.5
        tone = "favorable"
    else:
        score = 0.2
        tone = "neutral"

    quality_evidence: List[str] = []
    legs = _light_mediation_legs(light_mediation)
    if legs:
        leg_modifier, leg_evidence = _light_mediation_leg_modifier(legs)
        condition_modifier, condition_evidence = _light_mediator_condition_modifier(features, mediator)
        score = round(score + leg_modifier + condition_modifier, 2)
        if tone == "favorable" and not unfavorable:
            score = max(0.0, min(LIGHT_MEDIATION_POSITIVE_CAP, score))
        elif tone == "hostile":
            score = max(LIGHT_MEDIATION_NEGATIVE_CAP, min(0.0, score))
        else:
            score = max(-0.4, min(0.4, score))
        if leg_evidence:
            quality_evidence.append(
                f"aspect/orb quality {_format_signed(leg_modifier)}: {', '.join(leg_evidence)}"
            )
        if condition_evidence:
            quality_evidence.append(
                f"mediator condition {_format_signed(condition_modifier)}: {', '.join(condition_evidence)}"
            )
    if context_modifier or context_evidence:
        score = round(score + context_modifier, 2)
        quality_evidence.append(
            f"context {_format_signed(context_modifier)}: {', '.join(context_evidence)}"
        )

    bridge_upgrade_allowed = not (kind == "collection" and mediator == "Moon")
    if role == "victim_perpetrator_bridge" and score > 0 and not unfavorable and bridge_upgrade_allowed:
        score = round(score + 0.25, 2)
        quality_evidence.append("role +0.25: victim-perpetrator bridge")
    elif role == "perpetrator_only" and not unfavorable:
        score = -0.35
        tone = "hostile"
        quality_evidence.append("role -0.35: perpetrator-only mediation")
    elif role == "third_party_only" and not unfavorable:
        quality_evidence.append("role +0: third-party-only mediation")

    if tone == "favorable" and not unfavorable:
        score = max(0.0, min(LIGHT_MEDIATION_POSITIVE_CAP, score))
    elif tone == "hostile":
        score = max(LIGHT_MEDIATION_NEGATIVE_CAP, min(0.0, score))
    else:
        score = max(-0.4, min(0.4, score))
    if not unfavorable and tone != "hostile" and not legs and (has_translation or has_collection) and score <= 0.0:
        score = 0.05

    preposition = "via" if kind == "translation" else "by"
    if score > 0:
        evidence = f"{tone} {kind} {preposition} {mediator} {_format_signed(score)} recovery support"
    elif score < 0:
        evidence = f"{tone} {kind} {preposition} {mediator} +{abs(score):g} fatal pressure"
    else:
        evidence = f"{tone} {kind} {preposition} {mediator} +0"
    if quality_evidence:
        evidence = f"{evidence} ({'; '.join(quality_evidence)})"
    return round(score, 2), [evidence]


def _lunar_condition_component(
    moon: Dict[str, Any],
    features: Dict[str, Any],
) -> Tuple[float, List[str]]:
    score = 0.0
    evidence: List[str] = []
    if moon.get("void_of_course"):
        score -= 1.0
        evidence.append("Moon void of course -1")
    if moon.get("via_combusta"):
        score -= 1.25
        evidence.append("Moon via combusta -1.25")
    if moon.get("in_4_8_12"):
        score -= 0.75
        evidence.append("Moon in 4/8/12 -0.75")
    if moon.get("hard_malefic_contact"):
        score -= 1.25
        evidence.append("Moon under malefic pressure -1.25")

    moon_house = _to_int(moon.get("house"))
    first_ruler = ((features.get("houses") or {}).get("first_ruler"))
    aspects = features.get("aspects") or {}
    if first_ruler:
        for other, rec in _aspect_iter(aspects, "Moon"):
            if other != first_ruler:
                continue
            typ = str(rec.get("type") or "").lower()
            if typ in SUPPORT_ASPECT_WEIGHTS:
                pts = 0.9 if rec.get("applying") is True else 0.6
                score += pts
                evidence.append(f"Moon linked to victim ruler +{pts:g}")
                break
    if moon_house in (1, 10):
        score += 0.5
        evidence.append("Moon angular +0.5")
    return score, evidence


def _danger_component(
    features: Dict[str, Any],
    victim_significators: List[str],
) -> Tuple[float, List[str]]:
    aspects = features.get("aspects") or {}
    score = 0.0
    evidence: List[str] = []
    watched = list(dict.fromkeys(victim_significators + ["Moon"]))
    for planet in watched:
        for other, rec in _aspect_iter(aspects, planet):
            if other not in MALEFICS:
                continue
            aspect_type = str(rec.get("type") or "").lower()
            base = DANGER_ASPECT_WEIGHTS.get(aspect_type)
            if not base:
                continue
            orb = _to_float(rec.get("orb"), 999.0)
            orb_factor = _orb_weight(orb, max_orb=DANGER_MAX_ORB)
            if orb_factor <= 0:
                continue
            applying_bonus = 1.15 if rec.get("applying") is True else 1.0
            pts = round(base * orb_factor * applying_bonus, 2)
            score += pts
            evidence.append(f"{planet} {aspect_type} {other} +{pts:g} danger")
    return score, evidence


def _fatal_pressure_component(
    features: Dict[str, Any],
    findings: List[Dict[str, Any]],
    categories: Dict[str, int],
) -> Tuple[float, List[str]]:
    houses = features.get("houses") or {}
    moon = features.get("moon") or {}
    del categories
    finding_ids = _finding_ids(findings)
    score = 0.0
    evidence: List[str] = []

    if houses.get("first_ruler_rules_8th"):
        score += 1.5
        evidence.append("victim ruler also rules 8th +1.5")
    if houses.get("first_ruler_in_8_or_12"):
        score += 1.5
        evidence.append("victim ruler in 8th/12th +1.5")
    if moon.get("in_4_8_12") and moon.get("hard_malefic_contact"):
        score += 1.0
        evidence.append("Moon under death pressure +1")

    # Correlated rules often encode the same underlying chart testimony. Score
    # the strongest fired rule once per evidence family instead of adding the
    # category count, title substring, and mechanism bonus for the same rule.
    for family, rule_points in _FATAL_RULE_FAMILIES.items():
        matches = [(rule_id, points) for rule_id, points in rule_points.items() if rule_id in finding_ids]
        if not matches:
            continue
        rule_id, points = max(matches, key=lambda item: (item[1], item[0]))
        score += points
        evidence.append(f"{family} ({rule_id}) +{points:g}")

    if (
        "family_household_relationship_cluster" in finding_ids
        and finding_ids & {"malefics_in_6th", "venus_detriment_with_saturn"}
    ):
        score += 1.5
        evidence.append("family/household harm compound (relationship cluster + malefic access) +1.5")

    return round(score, 2), evidence


def _adjust_fatal_pressure_for_context(
    fatal_pressure: float,
    *,
    abduction_context: bool,
    violence_count: int,
    policy: SurvivabilityPolicy = DEFAULT_SURVIVABILITY_POLICY,
) -> float:
    if abduction_context and fatal_pressure:
        multiplier = (
            policy.abduction_high_violence_multiplier
            if violence_count >= policy.abduction_high_violence_min_count
            else policy.abduction_low_violence_multiplier
        )
        return round(fatal_pressure * multiplier, 2)
    return round(fatal_pressure, 2)


def _classify_survivability_level(
    *,
    net_score: float,
    adjusted_fatal_pressure: float,
    danger_score: float,
    recovery_support_score: float,
    support_score: float,
    abduction_context: bool,
    violent_context: bool,
    fatal_mechanism_context: bool,
    policy: SurvivabilityPolicy = DEFAULT_SURVIVABILITY_POLICY,
) -> str:
    if abduction_context:
        if (
            net_score >= policy.abduction_higher_net
            and adjusted_fatal_pressure < policy.abduction_max_fatal
            and danger_score < policy.abduction_max_danger
        ):
            return "Higher"
        return "Moderate"

    rescue_override = (
        recovery_support_score >= policy.rescue_min_recovery
        and support_score >= policy.rescue_min_support
        and support_score >= danger_score
        and adjusted_fatal_pressure < policy.rescue_max_fatal
    )
    weak_rescue_context = (
        recovery_support_score < policy.weak_rescue_max_recovery
        and support_score < policy.weak_rescue_max_support
    )
    if adjusted_fatal_pressure >= policy.fatal_gate_pressure and net_score <= policy.fatal_gate_max_net and not rescue_override:
        return "Lower"
    if (
        fatal_mechanism_context
        and adjusted_fatal_pressure >= policy.mechanism_gate_pressure
        and net_score <= policy.mechanism_gate_max_net
        and weak_rescue_context
        and not rescue_override
    ):
        return "Lower"
    if (
        violent_context
        and (danger_score >= policy.violent_gate_danger or adjusted_fatal_pressure >= policy.violent_gate_fatal)
        and net_score <= policy.violent_gate_max_net
        and not rescue_override
    ):
        return "Lower"
    if net_score >= policy.higher_net and adjusted_fatal_pressure < policy.higher_max_fatal:
        return "Higher"
    if net_score <= policy.lower_net and not rescue_override:
        return "Lower"
    return "Moderate"


def _classify_survivability_band(
    *,
    level: str,
    net_score: float,
    adjusted_fatal_pressure: float,
    danger_score: float,
    abduction_context: bool,
    policy: SurvivabilityPolicy = DEFAULT_SURVIVABILITY_POLICY,
) -> str:
    if abduction_context:
        if level == "Lower":
            return "fatal_pressure_dominant"
        if (
            net_score >= policy.nonfatal_band_net
            and adjusted_fatal_pressure < policy.abduction_max_fatal
            and danger_score < policy.abduction_max_danger
        ):
            return "release_favored"
        return "risk_loaded_survival"

    if level == "Lower":
        return "fatal_pressure_dominant"
    if net_score >= policy.nonfatal_band_net and adjusted_fatal_pressure < policy.abduction_max_fatal:
        return "nonfatal_tilt"
    return "mixed_nonfatal"


def _light_mediation_threshold_margin(
    *,
    level: str,
    net_score: float,
    adjusted_fatal_pressure: float,
    danger_score: float,
    abduction_context: bool,
    violent_context: bool,
    fatal_mechanism_context: bool,
    policy: SurvivabilityPolicy = DEFAULT_SURVIVABILITY_POLICY,
) -> Dict[str, Any]:
    if abduction_context:
        if level == "Higher":
            return {
                "boundary": "higher_floor",
                "margin": round(net_score - policy.abduction_higher_net, 2),
            }
        return {
            "boundary": "higher_requires_score_2.75_low_fatal_danger",
            "score_margin": round(policy.abduction_higher_net - net_score, 2),
            "fatal_pressure_margin": round(adjusted_fatal_pressure - policy.abduction_max_fatal, 2),
            "danger_margin": round(danger_score - policy.abduction_max_danger, 2),
        }

    if level == "Higher":
        return {
            "boundary": "higher_floor",
            "margin": round(net_score - policy.higher_net, 2),
        }
    if level == "Lower":
        if adjusted_fatal_pressure >= policy.fatal_gate_pressure:
            return {
                "boundary": "fatal_pressure_gate",
                "fatal_pressure_margin": round(adjusted_fatal_pressure - policy.fatal_gate_pressure, 2),
                "score_margin": round(policy.fatal_gate_max_net - net_score, 2),
            }
        if fatal_mechanism_context and adjusted_fatal_pressure >= policy.mechanism_gate_pressure:
            return {
                "boundary": "fatal_mechanism_gate",
                "fatal_pressure_margin": round(adjusted_fatal_pressure - policy.mechanism_gate_pressure, 2),
                "score_margin": round(policy.mechanism_gate_max_net - net_score, 2),
            }
        if violent_context:
            return {
                "boundary": "violent_lower_gate",
                "score_margin": round(policy.violent_gate_max_net - net_score, 2),
            }
        return {
            "boundary": "lower_score_floor",
            "margin": round(policy.lower_net - net_score, 2),
        }

    return {
        "boundary": "moderate_band",
        "higher_score_margin": round(policy.higher_net - net_score, 2),
        "lower_score_margin": round(net_score - policy.lower_net, 2),
        "violent_lower_score_margin": round(net_score - policy.violent_gate_max_net, 2) if violent_context else None,
    }


def _secondary_factor_component(features: Dict[str, Any]) -> Tuple[float, float, List[str], List[str]]:
    analysis = features.get("secondary_factor_analysis") if isinstance(features, dict) else {}
    if not isinstance(analysis, dict) or not analysis.get("enabled"):
        return 0.0, 0.0, [], []
    delta = analysis.get("survivability_delta") or {}
    if not isinstance(delta, dict):
        return 0.0, 0.0, [], []
    recovery = max(0.0, min(0.5, _to_float(delta.get("recovery_support"), 0.0)))
    fatal = max(0.0, min(1.2, _to_float(delta.get("fatal_pressure"), 0.0)))
    raw_evidence = [str(item) for item in analysis.get("evidence") or [] if str(item).strip()]
    recovery_evidence = []
    fatal_evidence = []
    if recovery:
        recovery_evidence = [f"secondary asteroid/degree support +{recovery:g}"] + raw_evidence[:3]
    if fatal:
        fatal_evidence = [f"secondary asteroid/degree pressure +{fatal:g}"] + raw_evidence[:3]
    return recovery, fatal, recovery_evidence, fatal_evidence


def compute_survivability(
    features: Dict[str, Any],
    findings: List[Dict[str, Any]] | None = None,
    categories: Dict[str, int] | None = None,
    *,
    case_type: str = "general",
    policy: SurvivabilityPolicy | None = None,
) -> Dict[str, Any]:
    policy = policy or DEFAULT_SURVIVABILITY_POLICY
    normalized_case_type = _normalize_case_type(case_type)
    planets = (features.get("planets") or {}) if isinstance(features, dict) else {}
    solar = (features.get("solar") or {}) if isinstance(features, dict) else {}
    moon = (features.get("moon") or {}) if isinstance(features, dict) else {}
    findings = findings or []
    categories = categories or {}

    victim_significators = _derive_victim_significators(features, normalized_case_type)

    vitality_score, vitality_evidence = _vitality_component(planets, solar, victim_significators)
    accidental_score, accidental_evidence = _accidental_power_component(features, planets, victim_significators)
    support_score, support_evidence = _benefic_support_component(features, victim_significators)
    recovery_support_score, recovery_support_evidence = _recovery_support_component(
        planets,
        features,
        victim_significators,
    )
    lunar_score, lunar_evidence = _lunar_condition_component(moon, features)
    danger_score, danger_evidence = _danger_component(features, victim_significators)
    fatal_pressure, fatal_evidence = _fatal_pressure_component(features, findings, categories)
    light_mediation_score, light_mediation_evidence = _light_mediation_component(features, victim_significators)
    secondary_recovery_score, secondary_fatal_score, secondary_recovery_evidence, secondary_fatal_evidence = _secondary_factor_component(features)
    recovery_support_without_light = recovery_support_score
    fatal_pressure_without_light = fatal_pressure
    if light_mediation_score > 0:
        recovery_support_score = round(recovery_support_score + light_mediation_score, 2)
        recovery_support_evidence = list(recovery_support_evidence) + light_mediation_evidence
    elif light_mediation_score < 0:
        fatal_pressure = round(fatal_pressure + abs(light_mediation_score), 2)
        fatal_evidence = list(fatal_evidence) + light_mediation_evidence
    recovery_support_before_secondary = recovery_support_score
    fatal_pressure_before_secondary = fatal_pressure
    if secondary_recovery_score:
        recovery_support_score = round(recovery_support_score + secondary_recovery_score, 2)
        recovery_support_evidence = list(recovery_support_evidence) + secondary_recovery_evidence
    if secondary_fatal_score:
        fatal_pressure = round(fatal_pressure + secondary_fatal_score, 2)
        fatal_evidence = list(fatal_evidence) + secondary_fatal_evidence

    mechanism_flags = _mechanism_flags(findings, categories)
    abduction_count = int((categories or {}).get("Abduction", 0) or 0)
    violence_count = int((categories or {}).get("Violence", 0) or 0)
    domestic_fatal_context = bool(mechanism_flags.get("family_household_harm"))
    case_context = features.get("case_context") if isinstance(features, dict) else {}
    case_context = case_context if isinstance(case_context, dict) else {}
    healthcare_child_context = bool(
        case_context.get("healthcare_child_context")
        or (
            case_context.get("child_case")
            and (case_context.get("healthcare_context") or case_context.get("caregiver_context") or case_context.get("institutional_care_context"))
        )
    )
    institutional_child_fatal_context = bool(
        healthcare_child_context
        and abduction_count > 0
        and violence_count > 0
    )
    abduction_context = abduction_count > 0 and not domestic_fatal_context and not institutional_child_fatal_context
    violent_context = violence_count > 0
    fatal_mechanism_context = any(mechanism_flags.values()) or institutional_child_fatal_context

    danger_weight = 0.55 if abduction_context else 0.85
    adjusted_fatal_pressure = _adjust_fatal_pressure_for_context(
        fatal_pressure,
        abduction_context=abduction_context,
        violence_count=violence_count,
        policy=policy,
    )
    if abduction_context and fatal_pressure:
        fatal_evidence = list(fatal_evidence) + [
            f"abduction context scales fatal pressure to {adjusted_fatal_pressure:g}"
        ]
    elif abduction_count > 0 and domestic_fatal_context:
        fatal_evidence = list(fatal_evidence) + [
            "domestic/known-person fatal context keeps abduction weighting from downscaling fatal pressure"
        ]
    elif abduction_count > 0 and institutional_child_fatal_context:
        fatal_evidence = list(fatal_evidence) + [
            "healthcare/caregiver child context keeps abduction weighting from downscaling fatal pressure"
        ]
    adjusted_fatal_without_light = _adjust_fatal_pressure_for_context(
        fatal_pressure_without_light,
        abduction_context=abduction_context,
        violence_count=violence_count,
        policy=policy,
    )
    adjusted_fatal_before_secondary = _adjust_fatal_pressure_for_context(
        fatal_pressure_before_secondary,
        abduction_context=abduction_context,
        violence_count=violence_count,
        policy=policy,
    )

    net_score = round(
        vitality_score + accidental_score + support_score + recovery_support_score + lunar_score - (danger_score * danger_weight) - adjusted_fatal_pressure,
        2,
    )
    net_score_without_light = round(
        vitality_score + accidental_score + support_score + recovery_support_without_light + lunar_score - (danger_score * danger_weight) - adjusted_fatal_without_light,
        2,
    )
    net_score_before_secondary = round(
        vitality_score + accidental_score + support_score + recovery_support_before_secondary + lunar_score - (danger_score * danger_weight) - adjusted_fatal_before_secondary,
        2,
    )

    level = _classify_survivability_level(
        net_score=net_score,
        adjusted_fatal_pressure=adjusted_fatal_pressure,
        danger_score=danger_score,
        recovery_support_score=recovery_support_score,
        support_score=support_score,
        abduction_context=abduction_context,
        violent_context=violent_context,
        fatal_mechanism_context=fatal_mechanism_context,
        policy=policy,
    )
    outcome_band = _classify_survivability_band(
        level=level,
        net_score=net_score,
        adjusted_fatal_pressure=adjusted_fatal_pressure,
        danger_score=danger_score,
        abduction_context=abduction_context,
        policy=policy,
    )
    level_without_light = _classify_survivability_level(
        net_score=net_score_without_light,
        adjusted_fatal_pressure=adjusted_fatal_without_light,
        danger_score=danger_score,
        recovery_support_score=recovery_support_without_light,
        support_score=support_score,
        abduction_context=abduction_context,
        violent_context=violent_context,
        fatal_mechanism_context=fatal_mechanism_context,
        policy=policy,
    )
    outcome_band_without_light = _classify_survivability_band(
        level=level_without_light,
        net_score=net_score_without_light,
        adjusted_fatal_pressure=adjusted_fatal_without_light,
        danger_score=danger_score,
        abduction_context=abduction_context,
        policy=policy,
    )
    level_before_secondary = _classify_survivability_level(
        net_score=net_score_before_secondary,
        adjusted_fatal_pressure=adjusted_fatal_before_secondary,
        danger_score=danger_score,
        recovery_support_score=recovery_support_before_secondary,
        support_score=support_score,
        abduction_context=abduction_context,
        violent_context=violent_context,
        fatal_mechanism_context=fatal_mechanism_context,
        policy=policy,
    )
    outcome_band_before_secondary = _classify_survivability_band(
        level=level_before_secondary,
        net_score=net_score_before_secondary,
        adjusted_fatal_pressure=adjusted_fatal_before_secondary,
        danger_score=danger_score,
        abduction_context=abduction_context,
        policy=policy,
    )

    score_delta_from_light = round(net_score - net_score_without_light, 2)
    level_changed = level != level_without_light
    band_changed = outcome_band != outcome_band_without_light
    if light_mediation_score > 0:
        light_effect = "recovery_support"
        tilt = "recovery_mitigated"
    elif light_mediation_score < 0:
        light_effect = "fatal_pressure"
        tilt = "fatal_pressure_added"
    else:
        light_effect = "none"
        tilt = "none"
    if light_effect == "none":
        visibility = "none"
    elif level_changed or band_changed:
        visibility = "classification"
    elif score_delta_from_light:
        visibility = "raw_only"
    else:
        visibility = "absorbed"
    light_mediation_impact = {
        "effect": light_effect,
        "tilt": tilt,
        "light_mediation_score": round(light_mediation_score, 2),
        "score_without_light_mediation": net_score_without_light,
        "score_delta": score_delta_from_light,
        "level_without_light_mediation": level_without_light,
        "outcome_band_without_light_mediation": outcome_band_without_light,
        "level_changed": level_changed,
        "band_changed": band_changed,
        "visibility": visibility,
        "threshold_margin": _light_mediation_threshold_margin(
            level=level,
            net_score=net_score,
            adjusted_fatal_pressure=adjusted_fatal_pressure,
            danger_score=danger_score,
            abduction_context=abduction_context,
            violent_context=violent_context,
            fatal_mechanism_context=fatal_mechanism_context,
            policy=policy,
        ),
    }
    secondary_factor_impact = {
        "enabled": bool((features.get("secondary_factor_analysis") or {}).get("enabled")) if isinstance(features, dict) else False,
        "recovery_support_delta": round(secondary_recovery_score, 2),
        "fatal_pressure_delta": round(secondary_fatal_score, 2),
        "score_without_secondary_factors": net_score_before_secondary,
        "score_delta": round(net_score - net_score_before_secondary, 2),
        "level_without_secondary_factors": level_before_secondary,
        "outcome_band_without_secondary_factors": outcome_band_before_secondary,
        "level_changed": level != level_before_secondary,
        "band_changed": outcome_band != outcome_band_before_secondary,
        "evidence": list(dict.fromkeys(secondary_recovery_evidence + secondary_fatal_evidence))[:8],
    }
    context_calibration = {
        "healthcare_child_context": bool(healthcare_child_context),
        "institutional_child_fatal_context": bool(institutional_child_fatal_context),
        "abduction_downscale_suppressed": bool(abduction_count > 0 and institutional_child_fatal_context),
        "source_basis": "6th/12th-house institutional-care testimony is treated as access/context in child harm, not as release-favored abduction context.",
    }

    note = (
        "Derived from significator vitality, accidental power, benefic support, Moon testimony, malefic pressure, and explicit death-edge findings."
    )
    if level == "Lower" and (adjusted_fatal_pressure >= 4.5 or fatal_mechanism_context):
        note = "Fatal mechanism testimony outweighs base vitality unless rescue or recovery support is strong."

    return {
        "level": level,
        "score": net_score,
        "score_basis": "symbolic_rule_total_not_probability",
        "classification_policy": asdict(policy),
        "is_statistical_probability": False,
        "outcome_band": outcome_band,
        "case_type": normalized_case_type,
        "victim_significators": victim_significators,
        "classification_context": {
            "abduction_context": bool(abduction_context),
            "violent_context": bool(violent_context),
            "fatal_mechanism_context": bool(fatal_mechanism_context),
            "mechanism_flags": mechanism_flags,
            "danger_weight": danger_weight,
        },
        "light_mediation_impact": light_mediation_impact,
        "secondary_factor_impact": secondary_factor_impact,
        "context_calibration": context_calibration,
        "breakdown": {
            "vitality": round(vitality_score, 2),
            "accidental": round(accidental_score, 2),
            "support": round(support_score, 2),
            "recovery_support": round(recovery_support_score, 2),
            "light_mediation": round(light_mediation_score, 2),
            "secondary_recovery_support": round(secondary_recovery_score, 2),
            "moon": round(lunar_score, 2),
            "danger": round(danger_score, 2),
            "fatal_pressure": round(adjusted_fatal_pressure, 2),
            "secondary_fatal_pressure": round(secondary_fatal_score, 2),
        },
        "evidence": {
            "vitality": vitality_evidence,
            "accidental": accidental_evidence,
            "support": support_evidence,
            "recovery_support": recovery_support_evidence,
            "light_mediation": light_mediation_evidence,
            "secondary_factors": list(dict.fromkeys(secondary_recovery_evidence + secondary_fatal_evidence))[:8],
            "moon": lunar_evidence,
            "danger": danger_evidence,
            "fatal_pressure": fatal_evidence,
        },
        "note": note,
    }
