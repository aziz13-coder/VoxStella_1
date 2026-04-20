# Astro Clock Final Transit Audit Report
## 2026-03-28

This report closes the current transit audit cycle.

It states:
- what was audited
- what was corrected
- what the feature can safely claim
- what limitations still remain

It is meant to be the final reference point after the source, algorithm, replay, rendering, and workflow passes.

## Audit coverage completed

The transit audit covered:

- Morin-facing source alignment
- house-domain vocabulary
- event-family wording
- backend route parity
- exact-time, scan, predictor, and stream consistency
- replay slices against public dated events
- frontend rendering parity
- workflow and performance seams visible in live use

Primary supporting docs:

- `docs/ASTROCLOCK_TRANSITS_MORIN_SOURCE_SUMMARY_2026-03-28.md`
- `docs/ASTROCLOCK_TRANSIT_KEYWORD_SOURCE_AUDIT_2026-03-27.md`
- `docs/ASTROCLOCK_TRANSIT_EVENT_FAMILY_AUDIT_2026-03-28.md`
- `docs/ASTROCLOCK_TRANSIT_ALGORITHM_FINDINGS_2026-03-27.md`
- `docs/ASTROCLOCK_PREDICTOR_AUDIT_2026-03-27.md`
- `docs/ASTROCLOCK_COMPLETE_TRANSIT_AUDIT_PLAN_2026-03-28.md`

## What was fixed

### Backend algorithm and route fixes

- Exact-time routes now retry minimal enrichment before falling back to raw hits, instead of silently degrading.
- Scan, predictor, and stream now reuse the same core transit engine path instead of drifting on a scan-only logic branch.
- Predictor grouping now respects contiguous support windows instead of merging separated recurrences into one false range.
- Predictor window ranking now balances total support and concentration instead of letting long diffuse windows dominate.
- Predictor plateau selection now prefers stronger event-family rows inside flat peaks instead of picking arbitrary neighboring rows.
- Equivalent predictor windows are merged so overlapping transit variants reinforce one support window instead of flooding the list with duplicates.
- Predictor family diversity is preserved better by widening the per-step candidate pool and de-duplicating same-family windows.

### Frontend parity and rendering fixes

- The exact-time card no longer hides real crisis/conflict rows behind purely benefic-looking summaries.
- `Critical Signals` now stays visible and uses coherent crisis-family selection instead of mixing unrelated accident, death, prison, and conflict chips together.
- The scan graph now follows backend `step_score` instead of a divergent local score, so the graph and peak selection agree.
- Timeline bars are accessible controls rather than decorative bars only.
- The exact-time result no longer shows contradictory empty-state text when real content is already visible.
- The modal now defaults to the replay-safe transit flags used by the promoted slices.
- The modal no longer narrows exact-time requests with overly aggressive default `sensitive_*` filters.
- Predictor cards now render merged support windows with reinforcing `supporting_transits` instead of repeated duplicate cards.

### Workflow and performance fixes

- Predictor requests now use a longer timeout and auto-clamped step size for long windows.
- Scan and exact-time date/time input layout was widened so the year is visible and native input is usable.
- Stream-ticket requests are now skipped entirely when the renderer already knows there is no usable license token, which removes avoidable `402` noise in unlicensed states while keeping the fallback path intact.

### Source-sensitivity and wording fixes

- 7th-house labels no longer collapse generic relationships into marriage by default.
- 12th-house labels no longer over-default to imprisonment or generic secrets.
- 3rd, 6th, 10th, and 12th house default labels are more consistent with the Morin baseline.
- Wealth, relationship, home, travel, religious, study, publication, and crisis-family labels were rewritten to be narrower and more source-sensitive.
- Revolution support cards no longer lead with tautological Sun/Moon return labels as if those were meaningful signals by themselves.

## Replay corpus status

Promoted replay coverage exists for:

- public authority
- public honor
- predictor localization
- stream retention
- public crisis
- marriage support
- pre-event controls
- war response
- recent war response

These slices are useful as bounded validation slices, not universal claims.

## Safe claims

The transit feature can now safely claim:

- it applies a Morin-facing, determination-led transit workflow rather than a purely generic keyword scan
- exact-time, window scan, predictor, and stream are materially more aligned than before
- promoted replay slices are source-backed and tested against real dated public events
- the frontend now surfaces the same core signal families the backend returns, instead of routinely hiding them behind unrelated summaries
- predictor output is better understood as support-window clustering, not a single isolated hit picker

## Claims that should still be avoided

The transit feature should not claim:

- that it universally predicts wars, deaths, or geopolitical events
- that every crisis chart will headline the crisis row as the top overall prediction
- that predictor support windows are a full Morin timing model
- that project keyword taxonomy is identical to Morin’s own wording
- that replay success on promoted slices proves all event families are solved

## Current accepted limitations

- A crisis chart can still have a benefic or honors-heavy top prediction row if that row is genuinely stronger in the current ranking model.
- Exact-time can retain a valid conflict row while predictor support windows do not surface the same family if the crisis testimony is isolated rather than sustained.
- Some project taxonomy remains broader than literal Morin wording, even after the wording passes.
- The replay corpus is strong enough for bounded claims, but it is not exhaustive across all mundane event classes.

## Residual technical risks

These are not current transit correctness failures, but they remain open technical items:

- Python dependency warnings around `pytz` and legacy datetime handling
- frontend bundle size warning during Vite build
- live packaged-app parity still depends on the running backend/app instance actually being restarted after source fixes

## Recommended next work

The current transit audit cycle should be treated as complete.

The next work should only start if one of these happens:

- a new live parity mismatch is reproduced in the packaged app
- a new replay-safe event family is added
- a user-facing ranking problem is reproduced repeatedly on real charts

If transit work resumes, the next pass should be one of:

- packaged-app live parity audit on 3 to 5 promoted slices
- new replay slice construction for a genuinely new event family
- targeted ranking refinement for cases where the principal visible signal is still semantically wrong

## Bottom line

The transit feature is materially more defensible now than it was at the start of the audit.

The biggest improvements came from:

- route unification
- predictor-window logic
- frontend parity
- source-sensitive wording
- crisis-family coherence

The feature is now in a state where it can be used and described with tighter boundaries and fewer hidden mismatches, but it should still be presented as a determination-led transit analysis system with bounded replay validation, not as a universal event prediction engine.
