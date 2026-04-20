# National Charts and Locality

Status: first pass

## Overview

The current source set does not treat mundane locality as one simple latitude/longitude problem. It uses several different locality frames:

- the capital town of the polity
- the standing national horoscope
- the exact site of the public event
- territories linked to zodiacal signs
- climes, regions, and local geography

This is important architecturally. A future mundane layer can reuse the place-handling architecture of astrocartography, but it should not treat place the same way astrocartography does. In mundane work, place is political and event-specific before it is personal.

## Main Locality Frames In The Current Sources

### 1. Capital towns are the default seat of state charts

Green is explicit that the ingress chart for a country is cast for the latitude and longitude of the capital town of the country being studied.

This gives a clear first-pass rule:

- annual state charts are capital-centered unless a different chart family requires a different place

Source:

- `horary_knowledge/mundane_books_text/Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt`, pages 12-13

### 2. Eclipses are strongest where they are visible

Green's eclipse doctrine is strongly locality-bound.

He says:

- the greatest influence of an eclipse is in the districts where it is visible
- total visible eclipses that are also angular produce marked effects
- next in importance after visibility zones are the places ruled by the sign in which the eclipse falls

Watters makes a closely related claim:

- eclipse-trigger events are estimated when heavy planets or Mars hit the degree of an eclipse visible in the nation concerned or a sensitive degree in the national chart

This is a strong cross-source agreement that mundane locality is not abstract. Visibility and territorial relevance matter.

Sources:

- Green volume, pages 17-18
- Watters, pages 103-104

### 3. National horoscopes are standing context charts

The Green / Raphael / Carter collection plainly treats national horoscopes as a legitimate mundane class:

- horoscopes for foreign countries
- horoscopes of nations
- the New Year figure
- special national and political horoscopes

Source:

- Green volume, contents pages 4-7

Watters gives the clearest operational rule for when to use them:

- if an exact war event chart is unavailable, use the national horoscope or the ruler's chart
- keep track of transits, eclipses, and solar arc progressions over it
- compare the same for the enemy or counterpart nation when possible

Source:

- Watters, pages 55-56 and 205

### 4. Event locality can override standing locality

Watters is explicit that war charts must be cast for the actual time and place where hostilities begin.

She also says:

- if different nations declare war at different times and in different capitals, separate charts can be set up for each event
- each chart then shows the course and outcome of the war for the nation concerned

This is a strong argument that the product should not reduce everything to one national chart per country. Event-place charts remain first-class.

Source:

- Watters, pages 203-205

### 5. Country and town rulership lists are part of the tradition

Green gives extended lists of:

- countries ruled by zodiac signs
- towns ruled by zodiac signs

He then adds an important caution:

- some rulerships are well corroborated
- others need further observation
- countries may have a primary sign but still contain important subdivisions under other signs
- long political and historical changes may complicate old rulership lists

This is one of the most important methodological cautions in the current corpus.

Sources:

- Green volume, pages 73-88

Watters also preserves sign-to-country and sign-to-city correspondences in her sign descriptions, which confirms that this layer belongs to the tradition even if the lists are historically dated.

Source:

- Watters, pages 33-44

### 6. Bonatti treats regions and climes as chart-sensitive

Bonatti adds a more granular regional logic than Green or Watters.

He says the astrologer should judge the revolution using:

- the Ascendant of the city or region in question
- the relevant clime and horizon
- the directions and extent over which the signification spreads
- the actual terrain, such as mountains, valleys, lakes, swamps, and similar site conditions

In other words, locality is not just a point on a map. Local geography modifies the expression of the chart.

Source:

- Bonatti, pages 48-49

## What Counts As The "Place" Of A Mundane Reading

Based on the current source set, there is no single universal answer. The correct place depends on chart class.

### For annual state charts

- use the capital town

### For standing context charts

- use the national horoscope if a defensible one exists

### For war and public event charts

- use the exact event site and time

### For eclipses

- test visibility in the polity concerned
- then test sign-ruled territories and national sensitive degrees

### For regional or environmental work

- consider region, clime, and terrain, not only the central city

## Product Notes

- The future mundane layer should store different chart contexts rather than one generic `location`.
- The minimum defensible context types are:
  - `capital_chart`
  - `national_chart`
  - `event_chart`
  - `regional_chart`
- Country-sign and city-sign rulerships should be treated as reference data with provenance, not as unquestioned scoring truth.
- The astrocartography architecture can be reused for:
  - location search
  - atlas storage
  - chart-context switching
  - source-backed doctrine assets

But the scoring semantics must change:

- astrocartography asks where a person thrives
- mundane asks what happens to a polity, territory, or public event at a place

## Recommended Default Order Of Fallback

If exact context is unavailable, the current source set supports this provisional order:

1. exact event chart for the public event
2. national chart for the polity concerned
3. ruler or head-of-state chart when the national chart is weak or unavailable
4. capital-based annual framework chart

## Open Questions

- For the first product version, should the default state context be the capital chart or a curated national chart?
- How should disputed or multiple national charts be represented in the data model?
- Should sign-country and sign-city rulership lists be exposed in the UI, or kept as research support only?
