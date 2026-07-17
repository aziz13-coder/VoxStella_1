# Forensic ASC-Ruler Placement Benchmark - 2026-05-22

## Scope

This benchmark validates the McIntosh ASC-ruler house placement signal added from *Criminal Astrology*, pp. 17-19. The source is treated as victim placement, setting, contact, motive, or disappearance-context testimony. It is not treated as direct survivability doctrine.

## Implementation

- Runner: `backend/forensic_asc_ruler_benchmark_runner.py`
- Fixture: `tests/fixtures/forensic_asc_ruler_placement_cases.json`
- Tests: `backend/test_forensic_asc_ruler_benchmark_runner.py`

The fixture curates all 29 runnable cases from the default forensic statistical benchmark corpus as of 2026-05-22. Expected and contradictory axes are inherited from the existing statistical case fixtures. The ASC-ruler fixture fixes the validation list and records why each case belongs in the benchmark.

It also includes separate source-doctrine checks for McIntosh's H1-H12 placement statements. These checks are not mixed into the 29-case replay score; they validate that each house doctrine maps to a precise context axis.

## Validation Target

The benchmark maps each ASC-ruler risk tone to the case axes it can reasonably support as placement/reason context:

- `hidden`: abduction/missing-person, deception/cover-up
- `fatal_pressure`: violence/homicide
- `route` / `distance`: route, vehicle, transport, or distance movement
- `material`: trafficking/possession context
- `social` / `associate`: friend/acquaintance or witness/accomplice context
- `access`: domestic/known access, friend/acquaintance access, abduction/missing-person access
- `public`: authority/public or witness/accomplice context
- `perpetrator_contact`: domestic/known contact, friend/acquaintance contact, violence/homicide

The source-doctrine layer uses dedicated house-level axes:

- H1: `immediate_scene_or_vicinity_context`
- H2: `trafficking_or_possession_context`
- H3: `communication_vehicle_short_distance_context`
- H4: `family_home_end_matter_context`
- H5: `party_entertainment_context`
- H6: `routine_disruption_stalker_context`
- H7: `suspect_territory_context`
- H8: `death_financial_entanglement_context`
- H9: `far_distance_departure_context`
- H10: `public_authority_witness_context`
- H11: `friends_social_circle_context`
- H12: `hidden_captive_kidnapped_context`

## Promotion Gates

The fixture requires all of the following before this signal can be promoted into engine scoring:

- Minimum evaluated cases: 24
- Support rate: at least 0.60
- Contradiction rate: at most 0.10
- Null-control empirical p-value for support rate: at most 0.10

## Baseline Result

Command:

```powershell
python backend\forensic_asc_ruler_benchmark_runner.py --json --control-iterations 100
```

Observed result:

- Evaluated cases: 29
- Route errors: 0
- Supported cases: 13/29 = 0.4483
- Contradicted cases: 0/29 = 0.0
- Context-support score: 0.4483
- Shifted null-control mean support: 0.3731
- Empirical p-value: 0.2069
- Promotion recommendation: no
- Scoring decision: `keep_descriptive_only`

Source-doctrine checks:

- Source doctrine cases: 12
- House doctrine support: 12/12 = 1.0
- Contradicted doctrine cases: 0
- Supported source axes: H1-H12 dedicated context axes listed above
- This proves the McIntosh house-placement rules are now tested directly without using unrelated real-world replay cases as proxies.

Tone distribution:

- `fatal_pressure`: 7
- `hidden`: 5
- `associate`: 5
- `social`: 4
- `route`: 3
- `access`: 2
- `public`: 2
- `material`: 1

## Decision

Keep ASC-ruler placement descriptive for now. Do not add a weighted placement/reason context score yet.

The signal is clean enough to keep as a descriptive context feature because it produced zero contradictions in the curated run. It is not strong enough for weighted context scoring because support is below the 0.60 gate and the observed support rate is not statistically separated from shifted null controls.

This specifically protects against over-reading placements such as H4/H8 as automatic outcome testimony. In this benchmark, those placements can support homicide/death-context labels, but they do not decide the victim's outcome by themselves.

## Follow-Up Criteria

Reconsider weighted context scoring only after a larger fixture or an independently curated holdout set clears the same gates. If promotion later passes, keep the score bounded to placement/reason context and rerun the broader forensic benchmark to verify it does not distort unrelated classifications.
