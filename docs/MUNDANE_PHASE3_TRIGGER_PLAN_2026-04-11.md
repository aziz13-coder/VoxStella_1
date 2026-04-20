# Mundane Phase 3 Trigger Promotion Plan

## Goal

Promote the trigger families from passive runtime metadata into computed reusable trigger assets.

Phase 2 is complete:

- `government_stability`
  - `leadership_transition`
  - `regime_stability`
- `war_conflict`
  - `war_outbreak`
  - `campaign_escalation`
  - `military_reversal`

The active target is now Phase 3:

- `eclipse_degree_activation`
- `retrograde_mars`
- `mutation_and_conjunction_cycles`
- `angularity`

## Why This Phase Is Next

The split domains are now precise enough that the main duplication risk has shifted into trigger logic:

- eclipse-degree activation is checked in multiple domains
- retrograde Mars is repeated as a warning trigger across war, leadership, and unrest
- angularity is recalculated repeatedly and only exposed indirectly through matched rules
- mutation and conjunction cycles exist as doctrine and benchmark language but are only partially computed, so they need direct runtime backdrop logic instead of remaining static background metadata

The next precision gain is to make these trigger families reusable runtime assets so domains can consume shared trigger state rather than duplicating trigger detection piecemeal.

## Scope

### Computed trigger profiles

Add computed trigger profiles to the analysis payload.

Each profile should expose:

- `id`
- `label`
- `status`
- `active`
- `strength`
- `summary`
- `source_tags`
- `research_flags`
- `evidence`
- `metrics`

### Initial trigger families

#### `angularity`

Expose:

- strongest angular planets
- malefic angular count
- benefic angular count
- nearest-angle distances for the strongest testimonies

#### `retrograde_mars`

Expose:

- whether Mars is retrograde
- house position
- whether Mars rules a conflict house
- whether the trigger is active, cautionary, or inactive

#### `eclipse_degree_activation`

Expose:

- activation hit count
- strongest orb
- activating planets
- whether the trigger is actively present or only being watched

#### `mutation_and_conjunction_cycles`

Expose:

- nearest Jupiter-Saturn conjunction backdrop relative to the chart anchor
- cycle phase and conjunction sign
- whether the chart sits inside a configured turning window
- whether the trigger is currently active or only background-weighted

This should remain an honest backdrop asset. It can intensify finance and unrest domains, but it should not masquerade as a short-term event timer.

## Runtime Behavior

The trigger profiles should be used in two places:

1. analysis payload output
2. domain evaluation reuse

The first Phase 3 reuse requirement is:

- eclipse-degree activation should come from a shared trigger profile
- retrograde Mars should come from a shared trigger profile

Angularity can still be weighted per domain, but the runtime should expose a shared angularity profile so those domain rules stop being the only place where angular evidence is visible.

## Code Targets

- `backend/mundane_trigger_rules.py`
- `backend/mundane_models.py`
- `backend/mundane_service.py`
- `backend/mundane_domain_rules.py`
- `backend/test_mundane_trigger_rules.py`
- `backend/test_mundane_domain_rules.py`
- `backend/test_astro_clock_api_mundane.py`

## Acceptance Gate

Phase 3 is complete when:

1. analysis output includes computed trigger profiles
2. eclipse-degree activation and retrograde Mars domain paths reuse shared trigger state
3. trigger and activation layers expose computed trigger status, not only static metadata
4. mutation and conjunction cycles are directly computed as reusable backdrop context where the source base supports it
5. a dedicated trigger benchmark runner validates trigger behavior independently
6. tests and benchmark runners remain green

## Completion Status

Phase 3 is now complete.

Delivered:

- computed reusable trigger profiles for:
  - `angularity`
  - `retrograde_mars`
  - `eclipse_degree_activation`
  - `mutation_and_conjunction_cycles`
- shared trigger reuse in domain evaluators instead of repeated ad hoc derivation
- direct Jupiter-Saturn cycle backdrop computation for:
  - `aries_ingress`
  - `national_chart`
  - `lunation`
  - `eclipse`
- a dedicated trigger benchmark suite in `backend/benchmarks/mundane/trigger_profile_cases.jsonl`
- a dedicated runner in `backend/run_mundane_trigger_benchmarks.py`

Current status:

- trigger benchmark suite: green
- core mundane benchmark suite: green
- scan benchmark suite: green
- scan-series benchmark suite: green

## Next Gate

After Phase 3:

- move to Phase 4 chart-context and polity expansion
- widen polity registry coverage where runtime analysis is already useful without curated national charts
- add more source-proven national charts and proving cases before treating new polity overlays as registry-mature
- keep trigger-family work incremental from here, but no longer treat it as the active roadmap gate
