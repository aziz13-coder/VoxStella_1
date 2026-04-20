# Mundane Post-Phase-5 Hardening Plan

Status date: 2026-04-12

## Purpose

Phase 5 added the first new domain families. The next clean move is not another new family. It is benchmark and runtime hardening of the still-thin domains that remain vulnerable to narrow historical shape.

## Current Hardening Targets

1. `regime_stability`
   - Add non-British, non-monarchical institutional-crisis cases.
   - Tighten runtime logic around parliamentary adverse votes, ministerial resignation, and regime-level collapse.
   - Target state after this slice: `supported`.

2. `civil_unrest`
   - Add non-British unrest beyond the existing United Kingdom and United States material.
   - Tighten runtime logic around worker, union, and strike unrest instead of only the 1st/4th/10th/11th public axis.
   - Target state after this slice: `supported`.

## First Hardening Slice

### Regime stability

- Add France 1940 collapse as an explicit regime-collapse case.
- Add France Fourth Republic collapse in 1958 as a source-seeded constitutional-crisis case.
- Preserve both the parliamentary and executive-collapse side of the doctrine.

### Civil unrest

- Add British India / Swadeshi unrest from 1905-1908 as a non-British reform-and-strike case.
- Preserve the distinction between reform agitation, strike pressure, and direct riot language.

## Runtime Hardening

The runtime changes for this slice should stay narrow:

- `regime_stability`
  - stronger eleventh-house parliamentary crisis handling
  - explicit Saturn/Uranus/Neptune logic for adverse votes, cabinet rupture, and collapse pressure

- `civil_unrest`
  - sixth-house labor, union, and strike handling
  - keep 1st/4th/10th/11th public-axis logic as the main frame

## Completion Gate For This Slice

This first post-Phase-5 hardening slice is complete when all are true:

1. `regime_stability` reaches `supported` coverage.
2. `civil_unrest` reaches `supported` coverage.
3. new cases are backed by local doctrine plus local anchor notes for external historical facts.
4. benchmark validation stays at `0` citation failures.

## Remaining Hardening After This Slice

After the first slice, keep hardening in this order:

1. `alliance_stress`
2. `trade_and_commerce`
3. `epidemic_wave_pressure`

Do not add a new domain family before these hardening passes are materially improved.
