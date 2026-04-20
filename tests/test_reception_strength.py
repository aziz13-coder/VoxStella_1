from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.reception import TraditionalReceptionCalculator

def test_reception_strength_min_synergy():
    calc = TraditionalReceptionCalculator()
    # One direction exaltation (4), other term (2) -> min=2, synergy+1 => 3
    assert calc._calculate_reception_strength(["exaltation"], ["term"]) == 3

def test_reception_strength_no_synergy_when_weak():
    calc = TraditionalReceptionCalculator()
    # Term vs face -> min=1, no synergy
    assert calc._calculate_reception_strength(["term"], ["face"]) == 1
