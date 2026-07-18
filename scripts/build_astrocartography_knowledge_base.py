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
from typing import Any

try:
    from .astrocartography_source_governance import (
        CLAIM_REGISTRY_PATH,
        SOURCE_REGISTRY_PATH,
        load_claim_registry,
        load_source_registry,
        make_chunk_id,
        make_page_id,
        sha256_text,
        validate_claim_registry,
        validate_source_registry,
    )
except ImportError:  # Script execution: python scripts/build_astrocartography_knowledge_base.py
    import sys as _sys

    _scripts_dir = str(Path(__file__).resolve().parent)
    if _scripts_dir not in _sys.path:
        _sys.path.insert(0, _scripts_dir)
    from astrocartography_source_governance import (
        CLAIM_REGISTRY_PATH,
        SOURCE_REGISTRY_PATH,
        load_claim_registry,
        load_source_registry,
        make_chunk_id,
        make_page_id,
        sha256_text,
        validate_claim_registry,
        validate_source_registry,
    )

try:  # Optional cleanup helper; available on this machine but not required.
    from ftfy import fix_text as _fix_text
except Exception:  # pragma: no cover - optional dependency
    _fix_text = None


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "horary_knowledge" / "astrocartography_books_text"
OUT_DIR = REPO_ROOT / "horary_knowledge" / "astrocartography_knowledge_base"
PAGE_MARKER_RE = re.compile(r"^=== Page (\d+) ===$")


@dataclass(frozen=True)
class BookSpec:
    source_id: str
    key: str
    source_name: str
    title: str
    authors: tuple[str, ...]
    year: int
    edition: str
    publisher: str
    role: str
    preferred_use: str
    authority_tier: str
    authority_rank: int
    authority_rationale: str
    default_claim_classification: str
    retrieval_enabled: bool
    retrieval_scopes: tuple[str, ...]
    exclusion_reason: str
    scan_notes: tuple[str, ...]
    keyword_terms: tuple[str, ...]


def load_book_specs(
    source_registry_path: Path = SOURCE_REGISTRY_PATH,
) -> tuple[BookSpec, ...]:
    registry = load_source_registry(source_registry_path)
    errors = validate_source_registry(registry, repo_root=REPO_ROOT)
    if errors:
        raise ValueError("Invalid astrocartography source registry:\n- " + "\n- ".join(errors))

    specs: list[BookSpec] = []
    for row in registry["sources"]:
        bibliography = row["bibliography"]
        authority = row["authority"]
        retrieval = row["retrieval"]
        specs.append(
            BookSpec(
                source_id=row["source_id"],
                key=row["key"],
                source_name=Path(row["extracted"]["repo_path"]).name,
                title=bibliography["title"],
                authors=tuple(bibliography["authors"]),
                year=int(bibliography["year"]),
                edition=bibliography["edition"],
                publisher=bibliography["publisher"],
                role=row["role"],
                preferred_use=row["preferred_use"],
                authority_tier=authority["tier"],
                authority_rank=int(authority["rank"]),
                authority_rationale=authority["rationale"],
                default_claim_classification=row["default_claim_classification"],
                retrieval_enabled=bool(retrieval["enabled"]),
                retrieval_scopes=tuple(retrieval["scopes"]),
                exclusion_reason=retrieval.get("exclusion_reason", ""),
                scan_notes=tuple(row.get("scan_notes") or []),
                keyword_terms=tuple(row.get("keyword_terms") or []),
            )
        )
    return tuple(sorted(specs, key=lambda item: (item.authority_rank, item.source_id)))


BOOKS = load_book_specs()


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


def _join_paragraph_parts(parts: list[str]) -> str:
    joined = ""
    for part in parts:
        if not joined:
            joined = part
        elif joined.endswith("-") and part[:1].islower():
            joined = joined[:-1] + part
        else:
            joined += " " + part
    return re.sub(r"\s+", " ", joined).strip()


def render_book_artifacts(
    book: BookSpec,
    raw_text: str,
) -> tuple[str, list[dict[str, object]]]:
    lines = [clean_line(line) for line in clean_text(raw_text).splitlines()]
    out: list[str] = [
        "<!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->",
        f"<!-- source-id: {book.source_id} -->",
        f"<!-- default-claim-classification: {book.default_claim_classification} -->",
        "",
        f"# {book.title}",
        "",
        f"- Source ID: `{book.source_id}`",
        f"- Source text: `{book.source_name}`",
        f"- Authority: `{book.authority_tier}` (rank {book.authority_rank})",
        f"- Retrieval scopes: {', '.join(f'`{scope}`' for scope in book.retrieval_scopes)}",
        "",
    ]
    chunks: list[dict[str, object]] = []
    paragraph_parts: list[str] = []
    page: int | None = None
    chunk_ordinal = 0
    i = 0

    def flush_paragraph() -> None:
        nonlocal chunk_ordinal, paragraph_parts
        if not paragraph_parts:
            return
        joined = _join_paragraph_parts(paragraph_parts)
        if joined:
            chunk_ordinal += 1
            chunk_id = make_chunk_id(book.source_id, page, chunk_ordinal)
            text_sha256 = sha256_text(joined)
            out.append(f"<!-- chunk-id: {chunk_id} -->")
            out.append(f"<!-- chunk-sha256: {text_sha256} -->")
            out.append(joined)
            out.append("")
            chunks.append(
                {
                    "source_id": book.source_id,
                    "page": page,
                    "page_id": make_page_id(book.source_id, page),
                    "chunk_ordinal": chunk_ordinal,
                    "chunk_id": chunk_id,
                    "text_sha256": text_sha256,
                    "claim_classification": book.default_claim_classification,
                    "authority_tier": book.authority_tier,
                    "authority_rank": book.authority_rank,
                    "retrieval_scopes": list(book.retrieval_scopes),
                    "text": joined,
                }
            )
        paragraph_parts = []

    while i < len(lines):
        line = lines[i]
        page_match = PAGE_MARKER_RE.match(line)
        if page_match:
            flush_paragraph()
            page = int(page_match.group(1))
            chunk_ordinal = 0
            stable_page_id = make_page_id(book.source_id, page)
            out.append(f'<a id="{stable_page_id}"></a>')
            out.append(f"<!-- page-id: {stable_page_id} -->")
            out.append(f"## Page {page}")
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
    return "\n".join(out).strip() + "\n", chunks


def render_markdown_book(book: BookSpec, raw_text: str) -> str:
    markdown, _chunks = render_book_artifacts(book, raw_text)
    return markdown


def extract_heading_index(
    raw_text: str,
    limit: int = 80,
    *,
    source_id: str | None = None,
) -> list[dict[str, object]]:
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
                item: dict[str, object] = {"page": page, "heading": heading}
                if source_id:
                    item["page_id"] = make_page_id(source_id, page)
                headings.append(item)
            i = j
            continue
        i += 1
        if len(headings) >= limit:
            break
    return headings


def keyword_pattern(term: str) -> re.Pattern[str]:
    """Compile a token-bounded pattern, including for short terms such as IC.

    Raw substring matching previously treated the ``ic`` in words such as
    ``publications`` as an IC anchor.  Boundaries are applied only where the
    keyword begins or ends with an alphanumeric character, so literal terms
    such as ``Astro*Carto*Graphy`` continue to work.
    """

    escaped = re.escape(term)
    escaped = escaped.replace(r"\ ", r"\s+")
    prefix = r"(?<![A-Za-z0-9])" if term[:1].isalnum() else ""
    suffix = r"(?![A-Za-z0-9])" if term[-1:].isalnum() else ""
    return re.compile(prefix + escaped + suffix, re.IGNORECASE)


def find_keyword_hits(
    raw_text: str,
    terms: tuple[str, ...],
    per_term: int = 4,
    *,
    source_id: str | None = None,
) -> dict[str, list[dict[str, object]]]:
    lines = [clean_line(line) for line in clean_text(raw_text).splitlines()]
    hits: dict[str, list[dict[str, object]]] = {}
    patterns = {term: keyword_pattern(term) for term in terms}
    page = None
    for line in lines:
        page_match = PAGE_MARKER_RE.match(line)
        if page_match:
            page = int(page_match.group(1))
            continue
        if not line:
            continue
        for term in terms:
            bucket = hits.setdefault(term, [])
            if len(bucket) >= per_term:
                continue
            if patterns[term].search(line):
                item: dict[str, object] = {"page": page, "excerpt": line[:220]}
                if source_id:
                    item["page_id"] = make_page_id(source_id, page)
                bucket.append(item)
    return hits


def write_book_guide(book: BookSpec, raw_text: str, destination: Path) -> dict[str, object]:
    headings = extract_heading_index(raw_text, source_id=book.source_id)
    keyword_hits = find_keyword_hits(
        raw_text,
        book.keyword_terms,
        source_id=book.source_id,
    )

    lines = [
        "<!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->",
        f"<!-- source-id: {book.source_id} -->",
        f"<!-- default-claim-classification: {book.default_claim_classification} -->",
        "",
        f"# {book.title}",
        "",
        f"- Source ID: `{book.source_id}`",
        f"- Source file: `horary_knowledge/astrocartography_books_text/{book.source_name}`",
        f"- Authors: {', '.join(book.authors)}",
        f"- Publication: {book.publisher}, {book.year}; {book.edition}",
        f"- Role: {book.role}",
        f"- Authority: `{book.authority_tier}` (rank {book.authority_rank})",
        f"- Default claim classification: `{book.default_claim_classification}`",
        f"- Retrieval scopes: {', '.join(f'`{scope}`' for scope in book.retrieval_scopes)}",
        f"- Primary use: {book.preferred_use}",
        "",
        "## Authority Note",
        "",
        book.authority_rationale,
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
            lines.append(f"- `{item['page_id']}` — Page {page}: {label}")
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
                    lines.append(f"- `{hit['page_id']}` — Page {page}: {excerpt}")
        lines.append("")

    destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return {
        "source_id": book.source_id,
        "title": book.title,
        "authors": list(book.authors),
        "year": book.year,
        "edition": book.edition,
        "publisher": book.publisher,
        "source_name": book.source_name,
        "role": book.role,
        "preferred_use": book.preferred_use,
        "authority": {
            "tier": book.authority_tier,
            "rank": book.authority_rank,
            "rationale": book.authority_rationale,
        },
        "default_claim_classification": book.default_claim_classification,
        "retrieval": {
            "enabled": book.retrieval_enabled,
            "scopes": list(book.retrieval_scopes),
        },
        "guide_path": f"guides/{destination.name}",
        "heading_count": len(headings),
        "keyword_hits": {term: len(items) for term, items in keyword_hits.items()},
    }


REFERENCE_DOCS = {
    "00_source_governance.md": dedent(
        """
        <!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->
        <!-- document-id: acg-ref-source-governance-v1 -->
        <!-- claim-classification: synthesis -->

        # Source Governance

        The source and claim registries are the authority for this knowledge base:

        - `horary_knowledge/astrocartography_sources/source_registry.json`
        - `horary_knowledge/astrocartography_sources/claim_registry.json`

        A page or chunk ID proves traceability to the local corpus. It does not prove that astrology, a retrospective case interpretation, or a Vox Stella score is scientifically valid.

        ## Authority Order

        1. `acg-src-lewis-guttman-1989` — canonical Astro*Carto*Graphy doctrine.
        2. `acg-src-furst-best-places-2015` — secondary practitioner workflow and variants.
        3. `acg-src-hermes-map-2023` — tertiary explanatory comparison.
        4. `acg-src-lee-dictionary-1968` — generic terminology only.
        5. `acg-src-houck-death-1994` — inventory only; excluded from astrocartography retrieval.

        ## Claim Classes

        - `direct`: faithful report of a named, page-located source.
        - `synthesis`: transparent combination of at least two located sources.
        - `legacy-parity`: product compatibility inferred from legacy artifacts, not astrological doctrine.
        - `experimental`: a Vox Stella hypothesis or product policy requiring independent validation.

        Conflicts stay visible. A lower-tier source does not silently overwrite a higher-tier source, and a product default is not presented as source consensus.
        """
    ).strip()
    + "\n",
    "01_core_concepts.md": dedent(
        """
        <!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->
        <!-- document-id: acg-ref-core-concepts-v2 -->
        <!-- claim-classification: synthesis -->
        <!-- claim-ids: acg-claim-natal-context-controls-expression, acg-claim-four-angles-have-distinct-frames, acg-claim-remote-activation-does-not-require-moving, acg-claim-no-universal-good-bad-planets, acg-claim-advisory-layered-workflow -->

        # Core Concepts

        Astrocartography maps natal planetary angularity geographically. It remains an astrological interpretive method, not an empirically validated location predictor.

        ## Grounded Principles

        - Natal condition modifies every line interpretation. (`direct`; `acg-src-lewis-guttman-1989.page-0011`)
        - MC, ASC, IC, and DSC are distinct frames rather than interchangeable intensity labels. (`direct`; `acg-src-lewis-guttman-1989.page-0014`, `acg-src-furst-best-places-2015.page-0018`)
        - Permanent relocation is not required; relationships with people, interests, or markets connected to a place may activate a location relationship. (`direct`; `acg-src-lewis-guttman-1989.page-0011`, `acg-src-furst-best-places-2015.page-0024`)
        - Lewis rejects universal good/bad planet labels and describes neutral, mixed, crowded, or cancelling regions. (`direct`; `acg-src-lewis-guttman-1989.page-0012`)

        ## The Four Angular Frames

        - `ASC / Ascendant`: direct personal expression, embodiment, identity, and projection.
        - `DSC / Descendant`: relationships and circumstances encountered through others; projection can make difficult planets especially consequential.
        - `MC / Midheaven`: social classification, public role, vocation, and reputation.
        - `IC / Nadir`: foundations, home, family, roots, and livelihood base.

        ## The Practical Reading Order

        1. Start with the user's purpose and the natal condition of the candidate planet.
        2. Identify the exact planet-by-angle expression rather than joining two generic paragraphs.
        3. Label the technique: line, geometric intersection, paran/co-angular relationship, or local-space direction.
        4. Show distance as sensitivity, not a universal hard boundary.
        5. Recast a relocation chart and preserve natal context before making a strong comparison.
        6. Show birth-time uncertainty as a geographic corridor or confidence limit.
        7. Add timing separately and keep the result advisory.

        This reading order is a `synthesis`, not a recovered formula. See `acg-claim-advisory-layered-workflow`.
        """
    ).strip()
    + "\n",
    "02_planetary_and_angular_reference.md": dedent(
        """
        <!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->
        <!-- document-id: acg-ref-planet-angle-v2 -->
        <!-- claim-classification: synthesis -->
        <!-- claim-ids: acg-claim-natal-context-controls-expression, acg-claim-lewis-planetary-location-baselines, acg-claim-lewis-descendant-externalizes-planets, acg-claim-four-angles-have-distinct-frames, acg-claim-explicit-planet-angle-matrix, acg-claim-neptune-ic-has-material-cautions, acg-claim-nodes-require-directional-distinction -->

        # Planetary And Angular Reference

        These rows are compact baselines for retrieval. They are not comparative weights, medical claims, or a substitute for an explicit planet-by-angle interpretation.

        ## Planet Baselines

        | Body | Core themes | Common upside | Common caution | Classification | Source refs |
        | --- | --- | --- | --- | --- | --- |
        | Sun | identity, vitality, purpose | confidence, leadership, recognition | ego inflation, pressure to perform | direct baseline | `acg-src-lewis-guttman-1989.page-0013` |
        | Moon | emotion, belonging, care | intuition, family ties, receptivity | volatility, dependency, over-identification | synthesis | `acg-src-lewis-guttman-1989.page-0013`; `acg-src-furst-best-places-2015.page-0018` |
        | Mercury | language, trade, learning | writing, networking, teaching, sales | nervousness, scattered focus | direct baseline | `acg-src-lewis-guttman-1989.page-0013` |
        | Venus | love, beauty, harmony | attraction, art, diplomacy, ease | indulgence, passivity, excess | direct baseline | `acg-src-lewis-guttman-1989.page-0013` |
        | Mars | action, heat, courage | initiative, athletic drive, boldness | conflict, haste, attacks or accidents | direct baseline | `acg-src-lewis-guttman-1989.page-0013` |
        | Jupiter | growth, opportunity, meaning | prosperity, status, teaching, lucky breaks | excess, complacency, overconfidence | direct baseline | `acg-src-lewis-guttman-1989.page-0013` |
        | Saturn | structure, duty, realism | discipline, mastery, endurance | heaviness, solitude, delay | direct baseline | `acg-src-lewis-guttman-1989.page-0013` |
        | Uranus | disruption, innovation, freedom | breakthrough, independence, reinvention | instability, shock, restlessness | direct baseline | `acg-src-lewis-guttman-1989.page-0014` |
        | Neptune | vision, spirituality, imagination | inspiration, compassion, artistry | confusion, glamour, unreliable foundations | synthesis | `acg-src-lewis-guttman-1989.page-0014`; `acg-src-furst-best-places-2015.page-0055` |
        | Pluto | intensity, power, regeneration | deep transformation, strategic force | obsession, control struggles, coercion | direct baseline | `acg-src-lewis-guttman-1989.page-0014` |
        | North Node | group relationships and developmental pull | future-facing contacts and participation | destiny overstatement | secondary variant | `acg-src-furst-best-places-2015.page-0059`; `acg-src-furst-best-places-2015.page-0060` |
        | Chiron | wound, unutilized gift, teaching through pain | insight, integration, mentoring | reopening unresolved pain | secondary variant | `acg-src-furst-best-places-2015.page-0121` |

        ## Angle Modifiers

        | Angle | Interprets the planet through | User-facing shorthand | Classification | Source refs |
        | --- | --- | --- | --- | --- |
        | AC | selfhood, body, projection, personal identity | what I express here | synthesis | `acg-src-lewis-guttman-1989.page-0014`; `acg-src-furst-best-places-2015.page-0018` |
        | DC | partnership, clients, allies, opponents, projection | who and what I meet here | synthesis | `acg-src-lewis-guttman-1989.page-0014`; `acg-src-furst-best-places-2015.page-0018` |
        | MC | career, reputation, social role, public outcomes | how I am classified publicly here | synthesis | `acg-src-lewis-guttman-1989.page-0014`; `acg-src-furst-best-places-2015.page-0018` |
        | IC | home, roots, family, livelihood foundation | what supports or unsettles my base here | synthesis | `acg-src-lewis-guttman-1989.page-0014`; `acg-src-furst-best-places-2015.page-0018` |

        ## Interpretation Rule

        Generate or curate an explicit planet-by-angle matrix with both supportive and difficult expressions. A generic planet paragraph plus a generic angle suffix is only a fallback summary, not a source-exact interpretation. (`synthesis`; `acg-claim-explicit-planet-angle-matrix`)
        """
    ).strip()
    + "\n",
    "03_techniques_and_ranges.md": dedent(
        """
        <!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->
        <!-- document-id: acg-ref-techniques-ranges-v2 -->
        <!-- claim-classification: synthesis -->
        <!-- claim-ids: acg-claim-distance-doctrines-differ, acg-claim-intersections-and-parans-need-separate-labels, acg-claim-birth-time-uncertainty-reduces-spatial-precision, acg-claim-product-radius-policy -->

        # Techniques And Ranges

        ## Three Related Methods In The Corpus

        - `Astrocartography`: world map of natal planets becoming angular.
        - `Relocation Astrology`: recast the chart for a new location while keeping the birth moment fixed. (`acg-src-furst-best-places-2015.page-0008`)
        - `Local Space Astrology`: a distinct directional technique projected from a chosen origin; do not silently present it as an astrocartography line.

        ## Intersections And Parans

        - A geometric line intersection is a mapped point where displayed planetary-angular lines cross.
        - A paran or co-angular relationship is a latitude/co-angular condition and is not automatically the same geometry as the displayed intersection.
        - Lewis distinguishes actual line crossings from same-latitude crossing effects. (`acg-src-lewis-guttman-1989.page-0015`)
        - Furst uses broader crossing/paran language. (`acg-src-furst-best-places-2015.page-0021`, `acg-src-furst-best-places-2015.page-0022`)
        - The product must preserve the technique label and may show a combined interpretation without merging the underlying geometry.

        ## Source Range Variants

        | Source | Stated working range | Governance note |
        | --- | --- | --- |
        | Lewis/Guttman | effects discussed as extending as far as about `700 miles / 1,000 km`; closest line remains theoretically strongest | canonical but broad and qualitative; `acg-src-lewis-guttman-1989.page-0012` |
        | Dan Furst | about `300 miles / 500 km` on either side as a cautious working consensus; wider views are mentioned | secondary practitioner variant; `acg-src-furst-best-places-2015.page-0022` |
        | Hermes Astrology | about `150 miles / 250 km` | tertiary comparison; `acg-src-hermes-map-2023.page-0017` |

        ## Product Default Recommendation

        - Primary interpretation radius: `300 km`
        - Extended influence radius: `500 km`
        - Crossing radius: same display default as lines, while preserving exact distance and technique type

        These values are `experimental` Vox Stella display defaults (`acg-claim-product-radius-policy`), not a recovered consensus. Use continuous distance sensitivity and allow conservative, standard, and wide views rather than presenting an invisible hard edge.

        ## Birth-Time Uncertainty

        Hermes explicitly warns that slight time uncertainty reduces spatial precision (`acg-src-hermes-map-2023.page-0017`). The map should therefore:

        - accept an uncertainty interval when the recorded time is approximate;
        - propagate that interval into geographic line corridors or repeated samples;
        - cap interpretation confidence where candidate lines move materially;
        - avoid precise city rankings when time uncertainty overwhelms the distance difference.
        """
    ).strip()
    + "\n",
    "04_glossary.md": dedent(
        """
        <!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->
        <!-- document-id: acg-ref-glossary-v2 -->
        <!-- claim-classification: synthesis -->
        <!-- claim-ids: acg-claim-four-angles-have-distinct-frames, acg-claim-intersections-and-parans-need-separate-labels -->

        # Glossary

        - `Astrocartography`: locational astrology method mapping where natal planets are angular on Earth.
        - `ASC / Ascendant`: eastern horizon; direct personal expression, embodiment, self-projection.
        - `DSC / Descendant`: western horizon; relationships, projection, allies, clients, and opponents.
        - `MC / Midheaven`: upper meridian; social role, vocation, public image, and reputation.
        - `IC / Nadir`: lower meridian; home, family, roots, livelihood foundation, and inner base.
        - `Relocation chart`: Natal chart recalculated for another location without changing the birth moment.
        - `Local space`: separate directional locational technique projected from a selected origin.
        - `Geometric intersection`: displayed map point where two astrocartography lines cross.
        - `Paran`: co-angular or same-latitude relationship; terminology varies in the corpus, so it must retain a technique label.
        - `Remote activation`: engagement with people, interests, or activity tied to a location without moving there.
        - `Source ID`: stable identifier for a bibliographic source.
        - `Page ID`: stable source-and-page locator such as `acg-src-lewis-guttman-1989.page-0014`.
        - `Chunk ID`: deterministic source, page, and paragraph locator emitted by the knowledge-base builder.
        """
    ).strip()
    + "\n",
    "05_feature_notes.md": dedent(
        """
        <!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->
        <!-- document-id: acg-ref-feature-notes-v2 -->
        <!-- claim-classification: synthesis -->
        <!-- claim-ids: acg-claim-advisory-layered-workflow, acg-claim-explicit-planet-angle-matrix, acg-claim-birth-time-uncertainty-reduces-spatial-precision -->

        # Feature Notes

        ## Source-Governed Scope

        - Show world lines for selected bodies and the four angles with exact technique labels.
        - Let the user inspect a city, exact distance, and a conservative/standard/wide distance sensitivity.
        - Explain nearby lines with explicit planet-by-angle, dual-polarity interpretations and page-located provenance.
        - Keep geometric intersections, parans/co-angular relationships, relocation charts, and local-space directions separate.
        - Recast a relocation chart and preserve the natal-condition context.
        - Support side-by-side city comparison, neutral places, crowded/cancelling regions, and remote activation.
        - Propagate approximate birth time into uncertainty corridors and confidence caps.

        ## Inputs

        - Birth date
        - Exact birth time
        - Birth-time certainty or uncertainty interval
        - Birthplace coordinates / timezone
        - Optional goal: career, love, home, creativity, healing, study, travel

        ## Output Language

        Use advisory terms such as emphasis, support, challenge, activation, opportunity, or pressure. Avoid guarantees, medical conclusions, one perfect city, or claims that an experimental score is recovered doctrine.
        """
    ).strip()
    + "\n",
    "06_extended_goal_domains.md": dedent(
        """
        <!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->
        <!-- document-id: acg-ref-extended-goals-v2 -->
        <!-- claim-classification: experimental -->
        <!-- claim-ids: acg-claim-gambling-case-is-illustrative-only, acg-claim-legacy-artifacts-are-parity-only, acg-claim-specialist-goal-formulas -->

        # Extended Goal Domains

        ## Governance Status

        Gambling, health, accident, hostile-place, erotic, and similar specialist scores are `experimental` Vox Stella extensions. Legacy Almagest filenames are `legacy-parity` evidence for feature-family coverage only; they do not recover weights or doctrine.

        These extensions must not be described as source-backed formulas merely because generic planet keywords can be assembled into a plausible story.

        ## Gambling / Speculation

        Furst presents a retrospective poker-player case on pages 111–115. It associates Sun, Jupiter, Venus, Mercury, and selectively Uranus with parts of that case and warns about Neptune plus difficult Mars, Pluto, or Saturn expressions.

        That case is a useful `direct` illustration (`acg-claim-gambling-case-is-illustrative-only`). It does not establish universal weights, a guaranteed luck line, electional timing logic, or superiority over a general money/opportunity model.

        A gambling model may be researched only when it has:

        - independently curated doctrine rather than generic keyword assembly;
        - page-exact fixtures that do not bake unrelated expected signals into the input;
        - held-out repeated-player or repeated-event data;
        - explicit no-bet and uncertainty behavior;
        - a benchmark that must beat simple opportunity and popularity baselines without accepting ties as proof.

        ## Health, Injury, And Accident

        The local astrocartography books contain difficult planet and angle interpretations, but they do not establish a validated medical or accident-risk formula.

        The Astrology of Death is not an astrocartography source and is excluded from normalized books, guides, and retrieval chunks. Generic Morin, house, or mortality doctrine must not be imported into location risk scoring and then labeled astrocartography evidence.

        Claims such as Mars equals inflammation, Neptune equals weakened immunity, Chiron predicts accidents, or Jupiter/Venus lower accident risk remain `experimental` unless independently curated and validated. They must not produce medical advice or safety assurances.

        ## Release Gate

        Specialist models remain research-only until their own held-out benchmarks beat their parent and simple baselines, their claims have independent doctrine fixtures, and the UI clearly communicates uncertainty and non-medical scope.
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
        "<!-- generated-by: scripts/build_astrocartography_knowledge_base.py -->",
        "",
        "# Astrocartography Knowledge Base",
        "",
        "This directory is a traceable, AI-oriented layer built from the governed local astrocartography corpus. Stable IDs prove where a claim came from; they do not prove astrology or a retrospective case interpretation scientifically valid.",
        "",
        "## Layout",
        "",
        "- `normalized_books/`: governed source books with stable page and paragraph chunk IDs",
        "- `guides/`: source-specific scan guides with token-bounded keyword anchors",
        "- `reference/`: classified direct, synthesis, legacy-parity, and experimental notes",
        "- `catalog.json`: portable source catalog with repository-relative paths",
        "- `chunk_index.jsonl`: retrieval index keyed by source, page, and chunk IDs",
        "- `../astrocartography_sources/`: canonical source and claim registries",
        "",
        "## Recommended Reading Order",
        "",
        "1. `reference/00_source_governance.md`",
        "2. `reference/01_core_concepts.md`",
        "3. `reference/02_planetary_and_angular_reference.md`",
        "4. `reference/03_techniques_and_ranges.md`",
        "5. `guides/lewis_guttman_book_of_maps.md` — canonical doctrine",
        "6. `guides/dan_furst_best_places.md` — secondary practitioner variants",
        "7. `guides/hermes_map_interpretation.md` — tertiary comparison only",
        "",
        "## Source Coverage",
        "",
        "| Rank | Source ID | Book | Retrieval | Best use |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in catalog_rows:
        retrieval = row["retrieval"]
        retrieval_label = (
            ", ".join(retrieval["scopes"])
            if retrieval["enabled"]
            else f"excluded — {retrieval['exclusion_reason']}"
        )
        lines.append(
            f"| {row['authority']['rank']} | `{row['source_id']}` | {row['title']} | "
            f"{retrieval_label} | {row['preferred_use']} |"
        )
    lines.extend(
        [
            "",
            "The Astrology of Death remains inventoried in `catalog.json` but is intentionally absent from normalized books, guides, and retrieval chunks. The dictionary is restricted to the `terminology` scope.",
        ]
    )
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _catalog_metadata(
    book: BookSpec,
    registry_row: dict[str, Any],
) -> dict[str, object]:
    retrieval = registry_row["retrieval"]
    return {
        "source_id": book.source_id,
        "title": book.title,
        "authors": list(book.authors),
        "year": book.year,
        "edition": book.edition,
        "publisher": book.publisher,
        "source_name": book.source_name,
        "source_path": registry_row["extracted"]["repo_path"],
        "role": book.role,
        "preferred_use": book.preferred_use,
        "authority": {
            "tier": book.authority_tier,
            "rank": book.authority_rank,
            "rationale": book.authority_rationale,
        },
        "default_claim_classification": book.default_claim_classification,
        "retrieval": {
            "enabled": book.retrieval_enabled,
            "scopes": list(book.retrieval_scopes),
            "exclusion_reason": retrieval.get("exclusion_reason", ""),
            "limitations": retrieval.get("limitations", ""),
        },
        "rights": registry_row["rights"],
        "original": registry_row["original"],
        "extracted": registry_row["extracted"],
    }


def build_catalog(
    raw_dir: Path,
    out_dir: Path,
    *,
    chunk_rows: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    normalized_dir = out_dir / "normalized_books"
    guides_dir = out_dir / "guides"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    guides_dir.mkdir(parents=True, exist_ok=True)

    registry = load_source_registry()
    registry_rows = {row["source_id"]: row for row in registry["sources"]}
    rows: list[dict[str, object]] = []
    for book in BOOKS:
        registry_row = registry_rows[book.source_id]
        row = _catalog_metadata(book, registry_row)
        source_path = raw_dir / book.source_name
        if not source_path.exists():
            row["error"] = "missing source file"
            rows.append(row)
            continue

        normalized_name = slugify(book.key) + ".md"
        guide_name = slugify(book.key) + ".md"
        normalized_path = normalized_dir / normalized_name
        guide_path = guides_dir / guide_name

        if not book.retrieval_enabled:
            for stale_path in (normalized_path, guide_path):
                if stale_path.is_file():
                    stale_path.unlink()
            row["normalized_book_path"] = None
            row["guide_path"] = None
            row["chunk_count"] = 0
            rows.append(row)
            continue

        raw_text = source_path.read_text(encoding="utf-8")
        normalized_markdown, book_chunks = render_book_artifacts(book, raw_text)
        normalized_path.write_text(normalized_markdown, encoding="utf-8")

        guide_metadata = write_book_guide(book, raw_text, guide_path)
        row.update(
            {
                "guide_path": guide_metadata["guide_path"],
                "heading_count": guide_metadata["heading_count"],
                "keyword_hits": guide_metadata["keyword_hits"],
            }
        )
        row["normalized_book_path"] = f"normalized_books/{normalized_name}"
        row["source_chars"] = len(raw_text)
        row["chunk_count"] = len(book_chunks)
        for chunk in book_chunks:
            chunk["normalized_book_path"] = row["normalized_book_path"]
        if chunk_rows is not None:
            chunk_rows.extend(book_chunks)
        rows.append(row)

    return rows


def write_chunk_index(
    destination: Path,
    chunk_rows: list[dict[str, object]],
) -> None:
    serialized: list[str] = []
    for row in chunk_rows:
        serialized.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    destination.write_text(
        "\n".join(serialized) + ("\n" if serialized else ""),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_DIR)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    raw_dir: Path = args.raw
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    registry = load_source_registry()
    claim_registry = load_claim_registry()
    governance_errors = validate_source_registry(registry, repo_root=REPO_ROOT)
    governance_errors.extend(validate_claim_registry(claim_registry, registry))
    if governance_errors:
        raise ValueError(
            "Astrocartography source governance failed:\n- "
            + "\n- ".join(governance_errors)
        )

    chunk_rows: list[dict[str, object]] = []
    catalog_rows = build_catalog(raw_dir, out_dir, chunk_rows=chunk_rows)
    write_reference_docs(out_dir / "reference")
    write_readme(out_dir / "README.md", catalog_rows)
    (out_dir / "catalog.json").write_text(
        json.dumps(catalog_rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_chunk_index(out_dir / "chunk_index.jsonl", chunk_rows)

    print(
        f"Built Astrocartography knowledge base in {out_dir} "
        f"({len(catalog_rows)} sources, {len(chunk_rows)} retrieval chunks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
