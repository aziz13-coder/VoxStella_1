from pathlib import Path
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mundane_national_chart_proving_runner


def test_evaluate_national_chart_proving_result_strong_pass():
    case = {
        "case_id": "proving_case",
        "label": "Proving case",
        "preferred_candidate_id": "france_fourth_republic_1946",
        "candidate_ids": ["france_third_republic_1870", "france_fourth_republic_1946"],
        "seed_quality": "source_explicit",
        "source_assertions": [{"title": "Carter"}],
    }
    result = {
        "polity_id": "france",
        "anchor_datetime": "1951-06-01T12:00:00",
        "selection_mode": True,
        "preferred_runtime_chart_id": "france_fourth_republic_1946",
        "context": {
            "reference_chart": {
                "id": "france_fourth_republic_1946",
                "selection_basis": "period_match",
            }
        },
    }

    evaluation = mundane_national_chart_proving_runner.evaluate_national_chart_proving_result(case, result)

    assert evaluation["passed"] is True
    assert evaluation["diagnostic_status"] == "strong_pass"
    assert evaluation["warning_flags"] == []


def test_evaluate_national_chart_proving_result_marks_seeded_weak_pass():
    case = {
        "case_id": "seeded_case",
        "label": "Seeded case",
        "preferred_candidate_id": "india_republic_1950",
        "candidate_ids": ["india_dominion_1947", "india_republic_1950"],
        "seed_quality": "source_seeded",
        "source_assertions": [{"title": "Carter"}],
    }
    result = {
        "polity_id": "india",
        "anchor_datetime": "1951-01-26T12:00:00",
        "selection_mode": True,
        "preferred_runtime_chart_id": "india_republic_1950",
        "context": {
            "reference_chart": {
                "id": "india_republic_1950",
                "selection_basis": "period_match",
            }
        },
    }

    evaluation = mundane_national_chart_proving_runner.evaluate_national_chart_proving_result(case, result)

    assert evaluation["passed"] is True
    assert evaluation["diagnostic_status"] == "weak_pass"
    assert "seeded_evidence" in evaluation["warning_flags"]


def test_run_national_chart_proving_benchmark_suite_aggregates_results(monkeypatch):
    cases = [
        {
            "case_id": "case_a",
            "label": "Case A",
            "preferred_candidate_id": "israel_proclamation_1948",
            "candidate_ids": ["israel_proclamation_1948", "israel_mandate_termination_1948"],
            "seed_quality": "source_explicit",
            "source_assertions": [{"title": "Watters"}],
        },
        {
            "case_id": "case_b",
            "label": "Case B",
            "preferred_candidate_id": "india_republic_1950",
            "candidate_ids": ["india_dominion_1947", "india_republic_1950"],
            "seed_quality": "source_seeded",
            "source_assertions": [{"title": "Carter"}],
        },
    ]

    monkeypatch.setattr(
        mundane_national_chart_proving_runner,
        "load_national_chart_proving_cases",
        lambda **kwargs: (cases, []),
    )
    monkeypatch.setattr(
        mundane_national_chart_proving_runner,
        "_load_candidate_index",
        lambda: {
            "israel_proclamation_1948": {"polity_id": "israel"},
            "israel_mandate_termination_1948": {"polity_id": "israel"},
            "india_dominion_1947": {"polity_id": "india"},
            "india_republic_1950": {"polity_id": "india"},
        },
    )
    monkeypatch.setattr(
        mundane_national_chart_proving_runner,
        "_index_polities",
        lambda: {
            "israel": {"id": "israel"},
            "india": {"id": "india"},
        },
    )

    def _fake_execute(case, *, active_clock, candidate_index, indexed_polities):
        if case["case_id"] == "case_a":
            return {
                "polity_id": "israel",
                "anchor_datetime": "1967-06-05T12:00:00",
                "selection_mode": True,
                "preferred_runtime_chart_id": "israel_proclamation_1948",
                "context": {"reference_chart": {"id": "israel_proclamation_1948", "selection_basis": "period_match"}},
            }
        return {
            "polity_id": "india",
            "anchor_datetime": "1951-01-26T12:00:00",
            "selection_mode": True,
            "preferred_runtime_chart_id": "india_republic_1950",
            "context": {"reference_chart": {"id": "india_republic_1950", "selection_basis": "period_match"}},
        }

    monkeypatch.setattr(
        mundane_national_chart_proving_runner,
        "execute_national_chart_proving_case",
        _fake_execute,
    )

    summary = mundane_national_chart_proving_runner.run_national_chart_proving_benchmark_suite()

    assert summary["case_count"] == 2
    assert summary["pass_count"] == 2
    assert summary["strong_pass_count"] == 1
    assert summary["weak_pass_count"] == 1
