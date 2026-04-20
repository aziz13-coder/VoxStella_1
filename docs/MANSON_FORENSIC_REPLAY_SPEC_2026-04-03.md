# Manson Forensic Replay Spec

## Scope

This note captures a source-grounded replay draft for cases surfaced by `Chaos: The Manson Murders` and related historical reporting. The goal is to turn documentary interest into usable forensic validation candidates without importing speculative motive theories into the expected-output layer.

The machine-readable draft fixture is:

- `tests/fixtures/forensic_external_manson_case_candidates.json`

## Why These Cases

Three cases were selected as the first-pass replay set:

1. `tate_cielo_drive_murders`
2. `labianca_murders`
3. `gary_hinman_murder`

These are the strongest candidates because they give distinct forensic patterns:

- Tate: multi-offender homicide, blood writing, celebrity/public-profile context
- LaBianca: linked second scene, blood writing, repeat-offender pattern continuity
- Hinman: known-associate victim, captivity, false-flag blood writing, cleaner deception test

`donald_shorty_shea_murder` is intentionally deferred. It is potentially useful for later concealment and rural-disposal testing, but it is weaker as a first replay candidate because the timing anchor is less defensible from the sources reviewed in this pass.

## Ground-Truth Rule

Use two label layers for any future executable replay:

### Hard outcomes

These are valid replay truths:

- victim list
- approximate date
- location
- scene markers
- known offender count or multi-offender status
- blood writing or staging facts
- conviction-level facts where relevant

### Soft interpretations

These must not become pass/fail truth labels:

- MKUltra or intelligence-adjacency theories
- global conspiracy framing
- Terry Melcher revenge as a settled fact
- Helter Skelter as the only accepted motive
- any documentary-only theory that lacks case-file-grade support

The replay should validate against the first list and keep the second list as analyst notes only.

## Case Notes

### Tate / Cielo Drive

Recommended expected axes:

- Primary: `violence_homicide`
- Secondary: `deception_coverup`, `authority_or_public_case`
- Contradictory: `domestic_partner_involvement`, `family_involvement`, `accident_or_disaster`, `child_victim`

Reasoning:

- Strong homicide signal is non-negotiable.
- Blood writing and staged messaging support deception or coverup pressure.
- The public-profile victim cluster makes this a valid public-case candidate.
- It should not collapse into domestic, family, or accident logic.

Replay blocker:

- This pass did not recover a narrow enough police-grade homicide-time window.

### LaBianca

Recommended expected axes:

- Primary: `violence_homicide`
- Secondary: `deception_coverup`
- Contradictory: `domestic_partner_involvement`, `family_involvement`, `child_victim`, `accident_or_disaster`

Reasoning:

- It is a linked homicide event with explicit blood writing and staged messaging.
- It is useful for checking whether the engine preserves violent/staging logic without drifting into domestic or family overreads simply because the victims were a married couple.

Replay blocker:

- This pass did not recover a narrow enough home-entry or homicide interval.

### Gary Hinman

Recommended expected axes:

- Primary: `violence_homicide`
- Secondary: `deception_coverup`, `friend_or_close_associate`
- Contradictory: `domestic_partner_involvement`, `family_involvement`, `child_victim`, `accident_or_disaster`, `authority_or_public_case`

Reasoning:

- This is the cleanest logic test of the three.
- The blood writing makes deception directly relevant.
- The victim's prior connection to Family members makes associate logic relevant.
- It should not overfire into public-case or domestic-family axes.

Replay blocker:

- Sources reviewed here support a date and captivity narrative more strongly than a precise fatal-assault timestamp.

## Recommended Patch Order If We Promote These Later

1. Recover police, court, coroner, or affidavit-grade time windows for Tate.
2. Recover equivalent timing support for LaBianca.
3. Recover a defensible final-assault window for Hinman inside the captivity period.
4. Run exploratory manual route probes for each candidate.
5. Check for false positives against `family_involvement`, `domestic_partner_involvement`, `child_victim`, and `accident_or_disaster`.
6. Promote only replay-safe anchors into a new external replay slice.

## Sources Used

- Netflix, `Chaos: The Manson Murders`
- TIME, `What We Still Don't Know About the Manson Murders`
- TIME, `The True Story Behind 'Making Manson' Docuseries`
- Britannica, `Charles Manson - Tate-LaBianca Murders`
- Los Angeles Times, `Remembering the victims of the Manson murders`
- Associated Press summary via ABC17, `The Manson 'family': A look at key players and victims in the cult leader's killings`
