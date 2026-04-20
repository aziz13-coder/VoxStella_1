# Core Concepts

Status: first pass

## Working Definition

Mundane astrology, in the current source set, is the branch of astrology that judges collective and political conditions through celestial events rather than through the nativity of a single individual.

The strongest plain-language definition in the current corpus comes from H.S. Green:

- mundane or national astrology studies the effects of equinoxes, solstices, new moons, eclipses, conjunctions, and similar celestial phenomena upon countries, nations, districts, and peoples
- it is explicitly framed as astrology of nations and states, not of separate persons

Source:

- `horary_knowledge/mundane_books_text/Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt`, pages 9-13

Barbara Watters gives the clearest bridge-definition:

- astrology was first used to predict the fate of kings and nations
- this branch is now called mundane
- mundane astrology keeps horary techniques, but shifts the frame from the individual to a celestial event

Source:

- `horary_knowledge/Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt`, pages 10-11

Bonatti confirms the older doctrinal frame by organizing the subject around:

- conjunctions
- mundane revolutions
- the Lord of the Year
- the significator of the king
- the condition of the common people

Source:

- `horary_knowledge/mundane_books_text/Bonatti_on_Mundane_Astrology_Guido_Bonattis_Book_of_Astronomy_Treatise_4_8.1_10_Conjunctions_Revolutions_Weat_fdd3953fa4.txt`, pages 5-9

## Core Agreements Across Sources

### 1. Mundane astrology is collective, not personal

All three sources place the subject at the level of:

- nations
- rulers and governments
- peoples or masses
- public events such as war, harvests, peace, political change, and disaster

This is the main boundary line between mundane work and natal work.

### 2. Mundane astrology is event-anchored

The sources do not begin from the birth of a single person. They begin from chartable events and cycles:

- solar ingresses
- new moons and lunations
- eclipses
- planetary conjunctions
- annual revolutions
- war outbreaks
- weather and other collective conditions

This matters product-wise: a future mundane layer should not be a renamed natal scorecard. It should be driven by event families and cycle charts.

### 3. Mundane astrology is political and civil, not merely symbolic

The source set treats mundane judgment as practical judgment about public life:

- victory or defeat in war
- strength or weakness of government
- public order or unrest
- finance, revenue, and trade
- relations with foreign powers
- public health, famine, and disaster

This is not generic “world energy.” The texts are concrete about institutions and outcomes.

### 4. Horary-style judgment remains relevant

Watters is explicit that mundane work often uses horary methods at larger scale:

- the same significators may be transferred from a personal question to a national one
- the same discipline of objective judgment is required
- the shift is in frame and scale, not in the complete abandonment of horary logic

This is an important architectural implication for Vox Stella because the existing horary/event logic in the codebase is not irrelevant to mundane work.

## Important Differences Inside the Corpus

### Green / Raphael / Carter

This volume is the strongest survey text in the current set for:

- public domains
- houses
- nations and states
- eclipses
- political framing
- national and governmental bodies

It is the best first-pass operational source.

### Watters

Watters is strongest where mundane work overlaps with:

- horary judgment
- event charts
- war charts
- eclipse activation
- public leaders and national actors

It is a bridge source rather than a self-contained national-astrology manual.

### Bonatti

Bonatti is the strongest traditional doctrinal source in the current set for:

- conjunction cycles
- yearly revolutions
- Lord of the Year logic
- king / allies / common people framing
- war and weather chapters

Its language is older and less directly product-ready, but it is the deepest formal structure in the current corpus.

## Operational Distinctions To Preserve

### Mundane is not natal

The source set does not support reducing mundane work to “use a national chart the way you use a birth chart” as a default simplification. National charts exist in the corpus, but they are not the only or even primary basis of judgment.

### Mundane is not astrocartography

Astrocartography is about place-selection and relocation meaning. Mundane astrology is about nations, governments, peoples, cycles, crises, and public conditions. The existing astrocartography architecture can be reused, but its semantics cannot be reused directly.

### Mundane is not only political

Although politics is central, the source set also treats:

- crops
- weather
- earthquakes
- public health
- mortality
- shipping
- trade
- religion

as legitimate mundane domains.

## Product Notes

- A future mundane layer should be modeled around chart classes and public domains, not around personal life goals.
- National charts, ingress charts, eclipse charts, and war/event charts should remain distinct entities in the design.
- The most defensible first models are likely domain lenses such as government stability, conflict pressure, public mood, finance, diplomacy, and public health rather than one generic “mundane score.”

## Next Reading

1. `02_chart_types.md`
2. `03_significations.md`
