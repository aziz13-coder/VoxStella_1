# Forensic Healthcare/Child Calibration - 2026-05-20

## Purpose

Calibrate survivability handling for child-harm charts in healthcare or caregiver settings without tuning to one named case.

The defect was not axis detection. The engine already surfaced child, violence, deception, and institutional/worksite testimony. The defect was survivability: an `Abduction`/worksite-seizure finding could force the abduction branch, downscale fatal pressure, and hold a chart at `Moderate` even when the same chart had child + violence + death-edge testimony.

## Source Basis

Local source-backed doctrine already separates institutional/caregiver context from ordinary abduction recovery:

- `backend/forensic/knowledge/house_meanings.yaml:22-23` maps the 6th house to illness, servants/employees, routine work, workplace incidents, accidents/injuries, and the body.
- `backend/forensic/knowledge/house_meanings.yaml:46` maps the 12th house to hidden things, confinement, hospitals, and prisons.
- `backend/forensic/knowledge/abduction_location.yaml:68-69` maps the 6th to workplaces, clinics, hospitals, controlled-access job/medical sites, and the 12th to hidden/secluded confinement.
- `backend/forensic/knowledge/abduction_location.yaml:182,191` specifically calls out hospital wings and clinic/lab/service corridors.
- Salerno local source notes that 6th-house servants in the 5th house of children places responsibility for the child with servants/caregivers: `docs/ai_agent_mac/forensic_local_text_sources/books/salerno_forensics_by_the_stars.txt:342-343`.
- Salerno also maps the 12th to hospitals/confinement: `docs/ai_agent_mac/forensic_local_text_sources/books/salerno_forensics_by_the_stars.txt:1402,2611`.
- McIntosh source keeps 8th-house death and 12th-house hidden/kidnapped testimony in the event-chart reading: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:256`.

External event anchors used for the smoke probe:

- Child A/B: Sky and Guardian court reporting place the attacks at Countess of Chester Hospital, with Child A dying on 8 June 2015 and Child B surviving a similar collapse the following night: <https://news.sky.com/story/lucy-letby-neonatal-nurse-who-allegedly-murdered-seven-babies-including-twins-was-a-poisoner-at-work-court-hears-12717509>, <https://www.theguardian.com/uk-news/2022/oct/17/mother-begged-medics-dont-let-my-baby-die-lucy-letby-trial-told-court-nurse>
- Child C: Guardian court reporting gives the sudden collapse at about 11:15pm on 13 June 2015: <https://www.theguardian.com/uk-news/2022/oct/31/lucy-letby-nurse-would-not-leave-parents-dead-newborn-alone>
- Child D: Sky court reporting gives the first deterioration around 1:30-1:40am on 22 June 2015: <https://news.sky.com/story/lucy-letby-trial-experienced-nurse-struck-by-unusual-rash-on-allegedly-murdered-baby-12738343>, <https://news.sky.com/story/lucy-letby-trial-completely-unclear-why-child-ds-condition-got-worse-court-hears-12741065>

These sources are used only for probe labels and timestamps, not as engine rules.

## Implemented Rule

Route context now exposes:

- `healthcare_context`
- `caregiver_context`
- `institutional_care_context`
- `healthcare_child_context`

The survivability engine now applies this narrow calibration:

```text
if child case
and healthcare/caregiver/institutional-care context is present
and Abduction/worksite-seizure testimony is present
and Violence testimony is present:
    do not treat the Abduction finding as release-favored recovery context
    keep fatal pressure undownscaled
    expose context_calibration.abduction_downscale_suppressed = true
```

The rule does not add a relationship category, does not force a fatal outcome by itself, and does not suppress ordinary abduction handling when violence testimony is absent.

## Probe Result

Post-calibration Lucy Letby smoke probe, using `case_type=child`, Countess of Chester Hospital coordinates, Regiomontanus, and secondary factors enabled:

| Probe | Expected | Post-calibration level | Band | Calibration |
|---|---:|---|---|---|
| Child A collapse, 2015-06-08 20:26 | fatal | Lower | fatal_pressure_dominant | downscale suppressed |
| Child B collapse, 2015-06-10 00:30 | survived | Moderate | mixed_nonfatal | no fatal-context suppression |
| Child C collapse, 2015-06-13 23:15 | fatal | Lower | fatal_pressure_dominant | already fatal without abduction suppression |
| Child D first collapse, 2015-06-22 01:40 | fatal | Lower | fatal_pressure_dominant | downscale suppressed |

The prior failure mode was Child A and Child D being held in `Moderate/risk_loaded_survival` because abduction/worksite context downscaled fatal pressure.

## 59-Case Regression Benchmark

Dataset: default 29-case corpus plus `tests/fixtures/forensic_holdout_30_cases_2026_05_20.json`. 9/11 remains excluded by `backend/forensic/benchmark_policy.py`.

| Run | Axis balanced accuracy | Axis micro recall | Survivability accuracy | Survivability partial | Relationship macro F1 | Route errors |
|---|---:|---:|---:|---:|---:|---:|
| Secondary factors off | 0.7551 | 0.8605 | 0.6604 | 0.6698 | 0.5681 | 0 |
| Secondary factors on | 0.7551 | 0.8605 | 0.6792 | 0.6887 | 0.5681 | 0 |

Null-control significance stayed positive:

- Axis balanced accuracy: `p=0.0169`
- Axis micro recall: `p=0.0169`
- Relationship macro F1: `p=0.0169`

No benchmark regression was observed in the 59-case corpus.

## Code Locations

- Route context inference: `backend/astro_clock_api.py:2907`, mirrored in `frontend/backend/astro_clock_api.py`.
- Survivability calibration: `backend/forensic/survivability.py:1146`, mirrored in `frontend/backend/forensic/survivability.py`.
- Regression tests: `backend/test_forensic_healthcare_child_calibration.py` and `tests/test_forensic_route_contract.py`.
