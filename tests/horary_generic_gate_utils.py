from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from tests.horary_book_examples_utils import load_book_replay_corpus, replay_book_case
from tests.horary_external_cunning_man_utils import (
    load_external_replay_corpus,
    replay_external_case,
)
from tests.horary_hard_test_utils import load_hard_test_corpus, replay_hard_test_case


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
GENERIC_GATE_CORPUS_PATH = FIXTURE_ROOT / "horary_generic_gate_corpus.json"


def load_generic_gate_corpus() -> List[Dict[str, Any]]:
    return json.loads(GENERIC_GATE_CORPUS_PATH.read_text(encoding="utf-8"))


def replay_generic_gate_case(case: Dict[str, Any], monkeypatch=None) -> Dict[str, Any]:
    source = case["source"]
    source_ref = case["source_ref"]

    if source == "hard_corpus":
        corpus = {item["id"]: item for item in load_hard_test_corpus()}
        return replay_hard_test_case(corpus[source_ref], monkeypatch=monkeypatch)

    if source == "book_replay":
        corpus = {item["id"]: item for item in load_book_replay_corpus()}
        return replay_book_case(corpus[source_ref])

    if source == "external_cunning_man":
        corpus = {item["id"]: item for item in load_external_replay_corpus()}
        return replay_external_case(corpus[source_ref])

    raise ValueError(f"Unsupported source: {source}")
