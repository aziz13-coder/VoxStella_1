export function shouldIgnoreElectionStreamError({ currentSource, errorSource, isTerminal, readyState }) {
  if (isTerminal) return true;
  if (currentSource && errorSource && currentSource !== errorSource) return true;

  const closedState =
    (typeof EventSource !== 'undefined' && Number.isFinite(EventSource.CLOSED))
      ? EventSource.CLOSED
      : 2;

  if (!currentSource && readyState === closedState) return true;
  return false;
}
