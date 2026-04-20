from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_friend_contact_routes_to_eleventh_house():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I hear from my friend?")

    assert analysis["question_type"] == Category.FRIEND_ENEMY
    assert analysis["relevant_houses"] == [1, 11]
    assert analysis["significators"]["quesited_house"] == 11
    assert analysis["significators"]["communication_family"] == "friend_contact"
    assert analysis["significators"]["friend_house"] == 11


def test_message_receipt_routes_with_third_house_in_view():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Has he received my message?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 7, 3]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["communication_family"] == "message_receipt"
    assert analysis["significators"]["communication_house"] == 3


def test_friend_message_receipt_uses_eleventh_and_third():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Did my friend get my email?")

    assert analysis["question_type"] == Category.FRIEND_ENEMY
    assert analysis["relevant_houses"] == [1, 11, 3]
    assert analysis["significators"]["quesited_house"] == 11
    assert analysis["significators"]["communication_family"] == "message_receipt"
    assert analysis["significators"]["communication_house"] == 3


def test_delivery_arrival_routes_as_goods_home_courier_and_holder():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("When will my parcel arrive?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 2, 4, 6, 8]
    assert analysis["significators"]["quesited_house"] == 4
    assert analysis["significators"]["communication_family"] == "delivery_arrival"
    assert analysis["significators"]["goods_house"] == 2
    assert analysis["significators"]["home_house"] == 4
    assert analysis["significators"]["courier_house"] == 6
    assert analysis["significators"]["holder_house"] == 8
