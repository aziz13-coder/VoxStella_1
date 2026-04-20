export function hydrateStoredCharts(rawCharts) {
  if (!Array.isArray(rawCharts)) return [];

  const hydrated = [];
  for (const chart of rawCharts) {
    if (!chart || typeof chart !== 'object') continue;

    const timestamp = new Date(chart.timestamp || chart.date || 0);
    if (!Number.isFinite(timestamp.getTime())) continue;

    hydrated.push({
      ...chart,
      confidence: chart.confidence ?? chart.verdict?.confidence ?? 0,
      timestamp,
      date: timestamp.toISOString().split('T')[0],
    });
  }

  return hydrated;
}
