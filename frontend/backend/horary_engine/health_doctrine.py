from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..models import Aspect, Planet, Sign
except ImportError:  # pragma: no cover - fallback for script execution
    from models import Aspect, Planet, Sign


FIXED_SIGNS = {Sign.TAURUS, Sign.LEO, Sign.SCORPIO, Sign.AQUARIUS}
EASY_ASPECTS = {Aspect.CONJUNCTION, Aspect.SEXTILE, Aspect.TRINE}


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


def analyze_health_question_text(
    question: str,
    question_type: Any | None = None,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    q = (question or "").lower().strip()

    medical_context_tokens = (
        "covid",
        "doctor",
        "clinic",
        "hospital",
        "medical",
        "lab",
        "laboratory",
        "blood",
        "biopsy",
        "scan",
        "mri",
        "ct",
        "x-ray",
        "xray",
        "ultrasound",
        "thyroid",
        "test result",
    )
    result_contact_tokens = (
        "test result",
        "result",
        "results",
        "report",
        "letter",
        "email",
        "message",
        "call",
        "hear back",
        "come back",
        "arrive",
    )

    diagnosis_tokens = (
        "is it",
        "what's the problem",
        "what is the problem",
        "where's the",
        "where is the",
        "diagnosis",
        "diagnosed",
        "multiple sclerosis",
        "ms",
        "inflammation",
        "stomach",
        "symptom",
        "symptoms",
        "tumor",
    )
    progression_tokens = (
        "stop growing",
        "get better",
        "recover",
        "recovery",
        "improve",
        "worse",
        "worsen",
        "survive",
        "survival",
        "stabilize",
        "stabilise",
        "slow rate",
        "slow rhythm",
        "overworking",
    )
    treatment_tokens = (
        "medicine",
        "medication",
        "treatment",
        "therapy",
        "prescription",
        "dose",
        "doctor",
        "tablet",
        "pill",
        "helping or harming",
        "helping me",
        "harming me",
        "side effect",
        "side effects",
    )

    has_medical_result_context = any(token in q for token in medical_context_tokens) and any(
        token in q for token in result_contact_tokens
    )

    family = "general"
    doctrine = "Default health analysis."
    if has_medical_result_context:
        family = "result_contact"
        doctrine = "Medical result questions judge the arrival of the doctor, lab, or report as the operative contact, not the disease itself and not an education-style exam chart."
    elif any(token in q for token in treatment_tokens):
        family = "treatment"
        doctrine = "Treatment questions judge whether the medicine or intervention helps or harms, using doctor and treatment houses rather than only the disease house."
    elif re.search(r"^\s*(is|am|are|has|have)\b", q) and any(token in q for token in diagnosis_tokens):
        family = "diagnosis"
        doctrine = "Present-state health questions judge whether the named illness or condition is actually present now."
    elif any(token in q for token in progression_tokens):
        family = "progression"
        doctrine = "Health progression questions judge whether the condition worsens, stabilizes, or recovers."
    elif any(token in q for token in diagnosis_tokens):
        family = "diagnosis"
        doctrine = "Medical diagnosis questions are judged as present-state condition charts."

    if third_person_analysis and third_person_analysis.get("is_third_person"):
        subject_house = int(third_person_analysis.get("subject_house") or 7)
        illness_house = _turn(subject_house, 6)
        if family == "result_contact":
            doctor_house = _turn(subject_house, 7)
            relevant_houses = [subject_house, doctor_house]
        elif family == "treatment":
            doctor_house = _turn(subject_house, 7)
            treatment_house = _turn(subject_house, 10)
            relevant_houses = [subject_house, illness_house, doctor_house, treatment_house]
        else:
            relevant_houses = [subject_house, illness_house]
    else:
        subject_house = 1
        illness_house = 6
        if family == "result_contact":
            doctor_house = 7
            relevant_houses = [1, 7]
        elif family == "treatment":
            doctor_house = 7
            treatment_house = 10
            relevant_houses = [1, 6, 7, 10]
        else:
            relevant_houses = [1, 6]

    result = {
        "family": family,
        "doctrine": doctrine,
        "subject_house": subject_house,
        "illness_house": illness_house,
        "quesited_house": doctor_house if family == "result_contact" else illness_house if family != "treatment" else treatment_house,
        "relevant_houses": relevant_houses,
    }

    if family == "result_contact":
        result["doctor_house"] = doctor_house
    if family == "treatment":
        result["doctor_house"] = doctor_house
        result["treatment_house"] = treatment_house

    return result


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


def build_health_diagnosis_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    health_analysis: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = health_analysis or {}
    if analysis.get("family") != "diagnosis":
        return None

    subject = chart.planets.get(querent_planet)
    illness = chart.planets.get(quesited_planet)
    if not (subject and illness):
        return None

    aspect = _find_major_aspect_between(chart, querent_planet, quesited_planet)
    moon_next = getattr(chart, "moon_next_aspect", None)
    return {
        "family": "diagnosis",
        "subject_name": querent_planet.value,
        "subject_house": analysis.get("subject_house", getattr(subject, "house", None)),
        "subject_sign": getattr(subject, "sign", None),
        "illness_name": quesited_planet.value,
        "illness_house": getattr(illness, "house", None),
        "illness_sign": getattr(illness, "sign", None),
        "illness_dignity": int(getattr(illness, "dignity_score", 0) or 0),
        "aspect_name": getattr(getattr(aspect, "aspect", None), "display_name", None),
        "aspect_applying": bool(getattr(aspect, "applying", False)) if aspect else None,
        "moon_next_planet": getattr(moon_next, "planet", None),
        "moon_next_aspect": getattr(moon_next, "aspect", None),
        "moon_next_applying": bool(getattr(moon_next, "applying", False)) if moon_next else False,
    }


def evaluate_health_diagnosis_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Health Doctrine",
            "rule": "Health family: present-state diagnosis (judge whether the named illness is present now, not whether it might develop later)",
            "weight": 0,
        }
    ]
    score = 0

    if snapshot.get("aspect_name"):
        if snapshot.get("aspect_applying"):
            score -= 4
            reasoning.append(
                {
                    "stage": "Health Doctrine",
                    "rule": f"Applying {snapshot['aspect_name']} between {snapshot['subject_name']} and {snapshot['illness_name']} shows the condition forming or clarifying later, not already confirmed now",
                    "weight": -4,
                }
            )
        else:
            score += 4
            reasoning.append(
                {
                    "stage": "Health Doctrine",
                    "rule": f"Separating {snapshot['aspect_name']} between {snapshot['subject_name']} and {snapshot['illness_name']} supports an already-established condition",
                    "weight": 4,
                }
            )

    if snapshot.get("illness_house") == snapshot.get("subject_house"):
        score += 4
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": "Illness significator is placed in the subject's house, showing the condition in the body already",
                "weight": 4,
            }
        )

    if snapshot.get("illness_sign") in FIXED_SIGNS:
        score += 1
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": "Illness significator is in a fixed sign, adding persistence testimony",
                "weight": 1,
            }
        )

    if snapshot.get("illness_dignity", 0) >= 4:
        score += 1
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": f"Illness significator {snapshot['illness_name']} is strongly placed, so the named disease is more visible if truly present",
                "weight": 1,
            }
        )
    elif snapshot.get("illness_dignity", 0) <= -4:
        score -= 1
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": f"Illness significator {snapshot['illness_name']} is weak, which does not strongly support the named diagnosis",
                "weight": -1,
            }
        )

    if (
        snapshot.get("moon_next_applying")
        and snapshot.get("moon_next_planet") == Planet[snapshot["illness_name"].upper()]
        and snapshot.get("moon_next_aspect") in EASY_ASPECTS
    ):
        score += 1
        aspect_name = getattr(snapshot["moon_next_aspect"], "display_name", "Applying aspect")
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": f"Moon next applies by {aspect_name} to the illness significator, adding a minor confirmation testimony",
                "weight": 1,
            }
        )

    if score >= 4:
        result = "YES"
        confidence = 78
    else:
        result = "NO"
        confidence = 82 if score <= 0 else 68

    return {
        "applies": True,
        "result": result,
        "confidence": confidence,
        "score": score,
        "reasoning": reasoning,
    }


def build_health_progression_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    health_analysis: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = health_analysis or {}
    if analysis.get("family") != "progression":
        return None

    subject = chart.planets.get(querent_planet)
    illness = chart.planets.get(quesited_planet)
    moon_next = getattr(chart, "moon_next_aspect", None)
    if not (subject and illness):
        return None

    return {
        "family": "progression",
        "subject_name": querent_planet.value,
        "subject_house": analysis.get("subject_house", getattr(subject, "house", None)),
        "subject_sign": getattr(subject, "sign", None),
        "subject_dignity": int(getattr(subject, "dignity_score", 0) or 0),
        "illness_name": quesited_planet.value,
        "illness_house": getattr(illness, "house", None),
        "illness_sign": getattr(illness, "sign", None),
        "illness_dignity": int(getattr(illness, "dignity_score", 0) or 0),
        "illness_retrograde": bool(getattr(illness, "retrograde", False)),
        "same_ruler": querent_planet == quesited_planet,
        "moon_next_planet": getattr(moon_next, "planet", None),
        "moon_next_aspect": getattr(moon_next, "aspect", None),
        "moon_next_applying": bool(getattr(moon_next, "applying", False)) if moon_next else False,
    }


def evaluate_health_progression_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Health Doctrine",
            "rule": "Health family: progression/stabilization (judge whether the condition worsens or stabilizes, not only whether a new event perfects)",
            "weight": 0,
        }
    ]
    score = 0

    if snapshot.get("same_ruler"):
        score += 2
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": "The subject and illness share one ruler, tying the condition to the current state rather than showing a fresh escalation",
                "weight": 2,
            }
        )

    if snapshot.get("illness_sign") in FIXED_SIGNS:
        score += 3
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": "Illness significator is in a fixed sign, favoring stasis or slow development rather than rapid worsening",
                "weight": 3,
            }
        )

    if snapshot.get("subject_sign") in FIXED_SIGNS:
        score += 1
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": "Subject significator is in a fixed sign, supporting persistence and stability",
                "weight": 1,
            }
        )

    if snapshot.get("subject_dignity", 0) >= 3:
        score += 1
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": f"Subject significator {snapshot['subject_name']} is in workable condition",
                "weight": 1,
            }
        )

    if snapshot.get("illness_retrograde"):
        score += 2
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": f"Illness significator {snapshot['illness_name']} is retrograde, showing withdrawal or reduction",
                "weight": 2,
            }
        )

    next_planet = snapshot.get("moon_next_planet")
    if (
        snapshot.get("moon_next_applying")
        and snapshot.get("moon_next_aspect") in EASY_ASPECTS
        and next_planet in {Planet.JUPITER, Planet.VENUS, Planet[snapshot["subject_name"].upper()], Planet[snapshot["illness_name"].upper()]}
    ):
        aspect_name = getattr(snapshot["moon_next_aspect"], "display_name", "Applying aspect")
        score += 2
        target = next_planet.value if hasattr(next_planet, "value") else str(next_planet)
        reasoning.append(
            {
                "stage": "Health Doctrine",
                "rule": f"Moon next applies by {aspect_name} to {target}, adding supportive development testimony",
                "weight": 2,
            }
        )

    if score >= 5:
        result = "YES"
        confidence = 78
    else:
        result = "NO"
        confidence = 72 if score <= 0 else 64

    return {
        "applies": True,
        "result": result,
        "confidence": confidence,
        "score": score,
        "reasoning": reasoning,
    }
