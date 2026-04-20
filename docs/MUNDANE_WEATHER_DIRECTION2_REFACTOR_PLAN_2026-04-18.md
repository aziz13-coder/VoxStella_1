# Mundane + Weather Direction 2 Refactor Plan

Date: 2026-04-18

## Decision

Direction 2 from the design package in [astrocarto.zip](C:/Users/sabaa/Downloads/astrocarto.zip) is now the target.

This supersedes the earlier recommendation in [MUNDANE_WEATHER_IMPLEMENTATION_PLAN_2026-04-18.md](C:/Users/sabaa/Downloads/codexhorary/docs/MUNDANE_WEATHER_IMPLEMENTATION_PLAN_2026-04-18.md), which favored Direction A as the primary path.

Direction 2 is the tighter console shell:

- bracketed monospace eyebrows
- denser top chrome
- command band replacing the setup summary rail after run start
- KPI strip instead of rounded metric cards
- tabular-first center pane
- thinner dividers and fewer boxed sections

## Current Gap

The current frontend has moved slightly toward the research-shell language, but it is still materially closer to Direction A than Direction 2.

The biggest mismatches are:

- the pages still rely on large rounded cards for all three columns
- the center pane still opens with headline blocks instead of a compact operator-console header
- setup remains a persistent left rail in places where Direction 2 collapses it into a command band
- KPI state is still rendered as separate blocks instead of one strip
- scan results are still mixed card/table hybrids instead of a single dense ranked table
- inspector rails still read like stacked cards instead of thin data rows and footnote surfaces
- Astrocartography still behaves like a modal with appended controls instead of a first-class console shell

## Direction 2 Principles

Direction 2 is not a skin pass. It requires layout refactoring.

The shell should behave like this:

1. Idle state:
   Left setup rail is visible.
   Center pane is mostly pre-run guidance.
   Right rail is light and contextual.

2. Running or loaded state:
   Left setup rail collapses away.
   Setup choices move into a single command band above the workspace body.
   KPI state becomes one horizontal strip.
   The center pane becomes the dominant artifact.
   The right rail becomes a compact inspector, not a second dashboard.

## Files That Need Refactor

### Shared shell

Primary file:

- [researchWorkspacePrimitives.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/researchWorkspacePrimitives.jsx)

This file currently gives us a partial shared layer, but it is still built around Direction A style surfaces.

It needs a Direction 2 pass with new primitives:

- `WorkspaceChromeConsole`
- `BracketEyebrow`
- `ConsoleModeTabs`
- `CommandBand`
- `KpiStrip`
- `SectionBar`
- `InspectorDataRow`
- `ConsoleTable`
- `ConsoleEmptyState`
- `ConsoleStatusBadge`

The current shared classes such as `railCardCls`, `sectionCardCls`, `nestedCardCls`, and `headerBandCls` should stop being the dominant layout grammar. Direction 2 should use flatter surfaces, line separators, and a much smaller number of rounded containers.

### Mundane scan

Primary file:

- [MundaneScanWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneScanWorkspace.jsx)

This is the largest delta against Direction 2.

Required refactors:

- replace the current large workspace headline block with a compact execution header
- make the left setup rail visible only in idle state
- collapse run configuration into a command band after scan start
- replace the current execution metric block with a single KPI strip
- replace the current `ScanResultsPanel` presentation with a dense ranked table
- move labels such as place, level, score, raw, and lead into one fixed table header
- keep selected-row state inline with a left rule or background tint instead of a separate card treatment
- reduce the right rail to scan scope, selected cell, doctrine anchors, and compact facts

Direction 2’s target outcome for Mundane Scan is:

- center pane reads like a ranked operator console
- right rail reads like a case inspector
- left rail disappears once the scan is underway

### Weather scan

Primary file:

- [WeatherWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/WeatherWorkspace.jsx)

The current Weather scan shell is still too card-heavy and too close to the existing app UI.

Required refactors:

- collapse setup into a command band after run start
- replace the current execution block with a KPI strip
- remove the large center headline band and replace it with a compact execution header
- keep the center artifact graph-first, but frame it in the same console shell as Mundane
- make the pressure matrix or timing surface feel like one editorial artifact, not multiple cards
- reduce the inspector to compact intensity rows, family counts, and focused peak details

Direction 2’s target outcome for Weather Scan is:

- same shell as Mundane Scan
- different center artifact
- weather-specific teal accent and lab-style inspector

### Mundane analysis

Primary file:

- [MundaneWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneWorkspace.jsx)

This file already uses some shared primitives, but the analysis body is still section-card driven.

Required refactors:

- flatten the current analysis layout into a console report
- promote the verdict and calibration summary into a compact top block
- convert signal chips and grouped cards into thin data rows
- make framework, triggers, and activation sections feel like labeled dossier chapters separated by rules, not boxes
- move sources and doctrine into a footnote-like inspector rail

Direction 2’s target outcome for Mundane Analysis is:

- strategic console
- denser textual hierarchy
- evidence and source trail in the right rail

### Weather analysis

Primary file:

- [WeatherWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/WeatherWorkspace.jsx)

The current analysis mode is still the furthest from Direction 2.

Required refactors:

- remove the large left-rail setup card stack and use the same console setup language as the scan mode
- flatten the center pane into one atmospheric report surface
- convert assessment metrics into a KPI strip or narrow metrics row
- reduce layer panels into console sections
- move calibration and doctrine into thinner inspector data rows
- make the right rail feel like a forecasting notebook rather than a dashboard

Direction 2’s target outcome for Weather Analysis is:

- compact lab notebook shell
- framework, trigger, and locality sections in one readable center flow
- right rail as instrumentation and references

## Astrocartography Alignment

Primary file:

- [AstrocartographyModal.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstrocartographyModal.jsx)

There is no direct Astrocartography sketch in the package, so this needs to be derived from Direction 2 principles rather than copied.

The Astrocartography refactor should not attempt to redesign the map logic. It should refactor the shell around the existing features.

Required shell refactors:

- replace the current hero-like top block with Direction 2 console chrome
- tighten the mode switcher into the same top strip language as Mundane and Weather
- convert the current extra control row into a command band once a snap is active
- move snap, view mode, body filters, and map state into the command band or compact top controls
- restyle the workspace tabs as console tabs, not rounded pills
- convert workspace section headers to bracketed eyebrows plus line rules
- flatten the left and right rail containers so the map center feels dominant

Required behavioral alignment:

- preflight snap selection can stay, but once a snap is chosen the workspace should enter the same console shell as the other modules
- map, intersections, local-space, and report should each feel like one artifact under the shared shell
- atlas ranking should use the same table-first language that Direction 2 gives to Mundane Scan

Astrocartography should become the parent visual language for the three advanced workspaces, not a separate modal styling system.

## Refactor Order

1. Rework [researchWorkspacePrimitives.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/researchWorkspacePrimitives.jsx) for Direction 2 primitives.
2. Refactor [MundaneScanWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneScanWorkspace.jsx) into the Direction 2 shell.
3. Refactor Weather scan mode in [WeatherWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/WeatherWorkspace.jsx).
4. Refactor Mundane analysis in [MundaneWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneWorkspace.jsx).
5. Refactor Weather analysis in [WeatherWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/WeatherWorkspace.jsx).
6. Do a dedicated Astrocartography shell pass in [AstrocartographyModal.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstrocartographyModal.jsx) once the shared console primitives are stable.

## What Is Styling Only vs Structural

Styling only:

- typography swap
- accent color adjustments
- border radius reductions
- button polish
- eyebrow label style

Structural refactor:

- left-rail collapse behavior
- command band introduction
- KPI strip replacement
- result-table rewrite
- inspector rail rewrite
- Astrocartography control consolidation

The current implementation is blocked mainly by the structural items, not the styling ones.

## Immediate Next Step

Do not keep iterating inside the current card grammar.

The next concrete implementation step should be:

- replace the current shared workspace surface model in [researchWorkspacePrimitives.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/researchWorkspacePrimitives.jsx) with Direction 2 console primitives, then refactor [MundaneScanWorkspace.jsx](C:/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/MundaneScanWorkspace.jsx) as the first full consumer

That file is the clearest baseline for proving the new shell before the same structure is applied to Weather and Astrocartography.
