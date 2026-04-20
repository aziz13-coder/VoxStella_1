from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..models import Aspect, Planet, Sign
except ImportError:  # pragma: no cover - fallback for script execution
    from models import Aspect, Planet, Sign


FERTILE_SIGNS = {Sign.CANCER, Sign.SCORPIO, Sign.PISCES}


def analyze_pregnancy_question_text(question: str) -> Dict[str, Any]:
    q = (question or "").lower().strip()

    if re.search(r"^\s*(am|is|are)\b.*\bpregnant\b", q):
        return {
            "family": "diagnosis",
            "doctrine": "Present-state pregnancy questions judge whether pregnancy already exists, not whether it will occur later.",
        }

    if any(token in q for token in ("conceive", "conception", "fertility", "will i conceive", "get pregnant")):
        return {
            "family": "conception",
            "doctrine": "Future conception questions may be judged by strong Moon-to-child testimony even without direct L1/L5 perfection.",
        }

    return {
        "family": "conception",
        "doctrine": "Default pregnancy analysis follows conception/event logic.",
    }


def _find_major_aspect_between(chart: Any, planet1: Planet, planet2: Planet):
    major = {
        Aspect.CONJUNCTION,
        Aspect.SEXTILE,
        Aspect.SQUARE,
        Aspect.TRINE,
        Aspect.OPPOSITION,
    }
    matches = [
        asp
        for asp in getattr(chart, "aspects", [])
        if {asp.planet1, asp.planet2} == {planet1, planet2} and asp.aspect in major
    ]
    if not matches:
        return None
    return min(matches, key=lambda asp: getattr(asp, "degrees_to_exact", 9999))


def build_pregnancy_diagnosis_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    pregnancy_analysis: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = pregnancy_analysis or {}
    if analysis.get("family") != "diagnosis":
        return None

    querent = chart.planets.get(querent_planet)
    quesited = chart.planets.get(quesited_planet)
    if not (querent and quesited):
        return None

    aspect = _find_major_aspect_between(chart, querent_planet, quesited_planet)
    return {
        "family": "diagnosis",
        "querent_name": querent_planet.value,
        "quesited_name": quesited_planet.value,
        "quesited_house": getattr(quesited, "house", None),
        "quesited_sign": getattr(quesited, "sign", None),
        "quesited_dignity": int(getattr(quesited, "dignity_score", 0) or 0),
        "quesited_speed": float(getattr(quesited, "speed", 0.0) or 0.0),
        "aspect_name": getattr(getattr(aspect, "aspect", None), "display_name", None),
        "aspect_applying": bool(getattr(aspect, "applying", False)) if aspect else None,
        "aspect_distance": getattr(aspect, "degrees_to_exact", None),
    }


def evaluate_pregnancy_diagnosis_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Pregnancy Doctrine",
            "rule": "Pregnancy family: present-state diagnosis (judge current condition, not future perfection)",
            "weight": 0,
        }
    ]

    score = 0

    if snapshot.get("aspect_name"):
        if snapshot.get("aspect_applying"):
            score -= 6
            reasoning.append(
                {
                    "stage": "Pregnancy Doctrine",
                    "rule": (
                        f"Applying {snapshot['aspect_name']} between {snapshot['querent_name']} and "
                        f"{snapshot['quesited_name']} shows connection forming later, not pregnancy already present"
                    ),
                    "weight": -6,
                }
            )
        else:
            score += 6
            reasoning.append(
                {
                    "stage": "Pregnancy Doctrine",
                    "rule": (
                        f"Separating {snapshot['aspect_name']} between {snapshot['querent_name']} and "
                        f"{snapshot['quesited_name']} shows an already-existing bond"
                    ),
                    "weight": 6,
                }
            )

    if snapshot.get("quesited_house") == 1:
        score += 3
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": f"{snapshot['quesited_name']} placed in the 1st house shows the child in the mother's body",
                "weight": 3,
            }
        )

    if snapshot.get("quesited_sign") in FERTILE_SIGNS:
        score += 1
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": f"{snapshot['quesited_name']} in a fertile sign adds supportive testimony",
                "weight": 1,
            }
        )

    if abs(snapshot.get("quesited_speed", 0.0)) < 0.03:
        score -= 1
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": f"{snapshot['quesited_name']} is nearly stationary, weakening living/current testimony",
                "weight": -1,
            }
        )

    if score >= 4:
        result = "YES"
        confidence = 80
    else:
        result = "NO"
        confidence = 82 if score <= -2 else 68

    return {
        "applies": True,
        "result": result,
        "confidence": confidence,
        "score": score,
        "reasoning": reasoning,
    }


def build_pregnancy_conception_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    pregnancy_analysis: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = pregnancy_analysis or {}
    if analysis.get("family") != "conception":
        return None

    querent = chart.planets.get(querent_planet)
    quesited = chart.planets.get(quesited_planet)
    moon = chart.planets.get(Planet.MOON)
    moon_next = getattr(chart, "moon_next_aspect", None)
    if not (querent and quesited and moon):
        return None

    return {
        "family": "conception",
        "querent_name": querent_planet.value,
        "quesited_name": quesited_planet.value,
        "querent_house": getattr(querent, "house", None),
        "quesited_house": getattr(quesited, "house", None),
        "querent_dignity": int(getattr(querent, "dignity_score", 0) or 0),
        "quesited_dignity": int(getattr(quesited, "dignity_score", 0) or 0),
        "quesited_retrograde": bool(getattr(quesited, "retrograde", False)),
        "moon_sign": getattr(moon, "sign", None),
        "moon_dignity": int(getattr(moon, "dignity_score", 0) or 0),
        "quesited_sign": getattr(quesited, "sign", None),
        "moon_next_planet": getattr(moon_next, "planet", None),
        "moon_next_aspect": getattr(moon_next, "aspect", None),
        "moon_next_applying": bool(getattr(moon_next, "applying", False)) if moon_next else False,
    }


def evaluate_pregnancy_conception_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Pregnancy Doctrine",
            "rule": "Pregnancy family: conception (strong Moon-to-child testimony can perfect the matter without direct L1/L5 contact)",
            "weight": 0,
        }
    ]

    score = 0
    next_planet = snapshot.get("moon_next_planet")
    next_aspect = snapshot.get("moon_next_aspect")
    if (
        snapshot.get("moon_next_applying")
        and next_planet == Planet[snapshot["quesited_name"].upper()]
        and next_aspect in {Aspect.CONJUNCTION, Aspect.SEXTILE, Aspect.TRINE}
    ):
        aspect_name = getattr(next_aspect, "display_name", "Applying aspect")
        bonus = 7 if next_aspect == Aspect.CONJUNCTION else 5
        score += bonus
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": f"Moon next applies by {aspect_name} to child significator {snapshot['quesited_name']}",
                "weight": bonus,
            }
        )

    if snapshot.get("moon_sign") in FERTILE_SIGNS:
        score += 2
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": "Moon is in a fertile sign",
                "weight": 2,
            }
        )

    if snapshot.get("quesited_sign") in FERTILE_SIGNS:
        score += 2
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": f"Child significator {snapshot['quesited_name']} is in a fertile sign",
                "weight": 2,
            }
        )

    if snapshot.get("moon_dignity", 0) >= 3:
        score += 1
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": "Moon is well dignified",
                "weight": 1,
            }
        )

    if snapshot.get("quesited_dignity", 0) >= 1:
        score += 1
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": f"Child significator {snapshot['quesited_name']} is not debilitated",
                "weight": 1,
            }
        )

    if snapshot.get("quesited_retrograde"):
        score -= 1
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": f"Child significator {snapshot['quesited_name']} is retrograde",
                "weight": -1,
            }
        )

    if snapshot.get("querent_house") in {6, 8, 12}:
        score -= 1
        reasoning.append(
            {
                "stage": "Pregnancy Doctrine",
                "rule": f"Querent significator {snapshot['querent_name']} is cadent, showing worry or weakness",
                "weight": -1,
            }
        )

    if score >= 7:
        return {
            "applies": True,
            "result": "YES",
            "confidence": min(88, 68 + score * 2),
            "score": score,
            "reasoning": reasoning,
        }

    return {"applies": False, "reasoning": reasoning, "result": None, "score": score}
