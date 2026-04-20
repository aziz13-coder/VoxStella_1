from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_passport_arrival_question_routes_as_document_not_education():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will the passports be here on time?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 3]
    assert analysis["significators"]["quesited_house"] == 3
    assert analysis["significators"]["passport_family"] == "passport_document_arrival"
    assert analysis["significators"]["document_house"] == 3
    assert analysis.get("communication_analysis") is None


def test_passport_receipt_question_keeps_documents_on_third_house():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get the passports in 3days?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 3]
    assert analysis["significators"]["quesited_house"] == 3
    assert analysis["significators"]["passport_family"] == "passport_document_arrival"
    assert analysis["significators"]["document_house"] == 3


def test_passport_renewal_approval_keeps_document_and_authority_visible():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my Passport Renewal be Approved?")

    assert analysis["question_type"] == Category.TRAVEL
    assert analysis["relevant_houses"] == [1, 9, 10]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["passport_family"] == "passport_authorization"
    assert analysis["significators"]["document_house"] == 9
    assert analysis["significators"]["authority_house"] == 10
