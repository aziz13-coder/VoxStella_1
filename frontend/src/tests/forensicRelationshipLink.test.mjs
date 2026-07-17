import { describe, expect, it } from 'vitest';

import {
  buildRelationshipDisplayRows,
  collectRelationshipAspectContacts,
  formatRelationshipRulershipLinks,
  scoreForensicRelationshipLink,
  summarizeForensicRelationshipLink,
} from '../features/astroclock/forensicRelationshipLink.mjs';

describe('forensic relationship link classification', () => {
  it('uses backend relationship status when the engine exposes it', () => {
    const summary = summarizeForensicRelationshipLink({
      score: 0,
      forensicResult: {
        relationship_status: {
          primary_label: 'intimate_partner',
          labels: ['intimate_partner'],
          confidence: 'Moderate',
          scores: { intimate_partner: 2.5 },
        },
        findings: [],
      },
    });

    expect(summary.relationshipType).toBe('Intimate/partner-linked');
    expect(summary.confidence).toBe('Moderate');
    expect(summary.relationshipStatus.labels).toEqual(['intimate_partner']);
  });

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

  it('dedupes symmetric aspect aliases before rendering relationship contacts', () => {
    const contacts = collectRelationshipAspectContacts({
      aspects: {
        Moon_to_Saturn: { type: 'opposition', applying: true, orb: 1.2 },
        Saturn_to_Moon: { type: 'opposition', applying: true, orb: 1.2 },
      },
      source: 'Saturn',
      target: 'Moon',
    });

    expect(contacts).toEqual(['opposition applying']);
  });

  it('scores relationship links with one shared rubric for UI and copied brief', () => {
    const score = scoreForensicRelationshipLink({
      victimHouse: 7,
      perpHouse: 1,
      sameHouse: false,
      directVictRulesPerp: true,
      isMutual: true,
      level3: true,
      level5Terms: true,
      criticalFamilyHouse: false,
      lightMediation: { translation: true },
      seventhHousePlanets: ['Mars'],
      aspectType: 'trine',
      aspect: { applying: true },
      criticalDegree: true,
      hasViolentStar: true,
      hasProtectiveStar: true,
    });

    expect(score.score).toBe(23);
    expect(score.reasons).toContain('Terms/bounds connection');
    expect(score.reasons).toContain('Light mediation lacks victim-perpetrator bridge');
    expect(score.reasons).not.toContain('Critical house combination');
  });

  it('adds relationship testimony only when light mediation bridges victim and perpetrator significators', () => {
    const generic = scoreForensicRelationshipLink({
      lightMediation: { translation: true, translator: 'Mercury' },
      victimSignificators: ['Moon'],
      perpetratorSignificators: ['Saturn'],
    });
    const bridged = scoreForensicRelationshipLink({
      lightMediation: {
        translation: true,
        translator: 'Mercury',
        participants: ['Moon', 'Mercury', 'Saturn'],
        legs: [
          { aspect: 'trine', orb: 1.2, phase: 'separating' },
          { aspect: 'sextile', orb: 0.9, phase: 'applying' },
        ],
        favorable: true,
      },
      victimSignificators: ['Moon'],
      perpetratorSignificators: ['Saturn'],
    });

    expect(generic.score).toBe(0);
    expect(generic.lightMediationImpact.scoreDelta).toBe(0);
    expect(bridged.score).toBeGreaterThan(0);
    expect(bridged.lightMediationImpact.role).toBe('victim_perpetrator_bridge');
    expect(bridged.reasons).toContain('Translation of light bridges victim/perpetrator significators');
  });

  it('treats light prohibition as blocking testimony instead of relationship inflation', () => {
    const score = scoreForensicRelationshipLink({
      score: 0,
      lightMediation: {
        prohibition: true,
        denial_type: 'frustration',
        prohibitor: 'Mars',
        participants: ['Moon', 'Mars', 'Saturn'],
      },
      victimSignificators: ['Moon'],
      perpetratorSignificators: ['Saturn'],
    });

    expect(score.score).toBe(-1);
    expect(score.lightMediationImpact.scoreDelta).toBe(-1);
    expect(score.reasons).toContain('Light prohibition blocks victim/perpetrator perfection');
  });

  it('scores a Moon-dispositor bridge to the perpetrator ruler as known-person testimony', () => {
    const score = scoreForensicRelationshipLink({
      moonDispositorTiesPerp: true,
      moonDispositorHardContact: true,
    });

    expect(score.score).toBe(3);
    expect(score.reasons).toContain('Moon dispositor hard-linked to perpetrator ruler');
  });
});

