from pathlib import Path
import sys

import pytest


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import mcp_feature_service as service  # noqa: E402


CHART_A = {
    "label": "Person A",
    "datetime": "1990-01-01T12:00:00+02:00",
    "location": "Jerusalem, Israel",
    "timezone": "Asia/Jerusalem",
    "latitude": 31.778,
    "longitude": 35.235,
    "house_system_code": "R",
}
CHART_B = {
    "label": "Person B",
    "datetime": "1992-06-15T18:30:00-04:00",
    "location": "New York, NY",
    "timezone": "America/New_York",
    "latitude": 40.7128,
    "longitude": -74.006,
    "house_system_code": "R",
}


def test_explicit_synastry_uses_no_saved_chart_state():
    result = service.calculate_synastry({
        "chart_a": CHART_A,
        "chart_b": CHART_B,
        "engine_id": "memo",
        "include_modern": False,
    })

    assert result["schema_version"] == "voxstella.astrology.v1"
    assert result["engine_id"] == "memo"
    assert result["governance"]["mcp_context"]["input_mode"] == "explicit"
    assert result["governance"]["mcp_context"]["saved_chart_access"] is False


def test_explicit_synastry_rejects_unknown_outer_fields():
    with pytest.raises(service.McpInputError, match="unsupported request fields"):
        service.calculate_synastry({
            "chart_a": CHART_A,
            "chart_b": CHART_B,
            "saved_chart_query": "all",
        })


def test_explicit_synastry_reuses_strict_chart_validation():
    with pytest.raises(service.McpInputError, match="timezone"):
        service.calculate_synastry({
            "chart_a": {**CHART_A, "timezone": "not/a-zone"},
            "chart_b": CHART_B,
        })
