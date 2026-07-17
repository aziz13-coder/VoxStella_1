from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


def analyze_immigration_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify visa, permit, and immigration-approval questions.

    Traditional doctrine keeps foreign travel, border-crossing, and the papers
    that authorize it on the 9th. When the question explicitly turns on an
    approving agency, embassy, or work authorization, the 10th is also kept in
    view as the authority or public decision-maker.
    """

    q = (question or "").lower().strip()
    if not q:
        return None

    def has_any(*tokens: str) -> bool:
        """Match complete words/phrases, not substrings inside unrelated words."""

        return any(
            re.search(
                r"(?<!\w)" + re.escape(token).replace(r"\ ", r"\s+") + r"(?!\w)",
                q,
            )
            for token in tokens
        )

    authorization_tokens = (
        "visa",
        "permit",
        "immigration",
        "residency",
        "residence permit",
        "green card",
        "entry clearance",
        "travel authorization",
        "travel permit",
        "travel application",
        "work permit",
        "work visa",
        "student visa",
    )
    status_tokens = (
        "citizenship",
        "citizen",
        "naturalization",
        "naturalisation",
        "permanent resident",
        "permanent residence",
        "permanent residency",
        "residency status",
        "residence status",
        "green card",
        "resident card",
    )
    approval_tokens = (
        "approve",
        "approved",
        "approval",
        "deny",
        "denied",
        "grant",
        "granted",
        "issue",
        "issued",
        "application",
        "clearance",
    )
    authority_tokens = (
        "embassy",
        "consulate",
        "government",
        "immigration office",
        "immigration department",
        "uscis",
        "home office",
        "ministry",
        "authority",
        "agency",
        "department",
        "official",
    )
    work_tokens = (
        "work",
        "job",
        "employment",
        "employer",
        "hired",
        "offer",
        "position",
    )

    if not has_any(*(authorization_tokens + status_tokens)):
        return None

    status_question = has_any(*status_tokens)
    subject_house = None
    if third_person_analysis and third_person_analysis.get("is_third_person"):
        subject_house = int(third_person_analysis.get("subject_house") or 0) or None

    if subject_house:
        authorization_house = _turn(subject_house, 9)
        authority_house = _turn(subject_house, 10)
        work_house = _turn(subject_house, 10) if has_any(*work_tokens) else None
        family = "turned_status_authorization" if status_question else "turned_visa_authorization"
        doctrine = (
            "When the question is about another person's citizenship, residency, green card, or visa, "
            "that person becomes the operative subject; their turned 9th shows the papers or status, "
            "and their turned 10th shows the approving authority."
        )
        if work_house is not None:
            family = "turned_work_visa_authorization"
            doctrine = (
                "A relative's work visa or status keeps that person as the operative subject, "
                "with the turned 9th for the authorization and the turned 10th for the work and approving authority."
            )
        return {
            "family": family,
            "category_override": Category.TRAVEL,
            "relevant_houses": [subject_house, authorization_house, authority_house],
            "subject_house": subject_house,
            "quesited_house": authorization_house,
            "authorization_house": authorization_house,
            "authority_house": authority_house,
            "work_house": work_house,
            "doctrine": doctrine,
        }

    if status_question:
        return {
            "family": "status_authorization",
            "category_override": Category.TRAVEL,
            "relevant_houses": [1, 9, 10],
            "subject_house": 1,
            "quesited_house": 9,
            "authorization_house": 9,
            "authority_house": 10,
            "doctrine": "Citizenship, permanent residence, and green-card status are judged as foreign-status or border-crossing authorizations on the 9th, with the state or approving authority also visible through the 10th.",
        }

    if has_any(*work_tokens):
        return {
            "family": "work_visa_authorization",
            "category_override": Category.TRAVEL,
            "relevant_houses": [1, 9, 10],
            "subject_house": 1,
            "quesited_house": 9,
            "authorization_house": 9,
            "authority_house": 10,
            "work_house": 10,
            "doctrine": "The visa or permit remains a 9th-house authorization, while the work side and approving authority stay visible through the 10th.",
        }

    if has_any(*approval_tokens) or has_any(*authority_tokens):
        return {
            "family": "visa_application_approval",
            "category_override": Category.TRAVEL,
            "relevant_houses": [1, 9, 10],
            "subject_house": 1,
            "quesited_house": 9,
            "authorization_house": 9,
            "authority_house": 10,
            "doctrine": "Visa or travel-authorization approval keeps the foreign-travel papers on the 9th and the approving authority on the 10th.",
        }

    return {
        "family": "visa_authorization",
        "category_override": Category.TRAVEL,
        "relevant_houses": [1, 9],
        "subject_house": 1,
        "quesited_house": 9,
        "authorization_house": 9,
        "doctrine": "A visa or permit itself is judged as a 9th-house foreign-travel or border-crossing authorization.",
    }
