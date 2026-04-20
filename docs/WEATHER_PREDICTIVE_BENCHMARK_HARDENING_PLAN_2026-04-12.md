# Weather Predictive Benchmark Hardening Plan

Status date: 2026-04-12

## Why This Revision Exists

The first hindcast suite was useful, but it was still too generous.

It could answer:

- does the target event window rank relatively high inside the scanned timeline

It could not answer cleanly:

- does the target event window beat matched nearby non-event windows
- did the model hit the real event timing exactly or only land nearby
- is the apparent pass rate inflated by broad pressure plateaus

## Revision Order

1. Add matched non-event control windows
   - every predictive hindcast case must include explicit nearby windows for the same place and season that did not contain the event
   - the target window should not count as a meaningful success if it fails to beat those controls

2. Separate exact-hit from near-hit behavior
   - keep broad alignment reporting
   - add exact pass rate, near pass rate, and miss rate
   - stop treating broad alignment as if it were exact event timing

3. Widen positive hindcast coverage where the current source corpus allows it
   - do not fake breadth where the local corpus is still thin
   - widen only from explicit local weather examples already curated in the benchmark branch

4. Add a formal prospective benchmark scaffold
   - define the file path, loader, runner, and report shape now
   - keep it unscored until forward cases are intentionally collected

## Acceptance Criteria

The hardened suite is acceptable only if:

- each predictive case has at least one matched control window
- the runner reports alignment, exact, and near outcomes separately
- the headline conclusion is driven by exact behavior, not broad alignment alone
- the repo has an explicit prospective benchmark path, even if it is still scaffold-only

## Current Scope Constraint

The local source corpus still limits positive hindcast expansion.

At the moment:

- `flood_risk` has two explicit local anchors
- `hurricane_pressure` has two explicit local anchors
- `severe_convective_pressure` has two explicit local anchors
- `wind_event_pressure` has three explicit local anchors

That means the hardening pass can widen the wind family immediately, but the other families remain source-limited until more local weather examples are extracted and normalized.
