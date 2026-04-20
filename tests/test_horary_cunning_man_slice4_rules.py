from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_religious_festival_weather_routes_to_ninth_house_event():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("What will the weather be for Lughnasadh?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [9]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["event_family"] == "event_weather_religious"


def test_other_religious_festival_weather_questions_use_same_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will the weather be good for Easter?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [9]
    assert analysis["significators"]["event_house"] == 9
    assert analysis["significators"]["event_family"] == "event_weather_religious"


def test_secular_celebration_weather_routes_to_fifth_house_event():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("What will the weather be for the garden party?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [5]
    assert analysis["significators"]["quesited_house"] == 5
    assert analysis["significators"]["event_family"] == "event_weather_celebration"


def test_other_secular_celebration_weather_questions_use_same_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will the weather be good for the birthday party?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [5]
    assert analysis["significators"]["event_house"] == 5
    assert analysis["significators"]["event_family"] == "event_weather_celebration"


def test_medical_result_contact_question_routes_as_health_not_education():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("When will my COVID test result arrive?")

    assert analysis["question_type"] == Category.HEALTH
    assert analysis["health_analysis"]["family"] == "result_contact"
    assert analysis["relevant_houses"] == [1, 7]
    assert analysis["significators"]["doctor_house"] == 7
    assert analysis["significators"]["quesited_house"] == 7


def test_other_medical_result_questions_use_same_contact_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("When will my biopsy results come back?")

    assert analysis["question_type"] == Category.HEALTH
    assert analysis["health_analysis"]["family"] == "result_contact"
    assert analysis["relevant_houses"] == [1, 7]
    assert analysis["significators"]["quesited_house"] == 7
