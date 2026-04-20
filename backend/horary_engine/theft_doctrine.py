from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


THEFT_TOKENS = (
    "thief",
    "stolen",
    "steal",
    "stole",
    "robbed",
    "rob",
    "burgled",
    "burglary",
    "taken by someone",
)

MONEY_TOKENS = (
    "money",
    "cash",
    "funds",
    "wages",
    "salary",
    "pay",
    "coins",
    "notes",
)


def analyze_theft_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify theft and stolen-item questions into reusable doctrine families.

    Traditional theft charts keep the thief on the 7th, the querent's goods on
    the 2nd, and, when tracing the stolen money or goods into the other party's
    possession, the thief's goods on the 8th.
    """

    q = (question or "").lower().strip()
    if not q:
        return None

    if not any(token in q for token in THEFT_TOKENS):
        return None

    identification_patterns = (
        r"\bwho is (?:the )?thief\b",
        r"\bwho stole\b",
        r"\bis he a thief\b",
        r"\bis she a thief\b",
        r"\bis this person a thief\b",
    )
    if any(re.search(pattern, q, re.IGNORECASE) for pattern in identification_patterns):
        return {
            "family": "thief_identification",
            "category_override": Category.GENERAL,
            "relevant_houses": [1, 7],
            "quesited_house": 7,
            "thief_house": 7,
            "doctrine": "In theft-identification questions, the thief is judged from the 7th as the other party or open enemy.",
        }

    if any(token in q for token in MONEY_TOKENS):
        return {
            "family": "suspected_money_theft",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 2, 7, 8],
            "quesited_house": 7,
            "money_house": 2,
            "thief_house": 7,
            "thief_possession_house": 8,
            "doctrine": "When money is suspected to have been stolen, the querent's money stays on the 2nd, the thief is on the 7th, and the thief's possession of the money is shown by the 8th.",
        }

    return {
        "family": "stolen_object",
        "category_override": Category.LOST_OBJECT,
        "relevant_houses": [1, 2, 7],
        "quesited_house": 2,
        "object_house": 2,
        "thief_house": 7,
        "doctrine": "A stolen-object question keeps the item on the 2nd but must still judge the thief from the 7th once theft is explicit.",
    }
