import { describe, expect, it } from 'vitest';

import { buildSolarConditionEntries } from '../features/astroclock/solarConditions.mjs';

describe('AstroClock solar condition entries', () => {
  it('omits Morin planets that are free of solar affliction', () => {
    const entries = buildSolarConditionEntries({
      morin_combustion: [
        { planet: 'Mercury', status: 'free', distance_deg: 30.2 },
        { planet: 'Venus', status: 'under_beams', distance_deg: 12.4 },
      ],
    }, true);

    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({
      planet: 'Venus',
      tone: 'under_beams',
      label: 'under beams',
      detail: '12.40° from Sun',
    });
  });

  it('returns an empty Morin list when every planet is free', () => {
    const entries = buildSolarConditionEntries({
      morin_combustion: [
        { planet: 'Mercury', status: 'free', distance_deg: 30.2 },
        { planet: 'Venus', status: 'free', distance_deg: 40.1 },
      ],
    }, true);

    expect(entries).toEqual([]);
  });

  it('uses plain solar-separation wording for traditional combustion rows', () => {
    const entries = buildSolarConditionEntries({
      solar_conditions: {
        combustion: [
          { planet: 'Mercury', distance_from_sun: 2.38 },
        ],
      },
    }, false);

    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({
      planet: 'Mercury',
      tone: 'combust',
      label: 'Combustion',
      detail: '2.38° from Sun',
    });
  });
});
