# AstroClock Synastry Content Slices

Date: 2026-04-03

## Purpose

Create a separate lane for synastry cases used in:

1. blog posts
2. demo walkthroughs
3. public-interest comparisons

These content slices must not be used for:

1. algorithm calibration
2. historical validation
3. rule-weight tuning

## Why This Exists

The historical-validation corpus and replay slices are designed to answer:

1. does the engine resemble real relationship outcomes?
2. should the model be tuned?

That is the wrong lane for high-search-interest celebrity examples with weaker timed data.

Content slices exist so we can still do:

1. `what the engine says about Justin Bieber + Selena Gomez`
2. `what the engine says about Justin Bieber + Hailey Bieber`

without polluting the calibration corpus.

## Implementation

Primary files:

1. [synastry_content_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_content_slice_1.json#L1)
2. [build_synastry_content_slice_1.py](C:/Users/sabaa/Downloads/codexhorary/scripts/build_synastry_content_slice_1.py#L1)
3. [synastry_content_slice_utils.py](C:/Users/sabaa/Downloads/codexhorary/tests/synastry_content_slice_utils.py#L1)
4. [run_synastry_content_slice_1.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_synastry_content_slice_1.py#L1)
5. [synastry_content_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_content_slice_1_results.json#L1)

## Current Slice

The first content slice currently contains:

1. `Justin Bieber + Selena Gomez`
2. `Justin Bieber + Hailey Bieber`

Current lane rules:

1. `usage_lane = blog_content_only`
2. `calibration_eligible = false`
3. `content_eligible = true`

## Current Behavior

The runner supports two modes:

1. if frozen chart snapshots are present, it runs the real synastry engine and emits a content-ready summary
2. if snapshots are not present, it emits a capture-required summary with the trust boundaries and capture requirements

The current `content slice 1` is now frozen and runnable. Both Bieber cases have chart snapshots captured from the local backend with documented public timed-source notes, so the runner now emits live engine summaries while still keeping the cases outside the calibration lane.

Current captured cases:

1. `Justin Bieber + Selena Gomez`
2. `Justin Bieber + Hailey Bieber`

Current trust boundary:

1. the engine output is valid for blog/demo framing
2. the pair metadata still has mixed public timed-data quality, especially for Hailey Bieber
3. these cases remain illustrative, not calibration-grade

Operationally, use the builder first to refresh the frozen chart snapshots and source notes, then run the slice runner to regenerate the blog/demo output artifact.

## Operational Rule

If a pair lives in a content slice, it stays outside the validation lane unless it is explicitly reviewed and promoted later.

That promotion would require:

1. explicit timed-source review
2. chart capture
3. a conscious decision to make it calibration-eligible

## Recommendation

Use content slices whenever the goal is:

1. public-interest blog content
2. SEO-facing celebrity comparisons
3. illustrative examples of what the synastry engine can surface

Do not use them to justify tuning the engine.
