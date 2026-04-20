from backend.horary_engine.polarity import Polarity, polarity_sign
from backend.horary_engine.rationale import build_rationale


def test_polarity_sign_and_rationale_neutral():
    assert polarity_sign(Polarity.NEUTRAL) == "0"
    ledger = [{"key": "dummy", "polarity": Polarity.NEUTRAL, "weight": 0.0}]
    assert build_rationale(ledger) == ["dummy (0)"]
