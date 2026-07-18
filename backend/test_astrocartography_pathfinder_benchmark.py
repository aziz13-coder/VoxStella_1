from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_astrocartography_pathfinder_benchmark import (
    _build_case_result,
    summarize_pathfinder_results,
)


def test_summarize_pathfinder_results_tracks_prepass_and_final_rank():
    summary = summarize_pathfinder_results(
        [
            {
                "goal_id": "gambling_luck",
                "pathfinder": {"candidate_count": 4},
                "event": {
                    "in_prepass": True,
                    "in_shortlist": True,
                    "in_final_ranking": True,
                    "top_1_hit": True,
                    "top_3_hit": True,
                    "initial_rank": 3,
                    "final_rank": 1,
                    "rank_delta": 2,
                },
            },
            {
                "goal_id": "gambling_luck",
                "pathfinder": {"candidate_count": 4},
                "event": {
                    "in_prepass": False,
                    "in_shortlist": False,
                    "in_final_ranking": False,
                    "top_1_hit": False,
                    "top_3_hit": False,
                    "initial_rank": 4,
                    "final_rank": None,
                    "rank_delta": None,
                },
            },
        ]
    )

    overall = summary["overall"]
    by_goal = summary["by_goal"]["gambling_luck"]

    assert overall["case_count"] == 2
    assert overall["prepass_hit_rate"] == 0.5
    assert overall["shortlist_hit_rate"] == 0.5
    assert overall["final_ranked_rate"] == 0.5
    assert overall["top_1_hit_rate"] == 0.5
    assert overall["top_3_hit_rate"] == 0.5
    assert overall["mean_initial_rank"] == 3.5
    assert overall["mean_final_rank"] == 3.0
    assert overall["mean_rank_delta"] == 2.0
    assert overall["dropped_before_prepass_count"] == 1
    assert overall["dropped_after_prepass_count"] == 0
    assert by_goal == overall


def test_case_result_matches_duplicate_labels_by_exact_coordinates():
    event_city = {
        "role": "event",
        "label": "Springfield",
        "query": "Springfield",
        "latitude": 39.7817213,
        "longitude": -89.6501481,
        "timezone": "America/Chicago",
    }
    control_city = {
        "role": "control",
        "label": "Springfield",
        "query": "Springfield",
        "latitude": 44.0462362,
        "longitude": -123.0220289,
        "timezone": "America/Los_Angeles",
    }
    ranking_result = {
        "shortlist_strategy": "relocation_prepass",
        "relocation_prepass_count": 2,
        "shortlisted_count": 2,
        "viable_count": 2,
        "ranking": [
            {**control_city, "rank": 1},
            {**event_city, "rank": 2},
        ],
        "debug": {
            "initial_ranking": [
                {**control_city, "rank": 1},
                {**event_city, "rank": 2},
            ],
            "final_scored_ranking": [
                {**control_city, "rank": 1},
                {**event_city, "rank": 2},
            ],
        },
    }

    result = _build_case_result(
        {"case_id": "same-label", "person_id": "person-1"},
        mode="natal_only",
        context={"goal_id": "travel_fun"},
        candidate_pool=[event_city, control_city],
        ranking_result=ranking_result,
        control_design={"frozen": True},
        resolution="standard",
        limit=2,
        relocation_limit=2,
    )

    assert result["event"]["initial_rank"] == 2
    assert result["event"]["rescored_rank"] == 2
    assert result["event"]["final_rank"] == 2
    assert result["candidate_pool"][0]["latitude"] == event_city["latitude"]
    assert result["candidate_pool"][0]["longitude"] == event_city["longitude"]
