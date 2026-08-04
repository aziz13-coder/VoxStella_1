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
  getSnap: vi.fn(),
  createSnap: vi.fn(),
  confirmSnapContext: vi.fn(),
  resolveTimezone: vi.fn(),
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

const traitProfileModalMock = vi.hoisted(() => ({
  props: [],
}));

const electionModalMock = vi.hoisted(() => ({
  props: [],
}));

const chineseAstrologyPageMock = vi.hoisted(() => ({
  props: [],
}));

const birthCertificationModalMock = vi.hoisted(() => ({
  props: [],
}));

const compassTileMock = vi.hoisted(() => ({
  props: [],
}));

const degreeHitsTileMock = vi.hoisted(() => ({
  props: [],
}));

const receptionsTileMock = vi.hoisted(() => ({
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
  default: (props) => {
    receptionsTileMock.props.push(props);
    return <div data-testid="receptions-tile" />;
  },
}));

vi.mock('../features/astroclock/MetricsTile.jsx', () => ({
  default: () => <div data-testid="metrics-tile" />,
}));

vi.mock('../features/astroclock/DegreeHitsTile.jsx', () => ({
  default: (props) => {
    degreeHitsTileMock.props.push(props);
    return <div data-testid="degree-hits-tile" />;
  },
}));

vi.mock('../features/astroclock/TraitProfileModal.jsx', () => ({
  default: (props) => {
    traitProfileModalMock.props.push(props);
    return <div data-testid="trait-profile-modal" />;
  },
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
  default: (props) => {
    electionModalMock.props.push(props);
    return props?.open ? <div data-testid="election-modal" /> : null;
  },
}));

vi.mock('../features/astroclock/AstrocartographyModal.jsx', () => ({
  default: (props) => {
    astrocartographyModalMock.props.push(props);
    return props?.open ? <div data-testid="astrocartography-modal" /> : null;
  },
}));

vi.mock('../features/astroclock/ChineseAstrologyPage.jsx', () => ({
  default: (props) => {
    chineseAstrologyPageMock.props.push(props);
    return <div data-testid="chinese-astrology-page" />;
  },
}));

vi.mock('../features/astroclock/BirthCertificationModal.jsx', () => ({
  default: (props) => {
    birthCertificationModalMock.props.push(props);
    return props?.open ? <div data-testid="birth-certification-modal" /> : null;
  },
}));

vi.mock('../features/astroclock/ResearchMode.jsx', () => ({
  default: () => null,
}));

vi.mock('../features/astroclock/AspectAnalysisModal.jsx', () => ({
  default: () => null,
}));

vi.mock('../features/astroclock/CompassTile.jsx', () => ({
  default: (props) => {
    compassTileMock.props.push(props);
    return <div data-testid="compass-tile" />;
  },
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
import { clearAstroClockWarmState, writeAstroClockWarmState } from '../features/astroclock/astroClockViewState.mjs';

function makeDashboard({
  timestamp = '2026-03-08T10:00:00Z',
  location = 'Jerusalem, Israel',
  timezone = 'Asia/Jerusalem',
  timezoneLabel = timezone,
  latitude = 31.778,
  longitude = 35.235,
} = {}) {
  return {
    success: true,
    data: {
      timestamp,
      location,
      timezone,
      timezone_label: timezoneLabel,
      latitude,
      longitude,
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

async function findAnyText(text) {
  let match = null;
  await waitFor(() => {
    match =
      screen.queryAllByText(text)[0] ||
      Array.from(document.querySelectorAll('input, textarea')).find((node) => node.value === text);
    if (!match) {
      throw new Error(`Unable to find text or form value: ${text}`);
    }
  });
  return match;
}

async function waitForDashboardReady() {
  await waitFor(() => {
    expect(astroClockApiMock.getDashboard).toHaveBeenCalled();
  });
}

function expectPremiumOffer(featureName) {
  expect(screen.getByTestId('premium-offer-modal')).toBeInTheDocument();
  expect(screen.getByText('$25')).toBeInTheDocument();
  expect(screen.getByText(/Standard monthly plan: \$35/i)).toBeInTheDocument();
  expect(screen.queryByText(/Normally \$35 \/ month/i)).not.toBeInTheDocument();
  expect(screen.getByText(/Vox Stella Premium Desktop Monthly/i)).toBeInTheDocument();
  expect(screen.getByText(/Unlock the full suite/i)).toBeInTheDocument();
  expect(screen.getByText(/Save nearly 30%/i)).toBeInTheDocument();
  expect(window.electronAPI.openExternal).not.toHaveBeenCalled();
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
    asc_ruler_placement: {
      ruler: 'Venus',
      house: 6,
      label: 'Routine Disrupted',
      summary: 'Victim routine or ordinary pattern was interrupted; stalker or watcher testimony may be relevant.',
      cues: ['routine activity interrupted', 'possible watcher or stalker context'],
      source: 'McIntosh Criminal Astrology, pp. 17-19',
    },
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
    traitProfileModalMock.props = [];
    electionModalMock.props = [];
    chineseAstrologyPageMock.props = [];
    birthCertificationModalMock.props = [];
    compassTileMock.props = [];
    degreeHitsTileMock.props = [];
    receptionsTileMock.props = [];
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
    Object.defineProperty(window, 'confirm', {
      configurable: true,
      writable: true,
      value: vi.fn().mockReturnValue(true),
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
    astroClockApiMock.getSnap.mockResolvedValue({ success: false });
    astroClockApiMock.createSnap.mockResolvedValue({ success: true });
    astroClockApiMock.confirmSnapContext.mockResolvedValue({ success: false });
    astroClockApiMock.resolveTimezone.mockResolvedValue({
      success: true,
      location: 'Jerusalem, Israel',
      latitude: 31.76904,
      longitude: 35.21633,
      timezone: 'Asia/Jerusalem',
    });
    astroClockApiMock.deleteSnap.mockResolvedValue({ success: true });
  });

  it('keeps the first-run Astro Clock surface in checking state without raw fetch errors', async () => {
    astroClockApiMock.getDashboard.mockRejectedValue(new Error('Failed to fetch'));
    astroClockApiMock.getPlanetaryHours.mockRejectedValue(new Error('Failed to fetch'));

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="checking"
        licenseActive
      />
    );

    expect(
      await screen.findByText(/waiting for the local astrology engine to finish starting/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/failed to fetch/i)).not.toBeInTheDocument();
    expect(astroClockApiMock.getDashboard).not.toHaveBeenCalled();
    expect(astroClockApiMock.getPlanetaryHours).not.toHaveBeenCalled();
    expect(astroClockApiMock.listSnaps).not.toHaveBeenCalled();
  });

  it('loads the dashboard after the backend moves from checking to connected', async () => {
    const view = render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="checking"
        licenseActive
      />
    );

    expect(screen.getByText(/waiting for the local astrology engine/i)).toBeInTheDocument();

    view.rerender(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="connected"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');

    expect(screen.queryByText(/waiting for the local astrology engine/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/failed to fetch/i)).not.toBeInTheDocument();
    expect(astroClockApiMock.getDashboard).toHaveBeenCalled();
  });

  it('keeps the current realtime chart visible without a red banner during transient backend status drops', async () => {
    const eventSource = { close: vi.fn(), onmessage: null, onerror: null };
    astroClockApiMock.createStream.mockResolvedValue(eventSource);

    const view = render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');

    view.rerender(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="offline"
        licenseActive
      />
    );

    expect(await findAnyText('Jerusalem, Israel')).toBeInTheDocument();
    expect(screen.queryByText(/failed to fetch/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/could not reach the local astrology engine/i)).not.toBeInTheDocument();
  });

  it('does not reuse warm realtime coordinates during startup requests', async () => {
    writeAstroClockWarmState({
      mode: 'realtime',
      autoLocation: 'Jerusalem, Israel',
      data: makeDashboard().data,
      hours: hoursResponse.data,
      houseSystem: 'R',
      snaps: [],
      snapsLoaded: true,
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await waitFor(() => {
      const setModePayload = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(setModePayload).toMatchObject({
        mode: 'realtime',
        location: 'Jerusalem, Israel',
        houseSystem: 'R',
      });
      expect(setModePayload?.timezone).toBeUndefined();
      expect(setModePayload?.latitude).toBeUndefined();
      expect(setModePayload?.longitude).toBeUndefined();
    });

    await waitFor(() => {
      const dashboardPayload = astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0];
      expect(dashboardPayload).toMatchObject({
        mode: 'realtime',
        location: 'Jerusalem, Israel',
        houseSystem: 'R',
      });
      expect(dashboardPayload?.timezone).toBeUndefined();
      expect(dashboardPayload?.latitude).toBeUndefined();
      expect(dashboardPayload?.longitude).toBeUndefined();
    });
  });

  it('does not reuse persisted automatic coordinates before the first dashboard payload arrives', async () => {
    global.localStorage.getItem.mockImplementation((key) => {
      if (key === 'vox_stella_astro_clock_auto_location') return 'Jerusalem, Israel';
      if (key === 'vox_stella_astro_clock_auto_context') {
        return JSON.stringify({
          location: 'Jerusalem, Israel',
          timezone: 'Asia/Jerusalem',
          latitude: 31.778,
          longitude: 35.235,
        });
      }
      return null;
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await waitFor(() => {
      const setModePayload = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(setModePayload).toMatchObject({
        mode: 'realtime',
        location: 'Jerusalem, Israel',
        houseSystem: 'R',
      });
      expect(setModePayload?.timezone).toBeUndefined();
      expect(setModePayload?.latitude).toBeUndefined();
      expect(setModePayload?.longitude).toBeUndefined();
    });
  });

  it('uses the explicit Astro Clock default when no applied realtime location exists', async () => {
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

    await waitFor(() => {
      const setModePayload = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(setModePayload).toMatchObject({
        mode: 'realtime',
        location: 'Greenwich, UK',
        houseSystem: 'R',
      });
      expect(setModePayload?.timezone).toBeUndefined();
      expect(setModePayload?.latitude).toBeUndefined();
      expect(setModePayload?.longitude).toBeUndefined();
    });
  });

  it('ignores a bare stale automatic location without a resolved context', async () => {
    astroClockApiMock.getDashboard.mockResolvedValue(
      makeDashboard({ location: 'Greenwich, UK', timezone: 'Europe/London' })
    );
    global.localStorage.getItem.mockImplementation((key) => {
      if (key === 'vox_stella_astro_clock_auto_location') return 'Israel';
      return null;
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await waitFor(() => {
      const setModePayload = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(setModePayload).toMatchObject({
        mode: 'realtime',
        location: 'Greenwich, UK',
        houseSystem: 'R',
      });
    });
    expect(document.querySelector('#astroclock-auto-location')?.value).toBe('Greenwich, UK');
  });

  it('saves realtime snaps with the active coordinate context', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Snap' }));

    await waitFor(() => {
      expect(astroClockApiMock.createSnap).toHaveBeenCalledWith(expect.objectContaining({
        includeModern: false,
        mode: 'realtime',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 31.778,
        longitude: 35.235,
        houseSystem: 'R',
      }));
    });
  });

  it('saves manual snaps with the active manual coordinate context', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');
    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2026-03-08T10:00:00Z',
      }));
    });

    astroClockApiMock.createSnap.mockClear();
    fireEvent.click(screen.getByRole('button', { name: 'Snap' }));

    await waitFor(() => {
      expect(astroClockApiMock.createSnap).toHaveBeenCalledWith(expect.objectContaining({
        includeModern: false,
        mode: 'manual',
        datetime: '2026-03-08T10:00:00Z',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 31.778,
        longitude: 35.235,
        houseSystem: 'R',
      }));
    });
  });

  it('coalesces rapid Snap clicks and allows a later save with a fresh idempotency key', async () => {
    let resolveFirstSave;
    const firstSave = new Promise((resolve) => {
      resolveFirstSave = resolve;
    });
    astroClockApiMock.createSnap
      .mockReturnValueOnce(firstSave)
      .mockResolvedValueOnce({ success: true, data: { id: 'snap-second' } });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');
    const snapButton = screen.getByRole('button', { name: 'Snap' });
    fireEvent.click(snapButton);
    fireEvent.click(snapButton);

    await waitFor(() => {
      expect(astroClockApiMock.createSnap).toHaveBeenCalledTimes(1);
      expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
    });
    const firstKey = astroClockApiMock.createSnap.mock.calls[0]?.[0]?.idempotencyKey;
    expect(firstKey).toMatch(/^astro-clock-snap-/);

    await act(async () => {
      resolveFirstSave({ success: true, data: { id: 'snap-first' } });
      await firstSave;
    });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Snap' })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Snap' }));
    await waitFor(() => {
      expect(astroClockApiMock.createSnap).toHaveBeenCalledTimes(2);
    });
    const secondKey = astroClockApiMock.createSnap.mock.calls[1]?.[0]?.idempotencyKey;
    expect(secondKey).toMatch(/^astro-clock-snap-/);
    expect(secondKey).not.toBe(firstKey);
  });

  it('renders each saved chart in its own timezone and surfaces migration review notices', async () => {
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      migration_report: {
        migrated_records: 2,
        backup_path: 'preserved-backup.json',
        semantic_duplicate_groups: [{ semantic_key: 'group-1' }],
      },
      items: [
        {
          id: 'snap-jerusalem',
          label: 'Jerusalem birth',
          effective_datetime: '2001-06-15T08:15:00+00:00',
          local_datetime: '2001-06-15T11:15:00+03:00',
          timezone: 'Asia/Jerusalem',
          timezone_label: 'Asia/Jerusalem (UTC+03:00)',
          location: 'Jerusalem, Israel',
          summary: {},
          calculation_context: { review_required: false },
        },
        {
          id: 'snap-new-york',
          label: 'New York comparison',
          effective_datetime: '2001-06-15T08:15:00+00:00',
          local_datetime: '2001-06-15T04:15:00-04:00',
          timezone: 'America/New_York',
          timezone_label: 'America/New_York (UTC-04:00)',
          location: 'New York, USA',
          summary: {},
          calculation_context: {
            review_required: true,
            time_provenance: { ambiguous: true },
          },
          duplicate_group: {
            semantic_key: 'group-1',
            canonical_id: 'snap-new-york',
            records_preserved: true,
          },
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

    expect(await screen.findByText('Jerusalem birth')).toBeInTheDocument();
    expect(screen.getByText(
      '15 Jun 2001, 11:15 · Asia/Jerusalem (UTC+03:00) · Jerusalem, Israel',
    )).toBeInTheDocument();
    expect(screen.getByText(
      '15 Jun 2001, 04:15 · America/New_York (UTC-04:00) · New York, USA',
    )).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(
      '2 saved charts were upgraded. 1 chart needs context review. 1 possible duplicate group was preserved. A safety backup was preserved.',
    );
    expect(screen.getByText('Review saved context')).toBeInTheDocument();
    expect(screen.getByText('Possible duplicate')).toBeInTheDocument();
    expect(screen.getByText(/Saved time interpretation needs review/)).toBeInTheDocument();
    expect(screen.getByText(/no saved chart was deleted/)).toBeInTheDocument();
  });

  it('disables review-required loads in both saved-list and search modes', async () => {
    const reviewSnap = {
      id: 'snap-review-only',
      label: 'Unsafe migrated chart',
      effective_datetime: null,
      local_datetime: '2026-11-01T01:30:00-04:00',
      timezone: 'America/New_York',
      location: 'New York, USA',
      summary: {},
      calculation_context: {
        review_required: true,
        time_provenance: { ambiguous: true },
      },
    };
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [reviewSnap],
    });
    astroClockApiMock.getSnap.mockResolvedValue({
      success: true,
      snap: reviewSnap,
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />,
    );

    const listTitle = await screen.findByText('Unsafe migrated chart');
    const listCard = listTitle.closest('.rounded-2xl');
    expect(listCard).not.toBeNull();
    expect(within(listCard).getByRole('button', { name: 'Load' })).toBeDisabled();
    expect(within(listCard).getByRole('button', { name: 'Correct context' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Search' }));
    await waitFor(() => {
      expect(astroClockApiMock.getSnap).toHaveBeenCalledWith('snap-review-only');
    });
    const searchTitle = await screen.findByText('Unsafe migrated chart');
    const searchCard = searchTitle.closest('.rounded-2xl');
    expect(searchCard).not.toBeNull();
    expect(within(searchCard).getByRole('button', { name: 'Load' })).toBeDisabled();
    expect(within(searchCard).getByRole('button', { name: 'Correct context' })).toBeEnabled();
  });

  it('rejects a snap when hydrated details newly require review without changing the active chart', async () => {
    const summary = {
      id: 'snap-stale-summary',
      label: 'Stale safe summary',
      effective_datetime: '2004-05-06T07:30:00+00:00',
      timezone: 'Europe/London',
      location: 'London, UK',
      latitude: 51.5072,
      longitude: -0.1276,
      calculation_context: { review_required: false },
      summary: {},
    };
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [summary],
    });
    astroClockApiMock.getSnap.mockResolvedValue({
      success: true,
      snap: {
        ...summary,
        effective_datetime: null,
        calculation_context: {
          review_required: true,
          time_provenance: { ambiguous: true },
        },
      },
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />,
    );

    const card = (await screen.findByText('Stale safe summary')).closest('.rounded-2xl');
    expect(card).not.toBeNull();
    astroClockApiMock.setMode.mockClear();
    fireEvent.click(within(card).getByRole('button', { name: 'Load' }));

    expect(await screen.findByText(/needs context review.*correct it/i)).toBeInTheDocument();
    expect(astroClockApiMock.setMode).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Transits' }));
    await waitFor(() => expect(screen.getByTestId('transits-modal')).toBeInTheDocument());
    expect(transitsModalMock.props.at(-1)?.initialNatalContext?.snapId).toBe('');
  });

  it('fails closed when saved-snap detail verification fails', async () => {
    const summary = {
      id: 'snap-unverified',
      label: 'Unverified summary',
      effective_datetime: '2004-05-06T07:30:00+00:00',
      timezone: 'Europe/London',
      location: 'London, UK',
      calculation_context: { review_required: false },
      summary: {},
    };
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [summary],
    });
    astroClockApiMock.getSnap.mockRejectedValue(new Error('detail endpoint unavailable'));

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />,
    );

    const card = (await screen.findByText('Unverified summary')).closest('.rounded-2xl');
    astroClockApiMock.setMode.mockClear();
    fireEvent.click(within(card).getByRole('button', { name: 'Load' }));

    expect(await screen.findByText(/could not be verified and was not loaded/i)).toBeInTheDocument();
    expect(astroClockApiMock.setMode).not.toHaveBeenCalled();
  });

  it('previews a confirmed context before saving a corrected copy and preserves the original', async () => {
    const legacySnap = {
      id: 'snap-legacy',
      label: 'Legacy Jerusalem birth',
      effective_datetime: '2001-06-15T08:15:00+00:00',
      local_datetime: '2001-06-15T11:15:00+03:00',
      timezone: 'Asia/Jerusalem',
      timezone_label: 'Asia/Jerusalem (UTC+03:00)',
      location: 'Israel',
      summary: {},
      coordinate_provenance: {
        persisted_with_chart: false,
        review_required: true,
      },
      calculation_context: { review_required: true },
    };
    const correctedSnap = {
      id: 'snap-confirmed',
      label: 'Legacy Jerusalem birth (confirmed context)',
      effective_datetime: '2001-06-15T08:15:00+00:00',
      local_datetime: '2001-06-15T11:15:00+03:00',
      timezone: 'Asia/Jerusalem',
      timezone_label: 'Asia/Jerusalem (UTC+03:00)',
      location: 'Jerusalem, Israel',
      latitude: 31.76904,
      longitude: 35.21633,
      calculation_context: { review_required: false },
    };
    let correctionPersisted = false;
    astroClockApiMock.listSnaps.mockImplementation(async () => ({
      success: true,
      items: correctionPersisted
        ? [{ ...legacySnap, superseded_by: 'snap-confirmed' }, correctedSnap]
        : [legacySnap],
      migration_report: { migrated_records: 1 },
    }));
    astroClockApiMock.confirmSnapContext
      .mockResolvedValueOnce({
        success: true,
        data: {
          persisted: false,
          original_preserved: true,
          replacement: correctedSnap,
        },
      })
      .mockImplementationOnce(async () => {
        correctionPersisted = true;
        return {
        success: true,
        data: {
          persisted: true,
          original_preserved: true,
          replacement: correctedSnap,
        },
        };
      });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Correct context' }));
    expect(screen.getByRole('region', { name: 'Correct saved chart context' })).toBeInTheDocument();
    expect(screen.getByLabelText('Confirmed local date and time')).toHaveValue('2001-06-15T11:15');
    expect(screen.getByLabelText('Confirmed IANA timezone')).toHaveValue('Asia/Jerusalem');
    expect(screen.getByLabelText('Confirmed latitude')).toHaveValue(null);
    expect(screen.getByLabelText('Confirmed longitude')).toHaveValue(null);

    fireEvent.change(screen.getByLabelText('Confirmed specific location'), {
      target: { value: 'Jerusalem, Israel' },
    });
    fireEvent.change(screen.getByLabelText('Confirmed house system'), {
      target: { value: 'P' },
    });
    expect(screen.getByText(/does not change astrocartography world-map line geometry/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Preview corrected chart' }));

    await waitFor(() => {
      expect(astroClockApiMock.resolveTimezone).toHaveBeenCalledWith(
        'Jerusalem, Israel',
        expect.objectContaining({
          requireSpecific: true,
          signal: expect.any(AbortSignal),
        }),
      );
    });
    expect(screen.getByLabelText('Confirmed latitude')).toHaveValue(31.76904);
    expect(screen.getByLabelText('Confirmed longitude')).toHaveValue(35.21633);
    expect(screen.getByLabelText('Confirmed IANA timezone')).toHaveValue('Asia/Jerusalem');
    expect(await screen.findByText(/Resolved automatically: Jerusalem, Israel/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(astroClockApiMock.confirmSnapContext).toHaveBeenNthCalledWith(
        1,
        'snap-legacy',
        expect.objectContaining({
          localDatetime: '2001-06-15T11:15',
          timezone: 'Asia/Jerusalem',
          location: 'Jerusalem, Israel',
          latitude: 31.76904,
          longitude: 35.21633,
          houseSystem: 'P',
          persist: false,
        }),
      );
    });
    expect(await screen.findByText('Corrected chart preview ready')).toBeInTheDocument();
    expect(screen.getByText(/Planets, houses, and angles were recalculated together/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Save corrected copy' }));
    await waitFor(() => {
      expect(astroClockApiMock.confirmSnapContext).toHaveBeenNthCalledWith(
        2,
        'snap-legacy',
        expect.objectContaining({ persist: true }),
      );
    });
    await waitFor(() => {
      expect(screen.queryByRole('region', { name: 'Correct saved chart context' })).not.toBeInTheDocument();
    });
    expect(screen.queryByText(
      'Corrected copy saved. The original saved chart was preserved.',
    )).not.toBeInTheDocument();
    expect(screen.getByText('Superseded—use corrected copy')).toBeInTheDocument();
    const originalCard = screen.getByText('Legacy Jerusalem birth').closest('.rounded-2xl');
    expect(originalCard).not.toBeNull();
    expect(within(originalCard).getByRole('button', { name: 'Load' })).toBeDisabled();
    fireEvent.click(within(originalCard).getByRole('button', { name: 'Load corrected copy' }));
    await waitFor(() => {
      expect(astroClockApiMock.getSnap).toHaveBeenCalledWith(
        'snap-confirmed',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });
  });

  it('does not guess a capital when a saved correction only names a country', async () => {
    // Deliberately synthetic non-person fixture that preserves a +02:00 UTC conversion.
    const countryOnlySnap = {
      id: 'snap-country-only',
      label: 'Synthetic country-only birthplace',
      effective_datetime: '2001-02-03T12:15:00+00:00',
      local_datetime: '2001-02-03T14:15:00+02:00',
      timezone: 'Asia/Jerusalem',
      location: 'Israel',
      summary: {},
      coordinate_provenance: {
        persisted_with_chart: false,
        review_required: true,
      },
      calculation_context: { review_required: true },
    };
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [countryOnlySnap],
    });
    astroClockApiMock.resolveTimezone.mockRejectedValueOnce(
      new Error(
        'Enter a specific city or place. A country or broad region cannot confirm birth coordinates.',
      ),
    );

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />,
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Correct context' }));
    fireEvent.click(screen.getByRole('button', { name: 'Preview corrected chart' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /enter a specific city or place/i,
    );
    expect(astroClockApiMock.resolveTimezone).toHaveBeenCalledWith(
      'Israel',
      expect.objectContaining({ requireSpecific: true }),
    );
    expect(screen.getByLabelText('Confirmed latitude')).toHaveValue(null);
    expect(screen.getByLabelText('Confirmed longitude')).toHaveValue(null);
    expect(astroClockApiMock.confirmSnapContext).not.toHaveBeenCalled();
  });

  it('validates full correction time and retries an ambiguous fold with the selected offset', async () => {
    const ambiguousSnap = {
      id: 'snap-fold',
      label: 'Repeated-hour saved chart',
      effective_datetime: null,
      local_datetime: '2026-11-01T01:30:00-04:00',
      timezone: 'America/New_York',
      timezone_label: 'America/New_York',
      location: 'New York, USA',
      latitude: 40.7128,
      longitude: -74.006,
      coordinate_provenance: {
        persisted_with_chart: true,
        review_required: false,
      },
      calculation_context: {
        review_required: true,
        time_provenance: {
          ambiguous: true,
          wall_time_status: 'ambiguous_fold',
        },
      },
      summary: {},
    };
    const ambiguityError = Object.assign(
      new Error('Local time occurs twice in America/New_York.'),
      {
        payload: {
          success: false,
          error_code: 'ambiguous_local_time',
          time_resolution: {
            code: 'ambiguous_local_time',
            wall_time_status: 'ambiguous_fold',
            candidates: [
              {
                fold: 0,
                local_datetime: '2026-11-01T01:30:00-04:00',
                utc_offset: '-04:00',
                instant_utc: '2026-11-01T05:30:00+00:00',
                valid: true,
              },
              {
                fold: 1,
                local_datetime: '2026-11-01T01:30:00-05:00',
                utc_offset: '-05:00',
                instant_utc: '2026-11-01T06:30:00+00:00',
                valid: true,
              },
            ],
          },
        },
      },
    );
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [ambiguousSnap],
    });
    astroClockApiMock.confirmSnapContext
      .mockRejectedValueOnce(ambiguityError)
      .mockResolvedValueOnce({
        success: true,
        data: {
          persisted: false,
          original_preserved: true,
          replacement: {
            ...ambiguousSnap,
            id: 'snap-fold-preview',
            effective_datetime: '2026-11-01T06:30:00+00:00',
            local_datetime: '2026-11-01T01:30:00-05:00',
            calculation_context: { review_required: false },
          },
        },
      });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />,
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Correct context' }));
    const localInput = screen.getByLabelText('Confirmed local date and time');
    fireEvent.change(localInput, { target: { value: '2026-11-01' } });
    fireEvent.click(screen.getByRole('button', { name: 'Preview corrected chart' }));
    expect(await screen.findByText(/complete, valid local date and time/i)).toBeInTheDocument();
    expect(astroClockApiMock.confirmSnapContext).not.toHaveBeenCalled();

    fireEvent.change(localInput, { target: { value: '2026-11-01T01:30' } });
    fireEvent.click(screen.getByRole('button', { name: 'Preview corrected chart' }));
    expect(await screen.findByLabelText(/Second occurrence/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/First occurrence/i)).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText(/Second occurrence/i));
    fireEvent.click(screen.getByRole('button', { name: 'Preview corrected chart' }));
    await waitFor(() => {
      expect(astroClockApiMock.confirmSnapContext).toHaveBeenNthCalledWith(
        2,
        'snap-fold',
        expect.objectContaining({
          localDatetime: '2026-11-01T01:30:00-05:00',
          timezone: 'America/New_York',
          persist: false,
        }),
      );
    });
    expect(await screen.findByText('Corrected chart preview ready')).toBeInTheDocument();
  });

  it('confirms ordinary deletion and clears the active saved-chart link after success', async () => {
    const savedSnap = {
      id: 'snap-delete-active',
      label: 'Delete confirmation chart',
      effective_datetime: '2004-05-06T07:30:00+00:00',
      timezone: 'Europe/London',
      location: 'London, UK',
      latitude: 51.5072,
      longitude: -0.1276,
      calculation_context: { review_required: false },
      summary: {},
    };
    let deleted = false;
    astroClockApiMock.listSnaps.mockImplementation(async () => ({
      success: true,
      items: deleted ? [] : [savedSnap],
    }));
    astroClockApiMock.getSnap.mockResolvedValue({
      success: true,
      snap: savedSnap,
    });
    astroClockApiMock.deleteSnap.mockImplementation(async () => {
      deleted = true;
      return { success: true };
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />,
    );

    const card = (await screen.findByText('Delete confirmation chart')).closest('.rounded-2xl');
    fireEvent.click(within(card).getByRole('button', { name: 'Load' }));
    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: savedSnap.effective_datetime,
      }));
    });

    window.confirm.mockReturnValueOnce(false);
    fireEvent.click(within(card).getByRole('button', { name: 'Delete' }));
    expect(window.confirm).toHaveBeenLastCalledWith(expect.stringMatching(
      /Delete “Delete confirmation chart”.*corrected-copy relationship.*recovery backup is retained/i,
    ));
    expect(astroClockApiMock.deleteSnap).not.toHaveBeenCalled();

    window.confirm.mockReturnValueOnce(true);
    fireEvent.click(within(card).getByRole('button', { name: 'Delete' }));
    await waitFor(() => {
      expect(astroClockApiMock.deleteSnap).toHaveBeenCalledWith('snap-delete-active');
      expect(screen.queryByText('Delete confirmation chart')).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Transits' }));
    await waitFor(() => expect(screen.getByTestId('transits-modal')).toBeInTheDocument());
    expect(transitsModalMock.props.at(-1)?.initialNatalContext?.snapId).toBe('');
  });

  it('refreshes corrected-copy relationships after deleting the replacement', async () => {
    const original = {
      id: 'snap-original-linked',
      label: 'Original linked chart',
      effective_datetime: null,
      local_datetime: '2026-11-01T01:30:00-04:00',
      timezone: 'America/New_York',
      location: 'New York, USA',
      calculation_context: { review_required: true },
      superseded_by: 'snap-replacement-linked',
      summary: {},
    };
    const replacement = {
      id: 'snap-replacement-linked',
      label: 'Corrected replacement chart',
      effective_datetime: '2026-11-01T06:30:00+00:00',
      local_datetime: '2026-11-01T01:30:00-05:00',
      timezone: 'America/New_York',
      location: 'New York, USA',
      latitude: 40.7128,
      longitude: -74.006,
      calculation_context: { review_required: false },
      summary: {},
    };
    let replacementDeleted = false;
    astroClockApiMock.listSnaps.mockImplementation(async () => ({
      success: true,
      items: replacementDeleted
        ? [{ ...original, superseded_by: undefined }]
        : [original, replacement],
    }));
    astroClockApiMock.deleteSnap.mockImplementation(async (id) => {
      if (id === replacement.id) replacementDeleted = true;
      return { success: true };
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />,
    );

    const replacementCard = (
      await screen.findByText('Corrected replacement chart')
    ).closest('.rounded-2xl');
    fireEvent.click(within(replacementCard).getByRole('button', { name: 'Delete' }));
    await waitFor(() => {
      expect(astroClockApiMock.deleteSnap).toHaveBeenCalledWith('snap-replacement-linked');
      expect(screen.queryByText('Corrected replacement chart')).not.toBeInTheDocument();
    });

    const originalCard = screen.getByText('Original linked chart').closest('.rounded-2xl');
    expect(within(originalCard).getByRole('button', { name: 'Correct context' })).toBeEnabled();
    expect(within(originalCard).queryByRole('button', { name: 'Load corrected copy' })).not.toBeInTheDocument();
    expect(within(originalCard).getByRole('button', { name: 'Load' })).toBeDisabled();
  });

  it('refreshes saved snaps before building the search index when the local list is empty', async () => {
    const snapSummary = {
      id: 'snap-search',
      label: 'Legacy Search Snap',
      effective_datetime: '1996-09-07T11:15:00Z',
      location: 'Las Vegas',
      summary: { moon_sign: 'Leo' },
    };
    const fullSnap = {
      ...snapSummary,
      dashboard: {
        planets: [{ planet: 'Sun', sign: 'Leo', house: 10 }],
        top_aspects: [{ planet1: 'Moon', aspect: 'Trine', planet2: 'Venus' }],
      },
    };
    astroClockApiMock.listSnaps
      .mockResolvedValueOnce({ success: true, items: [] })
      .mockResolvedValue({ success: true, items: [snapSummary] });
    astroClockApiMock.getSnap.mockResolvedValue({ success: true, snap: fullSnap });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await waitFor(() => {
      expect(astroClockApiMock.listSnaps).toHaveBeenCalled();
    });
    const callsBeforeSearch = astroClockApiMock.listSnaps.mock.calls.length;

    fireEvent.click(screen.getByRole('button', { name: 'Search' }));

    await waitFor(() => {
      expect(astroClockApiMock.listSnaps.mock.calls.length).toBeGreaterThan(callsBeforeSearch);
    });
    await waitFor(() => {
      expect(astroClockApiMock.getSnap).toHaveBeenCalledWith('snap-search');
    });
    expect(await screen.findByText('Legacy Search Snap')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/Search label/i), { target: { value: 'moon trine venus' } });
    expect(await screen.findByText('Legacy Search Snap')).toBeInTheDocument();
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

    await findAnyText('Jerusalem, Israel');

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

    await findAnyText('Jerusalem, Israel');

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

  it('lets Realtime interrupt a stuck manual transition', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();
    astroClockApiMock.setMode.mockImplementation((payload = {}) => {
      if (payload?.mode === 'manual') {
        return new Promise((_resolve, reject) => {
          payload?.signal?.addEventListener?.('abort', () => {
            const error = new Error('manual transition aborted');
            error.name = 'AbortError';
            reject(error);
          });
        });
      }
      return Promise.resolve({ success: true });
    });

    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
      }));
    });

    fireEvent.click(screen.getByRole('button', { name: 'Realtime' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'realtime',
      }));
    });

    expect(screen.queryByText(/failed to switch astro clock/i)).not.toBeInTheDocument();
  });

  it('lets a saved snap load interrupt a stuck saved snap transition', async () => {
    const firstSnap = {
      id: 'snap-one',
      label: 'First Snap',
      effective_datetime: '1999-01-01T00:00:00Z',
      location: 'First Place',
      special_degrees: [],
    };
    const secondSnap = {
      id: 'snap-two',
      label: 'Second Snap',
      effective_datetime: '2000-02-02T00:00:00Z',
      location: 'Second Place',
      dashboard: { timezone: 'UTC', timezone_label: 'UTC' },
      special_degrees: [],
    };
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [firstSnap, secondSnap],
    });
    astroClockApiMock.getSnap.mockImplementation((id, opts = {}) => {
      if (id === 'snap-one') {
        return new Promise((_resolve, reject) => {
          opts?.signal?.addEventListener?.('abort', () => {
            const error = new Error('first snap load aborted');
            error.name = 'AbortError';
            reject(error);
          });
        });
      }
      return Promise.resolve({ success: true, snap: secondSnap });
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await screen.findByText('First Snap');
    await screen.findByText('Second Snap');
    const loadButtons = screen.getAllByRole('button', { name: 'Load' });

    fireEvent.click(loadButtons[0]);

    await waitFor(() => {
      expect(astroClockApiMock.getSnap).toHaveBeenCalledWith(
        'snap-one',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });

    fireEvent.click(loadButtons[1]);

    await waitFor(() => {
      expect(astroClockApiMock.getSnap).toHaveBeenCalledWith(
        'snap-two',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2000-02-02T00:00:00Z',
        location: 'Second Place',
      }));
    });
    expect(screen.queryByText(/failed to load the selected snap/i)).not.toBeInTheDocument();
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

    await findAnyText('Jerusalem, Israel');
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

    expect(await findAnyText('Jerusalem, Israel')).toBeInTheDocument();

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

    await findAnyText('Jerusalem, Israel');

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

    await findAnyText('Jerusalem, Israel');

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

    await findAnyText('Jerusalem, Israel');

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

    await screen.findByText('Live Signal');

    const card = screen.getByTestId('current-aspects-card');
    const morinToggle = within(card).getByTestId('current-aspects-morin-toggle');
    const footer = within(card).getByTestId('current-aspects-footer');

    expect(within(footer).getByText('Morin')).toBeInTheDocument();
    expect(within(footer).getByText('Decl')).toBeInTheDocument();
    expect(within(footer).getByRole('button', { name: 'More' })).toBeInTheDocument();
    expect(within(card).queryByText(/Exactness emphasizes/)).not.toBeInTheDocument();

    fireEvent.click(morinToggle);

    expect(morinToggle).toBeChecked();
    expect(within(card).getByTestId('current-aspects-scroll')).toBeInTheDocument();
    expect(within(card).getByText(/Mercury/)).toBeInTheDocument();
    expect(within(card).getAllByText(/Mars/).length).toBeGreaterThan(0);
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

    await screen.findByText('Live Signal');

    const card = screen.getByTestId('current-aspects-card');
    const morinToggle = within(card).getByTestId('current-aspects-morin-toggle');

    fireEvent.click(morinToggle);
    expect(morinToggle).toBeChecked();
    expect(within(card).getByText(/platic/)).toBeInTheDocument();
    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(2);
    });

    fireEvent.click(morinToggle);
    await waitFor(() => {
      expect(morinToggle).not.toBeChecked();
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(3);
    });

    fireEvent.click(morinToggle);
    await waitFor(() => {
      expect(astroClockApiMock.getDashboard.mock.calls.length).toBeGreaterThanOrEqual(4);
      expect(resolvePendingMorin).toBeTypeOf('function');
    });
    expect(astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0]).toMatchObject({ morin: true });
    expect(morinToggle).toBeChecked();
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

    await screen.findByText('Live Signal');

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

    await findAnyText('Jerusalem, Israel');

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

    await findAnyText('Greenwich, UK');

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
      expect(setModePayload?.latitude).toBeUndefined();
      expect(setModePayload?.longitude).toBeUndefined();
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
      expect(dashboardPayload?.latitude).toBeUndefined();
      expect(dashboardPayload?.longitude).toBeUndefined();
      expect(hoursPayload?.latitude).toBeUndefined();
      expect(hoursPayload?.longitude).toBeUndefined();
      expect(dashboardPayload?.snapId).toBeUndefined();
      expect(hoursPayload?.snapId).toBeUndefined();
    });
  });

  it('requires an explicit UTC-offset choice for repeated manual times and blocks DST gaps', async () => {
    astroClockApiMock.getDashboard.mockResolvedValue(
      makeDashboard({ location: 'New York, USA', timezone: 'America/New_York' }),
    );

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />,
    );

    await findAnyText('New York, USA');
    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));
    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
      }));
    });

    const ambiguousError = Object.assign(
      new Error('Local time occurs twice in America/New_York.'),
      {
        payload: {
          success: false,
          error_code: 'ambiguous_local_time',
          time_resolution: {
            code: 'ambiguous_local_time',
            wall_time_status: 'ambiguous_fold',
            candidates: [
              {
                fold: 0,
                local_datetime: '2026-11-01T01:30:00-04:00',
                utc_offset: '-04:00',
                instant_utc: '2026-11-01T05:30:00+00:00',
                valid: true,
              },
              {
                fold: 1,
                local_datetime: '2026-11-01T01:30:00-05:00',
                utc_offset: '-05:00',
                instant_utc: '2026-11-01T06:30:00+00:00',
                valid: true,
              },
            ],
          },
        },
      },
    );
    const gapError = Object.assign(
      new Error('Local time does not exist in America/New_York.'),
      {
        payload: {
          success: false,
          error_code: 'nonexistent_local_time',
          time_resolution: {
            code: 'nonexistent_local_time',
            wall_time_status: 'nonexistent_gap',
            candidates: [],
          },
        },
      },
    );
    astroClockApiMock.setMode.mockImplementation((payload) => {
      if (payload?.datetime === '2026-11-01T01:30:00') return Promise.reject(ambiguousError);
      if (payload?.datetime === '2026-03-08T02:30:00') return Promise.reject(gapError);
      return Promise.resolve({ success: true });
    });

    fireEvent.change(document.querySelector('#astroclock-manual-date'), {
      target: { value: '2026-11-01' },
    });
    fireEvent.change(document.querySelector('#astroclock-manual-time'), {
      target: { value: '01:30' },
    });
    fireEvent.change(document.querySelector('#astroclock-manual-location'), {
      target: { value: 'New York, USA' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    expect(await screen.findByLabelText(/Second occurrence/i)).toBeInTheDocument();
    expect(screen.getByText(/UTC-04:00.*05:30 UTC/i)).toBeInTheDocument();
    expect(screen.getByText(/UTC-05:00.*06:30 UTC/i)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Second occurrence/i));
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2026-11-01T01:30:00-05:00',
        location: 'New York, USA',
      }));
    });

    fireEvent.change(document.querySelector('#astroclock-manual-date'), {
      target: { value: '2026-03-08' },
    });
    fireEvent.change(document.querySelector('#astroclock-manual-time'), {
      target: { value: '02:30' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    expect(await screen.findByText(/does not exist in the selected timezone/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/First occurrence/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Second occurrence/i)).not.toBeInTheDocument();
  });

  it('does not reuse stale dashboard coordinates for an unsnapped manual forensic chart', async () => {
    astroClockApiMock.getDashboard.mockResolvedValue(makeDashboard({
      timestamp: '2005-10-19T11:15:00Z',
      location: 'Sadr City, Baghdad, Iraq',
      timezone: 'Asia/Baghdad',
      timezoneLabel: 'Asia/Baghdad (UTC+03:00)',
      latitude: 51.4769,
      longitude: -0.0005,
    }));

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Sadr City, Baghdad, Iraq');
    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      const initialManualPayload = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(initialManualPayload).toMatchObject({
        mode: 'manual',
        location: 'Sadr City, Baghdad, Iraq',
      });
      expect(initialManualPayload?.latitude).toBeUndefined();
      expect(initialManualPayload?.longitude).toBeUndefined();
    });

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    fireEvent.change(document.querySelector('#astroclock-manual-date'), {
      target: { value: '2005-10-19' },
    });
    fireEvent.change(document.querySelector('#astroclock-manual-time'), {
      target: { value: '14:15' },
    });
    fireEvent.change(document.querySelector('#astroclock-manual-location'), {
      target: { value: 'Sadr City, Baghdad, Iraq' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      const setModePayload = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(setModePayload).toMatchObject({
        mode: 'manual',
        datetime: '2005-10-19T14:15:00',
        location: 'Sadr City, Baghdad, Iraq',
      });
      expect(setModePayload?.latitude).toBeUndefined();
      expect(setModePayload?.longitude).toBeUndefined();

      const dashboardPayload = astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0];
      const hoursPayload = astroClockApiMock.getPlanetaryHours.mock.calls.at(-1)?.[0];
      expect(dashboardPayload?.latitude).toBeUndefined();
      expect(dashboardPayload?.longitude).toBeUndefined();
      expect(hoursPayload?.latitude).toBeUndefined();
      expect(hoursPayload?.longitude).toBeUndefined();
    });

    astroClockApiMock.getForensic.mockClear();
    fireEvent.click(screen.getByRole('button', { name: 'Forensic' }));

    await waitFor(() => {
      const forensicPayload = astroClockApiMock.getForensic.mock.calls.at(-1)?.[0];
      expect(forensicPayload).toMatchObject({
        mode: 'manual',
        datetime: '2005-10-19T14:15:00',
        location: 'Sadr City, Baghdad, Iraq',
        timezone: 'Asia/Baghdad',
      });
      expect(forensicPayload?.latitude).toBeUndefined();
      expect(forensicPayload?.longitude).toBeUndefined();
    });
  });

  it('snaps the applied manual chart instead of later draft control edits', async () => {
    astroClockApiMock.getDashboard.mockImplementation(async (payload = {}) => {
      if (payload?.mode === 'manual' && payload?.location === 'Israel') {
        return makeDashboard({
          timestamp: '2004-09-21T10:00:00Z',
          location: 'Israel',
          timezone: 'Asia/Jerusalem',
          latitude: 30.8124,
          longitude: 34.8595,
        });
      }
      return makeDashboard({
        timestamp: '2026-03-08T10:00:00Z',
        location: 'Greenwich, UK',
        timezone: 'Europe/London',
        latitude: 51.4769,
        longitude: -0.0005,
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

    await findAnyText('Greenwich, UK');
    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        location: 'Greenwich, UK',
      }));
    });

    const dateInput = document.querySelector('input[type="date"]');
    const timeInput = document.querySelector('input[type="time"]');
    const locationInput = document.querySelector('input[type="text"][placeholder="e.g., London, UK"]');

    fireEvent.change(dateInput, { target: { value: '2004-09-21' } });
    fireEvent.change(timeInput, { target: { value: '12:00' } });
    fireEvent.change(locationInput, { target: { value: 'Israel' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2004-09-21T12:00:00',
        location: 'Israel',
      }));
    });

    fireEvent.change(locationInput, { target: { value: 'Berlin, Germany' } });
    astroClockApiMock.createSnap.mockClear();
    fireEvent.click(screen.getByRole('button', { name: 'Snap' }));

    await waitFor(() => {
      const snapPayload = astroClockApiMock.createSnap.mock.calls.at(-1)?.[0];
      expect(snapPayload).toMatchObject({
        mode: 'manual',
        datetime: '2004-09-21T12:00:00',
        location: 'Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 30.8124,
        longitude: 34.8595,
      });
      expect(snapPayload?.location).not.toBe('Berlin, Germany');
      expect(snapPayload?.dashboard).toMatchObject({
        timestamp: '2004-09-21T10:00:00Z',
        location: 'Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 30.8124,
        longitude: 34.8595,
      });
    });
  });

  it('keeps the applied manual snap context across feature branches', async () => {
    const appliedDashboard = makeDashboard({
      timestamp: '2004-09-21T10:00:00Z',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 30.8124,
      longitude: 34.8595,
    });
    const savedSnap = {
      id: 'snap-manual',
      label: 'Manual Israel snap',
      effective_datetime: '2004-09-21T10:00:00+00:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      timezone_label: 'Asia/Jerusalem',
      latitude: 30.8124,
      longitude: 34.8595,
      dashboard: appliedDashboard.data,
      special_degrees: [],
    };
    let snapCreated = false;

    astroClockApiMock.getDashboard.mockImplementation(async (payload = {}) => (
      payload?.mode === 'manual'
        ? appliedDashboard
        : makeDashboard({
            timestamp: '2026-03-08T10:00:00Z',
            location: 'Greenwich, UK',
            timezone: 'Europe/London',
            latitude: 51.4769,
            longitude: -0.0005,
          })
    ));
    astroClockApiMock.listSnaps.mockImplementation(async () => ({
      success: true,
      items: snapCreated ? [savedSnap] : [],
    }));
    astroClockApiMock.createSnap.mockImplementation(async (payload = {}) => {
      snapCreated = true;
      savedSnap.dashboard = payload.dashboard;
      return { success: true, data: { id: 'snap-manual', label: savedSnap.label } };
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Greenwich, UK');
    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        location: 'Greenwich, UK',
      }));
      expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument();
    });

    const dateInput = document.querySelector('input[type="date"]');
    const timeInput = document.querySelector('input[type="time"]');
    const locationInput = document.querySelector('input[type="text"][placeholder="e.g., London, UK"]');

    fireEvent.change(dateInput, { target: { value: '2004-09-21' } });
    fireEvent.change(timeInput, { target: { value: '12:00' } });
    fireEvent.change(locationInput, { target: { value: 'Israel' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2004-09-21T12:00:00',
        location: 'Israel',
      }));
    });

    fireEvent.change(locationInput, { target: { value: 'Berlin, Germany' } });
    fireEvent.click(screen.getByRole('button', { name: 'Snap' }));

    await waitFor(() => {
      const snapPayload = astroClockApiMock.createSnap.mock.calls.at(-1)?.[0];
      expect(snapPayload).toMatchObject({
        mode: 'manual',
        datetime: '2004-09-21T12:00:00',
        location: 'Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 30.8124,
        longitude: 34.8595,
      });
      expect(snapPayload?.location).not.toBe('Berlin, Germany');
      expect(snapPayload?.dashboard).toMatchObject({
        timestamp: '2004-09-21T10:00:00Z',
        location: 'Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 30.8124,
        longitude: 34.8595,
      });
    });

    await waitFor(() => expect(astroClockApiMock.listSnaps).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: 'Synastry' }));
    await waitFor(() => expect(screen.getByTestId('synastry-modal')).toBeInTheDocument());
    expect(synastryModalMock.props.at(-1)).toMatchObject({
      activeSnapId: 'snap-manual',
    });
    expect(synastryModalMock.props.at(-1)?.snaps).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'snap-manual', location: 'Israel' }),
    ]));

    fireEvent.click(screen.getByRole('button', { name: 'Trait Profile' }));
    await waitFor(() => expect(screen.getByTestId('trait-profile-modal')).toBeInTheDocument());
    expect(traitProfileModalMock.props.at(-1)).toMatchObject({
      activeSnapId: 'snap-manual',
      manualIso: '2004-09-21T12:00:00',
      manualLocation: 'Israel',
      timezone: 'Asia/Jerusalem',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Transits' }));
    await waitFor(() => expect(screen.getByTestId('transits-modal')).toBeInTheDocument());
    expect(transitsModalMock.props.at(-1)?.initialNatalContext).toMatchObject({
      snapId: 'snap-manual',
      date: '2004-09-21',
      time: '12:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      houseSystem: 'R',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Astrocartography' }));
    await waitFor(() => expect(screen.getByTestId('astrocartography-modal')).toBeInTheDocument());
    expect(astrocartographyModalMock.props.at(-1)).toMatchObject({
      activeSnapId: 'snap-manual',
    });
    expect(astrocartographyModalMock.props.at(-1)?.initialTransitContext).toMatchObject({
      snapId: 'snap-manual',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Election' }));
    await waitFor(() => expect(screen.getByTestId('election-modal')).toBeInTheDocument());
    expect(electionModalMock.props.at(-1)).toMatchObject({
      activeSnapId: 'snap-manual',
    });
    expect(electionModalMock.props.at(-1)?.snaps).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'snap-manual' }),
    ]));

    astroClockApiMock.getForensic.mockClear();
    fireEvent.click(screen.getByRole('button', { name: 'Forensic' }));
    await waitFor(() => {
      expect(astroClockApiMock.getForensic).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2004-09-21T12:00:00',
        location: 'Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 30.8124,
        longitude: 34.8595,
        houseSystem: 'R',
      }));
    });
    expect(astroClockApiMock.getForensic.mock.calls.at(-1)?.[0]?.location).not.toBe('Berlin, Germany');

    fireEvent.click(screen.getByRole('button', { name: /Copy Prompt/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Natal prompt (copy)' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Mock Submit Prompt' }));

    await waitFor(() => expect(window.navigator.clipboard.writeText).toHaveBeenCalled());
    const copied = String(window.navigator.clipboard.writeText.mock.calls.at(-1)?.[0] || '');
    expect(copied).toContain('"timestamp": "2004-09-21T10:00:00Z"');
    expect(copied).toContain('"location": "Israel"');
    expect(copied).not.toContain('Berlin, Germany');
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
    astroClockApiMock.getSnap.mockResolvedValue({
      success: true,
      snap: {
        id: 'snap-nyc',
        label: 'Snap 1946-06-13 14:14:00+00:00 - New York',
        effective_datetime: '1946-06-13T14:14:00Z',
        location: 'New York',
        dashboard: { timezone: 'America/New_York', timezone_label: 'America/New_York' },
        special_degrees: [],
      },
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

    await waitFor(() => {
      const locationInput = document.querySelector('#astroclock-manual-location');
      expect(dateInput?.value).toBe('1946-06-13');
      expect(timeInput?.value).toBe('10:14');
      expect(locationInput?.value).toBe('New York');
    });

    fireEvent.click(screen.getByRole('button', { name: 'Realtime' }));

    await waitFor(() => {
      const realtimeSetMode = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      const autoLocationInput = document.querySelector('#astroclock-auto-location');
      expect(realtimeSetMode).toMatchObject({
        mode: 'realtime',
        location: 'Jerusalem, Israel',
        houseSystem: 'R',
      });
      expect(dateInput?.value).toBe('2026-03-08');
      expect(timeInput?.value).toBe('12:00');
      expect(autoLocationInput?.value).toBe('Jerusalem, Israel');
    });

    expect(await findAnyText('Asia/Jerusalem (UTC+02:00)')).toBeInTheDocument();

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

  it('keeps manual location edits inside manual mode instead of forcing realtime', async () => {
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

    await findAnyText('Jerusalem, Israel');
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

    const locationInput = document.querySelector('input[type="text"][placeholder="e.g., London, UK"]');
    fireEvent.change(locationInput, {
      target: { value: 'Berlin, Germany' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        location: 'Berlin, Germany',
      }));
    });

    expect(astroClockApiMock.setMode.mock.calls.some(([payload]) => (
      payload?.mode === 'realtime' && payload?.location === 'Berlin, Germany'
    ))).toBe(false);

    await waitFor(() => {
      expect(locationInput?.value).toBe('Berlin, Germany');
    });

    const timezoneMatches = await screen.findAllByText(
      (_, node) => node?.textContent?.includes('Europe/Berlin (UTC+01:00)') ?? false
    );
    expect(timezoneMatches.length).toBeGreaterThan(0);
  });

  it('lets automatic location edits update the active live chart context', async () => {
    astroClockApiMock.getDashboard.mockImplementation(async (payload = {}) => {
      if (payload?.mode === 'realtime' && payload?.location === 'New York') {
        return makeDashboard({
          location: 'New York',
          timezone: 'America/New_York',
          timezoneLabel: 'America/New_York (UTC-04:00)',
        });
      }
      return makeDashboard();
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');

    const locationInput = document.querySelector('#astroclock-auto-location');
    fireEvent.change(locationInput, {
      target: { value: 'New York' },
    });

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    fireEvent.click(screen.getAllByRole('button', { name: 'Refresh' })[0]);

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledTimes(1);
      const setModePayload = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(setModePayload).toMatchObject({
        mode: 'realtime',
        location: 'New York',
        houseSystem: 'R',
      });
      expect(setModePayload?.datetime).toBeUndefined();
      expect(setModePayload?.timezone).toBeUndefined();
      expect(setModePayload?.latitude).toBeUndefined();
      expect(setModePayload?.longitude).toBeUndefined();

      const dashboardPayload = astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0];
      expect(dashboardPayload).toMatchObject({
        mode: 'realtime',
        location: 'New York',
        houseSystem: 'R',
      });
      expect(dashboardPayload?.datetime).toBeUndefined();
    });

    expect(await findAnyText('America/New_York (UTC-04:00)')).toBeInTheDocument();
  });

  it('keeps automatic location edits as drafts until refresh after returning from manual', async () => {
    const eventSource = { close: vi.fn(), onmessage: null, onerror: null };
    astroClockApiMock.createStream.mockResolvedValue(eventSource);
    astroClockApiMock.getDashboard.mockImplementation(async (payload = {}) => {
      if (payload?.mode === 'realtime' && payload?.location === 'New York') {
        return makeDashboard({
          location: 'New York',
          timezone: 'America/New_York',
          timezoneLabel: 'America/New_York (UTC-04:00)',
        });
      }
      return makeDashboard({
        timestamp: payload?.datetime || '2026-03-08T10:00:00Z',
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

    await findAnyText('Jerusalem, Israel');
    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        location: 'Jerusalem, Israel',
      }));
    });

    fireEvent.click(screen.getByRole('button', { name: 'Realtime' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode.mock.calls.at(-1)?.[0]).toMatchObject({
        mode: 'realtime',
        location: 'Jerusalem, Israel',
        houseSystem: 'R',
      });
      expect(typeof eventSource.onmessage).toBe('function');
    });

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    const locationInput = document.querySelector('#astroclock-auto-location');
    fireEvent.change(locationInput, {
      target: { value: 'New York' },
    });

    await act(async () => {
      eventSource.onmessage?.({ data: 'tick-with-draft-location' });
    });

    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledTimes(1);
    });
    const heartbeatPayload = astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0];
    expect(heartbeatPayload).toMatchObject({
      mode: 'realtime',
      location: 'Jerusalem, Israel',
      houseSystem: 'R',
    });
    expect(heartbeatPayload?.timezone).toBeUndefined();
    expect(heartbeatPayload?.snapId).toBeUndefined();

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    fireEvent.click(screen.getAllByRole('button', { name: 'Refresh' })[0]);

    await waitFor(() => {
      expect(astroClockApiMock.setMode.mock.calls.at(-1)?.[0]).toMatchObject({
        mode: 'realtime',
        location: 'New York',
        houseSystem: 'R',
      });
      expect(astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0]).toMatchObject({
        mode: 'realtime',
        location: 'New York',
        houseSystem: 'R',
      });
      expect(astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0]?.snapId).toBeUndefined();
      expect(astroClockApiMock.getPlanetaryHours.mock.calls.at(-1)?.[0]?.snapId).toBeUndefined();
    });
  });

  it('does not replay stale coordinates when refreshing an auto-filled realtime location', async () => {
    astroClockApiMock.getDashboard.mockResolvedValue(makeDashboard({
      location: 'Sadr City, Baghdad, Iraq',
      timezone: 'Europe/London',
      timezoneLabel: 'Europe/London (UTC+01:00)',
      latitude: 51.4769,
      longitude: -0.0005,
    }));

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Sadr City, Baghdad, Iraq');

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();

    fireEvent.click(screen.getAllByRole('button', { name: 'Refresh' })[0]);

    await waitFor(() => {
      const setModePayload = astroClockApiMock.setMode.mock.calls.at(-1)?.[0];
      expect(setModePayload).toMatchObject({
        mode: 'realtime',
        location: 'Sadr City, Baghdad, Iraq',
        houseSystem: 'R',
      });
      expect(setModePayload?.timezone).toBeUndefined();
      expect(setModePayload?.latitude).toBeUndefined();
      expect(setModePayload?.longitude).toBeUndefined();

      const dashboardPayload = astroClockApiMock.getDashboard.mock.calls.at(-1)?.[0];
      const hoursPayload = astroClockApiMock.getPlanetaryHours.mock.calls.at(-1)?.[0];
      expect(dashboardPayload).toMatchObject({
        mode: 'realtime',
        location: 'Sadr City, Baghdad, Iraq',
      });
      expect(dashboardPayload?.timezone).toBeUndefined();
      expect(dashboardPayload?.latitude).toBeUndefined();
      expect(dashboardPayload?.longitude).toBeUndefined();
      expect(hoursPayload?.timezone).toBeUndefined();
      expect(hoursPayload?.latitude).toBeUndefined();
      expect(hoursPayload?.longitude).toBeUndefined();
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

    expect(await findAnyText('Jerusalem, Israel')).toBeInTheDocument();
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

    await findAnyText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Transits' }));

    await waitFor(() => {
      expect(screen.getByTestId('transits-modal')).toBeInTheDocument();
    });

    const latestProps = transitsModalMock.props.at(-1);
    expect(latestProps?.defaultHouseSystem).toBe('W');
    expect(latestProps?.open).toBe(true);
  });

  it('shows Placidus as a selectable Astro Clock house system', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');

    const selector = screen.getByTitle('House system');
    expect(within(selector).getByRole('option', { name: 'Placidus (P)' })).toBeInTheDocument();
  });

  it('opens the in-app premium offer instead of the website for locked astrocartography', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
      />
    );

    await waitForDashboardReady();

    fireEvent.click(screen.getByRole('button', { name: 'Astrocartography' }));

    expectPremiumOffer('Astrocartography');
    expect(screen.queryByTestId('astrocartography-modal')).not.toBeInTheDocument();
  });

  it('passes the same premium gate into the Directional 3D tile action', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
      />
    );

    await waitForDashboardReady();

    const latestProps = compassTileMock.props.at(-1);
    expect(latestProps?.directional3dLocked).toBe(true);
    expect(latestProps?.directional3dLockedTitle).toBe('Premium feature - unlock Vox Stella to use this workflow');

    act(() => {
      latestProps?.onDirectional3dLocked?.();
    });

    expectPremiumOffer('Directional 3D');
  });

  it('passes the same premium gate into the Degree Hits More action', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
      />
    );

    await waitForDashboardReady();

    const latestProps = degreeHitsTileMock.props.at(-1);
    expect(latestProps?.detailsLocked).toBe(true);
    expect(latestProps?.detailsLockedTitle).toBe('Premium feature - unlock Vox Stella to use this workflow');

    act(() => {
      latestProps?.onDetailsLocked?.();
    });

    expectPremiumOffer('Degree Hits');
  });

  it('opens the in-app premium offer instead of Chinese Astrology for unverified packaged users', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
      />
    );

    await waitForDashboardReady();

    fireEvent.click(screen.getByRole('button', { name: 'Chinese Astrology' }));

    expectPremiumOffer('Chinese Astrology');
    expect(screen.queryByTestId('chinese-astrology-page')).not.toBeInTheDocument();
  });

  it('allows unverified packaged users to use realtime mode', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
      />
    );

    await findAnyText('Jerusalem, Israel');

    expect(screen.getByRole('button', { name: 'Realtime' })).toHaveClass('bg-zinc-900');

    fireEvent.click(screen.getByRole('button', { name: 'Manual' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
      }));
    });

    astroClockApiMock.setMode.mockClear();
    window.electronAPI.openExternal.mockClear();

    fireEvent.click(screen.getByRole('button', { name: 'Realtime' }));

    await waitFor(() => {
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'realtime',
      }));
    });

    expect(window.electronAPI.openExternal).not.toHaveBeenCalled();
  });

  it('does not consume a packaged feature click while license status is still loading', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
        licenseChecking
      />
    );

    await findAnyText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Synastry' }));

    await waitFor(() => {
      expect(screen.getByTestId('synastry-modal')).toBeInTheDocument();
    });
    expect(window.electronAPI.openExternal).not.toHaveBeenCalled();
  });

  it('shows the premium action rail above the clock controls for unverified packaged users', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
      />
    );

    await waitForDashboardReady();

    const synastryButton = screen.getByRole('button', { name: 'Synastry' });
    const realtimeButton = screen.getByRole('button', { name: 'Realtime' });
    const certificationButton = screen.getByRole('button', { name: 'Certification' });
    const copyPromptButton = screen.getByRole('button', { name: /Copy Prompt/ });

    expect(synastryButton.compareDocumentPosition(realtimeButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(synastryButton).toHaveClass('bg-red-600');
    expect(certificationButton).toHaveClass('bg-red-600');
    expect(copyPromptButton).toHaveClass('bg-red-600');
  });

  it('opens Certification from the action rail and keeps Copy Prompt beside Apply', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await waitForDashboardReady();

    const forensicButton = screen.getByRole('button', { name: 'Forensic' });
    const certificationButton = screen.getByRole('button', { name: 'Certification' });
    const copyPromptButton = screen.getByRole('button', { name: 'Copy Prompt' });
    const applyButton = screen.getByRole('button', { name: 'Apply' });
    const controlStrip = screen.getByTestId('astro-clock-control-strip');

    expect(forensicButton.compareDocumentPosition(certificationButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(applyButton.compareDocumentPosition(copyPromptButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(controlStrip).toHaveClass('min-w-0');
    expect(controlStrip).toHaveClass('max-w-full');
    expect(controlStrip).not.toHaveClass('md:min-w-[1152px]');
    expect(controlStrip).not.toHaveClass('lg:min-w-[1160px]');
    expect(copyPromptButton).toHaveClass('h-9');
    expect(copyPromptButton).toHaveClass('w-9');
    expect(copyPromptButton).toHaveClass('rounded-full');

    fireEvent.click(certificationButton);

    await waitFor(() => {
      expect(screen.getByTestId('birth-certification-modal')).toBeInTheDocument();
    });
    expect(birthCertificationModalMock.props.at(-1)).toMatchObject({
      open: true,
      manualLocation: 'Jerusalem, Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });
  });

  it('opens the in-app premium offer from Certification for unverified packaged users', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
      />
    );

    await waitForDashboardReady();

    fireEvent.click(screen.getByRole('button', { name: 'Certification' }));

    expectPremiumOffer('Certification');
    expect(screen.queryByTestId('birth-certification-modal')).not.toBeInTheDocument();
  });

  it('opens the in-app premium offer from the premium copy prompt utility', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive={false}
      />
    );

    await waitForDashboardReady();

    fireEvent.click(screen.getByRole('button', { name: /Copy Prompt/ }));

    expectPremiumOffer('AI prompt utility');
    expect(screen.queryByRole('button', { name: 'Natal prompt (copy)' })).not.toBeInTheDocument();
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

    await findAnyText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Astrocartography' }));

    await waitFor(() => {
      expect(screen.getByTestId('astrocartography-modal')).toBeInTheDocument();
    });

    expect(window.electronAPI.openExternal).not.toHaveBeenCalled();
    const latestProps = astrocartographyModalMock.props.at(-1);
    expect(latestProps?.open).toBe(true);
  });

  it('opens Chinese Astrology for verified packaged users', async () => {
    window.IS_PACKAGED = true;

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Chinese Astrology' }));

    await waitFor(() => {
      expect(screen.getByTestId('chinese-astrology-page')).toBeInTheDocument();
    });

    expect(window.electronAPI.openExternal).not.toHaveBeenCalled();
    const latestProps = chineseAstrologyPageMock.props.at(-1);
    expect(latestProps?.activeSnapId).toBe('');
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

    await findAnyText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: 'Synastry' }));

    await waitFor(() => {
      expect(screen.getByTestId('synastry-modal')).toBeInTheDocument();
    });

    const latestProps = synastryModalMock.props.at(-1);
    expect(latestProps?.open).toBe(true);
    expect(latestProps?.defaultHouseSystem).toBeUndefined();
  });

  it('opens synastry without waiting for a realtime pause snapshot', async () => {
    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    await findAnyText('Jerusalem, Israel');

    astroClockApiMock.setMode.mockClear();
    astroClockApiMock.setMode.mockImplementation(() => new Promise(() => {}));

    fireEvent.click(screen.getByRole('button', { name: 'Synastry' }));

    await waitFor(() => {
      expect(screen.getByTestId('synastry-modal')).toBeInTheDocument();
    });

    expect(astroClockApiMock.setMode).not.toHaveBeenCalled();
  });

  it('passes the active loaded snap context into the transit modal', async () => {
    const loadedSnap = {
      id: 'snap-israel',
      label: 'Snap 1948-05-14 14:00:00+00:00 - israel',
      effective_datetime: '1948-05-14T14:00:00Z',
      location: 'israel',
      dashboard: {
        timezone: 'Asia/Jerusalem',
        timezone_label: 'Asia/Jerusalem',
        latitude: 31.778,
        longitude: 35.235,
      },
      special_degrees: [],
    };
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [loadedSnap],
    });
    astroClockApiMock.getSnap.mockResolvedValue({
      success: true,
      snap: loadedSnap,
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
        timezone: 'Asia/Jerusalem',
        latitude: 31.778,
        longitude: 35.235,
      }));
    });

    await waitFor(() => {
      expect(receptionsTileMock.props.at(-1)?.clockContext).toMatchObject({
        snapId: 'snap-israel',
        houseSystem: 'R',
      });
      expect(degreeHitsTileMock.props.at(-1)?.pointsContext).toMatchObject({
        snapId: 'snap-israel',
        houseSystem: 'R',
      });
    });
    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledWith(
        expect.objectContaining({
          snapId: 'snap-israel',
          houseSystem: 'R',
        }),
      );
      expect(astroClockApiMock.getPlanetaryHours).toHaveBeenCalledWith(
        expect.objectContaining({
          snapId: 'snap-israel',
          houseSystem: 'R',
        }),
      );
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
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });

    astroClockApiMock.getForensic.mockClear();
    fireEvent.click(screen.getByRole('button', { name: 'Forensic' }));
    await waitFor(() => {
      expect(astroClockApiMock.getForensic).toHaveBeenCalledWith(
        expect.objectContaining({
          snapId: 'snap-israel',
          houseSystem: 'R',
        }),
      );
    });

    astroClockApiMock.getDashboard.mockClear();
    astroClockApiMock.getPlanetaryHours.mockClear();
    fireEvent.change(screen.getByTitle('House system'), {
      target: { value: 'P' },
    });
    await waitFor(() => {
      expect(astroClockApiMock.getDashboard).toHaveBeenCalledWith(
        expect.objectContaining({
          snapId: 'snap-israel',
          houseSystem: 'P',
        }),
      );
      expect(astroClockApiMock.getPlanetaryHours).toHaveBeenCalledWith(
        expect.objectContaining({
          snapId: 'snap-israel',
          houseSystem: 'P',
        }),
      );
    });
  });

  it('hydrates legacy snap details before applying manual context', async () => {
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [
        {
          id: 'snap-legacy',
          label: 'Snap 2003-02-10 08:45:00+00:00 - israel',
          effective_datetime: '2003-02-10T08:45:00+00:00',
          location: 'israel',
          dashboard: {
            timezone: null,
            timezone_label: null,
            latitude: null,
            longitude: null,
          },
          special_degrees: [],
        },
      ],
    });
    astroClockApiMock.getSnap.mockResolvedValue({
      success: true,
      snap: {
        id: 'snap-legacy',
        label: 'Snap 2003-02-10 08:45:00+00:00 - israel',
        effective_datetime: '2003-02-10T08:45:00+00:00',
        location: 'israel',
        timezone: 'Asia/Jerusalem',
        timezone_label: 'Asia/Jerusalem',
        latitude: 30.8124,
        longitude: 34.8595,
        dashboard: {
          timezone: 'Asia/Jerusalem',
          timezone_label: 'Asia/Jerusalem',
          latitude: 30.8124,
          longitude: 34.8595,
        },
        special_degrees: [],
      },
    });

    render(
      <AstroClock
        darkMode={false}
        setCurrentView={vi.fn()}
        apiStatus="ok"
        licenseActive
      />
    );

    expect(await screen.findByText('Snap 2003-02-10 08:45:00+00:00 - israel')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Load' }));

    await waitFor(() => {
      expect(astroClockApiMock.getSnap).toHaveBeenCalledWith(
        'snap-legacy',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
      expect(astroClockApiMock.setMode).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'manual',
        datetime: '2003-02-10T08:45:00+00:00',
        location: 'israel',
        timezone: 'Asia/Jerusalem',
        latitude: 30.8124,
        longitude: 34.8595,
      }));
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
    await findAnyText('israel');

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

    await findAnyText('Jerusalem, Israel');

    fireEvent.click(screen.getByRole('button', { name: /Copy Prompt/ }));
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
        payload?.location === 'Jerusalem, Israel' &&
        payload?.timezone === 'Asia/Jerusalem' &&
        payload?.latitude === 31.778 &&
        payload?.longitude === 35.235
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
        latitude: 31.778,
        longitude: 35.235,
        houseSystem: 'R',
      }));
    });
  });

  it('lets forensic switch to a saved snap without replacing its persisted house system', async () => {
    global.localStorage.getItem.mockImplementation((key) => (
      key === 'vox_stella_house_system_code' ? 'P' : null
    ));
    astroClockApiMock.listSnaps.mockResolvedValue({
      success: true,
      items: [
        {
          id: 'snap-vegas',
          label: 'Snap 1996-09-07 11:15:00+00:00 - Las Vegas',
          effective_datetime: '1996-09-07T11:15:00Z',
          location: 'Las Vegas, Nevada',
          calculation_context: {
            house_system_code: 'R',
          },
          dashboard: {
            timezone: 'America/Los_Angeles',
            timezone_label: 'America/Los_Angeles',
            latitude: 36.1699,
            longitude: -115.1398,
          },
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

    expect(await screen.findByText('Snap 1996-09-07 11:15:00+00:00 - Las Vegas')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Forensic' }));

    await waitFor(() => {
      expect(astroClockApiMock.getForensic).toHaveBeenCalledWith(expect.objectContaining({
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
      }));
    });

    astroClockApiMock.getForensic.mockClear();
    fireEvent.click(await screen.findByRole('button', { name: 'Saved Snap' }));

    await waitFor(() => {
      expect(screen.getByLabelText('Forensic saved snap')).toHaveValue('snap-vegas');
      expect(astroClockApiMock.getForensic).toHaveBeenCalledWith(expect.objectContaining({
        snapId: 'snap-vegas',
        houseSystem: 'R',
        caseType: 'general',
      }));
      expect(astroClockApiMock.getForensic).not.toHaveBeenCalledWith(expect.objectContaining({
        snapId: 'snap-vegas',
        houseSystem: 'P',
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
    expect(screen.queryByText(/not scientific forensic evidence/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/must not be used to identify people/i)).not.toBeInTheDocument();
    expect(screen.getByText('Symbolic Rule Score')).toBeInTheDocument();
    expect(screen.queryByText(/\/100 pressure/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Symbolic Brief · Copy' }));
    await waitFor(() => expect(window.navigator.clipboard.writeText).toHaveBeenCalled());
    const copiedBrief = String(window.navigator.clipboard.writeText.mock.calls.at(-1)?.[0] || '');
    expect(copiedBrief).toMatch(/summarize the forensic astrology rule output below/i);
    expect(copiedBrief).not.toMatch(/not scientific forensic evidence|statistical prediction/i);
    expect(copiedBrief).not.toMatch(/do not identify|assign guilt|investigative action/i);
    expect(copiedBrief).not.toMatch(/composite portrait|profiling image/i);
  });

  it('shows forensic fetch failures in the dossier findings view', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    astroClockApiMock.getForensic.mockRejectedValueOnce(new Error('Forensic backend down'));

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

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/forensic dossier/i);
    expect(alert).toHaveTextContent(/Forensic backend down/i);
    expect(screen.queryByText(/Abduction fetch failed/i)).not.toBeInTheDocument();

    consoleErrorSpy.mockRestore();
  });

  it('escapes forensic report HTML and does not attempt a denied popup after Electron export failure', async () => {
    const rawLocation = '<img src=x onerror=alert(1)>';
    const exportReport = vi.fn().mockResolvedValue({ ok: false, error: 'PDF generation failed' });
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      writable: true,
      value: {
        openExternal: vi.fn(),
        exportReport,
      },
    });
    const openSpy = vi.spyOn(window, 'open').mockReturnValue(null);
    astroClockApiMock.getForensic.mockResolvedValue({
      ...makeForensicPayload(),
      location: rawLocation,
      timezone_label: '<b>Unsafe TZ</b>',
    });

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
    fireEvent.click(screen.getByRole('button', { name: 'Export PDF' }));

    await waitFor(() => expect(exportReport).toHaveBeenCalledTimes(1));
    const html = exportReport.mock.calls[0][0]?.html || '';
    expect(html).not.toContain(rawLocation);
    expect(html).not.toContain('<img src=x');
    expect(html).not.toContain('<b>Unsafe TZ</b>');
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
    expect(html).toContain('&lt;b&gt;Unsafe TZ&lt;/b&gt;');
    expect(html).not.toMatch(/symbolic astrological interpretation only|not scientific forensic evidence/i);
    expect(html).not.toMatch(/identification method|probability of location, safety, or outcome/i);
    expect(await screen.findByText('Export failed: PDF generation failed')).toBeInTheDocument();
    expect(openSpy).not.toHaveBeenCalled();

    openSpy.mockRestore();
  });

  it('ignores stale forensic responses after switching case type', async () => {
    let resolveGeneral;
    let resolveChild;
    const generalPromise = new Promise((resolve) => { resolveGeneral = resolve; });
    const childPromise = new Promise((resolve) => { resolveChild = resolve; });
    astroClockApiMock.getForensic
      .mockReturnValueOnce(generalPromise)
      .mockReturnValueOnce(childPromise);

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

    await waitFor(() => {
      expect(astroClockApiMock.getForensic).toHaveBeenCalledWith(expect.objectContaining({
        caseType: 'general',
      }));
    });

    fireEvent.click(await screen.findByRole('button', { name: 'Child' }));

    await waitFor(() => {
      expect(astroClockApiMock.getForensic).toHaveBeenCalledWith(expect.objectContaining({
        caseType: 'child',
      }));
    });

    await act(async () => {
      resolveChild({
        ...makeForensicPayload(),
        location: 'Child case current',
        survivability: {
          level: 'Moderate',
          score: 0,
          outcome_band: 'release_favored',
          case_type: 'child',
          victim_significators: ['Mercury', 'Moon'],
          breakdown: { fatal_pressure: 0, danger: 0 },
          note: 'Current child response',
        },
        relationship_status: {
          primary_label: 'family',
          labels: ['family'],
          confidence: 'High',
          scores: { family: 3 },
          evidence: { family: ['child current'] },
        },
      });
      await childPromise;
    });

    expect((await screen.findAllByText('Child case current')).length).toBeGreaterThanOrEqual(1);

    await act(async () => {
      resolveGeneral({
        ...makeForensicPayload(),
        location: 'Stale general case',
        survivability: {
          level: 'Lower',
          score: -4,
          outcome_band: 'fatal_pressure_dominant',
          case_type: 'general',
          victim_significators: ['Venus', 'Moon'],
          breakdown: { fatal_pressure: 5, danger: 3 },
          note: 'Stale general response',
        },
      });
      await generalPromise;
    });

    expect(screen.queryAllByText('Stale general case')).toHaveLength(0);
    expect(screen.getAllByText('Child case current').length).toBeGreaterThanOrEqual(1);
  });

  it('includes backend relationship status in forensic raw evidence', async () => {
    astroClockApiMock.getForensic.mockResolvedValue({
      ...makeForensicPayload(),
      relationship_status: {
        primary_label: 'family',
        labels: ['family'],
        confidence: 'High',
        scores: { family: 3.4 },
        evidence: { family: ['home-axis cluster'] },
      },
    });

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
    fireEvent.click(screen.getByRole('button', { name: 'Raw' }));

    expect(await screen.findByText(/relationship_status/)).toBeInTheDocument();
    expect(screen.getByText(/home-axis cluster/)).toBeInTheDocument();
  });

  it('uses one backend Moon-dispositor result for the relationship headline, score, and evidence', async () => {
    astroClockApiMock.getForensic.mockResolvedValue({
      ...makeForensicPayload(),
      relationship_status: {
        primary_label: 'friend_acquaintance',
        labels: ['friend_acquaintance'],
        confidence: 'Low',
        scores: { friend_acquaintance: 1.75 },
        evidence: {
          friend_acquaintance: [
            'Moon dispositor Mercury opposition seventh ruler Saturn with transport-harm testimony',
          ],
        },
        moon_dispositor_relationship_component: {
          eligible: true,
          label_gate_met: true,
        },
      },
    });

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
    fireEvent.click(screen.getByRole('tab', { name: 'Relationship' }));

    expect(await screen.findByText('Relationship Signals')).toBeInTheDocument();
    expect(screen.getByText('1.75')).toBeInTheDocument();
    expect(screen.getAllByText('Friend/associate link').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Moon dispositor Mercury opposition seventh ruler Saturn/)).toBeInTheDocument();
    expect(screen.queryByText('Stranger/Random')).not.toBeInTheDocument();
  });

  it('presents simple lowercase forensic locations with title casing in the dossier header', async () => {
    astroClockApiMock.getForensic.mockResolvedValue({
      ...makeForensicPayload(),
      location: 'london',
      timezone: 'Europe/London',
      timezone_label: 'Europe/London (UTC+01:00)',
    });

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

    expect((await screen.findAllByText('London')).length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText('london')).toHaveLength(0);
  });

  it('renders forensic light-mediation impact without internal calibration wording', async () => {
    astroClockApiMock.getForensic.mockResolvedValue({
      ...makeForensicPayload(),
      survivability: {
        level: 'Lower',
        score: 3.85,
        outcome_band: 'fatal_pressure_dominant',
        case_type: 'adult_female',
        victim_significators: ['Jupiter', 'Moon'],
        breakdown: {
          vitality: 7,
          accidental: 1.1,
          support: 0,
          recovery_support: 0.25,
          light_mediation: 0.25,
          moon: -0.5,
          danger: 0,
          fatal_pressure: 4,
        },
        evidence: {
          light_mediation: ['favorable collection by Moon +0.25 recovery support'],
        },
        light_mediation_impact: {
          effect: 'recovery_support',
          tilt: 'recovery_mitigated',
          light_mediation_score: 0.25,
          score_without_light_mediation: 3.6,
          score_delta: 0.25,
          level_without_light_mediation: 'Lower',
          outcome_band_without_light_mediation: 'fatal_pressure_dominant',
          level_changed: false,
          band_changed: false,
          visibility: 'raw_only',
        },
        note: 'Fatal mechanism testimony outweighs base vitality unless rescue or recovery support is strong.',
      },
    });

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

    expect(await screen.findByText('Light Mediation Impact')).toBeInTheDocument();
    expect(await screen.findByText('+0.25 recovery support')).toBeInTheDocument();
    expect(await screen.findByText('recovery mitigated')).toBeInTheDocument();
    expect(await screen.findByText('Without light mediation: +3.6 · Lower · fatal-pressure dominant')).toBeInTheDocument();
    expect(screen.queryByText(/Visible as raw score movement/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Final level and band stayed stable/i)).not.toBeInTheDocument();
  });

  it('renders the McIntosh ASC-ruler placement in the victim tab', async () => {
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
    fireEvent.click(screen.getByRole('tab', { name: 'Victim' }));

    expect(await screen.findByText(/ASC-ruler placement/i)).toBeInTheDocument();
    expect(await screen.findByText(/Venus in H6/i)).toBeInTheDocument();
    expect(await screen.findByText(/routine activity interrupted/i)).toBeInTheDocument();
  });

  it('renders forensic current-chart time in the chart timezone, not the browser timezone', async () => {
    astroClockApiMock.getForensic.mockResolvedValue({
      ...makeForensicPayload(),
      timestamp: '2022-07-31T09:30:00+00:00',
      location: 'Strongsville, Ohio',
      timezone: 'America/New_York',
      timezone_label: 'America/New_York (UTC-04:00)',
    });

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

    expect((await screen.findAllByText('Strongsville, Ohio')).length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText(/05:30\s*AM/i)).toBeInTheDocument();
    expect(screen.getByText('America/New_York (UTC-04:00)')).toBeInTheDocument();
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
