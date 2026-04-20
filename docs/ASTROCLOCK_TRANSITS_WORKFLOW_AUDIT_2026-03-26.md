# Astro Clock Transits Workflow Audit

## Executive Summary

The Astro Clock transit feature is a multi-step workflow layered on top of shared natal chart resolution and the Morin transit engine. The safest way to improve it is to treat the transit modal as a contract boundary first and the scoring core second.

Confirmed current issue:

- The frontend transit modal hardcoded house system `R` instead of using the active Astro Clock house system. That means transit compute, scan, predictor, and export requests could diverge from the user-selected house system used elsewhere in Astro Clock.

Why corrections here are sensitive:

- The backend transit core in `backend/transits_morin.py` is reused by multiple routes, not only the transit modal.
- `backend/astro_clock_api.py` also proxies natal transit hits into other Astro Clock flows when `include_sr_lr` is enabled.
- Window scan, predictor, stream, and export paths all share the same natal bundle contract and most of the same filters.
- Timezone and manual datetime normalization happen at the frontend request layer, so frontend bugs can silently skew otherwise-correct backend calculations.

## Frontend Workflow

Entry point:

- `frontend/src/features/astroclock/AstroClock.jsx`

How it works:

1. Clicking `Transits` opens `TransitsModal` and pauses realtime Astro Clock updates.
2. The modal supports two natal sources:
   - manual natal datetime/location/timezone
   - saved Astro Clock snap
3. The modal supports four main actions:
   - single timestamp compute via `/api/astro-clock/transits`
   - window scan via `/api/astro-clock/transits/window`
   - predictor via `/api/astro-clock/predictor`
   - CSV exports via `/api/astro-clock/transits/export` and `/api/astro-clock/transits/window/export`
4. Window scan prefers the SSE route `/api/astro-clock/transits/window/stream` and falls back to REST if streaming fails.
5. Clicking a timeline bar feeds that timestamp back into the single-timestamp transit computation.
6. Closing the modal resumes realtime Astro Clock updates.

High-risk frontend seams:

- House system propagation from Astro Clock into `TransitsModal`
- `buildIso(...)` timezone normalization and DST handling
- request serialization for filters and context windows
- stream fallback behavior when SSE fails
- export queries staying consistent with compute/scan queries

## Backend Workflow

Primary route file:

- `backend/astro_clock_api.py`

Transit route family:

- `/api/astro-clock/transits`
- `/api/astro-clock/transits/window`
- `/api/astro-clock/predictor`
- `/api/astro-clock/transits/window/stream`
- `/api/astro-clock/transits/export`
- `/api/astro-clock/transits/window/export`

Shared backend contract:

1. Resolve natal input through `_natal_from_query(...)`
   - `natal_snap_id`, or
   - `natal_datetime` + `natal_location` + optional `natal_timezone`
   - optional `house_system_code` overrides natal bundle creation
2. Run Morin transit computation through `backend/transits_morin.py`
3. Optionally enrich hits with concordance and prediction scoring
4. Return wrapped JSON payloads or CSV downloads

Shared backend logic that needs extra care:

- `compute_morin_transits_to_natal(...)`
- `scan_morin_transits_window(...)`
- `enrich_hits_with_concordance(...)`
- `_prepare_natal_context(...)`
- `_compute_hits_with_ctx(...)`

Extra caution:

- `transits_window` currently computes PD windows in two separate blocks before scanning. That duplication is regression-prone and should be tested before refactoring.
- `predictor` allows explicit observer `location/timezone` overrides, while `transits/window` currently uses natal observer context. That divergence is real and should be preserved or changed deliberately, not accidentally.

## Shared Consumers / Regression Risk

Transit core changes can affect more than the transit modal.

Known downstream reuse:

- election/other Astro Clock workflows that request `include_sr_lr`
- any route that proxies top natal transit hits from `compute_morin_transits_to_natal(...)`
- transit CSV export routes
- transit stream and predictor route families

Practical implication:

- Avoid changing `backend/transits_morin.py` unless a route-contract or replay-style test proves a real logic defect.
- Prefer fixing request plumbing, serializer issues, and route mismatches first.

## Test Strategy

What should be covered first:

1. Backend route contracts
   - confirm natal bundle resolution handoff
   - confirm observer location/timezone behavior
   - confirm filter propagation
   - confirm window center/range fallback
   - confirm stream produces progress and done payloads
   - confirm export endpoints stay aligned with compute/scan parameters

2. Frontend request contracts
   - `getTransits(...)`
   - `getTransitsWindow(...)`
   - `createTransitsWindowStream(...)`
   - `getPredictions(...)`
   - `exportTransits(...)`
   - `exportTransitsWindow(...)`

3. Frontend Astro Clock integration
   - active house system must flow into `TransitsModal`
   - modal open/close must not break realtime pause/resume behavior

4. Only after contracts are locked down:
   - transit scoring quality tests
   - replay-style transit examples
   - predictor/window localization validation

## Implemented Guardrails In This Pass

- frontend house-system propagation fix from Astro Clock into `TransitsModal`
- backend transit route-contract tests
- frontend transit serializer tests
- frontend integration regression test proving the live Astro Clock house system reaches the transit modal
- shared transit prediction persistence fix:
  - `prediction.eventType` is now persisted on normal render paths, not only on fallback exceptions
  - explicit crisis/war tokens now outrank generic relationship/honor tokens when both are present
- relationship-domain normalization fix:
  - generic `Relationship` cues no longer auto-collapse into `marriage`
  - mixed-house domains like the 7th now preserve `relationships` unless stronger marriage/conflict evidence exists
- predictor/stream plateau fix:
  - flat high-score plateaus now pick the local highest-count representative row instead of an arbitrary midpoint
- frontend fallback parity fix:
  - the modal now applies the same crisis-first priority when `prediction.eventType` is absent

## Remaining Caution Areas

- Source-grounded replay slices now exist for:
  - single-timestamp public-authority events
  - public-honor announcement events
  - a predictor/window-localized subset
  - a bounded public-crisis support subset on real war/violent-event dates
  - a predictor/stream crisis-support retention subset for those same war/violent-event dates
  - a bounded marriage-support subset on two replay-safe royal wedding charts
  - a bounded pre-event control sweep on selected single-route honor, crisis, and marriage cases
  - a one-case war-response keyword slice on George W. Bush's Iraq address
  - a one-case recent-war response slice on Israel's national chart using the February 28, 2026 `22:28` IDF broad-strike update
- The stream-first scan path now also has replay coverage on a bounded subset of cases, not just serializer/contract coverage
- stream replay slice 4 should now be read as a retention/proximity seam:
  - exact event rows are preserved
  - predictor-aware peaks are preserved
  - but raw streamed row-rank bounds are looser than predictor/window on Sergio and Al Gore even after the later localization fixes
- Predictor/window validation is still narrower than the single-timestamp corpus and should not yet be generalized to every event class
- Marriage/family milestone replay is also still narrower than the public-authority slice:
  - current coverage only supports bounded marriage-support claims
  - slice 8 confirms Charles remains stronger than earlier controls on the single `/transits` route (`81.0` vs `27.0` and `0.0` after the relationship-domain fix)
  - probing did **not** justify promoting marriage-support into predictor/stream replay assertions
  - it does not yet justify broad wedding or childbirth localization claims
- War/death remains the weakest replay class:
  - the current engine more often preserves crisis support in retained event-row transit factors than as a clean top prediction title
  - the slice-6 fix keeps deeper per-step prediction candidates so predictor/stream stop dropping those crisis-support factors
  - the March 27 crisis-priority fix improves event typing on those rows, but slice 9 still only promotes Bush on a single-route war-response seam
  - slice 10 adds one recent-war same-day support case on Israel's national chart, but it remains a single-route support-layer claim, not broad war localization
  - future war/death slices should stay at the support-hit layer unless the route starts replaying stronger event-type labels
- The duplicated PD-window logic in `/api/astro-clock/transits/window` is still present and should be refactored only after stronger tests exist
