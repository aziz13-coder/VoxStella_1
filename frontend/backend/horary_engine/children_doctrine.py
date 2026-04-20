from __future__ import annotations

from typing import Any, Dict

try:
    from ..models import Sign
except ImportError:  # pragma: no cover - fallback for script execution
    from models import Sign


FIXED_SIGNS = {Sign.TAURUS, Sign.LEO, Sign.SCORPIO, Sign.AQUARIUS}


def analyze_children_question_text(question: str) -> Dict[str, Any]:
    q = (question or "").lower().strip()

    if "adoption" in q or "adopt" in q:
        return {
            "family": "adoption",
            "doctrine": "Someone-else's-child adoption questions are judged from the child and the current caretakers, not by pregnancy rules.",
        }

    return {
        "family": "general",
        "doctrine": "Default children analysis.",
    }


def build_children_adoption_snapshot(
    chart: Any,
    quesited_planet: Any,
    question_analysis: Dict[str, Any] | None,
    children_analysis: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = children_analysis or {}
    if analysis.get("family") != "adoption":
        return None

    significators = (question_analysis or {}).get("significators") or {}
    subject_house = significators.get("subject_house")
    child_house = significators.get("child_house", significators.get("quesited_house"))
    quesited = chart.planets.get(quesited_planet)
    if subject_house is None or child_house is None or not quesited:
        return None

    return {
        "family": "adoption",
        "subject_house": subject_house,
        "child_house": child_house,
        "child_planet_name": quesited_planet.value,
        "child_planet_house": getattr(quesited, "house", None),
        "child_sign": getattr(quesited, "sign", None),
        "child_dignity": int(getattr(quesited, "dignity_score", 0) or 0),
    }


def evaluate_children_adoption_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Children Doctrine",
            "rule": "Children family: adoption/custody (judge the child in relation to the current caretakers)",
            "weight": 0,
        }
    ]

    score = 0

    if snapshot.get("child_planet_house") == snapshot.get("subject_house"):
        score -= 6
        reasoning.append(
            {
                "stage": "Children Doctrine",
                "rule": "The child's significator is placed in the parents' house, showing the child remains with them",
                "weight": -6,
            }
        )

    if snapshot.get("child_sign") in FIXED_SIGNS:
        score -= 2
        reasoning.append(
            {
                "stage": "Children Doctrine",
                "rule": "The child is in a fixed sign, resisting transfer or change of custody",
                "weight": -2,
            }
        )

    if snapshot.get("child_dignity", 0) >= 4:
        score -= 2
        reasoning.append(
            {
                "stage": "Children Doctrine",
                "rule": f"Child significator {snapshot['child_planet_name']} is strong, favoring stability with the current caretakers",
                "weight": -2,
            }
        )

    if snapshot.get("child_planet_house") not in {snapshot.get("subject_house"), snapshot.get("child_house")}:
        score += 2
        reasoning.append(
            {
                "stage": "Children Doctrine",
                "rule": "The child's significator is separated from the current caretakers' house",
                "weight": 2,
            }
        )

    if score <= -4:
        result = "NO"
        confidence = 84
    elif score >= 4:
        result = "YES"
        confidence = 76
    else:
        result = "NO"
        confidence = 66

    return {
        "applies": True,
        "result": result,
        "confidence": confidence,
        "score": score,
        "reasoning": reasoning,
    }
