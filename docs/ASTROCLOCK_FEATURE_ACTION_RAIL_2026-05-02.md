# AstroClock Feature Action Rail

Date: 2026-05-02

## Recommendation

Move the AstroClock feature actions above the realtime/manual control bar and style them as a dedicated action rail.

This is the right direction. Synastry, Trait Profile, Transits, Astrocartography, Election, Forensic, and Copy Prompt are high-value actions. Their current location inside the center column makes them read as local tile controls, even though they open major workflows. Placing them above the clock controls makes the hierarchy clearer:

1. Leave AstroClock / return to dashboard.
2. Choose a feature workflow.
3. Set the clock mode and timestamp context.
4. Read the chart tiles.

The rail should not be treated as another navbar. Realtime/manual is the mode selector for the current chart context. The feature buttons are workflow launchers.

## Current Source Shape

Relevant source: `frontend/src/features/astroclock/AstroClock.jsx`.

- The realtime/manual control shell starts near the main AstroClock return markup, immediately after the "Back to Dashboard" button.
- The feature buttons currently render later in the center column, before the Solar Conditions tile.
- Premium workflow gating already lives in the feature handlers through `shouldGatePremiumFeature({ packagedRuntime, licenseActive })`.
- The Snap button already establishes the verified-user visual language: filled black pill, white text, compact uppercase lettering.

## Proposed Placement

Render the action rail in the same header band as "Back to Dashboard", before the existing `{/* Controls */}` shell.

On wide screens, keep "Back to Dashboard" anchored at the original left position and center the action rail in the middle of the page. Use a third empty balancing column on the right so the rail is visually centered instead of merely offset after the back link.

The order should be:

```text
Back to Dashboard | centered Feature Action Rail | empty balance column
Realtime / Manual control shell
AstroClock grid
```

Remove the old feature row from the center column after adding the rail. The Solar Conditions tile should become the first item in the center content column again.

## Button Set

Primary rail actions:

- Synastry
- Trait Profile
- Transits
- Astrocartography
- Election
- Forensic
- Copy Prompt

Keep the existing button labels and accessible names where possible so current tests and user muscle memory remain stable.

Copy Prompt should keep its dropdown behavior. It can sit at the end of the rail as a grouped action.

## Verified Versus Free Styling

For verified users, use the Snap visual family:

```text
bg-zinc-900 text-white hover:bg-zinc-800
dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200
```

For free users in the packaged app, use a red premium state:

```text
bg-red-600 text-white hover:bg-red-700
dark:bg-red-500 dark:hover:bg-red-400
```

This red state should mean "premium/locked", not "destructive". Avoid pairing it with delete-like wording. If the red styling feels too alarming after implementation, add a small lock icon or title text later rather than weakening the contrast.

Final product decision: Copy Prompt is a premium utility like the other feature workflows.

- Premium workflows: black for verified, red for free packaged users.
- Copy Prompt: black for verified, red for free packaged users.
- Free packaged users clicking Copy Prompt should go to the same premium upgrade URL instead of opening the prompt-type menu.

## Layout Rules

Desktop:

- Use a single flex row with wrapping.
- Keep the rail visually separate from the realtime/manual shell with `mb-3` or `mb-4`.
- Use compact pill buttons with stable height and minimum width.
- Do not introduce a large card around the rail.

Mobile / narrow widths:

- Allow wrapping into two rows.
- Keep tap targets at least 36px high.
- Avoid horizontal overflow that hides actions.
- Keep the realtime/manual shell directly below the rail.

Suggested container:

```jsx
<div className="mb-4 flex flex-wrap items-center gap-2">
  ...
</div>
```

## Implementation Notes

Use a small style helper rather than duplicating class strings on every button:

```jsx
const premiumLocked = shouldRedirectToUpgrade();
const featureActionCls = premiumLocked
  ? 'inline-flex ... bg-red-600 text-white hover:bg-red-700 ...'
  : 'inline-flex ... bg-zinc-900 text-white hover:bg-zinc-800 ...';
```

Avoid calling `shouldRedirectToUpgrade()` inside render if that callback later grows side effects. With the current implementation it is pure, but a clearer implementation is to derive the state directly:

```jsx
const featureActionsLocked = packagedRuntime && !licenseActive;
```

Then keep the existing click handlers unchanged:

- `handleOpenSynastry`
- `handleOpenTraitProfile`
- `handleOpenTransits`
- `handleOpenAstrocartography`
- `handleOpenElection`
- `handleOpenForensic`

Those handlers already redirect free packaged users to the premium upgrade flow. The UI change should not bypass or duplicate that logic.

## Tests To Update

Update `frontend/src/tests/astroClockModeFlow.test.jsx` only if assertions depend on DOM order or old placement.

Useful coverage:

- Verified user sees the rail actions before the Realtime/Manual control shell.
- Free packaged user sees premium workflow buttons with the red locked class.
- Free packaged user clicking a premium workflow still redirects through the existing premium route.
- Copy Prompt dropdown still opens from the new rail location.

## Acceptance Criteria

- Feature actions appear above Realtime/Manual in AstroClock.
- There is no duplicate feature row above Solar Conditions.
- Verified users see black filled feature buttons.
- Free packaged users see red premium workflow buttons.
- Existing feature handlers and modal workflows still work.
- Copy Prompt dropdown still works for verified users.
- Copy Prompt redirects free packaged users to the premium upgrade flow.
- The rail wraps cleanly at the screenshot width and on mobile.
