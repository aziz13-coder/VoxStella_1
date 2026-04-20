from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_plain_lawsuit_routes_to_full_court_axis():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I win the case?")

    assert analysis["question_type"] == Category.LAWSUIT
    assert analysis["relevant_houses"] == [1, 7, 10, 4]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["judge_house"] == 10
    assert analysis["significators"]["outcome_house"] == 4
    assert analysis["significators"]["lawsuit_family"] == "court_adjudication"


def test_employment_legal_battle_stays_lawsuit_not_money():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question(
        "Will I win the legal battle against my ex-employer?"
    )

    assert analysis["question_type"] == Category.LAWSUIT
    assert analysis["relevant_houses"] == [1, 7, 10, 4]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["judge_house"] == 10
    assert analysis["significators"]["outcome_house"] == 4
    assert analysis["significators"]["lawsuit_family"] == "court_adjudication"


def test_inheritance_litigation_keeps_legal_axis_and_eighth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question(
        "Will I win the court battle for my inheritance rights?"
    )

    assert analysis["question_type"] == Category.LAWSUIT
    assert analysis["relevant_houses"] == [1, 7, 10, 4, 8]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["judge_house"] == 10
    assert analysis["significators"]["outcome_house"] == 4
    assert analysis["significators"]["subject_matter_house"] == 8
    assert analysis["significators"]["lawsuit_family"] == "inheritance_litigation"


def test_third_person_appeal_turns_the_court_axis():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will he win the appeal?")

    assert analysis["question_type"] == Category.LAWSUIT
    assert analysis["relevant_houses"] == [7, 1, 4, 10]
    assert analysis["significators"]["querent_house"] == 7
    assert analysis["significators"]["quesited_house"] == 1
    assert analysis["significators"]["judge_house"] == 4
    assert analysis["significators"]["outcome_house"] == 10
