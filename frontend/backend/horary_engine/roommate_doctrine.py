from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


ROOMMATE_TOKENS = (
    "roommate",
    "room mate",
    "housemate",
    "house mate",
    "flatmate",
    "flat mate",
)


def _has_phrase(text: str, phrase: str) -> bool:
    pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def _has_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_has_phrase(text, phrase) for phrase in phrases)


def analyze_roommate_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify roommate and cohabitation questions into shared families."""

    q = (question or "").lower().strip()
    if not q:
        return None

    has_roommate = _has_any_phrase(q, ROOMMATE_TOKENS)
    cohabitation_tokens = (
        "move in together",
        "live together",
        "living together",
        "move in with",
        "share a home",
        "share a house",
        "share a flat",
        "share an apartment",
    )
    doctrine_query_tokens = (
        "what house for",
        "which house for",
        "what house signifies",
        "which house signifies",
    )
    whereabouts_tokens = (
        "where is",
        "where's",
        "where are",
    )

    if _has_any_phrase(q, cohabitation_tokens):
        return {
            "family": "cohabitation_decision",
            "category_override": Category.RELATIONSHIP,
            "relevant_houses": [1, 7, 4],
            "subject_house": 1,
            "partner_house": 7,
            "home_house": 4,
            "quesited_house": 7,
            "doctrine": "Moving in together is judged from the relationship axis plus the 4th-house home or cohabitation side of the matter.",
        }

    if not has_roommate:
        return None

    roommate_house = 7
    if third_person_analysis and third_person_analysis.get("subject_house"):
        roommate_house = int(third_person_analysis.get("subject_house") or 7)

    if _has_any_phrase(q, whereabouts_tokens):
        return {
            "family": "roommate_whereabouts",
            "category_override": Category.GENERAL,
            "relevant_houses": [1, roommate_house],
            "subject_house": 1,
            "roommate_house": roommate_house,
            "quesited_house": roommate_house,
            "doctrine": "A roommate is judged as a person sharing the home by agreement, so their whereabouts stay on the 7th rather than being treated like a lost possession.",
        }

    if _has_any_phrase(q, doctrine_query_tokens):
        return {
            "family": "roommate_person",
            "category_override": Category.GENERAL,
            "relevant_houses": [1, roommate_house],
            "subject_house": 1,
            "roommate_house": roommate_house,
            "quesited_house": roommate_house,
            "doctrine": "A roommate or housemate is treated as the other person in a cohabiting or contractual arrangement, so the operative house is the 7th.",
        }

    return {
        "family": "roommate_person",
        "category_override": Category.GENERAL,
        "relevant_houses": [1, roommate_house],
        "subject_house": 1,
        "roommate_house": roommate_house,
        "quesited_house": roommate_house,
        "doctrine": "A roommate is judged as a cohabiting other person, not as property or a lost object.",
    }
