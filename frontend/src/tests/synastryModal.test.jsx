import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const astroClockApiMock = vi.hoisted(() => ({
  getSynastry: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

import SynastryModal from '../features/astroclock/SynastryModal.jsx';

const snaps = [
  {
    id: 'snap-a',
    label: 'Alpha',
    effective_datetime: '2026-03-08T10:00:00Z',
    location: 'Jerusalem, Israel',
    summary: { profile_hint: 'feminine' },
  },
  {
    id: 'snap-b',
    label: 'Beta',
    effective_datetime: '2026-03-07T10:00:00Z',
    location: 'London, UK',
    summary: { profile_hint: 'masculine' },
  },
  {
    id: 'snap-c',
    label: 'Gamma',
    effective_datetime: '2026-03-06T10:00:00Z',
    location: 'Paris, France',
    summary: { profile_hint: 'blended' },
  },
];

function makeSynastryResponse(overrides = {}) {
  return {
    success: true,
    data: {
      categories: [
        {
          id: 'overall',
          name: 'Overall',
          score: 74,
          raw_score: 7.4,
          max_score: 10,
          polarity: 'positive',
          description: 'Baseline relationship signal.',
          evidence: ['Shared traction stays visible.'],
          evidence_items: [],
          source_keys: ['davison'],
          rule_family_ids: ['cross_aspects'],
        },
      ],
      summary: {
        overall_components: {
          compatibility: 68,
          binding: 83,
          growth: 62,
          challenge: 28,
          support_balance: 57,
          reception_bonus: 1.5,
        },
        supportive_link_count: 1,
        challenging_link_count: 0,
        mutual_reception_count: 0,
        summary_lines: ['Shared traction stays visible.'],
      },
      top_supportive_links: [
        {
          label: 'Sun trine Moon',
          detail: 'The pair lands in a naturally cooperative rhythm.',
          impact: 3.2,
          source: 'davison',
          rule_family_id: 'cross_aspects',
        },
      ],
      top_challenging_links: [],
      overlays: {
        a_in_b: [],
        b_in_a: [],
      },
      chart_a: {
        label: 'Alpha',
      },
      chart_b: {
        label: 'Beta',
      },
      governance: {
        orb_profile: 'balanced',
        catalog_version: '2026-04-02',
        active_source_keys: ['davison'],
        active_rule_family_ids: ['cross_aspects'],
        rule_family_count: 1,
        point_capability: {
          modern_supported: true,
          chiron_supported: true,
        },
      },
      sources: [
        {
          key: 'davison',
          title: 'Davison',
          role: 'Core compatibility source',
        },
      ],
      ...overrides,
    },
  };
}

describe('SynastryModal refresh behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('keeps the current report visible while Chiron refreshes', async () => {
    let resolveSecondRequest;
    astroClockApiMock.getSynastry
      .mockResolvedValueOnce(makeSynastryResponse())
      .mockImplementationOnce(() => new Promise((resolve) => {
        resolveSecondRequest = resolve;
      }));

    render(
      <SynastryModal
        open
        onClose={vi.fn()}
        snaps={snaps}
        activeSnapId="snap-a"
      />
    );

    expect(await screen.findByText('Relationship Signature')).toBeInTheDocument();
    expect(screen.getByText('Binding with real staying power')).toBeInTheDocument();
    expect(screen.getByText('Astro Clock / Synastry')).toBeInTheDocument();
    expect(screen.getByText('Verdict')).toBeInTheDocument();
    expect(screen.queryByText('Source doctrine')).not.toBeInTheDocument();
    expect(screen.queryByText('Core compatibility source')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('checkbox', { name: 'Chiron' }));

    await waitFor(() => {
      expect(astroClockApiMock.getSynastry).toHaveBeenCalledTimes(2);
    });

    expect(screen.getByText('Relationship Signature')).toBeInTheDocument();
    expect(screen.getByText('Binding with real staying power')).toBeInTheDocument();
    expect(screen.getByText('Refreshing report')).toBeInTheDocument();
    expect(screen.queryByText('Comparing snaps...')).not.toBeInTheDocument();
    expect(astroClockApiMock.getSynastry.mock.calls[1][0]).toMatchObject({
      engineId: 'memo',
      includeChiron: true,
    });
    expect(astroClockApiMock.getSynastry.mock.calls[0][0]).not.toHaveProperty('houseSystem');
    expect(astroClockApiMock.getSynastry.mock.calls[1][0]).not.toHaveProperty('houseSystem');

    resolveSecondRequest?.(makeSynastryResponse());

    await waitFor(() => {
      expect(screen.queryByText('Refreshing report')).not.toBeInTheDocument();
    });
  });

  it('requests a fresh report when either selected snap changes', async () => {
    astroClockApiMock.getSynastry
      .mockResolvedValueOnce(makeSynastryResponse())
      .mockResolvedValueOnce(makeSynastryResponse({
        chart_b: { label: 'Gamma' },
        summary: {
          overall_components: {
            compatibility: 42,
            binding: 35,
            growth: 48,
            challenge: 52,
            support_balance: 44,
            reception_bonus: 0,
          },
          supportive_link_count: 0,
          challenging_link_count: 1,
          mutual_reception_count: 0,
          summary_lines: ['The changed pair recalculated.'],
        },
      }));

    render(
      <SynastryModal
        open
        onClose={vi.fn()}
        snaps={snaps}
        activeSnapId="snap-a"
      />
    );

    expect(await screen.findByText('Relationship Signature')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('combobox', { name: 'Snap B' }), {
      target: { value: 'snap-c' },
    });

    await waitFor(() => {
      expect(astroClockApiMock.getSynastry).toHaveBeenCalledTimes(2);
    });

    expect(astroClockApiMock.getSynastry.mock.calls[1][0]).toMatchObject({
      snapAId: 'snap-a',
      snapBId: 'snap-c',
      engineId: 'memo',
    });
    expect(await screen.findByText('The changed pair recalculated.')).toBeInTheDocument();
  });

  it('clears the previous report when the selected snaps are not a valid pair', async () => {
    astroClockApiMock.getSynastry.mockResolvedValueOnce(makeSynastryResponse());

    render(
      <SynastryModal
        open
        onClose={vi.fn()}
        snaps={snaps}
        activeSnapId="snap-a"
      />
    );

    expect(await screen.findByText('Relationship Signature')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('combobox', { name: 'Snap B' }), {
      target: { value: 'snap-a' },
    });

    expect(await screen.findByText('Subject A and Subject B are the same snap.')).toBeInTheDocument();
    expect(screen.queryByText('Relationship Signature')).not.toBeInTheDocument();
    expect(astroClockApiMock.getSynastry).toHaveBeenCalledTimes(1);
  });

  it('requests the selected structured engine when switching tabs', async () => {
    astroClockApiMock.getSynastry
      .mockResolvedValueOnce(makeSynastryResponse())
      .mockResolvedValueOnce(makeSynastryResponse({
        report_kind: 'structured',
        engine_id: 'life_themes',
        engine_label: 'Life Themes',
        summary: {
          theme_total: 18,
          aspect_total: 7,
          burden_total: -3,
          composite_total: 25,
          summary_lines: ['Strongest area: Identity & Presence (+8).'],
        },
        sections: [
          {
            id: 'themes',
            label: 'Themes',
            kind: 'group_breakdown',
            items: [
              {
                id: 'alaspT01',
                label: 'Identity & Presence',
                score: 8,
                row_count: 3,
                positive_count: 2,
                negative_count: 1,
                summary: 'Self-to-theme exchange for house 1.',
                notes: ['Direct psychology pair for house 1.'],
                rows: [
                  {
                    left_label: '☉ Sun',
                    left_meta: 'H1 · Aries',
                    mid_raw: '☉△☽',
                    mid_semantic: 'Sun Trine Moon',
                    logic_type: 'explicit_aspect',
                    right_label: '☽ Moon',
                    right_meta: 'H11 · Leo',
                    score: 4,
                    detail: 'Theme row detail.',
                  },
                ],
              },
            ],
          },
        ],
        areas: {
          label: 'Areas Diagram',
          description: 'Four stripe graphs based on the selected pools.',
          stripes: [
            {
              id: 'subject_a_elements',
              label: 'Chart A thematic elements',
              primary_label: 'Direct',
              secondary_label: 'Role',
              max_value: 4,
              buckets: [
                { id: 'fire', label: 'Fire', glyph: '🜂', primary_value: 4, secondary_value: 2 },
                { id: 'earth', label: 'Earth', glyph: '🜃', primary_value: 1, secondary_value: 1 },
                { id: 'air', label: 'Air', glyph: '🜁', primary_value: 2, secondary_value: 1 },
                { id: 'water', label: 'Water', glyph: '🜄', primary_value: 0, secondary_value: 1 },
              ],
            },
          ],
        },
        governance: {
          point_capability: {
            modern_supported: true,
            chiron_supported: true,
          },
          known_gaps: ['Structured engine note.'],
        },
      }));

    render(
      <SynastryModal
        open
        onClose={vi.fn()}
        snaps={snaps}
        activeSnapId="snap-a"
      />
    );

    expect(await screen.findByText('Relationship Signature')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Life Themes' }));

    await waitFor(() => {
      expect(astroClockApiMock.getSynastry).toHaveBeenCalledTimes(2);
    });

    expect(astroClockApiMock.getSynastry.mock.calls[1][0]).toMatchObject({
      engineId: 'life_themes',
    });
    expect(await screen.findByText('Chart A thematic elements')).toBeInTheDocument();
    expect(screen.getAllByText('Areas Diagram')).toHaveLength(1);
    expect(screen.queryByText('Source doctrine')).not.toBeInTheDocument();
    expect(screen.queryByText('Working notes')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Themes' }));
    expect(await screen.findByText('Theme row detail.')).toBeInTheDocument();
  });

  it('defaults union profiles from snap profile hints when available', async () => {
    astroClockApiMock.getSynastry
      .mockResolvedValueOnce(makeSynastryResponse())
      .mockResolvedValueOnce(makeSynastryResponse({
        report_kind: 'structured',
        engine_id: 'union_dynamics',
        engine_label: 'Union Dynamics',
        summary: {
          theme_total: 12,
          aspect_total: 4,
          burden_total: -3,
          composite_total: 16,
          summary_lines: ['Strongest area: Bond / Psychology (+6).'],
        },
        sections: [
          {
            id: 'bond',
            label: 'Bond',
            kind: 'group_breakdown',
            items: [
              {
                id: 'alasp157P',
                label: 'Bond / Psychology',
                score: 6,
                row_count: 5,
                positive_count: 4,
                negative_count: 1,
                summary: 'Bond psychology layer.',
                notes: ['Bond / Psychology psychology slot 1.'],
                rows: [
                  {
                    left_label: 'Venus',
                    mid_raw: '♀☌♀',
                    mid_semantic: 'Venus Conjunction Venus',
                    logic_type: 'explicit_aspect',
                    right_label: 'Venus',
                    score: 7,
                    detail: 'Bond / Psychology psychology bucket match.',
                    aspect_name: 'Conjunction',
                    orb: 1.17,
                  },
                ],
              },
            ],
          },
        ],
        governance: {
          point_capability: {
            modern_supported: true,
            chiron_supported: true,
          },
          profile_mode: {
            profile_a: 'feminine',
            profile_b: 'masculine',
          },
          known_gaps: [],
        },
      }));

    render(
      <SynastryModal
        open
        onClose={vi.fn()}
        snaps={snaps}
        activeSnapId="snap-a"
      />
    );

    expect(await screen.findByText('Relationship Signature')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Union Dynamics' }));

    await waitFor(() => {
      expect(astroClockApiMock.getSynastry).toHaveBeenCalledTimes(2);
    });

    expect(astroClockApiMock.getSynastry.mock.calls[1][0]).toMatchObject({
      engineId: 'union_dynamics',
      profileA: 'feminine',
      profileB: 'masculine',
    });
    expect(screen.queryByText('Bond / Psychology psychology bucket match.')).not.toBeInTheDocument();
    expect(screen.getByText('Venus Conjunction Venus')).toBeInTheDocument();
  });

  it('renders the work alliance durability check inside the structured verdict', async () => {
    astroClockApiMock.getSynastry
      .mockResolvedValueOnce(makeSynastryResponse())
      .mockResolvedValueOnce(makeSynastryResponse({
        report_kind: 'structured',
        engine_id: 'work_alliance',
        engine_label: 'Work Alliance',
        summary: {
          theme_total: 36,
          aspect_total: 50,
          burden_total: -12,
          composite_total: 86,
          durability_check: {
            id: 'work_durability_v1',
            label: 'durable signal',
            score: 84,
            title: 'Durable collaboration signal',
            body: 'The business-house foundation stays net-positive and the pressure layer is not overwhelming.',
            notes: [
              'The business-house foundation is clearly net-positive.',
              'Shared contact rows are still adding collaborative traction.',
            ],
          },
          summary_lines: ['Durability check: Durable collaboration signal (84/100).'],
        },
        sections: [
          {
            id: 'themes',
            label: 'Themes',
            kind: 'group_breakdown',
            items: [
              {
                id: 'alaspT01',
                label: 'Identity & Presence',
                score: 14,
                row_count: 3,
                positive_count: 2,
                negative_count: 1,
                summary: 'Self-to-theme exchange for house 1.',
                notes: ['Direct psychology pair for house 1.'],
                rows: [
                  {
                    left_label: 'Sun',
                    mid_raw: '☉',
                    logic_type: 'explicit_aspect',
                    right_label: 'Mars',
                    score: 4,
                    detail: 'Theme row detail.',
                  },
                ],
              },
            ],
          },
          {
            id: 'pressure',
            label: 'Pressure',
            kind: 'event_rows',
            items: [],
          },
          {
            id: 'contact_grid',
            label: 'Contact Grid',
            kind: 'event_rows',
            items: [],
          },
        ],
        areas: {
          label: 'Areas Diagram',
          description: 'Four stripe graphs based on the selected pools.',
          stripes: [
            {
              id: 'subject_a_elements',
              label: 'Chart A thematic elements',
              primary_label: 'Direct',
              secondary_label: 'Role',
              max_value: 4,
              buckets: [
                { id: 'fire', label: 'Fire', glyph: '🔥', primary_value: 4, secondary_value: 2 },
                { id: 'earth', label: 'Earth', glyph: '⛰', primary_value: 1, secondary_value: 1 },
                { id: 'air', label: 'Air', glyph: '🜁', primary_value: 2, secondary_value: 1 },
                { id: 'water', label: 'Water', glyph: '🜄', primary_value: 0, secondary_value: 1 },
              ],
            },
          ],
        },
        governance: {
          point_capability: {
            modern_supported: true,
            chiron_supported: true,
          },
          outcome_model: 'work_durability_v1',
          known_gaps: [],
        },
      }));

    render(
      <SynastryModal
        open
        onClose={vi.fn()}
        snaps={snaps}
        activeSnapId="snap-a"
      />
    );

    expect(await screen.findByText('Relationship Signature')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Work Alliance' }));

    await waitFor(() => {
      expect(astroClockApiMock.getSynastry).toHaveBeenCalledTimes(2);
    });

    expect(await screen.findByText('Durability Check')).toBeInTheDocument();
    expect(screen.getByText('Durable collaboration signal')).toBeInTheDocument();
    expect(screen.getByText('Theme Base')).toBeInTheDocument();
    expect(screen.getByText('Contact Layer')).toBeInTheDocument();
    expect(screen.getByText('Pressure Load')).toBeInTheDocument();
    expect(screen.getByText('The business-house foundation is clearly net-positive.')).toBeInTheDocument();
  });
});
