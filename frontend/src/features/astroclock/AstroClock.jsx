import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import './forensicDossier.css';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, Polygon, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Ensure default marker icons load under Vite/Electron bundling
try {
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2x,
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
  });
} catch(_) {}
import SketchWheel from '../../components/wheel/SketchWheel';
import { AstroClockAPI } from './api.mjs';
import ReceptionsTile from './ReceptionsTile.jsx';
import MetricsTile from './MetricsTile.jsx';
import DegreeHitsTile from './DegreeHitsTile.jsx';
import AlmutenTile from './AlmutenTile.jsx';
import TraitProfileModal from './TraitProfileModal.jsx';
import SynastryModal from './SynastryModal.jsx';
import TransitsModal from './TransitsModal.jsx';
import ElectionModal from './ElectionModal.jsx';
import AstrocartographyModal from './AstrocartographyModal.jsx';
import ChineseAstrologyPage from './ChineseAstrologyPage.jsx';
import BirthCertificationModal from './BirthCertificationModal.jsx';
import { transformDashboard, degString, aspectSymbol } from './transform.mjs';
import { buildSolarConditionEntries } from './solarConditions.mjs';
import {
  formatDispositorSummary,
  formatDispositorTooltip,
  normalizeDispositorState,
  shouldRenderDispositorSummary,
} from './dispositorViewModel.mjs';
import AspectAnalysisModal from './AspectAnalysisModal.jsx';
import CompassTile from './CompassTile.jsx';
import AsteroidsTile from './AsteroidsTile.jsx';
import NamePromptModal from './NamePromptModal.jsx';
import PremiumOfferModal from './PremiumOfferModal.jsx';
import {
  cleanForensicDisplayText,
  deriveForensicReplayAxes,
  forensicFindingMatchesAxis,
  formatForensicDisplayLabel,
  getForensicReplayTailoring,
} from './forensicReplayAxes.mjs';
import { formatForensicAspectLabels } from './forensicAspectSummary.mjs';
import { buildAbductionCueReportLines, buildAbductionCueSummary } from './forensicAbductionCues.mjs';
import {
  buildProcessedAbductionBearings,
  formatAbductionBearingRoleLabel,
  getAbductionLegendEntries,
  getAbductionRoleStyle,
  normalizeCoordinateInput,
} from './forensicAbductionMap.mjs';
import {
  buildRelationshipDisplayRows,
  collectRelationshipAspectContacts,
  scoreForensicRelationshipLink,
  summarizeForensicRelationshipLink,
} from './forensicRelationshipLink.mjs';
import { summarizeForensicSurvivalSignal } from './forensicSurvivalSignal.mjs';
import {
  formatAstroClockTimezoneLabel,
  readAstroClockWarmState,
  resolveAstroClockTimezone,
  resolveManualSnapshotTarget,
  shouldApplyAstroClockRequest,
  writeAstroClockWarmState,
} from './astroClockViewState.mjs';
import {
  formatSavedSnapDateTime,
  getSavedSnapIneligibilityLabel,
  getSavedSnapReviewMessages,
  getSavedSnapTimezone,
  getSavedSnapTimezoneLabel,
  isSavedSnapCalculationEligible,
  isSavedSnapReviewRequired,
} from './savedSnapViewModel.mjs';
import { shouldGatePremiumFeature } from '../../utils/premiumAccess.mjs';
import { ClipboardCopy } from 'lucide-react';

// Robust clipboard helper for Electron/packaged builds
async function safeCopyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (_) {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      ta.style.pointerEvents = 'none';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch (_) {
      return false;
    }
  }
}

function printReportHtmlInBrowser(html) {
  return new Promise((resolve) => {
    if (typeof document === 'undefined' || !document.body) {
      resolve(false);
      return;
    }
    const frame = document.createElement('iframe');
    frame.setAttribute('sandbox', 'allow-modals allow-same-origin');
    frame.setAttribute('title', 'Report print preview');
    frame.style.position = 'fixed';
    frame.style.width = '1px';
    frame.style.height = '1px';
    frame.style.opacity = '0';
    frame.style.pointerEvents = 'none';
    frame.style.border = '0';
    let settled = false;
    const finish = (printed) => {
      if (settled) return;
      settled = true;
      resolve(printed);
      setTimeout(() => {
        try { frame.remove(); } catch (_) {}
      }, printed ? 1000 : 0);
    };
    const loadTimeout = setTimeout(() => finish(false), 5000);
    frame.addEventListener('load', () => {
      clearTimeout(loadTimeout);
      if (settled) return;
      try {
        const printWindow = frame.contentWindow;
        if (!printWindow || typeof printWindow.print !== 'function') {
          finish(false);
          return;
        }
        printWindow.focus?.();
        printWindow.print();
        finish(true);
      } catch (_) {
        finish(false);
      }
    }, { once: true });
    frame.srcdoc = String(html || '');
    document.body.appendChild(frame);
  });
}

function getActionErrorMessage(error, fallbackMessage) {
  const rawMessage = typeof error?.message === 'string' ? error.message.trim() : '';
  return rawMessage || fallbackMessage;
}

function normalizeBackendStatus(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'checking' || normalized === 'starting' || normalized === 'loading') return 'checking';
  if (normalized === 'offline' || normalized === 'error' || normalized === 'failed') return 'offline';
  return 'connected';
}

function isTransientFetchError(error) {
  const rawMessage = typeof error?.message === 'string' ? error.message.trim() : '';
  return /failed to fetch|networkerror|network request failed|load failed/i.test(rawMessage);
}

function isAbortError(error) {
  return error?.name === 'AbortError' || /abort/i.test(String(error?.message || ''));
}

function getClockLoadErrorMessage(error, fallbackMessage, { backendStatus = 'connected' } = {}) {
  const rawMessage = typeof error?.message === 'string' ? error.message.trim() : '';
  if (isTransientFetchError(error)) {
    if (backendStatus !== 'offline') {
      return '';
    }
    return 'Astro Clock could not reach the local astrology engine. Try Refresh after it reconnects.';
  }
  if (/^Request timed out after \d+s$/i.test(rawMessage)) {
    return 'Astro Clock refresh took too long. Try Refresh again.';
  }
  return rawMessage || fallbackMessage;
}

const TIME_LOCALE = 'en-GB';
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };
const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };

const PlanetSymbols = {
  Sun: '☉',
  Moon: '☾',
  Mercury: '☿',
  Venus: '♀',
  Mars: '♂',
  Jupiter: '♃',
  Saturn: '♄',
  Uranus: '♅',
  Neptune: '♆',
  Pluto: '♇',
  'North Node': '☊',
};

function formatHM(iso) {
  if (!iso) return '';
  try {
    const dt = new Date(iso);
    return new Intl.DateTimeFormat(TIME_LOCALE, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      hourCycle: 'h23'
    }).format(dt);
  } catch { return ''; }
}

function formatControlDateLabel(rawDate) {
  if (!rawDate) return 'Waiting';
  try {
    return new Intl.DateTimeFormat(TIME_LOCALE, {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(new Date(`${rawDate}T12:00:00`));
  } catch {
    return rawDate;
  }
}

function extractUtcOffsetLabel(label) {
  if (!label) return '';
  const normalized = String(label).trim();
  const match = normalized.match(/\((UTC[+-]\d{2}:\d{2})\)$/);
  if (match?.[1]) {
    return match[1].replace('UTC', '');
  }
  if (/^UTC[+-]\d{2}:\d{2}$/.test(normalized)) {
    return normalized.replace('UTC', '');
  }
  return '';
}

function hourProgress(startIso, endIso) {
  try {
    const now = Date.now();
    const s = Date.parse(startIso);
    const e = Date.parse(endIso);
    if (!isFinite(s) || !isFinite(e) || e <= s) return 0;
    return Math.max(0, Math.min(100, ((now - s) / (e - s)) * 100));
  } catch { return 0; }
}

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';
const ASTRO_CLOCK_DEFAULT_LOCATION = 'Greenwich, UK';
const ASTRO_CLOCK_AUTO_LOCATION_STORAGE_KEY = 'vox_stella_astro_clock_auto_location';
const ASTRO_CLOCK_AUTO_CONTEXT_STORAGE_KEY = 'vox_stella_astro_clock_auto_context';
const tileEyebrowCls = 'text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400';
const utilityPillCls = 'rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500 hover:bg-zinc-50';
const subduedEmptyCls = 'rounded-2xl border border-zinc-200 bg-white px-3 py-3 text-sm text-zinc-500';
const savedSnapNoticeCls = 'rounded-xl border border-zinc-200 bg-zinc-50/80 px-3 py-2 text-zinc-600';
const savedSnapContextBadgeCls = 'rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-zinc-600';
const savedSnapRemarkCls = 'mt-1 text-[11px] italic leading-4 text-zinc-500';
const SNAP_CORRECTION_HOUSE_OPTIONS = [
  { code: 'R', label: 'Regiomontanus' },
  { code: 'P', label: 'Placidus' },
  { code: 'W', label: 'Whole Sign' },
  { code: 'K', label: 'Koch' },
  { code: 'E', label: 'Equal' },
];

const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
function signFromLon(lon=0){ const n=((Math.floor(lon/30))%12+12)%12; return signs[n]; }
function degreeTextFromLon(lon=0){ const d=Math.floor(lon%30); const m=Math.floor(((lon%1)*60)); return `${d}°${String(m).padStart(2,'0')}'`; }
function normalizeLocationText(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : '';
}
function finiteNumberOrUndefined(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : undefined;
}
function firstPresent(...values) {
  for (const value of values) {
    if (value == null) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return undefined;
}
function resolveIntlTimezone(value) {
  const candidate = resolveAstroClockTimezone(undefined, firstPresent(value));
  if (!candidate || typeof Intl === 'undefined' || !Intl.DateTimeFormat) return undefined;
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: candidate }).format(new Date());
    return candidate;
  } catch (_) {
    return undefined;
  }
}
function createSnapIdempotencyKey() {
  try {
    if (typeof globalThis.crypto?.randomUUID === 'function') {
      return `astro-clock-snap-${globalThis.crypto.randomUUID()}`;
    }
  } catch (_) {}
  return `astro-clock-snap-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}
function normalizeLocalDateTimeInput(value) {
  const match = String(value || '').trim().match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/,
  );
  if (!match) return '';
  const [, yearText, monthText, dayText, hourText, minuteText, secondText = '00'] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  if (
    month < 1 || month > 12
    || day < 1 || day > 31
    || hour < 0 || hour > 23
    || minute < 0 || minute > 59
    || second < 0 || second > 59
  ) {
    return '';
  }
  const check = new Date(Date.UTC(year, month - 1, day, hour, minute, second));
  if (
    check.getUTCFullYear() !== year
    || check.getUTCMonth() !== month - 1
    || check.getUTCDate() !== day
    || check.getUTCHours() !== hour
    || check.getUTCMinutes() !== minute
    || check.getUTCSeconds() !== second
  ) {
    return '';
  }
  return `${yearText}-${monthText}-${dayText}T${hourText}:${minuteText}`;
}
function hasExplicitUtcOffset(value) {
  return /(Z|[+-]\d{2}:\d{2})$/i.test(String(value || '').trim());
}
function normalizeUtcOffset(value) {
  const text = String(value ?? '').trim();
  if (!text) return '';
  if (/^Z$/i.test(text) || /^(?:UTC|GMT)$/i.test(text)) return '+00:00';
  const match = text.match(/(?:UTC|GMT)?\s*([+-])(\d{1,2})(?::?(\d{2}))?$/i);
  if (!match) return '';
  const hours = Number(match[2]);
  const minutes = Number(match[3] || '00');
  if (hours > 23 || minutes > 59) return '';
  return `${match[1]}${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}
function normalizeLocalTimeCandidate(candidate, index, fallbackLocalDateTime = '') {
  if (!candidate || typeof candidate !== 'object' || candidate.round_trip_matches === false) return null;
  const rawLocal = firstPresent(
    candidate.offset_aware_local_datetime,
    candidate.local_datetime,
    candidate.datetime,
    candidate.value,
  );
  const fallbackWall = normalizeLocalDateTimeInput(fallbackLocalDateTime);
  const candidateWall = normalizeLocalDateTimeInput(String(rawLocal || '').slice(0, 19));
  const wall = candidateWall || fallbackWall;
  let offsetAwareLocalDatetime = String(rawLocal || '').trim();
  const explicitOffset = normalizeUtcOffset(
    candidate.utc_offset
      ?? candidate.offset
      ?? candidate.offset_label
      ?? candidate.gmt_offset,
  );
  if (!hasExplicitUtcOffset(offsetAwareLocalDatetime) && wall && explicitOffset) {
    offsetAwareLocalDatetime = `${wall}:00${explicitOffset}`;
  }
  if (!hasExplicitUtcOffset(offsetAwareLocalDatetime)) return null;
  const offsetMatch = offsetAwareLocalDatetime.match(/(Z|[+-]\d{2}:\d{2})$/i);
  const offset = normalizeUtcOffset(offsetMatch?.[1]) || explicitOffset;
  let instantUtc = firstPresent(
    candidate.instant_utc,
    candidate.utc_datetime,
    candidate.datetime_utc,
    candidate.instant,
  ) || '';
  if (!instantUtc) {
    const parsed = new Date(offsetAwareLocalDatetime);
    if (Number.isFinite(parsed.getTime())) instantUtc = parsed.toISOString();
  }
  const fold = Number.isInteger(Number(candidate.fold)) ? Number(candidate.fold) : index;
  return {
    key: String(candidate.key || candidate.id || `${fold}:${offsetAwareLocalDatetime}`),
    fold,
    offset,
    instantUtc: String(instantUtc || ''),
    localDatetime: offsetAwareLocalDatetime,
  };
}
function collectLocalTimeCandidateRows(value, seen = new Set()) {
  if (!value || typeof value !== 'object' || seen.has(value)) return [];
  seen.add(value);
  const directKeys = [
    'candidates',
    'wall_time_candidates',
    'candidate_instants',
    'valid_candidates',
    'choices',
    'options',
  ];
  for (const key of directKeys) {
    if (Array.isArray(value[key])) return value[key];
  }
  for (const key of ['detail', 'data', 'error', 'context', 'time_resolution']) {
    const nested = collectLocalTimeCandidateRows(value[key], seen);
    if (nested.length) return nested;
  }
  return [];
}
function extractLocalTimeResolution(error, fallbackLocalDateTime = '') {
  const payload = error?.payload && typeof error.payload === 'object' ? error.payload : {};
  let serialized = '';
  try {
    serialized = JSON.stringify(payload);
  } catch (_) {}
  const statusText = [
    error?.message,
    error?.detail,
    payload?.code,
    payload?.error_code,
    payload?.wall_time_status,
    payload?.status,
    serialized,
  ].map((value) => String(value || '')).join(' ').toLowerCase();
  const rows = collectLocalTimeCandidateRows(payload);
  const candidates = rows
    .map((candidate, index) => normalizeLocalTimeCandidate(candidate, index, fallbackLocalDateTime))
    .filter(Boolean);
  const uniqueCandidates = Array.from(
    new Map(candidates.map((candidate) => [candidate.localDatetime, candidate])).values(),
  );
  if (
    /nonexistent|non-existent|spring.?forward|dst.?gap|wall_time_gap|nonexistent_gap/.test(statusText)
  ) {
    return {
      kind: 'nonexistent',
      candidates: [],
      message: 'This local time does not exist in the selected timezone because the clock moved forward. Choose another time.',
    };
  }
  if (
    uniqueCandidates.length > 1
    || /ambiguous|repeated|fall.?back|dst.?fold|ambiguous_fold/.test(statusText)
  ) {
    return {
      kind: 'ambiguous',
      candidates: uniqueCandidates,
      message: uniqueCandidates.length > 1
        ? 'This local time occurs twice. Choose the intended UTC offset, then try again.'
        : 'This local time occurs twice, but the server did not return usable offset choices.',
    };
  }
  return null;
}
function formatLocalTimeCandidateLabel(candidate) {
  const offsetLabel = candidate?.offset ? `UTC${candidate.offset}` : 'UTC offset';
  let instantLabel = String(candidate?.instantUtc || '').trim();
  const parsed = new Date(instantLabel);
  if (Number.isFinite(parsed.getTime())) {
    instantLabel = `${parsed.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
  }
  return [offsetLabel, instantLabel].filter(Boolean).join(' · ');
}
function LocalTimeAmbiguityChoice({
  resolution,
  selectedKey,
  onSelect,
  dark = false,
  ariaLabel = 'Choose the intended UTC offset',
}) {
  if (resolution?.kind !== 'ambiguous') return null;
  return (
    <div
      className={`rounded-xl border px-3 py-2.5 ${
        dark
          ? 'border-amber-700/70 bg-amber-950/30 text-amber-100'
          : 'border-amber-300 bg-amber-50 text-amber-950'
      }`}
      role="group"
      aria-label={ariaLabel}
    >
      <div className="text-[11px] font-semibold">{resolution.message}</div>
      {resolution.candidates.length > 0 ? (
        <div className="mt-2 grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label={ariaLabel}>
          {resolution.candidates.map((candidate) => (
            <label
              key={candidate.key}
              className={`flex cursor-pointer items-start gap-2 rounded-lg border px-2.5 py-2 text-[11px] ${
                dark ? 'border-amber-700/60 bg-zinc-950/50' : 'border-amber-200 bg-white'
              }`}
            >
              <input
                type="radio"
                name={ariaLabel}
                value={candidate.key}
                checked={selectedKey === candidate.key}
                onChange={() => onSelect(candidate.key)}
              />
              <span>
                <span className="block font-semibold">
                  {candidate.fold === 0 ? 'First occurrence' : 'Second occurrence'}
                </span>
                <span className={dark ? 'text-amber-200' : 'text-amber-800'}>
                  {formatLocalTimeCandidateLabel(candidate)}
                </span>
              </span>
            </label>
          ))}
        </div>
      ) : null}
    </div>
  );
}
function savedSnapCorrectionSeed(snap) {
  const dashboard = snap?.dashboard && typeof snap.dashboard === 'object' ? snap.dashboard : {};
  const context = snap?.calculation_context && typeof snap.calculation_context === 'object'
    ? snap.calculation_context
    : {};
  const resolvedContext = snap?.resolved_context && typeof snap.resolved_context === 'object'
    ? snap.resolved_context
    : {};
  const coordinateProvenance = snap?.coordinate_provenance && typeof snap.coordinate_provenance === 'object'
    ? snap.coordinate_provenance
    : (context?.coordinate_provenance || {});
  const localDatetime = firstPresent(
    snap?.local_datetime,
    context?.local_datetime,
    dashboard?.local_datetime,
  ) || '';
  const localMatch = String(localDatetime).match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})/);
  const keepCoordinates = coordinateProvenance?.persisted_with_chart !== false
    && coordinateProvenance?.review_required !== true;
  const latitude = keepCoordinates
    ? finiteNumberOrUndefined(
      snap?.latitude ?? resolvedContext?.latitude ?? dashboard?.latitude,
    )
    : undefined;
  const longitude = keepCoordinates
    ? finiteNumberOrUndefined(
      snap?.longitude ?? resolvedContext?.longitude ?? dashboard?.longitude,
    )
    : undefined;
  return {
    localDatetime: localMatch?.[1] || '',
    timezone: getSavedSnapTimezone(snap) || '',
    location: firstPresent(snap?.location, context?.location, dashboard?.location) || '',
    latitude: latitude == null ? '' : String(latitude),
    longitude: longitude == null ? '' : String(longitude),
    houseSystem: firstPresent(
      context?.house_system_code,
      dashboard?.house_system_code,
      snap?.house_system_code,
      'R',
    ) || 'R',
  };
}
function formatForensicTimestampParts(iso, timezone) {
  if (!iso || typeof iso !== 'string') {
    return { datePart: '', timePart: '' };
  }
  try {
    const parsed = new Date(iso);
    if (!Number.isFinite(parsed.getTime())) {
      return { datePart: '', timePart: '' };
    }
    const resolvedTimezone = resolveIntlTimezone(timezone);
    const timezoneOption = resolvedTimezone ? { timeZone: resolvedTimezone } : {};
    return {
      datePart: new Intl.DateTimeFormat('en-US', {
        ...timezoneOption,
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
      }).format(parsed),
      timePart: new Intl.DateTimeFormat('en-US', {
        ...timezoneOption,
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      }).format(parsed),
    };
  } catch (_) {
    return { datePart: '', timePart: '' };
  }
}
function readStoredAstroClockAutoLocation() {
  try {
    return normalizeLocationText(localStorage.getItem(ASTRO_CLOCK_AUTO_LOCATION_STORAGE_KEY));
  } catch (_) {
    return '';
  }
}
function readStoredAstroClockAutoContext() {
  try {
    const raw = localStorage.getItem(ASTRO_CLOCK_AUTO_CONTEXT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const location = normalizeLocationText(parsed?.location);
    const latitude = finiteNumberOrUndefined(parsed?.latitude);
    const longitude = finiteNumberOrUndefined(parsed?.longitude);
    if (!location || latitude == null || longitude == null) return null;
    return {
      location,
      timezone: normalizeLocationText(parsed?.timezone),
      timezone_label: normalizeLocationText(parsed?.timezone_label),
      latitude,
      longitude,
    };
  } catch (_) {
    return null;
  }
}
const SignGlyphs = {
  Aries: '♈︎',
  Taurus: '♉︎',
  Gemini: '♊︎',
  Cancer: '♋︎',
  Leo: '♌︎',
  Virgo: '♍︎',
  Libra: '♎︎',
  Scorpio: '♏︎',
  Sagittarius: '♐︎',
  Capricorn: '♑︎',
  Aquarius: '♒︎',
  Pisces: '♓︎',
};
const zodiacGlyphStyle = { fontFamily: '"Noto Sans Symbols 2","Segoe UI Symbol","Apple Symbols",serif' };
const SignRulers = {
  Aries: 'Mars',
  Taurus: 'Venus',
  Gemini: 'Mercury',
  Cancer: 'Moon',
  Leo: 'Sun',
  Virgo: 'Mercury',
  Libra: 'Venus',
  Scorpio: 'Mars',
  Sagittarius: 'Jupiter',
  Capricorn: 'Saturn',
  Aquarius: 'Saturn',
  Pisces: 'Jupiter',
};
const CHART_LENS_OPTIONS = [
  { id: 'traditional', label: 'Traditional' },
  { id: 'modern', label: '+ Modern' },
  { id: 'bodies', label: 'Bodies' },
];
const CHART_TRADITIONAL_BODIES = new Set(['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn']);
const CHART_MODERN_OUTERS = new Set(['Uranus','Neptune','Pluto']);
const CHART_BODY_PRIORITY = ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Uranus','Neptune','Pluto','North Node','South Node','Chiron'];

function normalizeLongitude(lon) {
  const numeric = Number(lon);
  if (!Number.isFinite(numeric)) return null;
  return ((numeric % 360) + 360) % 360;
}

function chartPointSummary(lon) {
  const normalized = normalizeLongitude(lon);
  if (normalized == null) return null;
  const sign = signFromLon(normalized);
  return {
    lon: normalized,
    sign,
    glyph: SignGlyphs[sign] || '',
    degreeText: degreeTextFromLon(normalized),
    ruler: SignRulers[sign] || '',
  };
}

function chartLensRank(name) {
  const index = CHART_BODY_PRIORITY.indexOf(name);
  return index === -1 ? CHART_BODY_PRIORITY.length + 1 : index;
}

function filterChartPlanetsByLens(planets, lens) {
  const rows = Array.isArray(planets) ? planets : [];
  return rows
    .filter((planet) => {
      const name = String(planet?.planet || '');
      if (!name) return false;
      if (lens === 'traditional') return CHART_TRADITIONAL_BODIES.has(name);
      if (lens === 'modern') return CHART_TRADITIONAL_BODIES.has(name) || CHART_MODERN_OUTERS.has(name);
      return true;
    })
    .slice()
    .sort((left, right) => {
      const rankDiff = chartLensRank(left?.planet) - chartLensRank(right?.planet);
      if (rankDiff !== 0) return rankDiff;
      return (normalizeLongitude(left?.longitude) ?? 999) - (normalizeLongitude(right?.longitude) ?? 999);
    });
}

function mapAspectNameToWheelType(name) {
  const normalized = String(name || '').trim().toLowerCase();
  if (normalized === 'conjunction') return 'conj';
  if (normalized === 'opposition') return 'opp';
  if (normalized === 'trine') return 'trine';
  if (normalized === 'square') return 'square';
  if (normalized === 'sextile') return 'sextile';
  return null;
}

function formatAspectOrb(orb) {
  const numeric = Math.abs(Number(orb));
  if (!Number.isFinite(numeric)) return '-';
  return `${numeric.toFixed(1)}°`;
}

function buildWheelAspectRows(rows, visibleIds) {
  const ids = visibleIds instanceof Set ? visibleIds : new Set();
  return (Array.isArray(rows) ? rows : []).flatMap((row) => {
    const type = mapAspectNameToWheelType(row?.aspect);
    const a = String(row?.planet1 || '').trim();
    const b = String(row?.planet2 || '').trim();
    if (!type || !a || !b || !ids.has(a) || !ids.has(b)) return [];
    const orb = Math.abs(Number(row?.orb));
    if (!Number.isFinite(orb)) return [];
    const maxOrb = Number(row?.max_orb ?? row?.allowed_orb);
    return [{
      a,
      b,
      type,
      orb,
      maxOrb: Number.isFinite(maxOrb) && maxOrb > 0 ? maxOrb : 8,
      label: row?.aspect || '',
      phase: row?.phase || '',
      symbol: row?.symbol || aspectSymbol(row?.aspect),
      orbText: row?.orb_text || formatAspectOrb(orb),
    }];
  });
}

function extractFortuneLot(lots) {
  const source = lots?.fortune || lots?.part_of_fortune || lots?.fortune_part || null;
  if (!source || typeof source !== 'object') return null;
  const lon = source.lon ?? source.longitude ?? null;
  const summary = chartPointSummary(lon);
  if (!summary) return null;
  return {
    ...summary,
    house: source.house ?? null,
    name: source.name || 'Fortune',
  };
}

function normalizeSectValue(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'diurnal' || normalized === 'day') return 'diurnal';
  if (normalized === 'nocturnal' || normalized === 'night') return 'nocturnal';
  return null;
}

function summarizeSectMeta(sect) {
  if (!sect || typeof sect !== 'object') return null;
  const normalized = normalizeSectValue(sect.chart_sect || sect.sect || sect.type || sect.status);
  if (!normalized) return null;
  const isNight = normalized === 'nocturnal';
  return {
    glyph: isNight ? '☽' : '☉',
    label: isNight ? 'Night' : 'Day',
    detail: sect.benefic_of_sect ? `Benefic: ${sect.benefic_of_sect}` : '',
  };
}

function solarConditionAccentTone(tone) {
  if (tone === 'cazimi') return 'text-amber-600';
  if (tone === 'combust') return 'text-rose-600';
  if (tone === 'under_beams') return 'text-sky-600';
  return 'text-zinc-700';
}

function formatSurvivabilityBandLabel(value){
  const raw = String(value || '').trim();
  if (!raw) return '';
  const labels = {
    release_favored: 'release-favored',
    risk_loaded_survival: 'risk-loaded survival',
    fatal_pressure_dominant: 'fatal-pressure dominant',
    nonfatal_tilt: 'non-fatal tilt',
    mixed_nonfatal: 'mixed / non-fatal',
  };
  return labels[raw] || raw.replace(/_/g, ' ');
}

function formatForensicSignedScore(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '-';
  const rounded = Math.round(number * 100) / 100;
  return `${rounded >= 0 ? '+' : ''}${rounded.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatForensicLocationLabel(value) {
  const raw = normalizeLocationText(value);
  if (!raw) return '';
  const letters = raw.replace(/[^A-Za-z]/g, '');
  if (!letters || letters !== letters.toLowerCase()) return raw;
  const minorWords = new Set(['and', 'at', 'by', 'de', 'del', 'el', 'in', 'of', 'the']);
  return raw.replace(/[A-Za-z]+(?:'[A-Za-z]+)?/g, (word, offset) => {
    const lower = word.toLowerCase();
    if (minorWords.has(lower) && offset > 0) return lower;
    if (lower.length <= 3 && /(?:^|,\s*)[a-z]{2,3}(?:$|,)/.test(raw.slice(Math.max(0, offset - 2), offset + lower.length + 2))) {
      return lower.toUpperCase();
    }
    return lower.charAt(0).toUpperCase() + lower.slice(1);
  });
}

function formatLightMediationEffect(value) {
  const raw = String(value || '').trim();
  const labels = {
    recovery_support: 'recovery support',
    fatal_pressure: 'fatal pressure',
    none: 'no mediation change',
  };
  return labels[raw] || raw.replace(/_/g, ' ');
}

function formatLightMediationTilt(value) {
  const raw = String(value || '').trim();
  const labels = {
    recovery_mitigated: 'recovery mitigated',
    fatal_pressure_amplified: 'fatal pressure amplified',
    neutral: 'neutral',
  };
  return labels[raw] || raw.replace(/_/g, ' ');
}

function DispositorsCard({ data, includeModern }){
  // Use backend-provided dispositor chains to avoid duplicating reception logic
  const DISP = (data && data.dispositors) || {};
  const baseAnchors = ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn'];
  const modernAnchors = includeModern ? ['Uranus','Neptune','Pluto'] : [];
  const anchors = [...baseAnchors, ...modernAnchors].filter(p => DISP[p]);

  const planetGlyph = (name) => PlanetSymbols[name] || name || '?';

  // Traditional rulers for domicile check (kept in sync with backend)
  const signRuler = {
    'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury', 'Cancer': 'Moon', 'Leo': 'Sun', 'Virgo': 'Mercury',
    'Libra': 'Venus', 'Scorpio': 'Mars', 'Sagittarius': 'Jupiter', 'Capricorn': 'Saturn', 'Aquarius': 'Saturn', 'Pisces': 'Jupiter'
  };
  const planetSign = (planetName) => {
    try {
      const pl = (data?.planets || []).find(p => p.planet === planetName);
      return pl?.sign || null;
    } catch (_) { return null; }
  };
  const isDomicile = (planetName) => {
    const sign = planetSign(planetName);
    if (!sign) return false;
    return signRuler[sign] === planetName;
  };

  return (
    <div className="space-y-2.5 text-sm">
      {anchors.length === 0 ? <div className="text-sm text-zinc-500">No dispositor chains available.</div> : anchors.map((anchor) => {
        const info = DISP[anchor] || {};
        const state = normalizeDispositorState(info, anchor);
        const chain = state.chain;
        const finalDisp = state.finalDispositor || chain[chain.length - 1] || anchor;
        const domAnchor = isDomicile(anchor);
        const domFinal = isDomicile(finalDisp);
        const tooltip = formatDispositorTooltip(state, planetSign);
        const summary = formatDispositorSummary(state, { planetGlyph, domAnchor, domFinal });
        const showSummary = summary && shouldRenderDispositorSummary(state);
        return (
          <div
            key={anchor}
            title={tooltip}
            aria-label={`Dispositor chain: ${tooltip}`}
            className="border-t border-zinc-100 pt-2.5 first:border-t-0 first:pt-0"
          >
            <div className="flex items-center gap-2">
              <div className="flex min-w-0 flex-wrap items-center gap-2 text-[14px] leading-none text-zinc-900">
                {chain.map((nm, i) => (
                  <React.Fragment key={`${anchor}-${nm}-${i}`}>
                    <span>{planetGlyph(nm)}</span>
                    {i < chain.length - 1 && <span className="text-zinc-300">→</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>
            {showSummary ? (
              <div className="mt-1 text-[11px] text-zinc-500">
                {summary}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

const MORIN_PAYLOAD_KEYS = [
  'morin_aspects',
  'morin_antiscia',
  'morin_contra_antiscia',
  'morin_combustion',
  'morin_patterns',
];

function hasMorinRows(value) {
  if (Array.isArray(value)) return value.length > 0;
  if (value && typeof value === 'object') return Object.keys(value).length > 0;
  return false;
}

function hasMorinPayload(data) {
  if (!data || typeof data !== 'object') return false;
  return MORIN_PAYLOAD_KEYS.some((key) => hasMorinRows(data[key]));
}

function buildAstroClockChartSignature(data) {
  if (!data || typeof data !== 'object') return '';
  const timestamp = typeof data.timestamp === 'string' ? data.timestamp : '';
  const location = typeof data.location === 'string' ? data.location.trim().toLowerCase() : '';
  const timezone = typeof data.timezone === 'string' ? data.timezone.trim() : '';
  const houseCusps = Array.isArray(data.house_cusps)
    ? data.house_cusps.map((lon) => {
      const num = Number(lon);
      return Number.isFinite(num) ? num.toFixed(6) : '';
    }).join('|')
    : '';
  const planets = Array.isArray(data.planets)
    ? data.planets.map((planet) => {
      const lon = Number(planet?.longitude);
      const lonText = Number.isFinite(lon) ? lon.toFixed(6) : '';
      return `${planet?.planet || ''}:${lonText}:${planet?.house ?? ''}`;
    }).join('|')
    : '';
  if (!timestamp && !houseCusps && !planets) return '';
  return [timestamp, location, timezone, houseCusps, planets].join('||');
}

function preserveMorinPayloadForSameChart(currentData, nextData) {
  if (!currentData || !nextData) return nextData;
  if (!hasMorinPayload(currentData) || hasMorinPayload(nextData)) return nextData;
  const currentSignature = buildAstroClockChartSignature(currentData);
  const nextSignature = buildAstroClockChartSignature(nextData);
  if (!currentSignature || currentSignature !== nextSignature) return nextData;
  const merged = { ...nextData };
  for (const key of MORIN_PAYLOAD_KEYS) {
    merged[key] = currentData[key] ?? nextData[key];
  }
  return merged;
}


const AstroClock = ({
  darkMode,
  setCurrentView,
  apiStatus,
  licenseActive = false,
  licenseChecking = false,
  onLicenseChanged,
}) => {
  const backendStatus = normalizeBackendStatus(apiStatus);
  const backendChecking = backendStatus === 'checking';
  const backendOffline = backendStatus === 'offline';
  const backendReady = !backendChecking && !backendOffline;
  const packagedRuntime = typeof window !== 'undefined' && window.IS_PACKAGED === true;
  const initialWarmStateRef = useRef(readAstroClockWarmState() || {});
  const initialWarmState = initialWarmStateRef.current;
  const storedAutoContextRef = useRef(readStoredAstroClockAutoContext());
  const [mode, setMode] = useState(() => initialWarmState.mode || 'realtime');
  const [manualDate, setManualDate] = useState(() => initialWarmState.manualDate || '');
  const [manualTime, setManualTime] = useState(() => initialWarmState.manualTime || '');
  const [manualLocation, setManualLocation] = useState(() => initialWarmState.manualLocation || '');
  const [manualTimeResolution, setManualTimeResolution] = useState(null);
  const storedAutoLocationRef = useRef(readStoredAstroClockAutoLocation());
  const [autoLocation, setAutoLocation] = useState(() => (
    normalizeLocationText(storedAutoContextRef.current?.location) ||
    (initialWarmState.mode === 'realtime' ? normalizeLocationText(initialWarmState.data?.location) : '') ||
    (normalizeLocationText(storedAutoLocationRef.current).includes(',')
      ? normalizeLocationText(storedAutoLocationRef.current)
      : '') ||
    (initialWarmState.mode !== 'realtime' ? normalizeLocationText(initialWarmState.autoLocation) : '')
  ));
  const [activeSnapId, setActiveSnapId] = useState(() => initialWarmState.activeSnapId || '');
  const [data, setData] = useState(() => initialWarmState.data || null);
  const dataRef = useRef(initialWarmState.data || null);
  const [hours, setHours] = useState(() => initialWarmState.hours || null);
  const [loading, setLoading] = useState(false);
  const [actionError, setActionError] = useState('');
  const [clockLoadError, setClockLoadError] = useState('');
  const [includeModern, setIncludeModern] = useState(() => Boolean(initialWarmState.includeModern));
  const [chartLens, setChartLens] = useState(() => {
    const saved = typeof initialWarmState.chartLens === 'string' ? initialWarmState.chartLens : '';
    if (saved === 'traditional' || saved === 'modern' || saved === 'bodies') return saved;
    return initialWarmState.includeModern ? 'modern' : 'traditional';
  });
  const [houseSystem, setHouseSystem] = useState(() => {
    if (typeof initialWarmState.houseSystem === 'string' && initialWarmState.houseSystem.trim()) {
      return initialWarmState.houseSystem.trim();
    }
    try { return localStorage.getItem('vox_stella_house_system_code') || 'R'; } catch(_) { return 'R'; }
  });
  const [specialDegrees, setSpecialDegrees] = useState(() => (
    Array.isArray(initialWarmState.specialDegrees) ? initialWarmState.specialDegrees : []
  ));
  const [useMorin, setUseMorin] = useState(() => Boolean(initialWarmState.useMorin));
  const [activeManualIso, setActiveManualIso] = useState(() => initialWarmState.activeManualIso || null);
  const streamRef = useRef(null);
  const manualPending = mode === 'manual' && !activeManualIso;
  const [snaps, setSnaps] = useState(() => (
    Array.isArray(initialWarmState.snaps) ? initialWarmState.snaps : []
  ));
  const [loadingSnaps, setLoadingSnaps] = useState(false);
  const [snapsLoaded, setSnapsLoaded] = useState(() => Boolean(initialWarmState.snapsLoaded));
  const [snapMigrationReport, setSnapMigrationReport] = useState(null);
  const [snapSaving, setSnapSaving] = useState(false);
  const [showForensic, setShowForensic] = useState(false);
  const [openingForensic, setOpeningForensic] = useState(false);
  const [showTraits, setShowTraits] = useState(false);
  const [showSynastry, setShowSynastry] = useState(false);
  const [showTransits, setShowTransits] = useState(false);
  const [showElection, setShowElection] = useState(false);
  const [showAstrocartography, setShowAstrocartography] = useState(false);
  const [showChineseAstrology, setShowChineseAstrology] = useState(false);
  const [showBirthCertification, setShowBirthCertification] = useState(false);
  const [premiumOfferFeature, setPremiumOfferFeature] = useState('');
  const [copiedCasePrompt, setCopiedCasePrompt] = useState(false);
  const [copiedBirthPrompt, setCopiedBirthPrompt] = useState(false);
  const [copiedAssetPrompt, setCopiedAssetPrompt] = useState(false);
  const [showAspectAnalysis, setShowAspectAnalysis] = useState(false);
  // Single-button prompt menu state
  const [showPromptMenu, setShowPromptMenu] = useState(false);
  // Name prompt modal state (works in dev and packaged builds)
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [namePromptType, setNamePromptType] = useState(null); // 'natal' | 'case' | 'asset'
  const [isStreaming, setIsStreaming] = useState(false);
  const [realtimeTransportRefreshKey, setRealtimeTransportRefreshKey] = useState(0);
  const featurePauseRef = useRef({ count: 0, resumeNeeded: false, snapshotIso: null, pausing: false, pausePromise: null });
  const modeRef = useRef(mode);
  const activeManualIsoRef = useRef(activeManualIso);
  const manualLocationRef = useRef(manualLocation);
  const autoLocationRef = useRef(autoLocation);
  const activeManualContextRef = useRef(null);
  const viewVersionRef = useRef(0);
  const dashboardRequestRef = useRef(0);
  const hoursRequestRef = useRef(0);
  const loadingRef = useRef(false);
  const dashboardAbortRef = useRef(null);
  const hoursAbortRef = useRef(null);
  const modeTransitionAbortRef = useRef(null);
  const skipNextManualDashboardRefreshRef = useRef(false);
  const skipNextRealtimeBootstrapRef = useRef(false);
  const skipNextHoursRefreshRef = useRef(false);
  const snapSaveInFlightRef = useRef(null);

  const closeRealtimeStream = useCallback(() => {
    if (streamRef.current) {
      try { streamRef.current.close(); } catch (_) {}
      streamRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const replaceAbortController = useCallback((ref) => {
    if (ref.current) {
      try { ref.current.abort(); } catch (_) {}
    }
    const controller = new AbortController();
    ref.current = controller;
    return controller;
  }, []);

  useEffect(() => { modeRef.current = mode; }, [mode]);
  useEffect(() => { activeManualIsoRef.current = activeManualIso; }, [activeManualIso]);
  useEffect(() => { manualLocationRef.current = manualLocation; }, [manualLocation]);
  useEffect(() => { autoLocationRef.current = autoLocation; }, [autoLocation]);
  useEffect(() => { dataRef.current = data; }, [data]);
  useEffect(() => { loadingRef.current = loading; }, [loading]);
  useEffect(() => {
    if (backendChecking || backendReady) {
      setClockLoadError('');
    }
    if (!backendReady) {
      closeRealtimeStream();
    }
  }, [backendChecking, backendReady, closeRealtimeStream]);
  useEffect(() => {
    try {
      const dataLocation = normalizeLocationText(data?.location);
      const latitude = finiteNumberOrUndefined(data?.latitude);
      const longitude = finiteNumberOrUndefined(data?.longitude);
      if (mode === 'realtime' && dataLocation && latitude != null && longitude != null) {
        const nextContext = {
          location: dataLocation,
          timezone: resolveAstroClockTimezone(data?.timezone, data?.timezone_label) || '',
          timezone_label: normalizeLocationText(data?.timezone_label),
          latitude,
          longitude,
        };
        storedAutoContextRef.current = nextContext;
        localStorage.setItem(ASTRO_CLOCK_AUTO_LOCATION_STORAGE_KEY, dataLocation);
        localStorage.setItem(ASTRO_CLOCK_AUTO_CONTEXT_STORAGE_KEY, JSON.stringify(nextContext));
      } else if (!normalizeLocationText(autoLocation) && !dataLocation) {
        storedAutoContextRef.current = null;
        localStorage.removeItem(ASTRO_CLOCK_AUTO_LOCATION_STORAGE_KEY);
        localStorage.removeItem(ASTRO_CLOCK_AUTO_CONTEXT_STORAGE_KEY);
      }
    } catch (_) {}
  }, [autoLocation, data?.latitude, data?.location, data?.longitude, data?.timezone, data?.timezone_label, mode]);
  useEffect(() => {
    const wantsModern = chartLens !== 'traditional';
    setIncludeModern((current) => (current === wantsModern ? current : wantsModern));
  }, [chartLens]);
  useEffect(() => () => {
    if (dashboardAbortRef.current) {
      try { dashboardAbortRef.current.abort(); } catch (_) {}
      dashboardAbortRef.current = null;
    }
    if (hoursAbortRef.current) {
      try { hoursAbortRef.current.abort(); } catch (_) {}
      hoursAbortRef.current = null;
    }
  }, []);

  useEffect(() => {
    const warmAutoLocation = mode === 'realtime'
      ? (
        normalizeLocationText(data?.location) ||
        normalizeLocationText(storedAutoContextRef.current?.location) ||
        ASTRO_CLOCK_DEFAULT_LOCATION
      )
      : normalizeLocationText(autoLocation);
    writeAstroClockWarmState({
      mode,
      manualDate,
      manualTime,
      manualLocation,
      autoLocation: warmAutoLocation,
      activeSnapId,
      data,
      hours,
      includeModern,
      chartLens,
      houseSystem,
      specialDegrees,
      useMorin,
      activeManualIso,
      snaps,
      snapsLoaded,
    });
  }, [
    activeManualIso,
    activeSnapId,
    autoLocation,
    data,
    hours,
    houseSystem,
    chartLens,
    includeModern,
    manualDate,
    manualLocation,
    manualTime,
    mode,
    snaps,
    snapsLoaded,
    specialDegrees,
    useMorin,
  ]);

  const openNamePrompt = useCallback((type) => {
    setNamePromptType(type);
    setShowNamePrompt(true);
  }, []);

  const getSnapContext = useCallback((snapId) => {
    const targetId = String(snapId || '').trim();
    if (!targetId) return null;
    const item = (Array.isArray(snaps) ? snaps : []).find((snap) => String(snap?.id || '') === targetId);
    if (!isSavedSnapCalculationEligible(item)) return null;
    const dashboard = item?.dashboard && typeof item.dashboard === 'object' ? item.dashboard : {};
    const location =
      normalizeLocationText(item?.location) ||
      normalizeLocationText(dashboard?.location);
    const timezone = resolveAstroClockTimezone(
      item?.timezone || dashboard?.timezone,
      item?.timezone_label || dashboard?.timezone_label,
    );
    const latitude = finiteNumberOrUndefined(dashboard?.latitude ?? item?.latitude);
    const longitude = finiteNumberOrUndefined(dashboard?.longitude ?? item?.longitude);
    return {
      id: targetId,
      timestamp: item?.effective_datetime || dashboard?.timestamp || '',
      location,
      timezone,
      latitude,
      longitude,
    };
  }, [snaps]);

  const buildActiveChartPromptPayload = () => {
    const live = data || {};
    const snapContext = getSnapContext(activeSnapId);
    return {
      chart_context: {
        mode: modeRef.current || mode,
        timestamp: live.timestamp || activeManualIsoRef.current || null,
        location: snapContext?.location || live.location || autoLocationRef.current || manualLocationRef.current || null,
        timezone: live.timezone || snapContext?.timezone || null,
        timezone_label: live.timezone_label || null,
        house_system: houseSystem || null,
      },
      display_toggles: {
        include_modern: !!includeModern,
        morin_mode: !!useMorin,
      },
      chart_factors: {
        planets: Array.isArray(live.planets) ? live.planets.map((p) => ({
          planet: p?.planet || null,
          sign: p?.sign || null,
          house: p?.house ?? null,
          longitude: p?.longitude ?? null,
          dignity_score: p?.dignity_score ?? null,
          essential_dignity: p?.essential_dignity ?? null,
          accidental_dignity: p?.accidental_dignity ?? null,
          retrograde: !!p?.retrograde,
        })) : [],
        moon: live.moon || null,
        moon_timeline: live.moon_timeline || null,
        solar_conditions: live.solar_conditions || null,
        top_aspects: Array.isArray(live.top_aspects) ? live.top_aspects.slice(0, 12) : [],
        morin_aspects: Array.isArray(live.morin_aspects) ? live.morin_aspects.slice(0, 12) : [],
        house_cusps: Array.isArray(live.house_cusps) ? live.house_cusps : [],
        house_rulers: live.house_rulers || {},
        receptions: live.receptions || null,
        fixed_star_hits: Array.isArray(live.fixed_star_hits) ? live.fixed_star_hits : [],
        arabic_parts: live.arabic_parts || {},
        dispositors: live.dispositors || {},
        sect: live.sect || null,
        special_degrees: Array.isArray(specialDegrees) ? specialDegrees : [],
        morin_patterns: live.morin_patterns || null,
        metrics: live.metrics || null,
      },
    };
  };

  const withActiveChartPromptPayload = (baseText) => {
    const payload = buildActiveChartPromptPayload();
    return `${baseText}\n\nCurrent Astro Clock chart payload:\n\`\`\`json\n${JSON.stringify(payload, null, 2)}\n\`\`\``;
  };

  const buildCasePromptText = (name) => (
    withActiveChartPromptPayload(`Case name: ${name}\n\nTask:\nProvide the timestamp + location/time-zone package needed to cast forensic-astrology event charts. Do not generate charts or interpretations-only deliver items (1) and (2) below. Make best-judgment choices and state assumptions briefly (no follow-up questions).\n\n1) Identify Event Timestamps\n   - Primary: the earliest reliable discovery/notification moment.\n   - Alternates: (a) emergency/official log time, (b) legal pronouncement (e.g., time of death), (c) last confirmed alive/seen.\n   - For each timestamp: give local time (to the minute), UTC equivalent, a short reliability note, and 1–2 source links. If sources conflict, pick the most authoritative, explain why, and list the runner-up time(s).\n\n2) Locations & Time Zones\n   - For each timestamp: provide the full street address (venue + city + country), precise coordinates in decimal degrees (lat/long), time-zone name and UTC offset, and whether daylight saving time was in effect at that moment. Show the UTC conversion you used.\n\nOutput format (one markdown table):\nLabel | Local Time | UTC | Address | Lat/Long | Time Zone (incl. DST) | Source(s) | Reliability Notes`)
  );

  const buildNatalPromptText = (name) => (
    withActiveChartPromptPayload(`Subject: ${name}\n\nTask:\nProvide a complete natal birth data package to cast a birth chart. Do not generate the chart or interpretations-only deliver the data items below. Make best‑judgment choices and state assumptions briefly (no follow‑up questions).\n\n1) Birth Date & Time\n   - Local civil time (to the minute) with calendar (Gregorian/Julian if historical).\n   - UTC equivalent.\n   - Time accuracy rating (AA, A, B, C, DD) with a 1–2 sentence note.\n   - 1–2 source links (registry, certificate, biography, reliable database). If sources conflict, pick the most authoritative, explain why, and list runner‑up time(s).\n\n2) Location & Time Zone\n   - Birthplace: venue (if known), city, region, country.\n   - Coordinates in decimal degrees (lat/long).\n   - Time‑zone name and UTC offset at that moment; explicitly confirm whether DST was in effect.\n   - Show the UTC conversion used.\n\n3) If unknown/uncertain time\n   - Provide best estimated window (e.g., 08:00–10:00), basis (biography, hospital shift, sunrise/noon defaults), and cautions.\n\nOutput format (one markdown table):\nLabel | Local Time | UTC | Location | Lat/Long | Time Zone (incl. DST) | Source(s) | Reliability Notes`)
  );

  const buildAssetPromptText = (name) => (
    withActiveChartPromptPayload(`Asset/Instrument: ${name}\n\nTask:\nProvide a complete "birth chart" data package for this asset/instrument suitable for astrological research. Do not generate the chart or interpretations — only deliver the data items below. Make best‑judgment choices and state assumptions briefly (no follow‑up questions).\n\n1) Primary First‑Trade Chart\n   - Exchange/Market: primary listing venue (full name) and country.\n   - Ticker/Symbol: include class/series if applicable.\n   - First trade local time (to the minute) and date; specify whether this is opening auction/cross time or the first executed trade print.\n   - UTC equivalent.\n   - Location: exchange city/region/country; coordinates in decimal degrees (lat/long).\n   - Time‑zone name and UTC offset at that moment; explicitly confirm whether DST was in effect.\n   - 1–2 authoritative source links (exchange notices, prospectus/SEC/FCA filings, exchange/issuer press releases, reliable financial databases). If sources conflict, pick the most authoritative, explain why, and list runner‑up time(s).\n\n2) Special Cases Guidance\n   - Crypto: use genesis/launch timestamp or first exchange listing/trade; name the chain/exchange.\n   - Indices: use official launch/first publication timestamp.\n   - Futures/Options: use first trade timestamp on the primary exchange for the contract; include contract identifier.\n   - ETFs/ETNs: first trade on primary listing exchange; include ISIN if available.\n\nOutput format (one markdown table):\nLabel | Local Time | UTC | Exchange/Market | Ticker | Location | Lat/Long | Time Zone (incl. DST) | Source(s) | Reliability Notes`)
  );

  // Cusp Aspects filters (curated UI)
  const ANGULAR_SET = useMemo(()=> new Set(['H1','H4','H7','H10']), []);
  const SUCCEDENT_SET = useMemo(()=> new Set(['H2','H5','H8','H11']), []);
  const CADENT_SET = useMemo(()=> new Set(['H3','H6','H9','H12']), []);
  const REL_SET = useMemo(()=> new Set(['H5','H7','H11']), []);
  const TRAVEL_SET = useMemo(()=> new Set(['H3','H9']), []);
  const MONEY_SET = useMemo(()=> new Set(['H2','H8']), []);

  const DEFAULT_ALL = useMemo(()=> new Set(Array.from({length:12}, (_,i)=>`H${i+1}`)), []);
  const [cuspSelected, setCuspSelected] = useState(()=>{
    try { const raw = localStorage.getItem('cusp_sel'); if (raw) return new Set(JSON.parse(raw)); } catch(_) {}
    return new Set(DEFAULT_ALL);
  });
  const [cuspAll, setCuspAll] = useState(false);
  const [cuspAspectMode, setCuspAspectMode] = useState(()=>{ try { return localStorage.getItem('cusp_amode')||'all'; } catch(_) { return 'all'; }}); // 'hard'|'all'|'conj'
  const [cuspPhase, setCuspPhase] = useState(()=>{ try { return localStorage.getItem('cusp_phase')||'any'; } catch(_) { return 'any'; }}); // 'any'|'applying'|'separating'
  // Fixed orb policy for cusps: ≤ 1.0° (no UI slider)
  const [showCuspMenu, setShowCuspMenu] = useState(false);

  useEffect(()=>{ try { localStorage.setItem('cusp_sel', JSON.stringify(Array.from(cuspSelected))); } catch(_){} }, [cuspSelected]);
  useEffect(()=>{ try { localStorage.setItem('cusp_amode', String(cuspAspectMode)); } catch(_){} }, [cuspAspectMode]);
  useEffect(()=>{ try { localStorage.setItem('cusp_phase', String(cuspPhase)); } catch(_){} }, [cuspPhase]);
  // No cusp orb persistence; fixed at 1.0°

  const applyPreset = (set) => {
    setCuspSelected(prev => new Set([...prev, ...set]));
    setCuspAll(false);
  };
  const setAllCusps = () => { setCuspSelected(new Set(DEFAULT_ALL)); setCuspAll(true); };
  const clearCusps = () => { setCuspSelected(new Set()); setCuspAll(false); };
  const toggleCusp = (k) => {
    setCuspSelected(prev => { const n = new Set(prev); if (n.has(k)) n.delete(k); else n.add(k); setCuspAll(n.size===12); return n; });
  };

  const handleNamePromptSubmit = async (name) => {
    const trimmed = (name || '').trim();
    if (!trimmed) return;
    try {
      if (namePromptType === 'case') {
        const txt = buildCasePromptText(trimmed);
        const ok = await safeCopyText(txt);
        if (ok) { setCopiedCasePrompt(true); setTimeout(() => setCopiedCasePrompt(false), 2000); }
      } else if (namePromptType === 'natal') {
        const txt = buildNatalPromptText(trimmed);
        const ok = await safeCopyText(txt);
        if (ok) { setCopiedBirthPrompt(true); setTimeout(() => setCopiedBirthPrompt(false), 2000); }
      } else if (namePromptType === 'asset') {
        const txt = buildAssetPromptText(trimmed);
        const ok = await safeCopyText(txt);
        if (ok) { setCopiedAssetPrompt(true); setTimeout(() => setCopiedAssetPrompt(false), 2000); }
      }
    } finally {
      setShowNamePrompt(false);
    }
  };

  const beginViewVersion = useCallback(() => {
    viewVersionRef.current += 1;
    return viewVersionRef.current;
  }, []);

  const beginModeTransition = useCallback(() => {
    try { modeTransitionAbortRef.current?.abort?.(); } catch (_) {}
    try { dashboardAbortRef.current?.abort?.(); } catch (_) {}
    try { hoursAbortRef.current?.abort?.(); } catch (_) {}
    const controller = new AbortController();
    modeTransitionAbortRef.current = controller;
    return {
      controller,
      viewVersion: beginViewVersion(),
    };
  }, [beginViewVersion]);

  const completeModeTransition = useCallback((controller) => {
    if (modeTransitionAbortRef.current === controller) {
      modeTransitionAbortRef.current = null;
      setLoading(false);
    }
  }, []);

  const syncManualSnapshotInputs = useCallback((iso, { location, timezone } = {}) => {
    if (!iso || typeof iso !== 'string') return;
    try {
      const d = new Date(iso);
      if (!Number.isFinite(d.getTime())) return;
      const tz = (typeof timezone === 'string' && timezone.trim()) ? timezone.trim() : undefined;
      if (tz && typeof Intl !== 'undefined' && Intl.DateTimeFormat) {
        const parts = new Intl.DateTimeFormat('en-GB', {
          timeZone: tz,
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        }).formatToParts(d);
        const get = (t) => (parts.find(p => p.type === t)?.value || '').padStart(2, '0');
        const yyyy = parts.find(p => p.type === 'year')?.value || String(d.getFullYear());
        const mm = get('month');
        const dd = get('day');
        const hh = get('hour');
        const min = get('minute');
        setManualDate(`${yyyy}-${mm}-${dd}`);
        setManualTime(`${hh}:${min}`);
      } else {
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        const hh = String(d.getHours()).padStart(2, '0');
        const min = String(d.getMinutes()).padStart(2, '0');
        setManualDate(`${yyyy}-${mm}-${dd}`);
        setManualTime(`${hh}:${min}`);
      }
    } catch (_) {}
    if (typeof location === 'string' && location.trim()) {
      const nextLocation = location.trim();
      manualLocationRef.current = nextLocation;
      setManualLocation(nextLocation);
    }
  }, []);

  const normalizeSnapLocationKey = useCallback((value) => {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ');
  }, []);

  const findMatchingSnapId = useCallback((items, { iso, location } = {}) => {
    const targetMs = new Date(String(iso || '')).getTime();
    if (!Number.isFinite(targetMs)) return '';
    const targetLocation = normalizeSnapLocationKey(location);
    const findBy = (matcher) => {
      const match = (Array.isArray(items) ? items : []).find((snap) => {
        if (!isSavedSnapCalculationEligible(snap)) return false;
        const snapMs = new Date(String(snap?.effective_datetime || '')).getTime();
        if (!Number.isFinite(snapMs) || snapMs !== targetMs) return false;
        return matcher(snap);
      });
      return match?.id ? String(match.id) : '';
    };
    const exactLocationMatch = targetLocation
      ? findBy((snap) => normalizeSnapLocationKey(snap?.location) === targetLocation)
      : '';
    if (exactLocationMatch) return exactLocationMatch;
    return findBy(() => true);
  }, [normalizeSnapLocationKey]);

  const applyDashboardPayload = useCallback((payload, options = {}) => {
    const transformed = transformDashboard(payload);
    const merged = options?.requestedMorin
      ? transformed
      : preserveMorinPayloadForSameChart(dataRef.current, transformed);
    dataRef.current = merged;
    setData(merged);
    if (modeRef.current === 'realtime' && !autoLocationRef.current && merged?.location) {
      const nextAutoLocation = normalizeLocationText(merged.location);
      if (nextAutoLocation) {
        autoLocationRef.current = nextAutoLocation;
        setAutoLocation(nextAutoLocation);
      }
    }
    if (!manualLocationRef.current && merged?.location) {
      manualLocationRef.current = merged.location;
      setManualLocation(merged.location);
    }
    return merged;
  }, []);

  const buildClockContext = useCallback((overrides = {}) => {
    const currentMode = modeRef.current || mode;
    const requestedMode = overrides.mode || currentMode;
    const explicitLocation = normalizeLocationText(overrides.location);
    const hasExplicitLocation = Boolean(explicitLocation);
    const hasExplicitTimezone = typeof overrides.timezone === 'string' && overrides.timezone.trim();
    const explicitLatitude = finiteNumberOrUndefined(overrides.latitude);
    const explicitLongitude = finiteNumberOrUndefined(overrides.longitude);
    const hasExplicitCoordinates = explicitLatitude != null && explicitLongitude != null;
    const appliedLatitude = finiteNumberOrUndefined(data?.latitude);
    const appliedLongitude = finiteNumberOrUndefined(data?.longitude);
    const appliedTimezone = resolveAstroClockTimezone(data?.timezone, data?.timezone_label);
    const appliedLocation =
      (typeof data?.location === 'string' && data.location.trim()) ? data.location.trim() : undefined;
    const typedLocation =
      (typeof manualLocationRef.current === 'string' && manualLocationRef.current.trim())
        ? manualLocationRef.current.trim()
        : undefined;
    const typedAutoLocation =
      (typeof autoLocationRef.current === 'string' && autoLocationRef.current.trim())
        ? autoLocationRef.current.trim()
        : undefined;
    const manualLocationForDiff = explicitLocation || typedLocation;
    const locationDiffersFromApplied =
      !!manualLocationForDiff && !!appliedLocation && manualLocationForDiff.toLowerCase() !== appliedLocation.toLowerCase();
    const resolvedDatetime =
      (typeof overrides.datetime === 'string' && overrides.datetime.trim())
        ? overrides.datetime.trim()
        : activeManualIsoRef.current;
    const resolvedHouseSystem = overrides.houseSystem || houseSystem;
    const context = {};
    if (requestedMode === 'manual' && resolvedDatetime) {
      const resolvedLocation =
        explicitLocation || typedLocation || appliedLocation;
      const resolvedTimezone =
        hasExplicitTimezone
          ? overrides.timezone.trim()
          : (hasExplicitLocation || locationDiffersFromApplied)
            ? undefined
            : appliedTimezone;
      context.mode = 'manual';
      context.datetime = resolvedDatetime;
      if (resolvedLocation) context.location = resolvedLocation;
      if (resolvedTimezone) context.timezone = resolvedTimezone;
      if (hasExplicitCoordinates) {
        context.latitude = explicitLatitude;
        context.longitude = explicitLongitude;
      } else if (!hasExplicitLocation && !typedLocation && appliedLatitude != null && appliedLongitude != null) {
        context.latitude = appliedLatitude;
        context.longitude = appliedLongitude;
      }
    } else if (requestedMode === 'realtime') {
      const switchingToRealtime = currentMode !== 'realtime';
      const realtimeRequestedLocation = explicitLocation || (switchingToRealtime ? typedAutoLocation : undefined);
      const resolvedLocation =
        realtimeRequestedLocation ||
        (switchingToRealtime ? undefined : appliedLocation || typedAutoLocation) ||
        ASTRO_CLOCK_DEFAULT_LOCATION;
      const resolvedTimezone =
        hasExplicitTimezone
          ? overrides.timezone.trim()
          : resolvedLocation
            ? undefined
            : (switchingToRealtime ? undefined : appliedTimezone);
      context.mode = 'realtime';
      if (resolvedLocation) context.location = resolvedLocation;
      if (resolvedTimezone) context.timezone = resolvedTimezone;
      if (hasExplicitCoordinates) {
        context.latitude = explicitLatitude;
        context.longitude = explicitLongitude;
      }
    }
    if (resolvedHouseSystem) context.houseSystem = resolvedHouseSystem;
    return context;
  }, [data?.latitude, data?.location, data?.longitude, data?.timezone, data?.timezone_label, houseSystem, mode]);

  const buildAppliedClockContext = useCallback((overrides = {}) => {
    const activeMode = overrides.mode || modeRef.current || mode;
    const snapContext = activeMode === 'manual' ? getSnapContext(activeSnapId) : null;
    const manualContext = activeMode === 'manual' ? activeManualContextRef.current : null;
    const dashboardTimezone = resolveAstroClockTimezone(data?.timezone, data?.timezone_label);
    const appliedTimezone = activeMode === 'manual' && snapContext
      ? (snapContext.timezone || dashboardTimezone)
      : (dashboardTimezone || snapContext?.timezone || manualContext?.timezone);
    const dashboardLatitude = finiteNumberOrUndefined(data?.latitude);
    const dashboardLongitude = finiteNumberOrUndefined(data?.longitude);
    const manualLatitude = finiteNumberOrUndefined(manualContext?.latitude);
    const manualLongitude = finiteNumberOrUndefined(manualContext?.longitude);
    const appliedLatitude = activeMode === 'manual'
      ? (snapContext ? (snapContext.latitude ?? dashboardLatitude) : manualLatitude)
      : (dashboardLatitude ?? snapContext?.latitude);
    const appliedLongitude = activeMode === 'manual'
      ? (snapContext ? (snapContext.longitude ?? dashboardLongitude) : manualLongitude)
      : (dashboardLongitude ?? snapContext?.longitude);
    const dashboardLocation =
      (typeof data?.location === 'string' && data.location.trim())
        ? data.location.trim()
        : '';
    const appliedLocation =
      snapContext?.location ||
      dashboardLocation ||
      (activeMode === 'manual' ? manualLocationRef.current : autoLocationRef.current);
    const appliedContext = buildClockContext({
      ...overrides,
      mode: activeMode,
      datetime: activeMode === 'manual'
        ? (overrides.datetime || activeManualIsoRef.current || data?.timestamp)
        : overrides.datetime,
      location: overrides.location || appliedLocation,
      timezone: overrides.timezone || appliedTimezone,
      latitude: overrides.latitude ?? appliedLatitude,
      longitude: overrides.longitude ?? appliedLongitude,
      houseSystem: overrides.houseSystem || houseSystem,
    });
    if (activeMode === 'manual' && snapContext && activeSnapId) {
      return {
        ...appliedContext,
        snapId: String(activeSnapId),
      };
    }
    return appliedContext;
  }, [
    buildClockContext,
    data?.latitude,
    data?.location,
    data?.longitude,
    data?.timestamp,
    data?.timezone,
    data?.timezone_label,
    getSnapContext,
    houseSystem,
    mode,
    activeSnapId,
  ]);
  const buildAppliedClockContextRef = useRef(buildAppliedClockContext);
  buildAppliedClockContextRef.current = buildAppliedClockContext;

  const deriveChartDateTimeParts = useCallback((iso, timezone) => {
    if (!iso || typeof iso !== 'string') return { date: '', time: '' };
    try {
      const d = new Date(iso);
      if (!Number.isFinite(d.getTime())) return { date: '', time: '' };
      const tz = (typeof timezone === 'string' && timezone.trim()) ? timezone.trim() : undefined;
      if (tz && typeof Intl !== 'undefined' && Intl.DateTimeFormat) {
        const parts = new Intl.DateTimeFormat('en-GB', {
          timeZone: tz,
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        }).formatToParts(d);
        const get = (type) => (parts.find((part) => part.type === type)?.value || '').padStart(2, '0');
        const yyyy = parts.find((part) => part.type === 'year')?.value || String(d.getFullYear());
        const mm = get('month');
        const dd = get('day');
        const hh = get('hour');
        const min = get('minute');
        return { date: `${yyyy}-${mm}-${dd}`, time: `${hh}:${min}` };
      }
      return {
        date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
        time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
      };
    } catch (_) {
      return { date: '', time: '' };
    }
  }, []);

  const inferredActiveSnapId = useMemo(() => {
    if (activeSnapId) return '';
    return findMatchingSnapId(snaps, {
      iso: activeManualIso || data?.timestamp || '',
      location: data?.location || manualLocation || '',
    });
  }, [
    activeManualIso,
    activeSnapId,
    data?.location,
    data?.timestamp,
    findMatchingSnapId,
    manualLocation,
    snaps,
  ]);

  const activeSnapContext = useMemo(() => (
    getSnapContext(activeSnapId || inferredActiveSnapId)
  ), [activeSnapId, getSnapContext, inferredActiveSnapId]);

  useEffect(() => {
    if (!activeSnapId && inferredActiveSnapId) {
      setActiveSnapId(inferredActiveSnapId);
    }
  }, [activeSnapId, inferredActiveSnapId]);

  useEffect(() => {
    if (!activeSnapId) return;
    const activeSnap = (Array.isArray(snaps) ? snaps : []).find(
      (snap) => String(snap?.id || '') === String(activeSnapId),
    );
    if (activeSnap && !isSavedSnapCalculationEligible(activeSnap)) {
      setActiveSnapId('');
      setActionError(
        String(activeSnap?.superseded_by || '').trim()
          ? 'The previously selected saved chart was superseded. Use its corrected copy.'
          : 'The previously selected saved chart needs context review. Correct it and use the corrected copy.',
      );
    }
  }, [activeSnapId, snaps]);

  const activeTransitSeed = useMemo(() => {
    const timezone = resolveAstroClockTimezone(data?.timezone, data?.timezone_label) || activeSnapContext?.timezone || '';
    const activeIso = activeManualIso || data?.timestamp || '';
    const derived = deriveChartDateTimeParts(activeIso, timezone);
    const latitude = mode === 'realtime'
      ? finiteNumberOrUndefined(data?.latitude)
      : (activeSnapContext?.latitude ?? finiteNumberOrUndefined(activeManualContextRef.current?.latitude));
    const longitude = mode === 'realtime'
      ? finiteNumberOrUndefined(data?.longitude)
      : (activeSnapContext?.longitude ?? finiteNumberOrUndefined(activeManualContextRef.current?.longitude));
    return {
      snapId: activeSnapId || inferredActiveSnapId || '',
      date: derived.date || manualDate || '',
      time: derived.time || manualTime || '',
      location: (mode === 'realtime'
        ? data?.location || autoLocation || ''
        : activeSnapContext?.location || data?.location || manualLocation || ''
      ).trim(),
      timezone,
      latitude,
      longitude,
      houseSystem,
    };
  }, [
    activeManualIso,
    activeSnapId,
    activeSnapContext,
    autoLocation,
    data?.latitude,
    data?.location,
    data?.longitude,
    data?.timestamp,
    data?.timezone,
    data?.timezone_label,
    deriveChartDateTimeParts,
    inferredActiveSnapId,
    houseSystem,
    manualDate,
    manualLocation,
    manualTime,
    mode,
  ]);

  const requestDashboard = useCallback(async (opts = {}, meta = {}) => {
    if (!backendReady) {
      return null;
    }
    const requestId = ++dashboardRequestRef.current;
    const viewVersion = meta.viewVersion ?? viewVersionRef.current;
    const controller = replaceAbortController(dashboardAbortRef);
    const isCurrentRequest = () => shouldApplyAstroClockRequest({
      requestId,
      latestRequestId: dashboardRequestRef.current,
      viewVersion,
      latestViewVersion: viewVersionRef.current,
    });
    try {
      const res = await AstroClockAPI.getDashboard({ ...opts, signal: controller.signal });
      if (!res?.success) {
        if (isCurrentRequest()) {
          const message = getActionErrorMessage(
            { message: res?.error || res?.detail || res?.message },
            'Failed to load Astro Clock dashboard.',
          );
          if (message && !backendChecking) {
            console.error('Failed to load Astro Clock dashboard', res);
            setClockLoadError(message);
          } else {
            setClockLoadError('');
          }
        }
        return null;
      }
      if (!isCurrentRequest()) {
        return null;
      }
      setClockLoadError('');
      return applyDashboardPayload(res.data, { requestedMorin: Boolean(opts?.morin) });
    } catch (error) {
      if (controller.signal.aborted) {
        return null;
      }
      if (isCurrentRequest()) {
        const message = getClockLoadErrorMessage(error, 'Failed to load Astro Clock dashboard.', {
          backendStatus,
        });
        if (message) {
          console.error('Failed to load Astro Clock dashboard', error);
          setClockLoadError(message);
        } else {
          setClockLoadError('');
        }
      }
      return null;
    } finally {
      if (dashboardAbortRef.current === controller) {
        dashboardAbortRef.current = null;
      }
    }
  }, [applyDashboardPayload, backendChecking, backendReady, backendStatus, replaceAbortController]);

  const requestHours = useCallback(async (opts, meta = {}) => {
    if (!backendReady) {
      return null;
    }
    const requestId = ++hoursRequestRef.current;
    const viewVersion = meta.viewVersion ?? viewVersionRef.current;
    const controller = replaceAbortController(hoursAbortRef);
    try {
      const res = await AstroClockAPI.getPlanetaryHours({ ...opts, signal: controller.signal });
      if (!res?.success) return null;
      if (!shouldApplyAstroClockRequest({
        requestId,
        latestRequestId: hoursRequestRef.current,
        viewVersion,
        latestViewVersion: viewVersionRef.current,
      })) {
        return null;
      }
      setHours(res.data);
      return res.data;
    } catch (error) {
      if (controller.signal.aborted) {
        return null;
      }
      if (shouldApplyAstroClockRequest({
        requestId,
        latestRequestId: hoursRequestRef.current,
        viewVersion,
        latestViewVersion: viewVersionRef.current,
      })) {
        console.error('Failed to load Astro Clock planetary hours', error);
      }
      return null;
    } finally {
      if (hoursAbortRef.current === controller) {
        hoursAbortRef.current = null;
      }
    }
  }, [backendReady, replaceAbortController]);

  const syncClockModeAndRefresh = useCallback(async (context, meta = {}) => {
    const viewVersion = meta.viewVersion ?? viewVersionRef.current;
    const requestedSpecialDegrees = Array.isArray(meta.specialDegrees)
      ? meta.specialDegrees
      : specialDegrees;
    const requestedMorin = meta.morin ?? useMorin;
    setClockLoadError('');
    const signal = meta.signal;
    const modeResult = await AstroClockAPI.setMode({ ...context, signal });
    if (modeResult?.success === false) {
      const modeError = new Error(
        modeResult?.error?.message
          || modeResult?.error
          || modeResult?.detail?.message
          || modeResult?.detail
          || 'Failed to change Astro Clock mode.',
      );
      modeError.payload = modeResult;
      throw modeError;
    }
    if (signal?.aborted) {
      throw new DOMException('Mode transition was aborted.', 'AbortError');
    }
    const [nextDashboard, nextHours] = await Promise.all([
      requestDashboard({
        includeModern,
        specialDegrees: requestedSpecialDegrees,
        morin: requestedMorin,
        ...context,
      }, { viewVersion }),
      requestHours(context, { viewVersion }),
    ]);
    return { dashboard: nextDashboard, hours: nextHours };
  }, [includeModern, requestDashboard, requestHours, specialDegrees, useMorin]);

  const refreshDashboard = useCallback(async () => {
    setClockLoadError('');
    await requestDashboard({
      includeModern,
      specialDegrees,
      morin: useMorin,
      ...buildAppliedClockContext(),
    });
  }, [buildAppliedClockContext, includeModern, requestDashboard, specialDegrees, useMorin]);

  const refreshControlBar = useCallback(async () => {
    setLoading(true);
    setClockLoadError('');
    setActionError('');
    try {
      const activeContext = modeRef.current === 'realtime'
        ? buildClockContext({
          mode: 'realtime',
          location: normalizeLocationText(autoLocationRef.current) || undefined,
        })
        : buildAppliedClockContext();
      if (activeContext.mode === 'realtime') {
        const { controller, viewVersion } = beginModeTransition();
        try {
          closeRealtimeStream();
          skipNextRealtimeBootstrapRef.current = true;
          skipNextHoursRefreshRef.current = true;
          await syncClockModeAndRefresh(activeContext, { viewVersion, signal: controller.signal });
          setRealtimeTransportRefreshKey((value) => value + 1);
        } finally {
          completeModeTransition(controller);
        }
        return;
      }
      await Promise.allSettled([
        requestDashboard({ includeModern, specialDegrees, morin: useMorin, ...activeContext }),
        requestHours(activeContext),
      ]);
    } catch (error) {
      if (!isAbortError(error)) {
        console.error('Failed to refresh Astro Clock controls', error);
        setClockLoadError(getActionErrorMessage(error, 'Failed to refresh Astro Clock.'));
      }
    } finally {
      setLoading(false);
    }
  }, [
    beginModeTransition,
    buildAppliedClockContext,
    buildClockContext,
    closeRealtimeStream,
    completeModeTransition,
    includeModern,
    requestDashboard,
    requestHours,
    specialDegrees,
    syncClockModeAndRefresh,
    useMorin,
  ]);

  const controlShellCls = darkMode
    ? 'border border-zinc-700 bg-zinc-900/70 shadow-sm'
    : 'border border-zinc-200 bg-white shadow-sm';
  const isProd = (import.meta && import.meta.env && import.meta.env.PROD) || false;
  const shouldShowPremiumOffer = useCallback(() => shouldGatePremiumFeature({
    packagedRuntime,
    licenseActive,
    licenseChecking,
  }), [packagedRuntime, licenseActive, licenseChecking]);

  const openPremiumOffer = useCallback((featureName = 'Premium workflow') => {
    setShowPromptMenu(false);
    setPremiumOfferFeature(featureName);
  }, []);

  const openPremiumPrompt = useCallback((type) => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('AI prompt utility');
      return;
    }
    openNamePrompt(type);
  }, [openNamePrompt, openPremiumOffer, shouldShowPremiumOffer]);

  const handleTogglePromptMenu = useCallback(() => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('AI prompt utility');
      return;
    }
    setShowPromptMenu((visible) => !visible);
  }, [openPremiumOffer, shouldShowPremiumOffer]);

  const handleCopyForensicCasePrompt = () => openPremiumPrompt('case');

  const handleCopyBirthChartPrompt = () => openPremiumPrompt('natal');

  const handleCopyAssetPrompt = () => openPremiumPrompt('asset');

  // Derived state for unified prompt button "Copied" feedback
  const anyPromptCopied = copiedBirthPrompt || copiedCasePrompt || copiedAssetPrompt;

  const refreshSnaps = useCallback(async ({ silent = false } = {}) => {
    if (!backendReady) {
      return;
    }
    setLoadingSnaps(true);
    if (!silent) setActionError('');
    try {
      const res = await AstroClockAPI.listSnaps();
      if (res?.success) {
        setSnaps(res.items || []);
        setSnapMigrationReport(
          res?.migration_report && typeof res.migration_report === 'object'
            ? res.migration_report
            : null,
        );
        setSnapsLoaded(true);
      }
    } catch (error) {
      console.error('Failed to load Astro Clock snaps', error);
      if (!silent) {
        const message = isTransientFetchError(error) && !backendOffline
          ? ''
          : getActionErrorMessage(error, 'Failed to load Astro Clock snaps.');
        setActionError(message);
      }
    }
    finally { setLoadingSnaps(false); }
  }, [backendOffline, backendReady]);

  // Polling or SSE (realtime only; disabled while manual is pending)
  useEffect(() => {
    let cancelled = false;
    let pollId = null;
    let reconnectTimerId = null;
    let realtimeFetchInFlight = false;
    let queuedRealtimeFetch = false;
    const viewVersion = viewVersionRef.current;
    const skipBootstrap = skipNextRealtimeBootstrapRef.current;
    if (skipBootstrap) {
      skipNextRealtimeBootstrapRef.current = false;
    }
    if (!backendReady) {
      closeRealtimeStream();
      return () => {};
    }
    // Close any existing stream if leaving realtime or awaiting manual input
    if (mode !== 'realtime' || manualPending) {
      closeRealtimeStream();
      return () => {};
    }
    const clearReconnectTimer = () => {
      if (reconnectTimerId) {
        clearTimeout(reconnectTimerId);
        reconnectTimerId = null;
      }
    };
    const stopPolling = () => {
      if (pollId) {
        clearInterval(pollId);
        pollId = null;
      }
    };
    const fetchRealtimeDashboard = async () => {
      if (cancelled || modeRef.current !== 'realtime' || manualPending) return;
      if (realtimeFetchInFlight) {
        queuedRealtimeFetch = true;
        return;
      }
      realtimeFetchInFlight = true;
      try {
        await requestDashboard(
          { includeModern, specialDegrees, morin: useMorin, ...buildClockContext({ mode: 'realtime' }) },
          { viewVersion },
        );
      } finally {
        realtimeFetchInFlight = false;
        if (!cancelled && queuedRealtimeFetch && modeRef.current === 'realtime' && !manualPending) {
          queuedRealtimeFetch = false;
          void fetchRealtimeDashboard();
        }
      }
    };
    const startRealtimeTransport = async () => {
      if (cancelled || modeRef.current !== 'realtime' || manualPending) return;
      clearReconnectTimer();
      stopPolling();
      closeRealtimeStream();
      // SSE disabled when special degrees are in use; fallback to polling
      if (specialDegrees && specialDegrees.length === 0 && !useMorin) {
        const es = await AstroClockAPI.createStream({ includeModern });
        if (cancelled || modeRef.current !== 'realtime' || manualPending) {
          try { es?.close?.(); } catch (_) {}
          return;
        }
        if (es) {
          streamRef.current = es;
          setIsStreaming(true);
          es.onmessage = () => { void fetchRealtimeDashboard(); };
          es.onerror = () => {
            if (streamRef.current === es) {
              try { es.close(); } catch (_) {}
              streamRef.current = null;
            }
            setIsStreaming(false);
            if (cancelled || modeRef.current !== 'realtime' || manualPending) return;
            clearReconnectTimer();
            reconnectTimerId = setTimeout(() => {
              reconnectTimerId = null;
              void startRealtimeTransport();
            }, 1000);
          };
          return;
        }
      }
      pollId = setInterval(() => {
        void fetchRealtimeDashboard();
      }, 10000);
    };
    // Avoid clearing data on entry; prevents visible flicker while the first fetch completes
    const start = async () => {
      if (!skipBootstrap) {
        // Ensure backend is in realtime mode before streaming/fetching
        try { await AstroClockAPI.setMode(buildClockContext({ mode: 'realtime', houseSystem })); } catch(_){}
        if (cancelled) return;
        // Get the first dashboard payload on screen before starting secondary realtime plumbing.
        await fetchRealtimeDashboard();
        if (cancelled) return;
      }
      await startRealtimeTransport();
    };
    void start();
    return () => {
      cancelled = true;
      clearReconnectTimer();
      stopPolling();
      closeRealtimeStream();
    };
  }, [backendReady, buildClockContext, closeRealtimeStream, includeModern, houseSystem, specialDegrees, mode, manualPending, requestDashboard, realtimeTransportRefreshKey, useMorin]);

  // Manual mode: refresh dashboard when includeModern toggles
  useEffect(() => {
    if (!backendReady) return;
    if (mode !== 'manual' || manualPending) return;
    if (skipNextManualDashboardRefreshRef.current) {
      skipNextManualDashboardRefreshRef.current = false;
      return;
    }
    (async () => {
      await requestDashboard({
        includeModern,
        specialDegrees,
        morin: useMorin,
        ...buildAppliedClockContextRef.current({ mode: 'manual' }),
      });
    })();
  }, [
    activeManualIso,
    activeSnapId,
    backendReady,
    houseSystem,
    includeModern,
    manualPending,
    mode,
    requestDashboard,
    specialDegrees,
    useMorin,
  ]);

  // Load planetary hours and keep in sync with stream payload when present; fallback to periodic refresh
  useEffect(() => {
    if (!backendReady) return;
    if (manualPending) return;
    if (mode === 'manual' && !activeManualIso) return;
    let cancelled = false;
    const viewVersion = viewVersionRef.current;
    const fetchHours = async () => {
      if (cancelled) return;
      await requestHours(buildAppliedClockContextRef.current(), { viewVersion });
    };
    if (skipNextHoursRefreshRef.current) {
      skipNextHoursRefreshRef.current = false;
    } else {
      fetchHours();
    }
    const id = setInterval(fetchHours, 60000);
    return () => { cancelled = true; clearInterval(id); };
  }, [activeManualIso, activeSnapId, backendReady, houseSystem, manualPending, mode, requestHours]);

  useEffect(() => {
    if (!activeManualIso || (manualDate && manualTime)) return;
    syncManualSnapshotInputs(activeManualIso, {
      location: data?.location || manualLocationRef.current,
      timezone: resolveAstroClockTimezone(data?.timezone, data?.timezone_label),
    });
  }, [activeManualIso, data?.location, data?.timezone, data?.timezone_label, manualDate, manualTime, syncManualSnapshotInputs]);

  useEffect(() => {
    if (mode !== 'realtime' || manualPending || !data?.timestamp) return;
    syncManualSnapshotInputs(data.timestamp, {
      location: data?.location || manualLocationRef.current,
      timezone: resolveAstroClockTimezone(data?.timezone, data?.timezone_label),
    });
  }, [mode, manualPending, data?.timestamp, data?.location, data?.timezone, data?.timezone_label, syncManualSnapshotInputs]);

  // When stream payload includes planetary_hours, use it
  useEffect(() => {
    if (data?.planetary_hours) {
      setHours(data.planetary_hours);
    }
  }, [data?.planetary_hours]);

  const applyManual = async () => {
    if (!manualDate || !manualTime || loadingRef.current) return;
    const wallTime = normalizeLocalDateTimeInput(`${manualDate}T${manualTime}`);
    if (!wallTime) {
      setActionError('Enter a complete, valid local date and time.');
      return;
    }
    const selectedResolutionCandidate = manualTimeResolution?.candidates?.find(
      (candidate) => candidate.key === manualTimeResolution.selectedKey,
    );
    if (
      manualTimeResolution?.kind === 'ambiguous'
      && manualTimeResolution.wallTime === wallTime
      && !selectedResolutionCandidate
    ) {
      setActionError('Choose which UTC offset applies to this repeated local time.');
      return;
    }
    const iso = (
      manualTimeResolution?.wallTime === wallTime && selectedResolutionCandidate?.localDatetime
        ? selectedResolutionCandidate.localDatetime
        : `${wallTime}:00`
    );
    const previousMode = modeRef.current || mode;
    const previousManualIso = activeManualIsoRef.current;
    const previousManualContext = activeManualContextRef.current;
    setLoading(true);
    setActionError('');
    const { controller, viewVersion } = beginModeTransition();
    try {
      const manualContext = buildClockContext({
        mode: 'manual',
        datetime: iso,
        location: manualLocation || data?.location || autoLocation || ASTRO_CLOCK_DEFAULT_LOCATION,
      });
      activeManualContextRef.current = manualContext;
      closeRealtimeStream();
      skipNextManualDashboardRefreshRef.current = true;
      skipNextHoursRefreshRef.current = true;
      modeRef.current = 'manual';
      activeManualIsoRef.current = iso;
      setMode('manual');
      setActiveManualIso(iso);
      await syncClockModeAndRefresh(manualContext, { viewVersion, signal: controller.signal });
      setActiveSnapId('');
      setManualTimeResolution(null);
    } catch (error) {
      modeRef.current = previousMode;
      activeManualIsoRef.current = previousManualIso;
      activeManualContextRef.current = previousManualContext;
      setMode(previousMode);
      setActiveManualIso(previousManualIso);
      if (isAbortError(error) || controller.signal.aborted) return;
      console.error('Failed to apply Astro Clock manual mode', error);
      const resolution = extractLocalTimeResolution(error, wallTime);
      if (resolution?.kind === 'ambiguous') {
        setManualTimeResolution({
          ...resolution,
          wallTime,
          selectedKey: '',
        });
        setActionError(resolution.message);
        return;
      }
      if (resolution?.kind === 'nonexistent') {
        setManualTimeResolution(null);
        setActionError(resolution.message);
        return;
      }
      setActionError(getActionErrorMessage(error, 'Failed to switch Astro Clock into manual mode.'));
    } finally {
      completeModeTransition(controller);
    }
  };

  // Jump the main clock to a specific ISO timestamp (from Transits modal)
  const jumpToIso = useCallback(async (arg) => {
    const payload = (arg && typeof arg === 'object') ? arg : { iso: arg };
    const iso = payload.iso;
    if (!iso || typeof iso !== 'string') return;
    setLoading(true);
    setActionError('');
    const { controller, viewVersion } = beginModeTransition();
    try {
      setActiveSnapId('');
      // If election provided a specific location/timezone, honor them
      const jumpLocation = (typeof payload.location === 'string' && payload.location.trim()) ? payload.location.trim() : (manualLocation || autoLocation || ASTRO_CLOCK_DEFAULT_LOCATION);
      const jumpTimezone = (typeof payload.timezone === 'string' && payload.timezone.trim()) ? payload.timezone.trim() : undefined;
      const jumpLatitude = finiteNumberOrUndefined(payload.latitude);
      const jumpLongitude = finiteNumberOrUndefined(payload.longitude);
      const manualContext = buildClockContext({
        mode: 'manual',
        datetime: iso,
        location: jumpLocation,
        timezone: jumpTimezone,
        latitude: jumpLatitude,
        longitude: jumpLongitude,
      });
      activeManualContextRef.current = manualContext;
      syncManualSnapshotInputs(iso, { location: jumpLocation, timezone: jumpTimezone });
      closeRealtimeStream();
      skipNextManualDashboardRefreshRef.current = true;
      skipNextHoursRefreshRef.current = true;
      modeRef.current = 'manual';
      activeManualIsoRef.current = iso;
      setMode('manual');
      setActiveManualIso(iso);
      await syncClockModeAndRefresh(manualContext, { viewVersion, signal: controller.signal });
    } catch (error) {
      if (isAbortError(error) || controller.signal.aborted) return;
      console.error('Failed to jump Astro Clock to manual snapshot', error);
      setActionError(getActionErrorMessage(error, 'Failed to switch Astro Clock into manual mode.'));
      throw error;
    } finally {
      completeModeTransition(controller);
    }
  }, [autoLocation, beginModeTransition, buildClockContext, closeRealtimeStream, completeModeTransition, manualLocation, syncClockModeAndRefresh, syncManualSnapshotInputs]);

  const resumeRealtime = useCallback(async () => {
    setLoading(true);
    const ref = featurePauseRef.current;
    let success = false;
    const { controller, viewVersion } = beginModeTransition();
    const realtimeContext = buildClockContext({
      mode: 'realtime',
      location: normalizeLocationText(autoLocationRef.current) || undefined,
    });
    // Ensure UI state moves to realtime even if network requests fail
    modeRef.current = 'realtime';
    activeManualIsoRef.current = null;
    activeManualContextRef.current = null;
    setActiveSnapId('');
    setMode('realtime');
    setActiveManualIso(null);
    try {
      skipNextRealtimeBootstrapRef.current = true;
      skipNextHoursRefreshRef.current = true;
      const { dashboard: nextDashboard } = await syncClockModeAndRefresh(realtimeContext, { viewVersion, signal: controller.signal });
      if (nextDashboard?.timestamp) {
        syncManualSnapshotInputs(nextDashboard.timestamp, {
          location: nextDashboard.location,
          timezone: resolveAstroClockTimezone(nextDashboard.timezone, nextDashboard.timezone_label),
        });
      }
      success = true;
    } catch (error) {
      if (isAbortError(error) || controller.signal.aborted) return;
      console.error('Failed to resume Astro Clock realtime mode', error);
      setActionError(getActionErrorMessage(error, 'Failed to switch Astro Clock into realtime mode.'));
    } finally {
      completeModeTransition(controller);
      if (success) {
        ref.resumeNeeded = false;
        ref.snapshotIso = null;
        ref.pausing = false;
        ref.pausePromise = null;
        if (ref.count !== 0) ref.count = 0;
      }
    }
  }, [beginModeTransition, buildClockContext, completeModeTransition, syncClockModeAndRefresh, syncManualSnapshotInputs]);

  const enterManualMode = useCallback(async () => {
    if (modeRef.current === 'manual' && !activeManualIsoRef.current) {
      return;
    }
    const target = resolveManualSnapshotTarget({
      activeManualIso: activeManualIsoRef.current,
      dataTimestamp: data?.timestamp,
      dataLocation: data?.location,
      manualLocation: manualLocationRef.current,
      timezone: data?.timezone,
      timezoneLabel: data?.timezone_label,
    });
    if (modeRef.current === 'manual' && activeManualIsoRef.current) {
      syncManualSnapshotInputs(target.iso, { location: target.location, timezone: target.timezone });
      return;
    }
    await jumpToIso(target);
  }, [data?.location, data?.timestamp, data?.timezone, data?.timezone_label, jumpToIso, syncManualSnapshotInputs]);

  const pauseRealtimeForFeature = useCallback(async () => {
    const ref = featurePauseRef.current;
    ref.count += 1;
    if (mode !== 'realtime') {
      return;
    }
    if (ref.resumeNeeded) {
      if (ref.pausePromise) {
        try { await ref.pausePromise; } catch (_) {}
      }
      return;
    }
    if (ref.pausing && ref.pausePromise) {
      try { await ref.pausePromise; } catch (_) {}
      return;
    }
    const snapshotIso = (data && data.timestamp) ? data.timestamp : new Date().toISOString();
    const snapshotLocation = (data && data.location) ? data.location : (autoLocation || manualLocation || ASTRO_CLOCK_DEFAULT_LOCATION);
    const snapshotTimezone = resolveAstroClockTimezone(data?.timezone, data?.timezone_label);
    const snapshotLatitude = finiteNumberOrUndefined(data?.latitude);
    const snapshotLongitude = finiteNumberOrUndefined(data?.longitude);
    ref.pausing = true;
    ref.snapshotIso = null;
    ref.pausePromise = (async () => {
      try {
        await jumpToIso({
          iso: snapshotIso,
          location: snapshotLocation,
          timezone: snapshotTimezone,
          latitude: snapshotLatitude,
          longitude: snapshotLongitude,
        });
        ref.resumeNeeded = true;
        ref.snapshotIso = snapshotIso;
      } finally {
        ref.pausing = false;
        ref.pausePromise = null;
      }
    })();
    try {
      await ref.pausePromise;
    } catch (err) {
      console.error('Failed to pause realtime for feature', err);
    }
  }, [autoLocation, mode, data, manualLocation, jumpToIso]);

  const resumeRealtimeAfterFeature = useCallback(async () => {
    const ref = featurePauseRef.current;
    if (ref.count > 0) {
      ref.count -= 1;
    }
    if (ref.count > 0) {
      return;
    }
    if (ref.pausePromise) {
      try { await ref.pausePromise; } catch (_) {}
    }
    if (!ref.resumeNeeded) {
      ref.snapshotIso = null;
      ref.pausePromise = null;
      ref.pausing = false;
      return;
    }
    const snapshotIso = ref.snapshotIso;
    if (mode !== 'manual') {
      ref.resumeNeeded = false;
      ref.snapshotIso = null;
      ref.pausePromise = null;
      ref.pausing = false;
      return;
    }
    if (snapshotIso && activeManualIso && snapshotIso !== activeManualIso) {
      ref.resumeNeeded = false;
      ref.snapshotIso = null;
      ref.pausePromise = null;
      ref.pausing = false;
      return;
    }
    try {
      await resumeRealtime();
    } catch (err) {
      console.error('Failed to resume realtime after feature', err);
    } finally {
      ref.resumeNeeded = false;
      ref.snapshotIso = null;
      ref.pausePromise = null;
      ref.pausing = false;
    }
  }, [mode, activeManualIso, resumeRealtime]);

  const handleOpenForensic = useCallback(async () => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('Forensic');
      return;
    }
    setOpeningForensic(true);
    try {
      await pauseRealtimeForFeature();
    } catch (err) {
      console.error('Failed to pause realtime for forensic view', err);
    } finally {
      setOpeningForensic(false);
      setShowForensic(true);
    }
  }, [openPremiumOffer, pauseRealtimeForFeature, shouldShowPremiumOffer]);

  const handleCloseForensic = useCallback(() => {
    setOpeningForensic(false);
    setShowForensic(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after forensic view', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenTraitProfile = useCallback(async () => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('Trait Profile');
      return;
    }
    try {
      await pauseRealtimeForFeature();
    } catch (err) {
      console.error('Failed to pause realtime for trait profile', err);
    } finally {
      setShowTraits(true);
    }
  }, [openPremiumOffer, pauseRealtimeForFeature, shouldShowPremiumOffer]);

  const handleCloseTraitProfile = useCallback(() => {
    setShowTraits(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after trait profile', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenSynastry = useCallback(async () => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('Synastry');
      return;
    }
    setShowSynastry(true);
  }, [openPremiumOffer, shouldShowPremiumOffer]);

  const handleCloseSynastry = useCallback(() => {
    setShowSynastry(false);
  }, []);

  const handleOpenTransits = useCallback(() => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('Transits');
      return;
    }
    setShowTransits(true);
    pauseRealtimeForFeature().catch((err) => { console.error('Failed to pause realtime for transits', err); });
  }, [openPremiumOffer, pauseRealtimeForFeature, shouldShowPremiumOffer]);

  const handleCloseTransits = useCallback(() => {
    setShowTransits(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after transits', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenElection = useCallback(() => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('Election');
      return;
    }
    setShowElection(true);
    pauseRealtimeForFeature().catch((err) => { console.error('Failed to pause realtime for election scanner', err); });
  }, [openPremiumOffer, pauseRealtimeForFeature, shouldShowPremiumOffer]);

  const handleCloseElection = useCallback(() => {
    setShowElection(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after election scanner', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenAstrocartography = useCallback(() => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('Astrocartography');
      return;
    }
    setShowAstrocartography(true);
    pauseRealtimeForFeature().catch((err) => { console.error('Failed to pause realtime for astrocartography', err); });
  }, [openPremiumOffer, pauseRealtimeForFeature, shouldShowPremiumOffer]);

  const handleCloseAstrocartography = useCallback(() => {
    setShowAstrocartography(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after astrocartography', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenChineseAstrology = useCallback(() => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('Chinese Astrology');
      return;
    }
    setShowChineseAstrology(true);
    pauseRealtimeForFeature().catch((err) => { console.error('Failed to pause realtime for Chinese Astrology', err); });
  }, [openPremiumOffer, pauseRealtimeForFeature, shouldShowPremiumOffer]);

  const handleCloseChineseAstrology = useCallback(() => {
    setShowChineseAstrology(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after Chinese Astrology', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenBirthCertification = useCallback(() => {
    if (shouldShowPremiumOffer()) {
      openPremiumOffer('Certification');
      return;
    }
    setShowBirthCertification(true);
    pauseRealtimeForFeature().catch((err) => { console.error('Failed to pause realtime for Certification', err); });
  }, [openPremiumOffer, pauseRealtimeForFeature, shouldShowPremiumOffer]);

  const handleCloseBirthCertification = useCallback(() => {
    setShowBirthCertification(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after Certification', err); });
  }, [resumeRealtimeAfterFeature]);

  // Snap actions
  const doSnap = () => {
    if (snapSaveInFlightRef.current) {
      return snapSaveInFlightRef.current;
    }

    const idempotencyKey = createSnapIdempotencyKey();
    setSnapSaving(true);
    const pendingSave = (async () => {
      // Avoid window.prompt in packaged builds; generate a friendly default label
      const ts = data?.timestamp || new Date().toISOString();
      const existingSnapContext = getSnapContext(activeSnapId);
      const loc = existingSnapContext?.location || data?.location || autoLocation || manualLocation || '';
      const defaultLabel = `Snap ${ts.replace('T',' ').replace('Z','')}${loc? ` - ${loc}`:''}`;
      const label = defaultLabel;
      setActionError('');
      try {
        const activeMode = modeRef.current || mode;
        const appliedTimezone = resolveAstroClockTimezone(data?.timezone, data?.timezone_label);
        const appliedLatitude = finiteNumberOrUndefined(data?.latitude);
        const appliedLongitude = finiteNumberOrUndefined(data?.longitude);
        const appliedLocation =
          existingSnapContext?.location ||
          data?.location ||
          (activeMode === 'manual' ? manualLocation : autoLocation);
        const snapContext = buildClockContext({
          mode: activeMode,
          datetime: activeMode === 'manual'
            ? (activeManualIsoRef.current || data?.timestamp)
            : undefined,
          location: appliedLocation,
          timezone: appliedTimezone,
          latitude: appliedLatitude,
          longitude: appliedLongitude,
          houseSystem,
        });
        const res = await AstroClockAPI.createSnap({
          label,
          includeModern,
          specialDegrees,
          dashboard: data,
          idempotencyKey,
          ...snapContext,
        });
        const nextSnapId = String(res?.data?.id || res?.id || '');
        if (nextSnapId) setActiveSnapId(nextSnapId);
        await refreshSnaps();
        return {
          success: true,
          id: nextSnapId,
          label: String(res?.data?.label || label),
        };
      } catch (error) {
        console.error('Failed to create Astro Clock snap', error);
        const message = getActionErrorMessage(error, 'Failed to save this chart as a snap.');
        setActionError(message);
        return {
          success: false,
          error: message,
        };
      }
    })();
    const guardedSave = pendingSave.finally(() => {
      if (snapSaveInFlightRef.current === guardedSave) {
        snapSaveInFlightRef.current = null;
        setSnapSaving(false);
      }
    });
    snapSaveInFlightRef.current = guardedSave;
    return guardedSave;
  };

  const loadSnap = async (snap) => {
    if (!snap) return;
    if (isSavedSnapReviewRequired(snap) || String(snap?.superseded_by || '').trim()) {
      setActionError(
        String(snap?.superseded_by || '').trim()
          ? 'This original saved chart was superseded. Load its corrected copy instead.'
          : 'This saved chart needs context review. Correct it and load the corrected copy instead.',
      );
      return;
    }
    setLoading(true);
    setActionError('');
    const { controller, viewVersion } = beginModeTransition();
    try {
      const snapId = String(snap.id || '');
      if (!snapId) throw new Error('The saved chart has no stable identifier and cannot be verified.');
      let resolvedSnap = snap;
      try {
        const detail = await AstroClockAPI.getSnap(snapId, { signal: controller.signal });
        if (controller.signal.aborted) {
          throw new DOMException('Snap load was aborted.', 'AbortError');
        }
        if (!detail?.success || !detail?.snap) {
          throw new Error(
            detail?.error || detail?.detail || 'The saved chart details could not be verified.',
          );
        }
        resolvedSnap = detail.snap;
      } catch (detailError) {
        if (isAbortError(detailError) || controller.signal.aborted) throw detailError;
        throw new Error(
          `The saved chart could not be verified and was not loaded. ${
            getActionErrorMessage(detailError, 'Refresh Saved Snaps and try again.')
          }`,
        );
      }
      if (controller.signal.aborted) {
        throw new DOMException('Snap load was aborted.', 'AbortError');
      }
      if (
        isSavedSnapReviewRequired(resolvedSnap)
        || String(resolvedSnap?.superseded_by || '').trim()
      ) {
        throw new Error(
          String(resolvedSnap?.superseded_by || '').trim()
            ? 'This original saved chart was superseded. Load its corrected copy instead.'
            : 'This saved chart needs context review. Correct it and load the corrected copy instead.',
        );
      }
      const iso = resolvedSnap?.effective_datetime || snap.effective_datetime;
      if (!iso || Number.isNaN(new Date(iso).getTime())) {
        throw new Error(
          'This saved chart has no confirmed date and time. Correct its context before loading it.',
        );
      }
      const location = resolvedSnap?.location || snap.location;
      const nextSpecialDegrees = Array.isArray(resolvedSnap?.special_degrees)
        ? resolvedSnap.special_degrees
        : (Array.isArray(snap.special_degrees) ? snap.special_degrees : specialDegrees);
      const snapTimezone = resolveAstroClockTimezone(
        resolvedSnap?.timezone || resolvedSnap?.dashboard?.timezone,
        resolvedSnap?.timezone_label || resolvedSnap?.dashboard?.timezone_label,
      );
      const snapLatitude = Number.isFinite(Number(resolvedSnap?.dashboard?.latitude ?? resolvedSnap?.latitude))
        ? Number(resolvedSnap?.dashboard?.latitude ?? resolvedSnap?.latitude)
        : undefined;
      const snapLongitude = Number.isFinite(Number(resolvedSnap?.dashboard?.longitude ?? resolvedSnap?.longitude))
        ? Number(resolvedSnap?.dashboard?.longitude ?? resolvedSnap?.longitude)
        : undefined;
      const manualContext = buildClockContext({
        mode: 'manual',
        datetime: iso,
        location,
        timezone: snapTimezone,
        latitude: snapLatitude,
        longitude: snapLongitude,
      });
      activeManualContextRef.current = manualContext;
      syncManualSnapshotInputs(iso, { location, timezone: snapTimezone });
      closeRealtimeStream();
      skipNextManualDashboardRefreshRef.current = true;
      skipNextHoursRefreshRef.current = true;
      modeRef.current = 'manual';
      activeManualIsoRef.current = iso;
      setMode('manual');
      setActiveManualIso(iso);
      await syncClockModeAndRefresh(manualContext, {
        viewVersion,
        signal: controller.signal,
        specialDegrees: nextSpecialDegrees,
      });
      if (Array.isArray(resolvedSnap?.special_degrees)) setSpecialDegrees(resolvedSnap.special_degrees);
      setActiveSnapId(snapId);
    } catch (error) {
      if (isAbortError(error) || controller.signal.aborted) return;
      console.error('Failed to load Astro Clock snap', error);
      setActionError(getActionErrorMessage(error, 'Failed to load the selected snap.'));
      throw error;
    } finally {
      completeModeTransition(controller);
    }
  };

  const deleteSnap = async (id) => {
    setActionError('');
    try {
      await AstroClockAPI.deleteSnap(id);
      const deletedId = String(id || '');
      setSnaps((currentSnaps) => (
        (Array.isArray(currentSnaps) ? currentSnaps : []).filter(
          (snap) => String(snap?.id || '') !== deletedId,
        )
      ));
      setActiveSnapId((currentId) => (
        String(currentId || '') === deletedId ? '' : currentId
      ));
      await refreshSnaps();
    } catch (error) {
      console.error('Failed to delete Astro Clock snap', error);
      setActionError(getActionErrorMessage(error, 'Failed to delete the selected snap.'));
    }
  };

  const handleHouseSystemChange = async (code) => {
    try {
      const viewVersion = beginViewVersion();
      setHouseSystem(code);
      try { localStorage.setItem('vox_stella_house_system_code', code); } catch(_) {}
      // Update backend engine setting according to current mode
      if (mode === 'manual') {
        // Manual mode requires datetime (and optional location)
        const iso = activeManualIso;
        if (!iso) {
          // If manual time isn’t set yet, skip engine update; UI will apply when time is set
        } else {
          await AstroClockAPI.setMode(buildClockContext({
            mode: 'manual',
            datetime: iso,
            location: manualLocation || data?.location || autoLocation || ASTRO_CLOCK_DEFAULT_LOCATION,
            houseSystem: code,
          }));
        }
      } else {
        await AstroClockAPI.setMode(buildClockContext({ mode: 'realtime', houseSystem: code }));
      }
      // Refresh dashboard and hours
      const nextContext = buildAppliedClockContext({
        houseSystem: code,
        mode: mode === 'manual' ? 'manual' : 'realtime',
      });
      await Promise.allSettled([
        requestDashboard({ includeModern, specialDegrees, morin: useMorin, ...nextContext }, { viewVersion }),
        requestHours(nextContext, { viewVersion }),
      ]);
    } catch(_) {}
  };

  useEffect(() => {
    if (!backendReady) return;
    refreshSnaps({ silent: true });
  }, [backendReady, refreshSnaps]);

  const topBarDateValue = formatControlDateLabel(manualDate);
  const topBarTimeValue = manualTime || '--:--';
  const rawTopBarLocation = mode === 'realtime'
    ? (autoLocation || data?.location || ASTRO_CLOCK_DEFAULT_LOCATION)
    : (manualLocation || data?.location || 'Set location');
  const topBarLocationValue = typeof rawTopBarLocation === 'string' && rawTopBarLocation.trim()
    ? rawTopBarLocation.trim()
    : 'Set location';
  const activeCompassLocation = topBarLocationValue !== 'Set location' ? topBarLocationValue : undefined;
  const activeCompassTimestamp = mode === 'manual'
    ? (activeManualIso || data?.timestamp)
    : data?.timestamp;
  const topBarTimezoneLabel = formatAstroClockTimezoneLabel({
    timestamp: data?.timestamp || activeManualIso || undefined,
    timezone: data?.timezone,
    timezoneLabel: data?.timezone_label,
  });
  const topBarUtcOffset = extractUtcOffsetLabel(topBarTimezoneLabel);
  const topBarStatusLabel = mode === 'realtime'
    ? 'auto'
    : (activeManualIso ? 'snapshot' : 'draft');
  const suppressRealtimeBackendDropBanner = mode === 'realtime' && Boolean(data);
  const refreshButtonDisabled = loading || !backendReady || (mode === 'manual' && (!manualDate || !manualTime));
  const applyButtonDisabled = loading || !backendReady || mode !== 'manual' || (!manualDate || !manualTime);
  const featureActionsLocked = shouldGatePremiumFeature({ packagedRuntime, licenseActive, licenseChecking });
  const featureActionBaseCls = 'inline-flex min-h-9 items-center justify-center rounded-full border px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] shadow-sm transition-colors';
  const featureActionCls = featureActionsLocked
    ? `${featureActionBaseCls} border-red-600 bg-red-600 text-white hover:border-red-700 hover:bg-red-700 dark:border-red-500 dark:bg-red-500 dark:hover:border-red-400 dark:hover:bg-red-400`
    : `${featureActionBaseCls} border-zinc-900 bg-zinc-900 text-white hover:border-zinc-800 hover:bg-zinc-800 dark:border-white dark:bg-white dark:text-zinc-900 dark:hover:border-zinc-200 dark:hover:bg-zinc-200`;
  const featureActionTitle = featureActionsLocked ? 'Premium feature - unlock Vox Stella to use this workflow' : undefined;
  const copyPromptControlCls = featureActionsLocked
    ? 'border-red-600 bg-red-600 text-white hover:border-red-700 hover:bg-red-700 dark:border-red-500 dark:bg-red-500'
    : darkMode
      ? 'border-zinc-700 bg-zinc-950/60 text-zinc-100 hover:border-zinc-500 hover:bg-zinc-900'
      : 'border-zinc-200 bg-white text-zinc-900 hover:border-zinc-400 hover:bg-zinc-50';

  return (
    <div className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8`}>
      <div className="mb-4 grid min-w-0 grid-cols-[minmax(0,1fr)] gap-x-4 gap-y-3 lg:gap-x-5 xl:grid-cols-[minmax(180px,0.78fr)_minmax(0,2.55fr)_minmax(260px,1.22fr)] xl:items-center">
        <button onClick={() => setCurrentView('dashboard')} className="flex items-center self-start text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 xl:col-start-1 xl:col-end-2">
          <span className="mr-2">←</span> Back to Dashboard
        </button>
        <div className="flex min-w-0 flex-wrap items-center justify-start gap-2 xl:col-start-2 xl:col-end-4 xl:justify-end">
          <button
            type="button"
            className={featureActionCls}
            style={monoStyle}
            title={featureActionTitle}
            onClick={handleOpenSynastry}
          >
            Synastry
          </button>
          <button
            type="button"
            className={featureActionCls}
            style={monoStyle}
            title={featureActionTitle}
            onClick={handleOpenTraitProfile}
          >
            Trait Profile
          </button>
          <button
            type="button"
            className={featureActionCls}
            style={monoStyle}
            title={featureActionTitle}
            onClick={handleOpenTransits}
          >
            Transits
          </button>
          <button
            type="button"
            className={featureActionCls}
            style={monoStyle}
            title={featureActionTitle}
            onClick={handleOpenAstrocartography}
          >
            Astrocartography
          </button>
          <button
            type="button"
            className={featureActionCls}
            style={monoStyle}
            title={featureActionTitle}
            onClick={handleOpenElection}
          >
            Election
          </button>
          <button
            type="button"
            className={featureActionCls}
            style={monoStyle}
            title={featureActionTitle}
            onClick={handleOpenChineseAstrology}
          >
            Chinese Astrology
          </button>
          <button
            type="button"
            className={featureActionCls}
            style={monoStyle}
            title={featureActionTitle}
            onClick={handleOpenForensic}
          >
            Forensic
          </button>
          <button
            type="button"
            className={featureActionCls}
            style={monoStyle}
            title={featureActionTitle}
            onClick={handleOpenBirthCertification}
          >
            Certification
          </button>
        </div>
      </div>

      {/* Controls */}
      <div
        data-testid="astro-clock-control-strip"
        className={`mb-6 w-full min-w-0 max-w-full rounded-[24px] px-4 py-2.5 sm:px-5 ${controlShellCls}`}
      >
        <div className="sr-only" aria-hidden="true">
          <input
            type="date"
            value={manualDate}
            onChange={e => {
              setManualDate(e.target.value);
              setManualTimeResolution(null);
            }}
            tabIndex={-1}
          />
          <input
            type="time"
            lang="en-GB"
            inputMode="numeric"
            step="60"
            placeholder="HH:MM"
            value={manualTime}
            onChange={e => {
              setManualTime(e.target.value);
              setManualTimeResolution(null);
            }}
            tabIndex={-1}
          />
        </div>

        <div className="flex min-w-0 flex-col gap-2.5 xl:grid xl:grid-cols-[auto_minmax(0,1fr)_auto] xl:items-center xl:gap-2.5">
          <div className="flex flex-wrap items-center gap-2.5 xl:flex-nowrap xl:shrink-0">
            <div className={`inline-flex rounded-full p-1 ${darkMode ? 'bg-zinc-900' : 'bg-zinc-100'}`}>
              <button
                onClick={resumeRealtime}
                disabled={!backendReady}
                className={`rounded-full px-3 py-[0.375rem] text-[11px] font-medium disabled:cursor-not-allowed disabled:opacity-60 ${
                  mode === 'realtime'
                    ? 'bg-zinc-900 text-white shadow-sm dark:bg-white dark:text-zinc-900'
                    : darkMode
                      ? 'text-zinc-300 hover:text-white'
                      : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                Realtime
              </button>
              <button
                onClick={enterManualMode}
                disabled={!backendReady}
                className={`rounded-full px-3 py-[0.375rem] text-[11px] font-medium disabled:cursor-not-allowed disabled:opacity-60 ${
                  mode === 'manual'
                    ? 'bg-zinc-900 text-white shadow-sm dark:bg-white dark:text-zinc-900'
                    : darkMode
                      ? 'text-zinc-300 hover:text-white'
                      : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                Manual
              </button>
            </div>

            <div className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[9px] font-medium capitalize ${
              darkMode ? 'border-zinc-700 bg-zinc-950/60 text-zinc-300' : 'border-zinc-200 bg-white text-zinc-600'
            }`}>
              <span className={`h-2.5 w-2.5 rounded-full ${mode === 'realtime' ? 'bg-emerald-500' : 'bg-zinc-400'} ${mode === 'realtime' && isStreaming ? 'animate-pulse' : ''}`} />
              {topBarStatusLabel}
            </div>
          </div>

          <div className={`grid min-w-0 gap-2.5 sm:grid-cols-2 xl:grid-cols-[minmax(150px,0.68fr)_minmax(132px,0.46fr)_minmax(220px,1fr)] xl:border-l xl:pl-4 ${darkMode ? 'xl:border-zinc-800' : 'xl:border-zinc-200'}`}>
            <div className="min-w-0">
              <div className={`text-[8px] font-semibold uppercase tracking-[0.18em] ${darkMode ? 'text-zinc-500' : 'text-zinc-400'}`} style={monoStyle}>
                Date
              </div>
              {mode === 'manual' ? (
                <input
                  id="astroclock-manual-date"
                  type="date"
                  value={manualDate}
                  onChange={e => {
                    setManualDate(e.target.value);
                    setManualTimeResolution(null);
                  }}
                  className={`mt-1 w-full rounded-2xl border px-3 py-1.5 text-[13px] ${darkMode ? 'border-zinc-700 bg-zinc-900/70 text-zinc-100' : 'border-zinc-200 bg-white text-zinc-900'}`}
                />
              ) : (
                <div className={`mt-1 text-[1.3rem] font-medium leading-none tracking-[-0.035em] ${darkMode ? 'text-zinc-100' : 'text-zinc-900'}`} style={serifStyle}>
                  {topBarDateValue}
                </div>
              )}
            </div>

            <div className="min-w-0">
              <div className={`text-[8px] font-semibold uppercase tracking-[0.18em] ${darkMode ? 'text-zinc-500' : 'text-zinc-400'}`} style={monoStyle}>
                Time
              </div>
              {mode === 'manual' ? (
                <input
                  id="astroclock-manual-time"
                  type="time"
                  lang="en-GB"
                  inputMode="numeric"
                  step="60"
                  placeholder="HH:MM"
                  value={manualTime}
                  onChange={e => {
                    setManualTime(e.target.value);
                    setManualTimeResolution(null);
                  }}
                  className={`mt-1 w-full rounded-2xl border px-3 py-1.5 text-[13px] ${darkMode ? 'border-zinc-700 bg-zinc-900/70 text-zinc-100' : 'border-zinc-200 bg-white text-zinc-900'}`}
                />
              ) : (
                <div className={`mt-1 flex flex-wrap items-end gap-2 ${darkMode ? 'text-zinc-100' : 'text-zinc-900'}`}>
                  <span className="text-[1.3rem] font-medium leading-none tracking-[-0.035em]" style={serifStyle}>
                    {topBarTimeValue}
                  </span>
                  {topBarUtcOffset ? (
                    <span className={`pb-0.5 text-[10px] ${darkMode ? 'text-zinc-400' : 'text-zinc-500'}`} style={monoStyle}>
                      {topBarUtcOffset}
                    </span>
                  ) : null}
                </div>
              )}
            </div>

            <div className="min-w-0 sm:col-span-2 xl:col-span-1">
              <div className={`text-[8px] font-semibold uppercase tracking-[0.18em] ${darkMode ? 'text-zinc-500' : 'text-zinc-400'}`} style={monoStyle}>
                Location
              </div>
              {mode === 'manual' ? (
                <input
                  id="astroclock-manual-location"
                  type="text"
                  placeholder="e.g., London, UK"
                  value={manualLocation}
                  onChange={e => {
                    const nextLocation = e.target.value;
                    manualLocationRef.current = nextLocation;
                    setManualLocation(nextLocation);
                    setManualTimeResolution(null);
                  }}
                  className={`mt-1 w-full rounded-2xl border px-3 py-1.5 text-[13px] ${darkMode ? 'border-zinc-700 bg-zinc-900/70 text-zinc-100' : 'border-zinc-200 bg-white text-zinc-900'}`}
                />
              ) : (
                <>
                  <input
                    id="astroclock-auto-location"
                    type="text"
                    placeholder={ASTRO_CLOCK_DEFAULT_LOCATION}
                    value={autoLocation}
                    onChange={e => {
                      const nextLocation = e.target.value;
                      autoLocationRef.current = nextLocation;
                      setAutoLocation(nextLocation);
                    }}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !loadingRef.current) {
                        e.currentTarget.blur();
                        refreshControlBar();
                      }
                    }}
                    className={`mt-1 w-full rounded-2xl border px-3 py-1.5 text-[13px] ${darkMode ? 'border-zinc-700 bg-zinc-900/70 text-zinc-100 placeholder:text-zinc-600' : 'border-zinc-200 bg-white text-zinc-900 placeholder:text-zinc-400'}`}
                  />
                  {topBarTimezoneLabel ? (
                    <div className={`mt-0.5 truncate text-[9px] ${darkMode ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      {topBarTimezoneLabel}
                    </div>
                  ) : null}
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 xl:shrink-0">
            <button
              onClick={refreshControlBar}
              disabled={refreshButtonDisabled}
              className={`inline-flex min-w-[96px] items-center justify-center rounded-full border px-3.5 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] disabled:cursor-not-allowed ${
                darkMode
                  ? 'border-zinc-700 bg-zinc-950/60 text-zinc-100 disabled:border-zinc-800 disabled:bg-zinc-900 disabled:text-zinc-500'
                  : 'border-zinc-200 bg-white text-zinc-900 disabled:border-zinc-200 disabled:bg-zinc-100 disabled:text-zinc-400'
              }`}
              style={monoStyle}
            >
              {loading && mode !== 'manual' ? 'Refreshing...' : 'Refresh'}
            </button>
            <button
              onClick={applyManual}
              disabled={applyButtonDisabled}
              className="inline-flex min-w-[96px] items-center justify-center rounded-full bg-zinc-900 px-3.5 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-white disabled:cursor-not-allowed disabled:bg-zinc-300 disabled:text-zinc-50 dark:bg-white dark:text-zinc-900 dark:disabled:bg-zinc-700 dark:disabled:text-zinc-300"
              style={monoStyle}
            >
              {loading && mode === 'manual' ? 'Applying...' : 'Apply'}
            </button>
            <div className="relative">
              <button
                type="button"
                aria-label="Copy Prompt"
                onClick={handleTogglePromptMenu}
                title={featureActionsLocked ? 'Premium utility - unlock Vox Stella to copy prompts' : 'Copy AI-ready prompt'}
                className={`inline-flex h-9 w-9 items-center justify-center rounded-full border shadow-sm transition-colors ${copyPromptControlCls}`}
              >
                <ClipboardCopy className="h-4 w-4" aria-hidden="true" />
                <span className="sr-only">{anyPromptCopied ? 'Copied' : 'Copy Prompt'}</span>
              </button>
              {showPromptMenu && (
                <div className="absolute right-0 z-30 mt-2 w-56 rounded-lg border border-zinc-200 bg-white p-2 text-[12px] shadow-lg dark:border-gray-700 dark:bg-gray-800">
                  <div className="px-2 pb-1 text-[11px] font-medium text-zinc-600 dark:text-zinc-300">Choose prompt type</div>
                  <button
                    type="button"
                    className="w-full rounded px-2 py-1 text-left hover:bg-zinc-100 dark:hover:bg-gray-700"
                    onClick={()=> { setShowPromptMenu(false); handleCopyBirthChartPrompt(); }}
                    title="Copy AI-ready natal data prompt"
                  >
                    Natal prompt (copy)
                  </button>
                  <button
                    type="button"
                    className="w-full rounded px-2 py-1 text-left hover:bg-zinc-100 dark:hover:bg-gray-700"
                    onClick={()=> { setShowPromptMenu(false); handleCopyForensicCasePrompt(); }}
                    title="Copy AI-ready case-gathering prompt"
                  >
                    Case prompt (copy)
                  </button>
                  <button
                    type="button"
                    className="w-full rounded px-2 py-1 text-left hover:bg-zinc-100 dark:hover:bg-gray-700"
                    onClick={()=> { setShowPromptMenu(false); handleCopyAssetPrompt(); }}
                    title="Copy AI-ready asset first-trade prompt"
                  >
                    Asset prompt (copy)
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        {mode === 'manual' && manualTimeResolution?.kind === 'ambiguous' ? (
          <div className="mt-3">
            <LocalTimeAmbiguityChoice
              resolution={manualTimeResolution}
              selectedKey={manualTimeResolution.selectedKey}
              dark={darkMode}
              ariaLabel="Choose manual chart UTC offset"
              onSelect={(selectedKey) => {
                setManualTimeResolution((current) => current ? { ...current, selectedKey } : current);
                setActionError('');
              }}
            />
          </div>
        ) : null}
        {actionError && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {actionError}
          </div>
        )}
        {!actionError && clockLoadError && !suppressRealtimeBackendDropBanner && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {clockLoadError}
          </div>
        )}
        {!actionError && !clockLoadError && backendChecking && !data && (
          <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Astro Clock is waiting for the local astrology engine to finish starting. Data will appear automatically.
          </div>
        )}
        {!actionError && !clockLoadError && backendOffline && !suppressRealtimeBackendDropBanner && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            Astro Clock could not reach the local astrology engine. Use Refresh after it reconnects.
          </div>
        )}
      </div>

      {/* Single-column reading flow below xl; balanced three-column workspace on wide screens. */}
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-x-4 gap-y-4 lg:gap-x-5 lg:gap-y-6 xl:grid-cols-[minmax(180px,0.78fr)_minmax(0,2.55fr)_minmax(260px,1.22fr)] xl:grid-rows-[auto_minmax(500px,auto)_auto]">
        {/* Left column (col 1): stack Dispositors + Fixed Stars together to avoid row stretching */}
        <div className="order-1 min-w-0 self-start space-y-4 lg:space-y-6 xl:[grid-column:1] xl:[grid-row:1/4]">
          {/* Receptions - rectangle */}
          <section className={`${panelCls} h-auto max-h-80 md:max-h-[340px] overflow-auto`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Receptions</h3>
            </div>
            <ReceptionsTile
              dataTimestamp={data?.timestamp}
              receptions={data?.receptions}
              clockContext={buildAppliedClockContext()}
            />
          </section>
          {/* G) Dispositors - rectangle */}
          <section className={`${panelCls} h-auto max-h-80 md:max-h-[340px] overflow-auto`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Dispositors</h3>
            </div>
            {!data && <div className="text-sm text-zinc-500">Loading…</div>}
          {data && <DispositorsCard data={data} includeModern={includeModern} />}
          </section>

          {/* H) Fixed Stars - square */}
          <section className={`${panelCls} aspect-square`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Fixed Stars</h3>
            </div>
            <div className="text-sm space-y-2 overflow-auto h-[calc(100%-28px)] pr-1">
              {data?.fixed_star_hits?.length ? data.fixed_star_hits.map((hit, idx)=> {
                const conjWith = (() => {
                  if (hit.target_type === 'planet') {
                    const glyph = PlanetSymbols[hit.target] || '';
                    return `conj with ${glyph ? glyph + ' ' : ''}${hit.target}`;
                  }
                  if (hit.target_type === 'cusp') {
                    const labelMap = { C1: 'Asc', C10: 'MC' };
                    const nice = labelMap[hit.target] || hit.target;
                    return `conj with ${nice}`;
                  }
                  return `conj with ${hit.target}`;
                })();
                const orbText = typeof hit.orb_deg === 'number' ? `${Number(hit.orb_deg).toFixed(2)}°` : `${hit.orb_deg}°`;
                return (
                  <div key={idx} className="border-t border-zinc-100 pt-2.5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                          {hit.name}
                        </div>
                        <div className="mt-1 text-[14px] leading-5 text-zinc-900" style={serifStyle}>
                          {hit.constellation} {degreeTextFromLon(hit.star_longitude)}
                        </div>
                      </div>
                      <div className="text-[11px] text-zinc-500">{orbText}</div>
                    </div>
                    <div className="mt-1 text-[11px] text-zinc-500">{conjWith}</div>
                  </div>
                );
              }) : <div className="text-zinc-500">No close fixed stars</div>}
            </div>
          </section>

          {/* Arabic Lots - square */}
          <section className={`${panelCls} aspect-square`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Arabic Lots</h3>
            </div>
            <ArabicLotsPanel data={data} />
          </section>

          <section className={`${panelCls} aspect-square`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Sect</h3>
            </div>
            <div className="astro-scroll-shell h-[calc(100%-28px)]">
              <div className="astro-scroll text-sm space-y-2">
                <SectPanel data={data} />
              </div>
            </div>
          </section>

          {/* Degree Hits - square under Sect */}
          <section>
            <DegreeHitsTile
              metrics={data?.metrics}
              specialDegrees={specialDegrees}
              onApplyDegrees={(tokens)=> { setSpecialDegrees(tokens || []); }}
              onClearDegrees={()=> { setSpecialDegrees([]); }}
              pointsContext={buildAppliedClockContext()}
              detailsLocked={featureActionsLocked}
              onDetailsLocked={() => openPremiumOffer('Degree Hits')}
              detailsLockedTitle={featureActionTitle}
            />
          </section>
          <section>
            <AlmutenTile almutens={data?.almutens} />
          </section>

        </div>

        {/* Center column (col 2) */}
        <div className="order-4 min-w-0 space-y-4 lg:space-y-6 xl:[grid-column:2] xl:[grid-row:1]">
          {/* A) Solar Conditions - rectangle with chips (Morin-aware) */}
          <section className={panelCls}>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div>
                  <div className={tileEyebrowCls} style={monoStyle}>Solar State</div>
                  <h3 className="mt-1 font-semibold text-sm">Solar Conditions</h3>
                </div>
              </div>
            </div>
            {(() => {
              const solarEntries = buildSolarConditionEntries(data, useMorin);
              if (!solarEntries.length) {
                return (
                  <div className="mt-3 border-t border-zinc-100 pt-3 text-sm text-zinc-500">
                    No solar conditions are active in the current scope.
                  </div>
                );
              }
              return (
                <div className="mt-3 border-t border-zinc-100 pt-3">
                  <div className="grid gap-x-6 gap-y-3 md:grid-cols-3">
                    {solarEntries.map((entry) => (
                      <div key={entry.key} className="flex min-w-0 items-start gap-3 border-b border-zinc-100 pb-3">
                        <div
                          className={`inline-flex h-7 w-7 shrink-0 items-center justify-center text-[16px] leading-none ${solarConditionAccentTone(entry.tone)}`}
                          style={{ fontFamily: "'Segoe UI Symbol', 'Noto Sans Symbols 2', 'Arial Unicode MS', sans-serif" }}
                        >
                          {PlanetSymbols[entry.planet] || entry.planet || '☉'}
                        </div>
                        <div className="min-w-0 flex-1">
                          {entry.label ? (
                            <div className="text-[15px] leading-5 text-zinc-900" style={serifStyle}>
                              {entry.label}
                            </div>
                          ) : null}
                          <div className={`${entry.label ? 'mt-1' : 'mt-0.5'} text-[12px] text-zinc-600`}>{entry.detail}</div>
                          {entry.meta ? (
                            <div className="mt-1 text-[10px] text-zinc-500" style={monoStyle}>{entry.meta}</div>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}
          </section>

          {/* B) Chart - square mock with Hour-of-Day mini ring */}
          <section className="order-5 xl:[grid-column:2] xl:[grid-row:2]">
            <ChartMock
              data={data}
              chartLens={chartLens}
              onChartLensChange={setChartLens}
              onSnap={doSnap}
              snapDisabled={manualPending || snapSaving}
              snapBusy={snapSaving}
              houseSystem={houseSystem}
              onHouseSystemChange={async (code) => { await (async () => handleHouseSystemChange(code))(); }}
            />
          </section>

          {/* C) Moon Condition - rectangle */}
          <section className="order-6 xl:[grid-column:2] xl:[grid-row:3]">
            <MoonCondition data={data} />
          </section>
          {/* Saved Snaps - below Moon Condition */}
          <section className="order-7 xl:[grid-column:2] xl:[grid-row:4]">
            <SavedSnapsTile
              snaps={snaps}
              loading={loadingSnaps}
              loaded={snapsLoaded}
              migrationReport={snapMigrationReport}
              onRefresh={refreshSnaps}
              onLoad={loadSnap}
              onDelete={deleteSnap}
            />
          </section>
          {/* Influence & Afflictions - under Saved Snaps */}
          <section className="order-8 xl:[grid-column:2] xl:[grid-row:5]">
            <MetricsTile metrics={data?.metrics} specialDegrees={data?.special_degrees} />
          </section>
        </div>

        {/* Right column (col 3) */}
        <div className="order-7 min-w-0 space-y-4 lg:space-y-6 xl:-ml-2 xl:[grid-column:3] xl:[grid-row:1]">
          {/* D) Current Aspect - square */}
          <section className="xl:[grid-column:3] xl:[grid-row:1]">
            <CurrentAspectCard data={data} onOpenAnalysis={()=> setShowAspectAnalysis(true)} useMorin={useMorin} setUseMorin={setUseMorin} />
          </section>
          {/* Modal mount (fixed overlay) */}
          <AspectAnalysisModal
            open={!!showAspectAnalysis}
            onClose={()=> setShowAspectAnalysis(false)}
            specialDegrees={specialDegrees}
            useMorin={useMorin}
            includeModern={includeModern}
            dashboardData={data}
          />
          {/* E) Positions + Dignity - row 2 */}
          <section className="overflow-auto xl:[grid-column:3] xl:[grid-row:2/3]">
            <PositionsDignityCard data={data} />
          </section>
          {/* Current Cusps - moved up to row 3 */}
          <section className={`xl:[grid-column:3] xl:[grid-row:3] ${panelCls}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
                  House Sequence
                </div>
                <h3 className="mt-1 font-semibold text-sm">Current Cusps</h3>
              </div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                H · Deg · Sign · Ruler
              </div>
            </div>
            <div className="mt-3 overflow-auto max-h-72 pr-1">
              <div className="space-y-2">
                {(data?.house_cusps||[]).slice(0,12).map((lon, i)=> (
                  <div key={i} className="rounded-2xl border border-zinc-100 bg-white px-3 py-2.5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 shrink-0 text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>
                        H{i+1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-[14px] leading-5 text-zinc-900" style={serifStyle}>
                          {degreeTextFromLon(lon)} {signFromLon(lon)}
                        </div>
                        <div className="mt-0.5 text-[11px] text-zinc-500">
                          Ruler: {data?.house_rulers?.[String(i+1)] || '-'}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

      {/* Cusp Aspects - tight 1° aspects of cusps to planets */}
      <section className={`xl:[grid-column:3] xl:[grid-row:4] ${panelCls}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
              Angular Contacts
            </div>
            <h3 className="mt-1 font-semibold text-sm">Cusp Aspects</h3>
          </div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
            ≤ 1° orb
          </div>
        </div>
        <div className="mt-3 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-white p-1">
            {['all','conj','hard'].map(mode => (
              <button
                key={mode}
                type="button"
                className={`rounded-full px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] ${
                  cuspAspectMode===mode ? 'bg-zinc-900 text-white' : 'text-zinc-500'
                }`}
                style={monoStyle}
                onClick={()=> setCuspAspectMode(mode)}
              >
                {mode==='hard'? 'Hard' : mode==='all'? 'All' : 'Conj only'}
              </button>
            ))}
            </div>
            <div className="relative">
            <button
              type="button"
              className="rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-zinc-500"
              style={monoStyle}
              onClick={()=> setShowCuspMenu(v=>!v)}
            >
              Cusps ({cuspSelected.size})
            </button>
            {showCuspMenu && (
              <div className="absolute z-10 mt-1 w-56 rounded-2xl border border-zinc-200 bg-white p-3 shadow-lg text-[12px]">
                <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>Angular</div>
                <div className="flex items-center gap-2 mb-1">
                  {[...ANGULAR_SET].map(k=> (
                    <label key={k} className="flex items-center gap-1">
                      <input type="checkbox" checked={cuspSelected.has(k)} onChange={()=> toggleCusp(k)} /> {k}
                    </label>
                  ))}
                </div>
                <div className="mb-1 mt-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>Succedent</div>
                <div className="flex items-center gap-2 mb-1">
                  {[...SUCCEDENT_SET].map(k=> (
                    <label key={k} className="flex items-center gap-1">
                      <input type="checkbox" checked={cuspSelected.has(k)} onChange={()=> toggleCusp(k)} /> {k}
                    </label>
                  ))}
                </div>
                <div className="mb-1 mt-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>Cadent</div>
                <div className="flex items-center gap-2 mb-2">
                  {[...CADENT_SET].map(k=> (
                    <label key={k} className="flex items-center gap-1">
                      <input type="checkbox" checked={cuspSelected.has(k)} onChange={()=> toggleCusp(k)} /> {k}
                    </label>
                  ))}
                </div>
                <div className="flex items-center justify-between">
                  <button type="button" className="rounded-full border border-zinc-200 px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-zinc-500" style={monoStyle} onClick={setAllCusps}>All</button>
                  <button type="button" className="rounded-full border border-zinc-200 px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-zinc-500" style={monoStyle} onClick={clearCusps}>None</button>
                  <button type="button" className="rounded-full border border-zinc-200 px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-zinc-500" style={monoStyle} onClick={()=> setShowCuspMenu(false)}>Close</button>
                </div>
              </div>
            )}
            </div>
            <div className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-white p-1">
            {['any','applying','separating'].map(ph => (
              <button
                key={ph}
                type="button"
                className={`rounded-full px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] ${
                  cuspPhase===ph ? 'bg-zinc-900 text-white' : 'text-zinc-500'
                }`}
                style={monoStyle}
                onClick={()=> setCuspPhase(ph)}
              >
                {ph}
              </button>
            ))}
            </div>
            <div className="flex-1" />
          </div>
        </div>
        <div className="mt-3 astro-scroll-shell max-h-72" onClick={()=> setShowCuspMenu(false)}>
          <div className="astro-scroll space-y-3 max-h-72">
            {(() => {
              const src = data?.cusp_aspects || {};
              const hasData = !!data;
              const rawHitCount = Object.values(src).reduce((count, value) => {
                return count + (Array.isArray(value) ? value.length : 0);
              }, 0);
              if (!hasData) {
                return <div className="text-sm text-zinc-500">Loading cusp aspects...</div>;
              }
              const allKeys = Array.from({length:12}, (_,i)=>`H${i+1}`);
              // Keep an empty selection empty so the "None" action behaves as a
              // real filter state instead of silently reverting to all cusps.
              const keys = allKeys.filter(k => cuspSelected.has(k));
              const rows = [];
            for (const k of keys) {
              const items = Array.isArray(src[k]) ? src[k] : [];
              let list = items.filter(it => {
                if (cuspAspectMode === 'hard' && it?.category !== 'hard') return false;
                if (cuspAspectMode === 'conj' && String(it?.aspect).toLowerCase() !== 'conjunction') return false;
                const ph = String(it?.phase || '').toLowerCase();
                if (cuspPhase !== 'any' && ph !== cuspPhase) return false;
                if (it?.orb == null) return false;
                if (Number(it.orb) > 1.0 + 1e-6) return false;
                return true;
              });
              // Keep backend ordering (by orb, hard first). No user sort.
              if (list.length === 0) continue;
              rows.push(
                <div key={k} className="border-t border-zinc-100 pt-3">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                      {k}
                    </div>
                    <div className="text-[10px] text-zinc-400" style={monoStyle}>
                      {list.length} hit{list.length === 1 ? '' : 's'}
                    </div>
                  </div>
                  <ul className="space-y-2">
                    {list.slice(0, 16).map((it, idx) => {
                      const orb = (it?.orb != null) ? `${Number(it.orb).toFixed(2)}°` : '-';
                      const phase = it?.phase || '';
                      const band = it?.band || (Number(it?.orb||10) <= 0.5 ? 'partile' : 'tight');
                      const dex = (typeof it?.dexter === 'boolean') ? (it.dexter ? 'dexter' : 'sinister') : '';
                      const origin = (it?.origin_house != null) ? `H${it.origin_house}` : '';
                      const originTitle = it?.origin_domain ? String(it.origin_domain) : '';
                      const label = `${it.planet}${origin? ' ('+origin+')':''} ${it.aspect}`;
                      return (
                        <li
                          key={`${k}-${idx}`}
                          className="border-t border-zinc-100 pt-2.5"
                          title={originTitle}
                        >
                          <div className="flex items-start gap-2">
                            <span className="inline-flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full border border-zinc-200 bg-white px-1.5 text-[12px] leading-none">
                              {PlanetSymbols[it.planet] || it.planet}
                            </span>
                            <div className="min-w-0 flex-1">
                              <div className="break-words text-[13px] leading-5 text-zinc-900" style={serifStyle}>
                                {label}
                              </div>
                              {originTitle && (
                                <div className="mt-1 break-words text-[11px] leading-4 text-zinc-600">
                                  {originTitle}
                                </div>
                              )}
                              <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-zinc-500">
                                <span className="tabular-nums">{orb}</span>
                                {phase && (
                                  <span
                                    className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] ${
                                      String(phase).toLowerCase() === 'applying'
                                        ? 'border border-emerald-200 bg-emerald-50 text-emerald-700'
                                        : 'border border-zinc-200 bg-white text-zinc-500'
                                    }`}
                                    style={monoStyle}
                                  >
                                    {phase}
                                  </span>
                                )}
                                {dex && <span className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-[9px] text-zinc-500" style={monoStyle}>{dex}</span>}
                                {band && <span className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-[9px] text-zinc-500" style={monoStyle}>{band}</span>}
                              </div>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            }
              if (rows.length) return rows;
              if (rawHitCount > 0) {
                return <div className="text-zinc-500">No cusp aspects match the current filters.</div>;
              }
              return <div className="text-zinc-500">No cusp-to-planet aspects within 1° for this chart.</div>;
            })()}
          </div>
        </div>
      </section>

      <section className="min-w-0 xl:[grid-column:3] xl:[grid-row:5]">
        <CompassTile
          includeModern={includeModern}
          timestamp={activeCompassTimestamp}
          mode={mode}
          location={activeCompassLocation}
          timezone={mode === 'manual'
            ? (activeSnapContext?.timezone || resolveAstroClockTimezone(data?.timezone, data?.timezone_label))
            : resolveAstroClockTimezone(data?.timezone, data?.timezone_label)}
          latitude={mode === 'manual'
            ? (activeSnapContext?.latitude ?? finiteNumberOrUndefined(activeManualContextRef.current?.latitude))
            : data?.latitude}
          longitude={mode === 'manual'
            ? (activeSnapContext?.longitude ?? finiteNumberOrUndefined(activeManualContextRef.current?.longitude))
            : data?.longitude}
          houseSystem={houseSystem}
          initialData={data?.compass}
          planets={data?.planets}
          houseCusps={data?.house_cusps}
          snaps={snaps}
          activeSnapId={activeSnapId || inferredActiveSnapId || ''}
          loadingSnaps={loadingSnaps}
          snapsLoaded={snapsLoaded}
          onRefreshSnaps={refreshSnaps}
          directional3dLocked={featureActionsLocked}
          onDirectional3dLocked={() => openPremiumOffer('Directional 3D')}
          directional3dLockedTitle={featureActionTitle}
        />
      </section>
      <section className="min-w-0 xl:[grid-column:3] xl:[grid-row:6]">
        <AsteroidsTile asteroids={data?.asteroids} />
      </section>
        </div>
      </div>

      {openingForensic && !showForensic && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div
            className={`w-full max-w-[340px] rounded-2xl border p-4 shadow-xl ${
              darkMode
                ? 'border-zinc-700 bg-zinc-900 text-zinc-100'
                : 'border-zinc-200 bg-white text-zinc-900'
            }`}
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className={`text-[11px] font-medium uppercase tracking-[0.16em] ${darkMode ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    Forensic Workspace
                  </div>
                  <div className="mt-1 text-sm font-semibold leading-5">Opening Forensic...</div>
                </div>
                <span
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                    darkMode
                      ? 'border-zinc-700 bg-zinc-800 text-zinc-300'
                      : 'border-zinc-200 bg-white text-zinc-600'
                  }`}
                >
                  Preparing
                </span>
              </div>
              <p className={`text-[12px] leading-5 ${darkMode ? 'text-zinc-300' : 'text-zinc-600'}`}>
                Preparing the forensic workspace before it opens.
              </p>
              <div className={`h-1.5 overflow-hidden rounded-full ${darkMode ? 'bg-zinc-800' : 'bg-zinc-100'}`}>
                <div className={`h-full w-2/3 rounded-full animate-pulse ${darkMode ? 'bg-sky-400' : 'bg-sky-500'}`} />
              </div>
            </div>
          </div>
        </div>
      )}
      {showForensic && (
        <ForensicDashboard
          onClose={handleCloseForensic}
          clockContext={buildAppliedClockContext()}
          snaps={snaps}
          activeSnapId={activeSnapId || inferredActiveSnapId || ''}
          loadingSnaps={loadingSnaps}
          snapsLoaded={snapsLoaded}
          onRefreshSnaps={refreshSnaps}
        />
      )}
      {showChineseAstrology && (
        <ChineseAstrologyPage
          onClose={handleCloseChineseAstrology}
          snaps={snaps}
          activeSnapId={activeSnapId || inferredActiveSnapId || ''}
          loadingSnaps={loadingSnaps}
          snapsLoaded={snapsLoaded}
          onRefreshSnaps={refreshSnaps}
        />
      )}
      {showBirthCertification && (
        <BirthCertificationModal
          open={showBirthCertification}
          onClose={handleCloseBirthCertification}
          mode={mode}
          manualIso={activeManualIso}
          manualLocation={activeSnapContext?.location || data?.location || manualLocation || autoLocation}
          timezone={data?.timezone || activeSnapContext?.timezone || null}
          latitude={mode === 'manual'
            ? (activeSnapContext?.latitude ?? finiteNumberOrUndefined(activeManualContextRef.current?.latitude))
            : (activeSnapContext?.latitude ?? finiteNumberOrUndefined(data?.latitude))}
          longitude={mode === 'manual'
            ? (activeSnapContext?.longitude ?? finiteNumberOrUndefined(activeManualContextRef.current?.longitude))
            : (activeSnapContext?.longitude ?? finiteNumberOrUndefined(data?.longitude))}
          houseSystem={houseSystem}
          chartSnapshot={data}
          snaps={snaps}
          activeSnapId={activeSnapId || inferredActiveSnapId || ''}
          loadingSnaps={loadingSnaps}
          snapsLoaded={snapsLoaded}
          onRefreshSnaps={refreshSnaps}
        />
      )}
        {showTraits && (
          <TraitProfileModal
            onClose={handleCloseTraitProfile}
            specialDegrees={specialDegrees}
            mode={mode}
            manualIso={activeManualIso}
            manualLocation={activeSnapContext?.location || data?.location || manualLocation}
            timezone={data?.timezone || activeSnapContext?.timezone || null}
            latitude={mode === 'manual'
              ? (activeSnapContext?.latitude ?? finiteNumberOrUndefined(activeManualContextRef.current?.latitude))
              : (activeSnapContext?.latitude ?? finiteNumberOrUndefined(data?.latitude))}
            longitude={mode === 'manual'
              ? (activeSnapContext?.longitude ?? finiteNumberOrUndefined(activeManualContextRef.current?.longitude))
              : (activeSnapContext?.longitude ?? finiteNumberOrUndefined(data?.longitude))}
            houseSystem={houseSystem}
            chartSnapshot={data}
            fixedStarHits={Array.isArray(data?.fixed_star_hits) ? data.fixed_star_hits : []}
            snaps={snaps}
            activeSnapId={activeSnapId || inferredActiveSnapId || ''}
            loadingSnaps={loadingSnaps}
            snapsLoaded={snapsLoaded}
            onRefreshSnaps={refreshSnaps}
          />
        )}
      {showSynastry && (
        <SynastryModal
          open={showSynastry}
          onClose={handleCloseSynastry}
          snaps={snaps}
          activeSnapId={activeSnapId || inferredActiveSnapId || ''}
        />
      )}
      {showTransits && (
        <TransitsModal
          open={showTransits}
          onClose={handleCloseTransits}
          onJumpToTime={jumpToIso}
          defaultHouseSystem={houseSystem}
          initialNatalContext={activeTransitSeed}
        />
      )}
      {showElection && (
        <ElectionModal
          open={showElection}
          onClose={handleCloseElection}
          onJumpToTime={jumpToIso}
          defaultHouseSystem={houseSystem}
          snaps={snaps}
          activeSnapId={activeSnapId || inferredActiveSnapId || ''}
        />
      )}
      {showAstrocartography && (
        <AstrocartographyModal
          open={showAstrocartography}
          onClose={handleCloseAstrocartography}
          defaultHouseSystem={houseSystem}
          initialTransitContext={activeTransitSeed}
          snaps={snaps}
          activeSnapId={activeSnapId || inferredActiveSnapId || ''}
          onCreateSnap={doSnap}
        />
      )}
      <PremiumOfferModal
        open={Boolean(premiumOfferFeature)}
        featureName={premiumOfferFeature}
        onClose={() => setPremiumOfferFeature('')}
        onActivated={onLicenseChanged}
      />
      {showNamePrompt && (
        <NamePromptModal
          open={showNamePrompt}
          type={namePromptType}
          onCancel={()=> setShowNamePrompt(false)}
          onSubmit={handleNamePromptSubmit}
        />
      )}
    </div>
  );
};

export default AstroClock;

function forensicSnapDashboard(snap) {
  return snap?.dashboard && typeof snap.dashboard === 'object' ? snap.dashboard : {};
}

function forensicSnapCoordinates(snap) {
  const dashboard = forensicSnapDashboard(snap);
  const latitude = finiteNumberOrUndefined(
    snap?.latitude ?? dashboard?.latitude ?? snap?.coordinates?.latitude ?? snap?.coordinates?.lat ?? snap?.chart_snapshot?.latitude,
  );
  const longitude = finiteNumberOrUndefined(
    snap?.longitude ?? dashboard?.longitude ?? snap?.coordinates?.longitude ?? snap?.coordinates?.lon ?? snap?.coordinates?.lng ?? snap?.chart_snapshot?.longitude,
  );
  return { latitude, longitude };
}

function getForensicSnapMetaParts(snap) {
  const dashboard = forensicSnapDashboard(snap);
  const label = firstPresent(snap?.label, snap?.id, 'Untitled snap') || 'Untitled snap';
  const iso = firstPresent(snap?.effective_datetime, dashboard?.timestamp, snap?.datetime, snap?.timestamp);
  const location = firstPresent(snap?.location, dashboard?.location);
  const timezone = firstPresent(snap?.timezone, dashboard?.timezone, snap?.timezone_label, dashboard?.timezone_label);
  const displayParts = formatForensicTimestampParts(iso, timezone);
  const datePart = displayParts.datePart;
  const timePart = displayParts.timePart;
  return { label, datePart, timePart, location, timezone, iso };
}

function formatForensicSnapLabel(snap) {
  const parts = getForensicSnapMetaParts(snap);
  return [parts.label, parts.datePart, parts.timePart, parts.location].filter(Boolean).join(' | ');
}

function snapToForensicClockContext(snap, fallbackHouseSystem) {
  if (!isSavedSnapCalculationEligible(snap)) return null;
  const dashboard = forensicSnapDashboard(snap);
  const calculationContext = snap?.calculation_context && typeof snap.calculation_context === 'object'
    ? snap.calculation_context
    : {};
  const chartSnapshot = snap?.chart_snapshot && typeof snap.chart_snapshot === 'object'
    ? snap.chart_snapshot
    : {};
  const datetime = firstPresent(snap?.effective_datetime, dashboard?.timestamp, snap?.datetime, snap?.timestamp);
  const location = firstPresent(snap?.location, dashboard?.location);
  const timezone = firstPresent(snap?.timezone, dashboard?.timezone, snap?.timezone_label, dashboard?.timezone_label);
  const selectedHouseSystem = firstPresent(
    calculationContext?.house_system_code,
    chartSnapshot?.house_system_code,
    snap?.house_system_code,
    dashboard?.house_system_code,
    snap?.house_system,
    dashboard?.house_system,
    fallbackHouseSystem,
  );
  const { latitude, longitude } = forensicSnapCoordinates(snap);
  if (!datetime) return null;
  return {
    mode: 'manual',
    datetime,
    location,
    timezone,
    houseSystem: selectedHouseSystem,
    latitude,
    longitude,
  };
}

function ForensicDashboard({
  onClose,
  clockContext,
  snaps = [],
  activeSnapId = '',
  loadingSnaps = false,
  snapsLoaded = true,
  onRefreshSnaps,
}){
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [features, setFeatures] = useState(null);
  const [forensicError, setForensicError] = useState('');
  const [viability, setViability] = useState({ asc_desc: null, correlation: null, angular: null, logic: null });
  const [caseType, setCaseType] = useState('general'); // general|child|adult_female
  const [abductionMode, setAbductionMode] = useState(false);
  const [includeRaw, setIncludeRaw] = useState(false);
  const [forensicTab, setForensicTab] = useState('findings');
  const [copiedBrief, setCopiedBrief] = useState(false);
  const [originLat, setOriginLat] = useState('');
  const [originLon, setOriginLon] = useState('');
  const [fetchingAbd, setFetchingAbd] = useState(false);
  const [abdMsg, setAbdMsg] = useState('');
  const [mapHover, setMapHover] = useState(null); // { lat, lon }
  const [placeName, setPlaceName] = useState('');
  const [placeLoading, setPlaceLoading] = useState(false);
  const [showBackAz, setShowBackAz] = useState(false);
  const [flipSubHorizon, setFlipSubHorizon] = useState(false);
  const [expandedFindingIndex, setExpandedFindingIndex] = useState(null);
  const forensicRequestSeqRef = useRef(0);
  const forensicClockContextKey = JSON.stringify(clockContext || {});
  const forensicClockContext = useMemo(() => ({ ...(clockContext || {}) }), [forensicClockContextKey]);
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
  const selectedSnapContext = useMemo(() => (
    chartSource === 'snap'
      ? snapToForensicClockContext(selectedSnap, forensicClockContext.houseSystem || forensicClockContext.house_system_code)
      : null
  ), [chartSource, selectedSnap, forensicClockContext.houseSystem, forensicClockContext.house_system_code]);
  const effectiveForensicClockContext = useMemo(() => (
    chartSource === 'snap' && selectedSnapContext ? selectedSnapContext : forensicClockContext
  ), [chartSource, selectedSnapContext, forensicClockContext]);
  const snapSelectionMessage = useMemo(() => {
    if (chartSource !== 'snap') return '';
    if (loadingSnaps) return 'Loading saved snaps...';
    if (!eligibleSnapOptions.length && snapOptions.length) {
      return 'Saved charts needing context review are disabled. Create a corrected copy in Astro Clock.';
    }
    if (!eligibleSnapOptions.length) return 'No saved snaps are available yet.';
    if (!selectedSnap) return 'Choose a saved snap.';
    if (!selectedSnapContext) return 'Selected snap is missing date/time context.';
    return '';
  }, [chartSource, eligibleSnapOptions.length, loadingSnaps, selectedSnap, selectedSnapContext, snapOptions.length]);
  const forensicContextReady = chartSource !== 'snap' || Boolean(selectedSnapContext);
  const rawFindings = useMemo(() => (
    Array.isArray(data?.findings) ? data.findings.filter((finding) => finding && typeof finding === 'object') : []
  ), [data?.findings]);
  const replayAxes = useMemo(() => deriveForensicReplayAxes(data || {}), [data]);
  const replayTailoring = useMemo(() => getForensicReplayTailoring(data || {}), [data]);
  const topFindings = useMemo(() => {
    if (!rawFindings.length) return [];
    const weighted = rawFindings
      .map((finding, index) => ({
        finding,
        index,
        weight: Number(finding?.weight),
        displayWeight: (() => {
          const base = Number(finding?.weight);
          if (!Number.isFinite(base)) return Number.NaN;
          let score = base;
          if (replayTailoring.domesticFatalContext) {
            if (forensicFindingMatchesAxis(finding, 'abduction_missing_person')) score -= 100;
            if (forensicFindingMatchesAxis(finding, 'water_disappearance_or_drowning')) score -= 100;
            if (
              forensicFindingMatchesAxis(finding, 'violence_homicide') ||
              forensicFindingMatchesAxis(finding, 'family_involvement') ||
              forensicFindingMatchesAxis(finding, 'domestic_partner_involvement')
            ) {
              score += 20;
            }
          }
          if (replayTailoring.fatalPressureDominant && forensicFindingMatchesAxis(finding, 'violence_homicide')) {
            score += 10;
          }
          if (replayTailoring.childContext && forensicFindingMatchesAxis(finding, 'child_victim')) {
            score += 8;
          }
          return score;
        })(),
      }))
      .filter((item) => Number.isFinite(item.displayWeight) && item.displayWeight > -50);
    if (weighted.length) {
      return [...weighted]
        .sort((a, b) => (b.displayWeight - a.displayWeight) || (b.weight - a.weight) || (a.index - b.index))
        .slice(0, 6)
        .map((item) => item.finding);
    }
    const selected = [];
    const selectedIndexes = new Set();
    replayAxes.forEach((axis) => {
      const index = rawFindings.findIndex((finding, idx) => (
        !selectedIndexes.has(idx) && forensicFindingMatchesAxis(finding, axis)
      ));
      if (index >= 0) {
        selectedIndexes.add(index);
        selected.push(rawFindings[index]);
      }
    });
    rawFindings.forEach((finding, index) => {
      if (selected.length >= 6 || selectedIndexes.has(index)) return;
      selectedIndexes.add(index);
      selected.push(finding);
    });
    return selected;
  }, [rawFindings, replayAxes, replayTailoring]);
  const categoryEntries = useMemo(() => (
    data?.categories && typeof data.categories === 'object'
      ? Object.entries(data.categories).sort((a, b) => String(a[0]).localeCompare(String(b[0])))
      : []
  ), [data?.categories]);

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
    if (chartSource === 'snap' && !selectedSnap && eligibleSnapOptions.length) {
      setSelectedSnapId(String(eligibleSnapOptions[0].id || ''));
    }
    if (chartSource === 'snap' && !selectedSnap && !eligibleSnapOptions.length) {
      setSelectedSnapId('');
    }
  }, [chartSource, eligibleSnapOptions, selectedSnap]);

  useEffect(() => {
    if (typeof onRefreshSnaps !== 'function') return;
    if (snapsLoaded && snapOptions.length) return;
    onRefreshSnaps({ silent: true });
  }, [onRefreshSnaps, snapsLoaded, snapOptions.length]);

  useEffect(() => {
    setExpandedFindingIndex(null);
  }, [data?.timestamp, rawFindings.length]);

  useEffect(() => {
    if (includeRaw) setForensicTab('raw');
  }, [includeRaw]);

  const fetchForensic = useCallback(async (optsExtra={}) => {
    const requestSeq = forensicRequestSeqRef.current + 1;
    forensicRequestSeqRef.current = requestSeq;
    if (!forensicContextReady) {
      setAbdMsg(snapSelectionMessage);
      setForensicError('');
      return null;
    }
    try {
      setForensicError('');
      const opts = chartSource === 'snap' && selectedSnap?.id
        ? {
          snapId: String(selectedSnap.id),
          houseSystem:
            effectiveForensicClockContext.houseSystem
            || effectiveForensicClockContext.house_system_code,
          caseType,
        }
        : { ...effectiveForensicClockContext, caseType };
      if (optsExtra && optsExtra.abduction) {
        opts.abduction = true;
        if (optsExtra.origin) opts.origin = optsExtra.origin;
        if (optsExtra.line_zones != null) opts.line_zones = !!optsExtra.line_zones;
        if (optsExtra.corridor_deg != null) opts.corridor_deg = optsExtra.corridor_deg;
      }
      const res = await AstroClockAPI.getForensic(opts);
      if (requestSeq !== forensicRequestSeqRef.current) return null;
      if (res?.success) {
        setData(res);
        setFeatures(res.features || null);
        if (optsExtra && optsExtra.abduction) {
          const mapError = res.abduction_map_error ? `: ${res.abduction_map_error}` : '.';
          setAbdMsg(res.abduction_map ? 'Abduction map fetched.' : `Abduction map unavailable${mapError}`);
        } else {
          setAbdMsg('');
        }
      } else {
        const message = `Forensic dossier unavailable: ${String(res?.error || res?.detail || 'unknown error')}`;
        setForensicError(message);
        if (!(optsExtra && optsExtra.abduction)) {
          setData(null);
          setFeatures(null);
        }
      }
      return res;
    } catch(err){
      if (requestSeq !== forensicRequestSeqRef.current) return null;
      const isAbductionFetch = Boolean(optsExtra && optsExtra.abduction);
      const label = isAbductionFetch ? 'Abduction map' : 'Forensic dossier';
      const message = `${label} fetch failed: ${String(err?.message||err)} (API ${window.API_BASE_URL||'unknown'})`;
      console.error(`${label} fetch failed:`, err);
      setForensicError(message);
      if (!isAbductionFetch) {
        setData(null);
        setFeatures(null);
        setAbdMsg('');
      } else {
        try { setAbdMsg(message); } catch(_){ setAbdMsg('Abduction map fetch failed.'); }
      }
      throw err;
    }
  }, [
    caseType,
    chartSource,
    effectiveForensicClockContext,
    forensicContextReady,
    selectedSnap,
    snapSelectionMessage,
  ]);

  useEffect(() => {
    let cancelled = false;
    if (!forensicContextReady) {
      setData(null);
      setFeatures(null);
      setForensicError('');
      setAbdMsg(snapSelectionMessage);
      setLoading(Boolean(loadingSnaps));
      return () => {
        cancelled = true;
        forensicRequestSeqRef.current += 1;
      };
    }
    setLoading(true);
    (async () => {
      try {
        await fetchForensic();
      } catch {}
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => {
      cancelled = true;
      forensicRequestSeqRef.current += 1;
    };
  }, [fetchForensic, forensicContextReady, loadingSnaps, snapSelectionMessage]);

  function buildAIBrief(includeRawValues){
    try {
      const lines = [];
      const dash = data || {};
      const f = features || {};
      // Victim basics
      const cusps = f.house_cusps || [];
      const ascSignName = (()=>{ try { const L = Number(cusps[0]); const signs=['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']; return isFinite(L)? signs[Math.floor(((L%360)+360)%360/30)] : null; } catch{ return null; } })();
      const rulers = f.house_rulers || {};
      const primaryRuler = f.houses?.first_ruler || rulers['1'] || rulers[1] || null;
      const coRulers = ['Moon', ...(caseType==='child'? ['Mercury']: [])].filter((v,i,arr)=> arr.indexOf(v)===i);
      const moon = f.planets?.['Moon'] || {};
      const mt = dash.moon_timeline || {};
      const voc = (typeof mt.in_voc === 'boolean') ? mt.in_voc : Boolean((dash.moon || f.moon || {}).void_of_course);
      const moonPos = `${moon.sign||'-'} ${isFinite(moon.longitude)? degreeTextFromLon(moon.longitude):'-'} (H${moon.house??'-'})`;

      // Perpetrator basics
      const seventhRuler = f.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
      const pl = f.planets || {};
      const prInfo = pl[seventhRuler] || {};
      const degFlags = [];
      if (prInfo.anaretic) degFlags.push('Anaretic');
      if (prInfo.ingress) degFlags.push('Ingress');
      if (prInfo.middegree) degFlags.push('Mid-degree');
      if (prInfo.via_combusta) degFlags.push('Via combusta');
      const fsSunMoon = Array.isArray(f.fixed_stars_list)? f.fixed_stars_list.filter(h=> h?.target_type==='planet' && (h?.target==='Sun' || h?.target==='Moon')): [];
      const fsCusps = Array.isArray(f.fixed_stars_list)? f.fixed_stars_list.filter(h=> h?.target_type==='cusp'): [];

      // Witnesses
      const houseList = (h)=> Object.entries(pl).filter(([,p])=> p?.house===h).map(([n])=> n);
      const witnesses = ['Mercury', ...houseList(3)];
      const associates = houseList(11);
      const hidden = [...houseList(6), ...houseList(12)];

      // Deception config (reuse simplified flags)
      const asp = f.aspects || {};
      const getA = (a,b)=> Boolean(asp[`${a}_to_${b}`] || asp[`${b}_to_${a}`]);
      const houses = f.houses || {};
      const deceFlags = [];
      if (getA('Mercury','Neptune')) deceFlags.push('Mercury–Neptune');
      if (pl?.Mercury?.retrograde) deceFlags.push('Mercury retrograde');
      if ((dash.features?.solar || f.solar || {}).combustion?.includes?.('Mercury')) deceFlags.push('Mercury combust');
      if (pl?.Mercury?.house===12) deceFlags.push('Mercury in 12th');
      if (pl?.Mercury?.mute_sign) deceFlags.push('Mercury in mute sign');
      ['Sun','Moon','Mercury','Venus','Mars'].forEach(pn=> { if (getA('Neptune', pn)) deceFlags.push('Neptune->personal'); });
      if (pl?.Sun?.house===12 || pl?.Moon?.house===12) deceFlags.push('Sun/Moon in 12th');
      if (houses?.emphasis12_strong) deceFlags.push('12th emphasis');
      if (houses?.seventh_ruler_in_12th) deceFlags.push('7th ruler in 12th');
      if (getA('Mars','Neptune')) deceFlags.push('Mars–Neptune');
      if (getA('Venus','Saturn')) deceFlags.push('Venus–Saturn');
      if (houses?.mute_signs_on_angles) deceFlags.push('Mute signs on angles');
      if (houses?.mute_sign_on_3rd_or_9th) deceFlags.push('Mute signs on 3rd/9th');
      if (houses?.north_node_house===8) deceFlags.push('NN in 8th');
      if (houses?.north_node_house===4) deceFlags.push('NN in 4th');

      // Final Outcome
      const cusp4 = Number((f.house_cusps||[])[3]);
      const icSign = isFinite(cusp4)? signFromLon(cusp4): null;
      const icExpl = icSign ? (dash.ic_sign_meanings?.[icSign]?.outcome) : null;
      const r4 = rulers['4'] || rulers[4] || null;
      const r4h = r4 ? pl?.[r4]?.house : null;
      const r4Expl = (r4h!=null)? (dash.ic_ruler_house_meanings?.[String(r4h)]?.outcome) : null;
      const in4 = Object.entries(pl).filter(([,p])=> p?.house===4).map(([n])=> n);
      const in4Expl = in4.map(nm => {
        const e = dash.ic_planet_in_4th?.[nm];
        return e? `${nm} - ${e}` : nm;
      });
      const nodesIn4 = in4.filter(nm => nm==='North Node' || nm==='South Node' || nm==='Node');

      // Abduction / Location & Distance Cues
      let abdBlock = '';
      if (abductionMode) {
        abdBlock = buildAbductionCueReportLines({ data, features: f }).join('\n');
      }

      // Light mediation
      const lm = dash.light_mediation || {};

      const header = `Summarize the forensic astrology rule output below in an auditable way. Use these sections: Victim Significators, 7th-house Counterpart Signals, Witness Symbols, Deception Symbols, Outcome Rule Classification${abductionMode? ', Direction Cues':''}.`;
      lines.push(header, '');
      lines.push('Victim Analysis');
      lines.push(`ASC Sign: ${ascSignName||'-'}`);
      lines.push(`Primary Ruler: ${primaryRuler||'-'}; Co-rulers: ${coRulers.join(', ')||'-'}`);
      lines.push(`Moon: ${moonPos}; VoC ${voc? 'Yes':'No'}`);
      lines.push('');
      lines.push('7th-house Counterpart Signals');
      lines.push(`7th-house ruler: ${seventhRuler||'-'} · Degree markers: ${degFlags.join(', ')||'-'}`);
      lines.push(`Light mediation: ${lm.translation? `Translation${lm.translator? ' via '+lm.translator:''}` : (lm.collection? `Collection${lm.collector? ' by '+lm.collector:''}` : '-')}`);
      if (fsSunMoon.length) lines.push(`Sun/Moon fixed stars: ${fsSunMoon.map(x=> `${x.name}↔${x.target}`).join('; ')}`);
      if (fsCusps.length) lines.push(`Cusp fixed stars: ${fsCusps.map(x=> `${x.name}↔${x.target}`).join('; ')}`);
      // Dominant Signature (top 1–2)
      try {
        const dom = dash.dominance?.planets || {};
        const domArr = Object.entries(dom).map(([name,v])=> ({ name, score: Number(v?.score)||0, level: String(v?.level||'') })).sort((a,b)=> b.score-a.score);
        if (domArr.length){
          const top2 = domArr.slice(0,2).map(d=> `${d.name} ${d.score} (${d.level})`).join(', ');
          lines.push(`Dominant signals: ${top2}`);
        }
      } catch(_){ /* ignore dominant errors */ }
      // Relationship Link Determination (Algorithm)
      try {
        const firstRuler = f.houses?.first_ruler || rulers['1'] || rulers[1] || null;
        const seventhRuler = f.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
        const sr = { Aries:'Mars', Taurus:'Venus', Gemini:'Mercury', Cancer:'Moon', Leo:'Sun', Virgo:'Mercury', Libra:'Venus', Scorpio:'Mars', Sagittarius:'Jupiter', Capricorn:'Saturn', Aquarius:'Saturn', Pisces:'Jupiter' };
        const exaltation = { Sun:'Aries', Moon:'Taurus', Mercury:'Virgo', Venus:'Pisces', Mars:'Capricorn', Jupiter:'Cancer', Saturn:'Libra' };
        const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
        const opp = (s) => signs[(signs.indexOf(s)+6)%12] || null;
        const triOf = (sign) => {
          if (!sign) return null;
          if (['Aries','Leo','Sagittarius'].includes(sign)) return 'Fire';
          if (['Taurus','Virgo','Capricorn'].includes(sign)) return 'Earth';
          if (['Gemini','Libra','Aquarius'].includes(sign)) return 'Air';
          if (['Cancer','Scorpio','Pisces'].includes(sign)) return 'Water';
          return null;
        };
        const planets = f.planets || {};
        const victimSign = planets?.[firstRuler]?.sign; const perpSign = planets?.[seventhRuler]?.sign;
        const victimHouse = planets?.[firstRuler]?.house; const perpHouse = planets?.[seventhRuler]?.house;
        const recData = dash?.receptions || {};
        const mutual = Array.isArray(recData.mutual)? recData.mutual : [];
        const uni = Array.isArray(recData.top_unilateral)? recData.top_unilateral : [];
        const starRel = dash?.relationship_star_hits || {};

        // Level 1
        const directVictRulesPerp = victimSign && sr[perpSign] === firstRuler;
        const directPerpRulesVict = perpSign && sr[victimSign] === seventhRuler;
        // Level 2
        const isMutual = mutual.some(m => (m.p1===firstRuler && m.p2===seventhRuler) || (m.p1===seventhRuler && m.p2===firstRuler));
        // Level 3
        const level3 = victimSign && perpSign && (triOf(victimSign) === triOf(perpSign));
        // Level 4
        const perpExaltSign = exaltation[seventhRuler];
        const victExaltSign = exaltation[firstRuler];
        const level4_victim_in_exalt_of_perp = victimSign && (victimSign === perpExaltSign);
        const level4_victim_in_fall_of_perp = victimSign && (victimSign === opp(perpExaltSign));
        const level4_perp_in_exalt_of_victim = perpSign && (perpSign === victExaltSign);
        const level4_perp_in_fall_of_victim = perpSign && (perpSign === opp(victExaltSign));
        // Level 5
        const level5_terms = uni.some(u => ((u.receiving===firstRuler && u.received===seventhRuler) || (u.receiving===seventhRuler && u.received===firstRuler)) && (u.dignities||[]).includes('term'));

        // House analysis
        const houseFlags = [];
        if (victimHouse===1) houseFlags.push('Victim ruler in 1st');
        if (victimHouse===7) houseFlags.push('Victim ruler in 7th');
        if (victimHouse===4||victimHouse===10) houseFlags.push('Victim ruler in 4th/10th');
        if (victimHouse===8) houseFlags.push('Victim ruler in 8th');
        if (victimHouse===12) houseFlags.push('Victim ruler in 12th');
        if (perpHouse===1) houseFlags.push('Perp ruler in 1st');
        if (perpHouse===4||perpHouse===10) houseFlags.push('Perp ruler in 4th/10th');
        if (perpHouse===6) houseFlags.push('Perp ruler in 6th');
        if (perpHouse===11) houseFlags.push('Perp ruler in 11th');
        const sameHouse = (victimHouse!=null && perpHouse!=null && victimHouse===perpHouse);
        const crit = [];
        // Only flag family involvement in crit when BOTH rulers are in 4th OR BOTH are in 10th
        const _vh = Number(victimHouse), _ph = Number(perpHouse);
        const critSameFamily = (_vh === 4 && _ph === 4) || (_vh === 10 && _ph === 10);
        if (critSameFamily) crit.push('Both rulers in same family house (4 or 10)');
        // Consolidate 1st/7th exchange into a single label (avoid duplicate)
        if ((victimHouse===1 && perpHouse===7) || (victimHouse===7 && perpHouse===1)) crit.push('1st/7th exchange');
        if (sameHouse) crit.push('Both rulers in same house');

        // Traditional cues
        const h7Planets = Object.entries(planets).filter(([,p])=> p?.house===7).map(([n])=> n);
        const trad = [];
        if (h7Planets.includes('Venus')) trad.push('Venus in 7th');
        if (h7Planets.includes('Mars')) trad.push('Mars in 7th');
        if ((planets?.Sun?.house===4)) trad.push('Sun in 4th');
        if ((planets?.Moon?.house===10)) trad.push('Moon in 10th');
        if (Object.values(planets).some(p=> p?.house===5)) trad.push('5th house connection');
        if (Object.values(planets).some(p=> p?.house===3)) trad.push('3rd house emphasis');

        // Aspects
        const aspMap = f.aspects || {};
        const a = aspMap[`${firstRuler}_to_${seventhRuler}`] || aspMap[`${seventhRuler}_to_${firstRuler}`] || null;
        const aspType = a?.type || null;
        const aspectFlags = [];
        if (aspType) {
          const easy=['conjunction','trine','sextile']; const hard=['square','opposition'];
          if (easy.includes(aspType)) aspectFlags.push(`Harmonious (${aspType})`);
          if (hard.includes(aspType)) aspectFlags.push(`Stressful (${aspType})`);
        } else { aspectFlags.push('No direct aspect'); }

        // Degrees and fixed stars on significators
        const degInt = (nm)=> { const d = planets?.[nm]?.degree_in_sign; return (typeof d==='number')? Math.round(d): null; };
        const dVict = degInt(firstRuler); const dPerp = degInt(seventhRuler);
        const degFlags2 = [];
        if (dVict===0) degFlags2.push('0° (victim)'); if (dPerp===0) degFlags2.push('0° (perp)');
        if (dVict===15) degFlags2.push('15° (victim)'); if (dPerp===15) degFlags2.push('15° (perp)');
        if (dVict===29) degFlags2.push('29° (victim)'); if (dPerp===29) degFlags2.push('29° (perp)');
        const ascStars = (starRel?.asc_ruler||[]).map(h=> h?.name).filter(Boolean);
        const dscStars = (starRel?.dsc_ruler||[]).map(h=> h?.name).filter(Boolean);

        const violentStars = new Set(['Algol','Antares']); const protectStars = new Set(['Spica']);
        const hasViolent = [...ascStars, ...dscStars].some(n=> violentStars.has(n));
        const hasProtect = [...ascStars, ...dscStars].some(n=> protectStars.has(n));
        const moonDispositorTiesPerp = Boolean(f?.moon?.dispositor_to_seventh_ruler_type);
        const moonDispositorHardContact = Boolean(f?.moon?.dispositor_to_seventh_ruler_hard);
        const moonDispositorCue = moonDispositorTiesPerp
          ? `Moon dispositor ${f?.moon?.dispositor || 'ruler'} ${f?.moon?.dispositor_to_seventh_ruler_type || 'contacts'} ${seventhRuler || '7th ruler'}`
          : null;
        const relationshipScore = scoreForensicRelationshipLink({
          victimHouse,
          perpHouse,
          sameHouse,
          directVictRulesPerp,
          directPerpRulesVict,
          isMutual,
          level3,
          level4VictimInExaltOfPerp: level4_victim_in_exalt_of_perp,
          level4PerpInExaltOfVictim: level4_perp_in_exalt_of_victim,
          level4VictimInFallOfPerp: level4_victim_in_fall_of_perp,
          level4PerpInFallOfVictim: level4_perp_in_fall_of_victim,
          directionalReception: uni.some(u=> (u.receiving===firstRuler && u.received===seventhRuler) || (u.receiving===seventhRuler && u.received===firstRuler)),
          level5Terms: level5_terms,
          criticalFamilyHouse: critSameFamily,
          lightMediation: lm,
          seventhHousePlanets: h7Planets,
          aspectType: aspType,
          aspect: a,
          criticalDegree: dVict===0||dVict===15||dVict===29||dPerp===0||dPerp===15||dPerp===29,
          hasViolentStar: hasViolent,
          hasProtectiveStar: hasProtect,
          moonDispositorTiesPerp,
          moonDispositorHardContact,
          victimSignificators: [firstRuler, 'Moon'].filter(Boolean),
          perpetratorSignificators: [seventhRuler].filter(Boolean),
        });
        const score = relationshipScore.score;
        const relationshipSummary = summarizeForensicRelationshipLink({
          score,
          victimHouse,
          perpHouse,
          seventhHousePlanets: h7Planets,
          isMutual,
          forensicResult: dash,
        });

        lines.push('', 'Relationship Signals');
        const bothIn4 = Number(victimHouse) === 4 && Number(perpHouse) === 4;
        const bothIn10 = Number(victimHouse) === 10 && Number(perpHouse) === 10;
        const relationshipRows = buildRelationshipDisplayRows({
          firstRuler,
          moonContacts: aspectTo('Moon'),
          ascRulerContacts: aspectTo(firstRuler),
          directVictRulesPerp,
          directPerpRulesVict,
          isMutual,
          level3,
          exaltationFallFlags: [
            level4_victim_in_exalt_of_perp?'victim in exaltation of perpetrator':null,
            level4_perp_in_exalt_of_victim?'perpetrator in exaltation of victim':null,
            level4_victim_in_fall_of_perp?'victim in fall of perpetrator':null,
            level4_perp_in_fall_of_victim?'perpetrator in fall of victim':null,
          ].filter(Boolean),
          level5Terms: level5_terms,
          houseConnections: (bothIn4 || bothIn10)
            ? ['shared family-house placement (4th/10th)']
            : houseFlags.concat(crit),
          traditionalCues: moonDispositorCue ? trad.concat(moonDispositorCue) : trad,
          aspectTies: aspectFlags,
          degreeStarCues: degFlags2.concat([
            ascStars.length? `ASC ruler on ${ascStars.join('/')}`: null,
            dscStars.length? `DSC ruler on ${dscStars.join('/')}`: null,
          ].filter(Boolean)),
          score,
          relationshipType: relationshipSummary.relationshipType,
          confidence: relationshipSummary.confidence,
        });
        lines.push(`Contact signals: ${relationshipRows.contactSignals}`);
        lines.push(`Rulership links: ${relationshipRows.rulershipLinks}`);
        lines.push(`Mutual reception: ${relationshipRows.mutualReception}`);
        lines.push(`Shared triplicity: ${relationshipRows.sharedTriplicity}`);
        lines.push(`Exaltation/fall ties: ${relationshipRows.exaltationFallTies}`);
        lines.push(`Term/bounds ties: ${relationshipRows.termBoundsTies}`);
        lines.push(`House overlap: ${relationshipRows.houseOverlap}`);
        lines.push(`Traditional cues: ${relationshipRows.traditionalCues}`);
        lines.push(`Aspect ties: ${relationshipRows.aspectTies}`);
        lines.push(`Degree/star cues: ${relationshipRows.degreeStarCues}`);
        lines.push(`Connection summary: ${relationshipRows.connectionSummary}`);
      } catch(_) {}
      lines.push('');
      lines.push('Witness & Accomplice Detection');
      lines.push(`Mercury (witness/sibling): H${pl?.Mercury?.house ?? '-'}`);
      lines.push(`H3 (neighbors/local): ${houseList(3).join(', ')||'-'}; H11 (associates): ${associates.join(', ')||'-'}; H6/12 (hidden): ${hidden.join(', ')||'-'}`);
      lines.push('');
      lines.push('Deception Configuration');
      lines.push(`Indicators: ${deceFlags.join('; ')||'-'}`);
      lines.push('');
      lines.push('Outcome Rule Classification');
      lines.push(`IC sign: ${icSign||'-'}${icExpl? ' - '+icExpl:''}`);
      lines.push(`4th ruler: ${r4? `${r4} in H${r4h??'-'}`:'-'}${r4Expl? ' - '+r4Expl:''}`);
      lines.push(`Planets in 4th: ${in4Expl.join('; ')||'-'}${nodesIn4.length? ' · Node modifier present':''}`);
      lines.push('Summarize only what the symbolic rule set associates with these placements; do not present a real outcome, actor, or location as likely or established.');
      if (abductionMode){ lines.push(''); lines.push(abdBlock); }

      if (includeRawValues) {
        // Append a compact RAW block to aid AI with precise values
        const raw = {};
        try {
          raw.asc_cusp = (f.house_cusps||[])[0];
          raw.house_cusps = (f.house_cusps||[]).slice(0,12);
          raw.house_rulers = f.house_rulers || {};
          raw.planets = Object.fromEntries(Object.entries(f.planets||{}).map(([k,p])=> [k, {
            sign: p.sign, house: p.house, longitude: p.longitude, dignity_score: p.dignity_score,
            retrograde: p.retrograde
          }]));
          // Applying aspects with details
          raw.applying_aspects = Object.entries(f.aspects||{}).filter(([_,v])=> v && v.applying===true)
            .map(([k,v])=> ({ key:k, type:v.type, orb:v.orb, ttp:v.time_to_perfection, within_sign: v.perfection_within_sign }));
          raw.moon_timeline = dash.moon_timeline || {};
          raw.light_mediation = dash.light_mediation || {};
          if (abductionMode) {
            const rulersRaw = f.house_rulers || {};
            const fr = f.houses?.first_ruler || rulersRaw['1'] || rulersRaw[1] || null;
            const pl = f.planets || {};
            const c1 = Number((f.house_cusps||[])[0]);
            const ascSign = isFinite(c1)? signFromLon(c1): null;
            const sign = (pl?.[fr]?.sign) || ascSign;
            const house = (pl?.[fr]?.house != null)? pl[fr].house : 1;
            raw.abduction_pivot = { first_ruler: fr, sign, house, moon: { sign: pl?.Moon?.sign, house: pl?.Moon?.house } };
          }
        } catch(_){}
        lines.push('', 'RAW', JSON.stringify(raw, null, 2));
      }
      return lines.join('\n');
    } catch(e){ return ''; }
  }

  const card = (title, body) => {
    const forensicSectionMeta = {
      'Verdict': { kicker: '§1', meta: 'Signal summary' },
      'Directional Findings': { kicker: '§2', meta: `${replayAxes.length} primary axes · ${rawFindings.length} findings` },
      'Outcome Determination': { kicker: '§3', meta: 'IC and 4th-house matrix' },
      'Victim Analysis': { kicker: '§4', meta: activeCaseTypeLabel },
      'Counterpart Signals': { kicker: '§5', meta: '7th-house symbolic signals' },
      'Relationship Signals': { kicker: '§6', meta: relationshipSnapshot.relationshipType || 'Connection matrix' },
      'Witness & Accomplice Detection': { kicker: '§7', meta: 'Witness pool' },
      'Deception Configuration': { kicker: '§8', meta: 'Coverup and mute signatures' },
      'Abduction Cues': { kicker: '§9', meta: 'Optional local-space cues' },
      'Abduction Map': { kicker: '§10', meta: 'Directional map' },
      'Raw Evidence': { kicker: '§11', meta: 'Audit payload' },
    };
    const meta = forensicSectionMeta[title] || { kicker: 'Forensic Report', meta: '' };
    return (
    <section className="forensic-dossier-card">
      <div className="forensic-dossier-card-head mb-4">
        <div>
          <div className="forensic-dossier-card-kicker">{meta.kicker}</div>
          <h3 className="forensic-dossier-card-title">{title}</h3>
        </div>
        {meta.meta ? <div className="forensic-dossier-card-meta">{meta.meta}</div> : null}
      </div>
      {body}
    </section>
    );
  };

  const ascSign = (() => {
    try {
      const cusps = features?.house_cusps || [];
      if (!Array.isArray(cusps) || cusps.length < 1) return null;
      const L = Number(cusps[0])||0; const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
      return signs[Math.floor(((L%360)+360)%360 / 30)];
    } catch { return null; }
  })();
  const signRuler = {
    Aries:'Mars', Taurus:'Venus', Gemini:'Mercury', Cancer:'Moon', Leo:'Sun', Virgo:'Mercury', Libra:'Venus', Scorpio:'Mars', Sagittarius:'Jupiter', Capricorn:'Saturn', Aquarius:'Saturn', Pisces:'Jupiter'
  };

  // Build a minimal HTML report with optional vector abduction map (offline-safe)
  function buildReportHTML() {
    try {
      let brief = '';
      try { brief = String(buildAIBrief(includeRaw) || ''); } catch { brief = ''; }
      const ts = new Date().toLocaleString();
      const dash = data || {};
      const f = features || {};
      const h = (value) => String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
      // Case header fields
      const caseHeader = (() => {
        const parts = [];
        if (dash?.timestamp) parts.push(`Time: ${h(new Date(dash.timestamp).toLocaleString())}`);
        if (dash?.location) parts.push(`Location: ${h(dash.location)}`);
        if (dash?.timezone_label) parts.push(`TZ: ${h(dash.timezone_label)}`);
        return parts.join(' · ');
      })();
      const svg = (() => {
        try {
          if (!abductionMode) return '';
          const abd = data?.abduction_map || {};
          const origin = abd.origin || {};
          let lat = Number(origin.lat); let lon = Number(origin.lon);
          if (!isFinite(lat) || !isFinite(lon)) return '';
          const bearings = Array.isArray(abd.bearings)? abd.bearings : [];
          const firstRulerName = (()=> {
            try {
              const rulers = f?.house_rulers || {};
              return f?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
            } catch { return null; }
          })();
          const processedBearings = buildProcessedAbductionBearings(bearings, firstRulerName);
          const size = 520; const cx = size/2; const cy = size/2; const outerKm = 40; const kmToPx = (size*0.42)/outerKm;
          const rings = [3,12,40];
          const roleStyle = (role) => {
            const style = getAbductionRoleStyle(role);
            return {
              color: style.color,
              width: style.weight,
              dash: style.dashArray ? String(style.dashArray).replace(/\s+/g, ',') : null,
            };
          };
          const toRad = (v)=> v*Math.PI/180; const norm360=(x)=> (x%360+360)%360;
          const pointAt = (azDeg, km) => {
            const r = Math.min(km, outerKm) * kmToPx;
            const a = toRad(90 - norm360(azDeg));
            const x = cx + r * Math.cos(a);
            const y = cy - r * Math.sin(a);
            return [x, y];
          };
          const lines = processedBearings.slice(0,6).map(b => {
            const az = Number(b?.azimuth_deg); if (!isFinite(az)) return null;
            const st = roleStyle(b?.role);
            const [x2,y2] = pointAt(az, outerKm);
            return `<line x1="${cx}" y1="${cy}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${st.color}" stroke-width="${st.width}" ${st.dash? `stroke-dasharray=\"${st.dash}\"`:''} stroke-linecap="round" />`;
          }).filter(Boolean).join('');
          const ringsSvg = rings.map(km => `<circle cx="${cx}" cy="${cy}" r="${(km*kmToPx).toFixed(1)}" fill="none" stroke="#e5e7eb" stroke-width="1" />`).join('');
          const originDot = `<circle cx="${cx}" cy="${cy}" r="4" fill="#111827" />`;
          const legend = `
            <g transform="translate(${size-170}, 16)" font-size="10" fill="#111827">
              <text x="0" y="0">Legend</text>
              ${getAbductionLegendEntries().map((entry, i)=>{
                const r = entry.role;
                const s=roleStyle(r); const y= (i+1)*14;
                return `<g transform=\"translate(0,${y})\"><line x1=\"0\" y1=\"-4\" x2=\"22\" y2=\"-4\" stroke=\"${s.color}\" stroke-width=\"2\" ${s.dash?`stroke-dasharray=\"${s.dash}\"`:''} /><text x=\"26\" y=\"0\">${h(entry.legendLabel)}</text></g>`;
              }).join('')}
            </g>`;
          return `<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"${size}\" height=\"${size}\" viewBox=\"0 0 ${size} ${size}\"><rect x=\"0\" y=\"0\" width=\"${size}\" height=\"${size}\" fill=\"#ffffff\" />${ringsSvg}${originDot}${lines}${legend}</svg>`;
        } catch { return ''; }
      })();
      // Bearings table (top 6)
      const bearingsTable = (() => {
        try {
          if (!abductionMode) return '';
          const abd = data?.abduction_map || {};
          const bearings = Array.isArray(abd.bearings)? abd.bearings : [];
          const firstRulerName = (()=> {
            try {
              const rulers = f?.house_rulers || {};
              return f?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
            } catch { return null; }
          })();
          const processedBearings = buildProcessedAbductionBearings(bearings, firstRulerName);
          if (!processedBearings.length) return '';
          const pls = f?.planets || {};
          const rows = processedBearings.slice(0,6).map((b)=>{
            const p = pls?.[b.planet] || {};
            const house = p?.house!=null? `H${p.house}` : 'H-';
            const sign = p?.sign || '-';
            const az = (b?.azimuth_deg!=null)? `${Number(b.azimuth_deg).toFixed(1)}°` : '-';
            const alt = (b?.altitude_deg!=null)? `${Number(b.altitude_deg).toFixed(1)}°` : '-';
            const w = (b?.weight!=null)? Number(b.weight).toFixed(2) : '-';
            return `<tr><td>${h(formatAbductionBearingRoleLabel(b))}</td><td>${h(b.planet||'-')}</td><td style=\"text-align:right\">${h(az)}</td><td style=\"text-align:right\">${h(alt)}</td><td>${h(`${house} ${sign}`)}</td><td style=\"text-align:right\">${h(w)}</td></tr>`;
          }).join('');
          return rows ? `<h2>Abduction Bearings</h2><table class=\"tbl\"><thead><tr><th>Role</th><th>Planet</th><th>Az</th><th>Alt</th><th>Pos</th><th>W</th></tr></thead><tbody>${rows}</tbody></table>` : '';
        } catch { return ''; }
      })();
      // Build tile-like sections (textual)
      const victimSec = (() => {
        try {
          const cusps = f?.house_cusps || [];
          const ascLon = Number(cusps?.[0]);
          const ascSign = isFinite(ascLon) ? signFromLon(ascLon) : '-';
          const rulers = f?.house_rulers || {};
          const firstRuler = f?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
          const co = ['Moon', ...(caseType==='child'? ['Mercury']: [])];
          const mi = f?.planets?.Moon || {};
          const mSign = mi?.sign || '-';
          const mDeg = isFinite(mi?.longitude) ? degreeTextFromLon(mi.longitude) : '-';
          const mHouse = mi?.house ?? '-';
          const voc = (()=>{ try { const mt = dash?.moon_timeline; return (mt && typeof mt.in_voc === 'boolean') ? mt.in_voc : Boolean((dash?.moon || f?.moon || {}).void_of_course); } catch{ return false; } })();
          const via = Boolean(mi?.via_combusta);
          // Malefic danger lines
          const a = f?.aspects || {};
          const mal = Object.entries(a).filter(([k,v])=> v && (k.startsWith('Moon_to_') || k.endsWith('_to_Moon')))
            .map(([k,v])=>{ const [p1,p2]=k.split('_to_'); const other=(p1==='Moon'? p2: p1); return { other, type: String(v.type||''), applying: v.applying===true }; })
            .filter(x=> (x.other==='Mars'||x.other==='Saturn') && (x.type==='square'||x.type==='opposition'))
            .map(x=> `${x.type} ${x.other}${x.applying? ' (app)':''}`);
          return `<h2>Victim Analysis</h2>
            <table class=\"tbl\"><tbody>
              <tr><td>ASC Sign</td><td>${h(ascSign)}</td></tr>
              <tr><td>Primary Ruler</td><td>${h(firstRuler||'-')}</td></tr>
              <tr><td>Co‑rulers</td><td>${h(co.join(', '))}</td></tr>
              <tr><td>Moon</td><td>${h(`${mSign} ${mDeg} (H${mHouse}) · VoC ${voc? 'Yes':'No'} · Via combusta ${via? 'Yes':'No'}`)}</td></tr>
              <tr><td>Danger (malefics)</td><td>${h(mal.length? mal.join(' · '): '-')}</td></tr>
            </tbody></table>`;
        } catch { return ''; }
      })();

      const perpSec = (() => {
        try {
          const rulers = f?.house_rulers || {};
          const seventhRuler = f?.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
          const pl = f?.planets || {};
          const r = pl?.[seventhRuler] || {};
          const cusp7 = Number((f?.house_cusps||[])[6]);
          const cusp7Sign = isFinite(cusp7)? signFromLon(cusp7): '-';
          const cusp7Deg = isFinite(cusp7)? degreeTextFromLon(cusp7): '-';
          const h7List = Object.entries(pl).filter(([,p])=> p?.house===7).map(([n])=> n);
          const sign = r?.sign || '-'; const deg = isFinite(r?.longitude)? degreeTextFromLon(r.longitude): '-'; const house = r?.house ?? '-';
          const solar = dash?.features?.solar || f?.solar || {};
          const inSolar = (k, p) => Array.isArray(solar?.[k]) && solar[k].includes(p);
          const dignFlags = (() => { const raw=String(r?.essential_dignity_raw||'').toLowerCase(); const tags=new Set((Array.isArray(r?.dignities)? r.dignities: []).map(t=> String(t).toLowerCase())); const out=[]; if (raw.includes('domicile')||raw.includes('ruler')||tags.has('domicile')||tags.has('rulership')) out.push('Rulership'); if (raw.includes('exalt')||Array.from(tags).some(t=> t.includes('exalt'))) out.push('Exaltation'); if (Array.from(tags).some(t=> t.includes('triplicity'))) out.push('Triplicity'); if (Array.from(tags).some(t=> t.includes('term')||t.includes('bound'))) out.push('Term'); if (Array.from(tags).some(t=> t.includes('face')||t.includes('decan'))) out.push('Face'); if (raw.includes('detriment')||tags.has('detriment')) out.push('Detriment'); if (raw.includes('fall')||tags.has('fall')) out.push('Fall'); return out.length? out: ['Neutral']; })();
          const asp = f?.aspects || {};
          const collectBy = (planet) => Object.entries(asp)
            .filter(([k, v]) => v && (k.includes(`_to_${planet}`) || k.startsWith(`${planet}_to_`)))
            .map(([, v]) => ({ type: v?.type, applying: v?.applying }));
          const aspectBucket = (planet) => formatForensicAspectLabels(collectBy(planet));
          return `<h2>7th-house Counterpart Signals</h2>
            <table class=\"tbl\"><tbody>
              <tr><td>7th-house cusp</td><td>${h(`${cusp7Sign} ${cusp7Deg} | ruler ${seventhRuler||'-'}`)}</td></tr>
              <tr><td>7th-house co-signifiers</td><td>${h(h7List.length? h7List.join(', '): '-')}</td></tr>
              <tr><td>Ruler placement</td><td>${h(`${sign} ${deg} (H${house})`)}</td></tr>
              <tr><td>Dignity</td><td>${h(dignFlags.join(', ') || '-')}</td></tr>
              <tr><td>State</td><td>${h(`${r?.retrograde? 'Retrograde':'Direct'}${inSolar('cazimi', seventhRuler)? ' | Cazimi':''}${inSolar('combustion', seventhRuler)? ' | Combust':''}${inSolar('under_beams', seventhRuler)? ' | Under beams':''}`)}</td></tr>
              <tr><td>Malefic/benefic contacts</td><td>${h(`Saturn: ${aspectBucket('Saturn')} | Mars: ${aspectBucket('Mars')} | Jupiter: ${aspectBucket('Jupiter')} | Venus: ${aspectBucket('Venus')}`)}</td></tr>
            </tbody></table>`;
        } catch { return ''; }
      })();

      const relationshipSec = (() => {
        try {
          const rulers = f?.house_rulers || {};
          const firstRuler = f?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
          const seventhRuler = f?.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
          const sr = { Aries:'Mars', Taurus:'Venus', Gemini:'Mercury', Cancer:'Moon', Leo:'Sun', Virgo:'Mercury', Libra:'Venus', Scorpio:'Mars', Sagittarius:'Jupiter', Capricorn:'Saturn', Aquarius:'Saturn', Pisces:'Jupiter' };
          const exaltation = { Sun:'Aries', Moon:'Taurus', Mercury:'Virgo', Venus:'Pisces', Mars:'Capricorn', Jupiter:'Cancer', Saturn:'Libra' };
          const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
          const opp = (s) => signs[(signs.indexOf(s)+6)%12] || null;
          const triOf = (sign) => {
            if (!sign) return null;
            if (['Aries','Leo','Sagittarius'].includes(sign)) return 'Fire';
            if (['Taurus','Virgo','Capricorn'].includes(sign)) return 'Earth';
            if (['Gemini','Libra','Aquarius'].includes(sign)) return 'Air';
            if (['Cancer','Scorpio','Pisces'].includes(sign)) return 'Water';
            return null;
          };
          const planets = f?.planets || {};
          const victimSign = planets?.[firstRuler]?.sign; const perpSign = planets?.[seventhRuler]?.sign;
          const victimHouse = planets?.[firstRuler]?.house; const perpHouse = planets?.[seventhRuler]?.house;
          const recData = dash?.receptions || {};
          const mutual = Array.isArray(recData.mutual)? recData.mutual : [];
          const uni = Array.isArray(recData.top_unilateral)? recData.top_unilateral : [];
          const directVictRulesPerp = victimSign && sr[perpSign] === firstRuler;
          const directPerpRulesVict = perpSign && sr[victimSign] === seventhRuler;
          const isMutual = mutual.some(m => (m.p1===firstRuler && m.p2===seventhRuler) || (m.p1===seventhRuler && m.p2===firstRuler));
          const level3 = victimSign && perpSign && (triOf(victimSign) === triOf(perpSign));
          const perpExaltSign = exaltation[seventhRuler];
          const victExaltSign = exaltation[firstRuler];
          const level4_victim_in_exalt_of_perp = victimSign && (victimSign === perpExaltSign);
          const level4_perp_in_exalt_of_victim = perpSign && (perpSign === victExaltSign);
          const level4_victim_in_fall_of_perp = victimSign && (victimSign === opp(perpExaltSign));
          const level4_perp_in_fall_of_victim = perpSign && (perpSign === opp(victExaltSign));
          const houseFlags = [];
          if (victimHouse===1) houseFlags.push('Victim ruler in 1st');
          if (victimHouse===7) houseFlags.push('Victim ruler in 7th');
          if (victimHouse===4||victimHouse===10) houseFlags.push('Victim ruler in 4th/10th');
          if (perpHouse===1) houseFlags.push('Perp ruler in 1st');
          if (perpHouse===4||perpHouse===10) houseFlags.push('Perp ruler in 4th/10th');
          if (perpHouse===7) houseFlags.push('Perp ruler in 7th');
          const sameHouse = (victimHouse!=null && perpHouse!=null && victimHouse===perpHouse);
          if (sameHouse) houseFlags.push('Both rulers in same house');
          const aspMap = f?.aspects || {};
          const a = aspMap[`${firstRuler}_to_${seventhRuler}`] || aspMap[`${seventhRuler}_to_${firstRuler}`] || null;
          const aspType = a?.type || null;
          const aspectFlags = [];
          if (aspType) {
            const easy=['conjunction','trine','sextile']; const hard=['square','opposition'];
            if (easy.includes(aspType)) aspectFlags.push(`Harmonious (${aspType})`);
            if (hard.includes(aspType)) aspectFlags.push(`Stressful (${aspType})`);
            if (a?.applying===true) aspectFlags.push('Applying');
          } else { aspectFlags.push('No direct aspect'); }
          const relationshipRows = buildRelationshipDisplayRows({
            directVictRulesPerp,
            directPerpRulesVict,
            isMutual,
            level3,
            exaltationFallFlags: [
              level4_victim_in_exalt_of_perp ? 'victim in exaltation of perpetrator' : null,
              level4_perp_in_exalt_of_victim ? 'perpetrator in exaltation of victim' : null,
              level4_victim_in_fall_of_perp ? 'victim in fall of perpetrator' : null,
              level4_perp_in_fall_of_victim ? 'perpetrator in fall of victim' : null,
            ].filter(Boolean),
            houseConnections: houseFlags,
            aspectTies: aspectFlags,
          });
          const lines = [
            `Rulership links: ${relationshipRows.rulershipLinks}`,
            `Mutual reception: ${relationshipRows.mutualReception}`,
            `Shared triplicity: ${relationshipRows.sharedTriplicity}`,
            `Exaltation/fall ties: ${relationshipRows.exaltationFallTies}`,
            `House overlap: ${relationshipRows.houseOverlap}`,
            `Aspect ties: ${relationshipRows.aspectTies}`,
          ];
          return `<h2>Relationship Signals</h2><div class=\"text\">${lines.map(l=> `<div>${h(l)}</div>`).join('')}</div>`;
        } catch { return ''; }
      })();

      const witnessSec = (() => {
        try {
          const pls = f?.planets || {};
          const houseList = (h)=> Object.entries(pls).filter(([,p])=> p?.house===h).map(([n])=> n);
          const mercuryHouse = pls?.Mercury?.house || '-';
          const witnesses = ['Mercury', ...houseList(3)];
          const associates = houseList(11);
          const hidden = [...houseList(6), ...houseList(12)];
          return `<h2>Witness & Accomplice</h2>
            <table class=\"tbl\"><tbody>
              <tr><td>Mercury (witness)</td><td>${h(`H${mercuryHouse}`)}</td></tr>
              <tr><td>3rd (neighbors/local)</td><td>${h(witnesses.join(', ')||'-')}</td></tr>
              <tr><td>11th (associates)</td><td>${h(associates.join(', ')||'-')}</td></tr>
              <tr><td>6th/12th (hidden)</td><td>${h(hidden.join(', ')||'-')}</td></tr>
            </tbody></table>`;
        } catch { return ''; }
      })();

      const finalSec = (() => {
        try {
          const cusps = f?.house_cusps || [];
          const cusp4 = Number(cusps?.[3]);
          const icDeg = isFinite(cusp4) ? degreeTextFromLon(cusp4) : '-';
          const cusp4Sign = isFinite(cusp4) ? signFromLon(cusp4) : '-';
          const icDict = dash?.ic_sign_meanings || {};
          const icExpl = cusp4Sign && icDict?.[cusp4Sign]?.outcome;
          const ruler4 = f?.house_rulers?.['4'] || f?.house_rulers?.[4] || null;
          const ruler4House = ruler4 ? f?.planets?.[ruler4]?.house : null;
          const icRulerDict = dash?.ic_ruler_house_meanings || {};
          const icRulerExpl = (ruler4House != null) ? (icRulerDict?.[String(ruler4House)]?.outcome) : null;
          const planets = f?.planets || {};
          const in4All = Object.entries(planets).filter(([,p])=> p?.house===4).map(([n])=> n);
          return `<h2>Final outcome determination</h2>
            <table class=\"tbl\"><tbody>
              <tr><td>IC</td><td>${h(`${cusp4Sign} ${icDeg}${icExpl? ` - ${icExpl}`:''}`)}</td></tr>
              <tr><td>IC ruler</td><td>${h(`${ruler4||'-'}${ruler4House? ` in H${ruler4House}`:''}${icRulerExpl? ` - ${icRulerExpl}`:''}`)}</td></tr>
              <tr><td>Planets in 4th</td><td>${h(in4All.join(', ')||'-')}</td></tr>
            </tbody></table>`;
        } catch { return ''; }
      })();

      const css = `
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; color: #111827; }
        .container { padding: 24px; }
        h1 { font-size: 20px; margin: 0 0 4px; }
        h2 { font-size: 14px; margin: 16px 0 4px; }
        .muted { color: #6b7280; font-size: 12px; }
        pre { white-space: pre-wrap; font-size: 12px; line-height: 1.5; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: #fff; }
        .map { margin-top: 12px; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
        .sep { height: 1px; background: #e5e7eb; margin: 12px 0; }
        .tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
        .tbl th, .tbl td { border: 1px solid #e5e7eb; padding: 6px 8px; }
        .tbl thead { background: #f8fafc; }
        .text div { margin: 4px 0; }
      `;
      const safeBrief = brief ? h(brief) : '-';
      return `<!doctype html><html><head><meta charset=\"utf-8\" /><title>Forensic Astrology Report</title><style>${css}</style></head>
        <body><div class=\"container\">
          <h1>Forensic Astrology Report</h1>
          <div class=\"muted\">Generated ${h(ts)}${caseHeader? ` · ${caseHeader}`:''}</div>
          <div class=\"sep\"></div>
          <h2>Summary</h2>
          <pre>${safeBrief}</pre>
          ${victimSec}
          ${perpSec}
          ${relationshipSec}
          ${witnessSec}
          ${finalSec}
          ${svg ? `<h2>Abduction Map</h2><div class=\"map\">${svg}</div>` : ''}
          ${bearingsTable}
        </div></body></html>`;
    } catch { return '<html><body>Error</body></html>'; }
  }
  const primaryRuler = features?.houses?.first_ruler || (ascSign ? signRuler[ascSign] : null);
  const coRulers = (() => {
    const list = ['Moon'];
    if (ascSign === 'Cancer') return list; // special case (avoid over-adding here; we will dedupe later)
    if (caseType === 'child' && !list.includes('Mercury')) list.push('Mercury');
    return list;
  })();
  // Dominance helpers from API
  const domMap = (data?.dominance && data.dominance.planets) ? data.dominance.planets : {};
  const domInfo = (p) => (p && domMap && domMap[p]) ? domMap[p] : null;
  const dign = (pname) => {
    try { return Number(features?.planets?.[pname]?.dignity_score)||0; } catch { return 0; }
  };

  // Describe any aspects between victim ruler and malefics (Mars/Saturn), both directions
  const maleficThreatDetails = (pname) => {
    try {
      const a = features?.aspects || {};
      const keys = Object.keys(a).filter(k => k.startsWith(pname+"_to_") || k.endsWith("_to_"+pname));
      const out = [];
      for (const k of keys) {
        const rec = a[k] || {};
        const [p1, p2] = k.split('_to_');
        const other = (p1 === pname) ? p2 : p1;
        if (!['Mars','Saturn'].includes(other)) continue;
        const typ = String(rec.type || '').toLowerCase();
        if (!typ) continue;
        const app = rec.applying === true;
        const orb = (typeof rec.orb === 'number') ? `${Number(rec.orb).toFixed(1)}°` : null;
        out.push(`${other} ${typ}${app ? ' (app)' : ''}${orb ? ' · '+orb : ''}`);
      }
      return out;
    } catch { return []; }
  };
  const survival = (() => {
    return summarizeForensicSurvivalSignal({ forensicResult: data });
  })();
  const relationshipSnapshot = (() => {
    try {
      const rulers = features?.house_rulers || {};
      const firstRuler = features?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
      const seventhRuler = features?.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
      const planets = features?.planets || {};
      const victimHouse = firstRuler ? planets?.[firstRuler]?.house : null;
      const perpHouse = seventhRuler ? planets?.[seventhRuler]?.house : null;
      const seventhHousePlanets = Object.entries(planets)
        .filter(([, planet]) => Number(planet?.house) === 7)
        .map(([name]) => name);
      const mutual = Array.isArray(data?.receptions?.mutual) ? data.receptions.mutual : [];
      const isMutual = mutual.some((item) => (
        (item?.p1 === firstRuler && item?.p2 === seventhRuler) ||
        (item?.p1 === seventhRuler && item?.p2 === firstRuler)
      ));
      return summarizeForensicRelationshipLink({
        score: 0,
        victimHouse,
        perpHouse,
        seventhHousePlanets,
        isMutual,
        forensicResult: data || {},
      });
    } catch {
      return summarizeForensicRelationshipLink({ forensicResult: data || {} });
    }
  })();
  const relationshipInsight = useMemo(() => {
    try {
      const rulers = features?.house_rulers || {};
      const firstRuler = features?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
      const seventhRuler = features?.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
      const planets = features?.planets || {};
      const firstInfo = firstRuler ? planets?.[firstRuler] || {} : {};
      const seventhInfo = seventhRuler ? planets?.[seventhRuler] || {} : {};
      const signRulers = {
        Aries: 'Mars',
        Taurus: 'Venus',
        Gemini: 'Mercury',
        Cancer: 'Moon',
        Leo: 'Sun',
        Virgo: 'Mercury',
        Libra: 'Venus',
        Scorpio: 'Mars',
        Sagittarius: 'Jupiter',
        Capricorn: 'Saturn',
        Aquarius: 'Saturn',
        Pisces: 'Jupiter',
      };
      const triOf = (sign) => {
        if (['Aries','Leo','Sagittarius'].includes(sign)) return 'Fire';
        if (['Taurus','Virgo','Capricorn'].includes(sign)) return 'Earth';
        if (['Gemini','Libra','Aquarius'].includes(sign)) return 'Air';
        if (['Cancer','Scorpio','Pisces'].includes(sign)) return 'Water';
        return null;
      };
      const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
      const oppositeSign = (sign) => {
        const index = signs.indexOf(sign);
        return index >= 0 ? signs[(index + 6) % 12] : null;
      };
      const exaltation = { Sun:'Aries', Moon:'Taurus', Mercury:'Virgo', Venus:'Pisces', Mars:'Capricorn', Jupiter:'Cancer', Saturn:'Libra' };
      const aspects = features?.aspects || {};
      const aspectTo = (target) => collectRelationshipAspectContacts({
        aspects,
        source: seventhRuler,
        target,
        applyingLabel: ' applying',
      });
      const directAspect = aspects?.[`${firstRuler}_to_${seventhRuler}`] || aspects?.[`${seventhRuler}_to_${firstRuler}`] || null;
      const recData = data?.receptions || {};
      const mutual = Array.isArray(recData.mutual) ? recData.mutual : [];
      const uni = Array.isArray(recData.top_unilateral) ? recData.top_unilateral : [];
      const seventhHousePlanets = Object.entries(planets)
        .filter(([, planet]) => Number(planet?.house) === 7)
        .map(([name]) => name);
      const victimHouse = firstInfo?.house;
      const perpHouse = seventhInfo?.house;
      const sameHouse = victimHouse != null && perpHouse != null && Number(victimHouse) === Number(perpHouse);
      const isMutual = mutual.some((item) => (
        (item?.p1 === firstRuler && item?.p2 === seventhRuler) ||
        (item?.p1 === seventhRuler && item?.p2 === firstRuler)
      ));
      const directVictRulesPerp = Boolean(firstInfo?.sign && seventhInfo?.sign && signRulers[seventhInfo.sign] === firstRuler);
      const directPerpRulesVict = Boolean(firstInfo?.sign && seventhInfo?.sign && signRulers[firstInfo.sign] === seventhRuler);
      const level3 = Boolean(firstInfo?.sign && seventhInfo?.sign && triOf(firstInfo.sign) === triOf(seventhInfo.sign));
      const level4VictimInExaltOfPerp = Boolean(firstInfo?.sign && firstInfo.sign === exaltation[seventhRuler]);
      const level4PerpInExaltOfVictim = Boolean(seventhInfo?.sign && seventhInfo.sign === exaltation[firstRuler]);
      const level4VictimInFallOfPerp = Boolean(firstInfo?.sign && firstInfo.sign === oppositeSign(exaltation[seventhRuler]));
      const level4PerpInFallOfVictim = Boolean(seventhInfo?.sign && seventhInfo.sign === oppositeSign(exaltation[firstRuler]));
      const isRulerReception = (item) => (
        (item?.receiving === firstRuler && item?.received === seventhRuler) ||
        (item?.receiving === seventhRuler && item?.received === firstRuler)
      );
      const directionalReception = uni.some(isRulerReception);
      const level5Terms = uni.some((item) => (
        isRulerReception(item) &&
        (item?.dignities || []).includes('term')
      ));
      const criticalFamilyHouse = (
        (Number(victimHouse) === 4 && Number(perpHouse) === 4) ||
        (Number(victimHouse) === 10 && Number(perpHouse) === 10)
      );
      const degreeInt = (name) => {
        const degree = planets?.[name]?.degree_in_sign;
        return typeof degree === 'number' ? Math.round(degree) : null;
      };
      const victimDegree = degreeInt(firstRuler);
      const perpDegree = degreeInt(seventhRuler);
      const degreeStarCues = [
        victimDegree === 0 ? '0 degree new situation (victim)' : null,
        perpDegree === 0 ? '0 degree new situation (perpetrator)' : null,
        victimDegree === 15 ? '15 degree marker (victim)' : null,
        perpDegree === 15 ? '15 degree marker (perpetrator)' : null,
        victimDegree === 29 ? '29 degree crisis (victim)' : null,
        perpDegree === 29 ? '29 degree crisis (perpetrator)' : null,
      ].filter(Boolean);
      const starHits = data?.relationship_star_hits || {};
      const starNames = (hits) => (Array.isArray(hits) ? hits.map((hit) => hit?.name).filter(Boolean) : []);
      const ascStars = starNames(starHits.asc_ruler);
      const dscStars = starNames(starHits.dsc_ruler);
      if (ascStars.length) degreeStarCues.push(`ASC ruler on ${ascStars.join('/')}`);
      if (dscStars.length) degreeStarCues.push(`DSC ruler on ${dscStars.join('/')}`);
      const violentStars = new Set(['Algol', 'Antares']);
      const protectiveStars = new Set(['Spica']);
      const hasViolentStar = [...ascStars, ...dscStars].some((name) => violentStars.has(name));
      const hasProtectiveStar = [...ascStars, ...dscStars].some((name) => protectiveStars.has(name));
      const moonDispositorTiesPerp = Boolean(features?.moon?.dispositor_to_seventh_ruler_type);
      const moonDispositorHardContact = Boolean(features?.moon?.dispositor_to_seventh_ruler_hard);
      const moonDispositorCue = moonDispositorTiesPerp
        ? `Moon dispositor ${features?.moon?.dispositor || 'ruler'} ${features?.moon?.dispositor_to_seventh_ruler_type || 'contacts'} ${seventhRuler || '7th ruler'}`
        : null;
      const relationshipScore = scoreForensicRelationshipLink({
        victimHouse,
        perpHouse,
        sameHouse,
        directVictRulesPerp,
        directPerpRulesVict,
        isMutual,
        level3,
        level4VictimInExaltOfPerp,
        level4PerpInExaltOfVictim,
        level4VictimInFallOfPerp,
        level4PerpInFallOfVictim,
        directionalReception,
        level5Terms,
        criticalFamilyHouse,
        lightMediation: data?.light_mediation,
        seventhHousePlanets,
        aspectType: directAspect?.type,
        aspect: directAspect,
        criticalDegree: degreeStarCues.some((cue) => /degree|crisis|marker/i.test(cue)),
        hasViolentStar,
        hasProtectiveStar,
        moonDispositorTiesPerp,
        moonDispositorHardContact,
        victimSignificators: [firstRuler, 'Moon'].filter(Boolean),
        perpetratorSignificators: [seventhRuler].filter(Boolean),
      });
      const summary = summarizeForensicRelationshipLink({
        score: relationshipScore.score,
        victimHouse,
        perpHouse,
        seventhHousePlanets,
        isMutual,
        forensicResult: data || {},
      });
      const backendRelationshipStatus = summary?.relationshipStatus;
      const backendPrimaryLabel = backendRelationshipStatus?.primary_label;
      const backendPrimaryScore = Number(backendRelationshipStatus?.scores?.[backendPrimaryLabel]);
      const displayScore = Number.isFinite(backendPrimaryScore)
        ? backendPrimaryScore
        : relationshipScore.score;
      const backendPrimaryEvidence = Array.isArray(backendRelationshipStatus?.evidence?.[backendPrimaryLabel])
        ? backendRelationshipStatus.evidence[backendPrimaryLabel]
        : [];
      const displayReasons = backendPrimaryEvidence.length
        ? backendPrimaryEvidence
        : relationshipScore.reasons;
      const houseConnections = [
        victimHouse != null ? `victim ruler in H${victimHouse}` : null,
        perpHouse != null ? `perpetrator ruler in H${perpHouse}` : null,
        sameHouse ? 'both rulers in same house' : null,
        criticalFamilyHouse ? 'shared family-house placement' : null,
      ].filter(Boolean);
      const rows = buildRelationshipDisplayRows({
        firstRuler,
        moonContacts: aspectTo('Moon'),
        ascRulerContacts: aspectTo(firstRuler),
        directVictRulesPerp,
        directPerpRulesVict,
        isMutual,
        level3,
        exaltationFallFlags: [
          level4VictimInExaltOfPerp ? 'victim in exaltation of perpetrator' : null,
          level4PerpInExaltOfVictim ? 'perpetrator in exaltation of victim' : null,
          level4VictimInFallOfPerp ? 'victim in fall of perpetrator' : null,
          level4PerpInFallOfVictim ? 'perpetrator in fall of victim' : null,
        ].filter(Boolean),
        level5Terms,
        houseConnections,
        traditionalCues: [
          seventhHousePlanets.length ? `7th-house planets: ${seventhHousePlanets.join(', ')}` : null,
          moonDispositorCue,
        ].filter(Boolean),
        aspectTies: directAspect ? [`${directAspect.type || 'contact'} between rulers${directAspect.applying === true ? ' applying' : ''}`] : ['no direct ruler aspect'],
        degreeStarCues,
        score: displayScore,
        relationshipType: summary.relationshipType,
        confidence: summary.confidence,
      });
      return {
        rows,
        score: displayScore,
        reasons: displayReasons,
        summary,
      };
    } catch {
      return {
        rows: null,
        score: 0,
        reasons: [],
        summary: relationshipSnapshot,
      };
    }
  }, [data, features, relationshipSnapshot]);
  const fatalPressureDominant = Boolean(
    survival.fatalOverride ||
    survival.outcomeBand === 'fatal_pressure_dominant' ||
    /fatal pressure/i.test(String(survival.note || ''))
  );
  const survivabilitySummaryText = [
    `Survivability signal: ${survival.level || '-'}`,
    typeof survival.score === 'number' ? `(${survival.score >= 0 ? '+' : ''}${survival.score})` : null,
    survival.outcomeBand ? formatSurvivabilityBandLabel(survival.outcomeBand) : null,
    fatalPressureDominant ? '(fatal pressure dominates)' : null,
  ].filter(Boolean).join(' ');
  const survivalBreakdown = survival.breakdown || {};
  const lightMediationImpact = survival.lightMediationImpact && typeof survival.lightMediationImpact === 'object'
    ? survival.lightMediationImpact
    : null;
  const showLightMediationImpact = Boolean(
    lightMediationImpact &&
    (
      lightMediationImpact.effect ||
      lightMediationImpact.score_delta ||
      lightMediationImpact.light_mediation_score
    ) &&
    lightMediationImpact.effect !== 'none'
  );
  const lightMediationImpactTone = lightMediationImpact?.effect === 'fatal_pressure' ? 'is-rose' : 'is-teal';
  const categoryCount = (name) => Number(data?.categories?.[name] || 0);
  const symbolicRuleScore = Number.isFinite(Number(survival.score))
    ? `${Number(survival.score) >= 0 ? '+' : ''}${Number(survival.score)}`
    : '-';
  const survivalToneClass = survival.level === 'Lower' ? 'is-rose' : survival.level === 'Higher' ? 'is-teal' : 'is-amber';
  const outcomeBandLabel = survival.outcomeBand ? formatSurvivabilityBandLabel(survival.outcomeBand) : 'Pending';
  const caseTypeOptions = [
    { value: 'general', label: 'General' },
    { value: 'adult_female', label: 'Adult Female' },
    { value: 'child', label: 'Child' },
  ];
  const forensicTabs = [
    { id: 'findings', label: 'Findings', count: rawFindings.length || null },
    { id: 'victim', label: 'Victim' },
    { id: 'perpetrator', label: 'Counterpart' },
    { id: 'relationship', label: 'Relationship' },
    { id: 'witnesses', label: 'Witnesses', count: categoryCount('Witness') || null },
    { id: 'deception', label: 'Deception', count: categoryCount('Deception') || null },
    { id: 'abduction', label: 'Abduction' },
    { id: 'raw', label: 'Raw Evidence' },
  ];
  const showForensicSection = (...ids) => ids.includes(forensicTab);
  const caseTimestamp = data?.timestamp || effectiveForensicClockContext.datetime || '';
  const caseLocation = data?.location || effectiveForensicClockContext.location || 'Current chart';
  const caseTimezoneName =
    resolveAstroClockTimezone(data?.timezone, data?.timezone_label) ||
    resolveAstroClockTimezone(
      effectiveForensicClockContext.timezone,
      effectiveForensicClockContext.timezone_label,
    );
  const caseTimezone = data?.timezone_label || data?.timezone || effectiveForensicClockContext.timezone || '';
  const caseMode = effectiveForensicClockContext.mode || 'current';
  const caseHouseSystem = effectiveForensicClockContext.houseSystem || effectiveForensicClockContext.house_system_code || '';
  const caseTimestampParts = formatForensicTimestampParts(caseTimestamp, caseTimezoneName || caseTimezone);
  const caseDateLabel = caseTimestampParts.datePart || 'Date pending';
  const caseTimeLabel = caseTimestampParts.timePart || 'Time pending';
  const caseLocationLabel = formatForensicLocationLabel(caseLocation);
  const chartSourceLabel = chartSource === 'snap' ? 'Saved Snap' : 'Current Chart';
  const selectedSnapParts = getForensicSnapMetaParts(selectedSnap);
  const caseScopeLabel = `${chartSourceLabel} · Traditional + Modern${caseHouseSystem ? ` · ${caseHouseSystem}` : ''}`;
  const activeCaseTypeLabel = caseTypeOptions.find((option) => option.value === caseType)?.label || caseType;
  const hasSnapOptions = eligibleSnapOptions.length > 0;
  const switchForensicToSnap = () => {
    setChartSource('snap');
    if (!selectedSnapId && hasSnapOptions) {
      setSelectedSnapId(String(eligibleSnapOptions[0].id || ''));
    }
  };
  const rawControlActive = includeRaw || forensicTab === 'raw';
  const ascRulerPlacement = (
    data?.asc_ruler_placement && typeof data.asc_ruler_placement === 'object'
      ? data.asc_ruler_placement
      : (features?.asc_ruler_placement && typeof features.asc_ruler_placement === 'object' ? features.asc_ruler_placement : {})
  );
  const ascRulerPlacementCues = Array.isArray(ascRulerPlacement?.cues) ? ascRulerPlacement.cues.filter(Boolean) : [];
  const rawEvidenceGroups = [
    {
      title: 'Case Context',
      payload: {
        timestamp: data?.timestamp || effectiveForensicClockContext.datetime,
        location: data?.location || effectiveForensicClockContext.location,
        timezone: data?.timezone_label || data?.timezone || effectiveForensicClockContext.timezone,
        case_type: caseType,
        chart_source: chartSource,
        snap_id: chartSource === 'snap' ? selectedSnapId : undefined,
        mode: caseMode,
        house_system: caseHouseSystem,
      },
    },
    {
      title: 'Case Signals',
      payload: {
        categories: data?.categories,
        axes: replayAxes,
        findings: rawFindings,
      },
    },
    {
      title: 'Chart Features',
      payload: features,
    },
    {
      title: 'Relationship & Survivability',
      payload: {
        dominance: data?.dominance,
        survivability: data?.survivability,
        receptions: data?.receptions,
        light_mediation: data?.light_mediation,
        relationship_status: data?.relationship_status,
        relationship_star_hits: data?.relationship_star_hits,
      },
    },
    {
      title: 'Abduction Map',
      payload: {
        abduction_map: data?.abduction_map,
        abduction_map_error: data?.abduction_map_error,
      },
    },
  ];
  const formatFindingEvidenceKey = (key) => String(key || '')
    .split('.')
    .filter(Boolean)
    .map((part) => formatForensicDisplayLabel(part))
    .join(' / ');
  const formatFindingEvidenceValue = (value, depth = 0) => {
    if (value == null || value === '') return '-';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '-';
    if (Array.isArray(value)) {
      if (!value.length) return '-';
      const parts = value
        .slice(0, 4)
        .map((item) => formatFindingEvidenceValue(item, depth + 1))
        .filter((part) => part && part !== '-');
      if (value.length > 4) parts.push(`+${value.length - 4} more`);
      return parts.join(' | ') || '-';
    }
    if (typeof value === 'object') {
      if (depth > 1) {
        try {
          return cleanForensicDisplayText(JSON.stringify(value));
        } catch (_) {
          return '-';
        }
      }
      const entries = Object.entries(value);
      if (!entries.length) return '-';
      const parts = entries
        .slice(0, 4)
        .map(([key, item]) => `${formatForensicDisplayLabel(key)}: ${formatFindingEvidenceValue(item, depth + 1)}`)
        .filter(Boolean);
      if (entries.length > 4) parts.push(`+${entries.length - 4} more`);
      return parts.join(' | ') || '-';
    }
    return cleanForensicDisplayText(value);
  };
  const buildFindingEvidenceRows = (finding) => (
    Object.entries(finding?.evidence && typeof finding.evidence === 'object' ? finding.evidence : {})
      .map(([key, value]) => ({
        key: formatFindingEvidenceKey(key),
        value: formatFindingEvidenceValue(value),
      }))
      .filter((row) => row.key && row.value && row.value !== '-')
      .slice(0, 5)
  );
  const getFindingToneClass = (finding) => {
    const blob = `${finding?.category || ''} ${finding?.title || ''}`.toLowerCase();
    if (/violence|homicide|death|malefic|stress|headwind|danger|fatal/.test(blob)) return 'is-rose';
    if (/deception|abduction|missing|water|drowning|child|children|accident|disaster/.test(blob)) return 'is-amber';
    if (/public|authority|family|household|relationship|associate|witness/.test(blob)) return 'is-teal';
    return '';
  };

  return (
    <div className="forensic-dossier-overlay">
      <div className="forensic-dossier forensic-dossier-shell">
        <div className="forensic-dossier-topbar">
          <div className="forensic-dossier-brand">
            <div className="forensic-dossier-mark">∞</div>
            <div>
              <div className="forensic-dossier-breadcrumb">
                <span>ASTRO CLOCK</span>
                <span>/</span>
                <strong>FORENSIC ASTROLOGY</strong>
              </div>
            </div>
          </div>
          <div className="forensic-dossier-top-actions">
            <span><span className="forensic-dossier-live-dot" />{loading ? 'Syncing' : 'Live dossier'}</span>
            <button type="button" className="forensic-dossier-close" onClick={onClose}>Close</button>
          </div>
        </div>

        <div className="forensic-dossier-context">
          <div className="forensic-dossier-case-main">
            <div className="forensic-dossier-label">Case Snapshot</div>
            <div className="forensic-dossier-title"><span className="forensic-dossier-title-dot" />{caseLocationLabel}</div>
            <div className="forensic-dossier-meta">
              <span>{caseDateLabel}</span>
              <span className="forensic-dossier-divider">·</span>
              <span>{caseTimeLabel}</span>
              <span className="forensic-dossier-divider">·</span>
              <span>{caseLocationLabel}</span>
              {caseTimezone && <><span className="forensic-dossier-divider">·</span><span>{caseTimezone}</span></>}
            </div>
          </div>
          <div className="forensic-dossier-scope">
            <div className="forensic-dossier-label">Chart Scope</div>
            <div className="forensic-dossier-scope-title">{caseScopeLabel}</div>
            <div className="forensic-dossier-meta forensic-dossier-meta-right">
              <span>{String(caseMode).replace(/_/g, ' ')}</span>
              <span className="forensic-dossier-divider">·</span>
              <span>{rawFindings.length} findings</span>
              <span className="forensic-dossier-divider">·</span>
              <span>{replayAxes.length} axes</span>
            </div>
          </div>
        </div>

        <div className="forensic-dossier-controls">
          <div className="forensic-dossier-control-group forensic-dossier-source-group">
            <span className="forensic-dossier-label mb-0 mr-1">Chart Source</span>
            <button
              type="button"
              aria-pressed={chartSource === 'current'}
              className={`forensic-dossier-pill ${chartSource === 'current' ? 'is-active' : ''}`}
              onClick={() => setChartSource('current')}
            >
              Current Chart
            </button>
            <button
              type="button"
              aria-pressed={chartSource === 'snap'}
              className={`forensic-dossier-pill ${chartSource === 'snap' ? 'is-active' : ''}`}
              onClick={switchForensicToSnap}
              disabled={!hasSnapOptions}
            >
              Saved Snap
            </button>
            <select
              aria-label="Forensic saved snap"
              value={selectedSnapId}
              onChange={(event) => {
                setSelectedSnapId(event.target.value);
                setChartSource('snap');
              }}
              disabled={loadingSnaps || !hasSnapOptions}
              className="forensic-dossier-snap-select"
            >
              <option value="">{loadingSnaps ? 'Loading saved snaps...' : 'Select a saved snap'}</option>
              {snapOptions.map((snap) => (
                <option
                  key={snap.id}
                  value={snap.id}
                  disabled={!isSavedSnapCalculationEligible(snap)}
                >
                  {formatForensicSnapLabel(snap)}
                  {getSavedSnapIneligibilityLabel(snap)
                    ? ` — ${getSavedSnapIneligibilityLabel(snap)}`
                    : ''}
                </option>
              ))}
            </select>
            {typeof onRefreshSnaps === 'function' ? (
              <button
                type="button"
                className="forensic-dossier-action"
                onClick={() => onRefreshSnaps({ silent: true })}
                disabled={loadingSnaps}
              >
                {loadingSnaps ? 'Loading' : 'Refresh'}
              </button>
            ) : null}
            {chartSource === 'snap' && selectedSnap ? (
              <span className="forensic-dossier-source-note">
                {selectedSnapParts.label}
                {selectedSnapParts.location ? ` / ${selectedSnapParts.location}` : ''}
              </span>
            ) : null}
            {chartSource === 'snap' && snapSelectionMessage && (!selectedSnap || !selectedSnapContext) ? (
              <span className="forensic-dossier-source-note is-muted">{snapSelectionMessage}</span>
            ) : null}
            {snapOptions.some((snap) => !isSavedSnapCalculationEligible(snap)) ? (
              <span className="forensic-dossier-source-note is-muted font-serif italic">
                Review-required and superseded saved charts are disabled. Use a corrected copy from Astro Clock.
              </span>
            ) : null}
          </div>
          <div className="forensic-dossier-control-group forensic-dossier-case-type-group">
            <span className="forensic-dossier-label mb-0 mr-1">Case Type</span>
            {caseTypeOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={caseType === option.value}
                className={`forensic-dossier-pill ${caseType === option.value ? 'is-active' : ''}`}
                onClick={() => setCaseType(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="forensic-dossier-action-group">
            <button
              type="button"
              aria-pressed={rawControlActive}
              className={`forensic-dossier-action ${rawControlActive ? 'is-active' : ''}`}
              onClick={() => {
                const next = !includeRaw;
                setIncludeRaw(next);
                setForensicTab(next ? 'raw' : (forensicTab === 'raw' ? 'findings' : forensicTab));
              }}
            >
              Raw
            </button>
            <button
              type="button"
              aria-pressed={abductionMode}
              className={`forensic-dossier-action ${abductionMode ? 'is-active' : ''}`}
              onClick={() => {
                const next = !abductionMode;
                setAbductionMode(next);
                setForensicTab(next ? 'abduction' : 'findings');
              }}
            >
              Abduction View
            </button>
            <button
              type="button"
              className={`forensic-dossier-action ${copiedBrief ? 'is-active' : 'is-accent'}`}
              onClick={async () => {
                try {
                  const txt = buildAIBrief(includeRaw);
                  await navigator.clipboard.writeText(txt);
                  setCopiedBrief(true);
                  setTimeout(()=> setCopiedBrief(false), 2000);
                } catch(_){/*noop*/}
              }}
            >
              {copiedBrief ? 'Copied' : 'Symbolic Brief · Copy'}
            </button>
            <button
              type="button"
              className="forensic-dossier-action is-solid"
              onClick={async ()=>{
                try {
                  const html = buildReportHTML();
                  const electronExporter = window.electronAPI?.exportReport;
                  if (typeof electronExporter === 'function') {
                    const res = await electronExporter({ html, pageSize: 'A4' });
                    if (res?.ok) { setAbdMsg(`Report saved: ${res.path}`); return; }
                    setAbdMsg(`Export failed: ${res?.error || 'Unable to create PDF'}`);
                    return;
                  }
                  const printed = await printReportHtmlInBrowser(html);
                  if (printed) {
                    setAbdMsg('Opened browser print dialog - choose "Save as PDF"');
                  } else {
                    setAbdMsg('Unable to open print dialog');
                  }
                } catch (e) { console.warn('Export error', e); }
              }}
            >
              Export PDF
            </button>
          </div>
        </div>
        {abdMsg && (
          <div className="mt-2 text-[11px] text-zinc-600" role="status" aria-live="polite">
            {abdMsg}
          </div>
        )}

        <div className="forensic-dossier-tabs" role="tablist" aria-label="Forensic sections">
          {forensicTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={forensicTab === tab.id}
              className={`forensic-dossier-tab ${forensicTab === tab.id ? 'is-active' : ''}`}
              onClick={() => setForensicTab(tab.id)}
            >
              {tab.label}
              {tab.count != null && <span className="forensic-dossier-count">{tab.count}</span>}
            </button>
          ))}
        </div>

        <div className="forensic-dossier-content">

        {forensicError && card('Forensic Error', (
          <div role="alert" className="text-sm text-rose-700">
            {forensicError}
          </div>
        ))}

        {showForensicSection('findings') && card('Verdict', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="forensic-dossier-verdict">
              <div className="forensic-dossier-verdict-lead">
                <div className="forensic-dossier-label mb-1">Rule Classification</div>
                <div className={`forensic-dossier-score ${survivalToneClass}`}>
                  <span>{survival.level || '-'}</span>
                  <small>symbolic rule band</small>
                </div>
                <div className="forensic-dossier-card-note">
                  <span className="sr-only">{survivabilitySummaryText}</span>
                  {[outcomeBandLabel, survival.level ? `${survival.level} survivability` : null, fatalPressureDominant ? 'fatal pressure dominates' : null, survival.note].filter(Boolean).join(' · ') || 'Awaiting survivability signal.'}
                </div>
              </div>

              <div className="forensic-dossier-verdict-body">
                <div className="forensic-dossier-label mb-2">Relationship Signature</div>
                <h4 className="forensic-dossier-verdict-title">{relationshipInsight?.summary?.relationshipType || relationshipSnapshot.relationshipType}</h4>
                <div className="forensic-dossier-index-grid">
                  <div className="forensic-dossier-index-card">
                    <div className="forensic-dossier-label">Violence Findings</div>
                    <div className="forensic-dossier-stat-value is-rose">{categoryCount('Violence')}</div>
                    <div className="forensic-dossier-stat-line is-rose" />
                  </div>
                  <div className="forensic-dossier-index-card">
                    <div className="forensic-dossier-label">Deception Findings</div>
                    <div className="forensic-dossier-stat-value is-amber">{categoryCount('Deception')}</div>
                    <div className="forensic-dossier-stat-line is-amber" />
                  </div>
                  <div className="forensic-dossier-index-card">
                    <div className="forensic-dossier-label">Symbolic Rule Score</div>
                    <div className={`forensic-dossier-stat-value ${survivalToneClass}`}>{symbolicRuleScore}</div>
                    <div className={`forensic-dossier-stat-line ${survivalToneClass}`} />
                  </div>
                </div>
                {showLightMediationImpact ? (
                  <div className="forensic-dossier-light-impact">
                    <div className="forensic-dossier-light-impact-head">
                      <div>
                        <div className="forensic-dossier-label">Light Mediation Impact</div>
                      </div>
                      <div className={`forensic-dossier-light-impact-score ${lightMediationImpactTone}`}>
                        {formatForensicSignedScore(lightMediationImpact.score_delta)}
                      </div>
                    </div>
                    <div className="forensic-dossier-light-impact-grid">
                      <div>
                        <span>Effect</span>
                        <strong>
                          {`${formatForensicSignedScore(lightMediationImpact.light_mediation_score ?? lightMediationImpact.score_delta)} ${formatLightMediationEffect(lightMediationImpact.effect)}`}
                        </strong>
                      </div>
                      {lightMediationImpact.tilt ? (
                        <div>
                          <span>Tilt</span>
                          <strong>{formatLightMediationTilt(lightMediationImpact.tilt)}</strong>
                        </div>
                      ) : null}
                      <div>
                        <span>Baseline</span>
                        <strong>
                          {[
                            `Without light mediation: ${formatForensicSignedScore(lightMediationImpact.score_without_light_mediation)}`,
                            lightMediationImpact.level_without_light_mediation,
                            lightMediationImpact.outcome_band_without_light_mediation
                              ? formatSurvivabilityBandLabel(lightMediationImpact.outcome_band_without_light_mediation)
                              : null,
                          ].filter(Boolean).join(' · ')}
                        </strong>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          )
        ))}

        {showForensicSection('findings') && card('Directional Findings', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="forensic-dossier-panel">
                  <div className="font-medium mb-1">Case Axes</div>
                  <div className="forensic-dossier-card-subtitle">Primary case-axis signals found in the scan.</div>
                  <div className="forensic-dossier-chip-row">
                    {replayAxes.length ? replayAxes.map((axis) => (
                      <span key={axis} className="forensic-dossier-chip is-teal">
                        <span className="forensic-dossier-chip-dot" />
                        {formatForensicDisplayLabel(axis)}
                      </span>
                    )) : <span className="text-xs text-zinc-500">-</span>}
                  </div>
                </div>
                <div className="forensic-dossier-panel">
                  <div className="font-medium mb-1">Finding Groups</div>
                  <div className="forensic-dossier-card-subtitle">How the scan grouped the active findings.</div>
                  <div className="forensic-dossier-chip-row">
                    {categoryEntries.length ? categoryEntries.map(([name, count]) => (
                      <span key={name} className="forensic-dossier-chip">
                        <span className="forensic-dossier-chip-dot" />
                        {`${name}: ${count}`}
                      </span>
                    )) : <span className="text-xs text-zinc-500">-</span>}
                  </div>
                </div>
                <div className="forensic-dossier-panel md:col-span-2">
                  <div className="font-medium mb-1">Finding Notes</div>
                  <div className="forensic-dossier-card-subtitle">Key findings with supporting chart details.</div>
                  {topFindings.length ? (
                    <ul className="forensic-dossier-finding-list">
                    {topFindings.map((finding, idx) => {
                      const title = cleanForensicDisplayText(finding?.title || '-');
                      const rationale = cleanForensicDisplayText(finding?.rationale || '');
                      const isOpen = expandedFindingIndex === idx;
                      const category = cleanForensicDisplayText(finding?.category || 'Uncategorized');
                      const weight = Number(finding?.weight);
                      const weightLabel = Number.isFinite(weight) ? String(weight) : null;
                      const toneClass = getFindingToneClass(finding);
                      const evidenceRows = buildFindingEvidenceRows(finding);
                      const panelId = `forensic-finding-${idx}`;
                      return (
                        <li key={`${title}-${idx}`} className={`forensic-dossier-finding-row ${isOpen ? 'is-open' : ''}`}>
                          <button
                            type="button"
                            aria-expanded={isOpen ? 'true' : 'false'}
                            aria-controls={panelId}
                            onClick={() => setExpandedFindingIndex(isOpen ? null : idx)}
                            className="forensic-dossier-finding-head"
                          >
                            <span className="forensic-dossier-finding-head-main">
                              <span className="forensic-dossier-note-number">{String(idx + 1).padStart(2, '0')}</span>
                              <span className="forensic-dossier-finding-title">{title}</span>
                            </span>
                            <span className="forensic-dossier-finding-right">
                              <span className={`forensic-dossier-finding-tag ${toneClass}`}>{category}</span>
                              {weightLabel ? <span className="forensic-dossier-finding-weight">Weight {weightLabel}</span> : null}
                              <span className="forensic-dossier-finding-chev" aria-hidden="true">&gt;</span>
                            </span>
                          </button>
                          {isOpen && (
                            <div id={panelId} className="forensic-dossier-finding-body">
                              <p className="forensic-dossier-finding-copy">{rationale || 'No rationale supplied.'}</p>
                              {evidenceRows.length ? (
                                <div className="forensic-dossier-finding-data">
                                  {evidenceRows.map((row) => (
                                    <div key={row.key} className="forensic-dossier-finding-data-row">
                                      <span className="forensic-dossier-finding-key">{row.key}</span>
                                      <span className="forensic-dossier-finding-value">{row.value}</span>
                                      <span className={`forensic-dossier-finding-tag ${toneClass}`}>Evidence</span>
                                    </div>
                                  ))}
                                </div>
                              ) : null}
                            </div>
                          )}
                        </li>
                      );
                    })}
                    </ul>
                  ) : <div className="text-xs text-zinc-500">-</div>}
                </div>
              </div>
            </div>
          )
        ))}

        {showForensicSection('victim') && card('Victim Analysis', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              <div className="forensic-dossier-section-strip">
                <span>Asc Sign: {ascSign || '-'}</span>
                <span>Primary Ruler: {primaryRuler || '-'}</span>
                <span>Co-Rulers: {coRulers.join(', ')}</span>
                <span>Case Type: {activeCaseTypeLabel}</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="border rounded p-2">
                  <div className="font-medium mb-1">Victim Identification</div>
                  <div className="text-xs text-zinc-600">Selected significators for this case type.</div>
                  <div className="mt-1 text-xs">Angular rulers: {[primaryRuler, ...coRulers].filter(Boolean).filter((p)=>Boolean(features?.planets?.[p]?.angular)).join(', ') || '-'}</div>
                  <div className="mt-1 text-xs">Primary ruler dominance: {(() => { const d = domInfo(primaryRuler); return d ? `${d.score} (${d.level})` : '-'; })()}</div>
                  {(() => {
                    try {
                      const vHouseGroup = (h) => { const n=Number(h); if ([1,4,7,10].includes(n)) return 'Angular'; if ([2,5,8,11].includes(n)) return 'Succedent'; return 'Cadent'; };
                      const mi = features?.planets?.['Moon'] || {};
                      const mLon = mi?.longitude; const mSign = mi?.sign || '-';
                      const mDeg = isFinite(mLon) ? degreeTextFromLon(mLon) : '-';
                      const mHouse = mi?.house;
                      const mt = data?.moon_timeline;
                      const voc = (mt && typeof mt.in_voc === 'boolean')
                        ? mt.in_voc
                        : Boolean((data?.moon || features?.moon || {}).void_of_course);
                      const via = Boolean(mi?.via_combusta);
                      const a = features?.aspects || {};
                      const mAspects = Object.entries(a).filter(([k,v])=> v && (k.startsWith('Moon_to_') || k.endsWith('_to_Moon')))
                        .map(([k,v])=> { const [p1,p2]=k.split('_to_'); const other = (p1==='Moon'? p2 : p1); return { other, type: String(v.type||''), applying: v.applying===true }; });
                      const malHard = mAspects.filter(x=> (x.other==='Mars'||x.other==='Saturn') && (x.type==='square'||x.type==='opposition'))
                        .map(x=> `${x.type} ${x.other}${x.applying? ' (app)':''}`);
                      const toPrimary = mAspects.find(x=> x.other===primaryRuler);
                      return (
                        <div className="mt-2 pt-2 border-t border-zinc-200">
                          <div className="font-medium mb-1">Moon (universal co‑ruler)</div>
                          <div className="text-xs">Position: {mSign} {mDeg} (H{mHouse ?? '-'} · {vHouseGroup(mHouse)})</div>
                          <div className="text-xs">Dignity score: {dign('Moon')}</div>
                          <div className="text-xs">Conditions: VoC {voc? 'Yes':'No'} · Via combusta {via? 'Yes':'No'}</div>
                          <div className="text-xs">Danger (malefics): {malHard.length? malHard.join(' · ') : '-'}</div>
                          <div className="text-xs">Aspect to primary ruler: {toPrimary? `${toPrimary.type}${toPrimary.applying? ' (app)':''}` : '-'}</div>
                        </div>
                      );
                    } catch { return null; }
                  })()}
                </div>
                <div className="border rounded p-2">
                  <div className="font-medium mb-1">Victim Location Matrix</div>
                  <ul className="text-xs list-disc ml-4 space-y-1">
                    <li>1st House: immediate surroundings (ASC sign {ascSign || '-'}).</li>
                    {ascRulerPlacement?.ruler || ascRulerPlacement?.house ? (
                      <li>
                        ASC-ruler placement:{' '}
                        <span className="font-semibold">
                          {[ascRulerPlacement.ruler, ascRulerPlacement.house ? `in H${ascRulerPlacement.house}` : null].filter(Boolean).join(' ')}
                        </span>
                        {ascRulerPlacement.label ? <span> · {ascRulerPlacement.label}</span> : null}
                        {ascRulerPlacement.summary ? <span> · {ascRulerPlacement.summary}</span> : null}
                      </li>
                    ) : null}
                    {ascRulerPlacementCues.length ? (
                      <li>McIntosh cues: {ascRulerPlacementCues.join(' · ')}</li>
                    ) : null}
                    <li>Angular placements: immediacy, visibility, and direct contact.</li>
                    <li>Victim significators: {Array.isArray(survival.victimSignificators) && survival.victimSignificators.length ? survival.victimSignificators.join(' · ') : [primaryRuler, ...coRulers].filter(Boolean).join(' · ') || '-'}</li>
                      <li>
                        Survivability signal:{' '}
                        <span className={survival.level==='Higher'?'text-emerald-700':(survival.level==='Lower'?'text-rose-700':'text-amber-700')}>
                          {survival.level}
                        </span>
                        {typeof survival.score === 'number' ? <span className="text-zinc-500"> ({survival.score >= 0 ? '+' : ''}{survival.score})</span> : null}
                        {survival.outcomeBand ? <span className="text-zinc-500"> · {formatSurvivabilityBandLabel(survival.outcomeBand)}</span> : null}
                        {survival.fatalOverride ? <span className="text-zinc-500"> (fatal pressure dominates)</span> : null}
                      </li>
                      {survival.breakdown ? (
                        <li>
                          {(() => {
                            const accidental = Number(survival.breakdown.accidental || 0);
                            const recoverySupport = Number(survival.breakdown.recovery_support || 0);
                            return (
                              <>
                          Score basis: vitality {survival.breakdown.vitality >= 0 ? '+' : ''}{survival.breakdown.vitality} ·
                          accidental {accidental >= 0 ? '+' : ''}{accidental} ·
                          support {survival.breakdown.support >= 0 ? '+' : ''}{survival.breakdown.support} ·
                          recovery support {recoverySupport >= 0 ? '+' : ''}{recoverySupport} ·
                          Moon {survival.breakdown.moon >= 0 ? '+' : ''}{survival.breakdown.moon} ·
                          danger {survival.breakdown.danger} ·
                          fatal pressure {survival.breakdown.fatal_pressure}
                              </>
                            );
                          })()}
                        </li>
                      ) : null}
                    <li>Aspects to malefics: {(() => {
                      const vics = [primaryRuler, ...coRulers].filter(Boolean);
                      const parts = [];
                      vics.forEach(v => {
                        const det = maleficThreatDetails(v);
                        if (det.length) parts.push(`${v}: ${det.join(', ')}`);
                      });
                      return parts.join(' · ') || '-';
                    })()}</li>
                    {survival.note ? <li>Read: {survival.note}</li> : null}
                  </ul>
                </div>
              </div>
            </div>
          )
        ))}
        {showForensicSection('abduction') && card('Abduction Cues', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              {/* Origin input and fetch controls */}
              <div className="text-[11px] text-zinc-600">
                Use the last known point, seizure point, or reporting origin as the map anchor.
              </div>
              <div className="forensic-dossier-field-grid">
                <label className="forensic-dossier-field">
                  <span>Origin Latitude</span>
                  <input value={originLat} onChange={e=>setOriginLat(e.target.value)} className="forensic-dossier-input" placeholder="e.g., 40.7608" inputMode="decimal" />
                </label>
                <label className="forensic-dossier-field">
                  <span>Origin Longitude</span>
                  <input value={originLon} onChange={e=>setOriginLon(e.target.value)} className="forensic-dossier-input" placeholder="e.g., -111.8910" inputMode="decimal" />
                </label>
                <button type="button" disabled={fetchingAbd} className={`forensic-dossier-action ${fetchingAbd ? 'is-active' : ''}`} onClick={async()=>{
                  const latStr = normalizeCoordinateInput(originLat); const lonStr = normalizeCoordinateInput(originLon);
                  const lat = parseFloat(latStr); const lon = parseFloat(lonStr);
                  if (!isFinite(lat)||!isFinite(lon)) { setAbdMsg('Invalid coordinates. Example: 40.7608, -111.8910'); return; }
                  setAbductionMode(true);
                  setFetchingAbd(true);
                  setAbdMsg('Fetching abduction map…');
                  try { await fetchForensic({ abduction: true, origin: `${lat},${lon}`, line_zones: true }); }
                  catch(_){}
                  finally { setFetchingAbd(false); }
                }}>{fetchingAbd? 'Fetching…':'Load Abduction Map'}</button>
              </div>
              {(() => {
                try {
                  const summary = buildAbductionCueSummary({ data, features });
                  return (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="border rounded p-2">
                          <div className="font-medium mb-1">Scene Signals</div>
                          <div className="text-xs">Victim signal: <span className="font-semibold">{summary.victimAnchor}</span></div>
                          <div className="text-xs">Movement signal: {summary.movementAnchor}</div>
                          {summary.primaryHouseCues.length > 0 && (
                            <div className="text-xs mt-1">Primary place cues: {summary.primaryHouseCues.join(' · ')}</div>
                          )}
                          {summary.primarySignCues.length > 0 && (
                            <div className="text-xs">Scene modifiers: {summary.primarySignCues.join(' · ')}</div>
                          )}
                          {summary.movementCues.length > 0 && (
                            <div className="text-xs">Route and movement cues: {summary.movementCues.join(' · ')}</div>
                          )}
                        </div>
                        <div className="border rounded p-2">
                          <div className="font-medium mb-1">Access and Distance</div>
                          <div className="text-xs">Tier: <span className="font-semibold">{summary.accessProfile.title}</span></div>
                          {summary.accessNotes.length > 0 && (
                            <div className="text-xs mt-1">Access notes: {summary.accessNotes.join(' · ')}</div>
                          )}
                          {summary.distanceCues.length > 0 && (
                            <div className="text-xs">Distance read: {summary.distanceCues.join(' · ')}</div>
                          )}
                          {summary.modifiers.length > 0 && (
                            <div className="text-xs">Context modifiers: {summary.modifiers.join(' · ')}</div>
                          )}
                        </div>
                    </div>
                  );
                } catch(_) { return <div className="text-xs text-zinc-500">Unavailable</div>; }
              })()}
            </div>
          )
        ))}

        {showForensicSection('abduction') && card('Abduction Map', (
          (() => {
            const abd = data?.abduction_map || {};
            const origin = abd.origin || {};
            let lat = Number(origin.lat); let lon = Number(origin.lon);
            if (!isFinite(lat) || !isFinite(lon)) {
              const li = parseFloat(originLat); const lo = parseFloat(originLon);
              if (isFinite(li) && isFinite(lo)) { lat = li; lon = lo; }
            }
            // Raw bearings from backend
            const bearings = Array.isArray(abd.bearings)? abd.bearings : [];
            // Replace 'Planet in 7th' with '1st ruler' in both sources list and map
            const firstRulerName = (()=>{
              try {
                const rulers = features?.house_rulers || {};
                return features?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
              } catch { return null; }
            })();
            const processedBearings = buildProcessedAbductionBearings(bearings, firstRulerName);
            const hasOrigin = isFinite(lat) && isFinite(lon);
            if (!hasOrigin) return <div className="text-sm text-zinc-500">Enter an origin point above, then load the map.</div>;
            const MapClick = ({ onPick }) => { useMapEvents({ click(e){ try { onPick && onPick(e.latlng); } catch(_){} } }); return null; };
            const MapHover = () => { useMapEvents({ mousemove(e){ try { setMapHover({ lat: e.latlng.lat, lon: e.latlng.lng }); } catch(_){} } }); return null; };
            const dest = (lat0, lon0, brgDeg, distKm) => {
              const R = 6371.0; const d = distKm / R; const br = (brgDeg*Math.PI/180);
              const la1 = lat0*Math.PI/180; const lo1 = lon0*Math.PI/180;
              const la2 = Math.asin(Math.sin(la1)*Math.cos(d) + Math.cos(la1)*Math.sin(d)*Math.cos(br));
              const lo2 = lo1 + Math.atan2(Math.sin(br)*Math.sin(d)*Math.cos(la1), Math.cos(d)-Math.sin(la1)*Math.sin(la2));
              return [la2*180/Math.PI, ((lo2*180/Math.PI)+540)%360-180];
            };
            const bearingLine = (az, km) => [ [lat, lon], dest(lat, lon, az, km) ];
            const toRad = (v)=> v*Math.PI/180;
            const toDeg = (v)=> v*180/Math.PI;
            const normalize360 = (x)=> (x%360+360)%360;
            const distKm = (la1,lo1,la2,lo2)=>{
              const R=6371.0; const dLat=toRad(la2-la1); const dLon=toRad(lo2-lo1);
              const a = Math.sin(dLat/2)**2 + Math.cos(toRad(la1))*Math.cos(toRad(la2))*Math.sin(dLon/2)**2;
              return R*2*Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            };
            const bearingDeg = (la1,lo1,la2,lo2)=>{
              const dLon=toRad(lo2-lo1); const lat1=toRad(la1); const lat2=toRad(la2);
              const y=Math.sin(dLon)*Math.cos(lat2);
              const x=Math.cos(lat1)*Math.sin(lat2)-Math.sin(lat1)*Math.cos(lat2)*Math.cos(dLon);
              return normalize360(toDeg(Math.atan2(y,x)));
            };
            const toCardinal16 = (b)=>{
              const dirs=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
              const idx=Math.round(normalize360(b)/22.5)%16; return dirs[idx];
            };
            return (
              <div className="space-y-2">
                <div className="h-96 w-full border rounded overflow-hidden relative">
                  <MapContainer center={[lat, lon]} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={true}>
                    <MapClick onPick={(ll)=>{ try { setOriginLat(String(ll.lat.toFixed(5))); setOriginLon(String(ll.lng.toFixed(5))); } catch(_){} }} />
                    <MapHover />
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap contributors"/>
                    <Marker position={[lat, lon]}><Popup>Origin<br/>{lat.toFixed(5)}, {lon.toFixed(5)}</Popup></Marker>
                    <Circle center={[lat, lon]} radius={3000} pathOptions={{ color:'#22c55e', fillOpacity:0.05 }} />
                    <Circle center={[lat, lon]} radius={12000} pathOptions={{ color:'#eab308', fillOpacity:0.03 }} />
                    <Circle center={[lat, lon]} radius={40000} pathOptions={{ color:'#ef4444', fillOpacity:0.02 }} />
                    {(() => {
                      const drawAzimuth = (bearing) => {
                        try {
                          const az = Number(bearing?.azimuth_deg);
                          if (!isFinite(az)) return null;
                          const alt = Number(bearing?.altitude_deg);
                          if (flipSubHorizon && isFinite(alt) && alt < 0) return (az + 180) % 360;
                          return az;
                        } catch { return null; }
                      };
                      return processedBearings.slice(0,6).map((b,i)=> {
                        const azToDraw = drawAzimuth(b);
                        if (azToDraw == null) return null;
                        const style = getAbductionRoleStyle(b?.role);
                        return (
                          <Polyline
                            key={`b${i}`}
                            positions={bearingLine(azToDraw, 40)}
                            pathOptions={{
                              color: style.color,
                              dashArray: style.dashArray || undefined,
                              weight: style.weight,
                              opacity: style.opacity,
                              lineCap: 'round',
                              lineJoin: 'round',
                            }}
                          />
                        );
                      });
                    })()}
                  </MapContainer>
                  <div className="absolute top-2 right-2 z-[1001] pointer-events-none bg-white/90 backdrop-blur rounded border px-2 py-1 text-[11px] space-y-0.5 shadow">
                    {(() => { try {
                      const ml = mapHover; const has = ml && isFinite(ml.lat) && isFinite(ml.lon);
                      const d = has ? (function(){ const R=6371.0; const dLat=(ml.lat-lat)*Math.PI/180; const dLon=(ml.lon-lon)*Math.PI/180; const a = Math.sin(dLat/2)**2 + Math.cos(lat*Math.PI/180)*Math.cos(ml.lat*Math.PI/180)*Math.sin(dLon/2)**2; return R*2*Math.atan2(Math.sqrt(a), Math.sqrt(1-a)); })() : null;
                      const brg = has ? (function(){ const dLon=(ml.lon-lon)*Math.PI/180; const lat1=lat*Math.PI/180; const lat2=ml.lat*Math.PI/180; const y=Math.sin(dLon)*Math.cos(lat2); const x=Math.cos(lat1)*Math.sin(lat2)-Math.sin(lat1)*Math.cos(lat2)*Math.cos(dLon); const deg=(Math.atan2(y,x)*180/Math.PI); const n=((deg%360)+360)%360; return n; })() : null;
                      const dirs=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
                      const card = (brg!=null)? dirs[Math.round(((brg%360)+360)%360/22.5)%16] : null;
                      return (
                        <>
                          <div>Cursor: {has? `${ml.lat.toFixed(5)}, ${ml.lon.toFixed(5)}` : '-'}</div>
                          <div>From origin: {has? `${d.toFixed(1)} km` : '-'}{has? ` · ${Math.round(brg)}° ${card}`: ''}</div>
                        </>
                      );
                    } catch(_) { return <div>-</div>; } })()}
                    {/* Legend */}
                    <div className="mt-1 pt-1 border-t border-zinc-200">
                      <div className="text-[10px] text-zinc-600">Legend</div>
                      {(() => {
                        const lineStyle = (s) => {
                          const base = { display: 'inline-block', width: '22px', height: '0px', marginRight: '6px' };
                          if (!s?.dashArray) return { ...base, borderTop: `2px solid ${s.color}` };
                          if (s.dashArray === '1 4') return { ...base, borderTop: `2px dotted ${s.color}` };
                          return { ...base, borderTop: `2px dashed ${s.color}` };
                        };
                        return (
                          <div className="space-y-0.5">
                            {getAbductionLegendEntries().map((e) => (
                              <div key={e.role} className="flex items-center">
                                <span style={lineStyle(e.style)} />
                                <span>{e.legendLabel}</span>
                              </div>
                            ))}
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                </div>
                {/* Bearing sources list */}
                <div className="text-xs">
                  <div className="font-medium mb-1">Bearing Sources</div>
                  <div className="mb-1 flex items-center gap-2">
                    <label className="flex items-center gap-1">
                      <input type="checkbox" checked={!!showBackAz} onChange={(e)=> setShowBackAz(e.target.checked)} />
                      <span className="text-[11px]">Show back-azimuth (+180°)</span>
                    </label>
                    <label className="flex items-center gap-1">
                      <input type="checkbox" checked={!!flipSubHorizon} onChange={(e)=> setFlipSubHorizon(e.target.checked)} />
                      <span className="text-[11px]">Pro convention (flip sub-horizon)</span>
                    </label>
                  </div>
                  {(() => { try {
                    const pls = features?.planets || {};
                    const norm360 = (x)=> (x%360+360)%360;
                    const pad2 = (n)=> String(n).padStart(2,'0');
                    const pad3 = (n)=> String(n).padStart(3,'0');
                    const dmsCard4 = (az)=> {
                      if (az==null || !isFinite(az)) return '-';
                      let a = norm360(Number(az));
                      let d = Math.floor(a);
                      let mFloat = (a - d) * 60;
                      let m = Math.floor(mFloat);
                      let s = Math.round((mFloat - m) * 60);
                      if (s === 60) { s = 0; m += 1; }
                      if (m === 60) { m = 0; d += 1; }
                      if (d === 360) d = 0;
                      const card = (ang)=> {
                        const x = norm360(ang);
                        if (x>=45 && x<135) return 'E';
                        if (x>=135 && x<225) return 'S';
                        if (x>=225 && x<315) return 'W';
                        return 'N';
                      };
                      return `${pad3(d)} ${pad2(m)} ${pad2(s)} ${card(a)}`;
                    };
                    // Quadrantal N/S offset format (common in other software): angle measured from nearest N/S axis
                    const dmsNS = (az)=>{
                      if (az==null || !isFinite(az)) return '-';
                      const a = norm360(Number(az));
                      let off, letter;
                      if (a>=90 && a<270) { // South hemisphere
                        letter = 'S';
                        off = Math.abs(a - 180);
                      } else { // North hemisphere
                        letter = 'N';
                        // offset from North (0 or 360)
                        off = (a<=180)? a : (360 - a);
                      }
                      let d = Math.floor(off);
                      let mFloat = (off - d) * 60;
                      let m = Math.floor(mFloat);
                      let s = Math.round((mFloat - m) * 60);
                      if (s === 60) { s = 0; m += 1; }
                      if (m === 60) { m = 0; d += 1; }
                      if (d === 360) d = 0;
                      return `${pad2(d)} ${pad2(m)} ${pad2(s)} ${letter}`;
                    };
                    const items = processedBearings.slice(0,6).map((b,i)=> {
                      const inf = pls?.[b.planet] || {};
                      const sign = inf?.sign || '-';
                      const house = (inf?.house!=null)? `H${inf.house}` : 'H-';
                      const azNum = (b?.azimuth_deg!=null)? Number(b.azimuth_deg) : null;
                      const az = (azNum!=null)? `${azNum.toFixed(1)}°` : '-';
                      const alt = (b?.altitude_deg!=null)? `${Number(b.altitude_deg).toFixed(1)}°` : '-';
                      const weight = (b?.weight!=null)? Number(b.weight).toFixed(2) : '-';
                      const dms = dmsCard4(azNum);
                      const qns = dmsNS(azNum);
                      let extra = null;
                      if (showBackAz) {
                        const back = (azNum!=null)? ( (azNum + 180) % 360 ) : null;
                        const backDms = dmsCard4(back);
                        const backQns = dmsNS(back);
                        const backDec = (back!=null)? `${back.toFixed(1)}°` : '-';
                        extra = <> · back 180° {backDec} · {backDms} · NS {backQns}</>;
                      }
                      return <li key={i}>{formatAbductionBearingRoleLabel(b)}: {b.planet} - {az} (alt {alt}) · {house} {sign} · weight {weight} · {dms} · NS {qns}{extra}</li>;
                    });
                    return (
                      <ul className="list-disc ml-4 space-y-0.5">{items.length? items : <li>-</li>}</ul>
                    );
                  } catch(_) { return <div>-</div>; } })()}
                </div>
              </div>
            );
          })()
        ))}

        {showForensicSection('perpetrator') && card('Counterpart Signals', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              {(() => {
                const rulers = features?.house_rulers || {};
                const seventhRuler = features?.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
                const firstRuler = features?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
                const seventhHousePlanets = Object.entries(features?.planets||{})
                  .filter(([,p]) => (p?.house===7))
                  .map(([name]) => name);
                const rulerInfo = features?.planets?.[seventhRuler] || {};
                const asp = features?.aspects || {};
                const rAspects = [];
                Object.entries(asp).forEach(([k,v])=>{
                  if (!v) return;
                  if (k.startsWith(`${seventhRuler}_to_`) || k.endsWith(`_to_${seventhRuler}`)) {
                    rAspects.push({ key:k, ...v });
                  }
                });
                const degFlags = [];
                if (rulerInfo.anaretic) degFlags.push('Anaretic');
                if (rulerInfo.ingress) degFlags.push('Ingress');
                if (rulerInfo.middegree) degFlags.push('Mid-degree');
                if (rulerInfo.via_combusta) degFlags.push('Via combusta');
                // Integer degree helper for fallback display
                const degInt = (() => {
                  try {
                    if (typeof rulerInfo?.degree_in_sign === 'number') return Math.round(rulerInfo.degree_in_sign);
                    if (isFinite(rulerInfo?.longitude)) return Math.round(((Number(rulerInfo.longitude)%30)+30)%30);
                  } catch(_) {}
                  return null;
                })();
                // Degree specials from knowledge dictionary
                const degSpecialHits = (() => {
                  try {
                    const dict = data?.degree_special || {};
                    const s = rulerInfo?.sign; if (!s) return [];
                    let degIn = null;
                    if (typeof rulerInfo?.degree_in_sign === 'number') degIn = rulerInfo.degree_in_sign;
                    else if (isFinite(rulerInfo?.longitude)) degIn = ((Number(rulerInfo.longitude)%30)+30)%30;
                    if (degIn == null) return [];
                    const rounded = Math.round(Number(degIn));
                    const out = [];
                    const specials = dict?.special || {};
                    Object.entries(specials).forEach(([key, val])=>{
                      try {
                        const parts = String(key).split('_');
                        const signName = parts[0];
                        const degNum = Number(parts[1]);
                        if (signName === s && degNum === rounded) {
                          out.push(val?.label || key);
                        }
                      } catch(_){}
                    });
                    const sd = (dict?.sign_degrees || {})[s];
                    if (Array.isArray(sd)) {
                      sd.forEach(entry => {
                        try {
                          const arr = Array.isArray(entry?.degree) ? entry.degree : [];
                          if (arr.includes(rounded)) {
                            const kws = Array.isArray(entry?.keywords) ? entry.keywords : [];
                            if (kws.length) out.push(kws.slice(0,3).join('/'));
                          }
                        } catch(_){}
                      });
                    }
                    return out;
                  } catch(_) { return []; }
                })();
                const collectBy = (planet) => rAspects
                  .filter(a => (a.key.includes(`_to_${planet}`) || a.key.startsWith(`${planet}_to_`)))
                  .map(a => ({ type: a?.type, applying: a?.applying }));
                const aspectBucket = (planet) => formatForensicAspectLabels(collectBy(planet));
                const bpf = { Mars: collectBy('Mars'), Saturn: collectBy('Saturn'), Neptune: collectBy('Neptune'), Pluto: collectBy('Pluto') };
                const fsRaw = Array.isArray(features?.fixed_stars_list)
                  ? features.fixed_stars_list
                  : (Array.isArray(features?.fixed_stars) ? features.fixed_stars : (features?.fixed_stars ? Object.values(features.fixed_stars) : []));
                const fsSunMoon = fsRaw.filter(h=> h?.target_type==='planet' && (h?.target==='Sun' || h?.target==='Moon'));
                const fsCusps = fsRaw.filter(h=> h?.target_type==='cusp');
                const fsDict = data?.fixed_star_meanings || {};
                const fsDescribe = (hit) => {
                  try {
                    const nm = hit?.name; const tgt = hit?.target; if (!nm) return null;
                    const entry = fsDict?.[nm] || fsDict?.[String(nm).trim()] || null;
                    const kw = entry?.forensic || entry?.meaning || '';
                    return `${nm}↔${tgt}${kw? ` - ${kw}`:''}`;
                  } catch(_) { return `${hit?.name||''}↔${hit?.target||''}`; }
                };
                const cusp7 = Number((features?.house_cusps||[])[6]);
                const cusp7Sign = isFinite(cusp7) ? signFromLon(cusp7) : '-';
                const cusp7Deg = isFinite(cusp7) ? degreeTextFromLon(cusp7) : '-';

                // Helpers
                const houseGroup = (h) => {
                  const n = Number(h);
                  if ([1,4,7,10].includes(n)) return 'Angular';
                  if ([2,5,8,11].includes(n)) return 'Succedent';
                  return 'Cadent';
                };
                // Derived houses from 7th perspective - helper used by alternates and summary
                const planetsByHouse = (h)=> Object.entries(features?.planets||{}).filter(([,p])=> p?.house===h).map(([n])=> n);
                const solar = data?.features?.solar || features?.solar || {};
                const inSolar = (k, p) => Array.isArray(solar?.[k]) && solar[k].includes(p);
                const dignFlags = (() => {
                  const raw = String(rulerInfo?.essential_dignity_raw||'').toLowerCase();
                  const tags = new Set((Array.isArray(rulerInfo?.dignities)? rulerInfo.dignities: []).map(t=> String(t).toLowerCase()));
                  const out = [];
                  if (raw.includes('domicile') || raw.includes('ruler') || tags.has('domicile') || tags.has('rulership')) out.push('Rulership');
                  if (raw.includes('exalt') || Array.from(tags).some(t=> t.includes('exalt'))) out.push('Exaltation');
                  if (Array.from(tags).some(t=> t.includes('triplicity'))) out.push('Triplicity');
                  if (Array.from(tags).some(t=> t.includes('term')||t.includes('bound'))) out.push('Term');
                  if (Array.from(tags).some(t=> t.includes('face')||t.includes('decan'))) out.push('Face');
                  if (raw.includes('detriment') || tags.has('detriment')) out.push('Detriment');
                  if (raw.includes('fall') || tags.has('fall')) out.push('Fall');
                  if (out.length===0) out.push('Neutral');
                  return out;
                })();
                const aspectTo = (target) => {
                  if (!target) return [];
                  return collectRelationshipAspectContacts({
                    aspects: asp,
                    source: seventhRuler,
                    target,
                    applyingLabel: ' (app)',
                  });
                };
                const dispositorState = normalizeDispositorState(data?.dispositors?.[seventhRuler], seventhRuler);
                const dispChain = dispositorState.chain;
                const mutualReception = Boolean(dispositorState.mutualReception);
                const lm = data?.light_mediation || {};
                const translOrCollect = (() => {
                  try {
                    if (lm?.translation) return `Translation${lm?.translator? ` via ${lm.translator}`:''}`;
                    if (lm?.collection) return `Collection${lm?.collector? ` by ${lm.collector}`:''}`;
                    return '-';
                  } catch(_) { return '-'; }
                })();

                // Alternates based on context cues - compute with simple reasons
                const alt12Why = [];
                if (rulerInfo?.house === 12) alt12Why.push('ruler in H12');
                if (features?.houses?.emphasis12_strong) alt12Why.push('12th emphasis');
                const alt12 = alt12Why.length > 0;

                const alt5Why = [];
                if (rulerInfo?.house === 5) alt5Why.push('ruler in H5');
                const h5p = planetsByHouse(5);
                if (h5p.length >= 2) alt5Why.push('H5 emphasis');
                if (collectBy('Venus').length > 0 || (features?.planets?.Venus?.house === 5)) alt5Why.push('Venus link');
                const alt5 = alt5Why.length > 0;

                const alt10Why = [];
                if (rulerInfo?.house === 10) alt10Why.push('ruler in H10');
                const h10p = planetsByHouse(10);
                if (h10p.length >= 2) alt10Why.push('H10 emphasis');
                const satDom = domInfo('Saturn');
                if ((features?.planets?.Saturn?.angular === true) || (satDom && (satDom.level === 'Highly Dominant' || satDom.level === 'Extremely Dominant'))) alt10Why.push('Saturn/authority');
                const alt10 = alt10Why.length > 0;

                const derived = {
                  money: { house: 8, planets: planetsByHouse(8) },
                  home: { house: 10, planets: planetsByHouse(10) },
                  comms: { house: 9, planets: planetsByHouse(9) },
                  friends: { house: 5, planets: planetsByHouse(5) },
                };
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">7th-house Counterpart Signals</div>
                      <div className="text-xs">7th-house cusp: {cusp7Sign} {cusp7Deg} | ruler <span className="font-semibold">{seventhRuler || '-'}</span></div>
                      <div className="text-xs">7th-house co-signifiers: {seventhHousePlanets.length? seventhHousePlanets.join(', '): '-'}</div>
                      <div className="text-xs">Ruler placement: {(() => { const lon = rulerInfo?.longitude; const s = rulerInfo?.sign || '-'; const deg = isFinite(lon)? degreeTextFromLon(lon) : '-'; const h = rulerInfo?.house ?? '-'; return `${s} ${deg} (H${h} | ${houseGroup(h)})`; })()}</div>
                      <div className="text-xs">Dignity: {dignFlags.join(', ') || '-'}</div>
                      <div className="text-xs">State: {rulerInfo?.retrograde? 'Retrograde' : 'Direct'}{inSolar('cazimi', seventhRuler)? ' | Cazimi':''}{inSolar('combustion', seventhRuler)? ' | Combust':''}{inSolar('under_beams', seventhRuler)? ' | Under beams':''}</div>
                      <div className="text-xs">Malefic/benefic contacts: Saturn: {aspectBucket('Saturn')} | Mars: {aspectBucket('Mars')} | Jupiter: {aspectBucket('Jupiter')} | Venus: {aspectBucket('Venus')}</div>
                      {(() => {
                        // Applying aspects & timing (from horary perfections)
                        try {
                          const fmtDur = (days) => {
                            if (days == null || !isFinite(days)) return null;
                            const d = Math.floor(days);
                            const h = Math.round((days - d) * 24);
                            if (d > 0) return `${d}d${h? ` ${h}h`: ''}`;
                            return `${h}h`;
                          };
                          const ap = rAspects
                            .filter(a => a?.applying === true)
                            .map(a => ({...a, t: (a?.time_to_perfection != null ? Number(a.time_to_perfection) : Infinity)}))
                            .sort((a,b)=> a.t - b.t)
                            .slice(0,4)
                            .map(a => {
                              const [p1,p2] = a.key.split('_to_');
                              const other = (p1===seventhRuler ? p2 : p1);
                              const t = fmtDur(a.t);
                              const within = (a?.perfection_within_sign === true ? '[check]' : (a?.perfection_within_sign === false ? '✗' : ''));
                              const segs = [`${a.type||''} ${other}`];
                              if (t) segs.push(`in ${t}`);
                              if (within) segs.push(`(within sign ${within})`);
                              return segs.join(' ');
                            });
                          return (
                            <div className="text-xs">Applying contacts: {ap.length? ap.join(' | '): '-'}</div>
                          );
                        } catch(_) { return null; }
                      })()}
                      <div className="text-xs">Degree markers: {(() => { const parts = [...degFlags]; if (degSpecialHits.length) parts.push(...degSpecialHits); if (parts.length) return parts.join(' | '); const s=rulerInfo?.sign||'-'; return degInt!=null? `${s} ${degInt}°` : '-'; })()}</div>
                      {(() => {
                        const segs = [];
                        if (alt12) segs.push(`12th - hidden enemy${alt12Why.length? ` (${alt12Why.join(', ')})`: ''}`);
                        if (alt5) segs.push(`5th - dating/pleasure${alt5Why.length? ` (${alt5Why.join(', ')})`: ''}`);
                        if (alt10) segs.push(`10th - authority/public${alt10Why.length? ` (${alt10Why.join(', ')})`: ''}`);
                        return (
                          <div className="text-xs">Context links: {segs.length ? segs.join(' | ') : '-'}</div>
                        );
                      })()}
                      <div className="text-xs mt-1">Dispositor path: {dispChain.length? dispChain.join(' -> ') : '-'} | mutual reception: {mutualReception? 'Yes':'No'} | light mediation: {translOrCollect}</div>
                      {(() => {
                        try {
                          const pMean = (name) => {
                            const dict = data?.planetary_meanings || {};
                            const entry = dict?.[name] || {};
                            const src = entry.crime || entry.general || '';
                            // take first 2 comma-separated snippets for brevity
                            const parts = String(src).split(',').map(s=> s.trim()).filter(Boolean);
                            return parts.slice(0,2).join('/');
                          };
                          const hMean = (h) => {
                            const dict = data?.house_meanings || {};
                            const entry = dict?.[String(h)] || {};
                            const src = entry.crime || entry.general || '';
                            const parts = String(src).split(',').map(s=> s.trim()).filter(Boolean);
                            return parts.slice(0,2).join('/');
                          };
                          const degKeys = (sign, degInt) => {
                            const dict = data?.degree_special || {};
                            const out = [];
                            const specials = dict?.special || {};
                            const key = `${sign}_${degInt}`;
                            if (specials[key] && specials[key].label) out.push(String(specials[key].label));
                            const sd = (dict?.sign_degrees || {})[sign];
                            if (Array.isArray(sd)) {
                              sd.forEach(entry => {
                                const arr = Array.isArray(entry?.degree) ? entry.degree : [];
                                if (arr.includes(degInt)) {
                                  const kws = Array.isArray(entry?.keywords) ? entry.keywords : [];
                                  if (kws.length) out.push(kws.slice(0,3).join('/'));
                                }
                              });
                            }
                            return out;
                          };
                          const chainDesc = dispChain.slice(0,4).map((nm) => {
                            const info = features?.planets?.[nm] || {};
                            const h = info?.house;
                            const sign = info?.sign;
                            let degInt = null;
                            if (typeof info?.degree_in_sign === 'number') degInt = Math.round(info.degree_in_sign);
                            else if (isFinite(info?.longitude)) degInt = Math.round(((Number(info.longitude)%30)+30)%30);
                            const bits = [];
                            const pk = pMean(nm); if (pk) bits.push(pk);
                            if (h != null) { const hk = hMean(h); if (hk) bits.push(hk); }
                            if (sign && degInt != null) {
                              const dk = degKeys(sign, degInt);
                              if (dk.length) bits.push(dk.join(' · '));
                            }
                            const pos = (sign && degInt != null) ? ` (${sign} ${degInt}°${h? ` · H${h}`:''})` : (h? ` (H${h})` : '');
                            return `${nm}${pos}: ${bits.join(' · ')}`;
                          });
                          return (
                            <div className="text-xs mt-1">
                              <div className="font-medium">Dispositor cues</div>
                              <ul className="list-disc ml-4">
                                {chainDesc.length ? chainDesc.map((t,i)=> <li key={i} className="text-[11px]">{t}</li>) : <li className="text-[11px]">-</li>}
                              </ul>
                            </div>
                          );
                        } catch(_) { return null; }
                      })()}
                      <div className="text-xs mt-1">Derived-house links: money H{derived.money.house}{derived.money.planets.length? ` -> ${derived.money.planets.join(', ')}`: ''} | home H{derived.home.house}{derived.home.planets.length? ` -> ${derived.home.planets.join(', ')}`: ''} | route/vehicle H{derived.comms.house}{derived.comms.planets.length? ` -> ${derived.comms.planets.join(', ')}`: ''} | friends H{derived.friends.house}{derived.friends.planets.length? ` -> ${derived.friends.planets.join(', ')}`: ''}</div>
                    </div>
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">Counterpart Chart Signals</div>
                      <ul className="text-xs list-disc ml-4 space-y-1">
                        <li>Mars contacts: {formatForensicAspectLabels(bpf.Mars)}</li>
                        <li>Saturn contacts: {formatForensicAspectLabels(bpf.Saturn)}</li>
                        <li>Neptune contacts: {formatForensicAspectLabels(bpf.Neptune)}</li>
                        <li>Pluto contacts: {formatForensicAspectLabels(bpf.Pluto)}</li>
                        <li>Sun/Moon fixed stars: {fsSunMoon.length? fsSunMoon.map(fsDescribe).filter(Boolean).join(' | '): '-'}</li>
                        <li>Cusp fixed stars: {fsCusps.length? fsCusps.map(fsDescribe).filter(Boolean).join(' | '): '-'}</li>
                      </ul>
                  {/* Dominance and Profile Hints */}
                  {(() => {
                    try {
                      const domPlanets = (data?.dominance && data.dominance.planets) ? data.dominance.planets : {};
                      const domArr = Object.entries(domPlanets).map(([name, v]) => ({ name, score: Number(v?.score)||0, level: String(v?.level||'') }));
                      domArr.sort((a,b)=> b.score - a.score);
                      const top2 = domArr.slice(0,2);
                      return (
                        <div className="mt-2 pt-2 border-t border-zinc-200">
                          <div className="font-medium mb-1">Dominant signals</div>
                          <div className="text-xs mb-1">{top2.length ? top2.map(d=> `${d.name}: ${d.score} (${d.level})`).join(' · ') : '-'}</div>
                          {/* Relationship Signals */}
                          <div className="font-medium mt-2 mb-1">Relationship Signals</div>
                          {(() => {
                            try {
                              const sr = { Aries:'Mars', Taurus:'Venus', Gemini:'Mercury', Cancer:'Moon', Leo:'Sun', Virgo:'Mercury', Libra:'Venus', Scorpio:'Mars', Sagittarius:'Jupiter', Capricorn:'Saturn', Aquarius:'Saturn', Pisces:'Jupiter' };
                              const triplicity = {
                                Fire: { signs: ['Aries','Leo','Sagittarius'], rulers: ['Mars','Sun','Jupiter'] },
                                Earth: { signs: ['Taurus','Virgo','Capricorn'], rulers: ['Venus','Mercury','Saturn'] },
                                Air: { signs: ['Gemini','Libra','Aquarius'], rulers: ['Mercury','Venus','Saturn'] },
                                Water: { signs: ['Cancer','Scorpio','Pisces'], rulers: ['Moon','Mars','Jupiter'] },
                              };
                              const exaltation = { Sun:'Aries', Moon:'Taurus', Mercury:'Virgo', Venus:'Pisces', Mars:'Capricorn', Jupiter:'Cancer', Saturn:'Libra' };
                              const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
                              const opp = (s) => signs[(signs.indexOf(s)+6)%12] || null;
                              const ascp = features?.planets?.[firstRuler] || {};
                              const dscp = features?.planets?.[seventhRuler] || {};
                              const victimSign = ascp?.sign; const perpSign = dscp?.sign;
                              const victimHouse = ascp?.house; const perpHouse = dscp?.house;
                              const planets = features?.planets || {};
                              const rulersMap = features?.house_rulers || {};
                              const recData = (data?.receptions) || {};
                              const mutual = Array.isArray(recData.mutual) ? recData.mutual : [];
                              const uni = Array.isArray(recData.top_unilateral) ? recData.top_unilateral : [];
                              const starRel = data?.relationship_star_hits || {};
                              const h7List = Object.entries(planets).filter(([,p])=> p?.house===7).map(([n])=> n);

                              // Level 1: Direct Rulership Connections (either direction)
                              const directVictRulesPerp = victimSign && sr[perpSign] === firstRuler;
                              const directPerpRulesVict = perpSign && sr[victimSign] === seventhRuler;
                              const level1 = { directVictRulesPerp, directPerpRulesVict };

                              // Level 2: Mutual Reception between first and seventh rulers
                              const isMutual = mutual.some(m => (m.p1===firstRuler && m.p2===seventhRuler) || (m.p1===seventhRuler && m.p2===firstRuler));

                              // Level 3: Triplicity shared
                              const triOf = (sign) => Object.keys(triplicity).find(k => triplicity[k].signs.includes(sign));
                              const level3 = victimSign && perpSign && (triOf(victimSign) === triOf(perpSign));

                              // Level 4: Exaltation/Fall relationships
                              const perpExaltSign = exaltation[seventhRuler];
                              const victExaltSign = exaltation[firstRuler];
                              const level4_victim_in_exalt_of_perp = victimSign && (victimSign === perpExaltSign);
                              const level4_victim_in_fall_of_perp = victimSign && (victimSign === opp(perpExaltSign));
                              const level4_perp_in_exalt_of_victim = perpSign && (perpSign === victExaltSign);
                              const level4_perp_in_fall_of_victim = perpSign && (perpSign === opp(victExaltSign));

                              // Level 5: Terms - check unilateral dignities containing 'term' in either direction
                              const termDir = uni.filter(u => ((u.receiving===firstRuler && u.received===seventhRuler) || (u.receiving===seventhRuler && u.received===firstRuler)) && (u.dignities||[]).includes('term'));
                              const level5_terms = termDir.length>0;

                              // House placement analysis
                              const houseFlags = [];
                              if (victimHouse===1) houseFlags.push('Victim ruler in 1st (self-contained)');
                              if (victimHouse===7) houseFlags.push('Victim ruler in 7th (in perpetrator domain)');
                              // Do not imply family involvement unless BOTH rulers share 4th or 10th; keep single flags neutral
                              if (victimHouse===4||victimHouse===10) houseFlags.push('Victim ruler in 4th/10th');
                              if (victimHouse===8) houseFlags.push('Victim ruler in 8th (shared resources/intimate)');
                              if (victimHouse===12) houseFlags.push('Victim ruler in 12th (hidden/secret)');
                              if (perpHouse===1) houseFlags.push('Perpetrator ruler in 1st (immediate proximity)');
                              if (perpHouse===4||perpHouse===10) houseFlags.push('Perpetrator ruler in 4th/10th');
                              if (perpHouse===6) houseFlags.push('Perpetrator ruler in 6th (service/subordinate)');
                              if (perpHouse===11) houseFlags.push('Perpetrator ruler in 11th (friend/associate)');
                              if (perpHouse===7) houseFlags.push('Perpetrator ruler in 7th (own domain)');
                              const sameHouse = (victimHouse!=null && perpHouse!=null && victimHouse===perpHouse);
                              if (sameHouse) houseFlags.push('Both rulers in same house (entanglement)');
                              // Critical combinations + scoring for crossovers
                              const crit = [];
                              {
                                const _vh = Number(victimHouse), _ph = Number(perpHouse);
                                if ((_vh===4 && _ph===4) || (_vh===10 && _ph===10)) crit.push('Both rulers in same family house (4 or 10)');
                              }
                              if (victimHouse===7 && perpHouse===1) crit.push('Victim in 7th + Perp in 1st (intimate partners)');
                              if ((victimHouse===1 && perpHouse===7) || (victimHouse===7 && perpHouse===1)) crit.push('1st/7th exchange (known to each other)');
                              // NOTE: scoring for house crossovers is applied after score is initialized below

                              // Traditional ruler analysis
                              const trad = [];
                              if (h7List.includes('Venus')) trad.push('Venus in 7th (female perpetrator possible)');
                              if (h7List.includes('Mars')) trad.push('Mars in 7th (male perpetrator possible)');
                              if ((planets?.Sun?.house===4) || (planets?.Sun?.angular && (rulersMap['4']==='Sun'))) trad.push('Sun/4th emphasis (father figure)');
                              if ((planets?.Moon?.house===10) || (planets?.Moon?.angular && (rulersMap['10']==='Moon'))) trad.push('Moon/10th emphasis (mother figure)');
                              if (Object.values(planets).some(p=> p?.house===5)) trad.push('5th house connection (child involvement)');
                              if (Object.values(planets).some(p=> p?.house===3)) trad.push('3rd house emphasis (sibling/neighbors)');

                              // Aspect analysis
                              const aspMap = features?.aspects || {};
                              const key1 = `${firstRuler}_to_${seventhRuler}`;
                              const key2 = `${seventhRuler}_to_${firstRuler}`;
                              const a = aspMap[key1] || aspMap[key2] || null;
                              const aspType = a?.type || null; // 'conjunction','trine','square','opposition','sextile'
                              const aspectFlags = [];
                              if (aspType) {
                                const easy = ['conjunction','trine','sextile'];
                                const hard = ['square','opposition'];
                                if (easy.includes(aspType)) aspectFlags.push(`Harmonious aspect (${aspType})`);
                                if (hard.includes(aspType)) aspectFlags.push(`Stressful aspect (${aspType})`);
                              } else {
                                aspectFlags.push('No direct aspects between rulers');
                              }

                              // Degree indicators
                              const degInt = (nm)=> { const d = planets?.[nm]?.degree_in_sign; return (typeof d==='number')? Math.round(d): null; };
                              const dVict = degInt(firstRuler);
                              const dPerp = degInt(seventhRuler);
                              const degFlags = [];
                              const mark = (lab,cond)=> { if (cond) degFlags.push(lab); };
                              mark('0° new situation (victim)', dVict===0);
                              mark('0° new situation (perpetrator)', dPerp===0);
                              mark('15° assassination degree (victim)', dVict===15);
                              mark('15° assassination degree (perp)', dPerp===15);
                              mark('29° crisis (victim)', dVict===29);
                              mark('29° crisis (perp)', dPerp===29);
                              // Fixed stars on significators
                              const relStars = starRel || {};
                              const starNames = (arr)=> (Array.isArray(arr)? arr.map(h=> h?.name).filter(Boolean): []);
                              const starFlags = [];
                              const ascStars = starNames(relStars.asc_ruler);
                              const dscStars = starNames(relStars.dsc_ruler);
                              if (ascStars.length) starFlags.push(`ASC ruler on ${ascStars.join('/')}`);
                              if (dscStars.length) starFlags.push(`DSC ruler on ${dscStars.join('/')}`);

                              const violentStars = new Set(['Algol','Antares']);
                              const protectStars = new Set(['Spica']);
                              const hasViolent = [...ascStars, ...dscStars].some(n=> violentStars.has(n));
                              const hasProtect = [...ascStars, ...dscStars].some(n=> protectStars.has(n));
                              const moonDispositorTiesPerp = Boolean(f?.moon?.dispositor_to_seventh_ruler_type);
                              const moonDispositorHardContact = Boolean(f?.moon?.dispositor_to_seventh_ruler_hard);
                              const moonDispositorCue = moonDispositorTiesPerp
                                ? `Moon dispositor ${f?.moon?.dispositor || 'ruler'} ${f?.moon?.dispositor_to_seventh_ruler_type || 'contacts'} ${seventhRuler || '7th ruler'}`
                                : null;
                              const relationshipScore = scoreForensicRelationshipLink({
                                victimHouse,
                                perpHouse,
                                sameHouse,
                                directVictRulesPerp: level1.directVictRulesPerp,
                                directPerpRulesVict: level1.directPerpRulesVict,
                                isMutual,
                                level3,
                                level4VictimInExaltOfPerp: level4_victim_in_exalt_of_perp,
                                level4PerpInExaltOfVictim: level4_perp_in_exalt_of_victim,
                                level4VictimInFallOfPerp: level4_victim_in_fall_of_perp,
                                level4PerpInFallOfVictim: level4_perp_in_fall_of_victim,
                                directionalReception: uni.some(u=> (u.receiving===firstRuler && u.received===seventhRuler) || (u.receiving===seventhRuler && u.received===firstRuler)),
                                level5Terms: level5_terms,
                                criticalFamilyHouse: crit.includes('Both rulers in same family house (4 or 10)'),
                                lightMediation: lm,
                                seventhHousePlanets: h7List,
                                aspectType: aspType,
                                aspect: a,
                                criticalDegree: dVict===0||dVict===15||dVict===29||dPerp===0||dPerp===15||dPerp===29,
                                hasViolentStar: hasViolent,
                                hasProtectiveStar: hasProtect,
                                moonDispositorTiesPerp,
                                moonDispositorHardContact,
                                victimSignificators: [firstRuler, 'Moon'].filter(Boolean),
                                perpetratorSignificators: [seventhRuler].filter(Boolean),
                              });
                              const score = relationshipScore.score;

                              const relationshipSummary = summarizeForensicRelationshipLink({
                                score,
                                victimHouse,
                                perpHouse,
                                seventhHousePlanets: h7List,
                                isMutual,
                                forensicResult: data,
                              });
                              const bothIn4 = Number(victimHouse) === 4 && Number(perpHouse) === 4;
                              const bothIn10 = Number(victimHouse) === 10 && Number(perpHouse) === 10;
                              const relationshipRows = buildRelationshipDisplayRows({
                                firstRuler,
                                moonContacts: aspectTo('Moon'),
                                ascRulerContacts: aspectTo(firstRuler),
                                directVictRulesPerp: level1.directVictRulesPerp,
                                directPerpRulesVict: level1.directPerpRulesVict,
                                isMutual,
                                level3,
                                exaltationFallFlags: [
                                  level4_victim_in_exalt_of_perp ? 'victim in exaltation of perpetrator' : null,
                                  level4_perp_in_exalt_of_victim ? 'perpetrator in exaltation of victim' : null,
                                  level4_victim_in_fall_of_perp ? 'victim in fall of perpetrator' : null,
                                  level4_perp_in_fall_of_victim ? 'perpetrator in fall of victim' : null,
                                ].filter(Boolean),
                                level5Terms: level5_terms,
                                houseConnections: (bothIn4 || bothIn10)
                                  ? ['shared family-house placement (4th/10th)']
                                  : houseFlags.concat(crit),
                                traditionalCues: moonDispositorCue ? trad.concat(moonDispositorCue) : trad,
                                aspectTies: aspectFlags,
                                degreeStarCues: degFlags.concat(starFlags),
                                score,
                                relationshipType: relationshipSummary.relationshipType,
                                confidence: relationshipSummary.confidence,
                              });

                              return (
                                <div className="text-xs space-y-1">
                                  <div>Contact signals: {relationshipRows.contactSignals}</div>
                                  <div>Rulership links: {relationshipRows.rulershipLinks}</div>
                                  <div>Mutual reception: {relationshipRows.mutualReception}</div>
                                  <div>Shared triplicity: {relationshipRows.sharedTriplicity}</div>
                                  <div>Exaltation/fall ties: {relationshipRows.exaltationFallTies}</div>
                                  <div>Term/bounds ties: {relationshipRows.termBoundsTies}</div>
                                  <div>House overlap: {relationshipRows.houseOverlap}</div>
                                  <div>Traditional cues: {relationshipRows.traditionalCues}</div>
                                  <div>Aspect ties: {relationshipRows.aspectTies}</div>
                                  <div>Degree/star cues: {relationshipRows.degreeStarCues}</div>
                                  <div className="font-medium mt-1">Connection summary: {relationshipRows.connectionSummary}</div>
                                </div>
                              );
                            } catch(_) { return <div className="text-xs">-</div>; }
                          })()}
                        </div>
                      );
                    } catch(_) { return null; }
                  })()}
                    </div>
                  </div>
                );
              })()}
            </div>
          )
        ))}

        {showForensicSection('relationship') && card('Relationship Signals', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              <div className="forensic-dossier-verdict">
                <div className="forensic-dossier-verdict-lead">
                  <div className="forensic-dossier-label mb-1">Relationship Score</div>
                  <div className="forensic-dossier-score is-teal">
                    <span>{relationshipInsight?.score ?? 0}</span>
                    <small>{relationshipInsight?.summary?.confidence || relationshipSnapshot.confidence} rule strength</small>
                  </div>
                  <div className="forensic-dossier-card-note">
                    {relationshipInsight?.summary?.relationshipType || relationshipSnapshot.relationshipType}
                  </div>
                </div>
                <div className="forensic-dossier-panel">
                  <div className="font-medium mb-1">Connection Summary</div>
                  <div className="text-xs space-y-1">
                    <div>Contact: {relationshipInsight?.rows?.contactSignals || '-'}</div>
                    <div>Rulership: {relationshipInsight?.rows?.rulershipLinks || '-'}</div>
                    <div>Mutual reception: {relationshipInsight?.rows?.mutualReception || '-'}</div>
                    <div>Triplicity: {relationshipInsight?.rows?.sharedTriplicity || '-'}</div>
                    <div>Exaltation/fall: {relationshipInsight?.rows?.exaltationFallTies || '-'}</div>
                    <div>Terms/bounds: {relationshipInsight?.rows?.termBoundsTies || '-'}</div>
                    <div>House overlap: {relationshipInsight?.rows?.houseOverlap || '-'}</div>
                    <div>Traditional cues: {relationshipInsight?.rows?.traditionalCues || '-'}</div>
                    <div>Aspects: {relationshipInsight?.rows?.aspectTies || '-'}</div>
                    <div>Degree/star cues: {relationshipInsight?.rows?.degreeStarCues || '-'}</div>
                    <div className="font-medium mt-1">Summary: {relationshipInsight?.rows?.connectionSummary || '-'}</div>
                  </div>
                </div>
              </div>
              <div className="forensic-dossier-panel">
                <div className="font-medium mb-1">Supporting Signals</div>
                <div className="forensic-dossier-chip-row">
                  {relationshipInsight?.reasons?.length ? relationshipInsight.reasons.map((reason, index) => (
                    <span key={`${reason}-${index}`} className="forensic-dossier-chip is-teal">
                      <span className="forensic-dossier-chip-dot" />
                      {reason}
                    </span>
                  )) : <span className="text-xs text-zinc-500">No strong relationship indicators were found.</span>}
                </div>
              </div>
            </div>
          )
        ))}

        {showForensicSection('witnesses') && card('Witness & Accomplice Detection', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              {(() => {
                const pls = features?.planets || {};
                const houseList = (h)=> Object.entries(pls).filter(([,p])=> p?.house===h).map(([n])=> n);
                const mercuryHouse = pls?.Mercury?.house || '-';
                const witnesses = ['Mercury', ...houseList(3)];
                const associates = houseList(11);
                const hidden = [...houseList(6), ...houseList(12)];
                const groupings = Object.values(pls).reduce((acc,p)=>{ const h=p?.house; if (!h) return acc; acc[h]=(acc[h]||0)+1; return acc; }, {});
                const multiHouses = Object.entries(groupings).filter(([,c])=> c>=2).map(([h])=> h);
                const wdict = data?.witness_accomplice || {};
                const mod = (k)=> (wdict?.condition_modifiers?.[k] || '');
                const solar = features?.solar || {};
                const inSolar = (k, p) => Array.isArray(solar?.[k]) && solar[k].includes(p);
                const houseGroup = (h) => { const n=Number(h); if ([1,4,7,10].includes(n)) return 'angular'; if ([2,5,8,11].includes(n)) return 'succedent'; return 'cadent'; };
                const planetQualifiers = (name) => {
                  try {
                    const p = pls?.[name] || {};
                    if (!p || p.house==null) return [];
                    const tags = [];
                    tags.push(mod(houseGroup(p.house)));
                    if (p.retrograde) tags.push(mod('retrograde'));
                    if (p.anaretic) tags.push(mod('anaretic'));
                    if (p.ingress) tags.push(mod('ingress'));
                    if (p.via_combusta) tags.push(mod('via_combusta'));
                    if (inSolar('cazimi', name)) tags.push(mod('cazimi'));
                    if (inSolar('combustion', name)) tags.push(mod('combustion'));
                    if (inSolar('under_beams', name)) tags.push(mod('under_beams'));
                    return tags.filter(Boolean).slice(0,3);
                  } catch(_) { return []; }
                };
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">Additional People</div>
                      <ul className="text-xs list-disc ml-4 space-y-1">
                        <li>Mercury witness/sibling marker: H{mercuryHouse}{(() => { const q=planetQualifiers('Mercury'); return q.length? ` - ${q.join(' · ')}` : ''; })()}</li>
                        <li>3rd House (neighbors/local): {(() => { const arr = houseList(3); const out = arr.map(p=> { const q=planetQualifiers(p); return q.length? `${p} - ${q.join(' · ')}`: p; }); return out.length? out.join(', '): '-'; })()}</li>
                        <li>11th House (friends/associates): {(() => { const out = associates.map(p=> { const q=planetQualifiers(p); return q.length? `${p} - ${q.join(' · ')}`: p; }); return out.length? out.join(', '): '-'; })()}</li>
                        <li>6th/12th (hidden enemies): {(() => { const out = hidden.map(p=> { const q=planetQualifiers(p); return q.length? `${p} - ${q.join(' · ')}`: p; }); return out.length? out.join(', '): '-'; })()}</li>
                        <li>Planetary groupings (≥2 in house): {multiHouses.length? multiHouses.map(h=> `H${h}`).join(', '): '-'}</li>
                      </ul>
                    </div>
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">Witness Markers</div>
                      <div className="text-xs">{witnesses.join(', ') || '-'}</div>
                      {(() => {
                        try {
                          const base = wdict?.roles?.Mercury?.base;
                          const q = planetQualifiers('Mercury');
                          if (!base && q.length===0) return null;
                          return (
                            <div className="text-[11px] text-zinc-600 mt-1">Mercury: {(base||'').trim()}{q.length? ` - ${q.join(' · ')}`:''}</div>
                          );
                        } catch(_) { return null; }
                      })()}
                    </div>
                  </div>
                );
              })()}
            </div>
          )
        ))}

        {showForensicSection('deception') && card('Deception Configuration', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm">
              {(() => {
                try {
                  const pls = features?.planets || {};
                  const asp = features?.aspects || {};
                  const houses = features?.houses || {};
                  const solar = features?.solar || {};
                  const getA = (a,b,types)=> {
                    const tset = types? new Set(types.map(x=> String(x).toLowerCase())): null;
                    const hit = (k)=> {
                      const v = asp[k]; if (!v) return false;
                      if (tset && !tset.has(String(v.type||'').toLowerCase())) return false;
                      return true;
                    };
                    return hit(`${a}_to_${b}`) || hit(`${b}_to_${a}`);
                  };
                  const hasApp = (a,b)=> {
                    const va = asp[`${a}_to_${b}`]; const vb = asp[`${b}_to_${a}`];
                    return (va && va.applying===true) || (vb && vb.applying===true);
                  };
                  const inHouse = (p,h)=> (pls?.[p]?.house === h);
                  const hard = ['square','opposition'];
                  let score = 0;
                  const flags = [];
                  // Mercury-based
                  if (getA('Mercury','Neptune')) { score += hasApp('Mercury','Neptune')? 2:1; flags.push('Mercury–Neptune'); }
                  if (pls?.Mercury?.retrograde) { score += 1; flags.push('Mercury retrograde'); }
                  if (Array.isArray(solar?.combustion) && solar.combustion.includes('Mercury')) { score += 1; flags.push('Mercury combust'); }
                  if (inHouse('Mercury',12)) { score += 1; flags.push('Mercury in 12th'); }
                  if (pls?.Mercury?.mute_sign) { score += 1; flags.push('Mercury in mute sign'); }
                  // Neptune: master deceiver
                  const personals = ['Sun','Moon','Mercury','Venus','Mars'];
                  if (personals.some(p=> getA('Neptune', p))) { score += 1; flags.push('Neptune to personals'); }
                  if (inHouse('Neptune',7)) { score += 1; flags.push('Neptune in 7th'); }
                  if (inHouse('Neptune',12)) { score += 1; flags.push('Neptune in 12th'); }
                  if (houses?.neptune_angular === true) { score += 1; flags.push('Neptune angular'); }
                  // Mars–Neptune
                  if (getA('Mars','Neptune',['opposition'])) { score += 2; flags.push('Mars–Neptune opposition'); }
                  if (getA('Mars','Neptune',['square'])) { score += 1; flags.push('Mars–Neptune square'); }
                  // Venus–Saturn
                  if (getA('Venus','Saturn',hard)) { score += 1; flags.push('Venus–Saturn hard'); }
                  const vSign = pls?.Venus?.sign;
                  if (['Aries','Scorpio'].includes(vSign) && (getA('Venus','Saturn') || pls?.Saturn?.angular)) { score += 1; flags.push('Venus detriment w/ Saturn'); }
                  // House-based
                  if (houses?.emphasis12_strong) { score += 1; flags.push('12th house emphasis'); }
                  if (houses?.seventh_ruler_in_12th) { score += 1; flags.push('7th ruler in 12th'); }
                  if (pls?.Sun?.house===12 || pls?.Moon?.house===12) { score += 1; flags.push('Sun/Moon in 12th'); }
                  if (houses?.mute_signs_on_angles) { score += 1; flags.push('Mute signs on angles'); }
                  if (houses?.mute_sign_on_3rd_or_9th) { score += 1; flags.push('Mute signs on 3rd/9th'); }
                  if (houses?.north_node_in_8th) { score += 1; flags.push('North Node in 8th'); }
                  // NN in 4th - domestic deception tilt
                  const nnHouse = houses?.north_node_house;
                  if (nnHouse === 4) { score += 1; flags.push('North Node in 4th'); }
                  // Saturn–Neptune cover-up
                  if (getA('Saturn','Neptune')) { score += 1; flags.push('Saturn–Neptune'); }
                  // Node + deceptive planets
                  const nodeNames = ['North Node','Node'];
                  if (nodeNames.some(nm => getA(nm,'Neptune'))) { score += 1; flags.push('Node+Neptune'); }
                  if (nodeNames.some(nm => getA(nm,'Mercury'))) { score += 1; flags.push('Node+Mercury'); }

                  // Truth indicators (streamlined)
                  let truth = 0; const truths = [];
                  if (!houses?.mute_signs_on_angles && !houses?.mute_sign_on_3rd_or_9th) { truth += 1; truths.push('No mute sign emphasis'); }

                  const adjusted = Math.max(0, score - truth);
                  const level = (s)=> s>=8? 'Critical' : (s>=5? 'High' : (s>=3? 'Medium' : 'Low'));
                  const lvl = level(adjusted);
                  const show = flags.slice(0,8);
                  const flagKeywords = {
                    'Mercury–Neptune': 'Lies/cover‑ups; confusion and disinfo',
                    'Mercury retrograde': 'Revisions, reversals, withheld info',
                    'Mercury combust': 'Hidden facts; impaired communication',
                    'Mercury in 12th': 'Secrets; behind‑the‑scenes messaging',
                    'Mercury in mute sign': 'Silence; refusal to speak plainly',
                    'Neptune to personals': 'Illusion/fantasy around key actors',
                    'Neptune in 7th': 'Partner/open enemy deception',
                    'Neptune in 12th': 'Hidden deception; secret enemies',
                    'Neptune angular': 'Major staged/disguised events',
                    'Mars–Neptune opposition': 'Abduction/kidnapping cover',
                    'Mars–Neptune square': 'Violence + deception; missing evidence',
                    'Venus–Saturn hard': 'Relational deception/abuse',
                    'Venus detriment w/ Saturn': 'Deceptive charm; relational harm',
                    '12th house emphasis': 'Hidden enemies; cover‑ups; confinement',
                    '7th ruler in 12th': 'Partner’s secrecy',
                    'Sun/Moon in 12th': 'Identity hidden; secret activities',
                    'Mute signs on angles': 'Secrecy around the chart axis',
                    'Mute signs on 3rd/9th': 'Deception in comms/legal',
                    'North Node in 8th': 'Schemes/insurance ruses',
                    'North Node in 4th': 'Domestic staging/real estate ruse',
                    'Saturn–Neptune': 'Authority/institutional cover‑up',
                    'Node+Neptune': 'Karmic ruse with Neptune',
                    'Node+Mercury': 'Karmic ruse in communications',
                    'Jupiter↔Mercury easy': 'Clarity, lawful/ethical comms',
                    'Strong 3rd/9th': 'Robust comms/legal axis',
                    'No mute sign emphasis': 'Open, explicit signaling',
                    'Direct motion predominance': 'Less revision/reversal tendency',
                  };
                  const keywordLines = [];
                  flags.forEach(f=> { const k = flagKeywords[f]; if (k) keywordLines.push(`• ${f} - ${k}`); });
                  truths.forEach(f=> { const k = flagKeywords[f]; if (k) keywordLines.push(`• ${f} - ${k}`); });
                  return (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="border rounded p-2">
                        <div className="flex items-center gap-2 mb-1">
                          <div className="font-medium">Deception Level</div>
                          {(() => {
                            const col = (lvl==='Critical')? '#DC2626' : (lvl==='High')? '#F97316' : (lvl==='Medium')? '#F59E0B' : '#10B981';
                            const hatch = `repeating-linear-gradient(45deg, ${col} 0, ${col} 2px, rgba(255,255,255,0.25) 2px, rgba(255,255,255,0.25) 4px)`;
                            const active = (lvl==='Critical')?4:(lvl==='High')?3:(lvl==='Medium')?2:1;
                            return (
                              <div className="flex gap-[2px]" aria-hidden="true">
                                {Array.from({ length: 4 }).map((_, i) => (
                                  <div key={i} className="w-4 h-3 rounded-[2px] border border-zinc-300"
                                       style={ i < active ? { backgroundImage: hatch, backgroundColor: col, boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.06)' } : {} } />
                                ))}
                              </div>
                            );
                          })()}
                        </div>
                        <div className="text-xs">Deception level: <span className="font-semibold">{lvl}</span> <span className="text-zinc-500">({adjusted})</span></div>
                      </div>
                      <div className="border rounded p-2">
                        <div className="font-medium mb-1">Key Signals</div>
                        <div className="text-xs">{show.length? show.join(' · ') : '-'}</div>
                      </div>
                      <div className="border rounded p-2 md:col-span-2">
                        <div className="font-medium mb-1">Signal Notes</div>
                        <div className="text-[11px] whitespace-pre-line">{keywordLines.length? keywordLines.join('\n') : '-'}</div>
                      </div>
                    </div>
                  );
                } catch(_) {
                  return <div className="text-xs text-zinc-500">Unavailable</div>;
                }
              })()}
            </div>
          )
        ))}

        {showForensicSection('findings') && card('Outcome Determination', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              {(() => {
                const cusps = features?.house_cusps || [];
                const cusp4 = Number(cusps?.[3]);
                const icDeg = isFinite(cusp4) ? degreeTextFromLon(cusp4) : '-';
                const cusp4Sign = isFinite(cusp4) ? signFromLon(cusp4) : '-';
                const icDict = data?.ic_sign_meanings || {};
                const icExpl = cusp4Sign && icDict?.[cusp4Sign]?.outcome;
                const ruler4 = features?.house_rulers?.['4'] || features?.house_rulers?.[4] || null;
                const ruler4House = ruler4 ? features?.planets?.[ruler4]?.house : null;
                const icRulerDict = data?.ic_ruler_house_meanings || {};
                const icRulerExpl = (ruler4House != null) ? (icRulerDict?.[String(ruler4House)]?.outcome) : null;
                const planets = features?.planets || {};
                const in4All = Object.entries(planets).filter(([,p])=> p?.house===4).map(([n])=> n);
                const icP4 = data?.ic_planet_in_4th || {};
                const nodeNames = new Set(['North Node','South Node','Node']);
                const nodesIn4 = in4All.filter(nm => nodeNames.has(nm));
                const in4 = in4All.filter(nm => !nodeNames.has(nm));
                const in4Expl = (() => {
                  try {
                    if (!Array.isArray(in4) || in4.length===0) return [];
                    return in4.map(nm => {
                      const expl = icP4?.[nm];
                      return expl ? `${nm} - ${expl}` : nm;
                    });
                  } catch(_) { return in4; }
                })();
                const nodeModExpl = (() => {
                  try {
                    if (!nodesIn4.length) return null;
                    // Prefer explicit North/South Node descriptions, else generic Nodes concept
                    const parts = nodesIn4.map(nm => icP4?.[nm] || 'Karmic hinge; intensifies/tilts the ending');
                    const uniq = Array.from(new Set(parts));
                    return `Node modifier: ${uniq.join(' · ')}`;
                  } catch(_) { return null; }
                })();
                const benefics = ['Venus','Jupiter'];
                const malefics = ['Mars','Saturn'];
                const ben4 = in4.filter(n=> benefics.includes(n));
                const mal4 = in4.filter(n=> malefics.includes(n));
                const outcomeTags = [
                  { label: 'Benefics in 4th -> Positive resolution/recovery', ok: ben4.length>0, extra: ben4.join(', ') },
                  { label: 'Malefics in 4th -> Tragic/violent conclusion', ok: mal4.length>0, extra: mal4.join(', ') },
                  { label: 'Empty 4th House -> Inconclusive/ongoing case', ok: in4.length===0, extra: '' },
                  { label: 'Multiple planets in 4th -> Complex resolution', ok: in4.length>=2, extra: in4.length>=2 ? in4.join(', ') : '' },
                ];
                const asp = features?.aspects || {};
                const infl = (() => {
                  try {
                    const classical = new Set(['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn']);
                    const out = [];
                    for (const [k, v] of Object.entries(asp)) {
                      if (!v) continue;
                      const [p1, p2] = k.split('_to_');
                      const involves4 = (ruler4 && (p1===ruler4 || p2===ruler4)) || in4.includes(p1) || in4.includes(p2);
                      if (!involves4) continue;
                      // Show applying influences from classical planets; hide Node‑only hits for clarity
                      if (v.applying !== true) continue;
                      const other = in4.includes(p1) || (ruler4 && p1===ruler4) ? p2 : p1;
                      if (!classical.has(other)) continue;
                      out.push({ p1, p2, v });
                    }
                    out.sort((a,b)=> {
                      const ao = Math.abs(Number(a.v?.orb ?? 999));
                      const bo = Math.abs(Number(b.v?.orb ?? 999));
                      return ao - bo;
                    });
                    return out.slice(0,5).map(({p1,p2,v})=> `${p1} ${v.type || ''} ${p2}${v.applying? ' (app)':''}`);
                  } catch(_) { return []; }
                })();
                return (
                  <div className="forensic-dossier-outcome-grid">
                    <div className="forensic-dossier-panel">
                      <div className="font-medium mb-1">Primary Analysis Points</div>
                      <div className="forensic-dossier-card-subtitle">4th-house resolution indicators.</div>
                      <ul className="text-xs list-disc ml-4 space-y-1">
                        <li>4th House Cusp Sign {'->'} {cusp4Sign}{icExpl? ` - ${icExpl}`: ''}</li>
                        <li>4th House Ruler Placement {'->'} {ruler4 ? `${ruler4} in H${ruler4House ?? '-'}` : '-'}{icRulerExpl? ` - ${icRulerExpl}`: ''}</li>
                        <li>Planets in 4th House {'->'} {in4Expl.length? in4Expl.join(' · ') : '-'}{nodeModExpl? ` · ${nodeModExpl}`:''}</li>
                        <li>IC (Nadir) Degree {'->'} {icDeg}</li>
                        <li>Aspects influencing 4th House (ruler/occupants) {'->'} {infl.length? infl.join(' · ') : '-'}</li>
                      </ul>
                    </div>
                    <div className="forensic-dossier-panel">
                      <div className="font-medium mb-1">Resolution Pattern</div>
                      <div className="space-y-1">
                        {outcomeTags.map((t, i)=> (
                          <div key={i} className={`forensic-dossier-outcome-row ${t.ok ? 'is-active' : ''}`}>
                            {t.label}{t.extra? ` - ${t.extra}`:''}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )
        ))}
        {showForensicSection('raw') && card('Raw Evidence', (
          loading ? <div className="forensic-dossier-loading">Loading…</div> : (
            <div className="space-y-3">
              <div className="forensic-dossier-empty">
                Detailed case data for review. Expand any group to inspect the underlying fields.
              </div>
              <div className="forensic-dossier-raw-accordion">
                {rawEvidenceGroups.map((group, index) => (
                  <details key={group.title} open={index === 0}>
                    <summary>
                      <span>{group.title}</span>
                      <span className="forensic-dossier-raw-count">
                        {Array.isArray(group.payload) ? group.payload.length : Object.keys(group.payload || {}).length} items
                      </span>
                    </summary>
                    <pre className="forensic-dossier-raw">{JSON.stringify(group.payload, null, 2)}</pre>
                  </details>
                ))}
              </div>
            </div>
          )
        ))}
      </div>
    </div>
    </div>
  );
}

// Subcomponents per spec

function ArabicLotsPanel({ data }){
  const lots = data?.arabic_parts || {};
  const [deathVar, setDeathVar] = useState('A'); // 'A'|'B'
  const [poisonVar, setPoisonVar] = useState('V1'); // 'V1'|'V2'
  const [planeVar, setPlaneVar] = useState('V1'); // 'V1'|'V2'
  const [showOptions, setShowOptions] = useState(false);
  const rows = [];
  const push = (key, label) => { const x = lots[key]; if (x) rows.push({ label, x }); };
  push('fortune', 'Fortune');
  push('spirit', 'Spirit');
  push('peril', 'Peril');
  push(deathVar==='A'?'deathA':'deathB', `Death ${deathVar}`);
  push(poisonVar==='V1'?'poison_v1':'poison_v2', `Poison ${poisonVar}`);
  push(planeVar==='V1'?'plane_v1':'plane_v2', `Plane ${planeVar}`);
  return (
    <div className="text-sm h-full flex flex-col">
      <div className="rounded-2xl border border-zinc-200 bg-white p-3">
        <button
          type="button"
          onClick={()=> setShowOptions(v=>!v)}
          className="w-full text-left flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500 hover:text-zinc-900"
          style={monoStyle}
        >
          <span className="inline-block w-4">{showOptions ? '▾' : '▸'}</span>
          <span>Formula Options</span>
        </button>
        {showOptions && (
          <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px]">
            <div className="flex items-center gap-1">
              <span>Death</span>
              <button onClick={()=>setDeathVar('A')} className={`px-1.5 py-0.5 rounded border ${deathVar==='A'?'border-zinc-800':'border-zinc-300'}`}>A</button>
              <button onClick={()=>setDeathVar('B')} className={`px-1.5 py-0.5 rounded border ${deathVar==='B'?'border-zinc-800':'border-zinc-300'}`}>B</button>
            </div>
            <div className="flex items-center gap-1">
              <span>Poison</span>
              <button onClick={()=>setPoisonVar('V1')} className={`px-1.5 py-0.5 rounded border ${poisonVar==='V1'?'border-zinc-800':'border-zinc-300'}`}>V1</button>
              <button onClick={()=>setPoisonVar('V2')} className={`px-1.5 py-0.5 rounded border ${poisonVar==='V2'?'border-zinc-800':'border-zinc-300'}`}>V2</button>
            </div>
            <div className="flex items-center gap-1">
              <span>Plane</span>
              <button onClick={()=>setPlaneVar('V1')} className={`px-1.5 py-0.5 rounded border ${planeVar==='V1'?'border-zinc-800':'border-zinc-300'}`}>V1</button>
              <button onClick={()=>setPlaneVar('V2')} className={`px-1.5 py-0.5 rounded border ${planeVar==='V2'?'border-zinc-800':'border-zinc-300'}`}>V2</button>
            </div>
          </div>
        )}
      </div>
      <div className="astro-scroll-shell mt-3 flex-1">
        <div className="astro-scroll space-y-2">
          {rows.length===0 ? (
            <div className="text-zinc-500">No lots</div>
          ) : rows.map((r, idx)=> (
            <div key={idx} className="rounded-2xl border border-zinc-100 bg-white px-3 py-2.5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                    {r.label}
                  </div>
                  <div className="mt-1 text-[15px] leading-5 text-zinc-900" style={serifStyle}>
                    {degreeTextFromLon(r.x.lon)} {signFromLon(r.x.lon)}
                  </div>
                </div>
                <div className="text-right text-[11px] text-zinc-500">
                  H{r.x.house ?? '-'}
                </div>
              </div>
              <div className="mt-1 text-[11px] text-zinc-500">Ruler: {r.x.ruler}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SectPanel({ data }) {
  const sect = data?.sect;
  if (!sect) {
    return <div className="text-sm text-zinc-500">No sect data</div>;
  }
  const nice = (x)=> (x==null||x===undefined? '-' : String(x));
  const normalizedSect = normalizeSectValue(sect.chart_sect || sect.sect || sect.type || sect.status);
  if (!normalizedSect) {
    return <div className="text-sm text-zinc-500">No sect data</div>;
  }
  const isDay = normalizedSect === 'diurnal';
  const chartLabel = isDay ? 'Day' : 'Night';
  const mercuryLabel = (()=>{
    if (!sect.mercury_phase) return 'Mercury - -';
    const asg = sect.mercury_assigned_sect === 'diurnal' ? 'day sect' : sect.mercury_assigned_sect === 'nocturnal' ? 'night sect' : '-';
    return `Mercury - ${sect.mercury_phase} star (${asg})`;
  })();
  const rows = (sect.planets||[]).filter(p=> p && p.planet).map(p=> ({
    name: p.planet,
    sectState: p.in_sect === true ? 'in' : p.in_sect === false ? 'out' : 'unknown',
    hayz: !!p.hayz,
    polMatch: p.sign_polarity_match === true,
    hemMatch: p.hemisphere_match === true,
  }));
  return (
    <div className="flex flex-col">
      <div className="border-b border-zinc-100 pb-3">
        <div className="text-[1rem] leading-tight text-zinc-900" style={serifStyle}>
          {chartLabel} · {PlanetSymbols[sect.sect_light] || sect.sect_light}
        </div>
        <div className="mt-1 text-[11px] text-zinc-500">{mercuryLabel}</div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="min-w-0">
            <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>Malefic</div>
            <div className="mt-1 text-[14px] text-zinc-900" style={serifStyle}>{PlanetSymbols[sect.malefic_of_sect] || sect.malefic_of_sect}</div>
          </div>
          <div className="min-w-0 sm:border-l sm:border-zinc-100 sm:pl-4">
            <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>Benefic</div>
            <div className="mt-1 text-[14px] text-zinc-900" style={serifStyle}>{PlanetSymbols[sect.benefic_of_sect] || sect.benefic_of_sect}</div>
          </div>
        </div>
      </div>
      <div className="mt-3">
        {rows.length === 0 ? (
          <div className="text-sm text-zinc-500">No planets listed</div>
        ) : (
          <div className="space-y-2">
            {rows.map((r, i)=> (
              <div key={i} className="border-t border-zinc-100 pt-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-lg leading-none">{PlanetSymbols[r.name] || '·'}</span>
                  <span className="font-medium text-sm text-zinc-900">{r.name}</span>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px]">
                  <span
                    className={`rounded-full border px-1.5 py-0.5 ${
                      r.sectState === 'in'
                        ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                        : r.sectState === 'out'
                          ? 'border-rose-300 bg-rose-50 text-rose-700'
                          : 'border-zinc-200 bg-zinc-50 text-zinc-500'
                    }`}
                    style={monoStyle}
                  >
                    {r.sectState === 'in' ? 'in-sect' : r.sectState === 'out' ? 'out-of-sect' : 'sect n/a'}
                  </span>
                  {r.hayz && <span className="rounded-full border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-sky-700" style={monoStyle}>hayz</span>}
                  {r.polMatch && <span className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-zinc-500" style={monoStyle}>polarity</span>}
                  {r.hemMatch && <span className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-zinc-500" style={monoStyle}>hemisphere</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="mt-auto text-[11px] text-zinc-500">Malefic moderated by sect: {isDay? 'Saturn':'Mars'}.</div>
    </div>
  );
}



function ChartMock({ data, chartLens = 'traditional', onChartLensChange, onSnap, snapDisabled, snapBusy, houseSystem, onHouseSystemChange }){
  const HOUSE_OPTIONS = [
    { code: 'R', label: 'Regiomontanus (R)' },
    { code: 'P', label: 'Placidus (P)' },
    { code: 'E', label: 'Equal (E)' },
    { code: 'W', label: 'Whole Sign (W)' },
    { code: 'O', label: 'Porphyry (O)' },
    { code: 'C', label: 'Campanus (C)' },
    { code: 'K', label: 'Koch (K)' },
    { code: 'T', label: 'Topocentric (T)' },
  ];
  const planetGlyphs = {
    Sun: '☉',
    Moon: '☽',
    Mercury: '☿',
    Venus: '♀',
    Mars: '♂',
    Jupiter: '♃',
    Saturn: '♄',
    Uranus: '♅',
    Neptune: '♆',
    Pluto: '♇',
    'North Node': '☊',
    'South Node': '☋',
    Chiron: '⚷',
  };
  const ascLon = data?.ascendant ?? data?.house_cusps?.[0] ?? 0;
  const midheavenLon = data?.midheaven ?? data?.house_cusps?.[9] ?? null;
  const cusps = Array.isArray(data?.house_cusps) && data.house_cusps.length >= 12
    ? data.house_cusps.slice(0, 12)
    : undefined;
  const ascMeta = useMemo(() => chartPointSummary(ascLon), [ascLon]);
  const midheavenMeta = useMemo(() => chartPointSummary(midheavenLon), [midheavenLon]);
  const fortuneMeta = useMemo(() => extractFortuneLot(data?.arabic_parts), [data?.arabic_parts]);
  const sectMeta = useMemo(() => summarizeSectMeta(data?.sect), [data?.sect]);
  const visiblePlanetRows = useMemo(
    () => filterChartPlanetsByLens(data?.planets, chartLens),
    [data?.planets, chartLens],
  );
  const planets = useMemo(
    () => visiblePlanetRows
      .filter((planet) => planet && typeof planet === 'object' && planet.planet && planet.longitude != null)
      .map((planet) => ({
        id: planet.planet,
        glyph: planetGlyphs[planet.planet] || '·',
        lon: Number(planet.longitude) || 0,
        retro: !!planet.retrograde,
        house: planet.house,
        label: planet.planet,
      })),
    [visiblePlanetRows],
  );
  const visiblePlanetIds = useMemo(() => new Set(planets.map((planet) => planet.id)), [planets]);
  const wheelAspects = useMemo(
    () => buildWheelAspectRows(data?.planetary_aspects_precise, visiblePlanetIds),
    [data?.planetary_aspects_precise, visiblePlanetIds],
  );
  const locationLabel = typeof data?.location === 'string' && data.location.trim()
    ? data.location.trim()
    : 'Set location';
  const timezoneLabel = formatAstroClockTimezoneLabel({
    timestamp: data?.timestamp,
    timezone: data?.timezone,
    timezoneLabel: data?.timezone_label,
  });
  const chartContextLabel = [locationLabel, timezoneLabel].filter(Boolean).join(' • ');
  const chartDateLabel = data?.timestamp ? formatControlDateLabel(String(data.timestamp).split('T')[0]) : '';
  const chartTimeLabel = formatHM(data?.timestamp);
  const chartFooterLabel = ['chart', chartDateLabel, chartTimeLabel, timezoneLabel].filter(Boolean).join(' · ');

  return (
    <div className={`${panelCls} overflow-hidden px-0 py-0`}>
      <div className="border-b border-zinc-200">
        <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-3 sm:px-5">
          <div className="min-w-0 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-zinc-500" style={monoStyle}>
            {chartContextLabel ? <span className="truncate">{chartContextLabel}</span> : <span>Active chart</span>}
          </div>
          <button
            type="button"
            disabled={!!snapDisabled}
            className="inline-flex min-w-[86px] items-center justify-center rounded-full bg-zinc-900 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
            style={monoStyle}
            onClick={onSnap}
          >
            {snapBusy ? 'Saving…' : 'Snap'}
          </button>
        </div>
        <div className="flex flex-col gap-3 border-t border-zinc-200 px-4 py-3 sm:px-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-white p-1">
              {CHART_LENS_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => onChartLensChange?.(option.id)}
                  className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] ${
                    chartLens === option.id
                      ? 'bg-zinc-900 text-white shadow-sm'
                      : 'text-zinc-600 hover:text-zinc-900'
                  }`}
                  style={monoStyle}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <label className="inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.12em] text-zinc-500" style={monoStyle}>
              <span>Houses</span>
              <select
                className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] font-medium tracking-normal text-zinc-700"
                value={houseSystem || 'R'}
                onChange={(event)=> onHouseSystemChange && onHouseSystemChange(event.target.value)}
                title="House system"
              >
                {HOUSE_OPTIONS.map((option) => (
                  <option key={option.code} value={option.code}>{option.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-3 xl:justify-end">
            <div className="flex flex-wrap items-start gap-4">
              <div className="min-w-[116px]">
                <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>ASC</div>
                <div className="mt-0.5 text-[14px] leading-tight text-zinc-900" style={serifStyle}>
                  {ascMeta ? (
                    <>
                      <span className="text-zinc-700" style={zodiacGlyphStyle}>{ascMeta.glyph}</span>{' '}
                      {ascMeta.sign} {ascMeta.degreeText}
                    </>
                  ) : '—'}
                </div>
              </div>
              <div className="min-w-[116px]">
                <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>MC</div>
                <div className="mt-0.5 text-[14px] leading-tight text-zinc-900" style={serifStyle}>
                  {midheavenMeta ? (
                    <>
                      <span className="text-zinc-700" style={zodiacGlyphStyle}>{midheavenMeta.glyph}</span>{' '}
                      {midheavenMeta.sign} {midheavenMeta.degreeText}
                    </>
                  ) : '—'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="px-2 pb-2 pt-3 sm:px-4">
        <div className="mx-auto w-full max-w-[800px] aspect-square">
          <SketchWheel
            asc={ascMeta?.lon ?? 0}
            midheaven={midheavenMeta?.lon ?? undefined}
            cusps={cusps}
            planets={planets}
            aspects={wheelAspects}
            showAspects={wheelAspects.length > 0}
          />
        </div>
      </div>

      <div className="border-t border-zinc-200 px-4 py-3 sm:px-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 xl:gap-0">
          <div className="min-w-0 xl:px-4 xl:first:pl-0">
            <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>Ascendant</div>
            <div className="mt-1 text-[1.05rem] leading-tight text-zinc-900" style={serifStyle}>
              {ascMeta ? (
                <>
                  <span className="text-zinc-700" style={zodiacGlyphStyle}>{ascMeta.glyph}</span>{' '}
                  {ascMeta.degreeText}
                </>
              ) : '—'}
            </div>
            <div className="mt-1 text-[12px] text-zinc-600">
              {ascMeta ? `${ascMeta.sign} · ruled by ${ascMeta.ruler}` : 'No ascendant data'}
            </div>
          </div>
          <div className="min-w-0 xl:border-l xl:border-zinc-200 xl:px-4">
            <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>Midheaven</div>
            <div className="mt-1 text-[1.05rem] leading-tight text-zinc-900" style={serifStyle}>
              {midheavenMeta ? (
                <>
                  <span className="text-zinc-700" style={zodiacGlyphStyle}>{midheavenMeta.glyph}</span>{' '}
                  {midheavenMeta.degreeText}
                </>
              ) : '—'}
            </div>
            <div className="mt-1 text-[12px] text-zinc-600">
              {midheavenMeta ? `${midheavenMeta.sign} culminating` : 'No midheaven data'}
            </div>
          </div>
          <div className="min-w-0 xl:border-l xl:border-zinc-200 xl:px-4">
            <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>Lot of Fortune</div>
            <div className="mt-1 text-[1.05rem] leading-tight text-zinc-900" style={serifStyle}>
              {fortuneMeta ? `⊕ ${fortuneMeta.degreeText}` : '—'}
            </div>
            <div className="mt-1 text-[12px] text-zinc-600">
              {fortuneMeta ? `${fortuneMeta.sign}${fortuneMeta.house ? ` · H${fortuneMeta.house}` : ''}` : 'No fortune data'}
            </div>
          </div>
          <div className="min-w-0 xl:border-l xl:border-zinc-200 xl:px-4 xl:last:pr-0">
            <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>Sect</div>
            <div className="mt-1 text-[1.05rem] leading-tight text-zinc-900" style={serifStyle}>
              {sectMeta ? `${sectMeta.glyph} ${sectMeta.label}` : '—'}
            </div>
            <div className="mt-1 text-[12px] text-zinc-600">
              {sectMeta?.detail || 'No sect data'}
            </div>
          </div>
        </div>
        {chartFooterLabel ? (
          <div className="mt-3 flex justify-end border-t border-zinc-100 pt-3 text-[10px] text-zinc-400" style={monoStyle}>
            <span className="truncate">{chartFooterLabel}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function MoonCondition({ data }){
  const moon = data?.moon;
  const t = data?.moon_timeline || {};
  const left = moon ? `${degString(moon.longitude)} ${moon.sign}` : '-';
  // Compute basic Moon phase from Sun/Moon elongation (client-side)
  const phaseInfo = (() => {
    try {
      const planets = Array.isArray(data?.planets) ? data.planets : [];
      const m = planets.find(p => p?.planet === 'Moon');
      const s = planets.find(p => p?.planet === 'Sun');
      const mLon = Number(m?.longitude);
      const sLon = Number(s?.longitude);
      if (!isFinite(mLon) || !isFinite(sLon)) return null;
      const norm = (x) => ((x % 360) + 360) % 360;
      const D = norm(mLon - sLon); // elongation
      const illum = Math.max(0, Math.min(1, (1 - Math.cos(D * Math.PI/180)) / 2));
      const pct = Math.round(illum * 100);
      const near = (a, b, tol=8) => Math.abs(norm(a - b)) <= tol;
      let name = '';
      if (near(D, 0)) name = 'New Moon';
      else if (near(D, 90)) name = 'First Quarter';
      else if (near(D, 180)) name = 'Full Moon';
      else if (near(D, 270)) name = 'Last Quarter';
      else if (D > 0 && D < 90) name = 'Waxing Crescent';
      else if (D > 90 && D < 180) name = 'Waxing Gibbous';
      else if (D > 180 && D < 270) name = 'Waning Gibbous';
      else name = 'Waning Crescent';
      const waxing = D < 180;
      return { name, pct, waxing };
    } catch { return null; }
  })();
  // Format hours to a friendly string, e.g., 1d 5h or 2h 10m
  const fmtH = (h) => {
    if (h == null) return '-';
    const d = Math.floor(h/24); const hr = Math.floor(h%24); const m = Math.round((h*60)%60);
    if (d>0) return `${d}d ${hr}h`;
    if (hr>0) return `${hr}h ${m}m`;
    return `${m}m`;
  };
  // Map aspect numeric/name to canonical name
  const aspectLabel = (val) => {
    if (typeof val === 'string' && val) return val; // already a name like 'Trine'
    const n = typeof val === 'number' ? val : Number(val);
    if (!isFinite(n)) return String(val ?? '');
    if (Math.abs(n - 0) < 1e-6) return 'Conjunction';
    if (Math.abs(n - 60) < 1e-6) return 'Sextile';
    if (Math.abs(n - 90) < 1e-6) return 'Square';
    if (Math.abs(n - 120) < 1e-6) return 'Trine';
    if (Math.abs(n - 180) < 1e-6) return 'Opposition';
    return `${n}\u00B0`;
  };
  const vocTag = t.in_voc
    ? `VoC ends in ${fmtH(t.sign_exit_eta_hours)}`
    : (t.voc_starts_in_hours != null
        ? (t.voc_starts_in_hours <= (1/60) ? 'VoC now' : `VoC in ${fmtH(t.voc_starts_in_hours)}`)
        : 'VoC in -');
  const start = t.next_aspect?.eta_hours != null
    ? `Next ${PlanetSymbols.Moon} ${aspectSymbol(aspectLabel(t.next_aspect.aspect))} ${(PlanetSymbols[t.next_aspect.planet] || t.next_aspect.planet)} in ${fmtH(t.next_aspect.eta_hours)}`
    : '-';
  const next = t.sign_exit_eta_hours != null ? `Next sign ${fmtH(t.sign_exit_eta_hours)}` : '-';
  const prog = typeof t.sign_progress_pct === 'number' ? Math.max(0, Math.min(100, t.sign_progress_pct)) : 0;
  const lunarStatus = (t?.in_voc ?? moon?.void_of_course)
    ? 'Void of course'
    : 'Configured';
  const nextAspectLabel = t?.next_aspect
    ? `${PlanetSymbols.Moon} ${aspectSymbol(aspectLabel(t.next_aspect.aspect))} ${PlanetSymbols[t.next_aspect.planet] || t.next_aspect.planet}`
    : 'No imminent aspect';
  const nextAspectMeta = t?.next_aspect?.eta_hours != null ? `in ${fmtH(t.next_aspect.eta_hours)}` : 'awaiting next perfection';
  const nextSignLabel = moon?.next_sign || t?.next_sign || 'Next sign';
  const nextSignMeta = t.sign_exit_eta_hours != null ? `in ${fmtH(t.sign_exit_eta_hours)}` : 'timing unavailable';
  const signProgressLabel = prog > 0 ? `${prog.toFixed(0)}% through ${moon?.sign || 'current sign'}` : `Just entered ${moon?.sign || 'sign'}`;
  const phaseSummary = phaseInfo
    ? `${phaseInfo.name} · ${phaseInfo.pct}% illuminated${phaseInfo.waxing ? ' · waxing' : ' · waning'}`
    : 'Moon phase unavailable';
  return (
    <div className={panelCls}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
            Lunar State
          </div>
          <h3 className="mt-1 font-semibold text-sm">Moon Condition</h3>
        </div>
        <div className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${
          (t?.in_voc ?? moon?.void_of_course)
            ? 'border-amber-300 bg-amber-50 text-amber-700'
            : 'border-emerald-200 bg-emerald-50 text-emerald-700'
        }`} style={monoStyle}>
          {lunarStatus}
        </div>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.25fr)]">
        <div className="min-w-0">
          <div className="text-[1.45rem] leading-tight text-zinc-900" style={serifStyle}>
            {PlanetSymbols.Moon} {left}
          </div>
          <div className="mt-1 text-[13px] leading-5 text-zinc-700">{phaseSummary}</div>
          <div className="mt-3 grid gap-3 border-t border-zinc-100 pt-3 sm:grid-cols-2">
            <div className="min-w-0">
              <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                VoC Window
              </div>
              <div className="mt-1 text-[14px] leading-5 text-zinc-900" style={serifStyle}>{vocTag}</div>
            </div>
            <div className="min-w-0 sm:border-l sm:border-zinc-100 sm:pl-4">
              <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                Duration
              </div>
              <div className="mt-1 text-[14px] leading-5 text-zinc-900" style={serifStyle}>
                {t.voc_duration_hours != null ? fmtH(t.voc_duration_hours) : 'No VoC duration'}
              </div>
            </div>
          </div>
        </div>
        <div className="min-w-0 space-y-3">
          <div className="grid gap-3 border-t border-zinc-100 pt-3 sm:grid-cols-2">
            <div className="min-w-0">
              <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                Next Aspect
              </div>
              <div className="mt-1 text-[15px] leading-5 text-zinc-900" style={serifStyle}>{nextAspectLabel}</div>
              <div className="mt-1 text-[11px] text-zinc-500">{nextAspectMeta}</div>
            </div>
            <div className="min-w-0 sm:border-l sm:border-zinc-100 sm:pl-4">
              <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                Next Sign
              </div>
              <div className="mt-1 text-[15px] leading-5 text-zinc-900" style={serifStyle}>{nextSignLabel}</div>
              <div className="mt-1 text-[11px] text-zinc-500">{nextSignMeta}</div>
            </div>
          </div>
          <div className="border-t border-zinc-100 pt-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                Sign Progress
              </div>
              <div className="text-[11px] text-zinc-500">{signProgressLabel}</div>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-zinc-200">
              <div className="h-full bg-zinc-900" style={{ width: `${prog}%` }} />
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500">
              <span>{start}</span>
              <span>{next}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SavedSnapsTile({ snaps, loading, loaded, migrationReport, onRefresh, onLoad, onDelete }){
  const [mode, setMode] = useState('snaps'); // 'snaps' | 'search'
  const [q, setQ] = useState('');
  const [idxLoading, setIdxLoading] = useState(false);
  const [indexDocs, setIndexDocs] = useState(null); // [{ id, snap, text, title, subtitle }]
  const [actionBusy, setActionBusy] = useState(null); // id of snap being acted on
  const [correction, setCorrection] = useState(null);
  const [correctionNotice, setCorrectionNotice] = useState('');
  const searchRefreshRequestedRef = useRef(false);
  const correctionResolveSeqRef = useRef(0);
  const correctionResolveAbortRef = useRef(null);
  const correctionFormRevisionRef = useRef(0);
  const snapIdsKey = useMemo(
    () => (Array.isArray(snaps) ? snaps.map((snap) => String(snap?.id || '')).join('|') : ''),
    [snaps],
  );
  const migrationNotice = useMemo(() => {
    const safeSnaps = Array.isArray(snaps) ? snaps : [];
    const reviewCount = safeSnaps.filter((snap) => getSavedSnapReviewMessages(snap).some(
      (message) => !message.startsWith('A possible duplicate group'),
    )).length;
    const duplicateKeys = new Set(
      safeSnaps
        .map((snap) => firstPresent(
          snap?.duplicate_group?.semantic_key,
          snap?.duplicate_group?.canonical_id,
        ))
        .filter(Boolean),
    );
    const reportedDuplicateCount = Array.isArray(migrationReport?.semantic_duplicate_groups)
      ? migrationReport.semantic_duplicate_groups.length
      : 0;
    const duplicateCount = Math.max(duplicateKeys.size, reportedDuplicateCount);
    const migratedRecords = Number(migrationReport?.migrated_records);
    const parts = [];
    if (Number.isFinite(migratedRecords) && migratedRecords > 0) {
      parts.push(`${migratedRecords} saved ${migratedRecords === 1 ? 'chart was' : 'charts were'} upgraded.`);
    }
    if (reviewCount > 0) {
      parts.push(`${reviewCount} ${reviewCount === 1 ? 'chart needs' : 'charts need'} context review.`);
    }
    if (duplicateCount > 0) {
      parts.push(`${duplicateCount} possible duplicate ${duplicateCount === 1 ? 'group was' : 'groups were'} preserved.`);
    }
    if (migrationReport?.backup_path) {
      parts.push('A safety backup was preserved.');
    }
    return parts.join(' ');
  }, [migrationReport, snaps]);

  const handleLoad = async (snap) => {
    if (isSavedSnapReviewRequired(snap) || String(snap?.superseded_by || '').trim()) {
      setCorrectionNotice(
        String(snap?.superseded_by || '').trim()
          ? 'This original saved chart was superseded. Load its corrected copy instead.'
          : 'This saved chart must be corrected before it can be loaded.',
      );
      return;
    }
    try { setActionBusy(snap.id); await onLoad(snap); } catch (e) { /* no-op */ } finally { setActionBusy(null); }
  };
  const handleDelete = async (snap) => {
    const id = String(snap?.id || '');
    if (!id) return;
    const label = String(snap?.label || 'Untitled Snap').trim() || 'Untitled Snap';
    const message = `Delete “${label}”? The saved chart will be removed. Any corrected-copy relationship will be updated safely, and the migration recovery backup is retained.`;
    const confirmed = typeof window === 'undefined' || typeof window.confirm !== 'function'
      ? true
      : window.confirm(message);
    if (!confirmed) return;
    try {
      setActionBusy(id);
      await onDelete(id);
      setCorrection((current) => (
        String(current?.snap?.id || '') === id ? null : current
      ));
    } catch (e) {
      /* no-op */
    } finally {
      setActionBusy(null);
    }
  };
  const openCorrection = (snap) => {
    correctionResolveSeqRef.current += 1;
    correctionFormRevisionRef.current += 1;
    correctionResolveAbortRef.current?.abort();
    correctionResolveAbortRef.current = null;
    setCorrectionNotice('');
    setCorrection({
      snap,
      form: savedSnapCorrectionSeed(snap),
      locationResolution: {
        status: 'idle',
        location: '',
        latitude: null,
        longitude: null,
        timezone: '',
      },
      preview: null,
      ambiguity: null,
      busy: '',
      error: '',
    });
  };
  const updateCorrectionField = (field, value) => {
    correctionResolveSeqRef.current += 1;
    correctionFormRevisionRef.current += 1;
    correctionResolveAbortRef.current?.abort();
    correctionResolveAbortRef.current = null;
    setCorrection((current) => {
      if (!current) return current;
      const form = { ...current.form, [field]: value };
      let locationResolution = current.locationResolution;
      if (field === 'location') {
        form.latitude = '';
        form.longitude = '';
        locationResolution = {
          status: 'idle',
          location: '',
          latitude: null,
          longitude: null,
          timezone: '',
        };
      } else if (field === 'latitude' || field === 'longitude' || field === 'timezone') {
        locationResolution = {
          ...locationResolution,
          status: 'manual',
        };
      } else if (current.busy === 'resolve-location') {
        locationResolution = {
          ...locationResolution,
          status: 'idle',
        };
      }
      return {
        ...current,
        form,
        locationResolution,
        preview: null,
        ambiguity: null,
        busy: current.busy === 'resolve-location' ? '' : current.busy,
        error: '',
      };
    });
  };
  const resolveCorrectionLocation = async (formOverride = correction?.form || {}) => {
    const snapId = String(correction?.snap?.id || '');
    const query = String(formOverride.location || '').trim();
    if (!snapId || correction?.busy) return null;
    if (!query) {
      setCorrection((current) => current ? {
        ...current,
        error: 'Enter a specific city or place.',
      } : current);
      return null;
    }

    const requestSeq = correctionResolveSeqRef.current + 1;
    correctionResolveSeqRef.current = requestSeq;
    const formRevision = correctionFormRevisionRef.current;
    correctionResolveAbortRef.current?.abort();
    const controller = new AbortController();
    correctionResolveAbortRef.current = controller;
    setCorrection((current) => current ? {
      ...current,
      busy: 'resolve-location',
      preview: null,
      ambiguity: null,
      error: '',
      locationResolution: {
        ...current.locationResolution,
        status: 'loading',
      },
    } : current);

    try {
      const response = await AstroClockAPI.resolveTimezone(query, {
        requireSpecific: true,
        signal: controller.signal,
      });
      if (
        controller.signal.aborted
        || correctionResolveSeqRef.current !== requestSeq
        || correctionFormRevisionRef.current !== formRevision
      ) {
        return null;
      }
      const result = response?.data && typeof response.data === 'object'
        ? response.data
        : response;
      const latitude = Number(result?.latitude);
      const longitude = Number(result?.longitude);
      const timezone = resolveIntlTimezone(result?.timezone);
      const location = String(result?.location || query).trim();
      if (
        !location
        || !Number.isFinite(latitude)
        || latitude < -90
        || latitude > 90
        || !Number.isFinite(longitude)
        || longitude < -180
        || longitude > 180
        || !timezone
      ) {
        throw new Error('The place resolver did not return complete coordinates and timezone information.');
      }
      const resolvedForm = {
        ...formOverride,
        location,
        latitude: String(latitude),
        longitude: String(longitude),
        timezone,
      };
      setCorrection((current) => {
        if (
          !current
          || String(current.snap?.id || '') !== snapId
          || String(current.form?.location || '').trim() !== query
        ) {
          return current;
        }
        return {
          ...current,
          form: { ...current.form, ...resolvedForm },
          locationResolution: {
            status: 'resolved',
            location,
            latitude,
            longitude,
            timezone,
          },
          preview: null,
          ambiguity: null,
          busy: '',
          error: '',
        };
      });
      return resolvedForm;
    } catch (error) {
      if (
        controller.signal.aborted
        || correctionResolveSeqRef.current !== requestSeq
        || isAbortError(error)
      ) {
        return null;
      }
      setCorrection((current) => current ? {
        ...current,
        locationResolution: {
          ...current.locationResolution,
          status: 'error',
        },
        preview: null,
        ambiguity: null,
        busy: '',
        error: getActionErrorMessage(
          error,
          'Could not resolve that city. Enter a more specific place or use manual coordinates.',
        ),
      } : current);
      return null;
    } finally {
      if (correctionResolveAbortRef.current === controller) {
        correctionResolveAbortRef.current = null;
      }
    }
  };
  const correctionRequest = (formOverride = correction?.form || {}) => {
    const form = formOverride;
    const latitudeText = String(form.latitude ?? '').trim();
    const longitudeText = String(form.longitude ?? '').trim();
    const latitude = latitudeText ? Number(latitudeText) : Number.NaN;
    const longitude = longitudeText ? Number(longitudeText) : Number.NaN;
    const wallTime = normalizeLocalDateTimeInput(form.localDatetime);
    if (!wallTime) {
      throw new Error('Enter a complete, valid local date and time.');
    }
    if (!resolveIntlTimezone(form.timezone)) {
      throw new Error('Enter a valid IANA timezone, such as Asia/Jerusalem.');
    }
    if (!String(form.location || '').trim()) {
      throw new Error('Enter a specific city or place.');
    }
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
      throw new Error('Enter a valid latitude from -90 to 90.');
    }
    if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      throw new Error('Enter a valid longitude from -180 to 180.');
    }
    const selectedResolutionCandidate = correction?.ambiguity?.candidates?.find(
      (candidate) => candidate.key === correction.ambiguity.selectedKey,
    );
    if (correction?.ambiguity?.kind === 'ambiguous' && !selectedResolutionCandidate) {
      throw new Error('Choose which UTC offset applies to this repeated local time.');
    }
    return {
      localDatetime: selectedResolutionCandidate?.localDatetime || wallTime,
      timezone: String(form.timezone).trim(),
      location: String(form.location).trim(),
      latitude,
      longitude,
      houseSystem: form.houseSystem || 'R',
      includeModern: true,
      includeChiron: true,
    };
  };
  const previewCorrection = async () => {
    if (!correction?.snap?.id || correction.busy) return;
    let form = correction.form || {};
    const latitudeText = String(form.latitude ?? '').trim();
    const longitudeText = String(form.longitude ?? '').trim();
    const latitude = latitudeText ? Number(latitudeText) : Number.NaN;
    const longitude = longitudeText ? Number(longitudeText) : Number.NaN;
    const hasResolvedCoordinates = (
      Number.isFinite(latitude)
      && latitude >= -90
      && latitude <= 90
      && Number.isFinite(longitude)
      && longitude >= -180
      && longitude <= 180
    );
    const shouldResolveAutomatically = (
      correction.locationResolution?.status !== 'manual'
      && (!hasResolvedCoordinates || !resolveIntlTimezone(form.timezone))
    );
    if (shouldResolveAutomatically) {
      form = await resolveCorrectionLocation(form);
      if (!form) return;
    }
    let requestPayload;
    try {
      requestPayload = correctionRequest(form);
    } catch (error) {
      setCorrection((current) => current ? { ...current, error: error.message } : current);
      return;
    }
    setCorrection((current) => current ? { ...current, busy: 'preview', error: '' } : current);
    try {
      const res = await AstroClockAPI.confirmSnapContext(correction.snap.id, {
        ...requestPayload,
        persist: false,
      });
      const preview = res?.data?.replacement || res?.replacement;
      if (!preview) throw new Error('The corrected chart preview was not returned.');
      setCorrection((current) => current ? { ...current, preview, busy: '', error: '' } : current);
    } catch (error) {
      const resolution = extractLocalTimeResolution(error, requestPayload.localDatetime);
      setCorrection((current) => current ? {
        ...current,
        busy: '',
        preview: null,
        ambiguity: resolution?.kind === 'ambiguous'
          ? { ...resolution, selectedKey: '' }
          : null,
        error: resolution?.message
          || getActionErrorMessage(error, 'Failed to preview the corrected chart.'),
      } : current);
    }
  };
  const persistCorrection = async () => {
    if (!correction?.snap?.id || !correction?.preview || correction.busy) return;
    let requestPayload;
    try {
      requestPayload = correctionRequest();
    } catch (error) {
      setCorrection((current) => current ? { ...current, preview: null, error: error.message } : current);
      return;
    }
    setCorrection((current) => current ? { ...current, busy: 'persist', error: '' } : current);
    try {
      const res = await AstroClockAPI.confirmSnapContext(correction.snap.id, {
        ...requestPayload,
        persist: true,
      });
      if (res?.data?.original_preserved !== true) {
        throw new Error('The backend did not confirm that the original saved chart was preserved.');
      }
      await onRefresh?.({ silent: true });
      setCorrection(null);
    } catch (error) {
      setCorrection((current) => current ? {
        ...current,
        busy: '',
        error: getActionErrorMessage(error, 'Failed to save the corrected copy.'),
      } : current);
    }
  };

  useEffect(() => {
    return () => {
      correctionResolveSeqRef.current += 1;
      correctionResolveAbortRef.current?.abort();
      correctionResolveAbortRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (mode !== 'search') {
      searchRefreshRequestedRef.current = false;
      return;
    }
    if (loading || searchRefreshRequestedRef.current || typeof onRefresh !== 'function') return;
    if (!loaded || !Array.isArray(snaps) || snaps.length === 0) {
      searchRefreshRequestedRef.current = true;
      void onRefresh({ silent: true });
    }
  }, [loaded, loading, mode, onRefresh, snaps]);

  useEffect(() => {
    if (mode === 'search') setIndexDocs(null);
  }, [mode, snapIdsKey]);

  // Build index on demand when entering search
  useEffect(() => {
    let cancelled = false;
    const build = async () => {
      if (mode !== 'search' || indexDocs !== null || !Array.isArray(snaps) || snaps.length === 0) return;
      setIdxLoading(true);
      try {
        // Fetch full snap details concurrently with small batch size
        const ids = snaps.map(s => s.id);
        const batch = async (arr, size) => {
          const out = [];
          for (let i = 0; i < arr.length; i += size) {
            const group = arr.slice(i, i + size).map(async (id) => {
              try { const res = await AstroClockAPI.getSnap(id); return res?.snap; } catch { return null; }
            });
            const results = await Promise.all(group);
            out.push(...results.filter(Boolean));
            if (cancelled) break;
          }
          return out;
        };
        const fullSnaps = await batch(ids, 5);
        if (cancelled) return;
        const docs = fullSnaps.map((s) => {
          const dash = s?.dashboard || {};
          const parts = [];
          // Basic
          if (s?.label) parts.push(`label:${s.label}`);
          if (s?.location) parts.push(`loc:${s.location}`);
          if (s?.summary?.chart_sect) parts.push(`sect:${s.summary.chart_sect}`);
          if (s?.summary?.sect_light) parts.push(`light:${s.summary.sect_light}`);
          if (s?.summary?.hour_ruler) parts.push(`hour:${s.summary.hour_ruler}`);
          if (s?.summary?.moon_sign) parts.push(`moon:${s.summary.moon_sign}`);
          if (s?.summary?.certification) {
            parts.push(`certification ${s.summary.certification.status || ''} ${s.summary.certification.confidence || ''}`);
          }
          // Planets
          const planets = Array.isArray(dash.planets) ? dash.planets : [];
          planets.forEach(p => {
            const name = p.planet || p.name;
            const sign = p.sign || '';
            const house = (p.house != null) ? `H${p.house}` : '';
            parts.push(`${name} ${sign} ${house}`);
          });
          // Aspects
          const aspects = Array.isArray(dash.top_aspects) ? dash.top_aspects : [];
          const tight = dash.tightest_aspect ? [dash.tightest_aspect] : [];
          [...aspects, ...tight].forEach(a => {
            if (!a) return;
            const aName = (a.aspect || '').toString();
            const p1 = a.planet1 || '';
            const p2 = a.planet2 || '';
            parts.push(`${p1} ${aName} ${p2}`);
          });
          const text = parts.join(' ').toLowerCase();
          const title = s?.label || 'Untitled Snap';
          const subtitle = `${formatSavedSnapDateTime(s)} · ${getSavedSnapTimezoneLabel(s)} · ${s.location || '-'}`;
          return { id: s.id, snap: s, text, title, subtitle };
        });
        setIndexDocs(docs);
      } finally {
        if (!cancelled) setIdxLoading(false);
      }
    };
    build();
    return () => { cancelled = true; };
  }, [mode, indexDocs, snaps]);

  // Filter results
  const results = useMemo(() => {
    if (mode !== 'search' || !indexDocs) return [];
    const qq = (q || '').trim().toLowerCase();
    if (!qq) return indexDocs.slice(0, 50);
    const tokens = qq.split(/\s+/).filter(Boolean);
    return indexDocs.filter(doc => tokens.every(t => doc.text.includes(t))).slice(0, 100);
  }, [mode, indexDocs, q]);

  return (
    <div className={panelCls}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
            Reference Stack
          </div>
          <h3 className="mt-1 font-semibold text-sm">Saved Snaps</h3>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onRefresh} className={utilityPillCls} style={monoStyle}>Refresh</button>
          <button onClick={() => setMode(m => m === 'snaps' ? 'search' : 'snaps')} className={utilityPillCls} style={monoStyle}>{mode==='snaps' ? 'Search' : 'Snaps'}</button>
        </div>
      </div>

      <div className="mt-3">
      {migrationNotice ? (
        <div
          className={`mb-3 ${savedSnapNoticeCls}`}
          role="status"
        >
          <div className="text-[9px] font-semibold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
            Saved chart migration
          </div>
          <div className="mt-1 text-[12px] italic leading-5 text-zinc-500" style={serifStyle}>
            {migrationNotice}
          </div>
        </div>
      ) : null}
      {correctionNotice ? (
        <div
          className={`mb-3 ${savedSnapNoticeCls}`}
          role="status"
          style={serifStyle}
        >
          <span className="text-[12px] italic leading-5 text-zinc-500">{correctionNotice}</span>
        </div>
      ) : null}
      {correction ? (
        <div
          className="mb-3 rounded-2xl border border-zinc-200 bg-zinc-50/80 p-3"
          role="region"
          aria-label="Correct saved chart context"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
                Correct saved context
              </div>
              <div className="mt-1 text-sm font-semibold text-zinc-900">
                {correction.snap?.label || 'Saved chart'}
              </div>
            </div>
            <button
              type="button"
              className={utilityPillCls}
              onClick={() => {
                correctionResolveSeqRef.current += 1;
                correctionFormRevisionRef.current += 1;
                correctionResolveAbortRef.current?.abort();
                correctionResolveAbortRef.current = null;
                setCorrection(null);
              }}
              disabled={Boolean(correction.busy)}
            >
              Cancel
            </button>
          </div>
          <p className="mt-2 text-[12px] italic leading-5 text-zinc-500" style={serifStyle}>
            Confirm the original local civil time, IANA timezone, and exact birthplace.
            Preview recalculates the whole chart. Saving creates a corrected copy and preserves the original.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="text-[11px] font-medium text-zinc-700">
              Local date and time
              <input
                type="datetime-local"
                aria-label="Confirmed local date and time"
                className="mt-1 w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-sm text-zinc-900"
                value={correction.form.localDatetime}
                onChange={(event) => updateCorrectionField('localDatetime', event.target.value)}
              />
            </label>
            <label className="text-[11px] font-medium text-zinc-700">
              IANA timezone
              <input
                type="text"
                aria-label="Confirmed IANA timezone"
                placeholder="Asia/Jerusalem"
                className="mt-1 w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-sm text-zinc-900"
                value={correction.form.timezone}
                onChange={(event) => updateCorrectionField('timezone', event.target.value)}
              />
            </label>
            <div className="text-[11px] font-medium text-zinc-700 sm:col-span-2">
              <label>
                Specific city or place
                <input
                  type="text"
                  aria-label="Confirmed specific location"
                  placeholder="Jerusalem, Israel"
                  className="mt-1 w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-sm text-zinc-900"
                  value={correction.form.location}
                  onChange={(event) => updateCorrectionField('location', event.target.value)}
                />
              </label>
              <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] italic leading-4 text-zinc-500" style={serifStyle}>
                  Enter a city, not only a country. Preview resolves its coordinates and timezone automatically.
                </span>
                <button
                  type="button"
                  className={utilityPillCls}
                  onClick={() => { void resolveCorrectionLocation(); }}
                  disabled={Boolean(correction.busy) || !String(correction.form.location || '').trim()}
                >
                  {correction.busy === 'resolve-location' ? 'Resolving…' : 'Resolve city automatically'}
                </button>
              </div>
              {correction.locationResolution?.status === 'loading' ? (
                <div className="mt-2 text-[10px] font-normal text-zinc-500" role="status" style={monoStyle}>
                  Resolving city, coordinates, and timezone…
                </div>
              ) : null}
              {correction.locationResolution?.status === 'resolved' ? (
                <div className="mt-2 text-[10px] font-normal leading-4 text-zinc-600" role="status" style={monoStyle}>
                  Resolved automatically: {correction.locationResolution.location} ·{' '}
                  {correction.locationResolution.latitude.toFixed(5)},{' '}
                  {correction.locationResolution.longitude.toFixed(5)} ·{' '}
                  {correction.locationResolution.timezone}
                </div>
              ) : null}
              {correction.locationResolution?.status === 'manual' ? (
                <div className="mt-2 text-[10px] font-normal leading-4 text-zinc-500" role="status" style={monoStyle}>
                  Location details were adjusted manually. Resolve the city again to replace them automatically.
                </div>
              ) : null}
            </div>
            <label className="text-[11px] font-medium text-zinc-700">
              Latitude
              <input
                type="number"
                step="any"
                aria-label="Confirmed latitude"
                className="mt-1 w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-sm text-zinc-900"
                value={correction.form.latitude}
                onChange={(event) => updateCorrectionField('latitude', event.target.value)}
              />
            </label>
            <label className="text-[11px] font-medium text-zinc-700">
              Longitude
              <input
                type="number"
                step="any"
                aria-label="Confirmed longitude"
                className="mt-1 w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-sm text-zinc-900"
                value={correction.form.longitude}
                onChange={(event) => updateCorrectionField('longitude', event.target.value)}
              />
            </label>
            <label className="text-[11px] font-medium text-zinc-700 sm:col-span-2">
              House system for the corrected chart
              <select
                aria-label="Confirmed house system"
                className="mt-1 w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-sm text-zinc-900"
                value={correction.form.houseSystem}
                onChange={(event) => updateCorrectionField('houseSystem', event.target.value)}
              >
                {SNAP_CORRECTION_HOUSE_OPTIONS.map((option) => (
                  <option key={option.code} value={option.code}>
                    {option.label} ({option.code})
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-[11px] italic leading-4 text-zinc-500" style={serifStyle}>
                This changes recalculated houses and angles. It does not change astrocartography world-map line geometry.
              </span>
            </label>
          </div>
          {correction.ambiguity?.kind === 'ambiguous' ? (
            <div className="mt-3">
              <LocalTimeAmbiguityChoice
                resolution={correction.ambiguity}
                selectedKey={correction.ambiguity.selectedKey}
                ariaLabel="Choose corrected chart UTC offset"
                onSelect={(selectedKey) => {
                  setCorrection((current) => current ? {
                    ...current,
                    ambiguity: { ...current.ambiguity, selectedKey },
                    preview: null,
                    error: '',
                  } : current);
                }}
              />
            </div>
          ) : null}
          {correction.error ? (
            <p
              className="mt-3 rounded-lg border border-red-100 bg-red-50/60 px-2.5 py-2 text-[10px] leading-5 text-red-700"
              role="alert"
              style={monoStyle}
            >
              {correction.error}
            </p>
          ) : null}
          {correction.preview ? (
            <div className="mt-3 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-[10px] leading-5 text-zinc-600" style={monoStyle}>
              <div className="font-semibold uppercase tracking-[0.12em] text-zinc-700">Corrected chart preview ready</div>
              <div>
                {formatSavedSnapDateTime(correction.preview)} · {getSavedSnapTimezoneLabel(correction.preview)}
              </div>
              <div>
                {correction.preview.location} · {Number(correction.preview.latitude).toFixed(5)}, {Number(correction.preview.longitude).toFixed(5)}
              </div>
              <div className="text-zinc-500">
                Planets, houses, and angles were recalculated together. The original remains unchanged.
              </div>
            </div>
          ) : null}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={utilityPillCls}
              onClick={previewCorrection}
              disabled={Boolean(correction.busy)}
            >
              {correction.busy === 'resolve-location'
                ? 'Resolving city…'
                : correction.busy === 'preview'
                  ? 'Previewing…'
                  : 'Preview corrected chart'}
            </button>
            {correction.preview ? (
              <button
                type="button"
                className="rounded-full bg-zinc-900 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white disabled:bg-zinc-300"
                onClick={persistCorrection}
                disabled={Boolean(correction.busy)}
              >
                {correction.busy === 'persist' ? 'Saving…' : 'Save corrected copy'}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
      {mode === 'snaps' ? (
        loading ? (
          <div className="text-sm text-zinc-500">Loading…</div>
        ) : !loaded ? (
          <div className="text-sm text-zinc-500">Saved snaps are not loaded yet. Click Refresh when you need them.</div>
        ) : (snaps?.length || 0) === 0 ? (
          <div className="text-sm text-zinc-500">No snaps yet</div>
        ) : (
          <div className="space-y-2 max-h-72 overflow-auto pr-1">
            {snaps.map((s)=> {
              const certificationSummary = s.summary?.certification;
              const certificationLabel = certificationSummary?.status
                ? String(certificationSummary.status).replace(/_/g, ' ')
                : '';
              const reviewMessages = getSavedSnapReviewMessages(s);
              const needsContextReview = reviewMessages.some(
                (message) => !message.startsWith('A possible duplicate group'),
              );
              const supersededBy = String(s?.superseded_by || '').trim();
              const correctedReplacement = supersededBy
                ? (Array.isArray(snaps) ? snaps : []).find(
                  (candidate) => String(candidate?.id || '') === supersededBy,
                )
                : null;
              return (
              <div key={s.id} className="rounded-2xl border border-zinc-100 bg-white px-3 py-2.5 flex items-center justify-between gap-3">
                <div className="min-w-0 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-zinc-900">{s.label || 'Untitled Snap'}</span>
                    {certificationSummary ? (
                      <span className="rounded-full border border-sky-100 bg-sky-50 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-sky-700" style={monoStyle}>
                        Certification{certificationLabel ? ` · ${certificationLabel}` : ''}
                      </span>
                    ) : null}
                    {needsContextReview ? (
                      <span className={savedSnapContextBadgeCls} style={monoStyle}>
                        Review saved context
                      </span>
                    ) : null}
                    {s?.duplicate_group ? (
                      <span className={savedSnapContextBadgeCls} style={monoStyle}>
                        Possible duplicate
                      </span>
                    ) : null}
                    {supersededBy ? (
                      <span className={savedSnapContextBadgeCls} style={monoStyle}>
                        Superseded—use corrected copy
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-1 text-[11px] text-zinc-600">
                    {formatSavedSnapDateTime(s)} · {getSavedSnapTimezoneLabel(s)} · {s.location || '-'}
                  </div>
                  {reviewMessages.length > 0 ? (
                    <div className={savedSnapRemarkCls} style={serifStyle}>
                      {reviewMessages.join(' ')}
                    </div>
                  ) : null}
                  {supersededBy ? (
                    <div className={savedSnapRemarkCls} style={serifStyle}>
                      This original is retained for history and cannot be loaded as the active chart.
                    </div>
                  ) : null}
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500">
                    <span>Hour: {s.summary?.hour_ruler || '-'}</span>
                    <span>Moon: {s.summary?.moon_sign || '-'}</span>
                    <span>Sect: {(() => {
                      const snapSect = normalizeSectValue(s.summary?.chart_sect);
                      return snapSect ? (snapSect === 'diurnal' ? 'Day' : 'Night') : '-';
                    })()}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {needsContextReview && !supersededBy ? (
                    <button
                      disabled={actionBusy===s.id}
                      className={`${utilityPillCls} disabled:opacity-50`}
                      style={monoStyle}
                      onClick={() => openCorrection(s)}
                    >
                      Correct context
                    </button>
                  ) : null}
                  {correctedReplacement ? (
                    <button
                      disabled={Boolean(actionBusy)}
                      className={`${utilityPillCls} disabled:opacity-50`}
                      style={monoStyle}
                      onClick={() => handleLoad(correctedReplacement)}
                    >
                      Load corrected copy
                    </button>
                  ) : null}
                  <button
                    disabled={actionBusy===s.id || Boolean(supersededBy) || needsContextReview}
                    className={`${utilityPillCls} disabled:opacity-50`}
                    style={monoStyle}
                    title={
                      supersededBy
                        ? 'Use the corrected copy instead.'
                        : (needsContextReview ? 'Correct this saved context before loading it.' : undefined)
                    }
                    onClick={()=> handleLoad(s)}
                  >
                    {actionBusy===s.id ? '…' : 'Load'}
                  </button>
                  <button disabled={actionBusy===s.id} className={`${utilityPillCls} disabled:opacity-50`} style={monoStyle} onClick={()=> handleDelete(s)}>{actionBusy===s.id? '…':'Delete'}</button>
                </div>
              </div>
            );})}
          </div>
        )
      ) : (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search label, planet (e.g., Sun Leo H10), or aspect (e.g., Moon trine Venus)" className="w-full rounded-full border border-zinc-200 px-3 py-2 text-[12px] text-zinc-700 placeholder:text-zinc-400" />
            <button className={utilityPillCls} style={monoStyle} onClick={()=>setQ('')}>Clear</button>
          </div>
          {(loading || idxLoading) ? (
            <div className="text-sm text-zinc-500">{loading ? 'Loading snaps…' : 'Building index…'}</div>
          ) : (!indexDocs || indexDocs.length === 0) ? (
            <div className="text-sm text-zinc-500">No snaps to search</div>
          ) : results.length === 0 ? (
            <div className="text-sm text-zinc-500">No matches</div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-auto pr-1">
              {results.map((doc) => {
                const snap = doc.snap || {};
                const reviewMessages = getSavedSnapReviewMessages(snap);
                const needsContextReview = reviewMessages.some(
                  (message) => !message.startsWith('A possible duplicate group'),
                );
                const supersededBy = String(snap?.superseded_by || '').trim();
                const correctedReplacement = supersededBy
                  ? (Array.isArray(snaps) ? snaps : []).find(
                    (candidate) => String(candidate?.id || '') === supersededBy,
                  )
                  : null;
                return (
                  <div key={doc.id} className="rounded-2xl border border-zinc-100 bg-white px-3 py-2.5 flex items-center justify-between gap-3">
                    <div className="min-w-0 text-sm">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-zinc-900">{doc.title}</span>
                        {needsContextReview ? (
                          <span className={savedSnapContextBadgeCls} style={monoStyle}>
                            Review saved context
                          </span>
                        ) : null}
                        {snap?.duplicate_group ? (
                          <span className={savedSnapContextBadgeCls} style={monoStyle}>
                            Possible duplicate
                          </span>
                        ) : null}
                        {supersededBy ? (
                          <span className={savedSnapContextBadgeCls} style={monoStyle}>
                            Superseded—use corrected copy
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-1 text-[11px] text-zinc-600">{doc.subtitle}</div>
                      {reviewMessages.length > 0 ? (
                        <div className={savedSnapRemarkCls} style={serifStyle}>
                          {reviewMessages.join(' ')}
                        </div>
                      ) : null}
                      {supersededBy ? (
                        <div className={savedSnapRemarkCls} style={serifStyle}>
                          This original is retained for history and cannot be loaded as the active chart.
                        </div>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      {needsContextReview && !supersededBy ? (
                        <button
                          disabled={actionBusy===doc.id}
                          className={`${utilityPillCls} disabled:opacity-50`}
                          style={monoStyle}
                          onClick={() => openCorrection(snap)}
                        >
                          Correct context
                        </button>
                      ) : null}
                      {correctedReplacement ? (
                        <button
                          disabled={Boolean(actionBusy)}
                          className={`${utilityPillCls} disabled:opacity-50`}
                          style={monoStyle}
                          onClick={() => handleLoad(correctedReplacement)}
                        >
                          Load corrected copy
                        </button>
                      ) : null}
                      <button
                        disabled={actionBusy===doc.id || Boolean(supersededBy) || needsContextReview}
                        className={`${utilityPillCls} disabled:opacity-50`}
                        style={monoStyle}
                        title={
                          supersededBy
                            ? 'Use the corrected copy instead.'
                            : (needsContextReview ? 'Correct this saved context before loading it.' : undefined)
                        }
                        onClick={()=> handleLoad(snap)}
                      >
                        {actionBusy===doc.id? '…':'Load'}
                      </button>
                      <button disabled={actionBusy===doc.id} className={`${utilityPillCls} disabled:opacity-50`} style={monoStyle} onClick={()=> handleDelete(snap)}>{actionBusy===doc.id? '…':'Delete'}</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
      </div>
    </div>
  );
}

function CurrentAspectCard({ data, onOpenAnalysis, useMorin, setUseMorin }){
  const listStandard = (data?.planetary_aspects_precise && data.planetary_aspects_precise.length > 0)
    ? data.planetary_aspects_precise.slice(0,4)
    : (data?.top_aspects && data.top_aspects.length > 0)
    ? data.top_aspects.slice(0,4)
    : (data?.tightest_aspect ? [data.tightest_aspect] : []);
  const getMaxOrb = (name) => {
    const key = (name||'').toLowerCase();
    // Declination aspects (parallel / antiparallel) use much tighter orb by default
    if (key.includes('parallel')) return 1; // 1° default for declination parallels
    if (key.includes('conj')) return 8;
    if (key.includes('opp')) return 8;
    if (key.includes('square')) return 8;
    if (key.includes('trine')) return 8;
    if (key.includes('sext')) return 6;
    if (key.includes('semi') && key.includes('sext')) return 3; // semi-sextile (tighter window)
    if (key.includes('quin')) return 4; // quincunx
    return 6;
  };
  const [useDecl, setUseDecl] = useState(false);
  const [phaseFilter, setPhaseFilter] = useState('any');
  const declList = (data?.top_declinations || []).slice(0,4);
  const morinAntiList = (data?.morin_antiscia || []).slice(0,4);
  const morinList = Array.isArray(data?.morin_aspects) ? data.morin_aspects.slice(0,4) : [];
  const aspects = useDecl ? (useMorin ? morinAntiList : declList) : (useMorin ? morinList : listStandard);
  const scopeLabel = useDecl
    ? (useMorin ? 'Antiscia (Morin)' : 'Declination (∥ / antiparallel)')
    : (useMorin ? 'Morin Aspects' : 'Current Aspects');
  const filteredAspects = aspects.filter((row) => {
    if (phaseFilter === 'any') return true;
    return String(row?.phase || '').toLowerCase() === phaseFilter;
  });
  const getTone = (name) => {
    const key = String(name || '').toLowerCase();
    if (key.includes('trine') || key.includes('sext') || key.includes('parallel')) {
      return { accent: 'text-emerald-700', bar: 'bg-emerald-600' };
    }
    if (key.includes('square') || key.includes('opp') || key.includes('anti')) {
      return { accent: 'text-rose-700', bar: 'bg-rose-500' };
    }
    return { accent: 'text-zinc-900', bar: 'bg-zinc-900' };
  };
  const getExactnessPct = (row) => {
    const max = Number(row?.max_orb ?? getMaxOrb(row?.aspect));
    const orb = Math.abs(Number(row?.orb || 0));
    if (!Number.isFinite(max) || max <= 0) return 0;
    return Math.max(0, Math.min(100, Math.round((1 - (orb / max)) * 100)));
  };
  const formatMeta = (row) => {
    const pieces = [`orb ${row?.orb_text || `${Math.abs(Number(row?.orb || 0)).toFixed(2)}°`}`];
    if (row?.phase) pieces.push(String(row.phase));
    if (useMorin && row?.partile) {
      pieces.push('partile');
    } else if (useMorin && row?.complete_platic) {
      pieces.push('platic');
    }
    if (useMorin && row?.direction) pieces.push(String(row.direction));
    return pieces.join(' · ');
  };
  return (
    <div
      data-testid="current-aspects-card"
      role="region"
      aria-label={`Live Signal · ${scopeLabel}`}
      className={`${panelCls} aspect-square flex flex-col overflow-hidden`}
    >
      <h3 className={tileEyebrowCls} style={monoStyle}>Live Signal</h3>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {['any', 'applying', 'separating'].map((filterKey) => (
          <button
            key={filterKey}
            type="button"
            className={`rounded-full border px-2 py-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] ${
              phaseFilter === filterKey
                ? 'border-zinc-900 bg-zinc-900 text-white'
                : 'border-zinc-200 bg-white text-zinc-500'
            }`}
            style={monoStyle}
            onClick={() => setPhaseFilter(filterKey)}
          >
            {filterKey}
          </button>
        ))}
      </div>
      <div className="mt-1.5 text-[9px] text-zinc-500">
        {filteredAspects.length} active{phaseFilter !== 'any' ? ` · ${phaseFilter}` : ''}
      </div>
      {filteredAspects.length === 0 ? (
        <div className="mt-3 min-h-0 flex-1 text-sm text-zinc-500">
          No aspects in this scope.
        </div>
      ) : (
        <div className="astro-scroll-shell mt-2 min-h-0 flex-1">
          <div data-testid="current-aspects-scroll" className="astro-scroll min-h-0 flex-1 pr-1">
            <div className="space-y-0 pb-2">
              {filteredAspects.map((a, idx) => {
                const percent = getExactnessPct(a);
                const tone = getTone(a?.aspect);
                return (
                  <div key={idx} className="border-b border-zinc-100 py-2 first:pt-0 last:border-b-0 last:pb-0">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className={`truncate text-[13px] font-medium ${tone.accent}`} style={serifStyle}>
                          {a.planet1} {a.symbol || ''} {a.planet2}
                        </div>
                        <div className="mt-0.5 text-[9px] leading-4 text-zinc-500">
                          {formatMeta(a)}
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <div className="text-[1rem] leading-none tracking-[-0.03em] text-zinc-900" style={serifStyle}>
                          {percent}
                          <span className="ml-0.5 text-[0.6rem] text-zinc-400">%</span>
                        </div>
                        <div className="mt-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>
                          Exactness
                        </div>
                      </div>
                    </div>
                    <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-zinc-200">
                      <div className={`h-full ${tone.bar}`} style={{ width: `${percent}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
      <div
        data-testid="current-aspects-footer"
        className="mt-2 flex shrink-0 items-center justify-between gap-3 border-t border-zinc-100 pt-2"
      >
        <div className="flex flex-wrap items-center gap-3 text-[11px] text-zinc-600">
          <label className="inline-flex cursor-pointer select-none items-center gap-1.5">
            <span>Morin</span>
            <span className="relative inline-flex items-center">
              <input data-testid="current-aspects-morin-toggle" type="checkbox" className="sr-only peer" checked={useMorin} onChange={()=> { setUseMorin(v=>!v); }} />
              <span className="h-5 w-10 rounded-full bg-zinc-300 transition-colors peer-checked:bg-zinc-800 peer-focus-visible:ring-2 peer-focus-visible:ring-zinc-400 peer-focus-visible:ring-offset-2"></span>
              <span className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform peer-checked:translate-x-5"></span>
            </span>
          </label>
          <label className="inline-flex cursor-pointer select-none items-center gap-1.5">
            <span>Decl</span>
            <span className="relative inline-flex items-center">
              <input data-testid="current-aspects-decl-toggle" type="checkbox" className="sr-only peer" checked={useDecl} onChange={()=> { setUseDecl(v=>!v); }} />
              <span className="h-5 w-10 rounded-full bg-zinc-300 transition-colors peer-checked:bg-zinc-800 peer-focus-visible:ring-2 peer-focus-visible:ring-zinc-400 peer-focus-visible:ring-offset-2"></span>
              <span className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform peer-checked:translate-x-5"></span>
            </span>
          </label>
        </div>
        <button type="button" onClick={onOpenAnalysis}
                className="shrink-0 rounded border border-zinc-300 bg-white/80 px-2 py-0.5 text-[10px] hover:bg-white/90"
                title="Open comprehensive aspect analysis">More</button>
      </div>
    </div>
  );
}

function PositionsDignityCard({ data }){
  const [sort, setSort] = useState('score');
  const rows = (data?.planets||[]).slice().sort((a,b)=>{
    if (sort==='lon') return (a.longitude||0)-(b.longitude||0);
    const sa = Number(a.dignity_score)||0; const sb = Number(b.dignity_score)||0; return sb-sa;
  });
  const norm = (score)=> Math.max(-5, Math.min(5, Number(score)||0));
  const knobLeft = (score)=> `calc( ${( (norm(score) - (-5)) / 10 ) * 100}% - 8px )`;
  return (
    <div className={`${panelCls} aspect-square`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
            Planet Positions
          </div>
          <h3 className="mt-1 font-semibold text-sm">Positions + Dignity</h3>
        </div>
        <div className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-white p-1 text-[10px]" style={monoStyle}>
          <button
            onClick={()=>setSort('score')}
            className={`rounded-full px-2.5 py-0.5 font-semibold uppercase tracking-[0.1em] ${
              sort==='score' ? 'bg-zinc-900 text-white' : 'text-zinc-500'
            }`}
          >
            Score
          </button>
          <button
            onClick={()=>setSort('lon')}
            className={`rounded-full px-2.5 py-0.5 font-semibold uppercase tracking-[0.1em] ${
              sort==='lon' ? 'bg-zinc-900 text-white' : 'text-zinc-500'
            }`}
          >
            Longitude
          </button>
        </div>
      </div>
      <div className="mt-3 overflow-auto h-[calc(100%-56px)] pr-1">
        <div className="space-y-2">
          {rows.map((p, idx)=>{
            const s = Number(p.dignity_score)||0;
            const sign = p.sign || signFromLon(p.longitude);
            return (
              <div key={idx} className="rounded-2xl border border-zinc-100 bg-white px-3 py-2.5">
                <div className="flex items-center gap-3">
                  <div className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-zinc-200 bg-white text-[17px] leading-none">
                    {PlanetSymbols[p.planet] || '·'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="truncate text-[13px] font-medium text-zinc-900">{p.planet}</span>
                      {p.retrograde ? (
                        <span className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
                          Retrograde
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-0.5 text-[12px] text-zinc-600">
                      <span className="text-zinc-900" style={serifStyle}>
                        {degreeTextFromLon(p.longitude)} {sign}
                      </span>
                      <span className="mx-1 text-zinc-300">·</span>
                      <span>H{p.house ?? '-'}</span>
                    </div>
                    <div className="mt-2 relative h-1.5 rounded-full" style={{ background: 'linear-gradient(90deg, #fecdd3, #e5e7eb 50%, #bbf7d0)' }}>
                      <div className="absolute inset-y-0 left-1/2 w-px bg-zinc-400/70" />
                      <div className="absolute -top-1.5 h-4 w-4 rounded-full border border-zinc-800/20 bg-white shadow-sm" style={{ left: knobLeft(s) }} />
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className={`text-[1.05rem] leading-none ${s>=0?'text-emerald-700':'text-rose-700'}`} style={serifStyle}>
                      {s>=0? '+':''}{s}
                    </div>
                    <div className="mt-1 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>
                      Score
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
