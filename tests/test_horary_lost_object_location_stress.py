from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402
from tests.horary_book_examples_utils import (  # noqa: E402
    load_book_replay_corpus,
    replay_book_case,
)


CORPUS = load_book_replay_corpus()
RELEVANT_IDS = {
    "where_is_my_atm_card",
    "where_is_my_scarf",
    "wheres_my_passport",
}
RELEVANT_CASES = [case for case in CORPUS if case["id"] in RELEVANT_IDS]


def _labels(items):
    return [item.get("label", "") for item in items or []]


def test_relevant_lost_object_replays_all_emit_structured_location_payloads():
    assert {case["id"] for case in RELEVANT_CASES} == RELEVANT_IDS

    for case in RELEVANT_CASES:
        replayed = replay_book_case(case)
        raw = replayed["raw"]
        projection = raw.get("lost_object_location")

        assert projection is not None, case["id"]
        assert projection.get("applies") is True, case["id"]
        assert projection.get("summary"), case["id"]
        assert projection.get("confidence", 0) >= 60, case["id"]
        assert projection.get("primary_places"), case["id"]
        assert projection.get("environment_traits"), case["id"]
        assert projection.get("evidence"), case["id"]


def test_location_projection_matrix_matches_expected_book_style_clues():
    expected_clues = {
        "where_is_my_atm_card": ("high up", "clothes"),
        "where_is_my_scarf": ("friend", "floor"),
        "wheres_my_passport": ("workplace", "door"),
    }

    for case in RELEVANT_CASES:
        replayed = replay_book_case(case)
        projection = replayed["raw"]["lost_object_location"]
        haystack = " | ".join(
            _labels(projection.get("primary_places"))
            + _labels(projection.get("secondary_places"))
            + _labels(projection.get("environment_traits"))
        ).lower()
        expected_a, expected_b = expected_clues[case["id"]]
        assert expected_a in haystack, f"{case['id']} missing clue: {expected_a}"
        assert expected_b in haystack, f"{case['id']} missing clue: {expected_b}"


def test_lost_passport_phrase_variants_all_route_through_lost_object_bridge():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    phrases = [
        "Where's my passport?",
        "Where is my passport?",
        "My passport is missing. Where is it?",
        "I lost my passport, where can I find it?",
        "I misplaced my passport.",
        "Was my passport stolen?",
    ]

    for phrase in phrases:
        analysis = analyzer.analyze_question(phrase)
        sigs = analysis["significators"]
        assert analysis["question_type"] == Category.LOST_OBJECT, phrase
        if "stolen" in phrase.lower():
            assert analysis["relevant_houses"] == [1, 2, 7], phrase
        else:
            assert analysis["relevant_houses"] == [1, 2], phrase
        assert sigs["quesited_house"] == 2, phrase
        assert sigs["passport_family"] == "passport_lost_document", phrase
        assert sigs["document_house"] == 2, phrase
        assert sigs["lost_object_family"] in {"discovery", "discovery_timing"}, phrase


def test_passport_non_loss_questions_keep_original_passport_doctrine():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    cases = [
        (
            "Will the passports be here on time?",
            Category.GENERAL,
            "passport_document_arrival",
            3,
        ),
        (
            "Will I get the passports in 3days?",
            Category.GENERAL,
            "passport_document_arrival",
            3,
        ),
        (
            "Will my Passport Renewal be Approved?",
            Category.TRAVEL,
            "passport_authorization",
            9,
        ),
    ]

    for phrase, expected_category, expected_family, expected_house in cases:
        analysis = analyzer.analyze_question(phrase)
        sigs = analysis["significators"]
        assert analysis["question_type"] == expected_category, phrase
        assert sigs["passport_family"] == expected_family, phrase
        assert sigs["quesited_house"] == expected_house, phrase
