# Forensic External Replay Slice 3 Results

## Scope

Third live external replay pass through the actual `/api/astro-clock/forensic` route.

Machine-readable output:

- [forensic_external_replay_slice_3_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_replay_slice_3_results.json)

## Route-Level Result

- `1/1` case returned `200`
- `1/1` returned `success: true`

## Directional Comparison Result

- `1` aligned
- `0` partially aligned
- `0` misaligned

## Aligned Case

- `shinzo_abe_assassination`
  - matched:
    - `violence_homicide`
    - `authority_or_public_case`
  - no contradicted axes:
    - no `family_involvement`
    - no `accident_or_disaster`
    - no `abduction_missing_person`
  - top route signals:
    - `Life/death overlap points to violence or homicide`
    - `Malefic contrary to sect (angular)`
    - `Public or authority axis is foregrounded`

## Notes

The route also emitted secondary `Deception` and `Degree Signatures` findings.

Those did not contradict the replay labels, so this slice stayed a documentation and regression addition rather than a new rule-fix pass.
