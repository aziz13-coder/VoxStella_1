Date: 2026-04-15
Status: Baseline contract implemented
Depends on: `MARRIAGE_ELECTION_ALPHA_BETA_DECISION_2026-04-15.md`

> Historical implementation note. The favorable/tense line contract,
> total/detail extraction, period segmentation, and birth-time precision gates
> listed below as incomplete were completed in July 2026. See
> `ELECTION_MODEL_REFERENCE_2026-07-31.md` for the current contract.

# Purpose

This note records the first implementation slice of the `Beta` marriage election model.

The goal of this slice is not to finish full Galaxy parity.

The goal of this slice is to make the `Beta` path real in product code by adding:

- the `Alpha` / `Beta` marriage algorithm selector
- the `Snap A` / `Snap B` participant contract
- backend `alpha|beta` marriage dispatch
- a separate baseline `Beta` scorer

This keeps the current marriage electioner intact as `Alpha` while creating a concrete place to build the parity-oriented `Beta` logic.

# Scope Of This Slice

Implemented in this phase:

1. Marriage algorithm selection in the election workflow.
2. Dual participant snap inputs for `Beta`.
3. Separate backend routing for `Alpha` vs `Beta`.
4. Initial `Beta` marriage scorer that uses:
   - a dedicated beta event-chart branch
   - participant `A` cross-score
   - participant `B` cross-score
5. Use of newly exposed prerequisites where practical:
   - almutens
   - asteroid support including Proserpina

Implemented now in source:

- frontend marriage workflow exposes `Alpha` and `Beta`
- `Beta` requires `Snap A` and `Snap B`
- backend validation enforces the two-snap requirement
- backend marriage dispatch now routes `Alpha` and `Beta` separately
- `Beta` currently scores:
  - the event branch via beta-native event tags and scoring
  - participant `A` cross-score
  - participant `B` cross-score
  - event 7th almuten / participant almuten links
  - event benefic support to participant anchors
  - event Mars/Saturn/Proserpina strain to participant anchors

Not completed in this phase:

- full `favorable` / `tense` graph channels per line
- full `Show total` vs `Show detail` thresholding parity
- full Galaxy period segmentation parity
- all precision-gated participant rules
- all documented outer-body and participant-house rules

# Product Contract

Marriage now has two algorithms:

- `Alpha`
- `Beta`

Rules:

- `Alpha` preserves the existing Vox Stella marriage scorer.
- `Beta` is a separate marriage scorer.
- `Beta` requires two participant snaps:
  - `Snap A`
  - `Snap B`

Current backend query contract:

- `marriage_algorithm=alpha|beta`
- `participant_a_snap_id`
- `participant_b_snap_id`

Current UI contract:

- if `Marriage` is selected, show an algorithm selector
- if `Alpha` is selected, keep the old natal source path
- if `Beta` is selected, require `Snap A` and `Snap B`

# Beta Baseline Logic In This Phase

The initial `Beta` scorer is deliberately separate from `Alpha`.

Its structure is:

1. Score the event chart using the beta-native event branch.
2. Cross-score the event chart against participant `A`.
3. Cross-score the event chart against participant `B`.
4. Combine those three layers into the final row score.

The important runtime guardrail is:

- beta must not surface alpha-only fallback or source-provenance tags
- beta event results should read as event-chart and participant-fit output, not as alpha runtime commentary

The participant cross-score currently starts from the clearest parity-oriented factors already available in source:

- event Jupiter
- event Venus
- event Ascendant
- event 7th-house almuten
- participant Ascendant
- participant MC
- participant 1st-house almuten
- participant 2nd-house almuten
- participant 7th-house almuten
- event Proserpina as a tense factor

This is a baseline parity direction, not the finished Galaxy branch.

Verification run for this slice:

- `python -m pytest backend/test_marriage_beta_contract.py -q`
- `npm test -- astroclockApi.test.mjs`
- `npm run lint`

# Why This Slice First

Without this slice, the repo still has only one real marriage engine.

That blocks all later work because:

- there is nowhere to route `Beta`
- there is no participant A / participant B contract
- UI work and backend work would drift apart

By landing this slice first, later work can extend the `Beta` branch directly instead of retrofitting a live production path under pressure.

# Next Steps After This Slice

1. Expand the `Beta` scorer toward explicit `favorable` and `tense` accumulation instead of one combined scalar.
2. Add richer result payloads for event line, participant line 1, and participant line 2.
3. Add more Galaxy-derived atomic rules into both the event and participant branches.
4. Add precision-aware participant logic where house-sensitive rules should degrade gracefully.
5. Add period-threshold logic that matches Galaxy more closely.

# Non-Negotiable Preservation Rule

`Alpha` must stay stable while `Beta` evolves.

If future `Beta` work creates uncertainty, it should stay contained in the `Beta` scorer and `Beta` UI path instead of changing the existing `Alpha` marriage workflow.
