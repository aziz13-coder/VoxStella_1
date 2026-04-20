# Astrocartography Workflow Draft

Date: 2026-04-04

## Purpose

This memo sketches the product workflow for the Astrocartography feature using two explicit chart contexts:

- a natal base chart selected from a saved snap
- an optional transit chart using the same input structure already used in Astro Clock

This is a workflow draft, not a final implementation contract.

## Core Product Decision

The Astrocartography workflow should be split into two layers:

- `Natal source`: selected from a saved snap
- `Transit context`: seeded from the current Astro Clock state and editable with Astro Clock-style controls

This means:

- the natal chart is not typed manually inside Astrocartography in V1
- the user must choose a saved snap as the natal source
- the transit chart uses the familiar Astro Clock input grammar:
  - `Mode`
  - `Date`
  - `Time`
  - `Location`
  - `Apply`
  - `Refresh`

## Why This Shape Fits The Existing App

It matches the current Astro Clock architecture already visible in source:

- Astro Clock already has saved snaps and snap loading
- Astro Clock already has manual transit context inputs
- `TransitsModal` already accepts a seed object with:
  - `snapId`
  - `date`
  - `time`
  - `location`
  - `timezone`
  - `houseSystem`
- `TransitsModal` already supports:
  - `Saved Snap` natal source
  - `Manual Natal` fallback

For Astrocartography, the first release should be stricter:

- require `Saved Snap` for natal
- reuse the Astro Clock manual controls only for the transit layer

That keeps the geometry reliable and prevents users from entering incomplete natal data in a map feature that depends on precise birth context.

## Context Model

### 1. Natal source

Required.

Proposed shape:

```json
{
  "sourceMode": "snap",
  "snapId": "123",
  "label": "Napoleon Natal",
  "effectiveDatetime": "1769-08-15T11:30:00Z",
  "location": "Ajaccio, Corsica, France",
  "timezone": "Europe/Paris",
  "houseSystem": "R"
}
```

Rules:

- exactly one natal snap must be active
- no map computation runs until a natal snap is selected
- changing the natal snap resets map overlays, inspected cities, and compare results

### 2. Transit context

Optional at first load, but required when the user switches into transit mode.

Proposed shape:

```json
{
  "mode": "realtime",
  "date": "2026-04-04",
  "time": "13:30",
  "location": "Jerusalem, Israel",
  "timezone": "Asia/Jerusalem",
  "houseSystem": "R"
}
```

Rules:

- this should be seeded from the active Astro Clock context when the feature opens
- the user can switch between `Realtime` and `Manual`
- in `Manual`, the user edits `Date`, `Time`, and `Location`
- `Apply` freezes the transit context into a map-ready timestamp
- `Refresh` re-pulls the active transit layer without changing the natal base

## Main Mode Structure

The feature should expose a clear top-level mode switch:

- `Natal`
- `Transit`

### Natal mode

Shows:

- natal astrocartography lines from the selected snap
- city inspection
- compare cities
- relocation chart for the selected city
- crossings/parans

This is the default mode.

### Transit mode

Shows:

- the same natal base chart still anchored to the selected snap
- transit context controls using the current Astro Clock input pattern
- transit activation overlays or transit-sensitive location analysis
- the selected timestamp and location for the active transit layer

Important product rule:

- transit mode does not replace the natal source
- transit mode adds a time-sensitive overlay on top of the natal base

## Proposed User Workflow

### Flow 1: Open Astrocartography

1. User opens `Astro Clock`.
2. User clicks `Astrocartography`.
3. The feature opens as a modal or dedicated workspace panel.
4. If no saved snaps exist, the feature shows:
   - `No natal snaps available`
   - `Create a snap in Astro Clock first`

### Flow 2: Select Natal Source

1. The first required action is `Choose Natal Snap`.
2. The left rail shows a snap picker populated from Astro Clock saved snaps.
3. After selection, the map loads natal angular lines.
4. The map header confirms:
   - snap label
   - natal timestamp
   - natal birthplace

This is the minimum state needed before the user can do anything else.

### Flow 3: Work In Natal Mode

1. The mode defaults to `Natal`.
2. The user searches a city or clicks the map.
3. The inspector shows:
   - nearest lines
   - distances
   - line meanings
   - nearby crossings/parans
   - relocation summary
4. The user can add cities into a compare tray.

### Flow 4: Switch To Transit Mode

1. The user clicks `Transit`.
2. The natal snap remains fixed.
3. A transit setup card appears using the Astro Clock control pattern:
   - `Mode: Realtime | Manual`
   - `Date`
   - `Time`
   - `Location`
   - `Apply`
   - `Refresh`
4. The transit card is prefilled from the active Astro Clock context.
5. After `Apply`, the map updates with the transit layer.

### Flow 5: Inspect A City In Transit Mode

1. The user selects a city already on the map or searches a new one.
2. The inspector now shows two grouped readings:
   - `Natal baseline`
   - `Transit activation`
3. The compare view can optionally show:
   - baseline natal strengths
   - what is currently activated by transit

## Proposed UI Layout

### Left rail

- `Natal Snap` selector
- `Mode` switch: `Natal` / `Transit`
- transit setup card
- planet toggles
- angle toggles
- radius controls
- city search

### Center

- world map
- natal lines
- optional transit overlay
- city markers
- crossing markers

### Right rail

- selected city inspector
- nearest lines
- interpretation cards
- relocation summary
- compare tray

## Key Interaction Rules

### Rule 1: Natal snap is required

No astrocartography map should load without a selected natal snap.

### Rule 2: Transit depends on natal, not the other way around

Transit mode is an overlay workflow.

The user must never feel that the transit context has become the new natal base.

### Rule 3: Reuse Astro Clock control grammar

The transit setup should feel familiar to existing users.

Do not invent a second transit input pattern for Astrocartography when Astro Clock already has one.

### Rule 4: Seed from current context

When Astrocartography opens, its transit card should be seeded from the same active state currently used to seed `TransitsModal`.

This reduces duplicate typing and makes the feature feel connected to the rest of Astro Clock.

### Rule 5: Snapshot behavior inside the feature

Once the user applies a manual transit context, the feature should behave as a frozen snapshot until they change it again.

Do not let the map drift silently while the user is reading location results.

## Recommended First-Pass State Contract

```json
{
  "natalSource": {
    "sourceMode": "snap",
    "snapId": "",
    "label": "",
    "effectiveDatetime": "",
    "location": "",
    "timezone": "",
    "houseSystem": "R"
  },
  "viewMode": "natal",
  "transitContext": {
    "mode": "realtime",
    "date": "",
    "time": "",
    "location": "",
    "timezone": "",
    "houseSystem": "R"
  },
  "targets": [],
  "selectedTarget": null
}
```

## Recommended Backend Contract Direction

The frontend should pass two explicit context groups:

- natal source
- transit context

Suggested endpoint behavior:

- natal-only endpoints require `natal_snap_id`
- transit-aware endpoints require:
  - `natal_snap_id`
  - `transit_datetime`
  - optional transit location/timezone when relevant

This keeps the API aligned with the product mental model.

## Product Copy Recommendation

Use labels like:

- `Natal Snap`
- `Transit Context`
- `Use current Astro Clock time`
- `Manual transit time`
- `Apply transit`
- `Natal baseline`
- `Transit activation`

Avoid labels that blur the two chart layers together.

## Recommended V1 Scope

Include:

- required natal snap picker
- natal map
- transit mode toggle
- Astro Clock-style transit input card
- city inspector
- compare tray

Do not include yet:

- manual natal entry inside Astrocartography
- full local-space workflow
- global place ranking

## Main Product Benefit

This workflow gives Astrocartography a strong internal logic:

- the natal chart comes from a trusted saved chart object
- the transit chart feels native to Astro Clock
- the user always knows which layer is fixed and which layer is time-sensitive

That is the right foundation for the next implementation pass.
