"""
Build a repo-local mundane astrology knowledge base from the current source corpus.

Inputs:
- horary_knowledge/mundane_books_text/*.txt
- horary_knowledge/Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt

Outputs:
- horary_knowledge/mundane_knowledge_base/README.md
- horary_knowledge/mundane_knowledge_base/catalog.json
- horary_knowledge/mundane_knowledge_base/normalized_books/*.md
- horary_knowledge/mundane_knowledge_base/guides/*.md
- horary_knowledge/mundane_knowledge_base/summaries/*.md
- horary_knowledge/mundane_knowledge_base/reference/*.md

The goal is to create a stable, source-governed study workspace before any
mundane runtime assets or scoring models are designed.
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


REPO_ROOT = Path(__file__).resolve().parents[1]
HORARY_KNOWLEDGE_DIR = REPO_ROOT / "horary_knowledge"
OUT_DIR = HORARY_KNOWLEDGE_DIR / "mundane_knowledge_base"
PAGE_MARKER_RE = re.compile(r"^=== Page (\d+) ===$")
SECTION_MARKER_RE = re.compile(r"^=== (.+) ===$")


@dataclass(frozen=True)
class BookSpec:
    key: str
    source_relpath: str
    title: str
    role: str
    relevance: str
    preferred_use: str
    scan_notes: tuple[str, ...]
    keyword_terms: tuple[str, ...]


BOOKS = (
    BookSpec(
        key="bonatti_mundane_astrology",
        source_relpath=(
            "mundane_books_text/"
            "Bonatti_on_Mundane_Astrology_Guido_Bonattis_Book_of_Astronomy_"
            "Treatise_4_8.1_10_Conjunctions_Revolutions_Weat_fdd3953fa4.txt"
        ),
        title="Bonatti on Mundane Astrology",
        role="Traditional doctrine source for conjunctions, revolutions, weather, and collective judgment",
        relevance="high",
        preferred_use="Use for formal doctrine on conjunction cycles, revolutions, weather, and classical mundane judgment structure.",
        scan_notes=(
            "This should be treated as the strongest traditional-source anchor in the current mundane set.",
            "Best first source for formal chart classes and judgment logic rather than modern examples or product phrasing.",
            "Some extraction noise remains, but the text layer is strong enough for structured reference work.",
        ),
        keyword_terms=(
            "conjunction",
            "revolution",
            "weather",
            "eclipse",
            "ingress",
            "king",
            "nation",
            "war",
        ),
    ),
    BookSpec(
        key="green_raphael_carter_mundane_astrology",
        source_relpath=(
            "mundane_books_text/"
            "Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_"
            "Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt"
        ),
        title="Mundane Astrology: The Astrology of Nations and States",
        role="Survey source for national astrology, houses, eclipses, political framing, and event domains",
        relevance="high",
        preferred_use="Use for practical signification mapping across houses, planets, eclipses, nations, and political astrology.",
        scan_notes=(
            "This is the best broad survey source in the current set and should help define the taxonomy of mundane event domains.",
            "Green and Raphael are useful for systematic signification passes; Carter is useful for reflective political framing.",
            "Useful for product taxonomy and doctrine summaries because it spans several authors in one volume.",
        ),
        keyword_terms=(
            "nation",
            "state",
            "political",
            "eclipse",
            "war",
            "peace",
            "earthquake",
            "house",
        ),
    ),
    BookSpec(
        key="watters_judgment_of_events",
        source_relpath="Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt",
        title="Horary Astrology and the Judgment of Events",
        role="Bridge source from horary judgment into event and mundane work",
        relevance="high",
        preferred_use="Use for the bridge between horary-style judgment and mundane/event charts, especially eclipses, war charts, and national significations.",
        scan_notes=(
            "This is not a pure mundane textbook, but it already contains explicit mundane sections and should be used as a bridge source.",
            "Strong for eclipse activation, war-chart framing, and event judgment that later became product-facing logic.",
            "This source is especially useful for deciding where horary-style event charts and true mundane charts overlap.",
        ),
        keyword_terms=(
            "mundane",
            "lunation",
            "eclipse",
            "ingress",
            "nation",
            "war",
            "people",
            "king",
        ),
    ),
    BookSpec(
        key="annotated_raphael_mundane_astrology",
        source_relpath=(
            "mundane_books_text/"
            "The_Annotated_Raphael_s_Mundane_Astrology_Anthony_Louis_Robert_T._Cross_"
            "z-library.sk_1lib.sk_z-lib.sk.txt"
        ),
        title="The Annotated Raphael's Mundane Astrology",
        role="Annotated bridge source that modernizes Raphael/Cross with explanatory commentary and worked mundane examples",
        relevance="medium",
        preferred_use="Use for clarified house significations, annotated ingress examples, and modern commentary that links older mundane doctrine to concrete historical cases.",
        scan_notes=(
            "This EPUB extraction is structurally clean and includes both the original text and Anthony Louis' annotations.",
            "Best used as a corroborating bridge source rather than the sole doctrinal authority for a runtime rule.",
            "Especially useful where the annotations restate or modernize older mundane doctrine in clearer language.",
        ),
        keyword_terms=(
            "government",
            "parliament",
            "eclipse",
            "king",
            "war",
            "retrograde",
            "treaty",
            "nation",
        ),
    ),
)


REFERENCE_STUBS = (
    (
        "01_core_concepts.md",
        "Core Concepts",
        (
            "Define mundane astrology in contrast to natal, horary, and relocation work.",
            "Capture the high-level purpose of national, collective, and event judgment.",
        ),
    ),
    (
        "02_chart_types.md",
        "Chart Types",
        (
            "Summarize chart classes such as ingresses, lunations, eclipses, conjunctions, revolutions, weather charts, and war charts.",
            "Record which sources discuss each chart type directly.",
        ),
    ),
    (
        "03_significations.md",
        "Significations",
        (
            "Map houses, planets, rulers, leaders, the people, treasury, enemies, allies, and institutions.",
            "Track where sources agree and where they diverge.",
        ),
    ),
    (
        "04_timing_and_triggers.md",
        "Timing and Triggers",
        (
            "Capture activation logic for eclipses, heavy-planet contacts, angles, conjunction cycles, and other timing structures.",
            "Separate explicit timing doctrine from weaker anecdotal claims.",
        ),
    ),
    (
        "05_event_domains.md",
        "Event Domains",
        (
            "Group doctrines by war, political change, civil unrest, economics, treaties, weather, earthquakes, and public leaders.",
            "Mark which domains are strong enough for future model families.",
        ),
    ),
    (
        "06_national_charts_and_locality.md",
        "National Charts and Locality",
        (
            "Summarize how sources treat capitals, national charts, visible eclipses, and event locality.",
            "Document whether the future product should score countries, capitals, or specific event locations.",
        ),
    ),
    (
        "07_feature_notes.md",
        "Feature Notes",
        (
            "Translate doctrine into product-facing notes without defining weights yet.",
            "List likely API, UI, and benchmark implications for the future mundane layer.",
        ),
    ),
    (
        "08_conflicts_and_open_questions.md",
        "Conflicts and Open Questions",
        (
            "Record unresolved source conflicts, weak doctrines, and items that need more books before promotion into runtime assets.",
            "Keep this file updated before any scoring-model generation begins.",
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
    if not line or PAGE_MARKER_RE.match(line) or SECTION_MARKER_RE.match(line):
        return False
    if len(line) > 96:
        return False
    alpha_count = sum(ch.isalpha() for ch in line)
    if alpha_count < 4:
        return False
    if line.endswith((".", ",", ";")) and not line.isupper():
        return False
    if re.match(r"^(book|chapter|part|section|treatise)\s+\d+", line, flags=re.IGNORECASE):
        return True
    if re.match(r"^\d+\s*[\.\)]", line):
        return True
    if line.endswith(":") and len(line.split()) <= 14:
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
    out: list[str] = [f"# {book.title}", "", f"Source text: `{book.source_relpath}`", ""]
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
        section_match = SECTION_MARKER_RE.match(line)
        if section_match:
            flush_paragraph()
            out.append(f"## {section_match.group(1)}")
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


def extract_heading_index(raw_text: str, limit: int = 120) -> list[dict[str, object]]:
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
        section_match = SECTION_MARKER_RE.match(line)
        if section_match:
            heading = section_match.group(1).strip()
            key = (page, heading)
            if heading and key not in seen:
                seen.add(key)
                headings.append({"page": page, "heading": heading})
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
        if SECTION_MARKER_RE.match(line):
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
        f"- Source file: `{book.source_relpath}`",
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
        "source_relpath": book.source_relpath,
        "role": book.role,
        "relevance": book.relevance,
        "preferred_use": book.preferred_use,
        "guide_path": str(destination),
        "heading_count": len(headings),
        "keyword_hits": {term: len(items) for term, items in keyword_hits.items()},
    }


def write_readme(destination: Path, catalog_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Mundane Knowledge Base",
        "",
        "This directory is a cleaned, AI-oriented layer built from the current mundane astrology source corpus.",
        "",
        "## Layout",
        "",
        "- `normalized_books/`: full-book Markdown versions with page headings and flatter paragraphs",
        "- `guides/`: fast-scan per-book guides with role, relevance, headings, and keyword anchors",
        "- `summaries/`: per-source and merged summaries used to bridge the raw books into doctrine assets",
        "- `reference/`: distilled topic docs and operational notes for the future doctrine layer",
        "- `catalog.json`: machine-readable summary of the generated corpus",
        "",
        "## Recommended Reading Order",
        "",
        "1. `summaries/merged_doctrine_summary.md`",
        "2. `summaries/green_raphael_carter_summary.md`",
        "3. `summaries/bonatti_mundane_summary.md`",
        "4. `summaries/watters_judgment_of_events_summary.md`",
        "5. `guides/green_raphael_carter_mundane_astrology.md`",
        "6. `normalized_books/green_raphael_carter_mundane_astrology.md`",
        "7. `guides/annotated_raphael_mundane_astrology.md`",
        "8. `normalized_books/annotated_raphael_mundane_astrology.md`",
        "9. `guides/bonatti_mundane_astrology.md`",
        "10. `normalized_books/bonatti_mundane_astrology.md`",
        "11. `guides/watters_judgment_of_events.md`",
        "12. `normalized_books/watters_judgment_of_events.md`",
        "",
        "## Source Coverage",
        "",
        "| Book | Role | Relevance | Best use |",
        "| --- | --- | --- | --- |",
    ]
    for row in catalog_rows:
        if "error" in row:
            lines.append(f"| {row['title']} | {row['role']} | {row['relevance']} | missing source file |")
        else:
            lines.append(f"| {row['title']} | {row['role']} | {row['relevance']} | {row['preferred_use']} |")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reference_stubs(reference_dir: Path) -> None:
    reference_dir.mkdir(parents=True, exist_ok=True)
    for filename, title, prompts in REFERENCE_STUBS:
        path = reference_dir / filename
        if path.exists():
            continue
        lines = [
            f"# {title}",
            "",
            "Status: scaffold",
            "",
            "Purpose:",
            "",
        ]
        for prompt in prompts:
            lines.append(f"- {prompt}")
        lines.extend(
            [
                "",
                "Current source set:",
                "",
                "- `horary_knowledge/mundane_books_text/Bonatti_on_Mundane_Astrology_Guido_Bonattis_Book_of_Astronomy_Treatise_4_8.1_10_Conjunctions_Revolutions_Weat_fdd3953fa4.txt`",
                "- `horary_knowledge/mundane_books_text/Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt`",
                "- `horary_knowledge/mundane_books_text/The_Annotated_Raphael_s_Mundane_Astrology_Anthony_Louis_Robert_T._Cross_z-library.sk_1lib.sk_z-lib.sk.txt`",
                "- `horary_knowledge/Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt`",
                "",
                "Notes:",
                "",
                "- Fill this only after reading the normalized books and per-book guides.",
                "- Keep direct page citations or source-file references when asserting doctrine.",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")


def build_catalog(out_dir: Path) -> list[dict[str, object]]:
    normalized_dir = out_dir / "normalized_books"
    guides_dir = out_dir / "guides"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    guides_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for book in BOOKS:
        source_path = HORARY_KNOWLEDGE_DIR / Path(book.source_relpath)
        if not source_path.exists():
            rows.append(
                {
                    "title": book.title,
                    "source_relpath": book.source_relpath,
                    "role": book.role,
                    "relevance": book.relevance,
                    "preferred_use": book.preferred_use,
                    "error": "missing source file",
                }
            )
            continue

        raw_text = source_path.read_text(encoding="utf-8")
        normalized_path = normalized_dir / f"{slugify(book.key)}.md"
        normalized_path.write_text(render_markdown_book(book, raw_text), encoding="utf-8")

        guide_path = guides_dir / f"{slugify(book.key)}.md"
        row = write_book_guide(book, raw_text, guide_path)
        row["normalized_book_path"] = str(normalized_path)
        row["source_chars"] = len(raw_text)
        rows.append(row)

    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog_rows = build_catalog(out_dir)
    write_reference_stubs(out_dir / "reference")
    write_readme(out_dir / "README.md", catalog_rows)
    (out_dir / "catalog.json").write_text(json.dumps(catalog_rows, indent=2), encoding="utf-8")

    print(f"Built Mundane knowledge base in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
