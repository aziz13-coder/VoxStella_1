# Business Beta Certified Extraction Pass

Date: `2026-04-18`

## Scope

This pass moves the repo business beta flow closer to the Galaxy business source note while keeping the participant snap model unchanged.

## Key Decision

For this implementation pass, selected business beta participant charts are treated as `certified`.

That means the backend keeps these founder-fit branches active:

- Ascendant-to-Ascendant resonance
- participant Asc ruler support/strain to the event Moon
- event Fortuna contact to participant Ascendant
- participant Asc-ruler placement in the event houses

This was implemented as a runtime assumption inside the business beta path, not as a snap schema change.

## What Changed

### 1. Runtime participant precision context

Business beta participant bundles now carry an internal precision context:

- `precision_class = certified`
- `precision_safe = true`
- `precision_source = business_beta_certified_override`

This preserves a clean hook for future non-certified gating without expanding snap storage now.

### 2. Per-line favorable / tense channels

Business beta line payloads now expose:

- `score`
- `favorable`
- `tense`
- participant precision metadata where relevant

These channels are used by post-scan extraction.

### 3. Line-aware post-scan extraction

The election stream now supports business beta extraction controls:

- `business_beta_display_mode = total | detail`
- `business_beta_scope = all | current | selected`
- `business_beta_current_line_id`
- repeated `business_beta_selected_line_id`
- `business_beta_level_percent`

Per-line thresholds are derived as:

```text
threshold = max(fmax, abs(fmin)) * level_percent / 100
```

Where:

- `fmax` is the maximum net line score seen in the scan
- `fmin` is the minimum net line score seen in the scan

Extraction rules:

- `Show total`: selected line `score >= threshold`
- `Show detail`: selected line `favorable >= threshold`
- `all` / `selected`: all chosen lines must pass at the same minute
- `current`: only the active line must pass

Minutes that pass are grouped into contiguous business beta periods, and top windows are now taken from those extracted periods instead of the old aggregate-only rank.

## UI Notes

The business beta modal now exposes:

- `Show total`
- `Show detail`
- `All lines`
- `Current line`
- `Selected subset`
- threshold percent

It also displays:

- extracted periods
- selected-line signal instead of only aggregate score
- aggregate score as a secondary debug metric
- per-line favorable / tense values
- certified founder-chart labeling

## Non-Goals Of This Pass

- no snap schema migration
- no participant precision classifier
- no attempt to claim exact Galaxy coefficient parity where the source note is silent
