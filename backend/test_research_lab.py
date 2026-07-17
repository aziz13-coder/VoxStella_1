from __future__ import annotations

from research_lab import (
    analyze_feature_sets,
    analyze_research_snapshots,
    build_run_id,
    extract_research_features,
    generate_matched_control_rows,
    list_evaluator_catalog,
    normalize_chart_row,
    normalize_feature_scopes,
)


def test_build_run_id_uses_a_stable_sha256_fingerprint():
    run_id = build_run_id({"beta": 2, "alpha": 1})

    assert run_id == "c22290b89e167a67"
    assert len(run_id) == 16


def _synthetic_chart():
    return {
        "ascendant": 10.0,
        "midheaven": 100.0,
        "houses": [10.0, 40.0, 70.0, 100.0, 130.0, 160.0, 190.0, 220.0, 250.0, 280.0, 310.0, 340.0],
        "house_rulers": {"1": "Mars", "10": "Saturn"},
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 15.0, "sign": "Aries", "house": 1, "speed": 0.98, "dignity_score": 5},
            "Moon": {"planet": "Moon", "longitude": 75.0, "sign": "Gemini", "house": 3, "speed": 12.4, "dignity_score": 0},
            "Mars": {"planet": "Mars", "longitude": 105.0, "sign": "Cancer", "house": 4, "speed": -0.2, "retrograde": True, "dignity_score": -4},
            "Saturn": {"planet": "Saturn", "longitude": 195.0, "sign": "Libra", "house": 7, "speed": 0.05, "dignity_score": 4},
        },
        "receptions": {
            "items": [
                {"type": "mutual_rulership", "planet_a": "Mars", "planet_b": "Saturn"},
            ]
        },
    }


def _synthetic_enrichments():
    return {
        "metrics": {
            "planetary_aspects": [
                {"planet1": "Sun", "planet2": "Moon", "aspect": "Sextile", "orb": 0.0},
                {"planet1": "Mars", "planet2": "Saturn", "aspect": "Square", "orb": 0.0},
            ],
            "angle_aspects": [
                {"planet": "Sun", "angle": "ASC", "aspect": "Conjunction", "orb": 5.0},
            ],
            "planet_houses": {"Mars": 4, "Saturn": 7},
            "planet_signs": {"Mars": "Cancer", "Saturn": "Libra"},
            "solar": {"conditions": {"Mars": "Under the Beams"}},
            "solar_phase": {"under_beams_applying": ["Mars"]},
            "final_dispositor": {"Mars": "Moon"},
        },
        "points_payload": {
            "points": [
                {
                    "key": "career_parts_35",
                    "name": "Career",
                    "available": True,
                    "longitude": 182.0,
                    "zodiac": {"sign": "Libra", "formatted": "2 Libra 00"},
                    "hits": [{"object_name": "Jupiter", "aspect": "Square"}],
                }
            ]
        },
        "arabic_parts": {
            "fortune": {"name": "Fortune", "lon": 44.0, "sign": "Taurus", "house": 2, "ruler": "Venus"}
        },
        "fixed_star_hits": [
            {"star": "Regulus", "planet": "Sun", "orb": 0.4}
        ],
        "asteroids": {
            "items": [
                {"name": "Ceres", "longitude": 88.0, "sign": "Gemini", "retrograde": False}
            ]
        },
    }


def test_evaluator_catalog_includes_vox_stella_families():
    catalog = list_evaluator_catalog()
    ids = {row["id"] for row in catalog}

    assert {"positions", "aspects", "dignities", "points", "lots", "fixed_stars", "asteroids", "directional_3d"} <= ids
    assert all("legacy" not in row["label"].lower() for row in catalog)


def test_evaluator_catalog_exposes_explicit_scopes_and_defaults():
    catalog = list_evaluator_catalog()
    positions = next(row for row in catalog if row["id"] == "positions")
    directional = next(row for row in catalog if row["id"] == "directional_3d")

    assert positions["default_scopes"] == ["planet_signs"]
    assert {scope["id"] for scope in positions["scopes"]} >= {"planet_signs", "elements", "modalities", "zodiac_range"}
    assert directional["default_scopes"] == ["horizon_state"]
    assert {scope["id"] for scope in directional["scopes"]} == {"horizon_state"}


def test_legacy_family_selection_expands_to_default_scopes_only():
    scopes = normalize_feature_scopes(None, evaluator_families=["positions", "points"])

    assert scopes == [
        {"family": "points", "preset": "active_points", "objects": "default"},
        {"family": "positions", "preset": "planet_signs", "objects": "default"},
    ]


def test_normalize_chart_row_accepts_datetime_and_date_time_forms():
    row_a = normalize_chart_row({
        "name": "A",
        "datetime": "1990-01-13T21:33:00",
        "location": "Jerusalem, Israel",
        "timezone": "Asia/Jerusalem",
    })
    row_b = normalize_chart_row({
        "name": "B",
        "date": "13/01/1990",
        "time": "21:33",
        "location": "Jerusalem, Israel",
    })

    assert row_a["valid"] is True
    assert row_a["datetime"] == "1990-01-13T21:33:00"
    assert row_b["valid"] is True
    assert row_b["datetime"] == "1990-01-13T21:33:00"


def test_normalize_chart_row_accepts_bulk_import_header_aliases():
    row = normalize_chart_row({
        "Chart Name": "Subject A",
        "Birth Date": "1990-01-13",
        "Birth Time": "21:33",
        "Place": "Jerusalem, Israel",
        "TZ": "Asia/Jerusalem",
        "Lat": "31.778",
        "Lng": "35.235",
        "Type": "event",
    })

    assert row["valid"] is True
    assert row["name"] == "Subject A"
    assert row["datetime"] == "1990-01-13T21:33:00"
    assert row["location"] == "Jerusalem, Israel"
    assert row["timezone"] == "Asia/Jerusalem"
    assert row["latitude"] == 31.778
    assert row["longitude"] == 35.235
    assert row["chart_type"] == "event"


def test_matched_controls_are_reproducible_and_preserve_context():
    rows = [{
        "name": "Target",
        "datetime": "1990-01-13T21:33:00",
        "location": "Jerusalem, Israel",
        "timezone": "Asia/Jerusalem",
        "latitude": 31.778,
        "longitude": 35.235,
        "chart_type": "natal",
    }]

    first = generate_matched_control_rows(rows, per_chart=3, seed="abc", year_window=2)
    second = generate_matched_control_rows(rows, per_chart=3, seed="abc", year_window=2)

    assert first == second
    assert len(first) == 3
    assert {row["location"] for row in first} == {"Jerusalem, Israel"}
    assert {row["timezone"] for row in first} == {"Asia/Jerusalem"}
    assert {row["chart_type"] for row in first} == {"natal"}


def test_extract_research_features_from_supported_calculations():
    features = extract_research_features(
        _synthetic_chart(),
        feature_scopes=[
            {"family": "positions", "preset": "planet_signs"},
            {"family": "houses", "preset": "planet_houses"},
            {"family": "aspects", "preset": "planetary_aspects"},
            {"family": "rulership", "preset": "house_rulers"},
            {"family": "receptions", "preset": "reception_pairs"},
            {"family": "dispositors", "preset": "final_dispositors"},
            {"family": "dignities", "preset": "dignity_status"},
            {"family": "motion", "preset": "direction"},
            {"family": "solar", "preset": "solar_conditions"},
            {"family": "points", "preset": "active_points"},
            {"family": "lots", "preset": "lot_signs"},
            {"family": "fixed_stars", "preset": "star_hits"},
            {"family": "asteroids", "preset": "asteroid_signs"},
            {"family": "midpoints", "preset": "midpoint_signs"},
        ],
        enrichments=_synthetic_enrichments(),
    )

    keys = set(features)
    assert "positions:planet_sign:Sun:Aries" in keys
    assert "houses:planet_house:Mars:4" in keys
    assert "aspects:planetary:Sun:Sextile:Moon" in keys
    assert "rulership:house_ruler:1:Mars" in keys
    assert "receptions:mutual_rulership:Mars:Saturn" in keys
    assert "dispositors:final:Mars:Moon" in keys
    assert "dignities:planet_dignified:Sun" in keys
    assert "motion:retrograde:Mars" in keys
    assert "solar:condition:Mars:Under_the_Beams" in keys
    assert "points:active:career_parts_35" in keys
    assert "lots:sign:Fortune:Taurus" in keys
    assert "fixed_stars:hit:Regulus:Sun" in keys
    assert "asteroids:sign:Ceres:Gemini" in keys
    assert any(key.startswith("midpoints:pair_sign:Sun:Moon:") for key in keys)


def test_positions_default_scope_does_not_emit_elements_or_modalities():
    features = extract_research_features(_synthetic_chart(), evaluator_families=["positions"])
    keys = set(features)

    assert "positions:planet_sign:Sun:Aries" in keys
    assert "positions:planet_element:Sun:Fire" not in keys
    assert "positions:planet_modality:Sun:Cardinal" not in keys


def test_positions_element_scope_emits_element_features():
    features = extract_research_features(
        _synthetic_chart(),
        feature_scopes=[{"family": "positions", "preset": "elements"}],
    )
    keys = set(features)

    assert "positions:planet_element:Sun:Fire" in keys
    assert "positions:planet_sign:Sun:Aries" not in keys


def test_positions_custom_zodiac_range_matches_only_requested_range():
    matching = extract_research_features(
        _synthetic_chart(),
        feature_scopes=[{
            "family": "positions",
            "kind": "zodiac_range",
            "object": "Sun",
            "sign": "Aries",
            "start_degree": 5,
            "end_degree": 20,
        }],
    )
    non_matching = extract_research_features(
        _synthetic_chart(),
        feature_scopes=[{
            "family": "positions",
            "kind": "zodiac_range",
            "object": "Sun",
            "sign": "Aries",
            "start_degree": 20,
            "end_degree": 25,
        }],
    )

    assert "positions:zodiac_range:Sun:Aries:5:20" in matching
    assert "positions:zodiac_range:Sun:Aries:20:25" not in non_matching


def test_explicit_custom_scopes_do_not_merge_family_defaults():
    payload = analyze_research_snapshots(
        [{"chart_data": _synthetic_chart(), "enrichments": _synthetic_enrichments()}],
        [{"chart_data": _synthetic_chart(), "enrichments": _synthetic_enrichments()}],
        evaluator_families=["positions"],
        feature_scopes=[{
            "family": "positions",
            "kind": "zodiac_range",
            "object": "Sun",
            "sign": "Aries",
            "start_degree": 5,
            "end_degree": 20,
        }],
    )
    signal_keys = {row["key"] for row in payload["signals"]}

    assert payload["feature_scope_count"] == 1
    assert signal_keys == {"positions:zodiac_range:Sun:Aries:5:20"}


def test_multiple_custom_zodiac_ranges_are_preserved_as_separate_scopes():
    scopes = normalize_feature_scopes([
        {
            "family": "positions",
            "kind": "zodiac_range",
            "object": "Sun",
            "sign": "Aries",
            "start_degree": 4,
            "end_degree": 10,
        },
        {
            "family": "positions",
            "kind": "zodiac_range",
            "object": "Moon",
            "sign": "Taurus",
            "start_degree": 4,
            "end_degree": 10,
        },
    ])

    assert scopes == [
        {
            "family": "positions",
            "kind": "zodiac_range",
            "object": "Moon",
            "sign": "Taurus",
            "start_degree": 4.0,
            "end_degree": 10.0,
        },
        {
            "family": "positions",
            "kind": "zodiac_range",
            "object": "Sun",
            "sign": "Aries",
            "start_degree": 4.0,
            "end_degree": 10.0,
        },
    ]


def test_analysis_payload_reports_normalized_feature_scopes():
    payload = analyze_research_snapshots(
        [{"chart_data": _synthetic_chart(), "enrichments": _synthetic_enrichments()}],
        [{"chart_data": _synthetic_chart(), "enrichments": _synthetic_enrichments()}],
        feature_scopes=[{"family": "positions", "preset": "planet_signs"}],
    )

    assert payload["feature_scope_count"] == 1
    assert payload["feature_scopes"] == [{"family": "positions", "preset": "planet_signs", "objects": "default"}]


def test_analyze_feature_sets_ranks_target_heavy_signal_and_warns_on_small_sample():
    target_sets = [
        {"feature:shared", "feature:target_heavy"},
        {"feature:shared", "feature:target_heavy"},
        {"feature:target_heavy"},
        {"feature:target_heavy"},
    ]
    control_sets = [
        {"feature:shared"},
        {"feature:shared"},
        {"feature:shared"},
        {"feature:shared"},
        {"feature:shared"},
        {"feature:shared"},
        {"feature:shared"},
        {"feature:shared"},
    ]
    labels = {
        "feature:shared": {"label": "Shared Feature", "family": "test"},
        "feature:target_heavy": {"label": "Target Heavy", "family": "test"},
    }

    payload = analyze_feature_sets(target_sets, control_sets, labels)

    assert payload["target_count"] == 4
    assert payload["control_count"] == 8
    assert payload["signals"][0]["key"] == "feature:target_heavy"
    assert payload["signals"][0]["effect_direction"] == "more_common"
    assert payload["signals"][0]["target_count"] == 4
    assert payload["signals"][0]["control_count"] == 0
    assert payload["signals"][0]["p_value"] is not None
    assert payload["signals"][0]["q_value"] is not None
    assert "small_target_sample" in payload["signals"][0]["warnings"]
