const ROLE_META = {
  H1_ruler: {
    legendLabel: '1st ruler | victim',
    sourceLabel: '1st ruler (victim)',
    compactLabel: 'Victim pivot',
    style: { color: '#0ea5e9', weight: 3, dashArray: null, opacity: 0.95 },
  },
  H4_from_7_ruler: {
    legendLabel: '4th from 7th | perpetrator base',
    sourceLabel: '4th from 7th ruler (perpetrator base)',
    compactLabel: 'Perpetrator base',
    style: { color: '#fb7185', weight: 3, dashArray: null, opacity: 0.95 },
  },
  Moon: {
    legendLabel: 'Moon | movement',
    sourceLabel: 'Moon (movement)',
    compactLabel: 'Moon movement',
    style: { color: '#f59e0b', weight: 2, dashArray: '6 4', opacity: 0.9 },
  },
  H3_ruler: {
    legendLabel: '3rd ruler | local route and vehicle',
    sourceLabel: '3rd ruler (local route and vehicle)',
    compactLabel: 'Local route and vehicle',
    style: { color: '#10b981', weight: 2, dashArray: '1 4', opacity: 0.9 },
  },
  H8_ruler: {
    legendLabel: '8th ruler | harm',
    sourceLabel: '8th ruler (harm)',
    compactLabel: 'Harm',
    style: { color: '#94a3b8', weight: 1.5, dashArray: '10 6', opacity: 0.65 },
  },
  H9_ruler: {
    legendLabel: '9th ruler | abductor route and distance',
    sourceLabel: '9th ruler (abductor route and distance)',
    compactLabel: 'Abductor route and distance',
    style: { color: '#7c3aed', weight: 2, dashArray: '10 6', opacity: 0.9 },
  },
  H12_ruler: {
    legendLabel: '12th ruler | hidden or confinement',
    sourceLabel: '12th ruler (hidden or confinement)',
    compactLabel: 'Hidden or confinement',
    style: { color: '#0f766e', weight: 2, dashArray: '2 6', opacity: 0.9 },
  },
  H7_ruler: {
    legendLabel: '7th ruler | perpetrator',
    sourceLabel: '7th ruler (perpetrator)',
    compactLabel: 'Perpetrator',
    style: { color: '#6366f1', weight: 2, dashArray: '8 6', opacity: 0.9 },
  },
};

const DEFAULT_ROLE_META = {
  legendLabel: 'Bearing source',
  sourceLabel: 'Bearing source',
  compactLabel: 'Bearing source',
  style: { color: '#64748b', weight: 2, dashArray: '4 4', opacity: 0.8 },
};

const LEGEND_ROLE_ORDER = ['H1_ruler', 'H7_ruler', 'Moon', 'H3_ruler', 'H9_ruler', 'H12_ruler'];
const ROLE_PRIORITY = [...LEGEND_ROLE_ORDER, 'H8_ruler', 'H4_from_7_ruler'];

export function getAbductionRoleMeta(role) {
  return ROLE_META[String(role || '')] || DEFAULT_ROLE_META;
}

export function getAbductionRoleLabel(role, variant = 'sourceLabel') {
  const meta = getAbductionRoleMeta(role);
  return meta[variant] || meta.sourceLabel;
}

export function getAbductionRoleStyle(role) {
  return getAbductionRoleMeta(role).style;
}

export function getAbductionLegendEntries() {
  return LEGEND_ROLE_ORDER.map((role) => ({ role, ...getAbductionRoleMeta(role) }));
}

export function normalizeCoordinateInput(value = '') {
  return String(value || '').trim().replace(/[\u2212\u2010\u2011\u2012\u2013\u2014\u2015]/g, '-');
}

function getRolePriority(role) {
  const idx = ROLE_PRIORITY.indexOf(String(role || ''));
  return idx === -1 ? ROLE_PRIORITY.length : idx;
}

function mergeDuplicateBearings(bearings = []) {
  const grouped = new Map();
  for (const bearing of bearings) {
    if (!bearing) continue;
    const az = Number(bearing?.azimuth_deg);
    if (!Number.isFinite(az)) continue;
    const alt = Number(bearing?.altitude_deg);
    const planet = String(bearing?.planet || '').trim();
    const key = `${planet}|${az.toFixed(4)}|${Number.isFinite(alt) ? alt.toFixed(4) : ''}`;
    const existing = grouped.get(key);
    if (!existing) {
      grouped.set(key, { ...bearing, role_aliases: [] });
      continue;
    }
    const mergedRoles = Array.from(
      new Set([
        existing.role,
        ...(Array.isArray(existing.role_aliases) ? existing.role_aliases : []),
        bearing.role,
      ].filter(Boolean)),
    ).sort((a, b) => getRolePriority(a) - getRolePriority(b));
    existing.role = mergedRoles[0] || existing.role;
    existing.role_aliases = mergedRoles.slice(1);
  }
  return Array.from(grouped.values()).sort((a, b) => getRolePriority(a?.role) - getRolePriority(b?.role));
}

export function buildProcessedAbductionBearings(bearings = [], firstRulerName = null) {
  const source = Array.isArray(bearings) ? bearings.filter(Boolean) : [];
  const hasH1Role = source.some((bearing) => bearing?.role === 'H1_ruler');
  const h1ByPlanet = firstRulerName
    ? source.find((bearing) => String(bearing?.planet) === String(firstRulerName))
    : null;
  const h1Candidate = hasH1Role
    ? source.find((bearing) => bearing?.role === 'H1_ruler')
    : (h1ByPlanet ? { ...h1ByPlanet, role: 'H1_ruler' } : null);

  const out = [];
  let inserted = false;

  for (const bearing of source) {
    if (bearing?.role === 'H7_planet') {
      if (!inserted && h1Candidate && !out.some((item) => item?.role === 'H1_ruler')) {
        out.push(h1Candidate);
        inserted = true;
      }
      continue;
    }
    out.push(bearing);
  }

  const existingIdx = out.findIndex((item) => item?.role === 'H1_ruler');
  if (existingIdx === -1) {
    if (h1Candidate) out.unshift(h1Candidate);
  } else if (existingIdx >= 6) {
    const [h1] = out.splice(existingIdx, 1);
    out.unshift(h1);
  }

  return mergeDuplicateBearings(out);
}

export function formatAbductionBearingRoleLabel(bearing, variant = 'sourceLabel') {
  const primary = getAbductionRoleLabel(bearing?.role, variant);
  const aliases = (Array.isArray(bearing?.role_aliases) ? bearing.role_aliases : [])
    .map((role) => getAbductionRoleLabel(role, variant))
    .filter(Boolean);
  return aliases.length ? `${primary} + ${aliases.join(' + ')}` : primary;
}
