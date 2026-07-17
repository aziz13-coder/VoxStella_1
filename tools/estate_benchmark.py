from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

import election_models.estate as estate_model  # noqa: E402


MODEL_VERSION = "estate-election-v1"
BACKTEST_TEMPLATE_PATH = REPO_ROOT / "tests" / "fixtures" / "estate_backtest_dataset_template.csv"
BACKTEST_SAMPLE_PATH = REPO_ROOT / "tests" / "fixtures" / "estate_backtest_sample.csv"
PROSPECTIVE_TEMPLATE_PATH = REPO_ROOT / "tests" / "fixtures" / "estate_prospective_freeze_template.csv"
PROSPECTIVE_SAMPLE_PATH = REPO_ROOT / "tests" / "fixtures" / "estate_prospective_freeze_sample.csv"

BACKTEST_COLUMNS = [
    "case_id",
    "direction",
    "location",
    "timezone",
    "house_system",
    "latitude",
    "longitude",
    "scan_start",
    "scan_end",
    "step_minutes",
    "participant_snap_id",
    "participant_label",
    "participant_chart_path",
    "participant_chart_json",
    "listing_datetime",
    "offer_submitted_datetime",
    "offer_accepted_datetime",
    "contract_signed_datetime",
    "closing_datetime",
    "chosen_event_datetime",
    "deal_completed",
    "asking_price",
    "final_price",
    "price_delta_percent",
    "time_to_close_days",
    "inspection_issue",
    "appraisal_issue",
    "legal_issue",
    "chosen_score",
    "chosen_rank",
    "random_window_score",
    "random_window_rank",
    "moon_phase_baseline_score",
    "moon_phase_baseline_rank",
    "latitude_sign_baseline_score",
    "latitude_sign_baseline_rank",
    "event_line_baseline_score",
    "event_line_baseline_rank",
    "top_windows_json",
    "benchmark_status",
    "notes",
]

PROSPECTIVE_COLUMNS = [
    "case_id",
    "model_version",
    "freeze_datetime",
    "direction",
    "location",
    "timezone",
    "house_system",
    "latitude",
    "longitude",
    "scan_start",
    "scan_end",
    "step_minutes",
    "participant_snap_id",
    "participant_label",
    "participant_chart_path",
    "participant_chart_json",
    "top_windows_json",
    "selected_event_datetime",
    "selected_score",
    "selected_rank",
    "random_window_score",
    "random_window_rank",
    "moon_phase_baseline_score",
    "moon_phase_baseline_rank",
    "latitude_sign_baseline_score",
    "latitude_sign_baseline_rank",
    "event_line_baseline_score",
    "event_line_baseline_rank",
    "outcome_review_date",
    "deal_completed",
    "final_price",
    "time_to_close_days",
    "inspection_issue",
    "appraisal_issue",
    "legal_issue",
    "outcome_status",
    "notes",
]


def _parse_csv_list(raw: str, *, cast=str) -> List[Any]:
    values = []
    for item in str(raw or "").split(","):
        text = item.strip()
        if not text:
            continue
        values.append(cast(text))
    return values


def _houses(start: float) -> List[float]:
    return [((start + i * 30.0) % 360.0) for i in range(12)]


def _house_system_offset(name: str) -> float:
    key = str(name or "").strip().lower()
    offsets = {
        "placidus": 0.0,
        "whole-sign": 7.5,
        "whole_sign": 7.5,
        "whole sign": 7.5,
        "regiomontanus": 15.0,
        "porphyry": 22.5,
    }
    return offsets.get(key, float(sum(ord(ch) for ch in key) % 24))


def _planet(lon: float, speed: float = 1.0) -> Dict[str, float]:
    return {"longitude": round(lon % 360.0, 6), "speed": float(speed)}


def _synthetic_chart(dt: datetime, *, latitude: float, house_system: str) -> Dict[str, Any]:
    minutes = int(dt.timestamp() // 60)
    days = minutes / 1440.0
    offset = _house_system_offset(house_system)
    asc = (minutes * 0.25 + latitude * 0.4 + offset) % 360.0
    sun = (280.0 + days * 0.985647) % 360.0
    moon = (125.0 + days * 13.176358 + latitude * 0.15) % 360.0
    planets = {
        "Sun": _planet(sun, 0.985647),
        "Moon": _planet(moon, 13.176358),
        "Mercury": _planet(sun + 24.0 + (days % 40.0) * 1.2, 1.2),
        "Venus": _planet(sun + 62.0 + (days % 70.0) * 0.6, 0.6),
        "Mars": _planet(sun + 138.0 + (days % 120.0) * 0.35, 0.35),
        "Jupiter": _planet(sun + 214.0 + (days % 360.0) * 0.08, 0.08),
        "Saturn": _planet(sun + 286.0 + (days % 360.0) * 0.03, 0.03),
    }
    fortuna = {
        "longitude": round((asc + moon - sun) % 360.0, 6),
    }
    return {
        "houses": _houses(asc),
        "planets": planets,
        "arabic_parts": {"fortune": fortuna},
        "moon_day": {"nid": 7, "interval_tags": []},
    }


def _synthetic_participant() -> Dict[str, Any]:
    return {
        "label": "Synthetic Buyer",
        "precision_class": "certified",
        "precision_safe": True,
        "chart_data": {
            "houses": _houses(18.0),
            "planets": {
                "Sun": _planet(42.0),
                "Moon": _planet(118.0),
                "Mercury": _planet(64.0),
                "Venus": _planet(96.0),
                "Mars": _planet(146.0),
                "Jupiter": _planet(232.0),
                "Saturn": _planet(304.0),
            },
            "moon_day": {"nid": 8, "interval_tags": []},
        },
    }


def _scan_rows(*, days: int, step_minutes: int, latitude: float, house_system: str) -> List[Dict[str, Any]]:
    start = datetime(2026, 4, 18, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=days)
    step = timedelta(minutes=step_minutes)
    rows: List[Dict[str, Any]] = []
    participant = _synthetic_participant()
    dt = start
    while dt <= end:
        chart = _synthetic_chart(dt, latitude=latitude, house_system=house_system)
        result = estate_model.score_estate_election(
            chart,
            options={
                "estate_direction": "buy",
                "event_meta": {"latitude": latitude, "house_system": house_system},
                "estate_participant": participant,
            },
        )
        rows.append(
            {
                "timestamp": dt.isoformat(),
                "score": float(result.get("value") or 0.0),
                "lines": list(result.get("lines") or []),
                "tags": list(result.get("tags") or []),
            }
        )
        dt += step
    return rows


def _top_windows(rows: Iterable[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    ranked = sorted(
        list(rows),
        key=lambda row: (-float(row.get("score") or 0.0), str(row.get("timestamp") or "")),
    )
    return [
        {
            "timestamp": str(row.get("timestamp") or ""),
            "score": round(float(row.get("score") or 0.0), 2),
        }
        for row in ranked[:limit]
    ]


def _parse_dt(raw: Any) -> Optional[datetime]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except Exception:
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def _row_float(row: Dict[str, Any], key: str, default: Optional[float] = None) -> Optional[float]:
    try:
        raw = str(row.get(key) or "").strip()
        return float(raw) if raw else default
    except Exception:
        return default


def _row_int(row: Dict[str, Any], key: str, default: int) -> int:
    try:
        raw = str(row.get(key) or "").strip()
        return int(float(raw)) if raw else default
    except Exception:
        return default


def _case_latitude(row: Dict[str, Any], default: float = 31.778) -> float:
    value = _row_float(row, "latitude", default)
    return float(value if value is not None else default)


def _case_longitude(row: Dict[str, Any]) -> Optional[float]:
    return _row_float(row, "longitude", None)


def _scan_bounds(row: Dict[str, Any], *, chosen_key: str = "chosen_event_datetime") -> Tuple[Optional[datetime], Optional[datetime], Optional[datetime], int]:
    chosen = _parse_dt(row.get(chosen_key))
    start = _parse_dt(row.get("scan_start"))
    end = _parse_dt(row.get("scan_end"))
    if chosen is not None:
        if start is None:
            start = chosen - timedelta(days=3)
        if end is None:
            end = chosen + timedelta(days=4)
    step_minutes = max(1, _row_int(row, "step_minutes", 60))
    return start, end, chosen, step_minutes


def _candidate_datetimes(start: datetime, end: datetime, step_minutes: int, include: Optional[datetime] = None) -> List[datetime]:
    step = timedelta(minutes=max(1, step_minutes))
    values: Dict[str, datetime] = {}
    dt = start
    while dt <= end:
        values[dt.isoformat()] = dt
        dt += step
    if include is not None and start <= include <= end:
        values[include.isoformat()] = include
    return [values[key] for key in sorted(values)]


def _load_json_payload(raw: Any) -> Optional[Dict[str, Any]]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _participant_from_row(row: Dict[str, Any], *, engine: str) -> Dict[str, Any]:
    label = str(row.get("participant_label") or "Estate participant").strip() or "Estate participant"
    path_raw = str(row.get("participant_chart_path") or "").strip()
    if path_raw:
        path = Path(path_raw)
        if not path.is_absolute():
            path = REPO_ROOT / path
        payload = _load_json_payload(path.read_text(encoding="utf-8"))
        if payload:
            return {
                "label": label,
                "precision_class": "certified",
                "precision_safe": True,
                "chart_data": payload.get("chart_data") if isinstance(payload.get("chart_data"), dict) else payload,
            }
    payload = _load_json_payload(row.get("participant_chart_json"))
    if payload:
        return {
            "label": label,
            "precision_class": "certified",
            "precision_safe": True,
            "chart_data": payload.get("chart_data") if isinstance(payload.get("chart_data"), dict) else payload,
        }
    snap_id = str(row.get("participant_snap_id") or "").strip()
    if snap_id and engine == "app":
        os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
        try:
            import astro_clock_api  # type: ignore

            bundle = astro_clock_api._bundle_from_snap_id(snap_id, house_system_code=str(row.get("house_system") or "").strip() or None)
            chart_data = bundle.get("chart_data") if isinstance(bundle, dict) else None
            meta = bundle.get("meta") if isinstance(bundle, dict) else {}
            if isinstance(chart_data, dict) and chart_data:
                return {
                    "label": label,
                    "precision_class": "certified",
                    "precision_safe": True,
                    "precision_source": "saved_snap",
                    "chart_data": chart_data,
                    "meta": meta if isinstance(meta, dict) else {},
                }
        except Exception:
            pass
    synthetic = _synthetic_participant()
    synthetic["label"] = label if label != "Estate participant" else synthetic["label"]
    return synthetic


def _chart_for_candidate(dt: datetime, row: Dict[str, Any], *, engine: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    latitude = _case_latitude(row)
    longitude = _case_longitude(row)
    house_system = str(row.get("house_system") or "placidus").strip() or "placidus"
    if engine == "app":
        os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
        import astro_clock_api  # type: ignore

        bundle = astro_clock_api._compute_chart_bundle_for(
            dt.isoformat(),
            str(row.get("location") or "").strip() or None,
            str(row.get("timezone") or "").strip() or None,
            house_system_code=house_system,
            latitude=latitude if row.get("latitude") else None,
            longitude=longitude,
        )
        chart_data = bundle.get("chart_data") if isinstance(bundle, dict) else {}
        meta = bundle.get("meta") if isinstance(bundle, dict) else {}
        if not isinstance(chart_data, dict):
            chart_data = {}
        if not isinstance(meta, dict):
            meta = {}
        return chart_data, meta
    chart = _synthetic_chart(dt, latitude=latitude, house_system=house_system)
    return chart, {
        "timestamp": dt.isoformat(),
        "location": str(row.get("location") or ""),
        "timezone": str(row.get("timezone") or "UTC"),
        "latitude": latitude,
        "longitude": longitude,
        "house_system": house_system,
    }


def _event_line_score(result: Dict[str, Any]) -> float:
    for line in list(result.get("lines") or []):
        if isinstance(line, dict) and str(line.get("id") or "") == "event":
            try:
                return float(line.get("score") or 0.0)
            except Exception:
                return 0.0
    return 0.0


def _moon_phase_score(chart: Dict[str, Any], *, direction: str) -> float:
    value, _tag = estate_model._moon_phase_bonus(estate_model._collect_planets(chart), direction=direction)
    return float(value or 0.0)


def _latitude_sign_score(chart: Dict[str, Any], *, direction: str, latitude: float) -> float:
    planets = estate_model._collect_planets(chart)
    cusps = estate_model._house_cusps(chart)
    moon_lon = estate_model._planet_lon(planets, "Moon")
    asc_lon = estate_model._cusp_lon(cusps, 0)
    total = 0.0
    for label, lon in (("Moon", moon_lon), ("Asc", asc_lon)):
        value, _tag = estate_model._latitude_sign_bonus(lon, latitude, direction=direction, label=label)
        total += float(value or 0.0)
    return total


def _deterministic_random_score(case_id: str, timestamp: str) -> float:
    digest = hashlib.sha256(f"{case_id}|{timestamp}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def _rank_for_metric(rows: List[Dict[str, Any]], chosen_timestamp: str, metric: str) -> Tuple[Optional[int], Optional[float]]:
    chosen = next((row for row in rows if row.get("timestamp") == chosen_timestamp), None)
    if not chosen:
        return None, None
    chosen_score = float(chosen.get(metric) or 0.0)
    rank = 1 + sum(1 for row in rows if float(row.get(metric) or 0.0) > chosen_score)
    return rank, chosen_score


def _rank_case_row(row: Dict[str, Any], *, engine: str, top_limit: int, chosen_key: str = "chosen_event_datetime") -> Tuple[Dict[str, Any], Dict[str, Any]]:
    start, end, chosen, step_minutes = _scan_bounds(row, chosen_key=chosen_key)
    out = dict(row)
    if start is None or end is None or chosen is None:
        out["benchmark_status"] = "missing scan_start/scan_end/chosen_event_datetime"
        return out, {"status": out["benchmark_status"], "candidate_count": 0}
    if end < start:
        out["benchmark_status"] = "scan_end before scan_start"
        return out, {"status": out["benchmark_status"], "candidate_count": 0}

    direction = "sell" if str(row.get("direction") or "").strip().lower() == "sell" else "buy"
    participant = _participant_from_row(row, engine=engine)
    latitude = _case_latitude(row)
    case_id = str(row.get("case_id") or "estate-case").strip() or "estate-case"
    candidates: List[Dict[str, Any]] = []
    for dt in _candidate_datetimes(start, end, step_minutes, include=chosen):
        chart, meta = _chart_for_candidate(dt, row, engine=engine)
        event_latitude = _row_float(meta, "latitude", latitude) if isinstance(meta, dict) else latitude
        options = {
            "estate_direction": direction,
            "event_meta": {
                "latitude": event_latitude,
                "longitude": _row_float(meta, "longitude", _case_longitude(row)) if isinstance(meta, dict) else _case_longitude(row),
                "house_system": str(row.get("house_system") or ""),
            },
            "estate_participant": participant,
        }
        result = estate_model.score_estate_election(chart, options=options)
        timestamp = dt.isoformat()
        candidates.append(
            {
                "timestamp": timestamp,
                "score": float(result.get("value") or 0.0),
                "event_line_score": _event_line_score(result),
                "moon_phase_baseline_score": _moon_phase_score(chart, direction=direction),
                "latitude_sign_baseline_score": _latitude_sign_score(chart, direction=direction, latitude=float(event_latitude or 0.0)),
                "random_window_score": _deterministic_random_score(case_id, timestamp),
                "line_count": len(list(result.get("lines") or [])),
            }
        )

    chosen_timestamp = chosen.isoformat()
    metric_map = {
        "chosen": "score",
        "random_window": "random_window_score",
        "moon_phase_baseline": "moon_phase_baseline_score",
        "latitude_sign_baseline": "latitude_sign_baseline_score",
        "event_line_baseline": "event_line_score",
    }
    for prefix, metric in metric_map.items():
        rank, score = _rank_for_metric(candidates, chosen_timestamp, metric)
        score_key = "chosen_score" if prefix == "chosen" else f"{prefix}_score"
        rank_key = "chosen_rank" if prefix == "chosen" else f"{prefix}_rank"
        out[score_key] = _format_number(score)
        out[rank_key] = str(rank or "")
    top_windows = sorted(
        candidates,
        key=lambda item: (-float(item.get("score") or 0.0), str(item.get("timestamp") or "")),
    )[:top_limit]
    out["top_windows_json"] = json.dumps(
        [
            {
                "timestamp": item["timestamp"],
                "score": round(float(item.get("score") or 0.0), 2),
                "event_line_score": round(float(item.get("event_line_score") or 0.0), 2),
            }
            for item in top_windows
        ],
        separators=(",", ":"),
    )
    out["benchmark_status"] = "ranked"
    return out, {
        "status": "ranked",
        "candidate_count": len(candidates),
        "chosen_rank": out.get("chosen_rank"),
        "top_score": top_windows[0]["score"] if top_windows else None,
    }


def run_scan_stability(args: argparse.Namespace) -> Dict[str, Any]:
    latitudes = _parse_csv_list(args.latitudes, cast=float) or [-45.0, 0.0, 31.778, 45.0]
    house_systems = _parse_csv_list(args.house_systems) or ["placidus", "whole-sign", "regiomontanus"]
    scenarios = []
    for latitude in latitudes:
        for house_system in house_systems:
            started = time.perf_counter()
            crash = None
            try:
                rows = _scan_rows(
                    days=args.days,
                    step_minutes=args.step_minutes,
                    latitude=latitude,
                    house_system=house_system,
                )
                repeat_rows = _scan_rows(
                    days=args.days,
                    step_minutes=args.step_minutes,
                    latitude=latitude,
                    house_system=house_system,
                )
            except Exception as exc:  # pragma: no cover - defensive CLI path
                rows = []
                repeat_rows = []
                crash = f"{type(exc).__name__}: {exc}"
            elapsed = time.perf_counter() - started
            scores = [float(row.get("score") or 0.0) for row in rows]
            top_windows = _top_windows(rows)
            repeat_top_windows = _top_windows(repeat_rows)
            row_count = len(rows)
            timed_row_count = row_count + len(repeat_rows)
            runtime_per_1000 = (elapsed / timed_row_count * 1000.0) if timed_row_count else None
            empty_line_rows = sum(1 for row in rows if not row.get("lines"))
            score_spread = (max(scores) - min(scores)) if scores else None
            scenarios.append(
                {
                    "latitude": latitude,
                    "house_system": house_system,
                    "no_crashes": crash is None,
                    "crash": crash,
                    "row_count": row_count,
                    "deterministic_top_windows": top_windows == repeat_top_windows,
                    "top_windows": top_windows,
                    "score_min": round(min(scores), 2) if scores else None,
                    "score_max": round(max(scores), 2) if scores else None,
                    "score_spread": round(score_spread, 2) if score_spread is not None else None,
                    "reasonable_score_spread": bool(score_spread is not None and score_spread >= 1.0),
                    "score_mean": round(statistics.fmean(scores), 2) if scores else None,
                    "runtime_per_1000_timestamps_seconds": round(runtime_per_1000, 4) if runtime_per_1000 is not None else None,
                    "empty_line_rows": empty_line_rows,
                    "no_empty_lines": empty_line_rows == 0 and row_count > 0,
                }
            )
    return {
        "model_version": MODEL_VERSION,
        "days": args.days,
        "step_minutes": args.step_minutes,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }


def _read_csv(path: Path, required_columns: List[str]) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    missing = [column for column in required_columns if column not in fieldnames]
    return {
        "path": str(path),
        "fieldnames": fieldnames,
        "missing_columns": missing,
        "rows": rows,
    }


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _merged_fieldnames(existing: Iterable[str], required: List[str]) -> List[str]:
    fieldnames: List[str] = []
    for name in list(required) + list(existing or []):
        key = str(name or "").strip()
        if key and key not in fieldnames:
            fieldnames.append(key)
    return fieldnames


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "completed", "pass"}


def _is_number(value: Any) -> bool:
    try:
        float(str(value).strip())
        return True
    except Exception:
        return False


def validate_backtest(args: argparse.Namespace) -> Dict[str, Any]:
    payload = _read_csv(Path(args.dataset), BACKTEST_COLUMNS)
    rows = payload["rows"]
    rank_columns = [
        "chosen_rank",
        "random_window_rank",
        "moon_phase_baseline_rank",
        "latitude_sign_baseline_rank",
        "event_line_baseline_rank",
    ]
    completed = sum(1 for row in rows if _truthy(row.get("deal_completed")))
    failed = sum(1 for row in rows if str(row.get("deal_completed") or "").strip() and not _truthy(row.get("deal_completed")))
    comparison_rows = [
        row
        for row in rows
        if row.get("chosen_event_datetime")
        and all(_is_number(row.get(column)) for column in rank_columns)
    ]
    baseline_columns = [column for column in rank_columns if column != "chosen_rank"]
    comparisons = {}
    for column in baseline_columns:
        total = len(comparison_rows)
        chosen_better_or_tied = sum(
            1
            for row in comparison_rows
            if float(row.get("chosen_rank") or 0.0) <= float(row.get(column) or 0.0)
        )
        baseline_values = [float(row.get(column) or 0.0) for row in comparison_rows]
        comparisons[column] = {
            "cases": total,
            "baseline_mean_rank": round(statistics.fmean(baseline_values), 3) if baseline_values else None,
            "chosen_better_or_tied_cases": chosen_better_or_tied,
            "chosen_better_or_tied_rate": round(chosen_better_or_tied / total, 3) if total else None,
        }
    chosen_ranks = [float(row.get("chosen_rank") or 0.0) for row in comparison_rows]
    price_deltas = [float(row.get("price_delta_percent") or 0.0) for row in rows if _is_number(row.get("price_delta_percent"))]
    return {
        "dataset": payload["path"],
        "row_count": len(rows),
        "missing_columns": payload["missing_columns"],
        "completed_cases": completed,
        "failed_cases": failed,
        "comparison_ready_cases": len(comparison_rows),
        "chosen_mean_rank": round(statistics.fmean(chosen_ranks), 3) if chosen_ranks else None,
        "price_delta_mean_percent": round(statistics.fmean(price_deltas), 3) if price_deltas else None,
        "comparisons": comparisons,
        "rank_columns": rank_columns,
    }


def rank_backtest(args: argparse.Namespace) -> Dict[str, Any]:
    dataset_path = Path(args.dataset)
    payload = _read_csv(dataset_path, BACKTEST_COLUMNS)
    if not args.in_place and not args.output:
        raise ValueError("--output is required unless --in-place is used")
    output_path = dataset_path if args.in_place else Path(args.output)
    ranked_rows = []
    case_summaries = []
    for row in payload["rows"]:
        ranked, summary = _rank_case_row(
            row,
            engine=args.engine,
            top_limit=args.top_limit,
            chosen_key="chosen_event_datetime",
        )
        ranked_rows.append(ranked)
        case_summaries.append({"case_id": ranked.get("case_id"), **summary})
    fieldnames = _merged_fieldnames(payload["fieldnames"], BACKTEST_COLUMNS)
    _write_csv(output_path, ranked_rows, fieldnames)
    comparison_ready = sum(1 for row in ranked_rows if row.get("benchmark_status") == "ranked")
    return {
        "dataset": str(dataset_path),
        "output": str(output_path),
        "engine": args.engine,
        "row_count": len(ranked_rows),
        "missing_columns": payload["missing_columns"],
        "ranked_cases": comparison_ready,
        "case_summaries": case_summaries,
    }


def validate_prospective_freeze(args: argparse.Namespace) -> Dict[str, Any]:
    payload = _read_csv(Path(args.log), PROSPECTIVE_COLUMNS)
    rows = payload["rows"]
    invalid_top_windows = []
    frozen_versions = set()
    for index, row in enumerate(rows, start=2):
        version = str(row.get("model_version") or "").strip()
        if version:
            frozen_versions.add(version)
        raw_windows = str(row.get("top_windows_json") or "").strip()
        if not raw_windows:
            continue
        try:
            parsed = json.loads(raw_windows)
        except Exception:
            invalid_top_windows.append(index)
            continue
        if not isinstance(parsed, list):
            invalid_top_windows.append(index)
    return {
        "log": payload["path"],
        "row_count": len(rows),
        "missing_columns": payload["missing_columns"],
        "frozen_model_versions": sorted(frozen_versions),
        "invalid_top_windows_json_rows": invalid_top_windows,
        "ready_for_review_cases": sum(1 for row in rows if str(row.get("outcome_review_date") or "").strip()),
    }


def freeze_case(args: argparse.Namespace) -> Dict[str, Any]:
    log_path = Path(args.log)
    if log_path.exists():
        payload = _read_csv(log_path, PROSPECTIVE_COLUMNS)
        rows = payload["rows"]
        fieldnames = _merged_fieldnames(payload["fieldnames"], PROSPECTIVE_COLUMNS)
    else:
        rows = []
        fieldnames = list(PROSPECTIVE_COLUMNS)

    freeze_row = {
        "case_id": args.case_id,
        "model_version": args.model_version or MODEL_VERSION,
        "freeze_datetime": datetime.now(timezone.utc).isoformat(),
        "direction": args.direction,
        "location": args.location,
        "timezone": args.timezone,
        "house_system": args.house_system,
        "latitude": "" if args.latitude is None else _format_number(args.latitude),
        "longitude": "" if args.longitude is None else _format_number(args.longitude),
        "scan_start": args.scan_start,
        "scan_end": args.scan_end,
        "step_minutes": str(args.step_minutes),
        "participant_snap_id": args.participant_snap_id or "",
        "participant_label": args.participant_label or "",
        "participant_chart_path": args.participant_chart_path or "",
        "participant_chart_json": args.participant_chart_json or "",
        "selected_event_datetime": args.selected_event,
        "notes": args.notes or "",
    }
    ranking_input = {
        **freeze_row,
        "chosen_event_datetime": args.selected_event,
    }
    ranked, summary = _rank_case_row(
        ranking_input,
        engine=args.engine,
        top_limit=args.top_limit,
        chosen_key="chosen_event_datetime",
    )
    for source, target in (
        ("chosen_score", "selected_score"),
        ("chosen_rank", "selected_rank"),
        ("random_window_score", "random_window_score"),
        ("random_window_rank", "random_window_rank"),
        ("moon_phase_baseline_score", "moon_phase_baseline_score"),
        ("moon_phase_baseline_rank", "moon_phase_baseline_rank"),
        ("latitude_sign_baseline_score", "latitude_sign_baseline_score"),
        ("latitude_sign_baseline_rank", "latitude_sign_baseline_rank"),
        ("event_line_baseline_score", "event_line_baseline_score"),
        ("event_line_baseline_rank", "event_line_baseline_rank"),
        ("top_windows_json", "top_windows_json"),
    ):
        freeze_row[target] = ranked.get(source, "")

    if args.replace:
        rows = [row for row in rows if str(row.get("case_id") or "") != str(args.case_id)]
    rows.append(freeze_row)
    _write_csv(log_path, rows, fieldnames)
    return {
        "log": str(log_path),
        "engine": args.engine,
        "case_id": args.case_id,
        "model_version": freeze_row["model_version"],
        "selected_rank": freeze_row.get("selected_rank"),
        "candidate_count": summary.get("candidate_count"),
        "row_count": len(rows),
        "missing_columns": [],
    }


def run_benchmark_suite(args: argparse.Namespace) -> Dict[str, Any]:
    scan = run_scan_stability(
        argparse.Namespace(
            days=args.days,
            step_minutes=args.step_minutes,
            latitudes=args.latitudes,
            house_systems=args.house_systems,
        )
    )
    backtest_template = validate_backtest(argparse.Namespace(dataset=str(BACKTEST_TEMPLATE_PATH)))
    prospective_template = validate_prospective_freeze(argparse.Namespace(log=str(PROSPECTIVE_TEMPLATE_PATH)))
    backtest_sample = validate_backtest(argparse.Namespace(dataset=str(BACKTEST_SAMPLE_PATH)))
    prospective_sample = validate_prospective_freeze(argparse.Namespace(log=str(PROSPECTIVE_SAMPLE_PATH)))

    with tempfile.TemporaryDirectory(prefix="estate-benchmark-") as tmp_dir:
        reranked_path = Path(tmp_dir) / "estate_backtest_sample_reranked.csv"
        sample_rerank = rank_backtest(
            argparse.Namespace(
                dataset=str(BACKTEST_SAMPLE_PATH),
                output=str(reranked_path),
                in_place=False,
                engine=args.engine,
                top_limit=args.top_limit,
            )
        )
        sample_rerank_validation = validate_backtest(argparse.Namespace(dataset=str(reranked_path)))

    scan_ok = (
        scan.get("scenario_count") > 0
        and all(
            row.get("no_crashes")
            and row.get("deterministic_top_windows")
            and row.get("no_empty_lines")
            and row.get("reasonable_score_spread")
            for row in list(scan.get("scenarios") or [])
        )
    )
    validations = {
        "backtest_template": backtest_template,
        "prospective_template": prospective_template,
        "backtest_sample": backtest_sample,
        "prospective_sample": prospective_sample,
        "sample_rerank": sample_rerank,
        "sample_rerank_validation": sample_rerank_validation,
    }
    validations_ok = all(not payload.get("missing_columns") for payload in validations.values())
    validations_ok = validations_ok and not prospective_sample.get("invalid_top_windows_json_rows")
    validations_ok = validations_ok and sample_rerank.get("ranked_cases", 0) >= 1
    validations_ok = validations_ok and sample_rerank_validation.get("comparison_ready_cases", 0) >= 1

    scenarios = list(scan.get("scenarios") or [])
    runtime_values = [
        float(row.get("runtime_per_1000_timestamps_seconds") or 0.0)
        for row in scenarios
        if row.get("runtime_per_1000_timestamps_seconds") is not None
    ]
    spread_values = [
        float(row.get("score_spread") or 0.0)
        for row in scenarios
        if row.get("score_spread") is not None
    ]
    sample_summary = {
        "backtest_comparison_ready_cases": backtest_sample.get("comparison_ready_cases"),
        "backtest_chosen_mean_rank": backtest_sample.get("chosen_mean_rank"),
        "prospective_frozen_versions": prospective_sample.get("frozen_model_versions"),
        "sample_rerank_ranked_cases": sample_rerank.get("ranked_cases"),
    }
    return {
        "model_version": MODEL_VERSION,
        "ok": bool(scan_ok and validations_ok),
        "engine": args.engine,
        "scan_summary": {
            "scenario_count": scan.get("scenario_count"),
            "total_rows": sum(int(row.get("row_count") or 0) for row in scenarios),
            "all_no_crashes": all(row.get("no_crashes") for row in scenarios),
            "all_deterministic_top_windows": all(row.get("deterministic_top_windows") for row in scenarios),
            "all_no_empty_lines": all(row.get("no_empty_lines") for row in scenarios),
            "all_reasonable_score_spread": all(row.get("reasonable_score_spread") for row in scenarios),
            "runtime_per_1000_min": round(min(runtime_values), 4) if runtime_values else None,
            "runtime_per_1000_max": round(max(runtime_values), 4) if runtime_values else None,
            "score_spread_min": round(min(spread_values), 2) if spread_values else None,
            "score_spread_max": round(max(spread_values), 2) if spread_values else None,
        },
        "sample_summary": sample_summary,
        "validations": validations,
    }


def _emit(payload: Dict[str, Any], output: str | None) -> int:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    print(text)
    if payload.get("missing_columns"):
        return 2
    if payload.get("ok") is False:
        return 2
    if payload.get("invalid_top_windows_json_rows"):
        return 2
    scenarios = payload.get("scenarios")
    if isinstance(scenarios, list):
        if any(
            not row.get("no_crashes")
            or not row.get("deterministic_top_windows")
            or not row.get("no_empty_lines")
            or not row.get("reasonable_score_spread")
            for row in scenarios
        ):
            return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Estate election benchmark utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan-stability", help="Run deterministic synthetic scan stability checks")
    scan.add_argument("--days", type=int, default=7)
    scan.add_argument("--step-minutes", type=int, default=60)
    scan.add_argument("--latitudes", default="-45,0,31.778,45")
    scan.add_argument("--house-systems", default="placidus,whole-sign,regiomontanus")
    scan.add_argument("--output")
    scan.set_defaults(func=run_scan_stability)

    backtest = subparsers.add_parser("backtest", help="Validate an estate backtest dataset CSV")
    backtest.add_argument("--dataset", required=True)
    backtest.add_argument("--output")
    backtest.set_defaults(func=validate_backtest)

    rank = subparsers.add_parser("backtest-rank", help="Compute estate model and baseline ranks for a backtest CSV")
    rank.add_argument("--dataset", required=True)
    rank.add_argument("--output")
    rank.add_argument("--in-place", action="store_true")
    rank.add_argument("--engine", choices=["synthetic", "app"], default="synthetic")
    rank.add_argument("--top-limit", type=int, default=5)
    rank.set_defaults(func=rank_backtest)

    prospective = subparsers.add_parser("prospective-freeze", help="Validate a prospective freeze-test CSV")
    prospective.add_argument("--log", required=True)
    prospective.add_argument("--output")
    prospective.set_defaults(func=validate_prospective_freeze)

    freeze = subparsers.add_parser("freeze-case", help="Append a scored prospective freeze-test row")
    freeze.add_argument("--log", required=True)
    freeze.add_argument("--case-id", required=True)
    freeze.add_argument("--direction", choices=["buy", "sell"], required=True)
    freeze.add_argument("--location", required=True)
    freeze.add_argument("--timezone", default="UTC")
    freeze.add_argument("--house-system", default="placidus")
    freeze.add_argument("--latitude", type=float)
    freeze.add_argument("--longitude", type=float)
    freeze.add_argument("--scan-start", required=True)
    freeze.add_argument("--scan-end", required=True)
    freeze.add_argument("--step-minutes", type=int, default=60)
    freeze.add_argument("--selected-event", required=True)
    freeze.add_argument("--participant-snap-id")
    freeze.add_argument("--participant-label")
    freeze.add_argument("--participant-chart-path")
    freeze.add_argument("--participant-chart-json")
    freeze.add_argument("--model-version")
    freeze.add_argument("--engine", choices=["synthetic", "app"], default="synthetic")
    freeze.add_argument("--top-limit", type=int, default=5)
    freeze.add_argument("--replace", action="store_true")
    freeze.add_argument("--notes")
    freeze.add_argument("--output")
    freeze.set_defaults(func=freeze_case)

    suite = subparsers.add_parser("benchmark-suite", help="Run all estate benchmark checks and sample validations")
    suite.add_argument("--days", type=int, default=7)
    suite.add_argument("--step-minutes", type=int, default=60)
    suite.add_argument("--latitudes", default="-45,0,31.778,45")
    suite.add_argument("--house-systems", default="placidus,whole-sign,regiomontanus")
    suite.add_argument("--engine", choices=["synthetic", "app"], default="synthetic")
    suite.add_argument("--top-limit", type=int, default=5)
    suite.add_argument("--output")
    suite.set_defaults(func=run_benchmark_suite)
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = args.func(args)
    return _emit(payload, getattr(args, "output", None))


if __name__ == "__main__":
    raise SystemExit(main())
