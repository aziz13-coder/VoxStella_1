from __future__ import annotations

from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


COSMETIC_TOKENS = (
    "cosmetic surgery",
    "plastic surgery",
    "face lift",
    "facelift",
    "nose job",
    "rhinoplasty",
    "botox",
    "liposuction",
    "tummy tuck",
    "breast implant",
    "augmentation",
)

PROCEDURE_TOKENS = (
    "surgery",
    "surgical",
    "surgeon",
    "operation",
    "operate",
    "operated",
    "procedure",
)

MEDICAL_CONTEXT_TOKENS = (
    "doctor",
    "hospital",
    "clinic",
    "medical",
    "recovery",
    "recover",
    "complication",
    "complications",
    "risky",
    "risk",
    "go well",
    "go smoothly",
    "needed",
    "need",
    "have surgery",
)


def analyze_surgery_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify surgery, procedure, and cosmetic-operation questions.

    Traditional sources treat medical procedures as more than a plain illness
    chart: the patient, illness, practitioner, and surgery itself all matter.
    Cosmetic procedures are different again, because they primarily concern the
    body's appearance and the cost or value of the undertaking rather than a
    disease question.
    """

    q = (question or "").lower().strip()
    if not q:
        return None

    has_cosmetic = any(token in q for token in COSMETIC_TOKENS)
    has_explicit_procedure = any(token in q for token in PROCEDURE_TOKENS)
    has_medical_context = any(token in q for token in MEDICAL_CONTEXT_TOKENS)

    if has_cosmetic:
        subject_house = int((third_person_analysis or {}).get("subject_house") or 1)
        cost_house = _turn(subject_house, 2)
        return {
            "family": "cosmetic_procedure",
            "category_override": Category.GENERAL,
            "relevant_houses": [subject_house, cost_house],
            "subject_house": subject_house,
            "cost_house": cost_house,
            "quesited_house": subject_house,
            "doctrine": "Elective cosmetic surgery is judged first from the body and appearance, with the cost of the undertaking also in view, rather than as an ordinary illness chart.",
        }

    if not has_explicit_procedure:
        return None

    # Bare 'operation' can be non-medical; require explicit medical/procedure
    # context before routing it as a health chart.
    if "operation" in q and not (
        "surgery" in q
        or "surgeon" in q
        or has_medical_context
    ):
        return None

    subject_house = int((third_person_analysis or {}).get("subject_house") or 1)
    illness_house = _turn(subject_house, 6)
    doctor_house = _turn(subject_house, 7)
    procedure_house = _turn(subject_house, 8)

    return {
        "family": "medical_procedure",
        "category_override": Category.HEALTH,
        "relevant_houses": [subject_house, illness_house, doctor_house, procedure_house],
        "subject_house": subject_house,
        "illness_house": illness_house,
        "doctor_house": doctor_house,
        "procedure_house": procedure_house,
        "quesited_house": procedure_house,
        "doctrine": "Medical procedure questions keep the patient, illness, practitioner, and surgery itself in view instead of collapsing to a generic outcome chart.",
    }
