from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_named_bank_loan_keeps_counterparty_and_loan_axes():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my bank loan be approved?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 7, 8]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis["significators"]["counterparty_house"] == 7
    assert analysis["significators"]["counterparty_money_house"] == 8
    assert analysis["significators"]["lender_house"] == 7
    assert analysis["significators"]["loan_house"] == 8
    assert analysis["significators"]["economic_family"] == "named_lender_loan"


def test_named_mortgage_approval_does_not_collapse_into_hostile_bank_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my mortgage be approved by the bank?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 7, 8]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis["significators"]["counterparty_house"] == 7
    assert analysis["significators"]["economic_family"] == "named_lender_loan"


def test_generic_loan_without_named_lender_stays_on_eighth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get the loan I applied for?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 8]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis.get("economic_analysis") is None


def test_hostile_bank_foreclosure_stays_on_contracting_counterparty():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will the bank foreclose?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 7]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["counterparty_house"] == 7
    assert analysis["significators"]["economic_family"] == "bank_counterparty"
