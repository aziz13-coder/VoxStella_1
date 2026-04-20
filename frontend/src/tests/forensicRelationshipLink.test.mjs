import { describe, expect, it } from 'vitest';

import {
  buildRelationshipDisplayRows,
  formatRelationshipRulershipLinks,
  summarizeForensicRelationshipLink,
} from '../features/astroclock/forensicRelationshipLink.mjs';

describe('forensic relationship link classification', () => {
  it('does not overclaim intimate/family for public associate cases', () => {
    const summary = summarizeForensicRelationshipLink({
      score: 10,
      victimHouse: 5,
      perpHouse: 11,
      seventhHousePlanets: ['Mars'],
      isMutual: false,
      forensicResult: {
        categories: { Associates: 1, Public: 1, Violence: 1 },
        findings: [
          { title: 'Friend or close associate axis is active', category: 'Associates' },
          { title: 'Public or authority axis is foregrounded', category: 'Public' },
          { title: 'Life/death overlap points to violence or homicide', category: 'Violence' },
        ],
      },
    });

    expect(summary.relationshipType).toBe('Associate/public-network link');
    expect(summary.relationshipType).not.toBe('Intimate/Family');
    expect(summary.confidence).toBe('Moderate');
  });

  it('preserves explicit family-linked classifications', () => {
    const summary = summarizeForensicRelationshipLink({
      score: 9,
      victimHouse: 4,
      perpHouse: 4,
      seventhHousePlanets: ['Moon'],
      isMutual: true,
      forensicResult: {
        findings: [{ title: 'Domestic axis is emphasized', category: 'Houses' }],
      },
    });

    expect(summary.relationshipType).toBe('Family-linked');
    expect(summary.confidence).toBe('High');
  });

  it('formats relationship display rows without backend-native arrows or check markers', () => {
    const rows = buildRelationshipDisplayRows({
      firstRuler: 'Saturn',
      moonContacts: ['trine (app)'],
      ascRulerContacts: ['conjunction'],
      directVictRulesPerp: true,
      directPerpRulesVict: false,
      isMutual: false,
      level3: true,
      exaltationFallFlags: ['victim in exaltation of perpetrator'],
      level5Terms: true,
      houseConnections: ['victim ruler in 1st', 'perp ruler in 11th'],
      traditionalCues: ['Mars in 7th'],
      aspectTies: ['harmonious conjunction'],
      degreeStarCues: ['15° marker'],
      score: 12,
      relationshipType: 'Associate/public-network link',
      confidence: 'Moderate',
    });

    expect(rows.contactSignals).toContain('Moon: Moon trine (app)');
    expect(rows.rulershipLinks).toBe('victim ruler disposits perpetrator sign');
    expect(rows.mutualReception).toBe('none');
    expect(rows.sharedTriplicity).toBe('shared triplicity');
    expect(rows.termBoundsTies).toBe('term/bounds tie present');
    expect(rows.connectionSummary).toBe('Score 12 | Associate/public-network link | Moderate confidence');
  });

  it('compresses two-way rulership into a single readable phrase', () => {
    expect(
      formatRelationshipRulershipLinks({
        directVictRulesPerp: true,
        directPerpRulesVict: true,
      }),
    ).toBe('two-way rulership link');
  });
});

