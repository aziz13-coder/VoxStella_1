import React, { useEffect, useMemo, useRef, useState } from 'react';
import { buildProfessionSuggestions, buildHealthSuggestions } from './knowledgeMap.mjs';
import { buildFixedStarProfessionSuggestions, buildFixedStarHealthSuggestions } from './fixedStarMap.mjs';
import { AstroClockAPI } from './api.mjs';
import TraitProfilePointsTab from './TraitProfilePointsTab.jsx';
import {
  formatSavedSnapLabel,
  getSavedSnapIneligibilityLabel,
  getSavedSnapDateTimeParts,
  getSavedSnapTimezoneLabel,
  isSavedSnapCalculationEligible,
} from './savedSnapViewModel.mjs';
import {
  POLARITY_META,
  buildDomainIndex,
  buildHouseDeterminationChannels,
  buildTopByPolarity,
  buildTraitProfileViewModel,
  normalizePolarity,
  normalizeScore,
} from './traitProfileViewModel.mjs';

function finiteNumberOrUndefined(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function firstPresent(...values) {
  for (const value of values) {
    if (value == null) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return undefined;
}

function snapDashboard(snap) {
  return snap?.dashboard && typeof snap.dashboard === 'object' ? snap.dashboard : {};
}

function snapCoordinates(snap) {
  const dashboard = snapDashboard(snap);
  const latitude = finiteNumberOrUndefined(
    snap?.latitude ?? dashboard?.latitude ?? snap?.coordinates?.latitude ?? snap?.coordinates?.lat ?? snap?.chart_snapshot?.latitude,
  );
  const longitude = finiteNumberOrUndefined(
    snap?.longitude ?? dashboard?.longitude ?? snap?.coordinates?.longitude ?? snap?.coordinates?.lon ?? snap?.coordinates?.lng ?? snap?.chart_snapshot?.longitude,
  );
  return { latitude, longitude };
}

function getSnapMetaParts(snap) {
  const dashboard = snapDashboard(snap);
  const label = firstPresent(snap?.label, snap?.id, 'Untitled snap') || 'Untitled snap';
  const iso = firstPresent(snap?.effective_datetime, dashboard?.timestamp, snap?.datetime, snap?.timestamp);
  const location = firstPresent(snap?.location, dashboard?.location);
  const timezone = getSavedSnapTimezoneLabel(snap);
  const { datePart, timePart } = getSavedSnapDateTimeParts(snap);
  return { label, datePart, timePart, location, timezone, iso };
}

function formatSnapLabel(snap) {
  return formatSavedSnapLabel(snap);
}

function snapToTraitClockContext(snap, houseSystem) {
  if (!snap) return null;
  const dashboard = snapDashboard(snap);
  const datetime = firstPresent(snap?.effective_datetime, dashboard?.timestamp, snap?.datetime, snap?.timestamp);
  const location = firstPresent(snap?.location, dashboard?.location);
  const timezone = firstPresent(snap?.timezone, dashboard?.timezone, snap?.timezone_label, dashboard?.timezone_label);
  const selectedHouseSystem = firstPresent(houseSystem, snap?.house_system_code, dashboard?.house_system_code, snap?.house_system, dashboard?.house_system);
  const { latitude, longitude } = snapCoordinates(snap);
  if (!datetime) return null;
  return {
    mode: 'manual',
    datetime,
    location,
    timezone,
    houseSystem: selectedHouseSystem,
    latitude,
    longitude,
  };
}

function snapshotFromSnap(snap, fallbackSnapshot) {
  if (!snap) return fallbackSnapshot;
  const dashboard = snapDashboard(snap);
  const base = dashboard && Object.keys(dashboard).length ? dashboard : {};
  return {
    ...base,
    timestamp: firstPresent(dashboard?.timestamp, snap?.effective_datetime, snap?.datetime, snap?.timestamp) || base.timestamp || null,
    location: firstPresent(dashboard?.location, snap?.location) || base.location || null,
    timezone: firstPresent(dashboard?.timezone, snap?.timezone) || base.timezone || null,
    timezone_label: firstPresent(dashboard?.timezone_label, snap?.timezone_label, snap?.timezone) || base.timezone_label || null,
    latitude: finiteNumberOrUndefined(dashboard?.latitude ?? snap?.latitude) ?? base.latitude,
    longitude: finiteNumberOrUndefined(dashboard?.longitude ?? snap?.longitude) ?? base.longitude,
  };
}

function buildTraitClockContext({ mode, manualIso, manualLocation, timezone, latitude, longitude, houseSystem, chartSource, selectedSnap }) {
  if (chartSource === 'snap') {
    const snapContext = snapToTraitClockContext(selectedSnap, houseSystem);
    if (snapContext) return snapContext;
  }
  const resolvedLatitude = finiteNumberOrUndefined(latitude);
  const resolvedLongitude = finiteNumberOrUndefined(longitude);
  const coords = resolvedLatitude != null && resolvedLongitude != null
    ? { latitude: resolvedLatitude, longitude: resolvedLongitude }
    : {};
  if (mode === 'manual' && manualIso) {
    return {
      mode: 'manual',
      datetime: manualIso,
      location: manualLocation || undefined,
      timezone: timezone || undefined,
      ...coords,
      houseSystem,
    };
  }
  return {
    mode: 'realtime',
    location: manualLocation || undefined,
    timezone: timezone || undefined,
    ...coords,
    houseSystem,
  };
}

export default function TraitProfileModal({
  onClose,
  specialDegrees,
  mode,
  manualIso,
  manualLocation,
  timezone,
  latitude,
  longitude,
  houseSystem,
  chartSnapshot = null,
  fixedStarHits: initialFixedStarHits = [],
  snaps = [],
  activeSnapId = '',
  loadingSnaps = false,
  snapsLoaded = true,
  onRefreshSnaps,
}){
  const dialogRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [fixedStarHits, setFixedStarHits] = useState(Array.isArray(initialFixedStarHits) ? initialFixedStarHits : []);
  const snapOptions = useMemo(() => (Array.isArray(snaps) ? snaps : []).filter((snap) => snap?.id), [snaps]);
  const eligibleSnapOptions = useMemo(
    () => snapOptions.filter((snap) => isSavedSnapCalculationEligible(snap)),
    [snapOptions],
  );
  const initialActiveSnapIsEligible = Boolean(
    activeSnapId
      && eligibleSnapOptions.some((snap) => String(snap?.id || '') === String(activeSnapId)),
  );
  const [chartSource, setChartSource] = useState(initialActiveSnapIsEligible ? 'snap' : 'current');
  const [selectedSnapId, setSelectedSnapId] = useState(activeSnapId || '');
  const selectedSnap = useMemo(
    () => eligibleSnapOptions.find((snap) => String(snap?.id || '') === String(selectedSnapId || '')) || null,
    [eligibleSnapOptions, selectedSnapId],
  );
  // UI state for filters/sort
  const [band, setBand] = useState('all'); // all|strong|likely|possible
  const [polarity, setPolarity] = useState('all'); // all|positive|neutral|negative
  const [sortBy, setSortBy] = useState('score'); // score|name|polarity
  const [topCount, setTopCount] = useState(6);
  const [selectedDomains, setSelectedDomains] = useState([]); // empty means all
  const [domainOpen, setDomainOpen] = useState(false);
  const [domainSearch, setDomainSearch] = useState('');
  const [activeTab, setActiveTab] = useState('overview');
  const [activeDomain, setActiveDomain] = useState(null);
  const [selectedTrait, setSelectedTrait] = useState(null);
  const domainRef = useRef(null);
  const activeChartSnapshot = useMemo(
    () => (chartSource === 'snap' && selectedSnap ? snapshotFromSnap(selectedSnap, chartSnapshot) : chartSnapshot),
    [chartSource, selectedSnap, chartSnapshot],
  );
  const chartContext = useMemo(
    () => buildTraitClockContext({ mode, manualIso, manualLocation, timezone, latitude, longitude, houseSystem, chartSource, selectedSnap }),
    [mode, manualIso, manualLocation, timezone, latitude, longitude, houseSystem, chartSource, selectedSnap],
  );
  const chartContextKey = JSON.stringify(chartContext);
  const traitApiContext = useMemo(
    () => (
      chartSource === 'snap' && selectedSnap?.id
        ? {
          snapId: String(selectedSnap.id),
          houseSystem: chartContext?.houseSystem || houseSystem,
        }
        : chartContext
    ),
    [chartContext, chartSource, houseSystem, selectedSnap],
  );
  const traitApiContextKey = JSON.stringify(traitApiContext);
  const effectiveSpecialDegrees = useMemo(
    () => (chartSource === 'snap' && selectedSnap && Array.isArray(selectedSnap.special_degrees)
      ? selectedSnap.special_degrees
      : specialDegrees),
    [chartSource, selectedSnap, specialDegrees],
  );
  const specialDegreesKey = JSON.stringify(Array.isArray(effectiveSpecialDegrees) ? effectiveSpecialDegrees : []);

  useEffect(() => {
    if (!activeSnapId) return;
    const activeSnap = snapOptions.find(
      (snap) => String(snap?.id || '') === String(activeSnapId),
    );
    if (!activeSnap) return;
    if (!isSavedSnapCalculationEligible(activeSnap)) {
      setSelectedSnapId('');
      setChartSource('current');
      return;
    }
    setSelectedSnapId(String(activeSnapId));
    setChartSource('snap');
  }, [activeSnapId, snapOptions]);

  useEffect(() => {
    if (chartSource === 'snap' && !selectedSnap && eligibleSnapOptions.length) {
      setSelectedSnapId(String(eligibleSnapOptions[0].id || ''));
    }
    if (chartSource === 'snap' && selectedSnapId && !selectedSnap && !eligibleSnapOptions.length) {
      setSelectedSnapId('');
    }
  }, [chartSource, eligibleSnapOptions, selectedSnap, selectedSnapId]);

  useEffect(() => {
    if (typeof onRefreshSnaps !== 'function') return;
    if (snapsLoaded && snapOptions.length) return;
    onRefreshSnaps({ silent: true });
  }, [onRefreshSnaps, snapsLoaded, snapOptions.length]);

  useEffect(() => {
    let alive = true;
    (async () => {
      if (chartSource === 'snap' && !selectedSnap) {
        setData(null);
        setError(loadingSnaps ? null : (snapOptions.length ? 'Choose a saved snap.' : 'No saved snaps are available yet.'));
        setLoading(Boolean(loadingSnaps));
        return;
      }
      try {
        setLoading(true); setError(null);
        const res = await AstroClockAPI.getTraitProfile({
          specialDegrees: effectiveSpecialDegrees,
          ...traitApiContext,
        });
        if (!alive) return;
        if (res?.success) setData(res.data || {});
        else setError('Failed to load');
      } catch (e) {
        if (!alive) return; setError(String(e?.message || 'Failed to load'));
      } finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [chartSource, selectedSnap, loadingSnaps, snapOptions.length, specialDegreesKey, chartContextKey, traitApiContextKey]);

  useEffect(() => {
    setFixedStarHits(Array.isArray(initialFixedStarHits) ? initialFixedStarHits : []);
  }, [initialFixedStarHits]);

  // Copy-to-clipboard support for AI prompt
  const [copying, setCopying] = useState(false);
  const [copied, setCopied] = useState(false);

  async function safeCopyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        ta.style.pointerEvents = 'none';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        const ok = document.execCommand('copy');
        document.body.removeChild(ta);
        return ok;
      } catch (_) {
        return false;
      }
    }
  }

  function resolveTraitChartSnapshot(payload, opts = {}) {
    const src = (payload?.chart_snapshot && typeof payload.chart_snapshot === 'object') ? payload.chart_snapshot : {};
    const fallback = (opts.chartSnapshot && typeof opts.chartSnapshot === 'object') ? opts.chartSnapshot : {};
    const fixedStars = Array.isArray(opts.fixedStarHits) ? opts.fixedStarHits : [];
    const preferArray = (primary, secondary) => {
      if (Array.isArray(primary) && primary.length) return primary;
      if (Array.isArray(secondary) && secondary.length) return secondary;
      return [];
    };
    const preferObject = (primary, secondary) => {
      if (primary && typeof primary === 'object' && !Array.isArray(primary) && Object.keys(primary).length) return primary;
      if (secondary && typeof secondary === 'object' && !Array.isArray(secondary) && Object.keys(secondary).length) return secondary;
      return null;
    };
    return {
      timestamp: src.timestamp || fallback.timestamp || null,
      location: src.location || fallback.location || null,
      timezone: src.timezone || fallback.timezone || null,
      timezone_label: src.timezone_label || fallback.timezone_label || null,
      house_system: src.house_system || fallback.house_system || houseSystem || null,
      ascendant: src.ascendant ?? fallback.ascendant ?? null,
      midheaven: src.midheaven ?? fallback.midheaven ?? null,
      planets: preferArray(src.planets, fallback.planets),
      moon: src.moon || fallback.moon || null,
      moon_timeline: src.moon_timeline || fallback.moon_timeline || null,
      solar_conditions: src.solar_conditions || fallback.solar_conditions || null,
      top_aspects: preferArray(src.top_aspects, fallback.top_aspects),
      morin_aspects: preferArray(src.morin_aspects, fallback.morin_aspects),
      fixed_star_hits: preferArray(src.fixed_star_hits, fixedStars.length ? fixedStars : fallback.fixed_star_hits),
      house_cusps: preferArray(src.house_cusps, fallback.house_cusps),
      house_rulers: preferObject(src.house_rulers, fallback.house_rulers) || {},
      receptions: src.receptions || payload?.receptions || fallback.receptions || null,
      special_degrees: preferArray(src.special_degrees, payload?.special_degrees || fallback.special_degrees),
      morin_patterns: src.morin_patterns || payload?.morin_patterns || fallback.morin_patterns || null,
    };
  }

  function buildTraitAnalysisPrompt(payload, opts = {}) {
    // Build compact payload for AI to avoid overlong messages
    const compact = (() => {
      const src = payload || {};
      const liveChart = resolveTraitChartSnapshot(src, opts);
      const out = {
        chart_context: {
          timestamp: liveChart.timestamp,
          location: liveChart.location,
          timezone: liveChart.timezone,
          timezone_label: liveChart.timezone_label,
          house_system: liveChart.house_system,
          ascendant: liveChart.ascendant,
          midheaven: liveChart.midheaven,
        },
        ui_filters: {
          band: opts.band || 'all',
          polarity: opts.polarity || 'all',
          sort: opts.sortBy || 'score',
          top: opts.topCount || null,
          selected_domains: Array.isArray(opts.selectedDomains) ? opts.selectedDomains : [],
        },
        summary: src.summary || null,
        special_degrees: liveChart.special_degrees,
        receptions: liveChart.receptions,
        sect: src.sect || null,
        morin_patterns: liveChart.morin_patterns,
        top_traits: Array.isArray(src.top_traits) ? src.top_traits.map(t => ({
          id: t.id, name: t.name, score: t.score, band: t.band, polarity: t.polarity, domain: t.domain,
        })) : [],
        visible_traits: Array.isArray(opts.visibleTraits) ? opts.visibleTraits.map(t => ({
          id: t.id,
          name: t.name,
          score: t.score,
          band: t.band,
          polarity: t.polarity,
          domain: t.domain,
        })) : [],
        planet_strengths: (src?.house_influences?.planet_strengths ? src.house_influences.planet_strengths : null),
        chart_factors: {
          planets: (Array.isArray(liveChart.planets) ? liveChart.planets : []).map((p) => ({
            planet: p?.planet || null,
            sign: p?.sign || null,
            house: p?.house ?? null,
            longitude: p?.longitude ?? null,
            dignity_score: p?.dignity_score ?? null,
            essential_dignity: p?.essential_dignity ?? null,
            accidental_dignity: p?.accidental_dignity ?? null,
            retrograde: !!p?.retrograde,
          })),
          moon: liveChart.moon || null,
          moon_timeline: liveChart.moon_timeline || null,
          solar_conditions: liveChart.solar_conditions || null,
          top_aspects: (Array.isArray(liveChart.top_aspects) ? liveChart.top_aspects : []).slice(0, 12),
          morin_aspects: (Array.isArray(liveChart.morin_aspects) ? liveChart.morin_aspects : []).slice(0, 12),
          house_cusps: Array.isArray(liveChart.house_cusps) ? liveChart.house_cusps : [],
          house_rulers: liveChart.house_rulers || {},
          fixed_star_hits: Array.isArray(liveChart.fixed_star_hits) ? liveChart.fixed_star_hits : [],
        },
        houses: [],
      };
      const houses = src?.house_influences?.houses || [];
      for (const h of Array.isArray(houses) ? houses : []) {
        const ba = h?.basic_analysis || {};
        const det = ba?.determinators_panel || {};
        const presence = Array.isArray(det.presence) && det.presence.length ? det.presence[0] : null;
        const governance = Array.isArray(det.governance) && det.governance.length ? det.governance[0] : null;
        const aspect = Array.isArray(det.aspect) && det.aspect.length ? det.aspect[0] : null;
        // Engine influences: include top 4 with keywords for determination context
        const topInfluences = (Array.isArray(h?.influences) ? h.influences : []).slice(0,4).map(inf => ({
          planet: inf?.planet || null,
          type: inf?.type || null,
          aspect: inf?.aspect || null,
          co_kind: inf?.co_kind || null,
          value: inf?.value,
          rank: inf?.rank || null,
          keywords: Array.isArray(inf?.keywords) ? inf.keywords : [],
        }));
        // Basic Analysis: location summaries and main aspects to cusp (trimmed)
        const locSummaries = (Array.isArray(ba?.location) ? ba.location : []).slice(0,3).map(li => ({
          planet: li?.planet || null,
          summary: li?.summary || null,
          state: li?.state ? {
            strong: !!li.state.strong,
            dignified: !!li.state.dignified,
            afflicted: !!li.state.afflicted,
            solar_condition: li.state.solar_condition || null,
          } : null,
          main_aspects_to_cusp: Array.isArray(li?.main_aspects_to_cusp) ? li.main_aspects_to_cusp.slice(0,2).map(a => ({
            aspect: a?.aspect || null,
            orb: a?.orb,
            phase: a?.phase || null,
            dexter: !!a?.dexter,
            afflicting: !!a?.afflicting,
          })) : [],
        }));
        out.houses.push({
          house: h.house,
          sign: h.sign,
          overview: ba?.overview ? {
            cusp_sign: ba.overview.cusp_sign || null,
            ruler: ba.overview.ruler || null,
            exaltation: ba.overview.exaltation || null,
            triplicity_ruler: ba.overview.triplicity_ruler || null,
          } : null,
          route: ba?.route_line || null,
          synthesis: Array.isArray(ba?.synthesis) ? ba.synthesis.slice(0,3) : [],
          ruler_map: ba?.ruler_map || null,
          aspect_top: Array.isArray(ba?.aspect_top) ? ba.aspect_top : [],
          cues: ba?.cues || null,
          conflicts: ba?.conflicts || [],
          influences: topInfluences,
          basic_analysis: {
            location: locSummaries,
            primary: ba?.primary_determinator || null,
          },
          determinators: {
            presence: presence ? { planet: presence.planet, rank: presence.rank, adverb: presence.adverb || null, keywords: presence.keywords || [], analogy: presence.analogy || null, note: presence.note || null } : null,
            governance: governance ? { planet: governance.planet, type: governance.type, adverb: governance.adverb || null, keywords: governance.keywords || [], analogy: governance.analogy || null, note: governance.note || null } : null,
            aspect: aspect ? { planet: aspect.planet, aspect: aspect.aspect, orb: aspect.orb, phase: aspect.phase, phrase: aspect.phrase, adverb: aspect.adverb || null, keywords: aspect.keywords || [], note: aspect.note || null } : null,
          },
        });
      }
      // (Consolidated topic_maps assembly below)
      // Topic maps summary for export (Profession via 10th; Health via 1st/6th)
      try {
        const pick = (n) => out.houses.find(h => Number(h?.house) === Number(n));
        const h10 = pick(10);
        const h1 = pick(1);
        const h6 = pick(6);
        const mk = (h) => h ? ({
          house: h.house,
          sign: h.sign,
          overview: h.overview || null,
          determinators: h.determinators || null,
          top_location: Array.isArray(h?.basic_analysis?.location) && h.basic_analysis.location.length ? h.basic_analysis.location[0] : null,
          top_aspect: Array.isArray(h?.aspect_top) && h.aspect_top.length ? h.aspect_top[0] : null,
          route: h.route || null,
          ruler_notes: h?.ruler_map ? ({ conditions: h.ruler_map.conditions || null, dispositor: h.ruler_map.dispositor || null }) : null,
          morin_notes: null,
        }) : null;
        const prof = mk(h10);
        let hFirst = mk(h1);
        let hSixth = mk(h6);
        // Compose brief Morin notes (mirrors UI logic; safe, no calculations changed)
        const mkNotesProfession = () => {
          const ns = [];
          if (!prof) return ns;
          try {
            const a = prof?.top_aspect;
            if (a) {
              const malef = ['Saturn','Mars'].includes(String(a?.planet||''));
              const benef = ['Jupiter','Venus'].includes(String(a?.planet||''));
              if (a?.afflicting && malef) ns.push('Applying malefic affliction to MC cusp - career obstacles.');
              if (!a?.afflicting && ['Trine','Sextile'].includes(String(a?.aspect||'')) && benef) ns.push('Benefic support to MC cusp - advancement potential.');
            }
          } catch (_) {}
          return ns.slice(0,3);
        };
        const mkNotesHealth = () => {
          const ns = [];
          try {
            const a1 = hFirst?.top_aspect;
            if (a1) {
              const malef = ['Saturn','Mars'].includes(String(a1?.planet||''));
              const benef = ['Jupiter','Venus'].includes(String(a1?.planet||''));
              if (a1?.afflicting && malef) ns.push('Malefic affliction to ASC cusp - strain to constitution.');
              if (!a1?.afflicting && ['Trine','Sextile'].includes(String(a1?.aspect||'')) && benef) ns.push('Benefic support to ASC cusp - constitutional help.');
            }
          } catch (_) {}
          try {
            const a6 = hSixth?.top_aspect;
            if (a6) {
              const malef = ['Saturn','Mars'].includes(String(a6?.planet||''));
              const benef = ['Jupiter','Venus'].includes(String(a6?.planet||''));
              if (a6?.afflicting && malef) ns.push('Malefic affliction to H6 cusp - illness risk/activation.');
              if (!a6?.afflicting && ['Trine','Sextile'].includes(String(a6?.aspect||'')) && benef) ns.push('Benefic aspect to H6 cusp - mitigation/aid.');
            }
          } catch (_) {}
          return ns.slice(0,4);
        };
        if (prof) prof.morin_notes = mkNotesProfession();
        if (hFirst) hFirst.morin_notes = [];
        if (hSixth) hSixth.morin_notes = [];

        // Build suggestions using knowledge maps; add fixed-star helpers if provided
        try {
            const fsHits = Array.isArray(liveChart.fixed_star_hits) ? liveChart.fixed_star_hits : [];
          const profSugs = (typeof buildProfessionSuggestions === 'function') ? buildProfessionSuggestions(h10, { h2, h6, h4 }) : [];
          const profStar = (typeof buildFixedStarProfessionSuggestions === 'function') ? buildFixedStarProfessionSuggestions(fsHits) : [];
          const merge = (a,b) => {
            const acc = new Map();
            [...a, ...b].forEach(s => {
              const k = s.label;
              const prev = acc.get(k);
              if (!prev || Number(s.weight||0) > Number(prev.weight||0)) acc.set(k, s);
            });
            return Array.from(acc.values());
          };
          const profAll = merge(profSugs, profStar);
          if (prof) prof.suggestions = profAll;

          const healthSugs = (typeof buildHealthSuggestions === 'function') ? buildHealthSuggestions(h1, h6, pick(12), { morinStrict }) : [];
          const healthStar = (typeof buildFixedStarHealthSuggestions === 'function') ? buildFixedStarHealthSuggestions(fsHits) : [];
          const healthAll = merge(healthSugs, healthStar);
          // Enrich topic maps with triplicity shares, supports, and morin_strict heuristic
          const pickSrc = (n) => (Array.isArray(src?.house_influences?.houses) ? src.house_influences.houses : []).find(h => Number(h?.house) === Number(n));
          const shares = (hSrc) => {
            const list = Array.isArray(hSrc?.influences) ? hSrc.influences : [];
            let p=0,g=0,a=0; for (const it of list){ const v=Math.abs(Number(it?.value||0)); const t=String(it?.type||''); if (t==='occupation') p+=v; else if (t==='rulership'||t==='co_rulership') g+=v; else if (t==='aspect') a+=v; }
            const tot = p+g+a || 1; const q=(x)=> x/tot; const dots=(qv)=> (qv>=0.55?'+++':(qv>=0.30?'++':(qv>0?'+':'-')));
            return { presence: dots(q(p)), governance: dots(q(g)), aspect: dots(q(a)) };
          };
          const asList = (x) => x ? (Array.isArray(x) ? x : [x]) : [];
          const supports = (hObj) => {
            try {
              const det = hObj?.determinators || {};
              const all = [...asList(det?.presence), ...asList(det?.governance), ...asList(det?.aspect)];
              const s = []; if (all.some(x=>x?.planet==='Sun')) s.push('Sun'); if (all.some(x=>x?.planet==='Jupiter')) s.push('Jupiter'); return s;
            } catch { return []; }
          };
          const sumInf = (hSrc) => {
            const list = Array.isArray(hSrc?.influences)? hSrc.influences:[];
            let pres=0, gov=0, asp=0;
            for (const it of list){ const v=Math.abs(Number(it?.value||0)); const t=String(it?.type||''); if (t==='occupation') pres+=v; else if (t==='rulership'||t==='co_rulership') gov+=v; else if (t==='aspect') asp+=v; }
            return (pres*1.0) + (gov*0.9) + (asp*0.6);
          };
          const h6Src = pickSrc(6); const h12Src = pickSrc(12);
          const morinStrict = (sumInf(h12Src) > sumInf(h6Src));
          const profShares = { H2: shares(pickSrc(2)), H6: shares(pickSrc(6)), H10: shares(pickSrc(10)) };
          const healthShares = morinStrict ? ({ H1: shares(pickSrc(1)), H12: shares(pickSrc(12)) }) : ({ H1: shares(pickSrc(1)), H6: shares(pickSrc(6)), H12: shares(pickSrc(12)) });
          // Triplicity supporters: H2 and H6 occupants (state summary)
          const mkSupporter = (house) => {
            try {
              if (!house) return null;
              const loc = Array.isArray(house?.basic_analysis?.location) ? house.basic_analysis.location : [];
              if (!loc.length) return null;
              const li = loc[0] || {};
              const st = li?.state || {};
              return { house: Number(house?.house), planet: li?.planet || null, state: { strong: !!st.strong, dignified: !!st.dignified, afflicted: !!st.afflicted, solar_condition: st.solar_condition || null } };
            } catch(_) { return null; }
          };
          const supporters = [mkSupporter(pickSrc(2)), mkSupporter(pickSrc(6))].filter(Boolean);
          out.topic_maps = {
            profession: {
              ...(prof||{}),
              triplicity: { name: 'Action', houses: [2,6,10], shares: profShares },
              supports: supports(h10) || [],
              supporters
            },
            health: {
              first: hFirst, sixth: hSixth, morin_notes: mkNotesHealth(), suggestions: healthAll,
              morin_strict: !!morinStrict,
              triplicity: morinStrict ? { primary: [1,12], context: [4,8], name: 'Suffering', shares: healthShares } : { primary: [1,6], context: [12], name: 'Life+Service', shares: healthShares },
              supports: supports(morinStrict ? pick(12) : h1) || []
            }
          };
            out.fixed_star_hits = fsHits;
          } catch (_) {
            out.topic_maps = { profession: prof, health: { first: hFirst, sixth: hSixth, morin_notes: mkNotesHealth(), morin_strict: false } };
          }
        } catch (_) {}
        return out;
    })();

    const header = [
      "You are an astrologer analyzing a trait profile using Morin's determinations.",
      'Strict priority: Location > Rulership > Aspectual; color by state (dignity/debility, combustion, retrograde, angularity).',
      'Task: Provide a concise, predictive synthesis with clear house-level findings.',
      '',
      'Glossary: applying=form; separating=wane; partile<=1 degree (very strong); dexter=preceding; sinister=following; trine=strongest benefic; opposition=strongest malefic.',
      '',
      'Reasoning: Think deeply through the hierarchy at each house (presence > governance > aspect). Weigh indications carefully; avoid superficial readings.',
      'Conflicts: When indicators disagree, resolve contradictions per Morin\'s hierarchy. Note any key contradictions and how the hierarchy adjudicates them.',
      '',
      'Output structure:',
      '1) High-level summary (2–3 bullets)',
      '2) Planet highlights (top strengths/weaknesses; state notes; 4–6 bullets)',
      '3) House determinations (for notable houses, 1–2 bullets):',
      '   - Location: Planet in House - effect',
      '   - Rulership: Ruler of N in M - pattern (secondary), with ruler map conditions',
      '   - Aspectual: top applying aspect(s) to Cusp N with phase/partile/dexter notes (tertiary)',
      '4) Complex patterns: identify any present complex configurations (e.g., translation, besiegement, doryphory, mediation, preemptive transfer, frustration) and briefly explain their meanings'
    ].join('\n');
    const jsonBlock = '```json\n' + JSON.stringify(compact, null, 2) + '\n```';
    return `${header}\n\nData:\n${jsonBlock}`;
  }

  const copyAiPrompt = async () => {
      try {
        setCopying(true);
        let fresh = null;
        try {
          const res = await AstroClockAPI.getTraitProfile({ specialDegrees, ...traitApiContext });
          if (res?.success) fresh = res.data;
        } catch (_) {}
        const payload = fresh || data || {};
      const prompt = buildTraitAnalysisPrompt(payload, {
        fixedStarHits,
        chartSnapshot: activeChartSnapshot,
        band,
        polarity,
        sortBy,
        topCount,
        selectedDomains,
        visibleTraits: filteredTraits.slice(0, topCount),
      });
        const ok = await safeCopyText(prompt);
        setCopied(!!ok);
        if (ok) setTimeout(() => setCopied(false), 2200);
      } finally {
        setCopying(false);
    }
  };

  // Domains present in result
  const rawTraits = useMemo(() => Array.isArray(data?.traits) ? data.traits : [], [data?.traits]);
  const domainIndex = useMemo(
    () => buildDomainIndex(rawTraits, { selectedDomains, domainSearch }),
    [rawTraits, selectedDomains, domainSearch],
  );
  const allDomains = useMemo(() => {
    return domainIndex.allDomains;
  }, [domainIndex.allDomains]);

  // Initialize selected domains to all when data arrives
  useEffect(() => {
    if (allDomains.length && selectedDomains.length === 0) {
      setSelectedDomains(allDomains);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allDomains.join('|')]);

  const toggleDomain = (dom) => {
    setSelectedDomains(prev => {
      if (prev.includes(dom)) return prev.filter(d => d !== dom);
      return [...prev, dom];
    });
  };

  const filteredDomainList = useMemo(() => {
    const q = domainSearch.trim().toLowerCase();
    if (!q) return allDomains;
    return allDomains.filter(d => d.toLowerCase().includes(q));
  }, [allDomains, domainSearch]);

  useEffect(() => {
    if (!allDomains.length) {
      setActiveDomain(null);
      return;
    }
    if (!activeDomain || !allDomains.includes(activeDomain)) {
      setActiveDomain(allDomains[0]);
    }
  }, [allDomains, activeDomain]);

  useEffect(() => {
    if (!domainOpen) return;
    const onDoc = (e) => {
      if (domainRef.current && !domainRef.current.contains(e.target)) setDomainOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [domainOpen]);

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    dialogRef.current?.focus();
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('keydown', closeOnEscape);
      previouslyFocused?.focus?.();
    };
  }, [onClose]);

  const allTraits = rawTraits;
  const backendTopTraits = useMemo(() => Array.isArray(data?.top_traits) ? data.top_traits : [], [data?.top_traits]);
  const backendSummaryTraits = useMemo(() => Array.isArray(data?.summary_traits) ? data.summary_traits : [], [data?.summary_traits]);
  const backendTopTraitsByPolarity = useMemo(() => {
    const src = data?.top_traits_by_polarity;
    return (src && typeof src === 'object') ? src : {};
  }, [data?.top_traits_by_polarity]);
  const representativeTraits = useMemo(() => {
    const list = allTraits.filter((t) => t?.family_representative !== false);
    return list.length ? list : allTraits;
  }, [allTraits]);

  const summaryTraits = useMemo(() => {
    const backendSummary = backendSummaryTraits.filter((t) => t?.summary_eligible !== false);
    const eligibleReps = representativeTraits.filter((t) => t?.summary_eligible !== false);
    const base = backendSummary.length
      ? backendSummary
      : (eligibleReps.length ? eligibleReps : representativeTraits);
    const curated = base.filter((t) => !t?.provisional && String(t?.source_status || '').toLowerCase() !== 'provisional');
    return curated.length ? curated : base;
  }, [backendSummaryTraits, representativeTraits]);

  const filteredTraits = useMemo(() => {
    let list = allTraits;
    if (band !== 'all') list = list.filter(t => String(t.band || '').toLowerCase() === band);
    if (polarity !== 'all') list = list.filter(t => String(t.polarity || '').toLowerCase() === polarity);
    if (selectedDomains.length) list = list.filter(t => !t.domain || selectedDomains.includes(String(t.domain)));
    const cmpName = (a, b) => String(a?.name || a?.id || '').localeCompare(String(b?.name || b?.id || ''));
    const polRank = (p) => ({ positive: 0, neutral: 1, negative: 2 })[String(p || '').toLowerCase()] ?? 3;
    const sorter = (a, b) => {
      if (sortBy === 'name') return cmpName(a, b);
      if (sortBy === 'polarity') return polRank(a.polarity) - polRank(b.polarity) || cmpName(a, b);
      // score default: high to low
      const da = Number(a?.score || 0), db = Number(b?.score || 0);
      return (db - da) || cmpName(a, b);
    };
    return [...list].sort(sorter);
  }, [allTraits, band, polarity, selectedDomains, sortBy]);

  const hasFilteredTraits = filteredTraits.length > 0;
  const hasPartialDomains = allDomains.length > 0 && selectedDomains.length > 0 && selectedDomains.length !== allDomains.length;
  const hasActiveTraitFilters = band !== 'all' || polarity !== 'all' || hasPartialDomains;

  const resetTraitFilters = () => {
    setBand('all');
    setPolarity('all');
    setSelectedDomains(allDomains);
    setDomainSearch('');
    setDomainOpen(false);
  };

  // Top X by polarity (apply strength/domain filters; polarity overridden by section)
  const topBuckets = useMemo(() => buildTopByPolarity(data, {
    band,
    selectedDomains,
    topCount,
  }), [data, band, selectedDomains, topCount]);
  const topByPolarity = useMemo(() => ({
    pos: topBuckets.positive || [],
    neutral: topBuckets.neutral || [],
    neg: topBuckets.negative || [],
  }), [topBuckets]);
  const traitView = useMemo(() => buildTraitProfileViewModel(data, {
    filters: {
      band,
      polarity,
      sortBy,
      topCount,
      selectedDomains,
      domainSearch,
    },
    chartContext,
    mode,
    houseSystem,
    chartSnapshot: activeChartSnapshot,
    fixedStarHits,
  }), [data, band, polarity, sortBy, topCount, selectedDomains, domainSearch, chartContext, mode, houseSystem, activeChartSnapshot, fixedStarHits]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="trait-profile-title"
        tabIndex={-1}
        className="max-w-6xl relative flex w-full flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-[0_30px_80px_rgba(20,20,18,0.18),0_4px_16px_rgba(20,20,18,0.06)]"
        style={{ width: 'min(1380px, 96vw)', maxWidth: 1380, height: 'min(900px, 92vh)' }}
      >
        <TraitProfileHeader
          copied={copied}
          copying={copying}
          disabled={copying || loading || !data}
          modeLabel={traitView.chart.modeLabel}
          onClose={onClose}
          onCopy={copyAiPrompt}
        />
        <TraitSubjectStrip view={traitView} houseSystem={houseSystem} />
        <TraitChartSourceBar
          chartSource={chartSource}
          setChartSource={setChartSource}
          snapOptions={snapOptions}
          selectedSnapId={selectedSnapId}
          setSelectedSnapId={setSelectedSnapId}
          selectedSnap={selectedSnap}
          loadingSnaps={loadingSnaps}
          onRefreshSnaps={onRefreshSnaps}
        />
        <TraitTabs activeTab={activeTab} setActiveTab={setActiveTab} />
        {activeTab !== 'points' && (
          <TraitFilterBar
            band={band}
            setBand={setBand}
            polarity={polarity}
            setPolarity={setPolarity}
            sortBy={sortBy}
            setSortBy={setSortBy}
            topCount={topCount}
            setTopCount={setTopCount}
            domainRef={domainRef}
            domainOpen={domainOpen}
            setDomainOpen={setDomainOpen}
            domainSearch={domainSearch}
            setDomainSearch={setDomainSearch}
            allDomains={allDomains}
            selectedDomains={selectedDomains}
            setSelectedDomains={setSelectedDomains}
            filteredDomainList={filteredDomainList}
            toggleDomain={toggleDomain}
            hasPartialDomains={hasPartialDomains}
            resetTraitFilters={resetTraitFilters}
            hasActiveTraitFilters={hasActiveTraitFilters}
          />
        )}
        <div className="flex-1 overflow-x-hidden overflow-y-auto bg-white">
          {loading && (<div className="p-7 text-sm text-zinc-500">Analyzing...</div>)}
          {error && (<div className="p-7 text-sm text-red-600">{error}</div>)}
          {!loading && !error && data && (
            <div className="min-h-full">
              {activeTab === 'overview' && (
                <TraitOverviewTab
                  view={traitView}
                  specialDegrees={data.special_degrees}
                  topByPolarity={topByPolarity}
                  totalTraits={allTraits.length}
                  filteredTraits={filteredTraits.length}
                  band={band}
                  polarity={polarity}
                  selectedDomains={selectedDomains}
                  allDomains={allDomains}
                  onReset={resetTraitFilters}
                  onOpenTrait={setSelectedTrait}
                />
              )}
              {activeTab === 'domains' && (
                <TraitDomainsTab
                  view={traitView}
                  domainSearch={domainSearch}
                  setDomainSearch={setDomainSearch}
                  activeDomain={activeDomain}
                  setActiveDomain={setActiveDomain}
                  onOpenTrait={setSelectedTrait}
                />
              )}
              {activeTab === 'maps' && (
                <div className="p-7">
                  <TopicMapsSection houseInfluences={data.house_influences} fixedStarHits={fixedStarHits} />
                </div>
              )}
              {activeTab === 'houses' && (
                <div className="p-7">
                  <HouseInfluenceSection houseInfluences={data.house_influences} />
                </div>
              )}
              {activeTab === 'points' && (
                <TraitProfilePointsTab chartContext={traitApiContext} />
              )}
              {activeTab === 'all' && (
                <TraitAllTraitsTab
                  traits={filteredTraits}
                  totalTraits={allTraits.length}
                  band={band}
                  polarity={polarity}
                  selectedDomains={selectedDomains}
                  allDomains={allDomains}
                  onReset={resetTraitFilters}
                  onOpenTrait={setSelectedTrait}
                />
              )}
            </div>
          )}
        </div>
        {selectedTrait && (
          <TraitDetailDrawer trait={selectedTrait} onClose={() => setSelectedTrait(null)} onCopy={copyAiPrompt} />
        )}
      </div>
    </div>
  );

}

// Fixed star hits are passed via props; no global bridge.

function Micro({ children, className = '' }) {
  return (
    <span className={`font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-500 ${className}`}>
      {children}
    </span>
  );
}

function ToneDot({ polarity }) {
  const key = normalizePolarity(polarity);
  const cls = key === 'positive' ? 'bg-emerald-600' : key === 'negative' ? 'bg-rose-600' : 'bg-zinc-500';
  return <span className={`inline-block h-1.5 w-1.5 rounded-full ${cls}`} />;
}

function Pill({ children, active = false, tone = 'default', className = '', onClick, disabled = false }) {
  const toneCls = (() => {
    if (active) return 'border-zinc-950 bg-zinc-950 text-white';
    if (tone === 'positive') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
    if (tone === 'negative') return 'border-rose-200 bg-rose-50 text-rose-800';
    if (tone === 'neutral') return 'border-zinc-200 bg-zinc-100 text-zinc-700';
    if (tone === 'blue') return 'border-blue-200 bg-blue-50 text-blue-800';
    return 'border-zinc-200 bg-white text-zinc-700';
  })();
  const Tag = onClick ? 'button' : 'span';
  const actionProps = onClick ? { type: 'button', onClick, disabled } : {};
  return (
    <Tag
      {...actionProps}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] leading-none ${toneCls} ${onClick ? 'cursor-pointer hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50' : ''} ${className}`}
    >
      {children}
    </Tag>
  );
}

function SelectControl({ label, ariaLabel, value, onChange, options }) {
  return (
    <label className="inline-flex items-center gap-2">
      <Micro>{label}</Micro>
      <select
        aria-label={ariaLabel || label}
        value={value}
        onChange={onChange}
        className="h-8 rounded-full border border-zinc-200 bg-white px-3 pr-7 text-[12px] text-zinc-900 outline-none focus:border-zinc-400"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </label>
  );
}

function TraitProfileHeader({ copied, copying, disabled, modeLabel, onClose, onCopy }) {
  return (
    <div className="flex shrink-0 flex-col gap-4 bg-white px-7 py-5 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex min-w-0 max-w-full items-start gap-3.5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700">
          <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
            <circle cx="4" cy="9" r="2" fill="currentColor" />
            <circle cx="14" cy="5" r="2" fill="currentColor" opacity="0.55" />
            <circle cx="14" cy="13" r="2" fill="currentColor" opacity="0.55" />
            <path d="M5.5 8 13 5.5M5.5 10 13 12.5" stroke="currentColor" strokeWidth="0.9" fill="none" opacity="0.75" />
          </svg>
        </div>
        <div className="min-w-0">
          <Micro className="block text-emerald-700">Astro Clock / Trait Profile</Micro>
          <h2 id="trait-profile-title" className="mt-1 font-serif text-[18px] leading-snug text-zinc-950">
            Single-chart trait profile <span className="italic text-zinc-500">and domain map</span>
          </h2>
        </div>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2">
        <Micro>chart / {modeLabel || 'live'}</Micro>
        <button
          type="button"
          className="font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-700 hover:text-zinc-950 disabled:opacity-50"
          onClick={onCopy}
          disabled={disabled}
        >
          {copying ? 'Preparing...' : 'Copy AI Prompt'}
        </button>
        {copied ? <span className="text-[12px] text-emerald-700">Copied</span> : null}
        <button
          type="button"
          className="font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-950 hover:text-zinc-600"
          onClick={onClose}
        >
          Close
        </button>
      </div>
    </div>
  );
}

function TraitSubjectStrip({ view, houseSystem }) {
  const chart = view?.chart || {};
  const timestamp = chart.timestamp ? String(chart.timestamp).replace('T', ' ').replace(/Z$/, '') : 'Current chart';
  const location = chart.location || 'Current location';
  const tz = chart.timezoneLabel || 'local timezone';
  const system = chart.houseSystem || houseSystem || '-';
  return (
    <div className="flex shrink-0 flex-col gap-4 border-y border-zinc-200 bg-zinc-50 px-7 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 max-w-full flex-wrap items-center gap-x-3 gap-y-1">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-600" />
        <span className="text-[13px] font-medium text-zinc-950">{timestamp}</span>
        <span className="text-zinc-300">/</span>
        <Micro className="truncate">{location} / {tz}</Micro>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Micro>scope</Micro>
        <Pill active className="font-mono uppercase tracking-[0.08em]">Traditional</Pill>
        <span className="mx-1 text-zinc-300">/</span>
        <Micro>houses</Micro>
        <Pill className="font-mono uppercase tracking-[0.08em]">{system}</Pill>
      </div>
    </div>
  );
}

function TraitChartSourceBar({
  chartSource,
  setChartSource,
  snapOptions,
  selectedSnapId,
  setSelectedSnapId,
  selectedSnap,
  loadingSnaps,
  onRefreshSnaps,
}) {
  const parts = getSnapMetaParts(selectedSnap);
  const eligibleOptions = (Array.isArray(snapOptions) ? snapOptions : []).filter(
    (snap) => isSavedSnapCalculationEligible(snap),
  );
  const hasSnaps = eligibleOptions.length > 0;
  const hasReviewRequiredSnaps = (Array.isArray(snapOptions) ? snapOptions : []).some(
    (snap) => !isSavedSnapCalculationEligible(snap),
  );
  const switchToSnap = () => {
    setChartSource('snap');
    if (!selectedSnapId && hasSnaps) setSelectedSnapId(String(eligibleOptions[0].id || ''));
  };
  return (
    <div className="shrink-0 border-b border-zinc-200 bg-white px-7 py-3">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <Micro>chart source</Micro>
          <button
            type="button"
            className={`rounded-full border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] ${
              chartSource === 'current'
                ? 'border-zinc-950 bg-zinc-950 text-white'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 hover:text-zinc-950'
            }`}
            onClick={() => setChartSource('current')}
          >
            Current
          </button>
          <button
            type="button"
            className={`rounded-full border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] ${
              chartSource === 'snap'
                ? 'border-zinc-950 bg-zinc-950 text-white'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 hover:text-zinc-950'
            }`}
            onClick={switchToSnap}
            disabled={!hasSnaps}
          >
            Saved Snap
          </button>
        </div>
        <div className="flex min-w-0 flex-1 flex-wrap items-center justify-start gap-3 lg:justify-end">
          <select
            aria-label="Saved snap"
            value={selectedSnapId}
            onChange={(event) => {
              setSelectedSnapId(event.target.value);
              setChartSource('snap');
            }}
            disabled={loadingSnaps || !hasSnaps}
            className="h-8 min-w-[260px] max-w-full rounded-sm border border-zinc-200 bg-white px-3 text-[12px] text-zinc-700 outline-none focus:border-zinc-500 disabled:opacity-55"
          >
            <option value="">{loadingSnaps ? 'Loading saved snaps...' : 'Select a saved snap'}</option>
            {snapOptions.map((snap) => (
              <option
                key={snap.id}
                value={snap.id}
                disabled={!isSavedSnapCalculationEligible(snap)}
              >
                {formatSnapLabel(snap)}
                {getSavedSnapIneligibilityLabel(snap)
                  ? ` — ${getSavedSnapIneligibilityLabel(snap)}`
                  : ''}
              </option>
            ))}
          </select>
          {typeof onRefreshSnaps === 'function' ? (
            <button
              type="button"
              className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-zinc-600 hover:border-zinc-400 hover:text-zinc-950 disabled:opacity-55"
              onClick={() => onRefreshSnaps({ silent: true })}
              disabled={loadingSnaps}
            >
              {loadingSnaps ? 'Loading' : 'Refresh'}
            </button>
          ) : null}
          {hasReviewRequiredSnaps ? (
            <span className="font-serif text-[11px] italic leading-5 text-zinc-500">
              Review-required and superseded saved charts are disabled. Use a corrected copy from Astro Clock.
            </span>
          ) : null}
          {chartSource === 'snap' && selectedSnap ? (
            <div className="min-w-0 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-zinc-500">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
              <span className="max-w-[240px] truncate font-medium text-zinc-800">{parts.label}</span>
              {parts.datePart ? <span className="text-zinc-300">/</span> : null}
              {parts.datePart ? <span>{parts.datePart}</span> : null}
              {parts.timePart ? <span className="text-zinc-300">/</span> : null}
              {parts.timePart ? <span>{parts.timePart}</span> : null}
              {parts.location ? <span className="text-zinc-300">/</span> : null}
              {parts.location ? <span className="max-w-[220px] truncate">{parts.location}</span> : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function TraitTabs({ activeTab, setActiveTab }) {
  const tabs = [
    ['overview', 'Overview'],
    ['domains', 'Domains'],
    ['maps', 'Topic Maps'],
    ['houses', 'House Influence'],
    ['points', 'Points'],
    ['all', 'All Traits'],
  ];
  return (
    <div className="flex shrink-0 flex-wrap gap-2 bg-white px-7 pt-4">
      {tabs.map(([id, label]) => (
        <button
          key={id}
          type="button"
          onClick={() => setActiveTab(id)}
          className={`rounded-full border px-3.5 py-2 font-mono text-[11px] uppercase tracking-[0.1em] leading-none ${
            activeTab === id
              ? 'border-zinc-950 bg-zinc-950 text-white'
              : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 hover:text-zinc-950'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function TraitFilterBar({
  band,
  setBand,
  polarity,
  setPolarity,
  sortBy,
  setSortBy,
  topCount,
  setTopCount,
  domainRef,
  domainOpen,
  setDomainOpen,
  domainSearch,
  setDomainSearch,
  allDomains,
  selectedDomains,
  setSelectedDomains,
  filteredDomainList,
  toggleDomain,
  hasPartialDomains,
  resetTraitFilters,
  hasActiveTraitFilters,
}) {
  const selectedCount = selectedDomains.length || allDomains.length || 0;
  return (
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-zinc-200 bg-zinc-50/90 px-7 py-3">
      <div className="flex flex-wrap items-center gap-4">
        <SelectControl
          label="Strength"
          ariaLabel="Band"
          value={band}
          onChange={(event) => setBand(event.target.value)}
          options={[
            { value: 'all', label: 'All' },
            { value: 'strong', label: 'Strong' },
            { value: 'likely', label: 'Likely' },
            { value: 'possible', label: 'Possible' },
            { value: 'weak', label: 'Weak' },
          ]}
        />
        <SelectControl
          label="Polarity"
          value={polarity}
          onChange={(event) => setPolarity(event.target.value)}
          options={[
            { value: 'all', label: 'All' },
            { value: 'positive', label: 'Constructive' },
            { value: 'neutral', label: 'Style' },
            { value: 'negative', label: 'Strain' },
          ]}
        />
        <SelectControl
          label="Sort"
          value={sortBy}
          onChange={(event) => setSortBy(event.target.value)}
          options={[
            { value: 'score', label: 'Score' },
            { value: 'name', label: 'Name' },
            { value: 'polarity', label: 'Polarity' },
            { value: 'supports', label: 'Supports' },
          ]}
        />
        <SelectControl
          label="Top"
          ariaLabel="Top count"
          value={String(topCount)}
          onChange={(event) => setTopCount(Number(event.target.value) || 6)}
          options={[3, 5, 6, 8, 10].map((n) => ({ value: String(n), label: String(n) }))}
        />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative" ref={domainRef}>
          <button
            type="button"
            onClick={() => setDomainOpen((value) => !value)}
            className={`rounded-full border px-3 py-2 text-[12px] leading-none hover:bg-white ${
              hasPartialDomains ? 'border-amber-300 bg-amber-50 text-amber-900' : 'border-zinc-200 bg-white text-zinc-700'
            }`}
          >
            Domains ({selectedCount}/{allDomains.length || 0})
          </button>
          {domainOpen && (
            <div className="absolute right-0 z-50 mt-2 w-72 rounded-lg border border-zinc-200 bg-white p-2 shadow-xl">
              <input
                value={domainSearch}
                onChange={(event) => setDomainSearch(event.target.value)}
                placeholder="Search domains"
                className="mb-2 w-full rounded border border-zinc-300 px-2 py-1 text-[12px] outline-none focus:border-zinc-500"
              />
              <div className="mb-2 flex items-center justify-between">
                <label className="flex items-center gap-2 text-[12px]">
                  <input
                    type="checkbox"
                    checked={selectedDomains.length === allDomains.length && allDomains.length > 0}
                    onChange={(event) => event.target.checked ? setSelectedDomains(allDomains) : setSelectedDomains([])}
                  />
                  <span>Select all</span>
                </label>
                <button type="button" className="rounded border px-2 py-0.5 text-[12px] hover:bg-zinc-50" onClick={() => setSelectedDomains([])}>
                  Clear
                </button>
              </div>
              <div className="max-h-56 overflow-auto pr-1">
                {filteredDomainList.map((dom) => (
                  <label key={dom} className="flex items-center gap-2 py-1 text-[12px]">
                    <input type="checkbox" checked={selectedDomains.includes(dom)} onChange={() => toggleDomain(dom)} />
                    <span>{dom}</span>
                  </label>
                ))}
                {filteredDomainList.length === 0 && <div className="py-2 text-[12px] text-zinc-500">No matches</div>}
              </div>
            </div>
          )}
        </div>
        {hasActiveTraitFilters ? (
          <button
            type="button"
            className="rounded-full border border-amber-300 bg-amber-50 px-3 py-2 text-[12px] leading-none text-amber-900 hover:bg-amber-100"
            onClick={resetTraitFilters}
          >
            Reset filters
          </button>
        ) : null}
      </div>
    </div>
  );
}

function ScoreRail({ value, polarity = 'positive', showThumb = true }) {
  const pct = value == null ? 0 : normalizeScore(value);
  const borderCls = normalizePolarity(polarity) === 'negative'
    ? 'border-rose-600'
    : normalizePolarity(polarity) === 'neutral'
      ? 'border-zinc-500'
      : 'border-emerald-600';
  return (
    <div className="relative h-1.5 w-full rounded-full bg-gradient-to-r from-rose-100 via-zinc-100 to-emerald-100">
      {showThumb && value != null ? (
        <span
          className={`absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border bg-white shadow-sm ${borderCls}`}
          style={{ left: `${pct}%` }}
        />
      ) : null}
    </div>
  );
}

function StrengthRail({ value, polarity = 'positive' }) {
  const pct = value == null ? 0 : normalizeScore(value);
  const bg = normalizePolarity(polarity) === 'negative'
    ? 'bg-rose-600'
    : normalizePolarity(polarity) === 'neutral'
      ? 'bg-zinc-600'
      : 'bg-emerald-600';
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-zinc-200">
      <div className={`h-full ${bg}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function TraitOverviewTab({
  view,
  specialDegrees,
  topByPolarity,
  totalTraits,
  filteredTraits,
  band,
  polarity,
  selectedDomains,
  allDomains,
  onReset,
  onOpenTrait,
}) {
  const signals = view.signals;
  const balance = signals.profileBalanceIndex;
  return (
    <div className="p-7">
      <div className="grid gap-8 pb-7 lg:grid-cols-[0.95fr_2fr]">
        <div>
          <Micro className="block">Profile balance</Micro>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-serif text-[56px] leading-none text-emerald-700">{balance == null ? '-' : balance}</span>
            <span className="font-mono text-[12px] text-zinc-500">/100</span>
          </div>
          <div className="mt-3">
            <ScoreRail value={balance} polarity="positive" />
            <div className="mt-1 flex justify-between">
              <Micro>strain</Micro>
              <Micro>constructive</Micro>
            </div>
          </div>
          <div className="mt-4 text-[13px] leading-6 text-zinc-500">
            Derived from constructive and strain trait signals.
          </div>
        </div>
        <div>
          <Micro className="block">Trait signature</Micro>
          <h3 className="mt-2 max-w-3xl font-serif text-[34px] leading-tight text-zinc-950">
            {view.signature.line}
          </h3>
          <p className="mt-3 max-w-3xl font-serif text-[15px] italic leading-7 text-zinc-500">
            {view.signature.note}
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {view.chart.dominantElement ? <Pill tone="positive"><ToneDot polarity="positive" /> Element: {view.chart.dominantElement}</Pill> : null}
            {view.chart.dominantModality ? <Pill tone="neutral">Modality: {view.chart.dominantModality}</Pill> : null}
            {view.chart.sect ? <Pill tone="neutral">Sect: {view.chart.sect}</Pill> : null}
            {view.chart.chartRuler ? <Pill>Chart ruler: {view.chart.chartRuler}</Pill> : null}
          </div>
        </div>
      </div>
      <div className="border-t border-zinc-200 pt-6">
        <TraitFilterNotice
          totalTraits={totalTraits}
          filteredTraits={filteredTraits}
          band={band}
          polarity={polarity}
          selectedDomains={selectedDomains}
          allDomains={allDomains}
          onReset={onReset}
        />
        <div className="grid gap-8 lg:grid-cols-3">
          <div>
            <SignalPanel signal={signals.constructive} />
            <TraitColumn title={POLARITY_META.positive.splitLabel} label={POLARITY_META.positive.columnLabel} polarity="positive" traits={topByPolarity.pos} onOpenTrait={onOpenTrait} />
          </div>
          <div>
            <SignalPanel signal={signals.style} />
            <TraitColumn title={POLARITY_META.neutral.splitLabel} label={POLARITY_META.neutral.columnLabel} polarity="neutral" traits={topByPolarity.neutral} onOpenTrait={onOpenTrait} />
          </div>
          <div>
            <SignalPanel signal={signals.strain} />
            <TraitColumn title={POLARITY_META.negative.splitLabel} label={POLARITY_META.negative.columnLabel} polarity="negative" traits={topByPolarity.neg} onOpenTrait={onOpenTrait} />
          </div>
        </div>
      </div>
    </div>
  );
}

function SignalPanel({ signal }) {
  const polarity = signal?.polarity || 'neutral';
  const tone = normalizePolarity(polarity);
  const value = signal?.value;
  const valueColor = tone === 'positive' ? 'text-emerald-700' : tone === 'negative' ? 'text-rose-700' : 'text-zinc-900';
  return (
    <div className="border-t border-zinc-100 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ToneDot polarity={polarity} />
          <Micro>{signal?.label || 'Signal'}</Micro>
        </div>
        <Micro>{signal?.count || 0} traits</Micro>
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className={`font-serif text-[30px] leading-none ${valueColor}`}>{value == null ? '-' : value}</span>
        <span className="font-mono text-[11px] text-zinc-500">/100</span>
      </div>
      <div className="mt-2"><StrengthRail value={value} polarity={polarity} /></div>
    </div>
  );
}

function TraitColumn({ title, label, polarity, traits, onOpenTrait }) {
  const list = Array.isArray(traits) ? traits : [];
  return (
    <div className="border border-transparent">
      <div className="mb-2">
        <div className="flex items-center gap-2">
          <ToneDot polarity={polarity} />
          <Micro>{title}</Micro>
        </div>
        <div className="mt-1 text-[12px] text-zinc-500">{label}</div>
      </div>
      <div className="border-t border-zinc-200">
        {list.length ? list.map((trait) => (
          <TraitListRow key={trait.id || trait.name} trait={trait} onOpenTrait={onOpenTrait} />
        )) : (
          <div className="py-5 text-[13px] text-zinc-500">No results</div>
        )}
      </div>
    </div>
  );
}

function TraitListRow({ trait, onOpenTrait }) {
  const pol = normalizePolarity(trait?.polarity) || 'neutral';
  const score = normalizeScore(trait?.score);
  const supportHits = Number(trait?.support_hits || 0);
  const supportTotal = Number(trait?.support_total || 0);
  const rawScore = Number(trait?.raw_score || 0);
  const maxScore = Number(trait?.max_score || 0);
  const related = Number(trait?.family_size || 0) > 1 ? `${Number(trait.family_size) - 1} related variants` : null;
  return (
    <button
      type="button"
      className="block w-full border-b border-zinc-100 py-3 text-left outline-none hover:bg-zinc-50 focus:bg-zinc-50"
      onClick={() => onOpenTrait?.(trait)}
    >
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <ToneDot polarity={pol} />
          <span className="truncate text-sm font-medium text-zinc-900">{trait?.name || trait?.id}</span>
        </div>
        <span className={`${pol === 'positive' ? 'text-emerald-700' : pol === 'negative' ? 'text-rose-700' : 'text-zinc-700'} font-mono text-[12px]`}>
          {Math.round(score)}%
        </span>
      </div>
      <div className="mt-2"><ScoreRail value={score} polarity={pol} /></div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {trait?.band ? <Pill tone={pol}>{String(trait.band).replace(/_/g, ' ')}</Pill> : null}
        <Micro>{supportHits}/{supportTotal} supports / raw {rawScore.toFixed(1)}/{maxScore.toFixed(1)}</Micro>
        {related ? <Micro>{related}</Micro> : null}
        {trait?.domain ? <DomainChip domain={trait.domain} /> : null}
      </div>
    </button>
  );
}

function TraitRowProvenance({ trait }) {
  return null;
}

function TraitDomainsTab({ view, domainSearch, setDomainSearch, activeDomain, setActiveDomain, onOpenTrait }) {
  const domains = view.domains;
  const active = activeDomain || domains.visibleDomains[0] || domains.allDomains[0] || null;
  const traits = active ? view.allTraits.filter((trait) => String(trait?.domain || '') === active) : [];
  const groups = {
    positive: traits.filter((trait) => normalizePolarity(trait?.polarity) === 'positive').sort((a, b) => normalizeScore(b.score) - normalizeScore(a.score)),
    neutral: traits.filter((trait) => normalizePolarity(trait?.polarity) === 'neutral').sort((a, b) => normalizeScore(b.score) - normalizeScore(a.score)),
    negative: traits.filter((trait) => normalizePolarity(trait?.polarity) === 'negative').sort((a, b) => normalizeScore(b.score) - normalizeScore(a.score)),
  };
  return (
    <div className="grid gap-8 p-7 lg:grid-cols-[320px_1fr]">
      <div>
        <Micro className="block">Domain index</Micro>
        <input
          value={domainSearch}
          onChange={(event) => setDomainSearch(event.target.value)}
          placeholder="Search domains"
          className="mt-2 w-full rounded-lg border border-zinc-200 px-3 py-2 text-[13px] outline-none focus:border-zinc-500"
        />
        <Micro className="mt-3 block">{domains.visibleDomains.length} domains / {domains.traitCount} traits</Micro>
        <div className="mt-3 flex flex-col gap-1">
          {domains.visibleDomains.map((domain) => (
            <button
              type="button"
              key={domain}
              onClick={() => setActiveDomain(domain)}
              className={`flex items-center justify-between border-l-2 px-3 py-2 text-left text-[13px] ${
                active === domain ? 'border-zinc-950 bg-zinc-50 text-zinc-950' : 'border-transparent text-zinc-600 hover:bg-zinc-50'
              }`}
            >
              <span>{domain}</span>
              <span className="font-mono text-[11px] text-zinc-500">{domains.counts[domain] || 0}</span>
            </button>
          ))}
          {!domains.visibleDomains.length ? <div className="py-5 text-[13px] text-zinc-500">No matching domains.</div> : null}
        </div>
      </div>
      <div>
        <div className="flex items-end justify-between gap-4 border-b border-zinc-200 pb-4">
          <div>
            <Micro className="block">Domain / {active || 'none'}</Micro>
            <h3 className="mt-1 font-serif text-[26px] text-zinc-950">{active || 'No domain selected'}</h3>
            <div className="mt-1 text-[13px] text-zinc-500">{traits.length} traits in this domain.</div>
          </div>
        </div>
        {(['positive', 'neutral', 'negative']).map((pol) => {
          const items = groups[pol] || [];
          if (!items.length) return null;
          return (
            <div key={pol} className="mt-5">
              <div className="mb-1 flex items-center gap-2">
                <ToneDot polarity={pol} />
                <Micro>{POLARITY_META[pol].label} / {items.length}</Micro>
              </div>
              <div className="border-t border-zinc-200">
                {items.map((trait) => <TraitListRow key={trait.id || trait.name} trait={trait} onOpenTrait={onOpenTrait} />)}
              </div>
            </div>
          );
        })}
        {active && !traits.length ? <div className="py-8 text-[13px] text-zinc-500">No traits in this domain.</div> : null}
      </div>
    </div>
  );
}

function TraitAllTraitsTab({ traits, totalTraits, band, polarity, selectedDomains, allDomains, onReset, onOpenTrait }) {
  const list = Array.isArray(traits) ? traits : [];
  const groups = new Map();
  for (const trait of list) {
    const key = trait?.domain || 'general';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(trait);
  }
  const entries = Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
  return (
    <div className="p-7">
      <div className="mb-5 flex items-end justify-between gap-4 border-b border-zinc-200 pb-4">
        <div>
          <Micro className="block">All traits / {list.length}</Micro>
          <h3 className="mt-1 font-serif text-[26px] text-zinc-950">Grouped by domain</h3>
        </div>
      </div>
      <TraitFilterNotice
        totalTraits={totalTraits}
        filteredTraits={list.length}
        band={band}
        polarity={polarity}
        selectedDomains={selectedDomains}
        allDomains={allDomains}
        onReset={onReset}
      />
      <div className="mt-4 space-y-6">
        {entries.map(([domain, items]) => (
          <div key={domain}>
            <div className="mb-1 flex items-center gap-2">
              <DomainChip domain={domain} />
              <Micro>{items.length} items</Micro>
            </div>
            <div className="border-t border-zinc-200">
              {items.map((trait) => <TraitListRow key={trait.id || trait.name} trait={trait} onOpenTrait={onOpenTrait} />)}
            </div>
          </div>
        ))}
        {!entries.length ? <div className="py-8 text-[13px] text-zinc-500">No traits match the current filters.</div> : null}
      </div>
    </div>
  );
}

function TraitDetailDrawer({ trait, onClose, onCopy }) {
  const pol = normalizePolarity(trait?.polarity) || 'neutral';
  const evidence = Array.isArray(trait?.evidence) ? trait.evidence : [];
  const keywords = Array.isArray(trait?.keywords) ? trait.keywords : [];
  const score = normalizeScore(trait?.score);
  return (
    <>
      <div className="absolute inset-0 z-10 bg-zinc-950/15" onClick={onClose} />
      <aside className="absolute right-0 top-0 z-20 flex h-full w-full max-w-[460px] flex-col border-l border-zinc-200 bg-white shadow-[-12px_0_40px_rgba(20,20,18,0.10)]">
        <div className="border-b border-zinc-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <Micro><ToneDot polarity={pol} /> {POLARITY_META[pol]?.label || 'Trait'} / {String(trait?.band || '').replace(/_/g, ' ')}</Micro>
            <button type="button" className="font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-950" onClick={onClose}>Close</button>
          </div>
          <h3 className="mt-3 font-serif text-[26px] leading-tight text-zinc-950">{trait?.name || trait?.id}</h3>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">
          <div className="grid grid-cols-3 gap-4">
            <MetricBlock label="Score" value={`${Math.round(score)}%`} polarity={pol} />
            <MetricBlock label="Supports" value={`${Number(trait?.support_hits || 0)}/${Number(trait?.support_total || 0)}`} />
            <MetricBlock label="Raw" value={`${Number(trait?.raw_score || 0).toFixed(1)}/${Number(trait?.max_score || 0).toFixed(1)}`} />
          </div>
          <div className="mt-4"><ScoreRail value={score} polarity={pol} /></div>
          {trait?.description ? (
            <p className="mt-5 font-serif text-[16px] leading-7 text-zinc-700">{trait.description}</p>
          ) : null}
          <div className="mt-5">
            <Micro className="block">Evidence</Micro>
            {evidence.length ? (
              <ul className="mt-2 space-y-1.5 text-[13px] leading-5 text-zinc-700">
                {evidence.slice(0, 10).map((line, index) => <li key={index}>+ {line}</li>)}
              </ul>
            ) : (
              <div className="mt-2 text-[13px] text-zinc-500">No detailed evidence rows were returned.</div>
            )}
          </div>
          {keywords.length ? (
            <div className="mt-5">
              <Micro className="block">Domains and keywords</Micro>
              <div className="mt-2 flex flex-wrap gap-2">
                {trait?.domain ? <DomainChip domain={trait.domain} /> : null}
                {keywords.slice(0, 8).map((kw) => <Pill key={kw}>{kw}</Pill>)}
              </div>
            </div>
          ) : null}
          <div className="mt-6">
            <button
              type="button"
              className="rounded-full bg-zinc-950 px-4 py-2 font-mono text-[11px] uppercase tracking-[0.1em] text-white"
              onClick={onCopy}
            >
              Copy AI Prompt
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

function MetricBlock({ label, value, polarity }) {
  const pol = normalizePolarity(polarity);
  const color = pol === 'positive' ? 'text-emerald-700' : pol === 'negative' ? 'text-rose-700' : 'text-zinc-950';
  return (
    <div>
      <Micro className="block">{label}</Micro>
      <div className={`mt-1 font-serif text-[28px] leading-none ${color}`}>{value}</div>
    </div>
  );
}

function TopicMapsSection({ houseInfluences, fixedStarHits }){
  const houses = Array.isArray(houseInfluences?.houses) ? houseInfluences.houses : [];
  if (!houses.length) return null;
  const byNum = (n) => houses.find(h => Number(h?.house) === Number(n)) || null;
  const h10 = byNum(10);
  const h1 = byNum(1);
  const h6 = byNum(6);
  const h12 = byNum(12);
  if (!h10 && !h1 && !h6) return null;
  return (
    <div>
      <div className="mb-5 flex flex-col gap-2 border-b border-zinc-200 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Micro className="block">Morin / Topic maps</Micro>
          <h3 className="mt-1 font-serif text-[26px] leading-tight text-zinc-950">Where the chart pulls in life</h3>
          <p className="mt-1 max-w-2xl font-serif text-[13px] italic leading-5 text-zinc-500">
            Profession and health structures from the current house influence data.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[12px] text-zinc-500">
          {h10 ? <Pill>H10 {h10.sign || '-'}</Pill> : null}
          {h1 ? <Pill>H1 {h1.sign || '-'}</Pill> : null}
          {h6 ? <Pill>H6 {h6.sign || '-'}</Pill> : null}
          {h12 ? <Pill>H12 {h12.sign || '-'}</Pill> : null}
        </div>
      </div>
      <div className="grid grid-cols-1 gap-x-9 gap-y-8 xl:grid-cols-2">
        {h10 ? (<ProfessionMapCard h={h10} houses={houses} fixedStarHits={fixedStarHits} />) : null}
        {(h1 || h6 || h12) ? (<HealthMapCard h1={h1} h6={h6} h12={h12} houses={houses} fixedStarHits={fixedStarHits} />) : null}
      </div>
    </div>
  );
}

function Keywords({ items }){
  const list = (Array.isArray(items) ? items : []).filter(Boolean);
  if (!list.length) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {list.slice(0, 10).map((k, i) => (
        <span key={`${k}-${i}`} className="text-[10px] px-1 py-0.5 rounded-full border border-zinc-200 bg-zinc-50 text-zinc-700">{k}</span>
      ))}
    </div>
  );
}

function MiniDeterminators({ ba, exclude = {} }){
  const det = ba?.determinators_panel || {};
  const rankOrder = { dominant: 3, secondary: 2, tertiary: 1 };
  const sortDet = (arr) => {
    const list = Array.isArray(arr) ? arr.slice() : [];
    return list.sort((a,b)=> (rankOrder[String(b?.rank||'')]||0) - (rankOrder[String(a?.rank||'')]||0) || (Number(b?.value||0) - Number(a?.value||0)));
  };
  const sec = (label, arr, render) => {
    let list = sortDet(arr);
    // Exclude duplicates shown in the Lead/Route/Pressure bar
    try {
      if (label === 'Presence' && exclude.leadPlanet && list.length && list[0]?.planet === exclude.leadPlanet) {
        list = list.slice(1);
      }
      if (label === 'Governance' && exclude.govPlanet && list.length && list[0]?.planet === exclude.govPlanet) {
        list = list.slice(1);
      }
      if (label === 'Aspect' && list.length) {
        const idx = list.findIndex(x => (
          (exclude.aspectPlanet ? x?.planet === exclude.aspectPlanet : false) &&
          (exclude.aspectName ? x?.aspect === exclude.aspectName : true) &&
          (exclude.aspectPhase ? x?.phase === exclude.aspectPhase : true)
        ));
        if (idx === 0) list = list.slice(1);
        else if (idx > 0) list = list.filter((_,i)=> i !== idx);
      }
    } catch(_) {}
    list = list.slice(0, 2);
    if (!list.length) return null;
    return (
      <div>
        <div className="text-[10px] text-zinc-500 mb-0.5">{label}</div>
        <div className="flex flex-wrap gap-1">
          {list.map((x, i) => (
            <span key={i} className="text-[11px] px-1.5 py-0.5 rounded border border-zinc-200 bg-white text-zinc-800" title={x?.tooltip || ''}>
              {render(x)}
            </span>
          ))}
        </div>
      </div>
    );
  };
  return (
    <div className="grid grid-cols-3 gap-2">
      {sec('Presence', det.presence, (x)=> `${x.planet}${x.adverb ? ' ' + x.adverb : ''}`)}
      {sec('Governance', det.governance, (x)=> `${x.planet}${x.type==='co_rulership' ? ' (co)' : ''}${x.adverb ? ' ' + x.adverb : ''}`)}
      {sec('Aspect', det.aspect, (x)=> `${x.planet} ${x.aspect}${x.phase ? ' ' + x.phase : ''}`)}
    </div>
  );
}

function MapStatementRows({ rows }) {
  const list = (Array.isArray(rows) ? rows : []).filter((row) => row && (row.primary || row.sub));
  if (!list.length) return null;
  return (
    <div className="my-3 border-b border-zinc-100">
      {list.map((row) => (
        <div key={row.label} className="grid grid-cols-[7rem_1fr] gap-4 border-t border-zinc-100 py-3">
          <Micro>{row.label}</Micro>
          <div>
            <div className="text-[13px] leading-5 text-zinc-950">{row.primary || '-'}</div>
            {row.sub ? (
              <div className="mt-0.5 font-serif text-[12px] italic leading-5 text-zinc-500">{row.sub}</div>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function ProfessionMapCard({ h, houses, fixedStarHits = [] }){
  const byNum = (n) => (Array.isArray(houses)? houses: []).find(x => Number(x?.house) === Number(n)) || null;
  const h2 = byNum(2);
  const h6 = byNum(6);
  const ba = h?.basic_analysis || {};
  const keyWords = (() => {
    // Morin method keywords for Profession (10th): emphasize determination hierarchy and ruler route
    const set = new Set(['MC','profession','honors','reputation']);
    try {
      // Determinator lead (presence vs governance vs aspect) on H10
      const list = Array.isArray(h?.influences) ? h.influences : [];
      let pres=0, gov=0, asp=0;
      for (const it of list) {
        const v = Math.abs(Number(it?.value||0));
        const t = String(it?.type||'');
        if (t==='occupation') pres+=v; else if (t==='rulership' || t==='co_rulership') gov+=v; else if (t==='aspect') asp+=v;
      }
      const lead = pres >= gov && pres >= asp ? 'location' : (gov >= asp ? 'governance' : 'aspect');
      if (lead === 'location') set.add('location priority');
      if (lead === 'governance') set.add('ruler route');
      if (lead === 'aspect') set.add('aspect to cusp');
      // Ruler conditions
      const conds = Array.isArray(ba?.ruler_map?.conditions) ? ba.ruler_map.conditions.map(s=>String(s).toLowerCase()) : [];
      if (conds.some(s=> s.includes('dignified'))) set.add('dignified ruler');
      if (conds.some(s=> s.includes('debilitated'))) set.add('debilitated ruler');
      if (conds.some(s=> s.includes('angular'))) set.add('angular ruler');
      if (conds.some(s=> s.includes('cadent'))) set.add('cadent ruler');
      if (conds.some(s=> s.includes('retrograde'))) set.add('retrograde');
      if (conds.some(s=> s.includes('cazimi'))) set.add('cazimi');
      if (conds.some(s=> s.includes('combust'))) set.add('combust');
      if (conds.some(s=> s.includes('under the beams') || s.includes('under beams'))) set.add('under beams');
      // Top aspect cues
      const a = Array.isArray(ba?.aspect_top) && ba.aspect_top.length ? ba.aspect_top[0] : null;
      if (a) {
        if (a?.phase) set.add(String(a.phase));
        if (a?.dexter != null) set.add(a.dexter ? 'dexter' : 'sinister');
      }
    } catch (_) {}
    return Array.from(set);
  })();
  const overview = ba?.overview || {};
  const topLoc = Array.isArray(ba?.location) ? ba.location.slice(0,1) : [];
  const topAspect = Array.isArray(ba?.aspect_top) ? ba.aspect_top.slice(0,1) : [];
  const route = ba?.route_line || null;
  const routeHouse = (() => {
    try {
      const r = ba?.ruler_map?.route || route || '';
      const m = String(r).match(/H(\d{1,2})/);
      return m ? m[1] : null;
    } catch(_) { return null; }
  })();
  const rulerMap = ba?.ruler_map || {};
  const rulerConds = Array.isArray(rulerMap?.conditions) ? rulerMap.conditions : [];
  const rulerDisp = rulerMap?.dispositor || null;
  const channelText = (s) => `P ${Math.round((s?.presence || 0) * 100)}% G ${Math.round((s?.governance || 0) * 100)}% A ${Math.round((s?.aspect || 0) * 100)}% / ${Number(s?.total || 0).toFixed(1)}`;
  const s10 = buildHouseDeterminationChannels(h);
  const s2 = buildHouseDeterminationChannels(h2);
  const s6s = buildHouseDeterminationChannels(h6);
  // Precompute summary determinators to reuse (and pass to child)
  const detPanel = ba?.determinators_panel || {};
  const leadKindSum = (s10.presence >= s10.governance && s10.presence >= s10.aspect) ? 'presence' : ((s10.governance >= s10.aspect) ? 'governance' : 'aspect');
  const leadItemSum = (Array.isArray(detPanel?.[leadKindSum]) && detPanel[leadKindSum].length) ? detPanel[leadKindSum][0] : null;
  const leadPlanetSum = leadItemSum?.planet || null;
  const leadRankSum = leadItemSum?.rank || null;
  const govItemSum = (Array.isArray(detPanel?.governance) && detPanel.governance.length) ? detPanel.governance[0] : null;
  const govPlanetSum = govItemSum?.planet || null;
  let aspectSum = (Array.isArray(ba?.aspect_top) && ba.aspect_top.length) ? ba.aspect_top[0] : null;
  if (!aspectSum) {
    const alt = (Array.isArray(detPanel?.aspect) && detPanel.aspect.length) ? detPanel.aspect[0] : null;
    if (alt) aspectSum = alt;
  }
  const excludeSummary = {
    leadPlanet: leadPlanetSum,
    govPlanet: govPlanetSum,
    aspectPlanet: aspectSum?.planet,
    aspectName: aspectSum?.aspect,
    aspectPhase: aspectSum?.phase,
  };
  const morinNotes = (() => {
    const notes = [];
    // Aspect cue
    try {
      if (topAspect.length) {
        const a = topAspect[0];
        const malef = ['Saturn','Mars'].includes(String(a?.planet||''));
        const benef = ['Jupiter','Venus'].includes(String(a?.planet||''));
        if (a?.afflicting && malef) notes.push('Applying malefic affliction to MC cusp - career obstacles.');
        if (!a?.afflicting && ['Trine','Sextile'].includes(String(a?.aspect||'')) && benef) notes.push('Benefic support to MC cusp - advancement potential.');
      }
    } catch (_) {}
    return notes;
  })();
  return (
    <section className="border-t border-zinc-200 pt-4">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <div>
          <div className="font-serif text-[22px] leading-none text-zinc-950">Profession Map</div>
          <Micro className="mt-2 block">10th / {h?.sign || '-'}</Micro>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-zinc-600">10th</span>
          <div className="text-[11px] px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-zinc-700">{h?.sign || '-'}</div>
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5 text-[11px] text-zinc-700 mb-2">
        <span className="px-1.5 py-0.5 rounded border border-zinc-200 bg-white">Ruler: <span className="font-medium">{overview?.ruler || '-'}</span></span>
        <span className="px-1.5 py-0.5 rounded border border-zinc-200 bg-white">Exalt: <span className="font-medium">{overview?.exaltation || '-'}</span></span>
        <span className="px-1.5 py-0.5 rounded border border-zinc-200 bg-white">Triplicity: <span className="font-medium">{overview?.triplicity_ruler || '-'}</span></span>
      </div>
      {/* Triplicity context: Action (2/6/10) */}
      <div className="text-[11px] text-zinc-700 mb-2">
        <div className="mb-1">Action Triplicity: <span className="px-1 rounded border border-zinc-200 bg-white">H2</span> <span className="px-1 rounded border border-zinc-200 bg-white">H6</span> <span className="px-1 rounded border border-zinc-200 bg-white">H10</span></div>
        <div className="grid grid-cols-3 gap-2">
          <div className="text-zinc-500">
            <div className="text-[10px]">H2 (resources) - secondary</div>
            <div className="text-[10px]" title="Presence / governance / aspect share; trailing number is summed influence strength.">{channelText(s2)}</div>
          </div>
          <div className="text-zinc-500">
            <div className="text-[10px]">H6 (work/service) - secondary</div>
            <div className="text-[10px]" title="Presence / governance / aspect share; trailing number is summed influence strength.">{channelText(s6s)}</div>
          </div>
          <div className="text-zinc-800">
            <div className="text-[10px] font-medium">H10 (profession) - primary</div>
            <div className="text-[10px]" title="Presence / governance / aspect share; trailing number is summed influence strength.">{channelText(s10)}</div>
          </div>
        </div>
      </div>
      {(() => {
        const a = aspectSum;
        const orbTxt = (typeof a?.orb === 'number') ? `${Number(a.orb).toFixed(1)} deg` : null;
        const band = (typeof a?.orb === 'number') ? (a.orb <= 0.5 ? 'partile' : (a.orb <= 1.5 ? 'tight' : 'wide')) : null;
        const phase = a?.phase || null;
        const aspShort = a ? `${a.planet} ${String(a.aspect||'').toLowerCase()}` : null;
        const isWeakPressure = !!(a && typeof a.orb === 'number' && a.orb > 2.5 && String(phase||'').toLowerCase() === 'separating');
        const pressureLabel = isWeakPressure ? 'Context' : 'Pressure';
        const leadText = leadPlanetSum ? `${leadPlanetSum} (${leadKindSum}${leadRankSum? `, ${leadRankSum}`:''})` : '-';
        const routeText = govPlanetSum ? `${govPlanetSum}${routeHouse? ` -> H${routeHouse}`:''}` : (overview?.ruler || '-');
        const pressureText = aspShort ? `${aspShort}${orbTxt? ` (${orbTxt}${band? `, ${band}`:''}${phase? `, ${phase}`:''})` : ''}` : '-';
        return (
          <MapStatementRows rows={[
            { label: 'Lead', primary: leadText, sub: leadItemSum?.tooltip || '' },
            { label: 'Route', primary: routeText, sub: route || '' },
            { label: pressureLabel, primary: pressureText, sub: a?.phrase || '' },
          ]} />
        );
      })()}
      {/* Determinators (kept concise); exclude items already in summary */}
      <MiniDeterminators ba={ba} exclude={excludeSummary} />
      {/* Triplicity support: occupants of H2 and H6 (secondary) */}
      {(() => {
        try {
          const pickOcc = (house) => {
            const bl = house?.basic_analysis;
            const loc = Array.isArray(bl?.location) ? bl.location : [];
            if (!loc.length) return null;
            const li = loc[0] || {};
            const st = li?.state || {};
            const tags = [];
            if (st.strong && st.dignified && !st.afflicted) tags.push('well disposed');
            else if (st.afflicted) tags.push('afflicted');
            else if (st.dignified) tags.push('dignified');
            return { planet: li.planet, tags };
          };
          const occ2 = pickOcc(h2);
          const occ6 = pickOcc(h6);
          if (!occ2 && !occ6) return null;
          return (
            <div className="mt-1 text-[10px] text-zinc-700">
              <span className="mr-1">Triplicity support:</span>
              {occ2 ? (
                <span className="mr-1 px-1 rounded border border-zinc-200 bg-white">H2: {occ2.planet}{occ2.tags.length? ` [${occ2.tags.join(', ')}]`:''}</span>
              ) : null}
              {occ6 ? (
                <span className="mr-1 px-1 rounded border border-zinc-200 bg-white">H6: {occ6.planet}{occ6.tags.length? ` [${occ6.tags.join(', ')}]`:''}</span>
              ) : null}
            </div>
          );
        } catch(_) { return null; }
      })()}
      <div className="mt-2 flex flex-col gap-1">
        {topLoc.map((li, i) => {
          const st = li?.state || {};
          const locClass = st?.afflicted ? 'text-rose-700' : ((st?.strong && st?.dignified) ? 'text-emerald-700' : 'text-zinc-800');
          return (
            <div key={`loc-${i}`} className={`text-[12px] ${locClass} flex items-start gap-1.5`}>
              <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-current opacity-70"></span>
              <span className="px-1 rounded border border-zinc-200 bg-white mr-1">{li.planet}</span>
              <span>{li.summary}</span>
            </div>
          );
        })}
        {topAspect.map((a, i) => {
          const aff = !!a?.afflicting;
          const fav = ['Trine','Sextile'].includes(String(a?.aspect || ''));
          const aspClass = aff ? 'text-rose-700 pl-2' : (fav ? 'text-emerald-700 pl-2' : 'text-zinc-800');
          const simplifyAspectPhrase = (t) => {
            try {
              if (!t || typeof t !== 'string') return t;
              let s = t;
              s = s.replace(/\bin a\b[^;\.]+\bmanner\b/gi, '').replace(/\s{2,}/g, ' ').trim();
              s = s.replace(/;?\s*pressure builds toward perfection/gi, '').trim();
              s = s.replace(/;?\s*harsher out of sect/gi, '').trim();
              s = s.replace(/\bcircumstantially and\b/gi, '');
              s = s.replace(/\s{2,}/g, ' ').replace(/\s*;\s*;\s*/g, '; ').trim();
              return s;
            } catch(_) { return t; }
          };
          return (
            <div key={`asp-${i}`} className={`text-[12px] ${aspClass} flex items-start gap-1.5`}>
              <span className={`mt-1 h-2 w-2 rounded-full ${aff ? 'bg-rose-300' : (fav ? 'bg-emerald-300' : 'bg-zinc-300')}`}></span>
              <span className="px-1 rounded border border-zinc-200 bg-white mr-1">{a.planet}</span>
              <span>{simplifyAspectPhrase(a.phrase) || (`${a.planet} ${a.aspect?.toLowerCase?.() || a.aspect} to MC`)}</span>
            </div>
          );
        })}
        {/* Route line omitted to reduce duplication; summarized above */}
        {/* Natural significator support chips */}
        {(() => {
          try {
            const det = ba?.determinators_panel || {};
            const detAll = [...(det.presence||[]), ...(det.governance||[]), ...(det.aspect||[])];
            const hasSun = detAll.some(x => x?.planet === 'Sun');
            const hasJup = detAll.some(x => x?.planet === 'Jupiter');
            if (!hasSun && !hasJup) return null;
            return (
              <div className="mt-1 text-[10px] text-zinc-700">
                {hasSun && (<span className="px-1 mr-1 rounded border border-zinc-200 bg-white">Sun support</span>)}
                {hasJup && (<span className="px-1 mr-1 rounded border border-zinc-200 bg-white">Jupiter support</span>)}
              </div>
            );
          } catch (_) { return null; }
        })()}
        <div className="text-[10px] text-zinc-500 mt-1">H4 (opposition) - secondary frame; weaker determination</div>
        {(() => {
          try {
            const conds = Array.isArray(ba?.ruler_map?.conditions) ? ba.ruler_map.conditions.map(s => String(s).toLowerCase()) : [];
            const dispLine = ba?.ruler_map?.dispositor || '';
            // Normalize to avoid duplicates with keyword chips above
            const seenKW = new Set((keyWords || []).map(s => String(s).toLowerCase()));
            const map = [
              { key: 'retrograde', label: 'retrograde', tip: 'Delays, revisions, returns (ruler).' },
              { key: 'under beams', label: 'under beams', tip: "Muted/hidden expression under Sun's beams." },
              { key: 'combust', label: 'combust', tip: 'Severely impeded by proximity to Sun.' },
              { key: 'cazimi', label: 'cazimi', tip: "Strengthened at Sun's heart." },
              { key: 'angular', label: 'angular', tip: 'Prominent, direct delivery.' },
              { key: 'succedent', label: 'succedent', tip: 'Sustained, moderate delivery.' },
              { key: 'cadent', label: 'cadent', tip: 'Weaker delivery, indirect.' },
              { key: 'dignified', label: 'dignified', tip: 'Supported by essential strength.' },
              { key: 'debilitated', label: 'debilitated', tip: 'Weakened by detriment/fall.' },
            ];
            const wanted = [];
            for (const m of map) {
              if (conds.some(c => c.includes(m.key))) {
                // Skip if an equivalent keyword already displayed above
                const dup = (m.key === 'angular' && seenKW.has('angular ruler')) || seenKW.has(m.key);
                if (!dup) wanted.push(m);
              }
            }
            // Parse dispositor planet if present in parentheses
            let dispPlanet = null;
            try {
              const paren = dispLine.match(/\(([^)]+)\)/);
              if (paren) dispPlanet = paren[1];
            } catch(_) {}
            if (wanted.length === 0 && !dispLine) return null;
            return (
              <div className="text-[11px] text-zinc-700 mt-1">
                <div className="font-medium inline text-zinc-700 mr-1">Ruler status:</div>
                {wanted.map((m, i) => (
                  <span key={m.key+String(i)} title={m.tip} className="mr-1 mb-1 inline-block px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-[10px]">{m.label}</span>
                ))}
                {dispLine ? (
                  <span title="Dispositor colors the sign’s action" className="ml-1 inline-block px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-[10px]">
                    Dispositor{dispPlanet? `: ${dispPlanet}`:''}
                  </span>
                ) : null}
              </div>
            );
          } catch(_) { return null; }
        })()}
      </div>
      {(() => {
        try {
          const sugsA = buildProfessionSuggestions(h, { h2, h6, h4: byNum(4) });
          const sugsB = buildFixedStarProfessionSuggestions(Array.isArray(fixedStarHits) ? fixedStarHits : []);
          const merged = (() => {
            const acc = new Map();
            [...sugsA, ...sugsB].forEach(s => {
              const k = s.label;
              const prev = acc.get(k);
              if (!prev || Number(s.weight||0) > Number(prev.weight||0)) acc.set(k, s);
            });
            return Array.from(acc.values());
          })();
          const sugs = merged.sort((a,b)=> (Number(b.weight||0) - Number(a.weight||0)) || String(a.label).localeCompare(String(b.label)));
          if (!sugs.length) return null;
          // render as sleek chips with reasoning as tooltip
          const Chip = ({ s }) => {
            const w = Number(s?.weight || 1);
            const tier = w >= 1.1 ? 'highlight' : (w >= 0.9 ? 'normal' : 'faint');
            const cls = tier === 'highlight'
              ? 'bg-zinc-50 border-zinc-300 text-zinc-900 shadow-sm'
              : (tier === 'normal' ? 'bg-white border-zinc-200 text-zinc-800' : 'bg-white border-zinc-200 text-zinc-600 opacity-80');
            return (
              <span title={s?.reason || ''} className={`text-[11px] px-2 py-1 rounded-full border ${cls}`}>{s.label}</span>
            );
          };
          return (
            <div className="mt-2">
              <div className="text-[11px] font-medium text-zinc-700 mb-1">Potential Vocations</div>
              <div className="flex flex-wrap gap-1.5">
                {sugs.slice(0, 8).map((s, i) => (<Chip key={i} s={s} />))}
              </div>
            </div>
          );
        } catch (_) { return null; }
      })()}
      {morinNotes.length ? (
        <div className="mt-2 border-t border-zinc-100 pt-1">
          <ul className="text-[11px] text-zinc-700 list-disc pl-5">
            {morinNotes.slice(0,3).map((n,i)=> (<li key={i}>{n}</li>))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function HealthMapCard({ h1, h6, h12, houses, fixedStarHits = [] }){
  const byNum = (n) => (Array.isArray(houses)? houses: []).find(x => Number(x?.house) === Number(n)) || null;
  const ba1 = h1?.basic_analysis || {};
  const ba6 = h6?.basic_analysis || {};
  const ba12 = h12?.basic_analysis || {};
  const [morinStrict, setMorinStrict] = useState(false);
  const ov1 = ba1?.overview || {};
  const ov6 = ba6?.overview || {};
  const ov12 = ba12?.overview || {};
  const loc1 = Array.isArray(ba1?.location) ? ba1.location.slice(0,1) : [];
  const loc6 = Array.isArray(ba6?.location) ? ba6.location.slice(0,1) : [];
  const loc12 = Array.isArray(ba12?.location) ? ba12.location.slice(0,1) : [];
  const asp1 = Array.isArray(ba1?.aspect_top) ? ba1.aspect_top.slice(0,1) : [];
  const asp6 = Array.isArray(ba6?.aspect_top) ? ba6.aspect_top.slice(0,1) : [];
  const asp12 = Array.isArray(ba12?.aspect_top) ? ba12.aspect_top.slice(0,1) : [];
  // Keywords emphasize constitution (H1) and illness (H6)
  const kw = (() => {
    const base = ['health','constitution','ascendant','body','illness','disease','work','service'];
    base.push('afflictions','confinement');
    const add = (h) => (Array.isArray(h?.influences) ? h.influences : []).forEach(i => { if (Array.isArray(i?.keywords)) base.push(...i.keywords); });
    if (h1) add(h1);
    if (h6) add(h6);
    if (h12) add(h12);
    return Array.from(new Set(base));
  })();
  const channelText = (s) => `P ${Math.round((s?.presence || 0) * 100)}% G ${Math.round((s?.governance || 0) * 100)}% A ${Math.round((s?.aspect || 0) * 100)}% / ${Number(s?.total || 0).toFixed(1)}`;
  const s1 = buildHouseDeterminationChannels(h1 || {});
  const s6s = buildHouseDeterminationChannels(h6 || {});
  const s12 = buildHouseDeterminationChannels(h12 || {});
  const s4 = buildHouseDeterminationChannels(byNum(4) || {});
  const s8 = buildHouseDeterminationChannels(byNum(8) || {});

  // Primary house for Health per Morin (non-strict: H1; strict: H12)
  const primaryHouse = morinStrict ? (h12 || {}) : (h1 || {});
  const baPrimary = morinStrict ? ba12 : ba1;
  const detPrimary = baPrimary?.determinators_panel || {};
  const sharesPrimary = morinStrict ? s12 : s1;
  const leadKindH = (sharesPrimary.presence >= sharesPrimary.governance && sharesPrimary.presence >= sharesPrimary.aspect) ? 'presence' : ((sharesPrimary.governance >= sharesPrimary.aspect) ? 'governance' : 'aspect');
  const leadItemH = (Array.isArray(detPrimary?.[leadKindH]) && detPrimary[leadKindH].length) ? detPrimary[leadKindH][0] : null;
  const leadPlanetH = leadItemH?.planet || null;
  const leadRankH = leadItemH?.rank || null;
  const govItemH = (Array.isArray(detPrimary?.governance) && detPrimary.governance.length) ? detPrimary.governance[0] : null;
  const govPlanetH = govItemH?.planet || null;
  const routeHouseH = (() => {
    try {
      const r = baPrimary?.ruler_map?.route || baPrimary?.route_line || '';
      const m = String(r).match(/H(\d{1,2})/);
      return m ? m[1] : null;
    } catch(_) { return null; }
  })();
  let aPrimary = (Array.isArray(baPrimary?.aspect_top) && baPrimary.aspect_top.length) ? baPrimary.aspect_top[0] : null;
  if (!aPrimary) {
    const alt = (Array.isArray(detPrimary?.aspect) && detPrimary.aspect.length) ? detPrimary.aspect[0] : null;
    if (alt) aPrimary = alt;
  }
  const orbTxtH = (typeof aPrimary?.orb === 'number') ? `${Number(aPrimary.orb).toFixed(1)} deg` : null;
  const bandH = (typeof aPrimary?.orb === 'number') ? (aPrimary.orb <= 0.5 ? 'partile' : (aPrimary.orb <= 1.5 ? 'tight' : 'wide')) : null;
  const phaseH = aPrimary?.phase || null;
  const aspShortH = aPrimary ? `${aPrimary.planet} ${String(aPrimary.aspect||'').toLowerCase()}` : null;
  const isWeakPressH = !!(aPrimary && typeof aPrimary.orb === 'number' && aPrimary.orb > 2.5 && String(phaseH||'').toLowerCase() === 'separating');
  const pressureLabelH = isWeakPressH ? 'Context' : 'Pressure';
  const leadTextH = leadPlanetH ? `${leadPlanetH} (${leadKindH}${leadRankH? `, ${leadRankH}`:''})` : '-';
  const routeTextH = govPlanetH ? `${govPlanetH}${routeHouseH? ` -> H${routeHouseH}`:''}` : (baPrimary?.overview?.ruler || '-');
  const pressureTextH = aspShortH ? `${aspShortH}${orbTxtH? ` (${orbTxtH}${bandH? `, ${bandH}`:''}${phaseH? `, ${phaseH}`:''})` : ''}` : '-';
  const excludePrim = { leadPlanet: leadPlanetH, govPlanet: govPlanetH, aspectPlanet: aPrimary?.planet, aspectName: aPrimary?.aspect, aspectPhase: aPrimary?.phase };
  const morinNotes = (() => {
    const notes = [];
    try {
      if (asp1.length) {
        const a = asp1[0];
        const malef = ['Saturn','Mars'].includes(String(a?.planet||''));
        const benef = ['Jupiter','Venus'].includes(String(a?.planet||''));
        if (a?.afflicting && malef) notes.push('Malefic affliction to ASC cusp - strain to constitution.');
        if (!a?.afflicting && ['Trine','Sextile'].includes(String(a?.aspect||'')) && benef) notes.push('Benefic support to ASC cusp - constitutional help.');
      }
    } catch (_) {}
    try {
      if (asp6.length) {
        const a = asp6[0];
        const malef = ['Saturn','Mars'].includes(String(a?.planet||''));
        const benef = ['Jupiter','Venus'].includes(String(a?.planet||''));
        if (a?.afflicting && malef) notes.push('Malefic affliction to H6 cusp - illness risk/activation.');
        if (!a?.afflicting && ['Trine','Sextile'].includes(String(a?.aspect||'')) && benef) notes.push('Benefic aspect to H6 cusp - mitigation/aid.');
      }
    } catch (_) {}
    return notes;
  })();
  return (
    <section className="border-t border-zinc-200 pt-4">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <div>
          <div className="font-serif text-[22px] leading-none text-zinc-950">Health Map</div>
          <Micro className="mt-2 block">{morinStrict ? '1st / 12th' : '1st / 6th'}</Micro>
        </div>
        <label className="text-[11px] flex items-center gap-1">
          <input type="checkbox" checked={morinStrict} onChange={e=> setMorinStrict(e.target.checked)} /> Strict illness map
        </label>
      </div>
      {/* Triplicity context */}
      <div className="text-[11px] text-zinc-700 mb-2">
        {morinStrict ? (
          <>
            <div className="mb-1">Suffering Triplicity: <span className="px-1 rounded border border-zinc-200 bg-white">H4</span> <span className="px-1 rounded border border-zinc-200 bg-white">H8</span> <span className="px-1 rounded border border-zinc-200 bg-white">H12</span></div>
            <div className="grid grid-cols-3 gap-2">
              <div className="text-zinc-500">
                <div className="text-[10px]">H4 (background)</div>
                <div className="text-[10px]" title="Presence / governance / aspect share; trailing number is summed influence strength.">{channelText(s4)}</div>
              </div>
              <div className="text-zinc-500">
                <div className="text-[10px]">H8 (background)</div>
                <div className="text-[10px]" title="Presence / governance / aspect share; trailing number is summed influence strength.">{channelText(s8)}</div>
              </div>
              <div className="text-zinc-800">
                <div className="text-[10px] font-medium">H12 (illness) - primary</div>
                <div className="text-[10px]" title="Presence / governance / aspect share; trailing number is summed influence strength.">{channelText(s12)}</div>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="mb-1">Life Triplicity: <span className="px-1 rounded border border-zinc-200 bg-white">H1</span> <span className="px-1 rounded border border-zinc-200 bg-white">H5</span> <span className="px-1 rounded border border-zinc-200 bg-white">H9</span></div>
            <div className="grid grid-cols-3 gap-2">
              <div className="text-zinc-800">
                <div className="text-[10px] font-medium">H1 (constitution) - primary</div>
                <div className="text-[10px]" title="Presence / governance / aspect share; trailing number is summed influence strength.">{channelText(s1)}</div>
              </div>
              <div className="text-zinc-500">
                <div className="text-[10px]">H6 (service) - secondary</div>
                <div className="text-[10px]" title="Presence / governance / aspect share; trailing number is summed influence strength.">{channelText(s6s)}</div>
              </div>
              <div className="text-zinc-500">
                <div className="text-[10px]">H12 (afflictions) - context</div>
                <div className="text-[10px]" title="Presence / governance / aspect share; trailing number is summed influence strength.">{channelText(s12)}</div>
              </div>
            </div>
          </>
        )}
      </div>
      <div className="mb-2">
        <MapStatementRows rows={[
          { label: 'Lead', primary: leadTextH, sub: leadItemH?.tooltip || '' },
          { label: 'Route', primary: routeTextH, sub: baPrimary?.route_line || baPrimary?.ruler_map?.route || '' },
          { label: pressureLabelH, primary: pressureTextH, sub: aPrimary?.phrase || '' },
        ]} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {h1 ? (
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="text-[12px] font-medium">Constitution (1st)</div>
              <div className="text-[11px] px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white">{h1?.sign || '-'}</div>
            </div>
            {/* Health Map: no Ruler/Exalt/Triplicity pills */}
            <div className="mt-1">
              <MiniDeterminators ba={ba1} exclude={(!morinStrict ? excludePrim : {})} />
              {loc1.map((li, i) => {
                const st = li?.state || {};
                const locClass = st?.afflicted ? 'text-rose-700' : ((st?.strong && st?.dignified) ? 'text-emerald-700' : 'text-zinc-800');
                return (
                  <div key={`h1l-${i}`} className={`text-[12px] ${locClass} mt-1 flex items-start gap-1.5`}>
                    <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-current opacity-70"></span>
                    <span className="px-1 rounded border border-zinc-200 bg-white mr-1">{li.planet}</span>
                    <span>{li.summary}</span>
                  </div>
                );
              })}
              {asp1.map((a, i) => {
                const aff = !!a?.afflicting;
                const fav = ['Trine','Sextile'].includes(String(a?.aspect || ''));
                const aspClass = aff ? 'text-rose-700 pl-2' : (fav ? 'text-emerald-700 pl-2' : 'text-zinc-800');
                return (
                  <div key={`h1a-${i}`} className={`text-[12px] ${aspClass} mt-1 flex items-start gap-1.5`}>
                    <span className="px-1 rounded border border-zinc-200 bg-white mr-1">{a.planet}</span>
                    <span>{a.phrase || (`{a.planet} ${a.aspect?.toLowerCase?.() || a.aspect} to ASC`)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
        {(!morinStrict && h6) ? (
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="text-[12px] font-medium">Illness/Service (6th)</div>
              <div className="text-[11px] px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white">{h6?.sign || '-'}</div>
            </div>
            {/* Health Map: no Ruler/Exalt/Triplicity pills */}
            <div className="mt-1">
              <MiniDeterminators ba={ba6} />
              {loc6.map((li, i) => {
                const st = li?.state || {};
                const locClass = st?.afflicted ? 'text-rose-700' : ((st?.strong && st?.dignified) ? 'text-emerald-700' : 'text-zinc-800');
                return (
                  <div key={`h6l-${i}`} className={`text-[12px] ${locClass} mt-1 flex items-start gap-1.5`}>
                    <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-current opacity-70"></span>
                    <span className="px-1 rounded border border-zinc-200 bg-white mr-1">{li.planet}</span>
                    <span>{li.summary}</span>
                  </div>
                );
              })}
              {asp6.map((a, i) => {
                const aff = !!a?.afflicting;
                const fav = ['Trine','Sextile'].includes(String(a?.aspect || ''));
                const aspClass = aff ? 'text-rose-700 pl-2' : (fav ? 'text-emerald-700 pl-2' : 'text-zinc-800');
                return (
                  <div key={`h6a-${i}`} className={`text-[12px] ${aspClass} mt-1 flex items-start gap-1.5`}>
                    <span className={`mt-1 h-2 w-2 rounded-full ${aff ? 'bg-rose-300' : (fav ? 'bg-emerald-300' : 'bg-zinc-300')}`}></span>
                    <span className="px-1 rounded border border-zinc-200 bg-white mr-1">{a.planet}</span>
                    <span>{a.planet} {a.aspect?.toLowerCase?.() || a.aspect} to H6 cusp{a.phrase ? `; ${a.phrase}` : ''}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
        {(morinStrict && h12) ? (
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="text-[12px] font-medium">Illness/Afflictions (12th)</div>
              <div className="text-[11px] px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white">{h12?.sign || '-'}</div>
            </div>
            {/* Health Map: no Ruler/Exalt/Triplicity pills */}
            <div className="mt-1">
              <MiniDeterminators ba={ba12} exclude={(morinStrict ? excludePrim : {})} />
              {loc12.map((li, i) => {
                const st = li?.state || {};
                const locClass = st?.afflicted ? 'text-rose-700' : ((st?.strong && st?.dignified) ? 'text-emerald-700' : 'text-zinc-800');
                return (
                  <div key={`h12l-${i}`} className={`text-[12px] ${locClass} mt-1 flex items-start gap-1.5`}>
                    <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-current opacity-70"></span>
                    <span className="px-1 rounded border border-zinc-200 bg-white mr-1">{li.planet}</span>
                    <span>{li.summary}</span>
                  </div>
                );
              })}
              {asp12.map((a, i) => {
                const aff = !!a?.afflicting;
                const fav = ['Trine','Sextile'].includes(String(a?.aspect || ''));
                const aspClass = aff ? 'text-rose-700 pl-2' : (fav ? 'text-emerald-700 pl-2' : 'text-zinc-800');
                return (
                  <div key={`h12a-${i}`} className={`text-[12px] ${aspClass} mt-1 flex items-start gap-1.5`}>
                    <span className="px-1 rounded border border-zinc-200 bg-white mr-1">{a.planet}</span>
                    <span>{a.phrase || (`${a.planet} ${a.aspect?.toLowerCase?.() || a.aspect} to H12`)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
      {(() => {
        try {
          const sugsA = buildHealthSuggestions(h1, h6, h12, { morinStrict });
          const sugsB = buildFixedStarHealthSuggestions(Array.isArray(fixedStarHits) ? fixedStarHits : []);
          const merged = (() => {
            const acc = new Map();
            [...sugsA, ...sugsB].forEach(s => {
              const k = s.label;
              const prev = acc.get(k);
              if (!prev || Number(s.weight||0) > Number(prev.weight||0)) acc.set(k, s);
            });
            return Array.from(acc.values());
          })();
          const sugs = merged.sort((a,b)=> (Number(b.weight||0) - Number(a.weight||0)) || String(a.label).localeCompare(String(b.label)));
          if (!sugs.length) return null;
          const Chip = ({ s }) => {
            const w = Number(s?.weight || 1);
            const tier = w >= 1.1 ? 'highlight' : (w >= 0.9 ? 'normal' : 'faint');
            const cls = tier === 'highlight'
              ? 'bg-zinc-50 border-zinc-300 text-zinc-900 shadow-sm'
              : (tier === 'normal' ? 'bg-white border-zinc-200 text-zinc-800' : 'bg-white border-zinc-200 text-zinc-600 opacity-80');
            return (
              <span title={s?.reason || ''} className={`text-[11px] px-2 py-1 rounded-full border ${cls}`}>{s.label}</span>
            );
          };
          return (
            <div className="mt-2">
              <div className="text-[11px] font-medium text-zinc-700 mb-1">Health Focus (traditional)</div>
              <div className="flex flex-wrap gap-1.5">
                {sugs.slice(0, 8).map((s, i) => (<Chip key={i} s={s} />))}
              </div>
            </div>
          );
        } catch (_) { return null; }
      })()}
      {morinNotes.length ? (
        <div className="mt-2 border-t border-zinc-100 pt-1">
          <ul className="text-[11px] text-zinc-700 list-disc pl-5">
            {morinNotes.slice(0,4).map((n,i)=> (<li key={i}>{n}</li>))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

// Display filter for structural or redundant tags coming from backend keywords
function filterKeywords(list) {
  try {
    const deny = new Set([
      // Sect flags
      'sect_benefic','malefic_of_sect','in_sect','out_of_sect','hayz',
      // Geometry/structural
      'to-cusp','dominant','fortunate','unfortunate',
      // Cusp names
      'Ascendant','Descendant','Midheaven (MC)','Imum Coeli (IC)','MC','IC','Good Spirit','Bad Spirit','God','God/Sun','Goddess','Gate of Hades',
    ].map(x => String(x).toLowerCase()));
    const out = [];
    const seen = new Set();
    for (const raw of (Array.isArray(list) ? list : [])) {
      const s = String(raw || '').trim();
      if (!s) continue;
      const key = s.toLowerCase();
      if (deny.has(key)) continue;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(s);
    }
    return out;
  } catch {
    return Array.isArray(list) ? list : [];
  }
}

function DomainChip({ domain }){
  const dom = String(domain || 'Uncategorized');
  // Simple deterministic color mapping from domain name
  const palette = [
    ['bg-sky-100','text-sky-800','border-sky-200'],
    ['bg-emerald-100','text-emerald-800','border-emerald-200'],
    ['bg-indigo-100','text-indigo-800','border-indigo-200'],
    ['bg-amber-100','text-amber-800','border-amber-200'],
    ['bg-rose-100','text-rose-800','border-rose-200'],
    ['bg-violet-100','text-violet-800','border-violet-200'],
    ['bg-teal-100','text-teal-800','border-teal-200'],
  ];
  let h = 0; for (let i=0;i<dom.length;i++) h = (h*31 + dom.charCodeAt(i)) >>> 0;
  const idx = h % palette.length;
  const [bg, txt, br] = palette[idx];
  return <span className={`px-1.5 py-0.5 rounded-full border ${bg} ${txt} ${br} text-[10px]`}>{dom}</span>;
}

function TraitFilterNotice({ totalTraits, filteredTraits, band, polarity, selectedDomains, allDomains, onReset }){
  if (totalTraits <= 0 || filteredTraits > 0) return null;
  const details = [];
  if (String(band || '').toLowerCase() !== 'all') details.push(`Band: ${band}`);
  if (String(polarity || '').toLowerCase() !== 'all') details.push(`Polarity: ${polarity}`);
  const selected = Array.isArray(selectedDomains) ? selectedDomains.length : 0;
  const total = Array.isArray(allDomains) ? allDomains.length : 0;
  if (total > 0 && selected > 0 && selected !== total) details.push(`Domains: ${selected}/${total}`);
  return (
    <div className="border border-amber-300 bg-amber-50 rounded-xl px-3 py-2 text-[12px] text-amber-950 flex flex-wrap items-center justify-between gap-2">
      <div>
        <span className="font-medium">No traits match the current filters.</span>
        {details.length ? <span className="ml-1 text-amber-900">Active filters: {details.join(' / ')}</span> : null}
      </div>
      <button type="button" className="px-2 py-1 border border-amber-400 rounded bg-white hover:bg-amber-100 text-[12px]" onClick={onReset}>
        Reset filters
      </button>
    </div>
  );
}

function HouseInfluenceSection({ houseInfluences }){
  const houses = Array.isArray(houseInfluences?.houses) ? houseInfluences.houses : [];
  const [openDetail, setOpenDetail] = useState(null);
  const [openBasic, setOpenBasic] = useState({}); // { [houseNumber]: true }
  // Global alignment for meters: find max value across shown influences
  const sectionMax = useMemo(() => {
    let m = 0;
    for (const h of houses) {
      const list = Array.isArray(h?.influences) ? h.influences.slice(0,4) : [];
      for (const inf of list) {
        const v = Number(inf?.value || 0);
        if (v > m) m = v;
      }
    }
    return m || 1;
  }, [houses]);
  if (!houses.length) return null;
  return (
    <div>
      <div className="mb-5 flex flex-col gap-2 border-b border-zinc-200 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Micro className="block">Houses 1 - 12</Micro>
          <h3 className="mt-1 font-serif text-[26px] leading-tight text-zinc-950">Where each life-area pulls power from</h3>
          <p className="mt-1 max-w-2xl font-serif text-[13px] italic leading-5 text-zinc-500">
            Top influences per house: ruler, occupant, exaltation, triplicity. Strongest signal first.
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-x-8 gap-y-0 md:grid-cols-2 xl:grid-cols-3">
        {houses.map((h) => (
          <section key={h.house} className="border-t border-zinc-200 py-4">
            <div className="mb-3 flex items-baseline justify-between gap-4">
              <div className="flex items-baseline gap-2">
                <div className="font-serif text-[22px] leading-none text-zinc-950">H{h.house}</div>
                <Micro>{h.sign || '-'}</Micro>
              </div>
              <Micro>{(h.degree || h.cusp_degree || h.cusp || '').toString().trim() || '-'}</Micro>
            </div>
            {/* Basic Analysis toggle (non-breaking; shown only when data exists) */}
            {h?.basic_analysis ? (
              <div className="mb-2">
                <button
                  type="button"
                  className="p-0 font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-700 underline-offset-4 hover:underline"
                  onClick={() => setOpenBasic(prev => ({ ...prev, [h.house]: !prev[h.house] }))}
                >
                  {openBasic[h.house] ? 'Hide House Notes' : 'House Notes'}
                </button>
              </div>
            ) : null}
            {h?.basic_analysis && openBasic[h.house] && (
              <div className="mb-3 border-t border-zinc-100 pt-3">
                <div className="text-[12px] font-medium mb-1">{h.basic_analysis.label || 'Basic Analysis'}</div>
                {/* Overview */}
                <div className="text-[12px] text-zinc-700 mb-1">
                  <span className="mr-2">Cusp: {h?.sign || '-'}</span>
                  {(() => {
                    const o = h.basic_analysis.overview || {};
                    const bits = [];
                    if (o.ruler) bits.push(`Ruler: ${o.ruler}`);
                    if (o.exaltation) bits.push(`Exaltation: ${o.exaltation}`);
                    if (o.triplicity_ruler) bits.push(`Triplicity: ${o.triplicity_ruler}`);
                    if (o.house_system_code) bits.push(`System: ${o.house_system_code}`);
                    return <span className="text-zinc-600">{bits.join(' / ')}</span>;
                  })()}
                </div>
                {/* Synthesis bullets */}
                {Array.isArray(h.basic_analysis.synthesis) && h.basic_analysis.synthesis.length ? (
                  <ul className="list-disc pl-5 text-[12px] text-zinc-800 mb-2">
                    {h.basic_analysis.synthesis.slice(0,3).map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                ) : null}
                {/* Location only */}
                <div className="border-t border-zinc-100 pt-2">
                  <div className="text-[11px] font-medium mb-1">Location</div>
                  <ul className="space-y-1">
                    {(Array.isArray(h.basic_analysis.location) ? h.basic_analysis.location : []).slice(0,3).map((li, idx) => (
                      <li key={idx} className="text-[12px] text-zinc-800">
                        <span className="px-1 rounded border border-zinc-200 bg-zinc-50 mr-1">{li.planet}</span>
                        <span>{li.summary}</span>
                      </li>
                    ))}
                    {(!h.basic_analysis.location || h.basic_analysis.location.length === 0) && (
                      <li className="text-[12px] text-zinc-500">No planets by location</li>
                    )}
                  </ul>
                </div>
              </div>
            )}
            <ul className="space-y-1">
              {(Array.isArray(h.influences) ? h.influences : []).slice(0, 4).map((inf, idx) => {
                const role = inf.type === 'occupation' ? 'Occupying'
                            : inf.type === 'rulership' ? 'Ruler'
                            : inf.type === 'aspect' ? (inf.aspect || 'Aspect')
                            : inf.type === 'co_rulership' ? (inf.co_kind === 'exaltation' ? 'Exalt.' : (inf.co_kind === 'triplicity' ? 'Trip.' : 'Trip.(part.)'))
                            : inf.type;
                const v = (inf.value != null) ? `${Number(inf.value).toFixed(2)}` : '-';
                // Grayscale rank encoding: border weight/opacity instead of color
                const rankCls = inf.rank === 'dominant'
                  ? 'border-l-2 border-l-zinc-950'
                  : (inf.rank === 'secondary' ? 'border-l-2 border-l-zinc-400'
                  : 'border-l border-l-zinc-200 opacity-90');
                const key = `${h.house}-${idx}`;
                const bd = inf?.details?.breakdown || null;
                const val = Number(inf?.value || 0);
                const pct = Math.max(0, Math.min(100, (val / sectionMax) * 100));
                return (
                  <li key={key} className={`border-t border-zinc-100 py-3 pl-3 ${rankCls} min-w-0`} title={inf.tooltip || ''}>
                    <div className="flex flex-col gap-2">
                      <div className="grid grid-cols-[minmax(4rem,auto)_minmax(3.5rem,auto)_1fr_2.75rem_auto] items-center gap-2">
                        <div className="min-w-0 text-[12px] text-gray-800 truncate">{inf.planet}</div>
                        <Micro>{role}</Micro>
                        <div className="min-w-12">
                          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-1.5 bg-gray-700" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                        <div className="text-right text-[11px] text-gray-700 font-mono">{v}</div>
                        <button type="button" className="p-0 text-right font-mono text-[10px] uppercase tracking-[0.12em] text-gray-700 underline-offset-4 hover:underline" onClick={()=> setOpenDetail(openDetail === key ? null : key)}>Details</button>
                      </div>
                      {Array.isArray(inf.keywords) && inf.keywords.length ? (
                        <div className="flex flex-wrap gap-1 min-w-0">
                          {filterKeywords(inf.keywords).slice(0,3).map((t,i)=> (
                            <span key={i} className="text-[10px] px-1 py-0.5 rounded border border-gray-300 bg-white text-gray-700">{t}</span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                    {openDetail === key && (
                      <div className="mt-2 text-[12px] border-t border-gray-100 pt-2">
                        {bd ? (
                          <div className="space-y-2">
                            <div className="text-[11px] text-gray-500">Total: {bd.total != null ? bd.total : (inf?.details?.total ?? '-')} (core {bd.core != null ? bd.core : '-'}, aspects {bd?.aspects?.total != null ? bd.aspects.total : '-'})</div>
                            {(() => {
                              const caps = { intrinsic:18, dignity:5, house_position:6, motion:3, solar:5, orientation:2, elevation:1, aspects:30 };
                              const Row = ({ label, val, cap, hint }) => (
                                <div className="flex items-center justify-between gap-2">
                                  <div className="text-gray-700">{label}{hint ? ` (${hint})` : ''}</div>
                                  <div className="flex-1 mx-2">
                                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                      <div className="h-1.5 bg-gray-700" style={{ width: `${Math.max(0, Math.min(100, (Math.abs(Number(val||0))/ (cap||1)) * 100))}%` }} />
                                    </div>
                                  </div>
                                  <div className="text-gray-800 font-mono">{val}</div>
                                </div>
                              );
                              return (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                  <Row label="Intrinsic" val={bd.intrinsic} cap={caps.intrinsic} />
                                  <Row label="Dignity" val={bd.dignity} cap={caps.dignity} />
                                  <Row label="House pos" val={bd.house_position} cap={caps.house_position} />
                                  <Row label="Motion" val={bd.motion} cap={caps.motion} />
                                  <Row label="Solar" val={bd.solar} cap={caps.solar} />
                                  <Row label="Orient." val={bd?.orientation?.value ?? 0} cap={caps.orientation} hint={bd?.orientation?.label || ''} />
                                  <Row label="Elevation" val={bd?.elevation?.value ?? 0} cap={caps.elevation} hint={bd?.elevation?.label || ''} />
                                  <Row label="Aspects" val={bd?.aspects?.total ?? 0} cap={caps.aspects} />
                                </div>
                              );
                            })()}
                            {Array.isArray(bd?.aspects?.top) && bd.aspects.top.length ? (
                              <div className="mt-1">
                                <div className="text-[11px] font-medium text-gray-700">Top Aspect Inputs</div>
                                <ul className="text-[11px] text-gray-700 list-disc pl-4 space-y-0.5">
                                  {bd.aspects.top.map((a,i)=> (
                                    <li key={i}>{a.from} {a.aspect} (orb {a.orb} deg) -&gt; <span className="font-mono">{a.contrib}</span></li>
                                  ))}
                                </ul>
                              </div>
                            ) : null}
                            {Array.isArray(inf.keywords) && inf.keywords.length ? (
                              <div className="flex flex-wrap gap-1 pt-1">
                                {filterKeywords(inf.keywords).map((t,i)=> (
                                  <span key={i} className="text-[10px] px-1 py-0.5 rounded border border-gray-300 bg-white text-gray-700">{t}</span>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        ) : (
                          <div className="text-[11px] text-gray-500">No breakdown available.</div>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
              {(!h.influences || h.influences.length === 0) && (
                <li className="text-xs text-zinc-500">No influence data</li>
              )}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
