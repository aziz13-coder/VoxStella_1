# Frontend Bundle Warning

Date: 2026-04-11

## Issue

The frontend production build currently emits Vite's large-chunk warning during `npm run build`.

Observed behavior:

- the build succeeds
- Vite reports at least one JavaScript chunk above the default warning threshold
- the warning is advisory, not a build failure

## Why It Happens

The frontend Vite config in `frontend/vite.config.js` is minimal:

- React plugin only
- relative asset base for Electron
- no custom `manualChunks`
- no raised `chunkSizeWarningLimit`

That means Vite uses its default chunking behavior and default warning threshold.

## Current Impact

For this repository, the warning is not a correctness issue:

- Electron packaging still works
- the frontend build completes successfully
- the mundane frontend integration did not introduce the warning pattern; it already existed as a class of build concern

Potential real impact is performance-oriented:

- more JavaScript to parse and evaluate at startup
- slower feature entry for heavy optional surfaces
- larger memory footprint for a single eagerly loaded bundle

## Priority

This should be treated as a tracked performance issue, not an implementation blocker.

Priority assessment:

- not urgent for correctness
- worth addressing later as a focused performance task
- higher priority only if startup or modal-open latency is measurably poor

## Safe And Unsafe Fix Directions

Low-risk conclusion for the current feature track:

- do not change bundling as part of the mundane feature slice

If addressed later, the safer path is:

1. prefer targeted lazy-loading of heavy optional workspaces
2. verify each split with build plus runtime smoke testing
3. avoid broad manual chunk rewrites unless there is a measured need

Riskier path:

- aggressive `manualChunks` changes without incremental runtime verification

That can cause:

- import timing regressions
- chunk loading mistakes
- subtle runtime breakage in optional surfaces

## Recommendation

Leave the warning unresolved for the current mundane feature track.

Revisit it only as a dedicated frontend performance pass with explicit goals:

- startup time
- advanced workspace open time
- chunk size distribution

