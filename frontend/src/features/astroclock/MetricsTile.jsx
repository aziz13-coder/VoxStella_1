import React from 'react';

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };
const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };

const ELEMENT_ORDER = ['Fire', 'Earth', 'Air', 'Water'];
const MODALITY_ORDER = ['Cardinal', 'Fixed', 'Mutable'];
const ELEMENT_META = {
  Fire: { barClass: 'bg-orange-600', textClass: 'text-orange-700' },
  Earth: { barClass: 'bg-emerald-700', textClass: 'text-emerald-700' },
  Air: { barClass: 'bg-sky-700', textClass: 'text-sky-700' },
  Water: { barClass: 'bg-indigo-700', textClass: 'text-indigo-700' },
};
const MODALITY_META = {
  Cardinal: { barClass: 'bg-zinc-900', textClass: 'text-zinc-900' },
  Fixed: { barClass: 'bg-zinc-700', textClass: 'text-zinc-700' },
  Mutable: { barClass: 'bg-zinc-500', textClass: 'text-zinc-600' },
};

const SEGMENT_SHORT_LABELS = {
  Fire: 'Fire',
  Earth: 'Earth',
  Air: 'Air',
  Water: 'Wat.',
  Cardinal: 'Card.',
  Fixed: 'Fixed',
  Mutable: 'Mut.',
};

function severityRank(severity) {
  const raw = String(severity || '').toLowerCase();
  if (raw === 'severe') return 3;
  if (raw === 'moderate') return 2;
  if (raw === 'light' || raw === 'minor') return 1;
  return 0;
}

function formatAfflictionOrb(orb) {
  const value = Number(orb);
  if (!Number.isFinite(value)) return '-0.00\u00B0';
  return `-${Math.abs(value).toFixed(2)}\u00B0`;
}

function joinNames(names) {
  if (!names.length) return '';
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return `${names.slice(0, -1).join(', ')}, and ${names[names.length - 1]}`;
}

function formatBalanceValue(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '0';
  if (Math.abs(numeric - Math.round(numeric)) < 0.001) return String(Math.round(numeric));
  return numeric.toFixed(1);
}

function getSegmentDisplayLabel(segment) {
  const valueText = formatBalanceValue(segment?.value);
  const fullLabel = `${segment?.label || ''} ${valueText}`.trim();
  const shortBase = SEGMENT_SHORT_LABELS[segment?.label] || segment?.label || '';
  const shortLabel = `${shortBase} ${valueText}`.trim();
  const pct = Number(segment?.pct || 0);

  if (pct >= 22) return fullLabel;
  if (pct >= 13) return shortLabel;
  if (pct >= 8) return valueText;
  return '';
}

function buildElementSummary(balance) {
  const ranked = ELEMENT_ORDER
    .map((label) => ({ label, value: Number(balance?.[label] || 0) }))
    .sort((a, b) => b.value - a.value);
  const leader = ranked[0];
  const runnerUp = ranked[1];
  const trailing = ranked.filter((item) => item.value > 0 && item.label !== leader?.label && item.label !== runnerUp?.label);

  if (!leader || leader.value <= 0) {
    return {
      lead: null,
      toneKey: null,
      detail: 'No dominant elemental pattern is active yet.',
    };
  }

  if (runnerUp && leader.value === runnerUp.value) {
    return {
      lead: `${leader.label} and ${runnerUp.label} are level`,
      toneKey: null,
      detail: 'The chart reads balanced across the top elements.',
    };
  }

  const trailingLabels = trailing.map((item) => item.label.toLowerCase());
  let detail = runnerUp && runnerUp.value > 0
    ? `${runnerUp.label} runs second.`
    : 'No other element meaningfully registers.';
  if (trailingLabels.length === 1) {
    detail += ` ${trailingLabels[0][0].toUpperCase()}${trailingLabels[0].slice(1)} trails.`;
  } else if (trailingLabels.length > 1) {
    detail += ` ${joinNames(trailingLabels)} trail behind it.`;
  }

  return {
    lead: `${leader.label}-heavy.`,
    toneKey: leader.label,
    detail,
  };
}

function buildModalitySummary(balance) {
  const ranked = MODALITY_ORDER
    .map((label) => ({ label, value: Number(balance?.[label] || 0) }))
    .sort((a, b) => b.value - a.value);
  const leader = ranked[0];
  const runnerUp = ranked[1];

  if (!leader || leader.value <= 0) {
    return {
      lead: null,
      toneKey: null,
      detail: 'No dominant modality is active yet.',
    };
  }

  if (runnerUp && leader.value === runnerUp.value) {
    return {
      lead: `${leader.label} and ${runnerUp.label} are level`,
      toneKey: null,
      detail: 'The chart distributes momentum evenly across the main modes.',
    };
  }

  const trailing = ranked.filter((item) => item.value > 0 && item.label !== leader.label && item.label !== runnerUp?.label);
  let detail = runnerUp && runnerUp.value > 0
    ? `${runnerUp.label} runs second.`
    : 'No other mode meaningfully registers.';
  if (trailing.length === 1) {
    detail += ` ${trailing[0].label} trails behind it.`;
  }

  return {
    lead: `${leader.label}-led.`,
    toneKey: leader.label,
    detail,
  };
}

function summarizeAngleAfflictions(items) {
  if (!items.length) return 'No angular strain is active.';
  const sources = [...new Set(items.map((item) => item?.planet).filter(Boolean))];
  if (!sources.length) return `${items.length} active.`;
  return `${items.length} active - ${joinNames(sources)} pressure the angles.`;
}

function summarizePlanetAfflictions(items) {
  if (!items.length) return 'No planetary pressure is active.';
  const sources = [
    ...new Set(
      items.flatMap((item) => [item?.planet1, item?.planet2]).filter(Boolean),
    ),
  ];
  if (!sources.length) return `${items.length} active.`;
  return `${items.length} active - strongest pressure from ${joinNames(sources)}.`;
}

function SeverityMeter({ severity }) {
  const level = severityRank(severity);
  return (
    <div className="flex items-center gap-1" aria-label={`${Math.max(level, 0)} point severity`}>
      {[0, 1, 2].map((idx) => (
        <span
          key={idx}
          className={`h-3 w-3 rounded-[4px] ${idx < level ? 'bg-rose-600' : 'bg-zinc-200'}`}
        />
      ))}
    </div>
  );
}

function AfflictionList({ title, summary, items, getLabel }) {
  return (
    <div className="border-t border-zinc-100 pt-4">
      <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
        {title}
      </div>
      <div className="mt-1 text-[13px] leading-5 text-zinc-600">{summary}</div>
      {items.length === 0 ? (
        <div className="mt-4 text-sm text-zinc-500">None</div>
      ) : (
        <ul className="mt-4 space-y-1">
          {items.map((item, idx) => (
            <li key={`${title}-${idx}`} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 border-b border-zinc-100 py-2.5 last:border-b-0">
              <span className="min-w-0 text-[15px] leading-6 text-zinc-900">{getLabel(item)}</span>
              <span className="text-[1.5rem] font-medium leading-none tracking-[-0.04em] text-rose-700" style={serifStyle}>
                {formatAfflictionOrb(item?.orb)}
              </span>
              <SeverityMeter severity={item?.severity} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function MetricsTile({ metrics, specialDegrees }) {
  if (!metrics) {
    return (
      <div className={panelCls}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-sm">Influence & Afflictions</h3>
        </div>
        <div className="text-sm text-zinc-500">No metrics available.</div>
      </div>
    );
  }

  const el = metrics.element_balance || { Fire: 0, Earth: 0, Air: 0, Water: 0 };
  const mod = metrics.modality_balance || { Cardinal: 0, Fixed: 0, Mutable: 0 };
  const totalEl = (el.Fire || 0) + (el.Earth || 0) + (el.Air || 0) + (el.Water || 0);
  const totalMod = (mod.Cardinal || 0) + (mod.Fixed || 0) + (mod.Mutable || 0);

  const elementSegments = ELEMENT_ORDER.map((label) => {
    const value = Number(el[label] || 0);
    const pct = totalEl > 0 ? Math.max(0, Math.min(100, (value / totalEl) * 100)) : 0;
    return {
      label,
      value,
      pct,
      ...ELEMENT_META[label],
    };
  });
  const elementSummary = buildElementSummary(el);
  const modalitySegments = MODALITY_ORDER.map((label) => {
    const value = Number(mod[label] || 0);
    const pct = totalMod > 0 ? Math.max(0, Math.min(100, (value / totalMod) * 100)) : 0;
    return {
      label,
      value,
      pct,
      ...MODALITY_META[label],
    };
  });
  const modalitySummary = buildModalitySummary(mod);

  const angleAfflictions = (Array.isArray(metrics.angle_aspects) ? metrics.angle_aspects : [])
    .filter((item) => item?.afflicting)
    .sort((a, b) => severityRank(b?.severity) - severityRank(a?.severity) || Number(a?.orb || 99) - Number(b?.orb || 99))
    .slice(0, 3);

  const planetAfflictions = (Array.isArray(metrics.planetary_aspects) ? metrics.planetary_aspects : [])
    .filter((item) => item?.afflicting)
    .sort((a, b) => severityRank(b?.severity) - severityRank(a?.severity) || Number(a?.orb || 99) - Number(b?.orb || 99))
    .slice(0, 3);

  return (
    <div className={panelCls}>
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-sm">Influence & Afflictions</h3>
        {specialDegrees?.length ? (
          <div className="text-[11px] text-zinc-600">{specialDegrees.join(' | ')}</div>
        ) : null}
      </div>

      <div className="mt-4 space-y-5">
        <div className="rounded-[20px] border border-zinc-200 bg-white px-4 py-4">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(220px,0.9fr)] lg:items-start">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
                Element Balance
              </div>
              {totalEl > 0 ? (
                <>
                  <div className="mt-3 overflow-hidden rounded-full bg-zinc-200">
                    <div className="flex h-4 overflow-hidden rounded-full">
                      {elementSegments.map((segment) => (
                        <div
                          key={segment.label}
                          className={`min-w-0 overflow-hidden flex items-center justify-center px-2 text-[9px] font-semibold uppercase tracking-[0.08em] text-white sm:text-[10px] ${segment.barClass}`}
                          style={{ width: `${segment.pct}%` }}
                          title={`${segment.label}: ${formatBalanceValue(segment.value)}`}
                        >
                          <span className="block min-w-0 truncate">{getSegmentDisplayLabel(segment)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="mt-3 text-[15px] leading-6 text-zinc-700">
                    {elementSummary.lead ? (
                      <span className={ELEMENT_META[elementSummary.toneKey]?.textClass || 'text-zinc-900'} style={serifStyle}>
                        <span className="italic">{elementSummary.lead}</span>{' '}
                      </span>
                    ) : null}
                    <span>{elementSummary.detail}</span>
                  </div>
                </>
              ) : (
                <div className="mt-3 text-sm text-zinc-500">No elemental balance available.</div>
              )}
            </div>

            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
                Modality
              </div>
              {totalMod > 0 ? (
                <>
                  <div className="mt-3 overflow-hidden rounded-full bg-zinc-200">
                    <div className="flex h-4 overflow-hidden rounded-full">
                      {modalitySegments.map((segment) => (
                        <div
                          key={segment.label}
                          className={`min-w-0 overflow-hidden flex items-center justify-center px-2 text-[9px] font-semibold uppercase tracking-[0.08em] text-white sm:text-[10px] ${segment.barClass}`}
                          style={{ width: `${segment.pct}%` }}
                          title={`${segment.label}: ${formatBalanceValue(segment.value)}`}
                        >
                          <span className="block min-w-0 truncate">{getSegmentDisplayLabel(segment)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="mt-3 text-[15px] leading-6 text-zinc-700">
                    {modalitySummary.lead ? (
                      <span className={MODALITY_META[modalitySummary.toneKey]?.textClass || 'text-zinc-900'} style={serifStyle}>
                        <span className="italic">{modalitySummary.lead}</span>{' '}
                      </span>
                    ) : null}
                    <span>{modalitySummary.detail}</span>
                  </div>
                </>
              ) : (
                <div className="mt-3 text-sm text-zinc-500">No modality balance available.</div>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <AfflictionList
            title="Angle Afflictions"
            summary={summarizeAngleAfflictions(angleAfflictions)}
            items={angleAfflictions}
            getLabel={(item) => `${item?.planet || '-'} ${item?.aspect || '-'} ${item?.angle || '-'}`}
          />
          <AfflictionList
            title="Planet Afflictions"
            summary={summarizePlanetAfflictions(planetAfflictions)}
            items={planetAfflictions}
            getLabel={(item) => `${item?.planet1 || '-'} ${item?.aspect || '-'} ${item?.planet2 || '-'}`}
          />
        </div>
      </div>

      {/* Degree hits moved to its own tile */}
    </div>
  );
}
