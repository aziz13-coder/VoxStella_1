from pathlib import Path
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mundane_scan_benchmark_runner


def test_evaluate_scanner_case_result_matches_location_token_within_rank():
    case = {
        "case_id": "scanner_case",
        "label": "Scanner case",
        "benchmark_refs": ["benchmark_ref"],
        "expectation": {
            "minimum_results": 1,
            "location_tokens_any": ["london"],
            "max_rank": 4,
        },
    }
    result = {
        "results": [
            {"rank": 1, "location": {"label": "Belfast, United Kingdom", "country_code": "GB"}, "scan_level": "leading"},
            {"rank": 4, "location": {"label": "London, United Kingdom", "country_code": "GB"}, "scan_level": "watch"},
        ],
        "counts": {"returned": 2},
    }

    evaluation = mundane_scan_benchmark_runner.evaluate_scanner_case_result(case, result)

    assert evaluation["passed"] is True
    assert evaluation["diagnostic_status"] == "weak_pass"
    assert evaluation["matched_rank"] == 4
    assert evaluation["matched_location"] == "London, United Kingdom"
    assert "expected_location_not_top_rank" in evaluation["warning_flags"]


def test_evaluate_scanner_case_result_respects_max_rank():
    case = {
        "case_id": "scanner_case",
        "label": "Scanner case",
        "benchmark_refs": ["benchmark_ref"],
        "expectation": {
            "minimum_results": 1,
            "location_tokens_any": ["london"],
            "max_rank": 3,
        },
    }
    result = {
        "results": [
            {"rank": 4, "location": {"label": "London, United Kingdom", "country_code": "GB"}, "scan_level": "watch"},
        ],
        "counts": {"returned": 1},
    }

    evaluation = mundane_scan_benchmark_runner.evaluate_scanner_case_result(case, result)

    assert evaluation["passed"] is False
    assert evaluation["diagnostic_status"] == "fail"
    assert evaluation["matched_rank"] is None


def test_run_scanner_benchmark_suite_aggregates_results(monkeypatch):
    cases = [
        {
            "case_id": "case_a",
            "label": "Case A",
            "benchmark_refs": ["ref_a"],
            "expectation": {"minimum_results": 1, "location_tokens_any": ["tehran"]},
        },
        {
            "case_id": "case_b",
            "label": "Case B",
            "benchmark_refs": ["ref_b"],
            "expectation": {"minimum_results": 1, "location_tokens_any": ["london"]},
        },
    ]

    monkeypatch.setattr(
        mundane_scan_benchmark_runner,
        "load_scanner_benchmark_cases",
        lambda **kwargs: (cases, []),
    )

    def _fake_execute(case, *, active_clock):
        if case["case_id"] == "case_a":
            return {
                "results": [
                    {"rank": 1, "location": {"label": "Tehran, Iran", "country_code": "IR"}, "score": 10, "level": "elevated", "scan_level": "dominant"},
                    {"rank": 2, "location": {"label": "Qom, Iran", "country_code": "IR"}, "score": 4, "level": "quiet", "scan_level": "active"},
                    {"rank": 3, "location": {"label": "Shiraz, Iran", "country_code": "IR"}, "score": 1, "level": "quiet", "scan_level": "watch"},
                ],
                "counts": {"returned": 3},
            }
        return {"results": [{"rank": 1, "location": {"label": "Belfast, United Kingdom", "country_code": "GB"}, "score": 0, "level": "quiet", "scan_level": "background"}], "counts": {"returned": 1}}

    monkeypatch.setattr(mundane_scan_benchmark_runner, "execute_scanner_case", _fake_execute)

    summary = mundane_scan_benchmark_runner.run_scanner_benchmark_suite()

    assert summary["case_count"] == 2
    assert summary["pass_count"] == 1
    assert summary["fail_count"] == 1
    assert summary["weak_pass_count"] == 0
    assert summary["strong_pass_count"] == 1


def test_evaluate_scanner_case_result_prefers_scan_score_when_present():
    case = {
        "case_id": "scanner_case",
        "label": "Scanner case",
        "benchmark_refs": ["benchmark_ref"],
        "expectation": {
            "minimum_results": 1,
            "location_tokens_any": ["tehran"],
            "max_rank": 2,
        },
    }
    result = {
        "results": [
            {"rank": 1, "location": {"label": "Tehran, Iran", "country_code": "IR"}, "score": 0, "scan_score": 11, "scan_level": "leading"},
            {"rank": 2, "location": {"label": "Baghdad, Iraq", "country_code": "IQ"}, "score": 0, "scan_score": 3, "scan_level": "watch"},
        ],
        "counts": {"returned": 2},
    }

    evaluation = mundane_scan_benchmark_runner.evaluate_scanner_case_result(case, result)

    assert evaluation["passed"] is True
    assert evaluation["matched_score"] == 11
    assert evaluation["top_score"] == 11


def test_evaluate_scanner_case_result_can_require_scan_separation():
    case = {
        "case_id": "scanner_case",
        "label": "Scanner case",
        "benchmark_refs": ["benchmark_ref"],
        "expectation": {
            "minimum_results": 1,
            "location_tokens_any": ["tehran"],
            "max_rank": 2,
            "require_nonzero_top_score": True,
            "require_scan_separation": True,
        },
    }
    result = {
        "results": [
            {"rank": 1, "location": {"label": "Tehran, Iran", "country_code": "IR"}, "score": 0, "scan_score": 0, "scan_level": "background"},
            {"rank": 2, "location": {"label": "Baghdad, Iraq", "country_code": "IQ"}, "score": 0, "scan_score": 0, "scan_level": "background"},
        ],
        "counts": {"returned": 2},
    }

    evaluation = mundane_scan_benchmark_runner.evaluate_scanner_case_result(case, result)

    assert evaluation["passed"] is False
    assert "expected_nonzero_top_score" in evaluation["warning_flags"]
    assert "scan_separation_requirement_failed" in evaluation["warning_flags"]
