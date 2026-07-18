import React, { useEffect, useMemo, useState } from 'react';
import { MapPin, Plus, Save, ShieldCheck, Trash2 } from 'lucide-react';
import { AstroClockAPI } from './api.mjs';
import {
  formatSavedSnapLabel,
  getSavedSnapIneligibilityLabel,
  getSavedSnapDateTimeParts,
  isSavedSnapCalculationEligible,
} from './savedSnapViewModel.mjs';

const PAPER = 'bg-white';
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };
const monoStyle = {
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace',
};

const SOURCE_STATUS_OPTIONS = [
  { value: 'unknown', label: 'Unknown' },
  { value: 'approximate', label: 'Approximate' },
  { value: 'rectified_candidate', label: 'Rectified candidate' },
  { value: 'certificate', label: 'Certificate' },
  { value: 'family_exact', label: 'Family exact' },
  { value: 'certified', label: 'Certified' },
];

const PRECISION_OPTIONS = [
  { value: '1', label: 'Exact' },
  { value: '2', label: 'Minutes' },
  { value: '3', label: 'Hours' },
  { value: '4', label: 'Days' },
  { value: '5', label: 'Weeks' },
  { value: '6', label: 'Months' },
  { value: '0', label: 'Skip' },
];

const INSTRUMENT_OPTIONS = [
  { id: 'transit', label: 'T: Transits', defaultWeight: '1' },
  { id: 'direction_reverse', label: 'Dr-ArcSun=YearTrop', defaultWeight: '1' },
  { id: 'profection_reverse', label: 'DR-30=YearTrop', defaultWeight: '1' },
  { id: 'primary_progression', label: 'P1 primary progression', defaultWeight: '1' },
  { id: 'secondary_progression_local', label: 'P2 local secondary', defaultWeight: '1' },
  { id: 'secondary_progression_natal', label: 'P2 natal secondary', defaultWeight: '1' },
  { id: 'tertiary_progression', label: 'P3 tertiary progression', defaultWeight: '1' },
  { id: 'minor_progression', label: 'PM minor progression', defaultWeight: '1' },
];

const STATUS_META = {
  certified_source: {
    label: 'Certified Source',
    tone: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    badge: 'bg-emerald-600 text-white',
  },
  rectified_candidate: {
    label: 'Likely Rectified Candidate',
    tone: 'border-sky-200 bg-sky-50 text-sky-900',
    badge: 'bg-sky-600 text-white',
  },
  unresolved_rectification: {
    label: 'Weak / Unresolved',
    tone: 'border-amber-200 bg-amber-50 text-amber-900',
    badge: 'bg-amber-500 text-white',
  },
  insufficient_data: {
    label: 'Insufficient Data',
    tone: 'border-zinc-200 bg-zinc-50 text-zinc-800',
    badge: 'bg-zinc-700 text-white',
  },
};

let eventIdCounter = 0;

function nextEventId() {
  eventIdCounter += 1;
  return `event-${eventIdCounter}`;
}

function finiteNumberOrUndefined(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function isFiniteInput(value) {
  if (value == null || String(value).trim() === '') return false;
  return Number.isFinite(Number(value));
}

function firstPresent(...values) {
  for (const value of values) {
    if (value == null) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return undefined;
}

function snapDashboard(snap) {
  return snap?.dashboard && typeof snap.dashboard === 'object' ? snap.dashboard : {};
}

function snapCoordinates(snap) {
  const dashboard = snapDashboard(snap);
  return {
    latitude: finiteNumberOrUndefined(
      snap?.latitude ?? dashboard?.latitude ?? snap?.coordinates?.latitude ?? snap?.coordinates?.lat ?? snap?.chart_snapshot?.latitude,
    ),
    longitude: finiteNumberOrUndefined(
      snap?.longitude ?? dashboard?.longitude ?? snap?.coordinates?.longitude ?? snap?.coordinates?.lon ?? snap?.coordinates?.lng ?? snap?.chart_snapshot?.longitude,
    ),
  };
}

function getSnapMetaParts(snap) {
  const dashboard = snapDashboard(snap);
  const label = firstPresent(snap?.label, snap?.id, 'Untitled snap') || 'Untitled snap';
  const iso = firstPresent(snap?.effective_datetime, dashboard?.timestamp, snap?.datetime, snap?.timestamp);
  const location = firstPresent(snap?.location, dashboard?.location);
  const { datePart, timePart } = getSavedSnapDateTimeParts(snap);
  return { label, iso, location, datePart, timePart };
}

function formatSnapLabel(snap) {
  return formatSavedSnapLabel(snap);
}

function extractDate(value) {
  const text = firstPresent(value);
  if (!text) return '';
  const match = text.match(/^(\d{4}-\d{2}-\d{2})/);
  if (match) return match[1];
  try {
    return new Date(text).toISOString().slice(0, 10);
  } catch (_) {
    return '';
  }
}

function formatDateTime(value) {
  const text = firstPresent(value);
  if (!text) return '--';
  const match = text.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/);
  if (match) return `${match[1]} ${match[2]}`;
  try {
    const parsed = new Date(text);
    if (Number.isNaN(parsed.getTime())) return text;
    return `${parsed.toISOString().slice(0, 10)} ${parsed.toISOString().slice(11, 16)} UTC`;
  } catch (_) {
    return text;
  }
}

function formatNumber(value, digits = 1) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '--';
  return n.toFixed(digits);
}

function minutesFromTime(value) {
  const match = String(value || '').match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return null;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (!Number.isInteger(hours) || !Number.isInteger(minutes) || hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
    return null;
  }
  return hours * 60 + minutes;
}

function newEventRow() {
  return {
    id: nextEventId(),
    label: '',
    timestamp: '',
    location: '',
    latitude: '',
    longitude: '',
    timezone: '',
    precision: '1',
    theme: '',
    weight: '1',
    sourceNote: '',
  };
}

function buildCurrentSeed({ manualIso, manualLocation, timezone, latitude, longitude, chartSnapshot }) {
  const snapshot = chartSnapshot && typeof chartSnapshot === 'object' ? chartSnapshot : {};
  return {
    timestamp: firstPresent(manualIso, snapshot.timestamp),
    date: extractDate(firstPresent(manualIso, snapshot.timestamp)),
    location: firstPresent(manualLocation, snapshot.location),
    timezone: firstPresent(timezone, snapshot.timezone, snapshot.timezone_label),
    latitude: finiteNumberOrUndefined(latitude ?? snapshot.latitude),
    longitude: finiteNumberOrUndefined(longitude ?? snapshot.longitude),
  };
}

function buildSnapSeed(snap) {
  if (!snap) return null;
  const dashboard = snapDashboard(snap);
  const { latitude, longitude } = snapCoordinates(snap);
  const timestamp = firstPresent(snap?.effective_datetime, dashboard?.timestamp, snap?.datetime, snap?.timestamp);
  return {
    timestamp,
    date: extractDate(timestamp),
    location: firstPresent(snap?.location, dashboard?.location),
    timezone: firstPresent(snap?.timezone, dashboard?.timezone, snap?.timezone_label, dashboard?.timezone_label),
    latitude,
    longitude,
  };
}

function sanitizeUserFacingNote(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  if (/[A-Za-z]:\\|decompiled|research|source evidence|reference workflow|reference gui|proprietary/i.test(text)) {
    return 'Additional method notes are available for this calculation.';
  }
  return text;
}

function buildPayload({
  birthDate,
  birthLocation,
  birthLatitude,
  birthLongitude,
  birthTimezone,
  sourceTimeStatus,
  searchStart,
  searchEnd,
  houseSystem,
  orbDegrees,
  levelPercent,
  includeSeries,
  instruments,
  eventRows,
}) {
  return {
    birth: {
      date: birthDate,
      location: birthLocation || undefined,
      latitude: Number(birthLatitude),
      longitude: Number(birthLongitude),
      timezone: birthTimezone,
      source_time_status: sourceTimeStatus,
    },
    search: {
      start_time: searchStart,
      end_time: searchEnd,
    },
    house_system_code: houseSystem || 'R',
    orb_degrees: Number(orbDegrees || 1),
    level_percent: Number(levelPercent || 67),
    include_series: Boolean(includeSeries),
    instruments: instruments
      .filter((item) => item.enabled)
      .map((item) => ({ id: item.id, weight: Number(item.weight || 1) })),
    events: eventRows.map((event) => ({
      label: event.label.trim(),
      timestamp: event.timestamp.trim(),
      location: event.location.trim() || undefined,
      latitude: Number(event.latitude),
      longitude: Number(event.longitude),
      timezone: event.timezone.trim() || undefined,
      precision: Number(event.precision || 1),
      theme: event.theme.trim() || undefined,
      weight: Number(event.weight || 1),
      source_note: event.sourceNote.trim() || undefined,
    })),
  };
}

function compactCandidate(candidate, fallbackOffset) {
  if (!candidate || typeof candidate !== 'object') return {};
  return {
    rank: candidate.rank,
    timestamp: candidate.timestamp,
    favorable: finiteNumberOrUndefined(candidate.favorable),
    tense: finiteNumberOrUndefined(candidate.tense),
    strength: finiteNumberOrUndefined(candidate.strength),
    dominant_curve: candidate.dominant_curve || undefined,
    hit_count: candidate.hit_count,
    time_offset_minutes: Number.isFinite(Number(candidate.time_offset_minutes))
      ? Number(candidate.time_offset_minutes)
      : (Number.isFinite(Number(fallbackOffset)) ? Number(fallbackOffset) : undefined),
  };
}

function buildCertificationSnapLabel(candidate) {
  const displayTime = formatDateTime(candidate?.timestamp);
  return displayTime && displayTime !== '--'
    ? `Certification - ${displayTime}`
    : 'Certification Snap';
}

function buildCertificationSnapMetadata({
  certification,
  selectedCandidate,
  birthDate,
  birthLocation,
  birthLatitude,
  birthLongitude,
  birthTimezone,
  sourceTimeStatus,
  searchStart,
  searchEnd,
  selectedHouseSystem,
  bestOffset,
  result,
  qualityWarnings,
}) {
  const dataQuality = certification?.data_quality && typeof certification.data_quality === 'object'
    ? certification.data_quality
    : {};
  return {
    kind: 'birth_time_certification',
    status: certification?.status || 'insufficient_data',
    confidence: certification?.confidence || 'none',
    reason: sanitizeUserFacingNote(certification?.reason),
    selected_candidate: compactCandidate(selectedCandidate, bestOffset),
    data_quality: dataQuality,
    birth: {
      date: birthDate,
      location: birthLocation || undefined,
      latitude: finiteNumberOrUndefined(birthLatitude),
      longitude: finiteNumberOrUndefined(birthLongitude),
      timezone: birthTimezone || undefined,
      source_time_status: sourceTimeStatus || undefined,
    },
    search: {
      start_time: searchStart,
      end_time: searchEnd,
      house_system_code: selectedHouseSystem || 'R',
    },
    review: {
      matching_period_count: Array.isArray(result?.periods) ? result.periods.length : 0,
      candidate_count: Array.isArray(result?.top_candidates) ? result.top_candidates.length : 0,
      warnings: Array.isArray(qualityWarnings) ? qualityWarnings : [],
    },
  };
}

function validateForm({
  birthDate,
  birthLatitude,
  birthLongitude,
  birthTimezone,
  searchStart,
  searchEnd,
  instruments,
  eventRows,
}) {
  const errors = [];
  if (!birthDate) errors.push('Birth date is required.');
  if (!isFiniteInput(birthLatitude) || !isFiniteInput(birthLongitude)) {
    errors.push('Birth latitude and longitude are required.');
  }
  if (!String(birthTimezone || '').trim()) errors.push('Birth timezone is required.');
  if (!searchStart || !searchEnd) errors.push('Search start and end times are required.');

  const startMinutes = minutesFromTime(searchStart);
  const endMinutes = minutesFromTime(searchEnd);
  if (searchStart && startMinutes == null) errors.push('Search start time must use HH:MM.');
  if (searchEnd && endMinutes == null) errors.push('Search end time must use HH:MM.');
  if (startMinutes != null && endMinutes != null && endMinutes < startMinutes) {
    errors.push('Search end time cannot be before start time.');
  }
  if (startMinutes != null && endMinutes != null && (endMinutes - startMinutes) > 1439) {
    errors.push('Search range cannot exceed 24 hours.');
  }
  if (!eventRows.length) errors.push('At least one event is required.');
  eventRows.forEach((event, index) => {
    const label = event.label?.trim() || `Event ${index + 1}`;
    if (!event.timestamp?.trim()) errors.push(`${label}: event timestamp is required.`);
    if (!isFiniteInput(event.latitude) || !isFiniteInput(event.longitude)) {
      errors.push(`${label}: event latitude and longitude are required.`);
    }
    if (event.precision === '' || Number.isNaN(Number(event.precision))) {
      errors.push(`${label}: event precision is required.`);
    }
  });
  if (!instruments.some((item) => item.enabled)) {
    errors.push('At least one instrument is required.');
  }
  return errors;
}

function buildQualityWarnings({ eventRows, sourceTimeStatus }) {
  const warnings = [];
  if (eventRows.length < 3) warnings.push('Add at least three independent events for stronger review quality.');
  const themes = new Set(eventRows.map((row) => String(row.theme || row.label || '').trim()).filter(Boolean));
  if (eventRows.length > 1 && themes.size <= 1) warnings.push('Use events from more than one life theme when available.');
  if (eventRows.length && eventRows.every((row) => Number(row.precision) >= 6)) {
    warnings.push('All events are month-level precision; the review may be weak.');
  }
  if (eventRows.some((row) => !isFiniteInput(row.latitude) || !isFiniteInput(row.longitude))) {
    warnings.push('Each event needs latitude and longitude for a scan.');
  }
  if (sourceTimeStatus === 'certified' || sourceTimeStatus === 'certificate') {
    warnings.push('An externally sourced birth time can already be treated as source-backed; rectification is optional.');
  }
  return warnings;
}

function candidateOffset(candidate, seedTimestamp) {
  if (Number.isFinite(Number(candidate?.time_offset_minutes))) {
    return Number(candidate.time_offset_minutes);
  }
  if (!candidate?.timestamp || !seedTimestamp) return null;
  const left = new Date(candidate.timestamp);
  const right = new Date(seedTimestamp);
  if (Number.isNaN(left.getTime()) || Number.isNaN(right.getTime())) return null;
  return Math.round((left.getTime() - right.getTime()) / 60000);
}

function Field({ label, children }) {
  return (
    <label className="block text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500" style={monoStyle}>
      <span>{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

function textInputClass() {
  return 'w-full rounded-none border-0 border-b border-zinc-200 bg-transparent px-0 py-1.5 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-300 focus:border-sky-700';
}

function selectClass() {
  return 'w-full rounded-none border-0 border-b border-zinc-200 bg-transparent px-0 py-1.5 text-sm text-zinc-900 outline-none transition focus:border-sky-700';
}

function Kicker({ children, className = 'text-zinc-500' }) {
  return (
    <div className={`text-[10px] font-semibold uppercase tracking-[0.24em] ${className}`} style={monoStyle}>
      {children}
    </div>
  );
}

function ResultMetric({ label, value }) {
  return (
    <div className="min-w-0 border-t border-zinc-200 pt-3">
      <Kicker className="text-zinc-400">{label}</Kicker>
      <div className="mt-1 truncate text-lg text-zinc-950" style={serifStyle}>{value}</div>
    </div>
  );
}

function MiniHistogram({ series }) {
  const rows = Array.isArray(series) ? series.slice(0, 96) : [];
  if (!rows.length) {
    return (
      <div className="border-y border-dashed border-zinc-200 py-4 text-sm text-zinc-500">
        Full series is not included for this result.
      </div>
    );
  }
  return (
    <div className="border-y border-zinc-200 py-3" aria-label="Certification histogram">
      <div className="mb-2 flex items-center justify-between gap-3 text-[11px] text-zinc-500">
        <span>Favorable</span>
        <span>Tense</span>
      </div>
      <div className="flex h-28 items-end gap-[2px] overflow-hidden">
        {rows.map((row, index) => {
          const favorable = Math.max(0, Math.min(100, Number(row?.favorable) || 0));
          const tense = Math.max(0, Math.min(100, Number(row?.tense) || 0));
          return (
            <div key={`${row?.timestamp || index}`} className="flex min-w-[3px] flex-1 items-end gap-[1px]">
              <div className="w-1/2 rounded-t bg-emerald-500/70" style={{ height: `${Math.max(2, favorable)}%` }} />
              <div className="w-1/2 rounded-t bg-amber-500/70" style={{ height: `${Math.max(2, tense)}%` }} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function BirthCertificationModal({
  open = true,
  onClose,
  manualIso,
  manualLocation,
  timezone,
  latitude,
  longitude,
  houseSystem = 'R',
  chartSnapshot = null,
  snaps = [],
  activeSnapId = '',
  loadingSnaps = false,
  snapsLoaded = true,
  onRefreshSnaps,
}) {
  const snapOptions = useMemo(() => (Array.isArray(snaps) ? snaps : []).filter((snap) => snap?.id), [snaps]);
  const eligibleSnapOptions = useMemo(
    () => snapOptions.filter((snap) => isSavedSnapCalculationEligible(snap)),
    [snapOptions],
  );
  const [chartSource, setChartSource] = useState('current');
  const [selectedSnapId, setSelectedSnapId] = useState(activeSnapId || '');
  const selectedSnap = useMemo(
    () => eligibleSnapOptions.find((snap) => String(snap?.id || '') === String(selectedSnapId || '')) || null,
    [eligibleSnapOptions, selectedSnapId],
  );

  const currentSeed = useMemo(
    () => buildCurrentSeed({ manualIso, manualLocation, timezone, latitude, longitude, chartSnapshot }),
    [manualIso, manualLocation, timezone, latitude, longitude, chartSnapshot],
  );
  const snapSeed = useMemo(() => buildSnapSeed(selectedSnap), [selectedSnap]);
  const activeSeed = chartSource === 'snap' && snapSeed ? snapSeed : currentSeed;
  const activeSeedKey = JSON.stringify(activeSeed);

  const [birthDate, setBirthDate] = useState(activeSeed.date || '');
  const [birthLocation, setBirthLocation] = useState(activeSeed.location || '');
  const [birthLatitude, setBirthLatitude] = useState(activeSeed.latitude ?? '');
  const [birthLongitude, setBirthLongitude] = useState(activeSeed.longitude ?? '');
  const [birthTimezone, setBirthTimezone] = useState(activeSeed.timezone || '');
  const [sourceTimeStatus, setSourceTimeStatus] = useState('unknown');
  const [searchStart, setSearchStart] = useState('00:00');
  const [searchEnd, setSearchEnd] = useState('23:59');
  const [selectedHouseSystem, setSelectedHouseSystem] = useState(houseSystem || 'R');
  const [orbDegrees, setOrbDegrees] = useState('1');
  const [levelPercent, setLevelPercent] = useState('67');
  const [includeSeries, setIncludeSeries] = useState(true);
  const [eventRows, setEventRows] = useState(() => [newEventRow()]);
  const [eventLocationResolvingId, setEventLocationResolvingId] = useState('');
  const [eventLocationMessages, setEventLocationMessages] = useState({});
  const [instruments, setInstruments] = useState(() => INSTRUMENT_OPTIONS.map((item) => ({
    id: item.id,
    label: item.label,
    enabled: true,
    weight: item.defaultWeight,
  })));
  const [validationErrors, setValidationErrors] = useState([]);
  const [backendError, setBackendError] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [snapSaveState, setSnapSaveState] = useState({ loading: false, error: '', success: '' });
  const [snapSeedConfirmed, setSnapSeedConfirmed] = useState(false);

  useEffect(() => {
    if (!open) return;
    setBirthDate(activeSeed.date || '');
    setBirthLocation(activeSeed.location || '');
    setBirthLatitude(activeSeed.latitude ?? '');
    setBirthLongitude(activeSeed.longitude ?? '');
    setBirthTimezone(activeSeed.timezone || '');
    setSelectedHouseSystem(houseSystem || 'R');
  }, [activeSeedKey, houseSystem, open]);

  useEffect(() => {
    if (!activeSnapId) return;
    const activeSnap = snapOptions.find(
      (snap) => String(snap?.id || '') === String(activeSnapId),
    );
    if (!activeSnap) return;
    if (!isSavedSnapCalculationEligible(activeSnap)) {
      setSelectedSnapId('');
      setChartSource('current');
      return;
    }
    setSelectedSnapId(String(activeSnapId));
  }, [activeSnapId, snapOptions]);

  useEffect(() => {
    setSnapSeedConfirmed(false);
  }, [chartSource, selectedSnapId]);

  useEffect(() => {
    if (chartSource === 'snap' && !selectedSnap && eligibleSnapOptions.length) {
      setSelectedSnapId(String(eligibleSnapOptions[0].id || ''));
    }
    if (chartSource === 'snap' && !selectedSnap && !eligibleSnapOptions.length) {
      setSelectedSnapId('');
      setChartSource('current');
    }
  }, [chartSource, eligibleSnapOptions, selectedSnap]);

  useEffect(() => {
    if (typeof onRefreshSnaps !== 'function') return;
    if (snapsLoaded && snapOptions.length) return;
    onRefreshSnaps({ silent: true });
  }, [onRefreshSnaps, snapsLoaded, snapOptions.length]);

  if (!open) return null;

  const qualityWarnings = buildQualityWarnings({ eventRows, sourceTimeStatus });
  const certification = result?.certification || {};
  const topCandidates = Array.isArray(result?.top_candidates) ? result.top_candidates : [];
  const periods = Array.isArray(result?.periods) ? result.periods : [];
  const series = Array.isArray(result?.series) ? result.series : [];
  const statusMeta = STATUS_META[certification.status] || STATUS_META.insufficient_data;
  const bestCandidate = certification.candidate || topCandidates[0] || null;
  const bestOffset = candidateOffset(bestCandidate, activeSeed.timestamp);
  const dataQuality = certification.data_quality || {};

  const updateEvent = (id, patch) => {
    setEventRows((rows) => rows.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  };

  const resolveEventLocation = async (eventRow, index) => {
    const query = String(eventRow?.location || '').trim();
    const label = eventRow?.label?.trim() || `Event ${index + 1}`;
    if (!query) {
      setEventLocationMessages((messages) => ({
        ...messages,
        [eventRow.id]: { kind: 'error', text: `${label}: enter an event location first.` },
      }));
      return;
    }

    setEventLocationResolvingId(eventRow.id);
    setEventLocationMessages((messages) => ({
      ...messages,
      [eventRow.id]: { kind: 'info', text: 'Resolving event location...' },
    }));

    try {
      const response = await AstroClockAPI.resolveTimezone(query);
      if (!response?.success || !isFiniteInput(response.latitude) || !isFiniteInput(response.longitude)) {
        throw new Error(response?.error || 'Unable to resolve event location.');
      }
      const resolvedLocation = firstPresent(response.location, response.location_name, query) || query;
      const resolvedTimezone = firstPresent(response.timezone, response.timezone_name, eventRow.timezone);
      updateEvent(eventRow.id, {
        location: resolvedLocation,
        latitude: String(response.latitude),
        longitude: String(response.longitude),
        ...(resolvedTimezone ? { timezone: resolvedTimezone } : {}),
      });
      setEventLocationMessages((messages) => ({
        ...messages,
        [eventRow.id]: { kind: 'success', text: `Resolved: ${resolvedLocation}` },
      }));
    } catch (error) {
      setEventLocationMessages((messages) => ({
        ...messages,
        [eventRow.id]: { kind: 'error', text: String(error?.message || 'Unable to resolve event location.') },
      }));
    } finally {
      setEventLocationResolvingId((current) => (current === eventRow.id ? '' : current));
    }
  };

  const removeEvent = (id) => {
    setEventRows((rows) => (rows.length > 1 ? rows.filter((row) => row.id !== id) : rows));
    setEventLocationMessages((messages) => {
      if (!messages[id]) return messages;
      const next = { ...messages };
      delete next[id];
      return next;
    });
  };

  const runCertification = async () => {
    const errors = validateForm({
      birthDate,
      birthLatitude,
      birthLongitude,
      birthTimezone,
      searchStart,
      searchEnd,
      instruments,
      eventRows,
    });
    if (chartSource === 'snap' && selectedSnap && !snapSeedConfirmed) {
      errors.push(
        'Confirm that you reviewed the saved chart date, timezone, place, and coordinates before running Certification.',
      );
    }
    setValidationErrors(errors);
    setBackendError('');
    setSnapSaveState({ loading: false, error: '', success: '' });
    if (errors.length) return;

    const payload = {
      ...buildPayload({
      birthDate,
      birthLocation,
      birthLatitude,
      birthLongitude,
      birthTimezone,
      sourceTimeStatus,
      searchStart,
      searchEnd,
      houseSystem: selectedHouseSystem,
      orbDegrees,
      levelPercent,
      includeSeries,
      instruments,
      eventRows,
      }),
      ...(chartSource === 'snap' && selectedSnap?.id
        ? { snap_id: String(selectedSnap.id) }
        : {}),
    };

    try {
      setLoading(true);
      const response = await AstroClockAPI.rectifyBirthTime(payload);
      if (response?.success) {
        setResult(response.data || {});
      } else {
        setResult(null);
        setBackendError(String(response?.error || response?.detail || 'Certification review failed.'));
      }
    } catch (error) {
      setResult(null);
      setBackendError(String(error?.message || 'Certification review failed.'));
    } finally {
      setLoading(false);
    }
  };

  const saveCertificationSnap = async () => {
    if (!bestCandidate?.timestamp) {
      setSnapSaveState({ loading: false, error: 'No candidate time is available to save.', success: '' });
      return;
    }
    const certificationPayload = buildCertificationSnapMetadata({
      certification,
      selectedCandidate: bestCandidate,
      birthDate,
      birthLocation,
      birthLatitude,
      birthLongitude,
      birthTimezone,
      sourceTimeStatus,
      searchStart,
      searchEnd,
      selectedHouseSystem,
      bestOffset,
      result,
      qualityWarnings,
    });
    try {
      setSnapSaveState({ loading: true, error: '', success: '' });
      const response = await AstroClockAPI.createSnap({
        label: buildCertificationSnapLabel(bestCandidate),
        mode: 'manual',
        datetime: bestCandidate.timestamp,
        location: birthLocation || activeSeed.location,
        timezone: birthTimezone || activeSeed.timezone,
        latitude: finiteNumberOrUndefined(birthLatitude),
        longitude: finiteNumberOrUndefined(birthLongitude),
        houseSystem: selectedHouseSystem,
        certification: certificationPayload,
      });
      if (!response?.success) {
        throw new Error(response?.error || response?.detail || 'Unable to save Certification snap.');
      }
      if (typeof onRefreshSnaps === 'function') {
        await onRefreshSnaps({ silent: true });
      }
      setSnapSaveState({ loading: false, error: '', success: 'Certification snap saved.' });
    } catch (error) {
      setSnapSaveState({
        loading: false,
        error: String(error?.message || 'Unable to save Certification snap.'),
        success: '',
      });
    }
  };

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/35 p-3 backdrop-blur-[2px] sm:p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="birth-certification-title"
        className={`flex max-h-[94vh] w-full max-w-[1180px] flex-col overflow-hidden rounded-[28px] border border-zinc-200/80 ${PAPER} shadow-[0_28px_80px_rgba(20,14,33,0.22)]`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-zinc-200/80 px-5 py-4 sm:px-6">
          <div className="flex min-w-0 items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-sky-100 bg-sky-50 text-sky-700">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <Kicker className="text-sky-700">Astro Clock / Certification</Kicker>
              <h2 id="birth-certification-title" className="mt-1 text-xl font-normal text-zinc-950" style={serifStyle}>
                Birth Time Certification
              </h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-500">
                Review candidate birth times against dated life events. Certified status is shown only when the backend returns it.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 underline-offset-4 hover:text-zinc-950 hover:underline"
            aria-label="Close Birth Certification"
            style={monoStyle}
          >
            Close
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-5 sm:px-6">
          <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
            <div className="min-w-0 space-y-5">
              <div className="min-w-0 border-b border-zinc-200 pb-5">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-zinc-950">Birth Data</h3>
                  <select
                    value={chartSource}
                    onChange={(event) => setChartSource(event.target.value)}
                    className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[11px] font-medium text-zinc-700 shadow-sm"
                    aria-label="Birth chart source"
                  >
                    <option value="current">Current chart</option>
                    <option value="snap" disabled={!eligibleSnapOptions.length}>Saved snap</option>
                  </select>
                </div>

                {chartSource === 'snap' ? (
                  <div className="mb-3">
                    <label className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
                      Saved snap
                      <select
                        value={selectedSnapId}
                        onChange={(event) => setSelectedSnapId(event.target.value)}
                        className={`${selectClass()} mt-1`}
                        disabled={loadingSnaps || !eligibleSnapOptions.length}
                      >
                        <option value="">{loadingSnaps ? 'Loading snaps...' : 'Choose snap'}</option>
                        {snapOptions.map((snap) => (
                          <option
                            key={snap.id}
                            value={snap.id}
                            disabled={!isSavedSnapCalculationEligible(snap)}
                          >
                            {formatSnapLabel(snap)}
                            {getSavedSnapIneligibilityLabel(snap)
                              ? ` — ${getSavedSnapIneligibilityLabel(snap)}`
                              : ''}
                          </option>
                        ))}
                      </select>
                    </label>
                    {snapOptions.some((snap) => !isSavedSnapCalculationEligible(snap)) ? (
                      <p className="mt-2 font-serif text-[11px] italic leading-5 text-zinc-500">
                        Review-required and superseded saved charts are disabled. Use a corrected copy from Astro Clock.
                      </p>
                    ) : null}
                    {selectedSnap ? (
                      <label className="mt-3 flex items-start gap-2 rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-[11px] leading-5 text-sky-950">
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={snapSeedConfirmed}
                          onChange={(event) => setSnapSeedConfirmed(event.target.checked)}
                        />
                        <span>
                          I reviewed the saved chart’s date, IANA timezone, specific place, latitude, and longitude.
                        </span>
                      </label>
                    ) : null}
                  </div>
                ) : null}
                {chartSource !== 'snap' && snapOptions.some((snap) => !isSavedSnapCalculationEligible(snap)) ? (
                  <p className="mb-3 font-serif text-[11px] italic leading-5 text-zinc-500">
                    Review-required and superseded saved charts cannot seed certification. Use a corrected copy from Astro Clock.
                  </p>
                ) : null}

                <div className="grid min-w-0 gap-3 sm:grid-cols-2">
                  <Field label="Birth date">
                    <input aria-label="Birth date" type="date" value={birthDate} onChange={(event) => {
                      setBirthDate(event.target.value);
                      setSnapSeedConfirmed(false);
                    }} className={textInputClass()} />
                  </Field>
                  <Field label="Source time status">
                    <select aria-label="Source time status" value={sourceTimeStatus} onChange={(event) => setSourceTimeStatus(event.target.value)} className={selectClass()}>
                      {SOURCE_STATUS_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                    </select>
                  </Field>
                  <Field label="Birth location">
                    <input aria-label="Birth location" type="text" value={birthLocation} onChange={(event) => {
                      setBirthLocation(event.target.value);
                      setSnapSeedConfirmed(false);
                    }} className={textInputClass()} />
                  </Field>
                  <Field label="Birth timezone">
                    <input aria-label="Birth timezone" type="text" value={birthTimezone} onChange={(event) => {
                      setBirthTimezone(event.target.value);
                      setSnapSeedConfirmed(false);
                    }} className={textInputClass()} />
                  </Field>
                  <Field label="Birth latitude">
                    <input aria-label="Birth latitude" type="number" step="0.0001" value={birthLatitude} onChange={(event) => {
                      setBirthLatitude(event.target.value);
                      setSnapSeedConfirmed(false);
                    }} className={textInputClass()} />
                  </Field>
                  <Field label="Birth longitude">
                    <input aria-label="Birth longitude" type="number" step="0.0001" value={birthLongitude} onChange={(event) => {
                      setBirthLongitude(event.target.value);
                      setSnapSeedConfirmed(false);
                    }} className={textInputClass()} />
                  </Field>
                </div>
              </div>

              <div className="min-w-0 border-b border-zinc-200 pb-5">
                <h3 className="mb-3 text-sm font-semibold text-zinc-950">Search and Scoring</h3>
                <div className="grid min-w-0 gap-3 sm:grid-cols-2">
                  <Field label="Search start">
                    <input aria-label="Search start" type="time" value={searchStart} onChange={(event) => setSearchStart(event.target.value)} className={textInputClass()} />
                  </Field>
                  <Field label="Search end">
                    <input aria-label="Search end" type="time" value={searchEnd} onChange={(event) => setSearchEnd(event.target.value)} className={textInputClass()} />
                  </Field>
                  <Field label="House system">
                    <select aria-label="House system" value={selectedHouseSystem} onChange={(event) => setSelectedHouseSystem(event.target.value)} className={selectClass()}>
                      <option value="R">Regiomontanus</option>
                      <option value="P">Placidus</option>
                      <option value="E">Equal</option>
                      <option value="W">Whole Sign</option>
                      <option value="O">Porphyry</option>
                      <option value="C">Campanus</option>
                      <option value="K">Koch</option>
                      <option value="T">Topocentric</option>
                    </select>
                  </Field>
                  <Field label="Orb degrees">
                    <input aria-label="Orb degrees" type="number" min="0.1" max="5" step="0.1" value={orbDegrees} onChange={(event) => setOrbDegrees(event.target.value)} className={textInputClass()} />
                  </Field>
                  <Field label="Level threshold">
                    <input aria-label="Level threshold" type="number" min="1" max="100" step="1" value={levelPercent} onChange={(event) => setLevelPercent(event.target.value)} className={textInputClass()} />
                  </Field>
                  <label className="flex items-center gap-2 border-b border-zinc-200 py-2 text-sm text-zinc-700">
                    <input type="checkbox" checked={includeSeries} onChange={(event) => setIncludeSeries(event.target.checked)} className="h-4 w-4 accent-zinc-900" />
                    Include full series
                  </label>
                </div>

                <div className="mt-4 space-y-2">
                  <Kicker className="text-zinc-400">Instruments</Kicker>
                  {instruments.map((item) => (
                    <div key={item.id} className="flex items-center gap-3 border-t border-zinc-200 py-2">
                      <label className="flex min-w-0 flex-1 items-center gap-2 text-sm text-zinc-700">
                        <input
                          type="checkbox"
                          checked={item.enabled}
                          onChange={(event) => {
                            setInstruments((rows) => rows.map((row) => (row.id === item.id ? { ...row, enabled: event.target.checked } : row)));
                          }}
                          className="h-4 w-4 accent-zinc-900"
                        />
                        <span className="truncate">{item.label}</span>
                      </label>
                      <input
                        aria-label={`${item.label} weight`}
                        type="number"
                        step="0.1"
                        value={item.weight}
                        onChange={(event) => {
                          setInstruments((rows) => rows.map((row) => (row.id === item.id ? { ...row, weight: event.target.value } : row)));
                        }}
                        className="w-20 rounded-none border-0 border-b border-zinc-200 bg-transparent px-0 py-1 text-sm text-zinc-900 outline-none focus:border-sky-700"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {(validationErrors.length || qualityWarnings.length || backendError) ? (
                <div className="border-l-2 border-amber-400 bg-amber-50/80 py-3 pl-4 pr-3 text-sm text-amber-900">
                  <h3 className="mb-2 font-semibold">Warnings and Validation</h3>
                  <ul className="space-y-1">
                    {validationErrors.map((error) => <li key={error}>{error}</li>)}
                    {qualityWarnings.map((warning) => <li key={warning}>{warning}</li>)}
                    {backendError ? <li>{backendError}</li> : null}
                  </ul>
                </div>
              ) : null}
            </div>

            <div className="min-w-0 space-y-5">
              <div className="min-w-0 border-b border-zinc-200 pb-5">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-zinc-950">Life Events</h3>
                  <button
                    type="button"
                    onClick={() => setEventRows((rows) => [...rows, newEventRow()])}
                    className="inline-flex items-center gap-1 rounded-full border border-zinc-200 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-zinc-700 hover:bg-zinc-50"
                  >
                    <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                    Add Event
                  </button>
                </div>
                <div className="space-y-3">
                  {eventRows.map((event, index) => (
                    <div key={event.id} className="border-t border-zinc-200 pt-3">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <Kicker className="text-zinc-400">Event {index + 1}</Kicker>
                        <button
                          type="button"
                          onClick={() => removeEvent(event.id)}
                          disabled={eventRows.length <= 1}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-500 shadow-sm hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40"
                          aria-label={`Remove event ${index + 1}`}
                        >
                          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                        </button>
                      </div>
                      <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        <Field label="Event label">
                          <input aria-label="Event label" value={event.label} onChange={(e) => updateEvent(event.id, { label: e.target.value })} className={textInputClass()} />
                        </Field>
                        <Field label="Event timestamp">
                          <input aria-label="Event timestamp" value={event.timestamp} onChange={(e) => updateEvent(event.id, { timestamp: e.target.value })} placeholder="YYYY-MM-DDTHH:mm:ss+02:00" className={textInputClass()} />
                        </Field>
                        <Field label="Event precision">
                          <select aria-label="Event precision" value={event.precision} onChange={(e) => updateEvent(event.id, { precision: e.target.value })} className={selectClass()}>
                            {PRECISION_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                          </select>
                        </Field>
                        <div className="min-w-0 sm:col-span-2 xl:col-span-3">
                          <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                            <Field label="Event location">
                              <input aria-label="Event location" value={event.location} onChange={(e) => updateEvent(event.id, { location: e.target.value })} className={textInputClass()} />
                            </Field>
                            <button
                              type="button"
                              onClick={() => resolveEventLocation(event, index)}
                              disabled={eventLocationResolvingId === event.id}
                              aria-label={`Resolve Event ${index + 1} Location`}
                              className="inline-flex h-9 items-center justify-center gap-1 rounded-full border border-zinc-200 bg-white px-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-zinc-700 shadow-sm hover:bg-zinc-50 disabled:cursor-wait disabled:opacity-60"
                            >
                              <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                              {eventLocationResolvingId === event.id ? 'Resolving' : 'Resolve'}
                            </button>
                          </div>
                          {eventLocationMessages[event.id] ? (
                            <div
                              className={`mt-2 text-xs leading-5 ${
                                eventLocationMessages[event.id].kind === 'error'
                                  ? 'text-amber-700'
                                  : 'text-zinc-500'
                              }`}
                            >
                              {eventLocationMessages[event.id].text}
                            </div>
                          ) : null}
                        </div>
                        <Field label="Event latitude">
                          <input aria-label="Event latitude" type="number" step="0.0001" value={event.latitude} onChange={(e) => updateEvent(event.id, { latitude: e.target.value })} className={textInputClass()} />
                        </Field>
                        <Field label="Event longitude">
                          <input aria-label="Event longitude" type="number" step="0.0001" value={event.longitude} onChange={(e) => updateEvent(event.id, { longitude: e.target.value })} className={textInputClass()} />
                        </Field>
                        <Field label="Event timezone">
                          <input aria-label="Event timezone" value={event.timezone} onChange={(e) => updateEvent(event.id, { timezone: e.target.value })} className={textInputClass()} />
                        </Field>
                        <Field label="Event theme">
                          <input aria-label="Event theme" value={event.theme} onChange={(e) => updateEvent(event.id, { theme: e.target.value })} className={textInputClass()} />
                        </Field>
                        <Field label="Event weight">
                          <input aria-label="Event weight" type="number" step="0.1" value={event.weight} onChange={(e) => updateEvent(event.id, { weight: e.target.value })} className={textInputClass()} />
                        </Field>
                        <div className="sm:col-span-2 xl:col-span-3">
                          <Field label="Source note">
                            <input aria-label="Source note" value={event.sourceNote} onChange={(e) => updateEvent(event.id, { sourceNote: e.target.value })} className={textInputClass()} />
                          </Field>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-full border border-zinc-200 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-600 hover:bg-zinc-50"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={runCertification}
                  disabled={loading}
                  className="rounded-full bg-zinc-900 px-5 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-300"
                >
                  {loading ? 'Running...' : 'Run Certification'}
                </button>
              </div>

              {loading ? (
                <div className="border-y border-zinc-200 py-4 text-sm text-zinc-500">
                  Running the certification review. Full-day scans can take a few minutes.
                </div>
              ) : null}

              {result ? (
                <div className="min-w-0 border-t border-zinc-200 pt-5">
                  <div className={`border-l-2 py-3 pl-4 pr-3 ${statusMeta.tone}`}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <Kicker className="opacity-70">Certification status</Kicker>
                        <h3 className="mt-1 text-xl font-normal" style={serifStyle}>{statusMeta.label}</h3>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ${statusMeta.badge}`}>
                          {certification.confidence || 'none'}
                        </span>
                        {bestCandidate?.timestamp ? (
                          <button
                            type="button"
                            onClick={saveCertificationSnap}
                            disabled={snapSaveState.loading}
                            className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-zinc-800 shadow-sm hover:bg-zinc-50 disabled:cursor-wait disabled:opacity-60"
                          >
                            <Save className="h-3.5 w-3.5" aria-hidden="true" />
                            {snapSaveState.loading ? 'Saving...' : 'Save Certification Snap'}
                          </button>
                        ) : null}
                      </div>
                    </div>
                    {certification.reason ? <p className="mt-3 text-sm leading-6">{sanitizeUserFacingNote(certification.reason)}</p> : null}
                    {snapSaveState.success ? (
                      <div className="mt-3 text-xs font-medium text-emerald-700">{snapSaveState.success}</div>
                    ) : null}
                    {snapSaveState.error ? (
                      <div className="mt-3 text-xs font-medium text-red-700">{snapSaveState.error}</div>
                    ) : null}
                  </div>

                  <div className="mt-4 grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <ResultMetric label="Best time" value={bestCandidate?.timestamp ? formatDateTime(bestCandidate.timestamp) : '--'} />
                    <ResultMetric label="Time offset" value={bestOffset == null ? '--' : `${bestOffset} min`} />
                    <ResultMetric label="Strength" value={formatNumber(bestCandidate?.strength, 1)} />
                    <ResultMetric label="Dominant curve" value={bestCandidate?.dominant_curve || '--'} />
                  </div>

                  <div className="mt-4 grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
                    <div>
                      <h4 className="mb-2 text-sm font-semibold text-zinc-950">Curve Overview</h4>
                      <MiniHistogram series={series} />
                    </div>
                    <div>
                      <h4 className="mb-2 text-sm font-semibold text-zinc-950">Data Quality</h4>
                      <div className="grid gap-2 sm:grid-cols-3">
                        <ResultMetric label="Events" value={dataQuality.event_count ?? '--'} />
                        <ResultMetric label="Precise events" value={dataQuality.near_exact_event_count ?? '--'} />
                        <ResultMetric label="Themes" value={dataQuality.unique_theme_count ?? '--'} />
                      </div>
                      {result?.meta?.parity_note ? (
                        <div className="mt-3 border-t border-zinc-200 pt-3 text-xs leading-5 text-zinc-500">
                          {sanitizeUserFacingNote(result.meta.parity_note)}
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-5">
                    <h4 className="mb-2 text-sm font-semibold text-zinc-950">Candidate Results</h4>
                    <div className="overflow-x-auto border-y border-zinc-200 bg-white" aria-label="Candidate results">
                      <table className="min-w-full text-left text-sm">
                        <thead className="bg-zinc-50 text-[11px] uppercase tracking-[0.12em] text-zinc-500">
                          <tr>
                            <th className="px-3 py-2">Rank</th>
                            <th className="px-3 py-2">Time</th>
                            <th className="px-3 py-2">Strength</th>
                            <th className="px-3 py-2">Favorable</th>
                            <th className="px-3 py-2">Tense</th>
                            <th className="px-3 py-2">Hits</th>
                          </tr>
                        </thead>
                        <tbody>
                          {topCandidates.length ? topCandidates.map((row, index) => (
                            <tr key={`${row.timestamp || index}`} className="border-t border-zinc-100">
                              <td className="px-3 py-2">{row.rank ?? index + 1}</td>
                              <td className="px-3 py-2">{formatDateTime(row.timestamp)}</td>
                              <td className="px-3 py-2">{formatNumber(row.strength, 1)}</td>
                              <td className="px-3 py-2">{formatNumber(row.favorable, 1)}</td>
                              <td className="px-3 py-2">{formatNumber(row.tense, 1)}</td>
                              <td className="px-3 py-2">{row.hit_count ?? '--'}</td>
                            </tr>
                          )) : (
                            <tr>
                              <td className="px-3 py-4 text-zinc-500" colSpan={6}>No ranked candidates returned.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="mt-5">
                    <h4 className="mb-2 text-sm font-semibold text-zinc-950">Matching Periods</h4>
                    <div className="overflow-x-auto border-y border-zinc-200 bg-white">
                      <table className="min-w-full text-left text-sm">
                        <thead className="bg-zinc-50 text-[11px] uppercase tracking-[0.12em] text-zinc-500">
                          <tr>
                            <th className="px-3 py-2">Rank</th>
                            <th className="px-3 py-2">Start</th>
                            <th className="px-3 py-2">End</th>
                            <th className="px-3 py-2">Peak</th>
                            <th className="px-3 py-2">Curve</th>
                            <th className="px-3 py-2">Duration</th>
                          </tr>
                        </thead>
                        <tbody>
                          {periods.length ? periods.map((period, index) => (
                            <tr key={`${period.start || index}`} className="border-t border-zinc-100">
                              <td className="px-3 py-2">{period.rank ?? index + 1}</td>
                              <td className="px-3 py-2">{formatDateTime(period.start)}</td>
                              <td className="px-3 py-2">{formatDateTime(period.end)}</td>
                              <td className="px-3 py-2">{formatNumber(period.peak_strength, 1)}</td>
                              <td className="px-3 py-2">{period.dominant_curve || '--'}</td>
                              <td className="px-3 py-2">{period.duration_minutes ?? '--'} min</td>
                            </tr>
                          )) : (
                            <tr>
                              <td className="px-3 py-4 text-zinc-500" colSpan={6}>No matching periods crossed the threshold.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              ) : !loading ? (
                <div className="border-y border-dashed border-zinc-200 py-4 text-sm text-zinc-500">
                  Enter birth data and at least one dated event, then run Certification to review candidate times.
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
