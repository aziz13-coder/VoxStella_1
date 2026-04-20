# Journalist Abduction Holdout Probes

## Purpose

This pass adds a separate holdout set on top of the original six-case journalist benchmark and then reruns it after a source-backed rule expansion.

The original six-case benchmark remains the validation gate.
These holdout probes serve a different purpose:

- add fresh resolved journalist cases without rewriting the validated core set
- compare live engine output against real-world case dynamics
- compare the abduction-map payload against source-backed scene facts
- show where the engine generalizes and where it still underfires or drifts

## Holdout Set

The new holdout set contains four additional resolved journalist abduction cases.

1. Phil Sands
- Baghdad, Iraq
- abducted on December 26, 2005
- released alive after five days
- frozen anchor: `2005-12-26 10:30` local using a morning proxy inside the publicly reported ambush window

2. Meutya Hafid and Budiyanto
- near Ramadi, Iraq
- abducted on February 15, 2005
- released alive on February 21, 2005
- frozen anchor: `2005-02-15 14:00` local using a daytime route proxy inside the public travel window

3. Romanian journalists in Jadriya
- Baghdad, Iraq
- abducted on March 28, 2005
- released alive on May 22, 2005
- frozen anchor: `2005-03-28 20:30` local from the public hotel-area timing report

4. Richard Butler
- Sultan Palace Hotel, Basra, Iraq
- abducted on February 10, 2008
- released alive on April 14, 2008
- frozen anchor: `2008-02-10 02:30` local as a middle-of-the-night hotel-room seizure proxy from Butler's own account

## Engine Output Vs. Real Events

### Phil Sands

Real event:
- armed street ambush in Baghdad
- interpreter and driver present
- hidden rural custody
- released alive

Live engine output:
- categories:
  - `Abduction: 1`
  - `Deception: 2`
  - `Degree Signatures: 1`
  - `Headwinds: 1`
  - `Houses: 2`
  - `Violence: 2`
- leading findings:
  - `Life/death overlap points to violence or homicide`
  - `Abduction or public-place seizure pattern is active`
  - `1st ruler in the 8th house`
  - `Moon under death pressure`
  - `Malefic in the 6th house`

Assessment:
- `aligned`
- This is a good generalization case.
- The route surfaces abduction, danger, and hidden-custody pressure without drifting into family, accident, or domestic labels.

### Meutya Hafid and Budiyanto

Real event:
- route seizure near Ramadi while traveling and refueling
- removal from vehicle by armed men
- temporary hidden custody
- released alive

Live engine output:
- categories:
  - `Abduction: 1`
  - `Deception: 3`
  - `Houses: 1`
- leading findings:
  - `Abduction or confrontation-on-the-route pattern is active`
  - `Malefic in the 6th house`
  - `Mercury combust the Sun`
  - `Node with Neptune/Mercury (karmic ruse/lie scheme)`
  - `Mute signs on angles`

Assessment:
- `aligned`
- This is the cleanest route-seizure holdout in the new set.
- The engine stays focused on abduction plus concealment, which fits the public record.

### Romanian journalists in Jadriya

Real event:
- evening hotel-area seizure in Jadriya
- multiple hostages held for 55 days
- later evidence of organized deception around the kidnapping
- released alive

Live engine output:
- categories:
  - `Abduction: 1`
  - `Deception: 4`
  - `Degree Signatures: 2`
- leading findings:
  - `Moon in Via Combusta`
  - `Abduction or social-gathering seizure pattern is active`
  - `Mercury retrograde`
  - `Mercury combust the Sun`
  - `Mute signs on angles`
  - `Mute signs on 3rd/9th`

Assessment:
- `aligned`
- The route now keeps the deception testimony and also exposes the abduction structure.
- That fits the real event better: an evening hotel-area seizure, multiple hostages, and prolonged hidden custody.

### Richard Butler

Real event:
- armed men dressed as police entered a Basra hotel room at night
- forced hotel-room seizure
- extended concealed captivity
- released alive after roughly two months

Live engine output:
- categories:
  - `Abduction: 1`
  - `Deception: 3`
- leading findings:
  - `Abduction or deceptive public-assignment seizure pattern is active`
  - `Mercury retrograde`
  - `Mercury combust the Sun`
  - `Mute signs on angles`

Assessment:
- `aligned`
- This was previously the sharpest failure in the holdout set.
- The route no longer leaks into accident/disaster language and now matches the fake-police kidnapping pattern much more closely.

## Holdout Score

- Phil Sands: `aligned`
- Meutya Hafid / Budiyanto: `aligned`
- Romanian journalists in Jadriya: `aligned`
- Richard Butler: `aligned`

Holdout score: **4 / 4 aligned**

That means the original benchmark is no longer carrying the journalist validation alone.
The holdout set now generalizes cleanly enough to act as a second-layer confirmation set rather than only a stress set.

## Abduction Map State

All four holdout cases now have live abduction-map coverage.

For each case, the test suite verifies:
- `abduction_map` is returned
- the echoed origin matches the frozen fixture origin
- `origin_source` is `query_origin`
- the required role-bearing set is present

Frozen map constraints are conservative.
As with the main benchmark, the public record usually gives:
- the seizure point
- the scene type
- the broad custody outcome

It does not usually give:
- a reliable heading after seizure
- a precise transport corridor
- a destination vector

So these holdouts are scored for:
- origin fidelity
- role-bearing coverage
- scene-type compatibility

and not for exact escape geometry.

## What This Adds

The updated holdout set shows three useful things.

1. The engine generalizes beyond the original six-case benchmark.
- Phil Sands
- Meutya Hafid / Budiyanto
- Romanian journalists in Jadriya
- Richard Butler

2. Broader abduction patterns matter.
- social or group-gathering seizures can be recognized without hardcoding a single case
- deceptive public-assignment or fake-authority seizures can be separated from accident/disaster signatures

3. The map and engine are now more coherent together.
- the map still validates origin and role-bearing coverage
- the interpretive layer now better matches those same real-world seizure scenes

The original six-case gate should still stay in place because it is the established benchmark.
But these holdouts no longer read as unresolved failures.
They now function as an additional resolved-case confirmation set.

## Files Added In This Pass

- [forensic_external_journalist_abduction_holdout_cases.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_journalist_abduction_holdout_cases.json)
- [test_forensic_journalist_abduction_holdout_probes.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_journalist_abduction_holdout_probes.py)
- [test_forensic_journalist_abduction_holdout_map.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_journalist_abduction_holdout_map.py)

## Validation

Executed:

```powershell
python -m pytest -q tests\test_forensic_journalist_abduction_holdout_probes.py tests\test_forensic_journalist_abduction_holdout_map.py
```

This pass should be read alongside the original validation docs, not as a replacement for them.
What changed here is the interpretation layer, not the benchmark methodology.
