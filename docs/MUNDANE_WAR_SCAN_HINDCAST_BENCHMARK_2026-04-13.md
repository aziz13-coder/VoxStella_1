# Mundane War Scan Hindcast Benchmark

## Purpose

This suite tests the current mundane scan runtime against a small set of known war events and campaign windows.

It is intentionally narrower than the main mundane benchmark corpus:

- chart type: `war_event`
- domains:
  - `war_outbreak`
  - `campaign_escalation`
- output under test:
  - scan place-series localization
  - scan time-window concentration
  - control-window discrimination

It does **not** claim validated prospective war prediction.

## What It Measures

Each hindcast case runs a real scan and evaluates:

1. whether the expected target place survives into `series.places`
2. the target place rank inside the aggregated place-series output
3. whether the target window carries one of the stronger scores inside the matched place series
4. how far the selected peak sits from the target window
5. whether the target window beats matched non-event control windows

## Source-Backed Requirement

Every hindcast row must point to one or more historical benchmark rows through
`benchmark_refs`. Each referenced row is expected to carry local
`source_assertions` from the mundane benchmark corpus. The hindcast report must
therefore answer two questions together:

1. what real event/window is being tested
2. what local knowledge/source assertion backs that event/window and its
   expected mundane interpretation

Rows with unresolved references or references without source assertions should
fail validation. A green hindcast without event provenance is not useful.

## Pass / Partial / Fail Semantics

`alignment_passed` is strict: the target place must be returned, satisfy rank
and percentile thresholds, have a peak close enough to the real target window,
and beat all listed control windows.

The runner also has a stricter period-place discovery mode:

```powershell
python backend\run_mundane_war_scan_hindcasts.py --period-place-discovery
```

That mode strips known place anchors such as `reference_location`,
`reference_latitude`, `reference_longitude`, and `event_location` before running
the scan. It tests the user-facing shape where a user supplies a period, region,
chart type, and domain, then expects the engine to return candidate places. The
same target-place and target-window checks are applied afterward, but the scan
does not receive the target place as an input anchor.

## Algorithm Robustness Resolution

The period-place discovery result exposed a broad-region ranking weakness rather
than a missing war signal: Pearl Harbor/Honolulu was returned and peaked in the
real attack window, but it was buried behind repeated mainland U.S. places from
the same local chart corridor.

The source-backed resolution is a place-series ordering change, not a change to
the war-domain rule weights:

1. keep each place's computed score, breakout index, peak, and timing unchanged
2. sort places by the existing breakout signal
3. return the strongest place from each country/timezone theater first
4. append same-theater followups afterward in their original signal order

This is implemented in `mundane_scan_service._order_places_for_discovery(...)`.
It is meant for the user-facing scan question "given this period and region,
what places should I inspect?" A broad scan should not spend its first returned
slots on near-duplicate municipalities from one mainland meridian corridor when
an outlying theater also carries a live event-window signal.

Source basis:

- Local benchmark source: `war_outbreak_pearl_harbor_1941` points to Watters,
  _Horary Astrology and the Judgment of Events_, pp. 203-205, for the rule that
  a timed first-hostilities chart is the preferred war-judgment basis.
- Local benchmark source: the same row records Pearl Harbor/Oahu as the dated
  historical event target.
- External event source: the National Museum of the U.S. Air Force records the
  Dec. 7, 1941 attack as hitting U.S. military and naval facilities on Oahu:
  https://www.nationalmuseum.af.mil/Visit/Museum-Exhibits/Fact-Sheets/Display/Article/196218/day-of-infamy-the-pearl-harbor-attack/
- External site-source: the National Park Service describes Pearl Harbor as a
  strategic port, U.S. naval base, and Pacific Fleet home:
  https://www.nps.gov/perl/learn/historyculture/pearl-harbor.htm
- External strategic-context source: the National WWII Museum describes the
  Pacific Fleet's move from San Diego to Pearl Harbor and Japan's focus on that
  Pacific target:
  https://www.nationalww2museum.org/war/topics/pearl-harbor-december-7-1941

The report also carries diagnostic fields so failures can be resolved honestly:

- `source_backing`: local source assertions resolved from `benchmark_refs`
- `target_window_hit`: the selected place peak overlaps the real event window
- `near_hit`: the selected place peak is outside the target window but within
  the allowed distance
- `target_beats_all_controls`: the real window outscored the matched non-event
  controls for the same place
- `failure_reasons`: the exact rule or coverage failure to address

## Why This Exists

The existing mundane scan benchmarks answer operational questions:

- does the expected place survive into returned cells
- does the series payload have the expected shape

They do not answer the harder question:

- when we scan around a real war event, does the runtime recover the relevant theater and concentrate pressure in the event window better than nearby control windows

This suite fills that gap.

## Scope Limits

This benchmark is still a hindcast, not a true blind forecast test.

The current suite is limited to `war_event` because:

- local doctrine is strongest there for opening hostilities
- runtime policy already treats `war_outbreak` as chart-type-specific
- framework charts like `aries_ingress`, `lunation`, and `eclipse` are doctrinally narrower and should not be scored as if they were event-anchor outbreak scans

## Dataset Shape

Each JSONL row in `backend/benchmarks/mundane/war_scan_hindcast_cases.jsonl` includes:

- `enabled`
- `case_id`
- `label`
- `request`
- `target_window`
- `control_windows`
- `target_place_tokens_any`
- optional `target_country_codes_any`
- `scoring_expectations`
- `benchmark_refs`

### `request`

The request must be directly compatible with `build_scan_request(...)`.

### `target_window`

The expected event or campaign concentration window inside the scan window.

### `control_windows`

Matched non-event windows inside the same scan run. These are used to test whether the target window really stands out, instead of looking good only because the whole series is elevated.

### `scoring_expectations`

Current thresholds are intentionally modest:

- `max_target_place_rank`
- `min_target_percentile`
- `max_peak_distance_hours`

These thresholds should stay honest to the actual runtime behavior. They are not supposed to force a green benchmark through loose acceptance.

## Resolution Protocol

When this suite fails, resolve in this order:

1. Confirm the event source backing is present and points to the correct real
   event/window.
2. Check whether the target place is absent, low-ranked, or timing-only weak.
3. Check whether control windows outperform the target window.
4. Patch source/runtime logic only where the failure has a local knowledge basis
   in the referenced source assertions or domain rules.
5. Re-run the hindcast and keep the critical answer cautious unless both place
   localization and timing/control discrimination improve.

## Expected Interpretation

The critical answer from this suite should be read as:

- scan localization / timing concentration around known war events

not as:

- proof of standalone prospective war prediction

If this suite performs badly, the right conclusion is that the war scan runtime is still weak at theater localization and event-window concentration.

If it performs moderately, the right conclusion is still only that the runtime shows some hindcast signal.

## Next Steps After This Suite

If the suite shows real signal:

- widen case count
- add more matched control windows
- test `campaign_escalation` more broadly

If the suite shows weak signal:

- inspect place-atlas coverage
- inspect war-event locality semantics
- inspect raw-cell versus place-series ranking behavior
- inspect chart-type / domain leakage
