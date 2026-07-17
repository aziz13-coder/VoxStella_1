# Trait Profile Sketch Benchmark Test

Date: 2026-05-05
Rescan update: 2026-05-05, second pass for Topic Maps and House Influence

## Purpose

This benchmark verifies that the production Trait Profile redesign follows the AI sketch in `voxstella traIT profile.zip` while keeping every visible value real, derived, or explicitly unavailable.

The sketch is a visual and workflow reference. Its mock data is not a production data source.

## Source-Only Scope

Files in scope for this benchmark:

- `frontend/src/features/astroclock/TraitProfileModal.jsx`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/traitProfileViewModel.mjs`
- `frontend/src/tests/traitProfileModal.test.jsx`
- `frontend/src/tests/traitProfileViewModel.test.mjs`

Do not edit generated/package artifacts to pass this benchmark:

- `frontend/dist-electron/**`
- `frontend/backend/build/**`
- `frontend/dist/**`
- `website/**`
- any `win-unpacked/**`, `resources/**`, `venv/**`, or `node_modules/**`

## Sketch Inputs

Sketch package:

- `C:/Users/sabaa/Downloads/codexhorary/voxstella traIT profile.zip`

Zip contents inspected:

- `Trait Profile.html`
- `app.jsx`
- `chrome.jsx`
- `tabs.jsx`
- `data.js`
- `uploads/*.png`

The sketch was rendered locally at `1440 x 900` from the extracted HTML/JSX using:

```powershell
cd "$env:TEMP/voxstella_trait_profile_sketch_20260505"
python -m http.server 5174 --bind 127.0.0.1
```

Then opened at:

```text
http://127.0.0.1:5174/Trait%20Profile.html
```

The second benchmark pass captured the sketch `Topic Maps` and `House Influence` tabs directly after clicking their tab buttons. These were used as the comparison target for the layout polish.

## Sketch Visual Contract

The rendered sketch establishes these visual targets:

- Centered modal, `min(1380px, 96vw)` by `min(900px, 92vh)`.
- Dimmed Astro Clock dashboard backdrop.
- White modal paper, 16px radius, thin borders, subtle large shadow.
- Sticky header block with micro uppercase labels and restrained controls.
- Serif headline/display text plus mono micro labels.
- Pill tabs: `Overview`, `Domains`, `Topic Maps`, `House Influence`, `All Traits`.
- Compact filter bar with wrapping controls and domain count at right.
- Overview uses open analytical columns, rails, and row dividers rather than card walls.
- Topic Maps uses two worksheet columns: profession and health.
- House Influence uses an open three-column sequence of house worksheets, not individual heavy cards.

## Production Deviations Required For Data Honesty

These sketch elements must not be copied literally:

| Sketch element | Production decision |
| --- | --- |
| `Overall temperament` | Replaced with real `Profile balance`. Do not call it temperament. |
| Fixed score `78/100` | Replaced by `profileBalanceIndex` from `traitProfileViewModel.mjs`. |
| Domain count `129/129` | Replaced by real selected/all unique domains. |
| `Band: virtue/style/behavioral risk` | Replaced by real backend strength bands: `strong`, `likely`, `possible`, `weak`. |
| `Positive/Neutral/Negative` labels | Shown as `Constructive`, `Style`, `Strain`. |
| `Source` filter and `Carter-derived` chips | Not shown. Source/citation metadata remains backend data only, not visible Trait Profile chrome. |
| `Modern` / `Bodies` scope buttons | Not shipped as active fake controls unless backend supports the query contract. |
| `Almuten` chip | Hidden unless returned by a real backend field. |
| Factor breakdown bars | Not shown until backend exposes structured factor rows. Use real evidence text instead. |
| `Compare in chart` | Hidden until a real chart-focus behavior exists. |

## Current Implementation Benchmark

### Modal Shell

Pass criteria:

- Modal dimensions and backdrop match the sketch proportions.
- Header, subject strip, tab row, filter row, and scroll body stay in the Synastry/Astro Clock language.
- Header actions remain real: `Copy AI Prompt` and `Close`.
- Chart source is real: users can choose `Current` or `Saved Snap`; saved snap selection refetches using snap datetime/location/timezone/coordinates.

Current status: pass.

### Overview

Pass criteria:

- Uses `Profile balance`, not `Overall temperament`.
- Constructive, Style, and Strain signals are derived from real trait scores.
- Top rows are real traits from backend response/selectors.
- No visible source/citation labels.

Current status: pass.

### Domains

Pass criteria:

- Domain index comes from real unique `trait.domain` values.
- Domain search and selection are interactive.
- Counts update from real filtered data.
- No sketch-fixed `129` total.

Current status: pass.

### Topic Maps

Pass criteria:

- Two-column worksheet layout at desktop.
- Header follows the sketch frame: `Morin / Topic maps` and `Where the chart pulls in life`.
- Profession and Health sections use open row rhythm with thin dividers.
- Profession/Health lead-route-pressure rows are vertical worksheet rows, not boxed summary cards.
- Uses real `house_influences.houses[]`, `basic_analysis`, profession suggestions, health suggestions, and fixed-star suggestions where available.
- No mock profession/health values from `data.js`.
- No heavy card shell around the two worksheet areas.

Current status: pass after rescan polish.

### House Influence

Pass criteria:

- Open `H1` through `H12` worksheet sequence.
- Header follows the sketch frame: `Houses 1 - 12` and `Where each life-area pulls power from`.
- Desktop grid uses three columns; narrow widths collapse.
- Each house shows house number, sign, optional cusp when real, top influence rows, meters, values, keywords, and detail disclosure.
- No individual rounded card shells for each house.
- Missing cusp displays `-`, not invented text.
- Existing production detail affordances remain wired; row-level `Details` still expands real influence breakdown data.

Current status: pass after rescan polish.

### Source Citation Visibility

Pass criteria:

- `Source` filter is not visible.
- `Carter-derived`, `Classical source`, `Source Layers`, `Corpus Citations`, citation excerpts, and source-lineage chips are not visible in the modal.
- Prompt/export can still use backend data internally if needed, but the visible feature does not cite source labels.

Current status: pass.

## Automated Checks

Run from `C:/Users/sabaa/Downloads/codexhorary`.

```powershell
npm --prefix frontend run test:ui -- src/tests/traitProfileModal.test.jsx src/tests/traitProfileViewModel.test.mjs src/tests/astroclockApi.test.mjs
```

Expected:

- All focused Trait Profile UI/view-model/API tests pass.
- Saved snap selection is covered.
- No-source-visible behavior is covered.
- Topic/house layout expectations are covered.

Run ESLint from `frontend`.

```powershell
npm exec eslint -- src/features/astroclock/TraitProfileModal.jsx src/features/astroclock/traitProfileViewModel.mjs src/tests/traitProfileModal.test.jsx src/tests/traitProfileViewModel.test.mjs
```

Expected:

- No lint errors.

Run whitespace validation from repo root.

```powershell
git diff --check -- frontend/src/features/astroclock/TraitProfileModal.jsx frontend/src/features/astroclock/AstroClock.jsx frontend/src/tests/traitProfileModal.test.jsx docs/TRAIT_PROFILE_SKETCH_BENCHMARK_TEST_2026-05-05.md
```

Expected:

- No whitespace errors. Windows line-ending warnings are acceptable if no diff-check error is emitted.

## Rescan Result

Run date: 2026-05-05

- Sketch inspected: `Trait Profile.html`, `app.jsx`, `chrome.jsx`, `tabs.jsx`, `data.js`.
- Sketch rendered in Playwright at desktop size: pass.
- Topic Maps sketch state captured directly: pass.
- House Influence sketch state captured directly: pass.
- Implementation repolish: Topic Maps and House Influence changed from card-like blocks to open worksheet layouts.
- Second-pass polish: Topic Maps lead/route/pressure changed to vertical worksheet rows; House Influence heading and row meter layout aligned with the sketch.
- Backend wiring preserved: no mock sketch data imported; all displayed map/house values still come from `house_influences`, `basic_analysis`, suggestion builders, or selected snap/current chart context.
- Regression safety: saved snap selection, domain/filter behavior, no-visible-source behavior, prompt copy path, and trait row/detail flows remain covered by focused tests.
- Dead source-filter path removed from the modal.
- Automated tests: pass, 53 focused tests.
- Lint: pass on the scoped frontend files.
- Diff check: pass; Windows line-ending warnings only.
- Data honesty: pass.
- Release decision: acceptable for source implementation pending normal packaging workflow.

## Current Known Gaps

- No structured factor breakdown bars until backend exposes stable factor rows.
- No active Modern/Bodies trait scope until `/traits/profile` accepts and applies scope parameters.
- No visible source/citation labels by design.
- Packaged builds still need to be produced through the normal packaging workflow.
