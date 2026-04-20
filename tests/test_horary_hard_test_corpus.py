from __future__ import annotations

import pytest

from tests.horary_hard_test_utils import load_hard_test_corpus, replay_hard_test_case


CORPUS = load_hard_test_corpus()


def test_hard_test_corpus_contains_at_least_ten_cases_with_mixed_levels():
    assert len(CORPUS) >= 10
    levels = {case["level"] for case in CORPUS}
    assert "deterministic" in levels
    assert "manual_review" in levels


@pytest.mark.parametrize("case", CORPUS, ids=[case["id"] for case in CORPUS])
def test_horary_hard_test_corpus_replays_expected_backend_result(case, monkeypatch):
    replayed = replay_hard_test_case(case, monkeypatch=monkeypatch)

    assert replayed["verdict"] == case["expected_verdict"]
    assert replayed["category"] == case["expected_category"]
    assert replayed["perfection_type"] == case["expected_perfection_type"]

    rules = replayed["reasoning"]
    for snippet in case.get("expected_reasoning_contains", []):
        assert any(snippet in rule for rule in rules), (
            f"Expected reasoning snippet not found for {case['id']}: {snippet}"
        )
