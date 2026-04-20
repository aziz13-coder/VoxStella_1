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
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


DEFAULT_SOURCE = Path(r"C:\Users\sabaa\Desktop\astrolgy books")
DEFAULT_DEST = Path(r"C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\desktop_books_text")
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
    source_name: str
    source_ext: str
    output_name: str
    status: str
    chars: int
    notes: str = ""


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


def extract_pdf_text(path: Path) -> str:
    raw_prefix = path.read_bytes()[:2048]
    if raw_prefix.lstrip().startswith(b"<"):
        return extract_htmlish_text(raw_prefix + path.read_bytes()[2048:])
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(f"\n\n=== Page {page_num} ===\n{page_text.strip()}")
    return normalize_text("\n".join(parts))


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


def extract_epub_text(path: Path) -> str:
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
    return normalize_text("\n".join(sections))


def extract_txt_text(path: Path) -> str:
    raw = path.read_bytes()
    return normalize_text(_decode_bytes(raw))


def convert_file(path: Path) -> tuple[str, str]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf_text(path), ""
    if ext == ".epub":
        return extract_epub_text(path), ""
    if ext in TEXT_EXTENSIONS:
        return extract_txt_text(path), "copied from plain text source"
    raise ValueError(f"unsupported file type: {ext}")


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    args = parser.parse_args()

    source_dir: Path = args.source
    dest_dir: Path = args.dest
    dest_dir.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    manifest: list[ManifestRow] = []

    for source_path in iter_supported_files(source_dir):
        output_name = safe_slug(source_path, used_names)
        output_path = dest_dir / output_name
        try:
            text, note = convert_file(source_path)
            output_path.write_text(text, encoding="utf-8")
            status, note = classify_extraction(text, note)
            manifest.append(
                ManifestRow(
                    source_name=source_path.name,
                    source_ext=source_path.suffix.lower(),
                    output_name=output_name,
                    status=status,
                    chars=len(text),
                    notes=note,
                )
            )
        except Exception as exc:  # pragma: no cover - conversion summary
            manifest.append(
                ManifestRow(
                    source_name=source_path.name,
                    source_ext=source_path.suffix.lower(),
                    output_name=output_name,
                    status="error",
                    chars=0,
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
        f"Source: `{source_dir}`",
        "",
        "| Source | Output | Status | Characters | Notes |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in manifest:
        readme_lines.append(
            f"| {row.source_name} | {row.output_name} | {row.status} | {row.chars} | {row.notes or ''} |"
        )
    (dest_dir / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    print(f"Converted {len(manifest)} files into {dest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
