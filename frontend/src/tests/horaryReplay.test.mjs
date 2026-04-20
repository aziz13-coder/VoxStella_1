import { describe, expect, it } from 'vitest';

import { buildChartReplayContext, buildChartReplayRequest } from '../utils/horaryReplay.mjs';

describe('horary replay helpers', () => {
  it('captures backend-resolved coordinates for future reruns', () => {
    const requestBody = {
      question: 'Will I get the job?',
      location: 'New York, NY, USA',
      useCurrentTime: false,
      date: '18/04/2026',
      time: '06:30',
      timezone: 'America/New_York',
      manualHouses: '1,10',
      ignoreVoidMoon: true,
      exaltationConfidenceBoost: 20,
    };

    const result = {
      chart_data: {
        timezone_info: {
          timezone: 'America/New_York',
          location_name: 'New York, New York, United States',
          coordinates: {
            latitude: 40.7128,
            longitude: -74.006,
          },
        },
      },
    };

    expect(buildChartReplayContext(requestBody, result)).toEqual({
      question: 'Will I get the job?',
      location: 'New York, NY, USA',
      location_name: 'New York, New York, United States',
      useCurrentTime: false,
      date: '18/04/2026',
      time: '06:30',
      timezone: 'America/New_York',
      latitude: 40.7128,
      longitude: -74.006,
      manualHouses: '1,10',
      ignoreRadicality: false,
      ignoreVoidMoon: true,
      ignoreCombustion: false,
      ignoreSaturn7th: false,
      exaltationConfidenceBoost: 20,
    });
  });

  it('builds deterministic replay requests from stored replay context', () => {
    const chart = {
      question: 'Will I get the job?',
      timestamp: '2026-04-18T10:30:00.000Z',
      replay_context: {
        question: 'Will I get the job?',
        location: 'New York, NY, USA',
        location_name: 'New York, New York, United States',
        useCurrentTime: true,
        date: '18/04/2026',
        time: '06:30',
        timezone: 'America/New_York',
        latitude: 40.7128,
        longitude: -74.006,
        manualHouses: '1,10',
        ignoreVoidMoon: true,
        exaltationConfidenceBoost: 20,
      },
      chart_data: {
        timezone_info: {
          utc_time: '2026-04-18T10:30:00.000Z',
          timezone: 'America/New_York',
          location_name: 'New York, New York, United States',
          coordinates: {
            latitude: 40.7128,
            longitude: -74.006,
          },
        },
      },
    };

    expect(buildChartReplayRequest(chart)).toEqual({
      question: 'Will I get the job?',
      location: 'New York, New York, United States',
      useCurrentTime: false,
      date: '18/04/2026',
      time: '06:30',
      timezone: 'America/New_York',
      latitude: 40.7128,
      longitude: -74.006,
      locationName: 'New York, New York, United States',
      manualHouses: '1,10',
      ignoreVoidMoon: true,
      exaltationConfidenceBoost: 20,
    });
  });
});
