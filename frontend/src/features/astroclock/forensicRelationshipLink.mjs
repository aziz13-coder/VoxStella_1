import { deriveForensicReplayAxes } from './forensicReplayAxes.mjs';

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

