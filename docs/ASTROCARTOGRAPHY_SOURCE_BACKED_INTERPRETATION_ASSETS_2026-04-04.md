# Astrocartography Source-Backed Interpretation Assets

Date: 2026-04-04

## Purpose

This memo documents the switch from hardcoded interpretation copy to generated runtime assets backed by the repo-local Astrocartography knowledge base.

## Source Inputs

The runtime asset is built from:

- `horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md`
- `horary_knowledge/astrocartography_knowledge_base/reference/03_techniques_and_ranges.md`
- `horary_knowledge/astrocartography_knowledge_base/reference/05_feature_notes.md`

These files already distill the book corpus into:

- planet baselines
- angle modifiers
- interpretation-range policy
- product guidance for corpus-backed line explanations

## Build Pipeline

Builder script:

- `scripts/build_astrocartography_runtime_assets.py`

Generated runtime asset:

- `backend/knowledge/astrocartography/interpretation_runtime.json`

Backend loader:

- `backend/astrocartography_assets.py`

Consumer:

- `backend/astrocartography_service.py`

## What Is Now Source-Backed

- planet core themes
- common upside language
- common caution language
- angle-domain language
- user-facing angle shorthand
- an explicit supportive-and-difficult interpretation for every supported planet-by-angle combination
- primary and extended interpretation radii

## What Is Still Not A Final Model

The current reading layer is still intentionally limited.

It does not yet implement:

- goal-specific place-finder models like `Education`, `Love`, `Work`, or `Money`
- relocation-chart scoring
- paran/crossing ranking
- legacy Almagest-style multi-factor place selection

The current score is a distance-based proximity index derived from the source-backed radius policy. It is suitable for inspection and comparison, but it is not the final PathFinder engine.

## Practical Outcome

This change puts the current Astrocartography inspector on firmer ground:

- the geometry is algorithmic
- the descriptive copy is knowledge-base backed
- the distance policy is corpus backed
- the remaining non-source-specific logic is reduced to simple proximity ranking

The runtime asset is deterministic and checked against its source builder in
the test suite. Release checks can run:

`python scripts/build_astrocartography_runtime_assets.py --check`
