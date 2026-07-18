"""Shared source-governance helpers for the astrocartography corpus.

The registry and claim ledger are deliberately source assets, not generated
runtime assets.  Builders use this module so stable identifiers, authority
rules, and provenance checks do not drift between scripts.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DIR = REPO_ROOT / "horary_knowledge" / "astrocartography_sources"
SOURCE_REGISTRY_PATH = GOVERNANCE_DIR / "source_registry.json"
CLAIM_REGISTRY_PATH = GOVERNANCE_DIR / "claim_registry.json"
KNOWLEDGE_BASE_DIR = REPO_ROOT / "horary_knowledge" / "astrocartography_knowledge_base"

PAGE_MARKER_RE = re.compile(r"^=== Page (\d+) ===$", re.MULTILINE)
SOURCE_ID_RE = re.compile(r"^acg-src-[a-z0-9]+(?:-[a-z0-9]+)*$")
CLAIM_ID_RE = re.compile(r"^acg-claim-[a-z0-9]+(?:-[a-z0-9]+)*$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
ALLOWED_CLAIM_CLASSIFICATIONS = {
    "direct",
    "synthesis",
    "legacy-parity",
    "experimental",
}
REQUIRED_BIBLIOGRAPHY_FIELDS = {
    "title",
    "authors",
    "year",
    "edition",
    "publisher",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_source_registry(path: Path = SOURCE_REGISTRY_PATH) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Source registry must be a JSON object: {path}")
    return payload


def load_claim_registry(path: Path = CLAIM_REGISTRY_PATH) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Claim registry must be a JSON object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def page_numbers(text: str) -> list[int]:
    return [int(value) for value in PAGE_MARKER_RE.findall(text)]


def make_page_id(source_id: str, page: int | None) -> str:
    if not SOURCE_ID_RE.fullmatch(source_id):
        raise ValueError(f"Invalid source id: {source_id}")
    suffix = "frontmatter" if page is None else f"{page:04d}"
    return f"{source_id}.page-{suffix}"


def make_chunk_id(source_id: str, page: int | None, ordinal: int) -> str:
    if ordinal < 1:
        raise ValueError("Chunk ordinal must be positive")
    return f"{make_page_id(source_id, page)}.chunk-{ordinal:03d}"


def repo_relative_posix(path: Path, repo_root: Path = REPO_ROOT) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"Path is outside repository: {resolved}") from exc
    return relative.as_posix()


def is_repo_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    candidate = value.replace("\\", "/")
    return (
        not candidate.startswith("/")
        and not WINDOWS_ABSOLUTE_RE.match(value)
        and ".." not in Path(candidate).parts
    )


def source_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["source_id"]: row for row in registry.get("sources", [])}


def source_by_original_name(
    registry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        row["original"]["file_name"]: row
        for row in registry.get("sources", [])
        if isinstance(row.get("original"), dict) and row["original"].get("file_name")
    }


def source_by_extracted_name(
    registry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in registry.get("sources", []):
        extracted = row.get("extracted") or {}
        repo_path = extracted.get("repo_path")
        if repo_path:
            rows[Path(repo_path).name] = row
    return rows


def _duplicates(values: Iterable[object]) -> set[object]:
    seen: set[object] = set()
    duplicates: set[object] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _validate_authority_tiers(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tiers = registry.get("authority_tiers")
    if not isinstance(tiers, list) or not tiers:
        return ["source_registry.authority_tiers must be a non-empty list"]

    tier_ids = [row.get("id") for row in tiers if isinstance(row, dict)]
    ranks = [row.get("rank") for row in tiers if isinstance(row, dict)]
    if duplicates := _duplicates(tier_ids):
        errors.append(f"duplicate authority tier ids: {sorted(duplicates)}")
    if duplicates := _duplicates(ranks):
        errors.append(f"duplicate authority tier ranks: {sorted(duplicates)}")
    for row in tiers:
        if not isinstance(row, dict):
            errors.append("authority tier rows must be objects")
            continue
        for field in ("id", "rank", "label", "description"):
            if row.get(field) in (None, "", []):
                errors.append(f"authority tier missing {field}: {row!r}")
    return errors


def _validate_classification_definitions(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    definitions = registry.get("claim_classifications")
    if not isinstance(definitions, list):
        return ["source_registry.claim_classifications must be a list"]
    ids = {
        row.get("id")
        for row in definitions
        if isinstance(row, dict) and row.get("id")
    }
    if ids != ALLOWED_CLAIM_CLASSIFICATIONS:
        errors.append(
            "claim classification definitions must be exactly "
            f"{sorted(ALLOWED_CLAIM_CLASSIFICATIONS)}; found {sorted(ids)}"
        )
    for row in definitions:
        if not isinstance(row, dict) or not row.get("description"):
            errors.append(f"claim classification missing description: {row!r}")
    return errors


def _validate_source_row(
    row: dict[str, Any],
    *,
    repo_root: Path,
    tier_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    source_id = row.get("source_id")
    prefix = source_id or "<missing-source-id>"
    if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
        errors.append(f"{prefix}: invalid stable source_id")

    bibliography = row.get("bibliography")
    if not isinstance(bibliography, dict):
        errors.append(f"{prefix}: bibliography must be an object")
    else:
        for field in sorted(REQUIRED_BIBLIOGRAPHY_FIELDS):
            if bibliography.get(field) in (None, "", []):
                errors.append(f"{prefix}: bibliography.{field} is required")
        authors = bibliography.get("authors")
        if not isinstance(authors, list) or not all(
            isinstance(author, str) and author.strip() for author in authors
        ):
            errors.append(f"{prefix}: bibliography.authors must contain names")
        year = bibliography.get("year")
        if not isinstance(year, int) or not 1400 <= year <= 2100:
            errors.append(f"{prefix}: bibliography.year must be a plausible integer")

    authority = row.get("authority")
    if not isinstance(authority, dict):
        errors.append(f"{prefix}: authority must be an object")
    else:
        if authority.get("tier") not in tier_ids:
            errors.append(f"{prefix}: unknown authority tier {authority.get('tier')!r}")
        if not isinstance(authority.get("rank"), int):
            errors.append(f"{prefix}: authority.rank must be an integer")
        if not authority.get("rationale"):
            errors.append(f"{prefix}: authority.rationale is required")

    classification = row.get("default_claim_classification")
    if classification not in ALLOWED_CLAIM_CLASSIFICATIONS:
        errors.append(f"{prefix}: invalid default claim classification {classification!r}")

    rights = row.get("rights")
    if not isinstance(rights, dict):
        errors.append(f"{prefix}: rights must be an object")
    else:
        for field in ("status", "redistribution", "evidence"):
            if rights.get(field) in (None, "", []):
                errors.append(f"{prefix}: rights.{field} is required")

    retrieval = row.get("retrieval")
    if not isinstance(retrieval, dict):
        errors.append(f"{prefix}: retrieval must be an object")
    else:
        enabled = retrieval.get("enabled")
        if not isinstance(enabled, bool):
            errors.append(f"{prefix}: retrieval.enabled must be boolean")
        scopes = retrieval.get("scopes")
        if not isinstance(scopes, list):
            errors.append(f"{prefix}: retrieval.scopes must be a list")
        if not enabled and not retrieval.get("exclusion_reason"):
            errors.append(f"{prefix}: disabled retrieval requires exclusion_reason")

    original = row.get("original")
    if not isinstance(original, dict):
        errors.append(f"{prefix}: original must be an object")
    else:
        for field in ("file_name", "sha256", "bytes", "page_count", "repository_status"):
            if original.get(field) in (None, "", []):
                errors.append(f"{prefix}: original.{field} is required")
        if not re.fullmatch(r"[0-9a-f]{64}", str(original.get("sha256", ""))):
            errors.append(f"{prefix}: original.sha256 is invalid")

    extracted = row.get("extracted")
    if not isinstance(extracted, dict):
        errors.append(f"{prefix}: extracted must be an object")
        return errors

    for field in (
        "repo_path",
        "sha256",
        "bytes",
        "characters",
        "page_markers",
        "missing_pages",
        "coverage_status",
        "extraction",
    ):
        if extracted.get(field) in (None, "", []):
            if field != "missing_pages" or extracted.get(field) is None:
                errors.append(f"{prefix}: extracted.{field} is required")
    repo_path = extracted.get("repo_path")
    if not is_repo_relative_path(repo_path):
        errors.append(f"{prefix}: extracted.repo_path must be repository-relative")
    else:
        local_path = repo_root / repo_path
        if not local_path.is_file():
            errors.append(f"{prefix}: extracted file is missing: {repo_path}")
        else:
            text = local_path.read_text(encoding="utf-8")
            actual_pages = page_numbers(text)
            actual_hash = sha256_file(local_path)
            if extracted.get("sha256") != actual_hash:
                errors.append(
                    f"{prefix}: extracted.sha256 mismatch "
                    f"(registry {extracted.get('sha256')}, actual {actual_hash})"
                )
            if extracted.get("bytes") != local_path.stat().st_size:
                errors.append(f"{prefix}: extracted.bytes mismatch")
            if extracted.get("characters") != len(text):
                errors.append(f"{prefix}: extracted.characters mismatch")
            if extracted.get("page_markers") != len(actual_pages):
                errors.append(f"{prefix}: extracted.page_markers mismatch")
            original_pages = (original or {}).get("page_count")
            if isinstance(original_pages, int):
                actual_missing = sorted(set(range(1, original_pages + 1)) - set(actual_pages))
                if extracted.get("missing_pages") != actual_missing:
                    errors.append(
                        f"{prefix}: extracted.missing_pages mismatch "
                        f"(registry {extracted.get('missing_pages')}, actual {actual_missing})"
                    )

    if not re.fullmatch(r"[0-9a-f]{64}", str(extracted.get("sha256", ""))):
        errors.append(f"{prefix}: extracted.sha256 is invalid")
    extraction = extracted.get("extraction")
    if not isinstance(extraction, dict):
        errors.append(f"{prefix}: extracted.extraction must be an object")
    else:
        for field in ("extractor", "extractor_version", "extracted_on"):
            if extraction.get(field) in (None, ""):
                errors.append(f"{prefix}: extracted.extraction.{field} is required")
    return errors


def validate_source_registry(
    registry: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    errors = _validate_authority_tiers(registry)
    errors.extend(_validate_classification_definitions(registry))
    tiers = registry.get("authority_tiers") or []
    tier_ids = {
        row.get("id")
        for row in tiers
        if isinstance(row, dict) and row.get("id")
    }
    tier_rank_by_id = {
        row.get("id"): row.get("rank")
        for row in tiers
        if isinstance(row, dict)
    }
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        return errors + ["source_registry.sources must be a non-empty list"]

    source_ids = [
        row.get("source_id") for row in sources if isinstance(row, dict)
    ]
    if duplicates := _duplicates(source_ids):
        errors.append(f"duplicate source ids: {sorted(duplicates)}")

    for row in sources:
        if not isinstance(row, dict):
            errors.append("source rows must be objects")
            continue
        errors.extend(_validate_source_row(row, repo_root=repo_root, tier_ids=tier_ids))
        authority = row.get("authority") or {}
        expected_rank = tier_rank_by_id.get(authority.get("tier"))
        if expected_rank is not None and authority.get("rank") != expected_rank:
            errors.append(
                f"{row.get('source_id')}: authority.rank {authority.get('rank')} "
                f"does not match tier rank {expected_rank}"
            )

    canonical = [
        row
        for row in sources
        if (row.get("authority") or {}).get("tier") == "tier-1-canonical-doctrine"
    ]
    if [row.get("source_id") for row in canonical] != [
        "acg-src-lewis-guttman-1989"
    ]:
        errors.append(
            "Jim Lewis/Ariel Guttman must be the sole tier-1 canonical doctrinal source"
        )

    excluded = {
        row.get("source_id")
        for row in sources
        if not (row.get("retrieval") or {}).get("enabled", False)
    }
    if "acg-src-houck-death-1994" not in excluded:
        errors.append("The Astrology of Death must remain excluded from ACG retrieval")
    return errors


def validate_claim_registry(
    claims: dict[str, Any],
    registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    source_rows = source_map(registry)
    claim_rows = claims.get("claims")
    if not isinstance(claim_rows, list) or not claim_rows:
        return ["claim_registry.claims must be a non-empty list"]

    claim_ids = [
        row.get("claim_id") for row in claim_rows if isinstance(row, dict)
    ]
    if duplicates := _duplicates(claim_ids):
        errors.append(f"duplicate claim ids: {sorted(duplicates)}")

    classifications_seen: set[str] = set()
    for row in claim_rows:
        if not isinstance(row, dict):
            errors.append("claim rows must be objects")
            continue
        claim_id = row.get("claim_id")
        prefix = claim_id or "<missing-claim-id>"
        if not isinstance(claim_id, str) or not CLAIM_ID_RE.fullmatch(claim_id):
            errors.append(f"{prefix}: invalid claim_id")
        classification = row.get("classification")
        classifications_seen.add(classification)
        if classification not in ALLOWED_CLAIM_CLASSIFICATIONS:
            errors.append(f"{prefix}: invalid classification {classification!r}")
        if not row.get("statement"):
            errors.append(f"{prefix}: statement is required")
        if not row.get("status"):
            errors.append(f"{prefix}: status is required")

        refs = row.get("source_refs") or []
        if classification in {"direct", "synthesis"} and not refs:
            errors.append(f"{prefix}: {classification} claim requires source_refs")
        if classification == "synthesis" and len(refs) < 2:
            errors.append(f"{prefix}: synthesis claim requires at least two source_refs")
        for ref in refs:
            if not isinstance(ref, dict):
                errors.append(f"{prefix}: source_refs entries must be objects")
                continue
            source_id = ref.get("source_id")
            source = source_rows.get(source_id)
            if source is None:
                errors.append(f"{prefix}: unknown source ref {source_id!r}")
                continue
            page = ref.get("page")
            expected_page_id = make_page_id(source_id, page) if isinstance(page, int) else None
            if expected_page_id is None or ref.get("page_id") != expected_page_id:
                errors.append(f"{prefix}: invalid page locator {ref!r}")
            original_pages = (source.get("original") or {}).get("page_count")
            missing = set((source.get("extracted") or {}).get("missing_pages") or [])
            if (
                not isinstance(page, int)
                or not isinstance(original_pages, int)
                or page < 1
                or page > original_pages
                or page in missing
            ):
                errors.append(f"{prefix}: page is not covered by extraction: {ref!r}")

        if classification == "legacy-parity" and not row.get("legacy_artifact_refs"):
            errors.append(f"{prefix}: legacy-parity claim requires legacy_artifact_refs")
        if classification == "experimental" and not row.get("evidence_limitations"):
            errors.append(f"{prefix}: experimental claim requires evidence_limitations")

    if classifications_seen != ALLOWED_CLAIM_CLASSIFICATIONS:
        errors.append(
            "claim registry must exercise all classifications; "
            f"found {sorted(classifications_seen)}"
        )
    return errors


def validate_source_governance(
    *,
    registry_path: Path = SOURCE_REGISTRY_PATH,
    claim_registry_path: Path = CLAIM_REGISTRY_PATH,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    registry = load_source_registry(registry_path)
    claims = load_claim_registry(claim_registry_path)
    errors = validate_source_registry(registry, repo_root=repo_root)
    errors.extend(validate_claim_registry(claims, registry))
    return errors


__all__ = [
    "ALLOWED_CLAIM_CLASSIFICATIONS",
    "CLAIM_REGISTRY_PATH",
    "GOVERNANCE_DIR",
    "KNOWLEDGE_BASE_DIR",
    "PAGE_MARKER_RE",
    "REPO_ROOT",
    "SOURCE_REGISTRY_PATH",
    "is_repo_relative_path",
    "load_claim_registry",
    "load_source_registry",
    "make_chunk_id",
    "make_page_id",
    "page_numbers",
    "repo_relative_posix",
    "sha256_file",
    "sha256_text",
    "source_by_extracted_name",
    "source_by_original_name",
    "source_map",
    "validate_claim_registry",
    "validate_source_governance",
    "validate_source_registry",
]
