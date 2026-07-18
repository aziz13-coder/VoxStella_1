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

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
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

  it('blocks review-required saved charts until the corrected copy is selected', async () => {
    await renderModal({
      snaps: [{
        id: 'snap-review',
        label: 'Legacy chart',
        calculation_context: { review_required: true },
      }],
      activeSnapId: 'snap-review',
    });

    expect((await screen.findAllByText(
      /cannot be used for astrocartography.*correct its context or choose its corrected copy/i,
    )).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('option', {
      name: 'Legacy chart (needs context review)',
    })[0]).toBeDisabled();
    expect(astroClockApiMock.getAstrocartographyMap).not.toHaveBeenCalled();
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
    expect(screen.getByText('General inspection keeps the workspace neutral. Choose a PathFinder goal to rank candidate cities.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Rank Candidate Cities' })).toBeDisabled();
    expect(screen.getByText(/Astrology ranking only\. It does not assess personal safety/i)).toBeInTheDocument();
  });

  it('offers Chiron as an astrocartography body filter', async () => {
    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
    });

    await waitFor(() => {
      expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled();
    });

    expect(screen.getByLabelText(/Chiron/i)).toBeChecked();
  });

  it('shows one full body name without a duplicate abbreviation chip', async () => {
    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
    });

    await waitFor(() => {
      expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled();
    });

    expect(screen.getByLabelText('Jupiter')).toBeChecked();
    expect(screen.queryByText('Ju')).not.toBeInTheDocument();
    expect(screen.getByText(/North Node uses the mean node/i)).toBeInTheDocument();
  });

  it('shows observed birth-time resampling and the returned line envelope', async () => {
    const response = makeMapResponse();
    response.data.birth_time = {
      status: 'user_entered_time',
      confidence: 'user_entered',
      ranking_eligible: true,
    };
    response.data.birth_time_sampling = {
      status: 'ready',
      sample_count: 2,
      sampled_uncertainty_minutes: 5,
      assumption: 'User-entered times without a declared range are sampled at ±5 minutes.',
    };
    response.data.map.natal_line_uncertainty = {
      status: 'evaluated',
      corridors: [
        { id: 'Mars:IC', sampled_width_km_at_equator: 83.6 },
      ],
    };
    astroClockApiMock.getAstrocartographyMap.mockResolvedValueOnce(response);

    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
    });

    expect(await screen.findByText(/Recalculated 2 alternative birth times/i)).toBeInTheDocument();
    expect(screen.getByText(/widest sampled map-line envelope is about 84 km/i)).toBeInTheDocument();
  });

  it('labels higher-is-worse goals as lower-pressure rankings with an experimental caveat', async () => {
    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
      initialGoalOptions: [
        {
          id: 'health_risk',
          label: 'Health Risk',
          goal_family: 'risk',
          score_polarity: 'higher_is_worse',
        },
      ],
    });

    await waitFor(() => {
      expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled();
    });

    fireEvent.change(screen.getByDisplayValue('General inspection'), {
      target: { value: 'health_risk' },
    });

    expect(screen.getByRole('button', { name: 'Rank Lower Pressure' })).toBeEnabled();
    expect(screen.getByText('Lower-pressure candidates')).toBeInTheDocument();
    expect(screen.getByText('Experimental health-pressure interpretation')).toBeInTheDocument();
    expect(screen.getByText('Interpretive research only. It is not medical guidance or a prediction of illness.')).toBeInTheDocument();
  });

  it('uses pressure wording and adverse colors for high higher-is-worse scores', async () => {
    astroClockApiMock.startAstrocartographyAtlasSearch.mockResolvedValue({
      success: true,
      data: {
        session_id: 'session-pressure',
        progress: { ready: true, failed: false, percent: 1, stage: 'ready' },
      },
    });
    astroClockApiMock.getAstrocartographyAtlasSearchResult.mockResolvedValue({
      success: true,
      data: {
        ready: true,
        result: {
          birth_time: { status: 'certified', ranking_eligible: true },
          atlas: { candidate_count: 2, shortlisted_count: 2, resolution: { label: 'Standard' } },
          results: [
            {
              target: { candidate_id: 'high-pressure', label: 'High Pressure', latitude: 10, longitude: 20 },
              location_score: { score: 85, evidence_strength: 'strong' },
            },
            {
              target: { candidate_id: 'low-pressure', label: 'Low Pressure', latitude: 30, longitude: 40 },
              location_score: { score: 20, evidence_strength: 'weak' },
            },
          ],
        },
      },
    });

    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
      initialGoalOptions: [{
        id: 'health_risk',
        label: 'Health Risk',
        status: 'experimental',
        goal_family: 'risk',
        score_polarity: 'higher_is_worse',
      }],
    });
    await waitFor(() => expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled());
    fireEvent.change(screen.getByDisplayValue('General inspection'), {
      target: { value: 'health_risk' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Rank Lower Pressure' }));

    const highPressureBadge = await screen.findByText('Modeled pressure Strong');
    const lowPressureBadge = screen.getByText('Modeled pressure Weak');
    expect(highPressureBadge).toHaveClass('text-rose-700');
    expect(lowPressureBadge).toHaveClass('text-emerald-700');
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
    fireEvent.click(screen.getByRole('button', { name: 'Rank Candidate Cities' }));

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

  it('keeps active and experimental travel goals visible while excluding deprecated goals', async () => {
    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
      initialGoalOptions: [
        { id: 'travel_fun', label: 'Travel Fun', status: 'active', goal_family: 'travel' },
        { id: 'travel_relax', label: 'Travel Relax', status: 'experimental', goal_family: 'travel' },
        { id: 'old_travel', label: 'Old Travel', status: 'deprecated', goal_family: 'travel' },
      ],
    });

    await waitFor(() => {
      expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled();
    });

    expect(screen.getByRole('option', { name: 'Travel Fun (Experimental)' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Travel Relax (Experimental)' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Old Travel' })).not.toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue('General inspection'), {
      target: { value: 'travel_fun' },
    });
    expect(screen.getByText('Interpretive research only. Use practical safety, budget, and travel information when choosing a destination.')).toBeInTheDocument();
  });

  it('shows birth-time uncertainty and keeps an ineligible snap inspection-only', async () => {
    const mapResponse = makeMapResponse();
    mapResponse.data.birth_time = {
      status: 'approximate',
      confidence: 'low',
      uncertainty_minutes: 18,
      ranking_eligible: false,
      ranking_eligibility: 'ineligible_low_resolution',
      warnings: ['Birth-time uncertainty exceeds the ranking threshold.'],
    };
    mapResponse.data.calculation = {
      natal: {
        engine: 'Swiss Ephemeris',
        version: 'test-v1',
        frame: 'geocentric_equatorial',
      },
      degraded: true,
      warnings: ['Fallback provenance path was used.'],
    };
    mapResponse.data.distance_policy = {
      version: 'policy-v1',
      primary_radius_km: 250,
      local_paran_orb_deg: 1.5,
    };
    mapResponse.data.map.global_parans.degraded = true;
    astroClockApiMock.getAstrocartographyMap.mockResolvedValue(mapResponse);
    astroClockApiMock.getAstrocartographyLocation.mockResolvedValue({
      success: true,
      data: {
        target: { label: 'London, UK', query: 'London, UK', latitude: 51.5074, longitude: -0.1278 },
        birth_time: mapResponse.data.birth_time,
        natal: { reading: { signal_score: 55, nearest_lines: [] } },
        location_score: { score: 72 },
      },
    });

    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Approximate Snap' }],
      activeSnapId: 'snap-1',
      initialGoalOptions: [{ id: 'career_public_profile', label: 'Career Public Profile', goal_family: 'career' }],
    });

    expect(await screen.findByText('Inspection only · ranking unavailable')).toBeInTheDocument();
    expect(screen.getByText(/±18 min/)).toBeInTheDocument();
    expect(screen.getByText('Swiss Ephemeris · test-v1')).toBeInTheDocument();
    expect(screen.getByText('Primary Radius Km: 250')).toBeInTheDocument();
    expect(screen.getByText('Degraded')).toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue('General inspection'), {
      target: { value: 'career_public_profile' },
    });
    expect(screen.getByRole('button', { name: 'Inspection Only' })).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText('e.g., London, UK'), {
      target: { value: 'London, UK' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Inspect' }));

    expect(await screen.findByRole('button', { name: 'Add To Compare' })).toBeDisabled();
    expect(screen.getByText('Insufficient · index 72')).toBeInTheDocument();
    expect(screen.getByText('Transit and natal signals are displayed separately. The client does not apply a fixed natal/transit blend.')).toBeInTheDocument();
  });

  it('renders structured relocation errors without object coercion', async () => {
    astroClockApiMock.getAstrocartographyLocation.mockResolvedValue({
      success: true,
      data: {
        target: { label: 'Unavailable City', query: 'Unavailable City', latitude: 5, longitude: 6 },
        birth_time: { status: 'certified', ranking_eligible: true },
        natal: { reading: { signal_score: 30, nearest_lines: [] } },
        relocation: {
          available: false,
          relocation_unavailable: true,
          error: {
            code: 'relocation_failed',
            message: 'Relocated houses could not be calculated.',
          },
          warnings: [],
        },
      },
    });

    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
    });
    await waitFor(() => expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled());
    fireEvent.change(screen.getByPlaceholderText('e.g., London, UK'), {
      target: { value: 'Unavailable City' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Inspect' }));

    expect((await screen.findAllByText('relocation_failed: Relocated houses could not be calculated.')).length).toBeGreaterThan(0);
    expect(screen.getByText('Regiomontanus (R)')).toBeInTheDocument();
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
  });

  it('labels experimental and fallback line meanings on individual reading cards', async () => {
    astroClockApiMock.getAstrocartographyLocation.mockResolvedValue({
      success: true,
      data: {
        target: { label: 'Paris, France', query: 'Paris', latitude: 48.85341, longitude: 2.3488 },
        birth_time: { status: 'user_entered_time', ranking_eligible: true },
        natal: {
          reading: {
            signal_score: 45,
            nearest_lines: [
              {
                id: 'North Node:ASC',
                label: 'North Node ASC',
                distance_km: 42,
                zone: 'primary',
                summary: 'An experimental nodal interpretation.',
                caution: 'Treat as secondary.',
                interpretation_status: 'curated_experimental_extension',
              },
              {
                id: 'Unsupported:MC',
                label: 'Unsupported MC',
                distance_km: 84,
                zone: 'primary',
                summary: 'A generic fallback interpretation.',
                caution: 'Dedicated doctrine is unavailable.',
                interpretation_status: 'generic_unsupported_fallback',
              },
            ],
          },
        },
      },
    });

    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
    });
    await waitFor(() => expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled());
    fireEvent.change(screen.getByPlaceholderText('e.g., London, UK'), {
      target: { value: 'Jerusalem' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Inspect' }));

    expect(await screen.findByText('Experimental extension')).toBeInTheDocument();
    expect(screen.getByText('Generic fallback')).toBeInTheDocument();
    expect(screen.getByText(/separately curated experimental extension/i)).toBeInTheDocument();
    expect(screen.getByText(/No dedicated body–angle interpretation/i)).toBeInTheDocument();
  });

  it('preserves atlas target identity and ignores an older inspection response', async () => {
    const firstRequest = createDeferred();
    const secondRequest = createDeferred();
    astroClockApiMock.startAstrocartographyAtlasSearch.mockResolvedValue({
      success: true,
      data: {
        session_id: 'session-targets',
        progress: { ready: true, failed: false, percent: 1, stage: 'ready' },
      },
    });
    astroClockApiMock.getAstrocartographyAtlasSearchResult.mockResolvedValue({
      success: true,
      data: {
        ready: true,
        result: {
          birth_time: { status: 'certified', ranking_eligible: true },
          atlas: { candidate_count: 2, shortlisted_count: 2, resolution: { label: 'Standard' } },
          results: [
            {
              target: { label: 'Alpha City', query: 'Alpha City', latitude: 10, longitude: 20 },
              atlas_city: { geonameid: 101, country_name: 'Alpha' },
              rank: 1,
              astrology_rank: 1,
              display_rank: 1,
              selection_order: 1,
              location_score: { score: 80, rank_stability: { status: 'stable', detail: 'Held in sensitivity checks.' } },
              geographic_group: { label: 'Alpha City area', selection_pass: 'distinct_region' },
            },
            {
              target: { label: 'Beta City', query: 'Beta City', latitude: 20, longitude: 30 },
              atlas_city: { geonameid: 202, country_name: 'Beta' },
              rank: 3,
              astrology_rank: 3,
              display_rank: 2,
              selection_order: 2,
              location_score: {
                score: 60,
                rank_stability: {
                  status: 'moderate',
                  rank_interval: { best: 2, worst: 4 },
                  candidate_count: 21,
                  scope_candidate_count: 100,
                  bounded_scope: true,
                  scope_coverage: 0.21,
                },
              },
            },
          ],
        },
      },
    });
    astroClockApiMock.getAstrocartographyLocation.mockImplementation((options) => (
      options?.target?.candidate_id === 'geonames:101' ? firstRequest.promise : secondRequest.promise
    ));

    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
      initialGoalOptions: [{ id: 'career_public_profile', label: 'Career Public Profile', goal_family: 'career' }],
    });
    await waitFor(() => expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled());
    fireEvent.change(screen.getByDisplayValue('General inspection'), {
      target: { value: 'career_public_profile' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Rank Candidate Cities' }));

    expect(await screen.findByText('Astrology rank #1')).toBeInTheDocument();
    expect(screen.getAllByText('Alpha City').length).toBeGreaterThan(0);
    expect(screen.getByText('Astrology rank #3')).toBeInTheDocument();
    expect(screen.getByText('Regional display order #2')).toBeInTheDocument();
    expect(screen.queryByText('2. Beta City')).not.toBeInTheDocument();
    expect(screen.getByText(/evaluated among 21 of 100 candidates/i)).toBeInTheDocument();
    expect(screen.getByText('Regional group: Alpha City area')).toBeInTheDocument();
    const inspectButtons = screen.getAllByRole('button', { name: 'Inspect' });
    fireEvent.click(inspectButtons[1]);
    await waitFor(() => expect(astroClockApiMock.getAstrocartographyLocation).toHaveBeenCalledTimes(1));
    const firstCall = astroClockApiMock.getAstrocartographyLocation.mock.calls[0][0];
    expect(firstCall.target).toEqual(expect.objectContaining({
      candidate_id: 'geonames:101',
      latitude: 10,
      longitude: 20,
    }));

    fireEvent.click(inspectButtons[2]);
    await waitFor(() => expect(astroClockApiMock.getAstrocartographyLocation).toHaveBeenCalledTimes(2));
    expect(firstCall.signal.aborted).toBe(true);
    const secondCall = astroClockApiMock.getAstrocartographyLocation.mock.calls[1][0];
    expect(secondCall.target).toEqual(expect.objectContaining({
      candidate_id: 'geonames:202',
      latitude: 20,
      longitude: 30,
    }));

    await act(async () => {
      secondRequest.resolve({
        success: true,
        data: {
          target: { candidate_id: 'geonames:202', label: 'Beta City', query: 'Beta City', latitude: 20, longitude: 30 },
          birth_time: { status: 'certified', ranking_eligible: true },
          natal: { reading: { signal_score: 60, nearest_lines: [] } },
        },
      });
      await Promise.resolve();
    });
    expect((await screen.findAllByText('20.0000, 30.0000')).length).toBeGreaterThan(0);

    await act(async () => {
      firstRequest.resolve({
        success: true,
        data: {
          target: { candidate_id: 'geonames:101', label: 'Alpha City', query: 'Alpha City', latitude: 10, longitude: 20 },
          birth_time: { status: 'certified', ranking_eligible: true },
          natal: { reading: { signal_score: 80, nearest_lines: [] } },
        },
      });
      await Promise.resolve();
    });
    expect(screen.getAllByText('20.0000, 30.0000').length).toBeGreaterThan(0);
  });

  it('keeps relocated and natal Local Space origins separate', async () => {
    astroClockApiMock.getAstrocartographyLocation.mockResolvedValue({
      success: true,
      data: {
        target: { candidate_id: 'target-1', label: 'Target City', query: 'Target City', latitude: 40, longitude: -73 },
        natal: {
          reading: { signal_score: 45, nearest_lines: [] },
          parans: {
            count: 2,
            items: [
              {
                id: 'paran-copy-a',
                canonical_event_id: 'event-shared',
                event_kind: 'paran-crossing-point',
                label: 'Repeated Paran',
                distance_km: 20,
                orb_deg: 0.5,
              },
              {
                id: 'paran-copy-b',
                canonical_event_id: 'event-shared',
                event_kind: 'paran-crossing-point',
                label: 'Repeated Paran',
                distance_km: 20,
                orb_deg: 0.5,
              },
            ],
          },
          intersections: {
            primary_crossings: [
              {
                id: 'crossing-a',
                canonical_event_id: 'event-shared',
                event_kind: 'angular-line-crossing',
                label: 'Shared Crossing',
                distance_km: 15,
              },
            ],
          },
          local_space: {
            origin_kind: 'birthplace',
            origin: { label: 'Birthplace', latitude: 31.78, longitude: 35.23 },
            visible_count: 1,
            hidden_count: 0,
            rays: [{ id: 'natal-ray', label: 'Sun East', above_horizon: true, segments: [] }],
          },
        },
        relocation: {
          available: true,
          summary: {},
          provenance: {
            house_system_code: 'R',
          },
          local_space: {
            origin_kind: 'relocated_target',
            origin: { label: 'Target City', latitude: 40, longitude: -73 },
            visible_count: 1,
            hidden_count: 0,
            rays: [{ id: 'relocated-ray', label: 'Moon West', above_horizon: true, segments: [] }],
          },
        },
      },
    });

    await renderModal({
      snaps: [{ id: 'snap-1', label: 'Test Snap' }],
      activeSnapId: 'snap-1',
    });
    await waitFor(() => expect(astroClockApiMock.getAstrocartographyMap).toHaveBeenCalled());
    fireEvent.change(screen.getByPlaceholderText('e.g., London, UK'), {
      target: { value: 'Target City' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Inspect' }));
    expect((await screen.findAllByText('40.0000, -73.0000')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Repeated Paran')).toHaveLength(1);
    expect(screen.getAllByText('Shared Crossing')).toHaveLength(1);

    fireEvent.click(screen.getByRole('button', { name: 'Local Space' }));
    expect(screen.getAllByText('Relocated Local Space').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Target City').length).toBeGreaterThan(0);
    expect(screen.getByText('Regiomontanus (R)')).toBeInTheDocument();
    expect(screen.getByText(/Relocated house placements depend on this setting/i)).toBeInTheDocument();
    expect(screen.getByText(/Directional Local Space rays are shown separately/i)).toBeInTheDocument();

    const natalButtons = screen.getAllByRole('button', { name: 'Natal' });
    fireEvent.click(natalButtons[natalButtons.length - 1]);
    expect(screen.getAllByText('Natal Local Space').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Birthplace').length).toBeGreaterThan(0);
  });

  it('classifies ordinal strength, rank stability, and explicit birth-time eligibility', async () => {
    const {
      getAstrocartographyBirthTimeAssessment,
      getAstrocartographyOrdinal,
      getAstrocartographyRankStability,
    } = await import('../features/astroclock/AstrocartographyModal.jsx');

    expect(getAstrocartographyOrdinal({ score: 0 })).toBe('Insufficient');
    expect(getAstrocartographyOrdinal({ score: 20 })).toBe('Weak');
    expect(getAstrocartographyOrdinal({ score: 50 })).toBe('Mixed');
    expect(getAstrocartographyOrdinal({ score: 80 })).toBe('Strong');
    expect(getAstrocartographyOrdinal({ score: 80 }, { rankingEligible: false })).toBe('Insufficient');
    expect(getAstrocartographyRankStability({ rank_stability: 0.8 }).label).toBe('Stable');
    expect(getAstrocartographyRankStability({
      rank_stability: {
        status: 'moderate',
        rank_interval: { best: 2, worst: 5 },
        candidate_count: 21,
        scope_candidate_count: 100,
        bounded_scope: true,
        scope_coverage: 0.21,
      },
    })).toEqual(expect.objectContaining({
      label: 'Moderate',
      detail: 'Reported rank range 2–5 · evaluated among 21 of 100 candidates',
      boundedScope: true,
      candidateCount: 21,
      scopeCandidateCount: 100,
      scopeCoverage: 0.21,
    }));
    expect(getAstrocartographyBirthTimeAssessment({
      birth_time: {
        status: 'approximate',
        uncertainty_minutes: 20,
        ranking_eligible: false,
      },
    })).toEqual(expect.objectContaining({
      rankingEligible: false,
      uncertaintyLabel: '±20 min',
    }));
  });
});
