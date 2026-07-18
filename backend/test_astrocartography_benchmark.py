from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmarks.astrocartography.baselines import compute_case_baselines
from benchmarks.astrocartography.validation import assign_person_splits
from run_astrocartography_benchmark import (
    DEFAULT_SPECULATION_DATASET,
    _build_case_context,
    _control_blocks_for_case,
    _resolve_city_payload,
    _score_city_for_case,
    _validate_control_design,
    load_benchmark_cases,
    rank_case_scores,
    summarize_benchmark_results,
)


def test_load_benchmark_cases_skips_disabled_rows(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps({"enabled": False, "case_id": "skip_me"}),
                json.dumps({"enabled": True, "case_id": "use_me", "goal_id": "gambling_luck"}),
            ]
        ),
        encoding="utf-8",
    )

    cases, skipped = load_benchmark_cases([dataset])

    assert [case["case_id"] for case in cases] == ["use_me"]
    assert len(skipped) == 1
    assert skipped[0]["case_id"] == "skip_me"
    assert skipped[0]["reason"] == "disabled"


def test_brunson_longworth_birth_coordinates_are_authoritative_and_explicit():
    cases, skipped = load_benchmark_cases(
        [DEFAULT_SPECULATION_DATASET],
        case_id="spec_brunson_2004_la",
    )

    assert skipped == []
    assert len(cases) == 1
    birth = cases[0]["birth"]
    provenance = birth["coordinate_provenance"]
    assert birth["latitude"] == 32.6503906
    assert birth["longitude"] == -100.345661
    assert provenance["authority"] == (
        "U.S. Geological Survey Geographic Names Information System (GNIS)"
    )
    assert provenance["feature_id"] == "1374718"
    assert provenance["feature_name"] == "Longworth"
    assert provenance["feature_class"] == "Populated Place"
    assert provenance["record_file"] == "DomesticNames_TX.txt"

    _, control_design = _control_blocks_for_case(cases[0])
    assert control_design["frozen"] is False
    assert control_design["exposure_matched"] is False
    with pytest.raises(ValueError, match="frozen control"):
        _validate_control_design(
            control_design,
            require_frozen_controls=True,
            require_exposure_matched_controls=False,
        )


def test_brunson_coordinates_reach_shared_benchmark_context(monkeypatch):
    cases, _ = load_benchmark_cases(
        [DEFAULT_SPECULATION_DATASET],
        case_id="spec_brunson_2004_la",
    )

    import astro_clock_api
    import astrocartography_goal_models
    import astrocartography_service

    chart_calls = []

    def fake_chart(*args, **kwargs):
        chart_calls.append((args, kwargs))
        return {
            "meta": {
                "timestamp": "1933-08-10T21:20:00+00:00",
                "location": "Longworth, Texas, USA",
                "timezone": "America/Chicago",
                "latitude": kwargs.get("latitude"),
                "longitude": kwargs.get("longitude"),
            }
        }

    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", fake_chart)
    monkeypatch.setattr(
        astrocartography_service,
        "build_astrocartography_lines",
        lambda _timestamp: {"lines": []},
    )
    monkeypatch.setattr(
        astrocartography_goal_models,
        "get_goal_model",
        lambda goal_id: {"id": goal_id},
    )

    context = _build_case_context(cases[0], mode="natal_only")

    assert chart_calls[0][1]["latitude"] == 32.6503906
    assert chart_calls[0][1]["longitude"] == -100.345661
    assert context["natal_meta"]["latitude"] == 32.6503906
    assert context["natal_meta"]["longitude"] == -100.345661


def test_rank_case_scores_computes_pairwise_and_rank():
    candidates = [
        {
            "role": "event",
            "city": {"label": "Event City"},
            "models": {
                "product_model": {"label": "Product Model", "score": 80},
                "benefic_minus_malefic": {"label": "Benefic Minus Malefic", "score": 62},
            },
        },
        {
            "role": "control",
            "city": {"label": "Control A"},
            "models": {
                "product_model": {"label": "Product Model", "score": 70},
                "benefic_minus_malefic": {"label": "Benefic Minus Malefic", "score": 62},
            },
        },
        {
            "role": "control",
            "city": {"label": "Control B"},
            "models": {
                "product_model": {"label": "Product Model", "score": 50},
                "benefic_minus_malefic": {"label": "Benefic Minus Malefic", "score": 40},
            },
        },
    ]

    ranked = rank_case_scores(candidates)

    assert ranked["product_model"]["event_rank"] == 1
    assert ranked["product_model"]["pairwise_total"] == 2
    assert ranked["product_model"]["pairwise_wins"] == 2
    assert ranked["product_model"]["pairwise_win_rate"] == 1.0
    assert ranked["benefic_minus_malefic"]["pairwise_ties"] == 1
    assert ranked["benefic_minus_malefic"]["pairwise_win_rate"] == 0.75


def test_rank_case_scores_prefers_raw_score_over_display_score():
    candidates = [
        {
            "role": "event",
            "city": {"label": "Event City"},
            "models": {
                "product_model": {"label": "Product Model", "raw_score": 0.49, "score": 51},
            },
        },
        {
            "role": "control",
            "city": {"label": "Control A"},
            "models": {
                "product_model": {"label": "Product Model", "raw_score": 0.51, "score": 51},
            },
        },
        {
            "role": "control",
            "city": {"label": "Control B"},
            "models": {
                "product_model": {"label": "Product Model", "raw_score": 0.1, "score": 51},
            },
        },
    ]

    ranked = rank_case_scores(candidates)

    assert ranked["product_model"]["event_rank"] == 2
    assert ranked["product_model"]["event_score"] == 0.49
    assert ranked["product_model"]["event_display_score"] == 51
    assert ranked["product_model"]["pairwise_wins"] == 1
    assert ranked["product_model"]["pairwise_ties"] == 0
    assert ranked["product_model"]["pairwise_win_rate"] == 0.5
    assert ranked["product_model"]["ranking"][0]["label"] == "Control A"
    assert ranked["product_model"]["ranking"][0]["score"] == 0.51
    assert ranked["product_model"]["ranking"][0]["display_score"] == 51


def test_summarize_benchmark_results_aggregates_case_metrics():
    case_results = [
        {
            "goal_id": "gambling_luck",
            "comparators": {
                "product_model": {
                    "label": "Product Model",
                    "pairwise_total": 2,
                    "pairwise_wins": 2,
                    "pairwise_ties": 0,
                    "top_3_hit": True,
                    "reciprocal_rank": 1.0,
                    "event_rank": 1,
                },
                "parent_model": {
                    "label": "Parent Model (Money)",
                    "pairwise_total": 2,
                    "pairwise_wins": 1,
                    "pairwise_ties": 0,
                    "top_3_hit": True,
                    "reciprocal_rank": 0.5,
                    "event_rank": 2,
                },
            },
        },
        {
            "goal_id": "gambling_luck",
            "comparators": {
                "product_model": {
                    "label": "Product Model",
                    "pairwise_total": 2,
                    "pairwise_wins": 1,
                    "pairwise_ties": 1,
                    "top_3_hit": True,
                    "reciprocal_rank": 0.5,
                    "event_rank": 2,
                },
                "parent_model": {
                    "label": "Parent Model (Money)",
                    "pairwise_total": 2,
                    "pairwise_wins": 1,
                    "pairwise_ties": 0,
                    "top_3_hit": True,
                    "reciprocal_rank": 0.333333,
                    "event_rank": 3,
                },
            },
        },
    ]

    summary = summarize_benchmark_results(case_results)

    assert summary["overall"]["product_model"]["case_count"] == 2
    assert summary["overall"]["product_model"]["pairwise_win_rate"] == 0.875
    assert summary["overall"]["product_model"]["mean_event_rank"] == 1.5
    assert summary["by_goal"]["gambling_luck"]["parent_model"]["pairwise_lift_vs_product"] == 0.375


def test_compute_case_baselines_adds_experimental_health_risk_for_risk_pressure():
    relocation = {
        "planet_houses": {"Mars": 1, "Saturn": 6, "Uranus": 8},
        "planet_angles": {"Mars": "ASC"},
        "house_occupancy": {1: ["Mars"], 6: ["Saturn"], 8: ["Uranus"]},
        "metrics": {
            "malefic_pressure": 0.8,
            "benefic_balance": 0.1,
            "conflict_pressure": 0.6,
            "uncertainty": 0.4,
            "stability": 0.0,
            "health_risk": 0.75,
        },
    }
    natal_rows = [
        {"body": "Mars", "angle": "ASC", "distance_km": 20.0},
        {"body": "Saturn", "angle": "MC", "distance_km": 40.0},
    ]
    natal_crossings = [
        {"planets": ["Mars", "Saturn"], "distance_km": 60.0},
    ]
    baselines = compute_case_baselines(
        "risk_pressure",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        relocation=relocation,
    )

    assert "parent_model" not in baselines
    assert "experimental_health_risk" not in baselines
    assert "accident_pressure" in baselines
    assert "hostile_places" in baselines
    assert "drain_breakdown" in baselines
    assert "split_risk_max" in baselines
    assert all(
        payload["independent_from_product_model"]
        for payload in baselines.values()
    )
    assert baselines["benefic_minus_malefic"]["score_polarity"] == "higher_is_better"
    assert baselines["accident_pressure"]["score_polarity"] == "higher_is_worse"
    assert baselines["split_risk_max"]["raw_score"] == max(
        baselines["accident_pressure"]["raw_score"],
        baselines["hostile_places"]["raw_score"],
        baselines["drain_breakdown"]["raw_score"],
    )


def test_compute_case_baselines_adds_conflict_and_health_for_accident_prone():
    relocation = {
        "planet_houses": {"Mars": 1, "Saturn": 6, "Uranus": 8},
        "planet_angles": {"Mars": "ASC"},
        "house_occupancy": {1: ["Mars"], 6: ["Saturn"], 8: ["Uranus"]},
        "metrics": {
            "malefic_pressure": 0.8,
            "benefic_balance": 0.1,
            "conflict_pressure": 0.6,
            "uncertainty": 0.4,
            "stability": 0.0,
            "health_risk": 0.75,
        },
    }
    baselines = compute_case_baselines(
        "accident_prone",
        natal_rows=[{"body": "Mars", "angle": "ASC", "distance_km": 20.0}],
        natal_crossings=[{"planets": ["Mars", "Uranus"], "distance_km": 60.0}],
        relocation=relocation,
    )

    assert "parent_model" not in baselines
    assert "experimental_health_risk" not in baselines
    assert "accident_pressure" in baselines
    assert "malefic_pressure" in baselines
    assert all(
        payload["independent_from_product_model"]
        for payload in baselines.values()
    )


def test_compute_case_baselines_adds_gambling_ablations():
    relocation = {
        "planet_houses": {"Jupiter": 5, "Venus": 11, "Moon": 5, "Saturn": 8},
        "planet_angles": {"Jupiter": "ASC", "Moon": "MC"},
        "house_occupancy": {5: ["Jupiter", "Moon"], 8: ["Saturn"], 11: ["Venus"]},
        "metrics": {
            "gambling_activation": 0.65,
            "gambling_signature": 0.55,
            "asc_ruler_strength": 0.6,
            "gambling_ruler_strength": 0.75,
            "asc_gambling_harmony": 0.7,
            "moon_gambling_support": 0.45,
            "speculation": 0.6,
            "money_support": 0.4,
            "benefic_balance": 0.3,
            "speculation_drag": 0.15,
            "moon_liability": 0.1,
            "asc_gambling_tension": 0.05,
        },
    }
    baselines = compute_case_baselines(
        "gambling_luck",
        natal_rows=[
            {"body": "Jupiter", "angle": "ASC", "distance_km": 20.0},
            {"body": "Venus", "angle": "MC", "distance_km": 60.0},
            {"body": "Saturn", "angle": "IC", "distance_km": 80.0},
        ],
        natal_crossings=[{"planets": ["Jupiter", "Venus"], "distance_km": 45.0}],
        relocation=relocation,
    )

    assert "parent_model" not in baselines
    assert "jupiter_venus" in baselines
    assert "gambling_lines_only" in baselines
    assert "gambling_relocation_only" in baselines
    assert "gambling_no_activation_floor" in baselines
    assert baselines["gambling_lines_only"]["label"] == "Gambling Lines Heuristic"
    assert baselines["gambling_relocation_only"]["label"] == "Gambling Relocation Heuristic"
    assert baselines["gambling_no_activation_floor"]["label"] == "Gambling Combined Heuristic"


def test_compute_case_baselines_does_not_reuse_existing_goal_models_for_travel():
    relocation = {
        "planet_houses": {"Venus": 5, "Jupiter": 9, "Moon": 4, "Mercury": 3},
        "planet_angles": {"Moon": "IC"},
        "house_occupancy": {3: ["Mercury"], 4: ["Moon"], 5: ["Venus"], 9: ["Jupiter"]},
        "metrics": {
            "travel_joy": 0.75,
            "restoration": 0.55,
            "mobility": 0.5,
            "community": 0.4,
            "beliefs": 0.45,
            "domesticity": 0.35,
            "stability": 0.25,
            "benefic_balance": 0.6,
            "uncertainty": 0.1,
        },
    }
    natal_rows = [
        {"body": "Venus", "angle": "ASC", "distance_km": 20.0},
        {"body": "Jupiter", "angle": "MC", "distance_km": 40.0},
    ]
    natal_crossings = [
        {"planets": ["Venus", "Jupiter"], "distance_km": 60.0},
    ]

    fun_baselines = compute_case_baselines(
        "travel_fun",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        relocation=relocation,
    )
    relax_baselines = compute_case_baselines(
        "travel_relax",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        relocation=relocation,
    )

    assert set(fun_baselines) == {"benefic_minus_malefic"}
    assert set(relax_baselines) == {"benefic_minus_malefic"}


def test_rank_case_scores_respects_outcome_and_hazard_polarity():
    candidates = [
        {
            "role": "event",
            "city": {"label": "Hazard Event"},
            "models": {
                "product_model": {
                    "label": "Health Risk",
                    "raw_score": 8.0,
                    "score": 80,
                    "score_polarity": "higher_is_worse",
                },
                "benefic_minus_malefic": {
                    "label": "Benefic Balance",
                    "raw_score": -2.0,
                    "score": 20,
                    "score_polarity": "higher_is_better",
                },
            },
        },
        {
            "role": "control",
            "city": {"label": "Control"},
            "models": {
                "product_model": {
                    "label": "Health Risk",
                    "raw_score": 2.0,
                    "score": 20,
                    "score_polarity": "higher_is_worse",
                },
                "benefic_minus_malefic": {
                    "label": "Benefic Balance",
                    "raw_score": 3.0,
                    "score": 70,
                    "score_polarity": "higher_is_better",
                },
            },
        },
    ]

    ranked = rank_case_scores(
        candidates,
        outcome_polarity="negative",
        goal_id="health_risk",
    )

    assert ranked["product_model"]["rank_direction"] == "descending"
    assert ranked["product_model"]["pairwise_win_rate"] == 1.0
    assert ranked["benefic_minus_malefic"]["rank_direction"] == "ascending"
    assert ranked["benefic_minus_malefic"]["pairwise_win_rate"] == 1.0


def test_rank_case_scores_uses_tolerance_and_control_weights():
    candidates = [
        {
            "role": "event",
            "city": {"label": "Event"},
            "models": {"product_model": {"raw_score": 1.0, "score": 50}},
        },
        {
            "role": "control",
            "comparison_weight": 3.0,
            "city": {"label": "Near Tie"},
            "models": {"product_model": {"raw_score": 1.0 + 1e-12, "score": 50}},
        },
        {
            "role": "control",
            "comparison_weight": 1.0,
            "city": {"label": "Lower"},
            "models": {"product_model": {"raw_score": 0.0, "score": 50}},
        },
    ]

    result = rank_case_scores(candidates)["product_model"]

    assert result["pairwise_ties"] == 1
    assert result["event_rank_min"] == 1
    assert result["event_rank_max"] == 2
    assert result["pairwise_weight_total"] == 4.0
    assert result["pairwise_win_rate"] == 0.625


def test_summary_primary_rate_weights_cases_not_control_count():
    cases = [
        {
            "case_id": "many-controls",
            "person_id": "person-a",
            "goal_id": "gambling_luck",
            "comparators": {
                "product_model": {
                    "label": "Product",
                    "pairwise_total": 10,
                    "pairwise_wins": 10,
                    "pairwise_ties": 0,
                    "event_rank": 1,
                    "reciprocal_rank": 1.0,
                    "top_3_hit": True,
                }
            },
        },
        {
            "case_id": "one-control",
            "person_id": "person-b",
            "goal_id": "gambling_luck",
            "comparators": {
                "product_model": {
                    "label": "Product",
                    "pairwise_total": 1,
                    "pairwise_wins": 0,
                    "pairwise_ties": 0,
                    "event_rank": 2,
                    "reciprocal_rank": 0.5,
                    "top_3_hit": True,
                }
            },
        },
    ]

    summary = summarize_benchmark_results(cases)["overall"]["product_model"]

    assert summary["pairwise_win_rate"] == 0.5
    assert summary["micro_pairwise_win_rate"] == 0.9091
    assert summary["aggregation"] == "case_weighted"


def test_summary_uses_only_matched_cases_for_comparator_lift():
    cases = [
        {
            "case_id": "matched",
            "person_id": "person-a",
            "goal_id": "travel_fun",
            "comparators": {
                "product_model": {
                    "label": "Product",
                    "pairwise_win_rate": 1.0,
                    "event_rank": 1,
                    "reciprocal_rank": 1.0,
                    "top_3_hit": True,
                },
                "independent": {
                    "label": "Independent",
                    "pairwise_win_rate": 0.25,
                    "event_rank": 2,
                    "reciprocal_rank": 0.5,
                    "top_3_hit": True,
                },
            },
        },
        {
            "case_id": "product-only",
            "person_id": "person-b",
            "goal_id": "travel_fun",
            "comparators": {
                "product_model": {
                    "label": "Product",
                    "pairwise_win_rate": 0.0,
                    "event_rank": 2,
                    "reciprocal_rank": 0.5,
                    "top_3_hit": True,
                },
            },
        },
    ]

    summary = summarize_benchmark_results(cases)["overall"]

    assert summary["product_model"]["pairwise_win_rate"] == 0.5
    assert summary["independent"]["matched_case_count_vs_product"] == 1
    assert summary["independent"]["matched_product_pairwise_win_rate"] == 1.0
    assert summary["independent"]["pairwise_lift_vs_product"] == 0.75


def test_summary_reports_person_cluster_bootstrap_when_sample_allows():
    cases = [
        {
            "case_id": f"case-{index}",
            "person_id": f"person-{index}",
            "goal_id": "travel_fun",
            "comparators": {
                "product_model": {
                    "label": "Product",
                    "pairwise_win_rate": index / 5.0,
                    "event_rank": 1,
                    "reciprocal_rank": 1.0,
                    "top_3_hit": True,
                }
            },
        }
        for index in range(6)
    ]

    first = summarize_benchmark_results(cases)["overall"]["product_model"]
    second = summarize_benchmark_results(cases)["overall"]["product_model"]

    assert first["auc"] == 0.5
    assert first["auc_ci_95"] == second["auc_ci_95"]
    assert first["auc_ci_95"]["method"] == "person_cluster_bootstrap"
    assert first["auc_ci_95"]["cluster_count"] == 6
    assert first["auc_ci_95"]["lower"] <= first["auc"] <= first["auc_ci_95"]["upper"]


def test_summary_accounts_for_failed_cases_without_entering_model_metrics():
    cases = [
        {
            "case_id": "success",
            "person_id": "person-a",
            "goal_id": "travel_fun",
            "comparators": {
                "product_model": {
                    "label": "Product",
                    "pairwise_win_rate": 1.0,
                    "event_rank": 1,
                    "reciprocal_rank": 1.0,
                    "top_3_hit": True,
                }
            },
        }
    ]
    failures = [
        {"case_id": "failed-a", "goal_id": "travel_fun"},
        {"case_id": "failed-b", "goal_id": "travel_fun"},
    ]

    summary = summarize_benchmark_results(
        cases,
        attempted_case_count=3,
        failures=failures,
    )

    assert summary["accounting"] == {
        "attempted_case_count": 3,
        "successful_case_count": 1,
        "failed_case_count": 2,
        "coverage_rate": 0.3333,
        "model_metrics_exclude_failed_cases": True,
    }
    assert summary["overall"]["product_model"]["case_count"] == 1


def test_frozen_exposure_matched_control_design_can_be_required():
    controls, design = _control_blocks_for_case(
        {
            "frozen_controls": [{"label": "Control A"}],
            "control_design": {
                "exposure_matched": True,
                "control_set_id": "travel-controls",
                "version": "2026-07",
            },
        }
    )

    assert controls == [{"label": "Control A"}]
    assert design["source"] == "frozen_controls"
    assert design["frozen"] is True
    assert design["exposure_matched"] is True
    _validate_control_design(
        design,
        require_frozen_controls=True,
        require_exposure_matched_controls=True,
    )

    with pytest.raises(ValueError, match="frozen control"):
        _validate_control_design(
            {"frozen": False, "exposure_matched": True},
            require_frozen_controls=True,
            require_exposure_matched_controls=False,
        )
    with pytest.raises(ValueError, match="exposure-matched"):
        _validate_control_design(
            {"frozen": True, "exposure_matched": False},
            require_frozen_controls=False,
            require_exposure_matched_controls=True,
        )


def test_person_split_is_deterministic_and_keeps_people_together():
    cases = [
        {"case_id": "a1", "person_id": "a"},
        {"case_id": "a2", "person_id": "a"},
        {"case_id": "b1", "person_id": "b"},
        {"case_id": "c1", "person_id": "c"},
        {"case_id": "d1", "person_id": "d"},
    ]

    first, first_manifest = assign_person_splits(cases, holdout_fraction=0.5, seed="fixed")
    second, second_manifest = assign_person_splits(cases, holdout_fraction=0.5, seed="fixed")

    assert [(row["case_id"], row["_validation_split"]) for row in first] == [
        (row["case_id"], row["_validation_split"]) for row in second
    ]
    assert len({
        row["_validation_split"] for row in first if row["person_id"] == "a"
    }) == 1
    assert first_manifest == second_manifest


def test_explicit_coordinates_reach_relocation_chart_unchanged(monkeypatch):
    city = _resolve_city_payload(
        {
            "label": "Precise Site",
            "latitude": 12.34567891,
            "longitude": -98.76543219,
            "timezone": "UTC",
        }
    )
    assert city["latitude"] == 12.34567891
    assert city["longitude"] == -98.76543219

    import astro_clock_api
    import astrocartography_atlas_engine
    import astrocartography_goal_engine

    chart_calls = []

    def fake_chart(*args, **kwargs):
        chart_calls.append((args, kwargs))
        return {"chart_data": {}}

    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", fake_chart)
    monkeypatch.setattr(
        astrocartography_atlas_engine,
        "_score_candidate",
        lambda *_args, **_kwargs: {
            "location_score": {
                "raw_score": 1.0,
                "score": 51,
                "headline": "test",
                "goal": {"score_polarity": "higher_is_better"},
            },
            "natal": {"reading": {"nearest_lines": []}, "crossings": []},
        },
    )
    monkeypatch.setattr(
        astrocartography_goal_engine,
        "extract_relocation_features",
        lambda _chart: {"metrics": {}},
    )

    scored = _score_city_for_case(
        city,
        goal_id="gambling_luck",
        natal_timestamp="2020-01-01T00:00:00+00:00",
        natal_lines=[],
    )

    assert chart_calls[0][1]["latitude"] == city["latitude"]
    assert chart_calls[0][1]["longitude"] == city["longitude"]
    assert scored["city"]["latitude"] == city["latitude"]
    assert scored["city"]["longitude"] == city["longitude"]
