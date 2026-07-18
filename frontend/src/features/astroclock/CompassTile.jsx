import React, { useEffect, useMemo, useRef, useState } from 'react';

import { AstroClockAPI } from './api.mjs';
import Directional3DModal from './Directional3DModal.jsx';
import { isSavedSnapCalculationEligible } from './savedSnapViewModel.mjs';

const PlanetSymbols = {
  Sun: '\u2609',
  Moon: '\u263D',
  Mercury: '\u263F',
  Venus: '\u2640',
  Mars: '\u2642',
  Jupiter: '\u2643',
  Saturn: '\u2644',
  Uranus: '\u2645',
  Neptune: '\u2646',
  Pluto: '\u2647',
};

const SIGN_GLYPHS = ['\u2648', '\u2649', '\u264A', '\u264B', '\u264C', '\u264D', '\u264E', '\u264F', '\u2650', '\u2651', '\u2652', '\u2653'];
const symbolFontFamily = '\'Segoe UI Symbol\', \'Noto Sans Symbols 2\', \'Arial Unicode MS\', sans-serif';
const labelFontFamily = '\'Segoe UI\', system-ui, sans-serif';
const DOME_TILT_RAD = Math.PI / 7.5;
const DOME_PERSPECTIVE = 0.18;

function normalizeBearing(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return ((numeric % 360) + 360) % 360;
}

function roundContextNumber(value) {
  return Math.round(Number(value) * 1000000) / 1000000;
}

function clampLatitude(value) {
  return roundContextNumber(clamp(Number(value), -89.999999, 89.999999));
}

function wrapLongitude(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return undefined;
  let wrapped = ((numeric + 180) % 360 + 360) % 360 - 180;
  if (Object.is(wrapped, -180)) wrapped = 180;
  return roundContextNumber(wrapped);
}

function addHoursToIso(value, hours) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Date(date.getTime() + (Number(hours) * 60 * 60 * 1000)).toISOString();
}

export default React.memo(CompassTile);

function snapCoord(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.round(numeric * 2) / 2;
}

function snapPoint(point) {
  return {
    ...point,
    x: snapCoord(point.x),
    y: snapCoord(point.y),
  };
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function formatZodiacPoint(longitude) {
  const numeric = Number(longitude);
  if (!Number.isFinite(numeric)) return null;
  const normalized = ((numeric % 360) + 360) % 360;
  const signIndex = Math.floor(normalized / 30);
  const within = normalized % 30;
  const degrees = Math.floor(within);
  const minutes = Math.round((within - degrees) * 60);
  return `${SIGN_GLYPHS[signIndex]} ${degrees}\u00B0${String(minutes).padStart(2, '0')}'`;
}

function firstPresent(...values) {
  for (const value of values) {
    if (value === null || value === undefined) continue;
    const text = String(value).trim();
    if (text) return value;
  }
  return undefined;
}

function finiteNumberOrUndefined(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function snapDashboard(snap) {
  return snap?.dashboard && typeof snap.dashboard === 'object' ? snap.dashboard : {};
}

function directionalCoordinatePairFrom(source) {
  if (!source || typeof source !== 'object') return null;
  if (Array.isArray(source.coords) && source.coords.length >= 2) {
    const nested = {
      latitude: finiteNumberOrUndefined(source.coords[0]),
      longitude: finiteNumberOrUndefined(source.coords[1]),
    };
    if (nested.latitude !== undefined && nested.longitude !== undefined) return nested;
  }

  const direct = {
    latitude: finiteNumberOrUndefined(source.latitude ?? source.lat),
    longitude: finiteNumberOrUndefined(source.longitude ?? source.lon ?? source.lng),
  };
  if (direct.latitude !== undefined && direct.longitude !== undefined) return direct;

  const coords = source.coordinates && typeof source.coordinates === 'object' ? source.coordinates : null;
  if (coords) {
    const nested = {
      latitude: finiteNumberOrUndefined(coords.latitude ?? coords.lat),
      longitude: finiteNumberOrUndefined(coords.longitude ?? coords.lon ?? coords.lng),
    };
    if (nested.latitude !== undefined && nested.longitude !== undefined) return nested;
  }

  const tzCoords = source.timezone_info?.coordinates;
  if (tzCoords && typeof tzCoords === 'object') {
    const nested = {
      latitude: finiteNumberOrUndefined(tzCoords.latitude ?? tzCoords.lat),
      longitude: finiteNumberOrUndefined(tzCoords.longitude ?? tzCoords.lon ?? tzCoords.lng),
    };
    if (nested.latitude !== undefined && nested.longitude !== undefined) return nested;
  }

  return null;
}

function directionalSnapCoordinates(snap) {
  const dashboard = snapDashboard(snap);
  const location = firstPresent(snap?.location, dashboard?.location);
  const candidates = [
    directionalCoordinatePairFrom(snap),
    directionalCoordinatePairFrom(dashboard),
    directionalCoordinatePairFrom(snap?.chart_snapshot),
    directionalCoordinatePairFrom(dashboard?.chart_snapshot),
  ].filter(Boolean);

  let zeroPair = null;
  for (const pair of candidates) {
    const isZeroPair = Math.abs(pair.latitude) < 1e-9 && Math.abs(pair.longitude) < 1e-9;
    if (isZeroPair && location) {
      zeroPair = pair;
      continue;
    }
    return pair;
  }
  return location ? {} : (zeroPair || {});
}

function mergeDirectionalSnap(summary, detail) {
  if (!detail || typeof detail !== 'object') return summary || null;
  const full = detail.snap && typeof detail.snap === 'object'
    ? detail.snap
    : detail.data?.snap && typeof detail.data.snap === 'object'
      ? detail.data.snap
      : detail.data && typeof detail.data === 'object'
        ? detail.data
        : detail;
  if (!full || typeof full !== 'object') return summary || null;
  return {
    ...(summary || {}),
    ...full,
    id: full.id || summary?.id,
    label: full.label || summary?.label,
    dashboard: {
      ...(summary?.dashboard && typeof summary.dashboard === 'object' ? summary.dashboard : {}),
      ...(full.dashboard && typeof full.dashboard === 'object' ? full.dashboard : {}),
    },
    summary: {
      ...(summary?.summary && typeof summary.summary === 'object' ? summary.summary : {}),
      ...(full.summary && typeof full.summary === 'object' ? full.summary : {}),
    },
  };
}

function directionalSnapNeedsDetail(snap) {
  if (!snap) return false;
  const { latitude, longitude } = directionalSnapCoordinates(snap);
  if (latitude !== undefined && longitude !== undefined) return false;
  return Boolean(snap?.id);
}

function snapToDirectionalContext(snap, fallbackHouseSystem) {
  if (!snap) return null;
  const dashboard = snapDashboard(snap);
  const datetime = firstPresent(snap?.effective_datetime, dashboard?.timestamp, snap?.datetime, snap?.timestamp);
  if (!datetime) return null;
  const { latitude, longitude } = directionalSnapCoordinates(snap);
  const context = {
    mode: 'manual',
    datetime,
    location: firstPresent(snap?.location, dashboard?.location),
    timezone: firstPresent(snap?.timezone, dashboard?.timezone, snap?.timezone_label, dashboard?.timezone_label),
    houseSystem: firstPresent(
      dashboard?.house_system_code,
      snap?.house_system_code,
      dashboard?.house_system,
      snap?.house_system,
      fallbackHouseSystem,
    ),
  };
  if (latitude !== undefined && longitude !== undefined) {
    context.latitude = latitude;
    context.longitude = longitude;
  }
  return context;
}

function toRadians(value) {
  return (Number(value) || 0) * Math.PI / 180;
}

function normalizeAltitude(value) {
  const altitude = Number(value);
  if (!Number.isFinite(altitude)) return null;
  return Math.max(-90, Math.min(90, altitude));
}

function skyVector(azimuthDeg, altitudeDeg) {
  const azimuth = toRadians(normalizeBearing(azimuthDeg));
  const altitude = normalizeAltitude(altitudeDeg);
  const altitudeRad = toRadians(altitude == null ? 0 : altitude);
  const horizontal = Math.cos(altitudeRad);
  return {
    x: horizontal * Math.sin(azimuth),
    y: horizontal * Math.cos(azimuth),
    z: Math.sin(altitudeRad),
    altitudeDeg: altitude,
  };
}

function projectPlanPoint(azimuthDeg, altitudeDeg, radius, cx, cy) {
  const altitude = normalizeAltitude(altitudeDeg);
  const angle = toRadians(90 - normalizeBearing(azimuthDeg));
  const belowHorizon = altitude != null && altitude < 0;
  let pointRadius = radius * 0.78;
  if (altitude != null) {
    pointRadius = Math.max(radius * 0.06, Math.cos(toRadians(Math.abs(altitude))) * radius);
  }
  return {
    x: cx + pointRadius * Math.cos(angle),
    y: cy - pointRadius * Math.sin(angle),
    pointRadius,
    belowHorizon,
    altitudeDeg: altitude,
    depth: 0,
  };
}

function projectDomeVector(vector, radius, cx, cy) {
  const depth = (vector.y * Math.cos(DOME_TILT_RAD)) - (vector.z * Math.sin(DOME_TILT_RAD));
  const projectedY = (vector.y * Math.sin(DOME_TILT_RAD)) + (vector.z * Math.cos(DOME_TILT_RAD));
  const scale = clamp(1 - (depth * DOME_PERSPECTIVE), 0.82, 1.18);
  return {
    x: cx + (vector.x * radius * scale),
    y: cy - (projectedY * radius * scale),
    depth,
    scale,
  };
}

function projectDomePoint(azimuthDeg, altitudeDeg, radius, cx, cy) {
  const vector = skyVector(azimuthDeg, altitudeDeg);
  const point = projectDomeVector(vector, radius, cx, cy);
  return {
    ...point,
    altitudeDeg: vector.altitudeDeg,
    belowHorizon: vector.altitudeDeg != null && vector.altitudeDeg < 0,
    vector,
  };
}

function buildPath(points) {
  if (!Array.isArray(points) || points.length === 0) return '';
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' ');
}

function buildDomeRingPath(altitudeDeg, radius, cx, cy) {
  const points = [];
  for (let azimuth = 0; azimuth <= 360; azimuth += 8) {
    points.push(projectDomePoint(azimuth, altitudeDeg, radius, cx, cy));
  }
  return buildPath(points);
}

function CompassTile({
  includeModern = false,
  timestamp,
  mode,
  location,
  timezone,
  latitude,
  longitude,
  houseSystem,
  initialData = null,
  houseCusps = [],
  snaps = [],
  activeSnapId = '',
  loadingSnaps = false,
  snapsLoaded = true,
  onRefreshSnaps,
  directional3dLocked = false,
  onDirectional3dLocked,
  directional3dLockedTitle,
}) {
  const [view, setView] = useState('alt');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [remoteData, setRemoteData] = useState(null);
  const [directional3dOpen, setDirectional3dOpen] = useState(false);
  const [directional3dLoading, setDirectional3dLoading] = useState(false);
  const [directional3dError, setDirectional3dError] = useState(null);
  const [directional3dData, setDirectional3dData] = useState(null);
  const [directional3dSource, setDirectional3dSource] = useState('current');
  const [directional3dSnapId, setDirectional3dSnapId] = useState(activeSnapId || '');
  const [directional3dSnapDetailVersion, setDirectional3dSnapDetailVersion] = useState(0);
  const requestIdRef = useRef(0);
  const directional3dRequestIdRef = useRef(0);
  const directional3dSnapDetailsRef = useRef(new Map());

  const hasCoordinates = Number.isFinite(Number(latitude)) && Number.isFinite(Number(longitude));
  const hasLocation = typeof location === 'string' && location.trim().length > 0;
  const hasRequestContext = Boolean(timestamp && (hasCoordinates || hasLocation));
  const seededData = useMemo(
    () => (Array.isArray(initialData?.azimuths) ? initialData : null),
    [initialData],
  );
  const seededSupportsAltitude = useMemo(
    () => seededData?.azimuths?.some((item) => Number.isFinite(Number(item?.altitude_deg))) || false,
    [seededData],
  );
  const snapOptions = useMemo(
    () => (Array.isArray(snaps) ? snaps.filter((snap) => snap?.id) : []),
    [snaps],
  );
  const eligibleSnapOptions = useMemo(
    () => snapOptions.filter((snap) => isSavedSnapCalculationEligible(snap)),
    [snapOptions],
  );
  const activeCompassSnap = useMemo(
    () => eligibleSnapOptions.find(
      (snap) => String(snap?.id || '') === String(activeSnapId || ''),
    ) || null,
    [activeSnapId, eligibleSnapOptions],
  );
  const shouldFetchRemote = Boolean(
    activeCompassSnap
    || (hasRequestContext && (!seededData || !seededSupportsAltitude)),
  );
  const canOpenDirectional3d = hasRequestContext || eligibleSnapOptions.length > 0;
  const selectedDirectionalSnap = useMemo(
    () => {
      const summary = eligibleSnapOptions.find(
        (snap) => String(snap?.id || '') === String(directional3dSnapId || ''),
      ) || null;
      if (!summary?.id) return summary;
      return mergeDirectionalSnap(summary, directional3dSnapDetailsRef.current.get(String(summary.id)));
    },
    [directional3dSnapDetailVersion, directional3dSnapId, eligibleSnapOptions],
  );
  const currentDirectionalContext = useMemo(() => ({
    includeModern,
    mode: mode === 'manual' ? 'manual' : 'realtime',
    ...(mode === 'manual' && timestamp ? { datetime: timestamp } : {}),
    location,
    timezone,
    latitude,
    longitude,
    houseSystem,
  }), [houseSystem, includeModern, latitude, location, longitude, mode, timestamp, timezone]);

  useEffect(() => {
    if (!shouldFetchRemote) {
      setRemoteData(null);
      setError(null);
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    const requestId = ++requestIdRef.current;

    async function fetchCompass() {
      setLoading(true);
      setError(null);
      try {
        const res = await AstroClockAPI.getCompass(
          activeCompassSnap?.id
            ? {
              includeModern,
              snapId: String(activeCompassSnap.id),
              houseSystem,
            }
            : {
              includeModern,
              mode,
              datetime: timestamp,
              location,
              timezone,
              latitude,
              longitude,
              houseSystem,
            },
        );
        if (cancelled || requestId !== requestIdRef.current) return;
        if (res?.success) {
          setRemoteData(res.data || null);
        } else {
          setRemoteData(null);
          setError(res?.error || 'Failed to load bearings');
        }
      } catch (e) {
        if (cancelled || requestId !== requestIdRef.current) return;
        const msg = String(e?.message || '');
        if (msg.includes('license_required') || msg.includes('license_invalid')) {
          setError('License required');
        } else {
          setError(msg || 'Failed to load bearings');
        }
        setRemoteData(null);
      } finally {
        if (!cancelled && requestId === requestIdRef.current) {
          setLoading(false);
        }
      }
    }

    fetchCompass();
    return () => {
      cancelled = true;
    };
  }, [
    activeCompassSnap,
    houseSystem,
    includeModern,
    latitude,
    location,
    longitude,
    mode,
    shouldFetchRemote,
    timestamp,
    timezone,
  ]);

  useEffect(() => {
    if (!activeSnapId) return;
    const activeSnap = snapOptions.find(
      (snap) => String(snap?.id || '') === String(activeSnapId),
    );
    if (!activeSnap) return;
    if (!isSavedSnapCalculationEligible(activeSnap)) {
      setDirectional3dSnapId('');
      if (directional3dSource === 'snap') {
        setDirectional3dSource('current');
        setDirectional3dError(
          'This saved chart needs context review. Correct it in Astro Clock and use the corrected copy.',
        );
      }
      return;
    }
    setDirectional3dSnapId(String(activeSnapId));
  }, [activeSnapId, directional3dSource, snapOptions]);

  const resolveDirectionalContext = (source, snapId = directional3dSnapId, snapOverride = null) => {
    if (source !== 'snap') return currentDirectionalContext;
    const snap = snapOverride
      || eligibleSnapOptions.find((item) => String(item?.id || '') === String(snapId || ''))
      || null;
    return snapToDirectionalContext(snap, houseSystem);
  };

  async function resolveDirectionalSnapForLoad(snapId) {
    const snapKey = String(snapId || '');
    const summary = snapOptions.find((item) => String(item?.id || '') === snapKey) || null;
    if (!summary) return null;
    if (!isSavedSnapCalculationEligible(summary)) {
      throw new Error(
        'This saved chart needs context review. Correct it in Astro Clock and use the corrected copy.',
      );
    }
    const cached = directional3dSnapDetailsRef.current.get(snapKey);
    if (cached) return mergeDirectionalSnap(summary, cached);
    if (!directionalSnapNeedsDetail(summary)) return summary;

    const response = await AstroClockAPI.getSnap(snapKey);
    const detail = response?.snap || response?.data?.snap || response?.data || null;
    if (!response?.success || !detail) {
      throw new Error(response?.error || response?.detail || 'Failed to load saved snap details.');
    }
    if (!isSavedSnapCalculationEligible(detail)) {
      throw new Error(
        'This saved chart needs context review. Correct it in Astro Clock and use the corrected copy.',
      );
    }
    directional3dSnapDetailsRef.current.set(snapKey, detail);
    setDirectional3dSnapDetailVersion((version) => version + 1);
    return mergeDirectionalSnap(summary, detail);
  }

  async function loadDirectional3d(source = directional3dSource, snapId = directional3dSnapId, contextOverride = null) {
    setDirectional3dOpen(true);
    const requestId = ++directional3dRequestIdRef.current;
    setDirectional3dLoading(true);
    setDirectional3dError(null);
    try {
      const loadedSnap = contextOverride ? null : (source === 'snap' ? await resolveDirectionalSnapForLoad(snapId) : null);
      if (requestId !== directional3dRequestIdRef.current) return;
      const context = contextOverride || resolveDirectionalContext(source, snapId, loadedSnap);
      const requiresDatetime = source === 'snap' || context?.mode === 'manual';
      if (requiresDatetime && !context?.datetime) {
        setDirectional3dData(null);
        setDirectional3dError(source === 'snap'
          ? 'Choose a saved snap with chart time and location.'
          : 'Directional 3D needs an active chart time and location.');
        return;
      }
      const usesStoredSnap = source === 'snap' && !contextOverride && snapId;
      const res = await AstroClockAPI.getDirectional3d(
        usesStoredSnap
          ? {
            includeModern,
            snapId: String(snapId),
            houseSystem: context?.houseSystem || houseSystem,
          }
          : {
            includeModern,
            ...context,
          },
      );
      if (requestId !== directional3dRequestIdRef.current) return;
      if (res?.success) {
        setDirectional3dData(res.data || null);
      } else {
        setDirectional3dData(null);
        setDirectional3dError(res?.error || 'Failed to load Directional 3D');
      }
    } catch (e) {
      if (requestId !== directional3dRequestIdRef.current) return;
      const msg = String(e?.message || '');
      if (msg.includes('license_required') || msg.includes('license_invalid')) {
        setDirectional3dError('License required');
      } else {
        setDirectional3dError(msg || 'Failed to load Directional 3D');
      }
      setDirectional3dData(null);
    } finally {
      if (requestId === directional3dRequestIdRef.current) {
        setDirectional3dLoading(false);
      }
    }
  }

  const handleDirectional3dStep = (step = {}) => {
    const baseContext = resolveDirectionalContext(
      directional3dSource,
      directional3dSnapId,
      selectedDirectionalSnap,
    ) || {};
    const chartInfo = directional3dData?.chart_info || {};
    const nextContext = { ...baseContext };
    const chartLatitude = finiteNumberOrUndefined(chartInfo.latitude);
    const chartLongitude = finiteNumberOrUndefined(chartInfo.longitude);
    const latitudeBase = chartLatitude ?? finiteNumberOrUndefined(baseContext.latitude) ?? finiteNumberOrUndefined(latitude);
    const longitudeBase = chartLongitude ?? finiteNumberOrUndefined(baseContext.longitude) ?? finiteNumberOrUndefined(longitude);
    const chartIso = firstPresent(chartInfo.utc_datetime, baseContext.datetime, timestamp);
    const hours = finiteNumberOrUndefined(step.hours);
    const latitudeDelta = finiteNumberOrUndefined(step.latitudeDelta);
    const longitudeDelta = finiteNumberOrUndefined(step.longitudeDelta);

    if (chartLatitude !== undefined) nextContext.latitude = chartLatitude;
    if (chartLongitude !== undefined) nextContext.longitude = chartLongitude;
    if (nextContext.mode === 'manual' && chartIso) nextContext.datetime = addHoursToIso(chartIso, 0) || chartIso;

    if (hours !== undefined) {
      const nextIso = addHoursToIso(chartIso, hours);
      if (!nextIso) {
        setDirectional3dError('Directional 3D needs an active chart time before stepping.');
        return;
      }
      nextContext.mode = 'manual';
      nextContext.datetime = nextIso;
    }

    if (latitudeDelta !== undefined) {
      if (latitudeBase === undefined) {
        setDirectional3dError('Directional 3D needs chart latitude before stepping.');
        return;
      }
      nextContext.latitude = clampLatitude(latitudeBase + latitudeDelta);
    }

    if (longitudeDelta !== undefined) {
      if (longitudeBase === undefined) {
        setDirectional3dError('Directional 3D needs chart longitude before stepping.');
        return;
      }
      nextContext.longitude = wrapLongitude(longitudeBase + longitudeDelta);
    }

    loadDirectional3d(directional3dSource, directional3dSnapId, nextContext);
  };

  const handleOpenDirectional3d = () => {
    if (directional3dLocked) {
      onDirectional3dLocked?.();
      return;
    }
    if (hasRequestContext) {
      setDirectional3dSource('current');
      loadDirectional3d('current');
      return;
    }
    const activeEligibleSnap = eligibleSnapOptions.find(
      (snap) => String(snap?.id || '') === String(activeSnapId || ''),
    );
    const selectedEligibleSnap = eligibleSnapOptions.find(
      (snap) => String(snap?.id || '') === String(directional3dSnapId || ''),
    );
    const nextSnapId = selectedEligibleSnap?.id || activeEligibleSnap?.id || eligibleSnapOptions[0]?.id || '';
    setDirectional3dSource('snap');
    setDirectional3dSnapId(String(nextSnapId || ''));
    if (nextSnapId) {
      loadDirectional3d('snap', String(nextSnapId));
    } else {
      setDirectional3dOpen(true);
      setDirectional3dData(null);
      setDirectional3dError('No saved snaps are available yet.');
    }
  };

  const handleDirectional3dSourceChange = (nextSource) => {
    setDirectional3dSource(nextSource);
    if (nextSource === 'current') {
      loadDirectional3d('current');
      return;
    }
    const activeEligibleSnap = eligibleSnapOptions.find(
      (snap) => String(snap?.id || '') === String(activeSnapId || ''),
    );
    const selectedEligibleSnap = eligibleSnapOptions.find(
      (snap) => String(snap?.id || '') === String(directional3dSnapId || ''),
    );
    const nextSnapId = selectedEligibleSnap?.id || activeEligibleSnap?.id || eligibleSnapOptions[0]?.id || '';
    if (nextSnapId) {
      setDirectional3dSnapId(String(nextSnapId));
      loadDirectional3d('snap', String(nextSnapId));
    } else {
      setDirectional3dData(null);
      setDirectional3dError('No saved snaps are available yet.');
    }
  };

  const handleDirectional3dSnapChange = (snapId) => {
    const nextSnapId = String(snapId || '');
    const nextSnap = snapOptions.find((snap) => String(snap?.id || '') === nextSnapId);
    if (nextSnap && !isSavedSnapCalculationEligible(nextSnap)) {
      setDirectional3dError(
        'This saved chart needs context review. Correct it in Astro Clock and use the corrected copy.',
      );
      return;
    }
    if (directional3dSource === 'snap' && nextSnapId === String(directional3dSnapId || '')) {
      return;
    }
    setDirectional3dSnapId(nextSnapId);
    setDirectional3dSource('snap');
    if (nextSnapId) {
      loadDirectional3d('snap', nextSnapId);
    } else {
      setDirectional3dData(null);
      setDirectional3dError('Choose a saved snap.');
    }
  };

  const displayData = remoteData || seededData;
  const placements = useMemo(
    () => (Array.isArray(displayData?.azimuths) ? displayData.azimuths.filter(Boolean) : []),
    [displayData],
  );
  const hasDisplayData = placements.length > 0;
  const supportsAltitude = placements.some((item) => Number.isFinite(Number(item?.altitude_deg)));
  const activeView = view === 'alt' && supportsAltitude ? 'alt' : 'az';
  const risingLabel = useMemo(
    () => (Array.isArray(houseCusps) && houseCusps.length > 0 ? formatZodiacPoint(houseCusps[0]) : null),
    [houseCusps],
  );
  const settingLabel = useMemo(
    () => (Array.isArray(houseCusps) && houseCusps.length > 6 ? formatZodiacPoint(houseCusps[6]) : null),
    [houseCusps],
  );

  useEffect(() => {
    if (hasDisplayData && view === 'alt' && !supportsAltitude && !shouldFetchRemote) {
      setView('az');
    }
  }, [hasDisplayData, shouldFetchRemote, supportsAltitude, view]);

  const svg = useMemo(() => {
    if (!hasDisplayData) return null;

    const size = 272;
    const cx = size / 2;
    const cy = size / 2;
    const radius = 102;
    const isDomeView = activeView === 'alt' && supportsAltitude;
    const projectPoint = (entry) => (
      isDomeView
        ? projectDomePoint(entry?.azimuth_deg, entry?.altitude_deg, radius, cx, cy)
        : projectPlanPoint(entry?.azimuth_deg, entry?.altitude_deg, radius, cx, cy)
    );

    const ordered = [...placements]
      .map((entry, index) => ({ entry, index }))
      .sort((a, b) => normalizeBearing(a.entry?.azimuth_deg) - normalizeBearing(b.entry?.azimuth_deg));
    const pointLayout = new Map();

    for (const item of ordered) {
      const point = snapPoint(projectPoint(item.entry));
      pointLayout.set(item.index, point);
    }

    const planRings = [0, 30, 60].map((altitudeDeg) => ({
      altitudeDeg,
      ringRadius: Math.cos(toRadians(altitudeDeg)) * radius,
    }));
    const domeRingPaths = [0, 30, 60].map((altitudeDeg) => ({
      altitudeDeg,
      path: buildDomeRingPath(altitudeDeg, radius, cx, cy),
    }));
    const domeMeridianPath = buildPath([
      ...Array.from({ length: 10 }, (_value, index) => projectDomePoint(0, index * 10, radius, cx, cy)),
      ...Array.from({ length: 10 }, (_value, index) => projectDomePoint(180, 90 - (index * 10), radius, cx, cy)),
    ]);
    const domePrimeVerticalPath = buildPath([
      ...Array.from({ length: 10 }, (_value, index) => projectDomePoint(90, index * 10, radius, cx, cy)),
      ...Array.from({ length: 10 }, (_value, index) => projectDomePoint(270, 90 - (index * 10), radius, cx, cy)),
    ]);
    const zenithPoint = isDomeView
      ? projectDomePoint(0, 90, radius, cx, cy)
      : { x: cx, y: cy };
    const renderedEntries = isDomeView
      ? [...ordered].sort((left, right) => {
        const leftDepth = pointLayout.get(left.index)?.depth ?? 0;
        const rightDepth = pointLayout.get(right.index)?.depth ?? 0;
        return rightDepth - leftDepth;
      })
      : ordered;

    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox={`0 0 ${size} ${size}`}
        className="block h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
        shapeRendering="geometricPrecision"
        textRendering="optimizeLegibility"
      >
        {isDomeView ? (
          <>
            {domeRingPaths.map((ring, index) => (
              <path
                key={`dome-ring-${ring.altitudeDeg}`}
                d={ring.path}
                fill="none"
                stroke={index === 0 ? '#d4d4d8' : '#e8eaee'}
                strokeWidth="1"
                strokeDasharray={ring.altitudeDeg === 0 ? undefined : '3 4'}
              />
            ))}
            <path d={domeMeridianPath} fill="none" stroke="#eceef2" strokeDasharray="3 4" strokeWidth="1" />
            <path d={domePrimeVerticalPath} fill="none" stroke="#f1f3f6" strokeDasharray="3 4" strokeWidth="1" />
          </>
        ) : (
          <>
            {planRings.map((ring, index) => (
              <circle
                key={`plan-ring-${ring.altitudeDeg}`}
                cx={cx}
                cy={cy}
                r={ring.ringRadius}
                fill="none"
                stroke={index === 0 ? '#d4d4d8' : '#e8eaee'}
                strokeWidth="1"
                strokeDasharray={ring.altitudeDeg === 0 ? undefined : '3 4'}
              />
            ))}
            <line x1={cx - radius} y1={cy} x2={cx + radius} y2={cy} stroke="#eceef2" strokeDasharray="3 4" />
            <line x1={cx} y1={cy - radius} x2={cx} y2={cy + radius} stroke="#f1f3f6" strokeDasharray="3 4" />
            {false && [
              { label: 'H', altitudeDeg: 0 },
              { label: '30°', altitudeDeg: 30 },
              { label: '60°', altitudeDeg: 60 },
            ].map((ringLabel) => (
              <text
                key={ringLabel.label}
                x={cx + 8}
                y={cy - (Math.cos(toRadians(ringLabel.altitudeDeg)) * radius) + 4}
                fontSize="9"
                fill="#a1a1aa"
              >
                {ringLabel.label}
              </text>
            ))}
          </>
        )}
        <circle cx={zenithPoint.x} cy={zenithPoint.y} r={3} fill="#111827" />
        <text
          x={snapCoord(zenithPoint.x)}
          y={snapCoord(zenithPoint.y - 8)}
          fontSize="9"
          textAnchor="middle"
          fill="#a1a1aa"
          style={{ fontFamily: labelFontFamily }}
        >
          Z
        </text>
        {['N', 'E', 'S', 'W'].map((cardinal, index) => {
          const point = isDomeView
            ? projectDomePoint(index * 90, 0, radius + 10, cx, cy)
            : projectPlanPoint(index * 90, 0, radius + 14, cx, cy);
          return (
            <text
              key={cardinal}
              x={snapCoord(point.x)}
              y={snapCoord(point.y)}
              fontSize="11"
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#6b7280"
              style={{ fontFamily: labelFontFamily }}
            >
              {cardinal}
            </text>
          );
        })}
        {renderedEntries.map(({ entry, index }) => {
          const layout = pointLayout.get(index);
          if (!layout) return null;
          const belowHorizon = !!layout.belowHorizon;
          const symbol = PlanetSymbols[entry.planet] || entry.planet;
          return (
            <g key={`${entry.planet}-${index}`} opacity={belowHorizon ? 0.72 : 1}>
              <title>{`${entry.planet || 'Planet'} directional marker`}</title>
              <text
                x={layout.x}
                y={layout.y}
                fontSize={isDomeView ? '15' : '14'}
                fontWeight="600"
                textAnchor="middle"
                dominantBaseline="middle"
                fill={belowHorizon ? '#6b7280' : '#111827'}
                stroke="rgba(255,255,255,0.94)"
                strokeWidth="3.2"
                paintOrder="stroke"
                style={{ fontFamily: symbolFontFamily }}
              >
                {symbol}
              </text>
            </g>
          );
        })}
      </svg>
    );
  }, [activeView, hasDisplayData, placements, supportsAltitude]);

  const emptyMessage = !hasRequestContext
    ? (hasCoordinates ? 'Waiting for a chart timestamp.' : 'Set a chart location to render local-space bearings.')
    : 'No local-space bearings returned for this chart.';
  const directional3dChartInfo = directional3dData?.chart_info || {};
  const canStepDirectionalTime = directional3dSource === 'snap'
    || currentDirectionalContext.mode === 'manual'
    || Boolean(firstPresent(directional3dChartInfo.utc_datetime, currentDirectionalContext.datetime, timestamp));

  return (
    <>
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400">
            Directional
          </div>
        </div>
        <div className="inline-flex rounded-full border border-zinc-200 bg-white p-1">
          {[
            { key: 'az', label: 'Az', disabled: false },
            { key: 'alt', label: 'Alt', disabled: !supportsAltitude },
          ].map((option) => (
            <button
              key={option.key}
              type="button"
              disabled={option.disabled}
              onClick={() => setView(option.key)}
              className={`rounded-full px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${
                activeView === option.key
                  ? 'bg-zinc-900 text-white'
                  : 'text-zinc-500'
              } disabled:cursor-not-allowed disabled:text-zinc-300`}
            >
              {option.label}
            </button>
          ))}
          <button
            type="button"
            disabled={!canOpenDirectional3d}
            onClick={handleOpenDirectional3d}
            title={directional3dLocked ? (directional3dLockedTitle || 'Premium feature - unlock Vox Stella to use Directional 3D') : undefined}
            className={`rounded-full px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${
              directional3dLocked
                ? 'bg-red-600 text-white hover:bg-red-700'
                : directional3dOpen
                ? 'bg-zinc-900 text-white'
                : 'text-zinc-500'
            } disabled:cursor-not-allowed disabled:text-zinc-300`}
          >
            3D
          </button>
        </div>
      </div>

      <div className="mt-4">
        {error && !hasDisplayData ? <div className="text-sm text-red-600">{error}</div> : null}
        {!error && !hasDisplayData && loading ? (
          <div className="flex min-h-[280px] items-center justify-center text-sm text-zinc-500">
            Updating local-space bearings...
          </div>
        ) : null}
        {!error && !hasDisplayData && !loading ? (
          <div className="flex min-h-[280px] items-center justify-center text-sm text-zinc-500">
            {emptyMessage}
          </div>
        ) : null}
        {hasDisplayData ? (
          <div className="mx-auto w-full max-w-[276px]">{svg}</div>
        ) : null}
      </div>

      {hasDisplayData ? (
        <>
          <div className="mt-2 grid grid-cols-2 gap-3 border-t border-zinc-100 pt-3">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                Rising
              </div>
              <div className="mt-1 text-[1rem] font-medium text-zinc-900">
                {risingLabel || '\u2014'}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                Setting
              </div>
              <div className="mt-1 text-[1rem] font-medium text-zinc-900">
                {settingLabel || '\u2014'}
              </div>
            </div>
          </div>
          {error && hasDisplayData ? (
            <div className="mt-2 text-[11px] text-amber-600">{error}</div>
          ) : null}
        </>
      ) : null}
    </div>
    <Directional3DModal
      open={directional3dOpen}
      onClose={() => setDirectional3dOpen(false)}
      payload={directional3dData}
      loading={directional3dLoading}
      error={directional3dError}
      onRetry={() => loadDirectional3d(directional3dSource, directional3dSnapId)}
      chartSource={directional3dSource}
      currentSourceLabel={mode === 'manual' ? 'Current Manual' : 'Current Auto'}
      onChartSourceChange={handleDirectional3dSourceChange}
      snapOptions={snapOptions}
      selectedSnapId={directional3dSnapId}
      selectedSnap={selectedDirectionalSnap}
      onSnapChange={handleDirectional3dSnapChange}
      loadingSnaps={loadingSnaps}
      snapsLoaded={snapsLoaded}
      onRefreshSnaps={onRefreshSnaps}
      onStepContext={handleDirectional3dStep}
      canStepTime={canStepDirectionalTime}
    />
    </>
  );
}
