import { describe, expect, test } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

import { normalizeHoraryApiResult } from '../utils/normalizeHoraryApiResult.mjs';

const corpusPath = path.resolve(process.cwd(), '../tests/fixtures/horary_hard_test_corpus.json');
const corpus = JSON.parse(readFileSync(corpusPath, 'utf8'));

const oppositeVerdict = (verdict) => (verdict === 'YES' ? 'NO' : 'YES');
const expectedOutcome = (verdict) => {
  if (verdict === 'YES') return 'positive';
  if (verdict === 'UNCLEAR') return 'uncertain';
  return 'negative';
};

describe('horary hard corpus frontend parity', () => {
  test('starter corpus covers at least ten backend-validated cases', () => {
    expect(corpus.length).toBeGreaterThanOrEqual(10);
  });

  for (const entry of corpus) {
    test(`preserves backend verdict for ${entry.id}`, () => {
      const normalized = normalizeHoraryApiResult({
        judgment: entry.expected_verdict,
        result: oppositeVerdict(entry.expected_verdict),
        confidence_breakdown: { final_confidence: 64 },
        question_analysis: { question_type: entry.expected_category.toUpperCase() },
        chart_data: {
          aspects: [{ planet1: 'Moon', planet2: 'Mars', applying: 1 }],
        },
      });

      expect(normalized.judgment).toBe(entry.expected_verdict);
      expect(normalized.outcome).toBe(expectedOutcome(entry.expected_verdict));
      expect(normalized.tags).toEqual([entry.expected_category]);
      expect(normalized.chart_data.aspects[0].applying).toBe(true);
    });
  }
});
