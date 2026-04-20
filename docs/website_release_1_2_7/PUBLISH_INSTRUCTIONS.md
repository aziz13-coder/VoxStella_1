# Publish Instructions for Website Release 1.2.7

I did not edit `website/**` directly because this repository marks that path as generated/read-only.

Use these files to publish the new blog post manually:

## Files in this folder

- `vox-stella-update-1-2-7-astro-clock-elections-updating.html`
  Copy to:
  `website/blog/posts/vox-stella-update-1-2-7-astro-clock-elections-updating.html`

- `posts-json-entry.json`
  Insert as the first item in:
  `website/blog/posts.json`

- `sitemap-entry.xml`
  Add to:
  `website/sitemap.xml`

## Recommended build steps

After updating the website source files:

1. From `website/`, run:
   `npm run build`
2. Verify the new post appears in:
   - blog index
   - sitemap
   - rss
3. Deploy the rebuilt site.

## SEO choices used

- Title targets:
  - `Vox Stella Update 1.2.7`
  - `Astro Clock`
  - `elections`
  - `updating`
- Slug is short and release-specific
- Category is `Releases`
- Excerpt is product-focused and plain-language

## User-facing update wording

- Update from inside the app:
  `Settings > Updates > Check for updates`
- Fresh install:
  download again from [voxstella.app](https://voxstella.app/)
