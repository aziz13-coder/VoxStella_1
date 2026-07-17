# Trait Profile Redesign Implementation Plan

Date: 2026-05-05

## Goal

Implement the AI sketch in `voxstella traIT profile.zip` as a real Astro Clock Trait Profile redesign, using the visual language of Synastry and the current Astro Clock frontend, without importing mock values from the sketch.

Every visible value must be one of:

- Directly wired from `/api/astro-clock/traits/profile`.
- Derived by a named selector with a documented formula and a unit test.
- Removed, hidden, or renamed until a real backend contract exists.

This is source-only work. Do not edit packaged artifacts under `frontend/dist-electron/**`, `frontend/backend/build/**`, `frontend/dist/**`, `website/**`, `win-unpacked/**`, `resources/**`, `venv/**`, or `node_modules/**`.

## Inputs Inspected

- Sketch zip:
  - `app.jsx`
  - `chrome.jsx`
  - `tabs.jsx`
  - `data.js`
  - `Trait Profile.html`
  - `uploads/*.png`
- Current frontend:
  - `frontend/src/features/astroclock/TraitProfileModal.jsx`
  - `frontend/src/features/astroclock/api.mjs`
  - `frontend/src/features/astroclock/knowledgeMap.mjs`
  - `frontend/src/features/astroclock/fixedStarMap.mjs`
  - `frontend/src/tests/traitProfileModal.test.jsx`
- Current backend:
  - `backend/astro_clock_api.py`
  - `backend/astro_clock_metrics.py`
  - `backend/house_influence.py`
  - `backend/traits/engine.py`
  - `backend/test_astro_clock_api_traits.py`
  - `backend/test_trait_engine_contract.py`

## Current Real Contract

`GET /api/astro-clock/traits/profile` returns:

```js
{
  success: true,
  data: {
    summary,
    special_degrees,
    sect,
    receptions,
    morin_patterns,
    house_influences,
    top_traits,
    summary_traits,
    top_traits_by_polarity,
    traits,
    guidance,
    trait_enrichment_meta,
    chart_snapshot
  }
}
```

The frontend already passes manual/realtime chart context through `getTraitProfile`, including date, location, timezone, house system, and coordinates when available.

Real backend values available now:

- Trait catalog scoring from `backend/traits/catalog/**`, currently 331 source catalog JSON files.
- Trait score fields: `score`, `raw_score`, `max_score`, `support_hits`, `support_total`, `dampener_hits`, `band`, `polarity`.
- Trait metadata: `id`, `name`, `domain`, `description`, `confidence`, `sources`, `family_key`, `source_status`, `source_lineage`, `source_lineage_label`, `provisional`.
- Trait explanation fields: `evidence`, `keywords`, `keyword_layers`, `citations`, `citation_summary`, `enrichment_status`.
- Summary fields: `dominant_element`, `dominant_modality`, `flags`.
- Sect info under `sect`.
- House influence values from `house_influences.houses[]`, including `influences[]`, `basic_analysis`, determinators, values, ranks, keywords, and breakdowns.
- Chart snapshot values: timestamp, location, timezone, timezone label, house system, ASC, MC, planets, moon, solar conditions, top aspects, house cusps, house rulers, receptions, special degrees.

Values not currently backed by durable backend contracts:

- `chart_snapshot.moon_timeline` is always `null`.
- `chart_snapshot.morin_aspects` is currently empty.
- `chart_snapshot.fixed_star_hits` is currently empty unless passed from frontend props.
- `chart_snapshot.morin_patterns` is currently `null`.
- No single backend field exists for "overall temperament".
- No backend field exists for an "almuten" chip in the Trait Profile response.
- No backend field exists for structured factor bars. The engine has real `evidence` strings and weights internally, but not a stable `factors[]` array.
- The sketch's `Traditional / Modern / Bodies` scope switch is not a real trait-profile query contract yet.

## Sketch Inventory

The sketch is a standalone React prototype. Its `data.js` file is mock data and explicitly says numbers are illustrative.

Main layout:

- Dimmed Astro Clock dashboard backdrop.
- Centered modal: `min(1380px, 96vw)` by `min(900px, 92vh)`.
- Synastry-like micro labels, pill tabs, sticky header block, thin dividers, restrained white/surface palette.

Sketch tabs:

- Overview
- Domains
- Topic Maps
- House Influence
- All Traits

Sketch interactions:

- Header close.
- Copy AI prompt.
- Scope pills.
- Global filters.
- Domain search and domain selection.
- Trait row opens a detail drawer.
- House row has a `Show details` affordance.

## Realness Rules For Implementation

1. No static sketch values enter production.
2. No display-only controls. If a button, tab, filter, or toggle is visible, it must either work or be disabled with a real reason.
3. Any derived value gets a named selector in a view-model module and a unit test.
4. JSX should render view-model fields, not calculate business meaning inline.
5. Source citations should not be a primary UI surface in the redesign. The backend can keep citations for prompt/export support, but the visual design should use concise source lineage chips unless detailed provenance is explicitly opened.
6. The UI labels must match the actual data. Do not call a strength band "virtue/style/risk" unless the backend provides that classification.

## Wire Or Replace Matrix

| Sketch element | Decision | Real source or action |
| --- | --- | --- |
| Modal shell | Implement | Rebuild `TraitProfileModal.jsx` shell to match Synastry modal proportions, sticky chrome, tabs, and restrained Astro Clock palette. |
| Header title | Implement | Static product text is okay: `Astro Clock / Trait Profile`. |
| Chart/live label | Implement | Derived from current mode and `chart_snapshot.timestamp`; show `chart / manual` or `chart / live` truthfully. |
| Copy AI Prompt | Keep | Existing `copyAiPrompt` is real. Update it to use the new view model where useful. |
| Close | Keep | Existing `onClose`. |
| Subject strip chart label | Implement | `chart_snapshot.timestamp`, `chart_snapshot.location`, `chart_snapshot.timezone_label`, `chart_snapshot.house_system`. |
| Traditional / Modern / Bodies scope | Replace for first pass | Keep `Traditional` as a non-ornamental status chip. Hide or disable `Modern` and `Bodies` until `/traits/profile` accepts and applies scope/include-modern parameters. |
| House system selector | Replace for first pass | Show current house system from chart context. Do not make it look editable unless changing it refetches the profile. |
| Sketch Band filter: virtue/style/behavioral risk | Replace | Current `band` means strength: `strong`, `likely`, `possible`, `weak`. Use label `Strength`. Use `polarity` for Constructive, Style, Strain groups. |
| Polarity filter | Implement | Map backend `positive`, `neutral`, `negative` to UI labels `Constructive`, `Style`, `Strain`. |
| Source filter | Keep | Existing source filter uses `source_lineage`, `keyword_layers`, and citation lineage. |
| Sort and Top filters | Keep | Existing `sortBy` and `topCount`. Add selector tests for all redesigned lists. |
| Domains count `129/129` | Implement as real | Compute from unique `trait.domain` values and selected domain count. Use actual trait count from filtered/all list, never fixed `129`. |
| Overall temperament `78/100` | Do not implement as named | No real backend field exists. Replace with either three real signals or an explicitly named `Profile Balance Index`. Do not label it "temperament" unless backend defines that term. |
| Profile Balance Index | Optional derived value | If a single hero number is required: `clamp(round(50 + (constructiveSignal - strainSignal) / 2), 0, 100)`. Label it `Profile balance`, not temperament. Show/tooltip the formula. |
| Constructive signal | Implement | Weighted average of visible positive summary traits. Recommended weight: `max(1, support_hits)`. Fallback to simple average. |
| Style signal | Implement | Weighted average of visible neutral summary traits. |
| Strain signal | Implement | Weighted average of visible negative summary traits. |
| Signature headline | Replace mock copy | Deterministic text from real top traits and summary, e.g. `{dominant_modality} {dominant_element} profile led by {topPositive.name}; checked by {topNegative.name}.` |
| Italic interpretation quote | Replace mock copy | Use deterministic summary sentence from top polarity traits, or omit in first pass. Do not write literary static copy. |
| Element chip | Implement | `data.summary.dominant_element`. |
| Modality chip | Implement | `data.summary.dominant_modality`. |
| Sect chip | Implement | `data.sect`, normalized to a short display label. |
| Ruler chip | Implement as chart ruler | Use `chart_snapshot.house_rulers["1"]` or equivalent ASC ruler. Label `Chart ruler`, not generic `Ruler`. |
| Almuten chip | Replace or backend task | Hide in first pass. Add only if backend returns `chart_snapshot.almutens` or `summary.almuten`. |
| Top trait columns | Implement | Use `top_traits_by_polarity` with existing frontend fallback to `summary_traits`. |
| Trait score bars | Implement | `trait.score`, clamped to 0-100. Bar color follows `trait.polarity`. |
| Raw score | Implement | `trait.raw_score` / `trait.max_score`. |
| Supports | Implement | `trait.support_hits` / `trait.support_total`. |
| Related variants | Implement | Existing `family_size` / `related_traits` when present. |
| Trait source chip | Implement | `trait.source_lineage_label`, fallback from `source_lineage`, plus provisional status. |
| Trait domains/tags | Implement | `trait.domain` and `trait.keywords`. The sketch's `tags` map to current `keywords`, not a separate tag system. |
| Trait detail drawer | Implement | Use selected trait from real list. Include score, supports, raw score, summary/description, evidence, keywords, source lineage. |
| Factor breakdown bars | Backend task or replace | First pass: show `evidence` as bullets. Later add backend `evidence_factors[]` with `{label, value, kind}` and then render bars. Do not parse strings into factor bars in JSX. |
| Corpus citations | De-emphasize | Hide from main cards. Keep optional detail section only if needed for debugging/review, not as the default design. |
| Domains tab search | Implement | Frontend-only over real unique domains. Counts computed from actual traits per domain after current filters. |
| Domain grouped traits | Implement | Group matching traits by polarity and sort using same view-model selectors. |
| Profession Map | Implement | Existing real house influence/basic analysis plus `buildProfessionSuggestions`. Move calculations into tested selectors. |
| Health Map | Implement | Existing real H1/H6/H12 house influence/basic analysis plus `buildHealthSuggestions`. Move calculations into tested selectors. |
| Topic map triplicity dots/shares | Implement as derived | Current frontend already computes from influence types. Extract to selector and test with fixture. |
| House Influence tab | Implement | Use `house_influences.houses[]` and `influences[]`. Values are real. |
| House `Show details` | Implement | Open house detail panel/expanded section using `basic_analysis`, determinators, top aspects, and influence breakdown. |
| `Compare in chart` button | Hide first pass | No real behavior exists in the current trait modal. Add only when it can focus/highlight chart evidence. |
| Loading/error/empty states | Implement | Preserve current loading/error; add no-results and no-domain states for every tab. |

## Proposed Frontend Architecture

Do not port the sketch as one large component. Use the sketch as visual reference, then build around a tested view model.

Recommended source files:

- `frontend/src/features/astroclock/TraitProfileModal.jsx`
  - Container, fetch lifecycle, modal state, tab state, event handlers.
- `frontend/src/features/astroclock/traitProfileViewModel.mjs`
  - Pure selectors and derived formulas.
  - No React.
  - Unit tests for every displayed score/count/summary.
- `frontend/src/features/astroclock/TraitProfileChrome.jsx`
  - Modal header, subject strip, tabs, filters.
- `frontend/src/features/astroclock/TraitProfileSections.jsx`
  - Overview, Domains, Topic Maps, House Influence, All Traits, Detail Drawer.
- Optional `frontend/src/features/astroclock/traitProfileTheme.mjs`
  - Shared labels/colors/class names if the JSX becomes noisy.

If keeping a smaller change set is preferable, `TraitProfileChrome.jsx` and `TraitProfileSections.jsx` can stay inside `TraitProfileModal.jsx` initially, but `traitProfileViewModel.mjs` should still be split out. The view-model split is what keeps values honest.

Suggested view-model shape:

```js
{
  chart: {
    modeLabel,
    timestampLabel,
    locationLabel,
    timezoneLabel,
    houseSystemLabel
  },
  summary: {
    dominantElement,
    dominantModality,
    sectLabel,
    chartRuler,
    signatureLine,
    signatureNote
  },
  signals: {
    constructive: { value, count, label, traits },
    style: { value, count, label, traits },
    strain: { value, count, label, traits },
    profileBalanceIndex: null | number
  },
  domains: {
    all,
    selected,
    counts,
    visibleCount,
    totalCount
  },
  tabs: {
    overview,
    domains,
    topicMaps,
    houses,
    allTraits
  }
}
```

## Derived Formula Decisions

### Polarity Signals

Use real scored traits only.

```js
weightedAverage(traits) =
  sum(trait.score * max(1, trait.support_hits || 0)) /
  sum(max(1, trait.support_hits || 0))
```

If no traits exist for a polarity, return `null`, not `0`. A missing signal should display as "No indicated traits", not a zero score.

### Profile Balance Index

This is optional. It should not be present by default if the goal is maximum interpretive honesty.

If product wants a single hero number:

```js
profileBalanceIndex =
  clamp(round(50 + (constructiveSignal - strainSignal) / 2), 0, 100)
```

Rules:

- Label: `Profile balance`.
- Do not label: `Temperament`.
- Hide when either constructive or strain signal is missing.
- Add a tooltip or detail line: "Derived from constructive and strain trait signals."
- Test the formula directly.

### Signature Text

Use deterministic text from real fields:

```js
signatureLine =
  "{dominantModality} {dominantElement} profile with {topConstructive.name} leading"
  + (topStrain ? "; {topStrain.name} is the main strain." : ".")
```

Fallback order:

1. Dominant modality + element + top constructive + top strain.
2. Dominant modality + element + top available trait.
3. "Trait profile is ready" only if no traits are indicated.

No fixed poetic copy from the sketch.

## Backend Enhancements, Only If Needed

The first redesign can be done mostly in frontend source because the key data already exists. Backend changes should be limited to values that cannot be derived honestly in the frontend.

Candidate backend additions:

1. `trait.evidence_factors[]`
   - Source: `TraitEngine.evaluate`.
   - Purpose: structured factor bars in the trait detail drawer.
   - Shape:
     ```js
     {
       label: string,
       value: number,
       kind: "boost" | "dampener" | "escalator",
       condition_kind: string
     }
     ```
   - Tests: `backend/test_trait_engine_contract.py`.

2. `chart_snapshot.chart_ruler`
   - Source: ASC sign/ruler already available in chart data/house rulers.
   - Purpose: avoid frontend guessing for the `Chart ruler` chip.
   - Tests: `backend/test_astro_clock_api_traits.py`.

3. `chart_snapshot.almutens` or `summary.almuten`
   - Only if the almuten chip is required.
   - Must use the same source logic as existing Astro Clock almuten displays, not a new unrelated formula.

4. `topic_maps`
   - Optional future server contract for profession/health maps.
   - Not required for first pass because current frontend helpers already derive maps from real house influence data.

When backend source changes are made, apply them to source twins as needed:

- `backend/**`
- `frontend/backend/**`

Never patch packaged backend files.

## Implementation Phases

### Phase 1: View Model First

Create `traitProfileViewModel.mjs` and tests before changing the UI.

Selectors to implement:

- `normalizeTraitProfilePayload(data, opts)`
- `buildTraitChartSummary(data, opts)`
- `buildPolaritySignals(data, filters)`
- `buildProfileSignature(data, signals)`
- `buildDomainIndex(traits, filters)`
- `filterAndSortTraits(traits, filters)`
- `buildTopicMapViewModel(houseInfluences, fixedStarHits)`
- `buildHouseInfluenceViewModel(houseInfluences)`

Test targets:

- `frontend/src/tests/traitProfileViewModel.test.mjs`
- Extend `frontend/src/tests/traitProfileModal.test.jsx` only for integration behavior.

Acceptance:

- Every planned visible count and score has a selector test.
- `Profile balance` returns `null` when inputs are insufficient.
- Domain counts are never hard-coded.

### Phase 2: Modal Chrome

Rebuild the modal shell to match Synastry/Astro Clock language:

- Centered large modal over dimmed app.
- Sticky header block.
- Header row with glyph, route label, copy prompt, close.
- Subject strip with chart context.
- Pill tabs.
- Filter bar.

Controls:

- Rename `Band` to `Strength`.
- Polarity options display as `Constructive`, `Style`, `Strain`.
- Keep source/sort/top/domain filters.
- Hide unsupported scope switches or show only `Traditional`.

Acceptance:

- Existing fetch behavior still works.
- Existing copy prompt still works.
- Modal remains usable at desktop and mobile widths.

### Phase 3: Overview Tab

Implement:

- Real chart summary chips.
- Real `Constructive`, `Style`, `Strain` signal panels.
- Real top trait columns from `top_traits_by_polarity` or selector fallback.
- Deterministic signature line.
- Optional `Profile balance` only if accepted as a derived index.

Do not implement:

- Mock "Overall temperament".
- Mock poetic quote.
- Mock almuten.

Acceptance:

- Snapshot/DOM tests prove the hero uses actual API fixture data.
- No visible `78`, `129`, or sketch-only text appears unless fixture data provides it.

### Phase 4: Domains Tab

Implement:

- Left domain index with search.
- Real domain counts.
- Active domain detail grouped by Constructive/Style/Strain.
- Shared sorting/filter rules.

Acceptance:

- Domain count updates from fixtures.
- Empty domain search state works.
- Domain selection affects visible traits and count labels.

### Phase 5: Topic Maps Tab

Implement with existing real helpers:

- Profession Map from H10, H2, H6, H4.
- Health Map from H1, H6, H12.
- Determinator rows: Lead, Route, Pressure, Context.
- Triplicity/share chips from influence types.
- Suggestions from `knowledgeMap.mjs` and `fixedStarMap.mjs` only when real fixed-star hits exist.

Move current inline calculations out of JSX where practical.

Acceptance:

- Topic maps render from `house_influences` fixtures.
- If H10/H1/H6 are missing, the tab shows an honest empty state.
- Fixed-star suggestions do not appear unless hits exist.

### Phase 6: House Influence Tab

Implement:

- Twelve-house grid from `house_influences.houses[]`.
- Top influences per house, using real `value`, `rank`, `type`, `planet`, `aspect`, and `keywords`.
- Details expansion/drawer for `basic_analysis`, determinators, aspect top, ruler map, and breakdown.

Acceptance:

- Bars scale from real influence values.
- Detail button opens real details.
- No house card appears with mock sign/degree values.

### Phase 7: Trait Detail Drawer

Implement:

- Open from any trait row.
- Score, supports, raw score.
- Description or summary text from real trait fields.
- Evidence list.
- Source lineage chip.
- Keyword/domain chips.
- Related variants if present.
- Copy prompt scoped to selected trait if useful.

Factor bars:

- First pass: use evidence bullets.
- Later pass: add backend `evidence_factors[]` and then render bars.

Acceptance:

- Drawer content changes when a different trait is selected.
- No factor bar is rendered from parsed free-text evidence.

### Phase 8: Optional Backend Additions

Only after the frontend can prove a missing contract is blocking a real UI value:

- Add `evidence_factors[]`.
- Add `chart_ruler`.
- Add `almuten` only if required.
- Add server-side topic maps only if frontend heuristics need to become API-stable.

Backend tests must be written first for new fields.

### Phase 9: Verification

Run:

```powershell
python -m pytest -p no:cacheprovider backend/test_astro_clock_api_traits.py backend/test_trait_engine_contract.py
npm --prefix frontend run test:ui -- frontend/src/tests/traitProfileViewModel.test.mjs frontend/src/tests/traitProfileModal.test.jsx frontend/src/tests/astroclockApi.test.mjs
```

Then browser-check:

- Manual chart Trait Profile opens quickly.
- Realtime chart Trait Profile opens quickly.
- Copy prompt works.
- Each tab renders.
- Filters update counts and visible rows.
- No unsupported ornamental buttons are visible.
- Text fits at desktop and narrow widths.

## Recommended First Implementation Cut

The safest first cut is:

1. Add `traitProfileViewModel.mjs` with tests.
2. Redesign the modal shell and Overview tab.
3. Keep existing Topic Maps and House Influence behavior but restyle them through the new components.
4. Hide `Almuten`, `Modern`, `Bodies`, and `Compare in chart`.
5. Replace "Overall temperament" with three real signals. Add `Profile balance` only if the single hero number is explicitly wanted as a derived index.

This produces the requested design direction without corrupting the feature with attractive but unwired values.

## Definition Of Done

- No production UI text or numbers copied from the sketch mock data.
- Every visible score/count has a selector or backend field.
- Every selector has a test.
- Unsupported sketch controls are hidden or disabled with a truthful reason.
- Existing API context passing remains intact.
- Existing AI prompt copy behavior remains intact.
- Source-only files changed.
- Tests pass.
