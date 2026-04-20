# Astro Clock Trait Profile Career Comparison

Date: 2026-03-30
Scope: fact-backed known-chart comparison for a future blog post about Astro Clock's personality + career output

## Goal

Before drafting a marketing/guide post, compare:

- the real public vocation of several known charts
- the actual output of the current engine
- what is promotable for blog use versus what should be held back

This pass uses the real `/api/astro-clock/traits/profile` route plus the same frontend profession mapper the user sees in the trait-profile modal.

## Important implementation note

During this comparison, one real frontend bug was found and fixed in:

- [frontend/src/features/astroclock/knowledgeMap.mjs](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/knowledgeMap.mjs)

The bug:

- the career mapper was parsing the first house marker in the H10 route line instead of the actual ruler-route house
- that silently weakened route-based profession hints such as:
  - H11 -> politics / associations
  - H7 -> legal practice / public advocacy
  - H2 -> treasury / accountancy
  - H5 -> performing arts / youth education

The current results below use the corrected mapper.

## Method

Birth data source:

- existing replay fixtures in [tests/fixtures/trait_profile_replay_slice_1.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/trait_profile_replay_slice_1.json)
- existing exploratory replay fixture in [tests/fixtures/trait_profile_replay_slice_2.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/trait_profile_replay_slice_2.json)

Engine path:

- backend route: `/api/astro-clock/traits/profile`
- frontend career mapping: `buildProfessionSuggestions(...)` in [frontend/src/features/astroclock/knowledgeMap.mjs](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/knowledgeMap.mjs)

What was compared:

- real-world public vocation
- H10 route and synthesis
- top profession suggestions after frontend mapping
- summary-trait tone where relevant

## Results

### Donald Trump

Real-world role:

- real-estate developer
- television personality
- U.S. president

Career source:

- [Britannica: Donald Trump](https://www.britannica.com/biography/Donald-Trump)

Birth-data source:

- [Astro-Databank: Donald Trump](https://www.astro.com/astro-databank/Trump,_Donald)

Engine output:

- H10 sign: `Taurus`
- H10 route: ruler of 10 in H11
- synthesis includes:
  - `Friends/patrons elevate career and reputation`
- top profession labels:
  - `senior administrator`
  - `command`
  - `leadership`
  - `management`
  - `public office`
  - `political organizer`
  - `association director`

Assessment:

- strong alignment

Why:

- the engine clearly surfaces executive/public-office language
- after the route-parser fix, the H11 politics/network layer is now visible instead of being lost

Blog suitability:

- promotable

### Barack Obama

Real-world role:

- writer/editor
- community organizer
- constitutional law lecturer
- civil-rights attorney
- U.S. senator
- U.S. president

Career source:

- [Britannica: Barack Obama](https://www.britannica.com/biography/Barack-Obama)
- [Britannica: What did Barack Obama do for a living?](https://www.britannica.com/question/What-did-Barack-Obama-do-for-a-living)

Birth-data source:

- [Astro-Seek: Barack Obama birth chart](https://www.astro-seek.com/birth-chart/barack-obama-horoscope)

Engine output:

- H10 sign: `Scorpio`
- H10 route: ruler of 10 in H7
- synthesis includes:
  - `Career via partnership; public marriage`
- top profession labels:
  - `military officer`
  - `competition`
  - `military`
  - `security/police`
  - `surgery`
  - `legal practice`

Assessment:

- weak alignment

Why:

- the corrected mapper now at least preserves the H7 legal/public-advocacy thread
- but Mars/Scorpio still dominate the list too heavily, so the public-law/political career is underrepresented

Blog suitability:

- held back

### Oprah Winfrey

Real-world role:

- television host
- producer
- media executive
- entrepreneur
- philanthropist

Career source:

- [Britannica: Oprah Winfrey](https://www.britannica.com/biography/Oprah-Winfrey)

Birth-data source:

- [Astro-Databank: Oprah Winfrey](https://www.astro.com/astro-databank/Winfrey,_Oprah)

Engine output:

- H10 sign: `Libra`
- H10 route: ruler of 10 in H2
- synthesis includes:
  - `Career drives income; earnings through honors/reputation`
- top profession labels:
  - `arts`
  - `design`
  - `diplomacy`
  - `luxury/fashion`
  - `music`
  - `treasury/accountancy`

Assessment:

- partial alignment

Why:

- the Venus/Libra emphasis does capture public grace, aesthetics, and media polish indirectly
- the H2 route now correctly exposes income/enterprise logic
- but television/media/publishing are not prominent enough yet

Blog suitability:

- usable as a softer partial-alignment case

### Diana, Princess of Wales

Real-world public role:

- royal public figure
- charity/public humanitarian presence
- global celebrity

Career source:

- [Britannica: Diana, princess of Wales](https://www.britannica.com/biography/Diana-princess-of-Wales)

Birth-data source:

- [Astrotheme: Princess Diana](https://www.astrotheme.com/astrology/Princess_Diana)

Engine output:

- H10 sign: `Libra`
- H10 route: ruler of 10 in H5
- synthesis includes:
  - `Fame via creative pursuits; children visible in public`
- top profession labels:
  - `arts`
  - `design`
  - `diplomacy`
  - `luxury/fashion`
  - `performing arts`

Assessment:

- partial alignment

Why:

- diplomacy, aesthetics, and public grace fit the visible public role reasonably well
- the model does not capture humanitarian/charitable emphasis strongly enough in the profession summary

Blog suitability:

- usable only as a partial-alignment case

### Albert Einstein

Real-world role:

- theoretical physicist
- academic
- public intellectual

Career source:

- [Britannica: Albert Einstein](https://www.britannica.com/biography/Albert-Einstein)

Birth-data source:

- exploratory replay slice held-back note in [docs/ASTROCLOCK_TRAIT_PROFILE_REPLAY_SLICE_2_RESULTS_2026-03-30.md](C:/Users/sabaa/Downloads/codexhorary/docs/ASTROCLOCK_TRAIT_PROFILE_REPLAY_SLICE_2_RESULTS_2026-03-30.md)

Engine output:

- H10 sign: `Aquarius`
- H10 route: ruler of 10 in H11
- synthesis includes:
  - `Friends/patrons elevate career and reputation`
- top profession labels:
  - `professor`
  - `academia`
  - `judge/magistrate`
  - `law`
- summary traits include:
  - `invention_discovery`

Assessment:

- partial-to-strong alignment

Why:

- `professor` and `academia` are strong hits
- scientific specificity lives more in the trait summary than in the profession map
- the profession map still overproduces Jupiter/legal language around the same H10 pattern

Blog suitability:

- promotable with careful wording

### Steve Jobs

Real-world role:

- entrepreneur
- Apple cofounder
- technology executive
- product visionary

Career source:

- [Britannica: Steve Jobs](https://www.britannica.com/biography/Steve-Jobs)

Birth-data source:

- exploratory replay slice held-back note in [docs/ASTROCLOCK_TRAIT_PROFILE_REPLAY_SLICE_2_RESULTS_2026-03-30.md](C:/Users/sabaa/Downloads/codexhorary/docs/ASTROCLOCK_TRAIT_PROFILE_REPLAY_SLICE_2_RESULTS_2026-03-30.md)

Engine output:

- H10 sign: `Gemini`
- H10 route: ruler of 10 in H5
- top profession labels:
  - `judge/magistrate`
  - `professor`
  - `academia`
  - `law`
  - `performing arts`
- summary traits include:
  - `scholarship`
  - `invention_discovery`
  - `genius_inventive_scientific`

Assessment:

- weak alignment on profession map
- partial alignment on trait-summary cognition layer

Why:

- the profession map still fails to express entrepreneurship / technology clearly enough
- the trait engine is stronger here than the vocation layer

Blog suitability:

- held back for the vocation/career angle

## Promotable cases for the blog

Best current examples:

- Donald Trump
- Albert Einstein
- Oprah Winfrey as a partial-fit example

Usable with caution:

- Diana, Princess of Wales

Held back:

- Barack Obama
- Steve Jobs

## Honest claim boundary

The current trait-profile + profession workflow can be marketed honestly as:

- a tool that surfaces personality themes and vocation patterns from the natal chart
- sometimes strongly, sometimes partially
- with clearer strength on public-office, academic, and Venusian-public-image cases than on modern media/politics/technology translation

It should not yet be marketed as:

- a precise job-title predictor
- or a universally accurate vocation classifier

## Recommended blog use

If the blog post is meant to be strong and defensible, use:

- Trump for public-office / executive visibility
- Einstein for academic/intellectual vocation
- Oprah as a softer public-image / enterprise case

And avoid building the post around:

- Obama
- Jobs

until the career mapper gets a dedicated legal/political/media/technology refinement pass.
