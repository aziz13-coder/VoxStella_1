import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';

const astroClockApiMock = vi.hoisted(() => ({
  listSnaps: vi.fn(),
  createTransitsWindowStream: vi.fn(),
  getTransitsWindow: vi.fn(),
  getTransits: vi.fn(),
  getPredictions: vi.fn(),
  getAutoContext: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

import TransitsModal, { buildTransitIso } from '../features/astroclock/TransitsModal.jsx';

function makeWindowResponse({
  timezone,
  timestamp,
  eventType,
  lifeArea,
  description,
  predictionTags = [],
  significance = 60,
  stepScore = null,
  tone = 'positive',
  count = 1,
  rowPredictions = null,
  topHits = null,
}) {
  const defaultTopHit = {
    transiting: 'Jupiter',
    aspect: 'Trine',
    target_label: 'Sun',
    orb: 0.24,
    tone,
    significance,
    prediction_score: significance,
    prediction_tags: predictionTags,
    prediction: {
      description,
      lifeArea: lifeArea,
      eventType: eventType,
    },
    laws_applied: [
      {
        applies: true,
        lawNumber: 11,
        lawName: 'Benefics to MC Promise Honors',
        strengthModifier: 0.8,
      },
    ],
  };
  return {
    data: {
      natal: {
        timezone,
      },
      series: [
        {
          timestamp,
          count,
          step_score: stepScore ?? significance,
          moon_support: false,
          top: Array.isArray(topHits) && topHits.length ? topHits : [defaultTopHit],
          predictions: Array.isArray(rowPredictions) && rowPredictions.length
            ? rowPredictions
            : [
                {
                  date: timestamp,
                  description,
                  event_type: eventType,
                  life_area: lifeArea,
                  score: significance,
                  probability: 1.0,
                },
              ],
        },
      ],
      peaks: [{ timestamp }],
      prediction_card: null,
      context_window: null,
    },
  };
}

function makeSingleTransitResponse({
  natalLocation,
  timezone,
  houseSystem = 'W',
  transitTimestamp,
  transiting,
  targetLabel,
  aspect,
  lifeArea,
  eventType,
  description,
  enrichedKeywords,
  keywords,
  predictionTags,
  significance,
  orb = 0.24,
  longitudeOrb,
  orbBasis,
  tone = 'positive',
  revolutions = null,
  evidenceLevel = null,
  confidence = null,
}) {
  return {
    data: {
      natal: {
        location: natalLocation,
        timezone,
        house_system_code: houseSystem,
      },
      transit_timestamp: transitTimestamp,
      count: 1,
      moon_support: false,
      predictions: [
        {
          date: transitTimestamp,
          description,
          event_type: eventType,
          life_area: lifeArea,
          score: significance,
          probability: 1.0,
        },
      ],
      revolutions: revolutions || undefined,
      transits: [
        {
          transiting,
          target_label: targetLabel,
          natal: targetLabel,
          aspect,
          orb,
          longitude_orb: longitudeOrb,
          orb_basis: orbBasis,
          phase: 'applying',
          direction: 'sinister',
          effectiveWindow: {
            start: transitTimestamp,
            end: transitTimestamp,
          },
          prediction: {
            description,
            lifeArea: lifeArea,
            eventType: eventType,
            evidenceLevel,
            confidence,
          },
          enriched_keywords: enrichedKeywords,
          keywords,
          laws_applied: [
            {
              applies: true,
              lawNumber: 11,
              lawName: 'Benefics to MC Promise Honors',
              strengthModifier: 0.8,
            },
          ],
          prediction_score: significance,
          significance,
          tone,
          prediction_tags: predictionTags,
        },
      ],
    },
  };
}

function makePredictorResponse({
  windowStart,
  windowEnd,
  observerLocation,
  timezone,
  peaks = [],
  predictions = [],
  predictionGroups = [],
  stepMinutes = 60,
}) {
  return {
    data: {
      window: {
        start: windowStart,
        end: windowEnd,
      },
      step_minutes: stepMinutes,
      observer: {
        location: observerLocation,
        timezone,
      },
      peaks: peaks.map((peak) => (typeof peak === 'string' ? { timestamp: peak } : peak)),
      predictions,
      prediction_groups: predictionGroups,
    },
  };
}

function makeFakeEventSource() {
  return {
    onmessage: null,
    onerror: null,
    close: vi.fn(),
    emit(payload) {
      this.onmessage?.({ data: JSON.stringify(payload) });
    },
    fail() {
      this.onerror?.(new Event('error'));
    },
  };
}

function fillManualInputs(container, { natalDate, natalTime, natalLocation, natalTimezone, transitDate, transitTime }) {
  const dateInputs = container.querySelectorAll('input[type="date"]');
  const timeInputs = container.querySelectorAll('input[type="time"]');
  const locationInput = container.querySelector('input[placeholder="City, Country"]');
  const timezoneInput = container.querySelector('input[placeholder="e.g., Europe/London"]');

  fireEvent.change(dateInputs[0], { target: { value: natalDate } });
  fireEvent.change(timeInputs[0], { target: { value: natalTime } });
  fireEvent.change(locationInput, { target: { value: natalLocation } });
  fireEvent.change(timezoneInput, { target: { value: natalTimezone } });
  fireEvent.change(dateInputs[1], { target: { value: transitDate } });
  fireEvent.change(timeInputs[1], { target: { value: transitTime } });
}

async function runReplayCase({
  windowResponse,
  singleResponse,
  inputs,
  peakLabel,
  scanAssertions = [],
  resultAssertions = [],
}) {
  astroClockApiMock.getTransitsWindow.mockResolvedValue(windowResponse);
  astroClockApiMock.getTransits.mockResolvedValue(singleResponse);

  const { container } = render(
    <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
  );

  fillManualInputs(container, inputs);
  fireEvent.click(screen.getByRole('button', { name: 'Scan Window' }));

  expect(await screen.findByText(/Top peaks:/i)).toBeInTheDocument();
  for (const assertion of scanAssertions) {
    if (assertion.multiple) {
      expect((await screen.findAllByText(assertion.pattern)).length).toBeGreaterThan(0);
    } else {
      expect(await screen.findByText(assertion.pattern)).toBeInTheDocument();
    }
  }

  const peakButtons = await screen.findAllByRole('button', { name: peakLabel });
  fireEvent.click(peakButtons[0]);

  await waitFor(() => {
    expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
  });

  for (const assertion of resultAssertions) {
    if (assertion.multiple) {
      expect((await screen.findAllByText(assertion.pattern)).length).toBeGreaterThan(0);
    } else {
      expect(await screen.findByText(assertion.pattern)).toBeInTheDocument();
    }
  }
}

async function runPredictorReplayCase({
  predictorResponse,
  inputs,
  predictorAssertions = [],
}) {
  astroClockApiMock.getPredictions.mockResolvedValue(predictorResponse);

  const { container } = render(
    <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
  );

  fillManualInputs(container, inputs);
  fireEvent.click(screen.getByRole('button', { name: 'Run Predictor' }));

  await waitFor(() => {
    expect(astroClockApiMock.getPredictions).toHaveBeenCalledTimes(1);
  });

  expect(await screen.findByText(/Predictor Results/i)).toBeInTheDocument();
  expect(await screen.findByText(/Peak Timestamps/i)).toBeInTheDocument();
  for (const assertion of predictorAssertions) {
    if (assertion.multiple) {
      expect((await screen.findAllByText(assertion.pattern)).length).toBeGreaterThan(0);
    } else {
      expect(await screen.findByText(assertion.pattern)).toBeInTheDocument();
    }
  }
}

async function runDirectComputeCase({
  singleResponse,
  inputs,
  resultAssertions = [],
}) {
  astroClockApiMock.getTransits.mockResolvedValue(singleResponse);

  const { container } = render(
    <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
  );

  fillManualInputs(container, inputs);
  fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

  await waitFor(() => {
    expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
  });
  expect(astroClockApiMock.getTransitsWindow).not.toHaveBeenCalled();

  for (const assertion of resultAssertions) {
    if (assertion.multiple) {
      expect((await screen.findAllByText(assertion.pattern)).length).toBeGreaterThan(0);
    } else {
      expect(await screen.findByText(assertion.pattern)).toBeInTheDocument();
    }
  }
}

async function runStreamReplayCase({
  eventSource,
  streamDonePayload,
  singleResponse,
  inputs,
  peakLabel,
  scanAssertions = [],
  resultAssertions = [],
}) {
  astroClockApiMock.createTransitsWindowStream.mockResolvedValue(eventSource);
  astroClockApiMock.getTransits.mockResolvedValue(singleResponse);

  const { container } = render(
    <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
  );

  fillManualInputs(container, inputs);
  fireEvent.click(screen.getByRole('button', { name: 'Scan Window' }));

  await waitFor(() => {
    expect(astroClockApiMock.createTransitsWindowStream).toHaveBeenCalledTimes(1);
  });

  await act(async () => {
    eventSource.emit({
      type: 'progress',
      progress: 0.5,
      row: (streamDonePayload.series || [])[0],
    });
    eventSource.emit({
      type: 'done',
      ...streamDonePayload,
    });
  });

  expect(await screen.findByText(/Top peaks:/i)).toBeInTheDocument();
  expect(astroClockApiMock.getTransitsWindow).not.toHaveBeenCalled();
  for (const assertion of scanAssertions) {
    if (assertion.multiple) {
      expect((await screen.findAllByText(assertion.pattern)).length).toBeGreaterThan(0);
    } else {
      expect(await screen.findByText(assertion.pattern)).toBeInTheDocument();
    }
  }

  const peakButtons = await screen.findAllByRole('button', { name: peakLabel });
  const peakButton = peakButtons.find((el) => el.tagName === 'BUTTON') || peakButtons[0];
  fireEvent.click(peakButton);
  await waitFor(() => {
    expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
  });
  for (const assertion of resultAssertions) {
    if (assertion.multiple) {
      expect((await screen.findAllByText(assertion.pattern)).length).toBeGreaterThan(0);
    } else {
      expect(await screen.findByText(assertion.pattern)).toBeInTheDocument();
    }
  }
}

describe('TransitsModal replay rendering', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    astroClockApiMock.listSnaps.mockResolvedValue({ items: [] });
    astroClockApiMock.createTransitsWindowStream.mockResolvedValue(null);
    astroClockApiMock.getTransitsWindow.mockReset();
    astroClockApiMock.getTransits.mockReset();
    astroClockApiMock.getPredictions.mockReset();
    astroClockApiMock.getAutoContext.mockReset();
  });

  it('rejects nonexistent daylight-saving wall times and resolves overlaps deterministically', () => {
    expect(buildTransitIso('2026-03-08', '02:30', 'America/New_York')).toBeNull();
    expect(buildTransitIso('2026-03-08', '01:30', 'America/New_York')).toBe('2026-03-08T06:30:00.000Z');
    expect(buildTransitIso('2026-03-08', '03:30', 'America/New_York')).toBe('2026-03-08T07:30:00.000Z');
    expect(buildTransitIso('2026-11-01', '01:30', 'America/New_York')).toBe('2026-11-01T05:30:00.000Z');
    expect(buildTransitIso('2026-03-27', '02:30', 'Asia/Jerusalem')).toBeNull();
    expect(buildTransitIso('2026-03-08', '12:00', 'Not/A_Timezone')).toBeNull();
  });

  it('closes an active scan stream when the modal closes', async () => {
    const eventSource = makeFakeEventSource();
    const onClose = vi.fn();
    astroClockApiMock.createTransitsWindowStream.mockResolvedValue(eventSource);

    const { container } = render(
      <TransitsModal open={true} onClose={onClose} defaultHouseSystem="W" />
    );
    fillManualInputs(container, {
      natalDate: '1990-01-01',
      natalTime: '12:00',
      natalLocation: 'New York, USA',
      natalTimezone: 'America/New_York',
      transitDate: '2026-03-08',
      transitTime: '03:30',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Scan Window' }));
    await waitFor(() => {
      expect(astroClockApiMock.createTransitsWindowStream).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    expect(eventSource.close).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('leaves scan controls usable when stream creation fails', async () => {
    astroClockApiMock.createTransitsWindowStream.mockRejectedValue(new Error('stream unavailable'));

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );
    fillManualInputs(container, {
      natalDate: '1990-01-01',
      natalTime: '12:00',
      natalLocation: 'New York, USA',
      natalTimezone: 'America/New_York',
      transitDate: '2026-03-08',
      transitTime: '03:30',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Scan Window' }));

    expect(await screen.findByText('stream unavailable')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Scan Window' })).toBeEnabled();
  });

  it('explains daylight-saving gaps instead of shifting the requested transit time', async () => {
    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );
    fillManualInputs(container, {
      natalDate: '1990-01-01',
      natalTime: '12:00',
      natalLocation: 'New York, USA',
      natalTimezone: 'America/New_York',
      transitDate: '2026-03-08',
      transitTime: '02:30',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    expect(await screen.findByText(/not valid in the selected timezone/i)).toBeInTheDocument();
    expect(astroClockApiMock.getTransits).not.toHaveBeenCalled();
  });

  it('uses the edited manual timezone instead of a previous result timezone', async () => {
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'London, UK',
        timezone: 'Europe/London',
        transitTimestamp: '2026-03-08T03:30:00.000Z',
        transiting: 'Saturn',
        targetLabel: 'Sun',
        aspect: 'Trine',
        lifeArea: 'identity',
        eventType: 'activation',
        description: 'Prior result used the London chart timezone.',
        significance: 55,
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );
    fillManualInputs(container, {
      natalDate: '1990-01-01',
      natalTime: '12:00',
      natalLocation: 'London, UK',
      natalTimezone: 'Europe/London',
      transitDate: '2026-03-08',
      transitTime: '03:30',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));
    await waitFor(() => {
      expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
    });

    const dateInputs = container.querySelectorAll('input[type="date"]');
    const timeInputs = container.querySelectorAll('input[type="time"]');
    fireEvent.change(
      container.querySelector('input[placeholder="e.g., Europe/London"]'),
      { target: { value: 'America/New_York' } },
    );
    fireEvent.change(dateInputs[1], { target: { value: '2026-03-08' } });
    fireEvent.change(timeInputs[1], { target: { value: '02:30' } });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    expect(await screen.findByText(/not valid in the selected timezone/i)).toBeInTheDocument();
    expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
  });

  it('renders scan window inputs with dedicated labels and wider date fields', async () => {
    render(<TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />);
    await waitFor(() => {
      expect(astroClockApiMock.listSnaps).toHaveBeenCalled();
    });

    const startDate = screen.getByLabelText('Scan start date');
    const endDate = screen.getByLabelText('Scan end date');
    const startTime = screen.getByLabelText('Scan start time');
    const endTime = screen.getByLabelText('Scan end time');

    expect(startDate.className).toContain('min-w-[11rem]');
    expect(endDate.className).toContain('min-w-[11rem]');
    expect(startTime.className).toContain('min-w-[7.5rem]');
    expect(endTime.className).toContain('min-w-[7.5rem]');
    expect(screen.getByRole('button', { name: 'Compute Exact Time' })).toBeInTheDocument();
    expect(screen.getByText(/compute the exact time entered above or click a peak below/i)).toBeInTheDocument();
  });

  it('distinguishes Morin 3D orb from longitude exactness in exact results', async () => {
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'Tehran, Iran',
        timezone: 'Asia/Tehran',
        transitTimestamp: '2026-11-18T10:10:00+03:30',
        transiting: 'Mars',
        targetLabel: 'Mars',
        aspect: 'Conjunction',
        lifeArea: 'action',
        eventType: 'activation',
        description: 'Longitude is exact while the latitude-aware contact remains wider.',
        significance: 70,
        orb: 0.7278,
        longitudeOrb: 0.0003,
        orbBasis: 'great_circle_3d',
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );
    fillManualInputs(container, {
      natalDate: '1990-01-01',
      natalTime: '12:00',
      natalLocation: 'Tehran, Iran',
      natalTimezone: 'Asia/Tehran',
      transitDate: '2026-11-18',
      transitTime: '10:10',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    expect(await screen.findByText(/Morin 3D orb includes celestial latitude/i)).toBeInTheDocument();
    expect(screen.getByText(/3D 0\.73/)).toBeInTheDocument();
    expect(screen.getByText(/Lon 0\.00/)).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Orbs' })).toHaveAttribute(
      'title',
      expect.stringMatching(/great-circle distance/i),
    );
  });

  it('labels a low-concordance event token as a theme rather than a prediction', async () => {
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'London, UK',
        timezone: 'Europe/London',
        transitTimestamp: '2026-05-10T12:00:00Z',
        transiting: 'Mars',
        targetLabel: 'C7',
        aspect: 'Square',
        lifeArea: 'relationships',
        eventType: 'relationship_conflict',
        description: 'This is a thematic correspondence, not a standalone event prediction.',
        enrichedKeywords: ['relationship_conflict'],
        keywords: ['Relationship'],
        predictionTags: ['relationships', 'negative'],
        significance: 18,
        tone: 'negative',
        evidenceLevel: 'theme_only',
        confidence: 0.18,
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );
    fillManualInputs(container, {
      natalDate: '1990-01-01',
      natalTime: '12:00',
      natalLocation: 'London, UK',
      natalTimezone: 'Europe/London',
      transitDate: '2026-05-10',
      transitTime: '12:00',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    const badge = await screen.findByText('Theme only');
    expect(screen.getByText('Event / theme')).toBeInTheDocument();
    expect(screen.getByText('partnership/open dispute')).toBeInTheDocument();
    expect(badge).toHaveAttribute('title', expect.stringMatching(/18% rule support.*not a statistical probability/i));
  });

  it('seeds natal inputs from the active chart context when the modal opens', async () => {
    astroClockApiMock.listSnaps.mockResolvedValue({
      items: [
        { id: 'snap-israel', label: 'Snap 1948-05-14 14:00:00+00:00 - israel' },
      ],
    });

    const { container } = render(
      <TransitsModal
        open={true}
        onClose={() => {}}
        defaultHouseSystem="W"
        initialNatalContext={{
          snapId: 'snap-israel',
          date: '1948-05-14',
          time: '16:00',
          location: 'israel',
          timezone: 'Asia/Jerusalem',
          houseSystem: 'W',
        }}
      />
    );

    await waitFor(() => {
      expect(astroClockApiMock.listSnaps).toHaveBeenCalled();
    });

    expect(screen.getByLabelText('Saved Snap')).toBeChecked();
    expect(container.querySelector('select')?.value).toBe('snap-israel');

    fireEvent.click(screen.getByLabelText('Manual Natal'));

    expect(screen.getByDisplayValue('1948-05-14')).toBeInTheDocument();
    expect(screen.getByDisplayValue('16:00')).toBeInTheDocument();
    expect(screen.getByDisplayValue('israel')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Asia/Jerusalem')).toBeInTheDocument();
  });

  it('keeps seeded natal coordinates in manual transit requests', async () => {
    astroClockApiMock.listSnaps.mockResolvedValue({ items: [] });
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'Israel',
        timezone: 'Asia/Jerusalem',
        transitTimestamp: '2026-03-22T06:32:00+02:00',
        transiting: 'Sun',
        targetLabel: 'MC',
        aspect: 'Trine',
        lifeArea: 'honors',
        eventType: 'public_recognition',
        description: 'Sun Trine MC supports honors.',
        enrichedKeywords: [],
        keywords: [],
        predictionTags: [],
        significance: 60,
      })
    );

    const { container } = render(
      <TransitsModal
        open={true}
        onClose={() => {}}
        defaultHouseSystem="W"
        initialNatalContext={{
          date: '1948-05-14',
          time: '16:00',
          location: 'Israel',
          timezone: 'Asia/Jerusalem',
          latitude: 31.778,
          longitude: 35.235,
          houseSystem: 'W',
        }}
      />
    );

    await waitFor(() => {
      expect(astroClockApiMock.listSnaps).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByLabelText('Manual Natal'));
    const dateInputs = container.querySelectorAll('input[type="date"]');
    const timeInputs = container.querySelectorAll('input[type="time"]');
    fireEvent.change(dateInputs[1], { target: { value: '2026-03-22' } });
    fireEvent.change(timeInputs[1], { target: { value: '06:32' } });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    await waitFor(() => {
      expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
    });
    expect(astroClockApiMock.getTransits.mock.calls[0][0]).toMatchObject({
      natalDatetime: expect.stringContaining('1948-05-14'),
      natalLocation: 'Israel',
      natalTimezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'W',
    });
  });

  it('auto-selects a matching saved snap when the context matches but snapId is missing', async () => {
    astroClockApiMock.listSnaps.mockResolvedValue({
      items: [
        {
          id: 'snap-israel',
          label: 'Snap 1948-05-14 14:00:00+00:00 - israel',
          effective_datetime: '1948-05-14T14:00:00Z',
          location: 'israel',
        },
      ],
    });

    const { container } = render(
      <TransitsModal
        open={true}
        onClose={() => {}}
        defaultHouseSystem="W"
        initialNatalContext={{
          date: '1948-05-14',
          time: '16:00',
          location: 'israel',
          timezone: 'Asia/Jerusalem',
          houseSystem: 'W',
        }}
      />
    );

    await waitFor(() => {
      expect(astroClockApiMock.listSnaps).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByLabelText('Saved Snap')).toBeChecked();
      expect(container.querySelector('select')?.value).toBe('snap-israel');
    });
  });

  it('renders timeline bars from backend step score and exposes them as accessible controls', async () => {
    astroClockApiMock.getTransitsWindow.mockResolvedValue(
      makeWindowResponse({
        timezone: 'Asia/Jerusalem',
        timestamp: '2026-02-28T22:28:00+02:00',
        eventType: 'attack_violence',
        lifeArea: 'conflict',
        description: 'Moon Quincunx C7 (contra-antiscia)',
        predictionTags: ['attack_violence', 'conflict', 'negative'],
        significance: 20,
        stepScore: 120,
        tone: 'negative',
      })
    );
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        transitTimestamp: '2026-02-28T22:28:00+02:00',
        transiting: 'Moon',
        targetLabel: 'C7',
        aspect: 'Quincunx',
        lifeArea: 'conflict',
        eventType: 'attack_violence',
        description: 'Moon Quincunx C7 (contra-antiscia)',
        enrichedKeywords: ['attack_violence', 'conflict'],
        keywords: ['conflict'],
        predictionTags: ['attack_violence', 'conflict', 'negative'],
        significance: 20,
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Scan Window' }));

    expect(await screen.findByText(/Bars use the backend step score/i)).toBeInTheDocument();
    expect(await screen.findByLabelText(/Timeline point .*score 120\.0.*peak.*critical/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Context emphasis/i)).toBeInTheDocument();
  });

  it('keeps scan critical signals when the event is in row predictions instead of top hits', async () => {
    const selectedIso = '2026-05-03T21:00:00Z';
    astroClockApiMock.getTransitsWindow.mockResolvedValue(
      makeWindowResponse({
        timezone: 'Asia/Jerusalem',
        timestamp: selectedIso,
        eventType: 'promotion',
        lifeArea: 'honors',
        description: 'Jupiter Semi-sextile MC',
        predictionTags: ['honor', 'positive'],
        significance: 60,
        stepScore: 624.7,
        tone: 'negative',
        topHits: [
          {
            transiting: 'Jupiter',
            aspect: 'Semi-sextile',
            target_label: 'MC',
            orb: 0.24,
            tone: 'positive',
            significance: 60,
            prediction_score: 60,
            prediction_tags: ['honor', 'positive'],
            prediction: {
              description: 'Jupiter Semi-sextile MC',
              lifeArea: 'honors',
              eventType: 'promotion',
            },
            enriched_keywords: ['career', 'promotion'],
            keywords: ['Career', 'Promotion'],
          },
        ],
        rowPredictions: [
          {
            date: selectedIso,
            description: 'Saturn Opposition C7 (antiscia) indicates a violent attack, assault, or conflict in conflict.',
            event_type: 'attack_violence',
            life_area: 'conflict',
            score: 20.2,
            probability: 1.0,
            tags: ['conflict', 'multiple_transit', 'negative'],
          },
        ],
      })
    );
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'Israel',
        timezone: 'Asia/Jerusalem',
        transitTimestamp: selectedIso,
        transiting: 'Saturn',
        targetLabel: 'C7',
        aspect: 'Opposition (antiscia)',
        lifeArea: 'conflict',
        eventType: 'attack_violence',
        description: 'Saturn Opposition C7 (antiscia) indicates a violent attack, assault, or conflict in conflict.',
        enrichedKeywords: ['attack_violence', 'conflict'],
        keywords: ['Attack/violence', 'Conflict'],
        predictionTags: ['conflict', 'multiple_transit', 'negative'],
        significance: 20.2,
        tone: 'negative',
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '2003-02-10',
      natalTime: '08:45',
      natalLocation: 'Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-05-04',
      transitTime: '00:00',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Scan Window' }));

    const criticalBar = await screen.findByLabelText(/Timeline point .*critical/i);
    expect(criticalBar).toBeInTheDocument();
    const scanHeader = await screen.findByText(/Critical Signals In Scan/i);
    const scanSection = scanHeader.parentElement;
    expect(scanSection).toBeTruthy();
    expect(within(scanSection).getByText(/attack\/violence/i)).toBeInTheDocument();
    expect(within(scanSection).queryByText(/No critical signals found/i)).not.toBeInTheDocument();

    fireEvent.click(criticalBar);

    await waitFor(() => {
      expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
    });
    const criticalHeader = await screen.findByText(/^Critical Signals$/i);
    const criticalSection = criticalHeader.parentElement;
    expect(criticalSection).toBeTruthy();
    expect(within(criticalSection).getByText(/attack\/violence/i)).toBeInTheDocument();
    expect(within(criticalSection).getByText(/Top critical transit: Saturn Opposition C7/i)).toBeInTheDocument();
  });

  it('keeps timeline-selected transit fields in the chart timezone for replay', async () => {
    const selectedIso = '2026-03-10T04:30:00Z';
    astroClockApiMock.getTransitsWindow.mockResolvedValue(
      makeWindowResponse({
        timezone: 'America/New_York',
        timestamp: selectedIso,
        eventType: 'authority_earned',
        lifeArea: 'honors',
        description: 'Saturn Trine MC',
        predictionTags: ['authority_earned', 'structure_established'],
        significance: 55,
        stepScore: 55,
        tone: 'positive',
      })
    );
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'New York, USA',
        timezone: 'America/New_York',
        transitTimestamp: selectedIso,
        transiting: 'Saturn',
        targetLabel: 'MC',
        aspect: 'Trine',
        lifeArea: 'honors',
        eventType: 'authority_earned',
        description: 'Saturn Trine MC',
        enrichedKeywords: ['authority_earned'],
        keywords: ['authority_earned'],
        predictionTags: ['authority_earned', 'structure_established'],
        significance: 55,
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1990-01-01',
      natalTime: '12:00',
      natalLocation: 'New York, USA',
      natalTimezone: 'America/New_York',
      transitDate: '2026-03-09',
      transitTime: '23:00',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Scan Window' }));

    expect(await screen.findByText(/Top peaks:/i)).toBeInTheDocument();
    const peakButtons = await screen.findAllByRole('button', { name: '2026-03-10 00:30' });
    const dateInputs = container.querySelectorAll('input[type="date"]');
    const timeInputs = container.querySelectorAll('input[type="time"]');

    const spies = [
      vi.spyOn(Date.prototype, 'getFullYear').mockReturnValue(1999),
      vi.spyOn(Date.prototype, 'getMonth').mockReturnValue(0),
      vi.spyOn(Date.prototype, 'getDate').mockReturnValue(2),
      vi.spyOn(Date.prototype, 'getHours').mockReturnValue(3),
      vi.spyOn(Date.prototype, 'getMinutes').mockReturnValue(4),
    ];
    try {
      fireEvent.click(peakButtons[0]);
    } finally {
      spies.forEach((spy) => spy.mockRestore());
    }

    await waitFor(() => {
      expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
      expect(dateInputs[1].value).toBe('2026-03-10');
      expect(timeInputs[1].value).toBe('00:30');
    });

    astroClockApiMock.getTransits.mockClear();
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    await waitFor(() => {
      expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
    });
    const replayIso = astroClockApiMock.getTransits.mock.calls[0][0].transitDatetime;
    expect(new Date(replayIso).getTime()).toBe(new Date(selectedIso).getTime());
  });

  it('keeps suggested context windows in the chart timezone', async () => {
    astroClockApiMock.getAutoContext.mockResolvedValue({
      data: {
        pd_selected: {
          start: '2026-03-10T04:30:00Z',
          end: '2026-03-10T05:30:00Z',
          label: 'PD window',
        },
      },
    });

    const getHoursSpy = vi.spyOn(Date.prototype, 'getHours').mockReturnValue(13);
    const getMinutesSpy = vi.spyOn(Date.prototype, 'getMinutes').mockReturnValue(45);
    try {
      const { container } = render(
        <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
      );

      fillManualInputs(container, {
        natalDate: '1990-01-01',
        natalTime: '12:00',
        natalLocation: 'New York, USA',
        natalTimezone: 'America/New_York',
        transitDate: '2026-03-10',
        transitTime: '00:00',
      });

      fireEvent.click(screen.getByRole('button', { name: 'Suggest Context Windows' }));

      await waitFor(() => {
        expect(astroClockApiMock.getAutoContext).toHaveBeenCalledTimes(1);
      });

      expect(document.getElementById('pd-start-date').value).toBe('2026-03-10');
      expect(document.getElementById('pd-start-time').value).toBe('00:30');
      expect(document.getElementById('pd-end-date').value).toBe('2026-03-10');
      expect(document.getElementById('pd-end-time').value).toBe('01:30');
    } finally {
      getHoursSpy.mockRestore();
      getMinutesSpy.mockRestore();
    }
  });

  it('sends manually entered context windows as chart-timezone instants', async () => {
    astroClockApiMock.getTransitsWindow.mockResolvedValue({
      data: {
        natal: { timezone: 'America/New_York' },
        series: [],
        peaks: [],
        prediction_card: null,
        context_window: null,
      },
    });

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1990-01-01',
      natalTime: '12:00',
      natalLocation: 'New York, USA',
      natalTimezone: 'America/New_York',
      transitDate: '2026-03-10',
      transitTime: '00:00',
    });

    fireEvent.click(screen.getByLabelText(/Use context windows/i));
    fireEvent.change(document.getElementById('pd-start-date'), { target: { value: '2026-03-10' } });
    fireEvent.change(document.getElementById('pd-start-time'), { target: { value: '00:30' } });
    fireEvent.change(document.getElementById('pd-end-date'), { target: { value: '2026-03-10' } });
    fireEvent.change(document.getElementById('pd-end-time'), { target: { value: '01:30' } });

    fireEvent.click(screen.getByRole('button', { name: 'Scan Window' }));

    await waitFor(() => {
      expect(astroClockApiMock.getTransitsWindow).toHaveBeenCalledTimes(1);
    });
    const request = astroClockApiMock.getTransitsWindow.mock.calls[0][0];
    expect(request.pdStart).toBe('2026-03-10T04:30:00.000Z');
    expect(request.pdEnd).toBe('2026-03-10T05:30:00.000Z');
  });

  it('uses replay-safe option defaults for exact-time transit requests', async () => {
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        transitTimestamp: '2026-02-28T20:28:00Z',
        transiting: 'Moon',
        targetLabel: 'C7',
        aspect: 'Quincunx (contra-antiscia)',
        lifeArea: 'conflict',
        eventType: 'attack_violence',
        description: 'Moon Quincunx C7 (contra-antiscia)',
        enrichedKeywords: ['attack_violence', 'conflict'],
        keywords: ['Attack/violence', 'Conflict'],
        predictionTags: ['conflict', 'multiple_transit', 'mixed_outcome'],
        significance: 30,
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    await waitFor(() => {
      expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
    });

    expect(astroClockApiMock.getTransits).toHaveBeenCalledWith(
      expect.objectContaining({
        includeModern: true,
        includeNatalModern: true,
        includeCusps: true,
        includeAntiscia: true,
        includeLots: true,
        sensitiveHouses: [],
        sensitivePlanets: [],
      })
    );
  });

  it('classifies adverse transit tags separately from polarity and status tags', async () => {
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        transitTimestamp: '2026-04-22T02:00:00Z',
        transiting: 'Saturn',
        targetLabel: 'C7',
        aspect: 'Quincunx (antiscia)',
        lifeArea: 'conflict',
        eventType: 'attack_violence',
        description: 'Saturn Quincunx C7 indicates violent conflict pressure.',
        enrichedKeywords: ['attack_violence', 'conflict', 'home'],
        keywords: ['Attack/violence', 'Conflict', 'Home'],
        predictionTags: ['home', 'conflict', 'multiple_transit', 'positive', 'mixed_outcome'],
        significance: 60,
        tone: 'positive',
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-04-22',
      transitTime: '05:00',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    expect(await screen.findByText(/^Critical Signals$/i)).toBeInTheDocument();
    expect(screen.getAllByText(/attack\/violence/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Positive$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Multiple Transit$/i)).not.toBeInTheDocument();

    const conflictChips = screen.getAllByText(/^conflict$/i);
    expect(conflictChips.some((node) => node.className.includes('border-rose'))).toBe(true);

    fireEvent.click(screen.getByLabelText(/Show technical tags/i));
    const multipleTransit = await screen.findByText(/^Multiple Transit$/i);
    expect(multipleTransit.className).toContain('border-zinc');
    expect(multipleTransit.className).not.toContain('emerald');
  });

  it('suppresses the stale empty-state when exact compute has prediction content', async () => {
    astroClockApiMock.getTransits.mockResolvedValue({
      data: {
        natal: {
          location: 'Tel Aviv, Israel',
          timezone: 'Asia/Jerusalem',
          house_system_code: 'W',
        },
        transit_timestamp: '2026-02-28T20:28:00Z',
        count: 1,
        moon_support: false,
        predictions: [
          {
            date: '2026-02-28T20:28:00Z',
            description: 'Jupiter Semi-sextile Saturn',
            event_type: 'promotion',
            life_area: 'honors',
            score: 100,
            probability: 1.0,
          },
        ],
        transits: [],
      },
    });

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    await waitFor(() => {
      expect(astroClockApiMock.getTransits).toHaveBeenCalledTimes(1);
    });

    expect(screen.queryByText(/No transits found for this timestamp\./i)).not.toBeInTheDocument();
    expect(await screen.findByText(/^Critical Signals$/i)).toBeInTheDocument();
    expect(await screen.findByText(/No critical signals at this timestamp\./i)).toBeInTheDocument();
    expect(await screen.findByText(/Hits 1/i)).toBeInTheDocument();
  });

  it('renders revolution cards as support summaries and prefers backend support signals', async () => {
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        transitTimestamp: '2026-02-28T20:28:00Z',
        transiting: 'Moon',
        targetLabel: 'C7',
        aspect: 'Quincunx (contra-antiscia)',
        lifeArea: 'conflict',
        eventType: 'attack_violence',
        description: 'Moon Quincunx C7 (contra-antiscia)',
        enrichedKeywords: ['attack_violence', 'conflict'],
        keywords: ['Conflict', 'C7'],
        predictionTags: ['mixed_outcome'],
        significance: 30,
        revolutions: {
          solar_score: 0.5,
          lunar_score: 0.3,
          solar: {
            timestamp: '2026-05-14T10:15:00Z',
            normalized_score: 0.5,
            domains: ['honors', 'belief'],
            signals: ['Year ruler angular', 'Mars trines natal degree'],
            tags: ['Sun returns to place'],
          },
          lunar: {
            timestamp: '2026-02-01T07:26:00Z',
            normalized_score: 0.3,
            domains: ['hidden', 'life'],
            signals: ['Lunar return falls in active direction window'],
            tags: ['Moon LR~Natal place'],
          },
        },
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    expect(await screen.findByText(/Solar Revolution/i)).toBeInTheDocument();
    expect(screen.getByText(/50% support/i)).toBeInTheDocument();
    expect(screen.getByText(/30% support/i)).toBeInTheDocument();
    expect(screen.getAllByText(/^Themes:/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/^Support:/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Year ruler angular/i)).toBeInTheDocument();
    expect(screen.getByText(/Lunar return falls in active direction window/i)).toBeInTheDocument();
    expect(screen.queryByText(/Sun returns to place/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Moon LR~Natal place/i)).not.toBeInTheDocument();
  });

  it('runs predictor at a finer step than a coarse scan setting', async () => {
    astroClockApiMock.getPredictions.mockResolvedValue(
      makePredictorResponse({
        windowStart: '2026-02-27T12:00:00+02:00',
        windowEnd: '2026-03-01T12:00:00+02:00',
        observerLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        peaks: [{
          timestamp: '2026-02-28T22:28:00+02:00',
          event_type: 'attack_violence',
          life_area: 'conflict',
          description: 'Moon Quincunx C7 (contra-antiscia)',
          support_score: 73.0,
          keyword_tokens: ['attack_violence', 'conflict'],
        }],
        predictionGroups: [
          {
            event_type: 'attack_violence',
            life_area: 'conflict',
            label: 'Moon Quincunx C7 (contra-antiscia)',
            description: 'Moon Quincunx C7 (contra-antiscia)',
            transit: 'Moon Quincunx C7 (contra-antiscia)',
            count: 2,
            start: '2026-02-28T21:28:00+02:00',
            end: '2026-02-28T22:28:00+02:00',
            dominant_timestamp: '2026-02-28T22:28:00+02:00',
            support_score: 134.2,
            support_density: 67.1,
            probability_max: 1.0,
            probability_mean: 0.8,
            score_max: 30,
            keyword_tokens: ['attack_violence', 'conflict'],
            tags: ['conflict'],
            occurrences: [
              { date: '2026-02-28T21:28:00+02:00', probability: 0.6, score: 18, support_score: 61.2 },
              { date: '2026-02-28T22:28:00+02:00', probability: 1.0, score: 30, support_score: 73.0 },
            ],
          },
        ],
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.change(screen.getByPlaceholderText('e.g., 60'), { target: { value: '1440' } });
    fireEvent.click(screen.getByRole('button', { name: 'Run Predictor' }));

    await waitFor(() => {
      expect(astroClockApiMock.getPredictions).toHaveBeenCalledTimes(1);
    });

    expect(astroClockApiMock.getPredictions.mock.calls[0][0].stepMinutes).toBe(60);
    expect(await screen.findByText(/Predictor refines coarse scans/i)).toBeInTheDocument();
    expect(await screen.findByText(/Predictor step: 60m/i)).toBeInTheDocument();
    expect(await screen.findByText(/Support Windows/i)).toBeInTheDocument();
    expect(await screen.findByText(/not statistical event probabilities/i)).toBeInTheDocument();
    expect(await screen.findByText(/Rule concordance 100%/i)).toBeInTheDocument();
    expect(await screen.findByText(/Avg concordance 80%/i)).toBeInTheDocument();
    expect(await screen.findByText(/rule 60%/i)).toBeInTheDocument();
    expect(await screen.findByText(/Support 134\.2/i)).toBeInTheDocument();
    expect(await screen.findByText(/Density 67\.1/i)).toBeInTheDocument();
    expect(await screen.findByText(/Strongest at/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/attack\/violence/i)).length).toBeGreaterThan(0);
  });

  it('orders fallback support windows by balanced focus instead of raw support total', async () => {
    astroClockApiMock.getPredictions.mockResolvedValue(
      makePredictorResponse({
        windowStart: '2026-03-08T00:00:00Z',
        windowEnd: '2026-03-08T23:00:00Z',
        observerLocation: 'London, UK',
        timezone: 'Europe/London',
        predictions: [
          {
            date: '2026-03-08T10:00:00Z',
            event_type: 'recognition',
            life_area: 'honors',
            label: 'Diffuse Recognition Transit',
            description: 'Diffuse Recognition Transit',
            score: 14,
            probability: 0.45,
            tags: ['public_recognition'],
          },
          {
            date: '2026-03-08T11:00:00Z',
            event_type: 'recognition',
            life_area: 'honors',
            label: 'Diffuse Recognition Transit',
            description: 'Diffuse Recognition Transit',
            score: 14,
            probability: 0.45,
            tags: ['public_recognition'],
          },
          {
            date: '2026-03-08T12:00:00Z',
            event_type: 'recognition',
            life_area: 'honors',
            label: 'Diffuse Recognition Transit',
            description: 'Diffuse Recognition Transit',
            score: 14,
            probability: 0.45,
            tags: ['public_recognition'],
          },
          {
            date: '2026-03-08T13:00:00Z',
            event_type: 'recognition',
            life_area: 'honors',
            label: 'Diffuse Recognition Transit',
            description: 'Diffuse Recognition Transit',
            score: 14,
            probability: 0.45,
            tags: ['public_recognition'],
          },
          {
            date: '2026-03-08T20:00:00Z',
            event_type: 'promotion',
            life_area: 'honors',
            label: 'Concentrated Promotion Transit',
            description: 'Concentrated Promotion Transit',
            score: 50,
            probability: 0.95,
            tags: ['honor_award'],
          },
          {
            date: '2026-03-08T21:00:00Z',
            event_type: 'promotion',
            life_area: 'honors',
            label: 'Concentrated Promotion Transit',
            description: 'Concentrated Promotion Transit',
            score: 50,
            probability: 0.95,
            tags: ['honor_award'],
          },
        ],
        predictionGroups: [],
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Run Predictor' }));

    const supportHeading = await screen.findByText(/Support Windows/i);
    const cardsContainer = supportHeading.nextElementSibling;
    expect(cardsContainer).not.toBeNull();
    const cards = cardsContainer ? Array.from(cardsContainer.children) : [];
    expect(cards).toHaveLength(2);
    expect(cards[0].textContent).toMatch(/Promotion/i);
    expect(cards[1].textContent).toMatch(/fame\/recognition/i);
  });

  it('shows supporting transits when equivalent predictor windows are merged', async () => {
    astroClockApiMock.getPredictions.mockResolvedValue(
      makePredictorResponse({
        windowStart: '2026-02-27T20:28:00.000Z',
        windowEnd: '2026-03-01T20:28:00.000Z',
        observerLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        predictionGroups: [
          {
            event_type: 'promotion',
            life_area: 'honors',
            label: 'Jupiter Semi-sextile Saturn',
            description: 'Jupiter Semi-sextile Saturn touches opportunity, growth, and protection.',
            transit: 'Jupiter Semi-sextile Saturn',
            count: 2,
            start: '2026-02-27T20:28:00.000Z',
            end: '2026-02-27T21:28:00.000Z',
            dominant_timestamp: '2026-02-27T20:28:00.000Z',
            support_score: 261.6,
            support_density: 130.8,
            support_focus: 184.979,
            probability_max: 1.0,
            probability_mean: 1.0,
            score_max: 100,
            keyword_tokens: ['promotion', 'honors', 'honor', 'multiple_transit'],
            tags: ['honor', 'multiple_transit'],
            supporting_transits: [
              'Jupiter Semi-sextile Saturn',
              'Jupiter Sextile Saturn (antiscia)',
              'Jupiter Trine Saturn (contra-antiscia)',
            ],
            occurrences: [
              { date: '2026-02-27T20:28:00.000Z', probability: 1.0, score: 100, support_score: 130.8 },
              { date: '2026-02-27T21:28:00.000Z', probability: 1.0, score: 100, support_score: 130.8 },
            ],
          },
        ],
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Run Predictor' }));

    expect(await screen.findByText(/Also supported by:/i)).toBeInTheDocument();
    expect(screen.getByText(/Jupiter Sextile Saturn \(antiscia\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Jupiter Trine Saturn \(contra-antiscia\)/i)).toBeInTheDocument();
  });

  it('widens predictor step for long windows to avoid timing out on dense scans', async () => {
    astroClockApiMock.getPredictions.mockResolvedValue(
      makePredictorResponse({
        windowStart: '2026-02-01T12:00:00+02:00',
        windowEnd: '2026-03-01T12:00:00+02:00',
        observerLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        predictions: [
          {
            label: 'Mars Quincunx Mercury',
            description: 'Mars Quincunx Mercury',
            event_type: 'attack_violence',
            life_area: 'conflict',
            score: 61.2,
            probability: 0.74,
            support_score: 122.4,
            keyword_tokens: ['attack_violence', 'conflict'],
          },
        ],
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.change(screen.getByLabelText('Scan start date'), { target: { value: '2026-02-01' } });
    fireEvent.change(screen.getByLabelText('Scan start time'), { target: { value: '12:00' } });
    fireEvent.change(screen.getByLabelText('Scan end date'), { target: { value: '2026-03-01' } });
    fireEvent.change(screen.getByLabelText('Scan end time'), { target: { value: '12:00' } });
    fireEvent.change(screen.getByPlaceholderText('e.g., 60'), { target: { value: '15' } });
    fireEvent.click(screen.getByRole('button', { name: 'Run Predictor' }));

    await waitFor(() => {
      expect(astroClockApiMock.getPredictions).toHaveBeenCalledTimes(1);
    });

    expect(astroClockApiMock.getPredictions.mock.calls[0][0].stepMinutes).toBe(180);
    expect(await screen.findByText(/keep long windows responsive/i)).toBeInTheDocument();
    expect(await screen.findByText(/Predictor step: 180m/i)).toBeInTheDocument();
  });

  it('renders slice-1 promotion signals from the scan and single-transit results', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'America/New_York',
        timestamp: '2017-01-20T17:00:00Z',
        eventType: 'promotion',
        lifeArea: 'honors',
        description: 'Jupiter Trine Sun',
        predictionTags: ['honor_award', 'public_recognition'],
        significance: 60,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Queens, New York',
        timezone: 'America/New_York',
        transitTimestamp: '2017-01-20T17:00:00Z',
        transiting: 'Jupiter',
        targetLabel: 'Sun',
        aspect: 'Trine',
        lifeArea: 'honors',
        eventType: 'promotion',
        description: 'Jupiter Trine Sun',
        enrichedKeywords: ['career', 'public_recognition', 'promotion', 'honor_award'],
        keywords: ['Career', 'Promotion', 'Public fame/distinction'],
        predictionTags: ['honor_award', 'public_recognition'],
        significance: 60,
      }),
      inputs: {
        natalDate: '1946-06-14',
        natalTime: '10:54',
        natalLocation: 'Queens, New York',
        natalTimezone: 'America/New_York',
        transitDate: '2017-01-20',
        transitTime: '12:00',
      },
      peakLabel: /2017-01-20 12:00/i,
      scanAssertions: [
        { pattern: /action\/profession\/dignity/i },
        { pattern: /promotion/i },
      ],
      resultAssertions: [
        { pattern: /honor\/distinction/i, multiple: true },
        { pattern: /career/i, multiple: true },
      ],
    });
    expect(screen.getByText(/Show technical tags/i)).toBeInTheDocument();
  });

  it('renders Kamala Harris promotion signals through the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'America/New_York',
        timestamp: '2021-01-20T17:00:00Z',
        eventType: 'promotion',
        lifeArea: 'honors',
        description: 'Sun Semi-sextile MC',
        predictionTags: ['authority_earned', 'structure_established'],
        significance: 52,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Oakland, California',
        timezone: 'America/New_York',
        transitTimestamp: '2021-01-20T17:00:00Z',
        transiting: 'Saturn',
        targetLabel: 'MC',
        aspect: 'Semi-sextile',
        lifeArea: 'honors',
        eventType: 'promotion',
        description: 'Saturn Semi-sextile MC',
        enrichedKeywords: ['career', 'structure_established', 'authority_earned', 'promotion'],
        keywords: ['Career', 'Structure established', 'Authority earned'],
        predictionTags: ['authority_earned', 'structure_established'],
        significance: 52,
      }),
      inputs: {
        natalDate: '1964-10-20',
        natalTime: '21:28',
        natalLocation: 'Oakland, California',
        natalTimezone: 'America/Los_Angeles',
        transitDate: '2021-01-20',
        transitTime: '12:00',
      },
      peakLabel: /2021-01-20 12:00/i,
      scanAssertions: [
        { pattern: /promotion/i },
      ],
      resultAssertions: [
        { pattern: /authority earned/i, multiple: true },
        { pattern: /structure established/i, multiple: true },
        { pattern: /career/i, multiple: true },
      ],
    });
  });

  it('renders Sergio Mattarella public-recognition signals through the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/Rome',
        timestamp: '2015-01-31T12:00:00Z',
        eventType: 'promotion',
        lifeArea: 'honors',
        description: 'Jupiter Sextile Mercury (antiscia)',
        predictionTags: ['public_recognition'],
        significance: 58,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Palermo, Italy',
        timezone: 'Europe/Rome',
        transitTimestamp: '2015-01-31T12:00:00Z',
        transiting: 'Saturn',
        targetLabel: 'Sun',
        aspect: 'Trine',
        lifeArea: 'honors',
        eventType: 'promotion',
        description: 'Saturn Trine Sun',
        enrichedKeywords: ['career', 'public_recognition', 'promotion'],
        keywords: ['Career', 'Public fame/distinction'],
        predictionTags: ['public_recognition'],
        significance: 58,
      }),
      inputs: {
        natalDate: '1941-07-23',
        natalTime: '11:40',
        natalLocation: 'Palermo, Italy',
        natalTimezone: 'Europe/Rome',
        transitDate: '2015-01-31',
        transitTime: '13:00',
      },
      peakLabel: /2015-01-31 13:00/i,
      scanAssertions: [
        { pattern: /promotion/i },
      ],
      resultAssertions: [
        { pattern: /public fame\/distinction/i, multiple: true },
        { pattern: /career/i, multiple: true },
      ],
    });
  });

  it('renders slice-2 public-honor signals from the scan and single-transit results', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/Oslo',
        timestamp: '2009-10-09T09:00:00Z',
        eventType: 'opportunity_received',
        lifeArea: 'honors',
        description: 'Jupiter Conjunction Asc',
        predictionTags: ['authority_earned', 'structure_established'],
        significance: 95.4,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Honolulu, Hawaii',
        timezone: 'Europe/Oslo',
        transitTimestamp: '2009-10-09T09:00:00Z',
        transiting: 'Saturn',
        targetLabel: 'MC',
        aspect: 'Sextile',
        lifeArea: 'honors',
        eventType: 'opportunity_received',
        description: 'Saturn Sextile MC',
        enrichedKeywords: ['career', 'authority_earned', 'structure_established', 'opportunity_received'],
        keywords: ['Career', 'Authority earned', 'Structure established'],
        predictionTags: ['authority_earned', 'structure_established'],
        significance: 88.0,
      }),
      inputs: {
        natalDate: '1961-08-04',
        natalTime: '19:24',
        natalLocation: 'Honolulu, Hawaii',
        natalTimezone: 'Pacific/Honolulu',
        transitDate: '2009-10-09',
        transitTime: '11:00',
      },
      peakLabel: /2009-10-09 11:00/i,
      scanAssertions: [
        { pattern: /opportunity received/i },
      ],
      resultAssertions: [
        { pattern: /authority earned/i, multiple: true },
        { pattern: /structure established/i, multiple: true },
        { pattern: /career/i, multiple: true },
      ],
    });
  });

  it('renders Al Gore public-honor signals through the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/Oslo',
        timestamp: '2007-10-12T09:00:00Z',
        eventType: 'opportunity_received',
        lifeArea: 'honors',
        description: 'Jupiter Trine Saturn',
        predictionTags: ['authority_earned', 'structure_established'],
        significance: 93,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Washington, District of Columbia',
        timezone: 'Europe/Oslo',
        transitTimestamp: '2007-10-12T09:00:00Z',
        transiting: 'Saturn',
        targetLabel: 'Venus',
        aspect: 'Semi-sextile',
        lifeArea: 'honors',
        eventType: 'opportunity_received',
        description: 'Saturn Semi-sextile Venus (antiscia)',
        enrichedKeywords: ['career', 'authority_earned', 'structure_established', 'opportunity_received'],
        keywords: ['Career', 'Authority earned', 'Structure established'],
        predictionTags: ['authority_earned', 'structure_established'],
        significance: 86,
      }),
      inputs: {
        natalDate: '1948-03-31',
        natalTime: '12:53',
        natalLocation: 'Washington, District of Columbia',
        natalTimezone: 'America/New_York',
        transitDate: '2007-10-12',
        transitTime: '11:00',
      },
      peakLabel: /2007-10-12 11:00/i,
      scanAssertions: [
        { pattern: /opportunity received/i },
      ],
      resultAssertions: [
        { pattern: /authority earned/i, multiple: true },
        { pattern: /structure established/i, multiple: true },
        { pattern: /career/i, multiple: true },
      ],
    });
  });

  it('renders slice-4 stream replay signals through the modal for Donald Trump', async () => {
    const eventSource = makeFakeEventSource();
    await runStreamReplayCase({
      eventSource,
      streamDonePayload: {
        natal: { timezone: 'America/New_York' },
        series: [
          {
            timestamp: '2017-01-20T17:00:00Z',
            count: 147,
            step_score: 260,
            tone: 'mixed',
            moon_support: false,
            top: [
              {
                transiting: 'Jupiter',
                aspect: 'Trine',
                target_label: 'Sun',
                orb: 0.24,
                tone: 'positive',
                significance: 60,
                prediction_score: 60,
                prediction_tags: ['public_recognition'],
                prediction: {
                  description: 'Jupiter Trine Sun',
                  lifeArea: 'honors',
                  eventType: 'promotion',
                },
              },
            ],
          },
        ],
        peaks: [{ timestamp: '2017-01-20T17:00:00Z' }],
        prediction_card: null,
        context_window: null,
      },
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Queens, New York',
        timezone: 'America/New_York',
        transitTimestamp: '2017-01-20T17:00:00Z',
        transiting: 'Jupiter',
        targetLabel: 'Sun',
        aspect: 'Trine',
        lifeArea: 'honors',
        eventType: 'promotion',
        description: 'Jupiter Trine Sun',
        enrichedKeywords: ['career', 'public_recognition', 'promotion'],
        keywords: ['Career', 'Public fame/distinction', 'Promotion'],
        predictionTags: ['public_recognition'],
        significance: 60,
      }),
      inputs: {
        natalDate: '1946-06-14',
        natalTime: '10:54',
        natalLocation: 'Queens, New York',
        natalTimezone: 'America/New_York',
        transitDate: '2017-01-20',
        transitTime: '12:00',
      },
      peakLabel: /2017-01-20 12:00/i,
      scanAssertions: [
        { pattern: /promotion/i },
      ],
      resultAssertions: [
        { pattern: /public fame\/distinction/i, multiple: true },
        { pattern: /career/i, multiple: true },
      ],
    });
  });

  it('renders slice-4 stream replay signals through the modal for Sergio Mattarella', async () => {
    const eventSource = makeFakeEventSource();
    await runStreamReplayCase({
      eventSource,
      streamDonePayload: {
        natal: { timezone: 'Europe/Rome' },
        series: [
          {
            timestamp: '2015-01-31T12:00:00Z',
            count: 149,
            step_score: 248.1,
            tone: 'mixed',
            moon_support: false,
            top: [
              {
                transiting: 'Jupiter',
                aspect: 'Sextile',
                target_label: 'Mercury',
                orb: 0.24,
                tone: 'positive',
                significance: 58,
                prediction_score: 58,
                prediction_tags: ['public_recognition'],
                prediction: {
                  description: 'Jupiter Sextile Mercury (antiscia)',
                  lifeArea: 'honors',
                  eventType: 'promotion',
                },
              },
            ],
          },
        ],
        peaks: [{ timestamp: '2015-01-31T12:00:00Z' }],
        prediction_card: null,
        context_window: null,
      },
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Palermo, Italy',
        timezone: 'Europe/Rome',
        transitTimestamp: '2015-01-31T12:00:00Z',
        transiting: 'Saturn',
        targetLabel: 'Sun',
        aspect: 'Trine',
        lifeArea: 'honors',
        eventType: 'promotion',
        description: 'Saturn Trine Sun',
        enrichedKeywords: ['career', 'public_recognition', 'promotion'],
        keywords: ['Career', 'Public fame/distinction'],
        predictionTags: ['public_recognition'],
        significance: 58,
      }),
      inputs: {
        natalDate: '1941-07-23',
        natalTime: '11:40',
        natalLocation: 'Palermo, Italy',
        natalTimezone: 'Europe/Rome',
        transitDate: '2015-01-31',
        transitTime: '13:00',
      },
      peakLabel: /2015-01-31 13:00/i,
      scanAssertions: [],
      resultAssertions: [
        { pattern: /public fame\/distinction/i, multiple: true },
        { pattern: /career/i, multiple: true },
      ],
    });
  });

  it('renders slice-4 stream replay signals through the modal for Al Gore', async () => {
    const eventSource = makeFakeEventSource();
    await runStreamReplayCase({
      eventSource,
      streamDonePayload: {
        natal: { timezone: 'Europe/Oslo' },
        series: [
          {
            timestamp: '2007-10-12T09:00:00Z',
            count: 136,
            step_score: 249.4,
            tone: 'mixed',
            moon_support: false,
            top: [
              {
                transiting: 'Jupiter',
                aspect: 'Trine',
                target_label: 'Saturn',
                orb: 0.24,
                tone: 'positive',
                significance: 50,
                prediction_score: 50,
                prediction_tags: ['authority_earned', 'structure_established'],
                prediction: {
                  description: 'Jupiter Trine Saturn',
                  lifeArea: 'honors',
                  eventType: 'opportunity_received',
                },
              },
            ],
          },
        ],
        peaks: [{ timestamp: '2007-10-12T14:00:00Z' }],
        prediction_card: null,
        context_window: null,
      },
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Washington, District of Columbia',
        timezone: 'Europe/Oslo',
        transitTimestamp: '2007-10-12T09:00:00Z',
        transiting: 'Saturn',
        targetLabel: 'Venus',
        aspect: 'Semi-sextile',
        lifeArea: 'honors',
        eventType: 'opportunity_received',
        description: 'Saturn Semi-sextile Venus (antiscia)',
        enrichedKeywords: ['career', 'authority_earned', 'structure_established', 'opportunity_received'],
        keywords: ['Career', 'Authority earned', 'Structure established'],
        predictionTags: ['authority_earned', 'structure_established'],
        significance: 86,
      }),
      inputs: {
        natalDate: '1948-03-31',
        natalTime: '12:53',
        natalLocation: 'Washington, District of Columbia',
        natalTimezone: 'America/New_York',
        transitDate: '2007-10-12',
        transitTime: '11:00',
      },
      peakLabel: /2007-10-12 16:00/i,
      scanAssertions: [],
      resultAssertions: [
        { pattern: /authority earned/i, multiple: true },
        { pattern: /structure established/i, multiple: true },
      ],
    });
  });

  it('renders slice-5 public-crisis support through the modal for George W. Bush', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'America/New_York',
        timestamp: '2003-03-20T03:16:00Z',
        eventType: 'structure_established',
        lifeArea: 'honors',
        description: 'Saturn Sextile MC',
        predictionTags: ['authority_earned'],
        significance: 100,
      }),
      singleResponse: {
        data: {
          natal: {
            location: 'New Haven, Connecticut',
            timezone: 'America/New_York',
            house_system_code: 'W',
          },
          transit_timestamp: '2003-03-20T03:16:00Z',
          count: 1,
          moon_support: false,
          predictions: [
            {
              date: '2003-03-20T03:16:00Z',
              description: 'Saturn Sextile MC',
              event_type: 'structure_established',
              life_area: 'honors',
              score: 100,
              probability: 1.0,
            },
          ],
          transits: [
            {
              transiting: 'Mars',
              target_label: 'Mercury',
              natal: 'Mercury',
              aspect: 'Quincunx',
              orb: 0.24,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2003-03-20T03:16:00Z',
                end: '2003-03-20T03:16:00Z',
              },
              prediction: {
                description: 'Saturn Sextile MC',
                lifeArea: 'honors',
                eventType: 'structure_established',
              },
              enriched_keywords: ['accident_major'],
              keywords: ['Accident major'],
              laws_applied: [
                {
                  applies: true,
                  lawNumber: 11,
                  lawName: 'Benefics to MC Promise Honors',
                  strengthModifier: 0.8,
                },
              ],
              prediction_score: 31.5,
              significance: 31.5,
              tone: 'mixed',
              prediction_tags: [],
            },
          ],
        },
      },
      inputs: {
        natalDate: '1946-07-06',
        natalTime: '07:26',
        natalLocation: 'New Haven, Connecticut',
        natalTimezone: 'America/New_York',
        transitDate: '2003-03-19',
        transitTime: '22:16',
      },
      peakLabel: /2003-03-19 22:16/i,
      scanAssertions: [],
      resultAssertions: [
        { pattern: /major accident/i, multiple: true },
      ],
    });
  });

  it('renders slice-9 war-response keywords through the modal for George W. Bush', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'America/New_York',
        timestamp: '2003-03-20T03:16:00Z',
        eventType: 'structure_established',
        lifeArea: 'honors',
        description: 'Saturn Sextile MC',
        predictionTags: ['authority_earned'],
        significance: 100,
        rowPredictions: [
          {
            date: '2003-03-20T03:16:00Z',
            description: 'Saturn Sextile MC',
            event_type: 'structure_established',
            life_area: 'honors',
            score: 100,
            probability: 1.0,
          },
          {
            date: '2003-03-20T03:16:00Z',
            description: 'Saturn Quincunx C7 (antiscia)',
            event_type: 'attack_violence',
            life_area: 'conflict',
            score: 30,
            probability: 1.0,
          },
        ],
      }),
      singleResponse: {
        data: {
          natal: {
            location: 'New Haven, Connecticut',
            timezone: 'America/New_York',
            house_system_code: 'W',
          },
          transit_timestamp: '2003-03-20T03:16:00Z',
          count: 1,
          moon_support: false,
          predictions: [
            {
              date: '2003-03-20T03:16:00Z',
              description: 'Saturn Sextile MC',
              event_type: 'structure_established',
              life_area: 'honors',
              score: 100,
              probability: 1.0,
            },
            {
              date: '2003-03-20T03:16:00Z',
              description: 'Saturn Quincunx C7 (antiscia)',
              event_type: 'attack_violence',
              life_area: 'conflict',
              score: 30,
              probability: 1.0,
            },
          ],
          transits: [
            {
              transiting: 'Saturn',
              target_label: 'C7',
              natal: 'C7',
              aspect: 'Quincunx (antiscia)',
              orb: 0.18,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2003-03-20T03:16:00Z',
                end: '2003-03-20T03:16:00Z',
              },
              prediction: {
                description: 'Saturn Quincunx C7 (antiscia)',
                lifeArea: 'conflict',
                eventType: 'attack_violence',
              },
              enriched_keywords: ['war_response_defensive', 'attack_violence', 'conflict'],
              keywords: ['Defensive war/open-enemy conflict', 'Attack/violence', 'Conflict'],
              laws_applied: [
                {
                  applies: true,
                  lawNumber: 11,
                  lawName: 'Benefics to MC Promise Honors',
                  strengthModifier: 0.8,
                },
              ],
              prediction_score: 30.0,
              significance: 30.0,
              tone: 'mixed',
              prediction_tags: ['conflict', 'multiple_transit', 'mixed_outcome'],
            },
          ],
        },
      },
      inputs: {
        natalDate: '1946-07-06',
        natalTime: '07:26',
        natalLocation: 'New Haven, Connecticut',
        natalTimezone: 'America/New_York',
        transitDate: '2003-03-19',
        transitTime: '22:16',
      },
      peakLabel: /2003-03-19 22:16/i,
      scanAssertions: [
        { pattern: /attack\/violence/i, multiple: true },
        { pattern: /conflict/i, multiple: true },
      ],
      resultAssertions: [
        { pattern: /defensive war\/open-enemy conflict/i, multiple: true },
        { pattern: /attack\/violence/i, multiple: true },
        { pattern: /conflict/i, multiple: true },
      ],
    });
  });

  it('renders slice-10 recent war-response keywords through the modal for Israel', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Asia/Jerusalem',
        timestamp: '2026-02-28T20:28:00Z',
        eventType: 'promotion',
        lifeArea: 'honors',
        description: 'Jupiter Semi-sextile Saturn',
        predictionTags: ['honor_award', 'public_recognition'],
        significance: 100,
        rowPredictions: [
          {
            date: '2026-02-28T20:28:00Z',
            description: 'Jupiter Semi-sextile Saturn',
            event_type: 'promotion',
            life_area: 'honors',
            score: 100,
            probability: 1.0,
          },
          {
            date: '2026-02-28T20:28:00Z',
            description: 'Moon Quincunx C7 (contra-antiscia)',
            event_type: 'attack_violence',
            life_area: 'conflict',
            score: 30,
            probability: 1.0,
          },
        ],
      }),
      singleResponse: {
        data: {
          natal: {
            location: 'Tel Aviv, Israel',
            timezone: 'Asia/Jerusalem',
            house_system_code: 'R',
          },
          transit_timestamp: '2026-02-28T20:28:00Z',
          count: 2,
          moon_support: false,
          predictions: [
            {
              date: '2026-02-28T20:28:00Z',
              description: 'Jupiter Semi-sextile Saturn',
              event_type: 'promotion',
              life_area: 'honors',
              score: 100,
              probability: 1.0,
            },
            {
              date: '2026-02-28T20:28:00Z',
              description: 'Moon Quincunx C7 (contra-antiscia)',
              event_type: 'attack_violence',
              life_area: 'conflict',
              score: 30,
              probability: 1.0,
            },
          ],
          transits: [
            {
              transiting: 'Jupiter',
              target_label: 'Saturn',
              natal: 'Saturn',
              aspect: 'Semi-sextile',
              orb: 0.19,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2026-02-28T20:28:00Z',
                end: '2026-02-28T20:28:00Z',
              },
              prediction: {
                description: 'Jupiter Semi-sextile Saturn',
                lifeArea: 'honors',
                eventType: 'promotion',
              },
              enriched_keywords: ['career', 'promotion', 'public_recognition'],
              keywords: ['Career', 'Promotion', 'Public fame/distinction'],
              laws_applied: [
                {
                  applies: true,
                  lawNumber: 11,
                  lawName: 'Benefics to MC Promise Honors',
                  strengthModifier: 0.8,
                },
              ],
              prediction_score: 100,
              significance: 100,
              tone: 'positive',
              prediction_tags: ['honor_award', 'public_recognition'],
            },
            {
              transiting: 'Moon',
              target_label: 'C7',
              natal: 'C7',
              aspect: 'Quincunx (contra-antiscia)',
              orb: 0.24,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2026-02-28T20:28:00Z',
                end: '2026-02-28T20:28:00Z',
              },
              prediction: {
                description: 'Moon Quincunx C7 (contra-antiscia)',
                lifeArea: 'conflict',
                eventType: 'attack_violence',
              },
              enriched_keywords: ['attack_violence', 'conflict'],
              keywords: ['Attack/violence', 'Conflict'],
              laws_applied: [
                {
                  applies: true,
                  lawNumber: 11,
                  lawName: 'Benefics to MC Promise Honors',
                  strengthModifier: 0.8,
                },
              ],
              prediction_score: 30,
              significance: 30,
              tone: 'mixed',
              prediction_tags: ['conflict', 'multiple_transit', 'mixed_outcome'],
            },
          ],
        },
      },
      inputs: {
        natalDate: '1948-05-14',
        natalTime: '16:00',
        natalLocation: 'Tel Aviv, Israel',
        natalTimezone: 'Asia/Jerusalem',
        transitDate: '2026-02-28',
        transitTime: '22:28',
      },
      peakLabel: /2026-02-28 22:28/i,
      scanAssertions: [
        { pattern: /Critical Signals In Scan/i },
        { pattern: /attack\/violence/i, multiple: true },
        { pattern: /conflict/i, multiple: true },
      ],
      resultAssertions: [
        { pattern: /^Critical Signals$/i },
        { pattern: /attack\/violence/i, multiple: true },
        { pattern: /conflict/i, multiple: true },
        { pattern: /Top critical transit: Moon Quincunx C7 \(contra-antiscia\)/i },
        { pattern: /^Mixed$/i, multiple: true },
      ],
    });
  });

  it('keeps a critical-signals panel visible even when the exact timestamp has no crisis layer', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Asia/Jerusalem',
        timestamp: '2026-02-28T20:28:00Z',
        eventType: 'promotion',
        lifeArea: 'honors',
        description: 'Jupiter Semi-sextile Saturn',
        predictionTags: ['honor_award', 'public_recognition'],
        significance: 100,
        topHits: [
          {
            transiting: 'Jupiter',
            aspect: 'Semi-sextile',
            target_label: 'Saturn',
            orb: 0.19,
            tone: 'positive',
            significance: 100,
            prediction_score: 100,
            prediction_tags: ['honor_award', 'public_recognition'],
            prediction: {
              description: 'Jupiter Semi-sextile Saturn',
              lifeArea: 'honors',
              eventType: 'promotion',
            },
            enriched_keywords: ['career', 'promotion', 'public_recognition'],
            keywords: ['Career', 'Promotion', 'Public fame/distinction'],
          },
          {
            transiting: 'Moon',
            aspect: 'Quincunx (contra-antiscia)',
            target_label: 'C7',
            orb: 0.24,
            tone: 'mixed',
            significance: 30,
            prediction_score: 30,
            prediction_tags: ['conflict', 'multiple_transit', 'mixed_outcome'],
            prediction: {
              description: 'Moon Quincunx C7 (contra-antiscia)',
              lifeArea: 'conflict',
              eventType: 'attack_violence',
            },
            enriched_keywords: ['attack_violence', 'conflict'],
            keywords: ['Attack/violence', 'Conflict'],
          },
        ],
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        transitTimestamp: '2026-02-28T10:00:00Z',
        transiting: 'Jupiter',
        targetLabel: 'Saturn',
        aspect: 'Semi-sextile',
        lifeArea: 'honors',
        eventType: 'promotion',
        description: 'Jupiter Semi-sextile Saturn',
        enrichedKeywords: ['career', 'promotion', 'public_recognition'],
        keywords: ['Career', 'Promotion', 'Public fame/distinction'],
        predictionTags: ['honor_award', 'public_recognition'],
        significance: 100,
      }),
      inputs: {
        natalDate: '1948-05-14',
        natalTime: '16:00',
        natalLocation: 'Tel Aviv, Israel',
        natalTimezone: 'Asia/Jerusalem',
        transitDate: '2026-02-28',
        transitTime: '12:00',
      },
      peakLabel: /2026-02-28 22:28/i,
      scanAssertions: [
        { pattern: /Critical Signals In Scan/i },
      ],
      resultAssertions: [
        { pattern: /^Critical Signals$/i },
        { pattern: /No critical signals at this timestamp\./i },
        { pattern: /Check the scan summary above for nearby crisis rows\./i },
      ],
    });
  });

  it('shows only the primary eligible crisis token per hit in the exact-time summary', async () => {
    astroClockApiMock.getTransits.mockResolvedValue(
      makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        transitTimestamp: '2026-02-28T20:28:00Z',
        transiting: 'Moon',
        targetLabel: 'C7',
        aspect: 'Quincunx (contra-antiscia)',
        lifeArea: 'conflict',
        eventType: 'attack_violence',
        description: 'Moon Quincunx C7 (contra-antiscia)',
        enrichedKeywords: ['attack_violence', 'death_natural', 'fall_from_height', 'conflict'],
        keywords: ['Conflict', 'C7'],
        predictionTags: ['mixed_outcome'],
        significance: 30,
      })
    );

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    const criticalHeader = await screen.findByText(/^Critical Signals$/i);
    const criticalSection = criticalHeader.parentElement;
    expect(criticalSection).toBeTruthy();
    expect(within(criticalSection).getAllByText(/attack\/violence/i).length).toBeGreaterThan(0);
    expect(within(criticalSection).queryByText(/natural death/i)).not.toBeInTheDocument();
    expect(within(criticalSection).queryByText(/fall from height/i)).not.toBeInTheDocument();
  });

  it('computes the exact Israel war timestamp directly and surfaces the crisis layer', async () => {
    await runDirectComputeCase({
      singleResponse: {
        data: {
          natal: {
            location: 'Tel Aviv, Israel',
            timezone: 'Asia/Jerusalem',
            house_system_code: 'R',
          },
          transit_timestamp: '2026-02-28T20:28:00Z',
          count: 2,
          moon_support: false,
          predictions: [
            {
              date: '2026-02-28T20:28:00Z',
              description: 'Jupiter Semi-sextile Saturn',
              event_type: 'promotion',
              life_area: 'honors',
              score: 100,
              probability: 1.0,
            },
            {
              date: '2026-02-28T20:28:00Z',
              description: 'Moon Quincunx C7 (contra-antiscia)',
              event_type: 'attack_violence',
              life_area: 'conflict',
              score: 30,
              probability: 1.0,
            },
          ],
          transits: [
            {
              transiting: 'Jupiter',
              target_label: 'Saturn',
              natal: 'Saturn',
              aspect: 'Semi-sextile',
              orb: 0.19,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2026-02-28T20:28:00Z',
                end: '2026-02-28T20:28:00Z',
              },
              prediction: {
                description: 'Jupiter Semi-sextile Saturn',
                lifeArea: 'honors',
                eventType: 'promotion',
              },
              enriched_keywords: ['career', 'promotion', 'public_recognition'],
              keywords: ['Career', 'Promotion', 'Public fame/distinction'],
              laws_applied: [
                {
                  applies: true,
                  lawNumber: 11,
                  lawName: 'Benefics to MC Promise Honors',
                  strengthModifier: 0.8,
                },
              ],
              prediction_score: 100,
              significance: 100,
              tone: 'positive',
              prediction_tags: ['honor_award', 'public_recognition'],
            },
            {
              transiting: 'Moon',
              target_label: 'C7',
              natal: 'C7',
              aspect: 'Quincunx (contra-antiscia)',
              orb: 0.24,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2026-02-28T20:28:00Z',
                end: '2026-02-28T20:28:00Z',
              },
              prediction: {
                description: 'Moon Quincunx C7 (contra-antiscia)',
                lifeArea: 'conflict',
                eventType: 'attack_violence',
              },
              enriched_keywords: ['attack_violence', 'conflict'],
              keywords: ['Attack/violence', 'Conflict'],
              laws_applied: [
                {
                  applies: true,
                  lawNumber: 11,
                  lawName: 'Benefics to MC Promise Honors',
                  strengthModifier: 0.8,
                },
              ],
              prediction_score: 30,
              significance: 30,
              tone: 'mixed',
              prediction_tags: ['conflict', 'multiple_transit', 'mixed_outcome'],
            },
          ],
        },
      },
      inputs: {
        natalDate: '1948-05-14',
        natalTime: '16:00',
        natalLocation: 'Tel Aviv, Israel',
        natalTimezone: 'Asia/Jerusalem',
        transitDate: '2026-02-28',
        transitTime: '22:28',
      },
      resultAssertions: [
        { pattern: /^Critical Signals$/i },
        { pattern: /attack\/violence/i, multiple: true },
        { pattern: /conflict/i, multiple: true },
        { pattern: /Top critical transit: Moon Quincunx C7 \(contra-antiscia\)/i },
        { pattern: /^Mixed$/i, multiple: true },
      ],
    });
  });

  it('prioritizes war/conflict critical rows above broader accident rows at the same timestamp', async () => {
    await runDirectComputeCase({
      singleResponse: {
        data: {
          natal: {
            location: 'Tel Aviv, Israel',
            timezone: 'Asia/Jerusalem',
            house_system_code: 'R',
          },
          transit_timestamp: '2026-02-28T20:28:00Z',
          count: 3,
          moon_support: false,
          predictions: [
            {
              date: '2026-02-28T20:28:00Z',
              description: 'Mars Opposition Mars',
              event_type: 'accident_major',
              life_area: 'life',
              score: 69.6,
              probability: 1.0,
            },
            {
              date: '2026-02-28T20:28:00Z',
              description: 'Moon Quincunx C7 (contra-antiscia)',
              event_type: 'attack_violence',
              life_area: 'conflict',
              score: 30.0,
              probability: 1.0,
            },
          ],
          transits: [
            {
              transiting: 'Mars',
              target_label: 'Mars',
              natal: 'Mars',
              aspect: 'Opposition',
              orb: 0.42,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2026-02-28T20:28:00Z',
                end: '2026-02-28T20:28:00Z',
              },
              prediction: {
                description: 'Mars Opposition Mars',
                lifeArea: 'life',
                eventType: 'accident_major',
              },
              enriched_keywords: ['accident_major', 'fall_from_height'],
              keywords: ['Major accident', 'Fall from height'],
              prediction_score: 69.6,
              significance: 69.6,
              tone: 'negative',
              prediction_tags: ['mixed_outcome'],
              laws_applied: [],
            },
            {
              transiting: 'Saturn',
              target_label: 'Mars',
              natal: 'Mars',
              aspect: 'Quincunx (contra-antiscia)',
              orb: 0.57,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2026-02-28T20:28:00Z',
                end: '2026-02-28T20:28:00Z',
              },
              prediction: {
                description: 'Saturn Quincunx Mars (contra-antiscia)',
                lifeArea: 'life',
                eventType: 'death_natural',
              },
              enriched_keywords: ['death_natural'],
              keywords: ['Natural death'],
              prediction_score: 43.5,
              significance: 43.5,
              tone: 'negative',
              prediction_tags: ['mixed_outcome'],
              laws_applied: [],
            },
            {
              transiting: 'Moon',
              target_label: 'C7',
              natal: 'C7',
              aspect: 'Quincunx (contra-antiscia)',
              orb: 0.24,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2026-02-28T20:28:00Z',
                end: '2026-02-28T20:28:00Z',
              },
              prediction: {
                description: 'Moon Quincunx C7 (contra-antiscia)',
                lifeArea: 'conflict',
                eventType: 'attack_violence',
              },
              enriched_keywords: ['attack_violence', 'conflict'],
              keywords: ['Attack/violence', 'Conflict'],
              prediction_score: 30,
              significance: 30,
              tone: 'mixed',
              prediction_tags: ['conflict', 'multiple_transit', 'mixed_outcome'],
              laws_applied: [],
            },
          ],
        },
      },
      inputs: {
        natalDate: '1948-05-14',
        natalTime: '16:00',
        natalLocation: 'Tel Aviv, Israel',
        natalTimezone: 'Asia/Jerusalem',
        transitDate: '2026-02-28',
        transitTime: '22:28',
      },
      resultAssertions: [
        { pattern: /^Critical Signals$/i },
        { pattern: /attack\/violence/i, multiple: true },
        { pattern: /conflict/i, multiple: true },
        { pattern: /Top critical transit: Moon Quincunx C7 \(contra-antiscia\)/i },
      ],
    });
  });

  it('keeps the exact-time critical summary coherent when multiple crisis families coexist', async () => {
    astroClockApiMock.getTransits.mockResolvedValue({
      data: {
        natal: {
          location: 'Tel Aviv, Israel',
          timezone: 'Asia/Jerusalem',
          house_system_code: 'R',
        },
        transit_timestamp: '2026-02-28T20:28:00Z',
        count: 3,
        moon_support: false,
        predictions: [
          {
            date: '2026-02-28T20:28:00Z',
            description: 'Mars Opposition Mars',
            event_type: 'accident_major',
            life_area: 'life',
            score: 69.6,
            probability: 1.0,
          },
          {
            date: '2026-02-28T20:28:00Z',
            description: 'Moon Quincunx C7 (contra-antiscia)',
            event_type: 'attack_violence',
            life_area: 'conflict',
            score: 30.0,
            probability: 1.0,
          },
          {
            date: '2026-02-28T20:28:00Z',
            description: 'Saturn Quincunx Mars (contra-antiscia)',
            event_type: 'death_natural',
            life_area: 'life',
            score: 43.5,
            probability: 1.0,
          },
        ],
        transits: [
          {
            transiting: 'Mars',
            target_label: 'Mars',
            natal: 'Mars',
            aspect: 'Opposition',
            prediction: {
              description: 'Mars Opposition Mars',
              lifeArea: 'life',
              eventType: 'accident_major',
            },
            enriched_keywords: ['accident_major', 'fall_from_height'],
            keywords: ['Major accident', 'Fall from height'],
            prediction_score: 69.6,
            significance: 69.6,
            tone: 'negative',
          },
          {
            transiting: 'Saturn',
            target_label: 'Mars',
            natal: 'Mars',
            aspect: 'Quincunx (contra-antiscia)',
            prediction: {
              description: 'Saturn Quincunx Mars (contra-antiscia)',
              lifeArea: 'life',
              eventType: 'death_natural',
            },
            enriched_keywords: ['death_natural'],
            keywords: ['Natural death'],
            prediction_score: 43.5,
            significance: 43.5,
            tone: 'negative',
          },
          {
            transiting: 'Moon',
            target_label: 'C7',
            natal: 'C7',
            aspect: 'Quincunx (contra-antiscia)',
            prediction: {
              description: 'Moon Quincunx C7 (contra-antiscia)',
              lifeArea: 'conflict',
              eventType: 'attack_violence',
            },
            enriched_keywords: ['attack_violence', 'conflict'],
            keywords: ['Attack/violence', 'Conflict'],
            prediction_score: 30,
            significance: 30,
            tone: 'mixed',
          },
        ],
      },
    });

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-02-28',
      transitTime: '22:28',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    const criticalHeader = await screen.findByText(/^Critical Signals$/i);
    const criticalSection = criticalHeader.parentElement;
    expect(criticalSection).toBeTruthy();
    expect(within(criticalSection).getAllByText(/attack\/violence/i).length).toBeGreaterThan(0);
    expect(within(criticalSection).queryByText(/major accident/i)).not.toBeInTheDocument();
    expect(within(criticalSection).queryByText(/natural death/i)).not.toBeInTheDocument();
  });

  it('scores direct exact results with the same selected top-hit aggregate used by scan rows', async () => {
    astroClockApiMock.getTransits.mockResolvedValue({
      data: {
        natal: {
          location: 'Tel Aviv, Israel',
          timezone: 'Asia/Jerusalem',
          house_system_code: 'R',
        },
        transit_timestamp: '2026-05-06T19:00:00Z',
        count: 8,
        moon_support: false,
        predictions: [],
        transits: [
          { transiting: 'Mars', target_label: 'Mars', natal: 'Mars', target_type: 'planet', aspect: 'Opposition', prediction_score: 70, significance: 70, tone: 'negative' },
          { transiting: 'Jupiter', target_label: 'Venus', natal: 'Venus', target_type: 'planet', aspect: 'Trine', prediction_score: 60, significance: 60, tone: 'positive' },
          { transiting: 'Saturn', target_label: 'Moon', natal: 'Moon', target_type: 'planet', aspect: 'Square', prediction_score: 50, significance: 50, tone: 'negative' },
          { transiting: 'Sun', target_label: 'Mercury', natal: 'Mercury', target_type: 'planet', aspect: 'Sextile', prediction_score: 40, significance: 40, tone: 'positive' },
          { transiting: 'Moon', target_label: 'Asc', natal: 'Asc', target_type: 'cusp', aspect: 'Conjunction', prediction_score: 30, significance: 30, tone: 'mixed' },
          { transiting: 'Venus', target_label: 'MC', natal: 'MC', target_type: 'cusp', aspect: 'Trine', prediction_score: 20, significance: 20, tone: 'positive' },
          { transiting: 'Mercury', target_label: 'C7', natal: 'C7', target_type: 'cusp', aspect: 'Square', prediction_score: 10, significance: 10, tone: 'mixed' },
          { transiting: 'Sun', target_label: 'C4', natal: 'C4', target_type: 'cusp', aspect: 'Sextile', prediction_score: 5, significance: 5, tone: 'positive' },
        ],
      },
    });

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-05-06',
      transitTime: '22:00',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Compute Exact Time' }));

    expect(await screen.findByText('Score 240.0')).toBeInTheDocument();
    expect(screen.getByText('Hits 8')).toBeInTheDocument();
    expect(screen.queryByText('Score 285.0')).not.toBeInTheDocument();
  });

  it('keeps scan critical cards specific when predictor family support points elsewhere', async () => {
    const timestamp = '2026-05-06T19:00:00Z';
    astroClockApiMock.getTransitsWindow.mockResolvedValue(makeWindowResponse({
      timezone: 'Asia/Jerusalem',
      timestamp,
      eventType: 'attack_violence',
      lifeArea: 'conflict',
      description: 'Mars Square Asc',
      significance: 60,
      tone: 'negative',
      topHits: [
        {
          transiting: 'Mars',
          aspect: 'Square',
          target_label: 'Asc',
          target_type: 'cusp',
          orb: 0.2,
          tone: 'negative',
          significance: 60,
          prediction_score: 60,
          enriched_keywords: ['accident_major'],
          keywords: ['Major accident'],
          prediction_tags: ['accident_major', 'negative'],
          prediction: {
            description: 'Mars Square Asc',
            lifeArea: 'life',
            eventType: 'accident_major',
          },
          laws_applied: [],
        },
      ],
      rowPredictions: [
        {
          date: timestamp,
          description: 'Conflict context',
          event_type: 'attack_violence',
          life_area: 'conflict',
          score: 95,
          probability: 1.0,
        },
      ],
    }));
    astroClockApiMock.getTransits.mockResolvedValue({ data: { transits: [] } });

    const { container } = render(
      <TransitsModal open={true} onClose={() => {}} defaultHouseSystem="W" />
    );

    fillManualInputs(container, {
      natalDate: '1948-05-14',
      natalTime: '16:00',
      natalLocation: 'Tel Aviv, Israel',
      natalTimezone: 'Asia/Jerusalem',
      transitDate: '2026-05-06',
      transitTime: '22:00',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Scan Window' }));

    const scanHeader = await screen.findByText(/Critical Signals In Scan/i);
    const scanSection = scanHeader.parentElement;
    expect(scanSection).toBeTruthy();
    expect(within(scanSection).getByText(/major accident/i)).toBeInTheDocument();
    expect(within(scanSection).queryByText(/^critical signal$/i)).not.toBeInTheDocument();
  });

  it('renders slice-5 violent-event support through the modal for Shinzo Abe', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Asia/Tokyo',
        timestamp: '2022-07-08T02:30:00Z',
        eventType: 'delay_obstruction',
        lifeArea: 'life',
        description: 'Sun Quincunx Asc',
        predictionTags: [],
        significance: 100,
      }),
      singleResponse: {
        data: {
          natal: {
            location: 'Tokyo, Japan',
            timezone: 'Asia/Tokyo',
            house_system_code: 'W',
          },
          transit_timestamp: '2022-07-08T02:30:00Z',
          count: 1,
          moon_support: false,
          predictions: [
            {
              date: '2022-07-08T02:30:00Z',
              description: 'Sun Quincunx Asc',
              event_type: 'delay_obstruction',
              life_area: 'life',
              score: 100,
              probability: 1.0,
            },
          ],
          transits: [
            {
              transiting: 'Jupiter',
              target_label: 'Mercury',
              natal: 'Mercury',
              aspect: 'Quincunx',
              orb: 0.24,
              phase: 'applying',
              direction: 'sinister',
              effectiveWindow: {
                start: '2022-07-08T02:30:00Z',
                end: '2022-07-08T02:30:00Z',
              },
              prediction: {
                description: 'Sun Quincunx Asc',
                lifeArea: 'life',
                eventType: 'delay_obstruction',
              },
              enriched_keywords: ['accident_major'],
              keywords: ['Accident major'],
              laws_applied: [
                {
                  applies: true,
                  lawNumber: 11,
                  lawName: 'Benefics to MC Promise Honors',
                  strengthModifier: 0.8,
                },
              ],
              prediction_score: 60,
              significance: 60,
              tone: 'mixed',
              prediction_tags: [],
            },
          ],
        },
      },
      inputs: {
        natalDate: '1954-09-21',
        natalTime: '12:00',
        natalLocation: 'Tokyo, Japan',
        natalTimezone: 'Asia/Tokyo',
        transitDate: '2022-07-08',
        transitTime: '11:30',
      },
      peakLabel: /2022-07-08 11:30/i,
      scanAssertions: [],
      resultAssertions: [
        { pattern: /major accident/i, multiple: true },
      ],
    });
  });

  it('renders slice-3 Sergio predictor localization through the modal', async () => {
    await runPredictorReplayCase({
      predictorResponse: makePredictorResponse({
        windowStart: '2015-01-30T13:00:00+01:00',
        windowEnd: '2015-02-01T13:00:00+01:00',
        observerLocation: 'Palermo, Italy',
        timezone: 'Europe/Rome',
        peaks: [
          '2015-01-31T13:00:00+01:00',
          '2015-01-31T14:00:00+01:00',
        ],
        predictionGroups: [
          {
            event_type: 'recognition',
            life_area: 'honors',
            label: 'Jupiter Sextile Mercury (antiscia)',
            description: 'Jupiter Sextile Mercury (antiscia)',
            transit: 'Jupiter Sextile Mercury (antiscia)',
            count: 2,
            start: '2015-01-31T13:00:00+01:00',
            end: '2015-01-31T14:00:00+01:00',
            support_score: 78.4,
            probability_max: 0.42,
            probability_mean: 0.36,
            score_max: 18,
            score_mean: 16,
            keyword_tokens: ['recognition', 'honors', 'public_recognition'],
            tags: ['public_recognition'],
            occurrences: [
              { date: '2015-01-31T13:00:00+01:00', probability: 0.3, score: 14, support_score: 36.1 },
              { date: '2015-01-31T14:00:00+01:00', probability: 0.42, score: 18, support_score: 42.3 },
            ],
          },
        ],
      }),
      inputs: {
        natalDate: '1941-07-23',
        natalTime: '11:40',
        natalLocation: 'Palermo, Italy',
        natalTimezone: 'Europe/Rome',
        transitDate: '2015-01-31',
        transitTime: '13:00',
      },
      predictorAssertions: [
        { pattern: /Jupiter Sextile Mercury \(antiscia\)/i, multiple: true },
        { pattern: /Public fame\/distinction/i, multiple: true },
        { pattern: /Support 78\.4/i },
      ],
    });
  });

  it('renders slice-3 Obama predictor localization through the modal', async () => {
    await runPredictorReplayCase({
      predictorResponse: makePredictorResponse({
        windowStart: '2009-10-08T11:00:00+02:00',
        windowEnd: '2009-10-10T11:00:00+02:00',
        observerLocation: 'Honolulu, Hawaii',
        timezone: 'Europe/Oslo',
        peaks: [
          '2009-10-09T18:00:00+02:00',
          '2009-10-09T22:00:00+02:00',
        ],
        predictions: [
          {
            date: '2009-10-09T11:00:00+02:00',
            event_type: null,
            life_area: 'life',
            description: 'Jupiter Conjunction Asc',
            score: 95.4,
            probability: 0.954,
            tags: ['authority_earned', 'structure_established'],
            factors: { transit: 'Jupiter Conjunction Asc' },
          },
        ],
      }),
      inputs: {
        natalDate: '1961-08-04',
        natalTime: '19:24',
        natalLocation: 'Honolulu, Hawaii',
        natalTimezone: 'Pacific/Honolulu',
        transitDate: '2009-10-09',
        transitTime: '11:00',
      },
      predictorAssertions: [
        { pattern: /Transit: Jupiter Conjunction Asc/i },
        { pattern: /Authority earned/i, multiple: true },
        { pattern: /Structure established/i, multiple: true },
      ],
    });
  });

  it('renders slice-3 Al Gore predictor localization through the modal', async () => {
    await runPredictorReplayCase({
      predictorResponse: makePredictorResponse({
        windowStart: '2007-10-11T11:00:00+02:00',
        windowEnd: '2007-10-13T11:00:00+02:00',
        observerLocation: 'Washington, District of Columbia',
        timezone: 'Europe/Oslo',
        peaks: [
          '2007-10-12T16:00:00+02:00',
          '2007-10-12T21:00:00+02:00',
        ],
        predictions: [
          {
            date: '2007-10-12T11:00:00+02:00',
            event_type: null,
            life_area: null,
            description: 'Jupiter Trine Saturn',
            score: 0,
            probability: 0,
            tags: ['authority_earned', 'structure_established'],
            factors: { transit: 'Jupiter Trine Saturn' },
          },
        ],
      }),
      inputs: {
        natalDate: '1948-03-31',
        natalTime: '12:53',
        natalLocation: 'Washington, District of Columbia',
        natalTimezone: 'America/New_York',
        transitDate: '2007-10-12',
        transitTime: '11:00',
      },
      predictorAssertions: [
        { pattern: /Jupiter Trine Saturn/i, multiple: true },
        { pattern: /Authority earned/i, multiple: true },
        { pattern: /Structure established/i, multiple: true },
      ],
    });
  });

  it('renders slice-6 crisis-support retention through the predictor modal for George W. Bush', async () => {
    await runPredictorReplayCase({
      predictorResponse: makePredictorResponse({
        windowStart: '2003-03-18T22:16:00-05:00',
        windowEnd: '2003-03-20T22:16:00-05:00',
        observerLocation: 'New Haven, Connecticut',
        timezone: 'America/New_York',
        peaks: [
          '2003-03-19T03:16:00-05:00',
          '2003-03-20T03:16:00-05:00',
        ],
        predictions: [
          {
            date: '2003-03-19T22:16:00-05:00',
            event_type: 'structure_established',
            life_area: 'honors',
            description: 'Saturn Sextile MC',
            score: 31.5,
            probability: 0.315,
            tags: ['accident_major'],
            factors: { transit: 'Mars Quincunx Mercury' },
          },
        ],
      }),
      inputs: {
        natalDate: '1946-07-06',
        natalTime: '07:26',
        natalLocation: 'New Haven, Connecticut',
        natalTimezone: 'America/New_York',
        transitDate: '2003-03-19',
        transitTime: '22:16',
      },
      predictorAssertions: [
        { pattern: /Transit: Mars Quincunx Mercury/i },
        { pattern: /Major accident/i, multiple: true },
      ],
    });
  });

  it('renders slice-6 crisis-support retention through the predictor modal for Shinzo Abe', async () => {
    await runPredictorReplayCase({
      predictorResponse: makePredictorResponse({
        windowStart: '2022-07-07T11:30:00+09:00',
        windowEnd: '2022-07-09T11:30:00+09:00',
        observerLocation: 'Tokyo, Japan',
        timezone: 'Asia/Tokyo',
        peaks: [
          '2022-07-08T18:30:00+09:00',
          '2022-07-08T19:30:00+09:00',
        ],
        predictions: [
          {
            date: '2022-07-08T11:30:00+09:00',
            event_type: 'delay_obstruction',
            life_area: 'life',
            description: 'Sun Quincunx Asc',
            score: 60,
            probability: 0.6,
            tags: ['accident_major'],
            factors: { transit: 'Jupiter Quincunx Mercury (contra-antiscia)' },
          },
        ],
      }),
      inputs: {
        natalDate: '1954-09-21',
        natalTime: '12:00',
        natalLocation: 'Tokyo, Japan',
        natalTimezone: 'Asia/Tokyo',
        transitDate: '2022-07-08',
        transitTime: '11:30',
      },
      predictorAssertions: [
        { pattern: /Transit: Jupiter Quincunx Mercury \(contra-antiscia\)/i },
        { pattern: /Major accident/i, multiple: true },
      ],
    });
  });

  it('renders slice-7 Charles and Diana marriage-support signals through the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/London',
        timestamp: '1981-07-29T10:20:00Z',
        eventType: 'marriage',
        lifeArea: 'marriage',
        description: 'Jupiter Semi-sextile Mercury',
        predictionTags: ['family_celebration', 'wedding'],
        significance: 81,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'London, England',
        timezone: 'Europe/London',
        houseSystem: 'W',
        transitTimestamp: '1981-07-29T10:20:00Z',
        transiting: 'Jupiter',
        targetLabel: 'Mercury',
        aspect: 'Semi-sextile',
        lifeArea: 'marriage',
        eventType: 'marriage',
        description: 'Jupiter Semi-sextile Mercury',
        enrichedKeywords: ['family_celebration', 'marriage', 'wedding'],
        keywords: ['Family/domestic celebration', 'Marriage', 'Wedding'],
        predictionTags: ['family_celebration', 'wedding'],
        significance: 81,
      }),
      inputs: {
        natalDate: '1948-11-14',
        natalTime: '21:14',
        natalLocation: 'London, England',
        natalTimezone: 'Europe/London',
        transitDate: '1981-07-29',
        transitTime: '11:20',
      },
      peakLabel: /1981-07-29 11:20/i,
      scanAssertions: [
        { pattern: /marriage/i },
      ],
      resultAssertions: [
        { pattern: /Marriage/i, multiple: true },
        { pattern: /family\/domestic celebration/i, multiple: true },
        { pattern: /wedding/i, multiple: true },
      ],
    });
  });

  it('renders slice-7 Prince Harry marriage-support signals through the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/London',
        timestamp: '2018-05-19T11:00:00Z',
        eventType: null,
        lifeArea: 'marriage',
        description: 'Jupiter Semi-sextile Venus',
        predictionTags: ['engagement'],
        significance: 100,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'London, England',
        timezone: 'Europe/London',
        houseSystem: 'W',
        transitTimestamp: '2018-05-19T11:00:00Z',
        transiting: 'Venus',
        targetLabel: 'C7',
        aspect: 'Conjunction',
        lifeArea: 'marriage',
        eventType: null,
        description: 'Venus Conjunction C7',
        enrichedKeywords: ['engagement', 'family_celebration', 'marriage', 'partnership_strengthened', 'wedding'],
        keywords: ['Engagement', 'Family/domestic celebration', 'Marriage', 'Partnership strengthened', 'Wedding'],
        predictionTags: ['partnership_strengthened'],
        significance: 36,
      }),
      inputs: {
        natalDate: '1984-09-15',
        natalTime: '16:20',
        natalLocation: 'London, England',
        natalTimezone: 'Europe/London',
        transitDate: '2018-05-19',
        transitTime: '12:00',
      },
      peakLabel: /2018-05-19 12:00/i,
      scanAssertions: [],
      resultAssertions: [
        { pattern: /Marriage/i, multiple: true },
        { pattern: /Partnership strengthened/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive house-domain labels in the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Asia/Jerusalem',
        timestamp: '2026-02-03T12:00:00+02:00',
        eventType: 'contract_signing',
        lifeArea: 'siblings',
        description: 'Mercury Trine C3 supports dealings among brothers or relations.',
        predictionTags: ['wealth', 'service', 'hidden_enemies'],
        significance: 54,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        houseSystem: 'W',
        transitTimestamp: '2026-02-03T12:00:00+02:00',
        transiting: 'Mercury',
        targetLabel: 'C3',
        aspect: 'Trine',
        lifeArea: 'siblings',
        eventType: 'contract_signing',
        description: 'Mercury Trine C3 supports dealings among brothers or relations.',
        enrichedKeywords: ['wealth', 'service', 'hidden_enemies'],
        keywords: ['wealth', 'service', 'hidden_enemies'],
        predictionTags: ['wealth', 'service', 'hidden_enemies'],
        significance: 54,
      }),
      inputs: {
        natalDate: '1948-05-14',
        natalTime: '16:00',
        natalLocation: 'Tel Aviv, Israel',
        natalTimezone: 'Asia/Jerusalem',
        transitDate: '2026-02-03',
        transitTime: '12:00',
      },
      peakLabel: /2026-02-03 12:00/i,
      resultAssertions: [
        { pattern: /brothers\/relations/i, multiple: true },
        { pattern: /wealth\/acquired goods/i, multiple: true },
        { pattern: /servants\/subordinates\/animals/i, multiple: true },
        { pattern: /secret enemies\/hardships/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive event-family labels in the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Asia/Jerusalem',
        timestamp: '2026-02-05T12:00:00+02:00',
        eventType: 'public_recognition',
        lifeArea: 'honors',
        description: 'Sun Trine MC supports public distinction.',
        predictionTags: ['business_deal', 'contract_signing', 'financial_gain', 'recovery_health'],
        significance: 58,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        houseSystem: 'W',
        transitTimestamp: '2026-02-05T12:00:00+02:00',
        transiting: 'Sun',
        targetLabel: 'MC',
        aspect: 'Trine',
        lifeArea: 'honors',
        eventType: 'public_recognition',
        description: 'Sun Trine MC supports public distinction.',
        enrichedKeywords: ['business_deal', 'contract_signing', 'financial_gain', 'recovery_health'],
        keywords: ['business_deal', 'contract_signing', 'financial_gain', 'recovery_health'],
        predictionTags: ['business_deal', 'contract_signing', 'financial_gain', 'recovery_health'],
        significance: 58,
      }),
      inputs: {
        natalDate: '1948-05-14',
        natalTime: '16:00',
        natalLocation: 'Tel Aviv, Israel',
        natalTimezone: 'Asia/Jerusalem',
        transitDate: '2026-02-05',
        transitTime: '12:00',
      },
      peakLabel: /2026-02-05 12:00/i,
      resultAssertions: [
        { pattern: /public fame\/distinction/i, multiple: true },
        { pattern: /business\/contract agreement/i, multiple: true },
        { pattern: /contract\/agreement/i, multiple: true },
        { pattern: /gain in wealth\/income/i, multiple: true },
        { pattern: /recovery from illness/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive relationship-family labels in the modal for courtship rows', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Asia/Jerusalem',
        timestamp: '2026-02-06T12:00:00+02:00',
        eventType: 'romantic_connection',
        lifeArea: 'relationships',
        description: 'Venus Trine C7 supports a courtship or affectionate attachment.',
        predictionTags: ['reconciliation', 'engagement', 'partnership_strengthened'],
        significance: 59,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        houseSystem: 'W',
        transitTimestamp: '2026-02-06T12:00:00+02:00',
        transiting: 'Venus',
        targetLabel: 'C7',
        aspect: 'Trine',
        lifeArea: 'relationships',
        eventType: 'romantic_connection',
        description: 'Venus Trine C7 supports a courtship or affectionate attachment.',
        enrichedKeywords: ['reconciliation', 'engagement', 'partnership_strengthened', 'romance'],
        keywords: ['reconciliation', 'engagement', 'partnership_strengthened', 'romance'],
        predictionTags: ['reconciliation', 'engagement', 'partnership_strengthened'],
        significance: 59,
      }),
      inputs: {
        natalDate: '1948-05-14',
        natalTime: '16:00',
        natalLocation: 'Tel Aviv, Israel',
        natalTimezone: 'Asia/Jerusalem',
        transitDate: '2026-02-06',
        transitTime: '12:00',
      },
      peakLabel: /2026-02-06 12:00/i,
      resultAssertions: [
        { pattern: /courtship\/attachment/i, multiple: true },
        { pattern: /reconciliation\/renewed accord/i, multiple: true },
        { pattern: /engagement\/betrothal/i, multiple: true },
        { pattern: /partnership strengthened\/confirmed/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive relationship-family labels in the modal for dispute rows', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Asia/Jerusalem',
        timestamp: '2026-02-07T12:00:00+02:00',
        eventType: 'relationship_conflict',
        lifeArea: 'relationships',
        description: 'Mars Square C7 supports partnership conflict or open dispute.',
        predictionTags: ['separation', 'betrayal', 'partnership_strained'],
        significance: 61,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Tel Aviv, Israel',
        timezone: 'Asia/Jerusalem',
        houseSystem: 'W',
        transitTimestamp: '2026-02-07T12:00:00+02:00',
        transiting: 'Mars',
        targetLabel: 'C7',
        aspect: 'Square',
        lifeArea: 'relationships',
        eventType: 'relationship_conflict',
        description: 'Mars Square C7 supports partnership conflict or open dispute.',
        enrichedKeywords: ['separation', 'betrayal', 'partnership_strained', 'conflict'],
        keywords: ['separation', 'betrayal', 'partnership_strained', 'conflict'],
        predictionTags: ['separation', 'betrayal', 'partnership_strained'],
        significance: 61,
      }),
      inputs: {
        natalDate: '1948-05-14',
        natalTime: '16:00',
        natalLocation: 'Tel Aviv, Israel',
        natalTimezone: 'Asia/Jerusalem',
        transitDate: '2026-02-07',
        transitTime: '12:00',
      },
      peakLabel: /2026-02-07 12:00/i,
      resultAssertions: [
        { pattern: /partnership\/open dispute/i, multiple: true },
        { pattern: /separation\/estrangement/i, multiple: true },
        { pattern: /breach of trust/i, multiple: true },
        { pattern: /partnership strained\/disputed/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive wealth-family labels in the modal for gain rows', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/Rome',
        timestamp: '2026-05-01T10:00:00Z',
        eventType: 'financial_gain',
        lifeArea: 'wealth',
        description: 'Jupiter Trine C2 supports gain through speculation or hazard.',
        predictionTags: ['salary_increase', 'inheritance_windfall', 'speculation_gain'],
        significance: 92,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Rome, Italy',
        timezone: 'Europe/Rome',
        transitTimestamp: '2026-05-01T10:00:00Z',
        transiting: 'Jupiter',
        targetLabel: 'C2',
        aspect: 'Trine',
        lifeArea: 'wealth',
        eventType: 'financial_gain',
        description: 'Jupiter Trine C2 supports gain through speculation or hazard.',
        enrichedKeywords: ['salary_increase', 'inheritance_windfall', 'speculation_gain'],
        keywords: ['Wealth/acquired goods', 'Increase in salary/income', 'Inheritance/succession gain'],
        predictionTags: ['salary_increase', 'inheritance_windfall', 'speculation_gain'],
        significance: 92,
      }),
      inputs: {
        natalDate: '1980-01-01',
        natalTime: '12:00',
        natalLocation: 'Rome, Italy',
        natalTimezone: 'Europe/Rome',
        transitDate: '2026-05-01',
        transitTime: '12:00',
      },
      peakLabel: /2026-05-01 12:00/i,
      resultAssertions: [
        { pattern: /gain in wealth\/income/i, multiple: true },
        { pattern: /increase in salary\/income/i, multiple: true },
        { pattern: /inheritance\/succession gain/i, multiple: true },
        { pattern: /speculation\/hazard gain/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive wealth-family labels in the modal for loss rows', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/Rome',
        timestamp: '2026-05-02T10:00:00Z',
        eventType: 'financial_loss',
        lifeArea: 'wealth',
        description: 'Saturn Square C2 points to loss through debts or shared burdens.',
        predictionTags: ['shared_resource_loss', 'speculation_loss'],
        significance: 88,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Rome, Italy',
        timezone: 'Europe/Rome',
        transitTimestamp: '2026-05-02T10:00:00Z',
        transiting: 'Saturn',
        targetLabel: 'C2',
        aspect: 'Square',
        lifeArea: 'wealth',
        eventType: 'financial_loss',
        description: 'Saturn Square C2 points to loss through debts or shared burdens.',
        enrichedKeywords: ['shared_resource_loss', 'speculation_loss'],
        keywords: ['Wealth/acquired goods', 'Loss through debts/shared burdens', 'Speculation/hazard loss'],
        predictionTags: ['shared_resource_loss', 'speculation_loss'],
        significance: 88,
      }),
      inputs: {
        natalDate: '1980-01-01',
        natalTime: '12:00',
        natalLocation: 'Rome, Italy',
        natalTimezone: 'Europe/Rome',
        transitDate: '2026-05-02',
        transitTime: '12:00',
      },
      peakLabel: /2026-05-02 12:00/i,
      resultAssertions: [
        { pattern: /loss of wealth\/expense/i, multiple: true },
        { pattern: /loss through debts\/shared burdens/i, multiple: true },
        { pattern: /speculation\/hazard loss/i, multiple: true },
      ],
    });
  });

  it('prefers area-aware fallback event labels when a row has no explicit eventType', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/London',
        timestamp: '2026-05-14T09:00:00Z',
        eventType: null,
        lifeArea: 'wealth',
        description: 'Jupiter Trine C2 supports gain in wealth or income.',
        predictionTags: ['promotion', 'financial_gain'],
        significance: 58,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'London, England',
        timezone: 'Europe/London',
        transitTimestamp: '2026-05-14T09:00:00Z',
        transiting: 'Jupiter',
        targetLabel: 'C2',
        aspect: 'Trine',
        lifeArea: 'wealth',
        eventType: null,
        description: 'Jupiter Trine C2 supports gain in wealth or income.',
        enrichedKeywords: ['promotion', 'financial_gain'],
        keywords: ['Wealth/acquired goods'],
        predictionTags: ['promotion', 'financial_gain'],
        significance: 58,
      }),
      inputs: {
        natalDate: '1984-04-04',
        natalTime: '08:30',
        natalLocation: 'London, England',
        natalTimezone: 'Europe/London',
        transitDate: '2026-05-14',
        transitTime: '10:00',
      },
      peakLabel: /2026-05-14 10:00/i,
      resultAssertions: [
        { pattern: /gain in wealth\/income/i, multiple: true },
        { pattern: /wealth\/acquired goods/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive home and travel labels in the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/London',
        timestamp: '2026-06-10T09:00:00Z',
        eventType: 'moving_home',
        lifeArea: 'home',
        description: 'Moon Conjunction C4 supports a change of home or residence.',
        predictionTags: ['family_celebration', 'purchase_property', 'relocation_permanent', 'short_journey', 'long_journey'],
        significance: 64,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'London, England',
        timezone: 'Europe/London',
        transitTimestamp: '2026-06-10T09:00:00Z',
        transiting: 'Moon',
        targetLabel: 'C4',
        aspect: 'Conjunction',
        lifeArea: 'home',
        eventType: 'moving_home',
        description: 'Moon Conjunction C4 supports a change of home or residence.',
        enrichedKeywords: ['family_celebration', 'purchase_property', 'relocation_permanent', 'short_journey', 'long_journey'],
        keywords: ['Family/domestic celebration', 'Purchase of land/home', 'Permanent change of residence', 'Short journey/local movement', 'Long journey/distant travel'],
        predictionTags: ['family_celebration', 'purchase_property', 'relocation_permanent', 'short_journey', 'long_journey'],
        significance: 64,
      }),
      inputs: {
        natalDate: '1984-04-04',
        natalTime: '08:30',
        natalLocation: 'London, England',
        natalTimezone: 'Europe/London',
        transitDate: '2026-06-10',
        transitTime: '10:00',
      },
      peakLabel: /2026-06-10 10:00/i,
      resultAssertions: [
        { pattern: /change of home\/residence/i, multiple: true },
        { pattern: /family\/domestic celebration/i, multiple: true },
        { pattern: /purchase of land\/home/i, multiple: true },
        { pattern: /permanent change of residence/i, multiple: true },
        { pattern: /parents\/home\/inheritance/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive travel labels in the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/London',
        timestamp: '2026-06-11T09:00:00Z',
        eventType: 'short_journey',
        lifeArea: 'short_journeys',
        description: 'Mercury Sextile C3 supports a short journey or local movement.',
        predictionTags: ['long_journey'],
        significance: 57,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'London, England',
        timezone: 'Europe/London',
        transitTimestamp: '2026-06-11T09:00:00Z',
        transiting: 'Mercury',
        targetLabel: 'C3',
        aspect: 'Sextile',
        lifeArea: 'short_journeys',
        eventType: 'short_journey',
        description: 'Mercury Sextile C3 supports a short journey or local movement.',
        enrichedKeywords: ['long_journey'],
        keywords: ['Brothers/relations and short journeys', 'Long journey/distant travel'],
        predictionTags: ['long_journey'],
        significance: 57,
      }),
      inputs: {
        natalDate: '1984-04-04',
        natalTime: '08:30',
        natalLocation: 'London, England',
        natalTimezone: 'Europe/London',
        transitDate: '2026-06-11',
        transitTime: '10:00',
      },
      peakLabel: /2026-06-11 10:00/i,
      resultAssertions: [
        { pattern: /brothers\/relations and short journeys/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive spiritual labels in the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/Athens',
        timestamp: '2026-09-01T09:00:00Z',
        eventType: 'spiritual_awakening',
        lifeArea: 'belief',
        description: 'Jupiter Trine C9 supports a religious or spiritual awakening.',
        predictionTags: ['religious_conversion', 'pilgrimage', 'mystical_experience'],
        significance: 72,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Athens, Greece',
        timezone: 'Europe/Athens',
        transitTimestamp: '2026-09-01T09:00:00Z',
        transiting: 'Jupiter',
        targetLabel: 'C9',
        aspect: 'Trine',
        lifeArea: 'belief',
        eventType: 'spiritual_awakening',
        description: 'Jupiter Trine C9 supports a religious or spiritual awakening.',
        enrichedKeywords: ['religious_conversion', 'pilgrimage', 'mystical_experience'],
        keywords: ['Religion/journeys', 'Pilgrimage/religious journey', 'Visionary/mystical experience'],
        predictionTags: ['religious_conversion', 'pilgrimage', 'mystical_experience'],
        significance: 72,
      }),
      inputs: {
        natalDate: '1990-03-03',
        natalTime: '06:15',
        natalLocation: 'Athens, Greece',
        natalTimezone: 'Europe/Athens',
        transitDate: '2026-09-01',
        transitTime: '12:00',
      },
      peakLabel: /2026-09-01 12:00/i,
      resultAssertions: [
        { pattern: /religious\/spiritual awakening/i, multiple: true },
        { pattern: /change of religion\/faith/i, multiple: true },
        { pattern: /pilgrimage\/religious journey/i, multiple: true },
        { pattern: /visionary\/mystical experience/i, multiple: true },
        { pattern: /religion\/journeys/i, multiple: true },
      ],
    });
  });

  it('renders source-sensitive study and publication labels in the modal', async () => {
    await runReplayCase({
      windowResponse: makeWindowResponse({
        timezone: 'Europe/Athens',
        timestamp: '2026-09-02T09:00:00Z',
        eventType: 'degree_completion',
        lifeArea: 'belief',
        description: 'Mercury Trine C9 supports completion of studies or degree.',
        predictionTags: ['exam_success', 'enrollment_admission', 'publication', 'artistic_success'],
        significance: 68,
      }),
      singleResponse: makeSingleTransitResponse({
        natalLocation: 'Athens, Greece',
        timezone: 'Europe/Athens',
        transitTimestamp: '2026-09-02T09:00:00Z',
        transiting: 'Mercury',
        targetLabel: 'C9',
        aspect: 'Trine',
        lifeArea: 'belief',
        eventType: 'degree_completion',
        description: 'Mercury Trine C9 supports completion of studies or degree.',
        enrichedKeywords: ['exam_success', 'enrollment_admission', 'publication', 'artistic_success'],
        keywords: ['Religion/journeys', 'Completion of studies/degree', 'Publication/issued work'],
        predictionTags: ['exam_success', 'enrollment_admission', 'publication', 'artistic_success'],
        significance: 68,
      }),
      inputs: {
        natalDate: '1990-03-03',
        natalTime: '06:15',
        natalLocation: 'Athens, Greece',
        natalTimezone: 'Europe/Athens',
        transitDate: '2026-09-02',
        transitTime: '12:00',
      },
      peakLabel: /2026-09-02 12:00/i,
      resultAssertions: [
        { pattern: /completion of studies\/degree/i, multiple: true },
        { pattern: /success in examination/i, multiple: true },
        { pattern: /admission\/entrance into study/i, multiple: true },
        { pattern: /publication\/issued work/i, multiple: true },
        { pattern: /artistic distinction\/success/i, multiple: true },
        { pattern: /religion\/journeys/i, multiple: true },
      ],
    });
  });
});
