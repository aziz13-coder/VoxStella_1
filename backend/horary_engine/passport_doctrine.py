from __future__ import annotations

from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


def analyze_passport_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify passport and travel-document questions into shared families."""

    q = (question or "").lower().strip()
    if not q:
        return None

    def has_any(*tokens: str) -> bool:
        return any(token in q for token in tokens)

    document_tokens = (
        "passport",
        "passports",
        "travel document",
        "travel documents",
        "passport book",
    )
    approval_tokens = (
        "approve",
        "approved",
        "approval",
        "renewal",
        "renew",
        "renewed",
        "application",
        "issue",
        "issued",
        "issuance",
    )
    arrival_tokens = (
        "be here",
        "here on time",
        "on time",
        "arrive",
        "arrival",
        "delivered",
        "delivery",
        "mail",
        "mailed",
        "post",
        "posted",
        "courier",
        "receive",
        "received",
        "get the passport",
        "get the passports",
        "get my passport back",
        "get my passports back",
    )
    lost_tokens = (
        "where is",
        "where's",
        "lost",
        "missing",
        "stolen",
        "misplaced",
    )

    if not has_any(*document_tokens):
        return None

    subject_house = 1
    if third_person_analysis and third_person_analysis.get("is_third_person"):
        subject_house = int(third_person_analysis.get("subject_house") or 1)

    if has_any(*lost_tokens):
        document_house = _turn(subject_house, 2) if subject_house != 1 else 2
        family = "passport_lost_document" if subject_house == 1 else "turned_passport_lost_document"
        doctrine = (
            "A lost passport remains a lost-object discovery question. Keep the passport/document metadata "
            "visible, but route judgment through the lost-object recovery and location rules."
        )
        return {
            "family": family,
            "category_override": Category.LOST_OBJECT,
            "document_house": document_house,
            "object_house": document_house,
            "doctrine": doctrine,
        }

    if has_any(*approval_tokens):
        authorization_house = _turn(subject_house, 9) if subject_house != 1 else 9
        authority_house = _turn(subject_house, 10) if subject_house != 1 else 10
        family = "passport_authorization" if subject_house == 1 else "turned_passport_authorization"
        doctrine = (
            "Passport renewal or issuance is judged as an official travel-document authorization, "
            "keeping the travel-paper side visible with the approving authority."
        )
        return {
            "family": family,
            "category_override": Category.TRAVEL,
            "relevant_houses": [subject_house, authorization_house, authority_house],
            "subject_house": subject_house,
            "document_house": authorization_house,
            "authority_house": authority_house,
            "quesited_house": authorization_house,
            "doctrine": doctrine,
        }

    if has_any(*arrival_tokens) or "passport" in q or "passports" in q:
        document_house = _turn(subject_house, 3) if subject_house != 1 else 3
        family = "passport_document_arrival" if subject_house == 1 else "turned_passport_document_arrival"
        doctrine = (
            "Passport arrival or receipt is judged as a document question, so the papers stay on the 3rd "
            "rather than being mistaken for exams or generic education."
        )
        return {
            "family": family,
            "category_override": Category.GENERAL,
            "relevant_houses": [subject_house, document_house],
            "subject_house": subject_house,
            "document_house": document_house,
            "quesited_house": document_house,
            "doctrine": doctrine,
        }

    return None
