import { describe, expect, it } from 'vitest';
import {
  getAstrocartographyTargetLabel,
  getAstrocartographyTargetQuery,
  normalizeAstrocartographyTargetText,
  resolveAstrocartographyTargetQuery,
} from '../features/astroclock/astrocartographyTargets.mjs';

describe('astrocartography target normalization', () => {
  it('rejects serialized object placeholders', () => {
    expect(normalizeAstrocartographyTargetText('[object Object]')).toBe('');
  });

  it('strips serialized object prefixes from malformed labels', () => {
    expect(
      normalizeAstrocartographyTargetText('[object Object], 11, South Union Street, London, Ohio'),
    ).toBe('11, South Union Street, London, Ohio');
  });

  it('prefers string query and label values from target payloads', () => {
    const target = {
      query: { bad: true },
      label: 'Tokyo, Japan',
      latitude: 35.6762,
      longitude: 139.6503,
    };
    expect(getAstrocartographyTargetQuery(target)).toBe('Tokyo, Japan');
    expect(getAstrocartographyTargetLabel(target)).toBe('Tokyo, Japan');
  });

  it('falls back to the typed query when an event object is passed accidentally', () => {
    const clickEventLike = {
      type: 'click',
      target: { value: 'Ignored event payload' },
      preventDefault() {},
    };
    expect(resolveAstrocartographyTargetQuery(clickEventLike, 'Ponta Delgada, Portugal')).toBe('Ponta Delgada, Portugal');
  });
});
