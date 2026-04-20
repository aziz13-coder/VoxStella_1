# Mundane Chart-Type Domain Policy

Date: 2026-04-12

## Purpose

The frontend chooses `chart type` first and `domain lens` second. The catalog therefore needs an explicit policy for which lenses are preferred for each chart type.

This policy does not hard-break old API requests. It changes the runtime catalog and the frontend defaults so the UI stops presenting semantically flat combinations as if they were equally valid.

## Core Rule

- `chart type` defines the chart's job
- `domain lens` defines the question asked of that chart

The lens list should therefore be filtered by the selected chart type.

## Policy Matrix

### `war_event`

Preferred:
- `war_outbreak`
- `campaign_escalation`
- `military_reversal`

Supported:
- `war_conflict`
- `diplomacy_foreign_affairs`
- `alliance_stress`
- `leadership_transition`
- `regime_stability`
- `civil_unrest`

Discouraged:
- `public_health`
- `epidemic_wave_pressure`
- `finance_economy`
- `trade_and_commerce`

Default lens:
- `war_outbreak`

### `aries_ingress`

Preferred:
- `regime_stability`
- `leadership_transition`
- `civil_unrest`
- `finance_economy`
- `trade_and_commerce`
- `public_health`
- `epidemic_wave_pressure`
- `diplomacy_foreign_affairs`
- `alliance_stress`
- `campaign_escalation`
- `military_reversal`

Supported:
- `government_stability`
- `war_conflict`

Discouraged:
- `war_outbreak`

Default lens:
- `regime_stability`

### `lunation`

Preferred:
- `civil_unrest`
- `public_health`
- `epidemic_wave_pressure`
- `leadership_transition`
- `diplomacy_foreign_affairs`
- `alliance_stress`
- `campaign_escalation`
- `military_reversal`

Supported:
- `regime_stability`
- `finance_economy`
- `trade_and_commerce`
- `war_conflict`
- `government_stability`

Discouraged:
- `war_outbreak`

Default lens:
- `civil_unrest`

### `eclipse`

Preferred:
- `regime_stability`
- `leadership_transition`
- `public_health`
- `epidemic_wave_pressure`
- `civil_unrest`
- `campaign_escalation`
- `military_reversal`

Supported:
- `diplomacy_foreign_affairs`
- `alliance_stress`
- `finance_economy`
- `trade_and_commerce`
- `war_conflict`
- `government_stability`

Discouraged:
- `war_outbreak`

Default lens:
- `regime_stability`

### `national_chart`

Preferred:
- `regime_stability`
- `leadership_transition`
- `civil_unrest`
- `finance_economy`
- `trade_and_commerce`
- `public_health`
- `epidemic_wave_pressure`
- `diplomacy_foreign_affairs`
- `alliance_stress`

Supported:
- `campaign_escalation`
- `military_reversal`
- `war_conflict`
- `government_stability`

Discouraged:
- `war_outbreak`

Default lens:
- `regime_stability`

## Design Consequence

The frontend should:

1. load the full catalog
2. select the chart type
3. show only preferred and supported domain lenses for that chart type
4. default to the chart type's preferred default lens
5. avoid presenting discouraged combinations as normal first-class choices

## Why This Exists

The war research pass showed that chart families are not interchangeable:

- `war_event` is the preferred anchor for `war_outbreak`
- `aries_ingress` is a framework chart
- `lunation` is a short trigger
- `eclipse` is an intensified activation chart
- `national_chart` is a polity foundation chart

The domain lens must therefore be chart-type-aware, especially for war semantics.
