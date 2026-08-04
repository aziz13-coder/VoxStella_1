export const WHATS_NEW_RELEASES = {
  '3.1.14': {
    version: '3.1.14',
    publishedAt: '2026-08-04',
    headline: 'Stronger forensic outcome and relationship analysis',
    summary: 'This update makes forensic survivability follow Descendant evidence and resolves contradictions between relationship findings and final classification, with wider fixture-based regression safeguards.',
    items: [
      {
        title: 'Descendant-led survivability',
        tag: 'Fixed',
        body: 'Weighted Descendant-ruler aspects now inform victim survivability through the DCS evidence path only, without importing Ascendant testimony into the outcome.',
      },
      {
        title: 'Coherent relationship signals',
        tag: 'Fixed',
        body: 'A qualifying Moon-dispositor, 7th-ruler, and transport-harm bridge can support a broad friend or acquaintance link while never claiming a spouse or family relationship by itself.',
      },
      {
        title: 'Wider case validation',
        tag: 'Tested',
        body: 'The crash case, Idaho student murders case, and the full forensic fixture collection now guard the new logic against case-specific overfitting.',
      },
      {
        title: 'Neutral fixture terminology',
        tag: 'Improved',
        body: 'Forensic dashboard golden fixtures now use platform-neutral names that reflect their actual purpose.',
      },
    ],
  },
  '3.1.13': {
    version: '3.1.13',
    publishedAt: '2026-08-02',
    headline: 'Clearer transit exactness and dependable AI scans',
    summary: 'This update separates Morin three-dimensional contacts from zodiacal longitude exactness, corrects activation timing, and keeps licensed AI transit scans compact enough to return reliably.',
    items: [
      {
        title: 'Two clear transit orbs',
        tag: 'Improved',
        body: 'Transit results now show Morin three-dimensional orb and zodiacal longitude orb separately, so physical-space proximity is never mistaken for longitude exactness.',
      },
      {
        title: 'Accurate activation windows',
        tag: 'Fixed',
        body: 'Applying, exact, and separating timing now follows zodiacal longitude, producing activation windows around the actual aspect crossing.',
      },
      {
        title: 'Reliable MCP transit scans',
        tag: 'Improved',
        body: 'Licensed local AI clients now receive compact transit scans by default while retaining the evidence, timing, and ranking needed for interpretation.',
      },
      {
        title: 'Expanded forensic verification',
        tag: 'Tested',
        body: 'The Idaho student murders benchmark now includes a reproducible runner, documented facts, exact-window checks, and stability cases for regression testing.',
      },
    ],
  },
  '3.1.12': {
    version: '3.1.12',
    publishedAt: '2026-08-02',
    headline: 'Licensed AI access across Astro Clock',
    summary: 'This update lets licensed local AI clients use Synastry, Trait Profile, Transits, Astrocartography, Election, Chinese Astrology, Forensic, and Certification through the Vox Stella calculation engine.',
    items: [
      {
        title: 'Eight Astro Clock feature families',
        tag: 'New',
        body: 'The local MCP integration now offers focused tools for chart comparison, traits, timing, place analysis, elections, Chinese Astrology, forensic event charts, and birth-time certification.',
      },
      {
        title: 'Private explicit inputs',
        tag: 'Privacy',
        body: 'AI calculations use the dates, times, coordinates, and timezones you provide without giving the client a way to browse saved charts, notes, account details, or license credentials.',
      },
      {
        title: 'Reliable long calculations',
        tag: 'Improved',
        body: 'Transit windows, atlas searches, Election scans, and Certification now use bounded inputs and longer calculation deadlines, with streaming Election results returned as a normal structured response.',
      },
      {
        title: 'Stricter licensed access',
        tag: 'Security',
        body: 'Every request requires a fresh short-lived licensed session and can reach only its declared local calculation route, method, and input fields.',
      },
    ],
  },
  '3.1.11': {
    version: '3.1.11',
    publishedAt: '2026-08-02',
    headline: 'Local AI access with safer MCP setup',
    summary: 'This update adds guided MCP setup for licensed local AI clients and strengthens startup, cancellation, input validation, and private backend access.',
    items: [
      {
        title: 'Guided MCP setup',
        tag: 'New',
        body: 'Settings now shows whether local MCP access is ready, lists the available read-only tools, and copies tested JSON or Codex configuration for the installed launcher.',
      },
      {
        title: 'More dependable connections',
        tag: 'Improved',
        body: 'MCP startup now allows the licensed calculation engine to complete its full readiness sequence, while cancelled requests stop their pending local work promptly.',
      },
      {
        title: 'Stricter calculation inputs',
        tag: 'Fixed',
        body: 'Chart requests now require an explicit date and time instead of silently treating a date-only value as midnight.',
      },
      {
        title: 'Stronger local boundaries',
        tag: 'Security',
        body: 'Licensed MCP calls now validate and canonicalize their private loopback destination before any short-lived access token is attached.',
      },
    ],
  },
  '3.1.10': {
    version: '3.1.10',
    publishedAt: '2026-08-02',
    headline: 'More dependable transit timing',
    summary: 'This update makes exact transit calculations and predictor scans consistent across timezones, streaming, and fallback requests while keeping transit history isolated to the active chart.',
    items: [
      {
        title: 'Reliable exact-time calculations',
        tag: 'Fixed',
        body: 'Transit timestamps now use a consistent UTC contract, including timezone-free inputs, and invalid dates can no longer silently calculate the current sky.',
      },
      {
        title: 'Consistent scans and predictions',
        tag: 'Improved',
        body: 'Streaming and standard window scans now share bounded display logic, enrich each active transit once, and preserve deeper Ascendant evidence for predictions.',
      },
      {
        title: 'Chart history stays isolated',
        tag: 'Fixed',
        body: 'Multiple and successive transit evidence is now scoped to the active calculation so another chart or earlier request cannot alter the result.',
      },
      {
        title: 'Clearer aspect exactness',
        tag: 'Improved',
        body: 'Partile aspects follow the documented one-degree band, while physical planetary-disc contact is retained as a separate calculation detail.',
      },
    ],
  },
  '3.1.9': {
    version: '3.1.9',
    publishedAt: '2026-08-01',
    headline: 'Cleaner forensic reports',
    summary: 'This update removes repetitive warning copy from the Forensic workspace, generated reports, and copied analysis briefs. It also adds a source-backed Idaho murders benchmark for ongoing regression testing.',
    items: [
      {
        title: 'A cleaner forensic workspace',
        tag: 'Polished',
        body: 'The persistent warning beneath the Forensic controls has been removed so the dossier moves directly into its findings and evidence panels.',
      },
      {
        title: 'Cleaner reports and briefs',
        tag: 'Polished',
        body: 'PDF exports and copied analysis briefs no longer repeat the removed warning language.',
      },
      {
        title: 'Source-backed Idaho benchmark',
        tag: 'Tested',
        body: 'The Forensic regression suite now compares the engine with adjudicated facts and the official event-time interval from the Idaho student murders case.',
      },
    ],
  },
  '3.1.8': {
    version: '3.1.8',
    publishedAt: '2026-08-01',
    headline: 'Stronger forensic case analysis',
    summary: 'This update makes Forensic case classifications more careful, source-aware, and dependable across homicide, abduction, travel-disaster, water, public-event, and survivability readings.',
    items: [
      {
        title: 'Fewer false case labels',
        tag: 'Improved',
        body: 'Home, social, travel, and water symbolism now stays contextual until independent evidence supports a specific family, abduction, accident, or drowning classification.',
      },
      {
        title: 'Better documentary case matching',
        tag: 'Improved',
        body: 'The Forensic engine now performs more dependably across a wider range of documented homicide, disaster, crowd, and transport cases.',
      },
      {
        title: 'Clearer accident and outcome logic',
        tag: 'Fixed',
        body: 'Detecting a crash or transport event no longer automatically implies a fatal outcome; event type and survivability are evaluated separately.',
      },
      {
        title: 'Auditable source-backed rules',
        tag: 'Improved',
        body: 'New and revised rules expose their source basis and use corroborating evidence channels instead of case-specific exclusions.',
      },
    ],
  },
  '3.1.7': {
    version: '3.1.7',
    publishedAt: '2026-07-31',
    headline: 'Clearer transit guidance',
    summary: 'This update makes Transit timing, themes, and supported event readings easier to distinguish and more dependable across exact-time and predictor views.',
    items: [
      {
        title: 'Themes are clearly identified',
        tag: 'Improved',
        body: 'Transit symbolism now stays labeled as a theme until the chart has enough supporting timing factors for a stronger event reading.',
      },
      {
        title: 'More dependable event wording',
        tag: 'Improved',
        body: 'Broad words such as conflict, loss, or change no longer turn into an unrelated specific event through keyword matching alone.',
      },
      {
        title: 'Clearer support percentages',
        tag: 'Improved',
        body: 'Predictor percentages are now identified as rule-concordance scores instead of being presented like statistical event probabilities.',
      },
      {
        title: 'More faithful activation timing',
        tag: 'Fixed',
        body: 'Exact-time and window calculations now handle activation periods and local timezone transitions more consistently.',
      },
    ],
  },
  '3.1.6': {
    version: '3.1.6',
    publishedAt: '2026-07-31',
    headline: 'Stronger election planning',
    summary: 'This update makes Election searches clearer and more dependable across different goals, while making upgrades from earlier Vox Stella versions smoother.',
    items: [
      {
        title: 'Clearer choices for each goal',
        tag: 'Improved',
        body: 'Election searches now present the options that belong to the selected purpose, making it easier to shape the dates and times you want to compare.',
      },
      {
        title: 'More dependable ranked times',
        tag: 'Improved',
        body: 'The Election models now apply their required, supportive, and cautionary conditions more consistently when ranking candidate times.',
      },
      {
        title: 'Natal details stay optional',
        tag: 'Improved',
        body: 'You can still search without birth details, and add them only when you want the selected times compared with a natal chart.',
      },
      {
        title: 'Smoother upgrades',
        tag: 'Fixed',
        body: 'Setup can now recover more reliably when an earlier Vox Stella version cannot be removed in the usual way, while keeping your license, saved charts, and preferences.',
      },
    ],
  },
  '3.1.5': {
    version: '3.1.5',
    publishedAt: '2026-07-18',
    headline: 'Clearer Almuten readings',
    summary: 'This update makes traditional dignity and Almuten results more dependable, easier to compare, and clearer when chart context is incomplete.',
    items: [
      {
        title: 'More dependable dignity results',
        tag: 'Improved',
        body: 'Traditional degree ranges are now handled consistently across the chart, giving Almuten results a steadier foundation.',
      },
      {
        title: 'No guessed day or night',
        tag: 'Improved',
        body: 'When the chart cannot confirm whether it is a day or night chart, Vox Stella now says so clearly instead of making an assumption.',
      },
      {
        title: 'Ties are easier to understand',
        tag: 'Improved',
        body: 'When more than one planet shares the lead, each planet now shows its own supporting dignities.',
      },
      {
        title: 'Cleaner zodiac positions',
        tag: 'Polished',
        body: 'Degree and minute labels now round correctly, including positions that carry into the next sign.',
      },
    ],
  },
  '3.1.4': {
    version: '3.1.4',
    publishedAt: '2026-07-18',
    headline: 'Clearer Directional views',
    summary: 'This update makes the Directional compass and its 3D view clearer, more consistent, and easier to use across saved charts and smaller screens.',
    items: [
      {
        title: 'A more faithful compass',
        tag: 'Improved',
        body: 'Direction and height are now shown more clearly, with labels kept apart so crowded charts remain easier to read.',
      },
      {
        title: 'Three clearer 3D perspectives',
        tag: 'Improved',
        body: 'The 3D view now separates the chart, equatorial, and local-horizon perspectives, and each visible object can be selected directly while you explore.',
      },
      {
        title: 'Saved charts stay consistent',
        tag: 'Improved',
        body: 'Opening Directional views from a saved chart now keeps the chart\'s confirmed settings throughout the experience.',
      },
      {
        title: 'Better on smaller screens',
        tag: 'Polished',
        body: 'Astro Clock and Directional views now fit more comfortably on phones and tablets, with easier access to the workspace.',
      },
    ],
  },
  '3.1.3': {
    version: '3.1.3',
    publishedAt: '2026-07-18',
    headline: 'Safer saved chart corrections',
    summary: 'This update makes older saved charts easier to review and correct, while keeping the original chart safely preserved.',
    items: [
      {
        title: 'Automatic place details',
        tag: 'Improved',
        body: 'Entering a specific city can now fill its matching coordinates and timezone before you preview a corrected chart.',
      },
      {
        title: 'Safer local-time choices',
        tag: 'Improved',
        body: 'When a daylight-saving time occurs twice, Vox Stella asks which occurrence you meant, and it stops times that never occurred.',
      },
      {
        title: 'Corrected copies stay connected',
        tag: 'Improved',
        body: 'The original chart remains preserved while its corrected copy carries the confirmed details into related readings.',
      },
      {
        title: 'Calmer review guidance',
        tag: 'Polished',
        body: 'Saved-chart review notes now use the quieter visual style of the rest of the workspace.',
      },
    ],
  },
  '3.1.2': {
    version: '3.1.2',
    publishedAt: '2026-07-18',
    headline: 'Deeper Astrocartography guidance',
    summary: 'This update makes Astrocartography place guidance more dependable, clearer about why a location fits, and more careful when a city or interpretation is uncertain.',
    items: [
      {
        title: 'Better-matched destinations',
        tag: 'Improved',
        body: 'Place suggestions now respond more thoughtfully to what you want from a move or journey, including career, relationships, home life, wellbeing, creativity, and personal growth.',
      },
      {
        title: 'Clearer learning and communication guidance',
        tag: 'Improved',
        body: 'Writing, speaking, networking, studying, and teaching are now read as distinct goals, giving each kind of place search a more focused result.',
      },
      {
        title: 'More dependable city matching',
        tag: 'Improved',
        body: 'City searches are more precise, and Vox Stella now asks for clarity when a place name could refer to more than one location.',
      },
      {
        title: 'More honest confidence',
        tag: 'Improved',
        body: 'Readings now make it easier to see which guidance is well supported and which parts should be treated as tentative.',
      },
    ],
  },
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
