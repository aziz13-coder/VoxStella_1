export function shouldApplyAstroClockRequest({
  requestId,
  latestRequestId,
  viewVersion,
  latestViewVersion,
}) {
  return requestId === latestRequestId && viewVersion === latestViewVersion;
}

let astroClockWarmState = null;

export function readAstroClockWarmState() {
  return astroClockWarmState;
}

export function writeAstroClockWarmState(nextState) {
  if (!nextState || typeof nextState !== 'object') {
    astroClockWarmState = null;
    return astroClockWarmState;
  }
  astroClockWarmState = {
    ...nextState,
    updatedAt: Date.now(),
  };
  return astroClockWarmState;
}

export function clearAstroClockWarmState() {
  astroClockWarmState = null;
}

function firstNonEmpty(...values) {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }
  return '';
}

export function resolveAstroClockTimezone(timezone, timezoneLabel) {
  const rawTimezone = firstNonEmpty(timezone);
  if (rawTimezone) {
    return rawTimezone;
  }
  const label = firstNonEmpty(timezoneLabel);
  if (!label) {
    return undefined;
  }
  const directMatch = label.match(/^([A-Za-z_]+\/[A-Za-z0-9_+\-]+(?:\/[A-Za-z0-9_+\-]+)*)/);
  if (directMatch?.[1]) {
    return directMatch[1];
  }
  const prefix = label.split(' (')[0]?.trim();
  return prefix || undefined;
}

function formatUtcOffsetLabel(timestamp, timezone) {
  if (!timezone || typeof Intl === 'undefined' || !Intl.DateTimeFormat) {
    return '';
  }
  try {
    const dt = new Date(timestamp || Date.now());
    if (!Number.isFinite(dt.getTime())) {
      return '';
    }
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      timeZoneName: 'longOffset',
    }).formatToParts(dt);
    const rawOffset = parts.find((part) => part.type === 'timeZoneName')?.value || '';
    if (!rawOffset) {
      return '';
    }
    if (rawOffset === 'GMT') {
      return 'UTC+00:00';
    }
    const normalized = rawOffset.replace(/^GMT/, 'UTC');
    const match = normalized.match(/^UTC([+-])(\d{1,2})(?::?(\d{2}))?$/);
    if (!match) {
      return normalized;
    }
    const sign = match[1];
    const hh = String(match[2] || '0').padStart(2, '0');
    const mm = String(match[3] || '00').padStart(2, '0');
    return `UTC${sign}${hh}:${mm}`;
  } catch (_) {
    return '';
  }
}

export function formatAstroClockTimezoneLabel({
  timestamp,
  timezone,
  timezoneLabel,
} = {}) {
  const resolvedTimezone = resolveAstroClockTimezone(timezone, timezoneLabel);
  const fallbackLabel = firstNonEmpty(timezoneLabel, resolvedTimezone);
  if (!fallbackLabel) {
    return null;
  }
  const offsetLabel = formatUtcOffsetLabel(timestamp, resolvedTimezone || fallbackLabel);
  if (!offsetLabel) {
    return fallbackLabel;
  }
  if (fallbackLabel.includes(`(${offsetLabel})`)) {
    return fallbackLabel;
  }
  return `${resolvedTimezone || fallbackLabel} (${offsetLabel})`;
}

export function resolveManualSnapshotTarget({
  activeManualIso,
  dataTimestamp,
  dataLocation,
  manualLocation,
  timezone,
  timezoneLabel,
  fallbackIso,
}) {
  return {
    iso:
      firstNonEmpty(activeManualIso, dataTimestamp, fallbackIso) ||
      new Date().toISOString(),
    location:
      firstNonEmpty(dataLocation, manualLocation) || 'Greenwich, UK',
    timezone: resolveAstroClockTimezone(timezone, timezoneLabel),
  };
}
