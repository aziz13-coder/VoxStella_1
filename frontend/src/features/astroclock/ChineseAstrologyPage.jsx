import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown, Compass, Copy, Download, History, RotateCcw, Save, Trash2 } from 'lucide-react';
import { AstroClockAPI } from './api.mjs';

const PILLAR_ORDER = ['hour', 'day', 'month', 'year'];
const PILLAR_LABELS = {
  hour: 'Hour',
  day: 'Day',
  month: 'Month',
  year: 'Year',
};
const STEM_GLYPHS = {
  Jia: '甲',
  Yi: '乙',
  Bing: '丙',
  Ding: '丁',
  Wu: '戊',
  Ji: '己',
  Geng: '庚',
  Xin: '辛',
  Ren: '壬',
  Gui: '癸',
};
const BRANCH_GLYPHS = {
  Zi: '子',
  Chou: '丑',
  Yin: '寅',
  Mao: '卯',
  Chen: '辰',
  Si: '巳',
  Wu: '午',
  Wei: '未',
  Shen: '申',
  You: '酉',
  Xu: '戌',
  Hai: '亥',
};
const ELEMENTS = ['Wood', 'Fire', 'Earth', 'Metal', 'Water'];
const CALCULATION_SEX_OPTIONS = [
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
];
const CALCULATION_SEX_GLOBAL_OPTIONS = [
  { value: 'unset', label: 'Not Set' },
  ...CALCULATION_SEX_OPTIONS,
];
const DAY_BOUNDARY_OPTIONS = [
  { value: 'civil_midnight', label: 'Civil Day' },
  { value: 'true_solar_midnight', label: 'Solar Day' },
];
const HOUR_VARIANT_OPTIONS = [
  { value: 'standard_zi_hour', label: 'Standard Zi' },
  { value: 'late_zi_next_day', label: 'Late Zi +1' },
];
const LUCK_DIRECTION_OPTIONS = [
  { value: 'year_stem_polarity', label: 'Year Stem' },
  { value: 'year_branch_polarity', label: 'Year Branch' },
  { value: 'day_stem_polarity', label: 'Day Stem' },
];
const RELATIONSHIP_CONTEXT_OPTIONS = [
  { value: 'general', label: 'General' },
  { value: 'romantic', label: 'Romantic' },
  { value: 'family', label: 'Family' },
  { value: 'business', label: 'Business' },
];
const ORACLE_METHOD_OPTIONS = [
  { value: 'coins', label: 'Coin Cast' },
  { value: 'yarrow', label: 'Yarrow Model' },
  { value: 'manual', label: 'Manual Lines' },
];
const ORACLE_COIN_SCHEME_OPTIONS = [
  { value: 'heads_2_tails_3', label: 'Heads 2' },
  { value: 'heads_3_tails_2', label: 'Heads 3' },
];
const ORACLE_LINE_OPTIONS = [
  { value: 6, label: '6 old yin' },
  { value: 7, label: '7 young yang' },
  { value: 8, label: '8 young yin' },
  { value: 9, label: '9 old yang' },
];
const DEFAULT_ORACLE_LINES = [7, 7, 7, 7, 7, 7];
const DEFAULT_PREFERENCES = {
  activeTab: 'chart',
  calculationSex: '',
  comparisonSnapId: '',
  dayBoundaryRule: 'civil_midnight',
  hourPillarVariant: 'standard_zi_hour',
  luckDirectionRule: 'year_stem_polarity',
  relationshipCalculationSex: '',
  relationshipContext: 'general',
  sourceMode: 'snap',
  useTrueSolarTime: false,
};
const PAPER = 'bg-white';
const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };
const glyphStyle = { fontFamily: '"Segoe UI Symbol", "Noto Sans Symbols 2", "Noto Sans Symbols", "DejaVu Sans", sans-serif' };
const underlineControlClass = 'mt-2 w-full min-w-0 border-b border-zinc-200 bg-white pb-2 text-[12px] text-zinc-600 outline-none transition focus:border-teal-500 disabled:opacity-55';
const primaryActionClass = 'rounded-full border border-zinc-950 bg-zinc-950 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-white transition hover:bg-zinc-800 disabled:opacity-50';
const secondaryActionClass = 'inline-flex items-center justify-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-600 transition hover:border-zinc-400 hover:text-zinc-950 disabled:opacity-55';
const PREFERENCES_KEY = 'voxstella.chineseAstrology.preferences.v1';
const SAVED_READINGS_KEY = 'voxstella.chineseAstrology.savedReadings.v1';
const SHOW_DEV_METHOD_SURFACE = import.meta.env.DEV;
const PRIMARY_TAB_CONFIG = [
  ['chart', 'Four Pillars'],
  ['reading', 'Overview'],
  ['elements', 'Element Balance'],
  ['timing', 'Life Timing'],
  ['relationships', 'Relationships'],
];
const ANALYSIS_TAB_CONFIG = [
  ...(SHOW_DEV_METHOD_SURFACE ? [['day-master', 'Day Master']] : []),
  ['ten-gods', 'Ten Gods'],
  ['useful', 'Helpful Elements'],
  ['palaces', 'Life Areas'],
  ['stars', 'Auxiliary Stars'],
  ['classical', 'Classical Extras'],
];
const UTILITY_TAB_CONFIG = SHOW_DEV_METHOD_SURFACE ? [['notes', 'Method Notes']] : [];
const ORACLE_TAB = ['oracle', 'I Ching Oracle'];
const TAB_CONFIG = [...PRIMARY_TAB_CONFIG, ...ANALYSIS_TAB_CONFIG, ...UTILITY_TAB_CONFIG, ORACLE_TAB];
const VALID_TAB_IDS = new Set([
  ...TAB_CONFIG.map(([id]) => id),
  ...(SHOW_DEV_METHOD_SURFACE ? ['debug'] : []),
]);

const TEN_GOD_FACTOR_FALLBACKS = {
  Companion: {
    chinese: '比劫',
    pinyin: 'bi jie',
    relation_chinese: '同我',
    relation_label: 'same element as the Day Master',
    domain_summary: 'Peers, siblings, confidence, independence, competition, and shared resources.',
  },
  Output: {
    chinese: '食傷',
    pinyin: 'shi shang',
    relation_chinese: '我生',
    relation_label: 'the Day Master produces this element',
    domain_summary: 'Expression, talent, production, communication, craft, and visible output.',
  },
  Wealth: {
    chinese: '財星',
    pinyin: 'cai xing',
    relation_chinese: '我克',
    relation_label: 'the Day Master controls this element',
    domain_summary: 'Value, assets, money handling, practical management, and material responsibilities.',
  },
  Influence: {
    chinese: '官殺',
    pinyin: 'guan sha',
    relation_chinese: '克我',
    relation_label: 'this element controls the Day Master',
    domain_summary: 'Rules, pressure, authority, responsibility, discipline, status, and career structure.',
  },
  Resource: {
    chinese: '印梟',
    pinyin: 'yin xiao',
    relation_chinese: '生我',
    relation_label: 'this element produces the Day Master',
    domain_summary: 'Learning, protection, credentials, counsel, support, recovery, and intuition.',
  },
};

function normalizeChineseAstrologyTabId(id) {
  if (id === 'debug') return SHOW_DEV_METHOD_SURFACE ? 'notes' : 'chart';
  return VALID_TAB_IDS.has(id) ? id : 'chart';
}

function readPreferences() {
  if (typeof window === 'undefined' || !window.localStorage) return {};
  try {
    const parsed = JSON.parse(window.localStorage.getItem(PREFERENCES_KEY) || '{}');
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (_) {
    return {};
  }
}

function writePreferences(preferences) {
  if (typeof window === 'undefined' || !window.localStorage) return;
  try {
    window.localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
  } catch (_) {}
}

function clearPreferences() {
  if (typeof window === 'undefined' || !window.localStorage) return;
  try {
    window.localStorage.removeItem(PREFERENCES_KEY);
  } catch (_) {}
}

function normalizeRelationshipContext(value) {
  const key = String(value || '').trim();
  return RELATIONSHIP_CONTEXT_OPTIONS.some((option) => option.value === key) ? key : 'general';
}

function normalizeCalculationSex(value) {
  const key = String(value || '').trim().toLowerCase();
  return key === 'female' || key === 'male' ? key : '';
}

function readSavedReadingSnapshots() {
  if (typeof window === 'undefined' || !window.localStorage) return [];
  try {
    const parsed = JSON.parse(window.localStorage.getItem(SAVED_READINGS_KEY) || '[]');
    return Array.isArray(parsed) ? parsed.filter((row) => row?.id && row?.payload?.profile) : [];
  } catch (_) {
    return [];
  }
}

function clearSavedReadingSnapshots() {
  if (typeof window === 'undefined' || !window.localStorage) return false;
  try {
    window.localStorage.removeItem(SAVED_READINGS_KEY);
    return true;
  } catch (_) {
    return false;
  }
}

function firstPresent(...values) {
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

function getSnapMetaParts(snap) {
  const dashboard = snapDashboard(snap);
  const label = firstPresent(snap?.label, snap?.id, 'Untitled snap') || 'Untitled snap';
  const iso = firstPresent(snap?.effective_datetime, dashboard?.timestamp, snap?.datetime, snap?.timestamp);
  const location = firstPresent(snap?.location, dashboard?.location);
  const timezone = firstPresent(snap?.timezone, dashboard?.timezone, snap?.timezone_label, dashboard?.timezone_label);
  let datePart = '';
  let timePart = '';
  if (iso) {
    try {
      const parsed = new Date(iso);
      datePart = new Intl.DateTimeFormat('en-GB', {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
      }).format(parsed);
      timePart = new Intl.DateTimeFormat('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(parsed);
    } catch (_) {}
  }
  return { label, iso, datePart, timePart, location, timezone };
}

function formatSnapLabel(snap) {
  const parts = getSnapMetaParts(snap);
  return [parts.label, parts.datePart, parts.timePart, parts.location].filter(Boolean).join(' | ');
}

function snapHasLongitude(snap) {
  const dashboard = snapDashboard(snap);
  const value = firstPresent(snap?.longitude, dashboard?.longitude, snap?.lng, dashboard?.lng);
  return value !== '' && Number.isFinite(Number(value));
}

function buildReadingText(data, compatibilityReport) {
  if (!data) return '';
  const lines = [];
  lines.push(`Chinese Astrology / BaZi Profile`);
  if (data.snap_label || data.source_snap_id) {
    lines.push(`Chart: ${data.snap_label || data.source_snap_id}`);
  }
  const dayMaster = data.day_master || {};
  if (dayMaster.stem || dayMaster.element) {
    lines.push(`Day Master: ${[dayMaster.stem, dayMaster.polarity, dayMaster.element].filter(Boolean).join(' / ')}`);
  }
  if (data.interpretation?.summary) lines.push(`Summary: ${data.interpretation.summary}`);
  const sections = Array.isArray(data.interpretation?.sections) ? data.interpretation.sections : [];
  sections.forEach((section) => {
    lines.push('');
    lines.push(section.title || 'Reading');
    (Array.isArray(section.items) ? section.items : []).forEach((item) => lines.push(`- ${item}`));
  });
  if (data.useful_elements?.status) {
    lines.push('');
    lines.push(`Useful Elements: ${data.useful_elements.status} / confidence ${data.useful_elements.confidence || 'low'}`);
  }
  if (compatibilityReport?.scoring) {
    lines.push('');
    lines.push(`Experimental Pair Evidence Index: ${compatibilityReport.scoring.score}/100 / uncalibrated model band ${compatibilityReport.scoring.grade_label || '-'} / confidence ${compatibilityReport.scoring.confidence || 'low'}`);
  }
  return lines.join('\n');
}

function buildOracleText(oracle) {
  if (!oracle) return '';
  const lines = ['I Ching Oracle'];
  if (oracle.question) lines.push(`Question: ${oracle.question}`);
  if (oracle.primary?.label) lines.push(`Primary: ${oracle.primary.label}`);
  if (oracle.relating?.label) lines.push(`Relating: ${oracle.relating.label}`);
  if (Array.isArray(oracle.changing_lines) && oracle.changing_lines.length) {
    lines.push(`Changing Lines: ${oracle.changing_lines.join(', ')}`);
  }
  if (oracle.reading?.summary) lines.push(`Summary: ${oracle.reading.summary}`);
  if (oracle.reading?.primary_counsel) lines.push(`Counsel: ${oracle.reading.primary_counsel}`);
  return lines.join('\n');
}

async function copyText(text) {
  if (!text) return false;
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }
  if (typeof document === 'undefined') return false;
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', 'readonly');
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  const ok = document.execCommand('copy');
  document.body.removeChild(textarea);
  return ok;
}

function downloadJson(filename, payload) {
  if (typeof document === 'undefined' || typeof URL === 'undefined') return false;
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  return true;
}

function saveReadingSnapshot(payload) {
  if (typeof window === 'undefined' || !window.localStorage || !payload?.profile) return false;
  try {
    const current = JSON.parse(window.localStorage.getItem(SAVED_READINGS_KEY) || '[]');
    const rows = Array.isArray(current) ? current : [];
    const next = [
      {
        id: `chinese-${Date.now()}`,
        saved_at: new Date().toISOString(),
        snap_label: payload.profile.snap_label || payload.profile.source_snap_id || 'Chinese Astrology profile',
        day_master: payload.profile.day_master || null,
        summary: payload.profile.interpretation?.summary || '',
        payload,
      },
      ...rows,
    ].slice(0, 20);
    window.localStorage.setItem(SAVED_READINGS_KEY, JSON.stringify(next));
    return true;
  } catch (_) {
    return false;
  }
}

function Micro({ children, className = '' }) {
  return (
    <span className={`text-[10px] font-semibold uppercase leading-none tracking-[0.24em] text-zinc-500 ${className}`} style={monoStyle}>
      {children}
    </span>
  );
}

function Pill({ children, active = false, disabled = false, onClick, ariaLabel }) {
  const className = `inline-flex items-center rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase leading-none tracking-[0.12em] transition ${
    active
      ? 'border-zinc-950 bg-zinc-950 text-white'
      : 'border-zinc-200 bg-white text-zinc-600'
  } ${disabled ? 'opacity-55' : ''} ${onClick && !disabled ? 'cursor-pointer hover:border-zinc-400 hover:text-zinc-950' : ''}`;
  if (onClick) {
    return (
      <button
        type="button"
        aria-label={ariaLabel}
        onClick={onClick}
        disabled={disabled}
        className={className}
        style={monoStyle}
      >
        {children}
      </button>
    );
  }
  return <span className={className} style={monoStyle}>{children}</span>;
}

function IconAction({ icon: Icon, label, onClick, disabled = false }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-600 transition hover:border-zinc-400 hover:text-zinc-950 disabled:cursor-not-allowed disabled:opacity-45"
    >
      <Icon aria-hidden="true" className="h-4 w-4" />
    </button>
  );
}

function SegmentGroup({ label, options, value, onChange }) {
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <Micro>{label}</Micro>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${
              value === option.value
                ? 'border-zinc-950 bg-zinc-950 text-white'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400'
            }`}
            style={monoStyle}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function CompactOptionToggle({ label, options, value, onChange }) {
  const [open, setOpen] = useState(false);
  const selected = options.find((option) => option.value === value) || options[0];
  const selectedLabel = selected?.label || 'Select';

  const handleSelect = (nextValue) => {
    onChange(nextValue);
    setOpen(false);
  };

  return (
    <div
      className="relative min-w-0"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false);
        }
      }}
    >
      <Micro>{label}</Micro>
      <button
        type="button"
        aria-label={`${label}: ${selectedLabel}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="mt-2 flex h-9 w-full min-w-0 items-center justify-between gap-2 rounded-full border border-zinc-950 bg-zinc-950 px-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-white shadow-sm transition hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-300"
        style={monoStyle}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="truncate">{selectedLabel}</span>
        <ChevronDown aria-hidden="true" className={`h-3.5 w-3.5 shrink-0 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open ? (
        <div
          role="listbox"
          aria-label={`${label} options`}
          className="absolute left-0 z-40 mt-2 w-full min-w-[150px] overflow-hidden rounded-sm border border-zinc-200 bg-white shadow-lg"
        >
          {options.map((option) => {
            const active = option.value === value;
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={active}
                className={`block w-full px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.12em] transition ${
                  active
                    ? 'bg-zinc-950 text-white'
                    : 'bg-white text-zinc-700 hover:bg-zinc-100 hover:text-zinc-950'
                }`}
                style={monoStyle}
                onClick={() => handleSelect(option.value)}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function TabPillButton({ active = false, children, onClick, className = '' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`shrink-0 rounded-full border px-3.5 py-2 text-[11px] font-semibold uppercase leading-none tracking-[0.16em] transition ${
        active
          ? 'border-zinc-950 bg-zinc-950 text-white'
          : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400'
      } ${className}`}
      style={monoStyle}
    >
      {children}
    </button>
  );
}

function TabOptionMenu({ label, options, activeTab, onSelect }) {
  const [open, setOpen] = useState(false);
  const selected = options.find(([id]) => id === activeTab);

  return (
    <div
      className="relative shrink-0"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        aria-label={selected ? `${label}: ${selected[1]}` : label}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className={`flex items-center gap-2 rounded-full border px-3.5 py-2 text-[11px] font-semibold uppercase leading-none tracking-[0.16em] transition ${
          selected
            ? 'border-zinc-950 bg-zinc-950 text-white'
            : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400'
        }`}
        style={monoStyle}
      >
        <span>{label}</span>
        <ChevronDown aria-hidden="true" className={`h-3.5 w-3.5 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open ? (
        <div
          role="listbox"
          aria-label={`${label} options`}
          className="absolute bottom-full left-0 z-40 mb-2 min-w-[190px] overflow-hidden rounded-sm border border-zinc-200 bg-white shadow-lg"
        >
          {options.map(([id, optionLabel]) => {
            const active = activeTab === id;
            return (
              <button
                key={id}
                type="button"
                role="option"
                aria-selected={active}
                className={`block w-full px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.12em] transition ${
                  active
                    ? 'bg-zinc-950 text-white'
                    : 'bg-white text-zinc-700 hover:bg-zinc-100 hover:text-zinc-950'
                }`}
                style={monoStyle}
                onClick={() => {
                  onSelect(id);
                  setOpen(false);
                }}
              >
                {optionLabel}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function DecisionEvidencePanel({ evidence }) {
  const strength = evidence?.strength || {};
  const climate = evidence?.climate || {};
  const presence = evidence?.presence || {};
  const damage = evidence?.damage || {};
  const structureSelection = evidence?.structure_selection || {};
  const standardStructure = structureSelection?.primary_structure || {};
  const special = evidence?.special_structure || {};
  const timing = evidence?.timing || {};
  const primaryStructure = special?.primary_structure || {};
  const timingItems = Array.isArray(timing?.items) ? timing.items : [];
  const hasEvidence = [
    strength?.label,
    climate?.status,
    presence?.availability,
    damage?.status,
    standardStructure?.key,
    special?.status,
    timing?.status,
  ].some(Boolean);
  if (!hasEvidence) return null;
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-4">
      <Micro>Decision Evidence</Micro>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <TimingMetric label="Strength" value={ruleTokenLabel(strength?.label || '-')} />
        <TimingMetric label="Support / Pressure" value={`${strength?.support_score ?? '-'} / ${strength?.pressure_score ?? '-'}`} />
        <TimingMetric label="Model Confidence" value={ruleTokenLabel(strength?.model_confidence || '-')} />
        <TimingMetric label="Climate" value={ruleTokenLabel(climate?.override_status || climate?.status || '-')} />
        <TimingMetric label="Presence" value={ruleTokenLabel(presence?.availability || '-')} />
        <TimingMetric label="Damage" value={ruleTokenLabel(damage?.status || '-')} />
        <TimingMetric label="Month Structure" value={ruleTokenLabel(standardStructure?.key || '-')} />
        <TimingMetric label="Structure" value={ruleTokenLabel(special?.structure_status || special?.status || '-')} />
        <TimingMetric label="Timing" value={ruleTokenLabel(timing?.status || '-')} />
      </div>
      {standardStructure?.label || primaryStructure?.type || damage?.reason || timingItems.length ? (
        <div className="mt-4 space-y-2 text-[12px] leading-relaxed text-zinc-600">
          {standardStructure?.label ? (
            <div className="border-l border-indigo-300 pl-3">
              <span className="font-medium text-zinc-900">Month command: </span>
              {standardStructure.label}
              {standardStructure.status ? ` / ${ruleTokenLabel(standardStructure.status)}` : ''}
              {standardStructure.use_mode ? ` / ${ruleTokenLabel(standardStructure.use_mode)}` : ''}
            </div>
          ) : null}
          {primaryStructure?.type ? (
            <div className="border-l border-amber-300 pl-3">
              <span className="font-medium text-zinc-900">Primary structure: </span>
              {ruleTokenLabel(primaryStructure.type)}{primaryStructure.element ? ` / ${primaryStructure.element}` : ''}
            </div>
          ) : null}
          {damage?.reason ? (
            <div className="border-l border-rose-300 pl-3">
              <span className="font-medium text-zinc-900">Damage check: </span>{damage.reason}
            </div>
          ) : null}
          {timingItems.slice(0, 2).map((item) => (
            <div key={`${item.element}-${item.status}`} className="border-l border-sky-300 pl-3">
              <span className="font-medium text-zinc-900">Timing: </span>{item.summary || `${item.element} ${ruleTokenLabel(item.status)}`}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ProvisionalBadge({ children = 'Reading Layer' }) {
  return (
    <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[10px] font-semibold uppercase leading-none tracking-[0.12em] text-amber-800" style={monoStyle}>
      {children}
    </span>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <Micro className="mb-1 block">{label}</Micro>
      {children}
    </label>
  );
}

function EmptyPanel({ title, body }) {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16 text-center">
      <div className="text-[1.8rem] font-semibold tracking-[-0.03em] text-zinc-900">{title}</div>
      {body ? <p className="mx-auto mt-3 max-w-xl text-[1rem] leading-relaxed text-zinc-600">{body}</p> : null}
    </div>
  );
}

function MemoSection({ number, title, subtitle, children }) {
  return (
    <section className="mt-8 first:mt-0">
      <div className="flex flex-col gap-2 border-b border-zinc-200 pb-3 md:flex-row md:items-baseline md:gap-5">
        {number ? <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-teal-700" style={monoStyle}>{number}</div> : null}
        <div className="flex-1">
          <h4 className="text-[1.1rem] font-semibold tracking-[-0.02em] text-zinc-900">{title}</h4>
          {subtitle ? <p className="mt-1 max-w-3xl text-sm leading-relaxed text-zinc-500">{subtitle}</p> : null}
        </div>
      </div>
      <div className="pt-5">{children}</div>
    </section>
  );
}

function StatePanel({ title, body, tone = 'zinc' }) {
  const titleClass = tone === 'danger' ? 'text-rose-700' : tone === 'warn' ? 'text-amber-700' : 'text-zinc-900';
  return (
    <div className="mx-auto max-w-2xl px-6 py-20 text-center">
      <div className={`text-[1.8rem] font-semibold tracking-[-0.03em] ${titleClass}`}>{title}</div>
      {body ? <p className="mx-auto mt-3 max-w-xl text-[1rem] leading-relaxed text-zinc-600">{body}</p> : null}
    </div>
  );
}

function InputPromptStrip({ prompts }) {
  const items = Array.isArray(prompts) ? prompts.filter((item) => item?.message) : [];
  if (!items.length) return null;
  return (
    <div className="mt-4 rounded-sm border border-amber-200 bg-amber-50 px-4 py-3">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <Micro className="text-amber-800">Input checks</Micro>
          <div className="mt-2 grid gap-1.5 text-[12px] leading-relaxed text-amber-900 md:grid-cols-2">
            {items.slice(0, 6).map((item, index) => (
              <div key={`${item.field || item.type || 'prompt'}-${index}`}>
                {item.message}
              </div>
            ))}
          </div>
        </div>
        {items.length > 6 ? (
          <span className="shrink-0 rounded-full border border-amber-300 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-800" style={monoStyle}>
            +{items.length - 6} more
          </span>
        ) : null}
      </div>
    </div>
  );
}

function ReadingHistoryPanel({ rows, onLoad, onClear }) {
  const items = Array.isArray(rows) ? rows : [];
  return (
    <div className="border-b border-zinc-200/80 bg-white px-6 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Micro>Saved readings</Micro>
          <div className="mt-1 text-sm text-zinc-600">{items.length ? `${items.length} local reading snapshot${items.length === 1 ? '' : 's'}` : 'No local reading snapshots yet'}</div>
        </div>
        <button
          type="button"
          onClick={onClear}
          disabled={!items.length}
          className={secondaryActionClass}
          style={monoStyle}
        >
          <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
          Clear
        </button>
      </div>
      {items.length ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {items.slice(0, 8).map((row) => {
            const dayMaster = row.day_master || row.payload?.profile?.day_master || {};
            const savedAt = row.saved_at ? new Date(row.saved_at) : null;
            const savedLabel = savedAt && !Number.isNaN(savedAt.getTime())
              ? savedAt.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
              : 'Saved reading';
            const pairScore = row.payload?.compatibility?.scoring?.score;
            return (
              <div key={row.id} className="rounded-sm border border-zinc-200 bg-white px-4 py-3">
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-zinc-900">{row.snap_label || 'Chinese Astrology profile'}</div>
                    <div className="mt-1 text-[12px] text-zinc-500">
                      {savedLabel} / {dayMaster.stem || '-'} {dayMaster.element || ''}
                      {Number.isFinite(Number(pairScore)) ? ` / experimental pair index ${pairScore}` : ''}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => onLoad(row)}
                    className="shrink-0 rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-600 hover:border-zinc-400"
                    style={monoStyle}
                  >
                    Load
                  </button>
                </div>
                {row.summary ? <div className="mt-2 line-clamp-2 text-[12px] leading-relaxed text-zinc-500">{row.summary}</div> : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function StemValue({ stem, element, compact = false }) {
  if (!stem) return <span className="text-zinc-400">-</span>;
  return (
    <span className="inline-flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
      <span className="font-semibold text-zinc-950">{stem}</span>
      {STEM_GLYPHS[stem] ? (
        <span className={`${compact ? 'text-sm' : 'text-base'} font-semibold text-zinc-800`} style={glyphStyle} aria-label={`${stem} Chinese character`}>
          {STEM_GLYPHS[stem]}
        </span>
      ) : null}
      {element ? <span className="text-[11px] uppercase tracking-[0.08em] text-zinc-500">{element}</span> : null}
    </span>
  );
}

function BranchValue({ branch, animal, element, compact = false }) {
  if (!branch) return <span className="text-zinc-400">-</span>;
  return (
    <span className="inline-flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
      <span className="font-semibold text-zinc-950">{branch}</span>
      {BRANCH_GLYPHS[branch] ? (
        <span className={`${compact ? 'text-sm' : 'text-base'} font-semibold text-zinc-800`} style={glyphStyle} aria-label={`${branch} Chinese character`}>
          {BRANCH_GLYPHS[branch]}
        </span>
      ) : null}
      {animal ? <span className="text-[11px] uppercase tracking-[0.08em] text-zinc-500">{animal}</span> : null}
      {element ? <span className="text-[11px] uppercase tracking-[0.08em] text-zinc-400">/ {element}</span> : null}
    </span>
  );
}

function HiddenStemChips({ stems }) {
  const items = Array.isArray(stems) ? stems.filter((item) => item?.key) : [];
  if (!items.length) return <span className="text-zinc-400">-</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => {
        const role = item.god || item.factor;
        return (
          <span
            key={`${item.key}-${item.rank || role || 'hidden'}`}
            className="inline-flex min-w-0 max-w-full flex-col rounded-sm border border-zinc-200 bg-white px-2 py-1 leading-tight"
          >
            <span className="flex items-baseline gap-1 font-semibold text-zinc-900">
              <span>{item.key}</span>
              {STEM_GLYPHS[item.key] ? <span className="text-[12px]" style={glyphStyle}>{STEM_GLYPHS[item.key]}</span> : null}
            </span>
            <span className="truncate text-[10px] uppercase tracking-[0.06em] text-zinc-500">
              {[item.element, role].filter(Boolean).join(' / ')}
            </span>
          </span>
        );
      })}
    </div>
  );
}

function PillarCards({ pillars }) {
  return (
    <div className="grid gap-3 sm:hidden">
      {PILLAR_ORDER.map((key) => {
        const pillar = pillars?.[key];
        return (
          <article key={key} className={`rounded-sm border p-4 ${key === 'day' ? 'border-teal-200 bg-teal-50/60' : 'border-zinc-200 bg-white'}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <Micro className={key === 'day' ? 'text-teal-700' : ''}>{PILLAR_LABELS[key]}</Micro>
                <div className="mt-2 space-y-1 text-sm">
                  <div><StemValue stem={pillar?.stem} element={pillar?.stem_element} /></div>
                  <div><BranchValue branch={pillar?.branch} animal={pillar?.animal} element={pillar?.branch_element} /></div>
                </div>
              </div>
              {pillar?.ten_god ? <Pill active={key === 'day'}>{pillar.ten_god}</Pill> : null}
            </div>
            <div className="mt-4">
              <Micro>Hidden Stems</Micro>
              <div className="mt-2"><HiddenStemChips stems={pillar?.hidden_stems} /></div>
            </div>
            {pillar ? (
              <div className="mt-3 text-[11px] uppercase tracking-[0.08em] text-zinc-500" style={monoStyle}>
                {pillar.stem_polarity || '-'} stem / {pillar.branch_polarity || '-'} branch
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

function ChartGrid({ pillars }) {
  return (
    <>
      <PillarCards pillars={pillars} />
      <div className="hidden h-full overflow-x-auto rounded-sm border border-zinc-200 bg-white sm:block">
        <table className="h-full min-w-full table-fixed border-collapse text-sm">
          <thead>
            <tr className="border-b border-zinc-200 bg-zinc-50">
              <th className="w-28 px-3 py-3 text-left"><Micro>Layer</Micro></th>
              {PILLAR_ORDER.map((key) => (
                <th key={key} className="px-3 py-3 text-left">
                  <span className={key === 'day' ? 'font-semibold text-teal-700' : 'font-semibold text-zinc-950'}>
                    {PILLAR_LABELS[key]}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            <ChartRow label="Stem" pillars={pillars} render={(pillar) => <StemValue stem={pillar?.stem} element={pillar?.stem_element} />} />
            <ChartRow label="Branch" pillars={pillars} render={(pillar) => <BranchValue branch={pillar?.branch} animal={pillar?.animal} element={pillar?.branch_element} />} />
            <ChartRow label="Hidden" pillars={pillars} render={(pillar) => <HiddenStemChips stems={pillar?.hidden_stems} />} />
            <ChartRow label="Ten God" pillars={pillars} render={(pillar) => pillar?.ten_god || '-'} />
            <ChartRow label="Polarity" pillars={pillars} render={(pillar) => pillar ? `${pillar.stem_polarity} / ${pillar.branch_polarity}` : '-'} />
          </tbody>
        </table>
      </div>
    </>
  );
}

function ChartRow({ label, pillars, render }) {
  return (
    <tr>
      <td className="bg-zinc-50 px-3 py-3 align-top"><Micro>{label}</Micro></td>
      {PILLAR_ORDER.map((key) => (
        <td key={key} className={`px-3 py-3 align-top text-zinc-800 ${key === 'day' ? 'bg-teal-50/70' : ''}`}>
          {render(pillars?.[key])}
        </td>
      ))}
    </tr>
  );
}

function DayMasterCard({ dayMaster, analysis }) {
  if (!dayMaster) return null;
  const model = analysis?.strength_model || {};
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex items-start justify-between gap-5">
        <div>
          <Micro>Day Master</Micro>
          <div className="mt-3 flex items-baseline gap-3 text-[4.6rem] font-medium leading-none tracking-[-0.08em] text-zinc-950" style={serifStyle}>
            <span>{dayMaster.stem}</span>
            {STEM_GLYPHS[dayMaster.stem] ? <span className="text-[3.5rem] tracking-normal" style={glyphStyle}>{STEM_GLYPHS[dayMaster.stem]}</span> : null}
          </div>
          <div className="mt-3 text-sm leading-relaxed text-zinc-600">{dayMaster.polarity} {dayMaster.element}</div>
        </div>
        <Pill active>{analysis?.strength || 'pending'}</Pill>
      </div>
      {Array.isArray(analysis?.strength_evidence) && analysis.strength_evidence.length ? (
        <ul className="mt-5 space-y-2 border-t border-zinc-100 pt-4 text-sm leading-relaxed text-zinc-700">
          {analysis.strength_evidence.slice(0, 4).map((item) => (
            <li key={item} className="border-l border-emerald-300 pl-3">{item}</li>
          ))}
        </ul>
      ) : null}
      {model?.method ? <StrengthModelEvidence model={model} /> : null}
    </div>
  );
}

function StrengthModelEvidence({ model }) {
  const season = model?.season || {};
  const root = model?.root || {};
  const formation = model?.formation || {};
  const rootGrade = root.root_grade ? ruleTokenLabel(root.root_grade) : (root.score ?? '-');
  const gradeEvidence = model?.root_grade_evidence || {};
  const gainRows = [
    ['De Ling', gradeEvidence?.de_ling],
    ['De Di', gradeEvidence?.de_di],
    ['De Zhu', gradeEvidence?.de_zhu],
  ].filter(([, row]) => row && (row.status || row.evidence));
  return (
    <div className="mt-5 border-t border-zinc-100 pt-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <TimingMetric label="Season" value={`${season.season || '-'} / ${season.state || '-'}`} />
        <TimingMetric label="Root Grade" value={rootGrade} />
        <TimingMetric label="Formation" value={formation.score ?? '-'} />
      </div>
      {gainRows.length ? (
        <div className="mt-4 grid gap-2 md:grid-cols-3">
          {gainRows.map(([label, row]) => (
            <div key={label} className="border border-zinc-100 bg-zinc-50 px-3 py-2">
              <Micro>{label}</Micro>
              <div className="mt-1 text-sm font-semibold text-zinc-900">{ruleTokenLabel(row.status)}</div>
              {row.evidence ? <div className="mt-1 text-[12px] leading-relaxed text-zinc-500">{row.evidence}</div> : null}
            </div>
          ))}
        </div>
      ) : null}
      {gradeEvidence?.resource_substitute_limit?.active ? (
        <div className="mt-3 border-l border-amber-300 pl-3 text-[12px] leading-relaxed text-zinc-600">
          {gradeEvidence.resource_substitute_limit.note}
        </div>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2 text-[10.5px] uppercase leading-none tracking-[0.14em] text-zinc-400" style={monoStyle}>
        <span>strength model</span>
        <span>/</span>
        <span>season / root / formation</span>
        <span>/</span>
        <span>{model.confidence || 'low'} confidence</span>
        {model.weighted_score !== undefined ? (
          <>
            <span>/</span>
            <span>score {model.weighted_score}</span>
          </>
        ) : null}
      </div>
    </div>
  );
}

function ElementBalance({ balance }) {
  const total = balance?.total || {};
  const max = Math.max(1, ...ELEMENTS.map((element) => Number(total[element] || 0)));
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <Micro>Elements</Micro>
      <div className="mt-4 space-y-3">
        {ELEMENTS.map((element) => {
          const value = Number(total[element] || 0);
          return (
            <div key={element} className="grid grid-cols-[74px_minmax(0,1fr)_32px] items-center gap-3">
              <span className="text-sm text-zinc-700">{element}</span>
              <div className="h-2 rounded-full bg-zinc-100">
                <div
                  className="h-2 rounded-full bg-teal-600"
                  role="meter"
                  aria-label={`${element} unweighted presence`}
                  aria-valuemin={0}
                  aria-valuemax={max}
                  aria-valuenow={value}
                  style={{ width: `${(value / max) * 100}%` }}
                />
              </div>
              <span className="text-right text-xs font-semibold text-zinc-500" style={monoStyle}>{value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function factorFavorabilityClass(value) {
  if (['final_useful', 'favorable_candidate', 'timing_activated', 'favorable'].includes(value)) {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  }
  if (['pressured_useful', 'needed_absent', 'timing_challenged', 'caution'].includes(value)) {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }
  if (['neutral', 'balanced_watch', 'role_only', 'quiet'].includes(value)) return 'border-zinc-200 bg-zinc-50 text-zinc-600';
  return 'border-zinc-200 bg-white text-zinc-500';
}

function FiveFactorProfile({ profile }) {
  const factors = Array.isArray(profile?.factors) ? profile.factors : [];
  if (!factors.length) return null;
  const requirements = Array.isArray(profile?.context_requirements) ? profile.context_requirements : [];
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <Micro>Role Summary</Micro>
          {profile?.summary ? <p className="mt-2 max-w-3xl text-sm leading-relaxed text-zinc-600">{profile.summary}</p> : null}
        </div>
        <Pill active>Role Map</Pill>
      </div>
      <div className="mt-5 grid gap-3 lg:grid-cols-5">
        {factors.map((factor) => <FactorProfileCard key={factor.factor} factor={factor} />)}
      </div>
      {requirements.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {requirements.slice(0, 6).map((item) => (
            <span key={item} className="border border-zinc-200 bg-white px-2.5 py-1 text-[11px] text-zinc-600">
              {item}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function FactorProfileCard({ factor }) {
  const keywords = Array.isArray(factor?.keywords) ? factor.keywords : [];
  const gods = Array.isArray(factor?.gods) ? factor.gods : [];
  const decisionBasis = Array.isArray(factor?.decision_basis) ? factor.decision_basis : [];
  const fallback = TEN_GOD_FACTOR_FALLBACKS[factor?.factor] || {};
  const chinese = factor?.chinese || fallback.chinese || '';
  const pinyin = factor?.pinyin || fallback.pinyin || '';
  const relationChinese = factor?.relation_chinese || fallback.relation_chinese || '';
  const relationLabel = factor?.relation_label || fallback.relation_label || '';
  const domainSummary = factor?.domain_summary || fallback.domain_summary || factor?.source_note || '';
  const statusValue = factor?.functional_status || factor?.favorability || 'open';
  const statusLabel = factor?.status_label || (factor?.favorability === 'unresolved' ? 'Topic' : factor?.favorability) || 'Open';
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-zinc-950">{factor?.factor || '-'}</div>
          <div className="mt-1 text-xs text-zinc-500">
            {[chinese, pinyin].filter(Boolean).join(' / ') || factor?.element || '-'}
          </div>
        </div>
        <span className={`rounded-full border px-2 py-1 text-[10px] uppercase leading-none tracking-[0.1em] ${factorFavorabilityClass(statusValue)}`} style={monoStyle}>
          {statusLabel}
        </span>
      </div>
      <div className="mt-3 text-[12px] leading-relaxed text-zinc-600">
        {[relationChinese, relationLabel].filter(Boolean).join(' / ')}
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 border-y border-zinc-100 py-3">
        <TimingMetric label="Visible" value={factor?.visible_count ?? 0} />
        <TimingMetric label="Hidden" value={factor?.hidden_count ?? 0} />
        <TimingMetric label="Total" value={factor?.total_count ?? 0} />
      </div>
      {domainSummary ? <p className="mt-3 text-xs leading-relaxed text-zinc-600">{domainSummary}</p> : null}
      {keywords.length ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {keywords.slice(0, 4).map((keyword) => (
            <span key={keyword} className="rounded-full bg-zinc-50 px-2 py-1 text-[11px] leading-none text-zinc-600">{keyword}</span>
          ))}
        </div>
      ) : null}
      {factor?.summary ? <p className="mt-3 text-xs leading-relaxed text-zinc-600">{factor.summary}</p> : null}
      {decisionBasis.length ? (
        <div className="mt-3 space-y-1 border-t border-zinc-100 pt-3">
          {decisionBasis.slice(0, 2).map((item) => (
            <div key={item} className="text-[11px] leading-relaxed text-zinc-500">{item}</div>
          ))}
        </div>
      ) : null}
      {gods.length ? (
        <div className="mt-3 text-[11px] leading-relaxed text-zinc-500" style={monoStyle}>
          {gods.join(' / ')}
        </div>
      ) : null}
    </div>
  );
}

function TenGodsPanel({ tenGods }) {
  const visible = Array.isArray(tenGods?.visible) ? tenGods.visible : [];
  const hidden = Array.isArray(tenGods?.hidden) ? tenGods.hidden : [];
  const profile = tenGods?.factor_profile || null;
  return (
    <div className="space-y-5">
      <div className="border-l border-teal-500 pl-4 text-sm leading-relaxed text-zinc-600">
        Ten Gods maps visible and hidden stems to the Day Master, then marks each Five Factor through strength, useful-element direction, contact pressure, and active timing.
      </div>
      <FiveFactorProfile profile={profile} />
      <div className="rounded-sm border border-zinc-200 bg-white p-5">
        <Micro>Visible & Hidden Roles</Micro>
        <div className="mt-4 grid gap-5 lg:grid-cols-2">
          <TenGodRoleRows title="Visible Stems" rows={visible} layer="Visible" empty="No visible Ten God roles beyond the Day Master." />
          <TenGodRoleRows title="Hidden Stems" rows={hidden.slice(0, 12)} layer="Hidden" empty="No hidden-stem Ten God roles returned." />
        </div>
      </div>
    </div>
  );
}

function TenGodRoleRows({ title, rows, layer, empty }) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3 border-b border-zinc-100 pb-3">
        <Micro>{title}</Micro>
        <span className="text-sm font-semibold text-zinc-900">{rows.length}</span>
      </div>
      {rows.length ? (
        <div className="mt-3 space-y-2">
          {rows.map((row, idx) => (
            <TenGodRoleRow key={`${layer}-${row.pillar}-${row.stem}-${idx}`} row={row} layer={layer} />
          ))}
        </div>
      ) : (
        <div className="mt-3 text-sm text-zinc-500">{empty}</div>
      )}
    </div>
  );
}

function TenGodRoleRow({ row, layer }) {
  const fallback = TEN_GOD_FACTOR_FALLBACKS[row?.factor] || {};
  const godChinese = row?.god_chinese ? ` / ${row.god_chinese}` : '';
  const factorChinese = row?.factor_chinese || fallback.chinese || '';
  const relation = row?.relation_chinese || fallback.relation_chinese || '';
  return (
    <div className="rounded-sm border border-zinc-200 bg-white px-3 py-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-zinc-900">{row?.stem || '-'}</span>
        <Micro>{layer} / {row?.pillar || '-'}</Micro>
      </div>
      <div className="mt-1 text-xs text-zinc-600">
        {row?.god || '-'}{godChinese} / {row?.factor || '-'}{factorChinese ? ` ${factorChinese}` : ''}
      </div>
      <div className="mt-1 text-[11px] leading-relaxed text-zinc-500">
        {[relation, row?.relation_label || fallback.relation_label, row?.polarity_relation ? `${row.polarity_relation} polarity` : '', row?.rank ? `hidden rank ${row.rank}` : ''].filter(Boolean).join(' / ')}
      </div>
    </div>
  );
}

function PairCompatibilityPanel({ report, loading, error }) {
  const summary = report?.summary || {};
  const events = Array.isArray(report?.events) ? report.events : [];
  const exchange = report?.day_master_exchange || {};
  const timing = report?.timing_alignment || {};
  const interpretation = report?.interpretation || {};
  const judgement = report?.judgement || {};
  const judgementOrder = Array.isArray(judgement?.evidence_order) ? judgement.evidence_order : [];
  const scoring = report?.scoring || {};
  const subjects = report?.subjects || {};
  const primary = subjects.primary || {};
  const relationship = subjects.relationship || {};
  const topEvents = events.slice(0, 6);

  return (
    <MemoSection
      number="VIII-A"
      title="Pair Compatibility"
      subtitle="Two saved snaps are compared through an experimental cross-chart evidence model. It is not a classical compatibility verdict or an outcome prediction."
    >
      {loading ? <StatePanel title="Comparing saved snaps" body="Cross-chart relationship contacts are being calculated from the two selected BaZi charts." /> : null}
      {!loading && error ? <div className="rounded-sm border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
      {!loading && !error && !report ? <div className="text-sm text-zinc-500">Select a second saved snap to compare the pair.</div> : null}
      {!loading && !error && report ? (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            <ProvisionalBadge>Experimental Evidence Index</ProvisionalBadge>
          </div>
          <div className="grid gap-5 border-b border-zinc-200 pb-5 md:grid-cols-6">
            <RelationshipStat label="Index / 100" value={Number.isFinite(Number(scoring.score)) ? scoring.score : '-'} />
            <RelationshipStat label="Confidence" value={formatRelationshipStatus(scoring.confidence || 'low')} />
            <RelationshipStat label="Context" value={scoring.relationship_context_label || 'General'} />
            <RelationshipStat label="Supportive" value={summary.supportive || 0} />
            <RelationshipStat label="Challenging" value={summary.challenging || 0} />
            <RelationshipStat label="Partner Palace" value={(summary.day_partner_palace || 0) + (summary.partner_palace_contact || 0)} />
          </div>

          <div className="rounded-sm border border-zinc-200 bg-white p-4">
            <Micro>Pair Reading Focus</Micro>
            <div className="mt-2 text-[1.05rem] font-semibold tracking-[-0.02em] text-zinc-900">
              {interpretation.headline || 'Pair contacts are ready for review.'}
            </div>
            {Array.isArray(interpretation.highlights) && interpretation.highlights.length ? (
              <div className="mt-3 grid gap-2 text-sm leading-relaxed text-zinc-600 md:grid-cols-2">
                {interpretation.highlights.map((item) => <div key={item}>{item}</div>)}
              </div>
            ) : null}
            {scoring.grade_label ? (
              <div className="mt-3 text-[12px] text-zinc-500">
                Uncalibrated index {scoring.score ?? '-'} / 100 / model band {scoring.grade_label} / {scoring.relationship_context_label || 'General'} context
                {` / confidence ${formatRelationshipStatus(scoring.confidence || 'low')}`}
              </div>
            ) : null}
          </div>

          {judgementOrder.length ? (
            <div className="rounded-sm border border-zinc-200 bg-white p-4">
              <Micro>BaZi Relationship Judgement</Micro>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {judgementOrder.map((item) => (
                  <div key={item.key} className="rounded-sm border border-zinc-100 bg-zinc-50 px-3 py-2">
                    <div className="text-[11px] uppercase tracking-[0.12em] text-zinc-500" style={monoStyle}>{item.label || ruleTokenLabel(item.key)}</div>
                    <div className="mt-1 text-sm font-semibold text-zinc-900">{ruleTokenLabel(item.status || '-')}</div>
                  </div>
                ))}
              </div>
              {judgement?.timing_activation?.summary ? (
                <div className="mt-3 text-[12px] leading-relaxed text-zinc-500">{judgement.timing_activation.summary}</div>
              ) : null}
              {Array.isArray(judgement?.spouse_star?.directions) && judgement.spouse_star.directions.length ? (
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {judgement.spouse_star.directions.map((row) => (
                    <div key={row.direction} className="rounded-sm border border-zinc-100 bg-white px-3 py-2 text-[12px] leading-relaxed text-zinc-600">
                      <div className="font-semibold text-zinc-900">{ruleTokenLabel(row.direction)}</div>
                      <div>{ruleTokenLabel(row.sex_based_role || 'unknown')} / {row.factor || '-'}</div>
                      <div className="text-zinc-500">
                        Natal {ruleTokenLabel(row.natal_condition?.status || 'unknown')} / cross-chart {ruleTokenLabel(row.cross_chart_supply?.status || 'quiet')}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          <ScoreBreakdown scoring={scoring} />
          <div className="grid gap-4 lg:grid-cols-2">
            <TimingAlignmentCard title="Primary Timing" profile={timing.primary} />
            <TimingAlignmentCard title="Relationship Timing" profile={timing.relationship} />
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="rounded-sm border border-zinc-200 bg-white p-4">
              <Micro>Day Master Exchange</Micro>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div className="rounded-sm border border-zinc-100 bg-zinc-50/70 px-3 py-3">
                  <div className="text-sm font-semibold text-zinc-900">{primary.label || 'Primary'}</div>
                  <div className="mt-1 text-xs text-zinc-500">
                    {primary.day_master?.stem || '-'} / {primary.day_master?.element || '-'} / {primary.day_master?.polarity || '-'}
                  </div>
                  <div className="mt-3 text-[12px] text-zinc-600">
                    Sees relationship as {exchange.primary_to_relationship?.factor || '-'} / {exchange.primary_to_relationship?.god || '-'}
                  </div>
                </div>
                <div className="rounded-sm border border-zinc-100 bg-zinc-50/70 px-3 py-3">
                  <div className="text-sm font-semibold text-zinc-900">{relationship.label || 'Relationship'}</div>
                  <div className="mt-1 text-xs text-zinc-500">
                    {relationship.day_master?.stem || '-'} / {relationship.day_master?.element || '-'} / {relationship.day_master?.polarity || '-'}
                  </div>
                  <div className="mt-3 text-[12px] text-zinc-600">
                    Sees primary as {exchange.relationship_to_primary?.factor || '-'} / {exchange.relationship_to_primary?.god || '-'}
                  </div>
                </div>
              </div>
              {exchange.summary ? <div className="mt-3 text-[12px] leading-relaxed text-zinc-500">{exchange.summary}</div> : null}
            </div>

            <div className="rounded-sm border border-zinc-200 bg-white p-4">
              <Micro>Pair Notes</Micro>
              <div className="mt-3 space-y-2 text-sm leading-relaxed text-zinc-600">
                {(Array.isArray(report.notes) ? report.notes : []).map((note) => <div key={note}>{note}</div>)}
              </div>
            </div>
          </div>

          {topEvents.length ? (
            <div className="grid gap-3 lg:grid-cols-2">
              {topEvents.map((event) => <RelationshipCard key={event.id || `${event.type}-${event.label}`} event={event} />)}
            </div>
          ) : (
            <EmptyPanel title="No cross-chart relationship contacts detected." body="The pair report did not find configured stem or branch contacts between the two selected charts." />
          )}

        </div>
      ) : null}
    </MemoSection>
  );
}

function relationshipEventToneKey(event) {
  const type = String(event?.type || '');
  if (type.includes('combination') || type.includes('cross')) return 'supportive';
  if (type.includes('clash') || type.includes('harm') || type.includes('punishment') || type.includes('destruction')) return 'challenging';
  return 'mixed';
}

function relationshipEventTouchesDay(event) {
  const palaces = Array.isArray(event?.affected_palaces) ? event.affected_palaces : [];
  const domains = Array.isArray(event?.affected_domains) ? event.affected_domains : [];
  return [...palaces, ...domains].some((item) => {
    const text = String(item || '').toLowerCase();
    return text === 'day' || text.includes('partner palace') || text.includes('spouse palace') || text.includes('self / partner');
  });
}

function relationshipSummaryCounts(events, summary = {}) {
  const derived = events.reduce((acc, event) => {
    const tone = relationshipEventToneKey(event);
    acc[tone] = (acc[tone] || 0) + 1;
    if (event?.scope && event.scope !== 'natal') acc.timing += 1;
    if (relationshipEventTouchesDay(event)) acc.dayPartner += 1;
    return acc;
  }, { supportive: 0, challenging: 0, mixed: 0, timing: 0, dayPartner: 0 });
  const timingSummary = ['luck', 'annual', 'flowing_month', 'flowing_day', 'flowing_hour']
    .reduce((total, key) => total + Number(summary?.[key] || 0), 0);
  return {
    total: Number(summary?.total || 0) || events.length,
    supportive: Number(summary?.supportive || 0) || derived.supportive,
    challenging: Number(summary?.challenging || 0) || derived.challenging,
    mixed: Number(summary?.mixed || 0) || derived.mixed,
    timing: timingSummary || derived.timing,
    dayPartner: Number(summary?.day_partner_palace || summary?.partner_palace_contact || 0) || derived.dayPartner,
  };
}

function relationshipMainTone(counts) {
  if (!counts.total) return 'Quiet';
  if (counts.supportive && counts.challenging) return 'Mixed';
  if (counts.challenging) return 'Challenging';
  if (counts.supportive) return 'Supportive';
  return 'Mixed';
}

function RelationshipOverviewCards({ events, summary }) {
  const counts = relationshipSummaryCounts(events, summary);
  return (
    <div className="grid gap-5 border-b border-zinc-200 pb-5 sm:grid-cols-2 lg:grid-cols-4">
      <RelationshipStat label="Total Contacts" value={counts.total} />
      <RelationshipStat label="Main Tone" value={relationshipMainTone(counts)} />
      <RelationshipStat label="Day / Partner Palace" value={counts.dayPartner} />
      <RelationshipStat label="Timing Contacts" value={counts.timing} />
    </div>
  );
}

function RelationshipScopeStrip({ groups }) {
  return (
    <div className="grid gap-2 border-b border-zinc-100 pb-4 sm:grid-cols-2 lg:grid-cols-6">
      {groups.map((group) => (
        <div key={group.key} className="flex items-center justify-between gap-3 border border-zinc-200 bg-white px-3 py-2">
          <Micro>{group.shortLabel}</Micro>
          <span className="text-sm font-semibold text-zinc-900">{group.events.length}</span>
        </div>
      ))}
    </div>
  );
}

function QuietRelationshipLayers({ groups }) {
  if (!groups.length) return null;
  return (
    <div className="mt-6 border-t border-zinc-100 pt-4">
      <Micro>Quiet Layers</Micro>
      <div className="mt-3 flex flex-wrap gap-2">
        {groups.map((group) => (
          <span key={group.key} className="border border-zinc-200 bg-white px-2.5 py-1 text-[12px] text-zinc-500">
            {group.title}
          </span>
        ))}
      </div>
    </div>
  );
}

function RelationshipCodesPanel({ relationships, number = 'VIII' }) {
  const events = Array.isArray(relationships?.events)
    ? relationships.events
    : (Array.isArray(relationships) ? relationships : []);
  const summary = relationships?.summary || {};
  const knownScopes = new Set(['natal', 'luck', 'annual', 'flowing_month', 'flowing_day', 'flowing_hour']);
  const grouped = {
    natal: events.filter((event) => event.scope === 'natal'),
    luck: events.filter((event) => event.scope === 'luck'),
    annual: events.filter((event) => event.scope === 'annual'),
    flowingMonth: events.filter((event) => event.scope === 'flowing_month'),
    flowingDay: events.filter((event) => event.scope === 'flowing_day'),
    flowingHour: events.filter((event) => event.scope === 'flowing_hour'),
    other: events.filter((event) => !knownScopes.has(event.scope)),
  };
  const groupRows = [
    { key: 'natal', shortLabel: 'Natal', title: 'Natal Chart', events: grouped.natal, empty: 'No configured natal relationship contacts were found.' },
    { key: 'luck', shortLabel: 'Luck', title: 'Current 10-Year Luck', events: grouped.luck, empty: 'No current Luck Pillar triggers are active for this chart yet.' },
    { key: 'annual', shortLabel: 'Year', title: 'Current Year', events: grouped.annual, empty: 'No current-year triggers were found against the natal chart.' },
    { key: 'flowingMonth', shortLabel: 'Month', title: 'Flowing Month', events: grouped.flowingMonth, empty: 'No current flowing-month triggers were found against the natal chart.' },
    { key: 'flowingDay', shortLabel: 'Day', title: 'Flowing Day', events: grouped.flowingDay, empty: 'No current flowing-day triggers were found against the natal chart.' },
    { key: 'flowingHour', shortLabel: 'Hour', title: 'Flowing Hour', events: grouped.flowingHour, empty: 'No current flowing-hour triggers were found against the natal chart.' },
    ...(grouped.other.length ? [{ key: 'other', shortLabel: 'Other', title: 'Other Contacts', events: grouped.other, empty: '' }] : []),
  ];
  const activeGroups = groupRows.filter((group) => group.events.length);
  const quietGroups = groupRows.filter((group) => !group.events.length && group.key !== 'other');

  return (
    <MemoSection
      number={number}
      title="Relationships"
      subtitle="Stem and branch contacts are grouped by natal chart and current timing layers."
    >
      <div className="space-y-5">
        <RelationshipOverviewCards events={events} summary={summary} />
        <RelationshipScopeStrip groups={groupRows} />
      </div>

      {!events.length ? (
        <StatePanel
          title="No relationship contacts detected."
          body="The engine did not find configured combinations, clashes, harms, punishments, destructions, or complete branch sets in this chart layer."
        />
      ) : (
        <div className="mt-6 space-y-8">
          {activeGroups.map((group) => (
            <RelationshipGroup key={group.key} title={group.title} events={group.events} empty={group.empty} />
          ))}
        </div>
      )}

      <QuietRelationshipLayers groups={quietGroups} />
    </MemoSection>
  );
}

function ScoreBreakdown({ scoring }) {
  const components = Array.isArray(scoring?.components) ? scoring.components : [];
  if (!components.length) return null;
  return (
    <div>
      <div className="mb-3 text-[12px] leading-relaxed text-zinc-500">
        Component deltas and context weights are product-defined and uncalibrated; inspect them as comparative evidence, not predicted relationship quality.
      </div>
      <div className="grid gap-3 lg:grid-cols-5">
        {components.map((component) => (
          <div key={component.key || component.label} className="rounded-sm border border-zinc-200 bg-white p-3">
            <Micro>{component.label || component.key}</Micro>
            <div className={`mt-2 text-[1.4rem] font-medium leading-none tracking-[-0.05em] ${Number(component.delta || 0) < 0 ? 'text-rose-700' : Number(component.delta || 0) > 0 ? 'text-teal-700' : 'text-zinc-900'}`} style={serifStyle}>
              {formatSignedDelta(component.delta)}
            </div>
            <div className="mt-2 text-[12px] leading-relaxed text-zinc-500">{component.summary || ''}</div>
            {Number.isFinite(Number(component.weight)) && Number(component.weight) !== 1 ? (
              <div className="mt-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>
                raw {formatSignedDelta(component.raw_delta)} / product weight {component.weight}
              </div>
            ) : null}
            {component.confidence ? (
              <div className="mt-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>
                confidence {component.confidence}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function formatSignedDelta(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric) || numeric === 0) return '0';
  return numeric > 0 ? `+${Math.round(numeric)}` : String(Math.round(numeric));
}

function TimingAlignmentCard({ title, profile }) {
  const spouse = profile?.spouse_palace || {};
  const counts = profile?.counts || {};
  const topEvents = Array.isArray(profile?.top_events) ? profile.top_events : [];
  const status = formatRelationshipStatus(profile?.status);
  const activePillar = profile?.active_luck_pillar || profile?.annual_pillar || null;
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Micro>{title}</Micro>
          <div className="mt-2 text-[1rem] font-semibold tracking-[-0.02em] text-zinc-900">{profile?.subject_label || '-'}</div>
          <div className="mt-1 text-xs text-zinc-500">
            Day palace {spouse?.branch || '-'} / {spouse?.animal || '-'} / {spouse?.branch_element || '-'}
          </div>
        </div>
        <Pill active={profile?.status === 'active_pressure'}>{status}</Pill>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3 border-y border-zinc-100 py-3">
        <RelationshipStat compact label="Day Events" value={counts.day_events || 0} />
        <RelationshipStat compact label="Active" value={counts.active || 0} />
        <RelationshipStat compact label="Pressure" value={(counts.challenging_active || 0) + (counts.challenging_natal || 0)} />
      </div>
      {activePillar ? (
        <div className="mt-3 text-[12px] leading-relaxed text-zinc-500">
          Timing pillar {activePillar.stem || '-'} {activePillar.branch || '-'}{activePillar.ten_god ? ` / ${activePillar.ten_god}` : ''}
        </div>
      ) : null}
      {profile?.reading_note ? <div className="mt-3 text-[12px] leading-relaxed text-zinc-600">{profile.reading_note}</div> : null}
      {topEvents.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {topEvents.slice(0, 3).map((event) => (
            <span key={event.id || event.label} className={`rounded-full border px-2.5 py-1 text-[11px] ${relationshipTone(event.type)} border-zinc-200`}>
              {event.label || relationshipTypeLabel(event.type)}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function formatRelationshipStatus(status) {
  return String(status || 'quiet').replace(/_/g, ' ');
}

function RelationshipStat({ label, value, compact = false }) {
  return (
    <div>
      <Micro>{label}</Micro>
      <div className={`mt-2 font-medium leading-none tracking-[-0.05em] text-zinc-900 ${compact ? 'text-[1.25rem]' : 'text-[2rem]'}`} style={serifStyle}>{value}</div>
    </div>
  );
}

function RelationshipGroup({ title, events, empty }) {
  return (
    <div>
      <div className="flex items-center gap-3 border-b border-zinc-200 pb-3">
        <span className="inline-block h-2 w-2 rounded-full bg-teal-600" />
        <Micro>{title}</Micro>
      </div>
      {events.length ? (
        <div className="grid gap-3 pt-4 lg:grid-cols-2">
          {events.map((event) => <RelationshipCard key={event.id || `${event.type}-${event.label}`} event={event} />)}
        </div>
      ) : (
        <div className="pt-4 text-sm text-zinc-500">{empty}</div>
      )}
    </div>
  );
}

function RelationshipCard({ event }) {
  const tone = relationshipTone(event?.type);
  const palaces = Array.isArray(event?.affected_palaces) ? event.affected_palaces.join(' / ') : '';
  const domains = Array.isArray(event?.affected_domains) ? event.affected_domains.filter(Boolean).join(' / ') : '';
  const symbols = Array.isArray(event?.symbols) ? event.symbols.join(' + ') : '';
  return (
    <div className="rounded-sm border border-zinc-200 bg-white px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Micro className={tone}>{relationshipTypeLabel(event?.type)}</Micro>
          <div className="mt-2 text-[1.05rem] font-semibold tracking-[-0.02em] text-zinc-900">{event?.label || 'Relationship code'}</div>
          <div className="mt-2 text-sm leading-relaxed text-zinc-600">{palaces || domains || 'Palace details unavailable.'}</div>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-[1.2rem] font-medium leading-none tracking-[-0.04em] text-zinc-900" style={serifStyle}>{symbols || '-'}</div>
          <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>{event?.intensity || event?.scope_label || ''}</div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-zinc-500">
        {event?.element ? <span>{event.element} element</span> : null}
        {event?.scope_label ? <span>{event.scope_label}</span> : null}
        {domains ? <span>{domains}</span> : null}
      </div>
      {event?.reading_note ? <div className="mt-3 text-[12px] leading-relaxed text-zinc-500">{event.reading_note}</div> : null}
    </div>
  );
}

function relationshipTypeLabel(type) {
  return String(type || 'relationship').replace(/_/g, ' ');
}

function ruleTokenLabel(value) {
  return String(value || '-')
    .replace(/^yong_shen\./, '')
    .replace(/_/g, ' ');
}

function titleTokenLabel(value) {
  return ruleTokenLabel(value)
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function relationshipTone(type) {
  const normalized = String(type || '');
  if (normalized.includes('clash') || normalized.includes('harm') || normalized.includes('punishment') || normalized.includes('destruction')) {
    return 'text-rose-700';
  }
  if (normalized.includes('combination') || normalized.includes('cross')) return 'text-teal-700';
  return 'text-zinc-500';
}

function elementTotals(balance) {
  const raw = balance?.total || balance?.counts || {};
  return ELEMENTS.reduce((acc, element) => {
    acc[element] = Number(raw[element] || 0);
    return acc;
  }, {});
}

function rankedElements(balance, strongest = true) {
  const totals = elementTotals(balance);
  return ELEMENTS
    .map((element) => ({ element, count: totals[element] || 0 }))
    .sort((a, b) => strongest ? (b.count - a.count || a.element.localeCompare(b.element)) : (a.count - b.count || a.element.localeCompare(b.element)));
}

function formatElementRank(rows, fallback = '-') {
  const active = rows.filter((row) => Number.isFinite(row.count));
  if (!active.length || active.reduce((sum, row) => sum + row.count, 0) <= 0) return fallback;
  return active.slice(0, 2).map((row) => `${row.element} ${row.count}`).join(' / ');
}

function overviewUsefulStatus(usefulElements) {
  const usefulGod = usefulElements?.useful_god || {};
  if (usefulGod.final_status === 'final') {
    return {
      value: ruleTokenLabel(usefulGod.decision_path || usefulGod.candidate_role || 'Final'),
      detail: usefulGod.reason || 'The useful-element gate is clear for this chart.',
      active: true,
    };
  }
  if (usefulElements?.status === 'provisional') {
    return {
      value: 'candidate path',
      detail: 'Helpful elements are available as a decision path for this chart.',
      active: false,
    };
  }
  return {
    value: 'held back',
    detail: 'The chart does not yet meet the release conditions for a final Useful God.',
    active: false,
  };
}

function overviewTimingStatus(timing) {
  const active = timing?.active_luck_pillar || {};
  if (timing?.luck_pillars_enabled) {
    return {
      value: [active.stem, active.branch].filter(Boolean).join(' ') || 'Luck Pillars active',
      detail: active.age_label ? `Active decade: ${active.age_label}` : `Direction: ${timing.direction || 'pending'}`,
      active: true,
    };
  }
  const layers = Array.isArray(timing?.rhythm?.layers) ? timing.rhythm.layers : [];
  const liveLayers = layers.filter((layer) => layer?.layer && layer.layer !== 'da_yun');
  return {
    value: liveLayers.length ? 'current flow available' : 'decade not calculated',
    detail: liveLayers.length
      ? 'Annual, month, day, and hour layers remain available; set primary calculation sex to add Da Yun.'
      : 'Set primary calculation sex to add the decade Luck Pillar layer.',
    active: Boolean(liveLayers.length),
  };
}

function OverviewSignalCard({ label, value, detail, active = false }) {
  return (
    <div className={`rounded-sm border bg-white p-4 ${active ? 'border-teal-200' : 'border-zinc-200'}`}>
      <Micro className={active ? 'text-teal-700' : ''}>{label}</Micro>
      <div className="mt-2 min-h-[1.75rem] text-[1rem] font-semibold leading-snug text-zinc-950">
        {value || '-'}
      </div>
      {detail ? <div className="mt-2 text-[12px] leading-relaxed text-zinc-500">{detail}</div> : null}
    </div>
  );
}

function OverviewSignals({ data }) {
  const dayMaster = data?.day_master || {};
  const analysis = data?.analysis || {};
  const model = analysis?.strength_model || {};
  const season = model?.season || {};
  const root = model?.root || {};
  const strongest = rankedElements(data?.element_balance, true);
  const weakest = rankedElements(data?.element_balance, false);
  const useful = overviewUsefulStatus(data?.useful_elements || {});
  const timing = overviewTimingStatus(data?.timing || {});
  const relationships = data?.relationships || {};
  const eventCount = Number((relationships.summary || {}).total ?? (Array.isArray(relationships.events) ? relationships.events.length : 0));
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <OverviewSignalCard
        label="Day Master"
        value={<StemValue stem={dayMaster.stem} element={dayMaster.element} compact />}
        detail={`${dayMaster.polarity || '-'} ${dayMaster.element || 'element'} / ${analysis.strength || 'strength pending'}`}
        active
      />
      <OverviewSignalCard
        label="Season & Roots"
        value={season.season || data?.pillars?.month?.branch || 'pending'}
        detail={`Month ${data?.pillars?.month?.branch || '-'} / ${season.state || 'season pending'} / root ${root.score ?? '-'}`}
      />
      <OverviewSignalCard
        label="Element Spread"
        value={formatElementRank(strongest)}
        detail={`Lightest: ${formatElementRank(weakest)}`}
      />
      <OverviewSignalCard
        label="Helpful Element Gate"
        value={<Pill active={useful.active}>{useful.value}</Pill>}
        detail={useful.detail}
        active={useful.active}
      />
      <OverviewSignalCard
        label="Timing"
        value={timing.value}
        detail={timing.detail}
        active={timing.active}
      />
      <OverviewSignalCard
        label="Relationship Contacts"
        value={`${Number.isFinite(eventCount) ? eventCount : 0} active`}
        detail={eventCount ? 'Review the Relationships tab for placement and timing contacts.' : 'No relationship-contact pressure returned for this profile.'}
      />
    </div>
  );
}

function LifeAreasPanel({ lifeAreas, context }) {
  const areas = Array.isArray(lifeAreas?.areas) ? lifeAreas.areas : [];
  const palaces = Array.isArray(context?.palaces) ? context.palaces : [];

  return (
    <MemoSection
      number="VII"
      title="Life Areas"
      subtitle="Topic areas organize chart evidence by pillar, role, element, and timing."
    >
      {lifeAreas?.summary ? (
        <div className="mb-6 border-b border-zinc-200 pb-5">
          <Micro>Current Topic Map</Micro>
          <div className="mt-2 max-w-3xl text-[1.1rem] font-medium leading-snug text-zinc-900" style={serifStyle}>
            {lifeAreas.summary}
          </div>
        </div>
      ) : null}

      {areas.length ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {areas.map((area) => <LifeAreaCard key={area.id || area.label} area={area} />)}
        </div>
      ) : palaces.length ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {palaces.map((palace) => <PalaceCard key={palace.pillar} palace={palace} />)}
        </div>
      ) : (
        <EmptyPanel title="Life areas unavailable" body="The backend did not return enough pillar and Ten God evidence to build this topic map." />
      )}

    </MemoSection>
  );
}

function LifeAreaCard({ area }) {
  const signals = Array.isArray(area?.signals) ? area.signals : [];
  const keywords = Array.isArray(area?.keywords) ? area.keywords : [];
  const bodyBalance = area?.body_balance || null;
  const bodyCorrespondences = Array.isArray(bodyBalance?.symbolic_body_correspondences) ? bodyBalance.symbolic_body_correspondences : [];
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-4">
        <div>
          <Micro>{area?.short_label || 'Topic'}</Micro>
          <div className="mt-2 text-[1.35rem] font-medium leading-tight text-zinc-950" style={serifStyle}>
            {area?.label || 'Life Area'}
          </div>
        </div>
        <span className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${lifeAreaStateClass(area?.context_state)}`} style={monoStyle}>
          {lifeAreaStateLabel(area?.context_state)}
        </span>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-zinc-700">{area?.summary || 'This topic needs more chart evidence before it can be prioritized.'}</p>
      {area?.guidance ? <p className="mt-3 text-sm leading-relaxed text-zinc-500">{area.guidance}</p> : null}

      <div className="mt-4 grid gap-3 text-[12px] sm:grid-cols-3">
        <LifeAreaMetric label="Visible" value={area?.visible_factor_count ?? 0} />
        <LifeAreaMetric label="Hidden" value={area?.hidden_factor_count ?? 0} />
        <LifeAreaMetric label="Contacts" value={area?.relationship_contact_count ?? 0} />
      </div>

      {signals.length ? (
        <div className="mt-4 border-t border-zinc-100 pt-3">
          <Micro>Evidence</Micro>
          <div className="mt-2 grid gap-2">
            {signals.map((signal, index) => (
              <LifeAreaSignal key={`${signal.type || 'signal'}-${signal.label || index}-${index}`} signal={signal} />
            ))}
          </div>
        </div>
      ) : null}

      {bodyBalance?.status ? (
        <div className="mt-4 border-t border-zinc-100 pt-3">
          <Micro>Body Balance Evidence</Micro>
          <div className="mt-2 grid gap-2 text-[12px] sm:grid-cols-2">
            <div className="rounded-sm border border-zinc-100 bg-zinc-50 px-3 py-2">
              <span className="text-zinc-400">Excess watch</span> {(bodyBalance.element_excess || []).join(' / ') || '-'}
            </div>
            <div className="rounded-sm border border-zinc-100 bg-zinc-50 px-3 py-2">
              <span className="text-zinc-400">Deficiency watch</span> {(bodyBalance.element_deficiency || []).join(' / ') || '-'}
            </div>
          </div>
          {bodyCorrespondences.length ? (
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {bodyCorrespondences.slice(0, 5).map((row) => (
                <div key={row.element} className="rounded-sm border border-zinc-100 bg-white px-3 py-2 text-[11px] leading-relaxed text-zinc-600">
                  <span className="font-semibold text-zinc-900">{row.element}</span> x{row.count ?? 0}
                  <span className="text-zinc-400"> / hidden {row.hidden_count ?? 0}</span>
                  {Array.isArray(row.systems) && row.systems.length ? <div className="mt-1">{row.systems.join(' / ')}</div> : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {keywords.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {keywords.map((keyword) => <Pill key={keyword}>{keyword}</Pill>)}
        </div>
      ) : null}
    </div>
  );
}

function LifeAreaMetric({ label, value }) {
  return (
    <div>
      <div className="uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>{label}</div>
      <div className="mt-1 text-sm font-semibold text-zinc-900">{value}</div>
    </div>
  );
}

function LifeAreaSignal({ signal }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-b border-zinc-100 pb-2 text-[12px] last:border-b-0 last:pb-0">
      <div>
        <span className={lifeAreaSignalClass(signal?.tone)}>{signal?.label || '-'}</span>
        {signal?.type ? <span className="ml-2 text-zinc-400">{ruleTokenLabel(signal.type)}</span> : null}
      </div>
      <div className="text-zinc-500">{signal?.detail || '-'}</div>
    </div>
  );
}

function lifeAreaStateLabel(status) {
  const normalized = String(status || '');
  if (normalized === 'timing_active') return 'Timing active';
  if (normalized === 'emphasized') return 'Emphasized';
  if (normalized === 'context_required') return 'Context needed';
  return 'Quiet';
}

function lifeAreaStateClass(status) {
  const normalized = String(status || '');
  if (normalized === 'timing_active') return 'border-zinc-950 bg-zinc-950 text-white';
  if (normalized === 'emphasized') return 'border-teal-200 bg-teal-50 text-teal-800';
  if (normalized === 'context_required') return 'border-amber-200 bg-amber-50 text-amber-800';
  return 'border-zinc-200 bg-white text-zinc-500';
}

function lifeAreaSignalClass(tone) {
  const normalized = String(tone || '');
  if (normalized === 'activation') return 'text-zinc-950 font-semibold';
  if (normalized === 'contact') return 'text-rose-700';
  if (normalized === 'role') return 'text-teal-700';
  return 'text-zinc-700';
}

function PalaceCard({ palace }) {
  const events = Array.isArray(palace?.relationship_events) ? palace.relationship_events : [];
  const auxiliaryHits = Array.isArray(palace?.auxiliary_hits) ? palace.auxiliary_hits : [];
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-4">
        <div>
          <Micro>{palace?.pillar_label || palace?.pillar}</Micro>
          <div className="mt-2 text-[1.45rem] font-medium leading-none text-zinc-950" style={serifStyle}>
            {palace?.stem || '-'} {palace?.branch || '-'}
          </div>
          <div className="mt-2 text-sm text-zinc-500">{palace?.animal || '-'} / {palace?.life_stage || '-'} / {palace?.age_range || '-'}</div>
        </div>
        <div className="text-right">
          <div className="text-sm font-semibold text-zinc-900">{palace?.relationship_event_count ?? 0}</div>
          <div className="mt-1 text-[10px] uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>codes</div>
        </div>
      </div>

      <div className="mt-4 text-sm leading-relaxed text-zinc-600">{palace?.summary || palace?.domain || 'Palace details unavailable.'}</div>

      <dl className="mt-4 grid gap-3 text-[12px] sm:grid-cols-2">
        <div>
          <dt className="uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>Stem field</dt>
          <dd className="mt-1 text-zinc-700">{palace?.stem_domain || '-'}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>Branch field</dt>
          <dd className="mt-1 text-zinc-700">{palace?.branch_domain || '-'}</dd>
        </div>
      </dl>

      {events.length ? (
        <div className="mt-4 border-t border-zinc-100 pt-3">
          <Micro>Relationship Contacts</Micro>
          <div className="mt-2 space-y-2">
            {events.map((event) => (
              <div key={event.id || `${event.label}-${event.scope}`} className="text-[12px] leading-relaxed text-zinc-600">
                <span className={relationshipTone(event.type)}>{event.label}</span>
                {event.scope_label ? <span className="text-zinc-400"> / {event.scope_label}</span> : null}
                {event.placement_note ? <span className="text-zinc-400"> / {event.placement_note}</span> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {auxiliaryHits.length ? (
        <div className="mt-4 border-t border-zinc-100 pt-3">
          <Micro>Auxiliary Hits</Micro>
          <div className="mt-2 space-y-2 text-[12px] leading-relaxed text-zinc-600">
            {auxiliaryHits.map((hit) => (
              <div key={`${hit.label}-${hit.branch}`}>
                {hit.label}: {hit.branch || '-'} {hit.animal || ''}{hit.pressure ? ` / ${hit.pressure}` : ''}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function pressureToneClass(status) {
  if (status === 'pressured') return 'border-rose-200 bg-rose-50 text-rose-800';
  if (status === 'supported') return 'border-teal-200 bg-teal-50 text-teal-800';
  if (status === 'mixed') return 'border-amber-200 bg-amber-50 text-amber-800';
  return 'border-zinc-200 bg-zinc-50 text-zinc-700';
}

function AuxiliaryStarsPanel({ stars }) {
  const peach = stars?.peach_blossom || null;
  const markers = Array.isArray(stars?.markers)
    ? stars.markers
    : (peach?.status === 'source_based_preview' ? [peach] : []);
  return (
    <MemoSection
      number="IX"
      title="Auxiliary Stars"
      subtitle="Shen Sha markers add named placement cues after the pillar chart is read."
    >
      {markers.length ? (
        <AuxiliaryMarkerGrid markers={markers} />
      ) : (
        <EmptyPanel title="Auxiliary stars unavailable" body="The backend did not return enough branch evidence to calculate this star layer." />
      )}
    </MemoSection>
  );
}

function auxiliaryMarkerToneClass(state) {
  if (state === 'pressured') return 'border-rose-200 bg-rose-50 text-rose-800';
  if (state === 'supported' || state === 'active') return 'border-teal-200 bg-teal-50 text-teal-800';
  if (state === 'mixed') return 'border-amber-200 bg-amber-50 text-amber-800';
  return 'border-zinc-200 bg-zinc-50 text-zinc-700';
}

function AuxiliaryMarkerGrid({ markers }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {markers.map((marker, index) => (
        <AuxiliaryMarkerCard key={`${marker?.id || marker?.label}-${marker?.reference?.value || index}-${index}`} marker={marker} />
      ))}
    </div>
  );
}

function AuxiliaryMarkerCard({ marker }) {
  const activations = Array.isArray(marker?.activations) ? marker.activations : [];
  const keywords = Array.isArray(marker?.keywords) ? marker.keywords : [];
  const targets = Array.isArray(marker?.targets) ? marker.targets : [];
  const pressure = marker?.pressure || {};
  const impacts = Array.isArray(pressure?.event_impacts) ? pressure.event_impacts : [];
  const reference = marker?.reference || {};
  const flowing = Array.isArray(marker?.flowing_activations) ? marker.flowing_activations : [];
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-4">
        <div>
          <Micro>{marker?.label || 'Auxiliary Marker'}</Micro>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <div className="text-2xl font-medium tracking-[-0.03em] text-zinc-950" style={serifStyle}>
              {[marker?.chinese, marker?.pinyin].filter(Boolean).join(' / ') || marker?.target_summary || '-'}
            </div>
            <div className="text-sm text-zinc-500">
              {reference?.label || 'Reference'} {reference?.value || '-'}
            </div>
          </div>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${auxiliaryMarkerToneClass(marker?.marker_state)}`} style={monoStyle}>
          {marker?.state_label || marker?.marker_state || 'Open'}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3">
        <TimingMetric label="Natal" value={marker?.natal_count ?? 0} />
        <TimingMetric label="Timing" value={marker?.timing_count ?? 0} />
        <TimingMetric label="Pressure" value={pressure?.status || 'clear'} />
      </div>

      {marker?.summary ? <p className="mt-4 text-sm leading-relaxed text-zinc-600">{marker.summary}</p> : null}
      {marker?.theme ? <p className="mt-2 text-xs leading-relaxed text-zinc-500">{marker.theme}</p> : null}
      {marker?.placement_interpretation?.summary || marker?.timing_interpretation?.summary ? (
        <div className="mt-3 grid gap-2 text-[12px] leading-relaxed text-zinc-600 sm:grid-cols-2">
          {marker?.placement_interpretation?.summary ? <div className="rounded-sm border border-zinc-100 bg-zinc-50 px-3 py-2">{marker.placement_interpretation.summary}</div> : null}
          {marker?.timing_interpretation?.summary ? <div className="rounded-sm border border-zinc-100 bg-zinc-50 px-3 py-2">{marker.timing_interpretation.summary}</div> : null}
        </div>
      ) : null}

      {targets.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {targets.map((target) => (
            <span key={`${target.type}-${target.value}`} className="rounded-full border border-zinc-200 px-2.5 py-1 text-[11px] leading-none text-zinc-600">
              {target.label || target.value}
            </span>
          ))}
        </div>
      ) : null}

      {activations.length ? (
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {activations.slice(0, 4).map((item, index) => (
            <div key={`${item.layer}-${item.pillar}-${index}`} className="rounded-sm border border-zinc-100 bg-zinc-50/70 px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-xs font-semibold text-zinc-900">{item.pillar_label || item.pillar}</div>
                  <div className="mt-1 text-[11px] text-zinc-500">{item.domain || item.layer}</div>
                </div>
                <div className="text-right text-xs text-zinc-700">
                  {[item.stem, item.branch || item.animal].filter(Boolean).join(' / ')}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {flowing.length ? (
        <div className="mt-4 border-t border-zinc-100 pt-3">
          <Micro>Flowing Activation</Micro>
          <div className="mt-2 flex flex-wrap gap-2">
            {flowing.slice(0, 4).map((item, index) => (
              <Pill key={`${item.layer}-${item.stem}-${item.branch}-${index}`} active>
                {ruleTokenLabel(item.layer)} {item.stem || ''} {item.branch || ''}
              </Pill>
            ))}
          </div>
        </div>
      ) : null}

      {impacts.length ? (
        <div className="mt-4 space-y-2 border-t border-zinc-100 pt-3">
          {impacts.slice(0, 3).map((impact) => (
            <div key={`${impact.label}-${impact.scope}`} className="text-[12px] leading-relaxed text-zinc-600">
              <span className={relationshipTone(impact.type)}>{impact.label}</span>
              {impact.scope_label ? <span className="text-zinc-400"> / {impact.scope_label}</span> : null}
            </div>
          ))}
        </div>
      ) : null}

      {keywords.length ? (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {keywords.slice(0, 4).map((keyword) => (
            <span key={keyword} className="rounded-full bg-zinc-50 px-2 py-1 text-[11px] leading-none text-zinc-600">{keyword}</span>
          ))}
        </div>
      ) : null}

    </div>
  );
}

function PeachBlossomPanel({ peach }) {
  const activations = Array.isArray(peach?.activations) ? peach.activations : [];
  const pressure = peach?.pressure || {};
  const impacts = Array.isArray(pressure?.event_impacts) ? pressure.event_impacts : [];
  const family = peach?.branch_family || {};
  const keywords = Array.isArray(peach?.keywords) ? peach.keywords : [];
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="grid gap-6 border-b border-zinc-100 pb-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          <Micro>Peach Blossom</Micro>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <div className="text-[2.4rem] font-medium leading-none tracking-[-0.06em] text-zinc-950" style={serifStyle}>
              {peach?.target_branch || '-'}
            </div>
            <div className="text-sm text-zinc-500">{peach?.target_animal || '-'} from Day Branch {peach?.day_branch || '-'}</div>
          </div>
          {peach?.summary ? <p className="mt-3 max-w-3xl text-sm leading-relaxed text-zinc-600">{peach.summary}</p> : null}
          {keywords.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {keywords.map((keyword) => (
                <span key={keyword} className="rounded-full border border-zinc-200 px-2.5 py-1 text-[11px] leading-none text-zinc-600">{keyword}</span>
              ))}
            </div>
          ) : null}
        </div>
        <div className="grid grid-cols-3 gap-3">
          <TimingMetric label="Natal" value={peach?.natal_count ?? 0} />
          <TimingMetric label="Timing" value={peach?.timing_count ?? 0} />
          <TimingMetric label="Pressure" value={pressure?.status || 'clear'} />
        </div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <div>
          <Micro>Activations</Micro>
          {activations.length ? (
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {activations.map((item, index) => (
                <div key={`${item.layer}-${item.pillar}-${index}`} className="rounded-sm border border-zinc-100 bg-zinc-50/70 px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-zinc-900">{item.pillar_label || item.pillar}</div>
                      <div className="mt-1 text-xs text-zinc-500">{item.domain || item.layer}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-zinc-900">{item.branch} / {item.animal}</div>
                      <div className="mt-1 text-[10px] uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>{item.layer}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-3 text-sm text-zinc-500">No natal, Luck Pillar, or annual activation found for the personal Peach Blossom branch.</div>
          )}
        </div>

        <div className="rounded-sm border border-zinc-200 bg-white px-4 py-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Micro>Pressure Check</Micro>
              <div className="mt-2 text-sm leading-relaxed text-zinc-600">
                Relationship codes touching this branch keep the reading specific to the affected palace and timing layer.
              </div>
            </div>
            <span className={`rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${pressureToneClass(pressure?.status)}`} style={monoStyle}>
              {pressure?.status || 'clear'}
            </span>
          </div>
          {impacts.length ? (
            <div className="mt-4 space-y-2 border-t border-zinc-100 pt-3">
              {impacts.map((impact) => (
                <div key={`${impact.label}-${impact.scope}`} className="text-[12px] leading-relaxed text-zinc-600">
                  <span className={relationshipTone(impact.type)}>{impact.label}</span>
                  {impact.scope_label ? <span className="text-zinc-400"> / {impact.scope_label}</span> : null}
                </div>
              ))}
            </div>
          ) : null}
          <div className="mt-4 border-t border-zinc-100 pt-3 text-[12px] leading-relaxed text-zinc-500">
            Peach Blossom family branches present: {Array.isArray(family.present) && family.present.length ? family.present.join(', ') : 'none'}.
            {family.all_four_present ? ' All four are present, so placement context matters more than the marker name alone.' : ''}
          </div>
        </div>
      </div>
    </div>
  );
}

function ClassicalExtrasPanel({ extras }) {
  const tai = extras?.tai_yuan || {};
  const ming = extras?.ming_gong || {};
  const naYinRows = Array.isArray(extras?.na_yin?.pillars) ? extras.na_yin.pillars : [];
  return (
    <MemoSection
      number="XI"
      title="Classical Extras"
      subtitle="Tai Yuan, Ming Gong, and Na Yin sit beside the main BaZi structure."
    >
      <div className="grid gap-4 lg:grid-cols-3">
        <ClassicalExtraCard title="Tai Yuan" item={tai} />
        <ClassicalExtraCard title="Ming Gong" item={ming} />
        <div className="rounded-sm border border-zinc-200 bg-white p-5">
          <Micro>Na Yin</Micro>
          <div className="mt-2 text-sm leading-relaxed text-zinc-600">
            {extras?.na_yin?.summary || 'Na Yin rows are unavailable.'}
          </div>
          {naYinRows.length ? (
            <div className="mt-4 space-y-2">
              {naYinRows.map((row) => (
                <div key={`${row.pillar}-${row.stem}-${row.branch}`} className="flex items-center justify-between gap-3 border-b border-zinc-100 pb-2 text-[12px] last:border-0 last:pb-0">
                  <span className="font-semibold capitalize text-zinc-900">{row.pillar}</span>
                  <span className="text-zinc-600">{row.stem} {row.branch} / {row.na_yin || '-'}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
      {Array.isArray(extras?.notes) && extras.notes.length ? (
        <div className="mt-5 grid gap-2 text-sm leading-relaxed text-zinc-600 md:grid-cols-2">
          {extras.notes.map((note) => <div key={note} className="border-l border-zinc-300 pl-3">{note}</div>)}
        </div>
      ) : null}
    </MemoSection>
  );
}

function ClassicalExtraCard({ title, item }) {
  const pillar = item?.pillar || {};
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Micro>{title}</Micro>
          <div className="mt-2 text-[1.45rem] font-medium leading-none text-zinc-950" style={serifStyle}>
            {pillar?.stem && pillar?.branch ? `${pillar.stem} ${pillar.branch}` : '-'}
          </div>
        </div>
        <Pill active={String(item?.status || '').includes('preview')}>{ruleTokenLabel(item?.status || 'withheld')}</Pill>
      </div>
      {item?.summary ? <div className="mt-3 text-sm leading-relaxed text-zinc-600">{item.summary}</div> : null}
      {item?.reason ? <div className="mt-3 text-sm leading-relaxed text-zinc-500">{item.reason}</div> : null}
    </div>
  );
}

function InterpretationPanel({ data }) {
  const interpretation = data?.interpretation || {};
  const sections = Array.isArray(interpretation?.sections) ? interpretation.sections : [];
  return (
    <MemoSection
      number="II"
      title="Reading Overview"
      subtitle="A plain-language bridge from the Day Master into strength, element roles, timing, and relationship-contact pressure."
    >
      {interpretation?.summary ? (
        <div className="border-b border-zinc-200 pb-5">
          <Micro>Current Reading</Micro>
          <div className="mt-2 max-w-3xl text-[1.35rem] font-medium leading-snug tracking-[-0.03em] text-zinc-900" style={serifStyle}>
            {interpretation.summary}
          </div>
        </div>
      ) : null}
      <div className="mt-6">
        <OverviewSignals data={data} />
      </div>
      {sections.length ? (
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {sections.map((section, index) => (
            <div key={`${section.title || 'section'}-${index}`} className="rounded-sm border border-zinc-200 bg-white p-5">
              <Micro>{section.title || 'Reading'}</Micro>
              <div className="mt-4 space-y-3 text-sm leading-relaxed text-zinc-600">
                {(Array.isArray(section.items) ? section.items : []).map((item) => (
                  <div key={item} className="border-l border-teal-300 pl-3">{item}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyPanel title="Reading unavailable" body="The backend did not return a curated interpretation for this chart." />
      )}
    </MemoSection>
  );
}

function UsefulElementsPanel({ recommendations }) {
  const favorable = Array.isArray(recommendations?.favorable) ? recommendations.favorable : [];
  const unfavorable = Array.isArray(recommendations?.unfavorable) ? recommendations.unfavorable : [];
  const candidates = Array.isArray(recommendations?.candidates_to_watch) ? recommendations.candidates_to_watch : [];
  const integrity = Array.isArray(recommendations?.element_integrity) ? recommendations.element_integrity : [];
  const integritySummary = recommendations?.integrity_summary || {};
  const climate = recommendations?.climate_adjustment || {};
  const climateRows = Array.isArray(climate?.recommendations) ? climate.recommendations : [];
  const damageRows = Array.isArray(recommendations?.damage_assessment) ? recommendations.damage_assessment : [];
  const damageSummary = recommendations?.damage_summary || {};
  const tongGuan = recommendations?.tong_guan || {};
  const tongGuanCandidates = Array.isArray(tongGuan?.candidates) ? tongGuan.candidates : [];
  const usefulGod = recommendations?.useful_god || {};
  const usefulGodEvidence = usefulGod?.evidence || {};
  const usefulGodStatus = usefulGod?.final_status === 'final'
    ? 'Final'
    : usefulGod?.candidate_status === 'candidate_preview' ? 'Candidate' : 'Withheld';
  const blockingReasons = Array.isArray(usefulGod?.blocking_reasons) ? usefulGod.blocking_reasons : [];
  const specialScreen = recommendations?.special_structure_screen || {};
  const specialFlags = Array.isArray(specialScreen?.flags) ? specialScreen.flags : [];
  const notes = Array.isArray(recommendations?.notes) ? recommendations.notes : [];
  const withheldBody = blockingReasons.length
    ? `The engine is holding the final ruling because: ${blockingReasons.map(ruleTokenLabel).join(', ')}.`
    : 'The current strength evidence is balanced or uncertain, so the app does not name a definitive Yong Shen for this chart.';
  return (
    <MemoSection
      number="V"
      title="Useful Elements"
      subtitle="Helpful elements are organized as a decision path through strength, climate, structure, damage, and timing."
    >
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <ProvisionalBadge>{recommendations?.status === 'withheld' ? 'Withheld' : 'Decision Path'}</ProvisionalBadge>
      </div>
      <div className="grid gap-5 border-b border-zinc-200 pb-5 md:grid-cols-3">
        <TimingMetric label="Status" value={recommendations?.status || '-'} />
        <TimingMetric label="Confidence" value={recommendations?.confidence || '-'} />
        <TimingMetric label="Strength" value={recommendations?.day_master_strength || '-'} />
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <div className="rounded-sm border border-zinc-200 bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Micro>Useful God Gate</Micro>
            <ProvisionalBadge>{usefulGodStatus}</ProvisionalBadge>
          </div>
          <div className="mt-3 text-[1.2rem] font-semibold tracking-[-0.02em] text-zinc-900">
            {usefulGod?.element ? `${usefulGod.element} / ${usefulGod.role || '-'}` : 'Final Yong Shen withheld'}
          </div>
          {usefulGod?.reason ? <div className="mt-2 text-sm leading-relaxed text-zinc-600">{usefulGod.reason}</div> : null}
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <TimingMetric label="Decision Path" value={ruleTokenLabel(usefulGod?.decision_path)} />
            <TimingMetric label="Final Status" value={ruleTokenLabel(usefulGod?.final_status || usefulGod?.candidate_status || 'withheld')} />
          </div>
          {blockingReasons.length ? (
            <div className="mt-4">
              <Micro>Blocking Reasons</Micro>
              <div className="mt-2 flex flex-wrap gap-2">
                {blockingReasons.map((reason) => <Pill key={reason}>{ruleTokenLabel(reason)}</Pill>)}
              </div>
            </div>
          ) : null}
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <TimingMetric label="Damaged" value={damageSummary?.damaged ?? 0} />
            <TimingMetric label="Absent" value={damageSummary?.absent ?? 0} />
            <TimingMetric label="Checked" value={damageSummary?.checked ?? 0} />
          </div>
          <div className="mt-4">
            <DecisionEvidencePanel evidence={usefulGodEvidence} />
          </div>
        </div>

        <div className="rounded-sm border border-zinc-200 bg-white p-5">
          <Micro>Climate Regulating</Micro>
          <div className="mt-2 text-sm text-zinc-500">
            {climate?.season || 'Unknown'} season{climate?.month_branch ? ` / month ${climate.month_branch}` : ''}
          </div>
          {climateRows.length ? (
            <div className="mt-4 space-y-3">
              {climateRows.map((row) => (
                <div key={`${row.element}-${row.function}`} className="border-b border-zinc-100 pb-3 last:border-0 last:pb-0">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold text-zinc-900">{row.stem ? `${row.stem} / ${row.element}` : row.element}</div>
                    <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-500" style={monoStyle}>{row.priority || '-'} / x{row.count ?? 0}</div>
                  </div>
                  {row.condition ? <div className="mt-2 text-[12px] leading-relaxed text-zinc-700">{row.condition}</div> : null}
                  <div className="mt-2 text-[12px] leading-relaxed text-zinc-600">{row.reason}</div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {row.override_candidate ? <Pill active>override candidate</Pill> : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-3 text-sm text-zinc-500">No climate-regulating row was returned for this season.</div>
          )}
        </div>
      </div>

      {recommendations?.status === 'withheld' ? (
        <StatePanel
          tone="warn"
          title="Final Useful God withheld."
          body={withheldBody}
        />
      ) : null}

      {favorable.length || unfavorable.length ? (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <UsefulElementGroup title="Favorable Preview" items={favorable} tone="teal" />
          <UsefulElementGroup title="Use With Caution" items={unfavorable} tone="rose" />
        </div>
      ) : null}

      {candidates.length ? (
        <div className="mt-6 rounded-sm border border-zinc-200 bg-white p-5">
          <Micro>Elements To Watch</Micro>
          <div className="mt-4 flex flex-wrap gap-2">
            {candidates.map((item) => (
              <Pill key={item.element}>{item.element} x{item.count}</Pill>
            ))}
          </div>
        </div>
      ) : null}

      {integrity.length ? (
        <ElementIntegrityPanel rows={integrity} summary={integritySummary} />
      ) : null}

      {damageRows.length || specialFlags.length ? (
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {damageRows.length ? <DamageAssessmentPanel rows={damageRows} /> : null}
          <SpecialStructurePanel screen={specialScreen} />
        </div>
      ) : null}

      {tongGuanCandidates.length ? (
        <TongGuanPanel analysis={tongGuan} />
      ) : null}

      {notes.length ? (
        <div className="mt-6 space-y-2 border-t border-zinc-200 pt-4 text-sm leading-relaxed text-zinc-600">
          {notes.map((note) => <div key={note} className="border-l border-zinc-300 pl-3">{note}</div>)}
        </div>
      ) : null}
    </MemoSection>
  );
}

function TongGuanPanel({ analysis }) {
  const candidates = Array.isArray(analysis?.candidates) ? analysis.candidates : [];
  return (
    <div className="mt-6 rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Micro>Tong Guan Bridge</Micro>
          <div className="mt-2 text-sm leading-relaxed text-zinc-600">
            {analysis?.notes?.[0] || 'Bridge elements are checked when a damaged useful path needs circulation rather than direct opposition.'}
          </div>
        </div>
        <Pill active={analysis?.status === 'active'}>{ruleTokenLabel(analysis?.status || 'quiet')}</Pill>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {candidates.map((candidate) => (
          <div key={`${candidate.element}-${candidate.target_element}-${candidate.damaging_element}`} className="rounded-sm border border-zinc-100 bg-zinc-50/70 px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-zinc-900">{candidate.element}</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.14em] text-zinc-500" style={monoStyle}>
                  {candidate.damaging_element || '-'} to {candidate.target_element || '-'}
                </div>
              </div>
              <Pill active={candidate.decision_candidate}>{candidate.decision_candidate ? 'bridge candidate' : 'watch'}</Pill>
            </div>
            {candidate.reason ? <div className="mt-2 text-[12px] leading-relaxed text-zinc-600">{candidate.reason}</div> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function UsefulElementGroup({ title, items, tone }) {
  const border = tone === 'rose' ? 'border-rose-200' : 'border-teal-200';
  const micro = tone === 'rose' ? 'text-rose-700' : 'text-teal-700';
  if (!items.length) {
    return (
      <div className="rounded-sm border border-zinc-200 bg-white p-5">
        <Micro>{title}</Micro>
        <div className="mt-3 text-sm text-zinc-500">No items in this group.</div>
      </div>
    );
  }
  return (
    <div className={`rounded-sm border ${border} bg-white p-5`}>
      <Micro className={micro}>{title}</Micro>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div key={`${item.element}-${item.role}-${item.priority}`} className="border-b border-zinc-100 pb-3 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-[1.1rem] font-semibold tracking-[-0.02em] text-zinc-900">{item.element}</div>
                <div className="mt-1 text-xs uppercase tracking-[0.14em] text-zinc-500" style={monoStyle}>{item.role} / {item.priority}</div>
              </div>
              <div className="text-xs font-semibold text-zinc-500" style={monoStyle}>x{item.count ?? 0}</div>
            </div>
            <div className="mt-2 text-sm leading-relaxed text-zinc-600">{item.reason}</div>
            {item.integrity?.summary ? (
              <div className="mt-2 rounded-sm border border-zinc-100 bg-zinc-50 px-3 py-2 text-[12px] leading-relaxed text-zinc-600">
                {item.integrity.summary}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function damageToneClass(status) {
  if (status === 'damaged') return 'border-rose-200 bg-rose-50 text-rose-800';
  if (status === 'absent') return 'border-amber-200 bg-amber-50 text-amber-800';
  if (status === 'supported') return 'border-teal-200 bg-teal-50 text-teal-800';
  return 'border-zinc-200 bg-zinc-50 text-zinc-700';
}

function DamageAssessmentPanel({ rows }) {
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <Micro>Damaged Useful Check</Micro>
      <div className="mt-4 space-y-3">
        {rows.map((row) => (
          <div key={`${row.element}-${row.role}`} className="border-b border-zinc-100 pb-3 last:border-0 last:pb-0">
            {(() => {
              const channels = Array.isArray(row.damage_channels) ? row.damage_channels : [];
              const rescues = Array.isArray(row.rescue_candidates) ? row.rescue_candidates : [];
              return (
                <>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-zinc-900">{row.element}</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.14em] text-zinc-500" style={monoStyle}>{row.role || '-'} / {row.priority || '-'}</div>
              </div>
              <span className={`rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${damageToneClass(row.status)}`} style={monoStyle}>
                {String(row.status || 'open').replace(/_/g, ' ')}
              </span>
            </div>
            {row.reason ? <div className="mt-2 text-[12px] leading-relaxed text-zinc-600">{row.reason}</div> : null}
            {row.damage_type || row.functional_state ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {row.damage_type ? <Pill>{ruleTokenLabel(row.damage_type)}</Pill> : null}
                {row.functional_state ? <Pill>{ruleTokenLabel(row.functional_state)}</Pill> : null}
              </div>
            ) : null}
            {channels.length ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {channels.slice(0, 3).map((channel) => <Pill key={`${row.element}-${channel.channel}`}>{ruleTokenLabel(channel.channel)}</Pill>)}
              </div>
            ) : null}
            {rescues.length ? (
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {rescues.slice(0, 2).map((rescue) => (
                  <div key={`${row.element}-${rescue.path}-${rescue.element}`} className="rounded-sm border border-teal-100 bg-teal-50/60 px-3 py-2 text-[11px] leading-relaxed text-teal-900">
                    <span className="font-semibold">{rescue.role || 'Rescue'} {rescue.element}</span>
                    {rescue.count !== undefined ? ` x${rescue.count}` : ''}
                  </div>
                ))}
              </div>
            ) : null}
                </>
              );
            })()}
          </div>
        ))}
      </div>
    </div>
  );
}

function SpecialStructurePanel({ screen }) {
  const flags = Array.isArray(screen?.flags) ? screen.flags : [];
  const structureTypes = Array.isArray(screen?.structure_types) ? screen.structure_types : [];
  const primaryStructure = screen?.primary_structure || null;
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <Micro>Special Structure Screen</Micro>
      <div className="mt-2 text-sm text-zinc-500">
        {String(screen?.structure_status || screen?.status || 'screened').replace(/_/g, ' ')}
        {structureTypes.length ? ` / ${structureTypes.map(ruleTokenLabel).join(', ')}` : ''}
      </div>
      {primaryStructure?.type ? (
        <div className="mt-3 rounded-sm border border-amber-100 bg-amber-50 px-3 py-2 text-[12px] leading-relaxed text-amber-900">
          <span className="font-medium">Primary structure:</span> {ruleTokenLabel(primaryStructure.type)}
          {primaryStructure.element ? ` / ${primaryStructure.element}` : ''}
        </div>
      ) : null}
      {flags.length ? (
        <div className="mt-4 space-y-3">
          {flags.map((flag) => (
            <div key={`${flag.type}-${flag.element}`} className="border-l border-amber-300 pl-3 text-sm leading-relaxed text-amber-800">
              {flag.classification ? <span className="font-medium">{ruleTokenLabel(flag.classification)}: </span> : null}
              {flag.reason || flag.type}
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-4 text-sm leading-relaxed text-zinc-600">
          No special-structure flag was raised by the current classifier.
        </div>
      )}
    </div>
  );
}

function ElementIntegrityPanel({ rows, summary }) {
  return (
    <div className="mt-6 rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex flex-col gap-4 border-b border-zinc-100 pb-4 md:flex-row md:items-start md:justify-between">
        <div>
          <Micro>Presence & Pressure</Micro>
          <div className="mt-2 max-w-2xl text-sm leading-relaxed text-zinc-600">
            Favorable elements are checked against natal placements, current timing, and relationship-contact pressure before the app treats them as actionable.
          </div>
        </div>
        <div className="grid min-w-[280px] grid-cols-2 gap-3 text-right sm:grid-cols-4">
          <TimingMetric label="Natal" value={summary?.favorable_present ?? 0} />
          <TimingMetric label="Timing" value={summary?.favorable_timing_supported ?? 0} />
          <TimingMetric label="Missing" value={summary?.favorable_missing ?? 0} />
          <TimingMetric label="Pressed" value={summary?.favorable_pressured ?? 0} />
        </div>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {rows.map((row) => (
          <ElementIntegrityCard key={`${row.role_group}-${row.element}-${row.priority || ''}`} row={row} />
        ))}
      </div>
    </div>
  );
}

function ElementIntegrityCard({ row }) {
  const natalHits = Array.isArray(row?.natal_sources) ? row.natal_sources : [];
  const timingHits = Array.isArray(row?.timing_sources) ? row.timing_sources : [];
  const impacts = Array.isArray(row?.event_impacts) ? row.event_impacts : [];
  const toneClass = row?.pressure === 'pressured'
    ? 'border-rose-200 bg-rose-50 text-rose-800'
    : row?.pressure === 'supported'
      ? 'border-teal-200 bg-teal-50 text-teal-800'
      : 'border-zinc-200 bg-zinc-50 text-zinc-700';
  return (
    <div className="rounded-sm border border-zinc-200 px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[1rem] font-semibold text-zinc-900">{row?.element}</div>
          <div className="mt-1 text-[10px] uppercase tracking-[0.14em] text-zinc-500" style={monoStyle}>
            {integrityRoleLabel(row?.role_group)}{row?.role ? ` / ${row.role}` : ''}
          </div>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${toneClass}`} style={monoStyle}>
          {availabilityLabel(row?.availability)}
        </span>
      </div>
      {row?.summary ? <div className="mt-3 text-sm leading-relaxed text-zinc-600">{row.summary}</div> : null}
      <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-zinc-500">
        {natalHits.slice(0, 3).map((hit) => <span key={`n-${hit.label}`} className="rounded-full border border-zinc-200 px-2 py-1">{hit.label}</span>)}
        {timingHits.slice(0, 2).map((hit) => <span key={`t-${hit.label}`} className="rounded-full border border-teal-200 px-2 py-1 text-teal-700">{hit.label}</span>)}
        {!natalHits.length && !timingHits.length ? <span className="rounded-full border border-zinc-200 px-2 py-1">no active placement</span> : null}
      </div>
      {impacts.length ? (
        <div className="mt-3 space-y-1 border-t border-zinc-100 pt-3 text-[12px] text-zinc-500">
          {impacts.slice(0, 2).map((impact) => (
            <div key={`${impact.label}-${impact.scope}`} className="flex items-center justify-between gap-3">
              <span>{impact.label}</span>
              <span className="shrink-0 uppercase tracking-[0.12em]" style={monoStyle}>{impact.scope_label || impact.scope}</span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function integrityRoleLabel(value) {
  if (value === 'favorable') return 'favorable';
  if (value === 'unfavorable') return 'caution';
  return 'watch';
}

function availabilityLabel(value) {
  if (value === 'present_natal') return 'natal';
  if (value === 'timing_supported') return 'timing';
  if (value === 'missing') return 'missing';
  return 'unknown';
}

function timingPillarText(pillar) {
  return [pillar?.stem, pillar?.branch].filter(Boolean).join(' ') || '-';
}

function timingLayerPeriodLabel(layer) {
  const period = layer?.period || {};
  if (layer?.layer === 'da_yun') return period.age_label || layer?.pillar?.age_label || '10-year period';
  if (layer?.layer === 'liu_nian') return period.bazi_year ? `BaZi year ${period.bazi_year}` : 'current year';
  if (layer?.layer === 'flowing_month') {
    const solarTerm = period.solar_term || {};
    return solarTerm.name || solarTerm.key || (period.calendar_month ? `month ${period.calendar_month}` : 'flowing month');
  }
  if (layer?.layer === 'flowing_day') return period.local_date || 'flowing day';
  if (layer?.layer === 'flowing_hour') return period.hour_branch ? `${period.hour_branch} hour` : 'flowing hour';
  return layer?.label || '-';
}

function timingLayerToneSummary(layers) {
  const counts = (Array.isArray(layers) ? layers : []).reduce((acc, layer) => {
    const tone = layer?.tone || 'quiet';
    acc[tone] = (acc[tone] || 0) + 1;
    return acc;
  }, {});
  if (counts.supportive && counts.pressuring) return 'mixed';
  if (counts.pressuring) return 'pressuring';
  if (counts.supportive) return 'supportive';
  if (counts.mixed) return 'mixed';
  return 'quiet';
}

function timingContactCount(layers) {
  return (Array.isArray(layers) ? layers : []).reduce((sum, layer) => (
    sum + Number(layer?.relationship_summary?.total || 0)
  ), 0);
}

function TimingPillarValue({ pillar }) {
  if (!pillar) return <span className="text-zinc-400">-</span>;
  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <StemValue stem={pillar.stem} element={pillar.stem_element} compact />
      <span className="text-zinc-300">/</span>
      <BranchValue branch={pillar.branch} animal={pillar.animal} element={pillar.branch_element} compact />
    </span>
  );
}

function TimingSummaryCard({ label, value, detail, active = false }) {
  return (
    <div className={`rounded-sm border bg-white p-4 ${active ? 'border-teal-200' : 'border-zinc-200'}`}>
      <Micro className={active ? 'text-teal-700' : ''}>{label}</Micro>
      <div className="mt-2 text-[1rem] font-semibold leading-snug text-zinc-950">{value || '-'}</div>
      {detail ? <div className="mt-2 text-[12px] leading-relaxed text-zinc-500">{detail}</div> : null}
    </div>
  );
}

function TimingSummaryCards({ timing, rhythm, interaction }) {
  const layers = Array.isArray(rhythm?.layers) ? rhythm.layers : [];
  const active = timing?.active_luck_pillar || null;
  const luckPillarsEnabled = Boolean(timing?.luck_pillars_enabled);
  const flow = layers.find((layer) => layer?.layer === 'flowing_month') || layers.find((layer) => String(layer?.layer || '').startsWith('flowing_'));
  const contacts = timingContactCount(layers);
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <TimingSummaryCard
        label="Active Decade"
        value={active ? timingPillarText(active) : (luckPillarsEnabled ? 'not entered' : 'not calculated')}
        detail={active?.age_label || (
          luckPillarsEnabled
            ? 'No current decade is active yet for the reference date.'
            : 'Da Yun requires primary calculation sex; current year, month, day, and hour remain available.'
        )}
        active={Boolean(active)}
      />
      <TimingSummaryCard
        label="Live Flow"
        value={flow ? timingPillarText(flow.pillar) : '-'}
        detail={flow ? `${flow.label || ruleTokenLabel(flow.layer)} / ${ruleTokenLabel(flow.tone || 'quiet')}` : 'Month/day/hour timing is unavailable.'}
      />
      <TimingSummaryCard
        label="Timing Contacts"
        value={`${contacts} contact${contacts === 1 ? '' : 's'}`}
        detail={contacts ? 'Review the layer cards and Relationships tab for placement context.' : 'No timing contacts returned for the current layers.'}
      />
    </div>
  );
}

function TimingBasisRow({ timing }) {
  const annual = timing?.annual_pillar || null;
  return (
    <div className="grid gap-5 md:grid-cols-3">
      <div>
        <Micro>Direction</Micro>
        <div className="mt-2 text-[2rem] font-medium capitalize leading-none tracking-[-0.05em] text-zinc-900" style={serifStyle}>
          {timing?.direction || '-'}
        </div>
        <div className="mt-2 text-sm leading-relaxed text-zinc-500">{timing?.direction_rule || 'Direction rule unavailable.'}</div>
      </div>
      <div>
        <Micro>Start Age</Micro>
        <div className="mt-2 text-[2rem] font-medium leading-none tracking-[-0.05em] text-zinc-900" style={serifStyle}>
          {timing?.start_age_label || '-'}
        </div>
        <div className="mt-2 text-sm text-zinc-500">{timing?.start_date ? `Begins around ${timing.start_date}` : 'Start date unavailable.'}</div>
      </div>
      <div>
        <Micro>Current Year</Micro>
        <div className="mt-2 text-[2rem] font-medium leading-none tracking-[-0.05em] text-teal-700" style={serifStyle}>
          {annual?.stem && annual?.branch ? `${annual.stem} ${annual.branch}` : '-'}
        </div>
        <div className="mt-2 text-sm text-zinc-500">{annual?.bazi_year ? `BaZi year ${annual.bazi_year}` : 'Annual pillar unavailable.'}</div>
      </div>
    </div>
  );
}

function TimingUsefulInteractionPanel({ interaction }) {
  const items = Array.isArray(interaction?.items) ? interaction.items : [];
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Micro>Helpful Element Timing</Micro>
          <div className="mt-2 text-sm leading-relaxed text-zinc-600">
            {interaction?.summary || 'Timing interaction is unavailable for this chart.'}
          </div>
        </div>
        <Pill active={interaction?.status === 'active'}>{ruleTokenLabel(interaction?.status || 'quiet')}</Pill>
      </div>
      {items.length ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {items.map((item) => (
            <div key={`${item.element}-${item.role}-${item.priority}`} className="rounded-sm border border-zinc-100 bg-zinc-50/70 px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-zinc-900">{item.element}</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.14em] text-zinc-500" style={monoStyle}>
                    {item.role || '-'} / {item.priority || '-'}
                  </div>
                </div>
                <span className="rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] text-zinc-600" style={monoStyle}>
                  {ruleTokenLabel(item.status)}
                </span>
              </div>
              {item.summary ? <div className="mt-2 text-[12px] leading-relaxed text-zinc-600">{item.summary}</div> : null}
              {Array.isArray(item.effects) && item.effects.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.effects.map((effect) => (
                    <span key={`${effect.layer}-${effect.placement}-${effect.symbol}`} className="rounded-full border border-teal-200 bg-white px-2 py-1 text-[11px] text-teal-700">
                      {ruleTokenLabel(effect.layer)} {effect.symbol} {ruleTokenLabel(effect.effect)}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function TimingRhythmPanel({ rhythm }) {
  const layers = Array.isArray(rhythm?.layers) ? rhythm.layers : [];
  if (!layers.length) return null;
  const toneSummary = timingLayerToneSummary(layers);
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-3xl">
          <Micro>Current Timing Layers</Micro>
          <div className="mt-2 text-sm leading-relaxed text-zinc-600">
            {rhythm?.summary || 'Timing rhythm is resolved from the current decade, year, month, day, and hour layers.'}
          </div>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <Pill active={toneSummary === 'supportive'}>{ruleTokenLabel(toneSummary)}</Pill>
        </div>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-5 md:grid-cols-2">
        {layers.map((layer) => {
          const pillar = layer?.pillar || {};
          const effects = Array.isArray(layer?.useful_element_effects) ? layer.useful_element_effects : [];
          const interpretiveEffects = Array.isArray(layer?.interpretive_effects) ? layer.interpretive_effects : [];
          const weighting = layer?.layer_weighting || {};
          const relationships = layer?.relationship_summary || {};
          const growth = layer?.growth_stage || {};
          return (
            <div key={`${layer.layer}-${pillar.stem}-${pillar.branch}`} className="rounded-sm border border-zinc-200 bg-white px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <Micro>{layer.label || ruleTokenLabel(layer.layer)}</Micro>
                  <div className="mt-2 text-sm text-zinc-800">
                    <TimingPillarValue pillar={pillar} />
                  </div>
                </div>
                <span className={`rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.1em] ${timingToneClass(layer.tone)}`} style={monoStyle}>
                  {ruleTokenLabel(layer.tone || 'quiet')}
                </span>
              </div>
              <div className="mt-3 grid gap-2 text-[12px] text-zinc-600">
                <div><span className="text-zinc-400">Ten God</span> {layer?.ten_god?.stem || '-'}</div>
                <div><span className="text-zinc-400">Growth</span> {growth?.label || '-'}</div>
                <div><span className="text-zinc-400">Period</span> {timingLayerPeriodLabel(layer)}</div>
                <div><span className="text-zinc-400">Contacts</span> {relationships.total ?? 0}</div>
                <div><span className="text-zinc-400">Weight</span> S{weighting.stem_weight ?? '-'} / B{weighting.branch_weight ?? '-'}</div>
              </div>
              {effects.length ? (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {effects.slice(0, 3).map((effect) => (
                    <span key={`${effect.placement}-${effect.symbol}-${effect.status}`} className="rounded-full border border-teal-200 bg-white px-2 py-1 text-[10px] text-teal-700">
                      {effect.symbol} {ruleTokenLabel(effect.status)}
                    </span>
                  ))}
                </div>
              ) : null}
              {interpretiveEffects.length ? (
                <div className="mt-3 space-y-1.5">
                  {interpretiveEffects.slice(0, 2).map((effect, index) => (
                    <div key={`${effect.kind}-${effect.source}-${index}`} className="rounded-sm border border-zinc-100 bg-zinc-50 px-2 py-1.5 text-[11px] leading-relaxed text-zinc-600">
                      <span className="font-medium text-zinc-900">{titleTokenLabel(effect.kind)}:</span> {ruleTokenLabel(effect.summary || effect.label || effect.source)}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

    </div>
  );
}

function pluralCount(count, singular, plural = `${singular}s`) {
  const numeric = Number(count || 0);
  return `${numeric} ${numeric === 1 ? singular : plural}`;
}

function activationRoleLabel(trigger) {
  return trigger?.activation_role_label || ruleTokenLabel(trigger?.activation_role || 'Timing trigger');
}

function activationOverview(activation, triggers) {
  if (!triggers.length) return activation?.summary || 'Timing activation is quiet for the current reference date.';
  return `${pluralCount(triggers.length, 'timing layer')} activating chart evidence now.`;
}

function activationSummary(trigger) {
  const counts = trigger?.counts || {};
  const hasStructuredCounts = [
    counts.main_position_contacts,
    counts.rescue_arrival_signals,
    counts.pressure_movement_signals,
  ].some((value) => value !== undefined && value !== null);
  if (hasStructuredCounts) {
    return `${activationRoleLabel(trigger)} activates ${pluralCount(counts.main_position_contacts, 'Day or spouse-palace contact')}, brings ${pluralCount(counts.rescue_arrival_signals, 'rescue or arrival signal')}, and adds ${pluralCount(counts.pressure_movement_signals, 'pressure or movement signal')}.`;
  }
  if (!trigger?.summary) return '';
  return String(trigger.summary)
    .replace(/^[a-z_]+\s+[a-z_]+\s*:\s*/i, '')
    .replace(/_/g, ' ')
    .replace(/Day\/spouse-palace/g, 'Day or spouse-palace')
    .replace(/rescue\/arrival/g, 'rescue or arrival')
    .replace(/pressure\/movement/g, 'pressure or movement')
    .replace(/contact\(s\)/g, 'contacts')
    .replace(/signal\(s\)/g, 'signals');
}

function EventActivationPanel({ activation }) {
  const triggers = Array.isArray(activation?.primary_triggers) ? activation.primary_triggers : [];
  if (!triggers.length && activation?.status !== 'active') return null;
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Micro>Event Activation</Micro>
          <div className="mt-2 text-sm leading-relaxed text-zinc-600">
            {activationOverview(activation, triggers)}
          </div>
        </div>
        <Pill active={activation?.status === 'active'}>{ruleTokenLabel(activation?.status || 'quiet')}</Pill>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {triggers.slice(0, 4).map((trigger) => {
          const score = Number(trigger.activation_score || 0);
          const summary = activationSummary(trigger);
          return (
            <div key={`${trigger.layer}-${trigger.status}-${trigger.activation_score}`} className="rounded-sm border border-zinc-100 bg-zinc-50/70 px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-zinc-900">{trigger.label || ruleTokenLabel(trigger.layer)}</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.14em] text-zinc-500" style={monoStyle}>
                    {activationRoleLabel(trigger)}{score ? ` - Activation Score ${score}` : ''}
                  </div>
                </div>
                <Pill active={trigger.main_position_linked}>{trigger.main_position_linked ? 'Day Palace' : (trigger.status_label || ruleTokenLabel(trigger.status))}</Pill>
              </div>
              {summary ? <div className="mt-2 text-[12px] leading-relaxed text-zinc-600">{summary}</div> : null}
            </div>
          );
        })}
      </div>
      {activation?.spouse_timing ? (
        <div className="mt-4 rounded-sm border border-zinc-100 bg-white px-4 py-3 text-[12px] leading-relaxed text-zinc-600">
          <span className="font-semibold text-zinc-900">Spouse timing:</span> {activation.spouse_timing.summary || ruleTokenLabel(activation.spouse_timing.status)}
        </div>
      ) : null}
    </div>
  );
}

function timingToneClass(value) {
  if (value === 'supportive') return 'border-teal-200 bg-teal-50 text-teal-800';
  if (value === 'pressuring') return 'border-rose-200 bg-rose-50 text-rose-800';
  if (value === 'mixed') return 'border-amber-200 bg-amber-50 text-amber-800';
  return 'border-zinc-200 bg-white text-zinc-600';
}

function TimingPanel({ data }) {
  const timing = data?.timing || {};
  const missingInputs = Array.isArray(data?.missing_inputs) ? data.missing_inputs : [];
  const needsCalculationSex = missingInputs.some((item) => item?.field === 'calculation_sex');
  const luckPillars = Array.isArray(timing?.luck_pillars) ? timing.luck_pillars : [];
  const active = timing?.active_luck_pillar;
  const timingInteraction = timing?.useful_element_interaction || data?.useful_elements?.timing_interaction || {};
  const rhythm = timing?.rhythm || {};
  const eventActivation = rhythm?.event_activation || {};

  return (
    <MemoSection
      number="X"
      title="Life Timing"
      subtitle="Decade, year, month, day, and hour layers show when the natal chart receives support, pressure, or relationship contact."
    >
      {needsCalculationSex ? (
        <StatePanel
          tone="warn"
          title="Choose calculation sex for Luck Pillars."
          body="Set Primary Calculation Sex in the controls above before generating the Da Yun decade sequence. Current year, month, day, and hour layers remain available."
        />
      ) : null}

      {!needsCalculationSex && !timing?.luck_pillars_enabled ? (
        <StatePanel
          title="Da Yun is not calculated."
          body="Set Primary Calculation Sex in the controls above to generate the decade sequence. The current flow layers below do not require it."
        />
      ) : null}

      <div className="space-y-8">
          {timing?.luck_pillars_enabled ? <TimingBasisRow timing={timing} /> : null}

          <TimingSummaryCards timing={timing} rhythm={rhythm} interaction={timingInteraction} />

          {timing?.luck_pillars_enabled && active ? (
            <div className="border-y border-zinc-200 py-5">
              <div className="grid gap-6 lg:grid-cols-[180px_minmax(0,1fr)]">
                <div>
                  <Micro>Active Luck Pillar</Micro>
                  <div className="mt-2 text-[3.2rem] font-medium leading-none tracking-[-0.06em] text-teal-700" style={serifStyle}>
                    {active.stem} {active.branch}
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  <TimingMetric label="Age Range" value={active.age_label} />
                  <TimingMetric label="Calendar" value={`${active.calendar_start_year} - ${active.calendar_end_year}`} />
                  <TimingMetric label="Ten God" value={active.ten_god || '-'} />
                </div>
              </div>
            </div>
          ) : null}

          <TimingRhythmPanel rhythm={rhythm} />

          <EventActivationPanel activation={eventActivation} />

          <TimingUsefulInteractionPanel interaction={timingInteraction} />

          {timing?.luck_pillars_enabled ? (
            <div>
            <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
              <div>
                <Micro>Decade Sequence</Micro>
                <div className="mt-1 text-sm leading-relaxed text-zinc-500">
                  Each row is one 10-year Luck Pillar; the active decade is highlighted when the reference date has entered it.
                </div>
              </div>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              {luckPillars.map((pillar) => (
                <div
                  key={`${pillar.sequence}-${pillar.stem}-${pillar.branch}`}
                  className={`rounded-sm border px-4 py-3 ${
                    pillar.active ? 'border-teal-300 bg-teal-50/70' : 'border-zinc-200 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <Micro>{`Decade ${pillar.sequence}`}</Micro>
                      <div className="mt-2 text-sm text-zinc-800">
                        <TimingPillarValue pillar={pillar} />
                      </div>
                      <div className="mt-2 text-sm text-zinc-500">{pillar.age_label} / {pillar.calendar_start_year}-{pillar.calendar_end_year}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-zinc-900">{pillar.ten_god || '-'}</div>
                      <div className="mt-1 text-xs text-zinc-500">{pillar.stem_element} / {pillar.animal}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            </div>
          ) : null}

          {SHOW_DEV_METHOD_SURFACE && timing?.luck_pillars_enabled && timing?.debug ? (
            <details className="border-t border-zinc-200 pt-4">
              <summary className="cursor-pointer list-none text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-600" style={monoStyle}>
                Timing calculation details
              </summary>
              <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
                <DebugItem label="Solar Term" value={timing.debug.solar_term?.name || '-'} />
                <DebugItem label="Distance Days" value={timing.debug.distance_days ?? '-'} />
                <DebugItem label="Year Stem" value={`${timing.debug.year_stem || '-'} / ${timing.debug.year_stem_polarity || '-'}`} />
                <DebugItem label="Polarity Source" value={`${timing.debug.polarity_source || '-'} / ${timing.debug.selected_polarity || '-'}`} />
                <DebugItem label="Direction Rule" value={timing.debug.direction_rule_key || timing.direction_rule_key || '-'} />
                <DebugItem label="Method" value={timing.debug.method || '-'} />
              </dl>
            </details>
          ) : null}
      </div>
    </MemoSection>
  );
}

function TimingMetric({ label, value }) {
  const displayValue = value === 0 ? 0 : (value || '-');
  return (
    <div>
      <Micro>{label}</Micro>
      <div className="mt-2 text-[1.35rem] font-medium leading-none tracking-[-0.04em] text-zinc-900" style={serifStyle}>{displayValue}</div>
    </div>
  );
}

function OracleLineVisual({ visual = 'broken', moving = false }) {
  const solid = visual === 'solid';
  const fill = moving ? 'bg-teal-700' : 'bg-zinc-900';
  return (
    <div className="flex h-6 items-center gap-2">
      {solid ? (
        <span className={`h-2 w-24 rounded-sm ${fill}`} />
      ) : (
        <>
          <span className={`h-2 w-10 rounded-sm ${fill}`} />
          <span className={`h-2 w-10 rounded-sm ${fill}`} />
        </>
      )}
    </div>
  );
}

function HexagramLineStack({ lines, hexagram = null, resulting = false }) {
  const structuralRows = Array.isArray(hexagram?.line_visuals_bottom_to_top)
    ? hexagram.line_visuals_bottom_to_top.map((visual, index) => ({
      position: index + 1,
      label: visual,
      visual,
      resulting_label: visual,
      resulting_visual: visual,
      moving: false,
    }))
    : [];
  const rows = Array.isArray(lines) && lines.length ? [...lines].reverse() : [...structuralRows].reverse();
  if (!rows.length) return null;
  return (
    <div className="rounded-sm border border-zinc-100 bg-zinc-50/80 p-3">
      <div className="space-y-1">
        {rows.map((line) => {
          const visual = resulting ? line.resulting_visual : line.visual;
          const label = resulting ? line.resulting_label : line.label;
          return (
            <div key={`${resulting ? 'resulting' : 'primary'}-${line.position}`} className="grid grid-cols-[28px_112px_minmax(0,1fr)] items-center gap-2">
              <span className="text-[10px] text-zinc-400" style={monoStyle}>{line.position}</span>
              <OracleLineVisual visual={visual} moving={!resulting && line.moving} />
              <span className={`truncate text-[11px] ${line.moving && !resulting ? 'font-semibold text-teal-700' : 'text-zinc-500'}`}>
                {label}{line.moving && !resulting ? ' / changing' : ''}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function HexagramCard({ title, hexagram, lines, resulting = false, structureOnly = false }) {
  if (!hexagram) return null;
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Micro>{title}</Micro>
          <h5 className="mt-2 text-lg font-semibold text-zinc-950">
            {hexagram.number}. {hexagram.title}
          </h5>
          <div className="mt-1 text-sm text-zinc-500">{hexagram.pinyin}</div>
        </div>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1fr)]">
        <HexagramLineStack lines={structureOnly ? null : lines} hexagram={hexagram} resulting={resulting} />
        <div className="text-sm leading-relaxed text-zinc-600">
          <div className="grid gap-3 sm:grid-cols-2">
            <TimingMetric label="Upper" value={`${hexagram.upper_trigram?.name || '-'} / ${hexagram.upper_trigram?.image || '-'}`} />
            <TimingMetric label="Lower" value={`${hexagram.lower_trigram?.name || '-'} / ${hexagram.lower_trigram?.image || '-'}`} />
          </div>
          {hexagram.theme ? <p className="mt-4">{hexagram.theme}</p> : null}
          {hexagram.counsel ? <p className="mt-3 text-zinc-800">{hexagram.counsel}</p> : null}
          {Array.isArray(hexagram.keywords) && hexagram.keywords.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {hexagram.keywords.slice(0, 5).map((keyword) => <Pill key={keyword}>{keyword}</Pill>)}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function IChingOraclePanel({
  question,
  onQuestionChange,
  method,
  onMethodChange,
  coinValueScheme,
  onCoinValueSchemeChange,
  manualLines,
  onManualLineChange,
  onCast,
  loading,
  error,
  oracle,
}) {
  const movingFocus = Array.isArray(oracle?.moving_line_focus) ? oracle.moving_line_focus : [];
  const readingPolicy = oracle?.reading?.policy || null;
  return (
    <MemoSection
      number="XI"
      title="I Ching Oracle"
      subtitle="Standalone casting with primary, relating, and nuclear hexagram context."
    >
      <div className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.35fr)]">
        <div className="rounded-sm border border-zinc-200 bg-white p-5">
          <div className="grid gap-4">
            <Field label="question">
              <textarea
                aria-label="Oracle question"
                value={question}
                onChange={(event) => onQuestionChange(event.target.value)}
                rows={4}
                className="mt-2 w-full resize-none border-b border-zinc-200 bg-white pb-2 text-sm text-zinc-800 outline-none transition focus:border-teal-500"
              />
            </Field>
            <SegmentGroup label="cast mode" value={method} onChange={onMethodChange} options={ORACLE_METHOD_OPTIONS} />
            {method === 'coins' ? (
              <SegmentGroup label="coin values" value={coinValueScheme} onChange={onCoinValueSchemeChange} options={ORACLE_COIN_SCHEME_OPTIONS} />
            ) : null}
            {method === 'manual' ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {manualLines.map((value, index) => (
                  <Field key={`oracle-line-${index}`} label={`line ${index + 1}`}>
                    <select
                      aria-label={`Oracle line ${index + 1}`}
                      value={value}
                      onChange={(event) => onManualLineChange(index, Number(event.target.value))}
                      className={underlineControlClass}
                    >
                      {ORACLE_LINE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </Field>
                ))}
              </div>
            ) : null}
            <button
              type="button"
              onClick={onCast}
              disabled={loading}
              className={`justify-self-start ${primaryActionClass}`}
              style={monoStyle}
            >
              {loading ? 'Casting' : 'Cast Oracle'}
            </button>
          </div>
          {error ? (
            <div className="mt-4 rounded-sm border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
          ) : null}
        </div>

        <div className="space-y-5">
          {loading ? <StatePanel title="Casting Oracle" body="Resolving lines, hexagrams, and reading focus." /> : null}
          {!loading && !oracle ? <EmptyPanel title="No Oracle cast yet" body="" /> : null}
          {oracle ? (
            <>
              <div className="rounded-sm border border-zinc-200 bg-white p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <Micro>Oracle Reading</Micro>
                    {oracle.question ? <div className="mt-2 text-sm font-semibold text-zinc-950">{oracle.question}</div> : null}
                  </div>
                  {Array.isArray(oracle.changing_lines) && oracle.changing_lines.length ? (
                    <Pill active>Changing {oracle.changing_lines.join(', ')}</Pill>
                  ) : (
                    <Pill>No Changing Lines</Pill>
                  )}
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <TimingMetric label="Cast" value={ruleTokenLabel(oracle.casting_method || '-')} />
                  <TimingMetric label="Cast Input" value={ruleTokenLabel(oracle.cast_source || '-')} />
                  <TimingMetric label="Randomness" value={ruleTokenLabel(oracle.random_model || 'none')} />
                </div>
                {oracle.reading?.summary ? <p className="mt-4 text-sm leading-relaxed text-zinc-700">{oracle.reading.summary}</p> : null}
                {readingPolicy ? (
                  <div className="mt-4 rounded-sm border border-zinc-200 bg-zinc-50/70 p-4">
                    <Micro>Reading Focus</Micro>
                    <div className="mt-2 text-sm font-semibold text-zinc-950">{readingPolicy.label || 'Changing-line policy'}</div>
                    {readingPolicy.summary ? <p className="mt-2 text-[12px] leading-relaxed text-zinc-600">{readingPolicy.summary}</p> : null}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Pill>{ruleTokenLabel(readingPolicy.focus || 'focus')}</Pill>
                      {Array.isArray(readingPolicy.selected_lines) && readingPolicy.selected_lines.length ? (
                        <Pill>Lines {readingPolicy.selected_lines.join(', ')}</Pill>
                      ) : null}
                    </div>
                  </div>
                ) : null}
                {movingFocus.length ? (
                  <div className="mt-4 space-y-2">
                    {movingFocus.map((item) => (
                      <div key={item.position} className="border-l border-teal-300 pl-3 text-[12px] leading-relaxed text-zinc-600">
                        <span className="font-semibold text-zinc-900">Line {item.position}: </span>{item.transition} / {item.focus}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
              <HexagramCard title="Primary Hexagram" hexagram={oracle.primary} lines={oracle.lines} />
              {oracle.relating ? <HexagramCard title="Relating Hexagram" hexagram={oracle.relating} lines={oracle.lines} resulting /> : null}
              <HexagramCard title="Nuclear Hexagram" hexagram={oracle.nuclear} lines={oracle.lines} structureOnly />
            </>
          ) : null}
        </div>
      </div>
    </MemoSection>
  );
}

function NotesPanel({ data }) {
  const missingInputs = Array.isArray(data?.missing_inputs) ? data.missing_inputs : [];
  const warnings = Array.isArray(data?.debug?.warnings) ? data.debug.warnings : [];
  return (
    <MemoSection
      number="XII"
      title="Method Notes"
      subtitle="Calculation assumptions and reading boundaries for this profile."
    >
      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <Micro>Inputs</Micro>
          <div className="mt-3 space-y-3 text-sm leading-relaxed text-zinc-600">
            {missingInputs.length ? missingInputs.map((item) => (
              <div key={item.field || item.message} className="border-l border-amber-300 pl-3 text-amber-800">{item.message || item.field}</div>
            )) : <div>No required BaZi inputs are missing for the current chart layer.</div>}
            {warnings.length ? warnings.map((warning) => (
              <div key={warning} className="border-l border-zinc-300 pl-3">{warning}</div>
            )) : null}
          </div>
        </div>
        <div>
          <Micro>Reading Boundaries</Micro>
          <div className="mt-3 space-y-3 text-sm leading-relaxed text-zinc-600">
            <div>Final Yong Shen is released only when strength, damage, timing, and special-structure checks agree clearly.</div>
            <div>Climate and damaged-useful checks can change the decision path, but blocked families stay visibly withheld.</div>
            <div>True solar hour, true-solar day boundary, late-Zi day shifting, and Luck Direction variants are selectable calculation modes.</div>
            <div>Palace context locates where a symbol operates; it does not turn relationship contacts into fixed predictions.</div>
            <div>Animal labels are shown as branch metadata; the profile stays centered on pillars, elements, Ten Gods, and timing.</div>
          </div>
        </div>
      </div>
    </MemoSection>
  );
}

function DebugPanel({ data }) {
  const debug = data?.debug || {};
  const birth = data?.birth || {};
  const trueSolar = birth?.true_solar_time || debug?.true_solar_time || {};
  const comparison = debug?.hour_pillar_comparison || {};
  const dayComparison = debug?.day_pillar_comparison || {};
  const options = debug?.calculation_options || birth?.calculation_options || {};
  const civilHour = comparison?.civil;
  const solarHour = comparison?.true_solar;
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Micro>Provenance</Micro>
      </div>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <DebugItem label="Source" value={debug.snap_source || 'direct_input'} />
        <DebugItem label="Snap" value={data?.snap_label || data?.source_snap_id || '-'} />
        <DebugItem label="Local Time" value={birth.local_datetime || '-'} />
        <DebugItem label="Timezone" value={birth.timezone || '-'} />
        <DebugItem label="Year Boundary" value={debug.solar_year_boundary?.name || '-'} />
        <DebugItem label="Month Term" value={debug.month_solar_term?.name || '-'} />
        <DebugItem label="Solar Source" value={debug.solar_term_source || '-'} />
        <DebugItem label="Hour Rule" value={debug.hour_rule || '-'} />
        <DebugItem label="Hour Mode" value={comparison.mode || '-'} />
        <DebugItem label="Day Boundary" value={options.day_boundary_rule || debug.day_boundary_rule || '-'} />
        <DebugItem label="Zi Variant" value={options.hour_pillar_variant || debug.hour_pillar_variant || '-'} />
        <DebugItem label="Luck Rule" value={options.luck_direction_rule || debug.luck_direction_rule || '-'} />
        <DebugItem
          label="True Solar Time"
          value={trueSolar?.local_datetime ? `${trueSolar.local_datetime} / ${trueSolar.total_correction_minutes} min` : '-'}
        />
        <DebugItem
          label="Day Comparison"
          value={dayComparison?.selected ? `${dayComparison.civil?.stem || '-'} ${dayComparison.civil?.branch || '-'} -> ${dayComparison.selected?.stem || '-'} ${dayComparison.selected?.branch || '-'}${dayComparison.changed ? ' changed' : ' same'}` : '-'}
        />
        <DebugItem
          label="Hour Comparison"
          value={civilHour && solarHour ? `${civilHour.stem} ${civilHour.branch} -> ${solarHour.stem} ${solarHour.branch}${comparison.changed ? ' changed' : ' same'}` : '-'}
        />
      </dl>
      {Array.isArray(debug.warnings) && debug.warnings.length ? (
        <div className="mt-4 rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {debug.warnings.join(' ')}
        </div>
      ) : null}
    </div>
  );
}

function DebugItem({ label, value }) {
  return (
    <div>
      <dt><Micro>{label}</Micro></dt>
      <dd className="mt-1 break-words text-zinc-800">{value}</dd>
    </div>
  );
}

export default function ChineseAstrologyPage({
  setCurrentView,
  onClose,
  snaps: externalSnaps = [],
  activeSnapId = '',
  loadingSnaps: externalLoadingSnaps = false,
  snapsLoaded: externalSnapsLoaded = false,
  onRefreshSnaps,
}) {
  const initialPreferences = useMemo(() => readPreferences(), []);
  const [snaps, setSnaps] = useState(() => (Array.isArray(externalSnaps) ? externalSnaps : []));
  const [snapsLoaded, setSnapsLoaded] = useState(() => Boolean(
    externalSnapsLoaded || (Array.isArray(externalSnaps) && externalSnaps.length),
  ));
  const [loadingSnaps, setLoadingSnaps] = useState(false);
  const [selectedSnapId, setSelectedSnapId] = useState(() => (activeSnapId ? String(activeSnapId) : String(initialPreferences.selectedSnapId || '')));
  const [comparisonSnapId, setComparisonSnapId] = useState(() => String(initialPreferences.comparisonSnapId || ''));
  const [sourceMode, setSourceMode] = useState(() => (initialPreferences.sourceMode === 'manual' ? 'manual' : 'snap'));
  const [activeTab, setActiveTab] = useState(() => normalizeChineseAstrologyTabId(initialPreferences.activeTab));
  const [data, setData] = useState(null);
  const [compatibilityData, setCompatibilityData] = useState(null);
  const [compatibilityProfiles, setCompatibilityProfiles] = useState(null);
  const [compatibilityLoading, setCompatibilityLoading] = useState(false);
  const [compatibilityError, setCompatibilityError] = useState('');
  const [oracleQuestion, setOracleQuestion] = useState('');
  const [oracleMethod, setOracleMethod] = useState('coins');
  const [oracleCoinValueScheme, setOracleCoinValueScheme] = useState('heads_2_tails_3');
  const [oracleManualLines, setOracleManualLines] = useState(DEFAULT_ORACLE_LINES);
  const [oracleData, setOracleData] = useState(null);
  const [oracleLoading, setOracleLoading] = useState(false);
  const [oracleError, setOracleError] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [calculationSex, setCalculationSex] = useState(() => normalizeCalculationSex(initialPreferences.calculationSex));
  const [relationshipCalculationSex, setRelationshipCalculationSex] = useState(
    () => normalizeCalculationSex(initialPreferences.relationshipCalculationSex),
  );
  const [useTrueSolarTime, setUseTrueSolarTime] = useState(() => Boolean(initialPreferences.useTrueSolarTime));
  const [dayBoundaryRule, setDayBoundaryRule] = useState(() => (
    initialPreferences.dayBoundaryRule === 'true_solar_midnight' ? 'true_solar_midnight' : 'civil_midnight'
  ));
  const [hourPillarVariant, setHourPillarVariant] = useState(() => (
    initialPreferences.hourPillarVariant === 'late_zi_next_day' ? 'late_zi_next_day' : 'standard_zi_hour'
  ));
  const [luckDirectionRule, setLuckDirectionRule] = useState(() => {
    const value = String(initialPreferences.luckDirectionRule || '');
    return LUCK_DIRECTION_OPTIONS.some((option) => option.value === value) ? value : 'year_stem_polarity';
  });
  const [relationshipContext, setRelationshipContext] = useState(() => normalizeRelationshipContext(initialPreferences.relationshipContext));
  const [savedReadings, setSavedReadings] = useState(() => readSavedReadingSnapshots());
  const [showHistory, setShowHistory] = useState(false);
  const [copyStatus, setCopyStatus] = useState('');
  const [manual, setManual] = useState({
    date: '',
    time: '',
    location: '',
    timezone: '',
    latitude: '',
    longitude: '',
  });
  const calculationSexControlValue = calculationSex || 'unset';
  const handleCalculationSexChange = useCallback((value) => {
    setCalculationSex(value === 'unset' ? '' : normalizeCalculationSex(value));
  }, []);

  const snapOptions = useMemo(() => (Array.isArray(snaps) ? snaps.filter((snap) => snap?.id) : []), [snaps]);
  const selectedSnap = useMemo(
    () => snapOptions.find((snap) => String(snap?.id || '') === String(selectedSnapId || '')) || null,
    [snapOptions, selectedSnapId],
  );
  const effectiveLoadingSnaps = loadingSnaps || externalLoadingSnaps;
  const sameComparisonSnap = Boolean(
    sourceMode === 'snap'
      && selectedSnapId
      && comparisonSnapId
      && String(selectedSnapId) === String(comparisonSnapId),
  );
  const comparisonReady = Boolean(
    sourceMode === 'snap'
      && selectedSnapId
      && comparisonSnapId
      && !sameComparisonSnap,
  );

  const loadSnaps = useCallback(async () => {
    setLoadingSnaps(true);
    try {
      if (typeof onRefreshSnaps === 'function') {
        const refreshed = await onRefreshSnaps({ silent: true });
        const refreshedItems = Array.isArray(refreshed?.items)
          ? refreshed.items
          : (Array.isArray(refreshed) ? refreshed : null);
        if (refreshedItems) {
          setSnaps(refreshedItems);
          setSnapsLoaded(true);
          setSelectedSnapId((current) => current || (refreshedItems.length ? String(refreshedItems[0].id || '') : ''));
          if (refreshedItems.length) setSourceMode('snap');
          return;
        }
      }
      const res = await AstroClockAPI.listSnaps();
      const items = res?.success ? (res.items || []) : [];
      setSnaps(items);
      setSnapsLoaded(true);
      setSelectedSnapId((current) => current || (items.length ? String(items[0].id || '') : ''));
      if (items.length) setSourceMode('snap');
    } catch (err) {
      setError(String(err?.message || 'Failed to load saved snaps.'));
    } finally {
      setLoadingSnaps(false);
    }
  }, [onRefreshSnaps]);

  const runBazi = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const request = sourceMode === 'snap'
        ? {
            snapId: selectedSnapId,
            calculationSex: calculationSex || undefined,
            includeLuckPillars: true,
            useTrueSolarTime,
            dayBoundaryRule,
            hourPillarVariant,
            luckDirectionRule,
          }
        : {
            date: manual.date,
            time: manual.time,
            location: manual.location,
            timezone: manual.timezone,
            latitude: manual.latitude || undefined,
            longitude: manual.longitude || undefined,
            calculationSex: calculationSex || undefined,
            includeLuckPillars: true,
            useTrueSolarTime,
            dayBoundaryRule,
            hourPillarVariant,
            luckDirectionRule,
          };
      const res = await AstroClockAPI.getChineseAstrologyBazi(request);
      setData(res?.data || null);
    } catch (err) {
      setData(null);
      setError(String(err?.message || 'Failed to calculate BaZi chart.'));
    } finally {
      setLoading(false);
    }
  }, [
    calculationSex,
    dayBoundaryRule,
    hourPillarVariant,
    luckDirectionRule,
    manual.date,
    manual.latitude,
    manual.location,
    manual.longitude,
    manual.time,
    manual.timezone,
    selectedSnapId,
    sourceMode,
    useTrueSolarTime,
  ]);

  const runCompatibility = useCallback(async () => {
    if (!comparisonReady) return;
    setCompatibilityLoading(true);
    setCompatibilityError('');
    try {
      const res = await AstroClockAPI.getChineseAstrologyCompatibility({
        primarySnapId: selectedSnapId,
        relationshipSnapId: comparisonSnapId,
        relationshipContext,
        primaryCalculationSex: calculationSex || undefined,
        relationshipCalculationSex: relationshipCalculationSex || undefined,
        includeLuckPillars: true,
        useTrueSolarTime,
        dayBoundaryRule,
        hourPillarVariant,
        luckDirectionRule,
      });
      const responseData = res?.data || {};
      setCompatibilityData(responseData.compatibility || null);
      setCompatibilityProfiles({
        primary: responseData.primary || null,
        relationship: responseData.relationship || null,
      });
    } catch (err) {
      setCompatibilityData(null);
      setCompatibilityProfiles(null);
      setCompatibilityError(String(err?.message || 'Failed to calculate BaZi compatibility.'));
    } finally {
      setCompatibilityLoading(false);
    }
  }, [calculationSex, comparisonReady, comparisonSnapId, dayBoundaryRule, hourPillarVariant, luckDirectionRule, relationshipCalculationSex, relationshipContext, selectedSnapId, useTrueSolarTime]);

  const handleOracleLineChange = useCallback((index, value) => {
    setOracleManualLines((current) => current.map((line, lineIndex) => (lineIndex === index ? value : line)));
  }, []);

  const runOracle = useCallback(async () => {
    setOracleLoading(true);
    setOracleError('');
    try {
      const res = await AstroClockAPI.getChineseAstrologyIChingOracle({
        question: oracleQuestion,
        method: oracleMethod,
        lines: oracleMethod === 'manual' ? oracleManualLines : undefined,
        coinValueScheme: oracleCoinValueScheme,
      });
      setOracleData(res?.data?.oracle || null);
    } catch (err) {
      setOracleData(null);
      setOracleError(String(err?.message || 'Failed to cast I Ching Oracle.'));
    } finally {
      setOracleLoading(false);
    }
  }, [oracleCoinValueScheme, oracleManualLines, oracleMethod, oracleQuestion]);

  useEffect(() => {
    if (!Array.isArray(externalSnaps)) return;
    setSnaps(externalSnaps);
    if (externalSnapsLoaded || externalSnaps.length) {
      setSnapsLoaded(Boolean(externalSnapsLoaded || externalSnaps.length));
    }
  }, [externalSnaps, externalSnapsLoaded]);

  useEffect(() => {
    if (activeSnapId) {
      setSelectedSnapId(String(activeSnapId));
      setSourceMode('snap');
    }
  }, [activeSnapId]);

  useEffect(() => {
    if (!activeSnapId && !selectedSnapId && snapOptions.length) {
      setSelectedSnapId(String(snapOptions[0].id || ''));
      setSourceMode('snap');
    }
    if (!activeSnapId && selectedSnapId && snapOptions.length && !snapOptions.some((snap) => String(snap?.id || '') === String(selectedSnapId))) {
      setSelectedSnapId(String(snapOptions[0].id || ''));
    }
  }, [activeSnapId, selectedSnapId, snapOptions]);

  useEffect(() => {
    if (!comparisonSnapId) return;
    if (!snapOptions.some((snap) => String(snap?.id || '') === String(comparisonSnapId))) {
      setComparisonSnapId('');
    }
  }, [comparisonSnapId, snapOptions]);

  useEffect(() => {
    if (snapsLoaded || snapOptions.length || effectiveLoadingSnaps) return;
    loadSnaps();
  }, [effectiveLoadingSnaps, loadSnaps, snapOptions.length, snapsLoaded]);

  useEffect(() => {
    writePreferences({
      activeTab,
      calculationSex,
      comparisonSnapId,
      dayBoundaryRule,
      hourPillarVariant,
      luckDirectionRule,
      relationshipCalculationSex,
      relationshipContext,
      selectedSnapId,
      sourceMode,
      useTrueSolarTime,
    });
  }, [activeTab, calculationSex, comparisonSnapId, dayBoundaryRule, hourPillarVariant, luckDirectionRule, relationshipCalculationSex, relationshipContext, selectedSnapId, sourceMode, useTrueSolarTime]);

  useEffect(() => {
    if (sourceMode === 'snap' && selectedSnapId) {
      runBazi();
    }
  }, [runBazi, selectedSnapId, sourceMode]);

  useEffect(() => {
    if (comparisonReady) {
      runCompatibility();
      return;
    }
    setCompatibilityData(null);
    setCompatibilityProfiles(null);
    setCompatibilityError('');
    setCompatibilityLoading(false);
  }, [comparisonReady, runCompatibility]);

  const canRunManual = Boolean(manual.date);
  const handleBack = typeof onClose === 'function'
    ? onClose
    : () => setCurrentView?.('dashboard');
  const promptItems = useMemo(() => {
    const prompts = [];
    if (sourceMode === 'manual') {
      if (!manual.date) prompts.push({ field: 'date', message: 'Birth date is required before a manual BaZi profile can be calculated.' });
      if (!manual.time) prompts.push({ field: 'time', message: 'Birth time is empty; the backend will withhold hour-derived interpretation if time precision is unknown.' });
      if (!manual.timezone && !manual.location) prompts.push({ field: 'timezone', message: 'Add a timezone or location so the local civil chart can be resolved reliably.' });
      if (useTrueSolarTime && !manual.longitude) prompts.push({ field: 'longitude', message: 'True solar hour mode needs longitude; add longitude or use a saved snap with coordinates.' });
      if (dayBoundaryRule === 'true_solar_midnight' && !manual.longitude) prompts.push({ field: 'longitude', message: 'Solar day-boundary mode needs longitude before it can shift the Day Pillar.' });
    }
    if (sourceMode === 'snap') {
      if (!selectedSnapId) prompts.push({ field: 'snap_id', message: 'Select a primary saved snap to calculate the BaZi profile.' });
      if (useTrueSolarTime && selectedSnap && !snapHasLongitude(selectedSnap)) {
        prompts.push({ field: 'longitude', message: 'True solar hour mode needs longitude; this saved snap does not expose one.' });
      }
      if (dayBoundaryRule === 'true_solar_midnight' && selectedSnap && !snapHasLongitude(selectedSnap)) {
        prompts.push({ field: 'longitude', message: 'Solar day-boundary mode needs longitude; this saved snap does not expose one.' });
      }
      if (sameComparisonSnap) prompts.push({ field: 'relationship_snap_id', message: 'Choose two different saved snaps for pair compatibility.' });
      if (comparisonSnapId && !relationshipCalculationSex) {
        prompts.push({
          field: 'relationship_calculation_sex',
          message: "Choose relationship calculation sex to add the comparison chart's Da Yun and spouse-star context; structural pair comparison remains available without it.",
        });
      }
    }
    if (!calculationSex) prompts.push({ field: 'calculation_sex', message: "Choose primary calculation sex when you want the primary chart's Da Yun and spouse-star context." });
    (Array.isArray(data?.missing_inputs) ? data.missing_inputs : []).forEach((item) => prompts.push(item));
    return prompts;
  }, [
    calculationSex,
    comparisonSnapId,
    data?.missing_inputs,
    dayBoundaryRule,
    manual.date,
    manual.location,
    manual.longitude,
    manual.time,
    manual.timezone,
    relationshipCalculationSex,
    sameComparisonSnap,
    selectedSnap,
    selectedSnapId,
    sourceMode,
    useTrueSolarTime,
  ]);
  const handleCopyReading = useCallback(async () => {
    const text = activeTab === 'oracle' && oracleData
      ? buildOracleText(oracleData)
      : buildReadingText(data, compatibilityData);
    if (!text) return;
    try {
      await copyText(text);
      setCopyStatus('Copied');
    } catch (_) {
      setCopyStatus('Copy failed');
    }
    window.setTimeout?.(() => setCopyStatus(''), 1800);
  }, [activeTab, compatibilityData, data, oracleData]);
  const handleExportJson = useCallback(() => {
    if (!data && !oracleData) return;
    const oracleOnly = activeTab === 'oracle' && oracleData && !data;
    const labelSource = oracleOnly
      ? `iching-oracle-${oracleData.primary?.number || 'cast'}`
      : (data.snap_label || data.source_snap_id || 'bazi-profile');
    const label = String(labelSource)
      .replace(/[^a-z0-9_-]+/gi, '-')
      .replace(/^-+|-+$/g, '')
      .toLowerCase() || (oracleOnly ? 'iching-oracle' : 'bazi-profile');
    const ok = downloadJson(`${oracleOnly ? 'iching-oracle' : 'chinese-astrology'}-${label}.json`, {
      profile: data || null,
      compatibility: compatibilityData || null,
      compatibility_profiles: compatibilityProfiles || null,
      oracle: oracleData || null,
      exported_at: new Date().toISOString(),
    });
    setCopyStatus(ok ? 'Exported' : 'Export failed');
    window.setTimeout?.(() => setCopyStatus(''), 1800);
  }, [activeTab, compatibilityData, compatibilityProfiles, data, oracleData]);
  const handleSaveReading = useCallback(() => {
    if (!data) return;
    const ok = saveReadingSnapshot({
      profile: data,
      compatibility: compatibilityData || null,
      compatibility_profiles: compatibilityProfiles || null,
    });
    if (ok) {
      setSavedReadings(readSavedReadingSnapshots());
      setShowHistory(true);
    }
    setCopyStatus(ok ? 'Saved' : 'Save failed');
    window.setTimeout?.(() => setCopyStatus(''), 1800);
  }, [compatibilityData, compatibilityProfiles, data]);
  const handleOpenSavedReading = useCallback((row) => {
    const payload = row?.payload || {};
    if (!payload.profile) return;
    const profiles = payload.compatibility_profiles || null;
    const profileBirth = payload.profile?.birth || {};
    const primaryProfileBirth = profiles?.primary?.birth || {};
    const relationshipProfileBirth = profiles?.relationship?.birth || {};
    const calculationOptions = profileBirth.calculation_options || payload.profile?.debug?.calculation_options || {};
    setData(payload.profile);
    setCompatibilityData(payload.compatibility || null);
    setCompatibilityProfiles(profiles);
    setCompatibilityError('');
    setCompatibilityLoading(false);
    setCalculationSex(normalizeCalculationSex(profileBirth.calculation_sex || primaryProfileBirth.calculation_sex));
    setRelationshipCalculationSex(normalizeCalculationSex(relationshipProfileBirth.calculation_sex));
    if (DAY_BOUNDARY_OPTIONS.some((option) => option.value === calculationOptions.day_boundary_rule)) {
      setDayBoundaryRule(calculationOptions.day_boundary_rule);
    }
    if (HOUR_VARIANT_OPTIONS.some((option) => option.value === calculationOptions.hour_pillar_variant)) {
      setHourPillarVariant(calculationOptions.hour_pillar_variant);
    }
    if (LUCK_DIRECTION_OPTIONS.some((option) => option.value === calculationOptions.luck_direction_rule)) {
      setLuckDirectionRule(calculationOptions.luck_direction_rule);
    }
    if (typeof profileBirth.true_solar_time?.requested === 'boolean') {
      setUseTrueSolarTime(profileBirth.true_solar_time.requested);
    }
    setActiveTab('reading');
    setSourceMode('snap');
    if (payload.profile.source_snap_id) setSelectedSnapId(String(payload.profile.source_snap_id));
    const relationshipSnapId = profiles?.relationship?.source_snap_id
      || payload.compatibility?.subjects?.relationship?.source_snap_id;
    if (relationshipSnapId) setComparisonSnapId(String(relationshipSnapId));
    const context = payload.compatibility?.scoring?.relationship_context || payload.compatibility?.relationship_context;
    if (context) setRelationshipContext(normalizeRelationshipContext(context));
    setCopyStatus('Loaded');
    window.setTimeout?.(() => setCopyStatus(''), 1800);
  }, []);
  const handleClearReadings = useCallback(() => {
    const ok = clearSavedReadingSnapshots();
    if (ok) setSavedReadings([]);
    setCopyStatus(ok ? 'History cleared' : 'Clear failed');
    window.setTimeout?.(() => setCopyStatus(''), 1800);
  }, []);
  const handleResetPreferences = useCallback(() => {
    clearPreferences();
    setActiveTab(DEFAULT_PREFERENCES.activeTab);
    setCalculationSex(DEFAULT_PREFERENCES.calculationSex);
    setRelationshipCalculationSex(DEFAULT_PREFERENCES.relationshipCalculationSex);
    setComparisonSnapId(DEFAULT_PREFERENCES.comparisonSnapId);
    setCompatibilityProfiles(null);
    setDayBoundaryRule(DEFAULT_PREFERENCES.dayBoundaryRule);
    setHourPillarVariant(DEFAULT_PREFERENCES.hourPillarVariant);
    setLuckDirectionRule(DEFAULT_PREFERENCES.luckDirectionRule);
    setRelationshipContext(DEFAULT_PREFERENCES.relationshipContext);
    setSourceMode(DEFAULT_PREFERENCES.sourceMode);
    setUseTrueSolarTime(DEFAULT_PREFERENCES.useTrueSolarTime);
    setSelectedSnapId(activeSnapId ? String(activeSnapId) : String(snapOptions[0]?.id || ''));
    setCopyStatus('Preferences reset');
    window.setTimeout?.(() => setCopyStatus(''), 1800);
  }, [activeSnapId, snapOptions]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4 backdrop-blur-[2px]">
      <div className={`${PAPER} flex max-h-[94vh] w-full max-w-[1180px] flex-col overflow-hidden rounded-[28px] border border-zinc-200/80 shadow-[0_28px_80px_rgba(20,14,33,0.22)]`}>
        <div className="flex flex-wrap items-center gap-4 border-b border-zinc-200/80 bg-white/95 px-6 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-teal-200 bg-teal-50 text-teal-700">
              <Compass aria-hidden="true" className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <Micro className="text-teal-700">Astro Clock / Chinese Astrology</Micro>
              <div className="mt-1 text-sm text-zinc-500">
                {activeTab === 'oracle' ? 'I Ching Oracle / casting memo' : 'BaZi Profile / chart memo'}
              </div>
            </div>
          </div>
          <div className="flex-1" />
          <div className="hidden flex-wrap gap-2 md:flex">
            <Pill
              active={activeTab !== 'oracle'}
              ariaLabel="Switch to BaZi Profile"
              onClick={() => setActiveTab(data ? 'reading' : 'chart')}
            >
              BaZi Profile
            </Pill>
            <Pill
              active={activeTab === 'oracle'}
              ariaLabel="Switch to I Ching Oracle"
              onClick={() => setActiveTab('oracle')}
            >
              I Ching Oracle
            </Pill>
          </div>
          {activeTab !== 'oracle' ? (
            <div className="hidden text-[11px] text-zinc-400 md:block" style={monoStyle}>
            {data?.debug?.solar_term_source ? `solar terms / ${data.debug.solar_term_source}` : 'solar terms / live'}
            </div>
          ) : null}
          <div className="flex items-center gap-2">
            <IconAction icon={History} label="Open saved Chinese Astrology readings" onClick={() => setShowHistory((value) => !value)} disabled={!savedReadings.length} />
            <IconAction icon={RotateCcw} label="Reset Chinese Astrology preferences" onClick={handleResetPreferences} />
            <IconAction icon={Save} label="Save Chinese Astrology reading locally" onClick={handleSaveReading} disabled={!data} />
            <IconAction icon={Copy} label="Copy Chinese Astrology reading" onClick={handleCopyReading} disabled={!data && !oracleData} />
            <IconAction icon={Download} label="Export Chinese Astrology JSON" onClick={handleExportJson} disabled={!data && !oracleData} />
          </div>
          {copyStatus ? (
            <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-500" style={monoStyle}>{copyStatus}</div>
          ) : null}
          <button
            type="button"
            className="border-b border-zinc-300 pb-1 text-[13px] text-zinc-600 transition hover:border-zinc-500 hover:text-zinc-900"
            onClick={handleBack}
          >
            Close
          </button>
        </div>

        {showHistory ? (
          <ReadingHistoryPanel
            rows={savedReadings}
            onLoad={handleOpenSavedReading}
            onClear={handleClearReadings}
          />
        ) : null}

        {activeTab !== 'oracle' ? (
        <div className="border-b border-zinc-200/80 bg-white/95 px-6 py-4">
          <div className="flex flex-col gap-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              <CompactOptionToggle
                label="chart source"
                value={sourceMode}
                onChange={setSourceMode}
                options={[
                  { value: 'snap', label: 'Saved Snap' },
                  { value: 'manual', label: 'Direct Input' },
                ]}
              />
              <CompactOptionToggle
                label="primary calculation sex"
                value={calculationSexControlValue}
                onChange={handleCalculationSexChange}
                options={CALCULATION_SEX_GLOBAL_OPTIONS}
              />
              <CompactOptionToggle
                label="hour mode"
                value={useTrueSolarTime ? 'true_solar' : 'civil'}
                onChange={(value) => setUseTrueSolarTime(value === 'true_solar')}
                options={[
                  { value: 'civil', label: 'Civil' },
                  { value: 'true_solar', label: 'True Solar' },
                ]}
              />
              <CompactOptionToggle label="day boundary" value={dayBoundaryRule} onChange={setDayBoundaryRule} options={DAY_BOUNDARY_OPTIONS} />
              <CompactOptionToggle label="Zi hour" value={hourPillarVariant} onChange={setHourPillarVariant} options={HOUR_VARIANT_OPTIONS} />
              <CompactOptionToggle label="luck rule" value={luckDirectionRule} onChange={setLuckDirectionRule} options={LUCK_DIRECTION_OPTIONS} />
            </div>

            {sourceMode === 'snap' ? (
              <div className="grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_200px_170px_auto]">
                <Field label="primary snap">
                  <select
                    aria-label="Primary saved snap"
                    value={selectedSnapId}
                    onChange={(event) => setSelectedSnapId(event.target.value)}
                    disabled={effectiveLoadingSnaps || !snapOptions.length}
                    className={underlineControlClass}
                  >
                    <option value="">{effectiveLoadingSnaps ? 'Loading saved snaps...' : 'Select a saved snap'}</option>
                    {snapOptions.map((snap) => (
                      <option key={snap.id} value={snap.id}>{formatSnapLabel(snap)}</option>
                    ))}
                  </select>
                </Field>
                <Field label="relationship snap">
                  <select
                    aria-label="Relationship snap"
                    value={comparisonSnapId}
                    onChange={(event) => setComparisonSnapId(event.target.value)}
                    disabled={effectiveLoadingSnaps || snapOptions.length < 2}
                    className={underlineControlClass}
                  >
                    <option value="">{effectiveLoadingSnaps ? 'Loading saved snaps...' : 'No second snap'}</option>
                    {snapOptions.map((snap) => (
                      <option key={`compare-${snap.id}`} value={snap.id}>{formatSnapLabel(snap)}</option>
                    ))}
                  </select>
                </Field>
                <Field label="relationship calculation sex">
                  <select
                    aria-label="Relationship calculation sex"
                    value={relationshipCalculationSex}
                    onChange={(event) => setRelationshipCalculationSex(normalizeCalculationSex(event.target.value))}
                    disabled={!comparisonSnapId}
                    className={underlineControlClass}
                  >
                    <option value="">Not Set</option>
                    {CALCULATION_SEX_OPTIONS.map((option) => (
                      <option key={`relationship-sex-${option.value}`} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </Field>
                <Field label="pair use">
                  <select
                    aria-label="Relationship context"
                    value={relationshipContext}
                    onChange={(event) => setRelationshipContext(normalizeRelationshipContext(event.target.value))}
                    className={underlineControlClass}
                  >
                    {RELATIONSHIP_CONTEXT_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </Field>
                <button
                  type="button"
                  onClick={loadSnaps}
                  disabled={effectiveLoadingSnaps}
                  className={`self-end ${secondaryActionClass}`}
                  style={monoStyle}
                >
                  {effectiveLoadingSnaps ? 'Loading' : 'Refresh'}
                </button>
              </div>
            ) : (
              <div className="grid flex-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
                <Field label="date">
                  <input type="date" value={manual.date} onChange={(event) => setManual((prev) => ({ ...prev, date: event.target.value }))} className={underlineControlClass} />
                </Field>
                <Field label="time">
                  <input type="time" value={manual.time} onChange={(event) => setManual((prev) => ({ ...prev, time: event.target.value }))} className={underlineControlClass} />
                </Field>
                <Field label="location">
                  <input type="text" value={manual.location} onChange={(event) => setManual((prev) => ({ ...prev, location: event.target.value }))} className={underlineControlClass} />
                </Field>
                <Field label="timezone">
                  <input type="text" value={manual.timezone} onChange={(event) => setManual((prev) => ({ ...prev, timezone: event.target.value }))} className={underlineControlClass} />
                </Field>
                <Field label="latitude">
                  <input type="number" step="any" value={manual.latitude} onChange={(event) => setManual((prev) => ({ ...prev, latitude: event.target.value }))} className={underlineControlClass} />
                </Field>
                <Field label="longitude">
                  <input type="number" step="any" value={manual.longitude} onChange={(event) => setManual((prev) => ({ ...prev, longitude: event.target.value }))} className={underlineControlClass} />
                </Field>
              </div>
            )}
          </div>

          {sourceMode === 'manual' ? (
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={runBazi}
                disabled={!canRunManual || loading}
                className={primaryActionClass}
                style={monoStyle}
              >
                {loading ? 'Calculating' : 'Calculate'}
              </button>
            </div>
          ) : null}
          <InputPromptStrip prompts={promptItems} />
        </div>
        ) : null}

        <div className="border-b border-zinc-200/80 bg-white px-6 py-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex flex-wrap gap-2">
              {PRIMARY_TAB_CONFIG.map(([id, label]) => (
                <TabPillButton key={id} active={activeTab === id} onClick={() => setActiveTab(id)}>
                  {label}
                </TabPillButton>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <TabOptionMenu label="More Analysis" options={ANALYSIS_TAB_CONFIG} activeTab={activeTab} onSelect={setActiveTab} />
              {SHOW_DEV_METHOD_SURFACE ? (
                <TabPillButton active={activeTab === 'notes'} onClick={() => setActiveTab('notes')}>
                  Method Notes
                </TabPillButton>
              ) : null}
              <TabPillButton active={activeTab === 'oracle'} onClick={() => setActiveTab('oracle')}>
                I Ching Oracle
              </TabPillButton>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto bg-white px-6 py-6" aria-busy={loading || oracleLoading ? 'true' : 'false'}>
          {activeTab !== 'oracle' && error ? (
            <div className="mb-6 rounded-sm border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
          ) : null}

          {activeTab !== 'oracle' && loading ? (
            <StatePanel title="Composing BaZi profile." body="The memo is resolving pillars, Day Master, timing, and relationship contacts from the selected chart." />
          ) : null}

          {activeTab === 'oracle' ? (
            <IChingOraclePanel
              question={oracleQuestion}
              onQuestionChange={setOracleQuestion}
              method={oracleMethod}
              onMethodChange={setOracleMethod}
              coinValueScheme={oracleCoinValueScheme}
              onCoinValueSchemeChange={setOracleCoinValueScheme}
              manualLines={oracleManualLines}
              onManualLineChange={handleOracleLineChange}
              onCast={runOracle}
              loading={oracleLoading}
              error={oracleError}
              oracle={oracleData}
            />
          ) : null}

          {activeTab !== 'oracle' && !loading && !data && !error ? (
            <StatePanel
              title={snapsLoaded && !snapOptions.length ? 'No saved snaps found' : 'Choose a chart'}
              body={snapsLoaded && !snapOptions.length ? 'Save a chart snap in Astro Clock, or use direct input to calculate a profile.' : 'Select a saved snap or enter birth details to begin.'}
            />
          ) : null}

          {data && activeTab === 'chart' ? (
            <MemoSection
              number="I"
              title="Four Pillars"
            >
              <div className="grid gap-8 xl:grid-cols-[minmax(0,1.85fr)_minmax(300px,0.75fr)]">
                <ChartGrid pillars={data.pillars || {}} />
                <DayMasterCard dayMaster={data.day_master} analysis={data.analysis} />
              </div>
            </MemoSection>
          ) : null}
          {data && activeTab === 'reading' ? <InterpretationPanel data={data} /> : null}
          {SHOW_DEV_METHOD_SURFACE && data && activeTab === 'day-master' ? (
            <MemoSection number="III" title="Day Master" subtitle="Strength stays provisional until the chart evidence is decisive.">
              <DayMasterCard dayMaster={data.day_master} analysis={data.analysis} />
            </MemoSection>
          ) : null}
          {data && activeTab === 'elements' ? (
            <MemoSection number="IV" title="Element Balance" subtitle="Unweighted presence counts include visible stems, branch bodies, and hidden stems. They are an inventory, not a qi-strength score.">
              <ElementBalance balance={data.element_balance} />
            </MemoSection>
          ) : null}
          {data && activeTab === 'useful' ? <UsefulElementsPanel recommendations={data.useful_elements} /> : null}
          {data && activeTab === 'ten-gods' ? (
            <MemoSection number="VI" title="Ten Gods" subtitle="Visible stems and hidden stems are mapped relative to the Day Master.">
              <TenGodsPanel tenGods={data.ten_gods} />
            </MemoSection>
          ) : null}
          {data && activeTab === 'palaces' ? <LifeAreasPanel lifeAreas={data.life_areas} context={data.palace_context} /> : null}
          {data && activeTab === 'relationships' ? (
            <>
              {sourceMode === 'snap' && (comparisonSnapId || compatibilityLoading || compatibilityError || compatibilityData) ? (
                <PairCompatibilityPanel
                  report={compatibilityData}
                  loading={compatibilityLoading}
                  error={sameComparisonSnap ? 'Choose two different saved snaps for pair compatibility.' : compatibilityError}
                />
              ) : null}
              <RelationshipCodesPanel relationships={data.relationships} number={comparisonSnapId ? 'VIII-B' : 'VIII'} />
            </>
          ) : null}
          {data && activeTab === 'stars' ? <AuxiliaryStarsPanel stars={data.auxiliary_stars} /> : null}
          {data && activeTab === 'classical' ? <ClassicalExtrasPanel extras={data.classical_extras} /> : null}
          {data && activeTab === 'timing' ? (
            <TimingPanel data={data} />
          ) : null}
          {SHOW_DEV_METHOD_SURFACE && data && activeTab === 'notes' ? (
            <>
              <NotesPanel data={data} />
              <MemoSection number="XIII" title="Technical Details" subtitle="Calculation settings and backend assumptions for this profile.">
                <DebugPanel data={data} />
              </MemoSection>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
