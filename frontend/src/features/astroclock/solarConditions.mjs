export function buildSolarConditionEntries(data, useMorin) {
  if (!data || typeof data !== 'object') return [];

  if (useMorin) {
    const rows = Array.isArray(data?.morin_combustion) ? data.morin_combustion : [];
    return rows
      .filter((item) => {
        const rawStatus = String(item?.status || '').trim().toLowerCase();
        return rawStatus && rawStatus !== 'free';
      })
      .map((item, index) => {
        const rawStatus = String(item?.status || '').trim().toLowerCase();
        return {
          key: `morin-${index}`,
          planet: item?.planet || '',
          tone: rawStatus,
          label: rawStatus.replace(/_/g, ' '),
          detail: Number.isFinite(Number(item?.distance_deg)) ? `${Number(item.distance_deg).toFixed(2)}° from Sun` : 'distance unavailable',
          meta: '',
        };
      });
  }

  return ['cazimi', 'combustion', 'under_beams']
    .flatMap((group) => (data?.solar_conditions?.[group] || []).map((item, index) => ({ ...item, group, idx: `${group}-${index}` })))
    .map((item) => {
      const tone = item.group === 'combustion' ? 'combust' : item.group;
      const labelBase = item.group === 'cazimi' ? 'Cazimi' : item.group === 'combustion' ? 'Combustion' : 'Under Beams';
      const label = typeof item.phase === 'string' && item.phase
        ? `${labelBase} (${item.phase.charAt(0).toUpperCase()}${item.phase.slice(1)})`
        : labelBase;
      const hoursTo = Number(item.approx_hours_to_conjunction);
      const hoursSince = Number(item.approx_hours_since_conjunction);
      const timing = Number.isFinite(hoursTo)
        ? `in ~${Math.round(hoursTo)}h`
        : Number.isFinite(hoursSince)
          ? `since ~${Math.round(hoursSince)}h`
          : '';
      const detail = Number.isFinite(Number(item.distance_from_sun))
        ? `${Number(item.distance_from_sun).toFixed(2)}° from Sun`
        : 'distance unavailable';
      const relSpeed = Number(item.relative_speed_deg_per_day);
      const meta = Number.isFinite(relSpeed)
        ? `${timing ? `${timing} · ` : ''}${relSpeed.toFixed(2)}°/day relative`
        : timing;
      return {
        key: item.idx,
        planet: item?.planet || '',
        tone,
        label,
        detail,
        meta,
      };
    });
}
