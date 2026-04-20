from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402


def test_bank_loan_question_is_occurrence_not_reunion():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my bank loan be approved?")

    assert analysis["question_intent"] == "OCCURRENCE"


def test_property_sale_question_is_occurrence_not_reunion():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will we sell the house soon?")

    assert analysis["question_intent"] == "OCCURRENCE"


def test_property_advisability_question_is_quality():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Should I buy this house?")

    assert analysis["question_intent"] == "QUALITY"


def test_person_welfare_question_is_safety():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Where is my Dad? Is he ok?")

    assert analysis["question_intent"] == "SAFETY"


def test_treatment_help_or_harm_question_is_safety():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Is my thyroid medicine helping or harming me?")

    assert analysis["question_intent"] == "SAFETY"


def test_book_publication_question_is_occurrence_not_safety():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I publish my book?")

    assert analysis["question_intent"] == "OCCURRENCE"
