"""
Run the full synastry source-corpus pipeline:

1. Convert desktop PDFs into repo-local plain text.
2. Build the cleaned synastry knowledge base from that raw text.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
import shutil


REPO_ROOT = Path(r"C:\Users\sabaa\Downloads\codexhorary")
DEFAULT_SOURCE = Path(r"C:\Users\sabaa\Desktop\astrolgy books\synastry")
DEFAULT_RAW_DEST = REPO_ROOT / "horary_knowledge" / "synastry_books_text"
DEFAULT_KB_DEST = REPO_ROOT / "horary_knowledge" / "synastry_knowledge_base"
SUPPORTING_TEXT_SOURCES = (
    REPO_ROOT / "horary_knowledge" / "desktop_books_text" / "Person_to_person_Astrology_Stephen_Arroyo_z-library.sk_1lib.sk_z-lib.sk.txt",
)


def run_step(command: list[str]) -> None:
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, check=True)


def copy_supporting_texts(raw_dest: Path) -> None:
    raw_dest.mkdir(parents=True, exist_ok=True)
    for source in SUPPORTING_TEXT_SOURCES:
        if not source.exists():
            print(f"Skipping missing supporting text: {source}")
            continue
        dest = raw_dest / source.name
        shutil.copyfile(source, dest)
        print(f"Copied supporting text: {source.name}")


def refresh_raw_summary(source: Path, raw_dest: Path) -> None:
    manifest_path = raw_dest / "manifest.json"
    rows: list[dict[str, object]] = []
    if manifest_path.exists():
        rows = json.loads(manifest_path.read_text(encoding="utf-8"))

    by_output = {str(row.get("output_name")): row for row in rows}
    for support_path in SUPPORTING_TEXT_SOURCES:
        if not support_path.exists():
            continue
        dest = raw_dest / support_path.name
        if not dest.exists():
            continue
        by_output[dest.name] = {
            "source_name": support_path.name,
            "source_ext": support_path.suffix.lower(),
            "output_name": dest.name,
            "status": "ok",
            "chars": len(dest.read_text(encoding="utf-8")),
            "notes": "copied from repo-local support corpus",
        }

    rows = sorted(by_output.values(), key=lambda row: str(row.get("output_name", "")).lower())
    manifest_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    readme_lines = [
        "# Desktop Books Text Corpus",
        "",
        f"Source: `{source}`",
        "",
        "| Source | Output | Status | Characters | Notes |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in rows:
        readme_lines.append(
            f"| {row['source_name']} | {row['output_name']} | {row['status']} | {row['chars']} | {row.get('notes', '') or ''} |"
        )
    (raw_dest / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--raw-dest", type=Path, default=DEFAULT_RAW_DEST)
    parser.add_argument("--kb-dest", type=Path, default=DEFAULT_KB_DEST)
    args = parser.parse_args()

    source = args.source.resolve()
    raw_dest = args.raw_dest.resolve()
    kb_dest = args.kb_dest.resolve()

    run_step(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "convert_desktop_books_to_text.py"),
            "--source",
            str(source),
            "--dest",
            str(raw_dest),
        ]
    )
    copy_supporting_texts(raw_dest)
    refresh_raw_summary(source, raw_dest)
    run_step(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_synastry_knowledge_base.py"),
            "--raw",
            str(raw_dest),
            "--out",
            str(kb_dest),
        ]
    )
    print(f"Synastry corpus ready in {kb_dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
