import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';

const astroClockApiMock = vi.hoisted(() => ({
  listSnaps: vi.fn(),
  listAstrocartographyGoals: vi.fn(),
  getAstrocartographyMap: vi.fn(),
  getAstrocartographyLocation: vi.fn(),
  startAstrocartographyAtlasSearch: vi.fn(),
  getAstrocartographyAtlasSearchProgress: vi.fn(),
  getAstrocartographyAtlasSearchResult: vi.fn(),
  cancelAstrocartographyAtlasSearch: vi.fn(),
  compareAstrocartographyTargets: vi.fn(),
}));

const pollAsyncSessionMock = vi.hoisted(() => vi.fn());
const leafletMapMock = vi.hoisted(() => ({
  setView: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  getBounds: () => ({
    getNorth: () => 60,
    getSouth: () => -60,
    getEast: () => 180,
    getWest: () => -180,
  }),
  latLngToContainerPoint: () => ({ x: 0, y: 0 }),
}));

vi.mock('leaflet', () => {
  const Default = { mergeOptions: vi.fn() };
  const divIcon = vi.fn(() => ({}));
  return {
    default: { Icon: { Default }, divIcon },
    Icon: { Default },
    divIcon,
  };
});

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }) => <div data-testid="map">{children}</div>,
  Marker: ({ children }) => <div>{children}</div>,
  Popup: ({ children }) => <div>{children}</div>,
  Polyline: () => null,
  Circle: () => null,
  CircleMarker: ({ children }) => <div>{children}</div>,
  GeoJSON: () => null,
  useMap: () => leafletMapMock,
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

vi.mock('../features/astroclock/researchPolling.mjs', () => ({
  pollAsyncSession: pollAsyncSessionMock,
}));

vi.mock('../features/astroclock/MundaneWorkspace.jsx', () => ({
  default: () => <div data-testid="mundane-workspace" />,
}));

vi.mock('../features/astroclock/WeatherWorkspace.jsx', () => ({
  default: () => <div data-testid="weather-workspace" />,
}));

function makeMapResponse() {
  return {
    success: true,
    data: {
      natal: {
        timestamp: '2024-01-01T00:00:00Z',
        timezone: 'UTC',
      },
      map: {
        natal_lines: [],
        transit_lines: [],
        global_parans: { tracks: [] },
        transit_global_parans: { tracks: [] },
      },
    },
  };
}

async function renderModal(props = {}) {
  const { default: AstrocartographyModal } = await import('../features/astroclock/AstrocartographyModal.jsx');
  const onClose = props.onClose ?? vi.fn();
  await act(async () => {
    render(
      <AstrocartographyModal
        open
        onClose={onClose}
        defaultHouseSystem="R"
        {...props}
      />
    );
    await Promise.resolve();
  });
  return { onClose };
}

describe('AstrocartographyModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    astroClockApiMock.listSnaps.mockResolvedValue({ success: true, items: [] });
    astroClockApiMock.listAstrocartographyGoals.mockResolvedValue({ success: true, data: { goals: [] } });
    astroClockApiMock.getAstrocartographyMap.mockResolvedValue(makeMapResponse());
    astroClockApiMock.getAstrocartographyLocation.mockResolvedValue({ success: true, data: null });
    astroClockApiMock.startAstrocartographyAtlasSearch.mockResolvedValue({
      success: true,
      data: {
        session_id: 'session-1',
        progress: {
          ready: false,
          failed: false,
          percent: 0,
          stage: 'queued',
          message: 'Atlas search queued',
          done: 0,
          total: 0,
        },
      },
    });
    astroClockApiMock.getAstrocartographyAtlasSearchProgress.mockResolvedValue({ success: true, data: {} });
    astroClockApiMock.getAstrocartographyAtlasSearchResult.mockResolvedValue({ success: true, data: {} });
    astroClockApiMock.cancelAstrocartographyAtlasSearch.mockResolvedValue({ success: true, data: {} });
    astroClockApiMock.compareAstrocartographyTargets.mockResolvedValue({ success: true, data: {} });
    pollAsyncSessionMock.mockResolvedValue({
      ready: true,
      failed: false,
      percent: 1,
      stage: 'ready',
      message: 'Atlas search complete',
      done: 8,
      total: 8,
    });
  });

  it('surfaces PathFinder goal bootstrap failures in the astrocartography workspace', async () => {
    astroClockApiMock.listAstrocartographyGoals.mockResolvedValueOnce({
      success: false,
      error: 'Failed to load PathFinder goals. Refresh to retry.',
    });

    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
    });

    await waitFor(() => {
      expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled();
    });

    expect(await screen.findByText('Failed to load PathFinder goals. Refresh to retry.')).toBeInTheDocument();
  });

  it('surfaces saved-snap bootstrap failures instead of falling back to a silent empty state', async () => {
    astroClockApiMock.listSnaps.mockResolvedValueOnce({
      success: false,
      error: 'Failed to load saved natal snaps. Refresh to retry.',
    });

    await renderModal();

    expect(await screen.findByText('Failed to load saved natal snaps. Refresh to retry.')).toBeInTheDocument();
  });

  it('keeps General inspection selected and explains the atlas dependency on PathFinder goals', async () => {
    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
      initialGoalOptions: [{ id: 'career_public_profile', label: 'Career Public Profile', goal_family: 'career' }],
    });

    await waitFor(() => {
      expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled();
    });

    expect(screen.getByDisplayValue('General inspection')).toHaveValue('');
    expect(screen.getByText('General inspection keeps the workspace neutral. Choose a PathFinder goal to enable Search Best Cities.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Search Best Cities' })).toBeDisabled();
  });

  it('cancels the active atlas session when the modal closes', async () => {
    let resolvePoll;
    pollAsyncSessionMock.mockImplementation(() => new Promise((resolve) => {
      resolvePoll = resolve;
    }));
    const { onClose } = await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
      initialGoalOptions: [{ id: 'career_public_profile', label: 'Career Public Profile', goal_family: 'career' }],
    });

    await waitFor(() => {
      expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled();
    });

    fireEvent.change(screen.getByDisplayValue('General inspection'), {
      target: { value: 'career_public_profile' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Search Best Cities' }));

    await waitFor(() => {
      expect(astroClockApiMock.startAstrocartographyAtlasSearch).toHaveBeenCalled();
    });

    fireEvent.click(screen.getAllByText('Close')[0]);

    await waitFor(() => {
      expect(astroClockApiMock.cancelAstrocartographyAtlasSearch).toHaveBeenCalledWith('session-1');
    });
    expect(onClose).toHaveBeenCalled();
    resolvePoll?.({
      ready: false,
      failed: false,
      percent: 0.2,
      stage: 'cancelling',
      message: 'Cancelling atlas search',
      done: 0,
      total: 0,
    });
  });
});
