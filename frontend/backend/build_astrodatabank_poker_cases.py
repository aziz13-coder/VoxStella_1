from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


DEFAULT_BENCHMARK_DIR = Path(__file__).resolve().parent / "benchmarks" / "astrocartography"
DEFAULT_INPUT_PATH = DEFAULT_BENCHMARK_DIR / "astrodatabank_poker_profiles.jsonl"
DEFAULT_OUTPUT_PATH = DEFAULT_BENCHMARK_DIR / "astrodatabank_poker_cases.jsonl"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _read_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        yield line_number, payload


def _required_object(payload: Dict[str, Any], key: str, context: str) -> Dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{context}: {key} must be an object")
    return value


def _required_list(payload: Dict[str, Any], key: str, context: str) -> List[Any]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{context}: {key} must be a non-empty list")
    return value


def _location_payload(raw: Any, context: str) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{context}: location must be an object")
    label = _normalize_text(raw.get("label") or raw.get("query") or raw.get("place") or raw.get("name"))
    if not label:
        raise ValueError(f"{context}: location.label is required")

    location: Dict[str, Any] = {"label": label}
    for key in (
        "latitude",
        "longitude",
        "timezone",
        "country_code",
        "country_name",
        "admin1_code",
        "population",
        "feature_code",
    ):
        value = raw.get(key)
        if value is not None and value != "":
            location[key] = value
    return location


def _birth_block(raw: Dict[str, Any], context: str) -> Dict[str, Any]:
    birth = {}
    for key in ("date", "time", "place"):
        value = _normalize_text(raw.get(key))
        if not value:
            raise ValueError(f"{context}: birth.{key} is required")
        birth[key] = value
    for key in ("timezone", "data_quality"):
        value = _normalize_text(raw.get(key))
        if value:
            birth[key] = value
    return birth


def _canonical_json(value: Dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def _collect_sources(*values: Any) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        if value is None or value == "":
            continue
        items = value if isinstance(value, list) else [value]
        for item in items:
            if item is None or item == "":
                continue
            if not isinstance(item, dict):
                raise ValueError(f"Source entries must be objects, got: {item!r}")
            serialized = _canonical_json(item)
            if serialized in seen:
                continue
            seen.add(serialized)
            sources.append(dict(item))
    return sources


def _performance_map(performances: Sequence[Dict[str, Any]], context: str) -> Dict[str, Dict[str, Any]]:
    mapped: Dict[str, Dict[str, Any]] = {}
    for index, performance in enumerate(performances, start=1):
        if not isinstance(performance, dict):
            raise ValueError(f"{context}: performances[{index}] must be an object")
        performance_id = _normalize_text(performance.get("performance_id") or performance.get("id"))
        if not performance_id:
            raise ValueError(f"{context}: performances[{index}] requires performance_id")
        normalized_key = performance_id.lower()
        if normalized_key in mapped:
            raise ValueError(f"{context}: duplicate performance_id {performance_id}")
        if not _normalize_text(performance.get("date")):
            raise ValueError(f"{context}: performances[{index}] requires date")
        _location_payload(performance.get("location"), f"{context}: performances[{index}]")
        mapped[normalized_key] = dict(performance)
    return mapped


def _control_reason(performance: Dict[str, Any]) -> str:
    explicit = _normalize_text(performance.get("benchmark_reason") or performance.get("reason"))
    if explicit:
        return explicit
    result_label = _normalize_text(performance.get("result_label"))
    venue_label = _normalize_text(performance.get("venue_label"))
    notes = _normalize_text(performance.get("notes"))
    base = "Same-player comparison venue from the curated performance history."
    if result_label and venue_label:
        base = f"Same-player comparison venue from {venue_label} ({result_label})."
    elif result_label:
        base = f"Same-player comparison venue with a weaker result ({result_label})."
    if notes:
        return f"{base} {notes}"
    return base


def _performance_entry(performance: Dict[str, Any], *, include_reason: bool) -> Dict[str, Any]:
    location = _location_payload(performance.get("location"), f"performance {performance.get('performance_id') or performance.get('id')}")
    entry: Dict[str, Any] = dict(location)
    for source_key, target_key in (
        ("result_label", "result_label"),
        ("outcome_strength", "outcome_strength"),
        ("outcome_tier", "outcome_tier"),
        ("outcome_value", "outcome_value"),
        ("currency", "currency"),
        ("field_size", "field_size"),
        ("venue_label", "venue_label"),
        ("tour", "tour"),
    ):
        value = performance.get(source_key)
        if value is not None and value != "":
            entry[target_key] = value
    if include_reason:
        entry["reason"] = _control_reason(performance)
    return entry


def _notes(*parts: Any) -> str:
    cleaned = [_normalize_text(part) for part in parts if _normalize_text(part)]
    return " ".join(cleaned)


def build_cases_from_profiles(profiles: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []

    for index, profile in enumerate(profiles, start=1):
        if not isinstance(profile, dict):
            raise ValueError(f"profiles[{index}] must be an object")
        context = f"profiles[{index}]"
        person_id = _normalize_text(profile.get("person_id"))
        person_name = _normalize_text(profile.get("person_name"))
        if not person_id:
            raise ValueError(f"{context}: person_id is required")
        if not person_name:
            raise ValueError(f"{context}: person_name is required")
        goal_id = _normalize_text(profile.get("goal_id")).lower() or "gambling_luck"
        birth = _birth_block(_required_object(profile, "birth", context), context)
        performances = _required_list(profile, "performances", context)
        targets = _required_list(profile, "benchmark_targets", context)
        performance_by_id = _performance_map(performances, context)

        profile_enabled = bool(profile.get("enabled", True))
        profile_notes = _normalize_text(profile.get("notes"))
        control_selection = _normalize_text(profile.get("control_selection")) or "explicit_control_ids"
        performance_context = profile.get("performance_context") if isinstance(profile.get("performance_context"), dict) else {}
        birth_source = profile.get("birth_source")
        event_history_source = profile.get("event_history_source")
        profile_sources = profile.get("sources")

        for target_index, target in enumerate(targets, start=1):
            if not isinstance(target, dict):
                raise ValueError(f"{context}: benchmark_targets[{target_index}] must be an object")
            target_perf_id = _normalize_text(target.get("performance_id"))
            if not target_perf_id:
                raise ValueError(f"{context}: benchmark_targets[{target_index}] requires performance_id")
            event_performance = performance_by_id.get(target_perf_id.lower())
            if event_performance is None:
                raise ValueError(f"{context}: target performance not found: {target_perf_id}")

            raw_control_ids = target.get("control_ids")
            if not isinstance(raw_control_ids, list) or not raw_control_ids:
                raise ValueError(f"{context}: benchmark_targets[{target_index}] requires non-empty control_ids")

            controls: List[Dict[str, Any]] = []
            seen_controls: set[str] = set()
            for control_raw in raw_control_ids:
                control_id = _normalize_text(control_raw)
                if not control_id:
                    raise ValueError(f"{context}: benchmark_targets[{target_index}] contains an empty control_id")
                normalized_control_id = control_id.lower()
                if normalized_control_id == target_perf_id.lower():
                    raise ValueError(f"{context}: benchmark_targets[{target_index}] cannot use the event performance as a control")
                if normalized_control_id in seen_controls:
                    continue
                seen_controls.add(normalized_control_id)
                control_performance = performance_by_id.get(normalized_control_id)
                if control_performance is None:
                    raise ValueError(f"{context}: control performance not found: {control_id}")
                controls.append(_performance_entry(control_performance, include_reason=True))

            target_enabled = bool(target.get("enabled", True))
            case_id = _normalize_text(target.get("case_id")) or f"{person_id}_{target_perf_id}".lower().replace(" ", "_")
            event_entry = _performance_entry(event_performance, include_reason=False)
            event: Dict[str, Any] = {
                "type": _normalize_text(target.get("event_type") or event_performance.get("event_type")) or "poker_result",
                "date": _normalize_text(event_performance.get("date")),
                "location": {
                    key: value
                    for key, value in event_entry.items()
                    if key in {"label", "latitude", "longitude", "timezone", "country_code", "country_name", "admin1_code", "population", "feature_code"}
                },
                "outcome_polarity": _normalize_text(target.get("outcome_polarity") or event_performance.get("outcome_polarity")) or "positive",
            }
            event_time = _normalize_text(event_performance.get("time"))
            if event_time:
                event["time"] = event_time
            for key in ("result_label", "outcome_strength", "outcome_tier", "outcome_value", "currency", "field_size", "venue_label", "tour"):
                if key in event_entry:
                    event[key] = event_entry[key]

            case: Dict[str, Any] = {
                "enabled": profile_enabled and target_enabled,
                "case_id": case_id,
                "goal_id": goal_id,
                "person_id": person_id,
                "person_name": person_name,
                "benchmark_family": "astrodatabank_poker",
                "benchmark_type": "within_person_venue_performance",
                "birth": birth,
                "event": event,
                "controls": controls,
                "control_selection": control_selection,
                "performance_context": performance_context,
                "sources": _collect_sources(
                    birth_source,
                    event_history_source,
                    event_performance.get("sources"),
                    target.get("sources"),
                    profile_sources,
                ),
                "notes": _notes(
                    profile_notes,
                    target.get("notes"),
                    event_performance.get("notes"),
                ),
                "dataset_builder": "build_astrodatabank_poker_cases.py",
            }

            transit_context = target.get("transit_context")
            if isinstance(transit_context, dict) and transit_context:
                case["transit_context"] = dict(transit_context)

            candidate_pool = target.get("candidate_pool")
            if isinstance(candidate_pool, list) and candidate_pool:
                case["candidate_pool"] = list(candidate_pool)

            cases.append(case)

    return cases


def load_poker_profiles(dataset_paths: Sequence[str | Path]) -> List[Dict[str, Any]]:
    profiles: List[Dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    for raw_path in dataset_paths:
        path = Path(raw_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Poker profile dataset not found: {path}")
        for line_number, payload in _read_jsonl(path):
            profile = dict(payload)
            profile["_dataset_path"] = str(path)
            profile["_line_number"] = line_number
            profiles.append(profile)

            for target in profile.get("benchmark_targets") or []:
                if not isinstance(target, dict):
                    continue
                case_id = _normalize_text(target.get("case_id"))
                if not case_id:
                    continue
                normalized = case_id.lower()
                if normalized in seen_case_ids:
                    raise ValueError(f"{path}:{line_number} duplicate case_id across targets: {case_id}")
                seen_case_ids.add(normalized)
    return profiles


def write_cases_jsonl(cases: Sequence[Dict[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = "\n".join(json.dumps(case, ensure_ascii=True, separators=(",", ":")) for case in cases)
    path.write_text(f"{rendered}\n" if rendered else "", encoding="utf-8")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Astro-Databank-linked poker performance profiles into astrocartography benchmark cases.",
    )
    parser.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Input profile JSONL path. Defaults to the template file in backend/benchmarks/astrocartography.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output benchmark JSONL path.",
    )
    args = parser.parse_args(argv)

    profiles = load_poker_profiles(args.inputs or [DEFAULT_INPUT_PATH])
    cases = build_cases_from_profiles(profiles)
    output_path = write_cases_jsonl(cases, args.output)
    print(f"Wrote {len(cases)} cases to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
