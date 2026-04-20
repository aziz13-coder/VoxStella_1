from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_self_custody_dispute_keeps_child_and_family_court_axis():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I win back custody of my kids?")

    assert analysis["question_type"] == Category.LAWSUIT
    assert analysis["relevant_houses"] == [1, 7, 5, 10, 4]
    assert analysis["significators"]["quesited_house"] == 5
    assert analysis["significators"]["child_house"] == 5
    assert analysis["significators"]["opponent_house"] == 7
    assert analysis["significators"]["judge_house"] == 10
    assert analysis["significators"]["outcome_house"] == 4
    assert analysis["significators"]["custody_family"] == "family_court_custody_dispute"


def test_turned_spouse_child_custody_uses_subject_and_turned_fifth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my husband get custody of his child?")

    assert analysis["question_type"] == Category.CHILDREN
    assert analysis["relevant_houses"] == [7, 11]
    assert analysis["significators"]["quesited_house"] == 11
    assert analysis["significators"]["subject_house"] == 7
    assert analysis["significators"]["child_house"] == 11
    assert analysis["significators"]["custody_family"] == "turned_child_custody"


def test_opponent_taking_children_keeps_opponent_child_and_judge():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will he succeed in taking the children?")

    assert analysis["question_type"] == Category.LAWSUIT
    assert analysis["relevant_houses"] == [1, 7, 5, 10, 4]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["child_house"] == 5
    assert analysis["significators"]["opponent_house"] == 7
    assert analysis["significators"]["judge_house"] == 10
    assert analysis["significators"]["outcome_house"] == 4
    assert analysis["significators"]["custody_family"] == "family_court_custody_dispute"
