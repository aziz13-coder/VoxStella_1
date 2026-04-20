from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_buy_house_keeps_property_and_counterparty_axes():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will we buy a new house?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 4, 7]
    assert analysis["significators"]["quesited_house"] == 4
    assert analysis["significators"]["property_house"] == 4
    assert analysis["significators"]["counterparty_house"] == 7
    assert analysis["significators"]["property_family"] == "acquisition"


def test_purchase_apartment_generalizes_the_same_property_transition_route():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will we purchase the apartment?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 4, 7]
    assert analysis["significators"]["quesited_house"] == 4
    assert analysis["significators"]["counterparty_house"] == 7
    assert analysis["significators"]["property_family"] == "acquisition"


def test_sell_house_keeps_property_and_buyer_axes():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will we sell our home?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 4, 7]
    assert analysis["significators"]["quesited_house"] == 4
    assert analysis["significators"]["counterparty_house"] == 7
    assert analysis["significators"]["property_family"] == "sale"


def test_property_advisability_keeps_fourth_seventh_and_tenth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Should we buy the house?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 4, 7, 10]
    assert analysis["significators"]["quesited_house"] == 4
    assert analysis["significators"]["property_house"] == 4
    assert analysis["significators"]["counterparty_house"] == 7
    assert analysis["significators"]["profit_house"] == 10
    assert analysis["significators"]["property_family"] == "advisability_profit"
