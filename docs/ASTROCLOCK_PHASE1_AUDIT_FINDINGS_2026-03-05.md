# AstroClock Phase 1 Audit Findings (Analysis Only)

Date: 2026-03-05  
Workspace: `C:\Users\sabaa\Downloads\codexhorary`  
Scope: AstroClock logic correctness vs project knowledge texts, with AstroClock↔Horary integration preserved.

## 1. Findings (ordered by severity)

### 1) Critical - Datetime semantics are inconsistent (absolute instant vs local wall-time), causing silent chart-time shifts
- Severity: Critical
- File + line reference:
  - `frontend/src/features/astroclock/TransitsModal.jsx:574-601`
  - `frontend/src/features/astroclock/AstroClock.jsx:422-423`
  - `backend/astro_clock_api.py:996-1005`
  - `backend/astro_clock_api.py:1291-1313`
  - `backend/astro_clock_engine.py:183-204`
  - `backend/horary_engine/services/geolocation.py:242-331`
- Current behavior:
  - Frontend helpers build ISO instants (often UTC, e.g. `...Z`) from local date/time.
  - Backend stores that parsed datetime (`fromisoformat`), then AstroClock passes only `date` + `time` strings and a separate timezone to Horary.
  - Horary re-localizes those strings as local wall-time (`parse_datetime_with_timezone`), which can re-apply timezone offset and shift the intended instant.
  - Same pattern exists in scoped/stateless chart derivation (`_compute_chart_for`) used by transits/predictor/context/election/research.
- Why it is incorrect (knowledge text citation):
  - `extracted_text_docs/631069613-Jean-Baptiste-Morin-Astrologia-Gallica-book-24.txt:1243-1245` states transit effects timing should be measured by the transiting planet’s own motion; shifted timestamps violate that requirement.
  - `extracted_text_docs/631069613-Jean-Baptiste-Morin-Astrologia-Gallica-book-24.txt:1150-1168` stresses concordant transits as actual causes; mis-timed inputs break concordance logic.
- Risk to AstroClock↔Horary connection:
  - High risk of disagreement between AstroClock mode timestamp, Horary-evaluated chart, transits, predictor peaks, and election jumps.
  - Any downstream scoring that depends on exact timing can drift while still appearing successful.

### 2) High - Scoped/stateless computations leak global engine settings into dashboard payload fields
- Severity: High
- File + line reference:
  - `backend/astro_clock_api.py:633-634`
  - `backend/astro_clock_api.py:749`
  - `backend/astro_clock_api.py:2613-2632`
- Current behavior:
  - For override/scoped calculations (e.g., forensic ad-hoc chart), data is computed from local settings, but `_build_dashboard_payload` still reads location/timezone from `eng.settings` for payload and cusp-aspect context.
- Why it is incorrect (knowledge text citation):
  - `docs/HORARY_ASTROCLOCK_ENGINE_WORKFLOW.md:118-121` defines scoped/stateless path as temporary `AstroClockSettings` without permanent singleton dependence.
  - Using singleton settings during payload assembly violates that stateless contract.
- Risk to AstroClock↔Horary connection:
  - Output can contain mixed context (chart from override, metadata from singleton), making AstroClock appear inconsistent with Horary source state.

### 3) Medium - Export endpoints diverge from compute endpoints for concordance context
- Severity: Medium
- File + line reference:
  - `backend/astro_clock_api.py:1524-1528`
  - `backend/astro_clock_api.py:2230-2233`
  - `backend/astro_clock_api.py:1677`
  - `backend/astro_clock_api.py:2336-2350`
- Current behavior:
  - `/transits` computes natal timestamp fallback from `natal_meta` for PD windows; `/transits/export` does not use that fallback.
  - `/transits/window` passes `pd_windows` into scan scoring; `/transits/window/export` omits `pd_windows` in its scan call.
- Why it is incorrect (knowledge text citation):
  - `extracted_text_docs/631069613-Jean-Baptiste-Morin-Astrologia-Gallica-book-24.txt:1150-1168` and `:1623-1637` emphasize that transits should be judged with concordant context, not as isolated triggers.
  - `extracted_text_docs/631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt:2148-2154` requires natal + directions/revolutions/transits concordance for electional validity.
- Risk to AstroClock↔Horary connection:
  - On-screen results and exported CSV can disagree for the same user query, reducing trust in AstroClock analyses that depend on Horary-derived context.

### 4) Medium - Moon VoC timeline helper suppresses inferred VoC in a contradictory branch
- Severity: Medium
- File + line reference:
  - `backend/moon_voc_timeline.py:69-71`
- Current behavior:
  - If `in_voc` is false but no next aspect exists before sign exit, helper leaves VoC timing null instead of inferring immediate VoC.
- Why it is incorrect (knowledge text citation):
  - `extracted_text_docs/pdfcoffee.com_jean-baptiste-morin-astrologia-gallica-book-16-pdf-free.txt:4306-4309` defines void-of-course as separating and not applying to another planet.
  - The branch explicitly identifies “no next aspect within sign” but suppresses the implication.
- Risk to AstroClock↔Horary connection:
  - Moon/timing/election guidance can understate void periods despite Horary moon-aspect semantics.

### 5) Low - Snap payload contract mismatch for `special_degrees`
- Severity: Low
- File + line reference:
  - `frontend/src/features/astroclock/api.mjs:422-424`
  - `frontend/src/features/astroclock/AstroClock.jsx:668-683`
  - `backend/astro_clock_api.py:903-951`
- Current behavior:
  - Frontend sends `special_degrees` in snap creation and attempts to restore them on snap load.
  - Backend snap creation does not persist `special_degrees` in snap record.
- Why it is incorrect (knowledge text citation):
  - `docs/HORARY_ASTROCLOCK_ENGINE_WORKFLOW.md:97-109` defines AstroClock API enrichment as the stable UI-facing contract layer.
  - Current snap behavior breaks expected round-trip contract for an AstroClock-specific enrichment input.
- Risk to AstroClock↔Horary connection:
  - Reloaded snaps can compute different metrics context than original chart session, causing apparent analytical drift.

### 6) Low - Horary audit path assumes `chart_data.planets` is dict-only
- Severity: Low
- File + line reference:
  - `backend/horary_engine/engine.py:7603`
  - `docs/HORARY_ASTROCLOCK_ENGINE_WORKFLOW.md:154`
- Current behavior:
  - Audit chart constructor iterates `chart_data.get('planets', {}).items()` directly.
  - If `planets` shape changes to list (supported elsewhere in AstroClock normalization), this path can fail.
- Why it is incorrect (knowledge text citation):
  - Workflow checklist explicitly notes planets may vary (`dict vs list`) and must be normalized safely.
- Risk to AstroClock↔Horary connection:
  - Future serializer changes could break Horary judge post-processing used by AstroClock without obvious compile-time signal.

---

## 2. Proposed fixes (no code yet)

### Minimal safe change strategy
1. Establish one canonical datetime policy across AstroClock endpoints:
   - If payload datetime includes offset/`Z`, treat as absolute instant and never reinterpret as a different wall-time.
   - If payload datetime is naive, treat as wall-time in explicit timezone (or location-derived timezone).
2. In AstroClock→Horary adapter (`_generate_chart_with_horary_engine`), derive `date/time` in the same timezone being passed to Horary.
3. Update scoped chart helper (`_compute_chart_for`) to preserve instant semantics identically to `/mode` path.
4. Make `_build_dashboard_payload` consume effective settings (from `data.settings`/local context) instead of singleton fields when provided.
5. Align export endpoints with compute endpoints:
   - same natal timestamp fallback logic,
   - same PD window inclusion logic in window scans.
6. In Moon timeline helper, when no next aspect exists before sign exit, return inferred immediate VoC timeline (with explicit provenance flag).
7. Persist `special_degrees` in snap objects and include in list/get responses.
8. Harden Horary audit planet normalization (`dict` or `list`).

### Backward-compatibility notes
- Keep existing request parameters and endpoint URLs unchanged.
- Add only optional response fields where needed (e.g., inferred VoC provenance), do not remove existing keys.
- Preserve CSV column schemas for exports.
- Maintain AstroClock forced Horary override behavior (`ignore_radicality`, `ignore_void_moon`, etc.) per workflow contract.

---

## 3. Validation plan

### API checks (exact)
1. `POST /api/astro-clock/mode` with `datetime` containing offset and `timezone`; verify resulting `/dashboard` timestamp aligns to intended instant (no offset double-application).
2. `POST /api/astro-clock/mode` with naive `datetime` + `location` only; verify timezone derivation and stable chart time.
3. For same natal/transit inputs, compare `/transits` vs `/transits/export` top-hit ordering and determination fields.
4. For same window inputs, compare `/transits/window` vs `/transits/window/export` per-timestamp top entries.
5. `GET /forensic` with override `datetime/location/timezone`; verify returned `location/timezone_label` correspond to override context.
6. `POST /snap` with `special_degrees`, then `GET /snaps/<id>`; verify full round-trip of `special_degrees`.
7. Moon VoC fixture where no next aspect exists before sign exit; verify timeline returns immediate VoC inference.

### UI checks (exact)
1. From Transits modal, click “Use” on a candidate timestamp; verify AstroClock manual clock and backend chart reflect same instant.
2. From Election modal, “Jump” to selected candidate; verify no local-time shift after chart refresh.
3. Save snap with non-empty special degrees, reload snap, confirm metrics tile and filters restore exactly.
4. Run forensic with explicit override and ensure header/location/timezone are internally consistent.

### Integration criteria (AstroClock↔Horary intact)
- `HoraryEngine.judge` still receives required settings keys from AstroClock adapter.
- `chart_data` fields required by AstroClock (`planets/aspects/houses/house_rulers/timezone_info`) remain present.
- Planet shape normalization (`dict/list`) works in both AstroClock API enrichment and Horary audit path.
- Realtime/manual/paused mode transitions still produce deterministic chart snapshots.

---

## 4. Implementation plan (patch order + rollback points)

1. Add/adjust tests for datetime semantics and export parity first.
   - Rollback point: revert test additions if baseline is unstable.
2. Patch datetime canonicalization in backend (`/mode`, `_compute_chart_for`, AstroClock adapter).
   - Rollback point: revert backend datetime patch only.
3. Patch `_build_dashboard_payload` to use effective settings context.
   - Rollback point: revert payload-context patch.
4. Patch export endpoint parity (`/transits/export`, `/transits/window/export`).
   - Rollback point: revert export parity patch.
5. Patch Moon VoC timeline inference branch.
   - Rollback point: revert Moon timeline patch.
6. Patch snap `special_degrees` persistence and retrieval.
   - Rollback point: revert snap persistence patch.
7. Patch Horary audit planets normalization hardening.
   - Rollback point: revert audit-normalization patch.
8. Run full validation plan and compare before/after API/UI artifacts.
   - Rollback point: if regression appears, revert last patch and re-run focused tests to isolate.

No implementation was performed in this phase; this document is analysis and proposed remediation only.
