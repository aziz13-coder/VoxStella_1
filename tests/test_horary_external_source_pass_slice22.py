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
    / "horary_external_source_pass_slice22.json"
)


def _load_cases():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_slice22_contains_three_tenancy_and_eviction_cases():
    cases = _load_cases()
    assert len(cases) == 3


def test_slice22_is_fully_aligned_after_tenancy_doctrine_pass():
    cases = _load_cases()
    aligned_ids = {case["id"] for case in cases if case["source_alignment"]}

    assert aligned_ids == {
        "evicted_lose_home_astrologyweekly_source_pass",
        "tenant_move_out_astrologyweekly_source_pass",
        "illegal_tenant_leave_property_astrologyweekly_source_pass",
    }


def test_slice22_engine_observations_match_current_analyzer_behavior():
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
