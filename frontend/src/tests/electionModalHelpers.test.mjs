import { describe, expect, it } from 'vitest';

import {
  BUSINESS_ALPHA_DESCRIPTION,
  BUSINESS_BETA_DESCRIPTION,
  BUSINESS_BETA_PARTICIPANT_HELP,
  MARRIAGE_ALPHA_DESCRIPTION,
  MARRIAGE_BETA_DESCRIPTION,
  MARRIAGE_BETA_PARTICIPANT_HELP,
  buildBusinessBetaLineOptions,
  mergeElectionTimelineRows,
  parseElectionClockValue,
  sanitizeBusinessBetaElectionRow,
  sanitizeBusinessBetaTagDisplay,
  sanitizeMarriageBetaElectionRow,
  sanitizeMarriageBetaTagDisplay,
} from '../features/astroclock/ElectionModal.jsx';


describe('ElectionModal helpers', () => {
  it('parses local clock filters with minute precision', () => {
    expect(parseElectionClockValue('09:30')).toBe(570);
    expect(parseElectionClockValue('17')).toBe(1020);
    expect(parseElectionClockValue('23:59')).toBe(1439);
    expect(parseElectionClockValue('24:00')).toBeNull();
    expect(parseElectionClockValue('bad')).toBeNull();
  });

  it('merges top-ranked rows into the retained timeline set', () => {
    const merged = mergeElectionTimelineRows(
      [
        { timestamp: '2026-04-15T08:00:00Z', score: 1.5 },
        { timestamp: '2026-04-15T09:00:00Z', score: 2.5 },
      ],
      [
        { timestamp: '2026-04-15T07:00:00Z', score: 4.5, pros: ['Best overall'] },
        { timestamp: '2026-04-15T09:00:00Z', score: 2.5, cautions: ['Shared row'] },
      ],
    );

    expect(merged.map((row) => row.timestamp)).toEqual([
      '2026-04-15T07:00:00Z',
      '2026-04-15T08:00:00Z',
      '2026-04-15T09:00:00Z',
    ]);
    expect(merged[0].pros).toEqual(['Best overall']);
    expect(merged[2].cautions).toEqual(['Shared row']);
  });

  it('uses separation-focused marriage algorithm copy without source-name leakage', () => {
    expect(MARRIAGE_ALPHA_DESCRIPTION.toLowerCase()).not.toContain('morin');
    expect(MARRIAGE_BETA_DESCRIPTION).toContain('separate');
    expect(MARRIAGE_BETA_DESCRIPTION).toContain('chart A');
    expect(MARRIAGE_BETA_DESCRIPTION).toContain('chart B');
    expect(MARRIAGE_BETA_PARTICIPANT_HELP).toContain('participant 1');
    expect(MARRIAGE_BETA_PARTICIPANT_HELP).toContain('participant 2');
  });

  it('describes business beta as an event-plus-founder workflow', () => {
    expect(BUSINESS_ALPHA_DESCRIPTION).toContain('current business election path');
    expect(BUSINESS_BETA_DESCRIPTION).toContain('event line');
    expect(BUSINESS_BETA_DESCRIPTION).toContain('founder-owner fit line');
    expect(BUSINESS_BETA_PARTICIPANT_HELP).toContain('founder or owner');
    expect(BUSINESS_BETA_PARTICIPANT_HELP).toContain('saved charts');
    expect(BUSINESS_BETA_PARTICIPANT_HELP).toContain('treated as certified');
  });

  it('builds business beta line options from selected founder charts', () => {
    const options = buildBusinessBetaLineOptions({
      snaps: [
        { id: 'snap-a', label: 'Founder A', location: 'Jerusalem' },
        { id: 'snap-b', label: 'Founder B', location: 'Tel Aviv' },
      ],
      participantSnapIds: ['snap-a', 'snap-b'],
    });

    expect(options).toEqual([
      { id: 'event', label: 'Event line', kind: 'event' },
      { id: 'participant:1', label: 'Founder A', kind: 'participant' },
      { id: 'participant:2', label: 'Founder B', kind: 'participant' },
    ]);
  });

  it('removes weight markers from beta marriage tag labels without removing the meaning', () => {
    expect(sanitizeMarriageBetaTagDisplay('Event Asc marriage sign support: Pisces (+3.0)')).toBe(
      'Event Asc marriage sign support: Pisces',
    );
    expect(sanitizeMarriageBetaTagDisplay('Event Moon day caution: 045/180 interval (-1.0)')).toBe(
      'Event Moon day caution: 045/180 interval',
    );
    expect(sanitizeMarriageBetaTagDisplay('Event Moon support +9')).toBe('Event Moon support');
    expect(sanitizeMarriageBetaTagDisplay('Event Moon support: Trine to Jupiter')).toBe(
      'Event Moon support: Trine to Jupiter',
    );
  });

  it('sanitizes beta marriage rows for export and display while preserving the score', () => {
    const sanitized = sanitizeMarriageBetaElectionRow({
      score: 5.76,
      tags: [
        'Event Asc marriage sign support: Pisces (+3.0)',
        'Event Moon support: Trine to Jupiter',
      ],
      pros: ['Event Asc marriage sign support: Pisces (+3.0)'],
      cautions: ['Event Moon day caution: 045/180 interval (-1.0)'],
    });

    expect(sanitized.score).toBe(5.76);
    expect(sanitized.tags).toEqual([
      'Event Asc marriage sign support: Pisces',
      'Event Moon support: Trine to Jupiter',
    ]);
    expect(sanitized.pros).toEqual(['Event Asc marriage sign support: Pisces']);
    expect(sanitized.cautions).toEqual(['Event Moon day caution: 045/180 interval']);
  });

  it('removes score suffixes from business beta tag labels without dropping the wording', () => {
    expect(sanitizeBusinessBetaTagDisplay('Event Moon sign support: Cancer (+3.0)')).toBe(
      'Event Moon sign support: Cancer',
    );
    expect(sanitizeBusinessBetaTagDisplay('Founder 1: Asc ruler falls in event 10th (+1.35)')).toBe(
      'Founder 1: Asc ruler falls in event 10th',
    );
  });

  it('sanitizes business beta rows for display while preserving score and tag grouping', () => {
    const sanitized = sanitizeBusinessBetaElectionRow({
      score: 8.25,
      tags: [
        'Event Moon sign support: Cancer (+3.0)',
        'Founder 1: event Fortuna contacts natal Asc (+1.2)',
      ],
      pros: ['Event Moon sign support: Cancer (+3.0)'],
      cautions: ['Event Moon damage: opposition Pluto (-1.5)'],
      lines: [
        {
          label: 'Event line',
          score: 5.5,
          favorable: 5.5,
          tense: 0,
          tags: ['Event Moon sign support: Cancer (+3.0)'],
          pros: ['Event Moon sign support: Cancer (+3.0)'],
          cautions: [],
        },
        {
          label: 'Founder 1',
          score: 2.75,
          favorable: 3.95,
          tense: 1.2,
          tags: ['Founder 1: event Fortuna contacts natal Asc (+1.2)'],
          pros: ['Founder 1: event Fortuna contacts natal Asc (+1.2)'],
          cautions: ['Founder 1: Asc ruler falls in event 12th (-0.8)'],
        },
      ],
    });

    expect(sanitized.score).toBe(8.25);
    expect(sanitized.tags).toEqual([
      'Event Moon sign support: Cancer',
      'Founder 1: event Fortuna contacts natal Asc',
    ]);
    expect(sanitized.pros).toEqual(['Event Moon sign support: Cancer']);
    expect(sanitized.cautions).toEqual(['Event Moon damage: opposition Pluto']);
    expect(sanitized.lines).toEqual([
      {
        label: 'Event line',
        score: 5.5,
        favorable: 5.5,
        tense: 0,
        tags: ['Event Moon sign support: Cancer'],
        pros: ['Event Moon sign support: Cancer'],
        cautions: [],
      },
      {
        label: 'Founder 1',
        score: 2.75,
        favorable: 3.95,
        tense: 1.2,
        tags: ['Founder 1: event Fortuna contacts natal Asc'],
        pros: ['Founder 1: event Fortuna contacts natal Asc'],
        cautions: ['Founder 1: Asc ruler falls in event 12th'],
      },
    ]);
  });
});
