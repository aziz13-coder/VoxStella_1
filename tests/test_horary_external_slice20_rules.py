from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_specific_car_purchase_keeps_seller_and_sellers_possession_visible():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Should I buy the car?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 7, 8]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis["significators"]["vehicle_family"] == "specific_vehicle_purchase"
    assert analysis["significators"]["seller_house"] == 7
    assert analysis["significators"]["vehicle_house"] == 8
    assert analysis["significators"]["transaction_type"] is True


def test_owned_car_sale_keeps_vehicle_house_and_buyer_axis_together():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I be able to sell my car in July?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 3, 7]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["vehicle_family"] == "owned_vehicle_sale"
    assert analysis["significators"]["vehicle_house"] == 3
    assert analysis["significators"]["buyer_house"] == 7
    assert analysis["significators"]["transaction_type"] is True


def test_partner_vehicle_purchase_turns_possession_and_vehicle_from_partner():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my partner buy a new car within a month?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [7, 8, 9]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis["significators"]["vehicle_family"] == "turned_vehicle_acquisition"
    assert analysis["significators"]["subject_house"] == 7
    assert analysis["significators"]["possession_house"] == 8
    assert analysis["significators"]["vehicle_house"] == 9


def test_general_vehicle_acquisition_keeps_money_and_vehicle_together():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Should I get a car now?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 2, 3]
    assert analysis["significators"]["quesited_house"] == 3
    assert analysis["significators"]["vehicle_family"] == "general_vehicle_acquisition"
    assert analysis["significators"]["buyer_money_house"] == 2
    assert analysis["significators"]["vehicle_house"] == 3


def test_vehicle_delivery_question_stays_on_delivery_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("When will my car be delivered?")

    assert analysis["relevant_houses"] == [1, 2, 4, 6, 8]
    assert analysis.get("vehicle_analysis") is None
    assert analysis["significators"]["communication_family"] == "delivery_arrival"
