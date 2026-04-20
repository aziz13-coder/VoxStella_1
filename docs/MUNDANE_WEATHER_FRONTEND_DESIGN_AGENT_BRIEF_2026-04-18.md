# Mundane And Weather Frontend Design Agent Brief

Date: 2026-04-18

## Goal

Prepare a frontend-only brief for an external AI design agent so it can propose a stronger design language for the Astro Clock `Mundane` and `Weather` modules.

The target is not a backend redesign and not a feature rewrite. The target is a UI and UX redesign that makes these two modules feel like they belong to the same product family as `Astro Clock`, `Transits`, `Election`, and the stronger parts of `Astrocartography`, while still giving them a distinct identity.

## Scope

Focus only on source frontend surfaces:

- `frontend/src/features/astroclock/MundaneWorkspace.jsx`
- `frontend/src/features/astroclock/MundaneScanWorkspace.jsx`
- `frontend/src/features/astroclock/WeatherWorkspace.jsx`

Reference design language from:

- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/TransitsModal.jsx`
- `frontend/src/features/astroclock/ElectionModal.jsx`
- `frontend/src/features/astroclock/AstrocartographyModal.jsx`

## Product Context

`Mundane` and `Weather` live inside the Astro Clock advanced-workspace family. They are not simple settings forms. They are research workbenches that mix setup, async computation, inspection, and interpretation.

Both modules already use a three-column structure:

- left rail: setup, filters, and run actions
- center: primary results surface
- right rail: inspector, calibration, or supporting evidence

That base structure is correct. The issue is the current presentation. Both modules read as flat white card stacks with similar chrome everywhere, so setup, live execution, results, and deep inspection all compete at the same visual level.

## Current Frontend Features

### Mundane

`Mundane` has two major modes.

#### 1. Analysis mode

Current inputs and controls:

- chart type
- domain lens
- chart source toggle
- polity and national chart selection for registered charts
- custom chart entry path
- context overrides
- event overrides
- resolve context action
- analyze action

Current outputs:

- resolved context panel
- assessment summary
- level and score pills
- framework layer
- trigger layer
- activation layer
- domain notes
- calibration panel
- matched rules
- doctrine sources
- chart type notes
- context notes

Current state cases:

- empty before resolve
- resolved context without analysis
- analysis loaded
- loading resolve
- loading analysis
- error state

#### 2. Scan mode

Current inputs and controls:

- chart type
- domain lens
- chart source toggle
- polity and national chart
- context options tied to scan setup
- region or scan-specific limits and time slices
- run scan
- refresh or reset

Current outputs:

- execution and progress panel
- percent, done, total, and failure metrics
- returned count
- top cells or top places
- selected top candidate
- scan inspector
- breakout surfaces
- pressure-matrix style visualization
- peak window summaries

Current state cases:

- idle before scan
- running scan with partial progress
- running scan with no result rows yet
- completed scan with ranked cells
- selected candidate inspection
- error state

### Weather

`Weather` also has two major modes.

#### 1. Analysis mode

Current inputs and controls:

- weather family selection
- forecast override fields
- location and timezone overrides
- resolve context
- analyze
- clear

Current outputs:

- resolved weather context
- family assessment
- score and strength summary
- framework layer
- trigger layer
- locality layer
- calibration panel
- rule source lists
- notes

Current state cases:

- empty before resolve
- resolved context without analysis
- analysis loaded
- loading resolve
- loading analysis
- error state

#### 2. Scan mode

Current inputs and controls:

- weather family
- scan scope toggle
- place timeline or region timeline path
- place, region, timezone, and time-window fields
- resolution
- candidate limit
- top-k style limits
- run weather scan
- reset

Current outputs:

- async execution panel
- progress bar and scan status
- summary metrics
- result-view toggle
- graph view
- dates view
- scan inspector
- top windows or top candidate rows

Current state cases:

- idle before scan
- running scan
- running scan with no surfaced windows yet
- completed scan with graph or date output
- selected result inspection
- error state

## Current UI Character

The current mundane and weather frontend already has a coherent internal pattern, but it is too generic relative to the rest of Astro Clock.

Current visual traits:

- pale app background
- white cards everywhere
- soft blue accents
- rounded borders on nearly everything
- many pills and metric badges
- dashed empty-state boxes
- repeated section cards for almost every unit of information
- long left rails with form fields grouped into similar-looking cards

Current UX problems:

- control surfaces and result surfaces look too similar
- the eye does not know what is primary
- execution state, scan progress, and final interpretation share almost the same card treatment
- the right rail often feels like another stack of equal-weight boxes instead of a true inspector
- empty states take up space but do not help orientation
- the left rail feels heavier than the center pane in early states
- mundane scan and weather scan look too similar to each other
- these modules feel more like internal dashboards than polished Astro Clock workspaces

## Reference Design Language To Borrow From

Use the stronger Astro Clock family surfaces as the reference point, especially:

- Astro Clock main workspace
- Transits
- Election
- Astrocartography advanced workspace

Important qualities from those surfaces:

- stronger hierarchy between setup, live state, and result interpretation
- more obvious “operator console” feeling
- more distinct section framing
- clearer primary canvas or primary result zone
- less visual equality between every card
- better narrative flow from inputs to computation to insight
- more intentional use of headers, chips, and action bands
- more memorable identity per module

This does not mean copying those screens directly. It means making `Mundane` and `Weather` feel like sister tools inside the same platform.

## Design Problem To Solve

We want a new design language for `Mundane` and `Weather` that:

- overlaps with the Astro Clock family
- preserves the three-column research-workspace architecture where appropriate
- makes scan mode feel operational and alive
- makes analysis mode feel interpretive and editorial
- gives mundane and weather their own identities instead of looking like duplicate shells
- reduces the sense of form overload
- improves hierarchy without removing important expert detail

## Constraints

- frontend only
- do not change backend contracts
- do not remove existing feature coverage
- do not assume simpler data
- support async-running, partial, empty, success, and error states
- preserve dense expert workflows
- keep the result readable on desktop first, but avoid breaking narrower widths
- the redesign should be implementable in the current React and Tailwind-style component system

## What The Design Agent Should Deliver

Ask the design agent for:

1. A new shared design language for `Mundane` and `Weather`
2. Distinct sub-identities for each module
3. A proposal for scan-mode layout hierarchy
4. A proposal for analysis-mode layout hierarchy
5. Ideas for how progress, inspector, and result-selection states should look
6. Suggestions for card density, spacing, type hierarchy, pill usage, and section framing
7. Recommendations for how to make the center pane feel like the primary surface
8. Suggestions for how to make empty states and pre-run states feel intentional instead of blank
9. A component strategy that can still share primitives with Astro Clock
10. Two or three visual directions, not just one

## Ready-To-Send Prompt

Use the following prompt with the external design agent.

```text
You are helping redesign two advanced frontend research modules inside an astrology desktop application: Mundane and Weather.

I will show you screenshots of:
- the current Mundane UI
- the current Weather UI
- stronger reference surfaces from the same app family, especially Astro Clock, Transits, Elections, and Astrocartography

Your job is to propose a new frontend design language for Mundane and Weather only.

This is not a backend redesign. Do not remove major features. Work with the current feature density and async behavior, but redesign the layout, hierarchy, framing, and visual system so these modules feel like they belong to the same product family as the stronger Astro Clock tools.

Product context:
- Both modules are advanced “research console” workspaces inside Astro Clock.
- Both currently use a 3-column layout:
  - left rail for setup and controls
  - center for main results
  - right rail for inspector, calibration, and supporting evidence
- The current UI is functional but too flat, too card-heavy, and too visually uniform.
- Setup, progress, results, and deep inspection currently look too similar.
- Empty states feel like blank placeholders rather than designed states.
- Mundane and Weather currently look too similar to each other.

Current Mundane features:
- Analysis mode with chart type, domain lens, chart source, polity or custom chart input, context overrides, event overrides, resolve context, and analyze.
- Analysis outputs include resolved context, assessment summary, score and level, framework layer, trigger layer, activation layer, domain notes, calibration, matched rules, source lists, and context notes.
- Scan mode includes async scan execution, progress metrics, returned cells or places, top candidates, inspector, breakout surfaces, and pressure-matrix style views.

Current Weather features:
- Analysis mode with weather family selection, forecast overrides, resolve context, analyze, and clear.
- Analysis outputs include resolved context, family assessment, score summary, framework layer, trigger layer, locality layer, calibration, notes, and rule sources.
- Scan mode includes scan scope selection, place or region timeline setup, async execution, progress, summary metrics, graph view, dates view, and scan inspector.

What I want from you:
- Propose 2-3 strong visual directions for these modules.
- Keep them clearly related to Astro Clock, Transits, and Elections, but do not just copy those screens.
- Make Mundane feel like a geopolitical or strategic intelligence console.
- Make Weather feel like an atmospheric or forecasting lab, while still belonging to the same family.
- Suggest a better hierarchy for:
  - pre-run state
  - running state
  - partial-result state
  - completed-result state
  - selected-result inspection state
  - empty state
  - error state
- Suggest how the center pane should become the dominant surface.
- Suggest how to reduce card sameness and overuse of pills.
- Suggest how typography, spacing, framing, chips, tabs, and action areas should evolve.
- Suggest which components should be shared between Mundane and Weather, and which should diverge.

Constraints:
- frontend only
- keep current feature coverage
- preserve dense expert workflows
- no backend assumptions
- the redesign should be implementable in an existing React/Tailwind-style codebase

Please structure your answer like this:
1. Shared design-language principles
2. Direction A
3. Direction B
4. Optional Direction C
5. Mundane-specific recommendations
6. Weather-specific recommendations
7. Shared component system recommendations
8. State-design recommendations
9. Risks or tradeoffs

Be concrete. I do not want vague moodboards only. I want actionable interface ideas, layout moves, hierarchy changes, and component patterns.
```

## Recommended Framing When Sending Screens

When sharing screenshots with the design agent, send them in this order:

1. Astro Clock, Transits, and Election reference screens
2. Astrocartography advanced-workspace screens
3. Current Mundane analysis and scan screens
4. Current Weather analysis and scan screens

This order helps the agent understand the family resemblance target before it sees the weaker current surfaces.

## Implementation Note

This memo is intentionally design-facing. It does not prescribe code changes yet. The next step after design feedback should be to convert the chosen direction into a frontend implementation plan for:

- shared workspace primitives
- mundane scan refactor
- mundane analysis refactor
- weather scan refactor
- weather analysis refactor
