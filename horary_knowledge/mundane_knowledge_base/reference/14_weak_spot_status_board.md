# Weak Spot Status Board

Status date: 2026-04-12

## Current Status

### War split

- Status: split-domain-live, benchmark-expanded
- Datasets:
  - `backend/benchmarks/mundane/war_outbreak_cases.jsonl`
  - `backend/benchmarks/mundane/campaign_escalation_cases.jsonl`
  - `backend/benchmarks/mundane/military_reversal_cases.jsonl`
  - `backend/benchmarks/mundane/war_conflict_cases.jsonl`
- Notes:
  - `war_conflict` now remains as a compatibility umbrella while outbreak, escalation, and reversal become separate runtime lenses
  - outbreak logic is now anchored to first hostilities, aggressor-defender polarity, and immediate martial onset
  - campaign escalation now favors sustained malefic pressure, active polarity, and eclipse or activation stress
  - military reversal now prioritizes retrograde Mars, attrition signatures, and defender-strength testimonies
  - still needs additional non-Western and non-modern campaign cases before escalation or reversal should be treated as broadly mature

### Leadership transitions

- Status: benchmark-expanded, split-domain-live
- Datasets:
  - `backend/benchmarks/mundane/leadership_transition_cases.jsonl`
  - `backend/benchmarks/mundane/government_stability_cases.jsonl`
- Notes:
  - now includes royal death, coronation crisis, regicide, and accession-on-retrograde-Mars cases under the dedicated `leadership_transition` domain
  - parliamentary and constitutional cases have been moved out toward `regime_stability`
  - still lacks cleaner cabinet-fall and election-defeat examples

### Regime stability

- Status: post-phase5-hardened, split-domain-live, supported
- Datasets:
  - `backend/benchmarks/mundane/regime_stability_cases.jsonl`
  - `backend/benchmarks/mundane/government_stability_cases.jsonl`
- Notes:
  - now has a dedicated split-domain pack for parliamentary dissolution, constitutional blockage, French regime collapse in 1940, and the Fourth Republic crisis of 1958
  - runtime logic now distinguishes institutional strain from office-holder transition
  - post-Phase-5 hardening added explicit non-British and non-monarchical institutional crisis cases
  - runtime logic now treats Saturn/Uranus in the eleventh and Neptune in the tenth or eleventh as stronger regime-collapse and parliamentary-crisis signals
  - still remains research-gated and should be widened beyond France and Britain before it is treated as broad

### National-chart proving

- Status: phase4-complete, benchmark-expanded, proving-runner-live
- Datasets:
  - `backend/benchmarks/mundane/national_chart_proving_cases.jsonl`
  - `backend/benchmarks/mundane/national_chart_candidates.jsonl`
- Notes:
  - now includes proving cases for the United States, United Kingdom, German Empire, seeded German regime-chart overlays, seeded France/Burma/India comparisons, and an explicit Israel later-event proving case
  - runtime registry coverage now includes additional source-backed candidates for France, Germany, Israel, India, and Burma with period-aware chart selection
  - a dedicated proving harness now executes chart selection and period matching directly through `backend/run_mundane_national_chart_proving_benchmarks.py`
  - France, Burma, and India still retain seeded proving rows alongside explicit runtime checks; Israel now has an explicit later-event proving row from Watters

### Diplomacy and foreign affairs

- Status: benchmark-expanded, cross-source-seeded
- Dataset:
  - `backend/benchmarks/mundane/diplomacy_foreign_affairs_cases.jsonl`
- Notes:
  - now has settlement, ally-collapse, peace-overture / temporary de-escalation, and treaty-port coercion coverage
  - source alignment now explicitly preserves the seventh / ninth / eleventh house split for foreign-affairs logic
  - a second source family is now present through Annotated Raphael's treaty-failure / diplomatic-blunder doctrine and the 1939 Tientsin blockade case
  - still needs more treaty-failure and alliance-stress cases before it should be treated as broad rather than cross-source seeded

### Alliance stress

- Status: post-phase5-hardened, benchmark-backed, supported
- Dataset:
  - `backend/benchmarks/mundane/alliance_stress_cases.jsonl`
- Notes:
  - the first Phase 5 family is now hardened as a separate research-gated runtime lens instead of being absorbed into broad diplomacy output
  - runtime logic now extends beyond eleventh-house strain into seventh-house treaty weakness, eighth-house ally-resource damage, ninth-house foreign-relations weakness, afflicted Venus treaty logic, and explicit Saturn-in-the-seventh strain
  - the benchmark pack now covers France 1940, Atlantic Alliance strain in 1973-1974, the Sino-Soviet split, and the breakup of the United Arab Republic in 1961
  - the family is now supported and cross-geography seeded, but it still should not be treated as broad until more non-state-bloc and non-union alliance cases exist

### Trade / commerce

- Status: post-phase5-hardened, benchmark-backed, broad
- Dataset:
  - `backend/benchmarks/mundane/trade_and_commerce_cases.jsonl`
- Notes:
  - the second Phase 5 family is now hardened as a separate research-gated runtime lens instead of leaving commercial disputes inside broad finance or diplomacy output
  - runtime logic now includes afflicted Mercury in the second and ninth, Neptune in the ninth, foreign-trade dispute channels, eleventh-house commercial-legislation blockage, and explicit Saturn-in-the-seventh foreign-trade depression
  - the benchmark pack now covers Tientsin 1939, Britain's post-1947 restriction climate, Suez shipping disruption, the 1973-1974 oil embargo, Smoot-Hawley 1930, reciprocal trade liberalization in 1934, GATT 1947, and the Kennedy Round in 1967
  - the family is now broad and no longer concentrated in energy, shipping, or British-only material

### Epidemic wave pressure

- Status: post-phase5-hardened, benchmark-backed, broad
- Dataset:
  - `backend/benchmarks/mundane/epidemic_wave_pressure_cases.jsonl`
- Notes:
  - this Phase 5 family is now hardened as a narrower subfamily under public health rather than a replacement for the broader epidemic-burden lens
  - runtime logic now centers on recurrent sixth-, eighth-, and twelfth-house burden, Saturn-Uranus wave signatures, retrograde Venus onset warnings, lunation or eclipse timing windows, plus Mars-in-the-sixth and Neptune-in-the-twelfth wave burden
  - the benchmark pack now covers the October 1918 mortality peak, the February 1919 British secondary wave, a Watters-based retrograde-Venus onset / return-wave probe, India's COVID-19 second-wave surge in 2021, the 1957-1958 Asian flu, the 1968-1969 Hong Kong flu, the 2009-2010 H1N1 second wave, and the early-2022 Omicron surge
  - the family is now broad, but it remains research-gated and should still be treated as surge, recurrence, and subsiding-pressure research rather than deterministic outbreak prediction

### Retrograde Mars

- Status: benchmark-expanded, source-thin
- Datasets:
  - `backend/benchmarks/mundane/source_alignment_cases.jsonl`
  - `backend/benchmarks/mundane/retrograde_mars_cases.jsonl`
- Notes:
  - doctrine is explicit
  - now has five source-explicit historical leadership cases
  - still needs another corroborating source before runtime promotion

### Trigger-family promotion

- Status: phase3-complete, benchmark-validated
- Datasets:
  - `backend/benchmarks/mundane/source_alignment_cases.jsonl`
  - `backend/benchmarks/mundane/trigger_profile_cases.jsonl`
- Notes:
  - Phase 3 has promoted `eclipse_degree_activation`, `retrograde_mars`, `mutation_and_conjunction_cycles`, and `angularity` into computed trigger profiles
  - shared trigger state is now reused in domain evaluation instead of being re-derived independently in each path
  - mutation / conjunction cycles are now computed as Jupiter-Saturn backdrop context for ingress, national-chart, lunation, and eclipse frameworks, but they remain backdrop-weighted rather than short-term event timers
  - dedicated trigger validation now exists through `backend/run_mundane_trigger_benchmarks.py`

### Public health

- Status: benchmark-expanded, cross-source-seeded
- Dataset:
  - `backend/benchmarks/mundane/public_health_cases.jsonl`
- Notes:
  - now includes the 1918 influenza peak, the British secondary wave of early 1919, the Black Death in England, a Watters-based retrograde-Venus epidemic probe, and plague deaths in India under the Saturn-Uranus conjunction
  - runtime logic now treats public health through the 1st, 6th, 8th, and 12th houses rather than a sixth/eighth-only model
  - strongest support now comes from three local source families: annotated Raphael, Green/Carter, and Watters
  - still remains research-gated and should not be treated as a mature predictive model without more explicit modern epidemic cases

### Civil unrest

- Status: post-phase5-hardened, cross-source-seeded, supported
- Dataset:
  - `backend/benchmarks/mundane/civil_unrest_cases.jsonl`
- Notes:
  - now includes mutation-cycle unrest, the House of Lords crisis of 1909-1911, the 1926 General Strike, and Swadeshi agitation in British India from 1905-1908
  - runtime logic now reads unrest through the 1st / 4th / 10th / 11th axis plus sixth-house workers, unions, wages, and strike pressure instead of generic Mars / Uranus disruption alone
  - benchmark pack now covers street / labor unrest and parliamentary / constitutional unrest together
  - the first non-British case is now present, but the family should still be widened beyond India, Britain, and the United States before any subfamily split

### Finance and economy

- Status: benchmark-expanded, cross-source-seeded
- Dataset:
  - `backend/benchmarks/mundane/finance_economy_cases.jsonl`
- Notes:
  - now includes Watters' long-cycle U.S. depression case, Carter's 1930 financial-crisis year, and post-1947 British heavy-tax / restriction pressure
  - runtime logic now reads treasury, debt, banking, securities, trade, and parliamentary blockage through the 2nd / 8th / 10th / 11th houses
  - finance output now separates credit / treasury strain from generic social hardship more clearly than the earlier thin model
  - still remains research-gated and should not be split into trade / commerce or credit subfamilies until more cases exist

### Weather, earthquakes, fixed-star catastrophe logic

- Status: research-intake-started, runtime-blocked
- Notes:
  - weather and earthquake runtime work remains blocked by source readiness, not by code readiness
  - the local corpus now contains a usable multi-source weather base:
    - Kris Brandt Riske as the modern operational weather source
    - Bonatti as a classical operational weather and natural-phenomena source
    - Watters plus Green / Raphael / Carter as supporting category and signification context
  - weather now has a narrow seeded benchmark-first branch under `backend/benchmarks/weather`, covering floods, hurricanes, thunderstorms / tornadoes, drought, snow / freezing precipitation, temperature extremes, wind, and generalized seasonal temperature, but is still not runtime-ready
  - the current selected first runtime-candidate set is floods, hurricanes, thunderstorms / tornadoes, and wind
  - earthquakes are no longer purely source-blocked because Bonatti contains real doctrine and Watters / Green-Carter contain supporting mentions
  - earthquakes remain benchmark-not-ready because the current local corpus still lacks a strong worked-case inventory and a second clearly operational source family
  - the B.V. Raman multipart archive chain is still present locally but the embedded PDF remains corrupt with the extraction tooling currently available in this environment

## Immediate Next Moves

1. Keep Phase 6 defined but deferred until there is a concrete product need or the weather/earthquake research branch is settled
2. Widen and review the seeded weather benchmark branch from the current local corpus while holding the explicit runtime gate in `docs/WEATHER_RUNTIME_GATE_2026-04-12.md`
3. Keep earthquake work at doctrine-inventory level until its source and case base is widened
4. Resolve the Raman extraction blocker only as a source-widening task, not as a prerequisite for starting weather benchmarks
5. Preserve research-gating on all existing mundane outputs while the natural-phenomena branch is being evaluated
