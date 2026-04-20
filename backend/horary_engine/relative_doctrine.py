from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


MARRIAGE_TOKENS = (
    "get married",
    "married",
    "marry",
    "wedding",
    "spouse",
    "husband",
    "wife",
    "propose",
    "engaged",
    "engagement",
)

RELATIONSHIP_TOKENS = (
    "boyfriend",
    "girlfriend",
    "partner",
    "lover",
    "relationship",
    "happy with",
    "love",
    "together",
    "date",
    "dating",
    "romance",
)

WELFARE_TOKENS = (
    "is he ok",
    "is she ok",
    "is they ok",
    "is he okay",
    "is she okay",
    "safe",
    "well",
    "alive",
    "recover",
    "condition improve",
    "condition",
    "health",
    "ill",
    "sick",
)

POSSESSIVE_OBJECT_TOKENS = (
    "ashes",
    "wallet",
    "passport",
    "card",
    "cards",
    "keys",
    "phone",
    "iphone",
    "documents",
    "book",
    "books",
    "parcel",
    "package",
)


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


def analyze_relative_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify turned-relative questions into reusable doctrine families."""

    original = (question or "").strip()
    if not original:
        return None

    q = original.lower()
    if not (third_person_analysis and third_person_analysis.get("is_third_person")):
        return None

    subject_house = int(third_person_analysis.get("subject_house") or 0)
    if subject_house <= 0:
        return None

    if any(token in q for token in POSSESSIVE_OBJECT_TOKENS):
        return None

    if any(token in q for token in MARRIAGE_TOKENS):
        partner_house = _turn(subject_house, 7)
        return {
            "family": "turned_marriage",
            "category_override": Category.MARRIAGE,
            "relevant_houses": [subject_house, partner_house],
            "subject_house": subject_house,
            "partner_house": partner_house,
            "quesited_house": partner_house,
            "doctrine": "When the question is about a relative's marriage, the relative becomes the operative subject and marriage is judged from the turned 7th from that person's house.",
        }

    if any(token in q for token in RELATIONSHIP_TOKENS):
        partner_house = _turn(subject_house, 7)
        return {
            "family": "turned_relationship",
            "category_override": Category.RELATIONSHIP,
            "relevant_houses": [subject_house, partner_house],
            "subject_house": subject_house,
            "partner_house": partner_house,
            "quesited_house": partner_house,
            "doctrine": "When the question is about a relative's partner or relationship, that relative becomes the operative subject and the turned 7th shows the partner.",
        }

    where_match = bool(re.search(r"\bwhere(?:'s| is| are)\b", q))
    if where_match:
        if any(token in q for token in WELFARE_TOKENS):
            welfare_house = _turn(subject_house, 6)
            return {
                "family": "person_whereabouts_welfare",
                "category_override": Category.HEALTH,
                "relevant_houses": [subject_house, welfare_house],
                "subject_house": subject_house,
                "welfare_house": welfare_house,
                "quesited_house": welfare_house,
                "doctrine": "Questions about a relative's whereabouts and welfare are judged from that person's house and the turned 6th for their condition, not as lost-object charts.",
            }

        return {
            "family": "person_whereabouts",
            "category_override": Category.GENERAL,
            "relevant_houses": [subject_house],
            "subject_house": subject_house,
            "quesited_house": subject_house,
            "doctrine": "Where-is-person questions keep the missing person as the operative subject rather than treating them as a possession.",
        }

    return None
