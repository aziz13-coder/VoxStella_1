# Horary Generic Gate Doctrinal Review

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Related internal docs:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_AUDIT.md`
- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_GENERIC_GATE_REMEDIATION_PLAN.md`

## Scope

This review compares the current generic horary fallback logic in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

against traditional doctrine, with Lilly as the practical baseline and Bonatti/Sahl used to check whether the logic remains too broad or too narrow.

This is a doctrinal review only. No runtime logic changes were made in this pass.

## Sources Consulted

Primary / near-primary:

- William Lilly, *Christian Astrology*, Book II:
  - https://www.astrologiahumana.com/WilliamLilly-ChristianAstrology-BookII.pdf
- William Lilly, *Christian Astrology*, Book I:
  - https://www.astrologiahumana.com/CA-I-copy.pdf

Secondary comparative source:

- Graeme Tobyn, *A review of the astrological tradition concerning the perfection of significators and its denial*:
  - https://www.skyscript.co.uk/tobyn2.html

Secondary source on Sahl / perfection:

- Urania Trust, *Finding Lost Objects* discussion of Sahl's takmil/perfection framework:
  - https://www.uraniatrust.org/academic/finding-lost-objects

## Current Generic Gate, In Plain Terms

The current generic fallback is not the whole horary engine. It is only the branch used when:

- the question is occurrence-focused
- no special doctrine family has already taken over
- no recognized perfection route survives strongly enough to decide the matter

The live fallback logic currently sits in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\horary_engine\engine.py`

It evaluates:

- reception
- Moon next aspect
- Moon void/not void
- benefic support to significators
- quesited condition
- secondary synergy between Moon / reception / benefics

It then returns one of three buckets:

- `affirmative_secondary_balance`
- `mixed_or_inconclusive_secondary_balance`
- `denial_secondary_balance`

## Doctrinal Baseline

### 1. Bonatti / Arabic baseline

The broad medieval doctrine summarized by Tobyn is that perfection normally requires one of three forms:

- direct applying perfection between significators
- translation of light
- collection of light

This is substantially compatible with the current engine's main perfection core.

### 2. Lilly's practical baseline

Lilly gives reception major practical importance, but not as a free-floating replacement for connection in every case.

The recurring pattern in Lilly is:

- applying aspect remains central
- reception can rescue difficult aspects or afflicted contact
- benefics can mitigate damage before perfection
- a malefic connection without reception can destroy the matter
- significators placed in one another's relevant houses can show the matter coming to the querent or the querent going to it

This is richer than a flat "no aspect = no", but it is not equivalent to "strong reception anywhere = yes".

### 3. Sahl-style perfection

The Sahl framework, as summarized in the modern secondary material consulted here, is still perfection-centered:

- applying completion remains the technical criterion for fulfillment
- reception modifies the quality and viability of perfection

This again supports a structured perfection hierarchy, not a generic yes from soft secondary testimony alone.

## Doctrinal Comparison Of The Current Logic

### A. Direct perfection, translation, collection

Status:
Broadly correct.

Why:

- the engine has explicit direct perfection detection
- translation and collection are implemented as timed event routes
- chronology and pre-emption are handled before fallback

Doctrinal assessment:

This is consistent with Lilly and broadly consistent with Bonatti/Sahl-style perfection logic.

### B. Prohibition, refranation, frustration, abscission

Status:
Broadly correct in structure.

Why:

- the engine models these as explicit denial or interruption mechanisms
- chronology is checked instead of treating all malefic contact as equally destructive

Doctrinal assessment:

This is one of the stronger parts of the current engine. It is closer to the tradition than the old modern shortcut of "any bad aspect = no".

### C. Moon next aspect

Status:
Partially correct.

Why:

- traditional doctrine does give the Moon a major witness role
- Lilly explicitly tells the astrologer to judge from the Moon's separation and next application
- the engine correctly promotes Moon next aspect beyond a cosmetic modifier

Where it drifts:

- in the generic fallback, Moon support is scored numerically rather than judged in a fuller hierarchy
- a favorable Moon result can become one of several stackable points even when the chart lacks a more concrete connecting testimony

Doctrinal assessment:

Moon testimony belongs in the judgment at a high level. That is correct. The current implementation is serviceable, but still more algorithmic than doctrinally layered.

### D. Moon not void of course

Status:
Usable, but too mechanical.

Why:

- "Moon not void" does support activity and movement in the matter
- however, it is only a weak testimony, not a route to perfection on its own

Current issue:

- the fallback currently adds a fixed positive point whenever Moon is not void

Doctrinal assessment:

That is not doctrinally false, but it is too flat. In traditional judgment, a non-void Moon is permissive background context, not strong independent proof.

### E. Reception

Status:
Partly correct, but the most doctrinally sensitive area.

What is correct now:

- the engine does not treat reception as meaningless
- it distinguishes degrees of reception strength
- it uses reception alongside Moon and condition rather than in total isolation

What is not fully correct:

- the current generic fallback allows reception to accumulate enough weight toward a generic `YES` even when no true route survives
- this is broader than Bonatti/Sahl-style perfection doctrine
- it is also broader than Lilly's more careful usage, where reception usually matters in the context of application, affliction, mitigation, or rescue

Doctrinal assessment:

Reception without application can show willingness, consent, sympathy, or usability. It does not automatically show consummation of the matter. The present fallback still risks treating strong reception as too close to completion.

### F. Benefic support

Status:
Largely correct in intent, but should remain tightly bounded.

What is good:

- benefic support here is not generic "a benefic exists somewhere"
- it is derived from benefic aspects to the significators
- the code already treats it as secondary and can override it if the quesited is badly damaged

Doctrinal assessment:

This is reasonably Lilly-like. Benefics can mitigate and assist. But they should not by themselves produce a clean generic `YES` where the chart still lacks connection.

### G. Quesited condition

Status:
Correct as condition testimony, but not sufficient as completion testimony.

Why:

- traditional horary absolutely cares whether the quesited is dignified, retrograde, combust, cadent, or otherwise damaged
- that tells us whether the matter is viable, strong, weak, obstructed, or corrupt

Doctrinal assessment:

The engine is right to score this. But a strong quesited condition should mainly raise viability or move a case into `UNCLEAR`, unless some connecting testimony also exists.

### H. Generic secondary-balance `YES`

Status:
Doctrinally the weakest part of the present design.

Why:

- the current code allows `affirmative_secondary_balance` if the stacked secondary testimonies are strong enough
- that means a no-route chart can, in principle, still become a generic `YES`

Doctrinal assessment:

This is the place where the engine most clearly exceeds strict perfection doctrine. It is not entirely alien to Lilly's practice, because Lilly does sometimes judge from rescue, reception, and contextual placement in ways that are richer than a hard binary route test. But as a generic rule, this is too permissive unless a real connecting testimony is present.

## Correctness Verdict

Overall doctrinal verdict:
partially correct, structurally strong, but still too permissive in one specific area.

More precisely:

- The main perfection system is doctrinally sound enough for practical horary work.
- The generic fallback is better than a flat `no perfection = no`.
- The `UNCLEAR` middle bucket is doctrinally defensible and probably necessary.
- The current generic `YES` bucket is not yet doctrinally tight enough.

So the logic is not "wrong everywhere". The issue is concentrated:

- reception, Moon support, benefic support, and workable quesited condition are all real testimonies
- but in the generic fallback they are still too capable of acting as substitutes for completion instead of testimonies about viability, willingness, or tendency

## Fixes Needed

### Fix 1. Require a connecting testimony before generic `YES`

Recommended rule:

`affirmative_secondary_balance` should only be available if at least one real connecting testimony exists.

Examples of acceptable connecting testimony:

- Moon's next aspect gives a decisive positive route into the quesited or a relevant helper
- significator materially approaching the other by relevant placement/hastening logic
- house-placement testimony of the kind Lilly explicitly allows

Without one of these, the generic fallback should be capped at `UNCLEAR`, not `YES`.

### Fix 2. Treat reception alone as viability/consent, not completion

Recommended rule:

- strong reception without connection may raise a chart from `NO` to `UNCLEAR`
- it should not, by itself, create a generic affirmative completion judgment

This is the cleanest doctrinal correction.

### Fix 3. Keep Moon not void as a weak softener only

Recommended rule:

- `Moon not void` should remain supportive
- but it should not count toward major-support thresholds

It is background vitality, not a main perfection replacement.

### Fix 4. Keep benefic support subordinate to connection

Recommended rule:

- benefic support may help rescue or mitigate
- but generic `YES` should still require connection-level testimony, not just benefic atmosphere plus workable significators

### Fix 5. Add doctrine-pinned test cases for this exact issue

The next useful regression set should include:

- no-route charts with strong reception but no connection, expected `UNCLEAR`
- no-route charts with strong Moon carrying the matter, expected `YES` or arguable positive
- no-route charts with weak Moon plus damaged quesited, expected `NO`

## Recommended Next Work Queue

1. Keep the current special doctrine families unchanged.
2. Refine only the generic fallback.
3. Rework `affirmative_secondary_balance` so it requires a connection-level testimony.
4. Keep `mixed_or_inconclusive_secondary_balance` as the main bucket for strong but non-completing testimony.
5. Re-run the full horary replay corpus and frontend parity suites after any change.

## Bottom Line

The current engine is already much closer to traditional horary than a simplistic "aspect or no aspect" system.

Its main doctrinal weakness is not the perfection core. It is the generic fallback's willingness to let stacked soft testimonies become an outright `YES` without a sufficiently traditional bridge between the significators.

The safest doctrinal fix is therefore narrow:

- keep the current no-route `UNCLEAR` machinery
- tighten the conditions for no-route `YES`
- continue to let the main perfection system do the real event work
