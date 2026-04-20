# Business Beta Parity Review

Date: 2026-04-18

Source note:

- `C:\Program Files (x86)\Galaxy\docs\research\electioner_business_astrological_logic.md`

Reviewed code paths:

- `backend/election_models/business_beta.py`
- `backend/astro_clock_api.py`
- `frontend/src/features/astroclock/ElectionModal.jsx`
- `frontend/src/features/astroclock/api.mjs`

## Resolved

1. Per-line model

- Business beta no longer returns only a flat aggregate contract.
- `score_business_beta_election()` now returns:
  - one `event` line
  - one `participant` line per founder-owner chart
  - aggregate `value`, `tags`, `pros`, and `cautions`
- The stream route now preserves `lines` on scored rows, and the Election modal shows those lines in the selected-window panel.

2. Support network conjunctions

- The supportive network in business beta now uses sextiles and trines only.
- Conjunctions remain available only for resonance-style checks where the code is intentionally modeling direct alignment rather than the source support network.

3. Planetary timing

- Business beta no longer scores a separate planetary day ruler bonus.
- The business beta timing score now uses planetary hour support only, which is the documented timing rule in the source note.
- The backend still forces traditional timing context on so the planetary hour can be computed consistently during scans.

4. Alpha-only business overlays in beta

- Business beta no longer consumes alpha-style overlays on the backend:
  - `include_fixed_stars`
  - `include_lunation_screen`
  - `emphasize_commerce`
  - `business_mode`
- The business beta UI now hides those controls and keeps only the timing control visible.
- The request builder already stopped sending those alpha-only options for business beta.

## Current Contract

Backend business beta result shape:

```json
{
  "value": 12.4,
  "tags": ["..."],
  "pros": ["..."],
  "cautions": ["..."],
  "lines": [
    { "id": "event", "kind": "event", "label": "Event line", "score": 8.6, "tags": ["..."] },
    { "id": "participant:1", "kind": "participant", "label": "Founder A", "score": 2.1, "tags": ["..."] }
  ]
}
```

Frontend behavior:

- business beta keeps founder-owner participant selection
- business beta hides alpha-only overlays
- business beta renders the returned per-line breakdown inside the selected-window card

## Remaining Gaps Needing More Source Confidence

1. Participant precision gate

- The source note conditions some Ascendant-based founder-fit logic on chart precision.
- The current repo does not yet enforce a confidence gate before applying those Ascendant resonance checks.
- We need a reliable source of participant chart precision from saved snaps before implementing that strictly.

2. Threshold and graph semantics

- The source note describes line-based semantics, but it is still not fully clear whether each line has independent pass-fail thresholds, weighting bands, or display rules beyond "show them separately".
- The repo now preserves separate lines, but it still ranks windows by aggregate total.

3. Resonance vs support boundaries

- The source note is explicit about sextile/trine support networks.
- It is less explicit about whether direct conjunctions are still allowed for separate resonance checks like founder Asc to event Asc or other exact-contact logic.
- The current implementation still allows conjunctions in those resonance checks.

4. Hidden Galaxy implementation details

- The decoded note is strong, but it may still omit implementation details such as normalization, threshold clipping, tie-breaking, or scan-ranking behavior.

## Research Prompt For Another AI Agent

Use this prompt as-is:

```text
Research the business beta election model in this repo against the source note at:

C:\Program Files (x86)\Galaxy\docs\research\electioner_business_astrological_logic.md

Repo paths to inspect first:

- C:\Users\sabaa\Downloads\codexhorary\backend\election_models\business_beta.py
- C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py
- C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx
- C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs
- C:\Users\sabaa\Downloads\codexhorary\backend\test_business_beta_contract.py

Your task:

1. Determine whether the current business beta implementation fully adheres to the source note.
2. Identify every remaining gap between the repo implementation and the source logic.
3. Separate confirmed gaps from uncertain gaps where the source note is incomplete or ambiguous.
4. Focus especially on:
   - whether participant Ascendant resonance requires a chart-precision gate
   - whether any conjunction-based resonance checks are allowed by the source, or whether beta should use sextile/trine support only everywhere
   - whether each line should have its own threshold, grading band, or independent UI treatment
   - whether aggregate ranking across event plus participant lines matches the source intent
   - whether any other alpha-only overlays are still leaking into business beta behavior
   - whether the source implies any hidden weighting normalization, caps, tie-breakers, or filtering rules not yet implemented
5. Produce a written gap report with:
   - exact file and line references in the repo
   - exact source-note references
   - a status for each item: resolved, confirmed gap, likely gap, or unclear source
   - concrete implementation guidance for each confirmed gap
6. If the source note is insufficient for a strict implementation, say exactly what additional evidence would be needed.

Do not make code changes. Deliver a report only.
```

## Verification

- `python -m pytest backend\test_business_beta_contract.py -q`
- `npm run test:ui -- src/tests/electionModalHelpers.test.mjs`
- `npm run build`

Finding 5 about Electron startup was already addressed in earlier work and is not part of this business-beta parity pass.
