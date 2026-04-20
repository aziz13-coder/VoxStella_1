from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_astrocartography_pathfinder_benchmark import summarize_pathfinder_results


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
