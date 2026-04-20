import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const astroClockApiMock = vi.hoisted(() => ({
  getCompass: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

import CompassTile from '../features/astroclock/CompassTile.jsx';

describe('CompassTile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('derives compass bearings from the live astro clock payload when planets and cusps are present', () => {
    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-04-14T09:43:00Z"
        mode="realtime"
        location="Greenwich, UK"
        houseCusps={[15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345]}
        planets={[
          { planet: 'Sun', longitude: 14 },
          { planet: 'Mercury', longitude: 28 },
          { planet: 'Uranus', longitude: 40 },
        ]}
      />
    );

    expect(screen.getByText('☉')).toBeInTheDocument();
    expect(screen.getByText('☿')).toBeInTheDocument();
    expect(screen.queryByText('♅')).not.toBeInTheDocument();
    expect(astroClockApiMock.getCompass).not.toHaveBeenCalled();
  });

  it('falls back to the compass endpoint when local chart data is unavailable', async () => {
    astroClockApiMock.getCompass.mockResolvedValue({
      success: true,
      data: {
        azimuths: [{ planet: 'Jupiter', azimuth_deg: 90 }],
        ascendant: 0,
      },
    });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-04-14T09:43:00Z"
        mode="realtime"
        location="Greenwich, UK"
      />
    );

    await waitFor(() => {
      expect(astroClockApiMock.getCompass).toHaveBeenCalledWith({ includeModern: false });
    });
    expect(screen.getByText('♃')).toBeInTheDocument();
  });
});
