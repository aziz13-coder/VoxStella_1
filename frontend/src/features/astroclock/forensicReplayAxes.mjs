export const AXIS_KEYWORDS = {
  violence_homicide: [
    'murder',
    'homicide',
    'violent',
    'violence',
    'death',
    'killing',
    'blunt force',
    'strangulation',
    'gunshot',
    'stab',
  ],
  abduction_missing_person: [
    'abduction',
    'kidnapping',
    'missing',
    'disappearance',
    'taken',
  ],
  deception_coverup: [
    'deception',
    'cover-up',
    'coverup',
    'lie',
    'lies',
    'staged',
    'conceal',
    'concealment',
    'hidden',
  ],
  domestic_partner_involvement: [
    'spouse',
    'wife',
    'husband',
    'partner',
    'relationship',
    'domestic',
    '7th house',
  ],
  family_involvement: [
    'family',
    'mother',
    'father',
    'parent',
    'parents',
    'home',
    'domestic',
  ],
  child_victim: [
    'child',
    'children',
    'baby',
    'infant',
    'daughter',
    'son',
    '5th house',
  ],
  water_disappearance_or_drowning: [
    'water',
    'drowning',
    'marina',
    'sea',
    'boat',
    'harbor',
    'fluids',
  ],
  accident_or_disaster: [
    'accident',
    'disaster',
    'mechanical',
    'unintentional',
    'natural',
    'catastrophic accident',
  ],
  friend_or_close_associate: [
    'friend',
    'close associate',
    'acquaintance',
    'known to',
  ],
  authority_or_public_case: [
    'public',
    'authority',
    'institution',
    'celebrity',
    'leader',
    'law',
    'police',
  ],
  accomplice_or_witness: [
    'accomplice',
    'witness',
    'helper',
    'two perpetrators',
    'more than one',
  ],
};

export function buildForensicResultTextBlob(forensicResult = {}, { includeRationales = true } = {}) {
  const findings = Array.isArray(forensicResult?.findings) ? forensicResult.findings : [];
  const categories = forensicResult?.categories && typeof forensicResult.categories === 'object'
    ? forensicResult.categories
    : {};
  const dominance = forensicResult?.dominance && typeof forensicResult.dominance === 'object'
    ? forensicResult.dominance
    : {};
  const textParts = [];

  findings.forEach((finding) => {
    if (!finding || typeof finding !== 'object') return;
    const keys = includeRationales ? ['title', 'category', 'rationale'] : ['title', 'category'];
    keys.forEach((key) => {
      const value = finding[key];
      if (value) textParts.push(String(value));
    });
  });

  Object.keys(categories).forEach((key) => textParts.push(String(key)));

  Object.entries(dominance).forEach(([key, value]) => {
    textParts.push(String(key));
    if (value && typeof value === 'object') {
      Object.values(value).forEach((sub) => {
        if (sub) textParts.push(String(sub));
      });
    }
  });

  return textParts.join(' ').toLowerCase();
}

export function deriveForensicReplayAxes(forensicResult = {}) {
  const blob = buildForensicResultTextBlob(forensicResult, { includeRationales: true });
  return Object.entries(AXIS_KEYWORDS)
    .filter(([, keywords]) => keywords.some((keyword) => blob.includes(String(keyword).toLowerCase())))
    .map(([axis]) => axis);
}

export function formatForensicDisplayLabel(value = '') {
  return String(value || '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export function cleanForensicDisplayText(value = '') {
  return String(value || '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
