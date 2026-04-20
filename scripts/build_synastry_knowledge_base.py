"""
Build a repo-local synastry knowledge base from the extracted synastry book corpus.

Inputs:
- horary_knowledge/synastry_books_text/*.txt

Outputs:
- horary_knowledge/synastry_knowledge_base/README.md
- horary_knowledge/synastry_knowledge_base/catalog.json
- horary_knowledge/synastry_knowledge_base/normalized_books/*.md
- horary_knowledge/synastry_knowledge_base/guides/*.md

The goal is to convert the raw PDF extractions into cleaner Markdown files
that are easier for AI agents to scan, retrieve from, and cite during later
feature and algorithm work.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

try:  # Optional cleanup helper.
    from ftfy import fix_text as _fix_text
except Exception:  # pragma: no cover - optional dependency
    _fix_text = None


RAW_DIR = Path(r"C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\synastry_books_text")
OUT_DIR = Path(r"C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\synastry_knowledge_base")
PAGE_MARKER_RE = re.compile(r"^=== Page (\d+) ===$")


@dataclass(frozen=True)
class BookSpec:
    key: str
    source_name: str
    title: str
    role: str
    relevance: str
    preferred_use: str
    scan_notes: tuple[str, ...]
    keyword_terms: tuple[str, ...]


BOOKS = (
    BookSpec(
        key="davison_understanding_human_relations",
        source_name="Synastry_Understanding_Human_Relations_Through_Astrology_Ronald_C._Davison_z-library.sk_1lib.sk_z-lib.sk.txt",
        title="Synastry: Understanding Human Relations Through Astrology",
        role="Core synastry doctrine and relationship-judgment source",
        relevance="high",
        preferred_use="Use for pair-comparison principles, relationship promise in the nativity, and classical-style compatibility framing.",
        scan_notes=(
            "Best first-pass source for how a relationship comparison should be grounded in each natal chart before cross-chart judgment.",
            "Useful for turning synastry from loose aspect matching into structured relationship assessment.",
            "Strong source for product rules that need chart-to-chart judgment rather than generic compatibility copy.",
        ),
        keyword_terms=(
            "Marriage and other Relationships as Shown in the Nativity",
            "synastry",
            "Ascendant",
            "Descendant",
            "seventh house",
            "Sun",
            "Moon",
            "Venus",
            "Mars",
            "Saturn",
        ),
    ),
    BookSpec(
        key="arroyo_person_to_person",
        source_name="Person_to_person_Astrology_Stephen_Arroyo_z-library.sk_1lib.sk_z-lib.sk.txt",
        title="Person-to-Person Astrology",
        role="Relational temperament and energy-exchange reference",
        relevance="high",
        preferred_use="Use for relational language, elemental exchange, rising-sign dynamics, and Moon-Venus-Mars compatibility framing.",
        scan_notes=(
            "Best supporting source for user-facing relational language and temperament-based interpretation.",
            "Useful for scoring dimensions such as emotional fit, attraction style, communication tone, and elemental balance.",
            "This should shape explanatory copy and category framing more than hard doctrinal rules.",
        ),
        keyword_terms=(
            "rising sign",
            "Ascendant",
            "elements",
            "Moon",
            "Venus",
            "Mars",
            "compatibility",
            "energy",
            "love",
            "sex",
        ),
    ),
    BookSpec(
        key="march_mcevers_synastry_techniques",
        source_name="The_Only_Way_to_Learn_About_Relationships_Vol._5_Synastry_Techniques_Marion_D._March_Joan_McEvers_z-library.sk_1lib.sk_z-lib.sk.txt",
        title="The Only Way to Learn About Relationships, Vol. 5: Synastry Techniques",
        role="Technique workbook and applied synastry reference",
        relevance="high",
        preferred_use="Use for operational synastry techniques, aspect patterns, overlays, and implementation-oriented lookup material.",
        scan_notes=(
            "Best source for technique-level scanning once the feature needs concrete pairwise interpretation logic.",
            "The extraction is noisier than the Davison book, so use the guides and heading anchors before broad full-text scanning.",
            "Useful for broadening the algorithm beyond a single traditional source and for checking recurring aspect themes.",
        ),
        keyword_terms=(
            "TABLE OF CONTENTS",
            "synastry",
            "Sun",
            "Moon",
            "Mercury",
            "Venus",
            "Mars",
            "Ascendant",
            "house",
            "Saturn",
        ),
    ),
)


def fix_text(text: str) -> str:
    if _fix_text is not None:
        text = _fix_text(text)
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
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    value = value.strip("._-")
    return value or "book"


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
    if re.match(r"^(chapter|part|lesson)\s+\d+", line, flags=re.IGNORECASE):
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


def render_markdown_book(book: BookSpec, raw_text: str) -> str:
    lines = [clean_line(line) for line in clean_text(raw_text).splitlines()]
    out: list[str] = [f"# {book.title}", "", f"Source text: `{book.source_name}`", ""]
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
            heading = " ".join(part for part in cluster if part)
            heading = re.sub(r"\s+", " ", heading).strip()
            out.append(f"### {heading}")
            out.append("")
            i = j
            continue

        paragraph_parts.append(line)
        i += 1

    flush_paragraph()
    return "\n".join(out).strip() + "\n"


def extract_heading_index(raw_text: str, limit: int = 100) -> list[dict[str, object]]:
    lines = [clean_line(line) for line in clean_text(raw_text).splitlines()]
    headings: list[dict[str, object]] = []
    page: int | None = None
    i = 0
    seen: set[tuple[int | None, str]] = set()
    while i < len(lines):
        line = lines[i]
        page_match = PAGE_MARKER_RE.match(line)
        if page_match:
            page = int(page_match.group(1))
            i += 1
            continue
        if is_heading_candidate(line):
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
            key = (page, heading)
            if heading and key not in seen:
                seen.add(key)
                headings.append({"page": page, "heading": heading})
            i = j
            continue
        i += 1
        if len(headings) >= limit:
            break
    return headings


def find_keyword_hits(raw_text: str, terms: tuple[str, ...], per_term: int = 5) -> dict[str, list[dict[str, object]]]:
    lines = [clean_line(line) for line in clean_text(raw_text).splitlines()]
    hits: dict[str, list[dict[str, object]]] = {}
    page: int | None = None
    for line in lines:
        page_match = PAGE_MARKER_RE.match(line)
        if page_match:
            page = int(page_match.group(1))
            continue
        if not line:
            continue
        lowered = line.lower()
        for term in terms:
            bucket = hits.setdefault(term, [])
            if len(bucket) >= per_term:
                continue
            if term.lower() in lowered:
                bucket.append({"page": page, "excerpt": line[:220]})
    return hits


def write_book_guide(book: BookSpec, raw_text: str, destination: Path) -> dict[str, object]:
    headings = extract_heading_index(raw_text)
    keyword_hits = find_keyword_hits(raw_text, book.keyword_terms)

    lines = [
        f"# {book.title}",
        "",
        f"- Source file: `{book.source_name}`",
        f"- Role: {book.role}",
        f"- Relevance: {book.relevance}",
        f"- Primary use: {book.preferred_use}",
        "",
        "## Scan Notes",
        "",
    ]
    for note in book.scan_notes:
        lines.append(f"- {note}")

    lines.extend(["", "## Major Heading Index", ""])
    for item in headings:
        page = item["page"]
        label = item["heading"]
        if page is None:
            lines.append(f"- {label}")
        else:
            lines.append(f"- Page {page}: {label}")
    if not headings:
        lines.append("- No stable heading index was detected from the extracted text.")

    lines.extend(["", "## Keyword Anchors", ""])
    for term in book.keyword_terms:
        lines.append(f"### {term}")
        term_hits = keyword_hits.get(term, [])
        if not term_hits:
            lines.append("- No direct hit captured in the extracted text.")
        else:
            for hit in term_hits:
                page = hit["page"]
                excerpt = hit["excerpt"]
                if page is None:
                    lines.append(f"- {excerpt}")
                else:
                    lines.append(f"- Page {page}: {excerpt}")
        lines.append("")

    destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return {
        "title": book.title,
        "source_name": book.source_name,
        "role": book.role,
        "relevance": book.relevance,
        "preferred_use": book.preferred_use,
        "guide_path": str(destination),
        "heading_count": len(headings),
        "keyword_hits": {term: len(items) for term, items in keyword_hits.items()},
    }


def write_readme(destination: Path, catalog_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Synastry Knowledge Base",
        "",
        "This directory is a cleaned, AI-oriented layer built from the raw extracted synastry book corpus.",
        "",
        "## Layout",
        "",
        "- `normalized_books/`: full-book Markdown versions with page headings and flatter paragraphs",
        "- `guides/`: fast-scan per-book guides with role, relevance, headings, and keyword anchors",
        "- `catalog.json`: machine-readable summary of the generated corpus",
        "",
        "## Recommended Reading Order",
        "",
        "1. `guides/davison_understanding_human_relations.md`",
        "2. `normalized_books/davison_understanding_human_relations.md`",
        "3. `guides/arroyo_person_to_person.md`",
        "4. `normalized_books/arroyo_person_to_person.md`",
        "5. `guides/march_mcevers_synastry_techniques.md`",
        "6. `normalized_books/march_mcevers_synastry_techniques.md`",
        "",
        "## Source Coverage",
        "",
        "| Book | Role | Relevance | Best use |",
        "| --- | --- | --- | --- |",
    ]
    for row in catalog_rows:
        if "error" in row:
            lines.append(
                f"| {row['title']} | {row['role']} | {row['relevance']} | missing source file |"
            )
        else:
            lines.append(
                f"| {row['title']} | {row['role']} | {row['relevance']} | {row['preferred_use']} |"
            )
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_catalog(raw_dir: Path, out_dir: Path) -> list[dict[str, object]]:
    normalized_dir = out_dir / "normalized_books"
    guides_dir = out_dir / "guides"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    guides_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for book in BOOKS:
        source_path = raw_dir / book.source_name
        if not source_path.exists():
            rows.append(
                {
                    "title": book.title,
                    "source_name": book.source_name,
                    "role": book.role,
                    "relevance": book.relevance,
                    "preferred_use": book.preferred_use,
                    "error": "missing source file",
                }
            )
            continue

        raw_text = source_path.read_text(encoding="utf-8")
        normalized_path = normalized_dir / f"{slugify(book.key)}.md"
        normalized_markdown = render_markdown_book(book, raw_text)
        normalized_path.write_text(normalized_markdown, encoding="utf-8")

        guide_path = guides_dir / f"{slugify(book.key)}.md"
        row = write_book_guide(book, raw_text, guide_path)
        row["normalized_book_path"] = str(normalized_path)
        row["source_chars"] = len(raw_text)
        rows.append(row)

    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_DIR)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    raw_dir: Path = args.raw
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog_rows = build_catalog(raw_dir, out_dir)
    write_readme(out_dir / "README.md", catalog_rows)
    (out_dir / "catalog.json").write_text(json.dumps(catalog_rows, indent=2), encoding="utf-8")

    print(f"Built Synastry knowledge base in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
