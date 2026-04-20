# Horary Cunning Man Source-Pass Slice 2

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_cunning_man_source_pass_slice2.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_cunning_man_source_pass_slice2.py`

## Purpose

This slice expands the external horary stress tests with freshly fetched Cunning Man questions that are useful for routing and doctrine checks, even where full replay remains blocked by incomplete chart metadata.

This is a source-pass slice, not a full replay slice.

That means:

- the questions are real fetched external examples
- the article's doctrinal framing is recorded
- the current router's behavior is pinned
- alignment and mismatch are explicit

It does **not** mean:

- that these cases are fully replayed through chart reconstruction
- that missing cast metadata has been invented

## Cases Added

1. `Will I get into a university in the USA?`
2. `Will we win the award?`
3. `Will I get the job?`
4. `How will I do in my exams?`
5. `What time will the train arrive?`

## Results

Summary:

- fetched source-pass cases: `5`
- source-aligned router observations: `5`
- source-misaligned router observations: `0`

Aligned:

- `will_i_get_into_university_usa`
  - current router: `education`
  - houses: `[1, 9]`
  - status: aligned after higher-education router pass

- `will_i_get_job_source_pass`
  - current router: `career`
  - houses: `[1, 10]`
  - status: aligned with article doctrine and now separately promoted into replay as `will_i_get_job_article_spec`

- `will_we_win_award_source_pass`
  - current router: `general`
  - houses: `[1, 7]`
  - status: provisionally aligned as a generic contest-style question

- `how_will_i_do_in_my_exams_source_pass`
  - current router: `education`
  - houses: `[1, 9]`
  - status: aligned after higher-level exam router pass

- `what_time_will_the_train_arrive_source_pass`
  - current router: `travel`
  - houses: `[1, 3]`
  - status: aligned after short-transit router pass

## Interpretation

This slice still confirms that source-pass work is useful even without full chart replay, but the main router gaps identified on first capture have now been fixed in source.

The substantive changes were:

1. higher education, admissions, and higher-level exams now route `9th`-first instead of forcing a `10th`-first success frame
2. local transit / train-arrival questions now route as `travel` via the `3rd` house instead of falling through to generic `1/7`

One collateral effect was that the existing `masters_no_perfection` replay remained `NO` but now surfaces as `denial_secondary_balance` with the 9th-house quesited, which is now pinned in the replay suite.

## Why Most Of These Cases Were Not Promoted To Full Replay

Most of the fetched articles did not publish enough reliable cast metadata to justify executable replay without speculation.

Current exception:

- `will_i_get_job_source_pass`
  - this case has now also been promoted into the external replay corpus by reconstructing the chart timestamp from the published wheel positions and replaying it through the serialized backend path
  - the source-pass fixture remains useful as the routing audit for the same question family

For the remaining cases, the blocking issue still applies.

Examples of what remains missing:

- explicit cast location
- explicit cast time on several pages
- a complete published wheel reconstruction

So these cases are currently valid as:

- source-backed routing stress tests
- source-backed doctrine comparison cases

and not yet valid as:

- deterministic backend replay fixtures

## Verification

- `python -m pytest tests\\test_horary_cunning_man_source_pass_slice2.py tests\\test_horary_root_fixes.py tests\\test_horary_question_corpus.py tests\\test_horary_book_examples_replay.py -q`
  - result: `31 passed`

## Next Safe Step

Use the next external source-pass slice to test whether these same router corrections generalize beyond the first university/exam/train cases before widening education or travel doctrine further.
