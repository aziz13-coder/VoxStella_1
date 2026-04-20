# Forensic Corpus Replay Slice 6

## Scope

Sixth replay slice for the forensic overlay, focused on the last named local-source holdback whose live route output still needed a stable family-homicide direction.

Machine-readable fixture:

- [forensic_case_replay_slice_6.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_6.json)

## Why This Case

The earlier slices already covered:

- abduction and missing-person charts
- domestic partner homicide
- family homicide
- celebrity and public murder
- aviation, maritime, and structural disaster charts

The remaining named holdback was:

- `charles_whitman`

The local source clearly supports the mother-killing chart direction, but the live `/api/astro-clock/forensic` route was still under-signaling `family_involvement`.

## Case Promoted

### `charles_whitman`

- source:
  - [Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Exploring%20Forensic%20Astrology%20The%20Secrets%20Behind%20Famous%20Family%20Murders%20(B.%20D.%20Salerno)%20(Z-Library).txt)
- source basis:
  - the local text explicitly says Whitman killed his mother just after midnight on August 1, 1966 after she had moved to Houston
- replay choice:
  - `1966-08-01T00:05:00`, `Houston, Texas`, `America/Chicago`
- metadata note:
  - the source does not give an exact minute, so the replay uses a conservative five-minute anchor from the explicit "just after midnight" wording rather than introducing a new external source
- expected primary axes:
  - `family_involvement`
  - `violence_homicide`
- expected secondary axis:
  - `authority_or_public_case`

## Slice-6 Goal

This slice was meant to answer one narrow question:

- can the live forensic route classify the remaining named holdback as a family-homicide chart without changing shared Astro Clock request or chart plumbing

It was not intended to solve every anonymous family-murder chart in the local books.
