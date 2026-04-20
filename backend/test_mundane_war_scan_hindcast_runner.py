from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mundane_war_scan_hindcast_runner as runner


def _case(case_id: str, domain: str = "war_outbreak") -> dict:
    return {
        "enabled": True,
        "case_id": case_id,
        "label": case_id,
        "request": {
            "chart_type": "war_event",
            "domain": domain,
            "region_id": "persian_gulf",
            "scan_mode": "spatiotemporal_scan",
            "start_datetime": "2026-04-01T00:00:00+00:00",
            "end_datetime": "2026-04-02T00:00:00+00:00",
            "time_step_hours": 6,
        },
        "target_window": {
            "start_datetime": "2026-04-01T12:00:00+00:00",
            "end_datetime": "2026-04-01T18:00:00+00:00",
        },
        "control_windows": [
            {
                "start_datetime": "2026-04-01T00:00:00+00:00",
                "end_datetime": "2026-04-01T06:00:00+00:00",
            },
            {
                "start_datetime": "2026-04-02T00:00:00+00:00",
                "end_datetime": "2026-04-02T00:00:00+00:00",
            },
        ],
        "target_place_tokens_any": ["Baghdad"],
        "target_country_codes_any": ["IQ"],
        "scoring_expectations": {
            "max_target_place_rank": 2,
            "min_target_percentile": 0.75,
            "max_peak_distance_hours": 24,
        },
        "benchmark_refs": ["war_outbreak_desert_storm_1991"],
    }


def _scan_result(place_label: str, scores: list[float], peak_datetime: str, country_code: str = "IQ") -> dict:
    timeline = [
        "2026-04-01T00:00:00+00:00",
        "2026-04-01T06:00:00+00:00",
        "2026-04-01T12:00:00+00:00",
        "2026-04-01T18:00:00+00:00",
        "2026-04-02T00:00:00+00:00",
    ]
    series = [
        {
            "datetime": dt,
            "scan_score": score,
            "absolute_score": score,
            "scan_level": "dominant" if score == max(scores) else "watch",
            "absolute_level": "critical" if score == max(scores) else "watch",
        }
        for dt, score in zip(timeline, scores)
    ]
    peak_score = max(scores)
    return {
        "counts": {"candidate_locations": 6, "time_slices": 5, "returned": 8, "returned_places": 4},
        "series": {
            "places": [
                {
                    "location": {"label": place_label, "country_code": country_code},
                    "peak_scan_score": peak_score,
                    "peak_datetime": peak_datetime,
                    "peak_window_start_datetime": peak_datetime,
                    "peak_window_end_datetime": peak_datetime,
                    "peak_selection": "single_peak",
                    "breakout_index": peak_score,
                    "series": series,
                }
            ],
            "series_overview": {
                "top_breakout_location": {"label": place_label, "country_code": country_code},
            },
        },
    }


def test_run_war_scan_hindcast_suite_summarizes_pass_and_fail(monkeypatch):
    monkeypatch.setattr(
        runner,
        "load_war_scan_hindcast_cases",
        lambda **_: [_case("pass_case"), _case("fail_case", domain="campaign_escalation")],
    )

    def fake_run(case, *, quiet_engine):
        if case["case_id"] == "pass_case":
            return _scan_result("Baghdad, Iraq", [10, 20, 40, 38, 12], "2026-04-01T12:00:00+00:00")
        return _scan_result("Baghdad, Iraq", [45, 38, 14, 12, 11], "2026-04-01T00:00:00+00:00")

    monkeypatch.setattr(runner, "_run_case_scan", fake_run)

    report = runner.run_war_scan_hindcast_suite()

    assert report["case_count"] == 2
    assert report["place_recall_count"] == 2
    assert report["alignment_pass_count"] == 1
    assert report["target_window_hit_count"] == 1
    assert report["family_summary"]["war_outbreak"]["alignment_pass_count"] == 1
    assert report["family_summary"]["campaign_escalation"]["alignment_pass_count"] == 0
    assert report["family_summary"]["campaign_escalation"]["failure_reasons"]["control_window_outperformed_target"] == 1
    assert report["cases"][0]["alignment_passed"] is True
    assert report["cases"][0]["target_beats_all_controls"] is True
    assert report["cases"][1]["alignment_passed"] is False
    assert "control_window_outperformed_target" in report["cases"][1]["failure_reasons"]


def test_target_place_not_returned_fails_cleanly():
    summary = runner._summarize_case(
        _case("missing_place"),
        {
            "counts": {"candidate_locations": 6, "time_slices": 5},
            "series": {"places": [], "series_overview": {}},
        },
    )

    assert summary["target_place_found"] is False
    assert summary["alignment_passed"] is False
    assert "target_place_not_returned" in summary["failure_reasons"]


def test_place_matching_does_not_accept_country_only_when_place_token_exists():
    assert runner._place_matches(
        {"location": {"label": "Chula Vista, United States", "country_code": "US"}},
        {
            "target_place_tokens_any": ["Honolulu"],
            "target_country_codes_any": ["US"],
        },
    ) is False
    assert runner._place_matches(
        {"location": {"label": "Honolulu, United States", "country_code": "US"}},
        {
            "target_place_tokens_any": ["Honolulu"],
            "target_country_codes_any": ["US"],
        },
    ) is True


def test_critical_answer_stays_cautious():
    verdict = runner._critical_answer(
        {
            "place_recall_rate": 0.8,
            "alignment_pass_rate": 0.6,
            "target_window_hit_rate": 0.2,
        }
    )
    assert "mixed hindcast signal" in verdict.lower()
