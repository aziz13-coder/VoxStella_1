from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_stress_support import build_report_from_seed, category_map


def test_growth_scores_are_not_saturated_across_seeded_pairs():
    growth_scores = []
    for seed in range(24):
        report = build_report_from_seed(seed)
        growth = category_map(report).get("growth") or {}
        growth_scores.append(float(growth.get("score") or 0.0))

    assert len(set(growth_scores)) > 1
    assert any(score < 100.0 for score in growth_scores)
    assert min(growth_scores) < 80.0
