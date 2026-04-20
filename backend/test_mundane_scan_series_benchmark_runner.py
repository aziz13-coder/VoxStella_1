from pathlib import Path
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mundane_scan_series_benchmark_runner


def test_evaluate_scanner_series_case_result_matches_expected_breakout_place():
    case = {
        "case_id": "series_case",
        "label": "Series case",
        "benchmark_refs": ["benchmark_ref"],
        "series_expectation": {
            "expected_time_slices": 3,
            "expected_place_tokens_any": ["tehran"],
            "expected_breakout_place_tokens_any": ["tehran"],
            "max_breakout_rank": 2,
            "minimum_peak_scan_score": 10,
            "minimum_breakout_index": 10,
            "expected_breakout_kind_any": ["opening_break_candidate", "sustained_theater_candidate"],
            "require_nonzero_series": True,
            "require_series_alignment": True,
        },
    }
    result = {
        "series": {
            "timeline": [
                "2026-02-28T00:00:00+03:30",
                "2026-02-28T06:00:00+03:30",
                "2026-02-28T12:00:00+03:30",
            ],
            "places": [
                {
                    "location": {"label": "Tehran, Iran"},
                    "peak_scan_score": 24,
                    "breakout_index": 25,
                    "breakout_kind": "opening_break_candidate",
                    "series": [
                        {"datetime": "2026-02-28T00:00:00+03:30"},
                        {"datetime": "2026-02-28T06:00:00+03:30"},
                        {"datetime": "2026-02-28T12:00:00+03:30"},
                    ],
                }
            ],
            "breakout_candidates": [
                {"rank": 1, "location": {"label": "Tehran, Iran"}},
            ],
            "series_overview": {"top_breakout_location": {"label": "Tehran, Iran"}},
        }
    }

    evaluation = mundane_scan_series_benchmark_runner.evaluate_scanner_series_case_result(case, result)

    assert evaluation["passed"] is True
    assert evaluation["diagnostic_status"] == "strong_pass"
    assert evaluation["matched_place"] == "Tehran, Iran"
    assert evaluation["matched_breakout_rank"] == 1


def test_evaluate_scanner_series_case_result_fails_on_missing_series():
    case = {
        "case_id": "series_case",
        "label": "Series case",
        "benchmark_refs": ["benchmark_ref"],
        "series_expectation": {
            "expected_place_tokens_any": ["tehran"],
            "expected_breakout_place_tokens_any": ["tehran"],
        },
    }
    result = {"series": {"timeline": [], "places": [], "breakout_candidates": []}}

    evaluation = mundane_scan_series_benchmark_runner.evaluate_scanner_series_case_result(case, result)

    assert evaluation["passed"] is False
    assert "missing_series" in evaluation["warning_flags"]


def test_run_scanner_series_benchmark_suite_aggregates_results(monkeypatch):
    cases = [
        {
            "case_id": "case_a",
            "label": "Case A",
            "benchmark_refs": ["ref_a"],
            "series_expectation": {
                "expected_place_tokens_any": ["tehran"],
                "expected_breakout_place_tokens_any": ["tehran"],
                "require_series_alignment": True,
            },
        },
        {
            "case_id": "case_b",
            "label": "Case B",
            "benchmark_refs": ["ref_b"],
            "series_expectation": {
                "expected_place_tokens_any": ["london"],
                "expected_breakout_place_tokens_any": ["london"],
            },
        },
    ]

    monkeypatch.setattr(
        mundane_scan_series_benchmark_runner,
        "load_scanner_series_benchmark_cases",
        lambda **kwargs: (cases, []),
    )

    def _fake_execute(case, *, active_clock):
        if case["case_id"] == "case_a":
            return {
                "series": {
                    "timeline": ["2026-02-28T00:00:00+03:30"],
                    "places": [
                        {
                            "location": {"label": "Tehran, Iran"},
                            "peak_scan_score": 20,
                            "breakout_index": 20,
                            "breakout_kind": "opening_break_candidate",
                            "series": [{"datetime": "2026-02-28T00:00:00+03:30"}],
                        }
                    ],
                    "breakout_candidates": [{"rank": 1, "location": {"label": "Tehran, Iran"}}],
                    "series_overview": {},
                }
            }
        return {"series": {"timeline": ["2026-02-28T00:00:00+03:30"], "places": [], "breakout_candidates": []}}

    monkeypatch.setattr(mundane_scan_series_benchmark_runner, "execute_scanner_series_case", _fake_execute)

    summary = mundane_scan_series_benchmark_runner.run_scanner_series_benchmark_suite()

    assert summary["case_count"] == 2
    assert summary["pass_count"] == 1
    assert summary["fail_count"] == 1
    assert summary["strong_pass_count"] == 1


def test_evaluate_scanner_series_case_result_can_weak_pass_when_breakout_is_not_top_rank():
    case = {
        "case_id": "series_case",
        "label": "Series case",
        "benchmark_refs": ["benchmark_ref"],
        "series_expectation": {
            "expected_place_tokens_any": ["baghdad"],
            "expected_breakout_place_tokens_any": ["baghdad"],
            "max_breakout_rank": 2,
            "minimum_peak_scan_score": 20,
            "minimum_breakout_index": 20,
            "require_nonzero_series": True,
            "require_series_alignment": True,
        },
    }
    result = {
        "series": {
            "timeline": ["2026-02-28T00:00:00+03:30"],
            "places": [
                {
                    "location": {"label": "Baghdad, Iraq"},
                    "peak_scan_score": 24,
                    "breakout_index": 24,
                    "breakout_kind": "opening_break_candidate",
                    "series": [{"datetime": "2026-02-28T00:00:00+03:30"}],
                }
            ],
            "breakout_candidates": [
                {"rank": 1, "location": {"label": "Jeddah, Saudi Arabia"}},
                {"rank": 2, "location": {"label": "Baghdad, Iraq"}},
            ],
            "series_overview": {},
        }
    }

    evaluation = mundane_scan_series_benchmark_runner.evaluate_scanner_series_case_result(case, result)

    assert evaluation["passed"] is True
    assert evaluation["diagnostic_status"] == "weak_pass"
    assert evaluation["matched_breakout_rank"] == 2
    assert "expected_breakout_not_top_rank" in evaluation["warning_flags"]
