# Mundane Weak Spots Curation Plan

## Goal

Turn the remaining weak areas in the mundane layer into explicit research tracks with clear decisions about:

- when more benchmarks are enough
- when new sources are required first
- when both are required before runtime promotion

This plan assumes the current foundation already exists:

- source corpus
- normalized books and summaries
- doctrine reference docs
- benchmark datasets
- validator and runner

## Working Rule

Weak spots do not all need the same cure.

Use this split:

### Benchmark-first

Use when:

- the doctrine is already explicit in the current corpus
- the weakness is mostly sparse historical coverage

### Source-first

Use when:

- the doctrine is too concentrated in one source
- or the domain is too catastrophic, technical, or disputed for responsible scoring

### Source-plus-benchmark

Use when:

- the doctrine is attractive and operational
- but still too sharp, single-source, or ambiguous to trust without cross-source support and case testing

## Weak Spot Matrix

### 1. Leadership transitions, cabinet falls, and election defeat

Current state:

- doctrine exists in Green
- benchmark coverage is still thin

Primary cure:

- more benchmarks first

Secondary cure:

- one additional source later for corroboration

Why:

- this is not a missing-doctrine problem
- it is a sparse-case problem

Deliverables:

- `backend/benchmarks/mundane/leadership_transition_cases.jsonl`
- 4 to 8 explicit cases from Green / Carter examples and adjacent national-chart material
- at least 2 cases involving cabinet failure, legislative failure, or election defeat

Promotion gate:

- minimum 4 explicit historical cases
- at least 2 different leadership-failure subtypes

### 2. Diplomacy, treaties, and foreign-affairs reversals

Current state:

- doctrine is now present
- benchmark coverage has started but is still shallow

Primary cure:

- more benchmarks first

Secondary cure:

- one additional modern source later if treaty-failure logic remains too narrow

Deliverables:

- expand `backend/benchmarks/mundane/diplomacy_foreign_affairs_cases.jsonl`
- add treaty breakdown, alliance stress, and settlement cases
- add at least one case where diplomacy fails and one where settlement succeeds

Promotion gate:

- minimum 5 diplomacy cases
- at least one settlement case
- at least one treaty or alliance failure case

### 3. Public health and epidemics

Current state:

- doctrine exists in Green and Watters
- historical benchmark coverage is effectively absent
- source depth is weaker than war, government, or finance

Primary cure:

- source-plus-benchmark

Why:

- there is enough doctrine to justify research
- not enough to justify runtime promotion

Deliverables:

- one additional health- or disease-relevant mundane source
- `backend/benchmarks/mundane/public_health_cases.jsonl`
- 3 to 5 historical period or event cases

Promotion gate:

- at least 2 sources in the doctrine layer
- minimum 3 explicit public-health benchmark cases
- no public-health scoring until that minimum is met

### 4. Retrograde Mars

Current state:

- strong doctrine
- concentrated heavily in Watters
- only one lower-confidence historical probe so far

Primary cure:

- source-plus-benchmark

Why:

- this is a high-value trigger
- but too sharp to trust on one-source authority

Deliverables:

- `backend/benchmarks/mundane/retrograde_mars_cases.jsonl`
- 3 to 6 historical probes covering:
  - treaty failure
  - ruler instability
  - failed aggression
- one corroborating source outside Watters before runtime promotion

Promotion gate:

- at least 3 benchmark cases
- at least 2 source witnesses
- any remaining single-source claims stay research-gated

### 5. National-chart candidates

Current state:

- candidate registry now exists
- proving layer does not yet exist
- chart ambiguity remains a data problem, not just a doctrine problem

Primary cure:

- more benchmarks first
- plus one dedicated national-chart reference source

Why:

- candidate charts should be proved against events, not chosen by preference

Deliverables:

- `backend/benchmarks/mundane/national_chart_proving_cases.jsonl`
- benchmark cases that compare candidate charts against:
  - war events
  - leadership crises
  - foreign-affairs reversals
- one dedicated national-chart reference source

Promotion gate:

- every major polity used in runtime must have:
  - one preferred chart or an explicit contested policy
  - benchmark evidence for the choice

### 6. Weather, earthquakes, and fixed-star catastrophe logic

Current state:

- doctrine exists
- source breadth is too weak
- risk of overclaiming is high

Primary cure:

- source-first

Why:

- benchmarking thin or catastrophic doctrine too early would create false confidence

Deliverables:

- additional dedicated sources before any new public benchmark pack
- no runtime model family yet

Promotion gate:

- at least 2 strong sources per subdomain
- only then seed benchmarks

## New Source Priorities

The next external-source additions should be:

1. A stronger modern mundane textbook for nations and states.
   Recommended anchor: *Mundane Astrology* by Michael Baigent, Nicholas Campion, and Charles Harvey. It is described by Michael Baigent as the basic textbook they wrote for this branch, and the Faculty of Astrological Studies lists it as the set text for its world/place astrology module. Sources: [Michael Baigent](https://www.michaelbaigent.com/mundane-astrology), [Faculty of Astrological Studies](https://astrology.org.uk/shop/distance-learning-via-email/module-8-distance-learning/).
2. A dedicated national-chart registry.
   Recommended anchor: *The Book of World Horoscopes* by Nicholas Campion. Sources: [Open Library](https://openlibrary.org/books/OL8728508M/The_Book_of_World_Horoscopes), [Google Books](https://books.google.com/books/about/The_Book_of_World_Horoscopes.html?id=Yzf0NwAACAAJ).
3. Additional modern case material focused on political events, diplomacy, and public crises.
   This can come after the first two source additions are normalized.

## Benchmark Build Order

Use this order.

### Phase 1: Benchmark-first closures

- leadership transitions
- diplomacy / treaty cases
- national-chart proving cases

Reason:

- the current corpus is already good enough to expand these without waiting on new books

### Phase 2: Source additions

- add and normalize the modern mundane textbook
- add and normalize the national-chart reference source

Outputs:

- new raw text files
- normalized book files
- summary docs
- updates to `catalog.json`

### Phase 3: Mixed tracks

- retrograde Mars
- public health

Reason:

- both need more source depth and more benchmark density

### Phase 4: Research-gated domains

- weather
- earthquakes
- fixed-star catastrophe logic

Reason:

- these should stay out of runtime work until the source layer is clearly broader and less speculative

## Required New Files

Minimum planned additions:

- `backend/benchmarks/mundane/leadership_transition_cases.jsonl`
- `backend/benchmarks/mundane/public_health_cases.jsonl`
- `backend/benchmarks/mundane/retrograde_mars_cases.jsonl`
- `backend/benchmarks/mundane/national_chart_proving_cases.jsonl`
- `horary_knowledge/mundane_knowledge_base/reference/14_weak_spot_status_board.md`

Likely supporting docs:

- a source-addition memo for each newly added book
- a proving note for each contested national chart

## Acceptance Gates

A weak spot is considered curated only when all of these are true:

1. the doctrine is summarized in the knowledge base
2. the benchmark dataset exists
3. the runner validates the new dataset with zero citation failures
4. the weak spot has a documented promotion decision:
   - runtime-eligible
   - research-only
   - blocked pending more sources

## Immediate Next Sequence

1. Build `leadership_transition_cases.jsonl`
2. Build `national_chart_proving_cases.jsonl`
3. Add the modern mundane textbook
4. Add the national-chart reference source
5. Build `retrograde_mars_cases.jsonl`
6. Build `public_health_cases.jsonl`
