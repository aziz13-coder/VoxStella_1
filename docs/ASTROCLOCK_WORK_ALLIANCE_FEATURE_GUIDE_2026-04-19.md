# Astro Clock Work Alliance Feature Guide

## Purpose

This note is a feature-facing guide for the live `Work Alliance` synastry engine.

It is grounded in the current source runtime on April 19, 2026 and uses:

- the real-case work benchmark from [backend/synastry_benchmark_runner.py](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_benchmark_runner.py)
- the current public work dataset in [real_public_pairs.json](C:/Users/sabaa/Downloads/codexhorary/backend/benchmarks/synastry/real_public_pairs.json)
- the live structured engine output from [synastry_multi_engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_multi_engine.py)

This is not a reverse-engineering note. It is a practical reading guide for how the feature currently behaves on real public collaboration pairs.

## Benchmark Snapshot

Current work retrieval benchmark on the real-case set:

- `memo_overall_score`: top-1 `0.1000`, top-3 `0.2000`, `MRR 0.3117`
- `work_alliance_theme_total`: top-1 `0.1000`, top-3 `0.4000`, `MRR 0.3400`
- `work_alliance_aspect_total`: top-1 `0.3000`, top-3 `0.6000`, `MRR 0.5350`
- `work_alliance_composite_total`: top-1 `0.2000`, top-3 `0.4000`, `MRR 0.4117`
- `random_expected`: top-1 `0.1867`, top-3 `0.5600`, `MRR 0.4373`

Current outcome-aware work snapshot:

- labeled durable pair count: `1`
- labeled breakdown pair count: `1`
- all current work scalars rank `Buffett/Munger` above `Musk/Altman` on the pair-level durability track

So the current feature is strongest on the shared-contact layer, while the new durability interpretation helps make the business totals easier to read in the modal itself.

## How To Read The Feature

Inside the `Work Alliance` tab, focus on these fields:

- `Theme Base`: business-house foundation after pressure
- `Contact Layer`: cross-aspect traction still active between the two charts
- `Pressure Load`: burden rows dragging against long-run stability
- `Composite total`: the engine-wide app summary
- `Durability Check`: the live app interpretation for staying power versus fracture risk

The durability panel is an app-side interpretation of the business engine totals. It does not replace the source engine lists; it summarizes them into a more direct runtime read.

## Case 1: Warren Buffett / Charlie Munger

### Benchmark Read

Case id:

- `work_buffett_munger_real`

Retrieval rank:

- `memo_overall_score`: rank `4`
- `work_alliance_theme_total`: rank `1`
- `work_alliance_aspect_total`: rank `1`
- `work_alliance_composite_total`: rank `1`

This is the strongest showcase case for the current business engine. The business-specific scalars all put the true partner first.

### Live Work Alliance Output

Summary totals:

- `Theme total`: `36`
- `Aspect total`: `50`
- `Burden total`: `-12`
- `Composite total`: `86`

Durability check:

- score: `83`
- label: `durable signal`
- title: `Durable collaboration signal`

Modal reading:

> The business-house foundation stays net-positive and the pressure layer is not overwhelming, so the pair reads as more able to hold useful cooperation over time.

Top themes:

- `Partnership`: `+19`
- `Status & Direction`: `+14`
- `Service & Friction`: `+8`

Representative contact rows:

- `Moon Conjunction Jupiter`: `+8`
- `Sun Trine Sun`: `+8`
- `Mars Trine Moon`: `+7`
- `Sun Square Jupiter`: `-7`

Representative pressure rows:

- `Snap A: H2 cusp`: `-3`
- `Snap B: H2 cusp`: `-3`
- `Snap B: Saturn`: `-3`

Why this case matters:

- it shows the engine in its most convincing current state
- both the retrieval benchmark and the live feature output tell the same story
- the collaboration reads solid without pretending to be pressure-free

## Case 2: Elon Musk / Sam Altman

### Benchmark Read

Case id:

- `work_musk_altman_real`

Retrieval rank:

- `memo_overall_score`: rank `5`
- `work_alliance_theme_total`: rank `6`
- `work_alliance_aspect_total`: rank `4`
- `work_alliance_composite_total`: rank `6`

This is a benchmark miss on collaborator retrieval, but it is a strong showcase for the new durability reading because the live feature does not read this pair as stable.

### Live Work Alliance Output

Summary totals:

- `Theme total`: `-59`
- `Aspect total`: `-2`
- `Burden total`: `-9`
- `Composite total`: `-61`

Durability check:

- score: `6`
- label: `breakdown-prone`
- title: `Breakdown-prone pattern`

Modal reading:

> Pressure and business-theme drag are overtaking the cooperative layer, so the pair reads as more vulnerable to fracture than to durable alignment.

Top themes:

- `Status & Direction`: `+4`
- `Partnership`: `-3`
- `Identity & Presence`: `-10`

Representative contact rows:

- `Moon Trine Sun`: `+8`
- `Sun Square Venus`: `-7`
- `Sun Square Mercury`: `-7`
- `Mars Square Moon`: `-7`

Representative pressure rows:

- `Snap B: H10 cusp`: `-3`
- `Snap B: Sun`: `-3`
- `Snap B: Jupiter`: `-3`

Why this case matters:

- it shows a pair with real interaction and some visible traction
- the feature still lands on a very low durability read because the business foundation stays net-negative
- this is the clearest example of the new modal-side durability panel doing useful interpretive work

## Case 3: Steve Jobs / Steve Wozniak

### Benchmark Read

Case id:

- `work_jobs_wozniak`

Retrieval rank:

- `memo_overall_score`: rank `5`
- `work_alliance_theme_total`: rank `4`
- `work_alliance_aspect_total`: rank `2`
- `work_alliance_composite_total`: rank `4`

This is the most useful middle case in the current work set. It does not read like a clean enduring-success pair, but it also does not collapse into the same pattern as Musk/Altman.

### Live Work Alliance Output

Summary totals:

- `Theme total`: `14`
- `Aspect total`: `38`
- `Burden total`: `-6`
- `Composite total`: `52`

Durability check:

- score: `64`
- label: `mixed durability`
- title: `Capable, but not naturally stable`

Modal reading:

> The collaboration can function, but the business structure does not read as self-stabilizing. It may work in phases more easily than it holds cleanly.

Top themes:

- `Service & Friction`: `+15`
- `Identity & Presence`: `+8`
- `Status & Direction`: `0`

Representative contact rows:

- `Sun Conjunction Jupiter`: `+8`
- `Jupiter Conjunction Moon`: `+8`
- `Uranus Conjunction Moon`: `-7`
- `Saturn Square Sun`: `-7`

Representative pressure rows:

- `Snap A: Mercury`: `-3`
- `Snap B: Sun`: `-3`

Why this case matters:

- it shows the new feature is not only binary
- the engine can still read a pair as highly productive while stopping short of calling it durable
- this is the best current showcase for the `mixed durability` branch in the modal

## Recommended Demo Order

If you are showing the feature live, the clearest sequence is:

1. `Warren Buffett / Charlie Munger`
   Why: strongest clean success case
2. `Elon Musk / Sam Altman`
   Why: strongest clean rupture-pattern case
3. `Steve Jobs / Steve Wozniak`
   Why: best middle reading between those poles

That order shows the feature range clearly:

- durable
- breakdown-prone
- capable, but not naturally stable

## Commands Used

Benchmark:

```powershell
python backend/synastry_benchmark_runner.py --json
```

The live case snapshots in this note were pulled from the current runtime `Work Alliance` report path, not from a mocked or benchmark-only payload.
