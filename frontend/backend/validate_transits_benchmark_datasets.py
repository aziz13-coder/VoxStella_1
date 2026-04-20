from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


BENCHMARK_DIR = Path(__file__).resolve().parent / "benchmarks" / "transits"
EXACT_SCAN_FILE = BENCHMARK_DIR / "exact_scan_consistency_cases.jsonl"
PREDICTOR_STABILITY_FILE = BENCHMARK_DIR / "predictor_stability_cases.jsonl"
DOCUMENTED_HINDCAST_FILE = BENCHMARK_DIR / "documented_hindcast_cases.jsonl"

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_jsonl_cases(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno} invalid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{lineno} row must be a JSON object")
            yield payload


def _require_string(payload: Dict[str, Any], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: '{key}' must be a non-empty string")
    return value.strip()


def _require_int(payload: Dict[str, Any], key: str, path: Path) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{path}: '{key}' must be an integer")
    return value


def _require_bool(payload: Dict[str, Any], key: str, path: Path) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{path}: '{key}' must be a boolean")
    return value


def _require_citations(payload: Dict[str, Any], path: Path) -> List[str]:
    citations = payload.get("citations")
    if not isinstance(citations, list) or not citations:
        raise ValueError(f"{path}: 'citations' must be a non-empty array")
    cleaned: List[str] = []
    for item in citations:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{path}: each citation must be a non-empty string")
        citation = item.strip()
        citation_path = (REPO_ROOT / citation).resolve()
        if not citation_path.exists():
            raise ValueError(f"{path}: citation path does not exist: {citation}")
        cleaned.append(citation)
    return cleaned


def _validate_natal_fields(payload: Dict[str, Any], path: Path) -> None:
    _require_string(payload, "natal_datetime", path)
    _require_string(payload, "natal_location", path)
    _require_string(payload, "natal_timezone", path)
    _require_string(payload, "house_system_code", path)


def validate_exact_scan_consistency_case(payload: Dict[str, Any], path: Path) -> Dict[str, Any]:
    _require_string(payload, "case_id", path)
    _require_bool(payload, "enabled", path)
    _validate_natal_fields(payload, path)
    _require_string(payload, "transit_datetime", path)
    _require_string(payload, "window_start", path)
    _require_string(payload, "window_end", path)
    _require_int(payload, "step_minutes", path)
    _require_int(payload, "expected_transit_overlap_min", path)
    _require_int(payload, "expected_prediction_overlap_min", path)
    _require_citations(payload, path)
    return payload


def validate_predictor_stability_case(payload: Dict[str, Any], path: Path) -> Dict[str, Any]:
    _require_string(payload, "case_id", path)
    _require_bool(payload, "enabled", path)
    _validate_natal_fields(payload, path)
    _require_string(payload, "window_start", path)
    _require_string(payload, "window_end", path)
    _require_int(payload, "step_minutes_primary", path)
    _require_int(payload, "step_minutes_secondary", path)
    _require_string(payload, "expected_life_area", path)
    _require_string(payload, "expected_event_type", path)
    _require_int(payload, "max_rank", path)
    _require_int(payload, "max_dominant_gap_hours", path)
    _require_citations(payload, path)
    return payload


def validate_documented_hindcast_case(payload: Dict[str, Any], path: Path) -> Dict[str, Any]:
    _require_string(payload, "case_id", path)
    _require_bool(payload, "enabled", path)
    _validate_natal_fields(payload, path)
    _require_string(payload, "window_start", path)
    _require_string(payload, "window_end", path)
    _require_int(payload, "step_minutes", path)
    target_window = payload.get("target_window")
    if not isinstance(target_window, dict):
        raise ValueError(f"{path}: 'target_window' must be an object")
    if not isinstance(target_window.get("start"), str) or not isinstance(target_window.get("end"), str):
        raise ValueError(f"{path}: 'target_window.start' and 'target_window.end' must be strings")
    expected_life_areas = payload.get("expected_life_areas")
    if not isinstance(expected_life_areas, list) or not expected_life_areas:
        raise ValueError(f"{path}: 'expected_life_areas' must be a non-empty array")
    expected_event_types = payload.get("expected_event_types")
    if not isinstance(expected_event_types, list) or not expected_event_types:
        raise ValueError(f"{path}: 'expected_event_types' must be a non-empty array")
    _require_int(payload, "max_rank", path)
    _require_int(payload, "max_peak_distance_hours", path)
    _require_citations(payload, path)
    return payload


def validate_all() -> Dict[str, Any]:
    exact_cases = [validate_exact_scan_consistency_case(payload, EXACT_SCAN_FILE) for payload in load_jsonl_cases(EXACT_SCAN_FILE)]
    predictor_cases = [validate_predictor_stability_case(payload, PREDICTOR_STABILITY_FILE) for payload in load_jsonl_cases(PREDICTOR_STABILITY_FILE)]
    hindcast_cases = [validate_documented_hindcast_case(payload, DOCUMENTED_HINDCAST_FILE) for payload in load_jsonl_cases(DOCUMENTED_HINDCAST_FILE)]
    return {
        "exact_scan_consistency_case_count": len(exact_cases),
        "predictor_stability_case_count": len(predictor_cases),
        "documented_hindcast_case_count": len(hindcast_cases),
        "dataset_row_count": len(exact_cases) + len(predictor_cases) + len(hindcast_cases),
    }


def main() -> int:
    summary = validate_all()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
