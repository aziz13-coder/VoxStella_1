# App Review And Fixes

Date: 2026-04-16

## Scope

This pass documented the latest app-review findings and resolved the requested UI and workflow issues in source files only.

Findings addressed:

1. Notes panel claimed Markdown support but rendered plain text
2. Notes attachment actions were visible dead buttons
3. Settings documentation CTA was not wired
4. What's New release gating had drifted out of sync with the current package version

Only source files were changed:

- `frontend/src/**`
- `docs/**`

No packaged artifacts were edited.

## Findings Status

### 1. Notes panel advertised Markdown but rendered plain text [Resolved]

Problem:

- The notes editor placeholder said Markdown was supported.
- The read view rendered the saved note inside a plain text container.
- Users saw raw Markdown syntax instead of formatted notes.

Fix:

- Added a safe note Markdown renderer in `frontend/src/utils/noteMarkdown.jsx`.
- The rendered path now supports headings, paragraphs, lists, blockquotes, inline code, emphasis, bold text, and safe external links.
- The read view in the Notes tab now uses the Markdown renderer instead of plain text output.

Files:

- `frontend/src/utils/noteMarkdown.jsx`
- `frontend/src/App.jsx`
- `frontend/src/tests/noteMarkdown.test.jsx`

### 2. Notes attachment actions were dead buttons [Resolved]

Problem:

- The `Voice Note`, `Video Link`, and `External Link` controls in the notes workflow were rendered as clickable buttons.
- None of them had a handler, so they did nothing in the shipped UI.

Fix:

- Converted the controls into working insertion actions.
- Each action now switches the note into edit mode and inserts a Markdown link template for the selected attachment type.
- Renamed the labels to make the behavior clearer inside the note workflow.

Files:

- `frontend/src/utils/noteMarkdown.jsx`
- `frontend/src/App.jsx`
- `frontend/src/tests/noteMarkdown.test.jsx`

### 3. Settings documentation CTA was not wired [Resolved]

Problem:

- The About section exposed a `View Enhanced Documentation` button.
- The control had no handler and no URL target.

Fix:

- Wired the CTA to the workspace documentation URL:
  - `https://voxstella.app/docs/workspace/`
- The button now uses the existing Electron external-open bridge when available and falls back to `window.open` in browser-style runtimes.
- Updated the label to `View Workspace Documentation` so it matches the target.

Files:

- `frontend/src/App.jsx`

### 4. What's New release gating was out of sync with the current build [Resolved]

Problem:

- The release registry used exact version keys.
- The test suite still expected `2.1.1`, while the current packaged version is `2.1.2`.
- That made the frontend suite fail for the wrong reason and made the workflow fragile during version bumps.

Fix:

- Updated the tests to use the current bundled package version instead of a stale hard-coded value.
- Added an explicit test contract that the current package version has a matching registry entry.
- Hardened `getWhatsNewRelease(...)` so a future version newer than the registry can still fall back to the latest known release instead of silently returning `null`.
- Updated the modal badge so fallback behavior is visible if it ever happens.

Files:

- `frontend/src/content/whatsNew.mjs`
- `frontend/src/components/WhatsNewModal.jsx`
- `frontend/src/tests/whatsNew.test.mjs`

## Verification

Run after the fixes:

- `npm test` from `frontend/`

Not run:

- Manual packaged Electron validation in this pass
