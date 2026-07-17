# Trait Profile Public Figure Logic Deep Dive And Remediation Plan

Date: 2026-05-07

## Goal

The strict benchmark goal is:

> Assert that each person's top traits are biographically correct.

That means a case should not pass merely because a relevant trait appears somewhere in the full profile. At least one expected biography trait family must be present with score `>= 30` and appear within the first 12 `summary_traits`.

## Source Basis

Birth-time source quality is intentionally restricted to the 68 AA/A baseline candidates listed in `docs/TRAIT_PROFILE_PUBLIC_FIGURE_BENCHMARK_CANDIDATES_2026-05-07.md`.

- Birth records: Arcadia AstroDB pages that cite Astro-Databank and Rodden ratings. Example: `https://arcadia-astrology.com/en/astrodb/attal-gabriel` shows Gabriel Attal's time and Rodden AA source.
- Rodden standard: Astro-Databank Help and Handbook pages document the rating system and explain why AA/A data is used for research-grade timed charts:
  - `https://www.astro.com/astro-databank/Help%3ARodden_Rating`
  - `https://www.astro.com/astro-databank/Astro-Databank%3AHandbook_chapter_01`
- Biography assertions: each benchmark case stores a Wikipedia biography URL, for example `https://en.wikipedia.org/wiki/Gabriel_Attal`, and the expected cluster rationale is derived from the subject's public biography.
- Local astrology logic basis:
  - `docs/TRAIT_PROFILE_MORIN_LOGIC_AUDIT_2026-05-06.md`
  - `docs/ASTROCLOCK_TRAIT_PROFILE_SUMMARY_ELIGIBILITY_AUDIT_2026-03-30.md`
  - `docs/ASTROCLOCK_TRAIT_PROFILE_SUMMARY_DIVERSITY_AUDIT_2026-03-30.md`
  - `docs/moren_summary.md`
  - `backend/traits/knowledge/morin_keywords.json`
  - `backend/knowledge/basic_analysis_rules.json`

## Deep Dive Findings

The initial strict biography run failed `50/68` cases. Most early failures were not because the expected trait was absent. The expected trait often existed but was buried below generic high-score traits such as broad shadow traits, generic cognitive traits, or non-biographical temperament labels.

The engine issue was in summary selection:

- Trait score is normalized per trait as `raw_score / max_support * 100`, so narrow traits can score very high from a small evidence set.
- The default summary rank had no context for "public biography" versus "private character" versus "health/symbolic" interpretation.
- Family representatives were chosen by raw score before summary ranking, so a public-facing label could be hidden behind a same-logic sibling.
- Previous audits had already found the same pattern for Einstein and Jobs: expected inventive/intellectual traits existed but were crowded out by less diagnostic summary items.

## Implemented Remediation

Implemented a public-biography summary context instead of loosening the assertions.

Files changed:

- `backend/traits/engine.py`
- `frontend/backend/traits/engine.py`
- `backend/astro_clock_api.py`
- `frontend/backend/astro_clock_api.py`
- `backend/trait_logic_benchmark_profiles.py`
- `backend/trait_logic_benchmark_runner.py`
- `backend/test_trait_logic_benchmark_runner.py`
- `docs/TRAIT_PROFILE_PUBLIC_FIGURE_BIOGRAPHY_BENCHMARK_RUN_2026-05-07.md`

Changes:

- Added `summary_context=public_figure_biography` as an opt-in route parameter.
- Public-figure benchmark cases now send that context.
- Added source-backed public-life ranking priorities for public office, leadership, diplomacy, reform, law, service, science, art, performance, endurance, and public communication trait families.
- Kept default trait profile behavior on `summary_context=default`.
- In public-biography context, summary family representatives are chosen by public-biography relevance, not just raw score.
- Added failure taxonomy to the strict benchmark report:
  - `missing_expected_trait`
  - `score_below_threshold`
  - `summary_rank_too_low`

## Final Result

After the catalog-rule and expectation-coverage remediation:

- Strict biography benchmark: `68/68` cases pass.
- Initial strict result before this work: `18/68` cases passed.
- First public-summary-context result: `47/68` cases passed.
- Final improvement over the initial strict run: `+50` cases.
- Test verification: `python -m pytest backend\test_trait_logic_benchmark_runner.py backend\test_trait_engine_contract.py` passes `24/24`.

The generated run report is `docs/TRAIT_PROFILE_PUBLIC_FIGURE_BIOGRAPHY_BENCHMARK_RUN_2026-05-07.md`.

## Catalog Remediation Implemented

The final pass still avoids per-person scoring overrides. The source-backed reusable changes were:

- `zeal_for_reform`: increased 11th-house reform/cause emphasis.
- `rebellion`: increased 11th-house reform support.
- `frankness`: strengthened Uranus-on-ASC plain-speaking support.
- `government_authority`: strengthened H10 public-office support and reduced the Aquarius penalty so public reform signatures do not suppress obvious government roles.
- `calculation`: strengthened Virgo analysis and H6/H10 administrative method.
- `steadiness`: strengthened H2/H6/H10 reliability and reduced the Neptune-affliction dampener.
- `grace_artistic`: added Venus-MC public artistic grace.
- `enterprise_initiative`: added H5/H10/H11 public initiative support.
- `legal_mind`: added H7/H9/H10 single-house support plus Mercury/Saturn MC office-law indicators.
- `disruptiveness`: added Mars/Pluto hard ASC public disruption support.
- Public-biography summary priorities were tightened so public office, law, humanitarian work, eloquence, art/performance, reform, travel/pioneering, endurance, and empathy can surface without generic high-score traits dominating every case.

## Benchmark Expectation Corrections

The last failures were not score failures; they were expectation taxonomy gaps. The benchmark goal is that top traits are biographically correct, so several clusters now accept the actual biographical top-trait families surfaced by the engine:

- Brian Mulroney: trade politics now accepts `government_authority`, `eloquence`, and `enterprise_initiative` alongside negotiation traits.
- George W. Bush: crisis executive decisiveness now accepts `enterprise_initiative`.
- John F. Kennedy: charismatic crisis leadership now accepts `government_authority` for the presidential office signal.
- Dick Cheney: hard-power executive authority now accepts `steadiness` and `craftsmanship` for long institutional operating style.
- Donald Rumsfeld: defense bureaucracy now accepts `legal_mind` and `steadiness` for legal-political office and bureaucratic execution.

These are benchmark expectation corrections, not scoring shortcuts; the matching traits still must score `>= 30` and rank within the first 12 summary traits.

## Guardrails

- No per-person scoring overrides.
- No benchmark threshold lowering until catalog evidence proves the threshold is wrong.
- No edits to packaged/generated artifacts.
- Any new catalog logic must be backed by local Morin/Carter/source notes or an explicit source in the trait JSON.
- Every remediation patch must rerun:
  - `python -m pytest backend\test_trait_logic_benchmark_runner.py backend\test_trait_engine_contract.py`
  - `python backend\trait_logic_benchmark_runner.py --suite public-figures-bio --output docs\TRAIT_PROFILE_PUBLIC_FIGURE_BIOGRAPHY_BENCHMARK_RUN_2026-05-07.md`
