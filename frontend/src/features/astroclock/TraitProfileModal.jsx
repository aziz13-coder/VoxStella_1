import React, { useEffect, useMemo, useRef, useState } from 'react';
import { buildProfessionSuggestions, buildHealthSuggestions } from './knowledgeMap.mjs';
import { buildFixedStarProfessionSuggestions, buildFixedStarHealthSuggestions } from './fixedStarMap.mjs';
import { AstroClockAPI } from './api.mjs';

function buildTraitClockContext({ mode, manualIso, manualLocation, timezone, houseSystem }) {
  if (mode === 'manual' && manualIso) {
    return {
      mode: 'manual',
      datetime: manualIso,
      location: manualLocation || undefined,
      timezone: timezone || undefined,
      houseSystem,
    };
  }
  return {
    mode: 'realtime',
    location: manualLocation || undefined,
    timezone: timezone || undefined,
    houseSystem,
  };
}

function normalizeLineage(value) {
  return String(value || '').trim().toLowerCase();
}

function traitMatchesSourceFilter(trait, sourceFilter) {
  const filter = normalizeLineage(sourceFilter);
  if (!filter || filter === 'all') return true;
  const lineage = normalizeLineage(trait?.source_lineage);
  const layers = (trait?.keyword_layers && typeof trait.keyword_layers === 'object') ? trait.keyword_layers : {};
  const citations = Array.isArray(trait?.citations) ? trait.citations : [];
  const hasLayer = (key) => Array.isArray(layers?.[key]) && layers[key].length > 0;
  const hasCitationLineage = (...keys) => citations.some((cit) => keys.includes(normalizeLineage(cit?.source_lineage)));
  if (filter === 'morin') return lineage === 'morin' || hasLayer('morin');
  if (filter === 'classical') return lineage === 'classical' || hasLayer('classical') || hasLayer('textbook') || hasCitationLineage('classical', 'textbook');
  if (filter === 'modern') return lineage === 'modern' || hasLayer('modern') || hasCitationLineage('modern');
  return true;
}

function citationLineageLabel(value) {
  const key = normalizeLineage(value);
  return ({ morin: 'Morin', classical: 'Classical', modern: 'Modern', textbook: 'Textbook' })[key] || (key ? key[0].toUpperCase() + key.slice(1) : 'Source');
}

export default function TraitProfileModal({
  onClose,
  specialDegrees,
  mode,
  manualIso,
  manualLocation,
  timezone,
  houseSystem,
  chartSnapshot = null,
  fixedStarHits: initialFixedStarHits = [],
}){
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [fixedStarHits, setFixedStarHits] = useState(Array.isArray(initialFixedStarHits) ? initialFixedStarHits : []);
  // UI state for filters/sort
  const [band, setBand] = useState('all'); // all|strong|likely|possible
  const [polarity, setPolarity] = useState('all'); // all|positive|neutral|negative
  const [sourceFilter, setSourceFilter] = useState('all'); // all|morin|classical|modern
  const [sortBy, setSortBy] = useState('score'); // score|name|polarity
  const [topCount, setTopCount] = useState(6);
  const [selectedDomains, setSelectedDomains] = useState([]); // empty means all
  const [domainOpen, setDomainOpen] = useState(false);
  const [domainSearch, setDomainSearch] = useState('');
  const domainRef = useRef(null);
  const chartContext = useMemo(
    () => buildTraitClockContext({ mode, manualIso, manualLocation, timezone, houseSystem }),
    [mode, manualIso, manualLocation, timezone, houseSystem],
  );
  const chartContextKey = JSON.stringify(chartContext);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setLoading(true); setError(null);
        const res = await AstroClockAPI.getTraitProfile({ specialDegrees, ...chartContext });
        if (!alive) return;
        if (res?.success) setData(res.data || {});
        else setError('Failed to load');
      } catch (e) {
        if (!alive) return; setError(String(e?.message || 'Failed to load'));
      } finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [Array.isArray(specialDegrees) ? specialDegrees.join('|') : '', chartContextKey]);

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
          source_filter: opts.sourceFilter || 'all',
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
          source_lineage: t.source_lineage || null,
          citation_summary: t.citation_summary || null,
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
              if (a?.afflicting && malef) ns.push('Applying malefic affliction to MC cusp — career obstacles.');
              if (!a?.afflicting && ['Trine','Sextile'].includes(String(a?.aspect||'')) && benef) ns.push('Benefic support to MC cusp — advancement potential.');
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
              if (a1?.afflicting && malef) ns.push('Malefic affliction to ASC cusp — strain to constitution.');
              if (!a1?.afflicting && ['Trine','Sextile'].includes(String(a1?.aspect||'')) && benef) ns.push('Benefic support to ASC cusp — constitutional help.');
            }
          } catch (_) {}
          try {
            const a6 = hSixth?.top_aspect;
            if (a6) {
              const malef = ['Saturn','Mars'].includes(String(a6?.planet||''));
              const benef = ['Jupiter','Venus'].includes(String(a6?.planet||''));
              if (a6?.afflicting && malef) ns.push('Malefic affliction to H6 cusp — illness risk/activation.');
              if (!a6?.afflicting && ['Trine','Sextile'].includes(String(a6?.aspect||'')) && benef) ns.push('Benefic aspect to H6 cusp — mitigation/aid.');
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
            const tot = p+g+a || 1; const q=(x)=> x/tot; const dots=(qv)=> (qv>=0.55?'•••':(qv>=0.30?'••':(qv>0?'•':'·')));
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
      'Glossary: applying=form; separating=wane; partile=≤1° (very strong); dexter=preceding; sinister=following; trine=strongest benefic; opposition=strongest malefic.',
      '',
      'Reasoning: Think deeply through the hierarchy at each house (presence > governance > aspect). Weigh indications carefully; avoid superficial readings.',
      'Conflicts: When indicators disagree, resolve contradictions per Morin\'s hierarchy. Note any key contradictions and how the hierarchy adjudicates them.',
      '',
      'Output structure:',
      '1) High-level summary (2–3 bullets)',
      '2) Planet highlights (top strengths/weaknesses; state notes; 4–6 bullets)',
      '3) House determinations (for notable houses, 1–2 bullets):',
      '   - Location: Planet in House — effect',
      '   - Rulership: Ruler of N in M — pattern (secondary), with ruler map conditions',
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
          const res = await AstroClockAPI.getTraitProfile({ specialDegrees, ...chartContext });
          if (res?.success) fresh = res.data;
        } catch (_) {}
        const payload = fresh || data || {};
      const prompt = buildTraitAnalysisPrompt(payload, {
        fixedStarHits,
        chartSnapshot,
        band,
        polarity,
        sourceFilter,
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
  const allDomains = useMemo(() => {
    const list = Array.isArray(data?.traits) ? data.traits : [];
    const set = new Set();
    list.forEach(t => { if (t?.domain) set.add(String(t.domain)); });
    return Array.from(set).sort();
  }, [data?.traits]);

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
    if (!domainOpen) return;
    const onDoc = (e) => {
      if (domainRef.current && !domainRef.current.contains(e.target)) setDomainOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [domainOpen]);

  const allTraits = useMemo(() => Array.isArray(data?.traits) ? data.traits : [], [data?.traits]);
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
    if (sourceFilter !== 'all') list = list.filter((t) => traitMatchesSourceFilter(t, sourceFilter));
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
  }, [allTraits, band, polarity, sourceFilter, selectedDomains, sortBy]);

  const hasFilteredTraits = filteredTraits.length > 0;
  const hasPartialDomains = allDomains.length > 0 && selectedDomains.length > 0 && selectedDomains.length !== allDomains.length;
  const hasActiveTraitFilters = band !== 'all' || polarity !== 'all' || sourceFilter !== 'all' || hasPartialDomains;

  const resetTraitFilters = () => {
    setBand('all');
    setPolarity('all');
    setSourceFilter('all');
    setSelectedDomains(allDomains);
    setDomainSearch('');
    setDomainOpen(false);
  };

  // Top X by polarity (apply band/domain filters; polarity overridden by section)
  const topByPolarity = useMemo(() => {
    const sourcePriority = (t) => {
      const lineage = String(t?.source_lineage || '').toLowerCase();
      return ({ morin: 5, classical: 4, carter: 3, modern: 2, editorial: 1, provisional: 0 })[lineage] ?? 1;
    };
    const scoreTier = (t) => {
      const score = Number(t?.score || 0);
      return Number.isFinite(score) ? Math.floor(score / 5) : 0;
    };
    const sortSummary = (arr) => [...arr].sort((a, b) => {
      const pa = Number(a?.summary_priority || 0);
      const pb = Number(b?.summary_priority || 0);
      if (pb !== pa) return pb - pa;
      const ta = scoreTier(a);
      const tb = scoreTier(b);
      if (tb !== ta) return tb - ta;
      const la = sourcePriority(a);
      const lb = sourcePriority(b);
      if (lb !== la) return lb - la;
      const sa = Number(a?.score || 0);
      const sb = Number(b?.score || 0);
      if (sb !== sa) return sb - sa;
      return String(a?.name || a?.id || '').localeCompare(String(b?.name || b?.id || ''));
    });
    const applyCommon = (arr) => {
      let r = arr;
      if (band !== 'all') r = r.filter(t => String(t.band || '').toLowerCase() === band);
      if (sourceFilter !== 'all') r = r.filter((t) => traitMatchesSourceFilter(t, sourceFilter));
      if (selectedDomains.length) r = r.filter(t => !t.domain || selectedDomains.includes(String(t.domain)));
      const curated = r.filter((t) => !t?.provisional && String(t?.source_status || '').toLowerCase() !== 'provisional');
      return sortSummary(curated.length ? curated : r);
    };
    const fallback = summaryTraits;
    const posBase = Array.isArray(backendTopTraitsByPolarity?.positive) && backendTopTraitsByPolarity.positive.length
      ? backendTopTraitsByPolarity.positive
      : fallback.filter(t => String(t.polarity || '').toLowerCase() === 'positive');
    const neutralBase = Array.isArray(backendTopTraitsByPolarity?.neutral) && backendTopTraitsByPolarity.neutral.length
      ? backendTopTraitsByPolarity.neutral
      : fallback.filter(t => String(t.polarity || '').toLowerCase() === 'neutral');
    const negBase = Array.isArray(backendTopTraitsByPolarity?.negative) && backendTopTraitsByPolarity.negative.length
      ? backendTopTraitsByPolarity.negative
      : fallback.filter(t => String(t.polarity || '').toLowerCase() === 'negative');
    const pos = applyCommon(posBase)
      .slice(0, Math.max(1, Number(topCount)||6));
    const neutral = applyCommon(neutralBase)
      .slice(0, Math.max(1, Number(topCount)||6));
    const neg = applyCommon(negBase)
      .slice(0, Math.max(1, Number(topCount)||6));
    return { pos, neutral, neg };
  }, [summaryTraits, backendTopTraitsByPolarity, band, sourceFilter, selectedDomains, topCount]);

  const panel = (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-6xl max-h-[92vh] overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-semibold text-sm">Trait Profile</h3>
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            {/* Band filter */}
            <label className="text-zinc-600">Band</label>
            <select aria-label="Band" value={band} onChange={(e)=> setBand(e.target.value)} className="px-2 py-1 border rounded">
              <option value="all">All</option>
              <option value="strong">Strong</option>
              <option value="likely">Likely</option>
              <option value="possible">Possible</option>
              <option value="weak">Weak</option>
            </select>
            {/* Polarity filter (applies to All Traits list) */}
            <label className="text-zinc-600">Polarity</label>
            <select aria-label="Polarity" value={polarity} onChange={(e)=> setPolarity(e.target.value)} className="px-2 py-1 border rounded">
              <option value="all">All</option>
              <option value="positive">Positive</option>
              <option value="neutral">Neutral</option>
              <option value="negative">Negative</option>
            </select>
            <label className="text-zinc-600">Source</label>
            <select aria-label="Source" value={sourceFilter} onChange={(e)=> setSourceFilter(e.target.value)} className="px-2 py-1 border rounded">
              <option value="all">All</option>
              <option value="morin">Morin-facing</option>
              <option value="classical">Classical</option>
              <option value="modern">Modern</option>
            </select>
            {/* Sort */}
            <label className="text-zinc-600">Sort</label>
            <select aria-label="Sort" value={sortBy} onChange={(e)=> setSortBy(e.target.value)} className="px-2 py-1 border rounded">
              <option value="score">Score</option>
              <option value="name">Name</option>
              <option value="polarity">Polarity</option>
            </select>
            {/* Top X */}
            <label className="text-zinc-600">Top</label>
            <select aria-label="Top count" value={String(topCount)} onChange={(e)=> setTopCount(Number(e.target.value)||6)} className="px-2 py-1 border rounded">
              {[3,5,6,8,10].map(n=> (<option key={n} value={n}>{n}</option>))}
            </select>
            {/* Domain dropdown */}
            <div className="relative" ref={domainRef}>
              <button type="button" onClick={()=> setDomainOpen(v=>!v)} className={`px-2 py-1 border rounded hover:bg-zinc-50 ${hasPartialDomains ? 'bg-amber-50 border-amber-300 text-amber-900' : 'bg-white'}`}>
                Domains ({selectedDomains.length}/{allDomains.length || 0})
              </button>
              {domainOpen && (
                <div className="absolute right-0 mt-2 w-64 bg-white border border-zinc-200 rounded-lg shadow-lg p-2 z-50">
                  <input
                    value={domainSearch}
                    onChange={(e)=> setDomainSearch(e.target.value)}
                    placeholder="Search domains"
                    className="w-full text-[12px] px-2 py-1 border border-zinc-300 rounded mb-2 focus:outline-none focus:ring-1 focus:ring-zinc-300"
                  />
                  <div className="flex items-center justify-between mb-2">
                    <label className="flex items-center gap-2 text-[12px]">
                      <input type="checkbox" checked={selectedDomains.length === allDomains.length && allDomains.length>0} onChange={(e)=> e.target.checked ? setSelectedDomains(allDomains) : setSelectedDomains([])} />
                      <span>Select all</span>
                    </label>
                    <button type="button" className="text-[12px] px-2 py-0.5 border rounded hover:bg-zinc-50" onClick={()=> { setSelectedDomains([]); }}>Clear</button>
                  </div>
                  <div className="max-h-56 overflow-auto pr-1">
                    {filteredDomainList.map((dom) => (
                      <label key={dom} className="flex items-center gap-2 text-[12px] py-1">
                        <input type="checkbox" checked={selectedDomains.includes(dom)} onChange={()=> toggleDomain(dom)} />
                        <span>{dom}</span>
                      </label>
                    ))}
                    {filteredDomainList.length === 0 && (
                      <div className="text-[12px] text-zinc-500 py-2">No matches</div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <button
              type="button"
              className="text-[12px] px-2 py-1 border rounded hover:bg-zinc-50"
              onClick={copyAiPrompt}
              disabled={copying || loading || !data}
              title="Copy AI analysis prompt with current trait profile data"
            >
              {copying ? 'Preparing…' : 'Copy AI Prompt'}
            </button>
            {hasActiveTraitFilters ? (
              <button
                type="button"
                className="text-[12px] px-2 py-1 border rounded bg-amber-50 border-amber-300 text-amber-900 hover:bg-amber-100"
                onClick={resetTraitFilters}
              >
                Reset filters
              </button>
            ) : null}
            {copied && (<span className="text-[12px] text-emerald-700">Copied</span>)}
            <button className="text-[12px] px-2 py-1 border rounded hover:bg-zinc-50" onClick={onClose}>Close</button>
          </div>
        </div>
        <div className="p-4 overflow-x-hidden overflow-y-auto flex-1">
          {loading && (<div className="text-sm text-zinc-500">Analyzing…</div>)}
          {error && (<div className="text-sm text-red-600">{error}</div>)}
          {!loading && !error && data && (
            <div className="space-y-4">
              <SummaryBlock summary={data.summary} specialDegrees={data.special_degrees} />
          <TopSplit pos={topByPolarity.pos} neutral={topByPolarity.neutral} neg={topByPolarity.neg} />
              <TraitFilterNotice
                totalTraits={allTraits.length}
                filteredTraits={filteredTraits.length}
                band={band}
                polarity={polarity}
                sourceFilter={sourceFilter}
                selectedDomains={selectedDomains}
                allDomains={allDomains}
                onReset={resetTraitFilters}
              />
              <TopicMapsSection houseInfluences={data.house_influences} fixedStarHits={fixedStarHits} />
              <HouseInfluenceSection houseInfluences={data.house_influences} />
              <AllTraits traits={filteredTraits} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
  return panel;
}

// Fixed star hits are passed via props; no global bridge.

function SummaryBlock({ summary, specialDegrees }){
  if (!summary) return null;
  return (
    <div>
      <div className="text-xs font-medium mb-1">Summary</div>
      <div className="flex flex-wrap gap-2 text-[11px]">
        {summary.dominant_element && (<span className="px-2 py-1 rounded-full border">Element: {summary.dominant_element}</span>)}
        {summary.dominant_modality && (<span className="px-2 py-1 rounded-full border">Modality: {summary.dominant_modality}</span>)}
        {Array.isArray(specialDegrees) && specialDegrees.length ? (
          <span className="px-2 py-1 rounded-full border">Degrees: {specialDegrees.join(' · ')}</span>
        ) : null}
        {summary.flags?.mercury_shock ? (<span className="px-2 py-1 rounded-full border border-amber-300 bg-amber-50">Mercury Shock</span>) : null}
        {summary.flags?.neptune_station_or_angular ? (<span className="px-2 py-1 rounded-full border border-indigo-300 bg-indigo-50">Neptune Station/Angular</span>) : null}
      </div>
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
      <div className="text-xs font-medium mb-2">Topic Maps (Morin)</div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
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
  // Determinator shares per house
  const sharesForHouse = (house) => {
    const list = Array.isArray(house?.influences) ? house.influences : [];
    let pres = 0, gov = 0, asp = 0;
    for (const it of list) {
      const v = Math.abs(Number(it?.value||0));
      if (it?.type === 'occupation') pres += v;
      else if (it?.type === 'rulership' || it?.type === 'co_rulership') gov += v;
      else if (it?.type === 'aspect') asp += v;
    }
    const tot = pres + gov + asp || 1;
    const q = (x) => x / tot;
    return { presence: q(pres), governance: q(gov), aspect: q(asp) };
  };
  const quantDots = (q) => (q >= 0.55 ? '•••' : (q >= 0.30 ? '••' : (q > 0 ? '•' : '·')));
  const s10 = sharesForHouse(h);
  const s2 = sharesForHouse(h2);
  const s6s = sharesForHouse(h6);
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
        if (a?.afflicting && malef) notes.push('Applying malefic affliction to MC cusp — career obstacles.');
        if (!a?.afflicting && ['Trine','Sextile'].includes(String(a?.aspect||'')) && benef) notes.push('Benefic support to MC cusp — advancement potential.');
      }
    } catch (_) {}
    return notes;
  })();
  return (
    <div className="rounded-2xl border border-zinc-100 bg-gradient-to-b from-white to-zinc-50 shadow-sm p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-semibold tracking-tight">Profession Map</div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-zinc-600">10th</span>
          <div className="text-[11px] px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-zinc-700">{h?.sign || '-'}</div>
        </div>
      </div>
      {/* Keywords row removed per request */}
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
            <div className="text-[10px]">H2 (resources) — secondary</div>
            <div className="text-[10px]">P {quantDots(s2.presence)} G {quantDots(s2.governance)} A {quantDots(s2.aspect)}</div>
          </div>
          <div className="text-zinc-500">
            <div className="text-[10px]">H6 (work/service) — secondary</div>
            <div className="text-[10px]">P {quantDots(s6s.presence)} G {quantDots(s6s.governance)} A {quantDots(s6s.aspect)}</div>
          </div>
          <div className="text-zinc-800">
            <div className="text-[10px] font-medium">H10 (profession) — primary</div>
            <div className="text-[10px]">P {quantDots(s10.presence)} G {quantDots(s10.governance)} A {quantDots(s10.aspect)}</div>
          </div>
        </div>
      </div>
      {/* Compact Morin synthesis (deduplicates route text and aspect verbosity) */}
      {(() => {
        const a = aspectSum;
        const orbTxt = (typeof a?.orb === 'number') ? `${Number(a.orb).toFixed(1)}°` : null;
        const band = (typeof a?.orb === 'number') ? (a.orb <= 0.5 ? 'partile' : (a.orb <= 1.5 ? 'tight' : 'wide')) : null;
        const phase = a?.phase || null;
        const aspShort = a ? `${a.planet} ${String(a.aspect||'').toLowerCase()}` : null;
        const isWeakPressure = !!(a && typeof a.orb === 'number' && a.orb > 2.5 && String(phase||'').toLowerCase() === 'separating');
        const pressureLabel = isWeakPressure ? 'Context' : 'Pressure';
        const leadText = leadPlanetSum ? `${leadPlanetSum} (${leadKindSum}${leadRankSum? `, ${leadRankSum}`:''})` : '-';
        const routeText = govPlanetSum ? `${govPlanetSum}${routeHouse? ` → H${routeHouse}`:''}` : (overview?.ruler || '-');
        const pressureText = aspShort ? `${aspShort}${orbTxt? ` (${orbTxt}${band? `, ${band}`:''}${phase? `, ${phase}`:''})` : ''}` : '-';
        return (
          <div className="mb-2">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2">
                <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-0.5">Lead</div>
                <div className="text-[12px] text-zinc-800">{leadText}</div>
              </div>
              <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2">
                <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-0.5">Route</div>
                <div className="text-[12px] text-zinc-800">{routeText}</div>
              </div>
              <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2">
                <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-0.5">{pressureLabel}</div>
                <div className="text-[12px] text-zinc-800">{pressureText}</div>
              </div>
            </div>
          </div>
        );
      })()}
      {/* Presence vs. governance hint removed per request */}
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
        {/* Removed geometric chips to avoid duplication with Pressure box */}
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
        <div className="text-[10px] text-zinc-500 mt-1">H4 (opposition) — secondary frame; weaker determination</div>
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
      {/* Removed general bubbles for a cleaner look */}
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
    </div>
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
  // shares
  const sharesForHouse = (house) => {
    const list = Array.isArray(house?.influences) ? house.influences : [];
    let pres = 0, gov = 0, asp = 0;
    for (const it of list) {
      const v = Math.abs(Number(it?.value||0));
      if (it?.type === 'occupation') pres += v;
      else if (it?.type === 'rulership' || it?.type === 'co_rulership') gov += v;
      else if (it?.type === 'aspect') asp += v;
    }
    const tot = pres + gov + asp || 1;
    const q = (x) => x / tot;
    return { presence: q(pres), governance: q(gov), aspect: q(asp) };
  };
  const quantDots = (q) => (q >= 0.55 ? '•••' : (q >= 0.30 ? '••' : (q > 0 ? '•' : '·')));
  const s1 = sharesForHouse(h1||{});
  const s6s = sharesForHouse(h6||{});
  const s12 = sharesForHouse(h12||{});
  const s4 = sharesForHouse(byNum(4) || {});
  const s8 = sharesForHouse(byNum(8) || {});

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
  const orbTxtH = (typeof aPrimary?.orb === 'number') ? `${Number(aPrimary.orb).toFixed(1)}°` : null;
  const bandH = (typeof aPrimary?.orb === 'number') ? (aPrimary.orb <= 0.5 ? 'partile' : (aPrimary.orb <= 1.5 ? 'tight' : 'wide')) : null;
  const phaseH = aPrimary?.phase || null;
  const aspShortH = aPrimary ? `${aPrimary.planet} ${String(aPrimary.aspect||'').toLowerCase()}` : null;
  const isWeakPressH = !!(aPrimary && typeof aPrimary.orb === 'number' && aPrimary.orb > 2.5 && String(phaseH||'').toLowerCase() === 'separating');
  const pressureLabelH = isWeakPressH ? 'Context' : 'Pressure';
  const leadTextH = leadPlanetH ? `${leadPlanetH} (${leadKindH}${leadRankH? `, ${leadRankH}`:''})` : '-';
  const routeTextH = govPlanetH ? `${govPlanetH}${routeHouseH? ` → H${routeHouseH}`:''}` : (baPrimary?.overview?.ruler || '-');
  const pressureTextH = aspShortH ? `${aspShortH}${orbTxtH? ` (${orbTxtH}${bandH? `, ${bandH}`:''}${phaseH? `, ${phaseH}`:''})` : ''}` : '-';
  const excludePrim = { leadPlanet: leadPlanetH, govPlanet: govPlanetH, aspectPlanet: aPrimary?.planet, aspectName: aPrimary?.aspect, aspectPhase: aPrimary?.phase };
  const morinNotes = (() => {
    const notes = [];
    try {
      if (asp1.length) {
        const a = asp1[0];
        const malef = ['Saturn','Mars'].includes(String(a?.planet||''));
        const benef = ['Jupiter','Venus'].includes(String(a?.planet||''));
        if (a?.afflicting && malef) notes.push('Malefic affliction to ASC cusp — strain to constitution.');
        if (!a?.afflicting && ['Trine','Sextile'].includes(String(a?.aspect||'')) && benef) notes.push('Benefic support to ASC cusp — constitutional help.');
      }
    } catch (_) {}
    try {
      if (asp6.length) {
        const a = asp6[0];
        const malef = ['Saturn','Mars'].includes(String(a?.planet||''));
        const benef = ['Jupiter','Venus'].includes(String(a?.planet||''));
        if (a?.afflicting && malef) notes.push('Malefic affliction to H6 cusp — illness risk/activation.');
        if (!a?.afflicting && ['Trine','Sextile'].includes(String(a?.aspect||'')) && benef) notes.push('Benefic aspect to H6 cusp — mitigation/aid.');
      }
    } catch (_) {}
    return notes;
  })();
  return (
    <div className="rounded-2xl border border-zinc-100 bg-gradient-to-b from-white to-zinc-50 shadow-sm p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-medium">Health Map ({morinStrict? '1st • 12th' : '1st • 6th'})</div>
        <label className="text-[11px] flex items-center gap-1">
          <input type="checkbox" checked={morinStrict} onChange={e=> setMorinStrict(e.target.checked)} /> Morin strict
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
                <div className="text-[10px]">P {quantDots(s4.presence)} G {quantDots(s4.governance)} A {quantDots(s4.aspect)}</div>
              </div>
              <div className="text-zinc-500">
                <div className="text-[10px]">H8 (background)</div>
                <div className="text-[10px]">P {quantDots(s8.presence)} G {quantDots(s8.governance)} A {quantDots(s8.aspect)}</div>
              </div>
              <div className="text-zinc-800">
                <div className="text-[10px] font-medium">H12 (illness) — primary</div>
                <div className="text-[10px]">P {quantDots(s12.presence)} G {quantDots(s12.governance)} A {quantDots(s12.aspect)}</div>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="mb-1">Life Triplicity: <span className="px-1 rounded border border-zinc-200 bg-white">H1</span> <span className="px-1 rounded border border-zinc-200 bg-white">H5</span> <span className="px-1 rounded border border-zinc-200 bg-white">H9</span></div>
            <div className="grid grid-cols-3 gap-2">
              <div className="text-zinc-800">
                <div className="text-[10px] font-medium">H1 (constitution) — primary</div>
                <div className="text-[10px]">P {quantDots(s1.presence)} G {quantDots(s1.governance)} A {quantDots(s1.aspect)}</div>
              </div>
              <div className="text-zinc-500">
                <div className="text-[10px]">H6 (service) — secondary</div>
                <div className="text-[10px]">P {quantDots(s6s.presence)} G {quantDots(s6s.governance)} A {quantDots(s6s.aspect)}</div>
              </div>
              <div className="text-zinc-500">
                <div className="text-[10px]">H12 (afflictions) — context</div>
                <div className="text-[10px]">P {quantDots(s12.presence)} G {quantDots(s12.governance)} A {quantDots(s12.aspect)}</div>
              </div>
            </div>
          </>
        )}
      </div>
      {/* Primary summary (identical style to Profession Map) */}
      <div className="mb-2">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2">
            <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-0.5">Lead</div>
            <div className="text-[12px] text-zinc-800">{leadTextH}</div>
          </div>
          <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2">
            <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-0.5">Route</div>
            <div className="text-[12px] text-zinc-800">{routeTextH}</div>
          </div>
          <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2">
            <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-0.5">{pressureLabelH}</div>
            <div className="text-[12px] text-zinc-800">{pressureTextH}</div>
          </div>
        </div>
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
      {/* Removed general bubbles for a cleaner look */}
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
    </div>
  );
}

function TopTraits({ traits }){
  const list = Array.isArray(traits) ? traits : [];
  if (!list.length) return null;
  return (
    <div>
      <div className="text-xs font-medium mb-1">Top Traits</div>
      <div className="grid grid-cols-3 gap-3">
        {list.map((t, i) => (<TraitCard key={i} t={t} compact />))}
      </div>
    </div>
  );
}

function AllTraits({ traits }){
  const list = Array.isArray(traits) ? traits : [];
  if (!list.length) return null;
  // Group by domain and order groups by aggregate score (top-3 sum), then alphabetically
  const groups = new Map();
  list.forEach(t => {
    const dom = String(t?.domain || 'Uncategorized');
    if (!groups.has(dom)) groups.set(dom, []);
    groups.get(dom).push(t);
  });
  const groupEntries = Array.from(groups.entries()).map(([dom, arr]) => {
    const sorted = arr.slice().sort((a,b)=> Number(b?.score||0) - Number(a?.score||0));
    const agg = sorted.slice(0,3).reduce((s,x)=> s + Number(x?.score||0), 0);
    return { dom, items: sorted, agg };
  }).sort((a,b)=> (b.agg - a.agg) || a.dom.localeCompare(b.dom));
  return (
    <div>
      <div className="text-xs font-medium mb-2">All Traits</div>
      <div className="space-y-4">
        {groupEntries.map((g, gi) => (
          <div key={gi}>
            <div className="mb-1 flex items-center justify-between">
              <div className="text-[12px] font-medium flex items-center gap-2">
                <DomainChip domain={g.dom} />
                <span className="text-zinc-500">{g.items.length} items</span>
              </div>
            </div>
            <div className="space-y-2">
              {g.items.map((t, i) => (<TraitCard key={`${gi}-${i}`} t={t} />))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TraitCard({ t, compact }){
  const pct = Math.round(Math.min(100, Math.max(0, Number(t?.score || 0))));
  const pol = String(t?.polarity || '').toLowerCase();
  const scoreColor = pol === 'positive' ? 'text-emerald-700' : pol === 'negative' ? 'text-rose-700' : 'text-zinc-700';
  const supportHits = Number(t?.support_hits || 0);
  const supportTotal = Number(t?.support_total || 0);
  const rawScore = Number(t?.raw_score || 0);
  const maxScore = Number(t?.max_score || 0);
  const provisional = !!t?.provisional || String(t?.source_status || '').toLowerCase() === 'provisional';
  const sourceLineage = String(t?.source_lineage || '').toLowerCase();
  const sourceLineageLabel = String(t?.source_lineage_label || '').trim();
  const keywordLayers = (t?.keyword_layers && typeof t.keyword_layers === 'object') ? t.keyword_layers : {};
  const citations = Array.isArray(t?.citations) ? t.citations : [];
  const citationSummary = (t?.citation_summary && typeof t.citation_summary === 'object') ? t.citation_summary : null;
  const layerEntries = Object.entries(keywordLayers)
    .map(([key, items]) => [key, filterKeywords(items).slice(0, 6)])
    .filter(([, items]) => Array.isArray(items) && items.length);
  // Map score to color side: positive => right half (green), negative => left half (red)
  const mapped = (() => {
    if (pol === 'positive') return 50 + (pct / 2);
    if (pol === 'negative') return 50 - (pct / 2);
    return 50; // neutral/unknown stays centered
  })();
  const knobLeft = `calc(${Math.max(0, Math.min(100, mapped))}% - 8px)`; // center the knob over position
  return (
    <div className="border border-zinc-200 rounded p-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="font-medium text-sm">{t?.name || t?.id}</div>
          {!compact && t?.domain ? (<DomainChip domain={t.domain} />) : null}
          {provisional ? (
            <span
              className="px-1.5 py-0.5 rounded-full border border-amber-200 bg-amber-50 text-amber-800 text-[10px]"
              title="This trait is derived from placeholder or not-yet-fully-curated source material."
            >
              Provisional source
            </span>
          ) : null}
          {!provisional && sourceLineageLabel ? (
            <span
              className="px-1.5 py-0.5 rounded-full border border-sky-200 bg-sky-50 text-sky-800 text-[10px]"
              title="Lineage of the rule source used for this trait."
            >
              {sourceLineageLabel}
            </span>
          ) : null}
          {!provisional && citationSummary?.count ? (
            <span
              className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-zinc-50 text-zinc-700 text-[10px]"
              title="Corpus-backed citation support attached to this trait."
            >
              {citationSummary.count} citation{citationSummary.count === 1 ? '' : 's'}
            </span>
          ) : null}
        </div>
        <div className={`text-[11px] ${scoreColor}`}>{pct}%</div>
      </div>
      {/* Dignities-like gradient bar with midline and knob */}
      <div className="mt-2">
        <div className="relative h-3 rounded-full" style={{ background: 'linear-gradient(90deg, var(--grad-left,#fecdd3), var(--grad-mid,#e5e7eb), var(--grad-right,#bbf7d0))' }}>
          <div className="absolute inset-y-0 left-1/2 w-px bg-zinc-400/70" />
          <div className="absolute -top-1 -bottom-1 w-4 rounded-full border border-zinc-800/30 bg-white" style={{ left: knobLeft }} />
        </div>
      </div>
      <div className="mt-1 text-[10px] text-zinc-500 flex flex-wrap items-center gap-x-2 gap-y-1">
        <span>{supportHits}/{supportTotal || 0} supports active</span>
        {maxScore > 0 ? <span>raw {rawScore.toFixed(1)}/{maxScore.toFixed(1)}</span> : null}
        {Number(t?.family_size || 1) > 1 ? <span>{Number(t?.family_size || 1) - 1} related variants</span> : null}
        {provisional ? <span>placeholder-derived</span> : null}
        {!provisional && sourceLineage && sourceLineage !== 'editorial' ? <span>{sourceLineageLabel}</span> : null}
        {!provisional && citationSummary?.top_source ? <span>{citationSummary.top_source}</span> : null}
      </div>
      {/* Trait-level Morin keywords (compact view only) */}
      {compact && Array.isArray(t?.keywords) && t.keywords.length ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {filterKeywords(t.keywords).slice(0,5).map((kw, i) => (
            <span key={i} className="text-[10px] px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-zinc-700" title="Morin keyword">
              {String(kw)}
            </span>
          ))}
        </div>
      ) : null}
      {!compact && (
        <>
          {t?.description ? (<div className="mt-1 text-xs text-zinc-700">{t.description}</div>) : null}
          {Array.isArray(t?.evidence) && t.evidence.length ? (
            <ul className="mt-1 text-[11px] text-zinc-600 list-disc pl-5">
              {t.evidence.slice(0,6).map((e,i)=> (<li key={i}>{e}</li>))}
            </ul>
          ) : null}
          {layerEntries.length ? (
            <div className="mt-2 space-y-2">
              <div className="text-[11px] font-medium text-zinc-700">Source Layers</div>
              {layerEntries.map(([layer, items]) => (
                <div key={layer}>
                  <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-1">{citationLineageLabel(layer)}</div>
                  <Keywords items={items} />
                </div>
              ))}
            </div>
          ) : null}
          {citations.length ? (
            <div className="mt-2">
              <div className="text-[11px] font-medium text-zinc-700">Corpus Citations</div>
              <ul className="mt-1 text-[11px] text-zinc-600 list-disc pl-5 space-y-1">
                {citations.slice(0, 3).map((citation, index) => (
                  <li key={citation?.citation_id || index}>
                    <span className="inline-block mr-1 px-1 py-0.5 rounded-full border border-zinc-200 bg-white text-[10px] text-zinc-700">
                      {citationLineageLabel(citation?.source_lineage)}
                    </span>
                    <span className="font-medium text-zinc-700">{citation?.source_label || 'Corpus source'}</span>
                    {citation?.excerpt ? `: ${citation.excerpt}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}
    </div>
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

function TopSplit({ pos, neutral, neg }){
  const p = Array.isArray(pos) ? pos : [];
  const m = Array.isArray(neutral) ? neutral : [];
  const n = Array.isArray(neg) ? neg : [];
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div className="border border-zinc-200 rounded-2xl p-3">
        <div className="text-xs font-medium mb-2">Top Positive</div>
        {p.length === 0 ? (
          <div className="text-xs text-zinc-500">No results</div>
        ) : (
          <div className="space-y-2">
            {p.map((t, i) => (<TraitCard key={`p${i}`} t={t} compact />))}
          </div>
        )}
      </div>
      <div className="border border-zinc-200 rounded-2xl p-3">
        <div className="text-xs font-medium mb-2">Top Neutral</div>
        {m.length === 0 ? (
          <div className="text-xs text-zinc-500">No results</div>
        ) : (
          <div className="space-y-2">
            {m.map((t, i) => (<TraitCard key={`m${i}`} t={t} compact />))}
          </div>
        )}
      </div>
      <div className="border border-zinc-200 rounded-2xl p-3">
        <div className="text-xs font-medium mb-2">Top Negative</div>
        {n.length === 0 ? (
          <div className="text-xs text-zinc-500">No results</div>
        ) : (
          <div className="space-y-2">
            {n.map((t, i) => (<TraitCard key={`n${i}`} t={t} compact />))}
          </div>
        )}
      </div>
    </div>
  );
}

function TraitFilterNotice({ totalTraits, filteredTraits, band, polarity, sourceFilter, selectedDomains, allDomains, onReset }){
  if (totalTraits <= 0 || filteredTraits > 0) return null;
  const details = [];
  if (String(band || '').toLowerCase() !== 'all') details.push(`Band: ${band}`);
  if (String(polarity || '').toLowerCase() !== 'all') details.push(`Polarity: ${polarity}`);
  if (String(sourceFilter || '').toLowerCase() !== 'all') details.push(`Source: ${citationLineageLabel(sourceFilter)}`);
  const selected = Array.isArray(selectedDomains) ? selectedDomains.length : 0;
  const total = Array.isArray(allDomains) ? allDomains.length : 0;
  if (total > 0 && selected > 0 && selected !== total) details.push(`Domains: ${selected}/${total}`);
  return (
    <div className="border border-amber-300 bg-amber-50 rounded-xl px-3 py-2 text-[12px] text-amber-950 flex flex-wrap items-center justify-between gap-2">
      <div>
        <span className="font-medium">No traits match the current filters.</span>
        {details.length ? <span className="ml-1 text-amber-900">Active filters: {details.join(' · ')}</span> : null}
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
      <div className="text-xs font-medium mb-1">House Influence</div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {houses.map((h) => (
          <div key={h.house} className="border border-zinc-200 rounded-2xl p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium">House {h.house}</div>
              <div className="text-[11px] px-1.5 py-0.5 rounded-full border border-zinc-200 bg-zinc-50">
                {h.sign || '-'}
              </div>
            </div>
            {/* Basic Analysis toggle (non-breaking; shown only when data exists) */}
            {h?.basic_analysis ? (
              <div className="mb-2">
                <button
                  type="button"
                  className="text-[11px] px-1.5 py-0.5 rounded border border-zinc-300 text-gray-700 hover:bg-gray-50"
                  onClick={() => setOpenBasic(prev => ({ ...prev, [h.house]: !prev[h.house] }))}
                >
                  {openBasic[h.house] ? 'Hide Basic Analysis' : 'Show Basic Analysis'}
                </button>
              </div>
            ) : null}
            {h?.basic_analysis && openBasic[h.house] && (
              <div className="mb-3 rounded-lg border border-zinc-100 bg-zinc-50 p-2">
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
                    return <span className="text-zinc-600">{bits.join(' · ')}</span>;
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
                <div className="bg-white rounded border border-zinc-200 p-2">
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
                  ? 'border-2 border-gray-400 shadow-sm'
                  : (inf.rank === 'secondary' ? 'border border-gray-300'
                  : 'border border-gray-200 opacity-80');
                const key = `${h.house}-${idx}`;
                const bd = inf?.details?.breakdown || null;
                const val = Number(inf?.value || 0);
                const pct = Math.max(0, Math.min(100, (val / sectionMax) * 100));
                return (
                  <li key={key} className={`px-2 py-1 rounded-lg ${rankCls} min-w-0`} title={inf.tooltip || ''}>
                    <div className="flex flex-col gap-2">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div className="flex min-w-0 items-center gap-2 flex-wrap">
                          <span className="px-1.5 py-0.5 rounded-full border border-gray-300 bg-white text-[11px] text-gray-700 flex-shrink-0">{inf.planet}</span>
                          <span className="text-sm text-gray-800 truncate max-w-[9rem] sm:max-w-[12rem]">{role}</span>
                        </div>
                        <div className="flex min-w-0 items-center justify-end gap-2 sm:flex-nowrap">
                          <div className="w-16 sm:w-20 md:w-24 flex-shrink-0">
                            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                              <div className="h-1.5 bg-gray-700" style={{ width: `${pct}%` }} />
                            </div>
                          </div>
                          <div className="w-10 text-right text-[11px] text-gray-700 font-mono flex-shrink-0">{v}</div>
                          <button type="button" className="text-[11px] px-1.5 py-0.5 rounded border border-gray-300 text-gray-700 hover:bg-gray-50 flex-shrink-0" onClick={()=> setOpenDetail(openDetail === key ? null : key)}>Details</button>
                        </div>
                      </div>
                      {Array.isArray(inf.keywords) && inf.keywords.length ? (
                        <div className="flex flex-wrap gap-1 min-w-0">
                          {filterKeywords(inf.keywords).slice(0,3).map((t,i)=> (
                            <span key={i} className="text-[10px] px-1 py-0.5 rounded-full border border-gray-300 bg-white text-gray-700">{t}</span>
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
                                    <li key={i}>{a.from} {a.aspect} (orb {a.orb}°) → <span className="font-mono">{a.contrib}</span></li>
                                  ))}
                                </ul>
                              </div>
                            ) : null}
                            {Array.isArray(inf.keywords) && inf.keywords.length ? (
                              <div className="flex flex-wrap gap-1 pt-1">
                                {filterKeywords(inf.keywords).map((t,i)=> (
                                  <span key={i} className="text-[10px] px-1 py-0.5 rounded-full border border-gray-300 bg-white text-gray-700">{t}</span>
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
          </div>
        ))}
      </div>
    </div>
  );
}
