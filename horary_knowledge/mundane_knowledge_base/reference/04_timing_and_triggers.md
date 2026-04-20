# Timing and Triggers

Status: first pass

## Overview

The current source set does not use one single timing rule for mundane work. It uses layered timing:

- annual framework charts
- monthly or shorter trigger charts
- amplified eclipse points
- long-cycle conjunctions and mutations
- daily aspects and later transits over already-sensitive degrees

This matters for the future runtime. A mundane layer should not collapse timing into one score timestamp. It should distinguish:

- the background chart that sets the period
- the trigger event that sharpens it
- the activation that makes the latent promise concrete

## Main Timing Layers

### 1. Cardinal ingresses set the yearly framework

Green is the clearest first-pass source here.

- the four cardinal solar ingresses into Aries, Cancer, Libra, and Capricorn form the skeleton outline of the year
- the Aries ingress is often treated as the leading annual map
- the other ingresses still matter and should not be ignored

Green also preserves an older duration rule:

- if a fixed sign rises, the Aries ingress may rule the whole year
- if a common sign rises, it may rule six months
- if a movable sign rises, it may rule three months

But Green immediately weakens this as a practical rule, saying modern evidence is not strong enough to rely on it closely and that all four cardinal maps should still be studied.

Source:

- `horary_knowledge/mundane_books_text/Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt`, pages 12-14

### 2. New moons are shorter-horizon public triggers

Green explicitly ranks New Moons just below the cardinal ingresses.

Key rules:

- the New Moon map is judged like any other mundane map
- it becomes important when the lunation is strongly aspected by planets or when planets are angular in the map
- it should also be read against the currently active quarterly ingress map
- the influence of an ordinary New Moon lasts until the next New Moon, and no longer, unless it is an eclipse

This is one of the clearest timing statements in the current corpus.

Source:

- Green volume, pages 14-16

### 3. Eclipses are amplified lunations and sensitive degree-events

Green and Watters agree strongly that eclipses are not just ordinary lunations.

Green's timing model:

- eclipses are more important because Sun, Moon, and Earth are aligned under greater strain
- their strongest influence is in the districts where they are visible
- total visible eclipses that are also angular produce the most marked effects
- the house they fall in shows which public affairs suffer
- sign-ruled territories are affected next after visibility zones
- benefics angular to the luminaries reduce damage, malefics increase it

Green also preserves but questions an older duration rule from Ptolemy:

- solar eclipse effects allegedly last as many years as the obscuration lasted hours
- lunar eclipse effects allegedly last as many months as the obscuration lasted hours

Green says modern observation has not corroborated this well. In practice he says eclipse effects often show immediately and seldom extend beyond about one year.

Source:

- Green volume, pages 16-20

Watters adds the sharper trigger doctrine:

- eclipses are extremely important in mundane work
- they are linked to sudden outbreaks of violence, wars, riots, death of public men, assassination of national leaders, and abrupt economic or political change
- these events are estimated to occur when heavy planets or Mars make exact squares or conjunctions to the degree of an eclipse that was visible in the nation concerned or that fell on a sensitive degree of the national chart
- she also explicitly says that movements of planets to eclipse points or to angles, and transits over them, may be more accurate than more generic timing methods

Source:

- `horary_knowledge/Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt`, pages 43, 103-104

### 4. Major conjunctions describe long cycles and reversals

All three sources give conjunctions major timing weight.

Green:

- distinguishes ordinary yearly phenomena from longer-cycle conjunctions of the major planets
- says conjunctions should be read partly by the sign in which they fall and the countries ruled by that sign, and partly by a conjunction chart cast for the exact moment
- gives explicit cycle language for great conjunction theory, including Saturn-Jupiter recurrences at about 60 years, the same triplicity for about 240 years, and all four triplicities over about 960 years

Source:

- Green volume, pages 12, 20, 87-88

Watters:

- treats Jupiter-Saturn conjunctions every twenty years as extremely important
- says they reverse trends in mundane affairs and are therefore called Mutations
- says conjunctions in the same element for 240 years are Lesser Mutations
- says a change into a new element is a Great Mutation
- treats the Great Mutation chart as a master chart for long historical cycles

Source:

- Watters, pages 55-60

Bonatti:

- organizes Treatise 4 around conjunction families
- gives explicit doctrinal weight to Saturn-Mars, Saturn-Jupiter, and Sun-Moon conjunctions
- links Sun-Moon conjunctions and oppositions to recurring monthly signification

Source:

- Bonatti, pages 3-4, 19-24, 240-243

### 5. Daily aspects and ordinary transits still matter

Green does not limit mundane timing to ingresses and eclipses.

He explicitly says that daily aspects can be read in two ways:

- as changes occurring inside the currently active quarterly ingress or New Moon map
- as stand-alone effects according to the nature of the aspect itself

This is important because it gives a bridge between the large framework charts and day-level event activation.

Source:

- Green volume, pages 20-21

Watters extends this with slow-planet sign changes:

- sign changes of the heavy planets are of the utmost importance in mundane astrology
- they mark the end of eras of political power, peace or war, ideology, and long economic conditions
- they can change public opinion rapidly and alter the fate of elections and public leaders

Source:

- Watters, pages 112-113

### 6. Retrogradation is used as a live trigger condition

Watters is explicit that retrogradation is not just descriptive background.

Her strongest mundane claims here concern retrograde Mars:

- treaties signed under retrograde Mars are said to be abrogated
- rulers or elected officials coming to power under retrograde Mars have unfortunate administrations
- when a nation starts a war under retrograde Mars, the aggressor is defeated

This is doctrinally strong inside Watters, though it still needs careful benchmark treatment before product use.

Source:

- Watters, page 110

### 7. Bonatti treats revolution timing as divisible and local

Bonatti adds two timing structures that do not appear as clearly in Green or Watters.

First:

- a revolution can be read for a whole year, a half year, or a quarter year
- the house from which the Lord of the Year is taken affects the strength of what is signified in that year, semester, or quarter

Second:

- the accidents of a revolution are not only temporal but regional
- their manifestation depends on the city, region, clime, horizon, and local conditions

Source:

- Bonatti, pages 35-36 and 48-49

## Strong Cross-Source Agreements

The present corpus is already stable on several timing principles:

- mundane timing is layered, not singular
- annual framework charts and shorter trigger charts must be read together
- eclipses create especially sensitive degrees
- later aspects and transits activate earlier charts
- long conjunction cycles describe historical shifts rather than day-scale events

## Product Notes

- The future mundane runtime should separate `framework`, `trigger`, `activation`, and `cycle background`.
- The most defensible first activation logic is:
  - current ingress or revolution context
  - current lunation or eclipse
  - hard hits from Mars, Saturn, Jupiter, Uranus, Neptune, Pluto to sensitive degrees or angles
- Eclipse handling should preserve two distinct location tests:
  - visible in the polity concerned
  - exact contact to a sensitive national degree
- Retrograde doctrine should be benchmarked before it becomes a public scoring rule.

## Open Questions

- Should Bonatti's semester and quarter logic become explicit runtime windows or remain research-only?
- How much of Watters' retrograde doctrine survives validation against historical benchmark cases?
- Should daily aspects be exposed in the product UI, or only used internally as event activators?
