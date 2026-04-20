# Mundane War Chart-Type Research

Date: 2026-04-12
Status: research memo
Scope: evaluate whether war-oriented domains should be tied primarily or exclusively to war-specific chart types

## Research Question

Should war-oriented domains in the mundane runtime use a specifically war-oriented chart type, or is it defensible to use the same war domains across Aries ingresses, lunations, eclipses, and war-event charts?

## Short Answer

No single doctrine in the current corpus supports "war must always use one chart type only."

But the current runtime is too permissive.

The strongest doctrinal reading is:

- `war_event` is the preferred chart type for first hostilities, opening strikes, invasion, and outbreak judgment
- `aries_ingress` is a yearly war-climate or national-conflict framework chart, not the preferred outbreak chart
- `lunation` is a short-window trigger chart inside a larger framework, not the preferred outbreak chart
- `eclipse` is a high-impact trigger and activation chart that can intensify or time war developments, but is not by itself the preferred first-hostilities chart

So the correct design is chart-type-specific war subdomains, not one unrestricted war lens across all chart families.

## Local Doctrine Findings

### 1. The corpus already distinguishes chart classes before domains

The repo's own chart-type research says mundane work is a family of chart classes and that chart type should be selected before domain scoring. It explicitly separates:

- annual framework charts
- shorter trigger charts
- event charts
- standing charts

It also states that Watters is clearest that the governing chart for a war is the chart for the moment hostilities actually begin, and that this should not be collapsed into ingress or national-chart logic.

### 2. Annual and monthly charts are layered timing structures, not replacements for event charts

The timing memo says the source set uses layered timing:

- annual framework charts
- shorter trigger charts
- eclipse activations
- long-cycle backgrounds
- later transits and aspects

This is strong support for using ingress, lunation, and eclipse charts in war work, but not as interchangeable substitutes for the event chart of first hostilities.

### 3. Runtime assets already imply this distinction

The current chart-type runtime already says:

- `war_event` is an `event_anchor`
- `aries_ingress` is an `annual_backdrop`
- `lunation` is a `short_window_trigger`
- `eclipse` is a `high_impact_trigger`

The current domain runtime also says:

- `war_conflict` is only a compatibility umbrella
- `war_outbreak` should prioritize the war-event chart and first/seventh-house opening-hostilities logic
- `campaign_escalation` and `military_reversal` are different from outbreak

So the repo's own runtime language already argues against using one broad war lens equally across all chart types.

## Current Technical Findings

### 1. `war_outbreak` is only weakly chart-type-gated

In the current evaluator, `war_outbreak` gets an extra rule if the chart kind is `war_event`, but non-war charts can still score from:

- Mars angular
- Moon on the conflict axis
- aggressor or defender angularity
- eclipse activation support

That means outbreak semantics can still appear on charts that are doctrinally better treated as framework or trigger charts.

### 2. Long-range scan behavior shows the practical problem

A reproduced backend run using:

- `chart_type = aries_ingress`
- `domain = war_conflict`
- `scan_mode = long_range_async_scan`
- `region = global`
- `step = 6h`
- `window = 2026-02-01 01:00` to `2026-02-28 09:00`

returned:

- top ranked raw cells dominated by `Istanbul, Turkey`
- all top cells clustered on the first two days only because ranking is raw-cell based
- place-series output for top places as full-window plateaus, not sharp outbreak peaks
- `peak_selection = peak_plateau`
- `peak_window_start_datetime = 2026-02-01T01:00:00+00:00`
- `peak_window_end_datetime = 2026-02-28T07:00:00+00:00`

This is not evidence that the peak detector is wrong now. The plateau-aware fix is working. The issue is semantic:

- a framework chart plus a broad war lens across a long window produces a sustained war-climate surface
- the UI and ranking can still be read as if it were an outbreak-localization result

### 3. The scan backend itself treats war-event charts specially

The current scan bias logic only adds theater-proximity weighting for:

- `chart_type = war_event`
- `domain = war_conflict`

All other chart types get no war-theater locality bias at all. That is another strong technical sign that the codebase already assumes war-event charts are different in kind from ingress, lunation, and eclipse charts.

## Empirical Comparison Across Chart Types

A direct runtime comparison of `war_outbreak` for the same overall case produced:

- `war_event`: score 14, matched `war_outbreak_event_anchor` and `war_outbreak_moon_axis`
- `aries_ingress`: score 16, matched `war_outbreak_mars_angular`
- `lunation`: score 9, matched `war_outbreak_moon_axis`
- `eclipse`: score 9, matched `war_outbreak_moon_axis`

The important point is not the exact score. It is that the same outbreak summary can still be generated from framework and trigger charts with only thin chart-type differentiation.

That is doctrinally too loose.

## External Corroboration

External material used only as support, not as primary authority:

- Lee Lehman, "The Development of Modern Mundane Astrology" (blog essay)
  - discusses wartime interpretation using both lunations and Aries ingress charts
  - treats the 1939 Aries ingress as a major war framework chart
  - also treats the D-Day full moon/lunation as operationally descriptive of the invasion window
  - this supports layered use: ingress for broad war framework, lunation for shorter event windows, not simple interchangeability

- AstroCepheus knowledge-base summary on war and peace
  - secondary and less rigorous than the repo's local corpus
  - still broadly supports reading war through national charts, transits, house activations, and conflict indicators

The external picture is consistent with the local one:

- war can be studied through multiple chart families
- but chart families are used for different jobs

## Evaluation

### What is defensible

It is defensible to use war-related domains on more than one chart type, because the doctrine is layered.

Specifically:

- `war_event` for first hostilities and opening strikes
- `aries_ingress` for annual war climate or national exposure to conflict
- `lunation` for shorter trigger windows inside the larger frame
- `eclipse` for intensified or activated conflict periods

### What is not defensible

It is not defensible to treat the same war label as semantically identical across all those chart types.

The current problem is not that non-war chart types are used at all.
The problem is that:

- the outbreak semantics remain too available outside `war_event`
- the compatibility umbrella `war_conflict` is still too easy to use on framework charts
- long-range scans make framework charts look like outbreak-localization tools

## Recommendation

### Recommended domain-chart policy

#### 1. `war_outbreak`

Preferred:

- `war_event`

Allowed with strong caution:

- `lunation`
- `eclipse`

Not ideal for default public use:

- `aries_ingress`

Policy:

- `war_outbreak` should be public-primary on `war_event`
- if used on `lunation` or `eclipse`, it should be labeled as trigger support for outbreak pressure, not as the preferred first-hostilities chart
- if used on `aries_ingress`, it should either be blocked or renamed in presentation to something closer to `outbreak background pressure`

#### 2. `campaign_escalation`

Preferred:

- `war_event`
- `eclipse`
- `aries_ingress`

Allowed:

- `lunation`

Policy:

- this domain is the most defensible cross-chart war lens
- it naturally fits framework plus trigger layering

#### 3. `military_reversal`

Preferred:

- `war_event`
- `eclipse`
- `aries_ingress`

Allowed:

- `lunation`

Policy:

- this domain can legitimately read reversal pressure through retrograde, attritional, and activation logic across more than one chart family

#### 4. `war_conflict`

Policy:

- keep it only for backward compatibility
- de-emphasize it in UI
- avoid using it as the default war scan lens

## Technical Recommendations

### Immediate

1. Restrict or de-prioritize `war_outbreak` on non-`war_event` chart types in the UI.
2. Default war scans to:
   - `war_event + war_outbreak`
   - or `war_event + campaign_escalation`
3. Keep `aries_ingress + war_*` available only as framework-style research mode, not as the default war scan path.

### Runtime

1. Add chart-type penalties or hard gating to `war_outbreak` outside `war_event`.
2. Split scan presentation into:
   - `top_places`
   - `top_cells`
   so long flat plateaus do not masquerade as first-day spikes.
3. Apply war-theater scan bias only where doctrine supports it:
   - strongest on `war_event`
   - weaker or absent on framework charts

### Product

1. Present chart type first, then domain.
2. If a user chooses a war domain on a non-war chart:
   - show it as `framework` or `trigger` war reading
   - not as outbreak-localization by default

## Final Judgment

The answer is:

- war should not be forced into one single chart type only
- but war domains should be chart-type-specific in meaning

So:

- `war_event` should be the preferred and default chart type for outbreak-style war work
- `aries_ingress`, `lunation`, and `eclipse` should remain usable for war work
- but only with narrower, explicitly chart-appropriate war semantics

The present runtime is too permissive for `war_outbreak` and too tolerant of the umbrella `war_conflict` on long-range framework scans.
