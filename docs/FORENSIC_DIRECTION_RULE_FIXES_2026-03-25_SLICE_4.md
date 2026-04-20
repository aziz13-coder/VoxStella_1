# Forensic Direction Rule Fixes 2026-03-25 Slice 4

## Scope

Smallest-responsible forensic knowledge fix required by the slice-4 replay pass.

## Problem

`sam_sheppard` was replaying as a spouse/domestic case because `domestic_partner_near_home_axis` only needed:

- the 7th ruler tied to the home axis
- home-axis pressure

That combination was too broad for cold cases where the victim and open-enemy rulers both sit in the home context but the local source explicitly rejects spouse involvement.

Source evidence:

- [Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Exploring%20Forensic%20Astrology%20The%20Secrets%20Behind%20Famous%20Family%20Murders%20(B.%20D.%20Salerno)%20(Z-Library).txt)
  - lines `1326` to `1327`: the book anchors the chart at `12:30 a.m. on July 4, 1954, in Cleveland, Ohio`
  - lines `263` to `270`: the introduction says there were no astral correspondences to suggest spousal murder in the Sheppard case

## Fix

Tightened `domestic_partner_near_home_axis` in:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)
- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/frontend/backend/forensic/knowledge/directional_context_rules.yaml)

New requirement:

- partner-home overlap must now also show relational stress markers such as:
  - Venus/Saturn hard contact
  - Venus/Mars hard contact
  - Moon/Venus square or opposition

This keeps spouse/home readings available when the relationship symbolism is actually pressured, while suppressing home-axis-only false positives.

## Regression Coverage

Added:

- [test_forensic_direction_rules.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_direction_rules.py)
  - `test_partner_home_axis_rule_does_not_fire_from_home_overlap_alone`

Protected live case:

- [test_forensic_case_replay_slice_4.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_4.py)
  - `sam_sheppard` now asserts `domestic_partner_involvement` as contradictory
