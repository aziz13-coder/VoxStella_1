from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_roommate_whereabouts_treats_roommate_as_person_not_lost_object():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Where is my roommate?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 7]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["roommate_family"] == "roommate_whereabouts"
    assert analysis["significators"]["roommate_house"] == 7
    assert analysis.get("lost_object_analysis") is None


def test_roommate_doctrine_question_surfaces_seventh_house_person_axis():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("What house for a roommate?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 7]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["roommate_family"] == "roommate_person"
    assert analysis["significators"]["roommate_house"] == 7


def test_move_in_together_keeps_relationship_and_home_together():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Should we move in together?")

    assert analysis["question_type"] == Category.RELATIONSHIP
    assert analysis["relevant_houses"] == [1, 7, 4]
    assert analysis["question_intent"] == "QUALITY"
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["roommate_family"] == "cohabitation_decision"
    assert analysis["significators"]["partner_house"] == 7
    assert analysis["significators"]["home_house"] == 4
