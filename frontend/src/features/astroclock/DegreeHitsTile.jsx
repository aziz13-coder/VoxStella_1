import React from 'react';

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';

function HitBadge({ type }){
  const map = { planet: 'pl', angle: 'ang', cusp: 'cusp', part: 'lot' };
  const label = map[type] || type || 'hit';
  return <span className="px-1 py-0.5 rounded border border-zinc-200 text-[10px] text-zinc-700">{label}</span>;
}

export default function DegreeHitsTile({ metrics, specialDegrees, onApplyDegrees, onClearDegrees }){
  const items = (metrics?.degree_hits?.items || []).slice(0, 6);
  const [input, setInput] = React.useState(() => (Array.isArray(specialDegrees) && specialDegrees.length ? specialDegrees.join(', ') : ''));
  React.useEffect(() => {
    setInput(Array.isArray(specialDegrees) && specialDegrees.length ? specialDegrees.join(', ') : '');
  }, [Array.isArray(specialDegrees) ? specialDegrees.join('|') : '']);
  return (
    <div className={`${panelCls} aspect-square flex flex-col`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">Degree Hits</h3>
      </div>
      <div className="mb-2 flex items-center gap-2">
        <input
          value={input}
          onChange={e=> setInput(e.target.value)}
          placeholder="e.g., 25 59 Leo, Leo 21 15"
          className="text-[12px] px-3 py-1.5 border border-zinc-300 rounded-full w-full focus:outline-none focus:ring-1 focus:ring-zinc-300"
        />
        <button
          className="text-[11px] px-3 py-1 border border-zinc-300 rounded-full hover:bg-zinc-50 whitespace-nowrap"
          onClick={() => {
            const tokens = (input || '')
              .split(',')
              .map(s=> s.trim())
              .filter(Boolean);
            onApplyDegrees?.(tokens);
          }}
        >Apply</button>
        <button
          className="text-[11px] px-3 py-1 border border-zinc-300 rounded-full hover:bg-zinc-50 whitespace-nowrap"
          onClick={() => { setInput(''); onClearDegrees?.(); }}
        >Clear</button>
      </div>
      <div className="mb-2 text-[11px] text-zinc-500">Accepts sign-first or sign-last degrees, with optional minutes.</div>
      <div className="text-sm space-y-2 overflow-auto flex-1 pr-1">
        {items.length === 0 ? (
          <div className="text-sm text-zinc-500">No special degree hits.</div>
        ) : items.map((d, idx) => (
          <div key={idx} className="border border-zinc-200 rounded p-2">
            <div className="flex items-center justify-between">
              <div className="font-medium">{d.degree}</div>
              <div className="text-[11px] text-zinc-600">x{d.stack_factor} · hits {d.count}</div>
            </div>
            <div className="mt-1 flex items-center gap-2 text-[11px] text-zinc-600">
              <span className={`px-1 rounded border ${d.midpoint_active? 'bg-indigo-100 text-indigo-800 border-indigo-200':'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>{d.midpoint_active? 'midpoint':'—'}</span>
            </div>
            {Array.isArray(d.hits) && d.hits.length ? (
              <div className="mt-2 grid grid-cols-2 gap-1">
                {d.hits.slice(0,6).map((h,i)=> (
                  <div key={i} className="text-[11px] flex items-center justify-between">
                    <span className="truncate">
                      <HitBadge type={h.type} />
                      <span className="ml-1">{h.target}</span>
                    </span>
                    <span className="text-zinc-500">{(h.orb!=null)? `${Number(h.orb).toFixed(2)}°` : '—'}</span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
