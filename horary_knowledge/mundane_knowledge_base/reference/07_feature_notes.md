# Feature Notes

Status: first pass

## Overview

The current doctrine supports a mundane feature, but not as a cosmetic toggle over the existing astrocartography goal engine.

The architecture can be reused from astrocartography:

- place search
- chart-context switching
- source-backed runtime assets
- atlas-like location registries
- benchmark and source-alignment workflows

But the semantics must change:

- astrocartography is person -> place
- mundane is polity/event -> place/time -> public domain

## Capability Summary

The mundane layer should be able to:

- resolve which chart class is being used
- separate polity context from event location and capital context
- analyze public domains instead of personal outcomes
- return framework, trigger, and activation notes in one output
- keep source and research status attached to every result

The first intended capabilities are:

- chart analysis for `aries_ingress`, `lunation`, `eclipse`, `war_event`, and `national_chart`
- public-domain analysis for `war_conflict`, `government_stability`, `diplomacy_foreign_affairs`, and `public_health`
- chart-context resolution for `capital_chart`, `national_chart`, `event_chart`, and `regional_chart`

The mundane layer should not initially claim to:

- produce one universal score for a country
- replace personal astrocartography analysis
- expose research-gated domains like weather, earthquakes, or fixed-star catastrophe logic

## Recommended Product Shape

### 1. Start with chart type, not with score type

The current corpus treats chart class as the first organizing decision.

The most defensible first chart types are:

- `aries_ingress`
- `cardinal_ingress`
- `lunation`
- `eclipse`
- `war_event`
- `national_chart`
- `ruler_chart`

Sources behind this recommendation:

- Green on ingresses, new moons, eclipses, conjunctions, and national horoscopes, pages 12-20 and contents pages 4-7
- Watters on war charts and ruler-chart fallback, pages 55-56 and 203-205
- Bonatti on revolutions and Lord of the Year logic, pages 35-45

### 2. Separate polity context from physical location

The product should not use one generic `location`.

The doctrine already requires at least four context types:

- `capital_chart`
- `national_chart`
- `event_chart`
- `regional_chart`

This follows directly from:

- Green's capital-town ingress rule
- Watters' war-event place logic
- Bonatti's city/region/clime logic

Sources:

- Green, pages 12-13 and 17-18
- Watters, pages 103-104 and 203-205
- Bonatti, pages 48-49

### 3. Use domain lenses instead of one generic mundane score

The strongest first product domains are:

- `war_conflict`
- `government_stability`
- `civil_unrest`
- `finance_economy`
- `diplomacy_foreign_affairs`

The next domain behind them is:

- `public_health`

Research-gated domains:

- `weather_and_crops`
- `earthquakes_and_natural_disaster`

This ordering reflects the current source maturity, not product aesthetics.

Sources:

- Green, pages 45-61
- Watters, pages 44-48, 103-104, 110, and 203-205
- Bonatti, pages 11-12 and 238-243

## Recommended Runtime Layers

### 1. Framework layer

This stores the active background chart:

- ingress
- revolution
- mutation or conjunction master chart
- national chart context

### 2. Trigger layer

This stores the nearer event:

- current lunation
- eclipse
- war outbreak
- leadership accession

### 3. Activation layer

This stores the exact hit:

- Mars or heavy planet to eclipse degree
- angular contact
- conjunction or square to sensitive national degree
- retrograde trigger condition when validated

### 4. Domain layer

This translates chart conditions into public outcomes:

- war
- finance
- riots
- diplomacy
- leadership crisis

This four-layer split is consistent with the current doctrine and should keep the implementation honest.

## Suggested Data Model

Minimum fields the future mundane layer will likely need:

- `chart_type`
- `polity_id`
- `location_context_type`
- `reference_location`
- `event_datetime`
- `event_location`
- `national_chart_id`
- `ruler_chart_id`
- `visibility_scope`
- `sensitive_degrees`
- `domain_lenses`
- `source_tags`

Optional but probably necessary later:

- `historical_cycle_context`
- `mutation_context`
- `regional_override`
- `benchmark_status`

## Suggested Knowledge Assets

The new mundane family should parallel the astrocartography asset pattern, but remain separate from it.

Likely asset set:

- `backend/knowledge/mundane/mundane_reference_runtime.json`
- `backend/knowledge/mundane/mundane_chart_types.runtime.json`
- `backend/knowledge/mundane/mundane_domain_models.runtime.json`
- `backend/knowledge/mundane/mundane_country_registry.runtime.json`
- `backend/knowledge/mundane/mundane_source_alignment.runtime.json`

Likely benchmark set:

- `backend/benchmarks/mundane/source_alignment_cases.jsonl`
- `backend/benchmarks/mundane/historical_event_cases.jsonl`

## Suggested UI Flow

The first public flow should probably be:

1. choose chart type
2. choose polity or event
3. choose location context
4. choose domain lens
5. view framework, trigger, and activation notes

This is better than:

1. choose a country
2. receive one universal mundane score

because the source doctrine does not support that simplification.

## Suggested API Shape

The cleanest first backend shape is a sibling mundane namespace, not an astrocartography sub-goal.

Example surface:

- `/api/astro-clock/mundane/chart-types`
- `/api/astro-clock/mundane/context/resolve`
- `/api/astro-clock/mundane/analyze`
- `/api/astro-clock/mundane/benchmarks`

Payloads should include:

- resolved chart context
- cited doctrine notes
- domain outputs
- benchmark confidence or research gating flags

## Benchmark Notes

The first benchmark cases should focus on domains where the current sources are explicit:

- war outbreaks
- aggressor vs defender outcomes
- government crisis and cabinet instability
- assassinations or death of public leaders
- major riots or unrest
- treaty reversal or diplomatic breakdown

Only after these are stable should the project attempt:

- weather
- earthquakes
- fixed-star catastrophe logic

## Product Rules To Preserve

- Do not score mundane doctrine from personal-goal models.
- Do not treat sign-country lists as unquestioned truth.
- Do not expose weakly validated rules as if they were hard doctrine.
- Keep citations or source tags attached to outputs as long as the model family is still in research mode.

## Next Build Step

The research threshold is now sufficient to begin implementation.

The next build step is:

- scaffold the mundane runtime asset family
- add a sibling backend service and API namespace
- keep the first frontend toggle blocked until the backend contract is stable

The implementation sequence is tracked in:

- [MUNDANE_IMPLEMENTATION_PLAN_2026-04-11.md](C:/Users/sabaa/Downloads/codexhorary/docs/MUNDANE_IMPLEMENTATION_PLAN_2026-04-11.md)
