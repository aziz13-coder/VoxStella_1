Date: 2026-04-16
Scope: Alpha marriage electioner source alignment against Morin, *Astrologia Gallica* Book 26.

# Purpose

This note documents the alpha marriage election changes made after the Book 26 re-audit.

The goal was not to make alpha identical to the new beta path.

The goal was to make alpha track Morin's election rules more closely while keeping the product decision that natal input remains optional.

# Source Baseline

The relevant source used for this pass is:

- `631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.pdf`
- extracted text copy at `extracted_text_docs/631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt`

The key source constraints for marriage elections in this pass are:

1. A marriage election is a lasting matter, so a fixed Ascendant is preferred and a mobile Ascendant is contrary.
2. The Ascendant ruler should not be slow, retrograde, or afflicted by malefics.
3. The Moon should not be afflicted by Mars or Saturn and should not be in the 6th, 8th, or 12th.
4. Certain Moon applications must be avoided:
   - to Mars from Venus signs
   - to Jupiter from Mercury signs
   - to the Sun from Saturn signs
5. The Moon should not apply to or be joined with a retrograde planet.
6. Malefics should be kept out of the angles, especially the Ascendant and Midheaven.
7. Fixed stars matter, especially on angles and significators.
8. For marriage contracts Morin requires natal promise plus favorable directions, revolutions, and transits.

# Product Deviation Kept Intentionally

Morin does not treat natal input as optional.

Alpha now documents this explicitly instead of pretending otherwise.

Current product rule:

- alpha may run without natal input
- when natal is omitted, alpha emits a documented natal-aware warning
- that natal-optional path is still usable, but it is not presented as fully Morin-faithful

Runtime effect:

- alpha now emits a natal-aware caution tag when natal is missing

# Issues Resolved In Code

The following non-source alpha heuristics were removed from the scorer:

- hard-coded preferred and disfavored 7th-sign table
- Taurus-first-half and Leo-specific 7th-sign bonuses
- Moon sign preference table for marriage
- generic Moon waxing bonus
- generic Moon void-of-course penalty in alpha
- generic via-combusta penalty in alpha
- Jupiter dignity package
- Venus dignity and Venus-retrograde deal-breaker package
- L1-L7 perfection and translation or collection scoring
- MC-to-L1/L7 marriage linkage heuristics
- Moon-malefic reception mitigation heuristics

The following Book 26 gaps were added:

- Moon applying to retrograde planet penalty
- Moon-to-Mars from Venus signs penalty
- Moon-to-Jupiter from Mercury signs penalty
- Moon-to-Sun from Saturn signs penalty
- natal and return proxy scoring when natal context is present
- explicit natal-optional fallback warning

# Current Alpha Contract

Alpha is now best described as:

- Morin Book 26 source-backed event core
- natal-aware when natal data is available
- fallback-capable when natal is omitted

What alpha uses directly now:

- fixed versus mobile Ascendant logic for a lasting matter
- Ascendant ruler quality
- 7th-ruler quality as the house of the matter
- benefics and malefics in angles
- Moon safety rules from Book 26
- optional fixed-star checks
- natal promise screen when natal is provided
- return and transit proxies when supplied by the election workflow

# Remaining Approximations

Alpha still contains approximations because the current scan contract does not pass every classical input Morin discusses.

Approximations still present:

- directions are represented through `natal_hits` transit or direction proxy payloads
- solar and lunar revolutions are represented through `sr_windows` and `lr_list`
- Moon "increased in light and number" is approximated through waxing status and Moon speed
- full radical determination logic is still simplified to house and significator checks

These are acceptable for alpha as long as the product continues to allow natal-optional scanning.

# Beta Separation

This change does not relax the alpha/beta split.

- alpha remains the Morin-oriented marriage path
- beta remains the Galaxy-oriented marriage path

No Galaxy-specific marriage rules were moved back into alpha during this pass.
