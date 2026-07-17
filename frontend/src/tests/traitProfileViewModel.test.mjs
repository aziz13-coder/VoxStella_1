import { describe, expect, it } from 'vitest';
import {
  buildDomainIndex,
  buildHouseDeterminationChannels,
  buildPolaritySignals,
  buildProfileSignature,
  buildTopByPolarity,
  buildTraitProfileViewModel,
  filterAndSortTraits,
  sectLabel,
  traitMatchesSourceFilter,
  weightedAverageScore,
} from '../features/astroclock/traitProfileViewModel.mjs';

const trait = (overrides) => ({
  id: overrides.id,
  name: overrides.name || overrides.id,
  score: overrides.score ?? 50,
  raw_score: overrides.raw_score ?? 10,
  max_score: overrides.max_score ?? 20,
  support_hits: overrides.support_hits ?? 1,
  support_total: overrides.support_total ?? 1,
  band: overrides.band || 'likely',
  polarity: overrides.polarity || 'positive',
  domain: overrides.domain || 'general',
  source_status: overrides.source_status || 'curated',
  source_lineage: overrides.source_lineage || 'carter',
  source_lineage_label: overrides.source_lineage_label || 'Carter-derived',
  family_representative: overrides.family_representative ?? true,
  summary_eligible: overrides.summary_eligible ?? true,
  summary_priority: overrides.summary_priority ?? 0,
  keywords: overrides.keywords || [],
  ...overrides,
});

describe('traitProfileViewModel', () => {
  it('computes weighted polarity signals only from real trait scores', () => {
    const topByPolarity = {
      positive: [
        trait({ id: 'generosity', score: 90, support_hits: 3 }),
        trait({ id: 'wit', score: 60, support_hits: 1 }),
      ],
      neutral: [
        trait({ id: 'frankness', score: 70, support_hits: 2, polarity: 'neutral' }),
      ],
      negative: [
        trait({ id: 'rashness', score: 40, support_hits: 1, polarity: 'negative' }),
      ],
    };

    expect(weightedAverageScore(topByPolarity.positive)).toBe(83);
    const signals = buildPolaritySignals(topByPolarity);
    expect(signals.constructive.value).toBe(83);
    expect(signals.style.value).toBe(70);
    expect(signals.strain.value).toBe(40);
    expect(signals.profileBalanceIndex).toBe(72);
  });

  it('returns null for unavailable aggregate signals instead of decorative zeroes', () => {
    const signals = buildPolaritySignals({ positive: [], neutral: [], negative: [] });
    expect(signals.constructive.value).toBeNull();
    expect(signals.style.value).toBeNull();
    expect(signals.strain.value).toBeNull();
    expect(signals.profileBalanceIndex).toBeNull();
  });

  it('normalizes sect labels from backend chart_sect payloads', () => {
    expect(sectLabel({ chart_sect: 'diurnal' })).toBe('Day');
    expect(sectLabel({ chart_sect: 'nocturnal' })).toBe('Night');
    expect(sectLabel({ chart_sect: null })).toBeNull();
  });

  it('filters by strength, polarity, source lineage, citation layers, domains, and sort order', () => {
    const traits = [
      trait({ id: 'a', name: 'A', score: 80, band: 'strong', polarity: 'positive', domain: 'mind', source_lineage: 'carter' }),
      trait({
        id: 'b',
        name: 'B',
        score: 70,
        band: 'strong',
        polarity: 'positive',
        domain: 'mind',
        source_lineage: 'carter',
        citations: [{ source_lineage: 'modern' }],
      }),
      trait({ id: 'c', name: 'C', score: 95, band: 'likely', polarity: 'negative', domain: 'risk', source_lineage: 'classical' }),
    ];

    expect(traitMatchesSourceFilter(traits[1], 'modern')).toBe(true);
    const filtered = filterAndSortTraits(traits, {
      band: 'strong',
      polarity: 'positive',
      sourceFilter: 'modern',
      selectedDomains: ['mind'],
      sortBy: 'score',
    });
    expect(filtered.map((row) => row.id)).toEqual(['b']);
  });

  it('builds real domain counts without hard-coded sketch totals', () => {
    const traits = [
      trait({ id: 'a', domain: 'speech' }),
      trait({ id: 'b', domain: 'speech' }),
      trait({ id: 'c', domain: 'learning' }),
    ];

    const domains = buildDomainIndex(traits, { selectedDomains: ['speech'] });
    expect(domains.totalCount).toBe(2);
    expect(domains.selectedCount).toBe(1);
    expect(domains.traitCount).toBe(3);
    expect(domains.counts).toEqual({ learning: 1, speech: 2 });
  });

  it('derives house determination channels from real influence values', () => {
    const channels = buildHouseDeterminationChannels({
      influences: [
        { type: 'occupation', value: 30 },
        { type: 'rulership', value: 10 },
        { type: 'co_rulership', value: 5 },
        { type: 'aspect', value: 15 },
      ],
    });

    expect(channels.total).toBe(60);
    expect(channels.presenceValue).toBe(30);
    expect(channels.governanceValue).toBe(15);
    expect(channels.aspectValue).toBe(15);
    expect(Math.round(channels.presence * 100)).toBe(50);
    expect(Math.round(channels.governance * 100)).toBe(25);
    expect(Math.round(channels.aspect * 100)).toBe(25);
  });

  it('prefers backend polarity buckets and derives a deterministic profile signature', () => {
    const data = {
      summary: { dominant_element: 'Air', dominant_modality: 'Mutable' },
      sect: { sect: 'Diurnal' },
      chart_snapshot: {
        timestamp: '2026-05-05T10:45:00Z',
        location: 'Greenwich, UK',
        timezone_label: 'Europe/London (UTC+01:00)',
        house_system: 'R',
        house_rulers: { 1: 'Mercury' },
      },
      top_traits_by_polarity: {
        positive: [trait({ id: 'perception', name: 'Perceptiveness', score: 88, support_hits: 2 })],
        neutral: [trait({ id: 'frankness', name: 'Frankness', score: 72, support_hits: 2, polarity: 'neutral' })],
        negative: [trait({ id: 'rashness', name: 'Rashness', score: 61, support_hits: 1, polarity: 'negative' })],
      },
      traits: [
        trait({ id: 'perception', name: 'Perceptiveness', score: 88, support_hits: 2, domain: 'mind' }),
        trait({ id: 'frankness', name: 'Frankness', score: 72, support_hits: 2, polarity: 'neutral', domain: 'speech' }),
        trait({ id: 'rashness', name: 'Rashness', score: 61, support_hits: 1, polarity: 'negative', domain: 'risk' }),
      ],
    };

    const top = buildTopByPolarity(data, { topCount: 6 });
    expect(top.positive[0].id).toBe('perception');

    const vm = buildTraitProfileViewModel(data, { filters: { topCount: 6 } });
    expect(vm.chart.chartRuler).toBe('Mercury');
    expect(vm.signature.line).toBe('Mutable Air profile led by Perceptiveness; Rashness is the main strain.');
    expect(vm.signals.profileBalanceIndex).toBe(64);

    const directSignature = buildProfileSignature(data, top, vm.chart);
    expect(directSignature.note).toContain('strongest constructive');
  });
});
