# AstroClock Synastry Hardening Plan

Date: 2026-04-02

## Goal

Improve the current synastry engine where it still feels too product-led and not yet doctrinally mature.

This pass targets five weak points:

1. the overall score is too dependent on heuristic bar blending
2. the aspect model is too coarse
3. the scored point set is too narrow
4. the current dimensions flatten attraction, compatibility, attachment, and burden
5. the engine underuses source-backed "lack filling" and asymmetry logic

## Product Direction

The feature stays aligned to the current AstroClock workflow:

1. input remains snap A plus snap B
2. output remains trait-profile-style ranked bars
3. the report must stay source-governed and auditable
4. the UI should support richer doctrine without turning into a full research console

## Implementation Scope

### 1. Expanded scored point set

Use the existing chart payload more fully:

1. keep Sun through Saturn as the core layer
2. add Uranus, Neptune, and Pluto as an optional modern layer
3. add North Node and derived South Node as an optional nodal layer
4. add Chiron when available as an optional healing/wound layer
5. add Descendant and IC as derived angles so angle logic is not limited to Ascendant and Midheaven

### 2. Better aspect doctrine

Replace the fixed five-aspect model with a point-class-aware model:

1. retain conjunction, opposition, square, trine, sextile
2. add quincunx and semisextile by default
3. allow semisquare and sesquiquadrate in the engine, but keep them off in the default report until the source catalog grows further
4. use tighter orb handling for minor aspects
5. use orb modifiers by point class:
   - luminaries and angles get the widest allowance
   - personal planets stay medium
   - outers, nodes, and Chiron stay tight
6. boost exactitude and note applying/separating when chart speed data is available

### 3. New user-facing dimensions

Replace the old six-bar structure with a clearer doctrinal split:

1. `resonance`: emotional familiarity and instinctive understanding
2. `communication`: mental exchange and verbal fit
3. `attraction`: chemistry, magnetism, erotic pull
4. `compatibility`: practical ease, affection style, shared values, day-to-day fit
5. `attachment`: binding power, durability, loyalty, long-term staying force
6. `growth`: expansion, perspective, compensation, developmental value
7. `friction`: conflict, argument, volatility, mutual irritation
8. `burden`: heaviness, obligation, inhibition, karmic or duty-like weight

This solves the current flattening problem:

1. attraction is no longer mixed into general support
2. compatibility is separated from binding power
3. burden is separated from ordinary friction

## 4. Overall score doctrine

The overall score should stop being a direct average-minus-penalty summary of the bars.

New approach:

1. build a doctrine profile from raw positive evidence, raw challenge evidence, binding evidence, and compensation evidence
2. compute `overall_score` from supportive strength vs difficult strength, then adjust modestly for binding and compensation signals
3. expose the components used to compute overall so the score is inspectable
4. generate summary lines from the strongest governed evidence, not only from category totals

This will still be scoring math, but it will be transparent and much less arbitrary than the current direct blend.

## 5. New source-backed signal families

### Lacks and compensation

Add governed signals for:

1. missing elements filled by the partner
2. missing modalities filled by the partner
3. empty-house filling when the partner activates a house that is empty natally
4. previously unaspected natal personal planets becoming activated by the partner

### Asymmetry and balancing logic

Add governed signals for:

1. above-horizon vs below-horizon balancing
2. eastern vs western hemisphere balancing
3. directional overlay imbalance, so one-sided activation is visible instead of hidden in totals

### Additional affinity logic

Add governed signals for:

1. sign-house affinity from March/McEvers
2. nodal contacts as a meaningful but not automatically positive layer
3. selected outer-planet attraction/intensity patterns already described in the source books

## API and UI changes

### Backend

Add synastry options:

1. `include_modern`
2. `include_nodes`
3. `include_chiron`
4. `orb_profile`

### Frontend

Expose a compact advanced row in the synastry modal:

1. modern planets toggle
2. nodes toggle
3. Chiron toggle
4. orb profile selector

Keep the default UX light:

1. the new bars render in the same score-card style already used
2. advanced options stay optional
3. lineage and evidence continue to be visible

## Verification

This pass requires:

1. contract tests for expanded categories and overall components
2. tests for point extraction with modern planets, nodes, and Chiron
3. tests for lack filling and asymmetry families
4. lint for the modal and API client

## Done Criteria

This hardening pass is complete when:

1. the engine uses the expanded point set and richer aspect policy
2. the report exposes the new dimensions
3. lack/asymmetry logic contributes governed evidence
4. the overall score includes explainable components
5. the frontend can request the new options and render the new shape cleanly
