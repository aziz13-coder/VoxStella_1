# Mundane Runtime Workflow Audit

Date: 2026-04-13

## Purpose

This memo describes the current mundane runtime as it exists in source now:

- user workflow
- backend workflow
- current inputs
- current outputs
- scan path
- main agreements with the local source corpus
- main divergences and open technical issues

This is a current-state audit, not a plan.

## 1. Current User Workflow

The current frontend workflow is chart-type first, domain second.

### Analysis mode

1. Load the mundane catalog.
2. Choose chart type.
3. Choose domain lens from the allowed list for that chart type.
4. Choose chart source:
   - registered polity/national-chart path
   - custom chart path
5. Choose polity context / location context.
6. Optionally provide event datetime, event location, reference location, visibility scope, and source preference.
7. Resolve context.
8. Analyze context.

### Scan mode

1. Load the mundane scan catalog.
2. Choose chart type.
3. Choose domain lens from the allowed list for that chart type.
4. Choose chart source and polity context.
5. Choose scan mode, region, resolution, candidate limit, and minimum score.
6. Choose either:
   - fixed datetime for spatial scan
   - start/end/time-step for time scans
7. Run scan.
8. View either:
   - ranked returned cells
   - place-time breakout graph

## 2. Current Runtime Surface

### Chart types

The runtime currently exposes 5 chart types:

- `aries_ingress`
- `lunation`
- `eclipse`
- `war_event`
- `national_chart`

### Domain lenses

The runtime currently exposes 14 domain lenses:

- `war_conflict`
- `war_outbreak`
- `campaign_escalation`
- `military_reversal`
- `government_stability`
- `leadership_transition`
- `regime_stability`
- `alliance_stress`
- `trade_and_commerce`
- `epidemic_wave_pressure`
- `diplomacy_foreign_affairs`
- `public_health`
- `civil_unrest`
- `finance_economy`

### Scan-enabled chart types

Scan is narrower than analysis. It currently supports only:

- `war_event`
- `eclipse`
- `lunation`
- `aries_ingress`

`national_chart` is analysis-enabled but not scan-enabled.

## 3. Current Input Contract

### Analysis input

The normalized analysis request is `MundaneContextRequest`.

Current fields:

- `chart_type`
- `domain`
- `polity_id`
- `custom_polity_label`
- `location_context_type`
- `reference_location`
- `reference_latitude`
- `reference_longitude`
- `event_datetime`
- `event_location`
- `event_timezone`
- `national_chart_id`
- `custom_chart_label`
- `custom_chart_datetime`
- `custom_chart_location`
- `custom_chart_timezone`
- `visibility_scope`
- `source_preference`

The active Astro Clock state is passed separately as `ActiveClockContext`:

- `timestamp`
- `location`
- `timezone`
- optional `mode`
- optional `house_system_code`
- optional `latitude`
- optional `longitude`

### Scan input

The normalized scan request is `MundaneScanRequest`.

It contains the full `MundaneContextRequest`, plus:

- `scan_mode`
- `region_id`
- `resolution`
- `top_k`
- `minimum_score`
- `candidate_limit`
- `fixed_datetime`
- `start_datetime`
- `end_datetime`
- `time_step_hours`

## 4. Current Backend Workflow

### Analysis path

The current analysis path is:

1. `get_runtime_catalog()`
   - returns chart types, domains, polities, context types, trigger families, source index, and chart-type/domain policy
2. `build_context_request()`
   - normalizes request args into `MundaneContextRequest`
3. `resolve_context()`
   - validates chart type and domain
   - resolves polity alias and polity record
   - resolves national chart selection
   - resolves event/reference context
   - resolves the actual chart bundle via chart-type rules
4. `analyze_context()`
   - computes domain assessment
   - builds framework layer
   - builds trigger layer
   - builds activation layer
   - computes trigger profiles
   - packages doctrine and research blocks

### Chart resolution path

Chart resolution is chart-type-specific.

- `aries_ingress`
  - annual framework chart
  - capital/polity context
  - angular hits
  - Jupiter-Saturn cycle backdrop
- `lunation`
  - nearest lunation trigger chart
  - shorter trigger layer
  - cycle backdrop
- `eclipse`
  - nearest eclipse chart
  - node-orb handling
  - eclipse-degree activation hits
  - cycle backdrop
- `war_event`
  - event anchor chart
  - aggressor/defender axis logic
  - angular war signatures
- `national_chart`
  - curated polity chart foundation
  - later triggers expected as overlays

### Trigger profile path

Trigger families are now explicit runtime assets, not just notes.

Current trigger profiles:

- `angularity`
- `retrograde_mars`
- `eclipse_degree_activation`
- `mutation_and_conjunction_cycles`

## 5. Current Output Contract

### Analysis output

Current top-level analysis output keys:

- `context`
- `framework_layer`
- `trigger_layer`
- `activation_layer`
- `trigger_profiles`
- `domain_assessment`
- `doctrine`
- `research`

Current `domain_assessment` keys:

- `domain_id`
- `score`
- `raw_score`
- `level`
- `raw_level`
- `summary`
- `matched_rules`
- `cautions`
- `research_flags`
- `calibration`
- `axis`

### Scan output

Current top-level scan output keys:

- `scan_mode`
- `region`
- `resolution`
- `request`
- `counts`
- `scan_calibration`
- `results`
- `failures`
- `research_mode`
- `runtime_scope`
- optional `series`

Current `results` row keys:

- `rank`
- `location`
- `datetime`
- `score`
- `raw_score`
- `level`
- `raw_level`
- `scan_score`
- `scan_level`
- `scan_level_reason`
- `relative_score_ratio`
- `delta_from_top`
- `scan_bias`
- `scan_bias_reason`
- `scan_anchor_distance_km`
- `summary`
- `matched_rules`
- `primary_signals`
- `calibration`
- `research_flags`
- `primary_chart`

Current `series` keys:

- `timeline`
- `places`
- `breakout_candidates`
- `series_overview`

## 6. Current Scan Workflow

The scan path is:

1. Build `MundaneScanRequest`.
2. Validate chart type, region, scan mode, time bounds, slice limits, and evaluated-cell bounds.
3. Resolve atlas candidates for the chosen region/resolution.
4. For each candidate/time cell:
   - build a candidate-specific context request
   - resolve chart context
   - analyze domain context
   - build scan row
   - optionally apply war-event theater bias
5. Sort all kept rows by scan sort key.
6. Return:
   - raw ranked top cells
   - relative scan levels
   - optional series aggregation by place

### Current scan modes

- `spatial_scan`
- `spatiotemporal_scan`
- `long_range_async_scan`

### Important scan behavior

- scan currently ranks raw cells first
- graph view aggregates by place afterwards
- long flat plateaus are now midpoint-aware in the series layer
- raw top-cell ranking can still look early or repetitive in long plateaus

## 7. Strong Agreements With The Local Sources

### A. The runtime is chart-class first

This matches the local doctrine strongly.

The source corpus says mundane work is not one chart method. It is a family of chart classes and timing structures. The runtime follows that:

- annual framework chart types
- trigger chart types
- event-anchor chart types
- polity foundation chart types

This is one of the runtime's strongest design choices.

### B. Timing is layered

The local doctrine says mundane timing should separate:

- framework
- trigger
- activation
- cycle background

The runtime now does that directly:

- `framework_layer`
- `trigger_layer`
- `activation_layer`
- trigger profiles
- cycle context

This is a strong source alignment.

### C. Domain models are separate, not one universal mundane score

The local doctrine supports public-domain models more defensibly than one single universal score.

The runtime follows that:

- war families are split
- government families are split
- diplomacy, finance, public health, civil unrest, trade, alliance, epidemic-wave are separate
- compatibility umbrellas remain available but are explicitly marked as umbrellas

### D. Locality is layered, not one simple map point

The local doctrine supports several locality frames:

- event place
- national chart
- capital chart
- eclipse visibility / territorial relevance
- polity fallback logic

The runtime does preserve multiple locality frames:

- event chart context
- capital chart context
- national chart context
- polity-specific visibility scope metadata
- period-aware national chart selection

### E. Trigger promotion is explicit and benchmark-aware

The local doctrine says strong triggers should be benchmarked before being promoted.

The runtime reflects that posture:

- trigger families are explicit
- benchmark and research status remain attached
- trigger families are reused across domains instead of duplicated loosely

## 8. Main Divergences From The Local Sources

### A. Revolution framework is still thinner than the doctrine

The doctrine does not stop at Aries ingress, lunation, eclipse, war event, and national chart.

The local sources also support broader revolution hierarchy and capital-based framework reading. The current runtime is strongest on:

- Aries ingress
- lunation
- eclipse
- war event
- national chart

But it is still thinner than the full doctrinal revolution structure.

### B. Eclipse visibility is only partially implemented

The doctrine is strong here:

- eclipses matter most where visible
- visible eclipses plus angularity matter most
- territorial relevance matters

The current runtime does carry:

- `visibility_scope`
- eclipse chart selection
- eclipse-degree activation

But it does not yet appear to implement a true geographic visibility engine or territorial eclipse weighting. In practice the runtime is still closer to:

- eclipse chart + node/orb handling + activation hits

than to full visibility-zone doctrine.

### C. `war_outbreak` is still too permissive outside `war_event`

The local doctrine and the policy memo both imply:

- `war_event` should be the preferred opening-hostilities chart
- `aries_ingress`, `lunation`, and `eclipse` should be used for framework/trigger/escalation work

The runtime does give `war_event` a specific outbreak advantage, but non-war chart types can still generate meaningful `war_outbreak` scores through generic martial and polarity logic. So the code is directionally correct, but still looser than the policy.

### D. Scan still favors returned cells before place semantics

The graph layer is closer to doctrinal layered timing than the raw result list is.

The raw scan still returns:

- top cells first

and only then builds:

- place-series breakout behavior

That means framework charts can still visually read like outbreak localization if the user looks only at returned cells. This is a technical workflow issue, not a doctrine issue.

### E. `national_chart` is not scan-enabled

The doctrine treats national charts as a first-class mundane frame. The current runtime supports them for analysis, but not for scan.

That is a deliberate technical limitation, but still a real gap relative to the source doctrine.

## 9. Current Technical Weak Spots

### A. Analysis and scan semantics are stronger than raw ranking semantics

The analysis path is more doctrinally coherent than the scan ranking path.

Why:

- analysis keeps framework/trigger/activation separation
- scan compresses many evaluated cells into one ranked list
- graph view partially repairs that by re-aggregating place series

### B. Compatibility umbrellas remain operationally convenient but semantically blurry

This applies especially to:

- `war_conflict`
- `government_stability`

They remain useful for backward compatibility and scan workflows, but they are weaker doctrinally than the split families.

### C. Scan chart-type support is narrower than the analysis chart-type surface

This is technically manageable, but it means the product presents a broader model universe in analysis than in scan.

### D. Visibility, territorial relevance, and disputed-chart handling are still shallower than the doctrine corpus

The runtime has improved these areas, but the sources still support more nuance than the code currently carries.

## 10. Current-State Conclusion

The mundane runtime is in a materially better state than an undifferentiated "mundane score" engine.

Its strongest current qualities are:

- chart-class-first architecture
- layered timing architecture
- explicit trigger profiles
- split public-domain models
- period-aware national-chart handling
- scan graph aggregation on top of raw cell evaluation

Its main current weaknesses are:

- incomplete eclipse visibility implementation
- thinner revolution hierarchy than the doctrine corpus
- outbreak semantics still too permissive outside `war_event`
- raw scan ranking still able to obscure place-level or framework-level meaning
- national-chart analysis stronger than national-chart scan support

In source terms, the runtime is already aligned with the main doctrinal architecture. The remaining problems are mostly:

- enforcement
- narrowing
- deeper locality implementation
- clearer separation between opening-event logic and broader framework logic

## 11. Immediate Questions For The Next Pass

If the next step is model correction rather than more UI work, the most important questions are:

1. Should `war_outbreak` be hard-restricted or sharply down-weighted outside `war_event`?
2. Should scan output prioritize `top_places` alongside `top_cells` by default?
3. Should `national_chart` become scan-enabled?
4. Should eclipse handling gain actual visibility-zone logic before more eclipse-domain weighting is added?
5. Should compatibility umbrellas be de-emphasized further in runtime scoring as well as UI?
