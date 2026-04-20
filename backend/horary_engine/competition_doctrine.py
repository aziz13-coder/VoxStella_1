from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..taxonomy import Category
    from ..models import Aspect, Planet
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category
    from models import Aspect, Planet


def analyze_competition_question_text(question: str) -> Dict[str, Any] | None:
    """Classify contest questions that require non-generic house assignments."""

    q = (question or "").lower().strip()
    if not q:
        return None

    office_terms = (
        "presidency",
        "president",
        "governor",
        "mayor",
        "prime minister",
        "senator",
        "office",
        "election",
        "elect",
        "win the seat",
    )
    champion_terms = (
        "champion",
        "retain his belt",
        "retain her belt",
        "retain the belt",
        "retain his title",
        "retain her title",
        "retain the title",
        "title defense",
        "defend his belt",
        "defend her belt",
        "challenger",
        "belt",
    )
    win_terms = (" win", " wins", "won", "defeat", "beat", "victory", "retain")
    confidence_terms = (
        "vote of no confidence",
        "confidence vote",
        "leadership challenge",
        "survive the vote",
        "survive the confidence vote",
        "remain prime minister",
        "stay in office",
        "stay on",
    )

    if any(token in q for token in champion_terms):
        return {
            "family": "contest_champion_vs_challenger",
            "category_override": Category.GENERAL,
            "relevant_houses": [10, 4],
            "querent_house": 10,
            "quesited_house": 4,
            "incumbent_house": 10,
            "challenger_house": 4,
            "doctrine": "A reigning champion or title-holder is judged as the king in the 10th, with the challenger in the 4th.",
        }

    if any(token in q for token in confidence_terms) and (
        any(token in q for token in office_terms) or "vote of no confidence" in q
    ):
        return {
            "family": "contest_public_office_confidence",
            "category_override": Category.CAREER,
            "relevant_houses": [10, 7],
            "querent_house": 10,
            "quesited_house": 7,
            "incumbent_house": 10,
            "challenger_house": 7,
            "office_house": 10,
            "doctrine": "Confidence-vote questions judge whether the office-holder retains power against challengers, using the office-holder in the 10th and opponents in the 7th.",
        }

    if any(token in q for token in office_terms) and any(token in q for token in win_terms):
        return {
            "family": "contest_public_office",
            "category_override": Category.CAREER,
            "relevant_houses": [1, 10],
            "querent_house": 1,
            "quesited_house": 10,
            "incumbent_house": 10,
            "office_house": 10,
            "doctrine": "Public office contests are judged against the office or incumbent in the 10th, not as a generic 7th-house opponent chart.",
        }

    return None


def build_public_office_contest_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    competition_analysis: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = competition_analysis or {}
    if analysis.get("family") != "contest_public_office":
        return None

    candidate_pos = chart.planets.get(querent_planet)
    office_pos = chart.planets.get(quesited_planet)
    if not candidate_pos or not office_pos:
        return None

    moon_next = getattr(chart, "moon_next_aspect", None)
    return {
        "family": "contest_public_office",
        "candidate_name": querent_planet.value,
        "candidate_dignity": int(getattr(candidate_pos, "dignity_score", 0) or 0),
        "candidate_house": getattr(candidate_pos, "house", None),
        "candidate_retrograde": bool(getattr(candidate_pos, "retrograde", False)),
        "office_name": quesited_planet.value,
        "office_dignity": int(getattr(office_pos, "dignity_score", 0) or 0),
        "office_house": getattr(office_pos, "house", None),
        "office_retrograde": bool(getattr(office_pos, "retrograde", False)),
        "moon_next_planet": getattr(moon_next, "planet", None),
        "moon_next_aspect": getattr(moon_next, "aspect", None),
        "moon_next_applying": getattr(moon_next, "applying", None),
    }


def evaluate_public_office_contest_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    """Evaluate explicit office contests where no direct perfection is found."""

    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Competition Doctrine",
            "rule": "Public-office family: the candidate is judged against the office or incumbent in the 10th",
            "weight": 0,
        }
    ]
    candidate_score = 0
    office_score = 0

    if snapshot.get("candidate_house") in {1, 4, 7, 10}:
        candidate_score += 1
    if snapshot.get("office_house") in {1, 4, 7, 10}:
        office_score += 2
        reasoning.append(
            {
                "stage": "Competition Doctrine",
                "rule": "The office/incumbent significator is angular, strengthening the holder of the office",
                "weight": -2,
            }
        )

    candidate_dignity = snapshot.get("candidate_dignity", 0)
    office_dignity = snapshot.get("office_dignity", 0)
    if office_dignity > candidate_dignity:
        office_score += 2
        reasoning.append(
            {
                "stage": "Competition Doctrine",
                "rule": "The office significator is stronger than the challenger",
                "weight": -2,
            }
        )
    elif candidate_dignity > office_dignity:
        candidate_score += 2
        reasoning.append(
            {
                "stage": "Competition Doctrine",
                "rule": "The challenger is stronger than the office significator",
                "weight": 2,
            }
        )

    if snapshot.get("candidate_retrograde"):
        office_score += 1
        reasoning.append(
            {
                "stage": "Competition Doctrine",
                "rule": "The challenger's significator is retrograde, weakening the bid for office",
                "weight": -1,
            }
        )

    moon_next_planet = snapshot.get("moon_next_planet")
    moon_next_aspect = snapshot.get("moon_next_aspect")
    if (
        snapshot.get("moon_next_applying")
        and moon_next_aspect in {Aspect.CONJUNCTION, Aspect.SEXTILE, Aspect.TRINE}
    ):
        moon_target = getattr(moon_next_planet, "value", moon_next_planet)
        if moon_target == snapshot.get("office_name"):
            office_score += 2
            reasoning.append(
                {
                    "stage": "Competition Doctrine",
                    "rule": "The Moon next applies to the office significator, supporting the incumbent side",
                    "weight": -2,
                }
            )
        elif moon_target == snapshot.get("candidate_name"):
            candidate_score += 2
            reasoning.append(
                {
                    "stage": "Competition Doctrine",
                    "rule": "The Moon next applies to the candidate, supporting the challenge",
                    "weight": 2,
                }
            )

    delta = candidate_score - office_score
    if delta <= -2:
        return {
            "applies": True,
            "result": "NO",
            "confidence": 76,
            "reasoning": reasoning,
            "score": delta,
        }
    if delta >= 3:
        return {
            "applies": True,
            "result": "YES",
            "confidence": 74,
            "reasoning": reasoning,
            "score": delta,
        }

    return {"applies": False, "reasoning": reasoning, "result": None, "score": delta}


def build_champion_defense_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    competition_analysis: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = competition_analysis or {}
    if analysis.get("family") != "contest_champion_vs_challenger":
        return None

    champion_pos = chart.planets.get(querent_planet)
    challenger_pos = chart.planets.get(quesited_planet)
    if not champion_pos or not challenger_pos:
        return None

    moon_next = getattr(chart, "moon_next_aspect", None)
    return {
        "family": "contest_champion_vs_challenger",
        "champion_name": querent_planet.value,
        "champion_dignity": int(getattr(champion_pos, "dignity_score", 0) or 0),
        "champion_house": getattr(champion_pos, "house", None),
        "champion_retrograde": bool(getattr(champion_pos, "retrograde", False)),
        "challenger_name": quesited_planet.value,
        "challenger_dignity": int(getattr(challenger_pos, "dignity_score", 0) or 0),
        "challenger_house": getattr(challenger_pos, "house", None),
        "challenger_retrograde": bool(getattr(challenger_pos, "retrograde", False)),
        "moon_next_planet": getattr(moon_next, "planet", None),
        "moon_next_aspect": getattr(moon_next, "aspect", None),
        "moon_next_applying": getattr(moon_next, "applying", None),
    }


def evaluate_champion_defense_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    """Evaluate title-defense charts via champion/king asymmetry."""

    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Competition Doctrine",
            "rule": "Champion-defense family: the reigning holder of the title is judged as the king in the 10th, with the challenger in the 4th",
            "weight": 0,
        }
    ]
    champion_score = 0
    challenger_score = 0

    champion_score += 2
    reasoning.append(
        {
            "stage": "Competition Doctrine",
            "rule": "The reigning holder of the title receives the kingly/incumbent advantage",
            "weight": 2,
        }
    )

    if snapshot.get("champion_house") in {1, 4, 7, 10}:
        champion_score += 2
        reasoning.append(
            {
                "stage": "Competition Doctrine",
                "rule": "The champion's significator is angular",
                "weight": 2,
            }
        )
    if snapshot.get("challenger_house") in {1, 4, 7, 10}:
        challenger_score += 1

    champion_dignity = snapshot.get("champion_dignity", 0)
    challenger_dignity = snapshot.get("challenger_dignity", 0)
    if champion_dignity > challenger_dignity:
        champion_score += 2
        reasoning.append(
            {
                "stage": "Competition Doctrine",
                "rule": "The champion's significator is stronger than the challenger's",
                "weight": 2,
            }
        )
    elif challenger_dignity > champion_dignity:
        challenger_score += 2
        reasoning.append(
            {
                "stage": "Competition Doctrine",
                "rule": "The challenger is stronger than the reigning champion",
                "weight": -2,
            }
        )

    if snapshot.get("challenger_retrograde"):
        champion_score += 1
        reasoning.append(
            {
                "stage": "Competition Doctrine",
                "rule": "The challenger's significator is retrograde, supporting title retention",
                "weight": 1,
            }
        )

    moon_next_planet = snapshot.get("moon_next_planet")
    moon_next_aspect = snapshot.get("moon_next_aspect")
    if (
        snapshot.get("moon_next_applying")
        and moon_next_aspect in {Aspect.CONJUNCTION, Aspect.SEXTILE, Aspect.TRINE}
    ):
        moon_target = getattr(moon_next_planet, "value", moon_next_planet)
        if moon_target == snapshot.get("champion_name"):
            champion_score += 2
            reasoning.append(
                {
                    "stage": "Competition Doctrine",
                    "rule": "The Moon next applies to the champion, supporting title retention",
                    "weight": 2,
                }
            )
        elif moon_target == snapshot.get("challenger_name"):
            challenger_score += 2
            reasoning.append(
                {
                    "stage": "Competition Doctrine",
                    "rule": "The Moon next applies to the challenger",
                    "weight": -2,
                }
            )
        elif moon_target in {"Jupiter", "Venus"}:
            champion_score += 2
            reasoning.append(
                {
                    "stage": "Competition Doctrine",
                    "rule": f"The Moon next applies to benefic {moon_target}, supporting the reigning champion",
                    "weight": 2,
                }
            )

    delta = champion_score - challenger_score
    if delta >= 2:
        return {
            "applies": True,
            "result": "YES",
            "confidence": min(86, 68 + (delta * 4)),
            "reasoning": reasoning,
            "score": delta,
        }
    if delta <= -2:
        return {
            "applies": True,
            "result": "NO",
            "confidence": 74,
            "reasoning": reasoning,
            "score": delta,
        }

    return {"applies": False, "reasoning": reasoning, "result": None, "score": delta}
