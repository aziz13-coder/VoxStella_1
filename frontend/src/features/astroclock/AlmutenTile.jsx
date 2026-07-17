import React from 'react';

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';
const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };

const DIGNITY_LABELS = {
  domicile: 'Domicile',
  exaltation: 'Exaltation',
  triplicity: 'Triplicity',
  term: 'Term',
  face: 'Face',
};

const BREAKDOWN_ORDER = ['domicile', 'exaltation', 'triplicity', 'term', 'face'];
const POINT_LABEL_ALIASES = {
  Ascendant: 'Asc',
  Midheaven: 'Mid',
};

function formatDegreeInSign(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const degrees = Math.floor(numeric);
  const minutes = Math.floor((numeric - degrees) * 60);
  return `${degrees}°${String(minutes).padStart(2, '0')}'`;
}

function formatPointLabel(value) {
  const label = String(value || '').trim();
  if (!label) return 'Point';
  return POINT_LABEL_ALIASES[label] || label;
}

function formatBreakdownChips(breakdown) {
  if (!breakdown || typeof breakdown !== 'object') return [];
  return BREAKDOWN_ORDER
    .filter((key) => Number(breakdown[key]) > 0)
    .map((key) => `${DIGNITY_LABELS[key] || key} +${Number(breakdown[key])}`);
}

export default function AlmutenTile({ almutens }) {
  const items = Array.isArray(almutens?.items) ? almutens.items : [];
  const sect = typeof almutens?.sect === 'string' ? almutens.sect : null;
  const ascItem = items.find((item) => String(item?.label || '').toLowerCase() === 'ascendant') || items[0] || null;
  const mcItem = items.find((item) => String(item?.label || '').toLowerCase() === 'midheaven') || null;
  const remaining = items.filter((item) => item !== ascItem && item !== mcItem);
  const orderedItems = [ascItem, mcItem, ...remaining].filter(Boolean);

  const leaderLabel = (item) => {
    const leaders = Array.isArray(item?.leaders) && item.leaders.length
      ? item.leaders.filter(Boolean)
      : (item?.leader ? [item.leader] : []);
    return leaders.length ? leaders.join(' / ') : 'No leader';
  };

  return (
    <div className={`${panelCls} flex min-h-[21rem] flex-col md:min-h-[26rem] lg:min-h-[29rem]`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
            Dignity Summary
          </div>
          <h3 className="mt-1 font-semibold text-sm">Almuten</h3>
        </div>
        {sect ? (
          <div className="rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
            {sect} sect
          </div>
        ) : null}
      </div>

      <div className="mt-3 astro-scroll-shell min-h-0 flex-1">
        <div className="astro-scroll">
          {!orderedItems.length ? (
            <div className="text-sm text-zinc-500">No almuten data available.</div>
          ) : (
            <div className="divide-y divide-zinc-100">
              {orderedItems.map((item, index) => {
                const breakdown = formatBreakdownChips(item?.leader_breakdown);
                const isPrimary = index === 0;
                return (
                  <div key={item?.key || item?.label || index} className={`${index === 0 ? 'pt-0' : 'pt-3'} pb-3 last:pb-0`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                          <span>Almuten of </span>
                          <span>{formatPointLabel(item?.label)}</span>
                        </div>
                        <div className={`mt-1 leading-tight text-zinc-900 ${isPrimary ? 'text-[1.05rem]' : 'text-[15px]'}`} style={serifStyle}>
                          {leaderLabel(item)}
                        </div>
                        <div className="mt-1 text-[11px] text-zinc-500">
                          {item?.sign || '--'} {formatDegreeInSign(item?.degree_in_sign)}
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <div className={`${isPrimary ? 'text-[1.35rem]' : 'text-[1.05rem]'} leading-none text-zinc-900`} style={serifStyle}>
                          {Number(item?.leader_score || 0)}
                        </div>
                        <div className="mt-1 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>
                          points
                        </div>
                      </div>
                    </div>
                    {breakdown.length ? (
                      <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1 text-[10px] text-zinc-500" style={monoStyle}>
                        {breakdown.map((chip) => (
                          <span key={chip}>{chip}</span>
                        ))}
                      </div>
                    ) : null}
                    {Array.isArray(item?.tied_with) && item.tied_with.length ? (
                      <div className="mt-2 text-[11px] text-zinc-500">Tie with {item.tied_with.join(', ')}</div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
