# Active-Case Shadow Research Template

## Purpose

Use this template for **private research-only shadow analysis** on active cases.

This workflow exists to keep active-case experimentation disciplined.

It is designed to prevent:

- publication drift
- operational overreach
- invented timestamps
- location-claim inflation
- mixing public facts with speculative astrology output

## Allowed Use

This template is for:

- research
- method evaluation
- internal experimentation
- comparing engine output to already public facts

This template is **not** for:

- publication
- real-world search guidance
- perpetrator identification claims
- holding-location claims
- legal or journalistic sourcing

## Preconditions

Before using this template, confirm all of the following:

1. The case is active or unresolved.
2. Public sources identify at least:
- a date
- a place or scene cluster
- a rough event window
3. Public facts are separated from rumor.
4. Any exact timestamp is source-verifiable.

If there is **no** chart-safe exact timestamp:

- do **not** invent one
- use a bounded multi-anchor window instead

## Required Inputs

### 1. Public Fact Envelope

Document only facts that are public and source-backed.

Minimum structure:

- case title
- date
- scene location
- confirmed scene markers
- current outcome status
- known unknowns

### 2. Source Register

For each source, capture:

- `id`
- `url`
- `kind`
- `notes`
- `metadata_strength`

Use stronger source classes first:

- official statements
- court or police records
- wire reporting
- press-freedom groups
- reputable local reporting

Treat commentary, TV relays, and documentary narration as weaker context unless they contain independently verifiable facts.

### 3. Anchor Package

Create either:

- one exact anchor, if publicly verified

or:

- three bounded anchors:
  - earliest plausible
  - midpoint
  - latest plausible

For each anchor, freeze:

- `datetime`
- `location`
- `timezone`
- `house_system_code`
- `latitude`
- `longitude`
- `origin`
- `abduction=1` if testing the abduction map path

## Query Discipline

Use the same route shape for every anchor.

Baseline query fields:

```text
mode=manual
datetime=...
location=...
timezone=...
house_system_code=R
latitude=...
longitude=...
origin=lat,lon
abduction=1
```

If coordinates are approximate:

- say so explicitly
- describe them as a scene proxy or cluster proxy
- do not present them as police-grade pins

## Output Capture

For each anchor, record:

- route status
- `success`
- categories
- top findings
- comparison status
- abduction-map origin source
- abduction-map bearings

Recommended comparison axes:

- `abduction_missing_person`
- `deception_coverup`
- `authority_or_public_case`
- `accomplice_or_witness`

Recommended contradiction axes:

- `family_involvement`
- `child_victim`
- `accident_or_disaster`
- `domestic_partner_involvement`

## Comparison Rules

The comparison must be against **known public facts only**.

Do not compare against:

- rumor
- anonymous theory with no corroboration
- documentary speculation
- later hindsight facts that were not public at the time, unless the exercise is explicitly retrospective

## Interpreting Results

### Best-fit anchor

Select the anchor that:

- captures the core event class
- avoids major contradiction axes
- does not overread fatality or motive beyond the public record

### Underfire

Mark an anchor as underfiring when:

- the core event class is missing
- the reading stays at generic concealment or public noise

### Overread

Mark an anchor as overreading when:

- the output pushes into unsupported homicide certainty
- the output leaks into domestic, family, child, or disaster patterns not supported by public facts

## Abduction Map Rules

The map is useful for:

- origin fidelity
- role-bearing coverage
- spatializing victim / abductor / route / confinement roles

The map is **not** enough to justify:

- a route claim
- a holding-direction claim
- a search corridor
- a predictive location statement

unless there is public-source route evidence to compare against.

### Minimum map checks

Record:

- `origin_source`
- echoed origin coordinates
- role coverage:
  - `H7_ruler`
  - `H3_ruler`
  - `H12_ruler`
  - `Moon`

If public sources do not provide a transport heading:

- mark geometry as `not_scored`

## Required Deliverables

Create both:

1. A human-readable analysis note:

- `docs/<CASE>_PRIVATE_SHADOW_ANALYSIS_<DATE>.md`

2. A machine-readable package:

- `docs/<CASE>_SHADOW_PACKAGE_<DATE>.json`

Optional third artifact when one anchor is clearly superior:

3. A research learnings note:

- `docs/<CASE>_<BEST_ANCHOR>_RESEARCH_LEARNINGS_<DATE>.md`

## Human-Readable Note Structure

Use this section order:

1. Scope
2. Public-Source Fact Envelope
3. What Is Still Not Publicly Secure Enough
4. Anchor Package Used
5. Engine Output vs Known Facts
6. Abduction Map Output vs Known Facts
7. Current Best-Fit Reading
8. Boundaries That Still Matter
9. Conclusion

## Machine Package Structure

Use this section order:

- `generated_at`
- `purpose`
- `status`
- `do_not_use_for`
- `public_facts`
- `case`
- `anchors`
- `overall_assessment`

## Non-Negotiable Guardrails

Always state:

- this is research-only
- this is not operational guidance
- this is not publication-ready
- this does not identify perpetrators
- this does not identify holding location
- this does not prove homicide unless the public record already does

## Recommended Summary Language

Prefer:

- `best-fit anchor`
- `directionally coherent`
- `consistent with known public facts`
- `concealed custody risk`
- `multi-actor structure`
- `setup/deception pattern`
- `not publicly scoreable`

Avoid:

- `proves`
- `reveals who did it`
- `shows where they are`
- `confirmed route`
- `predictive corridor`

## Completion Check

Do not finalize the shadow note until all of these are true:

- public facts are separated from unknowns
- anchor basis is documented
- best-fit anchor is justified
- map limitations are explicit
- all claims are bounded to public facts
- the final note reads like research, not operational advice
