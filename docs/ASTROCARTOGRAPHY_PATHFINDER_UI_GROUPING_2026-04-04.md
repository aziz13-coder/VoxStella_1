# Astrocartography PathFinder UI Grouping

Date: 2026-04-04

## Why this change

After expanding the Astrocartography model set to `17` goals, the PathFinder dropdown became too flat to scan comfortably in the UI. The underlying model set was stronger, but the control looked like an internal enum instead of a user-facing choice surface.

## Implemented

The PathFinder goal picker in [AstrocartographyModal.jsx](/Users/sabaa/Downloads/codexhorary/frontend/src/features/astroclock/AstrocartographyModal.jsx) now groups goals into:

- `Core Goals`
- `Specialist Variants`

Current specialist variants:

- `Love Commitment`
- `Money Stable Income`
- `Career Public Profile`
- `Home Retreat`

Everything else remains in the core group.

## UI behavior

- `General inspection` still appears as the neutral top-level option.
- The grouped dropdown uses standard HTML `optgroup`, so it stays aligned with the current Astro Clock design language instead of introducing a new custom control.
- When a goal is selected, the modal now shows:
  - whether the goal is `Core Goals` or `Specialist Variants`
  - its goal family
  - its short summary

That keeps the advanced model set understandable without adding another settings screen.

## Design rationale

This keeps the feature aligned with the existing app:

- same simple select control grammar as the other feature inputs
- no extra modal complexity
- more semantic structure where the model list had become too long

## Boundary

This is a UI organization improvement only. It does not change backend ranking behavior or score math.
