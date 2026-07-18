import { resolveAstroClockTimezone } from './astroClockViewState.mjs';

const DEFAULT_LOCALE = 'en-GB';

function firstText(...values) {
  for (const value of values) {
    if (value == null) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return '';
}

function snapDashboard(snap) {
  return snap?.dashboard && typeof snap.dashboard === 'object' ? snap.dashboard : {};
}

function snapContext(snap) {
  return snap?.calculation_context && typeof snap.calculation_context === 'object'
    ? snap.calculation_context
    : {};
}

function validIntlTimezone(value) {
  const candidate = resolveAstroClockTimezone(undefined, firstText(value));
  if (!candidate || typeof Intl === 'undefined' || !Intl.DateTimeFormat) return '';
  try {
    new Intl.DateTimeFormat(DEFAULT_LOCALE, { timeZone: candidate }).format(new Date());
    return candidate;
  } catch (_) {
    return '';
  }
}

function parseWallClock(value) {
  const match = String(value || '').trim().match(
    /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/,
  );
  if (!match) return null;
  const [, year, month, day, hour, minute] = match;
  const parsed = new Date(Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
  ));
  return Number.isFinite(parsed.getTime()) ? parsed : null;
}

function resolvedDisplayInstant(snap) {
  const dashboard = snapDashboard(snap);
  const context = snapContext(snap);
  const localDatetime = firstText(snap?.local_datetime, dashboard?.local_datetime);
  const effectiveDatetime = firstText(
    snap?.effective_datetime,
    context?.instant_utc,
    dashboard?.timestamp,
    snap?.datetime,
    snap?.timestamp,
  );
  const timezone = getSavedSnapTimezone(snap);
  const sourceValue = effectiveDatetime || localDatetime;
  if (sourceValue && timezone) {
    const parsed = new Date(sourceValue);
    if (Number.isFinite(parsed.getTime())) {
      return { parsed, timezone, localDatetime, effectiveDatetime };
    }
  }
  if (localDatetime) {
    const parsed = parseWallClock(localDatetime);
    if (parsed) {
      return { parsed, timezone: 'UTC', localDatetime, effectiveDatetime };
    }
  }
  if (effectiveDatetime) {
    const parsed = new Date(effectiveDatetime);
    if (Number.isFinite(parsed.getTime())) {
      return { parsed, timezone: 'UTC', localDatetime, effectiveDatetime };
    }
  }
  return { parsed: null, timezone: '', localDatetime, effectiveDatetime };
}

export function getSavedSnapTimezone(snap) {
  const dashboard = snapDashboard(snap);
  const context = snapContext(snap);
  return validIntlTimezone(firstText(
    snap?.timezone,
    context?.timezone,
    dashboard?.timezone,
    snap?.timezone_label,
    context?.timezone_label,
    dashboard?.timezone_label,
  ));
}

export function getSavedSnapTimezoneLabel(snap) {
  const dashboard = snapDashboard(snap);
  const context = snapContext(snap);
  return firstText(
    snap?.timezone_label,
    context?.timezone_label,
    dashboard?.timezone_label,
    snap?.timezone,
    context?.timezone,
    dashboard?.timezone,
  ) || 'UTC';
}

export function getSavedSnapDateTimeParts(snap, { locale = DEFAULT_LOCALE } = {}) {
  const resolved = resolvedDisplayInstant(snap);
  if (!resolved.parsed) {
    return { datePart: '', timePart: '', stamp: '', timezone: getSavedSnapTimezone(snap) };
  }
  try {
    const datePart = new Intl.DateTimeFormat(locale, {
      timeZone: resolved.timezone,
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(resolved.parsed);
    const timePart = new Intl.DateTimeFormat(locale, {
      timeZone: resolved.timezone,
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    }).format(resolved.parsed);
    return {
      datePart,
      timePart,
      stamp: `${datePart}, ${timePart}`,
      timezone: getSavedSnapTimezone(snap),
    };
  } catch (_) {
    return { datePart: '', timePart: '', stamp: '', timezone: getSavedSnapTimezone(snap) };
  }
}

export function formatSavedSnapDateTime(snap, options = {}) {
  return getSavedSnapDateTimeParts(snap, options).stamp || 'Time unavailable';
}

export function formatSavedSnapLabel(snap, {
  separator = ' | ',
  includeTimezone = false,
  locale = DEFAULT_LOCALE,
} = {}) {
  const parts = getSavedSnapDateTimeParts(snap, { locale });
  const dashboard = snapDashboard(snap);
  const label = firstText(snap?.label, snap?.id, 'Untitled snap') || 'Untitled snap';
  const location = firstText(snap?.location, dashboard?.location);
  return [
    label,
    parts.datePart,
    parts.timePart,
    includeTimezone ? getSavedSnapTimezoneLabel(snap) : '',
    location,
  ].filter(Boolean).join(separator);
}

export function isSavedSnapReviewRequired(snap) {
  const context = snapContext(snap);
  const coordinateProvenance = snap?.coordinate_provenance && typeof snap.coordinate_provenance === 'object'
    ? snap.coordinate_provenance
    : (context?.coordinate_provenance || {});
  return Boolean(
    context?.review_required
    || snap?.migration?.review_required
    || coordinateProvenance?.review_required,
  );
}

export function isSavedSnapSuperseded(snap) {
  return Boolean(String(snap?.superseded_by || '').trim());
}

export function isSavedSnapCalculationEligible(snap) {
  return Boolean(
    snap
    && !isSavedSnapReviewRequired(snap)
    && !isSavedSnapSuperseded(snap),
  );
}

export function getSavedSnapIneligibilityLabel(snap) {
  if (isSavedSnapSuperseded(snap)) return 'superseded — use corrected copy';
  if (isSavedSnapReviewRequired(snap)) return 'needs context review';
  return '';
}

export function getSavedSnapReviewMessages(snap) {
  const context = snapContext(snap);
  const coordinateProvenance = snap?.coordinate_provenance && typeof snap.coordinate_provenance === 'object'
    ? snap.coordinate_provenance
    : (context?.coordinate_provenance || {});
  const timeProvenance = context?.time_provenance && typeof context.time_provenance === 'object'
    ? context.time_provenance
    : {};
  const messages = [];
  if (timeProvenance?.ambiguous) {
    messages.push('Saved time interpretation needs review.');
  }
  if (coordinateProvenance?.review_required) {
    messages.push('Saved location or coordinates need review.');
  }
  if (Array.isArray(context?.conflicts) && context.conflicts.length > 0) {
    messages.push('Conflicting saved context was preserved for review.');
  }
  if ((context?.review_required || snap?.migration?.review_required) && messages.length === 0) {
    messages.push('Saved chart context needs review after migration.');
  }
  if (snap?.duplicate_group) {
    messages.push('A possible duplicate group was preserved; no saved chart was deleted.');
  }
  return [...new Set(messages)];
}
