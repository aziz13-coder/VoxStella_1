# Astro Clock Trait Profile Source Lineage Audit

Date: 2026-03-30

## Purpose

Before expanding the trait-profile replay corpus again, this pass compared the current trait feature against the local source corpus.

The goal was to answer a narrower question than replay correctness:

- which parts of the trait feature are directly source-backed by the local Morin and nativity books
- which parts are only source-compatible shorthand
- which parts are still clearly Carter-derived or editorial

## Source Comparison

### What the local source corpus supports strongly

From the local Morin and nativity texts, the strongest support is for:

- house significations
- planetary nature
- general nativity judgment structure
- radical determination logic
- broad domains like life, wealth, siblings, parents, children, illness, marriage, death, religion, profession, friends, and hidden adversity

The cleanest compact Morin baseline remains the house list in:

- `horary_knowledge/desktop_books_text/toaz.info-jean-baptiste-morin-astrologia-gallica-book-22-directions-1994-transl-pr_c198dcbe1e631c7e9f774ec5e70b435c.txt`

Representative passage:

- 1st: life, temperament, health, moral nature, mental qualities
- 7th: marriage, open enemies, lawsuits
- 10th: action, profession, dignity, fame
- 12th: sickness, imprisonment, exile, secret enemies, hardships

That source strongly supports the Morin-facing house and planet enrichment layer already used by the trait feature.

### What the local source corpus does not support strongly

The current trait catalog contains many fine-grained personality and pathology labels such as:

- `quarrelsomeness`
- `philanthropy`
- `invention_discovery`
- `wisdom`
- `insomnia`
- `hydrophobia_rabies`

For those labels, the local source scan showed that the catalog is still overwhelmingly Carter-derived, not primarily Morin-derived.

That is visible directly in the catalog `sources` fields. Examples:

- `backend/traits/catalog/Q/quarrelsomeness.json` -> `Carter: Afflictions to Libra/Venus or Air cause quarrels`
- `backend/traits/catalog/P/philanthropy.json` -> `Carter: Aquarius love of mankind; 11th friends/allies`
- `backend/traits/catalog/I/invention_discovery.json` -> `Carter: Uranus prominence; Mercury-Uranus contact; Aquarius emphasis`
- `backend/traits/catalog/W/wisdom.json` -> `Carter: Sagittarius philosophy; Saturn sobriety and organization`

So the honest lineage is:

- Morin and classical texts strongly support the house/planet framework and judgment structure
- the detailed psychological trait catalog is mostly Carter-derived, with a small amount of later editorial adaptation

### Practical conclusion

The trait profile feature is not a pure Morin feature.

It is more accurately:

- Morin/classical chart framing
- plus a Carter-heavy trait catalog
- plus project editorial summary logic

That distinction matters enough that the UI should expose it instead of implying a single homogeneous source basis.

## Fix Implemented

The trait engine now emits explicit source-lineage metadata per trait in:

- `backend/traits/engine.py`
- `frontend/backend/traits/engine.py`

Each trait now carries:

- `source_lineage`
- `source_lineage_label`

Current lineage classes:

- `morin` -> `Morin-linked`
- `classical` -> `Classical source`
- `carter` -> `Carter-derived`
- `modern` -> `Modern source`
- `editorial` -> `Editorial`
- `provisional` -> `Provisional source`

The frontend now renders the lineage label on trait cards in:

- `frontend/src/features/astroclock/TraitProfileModal.jsx`

This does not change scoring. It changes interpretive honesty.

## Why this is the right next step

Before expanding replay slices again, the feature now tells the user what kind of source basis each trait is actually using.

That makes later replay claims more defensible:

- Morin-facing claims can focus on house/planet/domain structure
- Carter-derived claims can be described more carefully as catalog-derived personality interpretation

## Tests Added

Backend:

- `backend/test_trait_engine_contract.py`

Frontend:

- `frontend/src/tests/traitProfileModal.test.jsx`

These now verify that lineage metadata is emitted and rendered.
