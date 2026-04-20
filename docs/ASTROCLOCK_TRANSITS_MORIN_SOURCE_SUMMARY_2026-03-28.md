# Astro Clock Transits: Morin Source Summary
## 2026-03-28

This note summarizes the Morin transit flow currently most relevant to Astro Clock, using the converted text corpus in `horary_knowledge/desktop_books_text`.

It is not a general summary of all Morin books. It is a practical source note for:
- transit workflow
- transit logic
- determination hierarchy
- timing flow
- keyword vocabulary that can be defended from the source

## Source Basis

Primary transit source:
- `horary_knowledge/desktop_books_text/631069613-Jean-Baptiste-Morin-Astrologia-Gallica-book-24.txt`

Supporting direction and determination source:
- `horary_knowledge/desktop_books_text/toaz.info-jean-baptiste-morin-astrologia-gallica-book-22-directions-1994-transl-pr_c198dcbe1e631c7e9f774ec5e70b435c.txt`

Most important extracted sections used here:
- Book 24:
  - lines `116-151`
  - lines `986-1008`
  - lines `1190-1228`
  - lines `1471-1497`
  - lines `2808-2837`
- Book 22:
  - lines `3491-3504`
  - lines `4196-4224`
  - lines `4281-4306`
  - lines `9305-9335`

## Core Morin Flow

Morin's causal order is explicit.

From Book 24 lines `116-151`:
- minor events can sometimes arise from transits alone
- important events are not judged from transits alone
- the full chain is:
  - nativity
  - primary directions
  - solar and lunar revolutions, plus their directions
  - transits

Morin's analogy in the same section is central:
- nativity = the gun
- directions and revolutions = the shell or charge
- transits = the trigger

So the correct Morin-facing flow is:
1. Determine whether the event exists in the radix.
2. Determine whether a direction opens the period for that event.
3. Determine whether the solar and lunar revolutions conform to that event.
4. Use the transit as the immediate activator that reduces the potential cause into actual manifestation.

Book 24 lines `986-1008` says the same thing more formally:
- directions and revolutions are potential causes
- transits are the ultimate and particular active causes
- the effect becomes active when planets transit concordant places of the radix and the revolution

## Transit Logic

### 1. Determination comes first

Book 24 lines `1190-1228` makes the rule clear:
- transits act according to the transiting planet's own radical signification
- they must be judged through house combinations
- they must be observed by body and by aspect

Morin says the transiting planet must be judged under three heads:
1. its own particular nature
2. its radical determination
3. its celestial state at the time of transit

This means a transit is not judged from aspect geometry alone.

It must be judged from:
- the planet itself
- what that planet signifies in the radix
- the place or point through which it transits
- whether the current celestial state strengthens or weakens its action

### 2. Empty-space transits are weak or imperceptible

Book 24 lines `1471-1497` is one of the clearest practical passages:
- transits through empty places are imperceptible
- transits through radical planets, cusps, and aspect places are perceptible
- they become especially effective when there is a concordant direction and revolution

This is directly relevant to Astro Clock:
- a generic transit through zodiacal space should not be given the same weight as a transit through a radical place
- the strongest transit claims should be tied to a radical point, cusp, aspect, Part of Fortune, or antiscion

### 3. Agreement and contrariety matter

The same Book 24 passage says:
- if the transiting planet and the radical place agree in effect, the effect is produced immediately according to that place
- if their determinations are contrary, damages, impediments, and misfortunes are signified

This is the source basis for:
- concordance scoring
- positive versus adverse weighting
- mixed tone when good and bad significations coexist

### 4. Not every transit counts

Book 24 lines `2808-2837` makes several high-value rules:
- slower planets are more efficacious because they remain longer in place
- the Moon alone is of the least virtue
- the effect of a transit arises from the actual combination of:
  - the transiting planet's radical signification
  - the signification of the place through which it transits
- transits outside the meaningful places of the nativity are of no efficacy for the native

Morin explicitly names the meaningful places:
- 12 cusps
- 7 planets
- Part of Fortune
- aspects
- antiscions

This supports the current Astro Clock design choice to treat:
- natal points
- cusps
- aspects
- antiscions
- lots / Fortune
as the meaningful transit targets

### 5. House system accuracy matters

Book 24 repeatedly warns that transit work depends on the true places of the figure.

Operational consequence:
- incorrect house placement corrupts determination
- transit logic that relies on the wrong house system or wrong location context will drift away from the source

This supports the repo's emphasis on:
- explicit house-system propagation
- correct location/timezone handling
- not silently mixing natal-place and current-place logic

## Timing Workflow

Book 22 lines `9305-9335` and surrounding lines provide the practical Morin timing workflow:
- directions, revolutions, and transits are one natural and uniform doctrine
- exact times require labor because the astrologer must descend from universal causes to particular ones
- revolutions must be erected for the place where the native is at the time of the revolution
- solar revolutions hold for the year
- lunar revolutions further actuate within the year

This means the timing workflow is:
1. Radical direction opens the year or period.
2. Solar revolution confirms the year and supports the topic.
3. Lunar revolution narrows the month or nearer period.
4. Transit provides the immediate activation day or trigger.

That is the real Morin flow. A transit by itself is not the whole forecast.

## Multiple Effects and Selection Logic

Book 22 lines `4196-4224` is crucial for ranking and keyword selection:
- one direction can signify many effects at once
- it is safer to predict all the effects that can result from the concourse
- but the astrologer must pay attention to the effect most strongly and principally signified
- then look to the revolution to see which signification it favors most
- if several directions occur in the same year:
  - if they agree, the effect is more certain
  - if they disagree, the stronger governs, tempered by the contrary
  - sometimes effects are subordinated in sequence

This passage is the source basis for:
- keeping multiple candidate event families instead of collapsing everything to one
- preferring the strongest principal effect
- allowing mixed or tempered outcomes
- distinguishing a primary signal from secondary signals

For Astro Clock, this means the software should:
- preserve multiple plausible determinations when the source supports them
- avoid overclaiming a single event label too early
- still surface the strongest principal signification first

## House and Event Vocabulary

Book 22 lines `3491-3504` gives the cleanest source-grounded house vocabulary relevant to transit keywords.

### Strong source-grounded families

Book 22 lines `8046-8060` gives a compact full-house list that is useful as a baseline for transit vocabulary:

1st house:
- life
- temperament
- state of health
- moral nature
- mental qualities

2nd house:
- wealth
- gold
- acquired goods or estate

3rd house:
- brothers
- relations or kin

4th house:
- parents
- successions or inheritances

5th house:
- children
- bodily pleasures

6th house:
- servants
- subordinates
- domestic animals

7th house:
- marriage
- open enemies
- lawsuits

8th house:
- death

9th house:
- religion
- journeys

10th house:
- action
- profession
- dignity
- fame

11th house:
- friends

12th house:
- sickness
- imprisonment
- exile
- secret enemies
- hardships

Book 22 lines `3491-3504` expands several of these in a more qualitative way:
- the 7th is not only matrimony but also contracts and lawsuits
- the 12th also carries servitude and, by opposition, servants and domestic animals
- the 1st includes bodily conformation and mental qualities

These are the safest keyword roots for a Morin-facing transit layer.

### What this means for UI keywords

Safe source-facing render families:
- `life/vitality`
- `health`
- `honors/office`
- `undertakings/actions`
- `marriage`
- `contracts`
- `lawsuit/open dispute`
- `open enemies`
- `death`
- `danger to life`
- `imprisonment/exile`
- `secrets/hidden matters`
- `journeys`
- `religion/belief`
- `shared resources/debts` only when actually supported by the modern project taxonomy rather than presented as literal Morin wording

More modern shorthand that can still be acceptable if kept conservative:
- `attack_violence`
- `conflict`
- `public_recognition`
- `honor/distinction`
- `new office/role`

### Keywords that should be handled carefully

The source supports mixed houses, not one-note labels.

Examples:
- 7th house is not automatically marriage
- 12th house is not automatically imprisonment
- 8th house is not automatically death in every case

Therefore:
- `marriage` should require stricter gates than generic 7th-house partnership/contact testimony
- `imprisonment/exile` should require stronger 12th-house adversity than merely hiddenness
- `death` should remain high-bar and strongly determined, not a loose synonym for 8th or hidden material

## Combination Logic

Book 22 lines `4281-4306` adds another important rule:
- the nature of the aspect must agree with the nature and determination of the planet making it
- benefic aspect + benefic planet in a good house -> notable good
- malefic aspect + malefic planet in an evil house -> notable evil
- the promittor's state must be judged not only in the radix but also in the revolution

Morin's example in this section matters for modern render logic:
- Midheaven to trine of the Sun in the 7th may signify:
  - excellent marriage for a woman
  - notable military dignity for a man

That example is useful because it proves:
- the same structural contact can yield different event families
- judgment depends on determination and context, not just on the house alone

For Astro Clock, this argues against overly rigid one-label mapping.

## Practical Guidance for Astro Clock

### What should remain in the algorithm

- radical determination first
- concordance with directions and revolutions
- stronger weight for meaningful natal places
- body and aspect transit handling
- support for cusps, aspects, Fortune, and antiscions
- mixed-signification handling where the source supports it

### What should remain additive, not absolute

- modern event-family chips
- frontend summaries
- predictor grouping
- crisis or marriage shorthand

These are useful as a product layer, but they are not the same thing as Morin's own terminology.

### What wording should remain conservative

- `marriage`
  - use only when the testimony is stronger than generic 7th-house relational contact
- `death`
  - use only on high-bar determinations
- `imprisonment`
  - preferably render as `imprisonment/exile` unless the testimony is narrower
- `war`
  - should usually be rendered through open enemies, conflict, violence, public action, or military dignity logic rather than treated as a literal standalone Morin category

## Short Operational Summary

Morin transit work is not:
- transit cookbook astrology
- aspect-only forecasting
- isolated daily keyword matching

It is:
- a determination-led trigger doctrine
- subordinate to radix, directions, and revolutions
- dependent on meaningful places
- dependent on concordance
- strongest when multiple causes agree

So the clean Astro Clock translation is:
1. determine the event family radically
2. confirm the active period by directions and revolutions
3. use transits as the immediate activator
4. preserve multiple possible effects when the source supports them
5. surface the strongest principal effect first, but not at the cost of losing the secondary conforming signals

## Relation to Existing Repo Audits

This note should be read together with:
- `docs/ASTROCLOCK_TRANSIT_KEYWORD_SOURCE_AUDIT_2026-03-27.md`
- `docs/ASTROCLOCK_PREDICTOR_AUDIT_2026-03-27.md`
- `docs/ASTROCLOCK_TRANSITS_WORKFLOW_AUDIT_2026-03-26.md`
- `docs/ASTROCLOCK_TRANSIT_ALGORITHM_FINDINGS_2026-03-27.md`

Those docs describe implementation findings and fixes.

This note is the higher-level source summary behind them.
