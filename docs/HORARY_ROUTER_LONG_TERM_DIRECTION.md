# Horary Router Long-Term Direction

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

## Purpose

This document records the long-term answer to the router question raised during the external source-pass work:

- short-term doctrine passes are useful
- but the current pattern of adding more router/doctrine modules is not the final architecture

The goal here is to preserve the findings and the recommended long-term direction for later implementation.

## Current Finding

The current horary router works, but it scales by accumulating:

1. keyword/category matching
2. doctrine-family overrides
3. house/significator corrections

That approach has been good enough to uncover and fix many real gaps. It is why the source-pass slices were valuable.

But it also creates a structural problem:

- the analyzer is still too dependent on local phrase triggers
- routing correctness can depend on precedence order
- correct category does not guarantee correct houses
- correct houses do not guarantee correct turned subject
- substring collisions can still create false positives unless they are explicitly fenced

In other words:

- the short-term doctrine passes are valid
- but they are not the final scalable solution by themselves

## What The Slice Work Has Revealed

Across the source-pass corpus, the recurring failure modes were:

1. **Substring false positives**
   - Example: `passport` drifting into `education` because of `pass`

2. **Correct broad category, wrong operative houses**
   - Example: litigation or travel recognized, but wrong counterparty or authority axis

3. **Correct family, wrong turned-house subject**
   - Example: spouse/relative immigration or custody questions not turned from the operative person

4. **Person vs possession confusion**
   - Example: roommate or relative treated like a lost object

5. **Missing secondary axis**
   - Example: cohabitation questions reduced to `1/7` without the `4th`

6. **One doctrine family hijacking another**
   - Example: communication, education, property, or lost-object logic firing before the more specific doctrine

These are not random bugs. They point to the same architectural weakness:

- the engine needs a stronger semantic intermediate layer between question text and final doctrine selection

## Long-Term Recommendation

The best long-term fix is a **hybrid semantic router**, not a pure keyword router and not a pure LLM router.

### Core idea

Add an intermediate structured representation of the question before final doctrine selection.

Proposed concept:

- `QuestionFrame`

This frame should capture the real shape of the question, for example:

- `intent`
- `subject_role`
- `subject_house`
- `counterparty_role`
- `counterparty_house`
- `object_role`
- `object_house`
- `authority_role`
- `authority_house`
- `context_tags`
- `turned_from`
- `confidence`
- `trace`

Then doctrine modules consume that frame and produce:

- category
- relevant houses
- quesited house
- doctrine family
- reasoning trace

## Why This Is Better

It moves the system from:

- “which keywords matched first?”

to:

- “what is this question structurally about?”

That matters because horary routing is not just topical classification.

It is usually a combination of:

1. who the operative subject really is
2. whether the matter is event, quality, or safety
3. whether a turned-house derivation is required
4. whether the question is really about:
   - a person
   - an agreement
   - a possession
   - a document
   - an authority
   - a home
   - a child
   - a court
   - some combination of those

The current code often solves that correctly, but it does so by chaining many local doctrine checks.

The long-term fix is to make that structural step explicit.

## Should An LLM Be Used?

Yes, but only in a limited and safe role.

### What an LLM is good for here

1. extracting semantic roles from the question
2. proposing candidate doctrine frames
3. disambiguating difficult language
4. helping label or expand the training corpus offline

### What an LLM should not do here

1. directly choose final houses without deterministic validation
2. directly choose final judgment logic in production
3. replace doctrinal traceability
4. become the only source of routing truth

For horary, auditability matters too much.

The engine should still be able to say:

- why `1/7/4` was chosen
- why `turned 9th` was used
- why a chart was treated as custody, immigration, or cohabitation

That is much harder to guarantee with a fully generative router.

## Best Practical Long-Term Shape

The best practical design is:

1. **Deterministic doctrine engine remains primary**
2. **Structured semantic frame sits in front of it**
3. **Optional model-assisted candidate generation sits behind that**
4. **A deterministic validator/ranker chooses the final frame**
5. **Low-confidence cases can surface as uncertain routing instead of bluffing**

This preserves:

- reproducibility
- doctrinal control
- regression testing
- cost control
- explainability

## Recommended Implementation Path

### Phase 1: Introduce a Question Frame

Create a structured question-frame layer in the backend.

Suggested artifact:

- `backend/horary_engine/question_frame.py`

This should not change judgment yet.
It should only let the analyzer produce a structured semantic description of the question.

### Phase 2: Convert doctrine modules into candidate producers

Instead of directly mutating category/houses by precedence, doctrine modules should return:

- candidate family
- candidate houses
- candidate quesited house
- candidate confidence
- rationale

### Phase 3: Add deterministic conflict resolution

Build an explicit router resolver that:

1. collects doctrine candidates
2. ranks them
3. resolves conflicts with stable rules
4. emits the final frame and routing result

This replaces the current increasingly long override chain in:

- `C:\Users\sabaa\Downloads\codexhorary\backend\question_analyzer.py`

### Phase 4: Use the source-pass corpus as the labeled routing dataset

The source-pass work already produced the beginnings of a routing corpus.

That corpus should become the supervised benchmark for:

- subject-role extraction
- turned-house detection
- doctrine-family prediction
- house-frame validation

### Phase 5: Optional model-assisted candidate generation

Only after the deterministic frame/resolver exists should a model be tested.

Best first use:

- generate candidate `QuestionFrame` values
- not final routing truth

That keeps the model in a safe advisory role.

## What Not To Do

Avoid these long-term directions:

1. do not replace the router with a chat LLM prompt
2. do not let a model directly output final houses with no validation
3. do not continue indefinitely with only more local keyword patches
4. do not treat the current doctrine-pass pattern as the final scalable architecture

## Success Criteria

The long-term router should be considered successful when:

1. new doctrine families require less precedence surgery in `question_analyzer.py`
2. person vs possession errors become rare
3. turned-house errors are caught at the frame layer
4. substring false positives largely disappear
5. source-pass slices increasingly fail only on genuine doctrine ambiguity, not on text-shape mistakes
6. low-confidence routing can be surfaced explicitly instead of being silently forced

## Bottom Line

The short-term doctrine passes were the right move.

They gave the project:

- a large routing audit corpus
- many real doctrine fixes
- a clearer map of failure patterns

But the long-term fix is not “keep adding patches forever,” and it is not “replace the router with an LLM.”

The best long-term direction is:

- a **hybrid semantic router**
- with a structured intermediate `QuestionFrame`
- deterministic doctrine validation
- and optional model assistance only as a candidate generator or disambiguation helper

That is the direction most likely to scale without losing horary traceability.
