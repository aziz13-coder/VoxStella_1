from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from benchmarks.astrocartography.baselines import compute_case_baselines


DEFAULT_BENCHMARK_DIR = Path(__file__).resolve().parent / "benchmarks" / "astrocartography"
DEFAULT_SPECULATION_DATASET = DEFAULT_BENCHMARK_DIR / "speculation_cases.jsonl"
DEFAULT_HEALTH_RISK_DATASET = DEFAULT_BENCHMARK_DIR / "health_risk_cases.jsonl"
SUPPORTED_MODES = {"natal_only", "event_transit_overlay"}


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


def load_benchmark_cases(
    dataset_paths: Sequence[str | Path],
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cases: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()

    for raw_path in dataset_paths:
        path = Path(raw_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Benchmark dataset not found: {path}")
        for line_number, payload in _read_jsonl(path):
            current_case_id = _normalize_text(payload.get("case_id"))
            if case_filter and current_case_id.lower() != case_filter:
                continue
            if not include_disabled and not bool(payload.get("enabled")):
                skipped.append(
                    {
                        "dataset": str(path),
                        "line_number": line_number,
                        "case_id": current_case_id or f"line-{line_number}",
                        "reason": "disabled",
                    }
                )
                continue
            payload = dict(payload)
            payload["_dataset_path"] = str(path)
            payload["_line_number"] = line_number
            cases.append(payload)
    return cases, skipped


def _location_label(raw: Any) -> str:
    if isinstance(raw, str):
        return _normalize_text(raw)
    if isinstance(raw, dict):
        for key in ("label", "query", "name", "display_name", "place"):
            label = _normalize_text(raw.get(key))
            if label:
                return label
    return ""


def _resolve_city_payload(raw: Any, *, allow_live_geocode: bool = False) -> Dict[str, Any]:
    from astrocartography_city_catalog import search_city_catalog
    from horary_engine.services.geolocation import search_live_location_candidates

    if isinstance(raw, dict):
        label = _location_label(raw)
        lat = raw.get("latitude")
        lon = raw.get("longitude")
        if label and lat is not None and lon is not None:
            return {
                "label": label,
                "query": label,
                "latitude": round(float(lat), 6),
                "longitude": round(float(lon), 6),
                "timezone": _normalize_text(raw.get("timezone")),
                "country_code": _normalize_text(raw.get("country_code")).upper(),
                "country_name": _normalize_text(raw.get("country_name")),
                "admin1_code": _normalize_text(raw.get("admin1_code")),
                "population": int(raw.get("population") or 0),
                "feature_code": _normalize_text(raw.get("feature_code")) or "MANUAL",
                "resolution_source": "explicit_coordinates",
            }

    label = _location_label(raw)
    if not label:
        raise ValueError(f"Location label is required: {raw!r}")

    catalog_candidates = search_city_catalog(query=label, limit=6, resolution="ultra")
    if catalog_candidates:
        best = dict(catalog_candidates[0])
        best["resolution_source"] = "catalog"
        return best

    if allow_live_geocode:
        live_candidates = search_live_location_candidates(label, limit=6)
        if live_candidates:
            best = dict(live_candidates[0])
            best["resolution_source"] = "offline_catalog_candidate"
            return best

    raise ValueError(f"Could not resolve benchmark location: {label}")


def _require_block(case: Dict[str, Any], key: str) -> Dict[str, Any]:
    block = case.get(key)
    if not isinstance(block, dict):
        raise ValueError(f"Case {case.get('case_id')}: missing {key} block")
    return block


def _build_birth_datetime_iso(birth: Dict[str, Any]) -> str:
    birth_date = _normalize_text(birth.get("date"))
    birth_time = _normalize_text(birth.get("time"))
    if not birth_date or not birth_time:
        raise ValueError("Birth date and birth time are required")
    return f"{birth_date}T{birth_time}:00"


def _build_event_datetime_iso(event: Dict[str, Any]) -> str:
    event_date = _normalize_text(event.get("date"))
    event_time = _normalize_text(event.get("time")) or "12:00"
    if not event_date:
        raise ValueError("Event date is required")
    return f"{event_date}T{event_time}:00"


def _build_case_transit_context(
    case: Dict[str, Any],
    *,
    natal_meta: Dict[str, Any],
    event_city: Dict[str, Any],
) -> Tuple[str, Optional[str], Optional[str]]:
    event = _require_block(case, "event")
    transit_context = case.get("transit_context")
    if transit_context is not None and not isinstance(transit_context, dict):
        raise ValueError("transit_context must be an object when provided")
    transit_context = transit_context or {}
    location_strategy = _normalize_text(transit_context.get("location_strategy")).lower() or "natal"
    dt_iso = _build_event_datetime_iso(event)

    if location_strategy == "event":
        return dt_iso, str(event_city.get("label") or event_city.get("query") or ""), _normalize_text(event_city.get("timezone"))
    if location_strategy == "explicit":
        explicit_location = _normalize_text(transit_context.get("location") or transit_context.get("label"))
        if not explicit_location:
            raise ValueError("transit_context.location is required for explicit strategy")
        return dt_iso, explicit_location, _normalize_text(transit_context.get("timezone"))
    if location_strategy != "natal":
        raise ValueError(f"Unsupported transit_context.location_strategy: {location_strategy}")

    return (
        dt_iso,
        _normalize_text(transit_context.get("location")) or _normalize_text(natal_meta.get("location")),
        _normalize_text(transit_context.get("timezone")) or _normalize_text(natal_meta.get("timezone")),
    )


def _build_case_context(case: Dict[str, Any], *, mode: str, allow_live_geocode: bool = False) -> Dict[str, Any]:
    from astro_clock_api import _compute_chart_bundle_for
    from astrocartography_service import build_astrocartography_lines
    from astrocartography_goal_models import get_goal_model

    goal_id = _normalize_text(case.get("goal_id")).lower()
    if not goal_id:
        raise ValueError("goal_id is required")
    get_goal_model(goal_id)

    birth = _require_block(case, "birth")
    birth_place = _normalize_text(birth.get("place"))
    if not birth_place:
        raise ValueError("Birth place is required")
    birth_timezone = _normalize_text(birth.get("timezone")) or None
    natal_bundle = _compute_chart_bundle_for(_build_birth_datetime_iso(birth), birth_place, birth_timezone)
    natal_meta = natal_bundle.get("meta") or {}
    natal_timestamp = _normalize_text(natal_meta.get("timestamp"))
    if not natal_timestamp:
        raise ValueError("Failed to compute natal timestamp")

    natal_lines_payload = build_astrocartography_lines(natal_timestamp)
    context: Dict[str, Any] = {
        "goal_id": goal_id,
        "natal_bundle": natal_bundle,
        "natal_meta": natal_meta,
        "natal_lines": natal_lines_payload.get("lines") or [],
        "transit_meta": None,
        "transit_lines": None,
    }
    if mode == "natal_only":
        return context

    event = _require_block(case, "event")
    event_city = _resolve_city_payload(event.get("location"), allow_live_geocode=allow_live_geocode)
    dt_iso, transit_location, transit_timezone = _build_case_transit_context(case, natal_meta=natal_meta, event_city=event_city)
    transit_bundle = _compute_chart_bundle_for(dt_iso, transit_location, transit_timezone or None)
    transit_meta = transit_bundle.get("meta") or {}
    transit_timestamp = _normalize_text(transit_meta.get("timestamp"))
    if not transit_timestamp:
        raise ValueError("Failed to compute transit timestamp")
    transit_lines_payload = build_astrocartography_lines(transit_timestamp)
    context["transit_meta"] = transit_meta
    context["transit_lines"] = transit_lines_payload.get("lines") or []
    context["event_city_for_transit"] = event_city
    return context


def _score_city_for_case(
    city: Dict[str, Any],
    *,
    goal_id: str,
    natal_timestamp: str,
    natal_lines: Sequence[Dict[str, Any]],
    transit_lines: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    from astro_clock_api import _compute_chart_bundle_for
    from astrocartography_atlas_engine import _score_candidate
    from astrocartography_goal_engine import extract_relocation_features

    relocation_bundle = _compute_chart_bundle_for(str(natal_timestamp), str(city.get("label") or city.get("query") or ""), None)
    relocation_features = extract_relocation_features(relocation_bundle.get("chart_data") or {})
    scored = _score_candidate(
        city,
        goal_id=goal_id,
        natal_lines=natal_lines,
        transit_lines=transit_lines,
        relocation_features=relocation_features,
    )
    baselines = compute_case_baselines(
        goal_id,
        natal_rows=((scored.get("natal") or {}).get("reading") or {}).get("nearest_lines") or [],
        natal_crossings=((scored.get("natal") or {}).get("crossings") or []),
        relocation=relocation_features,
        transit_rows=(((scored.get("transit") or {}).get("reading") or {}).get("nearest_lines") or []),
        transit_crossings=((scored.get("transit") or {}).get("crossings") or []),
    )
    models = {
        "product_model": {
            "id": goal_id,
            "label": "Product Model",
            "raw_score": float(((scored.get("location_score") or {}).get("raw_score")) or 0.0),
            "score": int(((scored.get("location_score") or {}).get("score")) or 0),
            "summary": str(((scored.get("location_score") or {}).get("headline")) or ""),
        },
        **baselines,
    }
    return {
        "city": {
            "label": str(city.get("label") or city.get("query") or ""),
            "query": str(city.get("query") or city.get("label") or ""),
            "latitude": float(city.get("latitude") or 0.0),
            "longitude": float(city.get("longitude") or 0.0),
            "timezone": str(city.get("timezone") or ""),
            "country_code": str(city.get("country_code") or ""),
            "country_name": str(city.get("country_name") or ""),
            "resolution_source": str(city.get("resolution_source") or ""),
        },
        "product": scored,
        "models": models,
    }


def _comparator_rank_value(item: Dict[str, Any], comparator_id: str) -> float:
    payload = ((item.get("models") or {}).get(comparator_id) or {})
    if payload.get("raw_score") is not None:
        return float(payload.get("raw_score") or 0.0)
    return float(payload.get("score") or 0.0)


def rank_case_scores(scored_candidates: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    comparator_ids = sorted(
        {
            comparator_id
            for item in scored_candidates
            for comparator_id in (item.get("models") or {}).keys()
        }
    )
    results: Dict[str, Dict[str, Any]] = {}

    for comparator_id in comparator_ids:
        eligible = [item for item in scored_candidates if comparator_id in (item.get("models") or {})]
        if not eligible:
            continue
        ranked = sorted(
            eligible,
            key=lambda item: (
                -_comparator_rank_value(item, comparator_id),
                str(((item.get("city") or {}).get("label")) or ""),
            ),
        )
        event_idx = next((idx for idx, item in enumerate(ranked) if item.get("role") == "event"), None)
        if event_idx is None:
            continue
        event_item = ranked[event_idx]
        event_score = _comparator_rank_value(event_item, comparator_id)
        pairwise_total = 0
        pairwise_wins = 0
        pairwise_ties = 0
        control_scores: List[float] = []
        for item in ranked:
            if item.get("role") != "control":
                continue
            pairwise_total += 1
            control_score = _comparator_rank_value(item, comparator_id)
            control_scores.append(control_score)
            if event_score > control_score:
                pairwise_wins += 1
            elif event_score == control_score:
                pairwise_ties += 1
        pairwise_credit = pairwise_wins + (0.5 * pairwise_ties)
        results[comparator_id] = {
            "id": comparator_id,
            "label": str(((event_item.get("models") or {}).get(comparator_id) or {}).get("label") or comparator_id),
            "event_rank": event_idx + 1,
            "event_score": round(event_score, 4),
            "event_display_score": int((((event_item.get("models") or {}).get(comparator_id) or {}).get("score")) or 0),
            "best_control_score": max(control_scores) if control_scores else None,
            "pairwise_wins": pairwise_wins,
            "pairwise_ties": pairwise_ties,
            "pairwise_total": pairwise_total,
            "pairwise_win_rate": round((pairwise_credit / pairwise_total), 4) if pairwise_total else None,
            "top_3_hit": bool((event_idx + 1) <= 3),
            "reciprocal_rank": round(1.0 / float(event_idx + 1), 6),
            "ranking": [
                {
                    "role": item.get("role"),
                    "label": str((item.get("city") or {}).get("label") or ""),
                    "score": round(_comparator_rank_value(item, comparator_id), 4),
                    "display_score": int((((item.get("models") or {}).get(comparator_id) or {}).get("score")) or 0),
                }
                for item in ranked
            ],
        }
    return results


def _summarize_case_group(case_results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    comparator_ids = sorted(
        {
            comparator_id
            for case in case_results
            for comparator_id in (case.get("comparators") or {}).keys()
        }
    )
    comparators: Dict[str, Dict[str, Any]] = {}
    for comparator_id in comparator_ids:
        entries = [case["comparators"][comparator_id] for case in case_results if comparator_id in (case.get("comparators") or {})]
        if not entries:
            continue
        pairwise_total = sum(int(entry.get("pairwise_total") or 0) for entry in entries)
        pairwise_credit = sum(
            float(entry.get("pairwise_wins") or 0) + (0.5 * float(entry.get("pairwise_ties") or 0))
            for entry in entries
        )
        top_3_hits = sum(1 for entry in entries if entry.get("top_3_hit"))
        reciprocal_rank_total = sum(float(entry.get("reciprocal_rank") or 0.0) for entry in entries)
        mean_rank = sum(float(entry.get("event_rank") or 0.0) for entry in entries) / float(len(entries))
        comparators[comparator_id] = {
            "label": str(entries[0].get("label") or comparator_id),
            "case_count": len(entries),
            "pairwise_total": pairwise_total,
            "pairwise_win_rate": round(pairwise_credit / pairwise_total, 4) if pairwise_total else None,
            "top_3_hit_rate": round(top_3_hits / float(len(entries)), 4),
            "mean_reciprocal_rank": round(reciprocal_rank_total / float(len(entries)), 4),
            "mean_event_rank": round(mean_rank, 4),
        }
    product_pairwise = comparators.get("product_model", {}).get("pairwise_win_rate")
    for comparator_id, summary in comparators.items():
        if comparator_id == "product_model" or product_pairwise is None or summary.get("pairwise_win_rate") is None:
            continue
        summary["pairwise_lift_vs_product"] = round(product_pairwise - float(summary["pairwise_win_rate"]), 4)
    return comparators


def summarize_benchmark_results(case_results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    overall = _summarize_case_group(case_results)
    by_goal: Dict[str, Dict[str, Any]] = {}
    goal_ids = sorted({str(case.get("goal_id") or "") for case in case_results if str(case.get("goal_id") or "")})
    for goal_id in goal_ids:
        scoped = [case for case in case_results if str(case.get("goal_id") or "") == goal_id]
        by_goal[goal_id] = _summarize_case_group(scoped)
    return {
        "overall": overall,
        "by_goal": by_goal,
    }


def _render_markdown_report(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Astrocartography Benchmark Summary")
    lines.append("")
    lines.append(f"- Mode: `{result.get('mode')}`")
    lines.append(f"- Dataset count: `{len(result.get('datasets') or [])}`")
    lines.append(f"- Enabled cases: `{len(result.get('case_results') or [])}`")
    lines.append(f"- Skipped rows: `{len(result.get('skipped') or [])}`")
    lines.append(f"- Failed cases: `{len(result.get('failures') or [])}`")
    lines.append("")

    overall = (result.get("summary") or {}).get("overall") or {}
    if overall:
        lines.append("## Overall")
        lines.append("")
        lines.append("| Comparator | Cases | Pairwise | Top-3 | MRR | Mean Rank |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for comparator_id, payload in overall.items():
            lines.append(
                f"| {payload.get('label') or comparator_id} | {payload.get('case_count') or 0} | "
                f"{payload.get('pairwise_win_rate') if payload.get('pairwise_win_rate') is not None else 'n/a'} | "
                f"{payload.get('top_3_hit_rate') if payload.get('top_3_hit_rate') is not None else 'n/a'} | "
                f"{payload.get('mean_reciprocal_rank') if payload.get('mean_reciprocal_rank') is not None else 'n/a'} | "
                f"{payload.get('mean_event_rank') if payload.get('mean_event_rank') is not None else 'n/a'} |"
            )
        lines.append("")

    by_goal = (result.get("summary") or {}).get("by_goal") or {}
    for goal_id, comparators in by_goal.items():
        lines.append(f"## Goal: `{goal_id}`")
        lines.append("")
        lines.append("| Comparator | Cases | Pairwise | Top-3 | MRR | Mean Rank |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for comparator_id, payload in comparators.items():
            lines.append(
                f"| {payload.get('label') or comparator_id} | {payload.get('case_count') or 0} | "
                f"{payload.get('pairwise_win_rate') if payload.get('pairwise_win_rate') is not None else 'n/a'} | "
                f"{payload.get('top_3_hit_rate') if payload.get('top_3_hit_rate') is not None else 'n/a'} | "
                f"{payload.get('mean_reciprocal_rank') if payload.get('mean_reciprocal_rank') is not None else 'n/a'} | "
                f"{payload.get('mean_event_rank') if payload.get('mean_event_rank') is not None else 'n/a'} |"
            )
        lines.append("")

    if result.get("failures"):
        lines.append("## Failed Cases")
        lines.append("")
        for failure in result["failures"]:
            lines.append(f"- `{failure.get('case_id')}`: {failure.get('error')}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def run_benchmark(
    dataset_paths: Sequence[str | Path],
    *,
    mode: str,
    case_id: Optional[str] = None,
    allow_live_geocode: bool = False,
    include_disabled: bool = False,
) -> Dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode: {mode}")

    cases, skipped = load_benchmark_cases(dataset_paths, case_id=case_id, include_disabled=include_disabled)
    case_results: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    for case in cases:
        current_case_id = _normalize_text(case.get("case_id")) or f"line-{case.get('_line_number')}"
        try:
            context = _build_case_context(case, mode=mode, allow_live_geocode=allow_live_geocode)
            natal_timestamp = _normalize_text((context.get("natal_meta") or {}).get("timestamp"))
            if not natal_timestamp:
                raise ValueError("Missing natal timestamp")

            event_block = _require_block(case, "event")
            control_blocks = case.get("controls") or []
            if not isinstance(control_blocks, list) or not control_blocks:
                raise ValueError("At least one control location is required")

            scored_candidates: List[Dict[str, Any]] = []
            event_city = dict(context.get("event_city_for_transit") or {})
            if not event_city:
                event_city = _resolve_city_payload(event_block.get("location"), allow_live_geocode=allow_live_geocode)
            event_scored = _score_city_for_case(
                event_city,
                goal_id=str(context["goal_id"]),
                natal_timestamp=natal_timestamp,
                natal_lines=context["natal_lines"],
                transit_lines=context.get("transit_lines"),
            )
            event_scored["role"] = "event"
            scored_candidates.append(event_scored)

            for raw_control in control_blocks:
                resolved_control = _resolve_city_payload(raw_control, allow_live_geocode=allow_live_geocode)
                control_scored = _score_city_for_case(
                    resolved_control,
                    goal_id=str(context["goal_id"]),
                    natal_timestamp=natal_timestamp,
                    natal_lines=context["natal_lines"],
                    transit_lines=context.get("transit_lines"),
                )
                control_scored["role"] = "control"
                control_scored["reason"] = raw_control.get("reason") if isinstance(raw_control, dict) else ""
                scored_candidates.append(control_scored)

            comparators = rank_case_scores(scored_candidates)
            case_results.append(
                {
                    "case_id": current_case_id,
                    "goal_id": str(context["goal_id"]),
                    "dataset": str(case.get("_dataset_path") or ""),
                    "line_number": int(case.get("_line_number") or 0),
                    "person_name": _normalize_text(case.get("person_name")),
                    "mode": mode,
                    "comparators": comparators,
                    "candidates": scored_candidates,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "case_id": current_case_id,
                    "dataset": str(case.get("_dataset_path") or ""),
                    "line_number": int(case.get("_line_number") or 0),
                    "error": str(exc),
                }
            )

    result = {
        "mode": mode,
        "datasets": [str(Path(path).resolve()) for path in dataset_paths],
        "skipped": skipped,
        "failures": failures,
        "case_results": case_results,
        "summary": summarize_benchmark_results(case_results),
    }
    result["markdown"] = _render_markdown_report(result)
    return result


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run astrocartography benchmark cases against the current PathFinder scoring logic.")
    parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        help="Path to a JSONL benchmark dataset. Can be provided multiple times.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(SUPPORTED_MODES),
        default="natal_only",
        help="Benchmark mode to run.",
    )
    parser.add_argument("--case-id", help="Run a single case_id only.")
    parser.add_argument("--allow-live-geocode", action="store_true", help="Use expanded bundled catalog lookup when a city is missing from the primary shipped catalog match.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled template rows.")
    parser.add_argument("--output-json", help="Write the full benchmark result to a JSON file.")
    parser.add_argument("--output-md", help="Write the Markdown summary to a file.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    datasets = args.datasets or [str(DEFAULT_SPECULATION_DATASET)]
    result = run_benchmark(
        datasets,
        mode=args.mode,
        case_id=args.case_id,
        allow_live_geocode=bool(args.allow_live_geocode),
        include_disabled=bool(args.include_disabled),
    )

    if args.output_json:
        output_json_path = Path(args.output_json).resolve()
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    if args.output_md:
        output_md_path = Path(args.output_md).resolve()
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.write_text(result["markdown"], encoding="utf-8")

    print(result["markdown"])
    return 0 if not result.get("failures") else 1


if __name__ == "__main__":
    raise SystemExit(main())
