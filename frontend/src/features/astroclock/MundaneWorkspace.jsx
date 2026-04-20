import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AstroClockAPI } from './api.mjs';
import MundaneScanWorkspace from './MundaneScanWorkspace.jsx';
import { buildChartTypeDomainOptions, isChartTypeDomainAllowed } from './mundaneDomainProfiles.mjs';
import {
  ConsoleBracketEyebrow,
  ConsoleEmptyState,
  ConsoleKpiStrip,
  ConsoleModeTabs,
  ConsoleRailSection,
  ConsoleSectionBar,
  ConsoleStatusBadge,
  ResearchMetricPill,
  ResearchSectionIntro,
  ResearchSegmentedToggle,
  researchWorkspaceCls,
  toneBadgeClass,
} from './researchWorkspacePrimitives.jsx';

let mundaneCatalogCache = null;
let mundaneCatalogPromise = null;

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

function buildEventDatetime(date, time) {
  const safeDate = String(date || '').trim();
  const safeTime = String(time || '').trim();
  if (!safeDate) return '';
  if (!safeTime) return `${safeDate}T00:00:00`;
  return `${safeDate}T${safeTime.length === 5 ? `${safeTime}:00` : safeTime}`;
}

function formatDateTime(value) {
  const raw = String(value || '').trim();
  if (!raw) return 'Current Astro Clock context';
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleString();
}

function uniqueById(rows = []) {
  const seen = new Set();
  return rows.filter((row) => {
    const id = normalizeId(row?.id);
    if (!id || seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}

const {
  railCardCls,
  sectionCardCls,
  nestedCardCls,
  emptyStateCls,
  sectionBandCls,
  headerBandCls,
  mutedPanelCls,
  inputCls,
  actionButtonCls,
  secondaryActionButtonCls,
  primaryActionButtonCls,
} = researchWorkspaceCls;
const MUNDANE_MODULE = 'mundane';

function SectionIntro(props) {
  return <ResearchSectionIntro {...props} banded module={MUNDANE_MODULE} />;
}

function levelTone(level) {
  const value = normalizeId(level);
  if (value === 'critical' || value === 'high') return 'danger';
  if (value === 'elevated') return 'warning';
  if (value === 'quiet') return 'good';
  return 'accent';
}

function ordinalSuffix(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value || '');
  const abs = Math.abs(Math.trunc(n));
  const mod100 = abs % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${abs}th`;
  const mod10 = abs % 10;
  if (mod10 === 1) return `${abs}st`;
  if (mod10 === 2) return `${abs}nd`;
  if (mod10 === 3) return `${abs}rd`;
  return `${abs}th`;
}

function formatNumeric(value, digits = 3) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? '');
  if (Number.isInteger(n)) return String(n);
  return n.toFixed(digits).replace(/\.?0+$/, '');
}

function formatSignalChip(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return formatNumeric(value);
  return String(value);
}

function buildSignalCard(key, value) {
  const id = normalizeId(key);
  const label = formatLabel(key);

  if (id === 'aggressor_house' || id === 'defender_house') {
    const data = value && typeof value === 'object' ? value : {};
    const role = id === 'aggressor_house' ? 'Aggressor' : 'Defender';
    const ruler = data.ruler ? String(data.ruler) : 'Unknown ruler';
    const sourceHouse = data.house ? ordinalSuffix(data.house) : null;
    const placedHouse = data.house_position ? ordinalSuffix(data.house_position) : null;
    const sign = data.sign ? String(data.sign) : null;
    const retrograde = typeof data.retrograde === 'boolean' ? data.retrograde : null;
    const summaryParts = [
      sourceHouse ? `${ruler} rules the ${sourceHouse} house` : `${ruler} is used as the ${role.toLowerCase()} ruler`,
      placedHouse ? `placed in the ${placedHouse} house` : null,
      sign ? `in ${sign}` : null,
    ].filter(Boolean);
    return {
      id,
      label,
      tone: 'accent',
      summary: `${summaryParts.join(', ')}.`,
      chips: [
        sourceHouse ? `Source House: ${sourceHouse}` : null,
        placedHouse ? `Placed: ${placedHouse}` : null,
        sign ? `Sign: ${sign}` : null,
        retrograde == null ? null : retrograde ? 'Retrograde' : 'Direct',
      ].filter(Boolean),
    };
  }

  if (id === 'angular_hits') {
    const hits = Array.isArray(value) ? value.filter(Boolean) : [];
    return {
      id,
      label,
      tone: hits.length ? 'warning' : 'default',
      summary: hits.length
        ? `${hits.length} angular ${hits.length === 1 ? 'hit is' : 'hits are'} shaping the chart emphasis.`
        : 'No angular emphasis was detected in the resolved chart.',
      chips: hits.slice(0, 8).map((hit) => {
        const parts = [
          hit?.planet ? String(hit.planet) : null,
          hit?.house != null ? `H${hit.house}` : null,
          hit?.sign ? String(hit.sign) : null,
        ].filter(Boolean);
        return parts.join(' ');
      }),
    };
  }

  if (id === 'activation_hits') {
    const hits = Array.isArray(value) ? value.filter(Boolean) : [];
    return {
      id,
      label,
      tone: hits.length ? 'warning' : 'good',
      summary: hits.length
        ? `${hits.length} eclipse-degree activation ${hits.length === 1 ? 'hit is' : 'hits are'} present in the overlay chart.`
        : 'No eclipse-degree activation hits were detected.',
      chips: hits.slice(0, 8).map((hit) => {
        const parts = [
          hit?.planet ? String(hit.planet) : null,
          hit?.target_point ? `to ${hit.target_point}` : null,
          hit?.orb_deg != null ? `orb ${formatNumeric(hit.orb_deg)}°` : null,
        ].filter(Boolean);
        return parts.join(' ');
      }),
    };
  }

  if (id === 'mars_retrograde') {
    const active = Boolean(value);
    return {
      id,
      label,
      tone: active ? 'warning' : 'good',
      summary: active
        ? 'Mars is retrograde in the resolved chart, which is treated as a reversal or failed-aggression warning.'
        : 'Mars is direct in the resolved chart, so no retrograde reversal warning is present.',
      chips: [active ? 'Retrograde' : 'Direct'],
    };
  }

  if (typeof value === 'boolean') {
    return {
      id,
      label,
      tone: value ? 'accent' : 'default',
      summary: value ? `${label} is present.` : `${label} is absent.`,
      chips: [value ? 'Present' : 'Absent'],
    };
  }

  if (Array.isArray(value)) {
    const rows = value.filter(Boolean);
    return {
      id,
      label,
      tone: rows.length ? 'accent' : 'default',
      summary: rows.length
        ? `${rows.length} structured ${rows.length === 1 ? 'item is' : 'items are'} attached to this signal.`
        : 'No items are attached to this signal.',
      chips: rows.slice(0, 8).map((item) => {
        if (item && typeof item === 'object') {
          return item.label || item.id || item.watchpoint || JSON.stringify(item);
        }
        return String(item);
      }),
    };
  }

  if (value && typeof value === 'object') {
    const entries = Object.entries(value)
      .filter(([, itemValue]) => itemValue != null && itemValue !== '')
      .slice(0, 8);
    return {
      id,
      label,
      tone: 'default',
      summary: `${label} resolved as structured chart data.`,
      chips: entries.map(([entryKey, entryValue]) => `${formatLabel(entryKey)}: ${formatSignalChip(entryValue)}`),
    };
  }

  return {
    id,
    label,
    tone: 'default',
    summary: formatSignalChip(value) || 'No value provided.',
    chips: [],
  };
}

function MetricPill(props) {
  return <ResearchMetricPill {...props} />;
}

function SummaryList({ items }) {
  const rows = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!rows.length) return <p className="text-sm text-slate-500 dark:text-slate-400">No items.</p>;
  return (
    <div className="space-y-3">
      {rows.map((item, index) => {
        const data = item && typeof item === 'object' ? item : { value: item };
        const label = data.label || data.id || data.watchpoint || `Item ${index + 1}`;
        const detailEntries = Object.entries(data)
          .filter(([key, value]) => !['label', 'id', 'watchpoint'].includes(key) && value != null && value !== '' && !Array.isArray(value) && typeof value !== 'object')
          .slice(0, 5);
        return (
          <div key={`${label}-${index}`} className={nestedCardCls}>
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{label}</div>
              {data.status ? (
                <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] ${toneBadgeClass(levelTone(data.status))}`}>
                  {String(data.status).replace(/_/g, ' ')}
                </span>
              ) : null}
            </div>
            {data.summary ? <p className="mt-1.5 text-sm leading-6 text-slate-600 dark:text-slate-300">{data.summary}</p> : null}
            {detailEntries.length ? (
              <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-600 dark:text-slate-300">
                {detailEntries.map(([key, value]) => (
                  <span key={key} className="rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 dark:border-slate-700 dark:bg-slate-950/40">
                    {formatLabel(key)}: {String(value)}
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

function NoteList({ title, notes }) {
  const rows = Array.isArray(notes) ? notes.filter(Boolean) : [];
  if (!rows.length) return null;
  return (
    <section className={sectionCardCls}>
      <SectionIntro eyebrow="Doctrine" title={title} />
      <div className="mt-4 space-y-3">
        {rows.map((note, index) => (
          <div key={`${note.id || title}-${index}`} className={nestedCardCls}>
            <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">{note.summary || 'No summary provided.'}</p>
            {Array.isArray(note.source_tags) && note.source_tags.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {note.source_tags.map((tag) => (
                  <span key={tag} className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-slate-500 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
                    {formatLabel(tag)}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function SourceList({ title, sources }) {
  const rows = uniqueById(Array.isArray(sources) ? sources : []);
  if (!rows.length) return null;
  return (
    <section className={sectionCardCls}>
      <SectionIntro eyebrow="Sources" title={title} />
      <div className="mt-4 space-y-3">
        {rows.map((source) => (
          <div key={source.id} className={nestedCardCls}>
            <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{source.label || formatLabel(source.id)}</div>
            {source.citation ? <p className="mt-1.5 text-sm leading-6 text-slate-600 dark:text-slate-300">{source.citation}</p> : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function MatchedRules({ rules }) {
  const rows = Array.isArray(rules) ? rules.filter(Boolean) : [];
  if (!rows.length) {
    return (
      <section className={sectionCardCls}>
        <SectionIntro eyebrow="Rules" title="Matched Rules" />
      </section>
    );
  }
  return (
    <section className={sectionCardCls}>
      <SectionIntro eyebrow="Rules" title="Matched Rules" />
      <div className="mt-4 space-y-3">
        {rows.map((rule) => (
          <div key={rule.id} className={nestedCardCls}>
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{rule.label || formatLabel(rule.id)}</div>
              <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] ${toneBadgeClass((Number(rule.weight) || 0) >= 0 ? 'warning' : 'good')}`}>
                {Number(rule.weight) >= 0 ? '+' : ''}{rule.weight || 0}
              </span>
            </div>
            {rule.detail ? <p className="mt-1.5 text-sm leading-6 text-slate-600 dark:text-slate-300">{rule.detail}</p> : null}
            {Array.isArray(rule.source_tags) && rule.source_tags.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {rule.source_tags.map((tag) => (
                  <span key={tag} className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-slate-500 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
                    {formatLabel(tag)}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function CalibrationPanel({ assessment, research }) {
  const calibration = assessment?.calibration || {};
  return (
    <section className={sectionCardCls}>
      <SectionIntro eyebrow="Calibration" title="Benchmark Coverage" />
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <MetricPill label="Level" value={formatLabel(assessment?.level || 'quiet')} tone={levelTone(assessment?.level)} />
        <MetricPill label="Raw Level" value={formatLabel(assessment?.raw_level || 'quiet')} tone="default" />
        <MetricPill label="Score" value={assessment?.score ?? 0} tone={levelTone(assessment?.level)} />
        <MetricPill label="Raw Score" value={assessment?.raw_score ?? 0} tone="default" />
        <MetricPill label="Coverage" value={formatLabel(calibration.coverage_tier || 'unseeded')} tone="accent" />
        <MetricPill label="Cases" value={calibration.unique_case_count ?? 0} tone="default" />
      </div>
      <div className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
        <div>Dataset rows: {calibration.dataset_row_count ?? 0}</div>
        <div>Source breadth: {calibration.distinct_source_count ?? 0}</div>
        <div>Confidence factor: {calibration.confidence_factor ?? 0}</div>
        <div>Score cap: {calibration.score_cap ?? 0}</div>
        <div>Research status: {formatLabel(research?.status || 'research_gated')}</div>
      </div>
      {Array.isArray(calibration.gaps) && calibration.gaps.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {calibration.gaps.map((gap) => (
            <span key={gap} className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
              {formatLabel(gap)}
            </span>
          ))}
        </div>
      ) : null}
      {Array.isArray(research?.flags) && research.flags.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {research.flags.map((flag) => (
            <span key={flag} className="rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
              {formatLabel(flag)}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ContextPanel({ context, doctrine }) {
  const resolution = doctrine?.chart_resolution || context?.chart_resolution || {};
  const primaryChart = resolution?.primary_chart || null;
  const supportingCharts = Array.isArray(resolution?.supporting_charts) ? resolution.supporting_charts : [];
  const polity = context?.polity || null;
  const referenceChart = context?.reference_chart || null;
  const signalCards = Object.entries(resolution?.signals || {})
    .filter(([, value]) => value != null && value !== '')
    .map(([key, value]) => buildSignalCard(key, value));

  return (
    <section className={sectionCardCls}>
      <SectionIntro eyebrow="Resolved Context" title="Chart Stack And Frame" />
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <MetricPill label="Chart Type" value={context?.chart_type?.label || 'Unknown'} tone="accent" />
        <MetricPill label="Domain" value={context?.domain?.label || 'Unknown'} tone="accent" />
        <MetricPill label="Polity" value={polity?.label || 'No polity frame'} tone={polity ? 'accent' : 'default'} />
        <MetricPill label="Location Context" value={context?.location_context?.label || 'Unknown'} tone="default" />
        <MetricPill label="Reference Chart" value={referenceChart?.label || 'No reference chart'} tone={referenceChart ? 'accent' : 'default'} />
        <MetricPill label="Event Time" value={formatDateTime(context?.event_context?.event_datetime)} tone="default" />
      </div>
      <div className="mt-4 space-y-4">
        {primaryChart ? (
          <div className={nestedCardCls}>
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Primary Chart</div>
            <div className="mt-2 text-sm font-medium text-slate-900 dark:text-slate-50">{primaryChart.label || formatLabel(primaryChart.kind)}</div>
            <div className="mt-1.5 text-sm text-slate-600 dark:text-slate-300">
              {formatDateTime(primaryChart.computed_datetime || primaryChart.datetime)} {primaryChart.location ? `| ${primaryChart.location}` : ''}
            </div>
          </div>
        ) : null}
        {referenceChart ? (
          <div className={nestedCardCls}>
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Reference Chart</div>
            <div className="mt-2 text-sm font-medium text-slate-900 dark:text-slate-50">{referenceChart.label || 'Reference Chart'}</div>
            <div className="mt-1.5 text-sm text-slate-600 dark:text-slate-300">
              {formatDateTime(referenceChart.datetime)} {referenceChart.location ? `| ${referenceChart.location}` : ''}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {referenceChart.selection_basis ? (
                <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
                  Selection: {formatLabel(referenceChart.selection_basis)}
                </span>
              ) : null}
              {referenceChart.status ? (
                <span className={`rounded-full border px-2 py-0.5 text-[11px] ${toneBadgeClass(levelTone(referenceChart.status))}`}>
                  {formatLabel(referenceChart.status)}
                </span>
              ) : null}
            </div>
          </div>
        ) : null}
        {supportingCharts.length ? (
          <div>
            <div className="text-xs uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Supporting Charts</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {supportingCharts.map((chart, index) => (
                <span key={`${chart.id || chart.kind || 'support'}-${index}`} className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
                  {chart.label || formatLabel(chart.kind || `support_${index + 1}`)}
                </span>
              ))}
            </div>
          </div>
        ) : null}
        {signalCards.length ? (
          <div>
            <div className="text-xs uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Signals</div>
            <div className="mt-2 grid gap-3 md:grid-cols-2">
              {signalCards.map((card) => (
                <div key={card.id} className={nestedCardCls}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                      {card.label}
                    </div>
                    {card.tone && card.tone !== 'default' ? (
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] ${toneBadgeClass(card.tone)}`}>
                        {formatLabel(card.tone)}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-200">{card.summary}</p>
                  {Array.isArray(card.chips) && card.chips.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {card.chips.map((chip) => (
                        <span key={`${card.id}-${chip}`} className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
                          {chip}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function WorkspaceModeToggle({ value, onChange }) {
  const modes = [
    { id: 'scan', label: 'Scan' },
    { id: 'analysis', label: 'Analysis' },
  ];
  return <ConsoleModeTabs options={modes} value={value} onChange={onChange} />;
}

function ChartSourceToggle({ value, onChange }) {
  const options = [
    { id: 'registered', label: 'Registered' },
    { id: 'custom', label: 'Custom' },
  ];
  return (
    <ResearchSegmentedToggle
      options={options}
      value={value}
      onChange={onChange}
      buttonClassName="rounded-xl px-3.5 py-2 text-sm font-medium transition"
    />
  );
}

export default function MundaneWorkspace({ open, defaultHouseSystem = 'R' }) {
  const [catalog, setCatalog] = useState(() => mundaneCatalogCache);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [workspaceMode, setWorkspaceMode] = useState('scan');
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
  const [referenceLocation, setReferenceLocation] = useState('');
  const [referenceLocationMode, setReferenceLocationMode] = useState('auto');
  const [eventDate, setEventDate] = useState('');
  const [eventTime, setEventTime] = useState('');
  const [eventLocation, setEventLocation] = useState('');
  const [eventTimezone, setEventTimezone] = useState('');
  const [eventTimezoneMode, setEventTimezoneMode] = useState('auto');
  const [resolvedContext, setResolvedContext] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loadingResolve, setLoadingResolve] = useState(false);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [error, setError] = useState('');
  const resolveRequestIdRef = useRef(0);
  const analyzeRequestIdRef = useRef(0);

  const chartTypes = Array.isArray(catalog?.chart_types) ? catalog.chart_types : [];
  const domains = Array.isArray(catalog?.domains) ? catalog.domains : [];
  const contextTypes = Array.isArray(catalog?.context_types) ? catalog.context_types : [];
  const polities = Array.isArray(catalog?.polities) ? catalog.polities : [];

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
  const usingCustomChartSource = chartSourceMode === 'custom';
  const customChartDatetime = useMemo(
    () => buildEventDatetime(customChartDate, customChartTime),
    [customChartDate, customChartTime],
  );
  const effectivePolityProvided = usingCustomChartSource
    ? Boolean(String(customPolityLabel || '').trim())
    : Boolean(polityId);

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
    referenceLocation: referenceLocation || undefined,
    eventDatetime: buildEventDatetime(eventDate, eventTime) || undefined,
    eventLocation: eventLocation || undefined,
    eventTimezone: eventTimezone || undefined,
    houseSystem: defaultHouseSystem,
  }), [
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
    eventLocation,
    eventTime,
    eventTimezone,
    locationContextType,
    nationalChartId,
    polityId,
    referenceLocation,
    usingCustomChartSource,
    visibilityScope,
  ]);
  const requestSignature = useMemo(() => JSON.stringify(requestPayload), [requestPayload]);
  const latestRequestSignatureRef = useRef(requestSignature);

  const loadCatalog = useCallback(async () => {
    if (mundaneCatalogCache) {
      setCatalog(mundaneCatalogCache);
      return;
    }
    setLoadingCatalog(true);
    setCatalogError('');
    try {
      if (!mundaneCatalogPromise) {
        mundaneCatalogPromise = AstroClockAPI.listMundaneChartTypes()
          .then((res) => {
            const data = res?.success ? res.data : null;
            mundaneCatalogCache = data || null;
            return mundaneCatalogCache;
          })
          .finally(() => {
            mundaneCatalogPromise = null;
          });
      }
      const data = await mundaneCatalogPromise;
      setCatalog(data || null);
    } catch (nextError) {
      setCatalog(null);
      setCatalogError(nextError?.message || 'Failed to load mundane catalog.');
    } finally {
      setLoadingCatalog(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    loadCatalog();
  }, [loadCatalog, open]);

  useEffect(() => {
    if (!open) return;
    setResolvedContext(null);
    setAnalysis(null);
    setError('');
  }, [open]);

  useEffect(() => {
    latestRequestSignatureRef.current = requestSignature;
  }, [requestSignature]);

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
    if (eventTimezoneMode === 'auto') {
      setEventTimezone(String(selectedPolity.timezone || ''));
    }
    if (referenceLocationMode === 'auto') {
      setReferenceLocation(String(selectedPolity.default_location || selectedPolity.capital || ''));
    }
  }, [
    eventTimezoneMode,
    nationalChartId,
    referenceLocationMode,
    selectedNationalChartOptions,
    selectedPolity,
    usingCustomChartSource,
  ]);

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
    setResolvedContext(null);
    setAnalysis(null);
    setError('');
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
    referenceLocation,
    eventDate,
    eventTime,
    eventLocation,
    eventTimezone,
    open,
  ]);

  const handleResolve = useCallback(async () => {
    if (!chartTypeId) {
      setError('Choose a chart type first.');
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
    const requestId = resolveRequestIdRef.current + 1;
    resolveRequestIdRef.current = requestId;
    const expectedSignature = requestSignature;
    setLoadingResolve(true);
    setError('');
    try {
      const res = await AstroClockAPI.resolveMundaneContext(requestPayload);
      if (
        resolveRequestIdRef.current !== requestId
        || latestRequestSignatureRef.current !== expectedSignature
      ) {
        return;
      }
      if (!res?.success) throw new Error('Failed to resolve mundane context.');
      setResolvedContext(res.data?.context || null);
    } catch (nextError) {
      if (
        resolveRequestIdRef.current !== requestId
        || latestRequestSignatureRef.current !== expectedSignature
      ) {
        return;
      }
      setResolvedContext(null);
      setError(nextError?.message || 'Failed to resolve mundane context.');
    } finally {
      if (resolveRequestIdRef.current === requestId) {
        setLoadingResolve(false);
      }
    }
  }, [
    chartTypeId,
    customChartDatetime,
    customChartLocation,
    customChartTimezone,
    effectivePolityProvided,
    requestPayload,
    requestSignature,
    selectedChartType?.requires_polity,
    usingCustomChartSource,
  ]);

  const handleAnalyze = useCallback(async () => {
    if (!chartTypeId) {
      setError('Choose a chart type first.');
      return;
    }
    if (!domainId) {
      setError('Choose a mundane domain first.');
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
    const requestId = analyzeRequestIdRef.current + 1;
    analyzeRequestIdRef.current = requestId;
    const expectedSignature = requestSignature;
    setLoadingAnalyze(true);
    setError('');
    try {
      const res = await AstroClockAPI.analyzeMundane(requestPayload);
      if (
        analyzeRequestIdRef.current !== requestId
        || latestRequestSignatureRef.current !== expectedSignature
      ) {
        return;
      }
      if (!res?.success) throw new Error('Failed to analyze mundane context.');
      setAnalysis(res.data || null);
      setResolvedContext(res.data?.context || null);
    } catch (nextError) {
      if (
        analyzeRequestIdRef.current !== requestId
        || latestRequestSignatureRef.current !== expectedSignature
      ) {
        return;
      }
      setAnalysis(null);
      setError(nextError?.message || 'Failed to analyze mundane context.');
    } finally {
      if (analyzeRequestIdRef.current === requestId) {
        setLoadingAnalyze(false);
      }
    }
  }, [
    chartTypeId,
    customChartDatetime,
    customChartLocation,
    customChartTimezone,
    domainId,
    effectivePolityProvided,
    requestPayload,
    requestSignature,
    selectedChartType?.requires_polity,
    usingCustomChartSource,
  ]);

  const activeContext = analysis?.context || resolvedContext || null;
  const domainAssessment = analysis?.domain_assessment || null;
  const doctrine = analysis?.doctrine || null;
  const research = analysis?.research || null;

  if (workspaceMode === 'scan') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-end">
          <WorkspaceModeToggle value={workspaceMode} onChange={setWorkspaceMode} />
        </div>
        <MundaneScanWorkspace open={open} defaultHouseSystem={defaultHouseSystem} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <WorkspaceModeToggle value={workspaceMode} onChange={setWorkspaceMode} />
      </div>
      <div className="grid gap-6 lg:grid-cols-[336px_minmax(0,1.75fr)_332px]">
        <aside className={`${railCardCls} space-y-4 p-4`}>
          <section className={headerBandCls}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <ConsoleBracketEyebrow module={MUNDANE_MODULE}>workspace / setup_console</ConsoleBracketEyebrow>
                <h3 className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50">Mundane Analysis</h3>
              </div>
              <button type="button" className={actionButtonCls} onClick={loadCatalog} disabled={loadingCatalog}>
                {loadingCatalog ? 'Loading...' : 'Refresh'}
              </button>
            </div>
          </section>
          {catalogError ? <p className="text-xs text-rose-600">{catalogError}</p> : null}

          <ConsoleRailSection title="Chart Type" eyebrow="input" module={MUNDANE_MODULE} bodyClassName="mt-3">
            <select className={inputCls} value={chartTypeId} onChange={(event) => setChartTypeId(event.target.value)}>
              <option value="">Select chart type...</option>
              {chartTypes.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </ConsoleRailSection>

          <ConsoleRailSection title="Domain Lens" eyebrow="lens" module={MUNDANE_MODULE} bodyClassName="mt-3">
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
          </ConsoleRailSection>

          <ConsoleRailSection title="Chart Source" eyebrow="source" module={MUNDANE_MODULE} bodyClassName="mt-3">
            <ChartSourceToggle value={chartSourceMode} onChange={setChartSourceMode} />
          </ConsoleRailSection>

          {!usingCustomChartSource ? (
            <>
              <ConsoleRailSection title="Polity" eyebrow="reference" module={MUNDANE_MODULE}>
                <select
                  className={inputCls}
                  value={polityId}
                  onChange={(event) => setPolityId(event.target.value)}
                >
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
                {selectedPolity && !selectedNationalChartOptions.length ? (
                  <div className={nestedCardCls}>
                    <p className="text-[11px] leading-5 text-slate-600 dark:text-slate-300">
                      No registered national chart is attached to this polity. Switch to <span className="font-medium text-slate-900 dark:text-slate-50">Custom</span> to test a manual chart.
                    </p>
                  </div>
                ) : null}
              </ConsoleRailSection>

              {selectedNationalChartOptions.length ? (
                <ConsoleRailSection title="National Chart" eyebrow="reference" module={MUNDANE_MODULE} bodyClassName="mt-3">
                  <select className={inputCls} value={nationalChartId} onChange={(event) => setNationalChartId(event.target.value)}>
                    <option value="">Default chart...</option>
                    {selectedNationalChartOptions.map((item) => (
                      <option key={item.id} value={item.id}>{item.label}</option>
                    ))}
                  </select>
                </ConsoleRailSection>
              ) : null}
            </>
          ) : (
            <ConsoleRailSection title="Custom Reference Chart" eyebrow="reference" module={MUNDANE_MODULE}>
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
              <div className={nestedCardCls}>
                <p className="text-[11px] leading-5 text-slate-600 dark:text-slate-300">
                  Custom charts stay exploratory. The backend returns them as user-supplied, unverified, and not registry-backed.
                </p>
              </div>
            </ConsoleRailSection>
          )}

          <ConsoleRailSection title="Context Overrides" eyebrow="context" module={MUNDANE_MODULE}>
            <select className={inputCls} value={locationContextType} onChange={(event) => setLocationContextType(event.target.value)}>
              <option value="">Default location context...</option>
              {contextTypes.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
            <input
              type="text"
              className={inputCls}
              placeholder="Reference location (optional)"
              value={referenceLocation}
              onChange={(event) => {
                const nextValue = event.target.value;
                setReferenceLocation(nextValue);
                setReferenceLocationMode(nextValue.trim() ? 'manual' : 'auto');
              }}
            />
            <input
              type="text"
              className={inputCls}
              placeholder="Visibility scope (optional)"
              value={visibilityScope}
              onChange={(event) => setVisibilityScope(event.target.value)}
            />
          </ConsoleRailSection>

          <ConsoleRailSection title="Event Overrides" eyebrow="event" module={MUNDANE_MODULE}>
            <div className="grid grid-cols-2 gap-2">
              <input type="date" className={inputCls} value={eventDate} onChange={(event) => setEventDate(event.target.value)} />
              <input type="time" step="60" className={inputCls} value={eventTime} onChange={(event) => setEventTime(event.target.value)} />
            </div>
            <input
              type="text"
              className={inputCls}
              placeholder="Event location (optional)"
              value={eventLocation}
              onChange={(event) => setEventLocation(event.target.value)}
            />
            <input
              type="text"
              className={inputCls}
              placeholder="Event timezone (optional)"
              value={eventTimezone}
              onChange={(event) => {
                const nextValue = event.target.value;
                setEventTimezone(nextValue);
                setEventTimezoneMode(nextValue.trim() ? 'manual' : 'auto');
              }}
            />
          </ConsoleRailSection>

          <section className={`${sectionBandCls} flex flex-wrap gap-2`}>
            <button type="button" className={secondaryActionButtonCls} onClick={handleResolve} disabled={loadingResolve || loadingAnalyze}>
              {loadingResolve ? 'Resolving...' : 'Resolve Context'}
            </button>
            <button type="button" className={primaryActionButtonCls} onClick={handleAnalyze} disabled={loadingAnalyze || loadingResolve}>
              {loadingAnalyze ? 'Analyzing...' : 'Analyze'}
            </button>
          </section>

          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        </aside>

        <section className={`${railCardCls} space-y-5 p-4`}>
          <section className={headerBandCls}>
            <ConsoleBracketEyebrow module={MUNDANE_MODULE}>workspace / analysis_console</ConsoleBracketEyebrow>
            <h3 className="mt-3 font-serif text-[1.9rem] font-medium tracking-[-0.04em] text-slate-900 dark:text-slate-50">Mundane Analysis</h3>
          </section>

          {activeContext ? (
            <ContextPanel context={activeContext} doctrine={doctrine} />
          ) : (
            <ConsoleEmptyState
              module={MUNDANE_MODULE}
              title="No resolved context yet"
              detail="Resolve or analyze a chart to load the context surface."
            />
          )}

          {analysis ? (
            <>
              <section className={sectionCardCls}>
                <ConsoleSectionBar
                  module={MUNDANE_MODULE}
                  label="assessment"
                  right={<ConsoleStatusBadge label={formatLabel(domainAssessment?.level || 'quiet')} tone={levelTone(domainAssessment?.level)} />}
                />
                <div className="mt-3 text-lg font-semibold text-slate-900 dark:text-slate-50">
                  {domainAssessment?.summary || 'No assessment summary.'}
                </div>
                <div className="mt-4">
                  <ConsoleKpiStrip
                    module={MUNDANE_MODULE}
                    metrics={[
                      { label: 'Level', value: formatLabel(domainAssessment?.level || 'quiet') },
                      { label: 'Score', value: domainAssessment?.score ?? 0 },
                      { label: 'Raw level', value: formatLabel(domainAssessment?.raw_level || 'quiet') },
                      { label: 'Raw score', value: domainAssessment?.raw_score ?? 0 },
                    ]}
                  />
                </div>
              </section>
              <section className={sectionCardCls}>
                <SectionIntro eyebrow="Layer" title="Framework Layer" />
                <div className="mt-4">
                  <SummaryList items={analysis?.framework_layer?.items} />
                </div>
              </section>
              <section className={sectionCardCls}>
                <SectionIntro eyebrow="Layer" title="Trigger Layer" />
                <div className="mt-4">
                  <SummaryList items={analysis?.trigger_layer?.items} />
                </div>
              </section>
              <section className={sectionCardCls}>
                <SectionIntro eyebrow="Layer" title="Activation Layer" />
                <div className="mt-4">
                  <SummaryList items={analysis?.activation_layer?.items} />
                </div>
              </section>
              <NoteList title="Domain Notes" notes={analysis?.doctrine?.domain_notes} />
            </>
          ) : null}
        </section>

        <aside className={`${railCardCls} space-y-4 p-4`}>
          <section className={headerBandCls}>
            <ConsoleBracketEyebrow module={MUNDANE_MODULE}>research / sources</ConsoleBracketEyebrow>
            <h3 className="mt-2 text-base font-semibold text-slate-900 dark:text-slate-50">Calibration and Sources</h3>
          </section>

          {analysis ? (
            <>
              <CalibrationPanel assessment={domainAssessment} research={research} />
              <MatchedRules rules={domainAssessment?.matched_rules} />
              <SourceList title="Matched Rule Sources" sources={analysis?.doctrine?.matched_rule_sources} />
              <SourceList title="Doctrine Sources" sources={analysis?.doctrine?.sources} />
              <NoteList title="Chart Type Notes" notes={analysis?.doctrine?.chart_type_notes} />
              <NoteList title="Context Notes" notes={analysis?.doctrine?.context_notes} />
            </>
          ) : (
            <ConsoleEmptyState
              module={MUNDANE_MODULE}
              title="No analysis yet"
              detail="Analyze a chart to open calibration and source surfaces."
            />
          )}
        </aside>
      </div>
    </div>
  );
}
