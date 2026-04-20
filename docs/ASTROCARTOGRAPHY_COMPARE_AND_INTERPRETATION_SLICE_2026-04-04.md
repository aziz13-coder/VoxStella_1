# Astrocartography Compare And Interpretation Slice

Date: 2026-04-04

## Purpose

This memo documents the next useful Astrocartography implementation slice after the first map-and-inspector release.

The slice adds two things:

- richer interpretation cards for inspected cities
- a compare tray that lets the user pin inspected cities inside the same modal

This is intentionally smaller than the future batch compare engine. It is a workflow-first slice that improves the current feature immediately without committing the backend to a final goal-model API.

## Product Goal

The first Astrocartography modal already supports:

- snap-first natal source
- optional transit overlay
- world map with natal and transit lines
- single-city inspection

What it lacks is a way to answer two obvious user questions:

- "What does this city actually mean?"
- "How does this city compare to the last two I inspected?"

This slice addresses those two gaps.

## User-Facing Scope

### 1. Interpretation cards

When a city is inspected, the right rail should no longer show only raw line labels and distances.

Instead, each reading block should show:

- a short headline
- a support note
- a signal score
- enriched line cards with:
  - line label
  - distance
  - zone classification
  - short meaning
  - caution note

The reading blocks remain split into:

- `Natal Baseline`
- `Transit Activation`

This preserves the workflow rule already established in the product draft:

- natal is the fixed base
- transit is an overlay, not a replacement

### 2. Compare tray

The user can pin the currently inspected city into a tray without leaving the modal.

The compare tray should:

- live in the same right rail as the inspector
- use the current inspected reading as its source
- support quick removal
- be reset when the core map context changes

In this slice, compare is intentionally scoped to the current configuration:

- natal snap
- active bodies
- active angles
- transit overlay state

If those change, the compare tray is cleared.

## Why This Slice Is The Right Next Step

This is the smallest slice that makes the feature feel usable rather than technical.

It avoids two bad outcomes:

- forcing the user to interpret a wall of raw distances
- building a large place-finder engine before the basic city-inspection workflow feels coherent

It also matches the current Astro Clock design language:

- one modal workspace
- left rail for controls
- center for the map
- right rail for interpretation and decision support

## Backend Contract For This Slice

The existing location endpoint remains the main source:

- `/api/astro-clock/astrocartography/location`

The response is extended with a `reading` object for natal and transit:

```json
{
  "target": {
    "label": "Lisbon, Portugal",
    "latitude": 38.7223,
    "longitude": -9.1393
  },
  "natal": {
    "meta": {},
    "nearest_lines": [],
    "reading": {
      "signal_score": 74,
      "headline": "Sun MC is the clearest line here...",
      "support_note": "Secondary support comes from Venus DSC.",
      "lead_line": {},
      "support_line": {},
      "zone_counts": {
        "primary": 2,
        "extended": 1,
        "background": 5
      },
      "nearest_lines": [
        {
          "id": "Sun:MC",
          "label": "Sun MC",
          "distance_km": 92.4,
          "zone": "primary",
          "signal_score": 86,
          "summary": "Sun on the MC line emphasizes visibility...",
          "caution": "Watch for ego heat..."
        }
      ]
    }
  }
}
```

Important implementation note:

- this slice uses source-backed interpretation assets generated from the repo-local Astrocartography knowledge base
- its score is distance-first and filter-scoped, using the corpus-backed primary and extended radius policy
- it is not the final goal-model or PathFinder scoring engine

## Frontend Contract For This Slice

The modal should add:

- an `Add To Compare` button in the inspector header
- interpretation cards in the `Natal Baseline` and `Transit Activation` sections
- a `Compare Tray` section below the reading blocks

The compare tray should show:

- city label
- combined comparison index
- natal signal score
- optional transit signal score
- dominant natal line
- optional dominant transit line

## What This Slice Deliberately Does Not Do

- no batch compare endpoint yet
- no goal-model weighting like `Love`, `Work`, or `Money`
- no relocation chart output yet
- no paran or crossing ranking yet
- no city search result list or auto-suggest

Those remain valid next phases, but they should be built on top of a stable inspect-and-compare workflow.

## Implementation Status

This memo accompanies the first code pass for the slice:

- backend reading summaries and signal scoring added
- location endpoint extended with `reading`
- frontend inspector upgraded to interpretation cards
- compare tray added to the Astrocartography modal

The next logical follow-up after this slice is:

- backend batch compare endpoint
- relocation chart panel
- nearby crossings / parans panel
- goal-model overlays for `Education`, `Love`, `Work`, and `Money`
