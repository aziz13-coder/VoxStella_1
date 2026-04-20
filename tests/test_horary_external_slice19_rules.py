from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_masters_scholarship_keeps_higher_study_primary_and_eligibility_secondary():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I be accepted for masters scholarship?")

    assert analysis["question_type"] == Category.EDUCATION
    assert analysis["relevant_houses"] == [1, 9, 2]
    assert analysis["significators"]["quesited_house"] == 9
    assert analysis["significators"]["aid_family"] == "education_scholarship_support"
    assert analysis["significators"]["education_house"] == 9
    assert analysis["significators"]["support_house"] == 2
    assert analysis["significators"]["eligibility_house"] == 2


def test_relative_scholarship_turns_from_brother_to_turned_ninth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my brother be granted a scholarship?")

    assert analysis["question_type"] == Category.EDUCATION
    assert analysis["relevant_houses"] == [3, 11]
    assert analysis["significators"]["quesited_house"] == 11
    assert analysis["significators"]["aid_family"] == "turned_scholarship_support"
    assert analysis["significators"]["subject_house"] == 3
    assert analysis["significators"]["education_house"] == 11
    assert analysis["significators"]["scholarship_house"] == 11


def test_public_financial_aid_keeps_official_support_axis_visible():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get the financial aid?")

    assert analysis["question_type"] == Category.FUNDING
    assert analysis["relevant_houses"] == [1, 10]
    assert analysis["significators"]["quesited_house"] == 10
    assert analysis["significators"]["aid_family"] == "public_financial_aid"
    assert analysis["significators"]["authority_house"] == 10
    assert analysis["significators"]["support_house"] == 10
