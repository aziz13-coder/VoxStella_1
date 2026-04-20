# Synastry Frontend Design Agent Brief

Date: 2026-04-18

## Goal

Prepare a frontend-only brief for an external AI design agent so it can propose a stronger design language for the Astro Clock `Synastry` feature.

The target is not a backend redesign and not a change to the comparison logic. The target is a UI and UX redesign that makes `Synastry` feel like a first-class member of the Astro Clock feature family while preserving its distinct role as a report-first comparison surface.

## Scope

Focus on source frontend surfaces:

- `frontend/src/features/astroclock/SynastryModal.jsx`
- `frontend/src/features/astroclock/AstroClock.jsx`

Reference design language from:

- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/TraitProfileModal.jsx`
- `frontend/src/features/astroclock/TransitsModal.jsx`
- `frontend/src/features/astroclock/ElectionModal.jsx`
- `frontend/src/features/astroclock/AstrocartographyModal.jsx`

## Product Context

`Synastry` is launched from the Astro Clock action row as a modal. It is not a live workspace like `Mundane`, `Weather`, or `Astrocartography`.

Its product contract is intentionally narrow:

- chart A is a saved snap
- chart B is a saved snap
- both charts are already frozen
- the feature compares those two saved charts
- Astro Clock pauses realtime while Synastry is open

This means the design should feel related to the Astro Clock family, but it should not imitate the multi-column advanced-workspace shell directly. It is closer to a research report, score dossier, or comparison memo than to a control-heavy console.

## Current Workflow

1. User opens Astro Clock.
2. User saves or already has at least two snaps.
3. User opens `Synastry` from the Astro Clock action row.
4. Modal opens and defaults `Snap A` to the active snap when possible.
5. Modal defaults `Snap B` to the first different saved snap.
6. User can change comparison scope:
   - include modern planets
   - include nodes
   - include Chiron when available
   - orb profile (`tight`, `balanced`, `wide`)
7. Frontend requests `GET /api/astro-clock/synastry`.
8. Result renders as a comparison report.

## Current Frontend Features

### Header and Comparison Controls

Current controls:

- `Snap A` selector
- `Snap B` selector
- close button
- inline refreshing indicator when a report is being recomputed

Current behavior:

- defaults comparison from saved snaps
- prevents same-snap comparison
- refreshes automatically when scope toggles change
- keeps the previous report visible while refresh is in progress

### Scoring Scope Panel

Current controls:

- modern planets on/off
- nodes on/off
- Chiron on/off
- orb profile selector

Current support behavior:

- disables unsupported point layers based on backend capability
- shows capability notice when modern or Chiron layers are unavailable

### Primary Report Surface

Current primary content:

- `Overall Compatibility` featured score card
- bipolar score bar with positive and negative weighting
- raw score and polarity
- source and rule-family chips
- `Relationship Signature` narrative block
- overall score badge
- three summary axes:
  - ease
  - bond
  - growth
- two signal columns:
  - what holds it together
  - what creates strain
- expandable `Why this score` details block

### Secondary Report Surfaces

Current secondary content:

- chart A / chart B comparison cards
- `Scope & Model` block
- pressure and balance metrics
- dimension score cards
  - example intent includes communication, attraction, stability, and friction-like dimensions
- top supportive links list
- top challenging links list
- house overlay columns
  - chart A in chart B
  - chart B in chart A
- source stack / doctrine lineage block

### State Cases

Current modal states:

- fewer than two saved snaps
- same snap chosen twice
- initial loading
- refresh-in-place while preserving prior report
- error before any report is loaded
- inline error while a previous report is still visible
- completed report

## Current UI Character

The current Synastry modal is readable and feature-complete, but it is still visually closer to a first working pass than to a polished Astro Clock signature surface.

Current visual traits:

- white modal shell
- white cards inside white cards
- soft pastel gradients in the signature area
- many rounded rectangles of similar weight
- many chips and micro-labels
- stacked comparison and report cards with little hierarchy shift
- functional but plain selectors in the top bar

Current UX problems:

- the modal header feels utilitarian rather than editorial or premium
- the score controls and the report body feel weakly separated
- the `Overall Compatibility` card and `Relationship Signature` card compete instead of forming one clear hero zone
- source chips, rule chips, and evidence blocks create visual noise quickly
- the lower half becomes a long stack of similar white panels
- the report lacks a stronger reading path from "big picture" to "supporting evidence"
- it does not yet share enough visual DNA with the stronger Astro Clock family surfaces

## Design Problem To Solve

We want a new design language for `Synastry` that:

- clearly belongs to the Astro Clock family
- keeps Synastry as a modal report, not a full advanced workspace
- feels more premium, intentional, and memorable
- improves hierarchy between:
  - comparison setup
  - headline verdict
  - key dimensions
  - supporting evidence
  - doctrine and source provenance
- reduces card fatigue
- keeps expert detail available without making the first read feel crowded
- supports both calm "read this result" use and active "tune the scope and compare again" use

## Reference Design Language To Borrow From

Use these product qualities as reference:

- `Astro Clock`
  - family identity
  - clean action framing
  - confidence and clarity in primary surfaces
- `Trait Profile`
  - report-first reading flow
  - dimension-led interpretation
  - personality of the verdict surface
- `Transits`
  - stronger hierarchy and better module identity
- `Election`
  - denser expert presentation without losing direction
- `Astrocartography`
  - upgraded editorial shell language and more intentional section framing

This does not mean Synastry should copy the advanced-workspace layout. It means Synastry should inherit the same product language while remaining a compact comparison report.

## Synastry-Specific Direction

Important product framing for the design agent:

- this is about relationship comparison, not prediction
- this is not a raw aspect browser
- the first screen should emphasize the relationship verdict, not the full evidence dump
- the modal should feel closer to an authored comparison dossier than a settings panel
- evidence and doctrine should stay present, but they should support the read instead of dominating it

Useful metaphors for the redesign:

- editorial compatibility brief
- relationship diagnostic report
- comparison dossier
- premium research memo

## Constraints

- frontend only
- do not change backend contracts
- do not remove feature coverage already present
- do not assume simpler or smaller data
- keep snap-to-snap input as the product contract
- do not redesign this into a live chart editor
- do not require new scoring categories from the backend
- keep loading, refresh, empty, and error states supportable
- the redesign should be implementable in the current React and Tailwind-style component system

## Out Of Scope For This Phase

- composite chart follow-on features
- Davison chart follow-on features as separate surfaces
- export or copy-prompt tooling
- backend scoring changes
- source-governance model changes
- new interpretation categories that do not already exist in the response

## What The Design Agent Should Deliver

Ask the design agent for:

- 2 to 3 distinct design directions for the Synastry modal
- one recommended direction with reasoning
- a proposed information hierarchy for the modal
- a proposed layout system for:
  - header and snap comparison controls
  - scoring scope controls
  - primary verdict / hero area
  - dimension blocks
  - supportive vs challenging evidence
  - overlays and source provenance
- recommendations for how much content should be immediately visible vs collapsed
- shared design language ideas that let Synastry align with Astro Clock, Trait Profile, Transits, Election, and Astrocartography without becoming visually identical

## Specific Questions For The Design Agent

Please answer these directly:

1. What should the primary visual hero of Synastry be?
2. How should the snap selectors and scope controls be framed so they feel intentional instead of generic?
3. Should `Overall Compatibility` and `Relationship Signature` merge into one stronger top section, or remain as adjacent surfaces?
4. How should the lower evidence-heavy sections be reorganized so they read with less fatigue?
5. What should be always visible, and what should become expandable or secondary?
6. What design language should Synastry borrow from the broader Astro Clock family, and what should remain unique to relationship comparison?

## Ready Prompt To Send The Design Agent

Design a frontend-only redesign for the Astro Clock `Synastry` feature.

This feature is a modal that compares two saved chart snaps, not a live workspace. The user selects `Snap A` and `Snap B`, adjusts scope options like modern planets, nodes, Chiron, and orb profile, and receives a comparison report. The current output includes an overall compatibility score, a narrative relationship signature, dimension score cards, supportive links, challenging links, house overlays, and doctrine/source lineage.

We want the redesign to feel like part of the same product family as Astro Clock, Trait Profile, Transits, Election, and the upgraded Astrocartography shell, but Synastry should remain a report-first modal rather than a three-column advanced workspace.

Please propose 2 to 3 design directions and recommend one. Focus on:

- stronger hierarchy between setup and verdict
- a better hero section for the comparison result
- less card fatigue
- cleaner handling of evidence-heavy sections
- preserving expert depth without making the first read crowded
- keeping the feature implementable in a React and Tailwind-style frontend

Do not redesign backend behavior or feature scope. Work only within the current frontend contract.
