# Mundane Phase 2 Split Plan

## Goal

Split the overloaded strong domains into narrower runtime lenses without breaking the existing frontend or benchmark calibration path.

The first Phase 2 split is complete:

- `government_stability`
  - `leadership_transition`
  - `regime_stability`

`government_stability` remains in the runtime as a compatibility umbrella while the split domains mature.

The active second Phase 2 split is:

- `war_conflict`
  - `war_outbreak`
  - `campaign_escalation`
  - `military_reversal`

`war_conflict` remains in the runtime as a compatibility umbrella while the split domains mature.

## Why This Split Is Safe Now

Phase 1 is complete for the thinner domains:

- `diplomacy_foreign_affairs`
- `public_health`
- `civil_unrest`
- `finance_economy`

That means the strongest remaining compression is now inside the government lens itself:

- monarch or executive death
- accession and coronation disruption
- cabinet or executive continuity
- parliamentary and institutional instability

Those are not the same thing, and the current umbrella domain hides that distinction.

## Scope

### `leadership_transition`

Use for:

- monarch death
- succession disruption
- coronation / inauguration disturbance
- accession under affliction
- leadership crisis centered on the office-holder rather than the regime structure

Primary doctrinal emphasis:

- Sun and luminaries
- tenth-house ruler
- angular visibility of authority points
- retrograde and activation pressure attached to leadership events

### `regime_stability`

Use for:

- cabinet durability
- parliamentary crisis
- constitutional strain
- institutional blockage
- regime or governing-system instability beyond one office-holder

Primary doctrinal emphasis:

- tenth and eleventh houses
- capital-chart preference
- malefic pressure on authority or parliamentary structures
- activation hits that sharpen institutional stress

### `government_stability`

Keep as:

- backward-compatible umbrella lens
- merged output when the UI or an older saved request still asks for `government_stability`

It should combine the split rule families while exposing research flags that it is now a compatibility umbrella rather than the preferred fine-grained lens.

## Benchmark Migration Rule

Do not drop the old umbrella domain immediately.

Instead:

- move leadership-oriented rows into `leadership_transition`
- add a dedicated `regime_stability_cases.jsonl`
- keep `government_stability_cases.jsonl` as a compatibility umbrella pack during the transition

This preserves calibration for the existing domain while allowing the new split domains to build their own benchmark profiles.

## Implementation Sequence

1. Add runtime metadata for `leadership_transition` and `regime_stability`.
2. Add doctrine notes for both split domains.
3. Split the evaluator in `backend/mundane_domain_rules.py`.
4. Route the new domains in `evaluate_domain_context`.
5. Migrate benchmark rows and add `regime_stability_cases.jsonl`.
6. Keep `government_stability` alive as a merged compatibility evaluator.
7. Verify benchmark calibration and API catalog output.

## Acceptance Gate

Phase 2 split 1 is complete when:

1. the runtime catalog exposes `leadership_transition` and `regime_stability`
2. both new domains have their own benchmark-backed calibration profile
3. `government_stability` still works for older requests
4. tests and benchmark runners remain green

Phase 2 split 2 is complete when:

1. the runtime catalog exposes `war_outbreak`, `campaign_escalation`, and `military_reversal`
2. all three split domains have their own benchmark-backed calibration profile
3. `war_conflict` still works as a compatibility umbrella for older requests and scan flows
4. the benchmark, API, and scan test suites remain green
