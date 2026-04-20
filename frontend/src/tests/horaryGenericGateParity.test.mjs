import { describe, expect, test } from 'vitest';

import { normalizeHoraryApiResult } from '../utils/normalizeHoraryApiResult.mjs';

describe('horary generic gate frontend parity', () => {
  test('preserves UNCLEAR verdicts emitted by the generic secondary-balance path', () => {
    const normalized = normalizeHoraryApiResult({
      judgment: 'UNCLEAR',
      result: 'NO',
      confidence: 57,
      question_analysis: { question_type: 'MARRIAGE' },
      traditional_factors: {
        perfection_type: 'mixed_or_inconclusive_secondary_balance',
      },
      chart_data: {
        aspects: [{ planet1: 'Moon', planet2: 'Venus', applying: 1 }],
      },
    });

    expect(normalized.judgment).toBe('UNCLEAR');
    expect(normalized.judgment_display).toBe('UNCLEAR');
    expect(normalized.outcome).toBe('uncertain');
    expect(normalized.tags).toEqual(['marriage']);
    expect(normalized.chart_data.aspects[0].applying).toBe(true);
  });
});
