# AstroClock Synastry Summary Tile Direction

Date: 2026-04-03

## Problem

The previous summary tile in the synastry modal behaved more like a developer diagnostics panel than a user-facing interpretation surface.

What made it weak:

1. it repeated metrics the featured overall card already showed instead of interpreting them
2. it exposed internal model labels such as `binding`, `support balance`, and `reception bonus` too early
3. it used counts and tiny text rows where the UI needed a stronger editorial thesis
4. it made the top row feel like three disconnected boxes rather than one coherent reading surface

## Direction

The summary tile should become a `relationship thesis card`.

That means the top area should answer:

1. what kind of relationship does this read like?
2. what holds it together?
3. what creates strain?
4. what is the overall shape of the bond?

## Intended Hierarchy

The revised top section should read in this order:

1. featured overall score card
2. relationship signature card
3. charts and comparison setup
4. scope and advanced model details

The relationship signature card should contain:

1. a short headline verdict
2. one concise interpretive paragraph
3. compact axis chips for `Ease`, `Bond`, and `Growth`
4. a split view for:
   - `What Holds It Together`
   - `What Creates Strain`
5. a quieter `Why this score` disclosure for internal mechanics and counts

## Design Principles

1. interpret first, diagnose second
2. keep the strongest idea in large type, not buried in tiny rows
3. move internal model diagnostics out of the main reading path
4. let supportive and challenging themes sit side by side so the bond feels nuanced, not flattened
5. preserve the existing app language and utility-card system, but give the synastry top section a stronger visual center

## Content Strategy

The summary surface should use existing backend output, not introduce new logic:

1. headline and paragraph from the overall component blend
2. support column from `top_supportive_links`
3. strain column from `top_challenging_links`
4. axis chips from overall components
5. advanced disclosure from summary lines and counts

This keeps the redesign presentational rather than doctrinal.

## Implementation Notes

The frontend implementation should:

1. keep the featured overall card
2. replace the old summary box with a thesis-style card
3. move counts and model details into a quieter `Why this score` or scope area
4. separate `Charts` from `Scope & Model` so the top section reads cleanly on desktop and mobile

## Expected Result

The synastry modal should feel less like:

1. score card
2. utility box
3. diagnostics box

and more like:

1. overall reading
2. relationship thesis
3. supporting setup and traceability

That should make the synastry feature easier to trust, easier to scan, and better aligned with the product's strongest differentiator: structured, explainable relationship analysis rather than vague compatibility percentages.
