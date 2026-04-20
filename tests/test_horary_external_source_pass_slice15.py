from __future__ import annotations

import json
from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "horary_external_source_pass_slice15.json"
)


def _load_cases():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_slice15_contains_three_surgery_and_cosmetic_procedure_cases():
    cases = _load_cases()
    assert len(cases) == 3


def test_slice15_tracks_all_cases_as_aligned_after_surgery_doctrine_pass():
    cases = _load_cases()
    assert all(case["source_alignment"] for case in cases)
    assert {case["id"] for case in cases} == {
        "full_face_lift_cosmetic_surgery_source_pass",
        "operation_go_smoothly_source_pass",
        "big_surgery_yes_no_source_pass",
    }


def test_slice15_engine_observations_match_current_analyzer_behavior():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    cases = _load_cases()

    for case in cases:
        analysis = analyzer.analyze_question(case["question"])
        observed_category = analysis["question_type"].value
        observed_houses = analysis["relevant_houses"]
        observed_quesited_house = analysis["significators"]["quesited_house"]
        observed_intent = analysis["question_intent"]

        assert observed_category == case["current_engine_category"], case["id"]
        assert observed_houses == case["current_engine_houses"], case["id"]
        assert observed_quesited_house == case["current_engine_quesited_house"], case["id"]
        assert observed_intent == case["current_engine_intent"], case["id"]


def test_slice15_doctrine_assertions_match_current_surgery_and_cosmetic_analysis():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    cases = _load_cases()

    for case in cases:
        expectations = case.get("source_expected_doctrine_assertions")
        if not expectations:
            continue

        analysis = analyzer.analyze_question(case["question"])
        family = case.get("current_engine_doctrine_family")

        if family == "medical_procedure":
            doctrine_branch = analysis["surgery_analysis"]
            assert doctrine_branch is not None, case["id"]
            assert doctrine_branch["family"] == family, case["id"]
            assert analysis["health_analysis"] is not None, case["id"]
            assert analysis["health_analysis"]["family"] == family, case["id"]
        elif family == "cosmetic_procedure":
            doctrine_branch = analysis["surgery_analysis"]
            assert doctrine_branch is not None, case["id"]
            assert doctrine_branch["family"] == family, case["id"]
        else:
            raise AssertionError(f"Unexpected doctrine family for {case['id']}: {family}")

        assert analysis["significators"]["surgery_family"] == family, case["id"]

        for house_key in (
            "subject_house",
            "illness_house",
            "doctor_house",
            "procedure_house",
            "cost_house",
            "quesited_house",
        ):
            if house_key in expectations:
                assert doctrine_branch.get(house_key) == expectations[house_key], case["id"]
                assert analysis["significators"].get(house_key) == expectations[house_key], case["id"]

        doctrine_snippet = expectations.get("doctrine_contains")
        if doctrine_snippet:
            assert doctrine_snippet in doctrine_branch.get("doctrine", ""), case["id"]

        for null_key in expectations.get("expected_null_analyses", []):
            assert analysis.get(null_key) is None, case["id"]
