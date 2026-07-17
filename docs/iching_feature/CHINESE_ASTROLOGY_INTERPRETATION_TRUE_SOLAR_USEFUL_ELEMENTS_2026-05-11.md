# Chinese Astrology Interpretation, True Solar Time, And Useful Elements

Date: 2026-05-11

## Goal

Resolve the remaining MVP risk that the Chinese Astrology feature could look visually complete while still giving shallow or unsupported BaZi interpretation.

This slice adds:

- source-based interpretation sections,
- true solar time as an optional hour-pillar mode,
- provisional favorable/useful-element recommendations,
- explicit boundaries around final Yong Shen selection.
- a stronger Day Master strength model based on season, root, and formation evidence.
- favorable-element presence and relationship-code pressure checks.
- a Five Factors profile that groups Ten Gods by source-backed interpretive families.
- a Peach Blossom auxiliary-star slice for attraction/popularity timing evidence.
- a Palace Context layer that locates chart evidence in the Year, Month, Day, and Hour domains.

## Source Basis

Local corpus:

- `output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.md`
  - Used for Day Master as the analysis reference point, strength through season/root/formation, hidden stems, and Luck Pillar direction basis.
  - Used for palace context: Year, Month, Day, and Hour pillars describe life-stage/domain fields, and adjacent palace contacts are stronger than separated or timing-triggered contacts.
- `output/iching_private_corpus/bazi-the-destiny-code-your-guide-to-the-four-pillar-of-destin.md`
  - Used for the distinction between advanced Useful God/Yong Shen work and beginner-level favorable-element balancing.
  - Used for the strong Day Master rule: reduce excess through Wealth, Output, or control pressure; avoid more Companion/Resource support.
  - Used for the weak Day Master rule: favor Resource/Companion support; avoid Output, Wealth burden, and over-control.
  - Used for the Five Factors layer: Companion, Output, Wealth, Influence, and Resource are interpreted from the Day Master before direct/indirect Ten God labels are expanded.
  - Used for Peach Blossom reference groups: the Day Branch determines the target Peach Blossom branch, and the star can appear in natal, Luck Pillar, or annual layers.
- `output/iching_private_corpus/bazi-the-destiny-code-revealed-a-deeper-journey-into-the-four-pillars-of-destiny.md`
  - Used for relationship-code interpretation boundaries: severity depends on code type, affected element, affected palace, and whether the code is natal or activated by Luck/Annual pillars.
  - Used for Peach Blossom guardrails: the star is not automatically good or bad; its placement and relationship-code pressure matter.

External references:

- [NOAA General Solar Position Calculations](https://gml.noaa.gov/grad/solcalc/solareqns.PDF)
  - Used for equation-of-time and true-solar-time formula: equation of time plus longitude/timezone correction.
- [US Naval Observatory: The Equation of Time](https://aa.usno.navy.mil/faq/eqtime)
  - Used for the civil-time versus apparent-solar-time rationale and the 4-minutes-per-longitude-degree correction.
- [BaZi Calculator Real Solar Time note](https://bazi-calculator.com/instr/RST.pdf)
  - Used as BaZi-domain support that real solar time can change the hour pillar and sometimes other pillars.
- [BaZi Open Guide: Day Master Strength and Useful God](https://bazi8.net/learn/self-strength)
  - Used as a modern cross-check for the broad rule: strong charts need draining/circulating forces; weak charts need support.
- [ZodiacZen: Strong vs Weak Day Master and Yong Shen](https://zodiaczen.cc/learn/bazi/strong-weak-day-master/)
  - Used as a modern cross-check that Useful God is structural and should not be selected from simple element counts alone.

## Implemented Behavior

### Source-Based Reading

The backend now returns `interpretation` with:

- Day Master frame,
- season/root evidence,
- Ten God texture,
- hour-pillar timing note,
- Useful Element boundary,
- relationship-code highlights,
- timing highlights when Luck Pillars are enabled.

This prose is generated from computed chart evidence. It does not copy source text.

### True Solar Time

The route accepts:

- `use_true_solar_time: true`
- `true_solar_time: true`
- `solar_time_mode: "true_solar"` or `"real_solar"`

When longitude and known birth time are available, the hour pillar uses apparent/true solar time:

```text
true_solar_offset_minutes = equation_of_time + 4 * longitude - 60 * timezone_offset_hours
```

The response includes:

- `birth.true_solar_time`,
- `debug.true_solar_time`,
- `debug.hour_pillar_comparison`,
- selected mode in `debug.hour_rule`.

Civil local time remains the default because birth records are normally written in civil time. True solar mode is opt-in and shown as an hour-pillar mode.

Boundary:

- The current implementation applies true solar time to the hour pillar.
- If true solar time crosses the civil date, the engine warns that day-boundary variants are not applied yet.

### Useful God / Favorable Elements

The backend now returns `useful_elements`.

Status values:

- `provisional`: chart strength is strong or weak enough for a source-based favorable-element preview.
- `withheld`: chart strength is balanced or uncertain, so the app does not name a Useful God.

For a strong Day Master:

- favorable preview: Wealth, Output, conditional Influence,
- caution: Companion and Resource.

For a weak Day Master:

- favorable preview: Resource and Companion,
- caution: Influence, Output, and Wealth.

Boundary:

- This is not a final Yong Shen engine.
- Final Yong Shen still needs validated strength fixtures, special chart structures, climate adjustment, and damaged-useful-element checks from relationship codes.

### Favorable-Element Presence And Pressure

The next pass adds an evidence layer under `useful_elements.element_integrity`.

For every favorable, unfavorable, or watch-list element, the backend now reports:

- whether the element is present in natal stems, branches, or hidden stems,
- whether the active Luck Pillar or current annual pillar supplies the element,
- whether configured relationship codes touch that element,
- whether the relationship-code tone is supportive, challenging, or mixed,
- a short provisional summary suitable for the `Useful` tab.

This directly addresses two source constraints:

- favorable elements are stronger when they are present in the natal chart or supplied by timing,
- clashes, punishments, harms, destructions, and combinations cannot be read as uniformly good or bad without checking the affected element and palace.

The UI shows this as `Presence & Pressure` inside the `Useful` tab. This keeps the MVP practical while avoiding a false final Yong Shen claim.

### Five Factors / Ten Gods Profile

The next slice upgrades `ten_gods` from a raw row list into a source-backed `factor_profile`.

Backend behavior:

- The Day Stem is labeled as `Day Master` and is not counted as a separate visible Ten God.
- Visible stems and hidden branch stems are separated, because the local source treats stems as surface expression and branches/hidden stems as rooted or less obvious material.
- Each Five Factor reports its mapped element, direct/indirect Ten God variants present, visible count, hidden count, keywords, and provisional favorability.
- Favorability is linked to the current useful-element preview when available, but remains `unresolved` when the engine withholds useful elements.
- The summary stays descriptive; it does not turn repeated factors into deterministic topic predictions.

Frontend behavior:

- The `Ten Gods` tab now starts with a `Five Factors` panel styled like the existing Synastry/Trait Profile research cards.
- The raw Ten God rows remain available underneath for auditability.
- The day stem appears as the Day Master in the chart grid, matching the source role of the Day Master as the reference point.

### Peach Blossom Auxiliary Star

The next slice adds `auxiliary_stars.peach_blossom`.

Backend behavior:

- The Day Branch determines the personal Peach Blossom branch.
- The engine detects the target branch in the natal Year, Month, Day, and Hour pillars.
- The engine also detects the target branch in the active Luck Pillar and current annual pillar when timing data is available.
- Relationship-code events are checked for pressure against the target branch so the UI can show whether the placement is clear, mixed, or pressured.
- The four Peach Blossom family branches (`Zi`, `Wu`, `Mao`, `You`) are tracked without turning animal-zodiac content into the main reading.

Frontend behavior:

- A new `Stars` tab shows a Peach Blossom card using the same compact reading-workspace style as the Synastry and Trait/Profile surfaces.
- The card shows target branch, natal/timing activation counts, pressure state, keywords, and the evidence rows that produced the reading.
- If all four Peach Blossom branches appear, the UI shows a caution that this needs relationship-code review instead of presenting it as automatically favorable.

Boundary:

- The 2026-05-13 polish expands the tab into source-anchored Shen Sha marker detection for Peach Blossom, Traveling Horse, General Star, Wen Chang, Tian Yi Nobleman, Heavenly Virtue, and Moon Virtue.
- These markers remain placement cues. They do not override Day Master strength, Ten Gods, useful elements, relationship contacts, or timing.

### Palace Context

The next slice adds `palace_context`.

Backend behavior:

- Builds one source-backed context card for each natal pillar: Year, Month, Day, and Hour.
- Maps each pillar to its life-stage domain and its stem/branch field.
- Attaches relationship-code events to the palace they touch.
- Attaches natal auxiliary-star activations, starting with Peach Blossom.
- Keeps Luck Pillar and annual events as indirect/timing-triggered palace pressure unless a later school-specific rule is added.

Frontend behavior:

- A new `Palaces` tab shows the four palace cards in the same compact reading-workspace style.
- Relationship-code events display their placement note, such as adjacent palace contact or timing-triggered indirect pressure.
- Zero counts now render as `0`, not as a missing-value dash.

Boundary:

- Palace context locates where evidence operates; it does not replace Day Master strength, Ten Gods, Useful Element, or relationship-code judgement.
- The layer is descriptive and source-bounded, not a fixed life prediction.

### Strength Model Pass

The next slice replaced the earlier count-heavy strength preview with `season_root_formation_v2`.

Source-aligned weighting:

- season / month branch: 70%,
- root: 25%,
- formation: 5%.

Implementation notes:

- Month branch determines the seasonal state: Spring, Summer, Autumn, or Winter.
- The engine encodes the source season table: prosperous, strong, weak, very weak, dead/out of season.
- Day branch hidden stems are treated as the normal root.
- Hour branch hidden stems are treated as the secret root.
- Month/year hidden stems and visible stems contribute as secondary formation evidence.
- Earth receives a conservative floor because the local source says Earth is less seasonally fragile than the other elements.

The response now exposes:

- `analysis.weighted_score`,
- `analysis.strength_model.method`,
- `analysis.strength_model.season`,
- `analysis.strength_model.root`,
- `analysis.strength_model.formation`,
- `analysis.strength_model.confidence`.

Useful Element recommendations still stay `provisional` or `withheld`; this strength pass improves the evidence base but does not claim final Yong Shen.

## Frontend Placement

The feature stays inside Astro Clock and uses the same modal visual language as Synastry and Trait Profile.

Added/updated UI:

- `Reading` tab for source-based interpretation.
- `Useful` tab for provisional favorable-element guidance.
- `Stars` tab for the source-backed Peach Blossom auxiliary-star preview.
- `Palaces` tab for Year/Month/Day/Hour life-stage and domain context.
- `Day Master` tab now shows season/root/formation evidence, weighted score, and confidence.
- `Details` tab now shows true solar time, correction minutes, and civil-versus-true-solar hour-pillar comparison.
- Header control switches hour mode between `Civil` and `True Solar`.
- Direct input supports optional latitude/longitude for true solar mode.

Saved snaps remain the preferred workflow. When a saved snap includes coordinates, true solar mode can use them without asking the user to re-enter location data.

## Remaining Guardrails

- Do not present the provisional favorable elements as fixed life advice.
- Keep animal-zodiac content as branch metadata only.
- Keep day-boundary school variants visible in warnings, not silently applied.
- Add fixture cases before promoting `useful_elements.status` from `provisional` to a final Yong Shen claim.
