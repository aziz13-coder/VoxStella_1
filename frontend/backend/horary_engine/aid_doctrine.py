from __future__ import annotations

from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


SCHOLARSHIP_TOKENS = (
    "scholarship",
    "scholarships",
    "bursary",
    "fellowship",
    "stipend",
)

HIGHER_EDUCATION_TOKENS = (
    "master",
    "masters",
    "master's",
    "graduate",
    "postgraduate",
    "phd",
    "doctorate",
    "degree",
    "program",
    "course",
    "college",
    "university",
    "study",
    "studies",
    "student",
)

ELIGIBILITY_TOKENS = (
    "accepted",
    "acceptance",
    "eligible",
    "eligibility",
    "qualify",
    "qualified",
    "income",
    "income level",
    "financial",
    "finances",
    "tuition",
)

PUBLIC_AID_TOKENS = (
    "financial aid",
    "student aid",
    "aid package",
    "tuition aid",
    "public aid",
    "government aid",
)


def analyze_aid_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify scholarships, grants, and public aid into shared families.

    The doctrine keeps educational scholarships primarily on the 9th and only
    adds the 2nd when eligibility, income, or support is materially part of the
    question. Public financial aid keeps the official or governmental funder on
    the 10th instead of collapsing into simple personal money.
    """

    q = (question or "").lower().strip()
    if not q:
        return None

    def has_any(*tokens: str) -> bool:
        return any(token in q for token in tokens)

    has_scholarship = has_any(*SCHOLARSHIP_TOKENS)
    has_higher_education = has_any(*HIGHER_EDUCATION_TOKENS)
    has_eligibility = has_any(*ELIGIBILITY_TOKENS)
    has_public_aid = has_any(*PUBLIC_AID_TOKENS)

    if has_scholarship:
        if third_person_analysis and third_person_analysis.get("is_third_person"):
            subject_house = int(third_person_analysis.get("subject_house") or 7)
            scholarship_house = _turn(subject_house, 9)
            return {
                "family": "turned_scholarship_support",
                "category_override": Category.EDUCATION,
                "relevant_houses": [subject_house, scholarship_house],
                "subject_house": subject_house,
                "education_house": scholarship_house,
                "scholarship_house": scholarship_house,
                "quesited_house": scholarship_house,
                "doctrine": "A relative's scholarship for higher study is judged from that person's house and the turned 9th for the scholarship or course sought.",
            }

        relevant_houses = [1, 9]
        if has_higher_education or has_eligibility:
            relevant_houses.append(2)
        return {
            "family": "education_scholarship_support",
            "category_override": Category.EDUCATION,
            "relevant_houses": relevant_houses,
            "education_house": 9,
            "scholarship_house": 9,
            "support_house": 2 if 2 in relevant_houses else None,
            "eligibility_house": 2 if 2 in relevant_houses else None,
            "quesited_house": 9,
            "doctrine": "Scholarship questions tied to higher study keep the scholarship or course on the 9th, while the querent's means or eligibility can join on the 2nd when the wording makes that material.",
        }

    if has_public_aid:
        return {
            "family": "public_financial_aid",
            "category_override": Category.FUNDING,
            "relevant_houses": [1, 10],
            "quesited_house": 10,
            "authority_house": 10,
            "support_house": 10,
            "doctrine": "Public or official financial aid is judged from the authority or official body in the 10th rather than as simple personal money.",
        }

    return None
