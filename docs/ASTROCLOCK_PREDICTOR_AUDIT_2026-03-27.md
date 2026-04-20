# Astro Clock Predictor Audit 2026-03-27

## Scope

This audit covers the `Run Predictor` workflow in Astro Clock:

- frontend predictor request flow in `frontend/src/features/astroclock/TransitsModal.jsx`
- frontend request serialization in `frontend/src/features/astroclock/api.mjs`
- backend predictor route in `backend/astro_clock_api.py`
- shared transit hit generation already provided by `backend/transits_morin.py`

The goal was to compare the predictor behavior against the repo's Morin-facing source basis, especially Book 22 of *Astrologia Gallica*, and correct algorithm or render seams without forcing topic-specific output.

## Source-facing standard

The Morin points that matter most here are:

- effects must be judged by radical determination, not by generic universal signification
- concurrence of both termini matters
- one should judge whether an effect occurs before over-committing to the kind of effect
- transits/directions/revolutions operate by partial determinations and require careful topic discrimination

Operationally, that means a predictor should not rank rows only by the strongest isolated transit. It should also recognize repeated determined support across the scanned window.

## Workflow before the fix

### Frontend

- `Run Predictor` reused the raw scan step from the scan UI.
- If the user scanned daily (`1440` minutes), predictor also ran daily.
- Predictor cards were rebuilt locally from the flat backend `predictions` list.
- Local ranking favored the strongest isolated occurrence, not sustained window support.

### Backend

- `/api/astro-clock/predictor` returned:
  - flat `predictions`
  - `peaks`
  - optional `series`
- It did not return grouped window-level summaries.
- Predictor ranking therefore pushed the frontend toward single-hit emphasis.

## Confirmed issues

### 1. Coarse scan steps blurred predictor localization

This was a real workflow bug.

If a user scanned at `720m` or `1440m`, predictor inherited that coarse step. For event work, that can flatten multiple meaningful windows into a few generic rows.

### 2. Predictor ranking over-valued isolated spikes

This was a real algorithm issue at the predictor layer.

The route exposed only flat per-step predictions, and the frontend rebuilt cards by grouping them and sorting mainly by maximum probability and maximum score. That over-weighted one strong occurrence instead of repeated determined support through the window.

This is weaker than Morin's determination-and-concurrence logic.

### 3. Predictor keywords were too thin

The predictor cards mostly showed tags, not a stable aggregated keyword layer derived from:

- event type
- life area
- prediction tags

That made the frontend less transparent than the backend data allowed.

### 4. Predictor windows were not real windows

This was a real algorithm bug.

The grouped predictor summaries were aggregating by event family across the whole scanned range, even when the same signal only appeared in disconnected bursts hours or days apart.

That could create a misleading single `start -> end` window that was actually multiple separate support phases.

This is weaker than Morin's concurrence logic, because a predictor should surface contiguous support windows, not merge distant recurrences into one synthetic period.

## Implemented fixes

### Backend

Added grouped predictor summaries in:

- `backend/astro_clock_api.py`
- `frontend/backend/astro_clock_api.py`

New backend payload fields:

- `step_minutes`
- `prediction_groups`

Each group now includes:

- `event_type`
- `life_area`
- `label`
- `description`
- `transit`
- `count`
- `start`
- `end`
- `dominant_timestamp`
- `support_score`
- `probability_max`
- `probability_mean`
- `score_max`
- `score_mean`
- `determination_strength_max`
- `significance_max`
- `domain_alignment_max`
- `tags`
- `keyword_tokens`
- `occurrences`

The new group ranking is support-based and window-aware. It still preserves the existing flat `predictions` list for compatibility.

### Predictor plateau localization improvement

After the grouped-card fix, one real algorithm seam still remained:

- `/api/astro-clock/predictor` was still choosing `peaks` from the generic peak builder used by the scan routes
- that meant a flat plateau could still promote the wrong representative row when one timestamp carried stronger event-family support than the others
- in practice, the predictor cards were more Morin-facing than the peak timestamps themselves

This was corrected by adding a predictor-specific peak builder that:

- computes a grouped event-family summary per row from the row's own predictions
- prefers the row with the strongest determined support inside a flat plateau
- then uses domain alignment, probability, step score, and hit count as tie-breakers

The predictor payload `peaks` now includes additive summary fields:

- `event_type`
- `life_area`
- `description`
- `transit`
- `support_score`
- `keyword_tokens`

This keeps the existing `timestamp/count/step_score/tone` contract intact while making the predictor peak strip semantically closer to the grouped predictor cards.

### Frontend

Updated:

- `frontend/src/features/astroclock/TransitsModal.jsx`

Changes:

- predictor now uses a finer step of at most `60` minutes even when the scan step is coarser
- predictor results prefer backend `prediction_groups` when present
- predictor cards now render:
  - `support score`
  - average probability
  - aggregated keyword tokens
- the UI explains when predictor is using a finer step than the current scan step

### Contiguous support-window fix

Predictor grouping now splits repeated occurrences into separate windows when the gap between them exceeds the active predictor step band.

New grouped payload fields now better represent actual windows:

- `support_density`
- `window_span_minutes`
- `window_steps`
- `cluster_index`

This means the predictor card range shown in the UI is now a real contiguous support window rather than a merged all-range recurrence bucket.

### Window-localization and peak-spacing follow-up

One more real predictor seam remained after the grouped-window pass:

- group-window localization was still adding a very large flat bonus to every row inside a support window
- that bonus could overpower the row's own `raw_step_score` and row-localization signal
- long windows therefore drifted toward early or dominant rows even when the exact event row itself was still strong
- the peak strip could also fill up with adjacent hourly rows from the same support phase, crowding out equally valid peaks later in the window

This was corrected in `backend/astro_clock_api.py` and its mirrored packaged-backend source by:

- changing group-window localization into a modest distance-weighted support nudge
- weighting proximity to both the support-window midpoint and the dominant occurrence
- spacing predictor peaks across the window so adjacent redundant hours do not occupy the whole peak strip

This makes predictor localization more honest:

- support windows still matter
- but they no longer flood the score enough to drown the row's own signal
- and the peak strip now behaves like a distributed list of candidate windows rather than one repeated hourly cluster

### Balanced support-window ranking follow-up

One more ranking seam remained after the localization and peak-spacing pass:

- grouped predictor windows were still sorted by raw accumulated support first
- that could let a long diffuse window outrank a shorter, cleaner support window
- Morin-style concurrence is better served by a balance between sustained support and concentration, not raw total alone

This was corrected in `backend/astro_clock_api.py` and the mirrored frontend fallback path in `frontend/src/features/astroclock/TransitsModal.jsx` by:

- adding a grouped `support_focus` metric
- computing it as `sqrt(support_score * support_density)` when both are positive
- sorting grouped windows by `support_focus` before raw total support

This keeps repeated support valuable, but stops raw total alone from dominating the predictor summary.

## What was not changed

- shared transit hit generation in `backend/transits_morin.py`
- the flat per-hit prediction generation contract
- the existing replay slices and event classifications

This was intentionally kept additive. The fix was applied at the predictor aggregation and render seam, not by forcing different topic labels in the transit engine.

## Expected user-visible effect

After the fix:

- daily/coarse scan settings no longer make predictor equally coarse
- repeated moderate support can outrank one isolated stronger hit in the predictor summary
- predictor keyword chips reflect the grouped signal more clearly
- predictor peak timestamps are less likely to point at a generic row when the same flat plateau contains a stronger event-family row
- disconnected recurrences no longer masquerade as one long predictor window
- shorter, stronger support windows are less likely to be buried under longer diffuse windows
- the predictor view is closer to a Morin-style "determined window support" read instead of a raw "single best row" read
- long support windows no longer overpower stronger local rows just because the window starts earlier
- the peak strip is less redundant and better distributed across the scanned range
- equivalent support windows from overlapping transit variants are now merged instead of repeating three near-identical cards
- predictor support windows now preserve supporting transit variants without flooding the top list with duplicates
- the per-step predictor candidate pool is broader, so lower-ranked but still determined event families are less likely to be dropped before grouping

## Verification

Targeted checks:

- `python -m pytest tests/test_transits_route_contract.py tests/test_transit_predictor_replay_slice_3.py -q`
- `npm exec vitest run src/tests/transitsModalReplay.test.jsx src/tests/astroclockApi.test.mjs src/tests/astroClockModeFlow.test.jsx --config vitest.config.mjs`

Plateau-localization checks:

- predictor route contract now verifies that a flat plateau chooses the stronger event-family row rather than the next generic row
- predictor replay slice 3 now asserts that the first peak exposes event-family metadata
- frontend replay coverage now verifies that the predictor peak strip renders the richer peak summary

Window-localization checks:

- predictor route contract now verifies that long grouped windows act as a modest localization nudge instead of a flood bonus
- predictor route contract now verifies that adjacent hourly peaks are spaced out so later valid peaks are not crowded off the strip

Contiguous-window checks:

- predictor route contract now verifies that separated recurrences are split into distinct predictor windows instead of being merged into one broad range

Balanced-focus checks:

- predictor route contract now verifies that a shorter concentrated window can outrank a longer diffuse one even when the diffuse window has the larger raw total support
- frontend replay coverage now verifies that the modal fallback orders support windows by balanced focus when `prediction_groups` are absent

Merged-window checks:

- predictor route contract now verifies that equivalent windows for the same event family are merged into one support window
- merged windows preserve `supporting_transits` so the UI can still show the main transit plus overlapping variants
- the frontend replay coverage now verifies that merged support windows render `Also supported by ...` instead of repeated duplicate cards

Broader follow-up recommended:

- rerun the full promoted transit replay suite
- build the frontend bundle

## Remaining limitations

- predictor peaks are now more localized and less redundant, but they are still not a full event-family-specific Morin timing model
- the flat `predictions` list still exists and can look more generic than the grouped summary
- this improves Morin-facing predictor behavior, but it does not claim universal correctness for all mundane event classes
