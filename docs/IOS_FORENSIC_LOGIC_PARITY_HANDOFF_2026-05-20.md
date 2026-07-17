# iOS Forensic Logic Parity Handoff

Date: 2026-05-20

Purpose: keep the iOS app aligned with the forensic logic currently implemented in the desktop/backend app.

This document covers the two recent forensic logic upgrades:

1. asteroid + special-degree secondary factors
2. McIntosh-derived secondary forensic patterns from `Criminal Astrology: Volume I Understanding Crime Charts`

## Porting Principle

Do not port these signals into primary case-axis detection as direct findings.

In the current backend, asteroid/special-degree/McIntosh testimony is a secondary layer:

- it may move survivability scoring
- it may add small relationship score deltas
- it exposes descriptive evidence and axis hints
- it does not append to the core `findings` list used for primary axis scoring

This is important. Directly promoting these signals into primary findings made axis output broader and less specific during benchmark work.

## Source Files To Mirror

Backend source:

- `backend/forensic/features.py`
- `backend/forensic/secondary_factors.py`
- `backend/forensic/survivability.py`
- `backend/forensic/relationship_status.py`
- `backend/fixed_stars.py`
- `backend/forensic/knowledge/fixed_star_meanings.yaml`
- `backend/astro_clock_api.py`

Packaged/app backend mirror:

- `frontend/backend/forensic/features.py`
- `frontend/backend/forensic/secondary_factors.py`
- `frontend/backend/forensic/survivability.py`
- `frontend/backend/forensic/relationship_status.py`
- `frontend/backend/fixed_stars.py`
- `frontend/backend/forensic/knowledge/fixed_star_meanings.yaml`

## Runtime Toggle

Backend route behavior:

- query arg absent: secondary factors enabled
- `secondary_factors=1`: enabled
- `secondary_factors=0`: disabled

iOS should treat the current production behavior as enabled by default, but keep a developer/debug flag to compare disabled versus enabled.

## Feature Extraction Required

The secondary layer needs these normalized inputs:

- planets with `longitude`, `sign`, `degree_in_sign`, `house`, dignity fields, and angular flags
- aspects keyed both ways or queryable both ways
- house rulers for houses 1, 3, 4, 5, 7, 8, 9, 10, 11, 12
- angles: Ascendant, Descendant, IC, Midheaven
- asteroid positions: Ceres, Pallas, Juno, Vesta, Proserpina
- fixed-star hits
- special-degree dictionary

Role mapping:

- 1st ruler: victim
- Moon: victim co-significator / moon
- 7th ruler: perpetrator
- 8th ruler: death
- 12th ruler: hidden/confinement
- 4th ruler: family/home
- 5th ruler: child
- 3rd and 9th rulers: route/transport
- 10th ruler: authority/public
- 11th ruler: associate/friend
- Ascendant: victim angle
- Descendant: perpetrator/relationship angle
- IC: family/home angle
- Midheaven: authority/public angle

## Constants

Use these current backend constants:

- special degree orb: `0.75` degrees
- asteroid conjunction orb: `1.0` degree
- McIntosh quindecile orb: `2.0` degrees from 165
- Descendant cluster orb: `12.0` degrees
- Mars on Descendant cusp orb: `2.5` degrees
- McIntosh hard-aspect orb: `6.0` degrees
- McIntosh conjunction orb: `7.0` degrees
- exact exaltation/fall degree orb: `0.75` degrees

Caps:

- relationship score deltas cap per label: `1.5`
- survivability fatal pressure cap: `1.2`
- survivability recovery support cap: `0.5`

## Asteroid Logic

Asteroids count only on tight conjunction to a relevant target.

Current scoring:

- Juno conjunct victim/perpetrator/relationship point, Ascendant, Descendant, or Venus:
  - `intimate_partner += 0.85`
- Ceres conjunct family/child/home/Moon/victim point, Moon, or IC:
  - `family += 0.65`
  - `recovery_support += 0.15`
  - child-victim hint if the target has child role
- Vesta conjunct family/home/victim/Moon point, Moon, IC, or Ascendant:
  - `family += 0.35`
  - `recovery_support += 0.15`
- Proserpina conjunct victim/perpetrator/Moon/death/hidden point, Ascendant, or Descendant:
  - `fatal_pressure += 0.20`
- Pallas conjunct authority/public/associate point:
  - `friend_acquaintance += 0.25`

Do not treat asteroid names as standalone evidence. They must contact a role-relevant point.

## Special Degree Logic

Special degrees count only when the degree lands on a relevant significator, ruler, or angle.

Current scoring:

- domestic partner axis:
  - `intimate_partner += 0.35`
- family axis:
  - `family += 0.30`
- violence/homicide axis:
  - `fatal_pressure += 0.30`
- abduction/deception axis tied to victim/Moon/death roles:
  - `fatal_pressure += 0.15`

Special degrees should produce evidence and axis hints, not primary findings.

## McIntosh-Derived Rules

Implemented as source-backed, role-gated secondary factors.

### Quindecile

Detect 165 degree aspects within `2.0` degrees.

Only count if at least one side is role relevant:

- victim
- perpetrator
- Moon
- death
- hidden
- relationship

Scoring:

- `fatal_pressure += 0.18`

### Descendant / 7th-House Stellium

Detect 3 or more relevant bodies in the 7th house or within `12.0` degrees of Descendant.

Watched bodies:

- Sun
- Moon
- Venus
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune
- Pluto
- North Node / Node

Require at least one of:

- Moon
- Mars
- Saturn
- Uranus
- Neptune
- Pluto

Scoring:

- `fatal_pressure += 0.30`

### Mars Square Pluto

Detect Mars square Pluto within `6.0` degrees.

Only count if Mars/Pluto pair has role relevance.

Scoring:

- `fatal_pressure += 0.25`

### Moon Conjunct Outer/Malefic Planet

Detect Moon conjunctions within `7.0` degrees to:

- Saturn
- Uranus
- Neptune
- Pluto

Scoring:

- `fatal_pressure += 0.22`

### Mars On Descendant

Detect Mars within `2.5` degrees of Descendant.

Scoring:

- `fatal_pressure += 0.25`

### Exact Exaltation/Fall Degree

Use exact dignity-degree proximity within `0.75` degrees.

Exaltation degrees:

- Sun: Aries 19
- Moon: Taurus 3
- Mercury: Virgo 15
- Venus: Pisces 27
- Mars: Capricorn 28
- Jupiter: Cancer 15
- Saturn: Libra 21

Fall degrees:

- Sun: Libra 19
- Moon: Scorpio 3
- Mercury: Pisces 15
- Venus: Virgo 27
- Mars: Cancer 28
- Jupiter: Capricorn 15
- Saturn: Aries 21

Scoring:

- victim or Moon exact exaltation:
  - `recovery_support += 0.20`
- perpetrator exact exaltation:
  - `fatal_pressure += 0.12`
- victim or Moon exact fall:
  - `fatal_pressure += 0.20`
- perpetrator exact fall:
  - `recovery_support += 0.10`

## Traditional Direction Payload

The McIntosh direction mapping is exposed as auxiliary/descriptive output only.

No scoring effect.

Planet directions:

- Sun: east
- Moon: northwest
- Mars: south
- Mercury: north
- Jupiter: northeast
- Venus: southeast
- Saturn: west

House directions:

- 1: east
- 2: north-northeast
- 3: northeast
- 4: north
- 5: north-northwest
- 6: northwest
- 7: west
- 8: south-southwest
- 9: southwest
- 10: south
- 11: south-southeast
- 12: southeast

iOS should display this only in a technical/detail view unless a later location benchmark validates scoring use.

## Fixed Star Additions

The fixed-star catalog and meanings now include these McIntosh-backed additions:

- Hyades
- Praesaepe
- North Asellus
- South Asellus
- Phecda
- Unukalhai
- Scheat

Current rule: descriptive evidence only unless another existing fixed-star pathway already uses the hit. Do not create new survivability/axis scoring from these stars without a fixed-star-specific benchmark.

## Expected Output Shape

Expose a `secondary_factor_analysis` object equivalent to the backend:

```json
{
  "enabled": true,
  "findings": [],
  "axis_hints": [],
  "relationship_score_delta": {
    "intimate_partner": 0.0,
    "family": 0.0,
    "friend_acquaintance": 0.0
  },
  "survivability_delta": {
    "fatal_pressure": 0.0,
    "recovery_support": 0.0,
    "net_score": 0.0
  },
  "evidence": [],
  "traditional_directional_analysis": {},
  "source_basis": [
    "special_degrees_require_relevant_significator_or_angle",
    "asteroids_require_tight_conjunction_to_relevant_point",
    "mcintosh_role_gated_patterns",
    "mcintosh_traditional_direction_mapping"
  ]
}
```

Survivability should also expose:

```json
{
  "secondary_factor_impact": {
    "enabled": true,
    "recovery_support_delta": 0.0,
    "fatal_pressure_delta": 0.0,
    "score_without_secondary_factors": 0.0,
    "score_delta": 0.0,
    "level_without_secondary_factors": "Moderate",
    "outcome_band_without_secondary_factors": "mixed_nonfatal",
    "level_changed": false,
    "band_changed": false,
    "evidence": []
  }
}
```

## Benchmark Decision

The logic stayed active because it improved survivability without hurting the other targets.

Results:

- 29-case development set: no metric drift
- 30-case holdout:
  - survivability accuracy `0.6000 -> 0.6333`
  - partial survivability `0.6167 -> 0.6500`
  - axis unchanged
  - relationship unchanged
- combined 59 cases:
  - survivability accuracy `0.6604 -> 0.6792`
  - partial survivability `0.6698 -> 0.6887`
  - axis balanced accuracy stayed `0.7551`
  - relationship macro-F1 stayed `0.5681`

Known improved holdout classification:

- `holdout_2022_tops_buffalo`
  - disabled: `Moderate / mixed_nonfatal`
  - enabled: `Lower / fatal_pressure_dominant`

## iOS Parity Checklist

- Keep secondary factors enabled by default.
- Keep a debug switch to disable secondary factors.
- Do not merge secondary findings into primary axis findings.
- Apply secondary fatal/recovery deltas inside survivability after light mediation.
- Apply relationship deltas only through `relationship_score_delta`.
- Cap deltas exactly as the backend does.
- Keep traditional directions descriptive.
- Keep the expanded fixed-star list descriptive unless benchmarked later.
- Add unit tests for quindecile, Descendant stellium, exact dignity degree, traditional direction payload, and fixed-star catalog presence.
