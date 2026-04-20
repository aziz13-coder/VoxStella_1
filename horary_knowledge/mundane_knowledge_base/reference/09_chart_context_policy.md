# Chart Context Policy

Status: first pass

## Purpose

This file turns the current doctrine into an explicit fallback policy for chart selection and chart quality. The sources do not give one universal chart. The product must therefore choose a documented hierarchy instead of pretending the choice is automatic.

## Current Default Hierarchy

### 1. Exact event chart

Use when the public event has:

- a defensible timestamp
- a defensible initiating place
- a defensible initiating actor

Best current examples:

- war outbreak
- declaration
- accession
- assassination
- major parliamentary act with precise timing

Main source:

- Watters, pages 203-205

### 2. National chart

Use when:

- the polity has a defensible national chart
- the question is not reducible to one short public event
- the event chart is unavailable or incomplete

Main sources:

- Green, contents pages 4-7
- Watters, pages 55-56 and 205

### 3. Ruler or head-of-state chart

Use when:

- the national chart is weak, disputed, or missing
- the question is tightly bound to leadership fate
- the doctrine specifically permits ruler fallback

Main source:

- Watters, pages 55-56 and 205

### 4. Capital-based annual framework chart

Use when:

- the question is country-level and annual
- event or national charts are absent or being used only as overlays
- ingress and lunation framework is the primary lens

Main source:

- Green, pages 12-20

## Context Types To Preserve In Data

- `event_chart`
- `national_chart`
- `ruler_chart`
- `capital_chart`
- `regional_chart`

Optional later:

- `mutation_chart`
- `conjunction_master_chart`

## Data Quality Grades

### Grade A

- exact event time
- exact place
- initiating actor known
- chart basis uncontested

### Grade B

- event date known
- time approximate or windowed
- place known
- chart basis mostly stable

### Grade C

- event only periodized
- multiple possible places or initiators
- national chart disputed

### Grade D

- doctrinally interesting but historically loose
- kept for research and benchmark seeding, not public scoring

## Working Rule

If two chart bases disagree:

1. do not silently merge them
2. report the higher-priority chart first
3. treat lower-priority charts as overlays or supporting context

## Immediate Use In Benchmarks

- war cases should prefer `event_chart`
- annual political cases may combine `capital_chart` plus `lunation` or `eclipse`
- long-cycle finance and unrest cases may combine `mutation_chart` plus `national_chart`
