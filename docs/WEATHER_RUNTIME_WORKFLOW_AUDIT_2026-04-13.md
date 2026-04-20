# Weather Runtime Workflow Audit

Status date: 2026-04-13

## Scope

This audit records the current weather runtime as it exists now.

It answers four questions:

1. what the weather workflow is
2. what inputs it accepts
3. what outputs it returns
4. how closely the implementation matches the local source corpus

This is a current-state audit, not a change proposal.

## Frontend Workflow

The weather workspace now has two modes:

1. `analysis`
2. `scan`

`scan` is the default mode.

### Analysis path

The current analysis workflow is:

1. choose one weather family
2. optionally override forecast date, time, location, and timezone
3. resolve context
4. analyze

The frontend sends that through:

- `GET /api/astro-clock/weather/context/resolve`
- `GET /api/astro-clock/weather/analyze`

### Scan path

The current scan workflow is:

1. choose one weather family
2. choose scan scope:
   - `place_timeline`
   - `region_timeline`
3. choose either:
   - a specific place
   - or a region plus atlas resolution and candidate limit
4. choose a bounded time window
5. run scan
6. read either:
   - graph view
   - ranked dates / cells view

The frontend sends that through:

- `GET /api/astro-clock/weather/scan/catalog`
- `GET /api/astro-clock/weather/scan/run`

## Runtime Inputs

### Analysis request

The analysis runtime accepts:

- `family_id`
- `forecast_datetime`
- `location`
- `timezone`
- `latitude`
- `longitude`
- `house_system_code`
- `source_preference`

Fallbacks:

- forecast datetime falls back to the active Astro Clock timestamp
- location falls back to the active Astro Clock location
- timezone falls back to the active Astro Clock timezone
- house system falls back to the active Astro Clock house system

### Scan request

The scan runtime accepts:

- `family_id`
- `scan_scope`
- `start_datetime`
- `end_datetime`
- `time_step_hours`
- `top_k`
- `location`
- `timezone`
- `latitude`
- `longitude`
- `region_id`
- `resolution`
- `candidate_limit`
- `house_system_code`
- `source_preference`

Scope rules:

- `place_timeline` requires a place
- `region_timeline` requires a region id

Current hard bounds:

- max time slices: `120`
- max evaluated cells: `720`
- max candidates: `20`
- default step: `6h`
- default candidates: `6`
- default top k: `8`

## Runtime Families

The current runtime exposes four weather families:

1. `flood_risk`
2. `hurricane_pressure`
3. `severe_convective_pressure`
4. `wind_event_pressure`

These are family-specific outputs, not one generic weather score.

That is aligned with the source inventory, which already supports separate families for:

- wind
- drought
- floods
- heat and cold extremes
- hurricanes
- snow / sleet / freezing rain
- thunderstorms / hail / tornadoes

The runtime is therefore narrower than the benchmark branch on purpose.

## Backend Workflow

### Analysis path

The current backend sequence is:

1. parse a `WeatherContextRequest`
2. load the selected family from runtime assets
3. resolve the forecast datetime and location from request or active clock
4. resolve chart context
5. evaluate the selected family against the resolved charts
6. attach doctrine and benchmark-calibration metadata

### Chart resolution

The chart resolver currently computes three layers:

1. `forecast_chart`
2. latest cardinal ingress before the forecast time
3. latest lunar phase before the forecast time

That means the runtime is structurally:

- seasonal framework
- short trigger layer
- present-time chart

The returned chart-resolution payload includes:

- primary chart
- supporting charts
- ingress identity
- lunar phase identity
- angular hits for each resolved chart

### Family evaluation

Each family evaluator currently:

1. indexes the resolved charts
2. evaluates family-specific rules
3. groups those rules into:
   - framework notes
   - trigger notes
   - locality notes
4. sums note scores into a family score
5. maps that score into a level:
   - `quiet`
   - `watch`
   - `elevated`
   - `active`

### Scan path

The weather scan runtime currently:

1. validates the scan request
2. builds the time grid
3. resolves a candidate pool:
   - one place
   - or many atlas candidates from a chosen region
4. evaluates every candidate-time cell by running the same analysis stack
5. ranks raw cells by score
6. separately builds place series
7. returns both:
   - `results` for top candidate-time cells
   - `series` for graphing place behavior across time

This is important:

The scan is not a distinct meteorological engine.

It is the analysis runtime repeated across candidate places and timepoints, then summarized.

## Current Output Shape

### Analysis output

The analysis runtime returns:

- `context`
- `framework_layer`
- `trigger_layer`
- `locality_layer`
- `family_assessment`
- `doctrine`
- `research`

`family_assessment` includes:

- family id and label
- benchmark family id
- score
- level
- summary
- matched rules
- signal counts

`research` includes:

- runtime status
- runtime scope
- benchmark calibration
- flags
- limitations

### Scan output

The scan runtime returns:

- `request`
- `counts`
- `scope`
- `results`
- `series`
- `calibration`
- `runtime_scope`

`results` are top raw candidate-time cells.

`series` includes:

- timeline
- places
- peak candidates
- series overview

Each place series includes:

- location
- peak score
- peak datetime
- peak selection shape
- candidate index
- candidate kind
- full time series

So the scan output is already closer to the mundane scan pattern than to a single weather reading.

## Comparison To The Source Corpus

## Where the runtime matches the sources

### 1. Family partitioning

This is a good match.

The local corpus supports family-level weather doctrine, and the runtime preserves that instead of collapsing everything into one weather output.

### 2. Seasonal plus lunar layering

This is also a good match.

The sources support:

- solar ingresses for the larger weather frame
- lunar phases for shorter triggers

The runtime does exactly that.

### 3. Trigger-oriented interpretation

This is a partial but real match.

The source corpus repeatedly uses aspect and planet combinations to distinguish storm families, and the runtime does preserve family-specific signals such as:

- Saturn-Neptune flood testimony
- Mercury-Uranus and Mars-Uranus storm testimony
- Mercury-led wind logic

### 4. Benchmark-backed calibration

This is stronger than the source corpus alone.

The runtime does not only cite doctrine. It also carries benchmark profile data per family, which is the correct engineering shape for a research-gated system.

## Where the runtime is narrower than the sources

### 1. Locality logic is still reduced to a proxy

This is the biggest gap.

The sources support:

- map lines
- horizon and meridian logic
- line intersections
- path logic for storms and fronts

The current runtime does not implement that.

Instead it uses forecast-chart angularity and nearest-angle emphasis as a locality proxy.

This is already admitted in the schema and runtime flags, but it remains the main doctrinal gap.

### 2. Eclipse timing is absent from active weather runtime logic

The doctrine inventory says eclipse dates are part of timing context.

The current weather runtime does not actively resolve or score eclipse triggers. It uses:

- cardinal ingress
- lunar phase
- forecast chart

That makes the runtime cleaner, but narrower than the corpus.

### 3. The runtime supports only four families

The benchmark branch and doctrine inventory are broader than the live engine.

Not yet in runtime:

- drought
- snow / freezing precipitation
- temperature extremes
- generalized seasonal temperature

This is a deliberate maturity gate, not a bug, but it is still a current gap between corpus scope and runtime scope.

### 4. Scan uses the same family runtime repeatedly

This is efficient and coherent, but it also means the scan does not yet have a distinct weather-map model.

So a scan result is best interpreted as:

- repeated family pressure checks across a grid

not as:

- a full astrometeorological map engine

## Comparison To The Benchmarks

The weather branch currently has:

- doctrine / coverage benchmarks
- predictive hindcast benchmarks

The current hardened hindcast result is:

- `9` cases
- `5` alignment passes
- `55.6%` alignment pass rate
- `2` target-window hits
- `3` near passes
- `12h` median peak distance

That means the current runtime can often elevate the real event window, but it still does not justify strong forecasting claims.

Family shape from the latest result:

- `flood_risk` is now the strongest family in the current hindcast set
- `hurricane_pressure` improved materially after concentration fixes
- `severe_convective_pressure` is mixed
- `wind_event_pressure` remains the weakest family

So the benchmark picture matches the implementation picture:

- flood and hurricane are the most convincing runtime families
- wind is still too permissive
- severe convective still needs better control-window discrimination

## Current-State Judgment

The current weather system is internally coherent.

Its workflow is:

1. choose a weather family
2. resolve seasonal and lunar context for a forecast time and place
3. score family-specific rules
4. optionally scan across time and place by repeating that same evaluation

That is a valid first runtime shape.

The strongest parts are:

- family partitioning
- ingress plus lunar layering
- benchmark-calibration attachment
- scan workflow coherence

The weakest parts are:

- locality still being proxy-only
- eclipse timing not being active in runtime
- wind still being under-discriminated
- scan still not being a true weather-map engine

## Practical Conclusion

Compared with the local sources, the weather runtime is:

- structurally aligned
- deliberately narrowed
- benchmark-backed
- still research-gated

It is not a doctrinal mismatch in the large.

Its current limitations are mostly the expected first-runtime limitations:

- too little locality machinery
- incomplete family coverage
- still-weak control discrimination in wind and one severe-convective slice

## Best Next Moves

If the goal is to narrow the remaining gaps without overextending:

1. improve locality/path logic before adding more generic signals
2. review whether eclipse-trigger support is source-strong enough to justify a bounded weather timing layer
3. keep runtime expansion family-by-family, not by adding a generic weather score
4. continue using the predictive hindcast suite as the acceptance gate before widening runtime scope
