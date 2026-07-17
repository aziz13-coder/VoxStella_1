from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from validate_mundane_benchmark_datasets import (
    HISTORICAL_FILES,
    NATIONAL_CHART_CANDIDATE_FILE,
    SOURCE_ALIGNMENT_FILE,
    load_jsonl_cases,
    validate_historical_case,
    validate_national_chart_candidate_case,
    validate_source_alignment_case,
)


def _resolve_reference_root() -> Path:
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "AGENTS.md").exists() and (parent / "backend").is_dir():
            return parent
    return current_path.parents[1]


REPO_ROOT = _resolve_reference_root()
DEFAULT_DATASET_PATHS = [SOURCE_ALIGNMENT_FILE, *HISTORICAL_FILES, NATIONAL_CHART_CANDIDATE_FILE]


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _dataset_kind(path: Path) -> str:
    if path.name == SOURCE_ALIGNMENT_FILE.name:
        return "source_alignment"
    if path.name == NATIONAL_CHART_CANDIDATE_FILE.name:
        return "national_chart_candidate"
    return "historical"


def _validate_case(case: Dict[str, Any], path: Path) -> None:
    dataset_kind = _dataset_kind(path)
    if dataset_kind == "source_alignment":
        validate_source_alignment_case(case, path)
    elif dataset_kind == "national_chart_candidate":
        validate_national_chart_candidate_case(case, path)
    else:
        validate_historical_case(case, path)


def _source_entries(case: Dict[str, Any], dataset_kind: str) -> List[Dict[str, Any]]:
    if dataset_kind == "source_alignment":
        source = case.get("source")
        return [source] if isinstance(source, dict) else []
    assertions = case.get("source_assertions") or []
    return [item for item in assertions if isinstance(item, dict)]


def _is_remote_reference(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _check_source_files(case: Dict[str, Any], dataset_kind: str, dataset_path: Path) -> List[Dict[str, str]]:
    failures: List[Dict[str, str]] = []
    case_id = _normalize_text(case.get("case_id")) or "unknown"
    for source in _source_entries(case, dataset_kind):
        title = _normalize_text(source.get("title")) or "unknown"
        for key in ("raw_file", "normalized_file"):
            relpath = _normalize_text(source.get(key))
            if not relpath:
                failures.append(
                    {
                        "case_id": case_id,
                        "dataset": str(dataset_path),
                        "source_title": title,
                        "path_key": key,
                        "detail": f"Missing {key} value.",
                    }
                )
                continue
            if _is_remote_reference(relpath):
                continue
            candidate = REPO_ROOT / relpath
            if not candidate.exists():
                failures.append(
                    {
                        "case_id": case_id,
                        "dataset": str(dataset_path),
                        "source_title": title,
                        "path_key": key,
                        "detail": f"Referenced file does not exist: {relpath}",
                    }
                )
    return failures


def load_benchmark_cases(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cases: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    case_filter = _normalize_text(case_id).lower()

    for raw_path in dataset_paths or DEFAULT_DATASET_PATHS:
        path = Path(raw_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Benchmark dataset not found: {path}")
        dataset_kind = _dataset_kind(path)
        for payload in load_jsonl_cases(path):
            current_case_id = _normalize_text(payload.get("case_id"))
            if case_filter and current_case_id.lower() != case_filter:
                continue
            _validate_case(payload, path)
            if not include_disabled and not bool(payload.get("enabled")):
                skipped.append(
                    {
                        "dataset": str(path),
                        "case_id": current_case_id,
                        "reason": "disabled",
                    }
                )
                continue
            case = dict(payload)
            case["_dataset_path"] = str(path)
            case["_dataset_kind"] = dataset_kind
            cases.append(case)

    return cases, skipped


def _summarize_case(case: Dict[str, Any]) -> Dict[str, Any]:
    dataset_kind = str(case.get("_dataset_kind") or "")
    dataset_path = Path(str(case.get("_dataset_path") or ""))
    sources = _source_entries(case, dataset_kind)
    citation_failures = _check_source_files(case, dataset_kind, dataset_path)

    summary: Dict[str, Any] = {
        "case_id": case.get("case_id"),
        "label": case.get("label"),
        "dataset": str(dataset_path),
        "dataset_kind": dataset_kind,
        "citation_failures": citation_failures,
        "source_titles": sorted(
            {
                _normalize_text(source.get("title"))
                for source in sources
                if _normalize_text(source.get("title"))
            }
        ),
    }

    if dataset_kind == "source_alignment":
        summary["doctrine_area"] = case.get("doctrine_area")
        summary["tags"] = case.get("tags") or []
    elif dataset_kind == "historical":
        summary["domain_id"] = case.get("domain_id")
        summary["benchmark_type"] = case.get("benchmark_type")
        summary["seed_quality"] = case.get("seed_quality") or "unspecified"
        summary["chart_basis"] = case.get("chart_basis") or []
        event = case.get("event") or {}
        summary["event_type"] = event.get("type")
        summary["polity"] = event.get("polity")
    else:
        summary["benchmark_type"] = case.get("benchmark_type")
        summary["candidate_id"] = case.get("candidate_id")
        summary["candidate_type"] = case.get("candidate_type")
        summary["candidate_status"] = case.get("candidate_status")
        summary["confidence"] = case.get("confidence")
        summary["expected_uses"] = case.get("expected_uses") or []
        event = case.get("event") or {}
        summary["event_type"] = event.get("type")
        summary["polity_id"] = case.get("polity_id")

    return summary


def run_mundane_benchmark_suite(
    dataset_paths: Optional[Sequence[str | Path]] = None,
    *,
    case_id: Optional[str] = None,
    include_disabled: bool = False,
) -> Dict[str, Any]:
    cases, skipped = load_benchmark_cases(
        dataset_paths,
        case_id=case_id,
        include_disabled=include_disabled,
    )

    dataset_case_counts: Counter[str] = Counter()
    doctrine_area_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    benchmark_type_counts: Counter[str] = Counter()
    seed_quality_counts: Counter[str] = Counter()
    chart_basis_counts: Counter[str] = Counter()
    candidate_status_counts: Counter[str] = Counter()
    candidate_polity_counts: Counter[str] = Counter()
    source_title_counts: Counter[str] = Counter()
    case_summaries: List[Dict[str, Any]] = []
    citation_failures: List[Dict[str, str]] = []
    source_alignment_case_count = 0
    historical_case_count = 0
    national_chart_candidate_count = 0
    unique_case_ids: set[str] = set()

    for case in cases:
        summary = _summarize_case(case)
        case_summaries.append(summary)
        case_id = _normalize_text(summary.get("case_id"))
        if case_id:
            unique_case_ids.add(case_id)
        dataset_case_counts[Path(summary["dataset"]).name] += 1
        for title in summary.get("source_titles") or []:
            normalized_title = _normalize_text(title)
            if normalized_title:
                source_title_counts[normalized_title] += 1

        failures = summary.get("citation_failures") or []
        citation_failures.extend(failures)

        if summary["dataset_kind"] == "source_alignment":
            source_alignment_case_count += 1
            doctrine_area = _normalize_text(summary.get("doctrine_area"))
            if doctrine_area:
                doctrine_area_counts[doctrine_area] += 1
        elif summary["dataset_kind"] == "historical":
            historical_case_count += 1
            domain_id = _normalize_text(summary.get("domain_id"))
            if domain_id:
                domain_counts[domain_id] += 1
            benchmark_type = _normalize_text(summary.get("benchmark_type"))
            if benchmark_type:
                benchmark_type_counts[benchmark_type] += 1
            seed_quality = _normalize_text(summary.get("seed_quality"))
            if seed_quality:
                seed_quality_counts[seed_quality] += 1
            for chart_basis in summary.get("chart_basis") or []:
                normalized_basis = _normalize_text(chart_basis)
                if normalized_basis:
                    chart_basis_counts[normalized_basis] += 1
        else:
            national_chart_candidate_count += 1
            candidate_status = _normalize_text(summary.get("candidate_status"))
            polity_id = _normalize_text(summary.get("polity_id"))
            if candidate_status:
                candidate_status_counts[candidate_status] += 1
            if polity_id:
                candidate_polity_counts[polity_id] += 1

    return {
        "dataset_paths": [
            str(Path(path).resolve()) for path in (dataset_paths or DEFAULT_DATASET_PATHS)
        ],
        "case_count": len(case_summaries),
        "unique_case_count": len(unique_case_ids),
        "source_alignment_case_count": source_alignment_case_count,
        "historical_case_count": historical_case_count,
        "national_chart_candidate_count": national_chart_candidate_count,
        "dataset_case_counts": dict(sorted(dataset_case_counts.items())),
        "doctrine_area_counts": dict(sorted(doctrine_area_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "benchmark_type_counts": dict(sorted(benchmark_type_counts.items())),
        "seed_quality_counts": dict(sorted(seed_quality_counts.items())),
        "chart_basis_counts": dict(sorted(chart_basis_counts.items())),
        "candidate_status_counts": dict(sorted(candidate_status_counts.items())),
        "candidate_polity_counts": dict(sorted(candidate_polity_counts.items())),
        "source_title_counts": dict(sorted(source_title_counts.items())),
        "citation_failures": citation_failures,
        "skipped": skipped,
        "cases": case_summaries,
    }


def render_markdown_report(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Mundane Benchmark Report")
    lines.append("")
    lines.append(f"- Dataset rows: {int(report.get('case_count') or 0)}")
    lines.append(f"- Unique case IDs: {int(report.get('unique_case_count') or 0)}")
    lines.append(
        f"- Source-alignment cases: {int(report.get('source_alignment_case_count') or 0)}"
    )
    lines.append(f"- Historical cases: {int(report.get('historical_case_count') or 0)}")
    lines.append(
        f"- National-chart candidate cases: {int(report.get('national_chart_candidate_count') or 0)}"
    )
    lines.append(f"- Citation failures: {len(report.get('citation_failures') or [])}")
    lines.append("")
    lines.append("## Datasets")
    lines.append("")
    for dataset_path in report.get("dataset_paths") or []:
        lines.append(f"- `{dataset_path}`")

    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    for label, bucket in (
        ("By doctrine area", report.get("doctrine_area_counts") or {}),
        ("By domain", report.get("domain_counts") or {}),
        ("By benchmark type", report.get("benchmark_type_counts") or {}),
        ("By seed quality", report.get("seed_quality_counts") or {}),
        ("By chart basis", report.get("chart_basis_counts") or {}),
        ("By candidate status", report.get("candidate_status_counts") or {}),
        ("By candidate polity", report.get("candidate_polity_counts") or {}),
        ("By source title", report.get("source_title_counts") or {}),
    ):
        lines.append(f"### {label}")
        lines.append("")
        if not bucket:
            lines.append("- none")
        else:
            for key, count in bucket.items():
                lines.append(f"- `{key}`: {count}")
        lines.append("")

    skipped = report.get("skipped") or []
    if skipped:
        lines.append("## Skipped")
        lines.append("")
        for item in skipped:
            lines.append(f"- `{item.get('case_id')}`: {item.get('reason')}")
        lines.append("")

    citation_failures = report.get("citation_failures") or []
    if citation_failures:
        lines.append("## Citation Failures")
        lines.append("")
        for item in citation_failures:
            lines.append(
                f"- `{item.get('case_id')}` {item.get('path_key')}: {item.get('detail')}"
            )
        lines.append("")

    lines.append("## Cases")
    lines.append("")
    for case in report.get("cases") or []:
        lines.append(f"### {case.get('label') or case.get('case_id')}")
        lines.append("")
        lines.append(f"- Case ID: `{case.get('case_id')}`")
        lines.append(f"- Dataset: `{Path(str(case.get('dataset') or '')).name}`")
        if case.get("dataset_kind") == "source_alignment":
            lines.append(f"- Doctrine area: `{case.get('doctrine_area')}`")
        elif case.get("dataset_kind") == "historical":
            lines.append(f"- Domain: `{case.get('domain_id')}`")
            lines.append(f"- Benchmark type: `{case.get('benchmark_type')}`")
            lines.append(f"- Seed quality: `{case.get('seed_quality')}`")
        else:
            lines.append(f"- Candidate ID: `{case.get('candidate_id')}`")
            lines.append(f"- Polity: `{case.get('polity_id')}`")
            lines.append(f"- Candidate status: `{case.get('candidate_status')}`")
            lines.append(f"- Confidence: `{case.get('confidence')}`")
        source_titles = ", ".join(_normalize_text(title) for title in case.get("source_titles") or [])
        lines.append(f"- Sources: {source_titles or 'none'}")
        if case.get("citation_failures"):
            lines.append("- Status: FAIL")
        else:
            lines.append("- Status: PASS")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and summarize the mundane benchmark datasets."
    )
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        help="Path to a mundane benchmark JSONL dataset. Repeat for multiple datasets.",
    )
    parser.add_argument("--case-id", help="Run only one case_id from the dataset set.")
    parser.add_argument(
        "--include-disabled",
        action="store_true",
        help="Include disabled cases in the report.",
    )
    parser.add_argument("--output-json", help="Optional path to write the full report as JSON.")
    parser.add_argument("--output-md", help="Optional path to write the markdown summary.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    dataset_paths = args.dataset or DEFAULT_DATASET_PATHS
    report = run_mundane_benchmark_suite(
        dataset_paths,
        case_id=args.case_id,
        include_disabled=args.include_disabled,
    )
    markdown = render_markdown_report(report)
    print(markdown, end="")

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(markdown, encoding="utf-8")

    return 1 if report.get("citation_failures") else 0


if __name__ == "__main__":
    raise SystemExit(main())
