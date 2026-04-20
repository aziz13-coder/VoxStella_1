import { getJudgmentDisplayLabel } from './judgmentDisplay.mjs';
import { buildChartReplayContext } from './horaryReplay.mjs';

export function normalizeAspectData(chartData) {
  if (!chartData || !Array.isArray(chartData.aspects)) return chartData;

  return {
    ...chartData,
    aspects: chartData.aspects.map((aspect) => ({
      ...aspect,
      applying: Boolean(aspect?.applying),
    })),
  };
}

export function deriveCategoryTag(result, fallback = 'general') {
  const raw = result?.question_analysis?.question_type;
  if (typeof raw !== 'string' || !raw.trim()) return fallback;
  return raw.toLowerCase().replace(/_/g, ' ');
}

export function deriveOutcomeFromJudgment(judgment) {
  if (judgment === 'YES') return 'positive';
  if (judgment === 'NO') return 'negative';
  return 'uncertain';
}

export function computeFallbackConfidence(result, existingChart = null) {
  if (typeof result?.confidence === 'number' && Number.isFinite(result.confidence)) {
    return result.confidence;
  }

  try {
    if (result?.confidence_breakdown?.final_confidence != null) {
      return Math.round(result.confidence_breakdown.final_confidence);
    }

    const trace = Array.isArray(result?.scoring_trace) ? result.scoring_trace : [];
    if (trace.length > 0) {
      const total = trace.reduce((sum, item) => sum + (Number(item?.weight) || 0), 0);
      const sigmoid = (x) => 100 / (1 + Math.exp(-x));
      return Math.round(sigmoid(total));
    }
  } catch {}

  if (typeof existingChart?.confidence === 'number' && Number.isFinite(existingChart.confidence)) {
    return existingChart.confidence;
  }

  return 0;
}

export function normalizeHoraryApiResult(
  result,
  {
    existingChart = null,
    id = Date.now(),
    timestamp = new Date(),
    fallbackTag = 'general',
    requestContext = null,
  } = {},
) {
  const judgment =
    typeof result?.judgment === 'string' && result.judgment.trim()
      ? result.judgment
      : existingChart?.judgment || 'UNCLEAR';

  const category = deriveCategoryTag(
    result,
    existingChart?.tags?.[0] || fallbackTag,
  );

  const replayContext = requestContext
    ? buildChartReplayContext(requestContext, result)
    : existingChart?.replay_context || null;

  return {
    ...(existingChart || {}),
    ...result,
    judgment,
    judgment_display: getJudgmentDisplayLabel(
      {
        ...(existingChart || {}),
        ...result,
        judgment,
        category,
        tags: [category],
      },
      judgment,
    ),
    chart_data: normalizeAspectData(result?.chart_data),
    confidence: computeFallbackConfidence(result, existingChart),
    confidence_breakdown: result?.confidence_breakdown || null,
    scoring_trace: result?.scoring_trace || null,
    id: existingChart?.id ?? id,
    timestamp,
    tags: [category],
    outcome: deriveOutcomeFromJudgment(judgment),
    ...(replayContext ? { replay_context: replayContext } : {}),
  };
}
