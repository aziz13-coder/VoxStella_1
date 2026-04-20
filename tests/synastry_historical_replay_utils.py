import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_1.json"

for path in (REPO_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from synastry_engine import build_synastry_report
from tests.synastry_historical_validation_utils import compare_case_to_synastry_output


def load_synastry_historical_replay_cases(path=FIXTURE_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def replay_synastry_historical_case(case):
    bundle_a = {"chart_data": case["chart_data_a"], "meta": {"label": case["partner_a"]}}
    bundle_b = {"chart_data": case["chart_data_b"], "meta": {"label": case["partner_b"]}}
    report = build_synastry_report(
        bundle_a,
        bundle_b,
        case["chart_meta_a"],
        case["chart_meta_b"],
        options=case.get("options") or None,
    )
    comparison = compare_case_to_synastry_output(case, report)
    return report, comparison
