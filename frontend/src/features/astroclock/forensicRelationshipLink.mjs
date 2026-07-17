import { deriveForensicReplayAxes } from './forensicReplayAxes.mjs';

function relationshipTypeFromStatusLabel(label = '') {
  switch (String(label || '').trim()) {
    case 'intimate_partner':
      return 'Intimate/partner-linked';
    case 'family':
      return 'Family-linked';
    case 'friend_acquaintance':
      return 'Friend/associate link';
    case 'stranger_public':
      return 'Stranger/Random';
    default:
      return null;
  }
}

export function summarizeForensicRelationshipLink({
  score = 0,
  victimHouse = null,
  perpHouse = null,
  seventhHousePlanets = [],
  isMutual = false,
  forensicResult = {},
} = {}) {
  const normalizedVictimHouse = Number(victimHouse);
  const normalizedPerpHouse = Number(perpHouse);
  const axes = new Set(deriveForensicReplayAxes(forensicResult));
  const seventhPlanets = Array.isArray(seventhHousePlanets) ? seventhHousePlanets : [];
  const relationshipStatus = forensicResult?.relationship_status;
  if (relationshipStatus && typeof relationshipStatus === 'object' && relationshipStatus.primary_label) {
    const labels = Array.isArray(relationshipStatus.labels) ? relationshipStatus.labels : [];
    const labelSet = new Set(labels);
    return {
      relationshipType: relationshipTypeFromStatusLabel(relationshipStatus.primary_label) || 'Stranger/Random',
      confidence: relationshipStatus.confidence || (relationshipStatus.primary_label === 'stranger_public' ? 'Moderate' : 'Low'),
      axes: Array.from(axes),
      familyLinked: labelSet.has('family'),
      intimatePartnerLinked: labelSet.has('intimate_partner'),
      associateLinked: labelSet.has('friend_acquaintance'),
      publicLinked: axes.has('authority_or_public_case'),
      serviceLinked: false,
      relationshipStatus,
    };
  }

  const familyLinked =
    (normalizedVictimHouse === 4 && normalizedPerpHouse === 4) ||
    (normalizedVictimHouse === 10 && normalizedPerpHouse === 10);
  const hasExchange =
    (normalizedVictimHouse === 1 && normalizedPerpHouse === 7) ||
    (normalizedVictimHouse === 7 && normalizedPerpHouse === 1);
  const intimatePartnerLinked =
    hasExchange &&
    (isMutual || seventhPlanets.includes('Venus') || seventhPlanets.includes('Moon'));
  const associateLinked =
    axes.has('friend_or_close_associate') || normalizedPerpHouse === 11;
  const publicLinked = axes.has('authority_or_public_case');
  const serviceLinked = normalizedPerpHouse === 6;

  let relationshipType = 'Stranger/Random';
  if (familyLinked) relationshipType = 'Family-linked';
  else if (intimatePartnerLinked) relationshipType = 'Intimate/partner-linked';
  else if (associateLinked && publicLinked) relationshipType = 'Associate/public-network link';
  else if (associateLinked) relationshipType = 'Friend/associate link';
  else if (publicLinked) relationshipType = 'Authority/public-case link';
  else if (serviceLinked) relationshipType = 'Service/subordinate link';
  else if (score >= 8) relationshipType = 'Strong non-random connection';
  else if (score >= 6) relationshipType = 'Known/close connection';
  else if (score >= 4) relationshipType = 'Known person';
  else if (score >= 2) relationshipType = 'Acquaintance';

  let confidence = 'Very Low';
  if (familyLinked || intimatePartnerLinked) confidence = score >= 8 ? 'High' : score >= 5 ? 'Moderate' : 'Low';
  else if (associateLinked || publicLinked || serviceLinked) confidence = score >= 8 ? 'Moderate' : 'Low';
  else if (score >= 8) confidence = 'Moderate';
  else if (score >= 4) confidence = 'Low';

  return {
    relationshipType,
    confidence,
    axes: Array.from(axes),
    familyLinked,
    intimatePartnerLinked,
    associateLinked,
    publicLinked,
    serviceLinked,
  };
}

function normalizedAspectType(aspectType = null, aspect = null) {
  return String(aspectType || aspect?.type || aspect?.aspect || '').trim().toLowerCase();
}

function isApplyingAspect(applyingAspect = false, aspect = null) {
  if (applyingAspect === true) return true;
  if (aspect?.applying === true) return true;
  return String(aspect?.phase || '').trim().toLowerCase() === 'applying';
}

const LIGHT_MEDIATION_SOFT_ASPECTS = new Set(['trine', 'sextile']);
const LIGHT_MEDIATION_HARD_ASPECTS = new Set(['square', 'opposition']);
const LIGHT_MEDIATION_MALEFICS = new Set(['Mars', 'Saturn']);
const LIGHT_MEDIATION_BENEFICS = new Set(['Venus', 'Jupiter']);

function normalizedPlanetName(value = null) {
  const text = String(value || '').trim();
  if (!text) return '';
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function collectLightMediationPoints(value, out = new Set()) {
  if (value == null) return out;
  if (typeof value === 'string') {
    const text = normalizedPlanetName(value);
    if (text) out.add(text);
    return out;
  }
  if (Array.isArray(value)) {
    value.forEach((item) => collectLightMediationPoints(item, out));
    return out;
  }
  if (typeof value === 'object') {
    [
      'planet',
      'name',
      'from',
      'to',
      'middle',
      'target',
      'translator',
      'collector',
      'prohibitor',
      'frustrating',
      'frustrated',
      'swift_extreme',
      'receiving_extreme',
      'planet1',
      'planet2',
    ].forEach((key) => collectLightMediationPoints(value?.[key], out));
    collectLightMediationPoints(value?.participants, out);
    collectLightMediationPoints(value?.collected, out);
    collectLightMediationPoints(value?.legs, out);
    collectLightMediationPoints(value?.from_leg, out);
    collectLightMediationPoints(value?.to_leg, out);
  }
  return out;
}

function lightMediationLegs(lightMediation = {}) {
  const legs = [];
  const seen = new Set();
  const add = (value) => {
    if (!value) return;
    if (Array.isArray(value)) {
      value.forEach(add);
      return;
    }
    if (typeof value !== 'object') return;
    if (value.aspect || value.type || value.orb != null || value.phase) {
      const signature = [
        String(value.aspect || value.type || '').trim().toLowerCase(),
        String(value.orb ?? ''),
        String(value.phase || '').trim().toLowerCase(),
      ].join('|');
      if (!seen.has(signature)) {
        seen.add(signature);
        legs.push(value);
      }
      return;
    }
    add(value.legs);
    add(value.from_leg);
    add(value.to_leg);
  };
  add(lightMediation.legs);
  add(lightMediation.from_leg);
  add(lightMediation.to_leg);
  return legs;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export function scoreLightMediationRelationshipImpact(
  lightMediation = null,
  {
    victimSignificators = [],
    perpetratorSignificators = [],
  } = {},
) {
  const empty = {
    kind: 'none',
    role: 'none',
    mediator: null,
    scoreDelta: 0,
    evidence: [],
  };
  if (!lightMediation || typeof lightMediation !== 'object') return empty;

  const hasProhibition = Boolean(lightMediation.prohibition || lightMediation.denial_type);
  const hasTranslation = Boolean(lightMediation.translation);
  const hasCollection = Boolean(lightMediation.collection);
  if (!hasProhibition && !hasTranslation && !hasCollection) return empty;

  const kind = hasProhibition ? 'prohibition' : (hasTranslation ? 'translation' : 'collection');
  const mediator = normalizedPlanetName(
    lightMediation.translator ||
    lightMediation.collector ||
    lightMediation.prohibitor ||
    lightMediation.frustrating ||
    lightMediation.middle,
  ) || null;
  const points = collectLightMediationPoints(lightMediation);
  const victimPoints = new Set([...victimSignificators, 'Moon'].map(normalizedPlanetName).filter(Boolean));
  const perpetratorPoints = new Set(perpetratorSignificators.map(normalizedPlanetName).filter(Boolean));
  const touchesVictim = [...victimPoints].some((point) => points.has(point));
  const touchesPerpetrator = [...perpetratorPoints].some((point) => points.has(point));
  const role = touchesVictim && touchesPerpetrator
    ? 'victim_perpetrator_bridge'
    : touchesVictim
      ? 'victim_only'
      : touchesPerpetrator
        ? 'perpetrator_only'
        : points.size
          ? 'third_party_only'
          : 'unknown';

  if (role !== 'victim_perpetrator_bridge') {
    return {
      kind,
      role,
      mediator,
      scoreDelta: 0,
      evidence: ['Light mediation lacks victim-perpetrator bridge'],
    };
  }

  if (hasProhibition) {
    return {
      kind,
      role,
      mediator,
      scoreDelta: -1,
      evidence: ['Light prohibition blocks victim/perpetrator perfection'],
    };
  }

  let delta = kind === 'translation' ? 1.25 : 1.0;
  const evidence = [
    kind === 'translation'
      ? 'Translation of light bridges victim/perpetrator significators'
      : 'Collection of light gathers victim/perpetrator significators',
  ];

  if (lightMediation.favorable === false || (lightMediation.challenge_reasons || []).length) {
    delta -= 0.5;
    evidence.push('light mediation challenged');
  }
  if (mediator && LIGHT_MEDIATION_MALEFICS.has(mediator)) {
    delta -= 0.25;
    evidence.push(`${mediator} mediator is malefic`);
  } else if (mediator && LIGHT_MEDIATION_BENEFICS.has(mediator)) {
    delta += 0.15;
    evidence.push(`${mediator} mediator is benefic`);
  }

  lightMediationLegs(lightMediation).forEach((leg) => {
    const aspect = String(leg.aspect || leg.type || '').trim().toLowerCase().replace(/\s+/g, '_');
    if (LIGHT_MEDIATION_SOFT_ASPECTS.has(aspect)) delta += 0.1;
    else if (LIGHT_MEDIATION_HARD_ASPECTS.has(aspect)) delta -= 0.25;
  });

  return {
    kind,
    role,
    mediator,
    scoreDelta: Number(clamp(delta, 0, 1.5).toFixed(2)),
    evidence,
  };
}

export function collectRelationshipAspectContacts({
  aspects = {},
  source = null,
  target = null,
  applyingLabel = ' applying',
} = {}) {
  if (!source || !target || !aspects || typeof aspects !== 'object') return [];
  const sourceName = String(source);
  const targetName = String(target);
  const acceptedKeys = new Set([
    `${sourceName}_to_${targetName}`,
    `${targetName}_to_${sourceName}`,
  ]);
  const seen = new Set();
  const out = [];

  Object.entries(aspects).forEach(([key, aspect]) => {
    if (!acceptedKeys.has(key) || !aspect) return;
    const type = normalizedAspectType(null, aspect) || 'contact';
    const applying = isApplyingAspect(false, aspect);
    const orb = aspect?.orb != null && Number.isFinite(Number(aspect.orb))
      ? Number(aspect.orb).toFixed(3)
      : '';
    const exact = aspect?.degrees_to_exact != null && Number.isFinite(Number(aspect.degrees_to_exact))
      ? Number(aspect.degrees_to_exact).toFixed(3)
      : '';
    const signature = `${type}|${applying}|${orb}|${exact}`;
    if (seen.has(signature)) return;
    seen.add(signature);
    out.push(`${type}${applying ? applyingLabel : ''}`);
  });

  return out;
}

export function scoreForensicRelationshipLink({
  victimHouse = null,
  perpHouse = null,
  sameHouse = null,
  directVictRulesPerp = false,
  directPerpRulesVict = false,
  isMutual = false,
  level3 = false,
  level4VictimInExaltOfPerp = false,
  level4PerpInExaltOfVictim = false,
  level4VictimInFallOfPerp = false,
  level4PerpInFallOfVictim = false,
  directionalReception = false,
  level5Terms = false,
  criticalFamilyHouse = false,
  lightMediation = null,
  seventhHousePlanets = [],
  aspectType = null,
  aspect = null,
  applyingAspect = false,
  criticalDegree = false,
  hasViolentStar = false,
  hasProtectiveStar = false,
  moonDispositorTiesPerp = false,
  moonDispositorHardContact = false,
  victimSignificators = [],
  perpetratorSignificators = [],
} = {}) {
  const victim = Number(victimHouse);
  const perpetrator = Number(perpHouse);
  const rulersShareHouse = sameHouse == null
    ? victimHouse != null && perpHouse != null && victim === perpetrator
    : Boolean(sameHouse);
  const seventhPlanets = Array.isArray(seventhHousePlanets) ? seventhHousePlanets : [];
  const aspectLabel = normalizedAspectType(aspectType, aspect);
  const applying = isApplyingAspect(applyingAspect, aspect);
  const lightMediationImpact = scoreLightMediationRelationshipImpact(lightMediation, {
    victimSignificators,
    perpetratorSignificators,
  });

  let score = 0;
  const reasons = [];

  if (victim === 7) { score += 2; reasons.push('Victim ruler in 7th (+2)'); }
  if (perpetrator === 1) { score += 2; reasons.push('Perp ruler in 1st (+2)'); }
  if (perpetrator === 7) { score += 1; reasons.push('Perp ruler in 7th (+1)'); }
  if (rulersShareHouse) { score += 2; reasons.push('Both rulers in same house (+2)'); }
  if ([1, 4, 7, 10].includes(victim) && [1, 4, 7, 10].includes(perpetrator)) {
    score += 1;
    reasons.push('Both rulers angular (+1)');
  }
  if (directVictRulesPerp) { score += 3; reasons.push('Victim ruler rules perpetrator sign'); }
  if (directPerpRulesVict) { score += 3; reasons.push('Perp ruler rules victim sign'); }
  if (moonDispositorTiesPerp) {
    score += moonDispositorHardContact ? 3 : 2;
    reasons.push(
      moonDispositorHardContact
        ? 'Moon dispositor hard-linked to perpetrator ruler'
        : 'Moon dispositor linked to perpetrator ruler',
    );
  }
  if (isMutual) { score += 4; reasons.push('Mutual reception'); }
  if (level3) { score += 2; reasons.push('Shared triplicity'); }
  if (level4VictimInExaltOfPerp) { score += 2; reasons.push('Victim in exaltation of perpetrator'); }
  if (level4PerpInExaltOfVictim) { score += 2; reasons.push('Perp in exaltation of victim'); }
  if (level4VictimInFallOfPerp) { score += 1; reasons.push('Victim in fall of perpetrator'); }
  if (level4PerpInFallOfVictim) { score += 1; reasons.push('Perp in fall of victim'); }
  if (level5Terms || directionalReception) {
    score += 1;
    reasons.push(level5Terms ? 'Terms/bounds connection' : 'Directional reception');
  }
  if (criticalFamilyHouse) { score += 1; reasons.push('Family same-house (4 or 10)'); }
  if (lightMediationImpact.scoreDelta) {
    score += lightMediationImpact.scoreDelta;
    reasons.push(...lightMediationImpact.evidence);
  } else if (lightMediationImpact.evidence.length) {
    reasons.push(...lightMediationImpact.evidence);
  }
  if (seventhPlanets.includes('Venus') || seventhPlanets.includes('Mars')) {
    score += 1;
    reasons.push('7th-house indicator');
  }
  if (aspectLabel) {
    if (['conjunction', 'trine', 'sextile'].includes(aspectLabel)) {
      score += 2;
      reasons.push('Harmonious aspect');
    } else if (['square', 'opposition'].includes(aspectLabel)) {
      score += 1;
      reasons.push('Stressful aspect');
    }
    if (applying) {
      score += 1;
      reasons.push('Applying aspect');
    }
  }
  if (criticalDegree) { score += 1; reasons.push('Critical degree'); }
  if (hasViolentStar) { score += 2; reasons.push('Violent fixed star'); }
  if (hasProtectiveStar) { score += 1; reasons.push('Protective fixed star'); }

  return { score: Number(score.toFixed(2)), reasons, lightMediationImpact };
}

function joinOrNone(values = [], empty = 'none') {
  const items = (values || []).filter(Boolean).map((value) => String(value).trim()).filter(Boolean);
  return items.length ? items.join(' | ') : empty;
}

export function formatRelationshipRulershipLinks({
  directVictRulesPerp = false,
  directPerpRulesVict = false,
} = {}) {
  if (directVictRulesPerp && directPerpRulesVict) return 'two-way rulership link';
  if (directVictRulesPerp) return 'victim ruler disposits perpetrator sign';
  if (directPerpRulesVict) return 'perpetrator ruler disposits victim sign';
  return 'none';
}

export function buildRelationshipDisplayRows({
  firstRuler = null,
  moonContacts = [],
  ascRulerContacts = [],
  directVictRulesPerp = false,
  directPerpRulesVict = false,
  isMutual = false,
  level3 = false,
  exaltationFallFlags = [],
  level5Terms = false,
  houseConnections = [],
  traditionalCues = [],
  aspectTies = [],
  degreeStarCues = [],
  score = 0,
  relationshipType = 'Unknown',
  confidence = 'Low',
} = {}) {
  const moonLine = joinOrNone(moonContacts.map((value) => `Moon ${value}`));
  const ascLine = joinOrNone(ascRulerContacts.map((value) => `${firstRuler || 'ASC ruler'} ${value}`));

  return {
    contactSignals: `Moon: ${moonLine} | ASC ruler (${firstRuler || '-'}): ${ascLine}`,
    rulershipLinks: formatRelationshipRulershipLinks({ directVictRulesPerp, directPerpRulesVict }),
    mutualReception: isMutual ? 'present' : 'none',
    sharedTriplicity: level3 ? 'shared triplicity' : 'none',
    exaltationFallTies: joinOrNone(exaltationFallFlags),
    termBoundsTies: level5Terms ? 'term/bounds tie present' : 'none',
    houseOverlap: joinOrNone(houseConnections),
    traditionalCues: joinOrNone(traditionalCues),
    aspectTies: joinOrNone(aspectTies),
    degreeStarCues: joinOrNone(degreeStarCues),
    connectionSummary: `Score ${score} | ${relationshipType} | ${confidence} confidence`,
  };
}

