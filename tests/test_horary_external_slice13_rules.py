from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_plain_visa_question_routes_on_ninth_house_authorization():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get the visa?")

    assert analysis["question_type"] == Category.TRAVEL
    assert analysis["relevant_houses"] == [1, 9]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["authorization_house"] == 9
    assert analysis["significators"]["immigration_family"] == "visa_authorization"


def test_travel_application_approval_keeps_authority_in_tenth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my travel application be approved?")

    assert analysis["question_type"] == Category.TRAVEL
    assert analysis["relevant_houses"] == [1, 9, 10]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["authorization_house"] == 9
    assert analysis["significators"]["authority_house"] == 10
    assert analysis["significators"]["immigration_family"] == "visa_application_approval"


def test_work_visa_question_keeps_visa_and_work_axes_together():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get visa for work?")

    assert analysis["question_type"] == Category.TRAVEL
    assert analysis["relevant_houses"] == [1, 9, 10]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["authorization_house"] == 9
    assert analysis["significators"]["authority_house"] == 10
    assert analysis["significators"]["work_house"] == 10
    assert analysis["significators"]["immigration_family"] == "work_visa_authorization"
