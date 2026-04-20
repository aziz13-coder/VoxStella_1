const SIGNS = [
  'Aries',
  'Taurus',
  'Gemini',
  'Cancer',
  'Leo',
  'Virgo',
  'Libra',
  'Scorpio',
  'Sagittarius',
  'Capricorn',
  'Aquarius',
  'Pisces',
];

const MOJIBAKE_REPLACEMENTS = [
  ['вЂ”', '-'],
  ['вЂ“', '-'],
  ['вЂ‘', '-'],
  ['в€’', '-'],
  ['в†’', '->'],
  ['в‡’', '->'],
  ['вЂ™', "'"],
  ['вЂ˜', "'"],
  ['вЂњ', '"'],
  ['вЂќ', '"'],
  ['вЂ¦', '...'],
  ['вЂ‚', ' '],
  ['вЂ‰', ' '],
];

const LOCATION_RULES = [
  { id: 'work_service', label: 'work or service site', patterns: [/work/, /service/, /coworker/, /office/, /clerical/, /cleaning/, /laundry/, /job site/] },
  { id: 'medical', label: 'medical or institutional care site', patterns: [/clinic/, /pharmac/, /hospital/, /asylum/, /medical/] },
  { id: 'hospitality', label: 'hospitality or short-stay lodging', patterns: [/hotel/, /hostel/, /lodgings?/] },
  { id: 'water', label: 'waterside or waterfront', patterns: [/waterfront/, /near water/, /\bwells?\b/, /\bboat\b/, /marina/, /harbor/] },
  { id: 'confusion', label: 'confusing or low-clarity setting', patterns: [/lost/, /missing/, /confusing/, /ambiguous/, /distance by confusion/] },
  { id: 'hidden', label: 'hidden or controlled-access area', patterns: [/hidden/, /enclosed/, /prisons?/, /confinement/, /surveillance/, /secret enem/, /eavesdropping/, /access.?controlled/, /restricted/, /basements?\/cellars?/, /sewers?\/drains?/, /cemeter(y|ies)\/mortuar/, /trash\/dumps/] },
  { id: 'vice', label: 'hidden or vice-linked area', patterns: [/sex venues?/] },
  { id: 'records', label: 'office, records, or small-room trail', patterns: [/records?/, /documents?/, /signage/, /small rooms?/, /storage/] },
  { id: 'infrastructure', label: 'technical or infrastructure site', patterns: [/\blabs?\b/, /servers?/, /airfields?\/towers?/, /power lines?\/grids?/] },
  { id: 'route', label: 'road, vehicle, or transit route', patterns: [/vehicle/, /transit/, /roads?/, /side streets?/, /intersections?/, /buses?/, /courier/, /highways?/, /bridges?/, /transport/, /yard\/outside/, /front\/entrances?/] },
  { id: 'public', label: 'public or authority-facing place', patterns: [/public/, /authorit/, /government/, /courts?/, /legal/, /embassy/, /out in the open/] },
  { id: 'social', label: 'social or entertainment venue', patterns: [/bars?/, /clubs?/, /parties?/, /recreation/, /entertainment/, /playgrounds?/, /parks?/, /sports\/gyms?/, /stage/, /theater/, /fashion/, /beauty/, /children\/entertainment/] },
  { id: 'visibility', label: 'public or high-visibility place', patterns: [/celebrity\/spotlight/, /gold\/luxury/, /visible\/high places?/] },
  { id: 'home', label: 'home or residential threshold', patterns: [/home/, /residence/, /front door/, /family base/, /threshold/, /domestic/] },
  { id: 'long_range', label: 'campus, press, or long-distance corridor', patterns: [/universit/, /college/, /foreign/, /international/, /publishing\/press/, /long distance/, /jurisdiction/] },
  { id: 'industrial', label: 'industrial or workshop area', patterns: [/workshops?/, /garages?/, /industrial/, /construction/, /metal\/tools/] },
  { id: 'garden', label: 'garden or courtyard', patterns: [/gardens?\/fields?/] },
  { id: 'group', label: 'group or community setting', patterns: [/friends?\/groups?\/clubs/, /community events/, /large gatherings/, /clubs\/groups/, /group/] },
  { id: 'valuables', label: 'valuables or personal-effects trail', patterns: [/wallet/, /jewelry/, /\bcash\b/, /possessions?/, /valuables?/, /cash\/banks/] },
  { id: 'kitchen', label: 'food service or kitchen area', patterns: [/food\/kitchens?/, /\bkitchens?\b/] },
  { id: 'substances', label: 'substance-linked or disorienting setting', patterns: [/drugs?/, /alcohol/] },
];

const MODIFIER_RULES = [
  { id: 'hospitality_distance', label: 'hospitality or waterside', patterns: [/hotel/, /hostel/, /waterfront/, /waterside/] },
  { id: 'confusion_distance', label: 'confusion or low-clarity distance', patterns: [/lost/, /missing/, /ambiguous/, /confusion/] },
  { id: 'far_distance', label: 'farther or jurisdiction-linked distance', patterns: [/farther/, /highway/, /jurisdiction/, /distance/] },
  { id: 'campus_distance', label: 'campus or university corridor', patterns: [/campus\/university/, /campus/, /university/] },
  { id: 'hidden_distance', label: 'hidden or access-controlled approach', patterns: [/secrecy/, /hidden enemies/, /access.?controlled/] },
];

const DISTANCE_RULES = [
  { id: 'local_route', label: 'local route or neighborhood movement', patterns: [/local area\/roads/, /local/, /roads/] },
  { id: 'far_range', label: 'farther or long-range movement', patterns: [/far\/long distance/, /far\/distant/, /far range/, /long distance/] },
  { id: 'near_slow', label: 'nearby or slower access', patterns: [/near\/slow/, /nearby/, /near\/slow\/protective/] },
  { id: 'fast_sudden', label: 'fast or sudden movement', patterns: [/sudden\/fast/, /fast\/early/, /sudden\/early\/fast/, /sudden/] },
];

const LOCATION_BEARING_HOUSES = new Set([1, 3, 4, 5, 6, 9, 10, 11, 12]);
const IGNORED_LOCATION_PATTERNS = [
  /^family$/,
  /^heat$/,
  /^slow\/nearby$/,
  /^sudden\/early\/fast$/,
  /^long distance\/far$/,
  /^protective\/hidden at home$/,
];

function signFromLongitude(lon = 0) {
  const n = ((Math.floor(lon / 30)) % 12 + 12) % 12;
  return SIGNS[n];
}

export function normalizeAbductionCueText(value = '') {
  let out = String(value || '');
  for (const [from, to] of MOJIBAKE_REPLACEMENTS) {
    out = out.split(from).join(to);
  }
  return out
    .replace(/[—–]/g, '-')
    .replace(/\s+/g, ' ')
    .replace(/\s*->\s*/g, ' -> ')
    .replace(/\s*\/\s*/g, ' / ')
    .replace(/\s*-\s*>\s*/g, ' -> ')
    .replace(/->\s+([A-Za-z-]+)\s+\/\s+([A-Za-z-]+)/g, '-> $1/$2')
    .trim();
}

function canonicalizeText(value, rules) {
  const cleaned = normalizeAbductionCueText(value);
  const lower = cleaned.toLowerCase();
  const matchable = lower.replace(/\s*\/\s*/g, '/');
  if (IGNORED_LOCATION_PATTERNS.some((pattern) => pattern.test(matchable))) {
    return null;
  }
  for (const rule of rules) {
    if (rule.patterns.some((pattern) => pattern.test(matchable))) {
      return { id: rule.id, label: rule.label };
    }
  }
  return { id: lower, label: cleaned };
}

function canonicalizeLocationCue(value) {
  return canonicalizeText(value, LOCATION_RULES);
}

function canonicalizeModifier(value) {
  return canonicalizeText(value, MODIFIER_RULES);
}

function canonicalizeDistanceCue(value) {
  return canonicalizeText(value, DISTANCE_RULES);
}

function dedupeCanonical(values, mapper, limit = 4, excludeIds = new Set()) {
  const out = [];
  const seen = new Set();
  for (const raw of Array.isArray(values) ? values : []) {
    if (!raw) continue;
    const item = mapper(raw);
    if (!item?.label || excludeIds.has(item.id) || seen.has(item.id)) continue;
    seen.add(item.id);
    out.push(item);
    if (out.length >= limit) break;
  }
  return out;
}

function formatAnchor(planet, sign, house) {
  if (!planet && !sign && (house == null)) return 'none';
  const bits = [];
  if (planet) bits.push(String(planet));
  if (sign) bits.push(`in ${sign}`);
  if (house != null) bits.push(`(H${house})`);
  return bits.join(' ');
}

function tierKeyForHouse(house) {
  const n = Number(house);
  if (n === 6 || n === 12) return 'D';
  if (n === 9) return 'C';
  if (n === 1 || n === 4) return 'A';
  return 'B';
}

function strongestTierKey(houses = []) {
  const order = { A: 1, B: 2, C: 3, D: 4 };
  return (houses || [])
    .map((house) => tierKeyForHouse(house))
    .sort((a, b) => (order[b] || 0) - (order[a] || 0))[0] || 'B';
}

function listFor(dict, key, nestedKey) {
  if (!dict || key == null) return [];
  const value = nestedKey == null ? dict[key] : dict?.[nestedKey]?.[key];
  return Array.isArray(value) ? value : [];
}

function listForLocationHouse(dict, house) {
  const num = Number(house);
  if (!LOCATION_BEARING_HOUSES.has(num)) return [];
  return listFor(dict, String(num));
}

export function buildAbductionCueSummary({ data, features } = {}) {
  const dict = data?.abduction_location || {};
  const signsMap = dict?.signs || {};
  const housesMap = dict?.houses || {};
  const rulers = features?.house_rulers || {};
  const firstRuler = features?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
  const firstInfo = firstRuler ? (features?.planets?.[firstRuler] || {}) : {};
  const moonInfo = features?.planets?.Moon || {};
  const cusp1 = Number(features?.house_cusps?.[0]);
  const ascSign = Number.isFinite(cusp1) ? signFromLongitude(cusp1) : null;
  const primarySign = firstInfo?.sign || ascSign || null;
  const primaryHouse = firstInfo?.house != null ? firstInfo.house : 1;
  const moonSign = moonInfo?.sign || null;
  const moonHouse = moonInfo?.house != null ? moonInfo.house : null;

  const primaryHouseCues = dedupeCanonical(listForLocationHouse(housesMap, primaryHouse), canonicalizeLocationCue, 3);
  const primarySignCues = dedupeCanonical(
    listFor(signsMap, primarySign),
    canonicalizeLocationCue,
    3,
    new Set(primaryHouseCues.map((item) => item.id)),
  );
  const movementHouseCues = dedupeCanonical(
    listForLocationHouse(housesMap, moonHouse),
    canonicalizeLocationCue,
    3,
    new Set([...primaryHouseCues, ...primarySignCues].map((item) => item.id)),
  );
  const movementSignCues = dedupeCanonical(
    listFor(signsMap, moonSign),
    canonicalizeLocationCue,
    3,
    new Set([...primaryHouseCues, ...primarySignCues, ...movementHouseCues].map((item) => item.id)),
  );

  const accessNotes = dedupeCanonical(
    [
      ...listForLocationHouse(housesMap, primaryHouse),
      ...listForLocationHouse(housesMap, moonHouse),
    ],
    canonicalizeLocationCue,
    4,
  );

  const distCuesRaw = [];
  const primaryAndMoonSigns = [primarySign, moonSign].filter(Boolean);
  const signLists = [
    ...listFor(signsMap, primarySign),
    ...listFor(signsMap, moonSign),
  ];
  signLists.forEach((cue) => {
    const lower = String(cue || '').toLowerCase();
    if (/long distance|far/.test(lower)) distCuesRaw.push('far/long distance');
    if (/slow|nearby/.test(lower)) distCuesRaw.push('near/slow');
    if (/sudden|fast|early/.test(lower)) distCuesRaw.push('sudden/fast');
  });
  if (Number(primaryHouse) === 3 || Number(moonHouse) === 3) distCuesRaw.push('local area/roads');
  if (Number(primaryHouse) === 9 || Number(moonHouse) === 9) distCuesRaw.push('far/distant');
  if (primaryAndMoonSigns.some((sign) => sign === 'Sagittarius' || sign === 'Aquarius')) distCuesRaw.push('fast/early or far range');
  if (primaryAndMoonSigns.some((sign) => sign === 'Taurus' || sign === 'Cancer')) distCuesRaw.push('near/slow/protective');
  const distanceCues = dedupeCanonical(distCuesRaw, canonicalizeDistanceCue, 3);

  const distanceModifiers = [];
  const modifierSet = dict?.distance_modifiers || {};
  if (primaryAndMoonSigns.includes('Sagittarius') || Number(primaryHouse) === 9 || Number(moonHouse) === 9) {
    distanceModifiers.push(...(modifierSet.Sagittarius_or_9th || []));
  }
  if (primaryAndMoonSigns.includes('Pisces')) {
    distanceModifiers.push(...(modifierSet.Pisces_or_Neptune || []));
  }
  if (primaryAndMoonSigns.includes('Scorpio') || Number(primaryHouse) === 12 || Number(moonHouse) === 12) {
    distanceModifiers.push(...(modifierSet.Scorpio_or_12th || []));
  }
  const modifiers = dedupeCanonical(distanceModifiers, canonicalizeModifier, 3);

  const tierKey = strongestTierKey([primaryHouse, moonHouse]);
  const tierTitle = normalizeAbductionCueText(dict?.tiers?.[tierKey]?.title || `Tier ${tierKey}`);

  return {
    firstRuler,
    primarySign,
    primaryHouse,
    moonSign,
    moonHouse,
    victimAnchor: formatAnchor(firstRuler, primarySign, primaryHouse),
    movementAnchor: formatAnchor('Moon', moonSign, moonHouse),
    primaryHouseCues: primaryHouseCues.map((item) => item.label),
    primarySignCues: primarySignCues.map((item) => item.label),
    movementCues: [...movementHouseCues, ...movementSignCues].map((item) => item.label).slice(0, 3),
    accessProfile: {
      key: tierKey,
      title: tierTitle,
    },
    accessNotes: accessNotes.map((item) => item.label),
    distanceCues: distanceCues.map((item) => item.label),
    modifiers: modifiers.map((item) => item.label),
  };
}

export function buildAbductionCueReportLines(args = {}) {
  const summary = buildAbductionCueSummary(args);
  const lines = [
    'Abduction cues',
    `Victim signal: ${summary.victimAnchor}`,
    `Movement signal: ${summary.movementAnchor}`,
  ];
  if (summary.primaryHouseCues.length) {
    lines.push(`Primary place cues: ${summary.primaryHouseCues.join('; ')}`);
  }
  if (summary.primarySignCues.length) {
    lines.push(`Scene modifiers: ${summary.primarySignCues.join('; ')}`);
  }
  if (summary.movementCues.length) {
    lines.push(`Route and movement cues: ${summary.movementCues.join('; ')}`);
  }
  lines.push(`Access and distance: ${summary.accessProfile.title}`);
  if (summary.accessNotes.length) {
    lines.push(`Access notes: ${summary.accessNotes.join('; ')}`);
  }
  if (summary.distanceCues.length) {
    lines.push(`Distance read: ${summary.distanceCues.join('; ')}`);
  }
  if (summary.modifiers.length) {
    lines.push(`Context modifiers: ${summary.modifiers.join('; ')}`);
  }
  return lines;
}
