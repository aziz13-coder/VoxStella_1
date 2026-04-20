import { describe, expect, it } from 'vitest';

import { formatChartSourceForApi, getChartSourceInstant } from '../utils/chartTime.mjs';

describe('chartTime', () => {
  it('prefers the engine utc timestamp over mutable chart metadata', () => {
    const chart = {
      timestamp: '2026-03-22T08:45:00.000Z',
      chart_data: {
        timezone_info: {
          utc_time: '2001-05-15T14:20:00.000Z',
        },
      },
    };

    expect(getChartSourceInstant(chart)?.toISOString()).toBe('2001-05-15T14:20:00.000Z');
  });

  it('formats the original instant using the chart timezone for reruns', () => {
    const chart = {
      timestamp: '2026-03-22T08:45:00.000Z',
      chart_data: {
        timezone_info: {
          utc_time: '2001-05-15T14:20:00.000Z',
          timezone: 'America/New_York',
        },
      },
    };

    expect(formatChartSourceForApi(chart)).toMatchObject({
      date: '15/05/2001',
      time: '10:20',
      timezone: 'America/New_York',
    });
  });
});
