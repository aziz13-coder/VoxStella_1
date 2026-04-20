# App Review And Fixes

Date: 2026-04-15

## Scope

This pass documented the latest application review findings and fixed the two issues requested for immediate remediation:

1. Synastry catalog cache leakage between tests
2. Electron development startup gating
3. Astrocartography model-overlap finding status

Only source files were changed:

- `backend/**`
- `frontend/**`
- `docs/**`

No packaged artifacts were edited.

## Findings Status

### 1. Synastry catalog cache leakage between tests [Resolved]

Problem:

- `backend/test_synastry_catalog_resolution.py` seeded `synastry_engine._load_catalog()` with a synthetic catalog.
- The test cleared the cache before execution but did not clear it again after the assertions completed.
- Because `_load_catalog()` is `@lru_cache(maxsize=1)`, later synastry contract tests could observe the synthetic empty catalog and fail on missing polarity and version metadata.

Fix:

- Wrapped the test body in `try/finally`.
- Added a final `synastry_engine._load_catalog.cache_clear()` so teardown always leaves the global cache empty for the next test.

Files:

- `backend/test_synastry_catalog_resolution.py`

### 2. gambling_luck still duplicates the parent money profile [Documented, still open]

Problem:

- `backend/knowledge/astrocartography/place_goal_models.runtime.json` still describes `gambling_luck` as temporarily inheriting the parent `money` scoring shape.
- The maintained astrocartography stress suite reports cosine similarity `1.0` between `money` and `gambling_luck`, which means speculative scenarios cannot separate cleanly from the generic money model.

Status:

- This finding is documented here and remains open.
- It was not changed in this pass because it requires runtime model retuning and benchmark validation, not a small mechanical fix.

Files:

- `backend/knowledge/astrocartography/place_goal_models.runtime.json`
- `backend/astrocartography_model_stress.py`

### 3. electron:dev did not actually wait for Vite [Resolved]

Problem:

- `frontend/package.json` launched Vite, `wait-on`, and Electron as sibling commands.
- Electron could start before the Vite dev server was ready, producing a timing-dependent blank window or startup failure in local development.

Fix:

- Changed `electron:dev` so Electron starts only after `wait-on http://localhost:5173` succeeds.
- Kept the commands under `concurrently` and added `-k` so the dev server is torn down when Electron exits.

Files:

- `frontend/package.json`

## Verification

Run after the fixes:

- `python -m pytest backend/test_synastry_catalog_resolution.py backend/test_synastry_engine_contract.py -q`
- `npm test` from `frontend/`

Not run:

- Manual Electron GUI startup validation in this pass
