# Gambling Luck Source Alignment

This note tracks how the shipped `gambling_luck` astrocartography scorer currently aligns with the reverse-engineered `Gambling.exe` logic described in `C:\Users\sabaa\Downloads\Gambling_Reverse_Engineering.md`.

## Current Model

The live scorer is a curated natal-relocation place model, not a full timing engine.

- Source metadata: `backend/knowledge/astrocartography/place_goal_models.runtime.json`
- Evaluation strategy: `gambling_natal_curated`
- Transit strategy: `ignore`
- Primary external reference: `Gambling_Elect_Personal.hyp`

## Implemented Or Approximated

- Querent-versus-quesited analogue:
  - Implemented as Ascendant ruler versus 5th-house gambling ruler harmony/tension.
- Explicit Ascendant-angle support rules:
  - Implemented as dedicated Ascendant aspect metrics for the Ascendant ruler, the gambling ruler, and the Moon.
- Moon logic:
  - Implemented through `moon_void`, `moon_next_aspect`, Moon-to-key-ruler support, Moon-to-Ascendant support, and Moon liability.
- Retrograde weakness:
  - Implemented through `retrograde_liability` including combust drag.
- Intercepted Ascendant warning:
  - Implemented as `asc_interception`, derived from intercepted signs on the 1st/7th axis from house cusps.
- Pattern geometry:
  - Implemented as `grand_trine_support`, `kite_support`, and `t_square_pressure`.
- South Node obstruction:
  - Implemented as `south_node_obstruction`, derived from South Node contact to the Ascendant, key rulers, Moon, and obstructive houses.
- Secondary bankroll layer:
  - Implemented as `money_support`.
- General dignity/angularity:
  - Approximated through normalized planet strength and house/angle weighting rather than the legacy rule catalog.

## Current In-Scope Scorer Gaps

No open scorer-family gaps remain from the current source-alignment review.

What still remains is calibration and retrospective validation, not missing rule-family coverage inside the current best-place gambling scorer.

## Deferred For Now

These are real differences from the original product, but they are intentionally out of scope for the current scorer-alignment pass:

- The original timing/calendar architecture:
  - Best Time
  - Personal Calendar
  - transit-driven electional scoring
- Any gambling-specific score contribution from the legacy profile / happy-direction layer.

## Practical Reading

The scorer is now closer to the source logic family than a generic money model:

- it has direct ruler harmony,
- explicit Ascendant-angle support rules,
- Moon support and liability,
- South Node obstruction,
- retrograde drag,
- intercepted Ascendant penalty,
- and chart-pattern geometry.

But it still should be read as a best-place adaptation of the personal gambling layer, not as a recreation of the original gambling application.

## Verification

The current astrocartography regression slice passed after the latest scorer changes:

- `python -m pytest backend/test_astrocartography_goal_engine.py -q`
- `python -m pytest backend/test_astrocartography_goal_engine.py backend/test_astrocartography_atlas_engine.py backend/test_astrocartography_service.py backend/test_astro_clock_api_astrocartography.py -q`
