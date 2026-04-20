from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmarks.astrocartography.baselines import compute_case_baselines
from astrocartography_goal_engine import evaluate_goal_model
from run_astrocartography_benchmark import (
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

    assert "parent_model" in baselines
    assert "experimental_health_risk" in baselines
    assert "accident_pressure" in baselines
    assert "hostile_places" in baselines
    assert "drain_breakdown" in baselines
    assert "split_risk_max" in baselines
    assert baselines["experimental_health_risk"]["goal_id"] == "health_risk"
    product_eval = evaluate_goal_model(
        "risk_pressure",
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        relocation=relocation,
    )
    assert baselines["benefic_minus_malefic"]["raw_score"] == -product_eval["raw_score"]
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

    assert "parent_model" in baselines
    assert baselines["parent_model"]["goal_id"] == "conflict"
    assert "experimental_health_risk" in baselines
    assert baselines["experimental_health_risk"]["goal_id"] == "health_risk"


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

    assert baselines["parent_model"]["goal_id"] == "money"
    assert "jupiter_venus" in baselines
    assert "gambling_lines_only" in baselines
    assert "gambling_relocation_only" in baselines
    assert "gambling_no_activation_floor" in baselines
    assert baselines["gambling_lines_only"]["label"] == "Gambling Lines Only"
    assert baselines["gambling_relocation_only"]["label"] == "Gambling Relocation Only"
    assert baselines["gambling_no_activation_floor"]["label"] == "Gambling No Activation Floor"


def test_compute_case_baselines_adds_existing_goal_comparators_for_travel_models():
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

    assert fun_baselines["parent_model"]["goal_id"] == "friends"
    assert fun_baselines["existing_love"]["goal_id"] == "love"
    assert fun_baselines["existing_protective_places"]["goal_id"] == "protective_places"
    assert relax_baselines["parent_model"]["goal_id"] == "home_retreat"
    assert relax_baselines["existing_beliefs"]["goal_id"] == "beliefs"
    assert relax_baselines["existing_protective_places"]["goal_id"] == "protective_places"
