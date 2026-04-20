import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_stress_support import (
    assert_report_invariants,
    build_report_from_seed,
    canonical_aspect_signatures,
)


@pytest.mark.parametrize("seed", range(18))
def test_swapping_charts_preserves_cross_aspect_inventory(seed):
    report_ab = build_report_from_seed(seed)
    report_ba = build_report_from_seed(seed, swap=True)

    assert_report_invariants(report_ab)
    assert_report_invariants(report_ba)
    assert canonical_aspect_signatures(report_ab) == canonical_aspect_signatures(report_ba)
    assert report_ab["summary"]["mutual_reception_count"] == report_ba["summary"]["mutual_reception_count"]


@pytest.mark.parametrize("seed", range(18))
def test_swapping_charts_keeps_overall_scores_in_the_same_general_band(seed):
    report_ab = build_report_from_seed(seed)
    report_ba = build_report_from_seed(seed, swap=True)

    delta = abs(float(report_ab["summary"]["overall_score"]) - float(report_ba["summary"]["overall_score"]))
    assert delta <= 25.0
