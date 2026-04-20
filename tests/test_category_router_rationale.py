from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from backend.evaluate_chart import evaluate_chart


def build_chart(category: str):
    return {
        "category": category,
        "aspects": [
            {"planet1": "Moon", "planet2": "Sun", "aspect": "Trine", "applying": True}
        ],
    }


def test_category_router_toggle_and_rationale():
    chart = build_chart("education")
    result = evaluate_chart(chart)
    assert result["verdict"] == "YES"
    assert result["rationale"] == ["moon_applying_trine_examiner_sun (+1.0)"]

    chart_no = build_chart("finance")
    result_no = evaluate_chart(chart_no)
    assert result_no["verdict"] == "NO"
    assert result_no["rationale"] == []
