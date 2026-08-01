from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Set


RELATIONSHIP_LABELS = (
    "intimate_partner",
    "family",
    "friend_acquaintance",
    "stranger_public",
)

SOFT_ASPECTS = {"trine", "sextile"}
HARD_ASPECTS = {"square", "opposition"}
MALEFICS = {"Mars", "Saturn"}
BENEFICS = {"Venus", "Jupiter"}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_planet(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _collect_light_points(value: Any, out: Set[str] | None = None) -> Set[str]:
    points = out if out is not None else set()
    if value is None:
        return points
    if isinstance(value, str):
        text = _normalize_planet(value)
        if text:
            points.add(text)
        return points
    if isinstance(value, Mapping):
        for key in (
            "planet",
            "name",
            "from",
            "to",
            "middle",
            "target",
            "translator",
            "collector",
            "prohibitor",
            "frustrating",
            "frustrated",
            "swift_extreme",
            "receiving_extreme",
            "planet1",
            "planet2",
        ):
            _collect_light_points(value.get(key), points)
        _collect_light_points(value.get("participants"), points)
        _collect_light_points(value.get("collected"), points)
        _collect_light_points(value.get("legs"), points)
        _collect_light_points(value.get("from_leg"), points)
        _collect_light_points(value.get("to_leg"), points)
        return points
    if isinstance(value, Iterable):
        for item in value:
            _collect_light_points(item, points)
    return points


def _light_legs(light_mediation: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    legs: List[Mapping[str, Any]] = []
    seen = set()

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, Mapping):
            if any(key in value for key in ("aspect", "type", "orb", "phase")):
                signature = (
                    str(value.get("aspect") or value.get("type") or "").strip().lower(),
                    str(value.get("orb") or ""),
                    str(value.get("phase") or "").strip().lower(),
                )
                if signature not in seen:
                    seen.add(signature)
                    legs.append(value)
                return
            add(value.get("legs"))
            add(value.get("from_leg"))
            add(value.get("to_leg"))
            return
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            for item in value:
                add(item)

    add(light_mediation.get("legs"))
    add(light_mediation.get("from_leg"))
    add(light_mediation.get("to_leg"))
    return legs


def _add_score(
    scores: MutableMapping[str, float],
    evidence: MutableMapping[str, List[str]],
    label: str,
    points: float,
    reason: str,
) -> None:
    if label not in scores:
        return
    scores[label] = round(scores[label] + points, 2)
    if reason:
        evidence.setdefault(label, []).append(reason)


def _is_applying(aspect: Mapping[str, Any]) -> bool:
    raw = aspect.get("applying")
    if raw is not None:
        return raw in (True, "true", "True", "1", 1)
    return str(aspect.get("phase") or "").strip().lower() == "applying"


def _direct_aspect_entry(features: Mapping[str, Any]) -> Mapping[str, Any]:
    houses = features.get("houses") if isinstance(features, Mapping) else {}
    aspects = features.get("aspects") if isinstance(features, Mapping) else {}
    if not isinstance(houses, Mapping) or not isinstance(aspects, Mapping):
        return {}
    first_ruler = _normalize_planet(houses.get("first_ruler"))
    seventh_ruler = _normalize_planet(houses.get("seventh_ruler"))
    if not first_ruler or not seventh_ruler:
        return {}
    return (
        aspects.get(f"{first_ruler}_to_{seventh_ruler}")
        or aspects.get(f"{seventh_ruler}_to_{first_ruler}")
        or {}
    )


def direct_aspect_relationship_component(features: Mapping[str, Any]) -> Dict[str, Any]:
    aspect = _direct_aspect_entry(features)
    if not isinstance(aspect, Mapping) or not aspect:
        return {
            "aspect": None,
            "orb": None,
            "applying": False,
            "score_delta": 0.0,
            "evidence": [],
        }

    aspect_type = str(aspect.get("type") or aspect.get("aspect") or "").strip().lower().replace(" ", "_")
    orb = abs(_to_float(aspect.get("orb"), 999.0))
    applying = _is_applying(aspect)
    score = 0.2
    tone = "direct"
    if aspect_type == "conjunction":
        score = 1.15
        tone = "conjunction"
    elif aspect_type in SOFT_ASPECTS:
        score = 1.0
        tone = "soft direct aspect"
    elif aspect_type in HARD_ASPECTS:
        score = 0.45
        tone = "hard direct aspect"

    if applying:
        score += 0.25
    else:
        score -= 0.15
    if orb <= 2.0:
        score += 0.25
    elif orb <= 5.0:
        score += 0.1
    elif orb > 6.0:
        score -= 0.15

    score = round(_clamp(score, 0.0, 1.5), 2)
    if aspect_type in HARD_ASPECTS and not applying and orb > 6.0:
        evidence = ["wide hard separating direct aspect"]
    else:
        phase = "applying" if applying else "separating"
        evidence = [f"{tone} {phase} orb {orb:g}"]
    return {
        "aspect": aspect_type or None,
        "orb": None if orb == 999.0 else orb,
        "applying": applying,
        "score_delta": score,
        "evidence": evidence,
    }


def reception_relationship_component(
    features: Mapping[str, Any],
    receptions: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    empty = {
        "score_delta": 0.0,
        "evidence": [],
    }
    if not isinstance(receptions, Mapping):
        return empty
    houses = features.get("houses") if isinstance(features, Mapping) else {}
    if not isinstance(houses, Mapping):
        return empty
    first_ruler = _normalize_planet(houses.get("first_ruler"))
    seventh_ruler = _normalize_planet(houses.get("seventh_ruler"))
    if not first_ruler or not seventh_ruler:
        return empty

    def involves_pair(row: Mapping[str, Any], key_a: str, key_b: str) -> bool:
        a = _normalize_planet(row.get(key_a))
        b = _normalize_planet(row.get(key_b))
        return {a, b} == {first_ruler, seventh_ruler}

    score = 0.0
    evidence: List[str] = []
    for row in receptions.get("mutual") or []:
        if not isinstance(row, Mapping) or not involves_pair(row, "p1", "p2"):
            continue
        strength = _to_float(row.get("strength"), 0.0)
        score += 1.0 + min(0.5, max(0.0, strength) / 20.0)
        evidence.append("mutual reception between victim/perpetrator rulers")
        break

    for row in receptions.get("top_unilateral") or []:
        if not isinstance(row, Mapping) or not involves_pair(row, "receiving", "received"):
            continue
        strength = _to_float(row.get("strength"), 0.0)
        dignities = row.get("dignities") or []
        dignity_bonus = 0.15 if "term" in dignities else 0.0
        score += 0.35 + min(0.35, max(0.0, strength) / 20.0) + dignity_bonus
        evidence.append("directional reception between victim/perpetrator rulers")
        break

    return {
        "score_delta": round(_clamp(score, 0.0, 1.75), 2),
        "evidence": evidence,
    }


def light_mediation_relationship_component(
    features: Mapping[str, Any],
    light_mediation: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    empty = {
        "kind": "none",
        "role": "none",
        "mediator": None,
        "score_delta": 0.0,
        "evidence": [],
    }
    if not isinstance(light_mediation, Mapping):
        return empty

    has_prohibition = bool(light_mediation.get("prohibition") or light_mediation.get("denial_type"))
    has_translation = bool(light_mediation.get("translation"))
    has_collection = bool(light_mediation.get("collection"))
    if not (has_prohibition or has_translation or has_collection):
        return empty

    kind = "prohibition" if has_prohibition else ("translation" if has_translation else "collection")
    mediator = _normalize_planet(
        light_mediation.get("translator")
        or light_mediation.get("collector")
        or light_mediation.get("prohibitor")
        or light_mediation.get("frustrating")
        or light_mediation.get("middle")
    ) or None
    houses = features.get("houses") if isinstance(features, Mapping) else {}
    houses = houses if isinstance(houses, Mapping) else {}
    victim_points = {
        _normalize_planet(houses.get("first_ruler")),
        "Moon",
    }
    victim_points = {point for point in victim_points if point}
    perpetrator_points = {
        _normalize_planet(houses.get("seventh_ruler")),
    }
    perpetrator_points = {point for point in perpetrator_points if point}
    points = _collect_light_points(light_mediation)
    touches_victim = bool(victim_points.intersection(points))
    touches_perpetrator = bool(perpetrator_points.intersection(points))
    if touches_victim and touches_perpetrator:
        role = "victim_perpetrator_bridge"
    elif touches_victim:
        role = "victim_only"
    elif touches_perpetrator:
        role = "perpetrator_only"
    else:
        role = "third_party_only" if points else "unknown"

    if role != "victim_perpetrator_bridge":
        return {
            "kind": kind,
            "role": role,
            "mediator": mediator,
            "score_delta": 0.0,
            "evidence": ["Light mediation lacks victim-perpetrator bridge"],
        }

    if has_prohibition:
        return {
            "kind": kind,
            "role": role,
            "mediator": mediator,
            "score_delta": -1.0,
            "evidence": ["Light prohibition blocks victim/perpetrator perfection"],
        }

    score = 1.25 if kind == "translation" else 0.75
    evidence = [
        "Translation of light bridges victim/perpetrator significators"
        if kind == "translation"
        else "Collection of light gathers victim/perpetrator significators"
    ]

    challenges = light_mediation.get("challenge_reasons") or []
    if light_mediation.get("favorable") is False or challenges:
        score -= 0.5
        evidence.append("light mediation challenged")
    if mediator in MALEFICS:
        score -= 0.25
        evidence.append(f"{mediator} mediator is malefic")
    elif mediator in BENEFICS:
        score += 0.15
        evidence.append(f"{mediator} mediator is benefic")

    for leg in _light_legs(light_mediation):
        aspect = str(leg.get("aspect") or leg.get("type") or "").strip().lower().replace(" ", "_")
        if aspect in SOFT_ASPECTS:
            score += 0.1
        elif aspect in HARD_ASPECTS:
            score -= 0.25

    return {
        "kind": kind,
        "role": role,
        "mediator": mediator,
        "score_delta": round(_clamp(score, 0.0, 1.5), 2),
        "evidence": evidence,
    }


def _finding_blob(finding: Mapping[str, Any]) -> str:
    parts = [
        finding.get("id"),
        finding.get("title"),
        finding.get("category"),
        finding.get("rationale"),
    ]
    return " ".join(_normalize_text(part).lower() for part in parts if part)


def compute_relationship_status(
    features: Mapping[str, Any],
    *,
    findings: Sequence[Mapping[str, Any]] | None = None,
    categories: Mapping[str, Any] | None = None,
    receptions: Mapping[str, Any] | None = None,
    light_mediation: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Summarize forensic relationship status with light mediation as bounded testimony.

    Translation/collection can support a known-person bridge only when it touches
    both victim and perpetrator significators. Prohibition/frustration is treated
    as blocking testimony rather than closeness evidence.
    """

    scores = {
        "intimate_partner": 0.0,
        "family": 0.0,
        "friend_acquaintance": 0.0,
    }
    evidence: Dict[str, List[str]] = {
        "intimate_partner": [],
        "family": [],
        "friend_acquaintance": [],
        "direct_aspect": [],
        "reception": [],
        "light_mediation": [],
        "secondary_factors": [],
    }

    houses = features.get("houses") if isinstance(features, Mapping) else {}
    houses = houses if isinstance(houses, Mapping) else {}
    first_house = houses.get("first_ruler_house")
    seventh_house = houses.get("seventh_ruler_house")
    first_house_num = int(first_house) if str(first_house).isdigit() else None
    seventh_house_num = int(seventh_house) if str(seventh_house).isdigit() else None

    first_seventh_exchange = {first_house_num, seventh_house_num} == {1, 7}
    if first_seventh_exchange:
        _add_score(scores, evidence, "intimate_partner", 1.5, "1st/7th ruler exchange")
    if first_house_num is not None and first_house_num == seventh_house_num:
        _add_score(scores, evidence, "friend_acquaintance", 1.0, "victim/perpetrator rulers share a house")
    if (first_house_num, seventh_house_num) in ((4, 4), (10, 10)):
        _add_score(scores, evidence, "family", 2.5, "both rulers occupy family-axis houses")
    if houses.get("seventh_and_eleventh_same_ruler"):
        _add_score(scores, evidence, "friend_acquaintance", 1.75, "7th and 11th houses share a ruler")
    if seventh_house_num == 11:
        _add_score(scores, evidence, "friend_acquaintance", 1.5, "7th ruler in 11th house")

    direct_aspect_component = direct_aspect_relationship_component(features)
    direct_delta = _to_float(direct_aspect_component.get("score_delta"))
    if direct_delta:
        _add_score(
            scores,
            evidence,
            "friend_acquaintance",
            direct_delta,
            (direct_aspect_component.get("evidence") or ["victim/perpetrator rulers aspect"])[0],
        )
    evidence["direct_aspect"] = list(direct_aspect_component.get("evidence") or [])
    direct_aspect_type = str(direct_aspect_component.get("aspect") or "")
    direct_applying = bool(direct_aspect_component.get("applying"))
    direct_hard_or_conjunction = direct_aspect_type in HARD_ASPECTS or direct_aspect_type == "conjunction"
    if first_seventh_exchange and direct_delta and direct_applying:
        _add_score(
            scores,
            evidence,
            "intimate_partner",
            0.5,
            "applying 1st/7th aspect corroborates partner exchange",
        )

    reception_component = reception_relationship_component(features, receptions)
    reception_delta = _to_float(reception_component.get("score_delta"))
    if reception_delta:
        _add_score(
            scores,
            evidence,
            "friend_acquaintance",
            reception_delta,
            (reception_component.get("evidence") or ["victim/perpetrator reception"])[0],
        )
    evidence["reception"] = list(reception_component.get("evidence") or [])

    finding_blobs = [
        _finding_blob(finding)
        for finding in findings or []
        if isinstance(finding, Mapping)
    ]
    custody_family_context = any(
        "family_custody_child_violence_axis" in blob
        or "family custody" in blob
        for blob in finding_blobs
    )
    for blob in finding_blobs:
        specific_partner_harm = (
            "domestic_partner_confinement_pressure" in blob
            or "domestic_partner_proxy_or_contract_harm" in blob
            or "domestic_partner_route_abduction_pressure" in blob
            or (custody_family_context and "domestic_partner_near_home_axis" in blob)
            or "partner-linked confinement" in blob
            or (custody_family_context and "partner involvement tied to the home axis" in blob)
            or "partner-linked contract" in blob
            or "ex-partner route-abduction" in blob
            or "stalking pattern" in blob
        )
        if specific_partner_harm:
            _add_score(scores, evidence, "intimate_partner", 2.2, "specific partner-harm finding")
        elif "domestic_partner_known_spouse_homicide" in blob or "partner-linked" in blob:
            _add_score(scores, evidence, "intimate_partner", 1.5, "partner-linked finding")
            if first_seventh_exchange or direct_applying:
                _add_score(scores, evidence, "intimate_partner", 0.6, "partner finding has 1st/7th corroboration")
        elif "domestic" in blob and ("partner" in blob or "spouse" in blob or "relationship" in blob):
            _add_score(scores, evidence, "intimate_partner", 1.0, "domestic relationship finding")
            if first_seventh_exchange or (direct_applying and direct_hard_or_conjunction):
                _add_score(scores, evidence, "intimate_partner", 1.0, "domestic finding has 1st/7th corroboration")

        if "family_household_relationship_cluster" in blob or "family or household relationship cluster" in blob:
            _add_score(scores, evidence, "family", 2.5, "family/household cluster finding")
        elif "family" in blob and ("household" in blob or "custody" in blob):
            _add_score(scores, evidence, "family", 1.0, "family-context finding")

        if (
            "friend_or_associate_axis_active" in blob
            or "known_person_route_harm_moon_dispositor_bridge" in blob
            or "friend or close associate" in blob
            or "known-person" in blob
        ):
            _add_score(scores, evidence, "friend_acquaintance", 1.75, "known-person/associate finding")

    light_component = light_mediation_relationship_component(features, light_mediation)
    evidence["light_mediation"] = list(light_component.get("evidence") or [])
    light_delta = _to_float(light_component.get("score_delta"))
    if light_delta > 0:
        _add_score(
            scores,
            evidence,
            "friend_acquaintance",
            light_delta,
            evidence["light_mediation"][0] if evidence["light_mediation"] else "light mediation bridge",
        )
    elif light_delta < 0:
        for label in ("friend_acquaintance", "intimate_partner"):
            scores[label] = round(max(0.0, scores[label] + light_delta), 2)

    secondary_analysis = features.get("secondary_factor_analysis") if isinstance(features, Mapping) else {}
    secondary_delta = {}
    if isinstance(secondary_analysis, Mapping) and secondary_analysis.get("enabled"):
        raw_delta = secondary_analysis.get("relationship_score_delta") or {}
        if isinstance(raw_delta, Mapping):
            secondary_delta = dict(raw_delta)
        evidence["secondary_factors"] = [
            str(item)
            for item in secondary_analysis.get("evidence") or []
            if str(item).strip()
        ][:8]
    for label in ("intimate_partner", "family", "friend_acquaintance"):
        delta = _to_float(secondary_delta.get(label)) if isinstance(secondary_delta, Mapping) else 0.0
        if delta:
            _add_score(
                scores,
                evidence,
                label,
                delta,
                evidence["secondary_factors"][0] if evidence["secondary_factors"] else "secondary asteroid/degree testimony",
            )

    labels: List[str] = []
    if scores["intimate_partner"] >= 2.0:
        labels.append("intimate_partner")
    if scores["family"] >= 2.5 and scores["friend_acquaintance"] < 3.0:
        labels.append("family")
    friend_threshold_met = (
        scores["friend_acquaintance"] >= 4.5
        or (
            scores["friend_acquaintance"] >= 2.75
            and light_delta > 0
            and light_component.get("role") == "victim_perpetrator_bridge"
        )
    )
    if friend_threshold_met:
        labels.append("friend_acquaintance")
    if not labels:
        labels = ["stranger_public"]

    priority = ("intimate_partner", "family", "friend_acquaintance", "stranger_public")
    primary_label = next((label for label in priority if label in labels), "stranger_public")
    strongest_score = max(scores.values()) if scores else 0.0
    if primary_label == "stranger_public":
        confidence = "Moderate" if strongest_score < 1.0 else "Low"
    elif strongest_score >= 4.0:
        confidence = "High"
    elif strongest_score >= 2.5:
        confidence = "Moderate"
    else:
        confidence = "Low"

    return {
        "primary_label": primary_label,
        "labels": labels,
        "scores": {label: round(value, 2) for label, value in scores.items()},
        "confidence": confidence,
        "confidence_basis": "symbolic_rule_strength_not_empirical_probability",
        "is_statistical_probability": False,
        "evidence": evidence,
        "direct_aspect_component": direct_aspect_component,
        "reception_component": reception_component,
        "light_mediation_component": light_component,
        "secondary_factor_component": {
            "enabled": bool(isinstance(secondary_analysis, Mapping) and secondary_analysis.get("enabled")),
            "score_delta": {label: round(_to_float(secondary_delta.get(label)), 2) for label in ("intimate_partner", "family", "friend_acquaintance") if isinstance(secondary_delta, Mapping) and _to_float(secondary_delta.get(label))},
            "evidence": evidence["secondary_factors"],
        },
    }
