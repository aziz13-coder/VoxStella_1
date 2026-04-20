import { describe, expect, it } from 'vitest';

import {
  buildProcessedAbductionBearings,
  formatAbductionBearingRoleLabel,
  getAbductionLegendEntries,
  getAbductionRoleLabel,
  getAbductionRoleStyle,
  normalizeCoordinateInput,
} from '../features/astroclock/forensicAbductionMap.mjs';

describe('forensic abduction map helpers', () => {
  it('normalizes coordinate input with unicode minus characters', () => {
    expect(normalizeCoordinateInput(' \u221231.7683 ')).toBe('-31.7683');
    expect(normalizeCoordinateInput('47.84212')).toBe('47.84212');
  });

  it('exposes clean legend labels for the frontend map', () => {
    const legend = getAbductionLegendEntries();
    expect(legend.map((entry) => entry.legendLabel)).toEqual(
      expect.arrayContaining([
        '1st ruler | victim',
        '7th ruler | perpetrator',
        'Moon | movement',
        '9th ruler | abductor route and distance',
        '12th ruler | hidden or confinement',
      ]),
    );
    expect(getAbductionRoleLabel('H3_ruler')).toBe('3rd ruler (local route and vehicle)');
    expect(getAbductionRoleStyle('H9_ruler')).toMatchObject({ color: '#7c3aed', dashArray: '10 6' });
  });

  it('replaces raw 7th-planet bearings with a first-ruler victim bearing', () => {
    const bearings = [
      { role: 'Moon', planet: 'Moon', azimuth_deg: 12 },
      { role: 'H7_planet', planet: 'Mars', azimuth_deg: 55 },
      { role: 'misc', planet: 'Venus', azimuth_deg: 130 },
    ];

    const processed = buildProcessedAbductionBearings(bearings, 'Mars');

    expect(processed.some((bearing) => bearing.role === 'H7_planet')).toBe(false);
    expect(processed.some((bearing) => bearing.role === 'H1_ruler' && bearing.planet === 'Mars' && bearing.azimuth_deg === 55)).toBe(true);
  });

  it('promotes a late first-ruler bearing into the visible top six list', () => {
    const bearings = [
      { role: 'Moon', planet: 'Moon', azimuth_deg: 1 },
      { role: 'H3_ruler', planet: 'Mercury', azimuth_deg: 2 },
      { role: 'H9_ruler', planet: 'Saturn', azimuth_deg: 3 },
      { role: 'H12_ruler', planet: 'Neptune', azimuth_deg: 4 },
      { role: 'misc', planet: 'Venus', azimuth_deg: 6 },
      { role: 'misc', planet: 'Mars', azimuth_deg: 7 },
    ];

    const processed = buildProcessedAbductionBearings(bearings, 'Mars');

    expect(processed[0]).toMatchObject({ role: 'H1_ruler', planet: 'Mars', azimuth_deg: 7 });
    expect(processed.slice(0, 6).some((bearing) => bearing.role === 'H1_ruler')).toBe(true);
  });

  it('merges duplicate bearings when one planet carries multiple map roles', () => {
    const processed = buildProcessedAbductionBearings([
      { role: 'H1_ruler', planet: 'Saturn', azimuth_deg: 64.8, altitude_deg: 10.2 },
      { role: 'H12_ruler', planet: 'Saturn', azimuth_deg: 64.8, altitude_deg: 10.2 },
      { role: 'H3_ruler', planet: 'Venus', azimuth_deg: 189.83 },
      { role: 'H9_ruler', planet: 'Venus', azimuth_deg: 189.83 },
    ]);

    expect(processed).toHaveLength(2);
    expect(processed[0]).toMatchObject({ role: 'H1_ruler', role_aliases: ['H12_ruler'] });
    expect(processed[1]).toMatchObject({ role: 'H3_ruler', role_aliases: ['H9_ruler'] });
    expect(formatAbductionBearingRoleLabel(processed[1])).toBe(
      '3rd ruler (local route and vehicle) + 9th ruler (abductor route and distance)',
    );
  });
});
