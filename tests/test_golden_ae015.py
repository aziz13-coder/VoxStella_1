import json
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from backend.evaluate_chart import evaluate_chart
from backend.horary_engine.polarity_weights import TestimonyKey


def _find_ae015_fixture() -> Path | None:
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    matches = sorted(backend_dir.glob("*AE-015*.json"))
    return matches[0] if matches else None


def test_ae015_golden_expect_yes():
    data_path = _find_ae015_fixture()
    if data_path is None:
        pytest.skip("AE-015 golden fixture not present in backend/")
    chart = json.loads(data_path.read_text(encoding="utf-8"))
    result = evaluate_chart(chart)
    assert result["verdict"] == "YES"
    keys = [entry["key"] for entry in result["ledger"]]
    assert TestimonyKey.MOON_APPLYING_TRINE_EXAMINER_SUN in keys
