export const WHATS_NEW_RELEASES = {
  '3.1.1': {
    version: '3.1.1',
    publishedAt: '2026-07-17',
    headline: 'Deeper Chinese Astrology readings',
    summary: 'This update makes Chinese Astrology readings more careful when birth time is unknown, clearer about the elements, and more thoughtful in relationship comparisons.',
    items: [
      {
        title: 'Safer unknown birth times',
        tag: 'Improved',
        body: 'When an unknown birth time could change the year or month pillar, Vox Stella now shows the possible charts and clearly marks what cannot yet be settled.',
      },
      {
        title: 'Clearer element readings',
        tag: 'Improved',
        body: 'The reading now keeps element appearances separate from their seasonal strength, so a frequently seen element is not automatically treated as powerful.',
      },
      {
        title: 'More thoughtful relationship readings',
        tag: 'Improved',
        body: 'Comparisons now follow a carefully curated reading approach and describe the evidence in words instead of reducing two charts to a single score.',
      },
      {
        title: 'More reliable seasonal boundaries',
        tag: 'Improved',
        body: 'Seasonal turning points are handled more reliably, and a reading pauses clearly if an exact boundary cannot be confirmed.',
      },
    ],
  },
  '3.1.0': {
    version: '3.1.0',
    publishedAt: '2026-06-24',
    headline: 'Bug fixes',
    summary: 'This release focuses on bug fixes and reliability improvements.',
    items: [
      {
        title: 'Bug fixes',
        tag: 'Fix',
        body: 'Fixed issues and improved reliability across the desktop app.',
      },
    ],
  },
  '3.0.1': {
    version: '3.0.1',
    publishedAt: '2026-05-23',
    headline: 'Certification, Points, and calibrated Forensic scan',
    summary: 'This release adds birth-time certification, brings Symbolic Points into Trait Profile and Astro Clock Degree Hits, and calibrates the Forensic scan for clearer case review.',
    items: [
      {
        title: 'Birth Time Certification',
        tag: 'New',
        body: 'Review dated life events against a chart and compare possible birth-time candidates in one focused workflow.',
      },
      {
        title: 'Symbolic Points',
        tag: 'New',
        body: 'Trait Profile now includes active Symbolic Points, with a cleaner top-results view for chart review.',
      },
      {
        title: 'Degree Hits',
        tag: 'Astro Clock',
        body: 'The Degree Hits tile now opens a focused More view with the strongest active point contacts for the current chart.',
      },
      {
        title: 'Forensic Scan',
        tag: 'Calibrated',
        body: 'Forensic scan wording, layout, and calibration were cleaned up so case review reads more clearly and avoids unnecessary technical language.',
      },
    ],
  },
  '3.0.0': {
    version: '3.0.0',
    publishedAt: '2026-05-22',
    headline: 'Certification, Points, and clearer case review',
    summary: 'This release adds birth-time certification, brings Symbolic Points into Trait Profile and Astro Clock Degree Hits, and makes Forensic review clearer to read.',
    items: [
      {
        title: 'Birth Time Certification',
        tag: 'New',
        body: 'Review dated life events against a chart and compare possible birth-time candidates in one focused workflow.',
      },
      {
        title: 'Symbolic Points',
        tag: 'New',
        body: 'Trait Profile now includes active Symbolic Points, with a cleaner top-results view for chart review.',
      },
      {
        title: 'Degree Hits',
        tag: 'Astro Clock',
        body: 'The Degree Hits tile now opens a focused More view with the strongest active point contacts for the current chart.',
      },
      {
        title: 'Forensic Review',
        tag: 'Improved',
        body: 'Forensic wording and layout were cleaned up so case review reads more clearly and avoids unnecessary technical language.',
      },
    ],
  },
  '2.9.0': {
    version: '2.9.0',
    publishedAt: '2026-05-13',
    headline: 'Chinese Astrology and Forensic calibration',
    summary: 'This build adds Chinese Astrology to Astro Clock and refreshes Forensic readings with clearer calibration.',
    items: [
      {
        title: 'Chinese Astrology',
        tag: 'New',
        body: 'Explore Chinese Astrology readings from Astro Clock, including chart and relationship views.',
      },
      {
        title: 'Forensic',
        tag: 'Calibration',
        body: 'Forensic readings were recalibrated for clearer case signals and more careful wording.',
      },
    ],
  },
  '2.7.2': {
    version: '2.7.2',
    publishedAt: '2026-05-07',
    headline: 'Trait Profile criminal benchmark calibration',
    summary: 'This build recalibrates Trait Profile biography matching for the criminal-case benchmark batch.',
    items: [
      {
        title: 'Trait Profile',
        tag: 'Calibration',
        body: 'Added a criminal-case benchmark path and tuned the summary ranking for clearer biography matching.',
      },
    ],
  },
  '2.7.1': {
    version: '2.7.1',
    publishedAt: '2026-05-07',
    headline: 'Trait Profile engine recalibration',
    summary: 'This build recalibrates the Trait Profile engine so top traits better reflect the person\'s life and public profile.',
    items: [
      {
        title: 'Trait Profile',
        tag: 'Calibration',
        body: 'Recalibrated the trait engine and summary ranking for clearer, more biography-relevant top traits.',
      },
    ],
  },
  '2.7.0': {
    version: '2.7.0',
    publishedAt: '2026-05-06',
    headline: 'Trait Profile redesign and steadier snaps',
    summary: 'This build introduces the redesigned Trait Profile workspace with stronger chart-backed logic, saved-snap support, and reliability fixes for snapping realtime and manual charts. Read the blog for the full walkthrough.',
    items: [
      {
        title: 'Trait Profile redesign',
        tag: 'New',
        body: 'Trait Profile now uses the newer Astro Clock reading layout with Overview, Domains, Topic Maps, House Influence, and All Traits views.',
      },
      {
        title: 'Better trait logic',
        body: 'Trait scores and topic maps are more tightly wired to real chart determinations and were checked with focused benchmark cases.',
      },
      {
        title: 'Snap reliability',
        tag: 'Fix',
        body: 'Saving realtime and manual charts as snaps should be more reliable, with saved chart context preserved across related Astro Clock features.',
      },
      {
        title: 'More detail',
        body: 'For the complete explanation of the redesign, logic work, and snap fixes, read the Build 2.7 blog post.',
      },
    ],
  },
  '2.5.1': {
    version: '2.5.1',
    publishedAt: '2026-05-05',
    headline: 'Smoother startup and small-screen release notes',
    summary: 'This build improves first-run behavior so Vox Stella stays in a checking state while the local engine warms up, and makes the release notes window usable on smaller screens.',
    items: [
      {
        title: 'Startup readiness',
        tag: 'Polish',
        body: 'The app now waits through local engine startup before showing an offline state, avoiding early fetch errors while the packaged backend is still warming up.',
      },
      {
        title: 'Astro Clock loading',
        body: 'Astro Clock now pauses automatic dashboard requests while the backend is still checking and resumes once the engine reports connected.',
      },
      {
        title: 'Small-screen notes',
        body: 'The What\'s New window now uses a viewport-constrained shell with internal scrolling, so the close control and release details remain reachable on compact displays.',
      },
    ],
  },
  '2.4.0': {
    version: '2.4.0',
    publishedAt: '2026-04-24',
    headline: 'Forensic dossier redesign and Astro Clock polish',
    summary: 'This build refactors the Forensic report interface into the newer Astro Clock reading language while keeping the broader workspace polish notes visible.',
    items: [
      {
        title: 'Forensic report redesign',
        tag: 'Refactor',
        body: 'The Forensic feature now opens as a dossier-style workspace aligned with Astro Clock and Synastry: cleaner case context, tabbed evidence sections, a default case summary, dedicated raw evidence, and clearer controls for abduction, AI brief copy, and PDF export.',
      },
      {
        title: 'Forensic readability',
        body: 'Typography and spacing were tightened so forensic headings keep an editorial report feel while dense evidence rows, chips, and controls stay easier to scan.',
      },
      {
        title: 'Mundo and Weather',
        tag: 'In development',
        body: 'The Mundo and Weather modules are still under active development. These features will take time to mature, so they should be treated as evolving research work rather than finished tools.',
      },
      {
        title: 'Astro Clock polish',
        body: 'The Astro Clock workspace continues to be refined for a cleaner reading surface, including the recent directional tile and dashboard presentation improvements.',
      },
    ],
    note: 'You are more than welcome to share opinions and ask for features. If a request is feasible, we will try to implement it.',
  },
  '2.3.6': {
    version: '2.3.6',
    publishedAt: '2026-04-22',
    headline: 'Real Estate, Lunar Fertility reports, and Astro Clock polish',
    summary: 'This build adds Real Estate election timing and Lunar Fertility reporting, continues Astro Clock polish, and keeps the newer Mundo and Weather modules clearly marked as still maturing.',
    items: [
      {
        title: 'Real Estate election',
        tag: 'New',
        body: 'A Real Estate election model was added for property buy and sell timing. In general, it weighs the event chart together with one saved buyer or seller chart, looking at property, money or transfer, Moon timing, and participant fit signals.',
      },
      {
        title: 'Lunar Fertility reporting',
        tag: 'New',
        body: 'Lunar Fertility Windows now includes a dedicated fertility-only report export with the shared report header, graphic timeline, grouped fertile periods, top timepoints, and full hourly favorable table.',
      },
      {
        title: 'Mundo and Weather',
        tag: 'In development',
        body: 'The Mundo and Weather modules are still under active development. These features will take time to mature, so they should be treated as evolving research work rather than finished tools.',
      },
      {
        title: 'Astro Clock polish',
        body: 'The Astro Clock workspace continues to be refined for a cleaner reading surface, including the recent directional tile and dashboard presentation improvements.',
      },
    ],
    note: 'You are more than welcome to share opinions and ask for features. If a request is feasible, we will try to implement it.',
  },
  '2.3.4': {
    version: '2.3.4',
    publishedAt: '2026-04-21',
    headline: 'Real Estate election model and Astro Clock polish',
    summary: 'This build adds a Real Estate election model, continues Astro Clock polish, and keeps the newer Mundo and Weather modules clearly marked as still maturing.',
    items: [
      {
        title: 'Real Estate election',
        tag: 'New',
        body: 'A Real Estate election model was added for property buy and sell timing. In general, it weighs the event chart together with one saved buyer or seller chart, looking at property, money or transfer, Moon timing, and participant fit signals.',
      },
      {
        title: 'Mundo and Weather',
        tag: 'In development',
        body: 'The Mundo and Weather modules are still under active development. These features will take time to mature, so they should be treated as evolving research work rather than finished tools.',
      },
      {
        title: 'Astro Clock polish',
        body: 'The Astro Clock workspace continues to be refined for a cleaner reading surface, including the recent directional tile and dashboard presentation improvements.',
      },
    ],
    note: 'You are more than welcome to share opinions and ask for features. If a request is feasible, we will try to implement it.',
  },
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
