import React from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const getReceptions = vi.fn();

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: {
    getReceptions: (...args) => getReceptions(...args),
  },
}));

import ReceptionsTile from '../features/astroclock/ReceptionsTile.jsx';

describe('ReceptionsTile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a no reception summary when the endpoint summary is none', async () => {
    getReceptions.mockResolvedValueOnce({
      success: true,
      data: {
        traditional_reception: {
          type: 'none',
          display_text: 'No reception',
          mutual_count: 0,
          unilateral_count: 0,
        },
        mutual: [],
        top_unilateral: [],
      },
    });

    render(<ReceptionsTile dataTimestamp="2026-03-21T00:00:00Z" />);

    expect(await screen.findByText('No reception')).toBeInTheDocument();
    expect(screen.getByText('Mutual')).toBeInTheDocument();
    expect(screen.getByText('Unilateral')).toBeInTheDocument();
  });

  it('shows a mixed reception summary with matching counts', async () => {
    getReceptions.mockResolvedValueOnce({
      success: true,
      data: {
        traditional_reception: {
          type: 'mixed_reception',
          display_text: 'Mixed reception',
          mutual_count: 1,
          unilateral_count: 2,
        },
        mutual: [
          { p1: 'Venus', p2: 'Mars', type: 'mixed_reception', strength: 5 },
        ],
        top_unilateral: [
          { receiving: 'Jupiter', received: 'Mars', dignities: ['domicile'], strength: 5 },
          { receiving: 'Moon', received: 'Venus', dignities: ['domicile'], strength: 5 },
        ],
      },
    });

    render(<ReceptionsTile dataTimestamp="2026-03-21T00:00:00Z" />);

    expect((await screen.findAllByText('Mixed reception')).length).toBeGreaterThan(0);
    expect(
      screen.getByText((content) => content.includes('1') && content.includes('mutual') && content.includes('2') && content.includes('unilateral'))
    ).toBeInTheDocument();
    expect(screen.getByText('Mutual')).toBeInTheDocument();
    expect(screen.getByText('Unilateral')).toBeInTheDocument();
  });

  it('passes chart context to the fallback endpoint', async () => {
    getReceptions.mockResolvedValueOnce({
      success: true,
      data: {
        traditional_reception: {
          type: 'none',
          display_text: 'No reception',
          mutual_count: 0,
          unilateral_count: 0,
        },
        mutual: [],
        top_unilateral: [],
      },
    });

    const clockContext = {
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    };

    render(<ReceptionsTile dataTimestamp="2026-03-21T00:00:00Z" clockContext={clockContext} />);

    expect(await screen.findByText('No reception')).toBeInTheDocument();
    expect(getReceptions).toHaveBeenCalledWith(clockContext);
  });

  it('prefers chart-scoped receptions data over the fallback endpoint', async () => {
    render(
      <ReceptionsTile
        dataTimestamp="2026-03-21T00:00:00Z"
        receptions={{
          traditional_reception: {
            type: 'mixed_reception',
            display_text: 'Mixed reception',
            mutual_count: 4,
            unilateral_count: 8,
          },
          mutual: [
            { p1: 'Venus', p2: 'Mars', type: 'mixed_reception', strength: 5 },
          ],
          top_unilateral: [
            { receiving: 'Mars', received: 'Jupiter', dignities: ['domicile'], strength: 5 },
          ],
        }}
      />
    );

    expect((await screen.findAllByText('Mixed reception')).length).toBeGreaterThan(0);
    expect(
      screen.getByText((content) => content.includes('4 mutual') && content.includes('8 unilateral'))
    ).toBeInTheDocument();
    expect(getReceptions).not.toHaveBeenCalled();
  });
});
