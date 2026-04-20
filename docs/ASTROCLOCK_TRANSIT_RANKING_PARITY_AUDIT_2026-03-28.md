# Astro Clock Transit Ranking And Parity Audit
## 2026-03-28

This note starts the ranking/parity phase of the transit audit.

The wording passes are no longer the main issue.

The next risk is that the principal signal shown to the user can still drift away from
the most relevant determined family, even when the correct event tokens already exist
inside the row.

## Finding 1

Row-level `eventType` selection in `transits_morin.py` was still static-order based.

Observed backend behavior:
- a row could carry multiple candidate event tokens
- the chosen `eventType` was the first matching token from a long fixed list
- that meant generic earlier families could win over a better area-matched family

Why that is an algorithm issue:
- the row already has a chosen `lifeArea`
- Morin-style judgment is determination-first
- once the row is determined toward `wealth`, `conflict`, `belief`, or another area,
  the selected event family should prefer candidates that actually belong to that area

## First general fix

Implemented in:
- `backend/transits_morin.py`
- `frontend/backend/transits_morin.py`

What changed:
- row event-family selection now scores candidate event tokens by area alignment
- exact matches to the row's `lifeArea` outrank static list order
- explicit row event tokens from `enriched_keywords` and `prediction_tags` get a bonus
- crisis families keep a bounded bonus when the row area is crisis-compatible
- original fixed-order selection is kept only as a final tie-breaker

This is intentionally narrow:
- token generation did not change
- replay semantics are preserved unless a row had mixed competing families
- the change applies generally to exact-time, scan, predictor, and stream because they
  all consume the same enriched row predictions

## Regression target

The regression added for this pass proves:
- a mixed `promotion` + `financial_gain` row determined to `wealth`
  must now choose `financial_gain`
- the old static-order rule would have chosen `promotion`

Covered in:
- `backend/test_transits_quality.py`

## Remaining ranking/parity work

Still open after this first fix:
- whether grouped predictor ranking should further reward the dominant event family
- whether the frontend exact-time card should prefer the strongest area-aligned
  prediction when multiple backend predictions are very close
- whether scan rows should suppress lower-priority generic families once a stronger
  area-matched family is already present

Those are separate passes.

## Second parity fix

The frontend still had its own static fallback picker in `TransitsModal.jsx` for rows
where `prediction.eventType` was missing.

That meant:
- the backend could already be more area-aware
- but the rendered event chip could still fall back to the first token from a fixed list

Applied fix:
- the frontend fallback now uses the same area-aware candidate selection pattern
- explicit row tokens from `enriched_keywords` and `prediction_tags` get a bonus
- fixed-order priority remains only as the last tie-breaker

Regression target:
- a mixed `promotion` + `financial_gain` row with `lifeArea = wealth`
  must render the wealth-family label instead of defaulting back to `promotion`
