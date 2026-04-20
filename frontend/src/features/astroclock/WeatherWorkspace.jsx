import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AstroClockAPI } from './api.mjs';
import {
  ConsoleBracketEyebrow,
  ConsoleCommandBand,
  ConsoleDataRow,
  ConsoleEmptyState,
  ConsoleKpiStrip,
  ConsoleModeTabs,
  ConsoleRailSection,
  ConsoleSectionBar,
  ConsoleStatusBadge,
  ResearchMetricPill,
  ResearchQuickChoiceChips,
  ResearchSectionIntro,
  ResearchSegmentedToggle,
  ResearchSummaryBand,
  getResearchAccent,
  researchWorkspaceCls,
  toneBadgeClass,
} from './researchWorkspacePrimitives.jsx';

let weatherCatalogCache = null;
let weatherCatalogPromise = null;
let weatherScanCatalogCache = null;
let weatherScanCatalogPromise = null;
const WEATHER_MODULE = 'weather';

function normalizeId(value) {
  return String(value || '').trim().toLowerCase().replace(/\s+/g, '_');
}

function formatLabel(value) {
  const raw = String(value || '').trim();
  if (!raw) return 'Unknown';
  return raw
    .replace(/_/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function buildDateTime(date, time) {
  const safeDate = String(date || '').trim();
  const safeTime = String(time || '').trim();
  if (!safeDate) return '';
  if (!safeTime) return `${safeDate}T00:00:00`;
  return `${safeDate}T${safeTime.length === 5 ? `${safeTime}:00` : safeTime}`;
}

function formatDateTime(value) {
  const raw = String(value || '').trim();
  if (!raw) return 'Unknown time';
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleString();
}

function formatTimelineTick(value) {
  const raw = String(value || '').trim();
  if (!raw) return 'Unknown';
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDateTimeRange(startValue, endValue) {
  const start = String(startValue || '').trim();
  const end = String(endValue || '').trim();
  if (!start && !end) return 'Unknown time';
  if (!start) return formatDateTime(end);
  if (!end || start === end) return formatDateTime(start);
  return `${formatDateTime(start)} - ${formatDateTime(end)}`;
}

function estimateTimeSlices(startValue, endValue, stepHours) {
  const start = new Date(String(startValue || ''));
  const end = new Date(String(endValue || ''));
  const step = Number(stepHours || 0);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || step <= 0) return null;
  if (end <= start) return 0;
  const diffMs = end.getTime() - start.getTime();
  return Math.floor(diffMs / (step * 60 * 60 * 1000)) + 1;
}

function levelTone(level) {
  const value = normalizeId(level);
  if (value === 'active' || value === 'critical' || value === 'high') return 'danger';
  if (value === 'elevated') return 'warning';
  if (value === 'watch') return 'accent';
  if (value === 'quiet') return 'good';
  return 'default';
}

function formatScalar(value, digits = 2) {
  if (value == null || value === '') return null;
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(digits).replace(/\.?0+$/, '');
  }
  return String(value);
}

function buildDetailChips(data, ignoredKeys = []) {
  if (!data || typeof data !== 'object') return [];
  const ignored = new Set(ignoredKeys.map((key) => String(key)));
  return Object.entries(data)
    .filter(([key, value]) => !ignored.has(key) && value != null && value !== '' && !Array.isArray(value) && typeof value !== 'object')
    .slice(0, 6)
    .map(([key, value]) => `${formatLabel(key)}: ${formatScalar(value)}`);
}

function formatPercent(value, total) {
  const numericValue = Number(value || 0);
  const numericTotal = Number(total || 0);
  if (!(numericValue >= 0) || !(numericTotal > 0)) return '0%';
  return `${Math.round((numericValue / numericTotal) * 100)}%`;
}

function sparklinePoints(values, width = 160, height = 52, padding = 5) {
  const numericValues = values.map((value) => Number(value || 0));
  if (!numericValues.length) return { line: '', area: '', coords: [] };
  const max = Math.max(...numericValues, 1);
  const step = numericValues.length === 1 ? 0 : (width - padding * 2) / (numericValues.length - 1);
  const coords = numericValues.map((value, index) => {
    const x = padding + (step * index);
    const y = height - padding - ((value / max) * (height - padding * 2));
    return [x, y];
  });
  const line = coords.map(([x, y]) => `${x},${y}`).join(' ');
  const area = [`${padding},${height - padding}`, ...coords.map(([x, y]) => `${x},${y}`), `${padding + (step * (numericValues.length - 1))},${height - padding}`].join(' ');
  return { line, area, coords };
}

function peakLabelMeta(item) {
  const selection = normalizeId(item?.peak_selection);
  if (selection === 'peak_plateau' || selection === 'recurring_equal_peaks') {
    return {
      title: 'Peak window',
      label: formatDateTimeRange(item?.peak_window_start_datetime, item?.peak_window_end_datetime),
    };
  }
  return {
    title: 'Peak',
    label: item?.peak_datetime ? formatDateTime(item.peak_datetime) : 'Unknown time',
  };
}

function pointInPeakWindow(item, datetime) {
  const current = String(datetime || '').trim();
  const start = String(item?.peak_window_start_datetime || '').trim();
  const end = String(item?.peak_window_end_datetime || '').trim();
  if (!current || !start) return false;
  if (!end || start === end) return current === start;
  return current >= start && current <= end;
}

function formatMatrixBoundaryLabel(value) {
  const raw = String(value || '').trim();
  if (!raw) return 'Unknown';
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return `${parsed.toLocaleString([], { month: 'short', day: 'numeric' })} · ${parsed.toLocaleString([], { hour: '2-digit' })}`;
}

function matrixHeaderParts(value) {
  const raw = String(value || '').trim();
  if (!raw) return { dateLabel: 'Unknown', timeLabel: '' };
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return { dateLabel: raw, timeLabel: '' };
  return {
    dateLabel: parsed.toLocaleString([], { month: 'short', day: 'numeric' }),
    timeLabel: parsed.toLocaleString([], { hour: '2-digit', minute: '2-digit' }),
  };
}

const WEATHER_SCAN_LEVEL_META = {
  dominant: {
    shortLabel: 'DOM',
    label: 'Dominant',
    cellClass: 'border-rose-200/90 bg-rose-100/85 text-rose-800 dark:border-rose-500/40 dark:bg-rose-500/14 dark:text-rose-100',
    badgeClass: 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/35 dark:bg-rose-500/10 dark:text-rose-100',
    barColor: '#f43f5e',
  },
  co_leading: {
    shortLabel: 'CO',
    label: 'Co-leading',
    cellClass: 'border-cyan-200/90 bg-cyan-100/90 text-cyan-800 dark:border-cyan-500/40 dark:bg-cyan-500/14 dark:text-cyan-100',
    badgeClass: 'border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-500/35 dark:bg-cyan-500/10 dark:text-cyan-100',
    barColor: '#0891b2',
  },
  leading: {
    shortLabel: 'LEAD',
    label: 'Leading',
    cellClass: 'border-amber-200/90 bg-amber-100/88 text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/14 dark:text-amber-100',
    badgeClass: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/35 dark:bg-amber-500/10 dark:text-amber-100',
    barColor: '#d97706',
  },
  active: {
    shortLabel: 'ACT',
    label: 'Active',
    cellClass: 'border-teal-200/90 bg-teal-100/88 text-teal-800 dark:border-teal-500/40 dark:bg-teal-500/14 dark:text-teal-100',
    badgeClass: 'border-teal-200 bg-teal-50 text-teal-700 dark:border-teal-500/35 dark:bg-teal-500/10 dark:text-teal-100',
    barColor: '#0f766e',
  },
  watch: {
    shortLabel: 'W',
    label: 'Watch',
    cellClass: 'border-slate-200/90 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-900/35 dark:text-slate-200',
    badgeClass: 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-900/35 dark:text-slate-200',
    barColor: '#64748b',
  },
  background: {
    shortLabel: 'Q',
    label: 'Quiet',
    cellClass: 'border-slate-200/80 bg-white text-slate-400 dark:border-slate-800 dark:bg-slate-950/35 dark:text-slate-500',
    badgeClass: 'border-slate-200 bg-white text-slate-500 dark:border-slate-800 dark:bg-slate-950/35 dark:text-slate-300',
    barColor: '#94a3b8',
  },
};

function weatherScanLevelMeta(point) {
  const normalized = normalizeId(point?.scan_level || point?.level);
  if (WEATHER_SCAN_LEVEL_META[normalized]) return WEATHER_SCAN_LEVEL_META[normalized];
  const score = Number(point?.score || 0);
  if (score <= 0) return WEATHER_SCAN_LEVEL_META.background;
  if (score >= 36) return WEATHER_SCAN_LEVEL_META.dominant;
  if (score >= 24) return WEATHER_SCAN_LEVEL_META.leading;
  if (score >= 12) return WEATHER_SCAN_LEVEL_META.active;
  return WEATHER_SCAN_LEVEL_META.watch;
}

function timelineIndexFor(indexMap, value) {
  const key = String(value || '').trim();
  if (!key || !indexMap.has(key)) return null;
  return indexMap.get(key);
}

function peakWindowLayout(item, timeline, timelineIndexMap) {
  const timelineLength = Array.isArray(timeline) ? timeline.length : 0;
  const lastIndex = Math.max(0, timelineLength - 1);
  const peakIndex = timelineIndexFor(timelineIndexMap, item?.peak_datetime);
  let startIndex = timelineIndexFor(timelineIndexMap, item?.peak_window_start_datetime);
  let endIndex = timelineIndexFor(timelineIndexMap, item?.peak_window_end_datetime);
  if (startIndex == null) startIndex = peakIndex ?? 0;
  if (endIndex == null) endIndex = peakIndex ?? startIndex;
  if (endIndex < startIndex) {
    const swapIndex = startIndex;
    startIndex = endIndex;
    endIndex = swapIndex;
  }
  if (timelineLength <= 1) {
    return { left: '0%', width: '100%', markerLeft: '50%' };
  }
  const denominator = Math.max(1, lastIndex);
  const leftPercent = (startIndex / denominator) * 100;
  const rawWidth = ((endIndex - startIndex) / denominator) * 100;
  const widthPercent = Math.min(100 - leftPercent, Math.max(rawWidth, 8));
  const markerPercent = ((peakIndex ?? startIndex) / denominator) * 100;
  return {
    left: `${leftPercent}%`,
    width: `${widthPercent}%`,
    markerLeft: `${markerPercent}%`,
  };
}

const {
  railCardCls,
  sectionCardCls,
  nestedCardCls,
  emptyStateCls,
  headerBandCls,
  sectionBandCls,
  mutedPanelCls,
  inputCls,
  actionButtonCls,
  secondaryActionButtonCls,
  primaryActionButtonCls,
} = researchWorkspaceCls;
const WEATHER_SCAN_PROGRESS_POLL_MS = 800;
const weatherAccent = getResearchAccent(WEATHER_MODULE);

function WorkspaceModeToggle({ value, onChange }) {
  const options = [{ id: 'scan', label: 'Scan' }, { id: 'analysis', label: 'Analysis' }];
  return <ConsoleModeTabs options={options} value={value} onChange={onChange} />;
}

function ScanScopeToggle({ value, onChange }) {
  const options = [{ id: 'place_timeline', label: 'Specific Place' }, { id: 'region_timeline', label: 'Region' }];
  return <ConsoleModeTabs options={options} value={value} onChange={onChange} />;
}

function ResultViewToggle({ value, onChange }) {
  const options = [{ id: 'graph', label: 'Matrix' }, { id: 'dates', label: 'Dates' }];
  return <ConsoleModeTabs options={options} value={value} onChange={onChange} />;
}

function QuickChoiceChips({ items, value, onChange }) {
  return <ResearchQuickChoiceChips items={items} value={value} onChange={onChange} />;
}

function SectionIntro(props) {
  return <ResearchSectionIntro {...props} module={WEATHER_MODULE} />;
}

function MetricPill(props) {
  return <ResearchMetricPill {...props} />;
}

function SummaryList({ items, emptyText = 'No items.' }) {
  const rows = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!rows.length) return <p className="text-sm text-slate-500 dark:text-slate-400">{emptyText}</p>;
  return (
    <div className="space-y-3">
      {rows.map((item, index) => {
        const data = item && typeof item === 'object' ? item : { value: item };
        const label = data.label || data.title || data.id || `Item ${index + 1}`;
        const summary = data.summary || data.description || '';
        const chips = buildDetailChips(data, ['id', 'label', 'title', 'summary', 'description']);
        return (
          <div key={`${label}-${index}`} className={nestedCardCls}>
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{label}</div>
              {data.score != null ? (
                <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] ${toneBadgeClass(levelTone(data.level || (Number(data.score) >= 24 ? 'elevated' : 'watch')))}`}>
                  Score {formatScalar(data.score)}
                </span>
              ) : null}
            </div>
            {summary ? <p className="mt-1.5 text-sm leading-6 text-slate-600 dark:text-slate-300">{summary}</p> : null}
            {chips.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {chips.map((chip) => (
                  <span key={chip} className="rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300">
                    {chip}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function SourceList({ title, sources }) {
  const rows = Array.isArray(sources) ? sources.filter(Boolean) : [];
  if (!rows.length) return null;
  return (
    <section className={sectionCardCls}>
      <SectionIntro eyebrow="Sources" title={title} />
      <div className="mt-4 space-y-3">
        {rows.map((source, index) => {
          const label = source.title || source.label || source.id || `Source ${index + 1}`;
          const summary = source.scope_note || source.summary || source.description || '';
          const chips = buildDetailChips(source, ['id', 'title', 'label', 'scope_note', 'summary', 'description']);
          return (
            <div key={`${label}-${index}`} className={nestedCardCls}>
              <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{label}</div>
              {summary ? <p className="mt-1.5 text-sm leading-6 text-slate-600 dark:text-slate-300">{summary}</p> : null}
              {chips.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {chips.map((chip) => (
                    <span key={chip} className="rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300">
                      {chip}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function NoteList({ title, notes }) {
  const rows = Array.isArray(notes) ? notes.filter(Boolean) : [];
  if (!rows.length) return null;
  return (
    <section className={sectionCardCls}>
      <SectionIntro eyebrow="Notes" title={title} />
      <div className="mt-4 space-y-3">
        {rows.map((note, index) => {
          const label = note.title || note.label || note.id || `Note ${index + 1}`;
          const summary = note.summary || note.excerpt || note.watchpoint || '';
          return (
            <div key={`${label}-${index}`} className={nestedCardCls}>
              <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{label}</div>
              {summary ? <p className="mt-1.5 text-sm leading-6 text-slate-600 dark:text-slate-300">{summary}</p> : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Sparkline({ values, tone = 'accent', peakIndex = null, peakLabel = '', peakTitle = 'Peak' }) {
  const numericValues = Array.isArray(values) ? values.map((value) => Number(value || 0)) : [];
  const { line, area, coords } = sparklinePoints(numericValues);
  const palette =
    tone === 'danger'
      ? { stroke: '#f43f5e', fill: 'rgba(244,63,94,0.16)' }
      : tone === 'warning'
        ? { stroke: '#f59e0b', fill: 'rgba(245,158,11,0.16)' }
        : { stroke: '#0ea5e9', fill: 'rgba(14,165,233,0.16)' };
  const highlightCoord = Number.isInteger(peakIndex) && peakIndex >= 0 && peakIndex < coords.length ? coords[peakIndex] : null;
  if (!line) return <div className="h-14 rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-900/30" />;
  return (
    <div className="rounded-2xl border border-slate-200/85 bg-slate-50/85 p-2 dark:border-slate-700 dark:bg-slate-900/30">
      {peakLabel ? (
        <div className="mb-2 flex items-center justify-between gap-2 px-1">
          <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">{peakTitle}</span>
          <span className="text-[10px] font-medium text-slate-600 dark:text-slate-300">{peakLabel}</span>
        </div>
      ) : null}
      <svg viewBox="0 0 160 52" className="h-14 w-full">
        <polygon points={area} fill={palette.fill} />
        <polyline points={line} fill="none" stroke={palette.stroke} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {highlightCoord ? (
          <>
            <circle cx={highlightCoord[0]} cy={highlightCoord[1]} r="4.5" fill="white" stroke={palette.stroke} strokeWidth="2" />
            <circle cx={highlightCoord[0]} cy={highlightCoord[1]} r="1.75" fill={palette.stroke} />
          </>
        ) : null}
      </svg>
    </div>
  );
}

function ContextPanel({ context }) {
  const family = context?.family || {};
  const eventContext = context?.event_context || {};
  const chartResolution = context?.chart_resolution || {};
  const primaryChart = chartResolution?.primary_chart || {};
  const supportingCharts = Array.isArray(chartResolution?.supporting_charts) ? chartResolution.supporting_charts : [];
  const contextFlags = Array.isArray(context?.research_flags) ? context.research_flags.filter(Boolean) : [];
  return (
    <section className={sectionCardCls}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Resolved Context</div>
          <h4 className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-50">{family.label || 'Weather Context'}</h4>
        </div>
        <span className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.12em] ${toneBadgeClass(levelTone(family.status || 'watch'))}`}>
          {formatLabel(family.status || 'seed_runtime')}
        </span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricPill label="Family" value={family.label || 'Unknown'} tone="accent" />
        <MetricPill label="Forecast Time" value={formatDateTime(eventContext.forecast_datetime)} tone="default" />
        <MetricPill label="Location" value={eventContext.location || 'Current Astro Clock location'} tone="default" />
        <MetricPill label="Timezone" value={eventContext.timezone || 'Current Astro Clock timezone'} tone="default" />
      </div>

      <div className="mt-4 space-y-3">
        <div className={nestedCardCls}>
          <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Primary Chart</div>
          <div className="mt-2 text-sm font-medium text-slate-900 dark:text-slate-50">{primaryChart.label || 'Forecast Chart'}</div>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            {formatDateTime(primaryChart.computed_datetime)} {primaryChart.location ? `| ${primaryChart.location}` : ''}
          </p>
        </div>
        {supportingCharts.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {supportingCharts.map((chart, index) => (
              <div key={`${chart.kind || chart.label || 'support'}-${index}`} className={nestedCardCls}>
                <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                  {chart.kind ? formatLabel(chart.kind) : `Supporting Chart ${index + 1}`}
                </div>
                <div className="mt-2 text-sm font-medium text-slate-900 dark:text-slate-50">{chart.label || `Supporting Chart ${index + 1}`}</div>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                  {formatDateTime(chart.computed_datetime)} {chart.location ? `| ${chart.location}` : ''}
                </p>
              </div>
            ))}
          </div>
        ) : null}
        {contextFlags.length ? (
          <div className="flex flex-wrap gap-2">
            {contextFlags.map((flag) => (
              <span key={flag} className="rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 text-[11px] uppercase tracking-[0.12em] text-slate-600 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300">
                {formatLabel(flag)}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function LayerPanel({ layer }) {
  if (!layer) return null;
  return (
    <section className={sectionCardCls}>
      <SectionIntro eyebrow="Layer" title={layer.label || 'Layer'} />
      <div className="mt-4">
        <SummaryList items={layer.items} emptyText="No matched items for this layer." />
      </div>
    </section>
  );
}

function CalibrationPanel({ assessment, research }) {
  const calibration = research?.calibration || {};
  const flags = Array.isArray(research?.flags) ? research.flags.filter(Boolean) : [];
  const limitations = Array.isArray(research?.limitations) ? research.limitations.filter(Boolean) : [];
  return (
    <section className={sectionCardCls}>
      <SectionIntro eyebrow="Calibration" title="Runtime Coverage" />
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <MetricPill label="Level" value={formatLabel(assessment?.level || 'quiet')} tone={levelTone(assessment?.level)} />
        <MetricPill label="Score" value={formatScalar(assessment?.score) || '0'} tone={levelTone(assessment?.level)} />
        <MetricPill label="Coverage" value={formatLabel(calibration.coverage_tier || 'seeded')} tone="accent" />
        <MetricPill label="Cases" value={formatScalar(calibration.unique_case_count) || '0'} tone="default" />
      </div>
      <div className="mt-4 space-y-1 text-sm text-slate-600 dark:text-slate-300">
        <div>Dataset rows: {formatScalar(calibration.dataset_row_count) || '0'}</div>
        <div>Source breadth: {formatScalar(calibration.source_count) || '0'}</div>
        <div>Runtime scope: {formatLabel(research?.runtime_scope || research?.status || 'seed_runtime')}</div>
      </div>
      {flags.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {flags.map((flag) => (
            <span key={flag} className="rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 text-[11px] uppercase tracking-[0.12em] text-slate-600 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300">
              {formatLabel(flag)}
            </span>
          ))}
        </div>
      ) : null}
      {limitations.length ? (
        <div className="mt-4 space-y-2">
          <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Limitations</div>
          <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
            {limitations.map((item) => (
              <li key={item} className={nestedCardCls}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function WeatherScanExecutionPanel({ result, progress, running }) {
  if (!result && !progress && !running) return null;
  const counts = result?.counts || progress?.counts || {};
  const percent = Math.max(0, Math.min(100, Math.round(Number(progress?.percent || (result ? 1 : 0)) * 100)));
  const candidateCount = progress?.candidate_count ?? counts.candidate_count ?? 0;
  const evaluated = progress?.evaluated ?? counts.evaluated ?? progress?.done ?? 0;
  const returned = progress?.returned ?? counts.returned ?? 0;
  const statusLabel = running ? 'Running' : progress?.failed ? 'Failed' : progress?.ready || result ? 'Ready' : 'Queued';
  const title = progress?.message || (running ? 'Weather scan running' : 'Weather scan complete');
  return (
    <section className={sectionCardCls}>
      <ConsoleSectionBar
        module={WEATHER_MODULE}
        label="execution"
        right={<ConsoleStatusBadge label={statusLabel} tone={running ? 'accent' : progress?.failed ? 'danger' : 'good'} />}
      />
      <div className="mt-3 text-lg font-semibold text-slate-900 dark:text-slate-50">{title}</div>
      <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div
          className={`h-full rounded-full transition-all ${progress?.failed ? 'bg-rose-500' : ''}`}
          style={{ width: `${percent}%`, background: progress?.failed ? undefined : weatherAccent.line }}
        />
      </div>
      <div className="mt-4">
        <ConsoleKpiStrip
          module={WEATHER_MODULE}
          metrics={[
            { label: 'Percent', value: `${percent}%`, toneColor: weatherAccent.ink, bar: percent, barColor: weatherAccent.line },
            { label: 'Candidates', value: candidateCount },
            { label: 'Evaluated', value: evaluated },
            { label: 'Returned', value: returned, toneColor: returned > 0 ? '#047857' : undefined },
          ]}
        />
      </div>
    </section>
  );
}

function WeatherScanSummaryPanel({ result }) {
  const overview = result?.series?.series_overview || {};
  const topCandidateLabel = overview.top_candidate_location?.label || overview.top_peak_location?.label || 'Unknown';
  const topPlace = Array.isArray(result?.series?.places) && result.series.places.length ? result.series.places[0] : null;
  const topWindowLabel = topPlace
    ? peakLabelMeta(topPlace).label
    : overview.top_candidate_datetime || overview.top_peak_datetime
      ? formatDateTime(overview.top_candidate_datetime || overview.top_peak_datetime)
      : 'Unknown';
  return (
    <section className={sectionCardCls}>
      <ConsoleSectionBar module={WEATHER_MODULE} label="scan / potential_windows" />
      <div className="mt-4">
        <ConsoleKpiStrip
          module={WEATHER_MODULE}
          metrics={[
            { label: 'Timeline', value: overview.timeline_points ?? 0, toneColor: weatherAccent.ink },
            { label: 'Places', value: overview.place_count ?? 0 },
            { label: 'Top candidate', value: topCandidateLabel, toneColor: '#92400e' },
            { label: 'Peak window', value: topWindowLabel, toneColor: '#be123c' },
          ]}
        />
      </div>
    </section>
  );
}

function WeatherScanGraphPanel({ result }) {
  const places = Array.isArray(result?.series?.places) ? result.series.places : [];
  const timeline = Array.isArray(result?.series?.timeline) ? result.series.timeline : [];
  const timelineIndexMap = new Map(timeline.map((value, index) => [String(value || '').trim(), index]));
  const gridTemplateColumns = `260px repeat(${timeline.length}, minmax(78px, 1fr))`;
  const tableMinWidth = 260 + (timeline.length * 84);
  const scanStartLabel = timeline.length ? formatMatrixBoundaryLabel(timeline[0]) : 'Unknown';
  const scanEndLabel = timeline.length ? formatMatrixBoundaryLabel(timeline[timeline.length - 1]) : 'Unknown';
  if (!places.length || !timeline.length) {
    return (
      <ConsoleEmptyState
        module={WEATHER_MODULE}
        title="No scan matrix yet"
        detail="Matrix mode opens once the scan returns timeline data."
      />
    );
  }
  return (
    <section className={sectionCardCls}>
      <ConsoleSectionBar module={WEATHER_MODULE} label="pressure_matrix" />
      <div
        className="mt-4 rounded-[4px] border border-slate-200/90 bg-white/96 shadow-none dark:border-slate-700/90 dark:bg-slate-900/88"
        style={{ maxHeight: '560px', overflow: 'auto', scrollbarGutter: 'stable both-edges' }}
      >
        <div className="min-w-max" style={{ minWidth: `${tableMinWidth}px` }}>
          <div
            className="sticky top-0 z-10 grid border-b border-slate-200/90 bg-white/96 backdrop-blur dark:border-slate-700 dark:bg-slate-950/94"
            style={{
              gridTemplateColumns,
              borderTop: `2px solid ${weatherAccent.line}`,
            }}
          >
            <div className="border-r border-slate-200/80 px-4 py-3 dark:border-slate-700/80">
              <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Location · Peak Window
              </div>
            </div>
            {timeline.map((timepoint) => {
              const header = matrixHeaderParts(timepoint);
              return (
                <div
                  key={timepoint}
                  className="flex min-h-[82px] flex-col justify-end border-r border-slate-100/90 px-2 pb-3 pt-2 text-center last:border-r-0 dark:border-slate-800/80"
                >
                  <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                    {header.dateLabel}
                  </div>
                  <div className="mt-2 text-[11px] font-medium text-slate-800 dark:text-slate-100">{header.timeLabel}</div>
                </div>
              );
            })}
          </div>
          {places.map((place, index) => {
            const series = Array.isArray(place?.series) ? place.series : [];
            const pointMap = new Map(series.map((point) => [String(point?.datetime || '').trim(), point]));
            const peakMeta = peakLabelMeta(place);
            const windowLayout = peakWindowLayout(place, timeline, timelineIndexMap);
            const peakPoint = pointMap.get(String(place?.peak_datetime || '').trim())
              || series.reduce((best, point) => (
                Number(point?.score || 0) > Number(best?.score || 0) ? point : best
              ), null);
            const peakLevel = weatherScanLevelMeta(peakPoint);
            return (
              <div
                key={`${place.location?.label || 'place'}-${index}`}
                className="grid border-b border-slate-200/70 bg-white/94 last:border-b-0 dark:border-slate-700/70 dark:bg-slate-950/20"
                style={{ gridTemplateColumns, contentVisibility: 'auto' }}
              >
                <div className={`border-r border-slate-200/80 px-4 py-4 dark:border-slate-700/80 ${index === 0 ? 'border-l-2 border-slate-900 dark:border-slate-50' : ''}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-serif text-[1.1rem] font-medium tracking-[-0.02em] text-slate-900 dark:text-slate-50">
                        {place.location?.label || 'Unknown place'}
                      </div>
                      <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">{peakMeta.label}</div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Peak</div>
                      <div className="mt-1 text-[1.5rem] font-semibold leading-none text-slate-900 dark:text-slate-50">
                        {place.peak_score ?? 0}
                      </div>
                    </div>
                  </div>
                    <div className="mt-4">
                      <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.16em] text-slate-400 dark:text-slate-500">
                        <span>{scanStartLabel}</span>
                        <span>{scanEndLabel}</span>
                      </div>
                      <div className="relative mt-2 h-[8px] rounded-full bg-slate-200/85 dark:bg-slate-800">
                        <div
                          className="absolute top-1/2 h-[10px] -translate-y-1/2 rounded-full border border-white/80 shadow-[0_1px_2px_rgba(15,23,42,0.14)] dark:border-slate-950/70"
                          style={{ left: windowLayout.left, width: windowLayout.width, background: peakLevel.barColor }}
                        />
                        <div
                          className="absolute top-1/2 h-[16px] w-[3px] -translate-y-1/2 rounded-full shadow-[0_0_0_1px_rgba(255,255,255,0.55)] dark:shadow-[0_0_0_1px_rgba(15,23,42,0.65)]"
                          style={{ left: `calc(${windowLayout.markerLeft} - 1.5px)`, background: peakLevel.barColor }}
                        />
                      </div>
                    </div>
                  <div className="mt-3 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                    {formatLabel(place?.candidate_kind || place?.peak_selection || 'Peak window')}
                  </div>
                </div>
                {timeline.map((timepoint) => {
                  const point = pointMap.get(String(timepoint || '').trim()) || {
                    datetime: timepoint,
                    score: 0,
                    scan_level: 'background',
                  };
                  const score = Number(point?.score || 0);
                  const isPeak = pointInPeakWindow(place, timepoint);
                  const cellMeta = weatherScanLevelMeta(point);
                  return (
                    <div key={`${place.location?.label || 'place'}-${timepoint}`} className="flex items-center justify-center px-2 py-4">
                      <div
                        title={`${formatDateTime(timepoint)} | Score ${score} | ${cellMeta.label}`}
                        className={`flex h-[66px] w-full max-w-[74px] flex-col items-center justify-center rounded-[6px] border px-1.5 text-center transition ${cellMeta.cellClass} ${isPeak ? 'ring-1 ring-slate-900/20 dark:ring-white/20' : ''}`}
                      >
                        <div className="text-[18px] font-semibold leading-none tracking-[-0.03em] tabular-nums">
                          {score}
                        </div>
                        <div className="mt-2 font-mono text-[10px] font-semibold uppercase tracking-[0.16em]">
                          {cellMeta.shortLabel}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function WeatherScanDatesPanel({ result }) {
  const rows = Array.isArray(result?.results) ? result.results : [];
  const topScore = Math.max(0, ...rows.map((row) => Number(row?.score || 0)));
  if (!rows.length) {
    return (
      <ConsoleEmptyState
        module={WEATHER_MODULE}
        title="No ranked dates yet"
        detail="Returned windows will land here after the scan completes."
      />
    );
  }
  return (
    <section className={sectionCardCls}>
      <ConsoleSectionBar module={WEATHER_MODULE} label={`returned_dates / ${rows.length} ranked`} />
      <div className={`${researchWorkspaceCls.tableFrameCls} mt-4`}>
        <div className="hidden grid-cols-[52px_minmax(0,1.6fr)_130px_96px] gap-3 border-b border-slate-200/90 bg-slate-50/90 px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-400 lg:grid">
          <div>#</div>
          <div>Window</div>
          <div>Level</div>
          <div className="text-right">Score</div>
        </div>
        {rows.map((row) => (
          <article key={`${row.rank}-${row.location?.label}-${row.datetime}`} className="border-b border-slate-100/90 px-4 py-4 last:border-b-0 dark:border-slate-800/80">
            <div className={`grid gap-4 lg:grid-cols-[52px_minmax(0,1.6fr)_130px_96px] lg:items-start ${Number(row.rank) === 1 ? 'border-l-2 border-slate-900 pl-3 dark:border-slate-50' : ''}`}>
              <div className="font-mono text-xs font-semibold tracking-[0.12em] text-slate-500 dark:text-slate-400">
                {String(row.rank ?? '').padStart(2, '0')}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-base font-semibold text-slate-900 dark:text-slate-50">{row.location?.label || 'Unknown location'}</div>
                    <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                      {row.location?.country_name || row.location?.timezone || 'Weather scan'}
                    </div>
                  </div>
                  <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">{formatDateTime(row.datetime)}</div>
                </div>
                {Array.isArray(row.matched_rules) && row.matched_rules.length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {row.matched_rules.slice(0, 5).map((rule, index) => (
                      <span key={`${row.rank}-${rule.id || rule.label || index}`} className="rounded-[3px] border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
                        {rule.label || formatLabel(rule.id || `rule_${index + 1}`)}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              <div>
                <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${toneBadgeClass(levelTone(row.level))}`}>
                  {formatLabel(row.level)}
                </span>
              </div>
              <div className="lg:text-right">
                <div className="text-[1.6rem] font-semibold leading-none text-slate-900 dark:text-slate-50">{row.score}</div>
                <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                  {formatPercent(row.score, topScore)} of top
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function WeatherScanInspector({ result, resultView }) {
  const calibration = result?.calibration || {};
  const overview = result?.series?.series_overview || {};
  const peakPlace = Array.isArray(result?.series?.places) && result.series.places.length ? result.series.places[0] : null;
  const topDate = Array.isArray(result?.results) && result.results.length ? result.results[0] : null;
  const activeItem = resultView === 'dates' ? topDate : peakPlace;
  const title = resultView === 'dates' ? 'Top date' : 'Top candidate';
  if (!activeItem) {
    return (
      <ConsoleEmptyState
        module={WEATHER_MODULE}
        title="No scan output yet"
        detail="Run the scan to inspect the strongest place or date."
      />
    );
  }
  const peakMeta = resultView === 'dates'
    ? { label: formatDateTime(activeItem.datetime) }
    : peakLabelMeta(activeItem);
  return (
    <div className="space-y-4">
      <section className={sectionCardCls}>
        <ConsoleSectionBar module={WEATHER_MODULE} label="research_scope" />
        <div className="mt-1">
          <ConsoleDataRow label="Scope" value={formatLabel(result?.scope?.scan_scope || 'place_timeline')} tone={WEATHER_MODULE} />
          <ConsoleDataRow label="Resolution" value={formatLabel(result?.scope?.resolution || 'standard')} />
          <ConsoleDataRow label="Candidates" value={result?.counts?.candidate_count ?? 0} mono />
          <ConsoleDataRow label="Time slices" value={result?.counts?.time_slices ?? 0} mono />
          <ConsoleDataRow label="Evaluated" value={result?.counts?.evaluated ?? 0} mono />
          <ConsoleDataRow label="Returned" value={result?.counts?.returned ?? 0} mono strong />
        </div>
      </section>

      <section className={sectionCardCls}>
        <ConsoleSectionBar module={WEATHER_MODULE} label={`inspector / ${normalizeId(title)}`} />
        <div className="mt-3 text-xl font-semibold text-slate-900 dark:text-slate-50">{activeItem.location?.label || 'Unknown'}</div>
        <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">{peakMeta.label}</div>
        <div className="mt-4">
          <ConsoleDataRow label="Peak score" value={activeItem.peak_score ?? activeItem.score ?? 0} mono strong tone="warning" />
          <ConsoleDataRow label="Coverage" value={formatLabel(calibration.coverage_tier || 'seeded')} tone={WEATHER_MODULE} />
          <ConsoleDataRow label="Cases" value={calibration.unique_case_count ?? 0} mono />
          <ConsoleDataRow label="Timeline" value={overview.timeline_points ?? 0} mono />
        </div>
      </section>
    </div>
  );
}

export default function WeatherWorkspace({ open, defaultHouseSystem = 'R' }) {
  const [workspaceMode, setWorkspaceMode] = useState('scan');
  const [catalog, setCatalog] = useState(() => weatherCatalogCache);
  const [scanCatalog, setScanCatalog] = useState(() => weatherScanCatalogCache);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [familyId, setFamilyId] = useState('');
  const [forecastDate, setForecastDate] = useState('');
  const [forecastTime, setForecastTime] = useState('');
  const [location, setLocation] = useState('');
  const [timezone, setTimezone] = useState('');
  const [resolvedContext, setResolvedContext] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loadingResolve, setLoadingResolve] = useState(false);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [error, setError] = useState('');
  const resolveRequestIdRef = useRef(0);
  const analyzeRequestIdRef = useRef(0);

  const [scanScope, setScanScope] = useState('place_timeline');
  const [scanRegionId, setScanRegionId] = useState('global');
  const [scanResolutionId, setScanResolutionId] = useState('');
  const [scanCandidateLimit, setScanCandidateLimit] = useState('');
  const [scanTopK, setScanTopK] = useState('');
  const [scanLocation, setScanLocation] = useState('');
  const [scanTimezone, setScanTimezone] = useState('');
  const [scanStartDate, setScanStartDate] = useState('');
  const [scanStartTime, setScanStartTime] = useState('');
  const [scanEndDate, setScanEndDate] = useState('');
  const [scanEndTime, setScanEndTime] = useState('');
  const [scanStepHours, setScanStepHours] = useState('');
  const [scanLoading, setScanLoading] = useState(false);
  const [scanError, setScanError] = useState('');
  const [scanSessionId, setScanSessionId] = useState('');
  const [scanProgress, setScanProgress] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [scanView, setScanView] = useState('graph');

  const families = useMemo(() => {
    const primary = Array.isArray(catalog?.families) ? catalog.families : [];
    if (primary.length) return primary;
    return Array.isArray(scanCatalog?.families) ? scanCatalog.families : [];
  }, [catalog, scanCatalog]);
  const forecastDatetime = useMemo(() => buildDateTime(forecastDate, forecastTime), [forecastDate, forecastTime]);
  const analysisPayload = useMemo(() => ({
    familyId: familyId || undefined,
    forecastDatetime: forecastDatetime || undefined,
    location: location || undefined,
    timezone: timezone || undefined,
    houseSystem: defaultHouseSystem,
  }), [defaultHouseSystem, familyId, forecastDatetime, location, timezone]);
  const analysisRequestSignature = useMemo(() => JSON.stringify(analysisPayload), [analysisPayload]);
  const latestAnalysisSignatureRef = useRef(analysisRequestSignature);

  const scanRegions = Array.isArray(scanCatalog?.regions) ? scanCatalog.regions : [];
  const scanResolutions = Array.isArray(scanCatalog?.resolutions) ? scanCatalog.resolutions : [];
  const featuredScanRegions = useMemo(() => {
    const preferred = ['global', 'persian_gulf', 'middle_east', 'levant', 'east_asia', 'north_africa'];
    const byId = new Map(scanRegions.map((item) => [normalizeId(item?.id), item]));
    const ordered = preferred.map((id) => byId.get(id)).filter(Boolean);
    const extras = scanRegions.filter((item) => !preferred.includes(normalizeId(item?.id)));
    return [...ordered, ...extras].slice(0, 6);
  }, [scanRegions]);
  const maxTimeSlices = Number(scanCatalog?.max_time_slices || 120);
  const maxEvaluatedCells = Number(scanCatalog?.max_evaluated_cells || 720);
  const maxCandidates = Number(scanCatalog?.max_candidates || 20);
  const defaultTimeStepHours = Number(scanCatalog?.default_time_step_hours || 6);
  const defaultCandidateLimit = Number(scanCatalog?.default_candidate_limit || 6);
  const defaultTopK = Number(scanCatalog?.default_top_k || 8);

  const effectiveScanStepHours = Number(scanStepHours || defaultTimeStepHours || 6);
  const effectiveCandidateLimit = scanScope === 'place_timeline' ? 1 : Number(scanCandidateLimit || defaultCandidateLimit || 6);
  const scanStartDatetime = useMemo(() => buildDateTime(scanStartDate, scanStartTime), [scanStartDate, scanStartTime]);
  const scanEndDatetime = useMemo(() => buildDateTime(scanEndDate, scanEndTime), [scanEndDate, scanEndTime]);
  const estimatedSlices = useMemo(() => estimateTimeSlices(scanStartDatetime, scanEndDatetime, effectiveScanStepHours), [effectiveScanStepHours, scanEndDatetime, scanStartDatetime]);
  const estimatedCells = useMemo(() => {
    if (!estimatedSlices || estimatedSlices <= 0) return null;
    return estimatedSlices * effectiveCandidateLimit;
  }, [effectiveCandidateLimit, estimatedSlices]);
  const scanPayload = useMemo(() => ({
    familyId: familyId || undefined,
    scanScope,
    regionId: scanScope === 'region_timeline' ? scanRegionId || undefined : undefined,
    resolution: scanScope === 'region_timeline' ? (scanResolutionId || undefined) : undefined,
    candidateLimit: scanScope === 'region_timeline' ? (scanCandidateLimit || undefined) : undefined,
    location: scanScope === 'place_timeline' ? (scanLocation || undefined) : undefined,
    timezone: scanScope === 'place_timeline' ? (scanTimezone || undefined) : undefined,
    startDatetime: scanStartDatetime || undefined,
    endDatetime: scanEndDatetime || undefined,
    timeStepHours: scanStepHours || undefined,
    topK: scanTopK || undefined,
    houseSystem: defaultHouseSystem,
  }), [defaultHouseSystem, familyId, scanCandidateLimit, scanEndDatetime, scanLocation, scanRegionId, scanResolutionId, scanScope, scanStartDatetime, scanStepHours, scanTimezone, scanTopK]);

  const loadCatalog = useCallback(async () => {
    setLoadingCatalog(true);
    setCatalogError('');
    try {
      if (!weatherCatalogCache) {
        if (!weatherCatalogPromise) {
          weatherCatalogPromise = AstroClockAPI.listWeatherCatalog().then((res) => {
            const data = res?.success ? res.data : null;
            weatherCatalogCache = data || null;
            return weatherCatalogCache;
          }).finally(() => { weatherCatalogPromise = null; });
        }
        weatherCatalogCache = await weatherCatalogPromise;
      }
      if (!weatherScanCatalogCache) {
        if (!weatherScanCatalogPromise) {
          weatherScanCatalogPromise = AstroClockAPI.listWeatherScanCatalog().then((res) => {
            const data = res?.success ? res.data : null;
            weatherScanCatalogCache = data || null;
            return weatherScanCatalogCache;
          }).finally(() => { weatherScanCatalogPromise = null; });
        }
        weatherScanCatalogCache = await weatherScanCatalogPromise;
      }
      setCatalog(weatherCatalogCache || null);
      setScanCatalog(weatherScanCatalogCache || null);
    } catch (nextError) {
      setCatalogError(nextError?.message || 'Failed to load weather catalog.');
      setCatalog(weatherCatalogCache || null);
      setScanCatalog(weatherScanCatalogCache || null);
    } finally {
      setLoadingCatalog(false);
    }
  }, []);

  useEffect(() => { if (open) loadCatalog(); }, [loadCatalog, open]);

  useEffect(() => {
    latestAnalysisSignatureRef.current = analysisRequestSignature;
  }, [analysisRequestSignature]);

  useEffect(() => {
    if (!families.length) return;
    if (families.some((item) => normalizeId(item?.id) === normalizeId(familyId))) return;
    setFamilyId(String(families[0]?.id || ''));
  }, [families, familyId]);

  useEffect(() => {
    if (!scanCatalog) return;
    if (!scanResolutionId && scanCatalog.default_resolution) setScanResolutionId(String(scanCatalog.default_resolution));
    if (!scanStepHours && scanCatalog.default_time_step_hours) setScanStepHours(String(scanCatalog.default_time_step_hours));
    if (!scanCandidateLimit && scanCatalog.default_candidate_limit) setScanCandidateLimit(String(scanCatalog.default_candidate_limit));
    if (!scanTopK && scanCatalog.default_top_k) setScanTopK(String(scanCatalog.default_top_k));
  }, [scanCandidateLimit, scanCatalog, scanResolutionId, scanStepHours, scanTopK]);

  useEffect(() => { if (open) { setResolvedContext(null); setAnalysis(null); setError(''); } }, [familyId, forecastDate, forecastTime, location, open, timezone]);
  useEffect(() => {
    if (!open) return;
    setScanResult(null);
    setScanError('');
    setScanProgress(null);
    setScanSessionId('');
    setScanLoading(false);
  }, [familyId, open, scanCandidateLimit, scanEndDate, scanEndTime, scanLocation, scanRegionId, scanResolutionId, scanScope, scanStartDate, scanStartTime, scanStepHours, scanTimezone]);

  const handleClearOverrides = useCallback(() => {
    setForecastDate('');
    setForecastTime('');
    setLocation('');
    setTimezone('');
  }, []);

  const handleResolve = useCallback(async () => {
    if (!familyId) return setError('Choose a weather family first.');
    const requestId = resolveRequestIdRef.current + 1;
    resolveRequestIdRef.current = requestId;
    const expectedSignature = analysisRequestSignature;
    setLoadingResolve(true);
    setError('');
    try {
      const res = await AstroClockAPI.resolveWeatherContext(analysisPayload);
      if (
        resolveRequestIdRef.current !== requestId
        || latestAnalysisSignatureRef.current !== expectedSignature
      ) {
        return;
      }
      if (!res?.success) throw new Error('Failed to resolve weather context.');
      setResolvedContext(res.data?.context || null);
    } catch (nextError) {
      if (
        resolveRequestIdRef.current !== requestId
        || latestAnalysisSignatureRef.current !== expectedSignature
      ) {
        return;
      }
      setResolvedContext(null);
      setError(nextError?.message || 'Failed to resolve weather context.');
    } finally {
      if (resolveRequestIdRef.current === requestId) {
        setLoadingResolve(false);
      }
    }
  }, [analysisPayload, analysisRequestSignature, familyId]);

  const handleAnalyze = useCallback(async () => {
    if (!familyId) return setError('Choose a weather family first.');
    const requestId = analyzeRequestIdRef.current + 1;
    analyzeRequestIdRef.current = requestId;
    const expectedSignature = analysisRequestSignature;
    setLoadingAnalyze(true);
    setError('');
    try {
      const res = await AstroClockAPI.analyzeWeather(analysisPayload);
      if (
        analyzeRequestIdRef.current !== requestId
        || latestAnalysisSignatureRef.current !== expectedSignature
      ) {
        return;
      }
      if (!res?.success) throw new Error('Failed to analyze weather context.');
      setAnalysis(res.data || null);
      setResolvedContext(res.data?.context || null);
    } catch (nextError) {
      if (
        analyzeRequestIdRef.current !== requestId
        || latestAnalysisSignatureRef.current !== expectedSignature
      ) {
        return;
      }
      setAnalysis(null);
      setError(nextError?.message || 'Failed to analyze weather context.');
    } finally {
      if (analyzeRequestIdRef.current === requestId) {
        setLoadingAnalyze(false);
      }
    }
  }, [analysisPayload, analysisRequestSignature, familyId]);

  const handleRunScan = useCallback(async () => {
    if (!familyId) return setScanError('Choose a weather family first.');
    if (scanScope === 'place_timeline' && !scanLocation) return setScanError('Enter a place to scan.');
    if (scanScope === 'region_timeline' && !scanRegionId) return setScanError('Choose a region to scan.');
    if (!scanStartDatetime || !scanEndDatetime) return setScanError('Set a start and end datetime.');
    if (estimatedSlices === 0) return setScanError('End datetime must be after the start.');
    if (estimatedSlices && estimatedSlices > maxTimeSlices) return setScanError(`Weather scan is limited to ${maxTimeSlices} time slices.`);
    if (estimatedCells && estimatedCells > maxEvaluatedCells) return setScanError(`Weather scan is limited to ${maxEvaluatedCells} evaluated cells.`);
    setScanLoading(true);
    setScanError('');
    setScanProgress(null);
    setScanSessionId('');
    setScanResult(null);
    try {
      const res = await AstroClockAPI.startWeatherScan(scanPayload);
      if (!res?.success) throw new Error('Failed to start weather scan.');
      setScanProgress(res.data?.progress || null);
      setScanSessionId(String(res.data?.session_id || ''));
    } catch (nextError) {
      setScanProgress(null);
      setScanSessionId('');
      setScanResult(null);
      setScanLoading(false);
      setScanError(nextError?.message || 'Failed to run weather scan.');
    }
  }, [estimatedCells, estimatedSlices, familyId, maxEvaluatedCells, maxTimeSlices, scanEndDatetime, scanLocation, scanPayload, scanRegionId, scanScope, scanStartDatetime]);

  useEffect(() => {
    if (!open || !scanSessionId) return undefined;
    let cancelled = false;
    let timer = null;

    const poll = async () => {
      try {
        const progressRes = await AstroClockAPI.getWeatherScanProgress(scanSessionId);
        const progressData = progressRes?.success ? progressRes.data : null;
        if (cancelled) return;
        setScanProgress(progressData || null);
        if (progressData?.ready || progressData?.failed) {
          const resultRes = await AstroClockAPI.getWeatherScanResult(scanSessionId);
          const resultData = resultRes?.success ? resultRes.data : null;
          if (cancelled) return;
          if (resultData?.failed) {
            setScanError(resultData.error || 'Weather scan failed.');
            setScanResult(null);
          } else {
            setScanResult(resultData?.result || null);
            setScanView('graph');
          }
          setScanLoading(false);
          setScanSessionId('');
          return;
        }
        timer = setTimeout(poll, WEATHER_SCAN_PROGRESS_POLL_MS);
      } catch (nextError) {
        if (cancelled) return;
        setScanLoading(false);
        setScanSessionId('');
        setScanError(nextError?.message || 'Failed to load weather scan progress.');
      }
    };

    timer = setTimeout(poll, 0);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [open, scanSessionId]);

  const assessment = analysis?.family_assessment || null;
  const research = analysis?.research || null;
  const doctrine = analysis?.doctrine || null;
  const activeContext = analysis?.context || resolvedContext || null;
  const runningScan = scanLoading || Boolean(scanSessionId);
  const weatherScanSummaryItems = useMemo(() => {
    const targetValue = scanScope === 'region_timeline'
      ? scanRegions.find((item) => normalizeId(item?.id) === normalizeId(scanRegionId))?.label || ''
      : scanLocation || '';
    const densityValue = scanResolutions.find((item) => normalizeId(item?.id) === normalizeId(scanResolutionId))?.label || '';
    const windowValue = scanStartDatetime && scanEndDatetime
      ? formatDateTimeRange(scanStartDatetime, scanEndDatetime)
      : '';
    return [
      { label: 'Family', value: families.find((item) => normalizeId(item?.id) === normalizeId(familyId))?.label || '' },
      { label: 'Scope', value: scanScope === 'region_timeline' ? 'Region timeline' : 'Specific place' },
      { label: 'Target', value: targetValue },
      { label: 'Density', value: densityValue },
      { label: 'Window', value: windowValue },
      { label: 'Step', value: scanStepHours ? `${scanStepHours}h` : '' },
    ];
  }, [families, familyId, scanEndDatetime, scanLocation, scanRegionId, scanRegions, scanResolutionId, scanResolutions, scanScope, scanStartDatetime, scanStepHours]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <WorkspaceModeToggle value={workspaceMode} onChange={setWorkspaceMode} />
      </div>
      {workspaceMode === 'analysis' ? (
        <div className="grid gap-6 lg:grid-cols-[336px_minmax(0,1.75fr)_332px]">
          <aside className={`${railCardCls} space-y-4 p-4`}>
            <div className="flex items-center justify-end"><button type="button" className={actionButtonCls} onClick={loadCatalog} disabled={loadingCatalog}>{loadingCatalog ? 'Loading...' : 'Refresh'}</button></div>
            {catalogError ? <p className="text-xs text-rose-600">{catalogError}</p> : null}
            <section className={mutedPanelCls}><h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Weather Family</h4><div className="mt-2"><select className={inputCls} value={familyId} onChange={(event) => setFamilyId(event.target.value)}><option value="">Select family...</option>{families.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></div></section>
            <section className={mutedPanelCls}><h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Forecast Overrides</h4><div className="mt-2 grid grid-cols-2 gap-2"><input type="date" className={inputCls} value={forecastDate} onChange={(event) => setForecastDate(event.target.value)} /><input type="time" step="60" className={inputCls} value={forecastTime} onChange={(event) => setForecastTime(event.target.value)} /></div><div className="mt-2 space-y-2"><input type="text" className={inputCls} placeholder="Forecast location" value={location} onChange={(event) => setLocation(event.target.value)} /><input type="text" className={inputCls} placeholder="Forecast timezone" value={timezone} onChange={(event) => setTimezone(event.target.value)} /></div></section>
            <section className="flex flex-wrap gap-2"><button type="button" className={secondaryActionButtonCls} onClick={handleClearOverrides} disabled={loadingResolve || loadingAnalyze}>Clear</button><button type="button" className={secondaryActionButtonCls} onClick={handleResolve} disabled={loadingResolve || loadingAnalyze}>{loadingResolve ? 'Resolving...' : 'Resolve'}</button><button type="button" className={primaryActionButtonCls} onClick={handleAnalyze} disabled={loadingAnalyze || loadingResolve}>{loadingAnalyze ? 'Analyzing...' : 'Analyze'}</button></section>
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          </aside>
          <section className={`${railCardCls} space-y-5 p-4`}>
            <section className={headerBandCls}>
              <ConsoleBracketEyebrow module={WEATHER_MODULE}>workspace / analysis_console</ConsoleBracketEyebrow>
              <h3 className="mt-3 font-serif text-[1.9rem] font-medium tracking-[-0.04em] text-slate-900 dark:text-slate-50">Weather analysis</h3>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                Seasonal framework, trigger signals, and locality cues now sit in the same flatter research console used by the scan workbench.
              </p>
            </section>
            {activeContext ? (
              <ContextPanel context={activeContext} />
            ) : (
              <ConsoleEmptyState
                module={WEATHER_MODULE}
                title="No resolved context yet"
                detail="Resolve or analyze a family to load the forecast context."
              />
            )}
            {analysis ? (
              <>
                <section className={sectionCardCls}>
                  <ConsoleSectionBar
                    module={WEATHER_MODULE}
                    label="family_assessment"
                    right={<ConsoleStatusBadge label={formatLabel(assessment?.level || 'quiet')} tone={levelTone(assessment?.level)} />}
                  />
                  <div className="mt-3 text-lg font-semibold text-slate-900 dark:text-slate-50">{assessment?.summary || 'No weather assessment summary.'}</div>
                  <div className="mt-4">
                    <ConsoleKpiStrip
                      module={WEATHER_MODULE}
                      metrics={[
                        { label: 'Score', value: formatScalar(assessment?.score) || '0', toneColor: assessment?.level ? undefined : weatherAccent.ink },
                        { label: 'Framework', value: formatScalar(assessment?.signals?.framework_count) || '0' },
                        { label: 'Trigger', value: formatScalar(assessment?.signals?.trigger_count) || '0' },
                        { label: 'Locality', value: formatScalar(assessment?.signals?.locality_count) || '0' },
                      ]}
                    />
                  </div>
                </section>
                <LayerPanel layer={analysis.framework_layer} />
                <LayerPanel layer={analysis.trigger_layer} />
                <LayerPanel layer={analysis.locality_layer} />
              </>
            ) : null}
          </section>
          <aside className={`${railCardCls} space-y-4 p-4`}>
            <section className={headerBandCls}>
              <ConsoleBracketEyebrow module={WEATHER_MODULE}>research / sources</ConsoleBracketEyebrow>
              <h3 className="mt-2 text-base font-semibold text-slate-900 dark:text-slate-50">Calibration and sources</h3>
            </section>
            {analysis ? (
              <>
                <CalibrationPanel assessment={assessment} research={research} />
                <section className={sectionCardCls}>
                  <ConsoleSectionBar module={WEATHER_MODULE} label="matched_rules" />
                  <div className="mt-3"><SummaryList items={assessment?.matched_rules} emptyText="No matched rules for this family." /></div>
                </section>
                <SourceList title="Doctrine Sources" sources={doctrine?.sources} />
                <NoteList title="Doctrine Notes" notes={doctrine?.notes} />
              </>
            ) : (
              <ConsoleEmptyState
                module={WEATHER_MODULE}
                title="No analysis yet"
                detail="Analyze a weather family to open calibration and doctrine surfaces."
              />
            )}
          </aside>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[336px_minmax(0,1.75fr)_332px]">
          <aside className={`${railCardCls} space-y-4 p-4`}>
            <fieldset disabled={runningScan} className="m-0 space-y-4 border-0 p-0 min-w-0">
              <section className={headerBandCls}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <ConsoleBracketEyebrow module={WEATHER_MODULE}>workspace / setup_console</ConsoleBracketEyebrow>
                    <h3 className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50">Weather Scan</h3>
                  </div>
                  <button type="button" className={actionButtonCls} onClick={loadCatalog} disabled={loadingCatalog}>
                    {loadingCatalog ? 'Loading...' : 'Refresh'}
                  </button>
                </div>
              </section>
              {catalogError ? <p className="text-xs text-rose-600">{catalogError}</p> : null}

              <ConsoleRailSection title="Weather Family" eyebrow="input" module={WEATHER_MODULE} bodyClassName="mt-3">
                <select className={inputCls} value={familyId} onChange={(event) => setFamilyId(event.target.value)}>
                  <option value="">Select family...</option>
                  {families.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                </select>
              </ConsoleRailSection>

              <ConsoleRailSection title="Scan Scope" eyebrow="mode" module={WEATHER_MODULE} bodyClassName="mt-3">
                <ScanScopeToggle value={scanScope} onChange={setScanScope} />
              </ConsoleRailSection>

              {scanScope === 'region_timeline' ? (
                <ConsoleRailSection title="Region" eyebrow="target" module={WEATHER_MODULE}>
                  <QuickChoiceChips items={featuredScanRegions} value={scanRegionId} onChange={setScanRegionId} />
                  <select className={inputCls} value={scanRegionId} onChange={(event) => setScanRegionId(event.target.value)}>
                    <option value="">Select region...</option>
                    {scanRegions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                  </select>
                  <select className={inputCls} value={scanResolutionId} onChange={(event) => setScanResolutionId(event.target.value)}>
                    <option value="">Default resolution...</option>
                    {scanResolutions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                  </select>
                  <div className="grid grid-cols-2 gap-2">
                    <input type="number" min="1" max={String(maxCandidates)} className={inputCls} placeholder="Candidates" value={scanCandidateLimit} onChange={(event) => setScanCandidateLimit(event.target.value)} />
                    <input type="number" min="1" max="20" className={inputCls} placeholder="Top places" value={scanTopK} onChange={(event) => setScanTopK(event.target.value)} />
                  </div>
                </ConsoleRailSection>
              ) : (
                <ConsoleRailSection title="Specific Place" eyebrow="target" module={WEATHER_MODULE}>
                  <input type="text" className={inputCls} placeholder="Place" value={scanLocation} onChange={(event) => setScanLocation(event.target.value)} />
                  <input type="text" className={inputCls} placeholder="Timezone (optional)" value={scanTimezone} onChange={(event) => setScanTimezone(event.target.value)} />
                  <input type="number" min="1" max="20" className={inputCls} placeholder="Top dates" value={scanTopK} onChange={(event) => setScanTopK(event.target.value)} />
                </ConsoleRailSection>
              )}

              <ConsoleRailSection
                title="Time Window"
                eyebrow="window"
                module={WEATHER_MODULE}
                detail={estimatedSlices ? `${estimatedSlices} slices${estimatedCells ? ` | ${estimatedCells} cells` : ''}` : ''}
              >
                <div className="grid grid-cols-2 gap-2">
                  <input type="date" className={inputCls} value={scanStartDate} onChange={(event) => setScanStartDate(event.target.value)} />
                  <input type="time" step="60" className={inputCls} value={scanStartTime} onChange={(event) => setScanStartTime(event.target.value)} />
                  <input type="date" className={inputCls} value={scanEndDate} onChange={(event) => setScanEndDate(event.target.value)} />
                  <input type="time" step="60" className={inputCls} value={scanEndTime} onChange={(event) => setScanEndTime(event.target.value)} />
                </div>
                <input type="number" min="1" max="168" className={inputCls} placeholder="Step hours" value={scanStepHours} onChange={(event) => setScanStepHours(event.target.value)} />
              </ConsoleRailSection>

              <section className={sectionBandCls}>
                <div className="flex flex-wrap gap-2">
                  <button type="button" className={primaryActionButtonCls} onClick={handleRunScan} disabled={runningScan}>
                    {runningScan ? 'Scanning...' : 'Run Weather Scan'}
                  </button>
                  <button
                    type="button"
                    className={secondaryActionButtonCls}
                    onClick={() => {
                      setScanLocation('');
                      setScanTimezone('');
                      setScanStartDate('');
                      setScanStartTime('');
                      setScanEndDate('');
                      setScanEndTime('');
                      setScanStepHours(String(defaultTimeStepHours));
                      setScanProgress(null);
                      setScanSessionId('');
                      setScanResult(null);
                      setScanError('');
                      setScanLoading(false);
                    }}
                    disabled={runningScan}
                  >
                    Reset
                  </button>
                </div>
              </section>
            </fieldset>
            {scanError ? <p className="text-sm text-rose-600">{scanError}</p> : null}
          </aside>
          <section className={`${railCardCls} space-y-5 p-4`}>
            <section className={headerBandCls}>
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="max-w-3xl">
                  <ConsoleBracketEyebrow module={WEATHER_MODULE}>workspace / scan_console</ConsoleBracketEyebrow>
                  <h3 className="mt-3 font-serif text-[1.9rem] font-medium tracking-[-0.04em] text-slate-900 dark:text-slate-50">Weather scan and timing surfaces</h3>
                </div>
                {scanResult ? <ResultViewToggle value={scanView} onChange={setScanView} /> : null}
              </div>
            </section>
            {(runningScan || scanResult) ? (
              <ConsoleCommandBand
                module={WEATHER_MODULE}
                items={weatherScanSummaryItems}
                statusLabel={runningScan ? 'running' : 'ready'}
                statusTone={runningScan ? 'accent' : 'good'}
                trailing={scanResult ? <ResultViewToggle value={scanView} onChange={setScanView} /> : null}
              />
            ) : null}
            {runningScan || scanResult ? (
              <>
                <WeatherScanExecutionPanel result={scanResult} progress={scanProgress} running={runningScan} />
                {scanResult ? (
                  <>
                    <WeatherScanSummaryPanel result={scanResult} />
                    {scanView === 'graph' ? <WeatherScanGraphPanel result={scanResult} /> : <WeatherScanDatesPanel result={scanResult} />}
                  </>
                ) : null}
              </>
            ) : (
              <ConsoleEmptyState
                module={WEATHER_MODULE}
                title="No potential windows yet"
                detail="Set the family, scope, and window to open the scan console."
              />
            )}
          </section>
          <aside className={`${railCardCls} space-y-4 p-4`}>
            <section className={headerBandCls}>
              <ConsoleBracketEyebrow module={WEATHER_MODULE}>research / inspector</ConsoleBracketEyebrow>
              <h3 className="mt-2 text-base font-semibold text-slate-900 dark:text-slate-50">Scan inspector</h3>
            </section>
            {scanResult ? (
              <WeatherScanInspector result={scanResult} resultView={scanView} />
            ) : (
              <ConsoleEmptyState
                module={WEATHER_MODULE}
                title="No scan output yet"
                detail="Completed scan output will open the inspector scope and top-window summary here."
              />
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
