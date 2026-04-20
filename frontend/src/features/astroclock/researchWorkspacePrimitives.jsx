import React from 'react';

const RESEARCH_ACCENTS = {
  default: {
    line: '#2563eb',
    ink: '#1d4ed8',
    soft: 'rgba(37, 99, 235, 0.08)',
    border: 'rgba(37, 99, 235, 0.22)',
  },
  astrocartography: {
    line: '#2563eb',
    ink: '#1e40af',
    soft: 'rgba(37, 99, 235, 0.08)',
    border: 'rgba(37, 99, 235, 0.22)',
  },
  mundane: {
    line: '#5b52d6',
    ink: '#4338ca',
    soft: 'rgba(91, 82, 214, 0.08)',
    border: 'rgba(91, 82, 214, 0.22)',
  },
  weather: {
    line: '#0f8f99',
    ink: '#0f6f7b',
    soft: 'rgba(15, 143, 153, 0.08)',
    border: 'rgba(15, 143, 153, 0.22)',
  },
};

export function getResearchAccent(moduleName = 'default') {
  return RESEARCH_ACCENTS[moduleName] || RESEARCH_ACCENTS.default;
}

export function toneBadgeClass(tone) {
  if (tone === 'good') return 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-200';
  if (tone === 'warning') return 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-200';
  if (tone === 'danger') return 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-200';
  if (tone === 'accent') return 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/25 dark:bg-sky-500/10 dark:text-sky-200';
  return 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-200';
}

export const researchWorkspaceCls = {
  shellSurfaceCls: 'border-t-2 border-slate-900 bg-[#f7f4ed] dark:border-slate-50 dark:bg-slate-950',
  railCardCls: 'rounded-[4px] border border-slate-200/90 bg-white/96 shadow-none backdrop-blur-xl dark:border-slate-700/90 dark:bg-slate-900/90',
  sectionCardCls: 'rounded-[4px] border border-slate-200/90 bg-white/96 p-4 shadow-none dark:border-slate-700/90 dark:bg-slate-900/88',
  nestedCardCls: 'rounded-[3px] border border-slate-200/85 bg-slate-50/86 p-3.5 shadow-none dark:border-slate-700/80 dark:bg-slate-900/38',
  emptyStateCls: 'rounded-[4px] border border-slate-200/85 bg-white/84 p-6 dark:border-slate-700/85 dark:bg-slate-900/35',
  sectionBandCls: 'rounded-[4px] border border-slate-200/85 bg-slate-50/84 px-4 py-3 dark:border-slate-700/80 dark:bg-slate-900/38',
  headerBandCls: 'border-b border-slate-200/85 pb-3 dark:border-slate-700/80',
  mutedPanelCls: 'rounded-[4px] border border-slate-200/85 bg-slate-50/78 p-4 dark:border-slate-700/85 dark:bg-slate-900/34',
  inputCls: 'w-full rounded-[3px] border border-slate-200/90 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-none outline-none transition focus:border-sky-300 focus:ring-4 focus:ring-sky-100 dark:border-slate-700 dark:bg-slate-950/45 dark:text-slate-100 dark:focus:border-sky-500 dark:focus:ring-sky-500/15',
  actionButtonCls: 'rounded-[3px] border border-slate-300 bg-white px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-700 shadow-none hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900/45 dark:text-slate-100 dark:hover:bg-slate-900/70',
  secondaryActionButtonCls: 'rounded-[3px] border border-slate-300 bg-white px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-700 shadow-none hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900/45 dark:text-slate-100 dark:hover:bg-slate-900/70',
  primaryActionButtonCls: 'rounded-[3px] border border-slate-900 bg-slate-900 px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-white shadow-none hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-50 dark:bg-slate-50 dark:text-slate-900 dark:hover:bg-slate-200',
  commandBandCls: 'rounded-[4px] border border-slate-200/90 bg-slate-50/92 px-4 py-3 dark:border-slate-700/90 dark:bg-slate-900/45',
  kpiStripCls: 'overflow-hidden rounded-[4px] border border-slate-200/90 bg-white/96 dark:border-slate-700/90 dark:bg-slate-900/88',
  tableFrameCls: 'overflow-hidden rounded-[4px] border border-slate-200/90 bg-white/96 dark:border-slate-700/90 dark:bg-slate-900/88',
  inspectorPanelCls: 'rounded-[4px] border-l border-slate-200/90 bg-white/96 dark:border-slate-700/90 dark:bg-slate-900/88',
};

export function ResearchSectionIntro({
  eyebrow,
  title,
  body,
  actions = null,
  banded = false,
  bracketed = false,
  module = 'default',
}) {
  const accent = getResearchAccent(module);
  return (
    <div className={banded ? researchWorkspaceCls.sectionBandCls : undefined}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          {eyebrow ? (
            bracketed ? (
              <ConsoleBracketEyebrow module={module}>{eyebrow}</ConsoleBracketEyebrow>
            ) : (
              <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em]" style={{ color: accent.ink }}>
                {eyebrow}
              </div>
            )
          ) : null}
          <h4 className={`${eyebrow ? 'mt-2' : ''} text-[1.05rem] font-semibold tracking-[-0.02em] text-slate-900 dark:text-slate-50`}>
            {title}
          </h4>
          {body ? <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">{body}</p> : null}
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </div>
    </div>
  );
}

export function ResearchMetricPill({ label, value, tone = 'default' }) {
  return (
    <div className={`min-h-[74px] rounded-[4px] border px-3.5 py-3 text-sm ${toneBadgeClass(tone)}`}>
      <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] opacity-75">{label}</div>
      <div className="mt-2 text-[1.15rem] font-semibold leading-tight tracking-[-0.02em]">{value}</div>
    </div>
  );
}

export function ResearchSegmentedToggle({
  options,
  value,
  onChange,
  containerClassName = 'inline-flex rounded-[4px] border border-slate-200 bg-slate-50/90 p-1 dark:border-slate-700 dark:bg-slate-900/35',
  buttonClassName = 'rounded-[3px] px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] transition',
  activeClassName = 'bg-slate-900 text-white shadow-none dark:bg-slate-50 dark:text-slate-900',
  inactiveClassName = 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100',
}) {
  const rows = Array.isArray(options) ? options.filter(Boolean) : [];
  return (
    <div className={containerClassName}>
      {rows.map((option) => {
        const active = value === option.id;
        return (
          <button
            key={option.id}
            type="button"
            onClick={() => onChange(option.id)}
            className={`${buttonClassName} ${active ? activeClassName : inactiveClassName}`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function ResearchQuickChoiceChips({
  items,
  value,
  onChange,
  activeClassName = 'border-slate-900 bg-slate-900 text-white dark:border-slate-50 dark:bg-slate-50 dark:text-slate-900',
  inactiveClassName = 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-950/30 dark:text-slate-300 dark:hover:text-slate-100',
}) {
  const rows = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!rows.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {rows.map((item) => {
        const active = value === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onChange(item.id)}
            className={`rounded-[3px] border px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] transition ${active ? activeClassName : inactiveClassName}`}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

export function ResearchSummaryBand({ items }) {
  const rows = Array.isArray(items) ? items.filter((item) => item?.value) : [];
  if (!rows.length) return null;
  return (
    <section className={researchWorkspaceCls.commandBandCls}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {rows.map((item, index) => (
          <React.Fragment key={`${item.label}-${item.value}`}>
            {index ? <span className="font-mono text-[10px] text-slate-300 dark:text-slate-600">/</span> : null}
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{item.label}</span>
              <span className="text-sm font-medium text-slate-900 dark:text-slate-50">{item.value}</span>
            </div>
          </React.Fragment>
        ))}
      </div>
    </section>
  );
}

export function ConsoleBracketEyebrow({ children, module = 'default', className = '' }) {
  const accent = getResearchAccent(module);
  return (
    <div className={`font-mono text-[10px] font-semibold uppercase tracking-[0.18em] ${className}`} style={{ color: accent.ink }}>
      <span className="text-slate-400">[</span> {children} <span className="text-slate-400">]</span>
    </div>
  );
}

export function ConsoleStatusBadge({ label, tone = 'default' }) {
  return (
    <span className={`inline-flex rounded-full border px-3 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] ${toneBadgeClass(tone)}`}>
      {label}
    </span>
  );
}

export function ConsoleModeTabs({ options, value, onChange, wrap = false, fullWidth = false }) {
  const optionCount = Array.isArray(options) ? options.filter(Boolean).length : 0;
  const fullWidthGridCols = {
    0: 'grid-cols-1',
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-2 sm:grid-cols-3',
    4: 'grid-cols-2 sm:grid-cols-4',
  }[Math.min(optionCount, 4)] || 'grid-cols-2 sm:grid-cols-4';
  const containerClassName = wrap
    ? `${fullWidth ? `grid w-full max-w-full ${fullWidthGridCols}` : 'flex max-w-full flex-wrap'} gap-1 rounded-[4px] border border-slate-200 bg-slate-50/90 p-1 dark:border-slate-700 dark:bg-slate-900/35`
    : 'inline-flex rounded-[4px] border border-slate-200 bg-slate-50/90 p-1 dark:border-slate-700 dark:bg-slate-900/35';
  const buttonClassName = wrap
    ? 'inline-flex min-h-[40px] min-w-0 items-center justify-center rounded-[3px] px-3 py-1.5 text-center font-mono text-[10px] font-semibold uppercase tracking-[0.16em] leading-tight transition whitespace-normal'
    : 'rounded-[3px] px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] transition';
  return (
    <ResearchSegmentedToggle
      options={options}
      value={value}
      onChange={onChange}
      containerClassName={containerClassName}
      buttonClassName={buttonClassName}
      activeClassName="bg-slate-900 text-white dark:bg-slate-50 dark:text-slate-900"
      inactiveClassName="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
    />
  );
}

export function ConsoleCommandBand({
  items,
  module = 'default',
  statusLabel,
  statusTone = 'default',
  actionLabel,
  onAction,
  trailing = null,
}) {
  const rows = Array.isArray(items) ? items.filter((item) => item?.value) : [];
  return (
    <section className={researchWorkspaceCls.commandBandCls}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {statusLabel ? <ConsoleStatusBadge label={statusLabel} tone={statusTone} /> : null}
        {rows.map((item, index) => (
          <React.Fragment key={`${item.label}-${item.value}`}>
            {index || statusLabel ? <span className="font-mono text-[10px] text-slate-300 dark:text-slate-600">/</span> : null}
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{item.label}</span>
              <span className="text-sm font-medium text-slate-900 dark:text-slate-50">{item.value}</span>
            </div>
          </React.Fragment>
        ))}
        <div className="flex-1" />
        {trailing}
        {actionLabel && typeof onAction === 'function' ? (
          <button
            type="button"
            onClick={onAction}
            className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600 underline underline-offset-4 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-50"
          >
            {actionLabel}
          </button>
        ) : null}
      </div>
    </section>
  );
}

export function ConsoleKpiStrip({ metrics, module = 'default' }) {
  const accent = getResearchAccent(module);
  const rows = Array.isArray(metrics) ? metrics.filter(Boolean) : [];
  const mediumGridClass = {
    1: 'md:grid-cols-1',
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-3',
    4: 'md:grid-cols-4',
  }[Math.min(rows.length, 4)] || 'md:grid-cols-4';
  if (!rows.length) return null;
  return (
    <section className={researchWorkspaceCls.kpiStripCls}>
      <div className={`grid grid-cols-2 ${rows.length > 4 ? 'lg:grid-cols-6 md:grid-cols-3' : mediumGridClass}`}>
        {rows.map((metric, index) => (
          <div
            key={`${metric.label}-${metric.value}-${index}`}
            className={`px-4 py-4 ${index < rows.length - 1 ? 'border-b border-slate-200/80 md:border-b-0 md:border-r dark:border-slate-700/80' : ''}`}
          >
            <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
              {metric.label}
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <div className="text-[1.35rem] font-semibold leading-none tracking-[-0.03em]" style={{ color: metric.toneColor || '#0f172a' }}>
                {metric.value}
              </div>
              {metric.unit ? <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-400 dark:text-slate-500">{metric.unit}</div> : null}
            </div>
            {metric.hint ? <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">{metric.hint}</div> : null}
            {metric.bar != null ? (
              <div className="mt-3 h-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.max(0, Math.min(100, Number(metric.bar) || 0))}%`,
                    background: metric.barColor || accent.line,
                  }}
                />
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

export function ConsoleSectionBar({ label, right = null, module = 'default' }) {
  return (
    <div className="flex items-center gap-3 px-1 py-3">
      <ConsoleBracketEyebrow module={module}>{label}</ConsoleBracketEyebrow>
      <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
      {right}
    </div>
  );
}

export function ConsoleRailSection({
  title,
  eyebrow = 'setup',
  detail = '',
  module = 'default',
  headerRight = null,
  className = '',
  bodyClassName = 'mt-3 space-y-2',
  children,
}) {
  return (
    <section className={`${researchWorkspaceCls.mutedPanelCls} ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <ConsoleBracketEyebrow module={module}>{eyebrow}</ConsoleBracketEyebrow>
          <h4 className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-50">{title}</h4>
          {detail ? <p className="mt-2 text-[11px] leading-5 text-slate-600 dark:text-slate-300">{detail}</p> : null}
        </div>
        {headerRight ? <div className="shrink-0">{headerRight}</div> : null}
      </div>
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

export function ConsoleDataRow({
  label,
  value,
  mono = false,
  strong = false,
  hint = '',
  tone = 'default',
  className = '',
}) {
  const accent = getResearchAccent(tone === 'default' ? 'default' : tone);
  const textColor = tone === 'default' ? 'text-slate-800 dark:text-slate-100' : undefined;
  return (
    <div className={`flex items-baseline justify-between gap-4 border-b border-slate-100 py-2.5 last:border-b-0 dark:border-slate-800 ${className}`}>
      <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">{label}</div>
      <div className={`min-w-0 text-right ${mono ? 'font-mono text-[12px]' : 'text-sm'} ${strong ? 'font-semibold' : 'font-medium'} ${textColor || ''}`} style={tone !== 'default' ? { color: accent.ink } : undefined}>
        {value}
        {hint ? <span className="ml-2 text-[11px] font-normal text-slate-400 dark:text-slate-500">{hint}</span> : null}
      </div>
    </div>
  );
}

export function ConsoleEmptyState({ title, detail = '', module = 'default' }) {
  return (
    <section className={researchWorkspaceCls.emptyStateCls}>
      <ConsoleBracketEyebrow module={module}>waiting</ConsoleBracketEyebrow>
      <h4 className="mt-3 text-base font-semibold text-slate-900 dark:text-slate-50">{title}</h4>
      {detail ? <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{detail}</p> : null}
    </section>
  );
}
