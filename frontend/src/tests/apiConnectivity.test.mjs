import { describe, expect, it } from 'vitest';

import {
  resolveApiStatusAfterPingFailure,
} from '../utils/apiConnectivity.mjs';

describe('resolveApiStatusAfterPingFailure', () => {
  it('keeps the UI in checking during the startup grace window', () => {
    expect(
      resolveApiStatusAfterPingFailure({
        currentStatus: 'checking',
        startupDeadlineMs: 2_000,
        nowMs: 1_500,
      })
    ).toBe('checking');
  });

  it('marks the API offline after the startup grace window expires', () => {
    expect(
      resolveApiStatusAfterPingFailure({
        currentStatus: 'checking',
        startupDeadlineMs: 2_000,
        nowMs: 2_500,
      })
    ).toBe('offline');
  });

  it('marks the API offline immediately after a post-startup disconnect', () => {
    expect(
      resolveApiStatusAfterPingFailure({
        currentStatus: 'connected',
        startupDeadlineMs: 9_999,
        nowMs: 1_500,
      })
    ).toBe('offline');
  });
});
