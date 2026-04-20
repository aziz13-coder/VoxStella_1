# Astro Clock Transit Re-Audit Report
## 2026-03-28

This report records a fresh second-pass audit of the transit feature after the earlier audit cycle had already been closed.

The purpose of the re-audit was:
- to verify that the current source state still matches the Morin-facing baseline
- to confirm that the replay corpus and route contracts still hold after the later fixes
- to catch any drift between the backend semantics and the current frontend presentation

## Re-audit scope

The re-audit followed the same 7-part structure again:

1. source baseline
2. event-family wording and keyword taxonomy
3. backend algorithm
4. route contract parity
5. replay corpus
6. frontend rendering parity
7. workflow/performance seams

## What changed in this re-audit

This re-audit found one fresh baseline drift in the shared house-domain labels.

The shared label layer had become slightly broader and more modern than the Morin baseline in several places:

- `wealth`
- `children`
- `health`
- `relationships`
- `death`
- `belief`
- `honors`
- `shared_resources`
- `secrets`

Those labels were tightened in:

- `backend/nlg_templates.py`
- `frontend/backend/nlg_templates.py`
- `frontend/src/features/astroclock/TransitsModal.jsx`

The new direction is stricter:

- `wealth` now leads with acquired goods
- `children` now uses bodily pleasures instead of a creative-modern default
- `health` now leads with illness/service/subordinates
- `relationships` now reflects marriage/contracts/lawsuits/open enemies
- `death` now no longer leads with generic debts/crisis wording
- `belief` now leads with religion/journeys
- `honors` now leads with action/profession/dignity/fame
- `shared_resources` and `secrets` now read more explicitly as project shorthand layered on top of the source baseline

That work is documented in:

- `docs/ASTROCLOCK_TRANSIT_REAUDIT_PHASE1_2026-03-28.md`

## Revalidated in this re-audit

The full promoted backend transit suite was rerun successfully:

- `69 passed`
- `54 subtests passed`

That rerun covered:

- public authority slice
- public honor slice
- predictor localization slice
- stream retention slice
- public crisis slices
- marriage support slice
- pre-event control slice
- war-response slice
- recent war-response slice
- route contract tests
- context-layer tests
- transit quality tests

The frontend transit suite was also rerun successfully:

- `66 passed`

That rerun covered:

- modal replay rendering
- Astro Clock API request contracts
- Astro Clock mode-flow wiring

The production frontend build also passed again.

## What this re-audit confirms

This second pass confirms that:

- the replay corpus still survives the current source state
- the route parity fixes remain intact
- the predictor grouping/ranking fixes remain intact
- the stream-ticket licensing fallback remains intact
- the frontend still renders the promoted slices consistently
- the source-facing label layer is now slightly tighter than it was at the end of the previous cycle

## What this re-audit did not overturn

The re-audit did not uncover a new backend algorithm regression.

The previously accepted limitations still stand:

- a crisis chart can still surface a benefic or honors-heavy top row if that row is genuinely stronger in the current ranking model
- exact-time can retain a valid conflict row without predictor showing a sustained crisis support window for the same time range
- project taxonomy still contains shorthand that is not literal Morin wording, even where it is now more source-sensitive

## Remaining gaps

No new correctness bug was exposed by the source-side re-audit.

The main remaining practical gap is still live packaged-app parity:

- source/dev/frontend parity is well covered
- packaged-app parity still depends on testing the running packaged app instance after restart

That is now better treated as a deployment/live-parity check, not as an open source-code transit bug.

## Bottom line

The re-audit did not reopen the transit feature as unstable.

It found one real shared wording drift, corrected it, and confirmed that the broader transit stack still holds under:

- source baseline review
- replay corpus rerun
- backend contract rerun
- frontend replay rerun
- build verification

So the current transit feature should still be treated as:

- materially audited
- replay-backed on its promoted slices
- source-sensitive in its visible wording
- still bounded in its claims

It should not be treated as a universal event prediction engine.
