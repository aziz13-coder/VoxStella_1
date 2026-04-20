export const WHATS_NEW_RELEASES = {
  '2.2.6': {
    version: '2.2.6',
    publishedAt: '2026-04-19',
    headline: 'Synastry workspaces and new comparison views',
    summary: 'This build expands Astro Clock synastry with new ways to compare saved charts and a cleaner reading workspace.',
    items: [
      {
        title: 'Synastry',
        body: 'Saved-snap comparison now includes multiple views, so you can move between the memo, broad life themes, union-focused reading, and work-focused reading in one place.',
      },
      {
        title: 'Structured views',
        body: 'The new comparison views open into clearer worksheets with area summaries, grouped themes, and contact grids that are easier to scan.',
      },
      {
        title: 'Workspace polish',
        body: 'The synastry comparison surface now follows the calmer Astro Clock reading style more closely, with a cleaner layout and less visual clutter.',
      },
    ],
    note: 'Synastry is now broader and easier to navigate, and the comparison workspace will continue to be refined in upcoming builds.',
  },
  '2.1.4': {
    version: '2.1.4',
    publishedAt: '2026-04-16',
    headline: 'Aspect cleanup and marriage beta improvements',
    summary: 'This build focused on consistency across aspect handling and a steadier marriage election beta flow.',
    items: [
      {
        title: 'Aspect handling',
        body: 'Aspect output was cleaned up across the app for a clearer and more consistent reading surface.',
      },
      {
        title: 'Marriage election',
        tag: 'Beta',
        body: 'The marriage beta flow was refined for a steadier research experience.',
      },
      {
        title: 'Astrocartography',
        tag: 'In progress',
        body: 'Mundo and Weather remained under active development in this build.',
      },
    ],
    note: 'These notes are kept for version history and may describe work that has changed again in later builds.',
  },
  '2.1.2': {
    version: '2.1.2',
    publishedAt: '2026-04-16',
    headline: 'Astro Clock additions and marriage beta entry point',
    summary: 'This build expanded the Astro Clock dashboard and added a second research path for marriage elections.',
    items: [
      {
        title: 'Astro Clock',
        body: 'An Almuten tile was added so degree hits can be reviewed with almuten context directly in the dashboard.',
      },
      {
        title: 'Astro Clock',
        body: 'An Asteroids tile was added with major asteroids and Proserpina in the live workspace.',
      },
      {
        title: 'Marriage election',
        tag: 'Beta',
        body: 'A beta branch was added alongside the existing flow to open a second research path for marriage elections.',
      },
      {
        title: 'Astrocartography',
        tag: 'In progress',
        body: 'Mundo and Weather were still in an early workspace stage and should not be treated as finished tools in that build.',
      },
    ],
    note: 'Older release notes stay visible for version history, even when the current workspace has moved forward since then.',
  },
};

function parseVersionParts(version) {
  return String(version || '')
    .trim()
    .split('.')
    .map((part) => Number.parseInt(part, 10))
    .map((part) => (Number.isFinite(part) ? part : 0));
}

function compareVersions(left, right) {
  const a = parseVersionParts(left);
  const b = parseVersionParts(right);
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    const delta = (a[index] || 0) - (b[index] || 0);
    if (delta !== 0) return delta;
  }
  return 0;
}

export function getLatestWhatsNewRelease() {
  return Object.values(WHATS_NEW_RELEASES)
    .sort((left, right) => compareVersions(right.version, left.version))[0] || null;
}

export function getWhatsNewRelease(version) {
  const key = String(version || '').trim();
  if (!key) return null;
  const exact = WHATS_NEW_RELEASES[key];
  if (exact) {
    return {
      ...exact,
      requestedVersion: key,
      sourceVersion: exact.version,
      isFallback: false,
    };
  }

  const latest = getLatestWhatsNewRelease();
  if (!latest) return null;
  if (compareVersions(key, latest.version) < 0) return null;

  return {
    ...latest,
    requestedVersion: key,
    sourceVersion: latest.version,
    isFallback: true,
  };
}
