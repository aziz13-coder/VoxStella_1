# SEO AI Agent Curation Remediation - 2026-05-18

## Context

After the AI agent curation update, live SEO checks showed a drop in Lighthouse SEO scores and a duplicate crawl surface on the Cloudflare Pages preview host.

## Findings And Fixes

| Issue | Evidence | Resolution |
| --- | --- | --- |
| `robots.txt` failed Lighthouse validation | Lighthouse reported `Unknown directive` for three `Content-Signal:` lines. | Removed non-standard `Content-Signal:` directives from `website/robots.txt`. Agent-readable discovery remains available through `.well-known/agent-skills`, `.well-known/api-catalog`, and MCP discovery. |
| Blog index used generic link text | Lighthouse reported six `/blog` links with visible text `Read more`. | Updated `website/scripts/build-blog-index.js` and the inline blog renderer in `website/blog.html` so generated and client-rendered blog rows include the post title in visually hidden link text. |
| `voxstella.pages.dev` exposed duplicate indexable pages | Live checks returned `200` with `index,follow` meta robots and apex canonical tags. | Updated `website/functions/_middleware.js` to add `X-Robots-Tag: noindex, nofollow` on `voxstella.pages.dev` and branch-preview `*.voxstella.pages.dev` responses while preserving preview access. |

## Verification Commands

Run from `website/`:

```powershell
npm run build
npx --yes lighthouse https://voxstella.app/ --only-categories=seo --chrome-flags="--headless --no-sandbox" --quiet --output=json --output-path=$env:TEMP\voxstella-home-lighthouse-seo.json
npx --yes lighthouse https://voxstella.app/blog --only-categories=seo --chrome-flags="--headless --no-sandbox" --quiet --output=json --output-path=$env:TEMP\voxstella-blog-lighthouse-seo.json
```

After deployment, verify:

```powershell
curl.exe -sS https://voxstella.app/robots.txt
curl.exe -sS -I https://voxstella.pages.dev/ | Select-String -Pattern "HTTP/|x-robots-tag:"
```

Expected deployed results:

- `robots.txt` contains only standard robots fields and comments.
- `https://voxstella.app/` Lighthouse SEO no longer fails `robots-txt`.
- `https://voxstella.app/blog` no longer fails generic link text for generated `Read more` links.
- `https://voxstella.pages.dev/` includes `X-Robots-Tag: noindex, nofollow`.

## Local Verification Results

Verified after `npm run build` on 2026-05-18:

- `npm run build` passed, including structured-data validation and public PNG checks.
- Local Lighthouse SEO on `dist/index.html` through `http://127.0.0.1:8099/index.html`: `100`, with no failing SEO audits.
- Local Lighthouse SEO on `dist/blog.html` through `http://127.0.0.1:8099/blog.html`: `100`, with no failing SEO audits.
- Local robots parser check found `0` unknown directives in `website/robots.txt`.
- Middleware smoke test returned `X-Robots-Tag: noindex, nofollow` for `voxstella.pages.dev` and branch preview hosts, and no `X-Robots-Tag` for `voxstella.app`.

## Ownership Note

The public agent-facing guidance may describe the site as read-only to outside agents. For repository maintenance, the deployable website files in `website/` are the source of truth for these SEO fixes.

In this checkout, `website/` is ignored by `.gitignore`, so the website source and generated `dist/` changes do not appear in `git status`. The tracked documentation record is `docs/SEO_AI_AGENT_CURATION_REMEDIATION_2026-05-18.md`.
