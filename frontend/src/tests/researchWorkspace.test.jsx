import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const astroClockApiMock = vi.hoisted(() => ({
  listResearchEvaluators: vi.fn(),
  runResearchAnalysis: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

import ResearchWorkspace, { isResearchRowReady, normalizeResearchImportRows } from '../features/research/ResearchWorkspace.jsx';

const evaluatorCatalog = [
  {
    id: 'positions',
    label: 'Positions',
    description: 'Planet placements.',
    default_scopes: ['planet_signs'],
    scopes: [
      { id: 'planet_signs', label: 'Planet signs', description: 'Object signs.' },
      { id: 'elements', label: 'Elements', description: 'Object elements.' },
      { id: 'zodiac_range', label: 'Custom zodiac range', description: 'Object in a sign range.', custom: true },
    ],
  },
  {
    id: 'aspects',
    label: 'Aspects',
    description: 'Natal aspect features.',
    default_scopes: ['planetary_aspects'],
    scopes: [
      { id: 'planetary_aspects', label: 'Planetary aspects', description: 'Planet contacts.' },
    ],
  },
  {
    id: 'points',
    label: 'Symbolic Points',
    description: 'Active point rows.',
    default_scopes: ['active_points'],
    scopes: [
      { id: 'active_points', label: 'Active points', description: 'Active point rows.' },
      { id: 'activation_contacts', label: 'Activation contacts', description: 'Point contacts.' },
    ],
  },
];

describe('ResearchWorkspace', () => {
  beforeEach(() => {
    astroClockApiMock.listResearchEvaluators.mockReset();
    astroClockApiMock.runResearchAnalysis.mockReset();
    astroClockApiMock.listResearchEvaluators.mockResolvedValue({
      success: true,
      data: { families: evaluatorCatalog },
    });
  });

  it('normalizes common bulk chart import headers', () => {
    const rows = normalizeResearchImportRows([
      {
        'Chart Name': 'Subject A',
        'Birth Date': '1990-01-13',
        'Birth Time': '21:33',
        Place: 'Jerusalem, Israel',
        TZ: 'Asia/Jerusalem',
        Lat: '31.778',
        Lng: '35.235',
        Type: 'natal',
      },
    ]);

    expect(rows).toEqual([
      expect.objectContaining({
        name: 'Subject A',
        date: '1990-01-13',
        time: '21:33',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        latitude: '31.778',
        longitude: '35.235',
        chart_type: 'natal',
      }),
    ]);
  });

  it('marks chart rows ready only when date/time and place or coordinate pair are present', () => {
    expect(isResearchRowReady({
      date: '1990-01-13',
      time: '21:33',
      location: 'Jerusalem, Israel',
    })).toBe(true);
    expect(isResearchRowReady({
      datetime: '1990-01-13T21:33:00',
      latitude: '31.778',
      longitude: '35.235',
    })).toBe(true);
    expect(isResearchRowReady({
      datetime: '1990-01-13T21:33:00',
      latitude: '31.778',
    })).toBe(false);
    expect(isResearchRowReady({
      date: '1990-01-13',
      location: 'Jerusalem, Israel',
    })).toBe(false);
  });

  it('runs a selected feature list against a sample chart set', async () => {
    astroClockApiMock.runResearchAnalysis.mockResolvedValueOnce({
      success: true,
      data: {
        manifest: {
          generated_control_count: 6,
        },
        statistics: {
          signal_count: 1,
        },
        signals: [
          {
            key: 'positions:sun:aries',
            label: 'Sun in Aries',
            family: 'positions',
            target_count: 2,
            target_total: 3,
            target_rate: 0.6667,
            control_count: 1,
            control_total: 6,
            control_rate: 0.1667,
            lift: 4,
            p_value: 0.0321,
            q_value: 0.0482,
            effect_direction: 'more_common',
            warnings: ['small_target_sample'],
          },
        ],
      },
    });

    render(<ResearchWorkspace />);

    await screen.findByRole('tab', { name: /Positions/ });
    fireEvent.click(screen.getByRole('button', { name: 'Load Sample' }));
    expect(screen.getByText('Sample A')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'None' }));
    fireEvent.click(screen.getByRole('tab', { name: /Positions/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Add Planet signs' }));
    fireEvent.change(screen.getByLabelText('Controls per chart'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Year window'), { target: { value: '5' } });
    fireEvent.change(screen.getByLabelText('Seed'), { target: { value: 'fixed-seed' } });
    fireEvent.change(screen.getByLabelText('House system'), { target: { value: 'R' } });
    fireEvent.click(screen.getByRole('button', { name: 'Run Analysis' }));

    await waitFor(() => expect(astroClockApiMock.runResearchAnalysis).toHaveBeenCalledTimes(1));
    expect(astroClockApiMock.runResearchAnalysis).toHaveBeenCalledWith(expect.objectContaining({
      evaluator_families: ['positions'],
      feature_scopes: [
        { family: 'positions', preset: 'planet_signs' },
      ],
      house_system_code: 'R',
      control: expect.objectContaining({
        strategy: 'matched_generated',
        per_chart: 2,
        year_window: 5,
        seed: 'fixed-seed',
      }),
    }));

    const results = screen.getByText('Ranked Signals').closest('section');
    expect(within(results).getByText('Sun in Aries')).toBeTruthy();
    expect(within(results).getByText('2/3 (66.7%)')).toBeTruthy();
    expect(within(results).getByText('1/6 (16.7%)')).toBeTruthy();
    expect(within(results).getByText('small target sample')).toBeTruthy();
  });

  it('adds multiple custom zodiac ranges and sends each one explicitly', async () => {
    astroClockApiMock.runResearchAnalysis.mockResolvedValueOnce({
      success: true,
      data: {
        manifest: { generated_control_count: 2 },
        statistics: { signal_count: 0 },
        signals: [],
      },
    });

    render(<ResearchWorkspace />);

    await screen.findByRole('tab', { name: /Positions/ });
    fireEvent.click(screen.getByRole('button', { name: 'Load Sample' }));
    fireEvent.click(screen.getByRole('button', { name: 'None' }));
    fireEvent.click(screen.getByRole('tab', { name: /Positions/ }));
    fireEvent.change(screen.getByLabelText('Range object'), { target: { value: 'Sun' } });
    fireEvent.change(screen.getByLabelText('Range sign'), { target: { value: 'Aries' } });
    fireEvent.change(screen.getByLabelText('Start degree'), { target: { value: '5' } });
    fireEvent.change(screen.getByLabelText('End degree'), { target: { value: '10' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add range' }));
    fireEvent.change(screen.getByLabelText('Range object'), { target: { value: 'Moon' } });
    fireEvent.change(screen.getByLabelText('Range sign'), { target: { value: 'Taurus' } });
    fireEvent.change(screen.getByLabelText('Start degree'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('End degree'), { target: { value: '10' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add range' }));

    expect(screen.getByText('Sun in Aries 5-10')).toBeTruthy();
    expect(screen.getByText('Moon in Taurus 4-10')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Run Analysis' }));

    await waitFor(() => expect(astroClockApiMock.runResearchAnalysis).toHaveBeenCalledTimes(1));
    expect(astroClockApiMock.runResearchAnalysis).toHaveBeenCalledWith(expect.objectContaining({
      evaluator_families: ['positions'],
      feature_scopes: [
        {
          family: 'positions',
          kind: 'zodiac_range',
          object: 'Sun',
          sign: 'Aries',
          start_degree: 5,
          end_degree: 10,
        },
        {
          family: 'positions',
          kind: 'zodiac_range',
          object: 'Moon',
          sign: 'Taurus',
          start_degree: 4,
          end_degree: 10,
        },
      ],
    }));
  });

  it('uses tabs so every feature family can add presets into the selected list', async () => {
    astroClockApiMock.runResearchAnalysis.mockResolvedValueOnce({
      success: true,
      data: {
        manifest: { generated_control_count: 2 },
        statistics: { signal_count: 0 },
        signals: [],
      },
    });

    render(<ResearchWorkspace />);

    await screen.findByRole('tab', { name: /Positions/ });
    fireEvent.click(screen.getByRole('button', { name: 'Load Sample' }));
    fireEvent.click(screen.getByRole('button', { name: 'None' }));
    fireEvent.click(screen.getByRole('tab', { name: /Symbolic Points/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Add Activation contacts' }));
    expect(screen.getByText('Symbolic Points: Activation contacts')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Run Analysis' }));

    await waitFor(() => expect(astroClockApiMock.runResearchAnalysis).toHaveBeenCalledTimes(1));
    expect(astroClockApiMock.runResearchAnalysis).toHaveBeenCalledWith(expect.objectContaining({
      evaluator_families: ['points'],
      feature_scopes: [
        { family: 'points', preset: 'activation_contacts' },
      ],
    }));
  });

  it('falls back to default scopes when catalog metadata is not available yet', async () => {
    astroClockApiMock.listResearchEvaluators.mockResolvedValueOnce({
      success: true,
      data: {
        families: [
          { id: 'positions', label: 'Positions', description: 'Planet placements.' },
        ],
      },
    });
    astroClockApiMock.runResearchAnalysis.mockResolvedValueOnce({
      success: true,
      data: {
        manifest: { generated_control_count: 2 },
        statistics: { signal_count: 0 },
        signals: [],
      },
    });

    render(<ResearchWorkspace />);

    await screen.findByRole('tab', { name: /Positions/ });
    fireEvent.click(screen.getByRole('button', { name: 'Load Sample' }));
    fireEvent.click(screen.getByRole('button', { name: 'Run Analysis' }));

    await waitFor(() => expect(astroClockApiMock.runResearchAnalysis).toHaveBeenCalledTimes(1));
    expect(astroClockApiMock.runResearchAnalysis).toHaveBeenCalledWith(expect.objectContaining({
      evaluator_families: ['positions'],
      feature_scopes: [
        { family: 'positions', preset: 'planet_signs' },
      ],
    }));
  });
});
