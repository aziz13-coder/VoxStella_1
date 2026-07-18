import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import astrocartography_service
from astrocartography_assets import load_astrocartography_assets
from astrocartography_service import (
    build_delineation_report,
    build_astrocartography_lines,
    build_goal_scoring_context,
    build_global_paran_tracks,
    build_intersection_workspace,
    build_location_reading,
    build_local_space_rays,
    build_local_space_workspace,
    build_paran_candidates_for_point,
    crossing_candidates_for_point,
    nearest_lines_for_point,
)


def test_build_lines_returns_requested_meridian_lines():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Sun"],
        angles=["MC", "IC"],
    )

    ids = {line["id"] for line in payload["lines"]}
    assert ids == {"Sun:MC", "Sun:IC"}

    mc_line = next(line for line in payload["lines"] if line["id"] == "Sun:MC")
    segment = mc_line["segments"][0]
    longitudes = {round(point[1], 6) for point in segment}
    assert len(longitudes) == 1


def test_synthetic_mars_ic_uses_ut1_geometry():
    payload = build_astrocartography_lines(
        "2000-02-29T11:34:00Z",
        bodies=["Mars"],
        angles=["IC"],
    )

    line = payload["lines"][0]
    line_longitudes = {
        round(float(point[1]), 9)
        for segment in line["segments"]
        for point in segment
    }
    reading = build_location_reading(
        [line],
        latitude=0.0,
        longitude=-136.61213,
        limit=1,
    )

    assert payload["gst_deg"] == pytest.approx(332.093787, abs=5e-7)
    assert float(line["geometry"]["ra_deg"]) == pytest.approx(12.271030, abs=5e-7)
    assert len(line_longitudes) == 1
    assert next(iter(line_longitudes)) == pytest.approx(-139.822757, abs=5e-7)
    assert float(line["geometry"]["substellar_longitude_deg"]) == pytest.approx(
        40.177243123,
        abs=5e-9,
    )
    assert reading["nearest_lines"][0]["distance_km"] == pytest.approx(357.0, abs=0.1)


def test_build_lines_returns_rising_and_setting_curves():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Sun"],
        angles=["ASC", "DSC"],
    )

    ids = {line["id"] for line in payload["lines"]}
    assert "Sun:ASC" in ids
    assert "Sun:DSC" in ids


def test_generated_meridian_distance_is_spherical_at_high_latitude():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Sun"],
        angles=["MC"],
    )
    mc_line = payload["lines"][0]
    line_longitude = float(mc_line["geometry"]["substellar_longitude_deg"])
    query_longitude = ((line_longitude + 4.0 + 180.0) % 360.0) - 180.0

    reading = build_location_reading(
        [mc_line],
        latitude=80.0,
        longitude=query_longitude,
        limit=1,
    )

    assert reading["nearest_lines"][0]["distance_km"] == pytest.approx(77.2, abs=0.2)
    assert reading["nearest_lines"][0]["zone"] == "primary"
    assert reading["nearest_lines"][0]["signal_score"] == 92


def test_rising_curve_includes_and_scores_exact_circumpolar_tangent():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Sun"],
        angles=["ASC"],
    )
    asc_line = payload["lines"][0]
    geometry = asc_line["geometry"]
    northern_tangent = max(geometry["endpoints"], key=lambda point: point[0])

    assert northern_tangent[0] == pytest.approx(
        90.0 - abs(float(geometry["dec_deg"])),
        abs=1e-9,
    )
    assert northern_tangent[0] == pytest.approx(66.9415304295, abs=1e-8)
    assert northern_tangent[1] == pytest.approx(-179.2306457492, abs=1e-8)
    assert any(
        abs(float(point[0]) - northern_tangent[0]) < 1e-5
        and abs(float(point[1]) - northern_tangent[1]) < 1e-5
        for segment in asc_line["segments"]
        for point in segment
    )

    reading = build_location_reading(
        [asc_line],
        latitude=northern_tangent[0],
        longitude=northern_tangent[1],
        limit=1,
    )
    assert reading["nearest_lines"][0]["distance_km"] == 0.0
    assert reading["nearest_lines"][0]["zone"] == "primary"
    assert reading["nearest_lines"][0]["signal_score"] == 100


def test_setting_curve_inserts_paired_antimeridian_endpoints():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Moon"],
        angles=["DSC"],
    )
    dsc_line = payload["lines"][0]
    seam_points = [
        point
        for segment in dsc_line["segments"]
        for point in segment
        if abs(abs(float(point[1])) - 180.0) < 1e-9
    ]

    assert len(seam_points) == 2
    assert {float(point[1]) for point in seam_points} == {-180.0, 180.0}
    assert seam_points[0][0] == pytest.approx(66.511967, abs=1e-6)
    assert seam_points[1][0] == pytest.approx(seam_points[0][0], abs=1e-9)


def test_adaptive_display_polyline_stays_on_authoritative_half_arc():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Sun"],
        angles=["ASC"],
    )
    line = payload["lines"][0]
    normal = line["geometry"]["normal"]
    midpoint = line["geometry"]["midpoint"]

    for segment in line["segments"]:
        vectors = [
            astrocartography_service._latlon_to_unit(point[0], point[1])
            for point in segment
        ]
        for vector in vectors:
            assert abs(astrocartography_service._vector_dot(vector, normal)) < 2e-8
            assert astrocartography_service._vector_dot(vector, midpoint) >= -1e-8
        for start, end in zip(vectors, vectors[1:]):
            step_deg = math.degrees(
                astrocartography_service._angular_distance_rad(start, end)
            )
            assert step_deg <= 12.01


def test_build_lines_supports_chiron_filter_without_default_broadening():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Chiron"],
        angles=["MC"],
    )

    assert payload["bodies"] == ["Chiron"]
    assert {line["id"] for line in payload["lines"]} == {"Chiron:MC"}
    assert payload["calculation"]["degraded"] is False
    calculation = payload["calculation"]["bodies"]["Chiron"]
    assert calculation["returned_flags"] & astrocartography_service.swe.FLG_MOSEPH
    assert calculation["position_source"] == "moshier"
    assert calculation["position_source"] == calculation["ephemeris_engine"]
    assert calculation["position_source"] == astrocartography_service._ephemeris_engine_from_flags(
        calculation["returned_flags"]
    )
    assert calculation["orbital_data_source"] == "swiss-ephemeris-asteroid-file"
    assert calculation["object_type"] == "centaur"
    assert calculation["astrocartography_scope"] == "experimental_extension"
    assert calculation["extension_status"] == "experimental"
    assert calculation["doctrine_scope"] == "secondary_extension"
    assert calculation["ranking_eligibility_scope"] == (
        "astronomical_geometry_quality_only"
    )


def test_extended_bodies_self_describe_node_type_and_experimental_status():
    payload = build_astrocartography_lines(
        "2000-02-29T11:34:00Z",
        bodies=["North Node", "Chiron"],
        angles=["MC"],
    )
    calculations = payload["calculation"]["bodies"]
    node = calculations["North Node"]
    chiron = calculations["Chiron"]

    assert node["object_type"] == "calculated_lunar_node"
    assert node["node_type"] == "mean_node"
    assert node["node_polarity"] == "ascending"
    assert node["astrocartography_scope"] == "experimental_extension"
    assert node["extension_status"] == "experimental"
    assert node["doctrine_scope"] == "secondary_extension"
    assert "Mean North Node" in node["extension_note"]

    assert chiron["object_type"] == "centaur"
    assert chiron["astrocartography_scope"] == "experimental_extension"
    assert chiron["extension_status"] == "experimental"
    assert chiron["doctrine_scope"] == "secondary_extension"
    assert "Chiron lines" in chiron["extension_note"]

    for line in payload["lines"]:
        calculation = line["calculation"]
        assert calculation["astrocartography_scope"] == "experimental_extension"
        assert calculation["extension_status"] == "experimental"

    reading = build_location_reading(
        payload["lines"],
        latitude=0.0,
        longitude=0.0,
        limit=2,
    )
    for item in reading["nearest_lines"]:
        assert item["interpretation_method"] == "explicit_planet_angle_matrix"
        assert item["interpretation_status"] == "curated_experimental_extension"
        assert item["doctrine_scope"] == "secondary_extension"
        assert item["model_status"] == "experimental_extension"


@pytest.mark.parametrize(
    ("year", "expected_ra_deg"),
    [
        (1900, 258.341695),
        (1950, 255.056557),
        (2024, 13.713121),
    ],
)
def test_chiron_lines_use_bundled_ephemeris_across_natal_dates(year, expected_ra_deg):
    payload = build_astrocartography_lines(
        f"{year:04d}-01-01T00:00:00Z",
        bodies=["Chiron"],
        angles=["MC"],
    )
    line = payload["lines"][0]

    assert float(line["geometry"]["ra_deg"]) == pytest.approx(expected_ra_deg, abs=1e-5)
    assert line["calculation"]["degraded"] is False
    assert line["calculation"]["accuracy"] == "ephemeris"
    assert line["calculation"]["ranking_eligible"] is True


def test_chiron_fallback_is_explicitly_marked_degraded(monkeypatch, tmp_path):
    monkeypatch.setattr(
        astrocartography_service,
        "_resolve_astrocartography_ephemeris_path",
        lambda: str(tmp_path),
    )

    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Chiron"],
        angles=["MC"],
    )
    calculation = payload["calculation"]["bodies"]["Chiron"]

    assert payload["calculation"]["degraded"] is True
    assert calculation["degraded"] is True
    assert calculation["accuracy"] == "low"
    assert calculation["ranking_eligible"] is False
    assert calculation["position_source"] == "jpl-elements-two-body-fallback"
    assert calculation["astrocartography_scope"] == "experimental_extension"
    assert calculation["extension_status"] == "experimental"
    assert calculation["doctrine_scope"] == "secondary_extension"
    assert "experimental extension" in calculation["extension_note"]


def test_build_lines_does_not_broaden_invalid_body_filter():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Unsupported Body"],
        angles=["MC"],
    )

    assert payload["bodies"] == []
    assert payload["lines"] == []


def test_nearest_lines_for_point_orders_by_distance():
    lines = [
        {
            "id": "Sun:MC",
            "body": "Sun",
            "angle": "MC",
            "label": "Sun MC",
            "color": "#f59e0b",
            "segments": [[[-50.0, 0.0], [50.0, 0.0]]],
        },
        {
            "id": "Moon:MC",
            "body": "Moon",
            "angle": "MC",
            "label": "Moon MC",
            "color": "#2563eb",
            "segments": [[[-50.0, 30.0], [50.0, 30.0]]],
        },
    ]

    ranked = nearest_lines_for_point(lines, latitude=0.0, longitude=4.0, limit=2)
    assert [row["id"] for row in ranked] == ["Sun:MC", "Moon:MC"]
    assert ranked[0]["distance_km"] < ranked[1]["distance_km"]


def test_goal_scoring_context_keeps_rows_beyond_display_limit():
    lines = [
        {
            "id": f"Body{index}:MC",
            "body": f"Body{index}",
            "angle": "MC",
            "label": f"Body{index} MC",
            "segments": [[[-20.0, float(index)], [20.0, float(index)]]],
        }
        for index in range(9)
    ]

    display_reading = build_location_reading(lines, latitude=0.0, longitude=0.0)
    scoring_context = build_goal_scoring_context(lines, latitude=0.0, longitude=0.0)

    assert len(display_reading["nearest_lines"]) == 8
    assert len(scoring_context["nearest_lines"]) == 9
    assert "Body8:MC" in {row["id"] for row in scoring_context["nearest_lines"]}
    assert display_reading["zone_counts_scope"] == "all_evaluated_lines"
    assert display_reading["evaluated_line_count"] == 9
    assert display_reading["displayed_line_count"] == 8
    assert sum(display_reading["zone_counts"].values()) == 9
    assert sum(display_reading["displayed_zone_counts"].values()) == 8


def test_goal_scoring_context_collects_wide_crossings_but_keeps_display_zone_policy(monkeypatch):
    captured = {}

    def fake_crossings(*args, **kwargs):
        captured["max_distance_km"] = kwargs["max_distance_km"]
        return [
            {
                "id": "Sun:MC|Moon:IC",
                "kind": "crossing",
                "planets": ["Sun", "Moon"],
                "distance_km": 650.0,
                "zone": "extended",
            }
        ]

    monkeypatch.setattr(
        astrocartography_service,
        "crossing_candidates_for_point",
        fake_crossings,
    )
    astrocartography_service._goal_scoring_sensitivity_radius_km.cache_clear()
    context = build_goal_scoring_context(
        [
            {
                "id": "Sun:MC",
                "body": "Sun",
                "angle": "MC",
                "label": "Sun MC",
                "segments": [[[-20.0, 0.0], [20.0, 0.0]]],
            },
            {
                "id": "Moon:IC",
                "body": "Moon",
                "angle": "IC",
                "label": "Moon IC",
                "segments": [[[-20.0, 1.0], [20.0, 1.0]]],
            },
        ],
        latitude=0.0,
        longitude=0.0,
    )

    assert captured["max_distance_km"] == pytest.approx(700.0)
    assert context["standard_cutoff_km"] == 500.0
    assert context["sensitivity_cutoff_km"] == 700.0
    assert context["crossings"][0]["zone"] == "background"


def test_nearest_lines_for_point_wraps_antimeridian_distance():
    lines = [
        {
            "id": "Sun:MC",
            "body": "Sun",
            "angle": "MC",
            "label": "Sun MC",
            "color": "#f59e0b",
            "segments": [[[-50.0, 179.0], [50.0, 179.0]]],
        },
    ]

    ranked = nearest_lines_for_point(lines, latitude=0.0, longitude=-179.0, limit=1)
    reading = build_location_reading(lines, latitude=0.0, longitude=-179.0, limit=1)

    assert ranked[0]["distance_km"] < 230.0
    assert reading["nearest_lines"][0]["zone"] == "primary"


def test_build_location_reading_enriches_lines_with_signal_and_copy():
    lines = [
        {
            "id": "Sun:MC",
            "body": "Sun",
            "angle": "MC",
            "label": "Sun MC",
            "color": "#f59e0b",
            "segments": [[[-50.0, 0.0], [50.0, 0.0]]],
        },
        {
            "id": "Moon:IC",
            "body": "Moon",
            "angle": "IC",
            "label": "Moon IC",
            "color": "#2563eb",
            "segments": [[[-50.0, 2.0], [50.0, 2.0]]],
        },
    ]

    reading = build_location_reading(lines, latitude=0.0, longitude=0.5, limit=2)

    assert reading["signal_score"] > 0
    assert reading["reading_mode"]["id"] == "neutral_line_overview"
    assert reading["reading_mode"]["ranked"] is False
    assert reading["lead_line"]["id"] == "Sun:MC"
    assert "Sun MC is the clearest nearby line" in reading["headline"]
    assert reading["nearest_lines"][0]["zone"] == "primary"
    assert reading["nearest_lines"][0]["signal_score"] >= reading["nearest_lines"][1]["signal_score"]
    assert "purpose" in reading["nearest_lines"][0]["summary"]
    assert reading["nearest_lines"][0]["interpretation_method"] == "explicit_planet_angle_matrix"
    assert reading["nearest_lines"][0]["interpretation_status"] == "curated_supported_matrix"
    assert reading["nearest_lines"][0]["doctrine_scope"] == "core_planet_line"
    assert "Moon IC" in reading["support_note"]
    assert "Nesting, kinship" in reading["support_note"]


def test_mars_ic_uses_explicit_home_and_roots_semantics():
    lines = [
        {
            "id": "Mars:IC",
            "body": "Mars",
            "angle": "IC",
            "label": "Mars IC",
            "color": "#ef4444",
            "segments": [[[-50.0, 0.0], [50.0, 0.0]]],
        }
    ]

    reading = build_location_reading(lines, latitude=0.0, longitude=0.0, limit=1)
    mars_ic = reading["nearest_lines"][0]
    wording = " ".join(
        [
            str(mars_ic["summary"]),
            str(mars_ic["upside_note"]),
            str(mars_ic["caution"]),
        ]
    ).lower()

    assert mars_ic["interpretation_method"] == "explicit_planet_angle_matrix"
    assert mars_ic["interpretation_status"] == "curated_supported_matrix"
    assert mars_ic["doctrine_scope"] == "core_planet_line"
    assert all(term in wording for term in ("home", "roots", "foundations"))
    assert all(term in wording for term in ("restlessness", "abrasion"))
    assert "athletic drive" not in wording


def test_unsupported_line_truthfully_reports_generic_fallback():
    lines = [
        {
            "id": "Ceres:IC",
            "body": "Ceres",
            "angle": "IC",
            "label": "Ceres IC",
            "color": "#64748b",
            "segments": [[[-50.0, 0.0], [50.0, 0.0]]],
        }
    ]

    reading = build_location_reading(lines, latitude=0.0, longitude=0.0, limit=1)
    fallback = reading["nearest_lines"][0]

    assert fallback["interpretation_method"] == "generic_planet_plus_angle_fallback"
    assert fallback["interpretation_status"] == "generic_unsupported_fallback"
    assert fallback["doctrine_scope"] == "unsupported_extension"


def test_build_location_reading_marks_background_locations():
    lines = [
        {
            "id": "Venus:ASC",
            "body": "Venus",
            "angle": "ASC",
            "label": "Venus ASC",
            "color": "#ec4899",
            "segments": [[[-50.0, 40.0], [50.0, 40.0]]],
        },
    ]

    reading = build_location_reading(lines, latitude=0.0, longitude=-80.0, limit=1)

    assert reading["nearest_lines"][0]["zone"] == "background"
    assert "comparatively quiet" in reading["headline"]


def test_extended_location_copy_does_not_call_a_background_support_line_nearby():
    lines = [
        {
            "id": "Mars:IC",
            "body": "Mars",
            "angle": "IC",
            "label": "Mars IC",
            "segments": [[[-50.0, 4.0], [50.0, 4.0]]],
        },
        {
            "id": "Jupiter:MC",
            "body": "Jupiter",
            "angle": "MC",
            "label": "Jupiter MC",
            "segments": [[[-50.0, 10.0], [50.0, 10.0]]],
        },
    ]

    reading = build_location_reading(lines, latitude=0.0, longitude=0.0, limit=2)

    assert reading["lead_line"]["zone"] == "extended"
    assert reading["support_line"]["zone"] == "background"
    assert "next background line" in reading["support_note"]
    assert "nearby" not in reading["support_note"].lower()


def test_primary_location_copy_labels_a_background_fallback_as_non_reinforcing():
    lines = [
        {
            "id": "Sun:MC",
            "body": "Sun",
            "angle": "MC",
            "label": "Sun MC",
            "segments": [[[-50.0, 0.0], [50.0, 0.0]]],
        },
        {
            "id": "Saturn:IC",
            "body": "Saturn",
            "angle": "IC",
            "label": "Saturn IC",
            "segments": [[[-50.0, 10.0], [50.0, 10.0]]],
        },
    ]

    reading = build_location_reading(lines, latitude=0.0, longitude=0.0, limit=2)

    assert reading["lead_line"]["zone"] == "primary"
    assert reading["support_line"]["zone"] == "background"
    assert reading["support_note"] == (
        "Saturn IC is the next background line, outside the extended field rather than a reinforcing line."
    )


def test_crossing_candidates_for_point_detects_exact_intersection():
    lines = [
        {
            "id": "Sun:MC",
            "body": "Sun",
            "angle": "MC",
            "label": "Sun MC",
            "segments": [[[-20.0, 0.0], [20.0, 0.0]]],
        },
        {
            "id": "Venus:ASC",
            "body": "Venus",
            "angle": "ASC",
            "label": "Venus ASC",
            "segments": [[[0.0, -20.0], [0.0, 20.0]]],
        },
    ]
    nearest = nearest_lines_for_point(lines, latitude=1.0, longitude=1.0, limit=2)

    crossings = crossing_candidates_for_point(lines, latitude=1.0, longitude=1.0, nearest_rows=nearest, limit=2)

    assert crossings
    assert crossings[0]["kind"] == "crossing"
    assert set(crossings[0]["planets"]) == {"Sun", "Venus"}


def test_generated_crossing_is_exact_and_dateline_safe():
    timestamp = "2024-01-01T00:00:00Z"
    expected_point = [66.968932, -179.230646]
    payload = build_astrocartography_lines(
        timestamp,
        bodies=["Sun", "Moon"],
        angles=["MC", "DSC"],
    )
    nearest = nearest_lines_for_point(
        payload["lines"],
        latitude=expected_point[0],
        longitude=expected_point[1],
        limit=8,
    )

    crossings = crossing_candidates_for_point(
        payload["lines"],
        latitude=expected_point[0],
        longitude=expected_point[1],
        nearest_rows=nearest,
        limit=8,
        max_distance_km=1200.0,
    )
    crossing = next(
        item
        for item in crossings
        if item["canonical_event_id"] == "angular-event:Moon:DSC|Sun:MC"
    )

    assert crossing["kind"] == "crossing"
    assert crossing["event_kind"] == "angular-line-crossing"
    assert crossing["distance_km"] == 0.0
    assert crossing["point"][0] == pytest.approx(expected_point[0], abs=1e-6)
    assert crossing["point"][1] == pytest.approx(expected_point[1], abs=1e-6)


def test_build_intersection_workspace_surfaces_geometry_points():
    lines = [
        {
            "id": "Sun:MC",
            "body": "Sun",
            "angle": "MC",
            "label": "Sun MC",
            "segments": [[[-20.0, 0.0], [20.0, 0.0]]],
        },
        {
            "id": "Venus:ASC",
            "body": "Venus",
            "angle": "ASC",
            "label": "Venus ASC",
            "segments": [[[0.0, -20.0], [0.0, 20.0]]],
        },
    ]

    workspace = build_intersection_workspace(lines, latitude=1.0, longitude=1.0)

    assert workspace["exact_count"] >= 1
    assert workspace["geometry_points"]
    assert set(workspace["primary_crossings"][0]["planets"]) == {"Sun", "Venus"}
    assert workspace["geometry_points"][0]["canonical_event_id"] == "angular-event:Sun:MC|Venus:ASC"
    assert workspace["geometry_points"][0]["event_kind"] == "angular-line-crossing"


def test_build_local_space_rays_returns_visible_and_hidden_sets():
    payload = build_local_space_rays(
        "2024-01-01T00:00:00Z",
        latitude=51.5074,
        longitude=-0.1278,
        bodies=["Sun", "Moon"],
        max_distance_km=600,
        step_km=300,
    )

    assert payload["rays"]
    assert payload["visible_count"] + payload["hidden_count"] == len(payload["rays"])
    assert payload["rays"][0]["segments"]


def test_build_local_space_workspace_adds_sectors_and_rings():
    payload = build_local_space_workspace(
        "2024-01-01T00:00:00Z",
        latitude=51.5074,
        longitude=-0.1278,
        bodies=["Sun", "Moon", "Venus"],
        max_distance_km=1500,
        step_km=300,
    )

    assert payload["range_rings_km"] == [500, 1500]
    assert "peak_rays" in payload
    assert "shadow_rays" in payload
    assert payload["rays"][0]["summary"]
    assert "deg" in payload["rays"][0]["summary"]
    if payload["dominant_sectors"]:
        assert payload["dominant_sectors"][0]["sector"]
        assert payload["dominant_sectors"][0]["count"] >= 1


def test_build_paran_candidates_for_point_detects_matching_event_pair():
    payload = build_paran_candidates_for_point(
        "2024-01-01T00:00:00Z",
        latitude=51.5074,
        longitude=-0.1278,
        bodies=["Sun", "Moon", "Venus", "Mars"],
        limit=8,
        max_distance_km=40075.0,
        orb_deg=30.0,
    )

    assert "items" in payload
    assert payload["count"] >= len(payload["items"])
    if payload["items"]:
        assert payload["items"][0]["kind"] == "paran"
        assert {"ASC", "DSC", "MC", "IC"} >= {payload["items"][0]["angle_a"], payload["items"][0]["angle_b"]}


def test_point_paran_uses_exact_root_and_canonical_crossing_identity():
    expected_point = [66.968932, -179.230646]
    payload = build_paran_candidates_for_point(
        "2024-01-01T00:00:00Z",
        latitude=expected_point[0],
        longitude=expected_point[1],
        bodies=["Moon", "Sun"],
        limit=8,
        max_distance_km=1200.0,
        orb_deg=0.01,
    )
    paran = next(
        item
        for item in payload["items"]
        if item["canonical_event_id"] == "angular-event:Moon:DSC|Sun:MC"
    )

    assert payload["calculation_mode"] == "analytic-spherical-root"
    assert paran["event_kind"] == "paran-crossing-point"
    assert paran["root_residual_deg"] < 1e-7
    assert paran["distance_km"] == 0.0
    assert paran["point"][0] == pytest.approx(expected_point[0], abs=1e-6)
    assert paran["point"][1] == pytest.approx(expected_point[1], abs=1e-6)


def test_build_global_paran_tracks_returns_track_payload():
    payload = build_global_paran_tracks(
        "2024-01-01T00:00:00Z",
        bodies=["Sun", "Moon", "Venus", "Mars"],
        orb_deg=15.0,
        limit=12,
        min_points=3,
    )

    assert "tracks" in payload
    assert payload["track_count"] >= len(payload["tracks"])
    if payload["tracks"]:
        assert payload["tracks"][0]["kind"] == "global-paran"
        assert payload["tracks"][0]["segments"]


def test_global_parans_are_exact_latitude_roots_not_sample_bands():
    payload = build_global_paran_tracks(
        "2024-01-01T00:00:00Z",
        bodies=["Sun", "Moon"],
        orb_deg=0.01,
        limit=20,
        min_points=999,
    )
    track = next(
        item
        for item in payload["tracks"]
        if item["canonical_event_id"] == "angular-event:Moon:DSC|Sun:MC"
    )

    assert payload["calculation_mode"] == "analytic-spherical-root"
    assert payload["latitude_step_deg"] == 0
    assert payload["track_count"] == 4
    assert track["event_kind"] == "paran-latitude-corridor"
    assert track["root_residual_deg"] < 1e-7
    assert track["root_point"][0] == pytest.approx(66.968932, abs=1e-6)
    assert track["root_point"][1] == pytest.approx(-179.230646, abs=1e-6)
    assert all(
        float(point[0]) == pytest.approx(66.968932, abs=1e-6)
        for segment in track["segments"]
        for point in segment
    )


def test_build_delineation_report_returns_cards_and_sections():
    reading = build_location_reading(
        [
            {
                "id": "Sun:MC",
                "body": "Sun",
                "angle": "MC",
                "label": "Sun MC",
                "color": "#f59e0b",
                "segments": [[[-50.0, 0.0], [50.0, 0.0]]],
            }
        ],
        latitude=0.0,
        longitude=0.0,
    )
    intersections = {
        "headline": "Sun MC x Venus ASC is the clearest nearby intersection field.",
        "lead_intersection": {"label": "Sun MC x Venus ASC", "distance_km": 42.0},
        "primary_crossings": [{"label": "Sun MC x Venus ASC", "kind": "crossing", "distance_km": 42.0}],
    }
    local_space = {
        "headline": "Local Space is led by Sun toward E.",
        "rays": [{"id": "Sun:local-space", "label": "Sun Local Space", "direction_label": "E", "azimuth_deg": 90.0, "altitude_deg": 30.0, "above_horizon": True}],
    }
    relocation = {
        "headline": "Relocation is led by Venus DSC.",
        "angular_planets": [{"planet": "Venus", "angle": "DSC"}],
        "prominent_houses": [{"house": 7, "planets": ["Venus"]}],
        "metrics": {"home_base": 0.3, "career_status": 0.4},
        "support_notes": ["Career Status 40 / 100"],
        "caution_notes": [],
    }
    goal_evaluation = {
        "goal": {"label": "Love"},
        "score": 72,
        "top_supports": [{"label": "Venus DSC", "rationale": "Supports warmth."}],
        "top_cautions": [{"label": "Saturn DSC", "rationale": "Can cool the field."}],
    }

    report = build_delineation_report(
        target_label="London, United Kingdom",
        natal_reading=reading,
        natal_intersections=intersections,
        natal_parans={"headline": "Moon ASC paran Venus MC is the clearest nearby paran.", "lead_paran": {"label": "Moon ASC paran Venus MC", "distance_km": 18.0, "orb_deg": 0.8}, "items": [{"label": "Moon ASC paran Venus MC", "distance_km": 18.0, "orb_deg": 0.8}]},
        natal_local_space=local_space,
        relocation_summary=relocation,
        goal_evaluation=goal_evaluation,
    )

    assert report["cards"]
    assert any(card["id"] == "paran" for card in report["cards"])
    assert any(section["id"] == "local-space" for section in report["sections"])
    assert any(section["id"] == "parans" for section in report["sections"])
    assert "Current PathFinder score: 72." in report["headline"]


def test_runtime_assets_are_loaded_from_knowledge_base_output():
    payload = load_astrocartography_assets()

    assert payload["range_policy"]["primary_radius_km"] == 300
    assert payload["range_policy"]["extended_radius_km"] == 500
    assert payload["bodies"]["Sun"]["core_themes"] == "identity, vitality, purpose"
    assert payload["angles"]["MC"]["user_shorthand"] == "how I am classified publicly here"
    assert len(payload["line_interpretations"]) == 48
    assert "home, roots, family, and private foundations" in payload[
        "line_interpretations"
    ]["Mars:IC"]["summary"]
