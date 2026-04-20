function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function pollAsyncSession({
  fetchProgress,
  onProgress,
  shouldContinue,
  delayMs = 500,
  timeoutMs = 120000,
  timeoutMessage = 'Timed out waiting for task to finish',
  cancelMessage = 'Task cancelled',
  shouldResolve = (progress) => Boolean(progress?.ready),
  shouldReject = (progress) => Boolean(progress?.failed),
  buildErrorMessage = (progress) => progress?.error || progress?.message || 'Task failed',
}) {
  if (typeof fetchProgress !== 'function') {
    throw new Error('fetchProgress is required');
  }

  const emitProgress = typeof onProgress === 'function' ? onProgress : () => {};
  const canContinue = typeof shouldContinue === 'function' ? shouldContinue : () => true;
  const deadline = Date.now() + timeoutMs;

  while (canContinue()) {
    const remainingMs = deadline - Date.now();
    if (remainingMs <= 0) {
      throw new Error('Timed out waiting for research compile to finish');
    }

    const progress = await fetchProgress();
    emitProgress(progress);

    if (shouldReject(progress)) {
      throw new Error(buildErrorMessage(progress));
    }

    if (shouldResolve(progress)) {
      return progress;
    }

    const nextDelayMs = Math.min(delayMs, Math.max(0, deadline - Date.now()));
    if (nextDelayMs <= 0) {
      throw new Error(timeoutMessage);
    }

    await delay(nextDelayMs);
  }

  throw new Error(cancelMessage);
}

export async function pollResearchSession({
  fetchProgress,
  onProgress,
  shouldContinue,
  delayMs = 500,
  timeoutMs = 120000,
}) {
  return pollAsyncSession({
    fetchProgress,
    onProgress,
    shouldContinue,
    delayMs,
    timeoutMs,
    timeoutMessage: 'Timed out waiting for research compile to finish',
    cancelMessage: 'Research compile cancelled',
  });
}
