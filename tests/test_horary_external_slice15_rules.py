from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_operation_question_uses_shared_medical_procedure_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will the operation go smoothly?")

    assert analysis["question_type"] == Category.HEALTH
    assert analysis["relevant_houses"] == [1, 6, 7, 8]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis["significators"]["doctor_house"] == 7
    assert analysis["significators"]["procedure_house"] == 8
    assert analysis["significators"]["surgery_family"] == "medical_procedure"


def test_big_surgery_question_no_longer_falls_to_generic_occurrence():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Big surgery, yes or no?")

    assert analysis["question_type"] == Category.HEALTH
    assert analysis["relevant_houses"] == [1, 6, 7, 8]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis["significators"]["surgery_family"] == "medical_procedure"


def test_cosmetic_surgery_keeps_appearance_and_cost_in_view():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I go for the full face lift?")

    assert analysis["question_type"] == Category.GENERAL
    assert analysis["relevant_houses"] == [1, 2]
    assert analysis["significators"]["quesited_house"] == 1
    assert analysis["significators"]["cost_house"] == 2
    assert analysis["significators"]["surgery_family"] == "cosmetic_procedure"


def test_turned_relative_surgery_turns_patient_doctor_and_procedure():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my husband have surgery this year?")

    assert analysis["question_type"] == Category.HEALTH
    assert analysis["relevant_houses"] == [7, 12, 1, 2]
    assert analysis["significators"]["subject_house"] == 7
    assert analysis["significators"]["illness_house"] == 12
    assert analysis["significators"]["doctor_house"] == 1
    assert analysis["significators"]["procedure_house"] == 2
    assert analysis["significators"]["quesited_house"] == 2
    assert analysis["significators"]["surgery_family"] == "medical_procedure"
