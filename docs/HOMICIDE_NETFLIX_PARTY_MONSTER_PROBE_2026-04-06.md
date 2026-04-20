# Homicide Documentary Probe: Joey Comunale / "Party Monster"

## Scope

This pass treats the user's Netflix reference to `Homicide S3:E1` as the currently identifiable `Party Monster` episode tied to the Joey Comunale case.

That mapping is an assumption, not a certainty.

Reason for the assumption:
- the current public episode listings identify `Party Monster` as episode 1 of the latest `Homicide: New York` season that is publicly indexed
- the Joey Comunale case is the homicide case attached to that episode label in public listings

If the intended documentary episode is different, replace this probe with the exact episode title.

## Real-World Case Summary

Public reporting describes the Joey Comunale case as:
- an Upper East Side / Sutton Place apartment case after an after-party
- a fatal assault
- later body transport and concealment in New Jersey
- organized post-crime concealment and taunting behavior

That makes the expected real-world axes:
- violence / homicide
- deception / concealment
- linked-person or acquaintance dynamics

## Probed Anchor Windows

Location used:
- `420 East 58th Street, Manhattan, New York, USA`

Tested windows:
- `2016-11-13 06:40`
- `2016-11-13 06:50`
- `2016-11-13 07:00`
- `2016-11-13 07:30`

These are apartment-window probes around the publicly discussed departure / disappearance timeline.
They are exploratory anchors, not courtroom claims.

## Live Engine Output

### 06:40

- categories:
  - `Associates: 1`
  - `Deception: 2`
  - `Public: 1`
  - `Stressors: 1`
- leading findings:
  - `Malefic contrary to sect (angular)`
  - `Friend or close associate axis is active`
  - `Public or authority axis is foregrounded`
  - `Mute signs on angles`
  - `Mute signs on 3rd/9th`

### 06:50

- categories:
  - `Associates: 1`
  - `Deception: 3`
  - `Public: 1`
  - `Violence: 1`
- leading findings:
  - `Friend or close associate axis is active`
  - `Known-person violence pattern is active in a social or after-hours setting`
  - `Sun/Moon in 12th house`
  - `Public or authority axis is foregrounded`
  - `Mute signs on angles`
  - `Mute signs on 3rd/9th`

### 07:00

- categories:
  - `Associates: 1`
  - `Deception: 3`
  - `Public: 1`
  - `Violence: 1`
- leading findings:
  - `Friend or close associate axis is active`
  - `Known-person violence pattern is active in a social or after-hours setting`
  - `Sun/Moon in 12th house`
  - `Public or authority axis is foregrounded`
  - `Mute signs on angles`
  - `Mute signs on 3rd/9th`

### 07:30

- categories:
  - `Deception: 2`
  - `Public: 1`
- leading findings:
  - `Sun/Moon in 12th house`
  - `Public or authority axis is foregrounded`
  - `Mute signs on angles`

## Engine Output Vs. Real Events

The output is now materially better at the strongest anchors, but it is still uneven across the full apartment-window spread.

What the engine does now see cleanly at the stronger anchors:
- concealment / hiddenness
- linked-person or associate dynamics
- violence in a social or after-hours context

What it does not surface cleanly enough:
- a stable homicide pattern across every nearby anchor
- a clean cover-up chain proportional to the later concealment behavior
- a strong enough signal at the latest `07:30` window

The earlier disaster drift at `07:00` is gone.
The remaining weakness is that `07:30` still softens back into a more generic hidden/public read rather than holding the violence/associate pattern.

## Current Assessment

This is still not a replay-ready homicide benchmark.

It is useful as an exploratory documentary-linked stress probe because it shows:
- the engine can now pick up concealment pressure plus known-person violence and associate structure at the strongest anchors
- the engine is better on this apartment-homicide timeline than it was before, but it still is not stable enough across all nearby anchors to be treated as a clean comparative benchmark
- keyword-only comparator logic would overstate alignment here, so this case should be assessed manually rather than through the loose text-keyword comparator used for the journalist abduction set

## Files Added In This Pass

- [forensic_external_homicide_documentary_probes.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_homicide_documentary_probes.json)
- [test_forensic_homicide_documentary_probe.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_homicide_documentary_probe.py)

## Validation

Executed:

```powershell
python -m pytest -q tests\test_forensic_homicide_documentary_probe.py
```

That smoke test only verifies the route resolves for the four anchor windows.
It does not freeze the current weak category mix as a correctness target.
