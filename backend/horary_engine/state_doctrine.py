from __future__ import annotations

import re
from typing import Any, Dict, List

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


_QUESTION_STOPWORDS = {
    "Will",
    "What",
    "When",
    "Where",
    "Why",
    "How",
    "Is",
    "Are",
    "Can",
    "Could",
    "Would",
    "Should",
    "The",
    "My",
    "A",
    "An",
}


def _geopolitical_actors(question: str) -> List[str]:
    actors: List[str] = []
    for match in re.finditer(r"\b(?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+(?:[A-Z]{2,}|[A-Z][a-z]+))*\b", question or ""):
        parts = match.group(0).strip().split()
        while parts and parts[0] in _QUESTION_STOPWORDS:
            parts = parts[1:]
        actor = " ".join(parts).strip()
        if not actor or actor in _QUESTION_STOPWORDS:
            continue
        if actor not in actors:
            actors.append(actor)
    return actors


def analyze_state_question_text(question: str) -> Dict[str, Any] | None:
    """Classify geopolitical/state-action questions that need non-generic houses."""

    original = (question or "").strip()
    if not original:
        return None

    q = original.lower()
    actors = _geopolitical_actors(original)

    referendum_tokens = ("referendum", "independence", "secede", "secession")
    state_tokens = ("government", "parliament", "state", "country", "nation")
    war_tokens = ("invade", "invasion", "attack", "war", "military", "troops", "strike", "bomb", "border")

    if any(token in q for token in referendum_tokens) and (
        any(token in q for token in state_tokens) or bool(actors)
    ):
        return {
            "family": "foreign_state_constitutional_action",
            "category_override": Category.GENERAL,
            "relevant_houses": [1, 9],
            "querent_house": 1,
            "quesited_house": 9,
            "homeland_house": 1,
            "foreign_state_house": 9,
            "actors": actors,
            "doctrine": "Questions about a foreign country's constitutional or political action are judged from the 9th against the radical 1st.",
        }

    if len(actors) >= 2 and any(token in q for token in war_tokens):
        return {
            "family": "foreign_state_military_action",
            "category_override": Category.GENERAL,
            "relevant_houses": [9, 11],
            "querent_house": 9,
            "quesited_house": 11,
            "foreign_state_house": 9,
            "target_state_house": 11,
            "actors": actors,
            "doctrine": "A foreign nation's action against a neighboring state is judged from the 9th and the 3rd from the 9th.",
        }

    return None
