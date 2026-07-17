import argparse
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import estate_benchmark


def _write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _case_row():
    return {
        "case_id": "case-001",
        "direction": "buy",
        "location": "Jerusalem",
        "timezone": "Asia/Jerusalem",
        "house_system": "placidus",
        "latitude": "31.778",
        "longitude": "35.235",
        "scan_start": "2026-04-18T00:00:00+00:00",
        "scan_end": "2026-04-19T00:00:00+00:00",
        "step_minutes": "360",
        "chosen_event_datetime": "2026-04-18T12:00:00+00:00",
        "deal_completed": "true",
        "asking_price": "1000000",
        "final_price": "1015000",
        "price_delta_percent": "1.5",
        "time_to_close_days": "45",
        "inspection_issue": "false",
        "appraisal_issue": "false",
        "legal_issue": "false",
        "notes": "synthetic smoke row",
    }


def test_backtest_rank_computes_model_and_baseline_columns(tmp_path):
    dataset = tmp_path / "estate_cases.csv"
    output = tmp_path / "estate_cases_ranked.csv"
    _write_csv(dataset, estate_benchmark.BACKTEST_COLUMNS, [_case_row()])

    payload = estate_benchmark.rank_backtest(
        argparse.Namespace(
            dataset=str(dataset),
            output=str(output),
            in_place=False,
            engine="synthetic",
            top_limit=3,
        )
    )
    rows = _read_csv(output)

    assert payload["ranked_cases"] == 1
    assert rows[0]["benchmark_status"] == "ranked"
    assert rows[0]["chosen_rank"].isdigit()
    assert rows[0]["random_window_rank"].isdigit()
    assert rows[0]["moon_phase_baseline_rank"].isdigit()
    assert rows[0]["latitude_sign_baseline_rank"].isdigit()
    assert rows[0]["event_line_baseline_rank"].isdigit()
    assert float(rows[0]["chosen_score"]) == float(rows[0]["chosen_score"])

    top_windows = json.loads(rows[0]["top_windows_json"])
    assert len(top_windows) == 3
    assert {"timestamp", "score", "event_line_score"} <= set(top_windows[0])

    validation = estate_benchmark.validate_backtest(argparse.Namespace(dataset=str(output)))
    assert validation["missing_columns"] == []
    assert validation["comparison_ready_cases"] == 1
    assert validation["comparisons"]["random_window_rank"]["cases"] == 1


def test_freeze_case_appends_ranked_prospective_row(tmp_path):
    log = tmp_path / "estate_freeze.csv"

    payload = estate_benchmark.freeze_case(
        argparse.Namespace(
            log=str(log),
            case_id="live-001",
            direction="buy",
            location="Jerusalem",
            timezone="Asia/Jerusalem",
            house_system="placidus",
            latitude=31.778,
            longitude=35.235,
            scan_start="2026-04-18T00:00:00+00:00",
            scan_end="2026-04-19T00:00:00+00:00",
            step_minutes=360,
            selected_event="2026-04-18T12:00:00+00:00",
            participant_snap_id=None,
            participant_label="Buyer A",
            participant_chart_path=None,
            participant_chart_json=None,
            model_version="estate-test-freeze-v1",
            engine="synthetic",
            top_limit=2,
            replace=True,
            notes="freeze smoke row",
        )
    )
    rows = _read_csv(log)

    assert payload["row_count"] == 1
    assert rows[0]["case_id"] == "live-001"
    assert rows[0]["model_version"] == "estate-test-freeze-v1"
    assert rows[0]["selected_rank"].isdigit()
    assert len(json.loads(rows[0]["top_windows_json"])) == 2

    validation = estate_benchmark.validate_prospective_freeze(argparse.Namespace(log=str(log)))
    assert validation["missing_columns"] == []
    assert validation["invalid_top_windows_json_rows"] == []
    assert validation["frozen_model_versions"] == ["estate-test-freeze-v1"]


def test_benchmark_suite_runs_all_sample_checks():
    payload = estate_benchmark.run_benchmark_suite(
        argparse.Namespace(
            days=1,
            step_minutes=360,
            latitudes="31.778",
            house_systems="placidus",
            engine="synthetic",
            top_limit=3,
        )
    )

    assert payload["ok"] is True
    assert payload["scan_summary"]["scenario_count"] == 1
    assert payload["scan_summary"]["all_no_crashes"] is True
    assert payload["sample_summary"]["backtest_comparison_ready_cases"] == 1
    assert payload["sample_summary"]["sample_rerank_ranked_cases"] == 1
    assert payload["validations"]["prospective_sample"]["invalid_top_windows_json_rows"] == []
