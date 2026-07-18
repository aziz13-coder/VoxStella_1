# Astrocartography Runtime Findings

Date: 2026-04-04

## Scope

This note documents the current Astrocartography runtime behavior after manual QA exposed two issues:

1. PathFinder goal changes such as `Home` and `Money` appeared to point to the same place.
2. Inspector target text sometimes rendered as `[object Object], ...` and geocoded to a wrong live location.

## Main Finding

The Ohio result was not evidence that the goal models had collapsed into one formula. The immediate runtime problem was that the frontend sometimes sent a serialized object placeholder as the target string, which the backend then attempted to geocode.

The relevant request pattern was visible in `backend/horary_api.log`:

- `.../astrocartography/location?...goal_id=home&target_location=[object+Object]...`
- `.../astrocartography/location?...goal_id=money&target_location=[object+Object]...`

That malformed target was then resolved by live geocoding into a real address around London, Ohio.

## Current Product Flow

There are two separate Astrocartography operations:

### 1. Inspect one chosen place

This uses the `location` endpoint and scores one target against the currently selected goal model. It is the path used when the user clicks a city, uses a best-match pin, or presses `Inspect`.

### 2. Rank many places

This uses atlas search and evaluates a catalog of city candidates, then reranks the shortlist with relocation features. It is the path used by `Search Best Cities`.

Changing a PathFinder goal should change the scoring model, not silently choose a new place.

## What Was Wrong In Runtime

### Frontend target normalization

Astrocartography modal state could retain a non-string target object and reuse it as if it were a query string. That produced the `[object Object]` payload. The modal now normalizes target text before inspect, compare, and display operations.

### Goal switch behavior

Goal changes also triggered a fresh inspect cycle against the current target. That made the feature look as if changing the goal was selecting a place, when it was actually rescoring the same place. The goal change flow now clears inspect/compare state instead of auto-inspecting.

### Atlas ranking ambiguity

When a region had no meaningful positive signal, atlas search could still return population-ordered or tie-like results. That made low-signal cities look like valid "best matches". Atlas ranking now applies a minimum signal floor before returning ranked results.

## Backend Logic

### Atlas scoring

`rank_atlas_cities_for_goal(...)` in `backend/astrocartography_atlas_engine.py` currently does this:

1. Pull candidates from the shipped city catalog.
2. Optionally augment with live query candidates.
3. Score each city from natal line reading, crossings, and optional transit overlays.
4. Shortlist the highest raw candidates.
5. Re-score that shortlist with relocation features.
6. Filter out zero-signal or below-floor results.
7. Return both detailed results and a compact ranking payload.

The ranking output now includes:

- `candidate_count`
- `shortlisted_count`
- `viable_count`
- `signal_floor_raw_score`

### Goal model evaluation

`evaluate_goal_model(...)` in `backend/astrocartography_goal_engine.py` combines:

- natal line proximity
- crossings
- relocation features
- optional transit rows
- optional transit crossings

The current runtime models are explicit Vox Stella models rather than opaque recovered legacy formulas.

## Comparison To Sources

### What matches well

- The map-first product shape is aligned with the source research and legacy reference workflow.
- The runtime has distinct goal families such as `Home`, `Money`, `Love`, `Work`, `Career`, `Beliefs`, and others.
- Ranking uses line/crossing/relocation features in a way that is structurally consistent with the source material.

### What does not match exactly

- The formulas are not direct recovered Almagest `.PLS` / `.HYP` equations.
- The scoring is explicit and inspectable rather than black-box or numerically reverse-engineered.
- That means results are source-backed and differentiated, but not guaranteed to match a legacy application city-for-city.

## Concrete Example From QA

For the tested natal snap, switching between `Home` and `Money` while the target payload was malformed produced the same geocoded Ohio location because both goal changes were rescoring the same wrongly resolved target.

That does not prove the goal models are identical.

Separately, quick atlas probing showed that some narrow regional searches can legitimately produce no viable results under the current signal floor. In that case, the right answer is "no strong match surfaced here", not "this arbitrary city is your best option".

## Changes Applied

### Frontend

- Normalize target label/query text before inspect, compare, and display.
- Strip `[object Object], ...` payloads.
- Clear inspect/compare state on goal change instead of auto-inspecting.
- Clarify in the UI that choosing a PathFinder goal does not itself pick a city.

### Backend

- Reject serialized-object location payloads before geocoding.
- Do not live-search malformed target strings.
- Normalize atlas target labels and queries.
- Apply a signal floor before returning ranked atlas matches.

## Practical Outcome

After these changes:

- `Home` and `Money` no longer appear to select the same place because of malformed target state.
- Inspector labels are normalized for display and request generation.
- Atlas search is less likely to present noise as a meaningful best-city result.
- The feature behavior now better matches the intended source-driven workflow: choose a goal, then either inspect a place or run atlas search.

## Packaged Runtime Follow-up

Manual QA later exposed a separate packaged-only symptom: the installed desktop build could still show `internal_error` in the Astrocartography map while the source-run development version worked.

The follow-up findings are:

- The installed build uses a different snap store than source dev:
  - `%LOCALAPPDATA%\VoxStella\backend\snaps_store.json`
- A synthetic leap-day packaged snap is valid input.
- Running the current source backend against that packaged snap store succeeds:
  - natal bundle resolves correctly
  - astrocartography line generation returns 44 lines
  - global parans also build successfully

That means the snap data and the natal chart input are not the root cause of the packaged `internal_error`.

The remaining packaged-only issue is therefore in runtime/build behavior rather than chart content. The most important source-side packaged fix applied in this pass was Astrocartography resource resolution:

- runtime assets are now resolved through packaged-aware resource lookup
- backend packaging now explicitly includes `backend/knowledge/astrocartography`

So the practical reading is:

- dev success is real
- packaged snap data is also valid
- the old installed build still reflects pre-fix packaged runtime behavior and needs a fresh package cut to pick up the source fixes

To make any future packaged-only failure easier to diagnose, the Astrocartography frontend now preserves and displays backend `incident_id` values instead of showing only a bare `internal_error`.
