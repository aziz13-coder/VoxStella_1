# Astro Clock Trait Profile Replay Slice 2 Results

Date: 2026-03-30

## Purpose

This slice extends the trait-profile replay corpus beyond the promoted public-figure family-presence cases in slice 1.

It targets the previously held-back intellectual and inventive cases:

- Albert Einstein
- Steve Jobs

The goal is not to promote them into the same headline-summary claim boundary as slice 1. The goal is narrower:

- verify that the intellectual families survive into route-level `summary_traits`
- verify that those same families are visible in the positive summary-polarity lane
- verify that at least one expected intellectual family survives into `top_traits`

## Claim Boundary

Promoted claim for slice 2:

- the trait-profile route now retains the intended intellectual families at the summary layer for Einstein and Jobs
- at least one expected intellectual family survives into `top_traits`

Not promoted by slice 2:

- full psychological cleanliness of the headline summary
- exact top-rank adjective ordering
- strict biographical trait correctness beyond the bounded intellectual families

## Cases

### Albert Einstein

- replay datetime: `1879-03-14T09:30:00+00:00`
- location: `Ulm, Germany`
- retained in `top_traits`:
  - `invention_discovery`
- retained in `summary_traits` / positive polarity:
  - `invention_discovery`

Interpretation:

- the inventive family no longer disappears behind generic cognition or pathology noise
- the broader headline remains mixed, so this is still an exploratory summary-presence case, not a full promoted summary-cleanliness case

### Steve Jobs

- replay datetime: `1955-02-25T03:15:00+00:00`
- location: `San Francisco, California, USA`
- retained in `top_traits`:
  - `scholarship`
- retained in `summary_traits` / positive polarity:
  - `scholarship`
  - `invention_discovery`
  - `genius_inventive_scientific`

Interpretation:

- the intellectual and inventive family is now explicit at the summary level instead of being lost under broad pleasure/social clusters
- the broader summary still includes other strong families, so this remains an exploratory improvement slice

## Automated Coverage Added

- fixture: `tests/fixtures/trait_profile_replay_slice_2.json`
- replay test: `tests/test_trait_profile_replay_slice_2.py`

## Why This Matters

Slice 1 proved family presence in the full indicated trait list for the promoted public-figure cases.

Slice 2 is the first route-level stress test that checks whether the summary layers themselves retain the intended intellectual families for the previously problematic Einstein and Jobs cases.

That is a stricter and more useful replay test than simple family presence in the raw `traits` list.
