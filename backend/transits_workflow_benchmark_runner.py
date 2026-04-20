from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Optional, Tuple

from validate_transits_benchmark_datasets import (
    DOCUMENTED_HINDCAST_FILE,
    EXACT_SCAN_FILE,
    PREDICTOR_STABILITY_FILE,
    load_jsonl_cases,
    validate_documented_hindcast_case,
    validate_exact_scan_consistency_case,
    validate_predictor_stability_case,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _ensure_dev_env() -> None:
    os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
    os.environ.setdefault("VOX_STELLA_ENV", "development")


def _build_test_client():
    _ensure_dev_env()
    backend_dir = Path(__file__).resolve().parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    import app as app_module  # type: ignore

    return app_module.app.test_client()


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split()).lower()


def _parse_iso(value: Any) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _query_base(case: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "natal_datetime": case["natal_datetime"],
        "natal_location": case["natal_location"],
        "natal_timezone": case["natal_timezone"],
        "house_system_code": case["house_system_code"],
    }


def _signature_from_hit(hit: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(hit.get("transiting") or "").strip(),
            str(hit.get("aspect") or "").strip(),
            str(hit.get("target_label") or hit.get("natal") or "").strip(),
        ]
    )


def _signature_from_prediction(prediction: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(prediction.get("event_type") or "").strip(),
            str(prediction.get("life_area") or "").strip(),
            str(prediction.get("label") or "").strip(),
        ]
    )


def _run_get(client, path: str, query: Dict[str, Any], *, quiet: bool) -> Dict[str, Any]:
    sink = StringIO()
    context = redirect_stdout(sink) if quiet else nullcontext()
    err_context = redirect_stderr(sink) if quiet else nullcontext()
    with context, err_context:
        response = client.get(path, query_string=query)
    payload = response.get_json()
    if response.status_code != 200:
        raise ValueError(f"{path} returned {response.status_code}: {payload}")
    if not isinstance(payload, dict) or not payload.get("success"):
        raise ValueError(f"{path} returned unsuccessful payload: {payload}")
    return payload["data"]


class nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


def load_exact_scan_consistency_cases(*, case_id: Optional[str] = None, include_disabled: bool = False) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id)
    for payload in load_jsonl_cases(Path(EXACT_SCAN_FILE).resolve()):
        validate_exact_scan_consistency_case(payload, Path(EXACT_SCAN_FILE).resolve())
        if case_filter and _normalize_text(payload.get("case_id")) != case_filter:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            continue
        cases.append(dict(payload))
    return cases


def load_predictor_stability_cases(*, case_id: Optional[str] = None, include_disabled: bool = False) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id)
    for payload in load_jsonl_cases(Path(PREDICTOR_STABILITY_FILE).resolve()):
        validate_predictor_stability_case(payload, Path(PREDICTOR_STABILITY_FILE).resolve())
        if case_filter and _normalize_text(payload.get("case_id")) != case_filter:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            continue
        cases.append(dict(payload))
    return cases


def load_documented_hindcast_cases(*, case_id: Optional[str] = None, include_disabled: bool = False) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id)
    for payload in load_jsonl_cases(Path(DOCUMENTED_HINDCAST_FILE).resolve()):
        validate_documented_hindcast_case(payload, Path(DOCUMENTED_HINDCAST_FILE).resolve())
        if case_filter and _normalize_text(payload.get("case_id")) != case_filter:
            continue
        if not include_disabled and not bool(payload.get("enabled")):
            continue
        cases.append(dict(payload))
    return cases


def _find_row_by_timestamp(series: Iterable[Dict[str, Any]], target_iso: str) -> Optional[Dict[str, Any]]:
    target_dt = _parse_iso(target_iso)
    for row in series:
        if not isinstance(row, dict):
            continue
        try:
            if _parse_iso(row.get("timestamp")) == target_dt:
                return row
        except Exception:
            continue
    return None


def run_exact_scan_consistency_case(case: Dict[str, Any], *, client=None, quiet_engine: bool = True) -> Dict[str, Any]:
    client = client or _build_test_client()
    exact_query = _query_base(case)
    exact_query["transit_datetime"] = case["transit_datetime"]
    window_query = _query_base(case)
    window_query.update(
        {
            "start": case["window_start"],
            "end": case["window_end"],
            "step_minutes": case["step_minutes"],
        }
    )
    exact = _run_get(client, "/api/astro-clock/transits", exact_query, quiet=quiet_engine)
    window = _run_get(client, "/api/astro-clock/transits/window", window_query, quiet=quiet_engine)
    row = _find_row_by_timestamp(window.get("series") or [], case["transit_datetime"])
    if row is None:
        raise ValueError(f"{case['case_id']} scan row missing timestamp {case['transit_datetime']}")

    exact_transit_signatures = {_signature_from_hit(hit) for hit in (exact.get("transits") or [])[:5] if isinstance(hit, dict)}
    row_transit_signatures = {_signature_from_hit(hit) for hit in (row.get("top") or [])[:5] if isinstance(hit, dict)}
    exact_prediction_signatures = {_signature_from_prediction(pred) for pred in (exact.get("predictions") or [])[:5] if isinstance(pred, dict)}
    row_prediction_signatures = {_signature_from_prediction(pred) for pred in (row.get("predictions") or [])[:5] if isinstance(pred, dict)}

    transit_overlap = exact_transit_signatures & row_transit_signatures
    prediction_overlap = exact_prediction_signatures & row_prediction_signatures
    passed = (
        len(transit_overlap) >= int(case["expected_transit_overlap_min"])
        and len(prediction_overlap) >= int(case["expected_prediction_overlap_min"])
    )
    return {
        "case_id": case["case_id"],
        "passed": passed,
        "transit_overlap_count": len(transit_overlap),
        "prediction_overlap_count": len(prediction_overlap),
        "transit_overlap": sorted(transit_overlap),
        "prediction_overlap": sorted(prediction_overlap),
        "row_timestamp": row.get("timestamp"),
    }


def _match_prediction_group(groups: List[Dict[str, Any]], *, expected_life_area: str, expected_event_type: str) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    expected_area = _normalize_text(expected_life_area)
    expected_event = _normalize_text(expected_event_type)
    for index, group in enumerate(groups, start=1):
        if not isinstance(group, dict):
            continue
        if _normalize_text(group.get("life_area")) == expected_area and _normalize_text(group.get("event_type")) == expected_event:
            return group, index
    return None, None


def _hours_gap(a: Any, b: Any) -> float:
    return round(abs((_parse_iso(a) - _parse_iso(b)).total_seconds()) / 3600.0, 3)


def run_predictor_stability_case(case: Dict[str, Any], *, client=None, quiet_engine: bool = True) -> Dict[str, Any]:
    client = client or _build_test_client()
    base_query = _query_base(case)
    primary_query = dict(base_query)
    primary_query.update(
        {
            "start": case["window_start"],
            "end": case["window_end"],
            "step_minutes": case["step_minutes_primary"],
        }
    )
    secondary_query = dict(base_query)
    secondary_query.update(
        {
            "start": case["window_start"],
            "end": case["window_end"],
            "step_minutes": case["step_minutes_secondary"],
        }
    )
    primary = _run_get(client, "/api/astro-clock/predictor", primary_query, quiet=quiet_engine)
    secondary = _run_get(client, "/api/astro-clock/predictor", secondary_query, quiet=quiet_engine)
    primary_group, primary_rank = _match_prediction_group(
        primary.get("prediction_groups") or [],
        expected_life_area=case["expected_life_area"],
        expected_event_type=case["expected_event_type"],
    )
    secondary_group, secondary_rank = _match_prediction_group(
        secondary.get("prediction_groups") or [],
        expected_life_area=case["expected_life_area"],
        expected_event_type=case["expected_event_type"],
    )
    dominant_gap = None
    if primary_group and secondary_group:
        dominant_gap = _hours_gap(primary_group.get("dominant_timestamp"), secondary_group.get("dominant_timestamp"))
    passed = bool(
        primary_group
        and secondary_group
        and primary_rank is not None
        and secondary_rank is not None
        and primary_rank <= int(case["max_rank"])
        and secondary_rank <= int(case["max_rank"])
        and dominant_gap is not None
        and dominant_gap <= float(case["max_dominant_gap_hours"])
    )
    return {
        "case_id": case["case_id"],
        "passed": passed,
        "primary_rank": primary_rank,
        "secondary_rank": secondary_rank,
        "dominant_gap_hours": dominant_gap,
        "primary_dominant_timestamp": primary_group.get("dominant_timestamp") if primary_group else None,
        "secondary_dominant_timestamp": secondary_group.get("dominant_timestamp") if secondary_group else None,
    }


def _window_contains(start: Any, end: Any, current: Any) -> bool:
    current_dt = _parse_iso(current)
    return _parse_iso(start) <= current_dt <= _parse_iso(end)


def _window_distance_hours(start: Any, end: Any, current: Any) -> float:
    current_dt = _parse_iso(current)
    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)
    if start_dt <= current_dt <= end_dt:
        return 0.0
    if current_dt < start_dt:
        return round((start_dt - current_dt).total_seconds() / 3600.0, 3)
    return round((current_dt - end_dt).total_seconds() / 3600.0, 3)


def run_documented_hindcast_case(case: Dict[str, Any], *, client=None, quiet_engine: bool = True) -> Dict[str, Any]:
    client = client or _build_test_client()
    query = _query_base(case)
    query.update(
        {
            "start": case["window_start"],
            "end": case["window_end"],
            "step_minutes": case["step_minutes"],
        }
    )
    predictor = _run_get(client, "/api/astro-clock/predictor", query, quiet=quiet_engine)
    groups = predictor.get("prediction_groups") or []
    expected_areas = {_normalize_text(item) for item in case["expected_life_areas"]}
    expected_events = {_normalize_text(item) for item in case["expected_event_types"]}
    matched_group: Optional[Dict[str, Any]] = None
    matched_rank: Optional[int] = None
    for index, group in enumerate(groups, start=1):
        if not isinstance(group, dict):
            continue
        if _normalize_text(group.get("life_area")) in expected_areas and _normalize_text(group.get("event_type")) in expected_events:
            matched_group = group
            matched_rank = index
            break
    peak_distance_hours = None
    target_window_hit = False
    if matched_group is not None:
        peak_distance_hours = _window_distance_hours(
            case["target_window"]["start"],
            case["target_window"]["end"],
            matched_group.get("dominant_timestamp"),
        )
        target_window_hit = _window_contains(
            case["target_window"]["start"],
            case["target_window"]["end"],
            matched_group.get("dominant_timestamp"),
        )
    passed = bool(
        matched_group
        and matched_rank is not None
        and matched_rank <= int(case["max_rank"])
        and peak_distance_hours is not None
        and peak_distance_hours <= float(case["max_peak_distance_hours"])
    )
    return {
        "case_id": case["case_id"],
        "passed": passed,
        "matched_rank": matched_rank,
        "target_window_hit": target_window_hit,
        "peak_distance_hours": peak_distance_hours,
        "dominant_timestamp": matched_group.get("dominant_timestamp") if matched_group else None,
        "matched_group": {
            "event_type": matched_group.get("event_type"),
            "life_area": matched_group.get("life_area"),
            "label": matched_group.get("label"),
        }
        if matched_group
        else None,
    }


def _summarize_results(results: List[Dict[str, Any]], *, extra_numeric: Optional[List[str]] = None) -> Dict[str, Any]:
    extra_numeric = extra_numeric or []
    passed = [row for row in results if row.get("passed")]
    summary: Dict[str, Any] = {
        "case_count": len(results),
        "pass_count": len(passed),
        "pass_rate": round(len(passed) / len(results), 4) if results else 0.0,
    }
    for key in extra_numeric:
        values = [float(row[key]) for row in results if row.get(key) is not None]
        if values:
            summary[f"median_{key}"] = round(median(values), 3)
    return summary


def run_workflow_benchmarks(*, case_id: Optional[str] = None, quiet_engine: bool = True) -> Dict[str, Any]:
    client = _build_test_client()
    exact_results = [run_exact_scan_consistency_case(case, client=client, quiet_engine=quiet_engine) for case in load_exact_scan_consistency_cases(case_id=case_id)]
    predictor_results = [run_predictor_stability_case(case, client=client, quiet_engine=quiet_engine) for case in load_predictor_stability_cases(case_id=case_id)]
    hindcast_results = [run_documented_hindcast_case(case, client=client, quiet_engine=quiet_engine) for case in load_documented_hindcast_cases(case_id=case_id)]
    return {
        "exact_scan_consistency": {
            "summary": _summarize_results(exact_results, extra_numeric=["transit_overlap_count", "prediction_overlap_count"]),
            "results": exact_results,
        },
        "predictor_stability": {
            "summary": _summarize_results(predictor_results, extra_numeric=["dominant_gap_hours"]),
            "results": predictor_results,
        },
        "documented_hindcasts": {
            "summary": _summarize_results(hindcast_results, extra_numeric=["peak_distance_hours"]),
            "results": hindcast_results,
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run transits workflow validation benchmarks.")
    parser.add_argument("--case-id", help="Run a single case id across matching datasets.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a readable summary.")
    parser.add_argument("--no-quiet-engine", action="store_true", help="Do not suppress backend stdout/stderr noise.")
    args = parser.parse_args(argv)

    logging.disable(logging.CRITICAL)
    results = run_workflow_benchmarks(case_id=args.case_id, quiet_engine=not args.no_quiet_engine)
    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    for name, payload in results.items():
        print(f"[{name}]")
        print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
