from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mundane_analysis_benchmark_runner import (
    build_analysis_request_from_case,
    infer_chart_type_candidates,
    render_markdown_report,
    run_mundane_analysis_benchmark_suite,
)


def _fake_bundle_resolver(dt_iso, location, timezone_name, house_system_code, **kwargs):
    return {
        "chart_data": {
            "ascendant": 0.0,
            "midheaven": 90.0,
            "houses": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
            "house_rulers": {"1": "Mars", "7": "Venus", "10": "Sun"},
            "planets": {
                "Sun": {"longitude": 91.0, "sign": "Cancer", "house": 10, "retrograde": False, "speed": 1.0},
                "Moon": {"longitude": 179.0, "sign": "Virgo", "house": 7, "retrograde": False, "speed": 12.0},
                "Mars": {"longitude": 3.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 0.5},
                "Venus": {"longitude": 92.0, "sign": "Cancer", "house": 10, "retrograde": False, "speed": 1.0},
                "Saturn": {"longitude": 240.0, "sign": "Sagittarius", "house": 9, "retrograde": False, "speed": 0.1},
                "Jupiter": {"longitude": 120.0, "sign": "Leo", "house": 5, "retrograde": False, "speed": 0.1},
                "North Node": {"longitude": 12.0, "sign": "Aries", "house": 1, "retrograde": True, "speed": -0.1},
            },
        },
        "meta": {
            "timestamp": dt_iso,
            "location": location,
            "timezone": timezone_name,
            "latitude": kwargs.get("latitude"),
            "longitude": kwargs.get("longitude"),
        },
    }


def _case(**overrides):
    payload = {
        "enabled": True,
        "case_id": "bench_war_outbreak",
        "domain_id": "war_outbreak",
        "label": "Benchmark war outbreak",
        "benchmark_type": "historical_event",
        "chart_basis": ["war_event_chart"],
        "seed_quality": "source_explicit",
        "event": {
            "type": "event",
            "date": "1861-04-12",
            "time": "04:30",
            "location": "Charleston Harbor, South Carolina, USA",
            "polity": "United States of America",
            "counterpart": "Confederate States of America",
        },
        "expected_domain_lead": "war_outbreak",
        "expected_interpretations": [
            "first_house_tracks_aggressor",
            "seventh_house_tracks_defender",
            "event_chart_is_preferred_when_exact_hostilities_are_known",
        ],
        "source_assertions": [
            {
                "title": "Fixture source",
                "raw_file": "backend/mundane_analysis_benchmark_runner.py",
                "normalized_file": "backend/mundane_analysis_benchmark_runner.py",
                "claim": "Fixture claim.",
            }
        ],
    }
    payload.update(overrides)
    return payload


def _write_jsonl(path, cases):
    path.write_text("\n".join(json.dumps(case) for case in cases) + "\n", encoding="utf-8")


def test_infers_and_builds_mundane_analysis_request_from_historical_event():
    case = _case()

    assert infer_chart_type_candidates(case)[0] == "war_event"
    request = build_analysis_request_from_case(case, chart_type="war_event")

    assert request["chart_type"] == "war_event"
    assert request["domain"] == "war_outbreak"
    assert request["event_datetime"] == "1861-04-12T04:30:00"
    assert request["event_location"] == "Charleston Harbor, South Carolina, USA"
    assert request["polity_id"] == "united_states"
    assert request["location_context_type"] == "event_chart"


def test_analysis_benchmark_runs_true_event_against_engine_output(tmp_path):
    dataset = tmp_path / "sample_mundane_cases.jsonl"
    _write_jsonl(dataset, [_case()])

    report = run_mundane_analysis_benchmark_suite(
        [dataset],
        bundle_resolver=_fake_bundle_resolver,
        minimum_score=1,
    )

    assert report["case_count"] == 1
    assert report["executed_count"] == 1
    assert report["pass_count"] == 1
    row = report["results"][0]
    assert row["status"] == "pass"
    assert row["true_event"]["date"] == "1861-04-12"
    assert row["selected_chart_type"] == "war_event"
    assert row["engine_output"]["domain_id"] == "war_outbreak"
    assert row["engine_output"]["score"] >= 1
    assert "War-event anchor" in row["engine_output"]["matched_rule_labels"]
    assert row["checks"]["domain_match"] is True


def test_analysis_benchmark_dedupes_duplicate_case_ids_by_default(tmp_path):
    dataset_a = tmp_path / "sample_mundane_cases_a.jsonl"
    dataset_b = tmp_path / "sample_mundane_cases_b.jsonl"
    _write_jsonl(dataset_a, [_case(label="First copy")])
    _write_jsonl(dataset_b, [_case(label="Second copy")])

    report = run_mundane_analysis_benchmark_suite(
        [dataset_a, dataset_b],
        bundle_resolver=_fake_bundle_resolver,
        minimum_score=1,
    )
    raw_report = run_mundane_analysis_benchmark_suite(
        [dataset_a, dataset_b],
        bundle_resolver=_fake_bundle_resolver,
        include_duplicate_cases=True,
        minimum_score=1,
    )

    assert report["dedupe_case_ids"] is True
    assert report["case_count"] == 1
    assert report["duplicate_input_count"] == 1
    assert report["input_skipped_counts"]["duplicate_case_id"] == 1
    assert report["skipped_inputs"][0]["duplicate_of_dataset"] == str(dataset_a.resolve())
    assert raw_report["dedupe_case_ids"] is False
    assert raw_report["case_count"] == 2
    assert raw_report["duplicate_input_count"] == 0


def test_analysis_benchmark_bundle_cache_reuses_duplicate_chart_requests(tmp_path):
    dataset_a = tmp_path / "sample_mundane_cases_a.jsonl"
    dataset_b = tmp_path / "sample_mundane_cases_b.jsonl"
    _write_jsonl(dataset_a, [_case()])
    _write_jsonl(dataset_b, [_case()])
    calls = {"count": 0}

    def counting_resolver(*args, **kwargs):
        calls["count"] += 1
        return _fake_bundle_resolver(*args, **kwargs)

    report = run_mundane_analysis_benchmark_suite(
        [dataset_a, dataset_b],
        bundle_resolver=counting_resolver,
        include_duplicate_cases=True,
        minimum_score=1,
    )

    assert report["case_count"] == 2
    assert calls["count"] == 1
    assert report["bundle_cache"]["enabled"] is True
    assert report["bundle_cache"]["hits"] >= 1
    assert report["bundle_cache"]["misses"] == 1


def test_analysis_benchmark_skips_domains_without_analysis_evaluator(tmp_path):
    dataset = tmp_path / "sample_mundane_cases.jsonl"
    unsupported = _case(
        case_id="national_chart_proving_fixture",
        domain_id="national_chart_proving",
        expected_domain_lead="national_chart_proving",
        benchmark_type="national_chart_proving",
        chart_basis=["national_chart_progression"],
    )
    _write_jsonl(dataset, [unsupported])

    report = run_mundane_analysis_benchmark_suite(
        [dataset],
        bundle_resolver=_fake_bundle_resolver,
    )

    assert report["case_count"] == 1
    assert report["executed_count"] == 0
    assert report["skipped_count"] == 1
    assert report["results"][0]["skip_reason"] == "unsupported_domain"


def test_analysis_benchmark_markdown_lists_true_event_vs_engine_output(tmp_path):
    dataset = tmp_path / "sample_mundane_cases.jsonl"
    _write_jsonl(dataset, [_case()])
    report = run_mundane_analysis_benchmark_suite([dataset], bundle_resolver=_fake_bundle_resolver)

    markdown = render_markdown_report(report)

    assert "# Mundo / Mundane Analysis Benchmark" in markdown
    assert "## True Event vs Engine Output" in markdown
    assert "`bench_war_outbreak`" in markdown
    assert "War-event anchor" in markdown
