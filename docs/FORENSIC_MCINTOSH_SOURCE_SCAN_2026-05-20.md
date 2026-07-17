# McIntosh Criminal Astrology Source Scan

Date: 2026-05-20

## Local Source

Converted source:

- `extracted_text_docs/text_forensics/Criminal Astrology Understanding the Crime Charts (Kirsty McIntosh) (z-library.sk, 1lib.sk, z-lib.sk).txt`
- `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt`

Extraction summary:

- Source PDF: `C:\Users\sabaa\Downloads\Criminal Astrology - Understanding the Crime Charts (Kirsty McIntosh) (z-library.sk, 1lib.sk, z-lib.sk).pdf`
- Pages: 97
- Nonempty extracted pages: 96
- Handoff SHA-256: `92E9393302D9A7BBC2F3B45ECFE3CBA6B34A43807DC593F3AFF7270FB5C09DD0`

The text is page-marked and suitable for local AI retrieval.

## Current Logic Change Summary

The recent asteroid/special-degree change does not let those factors create primary forensic findings directly. It extracts asteroid and angle positions into the forensic feature payload, then computes a bounded `secondary_factor_analysis`.

That secondary analysis can move survivability and relationship scoring by small calibrated deltas, but it is kept out of the core findings list used for case-axis detection. This is deliberate because direct promotion into findings widened the signal and reduced axis specificity in benchmark runs.

The app route enables this analysis by default unless `secondary_factors=0` is passed. Benchmark runners can compare disabled versus enabled mode explicitly.

## McIntosh Points Already Mostly Covered

1. Victim/perpetrator assignment

   McIntosh uses the Ascendant/1st house for the victim or missing person and the Descendant/7th house for the perpetrator or open enemy. The engine already treats the victim and perpetrator significators around that 1st/7th axis.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:244`

2. Death/hidden-house pressure

   McIntosh repeatedly uses 8th-house and 12th-house testimony for death, concealment, captivity, or not being found. The coded directional/context rules already contain victim-ruler, death-house, and hidden-house pressure patterns.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:256`

3. Hard malefic contacts

   The source emphasizes Mars, Saturn, Pluto, Uranus, Neptune, and hard contacts when tied to the victim, perpetrator, Moon, or relevant cusps. The code already has broad malefic and forensic pressure logic, although some McIntosh-specific combinations are not yet modeled as named rules.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:1409`

4. Fixed-star testimony

   The engine already has a curated fixed-star dictionary and uses fixed-star hits in features. McIntosh reinforces Algol, Denebola, Antares, Zuben Algenubi, Scheat, and related violent or catastrophic stars.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:1200`

5. Emergency-call charts

   McIntosh treats 911/000 call charts as usable when the call start time is accurate. This supports the benchmark exclusion policy: the September 11 event is excluded, but ordinary "911 call" cases are not excluded just because the string `911` appears.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:197`

## New Knowledge Not Fully Represented In Code

1. Quindecile as obsession/separation testimony

   McIntosh explicitly watches the 165 degree quindecile for obsession, compulsion, disruption, and separation. The current feature extractor does not compute quindecile aspects as forensic evidence.

   Candidate implementation: add quindecile detection only for victim ruler, perpetrator ruler, Moon, 1st/7th rulers, and 7th/8th/12th rulers. Keep it low weight until benchmarked.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:1413`

2. Descendant or 7th-house stellium

   McIntosh describes repeated negative-outcome charts with stelliums over or around the Descendant/7th cusp, especially involving Moon, Mars, Pluto, Venus, Sun, Jupiter, Saturn, or Neptune opposition patterns. The current engine has house counts and many 7th-house rules, but no explicit `descendant_cluster` or `seventh_house_stellium` feature.

   Candidate implementation: compute a structured cluster feature when 3 or more relevant bodies are within the 7th house or near the Descendant, with stronger testimony if Moon/Mars/Pluto/Saturn/Neptune are included. Route it first into survivability pressure, not axis, then benchmark.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:1422`

3. Specific Mars-Pluto and Moon-outer-planet patterns

   The code has generic malefic pressure, but McIntosh calls out Mars square Pluto when one is suspect/POI ruler, Moon conjunct outer planets, and Mars on the 7th cusp as recurring negative-outcome testimony.

   Candidate implementation: add named, source-backed secondary forensic patterns gated by role relevance. Do not add generic Mars-Pluto penalties without tying one side to perpetrator, victim, Moon, or relevant cusps.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:1409`

4. Exact exaltation/fall degree nuance

   The engine uses dignity broadly, but McIntosh distinguishes victim in exaltation or exact exaltation degree as resilience/alive support and fall as weakness. Suspect dignity is also interpreted differently from victim dignity.

   Candidate implementation: compute exact exaltation/fall-degree proximity for victim ruler, Moon, and perpetrator ruler. Use it as a small survivability/perpetrator-proficiency modifier only after a benchmark comparison.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:261`

5. Traditional direction and distance mapping

   McIntosh gives planet and house direction mappings and discusses converting degrees into miles/distance for mapping. The engine has local-space and abduction-location logic, but not this exact McIntosh planet/house direction table or degree-to-distance mapping.

   Candidate implementation: add an auxiliary `traditional_forensic_direction` payload for abduction/location views. This should not affect axis/survivability/relationship scoring until location benchmarks exist.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:592`

6. Wider fixed-star catalog

   The current fixed-star catalog is curated and smaller than McIntosh's list. Missing or under-modeled candidates include Hyades, Praesaepe, North/South Asellus, Phecda, Serpentis, Unukalhai, and Scheat.

   Candidate implementation: expand fixed-star metadata cautiously as non-score descriptive evidence first, then test score integration only for stars repeated across multiple forensic sources.

   Local source: `docs/ai_agent_mac/forensic_local_text_sources/books/mcintosh_criminal_astrology_understanding_crime_charts.txt:1206`

## Recommendation

The safest next benchmarkable upgrade is not a broad asteroid/special-degree expansion. It is a McIntosh-derived secondary pattern layer:

1. quindecile detection for role-relevant planets only
2. Descendant/7th-house stellium detection
3. named Mars-Pluto, Moon-Pluto, Moon-Saturn, Moon-outer, and Mars-on-Descendant patterns
4. exact exaltation/fall-degree modifiers
5. fixed-star catalog expansion as descriptive evidence before scoring

These should be tested as secondary factors first. Promote only the parts that improve holdout results without harming axis specificity.

## Implemented Follow-Up

Implemented in source on 2026-05-20:

- role-gated quindecile detection
- Descendant / 7th-house stellium detection
- named Mars-Pluto, Moon-outer/malefic, and Mars-on-Descendant patterns
- exact exaltation/fall degree modifiers for victim, Moon, and perpetrator roles
- traditional planet/house direction payload with no scoring effect
- fixed-star catalog additions for Hyades, Praesaepe, North/South Asellus, Phecda, Unukalhai, and Scheat

Benchmark decision:

- 29-case development set: no metric drift.
- 30-case holdout: survivability accuracy improved from 0.6000 to 0.6333; partial survivability improved from 0.6167 to 0.6500; axis and relationship were unchanged.
- Combined 59 cases: survivability accuracy improved from 0.6604 to 0.6792; partial survivability improved from 0.6698 to 0.6887; axis balanced accuracy stayed 0.7551; relationship macro-F1 stayed 0.5681.
- Null-control significance on the combined enabled run remained significant for axis balanced accuracy, axis micro-recall, and relationship macro-F1 with empirical p = 0.0169 under the available 58 label-rotation controls.

Result: scoring integration stayed enabled as secondary survivability testimony because it improved holdout/combined survivability without axis or relationship regression. Traditional directions and expanded fixed-star descriptions remain auxiliary/descriptive unless future location or fixed-star-specific benchmarks justify scoring.

## 2026-05-22 Pages 17-19 Follow-Up: ASC Ruler Placement

User review flagged that the early McIntosh method was only partly represented: the code tracked `houses.first_ruler` and `houses.first_ruler_house`, but it did not expose the house-by-house interpretive layer for where the Ascendant ruler places the victim or missing person.

Source scan:

- Pages 17-19 treat the 1st house/Ascendant as the victim or person in question and ask where the 1st-house ruler is placed.
- The placement is read as a descriptive locator and case-context cue: immediate scene, possession/trafficking/value, communication/vehicle/local movement, family/end-of-matter, party or entertainment setting, disrupted routine/stalker, suspect territory, death/financial entanglement, far travel, public/authority visibility, friends/social circle, or hidden/captive testimony.
- The same pages reinforce that the 1st/7th rulers and Moon remain the main victim/perpetrator relationship checks.

Resolution:

- Added `backend/forensic/knowledge/asc_ruler_house_meanings.yaml` and the packaging source twin under `frontend/backend/forensic/knowledge/`.
- The forensic route now returns `asc_ruler_house_meanings` and a derived `asc_ruler_placement` block with `ruler`, `house`, `label`, `summary`, `cues`, `risk_tone`, `source`, and `scoring_effect: descriptive_only`.
- The derived placement is also copied into `features.asc_ruler_placement` for raw-evidence and downstream UI use.
- The frontend Victim tab now shows the ASC-ruler placement and McIntosh cues in the Victim Location Matrix.

Scoring decision:

- This pass is descriptive only. It does not change findings, survivability, relationship scoring, or abduction bearings. Scoring can be benchmarked later for specific placements such as 4th, 8th, 10th, and 12th, but promoting all twelve meanings directly would be too broad without holdout validation.

Regression coverage:

- `tests/test_forensic_route_contract.py::ForensicRouteContractTests::test_forensic_route_returns_mcintosh_asc_ruler_placement`
- `frontend/src/tests/astroClockModeFlow.test.jsx` test `renders the McIntosh ASC-ruler placement in the victim tab`

## 2026-05-22 Benchmark Follow-Up: H1-H12 Source-Doctrine Axes

The H2 example needed a more precise benchmark target than the generic deception/cover-up axis. Extending the same approach to all houses gives each McIntosh house-placement statement its own source-doctrine validation row.

Resolution:

- Added dedicated H1-H12 source-doctrine context axes, including `trafficking_or_possession_context` for H2.
- Mapped ASC-ruler `risk_tone: material` to `trafficking_or_possession_context` instead of `deception_coverup`.
- Added separate source-doctrine benchmark rows for H1-H12 so the house rules are tested directly without mixing synthetic source examples into the 29-case real replay score.
- Kept the real-case replay score separate from the source-doctrine check.

Current benchmark result:

- Real replay cases: 29 evaluated, 13 supported, 0 contradicted, context-support score 0.4483.
- H1-H12 source-doctrine checks: 12/12 supported, 0 contradicted.
