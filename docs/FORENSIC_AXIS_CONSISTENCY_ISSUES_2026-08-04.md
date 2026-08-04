# Forensic Axis Consistency Issues — 2026-08-04

Status: open; documented before implementation changes.

The separate survivability target, scoring, evidence, and validation review is
recorded in `docs/FORENSIC_SURVIVABILITY_MACKENZIE_DEEP_DIVE_2026-08-04.md`.

## Scope

This note records two consistency defects found while replaying the
`mackenzie_shirilla_the_crash` fixture. No engine, benchmark, or frontend logic
has been changed to resolve them yet. A second, independently sourced fixture
must be evaluated before choosing a general fix.

## FAC-001: legacy benchmark comparator can create axes from prose

The legacy fixture helper in `tests/forensic_case_corpus_utils.py` searches
finding titles, categories, and rationales for axis keywords. This conflicts
with the stable backend contract in `backend/forensic/axis_assessment.py`, which
uses only scoring-eligible findings, explicit axis hints, stable rule IDs, and
narrow category mappings.

Observed on `mackenzie_shirilla_the_crash`:

- Stable backend axes: `accident_or_disaster`,
  `friend_or_close_associate`, `authority_or_public_case`, and
  `route_vehicle_transport`.
- Stable comparison: `partially_aligned`; `accident_or_disaster` matched and
  `violence_homicide` missed.
- Legacy comparison: `aligned`; it falsely matches `violence_homicide` because
  explanatory prose contains the word `death`.

Risk: a test can pass even though the engine's declared machine-readable axis
output misses an expected axis. Wording-only edits can also change benchmark
scores without changing rule semantics.

## FAC-002: frontend replay axes can diverge from backend scoring axes

`frontend/src/features/astroclock/forensicReplayAxes.mjs` independently derives
visible replay axes from display categories and finding text. It does not use
`axis_assessment.predicted_axes` as its primary input and does not exclude
findings whose `scoring_eligible` value is `false`.

Observed on `mackenzie_shirilla_the_crash`:

- Backend axes: accident/disaster, friend/associate, authority/public, and
  route/transport.
- Frontend replay axes: authority/public, deception/cover-up, and
  accident/disaster.
- The visible deception axis is produced from contextual, non-scoring
  deception findings, while backend associate and transport axes are omitted
  from the frontend's three-axis display.

Risk: the API, benchmark report, and rendered dossier can describe different
case axes for the same payload.

## Cross-fixture validation before resolution

Use `netflix_idaho_murders_college_nightmare_2026` from
`tests/fixtures/forensic_recent_documentaries_2025_2026_cases.json` as the
second case. Compare all of the following without changing implementation:

1. live route `axis_assessment.predicted_axes`;
2. stable statistical benchmark comparison;
3. legacy prose comparator result;
4. frontend `deriveForensicReplayAxes` result;
5. scoring eligibility of any finding responsible for a disagreement.

## Cross-fixture result: Idaho student murders

Fixture: `netflix_idaho_murders_college_nightmare_2026` at the midpoint of the
official `04:00-04:25` local homicide interval.

Backend result with benchmark settings (`secondary_factors=0`):

- predicted axes: `violence_homicide`, `deception_coverup`;
- comparison: `aligned`;
- survivability: `Lower / fatal_pressure_dominant`, score `-2.92`;
- relationship observation: `stranger_public`, not hard scored;
- six of six declared fact checks passed;
- the same result held at `04:00:00`, `04:12:30`, and `04:25:00`.

The live default route enables secondary factors and returns the same axes and
qualitative outcome, with survivability score `-3.10`.

FAC-001 does not create a wrong visible result on this fixture. The legacy
comparator and stable comparator both match `violence_homicide` because the
scoring rule `violence_life_death_overlap` explicitly fires in category
`Violence`. This agreement is coincidental with respect to interface design:
the legacy path still derives its answer from text rather than consuming the
declared backend axes.

FAC-002 is exercised but does not change the final axis list on this fixture.
The backend reports six display findings in category `Deception`, but only
`venus_detriment_with_saturn` is scoring eligible. The other five deception
findings are explicitly excluded by the backend axis assessment. The frontend
still counts all six findings while ranking `deception_coverup`; the output
happens to remain correct because the one scoring-eligible deception rule
independently supports that axis and only two axes survive the final ranking.

This second case shows why the correction must preserve valid scoring axes
while excluding contextual amplification. A Mackenzie-only wording filter
would be inadequate, and globally suppressing deception would break the Idaho
case's legitimate scoring support.

## General resolution constraints

The eventual correction must not special-case a case ID, person, location,
rule title, or documentary. Machine consumers should share one canonical
scoring-axis contract. Context-only findings may remain visible as supporting
detail, but they must not silently become outcome axes in tests or the UI.

Regression coverage for the eventual change should use both fixtures:

- Mackenzie must remain accident/associate/public/transport in the canonical
  backend result and must remain a homicide miss unless a scoring violence rule
  independently fires.
- Idaho must retain its scoring `violence_homicide` and `deception_coverup`
  axes while its five non-scoring deception findings remain visible only as
  context.

No resolution has been implemented as part of this investigation.
