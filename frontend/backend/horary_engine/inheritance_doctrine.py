from __future__ import annotations

from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


INHERITANCE_TOKENS = (
    "inheritance",
    "inherit",
    "legacy",
    "bequest",
    "bequeath",
    "probate",
)

PROPERTY_TOKENS = (
    "house",
    "home",
    "property",
    "land",
    "estate property",
    "real estate",
    "building",
    "farm",
    "apartment",
    "flat",
)

LITIGATION_TOKENS = (
    "court",
    "lawsuit",
    "legal",
    "judge",
    "trial",
    "litigation",
    "battle",
    "rights",
    "hearing",
    "appeal",
)


def _turn(base_house: int, offset: int) -> int:
    return ((base_house + offset - 2) % 12) + 1


def _unique(items: list[int]) -> list[int]:
    seen: list[int] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def analyze_inheritance_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify inheritance questions into transferable-money vs estate-property families.

    Generic inheritance remains an 8th-house matter. When the inherited thing
    is explicitly a house, land, or other immovable property, the 4th remains
    visible alongside the inheritance axis instead of collapsing into abstract
    estate money only.
    """

    q = (question or "").lower().strip()
    if not q:
        return None

    has_inheritance = any(token in q for token in INHERITANCE_TOKENS)
    if not has_inheritance:
        return None

    # Court fights over inheritance belong to lawsuit doctrine first.
    if any(token in q for token in LITIGATION_TOKENS):
        return None

    subject_house = int((third_person_analysis or {}).get("subject_house") or 1)
    estate_house = _turn(subject_house, 8)
    has_property = any(token in q for token in PROPERTY_TOKENS)

    if has_property:
        property_house = _turn(subject_house, 4)
        return {
            "family": "estate_property_inheritance",
            "category_override": Category.PROPERTY,
            "relevant_houses": _unique([subject_house, property_house, estate_house]),
            "subject_house": subject_house,
            "property_house": property_house,
            "estate_house": estate_house,
            "quesited_house": property_house,
            "doctrine": "When the inheritance is explicitly a house, land, or estate property, the 4th remains primary for the thing inherited while the 8th remains the transfer-by-inheritance axis.",
        }

    return {
        "family": "inheritance_transfer",
        "category_override": Category.DEATH,
        "relevant_houses": _unique([subject_house, estate_house]),
        "subject_house": subject_house,
        "estate_house": estate_house,
        "quesited_house": estate_house,
        "doctrine": "Inheritance without a specific immovable property remains an 8th-house transfer question, turned from the operative subject when necessary.",
    }
