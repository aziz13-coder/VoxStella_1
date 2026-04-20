import { formatChartSourceForApi } from './chartTime.mjs';

function toFiniteNumber(value) {
  if (value === '' || value == null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function firstNonEmpty(...values) {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }
  return '';
}

function buildLocationLabel(location) {
  if (!location || typeof location !== 'object') return '';
  const city = firstNonEmpty(location.city, location.name);
  const country = firstNonEmpty(location.country, location.country_name);
  if (city && country) return `${city}, ${country}`;
  return city || country;
}

export function extractChartCoordinates(chart) {
  const coordinateCandidates = [
    {
      latitude: chart?.replay_context?.latitude,
      longitude: chart?.replay_context?.longitude,
    },
    {
      latitude: chart?.chart_data?.timezone_info?.coordinates?.latitude,
      longitude: chart?.chart_data?.timezone_info?.coordinates?.longitude,
    },
    {
      latitude: chart?.chart_data?.location?.latitude ?? chart?.chart_data?.location?.lat,
      longitude: chart?.chart_data?.location?.longitude ?? chart?.chart_data?.location?.lon,
    },
    {
      latitude: chart?.location?.latitude ?? chart?.location?.lat,
      longitude: chart?.location?.longitude ?? chart?.location?.lon,
    },
  ];

  for (const candidate of coordinateCandidates) {
    const latitude = toFiniteNumber(candidate.latitude);
    const longitude = toFiniteNumber(candidate.longitude);
    if (latitude != null && longitude != null) {
      return { latitude, longitude };
    }
  }

  return null;
}

export function extractChartLocationName(chart) {
  return firstNonEmpty(
    chart?.replay_context?.location_name,
    chart?.replay_context?.locationName,
    chart?.chart_data?.timezone_info?.location_name,
    buildLocationLabel(chart?.chart_data?.location),
    chart?.location_name,
    typeof chart?.location === 'string' ? chart.location : '',
    buildLocationLabel(chart?.location),
    chart?.replay_context?.location,
  );
}

export function buildChartReplayContext(requestBody = {}, result = null) {
  const replayCoordinates =
    extractChartCoordinates(result) || {
      latitude: toFiniteNumber(requestBody?.latitude),
      longitude: toFiniteNumber(requestBody?.longitude),
    };
  const latitude = toFiniteNumber(replayCoordinates?.latitude);
  const longitude = toFiniteNumber(replayCoordinates?.longitude);
  const boost = toFiniteNumber(requestBody?.exaltationConfidenceBoost);

  return {
    question: firstNonEmpty(requestBody?.question),
    location: firstNonEmpty(requestBody?.location),
    location_name:
      extractChartLocationName(result) ||
      firstNonEmpty(requestBody?.locationName, requestBody?.location_name, requestBody?.location) ||
      null,
    useCurrentTime: Boolean(requestBody?.useCurrentTime),
    date: firstNonEmpty(requestBody?.date) || null,
    time: firstNonEmpty(requestBody?.time) || null,
    timezone:
      firstNonEmpty(requestBody?.timezone, result?.chart_data?.timezone_info?.timezone) || null,
    latitude,
    longitude,
    manualHouses: firstNonEmpty(requestBody?.manualHouses) || null,
    ignoreRadicality: Boolean(requestBody?.ignoreRadicality),
    ignoreVoidMoon: Boolean(requestBody?.ignoreVoidMoon),
    ignoreCombustion: Boolean(requestBody?.ignoreCombustion),
    ignoreSaturn7th: Boolean(requestBody?.ignoreSaturn7th),
    exaltationConfidenceBoost: boost,
  };
}

export function buildChartReplayRequest(chart) {
  const timing = formatChartSourceForApi(chart);
  if (!timing) return null;

  const replayContext = chart?.replay_context || {};
  const question = firstNonEmpty(replayContext.question, chart?.question);
  const locationName = extractChartLocationName(chart);
  const location = firstNonEmpty(
    replayContext.location_name,
    replayContext.locationName,
    replayContext.location,
    locationName,
  );
  if (!question || !location) return null;

  const requestBody = {
    question,
    location,
    useCurrentTime: false,
    date: firstNonEmpty(replayContext.date) || timing.date,
    time: firstNonEmpty(replayContext.time) || timing.time,
  };

  const timezone = firstNonEmpty(replayContext.timezone) || timing.timezone;
  if (timezone) requestBody.timezone = timezone;

  if (firstNonEmpty(replayContext.manualHouses)) {
    requestBody.manualHouses = replayContext.manualHouses.trim();
  }

  if (replayContext.ignoreRadicality) requestBody.ignoreRadicality = true;
  if (replayContext.ignoreVoidMoon) requestBody.ignoreVoidMoon = true;
  if (replayContext.ignoreCombustion) requestBody.ignoreCombustion = true;
  if (replayContext.ignoreSaturn7th) requestBody.ignoreSaturn7th = true;

  const exaltationConfidenceBoost = toFiniteNumber(replayContext.exaltationConfidenceBoost);
  if (exaltationConfidenceBoost != null) {
    requestBody.exaltationConfidenceBoost = exaltationConfidenceBoost;
  }

  const coordinates = extractChartCoordinates(chart);
  if (coordinates) {
    requestBody.latitude = coordinates.latitude;
    requestBody.longitude = coordinates.longitude;
    if (locationName) requestBody.locationName = locationName;
  }

  return requestBody;
}
