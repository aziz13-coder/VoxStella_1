# Forensic Generic Drift Fix - 2026-04-03

## Summary

A general, source-backed drift fix was implemented in the forensic rule layer.

The original Manson exploratory pass exposed three broad problems:

1. family and child labels could be triggered from weak domestic symbolism
2. public-case labels could be triggered from light 10th-house noise
3. wide hard aspects were treated as binary afflictions without orb gating

The fix was applied at the feature/rule level, not by case-specific exceptions.

## Source Basis

The changes are grounded in the local forensic corpus:

1. `Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt`
- filicide and family-murder chapters treat family/child cases as compound patterns involving the 4th, 5th, 10th, Sun, Moon, Jupiter, and killer links
- family/child cases are not read from a single Moon or Cancer signature alone
- child cases repeatedly emphasize the 5th house of children, Jupiter as natural ruler of children, and parental/public-house clustering under stress

2. `Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt`
- public and leader cases are tied to the solar/10th axis
- the text explicitly refers to the 10th house of the President/world leader in a public death analysis
- abduction and high-profile cases are read through compound signatures, not single-house shortcuts

3. `Forensic Astrology for Everyone You Dont Need to be an Astrologer to Locate Lost Objects, Find Missing Persons, Solve… (Caroline J. Luley) (Z-Library).txt`
- the 10th house is described as the public, authorities, and public spaces
- the 12th house is hidden/concealed/end-of-life territory, not abduction by itself
- child cases can legitimately be read through Mercury and the 5th-house axis, depending on role structure

## Implemented Changes

### 1. Orb gating for hard affliction

File:
- `backend/forensic/features.py`

Change:
- `_planet_hard_afflicted()` now requires a hard aspect within `5.0` degrees orb.

Why:
- this removes false binary affliction from loose squares/oppositions that were inflating downstream family/home rules.

### 2. Family and child rules now require compound testimony

File:
- `backend/forensic/knowledge/directional_context_rules.yaml`

Changes:
- `child_family_overlap` now allows `Moon` in the 5th as a legitimate child-axis signal, but still requires separate family/home pressure and death/hidden pressure
- `family_parental_axis_homicide` now also accepts the compound pattern `4th ruler hard afflicted + 1st ruler in 8/12`

Why:
- this restores real family/child homicide charts such as Alice Crimmins without reopening broad family drift on non-family homicide scenes.

### 3. Public-case logic was split into two safer paths

File:
- `backend/forensic/knowledge/directional_context_rules.yaml`

Changes:
- `public_or_authority_axis_foregrounded` no longer treats `1st ruler rules 8th` as sufficient hidden/death pressure by itself
- `public_or_authority_axis_foregrounded` now allows `Moon hard malefic contact` as a violence-pressure qualifier when a real 10th/public axis is already live
- added `public_figure_or_leader_axis` for solar/10th public-figure cases requiring:
  - angular Sun
  - live 10th-house linkage
  - separate violence pressure

Why:
- this removes false public labels on exploratory homicide charts like Hinman
- it restores legitimate public-political homicide cases such as MLK and Shinzo Abe

## Files Changed

- `backend/forensic/features.py`
- `backend/forensic/knowledge/directional_context_rules.yaml`
- `tests/test_forensic_drift_guards.py`
- `tests/test_forensic_direction_rules.py`

## Validation

### Targeted guard and replay tests

- `python -m pytest -q tests/test_forensic_drift_guards.py`
  - passed: `9 passed`
- `python -m pytest -q tests/test_forensic_external_replay_slice_2.py tests/test_forensic_case_replay_slice_3.py tests/test_forensic_external_replay_slice_3.py`
  - passed after rule adjustments

### Full forensic matrix

- `python -m pytest -q tests/test_forensic*.py`
  - passed: `81 passed, 10 subtests passed, 1 warning`

Warning status:
- remaining warning is external `pytz` deprecation noise, not a forensic logic failure

## Manson Recheck

### Before the fix

Observed drift from exploratory probes:
- Tate could surface family, child, abduction, water, or public contamination depending on anchor
- LaBianca could drift into family/child/public contamination on weaker anchors
- Hinman could drift into public/disaster contamination

### After the fix

Rechecked anchors:

1. Tate
- `00:30` -> only light deception/mute-sign noise
- `01:15` -> light deception/house noise
- `04:10` -> violence + witness/accomplice + hidden-house emphasis
- family/child/water/public false positives removed

2. LaBianca
- `02:00` -> light deception/house noise
- `06:00` -> violence + associates + hidden-house emphasis
- `08:00` -> violence + deception + hidden-house emphasis
- family/child/public contamination removed

3. Hinman
- `00:00` -> deception/stressor only
- `06:00` -> associates + deception
- `12:00` -> violence + deception
- public false positive removed
- still not replay-safe due timing uncertainty and weak homicide-axis stability, but behavior is cleaner than before

## Outcome

Yes, a real root cause was found.

Yes, it was fixable generically.

Yes, the implemented fix is backed by the local forensic sources and behaves better on the original exploratory Manson set without breaking the broader forensic suite.
