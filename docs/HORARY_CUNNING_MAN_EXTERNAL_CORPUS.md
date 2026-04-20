# Horary External Corpus: Cunning Man Examples

## Purpose

This document records an external-source horary corpus drawn from:

- [Horary Astrology Chart Examples](https://cunning-man.co.uk/horary-chart-examples/)
- [Horary Astrology Chart Examples – Page 2](https://cunning-man.co.uk/horary-chart-examples/2/)

The goal is to use these articles as a source-backed audit corpus for the horary engine.

## Audit Type

This external corpus currently serves two different but related purposes:

1. `source-pass` routing audit
   These cases verify that the analyzer is choosing the right category, houses, quesited house, and doctrine family.
   They do not by themselves prove that the final horary judgment is correct.

2. `replay` judgment audit
   These cases verify the actual engine verdict and reasoning path on a replayable chart payload.
   They require enough chart metadata to avoid speculative recasting.

So when a slice is marked `source-pass`, it should be read as:

- router and doctrine alignment is being tested
- full chart judgment is not yet safely asserted unless that case has also been promoted into replay

## Current Status

This external corpus is active in both audit layers:

- `source-pass` routing audit
- selective `replay` judgment audit

The important limit is not whether replay is allowed in principle. It is whether a given source gives enough chart evidence for safe reconstruction.

We can use these examples now as:

- source-backed manual-review cases
- doctrine/rationale comparison cases
- executable replay cases when chart reconstruction is safe enough

We still cannot use most of them as executable engine replay tests, because the articles usually provide:

- the question
- the article's judgment/verdict
- some significator placements and rationale

but do not reliably provide:

- exact cast location
- full chart payload
- enough complete chart data to reconstruct the chart safely without speculation

That means many of these cases are useful now for audit and reasoning review, but only a subset are safe as deterministic backend replay fixtures.

## Source-Pass Status

The first source pass is complete for all 14 extracted cases.

What that means:

- each case has a title, source URL, expected category, and article verdict/result text where available
- each case has been reviewed for whether the article states exact date, time, and location
- each case can now be ranked as:
  - promotion candidate
  - blocked pending chart capture
  - manual-review only

## Corpus Inventory

The structured machine-readable inventory is stored in:

- [horary_external_cunning_man_corpus.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/horary_external_cunning_man_corpus.json)

Current extracted cases: 14

For the current state of source-vs-backend reasoning comparison, see:

- [HORARY_EXTERNAL_REASONING_COMPARISON_2026-03-25.md](C:/Users/sabaa/Downloads/codexhorary/docs/HORARY_EXTERNAL_REASONING_COMPARISON_2026-03-25.md)

## Promotion Queue

### High-priority chart-capture candidates

These are the best first candidates for later executable replay promotion:

1. `how_will_i_do_in_my_exams_source_pass`
2. `will_i_get_into_university_usa`
3. `will_we_win_award_source_pass`
4. `what_time_will_the_train_arrive_source_pass`
5. `scottish_independence_2022_source_pass`
6. `boris_vote_no_confidence_source_pass`

Why these go first:

- clear verdict direction
- app-relevant categories
- relatively clear doctrinal framing in the article
- some have explicit date/time even if location is still missing

## First Executable Replay Slice

The first article-derived replay slice is now in source.

Implemented replay-ready cases:

1. `will_i_get_job_article_spec`
2. `pay_rise_article_spec`
3. `x_romantically_article_spec`
4. `pope_die_article_spec`

Implementation method:

- use the article-published timestamp when it matches the wheel
- otherwise reconstruct the chart timestamp from the published wheel positions
- reconstruct houses from the published wheel image
- compute planetary longitudes/speeds from ephemeris at the reconstructed timestamp
- replay through the serialized backend path instead of a speculative live recast

Why this is safe enough:

- no cast location is invented for house calculation
- the published wheel supplies the house structure directly
- published planet positions from the article are checked against the reconstructed payload

Current outcomes:

- `will_i_get_job_article_spec`
  - status: `replay_ready_source_aligned`
  - article verdict: `NO`
  - backend replay verdict: `NO`
  - significance: promoted from source-pass after image-assisted reconstruction; backend reasoning matches the article's no-perfection / void-Moon / blocked-job rationale

- `pay_rise_article_spec`
  - status: `replay_ready_source_aligned`
  - article verdict: `NO`
  - backend replay verdict: `NO`

- `x_romantically_article_spec`
  - status: `replay_ready_source_aligned`
  - article verdict: `NO`
  - backend replay verdict: `NO`
  - significance: fixed by treating reciprocal-affection questions as reception-first rather than bare-perfection questions

- `pope_die_article_spec`
  - status: `replay_ready_source_aligned`
  - article verdict: `NO`
  - backend replay verdict: `NO`
  - significance: fixed by routing the Pope through the 9th and his turned 8th instead of stale health houses

## Source-Pass Slice 2

An additional fetched source-pass slice is now in source for questions where the article doctrine is clear but full replay metadata still is not.

Implemented source-pass cases:

1. `will_i_get_into_university_usa`
2. `will_we_win_award_source_pass`
3. `will_i_get_job_source_pass`
4. `how_will_i_do_in_my_exams_source_pass`
5. `what_time_will_the_train_arrive_source_pass`

Status summary:

- source-aligned router observations: `5`
- source-misaligned router observations: `0`

Primary artifact:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_CUNNING_MAN_SOURCE_PASS_SLICE_2_RESULTS.md`

## Source-Pass Slice 3

An additional fresh source-pass slice is now in source for later archive-page cases that stress foreign-nation, public-office, and treatment routing.

Implemented source-pass cases:

1. `scottish_independence_2022_source_pass`
2. `boris_vote_no_confidence_source_pass`
3. `where_is_my_watch_source_pass`
4. `ukraine_invasion_timing_source_pass`
5. `thyroid_medicine_source_pass`

Status summary:

- source-aligned router observations: `5`
- source-misaligned router observations: `0`

Primary artifact:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_CUNNING_MAN_SOURCE_PASS_SLICE_3_RESULTS.md`

## Source-Pass Slice 4

An additional fresh source-pass slice is now in source to probe the next unfixed doctrine gaps after the foreign-state / confidence-vote / treatment pass.

Implemented source-pass cases:

1. `weather_lughnasadh_source_pass`
2. `covid_test_result_timing_source_pass`
3. `train_arrive_v2_source_pass`

Status summary:

- source-aligned router observations: `3`
- source-misaligned router observations: `0`

What this slice exposed:

- weather/event questions tied to a religious festival now route through the event house instead of generic `1/7`
- medical-result timing/contact questions now stay out of the education family and route on the medical contact axis
- the short-transit `3rd`-house routing remains stable as a control

Primary artifact:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_CUNNING_MAN_SOURCE_PASS_SLICE_4_RESULTS.md`

### Medium-priority chart-capture candidates

- `train_arrive`
- `chance_of_romance`
- `raisi_dead`
- `parcel_christmas`
- `reconcile`
- `general_election`

These remain useful, but either require more reconstruction effort, involve specialised timing/event logic, or have weaker chart metadata.

### Manual-review-only cases for now

- `does_he_love_me`
- `can_ai_help_horary`

Reasons:

- anonymised chart details
- not a normal querent/outcome replay target

### Cases

1. `Can AI help with horary astrology?`
   Source: [cunning-man.co.uk/can-ai-help-with-horary-astrology](https://cunning-man.co.uk/can-ai-help-with-horary-astrology/)
   Status: `manual_review_only`
   Use now: source-backed rationale case

2. `Will we win the award?`
   Source: [cunning-man.co.uk/will-we-win-the-award](https://cunning-man.co.uk/will-we-win-the-award/)
   Stated verdict: `will not win`
   Status: `chart_capture_candidate`

3. `Will I get the job?`
   Source: [cunning-man.co.uk/will-i-get-the-job](https://cunning-man.co.uk/will-i-get-the-job/)
   Stated verdict: `no`
   Status: `replay_ready_source_aligned`

4. `We’ve been friends for years, but does he love me?`
   Source: [cunning-man.co.uk/weve-been-friends-for-years-but-does-he-love-me](https://cunning-man.co.uk/weve-been-friends-for-years-but-does-he-love-me/)
   Status: `manual_review_only`
   Note: article states the chart was altered for anonymisation, so this should remain manual-review only unless original chart data is available

5. `What time will the train arrive?`
   Source: [cunning-man.co.uk/what-time-will-the-train-arrive](https://cunning-man.co.uk/what-time-will-the-train-arrive/)
   Stated result: `train arrived at 11:13am`
   Status: `chart_capture_candidate`

6. `A chance of romance?`
   Source: [cunning-man.co.uk/a-chance-of-romance](https://cunning-man.co.uk/a-chance-of-romance/)
   Stated verdict: `no romance`
   Status: `chart_capture_candidate`

7. `Is Iranian President Ebrahim Raisi dead? What has happened to him?`
   Source: [cunning-man.co.uk/is-iranian-president-ebrahim-raisi-dead-what-has-happened-to-him](https://cunning-man.co.uk/is-iranian-president-ebrahim-raisi-dead-what-has-happened-to-him/)
   Status: `chart_capture_candidate`

8. `Will I get the pay rise?`
   Source: [cunning-man.co.uk/will-i-get-the-pay-rise](https://cunning-man.co.uk/will-i-get-the-pay-rise/)
   Stated verdict: `no`
   Stated result: denied around 3 weeks later
   Status: `replay_ready_source_aligned`

9. `Will the Pope die in the next few days?`
   Source: [cunning-man.co.uk/will-the-pope-die-in-the-next-few-days](https://cunning-man.co.uk/will-the-pope-die-in-the-next-few-days/)
   Stated verdict: `no`
   Stated result: recovery sufficient for Easter ceremonies
   Status: `replay_ready_source_aligned`

10. `Horary Astrology – How will I do in my exams?`
    Source: [cunning-man.co.uk/horary-astrology-how-will-i-do-in-my-exams](https://cunning-man.co.uk/horary-astrology-how-will-i-do-in-my-exams/)
    Stated verdict: `success`
    Status: `chart_capture_candidate`

11. `Will X and I like one another romantically?`
    Source: [cunning-man.co.uk/will-x-and-i-like-one-another-romantically](https://cunning-man.co.uk/will-x-and-i-like-one-another-romantically/)
    Stated verdict: `no romantic interest`
    Stated result: `no spark whatsoever`
    Status: `replay_ready_source_aligned`

12. `Will the parcel arrive before Christmas?`
    Source: [cunning-man.co.uk/will-the-parcel-arrive-before-christmas](https://cunning-man.co.uk/will-the-parcel-arrive-before-christmas/)
    Stated result: `did not arrive`
    Status: `chart_capture_candidate`

13. `Will we reconcile and rekindle our romance?`
    Source: [cunning-man.co.uk/will-we-reconcile](https://cunning-man.co.uk/will-we-reconcile/)
    Stated verdict: effectively `no / do not pursue`
    Stated result: querent moved toward letting go
    Status: `chart_capture_candidate`

14. `Will the UK government call an early general election?`
    Source: [cunning-man.co.uk/will-the-government-call-an-early-general-election](https://cunning-man.co.uk/will-the-government-call-an-early-general-election/)
    Stated verdict: `no`
    Stated result: scandal emerged instead
    Status: `chart_capture_candidate`

## Safe Next Step

Use this corpus in four passes:

1. Source pass
   Record verdict, result, category, and key rationale from the article.
   Status: complete.

2. Classification pass
   Tag each case with:
   - promotion priority
   - manual-review-only status
   - blocking reason
   Status: should be completed now in the machine-readable corpus.

3. Chart-capture pass
   For each article, capture or reconstruct exact cast metadata only if the source is explicit enough.
   Safe inputs:
   - exact article-stated cast date
   - exact article-stated cast time
   - exact cast location
   - or original chart payload if present

4. Replay pass
   Only after:
   - chart metadata is reliable
   Then:
   - run backend engine
   - compare backend verdict vs article verdict
   - compare frontend-rendered verdict vs backend verdict
   - compare reasoning emphasis vs article rationale

Current implementation note:

- four article-derived replay cases now exist
- all four replay-ready cases are source-aligned after the doctrine/routing fixes
- the fresh work queue is now concentrated in source-pass routing gaps, not replay disagreement on the promoted quartet
- the newest source-pass slice is now aligned after the weather and medical-result/contact router pass

## What This Protects

This external corpus is meant to test:

- category classification
- significator selection
- perfection/prohibition/frustration logic
- verdict directionality
- reasoning alignment
- backend/frontend verdict parity

It is not yet a safe deterministic replay suite.

## Recommendation

Promote cases from source-pass review into executable replay only when:

- chart metadata is strong enough to avoid speculative recasting
- the case is not marked manual-review only
- packaged/source parity has been reconfirmed on the rebuilt app

The broader promotion workflow for all completed source-pass slices is now documented in:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_SOURCE_PASS_TO_REPLAY_PLAN.md`
