# Forensic Asteroids and Special Degrees Benchmark

Date: 2026-05-20

## Decision

9/11 is excluded from forensic benchmarks by policy.

Asteroids and special degrees are enabled in the app only as bounded auxiliary testimony. They do not create new core case-axis findings because the benchmark showed axis specificity regression when they were exposed as ordinary findings.

## Source Basis

- B. D. Salerno, `extracted_text_docs/text_forensics/Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt`: forensic-practitioner use of fixed stars and critical/special degrees in event charts.
- B. D. Salerno, `extracted_text_docs/text_forensics/Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt`: critical-degree appendix and fixed-star use in forensic charts.
- `backend/forensic/knowledge/degree_special.yaml`: local degree dictionary already used by the forensic engine.
- `backend/forensic/knowledge/fixed_star_meanings.yaml`: local fixed-star forensic dictionary.
- Demetra George asteroid material and general modern asteroid doctrine support broad semantics only: Juno as partnership, Ceres as caregiving/family, Vesta as hearth/protection, Pallas as strategy, Proserpina/Persephone as abduction/underworld/return.

## Generalized Rule Constraints

- Special degrees must land on a relevant significator, house ruler, Moon, or angle.
- Asteroids must be within 1 degree of a relevant significator, ruler, Moon, or angle.
- The layer is low-weight and cannot override core ruler/aspect/reception testimony.
- Named asteroids are not used. The implemented set is limited to the app's existing calculated asteroid bodies: Ceres, Pallas, Juno, Vesta, and Proserpina.

## Benchmark Result

Baseline versus secondary factors enabled:

| Dataset | Axis BA | Axis recall | Axis specificity | Survivability accuracy | Survivability partial | Relationship primary |
|---|---:|---:|---:|---:|---:|---:|
| Default 29 off | 0.7758 | 0.9545 | 0.5970 | 0.7391 | 0.7391 | 0.7241 |
| Default 29 on | 0.7758 | 0.9545 | 0.5970 | 0.7391 | 0.7391 | 0.7241 |
| Holdout 30 off | 0.7194 | 0.7619 | 0.6769 | 0.6000 | 0.6167 | 0.5333 |
| Holdout 30 on | 0.7194 | 0.7619 | 0.6769 | 0.6333 | 0.6500 | 0.5333 |
| Combined 59 off | 0.7551 | 0.8605 | 0.6497 | 0.6604 | 0.6698 | 0.6271 |
| Combined 59 on | 0.7551 | 0.8605 | 0.6497 | 0.6792 | 0.6887 | 0.6271 |

The only classification improvement was `holdout_2022_tops_buffalo`, which moved from `Moderate/mixed_nonfatal` to `Lower/fatal_pressure_dominant`. No survivability classifications worsened.

This is an improvement, but not statistically significant by itself: one paired improvement and zero paired regressions is too small to claim durable statistical lift. Treat this as a source-backed calibration improvement that needs more holdout cases before being promoted to stronger axis or relationship logic.

## Implementation Notes

- App default: secondary factors enabled.
- Benchmark runner default: secondary factors disabled for baseline comparisons; pass `--secondary-factors` to evaluate the enabled app logic.
- Core case-axis findings remain unchanged by the auxiliary layer.
- `secondary_factor_analysis` and survivability `secondary_factor_impact` expose the audit trail.
