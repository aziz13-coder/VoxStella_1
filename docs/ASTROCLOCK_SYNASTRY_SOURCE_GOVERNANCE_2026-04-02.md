# AstroClock Synastry Source Governance

Date: 2026-04-02

## Purpose

The synastry MVP no longer relies only on hidden weights inside the engine.

It now uses a rule catalog in:

- `backend/synastry_rule_catalog.json`

That catalog defines:

1. source books
2. category scales
3. rule families
4. source anchors for each rule family

## Current Source Stack

### Davison

Role:

- core doctrine
- relationship promise
- interplanetary cross-aspects
- house interchanges

Main anchors used in the current catalog:

- `Chapter 5 · Triplicities`
- `Chapter 6 · Sun/Moon`
- `Chapter 6 · Moon/Moon`
- `Chapter 6 · Venus/Venus`
- `Chapter 6 · Saturn aspects`
- `Part Two · House Interchanges`

### Arroyo

Role:

- relational temperament
- elemental exchange
- rising-sign dynamics
- Moon, Venus, Mars, and aspect language

Main anchors used in the current catalog:

- `Chapter 6 · The Four Elements, the Twelve Signs, and the Rising Sign`
- `Chapter 7 · The Moon`
- `Chapter 8 · Mars and Venus`
- `Chapter 8 · Venus and Mars in the Elements`
- `Chapter 17 · The Aspects`

### March / McEvers

Role:

- operational chart comparison
- interaspects
- overlays
- practical technique support

Main anchors used in the current catalog:

- `Lesson 4 · Other Houses in Relationships`
- `Lesson 8 · Your Planets in the Other Person's Wheel`
- `Lesson 9 · Interaspects`
- `Lesson 11 · Other Key Factors`

## Governed Rule Families

The current catalog governs these families:

1. luminary resonance and tension
2. Mercury communication harmony and strain
3. Venus/Mars attraction and conflict
4. benefic support pairs
5. Saturn binding vs pressure
6. Mars/Saturn conflict
7. Ascendant contact effects
8. elemental compatibility modifiers
9. house overlays
10. cross-chart receptions

## What Is Still Heuristic

These parts are still product heuristics rather than direct source extraction:

1. the exact display scaling from raw points to 0-100 bars
2. the overall blended compatibility score
3. the choice to collapse many detailed indicators into six user-facing dimensions
4. the cap logic used for reception totals

## Implemented In This Pass

The synastry modal now exposes governed lineage instead of showing only opaque bars.

Implemented:

1. per-dimension evidence items now carry source key, source anchor, and rule-family id
2. supportive and challenging links now surface source anchors and rule-family ids
3. the source stack now shows active source books and catalog/rule-family coverage for the current comparison
4. house overlays now use a more explicit planet-in-house rule catalog instead of only a small generic house block
5. the overall summary now cites the strongest governed supportive and difficult links rather than relying only on generic score-profile text

## Next Governance Step

The next quality pass should:

1. split the rule catalog into smaller rule files by family
2. add more explicit chapter and page references
3. decide whether some current mixed overlay rules should be separated into romance vs conflict variants
4. expand outer-planet overlay handling once we deliberately include Uranus, Neptune, and Pluto in the scored point set
5. review whether empty-house filling logic from March/McEvers should become a governed signal family
