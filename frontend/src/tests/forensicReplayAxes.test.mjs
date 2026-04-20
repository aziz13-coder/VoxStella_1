import { describe, expect, it } from 'vitest';

import {
  buildForensicResultTextBlob,
  cleanForensicDisplayText,
  deriveForensicReplayAxes,
  formatForensicDisplayLabel,
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
});
