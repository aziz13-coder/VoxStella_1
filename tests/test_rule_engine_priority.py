from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.rule_engine import evaluate_rules


def test_first_hit_wins_within_tier():
    result = evaluate_rules(["V2", "V1", "M2", "M1"])
    assert result == ["V1", "M1"]


def test_tier_priority_order():
    candidates = ["M2", "P1", "V2", "MOD1", "H2", "T2", "S1"]
    result = evaluate_rules(candidates)
    assert result == ["V2", "H2", "P1", "S1", "M2", "MOD1", "T2"]
