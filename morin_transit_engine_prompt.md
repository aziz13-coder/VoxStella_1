# Morin Transiting Engine Implementation Spec

## Core Architecture

Build a 4-tier hierarchical prediction system:

```
Natal Chart (potential)
    ↓
Primary Directions (activation timing by year)
    ↓
Solar/Lunar Revolutions (monthly/daily refinement)
    ↓
Transits (trigger mechanism - actual event timing)
```

## Data Models

### NatalChart
- Planets with: longitude, latitude, dignity state, house position
- Houses: cusp degrees (Regiomontanus)
- Aspects: exact degree separations
- **Determinations**: Each planet's signification map
  - Natural: inherent meaning (Sun=honors, Saturn=illness)
  - Accidental: house rulership + house position
  - Store as: `{planet: {signifies: ['life', 'honors'], strengthFor: ['MC'], weakensFor: ['ASC']}}`

### Direction
- Significator (moving point)
- Promissor (receiving point)
- Arc (degrees of separation)
- Year of completion
- Signification (what it promises: honors/illness/death/travel)

### Revolution (Solar/Lunar)
- Chart for Sun/Moon return to natal position
- Valid for: 1 year (Solar) / 27.3 days (Lunar)
- Must recalculate for Native's current location
- Contains own directions to natal + revolution points

### Transit
- Planet position at specific datetime
- Through: natal point, revolution point, or direction degree
- Orb: Moon=±6hrs, others=±1 day
- State: dignity, aspects at transit time

## Core Algorithms

### 1. Determination Engine
```
For each planet in natal chart:
  - Compute natural rulership (Mars=aggression, Venus=relationships)
  - Compute accidental determination:
    * If planet in house N → signifies house N matters
    * If planet rules house M → signifies house M matters
  - Store weighted determination map
```

### 2. Direction Calculator
```
Input: natal_chart, target_year
Process:
  - For each significator (ASC, MC, planets):
    * Calculate arc to each promissor using Regiomontanus primary directions
    * Convert arc to time: 1° = 1.014583 days in solar revolution
    * Store: {significator, promissor, arc, year, signification}
  - Filter directions completing in target_year
Output: List[Direction]
```

### 3. Revolution Generator
```
Solar Revolution:
  - Find datetime when Sun returns to natal longitude
  - Erect chart for Native's current location
  - Calculate directions within revolution (360° = 365.25 days)
  
Lunar Revolution:
  - Find datetime when Moon returns to natal longitude  
  - Erect chart for Native's current location
  - Calculate directions (360° = 27.325 days)
  - Must be within ±2° latitude of natal Moon
```

### 4. Concordance Scorer
```
For each {direction, revolution, transit} triple:
  Score concordance based on:
  
  1. Signification Match (0-100 points)
     - Direction promises "honors" + Transit through MC ruler = 100
     - Direction promises "illness" + Transit through 12H ruler = 100
     - Mismatch = 0
  
  2. Planetary State (0-50 points)
     - Transiting planet in dignity = +25
     - Well-aspected at transit time = +25
     - Debilitated or afflicted = -25
  
  3. Determination Alignment (0-50 points)
     - Planet determined to signified matter in natal = +30
     - Planet determined in revolution = +20
  
  4. Timing Precision (0-30 points)
     - All three agree within 1 day = 30
     - Within 3 days = 20
     - Within 7 days = 10
  
  Threshold: Score ≥ 150 = probable event
```

### 5. Event Predictor
```
Input: natal_chart, start_date, end_date, native_location
Process:
  1. Generate all directions for date range
  2. For each direction:
     a. Calculate solar revolution for that year
     b. Generate revolution directions
     c. Find transits through:
        - Natal direction degree
        - Revolution promissors
        - Critical natal points (ASC, MC, planetary rulers)
     d. For promising days (concordant transits):
        - Calculate lunar revolution
        - Check lunar revolution directions
        - Compute final concordance score
  3. Rank predictions by concordance score
Output: List[{date, time, event_type, probability_score, details}]
```

## Critical Rules (from Chapter 13)

Implement these as validation/weighting factors:

1. **Determination Priority**: Planet acts per natal determination. Saturn determined to honors in natal → confers honors even if malefic.

2. **Multiple Transit Power**: Two planets of similar signification transiting same point simultaneously → double magnitude. Conjunction > aspects.

3. **Partile vs Platic**: Exact aspects (partile) weighted 3x over applying/separating (platic).

4. **Light Coupling**: Sun/Moon aspecting transiting planet → +50% strength even if alien to signification.

5. **Cluster Transits**: When transiting through stellium, each planet in cluster activates sequentially.

6. **Revolution State**: Check transiting planet's position in revolution chart. If in 8H/12H of revolution + transiting natal ASC → danger.

7. **Syzygy Power**: Conjunction of malefics at direction degree during New/Full Moon → strong activation.

## Output Format

```json
{
  "predictions": [
    {
      "date": "2025-03-15T14:30:00Z",
      "event_type": "HONOR_ELEVATION",
      "probability": 0.89,
      "description": "Major career advancement",
      "factors": {
        "direction": "Jupiter → MC (24°)",
        "solar_revolution": "Sun → natal Jupiter",
        "lunar_revolution": "Moon → MC",
        "transit": "Jupiter partile MC, well-dignified",
        "concordance_score": 185
      }
    }
  ]
}
```

## Performance Optimizations

1. **Precompute**: Store natal determinations, never recalculate
2. **Transit Index**: Hash table of transit times by degree for O(1) lookup
3. **Direction Cache**: Store arc calculations, reuse across revolutions
4. **Batch Revolution**: Calculate 12 lunar revolutions per solar year in single pass
5. **Prune Early**: Discard low-concordance combinations before full calculation

## Implementation Priority

1. ✓ Natal chart + determination engine
2. ✓ Primary direction calculator
3. ✓ Transit calculator with orbs
4. ✓ Concordance scoring
5. ✓ Solar revolution + directions
6. ✓ Lunar revolution + directions  
7. ✓ Integrated predictor
8. ✓ Validation against Morin's examples (Book 23-24)

## Edge Cases

- Native traveling: Recalculate revolutions for current location if >125 miles from natal place
- Retrograde transits: Count each pass (3x if station occurs)
- Latitude consideration: Match natal planet latitude when checking transits
- Term rulers: Ignore (Morin explicitly rejects)
- Progressions: Skip entirely (Morin calls "figments")
