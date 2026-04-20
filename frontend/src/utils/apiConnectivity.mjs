export const API_CONNECTIVITY_TIMEOUT_MS = 2000;
export const API_CONNECTIVITY_BOOT_GRACE_MS = 12000;

export function resolveApiStatusAfterPingFailure({
  currentStatus,
  startupDeadlineMs,
  nowMs = Date.now(),
}) {
  if (
    currentStatus === 'checking' &&
    Number.isFinite(startupDeadlineMs) &&
    nowMs < startupDeadlineMs
  ) {
    return 'checking';
  }

  return 'offline';
}
