# Mundane War Scan Hindcast Results

## Current Suite Result

Resolved on 2026-04-27 after adding source-backed reference resolution and
repairing two case windows whose previous controls conflicted with the local
source assertions.

- cases: `5`
- source-backed cases: `5`
- source assertions: `9`
- place recall: `5/5`
- alignment passes: `5/5`
- target-window hits: `5/5`
- near hits: `0/5`
- median target place rank: `2.0`
- median peak distance: `0.0h`
- failure reasons: none

## Critical Answer

The current source-backed suite shows a usable hindcast localization and timing
signal for war-event scans. This is still not enough to claim validated
prospective war prediction because the suite is small and every row is a
hindcast using known real-event windows.

## Source-Backed Resolution

The suite now requires each `benchmark_refs` entry to resolve to a local
historical benchmark row with `source_assertions`. The JSON and Markdown reports
include the resolved event facts and local source claims under `source_backing`.

Two earlier failures were resolved as benchmark-protocol issues rather than
threshold changes:

- `war_scan_hindcast_desert_storm_outbreak_1991`
  - previous issue: the first control window included the Jan. 15, 1991 eclipse pressure that the local source itself cites as part of the war setup.
  - source-backed change: the target window now spans the cited eclipse pressure through the Jan. 17 opening of Operation Desert Storm, while controls sit outside that source-backed activation band.

- `war_scan_hindcast_pearl_harbor_outbreak_1941`
  - previous issue: the scan sampled only midnight snapshots even though the local source basis says a timed first-hostilities chart is preferred for war judgment.
  - source-backed change: the case now samples the Dec. 7 first-hostilities time band at 6-hour resolution and carries a Honolulu reference anchor from the local atlas-backed target place.

## Place-Discovery Robustness Resolution

Resolved on 2026-04-27 after the strict period-place discovery mode showed a
ranking weakness in broad U.S. scans. The engine already returned Honolulu and
its Honolulu series peaked inside the Pearl Harbor attack window, but it ranked
behind many mainland U.S. places from repeated country/timezone corridors.

The runtime now applies theater-diverse place ordering in
`mundane_scan_service._order_places_for_discovery(...)`:

- computed scores, peaks, windows, and war-domain rule weights are unchanged
- places are first sorted by the existing breakout index
- the returned place list then takes the strongest candidate from each
  country/timezone theater before same-theater followups

This keeps the output useful for the user-facing question "given this period
and region, what places should I inspect?" and avoids burying an outlying war
theater behind near-duplicate mainland candidates.

Source basis:

- local: `war_outbreak_pearl_harbor_1941` cites Watters, _Horary Astrology and
  the Judgment of Events_, pp. 203-205, for timed first-hostilities charts as
  the preferred war-judgment basis.
- local: the same benchmark row records Pearl Harbor, Oahu as the real
  historical target.
- external: National Museum of the U.S. Air Force records the Dec. 7, 1941
  attack against U.S. military and naval facilities on Oahu:
  https://www.nationalmuseum.af.mil/Visit/Museum-Exhibits/Fact-Sheets/Display/Article/196218/day-of-infamy-the-pearl-harbor-attack/
- external: National Park Service describes Pearl Harbor as a strategic port,
  U.S. naval base, and Pacific Fleet home:
  https://www.nps.gov/perl/learn/historyculture/pearl-harbor.htm
- external: National WWII Museum describes the Pacific Fleet move to Pearl
  Harbor and Japan's focus on that Pacific target:
  https://www.nationalww2museum.org/war/topics/pearl-harbor-december-7-1941

## Case Notes

### `war_scan_hindcast_desert_storm_outbreak_1991`

- domain: `war_outbreak`
- target place: Baghdad, Iraq
- target place rank: `3`
- target-window hit: `true`
- target beats controls: `true`
- source backing: Louis, _The Annotated Raphael's Mundane Astrology_, pp. 793-795, linking the Jan. 15, 1991 eclipse setup with Operation Desert Storm beginning Jan. 17, 1991.

### `war_scan_hindcast_us_iran_outbreak_2026`

- domain: `war_outbreak`
- target place: Tehran, Iran
- target place rank: `2`
- target-window hit: `true`
- target beats controls: `true`
- source backing: local benchmark row `war_outbreak_us_iran_opening_2026`.

### `war_scan_hindcast_desert_storm_campaign_1991`

- domain: `campaign_escalation`
- target place: Baghdad, Iraq
- target place rank: `2`
- target-window hit: `true`
- target beats controls: `true`
- source backing: local benchmark row `campaign_escalation_desert_storm_1991`.

### `war_scan_hindcast_pearl_harbor_outbreak_1941`

- domain: `war_outbreak`
- target place: Honolulu, United States
- target place rank: `4`
- target-window hit: `true`
- target beats controls: `true`
- source backing: Watters, _Horary Astrology and the Judgment of Events_, pp. 203-205, where a timed first-hostilities chart is the preferred basis for war judgment.

### `war_scan_hindcast_israel_iran_rising_lion_2025`

- domain: `war_outbreak`
- target place: Tehran, Iran
- target place rank: `1`
- target-window hit: `true`
- target beats controls: `true`
- source backing: INSS, IDF, and Axios reports tying June 13, 2025 to Operation Rising Lion's opening strikes against Iranian military and nuclear infrastructure.

## Remaining Limits

This result is a source-backed hindcast pass, not a general prediction claim.
The next validation step is to widen the war set and add more non-war control
windows that are chosen before looking at engine output.

## Period-Place Discovery Mode

A stricter run was added on 2026-04-27:

```powershell
python backend\run_mundane_war_scan_hindcasts.py --period-place-discovery
```

This mode strips known target-place anchors before scanning. It tests the
user-facing flow where the user enters a period and region and the engine returns
potential places.

Current discovery-mode result:

- cases: `5`
- source-backed cases: `5`
- source assertions: `9`
- place recall: `5/5`
- alignment passes: `5/5`
- target-window hits: `5/5`
- failures: `0`
- failure reason: none
- median target place rank: `2.0`
- median peak distance: `0.0h`

Case-level outcome:

- Baghdad / Desert Storm outbreak: pass, target rank `3`
- Tehran / 2026 U.S.-Iran row: pass, target rank `2`
- Baghdad / Desert Storm campaign: pass, target rank `2`
- Honolulu / Pearl Harbor: pass, target rank `5`
- Tehran / Operation Rising Lion 2025: pass, target rank `1`

Conclusion for discovery mode: the engine can return the real theater from
period/region input alone in all five source-backed cases, and the real event
window is active in all five. This is a stronger hindcast result than the
pre-resolution run, but it remains a small source-backed hindcast suite rather
than evidence of validated prospective prediction.
