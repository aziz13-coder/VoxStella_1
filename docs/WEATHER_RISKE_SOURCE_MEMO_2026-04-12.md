# Weather Riske Source Memo

Status date: 2026-04-12

Current state: source-specific memo, no longer the active top-level branch decision

Primary source:

- `horary_knowledge/weather_earthquake_books_text/Predicting_Weather_Events_with_Astrology_-_Kris_Brandt_Riske.txt`

## Source Shape

The converted Riske text is not a thin essay. It is a structured weather manual with explicit forecasting workflow and event-family chapters.

Observed chapter structure from the converted text:

- weather charts
- planets, aspects, and signs
- national and local forecasting
- wind
- drought
- floods
- temperature
- hurricanes
- snow, sleet, and freezing rain
- thunderstorms, hail, and tornadoes
- example forecasts
- climate change

This is enough to support doctrine extraction and case inventory work.

## Core Method Signals Present In The Source

### Chart framework

The source explicitly uses:

- solar cardinal ingresses for seasonal framework
- lunar phases as shorter-term triggers
- eclipse dates as part of the timing environment

### Timing logic

The source states:

- each ingress is valid for roughly three months
- outer planets supply broad seasonal trends
- inner planets and especially retrogrades activate shorter-term weather developments
- the relevant charts for a forecast date are the most recent ingress and lunar phase before the target date

### Locality logic

The source explicitly uses map-based locality:

- horizon and meridian lines
- line intersections as stronger target zones
- horizon lines as likely storm/front paths
- local climatology as a required reality check

That means this source is materially compatible with the existing scan mentality in the repo, even though no weather runtime work should start yet.

## Event Families Covered

The source covers explicit weather-event families rather than one undifferentiated weather score.

Strongly represented families:

- wind
- drought
- floods
- heat / cold extremes
- hurricanes
- snow / freezing precipitation
- thunderstorms / hail / tornadoes

This is a positive sign for future modeling because it suggests family-level weather domains would be more coherent than a single generic weather lens.

## Doctrine Signal Types Visible In The Source

From the converted text, the source contains explicit aspect-level mappings such as:

- Mercury-Uranus hard or neutral aspects tied to sudden changes, storms, tornadoes, hail, and hurricanes
- Venus-Saturn hard or neutral aspects tied to heavy precipitation, overcast, humidity, sleet, or snow
- Venus-Neptune hard or neutral aspects tied to isolated cloudbursts and flood potential
- Mars-Saturn hard or neutral aspects tied to destructive windy storms
- Mars-Uranus hard or neutral aspects tied to wind, storms, tornadoes, hurricanes, hail, and sleet
- Saturn-Neptune hard or neutral aspects tied to above-normal precipitation, floods, chronic rain, and excessive snow

This is strong enough for a first doctrine inventory because it is explicit rather than merely symbolic.

## Candidate Historical Case Inventory Already Present

The book itself already contains candidate benchmark material, including:

- 1903 Bismarck weather charts
- 2011 Long Pond, Pennsylvania rain case
- 2002 Reno wind case
- 1964 Salt Lake City wind case
- 2011 Santa Ana wind case
- 1930 and 1933 Great Plains drought cases
- 1903 Heppner flood case
- 1964 Salem flood cases
- 1972 Rapid City flood case
- 1993 Des Moines flood cases
- 2012 Atlantic City / Caribbean hurricane sequence
- 1900 Galveston hurricane sequence
- 1978 Indianapolis snow case
- 1888 New York snowstorm sequence
- 2013 Lubbock thunderstorms
- 2013 Moore tornado
- 1974 Xenia tornado

This is enough to build a candidate-case registry before a formal benchmark decision is made.

## What The Source Is Strong Enough For Right Now

The Riske source is strong enough for:

- weather doctrine inventory
- candidate case inventory
- source-alignment memo drafting
- event-family partition design for a possible future weather branch

## What The Source Is Not Strong Enough For By Itself

By itself, this source is not yet strong enough to justify:

- a benchmark-first weather branch with confidence
- any earthquake branch
- runtime weather prediction code

Reason:

- it is still only one usable source family
- the method may be explicit, but the branch would still be source-thin and vulnerable to overfitting

## Later Reassessment

This source was later widened by the already ingested Bonatti weather treatise plus supporting Watters and Green / Raphael / Carter material.

That broader local corpus is now strong enough for a narrow seeded benchmark-first weather branch. See:

- `docs/WEATHER_DOCTRINE_INVENTORY_2026-04-12.md`
- `docs/WEATHER_EARTHQUAKE_SOURCE_INVENTORY_2026-04-12.md`

## Recommended Research Direction

Treat the next step as:

- weather-only doctrine extraction from Riske
- candidate-case registry building
- no runtime code
- no earthquake work until another usable source is accessible
