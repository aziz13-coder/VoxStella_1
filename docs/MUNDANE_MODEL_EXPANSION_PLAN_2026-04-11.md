# Mundane Model Expansion Plan

## Goal

Expand the mundane runtime by maturing thin current model families before adding new ones or splitting the strongest domains.

Phase 1 is complete.

Phase 2 is complete:

- `government_stability`
  - `leadership_transition`
  - `regime_stability`
- `war_conflict`
  - `war_outbreak`
  - `campaign_escalation`
  - `military_reversal`

Phase 3 is complete:

- `eclipse_degree_activation`
- `retrograde_mars`
- `mutation_and_conjunction_cycles`
- `angularity`

Phase 4 chart-context and polity expansion is now complete.

Phase 5 is now complete:

- `alliance_stress`
- `trade_and_commerce`
- `epidemic_wave_pressure`

## Expansion Order

### Phase 1: Mature thin current families

Start with:

- `diplomacy_foreign_affairs`
- `public_health`
- `civil_unrest`
- `finance_economy`

Acceptance gate for each:

- doctrine remains source-backed
- runtime rules reflect actual house/actor distinctions from the corpus
- benchmark packs exist and remain green after the rule change

### Phase 2: Split overloaded strong families

After Phase 1:

- split `government_stability` into:
  - `leadership_transition`
  - `regime_stability`
- split `war_conflict` into:
  - `war_outbreak`
  - `campaign_escalation`
  - `military_reversal`

Do not split early. Thin child models built from thin parents will drift fast.

### Phase 3: Promote trigger families into stronger reusable assets

Make the trigger families more explicit and reusable across domains:

- `eclipse_degree_activation`
- `retrograde_mars`
- `mutation_and_conjunction_cycles`
- `angularity`

This work should reduce duplicated trigger logic inside domain evaluators.

The Phase 3 implementation note is:

- `docs/MUNDANE_PHASE3_TRIGGER_PLAN_2026-04-11.md`

Phase 3 is now complete, so the next implementation note should be a dedicated Phase 4 chart-context plan rather than more trigger promotion work.

### Phase 4: Expand chart-context and polity coverage

Only after the domain layer is stronger:

- add more polity registry coverage
- add more source-proven national charts
- widen national-chart proving beyond the current core set

The active Phase 4 implementation note is:

- `docs/MUNDANE_PHASE4_CONTEXT_PLAN_2026-04-11.md`

### Phase 5: Add new domain families

Only after the source and benchmark gates are met:

- `alliance_stress`
- `trade_and_commerce`
- `epidemic_wave_pressure`

The active Phase 5 implementation note is:

- `docs/MUNDANE_PHASE5_DOMAIN_PLAN_2026-04-11.md`

Phase 5 has now completed with the first benchmark-backed new families:

- `alliance_stress`
- `trade_and_commerce`
- `epidemic_wave_pressure`

Phase 6 is now defined:

- `docs/MUNDANE_PHASE6_PLAN_2026-04-12.md`

## Post-Phase-5 Hardening

The active hardening note is:

- `docs/MUNDANE_POST_PHASE5_HARDENING_PLAN_2026-04-12.md`

The first hardening slice is now:

- `regime_stability` uplifted from narrow moderate coverage to supported coverage through France 1940 and France 1958
- `civil_unrest` uplifted to supported coverage with the addition of British India / Swadeshi unrest and sixth-house labor-union runtime logic

The hardening completion note is:

- `docs/MUNDANE_POST_PHASE5_HARDENING_COMPLETION_PLAN_2026-04-12.md`

The remaining direction after hardening is no longer more isolated families. It is Phase 6 composite synthesis across stabilized domain families.

Do not add weather, earthquake, or fixed-star catastrophe runtime families yet.

## Completed Phase 1 Expansions

- `diplomacy_foreign_affairs`
- `public_health`
- `civil_unrest`
- `finance_economy`

These domains now have widened runtime logic and materially broader benchmark packs. They remain research-gated, but they are no longer the thin edge of the current model family.

## Next Gate

Start Phase 5 only when the proposed family clears the existing maturity gate:

- source-backed doctrine
- benchmark pack
- honest runtime research flags and calibration

## Rule For Further Expansion

Do not add a new mundane model family unless all three are true:

1. source-backed doctrine exists
2. at least a seeded benchmark pack exists
3. runtime research flags and calibration can expose the model honestly
