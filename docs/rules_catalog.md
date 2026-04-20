# Horary Logic Rules Catalog

This catalog enumerates formal rules used by the horary logic engine.

## Receptions and Motion (R015–R020)

| Rule | Condition | Effect | Priority |
|------|-----------|--------|----------|
| R015 | `reception_pair_kind == 'unilateral'` | Apply moderate positive weight based on `reception_strength_pair` | 30 |
| R016 | `reception_pair_kind` in {`mutual_rulership`, `mutual_exaltation`, `mutual_term`, `mutual_face`} | Apply strong positive weight based on `reception_strength_pair` | 90 |
| R017 | `reception_pair_kind == 'mixed_reception'` | Apply medium positive weight based on `reception_strength_pair` | 60 |
| R018 | `house_ruler_reception` is true | Grant minor assistance to perfection | 40 |
| R019 | `S1_stations_before_perfection` is true | Refranation: perfection is prevented, apply strong negative weight | 80 |
| R020 | `S2_stations_before_perfection` is true | Refranation: perfection is prevented, apply strong negative weight | 80 |

*R015–R017* cover various forms of reception between the primary significators. *R018* captures cases where one significator rules the other's house. *R019* and *R020* address refranation due to either significator stationing before the perfecting aspect.
