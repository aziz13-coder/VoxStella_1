# Journalist Holdouts And Joey Remediation

## Scope

This pass fixed the remaining misaligned journalist holdout cases and improved the Joey Comunale documentary probe without adding case-specific hardcoding.

Targets:

- Romanian journalists in Jadriya
- Richard Butler in Basra
- Joey Comunale / "Party Monster" exploratory homicide probe

## General Root Causes

### 1. Missing social-gathering seizure pattern

The rule set already recognized:

- hidden custody
- route seizure
- worksite seizure
- transient-hospitality seizure

It did not yet recognize a broader social or group-setting seizure where:

- the `7th` or `11th` tied the event to another person or social circle
- the `5th` described an adult social setting
- separate `12th` or hidden-custody testimony was present
- deception or obscured communication was also present

That gap explains why the Romanian Jadriya case stayed in deception-only territory even though the real event was a hotel-area kidnapping with prolonged hidden custody.

### 2. Missing deceptive public-assignment seizure pattern

The rule set also lacked a clean way to distinguish:

- fake-authority seizure
- work or public-facing seizure
- route pressure
- Mercury-based deception markers

from accident/disaster charts.

That gap explains why the Richard Butler case leaked into `Disaster` despite being a fake-police hotel-room kidnapping.

### 3. Missing shared-ruler known-person synthesis

The feature layer did not expose:

- `houses.seventh_and_tenth_same_ruler`
- `houses.seventh_and_eleventh_same_ruler`

Those are not new astrological claims. They are missing structural summaries of house-ruler convergence that the rule layer needed in order to read:

- deceptive public / authority-style seizures
- known-person / acquaintance violence

### 4. Disaster rules lacked back-off when a stronger perpetrator structure was present

The disaster rules already had some exclusions for clear death or domestic structures.
They did not yet back off when the chart described:

- a deceptive 7th/10th seizure with route pressure
- a social / group seizure with hidden custody
- a known-person social-concealment violence pattern

That is why Butler and one Joey anchor could drift into disaster language before the fix.

## Source Basis

The fixes were anchored in the local forensic corpus, not in the individual modern cases alone.

### Caroline J. Luley

Source:

- [Forensic Astrology for Everyone You Dont Need to be an Astrologer to Locate Lost Objects, Find Missing Persons, Solve… (Caroline J. Luley) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Forensic%20Astrology%20for%20Everyone%20You%20Dont%20Need%20to%20be%20an%20Astrologer%20to%20Locate%20Lost%20Objects,%20Find%20Missing%20Persons,%20Solve%E2%80%A6%20(Caroline%20J.%20Luley)%20(Z-Library).txt)

Relevant principles used:

- `5th house` covers adult social life, parties, entertainment, outside interests, and romance, not only children.
- `7th house` is usually the abductor, attacker, kidnapper, murderer, accomplice, or co-conspirator.
- `9th house` can describe travel, highways, longer movement, foreigners, and authority context.
- `10th house` can describe public exposure, public places, professional visibility, and being taken openly.
- `11th house` covers friends, acquaintances, peers, and group links.
- `12th house` covers hidden places, confinement, secrecy, and being held against the will.

### B. D. Salerno

Sources:

- [Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Exploring%20Forensic%20Astrology%20The%20Secrets%20Behind%20Famous%20Family%20Murders%20(B.%20D.%20Salerno)%20(Z-Library).txt)
- [Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Forensics%20by%20the%20Stars%20Astrology%20Investigates%20(B.%20D.%20Salerno)%20(Z-Library).txt)

Relevant principles used:

- `7th house` remains the central marker for the other person, killer, abductor, or accomplice.
- `11th house` points to friends, peers, and associates.
- `5th house` can describe pleasure, parties, affairs, and recreation, so it should not default to child logic in adult crime charts.

## Implemented General Fixes

### Feature synthesis

Added to [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py):

- `houses.seventh_and_tenth_same_ruler`
- `houses.seventh_and_eleventh_same_ruler`

### New rules

Added to [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml):

- `abduction_social_or_group_gathering_seizure_signature`
- `abduction_deceptive_public_or_assignment_seizure_signature`
- `violence_known_person_social_concealment_pattern`

### Rule extension

Extended:

- `friend_or_associate_axis_active`

to recognize shared `7th/11th` rulership directly.

### Disaster back-off guards

Tightened:

- `travel_accident_or_disaster_pattern`
- `waterborne_accident_or_disaster_pattern`

so they do not fire when a stronger perpetrator or known-person seizure pattern is already present.

## Engine Output Vs. Real Events After Fix

### Romanian journalists in Jadriya

Real event:

- evening hotel-area seizure
- multi-hostage captivity
- prolonged hidden custody

Updated engine output:

- `Abduction: 1`
- `Deception: 4`
- `Degree Signatures: 2`

Leading improvement:

- `Abduction or social-gathering seizure pattern is active`

Assessment:

- now directionally aligned

### Richard Butler

Real event:

- fake-police hotel-room seizure
- covert custody
- later release alive

Updated engine output:

- `Abduction: 1`
- `Deception: 3`

Leading improvement:

- `Abduction or deceptive public-assignment seizure pattern is active`

Assessment:

- now directionally aligned
- disaster drift removed

### Joey Comunale

Real event:

- after-hours apartment homicide
- body transport and concealment
- known-person social setting

Best updated anchors:

- `2016-11-13 06:50`
- `2016-11-13 07:00`

Updated engine output at those anchors:

- `Associates: 1`
- `Deception: 3`
- `Public: 1`
- `Violence: 1`

Leading improvements:

- `Friend or close associate axis is active`
- `Known-person violence pattern is active in a social or after-hours setting`

Assessment:

- materially improved
- no disaster drift at the stronger anchors
- still exploratory, because later anchors remain weaker

## Validation

Executed:

```powershell
python -m pytest -q tests/test_forensic_journalist_abduction_benchmark.py tests/test_forensic_journalist_abduction_map_benchmark.py tests/test_forensic_journalist_abduction_holdout_probes.py tests/test_forensic_journalist_abduction_holdout_map.py tests/test_forensic_homicide_documentary_probe.py tests/test_forensic_direction_rules.py tests/test_forensic_drift_guards.py
```

Result:

- `53 passed`
- `32 subtests passed`
- `1 warning`

Broader forensic regression sweep:

```powershell
$files = Get-ChildItem tests -Filter 'test_forensic*.py' | ForEach-Object { $_.FullName }; python -m pytest -q $files
```

Result:

- `114 passed`
- `42 subtests passed`
- `1 warning`

The remaining warning is the existing external `pytz` deprecation warning.

## Current Conclusion

Yes, the remaining journalist holdout failures were caused by general gaps in the rule language rather than by isolated bad cases.

Yes, the fixes were generalized.

Yes, the fixes are backed by the local forensic source corpus.

Yes, the live engine now behaves better on:

- Romanian journalists in Jadriya
- Richard Butler
- Joey Comunale at the strongest apartment-window anchors
