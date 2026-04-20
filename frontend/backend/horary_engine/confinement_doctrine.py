from __future__ import annotations

from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


ARREST_TOKENS = (
    "arrested",
    "be arrested",
    "arrest",
    "detained",
    "detain",
    "taken into custody",
)

PRISON_TOKENS = (
    "prison",
    "jailed",
    "jail",
    "imprisoned",
    "incarcerated",
    "locked up",
)

RELEASE_TOKENS = (
    "get out of prison",
    "get out of jail",
    "released from prison",
    "release from prison",
    "released from jail",
    "release from jail",
    "out of prison",
    "out of jail",
    "serve till the end",
    "serve to the end",
    "serve until the end",
    "get out sooner",
    "released sooner",
)


def analyze_confinement_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify arrest, imprisonment, and prison-release questions.

    Arrest questions are primarily about the authority taking action. Prison
    and imprisonment questions are primarily about confinement, which stays on
    the radical 12th in the external doctrine sources used here. When the
    question is about another person, the subject remains visible alongside the
    confinement axis.
    """

    q = (question or "").lower().strip()
    if not q:
        return None

    subject_house = int((third_person_analysis or {}).get("subject_house") or 1)
    is_third_person = bool((third_person_analysis or {}).get("is_third_person"))
    houses_with_subject = [1, subject_house] if is_third_person and subject_house != 1 else [1]

    has_prison = any(token in q for token in PRISON_TOKENS)
    has_release = any(token in q for token in RELEASE_TOKENS)
    has_arrest = any(token in q for token in ARREST_TOKENS)

    if has_release and has_prison:
        relevant_houses = list(dict.fromkeys(houses_with_subject + [12]))
        return {
            "family": "confinement_release",
            "category_override": Category.GENERAL,
            "relevant_houses": relevant_houses,
            "subject_house": subject_house,
            "confinement_house": 12,
            "quesited_house": subject_house if is_third_person else 12,
            "doctrine": "Release-from-prison questions keep the imprisoned person visible while the prison itself remains on the 12th as the confinement axis.",
        }

    if has_prison:
        relevant_houses = list(dict.fromkeys(houses_with_subject + [12]))
        return {
            "family": "confinement",
            "category_override": Category.GENERAL,
            "relevant_houses": relevant_houses,
            "subject_house": subject_house,
            "confinement_house": 12,
            "quesited_house": 12 if not is_third_person else subject_house,
            "doctrine": "Prison and imprisonment questions judge confinement through the 12th, while keeping the subject person visible when the chart is asked about someone else.",
        }

    if has_arrest:
        relevant_houses = list(dict.fromkeys(houses_with_subject + [10]))
        return {
            "family": "arrest_authority",
            "category_override": Category.GENERAL,
            "relevant_houses": relevant_houses,
            "subject_house": subject_house,
            "authority_house": 10,
            "quesited_house": 10,
            "doctrine": "Arrest questions keep the authority or government side visible on the 10th rather than flattening the question into a generic other-person chart.",
        }

    return None
