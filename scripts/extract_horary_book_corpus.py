#!/usr/bin/env python3
"""Build a machine-readable horary example corpus from the EPUB source book."""

from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOK_PATH = Path(
    r"C:\Users\sabaa\Downloads\Horary Examples Traditional Horary Astrology By Example ( etc.) (z-library.sk, 1lib.sk, z-lib.sk).epub"
)
OUTPUT_PATH = REPO_ROOT / "tests" / "fixtures" / "horary_book_examples_corpus.json"

SECTION_TITLES = {
    "Introduction",
    "Contests",
    "Money & Jobs",
    "Housing",
    "Relationship",
    "Pregnancy & Children",
    "Health",
    "Lost & Found",
    "Miscellaneous",
    "Glossary",
    "Author Biographies",
}

SAFE_TIER1_SECTIONS = {"Money & Jobs", "Housing", "Lost & Found"}
DEATH_OR_HEALTH_PAT = re.compile(
    r"\b(die|dying|survive|tumou?r|sclerosis|recover|inflam|stomach|ill|health|baby)\b",
    re.IGNORECASE,
)
PUBLIC_EVENT_PAT = re.compile(
    r"\b(election|presidency|government|romney|brazil|argentina|brewers|badgers|britain|scotland|pope|priest|trial)\b",
    re.IGNORECASE,
)
TIMING_PAT = re.compile(r"^(when|what time)\b", re.IGNORECASE)
DISCOVERY_PAT = re.compile(r"^(where)\b", re.IGNORECASE)
ADVICE_PAT = re.compile(r"\bshould\b|\bany chance\b|\bany hope\b", re.IGNORECASE)
STATUS_PAT = re.compile(r"^(am|is|are|has)\b", re.IGNORECASE)

DATE_PAT = re.compile(
    r"\b(?P<date>(?:[A-Z][a-z]+ \d{1,2}, \d{4})|(?:\d{1,2} [A-Z][a-z]+ \d{4}))\b"
)
TIME_PAT = re.compile(r"\b(?P<time>\d{1,2}:\d{2}\s*(?:A\.M\.|P\.M\.|AM|PM|a\.m\.|p\.m\.))\b")
HEADER_PAT = re.compile(
    r"(?P<date>(?:[A-Z][a-z]+ \d{1,2}, \d{4})|(?:\d{1,2} [A-Z][a-z]+ \d{4})),?\s+"
    r"(?P<time>\d{1,2}:\d{2}\s*(?:A\.M\.|P\.M\.|AM|PM|a\.m\.|p\.m\.))\s*\|\s*"
    r"(?P<location>.*?)\s*\|\s*(?P<asc_degree>\d{1,2})\s+(?P<asc_sign>[A-Za-z]+)"
)
VERDICT_PAT = re.compile(r"\b(verdict|judgment|judgement)\b", re.IGNORECASE)
RESULT_PAT = re.compile(r"\b(result|outcome|happened|turned out)\b", re.IGNORECASE)
ALTERED_PAT = re.compile(r"\b(altered|anonymi[sz]ed|changed details)\b", re.IGNORECASE)


@dataclass
class TocEntry:
    title: str
    src: str


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
    return slug or "untitled"


def clean_text(raw_html: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", raw_html)
    unescaped = html.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def load_toc(epub_path: Path) -> list[TocEntry]:
    with zipfile.ZipFile(epub_path) as zf:
        toc_xml = zf.read("toc.ncx")
    root = ET.fromstring(toc_xml)
    ns = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}
    entries: list[TocEntry] = []
    for nav_point in root.findall(".//ncx:navPoint", ns):
        title_node = nav_point.find("ncx:navLabel/ncx:text", ns)
        content_node = nav_point.find("ncx:content", ns)
        if title_node is None or content_node is None:
            continue
        entries.append(
            TocEntry(
                title=html.unescape((title_node.text or "").strip()),
                src=content_node.attrib.get("src", "").strip(),
            )
        )
    return entries


def read_chapter_text(zf: zipfile.ZipFile, chapter_path: str) -> str:
    return clean_text(zf.read(chapter_path).decode("utf-8", errors="ignore"))


def infer_category(section: str, title: str) -> str:
    lower = title.lower()
    if section == "Contests":
        if "election" in lower or "presidency" in lower:
            return "politics"
        if "trial" in lower:
            return "legal"
        return "competition"
    if section == "Money & Jobs":
        if "job" in lower or "review of my work" in lower:
            return "career"
        if "tenant" in lower:
            return "money_property"
        if "business" in lower:
            return "business"
        return "money"
    if section == "Housing":
        return "property"
    if section == "Relationship":
        return "relationship"
    if section == "Pregnancy & Children":
        return "pregnancy_children"
    if section == "Health":
        if "die" in lower or "survive" in lower:
            return "death_health"
        return "health"
    if section == "Lost & Found":
        return "lost_found"
    if section == "Miscellaneous":
        if "euro" in lower or "scotland" in lower:
            return "politics"
        if "what time" in lower or "when " in lower:
            return "timing"
        if "thief" in lower or "kidnapped" in lower:
            return "crime"
        return "general"
    return "general"


def infer_question_family(title: str) -> str:
    lower = title.lower()
    if DISCOVERY_PAT.search(lower):
        return "discovery"
    if TIMING_PAT.search(lower):
        return "timing"
    if ADVICE_PAT.search(lower):
        return "advisability"
    if STATUS_PAT.search(lower):
        return "status_diagnosis"
    return "occurrence"


def infer_third_person(title: str) -> bool:
    lower = title.lower()
    if lower.startswith(("will i ", "am i ", "should i ", "where is my ", "what time will i ")):
        return False
    return bool(
        re.search(
            r"\b(dad|mum|mother|father|grandfather|daughter|friend|tenant|dog|pope|priest|deirdre|barrett|romney|brazil|argentina|brewers|badgers|zaza|darryl)\b",
            lower,
        )
    )


def header_metadata(title: str, plain_text: str) -> dict[str, Optional[str]]:
    after_title = plain_text.split(title, 1)[1].strip() if title in plain_text else plain_text
    match = HEADER_PAT.search(after_title)
    if not match:
        return {
            "author": None,
            "date_text": None,
            "time_text": None,
            "location_text": None,
            "asc_degree_text": None,
            "asc_sign_text": None,
        }

    before = after_title[: match.start()].strip(" |,-")
    author = before if before else None
    return {
        "author": author,
        "date_text": match.group("date"),
        "time_text": match.group("time"),
        "location_text": match.group("location"),
        "asc_degree_text": match.group("asc_degree"),
        "asc_sign_text": match.group("asc_sign"),
    }


def infer_tier(
    *,
    section: str,
    title: str,
    has_date: bool,
    has_time: bool,
    has_location: bool,
    has_explicit_verdict: bool,
    has_explicit_result: bool,
    altered: bool,
    question_family: str,
) -> tuple[str, str, str]:
    full_header = has_date and has_time and has_location
    multi_part = title.count("?") > 1 or " if so" in title.lower()
    public_event = bool(PUBLIC_EVENT_PAT.search(title))
    death_health = bool(DEATH_OR_HEALTH_PAT.search(title))

    if altered or not full_header:
        missing = []
        if not has_date:
            missing.append("date")
        if not has_time:
            missing.append("time")
        if not has_location:
            missing.append("location")
        blocker = "Chart metadata incomplete: missing " + ", ".join(missing) if missing else (
            "Chapter notes altered/anonymized details, so it is not safe for deterministic replay."
        )
        return "tier_3_manual_review_only", "manual_review_only", blocker

    if (
        section in SAFE_TIER1_SECTIONS
        and not multi_part
        and not public_event
        and not death_health
        and question_family not in {"timing"}
    ):
        blocker = (
            "Full header metadata is present; promote after chart casting/parity capture."
            if not (has_explicit_verdict or has_explicit_result)
            else "Ready for first deterministic replay pass."
        )
        return "tier_1_deterministic_candidate", "deterministic_replay_candidate", blocker

    blocker = (
        "Full header metadata is present, but this case needs doctrinal review or special-rule confirmation before deterministic automation."
    )
    return "tier_2_replay_ready_doctrinal_review", "replay_ready_doctrinal_review", blocker


def build_corpus(epub_path: Path) -> list[dict[str, object]]:
    entries = load_toc(epub_path)
    current_section = "Unknown"
    corpus: list[dict[str, object]] = []

    with zipfile.ZipFile(epub_path) as zf:
        for entry in entries:
            title = entry.title
            if title in SECTION_TITLES:
                current_section = title
                continue
            if title in {"Glossary", "Author Biographies"}:
                continue

            chapter_path, _, anchor = entry.src.partition("#")
            plain = read_chapter_text(zf, chapter_path)
            meta = header_metadata(title, plain)

            has_date = bool(meta["date_text"] or DATE_PAT.search(plain))
            has_time = bool(meta["time_text"] or TIME_PAT.search(plain))
            has_location = bool(meta["location_text"])
            has_explicit_verdict = bool(VERDICT_PAT.search(plain))
            has_explicit_result = bool(RESULT_PAT.search(plain))
            altered = bool(ALTERED_PAT.search(plain))
            question_family = infer_question_family(title)
            tier, replay_status, blocker = infer_tier(
                section=current_section,
                title=title,
                has_date=has_date,
                has_time=has_time,
                has_location=has_location,
                has_explicit_verdict=has_explicit_verdict,
                has_explicit_result=has_explicit_result,
                altered=altered,
                question_family=question_family,
            )

            corpus.append(
                {
                    "id": slugify(title),
                    "source": "horary_examples_book",
                    "book_title": "Horary Examples: Traditional Horary Astrology By Example",
                    "section": current_section,
                    "title": title,
                    "epub_chapter": chapter_path,
                    "epub_anchor": anchor or None,
                    "author": meta["author"],
                    "header_date_text": meta["date_text"],
                    "header_time_text": meta["time_text"],
                    "header_location_text": meta["location_text"],
                    "header_asc_degree_text": meta["asc_degree_text"],
                    "header_asc_sign_text": meta["asc_sign_text"],
                    "expected_category_guess": infer_category(current_section, title),
                    "question_family": question_family,
                    "third_person": infer_third_person(title),
                    "has_explicit_date": has_date,
                    "has_explicit_time": has_time,
                    "has_explicit_location": has_location,
                    "has_house_system": False,
                    "has_explicit_verdict": has_explicit_verdict,
                    "has_explicit_result": has_explicit_result,
                    "details_altered_or_anonymized": altered,
                    "tier": tier,
                    "replay_status": replay_status,
                    "manual_review_only": tier == "tier_3_manual_review_only",
                    "blocking_reason": blocker,
                    "source_excerpt": plain[:900],
                }
            )
    return corpus


def summarise(corpus: Iterable[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in corpus:
        key = str(item["tier"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", type=Path, default=BOOK_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    corpus = build_corpus(args.book)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(corpus, indent=2, ensure_ascii=True), encoding="utf-8")

    summary = summarise(corpus)
    print(f"Wrote {len(corpus)} corpus entries to {args.output}")
    for tier, count in sorted(summary.items()):
        print(f"  {tier}: {count}")


if __name__ == "__main__":
    main()
