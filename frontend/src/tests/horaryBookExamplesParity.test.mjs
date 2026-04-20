import fs from 'node:fs';
import path from 'node:path';

import { describe, expect, test } from 'vitest';

import { normalizeHoraryApiResult } from '../utils/normalizeHoraryApiResult.mjs';

const fixturePath = path.resolve(
  process.cwd(),
  '..',
  'tests',
  'fixtures',
  'horary_book_examples_replay.json',
);
const corpus = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));

describe('horary book examples frontend parity', () => {
  test('book replay corpus has both aligned and disagreement cases', () => {
    expect(corpus.length).toBeGreaterThanOrEqual(30);
    expect(corpus.some((item) => item.source_alignment)).toBe(true);
    expect(corpus.some((item) => !item.source_alignment)).toBe(true);
  });

  test.each(corpus)('normalization preserves backend verdict for $id', (item) => {
    const conflictingResult = item.engine_expected_verdict === 'YES' ? 'NO' : 'YES';
    const expectedTag = item.engine_expected_category.replace(/_/g, ' ');
    const normalized = normalizeHoraryApiResult({
      judgment: item.engine_expected_verdict,
      result: conflictingResult,
      confidence: 61,
      question_analysis: { question_type: item.engine_expected_category.toUpperCase() },
      chart_data: {
        aspects: [{ planet1: 'Moon', planet2: 'Mars', applying: 1 }],
      },
    });

    expect(normalized.judgment).toBe(item.engine_expected_verdict);
    expect(normalized.tags).toEqual([expectedTag]);
    expect(normalized.outcome).toBe(
      item.engine_expected_verdict === 'YES' ? 'positive' : 'negative',
    );
    expect(normalized.chart_data.aspects[0].applying).toBe(true);
  });
});
