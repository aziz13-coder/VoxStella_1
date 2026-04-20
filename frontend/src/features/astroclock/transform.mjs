// Transform functions from API payload to UI-friendly model

const two = (n) => String(Math.floor(n)).padStart(2, '0');

export const degString = (lon) => {
  const d = lon || 0;
  const deg = Math.floor(d % 30);
  const min = Math.floor((d % 1) * 60);
  return `${deg}\u00B0${two(min)}'`;
};

export const aspectSymbol = (name) => ({
  Conjunction: '\u260C',
  Opposition: '\u260D',
  Trine: '\u25B3',
  Square: '\u25A1',
  Sextile: '\u26B9',
  'Semi-sextile': '\u26BA',
  Quincunx: '\u26BB',
  Antiscia: 'A',
  'Contra-antiscia': 'CA',
  conjunction: '\u260C',
  opposition: '\u260D',
  trine: '\u25B3',
  square: '\u25A1',
  sextile: '\u26B9',
  'semi-sextile': '\u26BA',
  quincunx: '\u26BB',
  antiscia: 'A',
  'contra-antiscia': 'CA',
  parallel: '\u2225',
  antiparallel: '\u21F5',
})[name] || '~';

const aspectIdentity = (row) => {
  if (!row || typeof row !== 'object') return null;
  const p1 = String(row.planet1 || '').trim();
  const p2 = String(row.planet2 || '').trim();
  const aspect = String(row.aspect || '').trim().toLowerCase();
  if (!p1 || !p2 || !aspect) return null;
  return `${[p1, p2].sort().join('|')}|${aspect}`;
};

const aspectRank = (row) => {
  const orb = Math.abs(parseFloat(row?.orb || 0));
  const richness = ['max_orb', 'allowed_orb', 'phase', 'direction', 'partile', 'complete_platic', 'severity']
    .reduce((count, key) => count + (row?.[key] !== undefined && row?.[key] !== null && row?.[key] !== '' && row?.[key] !== false ? 1 : 0), 0);
  return [Number.isFinite(orb) ? orb : 9999, -richness];
};

export function dedupeAspectRows(rows) {
  const chosen = new Map();
  const passthrough = [];
  for (const raw of Array.isArray(rows) ? rows : []) {
    if (!raw || typeof raw !== 'object') continue;
    const row = { ...raw };
    const key = aspectIdentity(row);
    if (!key) {
      passthrough.push(row);
      continue;
    }
    const prev = chosen.get(key);
    if (!prev) {
      chosen.set(key, row);
      continue;
    }
    const [orbA, richA] = aspectRank(row);
    const [orbB, richB] = aspectRank(prev);
    if (orbA < orbB || (orbA === orbB && richA < richB)) {
      chosen.set(key, row);
    }
  }
  return [...chosen.values(), ...passthrough].sort((a, b) => {
    const [orbA, richA] = aspectRank(a);
    const [orbB, richB] = aspectRank(b);
    if (orbA !== orbB) return orbA - orbB;
    return richA - richB;
  });
}

const formatStandardAspectRows = (rows) => dedupeAspectRows(rows)
  .map((a) => ({
    ...a,
    orb: Number(a.orb),
    symbol: aspectSymbol(a.aspect),
    orb_text: `${Math.abs(parseFloat(a.orb || 0)).toFixed(1)}\u00B0`,
    max_orb: (a.max_orb != null ? Number(a.max_orb) : (a.allowed_orb != null ? Number(a.allowed_orb) : undefined)),
  }));

const formatMorinAspectRows = (rows) => dedupeAspectRows(rows)
  .map((a) => ({
    planet1: a.planet1,
    planet2: a.planet2,
    aspect: a.aspect,
    orb: Number(a.orb),
    max_orb: Number(a.max_orb),
    partile: !!a.partile,
    complete_platic: !!a.complete_platic,
    direction: a.direction,
    phase: a.phase,
    symbol: aspectSymbol(a.aspect),
    orb_text: `${Math.abs(parseFloat(a.orb || 0)).toFixed(2)}\u00B0`,
  }));

const formatDeclinationRows = (rows) => (Array.isArray(rows) ? rows : [])
  .filter((a) => a && typeof a === 'object')
  .map((a) => ({
    ...a,
    orb: Number(a.orb),
    symbol: aspectSymbol(a.aspect === 'parallel' ? 'parallel' : 'antiparallel'),
    orb_text: `${Math.abs(parseFloat(a.orb || 0)).toFixed(2)}\u00B0`,
  }));

const formatMorinShadowRows = (rows, fallbackAspect) => dedupeAspectRows(
  (Array.isArray(rows) ? rows : []).map((row) => ({
    ...row,
    aspect: row?.aspect || fallbackAspect,
  })),
).map((a) => ({
  planet1: a.planet1,
  planet2: a.planet2,
  aspect: a.aspect || fallbackAspect,
  orb: Number(a.orb),
  max_orb: Number(a.max_orb || 1),
  symbol: aspectSymbol(a.aspect || fallbackAspect),
  orb_text: `${Math.abs(parseFloat(a.orb || 0)).toFixed(2)}\u00B0`,
}));

export function transformDashboard(data) {
  if (!data) return { planets: [], moon: null, tightest_aspect: null, dispositors: {} };

  const planets = (data.planets || []).map((p) => ({
    planet: p.planet,
    longitude: p.longitude,
    sign: p.sign,
    house: p.house,
    degree_text: degString(p.longitude || 0),
    dignity_score: p.dignity_score,
    essential_dignity: p.essential_dignity,
    accidental_dignity: p.accidental_dignity,
    dignities: p.dignities,
    retrograde: !!p.retrograde,
  }));

  const standardAspectSource = (Array.isArray(data.planetary_aspects_precise) && data.planetary_aspects_precise.length > 0)
    ? data.planetary_aspects_precise
    : (Array.isArray(data.top_aspects) ? data.top_aspects : (data.tightest_aspect ? [data.tightest_aspect] : []));
  const standardAspects = formatStandardAspectRows(standardAspectSource);
  const rawTight = data.tightest_aspect ? formatStandardAspectRows([data.tightest_aspect])[0] : null;
  const tight = standardAspects[0] || rawTight || null;

  const morinAspects = formatMorinAspectRows(data.morin_aspects);
  const morinAntiscia = formatMorinShadowRows(data.morin_antiscia, 'Antiscia');
  const morinContraAntiscia = formatMorinShadowRows(data.morin_contra_antiscia, 'Contra-antiscia');

  const morinCombustion = Array.isArray(data.morin_combustion) ? data.morin_combustion.map((x) => ({
    planet: x.planet,
    status: x.status,
    distance_deg: Number(x.distance_deg || 0),
    exact_cazimi: !!x.exact_cazimi,
  })) : [];

  const morinPatterns = (data.morin_patterns && typeof data.morin_patterns === 'object') ? data.morin_patterns : null;
  const solar = data.solar_conditions || null;
  const moonTimeline = data.moon_timeline || null;
  const topDecl = formatDeclinationRows(data.top_declinations);
  const lots = data.arabic_parts || {};
  const metrics = data.metrics || null;
  const specialDegrees = Array.isArray(data.special_degrees) ? data.special_degrees : [];
  const cuspAspects = data.cusp_aspects || {};
  const almutens = (data.almutens && typeof data.almutens === 'object') ? data.almutens : { items: [], points: {}, display_order: [], sect: null };
  const asteroids = (data.asteroids && typeof data.asteroids === 'object')
    ? data.asteroids
    : { items: [], missing: [], status: 'unavailable', message: null, ephemeris_available: false };

  return {
    timestamp: data.timestamp,
    location: data.location,
    timezone: data.timezone || null,
    timezone_label: data.timezone_label || null,
    planets,
    moon: data.moon || null,
    tightest_aspect: tight,
    planetary_aspects_precise: standardAspects,
    top_aspects: standardAspects,
    morin_aspects: morinAspects,
    top_declinations: topDecl,
    morin_antiscia: morinAntiscia,
    morin_contra_antiscia: morinContraAntiscia,
    arabic_parts: lots,
    sect: data.sect || null,
    dispositors: data.dispositors || {},
    fixed_star_hits: Array.isArray(data.fixed_star_hits) ? data.fixed_star_hits : [],
    solar_conditions: solar,
    moon_timeline: moonTimeline,
    house_cusps: Array.isArray(data.house_cusps) ? data.house_cusps : [],
    house_rulers: data.house_rulers || {},
    receptions: (data.receptions && typeof data.receptions === 'object') ? data.receptions : null,
    metrics,
    special_degrees: specialDegrees,
    cusp_aspects: cuspAspects,
    almutens,
    asteroids,
    morin_combustion: morinCombustion,
    morin_patterns: morinPatterns,
  };
}
