# Memo Headline Hardening

## Sketch

Current flow:

1. `build_synastry_report()` in [synastry_engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_engine.py) builds memo categories and a narrative `overall_score`
2. the benchmark runner now compares the live memo headline against a preserved legacy baseline
3. public overall cases showed that the old memo headline was a weak ranking model even when the structured `Life Themes` totals were stronger

## Failure Pattern

The public overall slice exposed the same pattern repeatedly:

- the old memo headline rewarded high-activity or high-intensity candidates that were not the historical partner
- `growth` was frequently saturated near `100`
- raw support-balance often stayed high even when `friction` and `burden` were also high
- mutual reception could be counted twice: once through memo categories and then again as a separate headline bonus

This made the old memo headline behave like a readable summary score, not a strong ordered partner-retrieval score.

## Source Basis

The hardening is backed by source-side rules and benchmark notes:

- [synastry_rule_catalog.json](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_rule_catalog.json):
  - `compatibility_conflict_gate.summary` says compatibility should reflect lived ease, not just significance, compensation, or binding force when hard themes dominate
  - mutual reception is already scored by `mutual_reception_support`, so adding a second headline bonus double-counts willingness
- [compatibility_benchmark_plan.md](</C:/Program Files (x86)/Galaxy/docs/research/compatibility_benchmark_plan.md>):
  - the benchmark is ordered partner retrieval, not a prose-quality test
- [compatibility_baseline_logic.md](</C:/Program Files (x86)/Galaxy/docs/research/compatibility_baseline_logic.md>):
  - when a fuller aggregate overcounts noisy contribution, a reduced theme-led scalar can be the better retrieval model

## Resolution

Move the hardening into the live memo headline and keep the old formula as a benchmark baseline.

Current live headline formula:

- `0.26 * compatibility`
- `1.2 * communication`
- `0.12 * attachment`
- `0.18 * attraction`
- `-0.06 * friction`
- `-0.4 * burden`
- then pass the weighted total through a sigmoid normalizer centered at `40` with scale `18`

Why these terms:

- `compatibility` and `communication` remain the clearest memo-side lived-fit signals, but `communication` is no longer allowed to dominate the headline by itself
- `attachment` stays in as a light staying-power term without driving the score back toward sticky saturation
- `attraction` stays visible, but lightly
- `friction` now contributes a direct strain penalty instead of leaving all overt conflict to the narrative only
- `burden` remains the heavier chronic-hardship penalty
- the sigmoid normalization removes the old `sum then clamp to 100` behavior, so a strong but flawed pair can land in the `80s` or `90s` instead of falsely reading as a perfect `100`
- `growth`, raw support-volume balance, and a second reception bonus remain outside the headline because they were the main activity-inflating terms on the miss cases

## Hardening Plan

1. Use doctrine-level memo categories to build the live headline.
2. Keep the previous component-blend formula as `memo_legacy_score` inside the benchmark runner.
3. Report benchmark results by mode so overall, union, and work are not blended.
4. Keep the old memo scalar beside the new headline so regressions stay visible.
5. If the memo benchmark still misses core spouse cases after this step, inspect rule-level durability signals instead of continuing to tune scalar weights blindly.

## Remaining Gap

The hardened memo headline improves the public overall slice, but it does not fully solve every spouse-retrieval miss. The remaining misses point to deeper rule-layer issues, especially where the memo engine still favors dramatic interaction over partner-specific stability.

## Benchmark Rerun

After moving the hardening into the live memo headline, adding a direct `friction` penalty, replacing the hard clamp with a sigmoid normalization step, and preserving the old formula as `memo_legacy_score`, the public `overall` benchmark slice now reads:

- `memo_overall_score`: top-1 `0.4000`, top-3 `0.6000`, `MRR 0.5900`, mean rank `2.6`
- `memo_legacy_score`: top-1 `0.0000`, top-3 `0.2000`, `MRR 0.2200`, mean rank `4.8`

Case movement on the `overall` public slice:

- `overall_paul_linda`: `5 -> 1`
- `overall_frida_diego`: `6 -> 1`
- `overall_jimmy_rosalynn`: `5 -> 4`
- `overall_audrey_jose`: `3 -> 2`
- `overall_jfk_jackie`: `5 -> 5`

So the hardening is materially better than the legacy memo headline on the task it was meant to fix, but it is still not the best overall model on the public slice. `Life Themes theme_total` remains stronger at partner retrieval.
