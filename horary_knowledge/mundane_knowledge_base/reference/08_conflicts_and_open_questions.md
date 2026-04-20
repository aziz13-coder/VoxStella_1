# Conflicts and Open Questions

Status: first pass

## Overview

The current source set is already good enough to build a serious mundane knowledge base, but it is not yet clean enough to justify scoring-model generation without constraints.

This file records the main unresolved tensions so they stay visible before doctrine becomes code.

## Major Methodological Conflicts

### 1. Ingress duration rules are present but not secure

Green preserves the older rule that:

- fixed Ascendant can make the Aries ingress rule the whole year
- common Ascendant can make it rule six months
- movable Ascendant can make it rule three months

But he immediately says modern evidence is not strong enough to justify close reliance on this rule and that all four cardinal ingresses should still be examined.

Implication:

- do not hard-code this duration rule into a scoring engine yet

Source:

- `horary_knowledge/mundane_books_text/Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt`, pages 13-14

### 2. Eclipse duration doctrine is disputed

Green preserves the old Ptolemaic rule that eclipse duration in hours of obscuration maps to years or months of effect, but he says modern experience does not strongly confirm it and that effects often appear immediately and seldom extend beyond about a year.

Implication:

- keep eclipse duration heuristic as a research note, not a public runtime law

Source:

- Green, pages 18-19

### 3. Country and town sign rulerships are traditional but unstable

Green gives extensive country and town rulership lists, then warns:

- some need further observation
- countries may have subdivisions under different signs
- political and historical change complicates older lists

Watters preserves similar sign-country and sign-city associations, which confirms the tradition but does not resolve the instability.

Implication:

- sign-country and sign-city mappings should remain provenance-tagged reference data, not unquestioned truth

Sources:

- Green, pages 73-88
- Watters, pages 33-44

### 4. There is no single default chart context

The corpus supports multiple valid chart bases:

- capital-town ingress charts
- national horoscopes
- ruler charts
- event charts
- revolution charts

Watters is especially clear that exact event charts outrank generic war horaries, but she still falls back to national or ruler charts when exact event data is missing.

Implication:

- the first product version must choose and document a fallback hierarchy instead of pretending the tradition gives only one answer

Sources:

- Green, pages 12-13 and contents pages 4-7
- Watters, pages 55-56 and 203-205
- Bonatti, pages 35-45

### 5. Traditional vs modern planetary rulership is unresolved

Watters is explicit that in horary she generally prefers traditional sign rulerships, but in mundane work she says the outer planets should be used for Aquarius, Pisces, and Scorpio and that Uranus should be used in judging events and national matters.

This is operationally useful, but it creates a modeling question:

- should the runtime use traditional rulers, modern rulers, or dual-ruler logic depending on chart family?

Implication:

- rulership strategy must be represented as a configurable doctrine choice, at least in research mode

Sources:

- Watters, pages 39-43 and 103-104

### 6. Medieval king-language does not map one-to-one onto modern states

Bonatti's actor hierarchy is valuable, but it is explicitly built around:

- king
- nobles
- rustics
- bishops and clerics

This structure is not unusable, but it must be normalized carefully for modern republics, bureaucratic states, parties, parliaments, and executive systems.

Implication:

- actor normalization must be explicit and documented, not implicit or casual

Source:

- Bonatti, pages 40-45

## Strong Doctrines That Still Need Benchmarking

### 1. Retrograde Mars as a high-confidence public trigger

Watters makes very strong claims:

- treaties fail
- rulers suffer defeats or death in office
- aggressors lose wars started under retrograde Mars

These claims are operationally attractive, but they are still too concentrated in one source and too event-heavy to promote directly without historical case testing.

Source:

- Watters, page 110

### 2. Eclipse-trigger violence doctrine

Watters is explicit that heavy planets or Mars hitting a visible eclipse degree or national sensitive degree can trigger:

- wars
- riots
- death of public men
- assassination
- economic or political shocks

This is one of the strongest doctrines in the set, but it still needs benchmark cases before scoring.

Source:

- Watters, pages 103-104

### 3. Great Mutation charts as master charts

Watters gives very strong master-chart language for Great Mutations. Green gives strong long-cycle language too. But practical runtime use will require carefully defined rules for:

- which chart is the master chart
- how it is progressed
- how it interacts with national charts and annual charts

Sources:

- Green, pages 87-88
- Watters, pages 55-60

## Domains That Need More Books Before Public Promotion

### 1. Weather and rain doctrine

Bonatti's weather material is real and extensive, but it is also technical, local, and structurally different from the war and government material.

It should remain research-gated until it is cross-read with more dedicated mundane-weather sources.

Source:

- Bonatti, pages 11-12 and 238-243

### 2. Earthquakes and natural disasters

Green includes earthquake material, and Watters links eclipses to earthquakes and eruptions, but the present corpus is not yet enough to build a responsible scoring model for natural disaster forecasting.

Sources:

- Green, contents pages 4-5 and page 61
- Watters, page 103

### 3. Fixed stars in catastrophe logic

Watters uses fixed stars in mundane and event work, including disaster and war associations. This material is clearly part of the doctrine, but it is too sharp and too under-corroborated in the current corpus to surface early.

Sources:

- Watters, pages 114-116

## Data Problems Still To Solve

### 1. National charts are often disputed or unavailable

Watters explicitly allows the ruler's chart as fallback when a good national chart is unobtainable.

Implication:

- the data layer must support multiple national-chart candidates and fallback policies

Source:

- Watters, pages 55-56 and 205

### 2. Event timing quality will vary

War and political event charts depend on accurate first-action timestamps and correct attribution of the initiating side. Watters is explicit that mistaken beliefs or propaganda about who acted first will corrupt the chart reading.

Implication:

- benchmark cases need data-quality grading, not just outcome labels

Source:

- Watters, pages 203-204

### 3. Region is not reducible to one point

Bonatti explicitly says local geography and region shape the expression of the chart.

Implication:

- future regional logic may need more than a capital-city point estimate

Source:

- Bonatti, pages 48-49

## Minimum Gates Before Model Generation

Do not generate scoring models until these are complete:

1. source-alignment cases for eclipses, retrogrades, mutations, and war doctrine
2. benchmark cases for war, leadership crisis, civil unrest, and finance
3. explicit policy for national-chart fallback and disputed chart handling
4. explicit policy for traditional vs modern rulership handling
5. explicit policy for whether country-sign lists are public-facing, internal-only, or excluded

## Immediate Research Additions Needed

The current three-book set is enough to scaffold the doctrine, but not enough to close all disputes. Before final runtime generation, the corpus should be extended with:

- a stronger dedicated mundane textbook for nations and states
- a national-chart reference source
- additional modern mundane case material

## Working Rule

If a doctrine is:

- only in one source
- historically strong but operationally vague
- highly catastrophic in implication
- or dependent on disputed chart data

then it should remain in the knowledge base and benchmark layer, not the public scoring runtime.
