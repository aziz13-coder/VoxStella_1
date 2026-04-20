from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


LEGAL_CORE_TOKENS = (
    "court",
    "lawsuit",
    "legal battle",
    "court battle",
    "legal case",
    "litigation",
    "judge",
    "trial",
    "tribunal",
    "hearing",
    "appeal",
    "sue",
    "suing",
    "sued",
)

INHERITANCE_TOKENS = (
    "inheritance",
    "legacy",
    "estate",
    "testament",
    "inherit",
    "inherit rights",
)

COMPENSATION_TOKENS = (
    "compensation",
    "owed",
    "owe me",
    "pay me",
    "pay the money",
    "wages",
    "salary",
    "severance",
    "settlement",
    "damages",
)

THIRD_PERSON_SUBJECT_PATTERN = re.compile(
    r"^\s*(will|would|can|could|did|has|have|is|are|should)\s+(he|she|they)\b"
)
TITLED_SUBJECT_PATTERN = re.compile(
    r"^\s*(will|would|can|could|did|has|have|is|are|should)\s+my\s+"
    r"(father|dad|mother|mom|mum|grandfather|brother|sister|friend|son|daughter|child|husband|wife|partner|client)\b"
)


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


def _has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def analyze_lawsuit_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify legal-adjudication questions into a shared court-doctrine family.

    The core axis for ordinary litigation is querent/opponent/judge/end-of-matter.
    Subject-matter houses like the 8th for inheritance may join the chart, but
    should not replace the legal frame itself.
    """

    original = (question or "").strip()
    if not original:
        return None

    q = original.lower()
    has_legal_core = _has_any(q, LEGAL_CORE_TOKENS)
    has_case_phrase = bool(
        re.search(r"\b(win|lose|won|lost|success|succeed)\b.*\bcase\b", q)
        or re.search(r"\bcase\b.*\bagainst\b", q)
    )

    if not (has_legal_core or has_case_phrase):
        return None

    subject_house = 1
    if (
        third_person_analysis
        and third_person_analysis.get("is_third_person")
        and (
            THIRD_PERSON_SUBJECT_PATTERN.search(q)
            or TITLED_SUBJECT_PATTERN.search(q)
        )
    ):
        subject_house = int(third_person_analysis.get("subject_house") or 7)

    opponent_house = _turn(subject_house, 7)
    judge_house = _turn(subject_house, 10)
    outcome_house = _turn(subject_house, 4)

    relevant_houses = [subject_house]
    for house in (opponent_house, judge_house, outcome_house):
        if house not in relevant_houses:
            relevant_houses.append(house)

    family = "court_adjudication"
    doctrine = (
        "Court-battle questions keep the querent, opponent, judge, and end of "
        "the matter in view; subject-matter houses may join but do not replace "
        "the legal axis."
    )

    subject_matter_house = None
    if _has_any(q, INHERITANCE_TOKENS):
        subject_matter_house = _turn(subject_house, 8)
        if subject_matter_house not in relevant_houses:
            relevant_houses.append(subject_matter_house)
        family = "inheritance_litigation"
        doctrine = (
            "Inheritance disputes remain court-adjudication charts first; the "
            "8th-house estate joins as subject matter without replacing the "
            "opponent/judge/outcome structure."
        )
    elif _has_any(q, COMPENSATION_TOKENS):
        subject_matter_house = _turn(subject_house, 2)
        family = "compensation_litigation"
        doctrine = (
            "Compensation and wage disputes are still legal-adjudication charts "
            "first; the claim for money is a secondary witness, not the whole "
            "question."
        )

    result: Dict[str, Any] = {
        "family": family,
        "category_override": Category.LAWSUIT,
        "relevant_houses": relevant_houses,
        "querent_house": subject_house,
        "opponent_house": opponent_house,
        "judge_house": judge_house,
        "outcome_house": outcome_house,
        "quesited_house": opponent_house,
        "doctrine": doctrine,
    }
    if subject_matter_house is not None:
        result["subject_matter_house"] = subject_matter_house
    return result
