# Horary External Source-Pass Slice 16

Date:
2026-03-24

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice16.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice16.py`

## Purpose

This slice moves to another still-unprobed doctrine family: publishing, manuscript acceptance, and gain from publication.

The goal here is to test whether the router can distinguish:

- publication itself as a 9th-house matter
- a book or review as a written work rather than a delivered good
- financial gain from publication as a secondary money question, not the primary publication axis

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `Will i publish my book?`
2. `Will i get a book review published in this online magazine?`
3. `Will I publish my book and have gains from it?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `publish_my_book_source_pass`
  - current router: `general`
  - houses: `[1, 9]`
  - status: publication itself now stays on the 9th instead of a delivery-style goods frame

- `book_review_published_magazine_source_pass`
  - current router: `general`
  - houses: `[1, 9, 2]`
  - status: publication remains primary, with secondary gain or benefit kept on the 2nd

- `publish_book_and_have_gains_source_pass`
  - current router: `money`
  - houses: `[1, 9, 2]`
  - status: publication and profit from publication now keep the 9th and 2nd together

## Interpretation

This slice is now fully aligned after a shared publication doctrine pass.

What changed:

1. publication wording now outranks delivery or goods logic, so books and reviews are no longer treated like shipped objects
2. publication itself is now surfaced as a dedicated 9th-house family
3. publication-plus-profit questions now keep publication primary on the 9th and gain secondary on the 2nd
4. the intent classifier now uses bounded phrase matching, which also fixes the old false `SAFETY` label caused by `book` containing `ok`

## Sources

- [Astrology Weekly: Will i publish my book?](https://astrologyweekly.com/threads/will-i-publish-my-book.32269/)
- [Astrology Weekly: Will i get a book review published in this online magazine?](https://astrologyweekly.com/threads/will-i-get-a-book-review-published-in-this-online-magazine.28313/)
- [Astrology Weekly: Will I publish my book and have gains from it?](https://astrologyweekly.com/threads/will-i-publish-my-book-and-have-gains-from-it.147475/latest)

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice16.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice16_rules.py tests\\test_horary_external_source_pass_slice16.py tests\\test_horary_question_intent_labels.py tests\\test_horary_external_source_pass_slice15.py -q`
  - result: `16 passed`
- `python -m py_compile backend\\question_analyzer.py backend\\horary_engine\\publication_doctrine.py frontend\\backend\\question_analyzer.py frontend\\backend\\horary_engine\\publication_doctrine.py`
  - result: `passed`

Runtime routing changes were made in this pass in the shared publication doctrine layer.
