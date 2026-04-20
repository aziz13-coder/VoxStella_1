# AstroClock Synastry Implementation Plan

Date: 2026-04-02

## Product Direction

The synastry MVP should follow the existing AstroClock feature pattern, but with a stricter input model:

1. chart A is a saved snap
2. chart B is a saved snap
3. the user compares two already-frozen charts
4. the first UI surface should feel closer to Trait Profile than to Transits

This keeps the workflow deterministic and avoids mixing live/realtime context with relationship comparison.

## MVP Workflow

1. User opens AstroClock.
2. User saves two charts as snaps if they are not already saved.
3. User opens a new `Synastry` feature surface.
4. User selects `Snap A` and `Snap B`.
5. Backend resolves both snaps into normalized chart bundles.
6. Backend returns:
   - overall compatibility summary
   - ranked score bars
   - supportive links
   - challenging links
   - light house-overlay evidence
7. Frontend renders the result in a score-bar layout similar to Trait Profile.

## Frontend Plan

### Surface

- Add a dedicated `Synastry` action button in AstroClock beside existing feature actions.
- Open a modal rather than embedding new logic directly into the main AstroClock shell.
- Reuse the same modal shell pattern as `TraitProfileModal`.

### Inputs

- `Snap A` selector
- `Snap B` selector
- `House System` passthrough from AstroClock
- optional defaulting:
  - prefer currently active snap as `Snap A`
  - choose first different snap as `Snap B`

### Output Shape

The first screen should emphasize ranked bars, not raw aspect dumps.

Recommended score blocks:

1. Overall Compatibility
2. Emotional Resonance
3. Communication
4. Attraction / Chemistry
5. Support / Ease
6. Stability / Longevity
7. Friction / Stress

`Friction / Stress` should render as a negative-polarity bar using the same visual language as Trait Profile.

Secondary blocks:

- top supportive links
- top challenging links
- house overlays
- source note showing which corpus supports the feature

## Backend Plan

### Route

Add a new endpoint under the existing AstroClock blueprint:

- `GET /api/astro-clock/synastry`

Initial query contract:

- `snap_a_id`
- `snap_b_id`
- optional `house_system_code`

### Resolution

For each snap:

1. load snap from `SnapStore`
2. read `effective_datetime`
3. read `location`
4. recompute a chart bundle through existing AstroClock helpers

This keeps synastry aligned with the same chart-generation pipeline used elsewhere.

### Engine

Create a dedicated synastry service/module instead of expanding `astro_clock_api.py` with feature logic.

The engine should:

1. normalize chart A and chart B planet rows
2. compute cross-chart aspects
3. compute elemental and sign-based compatibility cues
4. compute light house overlays
5. compute cross-chart receptions where easy to support
6. aggregate those signals into a small number of user-facing dimensions

## Source Governance

The current source stack is enough for MVP:

1. Davison
   - primary doctrine
   - relationship promise
   - structured relationship judgment
2. Arroyo
   - relational language
   - temperament and energy exchange
   - emotional and attraction framing
3. March/McEvers
   - operational synastry techniques
   - chart comparison patterns
   - implementation-oriented lookup support

## Scoring Strategy For MVP

The first implementation should prefer explainable heuristics over opaque global scoring.

Recommended structure:

- compute category raw points from explicit aspect and overlay evidence
- clamp to a stable 0-100 display score
- keep evidence attached to every category
- separate positive categories from the dedicated friction category

This is better than pretending to deliver a final “soulmate score” in version one.

## Phase Order

### Phase 1

- backend route
- backend synastry engine
- frontend modal
- snap selectors
- score bars
- supportive/challenging links

### Phase 2

- richer house overlays
- source citations per rule family
- better category narratives
- export / copy prompt

### Phase 3

- composite / Davison chart follow-on feature
- more formal source catalog and rule provenance

## Implementation Notes

- Snap-only input is not a limitation; it is the intended first product contract.
- Reuse AstroClock chart bundles, not snap dashboards, as the analytic source of truth.
- The snap dashboard remains useful for labels and UI metadata.
- Keep the scoring categories stable now so later source refinements do not force a frontend redesign.
