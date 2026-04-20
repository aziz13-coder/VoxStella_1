"""
Search a text inspection corpus chunk index.

Defaults to the new_sources inspection corpus built by build_text_inspection_corpus.py.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_INDEX = Path(r"C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\new_sources_inspection\chunk_index.jsonl")


def tokenize(query: str) -> list[str]:
    return [tok for tok in re.findall(r"[A-Za-z0-9_']+", query.lower()) if len(tok) >= 2]


def score_row(row: dict[str, object], terms: list[str]) -> int:
    title = str(row.get("title") or "").lower()
    heading = str(row.get("heading") or "").lower()
    excerpt = str(row.get("excerpt") or "").lower()
    source_name = str(row.get("source_name") or "").lower()

    score = 0
    for term in terms:
        if term in title:
            score += 6
        if term in heading:
            score += 10
        if term in excerpt:
            score += 4
        if term in source_name:
            score += 2
    return score


def load_rows(index_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with index_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Search query")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--book", default="", help="Optional substring filter on title/source")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    index_path = args.index.resolve()
    rows = load_rows(index_path)
    terms = tokenize(args.query)
    if not terms:
        raise SystemExit("Query produced no searchable terms.")

    book_filter = args.book.strip().lower()
    scored: list[tuple[int, dict[str, object]]] = []
    for row in rows:
        if book_filter:
            hay = f"{row.get('title', '')} {row.get('source_name', '')}".lower()
            if book_filter not in hay:
                continue
        score = score_row(row, terms)
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: (-item[0], str(item[1].get("title") or ""), str(item[1].get("chunk_id") or "")))
    top = scored[: max(1, args.limit)]

    if args.json:
        payload = []
        for score, row in top:
            item = dict(row)
            item["score"] = score
            payload.append(item)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if not top:
        print("No matching chunks found.")
        return 0

    for score, row in top:
        pages = row.get("pages") or []
        page_label = ", ".join(str(p) for p in pages) if isinstance(pages, list) and pages else "n/a"
        print(f"[score={score}] {row.get('title')}")
        print(f"  heading: {row.get('heading')}")
        print(f"  pages:   {page_label}")
        print(f"  path:    {row.get('path')}")
        print(f"  excerpt: {row.get('excerpt')}")
        print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
