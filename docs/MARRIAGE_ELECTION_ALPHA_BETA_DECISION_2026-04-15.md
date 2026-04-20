Date: 2026-04-15
Scope: Marriage election workflow decision and implementation baseline.

# Decision Summary

The current marriage electioner stays in the product unchanged.

It becomes the `Alpha` marriage algorithm.

The new marriage engine will be introduced as a separate `Beta` algorithm, not as a rewrite of `Alpha`.

The product behavior will be:

- `Alpha` = the current Vox Stella marriage election workflow and scoring model
- `Beta` = the new marriage election workflow built for event chart + chart 1 + chart 2 analysis

For `Beta`, the user input model will be:

- `Snap A` = participant chart 1
- `Snap B` = participant chart 2

This means the intended UX is:

- keep the current marriage electioner available
- add a toggle for `Alpha` vs `Beta`
- use `Snap A` and `Snap B` only for the new `Beta` marriage path

# Exact Correspondence Requirement

`Beta` is not intended to be a loose reinterpretation of the Galaxy marriage workflow.

`Beta` is intended to correspond as exactly as practical to the logic documented in:

- `C:\Program Files (x86)\Galaxy\docs\research\electioner_marriage_astrological_logic.md`

That means:

- if the Galaxy marriage logic uses a calculation that Vox Stella does not currently expose, that calculation must be implemented first
- if the Galaxy marriage logic uses a body that Vox Stella does not currently calculate in the election stack, that body must be supported first
- `Beta` should not be treated as complete while it is still missing required Galaxy inputs

This changes the implementation standard for `Beta`:

- `Alpha` can remain the current Vox Stella model
- `Beta` must be built as a parity-oriented Galaxy branch

# Product Intent

The goal is not to replace the existing marriage electioner.

The goal is to preserve the current model for continuity, user familiarity, and benchmark stability, while adding a second marriage mode that tracks the Galaxy marriage workflow as closely as possible.

That gives a clean separation:

- `Alpha` preserves current behavior
- `Beta` becomes the Galaxy-parity path

# Current Baseline

The current election flow is:

- `AstroClock.jsx`
- `ElectionModal.jsx`
- `AstroClockAPI.electionStream()`
- `backend/astro_clock_api.py`
- `backend/election_models/marriage.py`

The current marriage implementation is structurally a single-score event scan with one optional natal overlay path.

Current code characteristics:

- the frontend has one marriage model entry, not an algorithm selector
- the modal supports only one optional natal source
- the backend route resolves only one natal chart bundle
- the marriage scorer returns one scalar score plus tags for each timestamp

That current baseline is exactly what should be preserved as `Alpha`.

# Agreed UI Direction

When the selected matter is `Marriage`, the modal should expose an algorithm selector.

Proposed selector:

- `Alpha`
- `Beta`

Expected behavior:

- default to `Alpha`
- keep the current `Alpha` controls intact
- when `Beta` is selected, show the new two-chart input path

`Alpha` mode should continue to use the existing input flow:

- `None`
- `Saved snap`
- optional `Include SR/LR weighting`

`Beta` mode should use a different input contract:

- `Snap A`
- `Snap B`

If `Beta` is selected, both snaps should be required before scan start.

# Agreed Backend Direction

The backend should treat `Alpha` and `Beta` as separate marriage algorithms under one shared `Marriage` matter.

Recommended contract additions:

- `marriage_algorithm=alpha|beta`
- `participant_a_snap_id`
- `participant_b_snap_id`

Recommended behavior:

- `alpha` keeps the current scoring path
- `beta` dispatches to a separate marriage scorer
- no silent mutation of the current scorer

This preserves backward compatibility and keeps regression risk low.

# Beta Workflow Target

The intended `Beta` marriage flow is:

1. Build the candidate event chart for each scanned timestamp.
2. Score the event chart as a marriage event chart.
3. Cross-score that same event chart against `Snap A`.
4. Cross-score that same event chart against `Snap B`.
5. Return a richer result shape than the current single-score row.

This is the main structural difference between the current system and the new one.

# Required Prerequisites For Beta

Before the full `Beta` marriage engine is implemented, some lower-level outputs need to exist first.

The first important prerequisite is almuten support.

At minimum, the new work should support:

- event `7th-house almuten`

Likely later expansion for participant-aware scoring:

- participant `1st-house almuten`
- participant `2nd-house almuten`
- participant `7th-house almuten`

The existing codebase already contains most of the dignity ingredients needed for this, including:

- domicile
- exaltation
- triplicity
- term
- face
- sect-aware triplicity selection

So the missing piece is a dedicated almuten helper and a stable output contract for it.

Another prerequisite is asteroid support when the Galaxy marriage logic depends on it.

The referenced Galaxy note explicitly includes:

- `17` Proserpina

So if `Beta` is meant to correspond to that logic, `17 Proserpina` cannot be treated as optional decoration.

It becomes part of the required calculation surface for the `Beta` branch.

In practice that means:

- confirm whether the current chart engine already computes `17 Proserpina`
- if not, implement asteroid calculation support before finishing the `Beta` scorer
- expose the asteroid output in a stable backend contract so the `Beta` logic can actually use it

The minimum `Beta` prerequisite set therefore includes:

- almuten support
- asteroid support required by the Galaxy marriage logic
- specifically `17 Proserpina` when reproducing the documented Galaxy branch

# Implementation Order

Recommended order of work:

1. Inventory every calculation and body used by the Galaxy marriage note.
2. Implement missing primitives in the backend, starting with almuten.
3. Implement missing asteroid support required by the Galaxy branch, including `17 Proserpina` if not already available in source.
4. Expose the needed almuten and asteroid outputs in chart or election data.
5. Add the `Marriage` algorithm toggle in the modal.
6. Add `Snap A` and `Snap B` for `Beta`.
7. Add backend `alpha|beta` dispatch for marriage.
8. Implement the new `Beta` marriage scorer against the documented Galaxy logic.
9. Expand the result payload if needed for event line + chart 1 line + chart 2 line output.

# Non-Goals For The First Slice

The first slice does not need to finish the entire `Beta` workflow.

It only needs to establish the foundation safely.

That means the first implementation slice can be:

- preserve current marriage as `Alpha`
- define the `Beta` contract
- build almuten support needed by the later `Beta` scorer
- add any missing asteroid support required for Galaxy parity

# Final Agreement

Yes:

- the current wedding or marriage electioner stays
- it becomes `Alpha`
- the new electioner is introduced as `Beta`
- `Beta` uses `Snap A` for chart 1
- `Beta` uses `Snap B` for chart 2
- `Beta` is expected to follow the Galaxy marriage logic as closely as possible
- if Galaxy logic depends on missing calculations such as almuten or `17 Proserpina`, those must be supported first

That is the agreed implementation direction for this feature.
