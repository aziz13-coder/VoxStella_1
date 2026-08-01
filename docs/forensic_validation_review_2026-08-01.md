# Forensic Astrology Workflow and Validation Review — 2026-08-01

## Scope and evidence status

The feature is a symbolic astrology rules engine. It is not a scientifically validated forensic method, and its scores are not probabilities. The API and UI must keep that distinction explicit.

The local doctrine is useful for checking whether code implements the repository's intended symbolic system, but it is expert/traditional opinion rather than empirical validation. The local text explicitly treats the Moon as a co-ruler and Mercury as a child marker, while warning that Venus and Mars do not reliably encode a person's sex.

External comparison:

- Carlson's double-blind natal-chart study tested astrologer matching claims and reported chance-level performance: [Nature 318, 419–425](https://doi.org/10.1038/318419a0). This is direct evidence about natal-chart matching, not a direct test of this event-chart algorithm.
- NIST says forensic-method validation should characterize performance and reliability with validation data: [NISTIR 8589](https://doi.org/10.6028/NIST.IR.8589).
- NIST scientific-foundation reviews evaluate empirical reliability, capabilities, limitations, and knowledge gaps: [Scientific Foundation Reviews](https://www.nist.gov/forensic-science/interdisciplinary-topics/scientific-foundation-reviews).
- Cawley and Talbot show that optimizing a finite-sample model-selection criterion can overfit the selection process and bias the reported performance: [JMLR 11 (2010), 2079-2107](https://www.jmlr.org/papers/v11/cawley10a.html).
- Scikit-learn's methodological guidance gives the same operational rule used here: split before model choice and never use evaluation data to make model decisions: [Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) and [nested cross-validation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html).

Evidence grading for this review: NIST guidance is Grade A for forensic validation practice; the peer-reviewed Nature experiment is Grade B for the narrower tested astrology claim; the local astrology texts are Grade D for empirical claims but are the primary specification for doctrine parity.

## Local source audit

The three local forensic books converge on a cautious symbolic workflow: verify event facts from multiple sources; select relevant house rulers and the Moon; prioritize angular, tight, and applying testimony; and require compound evidence. They do not provide controlled validation data for categorical outcome prediction. Their examples are retrospective and therefore cannot establish predictive accuracy.

Important doctrine-to-code comparisons:

- The local texts prioritize relevant significators and angular power. Generic aspects between unrelated bodies should not create categorical labels.
- Sextiles and other easy aspects are weak unless the planets are relevant rulers or angular. The old deception rules treated any Mercury-Neptune or Neptune-personal major aspect, at any orb, as an outcome-level deception signal.
- The Moon is a co-significator, but the same Moon-malefic contact must not be charged independently as lunar weakness, generic danger, category pressure, title pressure, and mechanism pressure.
- Child significators are contextual. A fifth-house or Mercury indication is not by itself proof that the victim is a child.
- The books warn against sex inference from Venus/Mars; that inference has been removed from victim and perpetrator presentation logic.
- One local procedure judges chart viability by correspondence with already-known facts. That can be useful for retrospective interpretation but is circular if reused as a predictive validation procedure.

## Runtime workflow

1. `GET /api/astro-clock/forensic` validates request mode, case type, coordinates, and optional local-space corridor.
2. The route resolves a current or saved chart and builds the full dashboard payload, including modern bodies and precise aspects.
3. `forensic.features.extract_features` normalizes planets, houses, aspects, solar conditions, stars, and derived house features.
4. `forensic.engine` evaluates the YAML knowledge rules and returns auditable findings.
5. Separate modules calculate dominance, secondary factors, symbolic survivability, relationship status, and optional local-space bearings.
6. The React dossier renders the backend result, raw audit payload, copied symbolic brief, and PDF report.

## Corrections made

- Aspect aliases now stay symmetric and deterministic when duplicate/reversed rows disagree; the tightest, richest row wins.
- An empty `all_aspects` array now falls back to compact aspects, negative orbs normalize to absolute values, and string house numbers correctly count as angular.
- Child cases now include Mercury in backend victim significators. Adult-female mode no longer automatically adds Venus solely from sex.
- Frontend collection-of-light scoring now matches the backend (`0.75` base rather than `1.0`).
- Invalid `case_type` values return `400` instead of silently becoming `general`.
- API metadata and the dossier state that outputs are symbolic, unvalidated, and non-probabilistic.
- Invented `/100` pressure and survivability percentages were removed. The UI now shows finding counts, qualitative bands, and the raw symbolic rule total.
- Physical/behavioral perpetrator profiles and composite-image prompts were removed from the API presentation path.
- Missing boolean features no longer satisfy explicit `false` conditions. Empty logical groups fail closed.
- Knowledge loading now rejects empty/ambiguous conditions, duplicate IDs, invalid evidence lists, and non-finite weights. Evaluation errors are surfaced instead of silently dropping rules.
- Missing or invalid house values are `unknown`, not cadent, and no longer create a synthetic vitality penalty.
- Outcome scoring is separated from display findings. Context-only and exploratory findings remain visible but cannot change axis, relationship, or survivability scoring.
- Generic deception indicators are context-only. The two retained Neptune outcome rules now require a tight hard/conjunction contact plus angular or significator relevance.
- The TWA-800 and Haiti-derived exact pattern rules are explicitly marked `case_derived_exploratory` and excluded from scoring.
- Survivability mechanism detection now uses stable rule IDs. Fatal pressure takes the strongest rule once per correlated evidence family instead of adding category count, title substring, and mechanism bonuses for the same testimony.
- Classification thresholds are centralized in a versioned `SurvivabilityPolicy` and emitted in the API response for auditability.

## Benchmark corrections

The old axis benchmark searched rule prose. Even after rationales were removed, incidental title words still cross-mapped outcomes (for example, `hidden` could create a deception axis). Axis scoring now uses only explicit rule metadata, stable rule IDs, and narrow category mappings. It never parses free text.

The old null control used at most `n-1` cyclic shifts. It now uses 100 deterministic Monte Carlo label permutations. Cases with no relationship ground truth are unscored rather than silently labeled `stranger_public`.

The old `specificity` label was also too broad: the fixtures label only selected contradictory axes, while all other absent axes are unknown. Reports now call this `explicit_contradiction_specificity`; compatibility aliases remain for existing consumers.

The 30-case FBI file is not an untouched holdout. `FORENSIC_HEALTHCARE_CHILD_CALIBRATION_2026-05-20.md` explicitly records calibration on the default 29 cases plus that file. Its metadata is now `contaminated_retrospective_evaluation`, and the tuning guard rejects it.

Post-correction curated replay (29 development cases):

- Labeled balanced accuracy `0.8564`; recall `0.7576`; explicit-contradiction specificity `0.9552`.
- 14 aligned, 13 partially aligned, 2 misaligned; 3 contradictory-axis false positives.
- Survivability: 15/23 aligned (`0.6522`).
- Relationship: 14 cases with ground truth, primary accuracy `0.5714`, exact match `0.4286`, macro-F1 `0.6270`.

The drop in development recall and survivability is retained rather than tuned back to the historical maximum: those cases were repeatedly used while authoring rules, so the earlier `0.8869` and `0.7391` figures were optimistic. The reduction in explicit contradictions (5 to 3) is consistent with removing weak outcome signals. These remain conditional replay results, not prospective validation.

## Locked known-outcome stress test

`tests/fixtures/forensic_known_outcome_aviation_holdout_v1.json` freezes eight NTSB-sourced aviation events before their first engine run: four in which at least 98% of occupants survived and four in which every occupant died. It is deliberately out of the engine's usual missing-person/homicide domain.

First-run results before these general corrections:

| Case | Known outcome | Engine result | Comparison |
|---|---|---|---|
| US Airways 1549 | 155/155 survived | Lower / fatal-pressure dominant | Misaligned |
| Aloha 243 | 94/95 survived | Moderate / mixed nonfatal | Aligned |
| Asiana 214 | 304/307 survived | Lower / fatal-pressure dominant | Misaligned |
| Southwest 1380 | 148/149 survived | Higher / nonfatal tilt | Aligned |
| ValuJet 592 | 0/110 survived | Moderate / risk-loaded survival | Misaligned |
| TWA 800 | 0/230 survived | Moderate / mixed nonfatal | Misaligned |
| American Eagle 4184 | 0/68 survived | Moderate / mixed nonfatal | Misaligned |
| Alaska 261 | 0/88 survived | Lower / fatal-pressure dominant | Aligned |

Aggregate: 3/8 outcomes aligned (`0.375`); the accident axis was detected in 2/8 cases. No relationship metric is reported because this fixture contains no relationship ground truth.

Post-correction evaluation, without choosing rules or thresholds from these eight cases:

| Case | Known outcome | Engine result | Comparison |
|---|---|---|---|
| US Airways 1549 | 155/155 survived | Lower / fatal-pressure dominant | Misaligned |
| Aloha 243 | 94/95 survived | Moderate / mixed nonfatal | Aligned |
| Asiana 214 | 304/307 survived | Moderate / mixed nonfatal | Aligned |
| Southwest 1380 | 148/149 survived | Higher / nonfatal tilt | Aligned |
| ValuJet 592 | 0/110 survived | Moderate / risk-loaded survival | Misaligned |
| TWA 800 | 0/230 survived | Moderate / mixed nonfatal | Misaligned |
| American Eagle 4184 | 0/68 survived | Moderate / mixed nonfatal | Misaligned |
| Alaska 261 | 0/88 survived | Lower / fatal-pressure dominant | Aligned |

Outcome alignment improved from 3/8 to 4/8, while accident-axis detection fell from 2/8 to 1/8 and explicit contradictions fell from 7 to 6. This is mixed and still poor out-of-domain performance. It does not validate the engine.

## Recent documentary development stress fixture

`tests/fixtures/forensic_recent_documentaries_2025_2026_cases.json` is a
separate development fixture, not an extension of the older Netflix baseline
and not a holdout. Documentary pages establish the released film or series;
official event records establish the replay anchor and outcome.

The four cases are deliberately heterogeneous:

- `The Idaho Murders: College Nightmare`: midpoint of the official 4:00-4:25
  a.m. homicide interval, four direct homicide victims.
- `Titan: The OceanGate Submersible Disaster`: NTSB's approximately 10:47
  a.m. local implosion time, all five occupants killed.
- `Trainwreck: The Astroworld Tragedy`: HPD's 9:38 p.m. stage-stop/light
  marker inside the developing crowd emergency. Survivability is unscored
  because the fixture does not assert a defensible crowd denominator.
- `Shipwrecked: Nightmare at Sea`: official 21:45:07 Costa Concordia impact
  time, 4,197 of 4,229 people rescued and 32 victims.

First Regiomontanus replay, before any rule changes based on these cases:

| Case | Explicit axis result | Survivability result | Main observed gap |
|---|---|---|---|
| Idaho murders | homicide matched; false water contradiction | Lower / fatal-pressure dominant, aligned | Correct core event, but a generic water rule overfires. |
| Titan | water matched; accident and transport missed; false family | Moderate / mixed nonfatal, misaligned | The engine recognizes water symbolism but misses the documented transport disaster and fatal outcome. |
| Astroworld | accident matched; public missed; false abduction and family | unscored | A public crowd disaster is forced into child/family/abduction patterns. |
| Costa Concordia | all three accident/water/transport axes missed; false homicide and family | Lower / fatal-pressure dominant, misaligned | The engine mistakes a survival-dominant marine evacuation for fatal interpersonal violence. |

Aggregate for this four-case slice: labeled-axis balanced accuracy `0.5088`,
axis recall `0.3333`, explicit-contradiction specificity `0.6842`, and
survivability `1/3` aligned. These failures are retained as development
regressions; changing rules to fit them would make later scores in-sample.

## House-system development selection

`backend/forensic_house_system_selection_runner.py` compares every supported
house system on the declared 33-case development corpus. It refuses any
dataset whose role is holdout, locked, prospective, retrospective, or
undeclared. Locked aviation cases were not used.

The predeclared composite is 60% labeled-axis balanced accuracy, 30%
survivability partial-credit accuracy, and 10% relationship macro-F1:

| Rank | System | Composite | Axis balanced | Survival partial | Relationship macro-F1 |
|---:|---|---:|---:|---:|---:|
| 1 | Regiomontanus (`R`) | 0.72224 | 0.8010 | 0.6154 | 0.5702 |
| 2 | Koch (`K`) | 0.70096 | 0.7926 | 0.5769 | 0.5233 |
| 3 | Campanus (`C`) | 0.69679 | 0.7627 | 0.6154 | 0.5455 |
| 4 | Placidus (`P`) | 0.68678 | 0.7419 | 0.6154 | 0.5702 |
| 5 | Topocentric (`T`) | 0.68678 | 0.7419 | 0.6154 | 0.5702 |
| 6 | Porphyry (`O`) | 0.68071 | 0.7602 | 0.5769 | 0.5152 |
| 7 | Whole Sign (`W`) | 0.63558 | 0.6952 | 0.6154 | 0.3384 |
| 8 | Equal (`E`) | 0.61042 | 0.7584 | 0.3846 | 0.4000 |

Regiomontanus remains the UI's existing new-install default and is now also
an explicit, deterministic forensic API default when the caller supplies no
house system. Explicit request choices still win, and a saved snap retains its
confirmed house system unless the caller requests recomputation.

## Leakage-safe tuning result

`forensic_survivability_tuning_runner.py` searches 27 threshold policies only on the declared 12-case development fixture and uses leave-one-family-out selection. It refuses locked, holdout, prospective, and retrospective-evaluation datasets.

The current policy already scores 12/12 on that previously calibrated fixture. No candidate improves it; the set contains only 12 cases across four families. The runner therefore returns `promotion.eligible=false` and leaves the default policy unchanged. A threshold change should be considered only after collecting a larger development set and a new, same-domain, versioned holdout that remains untouched until the policy is frozen.

## Source-backed generalization audit

The post-documentary audit changed rule semantics before changing weights. The
local doctrinal basis is Salerno's travel framework (Ascendant and ruler, Moon
and ruler, Mercury/travel houses, and corroborating malefic pressure) plus the
repository's 5th/10th/11th house meanings. External sources were used to set
validation and taxonomy boundaries, not to claim empirical support for
astrology:

- [NIST IR 8589](https://www.nist.gov/publications/validation-forensic-science-guiding-principles-collection-and-use-validation-data)
  requires a defined intended use, relevant test conditions, documented
  performance and uncertainty, and limitations supplied with results.
- The [FBI 2025 NIBRS User Manual](https://le.fbi.gov/file-repository/nibrs-user-manual-2025-0-062625.pdf)
  defines kidnapping/abduction through unlawful seizure, transport, or
  detention. A social setting plus hidden-house symbolism is therefore not a
  sufficient abduction classifier.

General corrections:

- Generic home/family clusters and the social-gathering seizure pattern remain
  visible but are non-scoring context. Relationship-specific rules are needed
  to activate family or abduction axes.
- Neptune in a water sign is not enough for a water label; Neptune must be in a
  relevant 4th/8th/12th house and have separate water testimony.
- Travel stress is context-only. A transport accident needs a reciprocal
  6th/9th link plus independent victim/Moon or public-event corroboration.
- A waterborne disaster needs five positive channels: concentrated water
  houses, occupied 9th house, afflicted 9th ruler, angular victim ruler, and
  angular malefic pressure.
- Public crowd context requires independent 5th-, 11th-, and 10th-house
  channels; the disaster form additionally requires a four-planet 5th-house
  concentration and angular malefic pressure.
- Accident mechanism no longer contributes fatal pressure by itself. Event
  family and lethality are separate targets.
- Findings now carry validated `source_refs`; legacy comparison tooling ignores
  the newly declared context-only rule families.

Frozen Regiomontanus comparisons:

| Set | Metric | Before | After |
|---|---|---:|---:|
| 33-case development | labeled-axis balanced accuracy | 0.8010 | 0.8692 |
| 33-case development | axis recall | 0.7067 | 0.7733 |
| 33-case development | contradiction specificity | 0.8953 | 0.9651 |
| 4 recent documentaries | labeled-axis balanced accuracy | 0.5088 | 0.9181 |
| 4 recent documentaries | axis recall | 0.3333 | 0.8889 |
| 4 recent documentaries | contradiction specificity | 0.6842 | 0.9474 |
| 8-case locked aviation holdout | labeled-axis balanced accuracy | 0.4375 | 0.4583 |
| 8-case locked aviation holdout | axis recall | 0.1250 | 0.1250 |
| 8-case locked aviation holdout | contradiction specificity | 0.7500 | 0.7917 |

The locked holdout was replayed only after the rules and synthetic negative
tests were frozen, and it was not used for a second tuning pass. Its 1/8 event
detection and 4/8 survivability alignment remain poor. On the documentary
slice, Idaho's false water label, Titan's false family label, and Astroworld's
false abduction/family labels are removed; Titan now matches all three event
axes and Astroworld both. Costa matches accident and transport but still misses
water, retains a false homicide contradiction, and remains survivability-
misaligned. These residuals are retained.

These are conditional symbolic-rule benchmarks. They do not establish that
astrology is scientifically valid or suitable for real forensic conclusions.

## Commands

```powershell
python backend\forensic_statistical_benchmark_runner.py
python backend\forensic_statistical_benchmark_runner.py --dataset tests\fixtures\forensic_recent_documentaries_2025_2026_cases.json
python backend\forensic_house_system_selection_runner.py
python backend\forensic_statistical_benchmark_runner.py --dataset tests\fixtures\forensic_known_outcome_aviation_holdout_v1.json
python backend\forensic_survivability_tuning_runner.py
python -m pytest -q backend\test_forensic_known_outcome_stress.py
```
