# AstroClock Estate Election Model

> Current implementation note (2026-07-31): participant house/cusp rules use
> saved birth-time quality and are not automatically treated as certified.
> Source files are canonical under `backend/**` and `frontend/src/**`; generated
> or legacy package mirrors must not be edited. See
> `ELECTION_MODEL_REFERENCE_2026-07-31.md`.

This document tracks the estate election implementation added from the Galaxy research note:

`C:\Program Files (x86)\Galaxy\docs\research\electioner_estate_astrological_logic.md`

## Source Paths

- Frontend modal: `frontend/src/features/astroclock/ElectionModal.jsx`
- Frontend API serialization: `frontend/src/features/astroclock/api.mjs`
- Backend API route: `backend/astro_clock_api.py`
- Scorer facade: `backend/election.py`
- Estate scorer: `backend/election_models/estate.py`

Do not edit generated packaged artifacts under `frontend/dist-electron`, `frontend/backend/build`, `frontend/dist`, or `website`.

## Workflow

The Estate model is selected in AstroClock Election as `matter=estate`.

Required inputs:

- `start`, `end`, `location`
- `estate_participant_snap_id`
- `estate_direction=buy|sell`

Optional period extraction inputs:

- `estate_display_mode=total|detail`
- `estate_scope=all|current|selected`
- `estate_current_line_id`
- repeated `estate_selected_line_id`
- `estate_level_percent`

The backend forces traditional timing for this model because the estate rules
use planetary-hour support. Participant house/cusp fit is active only when the
saved birth-time quality is precision-safe.

## Model Shape

The scorer returns the same line contract used by business beta, but the route exposes estate-specific fields.

Lines:

- `event`: event chart score for the property election
- `participant:1`: buyer or seller fit score from the selected saved chart

Top-level scorer payload:

- `value`
- `tags`
- `pros`
- `cautions`
- `lines`

## Estate-Specific Extraction Fields

The route does not reuse `business_beta_*` row names. Estate extraction produces:

- `estate_extraction`
- `estate_periods`
- row-level `estate_pass`
- row-level `estate_line_states`
- row-level `estate_selected_line_ids`
- row-level `estate_selected_threshold`

This keeps downstream UI and exports from confusing business beta periods with property election periods.

## Benchmarking

Benchmark coverage and dataset formats live in `docs/estate_election_benchmarks.md`.

Implemented benchmark assets:

- Synthetic rule fixtures: `backend/test_estate_synthetic_rule_fixtures.py`
- Extraction benchmarks: `backend/test_estate_extraction_benchmarks.py`
- Scan/backtest/prospective harness: `tools/estate_benchmark.py`
- Backtest CSV template: `tests/fixtures/estate_backtest_dataset_template.csv`
- Prospective freeze CSV template: `tests/fixtures/estate_prospective_freeze_template.csv`

## Rule Mapping

Shared event branch:

- 4th house and IC anchor property.
- 1st house represents the actor; 7th house represents the counterparty.
- 2nd ruler and 7th ruler contact is treated as transfer/counterparty tension.
- Moon day, Moon phase, via combusta, direct motion, Mercury-Mars friction, Fortuna, IC sign, property-house population, and planetary hour are scored on the event line.

Buy branch:

- Favors a waning Moon.
- Uses rapid-sign latitude tables for Moon and Ascendant.
- Emphasizes the 2nd-house money set.

Sell branch:

- Favors a waxing Moon.
- Uses slow-sign latitude tables for Moon and Ascendant.
- Emphasizes the 8th-house transfer set.

Participant branch:

- Builds a participant property set from participant 4th-house almuten/ruler, IC, 4th-house occupants, and Venus.
- Rewards participant Ascendant ruler harmony with the event Moon.
- Rewards event Ascendant resonance with participant Ascendant.
- Rewards event Fortuna contact to participant Ascendant.
- Rewards event benefic support and penalizes Mars, Saturn, node, Lilith, Uranus, Neptune, and Pluto pressure to participant property points.
