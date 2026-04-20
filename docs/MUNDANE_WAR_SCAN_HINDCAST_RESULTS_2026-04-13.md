# Mundane War Scan Hindcast Results

## Current Suite Result

- cases: `4`
- place recall: `4/4`
- alignment passes: `2/4`
- target-window hits: `3/4`
- near hits: `1/4`
- median target place rank: `4.0`
- median peak distance: `0.0h`

## Critical Answer

The current war-event scan shows mixed hindcast signal.

It can usually recover the relevant theater somewhere in the returned place-series output, but it does not yet discriminate the correct place-window combination reliably enough to claim predictive scan performance.

## Case Notes

### Passes

- `war_scan_hindcast_us_iran_outbreak_2026`
  - Tehran survives at rank `2`
  - target window is the selected peak window
  - target window beats both matched controls

- `war_scan_hindcast_desert_storm_campaign_1991`
  - Baghdad survives at rank `2`
  - target campaign window is the selected peak window
  - target window beats both matched controls

### Fails

- `war_scan_hindcast_desert_storm_outbreak_1991`
  - Baghdad survives, but only at rank `6`
  - target window stays near the peak, but a matched control ties the same peak score
  - failure is mainly control-window discrimination, not total absence of signal

- `war_scan_hindcast_pearl_harbor_outbreak_1941`
  - Honolulu survives in the full place series, but only at rank `18`
  - target window does coincide with the local peak, but the U.S. atlas field is dominated by unrelated mainland locations
  - this looks like a real atlas / locality weakness in the current runtime

## Dominant Failure Pattern

The suite is not failing because the target place vanishes.

The main failure pattern is:

- target place survives, but
- another control window or another place still outperforms the target

That means the current war scan is better at broad theater recovery than at clean outbreak localization.
