import { beforeEach, describe, expect, it } from 'vitest';

import { shouldIgnoreElectionStreamError } from '../features/astroclock/electionStreamState.mjs';


describe('election stream error handling', () => {
  beforeEach(() => {
    global.EventSource = { CLOSED: 2 };
  });

  it('ignores errors after the stream has already completed', () => {
    expect(
      shouldIgnoreElectionStreamError({
        currentSource: null,
        errorSource: { readyState: 2 },
        isTerminal: true,
        readyState: 2,
      })
    ).toBe(true);
  });

  it('ignores errors from stale event sources after a new scan replaces them', () => {
    const activeSource = { readyState: 1 };
    const staleSource = { readyState: 2 };

    expect(
      shouldIgnoreElectionStreamError({
        currentSource: activeSource,
        errorSource: staleSource,
        isTerminal: false,
        readyState: staleSource.readyState,
      })
    ).toBe(true);
  });

  it('ignores closed-source errors after the component clears the active stream reference', () => {
    expect(
      shouldIgnoreElectionStreamError({
        currentSource: null,
        errorSource: { readyState: 2 },
        isTerminal: false,
        readyState: 2,
      })
    ).toBe(true);
  });

  it('keeps real in-flight stream failures visible', () => {
    const activeSource = { readyState: 1 };

    expect(
      shouldIgnoreElectionStreamError({
        currentSource: activeSource,
        errorSource: activeSource,
        isTerminal: false,
        readyState: activeSource.readyState,
      })
    ).toBe(false);
  });
});
