# Weather Runtime Candidate Families

Status date: 2026-04-12

## Decision

The first runtime-candidate weather family set is:

1. `floods`
2. `hurricanes`
3. `thunderstorms_tornadoes`
4. `wind`

These are the first implemented seed runtime families.

They remain research-gated.

## Why These Four

### Floods

- strong explicit local doctrine in Riske
- additional classical support from Bonatti rain and excess-water logic
- multiple worked historical cases already seeded
- locality logic is clear because flood patterns can be tied to ingress maps, lunar phases, and target regions

### Hurricanes

- explicit modern operational treatment in Riske
- good overlap with locality and track logic
- clear distinction from general rain or flood families
- benchmark cases already cover origin-to-landfall sequence logic

### Thunderstorms / tornadoes

- explicit aspect logic already present in the corpus
- strong locality and target-zone logic
- event shape is clear and fast-moving
- well suited to later scan or map-based experimentation

### Wind

- explicit Mercury/front/wind doctrine in Riske
- multiple worked cases already in the local corpus
- distinct enough from storm, rain, and convective families
- useful as a lower-complexity runtime candidate before attempting broader seasonal families

## Why Not The Others First

### Drought

Viable, but better held slightly later because the line between drought and generalized seasonal pattern still benefits from a cleaner long-window treatment.

### Snow / freezing precipitation

Viable, but it currently overlaps more with broad winter-storm and precipitation logic than the first four families do.

### Temperature extremes

Viable, but the current benchmark shape mixes short-term heat/cold events with broader baseline temperature language.

### Generalized seasonal temperature

Useful as a framework family, not a first runtime family. It is too close to baseline seasonal description rather than a discrete event-pressure family.

## Runtime Mapping

The current proposed benchmark-to-runtime mapping is:

- benchmark `floods` -> runtime `flood_risk`
- benchmark `hurricanes` -> runtime `hurricane_pressure`
- benchmark `thunderstorms_tornadoes` -> runtime `severe_convective_pressure`
- benchmark `wind` -> runtime `wind_event_pressure`

## Intended Runtime Shape

Each future runtime family should expose:

- `framework_layer`
- `trigger_layer`
- `locality_layer`
- `family_assessment`
- `calibration`
- `matched_rules`

It should not expose one flat weather score without layered explanation.

## Gate Reminder

These runtime families are implemented in seed form, but promotion beyond seed status remains gated in:

- `docs/WEATHER_RUNTIME_GATE_2026-04-12.md`
