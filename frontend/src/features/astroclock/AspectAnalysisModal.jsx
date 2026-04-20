import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AstroClockAPI } from './api.mjs';
import { aspectSymbol, dedupeAspectRows, transformDashboard } from './transform.mjs';

const aspectColor = (name) => {
  const k = String(name||'').toLowerCase();
  if (k.includes('conj')) return { bar: 'bg-sky-600', text: 'text-sky-700', pill: 'border-sky-200 bg-sky-50' };
  if (k.includes('opp')) return { bar: 'bg-rose-600', text: 'text-rose-700', pill: 'border-rose-200 bg-rose-50' };
  if (k.includes('square')) return { bar: 'bg-amber-600', text: 'text-amber-700', pill: 'border-amber-200 bg-amber-50' };
  if (k.includes('trine')) return { bar: 'bg-emerald-600', text: 'text-emerald-700', pill: 'border-emerald-200 bg-emerald-50' };
  if (k.includes('sext')) return { bar: 'bg-violet-600', text: 'text-violet-700', pill: 'border-violet-200 bg-violet-50' };
  return { bar: 'bg-zinc-800', text: 'text-zinc-700', pill: 'border-zinc-200 bg-zinc-50' };
};

const PlanetSymbols = { Sun:'\u2609', Moon:'\u263D', Mercury:'\u263F', Venus:'\u2640', Mars:'\u2642', Jupiter:'\u2643', Saturn:'\u2644', Uranus:'\u2645', Neptune:'\u2646', Pluto:'\u2647', 'North Node':'\u260A' };

function exactnessPct(orb, max) {
  const o = Math.abs(Number(orb)||0);
  const m = Number(max)||0;
  if (!(m>0)) return 0;
  return Math.max(0, Math.min(100, (1 - (o/m)) * 100));
}

function fallbackMaxOrb(name) {
  const k = String(name||'').toLowerCase();
  if (k.includes('parallel')) return 1;
  if (k.includes('conj')) return 8;
  if (k.includes('opp')) return 8;
  if (k.includes('square')) return 8;
  if (k.includes('trine')) return 8;
  if (k.includes('sext')) return 6;
  return 6;
}

const formatOrbLabel = (row, digits = 2) => {
  if (row?.orb_text) return row.orb_text;
  const orb = Math.abs(Number(row?.orb || 0));
  return `${orb.toFixed(digits)}\u00B0`;
};

export default function AspectAnalysisModal({
  open,
  onClose,
  specialDegrees,
  useMorin,
  includeModern = true,
  dashboardData = null,
}){
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dash, setDash] = useState(null);
  const [q, setQ] = useState('');
  const [typeFilter, setTypeFilter] = useState('all'); // all|hard|soft|conj
  const [showPlanetary, setShowPlanetary] = useState(true);
  const [showDecl, setShowDecl] = useState(true);
  const [showCusps, setShowCusps] = useState(true);
  const openedRef = useRef(false);

  useEffect(() => {
    if (!open) {
      openedRef.current = false;
      return;
    }
    if (openedRef.current) return;
    openedRef.current = true;

    let alive = true;
    setError(null);
    if (dashboardData) {
      setLoading(false);
      setDash(dashboardData);
      return () => { alive = false; };
    }

    setLoading(true);
    setDash(null);
    AstroClockAPI.getDashboard({ includeModern, specialDegrees, morin: !!useMorin })
      .then(res => {
        if (!alive) return;
        if (res?.success) setDash(transformDashboard(res.data || {}));
        else setError('Failed to load');
      })
      .catch(()=> { if (alive) setError('Failed to load'); })
      .finally(()=> { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [dashboardData, includeModern, open, specialDegrees, useMorin]);

  const planetsIndex = useMemo(() => {
    const idx = {};
    const arr = Array.isArray(dash?.planets) ? dash.planets : [];
    arr.forEach(p => { if (p?.planet) idx[p.planet] = p; });
    return idx;
  }, [dash]);
  const standardPlanetaryAspects = useMemo(
    () => dedupeAspectRows(
      Array.isArray(dash?.planetary_aspects_precise)
        ? dash.planetary_aspects_precise
        : (dash?.metrics?.planetary_aspects || [])
    ),
    [dash]
  );
  const morinPlanetaryAspects = useMemo(
    () => dedupeAspectRows(dash?.morin_aspects || []),
    [dash]
  );

  // Angle geometry helpers for applying/separating estimation (UI-only)
  const toRad = (d) => (Number(d)||0) * Math.PI / 180;
  const norm360 = (x) => ((Number(x)||0) % 360 + 360) % 360;
  const norm180 = (x) => ((Number(x)||0) + 180) % 360 - 180;
  const orbToAspect = (lon1, lon2, A) => {
    const sep = Math.abs(norm180((Number(lon1)||0) - (Number(lon2)||0)));
    let orb = Math.abs(sep - (Number(A)||0));
    if (orb > 180) orb = 360 - orb;
    return orb;
  };
  const aspectAngle = (name) => {
    const k = String(name||'').toLowerCase();
    if (k.includes('conj')) return 0;
    if (k.includes('opp')) return 180;
    if (k.includes('square')) return 90;
    if (k.includes('trine')) return 120;
    if (k.includes('sext')) return 60;
    return 0;
  };
  // Angles section removed; helpers retained above for reference if needed

  const matchType = (asp) => {
    const t = String(asp?.aspect||'').toLowerCase();
    if (typeFilter === 'all') return true;
    if (typeFilter === 'conj') return t.includes('conj');
    const isHard = t.includes('opp') || t.includes('square');
    const isSoft = t.includes('trine') || t.includes('sext');
    if (typeFilter === 'hard') return isHard || t.includes('conj');
    if (typeFilter === 'soft') return isSoft;
    return true;
  };

  const matchesSearch = (a,b) => {
    const qq = q.trim().toLowerCase();
    if (!qq) return true;
    return String(a||'').toLowerCase().includes(qq) || String(b||'').toLowerCase().includes(qq);
  };

  const SectionHeader = ({ title }) => (
    <div className="flex items-center justify-between">
      <h4 className="font-semibold text-sm">{title}</h4>
    </div>
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="absolute inset-0 grid place-items-center p-4">
        <div className="w-[min(1100px,95vw)] h-[min(85vh,900px)] rounded-2xl border border-zinc-200 bg-white shadow-2xl overflow-hidden flex flex-col">
          {/* Header */}
          <div className="px-4 py-3 border-b border-zinc-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="text-base font-semibold">Aspect Analysis</div>
              <span className="text-[11px] px-2 py-0.5 rounded-full border border-zinc-200 bg-white text-zinc-700">Modern included</span>
            </div>
            <button onClick={onClose} className="px-2 py-0.5 rounded border border-zinc-300 hover:bg-zinc-50" aria-label="Close">{"\u00D7"}</button>
          </div>

          {/* Filters */}
          <div className="px-4 py-2 border-b border-zinc-200 bg-white flex items-center gap-2">
            <input value={q} onChange={e=>setQ(e.target.value)} placeholder={"Search planet\u2026"} className="px-2 py-1 border rounded text-[13px] w-44" />
            <div className="flex items-center gap-1 ml-2">
              {['all','conj','hard','soft'].map(mode => (
                <button key={mode} className={`px-2 py-0.5 rounded-full border text-[11px] ${typeFilter===mode? 'bg-zinc-800 text-white border-zinc-800' : ''}`} onClick={()=> setTypeFilter(mode)}>{mode==='all'?'All':mode.charAt(0).toUpperCase()+mode.slice(1)}</button>
              ))}
            </div>
            <div className="flex items-center gap-1 ml-4">
              <button className={`px-2 py-0.5 rounded-full border text-[11px] ${showPlanetary? 'bg-zinc-800 text-white border-zinc-800':''}`} onClick={()=> setShowPlanetary(v=>!v)}>Planetary</button>
              {/* Angles toggle removed */}
              <button className={`px-2 py-0.5 rounded-full border text-[11px] ${showDecl? 'bg-zinc-800 text-white border-zinc-800':''}`} onClick={()=> setShowDecl(v=>!v)}>Decl</button>
              <button className={`px-2 py-0.5 rounded-full border text-[11px] ${showCusps? 'bg-zinc-800 text-white border-zinc-800':''}`} onClick={()=> setShowCusps(v=>!v)}>Cusps</button>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-auto p-4 space-y-6">
            {loading && <div className="text-sm text-zinc-500">Loading…</div>}
            {error && <div className="text-sm text-red-600">{error}</div>}
            {!loading && !error && dash && (
              <>
                {/* Planetary Aspects */}
                {showPlanetary && (
                  <section>
                    <SectionHeader title={useMorin ? 'Morin Aspects' : 'Planetary Aspects'} />
                    <div className="mt-2 divide-y divide-zinc-100 border border-zinc-200 rounded-lg overflow-hidden">
                      {(useMorin ? morinPlanetaryAspects : standardPlanetaryAspects)
                        .filter(a => matchType(a) && matchesSearch(a.planet1, a.planet2))
                        .sort((a,b)=> Math.abs(a.orb||0)-Math.abs(b.orb||0))
                        .slice(0, 200)
                        .map((a, idx) => {
                          const col = aspectColor(a.aspect);
                          const max = a.max_orb ?? a.allowed_orb ?? fallbackMaxOrb(a.aspect);
                          const pct = exactnessPct(a.orb, max);
                          return (
                            <div key={`${a.planet1}-${a.aspect}-${a.planet2}-${idx}`} className="p-2 grid grid-cols-12 items-center gap-2" title={`${a.planet1} ${a.aspect} ${a.planet2}`}>
                              <div className="col-span-4 flex items-center gap-2">
                                <span className={`px-1.5 py-0.5 rounded-full border text-xs ${col.pill}`} title={a.planet1}>{PlanetSymbols[a.planet1]||''}</span>
                                <span className={`${col.text} text-sm`}>{aspectSymbol(a.aspect)}</span>
                                <span className={`px-1.5 py-0.5 rounded-full border text-xs ${col.pill}`} title={a.planet2}>{PlanetSymbols[a.planet2]||''}</span>
                              </div>
                              <div className="col-span-2 text-xs text-zinc-600">orb {formatOrbLabel(a)} / max {Number(max||0).toFixed(2)}{"\u00B0"}</div>
                              <div className="col-span-4">
                                <div className="flex items-center justify-between text-[11px] text-zinc-600"><span>Exactness</span><span>{Math.round(pct)}%</span></div>
                                <div className="h-2 rounded-full bg-zinc-200 overflow-hidden"><div className={`h-full ${col.bar}`} style={{ width: `${pct}%` }} /></div>
                              </div>
                              <div className="col-span-2 flex items-center justify-end gap-2 text-[11px]">
                                {a.phase && <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-zinc-700">{a.phase}</span>}
                                {useMorin && a.direction && <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-zinc-700">{a.direction}</span>}
                                {useMorin && (a.partile || a.complete_platic) && (
                                  <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-zinc-700">{a.partile? 'partile' : 'platic'}</span>
                                )}
                                {!useMorin && a.severity && <span className={`px-1.5 py-0.5 rounded-full border ${a.severity==='severe'?'bg-rose-100 border-rose-200 text-rose-800':a.severity==='moderate'?'bg-amber-100 border-amber-200 text-amber-800':'bg-zinc-100 border-zinc-200 text-zinc-700'}`}>{a.severity}</span>}
                              </div>
                            </div>
                          );
                        })}
                      {(!useMorin && standardPlanetaryAspects.length === 0) && (
                        <div className="p-3 text-sm text-zinc-500">None</div>
                      )}
                      {(useMorin && morinPlanetaryAspects.length === 0) && (
                        <div className="p-3 text-sm text-zinc-500">None</div>
                      )}
                    </div>
              </section>
            )}

            {/* Angle Aspects removed (redundant with Cusp Aspects ≤1°) */}

            {/* Declinations or Antiscia (Morin) */}
            {showDecl && (
              <section>
                <SectionHeader title={useMorin ? 'Antiscia / Contra-antiscia (Morin)' : 'Declination (∥ / antiparallel)'} />
                    <div className="mt-2 divide-y divide-zinc-100 border border-zinc-200 rounded-lg overflow-hidden">
                      {([]).concat(useMorin ? ((dash?.morin_antiscia||[]).concat(dash?.morin_contra_antiscia||[])) : (dash?.top_declinations||[]))
                        .filter(a => matchesSearch(a.planet1 || a.planet, a.planet2 || a.angle || ''))
                        .map((a, idx) => {
                          const max = (useMorin ? (a.max_orb ?? 1) : (a.max_orb ?? 1));
                          const orbVal = Number(a.orb||0);
                          const pct = exactnessPct(orbVal, max);
                          return (
                            <div key={`${a.planet1 || a.planet}-${a.aspect}-${a.planet2 || a.angle || ''}-${idx}`} className="p-2 grid grid-cols-12 items-center gap-2" title={`${a.planet1 || a.planet} ${a.aspect} ${a.planet2 || ''}`}>
                              <div className="col-span-4 flex items-center gap-2">
                                <span className="px-1.5 py-0.5 rounded-full border text-xs border-zinc-200 bg-white" title={a.planet1 || a.planet}>{PlanetSymbols[a.planet1 || a.planet]||''}</span>
                                <span className="text-sm">{aspectSymbol(a.aspect) || (a.aspect==='parallel'?'∥':'⇵')}</span>
                                <span className="px-1.5 py-0.5 rounded-full border text-xs border-zinc-200 bg-white" title={a.planet2 || ''}>{a.planet2 ? (PlanetSymbols[a.planet2]||'') : ''}</span>
                              </div>
                              <div className="col-span-2 text-xs text-zinc-600">orb {formatOrbLabel(a)} / max {Number(max||0).toFixed(2)}°</div>
                              <div className="col-span-4">
                                <div className="flex items-center justify-between text-[11px] text-zinc-600"><span>Exactness</span><span>{Math.round(pct)}%</span></div>
                                <div className="h-2 rounded-full bg-zinc-200 overflow-hidden"><div className="h-full bg-zinc-900" style={{ width: `${pct}%` }} /></div>
                              </div>
                              <div className="col-span-2" />
                            </div>
                          );
                        })}
                      {(!useMorin && (!dash?.top_declinations || dash.top_declinations.length===0)) && (
                        <div className="p-3 text-sm text-zinc-500">None</div>
                      )}
                      {(useMorin && (!((dash?.morin_antiscia||[]).length + (dash?.morin_contra_antiscia||[]).length))) && (
                        <div className="p-3 text-sm text-zinc-500">None</div>
                      )}
                    </div>
              </section>
            )}

            {useMorin && (
              <>
                <section>
                  <SectionHeader title="Combustion (Morin)" />
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(dash?.morin_combustion||[]).map((it, idx)=> (
                      <span key={`mc-${idx}`} className={`text-xs rounded-full px-2 py-1 border ${it.status==='cazimi'?'border-amber-300 bg-amber-50': it.status==='combust'?'border-rose-300 bg-rose-50': it.status==='under_beams'?'border-sky-300 bg-sky-50':'border-zinc-300 bg-zinc-50'}`} title={`${it.status} \u00B7 ${Number(it.distance_deg||0).toFixed(2)}\u00B0`}>
                        <span className="mr-1">{PlanetSymbols[it.planet]||''}</span>
                        {it.status.replace('_',' ')} {"\u00B7"} {Number(it.distance_deg||0).toFixed(2)}{"\u00B0"}
                      </span>
                    ))}
                    {(!dash?.morin_combustion || dash.morin_combustion.length===0) && (
                      <div className="text-sm text-zinc-500">None</div>
                    )}
                  </div>
                </section>

                <section>
                  <SectionHeader title="Translation (Morin)" />
                  <div className="mt-2 space-y-2">
                    {(dash?.morin_patterns?.translation||[]).map((t, idx)=> (
                      <div key={`tr-${idx}`} className="p-2 border border-zinc-200 rounded-lg">
                        <div className="text-sm">
                          <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[t.from]||''}</span>{t.from}
                          <span className="mx-2 text-zinc-500">→</span>
                          <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[t.middle]||''}</span>{t.middle}
                          <span className="mx-2 text-zinc-500">→</span>
                          <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[t.to]||''}</span>{t.to}
                        </div>
                        <div className="text-xs text-zinc-600 mt-1">
                          <div>From-leg: {t.from_leg?.aspect} {"\u00B7"} {Number(t.from_leg?.orb||0).toFixed(2)}{"\u00B0"} {"\u00B7"} {t.from_leg?.phase}{t.from_leg?.partile? ' \u00B7 partile': (t.from_leg?.complete_platic? ' \u00B7 platic':'')}</div>
                          <div>To-leg: {t.to_leg?.aspect} {"\u00B7"} {Number(t.to_leg?.orb||0).toFixed(2)}{"\u00B0"} {"\u00B7"} {t.to_leg?.phase}{t.to_leg?.partile? ' \u00B7 partile': (t.to_leg?.complete_platic? ' \u00B7 platic':'')}</div>
                        </div>
                      </div>
                    ))}
                    {(!dash?.morin_patterns?.translation || dash.morin_patterns.translation.length===0) && (
                      <div className="text-sm text-zinc-500">None</div>
                    )}
                  </div>
                </section>

                <section>
                  <SectionHeader title="Besiegement (Morin)" />
                  <div className="mt-2 space-y-3">
                    {(dash?.morin_patterns?.besiegement||[]).map((b, idx)=> {
                      const isMalefic = (p) => (p==='Mars' || p==='Saturn');
                      const beforeOrb = Number(b?.before_leg?.orb || 999);
                      const afterOrb = Number(b?.after_leg?.orb || 999);
                      const minOrb = Math.min(beforeOrb, afterOrb);
                      const anyPartile = !!(b?.before_leg?.partile || b?.after_leg?.partile);
                      const severity = anyPartile || minOrb <= 1.0 ? 'severe' : (minOrb <= 3.0 ? 'moderate' : 'mild');
                      const frameClass = severity === 'severe'
                        ? 'border-red-300 bg-red-50'
                        : severity === 'moderate'
                          ? 'border-amber-300 bg-amber-50'
                          : 'border-zinc-200 bg-white';
                      const legBar = (orb) => {
                        const max = 6.0;
                        const pct = Math.max(0, Math.min(100, (1 - (Number(orb||0)/max)) * 100));
                        return (
                          <div className="mt-1 h-1.5 rounded-full bg-zinc-200 overflow-hidden"><div className="h-full bg-zinc-900" style={{ width: `${pct}%` }} /></div>
                        );
                      };
                      const aspectGlyph = (name) => aspectSymbol(name||'');
                      const Pill = ({ text }) => (<span className="ml-2 px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white">{text}</span>);
                      const Leg = ({ title, leg }) => (
                        <div className="p-2 rounded bg-white border border-zinc-200">
                          <div className="font-medium mb-1">{title}</div>
                          <div className="flex items-center text-[12px] text-zinc-700">
                            <span className="mr-2">{aspectGlyph(leg?.aspect)} {leg?.aspect}</span>
                            <span className="text-zinc-500">{Number(leg?.orb||0).toFixed(2)}{"\u00B0"}</span>
                            {leg?.phase && <Pill text={leg.phase} />}
                            {leg?.partile ? <Pill text="partile" /> : (leg?.complete_platic ? <Pill text="platic" /> : null)}
                          </div>
                          {legBar(leg?.orb)}
                        </div>
                      );
                      return (
                        <div key={`bs-${idx}`} className={`p-3 border rounded-lg ${frameClass}`}>
                          {/* Header row: who is besieged */}
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2 text-sm font-medium">
                              <span className="text-zinc-500">Besieged:</span>
                              <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[b.besieged]||''}</span>{b.besieged}
                              <span className={`ml-2 text-[11px] ${severity==='severe'?'text-red-700':severity==='moderate'?'text-amber-700':'text-zinc-600'}`}>({severity})</span>
                            </div>
                            <div className="text-[11px] text-zinc-500">Malefic rays</div>
                          </div>
                          {/* By whom (malefics) */}
                          <div className="text-xs text-zinc-700 mb-2 flex items-center">
                            <span className="mr-2 text-zinc-500">By:</span>
                            <span className={`px-1.5 py-0.5 rounded-full border ${isMalefic(b.before)?'border-red-300 bg-red-50':'border-zinc-200 bg-white'} text-xs mr-1`}>{PlanetSymbols[b.before]||''}</span>{b.before} <span className="text-zinc-400">(before)</span>
                            <span className="mx-3 text-zinc-300">→</span>
                            <span className={`px-1.5 py-0.5 rounded-full border ${isMalefic(b.after)?'border-red-300 bg-red-50':'border-zinc-200 bg-white'} text-xs mr-1`}>{PlanetSymbols[b.after]||''}</span>{b.after} <span className="text-zinc-400">(after)</span>
                          </div>
                          {/* Legs */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <Leg title={`${b.before} → ${b.besieged}`} leg={b.before_leg} />
                            <Leg title={`${b.besieged} → ${b.after}`} leg={b.after_leg} />
                          </div>
                        </div>
                      );
                    })}
                    {(!dash?.morin_patterns?.besiegement || dash.morin_patterns.besiegement.length===0) && (
                      <div className="text-sm text-zinc-500">None</div>
                    )}
                  </div>
                </section>

                <section>
                  <SectionHeader title="Doryphory (Morin)" />
                  <div className="mt-2 space-y-3">
                    {(dash?.morin_patterns?.doryphory||[]).map((group, idx)=> (
                      <div key={`dr-${idx}`} className="p-2 border border-zinc-200 rounded-lg">
                        <div className="text-sm font-medium mb-1">{group.luminary}</div>
                        <ul className="text-xs text-zinc-700 space-y-1">
                          {(group.attendants||[]).map((a, j)=> (
                                <li key={`dr-${idx}-${j}`}>
                                  <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[a.planet]||''}</span>{a.planet}
                                  <span className="ml-2 text-zinc-500">{a.orientation || 'neutral'}</span>
                                  {a.angular && <span className="ml-2 text-zinc-500">angular</span>}
                                  <span className="ml-2 text-zinc-500">{a.aspect} · {Number(a.orb||0).toFixed(2)}° · {a.phase}</span>
                                  {a.partile? <span className="ml-2 text-zinc-500">partile</span> : (a.complete_platic? <span className="ml-2 text-zinc-500">platic</span> : null)}
                                  {a.sect_ok ? <span className="ml-2 text-emerald-600">sect ok</span> : <span className="ml-2 text-zinc-500">sect off</span>}
                                  <span className="ml-2 text-zinc-500">{a.sex}</span>
                                </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                    {(!dash?.morin_patterns?.doryphory || dash.morin_patterns.doryphory.length===0) && (
                      <div className="text-sm text-zinc-500">None</div>
                    )}
                  </div>
                </section>

                <section>
                  <SectionHeader title="Collection (Morin)" />
                  <div className="mt-2 space-y-2">
                    {(dash?.morin_patterns?.collection||[]).map((c, idx)=> (
                      <div key={`coll-${idx}`} className="p-2 border border-zinc-200 rounded-lg text-sm">
                        <span className="text-zinc-500 mr-2">Collector:</span>
                        <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[c.collector]||''}</span>{c.collector}
                        <span className="mx-2 text-zinc-400">→</span>
                        {(c.collected||[]).map((p,i)=> (
                          <span key={i} className="mr-2"><span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[p]||''}</span>{p}</span>
                        ))}
                        <span className="ml-2 text-[11px] text-zinc-500">{c.mode==='BY_SEPARATION'?'by separation':'by application'}</span>
                      </div>
                    ))}
                    {(!dash?.morin_patterns?.collection || dash.morin_patterns.collection.length===0) && (
                      <div className="text-sm text-zinc-500">None</div>
                    )}
                  </div>
                </section>

                <section>
                  <SectionHeader title="Frustration (Morin)" />
                  <div className="mt-2 space-y-2">
                    {(dash?.morin_patterns?.frustration||[]).map((f, idx)=> (
                      <div key={`fr-${idx}`} className="p-2 border border-zinc-200 rounded-lg text-sm">
                        <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[f.frustrated]||''}</span>{f.frustrated}
                        <span className="mx-2 text-zinc-400">→</span>
                        <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[f.target]||''}</span>{f.target}
                        <span className="mx-2 text-zinc-400">is frustrated by</span>
                        <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[f.frustrating]||''}</span>{f.frustrating}
                        <span className="ml-2 text-[11px] text-zinc-500">arrives earlier by ~{Number(f.days_C_before_A||0).toFixed(1)} days</span>
                      </div>
                    ))}
                    {(!dash?.morin_patterns?.frustration || dash.morin_patterns.frustration.length===0) && (
                      <div className="text-sm text-zinc-500">None</div>
                    )}
                  </div>
                </section>

                <section>
                  <SectionHeader title="Mediation (Morin)" />
                  <div className="mt-2 space-y-2">
                    {(dash?.morin_patterns?.mediation||[]).map((m, idx)=> (
                      <div key={`med-${idx}`} className="p-2 border border-zinc-200 rounded-lg text-sm">
                        <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[m.extreme_1]||''}</span>{m.extreme_1}
                        <span className="mx-2 text-zinc-400">→</span>
                        <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[m.middle]||''}</span>{m.middle}
                        <span className="mx-2 text-zinc-400">→</span>
                        <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs mr-1">{PlanetSymbols[m.extreme_2]||''}</span>{m.extreme_2}
                        <span className="ml-2 text-[11px] text-zinc-500">slower middle mediates</span>
                      </div>
                    ))}
                    {(!dash?.morin_patterns?.mediation || dash.morin_patterns.mediation.length===0) && (
                      <div className="text-sm text-zinc-500">None</div>
                    )}
                  </div>
                </section>
              </>
            )}

                {/* Cusp Aspects */}
                {showCusps && (
                  <section>
                    <SectionHeader title={"Cusp Aspects (\u22641\u00B0)"} />
                    <div className="mt-2 grid grid-cols-2 gap-3">
                      {Array.from({length:12}, (_,i)=>`H${i+1}`).map(h => {
                        const items = Array.isArray(dash?.cusp_aspects?.[h]) ? dash.cusp_aspects[h] : [];
                        if (!items.length) return null;
                        return (
                          <div key={h} className="border border-zinc-200 rounded-lg overflow-hidden">
                            <div className="px-2 py-1 text-[12px] font-medium border-b border-zinc-200 bg-zinc-50">{h}</div>
                            <ul className="divide-y divide-zinc-100">
                              {items
                                .filter(it => matchType(it) && matchesSearch(it.planet, h))
                                .slice(0, 12)
                                .map((it, idx) => (
                                  <li key={`${h}-${idx}`} className="px-2 py-1 text-sm flex items-center gap-2" title={`${it.planet} ${it.aspect} ${h} ${it?.origin_domain||''}`}>
                                    <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-xs" title={it.planet}>{PlanetSymbols[it.planet]||''}</span>
                                    <span>{aspectSymbol(it.aspect)}</span>
                                    <span className="text-zinc-500 text-xs">{(it?.orb!=null)? `${Number(it.orb).toFixed(2)}\u00B0` : '\u2014'}</span>
                                    <span className="text-zinc-500 text-xs">{it?.phase || ''}</span>
                                    {it?.origin_domain && (
                                      <span className="text-zinc-600 text-[11px]">— {String(it.origin_domain)}</span>
                                    )}
                                    {typeof it?.dexter === 'boolean' && (
                                      <span className="text-[11px] px-1 py-0.5 rounded bg-zinc-100 text-zinc-700 border border-zinc-200">{it.dexter? 'dexter':'sinister'}</span>
                                    )}
                                    {it?.band && (
                                      <span className="text-[11px] px-1 py-0.5 rounded bg-zinc-100 text-zinc-700 border border-zinc-200">{it.band}</span>
                                    )}
                                    {it?.origin_house != null && (
                                      <span className="text-[11px] px-1 py-0.5 rounded bg-zinc-100 text-zinc-700 border border-zinc-200">H{it.origin_house}</span>
                                    )}
                                  </li>
                                ))}
                            </ul>
                          </div>
                        );
                      })}
                    </div>
                  </section>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
