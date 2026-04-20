# Astrocartography Source Alignment Stress Test

## Purpose

This layer validates whether the current astrocartography goal models behave in a way that is consistent with curated source claims.

It is intentionally narrower than the historical city benchmark runner:

- source alignment asks whether the model logic matches the source claim
- historical benchmarking asks whether event cities beat controls on real cases

Both are necessary. Neither replaces the other.

## New Files

- `backend/astrocartography_source_alignment.py`
- `backend/run_astrocartography_source_alignment.py`
- `backend/benchmarks/astrocartography/source_alignment_cases.jsonl`
- `backend/test_astrocartography_source_alignment.py`

## What This Layer Tests

Each JSONL case encodes:

- a source claim
- a synthetic but source-faithful astrocartography pattern
- the expected leading goal model
- optional top-k and rank-order expectations

The runner converts the case into the same internal inputs used by `evaluate_goal_model(...)`:

- natal nearest-line rows
- natal crossings
- relocation features

This makes the suite stable. It avoids city-catalog drift, live geocoding drift, and chart-timestamp ambiguity.

## Why Not Use OCR Text Alone

Raw OCR books are useful, but they are a weak direct test target:

- they are noisy
- they mix definitions, anecdotes, and exceptions
- they often imply a polarity without naming a product goal directly

The correct workflow is:

1. read the source passage
2. restate the claim as a compact expectation
3. encode the smallest synthetic scenario that expresses that claim
4. freeze the case in JSONL
5. run the alignment suite on every model change

## Preferred Source Inputs

For astrocartography interpretation in this repo, source material falls into different roles:

- `horary_knowledge/astrocartography_books_text/The_AstroCartoGraphy_Book_of_Maps_-_The_Astrology_of_Relocation_How_136_Famous_People_Found_Their_Places_Jim_Lewis_Arielle_Guttman_z-library.sk_1lib.sk_z-lib.sk.txt`
  - best used as a case-study and angular framing source
- `horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md`
  - best used for normalized line and angle meaning claims

The source-alignment suite can cite either, but each case should name the exact source file and the compact claim being asserted.

## Dataset Shape

Each line in `source_alignment_cases.jsonl` is a JSON object with these fields:

- `enabled`
- `case_id`
- `label`
- `source`
- `natal_rows`
- `natal_crossings`
- `relocation_planets`
- `expected_lead`

Optional fields:

- `expected_in_top`
- `disallowed_in_top`
- `expected_above`
- `top_k`

`expected_above` is a list of objects:

```json
{"higher": "health_risk", "lower": "conflict"}
```

## Usage

From the repo root:

```powershell
python backend/run_astrocartography_source_alignment.py
python backend/run_astrocartography_source_alignment.py --case-id lewis_sun_publicity
python backend/run_astrocartography_source_alignment.py --output-json tmp/source-alignment.json --output-md tmp/source-alignment.md
python -m pytest backend/test_astrocartography_source_alignment.py -q
```

## How To Add A New Lewis/Guttman Case

1. Locate the passage and write down the exact claim being tested.
2. Decide which current goal model should lead if that claim is represented faithfully.
3. Build the smallest natal-line and crossing pattern that expresses the passage.
4. Add relocation house emphasis only where the claim clearly implies relocation behavior.
5. Freeze the case in `source_alignment_cases.jsonl`.
6. Run `python backend/run_astrocartography_source_alignment.py`.
7. If the case fails, either the model logic drifted or the encoded case is over- or under-specified. Fix the ambiguity before accepting the case.

## Relationship To Historical Benchmarks

Use the source-alignment suite when asking:

- did the model keep the intended polarity
- did a refactor invert a source-backed claim
- did a specialist goal collapse into the wrong neighbor

Use `backend/run_astrocartography_benchmark.py` when asking:

- does a real event city beat controls
- does transit overlay help or hurt
- does the product model outperform simpler heuristics

The two validation layers should move together:

- source alignment protects semantic intent
- historical benchmarks protect real-world usefulness

## Current Limits

- this suite is only as strong as its curated claim set
- it does not prove the source itself is correct
- it does not measure geography, city ranking, or live search behavior
- it should stay conservative and readable rather than bloated with every possible quote
