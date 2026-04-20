# Structured Synastry Aspect Fix

Date: 2026-04-19

## Issue

The structured synastry engines (`life_themes`, `union_dynamics`, `work_alliance`) build their explicit aspect rows from `_cross_aspects(...)`.

That extractor emits the aspect type under `aspect`, not `aspect_name`.

The structured engine was reading `aspect_name` directly in three places:

- explicit aspect scoring
- per-theme explicit row construction
- shared contact-grid row construction

Result:

- explicit rows rendered labels like `Venus None Venus`
- `aspect_name` was blank in serialized structured rows
- the explicit scorer treated many real aspects as unknown weak negatives
- many rows collapsed to `0` because the wrong aspect key fed the integer-truncated formula

## Fix

Added a shared normalizer in [backend/synastry_multi_engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_multi_engine.py) that resolves the compatibility aspect name from either:

- `aspect_name`
- `aspect`

The structured engine now routes all explicit-aspect logic through that resolver for:

- `nval` scoring
- row labels
- serialized `aspect_name`
- shared contact-grid rows

## Remaining Zero Scores

Some explicit rows still legitimately score `0` after the fix. That is expected by the decoded Galaxy scorer, not a remaining backend mismatch.

The source docs specify:

```text
nval = int( sqrt((w1 * abs(base) / 9) * (w2 * abs(base) / 9)) * sign(base) )
```

Because the runtime uses integer truncation:

- weak minor aspects like `Semisextile` and `Quincunx`
- low-weight non-planet ids
- some angle-vs-angle explicit contacts

can still quantize to `0` even when the aspect row is real and should stay visible.

So after this fix:

- missing aspect names on structured rows are a bug and are resolved
- some explicit rows with `score = 0` are still source-consistent behavior

## Regression Coverage

Added backend tests for:

- structured explicit rows preserving real aspect names
- shared contact-grid rows accepting the raw `_cross_aspects(...)` `aspect` field
- minor/angle explicit rows that legitimately quantize to `0`
