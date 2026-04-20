from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent / "benchmarks" / "weather"

SOURCE_ALIGNMENT_FILE = BASE_DIR / "source_alignment_cases.jsonl"
PREDICTIVE_HINDCAST_FILE = BASE_DIR / "predictive_hindcast_cases.jsonl"
PROSPECTIVE_FORECAST_FILE = BASE_DIR / "prospective_forecast_cases.jsonl"
HISTORICAL_FILES = [
    BASE_DIR / "historical_event_cases.jsonl",
    BASE_DIR / "flood_cases.jsonl",
    BASE_DIR / "hurricane_cases.jsonl",
    BASE_DIR / "thunderstorm_tornado_cases.jsonl",
    BASE_DIR / "drought_cases.jsonl",
    BASE_DIR / "snow_freezing_precipitation_cases.jsonl",
    BASE_DIR / "temperature_extremes_cases.jsonl",
    BASE_DIR / "wind_cases.jsonl",
    BASE_DIR / "generalized_seasonal_temperature_cases.jsonl",
]
PREDICTIVE_CASE_ORIGINS = {"source_backed", "novel_holdout"}


def load_jsonl_cases(path: Path) -> list[dict]:
    cases: list[dict] = []
    seen: set[str] = set()

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{line_number} invalid JSON: {exc}") from exc

            case_id = payload.get("case_id")
            if not case_id:
                raise ValueError(f"{path.name}:{line_number} missing case_id")
            if case_id in seen:
                raise ValueError(f"{path.name}:{line_number} duplicate case_id: {case_id}")

            seen.add(case_id)
            cases.append(payload)

    return cases


def _require_keys(payload: dict, keys: list[str], context: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"{context} missing required keys: {', '.join(missing)}")


def validate_source_alignment_case(case: dict, path: Path) -> None:
    context = f"{path.name}:{case['case_id']}"
    _require_keys(
        case,
        [
            "enabled",
            "case_id",
            "doctrine_area",
            "label",
            "source",
            "input_context",
            "expected_conclusions",
        ],
        context,
    )

    if not isinstance(case["source"], dict):
        raise ValueError(f"{context} source must be an object")
    _require_keys(case["source"], ["title", "raw_file", "normalized_file", "claim"], context)

    if not isinstance(case["input_context"], dict):
        raise ValueError(f"{context} input_context must be an object")
    if not isinstance(case["expected_conclusions"], list) or not case["expected_conclusions"]:
        raise ValueError(f"{context} expected_conclusions must be a non-empty list")


def _validate_event_shape(event: dict, context: str) -> None:
    if not isinstance(event, dict):
        raise ValueError(f"{context} event must be an object")
    if "type" not in event:
        raise ValueError(f"{context} event.type is required")

    has_exact = "date" in event
    has_window = "start_date" in event and "end_date" in event
    if not has_exact and not has_window:
        raise ValueError(f"{context} event requires date or start_date/end_date")


def _validate_source_assertions(source_assertions: list[dict], context: str) -> None:
    if not isinstance(source_assertions, list) or not source_assertions:
        raise ValueError(f"{context} source_assertions must be a non-empty list")

    for index, assertion in enumerate(source_assertions, start=1):
        if not isinstance(assertion, dict):
            raise ValueError(f"{context} source_assertions[{index}] must be an object")
        _require_keys(
            assertion,
            ["title", "raw_file", "normalized_file", "claim"],
            f"{context} source_assertions[{index}]",
        )


def _validate_datetime_windows(windows: list[dict], context: str) -> None:
    if not isinstance(windows, list) or not windows:
        raise ValueError(f"{context} must be a non-empty list")
    for index, window in enumerate(windows, start=1):
        if not isinstance(window, dict):
            raise ValueError(f"{context}[{index}] must be an object")
        _require_keys(window, ["start_datetime", "end_datetime"], f"{context}[{index}]")


def validate_historical_case(case: dict, path: Path) -> None:
    context = f"{path.name}:{case['case_id']}"
    _require_keys(
        case,
        [
            "enabled",
            "case_id",
            "weather_family_id",
            "label",
            "benchmark_type",
            "chart_basis",
            "event",
            "expected_weather_lead",
            "expected_interpretations",
            "source_assertions",
        ],
        context,
    )

    if not isinstance(case["chart_basis"], list) or not case["chart_basis"]:
        raise ValueError(f"{context} chart_basis must be a non-empty list")
    _validate_event_shape(case["event"], context)

    if (
        not isinstance(case["expected_interpretations"], list)
        or not case["expected_interpretations"]
    ):
        raise ValueError(f"{context} expected_interpretations must be a non-empty list")

    _validate_source_assertions(case["source_assertions"], context)


def validate_predictive_hindcast_case(case: dict, path: Path) -> None:
    context = f"{path.name}:{case['case_id']}"
    _require_keys(
        case,
        [
            "enabled",
            "case_id",
            "runtime_family_id",
            "benchmark_family_id",
            "label",
            "scan_scope",
            "location",
            "timezone",
            "benchmark_window",
            "target_window",
            "control_windows",
            "time_step_hours",
            "scoring_expectations",
            "source_assertions",
        ],
        context,
    )

    case_origin = str(case.get("case_origin") or "source_backed").strip().lower()
    if case_origin not in PREDICTIVE_CASE_ORIGINS:
        raise ValueError(
            f"{context} case_origin must be one of: {', '.join(sorted(PREDICTIVE_CASE_ORIGINS))}"
        )
    if case_origin == "source_backed" and not str(case.get("source_case_id") or "").strip():
        raise ValueError(f"{context} source_case_id is required for source_backed predictive hindcast cases")

    if case["scan_scope"] != "place_timeline":
        raise ValueError(f"{context} predictive hindcast currently supports only place_timeline")

    for window_key in ("benchmark_window", "target_window"):
        window = case.get(window_key)
        if not isinstance(window, dict):
            raise ValueError(f"{context} {window_key} must be an object")
        _require_keys(window, ["start_datetime", "end_datetime"], f"{context} {window_key}")

    _validate_datetime_windows(case.get("control_windows"), f"{context} control_windows")

    expectations = case.get("scoring_expectations")
    if not isinstance(expectations, dict):
        raise ValueError(f"{context} scoring_expectations must be an object")
    _require_keys(
        expectations,
        ["min_target_percentile", "max_target_rank", "max_peak_distance_hours"],
        f"{context} scoring_expectations",
    )

    _validate_source_assertions(case["source_assertions"], context)


def validate_weather_benchmark_datasets() -> dict:
    source_alignment_cases = load_jsonl_cases(SOURCE_ALIGNMENT_FILE)
    historical_cases: list[dict] = []
    predictive_hindcast_cases = load_jsonl_cases(PREDICTIVE_HINDCAST_FILE)
    prospective_forecast_cases = load_jsonl_cases(PROSPECTIVE_FORECAST_FILE)

    for case in source_alignment_cases:
        validate_source_alignment_case(case, SOURCE_ALIGNMENT_FILE)

    for dataset_path in HISTORICAL_FILES:
        dataset_cases = load_jsonl_cases(dataset_path)
        for case in dataset_cases:
            validate_historical_case(case, dataset_path)
        historical_cases.extend(dataset_cases)

    for case in predictive_hindcast_cases:
        validate_predictive_hindcast_case(case, PREDICTIVE_HINDCAST_FILE)

    return {
        "source_alignment_case_count": len(source_alignment_cases),
        "historical_case_count": len(historical_cases),
        "predictive_hindcast_case_count": len(predictive_hindcast_cases),
        "prospective_forecast_case_count": len(prospective_forecast_cases),
        "dataset_row_count": len(source_alignment_cases) + len(historical_cases) + len(predictive_hindcast_cases) + len(prospective_forecast_cases),
    }


def main() -> int:
    report = validate_weather_benchmark_datasets()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
