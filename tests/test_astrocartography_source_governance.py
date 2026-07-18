from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_astrocartography_knowledge_base as kb_builder
import build_astrocartography_runtime_assets as runtime_builder
from astrocartography_source_governance import (
    ALLOWED_CLAIM_CLASSIFICATIONS,
    load_claim_registry,
    load_source_registry,
    make_chunk_id,
    make_page_id,
    validate_source_governance,
)
from validate_astrocartography_sources import validate_generated_assets


def test_source_registry_and_generated_assets_are_complete() -> None:
    assert validate_source_governance() == []
    assert validate_generated_assets() == []


def test_source_hierarchy_and_retrieval_exclusion_are_explicit() -> None:
    registry = load_source_registry()
    sources = {row["source_id"]: row for row in registry["sources"]}

    canonical = sources["acg-src-lewis-guttman-1989"]
    assert canonical["authority"]["tier"] == "tier-1-canonical-doctrine"
    assert canonical["authority"]["rank"] == 1

    assert sources["acg-src-furst-best-places-2015"]["authority"]["rank"] == 2
    assert sources["acg-src-hermes-map-2023"]["authority"]["rank"] == 3
    assert sources["acg-src-lee-dictionary-1968"]["retrieval"]["scopes"] == [
        "terminology"
    ]

    excluded = sources["acg-src-houck-death-1994"]
    assert excluded["retrieval"]["enabled"] is False
    assert "health/death" in excluded["retrieval"]["exclusion_reason"]


def test_claim_ledger_exercises_all_governance_classes() -> None:
    claims = load_claim_registry()["claims"]
    assert {row["classification"] for row in claims} == ALLOWED_CLAIM_CLASSIFICATIONS

    direct = next(row for row in claims if row["classification"] == "direct")
    assert direct["source_refs"]
    for source_ref in direct["source_refs"]:
        assert source_ref["page_id"] == make_page_id(
            source_ref["source_id"], source_ref["page"]
        )

    assert any(
        row["classification"] == "legacy-parity" and row["legacy_artifact_refs"]
        for row in claims
    )
    assert all(
        row.get("evidence_limitations")
        for row in claims
        if row["classification"] == "experimental"
    )


def test_short_keyword_matches_are_token_bounded() -> None:
    raw = """=== Page 3 ===
LLEWELLYN PUBLICATIONS
ISBN 0-87542-434-1

=== Page 15 ===
Imum Coeli: IC
"""
    hits = kb_builder.find_keyword_hits(
        raw,
        ("IC",),
        per_term=10,
        source_id="acg-src-lewis-guttman-1989",
    )

    assert len(hits["IC"]) == 1
    assert hits["IC"][0]["page"] == 15
    assert hits["IC"][0]["page_id"] == (
        "acg-src-lewis-guttman-1989.page-0015"
    )


def test_page_and_chunk_ids_are_deterministic() -> None:
    source_id = "acg-src-lewis-guttman-1989"
    assert make_page_id(source_id, 14) == (
        "acg-src-lewis-guttman-1989.page-0014"
    )
    assert make_chunk_id(source_id, 14, 2) == (
        "acg-src-lewis-guttman-1989.page-0014.chunk-002"
    )


def test_runtime_builder_carries_governed_page_provenance() -> None:
    payload = runtime_builder.build_runtime_assets()

    assert payload["source_governance"]["authority_order"][0] == (
        "acg-src-lewis-guttman-1989"
    )
    assert payload["source_governance"]["excluded_source_ids"] == [
        "acg-src-houck-death-1994"
    ]
    assert payload["range_policy"]["source_ref"]["claim_classification"] == (
        "experimental"
    )
    assert payload["bodies"]["Sun"]["source_ref"]["page_ids"] == [
        "acg-src-lewis-guttman-1989.page-0013"
    ]
    assert payload["angles"]["MC"]["source_ref"]["page_ids"] == [
        "acg-src-lewis-guttman-1989.page-0014",
        "acg-src-furst-best-places-2015.page-0018",
    ]


def _build_into(destination: Path) -> None:
    chunks: list[dict[str, object]] = []
    rows = kb_builder.build_catalog(
        kb_builder.RAW_DIR,
        destination,
        chunk_rows=chunks,
    )
    kb_builder.write_reference_docs(destination / "reference")
    kb_builder.write_readme(destination / "README.md", rows)
    (destination / "catalog.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    kb_builder.write_chunk_index(destination / "chunk_index.jsonl", chunks)


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_knowledge_base_regeneration_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    _build_into(first)
    _build_into(second)

    assert _tree_hashes(first) == _tree_hashes(second)
    assert not (first / "guides" / "astrology_of_death.md").exists()
    assert not (first / "normalized_books" / "astrology_of_death.md").exists()
