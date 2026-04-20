# Forensic External Replay Slice 1

## Scope

First replay slice promoted from external-source review work after the local-source forensic corpus aligned through slice 6.

Machine-readable fixture:

- [forensic_external_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_replay_slice_1.json)

## Why This Slice Exists

The local-source corpus is intentionally conservative and is grounded in the Salerno and Luley source files already stored in the repo.

After that baseline aligned through slice 6, the next safe expansion path was:

- review user-supplied external candidates
- recover stronger event anchors from higher-confidence public records
- only promote a case if it can pass through the live `/api/astro-clock/forensic` route without introducing contradictory family, child, or disaster direction

## Case Promoted

### `idaho_four_murders`

- source basis:
  - official probable cause affidavit for the Moscow, Idaho homicides
  - the user-supplied Idaho forensic astrology video was used only as the initial candidate lead, not as the final timing authority
- replay choice:
  - `2022-11-13T04:17:00`, `Moscow, Idaho`, `America/Los_Angeles`
- metadata note:
  - the affidavit says investigators believe the homicides occurred between `4:00 AM` and `4:25 AM`
  - it also records distorted audio, a loud thud, and dog barking at approximately `4:17 AM`
  - that made `4:17 AM` the strongest specific anchor recovered in this pass
- expected primary axis:
  - `violence_homicide`
- expected secondary axes:
  - `deception_coverup`
  - `authority_or_public_case`
- contradictory axes:
  - `family_involvement`
  - `child_victim`
  - `accident_or_disaster`

## Why Delphi Was Not Promoted

`libby_abby_delphi` was re-checked with a stronger `2:32:39 PM` phone-stop anchor reported in trial coverage, but the live route still emitted domestic, family, and associate direction.

So Delphi remains in manual review rather than being promoted into this slice.
