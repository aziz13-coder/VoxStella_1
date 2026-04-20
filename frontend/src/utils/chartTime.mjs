function asValidDate(value) {
  if (value == null) return null;
  const date = value instanceof Date ? new Date(value) : new Date(value);
  return Number.isFinite(date.getTime()) ? date : null;
}

export function getChartSourceInstant(chart) {
  return (
    asValidDate(chart?.chart_data?.timezone_info?.utc_time) ||
    asValidDate(chart?.timestamp) ||
    asValidDate(chart?.date) ||
    null
  );
}

export function formatChartSourceForApi(chart) {
  const instant = getChartSourceInstant(chart);
  if (!instant) return null;

  const timezone = chart?.chart_data?.timezone_info?.timezone;
  if (timezone) {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: timezone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      hourCycle: 'h23',
    }).formatToParts(instant);

    const values = Object.fromEntries(
      parts
        .filter((part) => part.type !== 'literal')
        .map((part) => [part.type, part.value]),
    );

    return {
      instant,
      timezone,
      date: `${values.day}/${values.month}/${values.year}`,
      time: `${values.hour}:${values.minute}`,
    };
  }

  const day = String(instant.getDate()).padStart(2, '0');
  const month = String(instant.getMonth() + 1).padStart(2, '0');
  const year = instant.getFullYear();
  const hours = String(instant.getHours()).padStart(2, '0');
  const minutes = String(instant.getMinutes()).padStart(2, '0');

  return {
    instant,
    timezone: null,
    date: `${day}/${month}/${year}`,
    time: `${hours}:${minutes}`,
  };
}
