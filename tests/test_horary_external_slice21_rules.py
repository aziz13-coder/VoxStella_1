from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_citizenship_question_keeps_status_and_authority_visible():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("When will I get my citizenship?")

    assert analysis["question_type"] == Category.TRAVEL
    assert analysis["relevant_houses"] == [1, 9, 10]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["immigration_family"] == "status_authorization"
    assert analysis["significators"]["subject_house"] == 1
    assert analysis["significators"]["authorization_house"] == 9
    assert analysis["significators"]["authority_house"] == 10
    assert analysis.get("communication_analysis") is None


def test_permanent_resident_question_uses_shared_status_authorization_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("When will i get permanent resident?")

    assert analysis["question_type"] == Category.TRAVEL
    assert analysis["relevant_houses"] == [1, 9, 10]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["immigration_family"] == "status_authorization"
    assert analysis["significators"]["authorization_house"] == 9
    assert analysis["significators"]["authority_house"] == 10


def test_husband_green_card_question_turns_status_and_authority_from_husband():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("When will my husband's green card be approved?")

    assert analysis["question_type"] == Category.TRAVEL
    assert analysis["relevant_houses"] == [7, 3, 4]
    assert analysis["significators"]["quesited_house"] == 3
    assert analysis["significators"]["immigration_family"] == "turned_status_authorization"
    assert analysis["significators"]["subject_house"] == 7
    assert analysis["significators"]["authorization_house"] == 3
    assert analysis["significators"]["authority_house"] == 4
