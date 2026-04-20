import { describe, expect, it } from 'vitest';

import { buildChartPayload } from '../utils/buildChartPayload.js';


describe('buildChartPayload AI export contract', () => {
  it('preserves house rulers and core horary context for external audits', () => {
    const chart = {
      id: 1757726941666,
      question: 'Will I get a job? (government position)',
      category: 'career',
      timestamp: '2001-05-15T14:20:00.000Z',
      chart_data: {
        timezone_info: {
          utc_time: '2001-05-15T14:20:00.000Z',
          timezone: 'America/New_York',
          location_name: 'Washington, District of Columbia',
          coordinates: {
            latitude: 38.8950368,
            longitude: -77.0365427,
          },
        },
        location: {
          city: 'Washington',
          country: 'District of Columbia',
          latitude: 38.8950368,
          longitude: -77.0365427,
        },
        houses: [117.08, 139.65, 162.74, 192.33, 231.34, 269.05, 297.08, 319.65, 342.74, 12.33, 51.34, 89.05],
        house_rulers: {
          '1': 'Moon',
          '10': 'Mars',
        },
        ascendant: 117.08,
        midheaven: 12.33,
        considerations: {
          radical: false,
          moon_void: false,
        },
        moon_next_aspect: {
          planet: 'Mars',
          aspect: 'Sextile',
          applying: true,
        },
        aspects: [],
        planets: {},
      },
      traditional_factors: {
        perfection_type: 'direct',
      },
      solar_factors: {},
      reasoning: [
        { rule: 'Querent: Moon (ruler of 1), Quesited: Mars (ruler of 10)' },
      ],
      judgment: 'YES',
      confidence: 66,
    };

    const payload = buildChartPayload(chart, false, true);

    expect(payload.category).toBe('career');
    expect(payload.rulers).toEqual({ '1': 'Moon', '10': 'Mars' });
    expect(payload.house_rulers).toEqual({ '1': 'Moon', '10': 'Mars' });
    expect(payload.ascendant).toBe(117.08);
    expect(payload.midheaven).toBe(12.33);
    expect(payload.considerations).toEqual({
      radical: false,
      moon_void: false,
    });
    expect(payload.moon_next_aspect).toEqual({
      planet: 'Mars',
      aspect: 'Sextile',
      applying: true,
    });
    expect(payload.verdict).toBeUndefined();
    expect(payload.reasoning).toBeUndefined();
  });

  it('exports lost-object verdicts with recoverability wording while preserving the raw code', () => {
    const chart = {
      id: 1774245809366,
      question: 'is the iphone lost?',
      category: 'lost object',
      tags: ['lost object'],
      chart_data: {
        timezone_info: {
          utc_time: '2026-03-23T06:03:29.356Z',
          timezone: 'Asia/Jerusalem',
          location_name: 'Jerusalem, Israel',
          coordinates: {
            latitude: 31.7683,
            longitude: 35.2137,
          },
        },
        location: {
          city: 'Jerusalem',
          country: 'Israel',
          latitude: 31.7683,
          longitude: 35.2137,
        },
        houses: [],
        aspects: [],
        planets: {},
      },
      traditional_factors: {
        perfection_type: 'lost_object_discovery_balance',
      },
      lost_object_location: {
        applies: true,
        summary: 'With a friend; near the floor.',
        primary_places: [{ label: 'With a friend or among a friend\'s belongings' }],
      },
      reasoning: [],
      judgment: 'YES',
      confidence: 70,
    };

    const payload = buildChartPayload(chart, true, false);

    expect(payload.verdict).toEqual({
      label: 'RECOVERABLE',
      code: 'YES',
      confidence: 70,
      rationale: [],
    });
    expect(payload.lost_object_location).toEqual({
      applies: true,
      summary: 'With a friend; near the floor.',
      primary_places: [{ label: 'With a friend or among a friend\'s belongings' }],
    });
  });

  it('preserves missing-pet location clues in chart exports', () => {
    const chart = {
      id: 1774245809400,
      question: 'Will my dog come home?',
      category: 'pet',
      tags: ['pet'],
      chart_data: {
        timezone_info: {
          utc_time: '2025-01-07T04:19:00.000Z',
          timezone: 'America/New_York',
          location_name: 'Naples, New York',
          coordinates: {
            latitude: 42.6152778,
            longitude: -77.4027778,
          },
        },
        location: {
          city: 'Naples',
          country: 'United States',
          latitude: 42.6152778,
          longitude: -77.4027778,
        },
        houses: [],
        aspects: [],
        planets: {},
      },
      question_analysis: {
        question_type: 'PET',
        pet_analysis: { family: 'missing' },
      },
      traditional_factors: {
        perfection_type: 'pet_missing_balance',
      },
      lost_object_location: {
        applies: true,
        summary: 'Near home ground; search toward West by South.',
        directional_cues: [{ label: 'West by South' }],
      },
      reasoning: [],
      judgment: 'YES',
      confidence: 84,
    };

    const payload = buildChartPayload(chart, true, false);

    expect(payload.category).toBe('pet');
    expect(payload.verdict).toEqual({
      label: 'YES',
      code: 'YES',
      confidence: 84,
      rationale: [],
    });
    expect(payload.lost_object_location).toEqual({
      applies: true,
      summary: 'Near home ground; search toward West by South.',
      directional_cues: [{ label: 'West by South' }],
    });
  });
});
