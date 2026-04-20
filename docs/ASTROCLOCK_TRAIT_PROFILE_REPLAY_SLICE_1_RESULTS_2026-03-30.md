# Astro Clock Trait Profile Replay Slice 1 Results

Date: 2026-03-30

## Purpose

This is the first real-person replay slice for the Astro Clock trait profile feature.

Unlike the existing trait-profile tests, this slice does not stop at engine contracts or frontend rendering. It runs the real `/api/astro-clock/traits/profile` route against public birth data and checks whether expected trait **families** appear in the indicated trait list.

## Claim Boundary

Promoted claim for slice 1:

- family-level presence in the full indicated `traits` list is replay-safe enough to automate for the promoted cases below

Not promoted in slice 1:

- top-summary psychological cleanliness
- `top_traits[0]` correctness
- exact adjective ordering in the summary panels

The current engine can show a usable expected family in the full trait list while still surfacing noisy or obviously non-representative `top_traits` at the top. This slice is intentionally honest about that limitation.

## Method

- route used: `/api/astro-clock/traits/profile`
- mode: `manual`
- house system: `R`
- timezone used in replay requests: `UTC`
- location lookup: deterministic patched geocode in tests
- assertion style:
  - for each case, require a minimum number of expected trait families to appear above a floor score
  - do not assert the headline summary ordering

## Promoted Cases

### Donald Trump

- source birth time used: `1946-06-14 10:54 EDT`
- replay datetime: `1946-06-14T14:54:00+00:00`
- replay location: `Jamaica Hospital Queens, New York`
- promoted expected-family results:
  - `quarrelsomeness` `66.7`
  - `vanity` `48.1`
  - `volatility` `66.7`

Interpretation of promotion:

- the indicated trait list does retain a confrontational, self-regarding, and volatile family for this chart
- the summary layer remains much noisier than that

Sources:

- [Astro-Databank: Trump, Donald](https://www.astro.com/astro-databank/Trump,_Donald)
- [Donald Trump birth certificate analysis](https://starcats.com.au/blogs/astrology/donald-trump-birth-certificate)

### Barack Obama

- source birth time used: `1961-08-04 19:24 HST`
- replay datetime: `1961-08-05T05:24:00+00:00`
- replay location: `Honolulu, Hawaii`
- promoted expected-family results:
  - `leadership_executive` `50.0`
  - `quiet_authority` `36.4`
  - `wisdom` `35.7`

Interpretation of promotion:

- the indicated trait list does retain a leadership-authority-wisdom family
- the current top summary still over-surfaces unrelated gloomy or pathological clusters

Sources:

- [Barack Obama horoscope](https://rashi.my/celebrity-horoscopes/barack-obama-horoscope)
- [Barack Obama Astro-Seek chart](https://www.astro-seek.com/birth-chart/barack-obama-horoscope)

### Oprah Winfrey

- source birth time used: `1954-01-29 04:30 CST`
- replay datetime: `1954-01-29T10:30:00+00:00`
- replay location: `Kosciusko, Mississippi`
- promoted expected-family results:
  - `philanthropy` `66.7`
  - `compassion_universalism` `33.3`
  - `understanding` `73.3`

Interpretation of promotion:

- the indicated list retains a charitable and empathic family strongly enough for replay
- the current summary layer still overweights fixed-Saturn restraint families

Sources:

- [Astro-Databank: Winfrey, Oprah](https://www.astro.com/astro-databank/Winfrey,_Oprah)
- [Astro Charts: Oprah Winfrey](https://astro-charts.com/persons/chart/oprah-winfrey/)

### Diana, Princess of Wales

- source birth time used: `1961-07-01 19:45 BST`
- replay datetime: `1961-07-01T18:45:00+00:00`
- replay location: `Sandringham, England`
- promoted expected-family results:
  - `attractive_appearance` `37.7`
  - `tenderness` `54.5`
  - `compassion_universalism` `33.3`
  - `grace_artistic` `46.7`

Interpretation of promotion:

- the indicated list retains a grace-tenderness-compassion family for this chart
- the top summary is still crowded by fixed-sign reserve and rigidity families

Sources:

- [Astrotheme: Princess Diana](https://www.astrotheme.com/astrology/Princess_Diana)
- [Princess Diana birth chart](https://zvezdochet.guru/en/birth-chart/Princess-Diana)

## Held Back

These cases were explored but not promoted into slice 1:

- Albert Einstein
  - no longer held back because the inventive family is missing
  - after the intellectual/inventive and summary-diversity passes, `invention_discovery` now survives into `top_traits`
  - still held back because the broader headline summary remains only partially psychologically clean
- Steve Jobs
  - no longer held back because the intellectual family is missing
  - after the same passes, `scholarship` now survives into `top_traits`
  - still held back because the headline summary remains led by several broad social/pleasure families before the intellectual families

## Main Finding

The trait engine is now good enough to support a first replay-safe claim at the **family presence** layer.

After the summary-eligibility pass on `2026-03-30`, the headline summary is materially less misleading:

- pathological and anatomy-style traits no longer dominate `top_traits` by default
- symbolic motif entries no longer lead the general profile summary

That improvement is real, but it is still not enough to promote headline-summary correctness as a replay-safe claim.

Current remaining limitation:

- `top_traits` is now cleaner, but still often overweights broad fixed-sign or restraint families for some public figures
- this is why the slice still only promotes **family presence** in the full indicated trait list, not top-summary correctness

Later summary passes on `2026-03-30` materially improved that state:

- specialized/pathology noise is filtered out of the headline summary
- one summary bucket can no longer monopolize the whole headline
- cognition buckets now prefer intellectual families like `invention_discovery` and `scholarship` over looser generic cognition items

Those improvements are real, but the replay claim boundary remains the same until a dedicated summary-cleanliness slice is promoted.

So the honest current state is:

- full indicated family presence: replay-safe enough to automate
- headline trait ranking: improved, but still not psychologically clean enough to promote as a stronger claim

## Automated Coverage Added

- fixture: `tests/fixtures/trait_profile_replay_slice_1.json`
- deterministic replay helpers: `tests/trait_profile_replay_utils.py`
- replay tests: `tests/test_trait_profile_replay_slice_1.py`

## Recommended Next Step

The next trait-profile replay pass should stay focused on summary correctness:

- compare expected trait families against `top_traits`, not just the full `traits` list
- identify whether the ranking issue is mostly:
  - pathological overfiring
  - fixed/Saturn family over-weighting
  - duplicate-family promotion leakage
  - or weak family-level dampening
