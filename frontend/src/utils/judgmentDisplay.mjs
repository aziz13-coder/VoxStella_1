function normalizeCategoryValue(raw) {
  if (typeof raw !== 'string') return '';
  return raw.trim().toLowerCase().replace(/_/g, ' ');
}

export function deriveJudgmentCategory(source, fallback = '') {
  const candidates = [
    source?.question_analysis?.question_type,
    source?.category,
    Array.isArray(source?.tags) ? source.tags[0] : source?.tags,
    fallback,
  ];

  for (const candidate of candidates) {
    const normalized = normalizeCategoryValue(candidate);
    if (normalized) return normalized;
  }

  return '';
}

export function getJudgmentDisplayLabel(source, judgmentOverride = null) {
  const judgment =
    typeof judgmentOverride === 'string' && judgmentOverride.trim()
      ? judgmentOverride.trim()
      : typeof source?.judgment === 'string' && source.judgment.trim()
        ? source.judgment.trim()
        : typeof source?.verdict?.label === 'string' && source.verdict.label.trim()
          ? source.verdict.label.trim()
          : 'UNCLEAR';

  const category = deriveJudgmentCategory(source);

  if (category === 'lost object') {
    if (judgment === 'YES') return 'RECOVERABLE';
    if (judgment === 'NO') return 'NOT RECOVERABLE';
  }

  return judgment;
}
