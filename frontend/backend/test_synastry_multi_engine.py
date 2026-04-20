import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_multi_engine import (
    _build_engine_points,
    _explicit_aspect_score,
    _house_group,
    _shared_contact_rows,
    _union_pair_slots,
    build_synastry_engine_report,
    list_synastry_engines,
)


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
        ],
    }


def _build(engine_id="memo", **kwargs):
    return build_synastry_engine_report(
        _make_bundle(_sample_chart_a()),
        _make_bundle(_sample_chart_b()),
        {"id": "A", "label": "Chart A", "effective_datetime": "2026-04-19T10:00:00+00:00", "location": "A"},
        {"id": "B", "label": "Chart B", "effective_datetime": "2026-04-19T10:00:00+00:00", "location": "B"},
        options={"include_modern": True, "include_nodes": True, "include_chiron": False, "orb_profile": "balanced"},
        engine_id=engine_id,
        **kwargs,
    )


def test_synastry_engine_registry_lists_all_supported_modes():
    ids = [item["id"] for item in list_synastry_engines()]

    assert ids == ["memo", "life_themes", "union_dynamics", "work_alliance"]


def test_life_themes_report_returns_structured_theme_sections():
    report = _build("life_themes")

    assert report["report_kind"] == "structured"
    assert report["engine_id"] == "life_themes"
    assert [section["id"] for section in report["sections"]] == ["themes", "pressure", "contact_grid"]
    theme_ids = [item["id"] for item in report["sections"][0]["items"]]
    assert theme_ids == [f"alaspT{house:02d}" for house in range(1, 13)]
    assert "theme_total" in report["summary"]
    assert "aspect_total" in report["summary"]
    assert report["governance"]["ordered_pair"] is True
    assert report["areas"]["label"] == "Areas Diagram"
    assert [stripe["id"] for stripe in report["areas"]["stripes"]] == [
        "subject_a_elements",
        "subject_b_elements",
        "element_compliance",
        "house_importance",
    ]
    assert "mid_raw" in report["sections"][0]["items"][0]["rows"][0]
    assert "logic_type" in report["sections"][0]["items"][0]["rows"][0]


def test_structured_explicit_rows_preserve_cross_aspect_names():
    report = _build("life_themes")

    explicit_rows = []
    for section in report["sections"]:
        items = section.get("items") or []
        if items and isinstance(items[0], dict) and "rows" in items[0]:
            for item in items:
                explicit_rows.extend(
                    row for row in (item.get("rows") or [])
                    if row.get("logic_type") == "explicit_aspect"
                )
        else:
            explicit_rows.extend(
                row for row in items
                if row.get("logic_type") == "explicit_aspect"
            )

    assert explicit_rows
    assert all(str(row.get("aspect_name") or "").strip() for row in explicit_rows)
    assert all(" None " not in str(row.get("label") or "") for row in explicit_rows)


def test_shared_contact_rows_accept_cross_aspect_field_name():
    rows = _shared_contact_rows(
        [
            {
                "point_a": "Sun",
                "point_b": "Moon",
                "aspect": "Trine",
                "orb": 0.5,
            }
        ]
    )

    assert rows == [
        {
            "label": "Sun Trine Moon",
            "detail": "orb 0.5",
            "score": 8,
            "aspect_name": "Trine",
            "orb": 0.5,
            "mode": "explicit_aspect",
            "left": "Sun",
            "right": "Moon",
            "layer": "shared",
        }
    ]


def test_minor_explicit_aspects_can_legitimately_quantize_to_zero():
    assert _explicit_aspect_score({"point_a": "Venus", "point_b": "Mars", "aspect": "Semisextile"}) == 0
    assert _explicit_aspect_score({"point_a": "Ascendant", "point_b": "Ascendant", "aspect": "Opposition"}) == 0


def test_work_alliance_uses_business_house_cluster_only():
    report = _build("work_alliance")

    assert report["engine_id"] == "work_alliance"
    theme_ids = [item["id"] for item in report["sections"][0]["items"]]
    assert theme_ids == ["alaspT01", "alaspT02", "alaspT06", "alaspT07", "alaspT10"]
    assert any("multi-instrument benchmark coverage" in gap.lower() for gap in report["governance"]["known_gaps"])
    assert [stripe["id"] for stripe in report["areas"]["stripes"]] == [
        "subject_a_elements",
        "subject_b_elements",
        "element_compliance",
        "house_importance",
    ]
    durability = report["summary"]["durability_check"]
    assert durability["id"] == "work_durability_v1"
    assert 0 <= int(durability["score"]) <= 100
    assert str(durability["title"]).strip()
    assert report["governance"]["outcome_model"] == "work_durability_v1"
    assert str(report["summary"]["summary_lines"][0]).startswith("Durability check:")


def test_house_group_uses_full_cusp_span_rulers_without_occupants():
    chart = {
        "ascendant": 0.0,
        "midheaven": 270.0,
        "houses": [0.0, 75.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 315.0, 330.0, 345.0],
        "planets": [
            {"planet": "Mars", "longitude": 5.0, "sign": "Aries", "house": 1},
            {"planet": "Venus", "longitude": 40.0, "sign": "Taurus", "house": 1},
            {"planet": "Mercury", "longitude": 70.0, "sign": "Gemini", "house": 1},
            {"planet": "Moon", "longitude": 12.0, "sign": "Aries", "house": 1},
        ],
    }

    points = _build_engine_points(
        chart,
        {"include_modern": True, "include_nodes": True, "include_chiron": False, "orb_profile": "balanced"},
    )

    assert _house_group(points, chart, 1) == ["Mars", "Venus", "Mercury"]


def test_work_alliance_pressure_uses_business_warning_houses_and_cusp_rule():
    chart_a = _sample_chart_a()
    chart_b = _sample_chart_b()
    chart_a["houses"] = [240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0]
    chart_a["planets"] = [
        {"planet": "Sun", "longitude": 10.0, "sign": "Aries", "house": 1},
        {"planet": "Mercury", "longitude": 70.0, "sign": "Gemini", "house": 3},
        {"planet": "Venus", "longitude": 44.0, "sign": "Taurus", "house": 2},
        {"planet": "Mars", "longitude": 136.0, "sign": "Leo", "house": 5},
        {"planet": "Saturn", "longitude": 198.0, "sign": "Libra", "house": 7},
        {"planet": "Neptune", "longitude": 199.0, "sign": "Libra", "house": 7},
    ]

    report = build_synastry_engine_report(
        _make_bundle(chart_a),
        _make_bundle(chart_b),
        {"id": "A", "label": "Chart A", "effective_datetime": "2026-04-19T10:00:00+00:00", "location": "A"},
        {"id": "B", "label": "Chart B", "effective_datetime": "2026-04-19T10:00:00+00:00", "location": "B"},
        options={"include_modern": True, "include_nodes": True, "include_chiron": False, "orb_profile": "balanced"},
        engine_id="work_alliance",
    )

    pressure_labels = [item["label"] for item in report["sections"][1]["items"]]
    assert "Snap A: H2 cusp" in pressure_labels
    assert "Snap A: Neptune" not in pressure_labels


def test_union_dynamics_surfaces_profile_mode_and_core_sections():
    report = _build("union_dynamics", profile_a="feminine", profile_b="masculine")

    assert report["engine_id"] == "union_dynamics"
    assert [section["id"] for section in report["sections"]] == ["bond", "home", "contact_grid"]
    assert report["governance"]["profile_mode"] == {"profile_a": "feminine", "profile_b": "masculine"}
    bond_ids = [item["id"] for item in report["sections"][0]["items"]]
    home_ids = [item["id"] for item in report["sections"][1]["items"]]
    assert bond_ids == ["alasp157P", "alasp157R", "alasp157B"]
    assert home_ids == ["alasp14P", "alasp14R", "alasp14B"]


def test_union_dynamics_uses_exact_decoded_slot_tables_for_explicit_profiles():
    assert _union_pair_slots("masculine", "feminine", "157") == [
        ("Mars", "Venus"),
        ("Venus", "Mars"),
        ("Mars", "Mars"),
        ("Venus", "Venus"),
        ("Sun", "Mars"),
        ("Venus", "Sun"),
        ("Sun", "Sun"),
    ]
    assert _union_pair_slots("masculine", "feminine", "14") == [
        ("Moon", "Moon"),
        ("Saturn", "Moon"),
        ("Moon", "Saturn"),
        ("Saturn", "Saturn"),
        ("Moon", "Sun"),
        ("Saturn", "Sun"),
        ("Sun", "Sun"),
    ]

    report = _build("union_dynamics", profile_a="masculine", profile_b="feminine")
    bond_psychology = report["sections"][0]["items"][0]
    home_psychology = report["sections"][1]["items"][0]

    assert bond_psychology["logic_mode"] == "exact_slots"
    assert home_psychology["logic_mode"] == "exact_slots"
    assert bond_psychology["slot_count"] == 7
    assert home_psychology["slot_count"] == 7


def test_life_themes_summary_rolls_pressure_into_theme_total():
    report = _build("life_themes")

    theme_sum = sum(int(item["score"]) for item in report["sections"][0]["items"])
    summary = report["summary"]

    assert summary["theme_total"] == theme_sum + int(summary["burden_total"])
    assert summary["composite_total"] == int(summary["theme_total"]) + int(summary["aspect_total"])


def test_memo_engine_still_wraps_the_existing_synastry_report():
    report = _build("memo")

    assert report["report_kind"] == "memo"
    assert report["engine_id"] == "memo"
    assert report["engine_label"] == "Memo"
    assert "categories" in report
    assert len(report["available_engines"]) == 4
