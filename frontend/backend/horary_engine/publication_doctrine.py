from __future__ import annotations

from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


PUBLICATION_TOKENS = (
    "publish",
    "published",
    "publication",
    "accepted",
    "acceptance",
    "in print",
    "printed",
    "printing",
)

WORK_TOKENS = (
    "book",
    "review",
    "article",
    "paper",
    "manuscript",
    "novel",
    "essay",
    "story",
    "poem",
    "journal",
    "magazine",
)

OUTLET_TOKENS = (
    "magazine",
    "journal",
    "publisher",
    "publishing house",
    "online magazine",
    "editor",
    "review",
)

GAIN_TOKENS = (
    "gain",
    "gains",
    "profit",
    "money",
    "paid",
    "payment",
    "earn",
    "income",
    "royalty",
    "royalties",
    "sell copies",
)


def analyze_publication_question_text(question: str) -> Dict[str, Any] | None:
    """Classify publication and publication-plus-gain questions.

    Traditional practice often keeps publication itself on the 9th. If the
    question also asks about the querent's gain from publication, the 2nd joins
    the 9th instead of replacing it.
    """

    q = (question or "").lower().strip()
    if not q:
        return None

    has_publication = any(token in q for token in PUBLICATION_TOKENS)
    has_work = any(token in q for token in WORK_TOKENS)
    has_outlet = any(token in q for token in OUTLET_TOKENS)
    has_gain = any(token in q for token in GAIN_TOKENS)

    if not has_publication:
        return None
    if not (has_work or has_outlet):
        return None

    if has_gain:
        return {
            "family": "publication_gain",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 9, 2],
            "publication_house": 9,
            "gain_house": 2,
            "quesited_house": 9,
            "doctrine": "Publication remains a 9th-house matter; when the question also asks about gain from publication, the querent's 2nd joins as the profit axis.",
        }

    if has_outlet:
        return {
            "family": "publication_submission",
            "category_override": Category.GENERAL,
            "relevant_houses": [1, 9, 2],
            "publication_house": 9,
            "gain_house": 2,
            "publisher_house": 7,
            "quesited_house": 9,
            "doctrine": "Submission or publication through a magazine, journal, or publisher still judges publication on the 9th, while the querent's benefit from acceptance can be kept secondarily in view through the 2nd.",
        }

    return {
        "family": "publication",
        "category_override": Category.GENERAL,
        "relevant_houses": [1, 9],
        "publication_house": 9,
        "quesited_house": 9,
        "doctrine": "Publishing a written work is judged primarily as a 9th-house matter rather than as the delivery of a movable good.",
    }
