import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AstroClockAPI } from './api.mjs';
import {
  formatSavedSnapDateTime,
  getSavedSnapIneligibilityLabel,
  getSavedSnapTimezoneLabel,
  isSavedSnapCalculationEligible,
} from './savedSnapViewModel.mjs';

// House system fixed to Regiomontanus for this model
const HOUSE_SYSTEM_CODE = 'R';

const PlanetSymbols = {
  Sun: '☉',
  Moon: '☾',
  Mercury: '☿',
  Venus: '♀',
  Mars: '♂',
  Jupiter: '♃',
  Saturn: '♄',
  Uranus: '♅',
  Neptune: '♆',
  Pluto: '♇',
  'North Node': '☊',
};

const aspectSymbol = (name) => ({
  Conjunction: '☌', Opposition: '☍', Trine: '△', Square: '□', Sextile: '⚹',
  'Semi-sextile': '⚺', Quincunx: '⚻',
  'Antiscia': 'A', 'Contra-antiscia': 'CA'
})[name] || '~';

function finiteNumberOrUndefined(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : undefined;
}

const CanonicalLabels = {
  accident_risk: 'accident risk',
  authority_earned: 'authority earned',
  authority_problems: 'authority problems',
  belief: 'religion/journeys',
  honor_award: 'honor/distinction',
  new_job: 'new office/role',
  job_loss: 'loss of office/job',
  demotion: 'demotion',
  degree_completion: 'completion of studies/degree',
  exam_success: 'success in examination',
  exam_failure: 'failure in examination',
  enrollment_admission: 'admission/entrance into study',
  accident_major: 'major accident',
  near_death_experience: 'near-death experience',
  attack_violence: 'attack/violence',
  fire_burn: 'fire or burn injury',
  drowning_submersion: 'drowning/submersion',
  fall_from_height: 'fall from height',
  spiritual_awakening: 'religious/spiritual awakening',
  religious_conversion: 'change of religion/faith',
  pilgrimage: 'pilgrimage/religious journey',
  mystical_experience: 'visionary/mystical experience',
  publication: 'publication/issued work',
  artistic_success: 'artistic distinction/success',
  discovery_breakthrough: 'breakthrough discovery',
  loss_of_possessions: 'loss of possessions',
  reputation_damage: 'reputation damage',
  war_declaration_offensive: 'offensive war/open-enemy conflict',
  war_response_defensive: 'defensive war/open-enemy conflict',
  internal_conflict_war: 'civil/internal conflict',
  property_value_increase: 'property value increase',
  property_value_decrease: 'property value decrease',
  speculation_gain: 'speculation/hazard gain',
  speculation_loss: 'speculation/hazard loss',
  inheritance_windfall: 'inheritance/succession gain',
  shared_resource_loss: 'loss through debts/shared burdens',
  marriage: 'marriage',
  inheritance: 'inheritance',
  salary_increase: 'increase in salary/income',
  financial_gain: 'gain in wealth/income',
  financial_loss: 'loss of wealth/expense',
  financial_windfall: 'unexpected gain in wealth',
  illness_acute: 'acute illness',
  illness_chronic: 'chronic illness',
  injury_accident: 'injury/accident',
  injury_risk: 'injury risk',
  surgery: 'surgery',
  hospitalization: 'hospitalization',
  recovery_health: 'recovery from illness',
  fever: 'fever',
  family_conflict: 'family conflict',
  vitality_loss: 'vitality loss',
  birth_of_child: 'birth of child',
  birth_self: 'birth (self)',
  death_natural: 'natural death',
  death_violent: 'violent death',
  death_of_family: 'death in family',
  short_journey: 'short journey',
  long_journey: 'long journey',
  romantic_connection: 'courtship/attachment',
  romance: 'courtship/romance',
  reconciliation: 'reconciliation/renewed accord',
  conflict: 'conflict',
  relationship_conflict: 'partnership/open dispute',
  public_recognition: 'public fame/distinction',
  recognition: 'fame/recognition',
  public_approval: 'public favor/approval',
  business_deal: 'business/contract agreement',
  contract_signing: 'contract/agreement',
  contract_problems: 'contract problems',
  miscommunication: 'miscommunication',
  communication_breakthrough: 'communication breakthrough',
  lawsuit: 'lawsuit/open dispute',
  legal_victory: 'legal victory',
  legal_defeat: 'legal defeat',
  legal_resolution: 'legal resolution',
  settlement: 'settlement',
  arrest_imprisonment: 'imprisonment/exile',
  imprisonment_risk: 'imprisonment/exile risk',
  delay_obstruction: 'delay/obstruction',
  discipline_rewarded: 'discipline rewarded',
  structure_established: 'structure established',
  fall_from_power: 'fall from power',
  opportunity_received: 'opportunity received',
  initiative: 'initiative',
  protection_granted: 'protection granted',
  partnership_strengthened: 'partnership strengthened/confirmed',
  partnership_strained: 'partnership strained/disputed',
  engagement: 'engagement/betrothal',
  divorce: 'divorce/dissolution',
  separation: 'separation/estrangement',
  betrayal: 'breach of trust',
  pregnancy: 'pregnancy',
  investment_success: 'investment success',
  investment_loss: 'investment loss',
  bankruptcy: 'bankruptcy',
  business_success: 'business success',
  business_failure: 'business failure',
  theft_fraud: 'theft/fraud',
  family_celebration: 'family/domestic celebration',
  family_joy: 'family/domestic joy',
  family_problems: 'family/household problems',
  domestic_happiness: 'domestic peace/happiness',
  domestic_disruption: 'domestic disruption',
  comfort_security: 'comfort & security',
  honors: 'action/profession/dignity/fame',
  life: 'life/vitality',
  loss_deprivation: 'loss/deprivation',
  money: 'wealth/money/acquired goods',
  excess_problems: 'excess problems',
  moving_home: 'change of home/residence',
  purchase_property: 'purchase of land/home',
  relocation_permanent: 'permanent change of residence',
  relationships: 'marriage/contracts/lawsuits/open enemies',
  secrets: 'seclusion/exile/hidden adversity',
  short_journeys: 'brothers/relations and short journeys',
  shared_resources: 'inheritance/debts/shared burdens',
  siblings: 'brothers/relations',
  relatives: 'relations/kin',
  service: 'servants/subordinates/animals',
  hidden_enemies: 'secret enemies/hardships',
  parents: 'parents/inheritances',
  hopes: 'friends',
  travel_accident: 'travel accident',
  retirement: 'retirement',
  parties_celebrations: 'celebration',
  wealth: 'wealth/acquired goods',
  home: 'parents/home/inheritance',
  health: 'illness/service/subordinates',
  friends: 'friends',
};

const LegacyLabelAliases = {
  'honor award': 'honor_award',
  'new job': 'new_job',
  'job loss': 'job_loss',
  'war/open-enemy conflict (offensive)': 'war_declaration_offensive',
  'war/open-enemy conflict (defensive)': 'war_response_defensive',
  'internal conflict (war)': 'internal_conflict_war',
  'lawsuit': 'lawsuit',
  'imprisonment/exile': 'arrest_imprisonment',
  'imprisonment/exile risk': 'imprisonment_risk',
};

const formatTokenLabel = (token) => {
  if (!token && token !== 0) return '';
  const raw = String(token);
  if (CanonicalLabels[raw]) return CanonicalLabels[raw];
  const lower = raw.toLowerCase();
  if (CanonicalLabels[lower]) return CanonicalLabels[lower];
  const spaced = raw.replace(/_/g, ' ').trim();
  if (!spaced) return '';
  return spaced.replace(/\b\w/g, (ch) => ch.toUpperCase());
};

const LABEL_TO_EVENT_TOKEN = Object.entries(CanonicalLabels).reduce((acc, [token, label]) => {
  acc[label.toLowerCase()] = token;
  return acc;
}, {});
Object.entries(LegacyLabelAliases).forEach(([label, token]) => {
  if (!LABEL_TO_EVENT_TOKEN[label]) LABEL_TO_EVENT_TOKEN[label] = token;
});

// Priority order to pick a primary event when prediction.eventType is missing
const EVENT_PRIORITY = [
  'promotion','recognition','business_deal','contract_signing','communication_breakthrough','romantic_connection','romance','marriage','reconciliation',
  'financial_gain','financial_loss','injury_risk','accident_risk','public_recognition','parties_celebrations','opportunity_received',
  'protection_granted','delay_obstruction','illness_chronic','fall_from_power','authority_problems','domestic_happiness','family_joy',
  'domestic_disruption','family_problems','miscommunication','excess_problems','structure_established','discipline_rewarded','authority_earned',
  'honor_award','new_job','job_loss','inheritance','salary_increase',
  'degree_completion','exam_success','exam_failure','enrollment_admission',
  'accident_major','near_death_experience',
  'war_declaration_offensive','war_response_defensive','internal_conflict_war','warfare_involvement','enemy_attack','violent_confrontation',
  'attack_violence','fire_burn','drowning_submersion','fall_from_height',
  'publication','artistic_success','discovery_breakthrough','loss_of_possessions','reputation_damage',
  'property_value_increase','property_value_decrease','speculation_gain','speculation_loss','inheritance_windfall','shared_resource_loss',
  'spiritual_awakening','religious_conversion','pilgrimage','mystical_experience',
  'lawsuit','legal_victory','legal_defeat','legal_resolution','settlement','arrest_imprisonment',
  'illness_acute','injury_accident','surgery','hospitalization','recovery_health','fever',
  'demotion','business_success','business_failure','retirement',
  'birth_of_child','birth_self','death_natural','death_violent','death_of_family','short_journey','long_journey',
  'partnership_strengthened','partnership_strained','pregnancy','engagement','divorce','separation','betrayal',
  'investment_success','investment_loss','bankruptcy','theft_fraud','family_celebration','family_conflict','moving_home','purchase_property','relocation_permanent','travel_accident'
];

const CRISIS_EVENT_PRIORITY = [
  'war_declaration_offensive','war_response_defensive','internal_conflict_war','warfare_involvement','enemy_attack','violent_confrontation',
  'attack_violence','accident_major','near_death_experience','life_threatening_accident','death_violent',
  'death_natural','death_of_family','death_threat_high','death_threat_moderate',
  'fire_burn','drowning_submersion','fall_from_height','injury_accident','travel_accident','arrest_imprisonment',
];
const CRISIS_EVENT_SET = new Set([...CRISIS_EVENT_PRIORITY, 'imprisonment_risk']);
const CRISIS_SIGNAL_PRIORITY = [...CRISIS_EVENT_PRIORITY, 'conflict', 'relationship_conflict', 'family_conflict'];
const CRISIS_SIGNAL_SET = new Set(CRISIS_SIGNAL_PRIORITY);
const BROAD_CRISIS_SIGNAL_SET = new Set(['conflict', 'relationship_conflict', 'family_conflict']);
const HIGH_BAR_CRISIS_SIGNAL_SET = new Set(['death_natural', 'death_of_family']);
const CRISIS_FAMILY_PRIORITY = {
  conflict: 4,
  prison: 3,
  death: 2,
  accident: 1,
};
const CRISIS_FAMILY_AREA_SUPPORT = {
  conflict: new Set(['conflict', 'relationships', 'marriage', 'hidden_enemies', 'secrets']),
  prison: new Set(['prison', 'hidden_enemies', 'secrets']),
  death: new Set(['death', 'shared_resources']),
  accident: new Set(['danger', 'life', 'health', 'service', 'short_journeys', 'long_travel']),
};

function crisisSignalFamily(token) {
  const key = String(token || '').trim().toLowerCase();
  if (!key) return null;
  if ([
    'war_declaration_offensive', 'war_response_defensive', 'internal_conflict_war', 'warfare_involvement',
    'enemy_attack', 'violent_confrontation', 'attack_violence', 'conflict', 'relationship_conflict', 'family_conflict',
  ].includes(key)) return 'conflict';
  if (['arrest_imprisonment', 'imprisonment_risk'].includes(key)) return 'prison';
  if (['death_natural', 'death_violent', 'death_of_family', 'death_threat_high', 'death_threat_moderate'].includes(key)) return 'death';
  if ([
    'accident_major', 'near_death_experience', 'life_threatening_accident', 'fire_burn',
    'drowning_submersion', 'fall_from_height', 'injury_accident', 'travel_accident',
  ].includes(key)) return 'accident';
  return null;
}

function crisisFamilyAreaSupport(family, lifeArea) {
  const area = String(lifeArea || '').trim().toLowerCase();
  if (!family || !area) return 0;
  const allowed = CRISIS_FAMILY_AREA_SUPPORT[family];
  if (!allowed) return 0;
  return allowed.has(area) ? 1 : 0;
}

function normalizeEventToken(raw) {
  if (!raw) return null;
  const lower = String(raw).trim().toLowerCase();
  if (!lower) return null;
  if (CanonicalLabels[lower]) return lower;
  if (LABEL_TO_EVENT_TOKEN[lower]) return LABEL_TO_EVENT_TOKEN[lower];
  if (lower.includes(' ')) {
    const underscored = lower.replace(/\s+/g, '_');
    if (CanonicalLabels[underscored]) return underscored;
    if (LABEL_TO_EVENT_TOKEN[underscored]) return LABEL_TO_EVENT_TOKEN[underscored];
  }
  return null;
}

function collectHitEventTokens(hit) {
  const orderedTokens = [];
  const tokenSet = new Set();
  const explicitTokens = new Set();
  const pushToken = (raw, explicit = false) => {
    const token = normalizeEventToken(raw);
    if (token && !tokenSet.has(token)) {
      tokenSet.add(token);
      orderedTokens.push(token);
    }
    if (token && explicit) {
      explicitTokens.add(token);
    }
  };

  pushToken(hit?.prediction?.eventType, true);
  (Array.isArray(hit?.enriched_keywords) ? hit.enriched_keywords : []).forEach((raw) => pushToken(raw, true));
  (Array.isArray(hit?.keywords) ? hit.keywords : []).forEach((raw) => pushToken(raw, false));
  (Array.isArray(hit?.prediction_tags) ? hit.prediction_tags : []).forEach((raw) => pushToken(raw, true));

  return { orderedTokens, tokenSet, explicitTokens };
}

function collectPredictionEventTokens(prediction) {
  const orderedTokens = [];
  const tokenSet = new Set();
  const explicitTokens = new Set();
  const pushToken = (raw, explicit = false) => {
    const token = normalizeEventToken(raw);
    if (token && !tokenSet.has(token)) {
      tokenSet.add(token);
      orderedTokens.push(token);
    }
    if (token && explicit) {
      explicitTokens.add(token);
    }
  };

  pushToken(prediction?.event_type || prediction?.eventType, true);
  (Array.isArray(prediction?.tags) ? prediction.tags : []).forEach((raw) => pushToken(raw, true));

  return { orderedTokens, tokenSet, explicitTokens };
}

function classifyCriticalHit(hit) {
  const { orderedTokens, tokenSet, explicitTokens } = collectHitEventTokens(hit);
  const matched = CRISIS_SIGNAL_PRIORITY.filter((token) => tokenSet.has(token));
  if (!matched.length) return null;

  const score = morinHitScore(hit) || Number(hit?.significance ?? 0) || 0;
  const tone = morinHitTone(hit);
  const lifeArea = hit?.prediction?.lifeArea || hit?.life_area || null;
  const primaryToken = pickPrimaryEventToken(hit?.prediction?.eventType, lifeArea, tokenSet, orderedTokens, explicitTokens);
  const crisisToken = CRISIS_SIGNAL_SET.has(primaryToken) ? primaryToken : matched[0];
  if (!crisisToken) return null;

  const minScore = HIGH_BAR_CRISIS_SIGNAL_SET.has(crisisToken)
    ? 45
    : BROAD_CRISIS_SIGNAL_SET.has(crisisToken)
      ? 28
      : 18;
  if (score < minScore) return null;
  if (tone === 'positive' && score < 40) return null;
  if (HIGH_BAR_CRISIS_SIGNAL_SET.has(crisisToken) && tone === 'positive') return null;

  return {
    token: crisisToken,
    family: crisisSignalFamily(crisisToken),
    score,
    tone,
    lifeArea,
    explicitEventType: String(hit?.prediction?.eventType || '').trim().toLowerCase(),
    description: String(
      hit?.prediction?.description
      || [hit?.transiting, hit?.aspect, hit?.target_label || hit?.natal].filter(Boolean).join(' ')
    ),
    significance: Number(hit?.significance ?? score ?? 0) || 0,
    priority: CRISIS_SIGNAL_PRIORITY.indexOf(crisisToken),
  };
}

function classifyCriticalPrediction(prediction) {
  const { orderedTokens, tokenSet, explicitTokens } = collectPredictionEventTokens(prediction);
  const matched = CRISIS_SIGNAL_PRIORITY.filter((token) => tokenSet.has(token));
  if (!matched.length) return null;

  const score = Number(prediction?.score ?? prediction?.significance ?? prediction?.probability ?? 0) || 0;
  const tags = Array.isArray(prediction?.tags) ? prediction.tags.map((tag) => String(tag).toLowerCase()) : [];
  const tone = tags.includes('positive')
    ? 'positive'
    : tags.includes('negative')
      ? 'negative'
      : tags.includes('mixed') || tags.includes('mixed_outcome')
        ? 'mixed'
        : String(prediction?.tone || '').toLowerCase() || 'mixed';
  const lifeArea = prediction?.life_area || prediction?.lifeArea || null;
  const explicitEventType = String(prediction?.event_type || prediction?.eventType || '').trim().toLowerCase();
  const primaryToken = pickPrimaryEventToken(explicitEventType, lifeArea, tokenSet, orderedTokens, explicitTokens);
  const crisisToken = CRISIS_SIGNAL_SET.has(primaryToken) ? primaryToken : matched[0];
  if (!crisisToken) return null;

  const minScore = HIGH_BAR_CRISIS_SIGNAL_SET.has(crisisToken)
    ? 45
    : BROAD_CRISIS_SIGNAL_SET.has(crisisToken)
      ? 28
      : 18;
  if (score < minScore) return null;
  if (tone === 'positive' && score < 40) return null;
  if (HIGH_BAR_CRISIS_SIGNAL_SET.has(crisisToken) && tone === 'positive') return null;

  return {
    token: crisisToken,
    family: crisisSignalFamily(crisisToken),
    score,
    tone,
    lifeArea,
    explicitEventType,
    description: String(prediction?.description || prediction?.label || formatTokenLabel(crisisToken)),
    significance: Number(prediction?.significance ?? prediction?.score ?? score ?? 0) || 0,
    priority: CRISIS_SIGNAL_PRIORITY.indexOf(crisisToken),
  };
}

function rowHasCriticalSignals(row) {
  const hits = Array.isArray(row?.top) ? row.top : [];
  if (hits.some((hit) => Boolean(classifyCriticalHit(hit)))) return true;
  const predictions = Array.isArray(row?.predictions) ? row.predictions : [];
  return predictions.some((prediction) => Boolean(classifyCriticalPrediction(prediction)));
}

function collectCriticalSignalSummary(row, maxItems = 4) {
  const hits = Array.isArray(row?.top) ? row.top : [];
  const hitCriticals = [];
  hits.forEach((hit) => {
    const critical = classifyCriticalHit(hit);
    if (!critical) return;
    hitCriticals.push(critical);
  });
  const rowPredictions = Array.isArray(row?.predictions) ? row.predictions : [];
  const predictionCriticals = [];
  rowPredictions.forEach((prediction) => {
    const critical = classifyCriticalPrediction(prediction);
    if (!critical) return;
    predictionCriticals.push(critical);
  });
  const criticalHits = hitCriticals.length ? hitCriticals : predictionCriticals;

  const familyWeights = new Map();
  const pushFamilyCandidate = (family, lifeArea, score, explicit = false, fromPrediction = false) => {
    if (!family) return;
    const existing = familyWeights.get(family) || {
      family,
      totalScore: 0,
      maxScore: 0,
      explicitCount: 0,
      predictionCount: 0,
      specificAreaSupport: 0,
    };
    existing.totalScore += Number(score || 0);
    existing.maxScore = Math.max(existing.maxScore, Number(score || 0));
    if (explicit) existing.explicitCount += 1;
    if (fromPrediction) existing.predictionCount += 1;
    existing.specificAreaSupport = Math.max(existing.specificAreaSupport, crisisFamilyAreaSupport(family, lifeArea));
    familyWeights.set(family, existing);
  };

  rowPredictions.forEach((pred) => {
    const token = String(pred?.event_type || pred?.eventType || '').trim().toLowerCase();
    const family = crisisSignalFamily(token);
    if (!family) return;
    const score = Number(pred?.score ?? pred?.significance ?? 0) || 0;
    pushFamilyCandidate(family, pred?.life_area || pred?.lifeArea || null, score, true, true);
  });
  criticalHits.forEach((critical) => {
    pushFamilyCandidate(
      critical.family,
      critical.lifeArea,
      critical.score,
      Boolean(critical.explicitEventType),
      false,
    );
  });

  const dominantFamily = Array.from(familyWeights.values())
    .sort((a, b) => {
      if (a.specificAreaSupport !== b.specificAreaSupport) return b.specificAreaSupport - a.specificAreaSupport;
      const familyPriorityDiff = (CRISIS_FAMILY_PRIORITY[b.family] || 0) - (CRISIS_FAMILY_PRIORITY[a.family] || 0);
      if (familyPriorityDiff !== 0) return familyPriorityDiff;
      if (a.predictionCount !== b.predictionCount) return b.predictionCount - a.predictionCount;
      if (a.explicitCount !== b.explicitCount) return b.explicitCount - a.explicitCount;
      if (a.totalScore !== b.totalScore) return b.totalScore - a.totalScore;
      return b.maxScore - a.maxScore;
    })[0]?.family || null;

  let summaryHits = dominantFamily
    ? criticalHits.filter((critical) => critical.family === dominantFamily)
    : criticalHits;
  if (!summaryHits.length && criticalHits.length) {
    summaryHits = criticalHits;
  }

  const tokenWeights = new Map();
  summaryHits.forEach((critical) => {
    const existing = tokenWeights.get(critical.token);
    const boosted = critical.score + Math.max(0, 4 - Math.max(0, critical.priority)) * 0.01;
    if (!existing || boosted > existing.weight) {
      tokenWeights.set(critical.token, { token: critical.token, weight: boosted });
    }
  });

  const chips = Array.from(tokenWeights.values())
    .sort((a, b) => {
      const priorityA = CRISIS_SIGNAL_PRIORITY.indexOf(a.token);
      const priorityB = CRISIS_SIGNAL_PRIORITY.indexOf(b.token);
      if (priorityA !== priorityB) return priorityA - priorityB;
      return Number(b.weight || 0) - Number(a.weight || 0);
    })
    .slice(0, maxItems)
    .map((item) => ({
      key: item.token,
      label: formatTokenLabel(item.token),
    }));

  summaryHits.sort((a, b) => {
    const priorityDiff = Number(a.priority || Number.MAX_SAFE_INTEGER) - Number(b.priority || Number.MAX_SAFE_INTEGER);
    if (priorityDiff !== 0) return priorityDiff;
    return Number(b.significance || 0) - Number(a.significance || 0);
  });
  const topDescriptions = [];
  const seenDescriptions = new Set();
  summaryHits.forEach((item) => {
    if (item.description && !seenDescriptions.has(item.description)) {
      seenDescriptions.add(item.description);
      topDescriptions.push(item.description);
    }
  });

  return {
    chips,
    descriptions: topDescriptions.slice(0, 2),
  };
}

function collectSeriesCriticalRows(series, maxItems = 4) {
  if (!Array.isArray(series)) return [];
  const rows = [];
  series.forEach((row) => {
    if (!rowHasCriticalSignals(row)) return;
    const summary = collectCriticalSignalSummary(row, 3);
    rows.push({
      key: String(row?.timestamp || `${rows.length}`),
      timestamp: row?.timestamp || null,
      tone: morinStepTone(row),
      score: timelineStepScore(row),
      primaryChip: summary.chips?.[0] || null,
      chips: summary.chips || [],
      descriptions: summary.descriptions || [],
    });
  });
  rows.sort((a, b) => {
    const scoreDiff = Number(b.score || 0) - Number(a.score || 0);
    if (scoreDiff !== 0) return scoreDiff;
    return String(a.timestamp || '').localeCompare(String(b.timestamp || ''));
  });
  return rows.slice(0, maxItems);
}

function collectGroupedSeriesCriticalRows(series, maxGroups = 4, maxRowsPerGroup = 4) {
  const rows = collectSeriesCriticalRows(series, 24);
  if (!rows.length) return [];

  const groups = new Map();
  rows.forEach((row) => {
    const primary = row.primaryChip || row.chips?.[0] || { key: 'critical', label: 'critical signal' };
    const key = String(primary.key || primary.label || 'critical');
    const existing = groups.get(key) || {
      key,
      label: primary.label || 'critical signal',
      topScore: 0,
      topTimestamp: null,
      descriptions: [],
      rows: [],
    };
    existing.rows.push({
      key: row.key,
      timestamp: row.timestamp,
      score: row.score,
      tone: row.tone,
    });
    if (Number(row.score || 0) > Number(existing.topScore || 0)) {
      existing.topScore = Number(row.score || 0);
      existing.topTimestamp = row.timestamp || existing.topTimestamp;
    }
    (row.descriptions || []).forEach((description) => {
      if (description && !existing.descriptions.includes(description)) existing.descriptions.push(description);
    });
    groups.set(key, existing);
  });

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      rows: group.rows
        .sort((a, b) => {
          const scoreDiff = Number(b.score || 0) - Number(a.score || 0);
          if (scoreDiff !== 0) return scoreDiff;
          return String(a.timestamp || '').localeCompare(String(b.timestamp || ''));
        })
        .slice(0, maxRowsPerGroup),
      description: group.descriptions[0] || '',
    }))
    .sort((a, b) => {
      const scoreDiff = Number(b.topScore || 0) - Number(a.topScore || 0);
      if (scoreDiff !== 0) return scoreDiff;
      return (b.rows?.length || 0) - (a.rows?.length || 0);
    })
    .slice(0, maxGroups);
}

function isTimestampInsideWindow(ts, contextWindow) {
  try {
    if (!contextWindow?.start || !contextWindow?.end || !ts) return false;
    const t = new Date(String(ts)).getTime();
    const s = new Date(String(contextWindow.start)).getTime();
    const e = new Date(String(contextWindow.end)).getTime();
    return Number.isFinite(t) && Number.isFinite(s) && Number.isFinite(e) && t >= s && t <= e;
  } catch (_) {
    return false;
  }
}

function collectRowPredictionSummary(row, topHits, maxItems = 3) {
  const seen = new Set();
  const items = [];
  const pushItem = (lifeRaw, eventRaw) => {
    const life = formatTokenLabel(lifeRaw);
    const event = formatTokenLabel(eventRaw);
    if (!life && !event) return;
    const label = life && event ? `${life} · ${event}` : (life || event);
    const key = `${String(lifeRaw || '').toLowerCase()}|${String(eventRaw || '').toLowerCase()}`;
    if (!label || seen.has(key)) return;
    seen.add(key);
    items.push({ key, label });
  };

  const rowPredictions = Array.isArray(row?.predictions) ? row.predictions : [];
  rowPredictions.forEach((pred) => {
    pushItem(pred?.life_area, pred?.event_type);
  });
  if (!items.length) {
    (Array.isArray(topHits) ? topHits : []).forEach((hit) => {
      pushItem(hit?.prediction?.lifeArea, hit?.prediction?.eventType);
    });
  }

  const criticalSummary = rowHasCriticalSignals(row) ? collectCriticalSignalSummary(row, 2) : { chips: [] };
  const shownCritical = (criticalSummary.chips || []).filter((chip) => {
    const label = String(chip?.label || '').trim().toLowerCase();
    return label && !items.some((item) => String(item.label || '').trim().toLowerCase().includes(label));
  });

  return {
    items: items.slice(0, maxItems),
    criticalChips: shownCritical,
  };
}

function eventCandidateAreas(eventType) {
  const event = String(eventType || '').trim().toLowerCase();
  if (!event) return new Set();
  if (CRISIS_EVENT_SET.has(event)) return new Set(['conflict', 'danger', 'death', 'prison', 'hidden_enemies', 'secrets']);
  if ([
    'promotion', 'recognition', 'public_recognition', 'honor_award', 'new_job',
    'career_elevation', 'professional_recognition', 'authority_earned',
    'structure_established', 'power_increase', 'loss_of_authority',
    'public_humiliation', 'demotion', 'retirement', 'fall_from_power',
    'authority_problems', 'exceptional_honor_received', 'career_setback_major',
    'church_honors', 'business_success', 'business_failure',
  ].includes(event)) return new Set(['honors']);
  if ([
    'financial_gain', 'financial_loss', 'salary_increase', 'speculation_gain',
    'speculation_loss', 'inheritance', 'inheritance_windfall',
    'inheritance_received', 'shared_resource_loss', 'investment_success',
    'investment_loss', 'bankruptcy', 'bankruptcy_risk', 'debt_crisis',
    'major_wealth_acquisition', 'unexpected_financial_gain',
    'major_financial_loss', 'loss_of_possessions', 'property_value_increase',
    'property_value_decrease', 'theft_fraud',
  ].includes(event)) return new Set(['wealth', 'money', 'shared_resources']);
  if ([
    'marriage', 'marriage_likely', 'significant_partnership',
    'romantic_connection', 'romance', 'reconciliation', 'engagement',
    'partnership_strengthened', 'harmonious_relationship_period',
  ].includes(event)) return new Set(['relationships', 'marriage']);
  if ([
    'relationship_conflict', 'partnership_strained', 'lawsuit',
    'legal_victory', 'legal_defeat', 'legal_resolution', 'settlement',
    'major_lawsuit_initiated', 'divorce', 'separation',
    'divorce_or_separation', 'betrayal',
  ].includes(event)) return new Set(['relationships', 'conflict']);
  if ([
    'moving_home', 'purchase_property', 'relocation_permanent',
    'family_celebration', 'family_conflict', 'family_joy',
    'family_problems', 'domestic_happiness', 'domestic_disruption',
  ].includes(event)) return new Set(['home']);
  if ([
    'short_journey', 'long_journey', 'major_journey_fortunate',
    'travel_misfortune', 'foreign_residence', 'exile_or_forced_travel',
    'communication_breakthrough', 'miscommunication',
  ].includes(event)) return new Set(['short_journeys', 'long_travel']);
  if ([
    'degree_completion', 'exam_success', 'exam_failure',
    'enrollment_admission', 'publication', 'artistic_success',
    'discovery_breakthrough', 'intellectual_breakthrough',
    'educational_achievement', 'mental_confusion_period',
    'spiritual_awakening', 'religious_conversion', 'pilgrimage',
    'mystical_experience',
  ].includes(event)) return new Set(['belief']);
  if ([
    'illness_acute', 'illness_chronic', 'recovery_health', 'surgery',
    'hospitalization', 'fever', 'severe_illness_onset',
    'chronic_illness_development', 'sudden_health_crisis',
    'recovery_period', 'vitality_strengthening', 'injury_risk',
    'accident_risk', 'protection_granted',
  ].includes(event)) return new Set(['health', 'life', 'service']);
  if (['birth_of_child', 'pregnancy', 'childbirth', 'loss_of_child'].includes(event)) return new Set(['children', 'home']);
  if (['birth_self', 'opportunity_received'].includes(event)) return new Set(['life', 'honors', 'wealth']);
  return new Set();
}

function eventCandidateDomainAlignment(eventType, lifeArea) {
  const area = String(lifeArea || '').trim().toLowerCase();
  if (!area) return 0;
  const allowed = eventCandidateAreas(eventType);
  if (!allowed.size) return 0;
  if (allowed.has(area)) return 1;
  if ((area === 'wealth' || area === 'money') && (allowed.has('wealth') || allowed.has('money'))) return 0.9;
  if ((area === 'relationships' || area === 'marriage') && (allowed.has('relationships') || allowed.has('marriage'))) return 0.9;
  if ((area === 'short_journeys' || area === 'long_travel') && (allowed.has('short_journeys') || allowed.has('long_travel'))) return 0.9;
  if (CRISIS_EVENT_SET.has(String(eventType || '').trim().toLowerCase()) && ['conflict', 'danger', 'death', 'prison', 'hidden_enemies', 'secrets'].includes(area)) return 0.8;
  return 0;
}

function pickPrimaryEventToken(explicitEventType, lifeArea, tokenSet, orderedTokens = [], explicitTokens = new Set()) {
  const evExplicit = String(explicitEventType || '').trim();
  if (evExplicit) return evExplicit;
  const searchOrder = CRISIS_EVENT_PRIORITY.some((key) => tokenSet.has(key))
    ? [...CRISIS_EVENT_PRIORITY, ...EVENT_PRIORITY.filter((key) => !CRISIS_EVENT_PRIORITY.includes(key))]
    : EVENT_PRIORITY;
  let bestToken = '';
  let bestKey = null;
  searchOrder.forEach((key, idx) => {
    if (!tokenSet.has(key)) return;
    const alignment = eventCandidateDomainAlignment(key, lifeArea);
    const explicitBonus = explicitTokens.has(key) ? 1 : 0;
    const crisisBonus = CRISIS_EVENT_SET.has(key) && alignment > 0 ? 0.25 : 0;
    const candidateKey = [alignment, explicitBonus, crisisBonus, -idx];
    if (
      !bestKey
      || candidateKey[0] > bestKey[0]
      || (candidateKey[0] === bestKey[0] && candidateKey[1] > bestKey[1])
      || (candidateKey[0] === bestKey[0] && candidateKey[1] === bestKey[1] && candidateKey[2] > bestKey[2])
      || (candidateKey[0] === bestKey[0] && candidateKey[1] === bestKey[1] && candidateKey[2] === bestKey[2] && candidateKey[3] > bestKey[3])
    ) {
      bestKey = candidateKey;
      bestToken = key;
    }
  });
  if (bestToken) {
    return bestToken;
  }
  return orderedTokens.length ? orderedTokens[0] : '';
}

function formatMorinTagLabel(value) {
  const raw = String(value || '').trim();
  if (!raw) return null;
  const key = raw.toLowerCase();
  if (CanonicalLabels[key]) {
    return { key, label: CanonicalLabels[key] };
  }
  const friendly = raw.replace(/_/g, ' ');
  const label = friendly.toUpperCase() === friendly
    ? friendly
    : friendly.replace(/\b\w/g, (ch) => ch.toUpperCase());
  return { key, label };
}

function morinHitScore(hit) {
  const val = hit?.prediction_score ?? hit?.significance ?? 0;
  const num = Number(val);
  return Number.isFinite(num) ? num : 0;
}

function morinHitTone(hit) {
  const tags = Array.isArray(hit?.prediction_tags) ? hit.prediction_tags.map((t) => String(t).toLowerCase()) : [];
  if (tags.includes('positive')) return 'positive';
  if (tags.includes('negative')) return 'negative';
  if (tags.includes('mixed') || tags.includes('mixed_outcome')) return 'mixed';
  const tone = String(hit?.tone || '').toLowerCase();
  if (tone === 'positive' || tone === 'negative' || tone === 'mixed') {
    return tone;
  }
  return 'mixed';
}

const MORIN_ORIENTATION_TAGS = new Set(['positive', 'negative', 'mixed']);
const MORIN_STATUS_TAGS = new Set(['multiple_transit', 'successive']);
const MORIN_MIXED_OUTCOME_TAGS = new Set(['mixed_outcome']);
const MORIN_NEGATIVE_DOMAIN_TAGS = new Set([
  'conflict',
  'danger',
  'death',
  'health',
  'hidden_enemies',
  'illness',
  'prison',
  'secrets',
  'service',
  'shared_resources',
  'violence',
]);
const MORIN_POSITIVE_DOMAIN_TAGS = new Set([
  'belief',
  'career',
  'children',
  'friends',
  'home',
  'honor',
  'honors',
  'hopes',
  'life',
  'marriage',
  'money',
  'parents',
  'relationships',
  'relatives',
  'siblings',
  'wealth',
]);
const MORIN_NEGATIVE_EVENT_TAGS = new Set([
  ...CRISIS_SIGNAL_SET,
  'accident_risk',
  'authority_problems',
  'bankruptcy',
  'betrayal',
  'business_failure',
  'contract_problems',
  'delay_obstruction',
  'demotion',
  'divorce',
  'domestic_disruption',
  'excess_problems',
  'exam_failure',
  'fall_from_power',
  'family_conflict',
  'family_problems',
  'financial_loss',
  'hospitalization',
  'illness_acute',
  'illness_chronic',
  'injury_risk',
  'job_loss',
  'legal_defeat',
  'loss_deprivation',
  'loss_of_possessions',
  'miscommunication',
  'partnership_strained',
  'reputation_damage',
  'risk',
  'separation',
  'shared_resource_loss',
  'surgery',
  'theft_fraud',
  'vitality_loss',
]);
const MORIN_POSITIVE_EVENT_TAGS = new Set([
  'artistic_success',
  'authority_earned',
  'business_deal',
  'business_success',
  'communication_breakthrough',
  'comfort_security',
  'contract_signing',
  'degree_completion',
  'discipline_rewarded',
  'domestic_happiness',
  'engagement',
  'exam_success',
  'family_celebration',
  'family_joy',
  'financial_gain',
  'financial_windfall',
  'honor_award',
  'inheritance',
  'inheritance_windfall',
  'investment_success',
  'legal_resolution',
  'legal_victory',
  'new_job',
  'opportunity_received',
  'parties_celebrations',
  'partnership_strengthened',
  'promotion',
  'protection_granted',
  'public_approval',
  'public_recognition',
  'recognition',
  'reconciliation',
  'recovery_health',
  'romance',
  'romantic_connection',
  'salary_increase',
  'settlement',
  'structure_established',
]);

function normalizeMorinTagKey(value) {
  return String(value || '').trim().toLowerCase().replace(/\s+/g, '_');
}

function morinTagToneRank(orientation) {
  if (orientation === 'negative') return 0;
  if (orientation === 'mixed') return 1;
  if (orientation === 'positive') return 2;
  return 3;
}

function mergeMorinTagOrientation(current, next) {
  if (!current) return next || null;
  if (!next) return current;
  return morinTagToneRank(next) < morinTagToneRank(current) ? next : current;
}

function inferMorinDisplayTagOrientation(key, hitOrientation, hitHasCriticalSignal) {
  if (MORIN_NEGATIVE_EVENT_TAGS.has(key) || MORIN_NEGATIVE_DOMAIN_TAGS.has(key)) {
    return 'negative';
  }
  if (MORIN_MIXED_OUTCOME_TAGS.has(key)) {
    return hitHasCriticalSignal ? 'negative' : 'mixed';
  }
  if (MORIN_POSITIVE_EVENT_TAGS.has(key)) {
    return hitOrientation === 'negative' ? null : 'positive';
  }
  if (MORIN_POSITIVE_DOMAIN_TAGS.has(key)) {
    return hitOrientation === 'positive' && !hitHasCriticalSignal ? 'positive' : null;
  }
  if (hitOrientation === 'negative') return 'negative';
  if (hitOrientation === 'positive' && !hitHasCriticalSignal) return 'positive';
  return null;
}

function classifyMorinDisplayTag(rawTag, hit, showTechTags) {
  const key = normalizeMorinTagKey(rawTag);
  if (!key || MORIN_ORIENTATION_TAGS.has(key)) {
    return null;
  }

  const isStatus = MORIN_STATUS_TAGS.has(key);
  if (isStatus && !showTechTags) {
    return null;
  }

  const fmt = formatMorinTagLabel(key);
  if (!fmt) return null;

  if (isStatus) {
    return { ...fmt, orientation: null, role: 'status', priority: 4 };
  }

  const hitOrientation = morinHitTone(hit);
  const hitHasCriticalSignal = Boolean(classifyCriticalHit(hit));
  const orientation = inferMorinDisplayTagOrientation(key, hitOrientation, hitHasCriticalSignal);
  return {
    ...fmt,
    orientation,
    role: MORIN_MIXED_OUTCOME_TAGS.has(key) ? 'outcome' : 'semantic',
    priority: morinTagToneRank(orientation),
  };
}

function morinStepScore(row) {
  if (!row) return 0;
  const hits = Array.isArray(row?.top) ? row.top : [];
  const total = hits.reduce((sum, hit) => sum + morinHitScore(hit), 0);
  if (total > 0) return total;
  const fallback = Number(row?.step_score ?? 0);
  return Number.isFinite(fallback) ? fallback : 0;
}

function timelineStepScore(row) {
  if (row?.step_score !== undefined && row?.step_score !== null && row?.step_score !== '') {
    const backend = Number(row.step_score);
    if (Number.isFinite(backend)) return backend;
  }
  return morinStepScore(row);
}

function isPlanetTarget(hit) {
  const targetType = String(hit?.target_type || '').trim().toLowerCase();
  if (targetType) return targetType === 'planet';
  const target = String(hit?.target_label || hit?.natal || '').trim();
  return Boolean(target && Object.prototype.hasOwnProperty.call(PlanetSymbols, target));
}

function scanStyleSelectedHits(hits, topN = 3) {
  const rows = Array.isArray(hits) ? hits : [];
  const topPlanets = rows.filter((hit) => isPlanetTarget(hit)).slice(0, topN);
  const topPoints = rows.filter((hit) => !isPlanetTarget(hit)).slice(0, topN);
  return { topPlanets, topPoints, selected: [...topPlanets, ...topPoints] };
}

function scanStyleStepScore(hits) {
  const { selected } = scanStyleSelectedHits(hits);
  return selected.reduce((sum, hit) => sum + morinHitScore(hit), 0);
}

function morinStepTone(row) {
  const backendTone = String(row?.tone || '').toLowerCase();
  if (backendTone === 'negative') return 'negative';
  if (backendTone === 'mixed') return 'mixed';
  if (backendTone === 'positive') return rowHasCriticalSignals(row) ? 'mixed' : 'positive';
  const hits = Array.isArray(row?.top) ? row.top : [];
  if (!hits.length) return row?.tone || 'mixed';
  let balance = 0;
  let pos = 0;
  let neg = 0;
  let hasMixed = false;
  hits.forEach((hit) => {
    const tone = morinHitTone(hit);
    if (tone === 'positive') {
      balance += 1;
      pos += 1;
    } else if (tone === 'negative') {
      balance -= 1;
      neg += 1;
    } else {
      hasMixed = true;
    }
  });
  if (balance > 0) return rowHasCriticalSignals(row) ? 'mixed' : 'positive';
  if (balance < 0) return 'negative';
  if ((pos && neg) || hasMixed) return 'mixed';
  return row?.tone || 'mixed';
}

function _roundPredictorStep(minutes) {
  const safe = Math.max(1, Number(minutes) || 1);
  return Math.max(15, Math.ceil(safe / 15) * 15);
}

function derivePredictorStepPlan(requestedStepMinutes, startIso, endIso) {
  const requested = Math.max(1, Number(requestedStepMinutes || 60) || 60);
  const refinedStep = Math.min(requested, 60);
  let responsiveFloor = 15;
  try {
    const startMs = new Date(String(startIso || '')).getTime();
    const endMs = new Date(String(endIso || '')).getTime();
    if (Number.isFinite(startMs) && Number.isFinite(endMs) && endMs > startMs) {
      const spanMinutes = (endMs - startMs) / 60000;
      const maxPredictorSteps = 240;
      responsiveFloor = _roundPredictorStep(spanMinutes / maxPredictorSteps);
    }
  } catch (_) {}
  const stepMinutes = Math.max(responsiveFloor, refinedStep);
  return {
    stepMinutes,
    requested,
    refinedStep,
    responsiveFloor,
    wasAdjusted: stepMinutes !== requested,
    usesResponsiveFloor: stepMinutes > refinedStep,
    usesRefinedStep: stepMinutes < requested,
  };
}

function predictorWindowGapMs(stepMinutes) {
  const step = Math.max(1, Number(stepMinutes || 60) || 60);
  return step * 2.5 * 60000;
}

function clusterPredictorOccurrences(occurrences, stepMinutes) {
  const sorted = [...(Array.isArray(occurrences) ? occurrences : [])]
    .filter((occ) => occ && occ.date)
    .sort((a, b) => {
      const ta = new Date(a.date).getTime();
      const tb = new Date(b.date).getTime();
      if (!Number.isFinite(ta) || !Number.isFinite(tb)) {
        return String(a.date || '').localeCompare(String(b.date || ''));
      }
      return ta - tb;
    });
  if (!sorted.length) return [];
  const gapMs = predictorWindowGapMs(stepMinutes);
  const clusters = [];
  let current = [];
  let prevMs = null;
  sorted.forEach((occ) => {
    const currentMs = new Date(occ.date).getTime();
    const shouldSplit = (
      current.length > 0
      && Number.isFinite(currentMs)
      && Number.isFinite(prevMs)
      && (currentMs - prevMs) > gapMs
    );
    if (shouldSplit) {
      clusters.push(current);
      current = [];
    }
    current.push(occ);
    if (Number.isFinite(currentMs)) {
      prevMs = currentMs;
    }
  });
  if (current.length) {
    clusters.push(current);
  }
  return clusters;
}

function lawToneClass(modifier) {
  const mod = Number(modifier || 0);
  if (mod > 0.01) return 'border-emerald-300 bg-emerald-50 text-emerald-700';
  if (mod < -0.01) return 'border-rose-300 bg-rose-50 text-rose-700';
  return 'border-zinc-300 bg-zinc-50 text-zinc-700';
}

function appliedLawsForHit(hit) {
  const laws = Array.isArray(hit?.laws_applied) ? hit.laws_applied : [];
  return laws.filter((law) => law && law.applies === true);
}

function collectMorinTags(row, showTechTags) {
  const hits = Array.isArray(row?.top) ? row.top : [];
  const acc = new Map();
  hits.forEach((hit) => {
    const score = morinHitScore(hit);
    const tags = Array.isArray(hit?.prediction_tags) ? hit.prediction_tags : [];
    tags.forEach((tag) => {
      const displayTag = classifyMorinDisplayTag(tag, hit, showTechTags);
      if (!displayTag) return;
      const weight = score > 0 ? score : Number(hit?.significance ?? 0) || 0;
      const existing = acc.get(displayTag.key);
      if (existing) {
        existing.weight = Math.max(existing.weight, weight);
        existing.orientation = mergeMorinTagOrientation(existing.orientation, displayTag.orientation);
        existing.priority = Math.min(existing.priority, displayTag.priority);
      } else {
        acc.set(displayTag.key, { ...displayTag, weight });
      }
    });
    if (showTechTags) {
      const tech = Array.isArray(hit?.tech_tags) ? hit.tech_tags : [];
      tech.forEach((tag) => {
        const fmt = formatMorinTagLabel(tag);
        if (!fmt) return;
        const weight = (score || 1) * 0.5;
        const existing = acc.get(fmt.key);
        if (existing) {
          existing.weight = Math.max(existing.weight, weight);
        } else {
          acc.set(fmt.key, { ...fmt, orientation: null, weight });
        }
      });
    }
  });
  const maxItems = showTechTags ? 8 : 5;
  return Array.from(acc.values())
    .sort((a, b) => (
      Number(a.priority ?? 3) - Number(b.priority ?? 3)
      || morinTagToneRank(a.orientation) - morinTagToneRank(b.orientation)
      || Number(b.weight || 0) - Number(a.weight || 0)
      || a.label.localeCompare(b.label)
    ))
    .slice(0, maxItems);
}

// Canonical tokens → user-friendly labels (Phase 2 additions included)

// Curated secondary chips per primary eventType
const EventChipCurations = {
  promotion: {
    include: ['honor_award','new_job','salary_increase'],
    exclude: ['public_recognition'],
    max: 2,
  },
  marriage: {
    include: ['family_celebration', 'engagement', 'partnership_strengthened'],
    max: 3,
  },
  financial_gain: {
    include: ['salary_increase', 'financial_windfall', 'inheritance_windfall', 'speculation_gain'],
    max: 3,
  },
  financial_loss: {
    include: ['shared_resource_loss', 'speculation_loss'],
    max: 2,
  },
  inheritance_windfall: {
    include: ['financial_gain'],
    max: 1,
  },
  shared_resource_loss: {
    include: ['financial_loss'],
    max: 1,
  },
  romantic_connection: {
    include: ['reconciliation', 'engagement', 'partnership_strengthened'],
    exclude: ['romance'],
    max: 3,
  },
  reconciliation: {
    include: ['engagement', 'partnership_strengthened'],
    exclude: ['romance'],
    max: 2,
  },
  relationship_conflict: {
    include: ['separation', 'betrayal', 'partnership_strained'],
    exclude: ['conflict'],
    max: 3,
  },
  divorce: {
    include: ['separation', 'betrayal', 'partnership_strained'],
    max: 3,
  },
  moving_home: {
    include: ['family_celebration', 'purchase_property', 'relocation_permanent', 'short_journey', 'long_journey'],
    max: 5,
  },
  purchase_property: {
    include: ['moving_home', 'relocation_permanent', 'family_celebration'],
    max: 3,
  },
  spiritual_awakening: {
    include: ['religious_conversion', 'pilgrimage', 'mystical_experience'],
    max: 3,
  },
  degree_completion: {
    include: ['exam_success', 'enrollment_admission', 'publication', 'artistic_success'],
    max: 4,
  },
};

// Qualifiers implied by primary eventType (suppress in Keywords/Domain list)
const ImpliedQualifiersByEvent = {
  promotion: ['public_recognition'],
  romantic_connection: ['romance'],
  relationship_conflict: ['conflict'],
};

// (Icons intentionally not used per request)

function degText(v){
  const n = Number(v||0);
  return `${Math.abs(n).toFixed(2)}°`;
}

function formatTs(iso, tz) {
  try {
    const d = new Date(iso);
    const opts = {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
      hour12: false,
      hourCycle: 'h23'
    };
    if (tz) opts.timeZone = tz;
    return new Intl.DateTimeFormat('en-GB', opts).format(d);
  } catch {
    return String(iso || '');
  }
}

function normalizeTimezoneHint(hint) {
  if (!hint) return null;
  const text = String(hint).trim();
  if (!text) return null;
  const match = text.match(/^([A-Za-z_]+(?:\/[A-Za-z0-9_.+\-]+)+)/);
  if (match && match[1]) return match[1];
  if (text === 'UTC' || text === 'Etc/UTC' || text === 'GMT') return 'UTC';
  return text;
}

function formatIsoForInputFields(iso, tz) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const timezone = normalizeTimezoneHint(tz) || 'UTC';
  try {
    const fmt = new Intl.DateTimeFormat('en-GB', {
      timeZone: timezone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      hourCycle: 'h23',
    });
    const parts = fmt.formatToParts(d);
    const get = (type) => parts.find((part) => part.type === type)?.value || '';
    const year = get('year');
    const month = get('month');
    const day = get('day');
    let hour = get('hour');
    const minute = get('minute');
    if (hour === '24') hour = '00';
    if (year && month && day && hour && minute) {
      return {
        date: `${year}-${month}-${day}`,
        time: `${hour}:${minute}`,
      };
    }
  } catch (_) {}
  return {
    date: `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`,
    time: `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`,
  };
}

function formatTsCompact(iso, tz) {
  try {
    const d = new Date(iso);
    const fmt = new Intl.DateTimeFormat('en-GB', {
      timeZone: tz || undefined,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false
    });
    const parts = fmt.formatToParts(d);
    const get = (t) => (parts.find(p => p.type === t)?.value || '');
    const YYYY = get('year');
    const MM = get('month');
    const DD = get('day');
    const HH = get('hour');
    const MIN = get('minute');
    return `${YYYY}-${MM}-${DD} ${HH}:${MIN}`;
  } catch {
    // Fallback: strip seconds/offset crudely if ISO
    return String(iso || '').replace('T', ' ').replace(/:00(\.\d+)?(?:Z|[+-]\d\d:?\d\d)?$/, '');
  }
}

function formatTimingWindow(win, tz) {
  if (!win || typeof win !== 'object') return '';
  const start = win.start || win.begin || win.from;
  const end = win.end || win.finish || win.to;
  if (!start && !end) return '';
  const startLabel = start ? formatTsCompact(start, tz) : null;
  const endLabel = end ? formatTsCompact(end, tz) : null;
  if (startLabel && endLabel) {
    const [startDate, startTime] = startLabel.split(' ');
    const [endDate, endTime] = endLabel.split(' ');
    if (startDate === endDate) {
      return `${startDate} ${startTime} → ${endTime}`;
    }
    return `${startLabel} → ${endLabel}`;
  }
  return startLabel || endLabel || '';
}

function RevolutionCard({ title, summary, score, timezone }) {
  if (!summary) return null;
  const norm = (typeof score === 'number' && !Number.isNaN(score))
    ? score
    : (typeof summary.normalized_score === 'number' ? summary.normalized_score : null);
  const pct = norm != null ? Math.round(Math.max(0, Math.min(1, norm)) * 100) : null;
  const scoreClass = (() => {
    if (norm == null) return 'border-zinc-300 bg-zinc-50 text-zinc-700';
    if (norm >= 0.65) return 'border-emerald-300 bg-emerald-50 text-emerald-700';
    if (norm <= 0.3) return 'border-rose-300 bg-rose-50 text-rose-700';
    return 'border-amber-300 bg-amber-50 text-amber-700';
  })();
  const ts = summary.timestamp;
  const tags = Array.isArray(summary.signals) && summary.signals.length
    ? summary.signals
    : (Array.isArray(summary.tags) ? summary.tags : []);
  const domains = Array.isArray(summary.domains) ? summary.domains : [];
  return (
    <div className="border rounded-lg p-3 bg-white/80 shadow-sm text-xs">
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-sm">{title}</span>
        {pct != null && (
          <span className={`px-1.5 py-0.5 rounded border ${scoreClass}`} title="Normalized revolution support from backend">
            {pct}% support
          </span>
        )}
      </div>
      {ts && (
        <div className="text-[11px] text-zinc-600 mb-1">
          Exact: {formatTsCompact(ts, timezone)}
        </div>
      )}
      {domains.length > 0 && (
        <div className="text-[11px] text-zinc-700 mb-1">
          <span className="text-zinc-500 mr-1">Themes:</span>
          {domains.map((d, idx) => (
            <span key={idx} className="inline-block mr-1 mb-0.5 px-1 py-0.5 border rounded border-zinc-300 bg-zinc-50 text-zinc-700">
              {String(d).replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}
      {tags.length > 0 && (
        <div className="text-[11px] text-zinc-700 mb-1">
          <span className="text-zinc-500 mr-1">Support:</span>
          {tags.map((tag, idx) => (
            <span key={idx} className="inline-block mr-1 mb-0.5 px-1 py-0.5 border rounded border-sky-300 bg-sky-50 text-sky-700">
              {String(tag)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}


export default function TransitsModal({
  open,
  onClose,
  onJumpToTime,
  defaultHouseSystem = HOUSE_SYSTEM_CODE,
  initialNatalContext = null,
}){
  const [natalDate, setNatalDate] = useState('');
  const [natalTime, setNatalTime] = useState('');
  const [natalLocation, setNatalLocation] = useState('');
  const [natalTimezone, setNatalTimezone] = useState('');
  const [natalLatitude, setNatalLatitude] = useState(undefined);
  const [natalLongitude, setNatalLongitude] = useState(undefined);
  const houseSystem = defaultHouseSystem || HOUSE_SYSTEM_CODE;
  const [includeModern, setIncludeModern] = useState(true);
  const [includeNatalModern, setIncludeNatalModern] = useState(true);
  const [includeCusps, setIncludeCusps] = useState(true);
  const [includeAntiscia, setIncludeAntiscia] = useState(true);
  const [includeLots, setIncludeLots] = useState(true);
  const classicalPlanets = ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn'];
  const modernPlanets = ['Uranus','Neptune','Pluto'];
  const isProd = (() => { try { return !!(import.meta && import.meta.env && import.meta.env.PROD); } catch(_) { return false; } })();
  const [sensitiveHouses, setSensitiveHouses] = useState([]);
  const [sensitivePlanets, setSensitivePlanets] = useState([]);
  const [focusHouses, setFocusHouses] = useState([]);
  const [focusPlanets, setFocusPlanets] = useState("");
  const [transitDate, setTransitDate] = useState('');
  const [transitTime, setTransitTime] = useState('');
  const [computeLoading, setComputeLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const streamRef = React.useRef(null);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [predictorLoading, setPredictorLoading] = useState(false);
  const [predictorError, setPredictorError] = useState(null);
  const [predictorResults, setPredictorResults] = useState(null);
  // Window scan state
  const [winStartDate, setWinStartDate] = useState('');
  const [winStartTime, setWinStartTime] = useState('');
  const [winEndDate, setWinEndDate] = useState('');
  const [winEndTime, setWinEndTime] = useState('');
  const [stepMinutes, setStepMinutes] = useState(60);
  const [series, setSeries] = useState(null);
  const [activeStep, setActiveStep] = useState(null);
  const [peaks, setPeaks] = useState([]);
  const [windowTz, setWindowTz] = useState('');
  const [predictionCard, setPredictionCard] = useState(null);
  const [contextWindow, setContextWindow] = useState(null); // {start,end} iso or null
  const [contextWeighted, setContextWeighted] = useState(false);
  // Display toggles
  const [showTechTags, setShowTechTags] = useState(false);
  const [showEnriched, setShowEnriched] = useState(true);
  // Master switch: include PD/Prog/SA windows in scan/prediction requests
  const [useContextWindows, setUseContextWindows] = useState(false);
  // Layer toggles for Suggest + Intersection
  const [layersEnabled, setLayersEnabled] = useState({ pd: true, prog: true, sa: true });
  // Debug panels
  const [showDebugAuto, setShowDebugAuto] = useState(false);
  const [showDebugScan, setShowDebugScan] = useState(false);
  const [debugAutoCtx, setDebugAutoCtx] = useState(null);
  const [debugScan, setDebugScan] = useState(null);
  const [snaps, setSnaps] = useState([]);
  const [selectedSnapId, setSelectedSnapId] = useState('');
  const [sourceMode, setSourceMode] = useState('manual'); // 'manual' | 'snap'
  const eligibleSnaps = useMemo(
    () => snaps.filter((snap) => isSavedSnapCalculationEligible(snap)),
    [snaps],
  );
  const natalCoordinateContext = useMemo(() => {
    const latitude = finiteNumberOrUndefined(natalLatitude);
    const longitude = finiteNumberOrUndefined(natalLongitude);
    return latitude != null && longitude != null ? { latitude, longitude } : {};
  }, [natalLatitude, natalLongitude]);

  const buildStepFromResult = useCallback((data, fallbackIso) => {
    if (!data) return null;
    const hits = Array.isArray(data.transits) ? data.transits : [];
    const { topPlanets, topPoints } = scanStyleSelectedHits(hits);
    return {
      timestamp: data.transit_timestamp || fallbackIso || null,
      top: hits,
      top_planets: topPlanets,
      top_cusps: topPoints,
      step_score: scanStyleStepScore(hits),
      predictions: Array.isArray(data.predictions) ? data.predictions : [],
      count: typeof data.count === 'number' ? data.count : hits.length,
      moon_support: Boolean(data.moon_support),
    };
  }, []);

  const revolutionBundle = result?.revolutions || {};
  const solarSummary = revolutionBundle?.solar || null;
  const lunarSummary = revolutionBundle?.lunar || null;
  const solarScore = typeof revolutionBundle?.solar_score === 'number' ? revolutionBundle.solar_score : null;
  const lunarScore = typeof revolutionBundle?.lunar_score === 'number' ? revolutionBundle.lunar_score : null;
  const natalTz = result?.natal?.timezone || result?.natal?.timezone_label;

  // Debounce ref for scans (must be inside component for hooks)
  const scanDebounceRef = React.useRef(null);

  // Build a compact concordance tooltip for a hit
  const ccTip = (h) => {
    try {
      const c = h?.concordance || {};
      const pd = Array.isArray(c.pd_matches) && c.pd_matches.length ? c.pd_matches[0] : null;
      const pdStr = pd ? `PD: ${pd.type || '—'}${pd.quality ? ', ' + pd.quality : ''}${(pd.strength!=null) ? ' ' + Number(pd.strength).toFixed(1) : ''}` : 'PD: —';
      const srStr = `SR: ${Number(c.solar_match||0) > 0 ? '✔' : '—'}`;
      const lrStr = `LR: ${Number(c.lunar_match||0) > 0 ? '✔' : '—'}`;
      const ovStr = `Overall: ${Number(c.overall_concordance||0).toFixed(2)}`;
      return [pdStr, srStr, lrStr, ovStr].join(' | ');
    } catch { return ''; }
  };

  if (!open) return null;

  const close = () => {
    setResult(null);
    setError(null);
    setComputeLoading(false);
    setScanning(false);
    setActiveStep(null);
    if (scanDebounceRef.current) { clearTimeout(scanDebounceRef.current); scanDebounceRef.current = null; }
    onClose && onClose();
  };

  const getTimezoneOffsetMinutes = (date, timeZone) => {
    try {
      const dtf = new Intl.DateTimeFormat('en-US', {
        timeZone,
        hourCycle: 'h23',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      const parts = dtf.formatToParts(date);
      const bucket = {};
      parts.forEach((part) => {
        if (part.type !== 'literal') bucket[part.type] = part.value;
      });
      if (!bucket.year || !bucket.month || !bucket.day || !bucket.hour || !bucket.minute || !bucket.second) return null;
      const asUTC = Date.UTC(
        Number(bucket.year),
        Number(bucket.month) - 1,
        Number(bucket.day),
        Number(bucket.hour),
        Number(bucket.minute),
        Number(bucket.second),
      );
      return (asUTC - date.getTime()) / 60000;
    } catch {
      return null;
    }
  };

  const buildIso = (d, t, tzHint) => {
    if (!d || !t) return null;
    const hhmmss = t.length === 5 ? `${t}:00` : t;
    const [year, month, day] = d.split('-').map((part) => Number(part));
    const [hour, minute, second = 0] = hhmmss.split(':').map((part) => Number(part));
    if ([year, month, day, hour, minute, second].some((n) => !Number.isFinite(n))) return null;
    const baseUtc = Date.UTC(year, month - 1, day, hour, minute, second);
    if (!Number.isFinite(baseUtc)) return null;

    const normalizeTimezoneHint = (hint) => {
      if (!hint) return null;
      const text = String(hint).trim();
      if (!text) return null;
      const match = text.match(/^([A-Za-z_]+(?:\/[A-Za-z0-9_.+\-]+)+)/);
      if (match && match[1]) return match[1];
      return text;
    };

    const applyTimezone = (timezone) => {
      if (!timezone) return null;
      const baseDate = new Date(baseUtc);
      const offsetMinutes = getTimezoneOffsetMinutes(baseDate, timezone);
      if (offsetMinutes == null || Number.isNaN(offsetMinutes)) return null;
      return new Date(baseUtc - offsetMinutes * 60000).toISOString();
    };

    const tzName = normalizeTimezoneHint(tzHint);
    if (tzName) {
      const zoned = applyTimezone(tzName);
      if (zoned) return zoned;
    }

    if (!tzName) {
      const localDate = new Date(`${d}T${hhmmss}`);
      if (!Number.isNaN(localDate.getTime())) {
        return localDate.toISOString();
      }
    }

    return new Date(baseUtc).toISOString();
  };

  const getTransitInputTimezone = () => (
    windowTz
    || result?.natal?.timezone
    || result?.natal?.timezone_label
    || natalTimezone
    || 'UTC'
  );

  const setStoredContextIso = (key, boundary, iso) => {
    const value = iso || undefined;
    if (key === 'pd') {
      if (boundary === 'start') window.__pdStart = value;
      else window.__pdEnd = value;
    } else if (key === 'prog') {
      if (boundary === 'start') window.__progStart = value;
      else window.__progEnd = value;
    } else if (key === 'sa') {
      if (boundary === 'start') window.__saStart = value;
      else window.__saEnd = value;
    }
  };

  const buildContextIsoFromInputs = (date, time, fallbackTime) => {
    if (!date) return '';
    return buildIso(date, time || fallbackTime, getTransitInputTimezone()) || '';
  };

  const writeInputDateTime = (dateId, timeId, iso) => {
    const parts = formatIsoForInputFields(iso, getTransitInputTimezone());
    if (!parts) return;
    try { const el = document.getElementById(dateId); if (el) el.value = parts.date; } catch(_) { }
    try { const el = document.getElementById(timeId); if (el) el.value = parts.time; } catch(_) { }
  };

  const normalizeSnapLocationKey = useCallback((value) => {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ');
  }, []);

  const findMatchingSnapId = useCallback((items, context) => {
    const explicitSnapId = context?.snapId ? String(context.snapId) : '';
    const safeItems = Array.isArray(items) ? items : [];
    if (explicitSnapId && safeItems.some((snap) => String(snap?.id || '') === explicitSnapId)) {
      return explicitSnapId;
    }
    const targetIso = buildIso(context?.date, context?.time, context?.timezone);
    const targetMs = new Date(String(targetIso || '')).getTime();
    if (!Number.isFinite(targetMs)) return '';
    const targetLocation = normalizeSnapLocationKey(context?.location);
    const matchBy = (matcher) => {
      const match = safeItems.find((snap) => {
        const snapMs = new Date(String(snap?.effective_datetime || '')).getTime();
        if (!Number.isFinite(snapMs) || snapMs !== targetMs) return false;
        return matcher(snap);
      });
      return match?.id ? String(match.id) : '';
    };
    const exactLocationMatch = targetLocation
      ? matchBy((snap) => normalizeSnapLocationKey(snap?.location) === targetLocation)
      : '';
    if (exactLocationMatch) return exactLocationMatch;
    return matchBy(() => true);
  }, [buildIso, normalizeSnapLocationKey]);

  const handleCompute = async (overrideTransitIso=null) => {
    if (overrideTransitIso == null) {
      setError('Select a day by clicking a bar in the timeline.');
      return;
    }
    setComputeLoading(true); setError(null);
    try {
      const useSnap = (sourceMode === 'snap');
      const tzForNatal = natalTimezone || result?.natal?.timezone || result?.natal?.timezone_label || windowTz || undefined;
      const natalIso = useSnap ? null : buildIso(natalDate, natalTime, tzForNatal);
      if (useSnap) {
        if (!selectedSnapId) { setError('Choose a saved snap as natal source.'); setComputeLoading(false); return; }
      } else {
        if (!natalIso || !natalLocation) { setError('Enter natal date, time, and location.'); setComputeLoading(false); return; }
      }
      const transitIso = overrideTransitIso;
      const focusPlanetsList = focusPlanets.split(',').map(s => s.trim()).filter(Boolean);
      const res = await AstroClockAPI.getTransits((useSnap ? {
        natalSnapId: selectedSnapId,
        houseSystem,
        transitDatetime: transitIso,
        includeModern,
        includeNatalModern,
        includeCusps: includeCusps || (sensitiveHouses && sensitiveHouses.length>0),
        includeAntiscia,
        includeLots,
        focusHouses,
        focusPlanets: focusPlanetsList,
        sensitiveHouses,
        sensitivePlanets,
      } : {
        natalDatetime: natalIso,
        natalLocation,
        natalTimezone: natalTimezone || undefined,
        ...natalCoordinateContext,
        houseSystem,
        transitDatetime: transitIso,
        includeModern,
        includeNatalModern,
        includeCusps: includeCusps || (sensitiveHouses && sensitiveHouses.length>0),
        includeAntiscia,
        includeLots,
        focusHouses,
        focusPlanets: focusPlanetsList,
        sensitiveHouses,
        sensitivePlanets,
      }));
      const data = res?.data || null;
      try {
        if (data && Array.isArray(data.transits)) {
          const rankScore = (row) => Number(row?.prediction_score ?? row?.significance ?? 0);
          data.transits = [...data.transits].sort((a,b)=> {
            const sigDiff = Number(b.significance||0) - Number(a.significance||0);
            if (sigDiff !== 0) return sigDiff;
            return rankScore(b) - rankScore(a);
          });
        }
      } catch(_) {}
      setResult(data);
      const syntheticStep = buildStepFromResult(data, transitIso);
      setActiveStep(syntheticStep);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setComputeLoading(false);
    }
  };

  const handleComputeExactTime = async () => {
    const tzFallback = windowTz || result?.natal?.timezone || result?.natal?.timezone_label || natalTimezone || undefined;
    const transitIso = buildIso(transitDate, transitTime, tzFallback);
    if (!transitIso) {
      setError('Enter a transit date and time to compute the exact transit.');
      return;
    }
    await handleCompute(transitIso);
  };

  const doScan = async () => {
    setActiveStep(null);
    setScanning(true); setError(null); setScanProgress(0);
    try {
      const useSnap = (sourceMode === 'snap');
      const tzFallback = windowTz || result?.natal?.timezone || result?.natal?.timezone_label || natalTimezone || undefined;
      const natalIso = useSnap ? null : buildIso(natalDate, natalTime, natalTimezone || tzFallback);
      if (useSnap) {
        if (!selectedSnapId) { setError('Choose a saved snap as natal source.'); setScanning(false); return; }
      } else {
        if (!natalIso || !natalLocation) { setError('Enter natal date, time, and location.'); setScanning(false); return; }
      }
      const startIsoRaw = buildIso(winStartDate, winStartTime, tzFallback);
      const endIsoRaw = buildIso(winEndDate, winEndTime, tzFallback);
      const centerIso = buildIso(transitDate, transitTime, tzFallback);
      const hasStart = !!startIsoRaw;
      const hasEnd = !!endIsoRaw;
      if ((hasStart && !hasEnd) || (!hasStart && hasEnd)) {
        setError('Provide both scan start and end times, or leave both blank to center on the transit timestamp.');
        setScanning(false);
        return;
      }
      if (!hasStart && !hasEnd && !centerIso) {
        setError('Set scan start/end or a transit date/time before scanning.');
        setScanning(false);
        return;
      }
      const defaultRangeHours = 24;
      const msPerHour = 60 * 60 * 1000;
      let startIso = startIsoRaw;
      let endIso = endIsoRaw;
      if (!hasStart && !hasEnd && centerIso) {
        const centerDate = new Date(centerIso);
        if (Number.isNaN(centerDate.getTime())) {
          setError('Transit date/time could not be parsed. Please re-enter it.');
          setScanning(false);
          return;
        }
        const halfWindowMs = (defaultRangeHours / 2) * msPerHour;
        const startDate = new Date(centerDate.getTime() - halfWindowMs);
        const endDate = new Date(centerDate.getTime() + halfWindowMs);
        startIso = startDate.toISOString();
        endIso = endDate.toISOString();
      }
      const opts = (useSnap ? {
        natalSnapId: selectedSnapId,
        houseSystem,
      } : {
        natalDatetime: natalIso,
        natalLocation,
        natalTimezone: natalTimezone || undefined,
        ...natalCoordinateContext,
        houseSystem,
      });
      const focusPlanetsList = focusPlanets.split(',').map(s => s.trim()).filter(Boolean);
      const req = {
        ...opts,
        start: startIso || undefined,
        end: endIso || undefined,
        center: (!hasStart && !hasEnd) ? centerIso : undefined,
        rangeHours: (!hasStart && !hasEnd) ? defaultRangeHours : undefined,
        stepMinutes,
        includeModern,
        includeNatalModern,
        includeCusps: includeCusps || (sensitiveHouses && sensitiveHouses.length>0),
        includeAntiscia,
        includeLots,
        focusHouses,
        focusPlanets: focusPlanetsList,
        sensitiveHouses,
        sensitivePlanets,
        // Only include context windows when explicitly enabled
        pdStart: (useContextWindows && layersEnabled.pd) ? (window.__pdStart || undefined) : undefined,
        pdEnd: (useContextWindows && layersEnabled.pd) ? (window.__pdEnd || undefined) : undefined,

        progStart: (useContextWindows && layersEnabled.prog) ? (window.__progStart || undefined) : undefined,
        progEnd: (useContextWindows && layersEnabled.prog) ? (window.__progEnd || undefined) : undefined,

        saStart: (useContextWindows && layersEnabled.sa) ? (window.__saStart || undefined) : undefined,
        saEnd: (useContextWindows && layersEnabled.sa) ? (window.__saEnd || undefined) : undefined,
        // Context metadata (if any)
        ...(useContextWindows && layersEnabled.pd && window.__pdMeta ? {
          pdLabel: window.__pdMeta.label || undefined,
          pdSig: window.__pdMeta.significator || undefined,
          pdPro: window.__pdMeta.promittor || undefined,
          pdAspect: window.__pdMeta.aspect || undefined,
          pdType: window.__pdMeta.type || undefined,
        } : {}),
        ...(useContextWindows && layersEnabled.sa && window.__saMeta ? {
          saLabel: window.__saMeta.label || undefined,
        } : {}),
      };
      // Ensure progression window intersects Anchor; otherwise drop it
      try {
        if (req.progStart && req.progEnd && req.start && req.end) {
          const aS = new Date(req.start).getTime();
          const aE = new Date(req.end).getTime();
          const pS = new Date(req.progStart).getTime();
          const pE = new Date(req.progEnd).getTime();
          if (!(pE > aS && pS < aE)) {
            req.progStart = undefined; req.progEnd = undefined;
          }
        }
      } catch(_) {}
      const ps = new URLSearchParams();
      Object.entries(req).forEach(([k,v])=> {
        if (v==null) return;
        const key = k.replace(/[A-Z]/g,m=>`_${m.toLowerCase()}`);
        if (Array.isArray(v)) {
          v.forEach(x=> { if (x!=null) ps.append(key, String(x)); });
          return;
        }
        if (typeof v === 'boolean') {
          if (v) ps.set(key, '1'); // only send when true
          return;
        }
        ps.set(key, String(v));
      });
      const reqPreview = `/api/astro-clock/transits/window?${ps.toString()}`;
      const applyWindowData = (payload) => {
        const data = payload || {};
        setSeries(Array.isArray(data.series) ? data.series : []);
        setPeaks(Array.isArray(data.peaks) ? data.peaks : []);
        if (Object.prototype.hasOwnProperty.call(data, 'prediction_card')) {
          setPredictionCard(data.prediction_card || null);
        }
        setContextWindow(data.context_window || null);
        if (data.natal && data.natal.timezone) {
          setWindowTz(data.natal.timezone || '');
        }
        try {
          setDebugScan({
            request: reqPreview,
            stepMinutes,
            series: Array.isArray(data.series) ? data.series.length : 0,
            peaks: Array.isArray(data.peaks) ? data.peaks.length : 0,
            contextWindow: data.context_window || null,
          });
        } catch (_) {
          setDebugScan({ request: reqPreview, stepMinutes });
        }
      };
      const fetchWindowData = async () => {
        try {
          const res = await AstroClockAPI.getTransitsWindow(req);
          applyWindowData(res?.data);
          setScanProgress(1);
        } catch (err) {
          setError(err?.message || String(err));
        } finally {
          setScanning(false);
        }
      };
      // Try streaming for real progress updates
      if (streamRef.current) {
        try { streamRef.current.close(); } catch(_){ }
        streamRef.current = null;
      }
      const es = await AstroClockAPI.createTransitsWindowStream(req);
      if (es) {
        streamRef.current = es;
        const acc = [];
        let finished = false;
        es.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data || '{}');
            if (msg.type === 'progress') {
              setScanProgress(Number(msg.progress || 0));
              if (msg.row) {
                acc.push(msg.row);
                setSeries([...acc]);
              }
            } else if (msg.type === 'done') {
              finished = true;
              applyWindowData(msg);
              setScanProgress(1);
              es.close(); streamRef.current = null; setScanning(false);
            }
          } catch (_) {}
        };
        es.onerror = () => {
          if (finished) return;
          finished = true;
          try { es.close(); } catch(_){ }
          streamRef.current = null;
          fetchWindowData();
        };
      } else {
        await fetchWindowData();
      }
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      // scanning ends in stream handler for streaming path
    }
  };

  const runPredictor = async () => {
    setPredictorLoading(true);
    setPredictorError(null);
    setPredictorResults(null);
    try {
      const useSnap = (sourceMode === 'snap');
      const tzFallback = windowTz || result?.natal?.timezone || result?.natal?.timezone_label || natalTimezone || undefined;
      const natalIso = useSnap ? null : buildIso(natalDate, natalTime, natalTimezone || tzFallback);
      if (useSnap) {
        if (!selectedSnapId) { setPredictorError('Choose a saved snap as natal source.'); setPredictorLoading(false); return; }
      } else {
        if (!natalIso || !natalLocation) { setPredictorError('Enter natal date, time, and location.'); setPredictorLoading(false); return; }
      }
      let finalStart = predictorWindowBounds.startIso;
      let finalEnd = predictorWindowBounds.endIso;
      if (!finalStart || !finalEnd) {
        setPredictorError('Set scan start and end (or transit date & time) before running the predictor.');
        setPredictorLoading(false);
        return;
      }
      const baseOpts = useSnap ? {
        natalSnapId: selectedSnapId,
      } : {
        natalDatetime: natalIso,
        natalLocation,
        natalTimezone: natalTimezone || undefined,
        ...natalCoordinateContext,
      };
      const focusPlanetsList = focusPlanets.split(',').map(s => s.trim()).filter(Boolean);
      const req = {
        ...baseOpts,
        houseSystem,
        start: finalStart,
        end: finalEnd,
        stepMinutes: derivePredictorStepPlan(stepMinutes, finalStart, finalEnd).stepMinutes,
        includeModern,
        includeNatalModern,
        includeCusps: includeCusps || (sensitiveHouses && sensitiveHouses.length>0),
        includeAntiscia,
        includeLots,
        focusHouses,
        focusPlanets: focusPlanetsList,
        sensitiveHouses,
        sensitivePlanets,
        limit: 30,
      };
      if (useContextWindows && layersEnabled.pd && window.__pdStart && window.__pdEnd) {
        req.pdStart = window.__pdStart;
        req.pdEnd = window.__pdEnd;
      }
      if (useContextWindows && layersEnabled.prog && window.__progStart && window.__progEnd) {
        req.progStart = window.__progStart;
        req.progEnd = window.__progEnd;
      }
      if (useContextWindows && layersEnabled.sa && window.__saStart && window.__saEnd) {
        req.saStart = window.__saStart;
        req.saEnd = window.__saEnd;
      }
      const res = await AstroClockAPI.getPredictions(req);
      const data = res?.data || null;
      setPredictorResults(data);
    } catch (e) {
      setPredictorError(e?.message || String(e));
    } finally {
      setPredictorLoading(false);
    }
  };

  const handleScanClick = () => {
    // Debounce scans to avoid double-fire
    if (scanDebounceRef.current) {
      clearTimeout(scanDebounceRef.current);
    }
    scanDebounceRef.current = setTimeout(() => {
      scanDebounceRef.current = null;
      doScan();
    }, 300);
  };

  React.useEffect(() => () => { try { if (streamRef.current) streamRef.current.close(); } catch(_){ } }, []);

  // Auto-fill SR window and focus hints
  const handleAutoContext = async () => {
    try {
      const useSnap = (sourceMode === 'snap');
      const tzFallback = windowTz || result?.natal?.timezone || result?.natal?.timezone_label || natalTimezone || undefined;
      const natalIso = useSnap ? null : buildIso(natalDate, natalTime, natalTimezone || tzFallback);
      if (useSnap) {
        if (!selectedSnapId) { setError('Choose a saved snap as natal source.'); return; }
      } else {
        if (!natalIso || !natalLocation) { setError('Enter natal date, time, and location.'); return; }
      }
      // Anchor priority: Scan range > Transit datetime > default (engine)
      const anchorStart = buildIso(winStartDate, winStartTime, tzFallback) || undefined;
      const anchorEnd = buildIso(winEndDate, winEndTime, tzFallback) || undefined;
      const anchorCenter = buildIso(transitDate, transitTime, tzFallback) || undefined;
      const reqOpts = (useSnap ? {
        natalSnapId: selectedSnapId,
        houseSystem,
        anchorStart,
        anchorEnd,
        anchorCenter,
      } : {
        natalDatetime: natalIso,
        natalLocation,
        natalTimezone: natalTimezone || undefined,
        ...natalCoordinateContext,
        houseSystem,
        anchorStart,
        anchorEnd,
        anchorCenter,
      });
      const qp = new URLSearchParams();
      Object.entries(reqOpts).forEach(([k,v])=> { if (v!=null && v!=='') qp.set(k.replace(/[A-Z]/g,m=>`_${m.toLowerCase()}`), String(v)); });
      const preview = `/api/astro-clock/context/auto?${qp.toString()}`;
      const res = await AstroClockAPI.getAutoContext(reqOpts);
      const data = res?.data || {};
      // Do not overwrite user's focus selections on Auto-Fill.
      // Debug summary
      try {
        setDebugAutoCtx({
          request: preview,
          anchor: { start: anchorStart||null, end: anchorEnd||null, center: anchorCenter||null },
          counts: { pd: (data.pd_windows||[]).length, prog: (data.progression_windows||[]).length }
        });
      } catch(_) { setDebugAutoCtx({ request: preview }); }

      // Fill PD and Progression context windows (select nearest/overlapping per backend)
      try {
        const chosenPd = data.pd_selected || (Array.isArray(data.pd_windows) && data.pd_windows.length ? data.pd_windows[0] : null);
        if (layersEnabled.pd && chosenPd) {
          const w = chosenPd;
          if (w && w.start && w.end) {
            let s = new Date(w.start), e = new Date(w.end);
            let overlapped = true;
            try {
              if (anchorStart && anchorEnd) {
                const aS = new Date(anchorStart); const aE = new Date(anchorEnd);
                const cs = new Date(Math.max(s.getTime(), aS.getTime()));
                const ce = new Date(Math.min(e.getTime(), aE.getTime()));
                if (ce > cs) { s = cs; e = ce; } else { overlapped = false; }
              }
            } catch(_){}
            // Always reflect chosen PD to UI fields (original window)
            writeInputDateTime('pd-start-date', 'pd-start-time', w.start);
            writeInputDateTime('pd-end-date', 'pd-end-time', w.end);
            // Only pass overlapped PD window to scans
            if (overlapped && s && e) {
              window.__pdStart = s.toISOString(); window.__pdEnd = e.toISOString();
              try {
                const item = w.item || {};
                window.__pdMeta = {
                  label: w.label || undefined,
                  significator: item.significator || undefined,
                  promittor: item.promittor || undefined,
                  aspect: item.aspect || undefined,
                  type: item.type || undefined,
                };
              } catch(_) { window.__pdMeta = undefined; }
            } else {
              try { window.__pdStart = undefined; window.__pdEnd = undefined; window.__pdMeta = undefined; } catch(_){}
            }
          }
        }
      } catch(_) {}
      // Fill Solar Arc window (prefer selected; always show; only send to scans when overlapped with anchor)
      try {
        const chosenSa = data.sa_selected || (Array.isArray(data.sa_windows) && data.sa_windows.length ? data.sa_windows[0] : null);
        if (layersEnabled.sa && chosenSa) {
          const w = chosenSa;
          if (w && w.start && w.end) {
            let s = new Date(w.start), e = new Date(w.end);
            let overlapped = true;
            try {
              if (anchorStart && anchorEnd) {
                const aS = new Date(anchorStart); const aE = new Date(anchorEnd);
                const cs = new Date(Math.max(s.getTime(), aS.getTime()));
                const ce = new Date(Math.min(e.getTime(), aE.getTime()));
                if (!(ce > cs)) { overlapped = false; } else { s = cs; e = ce; }
              }
            } catch(_){}
            // Always reflect selected SA window to UI fields (original window)
            writeInputDateTime('sa-start-date', 'sa-start-time', w.start);
            writeInputDateTime('sa-end-date', 'sa-end-time', w.end);
            // Only pass overlapped SA window to scans
            if (overlapped && s && e) {
              window.__saStart = s.toISOString(); window.__saEnd = e.toISOString();
              try { window.__saMeta = { label: w.label || undefined }; } catch(_) { window.__saMeta = undefined; }
            } else {
              try { window.__saStart = undefined; window.__saEnd = undefined; window.__saMeta = undefined; } catch(_) {}
            }
          }
        }
      } catch(_) {}
      try {
        if (layersEnabled.prog) {
          const pw = data.prog_window;
          const startISO = (pw && (pw.outer_start || pw.start)) || null;
          const endISO = (pw && (pw.outer_end || pw.end)) || null;
          if (startISO && endISO) {
            const s = new Date(startISO), e = new Date(endISO);
            window.__progStart = s.toISOString(); window.__progEnd = e.toISOString();
            writeInputDateTime('prog-start-date', 'prog-start-time', startISO);
            writeInputDateTime('prog-end-date', 'prog-end-time', endISO);
          }
        }
      } catch(_) {}

      // If we successfully filled any context window, auto-enable using them for scans
      try {
        const anyCtx = (
          (layersEnabled.pd && window.__pdStart && window.__pdEnd) ||
          (layersEnabled.prog && window.__progStart && window.__progEnd) ||
          (layersEnabled.sa && window.__saStart && window.__saEnd)
        );
        if (anyCtx) setUseContextWindows(true);
      } catch(_) {}
    } catch (e) {
      setError(e?.message || String(e));
    }
  };

  const fillNowWindow = (days=7) => {
    const d = new Date();
    const start = new Date(d.getTime());
    const end = new Date(d.getTime() + days*24*60*60*1000);
    const fmtD = (x) => `${x.getFullYear()}-${String(x.getMonth()+1).padStart(2,'0')}-${String(x.getDate()).padStart(2,'0')}`;
    const fmtT = (x) => `${String(x.getHours()).padStart(2,'0')}:${String(x.getMinutes()).padStart(2,'0')}`;
    setWinStartDate(fmtD(start)); setWinStartTime(fmtT(start));
    setWinEndDate(fmtD(end)); setWinEndTime(fmtT(end));
  };

  const loadSnaps = async () => {
    try { const res = await AstroClockAPI.listSnaps(); setSnaps(res?.items || []); } catch(_) {}
  };

  useEffect(()=>{ if (open) loadSnaps(); }, [open]);

  useEffect(() => {
    if (!selectedSnapId) return;
    const selected = snaps.find(
      (snap) => String(snap?.id || '') === String(selectedSnapId),
    );
    if (!selected || isSavedSnapCalculationEligible(selected)) return;
    setSelectedSnapId('');
    setSourceMode('manual');
    setError('This saved chart needs context review. Correct it in Astro Clock and use the corrected copy.');
  }, [selectedSnapId, snaps]);

  useEffect(() => {
    if (!open || !initialNatalContext || typeof initialNatalContext !== 'object') return;
    const snapId = initialNatalContext.snapId ? String(initialNatalContext.snapId) : '';
    const nextDate = typeof initialNatalContext.date === 'string' ? initialNatalContext.date : '';
    const nextTime = typeof initialNatalContext.time === 'string' ? initialNatalContext.time : '';
    const nextLocation = typeof initialNatalContext.location === 'string' ? initialNatalContext.location : '';
    const nextTimezone = typeof initialNatalContext.timezone === 'string' ? initialNatalContext.timezone : '';
    const nextLatitude = finiteNumberOrUndefined(initialNatalContext.latitude);
    const nextLongitude = finiteNumberOrUndefined(initialNatalContext.longitude);

    setNatalDate(nextDate);
    setNatalTime(nextTime);
    setNatalLocation(nextLocation);
    setNatalTimezone(nextTimezone);
    setNatalLatitude(nextLatitude);
    setNatalLongitude(nextLongitude);
    setSelectedSnapId(snapId);
    setSourceMode(snapId ? 'snap' : 'manual');

    setError(null);
    setResult(null);
    setComputeLoading(false);
    setPredictorError(null);
    setPredictorResults(null);
    setPredictorLoading(false);
    setSeries(null);
    setPeaks([]);
    setPredictionCard(null);
    setActiveStep(null);
  }, [
    open,
    initialNatalContext?.date,
    initialNatalContext?.location,
    initialNatalContext?.latitude,
    initialNatalContext?.longitude,
    initialNatalContext?.snapId,
    initialNatalContext?.time,
    initialNatalContext?.timezone,
  ]);

  useEffect(() => {
    if (!open || !initialNatalContext || typeof initialNatalContext !== 'object') return;
    if (selectedSnapId || !snaps.length) return;
    const inferredSnapId = findMatchingSnapId(eligibleSnaps, initialNatalContext);
    if (!inferredSnapId) return;
    setSelectedSnapId(inferredSnapId);
    setSourceMode('snap');
  }, [
    findMatchingSnapId,
    initialNatalContext,
    open,
    selectedSnapId,
    eligibleSnaps,
  ]);

  // When a layer is disabled, clear its stored window and UI inputs to avoid accidental use
  useEffect(() => {
    const clearLayer = (key) => {
      try {
        if (key === 'pd' && !layersEnabled.pd) {
          window.__pdStart = undefined; window.__pdEnd = undefined;
          const ids = ['pd-start-date','pd-start-time','pd-end-date','pd-end-time'];
          ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
        }
        if (key === 'prog' && !layersEnabled.prog) {
          window.__progStart = undefined; window.__progEnd = undefined;
          const ids = ['prog-start-date','prog-start-time','prog-end-date','prog-end-time'];
          ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
        }
        if (key === 'sa' && !layersEnabled.sa) {
          window.__saStart = undefined; window.__saEnd = undefined;
          const ids = ['sa-start-date','sa-start-time','sa-end-date','sa-end-time'];
          ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
        }
      } catch(_) {}
    };
    ['pd','prog','sa'].forEach(clearLayer);
  }, [layersEnabled]);

  // Explicit action to clear all context windows and disable their use
  const clearAllContext = () => {
    try {
      window.__pdStart = undefined; window.__pdEnd = undefined;
      window.__progStart = undefined; window.__progEnd = undefined;
      window.__saStart = undefined; window.__saEnd = undefined;
      window.__pdMeta = undefined; window.__saMeta = undefined;
      ['pd','prog','sa'].forEach((key)=>{
        const ids = [`${key}-start-date`,`${key}-start-time`,`${key}-end-date`,`${key}-end-time`];
        ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
      });
    } catch(_) {}
    setUseContextWindows(false);
  };

  const timeline = Array.isArray(series) ? series : [];
  const fallbackStep = useMemo(() => buildStepFromResult(result, result?.transit_timestamp || null), [result, buildStepFromResult]);
  const computeStep = activeStep || fallbackStep;
  const transits = Array.isArray(result?.transits) ? result.transits : [];
  const computeStepScore = computeStep ? timelineStepScore(computeStep) : 0;
  const computeStepTone = computeStep ? morinStepTone(computeStep) : 'mixed';
  const computeTags = computeStep ? collectMorinTags(computeStep, showTechTags) : [];
  const computeCriticalSignals = computeStep ? collectCriticalSignalSummary(computeStep) : { chips: [], descriptions: [] };
  const computeCount = computeStep ? (typeof computeStep.count === 'number' ? computeStep.count : transits.length) : 0;
  const computeTimestamp = computeStep?.timestamp || result?.transit_timestamp || null;
  const hasExactVisibleResult = Boolean(
    computeStep
    && (
      transits.length > 0
      || (Array.isArray(computeStep?.predictions) && computeStep.predictions.length > 0)
      || computeCount > 0
      || computeTags.length > 0
      || computeCriticalSignals.chips.length > 0
      || computeCriticalSignals.descriptions.length > 0
    )
  );
  const scanCriticalRows = useMemo(() => collectSeriesCriticalRows(series, 24), [series]);
  const scanCriticalGroups = useMemo(() => collectGroupedSeriesCriticalRows(series, 4, 4), [series]);
  const hasCoarseScanStep = Number(stepMinutes || 0) >= 720;
  const predictorWindowBounds = useMemo(() => {
    const tzFallback =
      windowTz
      || result?.natal?.timezone
      || result?.natal?.timezone_label
      || natalTimezone
      || undefined;
    let startIso = buildIso(winStartDate, winStartTime, tzFallback);
    let endIso = buildIso(winEndDate, winEndTime, tzFallback);
    if (!startIso || !endIso) {
      const centerIso = buildIso(transitDate, transitTime, tzFallback);
      if (centerIso) {
        const centerDate = new Date(centerIso);
        if (!Number.isNaN(centerDate.getTime())) {
          const halfWindowMs = 12 * 60 * 60 * 1000;
          startIso = (new Date(centerDate.getTime() - halfWindowMs)).toISOString();
          endIso = (new Date(centerDate.getTime() + halfWindowMs)).toISOString();
        }
      }
    }
    return { startIso, endIso };
  }, [
    windowTz,
    result?.natal?.timezone,
    result?.natal?.timezone_label,
    natalTimezone,
    winStartDate,
    winStartTime,
    winEndDate,
    winEndTime,
    transitDate,
    transitTime,
  ]);
  const predictorStepPlan = useMemo(
    () => derivePredictorStepPlan(stepMinutes, predictorWindowBounds.startIso, predictorWindowBounds.endIso),
    [stepMinutes, predictorWindowBounds.startIso, predictorWindowBounds.endIso]
  );
  const predictorStepMinutes = predictorStepPlan.stepMinutes;
  const predictorStepWasClamped = predictorStepPlan.wasAdjusted;
  const predictorStepLabel = `${predictorStepMinutes}m`;
  const normalizePredictorGroup = useCallback((group) => {
    if (!group || typeof group !== 'object') return null;
    const toNumber = (value, fallback = null) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : fallback;
    };
    const occurrences = Array.isArray(group.occurrences)
      ? group.occurrences
          .filter((occ) => occ && typeof occ === 'object' && occ.date)
          .map((occ) => ({
            date: occ.date,
            probability: toNumber(occ.probability, null),
            score: toNumber(occ.score, null),
            supportScore: toNumber(occ.support_score ?? occ.supportScore, null),
          }))
      : [];
    const count = Math.max(0, toNumber(group.count, null) ?? occurrences.length);
    return {
      eventType: group.event_type || group.eventType || null,
      lifeArea: group.life_area || group.lifeArea || null,
      label: group.label || '',
      description: group.description || '',
      transit: group.transit || group.label || group.description || '',
      dominantTransit: group.dominant_transit || group.dominantTransit || group.transit || group.label || group.description || '',
      occurrences,
      tags: Array.isArray(group.tags) ? group.tags : [],
      keywordTokens: Array.isArray(group.keyword_tokens)
        ? group.keyword_tokens
        : (Array.isArray(group.keywordTokens) ? group.keywordTokens : []),
      probabilityMax: toNumber(group.probability_max ?? group.probabilityMax, 0),
      probabilityMean: toNumber(group.probability_mean ?? group.probabilityMean, 0),
      scoreMax: toNumber(group.score_max ?? group.scoreMax, null),
      scoreMean: toNumber(group.score_mean ?? group.scoreMean, null),
      supportScore: toNumber(group.support_score ?? group.supportScore, null),
      supportDensity: toNumber(group.support_density ?? group.supportDensity, null),
      supportFocus: toNumber(group.support_focus ?? group.supportFocus, null),
      dominantTimestamp: group.dominant_timestamp || group.dominantTimestamp || null,
      determinationStrengthMax: toNumber(group.determination_strength_max ?? group.determinationStrengthMax, null),
      domainAlignmentMax: toNumber(group.domain_alignment_max ?? group.domainAlignmentMax, null),
      windowSpanMinutes: toNumber(group.window_span_minutes ?? group.windowSpanMinutes, null),
      windowSteps: toNumber(group.window_steps ?? group.windowSteps, null),
      clusterIndex: toNumber(group.cluster_index ?? group.clusterIndex, null),
      supportingLabels: Array.isArray(group.supporting_labels)
        ? group.supporting_labels.filter(Boolean)
        : (Array.isArray(group.supportingLabels) ? group.supportingLabels.filter(Boolean) : []),
      supportingTransits: Array.isArray(group.supporting_transits)
        ? group.supporting_transits.filter(Boolean)
        : (Array.isArray(group.supportingTransits) ? group.supportingTransits.filter(Boolean) : []),
      count,
      start: group.start || occurrences[0]?.date || null,
      end: group.end || occurrences[occurrences.length - 1]?.date || null,
    };
  }, []);
  const aggregatedPredictions = useMemo(() => {
    if (!predictorResults) {
      return [];
    }
    if (Array.isArray(predictorResults.prediction_groups) && predictorResults.prediction_groups.length) {
      return predictorResults.prediction_groups
        .map(normalizePredictorGroup)
        .filter(Boolean)
        .slice(0, 5);
    }
    if (!Array.isArray(predictorResults.predictions)) {
      return [];
    }
    const predictorGroupingStep = Number(
      predictorResults?.step_minutes ?? predictorStepMinutes ?? 60
    ) || 60;
    const groups = new Map();
    predictorResults.predictions.forEach((item) => {
      if (!item) return;
      const predictionLabel = item.label || item.factors?.transit || '';
      const key = [
        item.event_type || '',
        predictionLabel,
        item.life_area || '',
        item.description || '',
      ].join('|');
      const existing = groups.get(key) || {
        eventType: item.event_type || null,
        lifeArea: item.life_area || null,
        label: predictionLabel,
        description: item.description || '',
        transit: predictionLabel,
        occurrences: [],
        tags: new Set(),
        probabilityMax: 0,
        scoreMax: null,
      };
      existing.occurrences.push({
        date: item.date,
        probability: typeof item.probability === 'number' ? item.probability : null,
        score: typeof item.score === 'number' ? item.score : null,
      });
      if (typeof item.probability === 'number') {
        existing.probabilityMax = Math.max(existing.probabilityMax, item.probability);
      }
      if (typeof item.score === 'number') {
        existing.scoreMax = existing.scoreMax == null ? item.score : Math.max(existing.scoreMax, item.score);
      }
      if (Array.isArray(item.tags)) {
        item.tags.forEach((tag) => existing.tags.add(tag));
      }
      groups.set(key, existing);
    });
    const aggregated = Array.from(groups.values()).flatMap((entry) => {
      const clusters = clusterPredictorOccurrences(entry.occurrences, predictorGroupingStep);
      return clusters.map((occurrences, clusterIndex) => {
        const start = occurrences[0]?.date || null;
        const end = occurrences[occurrences.length - 1]?.date || null;
        const startMs = new Date(String(start || '')).getTime();
        const endMs = new Date(String(end || '')).getTime();
        const windowSpanMinutes = (
          Number.isFinite(startMs) && Number.isFinite(endMs) && endMs >= startMs
            ? (endMs - startMs) / 60000
            : 0
        );
        const windowSteps = Math.max(1, (windowSpanMinutes / predictorGroupingStep) + 1);
        const occurrenceSupportValue = (occ) => {
          if (!occ || typeof occ !== 'object') return 0;
          if (occ.supportScore != null) return Number(occ.supportScore) || 0;
          return (Number(occ.probability || 0) * 100) + Number(occ.score || 0);
        };
        const dominantOccurrence = occurrences.reduce((best, occ) => {
          const occSupport = occurrenceSupportValue(occ);
          const bestSupport = best ? occurrenceSupportValue(best) : -Infinity;
          return occSupport > bestSupport ? occ : best;
        }, null);
        const supportScore = occurrences.reduce(
          (sum, occ) => sum + occurrenceSupportValue(occ),
          0
        );
        const supportDensity = supportScore / windowSteps;
        const supportFocus = (
          supportScore > 0 && supportDensity > 0
            ? Math.sqrt(supportScore * supportDensity)
            : Math.max(supportScore, supportDensity)
        );
        return {
          ...entry,
          tags: Array.from(entry.tags),
          keywordTokens: [],
          occurrences,
          count: occurrences.length,
          start,
          end,
          dominantTimestamp: dominantOccurrence?.date || null,
          supportScore,
          supportDensity,
          supportFocus,
          windowSpanMinutes,
          clusterIndex,
        };
      });
    });
    aggregated.sort((a, b) => {
      const focusA = Number(a.supportFocus ?? 0);
      const focusB = Number(b.supportFocus ?? 0);
      if (focusB !== focusA) return focusB - focusA;
      const densityA = Number(a.supportDensity ?? 0);
      const densityB = Number(b.supportDensity ?? 0);
      if (densityB !== densityA) return densityB - densityA;
      const supportA = Number(a.supportScore ?? 0);
      const supportB = Number(b.supportScore ?? 0);
      if (supportB !== supportA) return supportB - supportA;
      const domainA = Number(a.domainAlignmentMax ?? 0);
      const domainB = Number(b.domainAlignmentMax ?? 0);
      if (domainB !== domainA) return domainB - domainA;
      const probabilityMeanA = Number(a.probabilityMean ?? 0);
      const probabilityMeanB = Number(b.probabilityMean ?? 0);
      if (probabilityMeanB !== probabilityMeanA) return probabilityMeanB - probabilityMeanA;
      const detA = Number(a.determinationStrengthMax ?? 0);
      const detB = Number(b.determinationStrengthMax ?? 0);
      if (detB !== detA) return detB - detA;
      if (b.probabilityMax !== a.probabilityMax) return b.probabilityMax - a.probabilityMax;
      const scoreA = a.scoreMax ?? -Infinity;
      const scoreB = b.scoreMax ?? -Infinity;
      return scoreB - scoreA;
    });
    return aggregated.slice(0, 5);
  }, [normalizePredictorGroup, predictorResults, predictorStepMinutes]);
  const extractPeakIso = (peak) => {
    if (!peak) return null;
    if (typeof peak === 'string') return peak;
    if (typeof peak === 'object') {
      if (typeof peak.timestamp === 'string') return peak.timestamp;
      if (typeof peak.time === 'string') return peak.time;
    }
    return null;
  };
  const peakTimestampSet = useMemo(() => {
    const out = new Set();
    (Array.isArray(peaks) ? peaks : []).forEach((peak) => {
      const ts = extractPeakIso(peak);
      if (ts) out.add(ts);
    });
    return out;
  }, [peaks]);
  const onTimelineClick = async (ts) => {
    try {
      const selectedRow = Array.isArray(series)
        ? series.find((row) => {
            try {
              const target = new Date(ts).getTime();
              return Number.isFinite(target) && Math.abs(new Date(row.timestamp).getTime() - target) < 60000;
            } catch (_) {
              return row.timestamp === ts;
            }
          })
        : null;
      setActiveStep(selectedRow || null);
      const inputTimezone =
        windowTz
        || result?.natal?.timezone
        || result?.natal?.timezone_label
        || natalTimezone
        || 'UTC';
      const inputParts = formatIsoForInputFields(ts, inputTimezone);
      if (inputParts) {
        setTransitDate(inputParts.date);
        setTransitTime(inputParts.time);
      }
      // Pass ISO directly to avoid relying on async state updates
      await handleCompute((selectedRow && selectedRow.timestamp) || ts);
    } catch(_) {}
  };
  const triggerFileDownload = (blob, fallbackName, suggestedName) => {
    if (!(blob instanceof Blob) || blob.size <= 0) {
      throw new Error('Export returned an empty file.');
    }
    const downloadName = (typeof suggestedName === 'string' && suggestedName.trim())
      ? suggestedName.trim()
      : fallbackName;
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = downloadName;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1200);
  };

  const handleDownloadSingle = async () => {
    try {
      setError(null);
      const useSnap = (sourceMode === 'snap');
      const tzFallback = windowTz || result?.natal?.timezone || result?.natal?.timezone_label || natalTimezone || undefined;
      const natalIso = useSnap ? null : buildIso(natalDate, natalTime, natalTimezone || tzFallback);
      const transitIso = (transitDate && transitTime) ? buildIso(transitDate, transitTime, tzFallback) : undefined;
      const focusPlanetsList = focusPlanets.split(',').map(s => s.trim()).filter(Boolean);
      const payload = useSnap ? {
        natalSnapId: selectedSnapId,
        houseSystem,
        transitDatetime: transitIso,
        includeModern,
        includeNatalModern,
        includeCusps: includeCusps || (sensitiveHouses && sensitiveHouses.length>0),
        includeAntiscia,
        includeLots,
        focusHouses,
        focusPlanets: focusPlanetsList,
        sensitiveHouses,
        sensitivePlanets,
      } : {
        natalDatetime: natalIso,
        natalLocation,
        natalTimezone: natalTimezone || undefined,
        ...natalCoordinateContext,
        houseSystem,
        transitDatetime: transitIso,
        includeModern,
        includeNatalModern,
        includeCusps: includeCusps || (sensitiveHouses && sensitiveHouses.length>0),
        includeAntiscia,
        includeLots,
        focusHouses,
        focusPlanets: focusPlanetsList,
        sensitiveHouses,
        sensitivePlanets,
      };
      const exported = await AstroClockAPI.exportTransits(payload);
      triggerFileDownload(exported.blob, 'transits_export.csv', exported.filename);
    } catch (err) {
      setError(String(err?.message || err || 'Failed to export transits.'));
    }
  };
  const handleDownloadWindow = async () => {
    try {
      setError(null);
      const useSnap = (sourceMode === 'snap');
      const tzFallback = windowTz || result?.natal?.timezone || result?.natal?.timezone_label || natalTimezone || undefined;
      const startIso = buildIso(winStartDate, winStartTime, tzFallback);
      const endIso = buildIso(winEndDate, winEndTime, tzFallback);
      const hasRange = Boolean(startIso && endIso);
      const centerIso = buildIso(transitDate, transitTime, tzFallback);
      const focusPlanetsList = focusPlanets.split(',').map(s => s.trim()).filter(Boolean);
      const base = useSnap ? { natalSnapId: selectedSnapId } : {
        natalDatetime: buildIso(natalDate, natalTime, natalTimezone || tzFallback),
        natalLocation,
        natalTimezone: natalTimezone || undefined,
        ...natalCoordinateContext,
      };
      const exported = await AstroClockAPI.exportTransitsWindow({
        ...base,
        houseSystem,
        start: startIso || undefined,
        end: endIso || undefined,
        center: !hasRange ? (centerIso || undefined) : undefined,
        rangeHours: !hasRange ? defaultRangeHours : undefined,
        stepMinutes,
        includeModern,
        includeNatalModern,
        includeCusps: includeCusps || (sensitiveHouses && sensitiveHouses.length>0),
        includeAntiscia,
        includeLots,
        focusHouses,
        focusPlanets: focusPlanetsList,
        sensitiveHouses,
        sensitivePlanets,
        pdStart: (useContextWindows && layersEnabled.pd) ? (window.__pdStart || undefined) : undefined,
        pdEnd: (useContextWindows && layersEnabled.pd) ? (window.__pdEnd || undefined) : undefined,
        progStart: (useContextWindows && layersEnabled.prog) ? (window.__progStart || undefined) : undefined,
        progEnd: (useContextWindows && layersEnabled.prog) ? (window.__progEnd || undefined) : undefined,
        saStart: (useContextWindows && layersEnabled.sa) ? (window.__saStart || undefined) : undefined,
        saEnd: (useContextWindows && layersEnabled.sa) ? (window.__saEnd || undefined) : undefined,
      });
      triggerFileDownload(exported.blob, 'transits_window_export.csv', exported.filename);
    } catch (err) {
      setError(String(err?.message || err || 'Failed to export transits window.'));
    }
  };
  // Visual helpers for glyph colors and target rendering
  const planetColor = (nm) => {
    if (!nm) return 'text-zinc-800';
    if (nm === 'Saturn' || nm === 'Mars') return 'text-red-700';
    if (nm === 'Jupiter' || nm === 'Venus') return 'text-green-700';
    if (nm === 'Sun' || nm === 'Moon') return 'text-amber-700';
    return 'text-blue-700';
  };
  const targetColor = (t) => {
    const type = (t?.target_type) || '';
    const label = String((t?.target_label) || t?.natal || '')
      .replace(/ \(antiscia\)$/i, '')
      .replace(/ \(contra-antiscia\)$/i, '');
    if (type === 'cusp' || label === 'Asc' || label === 'MC' || /^C\d+$/.test(label)) return 'text-violet-700';
    if (type === 'antiscia' || type === 'contra_antiscia') return 'text-indigo-700';
    if (type === 'lot' || label === 'POF') return 'text-amber-700';
    return planetColor(label);
  };
  const targetDisplayMeta = (target) => {
    const type = (target && typeof target === 'object') ? String(target.target_type || '') : '';
    const rawLabel = (target && typeof target === 'object')
      ? String(target.target_label || target.natal || '')
      : String(target || '');
    let badge = null;
    let baseLabel = rawLabel;
    if (type === 'antiscia' || / \(antiscia\)$/i.test(rawLabel)) {
      baseLabel = rawLabel.replace(/ \(antiscia\)$/i, '');
      badge = 'A';
    } else if (type === 'contra_antiscia' || / \(contra-antiscia\)$/i.test(rawLabel)) {
      baseLabel = rawLabel.replace(/ \(contra-antiscia\)$/i, '');
      badge = 'CA';
    }
    return {
      rawLabel,
      baseLabel,
      badge,
      display: PlanetSymbols[baseLabel] || baseLabel,
    };
  };
  const renderTargetLabel = (target, compact = false) => {
    const meta = targetDisplayMeta(target);
    const badgeCls = compact
      ? 'inline-flex min-w-[1.05rem] items-center justify-center rounded-full border border-indigo-200 bg-indigo-50 px-1 py-[1px] text-[9px] font-semibold uppercase tracking-[0.18em] text-indigo-700'
      : 'inline-flex min-w-[1.25rem] items-center justify-center rounded-full border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-indigo-700';
    return (
      <span className="inline-flex items-center gap-1.5 align-middle">
        <span>{meta.display}</span>
        {meta.badge ? <span className={badgeCls}>{meta.badge}</span> : null}
      </span>
    );
  };

  const maxStepScore = useMemo(
    () => timeline.reduce((m, r) => Math.max(m, timelineStepScore(r)), 0),
    [timeline]
  );
  // Apply intersection of PD ∩ Prog ∩ SA into the Scan Window inputs
  const handleUseIntersectionRange = () => {
    const inputTimezone = getTransitInputTimezone();
    const getIso = (dateId, timeId, backup) => {
      try {
        const d = document.getElementById(dateId)?.value;
        const t = document.getElementById(timeId)?.value;
        if (d && t) return buildIso(d, t, inputTimezone);
      } catch(_){ }
      return backup || null;
    };
    const pdS = layersEnabled.pd ? getIso('pd-start-date','pd-start-time', window.__pdStart) : null;
    const pdE = layersEnabled.pd ? getIso('pd-end-date','pd-end-time', window.__pdEnd) : null;
    const prS = layersEnabled.prog ? getIso('prog-start-date','prog-start-time', window.__progStart) : null;
    const prE = layersEnabled.prog ? getIso('prog-end-date','prog-end-time', window.__progEnd) : null;
    const saS = layersEnabled.sa ? getIso('sa-start-date','sa-start-time', window.__saStart) : null;
    const saE = layersEnabled.sa ? getIso('sa-end-date','sa-end-time', window.__saEnd) : null;
    const starts = [pdS, prS, saS].filter(Boolean).map(s=> new Date(s));
    const ends = [pdE, prE, saE].filter(Boolean).map(s=> new Date(s));
    if (!starts.length || !ends.length) { setError('No context windows to intersect.'); return; }
    const start = new Date(Math.max.apply(null, starts.map(x=> x.getTime())));
    const end = new Date(Math.min.apply(null, ends.map(x=> x.getTime())));
    if (!(end > start)) { setError('No intersection among PD/Progressions/Solar Arc. Using current scan range.'); return; }
    const startParts = formatIsoForInputFields(start.toISOString(), inputTimezone);
    const endParts = formatIsoForInputFields(end.toISOString(), inputTimezone);
    if (!startParts || !endParts) { setError('Could not format context intersection in the chart timezone.'); return; }
    setWinStartDate(startParts.date); setWinStartTime(startParts.time);
    setWinEndDate(endParts.date); setWinEndTime(endParts.time);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex items-start justify-center p-4 overflow-auto">
      {/* Floating close for overlay (consistent with Forensic) */}
      <div className="absolute top-4 right-4">
        <div role="button" tabIndex={0} onClick={close}
             onKeyDown={(e)=>{ if (e.key==='Enter' || e.key===' ') { e.preventDefault(); close(); } }}
             className="text-[11px] px-2 py-0.5 border rounded bg-white/90 hover:bg-white cursor-pointer select-none shadow">Close</div>
      </div>
      <div className="relative w-full max-w-4xl">
        <div className="rounded-2xl border shadow-xl p-6 max-h-[85vh] overflow-auto 
                bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl 
                border-gray-200/80 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Transits</h2>
            <button onClick={close} className="text-zinc-600 hover:text-black">✕</button>
          </div>

        {/* Source selector */}
        <div className="mb-3 flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <input id="src-manual" type="radio" name="src" checked={sourceMode==='manual'} onChange={()=> setSourceMode('manual')} />
            <label htmlFor="src-manual">Manual Natal</label>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="src-snap"
              type="radio"
              name="src"
              checked={sourceMode==='snap'}
              disabled={!eligibleSnaps.length}
              onChange={()=> setSourceMode('snap')}
            />
            <label htmlFor="src-snap">Saved Snap</label>
          </div>
        </div>

        {/* Saved Snap picker (visible when snap mode) */}
        {sourceMode === 'snap' && (
          <div className="mb-4 flex items-center gap-2">
            <select className="border rounded px-2 py-1" value={selectedSnapId} onChange={e=> setSelectedSnapId(e.target.value)}>
              <option value="">Select a snap…</option>
              {snaps.map(s => (
                <option
                  key={s.id}
                  value={s.id}
                  disabled={!isSavedSnapCalculationEligible(s)}
                >
                  {s.label || s.id} · {formatSavedSnapDateTime(s)} · {getSavedSnapTimezoneLabel(s)}
                  {getSavedSnapIneligibilityLabel(s)
                    ? ` — ${getSavedSnapIneligibilityLabel(s)}`
                    : ''}
                </option>
              ))}
            </select>
            <button type="button" onClick={loadSnaps} className="text-xs px-2 py-1 border rounded">Refresh</button>
            {selectedSnapId ? (
              <button type="button" onClick={()=> setSelectedSnapId('')} className="text-xs px-2 py-1 border rounded">Clear</button>
            ) : null}
            <span className="text-xs text-zinc-600">Manual fields are ignored when a snap is selected.</span>
            {snaps.some((snap) => !isSavedSnapCalculationEligible(snap)) ? (
              <span className="font-serif text-xs italic leading-5 text-zinc-500">
                Review-required and superseded saved charts are disabled. Use a corrected copy from Astro Clock.
              </span>
            ) : null}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Manual-only natal inputs */}
          {sourceMode === 'manual' && (<>
          <div>
            <label className="block text-xs text-zinc-600 mb-1">Natal Date</label>
            <input type="date" value={natalDate} onChange={e=>setNatalDate(e.target.value)} className="w-full min-w-[11rem] border rounded px-2 py-1" />
          </div>
          <div>
            <label className="block text-xs text-zinc-600 mb-1">Natal Time</label>
            <input
              type="time"
              lang="en-GB"
              inputMode="numeric"
              step="60"
              placeholder="HH:MM"
              value={natalTime}
              onChange={e=>setNatalTime(e.target.value)}
              className="w-full border rounded px-2 py-1"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs text-zinc-600 mb-1">Natal Location</label>
            <input
              type="text"
              placeholder="City, Country"
              value={natalLocation}
              onChange={e=> {
                setNatalLocation(e.target.value);
                setNatalLatitude(undefined);
                setNatalLongitude(undefined);
              }}
              className="w-full border rounded px-2 py-1"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-600 mb-1">Time Zone (IANA)</label>
            <input type="text" placeholder="e.g., Europe/London" value={natalTimezone} onChange={e=>setNatalTimezone(e.target.value)} className="w-full border rounded px-2 py-1" />
          </div>
          </>)}
          <div>
            <label className="block text-xs text-zinc-600 mb-1">House System</label>
            <div className="w-full border rounded px-2 py-1 bg-zinc-50 text-zinc-700">Regiomontanus</div>
          </div>
          <div>
            <label className="block text-xs text-zinc-600 mb-1">Transit Date (optional)</label>
            <input type="date" value={transitDate} onChange={e=>setTransitDate(e.target.value)} className="w-full min-w-[11rem] border rounded px-2 py-1" />
          </div>
          <div>
            <label className="block text-xs text-zinc-600 mb-1">Transit Time (optional)</label>
            <input
              type="time"
              lang="en-GB"
              inputMode="numeric"
              step="60"
              placeholder="HH:MM"
              value={transitTime}
              onChange={e=>setTransitTime(e.target.value)}
              className="w-full border rounded px-2 py-1"
            />
          </div>
          {/* Modern flags moved into Filters panel below */}

          <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <label className="text-xs text-zinc-600">Sensitive Houses</label>
                <button type="button" className="text-[10px] px-1.5 py-0.5 border rounded" onClick={()=> setSensitiveHouses([])}>None</button>
                <button type="button" className="text-[10px] px-1.5 py-0.5 border rounded" onClick={()=> setSensitiveHouses([1,10])}>Angles (1/10)</button>
                <button type="button" className="text-[10px] px-1.5 py-0.5 border rounded" onClick={()=> setSensitiveHouses([1,4,7,10])}>Angular</button>
                <button type="button" className="text-[10px] px-1.5 py-0.5 border rounded" onClick={()=> setSensitiveHouses([1,2,3,4,5,6,7,8,9,10,11,12])}>All</button>
              </div>
              <div className="flex flex-wrap gap-1">
                {Array.from({length:12}, (_,i)=> i+1).map(h => (
                  <button key={h} type="button" className={`text-[11px] px-1.5 py-0.5 border rounded ${sensitiveHouses.includes(h)? 'bg-zinc-900 text-white border-zinc-900':'bg-white'}`} onClick={()=> {
                    setSensitiveHouses(prev => prev.includes(h) ? prev.filter(x=>x!==h) : [...prev, h]);
                    setIncludeCusps(true);
                  }}>C{h}</button>
                ))}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={includeCusps} onChange={e=>setIncludeCusps(e.target.checked)} /> Include cusps</label>
                <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={includeAntiscia} onChange={e=>setIncludeAntiscia(e.target.checked)} /> Antiscia</label>
                <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={includeLots} onChange={e=>setIncludeLots(e.target.checked)} /> Part of Fortune</label>
                <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={includeModern} onChange={e=>setIncludeModern(e.target.checked)} /> Transiting modern</label>
                <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={includeNatalModern} onChange={e=>setIncludeNatalModern(e.target.checked)} /> Natal modern</label>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-zinc-600 mb-1">Focus Houses (comma sep)</label>
                <input type="text" placeholder="e.g., 1,10" value={focusHouses.join(',')} onChange={e=>{
                  const list = e.target.value.split(',').map(s=>parseInt(s.trim(),10)).filter(n=>!isNaN(n) && n>=1 && n<=12);
                  setFocusHouses(list);
                }} className="w-full border rounded px-2 py-1" />
              </div>
              <div>
                <label className="block text-xs text-zinc-600 mb-1">Focus Planets (comma sep)</label>
                <input type="text" placeholder="e.g., Saturn, Jupiter" value={focusPlanets} onChange={e=>setFocusPlanets(e.target.value)} className="w-full border rounded px-2 py-1" />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs text-zinc-600 mb-1">Sensitive Planets</label>
                <div className="flex items-center gap-2 mb-1">
                  <button type="button" className="text-[10px] px-1.5 py-0.5 border rounded" onClick={()=> setSensitivePlanets([])}>None</button>
                  <button type="button" className="text-[10px] px-1.5 py-0.5 border rounded" onClick={()=> setSensitivePlanets(classicalPlanets)}>Classical</button>
                  <button type="button" className="text-[10px] px-1.5 py-0.5 border rounded" onClick={()=> setSensitivePlanets([...classicalPlanets, ...(includeNatalModern? modernPlanets: [])])}>All</button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {classicalPlanets.concat(includeNatalModern? modernPlanets: []).map(p => (
                    <button
                      key={p}
                      type="button"
                      className={`text-[11px] px-1.5 py-0.5 border rounded ${sensitivePlanets.includes(p)? 'bg-zinc-900 text-white border-zinc-900':'bg-white'}`}
                      onClick={()=> setSensitivePlanets(prev => prev.includes(p)? prev.filter(x=>x!==p): [...prev, p])}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 mb-4">
          <button type="button" onClick={handleAutoContext} className="px-2 py-1 rounded border">Suggest Context Windows</button>
          {!isProd && (
            <>
              <button type="button" onClick={handleDownloadSingle} className="px-2 py-1 rounded border">Download Excel</button>
              <button type="button" onClick={handleDownloadWindow} className="px-2 py-1 rounded border">Download Window Excel</button>
            </>
          )}
          {result && <span className="text-xs text-zinc-600">Transit time: {formatTsCompact(result.transit_timestamp, result?.natal?.timezone)}</span>}
          <span className="text-[11px] text-zinc-500">Scan highlights strong windows; compute the exact time entered above or click a peak below.</span>
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>
        {!isProd && (
        <div className="mb-2">
          <button type="button" onClick={()=> setShowDebugAuto(v=>!v)} className="px-2 py-1 rounded border text-[11px]">{showDebugAuto? 'Hide Auto-Context Debug':'Show Auto-Context Debug'}</button>
          {showDebugAuto && (
            <div className="mt-2 text-[11px] text-zinc-700 border rounded p-2 bg-zinc-50">
              <div><strong>Auto-Context Request</strong></div>
              <div className="break-all">{debugAutoCtx?.request||'-'}</div>
              <div className="mt-1">anchor: {debugAutoCtx?.anchor?.start||'-'} → {debugAutoCtx?.anchor?.end||'-'} (center: {debugAutoCtx?.anchor?.center||'-'})</div>
              <div className="mt-1">SR: {debugAutoCtx?.sr?.ts||'-'} {debugAutoCtx?.sr?.window? `| window ${debugAutoCtx.sr.window.start} → ${debugAutoCtx.sr.window.end}`:''}</div>
              <div className="mt-1">counts: PD {debugAutoCtx?.counts?.pd||0}, Prog {debugAutoCtx?.counts?.prog||0}</div>
            </div>
          )}
        </div>
        )}

        {(solarSummary || lunarSummary) && (
          <div className="mb-4 grid gap-3 md:grid-cols-2">
            <RevolutionCard
              title="Solar Revolution"
              summary={solarSummary}
              score={solarScore}
              timezone={natalTz}
            />
            <RevolutionCard
              title="Lunar Revolution"
              summary={lunarSummary}
              score={lunarScore}
              timezone={natalTz}
            />
          </div>
        )}

        <div className="mt-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-sm">Scan Window</h3>
            <div className="flex items-center gap-2 text-xs">
              <button type="button" onClick={()=> fillNowWindow(7)} className="px-2 py-0.5 rounded border">Now → +7d</button>
              <button type="button" onClick={()=> fillNowWindow(30)} className="px-2 py-0.5 rounded border">Now → +30d</button>
            </div>
          </div>
          {/* Layer toggles (include/exclude from Suggest + Intersection) */}
          <div className="flex items-center gap-3 text-xs mb-2">
            {[
              {key:'pd', label:'PD'},
              {key:'prog', label:'Prog'},
              {key:'sa', label:'SA'},
            ].map(cfg => (
              <label key={cfg.key} className="flex items-center gap-1">
                <input type="checkbox" checked={!!layersEnabled[cfg.key]} onChange={(e)=> setLayersEnabled(prev => ({ ...prev, [cfg.key]: e.target.checked }))} />
                {cfg.label}
              </label>
            ))}
          </div>
          {/* Use context in scans/predictions */}
          <div className="flex items-center justify-between mb-2 text-xs">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={useContextWindows} onChange={e=> setUseContextWindows(e.target.checked)} />
              Use context windows (PD/Prog/SA) in scan & predictions
            </label>
            <button type="button" onClick={clearAllContext} className="px-2 py-0.5 rounded border">Clear Context</button>
          </div>
          {/* Context windows for PD/SR/Progressions/LR/SA (optional) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mb-3">
            {[
              {key:'pd', label:'Primary Directions'},
              {key:'prog', label:'Progressions'},
              {key:'sa', label:'Solar Arc'},
            ].map(cfg => (
              <div key={cfg.key}>
                <label className="block text-xs text-zinc-600 mb-1">{cfg.label} Window</label>
                <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_7.5rem] gap-2 mb-1">
                  <input type="date" placeholder="Start" id={`${cfg.key}-start-date`} className="w-full min-w-[11rem] border rounded px-2 py-1" onChange={(e)=>{
                    const date = e.target.value; const time = document.getElementById(`${cfg.key}-start-time`)?.value || '00:00';
                    const iso = buildContextIsoFromInputs(date, time, '00:00');
                    setStoredContextIso(cfg.key, 'start', iso);
                  }} />
                  <input
                    type="time"
                    lang="en-GB"
                    inputMode="numeric"
                    step="60"
                    placeholder="HH:MM"
                    id={`${cfg.key}-start-time`}
                    className="w-full min-w-[7.5rem] border rounded px-2 py-1"
                    onChange={(e)=>{
                    const time = e.target.value; const date = document.getElementById(`${cfg.key}-start-date`)?.value || '';
                    const iso = buildContextIsoFromInputs(date, time, '00:00');
                    setStoredContextIso(cfg.key, 'start', iso);
                  }} />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_7.5rem] gap-2">
                  <input type="date" placeholder="End" id={`${cfg.key}-end-date`} className="w-full min-w-[11rem] border rounded px-2 py-1" onChange={(e)=>{
                    const date = e.target.value; const time = document.getElementById(`${cfg.key}-end-time`)?.value || '23:59';
                    const iso = buildContextIsoFromInputs(date, time, '23:59');
                    setStoredContextIso(cfg.key, 'end', iso);
                  }} />
                  <input
                    type="time"
                    lang="en-GB"
                    inputMode="numeric"
                    step="60"
                    placeholder="HH:MM"
                    id={`${cfg.key}-end-time`}
                    className="w-full min-w-[7.5rem] border rounded px-2 py-1"
                    onChange={(e)=>{
                    const time = e.target.value; const date = document.getElementById(`${cfg.key}-end-date`)?.value || '';
                    const iso = buildContextIsoFromInputs(date, time, '23:59');
                    setStoredContextIso(cfg.key, 'end', iso);
                  }} />
                </div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs text-zinc-600 mb-1">Start</label>
              <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_7.5rem] gap-2">
                <input
                  type="date"
                  aria-label="Scan start date"
                  title="YYYY-MM-DD"
                  value={winStartDate}
                  onChange={e=>setWinStartDate(e.target.value)}
                  className="w-full min-w-[11rem] border rounded px-2 py-1"
                />
                <input
                  type="time"
                  aria-label="Scan start time"
                  lang="en-GB"
                  inputMode="numeric"
                  step="60"
                  placeholder="HH:MM"
                  value={winStartTime}
                  onChange={e=>setWinStartTime(e.target.value)}
                  className="w-full min-w-[7.5rem] border rounded px-2 py-1"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-zinc-600 mb-1">End</label>
              <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_7.5rem] gap-2">
                <input
                  type="date"
                  aria-label="Scan end date"
                  title="YYYY-MM-DD"
                  value={winEndDate}
                  onChange={e=>setWinEndDate(e.target.value)}
                  className="w-full min-w-[11rem] border rounded px-2 py-1"
                />
                <input
                  type="time"
                  aria-label="Scan end time"
                  lang="en-GB"
                  inputMode="numeric"
                  step="60"
                  placeholder="HH:MM"
                  value={winEndTime}
                  onChange={e=>setWinEndTime(e.target.value)}
                  className="w-full min-w-[7.5rem] border rounded px-2 py-1"
                />
              </div>
            </div>
          </div>

          <div className="mb-3">
            <label className="block text-xs text-zinc-600 mb-1">Step (min)</label>
            <input
              type="number"
              min="1"
              value={stepMinutes}
              onChange={e=>{
                const v = Math.max(1, Number(e.target.value||60));
                setStepMinutes(v);
              }}
              className="w-full border rounded px-2 py-1"
              placeholder="e.g., 60"
            />
            <div className="mt-1 flex items-center gap-2 flex-nowrap overflow-x-auto w-full text-[10px] text-zinc-600">
              <span>≈ {Math.max(1, Math.round(1440 / (stepMinutes||60)))} scans/day</span>
              <span className="text-zinc-400">Quick picks:</span>
              {[15,30,60,120,180,360,720,1440].map(m => (
                <button key={m} type="button" onClick={()=> setStepMinutes(m)} className={`px-1.5 py-0.5 border rounded shrink-0 ${stepMinutes===m?'bg-zinc-800 text-white border-zinc-800':'bg-white'}`}>{m}m</button>
              ))}
            </div>
          </div>

          <div className="flex items-end mb-2 gap-2">
            <button disabled={scanning} onClick={() => {
              // append context windows into query by adding to URL via API call in doScan
              if (window.__pdStart) window.__pdStart; // no-op to keep eslint happy
              handleScanClick();
            }} className="px-4 py-1.5 rounded bg-zinc-900 text-white disabled:opacity-50">{scanning ? 'Scanning…' : 'Scan Window'}</button>
            <button type="button" onClick={handleUseIntersectionRange} className="px-2 py-1 rounded border" title="Set Scan Range to PD ∩ Prog ∩ SA">
              Use Intersection as Scan Range
            </button>
            <button
              type="button"
              onClick={handleComputeExactTime}
              disabled={computeLoading}
              className="px-2 py-1 rounded border text-[13px] hover:bg-zinc-100 disabled:opacity-50"
            >
              {computeLoading ? 'Computing…' : 'Compute Exact Time'}
            </button>
            <button
              type="button"
              onClick={runPredictor}
              disabled={predictorLoading}
              className="px-2 py-1 rounded border text-[13px] hover:bg-zinc-100 disabled:opacity-50"
            >
              {predictorLoading ? 'Predicting…' : 'Run Predictor'}
            </button>
            {!isProd && (
              <button type="button" onClick={()=> setShowDebugScan(v=>!v)} className="px-2 py-1 rounded border text-[11px]">{showDebugScan? 'Hide Debug':'Show Debug'}</button>
            )}
          </div>
          {predictorStepWasClamped && (
            <div className="mb-2 text-[11px] text-zinc-500">
              {predictorStepPlan.usesResponsiveFloor
                ? 'Predictor widened the step to keep long windows responsive instead of timing out on overly dense scans.'
                : 'Predictor refines coarse scans so repeated support is not blurred by daily rows.'}
            </div>
          )}
          {predictorError && (
            <div className="mb-2 text-sm text-rose-600">
              {predictorError}
            </div>
          )}
          {predictorResults && (
            <div className="mb-4 border rounded-lg p-3 bg-white/80 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="font-semibold text-sm text-zinc-800">Predictor Results</div>
                  {predictorResults.window && (
                    <div className="text-[11px] text-zinc-600">
                      {formatTsCompact(predictorResults.window.start, predictorResults?.observer?.timezone)} → {formatTsCompact(predictorResults.window.end, predictorResults?.observer?.timezone)}
                    </div>
                  )}
                  <div className="text-[11px] text-zinc-500">
                    Predictor step: {predictorStepLabel}{predictorStepPlan.usesResponsiveFloor ? ' (auto-tuned for window size)' : predictorStepWasClamped ? ' (finer than the current scan step)' : ''}
                  </div>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <div className="text-xs text-zinc-500 mb-1">Support Windows</div>
                  <div className="space-y-2">
                    {aggregatedPredictions.map((group, idx) => {
                      const title =
                        (group.eventType ? formatTokenLabel(group.eventType) : null) ||
                        (group.lifeArea ? formatTokenLabel(group.lifeArea) : null) ||
                        (group.label || null) ||
                        (group.description || null) ||
                        'Unclassified';
                      const transitLabel = group.transit
                        ? formatTokenLabel(group.transit)
                        : '';
                      const supportingTransits = Array.isArray(group.supportingTransits)
                        ? group.supportingTransits.filter((item) => item && item !== group.transit)
                        : [];
                      const detailLabel =
                        group.description && group.description !== title && group.description !== group.label
                          ? group.description
                          : null;
                      const tz = predictorResults?.observer?.timezone;
                      const windowLabel =
                        group.count > 1 && group.start && group.end
                          ? `${formatTsCompact(group.start, tz)} → ${formatTsCompact(group.end, tz)}`
                          : (group.start ? formatTsCompact(group.start, tz) : null);
                      const topOccurrences = group.occurrences.slice(0, 3);
                      const probabilityLabel = group.probabilityMax
                        ? `${Math.round(group.probabilityMax * 100)}%`
                        : null;
                      const probabilityMeanLabel = group.probabilityMean
                        ? `${Math.round(group.probabilityMean * 100)}% avg`
                        : null;
                      const scoreLabel = Number.isFinite(group.scoreMax)
                        ? Number(group.scoreMax).toFixed(1).replace(/\.0$/, '')
                        : null;
                      const supportLabel = Number.isFinite(group.supportScore)
                        ? Number(group.supportScore).toFixed(1).replace(/\.0$/, '')
                        : null;
                      const densityLabel = Number.isFinite(group.supportDensity)
                        ? Number(group.supportDensity).toFixed(1).replace(/\.0$/, '')
                        : null;
                      const lifeAreaLabel = group.lifeArea ? formatTokenLabel(group.lifeArea) : null;
                      const keywordTokens = Array.isArray(group.keywordTokens) && group.keywordTokens.length
                        ? group.keywordTokens
                        : (Array.isArray(group.tags) ? group.tags : []);
                      const strongestAtLabel = group.dominantTimestamp
                        ? formatTsCompact(group.dominantTimestamp, tz)
                        : null;
                      return (
                        <div key={idx} className="border rounded p-2 bg-zinc-50 text-xs text-zinc-700">
                          <div className="flex items-center justify-between gap-2">
                            <div className="font-medium text-zinc-800">{title}</div>
                            <div className="flex items-center gap-2 text-[11px] text-zinc-500">
                              {supportLabel && <span>Window support {supportLabel}</span>}
                              {densityLabel && <span>Density {densityLabel}</span>}
                              {scoreLabel && <span>Score {scoreLabel}</span>}
                              {probabilityLabel && <span className="text-indigo-600">{probabilityLabel}</span>}
                            </div>
                          </div>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-zinc-500">
                            {lifeAreaLabel && (
                              <span className="px-1 py-0.5 border border-zinc-300 rounded bg-white text-zinc-700">
                                {lifeAreaLabel}
                              </span>
                            )}
                            <span>{group.count} hit{group.count !== 1 ? 's' : ''}</span>
                            {probabilityMeanLabel && <span>{probabilityMeanLabel}</span>}
                          </div>
                          {windowLabel && (
                            <div className="mt-1 text-[11px] text-zinc-500">{windowLabel}</div>
                          )}
                          {strongestAtLabel && group.count > 1 && (
                            <div className="mt-1 text-[11px] text-zinc-500">Strongest at {strongestAtLabel}</div>
                          )}
                          {(transitLabel || detailLabel) && (
                            <div className="mt-1 text-[11px] text-zinc-600 italic space-y-0.5">
                              {transitLabel && <div>Transit: {transitLabel}</div>}
                              {detailLabel && <div>{detailLabel}</div>}
                              {supportingTransits.length > 0 && (
                                <div>
                                  Also supported by:{' '}
                                  {supportingTransits.slice(0, 3).map((item) => formatTokenLabel(item)).join(', ')}
                                  {supportingTransits.length > 3 ? ` +${supportingTransits.length - 3} more` : ''}
                                </div>
                              )}
                            </div>
                          )}
                          {topOccurrences.length > 0 && (
                            <ul className="mt-2 space-y-1 text-[11px] text-zinc-600">
                              {topOccurrences.map((occ, occIdx) => (
                                <li key={occIdx} className="flex items-center justify-between">
                                  <span>{formatTsCompact(occ.date, tz)}</span>
                                  <span className="text-zinc-500">
                                    {occ.probability != null ? `${Math.round(occ.probability * 100)}%` : ''}
                                    {occ.score != null ? `${occ.probability != null ? ' • ' : ''}score ${Number(occ.score).toFixed(1).replace(/\.0$/, '')}` : ''}
                                    {occ.supportScore != null ? `${(occ.probability != null || occ.score != null) ? ' • ' : ''}support ${Number(occ.supportScore).toFixed(1).replace(/\.0$/, '')}` : ''}
                                  </span>
                                </li>
                              ))}
                              {group.count > topOccurrences.length && (
                                <li className="text-[10px] text-zinc-500">
                                  +{group.count - topOccurrences.length} more in window
                                </li>
                              )}
                            </ul>
                          )}
                          {Array.isArray(keywordTokens) && keywordTokens.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {keywordTokens.slice(0, 5).map((tag, tIdx) => (
                                <span key={tIdx} className="px-1 py-0.5 rounded border border-zinc-300 bg-white text-[10px] text-zinc-700">
                                  {formatTokenLabel(tag)}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                    {aggregatedPredictions.length === 0 && (
                      <div className="text-xs text-zinc-500">No predictor highlights in this range.</div>
                    )}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500 mb-1">Peak Timestamps</div>
                  <div className="flex flex-col gap-1 text-xs text-zinc-700">
                    {(Array.isArray(predictorResults.peaks) ? predictorResults.peaks : []).slice(0,6).map((pk, idx) => {
                      const ts = typeof pk === 'string' ? pk : pk?.timestamp;
                      if (!ts) return null;
                      const peakTitle =
                        (pk && typeof pk === 'object' && pk.event_type ? formatTokenLabel(pk.event_type) : null) ||
                        (pk && typeof pk === 'object' && pk.life_area ? formatTokenLabel(pk.life_area) : null) ||
                        null;
                      const peakDetail =
                        pk && typeof pk === 'object' && typeof pk.description === 'string' && pk.description.trim()
                          ? pk.description.trim()
                          : null;
                      const peakSupport = pk && typeof pk === 'object' && Number.isFinite(Number(pk.support_score))
                        ? Number(pk.support_score).toFixed(1).replace(/\.0$/, '')
                        : null;
                      const peakKeywords = pk && typeof pk === 'object' && Array.isArray(pk.keyword_tokens)
                        ? pk.keyword_tokens
                        : [];
                      return (
                        <div key={idx} className="flex items-center justify-between border rounded px-2 py-1 bg-zinc-50">
                          <div className="min-w-0">
                            <div>{formatTsCompact(ts, predictorResults?.observer?.timezone)}</div>
                            {(peakTitle || peakDetail || peakSupport || peakKeywords.length) && (
                              <div className="mt-0.5 flex flex-wrap items-center gap-1 text-[10px] text-zinc-500">
                                {peakTitle && (
                                  <span className="px-1 py-0.5 rounded border border-zinc-300 bg-white text-zinc-700">
                                    {peakTitle}
                                  </span>
                                )}
                                {peakSupport && <span>support {peakSupport}</span>}
                                {peakDetail && <span className="italic">{peakDetail}</span>}
                                {peakKeywords.slice(0, 3).map((token, tokenIdx) => (
                                  <span key={tokenIdx} className="px-1 py-0.5 rounded border border-zinc-300 bg-white text-zinc-700">
                                    {formatTokenLabel(token)}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          {typeof onJumpToTime === 'function' && (
                            <button
                              type="button"
                              className="text-[10px] px-1 py-0.5 border rounded border-zinc-300 hover:bg-zinc-100"
                              onClick={()=> onJumpToTime(ts)}
                            >
                              Use
                            </button>
                          )}
                        </div>
                      );
                    })}
                    {( !predictorResults.peaks || predictorResults.peaks.length === 0) && (
                      <div className="text-xs text-zinc-500">No peaks identified.</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
          {!isProd && showDebugScan && (
            <div className="mb-2 text-[11px] text-zinc-700 border rounded p-2 bg-zinc-50">
              <div><strong>Scan Request</strong></div>
              <div className="break-all">{debugScan?.request||'-'}</div>
              <div className="mt-1">step: {debugScan?.stepMinutes||'-'} | series: {debugScan?.series||0} | peaks: {debugScan?.peaks||0}</div>
              {debugScan?.contextWindow && (<div>context_window: {formatTsCompact(debugScan.contextWindow.start, windowTz)} → {formatTsCompact(debugScan.contextWindow.end, windowTz)}</div>)}
            </div>
          )}
          {timeline.length ? (
            <>
            {/* Context-weighted toggle */}
            <div className="flex items-center justify-between mb-1">
              <div className="text-[11px] text-zinc-500">Timeline</div>
              <label className="flex items-center gap-2 text-[11px] text-zinc-700">
                <input type="checkbox" checked={contextWeighted} onChange={e=> setContextWeighted(e.target.checked)} />
                Context emphasis
              </label>
            </div>
            <div className="mb-1 flex items-center justify-between gap-3 text-[10px] text-zinc-500">
              <span>Bars use the backend step score so the graph matches peak selection.</span>
              <span>Peak outlines mark representative rows; red glow marks critical rows.</span>
            </div>
            <div
              className="relative h-32 overflow-x-auto border rounded mb-2 px-2 py-2"
              style={{
                backgroundImage:
                  'repeating-linear-gradient(to top, rgba(0,0,0,0.06) 0, rgba(0,0,0,0.06) 1px, transparent 1px, transparent 12px)'
              }}
            >
              <div className="flex items-end gap-1">
                {timeline.map((row,i)=> {
                  // Use original color mapping by tone (no gradient), keep new grid/ticks
                  const total = timelineStepScore(row);
                  const tone = morinStepTone(row);
                  const height = maxStepScore > 0 ? Math.max(6, Math.round((total / maxStepScore) * 80)) : 6;
                  const ratio = maxStepScore > 0 ? (total / maxStepScore) : 0;
                  const shade = Math.round(70 - 40*ratio); // 70% -> 30%
                  const isPeak = peakTimestampSet.has(row.timestamp);
                  const isActive = (activeStep?.timestamp || computeStep?.timestamp || null) === (row?.timestamp || null);
                  const hasCritical = rowHasCriticalSignals(row);
                  let color;
                  if (tone === 'negative') color = `hsl(0, 70%, ${shade}%)`;
                  else if (tone === 'positive') color = `hsl(140, 60%, ${shade}%)`;
                  else color = row.moon_support ? `hsl(210, 70%, ${shade}%)` : `hsl(0, 0%, ${shade}%)`;

                  const stride = Math.max(1, Math.round(1440 / (stepMinutes || 60)));
                  const isDayTick = (i % stride) === 0;
                  const inCtx = isTimestampInsideWindow(row.timestamp, contextWindow);
                  const criticalSummary = hasCritical ? collectCriticalSignalSummary(row, 2) : { chips: [] };
                  const criticalLabel = (criticalSummary.chips || []).map((chip) => chip.label).join(', ');
                  const barWidth = isActive ? 10 : (isPeak ? 8 : 6);
                  const contextOpacity = (contextWeighted && contextWindow) ? (inCtx ? 1 : 0.35) : 1;
                  const contextFilter = (contextWeighted && contextWindow && !inCtx) ? 'grayscale(60%)' : 'none';
                  const barTitle = [
                    formatTsCompact(row.timestamp, windowTz),
                    `${tone} tone`,
                    `backend score ${total.toFixed(1)}`,
                    `count ${row.count}`,
                    isPeak ? 'peak' : null,
                    hasCritical ? `critical${criticalLabel ? `: ${criticalLabel}` : ''}` : null,
                    contextWindow ? (inCtx ? 'inside context window' : 'outside context window') : null,
                  ].filter(Boolean).join(' • ');
                  const ariaLabel = [
                    'Timeline point',
                    formatTsCompact(row.timestamp, windowTz),
                    `score ${total.toFixed(1)}`,
                    `count ${row.count}`,
                    tone,
                    isPeak ? 'peak' : null,
                    hasCritical ? 'critical' : null,
                  ].filter(Boolean).join(' ');

                  return (
                    <React.Fragment key={row.timestamp || i}>
                      {isDayTick && (
                        <div className="relative" style={{ width: '2px', height: '100%' }}>
                          <div className="absolute inset-y-0 left-0 w-[2px] bg-zinc-300/70"></div>
                        </div>
                      )}
                      <div
                        className="cursor-pointer rounded-md ring-1 ring-white/30"
                        role="button"
                        tabIndex={0}
                        aria-label={ariaLabel}
                        aria-pressed={isActive}
                        data-peak={isPeak ? 'true' : 'false'}
                        data-critical={hasCritical ? 'true' : 'false'}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            onTimelineClick(row.timestamp);
                          }
                        }}
                        style={{
                          height: `${height}px`,
                          width: `${barWidth}px`,
                          backgroundColor: color,
                          border: isActive ? '2px solid rgba(15, 23, 42, 0.8)' : (isPeak ? '1px solid rgba(15, 23, 42, 0.45)' : '1px solid rgba(255,255,255,0.35)'),
                          boxShadow: (
                            hasCritical
                              ? `0 0 0 2px rgba(239, 68, 68, 0.35), ${row.moon_support ? '0 0 0 1px rgba(255,255,255,0.5) inset, 0 1px 2px rgba(0,0,0,0.2)' : '0 1px 2px rgba(0,0,0,0.2)'}`
                              : (row.moon_support ? '0 0 0 1px rgba(255,255,255,0.5) inset, 0 1px 2px rgba(0,0,0,0.2)' : '0 1px 2px rgba(0,0,0,0.2)')
                          ),
                          opacity: contextOpacity,
                          filter: contextFilter
                        }}
                        title={`${formatTsCompact(row.timestamp, windowTz)} • ${tone} tone • score ${total.toFixed(1)} • count ${row.count}`}
                        onClick={()=> onTimelineClick(row.timestamp)}
                      />
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
            {scanning && (
              <div className="mb-2">
                <div className="w-full h-2 bg-zinc-200 rounded overflow-hidden">
                  <div className="h-2 bg-sky-500" style={{ width: `${Math.round((scanProgress||0)*100)}%`, transition: 'width .2s ease' }} />
                </div>
                <div className="text-[10px] text-zinc-600 mt-1">Scanning… {Math.round((scanProgress||0)*100)}%</div>
              </div>
            )}
            {Array.isArray(peaks) && peaks.length > 0 && (
              <div className="text-xs text-zinc-700 mb-2">
                Top peaks:
                <span className="ml-2">
                    {peaks.slice(0,5).map((peak, idx)=> {
                      const ts = extractPeakIso(peak);
                      if (!ts) return null;
                      const key = ts || idx;
                      return (
                        <span key={key} className="mr-3 inline-flex items-center gap-2">
                          <button type="button" className="underline" onClick={()=> onTimelineClick(ts)}>{formatTsCompact(ts, windowTz)}</button>
                          {typeof onJumpToTime === 'function' && (
                            <button type="button" className="text-[10px] px-1 py-0.5 border rounded" onClick={()=> onJumpToTime(ts)} title="Use this time in the main Astro Clock">Use</button>
                          )}
                        </span>
                      );
                    })}
                </span>
              </div>
            )}
            {Array.isArray(series) && series.length > 0 && (
              <div className="mb-2 border rounded bg-rose-50/40 p-2 text-xs">
                <div className="text-[11px] uppercase tracking-wide text-rose-700 mb-1">Critical Signals In Scan</div>
                {scanCriticalGroups.length > 0 ? (
                  <div className="space-y-2">
                    {scanCriticalGroups.map((group) => (
                      <div key={group.key} className="rounded border border-rose-200 bg-white/80 p-3 md:p-4">
                        <div className="flex items-start justify-between gap-3 md:items-center">
                          <div className="min-w-0">
                            <div className="inline-flex items-center rounded-full border border-rose-300 bg-rose-50 px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] text-rose-700">
                              {group.label}
                            </div>
                          </div>
                          <div className="shrink-0 text-right">
                            <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">Top score</div>
                            <div className="text-base font-semibold text-zinc-900">{Number(group.topScore || 0).toFixed(1)}</div>
                          </div>
                        </div>
                        {group.description ? (
                          <div className="mt-2 text-[11px] leading-5 text-zinc-600">
                            {group.description}
                          </div>
                        ) : null}
                        <div className="mt-3 grid gap-1.5 sm:grid-cols-2 xl:grid-cols-4">
                          {group.rows.map((row) => (
                            <button
                              key={row.key}
                              type="button"
                              className="flex w-full items-center justify-between gap-3 rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-2 text-left transition hover:border-rose-300 hover:bg-rose-50/50"
                              onClick={() => row.timestamp && onTimelineClick(row.timestamp)}
                              disabled={!row.timestamp}
                            >
                              <span className="min-w-0 text-[11px] text-zinc-700">
                                {row.timestamp ? formatTsCompact(row.timestamp, windowTz) : 'Scan row'}
                              </span>
                              <span className="shrink-0 text-[11px] font-medium text-zinc-500">
                                {Number(row.score || 0).toFixed(1)}
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-[11px] text-zinc-600">
                    No critical signals found in the scanned rows. Try a smaller step or compute the exact source timestamp.
                  </div>
                )}
              </div>
            )}
            <div className="max-h-48 overflow-auto border rounded">
              <table className="w-full text-xs">
                <thead className="bg-zinc-50"><tr>
                  <th className="p-2 text-left">Time</th>
                  <th className="p-2 text-left">Top Hits</th>
                  <th className="p-2 text-left">Tags</th>
                  <th className="p-2 text-left">Predictions</th>
                  <th className="p-2 text-left">Tone</th>
                  <th className="p-2 text-right">Score</th>
                  <th className="p-2 text-right">Count</th>
                  <th className="p-2 text-center">☾</th>
                </tr></thead>
                <tbody>
                  {timeline.map((row,i)=> {
                    const stepScore = timelineStepScore(row);
                    const stepTone = morinStepTone(row);
                    const tagSummary = collectMorinTags(row, showTechTags);
                    const topHits = Array.isArray(row.top) ? row.top : [];
                    return (
                      <tr key={row.timestamp || i} className={i%2? 'bg-white':'bg-zinc-50/30'}>
                        <td className="p-2">{formatTsCompact(row.timestamp, windowTz)}</td>
                        <td className="p-2">
                          {topHits.map((h, j)=> {
                            const T = PlanetSymbols[h.transiting] || h.transiting;
                            const R = renderTargetLabel(h, true);
                            const hitTone = morinHitTone(h);
                            const toneCls = hitTone === 'positive'
                              ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                              : hitTone === 'negative'
                                ? 'border-rose-300 bg-rose-50 text-rose-700'
                                : 'border-zinc-200 bg-white text-zinc-700';
                            const hitScore = morinHitScore(h);
                            const sign = hitTone === 'positive' ? '+' : (hitTone === 'negative' ? '−' : '');
                            const orbTxt = `${degText(h.orb)}${sign}`;
                            const tagLabels = Array.isArray(h.prediction_tags)
                              ? h.prediction_tags.map((t) => {
                                  const fmt = formatMorinTagLabel(t);
                                  return fmt ? fmt.label : null;
                                }).filter(Boolean)
                              : [];
                            const laws = appliedLawsForHit(h);
                            const lawSummary = laws.map((law) => `L${law.lawNumber}`).join(', ');
                            const tipParts = [
                              (h.prediction && h.prediction.description) ? String(h.prediction.description) : `${h.transiting} ${h.aspect} ${h.target_label||h.natal}`,
                              `Score: ${hitScore.toFixed(1)}`,
                              tagLabels.length ? `Tags: ${tagLabels.join(', ')}` : null,
                              laws.length ? `Laws: ${lawSummary}` : null,
                              ccTip(h),
                            ].filter(Boolean);
                            const tip = tipParts.join('\n');
                            return (
                              <div key={j} className="flex items-center flex-wrap gap-1 mr-2 mb-0.5">
                                <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 border rounded-full ${toneCls}`} title={tip}>
                                  <span className={planetColor(h.transiting)} title={h.transiting}>{T}</span>
                                  <span>{aspectSymbol(h.aspect)}</span>
                                  <span className={targetColor(h)}>{R}</span>
                                  <span className="opacity-80">{orbTxt}</span>
                                  <span className="text-[10px] font-semibold">{hitScore.toFixed(1)}</span>
                                </span>
                                {laws.length > 0 && (
                                  <span className="inline-flex items-center flex-wrap gap-1">
                                    {laws.slice(0,3).map((law, idx) => (
                                      <span
                                        key={`${j}-law-${idx}`}
                                        className={`inline-flex items-center px-1 py-0.5 border rounded text-[9px] ${lawToneClass(law?.strengthModifier)}`}
                                        title={`${law?.lawName || `Law ${law?.lawNumber ?? ''}`}\nEffect: ${(Number(law?.strengthModifier)||0).toFixed(2)}`}
                                      >
                                        L{law?.lawNumber ?? '?'}
                                      </span>
                                    ))}
                                    {laws.length > 3 && (
                                      <span className="inline-flex items-center px-1 py-0.5 border rounded text-[9px] bg-zinc-50 border-zinc-300 text-zinc-600">
                                        +{laws.length - 3}
                                      </span>
                                    )}
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </td>
                        <td className="p-2">
                          {tagSummary.map((tag, idx) => {
                            const tagToneCls = tag.orientation === 'positive'
                              ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                              : tag.orientation === 'negative'
                                ? 'border-rose-300 bg-rose-50 text-rose-700'
                                : 'border-zinc-300 bg-zinc-50 text-zinc-700';
                            const weightTxt = Number(tag.weight || 0) > 0 ? `Weight: ${Number(tag.weight).toFixed(1)}` : null;
                            const tip = [`Morin tag: ${tag.label}`, weightTxt].filter(Boolean).join(' • ');
                            return (
                              <span key={tag.key || idx} className={`inline-block mr-1 mb-0.5 px-1 py-0.5 border rounded text-[10px] ${tagToneCls}`} title={tip}>
                                {tag.label}
                              </span>
                            );
                          })}
                          {/* Step-level domain summary chips */}
                          {Array.isArray(row.domain_summary) && row.domain_summary.length>0 && (
                            <div className="mt-1 text-[10px] text-zinc-600">
                              <span className="mr-1">Top domains:</span>
                              {row.domain_summary.map((ds, idx)=> {
                                const cls = ds.tone==='positive' ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                                  : ds.tone==='negative' ? 'border-rose-300 bg-rose-50 text-rose-700'
                                  : 'border-zinc-300 bg-zinc-50 text-zinc-700';
                                return (
                                  <span key={idx} className={`inline-block mr-1 mb-0.5 px-1 py-0.5 border rounded ${cls}`}>{ds.domain}</span>
                                );
                              })}
                            </div>
                          )}
                        </td>
                        <td className="p-2">
                          {(() => {
                            const { items, criticalChips } = collectRowPredictionSummary(row, topHits);
                            return (
                              <>
                                {items.map((item) => (
                                  <span key={item.key} className="inline-block mr-1 mb-0.5 px-1 py-0.5 border rounded text-[10px] bg-zinc-50 border-zinc-300 text-zinc-700">
                                    {item.label}
                                  </span>
                                ))}
                                {criticalChips.length > 0 && (
                                  <div className="mt-1">
                                    {criticalChips.map((chip) => (
                                      <span key={chip.key} className="inline-block mr-1 mb-0.5 px-1 py-0.5 border rounded text-[10px] border-rose-300 bg-rose-50 text-rose-700">
                                        {chip.label}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </>
                            );
                          })()}
                        </td>
                      <td className="p-2">
                        {stepTone === 'positive' && <span className="px-1.5 py-0.5 rounded border border-emerald-300 bg-emerald-50 text-emerald-700">Positive</span>}
                        {stepTone === 'negative' && <span className="px-1.5 py-0.5 rounded border border-rose-300 bg-rose-50 text-rose-700">Negative</span>}
                        {(stepTone !== 'positive' && stepTone !== 'negative') && (
                          <span className="px-1.5 py-0.5 rounded border border-zinc-300 bg-zinc-50 text-zinc-700">Mixed</span>
                        )}
                      </td>
                      <td className="p-2 text-right">{stepScore.toFixed(1)}</td>
                      <td className="p-2 text-right">{row.count}</td>
                      <td className="p-2 text-center">{row.moon_support ? '☾' : ''}</td>
                    </tr>
                  );
                })}
                </tbody>
              </table>
            </div>
            </>
          ) : !hasExactVisibleResult ? (
            <p className="text-xs text-zinc-600">No transits found for this timestamp.</p>
          ) : null}

          {predictionCard && (
            <div className="mt-3 border rounded p-3 text-xs">
              <div className="font-semibold mb-1">Prediction Card (beta)</div>
              <div>Window: {formatTsCompact(predictionCard.window?.start, windowTz)} → {formatTsCompact(predictionCard.window?.end, windowTz)}</div>
              {predictionCard.peaks?.length ? (
                <div className="mt-1">Peak dates:
                  <ul className="list-disc ml-5">
                    {predictionCard.peaks.map((ts,i)=> (
                      <li key={i}>{formatTs(ts, windowTz)}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {Array.isArray(predictionCard.why) && predictionCard.why.length>0 && (
                <div className="mt-1">Why:
                  <ul className="list-disc ml-5">
                    {predictionCard.why.map((item,i)=> (
                      <li key={i}>
                        {formatTs(item.timestamp, windowTz)}: {(item.top||[]).map((h,j)=> (
                          <span key={j} className="inline-block mr-2" title={`${h.transiting} ${h.aspect} ${(h.target_label||h.natal)}`}>
                            {(PlanetSymbols[h.transiting] || h.transiting)} {aspectSymbol(h.aspect)} {renderTargetLabel(h, true)}
                          </span>
                        ))}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {computeStep && (
          <div className="mb-3 border rounded-lg p-3 bg-white/80 text-xs">
            <div className="flex items-center justify-between mb-2">
              <div className="font-semibold text-sm">
                {computeTimestamp ? formatTsCompact(computeTimestamp, windowTz || natalTz) : '—'}
              </div>
              <div className="flex items-center gap-2 text-[11px] text-zinc-600">
                {computeStepTone === 'positive' && (
                  <span className="px-1.5 py-0.5 rounded border border-emerald-300 bg-emerald-50 text-emerald-700">Positive</span>
                )}
                {computeStepTone === 'negative' && (
                  <span className="px-1.5 py-0.5 rounded border border-rose-300 bg-rose-50 text-rose-700">Negative</span>
                )}
                {(computeStepTone !== 'positive' && computeStepTone !== 'negative') && (
                  <span className="px-1.5 py-0.5 rounded border border-zinc-300 bg-zinc-50 text-zinc-700">Mixed</span>
                )}
                <span title="Scan-style selected top-hit score">Score {computeStepScore.toFixed(1)}</span>
                <span>Hits {computeCount}</span>
                {computeStep?.moon_support ? <span title="Moon support">☾</span> : null}
              </div>
            </div>
            <div className="mb-2">
              <div className="text-[11px] uppercase tracking-wide text-zinc-500 mb-1">Critical Signals</div>
              {computeCriticalSignals.chips.length > 0 ? (
                <>
                  <div className="flex flex-wrap gap-1">
                    {computeCriticalSignals.chips.map((item) => (
                      <span key={item.key} className="inline-block px-1.5 py-0.5 border rounded text-[10px] border-rose-300 bg-rose-50 text-rose-700">
                        {item.label}
                      </span>
                    ))}
                  </div>
                  {computeCriticalSignals.descriptions.length > 0 && (
                    <div className="mt-1 text-[11px] text-zinc-600">
                      Top critical transit: {computeCriticalSignals.descriptions.join(' • ')}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-[11px] text-zinc-600">
                  No critical signals at this timestamp.
                  {scanCriticalRows.length > 0 ? ' Check the scan summary above for nearby crisis rows.' : ''}
                  {!scanCriticalRows.length && hasCoarseScanStep ? ' Daily or coarse scan steps can hide event-specific crisis rows.' : ''}
                </div>
              )}
            </div>
            <div className="flex flex-wrap gap-1">
              {computeTags.length ? (
                computeTags.map((tag, idx) => {
                  const toneCls = tag.orientation === 'positive'
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                    : tag.orientation === 'negative'
                      ? 'border-rose-300 bg-rose-50 text-rose-700'
                      : 'border-zinc-300 bg-zinc-50 text-zinc-700';
                  const weightTxt = Number(tag.weight || 0) > 0 ? `Weight: ${Number(tag.weight).toFixed(1)}` : null;
                  const tip = [`Morin tag: ${tag.label}`, weightTxt].filter(Boolean).join(' • ');
                  return (
                    <span key={tag.key || idx} className={`inline-block px-1 py-0.5 border rounded text-[10px] ${toneCls}`} title={tip}>
                      {tag.label}
                    </span>
                  );
                })
              ) : (
                <span className="text-zinc-500">No step tags</span>
              )}
            </div>
          </div>
        )}

        {transits.length > 0 ? (
          <>
            {/* Display toggles */}
            <div className="flex items-center gap-4 mb-2 text-[11px] text-zinc-700">
              <label className="inline-flex items-center gap-1">
                <input type="checkbox" checked={showTechTags} onChange={(e)=> setShowTechTags(e.target.checked)} />
                Show technical tags
              </label>
              <label className="inline-flex items-center gap-1">
                <input type="checkbox" checked={showEnriched} onChange={(e)=> setShowEnriched(e.target.checked)} />
                Show enriched tokens
              </label>
            </div>
            <div className="max-h-80 overflow-auto border rounded-lg">
              <table className="w-full text-sm">
              <thead className="bg-zinc-50">
                <tr>
                  <th className="text-left p-2">Transiting</th>
                  <th className="text-left p-2">Target</th>
                  <th className="text-left p-2">Aspect</th>
                  <th className="text-right p-2">Orb</th>
                  <th className="text-left p-2">Phase</th>
                  <th className="text-left p-2">Dir.</th>
                  <th className="text-left p-2">Timing</th>
                  <th className="text-left p-2">Area</th>
                  <th className="text-left p-2">Event</th>
                  <th className="text-left p-2">Laws</th>
                  <th className="text-left p-2">Keywords</th>
                </tr>
              </thead>
              <tbody>
                {transits.map((row, i)=> (
                  <tr key={`${row.transiting||'T'}-${row.aspect||'A'}-${row.natal||row.target_label||'N'}-${i}`} className={i%2? 'bg-white' : 'bg-zinc-50/30'}>
                    <td className={`p-2 ${planetColor(row.transiting)}`} title={`${(row.prediction && row.prediction.description) ? String(row.prediction.description) : row.transiting}\n${ccTip(row)}`}>{PlanetSymbols[row.transiting] || row.transiting}</td>
                    <td className="p-2">
                      <span className={targetColor(row)}>{renderTargetLabel(row)}</span>
                    </td>
                    <td className="p-2">{aspectSymbol(row.aspect)} {row.aspect}</td>
                    <td className="p-2 text-right">{degText(row.orb)}</td>
                    <td className="p-2">{row.phase}</td>
                    <td className="p-2">{row.direction}</td>
                    <td className="p-2 text-xs text-zinc-600">
                      {formatTimingWindow(row.effectiveWindow || row.effective_window, windowTz || natalTz)}
                    </td>
                    <td className="p-2">{(row.prediction && row.prediction.lifeArea) ? formatTokenLabel(row.prediction.lifeArea) : ''}</td>
                    <td className="p-2">
                      {(() => {
                        const allowed = CanonicalLabels;
                        const enrich = Array.isArray(row.enriched_keywords) ? row.enriched_keywords.map(String) : [];
                        const kwRaw = Array.isArray(row.keywords) ? row.keywords.map(String) : [];
                        const orderedTokens = [];
                        const tokenSet = new Set();
                        const explicitTokens = new Set();

                        const pushToken = (raw, explicit = false) => {
                          if (!raw) return;
                          const lower = String(raw).toLowerCase();
                          let token = null;
                          if (allowed[lower]) token = lower;
                          else if (LABEL_TO_EVENT_TOKEN[lower]) token = LABEL_TO_EVENT_TOKEN[lower];
                          if (!token && lower.includes(' ')) {
                            const underscored = lower.replace(/\s+/g, '_');
                            if (allowed[underscored]) token = underscored;
                          }
                          if (token && !tokenSet.has(token)) {
                            tokenSet.add(token);
                            orderedTokens.push(token);
                          }
                          if (token && explicit) {
                            explicitTokens.add(token);
                          }
                        };

                        enrich.forEach((tok) => pushToken(tok, true));
                        kwRaw.forEach((tok) => {
                          pushToken(tok);
                          pushToken(String(tok).replace(/\s+/g, '_'));
                        });

                        // Pick primary event: prediction.eventType, or first present in EVENT_PRIORITY, else first token
                        let evRaw = pickPrimaryEventToken(
                          (row.prediction && row.prediction.eventType) ? String(row.prediction.eventType) : '',
                          (row.prediction && row.prediction.lifeArea) ? String(row.prediction.lifeArea) : '',
                          tokenSet,
                          orderedTokens,
                          explicitTokens,
                        );
                        const evLabel = evRaw ? (allowed[evRaw] || evRaw.replace(/_/g,' ')) : '';
                        // Build curated secondary chips by eventType
                        const cur = EventChipCurations[evRaw] || null;
                        let keys = orderedTokens.filter((tok) => tok !== evRaw);
                        // apply curation if configured for this eventType
                        if (cur) {
                          if (Array.isArray(cur.exclude) && cur.exclude.length) {
                            keys = keys.filter(k => !cur.exclude.includes(k));
                          }
                          if (Array.isArray(cur.include) && cur.include.length) {
                            const have = new Set(keys);
                            keys = cur.include.filter(k => have.has(k));
                          }
                        }
                        // map to labels and cap with summarizer
                        const labels = keys.map(k => allowed[k]).filter(Boolean);
                        const cap = cur && cur.max ? Number(cur.max) : 3;
                        const shown = labels.slice(0, cap);
                        const remaining = labels.slice(cap);
                        const summary = remaining.length ? `+${remaining.length}` : null;
                        const summaryTip = remaining.length ? remaining.join(', ') : '';
                        return (
                          <>
                            <span className="font-semibold">{evLabel}</span>
                            {shown.map((t, i) => (
                              <span key={i} className="inline-block ml-1 px-1 py-0.5 border rounded text-[10px] bg-zinc-50 border-zinc-300 text-zinc-700 whitespace-nowrap">{t}</span>
                            ))}
                            {summary && (
                              <span className="inline-block ml-1 px-1 py-0.5 border rounded text-[10px] bg-zinc-50 border-zinc-300 text-zinc-700 whitespace-nowrap" title={summaryTip}>{summary}</span>
                            )}
                          </>
                        );
                      })()}
                    </td>
                    <td className="p-2 text-xs text-zinc-600">
                      {(() => {
                        const applied = (Array.isArray(row.laws_applied) ? row.laws_applied : []).filter(l => l && l.applies === true);
                        if (!applied.length) return null;
                        const tip = applied.map((law) => {
                          const ln = law.lawNumber != null ? `Law ${law.lawNumber}` : 'Law';
                          const name = law.lawName ? `: ${law.lawName}` : '';
                          const mod = law.strengthModifier != null ? ` (Δ ${Number(law.strengthModifier).toFixed(2)})` : '';
                          return `${ln}${name}${mod}`;
                        }).join('\n');
                        return (
                          <span
                            title={tip}
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 border rounded border-indigo-300 bg-indigo-50 text-indigo-700 text-[11px]"
                          >
                            {applied.length}
                          </span>
                        );
                      })()}
                    </td>
                    <td className="p-2 text-xs text-zinc-600">
                      {(() => {
                        const base = Array.isArray(row.keywords) ? [...row.keywords] : [];
                        const enriched = Array.isArray(row.enriched_keywords) ? [...row.enriched_keywords] : [];
                        const techTags = Array.isArray(row.tech_tags) ? [...row.tech_tags] : [];
                        // Area shown in Area column; suppress duplicate domain chip
                        const areaRaw = (row.prediction && row.prediction.lifeArea) ? String(row.prediction.lifeArea) : '';
                        const area = areaRaw.toLowerCase().replace(/_/g,' ');
                        const evRaw = (row.prediction && row.prediction.eventType) ? String(row.prediction.eventType) : '';
                        const impliedSet = new Set(ImpliedQualifiersByEvent[evRaw] || []);
                        const DOMAIN_KEYS = ['marriage','home','career','money','wealth','health','service','secrets','hidden_enemies','short_journeys','siblings','relatives','friends','hopes','children','life','belief','shared_resources','parents'];
                        // Canonical-friendly mapping for keywords
                        const friendly = (tok) => {
                          const key = String(tok);
                          if (CanonicalLabels[key]) return CanonicalLabels[key];
                          if (key === 'parties_celebrations') return 'celebration';
                          if (key === 'public_recognition') return 'public recognition';
                          if (key === 'Platic') return 'wide';
                          if (key === 'Partile') return 'partile';
                          return key;
                        };
                        // Hide aspect-type tokens from display
                        const ASPECT_TOKENS = new Set([
                          'Conj','Opp','Sq','Tri','Sex','Semi','Qnx',
                          'Conjunction','Opposition','Square','Trine','Sextile','Quincunx','Semi-sextile'
                        ].map(String));
                        // Split into groups
                        const raw = (showEnriched ? [...base, ...enriched] : base.filter(t => !enriched.includes(String(t))))
                          .filter(t => !ASPECT_TOKENS.has(String(t)));
                        const lowerSet = new Set(raw.map(s => String(s).toLowerCase()));
                        const domains = DOMAIN_KEYS.filter(d => lowerSet.has(d) && d !== area);
                        const qualifiers = [];
                        if (lowerSet.has('parties_celebrations') && !impliedSet.has('parties_celebrations')) qualifiers.push('parties_celebrations');
                        if (lowerSet.has('public_recognition') && !impliedSet.has('public_recognition')) qualifiers.push('public_recognition');
                        if (lowerSet.has('natal echo') || lowerSet.has('natal echo'.toLowerCase())) qualifiers.push('natal echo');
                        // Technical: show only when toggled
                        const TECH_HIDE = new Set(['dexter','sinister','benefic','malefic','soft','hard','exact','applying','separating','rx','antiscia','contra-antiscia','platic','partile']);
                        let technical = techTags.slice();
                        // Also include non-tag technical tokens in base if present (Dexter, Sinister, etc.)
                        for (const t of raw) {
                          const s = String(t);
                          const ls = s.toLowerCase();
                          if (TECH_HIDE.has(ls)) technical.push(s);
                          if (/^C\d+\s+(Conj|Opp|Sq|Tri|Sex|Semi|Qnx)\s+/.test(s)) technical.push(s);
                        }
                        // Build display order: domains → qualifiers → technical (if enabled)
                        const chips = [];
                        for (const d of domains) chips.push({ label: friendly(d), cls: 'border-zinc-300 bg-zinc-50 text-zinc-800' });
                        for (const q of qualifiers) chips.push({ label: friendly(q), cls: 'border-zinc-300 bg-zinc-50 text-zinc-800' });
                        if (showTechTags) {
                          // Map platic/partile names for non-experts
                          technical = Array.from(new Set(technical));
                          for (const t of technical) {
                            const disp = friendly(t);
                            chips.push({ label: disp, cls: 'border-zinc-200 bg-white text-zinc-600' });
                          }
                        }
                        return chips.map((c,i)=> (
                          <span key={i} className={`inline-block mr-1 mb-0.5 px-1 py-0.5 border rounded whitespace-nowrap ${c.cls}`}>{c.label}</span>
                        ));
                      })()}
                    </td>
                </tr>
                ))}
              </tbody>
            </table>
          </div>
          </>
        ) : (
          <p className="text-sm text-zinc-600">No single-time transits yet. Enter natal data and compute.</p>
        )}

        {/* End saved snap/manual sections */}
        </div>
      </div>
    </div>
  );
}
