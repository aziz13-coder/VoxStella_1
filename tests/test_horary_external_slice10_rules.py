from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_friend_repayment_keeps_friend_and_money_axes():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get back my money from my friend?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 11, 2]
    assert analysis["significators"]["quesited_house"] == 2
    assert analysis["significators"]["counterparty_house"] == 11
    assert analysis["significators"]["counterparty_money_house"] == 12
    assert analysis["significators"]["economic_family"] == "friend_repayment"


def test_college_refund_turns_to_institution_and_its_money():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get a refund from the college?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 9, 10]
    assert analysis["significators"]["quesited_house"] == 10
    assert analysis["significators"]["counterparty_house"] == 9
    assert analysis["significators"]["counterparty_money_house"] == 10
    assert analysis["significators"]["economic_family"] == "institutional_refund"


def test_tax_refund_turns_to_government_and_its_money():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("When will I receive my tax refund?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 10, 11]
    assert analysis["significators"]["quesited_house"] == 11
    assert analysis["significators"]["counterparty_house"] == 10
    assert analysis["significators"]["counterparty_money_house"] == 11
    assert analysis["significators"]["economic_family"] == "government_refund"


def test_insurance_refund_uses_counterparty_axis():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my insurance claim be solved favorably?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 7, 8]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis["significators"]["counterparty_house"] == 7
    assert analysis["significators"]["counterparty_money_house"] == 8
    assert analysis["significators"]["economic_family"] == "counterparty_refund"
