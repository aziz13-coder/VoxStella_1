# Mundane Knowledge Base Plan

## Goal

Build a source-governed mundane astrology knowledge layer before any scoring model or frontend toggle is implemented.

The astrocartography feature already gives us the delivery architecture:

- modal workspace
- goal registry
- async long-running searches
- runtime assets
- source-alignment testing

What is missing is a mundane doctrine corpus with stable references, summaries, and benchmarkable claims.

## Current Source Set

Primary raw sources currently available in-repo:

- [Horary Astrology and the Judgment of Events (Barbara H. Watters) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/horary_knowledge/Horary%20Astrology%20and%20the%20Judgment%20of%20Events%20(Barbara%20H.%20Watters)%20(Z-Library).txt)
- [Bonatti_on_Mundane_Astrology_Guido_Bonattis_Book_of_Astronomy_Treatise_4_8.1_10_Conjunctions_Revolutions_Weat_fdd3953fa4.txt](C:/Users/sabaa/Downloads/codexhorary/horary_knowledge/mundane_books_text/Bonatti_on_Mundane_Astrology_Guido_Bonattis_Book_of_Astronomy_Treatise_4_8.1_10_Conjunctions_Revolutions_Weat_fdd3953fa4.txt)
- [Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt](C:/Users/sabaa/Downloads/codexhorary/horary_knowledge/mundane_books_text/Mundane_Astrology_The_Astrology_of_Nations_and_States_H._S._Green_Raphael_C.E.O._Carter_z-library.sk_1lib.sk_z-lib.sk.txt)

## Working Rules

- Do not generate scoring weights directly from raw text.
- Normalize books first.
- Distill doctrine into reference docs second.
- Extract compact source claims for validation third.
- Design runtime models only after the reference layer is frozen.

## Build Phases

### Phase 1: Source Freeze and Normalization

Deliverables:

- `horary_knowledge/mundane_books_text/*`
- `horary_knowledge/mundane_knowledge_base/normalized_books/*`
- `horary_knowledge/mundane_knowledge_base/guides/*`
- `horary_knowledge/mundane_knowledge_base/catalog.json`
- `horary_knowledge/mundane_knowledge_base/README.md`

Purpose:

- preserve exact source lineage
- clean extraction noise
- create heading indexes and keyword anchors
- make later citation and synthesis reliable

### Phase 2: Topic Study and Reference Distillation

Target reference docs:

- `01_core_concepts.md`
- `02_chart_types.md`
- `03_significations.md`
- `04_timing_and_triggers.md`
- `05_event_domains.md`
- `06_national_charts_and_locality.md`
- `07_feature_notes.md`
- `08_conflicts_and_open_questions.md`

Study topics:

- mundanity versus personal/horary framing
- chart classes: ingresses, lunations, eclipses, conjunctions, revolutions, weather, war charts
- signification system: people, rulers, government, treasury, enemies, allies, treaties
- timing logic: eclipse activation, ingress effects, conjunction cycles, heavy-planet triggers
- locality: capitals, nations, national charts, event location
- judgment logic: what is descriptive, what is predictive, and what is too weak for product use

### Phase 3: Source Summaries and Merged Doctrine

Per-source outputs:

- Bonatti summary
- Green / Raphael / Carter summary
- Watters summary

Merged output:

- source agreements
- source disagreements
- strong doctrines suitable for product logic
- historical or speculative doctrines that should stay research-only

### Phase 4: Source-Alignment Dataset

Deliverables:

- `backend/benchmarks/mundane/source_alignment_cases.jsonl`
- `backend/mundane_source_alignment.py`
- tests similar to astrocartography source-alignment

Purpose:

- encode compact doctrinal claims
- prevent semantic drift during model generation
- keep the future mundane layer explainable

### Phase 5: Runtime Asset and Model Design

Only after phases 1 through 4 are stable.

Likely model families:

- public mood
- leadership change
- conflict / war pressure
- civil unrest
- diplomacy / treaty climate
- economic stress
- weather extremes

These should live in a new mundane runtime family, not inside the current astrocartography place-goal models.

## Immediate Next Step

Scaffold the mundane knowledge-base builder and generate the first pass of:

- normalized books
- per-book guides
- reference file stubs
- catalog and README

This establishes the source-governed study workspace before any summarization or modeling begins.

## Follow-On Plan

After the baseline corpus and benchmark runner are in place, weak-spot closure is tracked separately in:

- [MUNDANE_WEAK_SPOTS_CURATION_PLAN_2026-04-11.md](C:/Users/sabaa/Downloads/codexhorary/docs/MUNDANE_WEAK_SPOTS_CURATION_PLAN_2026-04-11.md)

After the doctrine and benchmark foundation became stable enough to start product work, the implementation sequence moved to:

- [MUNDANE_IMPLEMENTATION_PLAN_2026-04-11.md](C:/Users/sabaa/Downloads/codexhorary/docs/MUNDANE_IMPLEMENTATION_PLAN_2026-04-11.md)
