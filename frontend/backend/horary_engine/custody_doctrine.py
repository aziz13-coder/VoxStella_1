from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


def analyze_custody_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify custody and family-court questions into reusable families."""

    q = (question or "").lower().strip()
    if not q:
        return None

    child_tokens = ("child", "children", "kid", "kids", "son", "daughter", "baby")
    custody_tokens = (
        "custody",
        "visitation",
        "access to",
        "parenting time",
        "take the children",
        "taking the children",
        "take my child",
        "take my children",
        "take the child",
    )
    court_tokens = (
        "court",
        "judge",
        "lawyer",
        "hearing",
        "legal",
        "case",
        "papers",
        "law suit",
        "lawsuit",
    )
    contest_tokens = (
        "win back",
        "win custody",
        "lose custody",
        "regain custody",
        "succeed in taking",
        "lessen the time",
        "take the children",
        "taking the children",
    )

    has_child = any(token in q for token in child_tokens)
    has_custody_theme = any(token in q for token in custody_tokens) or (
        has_child and any(token in q for token in contest_tokens)
    )
    if not has_custody_theme:
        return None

    pronoun_subject = bool(
        re.match(r"^\s*(will|would|can|could|did|does|has|have|is|are|should)\s+(he|she|they)\b", q)
    )
    explicit_relative_subject = bool(
        re.search(r"\bmy\s+(husband|wife|spouse|partner|ex husband|ex wife|ex-wife|ex-wife|boyfriend|girlfriend)\b", q)
    )

    if explicit_relative_subject and third_person_analysis and third_person_analysis.get("subject_house"):
        subject_house = int(third_person_analysis["subject_house"])
        child_house = _turn(subject_house, 5)
        return {
            "family": "turned_child_custody",
            "category_override": Category.CHILDREN,
            "relevant_houses": [subject_house, child_house],
            "subject_house": subject_house,
            "child_house": child_house,
            "quesited_house": child_house,
            "doctrine": "When the question is about a spouse or relative getting custody of their own child, the relative is the operative subject and the child is judged from the turned 5th.",
        }

    legalized_dispute = pronoun_subject or any(token in q for token in court_tokens) or any(
        token in q for token in contest_tokens
    )
    if legalized_dispute:
        relevant_houses = [1]
        opponent_house = 7
        child_house = 5
        judge_house = 10
        outcome_house = 4
        if opponent_house not in relevant_houses:
            relevant_houses.append(opponent_house)
        if child_house not in relevant_houses:
            relevant_houses.append(child_house)
        if judge_house not in relevant_houses:
            relevant_houses.append(judge_house)
        if outcome_house not in relevant_houses:
            relevant_houses.append(outcome_house)
        return {
            "family": "family_court_custody_dispute",
            "category_override": Category.LAWSUIT,
            "relevant_houses": relevant_houses,
            "querent_house": 1,
            "opponent_house": opponent_house,
            "child_house": child_house,
            "judge_house": judge_house,
            "outcome_house": outcome_house,
            "quesited_house": opponent_house if pronoun_subject else child_house,
            "doctrine": "Custody disputes keep the child, opposing parent, judge, and final family-court disposition together rather than treating custody as a simple children-only question.",
        }

    return {
        "family": "self_child_custody",
        "category_override": Category.CHILDREN,
        "relevant_houses": [1, 5],
        "subject_house": 1,
        "child_house": 5,
        "quesited_house": 5,
        "doctrine": "Simple custody questions about one's own child keep the querent and child as the first-pass axis.",
    }
