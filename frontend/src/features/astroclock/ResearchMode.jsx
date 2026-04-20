import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AstroClockAPI } from './api.mjs';
import { pollResearchSession } from './researchPolling.mjs';

export default function ResearchMode({ onClose }) {
  const HARD_TIME = '23:30';
  const HARD_LOCATION = 'Tel Aviv, Israel';
  const [path, setPath] = useState('backend/Lotto(10).csv');
  const time = HARD_TIME;
  const location = HARD_LOCATION;
  const [rowLimit, setRowLimit] = useState('');
  // Filter builder (internal state)
  const [filters, setFilters] = useState([]); // [{ id, type:'element'|'modality', mode:'top'|'zero', value:'Water'|... }]
  const [selType, setSelType] = useState('element');
  const [selMode, setSelMode] = useState('top');
  const [selValue, setSelValue] = useState('Water');
  // Advanced filter inputs
  const [orderExpr, setOrderExpr] = useState('Water>Earth>Fire>Air');
  const [modOrderExpr, setModOrderExpr] = useState('Fixed>Cardinal>Mutable');
  const [posPlanet, setPosPlanet] = useState('Mars');
  const [posSign, setPosSign] = useState('');
  const [posMinDeg, setPosMinDeg] = useState('');
  const [posMaxDeg, setPosMaxDeg] = useState('');
  const [absLonMin, setAbsLonMin] = useState('');
  const [absLonMax, setAbsLonMax] = useState('');
  const [houseList, setHouseList] = useState('');
  const [rulerCusp, setRulerCusp] = useState('1');
  const [rulerTarget, setRulerTarget] = useState('1');
  const [recMode, setRecMode] = useState('mutual');
  const [recP1, setRecP1] = useState('Venus');
  const [recP2, setRecP2] = useState('Mars');
  const [recReceiving, setRecReceiving] = useState('Venus');
  const [recReceived, setRecReceived] = useState('Mars');
  const [dirPlanet, setDirPlanet] = useState('Mercury');
  const [dirMode, setDirMode] = useState('direct');
  const [fdPlanet, setFdPlanet] = useState('Venus');
  const [fdTarget, setFdTarget] = useState('Moon');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [sessionId, setSessionId] = useState('');
  const [progress, setProgress] = useState(null);
  const [banner, setBanner] = useState(null); // { source:'cache'|'compiled', workers:number }
  const mountedRef = useRef(true);
  const activeRunIdRef = useRef(0);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
      activeRunIdRef.current += 1;
    };
  }, []);

  const beginRun = () => {
    activeRunIdRef.current += 1;
    return activeRunIdRef.current;
  };

  const cancelRun = () => {
    activeRunIdRef.current += 1;
  };

  const isRunActive = (runId) => (
    mountedRef.current && activeRunIdRef.current === runId
  );

  const waitForReady = async (sid, runId) => (
    pollResearchSession({
      fetchProgress: async () => {
        const pr = await AstroClockAPI.researchProgress(sid);
        return pr?.data || {};
      },
      onProgress: (nextProgress) => {
        if (isRunActive(runId)) {
          setProgress(nextProgress);
        }
      },
      shouldContinue: () => isRunActive(runId),
    })
  );

  const run = async () => {
    const runId = beginRun();
    setBusy(true); setError(''); setResult(null);
    try {
      // Start or load dataset, and poll progress until ready
      const start = await AstroClockAPI.researchCompileStart({ path, defaults: { time, location } });
      const sid = start?.data?.session_id; if (!sid) throw new Error('Failed to start compile');
      if (!isRunActive(runId)) return;
      setSessionId(sid);
      const initialProg = start?.data?.progress || {};
      setProgress(initialProg);

      const readyProgress = initialProg?.ready
        ? initialProg
        : await waitForReady(sid, runId);
      if (!isRunActive(runId)) return;

      // Read final compile info for banner
      const fin = await AstroClockAPI.researchCompile({ path, defaults: { time, location } });
      if (!isRunActive(runId)) return;
      const prog2 = fin?.data?.progress || readyProgress || {};
      setProgress(prog2);
      setBanner({ source: prog2?.source || (start?.data?.cached ? 'cache':'compiled'), workers: prog2?.workers || 0, total: prog2?.total || 0 });

      // Compile filters to backend spec
      let topElement = '';
      let zeroElements = [];
      let topModality = '';
      let zeroModalities = [];
      let elementOrder = null;
      let modalityOrder = null;
      const positions = [];
      const receptions = { mutual_pairs: [], unilateral: [] };
      const directions = [];
      const finalDispositors = [];
      for (const f of filters) {
        if (f.type === 'element') {
          if (f.mode === 'top') topElement = f.value;
          if (f.mode === 'zero') zeroElements.push(f.value);
        } else if (f.type === 'modality') {
          if (f.mode === 'top') topModality = f.value;
          if (f.mode === 'zero') zeroModalities.push(f.value);
        } else if (f.type === 'element_order') {
          elementOrder = Array.isArray(f.values) ? f.values : null;
        } else if (f.type === 'modality_order') {
          modalityOrder = Array.isArray(f.values) ? f.values : null;
        } else if (f.type === 'position') {
          const pf = { planet: f.planet };
          if (f.sign) pf.sign = f.sign;
          if (f.min_deg!=null && f.min_deg!=='') pf.min_deg = Number(f.min_deg);
          if (f.max_deg!=null && f.max_deg!=='') pf.max_deg = Number(f.max_deg);
          positions.push(pf);
        } else if (f.type === 'reception') {
          if (f.mode === 'mutual') receptions.mutual_pairs.push([f.p1, f.p2]);
          else receptions.unilateral.push({ receiving: f.receiving, received: f.received });
        } else if (f.type === 'direction') {
          directions.push({ planet: f.planet, direction: (f.direction || 'direct').toLowerCase().startsWith('r') ? 'R' : 'D' });
        } else if (f.type === 'final_dispositor') {
          finalDispositors.push({ planet: f.planet, final: f.final });
        }
      }
      const body = {
        sessionId: sid,
        filter: {
          topElement: topElement || undefined,
          zeroElements,
          topModality: topModality || undefined,
          zeroModalities,
          elementOrder: elementOrder || undefined,
          modalityOrder: modalityOrder || undefined,
          positions: positions.length ? positions : undefined,
          housePositions: filters.filter(x=> x.type==='house_pos').map(x=> ({ planet: x.planet, in: x.houses })),
          rulerInHouse: filters.filter(x=> x.type==='ruler_in_house').map(x=> ({ cusp: Number(x.cusp), in_house: Number(x.in_house) })),
          directions: directions.length ? directions : undefined,
          finalDispositors: finalDispositors.length ? finalDispositors : undefined,
          receptions: (receptions.mutual_pairs.length || receptions.unilateral.length) ? receptions : undefined,
        },
        ...(rowLimit ? { rowLimit: Number(rowLimit) } : {}),
      };
      const res = await AstroClockAPI.researchAnalyze(body);
      if (!isRunActive(runId)) return;
      if (res?.success) setResult(res.data);
      else setError(res?.error || 'Failed');
    } catch (e) {
      if (!isRunActive(runId)) return;
      const message = String(e?.message || e || 'Failed');
      if (message !== 'Research compile cancelled') {
        setError(message);
      }
    } finally {
      if (isRunActive(runId)) {
        setBusy(false);
      }
    }
  };

  const stopActiveCompile = async () => {
    const sid = sessionId;
    if (!sid) return;
    cancelRun();
    if (mountedRef.current) {
      setBusy(false);
    }
    try {
      await AstroClockAPI.researchStop(sid);
      const pr = await AstroClockAPI.researchProgress(sid);
      if (mountedRef.current) {
        setProgress(pr?.data || {});
      }
    } catch (_) {}
  };

  const forceRecompile = async () => {
    const runId = beginRun();
    setError(''); setResult(null); setBanner(null); setProgress(null); setBusy(true);
    try {
      const start = await AstroClockAPI.researchCompileStart({ path, defaults: { time, location }, force: true });
      const sid = start?.data?.session_id; if (!sid) throw new Error('Failed to start recompile');
      if (!isRunActive(runId)) return;
      setSessionId(sid);

      const initialProg = start?.data?.progress || {};
      setProgress(initialProg);
      const readyProgress = initialProg?.ready
        ? initialProg
        : await waitForReady(sid, runId);
      if (!isRunActive(runId)) return;

      const fin = await AstroClockAPI.researchCompile({ path, defaults: { time, location } });
      if (!isRunActive(runId)) return;
      const prog2 = fin?.data?.progress || readyProgress || {};
      setProgress(prog2);
      setBanner({ source: prog2?.source || 'compiled', workers: prog2?.workers || 0, total: prog2?.total || 0 });
    } catch (e) {
      if (!isRunActive(runId)) return;
      const message = String(e?.message || e || 'Failed');
      if (message !== 'Research compile cancelled') {
        setError(message);
      }
    } finally {
      if (isRunActive(runId)) {
        setBusy(false);
      }
    }
  };

  const elements = ['Fire','Earth','Air','Water'];
  const modalities = ['Cardinal','Fixed','Mutable'];
  const planets = ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Uranus','Neptune','Pluto'];
  const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];

  const NumbersTable = ({ title, obj }) => {
    if (!obj) return null;
    const base = obj.baseline || {}; const inF = obj.in_filter || {};
    const keys = Array.from(new Set(Object.keys(base).concat(Object.keys(inF))));
    return (
      <div className="mt-3">
        <div className="font-semibold text-sm mb-1">{title}</div>
        <div className="max-h-48 overflow-auto border rounded">
          <table className="w-full text-[12px]">
            <thead className="bg-zinc-50 sticky top-0">
              <tr>
                <th className="text-left px-2 py-1">Number</th>
                <th className="text-right px-2 py-1">Count</th>
                <th className="text-right px-2 py-1">In Filter</th>
              </tr>
            </thead>
            <tbody>
              {keys.sort((a,b)=> (Number(a)||0)-(Number(b)||0)).map(k => (
                <tr key={k} className="border-t">
                  <td className="px-2 py-1">{k}</td>
                  <td className="px-2 py-1 text-right">{base[k]||0}</td>
                  <td className="px-2 py-1 text-right">{inF[k]||0}</td>
                </tr>
              ))}
              {keys.length===0 && (
                <tr><td colSpan={3} className="px-2 py-2 text-center text-zinc-500">No data</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // Visualization components
  const BarsBlock = ({ title, obj }) => {
    if (!obj) return null;
    const base = obj.baseline || {}; const inF = obj.in_filter || {};
    const basePct = obj.baseline_pct || {}; const inPct = obj.in_filter_pct || {};
    const keys = Array.from(new Set(Object.keys(base).concat(Object.keys(inF))));
    const rows = keys.map(k => {
      const b = Number(base[k] || 0);
      const i = Number(inF[k] || 0);
      const bp = Number(basePct[k] || 0);
      const ip = Number(inPct[k] || 0);
      const delta = ip - bp;
      return { k, b, i, bp, ip, delta };
    });
    const sorted = [...rows].sort((a,b)=> (b.delta - a.delta) || (b.ip - a.ip) || (Number(b.k)-Number(a.k)));
    const top = sorted.slice(0, Math.min(20, sorted.length));
    const worst = [...rows].sort((a,b)=> (a.delta - b.delta) || (a.ip - b.ip)).slice(0, Math.min(10, rows.length));
    return (
      <div className="mt-4">
        <div className="font-semibold text-sm mb-2">{title}</div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <div className="text-[12px] text-zinc-600 mb-1">Top lifts (In% vs Base%)</div>
            <div className="space-y-1.5">
              {top.map(r => (
                <div key={r.k} className="flex items-center gap-2">
                  <div className="w-10 text-right text-[12px] font-mono">{r.k}</div>
                  <div className="flex-1">
                    <div className="relative h-3 bg-zinc-100 rounded">
                      <div className="absolute left-0 top-0 h-3 bg-zinc-300 rounded" style={{ width: `${Math.min(100, r.bp*100)}%` }} />
                      <div className="absolute left-0 top-0 h-3 bg-emerald-500/80 rounded" style={{ width: `${Math.min(100, r.ip*100)}%` }} />
                    </div>
                  </div>
                  <div className="w-28 text-[11px] text-right tabular-nums">
                    {`${(r.ip*100).toFixed(1)}% / ${(r.bp*100).toFixed(1)}%`}
                  </div>
                  <div className={`w-14 text-[11px] text-right ${r.delta>=0?'text-emerald-600':'text-red-600'}`}>{(r.delta*100>=0?'+':'')}{(r.delta*100).toFixed(1)}%</div>
                </div>
              ))}
              {top.length === 0 && <div className="text-[12px] text-zinc-500">No data</div>}
            </div>
          </div>
          <div>
            <div className="text-[12px] text-zinc-600 mb-1">Top drops</div>
            <div className="space-y-1.5">
              {worst.map(r => (
                <div key={r.k} className="flex items-center gap-2">
                  <div className="w-10 text-right text-[12px] font-mono">{r.k}</div>
                  <div className="flex-1">
                    <div className="relative h-3 bg-zinc-100 rounded">
                      <div className="absolute left-0 top-0 h-3 bg-zinc-300 rounded" style={{ width: `${Math.min(100, r.bp*100)}%` }} />
                      <div className="absolute left-0 top-0 h-3 bg-red-500/70 rounded" style={{ width: `${Math.min(100, r.ip*100)}%` }} />
                    </div>
                  </div>
                  <div className="w-28 text-[11px] text-right tabular-nums">
                    {`${(r.ip*100).toFixed(1)}% / ${(r.bp*100).toFixed(1)}%`}
                  </div>
                  <div className={`w-14 text-[11px] text-right ${r.delta>=0?'text-emerald-600':'text-red-600'}`}>{(r.delta*100>=0?'+':'')}{(r.delta*100).toFixed(1)}%</div>
                </div>
              ))}
              {worst.length === 0 && <div className="text-[12px] text-zinc-500">No data</div>}
            </div>
          </div>
        </div>
        <div className="mt-3 text-[11px] text-zinc-600">Bar: green/red = In‑filter %, grey = Baseline %</div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/30 flex items-start justify-center p-6">
      <div className="bg-white w-[960px] max-w-[96vw] rounded-lg shadow-xl border border-zinc-200 overflow-hidden">
        <div className="px-4 py-3 border-b flex items-center justify-between bg-zinc-50">
          <div className="font-semibold">Research Mode (Dev)</div>
          <div className="flex items-center gap-2">
            {progress && !progress.ready && (
              <button
                className="px-2 py-1 text-[12px] border rounded hover:bg-zinc-100"
                title="Stop background compile"
                onClick={stopActiveCompile}
              >Stop</button>
            )}
            <button
              className="px-2 py-1 text-[12px] border rounded hover:bg-zinc-100"
              title="Clear cache and recompile the dataset"
              onClick={forceRecompile}
            >Recompile (clear cache)</button>
            <button className="px-2 py-1 text-[12px] border rounded hover:bg-zinc-100" onClick={onClose}>Close</button>
          </div>
        </div>
        <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-3 md:col-span-1">
            <div>
              <label className="block text-[12px] text-zinc-600">CSV Path</label>
              <input value={path} onChange={e=> setPath(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]" />
              <div className="text-[11px] text-zinc-500 mt-1">Default: backend/Lotto(10).csv</div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[12px] text-zinc-600">Default Time</label>
                <input value={time} readOnly className="w-full px-2 py-1 border rounded text-[12px] bg-zinc-100 cursor-not-allowed" title="Hard-coded to Israel draw time" />
              </div>
              <div>
                <label className="block text-[12px] text-zinc-600">Row Limit</label>
                <input value={rowLimit} onChange={e=> setRowLimit(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]" placeholder="(blank = all)" />
              </div>
            </div>
            <div>
              <label className="block text-[12px] text-zinc-600">Location</label>
              <input value={location} readOnly className="w-full px-2 py-1 border rounded text-[12px] bg-zinc-100 cursor-not-allowed" title="Hard-coded to Tel Aviv, Israel" />
              <div className="text-[11px] text-zinc-500 mt-1">Fixed to Tel Aviv, Israel · Backend always compiles at 23:30 Israel time.</div>
            </div>
            <div className="pt-2 border-t">
              <div className="text-[12px] font-semibold mb-1">Add Filter</div>
              <div className="grid grid-cols-3 gap-2 items-end">
                <div>
                  <label className="block text-[12px] text-zinc-600">Type</label>
                  <select value={selType} onChange={e=> { const t=e.target.value; setSelType(t); setSelValue(t==='element'?'Water':'Cardinal'); }} className="w-full px-2 py-1 border rounded text-[12px]">
                    <option value="element">Element Balance</option>
                    <option value="modality">Modality Balance</option>
                    <option value="element_order">Element Order</option>
                    <option value="modality_order">Modality Order</option>
                    <option value="planet_position">Planet Position</option>
                    <option value="absolute_longitude">Absolute Longitude</option>
                    <option value="planet_house">Planet in House(s)</option>
                    <option value="ruler_in_house">Ruler of Cusp in House</option>
                    <option value="reception">Reception</option>
                    <option value="planet_direction">Planet Direction</option>
                    <option value="final_dispositor">Final Dispositor</option>
                  </select>
                </div>
                {(selType==='element' || selType==='modality') && (
                  <>
                    <div>
                      <label className="block text-[12px] text-zinc-600">Condition</label>
                      <select value={selMode} onChange={e=> setSelMode(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">
                        <option value="top">Top is</option>
                        <option value="zero">Share is 0</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[12px] text-zinc-600">Value</label>
                      <select value={selValue} onChange={e=> setSelValue(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">
                        {(selType==='element'?elements:modalities).map(v => <option key={v} value={v}>{v}</option>)}
                      </select>
                    </div>
                  </>
                )}
              </div>
              {/* Advanced filter editors */}
              {selType==='element_order' && (
                <div className="mt-2">
                  <label className="block text-[12px] text-zinc-600">Order (e.g., Water&gt;Earth&gt;Fire&gt;Air)</label>
                  <input value={orderExpr} onChange={e=> setOrderExpr(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]" />
                </div>
              )}
              {selType==='modality_order' && (
                <div className="mt-2">
                  <label className="block text-[12px] text-zinc-600">Order (e.g., Fixed&gt;Cardinal&gt;Mutable)</label>
                  <input value={modOrderExpr} onChange={e=> setModOrderExpr(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]" />
                </div>
              )}
              {selType==='planet_position' && (
                <div className="mt-2 grid grid-cols-6 gap-2 items-end">
                  <div className="col-span-2">
                    <label className="block text-[12px] text-zinc-600">Planet</label>
                    <select value={posPlanet} onChange={e=> setPosPlanet(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">
                      {planets.map(p=> <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div className="col-span-2">
                    <label className="block text-[12px] text-zinc-600">Sign (optional)</label>
                    <select value={posSign} onChange={e=> setPosSign(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">
                      <option value="">Any</option>
                      {signs.map(s=> <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[12px] text-zinc-600">Min°</label>
                    <input value={posMinDeg} onChange={e=> setPosMinDeg(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]" placeholder="0" />
                  </div>
                  <div>
                    <label className="block text-[12px] text-zinc-600">Max°</label>
                    <input value={posMaxDeg} onChange={e=> setPosMaxDeg(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]" placeholder="29.9" />
                  </div>
                </div>
              )}
              {selType==='absolute_longitude' && (
                <div className="mt-2 grid grid-cols-4 gap-2 items-end">
                  <div className="col-span-2">
                    <label className="block text-[12px] text-zinc-600">Planet</label>
                    <select value={posPlanet} onChange={e=> setPosPlanet(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{planets.map(p=> <option key={p} value={p}>{p}</option>)}</select>
                  </div>
                  <div>
                    <label className="block text-[12px] text-zinc-600">Lon min</label>
                    <input value={absLonMin||''} onChange={e=> setAbsLonMin(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]" placeholder="0" />
                  </div>
                  <div>
                    <label className="block text-[12px] text-zinc-600">Lon max</label>
                    <input value={absLonMax||''} onChange={e=> setAbsLonMax(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]" placeholder="360" />
                  </div>
                </div>
              )}
              {selType==='planet_house' && (
                <div className="mt-2 grid grid-cols-3 gap-2 items-end">
                  <div>
                    <label className="block text-[12px] text-zinc-600">Planet</label>
                    <select value={posPlanet} onChange={e=> setPosPlanet(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{planets.map(p=> <option key={p} value={p}>{p}</option>)}</select>
                  </div>
                  <div className="col-span-2">
                    <label className="block text-[12px] text-zinc-600">Houses (comma-separated)</label>
                    <input value={houseList||''} onChange={e=> setHouseList(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]" placeholder="1,10" />
                  </div>
                </div>
              )}
              {selType==='ruler_in_house' && (
                <div className="mt-2 grid grid-cols-2 gap-2 items-end">
                  <div>
                    <label className="block text-[12px] text-zinc-600">Cusp</label>
                    <select value={rulerCusp||'1'} onChange={e=> setRulerCusp(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{Array.from({length:12}, (_,i)=> String(i+1)).map(h=> <option key={h} value={h}>{h}</option>)}</select>
                  </div>
                  <div>
                    <label className="block text-[12px] text-zinc-600">In house</label>
                    <select value={rulerTarget||'1'} onChange={e=> setRulerTarget(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{Array.from({length:12}, (_,i)=> String(i+1)).map(h=> <option key={h} value={h}>{h}</option>)}</select>
                  </div>
                </div>
              )}
              {selType==='reception' && (
                <div className="mt-2 space-y-2">
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="block text-[12px] text-zinc-600">Kind</label>
                      <select value={recMode} onChange={e=> setRecMode(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">
                        <option value="mutual">Mutual</option>
                        <option value="unilateral">Unilateral</option>
                      </select>
                    </div>
                    {recMode==='mutual' && (
                      <>
                        <div>
                          <label className="block text-[12px] text-zinc-600">Planet A</label>
                          <select value={recP1} onChange={e=> setRecP1(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{planets.slice(0,7).map(p=> <option key={p} value={p}>{p}</option>)}</select>
                        </div>
                        <div>
                          <label className="block text-[12px] text-zinc-600">Planet B</label>
                          <select value={recP2} onChange={e=> setRecP2(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{planets.slice(0,7).map(p=> <option key={p} value={p}>{p}</option>)}</select>
                        </div>
                      </>
                    )}
                    {recMode==='unilateral' && (
                      <>
                        <div>
                          <label className="block text-[12px] text-zinc-600">Receiving</label>
                          <select value={recReceiving} onChange={e=> setRecReceiving(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{planets.slice(0,7).map(p=> <option key={p} value={p}>{p}</option>)}</select>
                        </div>
                        <div>
                          <label className="block text-[12px] text-zinc-600">Received</label>
                          <select value={recReceived} onChange={e=> setRecReceived(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{planets.slice(0,7).map(p=> <option key={p} value={p}>{p}</option>)}</select>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
              {selType==='planet_direction' && (
                <div className="mt-2 grid grid-cols-2 gap-2 items-end">
                  <div>
                    <label className="block text-[12px] text-zinc-600">Planet</label>
                    <select value={dirPlanet} onChange={e=> setDirPlanet(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{planets.map(p=> <option key={p} value={p}>{p}</option>)}</select>
                  </div>
                  <div>
                    <label className="block text-[12px] text-zinc-600">Direction</label>
                    <select value={dirMode} onChange={e=> setDirMode(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">
                      <option value="direct">Direct</option>
                      <option value="retrograde">Retrograde</option>
                    </select>
                  </div>
                </div>
              )}
              {selType==='final_dispositor' && (
                <div className="mt-2 grid grid-cols-2 gap-2 items-end">
                  <div>
                    <label className="block text-[12px] text-zinc-600">Planet</label>
                    <select value={fdPlanet} onChange={e=> setFdPlanet(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{planets.map(p=> <option key={p} value={p}>{p}</option>)}</select>
                  </div>
                  <div>
                    <label className="block text-[12px] text-zinc-600">Final Dispositor</label>
                    <select value={fdTarget} onChange={e=> setFdTarget(e.target.value)} className="w-full px-2 py-1 border rounded text-[12px]">{planets.slice(0,7).map(p=> <option key={p} value={p}>{p}</option>)}</select>
                  </div>
                </div>
              )}
              <div className="mt-2 flex items-center gap-2">
                <button
                  type="button"
                  className="px-3 py-1.5 text-[12px] rounded border bg-white hover:bg-zinc-50"
                  onClick={() => {
                    // Prevent duplicates of same filter
                    let f = null; let id = '';
                    if (selType==='element' || selType==='modality') {
                      id = `${selType}:${selMode}:${selValue}`;
                      f = { id, type: selType, mode: selMode, value: selValue };
                    } else if (selType==='element_order') {
                      const parts = orderExpr.split('>').map(s=> s.trim()).filter(Boolean);
                      id = `element_order:${parts.join('>')}`;
                      f = { id, type: 'element_order', values: parts };
                    } else if (selType==='modality_order') {
                      const parts = modOrderExpr.split('>').map(s=> s.trim()).filter(Boolean);
                      id = `modality_order:${parts.join('>')}`;
                      f = { id, type: 'modality_order', values: parts };
                    } else if (selType==='planet_position') {
                      const pf = { planet: posPlanet, sign: posSign || undefined, min_deg: posMinDeg ? Number(posMinDeg) : undefined, max_deg: posMaxDeg ? Number(posMaxDeg) : undefined };
                      id = `position:${pf.planet}:${pf.sign||'any'}:${pf.min_deg||''}-${pf.max_deg||''}`;
                      f = { id, type: 'position', ...pf };
                    } else if (selType==='absolute_longitude') {
                      const pf = { planet: posPlanet, lon_min: absLonMin ? Number(absLonMin) : undefined, lon_max: absLonMax ? Number(absLonMax) : undefined };
                      id = `abs:${pf.planet}:${pf.lon_min||''}-${pf.lon_max||''}`;
                      f = { id, type: 'position', ...pf };
                    } else if (selType==='planet_house') {
                      const houses = (houseList||'').split(',').map(s=> parseInt(s.trim(),10)).filter(n=> !isNaN(n) && n>=1 && n<=12);
                      id = `house:${posPlanet}:${houses.join(',')}`;
                      f = { id, type: 'house_pos', planet: posPlanet, houses };
                    } else if (selType==='ruler_in_house') {
                      const cusp = parseInt(rulerCusp||'1', 10);
                      const target = parseInt(rulerTarget||'1', 10);
                      id = `ruler:${cusp}->${target}`;
                      f = { id, type: 'ruler_in_house', cusp, in_house: target };
                    } else if (selType==='reception') {
                      if (recMode==='mutual') {
                        id = `reception:mutual:${recP1}-${recP2}`;
                        f = { id, type: 'reception', mode: 'mutual', p1: recP1, p2: recP2 };
                      } else {
                        id = `reception:unilateral:${recReceiving}->${recReceived}`;
                        f = { id, type: 'reception', mode: 'unilateral', receiving: recReceiving, received: recReceived };
                      }
                    } else if (selType==='planet_direction') {
                      id = `direction:${dirPlanet}:${dirMode}`;
                      f = { id, type: 'direction', planet: dirPlanet, direction: dirMode };
                    } else if (selType==='final_dispositor') {
                      id = `final:${fdPlanet}->${fdTarget}`;
                      f = { id, type: 'final_dispositor', planet: fdPlanet, final: fdTarget };
                    }
                    if (!f) return;
                    setFilters(prev => prev.find(x => x.id===id) ? prev : [...prev, f]);
                  }}
                >Add</button>
                <button disabled={busy} onClick={run} className={`px-3 py-1.5 text-[12px] rounded border ${busy? 'bg-zinc-200' : 'bg-white hover:bg-zinc-50'}`}>Run Analysis</button>
              </div>
              {filters.length>0 && (
                <div className="mt-3">
                  <div className="text-[12px] font-semibold">Active Filters</div>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {filters.map(f => {
                      let label = '';
                      if (f.type==='element' || f.type==='modality') label = `${f.type==='element'?'Element':'Modality'} · ${f.mode==='top'?'Top =':'Zero'} ${f.value}`;
                      else if (f.type==='element_order') label = `Element order · ${f.values.join('>')}`;
                      else if (f.type==='modality_order') label = `Modality order · ${f.values.join('>')}`;
                      else if (f.type==='position') label = `Position · ${f.planet} ${f.sign||''} ${f.min_deg!=null?f.min_deg:''}-${f.max_deg!=null?f.max_deg:''}° ${f.lon_min!=null?`[${f.lon_min}`:''}${f.lon_max!=null?`-${f.lon_max}]`:''}`;
                      else if (f.type==='house_pos') label = `House · ${f.planet} in H${(f.houses||[]).join(',')}`;
                      else if (f.type==='ruler_in_house') label = `Ruler of cusp ${f.cusp} in H${f.in_house}`;
                      else if (f.type==='reception') label = f.mode==='mutual' ? `Reception · mutual ${f.p1}-${f.p2}` : `Reception · ${f.receiving} receives ${f.received}`;
                      else if (f.type==='direction') label = `${f.planet} ${f.direction==='retrograde'?'retrograde':'direct'}`;
                      else if (f.type==='final_dispositor') label = `${f.planet} final dispositor ${f.final}`;
                      return (
                        <span key={f.id} className="text-[12px] px-2 py-0.5 border rounded-full bg-zinc-50">
                          {label}
                          <button className="ml-2 text-zinc-500 hover:text-zinc-700" onClick={()=> setFilters(prev => prev.filter(x => x.id !== f.id))}>×</button>
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
              {error && (<div className="mt-2 text-[12px] text-red-600">{error}</div>)}
              <div className="mt-2 text-[11px] text-zinc-500">Dev only. Uses Astro Clock metrics per CSV date.</div>
            </div>
          </div>
          <div className="md:col-span-2">
            {progress && !progress.ready && (
              <div className="mb-2 text-[12px] text-zinc-700">Compiling dataset… {progress.done||0}/{progress.total||0} ({Math.round((progress.percent||0)*100)}%)
                {progress.workers ? ` · ${progress.workers} workers` : ''}
              </div>
            )}
            {banner && (
              <div className="mb-2 text-[12px] px-2 py-1 rounded border bg-zinc-50">
                Dataset: {banner.source === 'cache' ? 'loaded from cache' : `compiled with ${banner.workers||1} worker(s)`} · rows: {banner.total||'—'}
              </div>
            )}
            {!result && !busy && (
              <div className="text-sm text-zinc-500">Configure filters and click Run Analysis.</div>
            )}
            {busy && (
              <div className="text-sm text-zinc-600">Processing…</div>
            )}
            {result && (
              <div>
                <div className="text-sm mb-2">Rows processed: {result.rows_processed} · Matched: {result.rows_matched}</div>
                <BarsBlock title="Numbers (1–6)" obj={result.numbers} />
                <BarsBlock title="Power Numbers" obj={result.power} />
                <div className="mt-4">
                  <NumbersTable title="Raw Table — Numbers (1–6)" obj={result.numbers} />
                  <NumbersTable title="Raw Table — Power Numbers" obj={result.power} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
