import { describe, expect, it } from 'vitest';

import {
  buildForensicResultTextBlob,
  cleanForensicDisplayText,
  deriveForensicReplayAxes,
  formatForensicDisplayLabel,
  forensicKeywordMatches,
  getForensicReplayTailoring,
} from '../features/astroclock/forensicReplayAxes.mjs';

describe('forensic replay axis derivation', () => {
  it('derives MLK-style replay axes from raw backend findings', () => {
    const payload = {
      categories: {
        Associates: 1,
        Deception: 2,
        Public: 1,
        Violence: 1,
      },
      findings: [
        { title: 'Life/death overlap points to violence or homicide', category: 'Violence' },
        { title: 'Public or authority axis is foregrounded', category: 'Public' },
        { title: 'Friend or close associate axis is active', category: 'Associates' },
        { title: 'Mercury in a mute sign', category: 'Deception' },
      ],
    };

    expect(buildForensicResultTextBlob(payload)).toContain('life/death overlap points to violence or homicide');
    expect(deriveForensicReplayAxes(payload)).toEqual(
      expect.arrayContaining([
        'violence_homicide',
        'authority_or_public_case',
        'friend_or_close_associate',
        'deception_coverup',
      ]),
    );
    expect(deriveForensicReplayAxes(payload)).not.toContain('accident_or_disaster');
  });

  it('formats replay labels without underscores for frontend display', () => {
    expect(formatForensicDisplayLabel('authority_or_public_case')).toBe('Authority Or Public Case');
    expect(cleanForensicDisplayText('life/death_overlap points to violence_or homicide')).toBe(
      'life/death overlap points to violence or homicide',
    );
  });

  it('matches replay keywords as terms instead of substrings', () => {
    expect(forensicKeywordMatches('known-person home-axis violence', 'son')).toBe(false);
    expect(deriveForensicReplayAxes({ categories: { Violence: 1 }, findings: [] })).not.toContain('child_victim');
    expect(deriveForensicReplayAxes({ categories: { Family: 1 }, findings: [] })).toContain('family_involvement');
    expect(deriveForensicReplayAxes({ findings: [{ title: 'Home axis scene marker', category: 'General' }] })).not.toContain('family_involvement');
  });

  it('does not promote incidental rationale terms into visible case axes', () => {
    const axes = deriveForensicReplayAxes({
      categories: { Deception: 1 },
      findings: [
        {
          title: 'Domestic deception pattern',
          category: 'Deception',
          rationale: 'Not a child abduction, missing person, water disappearance, accident, public authority case, or witness-led case.',
        },
      ],
    });

    expect(axes).toEqual(['deception_coverup', 'domestic_partner_involvement']);
  });

  it('uses backend survivability evidence to suppress broad abduction axes in fatal household cases', () => {
    const payload = {
      categories: {
        Abduction: 1,
        Deception: 4,
        Family: 1,
        Water: 1,
      },
      findings: [
        { title: 'Abduction or deceptive public-assignment seizure pattern is active', category: 'Abduction', weight: 4 },
        { title: 'Family or household relationship cluster is active', category: 'Family', weight: 3 },
        { title: 'Water or drowning signatures are foregrounded', category: 'Water', weight: 3 },
      ],
      survivability: {
        level: 'Lower',
        outcome_band: 'fatal_pressure_dominant',
        case_type: 'general',
        breakdown: { fatal_pressure: 4.7 },
        evidence: {
          fatal_pressure: [
            'family/household fatal-harm mechanism +3.2',
            'domestic/known-person fatal context keeps abduction weighting from downscaling fatal pressure',
          ],
        },
      },
    };

    expect(getForensicReplayTailoring(payload).domesticFatalContext).toBe(true);
    expect(deriveForensicReplayAxes(payload)).toEqual([
      'violence_homicide',
      'family_involvement',
      'domestic_partner_involvement',
    ]);
  });
});
