from __future__ import annotations

import sys
from pathlib import Path

import pytest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.lost_object_doctrine import (  # noqa: E402
    build_lost_object_location_projection,
)
from tests.horary_book_examples_utils import (  # noqa: E402
    load_book_replay_corpus,
    replay_book_case,
)


def _projection_text(projection):
    text_parts = [projection.get("summary", "")]

    for bucket_name in (
        "primary_places",
        "secondary_places",
        "environment_traits",
        "directional_cues",
    ):
        for item in projection.get(bucket_name, []) or []:
            text_parts.append(item.get("label", ""))
            text_parts.append(item.get("reason", ""))

    for entry in projection.get("evidence", []) or []:
        text_parts.append(entry.get("clue", ""))
        text_parts.append(entry.get("rule", ""))

    return " | ".join(part for part in text_parts if part).lower()


def _assert_matches_real_answer(haystack, groups, case_label, actual_answer, source_ref):
    for description, variants in groups:
        assert any(variant in haystack for variant in variants), (
            f"{case_label} missing {description}. "
            f"Real answer: {actual_answer}. "
            f"Knowledge source: {source_ref}."
        )


def _replay_projection(case_id: str):
    corpus = {case["id"]: case for case in load_book_replay_corpus()}
    replayed = replay_book_case(corpus[case_id])
    return replayed["raw"]["lost_object_location"], replayed


REPLAY_REAL_ANSWER_CASES = [
    pytest.param(
        "where_is_my_atm_card",
        "Found in the laundry basket next to a window, in the pocket of the jeans she wore the day before.",
        "Horary Examples Traditional Horary Astrology By Example ...txt:2692-2704",
        [
            ("laundry area", ["laundry"]),
            ("clothing or pocket clue", ["clothes", "pockets", "handbags", "dressing areas"]),
            ("window or airy elevation clue", ["window", "windows", "high up"]),
        ],
        id="atm-card-replay",
    ),
    pytest.param(
        "where_is_my_scarf",
        "A friend had the scarf and the querent recovered it after phoning her.",
        "Horary Examples Traditional Horary Astrology By Example ...txt:2725-2746",
        [
            ("friend location", ["with a friend", "friend's belongings", "friend"]),
        ],
        id="scarf-replay",
    ),
    pytest.param(
        "wheres_my_passport",
        "The passport was on the floor by the door of her home office.",
        "Horary Examples Traditional Horary Astrology By Example ...txt:2802-2822",
        [
            ("home office or formal room clue", ["home office", "workplace", "formal room"]),
            ("doorway clue", ["doorway", "threshold", "door"]),
            ("floor clue", ["on or near the floor", "floor", "ground"]),
        ],
        id="passport-replay",
    ),
]


@pytest.mark.parametrize(
    "case_id,actual_answer,source_ref,expected_groups",
    REPLAY_REAL_ANSWER_CASES,
)
def test_location_clues_replay_align_with_real_recovered_locations(
    case_id,
    actual_answer,
    source_ref,
    expected_groups,
):
    projection, replayed = _replay_projection(case_id)
    haystack = _projection_text(projection)

    assert replayed["verdict"] == "YES", case_id
    assert projection["applies"] is True, case_id
    assert projection["confidence_label"] in {"moderate", "high"}, case_id

    _assert_matches_real_answer(
        haystack,
        expected_groups,
        case_id,
        actual_answer,
        source_ref,
    )


SOURCE_BACKED_LOCATION_CASES = [
    pytest.param(
        "notebook",
        {
            "object_name": "Mercury",
            "object_type": "document",
            "object_house": 7,
            "object_effective_house": 7,
            "object_sign": "Aquarius",
            "object_sign_element": "Air",
            "object_sign_modality": "Fixed",
            "object_sign_direction": "West by North",
            "dispositor_name": "Saturn",
            "dispositor_house": 4,
        },
        "The notebook was found in one of her husband's boxes, in the basement.",
        "Horary Examples Traditional Horary Astrology By Example ...txt:2865-2888",
        [
            ("partner or spouse clue", ["partner", "spouse", "another person's belongings"]),
            ("basement or lowest-place clue", ["basement", "cellar", "lowest part"]),
        ],
        id="notebook-source-backed",
    ),
    pytest.param(
        "pendant",
        {
            "object_name": "Mercury",
            "object_type": "movable",
            "object_house": 7,
            "object_effective_house": 7,
            "object_sign": "Pisces",
            "object_sign_element": "Water",
            "object_sign_modality": "Mutable",
            "object_sign_direction": "North by West",
            "dispositor_name": "Jupiter",
            "dispositor_house": 1,
        },
        "The pendant was in the bedroom, inside a small beach bag.",
        "Horary Examples Traditional Horary Astrology By Example ...txt:2908-2927",
        [
            ("bedroom clue", ["bedroom", "partner", "spouse"]),
            ("water clue", ["water", "bathroom", "kitchen", "washing"]),
            ("container clue", ["bag", "box", "drawer", "container"]),
        ],
        id="pendant-source-backed",
    ),
]


@pytest.mark.parametrize(
    "case_id,snapshot,actual_answer,source_ref,expected_groups",
    SOURCE_BACKED_LOCATION_CASES,
)
def test_location_clues_source_backed_examples_match_book_found_answers(
    case_id,
    snapshot,
    actual_answer,
    source_ref,
    expected_groups,
):
    projection = build_lost_object_location_projection(snapshot)
    haystack = _projection_text(projection)

    assert projection["applies"] is True, case_id

    _assert_matches_real_answer(
        haystack,
        expected_groups,
        case_id,
        actual_answer,
        source_ref,
    )
