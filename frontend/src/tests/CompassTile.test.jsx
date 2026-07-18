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

function deferredPromise() {
  let resolve;
  let reject;
  const promise = new Promise((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, reject, resolve };
}

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

  it.each([
    ['null coordinates', null, null],
    ['blank coordinates', '  ', ''],
    ['non-finite coordinates', Number.NaN, Number.POSITIVE_INFINITY],
    ['out-of-range coordinates', 91, 181],
  ])('rejects %s instead of coercing them to a chart location', (_label, latitude, longitude) => {
    render(
      <CompassTile
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        latitude={latitude}
        longitude={longitude}
        houseSystem="R"
      />,
    );

    expect(screen.getByText('Set a chart location to render local-space bearings.')).toBeInTheDocument();
    expect(astroClockApiMock.getCompass).not.toHaveBeenCalled();
  });

  it('omits invalid coordinates when a specific location can be resolved remotely', async () => {
    astroClockApiMock.getCompass.mockResolvedValue({
      success: true,
      data: {
        azimuths: [{ planet: 'Mars', azimuth_deg: 120, altitude_deg: 20 }],
        ascendant: 12,
      },
    });

    render(
      <CompassTile
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        location="Greenwich, UK"
        timezone="Europe/London"
        latitude=""
        longitude={null}
        houseSystem="R"
      />,
    );

    await waitFor(() => {
      expect(astroClockApiMock.getCompass).toHaveBeenCalledWith(
        expect.objectContaining({
          latitude: undefined,
          longitude: undefined,
          location: 'Greenwich, UK',
        }),
      );
    });
  });

  it('rejects blank, null, and non-finite bearings without manufacturing north-zero markers', async () => {
    astroClockApiMock.getCompass.mockResolvedValue({
      success: true,
      data: {
        azimuths: [
          { planet: 'Sun', azimuth_deg: 45, altitude_deg: 10 },
          { planet: 'Moon', azimuth_deg: null, altitude_deg: 20 },
          { planet: 'Mars', azimuth_deg: '', altitude_deg: 30 },
          { planet: 'Venus', azimuth_deg: Number.POSITIVE_INFINITY, altitude_deg: 40 },
        ],
        ascendant: 0,
      },
    });

    render(
      <CompassTile
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        location="Greenwich, UK"
        latitude={51.4769}
        longitude={-0.0005}
        houseSystem="R"
      />,
    );

    expect(await screen.findByText('\u2609')).toBeInTheDocument();
    expect(document.querySelectorAll('[data-directional-anchor]')).toHaveLength(1);
    expect(screen.queryByText('\u263D')).not.toBeInTheDocument();
    expect(screen.queryByText('\u2642')).not.toBeInTheDocument();
    expect(screen.queryByText('\u2640')).not.toBeInTheDocument();
  });

  it('omits missing altitude from ALT while retaining the body in bearing-only AZ', () => {
    render(
      <CompassTile
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        location="Greenwich, UK"
        latitude={51.4769}
        longitude={-0.0005}
        initialData={{
          azimuths: [
            { planet: 'Sun', azimuth_deg: 45, altitude_deg: 10 },
            { planet: 'Moon', azimuth_deg: 90, altitude_deg: null },
            { planet: 'Mars', azimuth_deg: 135, altitude_deg: '' },
          ],
          ascendant: 0,
        }}
      />,
    );

    expect(screen.getByRole('button', { name: 'Alt' })).toHaveAttribute('aria-pressed', 'true');
    expect(document.querySelectorAll('[data-directional-anchor]')).toHaveLength(1);
    expect(screen.getByText('2 bodies are omitted because altitude is unavailable.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Az' }));

    expect(screen.getByRole('button', { name: 'Az' })).toHaveAttribute('aria-pressed', 'true');
    expect(document.querySelectorAll('[data-directional-anchor]')).toHaveLength(3);
    expect(screen.queryByText(/omitted because altitude is unavailable/i)).not.toBeInTheDocument();
  });

  it('keys remote data to its chart context so old bearings disappear during a context change', async () => {
    const firstRequest = deferredPromise();
    const secondRequest = deferredPromise();
    astroClockApiMock.getCompass
      .mockReturnValueOnce(firstRequest.promise)
      .mockReturnValueOnce(secondRequest.promise);

    const common = {
      mode: 'manual',
      timezone: 'Etc/UTC',
      latitude: 10,
      longitude: 20,
      houseSystem: 'R',
    };
    const { rerender } = render(
      <CompassTile
        {...common}
        timestamp="2026-01-01T00:00:00Z"
        location="First place"
      />,
    );

    await waitFor(() => expect(astroClockApiMock.getCompass).toHaveBeenCalledTimes(1));
    firstRequest.resolve({
      success: true,
      data: {
        azimuths: [{ planet: 'Sun', azimuth_deg: 10, altitude_deg: 5 }],
        ascendant: 1,
      },
    });
    expect(await screen.findByText('\u2609')).toBeInTheDocument();

    rerender(
      <CompassTile
        {...common}
        timestamp="2026-01-02T00:00:00Z"
        location="Second place"
      />,
    );

    expect(screen.queryByText('\u2609')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Updating local-space bearings');
    await waitFor(() => expect(astroClockApiMock.getCompass).toHaveBeenCalledTimes(2));

    secondRequest.resolve({
      success: true,
      data: {
        azimuths: [{ planet: 'Moon', azimuth_deg: 20, altitude_deg: 6 }],
        ascendant: 2,
      },
    });
    expect(await screen.findByText('\u263D')).toBeInTheDocument();
    expect(screen.queryByText('\u2609')).not.toBeInTheDocument();
  });

  it('uses payload angles with correct minute carry at sign and zodiac boundaries', () => {
    render(
      <CompassTile
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        location="Greenwich, UK"
        latitude={51.4769}
        longitude={-0.0005}
        initialData={{
          azimuths: [{ planet: 'Sun', azimuth_deg: 45, altitude_deg: 10 }],
          ascendant: 359.9999,
        }}
        houseCusps={[12, 42, 72, 102, 132, 162, 192]}
      />,
    );

    expect(screen.getByText("\u2648 0\u00B000'")).toBeInTheDocument();
    expect(screen.getByText("\u264E 0\u00B000'")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("29\u00B060'");
  });

  it('keeps AZ anchors on one radius and offsets colliding labels deterministically', () => {
    render(
      <CompassTile
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        location="Greenwich, UK"
        latitude={51.4769}
        longitude={-0.0005}
        initialData={{
          azimuths: [
            { planet: 'Sun', azimuth_deg: 45, altitude_deg: 5 },
            { planet: 'Moon', azimuth_deg: 45, altitude_deg: 80 },
          ],
          ascendant: 0,
        }}
      />,
    );

    const viewGroup = screen.getByRole('group', { name: 'Directional view' });
    expect(within(viewGroup).getByRole('button', { name: 'Alt' })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(within(viewGroup).getByRole('button', { name: 'Az' }));

    expect(within(viewGroup).getByRole('button', { name: 'Az' })).toHaveAttribute('aria-pressed', 'true');
    const sunAnchor = document.querySelector('[data-directional-anchor="Sun"]');
    const moonAnchor = document.querySelector('[data-directional-anchor="Moon"]');
    const sunLabel = document.querySelector('[data-directional-label="Sun"]');
    const moonLabel = document.querySelector('[data-directional-label="Moon"]');
    expect(sunAnchor).toBeTruthy();
    expect(moonAnchor).toBeTruthy();
    expect(sunAnchor.getAttribute('cx')).toBe(moonAnchor.getAttribute('cx'));
    expect(sunAnchor.getAttribute('cy')).toBe(moonAnchor.getAttribute('cy'));
    expect(`${sunLabel.getAttribute('x')},${sunLabel.getAttribute('y')}`)
      .not.toBe(`${moonLabel.getAttribute('x')},${moonLabel.getAttribute('y')}`);
    expect(document.querySelectorAll('[data-directional-leader]')).toHaveLength(1);
    expect(screen.getByRole('img', { name: /bearing-only compass/i }))
      .toHaveAttribute('data-directional-plot', 'azimuth');
  });

  it('reserves zenith and cardinal labels without moving exact ALT or AZ anchors', () => {
    render(
      <CompassTile
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        location="Greenwich, UK"
        latitude={51.4769}
        longitude={-0.0005}
        initialData={{
          azimuths: [
            { planet: 'Sun', azimuth_deg: 0, altitude_deg: 90 },
            { planet: 'Moon', azimuth_deg: 90, altitude_deg: 0 },
          ],
          ascendant: 0,
        }}
      />,
    );

    const sunAnchor = document.querySelector('[data-directional-anchor="Sun"]');
    const moonAnchor = document.querySelector('[data-directional-anchor="Moon"]');
    const zenithAnchor = document.querySelector('[data-directional-zenith-anchor]');
    const zenithLabel = document.querySelector('[data-directional-reference-label="Z"]');
    const eastLabel = document.querySelector('[data-directional-reference-label="E"]');
    const sunLabel = document.querySelector('[data-directional-label="Sun"]');
    const moonLabel = document.querySelector('[data-directional-label="Moon"]');
    const distance = (left, right) => Math.hypot(
      Number(left.getAttribute('x') ?? left.getAttribute('cx'))
        - Number(right.getAttribute('x') ?? right.getAttribute('cx')),
      Number(left.getAttribute('y') ?? left.getAttribute('cy'))
        - Number(right.getAttribute('y') ?? right.getAttribute('cy')),
    );

    expect(sunAnchor.getAttribute('cx')).toBe(zenithAnchor.getAttribute('cx'));
    expect(sunAnchor.getAttribute('cy')).toBe(zenithAnchor.getAttribute('cy'));
    expect(Number(moonAnchor.getAttribute('cx'))).toBeCloseTo(238, 5);
    expect(Number(moonAnchor.getAttribute('cy'))).toBeCloseTo(136, 5);
    expect(distance(sunLabel, zenithLabel)).toBeGreaterThanOrEqual(15);
    expect(distance(moonLabel, eastLabel)).toBeGreaterThanOrEqual(15);
    expect(document.querySelector('[data-directional-leader="Sun"]')).toBeTruthy();
    expect(document.querySelector('[data-directional-leader="Moon"]')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Az' }));

    const azSunAnchor = document.querySelector('[data-directional-anchor="Sun"]');
    const azSunLabel = document.querySelector('[data-directional-label="Sun"]');
    const northLabel = document.querySelector('[data-directional-reference-label="N"]');
    expect(Number(azSunAnchor.getAttribute('cx'))).toBeCloseTo(136, 5);
    expect(Number(azSunAnchor.getAttribute('cy'))).toBeCloseTo(52.5, 5);
    expect(distance(azSunLabel, northLabel)).toBeGreaterThanOrEqual(15);
    expect(document.querySelector('[data-directional-reference-label="Z"]')).toBeNull();
  });

  it('enforces the explicit traditional versus modern body scope', () => {
    const data = {
      azimuths: [
        { planet: 'Sun', azimuth_deg: 10, altitude_deg: 10 },
        { planet: 'Uranus', azimuth_deg: 20, altitude_deg: 20 },
        { planet: 'Chiron', azimuth_deg: 30, altitude_deg: 30 },
      ],
      ascendant: 0,
    };
    const { rerender } = render(
      <CompassTile
        includeModern={false}
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        location="Greenwich, UK"
        latitude={51.4769}
        longitude={-0.0005}
        initialData={data}
      />,
    );

    expect(screen.getByTitle('Current chart · Traditional bodies')).toBeInTheDocument();
    expect(document.querySelector('[data-directional-anchor="Sun"]')).toBeTruthy();
    expect(document.querySelector('[data-directional-anchor="Uranus"]')).toBeNull();
    expect(document.querySelector('[data-directional-anchor="Chiron"]')).toBeNull();

    rerender(
      <CompassTile
        includeModern
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        location="Greenwich, UK"
        latitude={51.4769}
        longitude={-0.0005}
        initialData={data}
      />,
    );

    expect(screen.getByTitle('Current chart · Traditional and modern bodies')).toBeInTheDocument();
    expect(document.querySelector('[data-directional-anchor="Uranus"]')).toBeTruthy();
    expect(document.querySelector('[data-directional-anchor="Chiron"]')).toBeNull();
  });

  it('announces request failures and retries without retaining failed request state', async () => {
    const firstRequest = deferredPromise();
    astroClockApiMock.getCompass
      .mockReturnValueOnce(firstRequest.promise)
      .mockResolvedValueOnce({
        success: true,
        data: {
          azimuths: [{ planet: 'Sun', azimuth_deg: 45, altitude_deg: 10 }],
          ascendant: 0,
        },
      });

    const { container } = render(
      <CompassTile
        timestamp="2026-04-14T09:43:00Z"
        mode="manual"
        location="Greenwich, UK"
        latitude={51.4769}
        longitude={-0.0005}
      />,
    );

    await waitFor(() => expect(container.firstChild).toHaveAttribute('aria-busy', 'true'));
    firstRequest.resolve({ success: false, error: 'Bearing service unavailable' });
    expect(await screen.findByRole('alert')).toHaveTextContent('Bearing service unavailable');

    fireEvent.click(screen.getByRole('button', { name: 'Retry bearings' }));

    expect(await screen.findByText('\u2609')).toBeInTheDocument();
    expect(astroClockApiMock.getCompass).toHaveBeenCalledTimes(2);
    expect(container.firstChild).toHaveAttribute('aria-busy', 'false');
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
    expect(screen.getByText('Ascendant')).toBeInTheDocument();
    expect(screen.getByText('Descendant')).toBeInTheDocument();
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

  it('keeps bearings, angles, and the initial 3D request on the same saved-chart source', async () => {
    astroClockApiMock.getCompass.mockResolvedValue({
      success: true,
      data: {
        azimuths: [{ planet: 'Moon', azimuth_deg: 91, altitude_deg: 25 }],
        ascendant: 29.9999,
        source: 'local_space',
      },
    });
    astroClockApiMock.getDirectional3d.mockResolvedValue({
      success: true,
      data: {
        systems: ['EQL', 'EQU', 'HOR'],
        chart_info: {
          utc_datetime: '2001-06-15T08:15:00+00:00',
          latitude: 51.5,
          longitude: -0.1,
          house_system: 'T',
        },
        objects: [],
      },
    });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-03-22T04:32:00Z"
        mode="manual"
        location="Current place"
        timezone="Etc/UTC"
        latitude={31.778}
        longitude={35.235}
        houseSystem="R"
        initialData={{
          azimuths: [{ planet: 'Sun', azimuth_deg: 88, altitude_deg: 12 }],
          ascendant: 15,
        }}
        houseCusps={[15, 45, 75, 105, 135, 165, 195]}
        snaps={[{
          id: 'snap-source',
          label: 'Saved source chart',
          effective_datetime: '2001-06-15T08:15:00+00:00',
          location: 'Saved place',
          timezone: 'Etc/UTC',
          latitude: 51.5,
          longitude: -0.1,
          dashboard: { house_system_code: 'T' },
        }]}
        activeSnapId="snap-source"
      />,
    );

    expect(await screen.findByText('\u263D')).toBeInTheDocument();
    expect(astroClockApiMock.getCompass).toHaveBeenCalledWith({
      includeModern: false,
      snapId: 'snap-source',
      houseSystem: 'T',
    });
    expect(screen.queryByText('\u2609')).not.toBeInTheDocument();
    expect(screen.getByTitle('Saved source chart · Traditional bodies')).toBeInTheDocument();
    expect(screen.getByText("\u2649 0\u00B000'")).toBeInTheDocument();
    expect(screen.getByText("\u264F 0\u00B000'")).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '3D' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledWith({
        includeModern: false,
        snapId: 'snap-source',
        houseSystem: 'T',
      });
    });
    expect(screen.getByRole('button', { name: '3D' })).toHaveAttribute('aria-expanded', 'true');
  });

  it('loads saved-chart detail to recover its stored house system before Compass calculation', async () => {
    astroClockApiMock.getSnap.mockResolvedValue({
      success: true,
      snap: {
        id: 'snap-house-detail',
        dashboard: {
          house_system_code: 'T',
        },
      },
    });
    astroClockApiMock.getCompass.mockResolvedValue({
      success: true,
      data: {
        azimuths: [{ planet: 'Sun', azimuth_deg: 40, altitude_deg: 20 }],
        ascendant: 12,
      },
    });

    render(
      <CompassTile
        includeModern={false}
        timestamp="2026-03-22T04:32:00Z"
        mode="manual"
        location="Current place"
        timezone="Etc/UTC"
        latitude={31.778}
        longitude={35.235}
        houseSystem="R"
        snaps={[{
          id: 'snap-house-detail',
          label: 'Stored Topocentric chart',
          effective_datetime: '2001-06-15T08:15:00+00:00',
          location: 'Saved place',
          timezone: 'Etc/UTC',
          latitude: 51.5,
          longitude: -0.1,
        }]}
        activeSnapId="snap-house-detail"
      />,
    );

    await waitFor(() => expect(astroClockApiMock.getSnap).toHaveBeenCalledWith('snap-house-detail'));
    await waitFor(() => {
      expect(astroClockApiMock.getCompass).toHaveBeenCalledWith({
        includeModern: false,
        snapId: 'snap-house-detail',
        houseSystem: 'T',
      });
    });
    expect(await screen.findByText('\u2609')).toBeInTheDocument();
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
    expect(screen.getByRole('button', { name: 'HOR' })).toHaveAttribute('aria-pressed', 'true');
    let chart = screen.getByRole('group', { name: 'Horizon Directional 3D chart' });
    expect(within(chart).getByRole('button', {
      name: 'Inspect Sun in Horizon coordinates',
    })).toHaveAttribute('aria-pressed', 'true');
    let selectedSunGlyph = chart.querySelector('[data-directional-selected-object="planet:Sun"]');
    expect(selectedSunGlyph).toBeTruthy();
    expect(selectedSunGlyph).toHaveAttribute('data-directional-selected-system', 'HOR');
    expect(selectedSunGlyph).toHaveAttribute('filter', 'url(#directional-selected-glow-HOR)');
    expect(selectedSunGlyph).toHaveAttribute('stroke', 'none');
    expect(chart.querySelectorAll('[data-directional-selected-frame]')).toHaveLength(0);
    expect(chart.querySelectorAll('[data-directional-house-boundary]')).toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Horizon' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back points' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back points' })).toHaveAttribute('aria-pressed');
    expect(chart.querySelectorAll('[data-directional-reference="tropic"]')).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: 'EQU' }));
    chart = screen.getByRole('group', { name: 'Equatorial Directional 3D chart' });
    expect(screen.getByRole('button', { name: 'Equator' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tropics' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Polar' })).toBeInTheDocument();
    expect(chart.querySelectorAll('[data-directional-reference="tropic"]').length).toBeGreaterThan(0);
    expect(chart.querySelectorAll('[data-directional-reference="polar"]').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: 'Tropics' }));
    expect(chart.querySelectorAll('[data-directional-reference="tropic"]')).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: 'EQL' }));
    chart = screen.getByRole('group', { name: 'Ecliptic Directional 3D chart' });
    expect(screen.getByRole('button', { name: 'Ecliptic' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cusp points' })).toBeInTheDocument();
    expect(chart.querySelectorAll('[data-directional-house-cusp]')).toHaveLength(2);
    selectedSunGlyph = chart.querySelector('[data-directional-selected-object="planet:Sun"]');
    expect(selectedSunGlyph).toHaveAttribute('data-directional-selected-system', 'EQL');
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
    expect(within(inspector).getByText(/Sun/)).toBeInTheDocument();
    expect(screen.getByText('Lat speed -0.121')).toBeInTheDocument();
    expect(screen.getByText('Speed 312.456')).toBeInTheDocument();
    expect(screen.getByText('Lat speed -148.123')).toBeInTheDocument();
    expect(screen.getAllByText('Sun').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Moon').length).toBeGreaterThan(0);
    const houseRow = screen.getByRole('row', { name: /House 1/ });
    expect(within(houseRow).getByText('House 1')).toBeInTheDocument();
    expect(within(houseRow).queryByText('H1')).not.toBeInTheDocument();
    fireEvent.click(within(houseRow).getByRole('button', { name: /Inspect House 1 EQL Lon/ }));
    const selectedHouseMarker = chart.querySelector(
      '[data-directional-house-cusp="cusp:1"] circle:not([data-directional-hit-target])',
    );
    expect(selectedHouseMarker).toHaveAttribute('r', '4.5');
    const sunRow = screen.getByRole('row', { name: /Sun/ });
    expect(within(sunRow).getByText('\u2609')).toBeInTheDocument();
    const marsRow = screen.getByRole('row', { name: /Mars/ });
    fireEvent.click(within(marsRow).getByRole('button', { name: /Inspect Mars EQL Lon/ }));
    const selectedMarsGlyph = chart.querySelector('[data-directional-selected-object="planet:Mars"]');
    expect(selectedMarsGlyph).toHaveAttribute('data-directional-selected-system', 'EQL');
    expect(selectedMarsGlyph).toHaveAttribute('fill', '#ef4444');
    expect(selectedMarsGlyph).toHaveAttribute('color', '#ef4444');
    const saturnRow = screen.getByRole('row', { name: /Saturn/ });
    fireEvent.click(within(saturnRow).getByRole('button', { name: /Inspect Saturn EQL Lon/ }));
    const selectedSaturnGlyph = chart.querySelector('[data-directional-selected-object="planet:Saturn"]');
    expect(selectedSaturnGlyph).toHaveAttribute('data-directional-selected-system', 'EQL');
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

  it('retries the exact failed stepped context and replaces it on a base reload', async () => {
    const payload = (utcDatetime) => ({
      systems: ['EQL', 'EQU', 'HOR'],
      chart_info: {
        utc_datetime: utcDatetime,
        latitude: 31.778,
        longitude: 35.235,
        house_system: 'R',
      },
      objects: [{
        object_id: 'planet:Sun',
        name: 'Sun',
        symbol: '\u2609',
        EQL: { longitude: 1.5, latitude: 0.1, speed: 0.98 },
        EQU: { longitude: 1.4, latitude: 0.7, speed: 0.98 },
        HOR: { longitude: 88.1, latitude: 12.4, speed: 0 },
      }],
    });
    astroClockApiMock.getDirectional3d
      .mockResolvedValueOnce({
        success: true,
        data: payload('2026-03-22T04:32:00+00:00'),
      })
      .mockResolvedValueOnce({ success: false, error: 'Stepped request failed' })
      .mockResolvedValueOnce({
        success: true,
        data: payload('2026-03-22T05:32:00+00:00'),
      })
      .mockResolvedValueOnce({ success: false, error: 'Base reload failed' })
      .mockResolvedValueOnce({
        success: true,
        data: payload('2026-03-22T04:32:00+00:00'),
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
          azimuths: [{ planet: 'Sun', azimuth_deg: 88.1, altitude_deg: 12.4 }],
          ascendant: 18,
        }}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));
    expect(await screen.findByText('Directional 3D')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Time +1h' }));
    expect(await screen.findByText('Stepped request failed')).toBeInTheDocument();

    const steppedRequest = {
      includeModern: false,
      mode: 'manual',
      datetime: '2026-03-22T05:32:00.000Z',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    };
    expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith(steppedRequest);

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledTimes(3));
    expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith(steppedRequest);

    fireEvent.click(screen.getByRole('button', { name: 'Current Manual' }));
    expect(await screen.findByText('Base reload failed')).toBeInTheDocument();
    const baseRequest = {
      includeModern: false,
      mode: 'manual',
      datetime: '2026-03-22T04:32:00Z',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    };
    expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith(baseRequest);

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledTimes(5));
    expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith(baseRequest);
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
            utc_datetime: '2001-06-15T08:15:00+00:00',
            latitude: 51.5,
            longitude: -0.1,
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
            id: 'snap-synthetic',
            label: 'Synthetic saved chart',
            effective_datetime: '2001-06-15T08:15:00+00:00',
            location: 'Synthetic City',
            timezone: 'Europe/London',
            latitude: 51.5,
            longitude: -0.1,
            dashboard: { house_system_code: 'T' },
          },
        ]}
        loadingSnaps={false}
        snapsLoaded
        onRefreshSnaps={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));
    expect(await screen.findByText('Directional 3D')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Saved Snap' }));
    fireEvent.change(screen.getByLabelText('Directional saved snap'), {
      target: { value: 'snap-synthetic' },
    });
    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith({
        includeModern: false,
        snapId: 'snap-synthetic',
        houseSystem: 'T',
      });
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
            utc_datetime: '2001-06-15T08:15:00+00:00',
            latitude: 51.5,
            longitude: -0.1,
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
            id: 'snap-synthetic',
            label: 'Synthetic saved chart',
            effective_datetime: '2001-06-15T08:15:00+00:00',
            location: 'Synthetic City',
            timezone: 'Europe/London',
            latitude: 0,
            longitude: 0,
            chart_snapshot: {
              timezone_info: {
                coordinates: {
                  latitude: 51.5,
                  longitude: -0.1,
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
        loadingSnaps={false}
        snapsLoaded
        onRefreshSnaps={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));
    expect(await screen.findByText('Directional 3D')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Current Manual' })).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(screen.getByRole('button', { name: 'Saved Snap' }));
    fireEvent.change(screen.getByLabelText('Directional saved snap'), {
      target: { value: 'snap-synthetic' },
    });

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenLastCalledWith({
        includeModern: false,
        snapId: 'snap-synthetic',
        houseSystem: 'T',
      });
    });
    expect((await screen.findAllByText('Moon')).length).toBeGreaterThan(0);
    expect(screen.getByText('Synthetic saved chart')).toBeInTheDocument();
  });

  it('opens Directional 3D from a saved snap when the current chart is unavailable', async () => {
    astroClockApiMock.getDirectional3d.mockResolvedValueOnce({
      success: true,
      data: {
        systems: ['EQL', 'EQU', 'HOR'],
        chart_info: {
          utc_datetime: '2001-06-15T08:15:00+00:00',
          latitude: 51.5,
          longitude: -0.1,
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
            effective_datetime: '2001-06-15T08:15:00+00:00',
            location: 'Synthetic City',
            timezone: 'Europe/London',
            latitude: 51.5,
            longitude: -0.1,
            dashboard: { house_system_code: 'T' },
          },
        ]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '3D' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledWith({
        includeModern: false,
        snapId: 'snap-only',
        houseSystem: 'T',
      });
    });
    expect(screen.getByRole('button', { name: 'Saved Snap' })).toHaveAttribute('aria-pressed', 'true');
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
        snapId: 'snap-utah',
        houseSystem: 'R',
      });
    });
    expect((await screen.findAllByText('Moon')).length).toBeGreaterThan(0);
    expect(screen.getByText('Snap 2025-09-10 12:23:00 — utah')).toBeInTheDocument();
  });

  it('keeps review-required and superseded charts out of Compass and Directional 3D', async () => {
    astroClockApiMock.getDirectional3d.mockResolvedValueOnce({
      success: true,
      data: {
        systems: ['EQL', 'EQU', 'HOR'],
        chart_info: {
          utc_datetime: '2002-04-05T09:20:00+00:00',
          latitude: 1,
          longitude: 2,
          house_system: 'R',
        },
        objects: [],
      },
    });

    render(
      <CompassTile
        includeModern={false}
        houseSystem="R"
        activeSnapId="snap-review"
        snaps={[
          {
            id: 'snap-review',
            label: 'Review chart',
            calculation_context: { review_required: true },
          },
          {
            id: 'snap-old',
            label: 'Old chart',
            superseded_by: 'snap-safe',
          },
          {
            id: 'snap-safe',
            label: 'Safe chart',
            effective_datetime: '2002-04-05T09:20:00+00:00',
            location: 'Synthetic place',
            timezone: 'Etc/UTC',
            latitude: 1,
            longitude: 2,
            dashboard: { house_system_code: 'R' },
          },
        ]}
        snapsLoaded
      />,
    );

    expect(astroClockApiMock.getCompass).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '3D' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDirectional3d).toHaveBeenCalledWith({
        includeModern: false,
        snapId: 'snap-safe',
        houseSystem: 'R',
      });
    });

    const select = screen.getByLabelText('Directional saved snap');
    expect(within(select).getByRole('option', { name: /Review chart.*needs context review/i })).toBeDisabled();
    expect(within(select).getByRole('option', { name: /Old chart.*superseded.*corrected copy/i })).toBeDisabled();
    expect(screen.getByText(/Review-required and superseded saved charts are disabled/i)).toBeInTheDocument();
  });
});
