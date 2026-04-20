# Mundane Custom Chart Input

## Purpose

Allow a user to run mundane analysis or scan workflows even when the selected polity has no curated national chart in the runtime registry.

This is an exploratory input path. It does not replace the curated polity registry.

## Input Modes

The mundane workspace now has two chart-source modes:

- `Registered`
- `Custom`

### Registered

Use the runtime polity registry and any registered national charts already attached to that polity.

This is the preferred path when:

- a source-backed national chart already exists
- the user wants a repeatable, curated baseline
- benchmark comparisons should stay tied to registry entities

### Custom

Use a user-supplied polity label and a user-supplied reference chart.

This is the correct path when:

- the polity is missing from the chart registry
- the polity exists but has no registered chart
- the user wants to test a disputed or provisional national chart
- research is exploratory rather than registry-backed

## Required Custom Fields

When `Custom` mode is selected, the workspace should collect:

- `custom_polity_label`
- `custom_chart_label` (optional)
- `custom_chart_datetime`
- `custom_chart_location`
- `custom_chart_timezone`

For chart types that require a polity, the polity label is required.

The chart label is optional. If omitted, the backend will assign a fallback label.

## Backend Behavior

The backend should prefer the custom chart over registry lookup whenever the required custom chart fields are present.

Custom charts are returned with explicit research flags:

- `user_supplied_chart`
- `unverified_chart_provenance`
- `not_registry_backed`

Custom polities are returned with:

- `user_supplied_polity`
- `not_registry_backed`

This applies to both:

- single-chart mundane analysis
- bounded mundane scans

## Product Rules

- Do not silently merge a custom chart into the permanent polity registry.
- Do not represent custom charts as verified or curated.
- Always keep the research flags visible in the response path.
- Keep curated registry charts and custom charts as separate concepts.

## Analysis Mode

In single-chart analysis:

- the custom chart acts as the reference chart overlay
- the event or active Astro Clock chart remains the event anchor when relevant
- the resulting doctrine and calibration output should still expose the custom-chart research flags

## Scan Mode

In scan mode:

- candidate locations and times vary per evaluated cell
- the custom chart remains the fixed overlay chart across the scan
- the user-supplied chart should not be treated as a registry-backed national chart

## UX Rules

- If a polity has no registered national chart, the UI should not dead-end the user.
- The UI should suggest switching to `Custom` mode.
- The UI should explain that custom mode is exploratory and research-flagged.

## Acceptance

This feature is considered complete when:

1. the backend accepts custom chart inputs in both analysis and scan requests
2. the frontend exposes a clear `Registered` / `Custom` toggle
3. the analysis and scan workspaces validate the required custom fields
4. the output path visibly preserves the custom research flags
