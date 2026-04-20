# Merged Doctrine Summary

Status: first pass

## What The Current Corpus Already Supports

The current three-source corpus is already strong enough to support:

- a serious mundane knowledge base
- benchmark seeding for doctrine and historical cases
- a future mundane analysis namespace
- domain-lens design for war, government, unrest, finance, and diplomacy

It is not yet clean enough to justify automatic scoring-model generation without research gates.

## Strong Cross-Source Agreements

### 1. Mundane work is chart-class first

All three sources assume the astrologer chooses the right chart family before interpretation:

- Green: ingresses, lunations, eclipses, national charts
- Bonatti: conjunctions, revolutions, weather, yearly structures
- Watters: event charts, war charts, national charts, ruler-chart fallback

### 2. Public domains are more defensible than one universal score

The clearest current model families are:

- `war_conflict`
- `government_stability`
- `civil_unrest`
- `finance_economy`
- `diplomacy_foreign_affairs`

These are repeatedly supported across Green and Watters, with Bonatti reinforcing the formal structure behind war and public order.

### 3. Locality is real, but not simple

The sources converge on a layered locality doctrine:

- capital town for annual state charts
- event site for timed public events
- national chart when defensible
- region/clime/terrain as modifiers
- eclipse visibility as a major locality gate

### 4. Timing is layered

The current corpus supports a multi-layer timing model:

- framework charts: ingress, revolution, mutation
- trigger charts: lunation, eclipse, accession, outbreak
- activation hits: Mars or heavy planets to sensitive degrees or angles

## Main Disagreements Or Research Gates

### 1. Old duration rules are not secure

Green preserves older rules for:

- ingress duration by Ascendant quality
- eclipse duration by obscuration

but does not recommend heavy reliance on them.

### 2. National and country-sign data are unstable

Country and town rulership lists belong to the doctrine, but they are not stable enough to act as unquestioned runtime truth.

### 3. Strong trigger claims need benchmarking

The biggest cases are:

- retrograde Mars
- eclipse-degree activation
- mutation-chart periodization

These should stay benchmark-backed and citation-backed before any public scoring language is attached to them.

### 4. Weather and catastrophe material remains research-gated

Bonatti and Green both support weather work, and Green plus Watters touch earthquakes and disasters, but the current corpus is not yet broad enough for responsible production use.

## Immediate Product Implications

- Build a sibling mundane feature, not an astrocartography goal variant.
- Make chart type and context type explicit inputs.
- Keep source tags and research gating in outputs.
- Use benchmark coverage as a release gate for any future runtime model.

## Immediate Research Priorities

1. Add more explicit historical cases for diplomacy, public health, and leadership transition.
2. Add a national-chart reference source before country-level scoring is attempted.
3. Add a dedicated modern mundane source before promoting catastrophic doctrines.
