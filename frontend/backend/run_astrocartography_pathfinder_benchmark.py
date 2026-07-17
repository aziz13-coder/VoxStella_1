from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from astro_clock_api import _compute_chart_bundle_for
from astrocartography_atlas_engine import rank_candidate_pool_for_goal
from astrocartography_city_catalog import get_atlas_resolution_settings
from run_astrocartography_benchmark import (
    DEFAULT_SPECULATION_DATASET,
    SUPPORTED_MODES,
    _build_case_context,
    _normalize_text,
    _require_block,
    _resolve_city_payload,
    load_benchmark_cases,
)


def _candidate_key(city: Dict[str, Any]) -> tuple[str, float, float]:
    return (
        str(city.get("label") or city.get("query") or "").strip().lower(),
        round(float(city.get("latitude") or 0.0), 4),
        round(float(city.get("longitude") or 0.0), 4),
    )


def _resolve_candidate_pool(
    case: Dict[str, Any],
    *,
    context: Dict[str, Any],
    allow_live_geocode: bool = False,
) -> List[Dict[str, Any]]:
    event_block = _require_block(case, "event")
    event_city = dict(context.get("event_city_for_transit") or {})
    if not event_city:
        event_city = _resolve_city_payload(event_block.get("location"), allow_live_geocode=allow_live_geocode)

    candidate_pool = case.get("candidate_pool")
    raw_candidates = candidate_pool if isinstance(candidate_pool, list) and candidate_pool else (case.get("controls") or [])

    resolved: List[Dict[str, Any]] = []
    seen = set()

    event_key = _candidate_key(event_city)
    resolved.append({"role": "event", "reason": "", **event_city})
    seen.add(event_key)

    for raw in raw_candidates:
        city = _resolve_city_payload(raw, allow_live_geocode=allow_live_geocode)
        key = _candidate_key(city)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(
            {
                "role": "control",
                "reason": raw.get("reason") if isinstance(raw, dict) else "",
                **city,
            }
        )

    return resolved


def _resolve_pathfinder_options(
    case: Dict[str, Any],
    *,
    candidate_count: int,
    resolution_override: Optional[str] = None,
    limit_override: Optional[int] = None,
    relocation_limit_override: Optional[int] = None,
) -> Dict[str, Any]:
    pathfinder_context = case.get("pathfinder_context")
    if not isinstance(pathfinder_context, dict):
        pathfinder_context = {}

    resolution = _normalize_text(resolution_override or pathfinder_context.get("resolution") or "") or "standard"
    resolution_settings = get_atlas_resolution_settings(resolution)

    limit = limit_override
    if limit is None:
        try:
            limit = int(pathfinder_context.get("limit") or candidate_count)
        except Exception:
            limit = candidate_count
    limit = max(1, int(limit))

    relocation_limit = relocation_limit_override
    if relocation_limit is None:
        try:
            relocation_limit = int(pathfinder_context.get("relocation_limit") or resolution_settings.get("relocation_limit") or candidate_count)
        except Exception:
            relocation_limit = candidate_count
    relocation_limit = max(limit, int(relocation_limit))

    return {
        "resolution": resolution_settings.get("id") or resolution,
        "resolution_settings": resolution_settings,
        "limit": limit,
        "relocation_limit": relocation_limit,
    }


def _rank_for_label(rows: Sequence[Dict[str, Any]], label: str) -> Optional[int]:
    normalized = _normalize_text(label).lower()
    for row in rows:
        if _normalize_text(row.get("label")).lower() == normalized:
            try:
                return int(row.get("rank"))
            except Exception:
                return None
    return None


def _build_case_result(
    case: Dict[str, Any],
    *,
    mode: str,
    context: Dict[str, Any],
    candidate_pool: Sequence[Dict[str, Any]],
    ranking_result: Dict[str, Any],
    resolution: str,
    limit: int,
    relocation_limit: int,
) -> Dict[str, Any]:
    event_city = next(item for item in candidate_pool if item.get("role") == "event")
    event_label = str(event_city.get("label") or event_city.get("query") or "")
    debug = ranking_result.get("debug") or {}
    initial_ranking = debug.get("initial_ranking") or []
    final_scored_ranking = debug.get("final_scored_ranking") or []
    final_ranking = ranking_result.get("ranking") or []
    prepass_labels = {str(label) for label in (debug.get("prepass_labels") or [])}
    shortlisted_labels = {str(label) for label in (debug.get("shortlisted_labels") or [])}

    initial_rank = _rank_for_label(initial_ranking, event_label)
    rescored_rank = _rank_for_label(final_scored_ranking, event_label)
    final_rank = _rank_for_label(final_ranking, event_label)
    rank_delta = None
    if initial_rank is not None and final_rank is not None:
        rank_delta = initial_rank - final_rank

    return {
        "case_id": _normalize_text(case.get("case_id")) or f"line-{case.get('_line_number')}",
        "goal_id": str(context.get("goal_id") or ""),
        "dataset": str(case.get("_dataset_path") or ""),
        "line_number": int(case.get("_line_number") or 0),
        "person_name": _normalize_text(case.get("person_name")),
        "mode": mode,
        "pathfinder": {
            "resolution": resolution,
            "limit": limit,
            "relocation_limit": relocation_limit,
            "candidate_count": len(candidate_pool),
            "shortlist_strategy": ranking_result.get("shortlist_strategy"),
            "relocation_prepass_count": int(ranking_result.get("relocation_prepass_count") or 0),
            "shortlisted_count": int(ranking_result.get("shortlisted_count") or 0),
            "viable_count": int(ranking_result.get("viable_count") or 0),
            "signal_floor_raw_score": ranking_result.get("signal_floor_raw_score"),
        },
        "event": {
            "label": event_label,
            "initial_rank": initial_rank,
            "rescored_rank": rescored_rank,
            "final_rank": final_rank,
            "in_prepass": event_label in prepass_labels,
            "in_shortlist": event_label in shortlisted_labels,
            "in_final_ranking": final_rank is not None,
            "top_1_hit": final_rank == 1,
            "top_3_hit": bool(final_rank is not None and final_rank <= 3),
            "rank_delta": rank_delta,
        },
        "candidate_pool": [
            {
                "role": item.get("role"),
                "label": item.get("label"),
                "query": item.get("query"),
                "reason": item.get("reason") or "",
                "timezone": item.get("timezone") or "",
            }
            for item in candidate_pool
        ],
        "ranking": final_ranking,
    }


def _summarize_pathfinder_group(case_results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not case_results:
        return {}

    case_count = len(case_results)
    prepass_hits = 0
    shortlist_hits = 0
    final_ranked_hits = 0
    top_1_hits = 0
    top_3_hits = 0
    dropped_before_prepass = 0
    dropped_after_prepass = 0
    initial_rank_total = 0.0
    final_rank_total = 0.0
    rank_delta_values: List[float] = []

    for case in case_results:
        event = case.get("event") or {}
        candidate_count = int(((case.get("pathfinder") or {}).get("candidate_count")) or 0)
        fallback_rank = candidate_count + 1 if candidate_count > 0 else 1
        initial_rank = event.get("initial_rank")
        final_rank = event.get("final_rank")
        if event.get("in_prepass"):
            prepass_hits += 1
        else:
            dropped_before_prepass += 1
        if event.get("in_shortlist"):
            shortlist_hits += 1
        if final_rank is not None:
            final_ranked_hits += 1
        elif event.get("in_prepass"):
            dropped_after_prepass += 1
        if event.get("top_1_hit"):
            top_1_hits += 1
        if event.get("top_3_hit"):
            top_3_hits += 1
        initial_rank_total += float(initial_rank or fallback_rank)
        final_rank_total += float(final_rank or fallback_rank)
        if event.get("rank_delta") is not None:
            rank_delta_values.append(float(event.get("rank_delta") or 0.0))

    summary: Dict[str, Any] = {
        "case_count": case_count,
        "prepass_hit_rate": round(prepass_hits / float(case_count), 4),
        "shortlist_hit_rate": round(shortlist_hits / float(case_count), 4),
        "final_ranked_rate": round(final_ranked_hits / float(case_count), 4),
        "top_1_hit_rate": round(top_1_hits / float(case_count), 4),
        "top_3_hit_rate": round(top_3_hits / float(case_count), 4),
        "mean_initial_rank": round(initial_rank_total / float(case_count), 4),
        "mean_final_rank": round(final_rank_total / float(case_count), 4),
        "dropped_before_prepass_count": dropped_before_prepass,
        "dropped_after_prepass_count": dropped_after_prepass,
    }
    if rank_delta_values:
        summary["mean_rank_delta"] = round(sum(rank_delta_values) / float(len(rank_delta_values)), 4)
    return summary


def summarize_pathfinder_results(case_results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    overall = _summarize_pathfinder_group(case_results)
    by_goal: Dict[str, Dict[str, Any]] = {}
    goal_ids = sorted({str(case.get("goal_id") or "") for case in case_results if str(case.get("goal_id") or "")})
    for goal_id in goal_ids:
        scoped = [case for case in case_results if str(case.get("goal_id") or "") == goal_id]
        by_goal[goal_id] = _summarize_pathfinder_group(scoped)
    return {
        "overall": overall,
        "by_goal": by_goal,
    }


def _render_markdown_report(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Astrocartography Pathfinder Benchmark Summary")
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
        lines.append("| Cases | Prepass | Shortlist | Ranked | Top-1 | Top-3 | Mean Initial | Mean Final | Mean Delta |")
        lines.append("| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        lines.append(
            f"| {overall.get('case_count') or 0} | "
            f"{overall.get('prepass_hit_rate') if overall.get('prepass_hit_rate') is not None else 'n/a'} | "
            f"{overall.get('shortlist_hit_rate') if overall.get('shortlist_hit_rate') is not None else 'n/a'} | "
            f"{overall.get('final_ranked_rate') if overall.get('final_ranked_rate') is not None else 'n/a'} | "
            f"{overall.get('top_1_hit_rate') if overall.get('top_1_hit_rate') is not None else 'n/a'} | "
            f"{overall.get('top_3_hit_rate') if overall.get('top_3_hit_rate') is not None else 'n/a'} | "
            f"{overall.get('mean_initial_rank') if overall.get('mean_initial_rank') is not None else 'n/a'} | "
            f"{overall.get('mean_final_rank') if overall.get('mean_final_rank') is not None else 'n/a'} | "
            f"{overall.get('mean_rank_delta') if overall.get('mean_rank_delta') is not None else 'n/a'} |"
        )
        lines.append("")

    by_goal = (result.get("summary") or {}).get("by_goal") or {}
    for goal_id, summary in by_goal.items():
        lines.append(f"## Goal: `{goal_id}`")
        lines.append("")
        lines.append("| Cases | Prepass | Shortlist | Ranked | Top-1 | Top-3 | Mean Initial | Mean Final | Mean Delta |")
        lines.append("| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        lines.append(
            f"| {summary.get('case_count') or 0} | "
            f"{summary.get('prepass_hit_rate') if summary.get('prepass_hit_rate') is not None else 'n/a'} | "
            f"{summary.get('shortlist_hit_rate') if summary.get('shortlist_hit_rate') is not None else 'n/a'} | "
            f"{summary.get('final_ranked_rate') if summary.get('final_ranked_rate') is not None else 'n/a'} | "
            f"{summary.get('top_1_hit_rate') if summary.get('top_1_hit_rate') is not None else 'n/a'} | "
            f"{summary.get('top_3_hit_rate') if summary.get('top_3_hit_rate') is not None else 'n/a'} | "
            f"{summary.get('mean_initial_rank') if summary.get('mean_initial_rank') is not None else 'n/a'} | "
            f"{summary.get('mean_final_rank') if summary.get('mean_final_rank') is not None else 'n/a'} | "
            f"{summary.get('mean_rank_delta') if summary.get('mean_rank_delta') is not None else 'n/a'} |"
        )
        lines.append("")

    if result.get("failures"):
        lines.append("## Failed Cases")
        lines.append("")
        for failure in result["failures"]:
            lines.append(f"- `{failure.get('case_id')}`: {failure.get('error')}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def run_pathfinder_benchmark(
    dataset_paths: Sequence[str | Path],
    *,
    mode: str,
    case_id: Optional[str] = None,
    allow_live_geocode: bool = False,
    include_disabled: bool = False,
    resolution_override: Optional[str] = None,
    limit_override: Optional[int] = None,
    relocation_limit_override: Optional[int] = None,
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

            candidate_pool = _resolve_candidate_pool(case, context=context, allow_live_geocode=allow_live_geocode)
            if len(candidate_pool) < 2:
                raise ValueError("PathFinder benchmark candidate pool requires at least one event city and one comparison city")

            options = _resolve_pathfinder_options(
                case,
                candidate_count=len(candidate_pool),
                resolution_override=resolution_override,
                limit_override=limit_override,
                relocation_limit_override=relocation_limit_override,
            )

            def relocation_bundle_resolver(item: Dict[str, Any]) -> Dict[str, Any]:
                target = item.get("target") or {}
                atlas_city = item.get("atlas_city") or {}
                return _compute_chart_bundle_for(
                    str(natal_timestamp),
                    str(target.get("query") or target.get("label") or ""),
                    atlas_city.get("timezone") or None,
                )

            ranking_result = rank_candidate_pool_for_goal(
                goal_id=str(context["goal_id"]),
                candidates=candidate_pool,
                natal_lines=context["natal_lines"],
                transit_lines=context.get("transit_lines"),
                limit=options["limit"],
                relocation_limit=options["relocation_limit"],
                limit_cap=None,
                relocation_limit_cap=None,
                relocation_bundle_resolver=relocation_bundle_resolver,
                include_debug_ranking=True,
            )

            case_results.append(
                _build_case_result(
                    case,
                    mode=mode,
                    context=context,
                    candidate_pool=candidate_pool,
                    ranking_result=ranking_result,
                    resolution=str(options["resolution"]),
                    limit=int(options["limit"]),
                    relocation_limit=int(options["relocation_limit"]),
                )
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
        "summary": summarize_pathfinder_results(case_results),
    }
    result["markdown"] = _render_markdown_report(result)
    return result


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen-candidate PathFinder benchmarks against the live atlas shortlist and ranking logic.")
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
    parser.add_argument("--resolution", help="Override the benchmark resolution profile for relocation-limit defaults.")
    parser.add_argument("--limit", type=int, help="Override the final ranking limit.")
    parser.add_argument("--relocation-limit", type=int, help="Override the relocation shortlist limit.")
    parser.add_argument("--output-json", help="Write the full benchmark result to a JSON file.")
    parser.add_argument("--output-md", help="Write the Markdown summary to a file.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    datasets = args.datasets or [str(DEFAULT_SPECULATION_DATASET)]
    result = run_pathfinder_benchmark(
        datasets,
        mode=args.mode,
        case_id=args.case_id,
        allow_live_geocode=bool(args.allow_live_geocode),
        include_disabled=bool(args.include_disabled),
        resolution_override=args.resolution,
        limit_override=args.limit,
        relocation_limit_override=args.relocation_limit,
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
