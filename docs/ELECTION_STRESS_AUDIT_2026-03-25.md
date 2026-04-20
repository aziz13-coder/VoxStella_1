# ELECTION_STRESS_AUDIT_2026-03-25

## Executive Summary

This follow-up audit moved from the earlier election workflow review into deterministic stress validation of the live election stack and the individual election scorers.

Technical workflow confirmed:

1. `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\AstroClock.jsx:859-860` pauses realtime before opening the election scanner.
2. `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\AstroClock.jsx:1477-1481` mounts `ElectionModal` and passes `onJumpToTime` plus `defaultHouseSystem`.
3. `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\ElectionModal.jsx:221-320` builds election options, opens `AstroClockAPI.electionStream(opts)`, and falls back to `validateElection(opts)` on stream failure.
4. `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:267-282` mints a stream ticket, and `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs:510-567` serializes election validate/stream requests.
5. `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:3312-3385` serves `/api/astro-clock/election/validate`, `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:3389-3687` serves `/api/astro-clock/election/suggest/stream`, and `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py:3587-3669` parses model-specific options before dispatch.

Stress validation status:

- Backend route workflow matrix now exercises every registered election matter through the real Flask route.
- Backend model stress matrix now differentially tests all 11 election models against favorable vs degraded setups.
- Frontend Astro Clock API coverage now verifies election option serialization through the stream-ticket path.

Implemented source-level fixes were kept local to election models:

1. Haircut: Bonatti's Gemini exception is now enforced.
2. Journey: short-journey scoring now considers the Part of Fortune and its ruler.
3. Business: Part of Fortune payload handling now accepts the actual computed lot shape (`fortune` and `lon`).
4. Surgery: Bonatti's preference for the Moon in a fixed sign for cutting procedures is now modeled.

## Knowledge Sources Used

Primary user-supplied sources:

- `C:\Users\sabaa\Desktop\astrolgy books\Bonatti on Elections Treatise 7 of Guido Bonattis Book of Astronomy (Benjamin Dykes) (z-library.sk, 1lib.sk, z-lib.sk).pdf`
- `C:\Users\sabaa\Desktop\astrolgy books\631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.pdf`

Working text sources used for automation/citation:

- `C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt`

Key doctrinal references applied:

1. Bonatti page 67: haircuts should use common signs except Gemini.
2. Bonatti page 75: short journeys should adapt the Ascendant, Moon, Part of Fortune, their rulers, the 3rd house, and the hour lord.
3. Bonatti page 103: surgery by iron should prefer the Moon in increased light, fortified by benefics, in a fixed sign, and not in the sign ruling the body part.
4. Bonatti page 112: marriage elections should prefer fixed Ascendant and Moon, especially Taurus or Leo, and avoid Scorpio/Aquarius.
5. Bonatti page 131: in lawsuits/contentions, the 10th signifies victory and the 4th signifies the ending/verdict.
6. Morin `C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt:2148-2165`: natal promise plus directions/revolutions/transits are the ideal election basis.
7. Morin `C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt:2767-2781`: identify the matter house first, fortify it, then erect the election.
8. Morin `C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt:2847-2851`: use mobile signs for journeys and fixed signs for lasting matters such as marriage.
9. Morin `C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt:2928-3030`: fortify the house of the matter and avoid afflicted Moon/Asc ruler conditions.

Product policy retained:

- Morin's natal requirement remains an ideal layer, not a hard blocker, because the app intentionally allows transit-only election scoring when natal data is unavailable.

## Implemented Fixes

### 1. Haircut model: Gemini is now a Bonatti exception

Evidence:

- `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\haircut.py:26`
- `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\haircut.py:41`

Change:

- `Gemini` now scores negatively and is labeled `Bonatti exception: Moon in Gemini – avoid haircut timing`.

Reason:

- Bonatti page 67 explicitly carves Gemini out of the otherwise favorable common-sign haircut rule.

Risk:

- Election-local only. No Astro Clock or shared chart contract changes.

### 2. Journey model: short journeys now score the Part of Fortune and its ruler

Evidence:

- `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\journey.py:145-172`

Change:

- Short-journey scoring now reads the Part of Fortune from either precomputed `arabic_parts` or computed lots.
- It adds deterministic tags for Fortune placement and Fortune-ruler angularity/cadency/retrogradation.

Reason:

- Bonatti page 75 explicitly includes the Part of Fortune and its ruler in short-journey elections.

Risk:

- Election-local only. No shared helper changes.

### 3. Business model: Part of Fortune lot payload bug fixed

Evidence:

- `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\business.py:430-453`

Change:

- The scorer now accepts the lot keys actually produced by the app's lot computation (`fortune`, `lon`) in addition to older title-cased fallbacks.

Reason:

- The previous branch was too strict about lot key shape and could silently skip intended business Fortune scoring.

Risk:

- Election-local only. No route/schema changes.

### 4. Surgery model: Moon in fixed sign now receives an explicit cutting-procedure bonus

Evidence:

- `C:\Users\sabaa\Downloads\codexhorary\backend\election_models\surgery.py:236-240`

Change:

- Cutting procedures now receive a small positive tag/score when the Moon is in a fixed sign: `Moon in fixed sign (surgery stability)`.

Reason:

- Bonatti page 103 explicitly says the Moon should be in a fixed sign for surgery by iron.

Risk:

- Election-local only. No shared Astro Clock or chart projection change.

## Stress Corpus Added

### Backend model stress matrix

File:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_election_stress_matrix.py`

Coverage:

1. `test_haircut_prefers_common_signs_except_gemini_from_bonatti`
2. `test_short_journey_prefers_part_of_fortune_support`
3. `test_business_prefers_fortune_in_gain_houses`
4. `test_contract_penalizes_new_deals_under_mercury_retrograde`
5. `test_marriage_prefers_fixed_taurus_frame_over_aquarius_scorpio_mix`
6. `test_surgery_prefers_fixed_moon_for_cutting`
7. `test_legal_prefers_judicial_favor_over_hostile_court_signature`
8. `test_beautification_penalizes_forbidden_moon_signs`
9. `test_conception_prefers_fertile_supportive_frame_over_afflicted_frame`
10. `test_viral_content_prefers_social_benefics_and_direct_mercury`
11. `test_battle_prefers_direct_mars_for_attack`

Test method:

- These are differential assertions. Each test compares a more source-aligned election frame against a less source-aligned frame and asserts on score direction plus the required supporting tags.
- This avoids brittle prose matching and checks the actual doctrinal levers the models claim to use.

### Backend workflow matrix

File:

- `C:\Users\sabaa\Downloads\codexhorary\tests\test_election_workflow_matrix.py`

Coverage:

- Registered matters exercised through the real `/api/astro-clock/election/validate` and `/api/astro-clock/election/suggest/stream` routes:
  - marriage
  - surgery
  - contract
  - business
  - journey
  - haircut
  - legal
  - beautification
  - viral
  - battle
  - conception

What it protects:

- Flask route registration
- election option parsing
- scorer dispatch
- SSE `done` payload shape used by Astro Clock

### Frontend workflow contract

File:

- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\astroclockApi.test.mjs:78-141`

Coverage:

- Ensures `AstroClockAPI.electionStream(...)` serializes election options into the ticketed stream path with the snake_case parameter names the backend expects.

What it protects:

- The seam between `ElectionModal` camelCase options and Flask request parsing.

## Test Execution

Backend:

```powershell
python -m pytest tests\test_election_stress_matrix.py tests\test_election_workflow_matrix.py tests\test_election_route_contracts.py tests\test_election_morin_rules.py tests\test_battle_election.py tests\test_beautification_election.py tests\test_conception_gender.py tests\test_haircut_moon_phases.py tests\test_viral_content.py -q
```

Result:

- `47 passed, 1 warning`

Frontend:

```powershell
npx vitest run src/tests/astroclockApi.test.mjs src/tests/electionStreamState.test.mjs src/tests/astroClockModeFlow.test.jsx --config vitest.config.mjs
```

Result:

- `17 passed`

## Current Status

What is now covered well:

1. End-to-end election route workflow through Astro Clock.
2. Stress-differential scoring behavior in every current election model.
3. The most defensible Bonatti-derived haircut, short-journey, and surgery rules.
4. The business Fortune branch that was previously vulnerable to lot-payload shape drift.

What remains only partially automated:

1. Bonatti's full short-journey checklist is not fully modeled yet.
   - The current journey scorer still does not explicitly score the Moon's sign ruler or the hour lord from page 75.
2. Marriage still uses a coarse synthetic model rather than a replay corpus of historical book examples.
3. Conception still treats natal promise as optional by app design.
   - This is intentional, but it remains a doctrinal compromise relative to Morin.
4. No direct book-example replay corpus has yet been assembled for electional charts comparable to the forensic replay slices.

## Recommendation for the Next Election Pass

If election testing continues, the next responsible step is:

1. Build a small replay corpus from explicit Bonatti/Morin election examples or project-owned historical examples.
2. Compare model rankings against those replay cases, not just synthetic stress pairs.
3. Only then consider deeper weighting changes in marriage, legal, and conception, where the current models remain higher-interpretation than the narrower haircut/journey/surgery fixes implemented here.
