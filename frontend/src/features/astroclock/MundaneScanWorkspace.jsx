import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AstroClockAPI } from './api.mjs';
import { buildChartTypeDomainOptions, isChartTypeDomainAllowed } from './mundaneDomainProfiles.mjs';
import {
  ConsoleBracketEyebrow,
  ConsoleCommandBand,
  ConsoleDataRow,
  ConsoleEmptyState,
  ConsoleKpiStrip,
  ConsoleModeTabs,
  ConsoleSectionBar,
  ConsoleStatusBadge,
  ResearchMetricPill,
  ResearchSectionIntro,
  ResearchSegmentedToggle,
  ResearchSummaryBand,
  getResearchAccent,
  researchWorkspaceCls,
  toneBadgeClass,
} from './researchWorkspacePrimitives.jsx';

let mundaneScanCatalogCache = null;
let mundaneScanCatalogPromise = null;
const SCAN_PROGRESS_POLL_MS = 1200;
const MUNDANE_MODULE = 'mundane';

function normalizeId(value) {
  return String(value || '').trim().toLowerCase().replace(/\s+/g, '_');
}

function sameLocationLabel(left, right) {
  const leftId = normalizeId(left);
  const rightId = normalizeId(right);
  return Boolean(leftId) && leftId === rightId;
}

function scanRowSelectionKey(row) {
  const placeId = normalizeId(row?.location?.label);
  const datetime = String(row?.datetime || '').trim();
  if (!placeId && !datetime) return '';
  return `${placeId}::${datetime}`;
}

function prioritizePlaceLabel(items, activeLabel) {
  const rows = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!rows.length || !activeLabel) return rows;
  const activeIndex = rows.findIndex((item) => sameLocationLabel(item?.location?.label, activeLabel));
  if (activeIndex <= 0) return rows;
  return [rows[activeIndex], ...rows.slice(0, activeIndex), ...rows.slice(activeIndex + 1)];
}

function buildEventDatetime(date, time) {
  const safeDate = String(date || '').trim();
  const safeTime = String(time || '').trim();
  if (!safeDate) return '';
  if (!safeTime) return `${safeDate}T00:00:00`;
  return `${safeDate}T${safeTime.length === 5 ? `${safeTime}:00` : safeTime}`;
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

function formatDateTime(value) {
  const raw = String(value || '').trim();
  if (!raw) return 'Unknown time';
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleString();
}

function formatCompactDateTime(value) {
  const raw = String(value || '').trim();
  if (!raw) return 'Unknown time';
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
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

function isPeakPlateau(selection) {
  const value = normalizeId(selection);
  return value === 'peak_plateau' || value === 'recurring_equal_peaks';
}

function peakLabelMeta(item) {
  const plateau = isPeakPlateau(item?.peak_selection);
  if (plateau) {
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

function peakTickMeta(item) {
  const plateau = isPeakPlateau(item?.peak_selection);
  if (plateau) {
    return {
      title: 'Peak window',
      label: formatDateTimeRange(item?.peak_window_start_datetime, item?.peak_window_end_datetime),
      tickLabel:
        item?.peak_window_start_datetime && item?.peak_window_end_datetime
          ? `${formatTimelineTick(item.peak_window_start_datetime)} - ${formatTimelineTick(item.peak_window_end_datetime)}`
          : '',
    };
  }
  return {
    title: 'Peak',
    label: item?.peak_datetime ? formatDateTime(item.peak_datetime) : 'Unknown time',
    tickLabel: item?.peak_datetime ? formatTimelineTick(item.peak_datetime) : '',
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

function levelTone(level) {
  const value = normalizeId(level);
  if (value === 'critical' || value === 'high') return 'danger';
  if (value === 'elevated') return 'warning';
  if (value === 'quiet') return 'good';
  return 'accent';
}

function scanLevelTone(level) {
  const value = normalizeId(level);
  if (value === 'dominant') return 'danger';
  if (value === 'leading' || value === 'co_leading') return 'warning';
  if (value === 'active') return 'accent';
  if (value === 'watch') return 'good';
  return 'default';
}

function scanLevelShortLabel(level) {
  const value = normalizeId(level);
  if (value === 'dominant') return 'DOM';
  if (value === 'leading') return 'LEAD';
  if (value === 'co_leading') return 'CO';
  if (value === 'active') return 'ACT';
  if (value === 'watch') return 'W';
  return 'BG';
}

function trendToneForBreakoutKind(kind) {
  const value = normalizeId(kind);
  if (value === 'opening_break_candidate') return 'danger';
  if (value === 'campaign_pressure_candidate') return 'warning';
  return 'accent';
}

const {
  railCardCls,
  sectionCardCls,
  nestedCardCls,
  emptyStateCls,
  headerBandCls,
  mutedPanelCls,
  inputCls,
  actionButtonCls,
  primaryActionButtonCls,
  secondaryActionButtonCls,
} = researchWorkspaceCls;
const mundaneAccent = getResearchAccent(MUNDANE_MODULE);

function SectionIntro(props) {
  return <ResearchSectionIntro {...props} module={MUNDANE_MODULE} />;
}

function MetricPill(props) {
  return <ResearchMetricPill {...props} />;
}

function formatPercent(value, total) {
  const numericValue = Number(value || 0);
  const numericTotal = Number(total || 0);
  if (!(numericValue >= 0) || !(numericTotal > 0)) return '0%';
  return `${Math.round((numericValue / numericTotal) * 100)}%`;
}

function sparklinePoints(values, width = 160, height = 52, padding = 5) {
  const numericValues = values.map((value) => Number(value || 0));
  if (!numericValues.length) return { line: '', area: '', max: 0, coords: [] };
  const max = Math.max(...numericValues, 1);
  const step = numericValues.length === 1 ? 0 : (width - padding * 2) / (numericValues.length - 1);
  const coords = numericValues.map((value, index) => {
    const x = padding + (step * index);
    const y = height - padding - ((value / max) * (height - padding * 2));
    return [x, y];
  });
  const line = coords.map(([x, y]) => `${x},${y}`).join(' ');
  const area = [`${padding},${height - padding}`, ...coords.map(([x, y]) => `${x},${y}`), `${padding + (step * (numericValues.length - 1))},${height - padding}`].join(' ');
  return { line, area, max, coords };
}

function Sparkline({ values, tone = 'accent', className = '', peakIndex = null, peakLabel = '', peakTitle = 'Peak' }) {
  const numericValues = Array.isArray(values) ? values.map((value) => Number(value || 0)) : [];
  const { line, area, coords } = sparklinePoints(numericValues);
  const palette =
    tone === 'danger'
      ? { stroke: '#f43f5e', fill: 'rgba(244,63,94,0.16)' }
      : tone === 'warning'
        ? { stroke: '#f59e0b', fill: 'rgba(245,158,11,0.16)' }
        : { stroke: '#0ea5e9', fill: 'rgba(14,165,233,0.16)' };
  const highlightCoord = Number.isInteger(peakIndex) && peakIndex >= 0 && peakIndex < coords.length ? coords[peakIndex] : null;

  if (!line) {
    return <div className={`h-14 rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-900/30 ${className}`} />;
  }

  return (
    <div className={`rounded-2xl border border-slate-200/85 bg-slate-50/85 p-2 dark:border-slate-700 dark:bg-slate-900/30 ${className}`}>
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

function StatTrendCard({ label, value, caption, tone = 'accent', percent, values }) {
  return (
    <div className={`rounded-[22px] border px-4 py-4 ${toneBadgeClass(tone)}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.16em] opacity-75">{label}</div>
          <div className="mt-2 text-[1.7rem] font-semibold leading-none">{value}</div>
          {caption ? <div className="mt-2 text-[11px] uppercase tracking-[0.14em] opacity-75">{caption}</div> : null}
        </div>
        {percent ? (
          <div className="rounded-full border border-current/25 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]">
            {percent}
          </div>
        ) : null}
      </div>
      {Array.isArray(values) && values.length ? <Sparkline values={values} tone={tone} className="mt-4" /> : null}
    </div>
  );
}

function ChartSourceToggle({ value, onChange }) {
  const options = [
    { id: 'registered', label: 'Registered' },
    { id: 'custom', label: 'Custom' },
  ];
  return <ResearchSegmentedToggle options={options} value={value} onChange={onChange} />;
}

function ScanStatusBadge({ progress, running }) {
  const tone = running ? 'accent' : progress?.failed ? 'danger' : progress?.ready ? 'good' : 'default';
  const label = running ? 'Running' : progress?.failed ? 'Failed' : progress?.ready ? 'Ready' : 'Queued';
  return <ConsoleStatusBadge label={label} tone={tone} />;
}

function ScanProgressPanel({ progress, running }) {
  if (!progress && !running) return null;
  const percent = Math.max(0, Math.min(100, Math.round(Number(progress?.percent || 0) * 100)));
  return (
    <section className={sectionCardCls}>
      <div className={headerBandCls}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <ConsoleBracketEyebrow module={MUNDANE_MODULE}>execution</ConsoleBracketEyebrow>
            <h3 className="mt-3 text-[1.6rem] font-semibold tracking-[-0.03em] text-slate-900 dark:text-slate-50">
              {progress?.message || (running ? 'Running mundane scan...' : 'Scan idle')}
            </h3>
          </div>
          <ScanStatusBadge progress={progress} running={running} />
        </div>
      </div>
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className="h-full rounded-full transition-all" style={{ width: `${percent}%`, background: mundaneAccent.line }} />
      </div>
      <div className="mt-4">
        <ConsoleKpiStrip
          module={MUNDANE_MODULE}
          metrics={[
            {
              label: 'Percent',
              value: percent,
              unit: '%',
              bar: percent,
              barColor: mundaneAccent.line,
              toneColor: mundaneAccent.ink,
            },
            { label: 'Done', value: progress?.done ?? 0, unit: `/ ${progress?.total ?? 0}` },
            { label: 'Total', value: progress?.total ?? 0 },
            {
              label: 'Failures',
              value: progress?.failures ?? 0,
              toneColor: Number(progress?.failures || 0) > 0 ? '#be123c' : '#047857',
            },
          ]}
        />
      </div>
    </section>
  );
}

function ScanResultsPanel({ result }) {
  const rows = Array.isArray(result?.top_cells) ? result.top_cells : Array.isArray(result?.results) ? result.results : [];
  const places = Array.isArray(result?.series?.places) ? result.series.places : [];
  const topScanScore = Math.max(0, ...rows.map((row) => Number(row.scan_score ?? row.score ?? 0)));
  if (!rows.length) {
    return (
      <section className={emptyStateCls}>
        <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">No scan results yet</h4>
      </section>
    );
  }
  return (
    <section className={sectionCardCls}>
      <SectionIntro
        eyebrow="Top Cells"
        title={`${rows.length} ${rows.length === 1 ? 'cell' : 'cells'} returned`}
        actions={(
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-slate-600 dark:border-slate-700 dark:bg-slate-900/35 dark:text-slate-300">
            {formatLabel(result?.scan_mode || 'scan')}
          </span>
        )}
      />
      <div className="mt-5 overflow-hidden rounded-[22px] border border-slate-200/90 bg-white dark:border-slate-700 dark:bg-slate-950/30">
        <div className="hidden grid-cols-[44px_minmax(0,1.6fr)_150px_88px_88px_120px] gap-3 border-b border-slate-200/90 bg-slate-50/90 px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-400 lg:grid">
          <div>#</div>
          <div>Place</div>
          <div>Level</div>
          <div className="text-right">Scan</div>
          <div className="text-right">Raw</div>
          <div className="text-right">Lead</div>
        </div>
        {rows.map((row) => {
          const placeSeries = places.find((place) => normalizeId(place?.location?.label) === normalizeId(row.location?.label));
          const seriesValues = Array.isArray(placeSeries?.series) ? placeSeries.series.map((point) => Number(point?.scan_score || 0)) : [];
          const scanScore = Number(row.scan_score ?? row.score ?? 0);
          return (
            <article key={`${row.rank}-${row.location?.label}-${row.datetime}`} className="border-b border-slate-100/90 px-4 py-4 last:border-b-0 dark:border-slate-800/80">
              <div className="grid gap-4 lg:grid-cols-[44px_minmax(0,1.6fr)_150px_88px_88px_120px] lg:items-start">
                <div className="font-mono text-xs font-semibold tracking-[0.08em] text-slate-500 dark:text-slate-400">
                  {String(row.rank ?? '').padStart(2, '0')}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-start justify-between gap-3 lg:block">
                    <div>
                      <div className="text-base font-semibold text-slate-900 dark:text-slate-50">{row.location?.label || 'Unknown location'}</div>
                      <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                        {row.location?.country_name || row.location?.country_code || 'Unknown region'}
                        {row.location?.timezone ? ` | ${row.location.timezone}` : ''}
                      </div>
                    </div>
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400 lg:mt-2">
                      {formatDateTime(row.datetime)}
                    </div>
                  </div>
                  {Array.isArray(row.matched_rules) && row.matched_rules.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {row.matched_rules.slice(0, 4).map((rule, index) => (
                        <span key={`${row.rank}-${rule.id || rule.label || index}`} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-300">
                          {rule.label || formatLabel(rule.id || `rule_${index + 1}`)}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2 lg:block lg:space-y-2">
                  <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${toneBadgeClass(scanLevelTone(row.scan_level))}`}>
                    {formatLabel(row.scan_level || 'background')}
                  </span>
                  <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${toneBadgeClass(levelTone(row.level))}`}>
                    {formatLabel(row.level || 'quiet')} absolute
                  </span>
                </div>
                <div className="lg:text-right">
                  <div className="text-[1.6rem] font-semibold leading-none text-slate-900 dark:text-slate-50">{scanScore}</div>
                  <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                    {formatPercent(scanScore, topScanScore)} of top
                  </div>
                </div>
                <div className="lg:text-right">
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">{row.raw_score ?? 0}</div>
                  <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">raw</div>
                </div>
                <div className="lg:text-right">
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">{row.delta_from_top ?? 0}</div>
                  <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Δ top</div>
                </div>
              </div>
              {seriesValues.length ? (
                <div className="mt-4 lg:ml-[44px]">
                  <Sparkline
                    values={seriesValues}
                    tone={scanLevelTone(row.scan_level)}
                    className="max-w-[24rem]"
                  />
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ScanResearchPanel({ result, resultView }) {
  const topRow = Array.isArray(result?.top_cells) ? result.top_cells[0] || null : Array.isArray(result?.results) ? result.results[0] || null : null;
  const topPlace = Array.isArray(result?.top_places) ? result.top_places[0] || null : null;
  const places = Array.isArray(result?.series?.places) ? result.series.places : [];
  const counts = result?.counts || {};
  const failures = Array.isArray(result?.failures) ? result.failures : [];
  const graphPlace = topPlace
    ? places.find((place) => normalizeId(place?.location?.label) === normalizeId(topPlace?.location?.label)) || null
    : null;
  const graphPeakMeta = peakLabelMeta(graphPlace || topPlace || {});
  const inspectorMode = resultView === 'graph' && topPlace ? 'graph' : 'cells';
  return (
    <>
      <section className={sectionCardCls}>
        <SectionIntro
          eyebrow="Research Scope"
          title="Scan scope"
        />
        <div className="mt-4 grid grid-cols-2 gap-3">
          <MetricPill label="Region" value={result?.region?.label || 'Not selected'} tone="accent" />
          <MetricPill label="Resolution" value={result?.resolution?.label || 'Default'} tone="default" />
          <MetricPill label="Candidates" value={counts.candidate_locations ?? 0} tone="default" />
          <MetricPill label="Time Slices" value={counts.time_slices ?? 0} tone="default" />
          <MetricPill label="Evaluated" value={counts.evaluated_cells ?? 0} tone="default" />
          <MetricPill label="Places" value={counts.returned_places ?? (Array.isArray(result?.top_places) ? result.top_places.length : 0)} tone={Number(counts.returned_places || 0) > 0 ? 'good' : 'default'} />
          <MetricPill label="Top Cells" value={counts.returned ?? 0} tone={Number(counts.returned || 0) > 0 ? 'good' : 'default'} />
        </div>
      </section>
      {inspectorMode === 'graph' && topPlace ? (
        <section className={sectionCardCls}>
          <SectionIntro
            eyebrow="Inspector"
            title="Top breakout place"
          />
          <div className="mt-4 space-y-4">
            <div>
              <div className="text-base font-semibold text-slate-900 dark:text-slate-50">{topPlace.location?.label || 'Unknown location'}</div>
              <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                {graphPeakMeta.title}: {graphPeakMeta.label}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <MetricPill label="Peak Pressure" value={topPlace.peak_scan_score ?? 0} tone="danger" />
              <MetricPill label="Breakout" value={topPlace.breakout_index ?? 0} tone="warning" />
              <MetricPill label="Kind" value={formatLabel(topPlace.breakout_kind || 'candidate')} tone="accent" />
              <MetricPill label="Peak Mode" value={formatLabel((graphPlace || topPlace)?.peak_selection || 'single_peak')} tone="default" />
            </div>
          </div>
        </section>
      ) : topRow ? (
        <section className={sectionCardCls}>
          <SectionIntro
            eyebrow="Inspector"
            title="Top candidate"
          />
          <div className="mt-4 space-y-4">
            <div>
              <div className="text-base font-semibold text-slate-900 dark:text-slate-50">{topRow.location?.label || 'Unknown location'}</div>
              <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">{formatDateTime(topRow.datetime)}</div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <MetricPill label="Scan Level" value={formatLabel(topRow.scan_level || 'background')} tone={scanLevelTone(topRow.scan_level)} />
              <MetricPill label="Absolute Level" value={formatLabel(topRow.level || 'quiet')} tone={levelTone(topRow.level)} />
              <MetricPill label="Coverage" value={formatLabel(topRow.calibration?.coverage_tier || 'unseeded')} tone="accent" />
              <MetricPill label="Cases" value={topRow.calibration?.unique_case_count ?? 0} tone="default" />
              <MetricPill label="Flags" value={Array.isArray(topRow.research_flags) ? topRow.research_flags.length : 0} tone="default" />
              <MetricPill label="Relative" value={topRow.relative_score_ratio ?? 0} tone="default" />
              <MetricPill label="Top Gap" value={topRow.delta_from_top ?? 0} tone="default" />
            </div>
          </div>
        </section>
      ) : null}
      {failures.length ? (
        <section className={sectionCardCls}>
          <SectionIntro
            eyebrow="Backend Notes"
            title="Scan failures"
          />
          <div className="mt-3 space-y-2">
            {failures.slice(0, 5).map((failure, index) => (
              <div key={`${failure.location}-${failure.datetime}-${index}`} className={nestedCardCls}>
                <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{failure.location || 'Unknown location'}</div>
                {failure.datetime ? <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{formatDateTime(failure.datetime)}</div> : null}
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{failure.error || 'Unknown scan failure.'}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}

function ScanOutputToggle({ value, onChange, hasSeries }) {
  if (!hasSeries) return null;
  const options = hasSeries
    ? [
        { id: 'graph', label: 'Break Graph' },
        { id: 'cells', label: 'Top Cells' },
      ]
    : [{ id: 'cells', label: 'Top Cells' }];
  return <ResearchSegmentedToggle options={options} value={value} onChange={onChange} />;
}

function ScanOutputConsoleToggle({ value, onChange, hasSeries }) {
  if (!hasSeries) return null;
  const options = hasSeries
    ? [
        { id: 'graph', label: 'Break Graph' },
        { id: 'cells', label: 'Top Cells' },
      ]
    : [{ id: 'cells', label: 'Top Cells' }];
  return <ConsoleModeTabs options={options} value={value} onChange={onChange} />;
}

function ScanResultsConsolePanel({ result, activeRowKey = '', onSelectRow = null }) {
  const rows = Array.isArray(result?.top_cells) ? result.top_cells : Array.isArray(result?.results) ? result.results : [];
  const topScanScore = Math.max(0, ...rows.map((row) => Number(row.scan_score ?? row.score ?? 0)));

  if (!rows.length) {
    return (
      <ConsoleEmptyState
        module={MUNDANE_MODULE}
        title="No scan results yet"
        detail="Run a spatial or time-window scan to populate the ranking table."
      />
    );
  }

  return (
    <section className={sectionCardCls}>
      <ConsoleSectionBar
        module={MUNDANE_MODULE}
        label={`top_cells / ${rows.length} returned`}
        right={<ConsoleStatusBadge label={formatLabel(result?.scan_mode || 'scan')} />}
      />
      <div className={researchWorkspaceCls.tableFrameCls}>
        <div className="hidden grid-cols-[44px_minmax(0,2.55fr)_148px_88px_64px_64px] gap-3 border-b border-slate-200/90 bg-slate-50/90 px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-400 lg:grid">
          <div>#</div>
          <div>Place</div>
          <div>Level</div>
          <div className="text-right">Scan</div>
          <div className="text-right">Raw</div>
          <div className="text-right">Gap</div>
        </div>
        {rows.map((row) => {
          const scanScore = Number(row.scan_score ?? row.score ?? 0);
          const placeLabel = row.location?.label || 'Unknown location';
          const rowKey = scanRowSelectionKey(row);
          const isActive = rowKey === activeRowKey;
          const regionLabel = [
            row.location?.country_name || row.location?.country_code || null,
            row.location?.timezone || null,
          ].filter(Boolean).join(' / ');
          const rowAccentCls = isActive
            ? 'border-l-2 border-sky-500 pl-3 dark:border-sky-300'
            : Number(row.rank) === 1
              ? 'border-l-2 border-slate-900 pl-3 dark:border-slate-50'
              : '';

          return (
            <article key={`${row.rank}-${row.location?.label}-${row.datetime}`} className="border-b border-slate-100/90 last:border-b-0 dark:border-slate-800/80">
              <button
                type="button"
                onClick={() => onSelectRow?.(row)}
                aria-label={`Select ${placeLabel} at ${formatDateTime(row.datetime)}`}
                aria-pressed={isActive}
                className={`block w-full px-4 py-2.5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300/70 dark:focus-visible:ring-sky-500/40 ${isActive ? 'bg-sky-50/70 dark:bg-sky-500/10' : 'hover:bg-slate-50/80 dark:hover:bg-slate-900/45'}`}
              >
                <div className={`grid gap-3 lg:grid-cols-[44px_minmax(0,2.55fr)_148px_88px_64px_64px] lg:items-start ${rowAccentCls}`}>
                  <div className="font-mono text-xs font-semibold tracking-[0.12em] text-slate-500 dark:text-slate-400">
                    {String(row.rank ?? '').padStart(2, '0')}
                  </div>
                  <div className="min-w-0">
                    <div className="min-w-0">
                      <div className="truncate text-[1.02rem] font-semibold leading-tight text-slate-900 dark:text-slate-50">{placeLabel}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-slate-600 dark:text-slate-300">
                        <span className="truncate">{regionLabel || 'Unknown region'}</span>
                        <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-slate-300 dark:text-slate-600">/</span>
                        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
                          {formatCompactDateTime(row.datetime)}
                        </span>
                      </div>
                    </div>
                    {Array.isArray(row.matched_rules) && row.matched_rules.length ? (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {row.matched_rules.slice(0, 2).map((rule, index) => (
                          <span key={`${row.rank}-${rule.id || rule.label || index}`} className="rounded-[3px] border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.08em] text-slate-600 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-300">
                            {rule.label || formatLabel(rule.id || `rule_${index + 1}`)}
                          </span>
                        ))}
                        {row.matched_rules.length > 2 ? (
                          <span className="rounded-[3px] border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.08em] text-slate-400 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-500">
                            +{row.matched_rules.length - 2}
                          </span>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${toneBadgeClass(scanLevelTone(row.scan_level))}`}>
                      {formatLabel(row.scan_level || 'background')}
                    </span>
                    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${toneBadgeClass(levelTone(row.level))}`}>
                      {formatLabel(row.level || 'quiet')} absolute
                    </span>
                  </div>
                  <div className="lg:text-right">
                    <div className="text-[1.45rem] font-semibold leading-none text-slate-900 dark:text-slate-50">{scanScore}</div>
                    <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                      {formatPercent(scanScore, topScanScore)} of top
                    </div>
                  </div>
                  <div className="lg:text-right">
                    <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">{row.raw_score ?? 0}</div>
                    <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">raw</div>
                  </div>
                  <div className="lg:text-right">
                    <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">{row.delta_from_top ?? 0}</div>
                    <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">delta top</div>
                  </div>
                </div>
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ScanResearchConsolePanel({ result, resultView, activeRow = null, activePlace = null, activeGraphPlace = null }) {
  const topRow = activeRow || (Array.isArray(result?.top_cells) ? result.top_cells[0] || null : Array.isArray(result?.results) ? result.results[0] || null : null);
  const topPlace = activePlace || (Array.isArray(result?.top_places) ? result.top_places[0] || null : null);
  const places = Array.isArray(result?.series?.places) ? result.series.places : [];
  const counts = result?.counts || {};
  const failures = Array.isArray(result?.failures) ? result.failures : [];
  const graphPlace = activeGraphPlace || (topPlace
    ? places.find((place) => normalizeId(place?.location?.label) === normalizeId(topPlace?.location?.label)) || null
    : null);
  const graphPeakMeta = peakLabelMeta(graphPlace || topPlace || {});
  const inspectorMode = resultView === 'graph' && (graphPlace || topPlace) ? 'graph' : 'cells';

  return (
    <>
      <section className={sectionCardCls}>
        <ConsoleSectionBar module={MUNDANE_MODULE} label="research_scope" />
        <div className="mt-1">
          <ConsoleDataRow label="Region" value={result?.region?.label || 'Not selected'} tone={MUNDANE_MODULE} />
          <ConsoleDataRow label="Resolution" value={result?.resolution?.label || 'Default'} />
          <ConsoleDataRow label="Candidates" value={counts.candidate_locations ?? 0} mono />
          <ConsoleDataRow label="Time slices" value={counts.time_slices ?? 0} mono />
          <ConsoleDataRow label="Evaluated" value={counts.evaluated_cells ?? 0} mono />
          <ConsoleDataRow label="Places" value={counts.returned_places ?? (Array.isArray(result?.top_places) ? result.top_places.length : 0)} mono strong />
          <ConsoleDataRow label="Top cells" value={counts.returned ?? 0} mono strong />
        </div>
      </section>
      {inspectorMode === 'graph' && topPlace ? (
        <section className={sectionCardCls}>
          <ConsoleSectionBar module={MUNDANE_MODULE} label="inspector / selected_breakout_place" />
          <div className="mt-3 text-base font-semibold text-slate-900 dark:text-slate-50">{topPlace.location?.label || 'Unknown location'}</div>
          <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">{graphPeakMeta.title}: {graphPeakMeta.label}</div>
          <div className="mt-4">
            <ConsoleDataRow label="Peak pressure" value={topPlace.peak_scan_score ?? 0} mono strong tone="warning" />
            <ConsoleDataRow label="Breakout" value={topPlace.breakout_index ?? 0} mono />
            <ConsoleDataRow label="Kind" value={formatLabel(topPlace.breakout_kind || 'candidate')} tone={MUNDANE_MODULE} />
            <ConsoleDataRow label="Peak mode" value={formatLabel((graphPlace || topPlace)?.peak_selection || 'single_peak')} />
          </div>
        </section>
      ) : topRow ? (
        <section className={sectionCardCls}>
          <ConsoleSectionBar module={MUNDANE_MODULE} label="inspector / selected_candidate" />
          <div className="mt-3 text-base font-semibold text-slate-900 dark:text-slate-50">{topRow.location?.label || 'Unknown location'}</div>
          <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">{formatDateTime(topRow.datetime)}</div>
          <div className="mt-4">
            <ConsoleDataRow label="Scan level" value={formatLabel(topRow.scan_level || 'background')} tone={scanLevelTone(topRow.scan_level)} />
            <ConsoleDataRow label="Absolute level" value={formatLabel(topRow.level || 'quiet')} tone={levelTone(topRow.level)} />
            <ConsoleDataRow label="Coverage" value={formatLabel(topRow.calibration?.coverage_tier || 'unseeded')} tone={MUNDANE_MODULE} />
            <ConsoleDataRow label="Cases" value={topRow.calibration?.unique_case_count ?? 0} mono />
            <ConsoleDataRow label="Flags" value={Array.isArray(topRow.research_flags) ? topRow.research_flags.length : 0} mono />
            <ConsoleDataRow label="Relative" value={topRow.relative_score_ratio ?? 0} mono />
            <ConsoleDataRow label="Top gap" value={topRow.delta_from_top ?? 0} mono strong />
          </div>
        </section>
      ) : null}
      {failures.length ? (
        <section className={sectionCardCls}>
          <ConsoleSectionBar module={MUNDANE_MODULE} label="backend_notes / failures" />
          <div className="mt-3 space-y-2">
            {failures.slice(0, 5).map((failure, index) => (
              <div key={`${failure.location}-${failure.datetime}-${index}`} className={nestedCardCls}>
                <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{failure.location || 'Unknown location'}</div>
                {failure.datetime ? <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{formatDateTime(failure.datetime)}</div> : null}
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{failure.error || 'Unknown scan failure.'}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}

function heatCellStyle(score, maxScore, highlighted) {
  const numericScore = Number(score || 0);
  const ratio = maxScore > 0 ? Math.max(0, Math.min(1, numericScore / maxScore)) : 0;
  let background = 'rgba(161, 161, 170, 0.1)';
  let border = 'rgba(161, 161, 170, 0.22)';
  if (ratio >= 0.85) {
    background = `rgba(244, 63, 94, ${0.18 + (ratio * 0.42)})`;
    border = 'rgba(244, 63, 94, 0.55)';
  } else if (ratio >= 0.6) {
    background = `rgba(245, 158, 11, ${0.16 + (ratio * 0.38)})`;
    border = 'rgba(245, 158, 11, 0.48)';
  } else if (ratio > 0.18) {
    background = `rgba(14, 165, 233, ${0.14 + (ratio * 0.34)})`;
    border = 'rgba(14, 165, 233, 0.42)';
  }
  if (highlighted) {
    border = 'rgba(15, 23, 42, 0.7)';
  }
  return {
    backgroundColor: background,
    borderColor: border,
    boxShadow: highlighted ? 'inset 0 0 0 1px rgba(255,255,255,0.9)' : 'none',
  };
}

function ScanSeriesGraphPanel({ result, activePlaceLabel = '', onSelectPlace = null }) {
  const series = result?.series || {};
  const timeline = Array.isArray(series?.timeline) ? series.timeline : [];
  const places = prioritizePlaceLabel(
    Array.isArray(series?.graph_places) ? series.graph_places : Array.isArray(series?.places) ? series.places : [],
    activePlaceLabel,
  );
  const breakoutCandidates = prioritizePlaceLabel(
    Array.isArray(result?.top_places) && result.top_places.length
    ? result.top_places
    : Array.isArray(series?.breakout_candidates) ? series.breakout_candidates : [],
    activePlaceLabel,
  );
  const overview = series?.series_overview || {};
  const maxScore = Math.max(
    0,
    ...places.flatMap((place) => (Array.isArray(place?.series) ? place.series.map((point) => Number(point?.scan_score || 0)) : [0])),
  );

  if (!timeline.length || !places.length) {
    return (
      <section className={emptyStateCls}>
        <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">No graph data yet</h4>
      </section>
    );
  }

  return (
    <section className={sectionCardCls}>
      <SectionIntro
        eyebrow="Break Graph"
        title="Place-time breakout pressure"
      />
      <div className="mt-4 grid gap-3 lg:grid-cols-4">
        <MetricPill label="Timeline" value={overview.timeline_points ?? timeline.length} tone="accent" />
        <MetricPill label="Places" value={overview.place_count ?? places.length} tone="default" />
        <MetricPill
          label="Top Breakout"
          value={overview.top_breakout_location?.label || 'Unknown'}
          tone="warning"
        />
        <MetricPill
          label="Top Peak"
          value={overview.top_peak_location?.label || 'Unknown'}
          tone="danger"
        />
      </div>

      {breakoutCandidates.length ? (
        <div className="mt-6">
        <div className="flex flex-col gap-2 border-b border-slate-200/85 pb-3 dark:border-slate-700/80">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Visualization 1</div>
          <div className="text-lg font-semibold text-slate-900 dark:text-slate-50">Breakout leaderboard</div>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          {breakoutCandidates.slice(0, 3).map((candidate) => {
            const placeSeries = places.find((place) => normalizeId(place?.location?.label) === normalizeId(candidate.location?.label));
            const pointSeries = Array.isArray(placeSeries?.series) ? placeSeries.series : [];
            const seriesValues = pointSeries.map((point) => Number(point?.scan_score || 0));
            const peakIndex = pointSeries.findIndex((point) => point?.datetime === candidate.peak_datetime);
            const peakPercent = formatPercent(candidate.peak_scan_score, maxScore);
            const peakMeta = peakTickMeta(candidate);
            const isActive = sameLocationLabel(candidate.location?.label, activePlaceLabel);
            return (
              <button
                key={`${candidate.rank}-${candidate.location?.label}`}
                type="button"
                onClick={() => onSelectPlace?.(candidate)}
                aria-pressed={isActive}
                className={`${nestedCardCls} text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300/70 dark:focus-visible:ring-sky-500/40 ${isActive ? 'border-sky-300 bg-sky-50/70 dark:border-sky-500/40 dark:bg-sky-500/10' : 'hover:border-slate-300 hover:bg-slate-50/90 dark:hover:border-slate-600 dark:hover:bg-slate-900/55'}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
                    Breakout {candidate.rank}
                  </span>
                </div>
                <div className="mt-4 text-base font-semibold text-slate-900 dark:text-slate-50">{candidate.location?.label || 'Unknown location'}</div>
                <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                  {formatLabel(candidate.breakout_kind || 'candidate')}
                </div>
                <div className="mt-4">
                  <div>
                    <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Peak pressure</div>
                    <div className="mt-2 flex items-end gap-3">
                      <div className="text-[2.15rem] font-semibold leading-none text-slate-900 dark:text-slate-50">{candidate.peak_scan_score ?? 0}</div>
                      <div className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500 dark:border-slate-700 dark:bg-slate-950/35 dark:text-slate-300">
                        {peakPercent}
                      </div>
                    </div>
                    <div className="mt-2 text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                      Breakout {candidate.breakout_index ?? 0}
                    </div>
                  </div>
                </div>
                <Sparkline
                  values={seriesValues}
                  tone={trendToneForBreakoutKind(candidate.breakout_kind)}
                  className="mt-4"
                  peakIndex={peakIndex >= 0 ? peakIndex : null}
                  peakLabel={peakMeta.tickLabel}
                  peakTitle={peakMeta.title}
                />
              </button>
            );
          })}
          </div>
        </div>
      ) : null}

      <div className="mt-6">
        <div className="flex flex-col gap-2 border-b border-slate-200/85 pb-3 dark:border-slate-700/80">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Visualization 2</div>
          <div className="text-lg font-semibold text-slate-900 dark:text-slate-50">Pressure matrix</div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {[
            ['DOM', 'Dominant'],
            ['LEAD', 'Leading'],
            ['CO', 'Co-Leading'],
            ['ACT', 'Active'],
            ['W', 'Watch'],
          ].map(([short, label]) => (
            <span key={short} className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-950/35 dark:text-slate-300">
              <span className="font-semibold">{short}</span> {label}
            </span>
          ))}
        </div>
      </div>

      <div className={`${mutedPanelCls} mt-5 overflow-x-auto`}>
        <div className="min-w-[860px]">
          <div
            className="grid gap-2.5"
            style={{ gridTemplateColumns: `240px repeat(${timeline.length}, minmax(44px, 1fr))` }}
          >
            <div />
            {timeline.map((tick, index) => (
              <div
                key={`tick-${tick}-${index}`}
                className="text-center text-[10px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400"
                title={formatDateTime(tick)}
              >
                {formatTimelineTick(tick)}
              </div>
            ))}

            {places.map((place) => {
              const placeSeries = Array.isArray(place?.series) ? place.series : [];
              const peakIndex = placeSeries.findIndex((point) => point?.datetime === place.peak_datetime);
              const peakMeta = peakTickMeta(place);
              const isActivePlace = sameLocationLabel(place.location?.label, activePlaceLabel);
              return (
                <React.Fragment key={`${place.location?.label || 'unknown'}-${place.peak_datetime || 'none'}`}>
                  <button
                    type="button"
                    onClick={() => onSelectPlace?.(place)}
                    aria-pressed={isActivePlace}
                    className={`rounded-[20px] border px-4 py-4 text-left shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300/70 dark:focus-visible:ring-sky-500/40 ${isActivePlace ? 'border-sky-300 bg-sky-50/70 dark:border-sky-500/40 dark:bg-sky-500/10' : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-950/35'}`}
                  >
                    <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">{place.location?.label || 'Unknown location'}</div>
                    <Sparkline
                      values={placeSeries.map((point) => Number(point?.scan_score || 0))}
                      tone={normalizeId(place.breakout_kind) === 'opening_break_candidate' ? 'accent' : 'warning'}
                      className="mt-3"
                      peakIndex={peakIndex >= 0 ? peakIndex : null}
                      peakLabel={peakMeta.tickLabel}
                      peakTitle={peakMeta.title}
                    />
                  </button>
                  {placeSeries.map((point, index) => {
                    const highlighted = isPeakPlateau(place?.peak_selection)
                      ? pointInPeakWindow(place, point.datetime)
                      : point.datetime === place.peak_datetime;
                    return (
                      <div
                        key={`${place.location?.label}-${point.datetime || index}`}
                        className="h-[96px] rounded-[20px] border transition"
                        style={heatCellStyle(point.scan_score, maxScore, highlighted)}
                        title={`${place.location?.label || 'Unknown'}\n${formatDateTime(point.datetime)}\nBreakout score: ${point.scan_score ?? 0}\nAbsolute score: ${point.absolute_score ?? 0}\nScan level: ${formatLabel(point.scan_level || 'background')}\nAbsolute level: ${formatLabel(point.absolute_level || 'quiet')}\n${peakMeta.title}: ${peakMeta.label}`}
                      >
                        <div className="flex h-full flex-col items-center justify-between px-1.5 py-2.5">
                          <span className="text-xs font-semibold leading-none text-slate-900">{point.scan_score ?? 0}</span>
                          <span className="rounded-full border border-slate-900/10 bg-white/75 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-900/75">
                            {scanLevelShortLabel(point.scan_level)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </div>

    </section>
  );
}

export default function MundaneScanWorkspace({ open, defaultHouseSystem = 'R' }) {
  const [catalog, setCatalog] = useState(() => mundaneScanCatalogCache);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [chartSourceMode, setChartSourceMode] = useState('registered');
  const [chartTypeId, setChartTypeId] = useState('');
  const [domainId, setDomainId] = useState('');
  const [polityId, setPolityId] = useState('');
  const [nationalChartId, setNationalChartId] = useState('');
  const [customPolityLabel, setCustomPolityLabel] = useState('');
  const [customChartLabel, setCustomChartLabel] = useState('');
  const [customChartDate, setCustomChartDate] = useState('');
  const [customChartTime, setCustomChartTime] = useState('');
  const [customChartLocation, setCustomChartLocation] = useState('');
  const [customChartTimezone, setCustomChartTimezone] = useState('');
  const [locationContextType, setLocationContextType] = useState('');
  const [visibilityScope, setVisibilityScope] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [eventTime, setEventTime] = useState('');
  const [scanModeId, setScanModeId] = useState('spatial_scan');
  const [regionId, setRegionId] = useState('');
  const [resolutionId, setResolutionId] = useState('');
  const [topK, setTopK] = useState('8');
  const [minimumScore, setMinimumScore] = useState('');
  const [candidateLimit, setCandidateLimit] = useState('');
  const [scanStartDate, setScanStartDate] = useState('');
  const [scanStartTime, setScanStartTime] = useState('');
  const [scanEndDate, setScanEndDate] = useState('');
  const [scanEndTime, setScanEndTime] = useState('');
  const [timeStepHours, setTimeStepHours] = useState('6');
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [sessionId, setSessionId] = useState('');
  const [loadingScan, setLoadingScan] = useState(false);
  const [error, setError] = useState('');
  const [resultView, setResultView] = useState('cells');
  const [selectedCellKey, setSelectedCellKey] = useState('');
  const [selectedPlaceLabel, setSelectedPlaceLabel] = useState('');

  const chartTypes = Array.isArray(catalog?.chart_types) ? catalog.chart_types : [];
  const domains = Array.isArray(catalog?.domains) ? catalog.domains : [];
  const polities = Array.isArray(catalog?.polities) ? catalog.polities : [];
  const contextTypes = Array.isArray(catalog?.context_types) ? catalog.context_types : [];
  const scanModes = Array.isArray(catalog?.scan_modes) ? catalog.scan_modes : [];
  const regions = Array.isArray(catalog?.regions) ? catalog.regions : [];
  const resolutions = Array.isArray(catalog?.resolutions) ? catalog.resolutions : [];

  const selectedChartType = useMemo(
    () => chartTypes.find((item) => normalizeId(item?.id) === normalizeId(chartTypeId)) || null,
    [chartTypeId, chartTypes],
  );
  const domainOptions = useMemo(
    () => buildChartTypeDomainOptions(selectedChartType, domains),
    [domains, selectedChartType],
  );
  const availableDomains = domainOptions.availableDomains;
  const selectedDomain = useMemo(
    () => availableDomains.find((item) => normalizeId(item?.id) === normalizeId(domainId)) || null,
    [availableDomains, domainId],
  );
  const selectedPolity = useMemo(
    () => polities.find((item) => normalizeId(item?.id) === normalizeId(polityId)) || null,
    [polities, polityId],
  );
  const selectedNationalChartOptions = Array.isArray(selectedPolity?.national_charts) ? selectedPolity.national_charts : [];
  const selectedNationalChart = useMemo(
    () => selectedNationalChartOptions.find((item) => normalizeId(item?.id) === normalizeId(nationalChartId)) || null,
    [nationalChartId, selectedNationalChartOptions],
  );
  const usingCustomChartSource = chartSourceMode === 'custom';
  const missingRequiredPolityOptions = Boolean(selectedChartType?.requires_polity) && !usingCustomChartSource && polities.length === 0;
  const customChartDatetime = useMemo(
    () => buildEventDatetime(customChartDate, customChartTime),
    [customChartDate, customChartTime],
  );
  const effectivePolityProvided = usingCustomChartSource
    ? Boolean(String(customPolityLabel || '').trim())
    : Boolean(polityId);
  const selectedScanMode = useMemo(
    () => scanModes.find((item) => normalizeId(item?.id) === normalizeId(scanModeId)) || null,
    [scanModeId, scanModes],
  );
  const selectedRegion = useMemo(
    () => regions.find((item) => normalizeId(item?.id) === normalizeId(regionId)) || null,
    [regionId, regions],
  );
  const selectedResolution = useMemo(
    () => resolutions.find((item) => normalizeId(item?.id) === normalizeId(resolutionId)) || null,
    [resolutionId, resolutions],
  );
  const scanModeLimits = catalog?.scan_mode_limits || {};
  const selectedModeLimits = scanModeLimits?.[scanModeId] || {};
  const selectedModeLabel = selectedScanMode?.label || 'Time-window scan';
  const maxTimeSlices = Number(selectedModeLimits?.max_time_slices || catalog?.max_time_slices || 24);
  const maxEvaluatedCells = Number(selectedModeLimits?.max_evaluated_cells || catalog?.max_evaluated_cells || 160);
  const defaultModeCandidateLimit = Number(selectedModeLimits?.default_candidate_limit || 0) || null;
  const maxModeCandidates = Number(selectedModeLimits?.max_candidates || catalog?.max_candidates || 32);
  const defaultModeTimeStepHours = Number(selectedModeLimits?.default_time_step_hours || 0) || 6;
  const effectiveCandidateLimit = candidateLimit
    ? Math.min(Number(candidateLimit), maxModeCandidates)
    : defaultModeCandidateLimit || Number(selectedResolution?.relocation_limit || 0) || null;
  const estimatedTimeSlices = scanModeId === 'spatial_scan'
    ? 1
    : estimateTimeSlices(buildEventDatetime(scanStartDate, scanStartTime), buildEventDatetime(scanEndDate, scanEndTime), timeStepHours || defaultModeTimeStepHours);
  const estimatedEvaluatedCells = estimatedTimeSlices && effectiveCandidateLimit
    ? estimatedTimeSlices * effectiveCandidateLimit
    : null;
  const workspaceSummaryItems = useMemo(() => ([
    { label: 'Chart', value: selectedChartType?.label || '' },
    { label: 'Lens', value: selectedDomain?.label || '' },
    { label: 'Nation', value: usingCustomChartSource ? customPolityLabel || 'Custom' : selectedPolity?.label || '' },
    { label: 'Natal Ref', value: usingCustomChartSource ? customChartLabel || 'Custom chart' : selectedNationalChart?.label || (selectedPolity ? 'Default chart' : '') },
    { label: 'Area', value: selectedRegion?.label || '' },
    { label: 'Density', value: selectedResolution?.label || '' },
    { label: 'Mode', value: selectedScanMode?.label || '' },
  ]), [
    customChartLabel,
    customPolityLabel,
    selectedChartType?.label,
    selectedDomain?.label,
    selectedNationalChart?.label,
    selectedPolity,
    selectedRegion?.label,
    selectedResolution?.label,
    selectedScanMode?.label,
    usingCustomChartSource,
  ]);

  const requestPayload = useMemo(() => ({
    chartType: chartTypeId,
    domain: domainId,
    polityId: usingCustomChartSource ? undefined : polityId || undefined,
    customPolityLabel: usingCustomChartSource ? customPolityLabel || undefined : undefined,
    nationalChartId: usingCustomChartSource ? undefined : nationalChartId || undefined,
    customChartLabel: usingCustomChartSource ? customChartLabel || undefined : undefined,
    customChartDatetime: usingCustomChartSource ? customChartDatetime || undefined : undefined,
    customChartLocation: usingCustomChartSource ? customChartLocation || undefined : undefined,
    customChartTimezone: usingCustomChartSource ? customChartTimezone || undefined : undefined,
    locationContextType: locationContextType || undefined,
    visibilityScope: visibilityScope || undefined,
    houseSystem: defaultHouseSystem,
    scanMode: scanModeId || undefined,
    regionId: regionId || undefined,
    resolution: resolutionId || undefined,
    topK: topK ? Number(topK) : undefined,
    minimumScore: minimumScore !== '' ? Number(minimumScore) : undefined,
    candidateLimit: candidateLimit ? Number(candidateLimit) : undefined,
    fixedDatetime: buildEventDatetime(eventDate, eventTime) || undefined,
    startDatetime: buildEventDatetime(scanStartDate, scanStartTime) || undefined,
    endDatetime: buildEventDatetime(scanEndDate, scanEndTime) || undefined,
    timeStepHours: timeStepHours ? Number(timeStepHours) : undefined,
    includeSeries: scanModeId !== 'spatial_scan',
  }), [
    candidateLimit,
    chartTypeId,
    chartSourceMode,
    customChartDate,
    customChartDatetime,
    customChartLabel,
    customChartLocation,
    customChartTime,
    customChartTimezone,
    customPolityLabel,
    defaultHouseSystem,
    domainId,
    eventDate,
    eventTime,
    locationContextType,
    minimumScore,
    nationalChartId,
    polityId,
    regionId,
    resolutionId,
    scanEndDate,
    scanEndTime,
    scanModeId,
    scanStartDate,
    scanStartTime,
    timeStepHours,
    topK,
    usingCustomChartSource,
    visibilityScope,
  ]);

  const hasSeries = Array.isArray(result?.series?.places) && result.series.places.length > 0;
  const scanRows = useMemo(
    () => (Array.isArray(result?.top_cells) ? result.top_cells : Array.isArray(result?.results) ? result.results : []),
    [result],
  );
  const topPlaces = useMemo(
    () => (Array.isArray(result?.top_places) ? result.top_places : []),
    [result],
  );
  const seriesPlaces = useMemo(
    () => (Array.isArray(result?.series?.places) ? result.series.places : []),
    [result],
  );
  const activeScanRow = useMemo(() => {
    const exactMatch = scanRows.find((row) => scanRowSelectionKey(row) === selectedCellKey);
    if (exactMatch) return exactMatch;
    if (selectedPlaceLabel) {
      const placeMatch = scanRows.find((row) => sameLocationLabel(row?.location?.label, selectedPlaceLabel));
      if (placeMatch) return placeMatch;
    }
    return scanRows[0] || null;
  }, [scanRows, selectedCellKey, selectedPlaceLabel]);
  const activePlaceLabel = selectedPlaceLabel || activeScanRow?.location?.label || topPlaces[0]?.location?.label || seriesPlaces[0]?.location?.label || '';
  const activeTopPlace = useMemo(() => {
    if (activePlaceLabel) {
      const topPlaceMatch = topPlaces.find((place) => sameLocationLabel(place?.location?.label, activePlaceLabel));
      if (topPlaceMatch) return topPlaceMatch;
      const seriesPlaceMatch = seriesPlaces.find((place) => sameLocationLabel(place?.location?.label, activePlaceLabel));
      if (seriesPlaceMatch) return seriesPlaceMatch;
    }
    return topPlaces[0] || seriesPlaces[0] || null;
  }, [activePlaceLabel, seriesPlaces, topPlaces]);
  const activeGraphPlace = useMemo(() => {
    const targetLabel = activeTopPlace?.location?.label || activePlaceLabel;
    if (targetLabel) {
      return seriesPlaces.find((place) => sameLocationLabel(place?.location?.label, targetLabel)) || null;
    }
    return seriesPlaces[0] || null;
  }, [activePlaceLabel, activeTopPlace, seriesPlaces]);

  const loadCatalog = useCallback(async () => {
    setLoadingCatalog(true);
    setCatalogError('');
    try {
      if (!mundaneScanCatalogPromise) {
        mundaneScanCatalogPromise = AstroClockAPI.listMundaneScanCatalog()
          .then((res) => {
            const data = res?.success ? res.data : null;
            mundaneScanCatalogCache = data || null;
            return mundaneScanCatalogCache;
          })
          .finally(() => {
            mundaneScanCatalogPromise = null;
          });
      }
      const data = await mundaneScanCatalogPromise;
      setCatalog(data || null);
    } catch (nextError) {
      setCatalog(null);
      setCatalogError(nextError?.message || 'Failed to load scan catalog.');
    } finally {
      setLoadingCatalog(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    loadCatalog();
  }, [loadCatalog, open]);

  useEffect(() => {
    if (!chartTypes.length) return;
    if (chartTypes.some((item) => normalizeId(item?.id) === normalizeId(chartTypeId))) return;
    setChartTypeId(String(chartTypes[0]?.id || ''));
  }, [chartTypeId, chartTypes]);

  useEffect(() => {
    if (!availableDomains.length) return;
    if (isChartTypeDomainAllowed(selectedChartType, domainId, domains)) return;
    const nextDomainId = domainOptions.defaultDomainId || String(availableDomains[0]?.id || '');
    setDomainId(nextDomainId);
  }, [availableDomains, domainId, domainOptions.defaultDomainId, domains, selectedChartType]);

  useEffect(() => {
    if (!scanModes.length) return;
    if (scanModes.some((item) => normalizeId(item?.id) === normalizeId(scanModeId))) return;
    setScanModeId(String(scanModes[0]?.id || 'spatial_scan'));
  }, [scanModeId, scanModes]);

  useEffect(() => {
    if (!regions.length) return;
    if (regions.some((item) => normalizeId(item?.id) === normalizeId(regionId))) return;
    setRegionId(String(regions[0]?.id || ''));
  }, [regionId, regions]);

  useEffect(() => {
    if (!resolutions.length) return;
    if (resolutions.some((item) => normalizeId(item?.id) === normalizeId(resolutionId))) return;
    setResolutionId(String(catalog?.default_resolution || resolutions[0]?.id || ''));
  }, [catalog?.default_resolution, resolutionId, resolutions]);

  useEffect(() => {
    const preferred = selectedChartType?.default_location_context_type || '';
    setLocationContextType(preferred ? String(preferred) : '');
  }, [selectedChartType?.default_location_context_type]);

  useEffect(() => {
    if (usingCustomChartSource) return;
    if (!selectedChartType?.requires_polity) return;
    if (selectedPolity) return;
    if (polities[0]?.id) setPolityId(String(polities[0].id));
  }, [polities, selectedChartType?.requires_polity, selectedPolity, usingCustomChartSource]);

  useEffect(() => {
    if (usingCustomChartSource) return;
    if (!selectedPolity) {
      setNationalChartId('');
      setVisibilityScope('');
      return;
    }
    if (!selectedNationalChartOptions.some((item) => normalizeId(item?.id) === normalizeId(nationalChartId))) {
      const preferredChart = selectedNationalChartOptions.find((item) => normalizeId(item?.status) === 'preferred') || selectedNationalChartOptions[0] || null;
      setNationalChartId(preferredChart?.id ? String(preferredChart.id) : '');
    }
    setVisibilityScope(String(selectedPolity.visibility_scope || ''));
  }, [nationalChartId, selectedNationalChartOptions, selectedPolity, usingCustomChartSource]);

  useEffect(() => {
    if (!usingCustomChartSource) return;
    if (!selectedPolity) return;
    if (!customPolityLabel) {
      setCustomPolityLabel(String(selectedPolity.label || ''));
    }
    if (!customChartLabel) {
      setCustomChartLabel(`${selectedPolity.label || 'Custom'} Chart`);
    }
    if (!customChartLocation) {
      setCustomChartLocation(String(selectedPolity.default_location || selectedPolity.capital || ''));
    }
    if (!customChartTimezone) {
      setCustomChartTimezone(String(selectedPolity.timezone || ''));
    }
  }, [
    customChartLabel,
    customChartLocation,
    customChartTimezone,
    customPolityLabel,
    selectedPolity,
    usingCustomChartSource,
  ]);

  useEffect(() => {
    if (!open) return;
    setProgress(null);
    setResult(null);
    setSessionId('');
    setError('');
    setResultView('cells');
    setSelectedCellKey('');
    setSelectedPlaceLabel('');
  }, [
    chartTypeId,
    chartSourceMode,
    customChartDate,
    customChartLabel,
    customChartLocation,
    customChartTime,
    customChartTimezone,
    customPolityLabel,
    domainId,
    polityId,
    nationalChartId,
    locationContextType,
    visibilityScope,
    eventDate,
    eventTime,
    scanModeId,
    regionId,
    resolutionId,
    topK,
    minimumScore,
    candidateLimit,
    scanStartDate,
    scanStartTime,
    scanEndDate,
    scanEndTime,
    timeStepHours,
    open,
  ]);

  useEffect(() => {
    if (!result) return;
    setResultView(result?.default_output_view || (hasSeries ? 'graph' : 'cells'));
  }, [hasSeries, result]);

  useEffect(() => {
    if (!result) {
      setSelectedCellKey('');
      setSelectedPlaceLabel('');
      return;
    }
    const defaultRow = scanRows[0] || null;
    const defaultPlaceLabel = defaultRow?.location?.label || topPlaces[0]?.location?.label || seriesPlaces[0]?.location?.label || '';
    setSelectedCellKey(defaultRow ? scanRowSelectionKey(defaultRow) : '');
    setSelectedPlaceLabel(defaultPlaceLabel);
  }, [result, scanRows, seriesPlaces, topPlaces]);

  const handleSelectScanRow = useCallback((row) => {
    const nextKey = scanRowSelectionKey(row);
    if (nextKey) setSelectedCellKey(nextKey);
    if (row?.location?.label) setSelectedPlaceLabel(String(row.location.label));
  }, []);

  const handleSelectPlace = useCallback((place) => {
    const nextPlaceLabel = String(place?.location?.label || '').trim();
    if (!nextPlaceLabel) return;
    setSelectedPlaceLabel(nextPlaceLabel);
    const matchingRow = scanRows.find((row) => sameLocationLabel(row?.location?.label, nextPlaceLabel));
    if (matchingRow) {
      setSelectedCellKey(scanRowSelectionKey(matchingRow));
    }
  }, [scanRows]);

  const handleScan = useCallback(async () => {
    if (!chartTypeId) {
      setError('Choose a chart type first.');
      return;
    }
    if (!domainId) {
      setError('Choose a mundane domain first.');
      return;
    }
    if (missingRequiredPolityOptions) {
      setError('No polity options are available for this chart type. Refresh the scan catalog. If this persists in the packaged app, rebuild the desktop package from current source.');
      return;
    }
    if (selectedChartType?.requires_polity && !effectivePolityProvided) {
      setError('This chart type requires a polity.');
      return;
    }
    if (usingCustomChartSource && (!customChartDatetime || !customChartLocation || !customChartTimezone)) {
      setError('Custom chart mode requires a chart date, location, and timezone.');
      return;
    }
    if (!regionId) {
      setError('Choose a scan region first.');
      return;
    }
    if (scanModeId === 'spatial_scan' && !buildEventDatetime(eventDate, eventTime)) {
      setError('Spatial scan requires a fixed event date and time.');
      return;
    }
    if (scanModeId !== 'spatial_scan') {
      const startDatetime = buildEventDatetime(scanStartDate, scanStartTime);
      const endDatetime = buildEventDatetime(scanEndDate, scanEndTime);
      if (!startDatetime || !endDatetime) {
        setError(`${selectedModeLabel} requires start and end date/time.`);
        return;
      }
      const estimatedSlices = estimateTimeSlices(startDatetime, endDatetime, timeStepHours || defaultModeTimeStepHours);
      if (estimatedSlices === 0) {
        setError(`${selectedModeLabel} requires the end to be after the start.`);
        return;
      }
      if (estimatedSlices && estimatedSlices > maxTimeSlices) {
        setError(`${selectedModeLabel} is limited to ${maxTimeSlices} time slices. Reduce the date range or increase the step size.`);
        return;
      }
      if (estimatedSlices && effectiveCandidateLimit && (estimatedSlices * effectiveCandidateLimit) > maxEvaluatedCells) {
        setError(`${selectedModeLabel} is limited to ${maxEvaluatedCells} evaluated cells. Reduce the date range, lower candidates, or increase the step size.`);
        return;
      }
    }
    setLoadingScan(true);
    setError('');
    setResult(null);
    try {
      const res = await AstroClockAPI.startMundaneScan(requestPayload);
      if (!res?.success) throw new Error('Failed to start mundane scan.');
      setProgress(res.data?.progress || null);
      setSessionId(String(res.data?.session_id || ''));
    } catch (nextError) {
      setProgress(null);
      setSessionId('');
      setLoadingScan(false);
      setError(nextError?.message || 'Failed to start mundane scan.');
    }
  }, [
    chartTypeId,
    customChartDatetime,
    customChartLocation,
    customChartTimezone,
    domainId,
    effectivePolityProvided,
    eventDate,
    eventTime,
    regionId,
    requestPayload,
    scanEndDate,
    scanEndTime,
    scanModeId,
    scanStartDate,
    scanStartTime,
    defaultModeTimeStepHours,
    selectedModeLabel,
    selectedChartType?.requires_polity,
    effectiveCandidateLimit,
    maxEvaluatedCells,
    maxTimeSlices,
    missingRequiredPolityOptions,
    timeStepHours,
    usingCustomChartSource,
  ]);

  useEffect(() => {
    if (!open || !sessionId) return undefined;
    let cancelled = false;
    let timer = null;

    const poll = async () => {
      try {
        const progressRes = await AstroClockAPI.getMundaneScanProgress(sessionId);
        const progressData = progressRes?.success ? progressRes.data : null;
        if (cancelled) return;
        setProgress(progressData || null);
        if (progressData?.failed) {
          setLoadingScan(false);
          setSessionId('');
          setError(progressData.error || 'Mundane scan failed.');
          return;
        }
        if (progressData?.ready) {
          const resultRes = await AstroClockAPI.getMundaneScanResult(sessionId);
          const resultData = resultRes?.success ? resultRes.data : null;
          if (cancelled) return;
          if (resultData?.failed) {
            setError(resultData.error || 'Mundane scan failed.');
            setResult(null);
          } else {
            setResult(resultData?.result || null);
          }
          setLoadingScan(false);
          setSessionId('');
          return;
        }
        timer = setTimeout(poll, SCAN_PROGRESS_POLL_MS);
      } catch (nextError) {
        if (cancelled) return;
        setLoadingScan(false);
        setSessionId('');
        setError(nextError?.message || 'Failed to load scan progress.');
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [open, sessionId]);

  const runningScan = loadingScan || Boolean(sessionId);

  return (
    <div className="grid gap-6 lg:grid-cols-[336px_minmax(0,1.75fr)_332px]">
      <aside className={`${railCardCls} space-y-5 p-5`}>
        <fieldset disabled={runningScan} className="m-0 space-y-5 border-0 p-0 min-w-0">
          <section className={headerBandCls}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-700 dark:text-sky-300">Workspace</div>
                <h3 className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50">Mundane Scan</h3>
              </div>
              <button type="button" className={actionButtonCls} onClick={loadCatalog} disabled={loadingCatalog}>
                {loadingCatalog ? 'Loading...' : 'Refresh'}
              </button>
            </div>
            {catalogError ? <p className="mt-3 text-sm text-red-600">{catalogError}</p> : null}
          </section>

          <section className={`${mutedPanelCls} space-y-2`}>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Chart Type</h4>
            <select className={inputCls} value={chartTypeId} onChange={(event) => setChartTypeId(event.target.value)}>
              <option value="">Select chart type...</option>
              {chartTypes.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </section>

          <section className={`${mutedPanelCls} space-y-2`}>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Domain Lens</h4>
            <select className={inputCls} value={domainId} onChange={(event) => setDomainId(event.target.value)}>
              <option value="">Select domain...</option>
              {domainOptions.preferredDomains.length ? (
                <optgroup label="Preferred lenses">
                  {domainOptions.preferredDomains.map((item) => (
                    <option key={item.id} value={item.id}>{item.label}</option>
                  ))}
                </optgroup>
              ) : null}
              {domainOptions.supportedDomains.length ? (
                <optgroup label="Other supported lenses">
                  {domainOptions.supportedDomains.map((item) => (
                    <option key={item.id} value={item.id}>{item.label}</option>
                  ))}
                </optgroup>
              ) : null}
            </select>
          </section>

          <section className={`${mutedPanelCls} space-y-2`}>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Chart Source</h4>
            <ChartSourceToggle value={chartSourceMode} onChange={setChartSourceMode} />
          </section>

          {!usingCustomChartSource ? (
            <>
              <section className={`${mutedPanelCls} space-y-2`}>
                <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Polity</h4>
                <select className={inputCls} value={polityId} onChange={(event) => setPolityId(event.target.value)}>
                  <option value="">{selectedChartType?.requires_polity ? 'Select polity...' : 'Optional polity...'}</option>
                  {polities.map((item) => (
                    <option key={item.id} value={item.id}>{item.label}</option>
                  ))}
                </select>
                {selectedPolity ? (
                  <p className="text-[11px] leading-5 text-slate-600 dark:text-slate-300">
                    {selectedPolity.capital || selectedPolity.default_location} {selectedPolity.timezone ? `| ${selectedPolity.timezone}` : ''}
                  </p>
                ) : null}
                {missingRequiredPolityOptions ? (
                  <div className={nestedCardCls}>
                    <div className="text-[11px] leading-5 text-slate-600 dark:text-slate-300">Polity options unavailable. Refresh the catalog.</div>
                  </div>
                ) : null}
                {selectedPolity && !selectedNationalChartOptions.length ? (
                  <div className={nestedCardCls}>
                    <div className="text-[11px] leading-5 text-slate-600 dark:text-slate-300">No registered national chart. Use Custom.</div>
                  </div>
                ) : null}
              </section>

              {selectedNationalChartOptions.length ? (
                <section className={`${mutedPanelCls} space-y-2`}>
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">National Chart</h4>
                  <select className={inputCls} value={nationalChartId} onChange={(event) => setNationalChartId(event.target.value)}>
                    <option value="">Default chart...</option>
                    {selectedNationalChartOptions.map((item) => (
                      <option key={item.id} value={item.id}>{item.label}</option>
                    ))}
                  </select>
                </section>
              ) : null}
            </>
          ) : (
            <section className={`${mutedPanelCls} space-y-2`}>
              <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Custom Reference Chart</h4>
              <input
                type="text"
                className={inputCls}
                placeholder={selectedChartType?.requires_polity ? 'Custom polity label' : 'Custom polity label (optional)'}
                value={customPolityLabel}
                onChange={(event) => setCustomPolityLabel(event.target.value)}
              />
              <input
                type="text"
                className={inputCls}
                placeholder="Custom chart label (optional)"
                value={customChartLabel}
                onChange={(event) => setCustomChartLabel(event.target.value)}
              />
              <div className="grid grid-cols-2 gap-2">
                <input type="date" className={inputCls} value={customChartDate} onChange={(event) => setCustomChartDate(event.target.value)} />
                <input type="time" step="60" className={inputCls} value={customChartTime} onChange={(event) => setCustomChartTime(event.target.value)} />
              </div>
              <input
                type="text"
                className={inputCls}
                placeholder="Custom chart location"
                value={customChartLocation}
                onChange={(event) => setCustomChartLocation(event.target.value)}
              />
              <input
                type="text"
                className={inputCls}
                placeholder="Custom chart timezone"
                value={customChartTimezone}
                onChange={(event) => setCustomChartTimezone(event.target.value)}
              />
            </section>
          )}

          <section className={`${mutedPanelCls} space-y-2`}>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Polity Context</h4>
            <select className={inputCls} value={locationContextType} onChange={(event) => setLocationContextType(event.target.value)}>
              <option value="">Default location context...</option>
              {contextTypes.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
            <input type="text" className={inputCls} placeholder="Visibility scope (optional)" value={visibilityScope} onChange={(event) => setVisibilityScope(event.target.value)} />
          </section>

          <section className={`${mutedPanelCls} space-y-2`}>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Scan Controls</h4>
            <select className={inputCls} value={scanModeId} onChange={(event) => setScanModeId(event.target.value)}>
              <option value="">Select scan mode...</option>
              {scanModes.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
            <select className={inputCls} value={regionId} onChange={(event) => setRegionId(event.target.value)}>
              <option value="">Select region...</option>
              {regions.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
            <select className={inputCls} value={resolutionId} onChange={(event) => setResolutionId(event.target.value)}>
              <option value="">Default resolution...</option>
              {resolutions.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
            <div className="grid grid-cols-3 gap-2">
              <input type="number" min="1" max="20" className={inputCls} placeholder="Top K" value={topK} onChange={(event) => setTopK(event.target.value)} />
              <input type="number" min="0" step="1" className={inputCls} placeholder="Min score" value={minimumScore} onChange={(event) => setMinimumScore(event.target.value)} />
              <input type="number" min="1" max={String(maxModeCandidates)} className={inputCls} placeholder="Candidates" value={candidateLimit} onChange={(event) => setCandidateLimit(event.target.value)} />
            </div>
            {selectedScanMode ? (
              <p className="text-[11px] leading-5 text-slate-600 dark:text-slate-300">
                Mode limit: {maxTimeSlices} time slices, {maxEvaluatedCells} evaluated cells.
                {selectedModeLimits?.default_time_step_hours ? ` Default step: ${selectedModeLimits.default_time_step_hours}h.` : ''}
                {defaultModeCandidateLimit ? ` Default candidates: ${defaultModeCandidateLimit}.` : ''}
                {selectedModeLimits?.async_only ? ' This mode is async-only.' : ''}
              </p>
            ) : null}
          </section>

          {scanModeId === 'spatial_scan' ? (
            <section className={`${mutedPanelCls} space-y-2`}>
              <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Fixed Event Anchor</h4>
              <div className="grid grid-cols-2 gap-2">
                <input type="date" className={inputCls} value={eventDate} onChange={(event) => setEventDate(event.target.value)} />
                <input type="time" step="60" className={inputCls} value={eventTime} onChange={(event) => setEventTime(event.target.value)} />
              </div>
            </section>
          ) : (
            <section className={`${mutedPanelCls} space-y-2`}>
              <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Time Window</h4>
              <div className="grid grid-cols-2 gap-2">
                <input type="date" className={inputCls} value={scanStartDate} onChange={(event) => setScanStartDate(event.target.value)} />
                <input type="time" step="60" className={inputCls} value={scanStartTime} onChange={(event) => setScanStartTime(event.target.value)} />
                <input type="date" className={inputCls} value={scanEndDate} onChange={(event) => setScanEndDate(event.target.value)} />
                <input type="time" step="60" className={inputCls} value={scanEndTime} onChange={(event) => setScanEndTime(event.target.value)} />
              </div>
              <input type="number" min="1" max="168" className={inputCls} placeholder="Time step (hours)" value={timeStepHours} onChange={(event) => setTimeStepHours(event.target.value)} />
              {estimatedTimeSlices ? (
                <p className="text-[11px] leading-5 text-slate-600 dark:text-slate-300">
                  Estimated workload: {estimatedTimeSlices} time slices{estimatedEvaluatedCells ? `, about ${estimatedEvaluatedCells} evaluated cells` : ''}.
                </p>
              ) : null}
            </section>
          )}

          <section className={`${mutedPanelCls} space-y-3`}>
            <div className="flex flex-wrap items-center gap-3">
              <button type="button" className={primaryActionButtonCls} onClick={handleScan} disabled={runningScan}>
                {runningScan ? 'Running Scan...' : 'Run Scan'}
              </button>
              <button
                type="button"
                className={secondaryActionButtonCls}
                onClick={() => {
                  setEventDate('');
                  setEventTime('');
                  setScanStartDate('');
                  setScanStartTime('');
                  setScanEndDate('');
                  setScanEndTime('');
                  setTimeStepHours(String(defaultModeTimeStepHours));
                }}
                disabled={runningScan}
              >
                Reset window
              </button>
            </div>
          </section>
        </fieldset>

        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      </aside>

      <section className={`${railCardCls} space-y-5 p-5`}>
        <section className={headerBandCls}>
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="max-w-3xl">
              <ConsoleBracketEyebrow module={MUNDANE_MODULE}>workspace / scan_console</ConsoleBracketEyebrow>
              <h3 className="mt-3 font-serif text-[1.9rem] font-medium tracking-[-0.04em] text-slate-900 dark:text-slate-50">
                {resultView === 'graph' && hasSeries ? 'Breakout graph and pressure matrix' : 'Scan results and breakout surfaces'}
              </h3>
            </div>
            {result ? (
              <div className="flex flex-wrap items-center gap-3 self-start">
                <ConsoleStatusBadge label={`${result?.counts?.returned ?? 0} returned`} tone="default" />
                <ScanOutputConsoleToggle value={resultView} onChange={setResultView} hasSeries={hasSeries} />
              </div>
            ) : null}
          </div>
        </section>

        {(runningScan || result) ? (
          <ConsoleCommandBand
            module={MUNDANE_MODULE}
            items={workspaceSummaryItems}
            statusLabel={runningScan ? 'running' : 'ready'}
            statusTone={runningScan ? 'accent' : 'good'}
            trailing={result ? <ScanOutputConsoleToggle value={resultView} onChange={setResultView} hasSeries={hasSeries} /> : null}
          />
        ) : null}

        <ScanProgressPanel progress={progress} running={runningScan} />
        {resultView === 'graph' && hasSeries ? (
          <ScanSeriesGraphPanel result={result} activePlaceLabel={activePlaceLabel} onSelectPlace={handleSelectPlace} />
        ) : (
          <ScanResultsConsolePanel result={result} activeRowKey={activeScanRow ? scanRowSelectionKey(activeScanRow) : ''} onSelectRow={handleSelectScanRow} />
        )}
      </section>

      <aside className={`${railCardCls} space-y-4 p-5`}>
        <section className={headerBandCls}>
          <ConsoleBracketEyebrow module={MUNDANE_MODULE}>research / inspector</ConsoleBracketEyebrow>
          <h3 className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-50">Scan inspector</h3>
        </section>

        {result ? (
          <ScanResearchConsolePanel result={result} resultView={resultView} activeRow={activeScanRow} activePlace={activeTopPlace} activeGraphPlace={activeGraphPlace} />
        ) : (
          <ConsoleEmptyState
            module={MUNDANE_MODULE}
            title="No scan output yet"
            detail="Run the scan to open scope, top-candidate, and backend-note surfaces."
          />
        )}
      </aside>
    </div>
  );
}
