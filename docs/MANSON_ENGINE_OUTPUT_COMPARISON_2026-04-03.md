# Manson Engine Output Comparison

## Scope

This note advances the earlier candidate-spec work by doing three things:

1. recover the strongest timing windows available from source material,
2. run exploratory forensic engine probes inside those windows,
3. compare engine output to hard real-life outcomes rather than documentary speculation.

The underlying candidate fixture is:

- `tests/fixtures/forensic_external_manson_case_candidates.json`

## Source Windows Recovered

### Tate / Cielo Drive

Recovered from the Tate progress report:

- witness shots between `00:30` and `01:00` on August 9, 1969
- witness screams between `01:00` and `01:30`
- later shot/radio reports around `04:00` to `04:11`

This is enough for exploratory probing, but not enough for replay promotion because the homicide window is still too broad and internally ambiguous.

### LaBianca

Recovered from the December 8, 1969 grand-jury transcript:

- the LaBiancas were near home at about `01:00` on August 10, 1969
- Frank Struthers returned at about `10:30` that morning and they had already been killed

This gives a broad overnight death window. It is still too wide for promotion, but it is stronger than the Tate timing in one important way: the engine produced one clean directional match inside that interval.

### Gary Hinman

Recovered from reporting and historical summaries:

- multi-day captivity ending on July 27, 1969
- stable case-date and scene facts
- no narrow final-assault timestamp from the sources used in this pass

That means Hinman remains exploratory only. Any intraday anchor is a synthetic probe, not replay truth.

## Engine vs Real-Life Outcomes

### Tate / Cielo Drive

Real-life hard outcomes:

- multi-offender homicide
- blood writing on the door
- public-profile victim cluster
- not a domestic or family homicide
- not a child-victim case

Engine result:

- the engine only begins to emit clear violence markers around the later anchors
- across all tested anchors it repeatedly overfires:
  - `family_involvement`
  - `child_victim`
  - effectively domestic-home logic through family-axis findings
- the later anchors also introduce extra axes that do not belong in the core truth layer:
  - `abduction_missing_person`
  - `water_disappearance_or_drowning`
  - `accomplice_or_witness`

Bottom line:

- Tate is a stable **misread** right now, not just a bad-anchor problem.
- The strongest issue is persistent family/child contamination on a non-family multi-victim homicide scene.

### LaBianca

Real-life hard outcomes:

- double homicide
- linked second scene after Cielo Drive
- blood writing/staging
- not a child-victim case
- not a family-involvement case in the engine's intended sense
- not a domestic-partner case just because the victims were married

Engine result:

- early-window anchors still overfire family/domestic logic
- one exploratory midpoint anchor at `06:00` produced the cleanest output:
  - `Violence`
  - `Deception`
  - no contradictory domestic, family, child, or accident axes
- later-window anchors drift again, including:
  - `abduction_missing_person`
  - `child_victim`

Bottom line:

- LaBianca is the strongest future replay candidate.
- But the aligned `06:00` result is not enough for promotion because `06:00` is still an inferred midpoint inside a wide window, not a sourced event time.

### Gary Hinman

Real-life hard outcomes:

- homicide
- known-associate victim
- false-flag blood writing
- deception/staging relevance
- not a public-authority case
- not an accident/disaster

Engine result:

- the engine is unstable across exploratory intraday anchors:
  - `00:00` misses homicide and falsely emits `Disaster`
  - `06:00` catches associate logic but falsely emits `Public`
  - `12:00` catches homicide but still falsely emits `Public`
  - later anchors can miss homicide altogether

Bottom line:

- Hinman is not replay-safe.
- Right now the output changes too much with arbitrary time placement, which means the missing anchor is materially blocking valid comparison.

## Summary Table

| Case | Best exploratory anchor in this pass | Comparison status | Main engine problem |
| --- | --- | --- | --- |
| Tate / Cielo Drive | `1969-08-09 01:15` or `04:10` | Misaligned | Stable family/child contamination, plus late-window abduction/water noise |
| LaBianca | `1969-08-10 06:00` | Directionally aligned but not promotable | Needs tighter source timing before trusting the aligned midpoint |
| Gary Hinman | none | Misaligned across sweep | Anchor-sensitive output, with public/disaster contamination |

## Current Promotion Decision

No new Manson case is promoted into an external replay slice in this pass.

Reason:

- Tate: stable misalignment
- LaBianca: promising but still too broad a time window
- Hinman: insufficient timing support and unstable output

## What This Says About The Engine

The comparison points to three practical engine risks:

1. **Family/child overfire on interior homicide scenes**
- Tate and early LaBianca anchors repeatedly trigger family/child logic even when the real-world event is not a family-case pattern.

2. **Late-window drift into unrelated axes**
- Tate and LaBianca can pick up abduction, water, or witness pressure in ways that are not core to the historical scene truth.

3. **Public-case contamination**
- Hinman, which should be a cleaner associate-plus-deception case, drifts into public/authority logic on some anchors.

## Recommended Next Steps

1. Recover tighter case-file-grade timing for LaBianca first.
2. If a narrower LaBianca window still supports the current early-morning alignment, promote it first.
3. Use Tate as the next engine-correction benchmark for family/child false-positive suppression.
4. Do not promote Hinman until a real final-assault window is recovered.
