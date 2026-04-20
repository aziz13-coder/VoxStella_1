"""
Build an AI-friendly inspection corpus from extracted plain-text books.

Inputs:
- extracted TXT corpus produced by convert_desktop_books_to_text.py

Outputs:
- README.md
- catalog.json
- chunk_index.jsonl
- normalized_books/*.md
- guides/*.md
- chunks/<book_slug>/chunk_XXXX.md

The goal is to take raw PDF text extraction and reshape it into markdown files
with page/heading anchors plus smaller chunk files that are easier for agents
to inspect, quote, and retrieve from.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

try:  # Optional cleanup helper.
    from ftfy import fix_text as _fix_text
except Exception:  # pragma: no cover - optional dependency
    _fix_text = None


DEFAULT_RAW = Path(r"C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\new_sources_text")
DEFAULT_OUT = Path(r"C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\new_sources_inspection")
PAGE_MARKER_RE = re.compile(r"^=== Page (\d+) ===$")
MAX_CHUNK_CHARS = 7000
MAX_SLUG_LEN = 96
DEFAULT_KEYWORD_TERMS = (
    "ascendant",
    "descendant",
    "midheaven",
    "house",
    "houses",
    "sign",
    "signs",
    "zodiac",
    "planet",
    "planets",
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "aspect",
    "aspects",
    "ruler",
    "sect",
    "dignity",
    "triplicity",
    "exaltation",
    "temperament",
    "fortune",
    "spirit",
)

COMMON_MOJIBAKE = {
    "вЂ™s": "'s",
    "вЂ™": "'",
    "вЂњ": '"',
    "вЂќ": '"',
    "вЂ“": "-",
    "вЂ”": "-",
    "вЂ¦": "...",
    "в€’": "-",
    "В·": "·",
    "В©": "©",
    "В°": "°",
    "в‰¤": "<=",
    "в‰Ґ": ">=",
}


@dataclass(frozen=True)
class SourceRow:
    source_name: str
    output_name: str
    chars: int
    status: str
    notes: str = ""


@dataclass(frozen=True)
class ChunkRow:
    chunk_id: str
    path: str
    pages: list[int]
    heading: str
    chars: int
    excerpt: str


def fix_text(text: str) -> str:
    if _fix_text is not None:
        text = _fix_text(text)
    for bad, good in COMMON_MOJIBAKE.items():
        text = text.replace(bad, good)
    return text


def clean_line(line: str) -> str:
    line = line.replace("\u00a0", " ")
    line = line.replace("\xad", "")
    line = line.replace("\t", " ")
    line = fix_text(line)
    line = re.sub(r"[ ]{2,}", " ", line)
    return line.strip()


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xad", "")
    text = fix_text(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def slugify(value: str) -> str:
    original = fix_text(value)
    value = fix_text(value)
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    value = value.strip("._-")
    value = value or "book"
    if len(value) > MAX_SLUG_LEN:
        digest = hashlib.sha1(original.encode("utf-8")).hexdigest()[:10]
        keep = max(16, MAX_SLUG_LEN - len(digest) - 1)
        value = f"{value[:keep].rstrip('._-')}_{digest}"
    return value


def load_source_rows(raw_dir: Path) -> list[SourceRow]:
    manifest_path = raw_dir / "manifest.json"
    if manifest_path.exists():
        rows = json.loads(manifest_path.read_text(encoding="utf-8"))
        return [
            SourceRow(
                source_name=str(row.get("source_name") or row.get("output_name") or ""),
                output_name=str(row.get("output_name") or ""),
                chars=int(row.get("chars") or 0),
                status=str(row.get("status") or "ok"),
                notes=str(row.get("notes") or ""),
            )
            for row in rows
            if str(row.get("status") or "ok") == "ok" and str(row.get("output_name") or "").endswith(".txt")
        ]
    return [
        SourceRow(
            source_name=path.name,
            output_name=path.name,
            chars=len(path.read_text(encoding="utf-8")),
            status="ok",
        )
        for path in sorted(raw_dir.glob("*.txt"))
    ]


def is_heading_candidate(line: str) -> bool:
    if not line or PAGE_MARKER_RE.match(line):
        return False
    if len(line) > 96:
        return False
    alpha_count = sum(ch.isalpha() for ch in line)
    if alpha_count < 4:
        return False
    if line.endswith((".", ",", ";")) and not line.isupper():
        return False
    if re.match(r"^(chapter|book|part|lesson|section)\s+\d+", line, flags=re.IGNORECASE):
        return True
    if re.match(r"^\d+\s*[\.\)]", line):
        return True
    if line.endswith(":") and len(line.split()) <= 12:
        return True
    uppercase_letters = sum(ch.isupper() for ch in line if ch.isalpha())
    if uppercase_letters and uppercase_letters / alpha_count >= 0.8:
        return True
    words = line.split()
    titled_words = sum(word[:1].isupper() for word in words if word and word[0].isalnum())
    if 1 <= len(words) <= 10 and titled_words == len(words):
        return True
    return False


def pretty_title(source_name: str) -> str:
    title = Path(source_name).stem
    title = fix_text(title)
    title = title.replace("_", " ")
    title = re.sub(r"\s+", " ", title).strip()
    return title


def render_markdown_book(title: str, source_name: str, raw_text: str) -> str:
    lines = [clean_line(line) for line in clean_text(raw_text).splitlines()]
    out: list[str] = [f"# {title}", "", f"Source text: `{fix_text(source_name)}`", ""]
    paragraph_parts: list[str] = []
    i = 0

    def flush_paragraph() -> None:
        nonlocal paragraph_parts
        if not paragraph_parts:
            return
        joined = ""
        for part in paragraph_parts:
            if not joined:
                joined = part
            elif joined.endswith("-") and part[:1].islower():
                joined = joined[:-1] + part
            else:
                joined += " " + part
        joined = re.sub(r"\s+", " ", joined).strip()
        if joined:
            out.append(joined)
            out.append("")
        paragraph_parts = []

    while i < len(lines):
        line = lines[i]
        page_match = PAGE_MARKER_RE.match(line)
        if page_match:
            flush_paragraph()
            out.append(f"## Page {page_match.group(1)}")
            out.append("")
            i += 1
            continue
        if not line:
            flush_paragraph()
            i += 1
            continue
        if is_heading_candidate(line):
            flush_paragraph()
            cluster = [line.strip(" :")]
            j = i + 1
            while j < len(lines):
                candidate = lines[j]
                if not candidate or PAGE_MARKER_RE.match(candidate) or not is_heading_candidate(candidate):
                    break
                if len(cluster) >= 3:
                    break
                cluster.append(candidate.strip(" :"))
                j += 1
            heading = re.sub(r"\s+", " ", " ".join(cluster)).strip()
            out.append(f"### {heading}")
            out.append("")
            i = j
            continue
        paragraph_parts.append(line)
        i += 1

    flush_paragraph()
    return "\n".join(out).strip() + "\n"


def extract_heading_index(markdown_text: str, limit: int = 120) -> list[dict[str, object]]:
    headings: list[dict[str, object]] = []
    current_page: int | None = None
    for line in markdown_text.splitlines():
        page_match = re.match(r"^## Page (\d+)$", line.strip())
        if page_match:
            current_page = int(page_match.group(1))
            continue
        if line.startswith("### "):
            heading = line[4:].strip()
            if heading:
                headings.append({"page": current_page, "heading": heading})
        if len(headings) >= limit:
            break
    return headings


def find_keyword_hits(raw_text: str, terms: Iterable[str], per_term: int = 5) -> dict[str, list[dict[str, object]]]:
    lines = [clean_line(line) for line in clean_text(raw_text).splitlines()]
    hits: dict[str, list[dict[str, object]]] = {}
    current_page: int | None = None
    for line in lines:
        page_match = PAGE_MARKER_RE.match(line)
        if page_match:
            current_page = int(page_match.group(1))
            continue
        if not line:
            continue
        lowered = line.lower()
        for term in terms:
            bucket = hits.setdefault(term, [])
            if len(bucket) >= per_term:
                continue
            if term.lower() in lowered:
                bucket.append({"page": current_page, "excerpt": line[:220]})
    return hits


def iter_sections(markdown_text: str) -> Iterable[tuple[str, list[int], str]]:
    current_heading = "Opening"
    current_pages: list[int] = []
    current_lines: list[str] = []

    def flush():
        nonlocal current_lines, current_pages
        if current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                yield (current_heading, list(current_pages), body)
        current_lines = []
        current_pages = []

    for line in markdown_text.splitlines():
        page_match = re.match(r"^## Page (\d+)$", line.strip())
        if page_match:
            page_num = int(page_match.group(1))
            current_pages.append(page_num)
            current_lines.append(line)
            continue
        if line.startswith("### "):
            yield from flush()
            current_heading = line[4:].strip() or "Section"
            current_lines = [line]
            continue
        current_lines.append(line)
    yield from flush()


def chunk_markdown_book(title: str, source_name: str, markdown_text: str, chunk_dir: Path) -> list[ChunkRow]:
    chunk_dir.mkdir(parents=True, exist_ok=True)
    rows: list[ChunkRow] = []
    buffer_sections: list[tuple[str, list[int], str]] = []
    buffer_chars = 0
    chunk_index = 1

    def write_chunk() -> None:
        nonlocal buffer_sections, buffer_chars, chunk_index
        if not buffer_sections:
            return
        pages: list[int] = []
        for _, section_pages, _ in buffer_sections:
            pages.extend(section_pages)
        unique_pages = sorted(set(pages))
        heading = buffer_sections[0][0]
        page_label = "na"
        if unique_pages:
            page_label = f"p{unique_pages[0]:04d}"
            if len(unique_pages) > 1:
                page_label = f"{page_label}-p{unique_pages[-1]:04d}"
        chunk_name = f"chunk_{chunk_index:04d}_{page_label}.md"
        content_lines = [
            f"# {title}",
            "",
            f"- Source text: `{fix_text(source_name)}`",
            f"- Chunk: {chunk_index}",
            f"- First heading: {heading}",
            f"- Pages: {', '.join(str(p) for p in unique_pages) if unique_pages else 'n/a'}",
            "",
        ]
        content_body = "\n\n".join(section_body.strip() for _, _, section_body in buffer_sections).strip()
        for _, _, section_body in buffer_sections:
            content_lines.append(section_body.strip())
            content_lines.append("")
        rendered = "\n".join(content_lines).strip() + "\n"
        path = chunk_dir / chunk_name
        path.write_text(rendered, encoding="utf-8")
        rows.append(
            ChunkRow(
                chunk_id=f"{chunk_index:04d}",
                path=str(path),
                pages=unique_pages,
                heading=heading,
                chars=len(rendered),
                excerpt=re.sub(r"\s+", " ", content_body)[:320],
            )
        )
        chunk_index += 1
        buffer_sections = []
        buffer_chars = 0

    for section in iter_sections(markdown_text):
        heading, pages, body = section
        section_chars = len(body)
        if buffer_sections and buffer_chars + section_chars > MAX_CHUNK_CHARS:
            write_chunk()
        buffer_sections.append((heading, pages, body))
        buffer_chars += section_chars
        if buffer_chars >= MAX_CHUNK_CHARS:
            write_chunk()

    write_chunk()
    return rows


def write_book_guide(
    title: str,
    source_name: str,
    normalized_path: Path,
    markdown_text: str,
    raw_text: str,
    chunk_rows: list[ChunkRow],
    guide_path: Path,
) -> dict[str, object]:
    headings = extract_heading_index(markdown_text)
    keyword_hits = find_keyword_hits(raw_text, DEFAULT_KEYWORD_TERMS)
    lines = [
        f"# {title}",
        "",
        f"- Source text: `{fix_text(source_name)}`",
        f"- Normalized book: `{normalized_path}`",
        f"- Chunk count: {len(chunk_rows)}",
        "",
        "## How To Use",
        "",
        "- Start with the heading index to find likely sections.",
        "- Use the chunk files for bounded agent inspection and quoting.",
        "- Use keyword anchors to jump to pages before reading full chunks.",
        "",
        "## Heading Index",
        "",
    ]
    if headings:
        for item in headings:
            page = item["page"]
            heading = item["heading"]
            if page is None:
                lines.append(f"- {heading}")
            else:
                lines.append(f"- Page {page}: {heading}")
    else:
        lines.append("- No stable heading index detected.")

    lines.extend(["", "## Keyword Anchors", ""])
    rendered_terms = 0
    for term in DEFAULT_KEYWORD_TERMS:
        term_hits = keyword_hits.get(term, [])
        if not term_hits:
            continue
        rendered_terms += 1
        lines.append(f"### {term}")
        lines.append("")
        for hit in term_hits:
            page = hit["page"]
            excerpt = hit["excerpt"]
            if page is None:
                lines.append(f"- {excerpt}")
            else:
                lines.append(f"- Page {page}: {excerpt}")
        lines.append("")
    if rendered_terms == 0:
        lines.append("- No default keyword anchors were detected.")
        lines.append("")

    lines.extend(["## First Chunks", ""])
    for chunk in chunk_rows[:12]:
        page_label = ", ".join(str(p) for p in chunk.pages) if chunk.pages else "n/a"
        lines.append(f"- Chunk {chunk.chunk_id} | Pages {page_label} | {chunk.heading}")
    guide_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "guide_path": str(guide_path),
        "heading_count": len(headings),
        "keyword_terms_with_hits": rendered_terms,
    }


def write_readme(out_dir: Path, catalog_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Text Inspection Corpus",
        "",
        "This directory contains cleaned Markdown books and chunked excerpts built from the raw extracted text corpus.",
        "",
        "## Layout",
        "",
        "- `normalized_books/`: full-book cleaned Markdown with page and heading anchors",
        "- `guides/`: per-book scan guides with heading indexes and keyword anchors",
        "- `chunks/`: per-book chunk files sized for agent inspection",
        "- `catalog.json`: machine-readable summary of books and chunk coverage",
        "- `chunk_index.jsonl`: one line per chunk for simple retrieval/search tooling",
        "",
        "## Search",
        "",
        "Use the helper script to query the chunk index:",
        "",
        "`python scripts/search_text_inspection_corpus.py \"ascendant ruler\" --index \"C:\\Users\\sabaa\\Downloads\\codexhorary\\extracted_text_docs\\new_sources_inspection\\chunk_index.jsonl\" --limit 5`",
        "",
        "## Books",
        "",
        "| Title | Source | Chunks | Characters | Guide | Notes |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in catalog_rows:
        lines.append(
            f"| {row['title']} | {row['source_name']} | {row['chunk_count']} | {row['source_chars']} | {row.get('guide_path', '')} | {row.get('notes', '') or ''} |"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_corpus(raw_dir: Path, out_dir: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    normalized_dir = out_dir / "normalized_books"
    guides_dir = out_dir / "guides"
    chunks_dir = out_dir / "chunks"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    guides_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    catalog_rows: list[dict[str, object]] = []
    chunk_index_rows: list[dict[str, object]] = []
    for source_row in load_source_rows(raw_dir):
        source_path = raw_dir / source_row.output_name
        if not source_path.exists():
            continue
        title = pretty_title(source_row.source_name)
        slug = slugify(source_row.output_name)
        raw_text = source_path.read_text(encoding="utf-8")
        markdown_text = render_markdown_book(title, source_row.source_name, raw_text)
        normalized_path = normalized_dir / f"{slugify(title)}.md"
        normalized_path.write_text(markdown_text, encoding="utf-8")
        chunk_rows = chunk_markdown_book(title, source_row.source_name, markdown_text, chunks_dir / slug)
        guide_path = guides_dir / f"{slugify(title)}.md"
        guide_meta = write_book_guide(title, source_row.source_name, normalized_path, markdown_text, raw_text, chunk_rows, guide_path)
        for chunk in chunk_rows:
            chunk_index_rows.append(
                {
                    "title": title,
                    "source_name": fix_text(source_row.source_name),
                    "chunk_id": chunk.chunk_id,
                    "path": chunk.path,
                    "pages": chunk.pages,
                    "heading": chunk.heading,
                    "chars": chunk.chars,
                    "excerpt": chunk.excerpt,
                }
            )
        catalog_rows.append(
            {
                "title": title,
                "source_name": fix_text(source_row.source_name),
                "output_name": source_row.output_name,
                "source_chars": source_row.chars,
                "normalized_book_path": str(normalized_path),
                "chunk_count": len(chunk_rows),
                "guide_path": str(guide_path),
                "heading_count": guide_meta["heading_count"],
                "keyword_terms_with_hits": guide_meta["keyword_terms_with_hits"],
                "chunks": [asdict(row) for row in chunk_rows],
                "notes": source_row.notes,
            }
        )
    return catalog_rows, chunk_index_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    raw_dir = args.raw.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog_rows, chunk_index_rows = build_corpus(raw_dir, out_dir)
    (out_dir / "catalog.json").write_text(json.dumps(catalog_rows, indent=2), encoding="utf-8")
    chunk_index_path = out_dir / "chunk_index.jsonl"
    with chunk_index_path.open("w", encoding="utf-8") as handle:
        for row in chunk_index_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_readme(out_dir, catalog_rows)
    print(f"Built text inspection corpus in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
