# Local-First Logic Hardening Plan

Date: 2026-04-14

## Scope

This memo defines a local-first hardening plan for reducing reverse-engineering and tampering risk without moving core product logic to remote execution.

This is a planning document only.

No implementation is included in this pass.

## Product Constraints

The plan assumes the following product constraints remain true:

- The app must remain usable as a local-first desktop product.
- Core premium model execution should remain local.
- Astro Clock's intentionally public routes remain public by product decision.
- Premium remains a binary licensed versus unlicensed model unless product policy changes later.
- Periodic server contact remains acceptable for license activation, refresh, and revocation, but not as the primary execution path for core models.

## Problem Statement

If valuable logic executes locally, a determined attacker can eventually inspect or patch it.

The realistic goal is not perfect prevention. The realistic goal is:

- reduce how much sensitive logic is exposed to the easiest attack surface
- reduce how much value a successful extraction yields
- make patching and reuse materially harder
- preserve legitimate offline-capable use for paying users

## Threat Model

This plan is aimed at raising cost against these practical attacker behaviors:

1. Renderer inspection
   - extracting logic from `frontend/src/**`
   - patching premium UI branches
   - replaying privileged frontend requests

2. Local token replay
   - copying local token state to another device
   - reusing renderer-visible credentials

3. Packaged-code inspection
   - unpacking Electron and PyInstaller artifacts
   - reading JS/Python source-equivalent logic
   - extracting editable JSON rule bundles

4. Runtime patching
   - monkey-patching backend Python code
   - patching Electron main process logic
   - bypassing local feature checks

This plan does not assume resistance against a fully privileged adversary forever. It is meant to improve practical resilience, not provide cryptographic impossibility.

## Hardening Principles

### 1. Keep the renderer weak

The renderer should remain the easiest layer to inspect and the least valuable layer to attack.

Target state:

- `frontend/src/**` handles UI, display formatting, workflow state, and request shaping
- `frontend/src/**` does not hold durable entitlement truth
- `frontend/src/**` does not hold the highest-value proprietary scoring logic
- `frontend/src/**` does not hold editable premium-gate source of truth

### 2. Split trust boundaries locally

The local product should not behave as one flat blob of trust.

Target state:

- Electron renderer: low-trust UI surface
- Electron main: local privilege boundary for license, session, and integrity control
- local backend: ordinary local computation and protected route enforcement
- optional compiled local module: highest-value proprietary scoring or premium decision slice

### 3. Prefer signatures over secrecy for local assets

If local rule/config bundles remain editable plaintext, attackers get the easiest path to altering logic.

Target state:

- signed rule bundles or signed premium policy bundles
- local verification before load
- fail-closed or degrade-on-tamper behavior

### 4. Compile only the most valuable logic slice

Do not attempt to compile the entire application.

That would add cost and fragility without proportional value.

Target state:

- only the most commercially sensitive scoring or premium rule path is compiled or otherwise raised above plain JS/plain Python readability

### 5. Make tampering detectable before making it punitive

The system should first become capable of identifying tampered runtime conditions consistently.

Target state:

- startup integrity checks
- runtime spot checks for critical bundles
- controlled downgrade paths instead of unpredictable breakage

## Current-State Mapping

### Renderer

Current role should remain:

- UI
- scan/analysis state
- display formatting
- local workflow orchestration

Current risk:

- easiest layer to inspect
- easiest layer to patch cosmetically
- should not carry valuable long-lived secret material or authoritative premium logic

### Electron Main

Current role should become the primary local trust coordinator for:

- stored license state
- local session minting
- device binding
- integrity orchestration
- tamper signal aggregation

### Local Backend

Current role should remain:

- protected route enforcement
- local feature execution
- scan/model execution
- rule loading and model orchestration

But this layer should not remain fully transparent where the commercial core would be materially harmed by easy source extraction.

## Phase Plan

## Phase A: Boundary Cleanup

Goal:

Reduce the amount of valuable logic and trust living in the renderer.

Planned outcomes:

- inventory premium and proprietary logic currently reachable from `frontend/src/**`
- confirm those paths are UI-only or request-shaping only
- move any remaining authoritative premium checks into Electron main or backend
- ensure frontend state cannot become the effective source of entitlement truth

Repo focus:

- `frontend/src/**`
- `frontend/preload.js`
- `frontend/main/**`

Acceptance criteria:

- renderer cannot unlock premium execution by local state manipulation alone
- renderer-visible artifacts are session-scoped and low-value
- premium decisions are enforced outside the renderer

## Phase B: Signed Local Policy Bundles

Goal:

Reduce the value of editing local config or rule files directly.

Planned outcomes:

- identify premium-sensitive and commercially sensitive JSON or rule bundles
- define a signed bundle format
- verify signatures before loading those bundles
- decide tamper response for invalid signatures

Candidate targets:

- premium policy bundles
- high-value model rule bundles
- proprietary ranking/scoring parameter bundles

Acceptance criteria:

- direct bundle edits do not silently alter premium-sensitive behavior
- unsigned or modified bundles are detected reliably

## Phase C: Compile the Highest-Value Logic Slice

Goal:

Raise the extraction cost for the most commercially valuable local logic while keeping the app local-first.

Planned outcomes:

- identify one narrow high-value slice, not the whole app
- move that slice into a compiled boundary
- keep the compiled slice small and stable

Candidate shapes:

- Python -> Cython/Nuitka for one scoring/policy module
- native addon or Rust/C++ bridge for one premium-sensitive logic path

Non-goal:

- do not compile all frontend logic
- do not compile every backend module

Acceptance criteria:

- the highest-value proprietary path is no longer readable as plain source in the easiest runtime layer
- build and release complexity stays manageable

## Phase D: Integrity Verification

Goal:

Detect altered premium-critical local code and assets.

Planned outcomes:

- define a manifest of integrity-protected assets
- verify hashes/signatures at startup
- perform periodic spot checks for long-running sessions
- centralize integrity status in Electron main

Candidate protected assets:

- premium gate policy bundles
- compiled premium-sensitive modules
- critical backend modules
- critical Electron main modules

Acceptance criteria:

- mutation of a protected asset is detectable before premium execution proceeds
- integrity status can be surfaced or acted on consistently

## Phase E: Controlled Tamper Response

Goal:

Handle suspicious runtime conditions predictably instead of letting patched environments continue silently.

Planned outcomes:

- define response levels:
  - log only
  - require revalidation
  - disable premium execution
  - degrade to public/free mode
- tie those responses to tamper classes

Important guardrail:

- do not create brittle false-positive behavior that locks out legitimate users casually

Acceptance criteria:

- tamper response is explicit and testable
- legitimate users on unchanged builds are not disrupted

## Phase F: Packaging And Release Hardening

Goal:

Reduce the ease of extracting or patching premium-critical local artifacts from packaged builds.

Planned outcomes:

- package integrity-protected assets in a way that matches the verification design
- add per-build metadata and optional watermarking for forensic differentiation
- ensure packaging does not reintroduce plaintext sensitive bundles unexpectedly

Acceptance criteria:

- packaged outputs preserve integrity guarantees
- release workflow can verify that protected assets are in the expected form

## Phase G: Test And Rollout Discipline

Goal:

Avoid shipping hardening changes that lock out real users or create opaque failures.

Planned outcomes:

- add tests for same-device continuity after update
- add tests for copied-token or copied-install rejection
- add tests for signed-bundle tamper rejection
- add tests for renderer session continuity
- add tests for offline-capable perpetual behavior and subscription grace behavior

Acceptance criteria:

- legitimate licensed users on the same device retain continuity
- copied-state reuse is rejected
- hardening failures are diagnosable

## Repo-Specific Target Allocation

### `frontend/src/**`

Should contain:

- UI
- display logic
- workflow state
- export formatting
- local convenience helpers

Should not become the source of truth for:

- entitlement
- premium unlock policy
- proprietary scoring authority
- long-lived tokens

### `frontend/main/**`

Should own:

- stored license state
- local session token minting
- device and install identity
- integrity orchestration
- tamper classification

### `backend/**`

Should own:

- premium route enforcement
- protected model execution
- signed-bundle verification
- execution-time premium-sensitive policy checks

### New future boundary: compiled premium-sensitive module

Should contain only:

- the narrowest commercially valuable logic slice worth raising above plain-source readability

It should not become a dumping ground for unrelated logic.

## Trade-Offs

This plan preserves local execution, but it introduces real costs:

1. Build complexity
   - signing, manifests, compiled slices, and integrity verification add release work

2. Debugging complexity
   - failures become harder to inspect when part of the path is compiled or integrity-protected

3. Support complexity
   - false tamper signals can create real user friction if response rules are too aggressive

4. Cross-platform burden
   - compiled slices and native boundaries may increase Windows/macOS support cost

5. Imperfect ceiling
   - local hardening raises attack cost but does not make the product uncrackable

## Non-Goals

This plan does not aim to:

- make local code impossible to reverse engineer
- convert the app into an online-only service
- change Astro Clock's intentionally public status
- introduce route-level paid plan segmentation yet
- implement anti-debug theater with no measurable security value

## Recommended Execution Order

The order matters.

1. Phase A: boundary cleanup
2. Phase B: signed local policy bundles
3. Phase D: integrity verification
4. Phase E: controlled tamper response
5. Phase C: compile the highest-value logic slice
6. Phase F: packaging and release hardening
7. Phase G: test and rollout discipline

Reason:

- the product first needs clear local trust boundaries
- then signed assets and integrity policy
- only after that is it worth introducing compiled complexity

## Success Criteria

This plan should be considered successful only if all of the following become true:

1. The renderer is no longer a meaningful source of premium truth.
2. Direct editing of premium-sensitive local bundles is detectable.
3. A copied install or copied token state is materially less useful.
4. The highest-value logic slice is no longer exposed in the easiest plain-source layer.
5. Legitimate same-device licensed users keep working through updates with minimal friction.
6. The app remains local-first and operationally usable offline where product policy expects that.

## Immediate Next Step

If implementation starts later, the next justified step is Phase A only:

- inventory premium-sensitive logic in `frontend/src/**`
- classify what must move out of renderer authority
- produce a concrete renderer/main/backend boundary map before any signing or compiled-module work begins
