from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _resolve_reference_root() -> Path:
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "AGENTS.md").exists() and (parent / "backend").is_dir():
            return parent
    return current_path.parents[1]


REPO_ROOT = _resolve_reference_root()
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_DATASET_PATH = (
    BACKEND_ROOT / "benchmarks" / "forensic" / "worst_roommate_ever_cases.json"
)

for import_path in (REPO_ROOT, BACKEND_ROOT):
    import_value = str(import_path)
    if import_value not in sys.path:
        sys.path.insert(0, import_value)

from forensic.benchmark_policy import benchmark_exclusion_reason  # noqa: E402


AXIS_KEYWORDS: Dict[str, List[str]] = {
    "violence_homicide": [
        "assault",
        "attack",
        "beaten",
        "blunt force",
        "bodily injury",
        "death",
        "fatal",
        "gunfire",
        "gunshot",
        "homicide",
        "killing",
        "murder",
        "strangulation",
        "violent",
        "violence",
    ],
    "abduction_missing_person": [
        "abduction",
        "captivity",
        "confine",
        "confinement",
        "detention",
        "disappearance",
        "kidnapping",
        "missing",
        "seizure",
        "taken",
    ],
    "deception_coverup": [
        "conceal",
        "concealment",
        "cover-up",
        "coverup",
        "deception",
        "disposal",
        "hidden",
        "lie",
        "lies",
        "remains",
        "staged",
    ],
    "immediate_scene_or_vicinity_context": [
        "front of the victim",
        "immediate scene",
        "in the vicinity",
        "near the victim",
        "not been taken",
        "residence",
        "voluntarily left",
    ],
    "trafficking_or_possession_context": [
        "exploitation",
        "human trafficking",
        "made a possession",
        "person a possession",
        "possession",
        "possession or value motive",
        "sex trafficking",
        "sex trade",
        "sold",
        "taken for trafficking",
        "trafficking",
        "treated as a possession",
        "value motive",
    ],
    "communication_vehicle_short_distance_context": [
        "communication issue",
        "cousins",
        "local movement",
        "short distance",
        "sibling",
        "verbal argument",
        "vehicle",
        "vehicles involved",
    ],
    "family_home_end_matter_context": [
        "end of the matter",
        "family",
        "home",
        "house of the end",
        "tomb",
        "womb",
    ],
    "party_entertainment_context": [
        "dancing",
        "drinking",
        "entertainment",
        "fun",
        "party",
        "partying",
    ],
    "routine_disruption_stalker_context": [
        "disrupted",
        "normal thing",
        "routine",
        "stalker",
        "watching the victim",
    ],
    "suspect_territory_context": [
        "open enemy",
        "right in front of the suspect",
        "suspect territory",
        "suspects nose",
        "where the suspect feels comfortable",
    ],
    "death_financial_entanglement_context": [
        "debts",
        "deceased person",
        "financial disagreement",
        "house of death",
        "inheritance",
    ],
    "far_distance_departure_context": [
        "far away",
        "farther away",
        "further away",
        "going further away",
    ],
    "public_authority_witness_context": [
        "authorities",
        "boss",
        "government",
        "out in the open",
        "police",
        "public",
        "seen by a witness",
        "witness",
    ],
    "friends_social_circle_context": [
        "friends",
        "friends may know",
        "hopes and dreams",
        "social circle",
        "surrounded by friends",
    ],
    "hidden_captive_kidnapped_context": [
        "enclosed area",
        "hidden",
        "kept hidden",
        "kidnapped",
        "may not be found",
    ],
    "domestic_partner_involvement": [
        "7th house",
        "couple",
        "domestic",
        "husband",
        "partner",
        "relationship",
        "spouse",
        "wife",
    ],
    "family_involvement": [
        "brother",
        "custody",
        "family",
        "father",
        "household",
        "mother",
        "parent",
        "parents",
        "sibling",
        "son",
    ],
    "child_victim": [
        "5th house",
        "baby",
        "child",
        "children",
        "custody",
        "daughter",
        "infant",
        "minor",
        "son",
    ],
    "water_disappearance_or_drowning": [
        "beach",
        "boat",
        "drowning",
        "fluids",
        "harbor",
        "marina",
        "pool",
        "river",
        "sea",
        "water",
    ],
    "accident_or_disaster": [
        "accident",
        "catastrophic accident",
        "disaster",
        "fire",
        "mechanical",
        "natural",
        "unintentional",
    ],
    "friend_or_close_associate": [
        "acquaintance",
        "boarding house",
        "close associate",
        "cohabitation",
        "friend",
        "known person",
        "known to",
        "known-person",
        "landlord",
        "lodger",
        "roommate",
        "tenant",
    ],
    "authority_or_public_case": [
        "authority",
        "institution",
        "law",
        "legal",
        "police",
        "public",
    ],
    "accomplice_or_witness": [
        "accomplice",
        "helper",
        "more than one",
        "two perpetrators",
        "witness",
    ],
    "route_vehicle_transport": [
        "car",
        "driveway",
        "highway",
        "license plate",
        "movement",
        "road",
        "roads",
        "route",
        "transport",
        "travel",
        "trunk",
        "vehicle",
        "vehicles",
    ],
}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _keyword_matches(blob: str, keyword: str) -> bool:
    if not blob or not keyword:
        return False
    escaped = re.escape(keyword.lower())
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", blob) is not None


def load_worst_roommate_benchmark_dataset(
    path: str | Path = DEFAULT_DATASET_PATH,
) -> Dict[str, Any]:
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Worst Roommate Ever benchmark dataset not found: {dataset_path}")
    return json.loads(dataset_path.read_text(encoding="utf-8"))


def _source_ids_from(value: Any) -> List[str]:
    if isinstance(value, dict):
        source_ids = value.get("source_ids")
        return [str(item) for item in source_ids or [] if str(item).strip()]
    return []


def _check_fact_object(
    *,
    fact: Any,
    context: str,
    source_ids: set[str],
    missing_source_references: List[Dict[str, str]],
    fact_source_gaps: List[Dict[str, str]],
) -> None:
    if not isinstance(fact, dict):
        fact_source_gaps.append({"context": context, "detail": "fact is not an object"})
        return

    ids = _source_ids_from(fact)
    if not ids:
        fact_source_gaps.append({"context": context, "detail": "missing source_ids"})
    if not _normalize_text(fact.get("confidence")):
        fact_source_gaps.append({"context": context, "detail": "missing confidence"})
    for source_id in ids:
        if source_id not in source_ids:
            missing_source_references.append(
                {"context": context, "source_id": source_id, "detail": "unknown source_id"}
            )


def validate_worst_roommate_dataset(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Worst Roommate Ever benchmark payload must be an object")

    sources = payload.get("sources") or []
    if not isinstance(sources, list) or not sources:
        raise ValueError("Worst Roommate Ever benchmark requires a non-empty sources list")

    source_ids: set[str] = set()
    duplicate_sources: List[str] = []
    source_gaps: List[Dict[str, str]] = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            source_gaps.append({"context": f"sources[{index}]", "detail": "source is not an object"})
            continue
        source_id = _normalize_text(source.get("id"))
        if not source_id:
            source_gaps.append({"context": f"sources[{index}]", "detail": "missing id"})
            continue
        if source_id in source_ids:
            duplicate_sources.append(source_id)
        source_ids.add(source_id)
        for key in ("kind", "title", "url", "metadata_strength"):
            if not _normalize_text(source.get(key)):
                source_gaps.append(
                    {"context": f"sources[{source_id}]", "detail": f"missing {key}"}
                )

    cases = payload.get("cases") or []
    if not isinstance(cases, list) or not cases:
        raise ValueError("Worst Roommate Ever benchmark requires a non-empty cases list")

    missing_source_references: List[Dict[str, str]] = []
    fact_source_gaps: List[Dict[str, str]] = []
    runnable_case_ids: List[str] = []
    holdout_case_ids: List[str] = []
    case_ids: set[str] = set()
    duplicate_case_ids: List[str] = []
    season_counts: Counter[int] = Counter()

    for case_index, case in enumerate(cases):
        if not isinstance(case, dict):
            fact_source_gaps.append({"context": f"cases[{case_index}]", "detail": "case is not an object"})
            continue

        case_id = _normalize_text(case.get("id"))
        if not case_id:
            fact_source_gaps.append({"context": f"cases[{case_index}]", "detail": "missing id"})
            case_id = f"case_index_{case_index}"
        if case_id in case_ids:
            duplicate_case_ids.append(case_id)
        case_ids.add(case_id)

        episode = case.get("episode") or {}
        if not isinstance(episode, dict):
            fact_source_gaps.append({"context": f"{case_id}.episode", "detail": "episode is not an object"})
        else:
            try:
                season_counts[int(episode.get("season"))] += 1
            except Exception:
                fact_source_gaps.append(
                    {"context": f"{case_id}.episode", "detail": "missing numeric season"}
                )
            if not _normalize_text(episode.get("title")):
                fact_source_gaps.append({"context": f"{case_id}.episode", "detail": "missing title"})
            if not _normalize_text(episode.get("confidence")):
                fact_source_gaps.append({"context": f"{case_id}.episode", "detail": "missing confidence"})
            for source_id in _source_ids_from(episode):
                if source_id not in source_ids:
                    missing_source_references.append(
                        {
                            "context": f"{case_id}.episode",
                            "source_id": source_id,
                            "detail": "unknown source_id",
                        }
                    )

        inventory = case.get("case_inventory") or {}
        if not isinstance(inventory, dict):
            fact_source_gaps.append(
                {"context": f"{case_id}.case_inventory", "detail": "case_inventory is not an object"}
            )
            inventory = {}

        for key in ("real_people", "relationship_context", "incident_type", "outcome"):
            _check_fact_object(
                fact=inventory.get(key),
                context=f"{case_id}.case_inventory.{key}",
                source_ids=source_ids,
                missing_source_references=missing_source_references,
                fact_source_gaps=fact_source_gaps,
            )

        for key in ("key_dates", "locations"):
            items = inventory.get(key)
            if not isinstance(items, list) or not items:
                fact_source_gaps.append(
                    {"context": f"{case_id}.case_inventory.{key}", "detail": "missing non-empty list"}
                )
                continue
            for item_index, item in enumerate(items):
                _check_fact_object(
                    fact=item,
                    context=f"{case_id}.case_inventory.{key}[{item_index}]",
                    source_ids=source_ids,
                    missing_source_references=missing_source_references,
                    fact_source_gaps=fact_source_gaps,
                )

        birth_times = inventory.get("birth_times") or {}
        if not isinstance(birth_times, dict) or birth_times.get("status") != "not_used_not_collected":
            fact_source_gaps.append(
                {
                    "context": f"{case_id}.case_inventory.birth_times",
                    "detail": "birth_times must be marked not_used_not_collected",
                }
            )

        benchmark = case.get("benchmark") or {}
        replay_status = _normalize_text(benchmark.get("replay_status"))
        if replay_status == "runnable":
            runnable_case_ids.append(case_id)
            if not isinstance(benchmark.get("event_anchor"), dict):
                fact_source_gaps.append(
                    {"context": f"{case_id}.benchmark.event_anchor", "detail": "missing event_anchor"}
                )
            else:
                for source_id in _source_ids_from(benchmark["event_anchor"]):
                    if source_id not in source_ids:
                        missing_source_references.append(
                            {
                                "context": f"{case_id}.benchmark.event_anchor",
                                "source_id": source_id,
                                "detail": "unknown source_id",
                            }
                        )
            query = benchmark.get("query")
            if not isinstance(query, dict) or not query.get("datetime_local"):
                fact_source_gaps.append(
                    {"context": f"{case_id}.benchmark.query", "detail": "runnable case needs query.datetime_local"}
                )
        elif replay_status == "holdout_missing_precise_event_time":
            holdout_case_ids.append(case_id)
            if not _normalize_text(benchmark.get("hold_reason")):
                fact_source_gaps.append(
                    {"context": f"{case_id}.benchmark.hold_reason", "detail": "holdout needs hold_reason"}
                )
        else:
            fact_source_gaps.append(
                {
                    "context": f"{case_id}.benchmark.replay_status",
                    "detail": f"unsupported replay_status {replay_status!r}",
                }
            )

        if not benchmark.get("expected_primary_axes"):
            fact_source_gaps.append(
                {"context": f"{case_id}.benchmark.expected_primary_axes", "detail": "missing expected axes"}
            )

    return {
        "case_count": len(cases),
        "source_count": len(sources),
        "season_counts": dict(sorted(season_counts.items())),
        "runnable_case_count": len(runnable_case_ids),
        "runnable_case_ids": runnable_case_ids,
        "holdout_case_count": len(holdout_case_ids),
        "holdout_case_ids": holdout_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "duplicate_source_ids": duplicate_sources,
        "source_gaps": source_gaps,
        "missing_source_references": missing_source_references,
        "fact_source_gaps": fact_source_gaps,
    }


def _case_benchmark(case: Dict[str, Any]) -> Dict[str, Any]:
    benchmark = case.get("benchmark")
    return benchmark if isinstance(benchmark, dict) else case


def build_forensic_query(case: Dict[str, Any]) -> Dict[str, str]:
    benchmark = _case_benchmark(case)
    query = dict(benchmark.get("query") or {})
    datetime_local = query.pop("datetime_local", None)
    if datetime_local:
        query["datetime"] = datetime_local
    return {key: str(value) for key, value in query.items() if value is not None}


@lru_cache(maxsize=1)
def _make_forensic_app():
    from flask import Flask
    import backend.astro_clock_api as astro_clock_api

    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def _call_forensic_route(query: Dict[str, str]) -> Dict[str, Any]:
    app = _make_forensic_app()
    response = app.test_client().get("/api/astro-clock/forensic", query_string=query)
    try:
        payload = response.get_json() or {}
    except Exception as exc:  # pragma: no cover - Flask usually returns JSON here.
        payload = {"success": False, "error": f"Could not decode JSON response: {exc}"}
    return {"status_code": int(response.status_code), "payload": payload}


def _result_text_blob(forensic_result: Dict[str, Any], *, include_rationales: bool = True) -> str:
    findings = forensic_result.get("findings") or []
    categories = forensic_result.get("categories") or {}
    dominance = forensic_result.get("dominance") or {}
    text_parts: List[str] = []

    for finding in findings:
        if not isinstance(finding, dict):
            continue
        keys = ("title", "category", "rationale", "evidence") if include_rationales else ("title", "category")
        for key in keys:
            value = finding.get(key)
            if value:
                if isinstance(value, (dict, list)):
                    text_parts.append(json.dumps(value, sort_keys=True))
                else:
                    text_parts.append(str(value))

    if isinstance(categories, dict):
        text_parts.extend(str(key) for key in categories.keys())

    if isinstance(dominance, dict):
        text_parts.extend(str(key) for key in dominance.keys())
        for value in dominance.values():
            if isinstance(value, dict):
                for subvalue in value.values():
                    if subvalue:
                        text_parts.append(str(subvalue))

    survivability = forensic_result.get("survivability") or {}
    if isinstance(survivability, dict):
        text_parts.append(str(survivability.get("level") or ""))
        text_parts.append(str(survivability.get("outcome_band") or ""))

    return " ".join(text_parts).lower()


def compare_case_to_forensic_output(
    case: Dict[str, Any],
    forensic_result: Dict[str, Any],
) -> Dict[str, Any]:
    benchmark = _case_benchmark(case)
    blob = _result_text_blob(forensic_result, include_rationales=True)
    contradiction_blob = _result_text_blob(forensic_result, include_rationales=False)
    matched: List[str] = []
    missed: List[str] = []
    contradicted: List[str] = []

    for axis in benchmark.get("expected_primary_axes") or []:
        keywords = AXIS_KEYWORDS.get(axis, [])
        if any(_keyword_matches(blob, keyword) for keyword in keywords):
            matched.append(axis)
        else:
            missed.append(axis)

    for axis in benchmark.get("contradictory_axes") or []:
        keywords = AXIS_KEYWORDS.get(axis, [])
        if any(_keyword_matches(contradiction_blob, keyword) for keyword in keywords):
            contradicted.append(axis)

    if contradicted:
        status = "misaligned"
    elif not missed:
        status = "aligned"
    elif matched:
        status = "partially_aligned"
    else:
        status = "misaligned"

    return {
        "status": status,
        "matched_axes": matched,
        "missed_axes": missed,
        "contradicted_axes": contradicted,
    }


def _compare_survivability(case: Dict[str, Any], forensic_result: Dict[str, Any]) -> Dict[str, Any]:
    benchmark = _case_benchmark(case)
    expected = benchmark.get("expected_survivability") or {}
    survivability = forensic_result.get("survivability") or {}
    expected_levels = set(expected.get("levels") or [])
    expected_bands = set(expected.get("bands") or [])
    level = survivability.get("level")
    band = survivability.get("outcome_band")

    level_match = bool(expected_levels and level in expected_levels)
    band_match = bool(expected_bands and band in expected_bands)
    if level_match and band_match:
        status = "aligned"
    elif level_match or band_match:
        status = "partially_aligned"
    elif expected_levels or expected_bands:
        status = "misaligned"
    else:
        status = "not_scored"

    return {
        "status": status,
        "expected_levels": sorted(expected_levels),
        "expected_bands": sorted(expected_bands),
        "actual_level": level,
        "actual_band": band,
        "actual_score": survivability.get("score"),
    }


def _summarize_case_result(case: Dict[str, Any], route_result: Dict[str, Any]) -> Dict[str, Any]:
    payload = route_result.get("payload") or {}
    findings = payload.get("findings") or []
    top_findings = []
    for finding in findings[:10]:
        if not isinstance(finding, dict):
            continue
        top_findings.append(
            {
                "id": finding.get("id"),
                "title": finding.get("title"),
                "category": finding.get("category"),
                "weight": finding.get("weight"),
            }
        )

    comparison = compare_case_to_forensic_output(case, payload)
    survivability_comparison = _compare_survivability(case, payload)
    benchmark = _case_benchmark(case)
    anchor = benchmark.get("event_anchor") or {}
    episode = case.get("episode") or {}

    return {
        "case_id": case.get("id"),
        "episode": {
            "season": episode.get("season"),
            "episode": episode.get("episode"),
            "title": episode.get("title"),
        },
        "event_anchor": {
            "type": anchor.get("type"),
            "datetime_local": (
                f"{anchor.get('date_local')}T{anchor.get('time_local')}"
                if anchor.get("date_local") and anchor.get("time_local")
                else None
            ),
            "timezone": anchor.get("timezone"),
            "location": anchor.get("location"),
            "metadata_confidence": anchor.get("metadata_confidence"),
        },
        "query": build_forensic_query(case),
        "status_code": route_result.get("status_code"),
        "success": bool(payload.get("success")),
        "error": payload.get("error"),
        "comparison": comparison,
        "survivability_comparison": survivability_comparison,
        "categories": payload.get("categories") or {},
        "survivability": {
            key: (payload.get("survivability") or {}).get(key)
            for key in ("level", "score", "outcome_band")
        },
        "top_findings": top_findings,
        "finding_count": len(findings),
    }


def _summarize_holdout(case: Dict[str, Any]) -> Dict[str, Any]:
    episode = case.get("episode") or {}
    benchmark = _case_benchmark(case)
    return {
        "case_id": case.get("id"),
        "episode": {
            "season": episode.get("season"),
            "episode": episode.get("episode"),
            "title": episode.get("title"),
        },
        "hold_reason": benchmark.get("hold_reason"),
        "expected_primary_axes": list(benchmark.get("expected_primary_axes") or []),
    }


def _filter_cases(cases: Sequence[Dict[str, Any]], case_id: Optional[str]) -> List[Dict[str, Any]]:
    normalized = _normalize_text(case_id).lower()
    eligible = []
    excluded_matches = []
    for case in cases:
        exclusion_reason = benchmark_exclusion_reason(case)
        if exclusion_reason:
            if normalized and _normalize_text(case.get("id")).lower() == normalized:
                excluded_matches.append(exclusion_reason)
            continue
        eligible.append(case)
    if not normalized:
        return eligible
    if excluded_matches:
        raise ValueError(f"Excluded Worst Roommate Ever benchmark case id: {case_id}. {excluded_matches[0]}")
    selected = [case for case in eligible if _normalize_text(case.get("id")).lower() == normalized]
    if not selected:
        raise ValueError(f"Unknown Worst Roommate Ever benchmark case id: {case_id}")
    return selected


def run_worst_roommate_benchmark_suite(
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    *,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload = load_worst_roommate_benchmark_dataset(dataset_path)
    validation = validate_worst_roommate_dataset(payload)
    cases = _filter_cases(payload.get("cases") or [], case_id)
    runnable = [case for case in cases if _case_benchmark(case).get("replay_status") == "runnable"]
    holdouts = [
        case
        for case in cases
        if _case_benchmark(case).get("replay_status") == "holdout_missing_precise_event_time"
    ]

    case_results: List[Dict[str, Any]] = []
    route_errors: List[Dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    survivability_status_counts: Counter[str] = Counter()
    axis_expected: Counter[str] = Counter()
    axis_matched: Counter[str] = Counter()
    false_positive_contradictions: Counter[str] = Counter()

    for case in runnable:
        query = build_forensic_query(case)
        route_result = _call_forensic_route(query)
        summary = _summarize_case_result(case, route_result)
        case_results.append(summary)

        if summary["status_code"] != 200 or not summary["success"]:
            route_errors.append(
                {
                    "case_id": case.get("id"),
                    "status_code": summary["status_code"],
                    "error": summary.get("error"),
                }
            )
            continue

        comparison = summary["comparison"]
        status_counts[str(comparison.get("status") or "unknown")] += 1
        for axis in comparison.get("matched_axes") or []:
            axis_matched[str(axis)] += 1
        for axis in _case_benchmark(case).get("expected_primary_axes") or []:
            axis_expected[str(axis)] += 1
        for axis in comparison.get("contradicted_axes") or []:
            false_positive_contradictions[str(axis)] += 1
        survivability_status_counts[
            str(summary["survivability_comparison"].get("status") or "unknown")
        ] += 1

    expected_total = sum(axis_expected.values())
    matched_total = sum(axis_matched.values())
    primary_axis_recall = round(matched_total / expected_total, 4) if expected_total else None

    metrics = {
        "runnable_case_count": len(runnable),
        "holdout_case_count": len(holdouts),
        "route_error_count": len(route_errors),
        "comparison_status_counts": dict(sorted(status_counts.items())),
        "survivability_status_counts": dict(sorted(survivability_status_counts.items())),
        "primary_axis_expected_count": expected_total,
        "primary_axis_matched_count": matched_total,
        "primary_axis_recall": primary_axis_recall,
        "axis_expected_counts": dict(sorted(axis_expected.items())),
        "axis_matched_counts": dict(sorted(axis_matched.items())),
        "false_positive_contradictions": dict(sorted(false_positive_contradictions.items())),
    }

    return {
        "benchmark_id": payload.get("benchmark_id"),
        "dataset_path": str(Path(dataset_path).resolve()),
        "inventory": validation,
        "metrics": metrics,
        "route_errors": route_errors,
        "case_results": case_results,
        "holdouts": [_summarize_holdout(case) for case in holdouts],
    }


def render_markdown_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Worst Roommate Ever Forensic Benchmark Report")
    lines.append("")
    lines.append(f"- Benchmark ID: `{report.get('benchmark_id')}`")
    lines.append(f"- Dataset: `{report.get('dataset_path')}`")
    lines.append("")

    inventory = report.get("inventory") or {}
    lines.append("## Inventory")
    lines.append("")
    lines.append(f"- Cases: {inventory.get('case_count')}")
    lines.append(f"- Sources: {inventory.get('source_count')}")
    lines.append(f"- Season counts: `{inventory.get('season_counts')}`")
    lines.append(f"- Runnable cases: {inventory.get('runnable_case_count')}")
    lines.append(f"- Holdout cases: {inventory.get('holdout_case_count')}")
    lines.append(f"- Missing source references: {len(inventory.get('missing_source_references') or [])}")
    lines.append(f"- Fact source gaps: {len(inventory.get('fact_source_gaps') or [])}")
    lines.append("")

    metrics = report.get("metrics") or {}
    lines.append("## Baseline Metrics")
    lines.append("")
    lines.append(f"- Runnable case count: {metrics.get('runnable_case_count')}")
    lines.append(f"- Route error count: {metrics.get('route_error_count')}")
    lines.append(f"- Comparison statuses: `{metrics.get('comparison_status_counts')}`")
    lines.append(f"- Survivability statuses: `{metrics.get('survivability_status_counts')}`")
    lines.append(
        "- Primary-axis recall: "
        f"{metrics.get('primary_axis_matched_count')}/{metrics.get('primary_axis_expected_count')} "
        f"= {metrics.get('primary_axis_recall')}"
    )
    lines.append(f"- False-positive contradictions: `{metrics.get('false_positive_contradictions')}`")
    lines.append("")

    route_errors = report.get("route_errors") or []
    if route_errors:
        lines.append("## Route Errors")
        lines.append("")
        for error in route_errors:
            lines.append(
                f"- `{error.get('case_id')}`: status={error.get('status_code')} error={error.get('error')}"
            )
        lines.append("")

    lines.append("## Runnable Case Results")
    lines.append("")
    for result in report.get("case_results") or []:
        episode = result.get("episode") or {}
        comparison = result.get("comparison") or {}
        survivability = result.get("survivability") or {}
        survival_cmp = result.get("survivability_comparison") or {}
        lines.append(
            f"- `{result.get('case_id')}` S{episode.get('season')}E{episode.get('episode')} "
            f"{episode.get('title')}: {comparison.get('status')} "
            f"(matched={comparison.get('matched_axes')}, missed={comparison.get('missed_axes')}, "
            f"contradicted={comparison.get('contradicted_axes')}); "
            f"survivability={survivability.get('level')}/{survivability.get('outcome_band')} "
            f"({survival_cmp.get('status')})"
        )
        top_titles = [
            _normalize_text(item.get("title"))
            for item in result.get("top_findings") or []
            if _normalize_text(item.get("title"))
        ][:5]
        if top_titles:
            lines.append(f"  Top findings: {', '.join(top_titles)}")
    lines.append("")

    lines.append("## Holdouts")
    lines.append("")
    holdouts = report.get("holdouts") or []
    if not holdouts:
        lines.append("- none")
    else:
        for holdout in holdouts:
            episode = holdout.get("episode") or {}
            lines.append(
                f"- `{holdout.get('case_id')}` S{episode.get('season')}E{episode.get('episode')} "
                f"{episode.get('title')}: {holdout.get('hold_reason')}"
            )

    return "\n".join(lines).strip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Netflix Worst Roommate Ever forensic benchmark."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--case-id", help="Restrict execution to a single case id.")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to the Worst Roommate Ever benchmark dataset.",
    )
    args = parser.parse_args(argv)

    report = run_worst_roommate_benchmark_suite(args.dataset, case_id=args.case_id)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown_report(report))

    inventory = report.get("inventory") or {}
    validation_failure = any(
        inventory.get(key)
        for key in (
            "duplicate_case_ids",
            "duplicate_source_ids",
            "source_gaps",
            "missing_source_references",
            "fact_source_gaps",
        )
    )
    return 1 if validation_failure or report.get("route_errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
