from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from astro_clock_metrics import _degree_hits, _parse_degree_token


def _houses():
    return [i * 30.0 for i in range(12)]


def test_parse_degree_token_accepts_chart_style_notation():
    assert _parse_degree_token("25 Leo") == 145.0
    assert round(_parse_degree_token("25°59' Leo"), 6) == round(145.98333333333332, 6)
    assert _parse_degree_token("Leo 25°15'") == 145.25
    assert _parse_degree_token("25.5 Leo") == 145.5


def test_degree_hits_include_parts_for_chart_style_tokens():
    chart_data = {
        "ascendant": 0.0,
        "midheaven": 90.0,
        "houses": _houses(),
        "arabic_parts": {
            "fortune": {"name": "Part of Fortune", "lon": 145.25},
        },
    }
    planets = [
        {"planet": "Moon", "longitude": 145.25},
        {"planet": "Mars", "longitude": 145.9},
    ]

    result = _degree_hits(chart_data, planets, ["Leo 25°15'"])

    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["degree"] == "Leo 25°15'"
    assert item["count"] == 3
    assert item["midpoint_active"] is True
    assert {hit["type"] for hit in item["hits"]} == {"planet", "part"}
