from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent))

from astrocartography_service import build_astrocartography_lines
import astrocartography_atlas_engine as atlas_engine
from astrocartography_uncertainty import (
    apply_cross_location_rank_stability,
    attach_birth_time_sample_evaluations,
    bounded_stability_pool,
    build_birth_time_sampling_plan,
    shift_iso_timestamp,
    summarize_line_uncertainty_corridors,
)
from swisseph_state import require_swisseph, swisseph_lock


SYNTHETIC_LATITUDE = 48.85341
SYNTHETIC_LONGITUDE = 2.3488
SYNTHETIC_CHART_UTC = "2000-02-29T11:34:00+00:00"
SYNTHETIC_HOUSE_BOUNDARY_UTC = "2000-02-29T05:09:00+00:00"


def _longitude_in_arc(start, end, point):
    start %= 360.0
    end %= 360.0
    point %= 360.0
    if start <= end:
        return start <= point < end
    return point >= start or point < end


def _house_for_longitude(longitude, cusps):
    for index in range(12):
        if _longitude_in_arc(cusps[index], cusps[(index + 1) % 12], longitude):
            return index + 1
    return None


def _moon_house_and_twelfth_cusp(timestamp_iso):
    swe = require_swisseph()
    dt = datetime.fromisoformat(timestamp_iso).astimezone(timezone.utc)
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    jd_ut = swe.julday(dt.year, dt.month, dt.day, hour, swe.GREG_CAL)
    with swisseph_lock():
        moon, _ = swe.calc_ut(jd_ut, swe.MOON, swe.FLG_SWIEPH)
        cusps, _ = swe.houses(
            jd_ut,
            SYNTHETIC_LATITUDE,
            SYNTHETIC_LONGITUDE,
            b"R",
        )
    normalized_cusps = [float(value) % 360.0 for value in cusps]
    moon_longitude = float(moon[0]) % 360.0
    return (
        _house_for_longitude(moon_longitude, normalized_cusps),
        moon_longitude,
        normalized_cusps[11],
    )


def test_user_entered_time_gets_a_bounded_five_minute_sampling_plan():
    plan = build_birth_time_sampling_plan(
        {
            "status": "user_entered_time",
            "confidence": "user_entered",
            "ranking_eligibility": "provisional",
        }
    )

    assert plan["status"] == "ready"
    assert plan["assumed_uncertainty"] is True
    assert plan["sampled_uncertainty_minutes"] == 5.0
    assert [sample["offset_minutes"] for sample in plan["samples"]] == [-5.0, 5.0]


def test_wide_numeric_range_uses_interior_samples_but_unknown_range_is_not_invented():
    wide = build_birth_time_sampling_plan(
        {
            "status": "approximate",
            "effective_uncertainty_minutes": 360,
            "ranking_eligibility": "regional_only",
        }
    )
    unknown = build_birth_time_sampling_plan(
        {
            "status": "unknown_time",
            "ranking_eligibility": "ineligible_unknown_time",
        }
    )

    offsets = [sample["offset_minutes"] for sample in wide["samples"]]
    assert len(offsets) == 12
    assert offsets[0] == -360.0
    assert offsets[-1] == 360.0
    assert 0.0 not in offsets
    assert any(abs(value) < 360.0 for value in offsets)
    assert unknown["status"] == "not_sampled"
    assert unknown["samples"] == []


def test_synthetic_moon_flips_house_inside_two_minute_time_perturbation():
    center_house, moon_longitude, twelfth_cusp = _moon_house_and_twelfth_cusp(
        SYNTHETIC_HOUSE_BOUNDARY_UTC
    )
    earlier_house, _, _ = _moon_house_and_twelfth_cusp(
        shift_iso_timestamp(SYNTHETIC_HOUSE_BOUNDARY_UTC, -2.0)
    )

    separation = (twelfth_cusp - moon_longitude) % 360.0
    assert center_house == 11
    assert earlier_house == 12
    assert 0.12 < separation < 0.15


def test_nearby_time_samples_create_a_geographic_line_corridor():
    plan = build_birth_time_sampling_plan(
        {
            "status": "user_entered_time",
            "confidence": "user_entered",
            "ranking_eligibility": "provisional",
        }
    )
    base = build_astrocartography_lines(
        SYNTHETIC_CHART_UTC,
        bodies=["Moon"],
        angles=["MC"],
    )
    samples = []
    for sample in plan["samples"]:
        timestamp = shift_iso_timestamp(
            SYNTHETIC_CHART_UTC,
            sample["offset_minutes"],
        )
        samples.append(
            {
                **sample,
                "timestamp": timestamp,
                "lines_payload": build_astrocartography_lines(
                    timestamp,
                    bodies=["Moon"],
                    angles=["MC"],
                ),
            }
        )

    corridor = summarize_line_uncertainty_corridors(
        base,
        sampling_plan=plan,
        sample_line_payloads=samples,
    )
    moon_mc = corridor["corridors"][0]

    assert corridor["status"] == "evaluated"
    assert moon_mc["id"] == "Moon:MC"
    assert 250.0 < moon_mc["sampled_width_km_at_equator"] < 300.0
    shifts = [sample["shift_from_center_deg"] for sample in moon_mc["samples"]]
    assert min(shifts) < 0.0 < max(shifts)


def test_corridor_centers_match_base_line_equator_crossings_for_every_angle():
    base = build_astrocartography_lines(
        SYNTHETIC_CHART_UTC,
        bodies=["Sun"],
        angles=["MC", "IC", "ASC", "DSC"],
    )
    summary = summarize_line_uncertainty_corridors(
        base,
        sampling_plan={"status": "exact", "samples": []},
        sample_line_payloads=[],
    )
    centers = {
        corridor["id"]: corridor["center_equatorial_longitude"]
        for corridor in summary["corridors"]
    }

    for line in base["lines"]:
        equator_point = min(
            (
                point
                for segment in line["segments"]
                for point in segment
            ),
            key=lambda point: abs(float(point[0])),
        )
        assert abs(float(equator_point[0])) < 1e-4
        assert centers[line["id"]] == pytest.approx(float(equator_point[1]), abs=1e-5)


def test_observed_time_scores_replace_confidence_guesses_with_recomputed_bounds():
    base = {
        "score": 50,
        "raw_score": 1.0,
        "score_interval": {"low": 48, "high": 52},
        "uncertainty": {"distance_sensitivity": {"profiles": {}}},
    }
    result = attach_birth_time_sample_evaluations(
        base,
        sampling_plan={
            "status": "ready",
            "method": "bounded_symmetric_time_grid_v1",
            "samples": [],
        },
        sample_evaluations=[
            {
                "id": "birth_time_sample_01",
                "offset_minutes": -5.0,
                "evaluation": {"score": 45, "raw_score": 0.4, "score_available": True},
            },
            {
                "id": "birth_time_sample_02",
                "offset_minutes": 5.0,
                "evaluation": {"score": 57, "raw_score": 1.7, "score_available": True},
            },
        ],
    )

    sampling = result["uncertainty"]["birth_time_sampling"]
    assert sampling["score_interval"] == {"low": 45, "high": 57}
    assert sampling["raw_score_interval"] == {"low": 0.4, "high": 1.7}
    assert result["score_interval"] == {"low": 45, "high": 57}
    assert result["score_interval_method"] == "combined_recomputed_time_and_distance_scenarios_v1"


def test_incomplete_resampling_is_labeled_partial_instead_of_silent():
    result = attach_birth_time_sample_evaluations(
        {"score": 50, "raw_score": 1.0, "uncertainty": {}},
        sampling_plan={
            "status": "ready",
            "coverage_complete": False,
            "preparation_warning": "One endpoint failed.",
        },
        sample_evaluations=[
            {
                "id": "only-sample",
                "offset_minutes": -5.0,
                "evaluation": {"score": 48, "raw_score": 0.8},
            }
        ],
    )

    assert result["uncertainty"]["birth_time_sampling"]["status"] == "evaluated_partial"


def test_cross_location_rank_stability_uses_common_time_resamples():
    rows = [
        {
            "target": {"candidate_id": "alpha", "label": "Alpha"},
            "location_score": {
                "score": 60,
                "raw_score": 10.0,
                "uncertainty": {
                    "birth_time_sampling": {
                        "samples": [
                            {"id": "early", "score": 52, "raw_score": 4.0},
                            {"id": "late", "score": 52, "raw_score": 4.0},
                        ]
                    }
                },
            },
        },
        {
            "target": {"candidate_id": "beta", "label": "Beta"},
            "location_score": {
                "score": 59,
                "raw_score": 9.0,
                "uncertainty": {
                    "birth_time_sampling": {
                        "samples": [
                            {"id": "early", "score": 64, "raw_score": 12.0},
                            {"id": "late", "score": 64, "raw_score": 12.0},
                        ]
                    }
                },
            },
        },
    ]

    summary = apply_cross_location_rank_stability(
        rows,
        score_polarity="higher_is_better",
        top_k=1,
    )

    alpha = rows[0]["location_score"]["rank_stability"]
    beta = rows[1]["location_score"]["rank_stability"]
    assert summary["status"] == "evaluated"
    assert summary["scenario_count"] == 3
    assert alpha["baseline_rank"] == 1
    assert alpha["rank_interval"] == {"best": 1, "worst": 2}
    assert alpha["birth_time_scenario_count"] == 2
    assert beta["baseline_rank"] == 2
    assert beta["rank_interval"] == {"best": 1, "worst": 2}


def test_atlas_recomputes_candidate_scores_and_ranks_for_time_samples(monkeypatch):
    monkeypatch.setattr(
        atlas_engine,
        "resolve_goal_shortlist_plan",
        lambda goal_id, relocation_limit, candidate_count: {
            "strategy": "line_first",
            "prepass_limit": candidate_count,
        },
    )
    monkeypatch.setattr(
        atlas_engine,
        "get_goal_score_polarity",
        lambda goal_id: "higher_is_better",
    )

    scenario_scores = {
        "center": {"Alpha": 10.0, "Beta": 9.0},
        "early": {"Alpha": 4.0, "Beta": 12.0},
        "late": {"Alpha": 4.0, "Beta": 12.0},
    }

    def fake_score_candidate(
        city,
        *,
        goal_id,
        natal_lines,
        transit_lines=None,
        relocation_features=None,
        relocation_status=None,
    ):
        scenario = str((natal_lines[0] or {}).get("scenario") or "center")
        identity = atlas_engine._candidate_identity_payload(city)
        label = identity["target"]["label"]
        raw_score = scenario_scores[scenario][label]
        score = int(50 + raw_score)
        return {
            **identity,
            "natal": {
                "reading": {
                    "lead_line": {
                        "label": f"{scenario} line",
                        "distance_km": 20.0,
                    }
                }
            },
            "location_score": {
                "score": score,
                "score_available": True,
                "raw_score": raw_score,
                "ranking_eligible": True,
                "top_supports": [{"score": raw_score}],
                "top_cautions": [],
                "uncertainty": {
                    "distance_sensitivity": {
                        "profiles": {
                            "standard": {
                                "score": score,
                                "raw_score": raw_score,
                            }
                        }
                    }
                },
            },
        }

    monkeypatch.setattr(atlas_engine, "_score_candidate", fake_score_candidate)

    candidates = [
        {
            "candidate_id": "alpha",
            "label": "Alpha",
            "latitude": 0.0,
            "longitude": 0.0,
            "population": 100,
        },
        {
            "candidate_id": "beta",
            "label": "Beta",
            "latitude": 20.0,
            "longitude": 20.0,
            "population": 100,
        },
    ]
    result = atlas_engine.rank_candidate_pool_for_goal(
        goal_id="test",
        candidates=candidates,
        natal_lines=[{"scenario": "center"}],
        limit=2,
        relocation_limit=2,
        birth_time_sampling_plan={
            "status": "ready",
            "method": "bounded_symmetric_time_grid_v1",
        },
        birth_time_samples=[
            {
                "id": "early",
                "offset_minutes": -5.0,
                "natal_lines": [{"scenario": "early"}],
            },
            {
                "id": "late",
                "offset_minutes": 5.0,
                "natal_lines": [{"scenario": "late"}],
            },
        ],
    )

    assert result["birth_time_sampling"]["status"] == "evaluated"
    assert result["rank_stability"]["status"] == "evaluated"
    assert result["rank_stability"]["scenario_count"] == 3
    assert result["rank_stability"]["deduplicated_scenarios"] == [
        {"id": "distance:standard", "duplicate_of": "reported_time"}
    ]
    by_label = {
        item["target"]["label"]: item["location_score"]
        for item in result["results"]
    }
    assert by_label["Alpha"]["uncertainty"]["birth_time_sampling"]["score_interval"] == {
        "low": 54,
        "high": 60,
    }
    assert by_label["Alpha"]["rank_stability"]["rank_interval"] == {
        "best": 1,
        "worst": 2,
    }
    assert by_label["Beta"]["rank_stability"]["rank_interval"] == {
        "best": 1,
        "worst": 2,
    }


def test_duplicate_standard_scenario_does_not_bias_top_k_retention():
    rows = [
        {
            "target": {"candidate_id": "alpha", "label": "Alpha"},
            "location_score": {
                "score": 60,
                "raw_score": 10.0,
                "uncertainty": {
                    "distance_sensitivity": {
                        "profiles": {
                            "standard": {"score": 60, "raw_score": 9.9995},
                        }
                    },
                    "birth_time_sampling": {
                        "samples": [
                            {"id": "early", "score": 60, "raw_score": 10.0},
                            {"id": "late", "score": 50, "raw_score": 4.0},
                        ]
                    },
                },
            },
        },
        {
            "target": {"candidate_id": "beta", "label": "Beta"},
            "location_score": {
                "score": 59,
                "raw_score": 9.0,
                "uncertainty": {
                    "distance_sensitivity": {
                        "profiles": {
                            "standard": {"score": 59, "raw_score": 8.9996},
                        }
                    },
                    "birth_time_sampling": {
                        "samples": [
                            {"id": "early", "score": 59, "raw_score": 9.0},
                            {"id": "late", "score": 65, "raw_score": 12.0},
                        ]
                    },
                },
            },
        },
    ]

    summary = apply_cross_location_rank_stability(rows, top_k=1)
    alpha = rows[0]["location_score"]["rank_stability"]

    assert summary["scenario_count"] == 2
    assert summary["deduplicated_scenarios"] == [
        {"id": "distance:standard", "duplicate_of": "reported_time"},
        {"id": "time:early", "duplicate_of": "reported_time"},
    ]
    assert alpha["top_k_retention"] == 0.5
    assert alpha["status"] == "variable"


def test_bounded_atlas_stability_pool_discloses_evaluated_coverage():
    rows = [
        {
            "target": {"candidate_id": f"city-{index}", "label": f"City {index}"},
            "location_score": {
                "score": 100 - index,
                "raw_score": 100.0 - index,
                "uncertainty": {},
            },
        }
        for index in range(100)
    ]
    pool = bounded_stability_pool(rows, requested_limit=20)
    summary = apply_cross_location_rank_stability(
        pool,
        top_k=20,
        scope_candidate_count=len(rows),
    )

    assert len(pool) == 64
    assert summary["candidate_count"] == 64
    assert summary["scope_candidate_count"] == 100
    assert summary["bounded_scope"] is True
    assert summary["scope_coverage"] == 0.64


def test_stability_ties_use_stable_identity_not_population():
    rows = [
        {
            "target": {"candidate_id": "zeta", "label": "Zeta"},
            "atlas_city": {"population": 10_000_000},
            "location_score": {"score": 60, "raw_score": 10.0, "uncertainty": {}},
        },
        {
            "target": {"candidate_id": "alpha", "label": "Alpha"},
            "atlas_city": {"population": 1},
            "location_score": {"score": 60, "raw_score": 10.0, "uncertainty": {}},
        },
    ]

    apply_cross_location_rank_stability(rows, top_k=1)

    assert rows[1]["location_score"]["rank_stability"]["baseline_rank"] == 1
    assert rows[0]["location_score"]["rank_stability"]["baseline_rank"] == 2
