# Forensic External Case Candidates 2026-03-25

## Scope

These two cases were supplied after the local-source replay corpus had already aligned through slice 6.

They are not part of the existing local-source slice chain in:

- [FORENSIC_CORPUS_EVALUATION_PLAN.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_EVALUATION_PLAN.md)
- [FORENSIC_CORPUS_REPLAY_SLICE_6_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_6_RESULTS.md)

Machine-readable review record:

- [forensic_external_case_candidates.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_external_case_candidates.json)

## Reviewed External Sources

- `LIBBY AND ABBY ASTROLOGY DELPHI -THE ORIGINAL VIDEO #astrologyreadings  #astro #zodiac #astrology`
  - URL: `https://www.youtube.com/watch?v=4sYIAveyP3E`
  - published: `2017-07-26`
  - useful evidence: the description frames the February 13, 2017 Delphi murders of Liberty German and Abigail Williams, but it does not provide a defensible murder-time chart anchor
- `THE IDAHO MURDERS - ASTROLOGICAL DEEP DIVE #astrology #astro #youtube #news`
  - URL: `https://www.youtube.com/watch?v=ZweUodiwmDY`
  - published: `2022-11-21`
  - useful evidence: the description lists timestamp candidates of `1:45 AM`, `2:52 AM`, `3:45 AM`, and `11:58 AM` on November 13, 2022

## Live Route Check

Both cases were probed through the real backend route:

- `GET /api/astro-clock/forensic`

No Astro Clock request-context failure was found. The route returned `200` and `success: true` for all tested anchors.

## Candidate 1: Libby And Abby / Delphi

Expected broad direction from the supplied source:

- `violence_homicide`
- `child_victim`
- likely public or missing-person relevance

Tested anchors:

- `2017-02-13 14:13` at `Delphi, Indiana`
  - basis: public bridge-video clue-time anchor
- `2017-02-13 14:32:39` at `Delphi, Indiana`
  - basis: trial-reported phone-stop anchor

Observed route direction:

- strong `Violence` signal
- but still `Domestic`, `Family`, and `Associates` signal even after moving from the clue-time anchor to the stronger phone-stop anchor
- top findings included:
  - `Moon under death pressure`
  - `Hidden victim with angular violence markers`
  - `Partner axis is active in a domestic matter`
  - `Family axis activated by Moon and domestic houses`
  - `Friend or close associate axis is active`

Decision:

- do not add this case to slice 6
- keep it as `tier_3_manual_review`

Why:

- the tested anchor is only a clue-time proxy
- the live route still emits contradictory domestic and family direction
- without a stronger event-time anchor, any replay assertion would be weaker than the current slice standard

## Candidate 2: The Idaho 4 Murders

Expected broad direction from the supplied source:

- `violence_homicide`
- `authority_or_public_case`
- possibly `deception_coverup`

Tested anchors from the supplied source, plus the later official affidavit anchor:

- `2022-11-13 01:45` last seen on CCTV
- `2022-11-13 02:52` last phone call
- `2022-11-13 04:17` affidavit-backed audio/thud anchor inside the official homicide window
- `2022-11-13 11:58` 911 call

Observed route pattern:

- before the rule fix, the exploratory early-morning anchors leaked `Family`, and several also leaked `Children`
- after the rule fix, the official `4:17 AM` anchor holds `Violence` and `Deception` without family, child, or disaster contradiction
- `11:58` drifts into `Disaster`, which is clearly not replay-safe for this case

Representative findings:

- `Life/death overlap points to violence or homicide`
- `Mercury combust the Sun`
- `Venus in detriment with Saturn influence`
- `Travel accident or disaster pattern is active` at the `11:58` anchor

Decision:

- do not add this case to slice 6
- promote it into a new external replay slice instead:
  - [FORENSIC_EXTERNAL_REPLAY_SLICE_1.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_EXTERNAL_REPLAY_SLICE_1.md)
  - [FORENSIC_EXTERNAL_REPLAY_SLICE_1_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_EXTERNAL_REPLAY_SLICE_1_RESULTS.md)

Why:

- the official affidavit recovered a stronger event anchor
- the family and child false positives were traced to three broad direction-layer rules
- those rules were tightened without regressing slices 1 through 6, which made the `4:17 AM` anchor replay-safe

## Conclusion

Current status:

- Delphi is still a manual-review external candidate
- Idaho is now promoted into external replay slice 1
- neither case was added to slice 6, and slice 6 itself remains unchanged

Safest next step if promotion is desired later:

1. keep Delphi in manual review until a defensible murder-time anchor or stronger source support is recovered
2. use the Idaho slice-1 replay as the pattern for future external promotions
3. continue re-running the aligned local-source slices whenever an external-source rule change is made
