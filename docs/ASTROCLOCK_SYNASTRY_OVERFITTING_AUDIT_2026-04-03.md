# AstroClock Synastry Overfitting Audit

Date: 2026-04-03

## Purpose

Check whether the latest synastry tuning changes, especially:

1. `compatibility_conflict_gate`
2. `burden_saturn_context_relief`
3. `burden_oppressive_cluster_floor`
4. `attraction_supportive_polarity_floor`
5. `attraction_stress_cluster_floor`

behave like general doctrine or merely fit the first two historical replay couples.

This audit does not claim to prove full generalization. Even with three replay-ready slices, that would still be too strong.

It answers the narrower and more honest question:

1. do the new rules fire only on the historical couples?
2. do they stay selective in a broader seeded corpus?
3. do they behave correctly on synthetic counterexamples designed around doctrine?

## Audit Surface

The audit uses three layers:

1. historical replay slices:
   - [synastry_historical_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_1.json)
   - [synastry_historical_replay_slice_2.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_2.json)
   - [synastry_historical_replay_slice_3.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_historical_replay_slice_3.json)
2. seeded stress corpus:
   - `24` deterministic seeded chart pairs
3. synthetic doctrine archetypes:
   - oppressive cluster
   - serious but workable Saturn bond
   - high friction without hard-Saturn cluster

Implementation:

1. [synastry_overfit_audit_support.py](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_overfit_audit_support.py)
2. [test_synastry_overfit_audit.py](C:/Users/sabaa/Downloads/codexhorary/backend/test_synastry_overfit_audit.py)
3. [run_synastry_overfit_audit.py](C:/Users/sabaa/Downloads/codexhorary/scripts/run_synastry_overfit_audit.py)
4. [synastry_overfit_audit_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/synastry_overfit_audit_results.json)

## Current Findings

### Historical replay slices

Slice 1 remains fully `aligned`:

1. `Paul Newman / Joanne Woodward`
2. `Charles / Diana`

Slice 2 is now active and broadens the real-biography surface:

1. `Frida Kahlo / Diego Rivera`
2. `Sid Vicious / Nancy Spungen`
3. `Elizabeth Taylor / Richard Burton`

Current slice-2 result:

1. `Frida / Diego` remains `partially_aligned`
2. `Sid / Nancy` is now `aligned`
3. `Elizabeth / Burton` is now `aligned`
4. none of the slice-2 cases trigger `burden_oppressive_cluster_floor`
5. `attraction_stress_cluster_floor` appears on `Sid / Nancy`
6. `attraction_supportive_polarity_floor` appears on `Elizabeth / Burton`
7. neither attraction floor fires on `Frida / Diego`

Slice 3 extends the replay surface again:

1. `Frank Sinatra / Ava Gardner`
2. `Jean-Paul Sartre / Simone de Beauvoir`

Current slice-3 result:

1. `Frank / Ava` is `aligned`
2. `Sartre / Beauvoir` is now `aligned`
3. none of the slice-3 cases trigger `burden_oppressive_cluster_floor`
4. neither attraction floor fires on slice 3
5. the attachment floor fires only on `Sartre / Beauvoir`

Interpretation:

1. the burden-floor fix is still not spreading across every difficult real couple
2. the attraction-family audit improved two volatile replay cases without touching the burden floor
3. `Frank / Ava` shows the current attraction logic generalizes to another better-timed high-chemistry unstable marriage
4. the wider replay surface now leaves one live replay miss:
   - `Frida / Diego`: burden plus attraction in a growth-heavy strained bond

### Seeded corpus incidence

Current seeded-corpus result:

1. `burden_oppressive_cluster_floor` fires on `1 / 24` seeded pairs
2. `compatibility_conflict_gate` fires on `6 / 24` seeded pairs
3. `attraction_supportive_polarity_floor` fires on `1 / 24` seeded pairs
4. `attraction_stress_cluster_floor` fires on `0 / 24` seeded pairs
5. `attachment_enduring_binding_cluster_floor` fires on `1 / 24` seeded pairs

Interpretation:

1. the burden floor is selective, not broad
2. the compatibility gate is broader, which is expected because it regulates ease inflation under repeated conflict themes
3. the supportive attraction floor is also selective in the seeded corpus
4. the stress attraction floor does not appear in the seeded corpus, so its generalization needs synthetic and historical checks more than seeded incidence
5. the attachment floor is also selective; the one seeded hit carries the same mutual-reception plus Saturn-binding plus nodal confirmation cluster that the rule is meant to recognize

### Synthetic archetypes

Current doctrine-archetype result:

1. oppressive-cluster archetype:
   - `burden_oppressive_cluster_floor` fires
2. serious-but-workable Saturn archetype:
   - `burden_oppressive_cluster_floor` does not fire
3. high-friction-without-hard-Saturn-cluster archetype:
   - `burden_oppressive_cluster_floor` does not fire
4. supportive-polarity-plus-chemistry archetype:
   - `attraction_supportive_polarity_floor` fires
5. magnetic-stress-cluster archetype:
   - `attraction_stress_cluster_floor` fires

Interpretation:

The current floor rules behave like structured doctrine rules:

1. it requires hard Saturn
2. it requires emotional strain
3. it requires obstructive conflict
4. it does not simply convert any high-friction chart into high burden
5. supportive attraction needs repeated luminary plus Venus-Mars testimony
6. stressed attraction needs luminary strain, chemistry testimony, and already-high friction before it is floored upward

## Conclusion

Within the current audit surface, there is no strong evidence that the latest burden or attraction-floor fixes are narrow patches that only fit the earliest replay couples.

What the audit supports:

1. the rule generalizes to a synthetic oppressive pattern
2. it stays off for nearby counterexamples
3. the new attraction floors generalize to synthetic chemistry patterns
4. the burden and supportive-attraction floors remain rare in the broader seeded corpus
5. the burden floor does not spread automatically across the replay slices, even when real burden scores are high
6. the new attraction logic is not limited to just the two slice-2 volatile couples

What the audit does not support yet:

1. strong claims of historical generalization across relationship types
2. confidence that the rule is correctly calibrated beyond the current replay slices
3. confidence that the attraction families are fully finished, because `Frida / Diego` remains an attraction-and-burden miss
4. confidence that the attachment-family doctrine is fully finished beyond the current replay slices, even though it now handles `Sartre / Beauvoir`

## New Signal From Slices 2 And 3

The broader replay surface changed the question again.

The previous main risk is no longer:

1. `burden_oppressive_cluster_floor` is a Charles/Diana-only patch

The current live risks are:

1. attraction and burden may still be understated in some creative or growth-heavy strained bonds such as `Frida / Diego`

Current replay miss pattern:

1. `Frida / Diego`
   - growth matches
   - burden is too low
   - attraction is too low
2. `Sid / Nancy`
   - friction, burden, and attraction now match
3. `Elizabeth / Burton`
   - attraction, friction, and attachment now match
4. `Frank / Ava`
   - attraction, friction, and burden now match
5. `Sartre / Beauvoir`
   - attachment, growth, and burden now match
   - the attachment floor fires only here, where repeated binding testimony is present

## Next Step

The next real anti-overfitting move is no longer just "add more synthetic checking."

The next best move is:

1. keep the current attraction-family logic as-is unless another volatile replay case breaks it
2. keep the current attachment-family logic as-is unless another unconventional durable bond breaks it
3. keep burden tuning separate until the `Frida / Diego` pattern repeats in another growth-heavy strained case

That is the layer that can tell us whether the remaining misses come from doctrine weighting, burden-family weakness, or timed-data quality limits.
