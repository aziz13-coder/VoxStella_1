import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

const astroClockApiMock = vi.hoisted(() => ({
  getDashboard: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

import AspectAnalysisModal from '../features/astroclock/AspectAnalysisModal.jsx';

describe('AspectAnalysisModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    astroClockApiMock.getDashboard.mockResolvedValue({
      success: true,
      data: {
        planets: [],
        planetary_aspects_precise: [],
        morin_aspects: [],
        top_declinations: [],
        cusp_aspects: {},
        morin_antiscia: [],
        morin_contra_antiscia: [],
        morin_combustion: [],
        morin_patterns: {},
      },
    });
  });

  it('reuses the provided AstroClock snapshot without refetching and keeps the normalized orb label', async () => {
    render(
      <AspectAnalysisModal
        open
        onClose={() => {}}
        specialDegrees={[]}
        useMorin={false}
        includeModern={false}
        dashboardData={{
          planets: [],
          planetary_aspects_precise: [
            {
              planet1: 'Moon',
              planet2: 'Saturn',
              aspect: 'Conjunction',
              orb: 0.67,
              orb_text: '0.7°',
              max_orb: 8,
              symbol: '☌',
            },
          ],
          morin_aspects: [],
          top_declinations: [],
          cusp_aspects: {},
          morin_antiscia: [],
          morin_contra_antiscia: [],
          morin_combustion: [],
          morin_patterns: {},
        }}
      />
    );

    expect(await screen.findByText('Planetary Aspects')).toBeInTheDocument();
    expect(screen.getByText(/orb 0.7° \/ max 8.00°/)).toBeInTheDocument();
    expect(astroClockApiMock.getDashboard).not.toHaveBeenCalled();
  });

  it('renders the normalized cusp section label and search placeholder', async () => {
    render(
      <AspectAnalysisModal
        open
        onClose={() => {}}
        specialDegrees={[]}
        useMorin={false}
        includeModern={false}
        dashboardData={{
          planets: [],
          planetary_aspects_precise: [],
          morin_aspects: [],
          top_declinations: [],
          cusp_aspects: {
            H1: [
              { planet: 'Mars', aspect: 'Conjunction', orb: 0.4, phase: 'applying' },
            ],
          },
          morin_antiscia: [],
          morin_contra_antiscia: [],
          morin_combustion: [],
          morin_patterns: {},
        }}
      />
    );

    expect(await screen.findByText('Cusp Aspects (≤1°)')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search planet…')).toBeInTheDocument();
  });
});
