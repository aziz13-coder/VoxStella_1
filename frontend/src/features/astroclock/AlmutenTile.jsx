import React from 'react';

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';

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
  return `${degrees}\u00B0${String(minutes).padStart(2, '0')}'`;
}

function formatPointLabel(value) {
  const label = String(value || '').trim();
  if (!label) return 'Point';
  return POINT_LABEL_ALIASES[label] || label;
}

function formatBreakdown(breakdown) {
  if (!breakdown || typeof breakdown !== 'object') return '';
  return BREAKDOWN_ORDER
    .filter((key) => Number(breakdown[key]) > 0)
    .map((key) => `${DIGNITY_LABELS[key] || key} ${Number(breakdown[key])}`)
    .join(' | ');
}

export default function AlmutenTile({ almutens }) {
  const items = Array.isArray(almutens?.items) ? almutens.items : [];
  const sect = typeof almutens?.sect === 'string' ? almutens.sect : null;

  return (
    <div className={`${panelCls} aspect-square flex flex-col`}>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h3 className="font-semibold text-sm">Almuten</h3>
        {sect ? <div className="text-[11px] text-zinc-500">{sect} sect</div> : null}
      </div>
      <div className="astro-scroll-shell flex-1">
        <div className="astro-scroll">
          {items.length === 0 ? (
            <div className="text-sm text-zinc-500">No almuten data available.</div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => {
                const leaders = Array.isArray(item?.leaders) && item.leaders.length
                  ? item.leaders.filter(Boolean)
                  : (item?.leader ? [item.leader] : []);
                const breakdown = formatBreakdown(item?.leader_breakdown);
                const tiedWith = Array.isArray(item?.tied_with) ? item.tied_with.filter(Boolean) : [];

                return (
                  <div key={item?.key || item?.label} className="border-b border-zinc-100 pb-2 last:border-0 last:pb-0">
                    <div className="grid grid-cols-12 items-start gap-2">
                      <div className="col-span-4">
                        <div className="font-medium text-sm text-zinc-900">{formatPointLabel(item?.label)}</div>
                        <div className="text-[11px] text-zinc-500">
                          {item?.sign || '--'} {formatDegreeInSign(item?.degree_in_sign)}
                        </div>
                      </div>
                      <div className="col-span-5">
                        <div className="text-sm text-zinc-800">
                          {leaders.length ? leaders.join(' / ') : 'No leader'}
                        </div>
                        {breakdown ? (
                          <div className="mt-0.5 text-[11px] text-zinc-500">{breakdown}</div>
                        ) : null}
                        {tiedWith.length ? (
                          <div className="mt-0.5 text-[11px] text-zinc-500">Tie with {tiedWith.join(', ')}</div>
                        ) : null}
                      </div>
                      <div className="col-span-3 text-right">
                        <div className="text-sm font-medium text-zinc-800">
                          {Number(item?.leader_score || 0)}
                        </div>
                        <div className="text-[11px] text-zinc-500">points</div>
                      </div>
                    </div>
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
