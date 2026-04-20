# Astrocartography Model Validation Plan

Date: 2026-04-05

## Purpose

This memo defines how Vox Stella should test whether astrocartography PathFinder models are merely internally coherent or actually useful against real-life outcomes.

The current automated suite already proves internal coherence:

- unit tests for scoring logic
- synthetic stress scenarios
- overlap checks between adjacent goal families

That is necessary, but not enough. A model is only product-valid if it beats simple baselines against real event-location data.

## Three Validation Layers

### 1. Internal correctness

Questions:

- does the model score the intended goal family above adjacent families
- do specialist variants stay distinct from their parent models
- do high-risk models behave in the correct direction

Current coverage already exists in:

- [test_astrocartography_goal_engine.py](/Users/sabaa/Downloads/codexhorary/backend/test_astrocartography_goal_engine.py)
- [astrocartography_model_stress.py](/Users/sabaa/Downloads/codexhorary/backend/astrocartography_model_stress.py)
- [test_astrocartography_model_stress.py](/Users/sabaa/Downloads/codexhorary/backend/test_astrocartography_model_stress.py)

### 2. Retrospective validation against historical events

Questions:

- does the event location rank above control locations for the same person
- does the specialist model outperform its parent model
- does the model beat simple heuristics such as Jupiter-only or benefic-minus-malefic scoring

This is the most important next layer.

### 3. Prospective product validation

Questions:

- when the model recommends or warns before the outcome is known, does it prove useful later
- do users report that the suggested locations fit lived experience better than alternatives

This should only begin after retrospective validation shows real signal.

## Core Evaluation Rule

Avoid anecdotal validation.

The wrong standard is:

- one celebrity
- one lucky city
- one headline event

The right standard is:

- same person
- event city
- one or more control cities
- consistent scoring advantage over controls

## Benchmark Record Schema

Each benchmark row should contain:

- `person_id`
- `person_name`
- `birth_date`
- `birth_time`
- `birth_place`
- `birth_data_quality`
- `event_type`
- `event_date`
- `event_location`
- `event_outcome_polarity`
- `source_url`
- `source_quality`
- `control_locations`
- `notes`

Recommended extra fields:

- `country`
- `city_latitude`
- `city_longitude`
- `time_known`
- `location_certainty`
- `event_certainty`

## Best First Benchmark: Speculation / Gambling

This is a better first historical benchmark than health risk.

Why:

- repeated outcomes exist
- event locations are usually public
- dates are usually public
- same-person control locations are easier to collect

### Good target populations

- professional poker players
- tournament gamblers with repeated venue results
- traders or speculators with public place-and-date-linked performance only if the location is truly known

### Bad target populations

- lottery winners
- one-off casino anecdotes
- unverified social-media claims

Reason:

- poor birth-data quality
- poor control set quality
- strong survivor bias
- weak repeatability

### Speculation benchmark questions

- does `gambling_luck(event_city)` outrank `money(event_city)` for known speculative wins
- does `gambling_luck(event_city)` outrank the same person's control cities
- does adding event-date transit overlay improve ranking accuracy
- does the model beat a simple Jupiter/Venus baseline

## Health Risk Benchmark

This should be treated as a warning model, not a positive recommendation model.

Important product rule:

- higher score = worse place

### Good first event types

- injury
- accident
- surgery
- hospitalization
- acute health crisis

### Avoid first

- chronic disease onset
- vague illness periods
- long-term medical decline without a clear event location

Reason:

- dates are unclear
- locations are unclear
- confounding is much worse

### Health benchmark questions

- does `health_risk(event_city)` rank above control cities for injury or hospitalization events
- does transit overlay materially improve warning accuracy
- does `health_risk` beat `conflict` or generic malefic-pressure heuristics on bodily events

## Recommended Metrics

Use these metrics in order:

- pairwise win rate versus control locations
- top-3 hit rate
- AUC for event cities versus control cities
- mean reciprocal rank
- lift over baseline models

## Required Baselines

Every specialist model should be compared against:

- random control city
- nearest neutral city
- parent goal model
- simple benefic-minus-malefic heuristic
- a reduced single-axis baseline when relevant

Examples:

- `gambling_luck` versus `money`
- `health_risk` versus `conflict`
- `gambling_luck` versus Jupiter-only
- `health_risk` versus malefic-pressure-only

If the specialist model does not beat these, it should not ship as a distinct claim.

## Suggested Pilot Sequence

1. Build a small curated speculation benchmark with 20 to 30 cases.
2. Use only strong birth-data quality where possible.
3. Test natal-location only first.
4. Then test natal-location plus transit-on-event-date.
5. Compare against parent and heuristic baselines.
6. Only after that, build the health-risk benchmark.

## Validation Modes Under Current Product Logic

Benchmarking should reflect the model behavior that Vox Stella actually ships today.

Current Astrocartography scoring uses:

- natal line contributions at full weight
- natal crossing contributions at full weight
- transit line contributions at 0.35 weight
- transit crossing contributions at 0.35 weight
- relocation, modifier, and constraint terms from natal relocation only

Important boundary:

- the current product does not compute a separate transit relocation chart for goal scoring
- a transit test should therefore be treated as an activation overlay test, not a full chart replacement test

The benchmark runner should expose at least these modes:

- `natal_only`: natal lines + natal crossings + natal relocation
- `event_transit_overlay`: natal base + event-date transit overlay using the current 0.35 transit multiplier
- `transit_only_debug`: optional diagnostic mode for research only, not product parity

The first two are the real product questions. The third is useful only to understand whether transit is adding signal or merely noise.

## Practical Benchmark Sketch

Recommended repo slice:

- `backend/benchmarks/astrocartography/README.md`
- `backend/benchmarks/astrocartography/speculation_cases.jsonl`
- `backend/benchmarks/astrocartography/health_risk_cases.jsonl`
- `backend/benchmarks/astrocartography/baselines.py`
- `backend/run_astrocartography_benchmark.py`

Recommended workflow:

1. Curate cases into a frozen JSONL file.
2. Freeze a control-city list per case before scoring.
3. Run the benchmark in `natal_only`.
4. Run the same benchmark in `event_transit_overlay`.
5. Compare specialist model, parent model, and heuristic baselines.
6. Save a machine-readable result file plus a short Markdown summary.

## Current Pilot Status

The repo now contains an initial exploratory speculation seed in:

- [speculation_cases.jsonl](/Users/sabaa/Downloads/codexhorary/backend/benchmarks/astrocartography/speculation_cases.jsonl)

Current seed size:

- 7 enabled `gambling_luck` cases
- all cases use explicit event/control coordinates to avoid city-catalog resolution drift

## External Legacy Model Inspection Notes

On 2026-04-05 three external legacy `.HYP` models were reviewed directly:

- `Gambling_Elect_Personal.hyp`
- `MONEY_GAINS_INVESTMENTS.HYP`
- `CAREER_BUSINESS_PARENT.HYP`

The useful takeaway was structural, not literal-field decoding.

Observed pattern:

- the gambling pack is materially more asymmetric than the money and career parent packs
- the gambling pack contains stronger negative weights than positive weights
- the gambling pack repeatedly treats anti-speculation signatures as hard penalties, not mild cautions
- the money and career parents are more symmetric and therefore behave more like generic opportunity/throughput families

Practical product implication:

- `gambling_luck` should not be modeled as a flat count of benefics in money houses
- speculative upside should favor 5th and 11th-house signatures more than generic 2nd and 8th-house money signatures
- anti-speculation drag should be explicit and should subtract harder than upside adds

This inspection informed the current relocation rewrite:

- `speculation` now represents weighted upside rather than a raw house-hit count
- `speculation_drag` now captures negative relocated signatures separately
- the specialist `gambling_luck` model now penalizes drag directly instead of relying only on generic uncertainty and malefic-pressure metrics

Later product decision on the same day:

- the specialist `gambling_luck` profile was temporarily realigned to the stronger parent `money` model for shipped scoring
- reason: on the current seeded benchmark, the specialist variant improved materially but still did not beat the parent model cleanly
- this means the current product should be read as benchmark-first rather than theory-first for this goal

## Current Post-Inspection Benchmark Snapshot

After the relocation rewrite driven by the external legacy model inspection, the current seeded benchmark stands at:

- `natal_only`: `gambling_luck` pairwise win rate `0.5000`
- `event_transit_overlay`: `gambling_luck` pairwise win rate `0.5000`

Comparator context on the same 7-case seed:

- `money` parent model: `0.5000` natal, `0.5769` transit
- `Jupiter/Venus` heuristic: `0.4615` natal, `0.5000` transit

Interpretation:

- the specialist model materially improved from its earlier relocation-heavy failure mode
- it now matches the parent model in natal mode and matches the Jupiter/Venus heuristic in transit-overlay mode
- it still does not clearly beat the parent model on this seed, so more tuning and better controls are still required

Current shipped direction after alignment:

- `gambling_luck` now intentionally inherits the stronger `money` scoring shape until a later specialist version can beat it on the frozen benchmark

## Next Model To Test

The next model that should be tested is `health_risk`.

Reason:

- `gambling_luck` now has a frozen exploratory benchmark and a benchmark-aligned shipped fallback
- `health_risk` is the highest-risk interpretation model in product terms because a wrong warning model damages trust faster than a weak opportunity model
- `health_risk` still has no real retrospective benchmark in repo
- the newly inspected external `WORK__SERVICE _SICKNESS_.HYP` file strongly suggests there was a legacy service/sickness family that can help ground this validation pass

Practical sequence:

1. keep `gambling_luck` stable for now
2. curate the first real `health_risk` retrospective cases
3. use `WORK__SERVICE _SICKNESS_.HYP` as an external legacy reference during the review
4. only after that, revisit softer expansion families like communication or personality/presence

## External Legacy Family Inspection: Additional Files

On 2026-04-05 four more external `.HYP` files were inspected:

- `PERSONALITY_THE BODY_APPEARANCE.HYP`
- `COMMUNICATION_BROTHER_SISTER.HYP`
- `WORK__SERVICE _SICKNESS_.HYP`
- `MONEY_GAINS_INVESTMENTS.HYP`

These four files share the same overall rule skeleton:

- 39 events each
- the same visible weight distribution
- the same high-level positive/negative alternation pattern
- the same broad `A2` motif counts (`1`, `2/4`, `3/5`, `1/2/4`)

What differs is the domain token family:

- `PERSONALITY_THE BODY_APPEARANCE.HYP` centers on `*25`, `*29`, `*17`, `*13`
- `COMMUNICATION_BROTHER_SISTER.HYP` centers on `*27`, `*15`
- `WORK__SERVICE _SICKNESS_.HYP` centers on `*30`, `*18`
- `MONEY_GAINS_INVESTMENTS.HYP` centers on `*26`, `*14`

Interpretation:

- these are sibling domain variants from one older template rather than independently designed systems
- the token-family changes likely mark the domain identity, while the surrounding event skeleton stays mostly constant

Current mapping to Vox Stella goals:

- `MONEY_GAINS_INVESTMENTS.HYP` maps cleanly to `money`
- `COMMUNICATION_BROTHER_SISTER.HYP` maps most directly to `communication`, but with a likely 3rd-house / sibling / local-network bias that is narrower than the current broad communication goal
- `WORK__SERVICE _SICKNESS_.HYP` spans both `work` and `health_risk`; it is the clearest external hint that those two goals share a legacy family boundary around 6th-house service and sickness
- `PERSONALITY_THE BODY_APPEARANCE.HYP` does not map cleanly to `personal_growth`; it looks more like a missing future goal family around body presence, appearance, projection, or first-house persona

Product implication:

- `communication` and `work` are probably still missing some legacy specialization
- `health_risk` is the next validation priority because `WORK__SERVICE _SICKNESS_.HYP` gives it the strongest newly surfaced external anchor
- `PERSONALITY_THE BODY_APPEARANCE.HYP` points to a possible future capability, but not to an immediate benchmark priority

This seed is intentionally exploratory, not final:

- several control cities are still competing-positive venues
- some rows are stronger for pipeline validation than for final model claims
- the benchmark is good enough to expose whether the specialist model is beating its baselines

### Exploratory Result Snapshot

Using the current product scoring logic:

- `natal_only`
  - product model pairwise win rate: `0.2308`
  - parent `money` model pairwise win rate: `0.4231`
  - Jupiter/Venus heuristic pairwise win rate: `0.4615`
- `event_transit_overlay`
  - product model pairwise win rate: `0.3846`
  - parent `money` model pairwise win rate: `0.5000`
  - Jupiter/Venus heuristic pairwise win rate: `0.5385`

Interpretation:

- transit overlay improves `gambling_luck` materially on this seed
- the current specialist model still does not beat its parent baseline
- the current specialist model also does not beat the simple Jupiter/Venus heuristic

That is the correct kind of failure to surface early. It means the benchmark is already doing useful work.

## Concrete Record Shape

Suggested JSONL row:

```json
{
  "case_id": "spec_001",
  "goal_id": "gambling_luck",
  "person_id": "person_a",
  "person_name": "Example Person",
  "birth": {
    "date": "1985-01-01",
    "time": "14:35",
    "place": "Los Angeles, California, USA",
    "data_quality": "AA"
  },
  "event": {
    "type": "poker_tournament_win",
    "date": "2024-07-11",
    "location": "Las Vegas, Nevada, USA",
    "outcome_polarity": "positive"
  },
  "controls": [
    { "label": "Atlantic City, New Jersey, USA", "reason": "same domain, no matching win" },
    { "label": "Prague, Czech Republic", "reason": "same player, other tournament stop" }
  ],
  "sources": [
    { "kind": "birth_data", "quality": "high", "url": "source-or-note" },
    { "kind": "event_result", "quality": "high", "url": "source-or-note" }
  ],
  "notes": "Use event-date transit overlay in second pass only."
}
```

Minimum extra fields worth storing at scoring time:

- `event_location_rank`
- `event_location_score`
- `best_control_score`
- `pairwise_win`
- `model_mode`
- `baseline_results`

## Case Selection Rules

Use cases only if all of the following are true:

- birth date is known
- birth time is known or quality-graded low enough to exclude later
- event date is known to at least the day
- event location is specific enough to map to a city
- at least one credible control city exists

Reject a case if any of the following are true:

- event location is vague or symbolic rather than geographic
- outcome is famous but one-off with no controls
- birth data is weak and cannot be graded honestly
- the case would force hand-picked controls after seeing the score

## Speculation Pilot Sketch

Start with one repeated-outcome domain only. Do not mix poker, lottery, sports betting, and trading in the first pilot.

Preferred first slice:

- professional poker players
- repeated venue history
- publicly dated results
- multiple positive and neutral outcome cities for the same person

For each person:

1. choose one positive event city
2. choose one or more control cities from the same activity domain
3. run `gambling_luck`, `money`, and heuristic baselines
4. compare `natal_only` and `event_transit_overlay`

Primary question:

- does `gambling_luck` beat `money` and the heuristic baselines on same-person city ranking

## Health Risk Pilot Sketch

Run this only after the speculation benchmark is operational.

Preferred first slice:

- injury
- surgery
- hospitalization
- acute accident

Avoid mixing these with chronic disease cases in the first pass.

For each person:

1. choose one clear bodily event city
2. choose one or more neutral control cities from nearby time windows or known residence/travel exposure
3. run `health_risk`, `conflict`, and malefic-pressure heuristics
4. compare `natal_only` and `event_transit_overlay`

Primary question:

- does `health_risk` rank the event city as riskier than controls more often than `conflict` or generic malefic pressure

## Current Health-Risk Pilot Status

The repo now contains an initial exploratory health-risk seed in:

- [health_risk_cases.jsonl](/Users/sabaa/Downloads/codexhorary/backend/benchmarks/astrocartography/health_risk_cases.jsonl)

Current seed size:

- 4 enabled `health_risk` cases
- Sonny Bono
- Dale Earnhardt
- Ayrton Senna
- James Dean

Current seeded benchmark result:

- `natal_only`: product `health_risk` pairwise win rate `0.375`
- `event_transit_overlay`: product `health_risk` pairwise win rate `0.5000`
- parent `conflict`: `0.3125` natal, `0.2500` transit
- `malefic_pressure` heuristic: `0.3125` natal, `0.5000` transit
- `benefic_minus_malefic`: `0.8125` natal, `0.3750` transit

Interpretation:

- the seeded benchmark is already useful
- the product `health_risk` model beats the `conflict` parent on both current product modes
- transit overlay improves the product warning model materially
- the model still does not beat the strongest natal-only simple baseline, so it remains exploratory

Important caution:

- two cases still use noon fallback because event time is not pinned in the current seed
- several controls are home-base or same-domain comparison cities rather than clean matched controls
- the benchmark is good enough for model iteration and not good enough for strong product claims

## New Specialist Model Added

The repo now also includes a new specialist goal:

- `body_presence`

Why it was added:

- `PERSONALITY_THE BODY_APPEARANCE.HYP` did not map cleanly to the existing `personal_growth` goal
- the external legacy pack points to a narrower family around appearance, bodily charisma, and first-impression presence
- the Morin knowledge map explicitly supports a distinct 1st-house body, vitality, appearance, and personality layer

Current product position:

- `body_presence` is a specialist personal variant, not a replacement for `personal_growth`
- it is implemented and unit-tested
- it is not benchmarked yet against real event-location data

## Current Generic-Risk Pilot Status

The repo now contains an initial exploratory public-risk seed in:

- [risk_pressure_cases.jsonl](/Users/sabaa/Downloads/codexhorary/backend/benchmarks/astrocartography/risk_pressure_cases.jsonl)

Current seed size:

- 6 enabled `risk_pressure` cases
- Sonny Bono
- Dale Earnhardt
- Ayrton Senna
- James Dean
- Diana, Princess of Wales
- Frida Kahlo

Current seeded benchmark result:

- `risk_pressure` is now kept as a deprecated research model, not the public picker preset
- `natal_only`: product `risk_pressure` pairwise win rate `0.2917`
- `event_transit_overlay`: product `risk_pressure` pairwise win rate `0.2917`
- parent `conflict`: `0.4583` natal, `0.5833` transit
- experimental `health_risk`: `0.375` natal, `0.5000` transit
- `benefic_minus_malefic`: `0.7083` natal, `0.5417` transit

Interpretation:

- the deprecated `risk_pressure` benchmark is now real enough to falsify the old public implementation
- the current shipped public model is semantically correct now, but weak on this seed
- on this seed, `conflict`, `health_risk`, and the raw natal `benefic_minus_malefic` comparator all outperform the public model
- the current public model is therefore not benchmark-justified yet and should be treated as exploratory until a stronger generic-risk rule set is found

Current product decision:

- `High-Risk Places` now uses the simple heuristic path directly in the runtime engine
- that model is now locked to natal-only scoring
- the shipped product uses the inverted form of the comparator: `malefic_minus_benefic`, so higher score truly means more risk
- reason: on this exploratory generic-risk seed, adding transit lowered the simple heuristic from `0.7083` natal to `0.5417` transit
- the benchmark table above still reports the raw `benefic_minus_malefic` comparator, not the shipped product's inverted public-risk score
- `health_risk` remains separate and still supports transit overlay as an experimental caution model

Important caution:

- this is still an exploratory benchmark with home-base and same-domain controls
- some rows use city-level event locations rather than exact incident coordinates
- the benchmark is strong enough to reject false confidence and not strong enough for marketing claims

## Subtype Experiment

The strongest product suggestion for a future caution model was to stop treating "bad places" as one undifferentiated score and instead test narrower subtype lenses first:

- `Accident Pressure`
- `Hostile Places`
- `Drain / Breakdown`
- `Subtype Max` — the maximum of the three subtype scores for a given city

These are now implemented as benchmark-only comparators in [baselines.py](/Users/sabaa/Downloads/codexhorary/backend/benchmarks/astrocartography/baselines.py), not as shipped frontend goal models.

Current result on the same 6-case negative-place seed:

- `Accident Pressure`: `0.5000` natal, `0.5417` transit
- `Hostile Places`: `0.5833` natal, `0.5417` transit
- `Drain / Breakdown`: `0.3750` natal, `0.3750` transit
- `Subtype Max`: `0.5000` natal, `0.6250` transit

Interpretation:

- this is materially better than the old monolithic `risk_pressure` model
- `Subtype Max` is now the strongest of the new subtype experiments and beats both `conflict` and `health_risk` on the current transit-overlay run
- the current seed is dominated by accident/crash cases, so `Hostile Places` and especially `Drain / Breakdown` are not being tested against matched event families yet
- the raw natal `benefic_minus_malefic` comparator is still the strongest single natal-only comparator on this seed

Current research conclusion:

- the split-subtype approach is promising enough to keep as benchmark research
- it is not ready for product promotion as a generic warning model
- the next credible step is not more tuning on the same six cases; it is building subtype-matched retrospective seeds for:
  - acute accidents
  - hostile / violent / openly adversarial places
  - draining / breakdown / depletion environments

## Subtype-Matched Seed Results

That next step is now in repo. Three subtype-matched retrospective seeds were added:

- [accident_pressure_cases.jsonl](/Users/sabaa/Downloads/codexhorary/backend/benchmarks/astrocartography/accident_pressure_cases.jsonl)
- [hostile_places_cases.jsonl](/Users/sabaa/Downloads/codexhorary/backend/benchmarks/astrocartography/hostile_places_cases.jsonl)
- [drain_breakdown_cases.jsonl](/Users/sabaa/Downloads/codexhorary/backend/benchmarks/astrocartography/drain_breakdown_cases.jsonl)

All three still run through `goal_id = "risk_pressure"` so the runner exposes the same research comparators without creating new shipped goal ids.

### Accident Seed

Slice:

- 6 acute accident and crash cases
- same six rows filtered out from the mixed negative-place seed

Result:

- `natal_only`
  - `Accident Pressure`: `0.6667`
  - `conflict`: `0.7500`
  - `benefic_minus_malefic`: `0.7083`
  - deprecated `risk_pressure`: `0.2917`
- `event_transit_overlay`
  - `Accident Pressure`: `0.4583`
  - `conflict`: `0.5833`
  - `benefic_minus_malefic`: `0.5417`
  - deprecated `risk_pressure`: `0.2917`

Interpretation:

- the subtype-matched seed helped `Accident Pressure` substantially over the old generic-risk model
- transit overlay lowered performance, so this comparator should remain natal-first unless a later accident-specific transit hypothesis beats the natal run
- even on the crash-only slice, `conflict` and the raw benefic/malefic balance baseline still outperform the accident-specific research comparator

### Hostile Seed

Slice:

- 4 openly hostile-event cases
- John Lennon
- Monica Seles
- Nancy Kerrigan
- Bob Marley

Result:

- `natal_only`
  - `Hostile Places`: `0.5000`
  - deprecated `risk_pressure`: `0.6250`
  - `conflict`: `0.6250`
  - `benefic_minus_malefic`: `0.3750`
- `event_transit_overlay`
  - `Hostile Places`: `0.5625`
  - deprecated `risk_pressure`: `0.6250`
  - `conflict`: `0.5625`
  - `benefic_minus_malefic`: `0.3125`

Interpretation:

- the hostile-specific comparator did not dominate its own domain
- `conflict` is at least as good, and the deprecated research model actually scores best on this tiny seed
- the raw benefic/malefic baseline is weak here, which supports the idea that hostile places are not reducible to generic malefic load alone

### Drain / Breakdown Seed

Slice:

- 4 depletion and overdose-collapse cases
- Demi Lovato
- Whitney Houston
- Judy Garland
- Amy Winehouse

Result:

- `natal_only`
  - `Drain / Breakdown`: `0.1875`
  - deprecated `risk_pressure`: `0.6250`
  - `conflict`: `0.5625`
  - `benefic_minus_malefic`: `0.3750`
- `event_transit_overlay`
  - `Drain / Breakdown`: `0.1875`
  - deprecated `risk_pressure`: `0.6250`
  - `conflict`: `0.5625`
  - `benefic_minus_malefic`: `0.3750`

Interpretation:

- the current `Drain / Breakdown` heuristic fails on its own matched slice
- transit does not improve it at all
- this is a useful falsification: the current Saturn/Neptune/Pluto-heavy depletion logic is not yet describing real event-city outcomes well enough

### Updated Research Read

The subtype idea survives, but only in a narrow form:

- `Accident Pressure` is now the only subtype comparator that clearly improved when tested on a matched seed
- `Hostile Places` is plausible but not yet better than `conflict`
- `Drain / Breakdown` should be treated as a failed heuristic until redesigned

Current recommendation:

- keep subtype research alive
- do not ship any subtype as a product-facing caution model yet
- if further benchmark work continues, prioritize:
  1. more accident cases for `Accident Pressure`
  2. a larger hostile/adversarial seed before changing `Hostile Places`
  3. a redesign, not more blind benchmarking, for `Drain / Breakdown`

## Travel Goal Research Pass

The next product question explored after the warning-model work was:

- where should I travel for fun?
- where should I travel to relax?

Instead of pretending the existing goals already answered that cleanly, the repo now includes two first-pass specialist models in the backend catalog:

- `travel_fun` / `Travel for Fun`
- `travel_relax` / `Travel to Relax`

Current product state:

- both models are hidden from the frontend picker
- they remain available in the backend catalog and benchmark harness for research work
- they were hidden because the first benchmark pass did not justify exposing them as public presets

These were built from the local corpus, not from generic UX labeling:

- 3rd house: short journeys
- 5th house: pleasure, recreation, joy, celebration
- 9th house: long journeys, foreign countries, horizon-expansion
- 4th/12th with Moon/Venus/Jupiter/Neptune: restoration, retreat, decompression

The `travel_fun` model also references the external legacy file:

- `LOVE_CHILDREN_SPECULATION.HYP`

because it is the closest recovered pleasure-oriented rule family in the local legacy material.

The `travel_relax` model uses:

- `HOME.HYP`

as a structural ancestor, but shifts the emphasis away from permanent rooting and toward restorative travel.

### Travel Seed Design

Two new exploratory seeds were added:

- `travel_fun_cases.jsonl`
  - 3 leisure / honeymoon cases
  - Prince William
  - Nicole Kidman
  - George Harrison
- `travel_relax_cases.jsonl`
  - 4 retreat / restoration cases
  - Mia Farrow
  - Paul McCartney
  - George Harrison
  - Donovan

Both seeds currently use:

- explicit coordinates
- home/work controls rather than alternate vacation destinations
- `transit_context.location_strategy = "event"`

That last choice is intentional. For travel-event validation, the destination itself is the more meaningful transit anchor than the current frontend default natal fallback.

### Travel Fun Result

- `natal_only`
  - `travel_fun`: `0.3333`
  - parent `friends`: `0.5833`
  - `protective_places`: `0.5000`
  - `benefic_minus_malefic`: `0.5000`
  - `love`: `0.3333`
- `event_transit_overlay`
  - `travel_fun`: `0.3333`
  - parent `friends`: `0.3333`
  - `protective_places`: `0.5000`
  - `benefic_minus_malefic`: `0.3333`
  - `love`: `0.2500`

Interpretation:

- the model is source-backed, but the first weighting pass is not outperforming the closest existing goals
- `friends` is still the stronger natal-only comparator
- `protective_places` is unexpectedly the best performer on this honeymoon-heavy slice
- transit overlay does not add value here

The honest read is that this first-pass travel-fun model still behaves like a weaker, more opinionated rewrite of existing benefic-ease scoring.

### Travel Relax Result

- `natal_only`
  - `travel_relax`: `0.2500`
  - parent `home_retreat`: `0.7500`
  - `beliefs`: `0.5625`
  - `protective_places`: `0.2500`
  - `benefic_minus_malefic`: `0.2500`
- `event_transit_overlay`
  - `travel_relax`: `0.2500`
  - parent `home_retreat`: `0.6250`
  - `beliefs`: `0.5625`
  - `protective_places`: `0.2500`
  - `benefic_minus_malefic`: `0.2500`

Interpretation:

- the current relax-travel model does not justify itself against `home_retreat`
- the seed is strongly destination-concentrated in Rishikesh, so it is still exploratory
- even with that caveat, `home_retreat` is already doing a much better job of identifying this kind of restorative destination

### Practical Outcome

- the travel-model suggestion was implemented and benchmarked
- neither travel subtype is validated yet
- both travel models are now research-only from the product perspective because the frontend hides them
- `travel_fun` is exploratory and currently weaker than `friends` and `protective_places`
- `travel_relax` currently looks unnecessary relative to `home_retreat`

If travel benchmarking continues, the next high-value change is dataset quality, not more label proliferation:

- add alternate fun destinations beyond honeymoons
- add alternate retreat destinations beyond Rishikesh
- add control destinations that are other real travel options, not only home/work cities
- only then revisit whether a specialist travel model actually beats the nearest existing parent model

## Public Accident Model Added

Despite the mixed subtype results, one product-driven move was still made:

- a public accident-specific warning model was added as `accident_prone`
- frontend label: `Prone to Accidents`

Why this narrower model was chosen:

- it is more specific than the failed generic `risk_pressure` lens
- it states a concrete warning claim instead of a vague "bad places" claim
- transit is explicitly ignored because the accident-specific benchmark got worse with transit overlay

Current direct benchmark on the 6-case accident seed:

- `natal_only`
  - `Prone to Accidents`: `0.4583`
  - `conflict`: `0.5000`
  - `health_risk`: `0.4167`
  - `benefic_minus_malefic`: `0.7083`
- `event_transit_overlay`
  - `Prone to Accidents`: `0.4583`
  - `conflict`: `0.5417`
  - `health_risk`: `0.4583`
  - `benefic_minus_malefic`: `0.5417`

Interpretation:

- the model is now semantically clean: higher score truly means more accident-prone
- the ranking is stable across both product modes because transit is intentionally ignored
- benchmark performance is still only moderate; this model does not beat `conflict` or the simple natal benefic/malefic baseline on the current accident seed
- it should therefore be described as a narrow warning lens, not as an empirically superior all-purpose accident predictor

## Minimum Success Thresholds

These are not final scientific thresholds, but they are reasonable go or no-go gates for product work.

- pairwise win rate should beat 0.50 by a meaningful margin
- specialist model should beat its parent model on held-out cases
- event-date transit overlay should help or stay neutral; if it consistently hurts, it should not be used in scoring claims
- if a specialist model cannot beat simple baselines, it should remain experimental

Practical first-pass targets:

- `gambling_luck`: pairwise win rate above 0.60 on a curated pilot
- `health_risk`: pairwise win rate above 0.58 on a curated pilot
- specialist-over-parent lift: at least 5 percentage points on the same benchmark slice

## Output Shape For A Benchmark Run

Every run should emit:

- a per-case result table
- an aggregate metrics summary
- a comparison against parent and heuristic baselines
- a short failure review listing the worst misses

Recommended summary fields:

- case count
- usable case count after exclusions
- pairwise win rate
- top-3 hit rate
- mean reciprocal rank
- parent-model lift
- heuristic-baseline lift
- transit-overlay delta

## Immediate Implementation Work

Recommended next code slice:

- define a benchmark CSV or JSONL schema
- add a small loader under `backend/`
- add a benchmark runner that scores event and control cities per person
- output pairwise accuracy, top-k accuracy, and baseline comparisons

## Honest Boundary

These models are explainable and source-backed inside Vox Stella.

They are not yet historically validated.

Until benchmark work exists, product language should avoid implying that the models are empirically proven against real-world life-event datasets.
