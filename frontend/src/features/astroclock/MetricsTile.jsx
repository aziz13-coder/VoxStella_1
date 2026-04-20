import React, { useMemo } from 'react';

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';

const SeverityPill = ({ s }) => {
  const txt = String(s||'').toLowerCase();
  const cls = txt === 'severe' ? 'bg-rose-100 text-rose-800 border-rose-200'
            : txt === 'moderate' ? 'bg-amber-100 text-amber-800 border-amber-200'
            : 'bg-zinc-100 text-zinc-700 border-zinc-200';
  const label = txt ? txt[0].toUpperCase() + txt.slice(1) : '—';
  return <span className={`px-1.5 py-0.5 rounded-full text-[11px] border ${cls}`}>{label}</span>;
};

function BarRow({ label, value, total, color='bg-zinc-900' }){
  const pct = useMemo(()=> {
    const v = Number(value)||0; const t = Number(total)||0; if (t<=0) return 0; return Math.max(0, Math.min(100, (v/t)*100));
  }, [value, total]);
  return (
    <div>
      <div className="flex items-center justify-between text-[11px] text-zinc-600"><span>{label}</span><span>{Math.round(pct)}%</span></div>
      <div className="h-2 rounded-full bg-zinc-200 overflow-hidden"><div className={`h-full ${color}`} style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

export default function MetricsTile({ metrics, specialDegrees }){
  if (!metrics) return (
    <div className={panelCls}>
      <div className="flex items-center justify-between mb-2"><h3 className="font-semibold text-sm">Influence & Afflictions</h3></div>
      <div className="text-sm text-zinc-500">No metrics available.</div>
    </div>
  );

  const el = metrics.element_balance || { Fire:0, Earth:0, Air:0, Water:0 };
  const mod = metrics.modality_balance || { Cardinal:0, Fixed:0, Mutable:0 };
  const totalEl = (el.Fire||0)+(el.Earth||0)+(el.Air||0)+(el.Water||0);
  const totalMod = (mod.Cardinal||0)+(mod.Fixed||0)+(mod.Mutable||0);

  const angleAspects = Array.isArray(metrics.angle_aspects) ? metrics.angle_aspects : [];
  const severeAngles = angleAspects.filter(a=> a.afflicting && a.severity==='severe').slice(0,3);
  const modAngles = angleAspects.filter(a=> a.afflicting && a.severity==='moderate').slice(0,3);
  const planetAspects = Array.isArray(metrics.planetary_aspects) ? metrics.planetary_aspects : [];
  const severePlan = planetAspects.filter(a=> a.afflicting && a.severity==='severe').slice(0,3);

  const degreeItems = (metrics.degree_hits?.items || []).slice(0,4);

  return (
    <div className={panelCls}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">Influence & Afflictions</h3>
        {specialDegrees?.length ? (<div className="text-[11px] text-zinc-600">{specialDegrees.join(' · ')}</div>) : null}
      </div>

      {/* Element & Modality */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-xs font-medium mb-1">Element Balance</div>
          <div className="space-y-1.5">
            <BarRow label="Fire" value={el.Fire} total={totalEl} color="bg-orange-500" />
            <BarRow label="Earth" value={el.Earth} total={totalEl} color="bg-emerald-600" />
            <BarRow label="Air" value={el.Air} total={totalEl} color="bg-sky-600" />
            <BarRow label="Water" value={el.Water} total={totalEl} color="bg-indigo-600" />
          </div>
        </div>
        <div>
          <div className="text-xs font-medium mb-1">Modality</div>
          <div className="space-y-1.5">
            <BarRow label="Cardinal" value={mod.Cardinal} total={totalMod} color="bg-zinc-900" />
            <BarRow label="Fixed" value={mod.Fixed} total={totalMod} color="bg-zinc-700" />
            <BarRow label="Mutable" value={mod.Mutable} total={totalMod} color="bg-zinc-500" />
          </div>
        </div>
      </div>

      {/* Afflictions */}
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <div className="text-xs font-medium mb-1">Angle Afflictions</div>
          {severeAngles.length===0 && modAngles.length===0 ? (
            <div className="text-xs text-zinc-500">None</div>
          ) : (
            <ul className="space-y-1 text-xs">
              {[...severeAngles, ...modAngles].map((a, idx)=> (
                <li key={idx} className="flex items-center justify-between">
                  <span>{a.planet} {a.aspect} {a.angle}</span>
                  <span className="flex items-center gap-2"><span className="text-zinc-500">{a.orb?.toFixed?.(2)}°</span><SeverityPill s={a.severity} /></span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <div className="text-xs font-medium mb-1">Planet Afflictions</div>
          {severePlan.length===0 ? (
            <div className="text-xs text-zinc-500">None</div>
          ) : (
            <ul className="space-y-1 text-xs">
              {severePlan.map((a, idx)=> (
                <li key={idx} className="flex items-center justify-between">
                  <span>{a.planet1} {a.aspect} {a.planet2}</span>
                  <span className="flex items-center gap-2"><span className="text-zinc-500">{a.orb?.toFixed?.(2)}°</span><SeverityPill s={a.severity} /></span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Degree Hits moved to its own tile */}
    </div>
  );
}
