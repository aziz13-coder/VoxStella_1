import { deriveForensicReplayAxes } from './forensicReplayAxes.mjs';

function baseSurvivalLevel(total, dangerScore) {
  if (total <= -3) return 'Lower';
  if (dangerScore >= 3.0) return 'Lower';
  if (dangerScore >= 1.5 && total <= 2) return 'Lower';
  if (total >= 3 && dangerScore < 1.2) return 'Higher';
  return 'Moderate';
}

function summarizeLegacyForensicSurvivalSignal({
  total = 0,
  dangerScore = 0,
  forensicResult = {},
} = {}) {
  const axes = new Set(deriveForensicReplayAxes(forensicResult));
  const findings = Array.isArray(forensicResult?.findings) ? forensicResult.findings : [];
  const titles = findings
    .map((finding) => String(finding?.title || '').toLowerCase())
    .filter(Boolean);

  const strongFatalFinding = titles.some((title) =>
    title.includes('life/death overlap') ||
    title.includes('violence or homicide') ||
    title.includes('also rules the 8th') ||
    title.includes('malefic contrary to sect') ||
    title.includes('violent fixed star')
  );

  const fatalOverride =
    (axes.has('violence_homicide') && strongFatalFinding) ||
    (axes.has('accident_or_disaster') && titles.some((title) =>
      title.includes('life/death') ||
      title.includes('catastrophic') ||
      title.includes('drowning')
    ));

  const baseLevel = baseSurvivalLevel(total, dangerScore);
  const level = fatalOverride ? 'Lower' : baseLevel;
  const note = fatalOverride
    ? 'Strong fatal route findings override the base dignity-only vitality heuristic.'
    : 'Derived from victim-significator dignity, house condition, and malefic pressure.';

  return {
    level,
    baseLevel,
    fatalOverride,
    note,
    score: null,
    outcomeBand: null,
    breakdown: null,
    evidence: null,
  };
}

export function summarizeForensicSurvivalSignal({
  total = 0,
  dangerScore = 0,
  forensicResult = {},
} = {}) {
  const serverSummary = forensicResult?.survivability;
  if (serverSummary && typeof serverSummary === 'object' && serverSummary.level) {
    return {
      level: String(serverSummary.level),
      baseLevel: String(serverSummary.level),
      fatalOverride: Number(serverSummary?.breakdown?.fatal_pressure || 0) >= 4.5,
      note: String(serverSummary.note || ''),
      score: serverSummary.score ?? null,
      outcomeBand: serverSummary.outcome_band || null,
      breakdown: serverSummary.breakdown || null,
      evidence: serverSummary.evidence || null,
      victimSignificators: Array.isArray(serverSummary.victim_significators)
        ? serverSummary.victim_significators
        : [],
      caseType: serverSummary.case_type || null,
    };
  }

  return summarizeLegacyForensicSurvivalSignal({
    total,
    dangerScore,
    forensicResult,
  });
}
