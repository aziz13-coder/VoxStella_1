# AstroClock Transits Audit Phase 1 Baseline
## 2026-05-01

Phase 1 has started. This document records the baseline inventory for the full Transits audit before deeper technical and algorithmic findings are written.

This phase does not mark confirmed bugs. It maps the surface area, source authority, existing coverage, and candidate review queue for Phase 2 and Phase 3.

## Phase 1 Scope

Objectives:
- confirm the primary source hierarchy
- map Transits routes and frontend workflows
- map core backend algorithm entry points
- check canonical backend source against the frontend backend mirror
- identify existing tests
- queue high-risk areas for focused review

Out of scope for Phase 1:
- final bug severity
- code changes
- external astrology comparison
- full replay/benchmark execution

External references are allowed later, but Phase 1 uses only local repo sources and local code.

## Source Hierarchy

Primary rule authority remains the local Morin material and Morin-derived repo notes.

Primary local source files:
- `horary_knowledge/desktop_books_text/631069613-Jean-Baptiste-Morin-Astrologia-Gallica-book-24.txt`
- `horary_knowledge/desktop_books_text/toaz.info-jean-baptiste-morin-astrologia-gallica-book-22-directions-1994-transl-pr_c198dcbe1e631c7e9f774ec5e70b435c.txt`
- `horary_knowledge/desktop_books_text/631070060-Jean-Baptiste-Morin-Astrologia-Gallica-book-25.txt`
- `horary_knowledge/desktop_books_text/631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt`
- `backend/morin_transit_engine_specification(1).md`
- `backend/morin_transit_quality_determination(2).md`
- `docs/ASTROCLOCK_TRANSITS_MORIN_SOURCE_SUMMARY_2026-03-28.md`

Operational Morin baseline from the local summary:
- Important events are not judged from transits alone; transits act as triggers after radix, directions, and revolutions establish the event potential.
- Radical determination is the leading quality factor; planet nature and aspect type are modifiers, not the whole judgment.
- Empty-space transits are weak or imperceptible; meaningful targets are radical planets, cusps, aspect places, Part of Fortune, and antiscions.
- Agreement or contrariety between the transiting planet and radical place matters for tone and outcome.
- Slower planets are more effective because they remain longer in place; the Moon alone is lowest in virtue.
- Ranking should preserve the strongest principal signification while still retaining secondary or mixed effects.
- House-domain labels must remain source-sensitive and not over-modernized.

Secondary external references:
- allowed from Phase 5 onward
- used only for terminology, common UX expectation, or product-positioning notes
- not allowed to override clear local Morin evidence

## Backend Route Inventory

Canonical backend source: `backend/astro_clock_api.py`.

| Feature | Route | Function | Line |
| --- | --- | --- | --- |
| Exact transit compute | `GET /api/astro-clock/transits` | `transits_compute` | `backend/astro_clock_api.py:6162` |
| Window scan | `GET /api/astro-clock/transits/window` | `transits_window` | `backend/astro_clock_api.py:6235` |
| Predictor | `GET /api/astro-clock/predictor` | `transits_predictor` | `backend/astro_clock_api.py:6387` |
| Streaming window scan | `GET /api/astro-clock/transits/window/stream` | `transits_window_stream` | `backend/astro_clock_api.py:6537` |
| Exact CSV export | `GET /api/astro-clock/transits/export` | `transits_export_csv` | `backend/astro_clock_api.py:6794` |
| Window CSV export | `GET /api/astro-clock/transits/window/export` | `transits_window_export_csv` | `backend/astro_clock_api.py:6879` |

Shared backend helpers already identified:
- `_validate_transit_scan_bounds`: `backend/astro_clock_api.py:183`
- `_validate_transit_scan_request_bounds`: `backend/astro_clock_api.py:219`
- `_select_dominant_occurrence`: `backend/astro_clock_api.py:1325`
- `_predictions_from_hits`: `backend/astro_clock_api.py:1699`
- `_retry_enrich_transit_hits`: `backend/astro_clock_api.py:1706`
- `_compute_pd_windows_for_years`: `backend/astro_clock_api.py:1808`
- `_natal_from_query`: `backend/astro_clock_api.py:4537`

## Frontend API Inventory

Frontend source: `frontend/src/features/astroclock/api.mjs`.

| Feature | API wrapper | Line |
| --- | --- | --- |
| Exact transit compute | `AstroClockAPI.getTransits` | `frontend/src/features/astroclock/api.mjs:448` |
| Window scan | `AstroClockAPI.getTransitsWindow` | `frontend/src/features/astroclock/api.mjs:472` |
| Streaming window scan | `AstroClockAPI.createTransitsWindowStream` | `frontend/src/features/astroclock/api.mjs:506` |
| Predictor | `AstroClockAPI.getPredictions` | `frontend/src/features/astroclock/api.mjs:543` |
| Exact CSV export query | `buildTransitsExportQuery` | `frontend/src/features/astroclock/api.mjs:358` |
| Window CSV export query | `buildTransitsWindowExportQuery` | `frontend/src/features/astroclock/api.mjs:382` |
| Exact CSV export | `AstroClockAPI.exportTransits` | `frontend/src/features/astroclock/api.mjs:581` |
| Window CSV export | `AstroClockAPI.exportTransitsWindow` | `frontend/src/features/astroclock/api.mjs:588` |

## Frontend Workflow Inventory

Primary modal source: `frontend/src/features/astroclock/TransitsModal.jsx`.

| Workflow area | Handler/helper | Line |
| --- | --- | --- |
| Local date/time to instant conversion | `buildIso` | `frontend/src/features/astroclock/TransitsModal.jsx:1261` |
| Exact compute | `handleCompute` | `frontend/src/features/astroclock/TransitsModal.jsx:1335` |
| Compute exact button | `handleComputeExactTime` | `frontend/src/features/astroclock/TransitsModal.jsx:1402` |
| Window scan | `doScan` | `frontend/src/features/astroclock/TransitsModal.jsx:1412` |
| Predictor | `runPredictor` | `frontend/src/features/astroclock/TransitsModal.jsx:1608` |
| Timeline/peak replay | `onTimelineClick` | `frontend/src/features/astroclock/TransitsModal.jsx:2211` |
| Exact export | `handleDownloadSingle` | `frontend/src/features/astroclock/TransitsModal.jsx:2257` |
| Window export | `handleDownloadWindow` | `frontend/src/features/astroclock/TransitsModal.jsx:2300` |
| Context-window intersection | `handleUseIntersectionRange` | `frontend/src/features/astroclock/TransitsModal.jsx:2401` |

## Backend Algorithm Inventory

Canonical algorithm source: `backend/transits_morin.py`.

| Algorithm area | Function | Line |
| --- | --- | --- |
| Primitive quality classifier | `_classify_quality` | `backend/transits_morin.py:160` |
| Hit scoring | `_score_hit` | `backend/transits_morin.py:1124` |
| Window scan core | `scan_morin_transits_window` | `backend/transits_morin.py:1372` |
| Exact transit core | `compute_morin_transits_to_natal` | `backend/transits_morin.py:1570` |
| Concordance/context enrichment | `enrich_hits_with_concordance` | `backend/transits_morin.py:2441` |
| Natal context preparation | `_prepare_natal_context` | `backend/transits_morin.py:5999` |
| Context-backed compute helper | `_compute_hits_with_ctx` | `backend/transits_morin.py:6212` |

Phase 2 and Phase 4 need to determine whether these layers are semantically aligned:
- exact compute versus scan
- scan versus stream
- predictor versus scan
- primitive quality versus enriched Morin quality
- score ordering versus principal-signification ordering

## Source Mirror Parity

Checked by SHA-256 hash during Phase 1. These canonical backend files currently match their `frontend/backend` mirrors:

| Canonical source | Mirror | Phase 1 parity |
| --- | --- | --- |
| `backend/transits_morin.py` | `frontend/backend/transits_morin.py` | matched |
| `backend/astro_clock_api.py` | `frontend/backend/astro_clock_api.py` | matched |
| `backend/morin_aspects.py` | `frontend/backend/morin_aspects.py` | matched |
| `backend/pd_morin.py` | `frontend/backend/pd_morin.py` | matched |
| `backend/knowledge/morin_keywords.json` | `frontend/backend/knowledge/morin_keywords.json` | matched |
| `backend/test_astro_clock_api_transits.py` | `frontend/backend/test_astro_clock_api_transits.py` | matched |
| `backend/test_transits_quality.py` | `frontend/backend/test_transits_quality.py` | matched |

Generated/runtime artifacts remain out of scope for edits.

## Existing Test Inventory

Backend route and helper tests:
- `backend/test_astro_clock_api_transits.py`
  - context auto maturity
  - prediction sorting for crisis angle testimony
  - dominant occurrence midpoint selection
  - oversized scan rejection before scanning

Backend quality/source tests:
- `backend/test_transits_quality.py`
  - Morin doctorate/honors example
  - near-drowning malefic example
  - unmatched determination strength
  - prediction object persistence and event tokens
  - life-area-aware event selection
  - hidden crisis and legal support boundaries
  - weak concordance wording
  - relationship, wealth, travel, spiritual, study/publication, and house-domain wording

Frontend modal tests:
- `frontend/src/tests/transitsModalReplay.test.jsx`
  - modal seeding from active chart context
  - saved snap matching
  - timeline rendering and replay
  - chart-timezone replay for clicked timeline rows
  - exact request defaults
  - predictor step behavior
  - merged predictor windows with supporting transits
  - replay slices for public honor, crisis, war, marriage, and source-sensitive labels

Frontend API serialization tests:
- `frontend/src/tests/astroclockApi.test.mjs`
  - dead transit-window metadata suppression
  - single-transit request serialization
  - stream ticket path serialization
  - no-token stream fallback behavior
  - predictor request serialization with observer context and context windows
  - exact and window CSV export serialization

## Candidate Review Queue

These are not confirmed findings yet. They are the first items to verify in the next phases.

1. Stream versus non-stream parity.
   - `transits_window` delegates to `scan_morin_transits_window`.
   - `transits_window_stream` prepares context and emits rows manually through per-step exact computes.
   - Phase 2 should compare identical requests across both paths and verify series rows, peaks, prediction cards, context filtering, and truncation behavior.

2. Context-window timezone handling in frontend helper paths.
   - Several context-window fill/intersection helpers use `new Date(...)` plus browser-local `getFullYear()` and `getHours()` formatting.
   - Phase 3 should verify whether these fields are intended to be browser-local, chart-local, or source-window-local.
   - Initial locations: `frontend/src/features/astroclock/TransitsModal.jsx:1753`, `:1795`, `:1820`, `:1848`, `:2401`.

3. Exact compute frontend ranking versus backend ordering.
   - `handleCompute` re-sorts returned rows in the modal after backend response.
   - Phase 3 and Phase 4 should verify whether the frontend sort can change the backend's principal Morin signal.
   - Initial location: `frontend/src/features/astroclock/TransitsModal.jsx:1383`.

4. Export payload parity with visible filters.
   - API builders support `transiting`, `natal`, and `aspect` filters for exports.
   - Modal export handlers currently need review to confirm whether every visible filter used for scan/exact results is also sent to export.
   - Initial locations: `frontend/src/features/astroclock/api.mjs:358`, `frontend/src/features/astroclock/api.mjs:382`, `frontend/src/features/astroclock/TransitsModal.jsx:2257`, `frontend/src/features/astroclock/TransitsModal.jsx:2300`.

5. Primitive quality label versus Morin-enriched quality.
   - `_classify_quality` is explicitly simplified by planet nature and aspect family.
   - Phase 4 should verify whether any user-facing quality still comes from this simplified layer after enrichment, and whether that conflicts with the Morin determination-led model.
   - Initial location: `backend/transits_morin.py:160`.

6. Context/concordance effect boundary.
   - Routes pass PD windows and optional context windows into scan/predictor/export flows.
   - Phase 2 and Phase 4 should verify that context increases or tempers confidence without manufacturing unsupported event claims.
   - Initial locations: `backend/astro_clock_api.py:1808`, `backend/transits_morin.py:2441`.

## Phase 1 Status

Phase 1 baseline is complete.

Subsequent phases are completed in:
- `docs/ASTROCLOCK_TRANSITS_FULL_AUDIT_REPORT_2026-05-01.md`

Known tooling note:
- `rg.exe` is blocked by local permissions in this workspace, so Phase 1 used PowerShell `Select-String`, `Get-ChildItem`, and file hashes instead.

No tests were run in Phase 1 because this pass was inventory and documentation only.
