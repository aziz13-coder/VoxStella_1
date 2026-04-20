"""
Build compact runtime interpretation assets from the Astrocartography knowledge base.

Inputs:
- horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md
- horary_knowledge/astrocartography_knowledge_base/reference/03_techniques_and_ranges.md
- horary_knowledge/astrocartography_knowledge_base/reference/05_feature_notes.md

Outputs:
- backend/knowledge/astrocartography/interpretation_runtime.json

The goal is to keep frontend/backend runtime copy source-backed without
requiring the app to parse large markdown files on each request.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, List


ROOT = Path(r"C:\Users\sabaa\Downloads\codexhorary")
REFERENCE_DIR = ROOT / "horary_knowledge" / "astrocartography_knowledge_base" / "reference"
OUTPUT_PATH = ROOT / "backend" / "knowledge" / "astrocartography" / "interpretation_runtime.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_section_lines(text: str, heading: str) -> List[str]:
    lines = text.splitlines()
    start_idx = None
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start_idx = idx + 1
            break
    if start_idx is None:
        raise ValueError(f"Heading not found: {heading}")
    out: List[str] = []
    for line in lines[start_idx:]:
        if line.startswith("## "):
            break
        out.append(line.rstrip())
    return out


def _parse_markdown_table(section_lines: List[str]) -> List[Dict[str, str]]:
    table_lines = [line.strip() for line in section_lines if line.strip().startswith("|")]
    if len(table_lines) < 3:
        raise ValueError("Expected markdown table with header, divider, and rows")
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: List[Dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def _parse_range_value(section_lines: List[str], label: str) -> int:
    pattern = re.compile(rf"^- {re.escape(label)}: `([0-9]+) km`$")
    for line in section_lines:
        match = pattern.match(line.strip())
        if match:
            return int(match.group(1))
    raise ValueError(f"Range value not found for {label}")


def build_runtime_assets() -> Dict[str, object]:
    planet_reference_path = REFERENCE_DIR / "02_planetary_and_angular_reference.md"
    range_reference_path = REFERENCE_DIR / "03_techniques_and_ranges.md"
    feature_notes_path = REFERENCE_DIR / "05_feature_notes.md"

    planet_reference_text = _read_text(planet_reference_path)
    range_reference_text = _read_text(range_reference_path)
    feature_notes_text = _read_text(feature_notes_path)

    body_rows = _parse_markdown_table(_extract_section_lines(planet_reference_text, "## Planet Baselines"))
    angle_rows = _parse_markdown_table(_extract_section_lines(planet_reference_text, "## Angle Modifiers"))
    range_lines = _extract_section_lines(range_reference_text, "## Product Default Recommendation")

    angle_id_map = {
        "AC": "ASC",
        "DC": "DSC",
        "MC": "MC",
        "IC": "IC",
    }

    bodies: Dict[str, Dict[str, object]] = {}
    for row in body_rows:
        body = row["Body"]
        bodies[body] = {
            "core_themes": row["Core themes"],
            "common_upside": row["Common upside"],
            "common_caution": row["Common caution"],
            "source_ref": {
                "file": str(planet_reference_path.relative_to(ROOT)).replace("\\", "/"),
                "section": "Planet Baselines",
            },
        }

    angles: Dict[str, Dict[str, object]] = {}
    for row in angle_rows:
        angle_id = angle_id_map.get(row["Angle"], row["Angle"])
        angles[angle_id] = {
            "interprets_through": row["Interprets the planet through"],
            "user_shorthand": row["User-facing shorthand"],
            "source_ref": {
                "file": str(planet_reference_path.relative_to(ROOT)).replace("\\", "/"),
                "section": "Angle Modifiers",
            },
        }

    feature_note = ""
    for line in feature_notes_text.splitlines():
        if "corpus-backed interpretation library" in line:
            feature_note = line.strip("- ").strip()
            break

    return {
        "generated_on": date.today().isoformat(),
        "generator": "scripts/build_astrocartography_runtime_assets.py",
        "sources": [
            str(planet_reference_path.relative_to(ROOT)).replace("\\", "/"),
            str(range_reference_path.relative_to(ROOT)).replace("\\", "/"),
            str(feature_notes_path.relative_to(ROOT)).replace("\\", "/"),
        ],
        "range_policy": {
            "primary_radius_km": _parse_range_value(range_lines, "Primary interpretation radius"),
            "extended_radius_km": _parse_range_value(range_lines, "Extended influence radius"),
            "crossing_radius_note": "Crossing radius follows the same default as lines, but exact crossings rank more strongly.",
            "source_ref": {
                "file": str(range_reference_path.relative_to(ROOT)).replace("\\", "/"),
                "section": "Product Default Recommendation",
            },
        },
        "interpretation_policy": {
            "style": "source_backed_runtime_asset",
            "note": feature_note,
        },
        "bodies": bodies,
        "angles": angles,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Astrocartography runtime interpretation assets.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Output JSON path")
    args = parser.parse_args()

    payload = build_runtime_assets()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
