export function normalizeForensicAspectLabel(value) {
  if (value == null) return null;

  let label = '';
  if (typeof value === 'string') {
    label = value;
  } else if (typeof value === 'object') {
    const type = String(value?.type || '').trim().toLowerCase();
    if (!type) return null;
    label = `${type}${value?.applying ? ' (app)' : ''}`;
  } else {
    label = String(value);
  }

  label = label.replace(/\s+/g, ' ').replace(/\s*,+\s*$/g, '').trim();
  if (!label || label === '-') return null;
  return label;
}

export function dedupeForensicAspectLabels(values) {
  const seen = new Set();
  const out = [];
  for (const value of values || []) {
    const label = normalizeForensicAspectLabel(value);
    if (!label) continue;
    if (seen.has(label)) continue;
    seen.add(label);
    out.push(label);
  }
  return out;
}

export function formatForensicAspectLabels(values, { empty = 'none' } = {}) {
  const labels = dedupeForensicAspectLabels(values);
  return labels.length ? labels.join(', ') : empty;
}

