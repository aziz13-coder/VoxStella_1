"""Validate astrocartography source governance and generated knowledge assets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from astrocartography_source_governance import (  # noqa: E402
    ALLOWED_CLAIM_CLASSIFICATIONS,
    CLAIM_REGISTRY_PATH,
    KNOWLEDGE_BASE_DIR,
    REPO_ROOT,
    SOURCE_REGISTRY_PATH,
    is_repo_relative_path,
    load_claim_registry,
    load_source_registry,
    make_chunk_id,
    make_page_id,
    sha256_text,
    source_map,
    validate_source_governance,
)


DOCUMENT_ID_RE = re.compile(r"<!-- document-id: ([a-z0-9-]+) -->")
CLASSIFICATION_RE = re.compile(r"<!-- claim-classification: ([a-z-]+) -->")


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)


def _is_absolute_like(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\/]", value)) or value.startswith(("/", "\\\\"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: JSONL row must be an object")
        rows.append(row)
    return rows


def validate_reference_docs(reference_dir: Path) -> list[str]:
    errors: list[str] = []
    required_names = {
        "00_source_governance.md",
        "01_core_concepts.md",
        "02_planetary_and_angular_reference.md",
        "03_techniques_and_ranges.md",
        "04_glossary.md",
        "05_feature_notes.md",
        "06_extended_goal_domains.md",
    }
    actual_names = {path.name for path in reference_dir.glob("*.md")}
    missing = sorted(required_names - actual_names)
    if missing:
        errors.append(f"reference docs missing: {missing}")

    document_ids: list[str] = []
    for name in sorted(required_names & actual_names):
        path = reference_dir / name
        text = path.read_text(encoding="utf-8")
        document_match = DOCUMENT_ID_RE.search(text)
        classification_match = CLASSIFICATION_RE.search(text)
        if not document_match:
            errors.append(f"{path}: missing stable document-id")
        else:
            document_ids.append(document_match.group(1))
        if not classification_match:
            errors.append(f"{path}: missing claim-classification")
        elif classification_match.group(1) not in ALLOWED_CLAIM_CLASSIFICATIONS:
            errors.append(
                f"{path}: invalid claim-classification "
                f"{classification_match.group(1)!r}"
            )
        if "generated-by: scripts/build_astrocartography_knowledge_base.py" not in text:
            errors.append(f"{path}: missing builder provenance marker")
    if len(document_ids) != len(set(document_ids)):
        errors.append("reference document IDs must be unique")
    return errors


def validate_raw_manifest(repo_root: Path, registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    manifest_path = (
        repo_root / "horary_knowledge" / "astrocartography_books_text" / "manifest.json"
    )
    if not manifest_path.is_file():
        return [f"raw extraction manifest missing: {manifest_path}"]
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return [f"{manifest_path}: manifest must be a list"]

    rows_by_id = {
        row.get("source_id"): row
        for row in payload
        if isinstance(row, dict) and row.get("source_id")
    }
    expected_ids = set(source_map(registry))
    if set(rows_by_id) != expected_ids:
        errors.append(
            f"{manifest_path}: source IDs differ from registry "
            f"(expected {sorted(expected_ids)}, found {sorted(rows_by_id)})"
        )
    registry_by_id = source_map(registry)
    for source_id, row in rows_by_id.items():
        for field in (
            "source_sha256",
            "output_sha256",
            "bibliography",
            "authority",
            "rights",
            "extraction",
            "page_coverage",
        ):
            if row.get(field) in (None, "", {}):
                errors.append(f"{manifest_path}: {source_id} missing {field}")
        output_path = row.get("output_path")
        if not is_repo_relative_path(output_path):
            errors.append(
                f"{manifest_path}: {source_id} output_path is not repository-relative"
            )
        if any(_is_absolute_like(value) for value in _walk_strings(row)):
            errors.append(f"{manifest_path}: {source_id} contains an absolute path")
        governed = registry_by_id.get(source_id)
        if governed is None:
            continue
        if row.get("source_sha256") != governed["original"]["sha256"]:
            errors.append(f"{manifest_path}: {source_id} source SHA-256 mismatch")
        if row.get("output_sha256") != governed["extracted"]["sha256"]:
            errors.append(f"{manifest_path}: {source_id} output SHA-256 mismatch")
        if row.get("bibliography") != governed["bibliography"]:
            errors.append(f"{manifest_path}: {source_id} bibliography mismatch")
        if row.get("authority") != governed["authority"]:
            errors.append(f"{manifest_path}: {source_id} authority mismatch")
        if row.get("rights") != governed["rights"]:
            errors.append(f"{manifest_path}: {source_id} rights mismatch")
        extraction = row.get("extraction") or {}
        governed_extraction = governed["extracted"]["extraction"]
        for field in ("extractor", "extractor_version", "extracted_on"):
            if extraction.get(field) != governed_extraction.get(field):
                errors.append(
                    f"{manifest_path}: {source_id} extraction.{field} mismatch"
                )
        coverage = row.get("page_coverage") or {}
        if coverage.get("source_pages") != governed["original"]["page_count"]:
            errors.append(f"{manifest_path}: {source_id} source page count mismatch")
        if (
            coverage.get("extracted_page_markers")
            != governed["extracted"]["page_markers"]
        ):
            errors.append(
                f"{manifest_path}: {source_id} extracted page count mismatch"
            )
        if coverage.get("missing_pages") != governed["extracted"]["missing_pages"]:
            errors.append(f"{manifest_path}: {source_id} missing pages mismatch")
    return errors


def validate_source_alignment_fixtures(
    *,
    repo_root: Path,
    registry: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    dataset_path = (
        repo_root
        / "backend"
        / "benchmarks"
        / "astrocartography"
        / "source_alignment_cases.jsonl"
    )
    if not dataset_path.is_file():
        return [f"source-alignment dataset missing: {dataset_path}"]

    claim_registry = load_claim_registry(
        repo_root / CLAIM_REGISTRY_PATH.relative_to(REPO_ROOT)
    )
    claims = {row["claim_id"]: row for row in claim_registry["claims"]}
    source_rows = source_map(registry)
    chunks_by_id = {row["chunk_id"]: row for row in chunks}
    experimental_goals = {
        "health_risk",
        "accident_prone",
        "travel_relax",
        "travel_fun",
        "hostile_places",
        "risk_pressure",
        "drain_breakdown",
    }

    try:
        cases = _load_jsonl(dataset_path)
    except ValueError as exc:
        return [str(exc)]
    case_ids = [row.get("case_id") for row in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append(f"{dataset_path}: duplicate case IDs")

    for row in cases:
        case_id = row.get("case_id") or "<missing-case-id>"
        prefix = f"{dataset_path}:{case_id}"
        if row.get("fixture_policy") != "minimal_source_signal_v2":
            errors.append(f"{prefix}: fixture_policy must be minimal_source_signal_v2")
        natal_rows = row.get("natal_rows") or []
        if not isinstance(natal_rows, list) or len(natal_rows) > 1:
            errors.append(f"{prefix}: may contain at most one natal line")
        if row.get("natal_crossings"):
            errors.append(f"{prefix}: must not bake in crossing evidence")
        if row.get("relocation_planets"):
            errors.append(f"{prefix}: must not bake in relocation evidence")

        source = row.get("source")
        if not isinstance(source, dict):
            errors.append(f"{prefix}: source must be an object")
            continue
        claim_id = source.get("claim_id")
        claim = claims.get(claim_id)
        if claim is None:
            errors.append(f"{prefix}: unknown claim_id {claim_id!r}")
            continue
        if source.get("classification") != claim.get("classification"):
            errors.append(f"{prefix}: claim classification mismatch")
        normalized_file = source.get("normalized_file")
        if not is_repo_relative_path(normalized_file):
            errors.append(f"{prefix}: normalized_file must be repository-relative")
        elif not (repo_root / normalized_file).is_file():
            errors.append(f"{prefix}: normalized_file does not exist")

        claim_pages = {
            (ref["source_id"], ref["page_id"])
            for ref in claim.get("source_refs") or []
        }
        refs = source.get("refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{prefix}: source.refs must be non-empty")
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                errors.append(f"{prefix}: source ref must be an object")
                continue
            source_id = ref.get("source_id")
            page = ref.get("page")
            page_id = ref.get("page_id")
            chunk_id = ref.get("chunk_id")
            if source_id not in source_rows:
                errors.append(f"{prefix}: unknown source_id {source_id!r}")
                continue
            try:
                expected_page_id = make_page_id(source_id, page)
            except (TypeError, ValueError):
                expected_page_id = None
            if page_id != expected_page_id:
                errors.append(f"{prefix}: invalid page_id {page_id!r}")
            if (source_id, page_id) not in claim_pages:
                errors.append(
                    f"{prefix}: ref {source_id}/{page_id} is not in claim {claim_id}"
                )
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None:
                errors.append(f"{prefix}: unknown chunk_id {chunk_id!r}")
            elif (
                chunk.get("source_id") != source_id
                or chunk.get("page") != page
                or chunk.get("page_id") != page_id
            ):
                errors.append(f"{prefix}: chunk locator does not match source/page")

        expected_lead = row.get("expected_lead")
        if expected_lead and float(row.get("minimum_lead_raw_gap") or 0.0) <= 0.0:
            errors.append(f"{prefix}: expected_lead must reject raw-score ties")
        expected_positive_goals = {
            str(expected_lead or ""),
            *[str(goal) for goal in row.get("expected_in_top") or []],
            *[
                str(relation.get("higher") or "")
                for relation in row.get("expected_above") or []
                if isinstance(relation, dict)
            ],
        }
        invalid_experimental = sorted(
            expected_positive_goals & experimental_goals
        )
        if invalid_experimental:
            errors.append(
                f"{prefix}: experimental goals cannot be positive doctrine "
                f"expectations: {invalid_experimental}"
            )
        for relation in row.get("expected_above") or []:
            if (
                not isinstance(relation, dict)
                or float(relation.get("min_raw_gap") or 0.0) <= 0.0
            ):
                errors.append(
                    f"{prefix}: expected_above must require a positive raw gap"
                )
    return errors


def validate_generated_assets(
    *,
    repo_root: Path = REPO_ROOT,
    knowledge_base_dir: Path = KNOWLEDGE_BASE_DIR,
) -> list[str]:
    errors: list[str] = []
    registry = load_source_registry(
        repo_root / SOURCE_REGISTRY_PATH.relative_to(REPO_ROOT)
    )
    registry_rows = source_map(registry)

    catalog_path = knowledge_base_dir / "catalog.json"
    chunk_path = knowledge_base_dir / "chunk_index.jsonl"
    if not catalog_path.is_file():
        return [f"generated catalog missing: {catalog_path}"]
    if not chunk_path.is_file():
        return [f"generated chunk index missing: {chunk_path}"]

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        return [f"{catalog_path}: catalog must be a list"]
    catalog_by_id = {
        row.get("source_id"): row
        for row in catalog
        if isinstance(row, dict) and row.get("source_id")
    }
    if set(catalog_by_id) != set(registry_rows):
        errors.append(
            f"{catalog_path}: source IDs differ from registry "
            f"(expected {sorted(registry_rows)}, found {sorted(catalog_by_id)})"
        )

    expected_order = [
        row["source_id"]
        for row in sorted(
            registry["sources"],
            key=lambda item: (item["authority"]["rank"], item["source_id"]),
        )
    ]
    actual_order = [
        row.get("source_id") for row in catalog if isinstance(row, dict)
    ]
    if actual_order != expected_order:
        errors.append(
            f"{catalog_path}: sources are not ordered by authority "
            f"(expected {expected_order}, found {actual_order})"
        )

    absolute_values = [
        value for value in _walk_strings(catalog) if _is_absolute_like(value)
    ]
    if absolute_values:
        errors.append(
            f"{catalog_path}: absolute paths are forbidden: {absolute_values[:3]}"
        )

    chunks = _load_jsonl(chunk_path)
    chunk_ids = [row.get("chunk_id") for row in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        errors.append(f"{chunk_path}: duplicate chunk IDs")
    chunk_counts = Counter(row.get("source_id") for row in chunks)

    for row in chunks:
        source_id = row.get("source_id")
        source = registry_rows.get(source_id)
        if source is None:
            errors.append(f"{chunk_path}: unknown source ID {source_id!r}")
            continue
        if not source["retrieval"]["enabled"]:
            errors.append(f"{chunk_path}: excluded source was indexed: {source_id}")
        page = row.get("page")
        ordinal = row.get("chunk_ordinal")
        if not isinstance(ordinal, int):
            errors.append(f"{chunk_path}: invalid ordinal in {row.get('chunk_id')}")
            continue
        try:
            expected_chunk_id = make_chunk_id(source_id, page, ordinal)
            expected_page_id = make_page_id(source_id, page)
        except (TypeError, ValueError) as exc:
            errors.append(f"{chunk_path}: invalid locator: {exc}")
            continue
        if row.get("chunk_id") != expected_chunk_id:
            errors.append(
                f"{chunk_path}: chunk ID mismatch "
                f"{row.get('chunk_id')!r} != {expected_chunk_id!r}"
            )
        if row.get("page_id") != expected_page_id:
            errors.append(f"{chunk_path}: page ID mismatch in {expected_chunk_id}")
        text = row.get("text")
        if not isinstance(text, str) or row.get("text_sha256") != sha256_text(text):
            errors.append(f"{chunk_path}: text hash mismatch in {expected_chunk_id}")
        normalized_path = row.get("normalized_book_path")
        if not is_repo_relative_path(normalized_path):
            errors.append(f"{chunk_path}: invalid normalized path in {expected_chunk_id}")

    for source_id, source in registry_rows.items():
        catalog_row = catalog_by_id.get(source_id)
        if catalog_row is None:
            continue
        retrieval_enabled = source["retrieval"]["enabled"]
        normalized_path = catalog_row.get("normalized_book_path")
        guide_path = catalog_row.get("guide_path")
        if retrieval_enabled:
            for label, relative_path in (
                ("normalized_book_path", normalized_path),
                ("guide_path", guide_path),
            ):
                if not is_repo_relative_path(relative_path):
                    errors.append(f"{catalog_path}: {source_id} has invalid {label}")
                elif not (knowledge_base_dir / relative_path).is_file():
                    errors.append(
                        f"{catalog_path}: {source_id} {label} does not exist: "
                        f"{relative_path}"
                    )
            if chunk_counts[source_id] != catalog_row.get("chunk_count"):
                errors.append(f"{catalog_path}: {source_id} chunk_count mismatch")
        else:
            if normalized_path is not None or guide_path is not None:
                errors.append(
                    f"{catalog_path}: excluded source {source_id} exposes retrieval paths"
                )
            if chunk_counts[source_id]:
                errors.append(
                    f"{catalog_path}: excluded source {source_id} exposes chunks"
                )

    excluded_key = "astrology_of_death.md"
    for folder in ("normalized_books", "guides"):
        if (knowledge_base_dir / folder / excluded_key).exists():
            errors.append(
                f"{knowledge_base_dir / folder / excluded_key}: "
                "non-ACG health/death material must not be retrievable"
            )

    errors.extend(validate_reference_docs(knowledge_base_dir / "reference"))
    errors.extend(validate_raw_manifest(repo_root, registry))
    errors.extend(
        validate_source_alignment_fixtures(
            repo_root=repo_root,
            registry=registry,
            chunks=chunks,
        )
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate astrocartography sources, claims, and generated knowledge assets."
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--skip-generated", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    source_registry_path = (
        repo_root / SOURCE_REGISTRY_PATH.relative_to(REPO_ROOT)
    )
    claim_registry_path = repo_root / CLAIM_REGISTRY_PATH.relative_to(REPO_ROOT)
    errors = validate_source_governance(
        registry_path=source_registry_path,
        claim_registry_path=claim_registry_path,
        repo_root=repo_root,
    )
    if not args.skip_generated:
        errors.extend(
            validate_generated_assets(
                repo_root=repo_root,
                knowledge_base_dir=(
                    repo_root / KNOWLEDGE_BASE_DIR.relative_to(REPO_ROOT)
                ),
            )
        )

    if errors:
        print("Astrocartography source governance FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Astrocartography source governance OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
