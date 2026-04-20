# Forensic Corpus Replay Slice 1

## Scope

First replay-ready forensic case slice promoted from the local forensic books documented in [FORENSIC_CORPUS_EVALUATION_PLAN.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_EVALUATION_PLAN.md).

This slice intentionally uses only source-explicit event metadata from prose, not guessed timings.

## Promoted Cases

- `lindbergh_kidnapping`
- `phil_hartman`
- `natalie_wood`
- `scott_peterson`
- `jonbenet_ramsey`
- `susan_smith`

## Source-Metadata Basis

### High-confidence prose metadata

- `lindbergh_kidnapping`
  - "The chart was cast for 9:50 PM on March 1, 1932 in East Amwell, N.J."
- `phil_hartman`
  - "In the crime chart (May 28, 1998; Encino, California; 2:30 a.m.)"
- `natalie_wood`
  - "I cast the chart for 11:05 p.m. on November 29, 1981, the time Natalie was last seen alive."
- `scott_peterson`
  - "Laci's last known contact ... on the evening of December 23, 2002, at 8:30 p.m., and I used that time to cast the horoscope."
- `jonbenet_ramsey`
  - "JonBenet was reported missing ... at 5:52 a.m. I used the time of the call to the police."

### Medium-confidence prose metadata

- `susan_smith`
  - "The awful deed took place at approximately 9:00 p.m. on October 25, 1994."
  - This is still replay-worthy, but the source itself marks the time as approximate.

## Implemented Files

- [forensic_case_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_1.json)
- [forensic_case_replay_utils.py](C:/Users/sabaa/Downloads/codexhorary/tests/forensic_case_replay_utils.py)
- [run_forensic_case_replay_slice_1.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_1.py)
- [test_forensic_case_replay_slice_1.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_replay_slice_1.py)

## Intended Next Step

Run the replay slice against the real `/api/astro-clock/forensic` route and record:

- response success/failure
- directional alignment
- missed axes
- contradicted axes
- top findings / categories

If a case misaligns, classify the fault first:

- request-context problem
- feature extraction gap
- knowledge/rule gap
- dominance/presentation issue

Only then change forensic logic or knowledge files.

## Current Status

The first actual route replay has now been captured in:

- [FORENSIC_CORPUS_REPLAY_SLICE_1_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_1_RESULTS.md)
- [forensic_case_replay_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_1_results.json)
