# Forensic External Replay Slice 3

## Scope

Third external replay slice, extending the external forensic test set into a modern head-of-government assassination chart with a strong same-day event-time anchor.

Machine-readable fixture:

- [forensic_external_replay_slice_3.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_replay_slice_3.json)

## Why This Slice Exists

External slice 1 covered a modern mass-homicide chart.

External slice 2 covered a high-profile U.S. public assassination chart.

The next useful expansion was a different but still replay-safe pattern:

- modern political assassination
- same-day press timing rather than retrospective book metadata
- strong public-axis signal without family, disaster, or abduction contradiction

## Case Promoted

### `shinzo_abe_assassination`

- source basis:
  - same-day Asahi Shimbun reporting on the Nara shooting
- replay choice:
  - `2022-07-08T11:30:00`, `Nara, Japan`, `Asia/Tokyo`
- metadata note:
  - the same-day report places the shooting during Abe's speech in front of Yamato-Saidaiji Station at around `11:30 a.m.` local time
- expected primary axes:
  - `violence_homicide`
  - `authority_or_public_case`
- expected secondary axis:
  - `deception_coverup`
- contradictory axes:
  - `family_involvement`
  - `accident_or_disaster`
  - `abduction_missing_person`

## Why This Slice Was Useful

The live route already produced:

- `Violence`
- `Public`

and it did so without another direction-rule fix pass.

That makes this a clean external regression case for modern public assassination charts rather than a new backend-tuning exercise.
