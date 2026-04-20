# Chart Types

Status: first pass

## Overview

The current source set does not treat mundane astrology as a single chart method. It treats it as a family of chart classes and timing structures.

The practical conclusion is simple:

- the future mundane feature should classify charts by type first
- only after that should it score domains or outcomes

## Main Chart Families In The Current Sources

### 1. Solar ingresses

Green treats solar ingresses as one of the primary yearly phenomena. The four cardinal ingresses into Aries, Cancer, Libra, and Capricorn are the most important, and the Aries ingress is often treated as the leading annual framework chart.

Important details from Green:

- the ingress chart is cast for the capital town of the country being studied
- the four cardinal ingresses form a skeleton outline of the year
- the Aries ingress is often treated as the main annual map

Source:

- `horary_knowledge/mundane_books_text/Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt`, pages 10-13

### 2. New moons and lunations

Green includes new moons as a major yearly phenomenon, and Watters also includes lunations among the celestial events selected for mundane work.

Source:

- Green volume, pages 10-13 and contents pages 4-5
- Watters, pages 10-11

Practical reading:

- lunations look like shorter-horizon public-event triggers relative to the larger annual framework

### 3. Eclipses

Eclipses are central in every major source currently in hand.

Green:

- gives them as a primary subject of the manual
- treats both solar and lunar eclipses as major interpretive classes

Watters:

- says eclipses are extremely important in horary and mundane work
- links them to violence, wars, riots, assassination of public leaders, and sudden economic or political change
- emphasizes eclipses visible in the nation concerned or falling on a sensitive national degree

Bonatti:

- explicitly includes eclipse chapters inside the revolution material

Sources:

- Green volume, pages 4-5, 10-13, and eclipse chapter references on pages 180-189 in the contents
- Watters, pages 103-104
- Bonatti, pages 8-9

### 4. Planetary conjunctions

This is one of the strongest doctrinal families in the current corpus.

Green:

- treats planetary conjunctions as one of the major phenomena of mundane work
- includes a chapter specifically on conjunctions

Watters:

- treats Jupiter-Saturn conjunctions as extremely important because they indicate reversals of trend and long-cycle mutations in world affairs

Bonatti:

- organizes Treatise 4 around conjunctions
- gives special weight to Saturn-Mars and Saturn-Jupiter conjunctions
- treats conjunction cycles as world-changing, not merely descriptive

Sources:

- Green volume, pages 10-13
- Watters, pages 57-60
- Bonatti, pages 5, 19-24

### 5. Mundane revolutions / annual year charts

Bonatti makes this a formal chart family.

Key structures in the current Bonatti material:

- revolution of the year
- Lord of the Year
- significator of the king
- significator of the common people
- condition of allies, nobles, rustics, and other social bodies
- war and peace judgment inside the revolution logic

Source:

- `horary_knowledge/mundane_books_text/Bonatti_on_Mundane_Astrology_Guido_Bonattis_Book_of_Astronomy_Treatise_4_8.1_10_Conjunctions_Revolutions_Weat_fdd3953fa4.txt`, pages 5-9 and 31-32

Practical reading:

- Bonatti gives the clearest evidence that annual mundane judgment is not only ingress-based; it also depends on a revolution framework with hierarchy among rulers and significators

### 6. War charts and outbreak charts

Watters is clearest here.

She states that in mundane work the governing chart for a war is the chart for the moment hostilities actually begin:

- first overt military act
- invasion
- first firing
- first bombing

She then assigns the first house to the aggressor and the seventh to the defending nation.

Source:

- `horary_knowledge/Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt`, pages 217-218

Practical reading:

- this is a distinct event-chart class and should not be collapsed into ingress or national-chart logic

### 7. National horoscopes and political nativities

The Green / Raphael / Carter volume includes:

- horoscopes for foreign countries
- horoscopes of nations
- nativities of important persons
- special horoscopes
- the New Year figure

Watters also allows the ruler’s chart as a fallback when a correct national chart is unavailable.

Sources:

- Green volume, contents pages 4-7
- Watters, pages 55-56

Practical reading:

- national charts belong in the future layer, but as one chart family among several

### 8. Weather charts

This is an explicit part of the current traditional corpus.

Bonatti’s current source volume includes:

- Treatise 10: Heavy Rains

Green also connects mundane work to earthquakes and seasonal/weather effects.

Sources:

- Bonatti, pages 11-12
- Green volume, contents pages 4-5

Practical reading:

- weather should be treated as a legitimate mundane subdomain, even if it is not part of the first product surface

## Provisional Hierarchy For Product Design

Based on the current source set, the most defensible ordering is:

### Long-cycle charts

- great conjunctions
- Jupiter-Saturn cycles
- other major conjunction families

### Annual framework charts

- Aries ingress
- other cardinal ingresses
- yearly revolution structures

### Shorter-horizon trigger charts

- new moons
- lunations
- eclipses

### Event charts

- war outbreak charts
- political inceptionals
- other national events

### Standing charts

- national horoscopes
- ruler or leader charts when the tradition explicitly permits fallback

## Product Notes

- The future mundane toggle should probably start with chart-type selection, not a single default chart.
- If only one chart family is exposed in an MVP, the best candidates are `Aries ingress`, `eclipse`, and `war/event chart`.
- Weather and earthquake logic should stay research-gated until the source summaries are more fully distilled.

## Open Questions

- How strongly should Bonatti-style revolution logic be merged with Green-style ingress logic versus kept as separate analysis modes?
- Should national horoscopes be optional context or a first-class chart type?
- Which chart families deserve public UI exposure in v1 versus research-only support?
