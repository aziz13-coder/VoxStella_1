import { beforeEach, describe, expect, it } from 'vitest';

import {
  clearAstroClockWarmState,
  formatAstroClockTimezoneLabel,
  readAstroClockWarmState,
  resolveManualSnapshotTarget,
  shouldApplyAstroClockRequest,
  writeAstroClockWarmState,
} from '../features/astroclock/astroClockViewState.mjs';

describe('astro clock view state helpers', () => {
  beforeEach(() => {
    clearAstroClockWarmState();
  });

  it('uses the current dashboard snapshot when entering manual mode from realtime', () => {
    expect(resolveManualSnapshotTarget({
      activeManualIso: null,
      dataTimestamp: '2026-03-08T10:00:00Z',
      dataLocation: 'Jerusalem, Israel',
      manualLocation: '',
      timezoneLabel: 'Asia/Jerusalem',
      fallbackIso: '2026-03-08T10:05:00Z',
    })).toEqual({
      iso: '2026-03-08T10:00:00Z',
      location: 'Jerusalem, Israel',
      timezone: 'Asia/Jerusalem',
    });
  });

  it('keeps the snapped manual ISO when already viewing a manual chart', () => {
    expect(resolveManualSnapshotTarget({
      activeManualIso: '2026-03-09T12:30:00Z',
      dataTimestamp: '2026-03-08T10:00:00Z',
      dataLocation: '',
      manualLocation: 'Berlin, Germany',
      timezoneLabel: '',
      fallbackIso: '2026-03-08T10:05:00Z',
    })).toEqual({
      iso: '2026-03-09T12:30:00Z',
      location: 'Berlin, Germany',
      timezone: undefined,
    });
  });

  it('rejects stale requests from an older view version or request id', () => {
    expect(shouldApplyAstroClockRequest({
      requestId: 4,
      latestRequestId: 4,
      viewVersion: 2,
      latestViewVersion: 2,
    })).toBe(true);

    expect(shouldApplyAstroClockRequest({
      requestId: 3,
      latestRequestId: 4,
      viewVersion: 2,
      latestViewVersion: 2,
    })).toBe(false);

    expect(shouldApplyAstroClockRequest({
      requestId: 4,
      latestRequestId: 4,
      viewVersion: 1,
      latestViewVersion: 2,
    })).toBe(false);
  });

  it('recomputes the displayed UTC offset from the active timezone and timestamp', () => {
    expect(formatAstroClockTimezoneLabel({
      timestamp: '2026-03-08T16:20:00Z',
      timezone: 'America/New_York',
      timezoneLabel: 'America/New_York (UTC+00:00)',
    })).toBe('America/New_York (UTC-04:00)');
  });

  it('keeps a warm in-memory astro clock snapshot for in-app remounts', () => {
    writeAstroClockWarmState({
      mode: 'manual',
      manualLocation: 'Jerusalem, Israel',
      data: { timestamp: '2026-03-08T10:00:00Z' },
      hours: { current_hour: { ruling_planet: 'Sun' } },
    });

    expect(readAstroClockWarmState()).toMatchObject({
      mode: 'manual',
      manualLocation: 'Jerusalem, Israel',
      data: { timestamp: '2026-03-08T10:00:00Z' },
      hours: { current_hour: { ruling_planet: 'Sun' } },
    });
  });
});
