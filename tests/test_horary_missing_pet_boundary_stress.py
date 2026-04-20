from __future__ import annotations

import sys
from pathlib import Path

import pytest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


@pytest.mark.parametrize(
    ("question", "expected_category", "expected_houses", "expected_family_key", "expected_family"),
    [
        (
            "Will my dog come home?",
            Category.PET,
            [1, 6],
            "pet_analysis",
            "missing",
        ),
        (
            "Where is my cat?",
            Category.PET,
            [1, 6],
            "pet_analysis",
            "missing",
        ),
        (
            "Will my dog get better?",
            Category.PET,
            [1, 6],
            "pet_analysis",
            "recovery",
        ),
        (
            "Where is my passport?",
            Category.LOST_OBJECT,
            [1, 2],
            "lost_object_analysis",
            "discovery_timing",
        ),
        (
            "Will my boyfriend come home?",
            Category.RELATIONSHIP,
            [7, 1],
            "relationship_analysis",
            "outcome",
        ),
    ],
)
def test_missing_pet_boundary_questions_route_to_the_correct_doctrine(
    question: str,
    expected_category: Category,
    expected_houses: list[int],
    expected_family_key: str,
    expected_family: str,
):
    analyzer = TraditionalHoraryQuestionAnalyzer()

    analysis = analyzer.analyze_question(question)

    assert analysis["question_type"] == expected_category
    assert analysis["relevant_houses"] == expected_houses
    assert (analysis.get(expected_family_key) or {}).get("family") == expected_family


def test_theft_return_question_keeps_the_theft_overlay_instead_of_pet_or_relationship_logic():
    analyzer = TraditionalHoraryQuestionAnalyzer()

    analysis = analyzer.analyze_question("Will the thief come back?")

    assert analysis["question_type"] == Category.LOST_OBJECT
    assert analysis["relevant_houses"] == [1, 2, 7]
    assert analysis["pet_analysis"] is None
    assert analysis["relationship_analysis"] is None
    assert analysis["lost_object_analysis"] is None
    assert (analysis.get("theft_analysis") or {}).get("family") == "stolen_object"
    assert analysis["significators"]["thief_house"] == 7
    assert analysis["significators"]["object_house"] == 2
