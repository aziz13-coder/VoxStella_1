# AstroClock Synastry Historical Validation Plan

Date: 2026-04-03

## Current Status

Three replay-ready slices are now active:

1. [synastry_historical_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1.json)
2. [synastry_historical_replay_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1_results.json)
3. [synastry_historical_replay_slice_2.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_2.json)
4. [synastry_historical_replay_slice_2_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_2_results.json)
5. [synastry_historical_replay_slice_3.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_3.json)
6. [synastry_historical_replay_slice_3_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_3_results.json)

Current replay baseline:

1. `Paul Newman / Joanne Woodward` is now `aligned`
2. `Charles / Diana` is now `aligned`
3. `Frida Kahlo / Diego Rivera` is `partially_aligned`
4. `Sid Vicious / Nancy Spungen` is now `aligned`
5. `Elizabeth Taylor / Richard Burton` is now `aligned`
6. `Frank Sinatra / Ava Gardner` is now `aligned`
7. `Jean-Paul Sartre / Simone de Beauvoir` is now `aligned`

That means the framework is now doing real calibration work across multiple relationship archetypes rather than only collecting examples.

## Objective

Evaluate the synastry engine against real relationship examples rather than only synthetic stress fixtures.

The question here is not:

1. does the engine crash?
2. do the scores stay bounded?
3. do rule families fire?

The question is:

1. does the output resemble what is publicly known about a real relationship?
2. do the strongest supportive dimensions resemble the bond's actual strengths?
3. do the strongest burden and friction dimensions resemble the bond's actual problems?
4. does the overall tone feel directionally right across many cases?

This is `historical validation`, not technical stress testing.

## Why This Matters

The synthetic stress suite is still useful. It protects:

1. engine safety
2. threshold stability
3. option-toggle integrity
4. dead-rule detection

But it cannot tell us whether:

1. we overstate chemistry in destructive relationships
2. we understate attachment in quiet durable bonds
3. we over-reward growth signals in relationships that were mostly painful
4. our category blend resembles real-world outcomes

Historical validation is the layer that answers those questions.

## Evaluation Principle

Do not ask the engine to "predict a whole relationship perfectly."

Instead ask:

1. are the top positive dimensions directionally plausible?
2. are the top negative dimensions directionally plausible?
3. is the balance between attraction, compatibility, attachment, friction, and burden credible?
4. when the engine misses, is the miss systematic enough to justify reweighting or adding doctrine?

## Corpus Shape

Each case should describe:

1. the couple
2. the relationship type
3. known public outcome summary
4. data quality tier
5. expected synastry dimension bands
6. comparison status

This should be machine-readable so replay slices can be run repeatedly.

## Data Quality Tiers

Every case must carry a birth-data confidence tier.

Recommended vocabulary:

1. `AA`
   Recorded or highly trusted birth time.
2. `A`
   Strong source, but not perfect.
3. `B`
   Usable but lower confidence.
4. `C`
   Weak or uncertain time.
5. `date_only`
   No trusted birth time. Use only in reduced or manual-review mode.

Cases without a trustworthy time should not be treated as calibration-grade replay cases.

## Relationship Outcome Vocabulary

Use the synastry engine's actual dimensions so the evaluation stays aligned with the product surface:

1. `resonance`
2. `communication`
3. `attraction`
4. `compatibility`
5. `attachment`
6. `growth`
7. `friction`
8. `burden`

Each dimension should be labeled in a coarse band from `0` to `5`.

Band meanings:

1. `0` = very low
2. `1` = low
3. `2` = mixed-low
4. `3` = moderate
5. `4` = high
6. `5` = very high

Cases should usually define a target range, not a single exact value. This keeps the framework honest and avoids fake precision.

## Status Vocabulary

Use these status values:

1. `aligned`
2. `partially_aligned`
3. `misaligned`
4. `manual_review`
5. `not_runnable_yet`

## Corpus Tiers

### Tier 1. Directional seed couples

Public or source-backed couples with strong known outcomes but incomplete chart capture.

Purpose:

1. define expected dimension bands
2. prioritize chart capture
3. build the comparison backlog

### Tier 2. Replay-ready couples

Cases with enough chart metadata to run through the real synastry engine.

Purpose:

1. compare actual engine output against labeled expectations
2. detect repeated over- or under-scoring
3. build slice-based validation notes

### Tier 3. Manual-review couples

Cases that are:

1. too disputed
2. too data-weak
3. too complex for confident automated judgment

These cases stay useful, but they should not drive automated tuning until confidence improves.

### High-interest demo couples

Some public-interest pairs belong in the corpus because they are useful for:

1. blog examples
2. demo walkthroughs
3. traffic-oriented case studies

But they should stay distinct from calibration-grade couples when their timed data is too weak.

Current examples:

1. `Justin Bieber + Selena Gomez`
   - blog/demo-only
2. `Justin Bieber + Hailey Bieber`
   - blog/demo-only

## Comparison Workflow

### Phase 1. Build the couple inventory

Create a starter corpus with:

1. public couple name
2. relationship type
3. known outcome summary
4. birth-data confidence
5. source references

### Phase 2. Label expected dimension bands before replay

This is important. The labels must be set from known biography or source material before looking at the engine result.

For each case record:

1. expected strong dimensions
2. expected weak dimensions
3. expected burden/friction level
4. notes on why the labels were assigned

### Phase 3. Capture replay-ready chart metadata

When available, add:

1. chart data A
2. chart data B
3. or birth metadata sufficient to recreate them

The current starter implementation will support chart-data snapshots first because they are deterministic and avoid replay drift.

### Phase 4. Compare the real output

For each replay-ready case:

1. run the real synastry engine
2. convert product scores to `0-5` bands
3. compare each expected dimension
4. classify the result

### Phase 5. Log disagreement patterns

Every miss should be tagged by likely cause:

1. weighting issue
2. missing doctrine family
3. over-valued chemistry
4. under-valued burden
5. overlay interpretation issue
6. modern-layer issue
7. data-quality problem

### Phase 6. Tune the smallest responsible layer

If repeated misses appear:

1. adjust scoring blend
2. add missing governed rules
3. reduce overactive rule families
4. do not modify unrelated AstroClock infrastructure unless the corpus shows chart-state handling is wrong

## Starter Implementation In This Pass

This pass should provide:

1. a machine-readable starter corpus under `tests/fixtures/`
2. a comparison helper that scores directional alignment against expected dimension bands
3. corpus validation tests
4. a replay runner for future real chart-data slices

It does not yet require changing synastry runtime logic.

## Starter Status In This Pass

This pass adds:

1. [synastry_historical_validation_corpus.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_validation_corpus.json)
2. [synastry_historical_validation_utils.py](C:/Users/sabaa/Downloads/codexhorary/tests/synastry_historical_validation_utils.py)
3. [test_synastry_historical_validation_corpus.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_synastry_historical_validation_corpus.py)
4. [run_synastry_historical_validation.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_synastry_historical_validation.py)

## Immediate Next Order

1. keep the new attachment-cluster rule under replay pressure rather than widening it immediately
2. add another unconventional durable bond only if a new slice breaks the current attachment logic
3. keep burden tuning separate unless the same growth-heavy pattern repeats beyond `Frida / Diego`
4. treat `Frida / Diego` as the main remaining doctrinal pressure instead of reopening already-resolved attachment work

## First Replay Slice Status

The first replay-ready slice is now implemented in:

1. [synastry_historical_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1.json)
2. [run_synastry_historical_replay_slice_1.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_synastry_historical_replay_slice_1.py)
3. [synastry_historical_replay_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1_results.json)

Promoted cases:

1. Paul Newman and Joanne Woodward
2. Charles and Diana

Current baseline result:

1. both replay as `aligned`
2. no primary expected dimensions are currently missed in this slice
3. the next pressure was expanding the replay corpus so the current tuning generalized beyond two replay-ready couples

Observed early calibration signal:

1. the first two replay-ready cases are no longer active misses
2. calibration risk now comes from small-sample confidence, not from a known unresolved replay mismatch
3. that means the next doctrinal work should be driven by broader replay coverage, not by forcing more changes out of this two-case slice

## Second Replay Slice Status

The second replay-ready slice is now implemented in:

1. [synastry_historical_replay_slice_2.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_2.json)
2. [run_synastry_historical_replay_slice_2.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_synastry_historical_replay_slice_2.py)
3. [synastry_historical_replay_slice_2_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_2_results.json)

Promoted cases:

1. Frida Kahlo and Diego Rivera
2. Sid Vicious and Nancy Spungen
3. Elizabeth Taylor and Richard Burton

Current slice-2 result:

1. `Frida / Diego` remains `partially_aligned`
2. `Sid / Nancy` is now `aligned`
3. `Elizabeth / Burton` is now `aligned`
4. the engine now catches volatile attraction more reliably than before
5. `Frida / Diego` still suggests a burden underestimation problem in some growth-heavy strained bonds

Observed calibration signal:

1. the latest burden-floor fix does not appear to spread indiscriminately across the new slice
2. the attraction-family audit resolved two repeated volatile-couple misses without relying on the burden floor
3. the next doctrinal pressure has narrowed to whether attraction and burden are still underpowered in creative or growth-heavy strained bonds such as `Frida / Diego`

## Third Replay Slice Status

The third replay-ready slice is now implemented in:

1. [synastry_historical_replay_slice_3.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_3.json)
2. [run_synastry_historical_replay_slice_3.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_synastry_historical_replay_slice_3.py)
3. [synastry_historical_replay_slice_3_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_3_results.json)

Promoted cases:

1. Frank Sinatra and Ava Gardner
2. Jean-Paul Sartre and Simone de Beauvoir

Current slice-3 result:

1. `Frank / Ava` is `aligned`
2. `Sartre / Beauvoir` is now `aligned`
3. the attraction-family logic generalizes to another better-timed high-chemistry unstable marriage
4. the governed attachment-cluster floor resolves the unconventional lifelong-bond under-read without changing the volatile-couple attraction rules

Observed calibration signal:

1. `Frank / Ava` shows that the attraction-family work now generalizes beyond `Sid / Nancy` and `Elizabeth / Burton`
2. `Sartre / Beauvoir` now lands once repeated binding testimony is allowed to display as attachment instead of only pressure or growth
3. that means the current engine is no longer primarily missing chemistry in volatile cases or attachment in unconventional durable cases
4. the remaining live replay miss is still `Frida / Diego`, where burden and attraction likely remain underpowered in a growth-heavy strained bond

## First Slice Recommendation

The first replay slice should intentionally span different relationship shapes:

1. durable and high-attachment
2. high-chemistry but unstable
3. growth-heavy but burdened
4. public and conflict-heavy
5. quiet and enduring

This prevents the calibration set from overfitting to one relationship archetype.
