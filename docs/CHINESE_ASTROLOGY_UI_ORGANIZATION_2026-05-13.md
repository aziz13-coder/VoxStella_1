# Chinese Astrology UI Organization

Date: 2026-05-13

## Goal

Reduce the Chinese Astrology surface from an implementation-heavy row of equal-weight buttons into a user-facing reading flow.

The previous lower rail exposed every internal panel as a primary button:

`Chart`, `Reading`, `Day Master`, `Elements`, `Useful`, `Ten Gods`, `Palaces`, `Relationships`, `Stars`, `Timing`, `Oracle`, `Notes`, `Details`

That made advanced, debug, validation, and separate-feature surfaces compete with the main reading actions.

## Implemented Navigation Model

Primary reading rail:

- `Four Pillars`
- `Overview`
- `Element Balance`
- `Life Timing`
- `Relationships`

Specialist analysis menu:

- `Day Master`
- `Ten Gods`
- `Helpful Elements`
- `Life Areas`
- `Auxiliary Stars`

Utility and source surface:

- `Sources & Method` in dev mode only

Separate feature entry:

- `I Ching Oracle`

## Rationale

- The main rail now contains only the sections most users can understand without BaZi terminology overload.
- Specialist BaZi concepts remain available under `More Analysis` instead of being removed.
- `Notes` and `Details` are consolidated into `Sources & Method` because their content is provenance, validation, curation, and backend-method evidence rather than a normal reading destination.
- `Sources & Method` is dev-only. Production builds do not show the button or render the panel, and stale saved `notes`/`debug` preferences fall back to the normal chart view.
- `I Ching Oracle` remains accessible, but no longer reads as another BaZi analysis tab.

## Follow-Up Candidates

- Add short tooltips for `Ten Gods`, `Day Master`, and `Auxiliary Stars`.
- Split `Sources & Method` into collapsible `Sources`, `Validation`, and `Technical Details` blocks if the combined panel grows too dense.
- Consider making `Overview` the default first tab after the reading text is polished enough to replace `Four Pillars` as the landing view.
