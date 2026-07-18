from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from astro_clock_points import (
    _house_cusp,
    _houses,
    compute_fortune_longitude,
    compute_spirit_longitude,
    compute_symbolic_points_payload,
    load_filtered_points_catalog,
    normalize360,
    resolve_gradarh_token,
    resolve_manager_token,
    short_arc_midpoint,
)


FORCED_SOURCE_ROWS = {
    "parts#2",
    "parts#18",
    "parts#22",
    "parts#35",
    "parts#80",
    "parts#103",
    "parts#145",
    "parts#179",
    "parts#253",
    "parts#332",
    "parts#334",
    "parts#366",
    "midpoints#85",
}

GROUPED_MODULE_KEYS = {
    "serial_homicide",
    "cult_mass_spree",
    "individual_homicide",
    "legal_research_mixed",
}


def _base_planets(**overrides):
    rows = {
        "Sun": {"planet": "Sun", "longitude": 30.0, "house": 10},
        "Moon": {"planet": "Moon", "longitude": 80.0, "house": 4},
        "Mercury": {"planet": "Mercury", "longitude": 20.0, "house": 3},
        "Venus": {"planet": "Venus", "longitude": 95.0, "house": 5},
        "Mars": {"planet": "Mars", "longitude": 155.0, "house": 1},
        "Jupiter": {"planet": "Jupiter", "longitude": 215.0, "house": 9},
        "Saturn": {"planet": "Saturn", "longitude": 40.0, "house": 11},
        "Uranus": {"planet": "Uranus", "longitude": 275.0, "house": 8},
        "Neptune": {"planet": "Neptune", "longitude": 335.0, "house": 12},
        "Pluto": {"planet": "Pluto", "longitude": 125.0, "house": 6},
        "Chiron": {"planet": "Chiron", "longitude": 5.0, "house": 1},
        "Ceres": {"planet": "Ceres", "longitude": 12.0, "house": 4},
        "Pallas": {"planet": "Pallas", "longitude": 45.0, "house": 2},
        "Juno": {"planet": "Juno", "longitude": 75.0, "house": 3},
        "Vesta": {"planet": "Vesta", "longitude": 105.0, "house": 4},
        "Eros": {"planet": "Eros", "longitude": 135.0, "house": 5},
        "Psyche": {"planet": "Psyche", "longitude": 165.0, "house": 6},
        "Proserpina": {"planet": "Proserpina", "longitude": 195.0, "house": 7},
        "Lilith": {"planet": "Lilith", "longitude": 225.0, "house": 8},
        "Selena": {"planet": "Selena", "longitude": 255.0, "house": 9},
        "Rahu": {"planet": "Rahu", "longitude": 285.0, "house": 10},
        "Ketu": {"planet": "Ketu", "longitude": 105.0, "house": 4},
    }
    for name, patch in overrides.items():
        rows[name] = {**rows.get(name, {"planet": name}), **patch}
    return list(rows.values())


def _chart(**overrides):
    chart = {
        "ascendant": 20.0,
        "midheaven": 151.0,
        "houses": [20.0, 55.0, 90.0, 125.0, 160.0, 195.0, 230.0, 40.0, 250.0, 151.0, 290.0, 300.0],
        "planets": _base_planets(),
        "house_system_code": "P",
    }
    chart.update(overrides)
    return chart


def _rows_by_source(payload):
    return {row.get("source_row"): row for row in payload.get("points", [])}


def test_house_resolvers_prefer_exact_points_geometry_over_display_rounding():
    rounded_houses = [12.35, 44.44, 76.54, 262.19, 300.0, 331.0, 192.35, 19.8, 42.0, 82.35, 112.0, 144.81]
    exact_houses = [
        12.345678901,
        44.444444444,
        76.543219876,
        262.1948673182044,
        300.0,
        331.0,
        192.345678901,
        19.801681799358164,
        42.0,
        82.345678901,
        112.0,
        144.8074351945643,
    ]
    chart = {
        "houses": rounded_houses,
        "house_cusps_exact": exact_houses,
        "ascendant": 12.35,
        "ascendant_exact": 12.345678901,
        "midheaven": 82.35,
        "midheaven_exact": 82.345678901,
    }

    houses = _houses(chart)

    assert houses[3] == 262.1948673182044
    assert houses[7] == 19.801681799358164
    assert abs(houses[11] - 144.8074351945643) < 1e-12
    assert abs(_house_cusp(houses, 1, chart) - 12.345678901) < 1e-12
    assert abs(_house_cusp(houses, 10, chart) - 82.345678901) < 1e-12


def test_filtered_catalog_loads_403_unique_display_rows():
    catalog = load_filtered_points_catalog()
    points = catalog["points"]

    assert catalog["meta"]["kept"] == 403
    assert len(points) == 403

    normalized_names = [str(row["name"]).strip().lower() for row in points]
    assert len(normalized_names) == len(set(normalized_names))

    source_rows = {row["source_row"] for row in points}
    assert FORCED_SOURCE_ROWS.issubset(source_rows)
    assert "parts#8" not in source_rows
    assert not any(str(row.get("name", "")).strip().lower() == "aircraft" for row in points)


def test_filtered_catalog_formula_tokens_are_supported_by_current_resolvers():
    token_like = re.compile(r"[A-Z]+\d+")
    supported = re.compile(r"^(?:MS\d{2}|PM\d{2}|[PMTG]\d{3})$")
    tokens = set()
    for row in load_filtered_points_catalog()["points"]:
        for key in ("day_formula", "night_formula", "base_formula", "formula"):
            tokens.update(token_like.findall(str(row.get(key) or "")))

    assert tokens
    assert all(supported.match(token) for token in tokens)
    assert {"P024", "M010", "MS01", "MS08", "PM01", "T001", "T003", "G070"}.issubset(tokens)
    assert not any(token.startswith(("MM", "ME", "EH", "PGP", "PBP")) for token in tokens)


def test_normalize360_wraps_negative_and_overflow_values():
    assert normalize360(-1.0) == 359.0
    assert normalize360(361.25) == 1.25


def test_short_arc_midpoint_crosses_zero_on_shortest_arc():
    assert short_arc_midpoint(350.0, 10.0) == 0.0
    assert short_arc_midpoint(10.0, 350.0) == 0.0


def test_fortune_and_spirit_helpers_branch_by_day_night():
    assert compute_fortune_longitude(100.0, 30.0, 80.0, True) == 150.0
    assert compute_spirit_longitude(100.0, 30.0, 80.0, True) == 50.0
    assert compute_fortune_longitude(100.0, 30.0, 80.0, False) == 50.0
    assert compute_spirit_longitude(100.0, 30.0, 80.0, False) == 150.0


def test_day_night_formula_swap_uses_chart_context():
    day_chart = _chart(planets=_base_planets(
        Venus={"planet": "Venus", "longitude": 130.0, "house": 5},
        Uranus={"planet": "Uranus", "longitude": 230.0, "house": 8},
    ))
    night_chart = _chart(planets=_base_planets(
        Sun={"planet": "Sun", "longitude": 30.0, "house": 3},
        Venus={"planet": "Venus", "longitude": 130.0, "house": 5},
        Uranus={"planet": "Uranus", "longitude": 230.0, "house": 8},
    ))
    day_rows = _rows_by_source(compute_symbolic_points_payload(day_chart))
    night_rows = _rows_by_source(compute_symbolic_points_payload(night_chart))

    assert day_rows["parts#2"]["formula"]["used"] == "day"
    assert day_rows["parts#2"]["longitude"] == 280.0
    assert night_rows["parts#2"]["formula"]["used"] == "night"
    assert night_rows["parts#2"]["longitude"] == 120.0


def test_exact_time_formula_is_gated_when_houses_are_unavailable():
    payload = compute_symbolic_points_payload(_chart(ascendant=None, midheaven=None, houses=[]))
    career = _rows_by_source(payload)["parts#35"]

    assert career["available"] is False
    assert career["longitude"] is None
    assert payload["unavailable_count"] > 0
    assert payload["unavailable"][0]["reasons"][0]["code"]
    assert payload["unavailable"][0]["reasons"][0]["message"]


def test_exact_time_rows_can_use_exact_house_cusps_without_duplicate_angle_fields():
    exact_houses = [20.0, 55.0, 90.0, 125.0, 160.0, 195.0, 230.0, 40.0, 250.0, 151.0, 290.0, 300.0]
    payload = compute_symbolic_points_payload(_chart(
        ascendant=None,
        midheaven=None,
        houses=[],
        house_cusps_exact=exact_houses,
    ))
    theft = _rows_by_source(payload)["parts#334"]

    assert theft["available"] is True
    assert theft["unavailable_reasons"] == []
    assert theft["longitude"] == 165.0


def test_manager_and_gradarh_resolvers_use_documented_tables():
    chart = _chart(
        planets=_base_planets(
            Ceres={"planet": "Ceres", "longitude": 12.0, "house": 4},
            Saturn={"planet": "Saturn", "longitude": 170.0, "house": 11},
        )
    )

    manager = resolve_manager_token(chart, "M010")
    gradarh = resolve_gradarh_token(chart, "MS08")

    assert manager["available"] is True
    assert manager["object_name"] == "Ceres"
    assert manager["longitude"] == 12.0
    assert gradarh["available"] is True
    assert gradarh["object_name"] == "Saturn"
    assert gradarh["longitude"] == 170.0


def test_fixed_degree_and_pm_helper_rows_follow_catalog_formulas():
    rows = _rows_by_source(compute_symbolic_points_payload(_chart()))

    assert rows["parts#37"]["longitude"] == 40.0
    assert rows["parts#37"]["formula"]["tokens"]["G090"] == "Fixed zodiac degree 90"
    assert rows["parts#307"]["longitude"] == 202.5
    assert rows["parts#307"]["formula"]["tokens"]["PM01"] == "Cusp 1 manager midpoint"


def test_mercury_saturn_midpoint_uses_short_arc_formula():
    chart = _chart(
        planets=_base_planets(
            Mercury={"planet": "Mercury", "longitude": 350.0, "house": 3},
            Saturn={"planet": "Saturn", "longitude": 10.0, "house": 11},
        )
    )
    row = _rows_by_source(compute_symbolic_points_payload(chart))["midpoints#85"]

    assert row["longitude"] == 0.0
    assert row["formula"]["used"] == "midpoint"


def test_required_rows_are_present_and_grouped_modules_are_absent():
    payload = compute_symbolic_points_payload(_chart())
    source_rows = {row["source_row"] for row in payload["points"]}

    assert FORCED_SOURCE_ROWS.issubset(source_rows)
    assert not GROUPED_MODULE_KEYS.intersection({row["key"] for row in payload["points"]})
    assert "modules" not in payload
    assert "family_score" not in str(payload)


def test_active_hit_scoring_for_synthetic_exact_conjunction():
    chart = _chart(
        planets=_base_planets(
            Sun={"planet": "Sun", "longitude": 30.0, "house": 10},
            Mercury={"planet": "Mercury", "longitude": 20.0, "house": 3},
            Saturn={"planet": "Saturn", "longitude": 40.0, "house": 11},
        )
    )
    row = _rows_by_source(compute_symbolic_points_payload(chart))["midpoints#85"]

    exact = next(hit for hit in row["hits"] if hit["object_name"] == "Sun" and hit["aspect"] == "Conjunction")
    assert exact["orb"] == 0.0
    assert exact["fval"] == 0.0
    assert exact["strength"] == 1.0
    assert row["point_score"] == round(sum(hit["strength"] for hit in row["hits"]), 6)
    assert {"planet_channel", "aspect_tone", "tone_group", "summary"}.issubset(exact["interpretation"])


def test_inactive_point_returns_degree_without_hits():
    row = _rows_by_source(compute_symbolic_points_payload(_chart(
        planets=_base_planets(Sun={"planet": "Sun", "longitude": 0.0, "house": 10})
    )))["midpoints#85"]

    assert row["available"] is True
    assert row["longitude"] == 30.0
    assert row["zodiac"]["formatted"] == "0 Taurus 00"
    assert row["point_score"] == 0.0
    assert row["hits"] == []


def test_payload_shape_top_hits_limit_and_danger_metadata():
    chart = _chart(
        planets=_base_planets(
            Sun={"planet": "Sun", "longitude": 120.0, "house": 10},
            Mercury={"planet": "Mercury", "longitude": 20.0, "house": 3},
            Mars={"planet": "Mars", "longitude": 200.0, "house": 1},
        ),
        houses=[20.0, 55.0, 90.0, 125.0, 160.0, 195.0, 230.0, 40.0, 250.0, 151.0, 290.0, 300.0],
    )
    payload = compute_symbolic_points_payload(chart)

    assert {
        "points_catalog_version",
        "computed_count",
        "active_count",
        "unavailable_count",
        "top_hits",
        "unavailable",
    }.issubset(payload)
    assert len(payload["top_hits"]) <= 10

    top_row = payload["top_hits"][0]
    assert {
        "key",
        "source_row",
        "name",
        "longitude",
        "zodiac",
        "point_score",
        "ui_severity",
        "ui_color",
        "category",
        "hits",
    }.issubset(top_row)
    assert {
        "object_name",
        "aspect",
        "aspect_degrees",
        "orb",
        "fval",
        "allowed_orb",
        "strength",
    }.issubset(top_row["hits"][0])
    assert "formula" not in top_row
    assert "unavailable_reasons" not in top_row

    theft = _rows_by_source(payload)["parts#334"]
    assert theft["ui_severity"] == "danger"
    assert theft["ui_color"] == "red"
    assert theft["point_score"] > 0

    danger_sources = {
        "parts#2",
        "parts#90",
        "parts#103",
        "parts#251",
        "parts#253",
        "parts#327",
        "parts#334",
        "parts#355",
        "parts#366",
    }
    rows = _rows_by_source(payload)
    for source_row in danger_sources:
        assert rows[source_row]["ui_severity"] == "danger"
        assert rows[source_row]["ui_color"] == "red"


def test_chart_meta_datetime_utc_is_converted_from_offset_timestamp():
    payload = compute_symbolic_points_payload(
        _chart(),
        timestamp_iso="2000-02-29T12:34:00+01:00",
        house_system="P",
    )

    assert payload["chart_meta"]["datetime"] == "2000-02-29T12:34:00+01:00"
    assert payload["chart_meta"]["datetime_utc"] == "2000-02-29T11:34:00Z"


def test_unavailable_dependencies_are_structured_not_silent_zeroes():
    chart = _chart(planets=[row for row in _base_planets() if row["planet"] != "Ceres"])
    payload = compute_symbolic_points_payload(chart)
    career = _rows_by_source(payload)["parts#35"]

    assert career["available"] is False
    assert career["longitude"] is None
    assert any(reason["code"] == "missing_manager_object" for reason in career["unavailable_reasons"])
    assert any(row["source_row"] == "parts#35" for row in payload["unavailable"])
