# Forensic Corpus Replay Slice 4

## Scope

Fourth real replay pass through the actual `/api/astro-clock/forensic` route using the remaining source-defensible public cases that could still be promoted without leaning on weak chart metadata or unsupported directional labels.

Machine-readable fixture:

- [forensic_case_replay_slice_4.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_4.json)

## Why This Slice Is Smaller

The public-case pool remaining after slices 1 to 3 was not large.

Two candidate cases were reviewed but deliberately held back from executable assertions:

- `charles_whitman`
  - the local source gives only "just after midnight" for the mother-killing chart and the route result did not produce a stable, source-grounded violence/public reading from that approximate anchor
- `haiti_earthquake`
  - the local source gives exact time but only country-level location, and the current directional-axis model does not yet support a clean earthquake/natural-disaster label without speculative rule work

Rather than padding slice 4 with weak or force-fit cases, this pass promotes the three remaining public cases whose replay basis is still defensible.

## Cases Promoted

- `sam_sheppard`
  - source basis: explicit prose
  - target question for the slice: does the route avoid re-imposing spouse involvement when the book explicitly argues against it?

- `diane_downs`
  - source basis: explicit prose, state-level location only
  - target question for the slice: does the route continue to generalize on mother/child homicide plus deception pressure?

- `marilyn_monroe_murder`
  - source basis: explicit prose plus case-context location anchor
  - target question for the slice: can the route hold a narrow homicide plus cover-up direction on a suspicious celebrity death without forcing a disaster reading?

## What Slice 4 Is Meant To Test

Slice 4 is not another broad disaster pass. It is a residual-public-case pass aimed at:

- spouse false-positive suppression in a cold case where the local source rejects spouse guilt
- continued child/family homicide stability on a fresh filicide case
- narrow suspicious-death handling on a public murder/cover-up case

## Expected Directional Axes

- `sam_sheppard`
  - expected primary:
    - `violence_homicide`
    - `friend_or_close_associate`
  - contradictory:
    - `domestic_partner_involvement`

- `diane_downs`
  - expected primary:
    - `family_involvement`
    - `child_victim`
    - `violence_homicide`

- `marilyn_monroe_murder`
  - expected primary:
    - `violence_homicide`
    - `deception_coverup`

## Files Added For Slice 4

- [forensic_case_replay_slice_4.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_4.json)
- [run_forensic_case_replay_slice_4.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_4.py)
- [test_forensic_case_replay_slice_4.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_4.py)
