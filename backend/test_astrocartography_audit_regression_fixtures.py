from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent))

import astrocartography_service
from astrocartography_goal_engine import (
    evaluate_goal_model,
    extract_relocation_features,
)
from astrocartography_service import (
    build_astrocartography_lines,
    build_global_paran_tracks,
    build_local_space_workspace,
    build_location_reading,
    build_paran_candidates_for_point,
    crossing_candidates_for_point,
    nearest_lines_for_point,
)
from swisseph_state import swisseph_ephemeris_path


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "benchmarks"
    / "astrocartography"
    / "audit_regression_fixtures.json"
)
CLAIM_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1]
    / "horary_knowledge"
    / "astrocartography_sources"
    / "claim_registry.json"
)


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _wrap180(value: float) -> float:
    wrapped = float(value) % 360.0
    return wrapped - 360.0 if wrapped > 180.0 else wrapped


def _equator_longitude(line: dict) -> float:
    geometry = line["geometry"]
    longitude = float(geometry["substellar_longitude_deg"])
    angle = str(line["angle"]).upper()
    if angle == "IC":
        longitude += 180.0
    elif angle == "ASC":
        longitude -= 90.0
    elif angle == "DSC":
        longitude += 90.0
    return _wrap180(longitude)


def _circular_delta_deg(left: float, right: float) -> float:
    return abs(_wrap180(float(left) - float(right)))


def test_synthetic_civil_time_converts_to_the_frozen_utc_instant() -> None:
    fixture = _fixture()
    birth = fixture["birth"]
    assert fixture["synthetic_fixture"] is True
    assert birth["fixture_status"] == "synthetic_non_person"
    local = datetime.fromisoformat(birth["local_civil_datetime"]).replace(
        tzinfo=ZoneInfo(birth["timezone"])
    )

    assert local.utcoffset().total_seconds() == 60 * 60
    assert (
        local.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
        == birth["utc_datetime"]
    )


def test_fixture_product_policies_link_to_governed_experimental_claims() -> None:
    fixture = _fixture()
    registry = json.loads(
        CLAIM_REGISTRY_PATH.read_text(encoding="utf-8")
    )
    claims = {
        row["claim_id"]: row
        for row in registry["claims"]
    }

    for policy in fixture["policies"].values():
        claim_id = policy["claim_id"]
        assert claim_id in claims
        assert claims[claim_id]["classification"] == "experimental"
        assert claims[claim_id]["evidence_limitations"]


def test_synthetic_paris_line_geometry_and_nearest_lines_match_fixture() -> None:
    fixture = _fixture()
    birth = fixture["birth"]
    expected = fixture["voxstella_expected"]
    payload = build_astrocartography_lines(birth["utc_datetime"])
    by_id = {line["id"]: line for line in payload["lines"]}

    assert len(payload["lines"]) == expected["line_count_with_extensions"]
    assert payload["gst_deg"] == pytest.approx(expected["gst_deg"], abs=1e-6)
    for line_id, longitude in expected["line_longitudes_at_equator"].items():
        assert _equator_longitude(by_id[line_id]) == pytest.approx(
            longitude,
            abs=2e-6,
        )

    place = birth["place"]
    reading = build_location_reading(
        payload["lines"],
        latitude=place["latitude"],
        longitude=place["longitude"],
        limit=8,
    )
    expected_reading = expected["synthetic_paris_reading"]
    assert reading["zone_counts_scope"] == "all_evaluated_lines"
    assert reading["evaluated_line_count"] == 48
    assert reading["zone_counts"] == expected_reading["zone_counts_all_48_lines"]
    for observed, frozen in zip(
        reading["nearest_lines"],
        expected_reading["nearest"],
    ):
        assert observed["id"] == frozen["id"]
        assert observed["distance_km"] == pytest.approx(
            frozen["distance_km"],
            abs=0.2,
        )
        assert observed["zone"] == frozen["zone"]


def test_mars_ic_wording_uses_home_foundation_doctrine() -> None:
    fixture = _fixture()
    wording_policy = fixture["mars_ic_wording"]
    reading = build_location_reading(
        [
            {
                "id": "Mars:IC",
                "body": "Mars",
                "angle": "IC",
                "label": "Mars IC",
                "segments": [[[-50.0, 0.0], [50.0, 0.0]]],
            }
        ],
        latitude=0.0,
        longitude=0.0,
        limit=1,
    )
    row = reading["nearest_lines"][0]
    wording = " ".join(
        [
            str(row.get("summary") or ""),
            str(row.get("upside_note") or ""),
            str(row.get("caution") or ""),
        ]
    ).lower()

    assert row["interpretation_method"] == "explicit_planet_angle_matrix"
    assert all(term in wording for term in wording_policy["required_terms"])
    assert all(
        term not in wording
        for term in wording_policy["forbidden_primary_framing"]
    )


def test_display_boundaries_and_wide_policy_are_explicit() -> None:
    fixture = _fixture()
    policy = fixture["policies"]["distance"]

    for boundary in policy["boundary_expectations"]:
        assert astrocartography_service._distance_zone(
            boundary["distance_km"],
            primary_radius_km=policy["display_primary_radius_km"],
            extended_radius_km=policy["display_extended_radius_km"],
        ) == boundary["display_zone"]

    assert policy["profile_multipliers"]["standard"] == 1.0
    assert policy["profile_effective_cutoffs_km"] == {
        "conservative": 300.0,
        "standard": 500.0,
        "wide": 700.0,
    }
    assert (
        policy["display_extended_radius_km"]
        * policy["profile_multipliers"]["wide"]
        == pytest.approx(
            policy["profile_effective_cutoffs_km"]["wide"]
        )
    )
    distance_probe = fixture["voxstella_expected"]["synthetic_distance_probe"]
    assert distance_probe["distance_km"] > 300.0
    evaluation = evaluate_goal_model(
        "home",
        natal_rows=[
            {
                "id": distance_probe["id"],
                "body": "Mars",
                "angle": "IC",
                "label": "Mars IC",
                "distance_km": distance_probe["distance_km"],
                "zone": distance_probe["zone"],
            }
        ],
        natal_crossings=[],
        relocation=extract_relocation_features({"planets": {}}),
    )
    sensitivity = evaluation["uncertainty"]["distance_sensitivity"]
    assert sensitivity["policy"]["primary_boundary_km"] == (
        policy["display_primary_radius_km"]
    )
    assert sensitivity["policy"]["standard_cutoff_km"] == (
        policy["display_extended_radius_km"]
    )
    assert sensitivity["policy"]["profile_multipliers"] == (
        policy["profile_multipliers"]
    )

    expected_active = {
        "conservative": distance_probe["conservative_profile_active"],
        "standard": distance_probe["standard_profile_active"],
        "wide": distance_probe["wide_profile_active"],
    }
    for profile_name, expected_cutoff in policy[
        "profile_effective_cutoffs_km"
    ].items():
        profile = sensitivity["profiles"][profile_name]
        mars_ic = next(
            item
            for item in profile["distance_evidence"]
            if item["component_id"] == "home.line.04"
        )
        assert mars_ic["effective_max_km"] == expected_cutoff
        assert mars_ic["active"] is expected_active[profile_name]


def test_local_space_keeps_origin_and_technique_identity_separate() -> None:
    fixture = _fixture()
    birth = fixture["birth"]
    expected = fixture["voxstella_expected"]["local_space_canonical_ten"]
    policy = fixture["policies"]["local_space"]
    place = birth["place"]
    workspace = build_local_space_workspace(
        birth["utc_datetime"],
        latitude=place["latitude"],
        longitude=place["longitude"],
        bodies=policy["separate_from_astrocartography_lines"]
        and fixture["policies"]["body_scope"]["canonical"],
    )

    assert workspace["origin"]["latitude"] == expected["origin"]["latitude"]
    assert workspace["origin"]["longitude"] == expected["origin"]["longitude"]
    assert workspace["rays"][0]["body"] == expected["lead_body"]
    assert workspace["rays"][0]["direction_label"] == expected["lead_direction"]
    assert workspace["rays"][0]["azimuth_deg"] == pytest.approx(
        expected["lead_azimuth_deg"],
        abs=0.02,
    )
    assert workspace["rays"][0]["altitude_deg"] == pytest.approx(
        expected["lead_altitude_deg"],
        abs=0.02,
    )
    assert all(
        str(ray["id"]).endswith(
            fixture["technique_identity"]["local_space_id_suffix"]
        )
        for ray in workspace["rays"]
    )
    assert all("angle" not in ray for ray in workspace["rays"])


def test_crossing_point_paran_corridor_and_local_space_are_not_conflated() -> None:
    fixture = _fixture()
    identities = fixture["technique_identity"]
    expected_point = [66.968932, -179.230646]
    lines_payload = build_astrocartography_lines(
        "2024-01-01T00:00:00Z",
        bodies=["Sun", "Moon"],
        angles=["MC", "DSC"],
    )
    nearest = nearest_lines_for_point(
        lines_payload["lines"],
        latitude=expected_point[0],
        longitude=expected_point[1],
        limit=8,
    )
    crossing = next(
        item
        for item in crossing_candidates_for_point(
            lines_payload["lines"],
            latitude=expected_point[0],
            longitude=expected_point[1],
            nearest_rows=nearest,
            limit=8,
            max_distance_km=1200.0,
        )
        if item["canonical_event_id"] == "angular-event:Moon:DSC|Sun:MC"
    )
    local_paran = next(
        item
        for item in build_paran_candidates_for_point(
            "2024-01-01T00:00:00Z",
            latitude=expected_point[0],
            longitude=expected_point[1],
            bodies=["Moon", "Sun"],
            limit=8,
            max_distance_km=fixture["policies"]["parans"][
                "local_search_radius_km"
            ],
            orb_deg=fixture["policies"]["parans"][
                "local_residual_limit_deg"
            ],
        )["items"]
        if item["canonical_event_id"] == "angular-event:Moon:DSC|Sun:MC"
    )
    global_paran = next(
        item
        for item in build_global_paran_tracks(
            "2024-01-01T00:00:00Z",
            bodies=["Moon", "Sun"],
            orb_deg=fixture["policies"]["parans"][
                "global_residual_limit_deg"
            ],
            limit=20,
        )["tracks"]
        if item["canonical_event_id"] == "angular-event:Moon:DSC|Sun:MC"
    )

    assert crossing["event_kind"] == identities[
        "angular_line_crossing_event_kind"
    ]
    assert local_paran["event_kind"] == identities[
        "local_paran_event_kind"
    ]
    assert global_paran["event_kind"] == identities[
        "global_paran_event_kind"
    ]
    assert len(
        {
            crossing["event_kind"],
            local_paran["event_kind"],
            global_paran["event_kind"],
        }
    ) == 3


def test_time_perturbation_fixture_tracks_angle_and_line_motion() -> None:
    fixture = _fixture()
    place = fixture["birth"]["place"]
    samples = fixture["time_perturbation"]["samples"]
    observed_mars_longitudes = []

    for sample in samples:
        jd_ut1 = astrocartography_service._jd_ut_from_iso(
            sample["utc_datetime"]
        )
        houses, ascmc = astrocartography_service.swe.houses(
            jd_ut1,
            place["latitude"],
            place["longitude"],
            b"R",
        )
        assert len(houses) == 12
        assert ascmc[0] == pytest.approx(
            sample["ascendant_deg"],
            abs=2e-7,
        )
        assert ascmc[1] == pytest.approx(
            sample["midheaven_deg"],
            abs=2e-7,
        )
        line = build_astrocartography_lines(
            sample["utc_datetime"],
            bodies=["Mars"],
            angles=["IC"],
        )["lines"][0]
        longitude = _equator_longitude(line)
        observed_mars_longitudes.append(longitude)
        assert longitude == pytest.approx(
            sample["mars_ic_equator_longitude_deg"],
            abs=2e-6,
        )

    assert observed_mars_longitudes[0] > observed_mars_longitudes[1]
    assert observed_mars_longitudes[1] > observed_mars_longitudes[2]
    assert fixture["time_perturbation"]["rank_stability_requirement"].startswith(
        "A ranked multi-location result"
    )


def test_frozen_synthetic_almaatla_constants_match_without_loading_binary() -> None:
    fixture = _fixture()["almaatla_kernel_parity"]
    assert fixture["binary_needed_at_test_time"] is False
    assert fixture["kernel_input"]["fixture_status"] == "synthetic_non_person"
    jd_ut = fixture["kernel_input"]["julian_day_ut"]
    maximum_delta_arcsec = fixture["maximum_longitude_delta_arcsec"]
    ephemeris_path = (
        astrocartography_service._resolve_astrocartography_ephemeris_path()
        or ""
    )

    with swisseph_ephemeris_path(
        ephemeris_path,
        swe_module=astrocartography_service.swe,
    ):
        for body, expected_longitude in fixture[
            "planetary_longitudes_deg"
        ].items():
            position, _returned_flags = astrocartography_service.swe.calc_ut(
                jd_ut,
                astrocartography_service.PLANET_IDS[body],
                astrocartography_service.swe.FLG_MOSEPH,
            )
            assert (
                _circular_delta_deg(position[0], expected_longitude) * 3600.0
                <= maximum_delta_arcsec
            )

    houses, ascmc = astrocartography_service.swe.houses(
        jd_ut,
        fixture["kernel_input"]["latitude"],
        fixture["kernel_input"]["longitude"],
        b"R",
    )
    expected_houses = fixture["houses"]
    assert (
        _circular_delta_deg(
            ascmc[0],
            expected_houses["ascendant_deg"],
        )
        * 3600.0
        <= maximum_delta_arcsec
    )
    assert (
        _circular_delta_deg(
            ascmc[1],
            expected_houses["midheaven_deg"],
        )
        * 3600.0
        <= maximum_delta_arcsec
    )
    for observed, expected in zip(
        houses,
        expected_houses["cusps_deg"],
    ):
        assert (
            _circular_delta_deg(observed, expected) * 3600.0
            <= maximum_delta_arcsec
        )
