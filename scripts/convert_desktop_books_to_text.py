"""
Convert source books from a directory into plain text files for repo-local AI use.

Supported inputs:
- PDF (text-layer extraction via pypdf)
- EPUB (HTML/XHTML extraction via zipfile + stdlib HTMLParser)
- TXT (copied/normalized)

Outputs are written to a dedicated folder plus a manifest.json summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

import pypdf
from pypdf import PdfReader

try:
    from .astrocartography_source_governance import (
        SOURCE_REGISTRY_PATH,
        load_source_registry,
        repo_relative_posix,
        sha256_file,
        source_by_original_name,
    )
except ImportError:  # Script execution: python scripts/convert_desktop_books_to_text.py
    import sys as _sys

    _scripts_dir = str(Path(__file__).resolve().parent)
    if _scripts_dir not in _sys.path:
        _sys.path.insert(0, _scripts_dir)
    from astrocartography_source_governance import (
        SOURCE_REGISTRY_PATH,
        load_source_registry,
        repo_relative_posix,
        sha256_file,
        source_by_original_name,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / "Desktop" / "astrolgy books"
DEFAULT_DEST = REPO_ROOT / "horary_knowledge" / "desktop_books_text"
TEXT_EXTENSIONS = {".txt", ".text"}
EPUB_HTML_EXTENSIONS = {".html", ".htm", ".xhtml", ".xml", ".ncx", ".opf"}
SUSPECT_MIN_CHARS = 200
MAX_OUTPUT_STEM_LEN = 120


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._chunks.append(data)

    def text(self) -> str:
        return "\n".join(self._chunks)


@dataclass
class ManifestRow:
    source_id: str
    source_name: str
    source_ext: str
    source_sha256: str
    source_bytes: int
    bibliography: dict[str, Any]
    authority: dict[str, Any]
    default_claim_classification: str
    retrieval: dict[str, Any]
    rights: dict[str, Any]
    output_name: str
    output_path: str
    output_sha256: str
    status: str
    chars: int
    extraction: dict[str, Any]
    page_coverage: dict[str, Any]
    notes: str


@dataclass(frozen=True)
class ConversionResult:
    text: str
    note: str
    extractor: str
    extractor_version: str
    source_pages: int | None
    extracted_pages: tuple[int, ...]


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unescape(text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip() + "\n"


def safe_slug(path: Path, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("._-") or "book"
    if len(base) > MAX_OUTPUT_STEM_LEN:
        digest = hashlib.sha1(path.name.encode("utf-8")).hexdigest()[:10]
        keep = max(16, MAX_OUTPUT_STEM_LEN - len(digest) - 1)
        base = f"{base[:keep].rstrip('._-')}_{digest}"
    slug = base
    idx = 2
    while f"{slug}.txt" in used:
        slug = f"{base}_{idx}"
        idx += 1
    used.add(f"{slug}.txt")
    return f"{slug}.txt"


def extract_pdf(path: Path) -> ConversionResult:
    raw_prefix = path.read_bytes()[:2048]
    if raw_prefix.lstrip().startswith(b"<"):
        text = extract_htmlish_text(raw_prefix + path.read_bytes()[2048:])
        return ConversionResult(
            text=text,
            note="PDF extension contained HTML-like content",
            extractor="stdlib.HTMLParser",
            extractor_version="stdlib",
            source_pages=None,
            extracted_pages=(),
        )
    reader = PdfReader(str(path))
    parts: list[str] = []
    extracted_pages: list[int] = []
    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(f"\n\n=== Page {page_num} ===\n{page_text.strip()}")
            extracted_pages.append(page_num)
    return ConversionResult(
        text=normalize_text("\n".join(parts)),
        note="",
        extractor="pypdf.PdfReader.extract_text",
        extractor_version=pypdf.__version__,
        source_pages=len(reader.pages),
        extracted_pages=tuple(extracted_pages),
    )


def extract_pdf_text(path: Path) -> str:
    """Backward-compatible text-only wrapper."""

    return extract_pdf(path).text


def _decode_bytes(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def extract_htmlish_text(raw: bytes) -> str:
    parser = _HtmlTextExtractor()
    parser.feed(_decode_bytes(raw))
    return normalize_text(parser.text())


def extract_epub(path: Path) -> ConversionResult:
    sections: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = sorted(
            name for name in zf.namelist()
            if Path(name).suffix.lower() in EPUB_HTML_EXTENSIONS and not name.endswith("/")
        )
        for name in names:
            raw = zf.read(name)
            parser = _HtmlTextExtractor()
            parser.feed(_decode_bytes(raw))
            text = normalize_text(parser.text())
            if text.strip():
                sections.append(f"\n\n=== {name} ===\n{text.strip()}")
    return ConversionResult(
        text=normalize_text("\n".join(sections)),
        note="",
        extractor="zipfile+stdlib.HTMLParser",
        extractor_version="stdlib",
        source_pages=None,
        extracted_pages=(),
    )


def extract_epub_text(path: Path) -> str:
    """Backward-compatible text-only wrapper."""

    return extract_epub(path).text


def extract_txt_text(path: Path) -> str:
    raw = path.read_bytes()
    return normalize_text(_decode_bytes(raw))


def convert_file_with_metadata(path: Path) -> ConversionResult:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf(path)
    if ext == ".epub":
        return extract_epub(path)
    if ext in TEXT_EXTENSIONS:
        return ConversionResult(
            text=extract_txt_text(path),
            note="copied from plain text source",
            extractor="byte-decode+normalize_text",
            extractor_version="stdlib",
            source_pages=None,
            extracted_pages=(),
        )
    raise ValueError(f"unsupported file type: {ext}")


def convert_file(path: Path) -> tuple[str, str]:
    """Backward-compatible conversion API used by older callers."""

    result = convert_file_with_metadata(path)
    return result.text, result.note


def classify_extraction(text: str, note: str) -> tuple[str, str]:
    lowered = text.lower()
    if "file not found" in lowered:
        return "error", "source file contains a file-not-found placeholder instead of book text"
    if "a php error was encountered" in lowered or "failed to open stream" in lowered:
        return "error", "source file is an HTML/PHP error wrapper, not usable book text"
    if len(text.strip()) < SUSPECT_MIN_CHARS:
        extra = "very low extracted text; likely scan-only, broken source, or image-based PDF"
        if note:
            extra = f"{note}; {extra}"
        return "warning", extra
    return "ok", note


def iter_supported_files(source_dir: Path) -> Iterable[Path]:
    for path in sorted(source_dir.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".pdf", ".epub", *TEXT_EXTENSIONS}:
            yield path


def fallback_source_id(path: Path, source_sha256: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    stem = stem[:48].rstrip("-") or "document"
    return f"local-src-{stem}-{source_sha256[:12]}"


def manifest_output_path(output_path: Path, dest_dir: Path) -> str:
    try:
        return repo_relative_posix(output_path, REPO_ROOT)
    except ValueError:
        return output_path.relative_to(dest_dir).as_posix()


def external_source_label(source_dir: Path) -> str:
    try:
        return repo_relative_posix(source_dir, REPO_ROOT)
    except ValueError:
        return "external source directory supplied at conversion time; absolute path not recorded"


def _ungoverned_metadata(path: Path) -> dict[str, Any]:
    return {
        "bibliography": {
            "title": path.stem,
            "authors": ["unrecorded"],
            "year": "unrecorded",
            "edition": "unrecorded",
            "publisher": "unrecorded",
        },
        "authority": {
            "tier": "unclassified",
            "rank": None,
            "rationale": "No matching row in the supplied source registry.",
        },
        "default_claim_classification": "experimental",
        "retrieval": {
            "enabled": False,
            "scopes": [],
            "exclusion_reason": "Ungoverned source; review metadata before retrieval.",
        },
        "rights": {
            "status": "unverified-treat-as-restricted",
            "redistribution": "not-cleared",
            "evidence": ["No matching rights record in the supplied source registry."],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument(
        "--registry",
        type=Path,
        default=SOURCE_REGISTRY_PATH,
        help="Optional source-governance registry used to enrich matching files.",
    )
    args = parser.parse_args()

    source_dir: Path = args.source
    dest_dir: Path = args.dest
    dest_dir.mkdir(parents=True, exist_ok=True)

    registry_rows: dict[str, dict[str, Any]] = {}
    if args.registry and args.registry.is_file():
        registry_rows = source_by_original_name(load_source_registry(args.registry))

    used_names: set[str] = set()
    manifest: list[ManifestRow] = []

    for source_path in iter_supported_files(source_dir):
        registry_row = registry_rows.get(source_path.name)
        if registry_row:
            output_name = Path(registry_row["extracted"]["repo_path"]).name
            if output_name in used_names:
                raise ValueError(f"duplicate governed output name: {output_name}")
            used_names.add(output_name)
        else:
            output_name = safe_slug(source_path, used_names)
        output_path = dest_dir / output_name
        source_sha256 = sha256_file(source_path)
        source_bytes = source_path.stat().st_size
        metadata = registry_row or _ungoverned_metadata(source_path)
        source_id = (
            registry_row["source_id"]
            if registry_row
            else fallback_source_id(source_path, source_sha256)
        )
        try:
            result = convert_file_with_metadata(source_path)
            output_path.write_text(result.text, encoding="utf-8")
            status, note = classify_extraction(result.text, result.note)
            original_pages = result.source_pages
            extracted_pages = list(result.extracted_pages)
            missing_pages = (
                sorted(set(range(1, original_pages + 1)) - set(extracted_pages))
                if original_pages is not None
                else []
            )
            provenance_notes: list[str] = [note] if note else []
            if registry_row:
                recorded_source_hash = registry_row["original"]["sha256"]
                if recorded_source_hash != source_sha256:
                    status = "warning"
                    provenance_notes.append(
                        "source SHA-256 differs from the governed registry"
                    )
                recorded_output_hash = registry_row["extracted"]["sha256"]
                actual_output_hash = sha256_file(output_path)
                if recorded_output_hash != actual_output_hash:
                    status = "warning"
                    provenance_notes.append(
                        "extracted output SHA-256 differs from the governed registry"
                    )
            else:
                actual_output_hash = sha256_file(output_path)
                provenance_notes.append(
                    "source is not in the supplied governance registry; retrieval disabled"
                )
            manifest.append(
                ManifestRow(
                    source_id=source_id,
                    source_name=source_path.name,
                    source_ext=source_path.suffix.lower(),
                    source_sha256=source_sha256,
                    source_bytes=source_bytes,
                    bibliography=metadata["bibliography"],
                    authority=metadata["authority"],
                    default_claim_classification=metadata[
                        "default_claim_classification"
                    ],
                    retrieval=metadata["retrieval"],
                    rights=metadata["rights"],
                    output_name=output_name,
                    output_path=manifest_output_path(output_path, dest_dir),
                    output_sha256=actual_output_hash,
                    status=status,
                    chars=len(result.text),
                    extraction={
                        "extractor": result.extractor,
                        "extractor_version": result.extractor_version,
                        "extracted_on": date.today().isoformat(),
                    },
                    page_coverage={
                        "source_pages": original_pages,
                        "extracted_page_markers": len(extracted_pages),
                        "first_extracted_page": (
                            min(extracted_pages) if extracted_pages else None
                        ),
                        "last_extracted_page": (
                            max(extracted_pages) if extracted_pages else None
                        ),
                        "missing_pages": missing_pages,
                    },
                    notes="; ".join(provenance_notes),
                )
            )
        except Exception as exc:  # pragma: no cover - conversion summary
            manifest.append(
                ManifestRow(
                    source_id=source_id,
                    source_name=source_path.name,
                    source_ext=source_path.suffix.lower(),
                    source_sha256=source_sha256,
                    source_bytes=source_bytes,
                    bibliography=metadata["bibliography"],
                    authority=metadata["authority"],
                    default_claim_classification=metadata[
                        "default_claim_classification"
                    ],
                    retrieval=metadata["retrieval"],
                    rights=metadata["rights"],
                    output_name=output_name,
                    output_path=manifest_output_path(output_path, dest_dir),
                    output_sha256="",
                    status="error",
                    chars=0,
                    extraction={
                        "extractor": "failed-before-completion",
                        "extractor_version": "unknown",
                        "extracted_on": date.today().isoformat(),
                    },
                    page_coverage={
                        "source_pages": None,
                        "extracted_page_markers": 0,
                        "first_extracted_page": None,
                        "last_extracted_page": None,
                        "missing_pages": [],
                    },
                    notes=str(exc),
                )
            )

    manifest_path = dest_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps([asdict(row) for row in manifest], indent=2),
        encoding="utf-8",
    )

    readme_lines = [
        "# Desktop Books Text Corpus",
        "",
        f"Source: {external_source_label(source_dir)}",
        "",
        "Absolute external source locations are intentionally not persisted. Full SHA-256 hashes, extraction metadata, and governed source IDs are recorded in `manifest.json`.",
        "",
        "| Source ID | Source | Output | Status | Pages | Characters | Notes |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in manifest:
        page_count = row.page_coverage.get("extracted_page_markers") or 0
        source_pages = row.page_coverage.get("source_pages")
        pages = f"{page_count}/{source_pages}" if source_pages else str(page_count)
        readme_lines.append(
            f"| `{row.source_id}` | {row.source_name} | `{row.output_path}` | "
            f"{row.status} | {pages} | {row.chars} | {row.notes or ''} |"
        )
    (dest_dir / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    print(f"Converted {len(manifest)} files into {dest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
