from __future__ import annotations

from typing import Any, Dict

try:
    from ..models import Aspect, Planet, Sign
except ImportError:  # pragma: no cover - fallback for script execution
    from models import Aspect, Planet, Sign


FIXED_SIGNS = {Sign.TAURUS, Sign.LEO, Sign.SCORPIO, Sign.AQUARIUS}


def analyze_relationship_question_text(question: str) -> Dict[str, Any]:
    """Classify relationship questions into doctrinal sub-families.

    ``affection`` questions ask about reciprocal liking, attraction, or
    feelings. Traditional perfection alone is too coarse for those charts,
    because the judgment depends on whether the significators receive one
    another.

    ``outcome`` questions ask whether a relationship event will occur:
    marriage, reunion, reconciliation, divorce, and similar external outcomes.
    """

    q = (question or "").lower().strip()

    affection_words = (
        "like one another",
        "like each other",
        "like me",
        "like him",
        "like her",
        "feelings",
        "romantic interest",
        "romantically",
        "attracted",
        "attraction",
        "interested in",
        "crush",
        "love me",
        "love him",
        "love her",
        "love us",
        "spark",
        "chemistry",
    )
    outcome_words = (
        "marry",
        "marriage",
        "reconcile",
        "rekindle",
        "get back together",
        "come back",
        "be together",
        "relationship",
        "divorce",
        "separation",
        "separate",
        "break up",
        "breakup",
    )

    durability_words = (
        "relationship last",
        "last?",
        "last ",
        "lasting",
        "endure",
        "stand the test",
        "continue",
        "stable",
    )

    if any(token in q for token in durability_words):
        return {
            "family": "durability",
            "requires_mutuality": False,
            "doctrine": "Relationship durability is judged by the condition of the bond and the partners, not only by first perfection.",
        }

    if any(token in q for token in affection_words):
        return {
            "family": "affection",
            "requires_mutuality": True,
            "doctrine": "Reciprocal liking requires mutual reception, not merely contact.",
        }

    if any(token in q for token in outcome_words):
        return {
            "family": "outcome",
            "requires_mutuality": False,
            "doctrine": "Event-style relationship question judged by occurrence/perfection.",
        }

    return {
        "family": "outcome",
        "requires_mutuality": False,
        "doctrine": "Default relationship outcome analysis.",
    }


def _solar_name(value: str | None) -> str:
    return value or "Free of Sun"


def build_relationship_affection_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    relationship_analysis: Dict[str, Any] | None,
    perfection: Dict[str, Any] | None,
    reception_info: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    """Build a pure snapshot for reciprocal-affection judgments."""

    analysis = relationship_analysis or {}
    if analysis.get("family") != "affection":
        return None

    q_pos = chart.planets.get(querent_planet)
    qq_pos = chart.planets.get(quesited_planet)
    if not (q_pos and qq_pos):
        return None

    rec = reception_info or {}
    return {
        "family": analysis.get("family"),
        "requires_mutuality": bool(analysis.get("requires_mutuality", True)),
        "querent_name": querent_planet.value,
        "querent_dignity": int(getattr(q_pos, "dignity_score", 0) or 0),
        "querent_house": getattr(q_pos, "house", None),
        "querent_retrograde": bool(getattr(q_pos, "retrograde", False)),
        "querent_solar_condition": _solar_name(
            getattr(getattr(q_pos, "solar_condition", None), "condition", None)
        ),
        "quesited_name": quesited_planet.value,
        "quesited_dignity": int(getattr(qq_pos, "dignity_score", 0) or 0),
        "quesited_house": getattr(qq_pos, "house", None),
        "quesited_retrograde": bool(getattr(qq_pos, "retrograde", False)),
        "quesited_solar_condition": _solar_name(
            getattr(getattr(qq_pos, "solar_condition", None), "condition", None)
        ),
        "perfection_type": (perfection or {}).get("type"),
        "perfects": bool((perfection or {}).get("perfects")),
        "aspect_name": getattr((perfection or {}).get("aspect"), "display_name", None),
        "mutual": rec.get("mutual", "none"),
        "one_way": list(rec.get("one_way", []) or []),
        "display_text": rec.get("display_text", "no reception"),
    }


def build_relationship_durability_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    relationship_analysis: Dict[str, Any] | None,
    reception_info: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = relationship_analysis or {}
    if analysis.get("family") != "durability":
        return None

    q_pos = chart.planets.get(querent_planet)
    qq_pos = chart.planets.get(quesited_planet)
    moon_pos = chart.planets.get(Planet.MOON)
    if not (q_pos and qq_pos and moon_pos):
        return None

    moon_next = getattr(chart, "moon_next_aspect", None)
    rec = reception_info or {}
    return {
        "family": "durability",
        "querent_name": querent_planet.value,
        "querent_dignity": int(getattr(q_pos, "dignity_score", 0) or 0),
        "quesited_name": quesited_planet.value,
        "quesited_dignity": int(getattr(qq_pos, "dignity_score", 0) or 0),
        "quesited_house": getattr(qq_pos, "house", None),
        "quesited_retrograde": bool(getattr(qq_pos, "retrograde", False)),
        "moon_dignity": int(getattr(moon_pos, "dignity_score", 0) or 0),
        "moon_sign": getattr(moon_pos, "sign", None),
        "moon_next_planet": getattr(moon_next, "planet", None),
        "moon_next_aspect": getattr(moon_next, "aspect", None),
        "mutual": rec.get("mutual", "none"),
        "one_way": list(rec.get("one_way", []) or []),
        "display_text": rec.get("display_text", "no reception"),
    }


def evaluate_relationship_durability_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Relationship Doctrine",
            "rule": "Relationship family: durability/continuance (judge the condition of the bond, not only first perfection)",
            "weight": 0,
        }
    ]

    score = 0

    quesited_dignity = snapshot.get("quesited_dignity", 0)
    if quesited_dignity >= 5:
        score += 4
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Quesited significator {snapshot['quesited_name']} is very strong",
                "weight": 4,
            }
        )
    elif quesited_dignity >= 1:
        score += 2
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Quesited significator {snapshot['quesited_name']} is in workable condition",
                "weight": 2,
            }
        )
    elif quesited_dignity <= -3:
        score -= 3
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Quesited significator {snapshot['quesited_name']} is debilitated",
                "weight": -3,
            }
        )

    moon_dignity = snapshot.get("moon_dignity", 0)
    if moon_dignity >= 3:
        score += 3
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": "Moon is strong, supporting the continuance of the bond",
                "weight": 3,
            }
        )
    elif moon_dignity <= -2:
        score -= 3
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": "Moon is weak or troubled, destabilizing the relationship",
                "weight": -3,
            }
        )

    if snapshot.get("moon_sign") in FIXED_SIGNS:
        score += 2
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": "Moon in a fixed sign favors endurance",
                "weight": 2,
            }
        )

    if snapshot.get("mutual") != "none":
        score += 2
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Mutual reception supports the continuance of the relationship: {snapshot['display_text']}",
                "weight": 2,
            }
        )
    elif snapshot.get("one_way"):
        score += 1
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": "One-way reception provides limited but real support",
                "weight": 1,
            }
        )

    if snapshot.get("quesited_house") in {1, 4, 7, 10}:
        score += 1
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Quesited significator {snapshot['quesited_name']} is angular or prominent",
                "weight": 1,
            }
        )

    if snapshot.get("querent_dignity", 0) <= -5:
        score -= 2
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Querent significator {snapshot['querent_name']} is badly afflicted, showing worry or instability on the querent's side",
                "weight": -2,
            }
        )

    if snapshot.get("quesited_retrograde"):
        score -= 1
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Quesited significator {snapshot['quesited_name']} is retrograde",
                "weight": -1,
            }
        )

    next_planet = snapshot.get("moon_next_planet")
    next_aspect = snapshot.get("moon_next_aspect")
    if next_planet == Planet.SATURN and next_aspect in {Aspect.SQUARE, Aspect.OPPOSITION}:
        score -= 3
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": "Moon's next hard aspect to Saturn warns of strain or coldness still to be worked through",
                "weight": -3,
            }
        )

    if score >= 4:
        result = "YES"
        confidence = 78
    else:
        result = "NO"
        confidence = 74 if score <= -2 else 64

    return {
        "applies": True,
        "result": result,
        "confidence": confidence,
        "score": score,
        "reasoning": reasoning,
    }


def evaluate_relationship_affection_snapshot(
    snapshot: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Evaluate reciprocal-affection questions in a Lilly-style way.

    A question such as "Will X and I like one another romantically?" asks about
    mutual affection, not just contact. Lilly repeatedly emphasizes reception in
    love questions; mutual reception shows the two still love one another,
    whereas one-way reception is insufficient to prove reciprocity.
    """

    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Relationship Doctrine",
            "rule": "Relationship family: affection/reciprocity (judge mutual liking by reception before event-contact)",
            "weight": 0,
        }
    ]

    score = 0

    if snapshot.get("mutual") != "none":
        score += 6
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Mutual reception present: {snapshot['display_text']}",
                "weight": 6,
            }
        )
    elif snapshot.get("one_way"):
        score -= 4
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": "One-way reception only: one significator receives, but reciprocity is not shown",
                "weight": -4,
            }
        )
    else:
        score -= 5
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": "No mutual reception between significators: little evidence of reciprocal romantic feeling",
                "weight": -5,
            }
        )

    if snapshot.get("perfects"):
        score += 1
        aspect_name = snapshot.get("aspect_name") or "Applying aspect"
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"{aspect_name} can describe contact or a meeting, but does not by itself prove mutual liking",
                "weight": 1,
            }
        )

    if snapshot.get("quesited_solar_condition") in {"Combustion", "Under the Beams"}:
        score -= 3
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Quesited significator {snapshot['quesited_name']} is {snapshot['quesited_solar_condition'].lower()}, weakening clear romantic testimony",
                "weight": -3,
            }
        )

    if snapshot.get("querent_dignity", 0) <= -5:
        score -= 1
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Querent significator {snapshot['querent_name']} is badly debilitated, suggesting desire out of weakness rather than healthy reciprocity",
                "weight": -1,
            }
        )

    if snapshot.get("quesited_dignity", 0) <= -5:
        score -= 2
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Quesited significator {snapshot['quesited_name']} is badly debilitated, reducing stable romantic inclination",
                "weight": -2,
            }
        )

    if snapshot.get("quesited_retrograde"):
        score -= 1
        reasoning.append(
            {
                "stage": "Relationship Doctrine",
                "rule": f"Quesited significator {snapshot['quesited_name']} is retrograde, showing withdrawal or reconsideration",
                "weight": -1,
            }
        )

    if score >= 4:
        result = "YES"
        confidence = 78
    elif score <= -3:
        result = "NO"
        confidence = 80
    else:
        result = "NO"
        confidence = 65

    return {
        "applies": True,
        "result": result,
        "confidence": confidence,
        "score": score,
        "reasoning": reasoning,
    }
