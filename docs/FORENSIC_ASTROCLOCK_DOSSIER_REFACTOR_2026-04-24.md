# AstroClock Forensic Dossier Refactor - 2026-04-24

## Scope

The standalone `Forensic Report _Standalone_(1).html` file was used as a visual sketch for the AstroClock forensic modal. It is not a full replacement contract for the app workflow.

This implementation keeps the existing forensic workflow and outcome analysis intact while moving the modal toward the sketch structure:

- Dossier shell with case snap, mode/scope, controls, and tabbed sections.
- Findings-first report surface with verdict pressure, relationship signature, metric strips, directional axes, categories, top findings, and finding notes.
- The existing final outcome determination tile remains in the Findings tab because the app already has working IC/4th-house outcome logic and the sketch omits it only because it is incomplete.

## Design Decisions

- The frontend continues to expose only supported case profiles: `General`, `Child`, and `Adult Female`. The sketch shows `Adult Male` and `Missing`, but the backend currently normalizes unsupported values back to `general`, so exposing them would create a false control.
- Top findings should follow backend weight ordering when weights are available. Synthetic/frontend-only payloads without weights still use the conservative replay-axis selection path so prior replay-axis regression coverage remains stable.
- Relationship analysis is split into its own tab at the dossier level while the perpetrator section keeps its behavioral and 7th-house analysis.
- The outcome tile is restyled to match the dossier, not removed.

## Backend Fix

The survivability model no longer treats every `Abduction` category hit as a controlling abduction context. Domestic/family fatal mechanisms must remain active when a broad abduction/deceptive-assignment rule is also present.

This prevents known family-home homicide cases from being downweighted into `risk_loaded_survival` solely because a broad abduction category appears in the finding set.

## Source Paths

- `backend/forensic/survivability.py`
- `frontend/backend/forensic/survivability.py`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/forensicDossier.css`
