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


def _derive_victim_significators(features: Dict[str, Any], case_type: str) -> List[str]:
    houses = (features.get("houses") or {}) if isinstance(features, dict) else {}
    primary = houses.get("first_ruler") or SIGN_RULERS.get((houses.get("signs") or {}).get("1"))
    out: List[str] = []
    for item in [primary, "Moon"]:
        if item and item not in out:
            out.append(item)
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
        else:
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
    titles = [str((finding or {}).get("title") or "").strip().lower() for finding in findings or []]
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

    violence_count = int((categories or {}).get("Violence", 0) or 0)
    if violence_count:
        pts = min(2.5, violence_count * 0.8)
        score += pts
        evidence.append(f"violence findings +{pts:g}")

    disaster_count = int((categories or {}).get("Disaster", 0) or 0)
    if disaster_count:
        pts = min(1.5, disaster_count * 0.6)
        score += pts
        evidence.append(f"disaster findings +{pts:g}")

    if any("life/death overlap" in title for title in titles):
        score += 2.2
        evidence.append("life/death overlap +2.2")
    if any("violence or homicide" in title for title in titles):
        score += 1.8
        evidence.append("homicide testimony +1.8")
    elif any("homicide" in title for title in titles):
        score += 1.6
        evidence.append("explicit homicide testimony +1.6")
    title_rules = (
        ("known-person violence pattern", 1.6, "known-person violence"),
        ("malefic contrary to sect", 1.25, "malefic contrary to sect"),
        ("hidden victim with angular violence markers", 1.5, "hidden victim under violence"),
        ("moon under death pressure", 1.2, "Moon under death pressure"),
        ("violent fixed star", 1.0, "violent fixed star"),
        ("catastrophic", 1.5, "catastrophic testimony"),
        ("drowning", 1.5, "drowning testimony"),
    )
    for needle, pts, label in title_rules:
        if any(needle in title for title in titles):
            score += pts
            evidence.append(f"{label} +{pts:g}")

    return score, evidence


def compute_survivability(
    features: Dict[str, Any],
    findings: List[Dict[str, Any]] | None = None,
    categories: Dict[str, int] | None = None,
    *,
    case_type: str = "general",
) -> Dict[str, Any]:
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

    abduction_count = int((categories or {}).get("Abduction", 0) or 0)
    violence_count = int((categories or {}).get("Violence", 0) or 0)
    abduction_context = abduction_count > 0
    violent_context = violence_count > 0

    danger_weight = 0.55 if abduction_context else 0.85
    adjusted_fatal_pressure = fatal_pressure
    if abduction_context and fatal_pressure:
        adjusted_fatal_pressure = round(
            fatal_pressure * (0.45 if violence_count <= 2 else 0.6),
            2,
        )
        fatal_evidence = list(fatal_evidence) + [
            f"abduction context scales fatal pressure to {adjusted_fatal_pressure:g}"
        ]

    net_score = round(
        vitality_score + accidental_score + support_score + recovery_support_score + lunar_score - (danger_score * danger_weight) - adjusted_fatal_pressure,
        2,
    )

    if abduction_context:
        if adjusted_fatal_pressure >= 6.0 and net_score <= -1.5:
            level = "Lower"
        elif net_score >= 2.75 and adjusted_fatal_pressure < 1.5 and danger_score < 2.0:
            level = "Higher"
        else:
            level = "Moderate"
    else:
        rescue_override = (
            recovery_support_score >= 1.0
            and support_score >= 4.5
            and support_score >= danger_score
            and adjusted_fatal_pressure < 7.0
        )
        if adjusted_fatal_pressure >= 4.5 and net_score <= 1.5 and not rescue_override:
            level = "Lower"
        elif violent_context and (danger_score >= 3.0 or adjusted_fatal_pressure >= 1.5) and net_score <= 0.5 and not rescue_override:
            level = "Lower"
        elif net_score >= 3.0 and adjusted_fatal_pressure < 3.0:
            level = "Higher"
        elif net_score <= -4.0:
            level = "Lower"
        else:
            level = "Moderate"

    if abduction_context:
        if level == "Lower":
            outcome_band = "fatal_pressure_dominant"
        elif net_score >= 2.0 and adjusted_fatal_pressure < 1.5 and danger_score < 2.0:
            outcome_band = "release_favored"
        else:
            outcome_band = "risk_loaded_survival"
    else:
        if level == "Lower":
            outcome_band = "fatal_pressure_dominant"
        elif net_score >= 2.0 and adjusted_fatal_pressure < 1.5:
            outcome_band = "nonfatal_tilt"
        else:
            outcome_band = "mixed_nonfatal"

    note = (
        "Derived from significator vitality, accidental power, benefic support, Moon testimony, malefic pressure, and explicit death-edge findings."
    )
    if level == "Lower" and adjusted_fatal_pressure >= 4.5:
        note = "Explicit death-edge testimony outweighs base vitality and support."

    return {
        "level": level,
        "score": net_score,
        "outcome_band": outcome_band,
        "case_type": normalized_case_type,
        "victim_significators": victim_significators,
        "breakdown": {
            "vitality": round(vitality_score, 2),
            "accidental": round(accidental_score, 2),
            "support": round(support_score, 2),
            "recovery_support": round(recovery_support_score, 2),
            "moon": round(lunar_score, 2),
            "danger": round(danger_score, 2),
            "fatal_pressure": round(adjusted_fatal_pressure, 2),
        },
        "evidence": {
            "vitality": vitality_evidence,
            "accidental": accidental_evidence,
            "support": support_evidence,
            "recovery_support": recovery_support_evidence,
            "moon": lunar_evidence,
            "danger": danger_evidence,
            "fatal_pressure": fatal_evidence,
        },
        "note": note,
    }
