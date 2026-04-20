import { describe, expect, it } from 'vitest';

import { dedupeAspectRows, transformDashboard } from '../features/astroclock/transform.mjs';

describe('astroclock aspect data pipeline', () => {
  it('dedupes the same pair/aspect and keeps the tighter orb', () => {
    const rows = dedupeAspectRows([
      { planet1: 'Moon', planet2: 'Saturn', aspect: 'Conjunction', orb: 2.1, phase: 'separating' },
      { planet1: 'Saturn', planet2: 'Moon', aspect: 'Conjunction', orb: 0.4, phase: 'applying' },
      { planet1: 'Mars', planet2: 'Saturn', aspect: 'Conjunction', orb: 2.5 },
    ]);

    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      planet1: 'Saturn',
      planet2: 'Moon',
      aspect: 'Conjunction',
      orb: 0.4,
      phase: 'applying',
    });
  });

  it('prefers the precise aspect list for standard current aspects', () => {
    const transformed = transformDashboard({
      top_aspects: [
        { planet1: 'Moon', planet2: 'Saturn', aspect: 'Conjunction', orb: 2.1 },
      ],
      planetary_aspects_precise: [
        { planet1: 'Saturn', planet2: 'Moon', aspect: 'Conjunction', orb: 0.4, phase: 'applying', allowed_orb: 8 },
        { planet1: 'Mars', planet2: 'Saturn', aspect: 'Conjunction', orb: 2.5, phase: 'applying', allowed_orb: 8 },
      ],
      morin_aspects: [],
      morin_antiscia: [],
      morin_contra_antiscia: [],
      planets: [],
      fixed_star_hits: [],
      house_cusps: [],
      house_rulers: {},
      special_degrees: [],
      metrics: {},
    });

    expect(transformed.tightest_aspect).toMatchObject({
      planet1: 'Saturn',
      planet2: 'Moon',
      aspect: 'Conjunction',
      orb: 0.4,
      max_orb: 8,
    });
    expect(transformed.top_aspects[0]).toMatchObject({
      planet1: 'Saturn',
      planet2: 'Moon',
      orb: 0.4,
      max_orb: 8,
    });
    expect(transformed.planetary_aspects_precise).toHaveLength(2);
  });
});
