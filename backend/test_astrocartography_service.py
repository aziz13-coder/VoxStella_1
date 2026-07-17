from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

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


def test_build_lines_returns_rising_and_setting_curves():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Sun"],
        angles=["ASC", "DSC"],
    )

    ids = {line["id"] for line in payload["lines"]}
    assert "Sun:ASC" in ids
    assert "Sun:DSC" in ids


def test_build_lines_supports_chiron_filter_without_default_broadening():
    payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Chiron"],
        angles=["MC"],
    )

    assert payload["bodies"] == ["Chiron"]
    assert {line["id"] for line in payload["lines"]} == {"Chiron:MC"}


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
    assert reading["lead_line"]["id"] == "Sun:MC"
    assert "Sun MC is the clearest nearby line" in reading["headline"]
    assert reading["nearest_lines"][0]["zone"] == "primary"
    assert reading["nearest_lines"][0]["signal_score"] >= reading["nearest_lines"][1]["signal_score"]
    assert "identity, vitality, purpose" in reading["nearest_lines"][0]["summary"]
    assert "Moon IC" in reading["support_note"]
    assert "intuition, family ties, receptivity" in reading["support_note"]


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
    assert payload["angles"]["MC"]["user_shorthand"] == "what I do here"
