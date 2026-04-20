function compactWhitespace(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function readObjectText(value) {
  if (!value || typeof value !== 'object') return '';
  const keys = ['query', 'label', 'name', 'display_name', 'address'];
  for (const key of keys) {
    const candidate = value?.[key];
    if (typeof candidate === 'string' && candidate.trim()) {
      return compactWhitespace(candidate);
    }
  }
  return '';
}

export function normalizeAstrocartographyTargetText(value) {
  const text = typeof value === 'string'
    ? compactWhitespace(value)
    : readObjectText(value);
  if (!text) return '';
  if (text === '[object Object]') return '';
  if (text.startsWith('[object Object],')) {
    return compactWhitespace(text.replace(/^\[object Object\],\s*/u, ''));
  }
  return text;
}

export function resolveAstrocartographyTargetQuery(queryOverride, fallbackValue = '') {
  return (
    normalizeAstrocartographyTargetText(queryOverride)
    || normalizeAstrocartographyTargetText(fallbackValue)
  );
}

export function getAstrocartographyTargetQuery(target) {
  if (!target) return '';
  if (typeof target === 'string') return normalizeAstrocartographyTargetText(target);
  return (
    normalizeAstrocartographyTargetText(target?.query)
    || normalizeAstrocartographyTargetText(target?.label)
    || normalizeAstrocartographyTargetText(target?.name)
  );
}

export function getAstrocartographyTargetLabel(target) {
  if (!target) return '';
  if (typeof target === 'string') return normalizeAstrocartographyTargetText(target);
  return (
    normalizeAstrocartographyTargetText(target?.label)
    || normalizeAstrocartographyTargetText(target?.query)
    || normalizeAstrocartographyTargetText(target?.name)
  );
}
