from __future__ import annotations

import math

import pytest

from tests.horary_external_cunning_man_utils import (
    build_external_case_payload,
    load_external_replay_corpus,
    replay_external_case,
)


CORPUS = load_external_replay_corpus()


def _longitude_delta(actual: float, expected: float) -> float:
    return abs((actual - expected + 180.0) % 360.0 - 180.0)


def test_external_replay_corpus_has_source_aligned_and_manual_review_cases():
    assert len(CORPUS) >= 3
    assert any(case["source_alignment"] for case in CORPUS)
    assert all(isinstance(case["source_alignment"], bool) for case in CORPUS)


@pytest.mark.parametrize("case", CORPUS, ids=[case["id"] for case in CORPUS])
def test_external_replay_payload_matches_published_positions(case):
    payload = build_external_case_payload(case)
    planets = payload["chart_data"]["planets"]

    for check in case.get("published_checks", []):
        planet_data = planets[check["planet"]]
        if "longitude" in check:
            tolerance = float(check.get("tolerance_degrees", 0.2))
            assert _longitude_delta(float(planet_data["longitude"]), float(check["longitude"])) <= tolerance
        if "house" in check:
            assert int(planet_data["house"]) == int(check["house"])
        if "sign" in check:
            assert planet_data["sign"] == check["sign"]


@pytest.mark.parametrize("case", CORPUS, ids=[case["id"] for case in CORPUS])
def test_external_replay_cases_run_through_serialized_backend_path(case):
    replayed = replay_external_case(case)

    assert replayed["category"] == case["engine_expected_category"]
    assert replayed["perfection_type"] == case["engine_expected_perfection_type"]

    rules = replayed["reasoning"]
    for snippet in case.get("expected_reasoning_contains", []):
        assert any(snippet in rule for rule in rules), (
            f"Expected reasoning snippet not found for {case['id']}: {snippet}"
        )

    if case["source_alignment"]:
        assert replayed["verdict"] == case["article_expected_verdict"]
        assert replayed["verdict"] == case["engine_expected_verdict"]
    else:
        assert case["article_expected_verdict"] != case["engine_expected_verdict"]
        assert replayed["verdict"] == case["engine_expected_verdict"]
