from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from mundane_assets import get_domain_definitions, get_polity_definitions
from mundane_models import ActiveClockContext
from mundane_service import (
    analyze_context,
    build_context_request,
    get_chart_type_domain_pairing_policy,
    resolve_context,
)
from validate_mundane_benchmark_datasets import (
    HISTORICAL_FILES,
    load_jsonl_cases,
    validate_historical_case,
)


DEFAULT_DATASET_PATHS = list(HISTORICAL_FILES)
SUPPORTED_ENGINE_DOMAINS = {
    "war_conflict",
    "war_outbreak",
    "campaign_escalation",
    "military_reversal",
    "government_stability",
    "leadership_transition",
    "regime_stability",
    "alliance_stress",
    "trade_and_commerce",
    "diplomacy_foreign_affairs",
    "epidemic_wave_pressure",
    "public_health",
    "civil_unrest",
    "finance_economy",
}
_STOPWORDS = {
    "and",
    "are",
    "can",
    "for",
    "from",
    "into",
    "that",
    "the",
    "this",
    "when",
    "with",
}


BundleResolver = Callable[..., Dict[str, Any]]


class BenchmarkBundleCache:
    def __init__(self, resolver: BundleResolver) -> None:
        self._resolver = resolver
        self._cache: Dict[Any, Dict[str, Any]] = {}
        self.calls = 0
        self.hits = 0
        self.misses = 0

    def __call__(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        key = self._cache_key(args, kwargs)
        self.calls += 1
        if key in self._cache:
            self.hits += 1
            return copy.deepcopy(self._cache[key])
        self.misses += 1
        payload = self._resolver(*args, **kwargs)
        self._cache[key] = copy.deepcopy(payload)
        return copy.deepcopy(payload)

    def stats(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "calls": self.calls,
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self._cache),
        }

    @classmethod
    def _cache_key(cls, args: Tuple[Any, ...], kwargs: Mapping[str, Any]) -> Tuple[Any, Any]:
        return (
            tuple(cls._freeze(value) for value in args),
            tuple((str(key), cls._freeze(value)) for key, value in sorted(kwargs.items())),
        )

    @classmethod
    def _freeze(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            return tuple((str(key), cls._freeze(item)) for key, item in sorted(value.items(), key=lambda item: str(item[0])))
        if isinstance(value, (list, tuple)):
            return tuple(cls._freeze(item) for item in value)
        if isinstance(value, set):
            return tuple(sorted((cls._freeze(item) for item in value), key=repr))
        try:
            hash(value)
            return value
        except Exception:
            return repr(value)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_id(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _default_bundle_resolver(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    from astro_clock_api import _mundane_bundle_resolver

    return _mundane_bundle_resolver(*args, **kwargs)


def _domain_ids() -> set[str]:
    return {_normalize_id(row.get("id")) for row in get_domain_definitions() if _normalize_id(row.get("id"))}


def _polity_index() -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in get_polity_definitions():
        if not isinstance(row, dict):
            continue
        terms = [
            row.get("id"),
            row.get("label"),
            *(row.get("aliases") or []),
        ]
        label = str(row.get("label") or "")
        if "/" in label:
            terms.extend(part.strip() for part in label.split("/"))
        for term in terms:
            normalized = _normalize_id(term)
            if normalized:
                indexed[normalized] = row
    return indexed


def _resolve_polity(event: Mapping[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    raw_label = _normalize_text(event.get("polity"))
    if not raw_label:
        return None, None
    normalized = _normalize_id(raw_label)
    index = _polity_index()
    if normalized in index:
        return index[normalized], None
    for key, row in index.items():
        if len(key) >= 5 and (key in normalized or normalized in key):
            return row, None
    return None, raw_label


def _chart_domain_allowed(chart_type_id: str, domain_id: str) -> bool:
    try:
        policy = get_chart_type_domain_pairing_policy(chart_type_id, domain_id)
    except Exception:
        return True
    return bool(policy.get("allowed", True))


def infer_chart_type_candidates(case: Mapping[str, Any]) -> List[str]:
    domain_id = _normalize_id(case.get("domain_id"))
    basis_items = [_normalize_id(item) for item in (case.get("chart_basis") or [])]
    candidates: List[str] = []

    def add(chart_type_id: str) -> None:
        if chart_type_id not in candidates and _chart_domain_allowed(chart_type_id, domain_id):
            candidates.append(chart_type_id)

    for basis in basis_items:
        if "war_event" in basis or "hostilities" in basis or "declaration_chart" in basis:
            add("war_event")
        if "national_chart" in basis or "national_horoscope" in basis:
            add("national_chart")
        if "eclipse" in basis:
            add("eclipse")
        if "lunation" in basis or "new_moon" in basis or "full_moon" in basis:
            add("lunation")
        if "ingress" in basis:
            add("aries_ingress")
        if any(token in basis for token in ("conjunction", "mutation", "country_sign", "retrograde_condition")):
            add("aries_ingress")
        if "accession_event" in basis or basis == "event_chart":
            add("war_event")

    if domain_id == "war_outbreak":
        add("war_event")
    elif domain_id in {"war_conflict", "campaign_escalation", "military_reversal"}:
        for chart_type_id in ("war_event", "aries_ingress", "eclipse", "lunation", "national_chart"):
            add(chart_type_id)
    else:
        for chart_type_id in ("aries_ingress", "lunation", "eclipse", "national_chart", "war_event"):
            add(chart_type_id)

    return candidates


def _event_datetime(event: Mapping[str, Any]) -> str:
    date_value = _normalize_text(event.get("date") or event.get("start_date"))
    if not date_value:
        raise ValueError("event date or start_date is required")
    time_value = _normalize_text(event.get("time"))
    if not time_value:
        time_value = "00:00:00"
    elif re.fullmatch(r"\d{1,2}:\d{2}", time_value):
        time_value = f"{time_value}:00"
    return f"{date_value}T{time_value}"


def _true_event_payload(case: Mapping[str, Any]) -> Dict[str, Any]:
    event = case.get("event") or {}
    if not isinstance(event, Mapping):
        event = {}
    return {
        "type": event.get("type"),
        "date": event.get("date"),
        "time": event.get("time"),
        "start_date": event.get("start_date"),
        "end_date": event.get("end_date"),
        "location": event.get("location"),
        "polity": event.get("polity"),
        "counterpart": event.get("counterpart"),
    }


def build_analysis_request_from_case(
    case: Mapping[str, Any],
    *,
    chart_type: Optional[str] = None,
) -> Dict[str, Any]:
    event = case.get("event") or {}
    if not isinstance(event, Mapping):
        raise ValueError("case event must be an object")

    inferred_candidates = infer_chart_type_candidates(case)
    selected_chart_type = _normalize_id(chart_type) or (inferred_candidates[0] if inferred_candidates else "")
    if not selected_chart_type:
        raise ValueError("No compatible chart type could be inferred")

    domain_id = _normalize_id(case.get("domain_id"))
    event_location = _normalize_text(event.get("location"))
    polity, custom_polity_label = _resolve_polity(event)
    event_timezone = _normalize_text(event.get("timezone") or event.get("tz"))
    if not event_timezone and polity is not None:
        event_timezone = _normalize_text(polity.get("timezone"))

    request_payload: Dict[str, Any] = {
        "chart_type": selected_chart_type,
        "domain": domain_id,
        "event_datetime": _event_datetime(event),
        "event_location": event_location or None,
        "event_timezone": event_timezone or None,
        "source_preference": _normalize_text(case.get("seed_quality")) or None,
    }

    if selected_chart_type == "war_event" and event_location:
        request_payload["location_context_type"] = "event_chart"
        request_payload["reference_location"] = event_location
    elif custom_polity_label and event_location:
        request_payload["reference_location"] = event_location

    if polity is not None:
        request_payload["polity_id"] = _normalize_id(polity.get("id"))
    elif custom_polity_label:
        request_payload["custom_polity_label"] = custom_polity_label

    return {key: value for key, value in request_payload.items() if value not in (None, "")}


def _active_clock_for_request(request_payload: Mapping[str, Any]) -> ActiveClockContext:
    return ActiveClockContext(
        timestamp=str(request_payload.get("event_datetime") or ""),
        location=request_payload.get("event_location") or request_payload.get("reference_location"),
        timezone=request_payload.get("event_timezone"),
        mode="benchmark",
        house_system_code="P",
        latitude=None,
        longitude=None,
    )


def _flatten_text(value: Any) -> str:
    if isinstance(value, Mapping):
        parts: List[str] = []
        for key, item in value.items():
            parts.append(str(key))
            parts.append(_flatten_text(item))
        return " ".join(parts)
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def _tokens(value: Any) -> set[str]:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return {token for token in text.split() if len(token) > 2 and token not in _STOPWORDS}


def _match_expected_interpretations(
    expected_interpretations: Iterable[Any],
    engine_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    expected = [_normalize_text(item) for item in expected_interpretations if _normalize_text(item)]
    engine_text = _flatten_text(engine_payload)
    engine_tokens = _tokens(engine_text)
    rows: List[Dict[str, Any]] = []
    hits = 0
    for expectation in expected:
        expectation_tokens = _tokens(expectation)
        shared = sorted(expectation_tokens & engine_tokens)
        overlap = (len(shared) / len(expectation_tokens)) if expectation_tokens else 0.0
        exact = _normalize_id(expectation) in _normalize_id(engine_text)
        matched = bool(exact or overlap >= 0.34)
        if matched:
            hits += 1
        rows.append(
            {
                "expectation": expectation,
                "matched": matched,
                "token_overlap": round(overlap, 3),
                "matched_tokens": shared,
            }
        )
    hit_rate = (hits / len(expected)) if expected else 1.0
    return {
        "expected_count": len(expected),
        "matched_count": hits,
        "hit_rate": round(hit_rate, 3),
        "items": rows,
    }


def _summarize_engine_output(analysis_payload: Mapping[str, Any]) -> Dict[str, Any]:
    assessment = analysis_payload.get("domain_assessment") or {}
    context = analysis_payload.get("context") or {}
    chart_resolution = context.get("chart_resolution") or {}
    primary_chart = chart_resolution.get("primary_chart") or {}
    matched_rules = assessment.get("matched_rules") or []
    return {
        "domain_id": assessment.get("domain_id"),
        "score": int(assessment.get("score") or 0),
        "raw_score": int(assessment.get("raw_score") or 0),
        "level": assessment.get("level"),
        "raw_level": assessment.get("raw_level"),
        "summary": assessment.get("summary"),
        "matched_rules": matched_rules,
        "matched_rule_ids": [
            row.get("id") or row.get("rule_id")
            for row in matched_rules
            if isinstance(row, Mapping) and (row.get("id") or row.get("rule_id"))
        ],
        "matched_rule_labels": [
            row.get("label")
            for row in matched_rules
            if isinstance(row, Mapping) and row.get("label")
        ],
        "cautions": list(assessment.get("cautions") or []),
        "research_flags": list(assessment.get("research_flags") or []),
        "calibration": dict(assessment.get("calibration") or {}),
        "primary_chart": {
            "kind": primary_chart.get("kind"),
            "computed_datetime": primary_chart.get("computed_datetime"),
            "location": primary_chart.get("location"),
            "timezone": primary_chart.get("timezone"),
            "angles": primary_chart.get("angles"),
        },
        "signal_keys": sorted((chart_resolution.get("signals") or {}).keys()),
        "trigger_profiles": [
            {
                "id": row.get("id"),
                "status": row.get("status"),
                "active": bool(row.get("active")),
                "score": int(row.get("score") or 0),
            }
            for row in (analysis_payload.get("trigger_profiles") or [])
            if isinstance(row, Mapping)
        ],
    }


def _execute_case(
    case: Mapping[str, Any],
    *,
    bundle_resolver: BundleResolver,
    minimum_score: int,
    minimum_expectation_hit_rate: float,
) -> Dict[str, Any]:
    case_id = _normalize_text(case.get("case_id"))
    domain_id = _normalize_id(case.get("domain_id"))
    expected_domain = _normalize_id(case.get("expected_domain_lead") or domain_id)
    base_row: Dict[str, Any] = {
        "case_id": case_id,
        "label": case.get("label"),
        "dataset": case.get("_dataset_path"),
        "domain_id": domain_id,
        "expected_domain_lead": expected_domain,
        "benchmark_type": case.get("benchmark_type"),
        "seed_quality": case.get("seed_quality"),
        "chart_basis": list(case.get("chart_basis") or []),
        "true_event": _true_event_payload(case),
        "expected_interpretations": list(case.get("expected_interpretations") or []),
        "chart_type_attempts": [],
    }

    if domain_id not in _domain_ids() or domain_id not in SUPPORTED_ENGINE_DOMAINS:
        return {
            **base_row,
            "status": "skipped",
            "skip_reason": "unsupported_domain",
            "chart_type_candidates": [],
        }

    candidates = infer_chart_type_candidates(case)
    if not candidates:
        return {
            **base_row,
            "status": "failed",
            "error": "No compatible chart type could be inferred",
            "chart_type_candidates": [],
        }
    base_row["chart_type_candidates"] = candidates

    last_error = ""
    attempts: List[Dict[str, Any]] = []
    for chart_type in candidates:
        try:
            request_payload = build_analysis_request_from_case(case, chart_type=chart_type)
            request_model = build_context_request(request_payload, require_domain=True)
            active_clock = _active_clock_for_request(request_payload)
            context = resolve_context(
                request_model,
                active_clock=active_clock,
                bundle_resolver=bundle_resolver,
            )
            analysis = analyze_context(context)
            analysis_payload = analysis.to_dict()
        except Exception as exc:
            last_error = str(exc)
            attempts.append({"chart_type": chart_type, "status": "error", "error": last_error})
            continue

        attempts.append({"chart_type": chart_type, "status": "executed"})
        engine_output = _summarize_engine_output(analysis_payload)
        expectation_match = _match_expected_interpretations(
            case.get("expected_interpretations") or [],
            {"engine_output": engine_output, "analysis": analysis_payload},
        )
        actual_domain = _normalize_id(engine_output.get("domain_id"))
        score = int(engine_output.get("score") or 0)
        domain_match = actual_domain == expected_domain
        score_pass = score >= minimum_score
        expectation_pass = float(expectation_match.get("hit_rate") or 0.0) >= minimum_expectation_hit_rate
        status = "pass" if domain_match and score_pass and expectation_pass else "partial"
        return {
            **base_row,
            "status": status,
            "selected_chart_type": chart_type,
            "request": request_payload,
            "chart_type_attempts": attempts,
            "checks": {
                "domain_match": domain_match,
                "expected_domain": expected_domain,
                "actual_domain": actual_domain,
                "score_pass": score_pass,
                "minimum_score": minimum_score,
                "expectation_hit_rate_pass": expectation_pass,
                "minimum_expectation_hit_rate": minimum_expectation_hit_rate,
                "expectation_hit_rate": expectation_match.get("hit_rate"),
            },
            "expectation_match": expectation_match,
            "engine_output": engine_output,
        }

    return {
        **base_row,
        "status": "failed",
        "error": last_error or "All chart type attempts failed",
        "chart_type_attempts": attempts,
    }


def load_analysis_benchmark_cases(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
    domain_id: Optional[str] = None,
    include_disabled: bool = False,
    include_duplicate_cases: bool = False,
    max_cases: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cases: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    seen_case_ids: Dict[str, str] = {}
    case_filter = _normalize_text(case_id).lower()
    domain_filter = _normalize_id(domain_id)

    for raw_path in dataset_paths or DEFAULT_DATASET_PATHS:
        path = Path(raw_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Benchmark dataset not found: {path}")
        for payload in load_jsonl_cases(path):
            current_case_id = _normalize_text(payload.get("case_id"))
            if case_filter and current_case_id.lower() != case_filter:
                continue
            if domain_filter and _normalize_id(payload.get("domain_id")) != domain_filter:
                continue
            validate_historical_case(payload, path)
            if not include_disabled and not bool(payload.get("enabled")):
                skipped.append({"dataset": str(path), "case_id": current_case_id, "reason": "disabled"})
                continue
            dedupe_key = current_case_id.lower()
            if dedupe_key and not include_duplicate_cases and dedupe_key in seen_case_ids:
                skipped.append(
                    {
                        "dataset": str(path),
                        "case_id": current_case_id,
                        "reason": "duplicate_case_id",
                        "duplicate_of_dataset": seen_case_ids[dedupe_key],
                    }
                )
                continue
            case = dict(payload)
            case["_dataset_path"] = str(path)
            cases.append(case)
            if dedupe_key:
                seen_case_ids[dedupe_key] = str(path)
            if max_cases is not None and len(cases) >= max_cases:
                return cases, skipped

    return cases, skipped


def run_mundane_analysis_benchmark_suite(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
    domain_id: Optional[str] = None,
    include_disabled: bool = False,
    include_duplicate_cases: bool = False,
    max_cases: Optional[int] = None,
    minimum_score: int = 25,
    minimum_expectation_hit_rate: float = 0.0,
    bundle_resolver: Optional[BundleResolver] = None,
    use_bundle_cache: bool = True,
) -> Dict[str, Any]:
    cases, skipped = load_analysis_benchmark_cases(
        dataset_paths,
        case_id=case_id,
        domain_id=domain_id,
        include_disabled=include_disabled,
        include_duplicate_cases=include_duplicate_cases,
        max_cases=max_cases,
    )
    raw_resolver = bundle_resolver or _default_bundle_resolver
    cached_resolver = BenchmarkBundleCache(raw_resolver) if use_bundle_cache else None
    resolver = cached_resolver or raw_resolver
    results = [
        _execute_case(
            case,
            bundle_resolver=resolver,
            minimum_score=minimum_score,
            minimum_expectation_hit_rate=minimum_expectation_hit_rate,
        )
        for case in cases
    ]

    status_counts: Counter[str] = Counter(str(row.get("status") or "unknown") for row in results)
    domain_counts: Counter[str] = Counter(str(row.get("domain_id") or "unknown") for row in results)
    chart_type_counts: Counter[str] = Counter(
        str(row.get("selected_chart_type") or "none")
        for row in results
        if row.get("status") not in {"skipped", "failed"}
    )
    executed_scores = [
        int((row.get("engine_output") or {}).get("score") or 0)
        for row in results
        if isinstance(row.get("engine_output"), Mapping)
    ]
    skipped_input_counts: Counter[str] = Counter(str(row.get("reason") or "unknown") for row in skipped)
    bundle_cache_stats = cached_resolver.stats() if cached_resolver is not None else {"enabled": False}

    return {
        "runtime_scope": "computed_mundane_analysis_benchmark",
        "dataset_paths": [str(Path(path).resolve()) for path in (dataset_paths or DEFAULT_DATASET_PATHS)],
        "dedupe_case_ids": not include_duplicate_cases,
        "case_count": len(results),
        "executed_count": len(executed_scores),
        "pass_count": status_counts.get("pass", 0),
        "partial_count": status_counts.get("partial", 0),
        "failed_count": status_counts.get("failed", 0),
        "skipped_count": status_counts.get("skipped", 0),
        "input_skipped_count": len(skipped),
        "duplicate_input_count": skipped_input_counts.get("duplicate_case_id", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "input_skipped_counts": dict(sorted(skipped_input_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "chart_type_counts": dict(sorted(chart_type_counts.items())),
        "bundle_cache": bundle_cache_stats,
        "score_summary": {
            "min": min(executed_scores) if executed_scores else None,
            "max": max(executed_scores) if executed_scores else None,
            "average": round(sum(executed_scores) / len(executed_scores), 2) if executed_scores else None,
        },
        "thresholds": {
            "minimum_score": minimum_score,
            "minimum_expectation_hit_rate": minimum_expectation_hit_rate,
        },
        "skipped_inputs": skipped,
        "results": results,
    }


def _table_cell(value: Any, *, limit: int = 90) -> str:
    text = _normalize_text(value)
    text = text.replace("|", "\\|")
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def _event_label(event: Mapping[str, Any]) -> str:
    date_value = event.get("date") or event.get("start_date") or ""
    if event.get("end_date") and event.get("end_date") != date_value:
        date_value = f"{date_value} to {event.get('end_date')}"
    location = _normalize_text(event.get("location"))
    return _normalize_text(f"{date_value} {location}")


def render_markdown_report(report: Mapping[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Mundo / Mundane Analysis Benchmark")
    lines.append("")
    lines.append(f"- Cases: {int(report.get('case_count') or 0)}")
    lines.append(f"- Executed: {int(report.get('executed_count') or 0)}")
    lines.append(f"- Pass: {int(report.get('pass_count') or 0)}")
    lines.append(f"- Partial: {int(report.get('partial_count') or 0)}")
    lines.append(f"- Failed: {int(report.get('failed_count') or 0)}")
    lines.append(f"- Skipped: {int(report.get('skipped_count') or 0)}")
    lines.append(f"- Skipped input rows: {int(report.get('input_skipped_count') or 0)}")
    if report.get("duplicate_input_count"):
        lines.append(f"- Duplicate input rows deduped: {int(report.get('duplicate_input_count') or 0)}")
    cache_stats = report.get("bundle_cache") or {}
    if cache_stats.get("enabled"):
        lines.append(
            f"- Bundle cache: {int(cache_stats.get('hits') or 0)} hits, "
            f"{int(cache_stats.get('misses') or 0)} misses"
        )
    score_summary = report.get("score_summary") or {}
    if score_summary.get("average") is not None:
        lines.append(
            f"- Score range: {score_summary.get('min')} to {score_summary.get('max')} "
            f"(avg {score_summary.get('average')})"
        )
    lines.append("")
    lines.append("## Datasets")
    lines.append("")
    for dataset_path in report.get("dataset_paths") or []:
        lines.append(f"- `{dataset_path}`")

    lines.append("")
    lines.append("## True Event vs Engine Output")
    lines.append("")
    lines.append("| Status | Case | Domain | Chart | True event | Engine score | Top engine rules |")
    lines.append("|---|---|---|---|---|---:|---|")
    for row in report.get("results") or []:
        engine = row.get("engine_output") or {}
        rules = ", ".join(str(item) for item in (engine.get("matched_rule_labels") or [])[:3])
        score = engine.get("score")
        level = engine.get("level") or ""
        score_cell = "" if score is None else f"{score} {level}".strip()
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("status"), limit=20),
                    _table_cell(f"{row.get('label') or row.get('case_id')} (`{row.get('case_id')}`)", limit=72),
                    _table_cell(row.get("domain_id"), limit=36),
                    _table_cell(row.get("selected_chart_type") or ",".join(row.get("chart_type_candidates") or []), limit=40),
                    _table_cell(_event_label(row.get("true_event") or {}), limit=72),
                    _table_cell(score_cell, limit=24),
                    _table_cell(rules or row.get("error") or row.get("skip_reason"), limit=90),
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append("## Details")
    lines.append("")
    for row in report.get("results") or []:
        lines.append(f"### {row.get('case_id')}")
        lines.append("")
        lines.append(f"- Label: {_normalize_text(row.get('label'))}")
        lines.append(f"- Status: `{row.get('status')}`")
        lines.append(f"- Expected domain: `{row.get('expected_domain_lead')}`")
        lines.append(f"- Chart basis: {', '.join(f'`{item}`' for item in row.get('chart_basis') or [])}")
        if row.get("selected_chart_type"):
            lines.append(f"- Selected chart type: `{row.get('selected_chart_type')}`")
        if row.get("request"):
            request = row.get("request") or {}
            lines.append(f"- Request event datetime: `{request.get('event_datetime')}`")
            lines.append(f"- Request event location: {_normalize_text(request.get('event_location')) or 'none'}")
            lines.append(f"- Request event timezone: {_normalize_text(request.get('event_timezone')) or 'none'}")
        engine = row.get("engine_output") or {}
        if engine:
            lines.append(f"- Engine score: `{engine.get('score')}` (`{engine.get('level')}`)")
            lines.append(f"- Engine summary: {_normalize_text(engine.get('summary'))}")
            if engine.get("matched_rule_labels"):
                lines.append(
                    "- Matched rules: "
                    + ", ".join(f"`{_normalize_text(item)}`" for item in engine.get("matched_rule_labels") or [])
                )
        if row.get("expectation_match"):
            match = row.get("expectation_match") or {}
            lines.append(
                f"- Expected interpretation hit rate: `{match.get('matched_count')}/{match.get('expected_count')}` "
                f"({match.get('hit_rate')})"
            )
        if row.get("error"):
            lines.append(f"- Error: {_normalize_text(row.get('error'))}")
        if row.get("skip_reason"):
            lines.append(f"- Skip reason: {_normalize_text(row.get('skip_reason'))}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run historical Mundo/Mundane event cases through the analysis engine."
    )
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        help="Path to a historical mundane benchmark JSONL dataset. Repeat for multiple datasets.",
    )
    parser.add_argument("--case-id", help="Run only one case_id from the dataset set.")
    parser.add_argument("--domain", dest="domain_id", help="Run only cases for one domain_id.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled cases.")
    parser.add_argument(
        "--include-duplicate-cases",
        action="store_true",
        help="Run duplicate case_id rows from overlapping historical and per-domain datasets.",
    )
    parser.add_argument("--max-cases", type=int, help="Limit how many matching cases execute.")
    parser.add_argument("--minimum-score", type=int, default=25, help="Minimum calibrated engine score for pass.")
    parser.add_argument(
        "--minimum-expectation-hit-rate",
        type=float,
        default=0.0,
        help="Minimum expected-interpretation token hit rate for pass.",
    )
    parser.add_argument("--no-bundle-cache", action="store_true", help="Disable in-run chart bundle memoization.")
    parser.add_argument("--fail-on-regression", action="store_true", help="Exit non-zero on partial or failed rows.")
    parser.add_argument("--output-json", help="Optional path to write the full report as JSON.")
    parser.add_argument("--output-md", help="Optional path to write the markdown report.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    dataset_paths = args.dataset or DEFAULT_DATASET_PATHS
    report = run_mundane_analysis_benchmark_suite(
        dataset_paths,
        case_id=args.case_id,
        domain_id=args.domain_id,
        include_disabled=args.include_disabled,
        include_duplicate_cases=args.include_duplicate_cases,
        max_cases=args.max_cases,
        minimum_score=args.minimum_score,
        minimum_expectation_hit_rate=args.minimum_expectation_hit_rate,
        use_bundle_cache=not args.no_bundle_cache,
    )
    markdown = render_markdown_report(report)
    print(markdown, end="")

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(markdown, encoding="utf-8")

    if args.fail_on_regression and (report.get("partial_count") or report.get("failed_count")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
