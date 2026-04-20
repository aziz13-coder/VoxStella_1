# Horary Engine Root Fix Plan

## Objective

Fix the logic where the disagreement actually originates, without chart-specific answer flipping and without breaking Astro Clock or other shared consumers.

The current promoted hard-test disagreements pointed to two root faults:

1. reciprocal-affection questions were being judged like simple event questions
2. explicit death questions about another person could keep stale or incorrect houses/significators

## Double-Checked Horary Sources

Primary source used for this implementation pass:

- William Lilly, *Christian Astrology* Book I and Book II:
  - Book I, houses of the 7th, 8th, 9th, 10th:
    - 7th governs "all manner of Love questions" and the person inquired after
    - 8th governs death
    - 9th governs clergy and religious men
    - 10th governs kings, princes, judges and high officers
  - Book I, turned houses:
    - "the House signifying the party shall be his Ascendant or first House"
    - "If a question be made of a King, the tenth is his first house"
  - Book II, marriage/love:
    - marriage promised by conjunction/square/opposition is better with reception
    - mutual reception shows the parties "still love one another"
  - Book II, death:
    - death should not be pronounced rashly on a single testimony
    - lord of the ascendant / Moon must be chiefly afflicted by the lord of the 8th for death judgment

Practical doctrinal takeaways used here:

- Mutual liking is not proved by bare application alone.
- One-way reception may show one-sided inclination, but not reciprocal affection.
- For death of another person, the subject's house becomes the operative ascendant and the subject's 8th becomes the operative death house.
- Death should not be affirmed on a single generic testimony or from the wrong house pair.

## Root-Cause Fix Order

1. Fix category/routing before scoring:
   - explicit death-event language must resolve to `Category.DEATH` before generic health matching
   - titled third-party subjects must map to the correct operative house where possible

2. Fix turned-house death setup:
   - for third-person death questions, use subject house + turned 8th
   - stop letting those charts inherit a stale 1/6 or 1/8 pair from earlier classification

3. Fix reciprocal-affection logic locally:
   - keep relationship event logic intact for reunion/marriage/divorce questions
   - add a narrow affection doctrine layer only for questions about mutual liking / attraction / feelings
   - require mutuality/reception evidence before treating a chart as affirmative

4. Re-verify shared safety:
   - external replay corpus
   - hard-test corpus
   - frontend parity tests
   - no change to Astro Clock API contracts

## Implementation Scope

Source-only edits:

- `backend/question_analyzer.py`
- `backend/horary_engine/relationship_doctrine.py`
- `backend/horary_engine/engine.py`
- replay fixtures/tests/docs

No packaged artifacts, generated site files, or Electron build outputs should be edited.

## Expected Outcomes

- `x_romantically_article_spec` should stop resolving as a bare perfection `YES`
- `pope_die_article_spec` should stop inheriting the wrong operative houses/significators
- fixes remain category-local and doctrine-backed
