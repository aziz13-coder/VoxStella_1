from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = Path(__file__).resolve().parent / "benchmarks" / "synastry"
LOCAL_SAMPLE_FILE = BASE_DIR / "predictive_pairs_sample.json"
REAL_PUBLIC_FILE = BASE_DIR / "real_public_pairs.json"
EXTERNAL_PUBLIC_PAIRS_FILE = Path(
    os.environ.get("VOX_STELLA_SYNASTRY_PUBLIC_PAIRS_PATH")
    or r"C:\Program Files (x86)\Galaxy\docs\research\compatibility_public_pairs.json"
)
DEFAULT_PREDICTIVE_DATASET_PATHS = [
    path for path in (EXTERNAL_PUBLIC_PAIRS_FILE, REAL_PUBLIC_FILE) if path.exists()
] or [LOCAL_SAMPLE_FILE]
DEFAULT_LOGIC_FIXTURE_PATHS = [
    REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_1.json",
    REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_2.json",
    REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_3.json",
]
SUPPORTED_PERSON_KINDS = {"raw", "bank", "chart_data"}
SUPPORTED_CASE_MODES = {"overall", "union", "work"}


def load_json_object(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} root payload must be an object")
    return payload


def _require_keys(payload: Dict[str, Any], keys: Sequence[str], context: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"{context} missing required keys: {', '.join(missing)}")


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_mode(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"overall", "life_themes", "themes"}:
        return "overall"
    if raw in {"union", "union_dynamics", "marital", "relationship"}:
        return "union"
    if raw in {"work", "work_alliance", "business"}:
        return "work"
    return raw


def _validate_chart_data(chart_data: Any, context: str) -> None:
    if not isinstance(chart_data, dict):
        raise ValueError(f"{context} chart_data must be an object")
    planets = chart_data.get("planets")
    if not isinstance(planets, (list, dict)):
        raise ValueError(f"{context} chart_data.planets must be a list or object")
    if chart_data.get("ascendant") is None:
        raise ValueError(f"{context} chart_data.ascendant is required")


def validate_person_record(person: Dict[str, Any], path: Path) -> None:
    context = f"{path.name}:person:{person.get('person_id') or 'unknown'}"
    _require_keys(person, ["person_id", "kind", "label"], context)

    kind = str(person.get("kind") or "").strip().lower()
    if kind not in SUPPORTED_PERSON_KINDS:
        raise ValueError(
            f"{context} kind must be one of: {', '.join(sorted(SUPPORTED_PERSON_KINDS))}"
        )

    if kind == "raw":
        _require_keys(person, ["dt", "lat", "lon", "delta_t", "place"], context)
    elif kind == "bank":
        _require_keys(person, ["dbf", "row"], context)
    else:
        _require_keys(person, ["chart_data"], context)
        _validate_chart_data(person.get("chart_data"), context)


def validate_case_record(case: Dict[str, Any], path: Path, person_ids: Sequence[str]) -> None:
    context = f"{path.name}:case:{case.get('case_id') or 'unknown'}"
    _require_keys(
        case,
        ["case_id", "mode", "anchor_person_id", "true_partner_id", "candidate_ids"],
        context,
    )

    mode = _normalize_mode(case.get("mode"))
    if mode not in SUPPORTED_CASE_MODES:
        raise ValueError(
            f"{context} mode must be one of: {', '.join(sorted(SUPPORTED_CASE_MODES))}"
        )

    if not isinstance(case.get("candidate_ids"), list) or not case.get("candidate_ids"):
        raise ValueError(f"{context} candidate_ids must be a non-empty list")

    known_people = {str(person_id) for person_id in person_ids}
    anchor_person_id = str(case.get("anchor_person_id") or "").strip()
    true_partner_id = str(case.get("true_partner_id") or "").strip()
    if anchor_person_id not in known_people:
        raise ValueError(f"{context} anchor_person_id is unknown: {anchor_person_id}")
    if true_partner_id not in known_people:
        raise ValueError(f"{context} true_partner_id is unknown: {true_partner_id}")

    candidate_ids = [str(item or "").strip() for item in case.get("candidate_ids") or []]
    if true_partner_id not in candidate_ids:
        raise ValueError(f"{context} candidate_ids must include true_partner_id")
    missing_candidates = [item for item in candidate_ids if item not in known_people]
    if missing_candidates:
        raise ValueError(
            f"{context} candidate_ids contain unknown people: {', '.join(missing_candidates)}"
        )


def validate_logic_fixture_case(case: Dict[str, Any], path: Path) -> None:
    context = f"{path.name}:logic_case:{case.get('id') or case.get('case_id') or 'unknown'}"
    _require_keys(case, ["chart_data_a", "chart_data_b"], context)
    _validate_chart_data(case.get("chart_data_a"), f"{context}:chart_data_a")
    _validate_chart_data(case.get("chart_data_b"), f"{context}:chart_data_b")
    options = case.get("options")
    if options is not None and not isinstance(options, dict):
        raise ValueError(f"{context} options must be an object when present")


def load_synastry_predictive_dataset(path: Path) -> Dict[str, Any]:
    payload = load_json_object(path)
    people = payload.get("people")
    cases = payload.get("cases")
    if not isinstance(people, list) or not people:
        raise ValueError(f"{path.name} people must be a non-empty list")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path.name} cases must be a non-empty list")

    person_ids: List[str] = []
    for person in people:
        if not isinstance(person, dict):
            raise ValueError(f"{path.name} people entries must be objects")
        validate_person_record(person, path)
        person_ids.append(str(person["person_id"]))

    if len(person_ids) != len(set(person_ids)):
        raise ValueError(f"{path.name} contains duplicate person_id values")

    seen_case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{path.name} cases entries must be objects")
        validate_case_record(case, path, person_ids)
        case_id = str(case["case_id"])
        if case_id in seen_case_ids:
            raise ValueError(f"{path.name} duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)

    return payload


def load_logic_fixture(path: Path) -> Dict[str, Any]:
    payload = load_json_object(path)
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path.name} cases must be a non-empty list")
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{path.name} logic cases entries must be objects")
        validate_logic_fixture_case(case, path)
    return payload


def validate_synastry_benchmark_datasets(
    predictive_dataset_paths: Optional[Sequence[str | Path]] = None,
    logic_fixture_paths: Optional[Sequence[str | Path]] = None,
) -> Dict[str, Any]:
    predictive_people_by_kind: Dict[str, int] = {kind: 0 for kind in sorted(SUPPORTED_PERSON_KINDS)}
    predictive_mode_counts: Dict[str, int] = {mode: 0 for mode in sorted(SUPPORTED_CASE_MODES)}
    predictive_case_count = 0
    predictive_people_count = 0
    logic_case_count = 0
    predictive_paths: List[str] = []
    logic_paths: List[str] = []

    for raw_path in predictive_dataset_paths or DEFAULT_PREDICTIVE_DATASET_PATHS:
        path = Path(raw_path).resolve()
        dataset = load_synastry_predictive_dataset(path)
        predictive_paths.append(str(path))
        people = dataset.get("people") or []
        cases = dataset.get("cases") or []
        predictive_people_count += len(people)
        predictive_case_count += len(cases)
        for person in people:
            predictive_people_by_kind[str(person.get("kind") or "").strip().lower()] += 1
        for case in cases:
            predictive_mode_counts[_normalize_mode(case.get("mode"))] += 1

    for raw_path in logic_fixture_paths or DEFAULT_LOGIC_FIXTURE_PATHS:
        path = Path(raw_path).resolve()
        fixture = load_logic_fixture(path)
        logic_paths.append(str(path))
        logic_case_count += len(fixture.get("cases") or [])

    return {
        "predictive_dataset_paths": predictive_paths,
        "logic_fixture_paths": logic_paths,
        "predictive_people_count": predictive_people_count,
        "predictive_case_count": predictive_case_count,
        "logic_case_count": logic_case_count,
        "predictive_people_by_kind": predictive_people_by_kind,
        "predictive_mode_counts": predictive_mode_counts,
        "dataset_row_count": predictive_case_count + logic_case_count,
    }


def main() -> int:
    report = validate_synastry_benchmark_datasets()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
