import { describe, expect, it } from 'vitest';

import {
  buildAbductionCueReportLines,
  buildAbductionCueSummary,
  normalizeAbductionCueText,
} from '../features/astroclock/forensicAbductionCues.mjs';

describe('forensic abduction cues formatter', () => {
  it('normalizes mojibake and punctuation in knowledge text', () => {
    expect(normalizeAbductionCueText('Tier D вЂ” Institutional / concealed')).toBe('Tier D - Institutional / concealed');
    expect(normalizeAbductionCueText('12th house в†’ hidden/secluded')).toBe('12th house -> hidden/secluded');
  });

  it('separates house cues, sign modifiers, and movement overlay cues', () => {
    const data = {
      abduction_location: {
        signs: {
          Pisces: ['hotels/hostels', 'waterfronts', 'hospitals/asylums', 'lost/missing/confusing places'],
          Virgo: ['workplaces/offices', 'clerical/records', 'pharmacies/clinics', 'small rooms/storage'],
        },
        houses: {
          '6': ['work/service places', 'coworkers', 'clinics/pharmacies/pets'],
          '12': ['hidden/enclosed', 'hospitals/prisons', 'secret enemies/eavesdropping/surveillance'],
        },
        tiers: {
          D: { title: 'Tier D вЂ” Institutional / concealed (hard access)' },
        },
        distance_modifiers: {
          Pisces_or_Neptune: ['hotels/waterfronts', 'lost/missing/ambiguous', 'distance by confusion'],
          Scorpio_or_12th: ['secrecy/hidden enemies', 'accessвЂ‘controlled areas'],
        },
      },
    };
    const features = {
      houses: { first_ruler: 'Mercury' },
      house_rulers: { '1': 'Mercury' },
      planets: {
        Mercury: { sign: 'Pisces', house: 6 },
        Moon: { sign: 'Virgo', house: 12 },
      },
      house_cusps: [330, 0, 0, 0, 0, 0, 0],
    };

    const summary = buildAbductionCueSummary({ data, features });

    expect(summary.victimAnchor).toBe('Mercury in Pisces (H6)');
    expect(summary.movementAnchor).toBe('Moon in Virgo (H12)');
    expect(summary.primaryHouseCues).toEqual([
      'work or service site',
      'medical or institutional care site',
    ]);
    expect(summary.primarySignCues).toEqual([
      'hospitality or short-stay lodging',
      'waterside or waterfront',
      'confusing or low-clarity setting',
    ]);
    expect(summary.movementCues).toEqual([
      'hidden or controlled-access area',
      'office, records, or small-room trail',
    ]);
    expect(summary.accessProfile.title).toBe('Tier D - Institutional / concealed (hard access)');
    expect(summary.accessNotes).toContain('hidden or controlled-access area');
    expect(summary.modifiers).toEqual([
      'hospitality or waterside',
      'confusion or low-clarity distance',
      'hidden or access-controlled approach',
    ]);
  });

  it('omits empty placeholder rows from the report lines', () => {
    const data = {
      abduction_location: {
        signs: { Aries: ['heat'] },
        houses: { '1': ['victim & immediate surroundings'] },
        tiers: { A: { title: 'Tier A - Immediate vicinity' } },
        distance_modifiers: {},
      },
    };
    const features = {
      houses: { first_ruler: 'Mars' },
      house_rulers: { '1': 'Mars' },
      planets: {
        Mars: { sign: 'Aries', house: 1 },
        Moon: { sign: 'Aries', house: 1 },
      },
      house_cusps: [0, 0, 0, 0, 0, 0, 0],
    };

    const lines = buildAbductionCueReportLines({ data, features }).join('\n');

    expect(lines).toContain('Victim signal: Mars in Aries (H1)');
    expect(lines).toContain('Access and distance: Tier A - Immediate vicinity');
    expect(lines).not.toContain('Distance cues: none');
    expect(lines).not.toContain('Context modifiers: none');
  });

  it('suppresses non-location houses and collapses noisy sign phrases into scene labels', () => {
    const data = {
      abduction_location: {
        signs: {
          Leo: ['stage/theater', 'gold/luxury', 'celebrity/spotlight places'],
          Taurus: ['cash/banks', 'food/kitchens', 'slow/nearby'],
        },
        houses: {
          '8': ['insurance/financial instruments', 'death matters', 'other people’s property/resources'],
          '2': ['the victim’s possessions/valuables', 'wallet/jewelry/cash', 'what’s ‘on them’ or at their place'],
        },
        tiers: { B: { title: 'Tier B — Local / adjacent' } },
        distance_modifiers: {},
      },
    };
    const features = {
      houses: { first_ruler: 'Sun' },
      house_rulers: { '1': 'Sun' },
      planets: {
        Sun: { sign: 'Leo', house: 8 },
        Moon: { sign: 'Taurus', house: 2 },
      },
      house_cusps: [120, 0, 0, 0, 0, 0, 0],
    };

    const summary = buildAbductionCueSummary({ data, features });

    expect(summary.primaryHouseCues).toEqual([]);
    expect(summary.accessNotes).toEqual([]);
    expect(summary.primarySignCues).toEqual([
      'social or entertainment venue',
      'public or high-visibility place',
    ]);
    expect(summary.movementCues).toEqual([
      'valuables or personal-effects trail',
      'food service or kitchen area',
    ]);
    expect(summary.distanceCues).toEqual(['nearby or slower access']);
    expect(summary.accessProfile.title).toBe('Tier B - Local / adjacent');
  });
});
