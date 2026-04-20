# Forensic External Replay Slice 2 Results

## Scope

Second live external replay pass through the actual `/api/astro-clock/forensic` route.

Machine-readable output:

- [forensic_external_replay_slice_2_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_replay_slice_2_results.json)

## Route-Level Result

- `1/1` case returned `200`
- `1/1` returned `success: true`

## Directional Comparison Result

- `1` aligned
- `0` partially aligned
- `0` misaligned

## Aligned Case

- `mlk_assassination`
  - matched:
    - `violence_homicide`
    - `authority_or_public_case`
  - no contradicted axes:
    - no `family_involvement`
    - no `accident_or_disaster`
    - no `abduction_missing_person`
  - top route signals:
    - `Life/death overlap points to violence or homicide`
    - `Public or authority axis is foregrounded`
    - `Malefic contrary to sect (angular)`

## Notes

The route also emitted an `Associates` secondary signal.

That did not contradict the replay labels, so it was documented rather than treated as a miss.
