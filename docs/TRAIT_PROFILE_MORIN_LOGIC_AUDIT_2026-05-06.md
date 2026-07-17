# Trait Profile Morin Logic Audit

Date: 2026-05-06

## Scope

This audit checks whether the Trait Profile values shown in the frontend are backed by real backend logic, with Morin-style house determination as the main standard. It focuses on the runtime path used by the UI:

`GET /api/astro-clock/traits/profile`

## Morin Baseline Used For The Audit

Local source notes reviewed:

- `docs/moren_summary.md`
- `backend/house_influence.py`
- `backend/knowledge/basic_analysis_rules.json`
- `backend/traits/knowledge/morin_keywords.json`

The operative doctrine for this feature is:

- A planet needs a specific determination to a life area before it can meaningfully signify that area.
- The primary determination order is location, then rulership, then aspectual contact.
- A planet's nature must be filtered through its celestial state and terrestrial state.
- Applying and closer contacts should carry more weight than separating or wide contacts.
- Natural analogy is supporting context, not a replacement for actual house determination.

## Current Backend Wiring

The backend path is real and source-driven:

- `backend/astro_clock_api.py`
  - Resolves the active chart or requested manual/snap chart.
  - Computes chart metrics.
  - Computes house influence rows.
  - Builds per-planet area scores for trait rules.
  - Runs `TraitEngine.evaluate`.
- `backend/house_influence.py`
  - Scores occupation, rulership, aspect to cusp, exaltation, and triplicity.
  - Adds strength breakdowns from intrinsic nature, dignity, house position, motion, solar condition, orientation, elevation, and received aspects.
  - Builds `basic_analysis`, including determinator panels and synthesis lines.
- `backend/traits/engine.py`
  - Evaluates catalog rules against metrics.
  - Returns `score`, `raw_score`, `max_score`, support counts, evidence rows, polarity, band, and keyword enrichment.

## Issues Found

### 1. Planet Area Scores Were Too Relative

Previous behavior:

- `planet_area_scores` normalized each planet only against its own strongest area.
- That meant a weak planet could still produce `1.0` for its best area.
- This made `planet_area` trait rules look mathematically solid while ignoring absolute chart strength.

Why that conflicts with the Morin baseline:

- Morin determination requires both a routed area and an effective planet/state.
- A weak routed connection should not count the same as a dominant routed connection.

Resolution:

- `planet_area_scores` now uses a hybrid formula:

```text
score = sqrt(relative_strength * absolute_strength)
```

- `relative_strength` means the area's share within that planet's own determinations.
- `absolute_strength` means the area's weight compared with the strongest planet-area determination in the chart.
- Detailed metadata is also attached under `planet_area_score_details`.

### 2. Topic Map P/G/A Values Were Too Decorative

Previous behavior:

- Profession and Health topic maps showed `P/G/A` as `+`, `++`, or `+++`.
- Those symbols were based on share only and did not show actual strength.

Resolution:

- Topic maps now show real percentages plus summed influence strength:

```text
P 50% G 25% A 25% / 60.0
```

- `P` = presence/occupation.
- `G` = governance/rulership plus co-rulership.
- `A` = aspectual contact to the house cusp.
- The trailing value is the summed influence strength from the backend influence rows.

## Result

The key values now satisfy the non-ornamental rule:

- Trait scores are still the existing catalog rule score: `raw_score / max_score`.
- House influence rows remain backend values from `house_influence.py`.
- Planet-area trait supports now require both route relevance and chart-scale strength.
- Topic map channel values are no longer symbolic; they expose the actual influence distribution and total.

## Remaining Calibration Work

- Consider returning structured `evidence_factors[]` from the backend instead of evidence strings if the UI later needs factor bars.

## 2026-05-06 Expansion Pass

The first two remaining items above were completed in source.

Catalog expansion:

- Added Morin-backed `planet_area` rules for H1 temperament, H2 resources, H3 movement/messages, H4 home, H5 children/fertility, H6 service/labor, H7 contracts/alliances, H9 doctrine/journeys, H10 profession/office, and H11 friends/allies/support.
- Kept the expansion classical: Sun/Moon/Mercury/Venus/Mars/Jupiter/Saturn only. Modern-planet-only rules were not expanded because the local Morin knowledge layer is classical.
- Used moderate weights and `min` thresholds so these rules can corroborate a trait but do not replace the existing sign, planet-status, aspect, and house-emphasis logic.

Source basis:

- `docs/moren_summary.md`: planets need house determination by location, rulership, or aspect before they signify a specific life area.
- `backend/traits/knowledge/morin_keywords.json`: canonical house topics and planet keywords.
- `backend/knowledge/basic_analysis_rules.json`: house domain and natural significator support.

Benchmark expansion:

- Added direct Morin house-determination benchmark fixtures in `backend/trait_logic_benchmark_profiles.py`.
- The benchmark runner now supports source-backed direct metric cases in addition to public-figure route cases.
- Cluster checks can now require evidence tokens such as `Mars area[life]` or `Mercury area[health]`, so a case fails if the trait score is present but the house-determination support is missing.

Covered house-topic benchmark cases:

- H1 Mars temperament.
- H3/H9 Mercury-Jupiter learning and journeys.
- H4/H5 domestic and children/fertility topics.
- H6/H10 service and profession.
- H2/H11 resources and support.
- H7/H9/H10/H11 legal, social, and public-office topics.
