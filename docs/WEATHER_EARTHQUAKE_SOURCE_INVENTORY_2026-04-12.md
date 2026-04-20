# Weather And Earthquake Source Inventory

Status date: 2026-04-12

## Goal

Inventory the currently available weather and earthquake source material and decide whether it is strong enough to justify a benchmark-first research branch before any runtime code is added.

## Local Source Inventory

### 1. Kris Brandt Riske

- Source file:
  - `C:\Users\sabaa\Downloads\Predicting Weather Events with Astrology (Kris Brandt Riske) (z-library.sk, 1lib.sk, z-lib.sk).pdf`
- Intake status:
  - copied into `horary_knowledge/weather_earthquake_source_raw/source_books`
  - converted successfully into text
- Converted output:
  - `horary_knowledge/weather_earthquake_books_text/Predicting_Weather_Events_with_Astrology_-_Kris_Brandt_Riske.txt`
- Manifest status:
  - `ok`
- Notes:
  - this is the only currently usable converted source in the weather/earthquake intake

### 2. Guido Bonatti weather treatise

- Source file:
  - `horary_knowledge/mundane_books_text/Bonatti_on_Mundane_Astrology_Guido_Bonattis_Book_of_Astronomy_Treatise_4_8.1_10_Conjunctions_Revolutions_Weat_fdd3953fa4.txt`
- Intake status:
  - already present in the local corpus as text
- Notes:
  - contains explicit operational doctrine for heavy rains, mutations of the air, winds, snows, and some earthquake indications
  - materially changes the source picture for weather and earthquake research

### 3. Barbara Watters support material

- Source file:
  - `horary_knowledge/Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt`
- Intake status:
  - already present in the local corpus as text
- Notes:
  - includes explicit storm / hurricane / tornado signification material and an earthquake section
  - better as supporting doctrine than as the primary operational source

### 4. Green / Raphael / Carter support material

- Source file:
  - `horary_knowledge/mundane_books_text/Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt`
- Intake status:
  - already present in the local corpus as text
- Notes:
  - provides framework support for ingresses, new moons, and eclipses in natural prediction
  - supports treating droughts, earthquakes, epidemics, and related collective phenomena as valid mundane subjects

### 5. B.V. Raman multipart archive set

- Source files:
  - `C:\Users\sabaa\Downloads\Astrology in Forecastings Weather and Earthquakes Part 13 (Raman B.V.) (z-library.sk, 1lib.sk, z-lib.sk).rar`
  - `C:\Users\sabaa\Downloads\Astrology in Forecastings Weather and Earthquakes Part 23 (Raman B.V.) (z-library.sk, 1lib.sk, z-lib.sk).rar`
- Intake status:
  - outer archives inspected successfully
  - multipart `.rar` chain extracted into `horary_knowledge/weather_earthquake_source_raw/raman_parts`
  - embedded PDF name identified as `Astrology in Predicting Weather and Eart - B.V. RAMAN.pdf`
- Blocker:
  - extraction with the currently available toolchain produces a corrupt PDF payload
- Current extracted artifact:
  - `horary_knowledge/weather_earthquake_source_raw/raman_extracted/Astrology in Predicting Weather and Eart - B.V. RAMAN.pdf`
- Manifest status:
  - `error`
- Error detail:
  - `Stream has ended unexpectedly`
- Notes:
  - `tar` can inspect the archive chain but the final PDF bytes are invalid in this environment
  - no working `7z`, `unrar`, `unar`, or Python rar extraction package is currently available here

## Conversion Output

The generated text corpus folder is:

- `horary_knowledge/weather_earthquake_books_text`

Key files:

- `horary_knowledge/weather_earthquake_books_text/Predicting_Weather_Events_with_Astrology_-_Kris_Brandt_Riske.txt`
- `horary_knowledge/weather_earthquake_books_text/manifest.json`

Manifest summary for the new weather/earthquake conversion folder:

- Raman: `error`
- Riske: `ok`

## Source Strength Assessment

### Weather

Status:

- `multi-source doctrine available`
- `benchmark-feasible`

Reason:

- the corpus now includes:
  - one strong modern operational source
  - one strong classical operational source
  - two supporting framework/signification sources
- the Riske text already contains a large candidate case inventory across multiple weather families

Decision:

- weather is strong enough to justify a **narrow seeded benchmark-first branch**
- weather is not yet strong enough to justify runtime code

### Earthquakes

Status:

- `doctrine-seeded`
- `benchmark-not-ready`

Reason:

- Bonatti provides real operational earthquake doctrine
- Watters and Green / Carter provide supporting category legitimacy
- the current local corpus still lacks a strong worked-case earthquake inventory and a second clearly operational source family

Decision:

- earthquakes are **not yet strong enough** to justify a benchmark-first branch

## Active Research Scope

The active near-term scope is now:

- weather doctrine inventory
- earthquake doctrine inventory
- weather benchmark-first reassessment from the current local corpus

See:

- `docs/WEATHER_DOCTRINE_INVENTORY_2026-04-12.md`
- `docs/EARTHQUAKE_DOCTRINE_INVENTORY_2026-04-12.md`
- `docs/WEATHER_RISKE_SOURCE_MEMO_2026-04-12.md`

## Recommended Next Steps

1. widen and review the seeded benchmark-first weather branch now active under `backend/benchmarks/weather`, which now covers floods, hurricanes, thunderstorms / tornadoes, drought, snow / freezing precipitation, temperature extremes, wind, and generalized seasonal temperature
2. keep earthquake work at doctrine-inventory level only
3. obtain a working extraction path for the Raman multipart archive, or obtain the original Raman PDF directly
4. rerun Raman text conversion only if a working extractor or direct PDF becomes available
5. only after that, decide whether to widen earthquake from doctrine inventory into its own benchmark-first branch

## Runtime Decision

No weather or earthquake runtime family should be added yet.

The correct posture is:

- weather: seeded benchmark-first branch active
- earthquakes: doctrine-only for now
- runtime only after source and benchmark gates are satisfied

See also:

- `docs/WEATHER_RUNTIME_GATE_2026-04-12.md`
