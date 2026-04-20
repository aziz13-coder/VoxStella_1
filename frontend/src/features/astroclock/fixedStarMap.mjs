// Fixed star knowledge map (frontend helper)
// Morin-consistent use: corroborative hints only; no scoring or house influence changes

const STAR_PROFESSIONS = {
  Regulus: ['leadership', 'honors', 'high office'],
  Spica: ['artistry', 'craft', 'scholarship'],
  Aldebaran: ['command', 'military', 'high post'],
  Antares: ['risk operations', 'conflict roles'],
  Fomalhaut: ['spiritual arts', 'visionary work'],
  Algol: ['crisis roles', 'risk management'],
  Sirius: ['prominence', 'public success'],
  Arcturus: ['innovation', 'pioneering'],
  Vega: ['music', 'performance', 'art'],
  Betelgeuse: ['executive action', 'martial arts'],
  Pollux: ['athletics', 'combative sports'],
  Procyon: ['fast‑rise roles', 'messengers'],
  Denebola: ['non‑conformist roles'],
  Capella: ['craft', 'engineering'],
  Altair: ['bold command', 'aeronautics'],
  Bellatrix: ['strategy', 'martial planning'],
  Castor: ['writing', 'performing'],
  Canopus: ['navigation', 'leadership at sea'],
  Deneb: ['creative arts'],
  Zosma: ['service', 'support roles'],
  Rigel: ['command', 'engineering', 'operations'],
  Rasalhague: ['healing arts', 'medical research'],
  Rasalgethi: ['strategy', 'administration'],
  Alphard: ['logistics', 'waterways', 'trade'],
  Vindemiatrix: ['accounting', 'record‑keeping', 'analysis'],
  'Zuben Elgenubi': ['law', 'arbitration'],
  'Zuben Elschemali': ['diplomacy', 'policy'],
  'Deneb Kaitos': ['navigation', 'maritime'],
  Alkaid: ['security', 'defense'],
  Alnilam: ['theatre', 'performance'],
  Alrescha: ['communications', 'editing'],
  'Deneb Algedi': ['administration', 'regulation'],
};

const STAR_HEALTH = {
  Regulus: ['heart/circulation'],
  Spica: ['nervous assimilation'],
  Aldebaran: ['eyes/face'],
  Antares: ['heart/lungs strain'],
  Fomalhaut: ['susceptibility/fluids'],
  Algol: ['head injuries', 'fevers'],
  Sirius: ['fevers/heat'],
  Arcturus: ['legs/circulation tone'],
  Vega: ['eyes/nerves'],
  Betelgeuse: ['shoulders/arms strain'],
  Pollux: ['hands/arms'],
  Procyon: ['nervous excitability'],
  Denebola: ['spine/strain'],
  Capella: ['shoulders'],
  Altair: ['respiration'],
  Bellatrix: ['injury risk'],
  Castor: ['nervous system'],
  Canopus: ['digestion/fluids'],
  Deneb: ['sleep/dream tone'],
  Zosma: ['lower back'],
  Rigel: ['feet/legs fatigue'],
  Rasalhague: ['detox/poisons sensitivity'],
  Rasalgethi: ['shoulders', 'tendons'],
  Alphard: ['stomach/fluids'],
  Vindemiatrix: ['nervous strain'],
  'Zuben Elgenubi': ['kidneys'],
  'Zuben Elschemali': ['kidneys/renal tone'],
  'Deneb Kaitos': ['feet', 'circulation'],
  Alkaid: ['back/neck strain'],
  Alnilam: ['respiration'],
  Alrescha: ['nervous system'],
  'Deneb Algedi': ['knees/bones'],
};

function weightByTarget(hit, forTopic) {
  // Morin-consistent: angles > luminaries; use lower weight for corroboration
  const t = String(hit?.target || '');
  const tt = String(hit?.target_type || '');
  let w = 0.9;
  if (tt === 'cusp') {
    if (forTopic === 'profession' && (t === 'C10')) w = 1.05;
    else if (forTopic === 'health' && (t === 'C1' || t === 'C6')) w = 1.0;
    else w = 0.85;
  } else if (tt === 'planet') {
    if (t === 'Sun') w = 0.9;
    else if (t === 'Moon') w = 0.85;
    else w = 0.8;
  }
  // tighter orb increases influence slightly
  const orb = Number(hit?.orb_deg || 1.0);
  const orbF = Math.max(0.85, Math.min(1.1, 1.05 - (orb * 0.05)));
  return w * orbF;
}

function uniqByLabel(items) {
  const acc = new Map();
  for (const it of items) {
    const key = it?.label || JSON.stringify(it);
    if (!acc.has(key)) acc.set(key, it);
    else {
      const cur = acc.get(key);
      if (Number(it.weight || 0) > Number(cur.weight || 0)) acc.set(key, it);
    }
  }
  return Array.from(acc.values());
}

export function buildFixedStarProfessionSuggestions(fixedStarHits = []) {
  const out = [];
  for (const h of (Array.isArray(fixedStarHits) ? fixedStarHits : [])) {
    const name = String(h?.name || '');
    const packs = STAR_PROFESSIONS[name];
    if (!packs) continue;
    const w = weightByTarget(h, 'profession');
    const reason = `${name} with ${h?.target_type === 'cusp' ? (h.target || '') : h.target}`;
    for (const label of packs) out.push({ label, reason, weight: w });
  }
  return uniqByLabel(out)
    .filter(x => Number(x.weight || 0) >= 0.75)
    .sort((a,b)=> (Number(b.weight||0) - Number(a.weight||0)) || String(a.label).localeCompare(String(b.label)))
    .slice(0, 6);
}

export function buildFixedStarHealthSuggestions(fixedStarHits = []) {
  const out = [];
  for (const h of (Array.isArray(fixedStarHits) ? fixedStarHits : [])) {
    const name = String(h?.name || '');
    const packs = STAR_HEALTH[name];
    if (!packs) continue;
    const w = weightByTarget(h, 'health');
    const reason = `${name} with ${h?.target_type === 'cusp' ? (h.target || '') : h.target}`;
    for (const label of packs) out.push({ label, reason, weight: w });
  }
  return uniqByLabel(out)
    .filter(x => Number(x.weight || 0) >= 0.75)
    .sort((a,b)=> (Number(b.weight||0) - Number(a.weight||0)) || String(a.label).localeCompare(String(b.label)))
    .slice(0, 6);
}
