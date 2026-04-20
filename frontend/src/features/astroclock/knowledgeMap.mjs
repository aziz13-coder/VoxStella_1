// Lightweight Morin-inspired knowledge mapper for Topic Maps
// No backend changes; uses existing determinators and basic_analysis context

const SIGN_PROFESSIONS = {
  Aries: [
    'military', 'security', 'engineering', 'mechanics', 'sports', 'surgery', 'emergency response'
  ],
  Taurus: [
    'finance', 'banking', 'valuation', 'agriculture', 'music/voice', 'building', 'craftsmanship', 'beauty trade'
  ],
  Gemini: [
    'writing', 'journalism', 'media', 'commerce', 'merchants', 'transport/logistics', 'teaching', 'clerical', 'data'
  ],
  Cancer: [
    'hospitality', 'provisioning', 'food service', 'real estate', 'domestic management', 'maritime', 'property'
  ],
  Leo: [
    'leadership', 'government', 'judiciary', 'entertainment', 'spectacle', 'luxury goods', 'public office'
  ],
  Virgo: [
    'analysis', 'editing', 'bookkeeping', 'accounting', 'medicine (support)', 'technical crafts', 'audit'
  ],
  Libra: [
    'law', 'judiciary', 'diplomacy', 'design', 'aesthetics', 'partnership practice', 'contracts'
  ],
  Scorpio: [
    'research', 'forensics', 'surgery', 'risk finance', 'security/intelligence', 'taxation'
  ],
  Sagittarius: [
    'law', 'clergy', 'publishing', 'academia', 'higher education', 'travel trade', 'foreign service'
  ],
  Capricorn: [
    'administration', 'governance', 'civil service', 'engineering', 'architecture', 'construction', 'land management'
  ],
  Aquarius: [
    'technology', 'software', 'innovation', 'social reform', 'networks', 'associations', 'telecom'
  ],
  Pisces: [
    'maritime', 'navigation', 'healing arts', 'charity', 'institutions', 'spiritual vocations'
  ]
};

const PLANET_PROFESSIONS = {
  Sun: ['leadership', 'public office', 'management', 'command'],
  Moon: ['provisioning', 'logistics', 'hospitality', 'care work', 'travel', 'maritime'],
  Mercury: ['writing', 'clerks/notaries', 'trade', 'analysis', 'teaching', 'accounting', 'software/data'],
  Venus: ['arts', 'music', 'design', 'beauty industry', 'diplomacy', 'luxury/fashion'],
  Mars: ['military', 'security/police', 'surgery', 'mechanics/metalwork', 'competition'],
  Jupiter: ['law', 'clergy', 'academia', 'diplomacy/philanthropy'],
  Saturn: ['administration', 'surveying', 'architecture', 'construction', 'land governance', 'mining']
};

const RULER_ROUTE_PROF = {
  1: ['self‑employment', 'artisan trades'],
  2: ['finance', 'banking', 'treasury'],
  3: ['media', 'transport', 'communications', 'logistics'],
  4: ['real estate', 'land management', 'building'],
  5: ['entertainment', 'performance', 'education of youth'],
  6: ['service', 'healthcare support', 'craft', 'management of subordinates'],
  7: ['law practice', 'public relations', 'contract business'],
  8: ['taxation', 'estates', 'risk finance', 'forensics'],
  9: ['law', 'clergy', 'academia', 'publishing', 'foreign service'],
  10: ['leadership', 'office', 'command'],
  11: ['politics', 'patronage', 'networks', 'associations'],
  12: ['institutions', 'hospitals', 'charity', 'monastic orders']
};

const SIGN_HEALTH = {
  Aries: ['head', 'eyes', 'fever/inflammation', 'injury'],
  Taurus: ['throat', 'neck', 'thyroid', 'voice'],
  Gemini: ['lungs', 'arms/hands', 'nervous system', 'respiration'],
  Cancer: ['stomach', 'digestion', 'fluids', 'breast'],
  Leo: ['heart', 'spine', 'circulation'],
  Virgo: ['intestines', 'assimilation', 'malabsorption'],
  Libra: ['kidneys', 'lumbar region', 'hormonal'],
  Scorpio: ['reproductive system', 'excretory organs', 'toxicity'],
  Sagittarius: ['liver', 'hips/thighs', 'sciatica'],
  Capricorn: ['bones', 'skin', 'teeth', 'joints'],
  Aquarius: ['ankles/calves', 'circulatory', 'nervous'],
  Pisces: ['feet', 'lymph', 'susceptibility', 'addictions', 'immune']
};

const PLANET_HEALTH = {
  Sun: ['heart', 'vital heat', 'circulation'],
  Moon: ['fluids', 'digestion', 'emotional'],
  Mercury: ['nerves', 'respiration', 'mental'],
  Venus: ['kidneys', 'sugar/indulgence', 'throat'],
  Mars: ['fever', 'inflammation', 'injury', 'surgery', 'bleeding'],
  Jupiter: ['liver', 'excess', 'tumors/swellings'],
  Saturn: ['bones', 'skin', 'chronic obstruction', 'teeth', 'depression']
};

const BENE = new Set(['Jupiter','Venus']);
const MALE = new Set(['Saturn','Mars']);

const RANK_W = { dominant: 1.0, secondary: 0.7, tertiary: 0.45 };
// Morin hierarchy: emphasize location over governance over aspect-support
const DET_KIND_W = { presence: 1.35, governance: 1.0, co_rulership: 0.6 };

function adverbFactor(adverb) {
  const a = String(adverb || '').toLowerCase();
  if (!a) return 1.0;
  if (a.includes('strong')) return 1.15;
  if (a.includes('slight')) return 0.9;
  if (a.includes('moder')) return 1.0;
  return 1.0;
}

function aspectFactor(a) {
  if (!a) return 1.0;
  const aff = !!a.afflicting;
  const aspect = String(a.aspect || '');
  const phase = String(a.phase || '').toLowerCase();
  let f = 1.0;
  if (aff) f *= 0.85;
  else if (aspect === 'Trine' || aspect === 'Sextile') f *= 1.1;
  if (phase === 'applying') f *= 1.05;
  if (phase === 'separating') f *= 0.95;
  return f;
}

function rulerCondFactor(conditions) {
  const arr = Array.isArray(conditions) ? conditions.map(x => String(x).toLowerCase()) : [];
  let f = 1.0;
  if (arr.some(s => s.includes('dignified') || s.includes('cazimi'))) f *= 1.1;
  if (arr.some(s => s.includes('angular'))) f *= 1.08;
  if (arr.some(s => s.includes('succedent'))) f *= 1.03;
  if (arr.some(s => s.includes('cadent'))) f *= 0.92;
  if (arr.some(s => s.includes('debilitated'))) f *= 0.9;
  if (arr.some(s => s.includes('retro'))) f *= 0.92;
  if (arr.some(s => s.includes('combust'))) f *= 0.9;
  if (arr.some(s => s.includes('under beams'))) f *= 0.94;
  return f;
}

function uniqByLabel(items) {
  const acc = new Map();
  for (const it of items) {
    const key = it?.label || JSON.stringify(it);
    if (!acc.has(key)) acc.set(key, it);
    else {
      // Keep the higher weight
      const cur = acc.get(key);
      if (Number(it.weight || 0) > Number(cur.weight || 0)) acc.set(key, it);
    }
  }
  return Array.from(acc.values());
}

function isRouteSuggestion(item) {
  const reason = String(item?.reason || '');
  return reason.startsWith('ruler route H') || reason.startsWith('ruler in H');
}

function suggestionReasonPriority(reason) {
  const text = String(reason || '').toLowerCase();
  if (text.startsWith('ruler route h')) return 1.2;
  if (text.startsWith('ruler in h')) return 1.16;
  if (text.startsWith('10th sign ')) return 1.1;
  if (text.includes('presence')) return 1.06;
  if (text.includes('rulership') || text.includes('governance')) return 1.03;
  if (text.includes('lead determinator')) return 1.0;
  if (text.includes('mc pressure')) return 0.98;
  if (text.includes('support') || text.includes('background')) return 0.92;
  return 1.0;
}

function professionFamily(label) {
  const text = String(label || '').toLowerCase();
  if (!text) return 'general';
  if (/(judge|judiciar|law|legal|notary|contract|diplomat|clergy|public advocacy|public relations|mediator)/.test(text)) return 'legal-public';
  if (/(leadership|management|command|public office|senior administrator|public administrator|governance|civil service)/.test(text)) return 'executive-office';
  if (/(academia|professor|teacher|teaching|publishing|publisher|editor|records\/registrar|writing|journalism|media|software|data|analysis|clerical|commerce|merchants|transport\/logistics|printer)/.test(text)) return 'intellectual-media';
  if (/(technology|innovation|telecom|networks|associations|social reform)/.test(text)) return 'technology-networks';
  if (/(arts|music|design|beauty|luxury|fashion|aesthetics|perfumery|jewelry|performing arts|entertainment|spectacle)/.test(text)) return 'arts-aesthetics';
  if (/(military|security|police|surgery|mechanics|metalwork|fire service|orthopedic|engineering|emergency response|competition|sports)/.test(text)) return 'martial-technical';
  if (/(finance|banking|treasury|valuation|tax|forensic accounting|risk finance|estates|accountancy)/.test(text)) return 'finance-estates';
  if (/(real estate|land|building|construction|architecture|survey)/.test(text)) return 'land-building';
  if (/(hospitality|provisioning|food|maritime|care work|quartermaster|property|domestic)/.test(text)) return 'care-provisioning';
  if (/(charity|healing|institutions|hospital roles|monastic)/.test(text)) return 'institutional-service';
  if (/(political organizer|association director|politics|patronage)/.test(text)) return 'politics-networks';
  return 'general';
}

function professionContextFactor(label, { sign, routeHouse, leadPlanet }) {
  const family = professionFamily(label);
  let factor = 1.0;
  if (family === 'legal-public') {
    if ([7, 9].includes(routeHouse) || ['Libra', 'Sagittarius'].includes(sign) || ['Jupiter', 'Mercury', 'Venus'].includes(leadPlanet)) factor *= 1.08;
    else factor *= 0.84;
  } else if (family === 'executive-office') {
    if ([10, 11].includes(routeHouse) || ['Leo', 'Capricorn'].includes(sign) || leadPlanet === 'Sun') factor *= 1.08;
    else factor *= 0.96;
  } else if (family === 'intellectual-media') {
    if ([3, 5, 9].includes(routeHouse) || ['Gemini', 'Sagittarius', 'Virgo', 'Aquarius'].includes(sign) || ['Mercury', 'Jupiter'].includes(leadPlanet)) factor *= 1.08;
  } else if (family === 'technology-networks') {
    if ([11].includes(routeHouse) || ['Aquarius', 'Gemini'].includes(sign) || leadPlanet === 'Mercury') factor *= 1.08;
    else factor *= 0.94;
  } else if (family === 'arts-aesthetics') {
    if ([5].includes(routeHouse) || ['Libra', 'Taurus', 'Leo'].includes(sign) || leadPlanet === 'Venus') factor *= 1.08;
  } else if (family === 'martial-technical') {
    if ([6, 8].includes(routeHouse) || ['Aries', 'Scorpio', 'Capricorn'].includes(sign) || leadPlanet === 'Mars') factor *= 1.05;
  } else if (family === 'finance-estates') {
    if ([2, 8].includes(routeHouse) || ['Taurus', 'Scorpio', 'Capricorn'].includes(sign)) factor *= 1.08;
  } else if (family === 'politics-networks') {
    if ([11].includes(routeHouse) || ['Aquarius', 'Leo'].includes(sign)) factor *= 1.1;
  }
  return factor;
}

function parseRulerHouseFromRoute(route) {
  if (typeof route !== 'string') return null;
  const patterns = [
    /ruler in H(\d{1,2})/i,
    /ruler in House (\d{1,2})/i,
    /ruler [A-Za-z]+ in House (\d{1,2})/i,
    /via .* in House (\d{1,2})/i,
    /in House (\d{1,2})/i,
    /Ruler of \d{1,2} in (\d{1,2})/i,
  ];
  let n = null;
  for (const pattern of patterns) {
    const m = route.match(pattern);
    if (m) {
      n = parseInt(m[1], 10);
      break;
    }
  }
  if (!n || Number.isNaN(n)) return null;
  if (n >= 1 && n <= 12) return n;
  return null;
}

export function buildProfessionSuggestions(h10, ctx = {}) {
  if (!h10) return [];
  const out = [];
  const h2 = ctx.h2 || null;
  const h6 = ctx.h6 || null;
  const h4 = ctx.h4 || null;
  const panel = h10?.basic_analysis?.determinators_panel || {};
  // Compute determinator shares to identify lead kind
  const shares = (() => {
    try {
      const list = Array.isArray(h10?.influences) ? h10.influences : [];
      let p=0,g=0,a=0; for (const it of list){ const v=Math.abs(Number(it?.value||0)); const t=String(it?.type||''); if (t==='occupation') p+=v; else if (t==='rulership'||t==='co_rulership') g+=v; else if (t==='aspect') a+=v; }
      const tot = p+g+a || 1; return { presence: p/tot, governance: g/tot, aspect: a/tot };
    } catch(_) { return { presence: 0, governance: 0, aspect: 0 }; }
  })();
  const leadKind = (shares.presence >= shares.governance && shares.presence >= shares.aspect)
    ? 'presence' : ((shares.governance >= shares.aspect) ? 'governance' : 'aspect');
  const leadPlanet = (() => {
    try {
      const arr = Array.isArray(panel?.[leadKind]) ? panel[leadKind] : [];
      return arr.length ? arr[0]?.planet : null;
    } catch(_) { return null; }
  })();
  const topAsp = (() => {
    try { const arr = Array.isArray(h10?.basic_analysis?.aspect_top) ? h10.basic_analysis.aspect_top : []; return arr.length ? arr[0] : null; } catch(_) { return null; }
  })();
  // Sign base
  const sign = h10?.sign;
  if (sign && SIGN_PROFESSIONS[sign]) {
    for (const s of SIGN_PROFESSIONS[sign]) out.push({ label: s, reason: `10th sign ${sign}`, weight: 1.0 });
  }
  // Determinators
  const det = h10?.basic_analysis?.determinators_panel || {};
  const detSets = [
    ...(Array.isArray(det?.presence) ? det.presence.map(x => ({ ...x, _kind: 'presence' })) : []),
    ...(Array.isArray(det?.governance) ? det.governance.map(x => ({ ...x, _kind: x?.type || 'governance' })) : []),
  ];
  // Determine a value scale across determinators to reflect relative strength (non-destructive)
  let maxDetVal = 0;
  for (const d of detSets) {
    const v = Number(d?.value || 0);
    if (v > maxDetVal) maxDetVal = v;
  }
  const valueFactor = (v) => {
    const vmax = maxDetVal || 1;
    const r = Math.max(0, Math.min(1, Number(v || 0) / vmax));
    // map [0..1] -> [0.95 .. 1.15] modestly accentuating stronger determinators
    return 0.95 + (r * 0.20);
  };
  // Track best base weight per determinator planet for curated combos
  const detBaseByPlanet = new Map();
  for (const d of detSets) {
    const p = d?.planet;
    if (!p || !PLANET_PROFESSIONS[p]) continue;
    const base = 1.2 * (DET_KIND_W[d?._kind] || 1.0) * (RANK_W[String(d?.rank || '')] || 0.5) * adverbFactor(d?.adverb) * valueFactor(d?.value);
    detBaseByPlanet.set(p, Math.max(detBaseByPlanet.get(p) || 0, base));
    for (const s of PLANET_PROFESSIONS[p]) out.push({ label: s, reason: `${p} ${d?._kind}`, weight: base });
  }
  // Ruler route
  const rmap = h10?.basic_analysis?.ruler_map || {};
  const route = rmap?.route || h10?.basic_analysis?.route_line || '';
  const rHouse = parseRulerHouseFromRoute(route);
  const legalContext = [7, 9].includes(rHouse) || ['Libra', 'Sagittarius'].includes(sign);
  if (rHouse && RULER_ROUTE_PROF[rHouse]) {
    const rWeight = 1.0 * rulerCondFactor(rmap?.conditions);
    for (const s of RULER_ROUTE_PROF[rHouse]) out.push({ label: s, reason: `ruler in H${rHouse}`, weight: rWeight });
  }
  // Curated route-based roles (more specific labels)
  if (rHouse) {
    const CURATED = {
      1: [{ l: 'autonomous practice', w: 1.05 }, { l: 'artisan proprietor', w: 1.02 }],
      2: [{ l: 'treasury/accountancy', w: 1.08 }, { l: 'bank oversight', w: 1.05 }],
      3: [{ l: 'dispatch/logistics', w: 1.05 }, { l: 'editorial/media', w: 1.02 }],
      4: [{ l: 'estate management', w: 1.06 }, { l: 'land surveyor', w: 1.06 }],
      5: [{ l: 'performing arts', w: 1.06 }, { l: 'youth education', w: 1.04 }],
      6: [{ l: 'operations management', w: 1.06 }, { l: 'clinical support', w: 1.04 }],
      7: [{ l: 'legal practice', w: 1.08 }, { l: 'public advocacy', w: 1.05 }],
      8: [{ l: 'forensic accounting', w: 1.08 }, { l: 'tax officer', w: 1.06 }],
      9: [{ l: 'professor', w: 1.08 }, { l: 'diplomat/clergy', w: 1.06 }],
      10: [{ l: 'public administrator', w: 1.06 }],
      11: [{ l: 'political organizer', w: 1.06 }, { l: 'association director', w: 1.05 }],
      12: [{ l: 'institutional administration', w: 1.06 }, { l: 'hospital roles', w: 1.04 }],
    };
    const pack = CURATED[rHouse] || [];
    const f = rulerCondFactor(rmap?.conditions) || 1.0;
    for (const it of pack) out.push({ label: it.l, reason: `ruler route H${rHouse}`, weight: it.w * f });
  }
  // Curated planet-based roles (more targeted chips)
  if (detBaseByPlanet.size) {
    const addP = (planet, label, w=1.0, extraReason='') => {
      if (!detBaseByPlanet.has(planet)) return;
      const base = detBaseByPlanet.get(planet) || 1.0;
      out.push({ label, reason: `curated: ${planet}${extraReason? ' · '+extraReason:''}`, weight: base * w });
    };
    addP('Mercury', 'printer/publisher', 0.95);
    addP('Mercury', 'records/registrar', 0.92);
    addP('Jupiter', 'professor', 1.04);
    addP('Saturn', 'civil engineer', 1.03);
    addP('Sun', 'senior administrator', 1.04);
    addP('Venus', 'perfumery/jewelry', 0.98);
    addP('Mars', 'fire service', 0.98);
    addP('Mars', 'orthopedic surgeon', 0.98);
    addP('Mars', 'military officer', 1.02);
    addP('Moon', 'quartermaster/provisioner', 1.0);
    addP('Moon', 'hospitality manager', 0.98);

    // Route + planet targeted lifts
    if (rHouse === 9) {
      if (detBaseByPlanet.has('Jupiter')) addP('Jupiter', 'judge/magistrate', 1.06, 'H9 route');
      if (detBaseByPlanet.has('Mercury')) addP('Mercury', 'publisher/editor', 1.08, 'H9 route');
      if (detBaseByPlanet.has('Jupiter')) addP('Jupiter', 'jurist/professor', 1.06, 'H9 route');
    } else if (rHouse === 7) {
      if (detBaseByPlanet.has('Sun')) addP('Sun', 'judiciary', 1.02, 'H7 route');
      if (detBaseByPlanet.has('Jupiter')) addP('Jupiter', 'judge/magistrate', 1.04, 'H7 route');
      if (detBaseByPlanet.has('Venus') || detBaseByPlanet.has('Mercury')) addP(detBaseByPlanet.has('Venus') ? 'Venus' : 'Mercury', 'notary', 1.04, 'H7 route');
      if (detBaseByPlanet.has('Venus')) addP('Venus', 'mediator', 1.02, 'H7 route');
    } else if (rHouse === 4) {
      if (detBaseByPlanet.has('Saturn')) addP('Saturn', 'land surveyor', 1.06, 'H4 route');
      if (detBaseByPlanet.has('Saturn')) addP('Saturn', 'architect', 1.05, 'H4 route');
    }
    if (!rHouse && legalContext) {
      if (detBaseByPlanet.has('Sun')) addP('Sun', 'judiciary', 0.98, 'legal sign');
      if (detBaseByPlanet.has('Jupiter')) addP('Jupiter', 'judge/magistrate', 1.0, 'legal sign');
    }
  }
  // ---- Boost roles by Lead (determinative planet) and MC Pressure (top aspect) ----
  const addBoostForPlanet = (planet, baseW, reason) => {
    if (!planet || !PLANET_PROFESSIONS[planet]) return;
    for (const s of PLANET_PROFESSIONS[planet]) out.push({ label: s, reason, weight: baseW });
  };
  if (leadPlanet) {
    addBoostForPlanet(leadPlanet, 1.06, `lead determinator (${leadKind})`);
  }
  if (topAsp && topAsp.planet) {
    // Use aspectFactor heuristics to scale pressure influence modestly
    const base = aspectFactor(topAsp) * 1.04;
    addBoostForPlanet(topAsp.planet, base, 'MC pressure');
  }
  // ---- Action Triplicity supporters (H6 and H2) & Opposite frame (H4) ----
  const occFactor = (state) => {
    try {
      const st = state || {};
      if (st.strong && st.dignified && !st.afflicted) return 1.05;
      if (st.afflicted) return 0.9;
      if (st.dignified) return 1.02;
      return 1.0;
    } catch { return 1.0; }
  };
  const addPack = (labelList, baseW, reason, state, suffix) => {
    const f = occFactor(state);
    for (const l of labelList) out.push({ label: suffix ? `${l} ${suffix}` : l, reason, weight: baseW * f });
  };
  // H6 (service/work environment) — secondary
  try {
    const loc = Array.isArray(h6?.basic_analysis?.location) ? h6.basic_analysis.location : [];
    if (loc.length) {
      const st = loc[0]?.state;
      addPack(['service','operations management','healthcare support','craft','management of subordinates','work with animals'], 0.96, 'H6 occupant (support)', st, '(H6 support)');
    }
  } catch(_) {}
  // H2 (income/resources) — secondary
  try {
    const loc = Array.isArray(h2?.basic_analysis?.location) ? h2.basic_analysis.location : [];
    if (loc.length) {
      const st = loc[0]?.state;
      addPack(['finance','banking','treasury','valuation','equipment/logistics'], 0.96, 'H2 occupant (support)', st, '(H2 support)');
    }
  } catch(_) {}
  // H4 (opposition) — background frame
  try {
    const loc = Array.isArray(h4?.basic_analysis?.location) ? h4.basic_analysis.location : [];
    if (loc.length) {
      const st = loc[0]?.state;
      addPack(['family business','home-based work','real estate/foundations'], 0.9, 'H4 occupant (background)', st, '(H4 background)');
    }
  } catch(_) {}
  // Aspect to MC
  const a = (h10?.aspect_top && h10.aspect_top[0]) || null;
  if (a && a.planet && PLANET_PROFESSIONS[a.planet]) {
    let base = 1.0 * aspectFactor(a);
    if (a.afflicting && MALE.has(a.planet)) base *= 0.7; // de-prioritize
    if (!a.afflicting && BENE.has(a.planet)) base *= 1.15; // prioritize
    for (const s of PLANET_PROFESSIONS[a.planet]) out.push({ label: s, reason: `${a.planet} to MC cusp`, weight: base });
  }
  // Merge by label, keep higher weight, sort and threshold
  const merged = uniqByLabel(out)
    .map((item) => {
      const adjusted = Number(item.weight || 0)
        * suggestionReasonPriority(item.reason)
        * professionContextFactor(item.label, {
          sign,
          routeHouse: rHouse,
          leadPlanet,
        });
      return { ...item, adjustedWeight: adjusted, family: professionFamily(item.label) };
    })
    .sort((a,b)=> (Number(b.adjustedWeight||0) - Number(a.adjustedWeight||0)) || (Number(b.weight||0) - Number(a.weight||0)) || String(a.label).localeCompare(String(b.label)));
  const filtered = merged.filter(x => Number(x.weight||0) >= 0.6);
  const top = [];
  const usedFamilies = new Set();
  for (const item of filtered) {
    if (top.length >= 8) break;
    if (usedFamilies.has(item.family)) continue;
    top.push(item);
    usedFamilies.add(item.family);
  }
  for (const item of filtered) {
    if (top.length >= 8) break;
    if (top.some((existing) => existing.label === item.label)) continue;
    top.push(item);
  }
  const bestRoute = filtered.find(isRouteSuggestion);
  if (bestRoute && !top.some(isRouteSuggestion)) {
    const replaceAt = Math.max(0, top.length - 1);
    top.splice(replaceAt, top.length ? 1 : 0, bestRoute);
    top.sort((a,b)=> (Number(b.adjustedWeight||0) - Number(a.adjustedWeight||0)) || (Number(b.weight||0) - Number(a.weight||0)) || String(a.label).localeCompare(String(b.label)));
  }
  return top.map(({ adjustedWeight, family, ...rest }) => rest);
}

export function buildHealthSuggestions(h1, h6, h12, opts = {}) {
  const out = [];
  const morinStrict = !!opts.morinStrict;
  const pushSign = (sign, scope, weight) => {
    if (sign && SIGN_HEALTH[sign]) {
      for (const s of SIGN_HEALTH[sign]) out.push({ label: `${s}`, reason: `${scope} sign ${sign}`, weight });
    }
  };
  const pushPlanet = (planet, scope, base) => {
    if (planet && PLANET_HEALTH[planet]) {
      for (const s of PLANET_HEALTH[planet]) out.push({ label: `${s}`, reason: `${planet} ${scope}`, weight: base });
    }
  };
  if (h1) pushSign(h1?.sign, 'ASC', 1.0);
  if (morinStrict) {
    if (h12) pushSign(h12?.sign, 'H12', 1.0);
  } else {
    if (h6) pushSign(h6?.sign, 'H6', 1.0);
  }
  const det1 = h1?.basic_analysis?.determinators_panel || {};
  const detAux = (morinStrict ? (h12?.basic_analysis?.determinators_panel || {}) : (h6?.basic_analysis?.determinators_panel || {}));
  const dets = [
    ...(Array.isArray(det1?.presence) ? det1.presence.map(x => ({ ...x, _scope: 'ASC', _kind: 'presence' })) : []),
    ...(Array.isArray(det1?.governance) ? det1.governance.map(x => ({ ...x, _scope: 'ASC', _kind: x?.type || 'governance' })) : []),
    ...(Array.isArray(detAux?.presence) ? detAux.presence.map(x => ({ ...x, _scope: morinStrict ? 'H12' : 'H6', _kind: 'presence' })) : []),
    ...(Array.isArray(detAux?.governance) ? detAux.governance.map(x => ({ ...x, _scope: morinStrict ? 'H12' : 'H6', _kind: x?.type || 'governance' })) : []),
  ];
  for (const d of dets) {
    const p = d?.planet;
    if (!p || !PLANET_HEALTH[p]) continue;
    const base = 1.0 * (DET_KIND_W[d?._kind] || 1.0) * (RANK_W[String(d?.rank || '')] || 0.5) * adverbFactor(d?.adverb);
    for (const s of PLANET_HEALTH[p]) out.push({ label: `${s}`, reason: `${p} ${d?._kind} (${d?._scope})`, weight: base });
  }
  // Aspects to ASC/H6 cusp
  const a1 = (h1?.aspect_top && h1.aspect_top[0]) || null;
  const aAux = (morinStrict ? ((h12?.aspect_top && h12.aspect_top[0]) || null) : ((h6?.aspect_top && h6.aspect_top[0]) || null));
  if (a1 && a1.planet) {
    let base = 1.0 * aspectFactor(a1);
    if (a1.afflicting && MALE.has(a1.planet)) base *= 1.15; // emphasize risk topics
    if (!a1.afflicting && BENE.has(a1.planet)) base *= 1.0; // neutral bump handled by aspectFactor
    pushPlanet(a1.planet, 'to ASC cusp', base);
  }
  if (aAux && aAux.planet) {
    let base = 1.0 * aspectFactor(aAux);
    if (aAux.afflicting && MALE.has(aAux.planet)) base *= 1.2; // elevate illness risks
    if (!aAux.afflicting && BENE.has(aAux.planet)) base *= 0.9; // mitigating
    pushPlanet(aAux.planet, morinStrict ? 'to H12 cusp' : 'to H6 cusp', base);
  }
  // Curated Morin route-based health patterns (pattern-level hints)
  const targetH = morinStrict ? h12 : h6;
  try {
    const r = targetH?.basic_analysis?.ruler_map?.route || '';
    const rHouse = parseRulerHouseFromRoute(r);
    const add = (label, w) => out.push({ label, reason: `ruler route H${rHouse}`, weight: w });
    if (rHouse === 1) {
      add('constitutional weakness', 1.10);
      add('chronic baseline', 1.02);
    } else if (rHouse === 6) {
      add('work‑related triggers', 1.06);
      add('service strain', 1.02);
    } else if (rHouse === 8) {
      add('serious/critical risk', 1.10);
      add('elimination/reproductive', 1.06);
    } else if (rHouse === 12) {
      add('institutional care context', 1.06);
      add('hidden/confinement', 1.02);
    }
  } catch (_) {}
  // Merge/sort/threshold
  const merged = uniqByLabel(out).sort((a,b)=> (Number(b.weight||0) - Number(a.weight||0)) || String(a.label).localeCompare(String(b.label)));
  return merged.filter(x => Number(x.weight||0) >= 0.6).slice(0, 8);
}
