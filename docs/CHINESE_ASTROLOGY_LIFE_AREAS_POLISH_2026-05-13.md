# Chinese Astrology Life Areas Polish - 2026-05-13

## What The Tab Does

The Life Areas tab is the production-facing topic map for BaZi interpretation. It answers: where does the chart evidence land before any final outcome is claimed?

It is not a prediction tab. It combines:

- Five Factor / Ten God topic roles: Companion, Output, Wealth, Influence, Resource.
- Four pillar palace placement: Year, Month, Day, Hour.
- Relationship contacts and auxiliary markers already computed by the backend.
- Timing signals from active Luck, annual, month, day, and hour layers when available.
- Element balance for symbolic body-balance context only.

## Research Boundary

The source-backed boundary is that a life topic can be highlighted, but favorability is not assigned from presence alone. Career, wealth, relationships, family, children, and health claims require Day Master strength, useful-element direction, element condition, palace placement, contacts, and timing activation.

Chinese and local-source anchors used:

- `Ba Zi - The Four Pillars of Destiny`: pillar/palace context, Day Master centrality, Hour/Day/Month/Year life-stage and relationship-depth placement.
- `BaZi - The Destiny Code`: Five Factors as Wealth, Output, Influence, Resource, Companion.
- `BaZi - The Destiny Code Revealed`: career, wealth, relationships, and health are read through Five Factor condition, timing, and contacts.
- Chinese Text Project `San Ming Tong Hui`: Ten God naming is rooted in same-element, generating, and controlling relationships to the Day Master.
- Chinese-language research notes from common palace conventions: Year/Month/Day/Hour as family, public, partner/self, children/private/future contexts.

## Implemented

- Added backend `life_areas` payload with method `bazi_life_areas_v1`.
- Added seven topic cards:
  - Career & Authority
  - Wealth & Assets
  - Relationships & Family
  - Health & Body Balance
  - Learning & Support
  - Peers & Social Field
  - Children & Creative Output
- Each topic now exposes:
  - context state: `timing_active`, `emphasized`, `context_required`, or `quiet`
  - visible/hidden factor counts
  - relationship-contact counts
  - evidence rows for factors, palaces, timing, and element balance
  - production-safe summary and guidance copy
- Replaced the old raw Palace Context UI with a Life Areas UI.
- Removed withheld/unresolved style language from the Life Areas production surface.
- Added curation anchors and tests for backend payload and frontend rendering.

## Product Rule

Life Areas may say:

> Wealth & Assets is mapped through Wealth and the Month/Year palace context.

It must not say:

> This person will be rich.

## Remaining Work

- Add worked examples for each topic family.
- Add stronger Chinese-source anchors for gendered spouse-star conventions.
- Calibrate timing-active topic emphasis against dated examples.
- Add a small source-evidence drawer in dev mode only, not production.
