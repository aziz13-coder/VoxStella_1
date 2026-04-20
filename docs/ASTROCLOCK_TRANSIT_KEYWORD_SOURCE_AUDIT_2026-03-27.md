# Astro Clock Transit Keyword Source Audit
## 2026-03-27

This note audits the transit keywords shown in Astro Clock against the Book 22 Morin source used by the transit engine.

## Source Basis

Primary source:
- `C:\Users\sabaa\Desktop\astrolgy books\jean-baptiste-morin-astrologia-gallica-book-22-directions-1994-transl_compress.pdf`

Relevant extracted passages:
- Page 23-24: planets must be judged only for the things they signify particularly by radical determination.
- Page 31-32: the 12th is associated with sickness, imprisonment, exile, and secret enemies.
- Page 31: Mars in the 8th can signify dangers to life or even violent death.
- Page 31: Mars connected to the Midheaven and 11th can signify military honours.
- Page 78: transits must be judged from the planet's partial determinations.
- Page 78: the 7th is the house of matrimony, contracts, lawsuits, and open enemies.

## Audit Result

The backend transit engine is still Morin-style in its core:
- radical determination first
- target significance second
- aspect quality and concordance after that

The keywords shown in the frontend are a mixed layer:
- some are source-grounded domain labels
- some are modern shorthand for event families inferred from those domains

That is acceptable only if the shorthand does not overstate the source.

## Confirmed Bug

The shared transit keyword generator was still auto-promoting generic 7th-house soft Mercury, Venus, and Jupiter relationship hits into `marriage`.

Why this was wrong:
- Book 22 explicitly treats the 7th as mixed: matrimony, contracts, lawsuits, and open enemies.
- A generic relationship/open-enemy determination is not enough to label the row `marriage`.
- This could leak a `marriage` keyword onto war/conflict rows that were really about open enemies.

## Fix Applied

Backend and packaged backend:
- removed broad `marriage` promotion from the generic Mercury/Venus/Jupiter relationship branches
- marriage now remains on the stricter marriage-specific gates later in the pipeline

Frontend labels:
- `war_declaration_offensive` now displays as `offensive war/open-enemy conflict`
- `war_response_defensive` now displays as `defensive war/open-enemy conflict`
- `arrest_imprisonment` now displays as `imprisonment/exile`
- `imprisonment_risk` now displays as `imprisonment/exile risk`

These display changes keep the internal event tokens stable while making the user-facing labels closer to Morin's own house language.

## Second Wording Pass

A second wording pass was applied after re-checking the frontend render and backend NLG prose.

Additional adjustments:
- career/public chips now use less modern office language:
  - `honor_award` -> `honor/distinction`
  - `new_job` -> `new office/role`
  - `job_loss` -> `loss of office/job`
- war labels were shortened and kept explicitly tied to open enemies:
  - `war_declaration_offensive` -> `offensive war/open-enemy conflict`
  - `war_response_defensive` -> `defensive war/open-enemy conflict`
  - `internal_conflict_war` -> `civil/internal conflict`
- backend prediction prose now softens:
  - `promotion` -> `advancement or elevation in office`
  - `new_job` -> `a new office, role, or appointment`
  - `lawsuit` -> `a lawsuit, legal contest, or open dispute`
  - `arrest_imprisonment` -> `imprisonment or exile`

Backend rendering was also corrected for mixed 7th-house cases:
- when the event family is war/legal/conflict and the determined life area is the 7th, the rendered area now reads as `partnerships, contracts, or open enemies`
- this avoids misleading phrases like crisis or war occurring merely `in relationships and partnerships`
- the internal event tokens and replay assertions remain unchanged

## What Was Kept

These remain acceptable shorthand:
- `attack_violence`
- `conflict`
- `lawsuit`
- `public_recognition`

Reason:
- they are not literal Morin wording, but they still track source-backed effect families closely enough to be usable modern render labels.
- `attack_violence` remains defensible because the source explicitly discusses violent death, enemies, wounds, burning, drowning, hanging, and similar fundamental violent types.

## Verification

Backend:
- `python -m pytest tests/test_transit_marriage_support_replay_slice_7.py tests/test_transit_war_response_replay_slice_9.py tests/test_transit_recent_war_replay_slice_10.py backend/test_transits_quality.py -q`

Frontend:
- `npx vitest run src/tests/transitsModalReplay.test.jsx src/tests/astroclockApi.test.mjs src/tests/astroClockModeFlow.test.jsx --config vitest.config.mjs`
- `npm run build`

Result:
- war slices still pass
- marriage slice still passes
- war rows no longer tolerate stray `marriage` keywords in replay assertions

## House-by-House Follow-up
## 2026-03-28

After extending the source summary to all twelve houses, a second house-domain pass was applied.

Source baseline from Book 22 lines `8046-8060`:
- 1st: life, temperament, health, moral nature, mental qualities
- 2nd: wealth, gold, acquired goods
- 3rd: brothers, relations
- 4th: parents, successions
- 5th: children, bodily pleasures
- 6th: servants, subordinates, domestic animals
- 7th: marriage, open enemies, lawsuits
- 8th: death
- 9th: religion, journeys
- 10th: action, profession, dignity, fame
- 11th: friends
- 12th: sickness, imprisonment, exile, secret enemies, hardships

The clearest source-sensitive corrections were:
- 3rd-house default transit domain no longer leads with travel; it now leads with `siblings`
- 6th-house default transit domain no longer leads with health; it now leads with `service`
- 12th-house default transit domain no longer leads with generic `secrets`; it now leads with `hidden_enemies`
- generic `contracts` were moved out of the 3rd-house primary map and restored to the mixed 7th-house logic

Frontend render wording was also tightened:
- `wealth` -> `wealth/acquired goods`
- `belief` -> `religion/belief`
- `honors` -> `action/profession/dignity`
- `relationships` -> `partnerships/contracts/open enemies`
- `short_journeys` -> `brothers/relations`
- `secrets` -> `secret enemies/hidden adversity`
- `shared_resources` -> `inheritance/shared burdens`

Important limit:
- some internal domains such as `shared_resources`, `health`, or `short_travel` still exist as project taxonomy because the product layer is broader than Morin's compact house list
- the fix was to stop presenting those as the house-default face where that contradicted the source too directly
