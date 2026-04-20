from __future__ import annotations

import sys
from pathlib import Path


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


def _projection_labels(items):
    return [entry.get("label", "") for entry in items or []]


def _replay_case(case_id: str):
    corpus = {case["id"]: case for case in load_book_replay_corpus()}
    return replay_book_case(corpus[case_id])["raw"]["lost_object_location"]


def test_scarf_replay_projects_friend_location():
    projection = _replay_case("where_is_my_scarf")

    primary_labels = _projection_labels(projection["primary_places"])

    assert projection["applies"] is True
    assert any("friend" in label.lower() for label in primary_labels)
    assert projection["confidence_label"] in {"moderate", "high"}


def test_atm_card_replay_surfaces_high_place_and_clothing_clues():
    projection = _replay_case("where_is_my_atm_card")

    trait_labels = _projection_labels(projection["environment_traits"])
    secondary_labels = _projection_labels(projection["secondary_places"])

    assert any("high up" in label.lower() for label in trait_labels)
    assert any("clothes" in label.lower() or "pockets" in label.lower() for label in secondary_labels)


def test_passport_replay_now_exposes_location_projection():
    projection = _replay_case("wheres_my_passport")

    primary_labels = _projection_labels(projection["primary_places"])
    trait_labels = _projection_labels(projection["environment_traits"])

    assert projection["applies"] is True
    assert any("workplace" in label.lower() or "formal room" in label.lower() for label in primary_labels)
    assert any("door" in label.lower() or "threshold" in label.lower() for label in trait_labels)
    assert any("floor" in label.lower() for label in trait_labels)


def test_passport_style_projection_prioritizes_workplace_door_and_floor():
    projection = build_lost_object_location_projection(
        {
            "object_name": "Mercury",
            "object_type": "document",
            "object_house": 9,
            "object_effective_house": 10,
            "object_sign": "Taurus",
            "object_sign_element": "Earth",
            "object_sign_modality": "Fixed",
            "object_sign_direction": "South by East",
            "dispositor_name": "Venus",
            "dispositor_house": 1,
        }
    )

    primary_labels = _projection_labels(projection["primary_places"])
    trait_labels = _projection_labels(projection["environment_traits"])
    direction_labels = _projection_labels(projection["directional_cues"])

    assert any("workplace" in label.lower() or "home office" in label.lower() for label in primary_labels)
    assert any("door" in label.lower() or "threshold" in label.lower() for label in trait_labels)
    assert any("floor" in label.lower() for label in trait_labels)
    assert "South by East" in direction_labels


def test_notebook_style_projection_uses_partner_and_basement_refinement():
    projection = build_lost_object_location_projection(
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
        }
    )

    primary_labels = _projection_labels(projection["primary_places"])
    secondary_labels = _projection_labels(projection["secondary_places"])

    assert any("partner" in label.lower() or "another person" in label.lower() for label in primary_labels)
    assert any("basement" in label.lower() or "lowest part" in label.lower() for label in secondary_labels)


def test_pendant_style_projection_adds_water_and_container_clues():
    projection = build_lost_object_location_projection(
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
        }
    )

    primary_labels = _projection_labels(projection["primary_places"])
    trait_labels = _projection_labels(projection["environment_traits"])

    assert any("bedroom" in label.lower() or "partner" in label.lower() for label in primary_labels)
    assert any("water" in label.lower() or "bathroom" in label.lower() for label in trait_labels)
    assert any("bag" in label.lower() or "box" in label.lower() or "container" in label.lower() for label in trait_labels)
