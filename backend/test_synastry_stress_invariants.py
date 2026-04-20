import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_stress_support import assert_report_invariants, build_report_from_seed


@pytest.mark.parametrize("seed", range(24))
def test_seeded_synastry_reports_hold_core_invariants(seed):
    report = build_report_from_seed(seed)
    assert_report_invariants(report)
