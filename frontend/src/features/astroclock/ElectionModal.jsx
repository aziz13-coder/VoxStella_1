import React, { useEffect, useMemo, useState } from 'react';
import { AstroClockAPI } from './api.mjs';
import { shouldIgnoreElectionStreamError } from './electionStreamState.mjs';

const ALL_WEEKDAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
export const MARRIAGE_ALPHA_DESCRIPTION =
  'Alpha keeps the original wedding election path and can optionally layer one natal snap.';
export const MARRIAGE_BETA_DESCRIPTION =
  'Beta uses the separate event-plus-two-participant marriage path and requires chart A plus chart B.';
export const MARRIAGE_BETA_PARTICIPANT_HELP =
  'Beta uses two charts saved in Astro Clock. Chart A is participant 1 and chart B is participant 2.';
export const BUSINESS_ALPHA_DESCRIPTION =
  'Alpha keeps the current business election path and can optionally layer one natal snap.';
export const BUSINESS_BETA_DESCRIPTION =
  'Beta scans one event line plus one founder-owner fit line per selected saved chart and keeps those lines separate in the result.';
export const BUSINESS_BETA_PARTICIPANT_HELP =
  'Beta uses one or more saved charts from Astro Clock as founder or owner charts. It scores the event chart first, then checks founder fit for each selected chart. In this beta path the selected charts are treated as certified, so Ascendant-based founder fit stays active.';
export const ESTATE_DESCRIPTION =
  'Estate scans one event line plus one buyer or seller fit line from a selected saved chart, with separate buy and sell direction rules.';
export const ESTATE_PARTICIPANT_HELP =
  'Estate uses one saved Astro Clock chart as the buyer or seller chart. The scan scores the property event first, then checks the selected chart against the event Moon, Ascendant, Fortuna, and property set.';
export const LUNAR_FERTILITY_DESCRIPTION =
  'Lunar Fertility Windows scans natal Sun-Moon phase returns as hourly fertility windows with phase, antiphase, and Moon-sign polarity labels.';

function sanitizeWeightedElectionTagDisplay(tag) {
  const text = String(tag || '').trim();
  if (!text) return '';
  return text
    .replace(/\s*\(([+-]?\d+(?:\.\d+)?)\)\s*$/u, '')
    .replace(/\s+[+-]\d+(?:\.\d+)?\s*$/u, '')
    .trim();
}

function sanitizeWeightedElectionRow(row) {
  if (!row || typeof row !== 'object') return row;
  const mapTagList = (items) => (
    Array.isArray(items)
      ? items.map(sanitizeWeightedElectionTagDisplay).filter(Boolean)
      : items
  );
  return {
    ...row,
    tags: mapTagList(row.tags),
    pros: mapTagList(row.pros),
    cautions: mapTagList(row.cautions),
    lines: Array.isArray(row.lines)
      ? row.lines.map((line) => ({
          ...line,
          tags: mapTagList(line?.tags),
          pros: mapTagList(line?.pros),
          cautions: mapTagList(line?.cautions),
        }))
      : row.lines,
  };
}

export function sanitizeMarriageBetaTagDisplay(tag) {
  return sanitizeWeightedElectionTagDisplay(tag);
}

export function sanitizeBusinessBetaTagDisplay(tag) {
  return sanitizeWeightedElectionTagDisplay(tag);
}

export function sanitizeEstateTagDisplay(tag) {
  return sanitizeWeightedElectionTagDisplay(tag);
}

export function sanitizeMarriageBetaElectionRow(row) {
  return sanitizeWeightedElectionRow(row);
}

export function sanitizeBusinessBetaElectionRow(row) {
  return sanitizeWeightedElectionRow(row);
}

export function sanitizeEstateElectionRow(row) {
  return sanitizeWeightedElectionRow(row);
}

export function buildBusinessBetaLineOptions({
  snaps = [],
  participantSnapIds = [],
  participantItems = [],
} = {}) {
  const options = [{ id: 'event', label: 'Event line', kind: 'event' }];
  const items = Array.isArray(participantItems) && participantItems.length
    ? participantItems
    : (Array.isArray(participantSnapIds) ? participantSnapIds.map((snapId, index) => {
        const snap = Array.isArray(snaps) ? snaps.find((item) => String(item?.id || '') === String(snapId || '')) : null;
        return {
          snap_id: snapId,
          label: String(snap?.label || '').trim() || String(snap?.location || '').trim() || `Founder ${index + 1}`,
        };
      }) : []);
  items.forEach((item, index) => {
    options.push({
      id: `participant:${index + 1}`,
      label: String(item?.label || '').trim() || `Founder ${index + 1}`,
      kind: 'participant',
    });
  });
  return options;
}

export function buildEstateLineOptions({
  snaps = [],
  estateParticipantSnapId = '',
  participantItems = [],
} = {}) {
  const options = [{ id: 'event', label: 'Event line', kind: 'event' }];
  const item = Array.isArray(participantItems) && participantItems.length
    ? participantItems[0]
    : (() => {
        const snap = Array.isArray(snaps) ? snaps.find((row) => String(row?.id || '') === String(estateParticipantSnapId || '')) : null;
        return estateParticipantSnapId
          ? {
              snap_id: estateParticipantSnapId,
              label: String(snap?.label || '').trim() || String(snap?.location || '').trim() || 'Estate participant',
            }
          : null;
      })();
  if (item) {
    options.push({
      id: 'participant:1',
      label: String(item?.label || '').trim() || 'Estate participant',
      kind: 'participant',
    });
  }
  return options;
}

const PlanetSymbols = {
  Sun: '☉',
  Moon: '☾',
  Mercury: '☿',
  Venus: '♀',
  Mars: '♂',
  Jupiter: '♃',
  Saturn: '♄',
};

function buildIso(d, t) {
  if (!d || !t) return null;
  return `${d}T${t}:00`;
}

function formatTs(iso, tz) {
  try {
    const d = new Date(iso);
    const opts = {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
      hour12: false,
      hourCycle: 'h23'
    };
    if (tz) opts.timeZone = tz;
    return new Intl.DateTimeFormat('en-GB', opts).format(d);
  } catch {
    return String(iso || '');
  }
}

function formatShortTs(iso, tz) {
  try {
    const d = new Date(iso);
    const opts = {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      hourCycle: 'h23'
    };
    if (tz) opts.timeZone = tz;
    return new Intl.DateTimeFormat('en-GB', opts).format(d);
  } catch {
    return String(iso || '');
  }
}

function formatSavedSnapLabel(snap) {
  if (!snap || typeof snap !== 'object') return 'Saved chart';
  const label = String(snap.label || '').trim();
  const timezone = snap?.dashboard?.timezone || undefined;
  const when = snap.effective_datetime ? formatShortTs(snap.effective_datetime, timezone) : '';
  const location = String(snap.location || '').trim();
  return [label, when, location].filter(Boolean).join(' | ') || String(snap.id || 'Saved chart');
}

function normalizeElectionSeriesRows(rows) {
  if (!Array.isArray(rows)) return [];
  return rows
    .filter((row) => row && Number.isFinite(Number(row.score)) && (row.timestamp_local || row.timestamp))
    .slice()
    .sort((a, b) => new Date(a.timestamp || a.timestamp_local).getTime() - new Date(b.timestamp || b.timestamp_local).getTime());
}

export function parseElectionClockValue(value) {
  if (value == null) return null;
  const text = String(value).trim();
  if (!text) return null;
  if (/^\d{1,2}$/.test(text)) {
    const hour = Number(text);
    return Number.isInteger(hour) && hour >= 0 && hour <= 23 ? (hour * 60) : null;
  }
  const match = text.match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return null;
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (!Number.isInteger(hour) || !Number.isInteger(minute)) return null;
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null;
  return (hour * 60) + minute;
}

export function mergeElectionTimelineRows(seriesRows, topRows) {
  const merged = new Map();
  normalizeElectionSeriesRows([...(seriesRows || []), ...(topRows || [])]).forEach((row) => {
    const key = row.timestamp || row.timestamp_local;
    if (!key) return;
    const existing = merged.get(key);
    if (!existing) {
      merged.set(key, row);
      return;
    }
    const next = { ...existing, ...row };
    if (!Array.isArray(next.tags) && Array.isArray(existing.tags)) next.tags = existing.tags;
    if (!Array.isArray(next.pros) && Array.isArray(existing.pros)) next.pros = existing.pros;
    if (!Array.isArray(next.cautions) && Array.isArray(existing.cautions)) next.cautions = existing.cautions;
    merged.set(key, next);
  });
  return Array.from(merged.values()).sort(
    (a, b) => new Date(a.timestamp || a.timestamp_local).getTime() - new Date(b.timestamp || b.timestamp_local).getTime(),
  );
}

function compressElectionSeriesRows(rows, maxPoints = 180) {
  if (!Array.isArray(rows) || rows.length <= maxPoints) return rows || [];
  const chunkSize = Math.ceil(rows.length / maxPoints);
  const compressed = [];
  for (let i = 0; i < rows.length; i += chunkSize) {
    const chunk = rows.slice(i, i + chunkSize);
    if (!chunk.length) continue;
    const representative = chunk.slice().sort((a, b) => Number(b.score || 0) - Number(a.score || 0))[0] || chunk[0];
    compressed.push(representative);
  }
  return compressed;
}

function pickElectionPeakRows(rows, stepMinutes = 60, limit = 4) {
  if (!Array.isArray(rows) || !rows.length) return [];
  const minSpacingMs = Math.max(60, Number(stepMinutes) || 60) * 60 * 1000 * 4;
  const ranked = rows.slice().sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  const chosen = [];
  for (const row of ranked) {
    const ts = new Date(row.timestamp || row.timestamp_local).getTime();
    if (!Number.isFinite(ts)) continue;
    const farEnough = chosen.every((existing) => {
      const ets = new Date(existing.timestamp || existing.timestamp_local).getTime();
      return Math.abs(ts - ets) >= minSpacingMs;
    });
    if (!farEnough) continue;
    chosen.push(row);
    if (chosen.length >= limit) break;
  }
  return chosen;
}

function escapeReportHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function reportCell(value, fallback = '-') {
  const text = String(value ?? '').trim();
  return escapeReportHtml(text || fallback);
}

function reportTime(value, timezone) {
  return value ? formatTs(value, timezone) : '-';
}

function reportShortTime(value, timezone) {
  return value ? formatShortTs(value, timezone) : '-';
}

function reportStrengthBar(score) {
  const value = Math.max(0, Math.min(100, Number(score) || 0));
  const filled = Math.max(1, Math.round(value / 10));
  return `${'#'.repeat(filled)}${'-'.repeat(Math.max(0, 10 - filled))}`;
}

function reportModeLabel(mode) {
  if (mode === 'phase') return 'Phase';
  if (mode === 'antiphase') return 'Antiphase';
  return 'Phase + Antiphase';
}

function reportSexPhase(row) {
  const sex = String(row?.sex_label || 'unknown').trim() || 'unknown';
  const phase = row?.phase_kind === 'antiphase' ? 'antiphase' : row?.phase_kind === 'phase' ? 'phase' : 'unknown';
  return `${sex}, ${phase}`;
}

function fertilityReportRows(rows) {
  return normalizeElectionSeriesRows(rows)
    .filter((row) => Number(row?.score || 0) > 0);
}

export function buildLunarFertilityReportDefaultPath(context = {}) {
  const stamp = String(context?.generatedAt || new Date().toISOString()).slice(0, 10) || 'report';
  return `LunarFertilityReport_${stamp}.pdf`;
}

export function buildLunarFertilityReportHtml({
  result,
  topRows = [],
  seriesRows = [],
  periods = [],
  context = {},
} = {}) {
  if (!result || result.matter !== 'lunar_fertility') {
    throw new Error('Lunar fertility report can only be built for Lunar Fertility Windows results.');
  }

  const timezoneName = result.timezone || context.timezone || '';
  const rows = fertilityReportRows(seriesRows.length ? seriesRows : (result.series || []));
  const rankedTop = normalizeElectionSeriesRows(topRows.length ? topRows : (result.top || []))
    .slice()
    .sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  const periodRows = Array.isArray(periods) ? periods : [];
  const level = Math.max(0, Math.min(100, Number(result.level_percent ?? context.levelPercent ?? 33) || 0));
  const generatedAt = context.generatedAt || new Date().toISOString();
  const firstRow = rows[0] || rankedTop[0] || null;
  const lastRow = rows[rows.length - 1] || rankedTop[rankedTop.length - 1] || null;
  const natalSnap = context.natalSnap && typeof context.natalSnap === 'object' ? context.natalSnap : {};
  const natalDashboard = natalSnap.dashboard && typeof natalSnap.dashboard === 'object' ? natalSnap.dashboard : {};
  const natalLat = natalSnap.latitude ?? natalDashboard.latitude;
  const natalLon = natalSnap.longitude ?? natalDashboard.longitude;
  const natalCoords = natalLat != null && natalLon != null
    ? `${Number(natalLat).toFixed(4)}, ${Number(natalLon).toFixed(4)}`
    : '';
  const forecastLat = result.latitude ?? context.latitude;
  const forecastLon = result.longitude ?? context.longitude;
  const forecastCoords = forecastLat != null && forecastLon != null
    ? `${Number(forecastLat).toFixed(4)}, ${Number(forecastLon).toFixed(4)}`
    : '';
  const maxScore = Math.max(100, ...rows.map((row) => Number(row.score || 0)));
  const periodStart = context.rangeStart || firstRow?.timestamp_local || firstRow?.timestamp || '';
  const periodEnd = context.rangeEnd || lastRow?.timestamp_local || lastRow?.timestamp || '';

  const metaRows = [
    ['Feature', 'Lunar Fertility Windows'],
    ['Selected period', `${reportTime(periodStart, timezoneName)} - ${reportTime(periodEnd, timezoneName)}`],
    ['Forecast place', result.location || context.location || ''],
    ['Forecast coordinates', forecastCoords],
    ['Timezone', timezoneName],
    ['Natal chart', natalSnap.label || natalSnap.id || 'Saved chart'],
    ['Natal datetime', natalSnap.effective_datetime ? reportTime(natalSnap.effective_datetime, natalDashboard.timezone || timezoneName) : ''],
    ['Natal place', natalSnap.location || natalDashboard.location || ''],
    ['Natal coordinates', natalCoords],
    ['House system', context.houseSystem || ''],
    ['Consider', reportModeLabel(result.consider_mode || context.considerMode)],
    ['Level', `${level.toFixed(0)}%`],
    ['Generated', reportTime(generatedAt, timezoneName)],
  ];

  const metaHtml = metaRows.map(([label, value]) => `
    <tr><th>${reportCell(label)}</th><td>${reportCell(value)}</td></tr>
  `).join('');

  const graphBars = rows.length
    ? rows.map((row) => {
      const score = Math.max(0, Number(row.score || 0));
      const height = Math.max(4, Math.round((score / maxScore) * 132));
      const color = row.sex_label === 'male' ? '#2563eb' : row.sex_label === 'female' ? '#db2777' : '#71717a';
      const opacity = row.phase_kind === 'antiphase' ? 0.45 : 0.95;
      const title = `${reportShortTime(row.timestamp_local || row.timestamp, timezoneName)} | ${score.toFixed(0)} | ${reportSexPhase(row)}`;
      return `<div class="bar" title="${escapeReportHtml(title)}" style="height:${height}px;background:${color};opacity:${opacity};"></div>`;
    }).join('')
    : '<div class="empty">No favorable hourly rows retained.</div>';

  const periodHtml = periodRows.length
    ? periodRows.map((period) => `
      <tr>
        <td>${reportCell(`${reportTime(period.start_local || period.start, timezoneName)} - ${reportTime(period.end_local || period.end, timezoneName)}`)}</td>
        <td>${reportCell(period.best_timestamp_local || period.best_timestamp ? reportTime(period.best_timestamp_local || period.best_timestamp, timezoneName) : '-')}</td>
        <td class="num">${reportCell(Number(period.best_score || 0).toFixed(0))}</td>
        <td>${reportCell(`${period.sex_label || 'unknown'}, ${period.phase_kind || 'unknown'}`)}</td>
        <td>${reportCell(period.moon_sign || '-')}</td>
      </tr>
    `).join('')
    : '<tr><td colspan="5">No grouped fertility periods reached the selected level.</td></tr>';

  const hourlyHtml = rows.length
    ? rows.map((row) => `
      <tr>
        <td>${reportCell(reportTime(row.timestamp_local || row.timestamp, timezoneName))}</td>
        <td class="bartext">${reportCell(reportStrengthBar(row.score))}</td>
        <td class="num">${reportCell(Number(row.score || 0).toFixed(0))}</td>
        <td>${reportCell(reportSexPhase(row))}</td>
        <td>${reportCell(row.moon_sign || '-')}</td>
      </tr>
    `).join('')
    : '<tr><td colspan="5">No hourly fertility rows are available.</td></tr>';

  const topHtml = rankedTop.length
    ? rankedTop.slice(0, 24).map((row) => `
      <tr>
        <td>${reportCell(reportTime(row.timestamp_local || row.timestamp, timezoneName))}</td>
        <td class="num">${reportCell(Number(row.score || 0).toFixed(0))}</td>
        <td>${reportCell(reportSexPhase(row))}</td>
        <td>${reportCell(row.moon_sign || '-')}</td>
      </tr>
    `).join('')
    : '<tr><td colspan="4">No top timepoints are available.</td></tr>';

  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Lunar Fertility Windows Report</title>
  <style>
    body { font-family: Arial, Helvetica, sans-serif; color: #18181b; margin: 34px; line-height: 1.35; }
    h1 { font-size: 24px; margin: 0 0 6px; }
    h2 { font-size: 15px; margin: 24px 0 8px; letter-spacing: 0.08em; text-transform: uppercase; }
    .subtitle { color: #52525b; margin-bottom: 18px; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { border: 1px solid #d4d4d8; padding: 6px 7px; vertical-align: top; }
    th { text-align: left; background: #f4f4f5; font-weight: 700; }
    .meta th { width: 185px; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .bartext { font-family: Consolas, monospace; letter-spacing: 1px; }
    .graph { position: relative; min-height: 160px; border: 1px solid #d4d4d8; background: #fafafa; padding: 14px 10px 10px; overflow: hidden; }
    .bars { position: relative; z-index: 2; height: 138px; display: flex; align-items: end; gap: 2px; }
    .bar { flex: 1 1 4px; min-width: 2px; border-radius: 2px 2px 0 0; }
    .level { position: absolute; left: 0; right: 0; border-top: 1px dashed #18181b; z-index: 1; }
    .legend { display: flex; gap: 18px; color: #52525b; font-size: 10px; margin-top: 7px; }
    .swatch { display: inline-block; width: 10px; height: 10px; margin-right: 4px; vertical-align: -1px; }
    .page-break { break-before: page; page-break-before: always; }
    .empty { color: #71717a; padding: 48px 0; text-align: center; width: 100%; }
  </style>
</head>
<body>
  <h1>Lunar Fertility Windows Report</h1>
  <div class="subtitle">Natal Sun-Moon phase recurrence, grouped periods, hourly favorable rows, and top timepoints.</div>

  <h2>Shared Header</h2>
  <table class="meta"><tbody>${metaHtml}</tbody></table>

  <h2>Graphic Timeline</h2>
  <div class="graph">
    <div class="level" style="bottom:${Math.max(0, Math.min(100, level))}%;"></div>
    <div class="bars">${graphBars}</div>
  </div>
  <div class="legend">
    <span><span class="swatch" style="background:#2563eb;"></span>male Moon-sign polarity</span>
    <span><span class="swatch" style="background:#db2777;"></span>female Moon-sign polarity</span>
    <span>solid = phase, faded = antiphase, dashed line = selected level</span>
  </div>

  <h2>Grouped Fertility Periods</h2>
  <table>
    <thead><tr><th>Period</th><th>Peak time</th><th>Peak</th><th>Sex, phase</th><th>Peak Moon sign</th></tr></thead>
    <tbody>${periodHtml}</tbody>
  </table>

  <h2>Top Timepoints</h2>
  <table>
    <thead><tr><th>Date time</th><th>Strength</th><th>Sex, phase</th><th>Moon sign</th></tr></thead>
    <tbody>${topHtml}</tbody>
  </table>

  <h2 class="page-break">Full Hourly Favorable Table</h2>
  <table>
    <thead><tr><th>Date time</th><th>Strength bar</th><th>Strength</th><th>Sex, phase</th><th>Moon sign</th></tr></thead>
    <tbody>${hourlyHtml}</tbody>
  </table>
</body>
</html>`;
}

function openPrintableReportWindow(html) {
  if (typeof window === 'undefined') return false;
  const reportWindow = window.open('', '_blank');
  if (!reportWindow || !reportWindow.document) return false;
  reportWindow.document.write(html);
  reportWindow.document.close();
  setTimeout(() => {
    try {
      reportWindow.focus();
      reportWindow.print();
    } catch (_) {}
  }, 250);
  return true;
}

function downloadReportHtmlFallback(html, filename) {
  if (typeof document === 'undefined' || typeof URL === 'undefined') return false;
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = String(filename || 'lunar-fertility-report.html').replace(/\.pdf$/i, '.html');
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
  return true;
}

const BEAUTY_BODY_PART_OPTIONS = [
  'Face',
  'Lips',
  'Skin',
  'Eyes',
  'Cheeks',
  'Jaw',
  'Chin',
  'Neck',
  'Throat',
  'Chest',
  'Breasts',
  'Stomach',
  'Heart',
  'Spine',
  'Upper back',
  'Arms',
  'Hands',
  'Lungs',
  'Hips',
  'Thighs',
  'Liver',
  'Knees',
  'Teeth',
  'Bones',
  'Feet',
  'Ankles',
  'Circulation',
  'Reproductive organs',
  'Genitals',
  'Tattoo area',
];

const BEAUTY_PROCEDURE_DEFAULTS = {
  fillers: ['Face', 'Lips', 'Cheeks'],
  botox: ['Face', 'Skin'],
  skin: ['Skin', 'Face'],
  surgery: ['Face', 'Jaw', 'Chin', 'Neck'],
  tattoo_removal: ['Tattoo area'],
  augmentation: ['Chest', 'Breasts', 'Face'],
  reduction: ['Stomach', 'Hips', 'Thighs'],
};

const BEAUTY_PROCEDURE_LABELS = {
  fillers: 'Fillers / augmentation',
  botox: 'Botox / neurotoxin',
  skin: 'Skin treatment / laser resurfacing',
  surgery: 'Surgical procedures',
  tattoo_removal: 'Tattoo removal',
  augmentation: 'General augmentation',
  reduction: 'Reduction / contouring',
};

export default function ElectionModal({
  open,
  onClose,
  onJumpToTime,
  defaultHouseSystem,
  snaps: initialSnaps = [],
  activeSnapId = '',
}) {
  // Model selection (toggle). Supports 'marriage' and 'surgery'.
  const [matter, setMatter] = useState('marriage');
  // Surgery child options
  const [procedure, setProcedure] = useState('cutting'); // 'cutting' | 'purging' | 'diagnostic'
  const [surgerySign, setSurgerySign] = useState('');
  const [rangeStartDate, setRangeStartDate] = useState('');
  const [rangeStartTime, setRangeStartTime] = useState('');
  const [rangeEndDate, setRangeEndDate] = useState('');
  const [rangeEndTime, setRangeEndTime] = useState('');
  const [location, setLocation] = useState('');
  const [timezone, setTimezone] = useState('');
  const [houseSystem] = useState(defaultHouseSystem || 'R');
  const [stepMinutes, setStepMinutes] = useState(60);
  const [limit, setLimit] = useState(15);
  const [weekdays, setWeekdays] = useState(ALL_WEEKDAYS);
  const [weekdayMode, setWeekdayMode] = useState('all');
  const [hourStart, setHourStart] = useState(''); // 'HH:MM'
  const [hourEnd, setHourEnd] = useState('');   // 'HH:MM'
  const [marriageAlgorithm, setMarriageAlgorithm] = useState('alpha');
  const [businessAlgorithm, setBusinessAlgorithm] = useState('alpha');
  const [sourceMode, setSourceMode] = useState(activeSnapId ? 'snap' : 'none'); // 'none' | 'snap'
  const [snaps, setSnaps] = useState(() => (Array.isArray(initialSnaps) ? initialSnaps : []));
  const [selectedSnapId, setSelectedSnapId] = useState(activeSnapId || '');
  const [participantASnapId, setParticipantASnapId] = useState('');
  const [participantBSnapId, setParticipantBSnapId] = useState('');
  const [businessParticipantSnapIds, setBusinessParticipantSnapIds] = useState([]);
  const [estateParticipantSnapId, setEstateParticipantSnapId] = useState('');
  const [includeSrLr, setIncludeSrLr] = useState(true);
  // Surgery/Contract optional heavy checks
  const [includeLunationScreen, setIncludeLunationScreen] = useState(false);
  const [includeFixedStars, setIncludeFixedStars] = useState(false);
  const [genderPref, setGenderPref] = useState('');
  const [lunarFertilityConsiderMode, setLunarFertilityConsiderMode] = useState('phase_and_antiphase');
  const [lunarFertilityLevelPercent, setLunarFertilityLevelPercent] = useState(33);
  // Contract options
  const [preferFixedAsc, setPreferFixedAsc] = useState(true);
  const [saturnBindingOk, setSaturnBindingOk] = useState(true);
  const [minMercuryDirectDays, setMinMercuryDirectDays] = useState(0);
  const [contractMode, setContractMode] = useState('');
  // Business options
  const [includeTraditionalTiming, setIncludeTraditionalTiming] = useState(false);
  const [businessMode, setBusinessMode] = useState(''); // '', 'conservative', 'growth'
  const [emphasizeCommerce, setEmphasizeCommerce] = useState(false);
  const [businessBetaDisplayMode, setBusinessBetaDisplayMode] = useState('total');
  const [businessBetaScope, setBusinessBetaScope] = useState('all');
  const [businessBetaLevelPercent, setBusinessBetaLevelPercent] = useState(67);
  const [businessBetaCurrentLineId, setBusinessBetaCurrentLineId] = useState('event');
  const [businessBetaSelectedLineIds, setBusinessBetaSelectedLineIds] = useState(['event']);
  // Estate options
  const [estateDirection, setEstateDirection] = useState('buy');
  const [estateDisplayMode, setEstateDisplayMode] = useState('total');
  const [estateScope, setEstateScope] = useState('all');
  const [estateLevelPercent, setEstateLevelPercent] = useState(67);
  const [estateCurrentLineId, setEstateCurrentLineId] = useState('event');
  const [estateSelectedLineIds, setEstateSelectedLineIds] = useState(['event']);
  // Journey options
  const [journeyType, setJourneyType] = useState('long'); // 'long' | 'short'
  // Battle options
  const [battleAction, setBattleAction] = useState('battle'); // battle|attack|defense|siege|retreat
  // Hair options
  const [hairGoal, setHairGoal] = useState('balanced');
  // Beautification options
  const [beautyProcedureType, setBeautyProcedureType] = useState('fillers');
  const [beautyBodyParts, setBeautyBodyParts] = useState(() => [...(BEAUTY_PROCEDURE_DEFAULTS['fillers'] || [])]);
  const [beautyBodySigns, setBeautyBodySigns] = useState('');
  // Legal options
  const [legalAction, setLegalAction] = useState('filing'); // 'filing' | 'response' | 'counter'
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0); // 0..1 visual scan progress
  const progRef = React.useRef(null);
  const scanSrcRef = React.useRef(null);
  const scanTerminalRef = React.useRef(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [selectedSeriesTimestamp, setSelectedSeriesTimestamp] = useState('');
  const [reportStatus, setReportStatus] = useState('');

  useEffect(() => {
    if (open) {
      setResult(null); setError(null); setLoading(false); setReportStatus('');
      setSelectedSeriesTimestamp('');
      scanTerminalRef.current = false;
      if (matter === 'legal') {
        setLegalAction('filing');
      }
      // Prefetch snaps for convenience
      const seededSnaps = Array.isArray(initialSnaps) ? initialSnaps : [];
      if (seededSnaps.length) setSnaps(seededSnaps);
      if (activeSnapId) {
        setSelectedSnapId(String(activeSnapId));
        setSourceMode('snap');
      }
      AstroClockAPI.listSnaps().then((res) => {
        const items = res?.items || [];
        setSnaps(items);
        if (activeSnapId && items.some((snap) => String(snap?.id || '') === String(activeSnapId))) {
          setSelectedSnapId(String(activeSnapId));
          setSourceMode('snap');
        }
      }).catch(()=>{});
      // Reset beautification selections to the default procedure
      setBeautyProcedureType('fillers');
      setBeautyBodyParts([...(BEAUTY_PROCEDURE_DEFAULTS['fillers'] || [])]);
      setBeautyBodySigns('');
    }
  }, [activeSnapId, initialSnaps, open]);

  useEffect(() => {
    if (matter !== 'conception' && genderPref) {
      setGenderPref('');
    }
  }, [matter, genderPref]);

  useEffect(() => {
    if (matter === 'lunar_fertility' && sourceMode === 'none') {
      setSourceMode('snap');
      setIncludeSrLr(false);
    }
  }, [matter, sourceMode]);

  useEffect(() => {
    if (
      includeSrLr
      && (
        (matter === 'marriage' && marriageAlgorithm === 'beta')
        || (matter === 'business' && businessAlgorithm === 'beta')
        || matter === 'estate'
      )
    ) {
      setIncludeSrLr(false);
    }
  }, [businessAlgorithm, includeSrLr, marriageAlgorithm, matter]);

  if (!open) return null;

  const isMarriageMatter = matter === 'marriage';
  const isBusinessMatter = matter === 'business';
  const isEstateMatter = matter === 'estate';
  const isLunarFertilityMatter = matter === 'lunar_fertility';
  const isMarriageBeta = isMarriageMatter && marriageAlgorithm === 'beta';
  const isBusinessBeta = isBusinessMatter && businessAlgorithm === 'beta';
  const participantModeActive = isMarriageBeta || isBusinessBeta || isEstateMatter;
  const natalAvailable = !participantModeActive && (sourceMode === 'snap' && !!selectedSnapId);
  const hasSavedSnaps = Array.isArray(snaps) && snaps.length > 0;
  const currentProcedureLabel = BEAUTY_PROCEDURE_LABELS[beautyProcedureType] || 'Selected procedure';
  const businessBetaExtraction = result?.business_beta_extraction || null;
  const businessBetaPeriods = Array.isArray(result?.business_beta_periods) ? result.business_beta_periods : [];
  const estateExtraction = result?.estate_extraction || null;
  const estatePeriods = Array.isArray(result?.estate_periods) ? result.estate_periods : [];
  const lineExtraction = businessBetaExtraction || estateExtraction;
  const extractedPeriods = businessBetaExtraction ? businessBetaPeriods : estatePeriods;
  const lunarFertilityPeriods = result?.matter === 'lunar_fertility' && Array.isArray(result?.periods)
    ? result.periods
    : [];
  const hasLunarFertilityResult = result?.matter === 'lunar_fertility';
  const extractionPassKey = estateExtraction ? 'estate_pass' : 'business_beta_pass';
  const extractionThresholdKey = estateExtraction ? 'estate_selected_threshold' : 'business_beta_selected_threshold';
  const lineModelLabel = estateExtraction ? 'Estate lines' : 'Business beta lines';
  const businessBetaLineOptions = useMemo(
    () => (
      buildBusinessBetaLineOptions({
        snaps,
        participantSnapIds: businessParticipantSnapIds,
        participantItems: result?.participants?.items || [],
      })
    ),
    [businessParticipantSnapIds, result?.participants?.items, snaps],
  );
  const estateLineOptions = useMemo(
    () => (
      buildEstateLineOptions({
        snaps,
        estateParticipantSnapId,
        participantItems: result?.matter === 'estate' ? (result?.participants?.items || []) : [],
      })
    ),
    [estateParticipantSnapId, result?.matter, result?.participants?.items, snaps],
  );

  useEffect(() => {
    if (!isBusinessBeta) return;
    const availableIds = businessBetaLineOptions.map((item) => item.id);
    if (!availableIds.length) {
      setBusinessBetaCurrentLineId('event');
      setBusinessBetaSelectedLineIds(['event']);
      return;
    }
    setBusinessBetaCurrentLineId((current) => (
      availableIds.includes(current) ? current : availableIds[0]
    ));
    setBusinessBetaSelectedLineIds((current) => {
      const filtered = Array.isArray(current) ? current.filter((lineId) => availableIds.includes(lineId)) : [];
      return filtered.length ? filtered : availableIds;
    });
  }, [businessBetaLineOptions, isBusinessBeta]);

  useEffect(() => {
    if (!isEstateMatter) return;
    const availableIds = estateLineOptions.map((item) => item.id);
    if (!availableIds.length) {
      setEstateCurrentLineId('event');
      setEstateSelectedLineIds(['event']);
      return;
    }
    setEstateCurrentLineId((current) => (
      availableIds.includes(current) ? current : availableIds[0]
    ));
    setEstateSelectedLineIds((current) => {
      const filtered = Array.isArray(current) ? current.filter((lineId) => availableIds.includes(lineId)) : [];
      return filtered.length ? filtered : availableIds;
    });
  }, [estateLineOptions, isEstateMatter]);

  const updateWeekdaySelection = (nextDays, nextMode = null) => {
    const normalized = ALL_WEEKDAYS.filter((day) => Array.isArray(nextDays) && nextDays.includes(day));
    setWeekdays(normalized);
    setWeekdayMode(
      nextMode || (
        normalized.length === 0
          ? 'none'
          : normalized.length === ALL_WEEKDAYS.length
            ? 'all'
            : 'custom'
      ),
    );
  };

  const handleProcedureChange = (value) => {
    setBeautyProcedureType(value);
    setBeautyBodyParts([...(BEAUTY_PROCEDURE_DEFAULTS[value] || [])]);
  };

  const toggleBusinessParticipantSnapId = (snapId) => {
    const nextId = String(snapId || '').trim();
    if (!nextId) return;
    setBusinessParticipantSnapIds((current) => (
      current.includes(nextId)
        ? current.filter((item) => item !== nextId)
        : [...current, nextId]
    ));
  };

  const close = () => {
    setResult(null); setError(null); setLoading(false); setReportStatus(''); onClose?.();
    scanTerminalRef.current = false;
    if (progRef.current) { clearInterval(progRef.current); progRef.current = null; }
    if (scanSrcRef.current) { try { scanSrcRef.current.close(); } catch(_) {} scanSrcRef.current = null; }
    setProgress(0);
    setGenderPref('');
  };

  const doScan = async () => {
    setLoading(true); setError(null); setReportStatus(''); setProgress(0);
    scanTerminalRef.current = false;
    try {
      const startIso = buildIso(rangeStartDate, rangeStartTime);
      const endIso = buildIso(rangeEndDate, rangeEndTime);
      if (!startIso || !endIso) { setError('Enter a valid start and end date/time.'); setLoading(false); return; }
      if (new Date(startIso) >= new Date(endIso)) {
        setError('End must be after start (use 24-hour HH:MM).');
        setLoading(false);
        return;
      }
      if (!location) { setError('Enter a location.'); setLoading(false); return; }
      const hourStartMinutes = parseElectionClockValue(hourStart);
      const hourEndMinutes = parseElectionClockValue(hourEnd);
      if (hourStart && hourStartMinutes == null) {
        setError('Hour start must be a valid 24-hour HH:MM value.');
        setLoading(false);
        return;
      }
      if (hourEnd && hourEndMinutes == null) {
        setError('Hour end must be a valid 24-hour HH:MM value.');
        setLoading(false);
        return;
      }
      if (hourStartMinutes != null && hourEndMinutes != null && hourStartMinutes > hourEndMinutes) {
        setError('Hour end must be after hour start (24-hour format).');
        setLoading(false);
        return;
      }

      const effectiveWeekdayMode = (
        weekdayMode ||
        (weekdays.length === 0
          ? 'none'
          : weekdays.length === ALL_WEEKDAYS.length
            ? 'all'
            : 'custom')
      );

      const base = {
        matter,
        start: startIso,
        end: endIso,
        location,
        timezone: timezone || undefined,
        houseSystem,
        stepMinutes,
        limit,
        weekdays,
        weekdayMode: effectiveWeekdayMode,
        hourStart: hourStart || undefined,
        hourEnd: hourEnd || undefined,
        ...(matter === 'conception' && genderPref ? { gender: genderPref } : {}),
        ...(matter === 'lunar_fertility' ? {
          considerMode: lunarFertilityConsiderMode,
          levelPercent: Number.isFinite(Number(lunarFertilityLevelPercent))
            ? Math.max(0, Math.min(100, Number(lunarFertilityLevelPercent)))
            : 33,
        } : {}),
      };
      if (isMarriageMatter) base.marriageAlgorithm = marriageAlgorithm;
      if (isBusinessMatter) base.businessAlgorithm = businessAlgorithm;
      if (natalAvailable) base.includeSrLr = includeSrLr;
      if (isEstateMatter) {
        base.estateDirection = estateDirection === 'sell' ? 'sell' : 'buy';
        base.includeTraditionalTiming = true;
        base.estateDisplayMode = estateDisplayMode;
        base.estateScope = estateScope;
        base.estateLevelPercent = Number.isFinite(Number(estateLevelPercent))
          ? Math.max(0, Math.min(100, Number(estateLevelPercent)))
          : 67;
        if (estateCurrentLineId) base.estateCurrentLineId = estateCurrentLineId;
        if (estateScope === 'selected' && Array.isArray(estateSelectedLineIds) && estateSelectedLineIds.length) {
          base.estateSelectedLineIds = estateSelectedLineIds;
        }
      }
      if (matter === 'surgery') {
        if (surgerySign) base.surgerySign = surgerySign;
        if (procedure) base.procedure = procedure;
        if (includeLunationScreen) base.includeLunationScreen = true;
        if (includeFixedStars) base.includeFixedStars = true;
      }
      if (matter === 'business') {
        if (includeTraditionalTiming || isBusinessBeta) base.includeTraditionalTiming = true;
        if (!isBusinessBeta) {
          if (includeLunationScreen) base.includeLunationScreen = true;
          if (includeFixedStars) base.includeFixedStars = true;
          if (businessMode) base.businessMode = businessMode;
          if (emphasizeCommerce) base.emphasizeCommerce = true;
        } else {
          base.businessBetaDisplayMode = businessBetaDisplayMode;
          base.businessBetaScope = businessBetaScope;
          base.businessBetaLevelPercent = Number.isFinite(Number(businessBetaLevelPercent))
            ? Math.max(0, Math.min(100, Number(businessBetaLevelPercent)))
            : 67;
          if (businessBetaCurrentLineId) base.businessBetaCurrentLineId = businessBetaCurrentLineId;
          if (businessBetaScope === 'selected' && Array.isArray(businessBetaSelectedLineIds) && businessBetaSelectedLineIds.length) {
            base.businessBetaSelectedLineIds = businessBetaSelectedLineIds;
          }
        }
      }
      if (matter === 'contract') {
        base.preferFixedAsc = !!preferFixedAsc;
        if (!saturnBindingOk) base.saturnBindingOk = false;
        if (Number.isFinite(minMercuryDirectDays) && minMercuryDirectDays > 0) base.minMercuryDirectDays = Number(minMercuryDirectDays);
        if (includeFixedStars) base.includeFixedStars = true;
        if (contractMode) base.contractMode = contractMode;
      }
      if (matter === 'journey') {
        if (journeyType) base.journeyType = journeyType;
        if (includeFixedStars) base.includeFixedStars = true;
      }
      if (matter === 'battle') {
        if (battleAction) base.actionType = battleAction;
        if (includeFixedStars) base.includeFixedStars = true;
        if (includeTraditionalTiming) base.includeTraditionalTiming = true;
      }
      if (matter === 'haircut') {
        if (hairGoal) base.hairGoal = hairGoal;
      }
      if (matter === 'beautification') {
        if (beautyProcedureType) base.procedureType = beautyProcedureType;
        if (Array.isArray(beautyBodyParts) && beautyBodyParts.length) base.bodyParts = beautyBodyParts;
        if (beautyBodySigns) base.bodySigns = beautyBodySigns;
        if (includeTraditionalTiming) base.includeTraditionalTiming = true;
        if (includeFixedStars) base.includeFixedStars = true;
      }
      if (matter === 'conception') {
        if (includeTraditionalTiming) base.includeTraditionalTiming = true;
        if (includeFixedStars) base.includeFixedStars = true;
      }
      if (matter === 'viral') {
        if (includeTraditionalTiming) base.includeTraditionalTiming = true;
        if (includeFixedStars) base.includeFixedStars = true;
      }
      if (matter === 'legal') {
        base.legalAction = legalAction;
        if (includeTraditionalTiming) base.includeTraditionalTiming = true;
        if (includeFixedStars) base.includeFixedStars = true;
      }
      if (isMarriageBeta) {
        if (!participantASnapId || !participantBSnapId) {
          setError('Beta marriage requires Snap A and Snap B.');
          setLoading(false);
          return;
        }
        if (participantASnapId === participantBSnapId) {
          setError('Beta marriage requires two different saved charts.');
          setLoading(false);
          return;
        }
      }
      if (isBusinessBeta) {
        const participantSnapIds = businessParticipantSnapIds.filter(Boolean);
        if (!participantSnapIds.length) {
          setError('Beta business requires at least one founder or owner chart.');
          setLoading(false);
          return;
        }
        if ((new Set(participantSnapIds)).size !== participantSnapIds.length) {
          setError('Beta business requires unique founder or owner charts.');
          setLoading(false);
          return;
        }
      }
      if (isEstateMatter) {
        if (!estateParticipantSnapId) {
          setError('Estate election requires one buyer or seller saved chart.');
          setLoading(false);
          return;
        }
      }
      if (isLunarFertilityMatter) {
        if (sourceMode !== 'snap' || !selectedSnapId) {
          setError('Lunar Fertility Windows requires one saved natal chart.');
          setLoading(false);
          return;
        }
      }
      const opts = isMarriageBeta
        ? {
            ...base,
            participantASnapId,
            participantBSnapId,
          }
        : isBusinessBeta
          ? {
              ...base,
              participantSnapIds: businessParticipantSnapIds.filter(Boolean),
            }
        : isEstateMatter
          ? {
              ...base,
              estateParticipantSnapId,
            }
        : (sourceMode === 'snap' && selectedSnapId)
          ? { ...base, natalSnapId: selectedSnapId }
          : base;
      if (scanSrcRef.current) { try { scanSrcRef.current.close(); } catch(_) {} scanSrcRef.current = null; }
      const es = await AstroClockAPI.electionStream(opts);
      if (!es) { throw new Error('Unable to open stream'); }
      scanSrcRef.current = es;
      let completed = false;
      es.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg?.type === 'progress') {
            if (typeof msg.progress === 'number') setProgress(Math.max(0, Math.min(1, msg.progress)));
          } else if (msg?.type === 'done') {
            completed = true;
            scanTerminalRef.current = true;
            setResult(msg.data || null);
            setProgress(1);
            setLoading(false);
            if (scanSrcRef.current) { try { scanSrcRef.current.close(); } catch(_) {} scanSrcRef.current = null; }
          }
        } catch (_) {}
      };
      es.onerror = async () => {
        if (shouldIgnoreElectionStreamError({
          currentSource: scanSrcRef.current,
          errorSource: es,
          isTerminal: completed || scanTerminalRef.current,
          readyState: es?.readyState,
        })) {
          return;
        }
        let errMsg = 'Stream error';
        try {
          await AstroClockAPI.validateElection(opts);
        } catch (apiErr) {
          errMsg = apiErr?.message || errMsg;
        }
        scanTerminalRef.current = true;
        setError(errMsg);
        setLoading(false);
        if (scanSrcRef.current) { try { scanSrcRef.current.close(); } catch(_) {} scanSrcRef.current = null; }
      };
    } catch (e) {
      setError(e?.message || String(e)); setLoading(false);
      if (scanSrcRef.current) { try { scanSrcRef.current.close(); } catch(_) {} scanSrcRef.current = null; }
    }
  };

  const usesWeightedTagSanitizer = Boolean(
    isMarriageBeta
    || isBusinessBeta
    || isEstateMatter
    || result?.marriage_algorithm === 'beta'
    || result?.business_algorithm === 'beta'
    || result?.matter === 'estate'
  );
  const top = useMemo(() => {
    const rows = Array.isArray(result?.top) ? result.top : [];
    return usesWeightedTagSanitizer ? rows.map(sanitizeWeightedElectionRow) : rows;
  }, [result?.business_algorithm, result?.marriage_algorithm, result?.matter, result?.top, usesWeightedTagSanitizer]);
  const series = result?.series || [];
  const retainedSeries = useMemo(() => normalizeElectionSeriesRows(series), [series]);
  const timelineSeries = useMemo(() => mergeElectionTimelineRows(retainedSeries, top), [retainedSeries, top]);
  const displaySeries = useMemo(() => compressElectionSeriesRows(timelineSeries), [timelineSeries]);
  const peakSeriesRows = useMemo(() => pickElectionPeakRows(timelineSeries, stepMinutes, 4), [timelineSeries, stepMinutes]);
  const bestSeriesRow = peakSeriesRows[0] || timelineSeries.slice().sort((a, b) => Number(b.score || 0) - Number(a.score || 0))[0] || null;
  const selectedSeriesRow = useMemo(() => {
    if (!timelineSeries.length) return null;
    return timelineSeries.find((row) => row.timestamp === selectedSeriesTimestamp) || bestSeriesRow || null;
  }, [bestSeriesRow, selectedSeriesTimestamp, timelineSeries]);
  const seriesScoreRange = useMemo(() => {
    if (!timelineSeries.length) return { min: 0, max: 0 };
    const scores = timelineSeries.map((row) => Number(row.score || 0));
    return { min: Math.min(...scores), max: Math.max(...scores) };
  }, [timelineSeries]);

  useEffect(() => {
    if (!timelineSeries.length) {
      setSelectedSeriesTimestamp('');
      return;
    }
    setSelectedSeriesTimestamp((current) => {
      if (current && timelineSeries.some((row) => row.timestamp === current)) return current;
      return bestSeriesRow?.timestamp || timelineSeries[0]?.timestamp || '';
    });
  }, [bestSeriesRow, timelineSeries]);

  const isCautionTag = (t) => {
    try {
      const s = String(t || '').toLowerCase();
      // Allow enemy weakness indicators to remain in Pros
      if (s.includes('7th ruler') && s.includes('retrograde')) return false;
      return (
        s.includes('avoid') || s.includes('unfavored') || s.includes('severe') || s.includes('retrograde') || s.includes('combust') ||
        s.includes('under beams') || s.includes('void-of-course') || s.includes('voc') ||
        /\bin (6th|8th|12th)\b/.test(s) || s.includes('full moon') || s.includes('cardinal asc') ||
        s.includes('on asc') || s.includes('on desc') ||
        s.includes('dark moon') || s.includes('forbidden') || s.includes('softens posture') ||
        s.includes('debilitated') || s.includes('critical') ||
        // Surgery-specific: classify waxing/bleeding risk as a caution
        s.includes('bleeding risk') || (s.includes('waxing') && s.includes('(surgery)'))
      );
    } catch { return false; }
  };

  const splitRowTags = (row, prosLimit, cautionLimit) => {
    const mapDisplayTag = (tag) => (
      usesWeightedTagSanitizer ? sanitizeWeightedElectionTagDisplay(tag) : String(tag || '').trim()
    );
    const explicitPros = Array.isArray(row?.pros) ? row.pros.filter(Boolean) : [];
    const explicitCautions = Array.isArray(row?.cautions) ? row.cautions.filter(Boolean) : [];
    if (explicitPros.length || explicitCautions.length) {
      return {
        pros: explicitPros.map(mapDisplayTag).filter(Boolean).slice(0, prosLimit),
        cautions: explicitCautions.map(mapDisplayTag).filter(Boolean).slice(0, cautionLimit),
      };
    }
    const tags = Array.isArray(row?.tags) ? row.tags : [];
    return {
      pros: tags.filter((t) => !isCautionTag(t)).map(mapDisplayTag).filter(Boolean).slice(0, prosLimit),
      cautions: tags.filter(isCautionTag).map(mapDisplayTag).filter(Boolean).slice(0, cautionLimit),
    };
  };

  const jumpToElectionRow = async (row) => {
    try {
      if (!row) return;
      const iso = row.timestamp_local || row.timestamp;
      const loc = result?.location || location || '';
      let tz = result?.timezone || '';
      if (!tz && loc) {
        try {
          const z = await AstroClockAPI.resolveTimezone(loc);
          tz = z?.timezone || z?.data?.timezone || '';
        } catch (_) {}
      }
      onJumpToTime?.({ iso, location: loc, timezone: tz || undefined });
    } catch (_) {}
  };

  const doDownloadTopLocal = () => {
    try {
      if (!Array.isArray(top) || top.length === 0) {
        setError('No results to export. Run a scan first.');
        return;
      }
      const header = ['Timestamp', 'Score', 'Tags'];
      const rows = top.map(r => [
        (r.timestamp_local || r.timestamp || ''),
        String(Number(r.score || 0)),
        (Array.isArray(r.tags) ? r.tags.join(' · ') : ''),
      ]);
      const csv = [header, ...rows].map(cols => cols.map(v => {
        const s = String(v ?? '');
        return (/[,"\n]/.test(s)) ? '"' + s.replace(/"/g,'""') + '"' : s;
      }).join(',')).join('\n');
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `election_${matter}_top.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e?.message || String(e));
    }
  };

  const doExportLunarFertilityReport = async () => {
    try {
      if (result?.matter !== 'lunar_fertility') {
        setError('Fertility reporting is only available for Lunar Fertility Windows.');
        return;
      }
      if (!timelineSeries.length) {
        setError('No fertility rows to report. Run a Lunar Fertility scan first.');
        return;
      }

      const natalSnap = Array.isArray(snaps)
        ? snaps.find((snap) => String(snap?.id || '') === String(selectedSnapId || ''))
        : null;
      const generatedAt = new Date().toISOString();
      const filename = buildLunarFertilityReportDefaultPath({ generatedAt });
      const html = buildLunarFertilityReportHtml({
        result,
        topRows: top,
        seriesRows: timelineSeries,
        periods: lunarFertilityPeriods,
        context: {
          rangeStart: buildIso(rangeStartDate, rangeStartTime),
          rangeEnd: buildIso(rangeEndDate, rangeEndTime),
          location,
          timezone,
          houseSystem,
          considerMode: lunarFertilityConsiderMode,
          levelPercent: lunarFertilityLevelPercent,
          natalSnap,
          generatedAt,
        },
      });

      const exporter = typeof window !== 'undefined' ? window.electronAPI?.exportReport : null;
      if (exporter) {
        const response = await exporter({
          html,
          pageSize: 'A4',
          title: 'Save Lunar Fertility Report',
          defaultPath: filename,
        });
        if (response?.ok) {
          setReportStatus(`Report saved: ${response.path || filename}`);
          return;
        }
        setReportStatus(response?.error || 'Report export canceled.');
        return;
      }

      if (openPrintableReportWindow(html)) {
        setReportStatus('Opened browser print dialog - choose Save as PDF.');
      } else if (downloadReportHtmlFallback(html, filename)) {
        setReportStatus('Downloaded HTML fertility report.');
      } else {
        setError('Unable to open or download the fertility report.');
      }
    } catch (e) {
      setError(e?.message || String(e));
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex items-start justify-center p-4 overflow-auto">
      <div className="absolute inset-0" onClick={close} />
      {/* Floating close chip for consistency with Transits */}
      <div className="absolute top-4 right-4">
        <div role="button" tabIndex={0} onClick={close}
             onKeyDown={(e)=>{ if (e.key==='Enter' || e.key===' ') { e.preventDefault(); close(); } }}
             className="text-[11px] px-2 py-0.5 border rounded bg-white/90 hover:bg-white cursor-pointer select-none shadow">Close</div>
      </div>
      <div className="relative z-10 w-full max-w-3xl">
        <div className="rounded-2xl border shadow-xl p-6 max-h-[85vh] overflow-auto bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl border-gray-200/80 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Election</h2>
            <button className="text-zinc-600 hover:text-black" onClick={close}>✕</button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
            <div className="md:col-span-2">
              <label className="block text-xs text-zinc-600 mb-1">Model</label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='marriage' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('marriage')}
                >
                  Marriage
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='surgery' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('surgery')}
                >
                  Surgery
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='business' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('business')}
                >
                  Business
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='estate' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('estate')}
                >
                  Real Estate
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='contract' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('contract')}
                >
                  Contract
                </button>
                {/* Journey model */}
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='journey' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('journey')}
                >
                  Journey
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='haircut' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('haircut')}
                >
                  Haircut
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='beautification' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('beautification')}
                >
                  Beautification
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='conception' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('conception')}
                >
                  Conception
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='lunar_fertility' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>setMatter('lunar_fertility')}
                >
                  Lunar Fertility Windows
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='viral' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>{ setMatter('viral'); }}
                >
                  Viral Publish
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='battle' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>{ setMatter('battle'); setBattleAction('battle'); }}
                >
                  Battle
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${matter==='legal' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                  onClick={()=>{ setMatter('legal'); setLegalAction('filing'); }}
                >
                  Legal Action
                </button>
              </div>
            </div>
            {isMarriageMatter && (
              <div className="md:col-span-2">
                <label className="block text-xs text-zinc-600 mb-1">Marriage algorithm</label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${marriageAlgorithm === 'alpha' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                    onClick={() => setMarriageAlgorithm('alpha')}
                  >
                    Alpha
                  </button>
                  <button
                    type="button"
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${marriageAlgorithm === 'beta' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                    onClick={() => setMarriageAlgorithm('beta')}
                  >
                    Beta
                  </button>
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1">
                  {isMarriageBeta
                    ? MARRIAGE_BETA_DESCRIPTION
                    : MARRIAGE_ALPHA_DESCRIPTION}
                </p>
              </div>
            )}
            {isBusinessMatter && (
              <div className="md:col-span-2">
                <label className="block text-xs text-zinc-600 mb-1">Business algorithm</label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${businessAlgorithm === 'alpha' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                    onClick={() => setBusinessAlgorithm('alpha')}
                  >
                    Alpha
                  </button>
                  <button
                    type="button"
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${businessAlgorithm === 'beta' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                    onClick={() => setBusinessAlgorithm('beta')}
                  >
                    Beta
                  </button>
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1">
                  {isBusinessBeta
                    ? BUSINESS_BETA_DESCRIPTION
                    : BUSINESS_ALPHA_DESCRIPTION}
                </p>
              </div>
            )}
            {isEstateMatter && (
              <div className="md:col-span-2">
                <label className="block text-xs text-zinc-600 mb-1">Estate direction</label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${estateDirection === 'buy' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                    onClick={() => setEstateDirection('buy')}
                  >
                    Buy
                  </button>
                  <button
                    type="button"
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${estateDirection === 'sell' ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                    onClick={() => setEstateDirection('sell')}
                  >
                    Sell
                  </button>
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1">
                  {ESTATE_DESCRIPTION}
                </p>
                <div className="mt-3 rounded-xl border border-zinc-200 bg-zinc-50/80 p-3 dark:border-gray-700 dark:bg-gray-900/40">
                  <div className="text-[11px] uppercase tracking-[0.24em] text-zinc-500 dark:text-zinc-400">Estate period extraction</div>
                  <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                    <div>
                      <label className="block text-xs text-zinc-600 mb-1">Mode</label>
                      <select
                        className="px-2 py-1 border rounded w-full"
                        value={estateDisplayMode}
                        onChange={(e) => setEstateDisplayMode(e.target.value)}
                      >
                        <option value="total">Show total</option>
                        <option value="detail">Show detail</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-zinc-600 mb-1">Line scope</label>
                      <select
                        className="px-2 py-1 border rounded w-full"
                        value={estateScope}
                        onChange={(e) => setEstateScope(e.target.value)}
                      >
                        <option value="all">All lines</option>
                        <option value="current">Current line</option>
                        <option value="selected">Selected subset</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-zinc-600 mb-1">Threshold %</label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        className="px-2 py-1 border rounded w-full"
                        value={estateLevelPercent}
                        onChange={(e) => setEstateLevelPercent(Number(e.target.value || 67))}
                      />
                    </div>
                  </div>
                  {estateScope === 'current' && (
                    <div className="mt-3">
                      <label className="block text-xs text-zinc-600 mb-1">Current line</label>
                      <select
                        className="px-2 py-1 border rounded w-full"
                        value={estateCurrentLineId}
                        onChange={(e) => setEstateCurrentLineId(e.target.value)}
                      >
                        {estateLineOptions.map((option) => (
                          <option key={option.id} value={option.id}>{option.label}</option>
                        ))}
                      </select>
                    </div>
                  )}
                  {estateScope === 'selected' && (
                    <div className="mt-3">
                      <label className="block text-xs text-zinc-600 mb-1">Selected lines</label>
                      <div className="flex flex-wrap gap-2">
                        {estateLineOptions.map((option) => {
                          const checked = estateSelectedLineIds.includes(option.id);
                          return (
                            <label
                              key={option.id}
                              className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[12px] ${
                                checked
                                  ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-200 dark:bg-zinc-100 dark:text-zinc-900'
                                  : 'border-zinc-300 bg-white text-zinc-700 dark:border-gray-600 dark:bg-gray-800 dark:text-zinc-200'
                              }`}
                            >
                              <input
                                type="checkbox"
                                className="hidden"
                                checked={checked}
                                onChange={() => {
                                  setEstateSelectedLineIds((current) => {
                                    const next = Array.isArray(current) ? [...current] : [];
                                    if (next.includes(option.id)) {
                                      const filtered = next.filter((lineId) => lineId !== option.id);
                                      return filtered.length ? filtered : [option.id];
                                    }
                                    return [...next, option.id];
                                  });
                                }}
                              />
                              <span>{option.label}</span>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            <div>
              <label className="block text-xs text-zinc-600 mb-1">Start</label>
              <div className="flex gap-2">
                <input type="date" className="px-2 py-1 border rounded w-1/2" value={rangeStartDate} onChange={e=>setRangeStartDate(e.target.value)} />
                <input
                  type="time"
                  lang="en-GB"
                  inputMode="numeric"
                  step="60"
                  placeholder="HH:MM"
                  className="px-2 py-1 border rounded w-1/2"
                  value={rangeStartTime}
                  onChange={e=>setRangeStartTime(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-zinc-600 mb-1">End</label>
              <div className="flex gap-2">
                <input type="date" className="px-2 py-1 border rounded w-1/2" value={rangeEndDate} onChange={e=>setRangeEndDate(e.target.value)} />
                <input
                  type="time"
                  lang="en-GB"
                  inputMode="numeric"
                  step="60"
                  placeholder="HH:MM"
                  className="px-2 py-1 border rounded w-1/2"
                  value={rangeEndTime}
                  onChange={e=>setRangeEndTime(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-zinc-600 mb-1">Location</label>
              <input type="text" className="px-2 py-1 border rounded w-full" placeholder="e.g., London, UK" value={location} onChange={e=>setLocation(e.target.value)} />
            </div>
            {matter==='surgery' && (
              <>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Procedure Type</label>
                  <select className="px-2 py-1 border rounded w-full" value={procedure} onChange={e=>setProcedure(e.target.value)}>
                    <option value="cutting">Cutting (surgery)</option>
                    <option value="purging">Purging / cleansing</option>
                    <option value="diagnostic">Diagnostic / exploratory</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Body Part</label>
                  <select className="px-2 py-1 border rounded w-full" value={surgerySign} onChange={e=>setSurgerySign(e.target.value)}>
                    <option value="">— Select —</option>
                    <option value="Aries">Head, face, brain</option>
                    <option value="Taurus">Neck, throat, thyroid</option>
                    <option value="Gemini">Arms, shoulders, hands, lungs</option>
                    <option value="Cancer">Chest, breasts, stomach</option>
                    <option value="Leo">Heart, upper back, spine</option>
                    <option value="Virgo">Intestines, digestive system</option>
                    <option value="Libra">Kidneys, lower back, skin</option>
                    <option value="Scorpio">Reproductive organs, bladder, colon</option>
                    <option value="Sagittarius">Thighs, hips, liver</option>
                    <option value="Capricorn">Knees, bones, teeth</option>
                    <option value="Aquarius">Calves, ankles, circulatory</option>
                    <option value="Pisces">Feet, lymphatic</option>
                  </select>
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <label className="inline-flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={includeLunationScreen} onChange={e=>setIncludeLunationScreen(e.target.checked)} />
                    Last Lunation screen
                  </label>
                  <label className="inline-flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={includeFixedStars} onChange={e=>setIncludeFixedStars(e.target.checked)} />
                    Fixed stars (1°) on angles/Moon
                  </label>
                </div>
                {!hasSavedSnaps && (
                  <div className="md:col-span-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                    No saved Astro Clock charts were found. Save a chart first, then it will appear here.
                  </div>
                )}
              </>
            )}
            {matter==='journey' && (
              <>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Journey Type</label>
                  <select className="px-2 py-1 border rounded w-full" value={journeyType} onChange={e=>setJourneyType(e.target.value)}>
                    <option value="long">Long journey (9th house)</option>
                    <option value="short">Short journey (3rd house)</option>
                  </select>
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <label className="inline-flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={includeFixedStars} onChange={e=>setIncludeFixedStars(e.target.checked)} />
                    Fixed stars (1°) on angles/keys
                  </label>
                </div>
              </>
            )}
            {matter==='battle' && (
              <>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Action Focus</label>
                  <select className="px-2 py-1 border rounded w-full" value={battleAction} onChange={e=>setBattleAction(e.target.value)}>
                    <option value="battle">Balanced battle posture</option>
                    <option value="attack">Attack / assault</option>
                    <option value="defense">Defense / hold position</option>
                    <option value="siege">Siege / long engagement</option>
                    <option value="retreat">Organised retreat</option>
                  </select>
                </div>
                <div className="md:col-span-2 text-xs">
                  {natalAvailable ? (
                    <p className="text-emerald-700 dark:text-emerald-400">
                      Natal overlay active — directions, return windows, and transit hits are blended with the battle heuristics.
                    </p>
                  ) : (
                    <p className="text-zinc-500 dark:text-zinc-400">
                      Add a saved snap to enforce Morin&apos;s natal promise checks; transit-only scoring remains available without it.
                    </p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Guidance</label>
                  <ul className="text-[11px] text-zinc-600 space-y-0.5 pl-4 list-disc">
                    <li>Fortifies Ascendant and Mars, weakens the 7th, and screens for prohibitions like Algol or eclipse windows.</li>
                    <li>Action focus biases the scoring toward offensive or defensive traits (e.g., oriental Mars for attacks, occidental for defense).</li>
                    <li>Optional fixed star and planetary hour toggles refine results for critical engagements.</li>
                  </ul>
                </div>
                <div className="md:col-span-2 flex flex-wrap items-center gap-3 text-sm">
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeTraditionalTiming} onChange={e=>setIncludeTraditionalTiming(e.target.checked)} />
                    Add planetary day/hour context
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeFixedStars} onChange={e=>setIncludeFixedStars(e.target.checked)} />
                    Include fixed star screening (1°)
                  </label>
                </div>
              </>
            )}
            {matter==='haircut' && (
              <>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Hair Objectives</label>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="inline-flex items-center gap-2 text-sm">
                      <span>Goal</span>
                      <select className="px-2 py-1 border rounded" value={hairGoal} onChange={e=>setHairGoal(e.target.value)}>
                        <option value="balanced">Balanced (default)</option>
                        <option value="growth">Faster growth</option>
                        <option value="lasting">Longer-lasting style</option>
                      </select>
                    </div>
                    <div className="text-xs text-zinc-500 dark:text-zinc-400">
                      Waxing favors growth; waning favors longevity.
                    </div>
                  </div>
                  {natalAvailable && (
                    <div className="mt-2 text-xs text-emerald-700 dark:text-emerald-400">
                      Natal bonuses are applied automatically when a saved chart is selected.
                    </div>
                  )}
                </div>
              </>
            )}
            {matter==='beautification' && (
              <>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Procedure Type</label>
                  <select className="px-2 py-1 border rounded w-full" value={beautyProcedureType} onChange={e=>handleProcedureChange(e.target.value)}>
                    <option value="fillers">Fillers / augmentation</option>
                    <option value="botox">Botox / neurotoxin</option>
                    <option value="skin">Skin treatment / laser resurfacing</option>
                    <option value="surgery">Surgical (facelift, rhinoplasty)</option>
                    <option value="tattoo_removal">Tattoo removal</option>
                    <option value="augmentation">General augmentation</option>
                    <option value="reduction">Reduction / contouring</option>
                  </select>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1">
                    The engine biases Moon phase, malefic screening, and Venus condition according to the selected procedure, and the focus suggestions below adjust automatically.
                  </p>
                </div>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Body Parts / Focus</label>
                  <div className="flex flex-wrap gap-1.5">
                    {BEAUTY_BODY_PART_OPTIONS.map((option) => {
                      const selected = beautyBodyParts.includes(option);
                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => {
                            setBeautyBodyParts((prev) => {
                              if (prev.includes(option)) {
                                return prev.filter((item) => item !== option);
                              }
                              return [...prev, option];
                            });
                          }}
                          className={`px-2 py-0.5 rounded-full border text-[12px] transition-colors ${
                            selected
                              ? 'bg-zinc-900 text-white border-zinc-900 dark:bg-emerald-600 dark:border-emerald-600'
                              : 'bg-white hover:bg-zinc-100 text-zinc-700 border-zinc-300 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 dark:border-gray-600'
                          }`}
                          aria-pressed={selected}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                  <div className="flex items-center gap-2 mt-2 text-[12px] text-zinc-600 dark:text-zinc-300">
                    <span className="font-medium">Selected:</span>
                    <span>{beautyBodyParts.length ? beautyBodyParts.join(', ') : 'None'}</span>
                    <div className="ml-auto flex items-center gap-2">
                      <button
                        type="button"
                        className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 underline"
                        onClick={() => {
                          setBeautyBodyParts([...(BEAUTY_PROCEDURE_DEFAULTS[beautyProcedureType] || [])]);
                        }}
                      >
                        Reset to {currentProcedureLabel} defaults
                      </button>
                      <button
                        type="button"
                        className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 underline"
                        onClick={() => {
                          setBeautyBodyParts([]);
                        }}
                      >
                        Clear all
                      </button>
                    </div>
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-1">
                    We pre-select areas that pair best with {currentProcedureLabel.toLowerCase()}. Tap any chip to fine-tune the focus.
                  </p>
                </div>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Custom Sign Overrides (optional)</label>
                  <input
                    type="text"
                    className="px-2 py-1 border rounded w-full text-sm"
                    value={beautyBodySigns}
                    onChange={e=>setBeautyBodySigns(e.target.value)}
                    placeholder="Libra, Taurus"
                  />
                  <p className="text-[11px] text-zinc-500 mt-1">
                    Use when you already know the exact zodiac signs to avoid (adds their opposite signs automatically).
                  </p>
                </div>
                <div className="md:col-span-2 flex flex-wrap items-center gap-3 text-sm">
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeTraditionalTiming} onChange={e=>setIncludeTraditionalTiming(e.target.checked)} />
                    Add planetary day/hour context
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeFixedStars} onChange={e=>setIncludeFixedStars(e.target.checked)} />
                    Include fixed star screening (1° orb)
                  </label>
                </div>
                <div className="md:col-span-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                  The beautification model enforces Moon sign exclusions, Venus/Mercury/Mars retrograde checks, eclipse buffers, and natal promise gates when a saved chart is supplied.
                </div>
              </>
            )}
            {matter==='conception' && (
              <>
                <div className="md:col-span-2 text-xs">
                  {natalAvailable ? (
                    <p className="text-emerald-700 dark:text-emerald-400">
                      Natal overlay active — fertility directions, SR/LR windows, and transit harmony join the transit scoring.
                    </p>
                  ) : (
                    <p className="text-zinc-500 dark:text-zinc-400">
                      Add a saved snap to enable natal fertility checks (5th house promise, directions, returns). Transit-only screening remains available without it.
                    </p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Guidance</label>
                  <ul className="text-[11px] text-zinc-600 space-y-0.5 pl-4 list-disc">
                    <li>Prefer a waxing Moon in fertile signs (Cancer, Scorpio, Pisces, Taurus) supporting the 5th house.</li>
                    <li>Secure benefics on the 5th cusp or a dignified 5th ruler linking with the Ascendant or Moon.</li>
                    <li>Keep malefics off the 1st/5th/7th axis and avoid a combust or heavily afflicted Moon.</li>
                    <li>When natal data is supplied, the scan weighs fertility directions plus Solar/Lunar return support.</li>
                  </ul>
                </div>
                <div className="md:col-span-2 flex flex-wrap items-center gap-3 text-sm">
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeTraditionalTiming} onChange={e=>setIncludeTraditionalTiming(e.target.checked)} />
                    Add planetary day/hour context
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeFixedStars} onChange={e=>setIncludeFixedStars(e.target.checked)} />
                    Include fixed star screening (1°)
                  </label>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Sex focus (optional)</label>
                  <div className="flex flex-wrap items-center gap-3 text-sm">
                    {[
                      { value: '', label: 'None (balanced)' },
                      { value: 'male', label: 'Masculine testimonies (boy)' },
                      { value: 'female', label: 'Feminine testimonies (girl)' },
                    ].map(opt => (
                      <label key={opt.value || 'any'} className="inline-flex items-center gap-2">
                        <input
                          type="radio"
                          name="conception-gender"
                          checked={(genderPref || '') === opt.value}
                          onChange={() => setGenderPref(opt.value)}
                        />
                        {opt.label}
                      </label>
                    ))}
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-1">
                    Applies classical rules (Asc/5th/Moon/lot) to bias toward the selected sex; results still list highest overall fertility.
                  </p>
                </div>
              </>
            )}
            {matter==='lunar_fertility' && (
              <>
                <div className="md:col-span-2 text-xs">
                  {natalAvailable ? (
                    <p className="text-emerald-700 dark:text-emerald-400">
                      Saved natal chart selected. The scan will use its Sun-Moon phase signature.
                    </p>
                  ) : (
                    <p className="text-zinc-500 dark:text-zinc-400">
                      Select a saved natal chart below. This model requires natal Sun and Moon longitudes.
                    </p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Consider</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { value: 'phase', label: 'Phase' },
                      { value: 'phase_and_antiphase', label: 'Phase + Antiphase' },
                      { value: 'antiphase', label: 'Antiphase' },
                    ].map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        className={`px-3 py-1 text-sm rounded-full border transition-colors ${lunarFertilityConsiderMode === option.value ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600'}`}
                        onClick={() => setLunarFertilityConsiderMode(option.value)}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Level %</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    className="px-2 py-1 border rounded w-full"
                    value={lunarFertilityLevelPercent}
                    onChange={(e) => setLunarFertilityLevelPercent(Number(e.target.value || 33))}
                  />
                </div>
                <div className="md:col-span-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                  {LUNAR_FERTILITY_DESCRIPTION}
                </div>
              </>
            )}
            {matter==='viral' && (
              <>
                <div className="md:col-span-2 text-xs">
                  {natalAvailable ? (
                    <p className="text-emerald-700 dark:text-emerald-400">Natal overlay active via selected snap — harmonising 11th house rulers, SR/LR triggers, and transit hits.</p>
                  ) : (
                    <p className="text-zinc-500 dark:text-zinc-400">Add a saved snap under Natal source to layer natal harmonisation; without it the scan uses transits only.</p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Guidance</label>
                  <ul className="text-[11px] text-zinc-600 space-y-0.5 pl-4 list-disc">
                    <li>Favor benefics on 1st/11th, Mercury direct, and a waxing Moon.</li>
                    <li>Without a natal snap the engine hunts universal viral weather signatures.</li>
                    <li>Selecting a snap layers natal 11th rulers, SR/LR activations, and key transit hits automatically.</li>
                  </ul>
                </div>
                <div className="md:col-span-2 flex flex-wrap items-center gap-3 text-sm">
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeTraditionalTiming} onChange={e=>setIncludeTraditionalTiming(e.target.checked)} />
                    Add planetary day/hour context
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeFixedStars} onChange={e=>setIncludeFixedStars(e.target.checked)} />
                    Include fixed star screening (1°)
                  </label>
                </div>
              </>
            )}
            {matter==='legal' && (
              <>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Action Type</label>
                  <div className="flex flex-wrap items-center gap-3 text-sm">
                    <label className="inline-flex items-center gap-2">
                      <input type="radio" name="legal-action" checked={legalAction==='filing'} onChange={()=>setLegalAction('filing')} />
                      Filing / initiating
                    </label>
                    <label className="inline-flex items-center gap-2">
                      <input type="radio" name="legal-action" checked={legalAction==='response'} onChange={()=>setLegalAction('response')} />
                      Responding / defensive
                    </label>
                    <label className="inline-flex items-center gap-2">
                      <input type="radio" name="legal-action" checked={legalAction==='counter'} onChange={()=>setLegalAction('counter')} />
                      Counter-filing
                    </label>
                  </div>
                </div>
                <div className="md:col-span-2 text-xs">
                  {natalAvailable ? (
                    <p className="text-emerald-700 dark:text-emerald-400">Natal overlay active via selected snap — directions/returns are blended into the score.</p>
                  ) : (
                    <p className="text-zinc-500 dark:text-zinc-400">Add a saved snap under Natal source to enforce natal promise checks; otherwise results consider transits only.</p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Guidance</label>
                  <ul className="text-[11px] text-zinc-600 space-y-0.5 pl-4 list-disc">
                    <li>Cardinal Ascendant with a dignified, direct ruler anchors offensive filings.</li>
                    <li>Moon must avoid 6/8/12th houses and apply to benefics or the ASC ruler.</li>
                    <li>Selecting a snap layers Morin's hierarchy (directions, returns, transits) automatically.</li>
                  </ul>
                </div>
                <div className="md:col-span-2 flex flex-wrap items-center gap-3 text-sm">
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeTraditionalTiming} onChange={e=>setIncludeTraditionalTiming(e.target.checked)} />
                    Add planetary day/hour context
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={includeFixedStars} onChange={e=>setIncludeFixedStars(e.target.checked)} />
                    Include fixed star screening (1°)
                  </label>
                </div>
              </>
            )}
            {matter==='business' && (
              <>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Business Options</label>
                  <div className="flex flex-wrap items-center gap-3">
                    <label className={isBusinessBeta ? 'hidden' : 'inline-flex items-center gap-2 text-sm'}>
                      <input type="checkbox" checked={includeLunationScreen} onChange={e=>setIncludeLunationScreen(e.target.checked)} />
                      Last Lunation screen
                    </label>
                    <label className={isBusinessBeta ? 'hidden' : 'inline-flex items-center gap-2 text-sm'}>
                      <input type="checkbox" checked={includeFixedStars} onChange={e=>setIncludeFixedStars(e.target.checked)} />
                      Fixed stars (1°) on angles/keys
                    </label>
                    <label className="inline-flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={isBusinessBeta || includeTraditionalTiming}
                        disabled={isBusinessBeta}
                        onChange={e=>setIncludeTraditionalTiming(e.target.checked)}
                      />
                      {isBusinessBeta ? 'Traditional timing (planetary hour)' : 'Traditional timing (weekday + hour)'}
                    </label>
                    <label className={isBusinessBeta ? 'hidden' : 'inline-flex items-center gap-2 text-sm'}>
                      <input type="checkbox" checked={emphasizeCommerce} onChange={e=>setEmphasizeCommerce(e.target.checked)} />
                      Emphasize commerce (Mercury)
                    </label>
                    <div className={isBusinessBeta ? 'hidden' : 'inline-flex items-center gap-2 text-sm'}>
                      <span>Mode</span>
                      <select className="px-2 py-1 border rounded" value={businessMode} onChange={e=>setBusinessMode(e.target.value)}>
                        <option value="">Default</option>
                        <option value="conservative">Conservative</option>
                        <option value="growth">Growth</option>
                      </select>
                    </div>
                  </div>
                  {isBusinessBeta && (
                    <>
                      <p className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                        Beta always applies planetary hour checks and hides alpha-only overlays that are not part of the source business model.
                      </p>
                      <div className="mt-3 rounded-xl border border-zinc-200 bg-zinc-50/80 p-3 dark:border-gray-700 dark:bg-gray-900/40">
                        <div className="text-[11px] uppercase tracking-[0.24em] text-zinc-500 dark:text-zinc-400">Period extraction</div>
                        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                          <div>
                            <label className="block text-xs text-zinc-600 mb-1">Mode</label>
                            <select
                              className="px-2 py-1 border rounded w-full"
                              value={businessBetaDisplayMode}
                              onChange={(e) => setBusinessBetaDisplayMode(e.target.value)}
                            >
                              <option value="total">Show total</option>
                              <option value="detail">Show detail</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs text-zinc-600 mb-1">Line scope</label>
                            <select
                              className="px-2 py-1 border rounded w-full"
                              value={businessBetaScope}
                              onChange={(e) => setBusinessBetaScope(e.target.value)}
                            >
                              <option value="all">All lines</option>
                              <option value="current">Current line</option>
                              <option value="selected">Selected subset</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs text-zinc-600 mb-1">Threshold %</label>
                            <input
                              type="number"
                              min="0"
                              max="100"
                              step="1"
                              className="px-2 py-1 border rounded w-full"
                              value={businessBetaLevelPercent}
                              onChange={(e) => setBusinessBetaLevelPercent(Number(e.target.value || 67))}
                            />
                          </div>
                        </div>
                        {businessBetaScope === 'current' && (
                          <div className="mt-3">
                            <label className="block text-xs text-zinc-600 mb-1">Current line</label>
                            <select
                              className="px-2 py-1 border rounded w-full"
                              value={businessBetaCurrentLineId}
                              onChange={(e) => setBusinessBetaCurrentLineId(e.target.value)}
                            >
                              {businessBetaLineOptions.map((option) => (
                                <option key={option.id} value={option.id}>{option.label}</option>
                              ))}
                            </select>
                          </div>
                        )}
                        {businessBetaScope === 'selected' && (
                          <div className="mt-3">
                            <label className="block text-xs text-zinc-600 mb-1">Selected lines</label>
                            <div className="flex flex-wrap gap-2">
                              {businessBetaLineOptions.map((option) => {
                                const checked = businessBetaSelectedLineIds.includes(option.id);
                                return (
                                  <label
                                    key={option.id}
                                    className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[12px] ${
                                      checked
                                        ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-200 dark:bg-zinc-100 dark:text-zinc-900'
                                        : 'border-zinc-300 bg-white text-zinc-700 dark:border-gray-600 dark:bg-gray-800 dark:text-zinc-200'
                                    }`}
                                  >
                                    <input
                                      type="checkbox"
                                      className="hidden"
                                      checked={checked}
                                      onChange={() => {
                                        setBusinessBetaSelectedLineIds((current) => {
                                          const next = Array.isArray(current) ? [...current] : [];
                                          if (next.includes(option.id)) {
                                            const filtered = next.filter((lineId) => lineId !== option.id);
                                            return filtered.length ? filtered : [option.id];
                                          }
                                          return [...next, option.id];
                                        });
                                      }}
                                    />
                                    <span>{option.label}</span>
                                  </label>
                                );
                              })}
                            </div>
                          </div>
                        )}
                        <p className="mt-3 text-[11px] text-zinc-500 dark:text-zinc-400">
                          Selected founder-owner charts are treated as certified in this beta path, so Ascendant resonance, Fortuna-to-Asc, and Asc-ruler placement stay active without adding new snap metadata.
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </>
            )}
            {matter==='contract' && (
              <>
                <div className="md:col-span-2">
                  <label className="block text-xs mb-1">Contract Options</label>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="inline-flex items-center gap-2 text-sm">
                      <span>Context</span>
                      <select className="px-2 py-1 border rounded" value={contractMode} onChange={e=>setContractMode(e.target.value)}>
                        <option value="">New (default)</option>
                        <option value="renew">Re-sign / Renew</option>
                        <option value="amend">Revise / Amend</option>
                        <option value="finalize">Finalize long-negotiated</option>
                      </select>
                    </div>
                    <label className="inline-flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={preferFixedAsc} onChange={e=>setPreferFixedAsc(e.target.checked)} />
                      Prefer fixed Asc
                    </label>
                    <label className="inline-flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={saturnBindingOk} onChange={e=>setSaturnBindingOk(e.target.checked)} />
                      Allow Saturn binding (dignified)
                    </label>
                    <div className="inline-flex items-center gap-2 text-sm">
                      <span>Min days after Mercury direct</span>
                      <input type="number" min="0" step="1" className="px-2 py-1 border rounded w-20" value={minMercuryDirectDays}
                        onChange={e=> setMinMercuryDirectDays(Number(e.target.value||0))} />
                    </div>
                    <label className="inline-flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={includeFixedStars} onChange={e=>setIncludeFixedStars(e.target.checked)} />
                      Fixed stars (1°) on angles/keys
                    </label>
                  </div>
                </div>
              </>
            )}
            <div>
              <label className="block text-xs mb-1">Timezone (optional)</label>
              <input type="text" className="px-3 py-1 border rounded w-full" placeholder="e.g., Europe/London" value={timezone} onChange={e=>setTimezone(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs mb-1">Step minutes</label>
              <input type="number" min="5" step="5" className="px-3 py-1 border rounded w-full" value={stepMinutes} onChange={e=>setStepMinutes(Number(e.target.value||60))} />
            </div>
            <div>
              <label className="block text-xs mb-1">Limit</label>
              <input type="number" min="1" max="100" className="px-3 py-1 border rounded w-full" value={limit} onChange={e=>setLimit(Number(e.target.value||15))} />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs mb-1">Days</label>
              <div className="flex flex-wrap gap-1">
                {ALL_WEEKDAYS.map(d => (
                  <button key={d} type="button" className={`px-2 py-0.5 rounded-full border text-[11px] ${weekdays.includes(d)?'bg-zinc-800 text-white border-zinc-800':''}`} onClick={()=> {
                    const next = (() => {
                      const set = new Set(weekdays);
                      if (set.has(d)) set.delete(d); else set.add(d);
                      return ALL_WEEKDAYS.filter((day) => set.has(day));
                    })();
                    updateWeekdaySelection(next);
                  }}>
                    {d.charAt(0).toUpperCase()+d.slice(1)}
                  </button>
                ))}
                <button type="button" className={`px-2 py-0.5 rounded-full border text-[11px] ${weekdayMode === 'all' ? 'bg-zinc-800 text-white border-zinc-800' : ''}`} onClick={()=> updateWeekdaySelection(ALL_WEEKDAYS, 'all')}>All</button>
                <button type="button" className={`px-2 py-0.5 rounded-full border text-[11px] ${weekdayMode === 'none' ? 'bg-zinc-800 text-white border-zinc-800' : ''}`} onClick={()=> updateWeekdaySelection([], 'none')}>None</button>
              </div>
            </div>
            <div>
              <label className="block text-xs mb-1">Hours (local) — from</label>
              <input
                type="time"
                lang="en-GB"
                inputMode="numeric"
                step="60"
                placeholder="HH:MM"
                className="px-3 py-1 border rounded w-full"
                value={hourStart}
                onChange={e=>setHourStart(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs mb-1">Hours (local) — to</label>
              <input
                type="time"
                lang="en-GB"
                inputMode="numeric"
                step="60"
                placeholder="HH:MM"
                className="px-3 py-1 border rounded w-full"
                value={hourEnd}
                onChange={e=>setHourEnd(e.target.value)}
              />
            </div>
            {isMarriageBeta ? (
              <>
                <div className="md:col-span-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                  {MARRIAGE_BETA_PARTICIPANT_HELP}
                </div>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Saved chart A</label>
                  <select className="px-2 py-1 border rounded w-full" value={participantASnapId} onChange={e=>setParticipantASnapId(e.target.value)} disabled={!hasSavedSnaps}>
                    <option value="">{hasSavedSnaps ? 'Select saved chart' : 'No saved charts found'}</option>
                    {snaps.map(s => (
                      <option key={s.id} value={s.id}>{formatSavedSnapLabel(s)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Saved chart B</label>
                  <select className="px-2 py-1 border rounded w-full" value={participantBSnapId} onChange={e=>setParticipantBSnapId(e.target.value)} disabled={!hasSavedSnaps}>
                    <option value="">{hasSavedSnaps ? 'Select saved chart' : 'No saved charts found'}</option>
                    {snaps.map(s => (
                      <option key={s.id} value={s.id}>{formatSavedSnapLabel(s)}</option>
                    ))}
                  </select>
                </div>
              </>
            ) : isBusinessBeta ? (
              <>
                <div className="md:col-span-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                  {BUSINESS_BETA_PARTICIPANT_HELP}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Founder / owner charts</label>
                  <div className="max-h-56 overflow-auto rounded-xl border border-zinc-200 bg-zinc-50/80 p-2 dark:border-gray-700 dark:bg-gray-900/40">
                    {!hasSavedSnaps ? (
                      <div className="px-2 py-3 text-sm text-zinc-500 dark:text-zinc-400">No saved charts found.</div>
                    ) : (
                      <div className="space-y-1">
                        {snaps.map((snap) => {
                          const snapId = String(snap.id || '');
                          const checked = businessParticipantSnapIds.includes(snapId);
                          return (
                            <label
                              key={snapId}
                              className={`flex items-start gap-3 rounded-lg border px-3 py-2 text-sm transition-colors ${checked ? 'border-zinc-900 bg-white dark:border-zinc-200 dark:bg-zinc-800' : 'border-transparent bg-white/70 hover:border-zinc-300 dark:bg-zinc-900/60 dark:hover:border-zinc-600'}`}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => toggleBusinessParticipantSnapId(snapId)}
                              />
                              <span>{formatSavedSnapLabel(snap)}</span>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </div>
                  <p className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                    {businessParticipantSnapIds.length
                      ? `${businessParticipantSnapIds.length} founder-owner chart${businessParticipantSnapIds.length === 1 ? '' : 's'} selected.`
                      : 'Select at least one saved chart for founder-owner fit scoring.'}
                  </p>
                </div>
              </>
            ) : isEstateMatter ? (
              <>
                <div className="md:col-span-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                  {ESTATE_PARTICIPANT_HELP}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-zinc-600 mb-1">Buyer / seller chart</label>
                  <select
                    className="px-2 py-1 border rounded w-full"
                    value={estateParticipantSnapId}
                    onChange={(e) => setEstateParticipantSnapId(e.target.value)}
                    disabled={!hasSavedSnaps}
                  >
                    <option value="">{hasSavedSnaps ? 'Select saved chart' : 'No saved charts found'}</option>
                    {snaps.map((snap) => (
                      <option key={snap.id} value={snap.id}>{formatSavedSnapLabel(snap)}</option>
                    ))}
                  </select>
                  <p className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                    {estateParticipantSnapId
                      ? `${estateDirection === 'sell' ? 'Seller' : 'Buyer'} fit line will use the selected saved chart.`
                      : `Select one saved chart for ${estateDirection === 'sell' ? 'seller' : 'buyer'} fit scoring.`}
                  </p>
                </div>
              </>
            ) : (
              <>
                {!isLunarFertilityMatter && (
                <div className="flex items-center gap-2 mt-5">
              <input id="sr-lr" type="checkbox" checked={includeSrLr} disabled={!natalAvailable} onChange={e=>setIncludeSrLr(e.target.checked)} />
              <label htmlFor="sr-lr" className={`text-sm ${!natalAvailable ? 'opacity-60' : ''}`}>Include SR/LR weighting</label>
              {!natalAvailable && (
                <span className="text-xs text-zinc-500" title="Requires a natal source (saved snap)">Requires natal</span>
              )}
            </div>
                )}
            <div>
              <label className="block text-xs text-zinc-600 mb-1">Natal source</label>
              <div className="flex items-center gap-3 text-sm">
                {!isLunarFertilityMatter && (
                  <label className="flex items-center gap-1"><input type="radio" name="elsrc" checked={sourceMode==='none'} onChange={()=>{ setSourceMode('none'); setIncludeSrLr(false); }} /> None</label>
                )}
                <label className="flex items-center gap-1"><input type="radio" name="elsrc" checked={sourceMode==='snap'} onChange={()=>setSourceMode('snap')} /> Saved chart</label>
              </div>
            </div>
            {sourceMode==='snap' && (
              <div>
                <label className="block text-xs text-zinc-600 mb-1">Saved chart</label>
                <select className="px-2 py-1 border rounded w-full" value={selectedSnapId} onChange={e=>setSelectedSnapId(e.target.value)} disabled={!hasSavedSnaps}>
                  <option value="">{hasSavedSnaps ? 'Select saved chart' : 'No saved charts found'}</option>
                  {snaps.map(s => (
                    <option key={s.id} value={s.id}>{formatSavedSnapLabel(s)}</option>
                  ))}
                </select>
              </div>
            )}
              </>
            )}
          </div>

          <div className="flex items-center gap-2 mb-2">
            <button className="px-4 py-1.5 rounded bg-zinc-900 text-white disabled:opacity-50" disabled={loading} onClick={doScan}>Scan</button>
            {loading && (
              <span className="text-xs text-zinc-500">
                Scanning…{(rangeStartDate && rangeEndDate) ? ` (step ${stepMinutes}m)` : ''}
              </span>
            )}
            {error && <span className="text-xs text-red-600">{error}</span>}
          </div>
          {loading || progress > 0 ? (
            <div className="mb-3">
              <div className="h-2 w-full bg-zinc-200 dark:bg-gray-700 rounded overflow-hidden">
                <div className="h-full bg-zinc-900 transition-all" style={{ width: `${Math.max(0, Math.min(progress, 1))*100}%` }} />
              </div>
            </div>
          ) : null}

          {timelineSeries.length > 0 ? (
            <div className="mb-4 rounded-2xl border border-zinc-200 bg-zinc-50/80 dark:bg-gray-900/40 dark:border-gray-700 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.24em] text-zinc-700 dark:text-zinc-300">Scan timeline</div>
                  <div className="mt-1 text-sm text-zinc-600 dark:text-zinc-300">
                    {Number(result?.stats?.series_retained || retainedSeries.length)} retained windows across the scan.
                  </div>
                  {lineExtraction ? (
                    <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                      {Number(lineExtraction.period_count || 0)} extracted period{Number(lineExtraction.period_count || 0) === 1 ? '' : 's'} • {lineExtraction.display_mode === 'detail' ? 'Show detail' : 'Show total'} • {lineExtraction.scope === 'current' ? 'Current line' : lineExtraction.scope === 'selected' ? 'Selected subset' : 'All lines'}
                    </div>
                  ) : hasLunarFertilityResult ? (
                    <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                      {lunarFertilityPeriods.length} period{lunarFertilityPeriods.length === 1 ? '' : 's'} at or above {Number(result?.level_percent || 0).toFixed(0)}%.
                    </div>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2 text-[11px]">
                  <div className="rounded-full border border-zinc-300 bg-white px-3 py-1 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200">
                    Peak {Number(seriesScoreRange.max || 0).toFixed(2)}
                  </div>
                  <div className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-zinc-600 dark:border-gray-700 dark:bg-gray-800 dark:text-zinc-300">
                    Retained {Number(result?.stats?.series_retained || retainedSeries.length)}
                  </div>
                  <div className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-zinc-600 dark:border-gray-700 dark:bg-gray-800 dark:text-zinc-300">
                    Attempted {Number(result?.stats?.attempted || 0)}
                  </div>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-zinc-200 bg-white/90 p-3 dark:border-gray-700 dark:bg-gray-900/70">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                  <span>{formatShortTs(timelineSeries[0]?.timestamp_local || timelineSeries[0]?.timestamp, result?.timezone)}</span>
                  <span>{formatShortTs(timelineSeries[timelineSeries.length - 1]?.timestamp_local || timelineSeries[timelineSeries.length - 1]?.timestamp, result?.timezone)}</span>
                </div>
                <div className="overflow-x-auto pb-2">
                  <div className="flex h-40 min-w-max items-end gap-[3px] px-1">
                    {displaySeries.map((row, idx) => {
                      const score = Number(row.score || 0);
                      const min = Number(seriesScoreRange.min || 0);
                      const max = Number(seriesScoreRange.max || 0);
                      const ratio = max <= min ? 1 : (score - min) / (max - min);
                      const barHeight = Math.max(18, Math.round(24 + ratio * 102));
                      const isSelected = selectedSeriesRow?.timestamp === row.timestamp;
                      const isPeak = peakSeriesRows.some((peak) => peak.timestamp === row.timestamp);
                      const passesLineExtraction = Boolean(row?.[extractionPassKey]);
                      return (
                        <button
                          key={`${row.timestamp || idx}-${idx}`}
                          type="button"
                          title={`${formatTs(row.timestamp_local || row.timestamp, result?.timezone)} | Score ${score.toFixed(2)}`}
                          onClick={() => setSelectedSeriesTimestamp(row.timestamp)}
                          className={`group relative flex w-3.5 items-end rounded-full border transition-all ${
                            isSelected
                              ? 'border-zinc-500 bg-zinc-100 dark:bg-zinc-800/80'
                              : passesLineExtraction
                                ? 'border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/20'
                                : isPeak
                                ? 'border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30'
                                : 'border-zinc-200 bg-zinc-50 dark:border-gray-700 dark:bg-gray-800'
                          }`}
                          style={{ height: `${barHeight}px` }}
                        >
                          <span
                            className={`block w-full rounded-full ${
                              isSelected
                                ? 'bg-zinc-700 dark:bg-zinc-200'
                                : passesLineExtraction
                                  ? 'bg-emerald-500'
                                  : isPeak
                                  ? 'bg-emerald-500'
                                  : 'bg-zinc-500 dark:bg-zinc-400'
                            }`}
                            style={{ height: `${Math.max(12, barHeight - 10)}px` }}
                          />
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                  {peakSeriesRows.map((row) => (
                    <button
                      key={`peak-${row.timestamp}`}
                      type="button"
                      onClick={() => setSelectedSeriesTimestamp(row.timestamp)}
                      className={`rounded-full border px-2.5 py-1 transition-colors ${
                        selectedSeriesRow?.timestamp === row.timestamp
                          ? 'border-zinc-500 bg-zinc-100 text-zinc-800 dark:border-zinc-500 dark:bg-zinc-800 dark:text-zinc-100'
                          : 'border-zinc-200 bg-white text-zinc-600 dark:border-gray-700 dark:bg-gray-800 dark:text-zinc-300'
                      }`}
                    >
                      {formatShortTs(row.timestamp_local || row.timestamp, result?.timezone)}
                    </button>
                  ))}
                </div>
              </div>

              {selectedSeriesRow ? (() => {
                const { pros, cautions } = splitRowTags(selectedSeriesRow, 5, 4);
                const lineRows = Array.isArray(selectedSeriesRow?.lines) ? selectedSeriesRow.lines : [];
                return (
                  <div className="mt-4 grid gap-3 md:grid-cols-[1.4fr_1fr]">
                    <div className="rounded-xl border border-zinc-200 bg-white/90 p-3 dark:border-gray-700 dark:bg-gray-900/70">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-[11px] uppercase tracking-[0.24em] text-zinc-500 dark:text-zinc-400">Selected window</div>
                          <div className="mt-1 font-medium text-sm">{formatTs(selectedSeriesRow.timestamp_local || selectedSeriesRow.timestamp, result?.timezone)}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-[11px] uppercase tracking-[0.24em] text-zinc-500 dark:text-zinc-400">
                            {lineExtraction ? 'Selected signal' : 'Score'}
                          </div>
                          <div className="mt-1 text-2xl font-semibold">{Number(selectedSeriesRow.score || 0).toFixed(2)}</div>
                          {lineExtraction && Number.isFinite(Number(selectedSeriesRow.aggregate_score)) ? (
                            <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                              Aggregate {Number(selectedSeriesRow.aggregate_score || 0).toFixed(2)}
                            </div>
                          ) : null}
                        </div>
                      </div>
                      {lineExtraction ? (
                        <div className="mt-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                          Threshold {Number(selectedSeriesRow?.[extractionThresholdKey] || 0).toFixed(2)} • {selectedSeriesRow?.[extractionPassKey] ? 'passes extraction cut' : 'below extraction cut'}
                        </div>
                      ) : null}
                      {hasLunarFertilityResult ? (
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                          <span>{selectedSeriesRow.phase_kind === 'antiphase' ? 'Antiphase' : 'Phase'}</span>
                          <span>{selectedSeriesRow.sex_label === 'male' ? 'Male sign' : selectedSeriesRow.sex_label === 'female' ? 'Female sign' : 'Unknown sign'}</span>
                          {selectedSeriesRow.moon_sign ? <span>Moon in {selectedSeriesRow.moon_sign}</span> : null}
                          {selectedSeriesRow.anchor_offset_hours != null ? <span>{Number(selectedSeriesRow.anchor_offset_hours).toFixed(1)}h from anchor</span> : null}
                        </div>
                      ) : null}
                      {pros.length > 0 ? (
                        <div className="mt-3 text-[11px] text-emerald-700 dark:text-emerald-300">
                          <span className="uppercase tracking-wide mr-1">Pros:</span>
                          <span>{pros.join(' · ')}</span>
                        </div>
                      ) : null}
                      {cautions.length > 0 ? (
                        <div className="mt-2 text-[11px] text-rose-700 dark:text-rose-300">
                          <span className="uppercase tracking-wide mr-1">Cautions:</span>
                          <span>{cautions.join(' · ')}</span>
                        </div>
                      ) : null}
                      <div className="mt-3 flex items-center gap-2">
                        <button
                          className="px-3 py-1.5 rounded border text-[12px]"
                          onClick={() => jumpToElectionRow(selectedSeriesRow)}
                        >
                          Jump
                        </button>
                      </div>
                      {lineRows.length > 0 ? (
                        <div className="mt-4 border-t border-zinc-200 pt-3 dark:border-gray-700">
                          <div className="text-[11px] uppercase tracking-[0.24em] text-zinc-500 dark:text-zinc-400">{lineModelLabel}</div>
                          <div className="mt-3 space-y-3">
                            {lineRows.map((line, idx) => {
                              const { pros: linePros, cautions: lineCautions } = splitRowTags(line, 3, 2);
                              return (
                                <div key={`${line.id || line.label || idx}-${idx}`} className="rounded-lg border border-zinc-200/80 bg-zinc-50/80 px-3 py-2 dark:border-gray-700 dark:bg-gray-800/60">
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="text-sm font-medium text-zinc-800 dark:text-zinc-100">{line.label || line.kind || `Line ${idx + 1}`}</div>
                                    <div className="text-sm font-semibold text-zinc-700 dark:text-zinc-200">{Number(line.score || 0).toFixed(2)}</div>
                                  </div>
                                  <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                                    <span>Favorable {Number(line.favorable || 0).toFixed(2)}</span>
                                    <span>Tense {Number(line.tense || 0).toFixed(2)}</span>
                                    {line.kind === 'participant' ? (
                                      <span>{line.precision_class === 'certified' ? (estateExtraction ? 'Certified estate chart' : 'Certified founder chart') : `Precision: ${line.precision_class || 'unknown'}`}</span>
                                    ) : null}
                                  </div>
                                  {linePros.length > 0 ? (
                                    <div className="mt-2 text-[11px] text-emerald-700 dark:text-emerald-300">
                                      <span className="uppercase tracking-wide mr-1">Pros:</span>
                                      <span>{linePros.join(' · ')}</span>
                                    </div>
                                  ) : null}
                                  {lineCautions.length > 0 ? (
                                    <div className="mt-1 text-[11px] text-rose-700 dark:text-rose-300">
                                      <span className="uppercase tracking-wide mr-1">Cautions:</span>
                                      <span>{lineCautions.join(' · ')}</span>
                                    </div>
                                  ) : null}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ) : null}
                    </div>
                    <div className="rounded-xl border border-zinc-200 bg-white/90 p-3 dark:border-gray-700 dark:bg-gray-900/70">
                      <div className="text-[11px] uppercase tracking-[0.24em] text-zinc-500 dark:text-zinc-400">
                        {lineExtraction ? 'Extracted periods' : hasLunarFertilityResult ? 'Lunar periods' : 'Peak windows'}
                      </div>
                      {lineExtraction ? (
                        <div className="mt-3 space-y-2">
                          {extractedPeriods.length ? extractedPeriods.map((period) => (
                            <button
                              key={period.id || `${period.start}-${period.end}`}
                              type="button"
                              onClick={() => {
                                if (period.best_timestamp) setSelectedSeriesTimestamp(period.best_timestamp);
                              }}
                              className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left transition-colors ${
                                selectedSeriesRow?.timestamp === period.best_timestamp
                                  ? 'border-zinc-500 bg-zinc-100 dark:border-zinc-500 dark:bg-zinc-800/80'
                                  : 'border-zinc-200 bg-white dark:border-gray-700 dark:bg-gray-800'
                              }`}
                            >
                              <span className="text-sm">
                                {period.start === period.end
                                  ? formatShortTs(period.start_local || period.start, result?.timezone)
                                  : `${formatShortTs(period.start_local || period.start, result?.timezone)} → ${formatShortTs(period.end_local || period.end, result?.timezone)}`}
                              </span>
                              <span className="text-sm font-medium">{Number(period.best_score || 0).toFixed(2)}</span>
                            </button>
                          )) : (
                            <div className="rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-sm text-zinc-500 dark:border-gray-700 dark:text-zinc-400">
                              No extracted periods survived the current threshold and line-scope settings.
                            </div>
                          )}
                        </div>
                      ) : hasLunarFertilityResult ? (
                        <div className="mt-3 space-y-2">
                          {lunarFertilityPeriods.length ? lunarFertilityPeriods.map((period) => (
                            <button
                              key={period.id || `${period.start}-${period.end}`}
                              type="button"
                              onClick={() => {
                                if (period.best_timestamp) setSelectedSeriesTimestamp(period.best_timestamp);
                              }}
                              className={`flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left transition-colors ${
                                selectedSeriesRow?.timestamp === period.best_timestamp
                                  ? 'border-zinc-500 bg-zinc-100 dark:border-zinc-500 dark:bg-zinc-800/80'
                                  : 'border-zinc-200 bg-white dark:border-gray-700 dark:bg-gray-800'
                              }`}
                            >
                              <span className="text-sm">
                                {`${formatShortTs(period.start_local || period.start, result?.timezone)} -> ${formatShortTs(period.end_local || period.end, result?.timezone)}`}
                              </span>
                              <span className="text-right text-[11px] text-zinc-500 dark:text-zinc-400">
                                <span className="block font-medium text-zinc-700 dark:text-zinc-200">{Number(period.best_score || 0).toFixed(2)}</span>
                                <span>{period.phase_kind === 'antiphase' ? 'Antiphase' : 'Phase'} / {period.sex_label || 'unknown'}</span>
                              </span>
                            </button>
                          )) : (
                            <div className="rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-sm text-zinc-500 dark:border-gray-700 dark:text-zinc-400">
                              No periods reached the selected level.
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="mt-3 space-y-2">
                          {peakSeriesRows.map((row, idx) => (
                            <button
                              key={`peak-row-${row.timestamp}-${idx}`}
                              type="button"
                              onClick={() => setSelectedSeriesTimestamp(row.timestamp)}
                              className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left transition-colors ${
                                selectedSeriesRow?.timestamp === row.timestamp
                                  ? 'border-zinc-500 bg-zinc-100 dark:border-zinc-500 dark:bg-zinc-800/80'
                                  : 'border-zinc-200 bg-white dark:border-gray-700 dark:bg-gray-800'
                              }`}
                            >
                              <span className="text-sm">{formatShortTs(row.timestamp_local || row.timestamp, result?.timezone)}</span>
                              <span className="text-sm font-medium">{Number(row.score || 0).toFixed(2)}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })() : null}
            </div>
          ) : null}

          {Array.isArray(top) && top.length > 0 ? (
            <>
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-[11px] uppercase tracking-[0.24em] text-zinc-500 dark:text-zinc-400">
                  {lineExtraction ? 'Top extracted windows' : hasLunarFertilityResult ? 'Top lunar fertility hours' : 'Top ranked windows'}
                </div>
                <div className="text-[11px] text-zinc-500 dark:text-zinc-400">{top.length} rows</div>
              </div>
              <div className="max-h-72 overflow-auto border rounded p-2 bg-white/60 dark:bg-gray-900/40">
              {top.map((r, idx) => {
                const { pros, cautions } = splitRowTags(r, 4, 3);
                return (
                  <div key={idx} className="py-2 border-b last:border-0">
                    <div className="flex items-center gap-2">
                      <div className="font-medium text-sm w-56">{formatTs(r.timestamp_local || r.timestamp, result?.timezone)}</div>
                      <div className="text-sm">
                        {lineExtraction ? 'Signal' : 'Score'}: <span className="font-semibold">{Number(r.score).toFixed(2)}</span>
                      </div>
                      <button className="ml-auto px-2 py-1 rounded border text-[12px]" onClick={() => jumpToElectionRow(r)}>Jump</button>
                    </div>
                    {(pros.length>0) && (
                      <div className="mt-1 text-[11px] text-emerald-700 dark:text-emerald-300">
                        <span className="uppercase tracking-wide mr-1">Pros:</span>
                        <span className="opacity-90">{pros.join(' · ')}</span>
                      </div>
                    )}
                    {(cautions.length>0) && (
                      <div className="text-[11px] text-rose-700 dark:text-rose-300">
                        <span className="uppercase tracking-wide mr-1">Cautions:</span>
                        <span className="opacity-90">{cautions.join(' · ')}</span>
                      </div>
                    )}
                  </div>
                );
              })}
              </div>
            </>
          ) : timelineSeries.length > 0 && lineExtraction ? (
            <div className="text-xs text-zinc-500">
              No extracted top windows survived the current threshold and line-scope settings.
            </div>
          ) : (
            <div className="text-xs text-zinc-500">
              No results yet.
              {result?.stats ? (
                <>
                  {(result.stats?.kept_total === 0) && (
                    <span> Try widening Day/Hour filters.</span>
                  )}
                  {(result.stats?.kept_total > 0 && result.stats?.attempted === 0) && (
                    <span> No steps attempted; check timezone/location.</span>
                  )}
                  {(result.stats?.failed >= (result.stats?.kept_total||0) && (result.stats?.kept_total||0) > 0) && (
                    <span> All steps failed; see backend log.</span>
                  )}
                </>
              ) : null}
            </div>
          )}

          {(Array.isArray(top) && top.length > 0) ? (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button className="px-2 py-1 rounded border text-[12px]" onClick={doDownloadTopLocal}>Download Top (CSV)</button>
              {hasLunarFertilityResult ? (
                <button className="px-2 py-1 rounded border text-[12px]" onClick={doExportLunarFertilityReport}>Export Fertility Report</button>
              ) : null}
              {reportStatus ? (
                <span className="text-[11px] text-zinc-500 dark:text-zinc-400">{reportStatus}</span>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
