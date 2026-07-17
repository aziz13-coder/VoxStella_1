export const API_CONNECTIVITY_TIMEOUT_MS = 2000;
export const API_CONNECTIVITY_BOOT_GRACE_MS = 45000;
export const API_CONNECTIVITY_FAILURE_THRESHOLD = 3;

export function resolveApiStatusAfterPingFailure({
  currentStatus,
  startupDeadlineMs,
  failureCount = 1,
  failureThreshold = API_CONNECTIVITY_FAILURE_THRESHOLD,
  nowMs = Date.now(),
}) {
  if (
    currentStatus === 'checking' &&
    Number.isFinite(startupDeadlineMs) &&
    nowMs < startupDeadlineMs
  ) {
    return 'checking';
  }

  if (currentStatus === 'connected') {
    return 'offline';
  }

  const normalizedFailureCount = Number(failureCount);
  const normalizedThreshold = Math.max(1, Number(failureThreshold) || API_CONNECTIVITY_FAILURE_THRESHOLD);
  if (!Number.isFinite(normalizedFailureCount) || normalizedFailureCount < normalizedThreshold) {
    return 'checking';
  }

  return 'offline';
}
