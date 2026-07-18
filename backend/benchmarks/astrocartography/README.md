# Astrocartography Benchmarks

## Validation status

The source-alignment and model-stress fixtures are synthetic semantic checks
only. They test whether documented concepts map to the intended broad goal
families; they do not validate real-world outcomes, predictive accuracy, or
causal claims. Source-alignment fixtures use the
`minimal_source_signal_v2` policy: exact governed claim/page/chunk references,
at most one natal line, no baked crossings or relocation evidence, and no
positive doctrine assertions for experimental models.

The default stress gate evaluates only models whose catalog status is `active`
and whose composition is `standalone`. It fails public semantic errors and raw
score-vector cosine overlap at or above `0.92` among that peer population.
Every other catalog model is listed with its status and exclusion reason.

Active parent/specialist compositions are not independent peers. Comparing
their full scores with cosine would mostly measure the declared parent
inheritance, so the stress report replaces that comparison with bounded
specialist-residual distinctness and lift diagnostics. These diagnostics are a
separate section and do not silently enter the default standalone peer gate.

Models with `experimental` status are reported in a clearly labeled,
non-public research section. Deprecated models are inventoried but not scored
as public peers. Neither synthetic residual diagnostics nor research rankings
are promotion gates. Public specialist promotion still requires positive lift
on a deterministic, person-grouped holdout set, with the same frozen,
exposure-matched control design used for every comparator and uncertainty
reported with person-clustered bootstrap intervals when the sample permits.

Benchmark summaries use equal case-level weighting by default so people with
more control cities do not dominate the result. Pooled pair counts are reported
separately as diagnostic micro-averages. Comparator lift is calculated only on
the cases shared with the product model.

Older numeric snapshots below that call a parent or existing goal model a
"baseline" predate this correction. Production-model comparisons are no longer
treated as independent evidence and must be regenerated with the current
harness before they are cited.

This folder holds curated benchmark datasets for validating Astrocartography PathFinder models against real event-location cases.

The benchmark runners are:

- `backend/run_astrocartography_benchmark.py`
- `backend/run_astrocartography_pathfinder_benchmark.py`

Current intended datasets:

- `astrodatabank_poker_cases.jsonl`
- `speculation_cases.jsonl`
- `health_risk_cases.jsonl`
- `risk_pressure_cases.jsonl`
- `accident_pressure_cases.jsonl`
- `hostile_places_cases.jsonl`
- `drain_breakdown_cases.jsonl`
- `travel_fun_cases.jsonl`
- `travel_relax_cases.jsonl`
- `source_alignment_cases.jsonl`

## Ground Rules

- Keep cases frozen once they enter a reported benchmark run.
- Do not hand-pick control cities after seeing the score output.
- Prefer explicit city labels with country names.
- Prefer explicit time zones when known.
- Use only high-confidence birth data for serious reporting.

## JSONL Record Shape

Each line is a standalone JSON object.

Required top-level fields:

- `enabled`
- `case_id`
- `goal_id`
- `person_name`
- `birth`
- `event`
- `controls`

Recommended fields:

- `person_id`
- `sources`
- `notes`
- `transit_context`
- `benchmark_family`
- `benchmark_type`
- `control_selection`
- `performance_context`

## Birth Block

Required:

- `date`
- `time`
- `place`

Optional:

- `timezone`
- `data_quality`

## Event Block

Required:

- `type`
- `date`
- `location`

Optional:

- `time`
- `outcome_polarity`

`location` may be a string or an object.

If using an object, these are supported:

- `label`
- `latitude`
- `longitude`
- `timezone`

## Control Locations

Each entry may be a string or an object.

Supported object fields:

- `label`
- `latitude`
- `longitude`
- `timezone`
- `reason`

## Transit Context

The benchmark runner supports the current product logic:

- `natal_only`
- `event_transit_overlay`

For transit overlay cases, you can optionally provide:

- `transit_context.location_strategy`
- `transit_context.location`
- `transit_context.timezone`

Supported `location_strategy` values:

- `natal`
- `event`
- `explicit`

Default is `natal`, which matches the current frontend fallback when transit location and time zone are left blank.

## Usage

From the repo root:

```powershell
python backend/run_astrocartography_benchmark.py --dataset backend/benchmarks/astrocartography/speculation_cases.jsonl --mode natal_only
python backend/run_astrocartography_benchmark.py --dataset backend/benchmarks/astrocartography/speculation_cases.jsonl --mode event_transit_overlay
python backend/run_astrocartography_pathfinder_benchmark.py --dataset backend/benchmarks/astrocartography/speculation_cases.jsonl --mode natal_only
python backend/run_astrocartography_pathfinder_benchmark.py --dataset backend/benchmarks/astrocartography/speculation_cases.jsonl --mode event_transit_overlay
```

Useful options:

- `--output-json <path>`
- `--output-md <path>`
- `--case-id <id>`
- `--allow-live-geocode`

Builder path for Astro-Databank-linked poker profiles:

```powershell
python backend/build_astrodatabank_poker_cases.py
python backend/build_astrodatabank_poker_cases.py --input backend/benchmarks/astrocartography/astrodatabank_poker_profiles.template.jsonl --output backend/benchmarks/astrocartography/astrodatabank_poker_cases.jsonl
```

Benchmark semantics:

- the evaluator runner benchmarks `evaluate_goal_model(...)` directly against event/control cities
- the PathFinder runner benchmarks the live frozen-candidate atlas flow, including shortlist strategy, relocation rescoring, final viability filtering, and final ranking
- ranking order is now `raw_score` first and bucketed display `score` second across the benchmark runner, atlas ranking helper, and compare API so failures are reproducible from the product UI
- for `gambling_luck`, the product evaluator still sets `transit_strategy = "ignore"`, so the product-model rows should stay identical between `natal_only` and `event_transit_overlay`

## Astro-Databank Poker Design

The next gambling benchmark direction is a repeated-venue dataset built from:

- high-confidence natal data, ideally Astro-Databank `AA` or `A`
- separate public result history for the same person, ideally tournament pages with dated venues
- within-person venue comparisons rather than one-off winning cities

The benchmark question is:

- does the model rank the city of a strong breakthrough or title above weaker venues the same person actually played in?

This is intentionally different from naive "winning city" validation:

- it controls for exposure because Las Vegas and other major circuits appear often
- it reduces survivorship bias by comparing strong and weak outcomes from the same person
- it fits both the evaluator benchmark and the end-to-end PathFinder benchmark without changing the scoring logic

Required curation rules for this dataset family:

- keep birth provenance explicit and prefer `AA` or `A`
- use same-person controls whenever possible
- do not compare a title city only against neutral home cities when same-player venue history exists
- record why each control was chosen
- separate breakthrough wins from competing-positive venues in the notes

Recommended extra metadata on these cases:

- `benchmark_family = "astrodatabank_poker"`
- `benchmark_type = "within_person_venue_performance"`
- `control_selection`
- `performance_context`
- `event.result_label`
- `event.outcome_strength`
- `event.outcome_tier`
- `controls[*].result_label`
- `controls[*].outcome_strength`
- `controls[*].outcome_tier`

## Astro-Databank Poker Builder

The repo now includes a builder that converts higher-level player profiles into the current event-vs-control benchmark shape:

- builder: [build_astrodatabank_poker_cases.py](/Users/sabaa/Downloads/codexhorary/backend/build_astrodatabank_poker_cases.py)
- input template: [astrodatabank_poker_profiles.template.jsonl](/Users/sabaa/Downloads/codexhorary/backend/benchmarks/astrocartography/astrodatabank_poker_profiles.template.jsonl)
- output dataset: `astrodatabank_poker_cases.jsonl`

Builder contract:

- each input profile describes one person, one natal source block, a performance history, and explicit benchmark targets
- each benchmark target points to one event performance and an explicit list of same-person control performance ids
- the builder emits benchmark-ready rows using the existing `event` and `controls` schema, so the current evaluator and PathFinder runners can consume them directly

Important limitation:

- this is a dataset-construction tool, not a scraper
- Astro-Databank birth records and event-history pages still need to be curated manually before a case should be enabled

Current seed state:

- the repo now includes a real exploratory profile seed at `astrodatabank_poker_profiles.jsonl`
- the default builder input now points at that file rather than the disabled template
- the first live seed contains 5 enabled `gambling_luck` cases built from existing Astro-Databank-linked poker rows already curated in the repo
- all current rows use `transit_context.location_strategy = "event"` because the venue itself is what the benchmark is testing
- this seed is still exploratory because some players have only one clean control venue and some excluded profile performances remain competing-positive cities rather than neutral controls

## Source Alignment

The historical benchmark runner validates event cities against controls. For source-backed semantic drift testing, use the dedicated source-alignment runner instead:

```powershell
python backend/run_astrocartography_source_alignment.py
python backend/run_astrocartography_source_alignment.py --case-id lewis_sun_publicity
python -m pytest backend/test_astrocartography_source_alignment.py -q
```

`source_alignment_cases.jsonl` is intentionally different from the historical datasets:

- it encodes compact source claims rather than event/control city contests
- it feeds `evaluate_goal_model(...)` directly with curated natal rows, crossings, and relocation features
- it is designed to catch model drift against Jim Lewis and normalized reference claims before any map or atlas behavior is involved

## Current Dataset Status

Current repo state:

- `speculation_cases.jsonl` now contains a small exploratory seed with enabled real-world cases
- `health_risk_cases.jsonl` now contains a small exploratory seed with enabled real-world warning cases
- `risk_pressure_cases.jsonl` now contains a small exploratory seed for the research-only `risk_pressure` model
- `travel_fun_cases.jsonl` now contains a tiny exploratory leisure-travel seed built from honeymoon and celebration destinations
- `travel_relax_cases.jsonl` now contains a tiny exploratory retreat-travel seed built from Rishikesh-style restoration cases

Important caveat:

- the current speculation seed is useful for pipeline validation and early model comparisons
- it is not yet a publication-grade benchmark
- several control cities are still weak or competing-positive venues rather than clean neutral controls
- the current health-risk seed is even more exploratory than the speculation seed because several controls are home-base or same-domain exposure cities rather than clean matched controls
- the current generic-risk seed is also exploratory and should be read as a public warning-model benchmark, not a publication-grade validation set

Current health-risk seed:

- 4 enabled cases
- Sonny Bono, Dale Earnhardt, Ayrton Senna, and James Dean
- all event and control cities use explicit coordinates to avoid city-catalog resolution drift
- two rows use known event times, two rows still rely on the runner's noon fallback in transit-overlay mode

Current exploratory health-risk benchmark snapshot:

- `natal_only`: product `health_risk` pairwise win rate `0.375`
- `event_transit_overlay`: product `health_risk` pairwise win rate `0.5000`
- parent `conflict`: `0.3125` natal, `0.2500` transit
- `malefic_pressure` heuristic: `0.3125` natal, `0.5000` transit
- `benefic_minus_malefic`: unexpectedly strongest natal-only baseline at `0.8125`

Practical reading:

- the current `health_risk` model is stronger than the `conflict` parent on this seed
- transit overlay improves the product model materially
- the current warning model still does not beat the simplest natal-only baseline, so it should be treated as exploratory rather than validated

Current generic-risk seed:

- 6 enabled `risk_pressure` cases
- Sonny Bono
- Dale Earnhardt
- Ayrton Senna
- James Dean
- Diana, Princess of Wales
- Frida Kahlo

Current exploratory `risk_pressure` benchmark snapshot:

- `risk_pressure` is now kept as a deprecated research model, not the public picker preset
- `natal_only`: product `risk_pressure` pairwise win rate `0.2917`
- `event_transit_overlay`: product `risk_pressure` pairwise win rate `0.2917`
- parent `conflict`: `0.4583` natal, `0.5833` transit
- experimental `health_risk`: `0.375` natal, `0.5000` transit
- `benefic_minus_malefic`: `0.7083` natal, `0.5417` transit

Practical reading:

- the deprecated `risk_pressure` model is semantically correct now, but it is weak on this seed
- locking the model to natal-only did not rescue benchmark performance after the polarity inversion
- on this 6-case exploratory seed, both `conflict` and `health_risk` outperform the public model, and the raw `benefic_minus_malefic` comparator remains stronger in natal mode
- this means the current public model is interesting for exploratory map discovery but not benchmark-validated as a reliable public warning model yet

## Risk Subtype Experiment

To test the earlier product suggestion that a future warning model should be split into narrower subtype lenses rather than one broad blob, the benchmark harness now includes four research-only comparators for `risk_pressure`:

- `Accident Pressure`
- `Hostile Places`
- `Drain / Breakdown`
- `Subtype Max` — the maximum of the three subtype scores for a city

These are benchmark-only comparators in [baselines.py](/Users/sabaa/Downloads/codexhorary/backend/benchmarks/astrocartography/baselines.py). They are not shipped frontend presets.

Current subtype benchmark snapshot on the same 6-case negative-place seed:

- `Accident Pressure`: `0.5000` natal, `0.5417` transit
- `Hostile Places`: `0.5833` natal, `0.5417` transit
- `Drain / Breakdown`: `0.3750` natal, `0.3750` transit
- `Subtype Max`: `0.5000` natal, `0.6250` transit

Practical reading:

- splitting the warning problem into subtypes is a better research direction than the old monolithic `risk_pressure` model
- every subtype comparator beats the deprecated product model in at least one mode
- `Subtype Max` is the strongest of the new subtype comparators and beats both `conflict` and `health_risk` on the current transit-overlay run
- the current seed is accident-heavy, so `Drain / Breakdown` is under-tested and should not be judged from these six cases alone
- the raw natal `benefic_minus_malefic` heuristic is still the strongest single natal-only comparator on this seed

Current recommendation:

- keep `Protective Places` public
- keep `risk_pressure` deprecated and research-only
- if a future public caution model is revisited, prototype it as subtype-based research first, not as one generic warning score

## Subtype-Matched Seeds

To test whether the subtype comparators are actually better on their own domain rather than only on the mixed negative-place seed, the repo now includes three frozen subtype-matched datasets:

- `accident_pressure_cases.jsonl`
- `hostile_places_cases.jsonl`
- `drain_breakdown_cases.jsonl`

All three still use `goal_id = "risk_pressure"` so the benchmark runner exposes the same research comparators:

- `Accident Pressure`
- `Hostile Places`
- `Drain / Breakdown`
- `Subtype Max`
- deprecated product `risk_pressure`
- parent `conflict`
- experimental `health_risk`
- `benefic_minus_malefic`

### Accident Slice

Dataset:

- 6 acute accident and crash cases
- copied from the existing mixed generic-risk seed

Current result:

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

Reading:

- subtype matching helped `Accident Pressure` materially over the old generic-risk product model
- transit made the accident comparator worse, not better
- even on crash-only cases, `conflict` and the simple benefic/malefic balance baseline remain stronger

### Hostile Slice

Dataset:

- 4 hostile-event cases
- John Lennon
- Monica Seles
- Nancy Kerrigan
- Bob Marley

Current result:

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

Reading:

- the hostile-specific comparator did not dominate its own slice
- the structured `conflict` parent is at least as good, and the deprecated research model actually ranks best on this tiny seed
- the raw benefic/malefic baseline is clearly weak on hostile events, which suggests hostile places are not just "more malefic"

### Drain / Breakdown Slice

Dataset:

- 4 depletion and overdose-collapse cases
- Demi Lovato
- Whitney Houston
- Judy Garland
- Amy Winehouse

Current result:

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

Reading:

- the current `Drain / Breakdown` heuristic fails on its own domain
- transit does not rescue it at all
- the deprecated research model is unexpectedly much stronger on this tiny slice than the drain-specific comparator
- this is a research failure, not a product candidate

### Practical Conclusion

The subtype idea is still directionally useful, but the results are mixed:

- `Accident Pressure` is the only subtype comparator that clearly improved when moved onto a matched seed
- `Hostile Places` is plausible but not clearly better than `conflict`
- `Drain / Breakdown` is currently wrong enough to treat as a failed experiment

Current recommendation after subtype-matched testing:

- keep subtype research alive
- do not promote any subtype comparator to the product yet
- treat `Accident Pressure` as the only subtype worth further iteration right now
- revisit `Hostile Places` only after the seed grows beyond four cases
- redesign or discard the current `Drain / Breakdown` heuristic before spending more benchmarking effort on it

## Public Accident Warning Model

The repo now also includes a public warning model built from the accident-specific subtype work:

- goal id: `accident_prone`
- frontend label: `Prone to Accidents`

Important product rules:

- higher score = more accident-prone place
- transit is ignored
- the runtime uses the shared accident-pressure heuristic directly so the shipped model and benchmark logic stay aligned

Current benchmark on the 6-case accident seed:

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

Practical reading:

- the model's ranking semantics are now stable and explicit: higher really means more accident-prone
- locking transit out keeps the score stable across modes, which was the intended product behavior
- benchmark strength is still mixed; this model does not currently beat `conflict` or the simple natal benefic/malefic baseline on the accident seed
- it should therefore be treated as a narrower warning lens, not as a proven universal hazard model

## Travel Goal Experiment

The repo now also includes two travel-specific specialist goal models in the backend catalog:

- goal id: `travel_fun`
- backend label: `Travel for Fun`
- goal id: `travel_relax`
- backend label: `Travel to Relax`

Important product-state note:

- both travel models are currently hidden from the frontend picker
- they remain in the backend catalog and benchmark harness for research only
- this was done because the first benchmark pass did not justify exposing them as public presets

These were added to answer a narrower product question than generic love, friends, or home scoring:

- where should I go for an enjoyable, celebratory, light trip?
- where should I go for decompression, retreat, or restoration?

The first exploratory benchmark seeds are intentionally small and narrow:

- `travel_fun_cases.jsonl`
  - 3 honeymoon / celebration destination cases
  - Prince William, Nicole Kidman, George Harrison
  - controls are home or work cities, not alternate vacation cities
- `travel_relax_cases.jsonl`
  - 4 retreat / restoration destination cases
  - Mia Farrow, Paul McCartney, George Harrison, Donovan
  - all destination rows currently point to Rishikesh, so this is a retreat-slice benchmark, not a broad relax-travel benchmark

Important caveat:

- both datasets use `transit_context.location_strategy = "event"` because the destination itself is what is being validated
- that is a stronger fit for research benchmarking than the current frontend default transit fallback

### Travel for Fun

Current result:

- `natal_only`
  - `Travel for Fun`: `0.3333`
  - parent `friends`: `0.5833`
  - `protective_places`: `0.5000`
  - `benefic_minus_malefic`: `0.5000`
  - `love`: `0.3333`
- `event_transit_overlay`
  - `Travel for Fun`: `0.3333`
  - parent `friends`: `0.3333`
  - `protective_places`: `0.5000`
  - `benefic_minus_malefic`: `0.3333`
  - `love`: `0.2500`

Reading:

- the first-pass leisure-travel model does not currently beat `friends`
- transit overlay does not improve it on this seed
- on this tiny honeymoon-heavy slice, a broad ease/protection model still beats the specialist fun-travel model
- that suggests the current `travel_fun` weighting is still underfitting simple benefic ease and overclaiming subtype precision

### Travel to Relax

Current result:

- `natal_only`
  - `Travel to Relax`: `0.2500`
  - parent `home_retreat`: `0.7500`
  - `beliefs`: `0.5625`
  - `protective_places`: `0.2500`
  - `benefic_minus_malefic`: `0.2500`
- `event_transit_overlay`
  - `Travel to Relax`: `0.2500`
  - parent `home_retreat`: `0.6250`
  - `beliefs`: `0.5625`
  - `protective_places`: `0.2500`
  - `benefic_minus_malefic`: `0.2500`

Reading:

- the first-pass restoration-travel model is clearly weaker than `home_retreat`
- the relax seed is currently too concentrated in one destination to treat as publication-grade evidence
- even with that caveat, the current `travel_relax` model is not justified as a stronger alternative to simply using `home_retreat`
- transit overlay does not rescue it

### Practical Read

- the new travel models are now source-backed and benchmarked
- neither one is benchmark-validated as a stronger public model than the closest existing goal family
- both are currently research-only from a product perspective because the frontend hides them
- `travel_fun` is interesting but currently weaker than `friends` and `protective_places`
- `travel_relax` currently underperforms `home_retreat` badly enough that it should be treated as exploratory
- if travel research continues, the next worthwhile step is not adding more public travel labels; it is curating stronger travel-specific seeds with alternate leisure and retreat destinations rather than only home/work controls

## Legacy Inspection Note

The current `gambling_luck` relocation logic was revised after reviewing three external legacy `.HYP` models:

- `Gambling_Elect_Personal.hyp`
- `MONEY_GAINS_INVESTMENTS.HYP`
- `CAREER_BUSINESS_PARENT.HYP`

The key finding was that the gambling family is more asymmetric than the money or career parents:

- speculative upside is present, but anti-speculation signatures are punished much more sharply
- 5th/11th-house style upside matters more than generic 2nd/8th-house money placement

That inspection is why the current engine now separates:

- `speculation`: weighted upside
- `speculation_drag`: negative relocated drag

Current shipped gambling search choice:

- the atlas now uses a model-specific `relocation_prepass` shortlist strategy for `gambling_luck`
- that lets relocation-heavy gambling metrics participate before the final shortlist instead of only after a line-first cutoff
- the shared atlas/UI/benchmark ranking order is now `raw_score` first, with bucketed display `score` only as a secondary tiebreaker

## Gambling Benchmark Snapshot

Current evaluator snapshot on `speculation_cases.jsonl` after the relocation-prepass atlas fix and raw-score ranking alignment:

- `natal_only`
  - `Product Model`: `0.4615`
  - `Parent Model (Money)`: `0.5000`
  - `Jupiter Venus Heuristic`: `0.4615`
  - `Gambling Lines Only`: `0.3846`
  - `Gambling No Activation Floor`: `0.3846`
  - `Gambling Relocation Only`: `0.5769`
- `event_transit_overlay`
  - `Product Model`: `0.4615`
  - `Parent Model (Money)`: `0.5769`
  - `Jupiter Venus Heuristic`: `0.5000`
  - `Gambling Lines Only`: `0.4231`
  - `Gambling No Activation Floor`: `0.4231`
  - `Gambling Relocation Only`: `0.5769`

Practical read:

- the full gambling product model improved relative to the earlier `0.3846` seed result, but it still trails the `money` parent on this frozen benchmark
- the relocation-only ablation is the strongest comparator on the current seed, which means the live signal is coming more from relocated gambling metrics than from the natal line layer
- removing the activation floor makes the benchmark worse, not better, so the activation gate is currently helping rather than hiding strength
- because the product model ignores transit, its evaluator score is unchanged across `natal_only` and `event_transit_overlay`

Current frozen-candidate PathFinder snapshot on the same seed:

- `prepass_hit_rate`: `1.0`
- `shortlist_hit_rate`: `1.0`
- `final_ranked_rate`: `0.2857`
- `top_1_hit_rate`: `0.0`
- `top_3_hit_rate`: `0.2857`
- `mean_initial_rank`: `2.2857`
- `mean_final_rank`: `3.1429`
- `dropped_after_prepass_count`: `5`

Practical read:

- the relocation-prepass change fixes the specific shortlist-blindness problem for the current frozen event/control pools: event cities are no longer dropped before relocation rescoring
- the main failure mode on this seed is now final viability filtering, not shortlist survival
- this PathFinder seed still uses event plus controls as the frozen candidate pool, so it validates live ranking semantics and viability filtering but does not yet stress atlas-scale truncation pressure
- to stress the shortlist strategy harder, add larger `candidate_pool` arrays per case so the event city has to survive a materially larger prepass field
