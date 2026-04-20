# Horary Source-Pass Metadata Census

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_metadata_census.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_source_pass_metadata_census.py`

Generator:
`C:\Users\sabaa\Downloads\codexhorary\scripts\build_horary_source_pass_metadata_census.py`

## Purpose

This is the first conservative metadata census for the completed horary `source-pass` slices.

Its purpose is to decide which cases can realistically be promoted from:

- routing audit

to:

- judgment replay

without inventing chart inputs.

## Scope

Completed source-pass slices covered:

- slice `2` through slice `18`

Total cases censused:

- `55`

## First-Pass Classification

Promotion-track totals:

- `direct_replay`: `0`
- `image_reconstructable`: `14`
- `doctrine_only`: `41`

Host breakdown:

- `cunning-man.co.uk`: `13`
- `wroskopos.wordpress.com`: `1`
- `astrologyweekly.com`: `32`
- `skyscript.co.uk` and `mail.skyscript.co.uk`: `7`
- `reddit.com`: `2`

## What The Counts Mean

### Direct Replay

No current source-pass case was marked `direct_replay`.

Reason:

- the first census did not find any completed source-pass family with clearly pinned date, time, and location strong enough to justify direct non-speculative recast promotion

### Image-Reconstructable

The `14` image-reconstructable cases are:

- all `13` current Cunning Man source-pass cases from slices `2` to `4`
- the Wroskopos surgery case in slice `15`

Why these were promoted to this track:

- they come from article-style sources rather than fast-moving forum threads
- they have stronger publication context
- this source family already has replay precedent in the external corpus through image-assisted reconstruction

Important limit:

- this does **not** mean they are replay-ready today without review
- it means they are the best next candidates for image-assisted replay promotion

### Doctrine-Only

The remaining `41` cases stay `doctrine_only` in this first census.

Why:

- forum-thread chart attachments are not safely verifiable in the current non-interactive census
- Reddit sources are blocked or removed in the current environment
- forum timestamps do not by themselves prove cast date, time, and location

This is a conservative choice, not a claim that replay will never be possible.

## Best Replay-Promotion Shortlist

Highest-priority next candidates:

1. Cunning Man source-pass slices `2`, `3`, and `4`
2. `operation_go_smoothly_source_pass` from slice `15`

Why these go first:

- they have the strongest image-assisted promotion case in the current census
- they are likely to expand real judgment audit coverage faster than forum-thread cases
- they fit the existing external replay method already used in the corpus

## What Should Stay Routing-Only For Now

Keep these as doctrine audits unless manual chart capture is performed:

- most Astrology Weekly thread cases
- most Skyscript forum cases
- Reddit-derived cases

These still matter. They remain valuable for:

- category testing
- house routing
- turned-house derivation
- doctrine-family assertions

They just should not be promoted into replay on weak evidence.

## Recommended Next Step

The best next practical move is:

1. take the `14` image-reconstructable cases
2. perform a manual image/readability review
3. split them into:
   - replay-promotable now
   - still blocked after image review

That would convert this first census into a true replay shortlist instead of a host-based conservative filter.
