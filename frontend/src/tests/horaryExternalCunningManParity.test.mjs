import { describe, expect, test } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

import { normalizeHoraryApiResult } from '../utils/normalizeHoraryApiResult.mjs';

const corpusPath = path.resolve(
  process.cwd(),
  '../tests/fixtures/horary_external_cunning_man_replay.json',
);
const corpus = JSON.parse(readFileSync(corpusPath, 'utf8'));

const oppositeVerdict = (verdict) => (verdict === 'YES' ? 'NO' : 'YES');
const expectedOutcome = (verdict) => (verdict === 'YES' ? 'positive' : 'negative');

describe('external Cunning Man corpus frontend parity', () => {
  test('contains promoted external replay cases', () => {
    expect(corpus.length).toBeGreaterThanOrEqual(3);
  });

  for (const entry of corpus) {
    test(`preserves backend verdict for ${entry.id}`, () => {
      const normalized = normalizeHoraryApiResult({
        judgment: entry.engine_expected_verdict,
        result: oppositeVerdict(entry.engine_expected_verdict),
        confidence_breakdown: { final_confidence: 71 },
        question_analysis: { question_type: entry.engine_expected_category.toUpperCase() },
        chart_data: {
          aspects: [{ planet1: 'Moon', planet2: 'Mars', applying: 1 }],
        },
      });

      expect(normalized.judgment).toBe(entry.engine_expected_verdict);
      expect(normalized.outcome).toBe(expectedOutcome(entry.engine_expected_verdict));
      expect(normalized.tags).toEqual([entry.engine_expected_category]);
      expect(normalized.chart_data.aspects[0].applying).toBe(true);
    });
  }
});
