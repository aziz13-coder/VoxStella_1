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
    'household',
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

export const AXIS_CATEGORY_ALIASES = {
  violence_homicide: ['violence', 'homicide', 'murder', 'death'],
  abduction_missing_person: ['abduction', 'kidnapping', 'missing person', 'missing'],
  deception_coverup: ['deception', 'coverup', 'cover-up', 'staging'],
  domestic_partner_involvement: ['domestic', 'partner', 'spouse', 'relationship'],
  family_involvement: ['family', 'household'],
  child_victim: ['child', 'children'],
  water_disappearance_or_drowning: ['water', 'drowning'],
  accident_or_disaster: ['accident', 'disaster'],
  friend_or_close_associate: ['associates', 'associate', 'friend'],
  authority_or_public_case: ['public', 'authority', 'institution'],
  accomplice_or_witness: ['witness', 'accomplice'],
};

export const DEFAULT_FORENSIC_REPLAY_AXIS_LIMIT = 5;

export function forensicKeywordMatches(blob = '', keyword = '') {
  if (!blob || !keyword) return false;
  const escaped = String(keyword).toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(?<![a-z0-9])${escaped}(?![a-z0-9])`).test(String(blob).toLowerCase());
}

export function forensicTextMatchesAxis(axis = '', text = '', { includeAliases = true } = {}) {
  const blob = String(text || '');
  if (!axis || !blob.trim()) return false;
  const keywords = AXIS_KEYWORDS[axis] || [];
  const aliases = includeAliases ? AXIS_CATEGORY_ALIASES[axis] || [] : [];
  return [...keywords, ...aliases].some((keyword) => forensicKeywordMatches(blob, keyword));
}

export function forensicFindingMatchesAxis(finding = {}, axis = '') {
  if (!finding || typeof finding !== 'object' || !axis) return false;
  return (
    forensicTextMatchesAxis(axis, finding?.category, { includeAliases: true }) ||
    forensicTextMatchesAxis(axis, finding?.title, { includeAliases: false })
  );
}

function flattenSurvivabilityEvidence(survivability = null) {
  const evidence = survivability?.evidence;
  if (!evidence || typeof evidence !== 'object') return [];
  return Object.values(evidence)
    .flatMap((value) => (Array.isArray(value) ? value : [value]))
    .filter(Boolean)
    .map((value) => String(value));
}

export function getForensicReplayTailoring(forensicResult = {}) {
  const survivability = forensicResult?.survivability && typeof forensicResult.survivability === 'object'
    ? forensicResult.survivability
    : null;
  const evidenceText = [
    ...flattenSurvivabilityEvidence(survivability),
    survivability?.note,
    survivability?.outcome_band,
    survivability?.case_type,
  ].filter(Boolean).join(' ').toLowerCase();
  const categories = forensicResult?.categories && typeof forensicResult.categories === 'object'
    ? forensicResult.categories
    : {};
  const fatalPressure = Number(survivability?.breakdown?.fatal_pressure || 0);
  const outcomeBand = String(survivability?.outcome_band || '');
  const caseType = String(survivability?.case_type || '');

  return {
    hasServerSummary: Boolean(survivability?.level),
    fatalPressureDominant: outcomeBand === 'fatal_pressure_dominant' || fatalPressure >= 4.5,
    domesticFatalContext: (
      evidenceText.includes('family/household fatal-harm mechanism') ||
      evidenceText.includes('domestic/known-person fatal context')
    ),
    abductionContext: (
      Number(categories.Abduction || 0) > 0 &&
      !evidenceText.includes('domestic/known-person fatal context')
    ),
    transportFatalContext: evidenceText.includes('transport crash/impact mechanism'),
    knownPersonViolenceContext: evidenceText.includes('known-person violent injury mechanism'),
    fatalViolenceContext: (
      evidenceText.includes('homicide testimony') ||
      evidenceText.includes('life/death overlap') ||
      Number(categories.Violence || 0) > 0
    ),
    waterContext: evidenceText.includes('drowning testimony') || Number(categories.Water || 0) > 0,
    childContext: caseType === 'child' || Number(categories.Children || 0) > 0,
    childWitnessViolenceContext: evidenceText.includes('child/witness violent-event mechanism'),
  };
}

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
  const tailoring = getForensicReplayTailoring(forensicResult);
  const limit = tailoring.hasServerSummary ? Math.min(3, DEFAULT_FORENSIC_REPLAY_AXIS_LIMIT) : DEFAULT_FORENSIC_REPLAY_AXIS_LIMIT;
  const findings = Array.isArray(forensicResult?.findings) ? forensicResult.findings : [];
  const categories = forensicResult?.categories && typeof forensicResult.categories === 'object'
    ? forensicResult.categories
    : {};
  const hasCategoryRollup = Object.keys(categories).length > 0;
  const axisOrder = Object.keys(AXIS_KEYWORDS);
  const axisScores = new Map();
  const suppressedAxes = new Set();

  if (tailoring.domesticFatalContext) {
    suppressedAxes.add('abduction_missing_person');
    suppressedAxes.add('water_disappearance_or_drowning');
    suppressedAxes.add('deception_coverup');
  }
  if (tailoring.abductionContext) {
    suppressedAxes.add('deception_coverup');
  }
  if (tailoring.transportFatalContext) {
    suppressedAxes.add('authority_or_public_case');
    suppressedAxes.add('deception_coverup');
  }

  const addScore = (axis, weight, sourceIndex = 999) => {
    if (suppressedAxes.has(axis)) return;
    if (!axis || !Number.isFinite(weight) || weight <= 0) return;
    const previous = axisScores.get(axis) || { score: 0, firstSourceIndex: sourceIndex };
    axisScores.set(axis, {
      score: previous.score + weight,
      firstSourceIndex: Math.min(previous.firstSourceIndex, sourceIndex),
    });
  };

  if (tailoring.fatalPressureDominant) addScore('violence_homicide', 9, -10);
  if (tailoring.domesticFatalContext) {
    addScore('violence_homicide', 10, -10);
    addScore('family_involvement', 8, -10);
    addScore('domestic_partner_involvement', 7, -10);
  }
  if (tailoring.knownPersonViolenceContext) addScore('violence_homicide', 5, -9);
  if (tailoring.fatalViolenceContext) addScore('violence_homicide', 6, -9);
  if (tailoring.transportFatalContext) addScore('accident_or_disaster', 8, -9);
  if (tailoring.waterContext) addScore('water_disappearance_or_drowning', 6, -9);
  if (tailoring.abductionContext) addScore('abduction_missing_person', 7, -9);
  if (tailoring.childContext) addScore('child_victim', 6, -8);
  if (tailoring.childWitnessViolenceContext) addScore('accomplice_or_witness', 5, -8);

  Object.keys(categories).forEach((category) => {
    axisOrder.forEach((axis) => {
      if (forensicTextMatchesAxis(axis, category, { includeAliases: true })) addScore(axis, 3, -1);
    });
  });

  findings.forEach((finding, index) => {
    if (!finding || typeof finding !== 'object') return;
    const title = finding?.title || '';
    const category = finding?.category || '';
    const rationale = finding?.rationale || '';

    axisOrder.forEach((axis) => {
      const hadAxis = axisScores.has(axis);
      if (forensicTextMatchesAxis(axis, category, { includeAliases: true })) addScore(axis, hasCategoryRollup ? 1 : 4, index);
      if (forensicTextMatchesAxis(axis, title, { includeAliases: false })) addScore(axis, 3, index);

      // Rationale prose is useful context, but too broad for creating new visible axes.
      // It can only reinforce an axis already present in the title/category signal.
      if ((hadAxis || axisScores.has(axis)) && forensicTextMatchesAxis(axis, rationale, { includeAliases: false })) {
        addScore(axis, 1, index);
      }
    });
  });

  return Array.from(axisScores.entries())
    .filter(([, value]) => value.score >= 3)
    .sort(([leftAxis, left], [rightAxis, right]) => {
      if (right.score !== left.score) return right.score - left.score;
      if (left.firstSourceIndex !== right.firstSourceIndex) return left.firstSourceIndex - right.firstSourceIndex;
      return axisOrder.indexOf(leftAxis) - axisOrder.indexOf(rightAxis);
    })
    .slice(0, limit)
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
