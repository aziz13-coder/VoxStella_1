import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const astroClockApiMock = vi.hoisted(() => ({
  listMundaneChartTypes: vi.fn(),
  resolveMundaneContext: vi.fn(),
  analyzeMundane: vi.fn(),
  listMundaneScanCatalog: vi.fn(),
  startMundaneScan: vi.fn(),
  getMundaneScanProgress: vi.fn(),
  getMundaneScanResult: vi.fn(),
  listWeatherCatalog: vi.fn(),
  listWeatherScanCatalog: vi.fn(),
  resolveWeatherContext: vi.fn(),
  analyzeWeather: vi.fn(),
  startWeatherScan: vi.fn(),
  getWeatherScanProgress: vi.fn(),
  getWeatherScanResult: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

import MundaneWorkspace from '../features/astroclock/MundaneWorkspace.jsx';
import MundaneScanWorkspace from '../features/astroclock/MundaneScanWorkspace.jsx';
import WeatherWorkspace from '../features/astroclock/WeatherWorkspace.jsx';

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const mundaneChartTypes = [
  {
    id: 'war_event',
    label: 'War Event',
    requires_polity: true,
    default_location_context_type: 'capital_chart',
    preferred_domain_ids: ['war_conflict', 'public_health'],
    supported_domain_ids: [],
    default_domain_id: 'war_conflict',
  },
];

const mundaneDomains = [
  { id: 'war_conflict', label: 'War Conflict' },
  { id: 'public_health', label: 'Public Health' },
];

const mundaneContextTypes = [
  { id: 'capital_chart', label: 'Capital Chart' },
];

const mundanePolities = [
  {
    id: 'france',
    label: 'France',
    capital: 'Paris, France',
    default_location: 'Paris, France',
    timezone: 'Europe/Paris',
    visibility_scope: 'national',
    national_charts: [{ id: 'france_chart', label: 'France 1958', status: 'preferred' }],
  },
  {
    id: 'united_states',
    label: 'United States',
    capital: 'Washington, DC, USA',
    default_location: 'Washington, DC, USA',
    timezone: 'America/New_York',
    visibility_scope: 'national',
    national_charts: [{ id: 'us_chart', label: 'United States 1776', status: 'preferred' }],
  },
];

const mundaneCatalog = {
  chart_types: mundaneChartTypes,
  domains: mundaneDomains,
  context_types: mundaneContextTypes,
  polities: mundanePolities,
};

const mundaneScanCatalog = {
  chart_types: mundaneChartTypes,
  domains: mundaneDomains,
  context_types: mundaneContextTypes,
  polities: mundanePolities,
  scan_modes: [{ id: 'spatial_scan', label: 'Spatial Scan' }],
  regions: [{ id: 'middle_east', label: 'Middle East' }],
  resolutions: [{ id: 'standard', label: 'Standard' }],
  default_resolution: 'standard',
  max_time_slices: 24,
  max_evaluated_cells: 160,
  scan_mode_limits: {
    spatial_scan: {
      max_time_slices: 24,
      max_evaluated_cells: 160,
      max_candidates: 32,
      default_candidate_limit: 6,
      default_time_step_hours: 6,
    },
  },
};

const mundaneScanCatalogWithSeries = {
  ...mundaneScanCatalog,
  scan_modes: [
    { id: 'spatial_scan', label: 'Spatial Scan' },
    { id: 'spatiotemporal_scan', label: 'Time Window Scan' },
  ],
  scan_mode_limits: {
    ...mundaneScanCatalog.scan_mode_limits,
    spatiotemporal_scan: {
      max_time_slices: 24,
      max_evaluated_cells: 160,
      max_candidates: 32,
      default_candidate_limit: 6,
      default_time_step_hours: 6,
    },
  },
};

const weatherFamilies = [
  { id: 'wind_event_pressure', label: 'Wind Event Pressure' },
  { id: 'flood_risk', label: 'Flood Risk' },
];

const weatherCatalog = {
  families: weatherFamilies,
};

const weatherScanCatalog = {
  families: weatherFamilies,
  regions: [{ id: 'global', label: 'Global' }],
  resolutions: [{ id: 'standard', label: 'Standard' }],
  default_resolution: 'standard',
  default_time_step_hours: 6,
  default_candidate_limit: 6,
  default_top_k: 8,
  max_time_slices: 120,
  max_evaluated_cells: 720,
  max_candidates: 20,
};

function getSection(title) {
  return screen.getByText(title).closest('section');
}

beforeEach(() => {
  Object.values(astroClockApiMock).forEach((mockFn) => mockFn.mockReset());
  astroClockApiMock.listMundaneChartTypes.mockResolvedValue({ success: true, data: mundaneCatalog });
  astroClockApiMock.listMundaneScanCatalog.mockResolvedValue({ success: true, data: mundaneScanCatalog });
  astroClockApiMock.listWeatherCatalog.mockResolvedValue({ success: true, data: weatherCatalog });
  astroClockApiMock.listWeatherScanCatalog.mockResolvedValue({ success: true, data: weatherScanCatalog });
  astroClockApiMock.getMundaneScanProgress.mockResolvedValue({
    success: true,
    data: { ready: false, failed: false, percent: 0.5, done: 1, total: 2, failures: 0 },
  });
  astroClockApiMock.getWeatherScanProgress.mockResolvedValue({
    success: true,
    data: { ready: false, failed: false, percent: 0.5, done: 1, total: 2, returned: 0 },
  });
});

describe('mundane and weather workspaces', () => {
  it('updates auto-seeded mundane polity defaults when the polity changes', async () => {
    render(<MundaneWorkspace open defaultHouseSystem="R" />);

    fireEvent.click(screen.getByRole('button', { name: 'Analysis' }));

    const politySelect = within(getSection('Polity')).getByRole('combobox');
    const referenceLocationInput = within(getSection('Context Overrides')).getByPlaceholderText('Reference location (optional)');
    const eventTimezoneInput = within(getSection('Event Overrides')).getByPlaceholderText('Event timezone (optional)');

    await waitFor(() => {
      expect(referenceLocationInput).toHaveValue('Paris, France');
      expect(eventTimezoneInput).toHaveValue('Europe/Paris');
    });

    fireEvent.change(politySelect, { target: { value: 'united_states' } });

    await waitFor(() => {
      expect(referenceLocationInput).toHaveValue('Washington, DC, USA');
      expect(eventTimezoneInput).toHaveValue('America/New_York');
    });
  });

  it('ignores stale mundane analysis responses after the form changes', async () => {
    const pendingAnalyze = deferred();
    astroClockApiMock.analyzeMundane.mockReturnValueOnce(pendingAnalyze.promise);

    render(<MundaneWorkspace open defaultHouseSystem="R" />);

    fireEvent.click(screen.getByRole('button', { name: 'Analysis' }));

    await waitFor(() => expect(within(getSection('Domain Lens')).getByRole('combobox')).toHaveValue('war_conflict'));

    fireEvent.click(screen.getByRole('button', { name: 'Analyze' }));

    const domainSelect = within(getSection('Domain Lens')).getByRole('combobox');
    fireEvent.change(domainSelect, { target: { value: 'public_health' } });

    pendingAnalyze.resolve({
      success: true,
      data: {
        context: { family: null },
        domain_assessment: { summary: 'Stale war-event summary', level: 'elevated', score: 18, raw_score: 18 },
        framework_layer: { items: [] },
        trigger_layer: { items: [] },
        activation_layer: { items: [] },
        doctrine: {},
        research: {},
      },
    });

    await waitFor(() => {
      expect(screen.queryByText('Stale war-event summary')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Analyze' })).toBeInTheDocument();
    });
  });

  it('locks mundane scan controls while a scan session is active', async () => {
    astroClockApiMock.startMundaneScan.mockResolvedValue({
      success: true,
      data: {
        session_id: 'mundane-scan-1',
        progress: { ready: false, failed: false, percent: 0.1, done: 0, total: 2, failures: 0 },
      },
    });

    render(<MundaneScanWorkspace open defaultHouseSystem="R" />);

    const eventAnchorSection = await waitFor(() => getSection('Fixed Event Anchor'));
    const [eventDateInput, eventTimeInput] = eventAnchorSection.querySelectorAll('input');

    fireEvent.change(eventDateInput, { target: { value: '2026-02-28' } });
    fireEvent.change(eventTimeInput, { target: { value: '03:00' } });
    fireEvent.click(screen.getByRole('button', { name: 'Run Scan' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Running Scan...' })).toBeDisabled());
    expect(within(getSection('Chart Type')).getByRole('combobox')).toBeDisabled();
    expect(within(getSection('Polity')).getByRole('combobox')).toBeDisabled();
  });

  it('does not render a dead top-cells toggle when mundane scan has only one output surface', async () => {
    astroClockApiMock.startMundaneScan.mockResolvedValueOnce({
      success: true,
      data: {
        session_id: 'mundane-scan-single-surface',
        progress: { ready: false, failed: false, percent: 0.4, done: 1, total: 2, failures: 0 },
      },
    });
    astroClockApiMock.getMundaneScanProgress.mockResolvedValueOnce({
      success: true,
      data: { ready: true, failed: false, percent: 1, done: 2, total: 2, failures: 0 },
    });
    astroClockApiMock.getMundaneScanResult.mockResolvedValueOnce({
      success: true,
      data: {
        ready: true,
        failed: false,
        result: {
          scan_mode: 'spatial_scan',
          region: { id: 'middle_east', label: 'Middle East' },
          resolution: { id: 'standard', label: 'Standard' },
          counts: {
            candidate_locations: 2,
            time_slices: 1,
            evaluated_cells: 2,
            kept_cells: 2,
            returned: 1,
            returned_places: 0,
            failures: 0,
          },
          default_output_view: 'cells',
          top_cells: [
            {
              rank: 1,
              location: { label: 'Tehran, Iran', country_name: 'Iran', timezone: 'Asia/Tehran' },
              datetime: '2026-02-28T03:00:00+03:30',
              scan_score: 31,
              raw_score: 33,
              delta_from_top: 0,
              scan_level: 'dominant',
              level: 'high',
              calibration: { coverage_tier: 'moderate', unique_case_count: 2 },
              research_flags: ['benchmark_backed'],
              relative_score_ratio: 1,
              matched_rules: [{ id: 'mars_angular', label: 'Mars angular' }],
            },
          ],
          results: [
            {
              rank: 1,
              location: { label: 'Tehran, Iran', country_name: 'Iran', timezone: 'Asia/Tehran' },
              datetime: '2026-02-28T03:00:00+03:30',
              scan_score: 31,
              raw_score: 33,
              delta_from_top: 0,
              scan_level: 'dominant',
              level: 'high',
            },
          ],
        },
      },
    });

    render(<MundaneScanWorkspace open defaultHouseSystem="R" />);

    const eventAnchorSection = await waitFor(() => getSection('Fixed Event Anchor'));
    const [eventDateInput, eventTimeInput] = eventAnchorSection.querySelectorAll('input');

    fireEvent.change(eventDateInput, { target: { value: '2026-02-28' } });
    fireEvent.change(eventTimeInput, { target: { value: '03:00' } });
    fireEvent.click(screen.getByRole('button', { name: 'Run Scan' }));

    await screen.findByRole('button', { name: /Select Tehran, Iran/i });
    expect(screen.queryByRole('button', { name: 'Top Cells' })).not.toBeInTheDocument();
  });

  it('syncs mundane top-cell selection into the inspector and breakout graph', async () => {
    astroClockApiMock.listMundaneScanCatalog.mockResolvedValueOnce({ success: true, data: mundaneScanCatalogWithSeries });
    astroClockApiMock.startMundaneScan.mockResolvedValueOnce({
      success: true,
      data: {
        session_id: 'mundane-scan-series',
        progress: { ready: false, failed: false, percent: 0.2, done: 1, total: 6, failures: 0 },
      },
    });
    astroClockApiMock.getMundaneScanProgress.mockResolvedValueOnce({
      success: true,
      data: { ready: true, failed: false, percent: 1, done: 6, total: 6, failures: 0 },
    });
    astroClockApiMock.getMundaneScanResult.mockResolvedValueOnce({
      success: true,
      data: {
        ready: true,
        failed: false,
        result: {
          scan_mode: 'spatiotemporal_scan',
          region: { id: 'global', label: 'Global' },
          resolution: { id: 'standard', label: 'Standard' },
          counts: {
            candidate_locations: 2,
            time_slices: 3,
            evaluated_cells: 6,
            kept_cells: 6,
            returned: 2,
            returned_places: 2,
            failures: 0,
          },
          default_output_view: 'cells',
          top_cells: [
            {
              rank: 1,
              location: { label: 'Tehran, Iran', country_name: 'Iran', timezone: 'Asia/Tehran' },
              datetime: '2026-02-28T06:00:00+03:30',
              scan_score: 51,
              raw_score: 55,
              delta_from_top: 0,
              scan_level: 'dominant',
              level: 'high',
              calibration: { coverage_tier: 'moderate', unique_case_count: 4 },
              research_flags: ['benchmark_backed'],
              relative_score_ratio: 1,
              matched_rules: [{ id: 'mars_angular', label: 'Mars angular' }],
            },
            {
              rank: 2,
              location: { label: 'Shanghai, China', country_name: 'China', timezone: 'Asia/Shanghai' },
              datetime: '2026-02-28T06:00:00+08:00',
              scan_score: 49,
              raw_score: 53,
              delta_from_top: 2,
              scan_level: 'co_leading',
              level: 'elevated',
              calibration: { coverage_tier: 'moderate', unique_case_count: 3 },
              research_flags: ['benchmark_backed'],
              relative_score_ratio: 0.96,
              matched_rules: [{ id: 'saturn_angular', label: 'Saturn angular' }],
            },
          ],
          top_places: [
            {
              rank: 1,
              location: { label: 'Tehran, Iran' },
              breakout_index: 55,
              breakout_kind: 'opening_break_candidate',
              peak_scan_score: 51,
              peak_datetime: '2026-02-28T06:00:00+03:30',
              peak_selection: 'single_peak',
            },
            {
              rank: 2,
              location: { label: 'Shanghai, China' },
              breakout_index: 53,
              breakout_kind: 'sustained_theater_candidate',
              peak_scan_score: 49,
              peak_datetime: '2026-02-28T06:00:00+08:00',
              peak_selection: 'single_peak',
            },
          ],
          results: [
            {
              rank: 1,
              location: { label: 'Tehran, Iran', country_name: 'Iran', timezone: 'Asia/Tehran' },
              datetime: '2026-02-28T06:00:00+03:30',
              scan_score: 51,
              raw_score: 55,
              delta_from_top: 0,
              scan_level: 'dominant',
              level: 'high',
            },
            {
              rank: 2,
              location: { label: 'Shanghai, China', country_name: 'China', timezone: 'Asia/Shanghai' },
              datetime: '2026-02-28T06:00:00+08:00',
              scan_score: 49,
              raw_score: 53,
              delta_from_top: 2,
              scan_level: 'co_leading',
              level: 'elevated',
            },
          ],
          series: {
            timeline: [
              '2026-02-28T00:00:00+03:30',
              '2026-02-28T06:00:00+03:30',
              '2026-02-28T12:00:00+03:30',
            ],
            places: [
              {
                location: { label: 'Tehran, Iran' },
                breakout_index: 55,
                breakout_kind: 'opening_break_candidate',
                peak_scan_score: 51,
                peak_datetime: '2026-02-28T06:00:00+03:30',
                peak_selection: 'single_peak',
                series: [
                  { datetime: '2026-02-28T00:00:00+03:30', scan_score: 20, absolute_score: 22, scan_level: 'active', absolute_level: 'elevated' },
                  { datetime: '2026-02-28T06:00:00+03:30', scan_score: 51, absolute_score: 55, scan_level: 'dominant', absolute_level: 'high' },
                  { datetime: '2026-02-28T12:00:00+03:30', scan_score: 35, absolute_score: 38, scan_level: 'leading', absolute_level: 'elevated' },
                ],
              },
              {
                location: { label: 'Shanghai, China' },
                breakout_index: 53,
                breakout_kind: 'sustained_theater_candidate',
                peak_scan_score: 49,
                peak_datetime: '2026-02-28T06:00:00+08:00',
                peak_selection: 'single_peak',
                series: [
                  { datetime: '2026-02-28T00:00:00+03:30', scan_score: 18, absolute_score: 20, scan_level: 'watch', absolute_level: 'quiet' },
                  { datetime: '2026-02-28T06:00:00+03:30', scan_score: 49, absolute_score: 53, scan_level: 'co_leading', absolute_level: 'elevated' },
                  { datetime: '2026-02-28T12:00:00+03:30', scan_score: 41, absolute_score: 45, scan_level: 'active', absolute_level: 'elevated' },
                ],
              },
            ],
            graph_places: [
              {
                location: { label: 'Tehran, Iran' },
                breakout_index: 55,
                breakout_kind: 'opening_break_candidate',
                peak_scan_score: 51,
                peak_datetime: '2026-02-28T06:00:00+03:30',
                peak_selection: 'single_peak',
                series: [
                  { datetime: '2026-02-28T00:00:00+03:30', scan_score: 20, absolute_score: 22, scan_level: 'active', absolute_level: 'elevated' },
                  { datetime: '2026-02-28T06:00:00+03:30', scan_score: 51, absolute_score: 55, scan_level: 'dominant', absolute_level: 'high' },
                  { datetime: '2026-02-28T12:00:00+03:30', scan_score: 35, absolute_score: 38, scan_level: 'leading', absolute_level: 'elevated' },
                ],
              },
              {
                location: { label: 'Shanghai, China' },
                breakout_index: 53,
                breakout_kind: 'sustained_theater_candidate',
                peak_scan_score: 49,
                peak_datetime: '2026-02-28T06:00:00+08:00',
                peak_selection: 'single_peak',
                series: [
                  { datetime: '2026-02-28T00:00:00+03:30', scan_score: 18, absolute_score: 20, scan_level: 'watch', absolute_level: 'quiet' },
                  { datetime: '2026-02-28T06:00:00+03:30', scan_score: 49, absolute_score: 53, scan_level: 'co_leading', absolute_level: 'elevated' },
                  { datetime: '2026-02-28T12:00:00+03:30', scan_score: 41, absolute_score: 45, scan_level: 'active', absolute_level: 'elevated' },
                ],
              },
            ],
            breakout_candidates: [
              { rank: 1, location: { label: 'Tehran, Iran' }, breakout_index: 55, breakout_kind: 'opening_break_candidate', peak_scan_score: 51, peak_datetime: '2026-02-28T06:00:00+03:30', peak_selection: 'single_peak' },
              { rank: 2, location: { label: 'Shanghai, China' }, breakout_index: 53, breakout_kind: 'sustained_theater_candidate', peak_scan_score: 49, peak_datetime: '2026-02-28T06:00:00+08:00', peak_selection: 'single_peak' },
            ],
            series_overview: {
              timeline_points: 3,
              place_count: 2,
              top_breakout_location: { label: 'Tehran, Iran' },
              top_peak_location: { label: 'Tehran, Iran' },
            },
          },
        },
      },
    });

    render(<MundaneScanWorkspace open defaultHouseSystem="R" />);

    const controlsSection = await waitFor(() => getSection('Scan Controls'));
    const [scanModeSelect] = within(controlsSection).getAllByRole('combobox');
    fireEvent.change(scanModeSelect, { target: { value: 'spatiotemporal_scan' } });

    const timeWindowSection = await waitFor(() => getSection('Time Window'));
    const [startDateInput, startTimeInput, endDateInput, endTimeInput] = timeWindowSection.querySelectorAll('input');
    fireEvent.change(startDateInput, { target: { value: '2026-02-28' } });
    fireEvent.change(startTimeInput, { target: { value: '00:00' } });
    fireEvent.change(endDateInput, { target: { value: '2026-02-28' } });
    fireEvent.change(endTimeInput, { target: { value: '12:00' } });

    fireEvent.click(screen.getByRole('button', { name: 'Run Scan' }));

    const shanghaiRow = await screen.findByRole('button', { name: /Select Shanghai, China/i });
    const inspectorAside = screen.getByText('Scan inspector').closest('aside');
    expect(inspectorAside).not.toBeNull();

    fireEvent.click(shanghaiRow);

    await waitFor(() => {
      expect(within(inspectorAside).getByText('Shanghai, China')).toBeInTheDocument();
      expect(within(inspectorAside).getByText(/selected_candidate/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole('button', { name: 'Break Graph' })[0]);

    await waitFor(() => {
      expect(within(inspectorAside).getByText('Shanghai, China')).toBeInTheDocument();
      expect(within(inspectorAside).getByText(/selected_breakout_place/i)).toBeInTheDocument();
    });
  });

  it('ignores stale weather analysis responses after the family changes', async () => {
    const pendingAnalyze = deferred();
    astroClockApiMock.analyzeWeather.mockReturnValueOnce(pendingAnalyze.promise);

    render(<WeatherWorkspace open defaultHouseSystem="R" />);

    fireEvent.click(screen.getByRole('button', { name: 'Analysis' }));

    await waitFor(() => expect(within(getSection('Weather Family')).getByRole('combobox')).toHaveValue('wind_event_pressure'));

    fireEvent.click(screen.getByRole('button', { name: 'Analyze' }));

    const familySelect = within(getSection('Weather Family')).getByRole('combobox');
    fireEvent.change(familySelect, { target: { value: 'flood_risk' } });

    pendingAnalyze.resolve({
      success: true,
      data: {
        context: { family: { id: 'wind_event_pressure' } },
        family_assessment: { summary: 'Stale wind-event summary', level: 'active', score: 22, signals: {} },
        framework_layer: { items: [] },
        trigger_layer: { items: [] },
        locality_layer: { items: [] },
        doctrine: {},
        research: {},
      },
    });

    await waitFor(() => {
      expect(screen.queryByText('Stale wind-event summary')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Analyze' })).toBeInTheDocument();
    });
  });

  it('renders the backend weather analysis payload without recomputing the result', async () => {
    astroClockApiMock.analyzeWeather.mockResolvedValueOnce({
      success: true,
      data: {
        context: {
          family: { id: 'wind_event_pressure', label: 'Wind Event Pressure', status: 'seed_runtime' },
          event_context: {
            forecast_datetime: '2026-04-12T12:00:00+00:00',
            location: 'Miami, Florida, USA',
            timezone: 'America/New_York',
          },
          chart_resolution: {
            primary_chart: {
              label: 'Forecast Chart',
              computed_datetime: '2026-04-12T12:00:00+00:00',
              location: 'Miami, Florida, USA',
            },
            supporting_charts: [
              {
                kind: 'spring_ingress',
                label: 'Spring Ingress',
                computed_datetime: '2026-03-20T09:00:00+00:00',
                location: 'Miami, Florida, USA',
              },
            ],
          },
          research_flags: ['benchmark_backed'],
        },
        family_assessment: {
          summary: 'Backend wind-event summary',
          level: 'active',
          score: 42,
          matched_rules: [
            {
              id: 'target_zone_mercury_uranus',
              label: 'Target-zone intersection: Mercury x Uranus',
              summary: 'Backend target-zone summary',
              score: 12,
              combined_distance_deg: 2,
            },
          ],
          signals: {
            framework_count: 3,
            trigger_count: 4,
            locality_count: 5,
          },
        },
        framework_layer: {
          label: 'Seasonal Framework',
          items: [
            {
              id: 'spring_ingress',
              label: 'Spring Ingress',
              summary: 'Broader weather backdrop from the backend.',
            },
          ],
        },
        trigger_layer: {
          label: 'Lunar Trigger',
          items: [
            {
              id: 'full_moon',
              label: 'Full Moon',
              summary: 'Short-term trigger from the backend.',
            },
          ],
        },
        locality_layer: {
          label: 'Locality Proxy',
          items: [
            {
              id: 'forecast_chart_target_zones',
              label: 'Target-zone intersection: Mercury x Uranus',
              summary: 'Tight horizon/meridian proxy from the backend.',
              score: 12,
            },
          ],
        },
        doctrine: {
          sources: [
            {
              title: 'Predicting Weather Events with Astrology',
              scope_note: 'Backend doctrine source note.',
            },
          ],
          notes: [
            {
              label: 'Locality Proxy Only',
              summary: 'Backend doctrine note.',
            },
          ],
        },
        research: {
          runtime_scope: 'seed_weather_runtime',
          calibration: {
            coverage_tier: 'supported',
            unique_case_count: 4,
            dataset_row_count: 6,
            source_count: 3,
          },
          flags: ['benchmark_backed'],
          limitations: ['Backend limitation text.'],
        },
      },
    });

    render(<WeatherWorkspace open defaultHouseSystem="R" />);

    fireEvent.click(screen.getByRole('button', { name: 'Analysis' }));
    await waitFor(() => expect(within(getSection('Weather Family')).getByRole('combobox')).toHaveValue('wind_event_pressure'));

    fireEvent.click(screen.getByRole('button', { name: 'Analyze' }));

    await screen.findByText('Backend wind-event summary');
    expect(screen.getAllByText('Wind Event Pressure').length).toBeGreaterThan(0);
    expect(screen.getByText('Forecast Chart')).toBeInTheDocument();
    expect(screen.getAllByText('Miami, Florida, USA').length).toBeGreaterThan(0);
    expect(screen.getByText('Seasonal Framework')).toBeInTheDocument();
    expect(screen.getByText('Broader weather backdrop from the backend.')).toBeInTheDocument();
    expect(screen.getByText('Lunar Trigger')).toBeInTheDocument();
    expect(screen.getByText('Short-term trigger from the backend.')).toBeInTheDocument();
    expect(screen.getAllByText('Target-zone intersection: Mercury x Uranus').length).toBeGreaterThan(1);
    expect(screen.getByText('Predicting Weather Events with Astrology')).toBeInTheDocument();
    expect(screen.getByText('Backend doctrine note.')).toBeInTheDocument();
    expect(screen.getByText('Dataset rows: 6')).toBeInTheDocument();
    expect(screen.getByText('Source breadth: 3')).toBeInTheDocument();
    expect(screen.getByText('Backend limitation text.')).toBeInTheDocument();
  });

  it('locks weather scan controls while a scan session is active', async () => {
    astroClockApiMock.startWeatherScan.mockResolvedValue({
      success: true,
      data: {
        session_id: 'weather-scan-1',
        progress: { ready: false, failed: false, percent: 0.1, done: 0, total: 3, returned: 0 },
      },
    });

    render(<WeatherWorkspace open defaultHouseSystem="R" />);

    const placeInput = await screen.findByPlaceholderText('Place');
    const placeSection = placeInput.closest('section');
    expect(placeSection).not.toBeNull();
    fireEvent.change(placeInput, { target: { value: 'Miami, Florida, USA' } });

    const timeWindowSection = getSection('Time Window');
    const [startDateInput, startTimeInput, endDateInput, endTimeInput] = timeWindowSection.querySelectorAll('input');
    fireEvent.change(startDateInput, { target: { value: '2026-04-12' } });
    fireEvent.change(startTimeInput, { target: { value: '00:00' } });
    fireEvent.change(endDateInput, { target: { value: '2026-04-12' } });
    fireEvent.change(endTimeInput, { target: { value: '12:00' } });

    fireEvent.click(screen.getByRole('button', { name: 'Run Weather Scan' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Scanning...' })).toBeDisabled());
    expect(within(getSection('Weather Family')).getByRole('combobox')).toBeDisabled();
    expect(within(placeSection).getByPlaceholderText('Place')).toBeDisabled();
  });

  it('renders the completed weather scan as a matrix-first pressure table', async () => {
    astroClockApiMock.startWeatherScan.mockResolvedValueOnce({
      success: true,
      data: {
        session_id: 'weather-scan-matrix',
        progress: { ready: false, failed: false, percent: 0.25, done: 2, total: 8, returned: 0 },
      },
    });
    astroClockApiMock.getWeatherScanProgress.mockResolvedValueOnce({
      success: true,
      data: { ready: true, failed: false, percent: 1, done: 8, total: 8, returned: 3 },
    });
    astroClockApiMock.getWeatherScanResult.mockResolvedValueOnce({
      success: true,
      data: {
        ready: true,
        failed: false,
        result: {
          scope: { scan_scope: 'region_timeline', resolution: 'standard' },
          counts: {
            candidate_count: 3,
            time_slices: 3,
            evaluated: 8,
            returned: 3,
          },
          calibration: {
            coverage_tier: 'benchmark_backed',
            unique_case_count: 4,
          },
          results: [
            {
              rank: 1,
              location: { label: 'Istanbul, Turkiye' },
              datetime: '2026-02-10T08:00:00+03:00',
              score: 38,
              level: 'active',
            },
          ],
          series: {
            timeline: [
              '2026-02-10T02:00:00+03:00',
              '2026-02-10T08:00:00+03:00',
              '2026-02-10T14:00:00+03:00',
            ],
            places: [
              {
                location: { label: 'Istanbul, Turkiye' },
                candidate_kind: 'opening_break_candidate',
                peak_score: 38,
                peak_datetime: '2026-02-10T08:00:00+03:00',
                peak_window_start_datetime: '2026-02-10T02:00:00+03:00',
                peak_window_end_datetime: '2026-02-10T14:00:00+03:00',
                peak_selection: 'peak_plateau',
                series: [
                  { datetime: '2026-02-10T02:00:00+03:00', score: 38, level: 'active', scan_level: 'dominant' },
                  { datetime: '2026-02-10T08:00:00+03:00', score: 38, level: 'active', scan_level: 'co_leading' },
                  { datetime: '2026-02-10T14:00:00+03:00', score: 36, level: 'active', scan_level: 'leading' },
                ],
              },
              {
                location: { label: 'Kinshasa, DR Congo' },
                candidate_kind: 'sustained_window',
                peak_score: 21,
                peak_datetime: '2026-02-10T08:00:00+03:00',
                peak_window_start_datetime: '2026-02-10T08:00:00+03:00',
                peak_window_end_datetime: '2026-02-10T08:00:00+03:00',
                peak_selection: 'single_peak',
                series: [
                  { datetime: '2026-02-10T02:00:00+03:00', score: 21, level: 'quiet', scan_level: 'watch' },
                  { datetime: '2026-02-10T08:00:00+03:00', score: 21, level: 'quiet', scan_level: 'watch' },
                  { datetime: '2026-02-10T14:00:00+03:00', score: 21, level: 'quiet', scan_level: 'watch' },
                ],
              },
              {
                location: { label: 'Lagos, Nigeria' },
                candidate_kind: 'sustained_window',
                peak_score: 16,
                peak_datetime: '2026-02-10T14:00:00+03:00',
                peak_window_start_datetime: '2026-02-10T14:00:00+03:00',
                peak_window_end_datetime: '2026-02-10T14:00:00+03:00',
                peak_selection: 'single_peak',
                series: [
                  { datetime: '2026-02-10T02:00:00+03:00', score: 16, level: 'quiet', scan_level: 'active' },
                  { datetime: '2026-02-10T08:00:00+03:00', score: 16, level: 'quiet', scan_level: 'co_leading' },
                  { datetime: '2026-02-10T14:00:00+03:00', score: 16, level: 'quiet', scan_level: 'leading' },
                ],
              },
            ],
            series_overview: {
              timeline_points: 3,
              place_count: 3,
              top_candidate_location: { label: 'Istanbul, Turkiye' },
              top_candidate_datetime: '2026-02-10T08:00:00+03:00',
              top_peak_location: { label: 'Istanbul, Turkiye' },
              top_peak_datetime: '2026-02-10T08:00:00+03:00',
            },
          },
        },
      },
    });

    render(<WeatherWorkspace open defaultHouseSystem="R" />);

    const familySelect = await waitFor(() => within(getSection('Weather Family')).getByRole('combobox'));
    fireEvent.change(familySelect, { target: { value: 'wind_event_pressure' } });

    fireEvent.click(screen.getByRole('button', { name: 'Region' }));
    const regionSection = screen.getByRole('heading', { name: 'Region' }).closest('section');
    expect(regionSection).not.toBeNull();
    fireEvent.change(within(regionSection).getAllByRole('combobox')[0], { target: { value: 'global' } });

    const timeWindowSection = getSection('Time Window');
    const [startDateInput, startTimeInput, endDateInput, endTimeInput] = timeWindowSection.querySelectorAll('input');
    fireEvent.change(startDateInput, { target: { value: '2026-02-10' } });
    fireEvent.change(startTimeInput, { target: { value: '02:00' } });
    fireEvent.change(endDateInput, { target: { value: '2026-02-10' } });
    fireEvent.change(endTimeInput, { target: { value: '14:00' } });

    fireEvent.click(screen.getByRole('button', { name: 'Run Weather Scan' }));

    await screen.findByText('Location · Peak Window');
    expect(screen.getAllByText('Istanbul, Turkiye').length).toBeGreaterThan(0);
    expect(screen.getByText('Location · Peak Window')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Matrix' }).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Peak window').length).toBeGreaterThan(0);
    expect(screen.getAllByTitle(/Dominant/i).length).toBeGreaterThan(0);
    expect(screen.getAllByTitle(/Co-leading/i).length).toBeGreaterThan(0);
    expect(screen.getAllByTitle(/Leading/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText('W').length).toBeGreaterThan(0);
  });
});
