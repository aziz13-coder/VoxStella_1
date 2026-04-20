import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AstroClockAPI } from './api.mjs';

const PAPER = 'bg-white';
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };
const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };
const glyphStyle = { fontFamily: '"Segoe UI Symbol", "Noto Sans Symbols 2", "Noto Sans Symbols", "DejaVu Sans", sans-serif' };
const FALLBACK_ENGINES = [
  { id: 'memo', label: 'Memo', report_kind: 'memo', description: 'Narrative memo built from the current synastry scoring catalog.' },
  { id: 'life_themes', label: 'Life Themes', report_kind: 'structured', description: 'Full-house compatibility engine organized as self-to-theme comparisons.' },
  { id: 'union_dynamics', label: 'Union Dynamics', report_kind: 'structured', description: 'Partnership and domestic compatibility engine organized around bond and home dynamics.' },
  { id: 'work_alliance', label: 'Work Alliance', report_kind: 'structured', description: 'Collaboration-focused compatibility engine built from the business house cluster.' },
];
const PROFILE_OPTIONS = [
  { value: 'blended', label: 'Blended' },
  { value: 'feminine', label: 'Feminine' },
  { value: 'masculine', label: 'Masculine' },
];

function normalizeProfileHint(value) {
  const raw = String(value || '').trim().toLowerCase();
  if (raw === 'feminine' || raw === 'female' || raw === 'f') return 'feminine';
  if (raw === 'masculine' || raw === 'male' || raw === 'm') return 'masculine';
  return 'blended';
}

function formatSnapLabel(snap) {
  if (!snap) return 'Unknown snap';
  const label = String(snap.label || 'Untitled Snap').trim() || 'Untitled Snap';
  const iso = String(snap.effective_datetime || '');
  const location = String(snap.location || '').trim();
  let stamp = '';
  if (iso) {
    try {
      stamp = new Intl.DateTimeFormat('en-GB', {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(new Date(iso));
    } catch (_) {}
  }
  return [label, stamp, location].filter(Boolean).join(' | ');
}

function getSnapMetaParts(snap) {
  const label = String(snap?.label || 'Untitled Snap').trim() || 'Untitled Snap';
  const iso = String(snap?.effective_datetime || '');
  const location = String(snap?.location || '').trim();
  const timezone = String(snap?.timezone || snap?.tz || '').trim();
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
  return { label, datePart, timePart, location, timezone };
}

function mappedBarLeft(score, polarity) {
  const pct = Math.round(Math.min(100, Math.max(0, Number(score || 0))));
  if (String(polarity || '').toLowerCase() === 'negative') return `calc(${50 - (pct / 2)}% - 8px)`;
  return `calc(${50 + (pct / 2)}% - 8px)`;
}

function scoreColor(polarity) {
  const pol = String(polarity || '').toLowerCase();
  if (pol === 'negative') return 'text-rose-700';
  if (pol === 'positive') return 'text-emerald-700';
  return 'text-zinc-700';
}

function signedScoreColor(value) {
  const numeric = Number(value || 0);
  if (numeric > 0) return 'text-emerald-700';
  if (numeric < 0) return 'text-rose-700';
  return 'text-zinc-700';
}

function signedLineColor(value) {
  const numeric = Number(value || 0);
  if (numeric > 0) return 'bg-emerald-500';
  if (numeric < 0) return 'bg-rose-500';
  return 'bg-zinc-400';
}

function formatSigned(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric)) return '0';
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(0)}`;
}

function metricTone(value, negative = false) {
  const score = Math.max(0, Math.min(100, Number(value || 0)));
  if (negative) {
    if (score >= 72) return { label: 'high pressure', textClass: 'text-rose-700', lineClass: 'bg-rose-500' };
    if (score >= 45) return { label: 'present', textClass: 'text-amber-700', lineClass: 'bg-amber-500' };
    return { label: 'light', textClass: 'text-emerald-700', lineClass: 'bg-emerald-500' };
  }
  if (score >= 78) return { label: 'strong', textClass: 'text-emerald-700', lineClass: 'bg-emerald-500' };
  if (score >= 55) return { label: 'moderate', textClass: 'text-sky-700', lineClass: 'bg-sky-500' };
  return { label: 'thin', textClass: 'text-zinc-600', lineClass: 'bg-zinc-400' };
}

function durabilityTone(value) {
  const score = Math.max(0, Math.min(100, Number(value || 0)));
  if (score >= 78) return { textClass: 'text-emerald-700', lineClass: 'bg-emerald-500' };
  if (score >= 60) return { textClass: 'text-sky-700', lineClass: 'bg-sky-500' };
  if (score >= 40) return { textClass: 'text-amber-700', lineClass: 'bg-amber-500' };
  return { textClass: 'text-rose-700', lineClass: 'bg-rose-500' };
}

function buildRelationshipSignature({ overallScore, communication, compatibility, attachment, attraction, growth, burden, challenge, binding }) {
  const overall = Number(overallScore || 0);
  const dialogue = Number(communication || 0);
  const ease = Number(compatibility || 0);
  const staying = Number(attachment ?? binding ?? 0);
  const chemistry = Number(attraction ?? binding ?? 0);
  const developmental = Number(growth || 0);
  const weight = Number((burden ?? challenge) || 0);
  const pressure = Number(challenge || 0);
  if (staying >= 78 && developmental >= 78 && (weight >= 64 || pressure >= 68)) return { title: 'Binding and consequential, not effortless', body: 'The connection looks structurally strong and life-shaping, but the pressure load is too visible for it to read as easy or naturally smooth.' };
  if (staying >= 80 && ease >= 62 && weight <= 70) return { title: 'Binding with real staying power', body: 'The comparison suggests a relationship that tends to hold form over time. It may still require adjustment, but the bond itself is not weak.' };
  if (dialogue >= 70 && ease >= 72 && weight <= 45) return { title: 'Naturally cooperative', body: 'The charts lean toward day-to-day fit, mutual goodwill, and fewer structural obstacles than average.' };
  if (developmental >= 82 && (weight >= 72 || pressure >= 74)) return { title: 'Catalytic and high-pressure', body: 'This reads like a bond that changes both people quickly. It carries purpose and impact, but intensity can overwhelm peace.' };
  if (staying >= 72 && weight >= 76) return { title: 'Bound, but under strain', body: 'The comparison still shows real staying force, but the relationship carries enough heaviness that maintenance becomes part of the bond itself.' };
  if (chemistry >= 78 && staying < 62 && weight <= 68) return { title: 'Magnetic, but less settled', body: 'The draw is visible, but the bond looks more compelling than naturally stabilizing. It may hold attention more easily than form.' };
  if (pressure >= 76 || weight >= 76) return { title: 'Intense with recurring strain', body: 'The connection has force, but conflict or weight stays too present to ignore. It reads as vivid rather than restful.' };
  if (overall >= 65) return { title: 'Mixed, but workable', body: 'The charts show enough traction to function, even though the relationship still carries visible tradeoffs.' };
  return { title: 'Mixed, but meaningful', body: 'This comparison does not collapse into easy harmony or clear incompatibility. It reads as a relationship with both traction and tension.' };
}

function Kicker({ children, className = 'text-zinc-500' }) {
  return <div className={`text-[10px] font-semibold uppercase tracking-[0.24em] ${className}`} style={monoStyle}>{children}</div>;
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
      <p className="mx-auto mt-3 max-w-xl text-[1rem] leading-relaxed text-zinc-600">{body}</p>
    </div>
  );
}

function SubjectNameplate({ label, value, onChange, options, snap, chartLabel, right = false }) {
  const parts = getSnapMetaParts(snap);
  return (
    <div className={`flex flex-col gap-3 p-5 ${right ? 'md:items-end md:text-right' : ''}`}>
      <div className="w-full">
        <Kicker>{label}</Kicker>
        <label className="sr-only" htmlFor={`syn-${label.toLowerCase().replace(/\s+/g, '-')}`}>{label}</label>
        <select
          id={`syn-${label.toLowerCase().replace(/\s+/g, '-')}`}
          aria-label={label}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={`${PAPER} mt-2 w-full border-b border-zinc-200 pb-2 text-[12px] text-zinc-600 outline-none transition focus:border-teal-500`}
        >
          <option value="">{`Select ${label.toLowerCase()}`}</option>
          {options.map((option) => <option key={`${label}-${option.id}`} value={option.id}>{formatSnapLabel(option)}</option>)}
        </select>
      </div>
      <div className="min-h-[72px]">
        <div className={`flex items-center text-[1.05rem] font-semibold tracking-[-0.02em] text-zinc-900 ${right ? 'md:justify-end' : ''}`}>
          {!right ? <span className="mr-3 inline-block h-2 w-2 rounded-full bg-teal-600" /> : null}
          <span>{chartLabel || parts.label}</span>
          {right ? <span className="ml-3 inline-block h-2 w-2 rounded-full bg-teal-600" /> : null}
        </div>
        <div className={`mt-2 flex flex-wrap gap-x-2 gap-y-1 text-[12px] text-zinc-500 ${right ? 'md:justify-end' : ''}`}>
          {parts.datePart ? <span>{parts.datePart}</span> : null}
          {parts.timePart ? <span className="text-zinc-300">/</span> : null}
          {parts.timePart ? <span>{parts.timePart}</span> : null}
          {parts.location ? <span className="text-zinc-300">/</span> : null}
          {parts.location ? <span>{parts.location}</span> : null}
        </div>
        {parts.timezone ? <div className="mt-1 text-[10.5px] uppercase tracking-[0.2em] text-zinc-400" style={monoStyle}>{parts.timezone}</div> : null}
      </div>
    </div>
  );
}

function EvidenceColumn({ title, items, emptyText, negative = false, start = 1 }) {
  const toneClass = negative ? 'text-rose-700' : 'text-emerald-700';
  const bulletClass = negative ? 'bg-rose-500' : 'bg-emerald-500';
  const list = Array.isArray(items) ? items : [];
  return (
    <div>
      <div className="flex items-center gap-3 border-b border-zinc-200 pb-3">
        <span className={`inline-block h-2 w-2 rounded-full ${bulletClass}`} />
        <Kicker>{title}</Kicker>
      </div>
      {list.length ? list.map((item, idx) => (
        <div key={`${title}-${idx}`} className="grid gap-4 border-b border-zinc-100 py-4 md:grid-cols-[minmax(0,1fr)_auto]">
          <div>
            <div className="text-[1rem] font-semibold tracking-[-0.02em] text-zinc-900">
              {item?.label || item?.detail || 'Signal'}
              <sup className="ml-1 text-[10px] text-zinc-400">{start + idx}</sup>
            </div>
            {item?.detail ? <div className="mt-1 text-sm leading-relaxed text-zinc-600">{item.detail}</div> : null}
          </div>
          <div className={`text-[1.25rem] font-semibold tracking-[-0.02em] ${toneClass} md:text-right`}>
            {negative ? '-' : '+'}{Number(item?.impact || 0).toFixed(1)}
          </div>
        </div>
      )) : <div className="pt-4 text-sm text-zinc-500">{emptyText}</div>}
    </div>
  );
}

function OverlayColumn({ title, items, emptyText }) {
  const list = Array.isArray(items) ? items : [];
  return (
    <div>
      <Kicker>{title}</Kicker>
      {list.length ? (
        <div className="mt-3">
          {list.slice(0, 10).map((item, idx) => (
            <div key={`${title}-${idx}`} className="grid grid-cols-[84px_88px_minmax(0,1fr)] items-baseline gap-3 border-b border-zinc-100 py-3 text-sm">
              <div className="font-semibold text-zinc-900">{item?.point || 'Point'}</div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-teal-700" style={monoStyle}>House {item?.house}</div>
              <div className="text-zinc-600">{item?.label || 'House overlay'}</div>
            </div>
          ))}
        </div>
      ) : <div className="mt-3 text-sm text-zinc-500">{emptyText}</div>}
    </div>
  );
}

function ScopeTileToggle({ label, checked, disabled = false, onChange }) {
  const activeCls = checked
    ? 'border-zinc-900 bg-zinc-800 text-white'
    : 'border-zinc-300 bg-zinc-100 text-zinc-700 hover:bg-zinc-200';
  return (
    <label
      className={`inline-flex items-center gap-2 rounded-[4px] border px-2.5 py-1.5 text-[11px] font-semibold tracking-[0.08em] transition ${activeCls} ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
      style={monoStyle}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(Boolean(event.target.checked))}
        className="sr-only"
        aria-label={label}
      />
      <span
        aria-hidden="true"
        className={`inline-flex h-3.5 w-3.5 items-center justify-center rounded-[2px] border ${checked ? 'border-white/60 bg-black/15' : 'border-zinc-400 bg-white'}`}
      >
        {checked ? (
          <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
            <path d="M2 5.5L4 7.4L8 3.2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : null}
      </span>
      <span>{label}</span>
    </label>
  );
}

function EngineTabs({ engines, activeEngineId, onSelect }) {
  const list = Array.isArray(engines) && engines.length ? engines : FALLBACK_ENGINES;
  return (
    <div className="border-b border-zinc-200/80 bg-white px-6 py-3">
      <div className="flex flex-wrap gap-2">
        {list.map((engine) => {
          const active = String(engine?.id || '') === String(activeEngineId || '');
          return (
            <button
              key={engine?.id || engine?.label}
              type="button"
              onClick={() => onSelect(String(engine?.id || 'memo'))}
              className={`rounded-full border px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] transition ${active ? 'border-zinc-900 bg-zinc-900 text-white' : 'border-zinc-300 bg-zinc-50 text-zinc-700 hover:border-zinc-400 hover:bg-zinc-100'}`}
              style={monoStyle}
            >
              {engine?.label || engine?.id || 'Engine'}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function StructuredMetricCard({ label, value, caption }) {
  const width = Math.min(100, Math.max(8, Math.abs(Number(value || 0)) * 3.2));
  return (
    <div>
      <Kicker>{label}</Kicker>
      <div className={`mt-2 text-[2rem] font-medium leading-none tracking-[-0.05em] ${signedScoreColor(value)}`} style={serifStyle}>{formatSigned(value)}</div>
      {caption ? <div className="mt-2 text-sm leading-relaxed text-zinc-500">{caption}</div> : null}
      <div className="mt-3 h-[2px] bg-zinc-100">
        <div className={`h-full ${signedLineColor(value)}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function normalizeStructuredRowDetail(detail) {
  const text = String(detail || '').trim();
  if (!text) return '';
  const lowered = text.toLowerCase();
  if (lowered.includes('psychology bucket match')) return '';
  if (lowered.startsWith('direct psychology pair for house ')) return '';
  if (lowered.includes('psychology slot ')) return '';
  if (lowered.includes('h1(chart1) <-> hn(chart0)')) return '';
  if (lowered.includes('hn(chart1) <-> h1(chart0)')) return '';
  if (lowered.includes('h1(chart1) <-> h1(chart0)')) return '';
  return text;
}

function StructuredOutcomePanel({ check }) {
  if (!check) return null;
  const tone = durabilityTone(check?.score);
  return (
    <div className="mt-8 border-t border-zinc-200 pt-5">
      <div className="grid gap-6 lg:grid-cols-[152px_minmax(0,1fr)]">
        <div>
          <Kicker>Durability Check</Kicker>
          <div className={`mt-2 text-[3rem] font-medium leading-none tracking-[-0.06em] ${tone.textClass}`} style={serifStyle}>{Math.round(Number(check?.score || 0))}</div>
          <div className="mt-1 text-[10.5px] uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>{check?.label || 'outlook'}</div>
          <div className="mt-3 h-[2px] bg-zinc-200">
            <div className={`h-full ${tone.lineClass}`} style={{ width: `${Math.max(0, Math.min(100, Number(check?.score || 0)))}%` }} />
          </div>
        </div>
        <div>
          <div className="text-[1.15rem] font-semibold tracking-[-0.02em] text-zinc-900">{check?.title || 'Collaboration outlook'}</div>
          {check?.body ? <p className="mt-2 max-w-3xl text-sm leading-relaxed text-zinc-600">{check.body}</p> : null}
          {Array.isArray(check?.notes) && check.notes.length ? (
            <div className="mt-4 space-y-2 text-sm leading-relaxed text-zinc-600">
              {check.notes.map((note, idx) => <div key={`durability-note-${idx}`}>{note}</div>)}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function StructuredWorkspaceTabs({ pages, activePageId, onSelect }) {
  if (!Array.isArray(pages) || !pages.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {pages.map((page) => {
        const active = String(page?.id || '') === String(activePageId || '');
        return (
          <button
            key={page?.id || page?.label}
            type="button"
            onClick={() => onSelect(String(page?.id || ''))}
            className={`rounded-full border px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] transition ${active ? 'border-zinc-900 bg-zinc-900 text-white' : 'border-zinc-300 bg-white text-zinc-600 hover:border-zinc-400 hover:bg-zinc-50 hover:text-zinc-900'}`}
            style={monoStyle}
          >
            {page?.label || page?.id || 'Section'}
          </button>
        );
      })}
    </div>
  );
}

function StructuredRowsTable({ rows, emptyText = 'No rows were returned for this section.' }) {
  const list = Array.isArray(rows) ? rows : [];
  if (!list.length) return <div className="text-sm text-zinc-500">{emptyText}</div>;
  return (
    <div className="border-y border-zinc-200">
      <div className="grid grid-cols-[minmax(0,1fr)_108px_minmax(0,1fr)_72px] gap-4 border-b border-zinc-200 px-4 py-3 text-[10.5px] font-semibold uppercase tracking-[0.14em] text-zinc-500" style={monoStyle}>
        <div>Left</div>
        <div className="text-center">MID</div>
        <div>Right</div>
        <div className="text-right">Score</div>
      </div>
      <div>
        {list.map((row, idx) => {
          const score = Number(row?.score || 0);
          const detailText = normalizeStructuredRowDetail(row?.detail);
          const footerParts = [];
          if (detailText) footerParts.push(detailText);
          if (row?.mid_semantic && row?.mid_semantic !== detailText) footerParts.push(row.mid_semantic);
          if (row?.aspect_name) footerParts.push(
            <span key="aspect-name" className="text-[11px] uppercase tracking-[0.12em] text-zinc-500" style={monoStyle}>{row.aspect_name}</span>
          );
          if (row?.orb != null) footerParts.push(
            <span key="orb" className="text-[11px] uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>orb {Number(row.orb).toFixed(2)}</span>
          );
          return (
            <div key={`${row?.label || row?.mid_raw || 'row'}-${idx}`} className="border-b border-zinc-100 px-4 py-4 last:border-b-0">
              <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_108px_minmax(0,1fr)_72px]">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-zinc-900">{row?.left_label || '-'}</div>
                  {row?.left_meta ? <div className="mt-1 text-[11px] uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>{row.left_meta}</div> : null}
                </div>
                <div className="flex min-w-0 flex-col items-center justify-center text-center">
                  <div className="text-[1.35rem] leading-none text-zinc-900" style={glyphStyle}>{row?.mid_raw || '*'}</div>
                  <div className="mt-1 truncate text-[10px] uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>{String(row?.logic_type || row?.mode || '').replace(/_/g, ' ')}</div>
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-zinc-900">{row?.right_label || '-'}</div>
                  {row?.right_meta ? <div className="mt-1 text-[11px] uppercase tracking-[0.12em] text-zinc-400" style={monoStyle}>{row.right_meta}</div> : null}
                </div>
                <div className={`text-right text-[1.35rem] font-semibold leading-none tracking-[-0.03em] ${signedScoreColor(score)}`} style={serifStyle}>{formatSigned(score)}</div>
              </div>
              {footerParts.length ? (
                <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm leading-relaxed text-zinc-600">
                  {footerParts.map((part, partIdx) => (
                    <React.Fragment key={`${row?.label || row?.mid_raw || 'row'}-footer-${partIdx}`}>
                      {partIdx ? <span className="text-zinc-400">/</span> : null}
                      {typeof part === 'string' ? <span>{part}</span> : part}
                    </React.Fragment>
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

function StructuredGroupSection({ section }) {
  const items = Array.isArray(section?.items) ? section.items : [];
  if (!items.length) return <div className="text-sm text-zinc-500">No structured rows were returned for this section.</div>;
  return (
    <div className="divide-y divide-zinc-200">
      {items.map((item) => (
        <section key={item?.id || item?.label} className="py-6 first:pt-0 last:pb-0">
          <div className="grid gap-4 border-b border-zinc-200 pb-4 md:grid-cols-[minmax(0,1fr)_160px] md:items-start">
            <div className="max-w-3xl">
                <Kicker>{section?.label || 'Theme'}</Kicker>
                <div className="mt-2 text-[1.15rem] font-semibold tracking-[-0.02em] text-zinc-900">{item?.label || item?.id || 'Theme'}</div>
                {item?.summary ? <div className="mt-2 text-sm leading-relaxed text-zinc-600">{item.summary}</div> : null}
            </div>
            <div className="text-right">
              <div className={`text-[2.4rem] font-medium leading-none tracking-[-0.05em] ${signedScoreColor(item?.score)}`} style={serifStyle}>{formatSigned(item?.score)}</div>
              <div className="mt-2 flex flex-wrap justify-end gap-x-3 gap-y-1 text-[10.5px] uppercase tracking-[0.14em] text-zinc-400" style={monoStyle}>
                <span>{item?.row_count || 0} rows</span>
                <span>positive {Number(item?.positive_count || 0)}</span>
                <span>negative {Number(item?.negative_count || 0)}</span>
                {item?.house ? <span>house {item.house}</span> : null}
                {item?.direct_score != null ? <span>direct {formatSigned(item.direct_score)}</span> : null}
                {item?.role_score != null ? <span>role {formatSigned(item.role_score)}</span> : null}
              </div>
            </div>
          </div>
          {Array.isArray(item?.notes) && item.notes.length ? (
            <div className="space-y-1.5 pt-4 text-sm leading-relaxed text-zinc-600">
              {item.notes.map((note, idx) => <div key={`${item?.id || item?.label}-note-${idx}`}>{note}</div>)}
            </div>
          ) : null}
          <div className="pt-5">
            <StructuredRowsTable rows={item?.rows} emptyText="No row-level breakdown was returned for this theme." />
          </div>
        </section>
      ))}
    </div>
  );
}

function StructuredEventSection({ section }) {
  return <StructuredRowsTable rows={section?.items} />;
}

function StructuredAreaStripe({ stripe, activeBucketId, onSelect }) {
  const buckets = Array.isArray(stripe?.buckets) ? stripe.buckets : [];
  if (!buckets.length) return null;
  const activeBucket = buckets.find((bucket) => String(bucket?.id || '') === String(activeBucketId || '')) || buckets[0];
  const maxValue = Math.max(1, Number(stripe?.max_value || 0), ...buckets.map((bucket) => Math.max(Math.abs(Number(bucket?.primary_value || 0)), Math.abs(Number(bucket?.secondary_value || 0)))));
  const primaryPct = Math.round((Math.abs(Number(activeBucket?.primary_value || 0)) / maxValue) * 100);
  const secondaryPct = Math.round((Math.abs(Number(activeBucket?.secondary_value || 0)) / maxValue) * 100);
  return (
    <section className="border-t border-zinc-200 pt-5 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-zinc-200 pb-4">
        <div className="max-w-2xl">
          <Kicker>{stripe?.label || 'Stripe'}</Kicker>
          {stripe?.description ? <div className="mt-2 text-sm leading-relaxed text-zinc-600">{stripe.description}</div> : null}
        </div>
        <div className="min-w-[180px] text-right">
          <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>{activeBucket?.label || ''}</div>
          <div className="mt-1 flex items-end justify-end gap-3">
            <div className="text-[1.5rem] leading-none text-zinc-900" style={glyphStyle}>{activeBucket?.glyph || ''}</div>
            <div className="text-right">
              <div className="text-sm font-semibold text-sky-700">{stripe?.primary_label || 'Primary'} {Number(activeBucket?.primary_value || 0)} <span className="text-zinc-400">({primaryPct}%)</span></div>
              <div className="mt-1 text-sm font-semibold text-rose-600">{stripe?.secondary_label || 'Secondary'} {Number(activeBucket?.secondary_value || 0)} <span className="text-zinc-400">({secondaryPct}%)</span></div>
            </div>
          </div>
        </div>
      </div>
      <div className="pt-5">
        <div className={`grid gap-3 ${buckets.length > 4 ? 'grid-cols-12' : 'grid-cols-4'}`}>
          {buckets.map((bucket) => {
            const active = String(bucket?.id || '') === String(activeBucket?.id || '');
            const primaryHeight = Math.max(6, Math.round((Math.abs(Number(bucket?.primary_value || 0)) / maxValue) * 100));
            const secondaryHeight = Math.max(6, Math.round((Math.abs(Number(bucket?.secondary_value || 0)) / maxValue) * 100));
            return (
              <button
                key={bucket?.id || bucket?.label}
                type="button"
                onClick={() => onSelect(String(bucket?.id || ''))}
                className={`${buckets.length > 4 ? 'col-span-3' : ''} border-b px-2 pb-3 pt-1 text-center transition ${active ? 'border-zinc-900' : 'border-transparent hover:border-zinc-300'}`}
              >
                <div className="flex h-[124px] items-end justify-center gap-2 border-b border-zinc-100 pb-3">
                  <div className="relative flex h-full w-4 items-end">
                    <div className="w-full rounded-full bg-sky-500/20" style={{ height: `${primaryHeight}%` }} />
                    <div className="absolute inset-x-[3px] bottom-0 rounded-full bg-sky-600" style={{ height: `${primaryHeight}%` }} />
                  </div>
                  <div className="relative flex h-full w-4 items-end">
                    <div className="w-full rounded-full bg-rose-500/20" style={{ height: `${secondaryHeight}%` }} />
                    <div className="absolute inset-x-[3px] bottom-0 rounded-full bg-rose-600" style={{ height: `${secondaryHeight}%` }} />
                  </div>
                </div>
                <div className="mt-3 text-[1.05rem] leading-none text-zinc-900" style={glyphStyle}>{bucket?.glyph || bucket?.label || '*'}</div>
                <div className="mt-2 text-[10px] uppercase tracking-[0.14em] text-zinc-400" style={monoStyle}>{bucket?.label}</div>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function StructuredAreasPanel({ areas, selectedBuckets, onSelectBucket }) {
  const stripes = Array.isArray(areas?.stripes) ? areas.stripes : [];
  if (!stripes.length) return <div className="text-sm text-zinc-500">No areas diagram was returned for this engine.</div>;
  return (
    <div className="space-y-8">
      {stripes.map((stripe) => (
        <StructuredAreaStripe
          key={stripe?.id || stripe?.label}
          stripe={stripe}
          activeBucketId={selectedBuckets?.[stripe?.id] || ''}
          onSelect={(bucketId) => onSelectBucket(String(stripe?.id || ''), bucketId)}
        />
      ))}
    </div>
  );
}

export default function SynastryModal({ open, onClose, snaps = [], activeSnapId = '' }) {
  const sortedSnaps = useMemo(() => {
    const list = Array.isArray(snaps) ? snaps.slice() : [];
    return list.sort((a, b) => {
      const ta = new Date(String(a?.effective_datetime || '')).getTime();
      const tb = new Date(String(b?.effective_datetime || '')).getTime();
      if (Number.isFinite(tb) && Number.isFinite(ta) && tb !== ta) return tb - ta;
      return String(a?.label || '').localeCompare(String(b?.label || ''));
    });
  }, [snaps]);
  const [snapAId, setSnapAId] = useState('');
  const [snapBId, setSnapBId] = useState('');
  const [includeModern, setIncludeModern] = useState(true);
  const [includeNodes, setIncludeNodes] = useState(true);
  const [includeChiron, setIncludeChiron] = useState(false);
  const [orbProfile, setOrbProfile] = useState('balanced');
  const [activeEngineId, setActiveEngineId] = useState('memo');
  const [profileA, setProfileA] = useState('blended');
  const [profileB, setProfileB] = useState('blended');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [structuredPageId, setStructuredPageId] = useState('');
  const [selectedAreaBuckets, setSelectedAreaBuckets] = useState({});
  const lastEngineRef = useRef('memo');
  const requestProfileA = activeEngineId === 'union_dynamics' ? profileA : '';
  const requestProfileB = activeEngineId === 'union_dynamics' ? profileB : '';

  useEffect(() => {
    if (!open) return;
    const fallbackA = sortedSnaps.find((snap) => String(snap?.id || '') === String(activeSnapId || '')) || sortedSnaps[0] || null;
    const fallbackB = sortedSnaps.find((snap) => String(snap?.id || '') !== String(fallbackA?.id || '')) || null;
    setSnapAId((current) => current || String(fallbackA?.id || ''));
    setSnapBId((current) => current || String(fallbackB?.id || ''));
  }, [open, sortedSnaps, activeSnapId]);

  useEffect(() => {
    if (!open) return;
    const snapA = sortedSnaps.find((snap) => String(snap?.id || '') === String(snapAId || '')) || null;
    const snapB = sortedSnaps.find((snap) => String(snap?.id || '') === String(snapBId || '')) || null;
    const hintA = normalizeProfileHint(snapA?.profile_hint || snapA?.summary?.profile_hint);
    const hintB = normalizeProfileHint(snapB?.profile_hint || snapB?.summary?.profile_hint);
    setProfileA(hintA);
    setProfileB(hintB);
  }, [open, sortedSnaps, snapAId, snapBId]);

  useEffect(() => {
    if (!open) return;
    if (lastEngineRef.current !== activeEngineId) {
      lastEngineRef.current = activeEngineId;
      setData(null);
      setError(null);
    }
  }, [open, activeEngineId]);

  useEffect(() => {
    if (!open || !snapAId || !snapBId || snapAId === snapBId) return;
    let alive = true;
    const controller = new AbortController();
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await AstroClockAPI.getSynastry({
          snapAId,
          snapBId,
          engineId: activeEngineId,
          profileA: requestProfileA || undefined,
          profileB: requestProfileB || undefined,
          includeModern,
          includeNodes,
          includeChiron,
          orbProfile,
          signal: controller.signal,
        });
        if (!alive) return;
        if (res?.success) setData(res.data || null);
        else setError('Failed to load synastry report');
      } catch (err) {
        if (!alive || controller.signal.aborted) return;
        setError(String(err?.message || 'Failed to load synastry report'));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; controller.abort(); };
  }, [open, snapAId, snapBId, activeEngineId, requestProfileA, requestProfileB, includeModern, includeNodes, includeChiron, orbProfile]);

  const pointCapability = data?.governance?.point_capability || {};
  const isStructuredReport = String(data?.report_kind || '') === 'structured';
  const structuredSections = Array.isArray(data?.sections) ? data.sections : [];
  const structuredAreas = data?.areas || {};
  const structuredStripes = Array.isArray(structuredAreas?.stripes) ? structuredAreas.stripes : [];
  useEffect(() => {
    if (!open || !data) return;
    if (pointCapability.modern_supported === false && includeModern) setIncludeModern(false);
    if (pointCapability.chiron_supported === false && includeChiron) setIncludeChiron(false);
  }, [open, data, includeModern, includeChiron, pointCapability.modern_supported, pointCapability.chiron_supported]);

  useEffect(() => {
    if (!open || !isStructuredReport) {
      setStructuredPageId((current) => (current ? '' : current));
      setSelectedAreaBuckets((current) => (Object.keys(current).length ? {} : current));
      return;
    }
    const nextSections = Array.isArray(data?.sections) ? data.sections : [];
    const nextStripes = Array.isArray(data?.areas?.stripes) ? data.areas.stripes : [];
    const defaultPageId = nextStripes.length ? 'areas' : String(nextSections[0]?.id || '');
    setStructuredPageId((current) => (current === defaultPageId ? current : defaultPageId));
    setSelectedAreaBuckets(() => {
      const next = {};
      nextStripes.forEach((stripe) => {
        const stripeId = String(stripe?.id || '');
        const firstBucketId = String(stripe?.buckets?.[0]?.id || '');
        if (stripeId && firstBucketId) next[stripeId] = firstBucketId;
      });
      return next;
    });
  }, [open, data, isStructuredReport]);

  if (!open) return null;

  const selectedA = sortedSnaps.find((snap) => String(snap?.id || '') === String(snapAId || '')) || null;
  const selectedB = sortedSnaps.find((snap) => String(snap?.id || '') === String(snapBId || '')) || null;
  const availableEngines = Array.isArray(data?.available_engines) && data.available_engines.length ? data.available_engines : FALLBACK_ENGINES;
  const activeEngine = availableEngines.find((engine) => String(engine?.id || '') === String(activeEngineId || '')) || FALLBACK_ENGINES.find((engine) => engine.id === activeEngineId) || FALLBACK_ENGINES[0];
  const categories = Array.isArray(data?.categories) ? data.categories : [];
  const overall = categories.find((item) => String(item?.id || '') === 'overall') || null;
  const dimensions = categories.filter((item) => String(item?.id || '') !== 'overall');
  const dimensionScores = Object.fromEntries(
    dimensions
      .map((item) => [String(item?.id || ''), Number(item?.score || 0)])
      .filter(([id]) => id),
  );
  const overlays = data?.overlays || {};
  const summary = data?.summary || {};
  const governance = data?.governance || {};
  const overallComponents = summary?.overall_components || overall?.components || {};
  const categoryScores = overallComponents?.category_scores || dimensionScores;
  const supportiveLinks = Array.isArray(data?.top_supportive_links) ? data.top_supportive_links : [];
  const challengingLinks = Array.isArray(data?.top_challenging_links) ? data.top_challenging_links : [];
  const modernAvailable = pointCapability.modern_supported !== false;
  const chironAvailable = pointCapability.chiron_supported !== false;
  const pointCapabilityNotice = !modernAvailable && !chironAvailable
    ? 'This chart data path currently supports the classical layer only, so modern planets and Chiron are disabled for this pair.'
    : !modernAvailable
      ? 'Modern planets are not available from the current chart data path, so that layer is disabled for this pair.'
      : !chironAvailable
        ? 'Modern planets are available. Chiron requires an asteroid ephemeris file that is not present in this build, so the Chiron layer is disabled.'
        : '';
  const initialLoading = loading && !data;
  const refreshing = loading && Boolean(data);
  const signature = buildRelationshipSignature({
    overallScore: overall?.score,
    communication: categoryScores?.communication,
    compatibility: categoryScores?.compatibility ?? overallComponents?.compatibility,
    attachment: categoryScores?.attachment,
    attraction: categoryScores?.attraction,
    binding: overallComponents?.binding,
    growth: categoryScores?.growth ?? overallComponents?.growth,
    burden: categoryScores?.burden,
    challenge: overallComponents?.challenge,
  });
  const overallPct = Math.round(Math.min(100, Math.max(0, Number(overall?.score || 0))));
  const left = mappedBarLeft(overallPct, overall?.polarity);
  const chartALabel = data?.chart_a?.label || selectedA?.label || 'Chart A';
  const chartBLabel = data?.chart_b?.label || selectedB?.label || 'Chart B';
  const summaryLines = Array.isArray(summary?.summary_lines) ? summary.summary_lines : [];
  const pressureTone = metricTone(overallComponents?.challenge, true);
  const unionEngineActive = String(activeEngineId || '') === 'union_dynamics';
  const workAllianceActive = String(activeEngineId || '') === 'work_alliance';
  const durabilityCheck = workAllianceActive ? (summary?.durability_check || null) : null;
  const structuredPages = [
    ...(structuredStripes.length ? [{ id: 'areas', label: 'Areas' }] : []),
    ...structuredSections.map((section) => ({ id: String(section?.id || ''), label: section?.label || section?.id || 'Section' })),
  ].filter((page) => String(page?.id || '').trim());
  const activeStructuredPageId = structuredPageId || String(structuredPages[0]?.id || '');
  const activeStructuredPage = structuredPages.find((page) => String(page?.id || '') === String(activeStructuredPageId || '')) || null;
  const activeStructuredSection = structuredSections.find((section) => String(section?.id || '') === String(activeStructuredPageId || '')) || null;
  const structuredPageTitle = activeStructuredPageId === 'areas'
    ? (structuredAreas?.label || 'Areas Diagram')
    : (activeStructuredPage?.label || activeEngine?.label || 'Structured engine');
  const structuredPageSubtitle = activeStructuredPageId === 'areas'
    ? String(structuredAreas?.description || "Four stripe graphs based on the structured engine's selected thematic pools.")
    : activeStructuredSection?.kind === 'group_breakdown'
      ? 'Grouped totals stay visible alongside the row-level breakdown for the active engine section.'
      : 'Highest-impact rows returned by the active engine section.';
  const structuredPageCountLabel = structuredStripes.length ? `${structuredStripes.length} stripe views` : `${structuredSections.length} sections`;
  const structuredWorkspaceSummary = activeStructuredPageId === 'areas'
    ? workAllianceActive
      ? 'Use the areas view to scan where self, resources, work, counterparty, and status gather before drilling into the detailed row sheets.'
      : 'Use the areas view to scan the strongest pools before drilling into the detailed row sheets.'
    : activeStructuredSection?.kind === 'group_breakdown'
      ? workAllianceActive
        ? 'This worksheet keeps the business-house foundation and row-level strain visible together.'
        : 'This worksheet keeps grouped totals and row-level evidence visible together.'
      : workAllianceActive
        ? 'This worksheet surfaces the highest-impact contacts and warnings shaping collaboration durability.'
        : 'This worksheet surfaces the highest-impact rows returned by the active engine.';
  const structuredModeLabel = activeStructuredPageId === 'areas'
    ? structuredPageCountLabel
    : activeStructuredSection?.kind === 'group_breakdown'
      ? 'grouped rows'
      : 'event rows';
  const structuredMetricCards = workAllianceActive
    ? [
        { label: 'Theme Base', value: summary?.theme_total, caption: 'Business-house foundation after pressure.' },
        { label: 'Contact Layer', value: summary?.aspect_total, caption: 'Shared contacts still active in the pair.' },
        { label: 'Pressure Load', value: summary?.burden_total, caption: 'Warning rows subtracting from long-run stability.' },
      ]
    : [
        { label: 'Theme Total', value: summary?.theme_total, caption: 'Theme families plus burden rows.' },
        { label: 'Aspect Total', value: summary?.aspect_total, caption: 'Shared cross-aspect layer.' },
        { label: 'Pressure', value: summary?.burden_total, caption: 'Burdening contribution inside the engine.' },
      ];

  function handleSelectAreaBucket(stripeId, bucketId) {
    setSelectedAreaBuckets((current) => ({ ...current, [stripeId]: bucketId }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4 backdrop-blur-[2px]">
      <div className={`${PAPER} flex max-h-[94vh] w-full max-w-[1180px] flex-col overflow-hidden rounded-[28px] border border-zinc-200/80 shadow-[0_28px_80px_rgba(20,14,33,0.22)]`}>
        <div className="flex items-center gap-4 border-b border-zinc-200/80 bg-white/95 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-teal-200 bg-teal-50 text-teal-700">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="5" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.2" /><circle cx="11" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.2" /></svg>
            </div>
            <div>
              <Kicker className="text-teal-700">Astro Clock / Synastry</Kicker>
              <div className="mt-1 text-sm text-zinc-500">{activeEngine?.label || 'Memo'} / snap-to-snap comparison</div>
            </div>
          </div>
          <div className="flex-1" />
          <div className="hidden text-[11px] text-zinc-400 md:block" style={monoStyle}>{governance?.catalog_version ? `catalog / ${governance.catalog_version}` : 'catalog / live'}</div>
          <button className="border-b border-zinc-300 pb-1 text-[13px] text-zinc-600 transition hover:border-zinc-500 hover:text-zinc-900" onClick={onClose}>Close</button>
        </div>

        <div className="grid border-b border-zinc-200/80 bg-white/95 md:grid-cols-[1fr_48px_1fr]">
          <SubjectNameplate label="Snap A" value={snapAId} onChange={setSnapAId} options={sortedSnaps} snap={selectedA} chartLabel={chartALabel} />
          <div className="hidden items-center justify-center md:flex"><div className="relative flex h-full items-center justify-center"><div className="absolute inset-y-5 w-px bg-zinc-200" /><div className={`${PAPER} relative px-3 text-xl text-teal-700`} style={serifStyle}>x</div></div></div>
          <SubjectNameplate label="Snap B" value={snapBId} onChange={setSnapBId} options={sortedSnaps} snap={selectedB} chartLabel={chartBLabel} right />
        </div>

        <EngineTabs engines={availableEngines} activeEngineId={activeEngineId} onSelect={setActiveEngineId} />

        <div className="border-b border-zinc-200/80 bg-white px-6 py-3">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-3 text-[12px] text-zinc-700">
            <Kicker>Scope</Kicker>
            <ScopeTileToggle label="Modern planets" checked={includeModern} disabled={!modernAvailable} onChange={setIncludeModern} />
            <ScopeTileToggle label="Nodes" checked={includeNodes} onChange={setIncludeNodes} />
            <ScopeTileToggle label="Chiron" checked={includeChiron} disabled={!chironAvailable} onChange={setIncludeChiron} />
            <div className="h-4 w-px bg-zinc-200" />
            <label className="inline-flex items-center gap-2"><span className="text-zinc-500">Orb profile</span><select value={orbProfile} onChange={(event) => setOrbProfile(String(event.target.value || 'balanced'))} className="rounded-sm border border-zinc-200 bg-white px-2.5 py-1 text-[12px] text-zinc-700 outline-none transition focus:border-teal-500"><option value="tight">Tight</option><option value="balanced">Balanced</option><option value="wide">Wide</option></select></label>
            {unionEngineActive ? (
              <>
                <div className="h-4 w-px bg-zinc-200" />
                <label className="inline-flex items-center gap-2"><span className="text-zinc-500">Profile A</span><select value={profileA} onChange={(event) => setProfileA(String(event.target.value || 'blended'))} className="rounded-sm border border-zinc-200 bg-white px-2.5 py-1 text-[12px] text-zinc-700 outline-none transition focus:border-teal-500">{PROFILE_OPTIONS.map((option) => <option key={`profile-a-${option.value}`} value={option.value}>{option.label}</option>)}</select></label>
                <label className="inline-flex items-center gap-2"><span className="text-zinc-500">Profile B</span><select value={profileB} onChange={(event) => setProfileB(String(event.target.value || 'blended'))} className="rounded-sm border border-zinc-200 bg-white px-2.5 py-1 text-[12px] text-zinc-700 outline-none transition focus:border-teal-500">{PROFILE_OPTIONS.map((option) => <option key={`profile-b-${option.value}`} value={option.value}>{option.label}</option>)}</select></label>
              </>
            ) : null}
            <div className="flex-1" />
            {refreshing ? <div aria-live="polite" className="inline-flex items-center gap-2 text-[11px] font-medium text-teal-700" style={monoStyle}><span className="inline-block h-2 w-2 animate-pulse rounded-full bg-teal-600" />Refreshing report</div> : null}
            {error && data ? <div className="text-[11px] font-medium text-rose-700" style={monoStyle}>x last refresh failed / showing previous report</div> : null}
          </div>
        </div>
        {pointCapabilityNotice ? <div className="border-b border-amber-200 bg-amber-50/70 px-6 py-2.5 text-[12px] text-amber-700">{pointCapabilityNotice}</div> : null}

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6" aria-busy={refreshing ? 'true' : 'false'}>
          {(sortedSnaps.length || 0) < 2 ? <StatePanel title="Save two snaps to compare." body="Synastry runs on frozen chart snapshots. Save at least two snaps in Astro Clock, then reopen this memo." /> : null}
          {!((sortedSnaps.length || 0) < 2) && snapAId === snapBId && snapAId ? <StatePanel title="Subject A and Subject B are the same snap." body="Choose a different snap on either side to produce a comparison." tone="warn" /> : null}
          {!((sortedSnaps.length || 0) < 2) && !(snapAId === snapBId && snapAId) && initialLoading ? <div className="px-6 py-10">{[0, 1, 2].map((idx) => <div key={idx} className="mb-8 space-y-3"><div className="h-3 w-24 animate-pulse rounded bg-zinc-200" /><div className="h-8 w-2/3 animate-pulse rounded bg-zinc-200" /><div className="h-3 w-full animate-pulse rounded bg-zinc-100" /><div className="h-3 w-5/6 animate-pulse rounded bg-zinc-100" /></div>)}</div> : null}
          {!((sortedSnaps.length || 0) < 2) && !(snapAId === snapBId && snapAId) && !initialLoading && error && !data ? <StatePanel title="The memo could not be composed." body={String(error || 'Failed to load synastry report')} tone="danger" /> : null}
          {!((sortedSnaps.length || 0) < 2) && !(snapAId === snapBId && snapAId) && !initialLoading && !error && !data ? <StatePanel title="Choose two snaps to begin." body="Synastry compares two saved charts. Select both subjects to compose the report." /> : null}
          {data ? (isStructuredReport ? (
            <div>
              <MemoSection
                number="I"
                title="Verdict"
              >
                <div className="grid gap-8 xl:grid-cols-[280px_minmax(0,1fr)]">
                  <div>
                    <Kicker>{activeEngine?.label || 'Structured engine'}</Kicker>
                    <div className={`mt-3 text-[5rem] font-medium leading-none tracking-[-0.08em] ${signedScoreColor(summary?.composite_total)}`} style={serifStyle}>{formatSigned(summary?.composite_total)}</div>
                    <div className="mt-2 text-sm text-zinc-500">Composite total</div>
                    <div className="mt-4 h-[6px] rounded-full bg-zinc-200">
                      <div className={`h-full rounded-full ${signedLineColor(summary?.composite_total)}`} style={{ width: `${Math.min(100, Math.max(8, Math.abs(Number(summary?.composite_total || 0)) * 2.2))}%` }} />
                    </div>
                    <div className="mt-4 text-sm leading-relaxed text-zinc-600">{activeEngine?.description || 'Structured compatibility engine.'}</div>
                    {unionEngineActive ? <div className="mt-4 text-[10.5px] uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>profiles / {profileA} x {profileB}</div> : null}
                  </div>

                  <div>
                    <div className="flex flex-wrap items-start justify-between gap-6">
                      <div className="max-w-3xl">
                        <Kicker>Structured workspace</Kicker>
                        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-zinc-600">{structuredWorkspaceSummary}</p>
                      </div>
                      <div className="min-w-[120px] border-l border-zinc-200 pl-5 text-right">
                        <Kicker>Mode</Kicker>
                        <div className="mt-2 text-[11px] uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>{structuredModeLabel}</div>
                      </div>
                    </div>

                    <div className="mt-8 border-t border-zinc-200 pt-5">
                      <StructuredWorkspaceTabs pages={structuredPages} activePageId={activeStructuredPageId} onSelect={setStructuredPageId} />
                    </div>

                    <div className="mt-8 grid gap-5 border-t border-zinc-200 pt-5 md:grid-cols-3">
                      {structuredMetricCards.map((card) => (
                        <StructuredMetricCard key={card.label} label={card.label} value={card.value} caption={card.caption} />
                      ))}
                    </div>

                    {durabilityCheck ? <StructuredOutcomePanel check={durabilityCheck} /> : null}

                    {summaryLines.length ? (
                      <div className="mt-8 border-t border-zinc-200 pt-5">
                        <Kicker>Reading notes</Kicker>
                        <div className="mt-3 space-y-2 text-sm leading-relaxed text-zinc-600">
                          {summaryLines.map((line, idx) => <div key={`structured-summary-${idx}`}>{line}</div>)}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              </MemoSection>

              <MemoSection number="II" title={structuredPageTitle} subtitle={structuredPageSubtitle}>
                {activeStructuredPageId === 'areas' ? (
                  <StructuredAreasPanel areas={structuredAreas} selectedBuckets={selectedAreaBuckets} onSelectBucket={handleSelectAreaBucket} />
                ) : activeStructuredSection?.kind === 'group_breakdown' ? (
                  <StructuredGroupSection section={activeStructuredSection} />
                ) : (
                  <StructuredEventSection section={activeStructuredSection} />
                )}
              </MemoSection>
            </div>
          ) : (
            <div>
              <MemoSection number="I" title="Verdict">
                <div className="grid gap-8 xl:grid-cols-[280px_minmax(0,1fr)]">
                  <div>
                    <Kicker>Overall Compatibility</Kicker>
                    <div className="mt-3 flex items-end gap-3"><div className={`text-[5rem] font-medium leading-none tracking-[-0.08em] ${scoreColor(overall?.polarity)}`} style={serifStyle}>{overallPct}</div><div className="pb-2 text-sm text-zinc-400">/100</div></div>
                    <div className="mt-4"><div className="relative h-[6px] rounded-full bg-zinc-200"><div className="absolute inset-y-0 left-1/2 w-px bg-zinc-500/60" /><div className="absolute -top-[3px] bottom-[-3px] w-4 rounded-full border border-zinc-400 bg-white" style={{ left }} /></div><div className="mt-2 flex items-center justify-between text-[10.5px] uppercase tracking-[0.18em] text-zinc-500" style={monoStyle}><span>raw {Number(overall?.raw_score || 0).toFixed(1)}/{Number(overall?.max_score || 0).toFixed(1)}</span><span className={scoreColor(overall?.polarity)}>{String(overall?.polarity || 'neutral')}</span></div></div>
                    {overall?.description ? <p className="mt-4 text-sm leading-relaxed text-zinc-600">{overall.description}</p> : null}
                  </div>
                  <div>
                    <div className="flex flex-wrap items-start justify-between gap-6">
                      <div className="max-w-3xl"><Kicker>Relationship Signature</Kicker><h3 className="mt-2 text-[2rem] font-medium leading-[1.08] tracking-[-0.04em] text-zinc-900" style={serifStyle}>{signature.title}</h3><p className="mt-3 max-w-3xl text-[1rem] italic leading-[1.7] text-zinc-600" style={serifStyle}>"{signature.body}"</p></div>
                      <div className="min-w-[96px] border-l border-zinc-200 pl-5 text-right"><Kicker>Overall</Kicker><div className={`mt-2 text-[2.1rem] font-medium leading-none tracking-[-0.06em] ${scoreColor(overall?.polarity)}`} style={serifStyle}>{overallPct}%</div></div>
                    </div>
                    <div className="mt-8 grid gap-5 border-t border-zinc-200 pt-5 md:grid-cols-3">
                      {[
                        ['Ease', overallComponents?.compatibility, false],
                        ['Bond', overallComponents?.binding, false],
                        ['Growth', overallComponents?.growth, false],
                      ].map(([label, value, negative]) => { const tone = metricTone(value, negative); return <div key={label}><Kicker>{label}</Kicker><div className="mt-2 flex items-end justify-between gap-3"><div className={`text-[1.35rem] font-medium tracking-[-0.03em] ${tone.textClass}`} style={serifStyle}>{tone.label}</div><div className="text-[13px] font-semibold text-zinc-700" style={monoStyle}>{Math.max(0, Math.min(100, Number(value || 0))).toFixed(0)}</div></div><div className="mt-2 h-[2px] bg-zinc-200"><div className={`h-full ${tone.lineClass}`} style={{ width: `${Math.max(0, Math.min(100, Number(value || 0)))}%` }} /></div></div>; })}
                    </div>
                    <div className="mt-8 grid gap-8 border-t border-zinc-200 pt-5 lg:grid-cols-2">
                      <EvidenceColumn title="What holds it together" items={supportiveLinks.slice(0, 4)} emptyText="No clear supportive pattern rose above the current threshold." start={1} />
                      <EvidenceColumn title="What creates strain" items={challengingLinks.slice(0, 4)} emptyText="No major pressure pattern rose above the current threshold." negative start={(supportiveLinks?.length || 0) + 1} />
                    </div>
                    {(summaryLines.length || summary?.supportive_link_count || summary?.challenging_link_count || summary?.mutual_reception_count) ? <details className="mt-8 border-t border-zinc-200 pt-4"><summary className="cursor-pointer list-none text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-600" style={monoStyle}>Why this score</summary><div className="mt-4 space-y-4"><div className="grid gap-3 text-sm text-zinc-600 md:grid-cols-4"><div>supportive links: {Number(summary?.supportive_link_count || 0)}</div><div>challenging links: {Number(summary?.challenging_link_count || 0)}</div><div>mutual receptions: {Number(summary?.mutual_reception_count || 0)}</div><div>pressure: {Number(overallComponents?.challenge || 0).toFixed(1)}</div></div>{summaryLines.length ? <ul className="space-y-2 text-sm leading-relaxed text-zinc-600">{summaryLines.map((line, idx) => <li key={`summary-${idx}`} className="border-b border-zinc-100 pb-2 last:border-b-0">{line}</li>)}</ul> : null}</div></details> : null}
                  </div>
                </div>
              </MemoSection>

              <MemoSection number="II" title="Dimension scores">
                {dimensions.length ? dimensions.map((item) => {
                  const pct = Math.round(Math.min(100, Math.max(0, Number(item?.score || 0))));
                  const tone = metricTone(pct, String(item?.polarity || '').toLowerCase() === 'negative');
                  const evidenceItems = Array.isArray(item?.evidence_items) ? item.evidence_items.slice(0, 2) : [];
                  return <div key={item?.id || item?.name} className="border-b border-zinc-100 py-4 last:border-b-0"><div className="grid gap-4 md:grid-cols-[minmax(0,1.2fr)_120px_120px]"><div><div className="text-[1.05rem] font-semibold tracking-[-0.02em] text-zinc-900">{item?.name || item?.id || 'Dimension'}</div>{item?.description ? <div className="mt-1 text-sm leading-relaxed text-zinc-600">{item.description}</div> : null}{evidenceItems.length ? <div className="mt-3 space-y-1.5 text-[12px] leading-relaxed text-zinc-500">{evidenceItems.map((entry, idx) => <div key={`${item?.id || item?.name}-evidence-${idx}`}>{entry?.detail}</div>)}</div> : null}</div><div><Kicker>Score</Kicker><div className="mt-2 text-[2rem] font-semibold leading-none tracking-[-0.04em] text-zinc-900">{pct}</div><div className={`mt-1 text-[11px] uppercase tracking-[0.16em] ${tone.textClass}`} style={monoStyle}>{tone.label}</div></div><div><Kicker>Raw</Kicker><div className="mt-2 text-lg font-semibold text-zinc-800">{Number(item?.raw_score || 0).toFixed(1)}</div><div className="mt-1 text-[11px] uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>{String(item?.polarity || 'neutral')}</div></div></div><div className="mt-3 h-[2px] bg-zinc-100"><div className={`h-full ${tone.lineClass}`} style={{ width: `${pct}%` }} /></div></div>;
                }) : <div className="text-sm text-zinc-500">No secondary dimensions were returned for this comparison.</div>}
              </MemoSection>

              <MemoSection number="III" title="Evidence">
                <div className="grid gap-8 lg:grid-cols-2">
                  <EvidenceColumn title="What holds it together" items={supportiveLinks} emptyText="No supportive links rose above the current threshold." start={1} />
                  <EvidenceColumn title="What creates strain" items={challengingLinks} emptyText="No major challenge links rose above the current threshold." negative start={(supportiveLinks?.length || 0) + 1} />
                </div>
              </MemoSection>

              <MemoSection number="IV" title="House overlays">
                <div className="grid gap-8 lg:grid-cols-2">
                  <OverlayColumn title={`${chartALabel} in ${chartBLabel}`} items={overlays?.a_in_b} emptyText="No clear house overlays were extracted." />
                  <OverlayColumn title={`${chartBLabel} in ${chartALabel}`} items={overlays?.b_in_a} emptyText="No clear house overlays were extracted." />
                </div>
              </MemoSection>

              <MemoSection number="V" title="Model & pressure">
                <div className="grid gap-8 lg:grid-cols-3">
                  <div><Kicker>Pressure</Kicker><div className={`mt-2 text-[1.5rem] font-semibold tracking-[-0.02em] ${pressureTone.textClass}`}>{pressureTone.label}</div><div className="mt-2 text-[13px] text-zinc-600" style={monoStyle}>{Number(overallComponents?.challenge || 0).toFixed(1)} / 100</div></div>
                  <div><Kicker>Balance</Kicker><div className="mt-2 text-[2rem] font-semibold tracking-[-0.04em] text-zinc-900">{Number(overallComponents?.support_balance || 0).toFixed(1)}</div><div className="mt-2 text-sm text-zinc-500">reception bonus {Number(overallComponents?.reception_bonus || 0).toFixed(1)}</div></div>
                  <div><Kicker>Scope Snapshot</Kicker><div className="mt-2 space-y-1.5 text-sm text-zinc-700"><div>Modern planets / <span className="text-zinc-500">{includeModern ? 'on' : 'off'}</span></div><div>Nodes / <span className="text-zinc-500">{includeNodes ? 'on' : 'off'}</span></div><div>Chiron / <span className="text-zinc-500">{includeChiron ? 'on' : 'off'}</span></div><div>Orb profile / <span className="text-zinc-500">{String(governance?.orb_profile || orbProfile)}</span></div><div>Catalog / <span className="text-zinc-500">{governance?.catalog_version || 'unknown'}</span></div></div></div>
                </div>
              </MemoSection>
            </div>
          )) : null}
        </div>
      </div>
    </div>
  );
}
