# Transits 1615 Hindcast Failure Review
Date: 2026-04-14

## Scope

This note inspects the failing documented hindcast case:

- `transits_documented_hindcast_drowning_1615`

Question:

- is the miss mainly predictor timing-window aggregation drift
- or a deeper event-family scoring/ranking problem

## Case Definition

- natal: `1583-02-23 05:45 UTC`, `Villefranche, France`
- target event: Morin near-drowning
- target window: `1615-07-07` to `1615-07-08`
- current benchmark expectation:
  - `life_area = danger`
  - `event_type = accident_major`

## Source Baseline

The local Morin source material is clear about the doctrinal shape of this case.

From the internal Morin notes:

- the `1615-07-07` case is explicitly treated as a near-drowning / danger-to-life example
- the formula emphasized is malefic contact to the Ascendant with concordant direction
- Morin's flow remains:
  - radix determination
  - direction opening the period
  - revolution agreement
  - transit as the trigger of the precise day

That means the runtime should not merely find some adverse content somewhere inside the window. It should localize the danger-family trigger near the event date and keep it ahead of unrelated benefic families.

## Observed Runtime Behavior

### 1. Exact-Day Analysis

Exact analysis on `1615-07-07T12:00:00+00:00` does contain the expected danger family.

Strong exact-day predictions include:

- `accident_major | danger | Mars Opposition Saturn`
- `accident_major | danger | Mars Quincunx Asc`
- `accident_major | danger | Mars Opposition Sun`
- `accident_major | danger | Mars Opposition Moon`

So the failure is not "the engine cannot see the danger family at all."

### 2. Window Scan Behavior

The problem appears earlier than predictor aggregation.

Inside the scan rows around the actual target window:

- `1615-07-06` rows are topped by `public_recognition | honors`
- `1615-07-07` rows are still topped by `promotion | honors`
- `1615-07-08` rows shift toward `marriage | marriage`

So even near the event window, the scan's row-level top family is usually not the crisis family.

The highest scan rows in the whole window are even more skewed:

- early `1615-07-01` rows are dominated by `promotion | honors`
- those rows outrank the later target-window danger rows by total `step_score`

This means the predictor is inheriting a ranking problem that already exists in the scan rows.

### 3. Predictor Group Behavior

Predictor output shows the same split:

- rank 1:
  - `opportunity_received | life | Jupiter Trine Moon`
  - dominant timestamp `1615-07-02`
- rank 2:
  - `accident_major | danger | Mars Opposition Saturn`
  - dominant timestamp `1615-07-01`
- lower ranks still contain more `accident_major | danger` groups
  - `Mars Opposition Moon`
  - `Mars Opposition Sun`
  - `Mars Quincunx Asc`

So predictor aggregation is not inventing the crisis family. It is grouping it, but the dominant timestamps remain early because the earlier rows were already scored more strongly.

## Diagnosis

The miss is **not mainly a pure predictor aggregation problem**.

It is a layered issue:

1. **Primary problem: event-family scoring / ranking inside scan rows**
   - the target-window rows are being topped by honors and marriage families
   - this is doctrinally wrong for a documented near-drowning benchmark
   - the exact-day engine can see danger, but row-level ranking is not preserving that crisis emphasis

2. **Secondary problem: predictor timing-window aggregation drift**
   - once scan rows are already early-biased, predictor grouping chooses early dominant timestamps
   - this makes the danger-family cluster localize around `1615-07-01` instead of the event window

So the correct conclusion is:

- **mostly a deeper event-family scoring/ranking problem**
- with **additional predictor timing-window drift layered on top**

## Why This Matters

If the issue were only aggregation drift, the scan rows near `1615-07-07` would already be dominated by the danger family and predictor would merely be choosing the wrong representative timestamp.

That is not what the current runtime shows.

The runtime is currently letting unrelated benefic and non-crisis families outrank the documented crisis family during the same window. That means fixing predictor aggregation alone would not fully solve the benchmark miss.

## Narrow Fix Order

The next fixes should happen in this order:

1. **Fix row-level crisis ranking**
   - when malefic-to-Asc / danger testimony is exact and directionally concordant, crisis-family predictions should stop losing so easily to generic honors/life families
   - this is the first layer to correct

2. **Then fix predictor dominant-timestamp choice within matched crisis groups**
   - if the same danger family recurs across the window, dominant timestamp selection should favor the tighter trigger band, not merely the earliest strongest support total

3. **Then rerun the documented hindcast suite**
   - especially:
     - `transits_documented_hindcast_drowning_1615`
     - `transits_documented_hindcast_doctorate_1613`
   - to ensure the crisis correction does not damage the honors case

## Decision

For the current benchmark miss:

- `timing-window aggregation drift` is real
- but it is **not the main cause**
- the main cause is **row-level event-family ranking that is too permissive toward unrelated benefic/non-crisis families in a documented danger window**

## Resolution Note

This review is now resolved in runtime terms.

Implemented corrections:

1. crisis-family rows now receive full primary-area alignment where doctrine already supports `danger` / `death` as the primary area
2. crisis testimony with malefic-to-angle / directional focus now gets a narrow ranking bonus
3. predictor dominant timestamp selection now uses a representative strongest-band occurrence instead of defaulting to the earliest tied maximum

Observed rerun result:

- `transits_documented_hindcast_drowning_1615`
  - pass
  - matched rank `1`
  - dominant timestamp `1615-07-08T12:00:00+00:00`
  - target-window hit `true`
- `transits_documented_hindcast_doctorate_1613`
  - still passes at rank `1`

So the diagnosis in this memo was correct: fixing row-level crisis ranking first, then predictor dominant-window choice, was the right order.
