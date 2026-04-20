from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent / "benchmarks" / "mundane"

SOURCE_ALIGNMENT_FILE = BASE_DIR / "source_alignment_cases.jsonl"
NATIONAL_CHART_PROVING_FILE = BASE_DIR / "national_chart_proving_cases.jsonl"
HISTORICAL_FILES = [
    BASE_DIR / "historical_event_cases.jsonl",
    BASE_DIR / "war_conflict_cases.jsonl",
    BASE_DIR / "war_outbreak_cases.jsonl",
    BASE_DIR / "campaign_escalation_cases.jsonl",
    BASE_DIR / "military_reversal_cases.jsonl",
    BASE_DIR / "government_stability_cases.jsonl",
    BASE_DIR / "leadership_transition_cases.jsonl",
    BASE_DIR / "regime_stability_cases.jsonl",
    BASE_DIR / "alliance_stress_cases.jsonl",
    BASE_DIR / "trade_and_commerce_cases.jsonl",
    BASE_DIR / "epidemic_wave_pressure_cases.jsonl",
    BASE_DIR / "civil_unrest_cases.jsonl",
    BASE_DIR / "finance_economy_cases.jsonl",
    BASE_DIR / "diplomacy_foreign_affairs_cases.jsonl",
    BASE_DIR / "public_health_cases.jsonl",
    NATIONAL_CHART_PROVING_FILE,
    BASE_DIR / "retrograde_mars_cases.jsonl",
]
NATIONAL_CHART_CANDIDATE_FILE = BASE_DIR / "national_chart_candidates.jsonl"
SCANNER_BENCHMARK_FILE = BASE_DIR / "scanner_cases.jsonl"
SCANNER_SERIES_BENCHMARK_FILE = BASE_DIR / "scanner_series_cases.jsonl"
TRIGGER_PROFILE_BENCHMARK_FILE = BASE_DIR / "trigger_profile_cases.jsonl"
WAR_SCAN_HINDCAST_BENCHMARK_FILE = BASE_DIR / "war_scan_hindcast_cases.jsonl"


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


def validate_historical_case(case: dict, path: Path) -> None:
    context = f"{path.name}:{case['case_id']}"
    _require_keys(
        case,
        [
            "enabled",
            "case_id",
            "domain_id",
            "label",
            "benchmark_type",
            "chart_basis",
            "event",
            "expected_domain_lead",
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


def validate_national_chart_candidate_case(case: dict, path: Path) -> None:
    context = f"{path.name}:{case['case_id']}"
    _require_keys(
        case,
        [
            "enabled",
            "case_id",
            "candidate_id",
            "polity_id",
            "label",
            "benchmark_type",
            "candidate_type",
            "candidate_status",
            "confidence",
            "event",
            "expected_uses",
            "source_assertions",
        ],
        context,
    )

    _validate_event_shape(case["event"], context)
    if not isinstance(case["expected_uses"], list) or not case["expected_uses"]:
        raise ValueError(f"{context} expected_uses must be a non-empty list")

    _validate_source_assertions(case["source_assertions"], context)


def validate_scanner_case(case: dict, path: Path) -> None:
    context = f"{path.name}:{case['case_id']}"
    _require_keys(
        case,
        [
            "enabled",
            "case_id",
            "label",
            "request",
            "expectation",
            "benchmark_refs",
        ],
        context,
    )

    request = case.get("request")
    if not isinstance(request, dict):
        raise ValueError(f"{context} request must be an object")
    _require_keys(request, ["chart_type", "domain", "region_id", "scan_mode"], context)
    if request.get("scan_mode") == "spatial_scan":
        if not request.get("fixed_datetime"):
            raise ValueError(f"{context} spatial scan request requires fixed_datetime")
    elif request.get("scan_mode") == "spatiotemporal_scan":
        if not request.get("start_datetime") or not request.get("end_datetime"):
            raise ValueError(f"{context} spatiotemporal scan request requires start_datetime and end_datetime")

    expectation = case.get("expectation")
    if not isinstance(expectation, dict):
        raise ValueError(f"{context} expectation must be an object")
    minimum_results = expectation.get("minimum_results")
    if minimum_results is None:
        raise ValueError(f"{context} expectation.minimum_results is required")
    try:
        if int(minimum_results) < 1:
            raise ValueError
    except Exception as exc:
        raise ValueError(f"{context} expectation.minimum_results must be an integer >= 1") from exc

    location_tokens = expectation.get("location_tokens_any") or []
    country_codes = expectation.get("country_codes_any") or []
    if not isinstance(location_tokens, list) or not isinstance(country_codes, list):
        raise ValueError(f"{context} expectation location_tokens_any and country_codes_any must be arrays when present")
    if not location_tokens and not country_codes:
        raise ValueError(f"{context} expectation must include location_tokens_any or country_codes_any")
    if expectation.get("max_rank") is not None:
        try:
            if int(expectation.get("max_rank")) < 1:
                raise ValueError
        except Exception as exc:
            raise ValueError(f"{context} expectation.max_rank must be an integer >= 1") from exc
    for flag_name in ("require_nonzero_top_score", "require_scan_separation"):
        if flag_name in expectation and not isinstance(expectation.get(flag_name), bool):
            raise ValueError(f"{context} expectation.{flag_name} must be a boolean when present")

    benchmark_refs = case.get("benchmark_refs")
    if not isinstance(benchmark_refs, list) or not benchmark_refs:
        raise ValueError(f"{context} benchmark_refs must be a non-empty list")


def validate_scanner_series_case(case: dict, path: Path) -> None:
    context = f"{path.name}:{case['case_id']}"
    _require_keys(
        case,
        [
            "enabled",
            "case_id",
            "label",
            "request",
            "series_expectation",
            "benchmark_refs",
        ],
        context,
    )

    request = case.get("request")
    if not isinstance(request, dict):
        raise ValueError(f"{context} request must be an object")
    _require_keys(request, ["chart_type", "domain", "region_id", "scan_mode"], context)
    if request.get("scan_mode") == "spatial_scan":
        if not request.get("fixed_datetime"):
            raise ValueError(f"{context} spatial scan request requires fixed_datetime")
    elif request.get("scan_mode") == "spatiotemporal_scan":
        if not request.get("start_datetime") or not request.get("end_datetime"):
            raise ValueError(f"{context} spatiotemporal scan request requires start_datetime and end_datetime")

    expectation = case.get("series_expectation")
    if not isinstance(expectation, dict):
        raise ValueError(f"{context} series_expectation must be an object")
    place_tokens = expectation.get("expected_place_tokens_any") or []
    breakout_place_tokens = expectation.get("expected_breakout_place_tokens_any") or []
    if not isinstance(place_tokens, list) or not isinstance(breakout_place_tokens, list):
        raise ValueError(f"{context} expected_place_tokens_any and expected_breakout_place_tokens_any must be arrays when present")
    if not place_tokens and not breakout_place_tokens:
        raise ValueError(f"{context} series_expectation must include expected_place_tokens_any or expected_breakout_place_tokens_any")

    int_fields = ("expected_time_slices", "max_breakout_rank")
    for field_name in int_fields:
        if expectation.get(field_name) is None:
            continue
        try:
            if int(expectation.get(field_name)) < 1:
                raise ValueError
        except Exception as exc:
            raise ValueError(f"{context} series_expectation.{field_name} must be an integer >= 1") from exc

    numeric_fields = ("minimum_peak_scan_score", "minimum_breakout_index")
    for field_name in numeric_fields:
        if expectation.get(field_name) is None:
            continue
        try:
            float(expectation.get(field_name))
        except Exception as exc:
            raise ValueError(f"{context} series_expectation.{field_name} must be numeric") from exc

    expected_breakout_kind_any = expectation.get("expected_breakout_kind_any")
    if expected_breakout_kind_any is not None and not isinstance(expected_breakout_kind_any, list):
        raise ValueError(f"{context} series_expectation.expected_breakout_kind_any must be an array when present")

    for field_name in ("require_nonzero_series", "require_series_alignment"):
        if field_name in expectation and not isinstance(expectation.get(field_name), bool):
            raise ValueError(f"{context} series_expectation.{field_name} must be a boolean when present")

    benchmark_refs = case.get("benchmark_refs")
    if not isinstance(benchmark_refs, list) or not benchmark_refs:
        raise ValueError(f"{context} benchmark_refs must be a non-empty list")


def validate_trigger_profile_case(case: dict, path: Path, source_alignment_case_ids: set[str]) -> None:
    context = f"{path.name}:{case['case_id']}"
    _require_keys(
        case,
        [
            "enabled",
            "case_id",
            "label",
            "trigger_id",
            "context",
            "expectation",
            "benchmark_refs",
        ],
        context,
    )

    case_context = case.get("context")
    if not isinstance(case_context, dict):
        raise ValueError(f"{context} context must be an object")
    _require_keys(case_context, ["chart_type", "domain", "chart_resolution"], context)
    if not isinstance(case_context.get("chart_resolution"), dict):
        raise ValueError(f"{context} context.chart_resolution must be an object")

    expectation = case.get("expectation")
    if not isinstance(expectation, dict):
        raise ValueError(f"{context} expectation must be an object")
    if "status" in expectation and not _normalize_scalar(expectation.get("status")):
        raise ValueError(f"{context} expectation.status must be non-empty when present")
    if "minimum_score" in expectation:
        try:
            float(expectation.get("minimum_score"))
        except Exception as exc:
            raise ValueError(f"{context} expectation.minimum_score must be numeric") from exc
    if "minimum_evidence_count" in expectation:
        try:
            if int(expectation.get("minimum_evidence_count")) < 0:
                raise ValueError
        except Exception as exc:
            raise ValueError(f"{context} expectation.minimum_evidence_count must be an integer >= 0") from exc
    if "allowed_strengths" in expectation and not isinstance(expectation.get("allowed_strengths"), list):
        raise ValueError(f"{context} expectation.allowed_strengths must be an array when present")
    if "required_metric_values" in expectation and not isinstance(expectation.get("required_metric_values"), dict):
        raise ValueError(f"{context} expectation.required_metric_values must be an object when present")
    for field_name in ("active",):
        if field_name in expectation and not isinstance(expectation.get(field_name), bool):
            raise ValueError(f"{context} expectation.{field_name} must be a boolean when present")

    benchmark_refs = case.get("benchmark_refs")
    if not isinstance(benchmark_refs, list) or not benchmark_refs:
        raise ValueError(f"{context} benchmark_refs must be a non-empty list")
    for ref in benchmark_refs:
        ref_id = _normalize_scalar(ref)
        if not ref_id:
            raise ValueError(f"{context} benchmark_refs must contain non-empty strings")
        if ref_id not in source_alignment_case_ids:
            raise ValueError(f"{context} benchmark_refs includes unknown source-alignment case_id: {ref_id}")


def validate_war_scan_hindcast_case(case: dict, path: Path) -> None:
    context = f"{path.name}:{case['case_id']}"
    _require_keys(
        case,
        [
            "enabled",
            "case_id",
            "label",
            "request",
            "target_window",
            "control_windows",
            "target_place_tokens_any",
            "scoring_expectations",
            "benchmark_refs",
        ],
        context,
    )

    request = case.get("request")
    if not isinstance(request, dict):
        raise ValueError(f"{context} request must be an object")
    _require_keys(request, ["chart_type", "domain", "region_id", "scan_mode"], context)
    if request.get("scan_mode") == "spatial_scan":
        if not request.get("fixed_datetime"):
            raise ValueError(f"{context} spatial scan request requires fixed_datetime")
    else:
        if not request.get("start_datetime") or not request.get("end_datetime"):
            raise ValueError(f"{context} non-spatial scan request requires start_datetime and end_datetime")

    target_window = case.get("target_window")
    if not isinstance(target_window, dict):
        raise ValueError(f"{context} target_window must be an object")
    _require_keys(target_window, ["start_datetime", "end_datetime"], f"{context} target_window")

    control_windows = case.get("control_windows")
    if not isinstance(control_windows, list) or not control_windows:
        raise ValueError(f"{context} control_windows must be a non-empty array")
    for index, window in enumerate(control_windows, start=1):
        if not isinstance(window, dict):
            raise ValueError(f"{context} control_windows[{index}] must be an object")
        _require_keys(window, ["start_datetime", "end_datetime"], f"{context} control_windows[{index}]")

    target_place_tokens = case.get("target_place_tokens_any") or []
    target_country_codes = case.get("target_country_codes_any") or []
    if not isinstance(target_place_tokens, list) or not isinstance(target_country_codes, list):
        raise ValueError(f"{context} target_place_tokens_any and target_country_codes_any must be arrays when present")
    if not target_place_tokens and not target_country_codes:
        raise ValueError(f"{context} must include target_place_tokens_any or target_country_codes_any")

    scoring_expectations = case.get("scoring_expectations")
    if not isinstance(scoring_expectations, dict):
        raise ValueError(f"{context} scoring_expectations must be an object")
    _require_keys(
        scoring_expectations,
        ["max_target_place_rank", "min_target_percentile", "max_peak_distance_hours"],
        f"{context} scoring_expectations",
    )
    try:
        if int(scoring_expectations.get("max_target_place_rank")) < 1:
            raise ValueError
    except Exception as exc:
        raise ValueError(f"{context} scoring_expectations.max_target_place_rank must be an integer >= 1") from exc
    for field_name in ("min_target_percentile", "max_peak_distance_hours"):
        try:
            float(scoring_expectations.get(field_name))
        except Exception as exc:
            raise ValueError(f"{context} scoring_expectations.{field_name} must be numeric") from exc

    benchmark_refs = case.get("benchmark_refs")
    if not isinstance(benchmark_refs, list) or not benchmark_refs:
        raise ValueError(f"{context} benchmark_refs must be a non-empty list")


def _normalize_scalar(value: object) -> str:
    return str(value or "").strip()


def validate_all_datasets() -> dict[str, int]:
    if not BASE_DIR.exists():
        raise FileNotFoundError(f"Missing benchmark directory: {BASE_DIR}")

    source_alignment_cases = load_jsonl_cases(SOURCE_ALIGNMENT_FILE)
    for case in source_alignment_cases:
        validate_source_alignment_case(case, SOURCE_ALIGNMENT_FILE)

    source_alignment_case_ids = {str(case.get("case_id")) for case in source_alignment_cases}

    historical_counts: dict[str, int] = {}
    for path in HISTORICAL_FILES:
        cases = load_jsonl_cases(path)
        for case in cases:
            validate_historical_case(case, path)
        historical_counts[path.name] = len(cases)

    candidate_cases = load_jsonl_cases(NATIONAL_CHART_CANDIDATE_FILE)
    for case in candidate_cases:
        validate_national_chart_candidate_case(case, NATIONAL_CHART_CANDIDATE_FILE)

    scanner_cases = load_jsonl_cases(SCANNER_BENCHMARK_FILE)
    for case in scanner_cases:
        validate_scanner_case(case, SCANNER_BENCHMARK_FILE)

    scanner_series_cases = load_jsonl_cases(SCANNER_SERIES_BENCHMARK_FILE)
    for case in scanner_series_cases:
        validate_scanner_series_case(case, SCANNER_SERIES_BENCHMARK_FILE)

    trigger_profile_cases = load_jsonl_cases(TRIGGER_PROFILE_BENCHMARK_FILE)
    for case in trigger_profile_cases:
        validate_trigger_profile_case(case, TRIGGER_PROFILE_BENCHMARK_FILE, source_alignment_case_ids)

    war_scan_hindcast_cases = load_jsonl_cases(WAR_SCAN_HINDCAST_BENCHMARK_FILE)
    for case in war_scan_hindcast_cases:
        validate_war_scan_hindcast_case(case, WAR_SCAN_HINDCAST_BENCHMARK_FILE)

    return {
        SOURCE_ALIGNMENT_FILE.name: len(source_alignment_cases),
        **historical_counts,
        NATIONAL_CHART_CANDIDATE_FILE.name: len(candidate_cases),
        SCANNER_BENCHMARK_FILE.name: len(scanner_cases),
        SCANNER_SERIES_BENCHMARK_FILE.name: len(scanner_series_cases),
        TRIGGER_PROFILE_BENCHMARK_FILE.name: len(trigger_profile_cases),
        WAR_SCAN_HINDCAST_BENCHMARK_FILE.name: len(war_scan_hindcast_cases),
    }


def main() -> None:
    counts = validate_all_datasets()

    print("Validated mundane benchmark datasets")
    print(f"- {SOURCE_ALIGNMENT_FILE.name}: {counts[SOURCE_ALIGNMENT_FILE.name]} cases")
    for filename, count in counts.items():
        if filename == SOURCE_ALIGNMENT_FILE.name:
            continue
        print(f"- {filename}: {count} cases")


if __name__ == "__main__":
    main()
