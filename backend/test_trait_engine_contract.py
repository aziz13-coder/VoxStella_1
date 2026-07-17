from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.traits.engine import TraitEngine, _load_dictionary_csv, _load_morin_keywords_safe, _load_traits_catalog, compute_guidance


def test_auxiliary_guidance_sources_are_restored():
    rows = _load_dictionary_csv()
    mk = _load_morin_keywords_safe()

    assert len(rows) >= 10
    assert (mk.get("houses") or {}).get("7", {}).get("keywords_primary")
    assert (mk.get("planets") or {}).get("Mars", {}).get("keywords_primary")
    assert (mk.get("sect") or {}).get("malefic_out_of_sect")

    guidance = compute_guidance(
        {
            "planet_status": {"Mars": {"strong": True, "afflicted": False}},
            "sign_emphasis": {"Aries": 2.0},
            "house": {"emphasis": {"1": 2}, "afflicted": {}},
            "planetary_aspects": [
                {"planet1": "Mars", "planet2": "Saturn", "aspect": "Square", "orb": 0.4, "afflicting": True}
            ],
        }
    )
    categories = {row["category"] for row in guidance}
    assert "Planet" in categories
    assert "Sign" in categories
    assert "House" in categories
    assert "Aspect" in categories


def test_traits_catalog_cache_invalidates_when_catalog_changes(tmp_path):
    traits_dir = tmp_path / "traits"
    catalog_dir = traits_dir / "catalog"
    catalog_dir.mkdir(parents=True)
    trait_file = catalog_dir / "sample.json"

    trait_file.write_text(
        json.dumps(
            {
                "id": "sample_trait",
                "name": "Sample Trait",
                "logic": {},
            }
        ),
        encoding="utf-8",
    )

    first = _load_traits_catalog(str(traits_dir))
    assert any(t.get("name") == "Sample Trait" for t in first.get("traits", []))

    time.sleep(1.05)
    trait_file.write_text(
        json.dumps(
            {
                "id": "sample_trait",
                "name": "Updated Trait",
                "logic": {},
            }
        ),
        encoding="utf-8",
    )

    second = _load_traits_catalog(str(traits_dir))
    assert any(t.get("name") == "Updated Trait" for t in second.get("traits", []))


def test_trait_engine_uses_restored_sources_for_keywords_and_guidance(tmp_path, monkeypatch):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    knowledge_dir = traits_dir / "knowledge"
    knowledge_dir.mkdir()
    knowledge_dir.joinpath("morin_keywords.json").write_text(
        json.dumps(
            {
                "houses": {
                    "1": {"keywords_primary": ["life", "temperament"]},
                },
                "planets": {
                    "Mars": {"keywords_primary": ["conflict", "boldness"]},
                },
                "sect": {},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("HORARY_BACKEND_DIR", str(tmp_path))
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "test_fire_trait",
                        "name": "Test Fire Trait",
                        "domain": "character_trait",
                        "description": "Test trait driven by fire emphasis.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 40},
                                {"kind": "planet_area", "planet": "Mars", "areas": ["life"], "min": 0.5, "weight": 6}
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    engine = TraitEngine(root=str(traits_dir))
    metrics = {
        "element_balance": {"Fire": 4.0, "Earth": 1.0, "Air": 1.0, "Water": 1.0},
        "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
        "flags": {"mercury_shock": True},
        "planet_status": {"Mars": {"strong": True, "afflicted": False}},
        "planetary_aspects": [],
        "house": {"emphasis": {}, "afflicted": {}},
        "planet_area_scores": {"Mars": {"life": 0.9}},
        "sign_emphasis": {},
    }

    profile = engine.evaluate(metrics, min_score=0)

    assert profile["summary"]["dominant_element"] == "Fire"
    assert profile["summary"]["dominant_modality"] == "Cardinal"
    assert profile["top_traits"][0]["id"] == "test_fire_trait"
    assert profile["top_traits"][0]["score"] == 100.0
    assert profile["top_traits"][0]["raw_score"] == 46.0
    assert profile["top_traits"][0]["max_score"] == 46.0
    assert profile["top_traits"][0]["support_hits"] == 2
    assert profile["top_traits"][0]["support_total"] == 2
    keywords = profile["top_traits"][0]["keywords"]
    assert keywords[:2] == ["life", "temperament"]
    assert "conflict" in keywords
    assert profile["guidance"][0]["category"] == "Planet"
    assert profile["guidance"][0]["term"] == "Mars"


def test_trait_engine_emits_layered_keywords_and_citations_from_corpus(tmp_path, monkeypatch):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    knowledge_dir = traits_dir / "knowledge"
    knowledge_dir.mkdir()
    knowledge_dir.joinpath("morin_keywords.json").write_text(
        json.dumps(
            {
                "houses": {},
                "planets": {
                    "Mercury": {"keywords_primary": ["learning", "speech"]},
                },
                "sect": {},
            }
        ),
        encoding="utf-8",
    )
    corpus_dir = tmp_path / "extracted_text_docs" / "new_sources_inspection"
    corpus_dir.mkdir(parents=True)
    (corpus_dir / "chunk_index.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "title": "Ancient Astrology in Theory and Practice",
                        "source_name": "Demetra George.pdf",
                        "chunk_id": "0007",
                        "path": str(corpus_dir / "chunks" / "demetra" / "chunk_0007.md"),
                        "pages": [188, 189],
                        "heading": "Scholarship and Mercury",
                        "chars": 300,
                        "excerpt": "Scholarship depends on Mercury, study, disciplined inquiry, and clear speech.",
                    }
                ),
                json.dumps(
                    {
                        "title": "Person Centered Astrology",
                        "source_name": "Dane Rudhyar.pdf",
                        "chunk_id": "0012",
                        "path": str(corpus_dir / "chunks" / "rudhyar" / "chunk_0012.md"),
                        "pages": [74, 75],
                        "heading": "Mental growth",
                        "chars": 280,
                        "excerpt": "Intellectual development and meaning-making shape the native's mental life.",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "catalog.json").write_text(
        json.dumps(
            [
                {
                    "title": "Ancient Astrology in Theory and Practice",
                    "guide_path": str(corpus_dir / "guides" / "demetra.md"),
                },
                {
                    "title": "Person Centered Astrology",
                    "guide_path": str(corpus_dir / "guides" / "rudhyar.md"),
                },
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("HORARY_BACKEND_DIR", str(tmp_path))
    monkeypatch.setenv("HORARY_TRAIT_CORPUS_DIR", str(corpus_dir))
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "scholarship",
                        "name": "Scholarship",
                        "domain": "cognitive_style",
                        "description": "Structured learning and disciplined thought.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["Carter: scholarship"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "planet_status", "planet": "Mercury", "strong": True, "weight": 20},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    profile = TraitEngine(root=str(traits_dir)).evaluate(
        {
            "element_balance": {"Fire": 1.0, "Earth": 1.0, "Air": 3.0, "Water": 1.0},
            "modality_balance": {"Cardinal": 2.0, "Fixed": 1.0, "Mutable": 1.0},
            "flags": {},
            "planet_status": {"Mercury": {"strong": True, "afflicted": False}},
            "planetary_aspects": [],
            "house": {"emphasis": {}, "afflicted": {}},
        },
        min_score=0,
    )

    trait = profile["top_traits"][0]
    assert profile["trait_enrichment_meta"]["morin_keywords_policy"] == "canonical_non_scoring"
    assert profile["trait_enrichment_meta"]["corpus_enrichment_policy"] == "parallel_non_scoring"
    assert profile["trait_enrichment_meta"]["corpus_index_path"] == str(corpus_dir / "chunk_index.jsonl")
    assert trait["keyword_layers"]["morin"] == trait["keywords"]
    assert trait["citation_summary"]["count"] >= 1
    assert trait["enrichment_status"]["morin_keywords"] == "present"
    assert trait["enrichment_status"]["citations"] == "present"
    assert any(citation["source_lineage"] in {"classical", "modern"} for citation in trait["citations"])
    assert trait["citations"][0]["locator"]["chunk_path"]
    assert trait["citations"][0]["locator"]["guide_path"]


def test_trait_engine_finds_short_bundled_packaged_corpus_layout(tmp_path, monkeypatch):
    backend_root = tmp_path / "backend"
    traits_dir = backend_root / "traits"
    traits_dir.mkdir(parents=True)
    knowledge_dir = traits_dir / "knowledge"
    knowledge_dir.mkdir()
    knowledge_dir.joinpath("morin_keywords.json").write_text(
        json.dumps(
            {
                "houses": {},
                "planets": {
                    "Mercury": {"keywords_primary": ["learning", "speech"]},
                },
                "sect": {},
            }
        ),
        encoding="utf-8",
    )
    corpus_dir = backend_root / "tc"
    corpus_dir.mkdir(parents=True)
    (corpus_dir / "chunk_index.jsonl").write_text(
        json.dumps(
            {
                "title": "Ancient Astrology in Theory and Practice",
                "source_name": "Demetra George.pdf",
                "chunk_id": "0007",
                "path": str(corpus_dir / "chunks" / "demetra" / "chunk_0007.md"),
                "pages": [188, 189],
                "heading": "Scholarship and Mercury",
                "chars": 300,
                "excerpt": "Scholarship depends on Mercury, study, disciplined inquiry, and clear speech.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "catalog.json").write_text(
        json.dumps(
            [
                {
                    "title": "Ancient Astrology in Theory and Practice",
                    "guide_path": str(corpus_dir / "guides" / "demetra.md"),
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("HORARY_TRAIT_CORPUS_DIR", raising=False)
    monkeypatch.delenv("HORARY_TRAIT_CORPUS_INDEX", raising=False)
    monkeypatch.delenv("HORARY_TRAIT_CORPUS_CATALOG", raising=False)
    monkeypatch.delenv("HORARY_REPO_ROOT", raising=False)
    monkeypatch.setenv("HORARY_BACKEND_DIR", str(backend_root))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("backend.traits.engine._candidate_backend_roots", lambda: [str(backend_root)])
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "scholarship",
                        "name": "Scholarship",
                        "domain": "cognitive_style",
                        "description": "Structured learning and disciplined thought.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["Carter: scholarship"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "planet_status", "planet": "Mercury", "strong": True, "weight": 20},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    profile = TraitEngine(root=str(traits_dir)).evaluate(
        {
            "element_balance": {"Fire": 1.0, "Earth": 1.0, "Air": 3.0, "Water": 1.0},
            "modality_balance": {"Cardinal": 2.0, "Fixed": 1.0, "Mutable": 1.0},
            "flags": {},
            "planet_status": {"Mercury": {"strong": True, "afflicted": False}},
            "planetary_aspects": [],
            "house": {"emphasis": {}, "afflicted": {}},
        },
        min_score=0,
    )

    trait = profile["top_traits"][0]
    assert profile["trait_enrichment_meta"]["corpus_index_path"] == str(corpus_dir / "chunk_index.jsonl")
    assert trait["enrichment_status"]["citations"] == "present"
    assert any(citation["source_lineage"] == "classical" for citation in trait["citations"])


def test_top_traits_prefer_non_weak_bands_when_available(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "weak_trait",
                        "name": "Weak Trait",
                        "domain": "test",
                        "description": "weak",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 10},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 10},
                                {"kind": "house_emphasis", "houses": [1], "min_total": 1, "weight": 10},
                                {"kind": "planet_status", "planet": "Sun", "strong": True, "weight": 10},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "possible_trait",
                        "name": "Possible Trait",
                        "domain": "test",
                        "description": "possible",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 17},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 17},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    engine = TraitEngine(root=str(traits_dir))
    metrics = {
        "element_balance": {"Fire": 4.0, "Earth": 1.0, "Air": 1.0, "Water": 1.0},
        "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
        "flags": {},
        "planet_status": {},
        "planetary_aspects": [],
        "house": {"emphasis": {}, "afflicted": {}},
    }

    profile = engine.evaluate(metrics, min_score=0)

    assert [t["id"] for t in profile["top_traits"]] == ["possible_trait"]
    assert {t["id"] for t in profile["traits"]} == {"weak_trait", "possible_trait"}


def test_trait_bands_require_corroboration_for_strong_labels(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "single_trigger",
                        "name": "Single Trigger",
                        "domain": "test",
                        "description": "single support only",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [{"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 12}],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "double_trigger",
                        "name": "Double Trigger",
                        "domain": "test",
                        "description": "corroborated support",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 12},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 12},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    engine = TraitEngine(root=str(traits_dir))
    metrics = {
        "element_balance": {"Fire": 4.0, "Earth": 1.0, "Air": 1.0, "Water": 1.0},
        "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
        "flags": {},
        "planet_status": {"Mars": {"strong": True, "afflicted": False}},
        "planetary_aspects": [],
        "house": {"emphasis": {}, "afflicted": {}},
    }

    profile = engine.evaluate(metrics, min_score=0)
    by_id = {trait["id"]: trait for trait in profile["traits"]}

    assert by_id["single_trigger"]["score"] == 100.0
    assert by_id["single_trigger"]["band"] == "likely"
    assert by_id["single_trigger"]["support_hits"] == 1

    assert by_id["double_trigger"]["score"] == 100.0
    assert by_id["double_trigger"]["band"] == "strong"
    assert by_id["double_trigger"]["support_hits"] == 2


def test_top_traits_collapse_identical_logic_families(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "variant_a",
                        "name": "Variant A",
                        "domain": "test",
                        "description": "same logic family A",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 12},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 12},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "variant_b",
                        "name": "Variant B",
                        "domain": "test",
                        "description": "same logic family B",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 12},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 12},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "other_family",
                        "name": "Other Family",
                        "domain": "test",
                        "description": "different logic family",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [{"kind": "element", "element": "Water", "min_share": 0.35, "weight": 12}],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    engine = TraitEngine(root=str(traits_dir))
    metrics = {
        "element_balance": {"Fire": 4.0, "Earth": 1.0, "Air": 1.0, "Water": 1.0},
        "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
        "flags": {},
        "planet_status": {"Mars": {"strong": True, "afflicted": False}},
        "planetary_aspects": [],
        "house": {"emphasis": {}, "afflicted": {}},
    }

    profile = engine.evaluate(metrics, min_score=0)
    top_ids = [t["id"] for t in profile["top_traits"]]
    traits_by_id = {t["id"]: t for t in profile["traits"]}

    assert top_ids == ["variant_a"]
    assert traits_by_id["variant_a"]["family_representative"] is True
    assert traits_by_id["variant_b"]["family_representative"] is False
    assert traits_by_id["variant_a"]["family_size"] == 2
    assert traits_by_id["variant_a"]["related_traits"][0]["id"] == "variant_b"


def test_top_traits_prefer_curated_over_provisional_variants(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "curated_trait",
                        "name": "Curated Trait",
                        "domain": "test",
                        "description": "properly curated trait",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 12},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 12},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "provisional_trait",
                        "name": "Provisional Trait",
                        "domain": "test",
                        "description": "placeholder trait pending Carter extraction",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["TBD source extraction"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 11},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 11},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    engine = TraitEngine(root=str(traits_dir))
    metrics = {
        "element_balance": {"Fire": 4.0, "Earth": 1.0, "Air": 1.0, "Water": 1.0},
        "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
        "flags": {},
        "planet_status": {"Mars": {"strong": True, "afflicted": False}},
        "planetary_aspects": [],
        "house": {"emphasis": {}, "afflicted": {}},
    }

    profile = engine.evaluate(metrics, min_score=0)
    by_id = {trait["id"]: trait for trait in profile["traits"]}

    assert by_id["curated_trait"]["source_status"] == "curated"
    assert by_id["curated_trait"]["provisional"] is False
    assert by_id["provisional_trait"]["source_status"] == "provisional"
    assert by_id["provisional_trait"]["provisional"] is True
    assert [t["id"] for t in profile["top_traits"]] == ["curated_trait"]


def test_top_traits_fall_back_to_provisional_when_no_curated_traits_exist(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "provisional_only",
                        "name": "Provisional Only",
                        "domain": "test",
                        "description": "placeholder entry still under review",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["placeholder"],
                        "logic": {
                            "base": 0,
                            "boosts": [{"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 12}],
                            "dampeners": [],
                            "escalators": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    engine = TraitEngine(root=str(traits_dir))
    metrics = {
        "element_balance": {"Fire": 4.0, "Earth": 1.0, "Air": 1.0, "Water": 1.0},
        "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
        "flags": {},
        "planet_status": {},
        "planetary_aspects": [],
        "house": {"emphasis": {}, "afflicted": {}},
    }

    profile = engine.evaluate(metrics, min_score=0)
    assert profile["top_traits"][0]["id"] == "provisional_only"
    assert profile["top_traits"][0]["provisional"] is True


def test_top_traits_prefer_general_summary_surfaces_over_specialized_indicators(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "general_trait",
                        "name": "General Trait",
                        "domain": "cognitive_style",
                        "description": "A general summary trait.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 12},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 12}
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "specialized_indicator",
                        "name": "Specialized Indicator",
                        "domain": "disease_infectious",
                        "description": "A medical-specialty indicator that should stay out of the summary by default.",
                        "confidence": "test",
                        "polarity": "negative",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Water", "min_share": 0.35, "weight": 20},
                                {"kind": "planet_status", "planet": "Neptune", "afflicted": True, "weight": 20}
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    engine = TraitEngine(root=str(traits_dir))
    metrics = {
        "element_balance": {"Fire": 4.0, "Earth": 1.0, "Air": 1.0, "Water": 4.0},
        "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
        "flags": {},
        "planet_status": {
            "Mars": {"strong": True, "afflicted": False},
            "Neptune": {"strong": False, "afflicted": True},
        },
        "planetary_aspects": [],
        "house": {"emphasis": {}, "afflicted": {}},
    }

    profile = engine.evaluate(metrics, min_score=0)
    by_id = {trait["id"]: trait for trait in profile["traits"]}

    assert by_id["general_trait"]["summary_surface"] == "general"
    assert by_id["general_trait"]["summary_eligible"] is True
    assert by_id["specialized_indicator"]["summary_surface"] == "specialized"
    assert by_id["specialized_indicator"]["summary_eligible"] is False
    assert [trait["id"] for trait in profile["top_traits"]] == ["general_trait"]


def test_any_aspect_and_any_angle_contact_support_marked_uranian_originality(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "marked_uranian_originality",
                        "name": "Marked Uranian Originality",
                        "domain": "cognition_originality",
                        "description": "Contract test for any Mercury-Uranus contact plus angular Uranus.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {
                                    "kind": "aspect",
                                    "pair": ["Mercury", "Uranus"],
                                    "type": "any",
                                    "max_orb": 6,
                                    "allowed_names": ["Conjunction", "Sextile", "Trine", "Square", "Opposition", "Quincunx"],
                                    "weight": 10
                                },
                                {
                                    "kind": "angle_aspect",
                                    "planet": "Uranus",
                                    "type": "any",
                                    "angle": "MC",
                                    "max_orb": 10,
                                    "weight": 8
                                }
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    engine = TraitEngine(root=str(traits_dir))
    metrics = {
        "element_balance": {"Fire": 1.0, "Earth": 1.0, "Air": 1.0, "Water": 1.0},
        "modality_balance": {"Cardinal": 1.0, "Fixed": 1.0, "Mutable": 1.0},
        "flags": {},
        "planet_status": {},
        "planetary_aspects": [
            {
                "planet1": "Mercury",
                "planet2": "Uranus",
                "aspect": "Quincunx",
                "orb": 1.8,
                "afflicting": True,
                "severity": "severe",
            }
        ],
        "angle_aspects": [
            {
                "planet": "Uranus",
                "angle": "MC",
                "aspect": "Opposition",
                "orb": 6.0,
                "afflicting": False,
                "severity": None,
            }
        ],
        "house": {"emphasis": {}, "afflicted": {}},
    }

    profile = engine.evaluate(metrics, min_score=0)
    trait = profile["traits"][0]

    assert trait["score"] == 100.0
    assert trait["support_hits"] == 2
    assert profile["top_traits"][0]["id"] == "marked_uranian_originality"


def test_top_traits_diversify_summary_buckets_before_reusing_one_bucket(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "stubborn_drive",
                        "name": "Stubborn Drive",
                        "domain": "temperament",
                        "description": "High-scoring character bucket trait.",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 12},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 12},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "unyielding_style",
                        "name": "Unyielding Style",
                        "domain": "character",
                        "description": "Another strong character bucket trait.",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Fire", "min_share": 0.35, "weight": 11},
                                {"kind": "planet_status", "planet": "Mars", "strong": True, "weight": 11},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "inventive_mind",
                        "name": "Inventive Mind",
                        "domain": "cognition_originality",
                        "description": "Distinct cognition bucket trait.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "aspect", "pair": ["Mercury", "Uranus"], "type": "any", "max_orb": 6, "allowed_names": ["Quincunx"], "weight": 10},
                                {"kind": "angle_aspect", "planet": "Uranus", "type": "any", "angle": "MC", "max_orb": 10, "weight": 8},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "social_bearing",
                        "name": "Social Bearing",
                        "domain": "social_function",
                        "description": "Distinct social bucket trait.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Water", "min_share": 0.20, "weight": 10},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    engine = TraitEngine(root=str(traits_dir))
    metrics = {
        "element_balance": {"Fire": 4.0, "Earth": 1.0, "Air": 1.0, "Water": 2.0},
        "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
        "flags": {},
        "planet_status": {"Mars": {"strong": True, "afflicted": False}},
        "planetary_aspects": [
            {
                "planet1": "Mercury",
                "planet2": "Uranus",
                "aspect": "Quincunx",
                "orb": 1.8,
                "afflicting": True,
                "severity": "severe",
            }
        ],
        "angle_aspects": [
            {
                "planet": "Uranus",
                "angle": "MC",
                "aspect": "Opposition",
                "orb": 6.0,
                "afflicting": False,
                "severity": None,
            }
        ],
        "house": {"emphasis": {}, "afflicted": {}},
    }

    profile = engine.evaluate(metrics, min_score=0)
    top_ids = [trait["id"] for trait in profile["top_traits"][:4]]
    by_id = {trait["id"]: trait for trait in profile["traits"]}

    assert by_id["stubborn_drive"]["summary_bucket"] == "character"
    assert by_id["unyielding_style"]["summary_bucket"] == "character"
    assert by_id["inventive_mind"]["summary_bucket"] == "cognition"
    assert by_id["social_bearing"]["summary_bucket"] == "social"
    assert top_ids == ["inventive_mind", "social_bearing", "stubborn_drive", "unyielding_style"]


def test_cognition_bucket_prefers_headline_intellectual_families_over_generic_cognition(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "generic_plain_speaking",
                        "name": "Generic Plain Speaking",
                        "domain": "communication_style",
                        "description": "Generic cognition-adjacent summary item.",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Air", "min_share": 0.20, "weight": 14},
                                {"kind": "planet_status", "planet": "Mercury", "strong": True, "weight": 14},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "scholarship",
                        "name": "Scholarship",
                        "domain": "cognitive_style",
                        "description": "Headline intellectual family.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [
                                {"kind": "element", "element": "Air", "min_share": 0.20, "weight": 11},
                                {"kind": "planet_status", "planet": "Mercury", "strong": True, "weight": 11},
                            ],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "social_bearing",
                        "name": "Social Bearing",
                        "domain": "social_function",
                        "description": "Distinct second bucket.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {
                            "base": 0,
                            "boosts": [{"kind": "element", "element": "Water", "min_share": 0.20, "weight": 10}],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    profile = TraitEngine(root=str(traits_dir)).evaluate(
        {
            "element_balance": {"Fire": 1.0, "Earth": 1.0, "Air": 3.0, "Water": 2.0},
            "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
            "flags": {},
            "planet_status": {"Mercury": {"strong": True, "afflicted": False}},
            "planetary_aspects": [],
            "house": {"emphasis": {}, "afflicted": {}},
        },
        min_score=0,
    )

    top_ids = [trait["id"] for trait in profile["top_traits"][:2]]
    by_id = {trait["id"]: trait for trait in profile["traits"]}

    assert by_id["generic_plain_speaking"]["summary_bucket"] == "cognition"
    assert by_id["generic_plain_speaking"]["summary_priority"] == 1
    assert by_id["scholarship"]["summary_priority"] == 3
    assert top_ids == ["scholarship", "social_bearing"]


def test_top_traits_by_polarity_preserves_neutral_and_negative_summary_candidates(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "positive_trait",
                        "name": "Positive Trait",
                        "domain": "social_function",
                        "description": "positive summary trait",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["contract test"],
                        "logic": {"base": 0, "boosts": [{"kind": "element", "element": "Water", "min_share": 0.20, "weight": 12}], "dampeners": [], "escalators": []},
                    },
                    {
                        "id": "neutral_trait",
                        "name": "Neutral Trait",
                        "domain": "drive",
                        "description": "neutral summary trait",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["contract test"],
                        "logic": {"base": 0, "boosts": [{"kind": "element", "element": "Fire", "min_share": 0.30, "weight": 12}], "dampeners": [], "escalators": []},
                    },
                    {
                        "id": "negative_trait",
                        "name": "Negative Trait",
                        "domain": "temperament_negative",
                        "description": "negative summary trait",
                        "confidence": "test",
                        "polarity": "negative",
                        "sources": ["contract test"],
                        "logic": {"base": 0, "boosts": [{"kind": "planet_status", "planet": "Saturn", "afflicted": True, "weight": 12}], "dampeners": [], "escalators": []},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    profile = TraitEngine(root=str(traits_dir)).evaluate(
        {
            "element_balance": {"Fire": 3.0, "Earth": 1.0, "Air": 1.0, "Water": 3.0},
            "modality_balance": {"Cardinal": 3.0, "Fixed": 1.0, "Mutable": 1.0},
            "flags": {},
            "planet_status": {"Saturn": {"strong": False, "afflicted": True}},
            "planetary_aspects": [],
            "house": {"emphasis": {}, "afflicted": {}},
        },
        min_score=0,
    )

    assert profile["top_traits_by_polarity"]["positive"][0]["id"] == "positive_trait"
    assert profile["top_traits_by_polarity"]["neutral"][0]["id"] == "neutral_trait"
    assert profile["top_traits_by_polarity"]["negative"][0]["id"] == "negative_trait"


def test_trait_engine_emits_source_lineage_metadata(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "carter_trait",
                        "name": "Carter Trait",
                        "domain": "social_function",
                        "description": "Carter-derived trait.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["Carter: Aquarius and friendship"],
                        "logic": {"base": 0, "boosts": [{"kind": "element", "element": "Air", "min_share": 0.20, "weight": 12}], "dampeners": [], "escalators": []},
                    },
                    {
                        "id": "classical_trait",
                        "name": "Classical Trait",
                        "domain": "cognitive_style",
                        "description": "Classical nativity trait.",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["Montulmo: Mercury and judgment"],
                        "logic": {"base": 0, "boosts": [{"kind": "planet_status", "planet": "Mercury", "strong": True, "weight": 12}], "dampeners": [], "escalators": []},
                    },
                    {
                        "id": "morin_trait",
                        "name": "Morin Trait",
                        "domain": "temperament",
                        "description": "Morin-linked trait.",
                        "confidence": "test",
                        "polarity": "neutral",
                        "sources": ["Morin: house determination"],
                        "logic": {"base": 0, "boosts": [{"kind": "house_emphasis", "houses": [1], "min_total": 1, "weight": 12}], "dampeners": [], "escalators": []},
                    },
                    {
                        "id": "provisional_trait",
                        "name": "Provisional Trait",
                        "domain": "temperament_negative",
                        "description": "placeholder trait to refine",
                        "confidence": "test",
                        "polarity": "negative",
                        "sources": ["to refine later"],
                        "logic": {"base": 0, "boosts": [{"kind": "planet_status", "planet": "Saturn", "afflicted": True, "weight": 12}], "dampeners": [], "escalators": []},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    profile = TraitEngine(root=str(traits_dir)).evaluate(
        {
            "element_balance": {"Fire": 1.0, "Earth": 1.0, "Air": 3.0, "Water": 1.0},
            "modality_balance": {"Cardinal": 2.0, "Fixed": 1.0, "Mutable": 1.0},
            "flags": {},
            "planet_status": {"Mercury": {"strong": True, "afflicted": False}, "Saturn": {"strong": False, "afflicted": True}},
            "planetary_aspects": [],
            "house": {"emphasis": {"1": 1}, "afflicted": {}},
        },
        min_score=0,
    )

    by_id = {trait["id"]: trait for trait in profile["traits"]}

    assert by_id["carter_trait"]["source_lineage"] == "carter"
    assert by_id["carter_trait"]["source_lineage_label"] == "Carter-derived"
    assert by_id["classical_trait"]["source_lineage"] == "classical"
    assert by_id["morin_trait"]["source_lineage"] == "morin"
    assert by_id["provisional_trait"]["source_lineage"] == "provisional"


def test_summary_prefers_source_backed_traits_when_scores_are_close(tmp_path):
    traits_dir = tmp_path / "traits"
    traits_dir.mkdir()
    (traits_dir / "traits.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "traits": [
                    {
                        "id": "editorial_trait",
                        "name": "Editorial Trait",
                        "domain": "cognitive_style",
                        "description": "editorial summary item",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["house-based synthesis"],
                        "logic": {
                            "base": 0,
                            "boosts": [{"kind": "planet_status", "planet": "Mercury", "strong": True, "weight": 13}],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "classical_trait",
                        "name": "Classical Trait",
                        "domain": "cognitive_style",
                        "description": "classical summary item",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["Montulmo: Mercury and judgment"],
                        "logic": {
                            "base": 0,
                            "boosts": [{"kind": "planet_status", "planet": "Mercury", "strong": True, "weight": 12}],
                            "dampeners": [],
                            "escalators": [],
                        },
                    },
                    {
                        "id": "other_bucket",
                        "name": "Other Bucket",
                        "domain": "social_function",
                        "description": "second summary bucket",
                        "confidence": "test",
                        "polarity": "positive",
                        "sources": ["Carter: friendship"],
                        "logic": {
                            "base": 0,
                            "boosts": [{"kind": "element", "element": "Water", "min_share": 0.20, "weight": 12}],
                            "dampeners": [],
                            "escalators": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    profile = TraitEngine(root=str(traits_dir)).evaluate(
        {
            "element_balance": {"Fire": 1.0, "Earth": 1.0, "Air": 2.0, "Water": 2.0},
            "modality_balance": {"Cardinal": 2.0, "Fixed": 1.0, "Mutable": 1.0},
            "flags": {},
            "planet_status": {"Mercury": {"strong": True, "afflicted": False}},
            "planetary_aspects": [],
            "house": {"emphasis": {}, "afflicted": {}},
        },
        min_score=0,
    )

    top_ids = [trait["id"] for trait in profile["top_traits"][:2]]
    summary_ids = [trait["id"] for trait in profile["summary_traits"][:2]]

    assert top_ids == ["classical_trait", "other_bucket"]
    assert summary_ids[0] == "classical_trait"
