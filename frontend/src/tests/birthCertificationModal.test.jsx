import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import BirthCertificationModal from '../features/astroclock/BirthCertificationModal.jsx';

const astroClockApiMock = vi.hoisted(() => ({
  rectifyBirthTime: vi.fn(),
  resolveTimezone: vi.fn(),
  createSnap: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

function renderModal(props = {}) {
  return render(
    <BirthCertificationModal
      open
      onClose={vi.fn()}
      mode="manual"
      manualIso="1990-01-01T06:30:00+02:00"
      manualLocation="Jerusalem, Israel"
      timezone="Asia/Jerusalem"
      latitude={31.778}
      longitude={35.235}
      houseSystem="R"
      snaps={[]}
      snapsLoaded
      {...props}
    />
  );
}

const fakeResponse = {
  success: true,
  data: {
    meta: { row_count: 5, parity_note: 'Minute scan completed.' },
    certification: {
      status: 'rectified_candidate',
      confidence: 'medium',
      reason: 'A candidate minute is present, but this remains a model review.',
      candidate: {
        timestamp: '1990-01-01T06:32:00+02:00',
        strength: 91.2,
        dominant_curve: 'favorable',
        time_offset_minutes: 2,
      },
      data_quality: {
        event_count: 1,
        near_exact_event_count: 1,
        unique_theme_count: 1,
      },
    },
    top_candidates: [
      {
        rank: 1,
        timestamp: '1990-01-01T06:32:00+02:00',
        favorable: 91.2,
        tense: 38.4,
        strength: 91.2,
        dominant_curve: 'favorable',
        hit_count: 3,
      },
    ],
    periods: [
      {
        rank: 1,
        start: '1990-01-01T06:31:00+02:00',
        end: '1990-01-01T06:33:00+02:00',
        peak_strength: 91.2,
        dominant_curve: 'favorable',
        duration_minutes: 3,
      },
    ],
    series: [
      { timestamp: '1990-01-01T06:30:00+02:00', favorable: 20, tense: 5, strength: 20, dominant_curve: 'favorable' },
      { timestamp: '1990-01-01T06:31:00+02:00', favorable: 70, tense: 10, strength: 70, dominant_curve: 'favorable' },
      { timestamp: '1990-01-01T06:32:00+02:00', favorable: 91.2, tense: 38.4, strength: 91.2, dominant_curve: 'favorable' },
    ],
  },
};

describe('BirthCertificationModal', () => {
  beforeEach(() => {
    astroClockApiMock.rectifyBirthTime.mockReset();
    astroClockApiMock.resolveTimezone.mockReset();
    astroClockApiMock.createSnap.mockReset();
    astroClockApiMock.rectifyBirthTime.mockResolvedValue(fakeResponse);
    astroClockApiMock.resolveTimezone.mockResolvedValue({
      success: true,
      location: 'Tel Aviv, Israel',
      latitude: 32.0809,
      longitude: 34.7806,
      timezone: 'Asia/Jerusalem',
    });
    astroClockApiMock.createSnap.mockResolvedValue({
      success: true,
      data: { id: 'snap-certification', label: 'Certification - Jan 01, 1990, 06:32 AM' },
    });
  });

  it('uses a flat Synastry-style workspace shell without framed input cards', () => {
    const { container } = renderModal();

    const dialog = screen.getByRole('dialog', { name: 'Birth Time Certification' });
    expect(dialog).toHaveClass('rounded-[28px]');
    expect(container.querySelectorAll('section.rounded-2xl')).toHaveLength(0);
  });

  it('validates required birth fields before calling the API', async () => {
    renderModal({
      manualIso: '',
      manualLocation: '',
      timezone: '',
      latitude: undefined,
      longitude: undefined,
    });

    fireEvent.click(screen.getByRole('button', { name: 'Run Certification' }));

    expect(await screen.findByText('Birth date is required.')).toBeInTheDocument();
    expect(screen.getByText('Birth latitude and longitude are required.')).toBeInTheDocument();
    expect(screen.getByText('Birth timezone is required.')).toBeInTheDocument();
    expect(astroClockApiMock.rectifyBirthTime).not.toHaveBeenCalled();
  });

  it('resolves an event location through the shared location resolver', async () => {
    renderModal();

    fireEvent.change(screen.getByLabelText('Event location'), { target: { value: 'Tel Aviv' } });
    fireEvent.click(screen.getByRole('button', { name: 'Resolve Event 1 Location' }));

    await waitFor(() => expect(astroClockApiMock.resolveTimezone).toHaveBeenCalledWith('Tel Aviv'));
    expect(screen.getByLabelText('Event latitude')).toHaveValue(32.0809);
    expect(screen.getByLabelText('Event longitude')).toHaveValue(34.7806);
    expect(screen.getByLabelText('Event timezone')).toHaveValue('Asia/Jerusalem');
    expect(screen.getByText('Resolved: Tel Aviv, Israel')).toBeInTheDocument();
  });

  it('submits a normalized payload and renders certification results', async () => {
    renderModal();

    fireEvent.change(screen.getByLabelText('Event label'), { target: { value: 'Documented milestone' } });
    fireEvent.change(screen.getByLabelText('Event timestamp'), { target: { value: '2020-01-01T12:00:00+02:00' } });
    fireEvent.change(screen.getByLabelText('Event latitude'), { target: { value: '32.0809' } });
    fireEvent.change(screen.getByLabelText('Event longitude'), { target: { value: '34.7806' } });
    fireEvent.change(screen.getByLabelText('Event timezone'), { target: { value: 'Asia/Jerusalem' } });
    fireEvent.change(screen.getByLabelText('Event precision'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Event theme'), { target: { value: 'career' } });

    fireEvent.click(screen.getByRole('button', { name: 'Run Certification' }));

    await waitFor(() => expect(astroClockApiMock.rectifyBirthTime).toHaveBeenCalledTimes(1));
    const payload = astroClockApiMock.rectifyBirthTime.mock.calls[0][0];
    expect(payload).toMatchObject({
      birth: {
        date: '1990-01-01',
        location: 'Jerusalem, Israel',
        latitude: 31.778,
        longitude: 35.235,
        timezone: 'Asia/Jerusalem',
        source_time_status: 'unknown',
      },
      search: {
        start_time: '00:00',
        end_time: '23:59',
      },
      house_system_code: 'R',
      orb_degrees: 1,
      level_percent: 67,
      include_series: true,
      instruments: [
        { id: 'transit', weight: 1 },
        { id: 'direction_reverse', weight: 1 },
        { id: 'profection_reverse', weight: 1 },
        { id: 'primary_progression', weight: 1 },
        { id: 'secondary_progression_local', weight: 1 },
        { id: 'secondary_progression_natal', weight: 1 },
        { id: 'tertiary_progression', weight: 1 },
        { id: 'minor_progression', weight: 1 },
      ],
      events: [
        expect.objectContaining({
          label: 'Documented milestone',
          timestamp: '2020-01-01T12:00:00+02:00',
          latitude: 32.0809,
          longitude: 34.7806,
          timezone: 'Asia/Jerusalem',
          precision: 2,
          theme: 'career',
          weight: 1,
        }),
      ],
    });

    expect(await screen.findByText('Likely Rectified Candidate')).toBeInTheDocument();
    expect(screen.getByText('2 min')).toBeInTheDocument();
    expect(screen.getByText('Matching Periods')).toBeInTheDocument();
    expect(screen.getByText('Minute scan completed.')).toBeInTheDocument();
    expect(within(screen.getByLabelText('Candidate results')).getAllByText('91.2').length).toBeGreaterThan(0);
  });

  it('saves the selected certification candidate as a saved snap', async () => {
    const onRefreshSnaps = vi.fn().mockResolvedValue(undefined);
    renderModal({ onRefreshSnaps });

    fireEvent.change(screen.getByLabelText('Event label'), { target: { value: 'Documented milestone' } });
    fireEvent.change(screen.getByLabelText('Event timestamp'), { target: { value: '2020-01-01T12:00:00+02:00' } });
    fireEvent.change(screen.getByLabelText('Event latitude'), { target: { value: '32.0809' } });
    fireEvent.change(screen.getByLabelText('Event longitude'), { target: { value: '34.7806' } });
    fireEvent.change(screen.getByLabelText('Event timezone'), { target: { value: 'Asia/Jerusalem' } });

    fireEvent.click(screen.getByRole('button', { name: 'Run Certification' }));

    expect(await screen.findByText('Likely Rectified Candidate')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Save Certification Snap' }));

    await waitFor(() => expect(astroClockApiMock.createSnap).toHaveBeenCalledTimes(1));
    expect(astroClockApiMock.createSnap).toHaveBeenCalledWith(expect.objectContaining({
      label: expect.stringContaining('Certification'),
      mode: 'manual',
      datetime: '1990-01-01T06:32:00+02:00',
      location: 'Jerusalem, Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
      certification: expect.objectContaining({
        kind: 'birth_time_certification',
        status: 'rectified_candidate',
        confidence: 'medium',
        selected_candidate: expect.objectContaining({
          timestamp: '1990-01-01T06:32:00+02:00',
          strength: 91.2,
          time_offset_minutes: 2,
        }),
        data_quality: expect.objectContaining({
          event_count: 1,
          near_exact_event_count: 1,
        }),
      }),
    }));
    await waitFor(() => expect(onRefreshSnaps).toHaveBeenCalledWith({ silent: true }));
    expect(screen.getByText('Certification snap saved.')).toBeInTheDocument();
  });
});
