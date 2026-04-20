# Horary Lost-Pet Stress Plan

Date: `2026-03-26`

## Goal

Harden the lost-pet branch of the horary engine after the recent doctrinal fix, and do it at the rule boundary where the last real defect occurred:

- question routing
- pet-family classification
- `/api/calculate-chart` request/response contract
- lost-pet location-clue preservation for frontend consumers

This is not a one-chart patch plan. The purpose is to confirm that lost-pet logic generalizes safely without leaking into adjacent domains such as pet health, lost documents, theft, or relationship return-home questions.

Important terminology note:

- this document now uses `lost-pet` for the replay corpus and user-facing feature area
- the engine's internal family label remains `missing`, so references to `pet_analysis.family = missing` are intentional code/doctrine terms

## Trusted Doctrine Basis

Primary local source:

- `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt`

Relevant source-backed points from the repo knowledge:

- missing animals are judged from the `6th house`
- mutual reception between significators supports the animal being found
- the `12th from the 6th` can show confinement such as a vet or shelter
- sign-based direction is part of the locating process

Secondary local source:

- `C:\Users\sabaa\Downloads\codexhorary\horary_knowledge\Horary Examples Traditional Horary Astrology By Example (Christodoulou, Fotini Cuperman, Leah Frawley etc.) (Z-Library)-1.txt`

Relevant repo-supported point:

- return-home language can be read literally in horary, so wording like `come home` should not be dismissed as non-locational by default

## Why This Is The Next Stress Target

The recent lost-pet defect was not caused by a single bad confidence weight. It was caused by the doctrinal seam between:

- `Category.PET`
- `Category.LOST_OBJECT`
- return/recovery wording
- route-level request normalization

That makes lost-pet the highest-value next stress area, because the same seam can silently misroute:

- `Will my dog come home?`
- `Where is my cat?`
- `Will my dog get better?`
- `Where is my passport?`
- `Will my boyfriend come home?`
- `Will the thief come back?`

If those boundaries drift, the engine can still return a superficially plausible answer while using the wrong house structure and the wrong doctrine.

## Current Verified Baseline

Already fixed and verified:

- lost-pet wording now routes to `Category.PET`
- the internal pet family now resolves to `missing`
- the engine now uses `pet_missing_balance`
- lost-pet location clues are emitted from the pet significator path
- the public Valkyrie lost-dog replay now aligns on recovery outcome

Existing supporting tests:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_missing_pet_doctrine.py`
- `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_lost_pet_replay.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\lostObjectLocationStress.test.mjs`

## Stress Areas To Implement

### Phase 1: Boundary Routing Stress

Add analyzer-level tests that assert adjacent phrasings land on the correct doctrine:

- lost pet -> `PET / missing / [1, 6]`
- pet health -> `PET / recovery / [1, 6]`
- lost passport -> `LOST_OBJECT / document / [1, 2]`
- boyfriend come home -> `RELATIONSHIP / outcome / [7, 1]`
- thief come back -> theft overlay with `[1, 2, 7]`

Purpose:

- prove the fix did not overreach
- prove the lost-pet doctrine does not swallow unrelated return-home questions

### Phase 2: Route Contract Stress

Add `/api/calculate-chart` tests for the lost-pet replay path using the real Flask route and the frontend request shape.

The route test must prove:

- the request uses `useCurrentTime` correctly
- the backend honors the manual 2025 chart timestamp rather than falling back to current time
- the response stays on `question_type = pet`
- `pet_analysis.family = missing`
- `traditional_factors.perfection_type = pet_missing_balance`
- `lost_object_location.applies = true`

An adjacent route test must prove:

- `Will my dog get better?` stays on the pet-recovery path
- it does not emit lost-pet location clues just because it is a pet question

### Phase 3: Frontend Preservation Stress

After the backend contract is stable, expand the frontend stress layer so a lost-pet result preserves:

- `Location Clues` tab visibility
- normalized payload integrity
- export/share payload integrity
- rerun behavior for saved charts

### Phase 4: External Replay Expansion

Only after the above seams are locked down, expand the external replay corpus with more source-backed lost-pet cases that have:

- trustworthy metadata
- a documented outcome
- enough locating testimony to compare outcome vs. projection substance

## Safety Constraint

Any lost-pet change must be treated as a shared horary-engine change.

At minimum, after each doctrinal edit rerun:

- lost-pet doctrine tests
- lost-object location tests
- route contract tests
- frontend `Location Clues` tests

If shared chart helpers or serialization change, also rerun the wider horary frontend parity layer.

## Implementation Started In This Pass

This pass starts Phase 1 and Phase 2 by adding:

- analyzer boundary-stress tests
- route-level contract tests for lost-pet replay and adjacent pet-recovery behavior

If those pass, the next implementation pass should start Phase 3 rather than introducing another doctrine change immediately.

## Status Update

Phase 1: implemented and passing.

- analyzer boundary-stress coverage now proves the lost-pet branch stays separate from:
  - pet recovery
  - lost passport
  - relationship return-home
  - theft return questions

Phase 2: implemented and passing.

- the real `/api/calculate-chart` route is now covered for:
  - `Will my dog come home?`
  - `Will my dog get better?`
- the contract test proves the frontend request shape must use `useCurrentTime: false`
- the route test also proves the manual `2025-01-06 23:19 America/New_York` timestamp is honored rather than silently falling back to current time

Phase 3: implemented and passing.

- frontend tab gating now treats legacy saved lost-pet charts as locational charts
- legacy lost-pet charts now show rerun guidance in the `Location Clues` tab just like legacy lost-object charts
- normalization and export tests now prove lost-pet location payloads survive rerun-style updates and AI/export payload building

## External Replay Expansion Status

The external lost-pet replay corpus is now materially expanded to five public cases, though still not complete.

- Promoted external replay:
  - Valkyrie Astrology, missing dog case
  - replay question: `Will my missing dog be found?`
  - replay inputs: `2025-01-06 23:19`, `Naples, New York`, `America/New_York`
  - source outcome: the dog was later recovered
  - verified result: aligned on `YES`

- Promoted external replay:
  - Patrick Watson, `The Horary Mystery of the Missing Cat`
  - replay question: `Will I find my cat alive?`
  - replay inputs: `2021-08-03 02:46`, `Phoenix, Arizona`, `America/Phoenix`
  - source outcome: the cat was not recovered alive; the post explains that an apparent Moon-Jupiter perfection was pre-empted by an earlier perfection to Mercury
  - verified result: aligned on `NO`

- Promoted external replay:
  - Astrology Weekly, `missing pet/horary`
  - replay question: `Where is my pet chow chow Biggie?`
  - replay inputs: `2005-12-28 13:18`, `Opelousas, Louisiana`, `America/Chicago`
  - source outcome: the dog came home the same night at `10:44 PM`
  - note on date:
    - the post body says `12/28/06`, but the thread itself is dated `December 28, 2005` and the follow-up recovery post is `December 29, 2005`
    - using `2005-12-28` is therefore an explicit source-grounded inference, not a guess
  - verified result: aligned on `YES`

- Promoted external replay:
  - Anthony Louis, `Where is my pet? Is he okay?`
  - replay question: `Where is the missing cat?`
  - replay inputs: `1993-08-30 09:20`, `London, England`, `Europe/London`
  - source outcome: the cat returned less than 24 hours later, meowing at the door after sunset
  - verified result: aligned on `YES`
  - locational substance:
    - engine projects a hidden or difficult-to-reach place first
    - direction cue is `West`
    - this is treated as substantively aligned because the published outcome is a quick return after hiding, not an exact-address proof case

- Promoted external replay:
  - Astrological Mind, `Where is Pukka?`
  - replay question: `Where is the cat?`
  - replay inputs: `2007-11-04 16:48`, `Melbourne, Australia`, `Australia/Melbourne`
  - source outcome: the cat returned in three days after hiding near the querent's apartment block, likely in or under an abandoned shed behind the building
  - verified result: aligned on `YES`
  - locational substance:
    - engine projects `West`
    - secondary place clues keep the search close to home / yard / doorway territory
    - this is treated as a partial but acceptable location alignment because the published outcome is a near-home hiding place rather than a distant route or confinement case

- What this replay exposed:
  - the lost-pet balance branch was reading only the primary positive perfection label
  - it was dropping the earlier secondary blocker already detected by the unified perfection core
  - this produced a false `YES` on the Patrick replay even though the underlying perfection timeline already contained a pre-empting `frustration`

- Fix now implemented:
  - the engine now passes the unified-core secondary perfection into the pet-missing snapshot
  - the pet-missing evaluator now treats an earlier `frustration`, `prohibition`, `refranation`, or `abscission` as blocking the apparent recovery route
  - this is a general doctrine fix for lost-pet replay cases, not a one-chart patch

- Verified result after the fix:
  - Valkyrie replay remains aligned on `YES`
  - Patrick replay now aligns on `NO`
  - Biggie replay aligns on `YES`
  - Anthony Louis / Frawley replay aligns on `YES`
  - Pukka replay aligns on `YES`

Holdbacks still not promoted:

- the strongest public forum-style secondary candidates still expose outcome discussion but not enough exact chart metadata in the fetched source text to support a replay-safe automated assertion

Current holdback examples:

- `Missing cat =(` on Astrology Weekly
  - confirms the cat returned
  - but the fetched page does not expose the exact horary chart metadata needed for deterministic replay
- `Will my cat return`
  - confirms the cat returned
  - but again the fetched page lacks replay-safe full chart metadata in the accessible text

This means the corpus is no longer a single-case replay. It now covers five public outcomes and sub-patterns:

- positive recovery after disappearance
- blocked / negative alive-recovery
- same-day return
- quick hidden return within a day
- near-home hiding followed by return in days

The correct next move for Phase 4 is:

- continue source hunting for at least one more replay-safe case
- prioritize a shelter / confinement or injured-return case to diversify the outcome classes
- do not promote forum anecdotes unless date, time, location, and outcome are all defensible enough to replay
