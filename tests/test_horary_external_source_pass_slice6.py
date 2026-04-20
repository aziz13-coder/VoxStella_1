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
    / "horary_external_source_pass_slice6.json"
)


def _load_cases():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_slice6_contains_three_communication_and_delivery_cases():
    cases = _load_cases()
    assert len(cases) == 3


def test_slice6_tracks_all_cases_as_aligned_after_communication_and_delivery_pass():
    cases = _load_cases()
    assert all(case["source_alignment"] for case in cases)
    assert {case["id"] for case in cases} == {
        "hear_from_friend_skyscript_source_pass",
        "received_message_skyscript_source_pass",
        "goods_arrive_home_skyscript_source_pass",
    }


def test_slice6_engine_observations_match_current_analyzer_behavior():
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
