# Forensic Rule Coverage Expansion - 2026-04-03

## Scope
- Added direct coverage for the remaining high-value forensic rule files and dominance scoring.
- Focused on:
  - `base.yaml`
  - `degree_signatures.yaml`
  - `house_rules.yaml`
  - remaining uncovered directional violence rules
  - `compute_dominance()`

## Test File Added
- `tests/test_forensic_core_rules.py`

## Explicit Rule Coverage Added
- Base rules:
  - `sect_malefic_out_of_sect`
  - `moon_applying_malefic_hard`
- Degree signatures:
  - `any_anaretic_planet`
  - `any_anaretic_planet_any`
  - `moon_via_combusta`
  - `planet_ingress`
  - `mid_degree_focus`
- House rules:
  - `first_ruler_in_8th`
  - `first_ruler_rules_8th`
  - `strong_12th_emphasis`
  - `malefics_in_6th`
- Directional violence rules:
  - `violence_moon_under_death_pressure`
  - `violence_hidden_victim_with_angular_malefic`

## Direct Algorithm Coverage Added
- `compute_dominance()`:
  - exact scoring for an extremely dominant planet
  - weak retrograde cadent planet classification

## Validation Commands
- `python -m pytest -q tests/test_forensic_core_rules.py`
- `python -m pytest -q tests/test_forensic_deception_rules.py`
- full forensic suite (`tests/test_forensic*.py`)

## Result
- Core-rule coverage file:
  - `6 passed`
- Full forensic suite after expansion:
  - `72 passed`
  - `10 subtests passed`
  - `1` non-blocking external warning (`pytz` deprecation)

## Remaining Gaps After This Expansion
- Lookup/dictionary YAMLs are still mostly validated indirectly via route/replay output rather than by targeted semantic assertions:
  - `aspect_meanings.yaml`
  - `planetary_meanings.yaml`
  - `crime_patterns.yaml`
  - `house_meanings.yaml`
  - `fixed_star_meanings.yaml`
  - `perpetrator_profiles.yaml`
  - `abduction_location.yaml`
  - `degree_special.yaml`
  - `ic_planet_in_4th.yaml`
  - `ic_ruler_house_meanings.yaml`
  - `ic_sign_meanings.yaml`
  - `witness_accomplice.yaml`
- Core rule-list files (`base.yaml`, `degree_signatures.yaml`, `house_rules.yaml`, `directional_context_rules.yaml`, `deception_rules.yaml`) now have direct assertion-based coverage.
- `compute_dominance()` now has baseline direct scoring coverage.
