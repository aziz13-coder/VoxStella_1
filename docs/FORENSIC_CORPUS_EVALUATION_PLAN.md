# Forensic Corpus Evaluation Plan

## Objective

Build a small, source-grounded forensic evaluation corpus that can be used to compare the current forensic feature output against labeled real-world case directions before changing forensic rules, feature extraction, or shared Astro Clock chart plumbing.

This is not a horary-style yes/no corpus. The forensic feature is a directional overlay over Astro Clock, so the evaluation needs to judge:

- whether the feature points in the right general direction
- whether it overstates or misses key signals
- whether its emphasis is plausible for the case type
- whether improvements belong in forensic knowledge files or in shared Astro Clock chart-state handling

## Source Set

### Primary local source books

- [Forensics by the Stars Astrology Investigates (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Forensics%20by%20the%20Stars%20Astrology%20Investigates%20(B.%20D.%20Salerno)%20(Z-Library).txt)
- [Exploring Forensic Astrology The Secrets Behind Famous Family Murders (B. D. Salerno) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Exploring%20Forensic%20Astrology%20The%20Secrets%20Behind%20Famous%20Family%20Murders%20(B.%20D.%20Salerno)%20(Z-Library).txt)

### Methodology / taxonomy source

- [Forensic Astrology for Everyone You Dont Need to be an Astrologer to Locate Lost Objects, Find Missing Persons, Solve… (Caroline J. Luley) (Z-Library).txt](C:/Users/sabaa/Downloads/codexhorary/extracted_text_docs/text_forensics/Forensic%20Astrology%20for%20Everyone%20You%20Dont%20Need%20to%20be%20an%20Astrologer%20to%20Locate%20Lost%20Objects,%20Find%20Missing%20Persons,%20Solve%E2%80%A6%20(Caroline%20J.%20Luley)%20(Z-Library).txt)

### Existing repo context

- [FORENSIC_FEATURE_AUDIT_2026-03-22.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_FEATURE_AUDIT_2026-03-22.md)
- [FORENSIC_FEATURE_FIXES_2026-03-22.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_FEATURE_FIXES_2026-03-22.md)

## Why A Forensic Corpus Needs A Different Shape

The current forensic feature does not return a single formal verdict like horary. It returns:

- findings from YAML rules
- category rollups
- planetary dominance
- receptions and relationship-star context
- optional local-space abduction mapping

So the corpus should not ask only, "was it correct?" It needs to evaluate directional fit across a few stable axes.

## Directional Label Axes

Each case should be labeled on one or more of these axes:

- `violence_homicide`
- `abduction_missing_person`
- `deception_coverup`
- `domestic_partner_involvement`
- `family_involvement`
- `child_victim`
- `water_disappearance_or_drowning`
- `accident_or_disaster`
- `friend_or_close_associate`
- `authority_or_public_case`
- `accomplice_or_witness`

These axes are intentionally broader than a full narrative. They match what the forensic feature can reasonably express today through findings, knowledge dictionaries, and dominance cues.

## Corpus Tiers

### Tier 1: Directional seed cases

Use source cases where the case title or nearby source text already gives a strong directional label.

Examples:

- "The Lindbergh Kidnapping"
- "Phil Hartman: Murder by Wife"
- "Scott Peterson: A Talent for Deception"

These are good for early alignment testing even before full chart metadata is captured.

### Tier 2: Replay-ready chart cases

Use cases where the book text provides enough timing/location data to recreate the chart and hit the real backend forensic route.

These become executable comparison cases.

### Tier 3: Manual-review cases

Cases where:

- source direction is clear, but chart data is incomplete
- outcome is disputed
- the feature may be directionally right even if some narrative details differ

These remain human-review only until the metadata is strong enough.

## Comparison Workflow

### Phase 1. Build the source inventory

- inventory local forensic books and known cases
- record source title, source file, and source family
- mark whether the case is event-driven, disappearance, homicide, disaster, or lost-object oriented

### Phase 2. Add starter labels

- assign directional axes
- record label basis:
  - title-only
  - title + nearby source summary
  - stronger narrative support
- assign label confidence:
  - high
  - medium
  - low

### Phase 3. Capture executable metadata

For the first replay slice, capture:

- chart date
- chart time
- chart location
- timezone if explicit or derivable

### Phase 4. Compare against the real feature path

Run cases through:

- [astro_clock_api.py](C:/Users/sabaa/Downloads/codexhorary/backend/astro_clock_api.py) `/api/astro-clock/forensic`

Then compare:

- matched directional axes
- missed axes
- contradicted axes
- category rollups
- notable dominance and abduction-map relevance

### Phase 5. Improve only the correct layer

If a case misses because:

- request context is wrong, fix Astro Clock integration
- chart payload is wrong, fix shared chart projection or feature extraction
- knowledge is weak, fix `backend/forensic/knowledge/*.yaml`
- dominance is distorting the presentation, fix heuristic weighting in [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py)

Do not change shared Astro Clock logic unless the corpus shows the chart context itself is wrong.

### Phase 6. Re-test shared Astro Clock safety

After any forensic change, re-run:

- forensic route contract tests
- forensic feature tests
- Astro Clock API tests
- Astro Clock mode-flow tests

This keeps manual/realtime state, house-system handling, and shared dashboard context stable.

## Starter Implementation In This Pass

This pass should provide:

- a machine-readable starter corpus under `tests/fixtures/`
- a small comparison helper that can score direction alignment
- validation tests for the corpus structure and comparison helper

It does not yet require changing forensic runtime logic.

### Current starter status

- Starter source inventory generated: `3` source records
- Starter labeled case seeds generated: `21` cases
- Current seed books:
  - `Forensics by the Stars`
  - `Exploring Forensic Astrology`
- Current methodology source:
  - `Forensic Astrology for Everyone`
- Current output files:
  - [forensic_case_corpus.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_corpus.json)
  - [extract_forensic_case_corpus.py](C:/Users/sabaa/Downloads/codexhorary/scripts/extract_forensic_case_corpus.py)
  - [forensic_case_corpus_utils.py](C:/Users/sabaa/Downloads/codexhorary/tests/forensic_case_corpus_utils.py)
  - [test_forensic_case_corpus.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_case_corpus.py)

## Evaluation Status Vocabulary

Use these result labels when replay cases are added:

- `aligned`
- `partially_aligned`
- `misaligned`
- `manual_review`
- `not_runnable_yet`

## Immediate Next Order After This Pass

1. Promote 5 to 8 high-confidence book cases into executable replay cases.
2. Run them through the real forensic route.
3. Compare the output against directional labels, not just narrative prose.
4. Fix the smallest responsible layer.
5. Re-run Astro Clock safety tests after every change.

### Suggested first replay slice

- `lindbergh_kidnapping`
- `phil_hartman`
- `scott_peterson`
- `jonbenet_ramsey`
- `susan_smith`
- `natalie_wood`

### Slice 1 current execution status

- Replay fixture implemented:
  - [forensic_case_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_1.json)
- Real route replay helper implemented:
  - [run_forensic_case_replay_slice_1.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_1.py)
- First actual route results captured:
  - [forensic_case_replay_slice_1_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_1_results.json)
- Summary:
  - `6/6` cases returned `200`
  - `6` fully aligned
  - `0` partially aligned
  - `0` misaligned
- This means the forensic feature path is operational on the replay slice and the first grounded directional-rule pass is working.

### Slice 2 current execution status

- Replay fixture implemented:
  - [forensic_case_replay_slice_2.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_2.json)
- Real route replay helper implemented:
  - [run_forensic_case_replay_slice_2.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_2.py)
- Actual route results captured:
  - [forensic_case_replay_slice_2_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_2_results.json)
- Summary:
  - `8/8` cases returned `200`
  - `8` aligned
  - `0` partially aligned
  - `0` misaligned
- The detailed note is in:
  - [FORENSIC_CORPUS_REPLAY_SLICE_2_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_2_RESULTS.md)
- Follow-up direction-layer fix pass completed:
  - [FORENSIC_DIRECTION_RULE_FIXES_2026-03-23.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-23.md)

### Slice 3 current execution status

- Replay fixture implemented:
  - [forensic_case_replay_slice_3.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_3.json)
- Real route replay helper implemented:
  - [run_forensic_case_replay_slice_3.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_3.py)
- Actual route results captured:
  - [forensic_case_replay_slice_3_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_3_results.json)
- Summary:
  - `5/5` cases returned `200`
  - `5` aligned
  - `0` partially aligned
  - `0` misaligned
- The detailed note is in:
  - [FORENSIC_CORPUS_REPLAY_SLICE_3_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_3_RESULTS.md)
- Follow-up direction-layer fix pass completed:
  - [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25.md)

### Slice 4 current execution status

- Replay fixture implemented:
  - [forensic_case_replay_slice_4.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_4.json)
- Real route replay helper implemented:
  - [run_forensic_case_replay_slice_4.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_4.py)
- Actual route results captured:
  - [forensic_case_replay_slice_4_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_4_results.json)
- Summary:
  - `3/3` cases returned `200`
  - `3` aligned
  - `0` partially aligned
  - `0` misaligned
- The detailed note is in:
  - [FORENSIC_CORPUS_REPLAY_SLICE_4_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_4_RESULTS.md)
- Follow-up direction-layer fix pass completed:
  - [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_4.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_4.md)

### Slice 5 current execution status

- Replay fixture implemented:
  - [forensic_case_replay_slice_5.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_5.json)
- Real route replay helper implemented:
  - [run_forensic_case_replay_slice_5.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_5.py)
- Actual route results captured:
  - [forensic_case_replay_slice_5_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_5_results.json)
- Summary:
  - `2/2` cases returned `200`
  - `2` aligned
  - `0` partially aligned
  - `0` misaligned
- The detailed note is in:
  - [FORENSIC_CORPUS_REPLAY_SLICE_5_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_5_RESULTS.md)
- Follow-up direction-layer fix pass completed:
  - [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_5.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_5.md)

### Slice 6 current execution status

- Replay fixture implemented:
  - [forensic_case_replay_slice_6.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_6.json)
- Real route replay helper implemented:
  - [run_forensic_case_replay_slice_6.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_forensic_case_replay_slice_6.py)
- Actual route results captured:
  - [forensic_case_replay_slice_6_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_6_results.json)
- Summary:
  - `1/1` case returned `200`
  - `1/1` aligned
  - `0` partially aligned
  - `0` misaligned
- The detailed note is in:
  - [FORENSIC_CORPUS_REPLAY_SLICE_6_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_CORPUS_REPLAY_SLICE_6_RESULTS.md)
- Follow-up direction-layer fix pass completed:
  - [FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_6.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_DIRECTION_RULE_FIXES_2026-03-25_SLICE_6.md)

### What The Current Baseline Shows

- Slice 1 is aligned.
- Slice 2 is aligned.
- Slice 3 is aligned.
- Slice 4 is aligned.
- Slice 5 is aligned.
- Slice 6 is aligned.
- The feature/rule layer handled the earlier slice-2 gaps without needing shared Astro Clock request-context changes.
- The fresh slice-3 disaster/generalization pass also stayed in the forensic knowledge layer and did not require shared Astro Clock context changes.
- The deferred disaster holdbacks in slice 5 were also solved in the forensic knowledge layer without requiring shared Astro Clock context changes.
- The remaining named family-homicide holdback in slice 6 was also solved in the forensic knowledge layer without requiring shared Astro Clock context changes.

That means the current replay-ready named case set is aligned through slice 6. The next safe move is not another weakly anchored replay slice; it is either low-priority directional-noise cleanup or manual-review work on anonymous / weak-metadata source cases until stronger chart anchors can be recovered.

User-supplied external cases reviewed after that baseline are tracked separately in:

- [FORENSIC_EXTERNAL_CASE_CANDIDATES_2026-03-25.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_EXTERNAL_CASE_CANDIDATES_2026-03-25.md)

Those cases were not promoted into slice 6 because the local-source slice chain remains closed.

Current external status:

- Delphi remains a manual-review external candidate
- Idaho is now promoted into:
  - [FORENSIC_EXTERNAL_REPLAY_SLICE_1.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_EXTERNAL_REPLAY_SLICE_1.md)
  - [FORENSIC_EXTERNAL_REPLAY_SLICE_1_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_EXTERNAL_REPLAY_SLICE_1_RESULTS.md)
- MLK is now promoted into:
  - [FORENSIC_EXTERNAL_REPLAY_SLICE_2.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_EXTERNAL_REPLAY_SLICE_2.md)
  - [FORENSIC_EXTERNAL_REPLAY_SLICE_2_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_EXTERNAL_REPLAY_SLICE_2_RESULTS.md)
- Shinzo Abe is now promoted into:
  - [FORENSIC_EXTERNAL_REPLAY_SLICE_3.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_EXTERNAL_REPLAY_SLICE_3.md)
  - [FORENSIC_EXTERNAL_REPLAY_SLICE_3_RESULTS.md](C:/Users/sabaa/Downloads/codexhorary/docs/FORENSIC_EXTERNAL_REPLAY_SLICE_3_RESULTS.md)
