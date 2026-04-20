from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_foreign_state_referendum_routes_to_first_and_ninth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question(
        "Will the Scottish Government hold another independence referendum in 2022?"
    )

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 9]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["state_family"] == "foreign_state_constitutional_action"


def test_public_office_confidence_question_stays_on_office_axis():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question(
        "Will Boris Johnson survive the vote of no confidence?"
    )

    assert analysis["question_type"] == Category.CAREER
    assert analysis["relevant_houses"] == [10, 7]
    assert analysis["significators"]["querent_house"] == 10
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["competition_family"] == "contest_public_office_confidence"


def test_foreign_state_military_question_routes_to_ninth_and_turned_third():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will Russia invade Ukraine, and when?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [9, 11]
    assert analysis["significators"]["querent_house"] == 9
    assert analysis["significators"]["quesited_house"] == 11
    assert analysis["significators"]["state_family"] == "foreign_state_military_action"


def test_medicine_question_routes_to_treatment_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Is my thyroid medicine helping or harming me?")

    assert analysis["question_type"] == Category.HEALTH
    assert analysis["health_analysis"]["family"] == "treatment"
    assert analysis["relevant_houses"] == [1, 6, 7, 10]
    assert analysis["significators"]["doctor_house"] == 7
    assert analysis["significators"]["treatment_house"] == 10
    assert analysis["significators"]["quesited_house"] == 10
