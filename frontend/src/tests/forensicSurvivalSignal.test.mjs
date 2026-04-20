import { describe, expect, it } from 'vitest';

import { summarizeForensicSurvivalSignal } from '../features/astroclock/forensicSurvivalSignal.mjs';

describe('forensic survival signal', () => {
  it('prefers the backend survivability summary when present', () => {
    const summary = summarizeForensicSurvivalSignal({
      forensicResult: {
        survivability: {
          level: 'Moderate',
          score: 1.75,
          outcome_band: 'release_favored',
          case_type: 'adult_female',
          victim_significators: ['Mercury', 'Moon', 'Venus'],
          breakdown: {
            vitality: 1.0,
            accidental: 0.9,
            support: 2.5,
            recovery_support: 1.2,
            moon: 0.25,
            danger: 1.0,
            fatal_pressure: 1.0,
          },
          evidence: { vitality: [], support: [], recovery_support: [], moon: [], danger: [], fatal_pressure: [] },
          note: 'Derived from significator vitality, benefic support, Moon testimony, malefic pressure, and explicit death-edge findings.',
        },
      },
    });

    expect(summary.level).toBe('Moderate');
    expect(summary.score).toBe(1.75);
    expect(summary.outcomeBand).toBe('release_favored');
    expect(summary.caseType).toBe('adult_female');
    expect(summary.victimSignificators).toEqual(['Mercury', 'Moon', 'Venus']);
    expect(summary.breakdown.recovery_support).toBe(1.2);
  });

  it('keeps the legacy fallback when no backend summary exists', () => {
    const summary = summarizeForensicSurvivalSignal({
      total: 5,
      dangerScore: 0.4,
      forensicResult: {
        findings: [{ title: 'Friend or close associate axis is active', category: 'Associates' }],
      },
    });

    expect(summary.baseLevel).toBe('Higher');
    expect(summary.level).toBe('Higher');
    expect(summary.fatalOverride).toBe(false);
  });
});
