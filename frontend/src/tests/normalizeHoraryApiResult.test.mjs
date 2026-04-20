import { describe, expect, test } from 'vitest';

import {
  normalizeHoraryApiResult,
} from '../utils/normalizeHoraryApiResult.mjs';

describe('normalizeHoraryApiResult', () => {
  test('preserves backend judgment even if a secondary result field disagrees', () => {
    const normalized = normalizeHoraryApiResult({
      judgment: 'YES',
      result: 'NO',
      confidence_breakdown: { final_confidence: 66 },
      question_analysis: { question_type: 'CAREER' },
      chart_data: {
        aspects: [{ planet1: 'Moon', planet2: 'Mars', applying: 1 }],
      },
    });

    expect(normalized.judgment).toBe('YES');
    expect(normalized.outcome).toBe('positive');
    expect(normalized.confidence).toBe(66);
    expect(normalized.tags).toEqual(['career']);
    expect(normalized.chart_data.aspects[0].applying).toBe(true);
  });

  test('recomputes outcome and preserves id on rerun updates', () => {
    const normalized = normalizeHoraryApiResult(
      {
        judgment: 'NO',
        question_analysis: { question_type: 'PROPERTY' },
      },
      {
        existingChart: {
          id: 42,
          judgment: 'YES',
          outcome: 'positive',
          tags: ['career'],
          confidence: 71,
        },
      },
    );

    expect(normalized.id).toBe(42);
    expect(normalized.judgment).toBe('NO');
    expect(normalized.outcome).toBe('negative');
    expect(normalized.tags).toEqual(['property']);
    expect(normalized.confidence).toBe(71);
  });

  test('derives lost-object display labels without changing the raw verdict code', () => {
    const normalized = normalizeHoraryApiResult({
      judgment: 'YES',
      question_analysis: { question_type: 'LOST_OBJECT' },
      lost_object_location: {
        applies: true,
        summary: 'With a friend; near the floor.',
      },
    });

    expect(normalized.judgment).toBe('YES');
    expect(normalized.judgment_display).toBe('RECOVERABLE');
    expect(normalized.outcome).toBe('positive');
    expect(normalized.tags).toEqual(['lost object']);
    expect(normalized.lost_object_location).toEqual({
      applies: true,
      summary: 'With a friend; near the floor.',
    });
  });

  test('preserves missing-pet location clues and rerun identity on updated saved charts', () => {
    const normalized = normalizeHoraryApiResult(
      {
        judgment: 'YES',
        question_analysis: {
          question_type: 'PET',
          pet_analysis: { family: 'missing' },
          significators: { pet_family: 'missing' },
        },
        traditional_factors: { perfection_type: 'pet_missing_balance' },
        lost_object_location: {
          applies: true,
          summary: 'Near home ground; search toward West by South.',
        },
      },
      {
        existingChart: {
          id: 84,
          judgment: 'NO',
          outcome: 'negative',
          confidence: 84,
          tags: ['pet'],
        },
      },
    );

    expect(normalized.id).toBe(84);
    expect(normalized.judgment).toBe('YES');
    expect(normalized.outcome).toBe('positive');
    expect(normalized.tags).toEqual(['pet']);
    expect(normalized.lost_object_location).toEqual({
      applies: true,
      summary: 'Near home ground; search toward West by South.',
    });
  });
});
