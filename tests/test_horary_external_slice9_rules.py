from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_money_theft_keeps_second_seventh_and_eighth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Did my coworker steal the money?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 2, 7, 8]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["money_house"] == 2
    assert analysis["significators"]["thief_house"] == 7
    assert analysis["significators"]["thief_possession_house"] == 8
    assert analysis["significators"]["theft_family"] == "suspected_money_theft"


def test_stolen_wallet_keeps_object_and_thief_axes():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Was my wallet stolen?")

    assert analysis["question_type"] == Category.LOST_OBJECT
    assert analysis["relevant_houses"] == [1, 2, 7]
    assert analysis["significators"]["quesited_house"] == 2
    assert analysis["significators"]["object_house"] == 2
    assert analysis["significators"]["thief_house"] == 7
    assert analysis["significators"]["theft_family"] == "stolen_object"


def test_plain_thief_identification_stays_on_seventh():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Who is the thief?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 7]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["thief_house"] == 7
    assert analysis["significators"]["theft_family"] == "thief_identification"
