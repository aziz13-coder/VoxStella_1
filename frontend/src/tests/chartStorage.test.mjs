import { describe, expect, it } from 'vitest';

import { hydrateStoredCharts } from '../utils/chartStorage.mjs';

describe('hydrateStoredCharts', () => {
  it('keeps valid chart rows and backfills derived fields', () => {
    const charts = hydrateStoredCharts([
      {
        id: 1,
        question: 'Will the job come through?',
        timestamp: '2026-03-30T08:00:00.000Z',
        verdict: { confidence: 72 },
      },
    ]);

    expect(charts).toHaveLength(1);
    expect(charts[0].confidence).toBe(72);
    expect(charts[0].timestamp).toBeInstanceOf(Date);
    expect(charts[0].date).toBe('2026-03-30');
  });

  it('drops malformed rows instead of discarding the whole history', () => {
    const charts = hydrateStoredCharts([
      {
        id: 1,
        question: 'Keep me',
        timestamp: '2026-03-30T08:00:00.000Z',
        confidence: 81,
      },
      {
        id: 2,
        question: 'Bad row',
        timestamp: 'not-a-real-date',
      },
      null,
    ]);

    expect(charts).toHaveLength(1);
    expect(charts[0].id).toBe(1);
  });
});
