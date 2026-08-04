# Forensic Survivability: Mackenzie Deep Dive - 2026-08-04

Status: research and design record. No survivability weights, thresholds, rules,
fixtures, or frontend behavior were changed as part of this deep dive.

Related issue record:
`docs/FORENSIC_AXIS_CONSISTENCY_ISSUES_2026-08-04.md`.

## Executive conclusion

The Mackenzie result is not adequately described as a single bad threshold.
There are three separate problems:

1. The target is undefined. One event chart is being compared with three
   occupants who had different outcomes: two passengers died and the driver
   survived.
2. The chart-only scorer recognizes a tight Moon-dispositor-to-death-ruler
   bridge as route/associate evidence but does not pass the same testimony to
   danger or fatal pressure.
3. Repository claims and May 2026 dashboard goldens describe an older
   transport-fatal rule that the current code explicitly excludes.

The first correction should therefore be a target/schema correction, not a
Mackenzie-specific weight. The next chart-only experiment should be a
deduplicated victim-dispositor/death bridge and a compound transport-severity
gate. It must be instrumented before it is scored and evaluated on a new,
source-backed transport development set. Physical crash and clinical factors
belong in separately labeled evidence layers; they must not be presented as
astrological predictors.

## 1. Current engine state

The live `/api/astro-clock/forensic` route derives chart features, evaluates
rules, builds scoring categories, applies optional secondary factors, and then
calls `compute_survivability()` in `backend/forensic/survivability.py`.

The current net score is:

```text
vitality
+ accidental_power
+ benefic_support
+ recovery_support
+ lunar_condition
- danger_weight * danger
- adjusted_fatal_pressure
```

For a non-abduction case, `danger_weight` is `0.85`. The qualitative policy is
versioned as `deduplicated_v2`:

- `Lower` can result from fatal pressure at least `4.5` with net at most `1.5`;
- a recognized fatal mechanism can lower the pressure gate to `2.0`, provided
  rescue is weak and net is at most `5.0`;
- violent context has its own danger/fatal gate and net cap;
- otherwise net at least `3.0` with fatal pressure below `3.0` is `Higher`;
- net at most `-4.0` is `Lower`; and
- the remainder is `Moderate`.

A non-abduction result that is not `Lower`, has net at least `2.0`, and has
fatal pressure below `1.5` is labeled `nonfatal_tilt`.

### Mackenzie live result

Fixture: `mackenzie_shirilla_the_crash`, local time approximately 05:30 on
2022-07-31 in Strongsville, Ohio, Regiomontanus houses, `case_type=general`.

| Mode | Level | Band | Net | Vitality | Accidental | Recovery | Danger | Fatal pressure |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Current route, secondary factors on | Moderate | nonfatal_tilt | 2.99 | 3.00 | 0.30 | 0.05 | 0.00 | 0.36 |
| Current route, secondary factors off | Higher | nonfatal_tilt | 3.35 | 3.00 | 0.30 | 0.05 | 0.00 | 0.00 |

The `3.00` vitality is entirely the Moon: dignity contributes `+2.5` and its
succedent second-house placement contributes `+0.5`. Because the Moon is also
the first-house ruler, the deduplicated significator list contains the Moon
once rather than double-counting it. The `+0.30` accidental score comes from
the Moon being an angular ruler in a steady placement. The `+0.05` recovery
score is a weak, neutral collection by the Sun. Secondary degrees and
quindeciles supply only `0.36` fatal pressure.

The current engine correctly identifies a transport-harm mechanism, but
`fatal_mechanism_context` is false by design. Lines 1215-1221 of the current
scorer explicitly exclude `transport_harm` because detecting a crash does not
establish that a crash was fatal. The regression test
`tests/test_forensic_survivability_missing_data.py` asserts this behavior.

### Relevant Mackenzie chart testimony already available to the engine

- Cancer rises; the Moon is both the first-house ruler and the general victim
  co-significator.
- The Moon is in Virgo in the second house. Its dispositor is Mercury.
- Mercury is in the second house and is in a `0.266` degree opposition to
  Saturn.
- Saturn rules both the seventh and eighth houses, is placed in the eighth,
  and is marked hard-afflicted.
- The rule `known_person_route_harm_moon_dispositor_bridge` uses this chain to
  support associate and route axes, but survivability examines only direct
  hard contacts from the victim significators to Mars/Saturn. It therefore
  assigns danger `0.00`.
- Mars is angular in the tenth and is within `1.001` degrees of Uranus; Mars is
  also in a hard aspect to Saturn. The current survivability scorer does not
  use a Mars-Uranus transport-shock cluster.
- The third-house ruler is hard-afflicted. A scoring transport rule fires, but
  transport contributes no fatal pressure in the current policy.

### Idaho comparison fixture

The second fixture, `netflix_idaho_murders_college_nightmare_2026`, has a
well-defined target: four direct homicide victims, four fatalities, zero
survivors. It returns `Lower / fatal_pressure_dominant` (`-2.92` with secondary
factors off and `-3.10` with them on). This shows that the existing fatal path
works where a scoring violence rule and an unambiguous all-fatal victim group
are present. It does not resolve the mixed-occupant transport problem.

## 2. Issues recorded

### SURV-001: outcome scope is missing

The Mackenzie fixture says only "two passenger deaths and driver survivor."
It has no `known_outcome`, no `expected_survivability`, no target role, and no
denominator. The statistical benchmark consequently does not score its
survivability result.

The official prosecutor record states that two passengers were pronounced
dead and Shirilla was transported to a hospital and treated. A single event
label can therefore mean three different things:

| Intended target | Denominator | Observed outcome |
| --- | ---: | --- |
| All vehicle occupants | 3 | mixed: 2 fatalities, 1 survivor |
| The two passenger victims | 2 | all fatal |
| The driver | 1 | survived with injury |

Without an explicit target, `Moderate` may be a defensible description of the
mixed event while `nonfatal_tilt` is misleading for the two direct victims.
The engine cannot infer which person the user means from `case_type=general`.

### SURV-002: the fatal chain stops at the Moon

The danger component looks for direct hard aspects from the first ruler/Moon
to Mars or Saturn. It does not follow a significator's dispositor. Mackenzie
therefore receives no danger even though the Moon's dispositor is in an exact
hard link to a planet that simultaneously rules the opponent and death houses
and occupies the eighth house.

This is a general representational gap, but it is not yet a validated scoring
factor. It should first be emitted as a non-scoring feature with provenance,
orb, applying/separating state, reception, dignity, and house roles.

### SURV-003: transport severity and transport occurrence are conflated in old artifacts

The current code correctly refuses to make every crash fatal. However, there
is no second-stage transport-severity gate. The only choices are effectively
"transport is not fatal evidence" or the obsolete flat `+3` transport bonus.

The repository currently contains conflicting claims:

- `forensic_netflix_true_crime_2025_2026_cases.json` says survivability "now
  applies general transport-crash fatal-mechanism pressure";
- the dashboard golden generated on 2026-05-19 records Mackenzie as
  `Lower / fatal_pressure_dominant`, score `-0.30`, including
  `transport crash/impact mechanism +3`;
- the current live route returns `Moderate / nonfatal_tilt`, score `2.99`; and
- the current source and regression test deliberately exclude transport from
  fatal-mechanism context.

The fixture prose and golden are stale relative to the live source. Neither
should be used as evidence of current engine behavior.

### SURV-004: the output is event-level but the predictors are person-like

The score speaks of a "victim significator," yet an event chart can include
multiple victims, perpetrators, survivors, passengers, and bystanders. One
Moon/first-ruler score cannot produce distinct occupant outcomes. Relationship
roles also do not establish seat position or injury exposure.

### SURV-005: confidence is not supported by current evaluation

Read-only replay on 2026-08-04 produced the following survivability alignment:

| Dataset | Aligned | Scored | Accuracy | Status |
| --- | ---: | ---: | ---: | --- |
| Current curated default | 16 | 26 | 61.54% | development/retrospective mix |
| Locked aviation outcome stress set | 4 | 8 | 50.00% | untouched locked stress set |
| Recent documentaries | 1 | 3 | 33.33% | development fixture |
| Thirty-case retrospective set | 15 | 30 | 50.00% | explicitly contaminated |

These are small, heterogeneous sets and are not evidence of calibrated
individual survival prediction. The API correctly says the score is not a
statistical probability, but `nonfatal_tilt` can still read as a prediction
with more certainty than the evaluation supports.

### SURV-006: secondary factors can cross a display threshold without solving the mechanism

In Mackenzie, optional degrees/quindeciles change `Higher` to `Moderate` by
only `0.36`, but leave `nonfatal_tilt` unchanged. This is a threshold-side
effect, not a coherent explanation of two deaths and one survival. Secondary
factors should remain explicitly optional and should not be promoted to core
survivability inputs without independent evidence.

### SURV-007: Descendant aspects were not represented in survivability

Under `deduplicated_v2`, the forensic feature payload contained longitudes for
the Ascendant, Descendant, MC and IC, but its `aspects` collection contained
planet-to-planet records only. The survivability scorer consequently could not
weight a planet conjunct, opposite or square the Descendant.

The Ascendant is represented indirectly through its ruler, and a victim
significator gets modest accidental-strength credit when it rules an angle and
is well placed. The Descendant and MC can also influence upstream rule
findings through their rulers and house roles. None of these paths is the same
as measuring an aspect to the angle degree.

For Mackenzie, Pluto is approximately `0.027` degrees from the Descendant.
`deduplicated_v3_descendant_aspects` now treats that conjunction as direct
fatal-pressure testimony. Jupiter is approximately `1.803` degrees from the
MC, but MC, IC, and ASC contacts remain excluded from survivability because
they are contextual angles rather than this component's declared victim-state
target.

## 3. What the sources support

### Local forensic doctrine

The local texts support treating the first-house ruler and Moon as subject
significators, angularity as strength, hard malefic contacts as danger,
benefic contacts as possible safety testimony, and eighth/twelfth-house links
as death-edge testimony. They also support inspecting the Moon's dispositor
and travel rulers rather than stopping at the Moon itself.

Relevant local sources include:

- `extracted_text_docs/text_forensics/Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt`;
- `extracted_text_docs/text_forensics/Forensic Astrology for Everyone You Dont Need to be an Astrologer to Locate Lost Objects, Find Missing Persons, Solve... (Caroline J. Luley) (Z-Library).txt`;
- `docs/FORENSIC_SURVIVABILITY_CALIBRATION_2026-04-07.md`; and
- `docs/FORENSIC_SURVIVABILITY_STRATIFIED_BENCHMARK_2026-04-07.md`.

Salerno specifically describes affliction to the Moon as danger, Saturn as
injury/death, Mars as violence, Uranus as catastrophic accident, and a
well-placed Jupiter or Venus associated with the Ascendant as hopeful. The
travel examples examine the Ascendant/ruler, Moon and its ruler, Mercury,
travel-house rulers, angular malefics, and hard aspects together. Luley treats
the Moon's dispositor and planets contacting the Moon as important, and says a
death pattern commonly involves the first ruler and Moon.

This is doctrinal support for feature generation, not empirical validation of
survival prediction. The texts are practitioner works, often interpret known
cases retrospectively, and do not supply blinded controls, calibrated effect
sizes, or prospective accuracy.

### Empirical crash and trauma evidence

The Cuyahoga County Prosecutor's Office documents the Mackenzie event at
approximately 05:30, acceleration to 100 mph, impact with a brick building,
two passenger deaths, treatment of the surviving driver, discovery about 45
minutes later, full accelerator input, no brake application, and no
contributing vehicle defect:
https://www.ccprosecutor.us/strongsville-woman-sentenced-life-in-prison-crash-killed-two/

NHTSA does not characterize occupant outcome using event type alone. Its Crash
Investigation Sampling System combines scene evidence, vehicle damage,
interior contacts, safety systems, victim interviews, and medical records:
https://www.nhtsa.gov/crash-data-systems/crash-investigation-sampling-system

NHTSA's crash-injury program exposes vehicle variables such as impact type,
crash angle, delta-V, rollover status, make/model/year and occupant variables
such as seat, age, height, weight and sex. Its injury-causation method also
records energy source, contacted components, body regions, internal injury
paths, critical intrusion, contributing factors, and confidence:
https://www.nhtsa.gov/research-data/crash-injury-research

NHTSA describes delta-V as the principal crash-severity measure in its crash
databases while also warning that it can be difficult to reconstruct for some
crash modes. EDRs add pre-crash speed, throttle and brake data but do not make
those measurements interchangeable with occupant delta-V or injury severity:
https://www.nhtsa.gov/research-data/event-data-recorder

A FARS study of rear-seat adult mortality adjusted for passenger age, belt
use, ejection, driver factors, vehicle year/type/weight, impact point,
rollover, and excessive speed. Increased mortality was associated with age,
excessive speed, ejection, no belt, and impact geometry; belt use was strongly
protective:
https://pubmed.ncbi.nlm.nih.gov/27747737/

The original TRISS method combines anatomical injury severity, physiological
state, age, and blunt-versus-penetrating mechanism to estimate trauma survival:
https://pubmed.ncbi.nlm.nih.gov/3106646/

The important engineering conclusion is not that these variables should be
added to astrology. It is that actual occupant survival is individual and
mechanistic. A chart-only event score lacks the information needed to explain
why different occupants in the same vehicle have different outcomes.

### Prediction-model evidence

External validation means evaluating performance in relevant data not used in
development. Recommended evaluation covers overall fit, calibration and
discrimination, with confidence intervals and important subgroups:
https://www.bmj.com/content/384/bmj-2023-074820

Calibration must be assessed over the prediction range rather than inferred
from accuracy alone:
https://doi.org/10.1186/S12916-019-1466-7

TRIPOD+AI calls for a transparent, complete account of the target, data,
predictors, methods and results, regardless of whether regression or machine
learning is used:
https://www.bmj.com/content/385/bmj-2023-078378

NIST AI RMF emphasizes validity, reliability, robustness, transparency and
evaluation in the actual context of use:
https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10

### Scientific-status boundary

No direct controlled validation of this repository's forensic-astrology
survivability method was found. A well-known double-blind Nature experiment
tested natal-chart personality interpretation, not forensic event-chart
survival, and did not validate the tested astrological claim:
https://www.nature.com/articles/318419a0.pdf

That paper is not direct disproof of this exact engine, but it reinforces the
need to label the chart layer as symbolic and unvalidated. Adding more
astrological parameters can improve retrospective fixture fit without
establishing real predictive validity.

## 4. Proposed target contract before scoring changes

Every benchmarked survivability case should declare:

```json
{
  "survivability_target": {
    "scope": "individual | direct_victim_group | occupant_group | event",
    "role": "passenger_victims",
    "denominator": 2,
    "anchor_relation": "directly_exposed_at_event",
    "selection_rule": "defined_before_engine_replay"
  },
  "known_outcome": {
    "survivors": 0,
    "fatalities": 2,
    "class": "all_fatal"
  }
}
```

The observed counts are benchmark labels and must never be passed to the
engine as predictors. A useful outcome taxonomy is:

- `all_survived`;
- `survival_dominant` with the policy threshold stated;
- `mixed_outcome` whenever both fatalities and survivors are present;
- `fatal_dominant` with the policy threshold stated; and
- `all_fatal`.

Mackenzie should have two explicit evaluations if both questions matter:

1. `occupant_group`, 3 occupants, 1 survivor, 2 fatalities,
   `mixed_outcome` plus a fatality fraction of `2/3`; and
2. `direct_victim_group`, the 2 passengers, 0 survivors, 2 fatalities,
   `all_fatal`.

The driver survivor can be a third, individual target only if the engine has a
principled way to map that person to a distinct significator. The current
event chart does not.

If no target is declared, the engine should return
`target_scope=unspecified` and an outcome band such as
`indeterminate_target`, not `nonfatal_tilt`.

## 5. Candidate chart-only improvements

These are hypotheses for instrumentation and evaluation, not approved weights.

### A. Victim-dispositor danger bridge

For every deduplicated victim significator:

1. identify its dispositor;
2. inspect tight hard contacts from that dispositor to Mars, Saturn, the
   eighth ruler, and the seventh ruler;
3. retain all simultaneous roles of the contacted planet;
4. record house placement, dignity, reception, orb, and applying/separating
   state; and
5. score the evidence family at most once.

Mackenzie would expose `Moon -> Mercury -> Saturn`, with Saturn simultaneously
the seventh and eighth ruler in the eighth house. The feature should be called
something structural, such as `victim_dispositor_death_bridge`, rather than a
case narrative.

### B. Opponent/death ruler overlap

Emit a separate feature when the seventh and eighth share a ruler and that
ruler is in the eighth/twelfth or otherwise strongly death-linked. Do not make
this fatal by itself: the overlap can describe an opponent or crisis without
proving death. It becomes a candidate severity channel only when linked back
to a victim significator and an independently detected mechanism.

### C. Compound transport-severity gate

Keep the existing transport rule as mechanism detection. Add a second gate
that requires multiple independent channels, for example:

```text
transport_harm
AND victim/death bridge
AND at least one of:
    direct victim-malefic danger
    tight Mars-Uranus shock testimony
    strongly afflicted route ruler linked to the death ruler
```

This avoids restoring the obsolete flat `transport +3` rule. It also preserves
the safety requirement that a crash can be survivable. The exact channels and
any score must be selected by generalization tests, not by matching Mackenzie.

### D. Dynamic and qualitative modifiers

For each candidate bridge, retain:

- continuous orb rather than only a boolean cutoff;
- applying/separating and within-sign perfection;
- reception between victim, dispositor and afflictor;
- essential dignity/debility of both sides;
- angularity and house role; and
- whether multiple rule IDs are derived from the same underlying testimony.

Separating aspects should not automatically be discarded in an event chart
cast at or just after impact; they may describe a just-completed event. Their
treatment must be specified prospectively.

### E. Rescue and recovery specificity

Recovery support should distinguish:

- direct, applying benefic contact to the victim ruler/Moon;
- indirect collection or translation;
- strength of the benefic;
- obstruction/prohibition before perfection; and
- missing or ambiguous timing data.

The current `+0.05` neutral collection in Mackenzie is already small. It should
remain visible as weak testimony rather than be read as an explanation for the
driver's survival.

### F. Secondary factors remain exploratory

Asteroids, special degrees and quindeciles should stay outside the core model
until their incremental value is demonstrated on data not used to define
them. Report their contribution separately and test the core model with them
off by default.

### G. Planet-to-Descendant aspect family

Generate precise contacts to the Descendant and preserve:

- planet and aspect type to DSC;
- continuous orb and configured maximum orb;
- applying/separating state using moving angles, not a static-angle shortcut;
- planet dignity, angular house placement and relevant forensic role; and
- whether the same testimony is already counted through house placement or the
  DSC ruler.

The survivability semantics are deliberately narrow:

- DSC contacts can intensify the opponent/perpetrator axis;
- ASC, MC, and IC contacts remain contextual and do not change survivability;
  and
- benefic DSC contacts require a separate tested support hypothesis before
  they can affect the score.

A contact should affect survivability only when its planet and role carry
independent danger or support meaning and it links to the declared target. For
example, Mackenzie's exact Pluto-DSC conjunction may reinforce an
opponent/destructive channel, but it should not become a flat angularity fatal
bonus. The exploratory audit already found that a generic count of three
or more angular malefics occurred in `0/25` fatal-labeled versus `4/9`
nonfatal-labeled cases, so undifferentiated angularity is an unsafe shortcut.

## 6. Exploratory feature audit

A read-only diagnostic combined 34 currently labeled cases from the curated
datasets and the locked aviation stress set: 25 fatal-labeled and 9
nonfatal-labeled. These sets are small, imbalanced and partly developmental;
the counts below are hypothesis-generating only.

| Candidate testimony | Fatal cases | Nonfatal cases | Interpretation |
| --- | ---: | ---: | --- |
| Moon dispositor hard to seventh ruler | 2/25 | 0/9 | interesting but sparse; Mackenzie also has it |
| Tight hard Mars-Uranus contact (<=3 degrees) | 3/25 | 0/9 | possible shock channel; too sparse to weight |
| Third ruler hard-afflicted | 9/25 | 4/9 | common and non-specific |
| Three or more angular malefics | 0/25 | 4/9 | points the wrong way in this sample; reject as a fatal shortcut |

The exact compound `Moon dispositor -> seventh/eighth ruler in a death house`
occurred in Mackenzie but not in those 34 labeled cases. That makes it a useful
feature to collect, not evidence for a weight. More transport cases are needed
to determine whether it generalizes or is effectively a one-case rule.

## 7. Optional empirical evidence layers

The product should keep three outputs separate:

### Layer 1: symbolic outcome pressure

Chart-only, explicitly unvalidated, qualitative, with complete rule provenance
and no probability language.

### Layer 2: observed mechanism-risk context

Optional factual inputs, each tagged with source and observation time:

- pre-impact speed, measured delta-V, crash pulse and acceleration;
- impact direction/type, rigid versus deformable object, overlap and angle;
- compartment intrusion and occupant contact points;
- rollover and ejection;
- restraint use, airbag deployment/performance and seat/recline position;
- vehicle type, mass, model year and safety design;
- occupant age, size and pre-existing vulnerability;
- time to discovery, extrication and emergency response; and
- confidence/missingness for every field.

This layer can say that a mechanism is empirically high-risk. It must not claim
that the chart predicted those facts. In Mackenzie, 100 mph into a brick
building, no braking, and delayed discovery are retrospective observed facts.
They are not permissible chart-only inputs and cannot be used to tune the
Mackenzie chart result without creating leakage.

### Layer 3: clinical survival estimation

Only when individual injury data and a medically appropriate, validated model
are available. Candidate inputs include anatomical injury severity (AIS/ISS),
physiology such as Glasgow Coma Scale, systolic blood pressure and respiratory
rate, age, mechanism and care context. This is outside the astrology engine's
current scope and should never be reconstructed from planetary features.

A combined display may show all three panels, but it should not blend them into
one number unless the product is explicitly renamed and validated as a hybrid
model.

## 8. Proposed chart-only algorithm shape

```text
target = resolve_survivability_target(request_or_fixture)
if target is unspecified:
    suppress nonfatal/fatal directional claim
    return target_scope=unspecified, outcome_band=indeterminate_target

base = current deduplicated survivability components
bridge = evaluate_victim_dispositor_death_bridge(features)
shock = evaluate_transport_shock_cluster(features)
angle_contacts = evaluate_planet_to_angle_contacts(features)

transport_fatal_gate = (
    mechanism.transport_harm
    and bridge.strong
    and (
        direct_victim_danger
        or shock.strong
        or route_death_link.strong
        or angle_contacts.target_linked_danger
    )
)

fatal_mechanism_context = (
    existing_non_transport_fatal_context
    or transport_fatal_gate
)

return:
    symbolic outcome band
    target scope
    component provenance
    missing-data flags
    counterfactual result with each candidate family removed
```

The bridge, shock and route-death feature families should first be logged with
zero score. Only then should a development-only search consider modest weights
and thresholds under leave-one-family-out evaluation.

## 9. Validation plan and promotion gates

### Phase 0: repair the contract

- add explicit target scope and outcome counts to every scored fixture;
- mark Mackenzie as mixed for all occupants and all-fatal for the passenger
  victim group;
- distinguish current engine observations from historical baselines;
- regenerate dashboard goldens from current source or label historical ones;
- make stale-baseline detection fail when a fixture claims a result different
  from the current route; and
- keep the axis issues FAC-001 and FAC-002 separate from survivability.

### Phase 1: instrument without scoring

Emit the proposed bridge, shock, planet-to-angle contacts, route severity,
reception, orb and dynamic features. Add provenance and
`scoring_eligible=false`. Audit missingness and correlated feature families.

### Phase 2: build a transport development set

Create a source-backed, versioned set with road, aviation, marine and rail
events where appropriate. Stratify by:

- all survived, survival-dominant, mixed, fatal-dominant and all fatal;
- individual versus occupant-group target;
- single versus multiple occupants;
- crash family and impact type; and
- exact time versus bounded interval, with sensitivity times.

Mackenzie and Idaho are development probes, not future holdouts. The existing
eight-case aviation file remains locked and must not be used to choose weights.
The 30-case retrospective set remains contaminated.

### Phase 3: development-only selection

- calculate the required sample size from outcome prevalence, candidate
  parameters and intended metrics rather than choosing an arbitrary case count;
- use leave-one-event-family-out and nested resampling;
- compare every candidate with the frozen `deduplicated_v2` baseline;
- run ablations for each new evidence family;
- include survivor guardrails and mixed-outcome cases;
- test event-time uncertainty and supported house systems;
- use permutation/negative controls; and
- reject a candidate that only improves Mackenzie or depends on fixture prose.

### Phase 4: locked external evaluation

Freeze the chosen policy before running a new untouched transport holdout.
Report confusion matrices, balanced accuracy, macro-F1, class recall and
bootstrap confidence intervals. If probabilities are ever introduced, also
report calibration plots, calibration intercept/slope, Brier score and log
loss. Do not call the current symbolic score a probability.

Promotion should require a material improvement with uncertainty bounds and no
material regression on the locked aviation set, nonfatal violence survivors,
abduction survivors, and mixed group outcomes. A result near chance on an
untouched set is a reason not to promote the new weights.

## 10. Devil's-advocate review

The strongest objection is that adding chart parameters may only make a
retrospective symbolic system more elaborate. The current locked aviation
result is 4/8, the data are small, and no scientific validation links these
astrological features to survival. A tight Mackenzie-specific compound can be
perfectly interpretable and still be overfit.

Adding real crash variables would likely make the output more factually
grounded, but it would answer a different question and turn the product into a
hybrid forensic-risk tool. It would not validate the astrology layer. The
ethical and technically honest response is to keep the layers separate,
preserve `is_statistical_probability=false`, and avoid use for medical,
emergency, legal or investigative decisions.

There is also a narrower counterargument: for the all-occupant target,
Mackenzie's `Moderate` level may be directionally compatible with a mixed
outcome. The demonstrably incorrect parts are the undefined target, the
`nonfatal_tilt` wording for the deceased victim group, the unscored/stale
fixture claims, and the absence of a principled transport-severity stage.

## Recommended implementation order

1. Fix target scope, outcome taxonomy, stale fixture prose and golden drift.
2. Add zero-weight instrumentation for the victim-dispositor/death bridge and
   compound transport-severity channels, including precise planet-to-angle
   contacts.
3. Curate a sufficiently powered transport development set and reserve a new
   untouched holdout.
4. Evaluate candidate feature families and ablations; do not tune on Mackenzie
   or the existing locked aviation cases.
5. Only after external evaluation, decide whether any chart-only scoring change
   is promotable.
6. If empirical crash context is desired, add it as a separate, explicitly
   hybrid panel with source, timing, missingness and uncertainty.

## Production follow-up — 2026-08-04

The DSC-only weighting component is implemented in the default
`deduplicated_v3_descendant_aspects` policy. It moves Mackenzie to
`Lower/fatal_pressure_dominant`, leaves the Idaho fixture unchanged, improves
two scored cases with secondary factors off and one with them on, and produces
no scored exact-label regression across 76 scored fixtures in either route
mode. ASC, MC, and IC contacts do not affect survivability.

The production rule also requires independent scored harm context before a DSC
contact can add pressure. This guard was added after the full forensic suite
found a clean-release abduction survivor whose band would otherwise regress.
The completed suite passes `283` tests and `130` subtests.

See `FORENSIC_SURVIVABILITY_DESCENDANT_ASPECT_IMPLEMENTATION_2026-08-04.md` for
the production policy, full fixture results, risks, and reproduction commands.
