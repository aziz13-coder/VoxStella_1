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
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "horary_knowledge" / "astrocartography_knowledge_base" / "reference"
OUTPUT_PATH = ROOT / "backend" / "knowledge" / "astrocartography" / "interpretation_runtime.json"
SOURCE_REGISTRY_PATH = ROOT / "horary_knowledge" / "astrocartography_sources" / "source_registry.json"
CLAIM_REGISTRY_PATH = ROOT / "horary_knowledge" / "astrocartography_sources" / "claim_registry.json"
PAGE_ID_RE = re.compile(r"`(acg-src-[a-z0-9-]+\.page-[0-9]{4})`")
ASSET_SCHEMA_VERSION = 2
ASSET_GENERATED_ON = "2026-07-18"


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


def _page_ids(value: str) -> List[str]:
    return PAGE_ID_RE.findall(value or "")


def build_runtime_assets() -> Dict[str, object]:
    planet_reference_path = REFERENCE_DIR / "02_planetary_and_angular_reference.md"
    range_reference_path = REFERENCE_DIR / "03_techniques_and_ranges.md"
    feature_notes_path = REFERENCE_DIR / "05_feature_notes.md"

    planet_reference_text = _read_text(planet_reference_path)
    range_reference_text = _read_text(range_reference_path)
    feature_notes_text = _read_text(feature_notes_path)

    body_rows = _parse_markdown_table(_extract_section_lines(planet_reference_text, "## Planet Baselines"))
    angle_rows = _parse_markdown_table(_extract_section_lines(planet_reference_text, "## Angle Modifiers"))
    line_interpretation_rows = _parse_markdown_table(
        _extract_section_lines(planet_reference_text, "## Explicit Planet-By-Angle Matrix")
    )
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
                "claim_classification": row.get("Classification") or "unclassified",
                "page_ids": _page_ids(row.get("Source refs") or ""),
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
                "claim_classification": row.get("Classification") or "unclassified",
                "page_ids": _page_ids(row.get("Source refs") or ""),
            },
        }

    line_interpretations: Dict[str, Dict[str, object]] = {}
    for row in line_interpretation_rows:
        body = row["Body"]
        angle_id = angle_id_map.get(row["Angle"], row["Angle"])
        key = f"{body}:{angle_id}"
        if key in line_interpretations:
            raise ValueError(f"Duplicate explicit planet-by-angle row: {key}")
        line_interpretations[key] = {
            "summary": row["Summary"],
            "supportive_expression": row["Supportive expression"],
            "difficult_expression": row["Difficult expression"],
            "doctrine_scope": (
                "secondary_extension"
                if body in {"North Node", "Chiron"}
                else "core_planet_line"
            ),
            "model_status": (
                "experimental_extension"
                if body in {"North Node", "Chiron"}
                else "doctrine_synthesis"
            ),
            "source_ref": {
                "file": str(planet_reference_path.relative_to(ROOT)).replace("\\", "/"),
                "section": "Explicit Planet-By-Angle Matrix",
                "claim_id": "acg-claim-explicit-planet-angle-matrix",
                "claim_classification": row.get("Classification") or "synthesis",
                "page_ids": _page_ids(row.get("Source refs") or ""),
            },
        }

    expected_line_keys = {
        f"{body}:{angle_id}"
        for body in bodies
        for angle_id in angles
    }
    actual_line_keys = set(line_interpretations)
    if actual_line_keys != expected_line_keys:
        missing = sorted(expected_line_keys - actual_line_keys)
        extra = sorted(actual_line_keys - expected_line_keys)
        raise ValueError(
            "Explicit planet-by-angle matrix must cover every supported combination "
            f"(missing={missing}, extra={extra})"
        )

    feature_note = ""
    for line in feature_notes_text.splitlines():
        if "corpus-backed interpretation library" in line:
            feature_note = line.strip("- ").strip()
            break

    return {
        "asset_schema_version": ASSET_SCHEMA_VERSION,
        "generated_on": ASSET_GENERATED_ON,
        "generator": "scripts/build_astrocartography_runtime_assets.py",
        "sources": [
            str(planet_reference_path.relative_to(ROOT)).replace("\\", "/"),
            str(range_reference_path.relative_to(ROOT)).replace("\\", "/"),
            str(feature_notes_path.relative_to(ROOT)).replace("\\", "/"),
            str(SOURCE_REGISTRY_PATH.relative_to(ROOT)).replace("\\", "/"),
            str(CLAIM_REGISTRY_PATH.relative_to(ROOT)).replace("\\", "/"),
        ],
        "source_governance": {
            "source_registry": str(SOURCE_REGISTRY_PATH.relative_to(ROOT)).replace("\\", "/"),
            "claim_registry": str(CLAIM_REGISTRY_PATH.relative_to(ROOT)).replace("\\", "/"),
            "authority_order": [
                "acg-src-lewis-guttman-1989",
                "acg-src-furst-best-places-2015",
                "acg-src-hermes-map-2023",
                "acg-src-lee-dictionary-1968",
            ],
            "excluded_source_ids": ["acg-src-houck-death-1994"],
            "claim_classes": ["direct", "synthesis", "legacy-parity", "experimental"],
        },
        "range_policy": {
            "primary_radius_km": _parse_range_value(range_lines, "Primary interpretation radius"),
            "extended_radius_km": _parse_range_value(range_lines, "Extended influence radius"),
            "crossing_radius_note": "Crossing radius follows the same default as lines, but exact crossings rank more strongly.",
            "source_ref": {
                "file": str(range_reference_path.relative_to(ROOT)).replace("\\", "/"),
                "section": "Product Default Recommendation",
                "claim_id": "acg-claim-product-radius-policy",
                "claim_classification": "experimental",
                "page_ids": [
                    "acg-src-lewis-guttman-1989.page-0012",
                    "acg-src-furst-best-places-2015.page-0022",
                    "acg-src-hermes-map-2023.page-0017",
                ],
            },
        },
        "interpretation_policy": {
            "style": "source_backed_runtime_asset",
            "note": feature_note,
            "generic_planet_plus_angle_is_fallback_only": True,
            "preferred_claim_id": "acg-claim-explicit-planet-angle-matrix",
            "supported_matrix_complete": True,
        },
        "bodies": bodies,
        "angles": angles,
        "line_interpretations": line_interpretations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Astrocartography runtime interpretation assets.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Output JSON path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the checked-in runtime asset differs from the deterministic builder output.",
    )
    args = parser.parse_args()

    payload = build_runtime_assets()
    if args.check:
        if not args.output.exists():
            raise SystemExit(f"Astrocartography runtime asset is missing: {args.output}")
        try:
            current = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Unable to read Astrocartography runtime asset: {exc}") from exc
        if current != payload:
            raise SystemExit(
                "Astrocartography runtime asset is stale. "
                "Run: python scripts/build_astrocartography_runtime_assets.py"
            )
        print(f"Current: {args.output}")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
