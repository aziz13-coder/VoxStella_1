import { cleanMoonText } from './cleanMoonText';
import { getChartSourceInstant } from './chartTime.mjs';

import { getJudgmentDisplayLabel } from './judgmentDisplay.mjs';

export function buildChartPayload(chart, includeVerdict = true, forAI = false) {
  const chartData = chart?.chart_data || {};
  const utcTime = chartData?.timezone_info?.utc_time;
  const timezone = chartData?.timezone_info?.timezone || 'UTC';
  const instant = getChartSourceInstant(chart) || (utcTime ? new Date(utcTime) : new Date(chart.timestamp));
  const asked_at_utc = instant.toISOString();
  const asked_at_local = instant.toLocaleString('en-US', { timeZone: timezone });
  const exportedCategory = chart.tags?.[0] || chart.category || 'general';
  const houseRulers = chartData.house_rulers || chartData.rulers || {};
  const considerations = chartData.considerations || chart.considerations || null;
  const moonLastAspect = chartData.moon_last_aspect || null;
  const moonNextAspect = chartData.moon_next_aspect || null;

  const getLocationData = () => {
    if (chartData?.location?.city && chartData?.location?.city !== 'Unknown') {
      return {
        city: chartData.location.city,
        country: chartData.location.country || 'Unknown',
        lat: chartData.location.latitude || chartData.location.lat || 0,
        lon: chartData.location.longitude || chartData.location.lon || 0
      };
    }

    if (chartData?.timezone_info?.location && typeof chartData.timezone_info.location === 'object') {
      const loc = chartData.timezone_info.location;
      return {
        city: loc.city || loc.name || 'Unknown',
        country: loc.country || 'Unknown',
        lat: loc.latitude || loc.lat || 0,
        lon: loc.longitude || loc.lon || 0
      };
    }

    if (chartData?.timezone_info?.location_name &&
        chartData.timezone_info.location_name !== 'Unknown location' &&
        chartData.timezone_info.location_name !== 'Unknown') {
      const locationStr = chartData.timezone_info.location_name;
      const parts = locationStr.split(',').map(s => s.trim());
      return {
        city: parts[0] || locationStr,
        country: parts[1] || 'Unknown',
        lat: chartData.timezone_info?.coordinates?.latitude || 0,
        lon: chartData.timezone_info?.coordinates?.longitude || 0
      };
    }

    if (chart.location_name && chart.location_name !== 'Unknown location' && chart.location_name !== 'Unknown') {
      const locationStr = chart.location_name;
      const parts = locationStr.split(',').map(s => s.trim());
      return {
        city: parts[0] || locationStr,
        country: parts[1] || 'Unknown',
        lat: chartData?.timezone_info?.coordinates?.latitude || 0,
        lon: chartData?.timezone_info?.coordinates?.longitude || 0
      };
    }

    if (chart.location && typeof chart.location === 'object') {
      return {
        city: chart.location.city || 'Unknown',
        country: chart.location.country || 'Unknown',
        lat: chart.location.latitude || chart.location.lat || 0,
        lon: chart.location.longitude || chart.location.lon || 0
      };
    }

    if (typeof chart.location === 'string' && chart.location !== 'Unknown') {
      const parts = chart.location.split(',').map(s => s.trim());
      return {
        city: parts[0] || chart.location,
        country: parts[1] || 'Unknown',
        lat: 0,
        lon: 0
      };
    }

    const tz = chartData?.timezone_info?.timezone;
    if (tz && tz !== 'UTC' && tz.includes('/')) {
      const parts = tz.split('/');
      const city = parts[parts.length - 1].replace(/_/g, ' ');
      return {
        city,
        country: parts[0] || 'Unknown',
        lat: 0,
        lon: 0
      };
    }

    return {
      city: 'Unknown',
      country: 'Unknown',
      lat: 0,
      lon: 0
    };
  };

  // Prefer the engine's structured reasoning; fall back to legacy rationale
  const engineReasoning = Array.isArray(chart.reasoning)
    ? chart.reasoning
    : (chart.rationale || []);
  // Keep evaluation/auxiliary ledger separate so exports don't replace reasoning
  const ledgerEntries = chart.ledger || null;

  // Process traditional_factors to remove time_to_perfection when perfection_within_sign is false
  let processedTraditionalFactors = chart.traditional_factors || {};
  if (forAI && processedTraditionalFactors.time_to_perfection && processedTraditionalFactors.perfection_within_sign === false) {
    processedTraditionalFactors = { ...processedTraditionalFactors };
    delete processedTraditionalFactors.time_to_perfection;
  }

  const payload = {
    id: chart.id,
    question: chart.question,
    category: exportedCategory,
    asked_at_local,
    asked_at_utc,
    tz: timezone,
    location: getLocationData(),
    house_system: 'Regiomontanus',
    houses: chartData?.houses || {},
    rulers: houseRulers,
    house_rulers: houseRulers,
    ascendant: chartData?.ascendant ?? null,
    midheaven: chartData?.midheaven ?? null,
    aspects: chartData?.aspects || [],
    planets: chartData?.planets || {},
    traditional_factors: processedTraditionalFactors,
    solar_factors: chart.solar_factors || {},
    ...(considerations && typeof considerations === 'object' ? { considerations } : {}),
    ...(moonLastAspect ? { moon_last_aspect: moonLastAspect } : {}),
    ...(moonNextAspect ? { moon_next_aspect: moonNextAspect } : {}),
    // Only include reasoning if not for AI analysis
    ...(forAI ? {} : { reasoning: engineReasoning }),
    // Include evaluation diagnostics when present (but not for AI analysis)
    ...(forAI ? {} : (chart.scoring_trace ? { scoring_trace: chart.scoring_trace } : {})),
    ...(chart.confidence_breakdown ? { confidence_breakdown: chart.confidence_breakdown } : {}),
    ...(chart.lost_object_location ? { lost_object_location: chart.lost_object_location } : {}),
  };

  // Preserve the auxiliary/evaluation ledger separately for auditability
  if (ledgerEntries) payload.ledger = ledgerEntries;

  if (includeVerdict) {
    const keyTestimonies = (engineReasoning || [])
      ?.filter(r => {
        // CRITICAL FIX: Handle both string and object reasoning entries
        const reasonText = typeof r === 'string' ? r : (r?.rule || r?.key || String(r));
        return typeof reasonText === 'string' && (
          reasonText.includes('perfection') || 
          reasonText.includes('reception') || 
          reasonText.includes('Moon') || 
          reasonText.includes('dignity') || 
          reasonText.includes('applying')
        );
      })
      ?.slice(0, 5)
      ?.map(r => {
        // CRITICAL FIX: Safely extract text from reasoning entries
        const reasonText = typeof r === 'string' ? r : (r?.rule || r?.key || String(r));
        return `• ${cleanMoonText(reasonText)}`;
      }) || [];

    payload.verdict = {
      label: getJudgmentDisplayLabel(chart),
      code: chart.judgment,
      confidence: chart.confidence,
      // Provide readable rationale derived from structured reasoning
      rationale: engineReasoning.map(r => {
        // CRITICAL FIX: Safely extract text from reasoning entries
        const reasonText = typeof r === 'string' ? r : (r?.rule || r?.key || String(r));
        return cleanMoonText(reasonText);
      })
    };
    payload.key_testimonies = keyTestimonies;
    payload.keyTestimoniesText = keyTestimonies.join('\n');
  }

  return payload;
}
