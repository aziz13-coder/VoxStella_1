from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.aggregator import aggregate
from backend.horary_engine.polarity_weights import TestimonyKey


def test_perfection_family_single_contribution():
    tokens = [
        TestimonyKey.PERFECTION_DIRECT,
        TestimonyKey.PERFECTION_TRANSLATION_OF_LIGHT,
    ]
    score, ledger = aggregate(tokens)
    assert score == 1.0
    entry_direct = next(l for l in ledger if l["key"] is TestimonyKey.PERFECTION_DIRECT)
    entry_tol = next(l for l in ledger if l["key"] is TestimonyKey.PERFECTION_TRANSLATION_OF_LIGHT)
    assert entry_direct["family"] == "perfection"
    assert entry_direct["kind"] == "direct"
    assert entry_direct["context"] is False
    assert entry_direct["delta_yes"] == 1.0
    assert entry_tol["family"] == "perfection"
    assert entry_tol["kind"] == "tol"
    assert entry_tol["context"] is True
    assert entry_tol["delta_yes"] == 0.0
