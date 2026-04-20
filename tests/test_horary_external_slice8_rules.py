from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_sister_marriage_turns_to_ninth_house():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my sister get married this year?")

    assert analysis["question_type"] == Category.MARRIAGE
    assert analysis["relevant_houses"] == [3, 9]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["subject_house"] == 3
    assert analysis["significators"]["partner_house"] == 9
    assert analysis["significators"]["relative_family"] == "turned_marriage"


def test_daughter_relationship_uses_fifth_and_turned_seventh():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my daughter be happy with her boyfriend?")

    assert analysis["question_type"] == Category.RELATIONSHIP
    assert analysis["relevant_houses"] == [5, 11]
    assert analysis["significators"]["quesited_house"] == 11
    assert analysis["significators"]["subject_house"] == 5
    assert analysis["significators"]["partner_house"] == 11
    assert analysis["significators"]["relative_family"] == "turned_relationship"


def test_relative_whereabouts_welfare_is_not_lost_object():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Where is my Dad? Is he ok?")

    assert analysis["question_type"] == Category.HEALTH
    assert analysis["relevant_houses"] == [4, 9]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["subject_house"] == 4
    assert analysis["significators"]["welfare_house"] == 9
    assert analysis["significators"]["relative_family"] == "person_whereabouts_welfare"


def test_friend_whereabouts_is_person_not_possession():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Where is my friend? Is she okay?")

    assert analysis["question_type"] == Category.HEALTH
    assert analysis["relevant_houses"] == [11, 4]
    assert analysis["significators"]["subject_house"] == 11
    assert analysis["significators"]["welfare_house"] == 4
    assert analysis["significators"]["relative_family"] == "person_whereabouts_welfare"
