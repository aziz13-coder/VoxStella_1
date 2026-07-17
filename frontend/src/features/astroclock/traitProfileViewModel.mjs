const SOURCE_LABELS = {
  morin: 'Morin',
  classical: 'Classical',
  modern: 'Modern',
  textbook: 'Textbook',
  carter: 'Carter-derived',
  editorial: 'Editorial',
};

export const POLARITY_META = {
  positive: {
    key: 'positive',
    shortKey: 'pos',
    label: 'Constructive',
    splitLabel: 'Top Constructive',
    columnLabel: 'What strengthens',
    tone: 'positive',
  },
  neutral: {
    key: 'neutral',
    shortKey: 'neu',
    label: 'Style',
    splitLabel: 'Top Style',
    columnLabel: 'What flavours behaviour',
    tone: 'neutral',
  },
  negative: {
    key: 'negative',
    shortKey: 'neg',
    label: 'Strain',
    splitLabel: 'Top Strain',
    columnLabel: 'What creates strain',
    tone: 'negative',
  },
};

export function normalizeLineage(value) {
  return String(value || '').trim().toLowerCase();
}

export function citationLineageLabel(value) {
  const key = normalizeLineage(value);
  return SOURCE_LABELS[key] || (key ? key[0].toUpperCase() + key.slice(1) : 'Source');
}

export function normalizePolarity(value) {
  const key = String(value || '').trim().toLowerCase();
  if (key === 'pos' || key === 'constructive') return 'positive';
  if (key === 'neu' || key === 'style') return 'neutral';
  if (key === 'neg' || key === 'strain') return 'negative';
  if (key === 'positive' || key === 'neutral' || key === 'negative') return key;
  return '';
}

export function polarityLabel(value) {
  const key = normalizePolarity(value);
  return POLARITY_META[key]?.label || 'Trait';
}

export function normalizeScore(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, n));
}

function traitName(trait) {
  return String(trait?.name || trait?.id || '').trim();
}

function sourcePriority(trait) {
  const lineage = normalizeLineage(trait?.source_lineage);
  return ({ morin: 5, classical: 4, carter: 3, modern: 2, editorial: 1, provisional: 0 })[lineage] ?? 1;
}

function scoreTier(trait) {
  const score = normalizeScore(trait?.score);
  return Math.floor(score / 5);
}

function isProvisional(trait) {
  return !!trait?.provisional || normalizeLineage(trait?.source_status) === 'provisional';
}

export function traitSourceLabel(trait) {
  if (trait?.source_lineage_label) return String(trait.source_lineage_label);
  if (trait?.source_lineage) return citationLineageLabel(trait.source_lineage);
  if (Array.isArray(trait?.sources) && trait.sources.length) return String(trait.sources[0]);
  return isProvisional(trait) ? 'Provisional source' : 'Source';
}

export function traitMatchesSourceFilter(trait, sourceFilter) {
  const filter = normalizeLineage(sourceFilter);
  if (!filter || filter === 'all') return true;
  const lineage = normalizeLineage(trait?.source_lineage);
  const layers = (trait?.keyword_layers && typeof trait.keyword_layers === 'object') ? trait.keyword_layers : {};
  const citations = Array.isArray(trait?.citations) ? trait.citations : [];
  const hasLayer = (key) => Array.isArray(layers?.[key]) && layers[key].length > 0;
  const hasCitationLineage = (...keys) => citations.some((cit) => keys.includes(normalizeLineage(cit?.source_lineage)));
  if (filter === 'morin') return lineage === 'morin' || hasLayer('morin');
  if (filter === 'classical') return lineage === 'classical' || hasLayer('classical') || hasLayer('textbook') || hasCitationLineage('classical', 'textbook');
  if (filter === 'modern') return lineage === 'modern' || hasLayer('modern') || hasCitationLineage('modern');
  if (filter === 'carter') return lineage === 'carter';
  return true;
}

function compareTraits(sortBy = 'score') {
  const cmpName = (a, b) => traitName(a).localeCompare(traitName(b));
  const polRank = (p) => ({ positive: 0, neutral: 1, negative: 2 })[normalizePolarity(p)] ?? 3;
  return (a, b) => {
    if (sortBy === 'name') return cmpName(a, b);
    if (sortBy === 'polarity') return polRank(a?.polarity) - polRank(b?.polarity) || cmpName(a, b);
    if (sortBy === 'supports') {
      const sa = Number(a?.support_hits || 0);
      const sb = Number(b?.support_hits || 0);
      if (sb !== sa) return sb - sa;
    }
    const scoreDiff = normalizeScore(b?.score) - normalizeScore(a?.score);
    return scoreDiff || cmpName(a, b);
  };
}

function compareSummaryTraits(a, b) {
  const pa = Number(a?.summary_priority || 0);
  const pb = Number(b?.summary_priority || 0);
  if (pb !== pa) return pb - pa;
  const ta = scoreTier(a);
  const tb = scoreTier(b);
  if (tb !== ta) return tb - ta;
  const la = sourcePriority(a);
  const lb = sourcePriority(b);
  if (lb !== la) return lb - la;
  const scoreDiff = normalizeScore(b?.score) - normalizeScore(a?.score);
  return scoreDiff || traitName(a).localeCompare(traitName(b));
}

export function representativeTraits(data) {
  const all = Array.isArray(data?.traits) ? data.traits : [];
  const reps = all.filter((trait) => trait?.family_representative !== false);
  return reps.length ? reps : all;
}

export function summaryTraits(data) {
  const backendSummary = (Array.isArray(data?.summary_traits) ? data.summary_traits : [])
    .filter((trait) => trait?.summary_eligible !== false);
  const reps = representativeTraits(data).filter((trait) => trait?.summary_eligible !== false);
  const base = backendSummary.length ? backendSummary : (reps.length ? reps : representativeTraits(data));
  const curated = base.filter((trait) => !isProvisional(trait));
  return (curated.length ? curated : base).slice().sort(compareSummaryTraits);
}

export function filterAndSortTraits(traits, filters = {}) {
  let list = Array.isArray(traits) ? traits.slice() : [];
  const band = normalizeLineage(filters.band);
  const polarity = normalizePolarity(filters.polarity);
  const sourceFilter = normalizeLineage(filters.sourceFilter || filters.source);
  const selectedDomains = Array.isArray(filters.selectedDomains) ? filters.selectedDomains.map(String) : [];

  if (band && band !== 'all') list = list.filter((trait) => normalizeLineage(trait?.band) === band);
  if (polarity && polarity !== 'all') list = list.filter((trait) => normalizePolarity(trait?.polarity) === polarity);
  if (sourceFilter && sourceFilter !== 'all') list = list.filter((trait) => traitMatchesSourceFilter(trait, sourceFilter));
  if (selectedDomains.length) list = list.filter((trait) => !trait?.domain || selectedDomains.includes(String(trait.domain)));
  return list.sort(compareTraits(filters.sortBy || filters.sort || 'score'));
}

export function buildDomainIndex(traits, filters = {}) {
  const allTraits = Array.isArray(traits) ? traits : [];
  const selectedDomains = Array.isArray(filters.selectedDomains) ? filters.selectedDomains.map(String) : [];
  const q = String(filters.domainSearch || '').trim().toLowerCase();
  const counts = new Map();
  for (const trait of allTraits) {
    const domain = trait?.domain ? String(trait.domain) : null;
    if (!domain) continue;
    counts.set(domain, (counts.get(domain) || 0) + 1);
  }
  const allDomains = Array.from(counts.keys()).sort();
  const effectiveSelected = selectedDomains.length ? selectedDomains : allDomains;
  const visibleDomains = q ? allDomains.filter((domain) => domain.toLowerCase().includes(q)) : allDomains;
  return {
    allDomains,
    visibleDomains,
    selectedDomains: effectiveSelected,
    selectedCount: effectiveSelected.length,
    totalCount: allDomains.length,
    traitCount: allTraits.length,
    counts: Object.fromEntries(Array.from(counts.entries()).sort(([a], [b]) => a.localeCompare(b))),
  };
}

export function buildHouseDeterminationChannels(house) {
  const list = Array.isArray(house?.influences) ? house.influences : [];
  let presenceValue = 0;
  let governanceValue = 0;
  let aspectValue = 0;
  for (const item of list) {
    const value = Math.abs(Number(item?.value || 0));
    if (!Number.isFinite(value) || value <= 0) continue;
    if (item?.type === 'occupation') presenceValue += value;
    else if (item?.type === 'rulership' || item?.type === 'co_rulership') governanceValue += value;
    else if (item?.type === 'aspect') aspectValue += value;
  }
  const total = presenceValue + governanceValue + aspectValue;
  const share = (value) => (total > 0 ? value / total : 0);
  return {
    presence: share(presenceValue),
    governance: share(governanceValue),
    aspect: share(aspectValue),
    presenceValue: Number(presenceValue.toFixed(2)),
    governanceValue: Number(governanceValue.toFixed(2)),
    aspectValue: Number(aspectValue.toFixed(2)),
    total: Number(total.toFixed(2)),
  };
}

export function buildTopByPolarity(data, filters = {}) {
  const backend = (data?.top_traits_by_polarity && typeof data.top_traits_by_polarity === 'object')
    ? data.top_traits_by_polarity
    : {};
  const fallback = summaryTraits(data);
  const top = filters.topCount === 'all' ? Number.POSITIVE_INFINITY : Math.max(1, Number(filters.topCount) || 6);
  const commonFilters = {
    band: filters.band,
    sourceFilter: filters.sourceFilter || filters.source,
    selectedDomains: filters.selectedDomains,
    sortBy: 'summary',
  };
  const applyCommon = (items) => {
    let list = Array.isArray(items) ? items.slice() : [];
    const band = normalizeLineage(commonFilters.band);
    const sourceFilter = normalizeLineage(commonFilters.sourceFilter);
    const selectedDomains = Array.isArray(commonFilters.selectedDomains) ? commonFilters.selectedDomains.map(String) : [];
    if (band && band !== 'all') list = list.filter((trait) => normalizeLineage(trait?.band) === band);
    if (sourceFilter && sourceFilter !== 'all') list = list.filter((trait) => traitMatchesSourceFilter(trait, sourceFilter));
    if (selectedDomains.length) list = list.filter((trait) => !trait?.domain || selectedDomains.includes(String(trait.domain)));
    const curated = list.filter((trait) => !isProvisional(trait));
    return (curated.length ? curated : list).slice().sort(compareSummaryTraits).slice(0, top);
  };
  const fromBackendOrFallback = (key) => {
    const backendList = Array.isArray(backend?.[key]) && backend[key].length ? backend[key] : null;
    return backendList || fallback.filter((trait) => normalizePolarity(trait?.polarity) === key);
  };
  return {
    positive: applyCommon(fromBackendOrFallback('positive')),
    neutral: applyCommon(fromBackendOrFallback('neutral')),
    negative: applyCommon(fromBackendOrFallback('negative')),
  };
}

export function weightedAverageScore(traits) {
  const list = (Array.isArray(traits) ? traits : []).filter(Boolean);
  if (!list.length) return null;
  let total = 0;
  let weightTotal = 0;
  for (const trait of list) {
    const weight = Math.max(1, Number(trait?.support_hits || trait?.supports?.active || 0));
    total += normalizeScore(trait?.score) * weight;
    weightTotal += weight;
  }
  if (!weightTotal) return null;
  return Math.round(total / weightTotal);
}

export function buildPolaritySignals(topByPolarity) {
  const source = topByPolarity || {};
  const constructive = weightedAverageScore(source.positive);
  const style = weightedAverageScore(source.neutral);
  const strain = weightedAverageScore(source.negative);
  const profileBalanceIndex = constructive == null || strain == null
    ? null
    : Math.max(0, Math.min(100, Math.round(50 + ((constructive - strain) / 2))));
  return {
    constructive: {
      key: 'constructive',
      polarity: 'positive',
      label: 'Constructive',
      value: constructive,
      count: Array.isArray(source.positive) ? source.positive.length : 0,
      traits: Array.isArray(source.positive) ? source.positive : [],
    },
    style: {
      key: 'style',
      polarity: 'neutral',
      label: 'Style',
      value: style,
      count: Array.isArray(source.neutral) ? source.neutral.length : 0,
      traits: Array.isArray(source.neutral) ? source.neutral : [],
    },
    strain: {
      key: 'strain',
      polarity: 'negative',
      label: 'Strain',
      value: strain,
      count: Array.isArray(source.negative) ? source.negative.length : 0,
      traits: Array.isArray(source.negative) ? source.negative : [],
    },
    profileBalanceIndex,
  };
}

export function sectLabel(sect) {
  if (!sect) return null;
  if (typeof sect === 'string') return sect;
  const raw = sect.label || sect.chart_sect || sect.sect || sect.type || sect.light || sect.status;
  if (!raw) return null;
  const normalized = String(raw).trim().toLowerCase();
  if (normalized === 'diurnal' || normalized === 'day') return 'Day';
  if (normalized === 'nocturnal' || normalized === 'night') return 'Night';
  return String(raw);
}

export function buildChartSummary(data, opts = {}) {
  const summary = data?.summary || {};
  const snapshot = data?.chart_snapshot || opts.chartSnapshot || {};
  const houseRulers = snapshot?.house_rulers && typeof snapshot.house_rulers === 'object' ? snapshot.house_rulers : {};
  const mode = opts.mode || opts.chartContext?.mode || null;
  return {
    modeLabel: mode === 'manual' ? 'manual' : 'live',
    timestamp: snapshot?.timestamp || opts.chartContext?.datetime || null,
    location: snapshot?.location || opts.chartContext?.location || null,
    timezoneLabel: snapshot?.timezone_label || snapshot?.timezone || opts.chartContext?.timezone || null,
    houseSystem: snapshot?.house_system || opts.chartContext?.houseSystem || opts.houseSystem || null,
    dominantElement: summary?.dominant_element || null,
    dominantModality: summary?.dominant_modality || null,
    sect: sectLabel(data?.sect),
    chartRuler: houseRulers['1'] || houseRulers[1] || null,
    ascendant: snapshot?.ascendant ?? null,
    midheaven: snapshot?.midheaven ?? null,
  };
}

export function buildProfileSignature(data, topByPolarity, chartSummary = {}) {
  const summary = chartSummary || buildChartSummary(data);
  const pos = Array.isArray(topByPolarity?.positive) ? topByPolarity.positive[0] : null;
  const neg = Array.isArray(topByPolarity?.negative) ? topByPolarity.negative[0] : null;
  const neutral = Array.isArray(topByPolarity?.neutral) ? topByPolarity.neutral[0] : null;
  const lead = pos || neutral || neg;
  const frame = [summary.dominantModality, summary.dominantElement].filter(Boolean).join(' ');
  if (frame && lead && neg && pos) {
    return {
      line: `${frame} profile led by ${traitName(pos)}; ${traitName(neg)} is the main strain.`,
      note: `Derived from the strongest constructive and strain traits indicated in this chart.`,
    };
  }
  if (frame && lead) {
    return {
      line: `${frame} profile with ${traitName(lead)} leading.`,
      note: `Derived from the dominant element/modality and the strongest indicated trait.`,
    };
  }
  if (lead) {
    return {
      line: `${traitName(lead)} is the leading indicated trait.`,
      note: `Derived from the highest ranked trait in the current profile.`,
    };
  }
  return {
    line: 'Trait profile is ready.',
    note: 'No scored trait cluster is strong enough for a fuller signature.',
  };
}

export function buildTraitProfileViewModel(data, opts = {}) {
  const filters = opts.filters || {};
  const allTraits = Array.isArray(data?.traits) ? data.traits : [];
  const filteredTraits = filterAndSortTraits(allTraits, filters);
  const topByPolarity = buildTopByPolarity(data, filters);
  const signals = buildPolaritySignals(topByPolarity);
  const chart = buildChartSummary(data, opts);
  const signature = buildProfileSignature(data, topByPolarity, chart);
  const domains = buildDomainIndex(allTraits, {
    selectedDomains: filters.selectedDomains,
    domainSearch: filters.domainSearch,
  });
  return {
    chart,
    signature,
    signals,
    domains,
    topByPolarity,
    allTraits,
    filteredTraits,
    summaryTraits: summaryTraits(data),
  };
}
