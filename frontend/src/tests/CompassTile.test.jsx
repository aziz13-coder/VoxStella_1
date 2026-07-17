import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';

const astroClockApiMock = vi.hoisted(() => ({
  getCompass: vi.fn(),
  getDirectional3d: vi.fn(),
  getSnap: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

import CompassTile from '../features/astroclock/CompassTile.jsx';

describe('CompassTile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('stays empty when chart coordinates are missing', () => {
    render(
      <CompassTile
        includeModern={false}
        houseCusps={[15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345]}
      />
    );

    expect(screen.getByText('Set a chart location to render local-space bearings.')).toBeInTheDocument();
    expect(astroClockApiMock.getCompass).not.toHaveBeenCalled();
  });

  it('requests real compass bearings with the active Astro Clock context', async () => {
    astroClockApiMock.getCompass.mockResolvedValue({
      success: true,
      data: {
        azimuths: [{ planet: 'Jupiter', azimuth_deg: 90, altitude_deg: 34.2, longitude_deg: 123.0 }],
        ascendant: 0,
        source: 'local_space',
        has_altitude: true,
      },
    });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-04-14T09:43:00Z"
        mode="realtime"
        location="Greenwich, UK"
        timezone="Europe/London"
        latitude={51.4769}
        longitude={-0.0005}
        houseSystem="R"
        houseCusps={[15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345]}
      />
    );

    await waitFor(() => {
      expect(astroClockApiMock.getCompass).toHaveBeenCalledWith({
        includeModern: false,
        mode: 'realtime',
        datetime: '2026-04-14T09:43:00Z',
        location: 'Greenwich, UK',
        timezone: 'Europe/London',
        latitude: 51.4769,
        longitude: -0.0005,
        houseSystem: 'R',
      });
    });
    expect(screen.getByText('\u2643')).toBeInTheDocument();
    expect(screen.getByText('Directional')).toBeInTheDocument();
    expect(screen.queryByText('Compass Bearings')).not.toBeInTheDocument();
    expect(screen.getByText('Rising')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Alt' })).toHaveClass('bg-zinc-900');
    expect(screen.getByRole('button', { name: 'Alt' })).toBeEnabled();
  });

  it('renders dashboard-provided compass data without a follow-up fetch', () => {
    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-04-14T09:43:00Z"
        mode="realtime"
        location="Greenwich, UK"
        timezone="Europe/London"
        latitude={51.4769}
        longitude={-0.0005}
        houseSystem="R"
        initialData={{
          azimuths: [{ planet: 'Sun', azimuth_deg: 182.1, altitude_deg: 16.4, longitude_deg: 24.3 }],
          ascendant: 0,
          source: 'local_space',
          has_altitude: true,
        }}
        houseCusps={[15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345]}
      />
    );

    expect(astroClockApiMock.getCompass).not.toHaveBeenCalled();
    expect(screen.getByText('\u2609')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Alt' })).toHaveClass('bg-zinc-900');
    expect(screen.getByRole('button', { name: 'Alt' })).toBeEnabled();
  });

  it('upgrades a flat seeded payload with remote altitude data and restores the dome view', async () => {
    astroClockApiMock.getCompass.mockResolvedValue({
      success: true,
      data: {
        azimuths: [{ planet: 'Moon', azimuth_deg: 182.1, altitude_deg: 22.4, longitude_deg: 144.3 }],
        ascendant: 0,
        source: 'local_space',
        has_altitude: true,
      },
    });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-04-14T09:43:00Z"
        mode="realtime"
        location="Greenwich, UK"
        timezone="Europe/London"
        latitude={51.4769}
        longitude={-0.0005}
        houseSystem="R"
        initialData={{
          azimuths: [{ planet: 'Moon', azimuth_deg: 182.1, longitude_deg: 144.3 }],
          ascendant: 0,
          source: 'legacy_dashboard',
          has_altitude: false,
        }}
        houseCusps={[15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345]}
      />
    );

    await waitFor(() => {
      expect(astroClockApiMock.getCompass).toHaveBeenCalledTimes(1);
      expect(screen.getByRole('button', { name: 'Alt' })).toHaveClass('bg-zinc-900');
      expect(screen.getByRole('button', { name: 'Alt' })).toBeEnabled();
    });
  });

  it('requests bearings when Astro Clock has a location even before explicit coordinates are surfaced', async () => {
    astroClockApiMock.getCompass.mockResolvedValue({
      success: true,
      data: {
        azimuths: [{ planet: 'Mars', azimuth_deg: 120.5, longitude_deg: 12.4 }],
        ascendant: 0,
        source: 'local_space',
        has_altitude: false,
      },
    });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-04-20T01:44:00Z"
        mode="realtime"
        location="London, UK"
        timezone="Europe/London"
        houseSystem="R"
        houseCusps={[15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345]}
      />
    );

    await waitFor(() => {
      expect(astroClockApiMock.getCompass).toHaveBeenCalledWith({
        includeModern: false,
        mode: 'realtime',
        datetime: '2026-04-20T01:44:00Z',
        location: 'London, UK',
        timezone: 'Europe/London',
        latitude: undefined,
        longitude: undefined,
        houseSystem: 'R',
      });
    });
    expect(screen.getByText('\u2642')).toBeInTheDocument();
  });

  it('keeps the azimuth view free of the old altitude ring labels', async () => {
    astroClockApiMock.getCompass.mockResolvedValue({
      success: true,
      data: {
        azimuths: [{ planet: 'Venus', azimuth_deg: 270, altitude_deg: 12.1, longitude_deg: 88.5 }],
        ascendant: 0,
        source: 'local_space',
        has_altitude: true,
      },
    });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-04-14T09:43:00Z"
        mode="realtime"
        location="Greenwich, UK"
        timezone="Europe/London"
        latitude={51.4769}
        longitude={-0.0005}
        houseSystem="R"
        houseCusps={[15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345]}
      />
    );

    await waitFor(() => {
      expect(astroClockApiMock.getCompass).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole('button', { name: 'Az' }));

    expect(screen.queryByText('H')).not.toBeInTheDocument();
  });

  it('opens Directional 3D with the active chart context', async () => {
    astroClockApiMock.getDirectional3d.mockResolvedValueOnce({
      success: true,
      data: {
        systems: ['EQL', 'EQU', 'HOR'],
        chart_info: {
          utc_datetime: '2026-03-22T04:32:00+00:00',
          latitude: 31.778,
          longitude: 35.235,
          rotation: 9,
          tilt: 19,
          house_system: 'R',
        },
        objects: [
          {
            object_id: 'planet:Sun',
            name: 'Sun',
            symbol: '\u2609',
            buse: true,
            bfull: true,
            EQL: { longitude: 1.5, latitude: 0.1, speed: 0.98 },
            EQU: { longitude: 1.4, latitude: 0.7, speed: 1.097, latitude_speed: -0.121 },
            HOR: { longitude: 88.1, latitude: 12.4, speed: 312.456, latitude_speed: -148.123 },
            coordinate_meta: {
              EQL: { source: 'chart_ecliptic', speed_source: 'native' },
              EQU: { source: 'derived_from_ecliptic', speed_source: 'derived', latitude_speed_source: 'derived' },
              HOR: { source: 'swisseph_azalt', speed_source: 'finite_difference', latitude_speed_source: 'finite_difference' },
            },
          },
          {
            object_id: 'planet:Moon',
            name: 'Moon',
            symbol: '\u263D',
            buse: true,
            bfull: true,
            EQL: { longitude: 45.0, latitude: 3.2, speed: 13.4 },
            EQU: { longitude: 46.1, latitude: 19.2, speed: 12.9, latitude_speed: null },
            HOR: { longitude: 270.2, latitude: -5.1, speed: 0 },
            coordinate_meta: {
              EQL: { source: 'chart_ecliptic', speed_source: 'native' },
              EQU: { source: 'chart_equatorial', speed_source: 'native', latitude_speed_source: 'unavailable' },
              HOR: { source: 'swisseph_azalt', speed_source: 'static_zero' },
            },
          },
          {
            object_id: 'planet:Mars',
            name: 'Mars',
            symbol: '\u2642',
            buse: true,
            bfull: true,
            EQL: { longitude: 120.0, latitude: 1.2, speed: 0.72 },
            EQU: { longitude: 122.1, latitude: 21.4, speed: 0.68, latitude_speed: null },
            HOR: { longitude: 186.2, latitude: 22.1, speed: 0 },
          },
          {
            object_id: 'planet:Saturn',
            name: 'Saturn',
            symbol: '\u2644',
            buse: true,
            bfull: true,
            EQL: { longitude: 301.2, latitude: -2.1, speed: -0.03 },
            EQU: { longitude: 303.4, latitude: -21.7, speed: -0.02, latitude_speed: null },
            HOR: { longitude: 42.4, latitude: -16.2, speed: 0 },
          },
          {
            object_id: 'cusp:1',
            name: 'House 1',
            symbol: 'H1',
            object_type: 'cusp',
            buse: true,
            bfull: false,
            EQL: { longitude: 18, latitude: 0, speed: 0 },
            EQU: { longitude: 18, latitude: 0, speed: 0 },
            HOR: { longitude: 83.5, latitude: 0, speed: 0 },
          },
          {
            object_id: 'cusp:7',
            name: 'House 7',
            symbol: 'H7',
            object_type: 'cusp',
            buse: true,
            bfull: false,
            EQL: { longitude: 198, latitude: 0, speed: 0 },
            EQU: { longitude: 198, latitude: 0, speed: 0 },
            HOR: { longitude: 263.5, latitude: 0, speed: 0 },
          },
        ],
      },
    });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-03-22T04:32:00Z"
        mode="manual"
        location="Israel"
        timezone="Asia/Jerusalem"
        latitude={31.778}
        longitude={35.235}
        houseSystem="R"
        initialData={{
          azimuths: [{ planet: 'Sun', azimuth_deg: 88.1, altitude_deg: 12.4, longitude_deg: 1.5 }],
          ascendant: 18,
          source: 'local_space',
          has_altitude: true,
        }}
        houseCusps={[18, 44, 71, 99, 130, 159, 198, 224, 251, 279, 310, 339]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledWith({
        includeModern: false,
        mode: 'manual',
        datetime: '2026-03-22T04:32:00Z',
        location: 'Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 31.778,
        longitude: 35.235,
        houseSystem: 'R',
      });
    });
    expect(await screen.findByText('Directional 3D')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'EQL' })).toHaveClass('bg-zinc-900');
    const chart = screen.getByRole('img', { name: 'Directional 3D chart' });
    expect(chart).toBeInTheDocument();
    expect(chart.querySelectorAll('g[role="button"] circle')).toHaveLength(0);
    const selectedSunGlyph = chart.querySelector('[data-directional-selected-object="planet:Sun"]');
    expect(selectedSunGlyph).toBeTruthy();
    expect(selectedSunGlyph).toHaveAttribute('filter', 'url(#directional-selected-glow)');
    expect(selectedSunGlyph).toHaveAttribute('stroke', 'none');
    expect(selectedSunGlyph.closest('g')).toHaveStyle({ outline: 'none' });
    expect(chart.querySelectorAll('[data-directional-selected-frame]')).toHaveLength(0);
    expect(chart.querySelectorAll('[data-directional-house-boundary]')).toHaveLength(2);
    expect(screen.getByRole('button', { name: 'Ecliptic' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Equator' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Horizon' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tropics' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Polar' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back half' })).toBeInTheDocument();
    expect(chart.querySelectorAll('[data-directional-reference="tropic"]')).toHaveLength(2);
    expect(chart.querySelectorAll('[data-directional-reference="polar"]')).toHaveLength(2);
    fireEvent.click(screen.getByRole('button', { name: 'Tropics' }));
    expect(chart.querySelectorAll('[data-directional-reference="tropic"]')).toHaveLength(0);
    const inspector = document.querySelector('[data-directional-inspector]');
    expect(inspector).toBeTruthy();
    expect(within(inspector).getByText('Selected object')).toBeInTheDocument();
    expect(within(inspector).queryByText('Selected: Sun')).not.toBeInTheDocument();
    expect(inspector.querySelectorAll('[data-directional-coordinate-panel]')).toHaveLength(3);
    expect(inspector.querySelector('[data-directional-coordinate-panel="HOR"]')).toBeTruthy();
    expect(within(inspector).getByText('Az')).toBeInTheDocument();
    expect(within(inspector).getByText('Alt')).toBeInTheDocument();
    expect(inspector.querySelector('[data-directional-source-badge]')).toBeNull();
    expect(within(inspector).queryByText('Speed source')).not.toBeInTheDocument();
    expect(within(inspector).queryByText('Lat source')).not.toBeInTheDocument();
    expect(within(inspector).queryByText('finite_difference')).not.toBeInTheDocument();
    expect(within(inspector).getByText('Sun')).toBeInTheDocument();
    expect(screen.getByText('Lat speed -0.121')).toBeInTheDocument();
    expect(screen.getByText('Speed 312.456')).toBeInTheDocument();
    expect(screen.getByText('Lat speed -148.123')).toBeInTheDocument();
    expect(screen.getAllByText('Sun').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Moon').length).toBeGreaterThan(0);
    const houseRow = screen.getByRole('row', { name: /House 1/ });
    expect(within(houseRow).getByText('House 1')).toBeInTheDocument();
    expect(within(houseRow).queryByText('H1')).not.toBeInTheDocument();
    fireEvent.click(within(houseRow).getByRole('button', { name: 'House 1' }));
    const selectedHouseLabel = chart.querySelector('[data-directional-selected-object="cusp:1"]');
    expect(selectedHouseLabel).toBeTruthy();
    expect(selectedHouseLabel).toHaveAttribute('stroke', 'none');
    expect(selectedHouseLabel.closest('g')).toHaveStyle({ outline: 'none' });
    expect(chart.querySelector('[aria-label="House 1 EQL"] path')).toBeNull();
    const sunRow = screen.getByRole('row', { name: /Sun/ });
    expect(within(sunRow).getByText('\u2609')).toBeInTheDocument();
    const marsRow = screen.getByRole('row', { name: /Mars/ });
    fireEvent.click(within(marsRow).getByRole('button', { name: /\u2642\s*Mars/ }));
    const selectedMarsGlyph = chart.querySelector('[data-directional-selected-object="planet:Mars"]');
    expect(selectedMarsGlyph).toHaveAttribute('fill', '#ef4444');
    expect(selectedMarsGlyph).toHaveAttribute('color', '#ef4444');
    const saturnRow = screen.getByRole('row', { name: /Saturn/ });
    fireEvent.click(within(saturnRow).getByRole('button', { name: /\u2644\s*Saturn/ }));
    const selectedSaturnGlyph = chart.querySelector('[data-directional-selected-object="planet:Saturn"]');
    expect(selectedSaturnGlyph).toHaveAttribute('fill', '#27272a');
    expect(selectedSaturnGlyph).toHaveAttribute('color', '#27272a');
  });

  it('routes locked Directional 3D clicks through the premium gate', async () => {
    const onLocked = vi.fn();

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-03-22T04:32:00Z"
        mode="manual"
        location="Israel"
        timezone="Asia/Jerusalem"
        latitude={31.778}
        longitude={35.235}
        houseSystem="R"
        initialData={{
          azimuths: [{ planet: 'Sun', azimuth_deg: 88.1, altitude_deg: 12.4, longitude_deg: 1.5 }],
          ascendant: 18,
          source: 'local_space',
          has_altitude: true,
        }}
        houseCusps={[18, 44, 71, 99, 130, 159, 198, 224, 251, 279, 310, 339]}
        directional3dLocked
        onDirectional3dLocked={onLocked}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));

    expect(onLocked).toHaveBeenCalledTimes(1);
    expect(astroClockApiMock.getDirectional3d).not.toHaveBeenCalled();
    expect(screen.queryByText('Directional 3D')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '3D' })).toHaveClass('bg-red-600');
  });

  it('steps Directional 3D time and coordinates through the chart context', async () => {
    const makeData = (overrides = {}) => ({
      systems: ['EQL', 'EQU', 'HOR'],
      chart_info: {
        utc_datetime: '2026-03-22T04:32:00+00:00',
        latitude: 31.778,
        longitude: 35.235,
        rotation: 9,
        tilt: 19,
        house_system: 'R',
        ...overrides.chart_info,
      },
      objects: [
        {
          object_id: 'planet:Sun',
          name: 'Sun',
          symbol: '\u2609',
          buse: true,
          bfull: true,
          EQL: { longitude: 1.5, latitude: 0.1, speed: 0.98 },
          EQU: { longitude: 1.4, latitude: 0.7, speed: 0.98 },
          HOR: { longitude: 88.1, latitude: 12.4, speed: 0 },
        },
      ],
    });
    astroClockApiMock.getDirectional3d
      .mockResolvedValueOnce({ success: true, data: makeData() })
      .mockResolvedValueOnce({
        success: true,
        data: makeData({
          chart_info: {
            utc_datetime: '2026-03-22T05:32:00+00:00',
            latitude: 31.778,
            longitude: 35.235,
          },
        }),
      })
      .mockResolvedValueOnce({
        success: true,
        data: makeData({
          chart_info: {
            utc_datetime: '2026-03-22T05:32:00+00:00',
            latitude: 32.778,
            longitude: 35.235,
          },
        }),
      });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-03-22T04:32:00Z"
        mode="manual"
        location="Israel"
        timezone="Asia/Jerusalem"
        latitude={31.778}
        longitude={35.235}
        houseSystem="R"
        initialData={{
          azimuths: [{ planet: 'Sun', azimuth_deg: 88.1, altitude_deg: 12.4, longitude_deg: 1.5 }],
          ascendant: 18,
          source: 'local_space',
          has_altitude: true,
        }}
        houseCusps={[18, 44, 71, 99, 130, 159, 198, 224, 251, 279, 310, 339]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));
    expect(await screen.findByText('Directional 3D')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Time +1h' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledTimes(2);
    });
    expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith({
      includeModern: false,
      mode: 'manual',
      datetime: '2026-03-22T05:32:00.000Z',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Latitude +1 deg' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledTimes(3);
    });
    expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith({
      includeModern: false,
      mode: 'manual',
      datetime: '2026-03-22T05:32:00.000Z',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 32.778,
      longitude: 35.235,
      houseSystem: 'R',
    });
  });

  it('uses realtime context without datetime when Current Auto is selected after a saved snap', async () => {
    astroClockApiMock.getDirectional3d
      .mockResolvedValueOnce({
        success: true,
        data: {
          systems: ['EQL', 'EQU', 'HOR'],
          chart_info: {
            utc_datetime: '2026-05-18T15:40:00+00:00',
            latitude: 51.4769,
            longitude: -0.0005,
            rotation: 9,
            tilt: 19,
            house_system: 'R',
          },
          objects: [
            {
              object_id: 'planet:Sun',
              name: 'Sun',
              symbol: '\u2609',
              buse: true,
              bfull: true,
              EQL: { longitude: 57.8, latitude: 0, speed: 0.96 },
              EQU: { longitude: 55.4, latitude: 19.6, speed: 0.96 },
              HOR: { longitude: 74.8, latitude: 36.6, speed: 0 },
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          systems: ['EQL', 'EQU', 'HOR'],
          chart_info: {
            utc_datetime: '1990-01-13T19:33:00+00:00',
            latitude: 31.777779,
            longitude: 35.235001,
            rotation: 9,
            tilt: 19,
            house_system: 'T',
          },
          objects: [
            {
              object_id: 'planet:Moon',
              name: 'Moon',
              symbol: '\u263D',
              buse: true,
              bfull: true,
              EQL: { longitude: 145.9, latitude: -0.8, speed: 13.0 },
              EQU: { longitude: 147.9, latitude: 12.0, speed: 13.0 },
              HOR: { longitude: 91.8, latitude: 26.2, speed: 0 },
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          systems: ['EQL', 'EQU', 'HOR'],
          chart_info: {
            utc_datetime: '2026-05-18T15:41:00+00:00',
            latitude: 51.4769,
            longitude: -0.0005,
            rotation: 9,
            tilt: 19,
            house_system: 'R',
          },
          objects: [
            {
              object_id: 'planet:Sun',
              name: 'Sun',
              symbol: '\u2609',
              buse: true,
              bfull: true,
              EQL: { longitude: 57.9, latitude: 0, speed: 0.96 },
              EQU: { longitude: 55.5, latitude: 19.7, speed: 0.96 },
              HOR: { longitude: 75.1, latitude: 36.8, speed: 0 },
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          systems: ['EQL', 'EQU', 'HOR'],
          chart_info: {
            utc_datetime: '2026-05-18T16:41:00+00:00',
            latitude: 51.4769,
            longitude: -0.0005,
            rotation: 9,
            tilt: 19,
            house_system: 'R',
          },
          objects: [
            {
              object_id: 'planet:Sun',
              name: 'Sun',
              symbol: '\u2609',
              buse: true,
              bfull: true,
              EQL: { longitude: 58.8, latitude: 0, speed: 0.96 },
              EQU: { longitude: 56.5, latitude: 19.8, speed: 0.96 },
              HOR: { longitude: 89.1, latitude: 31.8, speed: 0 },
            },
          ],
        },
      });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-05-18T15:40:00Z"
        mode="realtime"
        location="Greenwich, UK"
        timezone="Europe/London"
        latitude={51.4769}
        longitude={-0.0005}
        houseSystem="R"
        initialData={{
          azimuths: [{ planet: 'Sun', azimuth_deg: 74.8, altitude_deg: 36.6, longitude_deg: 57.8 }],
          ascendant: 194,
          source: 'local_space',
          has_altitude: true,
        }}
        houseCusps={[194, 220, 246, 278, 310, 340, 14, 40, 66, 98, 130, 160]}
        snaps={[
          {
            id: 'snap-aziz',
            label: 'Aziz natal snap',
            effective_datetime: '1990-01-13T19:33:00+00:00',
            location: 'Jerusalem, Israel',
            timezone: 'Asia/Jerusalem',
            latitude: 31.777779,
            longitude: 35.235001,
            dashboard: { house_system_code: 'T' },
          },
        ]}
        activeSnapId="snap-aziz"
        loadingSnaps={false}
        snapsLoaded
        onRefreshSnaps={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));
    expect(await screen.findByText('Directional 3D')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Saved Snap' }));
    fireEvent.change(screen.getByLabelText('Directional saved snap'), {
      target: { value: 'snap-aziz' },
    });
    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '1990-01-13T19:33:00+00:00',
        location: 'Jerusalem, Israel',
      }));
    });

    fireEvent.click(screen.getByRole('button', { name: 'Current Auto' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith({
        includeModern: false,
        mode: 'realtime',
        location: 'Greenwich, UK',
        timezone: 'Europe/London',
        latitude: 51.4769,
        longitude: -0.0005,
        houseSystem: 'R',
      });
    });
    expect(screen.getByLabelText('Directional saved snap')).toHaveValue('');

    expect(screen.getByRole('button', { name: 'Time +1h' })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: 'Time +1h' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledTimes(4);
    });
    expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith({
      includeModern: false,
      mode: 'manual',
      datetime: '2026-05-18T16:41:00.000Z',
      location: 'Greenwich, UK',
      timezone: 'Europe/London',
      latitude: 51.4769,
      longitude: -0.0005,
      houseSystem: 'R',
    });
  });

  it('lets Directional 3D reload from a saved snap inside the modal', async () => {
    astroClockApiMock.getDirectional3d
      .mockResolvedValueOnce({
        success: true,
        data: {
          systems: ['EQL', 'EQU', 'HOR'],
          chart_info: {
            utc_datetime: '2026-03-22T04:32:00+00:00',
            latitude: 31.778,
            longitude: 35.235,
            rotation: 9,
            tilt: 19,
            house_system: 'R',
          },
          objects: [
            {
              object_id: 'planet:Sun',
              name: 'Sun',
              symbol: '\u2609',
              buse: true,
              bfull: true,
              EQL: { longitude: 1.5, latitude: 0.1, speed: 0.98 },
              EQU: { longitude: 1.4, latitude: 0.7, speed: 0.98 },
              HOR: { longitude: 88.1, latitude: 12.4, speed: 0 },
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          systems: ['EQL', 'EQU', 'HOR'],
          chart_info: {
            utc_datetime: '1990-01-13T19:33:00+00:00',
            latitude: 31.777779,
            longitude: 35.235001,
            rotation: 9,
            tilt: 19,
            house_system: 'T',
          },
          objects: [
            {
              object_id: 'planet:Moon',
              name: 'Moon',
              symbol: '\u263D',
              buse: true,
              bfull: true,
              EQL: { longitude: 145.9, latitude: -0.8, speed: 13.0 },
              EQU: { longitude: 147.9, latitude: 12.0, speed: 13.0 },
              HOR: { longitude: 91.8, latitude: 26.2, speed: 0 },
            },
          ],
        },
      });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-03-22T04:32:00Z"
        mode="manual"
        location="Israel"
        timezone="Asia/Jerusalem"
        latitude={31.778}
        longitude={35.235}
        houseSystem="R"
        initialData={{
          azimuths: [{ planet: 'Sun', azimuth_deg: 88.1, altitude_deg: 12.4, longitude_deg: 1.5 }],
          ascendant: 18,
          source: 'local_space',
          has_altitude: true,
        }}
        houseCusps={[18, 44, 71, 99, 130, 159, 198, 224, 251, 279, 310, 339]}
        snaps={[
          {
            id: 'snap-aziz',
            label: 'Aziz natal snap',
            effective_datetime: '1990-01-13T19:33:00+00:00',
            location: 'Jerusalem, Israel',
            timezone: 'Asia/Jerusalem',
            latitude: 0,
            longitude: 0,
            chart_snapshot: {
              timezone_info: {
                coordinates: {
                  latitude: 31.777779,
                  longitude: 35.235001,
                },
              },
            },
            dashboard: {
              latitude: 0,
              longitude: 0,
              house_system_code: 'T',
            },
          },
        ]}
        activeSnapId="snap-aziz"
        loadingSnaps={false}
        snapsLoaded
        onRefreshSnaps={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));
    expect(await screen.findByText('Directional 3D')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Current Manual' })).toHaveClass('bg-zinc-900');

    fireEvent.click(screen.getByRole('button', { name: 'Saved Snap' }));
    fireEvent.change(screen.getByLabelText('Directional saved snap'), {
      target: { value: 'snap-aziz' },
    });

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith({
        includeModern: false,
        mode: 'manual',
        datetime: '1990-01-13T19:33:00+00:00',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 31.777779,
        longitude: 35.235001,
        houseSystem: 'T',
      });
    });
    expect((await screen.findAllByText('Moon')).length).toBeGreaterThan(0);
    expect(screen.getByText('Aziz natal snap')).toBeInTheDocument();
  });

  it('opens Directional 3D from a saved snap when the current chart is unavailable', async () => {
    astroClockApiMock.getDirectional3d.mockResolvedValueOnce({
      success: true,
      data: {
        systems: ['EQL', 'EQU', 'HOR'],
        chart_info: {
          utc_datetime: '1990-01-13T19:33:00+00:00',
          latitude: 31.777779,
          longitude: 35.235001,
          rotation: 9,
          tilt: 19,
          house_system: 'T',
        },
        objects: [
          {
            object_id: 'planet:Moon',
            name: 'Moon',
            symbol: '\u263D',
            buse: true,
            bfull: true,
            EQL: { longitude: 145.9, latitude: -0.8, speed: 13.0 },
            EQU: { longitude: 147.9, latitude: 12.0, speed: 13.0 },
            HOR: { longitude: 91.8, latitude: 26.2, speed: 0 },
          },
        ],
      },
    });

    render(
      <CompassTile
        includeModern={false}
        houseSystem="R"
        snaps={[
          {
            id: 'snap-only',
            label: 'Only saved snap',
            effective_datetime: '1990-01-13T19:33:00+00:00',
            location: 'Jerusalem, Israel',
            timezone: 'Asia/Jerusalem',
            latitude: 31.777779,
            longitude: 35.235001,
            dashboard: { house_system_code: 'T' },
          },
        ]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledWith({
        includeModern: false,
        mode: 'manual',
        datetime: '1990-01-13T19:33:00+00:00',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 31.777779,
        longitude: 35.235001,
        houseSystem: 'T',
      });
    });
    expect(screen.getByRole('button', { name: 'Saved Snap' })).toHaveClass('bg-zinc-900');
    expect((await screen.findAllByText('Moon')).length).toBeGreaterThan(0);
  });

  it('loads full saved snap details before Directional 3D when the snap list omits coordinates', async () => {
    astroClockApiMock.getSnap.mockResolvedValueOnce({
      success: true,
      snap: {
        id: 'snap-utah',
        coords: [39.4225192, -111.714358],
        dashboard: {
          timezone: 'America/Denver',
          house_system_code: 'R',
        },
      },
    });
    astroClockApiMock.getDirectional3d.mockResolvedValueOnce({
      success: true,
      data: {
        systems: ['EQL', 'EQU', 'HOR'],
        chart_info: {
          utc_datetime: '2025-09-10T12:23:00+00:00',
          latitude: 39.4225192,
          longitude: -111.714358,
          rotation: 9,
          tilt: 19,
          house_system: 'R',
        },
        objects: [
          {
            object_id: 'planet:Moon',
            name: 'Moon',
            symbol: '\u263D',
            buse: true,
            bfull: true,
            EQL: { longitude: 28.98, latitude: 0, speed: 13.0 },
            EQU: { longitude: 26.85, latitude: 10.9, speed: 13.0 },
            HOR: { longitude: 205.1, latitude: 42.2, speed: 0 },
          },
        ],
      },
    });

    render(
      <CompassTile
        includeModern={false}
        houseSystem="R"
        snaps={[
          {
            id: 'snap-utah',
            label: 'Snap 2025-09-10 12:23:00 — utah',
            effective_datetime: '2025-09-10T12:23:00',
            location: 'utah',
            dashboard: {
              latitude: null,
              longitude: null,
              timezone: 'America/Denver',
            },
          },
        ]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));

    await waitFor(() => expect(astroClockApiMock.getSnap).toHaveBeenCalledWith('snap-utah'));
    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledWith({
        includeModern: false,
        mode: 'manual',
        datetime: '2025-09-10T12:23:00',
        location: 'utah',
        timezone: 'America/Denver',
        latitude: 39.4225192,
        longitude: -111.714358,
        houseSystem: 'R',
      });
    });
    expect((await screen.findAllByText('Moon')).length).toBeGreaterThan(0);
    expect(screen.getByText('Snap 2025-09-10 12:23:00 — utah')).toBeInTheDocument();
  });
});
