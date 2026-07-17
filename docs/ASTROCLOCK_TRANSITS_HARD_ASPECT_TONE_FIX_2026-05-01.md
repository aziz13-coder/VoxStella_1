# AstroClock Transits: Hard Aspect Tone Fix

Date: 2026-05-01

## Screenshot Symptom

The scan showed a green top-hit pill for `Jupiter Opposition Saturn` while the exact-detail table described the same hit as `delay/obstruction` in the parents/home/inheritance area.

That was internally inconsistent:

- The glyph/aspect was a hard aspect: opposition.
- The selected event was adverse: `delay_obstruction`.
- The rendered top-hit pill was green because the final hit tone was still `positive`.

## How The Pill Is Calculated

The frontend top-hit pill in `frontend/src/features/astroclock/TransitsModal.jsx` calls `morinHitTone(hit)`.

`morinHitTone` resolves color in this order:

1. `prediction_tags` contains `positive`, `negative`, or `mixed`.
2. Otherwise, it uses `hit.tone`.
3. Otherwise, it falls back to `mixed`.

So a green pill means the payload advertises positive orientation, not merely that the aspect glyph is colored green.

## Root Cause

The backend final quality pass in `transits_morin.py` was determination-led:

- benefic nature of Jupiter;
- positive radical determination to home/parents;
- hard-aspect multiplier treated as strength, not polarity;
- close-enough orb factor.

That produced a positive `quality_score` even after the selected event had become `delay_obstruction`.

This was too permissive. Morin logic should allow radical determination to override generic planet/aspect stereotypes, but it should not let a hard aspect with a selected adverse event present itself as a clean positive signal.

There was a second consistency issue: final `tone` was calculated after `prediction_tags` and `prediction.tags` were assembled, so orientation tags could drift from the finalized tone.

## New Behavior

For hard aspects, the final tone pass now checks the selected event:

- If the selected event is adverse but not severe, a positive score is capped to neutral/mixed.
- If the selected event is strongly adverse, or the planet/domain context is malefic, the hit is capped negative.
- Final `prediction_tags` and `prediction.tags` are synchronized from final `tone`.

For the screenshot-shaped case, the expected payload is now:

```json
{
  "tone": "mixed",
  "quality_score": 0.0,
  "quality_label": "neutral",
  "prediction_tags": ["home", "mixed_outcome", "mixed"],
  "prediction": {
    "eventType": "delay_obstruction",
    "tags": ["home", "mixed_outcome", "mixed"]
  }
}
```

## Regression Coverage

Added a focused test in both source backends:

- `backend/test_transits_quality.py`
- `frontend/backend/test_transits_quality.py`

The test uses benefic Jupiter opposing natal Saturn in a fourth-house/home determination with `delay_obstruction`. It asserts the event remains obstruction, but the hit is not marked positive and the prediction tags match final tone.
