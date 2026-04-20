from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_arrest_question_keeps_authority_visible():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I be arrested?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 10]
    assert analysis["significators"]["quesited_house"] == 10
    assert analysis["significators"]["authority_house"] == 10
    assert analysis["significators"]["confinement_family"] == "arrest_authority"


def test_imprisonment_question_uses_twelfth_house_confinement():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will i be imprisoned?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 12]
    assert analysis["third_person_analysis"] == {"is_third_person": False}
    assert analysis["significators"]["quesited_house"] == 12
    assert analysis["significators"]["confinement_house"] == 12
    assert analysis["significators"]["confinement_family"] == "confinement"


def test_spouse_release_question_keeps_spouse_and_prison_together():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my husband get out of prison sooner?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 7, 12]
    assert analysis["significators"]["subject_house"] == 7
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["confinement_house"] == 12
    assert analysis["significators"]["confinement_family"] == "confinement_release"
