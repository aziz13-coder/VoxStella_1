from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.aggregator import aggregate
from backend.horary_engine.polarity_weights import TestimonyKey
from backend.horary_engine.polarity import Polarity

POS = TestimonyKey.MOON_APPLYING_TRINE_EXAMINER_SUN
NEG = TestimonyKey.MOON_APPLYING_SQUARE_EXAMINER_SUN


def test_polars_and_monotonicity():
    score_pos, ledger_pos = aggregate([POS])
    assert score_pos > 0
    entry_pos = ledger_pos[0]
    assert entry_pos["key"] is POS
    assert entry_pos["polarity"] is Polarity.POSITIVE
    assert entry_pos["delta_yes"] > 0 and entry_pos["delta_no"] == 0
    # Duplicate contributions do not increase score
    score_dup, _ = aggregate([POS, POS])
    assert score_dup == score_pos

    score_both, _ = aggregate([POS, NEG])
    assert score_both < score_pos

    score_neg, ledger_neg = aggregate([NEG])
    assert score_neg < 0
    entry_neg = ledger_neg[0]
    assert entry_neg["key"] is NEG
    assert entry_neg["polarity"] is Polarity.NEGATIVE
    assert entry_neg["delta_no"] > 0 and entry_neg["delta_yes"] == 0
