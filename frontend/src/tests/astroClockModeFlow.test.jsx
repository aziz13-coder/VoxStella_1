import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';

const astroClockApiMock = vi.hoisted(() => ({
  getDashboard: vi.fn(),
  getPlanetaryHours: vi.fn(),
  getForensic: vi.fn(),
  setMode: vi.fn(),
  createStream: vi.fn(),
  listSnaps: vi.fn(),
  createSnap: vi.fn(),
  deleteSnap: vi.fn(),
}));

const transitsModalMock = vi.hoisted(() => ({
  props: [],
}));

const synastryModalMock = vi.hoisted(() => ({
  props: [],
}));

const astrocartographyModalMock = vi.hoisted(() => ({
  props: [],
}));

vi.mock('leaflet', () => {
  const Default = { mergeOptions: vi.fn() };
  return {
    default: { Icon: { Default } },
    Icon: { Default },
  };
});

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  Marker: ({ children }) => <div>{children}</div>,
  Popup: ({ children }) => <div>{children}</div>,
  Polyline: () => null,
  Circle: () => null,
  CircleMarker: ({ children }) => <div>{children}</div>,
  GeoJSON: () => null,
  Polygon: () => null,
  useMapEvents: () => ({}),
  useMap: () => ({ setView: vi.fn() }),
}));

vi.mock('../components/wheel/SketchWheel', () => ({
  default: () => <div data-testid="sketch-wheel" />,
}));

vi.mock('../features/astroclock/ReceptionsTile.jsx', () => ({
  default: () => <div data-testid="receptions-tile" />,
}));

vi.mock('../features/astroclock/MetricsTile.jsx', () => ({
  default: () => <div data-testid="metrics-tile" />,
}));

vi.mock('../features/astroclock/DegreeHitsTile.jsx', () => ({
  default: () => <div data-testid="degree-hits-tile" />,
}));

vi.mock('../features/astroclock/TraitProfileModal.jsx', () => ({
  default: () => null,
}));

vi.mock('../features/astroclock/SynastryModal.jsx', () => ({
  default: (props) => {
    synastryModalMock.props.push(props);
    return props?.open ? <div data-testid="synastry-modal" /> : null;
  },
}));

vi.mock('../features/astroclock/TransitsModal.jsx', () => ({
  default: (props) => {
    transitsModalMock.props.push(props);
    return props?.open ? <div data-testid="transits-modal" /> : null;
  },
}));

vi.mock('../features/astroclock/ElectionModal.jsx', () => ({
  default: () => null,
}));

vi.mock('../features/astroclock/AstrocartographyModal.jsx', () => ({
  default: (props) => {
    astrocartographyModalMock.props.push(props);
    return props?.open ? <div data-testid="astrocartography-modal" /> : null;
  },
}));

vi.mock('../features/astroclock/ResearchMode.jsx', () => ({
  default: () => null,
}));

vi.mock('../features/astroclock/AspectAnalysisModal.jsx', () => ({
  default: () => null,
}));

vi.mock('../features/astroclock/CompassTile.jsx', () => ({
  default: () => <div data-testid="compass-tile" />,
}));

vi.mock('../features/astroclock/NamePromptModal.jsx', () => ({
  default: ({ open, onSubmit }) => (
    open ? <button type="button" onClick={() => onSubmit?.('Test Subject')}>Mock Submit Prompt</button> : null
  ),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

import AstroClock from '../features/astroclock/AstroClock.jsx';
import { clearAstroClockWarmState } from '../features/astroclock/astroClockViewState.mjs';

function makeDashboard({
  timestamp = '2026-03-08T10:00:00Z',
  location = 'Jerusalem, Israel',
  timezone = 'Asia/Jerusalem',
  timezoneLabel = timezone,
} = {}) {
  return {
    success: true,
    data: {
      timestamp,
      location,
      timezone,
      timezone_label: timezoneLabel,
      planets: [],
      moon: null,
      moon_timeline: null,
      solar_conditions: [],
      tightest_aspect: null,
      top_aspects: [],
      fixed_star_hits: [],
      arabic_parts: {},
      sect: null,
      dispositors: {},
      cusp_aspects: {},
      house_cusps: Array.from({ length: 12 }, (_, i) => i * 30),
      house_rulers: {},
      special_degrees: [],
      metrics: {},
      morin_aspects: [],
      morin_antiscia: [],
      morin_contra_antiscia: [],
      morin_combustion: [],
      morin_patterns: {},
    },
  };
}

const hoursResponse = {
  success: true,
  data: {
    current_hour: { ruling_planet: 'Sun' },
    hours: [],
  },
};

function makeForensicPayload() {
  return {
    success: true,
    timestamp: '1968-04-04T18:01:00',
    location: 'Memphis, Tennessee',
    timezone: 'America/Chicago',
    moon_timeline: { in_voc: false },
    features: {
      house_cusps: [180, 210, 240, 270, 300, 330, 0, 30, 60, 90, 120, 150],
      house_rulers: { 1: 'Venus', 4: 'Saturn', 7: 'Mars', 10: 'Moon' },
      houses: {
        first_ruler: 'Venus',
        seventh_ruler: 'Mars',
      },
      planets: {
        Venus: { sign: 'Pisces', house: 6, dignity_score: 6, angular: false, longitude: 355.18, degree_in_sign: 25.18 },
        Moon: { sign: 'Cancer', house: 9, dignity_score: 3, angular: false, longitude: 92.41, degree_in_sign: 2.41, mute_sign: false },
        Mars: { sign: 'Taurus', house: 11, dignity_score: 0, angular: false, longitude: 33.0, degree_in_sign: 3.0 },
        Mercury: { sign: 'Pisces', house: 6, dignity_score: -2, angular: false, longitude: 340.0, degree_in_sign: 10.0, mute_sign: true },
        Saturn: { sign: 'Aries', house: 10, dignity_score: -1, angular: true, longitude: 15.0, degree_in_sign: 15.0 },
        Sun: { sign: 'Aries', house: 7, dignity_score: 0, angular: true, longitude: 14.0, degree_in_sign: 14.0 },
      },
      aspects: {
        Mars_to_Moon: { type: 'sextile', applying: true, orb: 3.47 },
        Moon_to_Mars: { type: 'sextile', applying: true, orb: 3.47 },
        Venus_to_Mars: { type: 'sextile', applying: false, orb: 2.1 },
        Mercury_to_Neptune: { type: 'conjunction', applying: false, orb: 1.2 },
      },
      fixed_stars_list: [],
    },
    findings: [
      {
        title: 'Life/death overlap points to violence or homicide',
        category: 'Violence',
        rationale: 'When the victim ruler also rules death matters or falls into hidden/death houses, violence or homicide becomes a primary forensic direction.',
      },
      {
        title: '1st ruler also rules the 8th',
        category: 'Houses',
        rationale: 'Overlap of life and death rulerships strengthens mortality themes in the case chart.',
      },
      {
        title: 'Malefic contrary to sect (angular)',
        category: 'Stressors',
        rationale: 'An angular out-of-sect malefic pushes the event toward harsh, destabilizing outcomes.',
      },
      {
        title: 'Friend or close associate axis is active',
        category: 'Associates',
        rationale: 'The chart activates acquaintance and associate channels rather than purely domestic ones.',
      },
      {
        title: 'Public or authority axis is foregrounded',
        category: 'Public',
        rationale: 'Angular public/authority signatures make the event socially visible and institutionally important.',
      },
      {
        title: 'Mercury in a mute sign',
        category: 'Deception',
        rationale: 'Mute-sign Mercury can point to withheld speech, obscured testimony, or communication gaps.',
      },
    ],
    categories: {
      Associates: 1,
      Deception: 1,
      Houses: 1,
      Public: 1,
      Stressors: 1,
      Violence: 1,
    },
    dominance: {
      planets: {
        Saturn: { score: 89, level: 'Extremely Dominant' },
        Sun: { score: 89, level: 'Extremely Dominant' },
      },
    },
    relationship_star_hits: {},
    receptions: { mutual: [], top_unilateral: [] },
    light_mediation: {},
    planetary_meanings: {},
    house_meanings: {},
    degree_special: {},
    ic_sign_meanings: {},
    ic_ruler_house_meanings: {},
    ic_planet_in_4th: {},
    perpetrator_profiles: {},
  };
}

function makeShinzoAbeForensicPayload() {
  const payload = makeForensicPayload();
  return {
    ...payload,
    timestamp: '2022-07-08T11:30:00',
    location: 'Nara, Japan',
    timezone: 'Asia/Tokyo',
    categories: {
      Deception: 3,
      'Degree Signatures': 1,
      Headwinds: 1,
      Houses: 1,
      Public: 1,
      Stressors: 1,
      Violence: 2,
    },
    findings: [
      {
        title: 'Moon in Via Combusta',
        category: 'Degree Signatures',
        rationale: 'Traditional caution when the Moon is between 15° Libra and 15° Scorpio.',
      },
      {
        title: 'Life/death overlap points to violence or homicide',
        category: 'Violence',
        rationale: 'When the victim ruler also rules death matters or falls into hidden/death houses, violence or homicide becomes a primary forensic direction.',
      },
      {
        title: '1st ruler also rules the 8th',
        category: 'Houses',
        rationale: 'Overlap of life (1st) and death (8th) rulers amplifies mortality themes.',
      },
      {
        title: 'Malefic contrary to sect (angular)',
        category: 'Stressors',
        rationale: 'Angular malefic contrary to sect increases friction.',
      },
      {
        title: 'Moon under death pressure',
        category: 'Violence',
        rationale: 'Moon pressure in death/end-matter houses or under hard malefic attack often describes violence, homicide, or acute bodily danger.',
      },
      {
        title: 'Moon applying to malefic by hard aspect',
        category: 'Headwinds',
        rationale: 'Applying hard aspect from the Moon to malefic signals near-term friction.',
      },
      {
        title: 'Public or authority axis is foregrounded',
        category: 'Public',
        rationale: 'A strong 10th-house or solar signature tied to violence/hidden-house pressure points to an authority, public, or celebrity-linked case.',
      },
      {
        title: 'Mercury in a mute sign',
        category: 'Deception',
        rationale: 'Silence or refusal to speak plainly (Cancer, Scorpio, Pisces).',
      },
    ],
  };
}

describe('AstroClock mode flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearAstroClockWarmState();
    transitsModalMock.props = [];
    synastryModalMock.props = [];
    astrocartographyModalMock.props = [];
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    Object.defineProperty(window, 'IS_PACKAGED', {
      configurable: true,
      writable: true,
      value: undefined,
    });
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      writable: true,
      value: {
        openExternal: vi.fn(),
      },
    });
    global.localStorage = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    };
    astroClockApiMock.getDashboard.mockResolvedValue(makeDashboard());
    astroClockApiMock.getPlanetaryHours.mockResolvedValue(hoursResponse);
    astroClockApiMock.getForensic.mockResolvedValue({ success: true, features: {}, moon_timeline: null });
    astroClockApiMock.setMode.mockResolvedValue({ success: true });
    astroClockApiMock.createStream.mockResolvedValue(null);
    astroClockApiMock.listSnaps.mockResolvedValue({ success: true, items: [] });
    astroClockApiMock.createSnap.mockResolvedValue({ success: true });
    astroClockApiMock.deleteSnap.mockResolvedValue({ success: true });
  });

  it('freezes the current chart when Manual is clicked so the controls stay coherent', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2026-03-08T10:00:00Z',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        houseSystem: 'R',
      }));
    });

    const dateInput = document.querySelector('input[type="date"]');
    const timeInput = document.querySelector('input[type="time"]');
    const locationInput = document.querySelector('input[type="text"][placeholder="e.g., London, UK"]');

    expect(dateInput?.value).toBe('2026-03-08');
    expect(timeInput?.value).toBe('12:00');
    expect(locationInput?.value).toBe('Jerusalem, Israel');
  });

  it('keeps mode toggles to a single dashboard and hours refresh per transition', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledTimes(1);
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(1);
      expect(astroClockApiMock.getPlanetaryHours).toHaveBeenCalledTimes(1);
    });

    expect(astroClockApiMock.setMode.mock.invocationCallOrder[0]).toBeLessThan(
      astroClockApiMock.getDashboard.mock.invocationCallOrder[0]
    );
    expect(astroClockApiMock.setMode.mock.invocationCallOrder[0]).toBeLessThan(
      astroClockApiMock.getPlanetaryHours.mock.invocationCallOrder[0]
    );

    expect(astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0]).toMatchObject({
      mode: 'manual',
      datetime: '2026-03-08T10:00:00Z',
      location: 'Jerusalem, Israel',
    });
    expect(astroClockApiMock.getPlanetaryHours.mock.calls.at(-1)?.[0]).toMatchObject({
      mode: 'manual',
      datetime: '2026-03-08T10:00:00Z',
      location: 'Jerusalem, Israel',
    });

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    fireEvent.click(screen.getByRole('button', { name: 'Realtime' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledTimes(1);
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(1);
      expect(astroClockApiMock.getPlanetaryHours).toHaveBeenCalledTimes(1);
    });

    expect(astroClockApiMock.setMode.mock.invocationCallOrder[0]).toBeLessThan(
      astroClockApiMock.getDashboard.mock.invocationCallOrder[0]
    );
    expect(astroClockApiMock.setMode.mock.invocationCallOrder[0]).toBeLessThan(
      astroClockApiMock.getPlanetaryHours.mock.invocationCallOrder[0]
    );

    expect(astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0]).toMatchObject({
      mode: 'realtime',
      houseSystem: 'R',
    });
    expect(astroClockApiMock.getPlanetaryHours.mock.calls.at(-1)?.[0]).toMatchObject({
      mode: 'realtime',
      houseSystem: 'R',
    });
  });

  it('rehydrates the last astro clock snapshot immediately after a remount', async () => {
    const eventSource = { close: vi.fn() };
    astroClockApiMock.createStream.mockResolvedValue(eventSource);

    const firstPass = render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');
    firstPass.unmount();

    let resolveDashboard;
    let resolveHours;
    astroClockApiMock.getDashboard.mockReset();
    astroClockApiMock.getPlanetaryHours.mockReset();
    astroClockApiMock.createStream.mockResolvedValue(eventSource);
    astroClockApiMock.getDashboard.mockImplementation(
      () => new Promise((resolve) => { resolveDashboard = resolve; })
    );
    astroClockApiMock.getPlanetaryHours.mockImplementation(
      () => new Promise((resolve) => { resolveHours = resolve; })
    );

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    expect(screen.getByText('Jerusalem, Israel')).toBeInTheDocument();

    resolveDashboard?.(makeDashboard());
    resolveHours?.(hoursResponse);

    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalled();
    });
  });

  it('does not refetch planetary hours on every realtime stream heartbeat', async () => {
    const eventSource = { close: vi.fn(), onmessage: null, onerror: null };
    let tick = 0;
    astroClockApiMock.createStream.mockResolvedValue(eventSource);
    astroClockApiMock.getDashboard.mockImplementation(() => Promise.resolve(
      makeDashboard({
        timestamp: `2026-03-08T10:00:0${tick += 1}Z`,
      })
    ));

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    await act(async () => {
      eventSource.onmessage?.({ data: 'tick-1' });
    });
    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      eventSource.onmessage?.({ data: 'tick-2' });
    });
    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(2);
    });

    expect(astroClockApiMock.getPlanetaryHours).toHaveBeenCalledTimes(0);
  });

  it('reconnects the realtime stream after a disconnect so live updates continue', async () => {
    const firstStream = { close: vi.fn(), onmessage: null, onerror: null };
    const secondStream = { close: vi.fn(), onmessage: null, onerror: null };
    astroClockApiMock.createStream
      .mockResolvedValueOnce(firstStream)
      .mockResolvedValueOnce(secondStream);

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    astroClockApiMock.getDashboard.mockClear();

    await act(async () => {
      firstStream.onerror?.(new Event('error'));
    });

    await waitFor(() => {
      expect(firstStream.close).toHaveBeenCalledTimes(1);
      expect(astroClockApiMock.createStream).toHaveBeenCalledTimes(2);
    }, { timeout: 2500 });

    await act(async () => {
      secondStream.onmessage?.({ data: 'tick-after-reconnect' });
    });

    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(1);
    });
  });

  it('queues realtime heartbeat refreshes instead of starting overlapping dashboard loads', async () => {
    const eventSource = { close: vi.fn(), onmessage: null, onerror: null };
    const resolvers = [];
    astroClockApiMock.createStream.mockResolvedValue(eventSource);

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getDashboard.mockImplementation(
      () => new Promise((resolve) => { resolvers.push(resolve); })
    );

    await act(async () => {
      eventSource.onmessage?.({ data: 'tick-1' });
    });
    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      eventSource.onmessage?.({ data: 'tick-2' });
    });
    await act(async () => {});

    expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(1);
    expect(resolvers).toHaveLength(1);

    await act(async () => {
      resolvers[0]?.(makeDashboard({ timestamp: '2026-03-08T10:00:01Z' }));
    });

    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(2);
      expect(resolvers).toHaveLength(2);
    });

    await act(async () => {
      resolvers[1]?.(makeDashboard({ timestamp: '2026-03-08T10:00:02Z' }));
    });
  });

  it('shows a loading state for cusp aspects before the dashboard payload arrives', async () => {
    let resolveDashboard;
    let resolveHours;
    astroClockApiMock.getDashboard.mockImplementation(
      () => new Promise((resolve) => { resolveDashboard = resolve; })
    );
    astroClockApiMock.getPlanetaryHours.mockImplementation(
      () => new Promise((resolve) => { resolveHours = resolve; })
    );

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    expect(screen.getByText('Loading cusp aspects...')).toBeInTheDocument();

    resolveDashboard?.(makeDashboard());
    resolveHours?.(hoursResponse);

    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalled();
    });
  });

  it('respects an empty cusp selection when the user clicks None', async () => {
    const dashboard = makeDashboard();
    dashboard.data.cusp_aspects = {
      H1: [
        {
          planet: 'Mars',
          aspect: 'Conjunction',
          orb: 0.4,
          phase: 'applying',
          band: 'partile',
          origin_house: 1,
          origin_domain: 'self, body, character',
        },
      ],
    };
    astroClockApiMock.getDashboard.mockResolvedValue(dashboard);

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    expect(await screen.findByText('Mars (H1) Conjunction')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Cusps \(/ }));
    fireEvent.click(screen.getByRole('button', { name: 'None' }));

    await waitFor(() => {
      expect(screen.getByText('No cusp aspects match the current filters.')).toBeInTheDocument();
    });
    expect(screen.queryByText('Mars (H1) Conjunction')).not.toBeInTheDocument();
  });

  it('keeps Morin aspects inside the current aspects card scroll region', async () => {
    const dashboard = makeDashboard();
    dashboard.data.top_aspects = [
      { planet1: 'Venus', symbol: '☌', planet2: 'Jupiter', orb: 1.11, orb_text: '1.11°', max_orb: 6 },
    ];
    dashboard.data.morin_aspects = [
      { planet1: 'Venus', symbol: '✶', planet2: 'Jupiter', orb: 2.87, orb_text: '2.87°', max_orb: 10.5, complete_platic: true, direction: 'sinister', phase: 'separating' },
      { planet1: 'Mars', symbol: '☍', planet2: 'Saturn', orb: 3.8, orb_text: '3.80°', max_orb: 6.75, direction: 'sinister', phase: 'applying' },
      { planet1: 'Moon', symbol: '△', planet2: 'Jupiter', orb: 4.76, orb_text: '4.76°', max_orb: 10, direction: 'sinister', phase: 'applying' },
      { planet1: 'Mercury', symbol: '☌', planet2: 'Mars', orb: 4.85, orb_text: '4.85°', max_orb: 7.25, direction: 'sinister', phase: 'applying' },
    ];
    astroClockApiMock.getDashboard.mockResolvedValue(dashboard);

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Current Aspects');

    const card = screen.getByTestId('current-aspects-card');
    fireEvent.click(within(card).getByTestId('current-aspects-morin-toggle'));

    expect(await screen.findByText('Morin Aspects')).toBeInTheDocument();
    expect(within(card).getByTestId('current-aspects-scroll')).toBeInTheDocument();
    expect(within(card).getByText(/Mercury/)).toBeInTheDocument();
    expect(within(card).getAllByText(/Mars/).length).toBeGreaterThan(0);
    expect(within(card).getByRole('button', { name: 'More' })).toBeInTheDocument();
  });

  it('keeps the last Morin rows visible for the same chart while a repeat Morin refresh is pending', async () => {
    const morinDashboard = makeDashboard();
    morinDashboard.data.top_aspects = [
      { planet1: 'Venus', symbol: '☌', planet2: 'Jupiter', orb: 1.11, orb_text: '1.11°', max_orb: 6 },
    ];
    morinDashboard.data.morin_aspects = [
      { planet1: 'Venus', symbol: '✶', planet2: 'Jupiter', orb: 2.87, orb_text: '2.87°', max_orb: 10.5, complete_platic: true, direction: 'sinister', phase: 'separating' },
    ];
    const standardDashboard = makeDashboard();
    standardDashboard.data.top_aspects = morinDashboard.data.top_aspects;

    let morinRequestCount = 0;
    let resolvePendingMorin;
    astroClockApiMock.getDashboard.mockImplementation((payload = {}) => {
      if (payload?.morin) {
        morinRequestCount += 1;
        if (morinRequestCount === 2) {
          return new Promise((resolve) => { resolvePendingMorin = resolve; });
        }
        return Promise.resolve(morinDashboard);
      }
      return Promise.resolve(morinRequestCount >= 1 ? standardDashboard : morinDashboard);
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Current Aspects');

    const card = screen.getByTestId('current-aspects-card');
    const morinToggle = within(card).getByTestId('current-aspects-morin-toggle');

    fireEvent.click(morinToggle);
    expect(await screen.findByText('Morin Aspects')).toBeInTheDocument();
    expect(within(card).getByText(/platic/)).toBeInTheDocument();

    fireEvent.click(morinToggle);
    await waitFor(() => {
      expect(screen.getByText('Current Aspects')).toBeInTheDocument();
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(3);
    });

    fireEvent.click(morinToggle);
    await waitFor(() => {
      expect(astroClockApiMock.getDashboard.mock.calls.length).toBeGreaterThanOrEqual(4);
      expect(resolvePendingMorin).toBeTypeOf('function');
    });
    expect(astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0]).toMatchObject({ morin: true });
    expect(screen.getByText('Morin Aspects')).toBeInTheDocument();
    expect(within(card).getByText(/platic/)).toBeInTheDocument();

    resolvePendingMorin?.(morinDashboard);
    await waitFor(() => {
      expect(within(card).getByText(/platic/)).toBeInTheDocument();
    });
  });

  it('requests the realtime dashboard once when Morin mode disables streaming', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Current Aspects');

    astroClockApiMock.getDashboard.mockClear();

    const card = screen.getByTestId('current-aspects-card');
    fireEvent.click(within(card).getByTestId('current-aspects-morin-toggle'));

    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(1);
    });

    expect(astroClockApiMock.getDashboard.mock.calls[0]?.[0]).toMatchObject({
      morin: true,
      mode: 'realtime',
    });
  });

  it('uses the raw timezone id when the dashboard timezone label includes a UTC suffix', async () => {
    astroClockApiMock.getDashboard.mockResolvedValue(
      makeDashboard({
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        timezoneLabel: 'Asia/Jerusalem (UTC+02:00)',
      })
    );

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2026-03-08T10:00:00Z',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        houseSystem: 'R',
      }));
    });

    const dateInput = document.querySelector('input[type="date"]');
    const timeInput = document.querySelector('input[type="time"]');

    expect(dateInput?.value).toBe('2026-03-08');
    expect(timeInput?.value).toBe('12:00');
    expect(screen.queryByText('Failed to switch Astro Clock into manual mode.')).not.toBeInTheDocument();
  });

  it('applies manual date, time, and location through the scoped dashboard workflow', async () => {
    astroClockApiMock.getDashboard.mockResolvedValue(
      makeDashboard({ location: 'Greenwich, UK', timezone: 'Europe/London' })
    );

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Greenwich, UK');

    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2026-03-08T10:00:00Z',
        location: 'Greenwich, UK',
        timezone: 'Europe/London',
        houseSystem: 'R',
      }));
    });

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    const dateInput = document.querySelector('input[type="date"]');
    const timeInput = document.querySelector('input[type="time"]');
    const locationInput = document.querySelector('input[type="text"][placeholder="e.g., London, UK"]');

    fireEvent.change(dateInput, { target: { value: '2026-03-22' } });
    fireEvent.change(timeInput, { target: { value: '06:32' } });
    fireEvent.change(locationInput, { target: { value: 'Israel' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      const setModePayload = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(setModePayload).toMatchObject({
        mode: 'manual',
        datetime: '2026-03-22T06:32:00',
        location: 'Israel',
      });
      expect(setModePayload?.timezone).toBeUndefined();
    });

    await waitFor(() => {
      const dashboardPayload = astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0];
      const hoursPayload = astroClockApiMock.getPlanetaryHours.mock.calls.at(-1)?.[0];
      expect(dashboardPayload).toMatchObject({
        mode: 'manual',
        datetime: '2026-03-22T06:32:00',
        location: 'Israel',
      });
      expect(hoursPayload).toMatchObject({
        mode: 'manual',
        datetime: '2026-03-22T06:32:00',
        location: 'Israel',
      });
      expect(dashboardPayload?.timezone).toBeUndefined();
      expect(hoursPayload?.timezone).toBeUndefined();
    });
  });

  it('reconciles loaded snaps back into a coherent realtime chart context', async () => {
    astroClockApiMock.getDashboard.mockImplementation(async (payload = {}) => {
      if (payload?.mode === 'manual' && payload?.location === 'New York') {
        return makeDashboard({
          timestamp: '1946-06-13T14:14:00Z',
          location: 'New York',
          timezone: 'America/New_York',
          timezoneLabel: 'America/New_York (UTC-04:00)',
        });
      }
      if (payload?.mode === 'realtime') {
        return makeDashboard({
          timestamp: '2026-03-08T10:00:00Z',
          location: 'Jerusalem, Israel',
          timezone: 'Asia/Jerusalem',
          timezoneLabel: 'Asia/Jerusalem (UTC+02:00)',
        });
      }
      return makeDashboard();
    });
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [
        {
          id: 'snap-nyc',
          label: 'Snap 1946-06-13 14:14:00+00:00 - New York',
          effective_datetime: '1946-06-13T14:14:00Z',
          location: 'New York',
          dashboard: { timezone: 'America/New_York', timezone_label: 'America/New_York' },
          special_degrees: [],
        },
      ],
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    expect(await screen.findByText('Snap 1946-06-13 14:14:00+00:00 - New York')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Load' }));

    const dateInput = document.querySelector('input[type="date"]');
    const timeInput = document.querySelector('input[type="time"]');
    const locationInput = document.querySelector('input[type="text"][placeholder="e.g., London, UK"]');

    await waitFor(() => {
      expect(dateInput?.value).toBe('1946-06-13');
      expect(timeInput?.value).toBe('10:14');
      expect(locationInput?.value).toBe('New York');
    });

    fireEvent.click(screen.getByRole('button', { name: 'Realtime' }));

    await waitFor(() => {
      const realtimeSetMode = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(realtimeSetMode).toMatchObject({
        mode: 'realtime',
        houseSystem: 'R',
      });
      expect(realtimeSetMode?.location).toBeUndefined();
      expect(dateInput?.value).toBe('2026-03-08');
      expect(timeInput?.value).toBe('12:00');
      expect(locationInput?.value).toBe('Jerusalem, Israel');
    });

    expect(screen.getByText('Asia/Jerusalem (UTC+02:00)')).toBeInTheDocument();

    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    fireEvent.click(screen.getAllByRole('button', { name: 'Refresh' })[0]);

    await waitFor(() => {
      const dashboardPayload = astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0];
      expect(dashboardPayload).toMatchObject({
        mode: 'realtime',
        location: 'Jerusalem, Israel',
        houseSystem: 'R',
      });
      expect(dashboardPayload?.datetime).toBeUndefined();
    });
  });

  it('keeps chart-header location edits inside manual mode instead of forcing realtime', async () => {
    astroClockApiMock.getDashboard.mockImplementation(async (payload = {}) => {
      if (payload?.mode === 'manual' && payload?.location === 'Berlin, Germany') {
        return makeDashboard({
          timestamp: '2026-03-08T10:00:00Z',
          location: 'Berlin, Germany',
          timezone: 'Europe/Berlin',
          timezoneLabel: 'Europe/Berlin (UTC+01:00)',
        });
      }
      return makeDashboard({
        timestamp: '2026-03-08T10:00:00Z',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        timezoneLabel: 'Asia/Jerusalem (UTC+02:00)',
      });
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');
    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2026-03-08T10:00:00Z',
        location: 'Jerusalem, Israel',
      }));
    });

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    fireEvent.change(screen.getByPlaceholderText('City, Country or lat,lon'), {
      target: { value: 'Berlin, Germany' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Set' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2026-03-08T10:00:00Z',
        location: 'Berlin, Germany',
      }));
    });

    expect(astroClockApiMock.setMode.mock.calls.some(([payload]) => (
      payload?.mode === 'realtime' && payload?.location === 'Berlin, Germany'
    ))).toBe(false);

    const locationInput = document.querySelector('input[type="text"][placeholder="e.g., London, UK"]');
    await waitFor(() => {
      expect(locationInput?.value).toBe('Berlin, Germany');
    });

    expect(screen.getByText('Europe/Berlin (UTC+01:00)')).toBeInTheDocument();
  });

  it('does not let realtime draft inputs override the active live chart context', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    const locationInput = document.querySelector('input[type="text"][placeholder="e.g., London, UK"]');
    fireEvent.change(locationInput, {
      target: { value: 'New York' },
    });

    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    fireEvent.click(screen.getAllByRole('button', { name: 'Refresh' })[0]);

    await waitFor(() => {
      const dashboardPayload = astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0];
      expect(dashboardPayload).toMatchObject({
        mode: 'realtime',
        location: 'Jerusalem, Israel',
        houseSystem: 'R',
      });
      expect(dashboardPayload?.datetime).toBeUndefined();
    });
  });

  it('does not surface a snap preload timeout as a top-level Astro Clock failure', async () => {
    astroClockApiMock.listSnaps.mockRejectedValueOnce(new Error('Request timed out after 30s'));

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    expect(await screen.findByText('Jerusalem, Israel')).toBeInTheDocument();
    expect(screen.queryByText('Request timed out after 30s')).not.toBeInTheDocument();
    expect(screen.getByText('Saved snaps are not loaded yet. Click Refresh when you need them.')).toBeInTheDocument();
  });

  it('passes the active Astro Clock house system into the transit modal', async () => {
    global.localStorage.getItem.mockImplementation((key) => (
      key === 'vox_stella_house_system_code' ? 'W' : null
    ));

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Transits' }));

    await waitFor(() => {
      expect(screen.getByTestId('transits-modal')).toBeInTheDocument();
    });

    const latestProps = transitsModalMock.props.at(-1);
    expect(latestProps?.defaultHouseSystem).toBe('W');
    expect(latestProps?.open).toBe(true);
  });

  it('redirects unverified packaged users to the website instead of opening astrocartography', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
      />
    );

    await screen.findByText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Astrocartography' }));

    expect(window.electronAPI.openExternal).toHaveBeenCalledWith('https://voxstella.app/product');
    expect(screen.queryByTestId('astrocartography-modal')).not.toBeInTheDocument();
  });

  it('opens astrocartography for verified packaged users', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Astrocartography' }));

    await waitFor(() => {
      expect(screen.getByTestId('astrocartography-modal')).toBeInTheDocument();
    });

    expect(window.electronAPI.openExternal).not.toHaveBeenCalled();
    const latestProps = astrocartographyModalMock.props.at(-1);
    expect(latestProps?.open).toBe(true);
  });

  it('opens the synastry modal for licensed users from the AstroClock action row', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Synastry' }));

    await waitFor(() => {
      expect(screen.getByTestId('synastry-modal')).toBeInTheDocument();
    });

    const latestProps = synastryModalMock.props.at(-1);
    expect(latestProps?.open).toBe(true);
    expect(latestProps?.defaultHouseSystem).toBeUndefined();
  });

  it('passes the active loaded snap context into the transit modal', async () => {
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [
        {
          id: 'snap-israel',
          label: 'Snap 1948-05-14 14:00:00+00:00 - israel',
          effective_datetime: '1948-05-14T14:00:00Z',
          location: 'israel',
          dashboard: { timezone_label: 'Asia/Jerusalem' },
          special_degrees: [],
        },
      ],
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    expect(await screen.findByText('Snap 1948-05-14 14:00:00+00:00 - israel')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Load' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '1948-05-14T14:00:00Z',
        location: 'israel',
      }));
    });

    fireEvent.click(screen.getByRole('button', { name: 'Transits' }));

    await waitFor(() => {
      expect(screen.getByTestId('transits-modal')).toBeInTheDocument();
    });

    const latestProps = transitsModalMock.props.at(-1);
    expect(latestProps?.initialNatalContext).toMatchObject({
      snapId: 'snap-israel',
      date: '1948-05-14',
      time: '16:00',
      location: 'israel',
      timezone: 'Asia/Jerusalem',
      houseSystem: 'R',
    });
  });

  it('re-links the active chart to a matching saved snap before opening the transit modal', async () => {
    astroClockApiMock.getDashboard.mockResolvedValue(makeDashboard({
      timestamp: '1948-05-14T14:00:00Z',
      location: 'israel',
      timezone: 'Asia/Jerusalem',
    }));
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [
        {
          id: 'snap-israel',
          label: 'Snap 1948-05-14 14:00:00+00:00 - israel',
          effective_datetime: '1948-05-14T14:00:00Z',
          location: 'israel',
          dashboard: { timezone_label: 'Asia/Jerusalem' },
          special_degrees: [],
        },
      ],
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Snap 1948-05-14 14:00:00+00:00 - israel');
    await screen.findByText('israel');

    fireEvent.click(screen.getByRole('button', { name: 'Transits' }));

    await waitFor(() => {
      expect(screen.getByTestId('transits-modal')).toBeInTheDocument();
    });

    const latestProps = transitsModalMock.props.at(-1);
    expect(latestProps?.initialNatalContext).toMatchObject({
      snapId: 'snap-israel',
      date: '1948-05-14',
      time: '16:00',
      location: 'israel',
      timezone: 'Asia/Jerusalem',
      houseSystem: 'R',
    });
  });

  it('copies the main Astro Clock prompt with current chart payload data', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Copy Prompt ▾' }));
    fireEvent.click(screen.getByRole('button', { name: 'Natal prompt (copy)' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Mock Submit Prompt' }));

    await waitFor(() => expect(window.navigator.clipboard.writeText).toHaveBeenCalledTimes(1));
    const copied = String(window.navigator.clipboard.writeText.mock.calls[0][0] || '');
    expect(copied).toContain('Current Astro Clock chart payload');
    expect(copied).toContain('"chart_context"');
    expect(copied).toContain('"location": "Jerusalem, Israel"');
    expect(copied).toContain('"chart_factors"');
    expect(copied).toContain('"house_cusps"');
  });

  it('waits for the pause snapshot before opening forensic and sends the full scoped chart context', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByRole('button', { name: 'Forensic' });
    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalled();
    });

    let releasePause;
    astroClockApiMock.setMode.mockImplementationOnce(
      () => new Promise((resolve) => { releasePause = resolve; })
    );

    fireEvent.click(screen.getByRole('button', { name: 'Forensic' }));

    await waitFor(() => {
      expect(screen.getByText('Opening Forensic...')).toBeInTheDocument();
      expect(screen.queryByText('Close')).not.toBeInTheDocument();
      expect(astroClockApiMock.getForensic).not.toHaveBeenCalled();
    });

    releasePause({ success: true });

    await waitFor(() => {
      const sawManualRefresh = astroClockApiMock.getDashboard.mock.calls.some(([payload]) => (
        payload?.mode === 'manual' &&
        payload?.datetime === '2026-03-08T10:00:00Z' &&
        payload?.location === 'Jerusalem, Israel'
      ));
      expect(sawManualRefresh).toBe(true);
    });

    expect(await screen.findByText('Close')).toBeInTheDocument();
    expect(screen.queryByText('Opening Forensic...')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(astroClockApiMock.getForensic).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2026-03-08T10:00:00Z',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        houseSystem: 'R',
      }));
    });
  });

  it('renders forensic directional findings and corrected labels in the frontend modal', async () => {
    astroClockApiMock.getForensic.mockResolvedValue(makeForensicPayload());

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByRole('button', { name: 'Forensic' });
    fireEvent.click(screen.getByRole('button', { name: 'Forensic' }));

    expect(await screen.findByText('Directional Findings')).toBeInTheDocument();
    expect(await screen.findByText('Authority Or Public Case')).toBeInTheDocument();
    expect((await screen.findAllByText('Life/death overlap points to violence or homicide')).length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText('Finding Notes')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Life\/death overlap points to violence or homicide/i }));
    expect(await screen.findByText(/When the victim ruler also rules death matters or falls into hidden\/death houses/i)).toBeInTheDocument();
    expect(await screen.findByText(/Associate\/public-network link/i)).toBeInTheDocument();
    expect(await screen.findByText(/Survivability signal:/i)).toBeInTheDocument();
    expect(await screen.findByText(/\(fatal pressure dominates\)/i)).toBeInTheDocument();
  });

  it('renders a replay-slice public assassination payload cleanly in the frontend modal', async () => {
    astroClockApiMock.getForensic.mockResolvedValue(makeShinzoAbeForensicPayload());

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByRole('button', { name: 'Forensic' });
    fireEvent.click(screen.getByRole('button', { name: 'Forensic' }));

    expect(await screen.findByText('Directional Findings')).toBeInTheDocument();
    expect(await screen.findByText('Violence Homicide')).toBeInTheDocument();
    expect(await screen.findByText('Authority Or Public Case')).toBeInTheDocument();
    expect(await screen.findByText('Public: 1')).toBeInTheDocument();
    expect((await screen.findAllByText('Public or authority axis is foregrounded')).length).toBeGreaterThanOrEqual(1);
    fireEvent.click(screen.getByRole('button', { name: /Public or authority axis is foregrounded/i }));
    expect(await screen.findByText(/A strong 10th-house or solar signature tied to violence\/hidden-house pressure points/i)).toBeInTheDocument();
  });
});
