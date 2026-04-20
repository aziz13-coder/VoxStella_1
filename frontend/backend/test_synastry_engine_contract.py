import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_engine import build_synastry_report


def _make_bundle(chart_data):
    return {"chart_data": chart_data, "meta": {}}


def _sample_chart_a():
    return {
        "ascendant": 0.0,
        "midheaven": 270.0,
        "houses": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        "planets": [
            {"planet": "Sun", "longitude": 10.0, "sign": "Aries", "house": 1},
            {"planet": "Moon", "longitude": 102.0, "sign": "Cancer", "house": 4},
            {"planet": "Mercury", "longitude": 70.0, "sign": "Gemini", "house": 3},
            {"planet": "Venus", "longitude": 14.0, "sign": "Aries", "house": 1},
            {"planet": "Mars", "longitude": 130.0, "sign": "Leo", "house": 5},
            {"planet": "Jupiter", "longitude": 252.0, "sign": "Sagittarius", "house": 9},
            {"planet": "Saturn", "longitude": 311.0, "sign": "Aquarius", "house": 11},
            {"planet": "Uranus", "longitude": 132.0, "sign": "Leo", "house": 5},
            {"planet": "North Node", "longitude": 188.0, "sign": "Libra", "house": 7},
            {"planet": "Chiron", "longitude": 42.0, "sign": "Taurus", "house": 2},
        ],
    }


def _sample_chart_b():
    return {
        "ascendant": 180.0,
        "midheaven": 90.0,
        "houses": [180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0],
        "planets": [
            {"planet": "Sun", "longitude": 132.0, "sign": "Leo", "house": 11},
            {"planet": "Moon", "longitude": 188.0, "sign": "Libra", "house": 1},
            {"planet": "Mercury", "longitude": 73.0, "sign": "Gemini", "house": 9},
            {"planet": "Venus", "longitude": 43.0, "sign": "Taurus", "house": 8},
            {"planet": "Mars", "longitude": 44.0, "sign": "Taurus", "house": 8},
            {"planet": "Jupiter", "longitude": 15.0, "sign": "Aries", "house": 7},
            {"planet": "Saturn", "longitude": 101.0, "sign": "Cancer", "house": 10},
            {"planet": "Neptune", "longitude": 102.0, "sign": "Cancer", "house": 10},
            {"planet": "Pluto", "longitude": 12.0, "sign": "Aries", "house": 7},
            {"planet": "North Node", "longitude": 311.0, "sign": "Aquarius", "house": 5},
            {"planet": "Chiron", "longitude": 14.0, "sign": "Aries", "house": 7},
        ],
    }


def _build_report(**options):
    return build_synastry_report(
        _make_bundle(_sample_chart_a()),
        _make_bundle(_sample_chart_b()),
        {"id": "A", "label": "Chart A", "effective_datetime": "2026-04-02T10:00:00+00:00", "location": "A"},
        {"id": "B", "label": "Chart B", "effective_datetime": "2026-04-02T10:00:00+00:00", "location": "B"},
        options=options or None,
    )


def test_synastry_report_returns_expected_sections_and_dimensions():
    report = _build_report()

    assert "summary" in report
    assert "categories" in report
    assert "top_supportive_links" in report
    assert "top_challenging_links" in report
    assert "overlays" in report
    assert "receptions" in report
    assert "sources" in report
    assert "governance" in report
    assert "options" in report

    categories = {item["id"]: item for item in report["categories"]}
    for key in ("overall", "resonance", "communication", "attraction", "compatibility", "attachment", "growth", "friction", "burden"):
        assert key in categories
    assert categories["friction"]["polarity"] == "negative"
    assert categories["burden"]["polarity"] == "negative"
    assert 0 <= categories["overall"]["score"] <= 100
    assert isinstance(categories["overall"]["components"], dict)
    assert isinstance(categories["communication"]["evidence_items"], list)


def test_synastry_report_uses_new_lineage_and_compensation_logic():
    report = _build_report()
    categories = {item["id"]: item for item in report["categories"]}

    assert report["governance"]["catalog_version"] == "2026-04-02"
    assert "davison" in report["governance"]["active_source_keys"]
    assert "march_mcevers" in report["governance"]["active_source_keys"]
    assert categories["growth"]["score"] > 0
    assert categories["attachment"]["score"] > 0
    assert categories["burden"]["score"] >= 0
    assert report["top_supportive_links"]
    assert report["top_challenging_links"]
    assert any(item.get("rule_family_id") == "element_lack_fill" for item in categories["growth"]["evidence_items"])
    assert any("Strongest support:" in line or "Main pressure:" in line for line in report["summary"]["summary_lines"])
    assert report["summary"]["overall_components"]["compatibility"] >= 0
    assert report["summary"]["overall_components"]["support_balance"] >= 0
    assert report["summary"]["overall_components"]["headline_weighted_total"] >= 0
    assert 0 <= report["summary"]["overall_components"]["headline_normalized_total"] <= 100
    assert report["summary"]["overall_components"]["legacy_weighted_total"] >= 0
    assert report["summary"]["overall_components"]["headline_model"] == "category_weighted_v3_sigmoid"
    assert report["summary"]["overall_components"]["headline_weights"]["attachment"] == 0.12
    assert report["summary"]["overall_components"]["headline_weights"]["friction"] == -0.06
    assert report["summary"]["overall_components"]["headline_normalization"]["method"] == "sigmoid"
    assert report["summary"]["overall_components"]["category_scores"]["attachment"] >= 0


def test_synastry_report_respects_optional_point_layers():
    report = _build_report(include_modern=False, include_nodes=False, include_chiron=False, orb_profile="tight")

    active_points = set(report["governance"]["active_points"])
    active_rule_families = set(report["governance"]["active_rule_family_ids"])

    assert "Uranus" not in active_points
    assert "Neptune" not in active_points
    assert "Pluto" not in active_points
    assert "North Node" not in active_points
    assert "Chiron" not in active_points
    assert "sun_uranus_dynamic" not in active_rule_families
    assert report["options"]["orb_profile"] == "tight"


def test_synastry_report_exposes_point_availability_metadata():
    report = _build_report(include_modern=True, include_nodes=True, include_chiron=True, orb_profile="balanced")

    availability = report["governance"]["point_availability"]

    assert availability["modern_available"] is True
    assert availability["chiron_available"] is True
    assert availability["nodes_available"] is True
    assert "Uranus" in availability["chart_a_raw_points"] or "Uranus" in availability["chart_b_raw_points"]
    assert "Chiron" in availability["chart_a_raw_points"] or "Chiron" in availability["chart_b_raw_points"]
