# Horary Generic Gate Audit

Date:
2026-03-22

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

## Scope

This audit answers four practical questions about the current generic horary engine path:

1. How does the generic verdict gate actually work?
2. Is the engine only deciding by direct perfection?
3. Which traditional horary mechanisms are implemented beyond direct perfection?
4. Does the current generic process adhere to traditional horary method, or does it still compress too much into a generic `no perfection = no` outcome?

This is a source audit only. No runtime logic changes were made in this pass.

## Executive Summary

The current generic horary gate is not a simple direct-aspect engine. It does implement a broader perfection model:

- direct perfection
- translation of light
- collection of light
- prohibition
- refranation
- frustration
- abscission
- some house-placement style perfection

The active path uses the unified perfection core first, then applies a procedural judgment layer in the main engine.

However, the generic gate is still strongly perfection-first. For ordinary occurrence questions, when no recognized perfection route survives, the engine usually falls into a generic denial branch and returns `NO`, with Moon, reception, benefic help, and dignities often treated as secondary modifiers rather than co-equal decision factors.

So the current process is:

- broader than direct perfection only
- partly traditional in structure
- still not fully faithful to a richer Lilly-style judgment hierarchy

## Active Generic Pipeline

### 1. The active engine is the new perfection-core path

The runtime engine is explicitly configured to use the new perfection system:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):18
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):22

`ENABLE_FULL_PHASE = True` means the new perfection core is not shadow-only. It is the active judgment path.

### 2. Question judgment enters `_apply_enhanced_judgment(...)`

The generic judgment process starts in:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):2151

That function:

- computes considerations, Moon testimony, prohibitions, solar impediments, and category-specific branches
- calls the perfection core
- interprets the returned perfection route
- falls back to generic condition/secondary-testimony logic when no route perfects

### 3. The perfection core builds the event timeline

The unified perfection API lives in:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):1384

The detector gathers:

- direct events
- house placement
- translation
- collection
- prohibition
- denial events

Relevant source points:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):281
- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):295
- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):302

### 4. Primary perfection is selected by chronology

Primary selection happens in:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):1321

The chooser rule is:

- if an earlier prohibition truly pre-empts a positive route, choose prohibition
- else choose the earliest positive route
- else choose the earliest denial route
- else choose the earliest event overall

This is a real chronology gate, not just a weight sum.

## What Counts As “Perfection” In The Current Engine

The engine does not only mean “direct aspect between significators.”

### Direct perfection

Direct aspect checking is in:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):316

It evaluates all five major geometries and keeps the earliest valid one within the window.

### Translation of light

Translation is implemented in:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):376

The engine imposes real conditions:

- separation from one significator and application to the other
- translator faster than both significators
- recency bound on the separating leg
- next application must be the intended receiver
- abscission guard

So translation is not a loose symbolic check. It is treated as a timed route.

### Collection of light

Collection is implemented in:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):576

The collector must be slower, both significators must apply to it, and abscission is checked before completion.

### Prohibition

Prohibition is implemented in:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):826

and also as an explicit chronology gate in the main engine:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):2470
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):7699

The important point is that prohibition is not treated as “any bad aspect exists.” It is treated as pre-emption relative to the earliest perfection timing.

### Refranation

Refranation is implemented in:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):864
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):2719

If a significator stations before the direct contact perfects, the engine can return an explicit refranation denial.

### Frustration

Frustration is implemented in:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):938
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):2738

The logic checks whether the applier perfects with another planet before reaching the intended receiver.

### Abscission

Abscission is implemented in:

- [perfection_core.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/perfection_core.py):906
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):511

The engine uses `abscission`, not `abduction`.

Important clarification:

- I do not find a distinct horary mechanism called `abduction` in the code.
- I do find `abscission`, which is the cutting-off/interception logic the engine already models.

If by “abduction” you meant a separate traditional doctrine term, it is not implemented under that name in the generic core.

## What Else The Generic Gate Uses Besides Perfection

### Moon next aspect

The engine checks the Moon’s next aspect to significators in:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):7143

This can support or deny, but when a true perfection already exists it is usually demoted to supportive testimony rather than becoming the main route.

### Moon testimony more broadly

Enhanced Moon testimony is handled in:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):4771
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):7917

This includes:

- void of course
- Moon’s applications/separations
- Moon speed
- Moon-to-benefic support

### Void of course

The engine has a dedicated “ground truth” VOC path in:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):5265

It is not treated everywhere as an absolute blocker anymore. In the newer logic it is more often a caution or penalty.

### Reception, dignity, retrogradation, benefic/malefic support

These are used in the judgment path, but mostly as modifiers or secondary testimony once the perfection route question has already been handled.

Key areas:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):2463
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):3696
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):3888

## How The Generic `No Perfection` Gate Actually Works

This is the most important practical behavior.

### If a recognized perfection route exists

When `perfection["perfects"]` is true, the engine enters the positive/negative perfection handling branch in:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):3088

It then adjusts confidence with:

- Moon next aspect
- receptions
- dignities
- retrograde penalties
- aspect quality
- special category doctrine

### If no perfection route exists

The generic fallback starts around:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):3696

This branch:

- checks enhanced denial conditions
- checks theft/loss-specific denials
- notes benefic support
- may allow category-specific sufficiency branches
- otherwise enters a generic no-perfection denial path

The ordinary occurrence-style fallback is explicit:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):3840
- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):4006

That final generic branch returns:

- `result: "NO"`
- `traditional_factors.perfection_type: "none"`

with secondary supports only softening confidence, not usually reversing the verdict.

## Is The Generic Gate Driven By The Rule Ledger?

Not primarily.

There is a scoring/evaluation layer:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):238
- [aggregator.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/aggregator.py)
- [polarity_weights.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/polarity_weights.py)
- [rule_engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/rule_engine.py)

But in the current architecture:

- the main verdict is still produced procedurally inside `_apply_enhanced_judgment(...)`
- `_evaluate_enhanced(...)` is used later for score/confidence interpretation and trace shaping
- the ledger is not the primary judge of the generic yes/no verdict

So the live gate is not a unified testimony-ledger engine. It is a procedural engine with a scoring layer attached.

## Traditional Adherence: Where It Is Good

The current generic path does respect several traditional principles better than a simplistic engine would.

### 1. Chronology matters

The perfection core does not just ask whether patterns exist. It asks which route perfects first.

This is traditional and important.

### 2. Translation and collection are real routes

These are not decorative labels. They are implemented as timed and sequenced routes.

### 3. Prohibition is treated as pre-emption

That is much closer to traditional logic than a flat “malefic afflicts therefore no.”

### 4. Refranation, frustration, and abscission are explicit

The engine does not lump every failed matter into one generic failure word.

### 5. Moon VOC is no longer always absolute

That is a healthier modern correction inside a traditional framework, because context matters.

## Traditional Adherence: Where It Is Still Weak

### 1. The generic branch is still too perfection-dominant

For ordinary occurrence questions, once the engine fails to find a recognized perfection route, it usually falls into a generic `NO`.

This means:

- receptions
- dignities
- Moon support
- benefic testimony
- condition of the quesited

are often treated as secondary confidence modifiers rather than truly co-decisive testimonies.

### 2. The generic branch compresses too much into `perfection_type = none`

The fallback at:

- [engine.py](C:/Users/sabaa/Downloads/codexhorary/backend/horary_engine/engine.py):4008

still functions like:

- no recognized route
- supportive signals noted
- final generic denial

That is cleaner technically than the old engine, but it is still thinner than full traditional judgment.

### 3. The active architecture is partly duplicated

There is a new perfection core, but `engine.py` still contains:

- legacy perfection helpers
- older Moon testimony paths
- special-case sufficiency branches
- procedural override layers

That makes the active judgment process harder to audit and easier to distort over time.

### 4. The rule/weight system is not the true generic gate

The polarity/weight machinery exists, but it is not the primary decider of the ordinary generic verdict.

So the engine is not yet a clean “traditional testimony hierarchy engine.” It is still a layered hybrid.

### 5. Some traditional mechanisms are still absent as first-class categories

The code clearly models:

- direct
- translation
- collection
- prohibition
- refranation
- frustration
- abscission

But it does not present a broader systematic handling for all traditional edge conditions as first-class generic gate logic. Some are still implicit, duplicated, or category-local.

## Bottom-Line Judgment

The generic horary gate is not simply:

- “no direct perfection = no”

But it is still effectively:

- “no recognized perfection route = usually no, unless a category-specific doctrine branch intercepts first”

That is the key distinction.

So the current engine:

- does use more than direct perfection
- does include several real traditional mechanisms
- does not yet fully conduct generic horary judgment in a balanced Lilly-style hierarchy

Its center of gravity remains:

- perfection first
- denial if no route
- secondary testimonies after that

## What To Audit Next

The safest next step is not a blind logic rewrite. It is a focused generic-gate refinement audit.

Recommended order:

1. Map the exact verdict hierarchy for ordinary occurrence questions:
   - direct
   - translation
   - collection
   - prohibition
   - refranation
   - frustration
   - abscission
   - no-perfection fallback
2. Define which non-route testimonies should be truly verdict-level in generic charts:
   - Moon application
   - strong reception
   - strong dignity asymmetry
   - strong condition of quesited
3. Reduce duplicate procedural branches in `engine.py` so one auditable gate remains
4. Add deterministic corpus tests specifically for:
   - no direct perfection but strong Moon/reception support
   - translation valid vs invalid sequence
   - prohibition pre-emption vs post-perfection corruption
   - frustration and abscission chronology
5. Only then adjust the generic no-perfection gate itself

## Practical Conclusion

If the question is:

“Does the engine adhere to horary rules and process?”

The honest answer is:

- partly yes in structure
- not yet fully yes in generic judgment philosophy

If the question is:

“Does it answer only by direct perfection?”

The answer is:

- no

If the question is:

“Does it still deny too many generic charts when no recognized perfection route exists?”

The answer is:

- yes
