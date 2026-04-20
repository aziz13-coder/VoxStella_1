# Forensic Fixes Implemented - 2026-03-05

## Scope
- Implemented approved Forensic fixes while preserving AstroClock <-> Horary integration.
- Source-only edits; no packaged/generated artifacts were modified.

## Fixes Implemented

### 1) Forensic modal pause/sync correctness
- File: `frontend/src/features/astroclock/AstroClock.jsx`
- Change:
  - `handleOpenForensic` now awaits `pauseRealtimeForFeature()` before opening the forensic modal.
- Resolution:
  - Prevents race conditions between realtime clock updates and forensic modal lifecycle.

### 2) Forensic request contract completeness
- File: `frontend/src/features/astroclock/AstroClock.jsx`
- Change:
  - `fetchForensic` converted to `useCallback` with stable dependencies.
  - Abduction request path now forwards `line_zones` and `corridor_deg`.
  - Initial fetch effect now depends on the callback reference.
- Resolution:
  - Removes stale closure risk and ensures full forensic query parameters are sent.

### 3) Frontend runtime TDZ bug in abduction brief
- File: `frontend/src/features/astroclock/AstroClock.jsx`
- Change:
  - `firstRuler` declared before first use.
- Resolution:
  - Eliminates temporal-dead-zone runtime failure path.

### 4) Backend forensic mode handling/validation
- File: `backend/astro_clock_api.py`
- Change:
  - Added normalized mode parsing/validation (`realtime`, `manual`, `paused`).
  - Invalid mode now returns HTTP 400.
  - `mode_override` now consistently applies requested mode.
  - Datetime override correctly forces manual mode.
- Resolution:
  - Aligns backend behavior with frontend contract and avoids silent mode mismatch.

### 5) Full aspect injection for forensic extraction
- File: `backend/astro_clock_api.py`
- Change:
  - Forensic route now injects `all_aspects` from chart payload when available (top-level or `chart_data`).
- Resolution:
  - Ensures forensic extraction uses complete aspect coverage.

### 6) Directional aspect alias robustness
- File: `backend/forensic/features.py`
- Change:
  - Added reverse aspect alias generation (`p2_to_p1`) when missing.
- Resolution:
  - Makes rule matching robust to serialization order/direction.

### 7) Knowledge rule path/key corrections
- File: `backend/forensic/knowledge/deception_rules.yaml`
- Change:
  - Corrected malformed Node/Neptune/Mercury key paths and quoting.
- Resolution:
  - Prevents false negatives caused by invalid rule path parsing.

## Tests Added
- File: `tests/test_forensic_features.py`
- Coverage:
  - Full-aspect usage when `all_aspects` exists.
  - Bidirectional aspect alias generation.
  - Node-related rule path resolution.

## Validation Results
- `pytest -q tests/test_forensic_features.py` -> `3 passed`
- `pytest -q tests/test_astroclock_adapter_fixes.py` -> `2 passed`
- `python -m py_compile backend/astro_clock_api.py backend/forensic/features.py` -> passed
- YAML parse sanity (`backend/forensic/knowledge/deception_rules.yaml`) -> valid, 23 rules loaded

## Integration Outcome
- AstroClock <-> Horary contracts preserved.
- Forensic mode handling, aspect ingestion, and rule matching are now deterministic and consistent.
- Non-blocking note: one dependency-level deprecation warning (`pytz`) observed during test run.
