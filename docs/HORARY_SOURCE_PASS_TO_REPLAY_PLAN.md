# Horary Source-Pass To Replay Plan

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

## Purpose

This document defines how to upgrade completed `source-pass` slices into stronger judgment tests without introducing speculative chart reconstruction.

The key distinction is:

- `source-pass` = routing audit
- `replay` = judgment audit

The already-completed source-pass slices should not all be promoted in the same way. Some are ready for replay, some are only safe for image-assisted reconstruction, and some should remain doctrine/routing audits only.

## Promotion Rule

Do not promote a source-pass case into replay unless the chart can be reconstructed without inventing material chart inputs.

Safe promotion inputs:

1. exact cast date
2. exact cast time
3. exact cast location
4. or a published wheel/chart image with enough fidelity to reconstruct houses safely
5. or an original chart payload

Unsafe promotion inputs:

1. guessing the location from author nationality or website domain
2. inferring houses from prose alone when the wheel is not shown
3. rebuilding a chart from verdict text only
4. treating a forum timestamp as the chart timestamp without clear evidence

## Audit Ladder

Each completed source-pass case should be assigned one of three follow-up tracks.

### Track A: Direct Replay Candidate

Use this when the source gives:

- exact date
- exact time
- exact location

What to test:

- backend verdict
- backend reasoning/perfection family
- frontend normalized verdict
- backend/frontend parity

### Track B: Image-Assisted Replay Candidate

Use this when the source does not give full cast metadata, but does provide:

- a legible wheel
- visible house cusps
- enough planetary positions to reconstruct the payload safely

What to test:

- backend verdict
- backend reasoning family
- serialized replay stability
- frontend/backend parity

This is the same general safety model already used for the replay-ready external trio documented in:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_CUNNING_MAN_EXTERNAL_CORPUS.md`

### Track C: Doctrine-Only Permanent Source-Pass

Use this when the source provides:

- clear doctrinal framing
- clear category or significator rationale

but does not provide enough chart data for safe replay.

What to test:

- question type
- relevant houses
- quesited house
- intent
- doctrine notes

Do not force these into replay.

## How To Test The Already-Completed Slices

### Phase 1: Metadata Census

For every existing source-pass case from slices `2` through `18`, record:

1. exact date available: yes/no
2. exact time available: yes/no
3. exact location available: yes/no
4. wheel image available: yes/no
5. house cusps readable: yes/no
6. planetary positions readable: yes/no
7. article verdict explicit: yes/no
8. outcome/result explicit: yes/no

Output:

- one promotion table marking each case as `direct_replay`, `image_reconstructable`, or `doctrine_only`

### Phase 2: Promote Only The Safe Cases

After the census:

1. promote all `direct_replay` cases first
2. then promote `image_reconstructable` cases where the wheel is truly legible
3. leave `doctrine_only` cases as source-pass audits

This keeps the replay suite honest.

### Phase 3: Build Slice-Level Judgment Packs

For every promoted case, create:

1. replay fixture
2. backend replay test
3. frontend parity assertion where applicable
4. source-vs-engine result note

Recommended artifact pattern:

- `tests/fixtures/horary_external_<family>_replay.json`
- `tests/test_horary_external_<family>_replay.py`
- results doc in `docs/`

### Phase 4: Add A Middle Layer For Blocked Cases

For cases that cannot become replay safely, add a stronger doctrine audit than the current minimal source-pass format.

Suggested additions:

1. expected operative significators
2. expected turned-house derivation note
3. expected doctrine family
4. expected house priority note

This creates a better reasoning audit without pretending to be a chart replay.

## Recommended Order For Existing Slices

### Highest Priority

Start with cases most likely to be safely promotable:

1. Cunning Man article cases already closest to replay methodology
2. source-pass cases whose articles include clear wheels or strong timestamp context
3. timing/event cases where the published chart image is likely to be preserved

Why:

- these are the best chance to expand real judgment audit coverage quickly
- they also make the strongest backend/frontend parity checks

### Medium Priority

Promote forum or blog cases only when:

- the chart image is readable
- the post clearly shows enough chart structure

These can become Track B image-assisted replay cases.

### Lowest Priority

Keep as doctrine-only source-pass:

- anonymized cases
- discussion threads with missing or ambiguous chart metadata
- cases where the source explains the doctrine but does not preserve the chart

## Practical Next Step

The best next move is not another doctrine change.

It is a metadata census for the already-completed source-pass slices, producing:

1. a promotion table
2. a replay-ready shortlist
3. a blocked/doctrine-only shortlist

That gives a clean path from:

- router alignment

to:

- judgment alignment

without weakening evidence quality.

The first-pass census for that work now exists in:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_SOURCE_PASS_METADATA_CENSUS.md`
- `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_metadata_census.json`
