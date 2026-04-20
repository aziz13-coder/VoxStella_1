# Manson Drift Root-Cause Audit

## Scope

This note traces the Manson exploratory drift back to the specific forensic rules and feature helpers that produced it.

Goal:

- identify where the engine drifted,
- determine whether the root causes are general rather than case-specific,
- tie any proposed fix direction back to the forensic source texts already in the repo.

This is analysis only. No code changes are proposed or applied in this note.

## Executive Summary

The drift is general and fixable.

It does **not** come from one bad Manson edge case. It comes from a small cluster of rule-design problems:

1. family and child rules fire on weak proxies,
2. hidden-house logic is being treated as abduction logic,
3. water signatures are too permissive,
4. public-axis rules are too easy to trigger,
5. hard-affliction is computed too loosely.

Those issues are generic and will affect other cases beyond Manson.

## Where The Drift Came From

### 1. Family and child drift

Primary misfiring rules:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:129) `family_domestic_moon_signature`
- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:150) `family_home_axis_under_pressure`
- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:221) `child_family_overlap`

Supporting feature helper:

- [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py:70) `_planet_hard_afflicted`

Observed drift:

- Tate `01:15` and LaBianca `02:00` both fired family and child findings even though neither case is a family-killing chart in the intended sense.

Why it fired:

- Tate `01:15`
  - `Moon.sign = Cancer`
  - `fourth_ruler_hard_afflicted = true`
  - `fifth_ruler_house = 4`
- LaBianca `02:00`
  - `Moon.sign = Cancer`
  - `fourth_ruler_hard_afflicted = true`
  - `first_ruler_house = 4`
  - `seventh_ruler_house = 4`

The problem is structural:

- `family_domestic_moon_signature` allows family activation from a broad `any` condition that includes:
  - afflicted 4th ruler,
  - Moon in Cancer plus one more pressure flag.
- `child_family_overlap` allows child/family activation when:
  - `counts.5 >= 1`, or
  - `fifth_ruler_house in [4, 5, 8, 12]`.

Those are too weak to classify family or child involvement on their own.

## Source Basis

The family-murder source material is more specific than the current rules.

Relevant source:

- [Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Exploring%20Forensic%20Astrology%20The%20Secrets%20Behind%20Famous%20Family%20Murders%20(B.%20D.%20Salerno)%20(Z-Library).txt)

What that source supports:

- spouse, child, parent, and family cases are treated as **distinct role-patterns**,
- child cases rely on explicit 5th-house child context,
- spouse cases rely on explicit 7th-house partner context,
- family homicide is argued through clustered kinship significators under death/malefic pressure, not through Moon-in-Cancer alone.

Example from the source:

- Laci Peterson is read through a compound pattern:
  - victim ruler tied to death,
  - 5th-house child context because of pregnancy,
  - Moon as wife/mother,
  - direct stress from the partner axis.

That is materially narrower than the current rules.

## General Fix Direction

Safe generic fix:

1. Remove `Moon.sign = Cancer` as a near-standalone family trigger.
2. Remove `counts.5 >= 1` as a child-victim trigger.
3. Require at least:
  - one explicit kinship role marker,
  - one death/malefic marker,
  - one relational cluster marker.

Concretely:

- family should require a real 4th/5th/10th/7th cluster or a direct kinship-ruler/death linkage,
- child should require stronger 5th-house death pressure than just one 5th-house occupant or a 5th ruler in the 4th.

## 2. Abduction drift

Primary misfiring rule:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:275) `abduction_missing_person_signature`

Supporting house rules:

- [house_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/house_rules.yaml:14) `first_ruler_rules_8th`
- [house_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/house_rules.yaml:25) `strong_12th_emphasis`

Observed drift:

- Tate `04:10` and LaBianca `08:00` both drifted into abduction/missing-person logic.

Why it fired:

- Tate `04:10`
  - `emphasis12_strong = true`
  - `first_ruler_in_8_or_12 = true`
- no explicit abductor indicator was needed.

The rule currently permits:

- hidden-house pressure (`12th`) plus
- death pressure (`1st` or `5th` tied to `8th/12th`)

to stand in for actual abduction logic.

## Source Basis

Relevant sources:

- [Forensic Astrology for Everyone You Dont Need to be an Astrologer to Locate Lost Objects, Find Missing Persons, Solve… (Caroline J. Luley) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Forensic%20Astrology%20for%20Everyone%20You%20Dont%20Need%20to%20be%20an%20Astrologer%20to%20Locate%20Lost%20Objects,%20Find%20Missing%20Persons,%20Solve%E2%80%A6%20(Caroline%20J.%20Luley)%20(Z-Library).txt)
- [Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Forensics%20by%20the%20Stars%20Astrology%20Investigates%20(B.%20D.%20Salerno)%20(Z-Library).txt)

What those sources support:

- Luley treats the 12th as hidden areas, confinement, burial, and death pattern development.
- That means 12th-house pressure is a **general concealment/death signal**, not automatically an abduction signal.
- Salerno's Lindbergh discussion is much narrower:
  - Mars in Pisces,
  - Mars opposite Neptune,
  - Mars ruling the 7th of the abductor,
  - servant/cooperation logic from the 6th.

That is a real abduction compound pattern.

## General Fix Direction

Safe generic fix:

1. Split `hidden/death` from `abduction/missing`.
2. Require at least one explicit abductor/opponent indicator for abduction:
  - 7th-ruler involvement,
  - Mars-Neptune kidnapping pattern,
  - 7th + 6th cooperation pattern,
  - or equivalent perpetrator-concealment linkage.
3. Keep pure 12th/8th pressure as concealment or hidden-victim evidence, not abduction by default.

## 3. Water drift

Primary misfiring rule:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:246) `water_disappearance_signatures`

Observed drift:

- Tate `04:10` and LaBianca `06:00` both picked up water logic.

Why it fired:

- Tate `04:10`
  - `Moon.sign = Cancer`
  - `Moon.house = 12`
- LaBianca `06:00`
  - `Moon.sign = Cancer`
  - `Moon.house = 12`
  - `water_cusp_4_8_12 = 3`

The current rule allows water classification from:

- Moon in a water sign plus Moon in `4/8/12`,
- or water cusps plus one death/concealment flag.

That is too permissive for categorical drowning/disposal inference.

## Source Basis

Relevant source:

- [Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Forensics%20by%20the%20Stars%20Astrology%20Investigates%20(B.%20D.%20Salerno)%20(Z-Library).txt)

What that source supports:

- water indicators can be meaningful,
- but even multiple water indicators may indicate concealment only loosely.

The strongest local example actually warns against over-reading:

- a chart suggested drowning because:
  - 4th house Cancer,
  - 8th house Scorpio,
  - Pisces fortune,
- but the body was found in snow, not in the lake.

That means water symbolism is suggestive, not categorical, unless reinforced strongly.

## General Fix Direction

Safe generic fix:

1. Require at least two independent water signals.
2. Require one of them to be more specific than Moon-in-water:
  - Neptune linkage,
  - water on death/end houses,
  - fixed-star support,
  - or explicit water-disposal context.
3. Demote single Moon-water triggers from category-level output to weak contextual evidence.

## 4. Public-axis drift

Primary misfiring rules:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:356) `public_or_authority_axis_foregrounded`
- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:485) `public_axis_saturated`

Observed drift:

- Hinman `06:00` and `12:00` drifted into public/authority logic.

Why it fired:

- `Sun.angular = true`
- plus a permissive 10th-house condition such as:
  - `counts.10 >= 1`, or
  - `tenth_ruler_house in [5, 10]`

That is far too broad.

## Source Basis

Relevant source:

- [Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Exploring%20Forensic%20Astrology%20The%20Secrets%20Behind%20Famous%20Family%20Murders%20(B.%20D.%20Salerno)%20(Z-Library).txt)

What that source supports:

- public visibility can matter,
- angular luminaries can describe public or sudden death in a public figure case,
- but that is contextual reading, not a generic case-type classifier.

The current rule base turns weak visibility markers into a `Public` category too easily.

## General Fix Direction

Safe generic fix:

1. Require repeated 10th-house concentration before classifying a case as public/celebrity.
2. Treat angular Sun alone as supporting context, not category-level evidence.
3. Keep `Public` as a contextual modifier unless there is explicit multi-factor 10th-house saturation.

## 5. Hard-affliction is too loose

Feature helper:

- [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py:19) `HARD_MALEFIC_PLANETS`
- [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py:70) `_planet_hard_afflicted`

Observed effect:

- Tate `01:15` family logic was helped along by `fourth_ruler_hard_afflicted = true` even though the underlying aspect was a wide Sun-Saturn square with `orb = 7.74`.

Current behavior:

- any conjunction/square/opposition to `Mars`, `Saturn`, `Uranus`, or `Pluto` counts,
- there is no orb threshold,
- there is no applying/separating threshold,
- there is no distinction between tight and loose affliction.

That makes downstream rules too easy to trigger.

## Source Basis

This is not a source conflict so much as a strength-control problem.

The books read these patterns as compounded testimonies, not as any harsh aspect regardless of distance. A wide square used as a binary trigger is too coarse for the way the source analyses are argued.

## General Fix Direction

Safe generic fix:

1. Add orb gating to `_planet_hard_afflicted`.
2. Prefer tighter or applying aspects for binary rule triggers.
3. Optionally split:
  - `hard_afflicted_strict`
  - `hard_afflicted_loose`

Then use only the strict version in family, child, abduction, and accident rules.

## 6. Disaster drift is also too permissive

Primary misfiring rule:

- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:530) `waterborne_accident_or_disaster_pattern`

Observed drift:

- Hinman `00:00` falsely emitted `Disaster`.

Why it fired:

- a 9th-house indicator,
- one or more water-cusp markers,
- angular malefic pressure,
- and the absence of certain death-pattern booleans.

That is enough to describe many ordinary charts and should not be strong enough to classify a homicide case as accident/disaster.

## Source Basis

The local forensic texts support travel, water, and disaster interpretation, but again as compound context. Nothing in the local corpus supports promoting a case to disaster classification on a light travel-plus-water reading with no stronger corroboration.

## General Fix Direction

Safe generic fix:

1. Tighten disaster classification to require more explicit accident signatures.
2. Require stronger travel/mechanical/disaster corroboration before assigning the category.
3. Keep the current logic, at most, as weak contextual evidence.

## Recommended General Patch Order

1. Tighten `_planet_hard_afflicted` in [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py:70).
2. Narrow family and child rules in [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:129) and [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:221).
3. Split hidden/death logic from abduction logic in [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:275).
4. Raise the threshold for water categorization in [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:246).
5. Demote or tighten public/disaster rules in [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:356), [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:485), and [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml:530).

## Bottom Line

The drift is general.

The most defensible generic fixes are:

- make rule triggers stricter,
- separate contextual signals from categorical ones,
- and stop using single weak testimonies as family, child, abduction, water, public, or disaster labels.

Those changes are source-consistent and should improve behavior across the forensic engine, not only for Manson-related cases.

## Secondary Testing Caveat

There is also a non-engine issue in the replay comparison harness:

- [forensic_case_corpus_utils.py](C:/Users/sabaa/Downloads/codexhorary/tests/forensic_case_corpus_utils.py:135)

Current behavior:

- axis matching is keyword-based across finding titles, categories, and rationales,
- so a non-violence rule can still satisfy `violence_homicide` if its rationale contains words like `violence` or `death`.

Example effect:

- Tate `01:15` was still counted as matching `violence_homicide` in one probe because `malefics_in_6th` carries a rationale mentioning violence, even though the finding itself is not a homicide classifier.

This does **not** cause the engine drift, but it can hide it.

Safe fix direction:

1. Prefer category and rule-id based matching over rationale keyword matching.
2. Treat rationales as explanatory text, not primary replay truth.
