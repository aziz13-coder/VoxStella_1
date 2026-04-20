# What's New Modal Polish

Date: 2026-04-19

## Scope

This pass updated the desktop `What's New` popup so it follows the same design language as the newer Astro Clock workspaces and modals.

Files changed:

- `frontend/src/components/WhatsNewModal.jsx`
- `frontend/src/content/whatsNew.mjs`
- `frontend/src/tests/whatsNew.test.mjs`
- `frontend/src/tests/whatsNewModal.test.jsx`

## Design Direction

The previous popup read like a separate announcement surface:

- dark glass shell in both themes
- tighter radius than the newer modal family
- badge-heavy header
- duplicated close actions
- release-copy phrasing closer to changelog marketing than in-app workspace language

The updated modal now follows the current workspace pattern:

- paper-style shell with `rounded-[28px]`
- zinc borders and restrained shadow
- small uppercase kicker plus large serif headline
- one accent family only
- single header close action
- divided content rows instead of stacked promo blocks

## Content Model

`frontend/src/content/whatsNew.mjs` now supports a calmer, product-oriented release structure:

- `headline`
- `summary`
- `items`
- `note`

Each `item` is now written as:

```js
{
  title: 'Election',
  tag: 'Beta',
  body: 'Business Beta is now available as an early research path...'
}
```

This keeps the popup readable and makes each release point scan like product UI, not a changelog paragraph.

## UX Rules

The modal should stay aligned with the app if future entries follow these rules:

- Keep the headline short and operational.
- Use one summary sentence only.
- Prefer 3-4 item rows max.
- Use `tag` only for meaningful state such as `Beta` or `In progress`.
- Keep the note block for context or maturity status, not for marketing copy.
- Avoid duplicate footer actions when the header already provides a close affordance.

## Verification

Run from `frontend/`:

- `npx vitest run src/tests/whatsNew.test.mjs src/tests/whatsNewModal.test.jsx`
