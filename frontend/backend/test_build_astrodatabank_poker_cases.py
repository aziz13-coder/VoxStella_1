from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_astrodatabank_poker_cases import build_cases_from_profiles, load_poker_profiles, write_cases_jsonl


def test_build_cases_from_profiles_emits_benchmark_case():
    profiles = [
        {
            "enabled": True,
            "person_id": "template_player",
            "person_name": "Template Player",
            "goal_id": "gambling_luck",
            "birth": {
                "date": "1980-01-01",
                "time": "12:00",
                "place": "New York, New York, USA",
                "timezone": "America/New_York",
                "data_quality": "AA",
            },
            "birth_source": {
                "kind": "birth_data",
                "quality": "high",
                "url": "https://example.com/birth",
            },
            "event_history_source": {
                "kind": "event_result",
                "quality": "high",
                "url": "https://example.com/results",
            },
            "control_selection": "same_person_weaker_venues",
            "performance_context": {
                "discipline": "poker_tournaments",
                "selection_basis": "breakthrough win vs weaker same-player venues",
            },
            "notes": "Profile note.",
            "performances": [
                {
                    "performance_id": "target_win",
                    "event_type": "poker_title",
                    "date": "2010-06-01",
                    "location": {
                        "label": "Las Vegas, NV, United States",
                        "latitude": 36.167426,
                        "longitude": -115.148413,
                        "timezone": "America/Los_Angeles",
                    },
                    "result_label": "Winner",
                    "outcome_tier": 5,
                    "outcome_strength": "breakthrough_title",
                    "outcome_value": 250000.0,
                    "currency": "USD",
                    "field_size": 400,
                    "venue_label": "Main Event",
                    "notes": "Event note.",
                    "sources": [
                        {
                            "kind": "event_result",
                            "quality": "high",
                            "url": "https://example.com/event",
                        }
                    ],
                },
                {
                    "performance_id": "control_a",
                    "date": "2009-04-01",
                    "location": {
                        "label": "Mashantucket, CT, United States",
                        "latitude": 41.468233,
                        "longitude": -71.966556,
                        "timezone": "America/New_York",
                    },
                    "result_label": "Final Table",
                    "outcome_tier": 3,
                    "outcome_strength": "strong_cash",
                    "benchmark_reason": "Weaker same-player venue with a lower finish.",
                },
                {
                    "performance_id": "control_b",
                    "date": "2008-03-01",
                    "location": {
                        "label": "San Jose, CA, United States",
                        "latitude": 37.336166,
                        "longitude": -121.890591,
                        "timezone": "America/Los_Angeles",
                    },
                    "result_label": "Minor Cash",
                    "outcome_tier": 2,
                    "outcome_strength": "minor_cash",
                    "notes": "Useful weaker same-player venue.",
                },
            ],
            "benchmark_targets": [
                {
                    "case_id": "template_player_target_win",
                    "performance_id": "target_win",
                    "control_ids": ["control_a", "control_b"],
                    "transit_context": {"location_strategy": "event"},
                    "notes": "Target note.",
                }
            ],
        }
    ]

    cases = build_cases_from_profiles(profiles)

    assert len(cases) == 1
    case = cases[0]
    assert case["enabled"] is True
    assert case["case_id"] == "template_player_target_win"
    assert case["goal_id"] == "gambling_luck"
    assert case["benchmark_family"] == "astrodatabank_poker"
    assert case["benchmark_type"] == "within_person_venue_performance"
    assert case["control_selection"] == "same_person_weaker_venues"
    assert case["birth"]["data_quality"] == "AA"
    assert case["event"]["type"] == "poker_title"
    assert case["event"]["location"]["label"] == "Las Vegas, NV, United States"
    assert case["event"]["outcome_strength"] == "breakthrough_title"
    assert len(case["controls"]) == 2
    assert case["controls"][0]["reason"] == "Weaker same-player venue with a lower finish."
    assert "same-player" in case["controls"][1]["reason"].lower()
    assert case["transit_context"]["location_strategy"] == "event"
    assert len(case["sources"]) == 3
    assert "Profile note." in case["notes"]
    assert "Target note." in case["notes"]


def test_build_cases_from_profiles_requires_non_empty_control_ids():
    profiles = [
        {
            "enabled": True,
            "person_id": "template_player",
            "person_name": "Template Player",
            "birth": {
                "date": "1980-01-01",
                "time": "12:00",
                "place": "New York, New York, USA",
            },
            "performances": [
                {
                    "performance_id": "target_win",
                    "date": "2010-06-01",
                    "location": {"label": "Las Vegas, NV, United States"},
                }
            ],
            "benchmark_targets": [
                {
                    "performance_id": "target_win",
                    "control_ids": [],
                }
            ],
        }
    ]

    try:
        build_cases_from_profiles(profiles)
    except ValueError as exc:
        assert "requires non-empty control_ids" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty control_ids")


def test_write_cases_jsonl_renders_single_line_jsonl(tmp_path):
    output = tmp_path / "cases.jsonl"
    path = write_cases_jsonl(
        [
            {
                "enabled": False,
                "case_id": "example",
                "goal_id": "gambling_luck",
                "person_name": "Example",
                "birth": {"date": "1980-01-01", "time": "12:00", "place": "Example"},
                "event": {"type": "poker_result", "date": "2010-01-01", "location": {"label": "Example"}},
                "controls": [{"label": "Control", "reason": "Example"}],
            }
        ],
        output,
    )

    assert path == output.resolve()
    assert output.read_text(encoding="utf-8").count("\n") == 1


def test_real_profile_seed_builds_cases():
    dataset = Path(__file__).resolve().parent / "benchmarks" / "astrocartography" / "astrodatabank_poker_profiles.jsonl"

    profiles = load_poker_profiles([dataset])
    cases = build_cases_from_profiles(profiles)

    assert len(cases) == 5
    assert all(case["goal_id"] == "gambling_luck" for case in cases)
    assert all(case["benchmark_family"] == "astrodatabank_poker" for case in cases)
    assert all(case["benchmark_type"] == "within_person_venue_performance" for case in cases)
    assert any(case["birth"]["data_quality"] == "AA" for case in cases)
    assert any(case["birth"]["data_quality"] == "A" for case in cases)
