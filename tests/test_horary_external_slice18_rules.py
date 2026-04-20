from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_house_inheritance_keeps_property_and_estate_axes_together():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get the house inheritance?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 4, 8]
    assert analysis["significators"]["quesited_house"] == 4
    assert analysis["significators"]["property_house"] == 4
    assert analysis["significators"]["estate_house"] == 8
    assert analysis["significators"]["inheritance_family"] == "estate_property_inheritance"


def test_turned_person_inheritance_stays_on_subject_and_turned_eighth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my mother receive her inheritance?")

    assert analysis["question_type"] == Category.DEATH
    assert analysis["relevant_houses"] == [10, 5]
    assert analysis["significators"]["subject_house"] == 10
    assert analysis["significators"]["estate_house"] == 5
    assert analysis["significators"]["quesited_house"] == 5
    assert analysis["significators"]["inheritance_family"] == "inheritance_transfer"


def test_turned_person_house_inheritance_turns_property_and_estate():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my mother inherit the house?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [10, 1, 5]
    assert analysis["significators"]["subject_house"] == 10
    assert analysis["significators"]["property_house"] == 1
    assert analysis["significators"]["estate_house"] == 5
    assert analysis["significators"]["quesited_house"] == 1
    assert analysis["significators"]["inheritance_family"] == "estate_property_inheritance"


def test_inheritance_litigation_stays_on_lawsuit_doctrine():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I win the court battle for my inheritance rights?")

    assert analysis["question_type"] == Category.LAWSUIT
    assert analysis["relevant_houses"] == [1, 7, 10, 4, 8]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["subject_matter_house"] == 8
    assert analysis["significators"]["lawsuit_family"] == "inheritance_litigation"
