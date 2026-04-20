import { afterEach, describe, expect, it, vi } from 'vitest';

import { pollResearchSession } from '../features/astroclock/researchPolling.mjs';

afterEach(() => {
  vi.useRealTimers();
});

describe('pollResearchSession', () => {
  it('returns as soon as the backend marks the session ready', async () => {
    const fetchProgress = vi.fn().mockResolvedValue({ ready: true, done: 10, total: 10 });

    await expect(
      pollResearchSession({ fetchProgress })
    ).resolves.toEqual({ ready: true, done: 10, total: 10 });

    expect(fetchProgress).toHaveBeenCalledTimes(1);
  });

  it('times out stalled sessions', async () => {
    vi.useFakeTimers();
    const fetchProgress = vi.fn().mockResolvedValue({ ready: false, done: 1, total: 10 });

    const pending = pollResearchSession({
      fetchProgress,
      delayMs: 100,
      timeoutMs: 150,
    });
    const expectation = expect(pending).rejects.toThrow('Timed out waiting for research compile to finish');

    await vi.advanceTimersByTimeAsync(250);

    await expectation;
    expect(fetchProgress).toHaveBeenCalledTimes(2);
  });

  it('aborts cleanly when the caller cancels the polling loop', async () => {
    vi.useFakeTimers();
    let active = true;
    const fetchProgress = vi.fn().mockResolvedValue({ ready: false, done: 1, total: 10 });

    const pending = pollResearchSession({
      fetchProgress,
      shouldContinue: () => active,
      delayMs: 100,
    });
    const expectation = expect(pending).rejects.toThrow('Research compile cancelled');

    await Promise.resolve();
    active = false;
    await vi.advanceTimersByTimeAsync(100);

    await expectation;
    expect(fetchProgress).toHaveBeenCalledTimes(1);
  });
});
