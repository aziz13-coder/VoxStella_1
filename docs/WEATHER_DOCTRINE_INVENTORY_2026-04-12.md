# Weather Doctrine Inventory

Status date: 2026-04-12

## Scope

This inventory covers weather doctrine only.

It does not include earthquake doctrine, which now has its own separate inventory:

- `docs/EARTHQUAKE_DOCTRINE_INVENTORY_2026-04-12.md`

## Source Base

### Primary operational source: Kris Brandt Riske

- `horary_knowledge/weather_earthquake_books_text/Predicting_Weather_Events_with_Astrology_-_Kris_Brandt_Riske.txt`

What it contributes:

- explicit seasonal ingress workflow
- explicit lunar-phase trigger workflow
- locality and mapping logic through horizon and meridian lines
- event-family chapters
- many worked modern and historical examples

### Primary classical operational source: Bonatti weather treatise

- `horary_knowledge/mundane_books_text/Bonatti_on_Mundane_Astrology_Guido_Bonattis_Book_of_Astronomy_Treatise_4_8.1_10_Conjunctions_Revolutions_Weat_fdd3953fa4.txt`

What it contributes:

- explicit natural-astrology doctrine for rains and mutations of the air
- timing of showers, heavy rains, and winds
- rainfall prohibition logic
- place-specific and month-specific rain judgment
- abundant classical material on winds, snow, floods, and weather variation

### Supporting source: Barbara Watters

- `horary_knowledge/Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt`

What it contributes:

- support for violent storms, hurricanes, and tornadoes in natural-signification logic
- category support that natural catastrophes belong inside astrology of events

### Supporting source: Green / Raphael / Carter

- `horary_knowledge/mundane_books_text/Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt`

What it contributes:

- framework support for solar ingresses, new moons, and eclipses in national prediction
- category support that droughts and other collective natural phenomena belong inside mundane astrology

## Operational Doctrine Present In The Corpus

### Seasonal framework

Strongly present.

- solar ingresses as the large-frame weather map
- validity by season or quarter
- shorter events read inside the ingress framework

### Short-term triggers

Strongly present.

- lunar phases as shorter weather triggers
- eclipse dates as part of timing context
- inner-planet activations and retrogrades as event sharpeners

### Locality logic

Strongly present.

- map-based or place-based judgment
- horizon and meridian lines
- line intersections as stronger target areas
- path logic for fronts and storms

### Planet / aspect weather mappings

Strongly present.

Examples visible in the corpus:

- Mercury-Uranus for sudden changes, storms, tornadoes, hail, and hurricanes
- Venus-Saturn for heavy precipitation, overcast, sleet, or snow
- Venus-Neptune for heavy precipitation and flood potential
- Mars-Saturn for destructive windy storms
- Mars-Uranus for storms, tornadoes, hurricanes, hail, and sleet
- Saturn-Neptune for above-normal precipitation, chronic rain, floods, and excessive snow

### Event-family partitioning

Strongly present.

The corpus already supports family-level weather interpretation instead of one generic weather output:

- wind
- drought
- floods
- heat and cold extremes
- hurricanes
- snow / sleet / freezing rain
- thunderstorms / hail / tornadoes

## Candidate Benchmark Material Already Present

The current usable corpus already contains enough obvious candidate weather cases to justify a narrow seeded benchmark decision.

Examples directly visible in the converted Riske material:

- 2002 Reno wind case
- 1964 Salt Lake City wind case
- 2011 Santa Ana wind case
- 1930 and 1933 Great Plains drought cases
- 1903 Heppner flood case
- 1964 Salem flood sequence
- 1972 Rapid City flood case
- 1993 Des Moines flood sequence
- 2012 Atlantic City / Caribbean hurricane sequence
- 1900 Galveston hurricane sequence
- 1978 Indianapolis snow case
- 1888 New York snowstorm sequence
- 2013 Lubbock thunderstorm case
- 2013 Moore tornado case
- 1974 Xenia tornado case

## Reassessment

### Weather branch decision

Weather is now strong enough for a **narrow seeded benchmark-first branch**.

That seeded branch is now present under:

- `backend/benchmarks/weather/source_alignment_cases.jsonl`
- `backend/benchmarks/weather/historical_event_cases.jsonl`
- `backend/benchmarks/weather/flood_cases.jsonl`
- `backend/benchmarks/weather/hurricane_cases.jsonl`
- `backend/benchmarks/weather/thunderstorm_tornado_cases.jsonl`
- `backend/benchmarks/weather/drought_cases.jsonl`
- `backend/benchmarks/weather/snow_freezing_precipitation_cases.jsonl`
- `backend/benchmarks/weather/temperature_extremes_cases.jsonl`
- `backend/benchmarks/weather/wind_cases.jsonl`
- `backend/benchmarks/weather/generalized_seasonal_temperature_cases.jsonl`

Reason:

- there are now two operational source families in the local corpus:
  - Riske
  - Bonatti
- there are supporting category/framework sources:
  - Watters
  - Green / Raphael / Carter
- the corpus already contains many candidate worked cases rather than only abstract doctrine

### Boundaries

This does **not** justify:

- runtime weather models yet
- a universal weather score
- climate-change modeling
- folding earthquakes into the same decision

It justifies:

- source-alignment cases for weather doctrine
- a narrow seeded historical weather benchmark pack
- weather-family research slices one family at a time

## Recommended Narrow Benchmark Scope

Start with a small seeded pack, not the whole weather field at once.

Current seeded families:

1. floods
2. hurricanes
3. thunderstorms / tornadoes
4. drought
5. snow / freezing precipitation
6. temperature extremes
7. wind
8. generalized seasonal temperature

Leave these for later:

- climate change

## Runtime Decision

No runtime weather family should be added from this inventory alone.

The seeded benchmark-first branch is active.

The correct next step is to widen and review the benchmark branch, not to add runtime weather models.

The current first runtime-candidate set is now frozen in:

- `docs/WEATHER_RUNTIME_CANDIDATE_FAMILIES_2026-04-12.md`
