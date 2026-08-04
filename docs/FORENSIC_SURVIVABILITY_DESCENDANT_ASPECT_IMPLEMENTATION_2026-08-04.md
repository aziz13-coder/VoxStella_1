# Forensic Survivability Descendant-Aspect Implementation — 2026-08-04

## Implemented decision

The forensic survivability engine now weights selected hard aspects to the
Descendant under the default `deduplicated_v3_descendant_aspects` policy.

This component is DSC-only. It does not use the Ascendant, MC, or IC as a
survivability input. Those angles may remain useful elsewhere as contextual
forensic testimony, but they do not change the victim-state score here.

The production change was accepted because the full fixture comparison showed
two additional exact alignments with secondary factors off, one additional
alignment with them on, no scored exact-label regression, and the intended
correction in Mackenzie. Every future weight change must be replayed against
the complete fixture corpus before acceptance.

## Production rule

The Descendant component evaluates:

- conjunction, square, or opposition to the DSC;
- Mars and Saturn at full weight;
- Uranus and Pluto at a 0.75 multiplier;
- a maximum orb of 3 degrees using the engine's existing orb decay;
- only the strongest Mars/Saturn contact and the strongest Uranus/Pluto
  contact, preventing correlated contacts within a family from stacking; and
- a total raw-pressure cap of 4.5.

The selected pressure is added to fatal pressure, not generic danger. For a
contact to be applied, the scorer must first have independent harm context from
a scored violence category, a fatal mechanism finding, or transport harm. The
DSC aspect cannot establish both that harm occurred and how severe it was. For
a transport case it can activate fatal mechanism context only when both a
transport-harm finding and nonzero DSC pressure are present. The result also
reports a counterfactual classification with the DSC component removed.

The component emits:

- planet, aspect to DSC, orb, family, raw pressure, and forensic role;
- raw and context-adjusted fatal-pressure deltas;
- harm-context eligibility and the reason a detected contact was or was not
  applied;
- score, level, and outcome band without DSC aspects;
- classification-change flags; and
- whether the compound transport gate was activated.

Applying/separating state is not available from the current static chart
snapshot, so every contact explicitly records that limitation.

## Excluded angle testimony

ASC, MC, and IC contacts are not survival weights. In particular, Mackenzie's
Jupiter contact near the MC is not treated as survival support. MC testimony is
more naturally public/authority manifestation, while IC testimony concerns
scene or end-of-matter context; neither has been shown to improve the declared
victim-state target.

Venus and Jupiter contacts to the DSC are also not included in this pressure
component. The small labeled audit did not support a generic benefic-on-angle
survival bonus: close benefic horizon contacts were also present in fatal
cases. A future support proposal would require a separate hypothesis and a
complete fixture replay.

## Mackenzie fixture

The production engine finds Pluto conjunct the Descendant with a 0.027-degree
orb. Because the aspect is calculated directly to the DSC, it uses the
conjunction weight and contributes 2.43 raw fatal pressure.

| Mode | `deduplicated_v2` baseline | Production v3 | Change |
|---|---|---|---|
| Secondary factors off | `Higher / nonfatal_tilt`, 3.35 | `Lower / fatal_pressure_dominant`, 0.92 | level and band corrected |
| Secondary factors on | `Moderate / nonfatal_tilt`, 2.99 | `Lower / fatal_pressure_dominant`, 0.56 | level and band corrected |

The new result fits the two deceased passengers when they are the declared
victim group. The current fixture still lacks a scored survivability target and
does not distinguish that group from all three occupants, whose outcome is
mixed because the driver survived. The comparison therefore records Mackenzie
as `not_scored`, not as a benchmark improvement.

## Idaho fixture

The Moscow, Idaho four-victim fixture's declared midpoint has no qualifying DSC
pressure contact. Its midpoint result remains exactly:

- `Lower / fatal_pressure_dominant`;
- score -2.92; and
- `unchanged_aligned` against the four direct homicide victims.

Across the official 04:00–04:25 event interval, the level and band remain
stable. The raw score is time-sensitive: it is -2.92 at 04:00 and the 04:12:30
midpoint, and -4.14 at 04:25 as a DSC contact enters range. The Idaho benchmark
now reports classification stability and raw-score stability separately.

## Complete fixture replay

The production comparison covers 88 unique cases across every fixture set that
carries survivability expectations, including 76 scored cases and 12 unscored
development probes. It includes the five general forensic datasets, the locked
aviation stress set, the 12-case stratified survivability set, and the
contaminated 30-case active-shooter retrospective set. The last set is a
regression diagnostic, not untouched validation.

| Route mode | v2 exact alignment | v3 exact alignment | Improved | Regressed |
|---|---:|---:|---:|---:|
| Secondary factors off | 47/76 (61.84%) | 49/76 (64.47%) | 2 | 0 |
| Secondary factors on | 48/76 (63.16%) | 49/76 (64.47%) | 1 | 0 |

The improvements with secondary factors off are Pine Kirk and Cooks Corner;
both change from `Moderate/mixed_nonfatal` to
`Lower/fatal_pressure_dominant`. With secondary factors on, Pine Kirk is
already aligned before the DSC component, while Cooks Corner remains the one
new exact alignment.

all internal movement:
Twenty of 88 cases contain a qualifying DSC contact; 14 pass the independent
harm-context gate and receive pressure. Exact-label agreement does not capture
all internal movement:
all internal movement:

- Geoffrey Paschel's nonfatal kidnapping stays within its accepted
  `Moderate/risk_loaded_survival` classification, while its score moves from
  -2.31 to -4.49 with secondary factors off;
- the Romanian journalists clean-release fixture initially exposed a survivor
  regression, which led to the general harm-context gate; it now remains
  `Moderate/nonfatal_tilt`;
- Southwest 1380 stays `Higher/nonfatal_tilt` because a DSC contact alone is
  not permitted to establish harm; and
- TWA 800, American Eagle 4184, and Route 91 expose DSC contacts but do not
  apply them because their route payloads lack independent scored harm context.
  Those are upstream mechanism-detection gaps, not reasons to bypass the gate.

These cases should be reviewed next. A future change must improve their stated
target without breaking survivor, abduction, or event-time guardrails, and it
must again be tested on all fixtures.

## Reproduction

Compare v2 and the production policy over all configured datasets:

```powershell
python backend\forensic_survivability_descendant_aspect_comparison.py
```

Repeat with secondary factors enabled:

```powershell
python backend\forensic_survivability_descendant_aspect_comparison.py --secondary-factors
```

Inspect Mackenzie with full provenance:

```powershell
python backend\forensic_survivability_descendant_aspect_comparison.py `
  --dataset tests\fixtures\forensic_netflix_true_crime_2025_2026_cases.json `
  --case-id mackenzie_shirilla_the_crash `
  --secondary-factors `
  --json
```

The output remains a transparent symbolic rule total, not a statistical
probability and not a medical, legal, or investigative conclusion.
