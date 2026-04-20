# Forensic External Replay Slice 1 Results

## Scope

First live external replay pass through the actual `/api/astro-clock/forensic` route after the local-source corpus had already aligned through slice 6.

Machine-readable output:

- [forensic_external_replay_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_replay_slice_1_results.json)

## Route-Level Result

- `1/1` case returned `200`
- `1/1` returned `success: true`

## Directional Comparison Result

- `1` aligned
- `0` partially aligned
- `0` misaligned

## Aligned Case

- `idaho_four_murders`
  - matched:
    - `violence_homicide`
  - no contradicted axes:
    - no `family_involvement`
    - no `child_victim`
    - no `accident_or_disaster`
  - top route signals:
    - `Life/death overlap points to violence or homicide`
    - `Mercury combust the Sun`
    - `Venus in detriment with Saturn influence`

## Why This Case Became Replay-Safe

Two things changed compared with the earlier exploratory pass:

- the event anchor improved from speculative video timestamps to the affidavit-backed `4:17 AM` point inside the official `4:00 AM` to `4:25 AM` homicide window
- the direction layer stopped treating Moon in Cancer alone, and a 4th ruler merely sitting in its own house, as enough to force family or child labels

That left a route output that still expresses homicide pressure, but no longer contradicts the case with family, child, or disaster direction.

## Residual Notes

The route still leans heavily on `Deception` language for this chart.

That does not contradict the external replay labels, so it was documented rather than widened into a larger deception rewrite in this pass.
