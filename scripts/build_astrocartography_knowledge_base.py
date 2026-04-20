"""
Build a repo-local Astrocartography knowledge base from the extracted book corpus.

Inputs:
- horary_knowledge/astrocartography_books_text/*.txt

Outputs:
- horary_knowledge/astrocartography_knowledge_base/README.md
- horary_knowledge/astrocartography_knowledge_base/catalog.json
- horary_knowledge/astrocartography_knowledge_base/normalized_books/*.md
- horary_knowledge/astrocartography_knowledge_base/guides/*.md
- horary_knowledge/astrocartography_knowledge_base/reference/*.md

The goal is not to create perfect scholarly editions. The goal is to produce
cleaner, markdown-friendly files that are easier for AI agents to scan,
retrieve from, and cite while planning the Astrocartography feature.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

try:  # Optional cleanup helper; available on this machine but not required.
    from ftfy import fix_text as _fix_text
except Exception:  # pragma: no cover - optional dependency
    _fix_text = None


RAW_DIR = Path(r"C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\astrocartography_books_text")
OUT_DIR = Path(r"C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\astrocartography_knowledge_base")
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
        key="hermes_map_interpretation",
        source_name="Astrocartography_Map_Interpretation_Hermes_Astrology_z-library.sk_1lib.sk_z-lib.sk.txt",
        title="Astrocartography Map Interpretation (Hermes Astrology)",
        role="Interpretation encyclopedia",
        relevance="high",
        preferred_use="Use for line meanings, angle meanings, and crossing interpretations.",
        scan_notes=(
            "Best source for quick explanatory copy about planets, angles, and crossings.",
            "Has repetitive structure, which makes retrieval easier but also means it can sound generic.",
            "Useful for building the first-pass interpretation library, not for proving the method.",
        ),
        keyword_terms=(
            "Sun Line",
            "Moon Line",
            "Mercury Line",
            "Venus Line",
            "Mars Line",
            "Jupiter Line",
            "Saturn Line",
            "Uranus Line",
            "Neptune Line",
            "Pluto Line",
            "North Node Line",
            "Chiron Line",
            "AC LINE",
            "DC LINE",
            "MC LINE",
            "IC LINE",
            "LINE CROSSINGS",
        ),
    ),
    BookSpec(
        key="dan_furst_best_places",
        source_name="Finding_Your_Best_Places_Using_Astrocartography_to_Navigate_Your_Life_Dan_Fursts_Astrocartography_Book_1_Dan_Furst_z-library.sk_1lib.sk_z-lib.sk.txt",
        title="Finding Your Best Places",
        role="Conceptual and practical field guide",
        relevance="high",
        preferred_use="Use for workflow, line range assumptions, relocation vs. local-space distinctions, and user-facing guidance.",
        scan_notes=(
            "Best source for how a reader should actually use maps in life decisions.",
            "Strong on local space, relocation astrology, line crossings, and practical caveats.",
            "Useful for product decisions because it frames astrocartography as a decision aid, not a magic selector.",
        ),
        keyword_terms=(
            "TABLE OF CONTENTS",
            "Relocation Astrology",
            "Local Space Astrology",
            "Astro*Carto*Graphy",
            "Ascendant",
            "Descendant",
            "Midheaven",
            "Nadir",
            "parans",
            "effective range",
            "If Your Best Lines Aren't Near You",
        ),
    ),
    BookSpec(
        key="lewis_guttman_book_of_maps",
        source_name="The_AstroCartoGraphy_Book_of_Maps_-_The_Astrology_of_Relocation_How_136_Famous_People_Found_Their_Places_Jim_Lewis_Arielle_Guttman_z-library.sk_1lib.sk_z-lib.sk.txt",
        title="The Astro*Carto*Graphy Book of Maps",
        role="Case-study atlas and historical reference",
        relevance="high",
        preferred_use="Use for evidence patterns, angular framing, and examples of how lines were linked to places and life events.",
        scan_notes=(
            "The extraction is noisier than the other astrocartography books, but the conceptual pages are still useful.",
            "Best used for examples, case-study patterns, and the original Jim Lewis framing.",
            "Not the best source for fast definitions; use the Hermes and Dan Furst books first.",
        ),
        keyword_terms=(
            "angular positions",
            "Ascendant",
            "Descendant",
            "Midheaven",
            "IC",
            "Crossings",
            "Venus line",
            "Jupiter line",
            "Astro*Carto*Graphy",
        ),
    ),
    BookSpec(
        key="dictionary_of_astrology",
        source_name="Dictionary_of_Astrology_D._Lee_z-library.sk_1lib.sk_z-lib.sk.txt",
        title="Dictionary of Astrology",
        role="Supporting terminology reference",
        relevance="medium",
        preferred_use="Use for generic astrology vocabulary when the astrocartography books assume prior knowledge.",
        scan_notes=(
            "Broad reference source rather than an astrocartography source.",
            "Useful to fill term gaps like angularity, houses, signs, and chart components.",
            "Search directly for terms rather than reading top to bottom.",
        ),
        keyword_terms=(
            "Ascendant",
            "Descendant",
            "Midheaven",
            "IC",
            "houses",
            "mundane",
            "relocation",
        ),
    ),
    BookSpec(
        key="astrology_of_death",
        source_name="The_Astrology_of_Death_Richard_Houck_z-library.sk_1lib.sk_z-lib.sk.txt",
        title="The Astrology of Death",
        role="Tangential supporting source",
        relevance="low",
        preferred_use="Treat as lower-priority support; it is not a primary astrocartography book.",
        scan_notes=(
            "Relevant mainly if the future feature expands into crisis, mortality, or event relocation casework.",
            "Not needed for the Astrocartography MVP.",
            "Keep indexed so agents know it exists, but do not let it dominate feature design.",
        ),
        keyword_terms=(
            "TABLE OF CONTENTS",
            "Introduction",
            "Theory",
            "Application",
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
    if len(line) > 90:
        return False
    alpha_count = sum(ch.isalpha() for ch in line)
    if alpha_count < 4:
        return False
    if line.endswith((".", ",", ";")) and not line.isupper():
        return False
    if re.match(r"^\d+\s*[\.\)]", line):
        return True
    if line.endswith(":") and len(line.split()) <= 12:
        return True
    uppercase_letters = sum(ch.isupper() for ch in line if ch.isalpha())
    if uppercase_letters and uppercase_letters / alpha_count >= 0.8:
        return True
    words = line.split()
    titled_words = sum(word[:1].isupper() for word in words if word and word[0].isalnum())
    if 1 <= len(words) <= 8 and titled_words == len(words):
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


def extract_heading_index(raw_text: str, limit: int = 80) -> list[dict[str, object]]:
    lines = [clean_line(line) for line in clean_text(raw_text).splitlines()]
    headings: list[dict[str, object]] = []
    page = None
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


def find_keyword_hits(raw_text: str, terms: tuple[str, ...], per_term: int = 4) -> dict[str, list[dict[str, object]]]:
    lines = [clean_line(line) for line in clean_text(raw_text).splitlines()]
    hits: dict[str, list[dict[str, object]]] = {}
    page = None
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


REFERENCE_DOCS = {
    "01_core_concepts.md": dedent(
        """
        # Core Concepts

        Astrocartography maps a natal chart onto the Earth so that planetary power points can be read geographically rather than only in the birth-place chart.

        ## What The Corpus Agrees On

        - Astrocartography is a locational astrology method, not a replacement for the natal chart.
        - The map is built from the natal chart plus the four angles: Ascendant, Descendant, Midheaven, and IC/Nadir.
        - The same birth data can produce multiple useful location views: astrocartography lines, relocation charts, and local-space lines.
        - The method is strongest when used to narrow possibilities, compare locations, and explain why a place feels supportive or difficult.
        - The corpus repeatedly warns against treating one map line as an automatic guarantee of success.

        ## The Four Angular Frames

        - `AC / Ascendant`: identity, embodiment, first impression, self-projection, personal style.
        - `DC / Descendant`: partnership, clients, collaboration, attraction, conflict through other people.
        - `MC / Midheaven`: vocation, visibility, reputation, public trajectory.
        - `IC / Nadir`: home, roots, family, inner security, psychological base.

        ## The Practical Reading Order

        1. Start with the client goal.
        2. Identify the most relevant planets for that goal.
        3. Check which angle those planets occupy in a target location.
        4. Check nearby line crossings / parans.
        5. Recast a relocation chart before making a strong judgment.
        6. Add timing later through transits or progressed techniques rather than overloading the first pass.
        """
    ).strip()
    + "\n",
    "02_planetary_and_angular_reference.md": dedent(
        """
        # Planetary And Angular Reference

        ## Planet Baselines

        | Body | Core themes | Common upside | Common caution |
        | --- | --- | --- | --- |
        | Sun | identity, vitality, purpose | confidence, leadership, recognition | ego inflation, pressure to perform |
        | Moon | emotion, belonging, care | intuition, family ties, receptivity | volatility, moodiness, dependency |
        | Mercury | language, trade, learning | writing, networking, teaching, sales | nervousness, scattered focus |
        | Venus | love, beauty, harmony | attraction, art, diplomacy, ease | indulgence, passivity, vanity |
        | Mars | action, heat, courage | initiative, athletic drive, boldness | conflict, haste, irritation |
        | Jupiter | growth, opportunity, meaning | expansion, generosity, teaching, luck | excess, overconfidence |
        | Saturn | structure, duty, realism | discipline, mastery, endurance | heaviness, isolation, delay |
        | Uranus | disruption, innovation, freedom | breakthrough, independence, reinvention | instability, shock, restlessness |
        | Neptune | vision, spirituality, imagination | inspiration, compassion, artistry | confusion, glamour, escapism |
        | Pluto | intensity, power, regeneration | deep transformation, strategic force | obsession, control struggles |
        | North Node | development, pull toward growth | meaningful contacts, future-facing movement | over-identifying with destiny language |
        | Chiron | wound, healing, teaching through pain | insight, integration, mentoring | reopening unresolved pain |

        ## Angle Modifiers

        | Angle | Interprets the planet through | User-facing shorthand |
        | --- | --- | --- |
        | AC | selfhood, body, projection, personal identity | what I become here |
        | DC | partnership, clients, allies, opponents | who I meet here |
        | MC | career, reputation, calling, public outcomes | what I do here |
        | IC | home, roots, family, internal safety | how I live here |
        """
    ).strip()
    + "\n",
    "03_techniques_and_ranges.md": dedent(
        """
        # Techniques And Ranges

        ## Three Related Methods In The Corpus

        - `Astrocartography`: world map of planetary lines derived from natal planets and the four angles.
        - `Relocation Astrology`: recast the chart for a new city while keeping the birth moment fixed.
        - `Local Space Astrology`: project directional planetary lines outward from the birthplace.

        ## Crossings / Parans

        - Crossings happen when two planetary-angular conditions meet in the map.
        - Dan Furst treats them as powerful blended zones and explicitly names them as parans.
        - The Lewis/Guttman material treats crossings as important composite locations, especially in case studies.
        - Crossings should be surfaced as combinations, not as isolated single-planet meanings.

        ## Effective Range

        The corpus does not give one perfectly stable number:

        - Hermes-style interpretation text mentions roughly `150 miles / 250 km`.
        - Dan Furst reports a looser consensus around `300 miles / 500 km`, with some practitioners going wider.

        ## Product Default Recommendation

        - Primary interpretation radius: `300 km`
        - Extended influence radius: `500 km`
        - Crossing radius: same default as lines, but rank more strongly when the user is close to the exact crossing
        """
    ).strip()
    + "\n",
    "04_glossary.md": dedent(
        """
        # Glossary

        - `Astrocartography`: Locational astrology method that maps natal planetary power points across the Earth.
        - `AC / Ascendant`: Eastern horizon; identity, embodiment, self-projection.
        - `DC / Descendant`: Western horizon; partnership, clients, attraction, negotiation.
        - `MC / Midheaven`: Highest point in the chart; vocation, public image, reputation.
        - `IC / Nadir`: Lower root of the chart; home, family, inner life, security.
        - `Relocation chart`: Natal chart recalculated for another location without changing the birth moment.
        - `Local space`: Locational technique projecting planetary directions from the birthplace outward.
        - `Paran`: Traditional term used in the corpus for crossings / co-angular relationships mapped geographically.
        """
    ).strip()
    + "\n",
    "05_feature_notes.md": dedent(
        """
        # Feature Notes

        ## Recommended MVP Scope

        - Show world lines for selected bodies and four angles.
        - Let the user search a city and see the nearest lines plus distance.
        - Explain each nearby line in plain language using a corpus-backed interpretation library.
        - Show crossings / parans when relevant.
        - Recast a relocation chart for the selected city.
        - Support side-by-side city comparison.

        ## Inputs

        - Birth date
        - Exact birth time
        - Birthplace coordinates / timezone
        - Optional goal: career, love, home, creativity, healing, study, travel
        """
    ).strip()
    + "\n",
}


def write_reference_docs(reference_dir: Path) -> None:
    reference_dir.mkdir(parents=True, exist_ok=True)
    for name, content in REFERENCE_DOCS.items():
        (reference_dir / name).write_text(content, encoding="utf-8")


def write_readme(destination: Path, catalog_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Astrocartography Knowledge Base",
        "",
        "This directory is a cleaned, AI-oriented layer built from the raw extracted astrocartography book corpus.",
        "",
        "## Layout",
        "",
        "- `normalized_books/`: full-book markdown versions with page headings and flatter paragraphs",
        "- `guides/`: fast-scan per-book guides with role, relevance, headings, and keyword anchors",
        "- `reference/`: distilled concept docs for implementation work",
        "- `catalog.json`: machine-readable summary of the generated corpus",
        "",
        "## Recommended Reading Order",
        "",
        "1. `reference/01_core_concepts.md`",
        "2. `reference/02_planetary_and_angular_reference.md`",
        "3. `reference/03_techniques_and_ranges.md`",
        "4. `reference/05_feature_notes.md`",
        "5. `guides/hermes_map_interpretation.md`",
        "6. `guides/dan_furst_best_places.md`",
        "7. `guides/lewis_guttman_book_of_maps.md`",
        "",
        "## Source Coverage",
        "",
        "| Book | Role | Relevance | Best use |",
        "| --- | --- | --- | --- |",
    ]
    for row in catalog_rows:
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
        normalized_name = slugify(book.key) + ".md"
        normalized_path = normalized_dir / normalized_name
        normalized_markdown = render_markdown_book(book, raw_text)
        normalized_path.write_text(normalized_markdown, encoding="utf-8")

        guide_name = slugify(book.key) + ".md"
        guide_path = guides_dir / guide_name
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
    write_reference_docs(out_dir / "reference")
    write_readme(out_dir / "README.md", catalog_rows)
    (out_dir / "catalog.json").write_text(json.dumps(catalog_rows, indent=2), encoding="utf-8")

    print(f"Built Astrocartography knowledge base in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
