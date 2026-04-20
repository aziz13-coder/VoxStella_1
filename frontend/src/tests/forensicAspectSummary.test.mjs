import { describe, expect, it } from 'vitest';

import {
  dedupeForensicAspectLabels,
  formatForensicAspectLabels,
  normalizeForensicAspectLabel,
} from '../features/astroclock/forensicAspectSummary.mjs';

describe('forensic aspect summary formatting', () => {
  it('normalizes object entries and preserves applying markers', () => {
    expect(normalizeForensicAspectLabel({ type: 'conjunction', applying: true })).toBe('conjunction (app)');
    expect(normalizeForensicAspectLabel({ type: 'square', applying: false })).toBe('square');
  });

  it('deduplicates repeated reverse-alias labels and drops empty placeholders', () => {
    const labels = dedupeForensicAspectLabels([
      { type: 'conjunction', applying: false },
      'conjunction',
      'conjunction, ',
      '',
      '-',
      null,
      undefined,
      { type: '', applying: false },
      { type: 'square', applying: false },
    ]);

    expect(labels).toEqual(['conjunction', 'square']);
  });

  it('renders a clear fallback when no usable aspects are present', () => {
    expect(formatForensicAspectLabels([])).toBe('none');
    expect(formatForensicAspectLabels(['', '-', null])).toBe('none');
  });
});

