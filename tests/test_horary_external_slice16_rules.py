from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_simple_book_publication_uses_ninth_house():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will i publish my book?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 9]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["publication_family"] == "publication"
    assert analysis["significators"]["publication_house"] == 9


def test_publication_submission_keeps_publication_primary_and_gain_secondary():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will i get a book review published in this online magazine?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 9, 2]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["gain_house"] == 2
    assert analysis["significators"]["publication_family"] == "publication_submission"


def test_publication_plus_profit_keeps_ninth_and_second_together():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I publish my book and have gains from it?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 9, 2]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["gain_house"] == 2
    assert analysis["significators"]["publication_family"] == "publication_gain"


def test_manuscript_acceptance_generalizes_to_publication_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my manuscript be accepted?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 9]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["publication_family"] == "publication"
